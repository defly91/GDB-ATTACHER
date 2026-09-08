# genera_prototipo.py — PROTOTIPO throwaway (ticket 04)
# "Tre varianti di stile QML per la tabella allegati, su GDB di test."
#
# ESECUZIONE (una tantum, per rigenerare i QML):
#   "C:/Program Files/QGIS 3.44.4/apps/Python312/python.exe" con
#   PYTHONPATH='C:\Program Files\QGIS 3.44.4\apps\qgis\python' genera_prototipo.py
# (oppure da console Python di QGIS: exec(open('genera_prototipo.py', encoding='utf-8').read())
#   dopo aver impostato BASE come directory di questo file)
#
# OUTPUT (nella stessa cartella):
#   variante_A_anteprima.qml / variante_B_essenziale.qml / variante_C_blindata.qml
#   test_attach.gdb/  (GDB di test con fotorilievo_test + fotorilievo_test__ATTACH)
#   anteprima_demo.html (anteprima statica dell'HTML del form, apribile con doppio click)

import base64
import os
import shutil
import sys

BASE = os.path.dirname(os.path.abspath(__file__))

# ---------------------------------------------------------------- campioni
# PNG 1x1 rosso (vero file, 70 byte)
PNG_B64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
PNG_RAW = base64.b64decode(PNG_B64)
# Finto PDF (header reale, corpo minimo: basta per il test dello stile, NON un doc valido)
PDF_RAW = b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n2 0 obj<</Type/Pages/Count 0/Kids[]>>endobj\ntrailer<</Root 1 0 R>>\n%%EOF"
# Finto TIFF (header little-endian II*\0 + qualche byte)
TIFF_RAW = b"II*\x00" + bytes(range(64))

CAMPIONI = [
    # (ATT_NAME, CONTENT_TYPE, bytes)
    ("foto_001.jpg", "image/jpeg", PNG_RAW),   # blob piccolo ma con mime jpeg: testa il ramo immagini
    ("rilievo_002.png", "image/png", PNG_RAW),  # ramo immagini
    ("planimetria_003.pdf", "application/pdf", PDF_RAW),  # ramo fallback non-immagini
    ("dettaglio_004.tif", "image/tiff", TIFF_RAW),  # ramo fallback non-immagini
]

GUID_PARENT_1 = "{A1B2C3D4-E5F6-47A8-B9C0-D1E2F3A4B5C6}"
GUID_PARENT_2 = "{B1B2C3D4-E5F6-47A8-B9C0-D1E2F3A4B5D7}"

AZIONE_APRI = """import base64, os, tempfile
from qgis.PyQt.QtCore import QUrl
from qgis.PyQt.QtGui import QDesktopServices
_dati = base64.b64decode('[% to_base64("DATA") %]')
_nome = '[% "ATT_NAME" %]'
_percorso = os.path.join(tempfile.gettempdir(), 'gdb_attacher_' + _nome)
with open(_percorso, 'wb') as _f:
    _f.write(_dati)
QDesktopServices.openUrl(QUrl.fromLocalFile(_percorso))"""

AZIONE_SALVA = """import base64
from qgis.PyQt.QtWidgets import QFileDialog
_dati = base64.b64decode('[% to_base64("DATA") %]')
_percorso, _ = QFileDialog.getSaveFileName(None, 'Salva allegato', '[% "ATT_NAME" %]')
if _percorso:
    with open(_percorso, 'wb') as _f:
        _f.write(_dati)"""

# Singolo elemento HTML: la condizione immagine/fallback vive DENTRO l'espressione
# (gli elementi HTML del form non hanno "visibilita condizionale" propria).
HTML_DOSSIER = """<div style="font-family:sans-serif;max-width:640px">
<h3 style="margin:0 0 4px">[% "ATT_NAME" %]</h3>
<p style="color:#555;margin:0 0 8px">[% "CONTENT_TYPE" %] \u00b7 [% "DATA_SIZE" %] byte</p>
[% CASE WHEN "CONTENT_TYPE" IN ('image/jpeg', 'image/png') THEN '<img src="data:' || "CONTENT_TYPE" || ';base64,' || to_base64("DATA") || '" style="max-width:100%;border:1px solid #ccc"/>' ELSE '<p><i>Nessuna anteprima inline per questo formato. Usa l''azione Apri allegato.</i></p>' END %]
</div>"""

MAPTIP = """<b>[% "ATT_NAME" %]</b> ([% "CONTENT_TYPE" %], [% "DATA_SIZE" %] byte)<br/>[% CASE WHEN "CONTENT_TYPE" IN ('image/jpeg', 'image/png') THEN '<img src="data:' || "CONTENT_TYPE" || ';base64,' || to_base64("DATA") || '" width="300"/>' ELSE '' END %]"""

MIME_MAP = {
    "Immagine JPEG": "image/jpeg",
    "Immagine PNG": "image/png",
    "Immagine TIFF": "image/tiff",
    "Documento PDF": "application/pdf",
    "Video MP4": "video/mp4",
}

ALIAS_IT = {
    "GLOBALID": "ID globale",
    "REL_GLOBALID": "Feature collegata",
    "CONTENT_TYPE": "Tipo contenuto",
    "ATT_NAME": "Nome file",
    "DATA_SIZE": "Dimensione (byte)",
    "DATA": "Dati binari",
}

SCHEMA = ["GLOBALID", "REL_GLOBALID", "CONTENT_TYPE", "ATT_NAME", "DATA_SIZE", "DATA"]


def boot_qgis():
    from qgis.core import QgsApplication
    QgsApplication.setPrefixPath('C:/Program Files/QGIS 3.44.4/apps/qgis', True)
    app = QgsApplication([], False)
    QgsApplication.initQgis()
    from qgis.gui import QgsGui
    QgsGui.editorWidgetRegistry().initEditors()
    return app


def memoria_attach(nome="mem__ATTACH"):
    """Layer memoria SENZA geometria con gli stessi 6 campi della tabella allegati.
    Il None e fondamentale: la tabella allegati non ha geometria e QGIS rifiuta
    QML con layerGeometryType diverso ("geom. sbagliata")."""
    from qgis.core import QgsVectorLayer, QgsField
    from qgis.PyQt.QtCore import QMetaType
    lyr = QgsVectorLayer("None", nome, "memory")
    assert lyr.isValid()
    lyr.dataProvider().addAttributes([
        QgsField("GLOBALID", QMetaType.Type.QString),
        QgsField("REL_GLOBALID", QMetaType.Type.QString),
        QgsField("CONTENT_TYPE", QMetaType.Type.QString),
        QgsField("ATT_NAME", QMetaType.Type.QString),
        QgsField("DATA_SIZE", QMetaType.Type.LongLong),
        QgsField("DATA", QMetaType.Type.QByteArray),
    ])
    lyr.updateFields()
    return lyr


def base_comune(lyr, data_widget="Binary"):
    """Alias IT + widget/valori condivisi da tutte le varianti. Ritorna fidx()."""
    from qgis.core import QgsEditorWidgetSetup
    from qgis.core import Qgis
    def fidx(n):
        return lyr.fields().indexOf(n)
    for nome, alias in ALIAS_IT.items():
        lyr.setFieldAlias(fidx(nome), alias)
    lyr.setEditorWidgetSetup(fidx("CONTENT_TYPE"), QgsEditorWidgetSetup("ValueMap", {"map": MIME_MAP}))
    lyr.setEditorWidgetSetup(fidx("DATA"), QgsEditorWidgetSetup(data_widget, {}))
    # GUID e dimensione: sola lettura nel form (il blob non si tocca mai a mano)
    cfg = lyr.editFormConfig()
    for n in ("GLOBALID", "REL_GLOBALID", "DATA_SIZE"):
        cfg.setReadOnly(fidx(n), True)
    lyr.setEditFormConfig(cfg)
    try:
        lyr.setDisplayExpression('"ATT_NAME"')
    except Exception as e:
        print("  [avviso] displayExpression:", e)
    try:
        lyr.setMapTipTemplate(MAPTIP)
    except Exception as e:
        print("  [avviso] mapTip:", e)
    # nascondi la colonna blob nella tabella attributi
    try:
        from qgis.core import QgsAttributeTableConfig
        tc = lyr.attributeTableConfig()
        cols = tc.columns()
        for c in cols:
            if c.name == "DATA":
                c.hidden = True
        tc.setColumns(cols)
        lyr.setAttributeTableConfig(tc)
    except Exception as e:
        print("  [avviso] colonne tabella:", e)
    # azioni (id stabili per QML leggibile)
    from qgis.PyQt.QtCore import QUuid
    lyr.actions().addAction(Qgis.AttributeActionType.GenericPython, "Apri allegato", AZIONE_APRI, False)
    lyr.actions().addAction(Qgis.AttributeActionType.GenericPython, "Salva allegato con nome…", AZIONE_SALVA, False)
    acts = {a.name(): a.id() for a in lyr.actions().actions()}
    try:
        lyr.actions().setDefaultAction("Feature", acts["Apri allegato"])
    except Exception as e:
        print("  [avviso] azione default:", e)
    return fidx


def variante_A(lyr):
    """A — Anteprima in testa: 2 tab, dossier HTML grande + dati tecnici separati."""
    from qgis.core import (QgsEditFormConfig, QgsAttributeEditorContainer,
                           QgsAttributeEditorField, QgsAttributeEditorHtmlElement)
    from qgis.core import Qgis
    fidx = base_comune(lyr)
    cfg = lyr.editFormConfig()
    cfg.setLayout(QgsEditFormConfig.EditorLayout.TabLayout)
    root = cfg.invisibleRootContainer()
    root.clear()
    tab = QgsAttributeEditorContainer("Anteprima", root)
    tab.setType(Qgis.AttributeEditorContainerType.Tab)
    html = QgsAttributeEditorHtmlElement("DossierFoto", tab)
    html.setHtmlCode(HTML_DOSSIER)
    tab.addChildElement(html)
    for n in ("ATT_NAME", "CONTENT_TYPE", "DATA_SIZE"):
        tab.addChildElement(QgsAttributeEditorField(n, fidx(n), tab))
    root.addChildElement(tab)
    tech = QgsAttributeEditorContainer("Dati tecnici", root)
    tech.setType(Qgis.AttributeEditorContainerType.Tab)
    for n in ("GLOBALID", "REL_GLOBALID", "DATA"):
        tech.addChildElement(QgsAttributeEditorField(n, fidx(n), tech))
    root.addChildElement(tech)
    lyr.setEditFormConfig(cfg)


def variante_B(lyr):
    """B — Essenziale da tabella: un solo gruppo, niente HTML nel form,
    anteprima solo in mapTip (hover) + azione default. Per scansioni massive."""
    from qgis.core import (QgsEditFormConfig, QgsAttributeEditorContainer,
                           QgsAttributeEditorField)
    fidx = base_comune(lyr, data_widget="Hidden")
    cfg = lyr.editFormConfig()
    cfg.setLayout(QgsEditFormConfig.EditorLayout.TabLayout)
    root = cfg.invisibleRootContainer()
    root.clear()
    box = QgsAttributeEditorContainer("Allegato", root)
    for n in ("ATT_NAME", "CONTENT_TYPE", "DATA_SIZE"):
        box.addChildElement(QgsAttributeEditorField(n, fidx(n), box))
    root.addChildElement(box)
    tech = QgsAttributeEditorContainer("Tecnici (non toccare)", root)
    tech.setCollapsed(True)
    for n in ("GLOBALID", "REL_GLOBALID"):
        tech.addChildElement(QgsAttributeEditorField(n, fidx(n), tech))
    root.addChildElement(tech)
    lyr.setEditFormConfig(cfg)


def variante_C(lyr):
    """C — Scheda blindata: 3 tab, ATT_NAME obbligatorio, DATA nascosto,
    pulsante 'Apri allegato' incorporato nel form."""
    from qgis.core import (QgsEditFormConfig, QgsAttributeEditorContainer,
                           QgsAttributeEditorField, QgsAttributeEditorHtmlElement,
                           QgsAttributeEditorTextElement, QgsAttributeEditorAction)
    from qgis.core import Qgis
    fidx = base_comune(lyr, data_widget="Hidden")
    cfg = lyr.editFormConfig()
    cfg.setLayout(QgsEditFormConfig.EditorLayout.TabLayout)
    # ATT_NAME obbligatorio (vincolo form, non toccare il GDB)
    try:
        from qgis.core import QgsFieldConstraints
        lyr.setFieldConstraint(fidx("ATT_NAME"), QgsFieldConstraints.Constraint.ConstraintNotNull,
                               QgsFieldConstraints.ConstraintStrength.ConstraintStrengthHard)
    except Exception as e:
        print("  [avviso] vincolo NotNull:", e)
    root = cfg.invisibleRootContainer()
    root.clear()
    foto = QgsAttributeEditorContainer("Foto", root)
    foto.setType(Qgis.AttributeEditorContainerType.Tab)
    html = QgsAttributeEditorHtmlElement("DossierFoto", foto)
    html.setHtmlCode(HTML_DOSSIER)
    foto.addChildElement(html)
    foto.addChildElement(QgsAttributeEditorField("ATT_NAME", fidx("ATT_NAME"), foto))
    foto.addChildElement(QgsAttributeEditorField("CONTENT_TYPE", fidx("CONTENT_TYPE"), foto))
    # pulsante azione dentro il form
    aid = next(a.id() for a in lyr.actions().actions() if a.name() == "Apri allegato")
    foto.addChildElement(QgsAttributeEditorAction(aid, foto))
    root.addChildElement(foto)
    fil = QgsAttributeEditorContainer("File", root)
    fil.setType(Qgis.AttributeEditorContainerType.Tab)
    fil.addChildElement(QgsAttributeEditorField("DATA_SIZE", fidx("DATA_SIZE"), fil))
    nota = QgsAttributeEditorTextElement("NotaBlob", fil)
    nota.setText("I dati binari non si modificano a mano: usa «Salva allegato con nome…» per estrarli.")
    fil.addChildElement(nota)
    root.addChildElement(fil)
    col = QgsAttributeEditorContainer("Collegamento", root)
    col.setType(Qgis.AttributeEditorContainerType.Tab)
    for n in ("GLOBALID", "REL_GLOBALID"):
        col.addChildElement(QgsAttributeEditorField(n, fidx(n), col))
    root.addChildElement(col)
    lyr.setEditFormConfig(cfg)


def crea_gdb_test(percorso):
    """GDB di test (solo nomi-campi fedeli, per provare i QML).

    ATTENZIONE: tabella creata via GDAL = SENZA __ATTACHREL e metadati GDB_Items.
    Serve solo a testare gli stili; la vera tabella allegati nasce solo da
    ArcGIS Pro (EnableAttachments) — vedi ticket 02."""
    from osgeo import gdal, ogr
    gdal.UseExceptions()
    shutil.rmtree(percorso, ignore_errors=True)
    drv = ogr.GetDriverByName("OpenFileGDB")
    ds = drv.CreateDataSource(percorso)
    import uuid as _uuid

    pt = ds.CreateLayer("fotorilievo_test", geom_type=ogr.wkbPoint)
    pt.CreateField(ogr.FieldDefn("GLOBALID", ogr.OFTString))
    pt.CreateField(ogr.FieldDefn("codice", ogr.OFTString))
    for gid, x in [(GUID_PARENT_1.strip("{}").upper(), 1650000.0),
                   (GUID_PARENT_2.strip("{}").upper(), 1650010.0)]:
        f = ogr.Feature(pt.GetLayerDefn())
        f["GLOBALID"] = gid
        f["codice"] = "P" + gid[0:4]
        from osgeo import ogr as _ogr
        f.SetGeometry(_ogr.CreateGeometryFromWkt("POINT (%f 5070000)" % x))
        pt.CreateFeature(f)

    at = ds.CreateLayer("fotorilievo_test__ATTACH", geom_type=ogr.wkbNone)
    at.CreateField(ogr.FieldDefn("GLOBALID", ogr.OFTString))
    at.CreateField(ogr.FieldDefn("REL_GLOBALID", ogr.OFTString))
    at.CreateField(ogr.FieldDefn("CONTENT_TYPE", ogr.OFTString))
    at.CreateField(ogr.FieldDefn("ATT_NAME", ogr.OFTString))
    at.CreateField(ogr.FieldDefn("DATA_SIZE", ogr.OFTInteger))  # int32: niente warning GDAL
    at.CreateField(ogr.FieldDefn("DATA", ogr.OFTBinary))
    data_idx = at.GetLayerDefn().GetFieldIndex("DATA")
    righe = [
        (GUID_PARENT_1, CAMPIONI[0]),
        (GUID_PARENT_1, CAMPIONI[2]),
        (GUID_PARENT_2, CAMPIONI[1]),
        (GUID_PARENT_2, CAMPIONI[3]),
    ]
    for rel, (nome, mime, blob) in righe:
        f = ogr.Feature(at.GetLayerDefn())
        f["GLOBALID"] = str(_uuid.uuid4()).upper()
        f["REL_GLOBALID"] = rel
        f["CONTENT_TYPE"] = mime
        f["ATT_NAME"] = nome
        f["DATA_SIZE"] = len(blob)
        f.SetFieldBinaryFromHexString(data_idx, blob.hex().upper())
        at.CreateFeature(f)
    ds = None
    return len(righe)


def verifica(qml_path, gdb_path):
    """Ricarica il QML su un layer fresco + round-trip base64 sul vero GDB."""
    from qgis.core import QgsVectorLayer, QgsExpression, QgsExpressionContext, QgsExpressionContextUtils
    fresco = memoria_attach("verifica")
    msg, ok = fresco.loadNamedStyle(qml_path)
    assert ok, "loadNamedStyle fallito per %s: %s" % (qml_path, msg)
    tab = QgsVectorLayer(gdb_path + "|layername=fotorilievo_test__ATTACH", "gdb", "ogr")
    assert tab.isValid(), "GDB non apribile: %s" % gdb_path
    assert tab.featureCount() == 4, "righe attese 4, trovate %d" % tab.featureCount()
    import base64 as _b64
    attesi = {n: b for (n, _m, b) in CAMPIONI}
    for feat in tab.getFeatures():
        ctx = QgsExpressionContext()
        ctx.appendScopes(QgsExpressionContextUtils.globalProjectLayerScopes(tab))
        ctx.setFeature(feat)
        e = QgsExpression('to_base64("DATA")')
        v = e.evaluate(ctx)
        assert not e.hasEvalError(), e.evalErrorString()
        assert _b64.b64decode(str(v)) == attesi[feat["ATT_NAME"]], "byte non fedeli per %s" % feat["ATT_NAME"]
        e2 = QgsExpression('CASE WHEN "CONTENT_TYPE" IN (\'image/jpeg\', \'image/png\') THEN 1 ELSE 0 END')
        v2 = e2.evaluate(ctx)
        img = feat["CONTENT_TYPE"] in ("image/jpeg", "image/png")
        assert bool(v2) == img, "ramo CASE WHEN errato per %s" % feat["ATT_NAME"]
    # regressione ticket 04: il QML deve applicarsi alla VERA tabella senza geometria
    msg2, ok2 = tab.loadNamedStyle(qml_path)
    assert ok2, "QML rifiutato dalla tabella GDB (geometria?): %s" % msg2
    return True


def demo_html(gdb):
    """Anteprima statica (doppio click, niente QGIS): l'HTML del form renderizzato
    con il VERO motore QGIS per ognuna delle 4 righe di test."""
    from qgis.core import QgsVectorLayer, QgsExpression, QgsExpressionContext, QgsExpressionContextUtils
    tab = QgsVectorLayer(gdb + "|layername=fotorilievo_test__ATTACH", "gdb", "ogr")
    assert tab.isValid()
    parti = ["<!doctype html><html lang=it><meta charset=utf-8>"
             "<title>Demo anteprima (variante A/C)</title><body>"
             "<h1>Cosi deve apparire il riquadro HTML nel form</h1>"
             "<p>Renderizzato con il motore QGIS reale (stesso del form).</p>"]
    for feat in tab.getFeatures():
        ctx = QgsExpressionContext()
        ctx.appendScopes(QgsExpressionContextUtils.globalProjectLayerScopes(tab))
        ctx.setFeature(feat)
        reso = QgsExpression.replaceExpressionText(HTML_DOSSIER, ctx)
        assert "[%" not in reso, "sostituzione fallita per %s" % feat["ATT_NAME"]
        parti.append("<hr><h2>%s</h2>\n%s" % (feat["ATT_NAME"], reso))
    parti.append("</body></html>\n")
    return "\n".join(parti)


def gdb_valido(percorso):
    """Il GDB di test esiste gia con le 2 tabelle e le 4 righe attese?"""
    try:
        from osgeo import gdal, ogr
        gdal.UseExceptions()
        ds = ogr.Open(percorso)
        if ds is None:
            return False
        nomi = [ds.GetLayer(i).GetName() for i in range(ds.GetLayerCount())]
        if "fotorilievo_test__ATTACH" not in nomi:
            return False
        at = ds.GetLayerByName("fotorilievo_test__ATTACH")
        ok = at.GetFeatureCount() == 4
        ds = None
        return ok
    except Exception:
        return False


def main():
    app = boot_qgis()
    print("== ticket 04: genero prototipo stile ==")
    gdb = os.path.join(BASE, "test_attach.gdb")
    if gdb_valido(gdb):
        print("GDB di test gia presente e valido: riuso (niente ricreazione)")
        n = 4
    else:
        n = crea_gdb_test(gdb)
    print("GDB di test: %s (%d allegati)" % (gdb, n))
    risultati = {}
    for key, fn, fnome in (("A", variante_A, "variante_A_anteprima.qml"),
                           ("B", variante_B, "variante_B_essenziale.qml"),
                           ("C", variante_C, "variante_C_blindata.qml")):
        lyr = memoria_attach()
        fn(lyr)
        out = os.path.join(BASE, fnome)
        msg, ok = lyr.saveNamedStyle(out)
        assert ok, "save fallito: %s" % msg
        verifica(out, gdb)
        print("variante %s OK: %s (reload + 4 round-trip byte fedeli)" % (key, fnome))
        risultati[key] = fnome
    with open(os.path.join(BASE, "anteprima_demo.html"), "w", encoding="utf-8") as f:
        f.write(demo_html(gdb))
    print("demo HTML: anteprima_demo.html (4 casi renderizzati col motore reale)")
    print("== tutto verificato headless ==")
    from qgis.core import QgsApplication
    QgsApplication.exitQgis()


if __name__ == "__main__":
    main()
