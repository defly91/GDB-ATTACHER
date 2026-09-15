#!/usr/bin/env python3
"""Esperimento di controllo: un blob scritto e riletto con SOLO GDAL.

Serve a distinguere due cose quando un blob non torna:
  - il driver/il mio modo di leggere sbaglia (allora anche la scrittura diretta GDAL
    mostra lo stesso comportamento);
  - la scrittura fatta da QGIS (``QByteArray`` nell'edit buffer) produce un blob
    diverso da quello scritto (allora qui il giro è pulito e il problema è a monte).

Non fa parte del plugin: è un attrezzo di diagnosi, si lancia a mano.
"""
import os
import tempfile

from osgeo import ogr

contenuto = bytes(range(256)) * 4

cartella = tempfile.mkdtemp(prefix="probe_blob_")
percorso = os.path.join(cartella, "Probe.gdb")
driver = ogr.GetDriverByName("OpenFileGDB")
ds = driver.CreateDataSource(percorso)
tabella = ds.CreateLayer("Probe__ATTACH", geom_type=ogr.wkbNone)
for nome, tipo in (("ATT_NAME", ogr.OFTString), ("DATA_SIZE", ogr.OFTInteger64),
                   ("DATA", ogr.OFTBinary)):
    campo = ogr.FieldDefn(nome, tipo)
    if tipo == ogr.OFTString:
        campo.SetWidth(255)
    tabella.CreateField(campo)

feature = ogr.Feature(tabella.GetLayerDefn())
feature.SetField("ATT_NAME", "prova.jpg")
feature.SetField("DATA_SIZE", len(contenuto))
feature.SetField("DATA", contenuto)
tabella.CreateFeature(feature)

# Rilettura con un datasource nuovo, come farebbe un verificatore esterno.
ds = None
ds = ogr.Open(percorso, 0)
tabella = ds.GetLayerByName("Probe__ATTACH")
for f in tabella:
    valore = f.GetField("DATA")
    print("tipo restituito:", type(valore).__name__)
    print("lunghezza scritta:", len(contenuto), "| lunghezza letta:", len(valore))
    if isinstance(valore, bytes):
        print("primi byte letti:", valore[:16].hex())
        print("uguale all'originale:", valore == contenuto)
    else:
        print("prime posizioni:", repr(valore[:16]))
        print("come latin-1:", valore.encode("latin-1")[:16].hex())
        print("uguale all'originale (latin-1):", valore.encode("latin-1") == contenuto)
        print("uguale all'originale (utf-8)  :", valore.encode("utf-8", "surrogateescape") == contenuto)
ds = None
print("cartella:", cartella)
