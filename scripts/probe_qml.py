#!/usr/bin/env python3
"""Probe mirato: perché QGIS rifiuta il QML di stile del plugin?

Prova il caricamento su layer con e senza geometria, convalida l'XML e stampa il
messaggio d'errore completo, così si distingue un QML rotto da un'incompatibilità
di versione di QGIS.
"""
import os
import sys

QML = os.environ.get("QML", "/repo/gdb_attacher/resources/stile_attach_variante_A.qml")

from qgis.core import Qgis, QgsVectorLayer  # noqa: E402

print("QGIS:", Qgis.QGIS_VERSION)

# 1. XML valido?
from xml.etree import ElementTree as ET  # noqa: E402
try:
    radice = ET.parse(QML).getroot()
    print(f"XML valido. Radice <{radice.tag}>, attributi: {radice.attrib}")
    print("Sezioni:", sorted({figlio.tag for figlio in radice}))
except Exception as e:  # noqa: BLE001
    print("XML NON valido:", e)
    sys.exit(1)

# 2. Caricamento su vari tipi di layer, stampando il messaggio completo.
casi = {
    "tabella senza geometria": "None?field=ATT_NAME:string&field=REL_GLOBALID:string&field=REL_OBJECTID:integer",
    "punto con gli stessi campi": "Point?field=ATT_NAME:string&field=REL_GLOBALID:string",
}
for nome, definizione in casi.items():
    layer = QgsVectorLayer(definizione, "prova", "memory")
    if not layer.isValid():
        print(f"[{nome}] layer non valido")
        continue
    messaggio, ok = layer.loadNamedStyle(QML)
    print(f"[{nome}] ok={ok} messaggio={messaggio!r}")
    if ok:
        print(f"          renderer={layer.renderer().type()}")
        print(f"          campi di labeling/espressioni accettati")
