# -*- coding: utf-8 -*-
"""core/naming.py — come si chiama l'**allegato** (ticket 06).

Principio di separazione: il *file da allegare* è sempre risolto dal **campo foto
+ cartella base** (ticket 05). Il naming calcola **solo il nome allegato**, cioè il
valore di ``ATT_NAME``. Nome allegato e file su disco sono due cose diverse: il
glossario di ``CONTEXT.md`` lo dice esplicitamente.

Tre modalità **esclusive** (una per esecuzione):

``originale``
    ``ATT_NAME`` = nome reale del file risolto, estensione inclusa, verbatim.
    È la modalità predefinita.

``formula``
    ``ATT_NAME`` = espressione QGIS valutata **per feature**, con le variabili
    ``@original_name``, ``@stem``, ``@ext`` (col punto), ``@index`` (1-based) più
    tutti i campi del layer. La formula può riscrivere anche l'estensione.

``csv``
    Il CSV è la **fonte dell'elenco file**: una riga per allegato, più righe con la
    stessa chiave = più allegati sulla stessa feature. Chiave selezionabile
    (predefinita ``GLOBALID``, normalizzata con/senza graffe e senza differenze di
    case), nomi di colonna configurabili, colonna del nome allegato facoltativa.

Regole comuni:

- **Multi-valore**: ``;``, ``|`` e a capo spezzano un valore in più token (virgola
  **esclusa**: rischio prosa). Un allegato per token, ``@index`` 1-based, token
  indipendenti (uno mancante non trascina gli altri).
- **Verbatim**: dentro il GDB ``ATT_NAME`` non viene sanificato (accenti, apici,
  spazi). Il limite dell'apice è lato azione QML e si risolve con ``to_base64``.
- **Collisioni** sullo stesso ``(REL_GLOBALID, ATT_NAME)``: suffisso ``_2``, ``_3``…
  prima dell'estensione, 1-based, il primo tiene il nome pulito.
- **Nomi vuoti** (formula/CSV che produce stringa vuota): salta e prosegue, con la
  riga nel report. Il blocco duro resta per i casi strutturali del ticket 03.

Il modulo è importabile **senza QGIS**: l'unica parte che ne ha bisogno è
``valutatore_qgis()``, che importa ``qgis.core`` al suo interno.
"""

from __future__ import annotations

import csv as _csv
import io
import os
from dataclasses import dataclass, field, replace

from .attach import normalizza_guid
from .discovery import SEPARATORI_RE

# ---------------------------------------------------------------- costanti

MODALITA_ORIGINALE = "originale"
MODALITA_FORMULA = "formula"
MODALITA_CSV = "csv"
MODALITA = (MODALITA_ORIGINALE, MODALITA_FORMULA, MODALITA_CSV)

MODALITA_PREDEFINITA = MODALITA_ORIGINALE

#: Variabili disponibili nella formula, nella forma attesa da QGIS (senza ``@``
#: nel nome registrato nello scope).
VARIABILI_FORMULA = ("original_name", "stem", "ext", "index")

#: Stati di un candidato allegato (i codici → testi stanno in ``wizard/strings.py``).
STATI = ("ok", "missing", "collisione", "vuoto", "salta", "errore",
         "chiave_ignota", "file_ignoto", "duplicato")

#: Colonne riconosciute automaticamente nel CSV.
NOMI_COLONNA_CHIAVE = ("globalid", "rel_globalid", "id", "chiave", "key", "codice")
NOMI_COLONNA_FILE = ("file", "percorso", "path", "nome_file", "nomefile", "filename",
                     "foto", "allegato", "attachment", "documento")
NOMI_COLONNA_NOME = ("att_name", "nome_allegato", "nome", "name", "alias")

#: Codifiche provate in ordine quando leggo il CSV (il BOM UTF-8 è gestito a parte).
ENCODING_CSV = ("utf-8", "cp1252")

#: Tetto ai tentativi di rinomina per collisione.
MAX_SUFFISSO = 1000


# ---------------------------------------------------------------- strutture


@dataclass
class RigaSorgente:
    """Una coppia (feature del layer sorgente, campo foto) da elaborare.

    È il materiale grezzo che il wizard estrae dal layer; tenerlo in una dataclass
    (senza QGIS dentro) è quello che rende testabile tutta la parte di naming.
    """

    id_parent: str = ""          # valore grezzo del GLOBALID della feature
    campo_foto: str = ""         # nome del campo foto
    valore: object = ""          # valore del campo foto (può essere multi-valore)
    indice_feature: int = 0      # posizione della feature nell'iterazione (1-based)
    feature: object = None       # la feature QGIS, solo per la modalità formula
    percorso: str = ""           # token corrente (risolto o no): base di @original_name


@dataclass
class CandidatoAllegato:
    """Un allegato candidato: file, nome finale e stato."""

    id_parent: str = ""
    campo_foto: str = ""
    valore_campo: str = ""
    token: str = ""
    percorso_file: str = ""
    nome_allegato: str = ""
    nome_originale: str = ""     # nome prima di un'eventuale rinomina per collisione
    indice_token: int = 0        # @index, 1-based
    indice_feature: int = 0
    stato: str = "ok"            # uno di STATI
    motivo: str = ""

    @property
    def da_scrivere(self) -> bool:
        return self.stato == "ok"

    @property
    def rinominato(self) -> bool:
        return self.stato == "collisione"


@dataclass
class RigaCsv:
    """Una riga utile del CSV degli allegati."""

    numero: int = 0
    chiave: str = ""
    percorso: str = ""
    nome: str = ""


@dataclass
class ElencoCsv:
    """CSV letto e interpretato: righe, avvisi e indice per chiave."""

    percorso: str = ""
    separatore: str = ";"
    encoding: str = "utf-8-sig"
    colonna_chiave: str = ""
    colonna_file: str = ""
    colonna_nome: str = ""
    righe: list = field(default_factory=list)
    avvisi: list = field(default_factory=list)
    per_chiave: dict = field(default_factory=dict)

    @property
    def chiavi_duplicate(self) -> list:
        return sorted(c for c, righe in self.per_chiave.items() if len(righe) > 1)

    def candidati_chiave(self) -> list:
        return list(self.per_chiave)


# ---------------------------------------------------------------- funzioni pure


def dividi_multivalore(valore) -> list:
    """Spezza un valore multi-file sui separatori ``;``, ``|`` e a capo.

    La virgola è **esclusa** di proposito (rischio prosa, ticket 06). Gli apici di
    contenimento (``"foto.jpg"``) vengono tolti, i token vuoti scartati.
    """
    if valore is None:
        return []
    testo = str(valore).strip()
    if not testo or testo.upper() == "NULL":
        return []
    return [t.strip().strip('"').strip("'") for t in SEPARATORI_RE.split(testo) if t.strip()]


def nome_da_percorso(percorso) -> str:
    """Nome file da un percorso (o dal token, se il file non esiste)."""
    return os.path.basename(str(percorso or "").replace("\\", "/").strip())


def con_suffisso(nome: str, numero: int) -> str:
    """``foto.jpg`` + 2 → ``foto_2.jpg``; ``foto`` + 3 → ``foto_3``.

    Il suffisso va **prima dell'estensione** (ticket 06) e il primo che arriva tiene
    il nome pulito: qui ``numero`` parte da 2.
    """
    radice, estensione = os.path.splitext(str(nome))
    return f"{radice}_{int(numero)}{estensione}"


def variabili_nome(percorso_o_token: str, indice: int) -> dict:
    """Variabili per la formula: ``@original_name``, ``@stem``, ``@ext``, ``@index``.

    ``@ext`` include il punto (``.jpg``) e vale ``""`` quando il file non ha
    estensione; ``@index`` è 1-based.
    """
    nome = nome_da_percorso(percorso_o_token)
    radice, estensione = os.path.splitext(nome)
    return {
        "original_name": nome,
        "stem": radice,
        "ext": estensione,
        "index": int(indice),
    }


def nome_allegato_da_formula(espressione: str, riga: RigaSorgente, indice_token: int,
                             valutatore) -> tuple:
    """Valuta la formula per una riga. Ritorna ``(nome, errore)``.

    ``valutatore`` è iniettato (``f(espressione, riga, variabili) -> valore``): in
    QGIS è :func:`valutatore_qgis`, nei test è una funzione finta. Così la logica di
    naming resta testabile senza QGIS.
    """
    if not espressione or not str(espressione).strip():
        return "", "formula vuota"
    variabili = variabili_nome(getattr(riga, "percorso", "") or riga.valore, indice_token)
    try:
        valore = valutatore(espressione, riga, variabili)
    except Exception as errore:  # formula rotta su questa feature: riga nel report
        return "", str(errore)
    if valore is None:
        return "", ""
    return str(valore).strip(), ""


def normalizza_chiave(valore) -> str:
    """Chiave di join normalizzata.

    GUID (con/senza graffe, qualsiasi case) → forma canonica uppercase; qualunque
    altra chiave → testo ripulito dagli spazi ai bordi.
    """
    if valore is None:
        return ""
    testo = str(valore).strip()
    if not testo:
        return ""
    from .discovery import GUID_RE

    return normalizza_guid(testo) if GUID_RE.match(testo) else testo


# ---------------------------------------------------------------- candidati


def _chiave_riga(riga: RigaSorgente) -> tuple:
    return (riga.id_parent, riga.campo_foto, riga.indice_feature)


def candidati_da_campi(righe, risolutore, modalita: str = MODALITA_PREDEFINITA,
                       espressione: str = None, valutatore=None) -> list:
    """Costruisce i candidati dalle coppie (feature, campo foto) — modalità file.

    Vale per ``originale`` e ``formula``: il file viene dal campo foto + cartella
    base (via ``risolutore``), il nome dalla modalità scelta.

    :param righe: iterabile di :class:`RigaSorgente`
    :param risolutore: ``f(token) -> percorso`` (o ``""`` se il file non si risolve)
    :param modalita: ``originale`` o ``formula``
    :param espressione: espressione QGIS, obbligatoria in modalità formula
    :param valutatore: ``f(espressione, riga, variabili) -> valore``
    """
    if modalita not in (MODALITA_ORIGINALE, MODALITA_FORMULA):
        raise ValueError(f"modalità non gestita da candidati_da_campi: {modalita!r}")
    if modalita == MODALITA_FORMULA and valutatore is None:
        raise ValueError("modalità formula senza valutatore")

    candidati = []
    for riga in righe:
        token_lista = dividi_multivalore(riga.valore)
        if not token_lista:
            candidati.append(CandidatoAllegato(
                id_parent=riga.id_parent, campo_foto=riga.campo_foto,
                valore_campo="" if riga.valore is None else str(riga.valore),
                indice_feature=riga.indice_feature,
                stato="vuoto", motivo="campo foto vuoto o nullo",
            ))
            continue

        for indice, token in enumerate(token_lista, start=1):
            percorso = risolutore(token) or ""
            stato = "ok" if percorso else "missing"
            motivo = "" if percorso else "file non trovato sulla cartella base"
            base = nome_da_percorso(percorso or token)
            nome = base

            if modalita == MODALITA_FORMULA:
                riga_formula = replace(riga, percorso=token)
                nome, errore = nome_allegato_da_formula(
                    espressione, riga_formula, indice, valutatore,
                )
                if errore:
                    candidati.append(CandidatoAllegato(
                        id_parent=riga.id_parent, campo_foto=riga.campo_foto,
                        valore_campo=str(riga.valore), token=token, percorso_file=percorso,
                        nome_originale=base, indice_token=indice,
                        indice_feature=riga.indice_feature,
                        stato="errore", motivo=errore,
                    ))
                    continue
                if not nome:
                    candidati.append(CandidatoAllegato(
                        id_parent=riga.id_parent, campo_foto=riga.campo_foto,
                        valore_campo=str(riga.valore), token=token, percorso_file=percorso,
                        nome_originale=base, indice_token=indice,
                        indice_feature=riga.indice_feature,
                        stato="salta", motivo="la formula ha prodotto un nome vuoto",
                    ))
                    continue
            elif not nome:
                candidati.append(CandidatoAllegato(
                    id_parent=riga.id_parent, campo_foto=riga.campo_foto,
                    valore_campo=str(riga.valore), token=token, percorso_file=percorso,
                    indice_token=indice, indice_feature=riga.indice_feature,
                    stato="salta", motivo="nome allegato vuoto",
                ))
                continue

            candidati.append(CandidatoAllegato(
                id_parent=riga.id_parent, campo_foto=riga.campo_foto,
                valore_campo=str(riga.valore), token=token, percorso_file=percorso,
                nome_allegato=nome, nome_originale=nome, indice_token=indice,
                indice_feature=riga.indice_feature, stato=stato, motivo=motivo,
            ))

    return candidati


def candidati_da_csv(elenco: ElencoCsv, righe, risolutore) -> list:
    """Costruisce i candidati da un CSV incrociato col layer.

    Il CSV è la fonte dell'elenco file (ticket 06): qui non servono i campi foto.
    Una riga del CSV assente dal layer produce un candidato ``chiave_ignota``
    (contato e riportato), non un errore bloccante.
    """
    per_chiave = {}
    for riga in righe:
        per_chiave.setdefault(normalizza_chiave(riga.id_parent), []).append(riga)

    candidati = []
    for riga_csv in elenco.righe:
        chiave = normalizza_chiave(riga_csv.chiave)
        righe_layer = per_chiave.get(chiave) or []
        if not righe_layer:
            candidati.append(CandidatoAllegato(
                id_parent=riga_csv.chiave, campo_foto=elenco.colonna_file,
                valore_campo=riga_csv.percorso, token=riga_csv.percorso,
                nome_originale=nome_da_percorso(riga_csv.percorso),
                stato="chiave_ignota", motivo="chiave del CSV assente nel layer",
            ))
            continue

        for riga_layer in righe_layer:
            percorso = risolutore(riga_csv.percorso) or ""
            nome = (riga_csv.nome or "").strip() or nome_da_percorso(percorso or riga_csv.percorso)
            if not percorso:
                stato, motivo = "file_ignoto", "file del CSV non trovato sulla cartella base"
            elif not nome:
                stato, motivo = "salta", "nome allegato vuoto"
            else:
                stato, motivo = "ok", ""
            candidati.append(CandidatoAllegato(
                id_parent=riga_layer.id_parent, campo_foto=elenco.colonna_file,
                valore_campo=riga_csv.percorso, token=riga_csv.percorso,
                percorso_file=percorso, nome_allegato=nome if stato == "ok" else "",
                nome_originale=nome, indice_feature=riga_layer.indice_feature,
                stato=stato, motivo=motivo,
            ))

    return candidati


def risolvi_collisioni(candidati, esistenti=(), rinomina_se_esistente: bool = False) -> list:
    """Deduplica e rinomina i candidati che collidono sullo stesso ``(REL_GLOBALID, ATT_NAME)``.

    Due situazioni diverse, due comportamenti (vedi anche il commento qui sotto):

    - **coppia già nella tabella allegati** (``esistenti``): deduplica/idempotenza →
      stato ``duplicato`` e non si scrive (contata fra i «già presenti» nel report).
      Questo è il comportamento predefinito, quello che rende ripetibile un batch:
      rilanciare lo stesso lavoro non duplica nulla. Con ``rinomina_se_esistente``
      si sceglie invece la regola del suffisso (utente esplicito).
    - **coppia ripetuta dentro il lotto**: collisione di naming → suffisso ``_2``,
      ``_3``… prima dell'estensione, il primo tiene il nome pulito.

    Nota di progetto: i due criteri vengono da decisioni diverse dello stesso effort
    (dedup del ticket 02, suffisso del ticket 06). Il default segue la regola di
    idempotenza, la scelta di rinominare resta a un clic nel wizard.
    """
    from .attach import chiave_dedup

    chiavi_esistenti = {chiave for chiave in esistenti if chiave}
    usate = set(chiavi_esistenti)      # nomi già impegnati (tabella + lotto)
    risultato = []
    for candidato in candidati:
        if candidato.stato != "ok":
            risultato.append(candidato)
            continue

        base = candidato.nome_allegato
        chiave_base = chiave_dedup(candidato.id_parent, base)
        if chiave_base and chiave_base in chiavi_esistenti and not rinomina_se_esistente:
            candidato.stato = "duplicato"
            candidato.motivo = "allegato già presente nella tabella allegati"
            risultato.append(candidato)
            continue

        scelto = ""
        for numero in range(1, MAX_SUFFISSO + 1):
            tentativo = base if numero == 1 else con_suffisso(base, numero)
            chiave = chiave_dedup(candidato.id_parent, tentativo)
            if chiave and chiave not in usate:
                scelto = tentativo
                usate.add(chiave)
                break
        if not scelto:
            candidato.stato = "errore"
            candidato.motivo = f"impossibile trovare un nome libero per «{base}»"
            risultato.append(candidato)
            continue

        if scelto != base:
            candidato.nome_allegato = scelto
            candidato.stato = "collisione"
            candidato.motivo = f"nome già usato: rinominato in {scelto}"
        risultato.append(candidato)

    return risultato


# ---------------------------------------------------------------- CSV


def _decodifica(grezzo: bytes) -> tuple:
    """Testo + codifica usata: BOM UTF-8 quando c'è, poi UTF-8, poi cp1252.

    Il BOM va riconosciuto dai byte, non provando ``utf-8-sig``: la decodifica
    ``utf-8-sig`` riesce anche senza BOM e riporterebbe una codifica sbagliata
    nell'anteprima.
    """
    if grezzo.startswith(b"\xef\xbb\xbf"):
        try:
            return grezzo.decode("utf-8-sig"), "utf-8-sig"
        except UnicodeDecodeError:
            pass
    for codifica in ENCODING_CSV:
        try:
            return grezzo.decode(codifica), codifica
        except UnicodeDecodeError:
            continue
    return grezzo.decode("cp1252", errors="replace"), "cp1252 (con sostituzioni)"


def _rileva_separatore(testo: str) -> str:
    """Separatore del CSV: ``;`` o ``,`` (o tab), rilevato dal file.

    Prima il ``Sniffer`` della stdlib, poi il ripiego sull'occorrenza più frequente
    nella prima riga utile, con ``;`` come preferenza (CSV italiani con decimali).
    """
    campione = "\n".join(riga for riga in testo.splitlines()[:5] if riga.strip())
    if not campione:
        return ";"
    try:
        return _csv.Sniffer().sniff(campione, delimiters=";,\t").delimiter
    except Exception:
        pass
    prima = campione.splitlines()[0]
    if prima.count(";") >= prima.count(","):
        return ";" if prima.count(";") else ","
    return ","


def _trova_colonna(intestazioni, candidati) -> str:
    lut = {str(i).strip().lower(): i for i in intestazioni}
    for candidato in candidati:
        trovato = lut.get(candidato.lower())
        if trovato:
            return trovato
    return ""


def intestazioni_csv(percorso: str, separatore: str = None) -> tuple:
    """Legge solo l'intestazione del CSV: ``(colonne, separatore, encoding)``.

    Serve al wizard per popolare i menu delle colonne *prima* di sapere quale sia la
    colonna chiave. Su file illeggibile ritorna ``([], messaggio, "")``.
    """
    try:
        with open(percorso, "rb") as flusso:
            grezzo = flusso.read()
    except OSError as errore:
        return [], f"non riesco a leggere il file: {errore}", ""

    testo, codifica = _decodifica(grezzo)
    separatore = separatore or _rileva_separatore(testo)
    lettore = list(_csv.reader(io.StringIO(testo), delimiter=separatore))
    lettore = [riga for riga in lettore if any((cella or "").strip() for cella in riga)]
    if not lettore:
        return [], "il CSV è vuoto o senza intestazione", codifica
    return [str(cella).strip() for cella in lettore[0]], separatore, codifica


def leggi_csv_allegati(percorso: str, chiave: str = "GLOBALID", colonna_file: str = None,
                       colonna_att_name: str = None, separatore: str = None,
                       encoding: str = None) -> ElencoCsv:
    """Legge il CSV dell'elenco file e lo indicizza per chiave.

    :raises ValueError: solo per i due casi bloccanti del ticket 06 — CSV
        illeggibile (o senza intestazione) e CSV privo della colonna chiave.

    Avvisi **non bloccanti** finiscono in ``ElencoCsv.avvisi``: colonna file
    assente, chiavi ripetute. Le chiavi assenti nel layer sono contate al momento
    dell'incrocio (:func:`candidati_da_csv`).
    """
    try:
        with open(percorso, "rb") as flusso:
            grezzo = flusso.read()
    except OSError as errore:
        raise ValueError(f"non riesco a leggere il file: {errore}") from errore

    testo, codifica = _decodifica(grezzo)
    codifica = encoding or codifica
    separatore = separatore or _rileva_separatore(testo)

    lettore = list(_csv.reader(io.StringIO(testo), delimiter=separatore))
    lettore = [riga for riga in lettore if any((cella or "").strip() for cella in riga)]
    if not lettore:
        raise ValueError("il CSV è vuoto o senza intestazione")

    intestazioni = [str(c).strip() for c in lettore[0]]
    colonna_chiave = _trova_colonna(intestazioni, (chiave,)) or chiave
    if colonna_chiave not in intestazioni:
        raise ValueError(f"colonna chiave «{chiave}» assente")

    elenco = ElencoCsv(
        percorso=str(percorso), separatore=separatore, encoding=codifica,
        colonna_chiave=colonna_chiave,
    )

    indice_chiave = intestazioni.index(colonna_chiave)
    colonna_file_trovata = colonna_file or _trova_colonna(intestazioni, NOMI_COLONNA_FILE)
    colonna_nome_trovata = colonna_att_name or _trova_colonna(intestazioni, NOMI_COLONNA_NOME)
    indice_file = intestazioni.index(colonna_file_trovata) if colonna_file_trovata in intestazioni else -1
    indice_nome = intestazioni.index(colonna_nome_trovata) if colonna_nome_trovata in intestazioni else -1
    elenco.colonna_file = colonna_file_trovata if indice_file >= 0 else ""
    elenco.colonna_nome = colonna_nome_trovata if indice_nome >= 0 else ""

    if colonna_file and colonna_file not in intestazioni:
        elenco.avvisi.append(("colonna_mancante", colonna_file))
    elif indice_file < 0:
        elenco.avvisi.append(("colonna_file_da_indicare", ""))

    for numero, riga in enumerate(lettore[1:], start=2):
        celle = [str(c).strip() for c in riga]
        chiave_riga = celle[indice_chiave] if indice_chiave < len(celle) else ""
        if not chiave_riga:
            continue
        percorso_riga = celle[indice_file] if 0 <= indice_file < len(celle) else ""
        nome_riga = celle[indice_nome] if 0 <= indice_nome < len(celle) else ""
        riga_csv = RigaCsv(numero=numero, chiave=chiave_riga,
                           percorso=percorso_riga, nome=nome_riga)
        elenco.righe.append(riga_csv)
        elenco.per_chiave.setdefault(normalizza_chiave(chiave_riga), []).append(riga_csv)

    duplicate = elenco.chiavi_duplicate
    if duplicate:
        elenco.avvisi.append(("chiavi_duplicate", len(duplicate)))

    return elenco


# ---------------------------------------------------------------- formula (QGIS)


def valutatore_qgis(layer):
    """Ritorna il valutatore di formule basato su ``QgsExpression``.

    Pattern verificato a headless su QGIS 3.44.4 (ticket 06):

    - contesto da ``QgsExpressionContextUtils.globalProjectLayerScopes(layer)`` più
      ``ctx.setFeature(feature)``;
    - variabili custom via ``QgsExpressionContextScope().setVariable(nome, valore, False)``
      e ``ctx.appendScope(scope)`` (in 3.44.4 **non** esiste ``setExpressionContext``);
    - ``expression.prepare(ctx)`` prima di ``evaluate(ctx)``.

    La funzione ritornata solleva ``ValueError`` sull'errore di valutazione, così il
    chiamante lo registra come riga del report invece di far cadere tutto il batch.
    """
    from qgis.core import (QgsExpression, QgsExpressionContext, QgsExpressionContextScope,
                           QgsExpressionContextUtils)

    def _valuta(espressione, riga, variabili):
        contesto = QgsExpressionContext(
            QgsExpressionContextUtils.globalProjectLayerScopes(layer)
        )
        feature = getattr(riga, "feature", None)
        if feature is not None:
            contesto.setFeature(feature)
        scope = QgsExpressionContextScope()
        for nome, valore in (variabili or {}).items():
            scope.setVariable(nome, valore, False)
        contesto.appendScope(scope)

        expr = QgsExpression(espressione)
        if expr.hasParserError():
            raise ValueError(expr.parserErrorString())
        expr.prepare(contesto)
        valore = expr.evaluate(contesto)
        if expr.hasEvalError():
            raise ValueError(expr.evalErrorString())
        return valore

    return _valuta


def verifica_formula(espressione: str, layer=None) -> tuple:
    """Controlla una formula: ritorna ``(errore, avviso)``.

    Errore = formula vuota o non parsabile (blocca il pulsante Avanti).
    Avviso = attributo citato che non esiste nel layer (la formula valuterebbe a
    NULL: si può proseguire, ma è bene saperlo).
    """
    testo = str(espressione or "").strip()
    if not testo:
        return "formula vuota", ""
    try:
        from qgis.core import QgsExpression

        expr = QgsExpression(testo)
        if expr.hasParserError():
            return expr.parserErrorString(), ""
        if layer is not None:
            nomi = {campo.name() for campo in layer.fields()}
            ignoti = [str(c) for c in (expr.referencedColumns() or []) if str(c) not in nomi]
            if ignoti:
                return "", "attributi non presenti nel layer: " + ", ".join(sorted(ignoti))
        return "", ""
    except Exception as errore:  # fuori da QGIS la verifica non è possibile
        return "", f"verifica della formula non disponibile: {errore}"


# ---------------------------------------------------------------- conteggi


def conteggi(candidati) -> dict:
    """Conteggi complessivi del lotto: ok / missing / collisioni / saltati / errori…

    Gli «errori» comprendono anche le chiavi del CSV assenti nel layer e i file del
    CSV non risolti: sono righe che finiscono nel report, non scritture.
    """
    risultato = {
        "ok": 0, "missing": 0, "collisione": 0, "vuoto": 0, "salta": 0,
        "errore": 0, "chiave_ignota": 0, "file_ignoto": 0, "duplicato": 0,
    }
    for candidato in candidati:
        risultato[candidato.stato] = risultato.get(candidato.stato, 0) + 1
    risultato["saltati"] = (risultato["vuoto"] + risultato["salta"] + risultato["errore"]
                            + risultato["chiave_ignota"] + risultato["file_ignoto"])
    risultato["totale"] = sum(risultato[stato] for stato in STATI)
    return risultato


def conteggi_per_campo(candidati) -> dict:
    """Allegati (stato ``ok``) per campo foto — il «conteggio per campo» del ticket 06."""
    per_campo = {}
    for candidato in candidati:
        per_campo.setdefault(candidato.campo_foto, 0)
        if candidato.stato == "ok":
            per_campo[candidato.campo_foto] += 1
    return per_campo
