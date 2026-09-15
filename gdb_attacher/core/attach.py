# -*- coding: utf-8 -*-
"""core/attach.py — verifica del layer sorgente / della tabella allegati e scrittura.

Qui vive la decisione del **ticket 02** (confermata dal ticket 03): il plugin
**non crea mai** la tabella ``<layer>__ATTACH``. La tabella allegati nasce solo da
ArcGIS Pro (``arcpy.management.EnableAttachments``), che crea *insieme* tabella,
relationship class ``__ATTACHREL`` e metadati ``GDB_Items``: crearla via GDAL
produrrebbe una tabella fantasma, invisibile come allegato ad ArcGIS. Se manca o è
incompleta il wizard si **blocca** e rimanda ad ArcGIS Pro.

Schema di scrittura (6 campi, dai due script in repo, versione normalizzata):

===================== =====================================================
``GLOBALID``          ``str(uuid.uuid4()).upper()``, **senza** graffe
``REL_GLOBALID``      GLOBALID della feature, uppercase **con** graffe ``{...}``
``CONTENT_TYPE``      mime reale dedotto dall'estensione
``ATT_NAME``          **nome allegato** verbatim (ticket 06: nessuna sanificazione)
``DATA_SIZE``         ``len(blob)``
``DATA``              blob (``QByteArray``)
===================== =====================================================

Questo modulo è importabile **senza QGIS**: gli import di ``qgis.*`` stanno dentro
le funzioni che ne hanno bisogno.
"""

from __future__ import annotations

import os
import shutil
import unicodedata
import uuid
from dataclasses import dataclass, field
from datetime import datetime

# ---------------------------------------------------------------- costanti

#: I sei campi che la tabella allegati deve avere (matching case-insensitive).
CAMPI_ALLEGATI = ("GLOBALID", "REL_GLOBALID", "CONTENT_TYPE", "ATT_NAME", "DATA_SIZE", "DATA")

#: Suffisso della tabella allegati creata da ArcGIS.
SUFFISSO_TABELLA_ALLEGATI = "__ATTACH"

#: Nomi accettati per il campo GlobalID del layer sorgente (in ordine di preferenza).
NOMI_GLOBALID_SORGENTE = ("GlobalID", "GLOBALID", "globalid")

#: Sentinelle di nullità: QGIS consegna i valori nulli come stringa ``"NULL"``, non come
#: ``None``. Qualunque valore che, ripulito e in maiuscolo, sta qui va trattato come vuoto.
SENTINELLE_NULL = frozenset({"", "NULL", "NONE", "<NULL>", "N/A"})

#: Mime per estensione. Volutamente più larga dello script click (che copre 4
#: formati e ricade su octet-stream): qui il mime serve anche all'anteprima HTML.
MIME_PER_ESTENSIONE = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".gif": "image/gif",
    ".bmp": "image/bmp",
    ".webp": "image/webp",
    ".heic": "image/heic",
    ".heif": "image/heif",
    ".tif": "image/tiff",
    ".tiff": "image/tiff",
    ".pdf": "application/pdf",
    ".txt": "text/plain",
    ".csv": "text/csv",
    ".doc": "application/msword",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".xls": "application/vnd.ms-excel",
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ".odt": "application/vnd.oasis.opendocument.text",
    ".ods": "application/vnd.oasis.opendocument.spreadsheet",
    ".zip": "application/zip",
    ".7z": "application/x-7z-compressed",
    ".dwg": "image/vnd.dwg",
    ".dxf": "image/vnd.dxf",
    ".dgn": "image/vnd.dgn",
    ".mp4": "video/mp4",
    ".mov": "video/quicktime",
    ".avi": "video/x-msvideo",
    ".mkv": "video/x-matroska",
    ".mp3": "audio/mpeg",
    ".wav": "audio/wav",
}

MIME_FALLBACK = "application/octet-stream"


# ---------------------------------------------------------------- strutture


@dataclass
class Problema:
    """Un problema strutturale, senza testo tradotto: un codice + un dettaglio tecnico.

    Il core non conosce l'interfaccia: restituisce il codice (``non_filegdb``,
    ``attach_incompleta``…) e la UI lo rende nella lingua attiva
    (``wizard/strings.py``, mappa ``TESTI_PROBLEMA``).
    """

    codice: str
    dettaglio: str = ""


@dataclass
class EsitoVerificaLayer:
    """Esito dei controlli sul **layer sorgente**."""

    origine: str = ""
    e_filegdb: bool = False
    e_scrivibile: bool = False
    campo_globalid: str = ""
    problemi: list = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.problemi


@dataclass
class EsitoTabellaAllegati:
    """Esito dei controlli sulla **tabella allegati**."""

    nome: str = ""
    presente: bool = False
    campi: dict = field(default_factory=dict)      # ruolo -> nome reale del campo
    mancanti: list = field(default_factory=list)   # ruoli assenti

    @property
    def completa(self) -> bool:
        return self.presente and not self.mancanti


@dataclass
class EsitoCompleto:
    """Verifica bloccante complessiva (ticket 03, passo 2 del wizard)."""

    layer: EsitoVerificaLayer = field(default_factory=EsitoVerificaLayer)
    tabella: EsitoTabellaAllegati = field(default_factory=EsitoTabellaAllegati)
    layer_allegati: object = None

    @property
    def bloccante(self) -> bool:
        return bool(self.layer.problemi) or not self.tabella.completa

    @property
    def problemi(self) -> list:
        return list(self.layer.problemi)


@dataclass
class StatisticaScrittura:
    """Numeri di una scrittura batch."""

    aggiunti: int = 0
    duplicati: int = 0
    saltati: int = 0
    errori: list = field(default_factory=list)   # lista di (descrizione, errore)
    annullata: bool = False
    errore_commit: str = ""                      # commit fallito: nulla è stato scritto


class EsecuzioneAnnullata(Exception):
    """Sollevata quando l'utente annulla il batch dalla barra di avanzamento.

    Serve a uscire dal blocco ``with edit(...)`` in modo che QGIS **non** committi:
    annullare = nessuna modifica al geodatabase (ticket 03). L'eccezione non esce
    dal plugin: ``scrivi_allegati()`` la intercetta e marca il risultato come
    annullato.
    """


# ---------------------------------------------------------------- funzioni pure


def normalizza_guid(valore) -> str:
    """GUID in forma canonica interna: **uppercase senza graffe**, o ``"``.

    Porta di ``normalize_guid()`` dello script click: accetta ``{GUID}`` o ``GUID``,
    spazi compresi, e rifiuta il vuoto. Il valore vuoto è il segnale che la feature
    non ha GlobalID e non può ricevere allegati.

    Tratta come vuote anche le sentinelle di nullità (``NULL``, ``None``, ``<NULL>``,
    ``""``): un campo GlobalID *presente nel layer* ma con valore nullo arriva qui come
    stringa ``"NULL"``, non come ``None``. Senza questo controllo si scriveva un
    allegato orfano con ``REL_GLOBALID="{NULL}"``, che ArcGIS non ricollega a nessuna
    feature.
    """
    if valore is None:
        return ""
    testo = str(valore).strip()
    if testo.startswith("{") and testo.endswith("}"):
        testo = testo[1:-1].strip()
    if testo.upper() in SENTINELLE_NULL:
        return ""
    return testo.upper()


def guid_con_graffe(guid) -> str:
    """GUID nella forma che ArcGIS si aspetta in ``REL_GLOBALID``: ``{UPPER}``."""
    normalizzato = normalizza_guid(guid)
    return "{" + normalizzato + "}" if normalizzato else ""


def chiave_dedup(rel_globalid, nome_allegato) -> tuple:
    """Chiave di deduplicazione ``(REL_GLOBALID, ATT_NAME)`` del ticket 02.

    Il GUID è normalizzato (graffe/case), il nome allegato è confrontato in forma
    Unicode **NFC** (``é`` composto e decomposto sono lo stesso file), ma la
    **maiuscolatura resta significativa**: ``O'Brien.JPG`` e ``o'brien.jpg`` sono due
    allegati distinti, come da regola "verbatim" del ticket 06 — il nome scritto nel GDB
    è sempre quello originale.
    Ritorna ``None`` se il GUID parent è nullo: in quel caso non si scrive nulla.
    """
    rel = guid_con_graffe(rel_globalid)
    if not rel:
        return None
    return (rel, unicodedata.normalize("NFC", "" if nome_allegato is None else str(nome_allegato)))


def indovina_content_type(percorso: str) -> str:
    """Mime reale dall'estensione del file, con ricaduta su ``octet-stream``.

    Corregge il difetto dello script batch (``image/jpeg`` hardcoded anche per PDF).
    """
    estensione = os.path.splitext(str(percorso or ""))[1].lower()
    return MIME_PER_ESTENSIONE.get(estensione, MIME_FALLBACK)


def _percorso_dataset(origine) -> str:
    """Parte "percorso" dell'origine di un layer QGIS, senza i suffissi ``|layername=...``."""
    return str(origine or "").split("|")[0].strip().rstrip("/\\")


def sembra_filegdb(origine: str) -> bool:
    """Vero se l'origine del layer punta a un dataset ``.gdb`` (FileGDB/OpenFileGDB).

    Il ``.gdb`` deve essere **l'ultimo segmento del percorso del dataset**: le forme reali
    di QGIS/GDAL sono ``.../x.gdb`` e ``.../x.gdb|layername=y``. Un ``.gdb`` che compare a
    metà percorso non basta: ``.../export.gdb/shp/layer.shp`` è uno shapefile dentro una
    cartella che si chiama ``.gdb``, e accettarlo portava a verifiche fuorvianti e a un
    backup proposto sul percorso sbagliato.
    """
    percorso = _percorso_dataset(origine)
    if not percorso:
        return False
    if percorso.lower().endswith((".gpkg", ".shp", ".zip", ".tab", ".json", ".geojson")):
        return False
    return percorso.lower().endswith(".gdb")


def percorso_gdb(origine: str) -> str:
    """Estrae il percorso del ``.gdb`` dall'origine di un layer (per il backup).

    Ritorna ``""`` se l'origine non è un dataset FileGDB. L'ultimo segmento del percorso
    è la cartella ``.gdb``: ``D:/dati/vecchio.gdb_old/layer.gdb`` → quest'ultimo, non il
    primo ``.gdb`` trovato nel testo.
    """
    percorso = _percorso_dataset(origine)
    return percorso if sembra_filegdb(percorso) else ""


def nome_tabella_allegati(nome_layer: str) -> str:
    """Nome della tabella allegati di un layer sorgente: ``<layer>__ATTACH``."""
    return f"{nome_layer}{SUFFISSO_TABELLA_ALLEGATI}"


def nome_campo(oggetto_campi, nomi) -> str:
    """Trova il nome reale di un campo ignorando maiuscole/minuscole.

    :param oggetto_campi: qualunque cosa esponga ``fields()`` (layer QGIS o finto)
    :param nomi: nomi preferiti, in ordine di preferenza
    :return: il nome presente nell'oggetto, o ``""``
    """
    try:
        campi = oggetto_campi.fields() if hasattr(oggetto_campi, "fields") else oggetto_campi
        esistenti = [c.name() for c in campi]
    except Exception:
        return ""
    lut = {nome.lower(): nome for nome in esistenti}
    for candidato in nomi:
        trovato = lut.get(str(candidato).lower())
        if trovato:
            return trovato
    return ""


def risolvi_campi_allegati(layer_allegati) -> tuple:
    """Mappa ruolo → nome reale dei 6 campi della tabella allegati.

    :return: ``(campi, mancanti)``
    """
    campi = {}
    for ruolo in CAMPI_ALLEGATI:
        nome = nome_campo(layer_allegati, (ruolo,))
        if nome:
            campi[ruolo] = nome
    mancanti = [ruolo for ruolo in CAMPI_ALLEGATI if ruolo not in campi]
    return campi, mancanti


def leggi_bytes(percorso: str) -> bytes:
    """Legge il file da allegare. Solleva ``OSError`` se non è leggibile."""
    with open(percorso, "rb") as flusso:
        return flusso.read()


def messaggio_abilitazione(layer_sorgente: str, lingua: str = None) -> str:
    """Testo che rimanda ad ArcGIS Pro / ``EnableAttachments`` (ticket 02 e 03)."""
    from ..wizard import strings

    return strings.tr("msg_arcgis_pro", lingua, layer=layer_sorgente)


# ---------------------------------------------------------------- verifica (QGIS)


def verifica_layer_sorgente(layer) -> EsitoVerificaLayer:
    """Controlli sul layer sorgente: FileGDB + GlobalID (+ scrivibilità dichiarata).

    Non solleva eccezioni: qualunque anomalia è un :class:`Problema`, così il wizard
    può mostrarle tutte insieme in tabella.
    """
    esito = EsitoVerificaLayer()

    try:
        esito.origine = str(layer.source())
    except Exception:
        esito.origine = ""

    esito.e_filegdb = sembra_filegdb(esito.origine)
    if not esito.e_filegdb:
        esito.problemi.append(Problema("non_filegdb", esito.origine))

    esito.campo_globalid = nome_campo(layer, NOMI_GLOBALID_SORGENTE)
    if not esito.campo_globalid:
        esito.problemi.append(Problema("senza_globalid", ""))

    esito.e_scrivibile = _campabilita_scrittura(layer)
    if not esito.e_scrivibile:
        esito.problemi.append(Problema("locale_non_scrivibile", ""))

    return esito


def _campabilita_scrittura(layer) -> bool:
    """Vero se il provider dichiara la capacità di aggiungere feature.

    Se non è possibile saperlo (provider esotico, oggetto finto) si assume di sì:
    un falso blocco sarebbe peggio di un errore in scrittura, che è già gestito.
    """
    try:
        from qgis.core import QgsVectorDataProvider

        capacita = layer.dataProvider().capabilities()
        return bool(capacita & QgsVectorDataProvider.Capabilities.AddFeatures)
    except Exception:
        return True


def trova_tabella_allegati(progetto, nome_layer: str):
    """Cerca nel progetto la tabella allegati ``<layer>__ATTACH``.

    :param progetto: ``QgsProject`` (o qualunque oggetto con ``mapLayersByName``)
    :return: il layer allegati o ``None``
    """
    nome = nome_tabella_allegati(nome_layer)
    try:
        trovati = list(progetto.mapLayersByName(nome))
    except Exception:
        return None
    return trovati[0] if trovati else None


def verifica_tabella_allegati(layer_allegati) -> EsitoTabellaAllegati:
    """Verifica presenza e completezza della tabella allegati (mai riparata a mano)."""
    esito = EsitoTabellaAllegati()
    if layer_allegati is None:
        return esito
    esito.presente = True
    try:
        esito.nome = str(layer_allegati.name())
    except Exception:
        esito.nome = ""
    esito.campi, esito.mancanti = risolvi_campi_allegati(layer_allegati)
    return esito


def verifica_completa(progetto, layer_sorgente) -> EsitoCompleto:
    """Verifica bloccante del passo 2 del wizard: layer + tabella allegati."""
    layer_allegati = trova_tabella_allegati(progetto, _nome_layer(layer_sorgente))
    return EsitoCompleto(
        layer=verifica_layer_sorgente(layer_sorgente),
        tabella=verifica_tabella_allegati(layer_allegati),
        layer_allegati=layer_allegati,
    )


def _nome_layer(layer) -> str:
    try:
        return str(layer.name())
    except Exception:
        return ""


# ---------------------------------------------------------------- scrittura (QGIS)


def carica_chiavi_esistenti(layer_allegati, campi=None) -> set:
    """Precarica le coppie ``(REL_GLOBALID, ATT_NAME)`` già presenti nella tabella.

    Stessa cache dello script click: serve a non riscrivere un allegato esistente
    quando il GUID parent è memorizzato con/senza graffe o in case diverso.
    """
    campi = campi or risolvi_campi_allegati(layer_allegati)[0]
    chiavi = set()
    campo_rel = campi.get("REL_GLOBALID")
    campo_nome = campi.get("ATT_NAME")
    if not campo_rel or not campo_nome:
        return chiavi
    richiesta = _richiesta_solo_chiavi(layer_allegati, campo_rel, campo_nome)
    features = (layer_allegati.getFeatures(richiesta) if richiesta is not None
                else layer_allegati.getFeatures())
    for feature in features:
        chiave = chiave_dedup(feature[campo_rel], feature[campo_nome])
        if chiave:
            chiavi.add(chiave)
    return chiavi


def _richiesta_solo_chiavi(layer_allegati, campo_rel: str, campo_nome: str):
    """Richiesta che legge **solo** ``REL_GLOBALID`` e ``ATT_NAME``, o ``None``.

    Senza limite, ``getFeatures()`` carica anche il campo ``DATA``: costruire l'insieme
    delle chiavi su una tabella con migliaia di allegati legge gigabyte dal GDB per niente
    (e l'anteprima lo fa a ogni ricarica). Se l'ambiente non offre ``QgsFeatureRequest``
    (test con finti, provider esotici) si torna a ``None`` e si legge tutto: la
    correttezza non dipende dall'ottimizzazione.
    """
    try:
        from qgis.core import QgsFeatureRequest

        campi = layer_allegati.fields()
        indici = [campi.indexOf(campo_rel), campi.indexOf(campo_nome)]
        if any(indice < 0 for indice in indici):
            return None
        return QgsFeatureRequest().setSubsetOfAttributes(indici, campi)
    except Exception:
        return None


def scrivi_allegati(layer_allegati, candidati, campi=None, chiavi_esistenti=None,
                    callback_progresso=None) -> StatisticaScrittura:
    """Scrive gli allegati in **una sola transazione**.

    :param layer_allegati: layer della tabella allegati (già verificato)
    :param candidati: iterabile di candidati con gli attributi ``nome_allegato``,
        ``percorso_file``, ``rel_globalid``, ``campo_foto``, ``id_parent``
    :param campi: mappa ruolo → nome reale dei campi (di default la ricalcola)
    :param chiavi_esistenti: cache di deduplicazione già pronta (di default la carica)
    :param callback_progresso: ``f(indice, totale, candidato)``; se ritorna ``False``
        il batch si ferma e viene annullato: nessuna scrittura, ``statistica.annullata``
        vale ``True`` (l'eccezione interna ``EsecuzioneAnnullata`` non esce da qui, il
        wizard guarda il flag per mostrare "esecuzione annullata")
    :return: :class:`StatisticaScrittura`

    Tutte le righe scritte stanno in un unico blocco ``with edit(...)``: se QGIS
    annulla la sessione di modifica, il GDB resta com'era (annulla = non si scrive
    nulla, ticket 03). Il chiamante decide *cosa* scrivere: qui si controlla solo
    che il file esista, che il parent abbia GlobalID e che la coppia
    ``(REL_GLOBALID, ATT_NAME)`` non sia già presente (deduplica/idempotenza).
    """
    from qgis.core import QgsFeature, edit
    from qgis.PyQt.QtCore import QByteArray

    campi = campi or risolvi_campi_allegati(layer_allegati)[0]
    mancanti = [ruolo for ruolo in CAMPI_ALLEGATI if ruolo not in campi]
    if mancanti:
        raise ValueError(f"tabella allegati incompleta, campi mancanti: {mancanti}")

    chiavi = set(chiavi_esistenti) if chiavi_esistenti is not None else carica_chiavi_esistenti(
        layer_allegati, campi
    )
    statistica = StatisticaScrittura()
    elenco = list(candidati)
    totale = len(elenco)
    campi_layer = layer_allegati.fields()

    try:
        with edit(layer_allegati):
            for indice, candidato in enumerate(elenco, start=1):
                if callback_progresso is not None:
                    if callback_progresso(indice, totale, candidato) is False:
                        raise EsecuzioneAnnullata()

                nome_allegato = getattr(candidato, "nome_allegato", "") or ""
                percorso = getattr(candidato, "percorso_file", "") or ""
                # Il candidato porta il GLOBALID grezzo della feature in ``id_parent``
                # (``rel_globalid`` esiste per compatibilità con chiamanti esterni).
                guid_parent = (getattr(candidato, "rel_globalid", "")
                               or getattr(candidato, "id_parent", ""))
                rel_globalid = guid_con_graffe(guid_parent)

                if not rel_globalid:
                    statistica.saltati += 1
                    statistica.errori.append(
                        (f"{getattr(candidato, 'id_parent', '')} · {nome_allegato}",
                         "GlobalID parent nullo",
                         getattr(candidato, "id_parent", ""),
                         getattr(candidato, "campo_foto", ""))
                    )
                    continue
                if not nome_allegato:
                    statistica.saltati += 1
                    continue

                chiave = chiave_dedup(rel_globalid, nome_allegato)
                if chiave in chiavi:
                    statistica.duplicati += 1
                    continue

                try:
                    blob = leggi_bytes(percorso)
                except OSError as errore:
                    statistica.saltati += 1
                    statistica.errori.append(
                        (percorso, str(errore),
                         getattr(candidato, "id_parent", ""),
                         getattr(candidato, "campo_foto", ""))
                    )
                    continue

                feature = QgsFeature(campi_layer)
                feature[campi["GLOBALID"]] = str(uuid.uuid4()).upper()
                feature[campi["REL_GLOBALID"]] = rel_globalid
                feature[campi["CONTENT_TYPE"]] = indovina_content_type(percorso)
                feature[campi["ATT_NAME"]] = nome_allegato
                feature[campi["DATA_SIZE"]] = len(blob)
                feature[campi["DATA"]] = QByteArray(blob)

                if layer_allegati.addFeature(feature):
                    chiavi.add(chiave)
                    statistica.aggiunti += 1
                else:
                    statistica.errori.append(
                        (percorso, "addFeature() ha restituito False",
                         getattr(candidato, "id_parent", ""),
                         getattr(candidato, "campo_foto", ""))
                    )
    except EsecuzioneAnnullata:
        # `with edit(...)` esce con eccezione → QGIS fa rollback: nulla è stato scritto.
        statistica.annullata = True
        statistica.aggiunti = 0
    except Exception as errore:  # noqa: BLE001 — QgsEditError sul commit, MemoryError, provider
        # Il commit è fallito (GDB bloccato da ArcGIS, disco pieno, blob rifiutato) oppure
        # il lotto non è entrato in memoria: `with edit(...)` ha già fatto rollback, quindi
        # ciò che risultava aggiunto non esiste nel GDB. Senza questa cattura l'eccezione
        # usciva da uno slot Qt (traceback, report perso, layer lasciato in modifica).
        statistica.aggiunti = 0
        statistica.errore_commit = f"{type(errore).__name__}: {errore}"

    return statistica


# ---------------------------------------------------------------- backup


def percorso_backup_predefinito(percorso_gdb_originale: str, adesso=None) -> str:
    """Percorso del backup accanto all'originale: ``<nome>_backup_AAAAMMGG_HHMMSS.gdb``."""
    adesso = adesso or datetime.now()
    radice, nome = os.path.split(str(percorso_gdb_originale).rstrip("/\\"))
    base = nome[:-4] if nome.lower().endswith(".gdb") else nome
    nuovo = f"{base}_backup_{adesso.strftime('%Y%m%d_%H%M%S')}.gdb"
    return os.path.join(radice, nuovo) if radice else nuovo


def backup_gdb(percorso_gdb_originale: str, destinazione: str = None, callback=None) -> str:
    """Copia l'intero ``.gdb`` (cartella) prima della scrittura.

    Proposta dal wizard ma **aggirabile** («continua senza backup», ticket 03):
    a rischio dell'utente. Solleva ``OSError`` se la copia fallisce.

    :return: percorso del backup creato
    """
    origine = str(percorso_gdb_originale).rstrip("/\\")
    if not os.path.isdir(origine):
        raise OSError(f"cartella .gdb non trovata: {origine}")
    destinazione = destinazione or percorso_backup_predefinito(origine)
    if os.path.exists(destinazione):
        raise OSError(f"destinazione già esistente: {destinazione}")
    if callback is not None:
        callback(destinazione)
    # Copia prima su una cartella temporanea e rinomina solo a copia riuscita: se il disco
    # si riempie a metà, non resta un backup parziale con il nome definitivo (che al
    # tentativo successivo farebbe fallire tutto con "destinazione già esistente").
    temporanea = destinazione + ".parziale"
    try:
        if os.path.exists(temporanea):
            shutil.rmtree(temporanea, ignore_errors=True)
        shutil.copytree(origine, temporanea)
        os.rename(temporanea, destinazione)
    except Exception:
        shutil.rmtree(temporanea, ignore_errors=True)
        raise
    return destinazione
