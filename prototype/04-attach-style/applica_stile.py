# applica_stile.py — PROTOTIPO throwaway (ticket 04)
# Carica la tabella allegati di test e ci applica una delle 3 varianti QML.
#
# USO (console Python di QGIS, 2 righe):
#   exec(open(r'C:/Users/Stefano/Documents/Prove Claude/GDB-ATTACHER/prototype/04-attach-style/applica_stile.py', encoding='utf-8').read())
#   applica('A')   # oppure 'B' o 'C'
#
# Apre anche il form della prima feature, così lo stile si vede subito.

import os

BASE = (os.path.dirname(os.path.abspath(__file__))
        if '__file__' in globals()
        else 'C:/Users/Stefano/Documents/Prove Claude/GDB-ATTACHER/prototype/04-attach-style')

QMLS = {
    'A': 'variante_A_anteprima.qml',
    'B': 'variante_B_essenziale.qml',
    'C': 'variante_C_blindata.qml',
}


def applica(variante='A'):
    from qgis.core import QgsVectorLayer, QgsProject
    key = variante.upper()
    assert key in QMLS, "variante? usa 'A', 'B' o 'C', non %r" % (variante,)
    gdb = os.path.join(BASE, 'test_attach.gdb')
    lyr = QgsVectorLayer(gdb + '|layername=fotorilievo_test__ATTACH',
                         'fotorilievo_test__ATTACH [%s]' % key, 'ogr')
    assert lyr.isValid(), "non apro il GDB di test: %s" % gdb
    msg, ok = lyr.loadNamedStyle(os.path.join(BASE, QMLS[key]))
    print('stile %s applicato: %s (%s), %d allegati' % (key, ok, msg, lyr.featureCount()))
    QgsProject.instance().addMapLayer(lyr)
    try:
        from qgis.utils import iface
        feat = next(lyr.getFeatures())
        iface.openFeatureForm(lyr, feat, False)
    except Exception as e:
        print('form non aperto in automatico (%s): aprilo a mano con Identifica sulla tabella' % e)
    return lyr
