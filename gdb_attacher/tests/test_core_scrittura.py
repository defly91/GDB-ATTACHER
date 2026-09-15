# -*- coding: utf-8 -*-
"""Test della **scrittura** dei 6 campi (``attach.scrivi_allegati``).

``scrivi_allegati`` dipende da QGIS (``QgsFeature``, ``edit()``, ``QByteArray``):
qui quei tre pezzi vengono sostituiti con dei finti messi in ``sys.modules`` per la
durata del test, così si controlla davvero *cosa finisce nelle colonne* senza avere
QGIS installato:

- ``GLOBALID`` uuid uppercase **senza** graffe, ``REL_GLOBALID`` con graffe;
- ``CONTENT_TYPE`` dal mime reale (non hardcoded come nello script batch);
- ``DATA_SIZE`` coerente col blob e ``DATA`` identico ai byte del file;
- ``ATT_NAME`` verbatim, deduplica sulla coppia, annullo = rollback senza commit.

Non serve il ``conftest.py`` di un altro agente: i finti sono installati qui, con
``monkeypatch``, e rimossi a fine test.
"""

import contextlib
import os
import re
import sys

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from gdb_attacher.core import attach, naming  # noqa: E402


# ---------------------------------------------------------------- finti QGIS


class _FintoQgsFeature:
    def __init__(self, fields=None):
        self.valori = {}

    def __setitem__(self, chiave, valore):
        self.valori[chiave] = valore

    def __getitem__(self, chiave):
        return self.valori.get(chiave)


class _FintoQByteArray:
    def __init__(self, dati=b""):
        self.dati = bytes(dati)


class _Corse:
    """Conta commit e rollback del contesto ``edit()``."""

    def __init__(self):
        self.commit = 0
        self.rollback = 0


@pytest.fixture()
def qgis_finto(monkeypatch):
    """Installa i finti di ``qgis.core`` / ``qgis.PyQt.QtCore`` e pulisce a fine test."""
    import types

    corse = _Corse()

    @contextlib.contextmanager
    def _edit(layer):
        try:
            yield
        except Exception:
            corse.rollback += 1
            raise
        corse.commit += 1

    moduli = {}
    core = types.ModuleType("qgis.core")
    core.QgsFeature = _FintoQgsFeature
    core.edit = _edit
    core.QgsVectorDataProvider = type("QgsVectorDataProvider", (), {
        "Capabilities": type("Capabilities", (), {"AddFeatures": 1}),
    })
    qtcore = types.ModuleType("qgis.PyQt.QtCore")
    qtcore.QByteArray = _FintoQByteArray
    pyqt = types.ModuleType("qgis.PyQt")
    pyqt.QtCore = qtcore
    qgis = types.ModuleType("qgis")
    qgis.core = core
    qgis.PyQt = pyqt

    for nome, modulo in (("qgis", qgis), ("qgis.core", core),
                         ("qgis.PyQt", pyqt), ("qgis.PyQt.QtCore", qtcore)):
        monkeypatch.setitem(sys.modules, nome, modulo)

    corse.moduli = moduli
    return corse


class _Campo:
    def __init__(self, nome):
        self._nome = nome

    def name(self):
        return self._nome


class _Campi:
    def __init__(self, nomi):
        self._nomi = list(nomi)

    def __iter__(self):
        return iter(_Campo(n) for n in self._nomi)


class _LayerAllegati:
    """Tabella allegati finta: tiene le righe scritte e le restituisce."""

    def __init__(self, nome="fotorilievo__ATTACH", campi=attach.CAMPI_ALLEGATI):
        self._nome = nome
        self._campi = _Campi(campi)
        self.righe = []

    def name(self):
        return self._nome

    def fields(self):
        return self._campi

    def addFeature(self, feature):
        self.righe.append(feature)
        return True

    def getFeatures(self):
        return list(self.righe)


GUID_PARENT = "8AA1F6C0-1111-2222-3333-444455556666"


def _candidato(nome, percorso, guid=GUID_PARENT, campo="FOTO_EST"):
    return naming.CandidatoAllegato(
        id_parent=guid, campo_foto=campo, valore_campo=nome, token=nome,
        percorso_file=percorso, nome_allegato=nome, nome_originale=nome,
        indice_token=1, indice_feature=1, stato="ok",
    )


@pytest.fixture()
def file_veri(tmp_path):
    (tmp_path / "foto_est.jpg").write_bytes(b"\xff\xd8jpeg-finto")
    (tmp_path / "relazione.pdf").write_bytes(b"%PDF-1.4 finto")
    return tmp_path


# ---------------------------------------------------------------- test


def test_scrittura_dei_sei_campi(qgis_finto, file_veri):
    layer = _LayerAllegati()
    campi = attach.risolvi_campi_allegati(layer)[0]
    candidati = [
        _candidato("foto_est.jpg", str(file_veri / "foto_est.jpg")),
        _candidato("relazione.pdf", str(file_veri / "relazione.pdf"), campo="FOTO_INT"),
    ]

    statistica = attach.scrivi_allegati(layer, candidati, campi=campi)

    assert statistica.aggiunti == 2
    assert statistica.saltati == 0
    assert qgis_finto.commit == 1 and qgis_finto.rollback == 0   # una sola transazione

    prima = layer.righe[0]
    assert re.match(r"^[0-9A-F-]{36}$", prima["GLOBALID"])
    assert "{" not in prima["GLOBALID"] and "-" in prima["GLOBALID"]
    assert prima["REL_GLOBALID"] == "{" + GUID_PARENT + "}"
    assert prima["CONTENT_TYPE"] == "image/jpeg"
    assert prima["ATT_NAME"] == "foto_est.jpg"
    assert prima["DATA_SIZE"] == len(b"\xff\xd8jpeg-finto")
    assert bytes(prima["DATA"].dati) == b"\xff\xd8jpeg-finto"

    secondo = layer.righe[1]
    assert secondo["CONTENT_TYPE"] == "application/pdf"     # mime reale, non image/jpeg
    assert len({riga["GLOBALID"] for riga in layer.righe}) == 2   # GLOBALID mai riusato


def test_dedup_secondo_giro_non_riscrive(qgis_finto, file_veri):
    """Idempotenza: la coppia (REL_GLOBALID, ATT_NAME) già presente viene saltata."""
    layer = _LayerAllegati()
    campi = attach.risolvi_campi_allegati(layer)[0]
    candidato = _candidato("foto_est.jpg", str(file_veri / "foto_est.jpg"))

    attach.scrivi_allegati(layer, [candidato], campi=campi)
    esistenti = attach.carica_chiavi_esistenti(layer, campi)
    assert len(esistenti) == 1

    statistica = attach.scrivi_allegati(layer, [candidato], campi=campi,
                                        chiavi_esistenti=esistenti)
    assert statistica.aggiunti == 0
    assert statistica.duplicati == 1
    assert len(layer.righe) == 1


def test_guid_parent_con_graffe_o_case_non_cambia_la_dedup(qgis_finto, file_veri):
    layer = _LayerAllegati()
    campi = attach.risolvi_campi_allegati(layer)[0]
    percorso = str(file_veri / "foto_est.jpg")
    attach.scrivi_allegati(layer, [_candidato("foto_est.jpg", percorso)], campi=campi)

    esistenti = attach.carica_chiavi_esistenti(layer, campi)
    candidato = _candidato("foto_est.jpg", percorso, guid=GUID_PARENT.lower())
    statistica = attach.scrivi_allegati(layer, [candidato], campi=campi,
                                        chiavi_esistenti=esistenti)
    assert statistica.duplicati == 1


def test_annullo_dalla_barra_progresso_non_committa(qgis_finto, file_veri):
    """Annulla = il GDB resta com'era (ticket 03): nessuna scrittura."""
    layer = _LayerAllegati()
    campi = attach.risolvi_campi_allegati(layer)[0]
    candidato = _candidato("foto_est.jpg", str(file_veri / "foto_est.jpg"))

    statistica = attach.scrivi_allegati(layer, [candidato], campi=campi,
                                        callback_progresso=lambda *a: False)

    assert statistica.annullata is True
    assert statistica.aggiunti == 0
    assert layer.righe == []
    assert qgis_finto.commit == 0 and qgis_finto.rollback == 1


def test_parent_senza_globalid_viene_saltato(qgis_finto, file_veri):
    """Mai scrivere un allegato orfano: senza GlobalID il parent non esiste."""
    layer = _LayerAllegati()
    campi = attach.risolvi_campi_allegati(layer)[0]
    candidato = _candidato("foto_est.jpg", str(file_veri / "foto_est.jpg"), guid="")

    statistica = attach.scrivi_allegati(layer, [candidato], campi=campi)

    assert statistica.aggiunti == 0
    assert statistica.saltati == 1
    assert statistica.errori and "GlobalID" in statistica.errori[0][1]
    assert layer.righe == []


def test_file_sparito_tra_preview_e_scrittura(qgis_finto, file_veri):
    layer = _LayerAllegati()
    campi = attach.risolvi_campi_allegati(layer)[0]
    candidato = _candidato("sparita.jpg", str(file_veri / "sparita.jpg"))

    statistica = attach.scrivi_allegati(layer, [candidato], campi=campi)

    assert statistica.aggiunti == 0 and statistica.saltati == 1
    assert layer.righe == []


def test_tabella_incompleta_solleva(qgis_finto, file_veri):
    """La scrittura non prova nemmeno a riparare una tabella allegati incompleta."""
    layer = _LayerAllegati(campi=["GLOBALID", "ATT_NAME"])
    with pytest.raises(ValueError):
        attach.scrivi_allegati(layer, [_candidato("foto_est.jpg", str(file_veri / "foto_est.jpg"))])


def test_campi_risolti_case_insensitive(qgis_finto, file_veri):
    """ArcGIS/Pro a volte consegna i campi in minuscolo: si risolvono comunque."""
    layer = _LayerAllegati(campi=[c.lower() for c in attach.CAMPI_ALLEGATI])
    campi = attach.risolvi_campi_allegati(layer)[0]
    campi_ordinati = {ruolo: nome for ruolo, nome in campi.items()}
    statistica = attach.scrivi_allegati(layer, [_candidato("foto_est.jpg",
                                                           str(file_veri / "foto_est.jpg"))],
                                        campi=campi_ordinati)
    assert statistica.aggiunti == 1
    assert layer.righe[0]["att_name"] == "foto_est.jpg"
