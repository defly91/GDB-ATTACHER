# genera_esempi.py — PROTOTIPO throwaway (ticket 05)
# "Layer di esempio + cartella foto finta" per misurare l'euristica suggerisci_campi().
#
# ESECUZIONE (headless):
#   "C:/Program Files/QGIS 3.44.4/apps/Python312/python.exe" con
#   PYTHONPATH="C:\Program Files QGIS...\apps\qgis\python" genera_esempi.py
#
# OUTPUT (in questa cartella):
#   foto/...                      cartella base finta (file jpg/pdf reali, minuscoli)
#   discovery_esempi.gpkg         3 layer di esempio (contatore / superficie / docs)
#   attesi.json                   verita' attesa (campi foto + trappole) per la misura
#
# Perche' dati sintetici: la mappa ha in "Not yet specified" la "strategia test senza
# GDB reale". Qui NON serve un GDB: la discovery legge solo campi e valori.

import base64
import json
import os
import shutil

BASE = os.path.dirname(os.path.abspath(__file__))
FOTO_DIR = os.path.join(BASE, "foto")
GPKG = os.path.join(BASE, "discovery_esempi.gpkg")
ATTESI = os.path.join(BASE, "attesi.json")

PNG_1PX = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
)
PDF_MIN = b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\ntrailer<</Root 1 0 R>>\n%%EOF\n"

GUID = "{A1B2C3D4-E5F6-47A8-B9C0-D1E2F3A4B5%02d}"


def _scrivi_file():
    if os.path.isdir(FOTO_DIR):
        shutil.rmtree(FOTO_DIR)
    gruppi = {
        "contatore": [f"ACQ_{i:04d}.jpg" for i in range(1, 11)],      # 10 file
        "sottosuolo": [f"SS_{i:04d}.jpg" for i in range(1, 9)],       # 8 file
        "superficie": ([f"EST_{i:04d}.jpg" for i in range(1, 9)]
                       + [f"INT_{i:04d}.jpg" for i in range(1, 9)]),  # 16 file
    }
    for sotto, nomi in gruppi.items():
        d = os.path.join(FOTO_DIR, sotto)
        os.makedirs(d, exist_ok=True)
        for n in nomi:
            with open(os.path.join(d, n), "wb") as f:
                f.write(PNG_1PX)
    docs = os.path.join(FOTO_DIR, "docs")
    os.makedirs(docs, exist_ok=True)
    for i in range(1, 9):
        with open(os.path.join(docs, f"planimetria_{i:02d}.pdf"), "wb") as f:
            f.write(PDF_MIN)
    with open(os.path.join(docs, "relazione.pdf"), "wb") as f:
        f.write(PDF_MIN)


# --------------------------------------------------------------- dati dei layer

def _dati_contatore():
    assoluto = os.path.join(FOTO_DIR, "contatore", "ACQ_0010.jpg").replace("\\", "/")
    filefoto = ([f"contatore/ACQ_{i:04d}.jpg" for i in range(1, 10)]
                + [assoluto, "contatore/ACQ_0099.jpg", None])
    note = ["sopralluogo regolare"] * 10 + ["manca la foto contatore/ACQ_0099.jpg", "verificare"]
    foto_note = ["ok", "da controllare", "ok", "ok", "da rifare", "ok",
                 "ok", "controllata", "ok", "ok", "ok", "da controllare"]
    return {
        "nome": "Ril_ApFp_contatore",
        "campi": [
            ("GlobalID", "stringa"), ("filefoto", "stringa"), ("foto_note", "stringa"),
            ("note", "stringa"), ("codice", "stringa"), ("nome_operatore", "stringa"),
            ("quota", "double"), ("data_rilievo", "datetime"),
        ],
        "valori": {
            "GlobalID": [GUID % i for i in range(1, 13)],
            "filefoto": filefoto,
            "foto_note": foto_note,
            "note": note,
            "codice": [f"ACQ-{i:04d}" for i in range(1, 13)],
            "nome_operatore": ["M. Rossi", "L. Bianchi"] * 6,
            "quota": [round(120.5 + i * 0.7, 2) for i in range(12)],
            "data_rilievo": [f"2026-03-{i:02d}" for i in range(1, 13)],
        },
    }


def _dati_superficie():
    foto_est = ([f"superficie/EST_{i:04d}.jpg" for i in range(1, 9)]
                + ["superficie/EST_0099.jpg", "superficie/EST_0098.jpg", None, None])
    foto_int = ([f"superficie/INT_{i:04d}.jpg" for i in range(1, 9)]
                + ["superficie/INT_0099.jpg", "superficie/INT_0098.jpg", None, None])
    foto_impianto = ([f"SS_{i:04d}" for i in range(1, 9)]
                     + ["SS_0099", "SS_0098", None, None])
    return {
        "nome": "Ril_ApFp_superficie",
        "campi": [
            ("GLOBALID", "stringa"), ("FOTO_EST", "stringa"), ("FOTO_INT", "stringa"),
            ("foto_impianto", "stringa"), ("link_foto", "stringa"), ("id_foto", "stringa"),
            ("foto_archiviata", "stringa"), ("data_foto", "date"),
        ],
        "valori": {
            "GLOBALID": [GUID % i for i in range(21, 33)],
            "FOTO_EST": foto_est,
            "FOTO_INT": foto_int,
            "foto_impianto": foto_impianto,
            "link_foto": [f"https://esempio.it/foto/EST_{i:04d}.jpg" for i in range(1, 13)],
            "id_foto": [str(i) for i in range(1, 13)],
            "foto_archiviata": [None] * 12,
            "data_foto": [f"2026-04-{i:02d}" for i in range(1, 13)],
        },
    }


def _dati_docs():
    doc = ([f"docs/planimetria_{i:02d}.pdf" for i in range(1, 9)]
           + ["docs/planimetria_99.pdf", "docs/planimetria_98.pdf", None, None])
    multipli = (["superficie/EST_0001.jpg;superficie/INT_0001.jpg"] * 6
                + ["docs/relazione.pdf"] * 2
                + ["superficie/EST_0099.jpg"] * 2
                + [None, None])
    descrizione = ["impianto conforme"] * 5 + ["vedi foto superficie/EST_0001.jpg"] + ["ok"] * 6
    return {
        "nome": "Ril_ApFp_docs",
        "campi": [
            ("GLOBALID", "stringa"), ("doc_allegato", "stringa"), ("foto_multiple", "stringa"),
            ("riferimento_relazione", "stringa"), ("descrizione", "stringa"),
            ("note_doc", "stringa"), ("data_doc", "date"),
        ],
        "valori": {
            "GLOBALID": [GUID % i for i in range(41, 53)],
            "doc_allegato": doc,
            "foto_multiple": multipli,
            "riferimento_relazione": doc,
            "descrizione": descrizione,
            "note_doc": ["archiviato"] * 12,
            "data_doc": [f"2026-05-{i:02d}" for i in range(1, 13)],
        },
    }


VERITA = {
    "Ril_ApFp_contatore": {
        "attesi": ["filefoto"],
        "trappole": ["GlobalID", "note", "codice", "nome_operatore", "quota", "data_rilievo"],
        "trappole_soft_ammesse": ["foto_note"],
    },
    "Ril_ApFp_superficie": {
        "attesi": ["FOTO_EST", "FOTO_INT", "foto_impianto"],
        "trappole": ["GLOBALID", "link_foto", "id_foto", "foto_archiviata", "data_foto"],
        "trappole_soft_ammesse": [],
    },
    "Ril_ApFp_docs": {
        "attesi": ["doc_allegato", "foto_multiple", "riferimento_relazione"],
        "trappole": ["GLOBALID", "descrizione", "note_doc", "data_doc"],
        "trappole_soft_ammesse": [],
    },
}


# --------------------------------------------------------------- scrittura GPKG

def _tipo_qt(t):
    from qgis.PyQt.QtCore import QMetaType
    return {
        "stringa": QMetaType.Type.QString,
        "double": QMetaType.Type.Double,
        "datetime": QMetaType.Type.QDateTime,
        "date": QMetaType.Type.QDate,
    }[t]


def _valore_qt(t, v):
    from qgis.PyQt.QtCore import QDate, QDateTime, QVariant
    if v is None:
        return QVariant()
    if t == "double":
        return float(v)
    if t == "date":
        return QDate.fromString(v, "yyyy-MM-dd")
    if t == "datetime":
        return QDateTime(QDate.fromString(v, "yyyy-MM-dd"))
    return str(v)


def _scrivi_gpkg(spec):
    from qgis.core import (QgsVectorLayer, QgsField, QgsFeature, QgsGeometry,
                           QgsPointXY, QgsVectorFileWriter, QgsCoordinateTransformContext)
    if os.path.exists(GPKG):
        os.remove(GPKG)
    for i, s in enumerate(spec):
        lyr = QgsVectorLayer("Point?crs=EPSG:4326", s["nome"], "memory")
        assert lyr.isValid(), "layer memoria non valido"
        lyr.dataProvider().addAttributes([QgsField(n, _tipo_qt(t)) for n, t in s["campi"]])
        lyr.updateFields()
        feats = []
        for k in range(12):
            f = QgsFeature(lyr.fields())
            f.setGeometry(QgsGeometry.fromPointXY(QgsPointXY(11.0 + k * 0.001, 45.4)))
            for n, t in s["campi"]:
                f[n] = _valore_qt(t, s["valori"][n][k])
            feats.append(f)
        lyr.dataProvider().addFeatures(feats)
        opt = QgsVectorFileWriter.SaveVectorOptions()
        opt.driverName = "GPKG"
        opt.layerName = s["nome"]
        opt.actionOnExistingFile = (
            QgsVectorFileWriter.CreateOrOverwriteFile if i == 0
            else QgsVectorFileWriter.CreateOrOverwriteLayer)
        err, msg, _, _ = QgsVectorFileWriter.writeAsVectorFormatV3(
            lyr, GPKG, QgsCoordinateTransformContext(), opt)
        assert err == QgsVectorFileWriter.NoError, f"scrittura GPKG fallita: {msg}"


def genera_tutto() -> int:
    """Scrive cartella foto + GPKG + attesi.json. Ritorna il numero di file finti.
    Non inizializza QGIS: il chiamante deve avere gia' un QgsApplication attivo."""
    _scrivi_file()
    spec = [_dati_contatore(), _dati_superficie(), _dati_docs()]
    _scrivi_gpkg(spec)
    with open(ATTESI, "w", encoding="utf-8") as f:
        json.dump(VERITA, f, ensure_ascii=False, indent=2)
    return sum(len(fs) for _, _, fs in os.walk(FOTO_DIR))


def main():
    from qgis.core import QgsApplication
    app = QgsApplication([], False)
    QgsApplication.setPrefixPath(r"C:\Program Files\QGIS 3.44.4\apps\qgis", True)
    QgsApplication.initQgis()
    try:
        n_file = genera_tutto()
        print(f"OK  foto/: {n_file} file   gpkg: {GPKG}   attesi: {ATTESI}")
    finally:
        QgsApplication.exitQgis()


if __name__ == "__main__":
    main()
