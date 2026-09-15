# test_fake_qgis.py — verifica che il finto QGIS regga il carico.
#
# Questi test non provano il plugin: provano l'IMPALCATURA. Se il finto QGIS non
# si comporta come QGIS, ogni test scritto sopra e' una bugia, quindi va testato
# per primo. Girano su una macchina senza QGIS e senza GDAL.
#
# Marcatura: tutti `unit` (logica pura, nessun I/O GIS reale).

from __future__ import annotations

import sys

import pytest

from fake_qgis import (
    GUID_1, NULL, QByteArray, QgsMapLayerType, crea_layer_attach,
    crea_layer_sorgente, crea_feature,
)

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# I moduli finti sono importabili con i nomi che usa il codice QGIS

def test_moduli_finti_importabili():
    import qgis
    import qgis.core
    import qgis.gui
    import qgis.utils
    from qgis.core import QgsFeature, QgsFields, QgsProject, QgsVectorLayer, edit
    from qgis.PyQt.QtCore import QByteArray as QA, Qt
    from qgis.PyQt.QtGui import QCursor
    from qgis.PyQt.QtWidgets import QFileDialog, QInputDialog, QMessageBox

    assert qgis.core is sys.modules["qgis.core"]
    assert callable(edit)
    for oggetto in (QgsFeature, QgsFields, QgsProject, QgsVectorLayer, QA, Qt,
                    QCursor, QFileDialog, QInputDialog, QMessageBox):
        assert oggetto is not None


def test_qgis_non_e_installato_davvero():
    """Il test sopra vale solo se QGIS vero non c'e': lo dichiariamo esplicitamente."""
    import qgis
    assert getattr(qgis, "__fake_qgis__", False) is True


def test_simbolo_sconosciuto_diventa_stub():
    """Un import non previsto non deve far fallire la raccolta dei test."""
    from qgis.core import QgsPippoInesistente
    from qgis.PyQt.QtWidgets import QWidgetMaiSentito

    assert QgsPippoInesistente() is not None
    assert QWidgetMaiSentito() is not None


def test_metaclasse_enum_crea_costanti_al_volo():
    from qgis.core import Qgis
    prima = Qgis.LayerType.Vector
    assert Qgis.LayerType.VettorialeNonEsiste is not None
    assert Qgis.LayerType.Vector == prima      # le costanti dichiarate non cambiano


# ---------------------------------------------------------------------------
# Campi, feature, NULL

def test_campi_e_tipi():
    layer = crea_layer_sorgente()
    campi = layer.fields()
    assert campi.names() == ["GLOBALID", "Nome", "filefoto", "FOTO_EST"]
    assert campi[0].name() == "GLOBALID"
    assert campi["filefoto"].typeName() == "String"
    assert campi.indexFromName("filefoto") == 2
    assert campi.indexFromName("non_esiste") == -1
    assert "GLOBALID" in campi
    assert campi.at(1).alias() == "Nome"


def test_tipi_metaqt_leggibili_dallo_pseudo_codice_plugin():
    """Il pattern `campo.type() in (QMetaType.Type.QString, ...)` deve funzionare."""
    from qgis.PyQt.QtCore import QMetaType
    layer = crea_layer_attach()
    tipi = {c.name(): c.type() for c in layer.fields()}
    assert tipi["ATT_NAME"] == QMetaType.Type.QString
    assert tipi["DATA"] == QMetaType.Type.QByteArray
    assert tipi["DATA_SIZE"] not in (QMetaType.Type.QString, QMetaType.Type.QByteArray)


def test_feature_legge_e_scrive_per_nome_e_indice():
    campi = crea_layer_sorgente().fields()
    feat = crea_feature(campi, {"GLOBALID": GUID_1, "filefoto": "SS_0001.jpg"})
    assert feat["GLOBALID"] == GUID_1
    assert feat.attribute("filefoto") == "SS_0001.jpg"
    assert feat.attribute(2) == "SS_0001.jpg"
    feat["Nome"] = "pozzetto"
    feat.setAttribute(3, "EST")
    assert feat[1] == "pozzetto"
    assert feat["FOTO_EST"] == "EST"
    assert feat[0] == GUID_1


def test_campo_non_valorizzato_e_null_e_falsy():
    campi = crea_layer_sorgente().fields()
    feat = crea_feature(campi, {"GLOBALID": GUID_1})
    valore = feat["filefoto"]
    assert valore == NULL
    assert not valore
    assert valore is not None
    assert str(valore) == "NULL"


def test_accesso_a_campo_inesistente_solleva_keyerror():
    feat = crea_feature(crea_layer_sorgente().fields(), {})
    with pytest.raises(KeyError):
        _ = feat["campo_che_non_esiste"]


# ---------------------------------------------------------------------------
# Layer, edit(), progetto

def test_layer_itera_feature_e_conta():
    layer = crea_layer_sorgente()
    assert layer.featureCount() == 2
    globalids = [f["GLOBALID"] for f in layer.getFeatures()]
    assert globalids[0] == GUID_1


def test_edit_aggiunge_al_commit():
    from qgis.core import edit

    layer = crea_layer_attach()
    campi = layer.fields()
    with edit(layer):
        layer.addFeature(crea_feature(campi, {"ATT_NAME": "SS_0001.jpg"}))
    assert layer.featureCount() == 1


def test_edit_annulla_su_eccezione():
    from qgis.core import edit

    layer = crea_layer_attach()
    campi = layer.fields()
    with pytest.raises(RuntimeError):
        with edit(layer):
            layer.addFeature(crea_feature(campi, {"ATT_NAME": "prima.jpg"}))
            raise RuntimeError("errore a meta' scrittura")
    assert layer.featureCount() == 0        # rollback: nessuna scrittura parziale
    assert layer.isEditable() is False


def test_addfeature_assegna_un_fid():
    layer = crea_layer_attach()
    feat = crea_feature(layer.fields(), {"ATT_NAME": "a.jpg"})
    assert layer.addFeature(feat) is True
    assert feat.id() >= 1


def test_progetto_registra_e_ritrova_i_layer(progetto, progetto_con_layer):
    assert len(progetto.mapLayers()) == 2
    assert progetto.mapLayersByName("fotorilievo")[0] is progetto_con_layer["sorgente"]
    attach = progetto.mapLayersByName("fotorilievo" + "__ATTACH")[0]
    assert attach is progetto_con_layer["allegati"]
    assert progetto.mapLayersByName("non_esiste") == []


def test_progetto_con_layer_chiavi_attese(progetto_con_layer):
    assert set(progetto_con_layer) == {"progetto", "sorgente", "allegati"}


def test_layer_type_usa_le_costanti_di_classe():
    """I due script in repo confrontano `lyr.type() == lyr.VectorLayer`."""
    layer = crea_layer_sorgente()
    assert layer.type() == layer.VectorLayer
    assert layer.VectorLayer == QgsMapLayerType.VectorLayer


def test_metodo_qgis_non_implementato_finisce_nel_registro():
    layer = crea_layer_sorgente()
    layer.impostaUnQualcosaDiAssurdo(42)
    assert layer.chiamate_sconosciute[0][0] == "impostaUnQualcosaDiAssurdo"


# ---------------------------------------------------------------------------
# QByteArray e dialoghi

def test_qbytearray_confronta_con_bytes():
    dati = b"\x89PNG\x00finto"
    ba = QByteArray(dati)
    assert bytes(ba) == dati
    assert ba == dati
    assert ba.data() == dati
    assert len(ba) == len(dati)
    assert ba.size() == len(dati)


def test_qbytearray_vuoto_e_vuoto():
    assert QByteArray().isEmpty() is True
    assert len(QByteArray()) == 0


def test_messagebox_registra_e_non_blocca(dialoghi):
    from qgis.PyQt.QtWidgets import QMessageBox
    QMessageBox.warning(None, "Attenzione", "campo foto vuoto")
    assert dialoghi[-1]["tipo"] == "warning"
    assert "campo foto vuoto" in dialoghi[-1]["testo"]


def test_inputdialog_getitem_dalla_coda(risposte_dialoghi):
    from qgis.PyQt.QtWidgets import QInputDialog
    risposte_dialoghi.item.append(("fotorilievo", True))
    assert QInputDialog.getItem(None, "Layer", "Scegli", ["a", "b"], 0, False) == \
        ("fotorilievo", True)
    # senza coda: prima voce, esito True
    assert QInputDialog.getItem(None, "Layer", "Scegli", ["a", "b"], 0, False) == ("a", True)


def test_filedialog_senza_coda_annulla():
    from qgis.PyQt.QtWidgets import QFileDialog
    assert QFileDialog.getExistingDirectory(None, "Cartella") == ""


# ---------------------------------------------------------------------------
# Prova end-to-end: uno script "del plugin" gira senza QGIS

SCRIPT_PROVA = '''
import os

from qgis.PyQt.QtCore import QByteArray
from qgis.core import QgsFeature, QgsProject, edit

ATTESI = ("GLOBALID", "REL_GLOBALID", "CONTENT_TYPE", "DATA_SIZE", "ATT_NAME", "DATA")


def allega(attach_layer, rel_globalid, nome_file, contenuto, content_type="image/jpeg"):
    """Stessa forma dei due script in repo: context manager edit() + addFeature."""
    with edit(attach_layer):
        nuova = QgsFeature(attach_layer.fields())
        nuova["GLOBALID"] = "AABBCCDD-1111-2222-3333-444455556666"
        nuova["REL_GLOBALID"] = rel_globalid
        nuova["CONTENT_TYPE"] = content_type
        nuova["DATA_SIZE"] = len(contenuto)
        nuova["ATT_NAME"] = nome_file
        nuova["DATA"] = QByteArray(contenuto)
        return attach_layer.addFeature(nuova)


def campo_mancante(layer):
    nomi = set(layer.fields().names())
    return [c for c in ATTESI if c not in nomi]


def registra(progetto, layer):
    progetto.addMapLayer(layer)
    return QgsProject.instance().mapLayersByName(layer.name())[0] is layer
'''


def test_script_plugin_gira_senza_qgis(tmp_path, carica_modulo):
    """Uno script che importa qgis.* gira davvero: prova che l'impalcatura basta."""
    percorso = tmp_path / "modulo_prova.py"
    percorso.write_text(SCRIPT_PROVA, encoding="utf-8")

    modulo = carica_modulo(str(percorso), nome_modulo="modulo_prova_end_to_end")

    from fake_qgis import FakeProject
    attach = crea_layer_attach(nome="fotorilievo__ATTACH")
    assert modulo.campo_mancante(attach) == []
    assert modulo.registra(FakeProject.instance(), attach) is True

    dati = b"\xff\xd8\xff\xe0contenuto-finto"
    ok = modulo.allega(attach, "{%s}" % GUID_1, "SS_0001.jpg", dati)
    assert ok is True
    assert attach.featureCount() == 1
    riga = next(attach.getFeatures())
    assert riga["DATA"] == dati
    assert riga["DATA_SIZE"] == len(dati)
    assert riga["REL_GLOBALID"] == "{%s}" % GUID_1
