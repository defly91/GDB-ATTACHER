# test_wizard_chiavi_stantie.py — la cache delle chiavi esistenti non deve
# sopravvivere a un'esecuzione, altrimenti il secondo lotto riscrive gli stessi
# allegati (doppioni nel GDB).
#
# Marcatura: `unit`.

from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fake_qgis import (                                            # noqa: E402
    GUID_1, FakeFeature, FakeFields, FakeProject,
    crea_layer_attach, crea_layer_sorgente,
)
from gdb_attacher.core import attach, naming                       # noqa: E402
from test_wizard_montaggio import apri_wizard, progetto_con        # noqa: E402

pytestmark = pytest.mark.unit

#: GLOBALID della prima feature del layer sorgente finto.
GUID_FEATURE = GUID_1


def wizard_pronto(monkeypatch, tmp_path, tabella=None, nome_file="SS_0001.jpg"):
    """Wizard col passo 5 pronto: sorgente su FileGDB, tabella allegati, file su disco."""
    cartella = tmp_path / "foto"
    cartella.mkdir()
    (cartella / nome_file).write_bytes(b"\xff\xd8\xff\xe0finto-jpeg")

    sorgente = crea_layer_sorgente(source="/tmp/campione.gdb|layername=fotorilievo")
    tabella = tabella if tabella is not None else crea_layer_attach()
    progetto_con(layer_sorgente=sorgente, layer_allegati=tabella)

    from fake_qgis import FakeProject
    wizard = apri_wizard(monkeypatch)
    wizard.layer_sorgente = sorgente
    wizard.esito = attach.verifica_completa(FakeProject.instance(), sorgente)
    wizard.cartella_base = str(cartella)
    wizard.campi_scelti = ["filefoto"]
    wizard.modalita = naming.MODALITA_ORIGINALE
    return wizard, tabella


def riga_allegato(tabella, rel_globalid, nome):
    """Aggiunge a mano un allegato alla tabella finta (come farebbe ArcGIS)."""
    campi = tabella.fields()
    feature = FakeFeature(campi=FakeFields(campi), valori={
        "GLOBALID": "AABBCCDD-0000-1111-2222-334455667788",
        "REL_GLOBALID": rel_globalid, "CONTENT_TYPE": "image/jpeg",
        "DATA_SIZE": 4, "ATT_NAME": nome, "DATA": b"\xff\xd8\xff\xe0",
    })
    tabella.addFeature(feature)
    return feature


def esegui_senza_backup(wizard):
    pagina = wizard.pagina_esegui
    pagina.initializePage()
    pagina.radio_senza_backup.setChecked(True)
    pagina.esegui()
    return pagina


# ---------------------------------------------------------------------------
# La cache si invalida quando cambia qualcosa sotto

def test_la_cache_si_butta_quando_cambia_il_layer_allegati(monkeypatch, tmp_path):
    wizard, tabella = wizard_pronto(monkeypatch, tmp_path)
    pagina = wizard.pagina_naming
    assert pagina.chiavi_tabella_esistenti() == set()

    # un altro layer allegati (per esempio il .gdb ricaricato): la cache non vale
    altra = crea_layer_attach(source="/tmp/altro.gdb|layername=fotorilievo__ATTACH")
    riga_allegato(altra, "{%s}" % GUID_FEATURE, "SS_0001.jpg")
    from fake_qgis import FakeProject
    wizard.esito = attach.verifica_completa(FakeProject.instance(), wizard.layer_sorgente)
    wizard.esito.layer_allegati = altra
    wizard.esito.tabella.presente = True

    assert pagina.chiavi_tabella_esistenti() == {("{%s}" % GUID_FEATURE, "SS_0001.jpg")}


def test_la_cache_si_butta_quando_ripassa_la_verifica(monkeypatch, tmp_path):
    wizard, tabella = wizard_pronto(monkeypatch, tmp_path)
    pagina = wizard.pagina_naming
    assert pagina.chiavi_tabella_esistenti() == set()

    riga_allegato(tabella, "{%s}" % GUID_FEATURE, "SS_0001.jpg")
    wizard.pagina_verifica.esegui_verifiche()          # l'utente rifà le verifiche
    assert pagina.chiavi_tabella_esistenti() == {("{%s}" % GUID_FEATURE, "SS_0001.jpg")}


def test_forza_rilegge_sempre(monkeypatch, tmp_path):
    wizard, tabella = wizard_pronto(monkeypatch, tmp_path)
    pagina = wizard.pagina_naming
    assert pagina.chiavi_tabella_esistenti() == set()
    riga_allegato(tabella, "{%s}" % GUID_FEATURE, "SS_0001.jpg")
    assert pagina.chiavi_tabella_esistenti() == set()            # cache ancora calda
    assert pagina.chiavi_tabella_esistenti(forza=True) == {("{%s}" % GUID_FEATURE,
                                                            "SS_0001.jpg")}
    assert wizard.chiavi_esistenti == set()                       # non tocca il wizard


def test_ricarica_allinea_anche_lo_stato_del_wizard(monkeypatch, tmp_path):
    wizard, tabella = wizard_pronto(monkeypatch, tmp_path)
    riga_allegato(tabella, "{%s}" % GUID_FEATURE, "SS_0001.jpg")
    wizard.pagina_naming.ricarica_chiavi_esistenti()
    assert wizard.chiavi_esistenti == {("{%s}" % GUID_FEATURE, "SS_0001.jpg")}


# ---------------------------------------------------------------------------
# Il percorso vero: esegui → indietro al naming → riesegui

def test_rieseguire_non_riscrive_gli_stessi_allegati(monkeypatch, tmp_path):
    """Il difetto: la cache vuota sopravviveva al primo lotto, quindi il secondo
    lotto riscriveva le stesse righe (`REL_GLOBALID`, `ATT_NAME`)."""
    wizard, tabella = wizard_pronto(monkeypatch, tmp_path)
    wizard.pagina_naming.aggiorna_anteprima()          # passo 5: riempie la cache

    esegui_senza_backup(wizard)
    assert tabella.featureCount() == 1
    assert wizard.report.aggiunti == 1

    # «Indietro» al passo 5: l'anteprima deve accorgersi del nuovo allegato
    wizard.pagina_naming.aggiorna_anteprima()
    candidati = wizard.pagina_naming.costruisci_candidati(salva=False)
    stati = [c.stato for c in candidati]
    assert stati.count("duplicato") == 1
    assert stati.count("ok") == 0

    esegui_senza_backup(wizard)                        # passo 6 di nuovo
    assert tabella.featureCount() == 1                 # nessun doppione
    assert wizard.report.aggiunti == 0
    assert wizard.report.duplicati == 1


def test_il_riepilogo_riconosce_l_allegato_scritto_da_altri(monkeypatch, tmp_path):
    """Un allegato aggiunto in mezzo (ArcGIS, altra sessione) non viene riscritto."""
    wizard, tabella = wizard_pronto(monkeypatch, tmp_path)
    wizard.pagina_naming.aggiorna_anteprima()          # cache vuota
    riga_allegato(tabella, "{%s}" % GUID_FEATURE, "SS_0001.jpg")

    esegui_senza_backup(wizard)
    assert tabella.featureCount() == 1
    assert wizard.report.aggiunti == 0
    assert wizard.report.duplicati == 1


def test_ogni_esecuzione_rilegge_le_chiavi(monkeypatch, tmp_path):
    """`esegui()` non si fida della cache: il core ricarica le chiavi."""
    wizard, tabella = wizard_pronto(monkeypatch, tmp_path)
    wizard.pagina_naming.aggiorna_anteprima()
    visti = {}
    vero = attach.scrivi_allegati

    def spia(layer_allegati, candidati, **kwargs):
        visti["chiavi_esistenti"] = kwargs.get("chiavi_esistenti", "assente")
        return vero(layer_allegati, candidati, **kwargs)

    monkeypatch.setattr(attach, "scrivi_allegati", spia)
    esegui_senza_backup(wizard)
    assert visti["chiavi_esistenti"] is None           # None = il core le ricarica


def test_dopo_l_esecuzione_la_cache_e_pulita(monkeypatch, tmp_path):
    wizard, _ = wizard_pronto(monkeypatch, tmp_path)
    wizard.pagina_naming.aggiorna_anteprima()
    pagina = wizard.pagina_naming
    esegui_senza_backup(wizard)
    assert pagina._cache_chiavi is None
    assert wizard.chiavi_esistenti == set()
