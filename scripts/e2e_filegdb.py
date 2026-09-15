#!/usr/bin/env python3
"""Test end-to-end su un FileGDB VERO creato con GDAL, dentro un container QGIS.

I test con i finti non toccano mai un GDB: questo script ne crea uno con il driver
OpenFileGDB (GDAL ≥ 3.6 sa scrivere i FileGDB), carica i layer in QGIS, fa passare la
verifica del plugin e scrive allegati veri con ``scrivi_allegati``, poi rilegge il GDB
con GDAL indipendente e controlla riga per riga.

Cosa verifica:
  1. la verifica del plugin accetta un FileGDB con GlobalID e tabella ``__ATTACH``;
  2. la scrittura produce una riga valida: 6 campi, blob identico al file su disco,
     ``DATA_SIZE`` = dimensione reale, ``REL_GLOBALID`` con graffe e maiuscolo,
     ``CONTENT_TYPE`` dedotto dall'estensione;
  3. rilanciare lo stesso lavoro non duplica nulla (deduplica idempotente);
  4. annullare a metà batch non lascia scritture parziali (rollback).

ATTENZIONE: non sostituisce il test su un GDB creato da ArcGIS Pro. Qui manca il
relationship class ``__ATTACHREL`` e i metadati ``GDB_Items``: servono a dimostrare che
la tabella non è "fantasma" per ArcGIS, e si possono creare solo da ArcGIS Pro.

Uso (dentro l'immagine QGIS):
    docker run --rm --memory=1500m -e QT_QPA_PLATFORM=offscreen \
      -e PYTHONPATH=/repo:/usr/share/qgis/python --entrypoint python3 \
      -v "$PWD":/repo:ro qgis/qgis:stable /repo/scripts/e2e_filegdb.py
"""
from __future__ import annotations

import os
import shutil
import sys
import tempfile

REPO = os.environ.get("REPO", "/repo")
sys.path.insert(0, REPO)

from osgeo import ogr  # noqa: E402

from qgis.core import QgsApplication, QgsProject, QgsVectorLayer  # noqa: E402

from gdb_attacher.core import attach, naming  # noqa: E402

esiti = []
GUID_1 = "1A2B3C4D-5E6F-7A8B-9C0D-1E2F3A4B5C6D"
GUID_2 = "0F1E2D3C-4B5A-6978-8796-A5B4C3D2E1F0"


def registra(nome, ok, dettaglio=""):
    esiti.append((nome, ok, dettaglio))
    print(f"[{'PASS' if ok else 'FAIL'}] {nome}: {dettaglio}")


def crea_gdb(cartella):
    """Crea un FileGDB con un layer di punti e la sua tabella allegati."""
    percorso = os.path.join(cartella, "Pozzetti.gdb")
    driver = ogr.GetDriverByName("OpenFileGDB")
    ds = driver.CreateDataSource(percorso)

    layer = ds.CreateLayer("Pozzetti", geom_type=ogr.wkbPoint)
    campo = ogr.FieldDefn("GLOBALID", ogr.OFTString)
    campo.SetWidth(38)
    layer.CreateField(campo)
    layer.CreateField(ogr.FieldDefn("CODICE", ogr.OFTString))

    for guid, codice in ((GUID_1, "PZ001"), (GUID_2, "PZ002")):
        feature = ogr.Feature(layer.GetLayerDefn())
        feature.SetField("GLOBALID", guid)
        feature.SetField("CODICE", codice)
        geometria = ogr.Geometry(ogr.wkbPoint)
        geometria.AddPoint(11.1, 46.0)
        feature.SetGeometry(geometria)
        layer.CreateFeature(feature)

    # Tabella allegati: i 6 campi del plugin (l'OID lo aggiunge GDAL da sé).
    tipi = {
        "GLOBALID": ogr.OFTString,
        "REL_GLOBALID": ogr.OFTString,
        "CONTENT_TYPE": ogr.OFTString,
        "ATT_NAME": ogr.OFTString,
        "DATA_SIZE": ogr.OFTInteger64,
        "DATA": ogr.OFTBinary,
    }
    tabella = ds.CreateLayer("Pozzetti__ATTACH", geom_type=ogr.wkbNone)
    for nome, tipo in tipi.items():
        campo = ogr.FieldDefn(nome, tipo)
        if tipo == ogr.OFTString:
            campo.SetWidth(255)
        tabella.CreateField(campo)

    ds = None  # chiude e scrive su disco
    return percorso


def _come_bytes(valore):
    """Normalizza quello che il driver restituisce per un campo binario.

    Nota verificata con un esperimento di controllo (scripts/probe_blob_gdal.py):
    il driver OpenFileGDB restituisce i campi binari da ``GetField`` come **testo
    esadecimale** (1024 byte → 2048 caratteri), non come ``bytes``. Senza questa
    decodifica un blob corretto sembra sbagliato.
    """
    if valore is None:
        return b""
    if isinstance(valore, memoryview):
        return valore.tobytes()
    if isinstance(valore, (bytes, bytearray)):
        return bytes(valore)
    if isinstance(valore, str):
        testo = valore
        if testo and len(testo) % 2 == 0 and all(c in "0123456789abcdefABCDEF" for c in testo):
            return bytes.fromhex(testo)
        return testo.encode("latin-1")
    return bytes(valore)


def conta_allegati(percorso):
    """Rilegge il GDB con GDAL (indipendente da QGIS) e ritorna le righe."""
    ds = ogr.Open(percorso, 0)
    tabella = ds.GetLayerByName("Pozzetti__ATTACH")
    righe = []
    for feature in tabella:
        righe.append({
            "GLOBALID": feature.GetField("GLOBALID"),
            "REL_GLOBALID": feature.GetField("REL_GLOBALID"),
            "CONTENT_TYPE": feature.GetField("CONTENT_TYPE"),
            "ATT_NAME": feature.GetField("ATT_NAME"),
            "DATA_SIZE": feature.GetField("DATA_SIZE"),
            "DATA": _come_bytes(feature.GetField("DATA")),
        })
    ds = None
    return righe


def main():
    cartella = tempfile.mkdtemp(prefix="e2e_gdb_")
    try:
        # Cartella foto con un file vero.
        foto_dir = os.path.join(cartella, "foto")
        os.makedirs(foto_dir)
        contenuto = bytes(range(256)) * 4  # 1024 byte con tutti i valori possibili
        foto = os.path.join(foto_dir, "foto d'interno.jpg")  # nome con apice e spazio
        with open(foto, "wb") as f:
            f.write(contenuto)

        percorso_gdb = crea_gdb(cartella)
        print(f"GDB creato: {percorso_gdb}")

        # --- QGIS ---
        QgsApplication.setPrefixPath("/usr", True)
        app = QgsApplication.instance() or QgsApplication([], False)
        if not QgsApplication.instance():
            app.initQgis()
        progetto = QgsProject.instance()

        def carica(tabella, alias):
            layer = QgsVectorLayer(f"{percorso_gdb}|layername={tabella}", alias, "ogr")
            if not layer.isValid():
                raise RuntimeError(f"QGIS non carica {tabella} dal GDB")
            return layer

        sorgente = carica("Pozzetti", "Pozzetti")
        allegati = carica("Pozzetti__ATTACH", "Pozzetti__ATTACH")
        progetto.addMapLayers([sorgente, allegati])

        # 1. verifica del plugin
        esito = attach.verifica_completa(progetto, sorgente)
        problemi = [getattr(p, "codice", str(p)) for p in esito.problemi]
        registra(
            "verifica del plugin su FileGDB reale",
            not esito.bloccante,
            f"filegdb={esito.layer.e_filegdb} globalid={esito.layer.campo_globalid!r} "
            f"scrivibile={esito.layer.e_scrivibile} tabella={esito.tabella is not None} "
            f"problemi={problemi}",
        )
        if esito.bloccante:
            return 1

        # 2. scrittura di un allegato vero
        righe = [naming.RigaSorgente(id_parent=GUID_1, campo_foto="FOTO",
                                     valore="foto d'interno.jpg", indice_feature=1)]
        risolutore = lambda token: os.path.join(foto_dir, token) \
            if os.path.isfile(os.path.join(foto_dir, token)) else ""
        candidati = naming.risolvi_collisioni(
            naming.candidati_da_campi(righe, risolutore, naming.MODALITA_ORIGINALE),
            esistenti=attach.carica_chiavi_esistenti(allegati),
        )
        statistica = attach.scrivi_allegati(allegati, candidati)
        registra("scrittura di un allegato", statistica.aggiunti == 1,
                 f"aggiunti={statistica.aggiunti} errori={statistica.errori}")

        lette = conta_allegati(percorso_gdb)
        registra("una sola riga scritta", len(lette) == 1, f"righe nella tabella: {len(lette)}")
        if not lette:
            return 1

        riga = lette[0]
        registra("ATT_NAME verbatim (apice e spazi conservati)",
                 riga["ATT_NAME"] == "foto d'interno.jpg", f"ATT_NAME={riga['ATT_NAME']!r}")
        registra("CONTENT_TYPE dedotto dall'estensione",
                 riga["CONTENT_TYPE"] == "image/jpeg", f"CONTENT_TYPE={riga['CONTENT_TYPE']!r}")
        registra("DATA_SIZE uguale alla dimensione reale del file",
                 int(riga["DATA_SIZE"] or 0) == len(contenuto),
                 f"DATA_SIZE={riga['DATA_SIZE']} file={len(contenuto)}")
        registra("blob identico al file su disco", riga["DATA"] == contenuto,
                 f"byte letti: {len(riga['DATA'])}")
        registra("REL_GLOBALID maiuscolo e con graffe",
                 riga["REL_GLOBALID"] == "{" + GUID_1 + "}", f"REL_GLOBALID={riga['REL_GLOBALID']!r}")
        registra("GLOBALID dell'allegato: maiuscolo e senza graffe",
                 bool(riga["GLOBALID"]) and riga["GLOBALID"] == riga["GLOBALID"].upper()
                 and "{" not in riga["GLOBALID"], f"GLOBALID={riga['GLOBALID']!r}")

        # 3. deduplica: rilanciando lo stesso lavoro non si duplica
        allegati.reload()
        candidati2 = naming.risolvi_collisioni(
            naming.candidati_da_campi(righe, risolutore, naming.MODALITA_ORIGINALE),
            esistenti=attach.carica_chiavi_esistenti(allegati),
        )
        statistica2 = attach.scrivi_allegati(allegati, candidati2)
        lette2 = conta_allegati(percorso_gdb)
        registra("deduplica: rilancio senza doppioni",
                 len(lette2) == 1 and statistica2.aggiunti == 0,
                 f"righe={len(lette2)} aggiunti={statistica2.aggiunti} duplicati={statistica2.duplicati}")

        # 4. annullo a metà batch: nessuna scrittura parziale
        #    L'annullo non solleva eccezioni: il wizard legge `statistica.annullata`.
        righe2 = [naming.RigaSorgente(id_parent=GUID_2, campo_foto="FOTO",
                                      valore="foto d'interno.jpg", indice_feature=1)]
        candidati3 = naming.risolvi_collisioni(
            naming.candidati_da_campi(righe2, risolutore, naming.MODALITA_ORIGINALE),
            esistenti=attach.carica_chiavi_esistenti(allegati),
        )
        statistica3 = attach.scrivi_allegati(
            allegati, candidati3, callback_progresso=lambda *a: False,
        )
        lette3 = conta_allegati(percorso_gdb)
        registra("annullo durante il batch: nessuna scrittura parziale",
                 statistica3.annullata and statistica3.aggiunti == 0
                 and len(lette3) == 1 and lette3[0]["DATA"] == contenuto,
                 f"annullata={statistica3.annullata} aggiunti={statistica3.aggiunti} "
                 f"righe={len(lette3)}")
        return 0
    finally:
        shutil.rmtree(cartella, ignore_errors=True)


if __name__ == "__main__":
    codice = main()
    falliti = [n for n, ok, _ in esiti if not ok]
    print("=" * 68)
    print(f"RIEPILOGO: {len(esiti) - len(falliti)}/{len(esiti)} controlli superati")
    if falliti:
        print("FALLITI: " + ", ".join(falliti))
    sys.exit(1 if falliti or codice else 0)
