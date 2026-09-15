# test_wizard_pagina_layer.py — passo 1: quali layer si possono scegliere, e
# quale resta scelto tornando indietro.
#
# Marcatura: `unit` (girano su una macchina senza QGIS).

from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fake_qgis import crea_layer_sorgente                       # noqa: E402
from gdb_attacher.core import attach                             # noqa: E402
from test_wizard_montaggio import (                              # noqa: E402
    GDB, apri_wizard, layer_sorgente, progetto_con,
)

pytestmark = pytest.mark.unit


def sorgente_finta(nome):
    return crea_layer_sorgente(nome=nome, source="%s|layername=%s" % (GDB, nome))


# ---------------------------------------------------------------------------
# Difetto: tornando indietro, il combo perdeva la scelta

def due_sorgenti(monkeypatch):
    """Progetto con due layer FileGDB: `fotorilievo` e `fotorilievo_bis`."""
    secondo = sorgente_finta("fotorilievo_bis")
    progetto_con(extra=[secondo])
    return apri_wizard(monkeypatch), secondo


def test_tornando_indietro_resta_scelto_il_layer_di_prima(monkeypatch):
    """Il difetto: `initializePage()` ripopolava il combo e la scelta cadeva sul
    PRIMO layer della lista, quindi si proseguiva scrivendo sul GDB sbagliato."""
    wizard, secondo = due_sorgenti(monkeypatch)
    pagina = wizard.pagina_layer
    pagina.initializePage()
    pagina.combo.setCurrentIndex(1)
    assert pagina.validatePage() is True
    assert wizard.layer_sorgente is secondo

    pagina.initializePage()          # l'utente torna indietro dal passo 2
    assert pagina.combo.currentData() == secondo.id()
    assert pagina.layer_scelto() is secondo
    assert wizard.layer_sorgente is secondo


def test_la_scelta_non_cambia_con_aggiorna(monkeypatch):
    wizard, secondo = due_sorgenti(monkeypatch)
    pagina = wizard.pagina_layer
    pagina.initializePage()
    pagina.combo.setCurrentIndex(1)
    assert pagina.validatePage() is True

    pagina.bottone_aggiorna.click()          # «Aggiorna» non azzera la scelta
    assert pagina.layer_scelto() is secondo


def test_validate_page_registra_sempre_il_layer_mostrato(monkeypatch):
    """La scrittura va sul layer che l'utente *vede* selezionato."""
    wizard, secondo = due_sorgenti(monkeypatch)
    pagina = wizard.pagina_layer
    pagina.initializePage()
    primo = pagina.layer_scelto()
    assert primo is not secondo
    assert pagina.validatePage() is True
    assert wizard.layer_sorgente is primo

    pagina.combo.setCurrentIndex(1)
    assert pagina.validatePage() is True
    assert wizard.layer_sorgente is secondo


def test_senza_layer_filegdb_il_passo_non_e_completo(monkeypatch):
    progetto_con(layer_sorgente=False, layer_allegati=False,
                 extra=[crea_layer_sorgente(nome="shape", source="/tmp/qualsiasi.shp")])
    wizard = apri_wizard(monkeypatch)
    pagina = wizard.pagina_layer
    pagina.initializePage()
    assert pagina.combo.count() == 0
    assert pagina.etichetta_vuoto.isVisible() is True
    assert pagina.isComplete() is False
    assert pagina.validatePage() is False
    assert wizard.layer_sorgente is None


def test_l_origine_mostrata_e_quella_del_layer_scelto(monkeypatch):
    wizard, secondo = due_sorgenti(monkeypatch)
    pagina = wizard.pagina_layer
    pagina.initializePage()
    pagina.combo.setCurrentIndex(1)
    assert secondo.source() in pagina.etichetta_origine.text()


# ---------------------------------------------------------------------------
# Difetto: la tabella allegati compariva fra i layer sorgente

def test_la_tabella_allegati_non_compare_fra_i_layer_sorgente(monkeypatch):
    """Il difetto: `fotorilievo__ATTACH` si poteva scegliere come sorgente e il
    wizard cercava poi `fotorilievo__ATTACH__ATTACH`, bloccandosi senza dire
    perché."""
    progetto_con()
    wizard = apri_wizard(monkeypatch)
    nomi = [layer.name() for layer in wizard.layer_filegdb()]
    assert nomi == ["fotorilievo"]
    assert attach.nome_tabella_allegati("fotorilievo") not in nomi


def test_ogni_nome_che_finisce_col_suffisso_e_escluso(monkeypatch):
    """Il suffisso è quello dichiarato dal core e vale in qualunque maiuscola."""
    progetto_con(extra=[
        sorgente_finta("altro" + attach.SUFFISSO_TABELLA_ALLEGATI),
        sorgente_finta("minuscola" + attach.SUFFISSO_TABELLA_ALLEGATI.lower()),
        sorgente_finta("sorvegliante"),
    ])
    nomi = [layer.name() for layer in apri_wizard(monkeypatch).layer_filegdb()]
    assert nomi == ["fotorilievo", "sorvegliante"]


def test_un_nome_simile_ma_non_tabella_allegati_resta(monkeypatch):
    progetto_con(extra=[
        sorgente_finta("fotorilievo__ATTACHMENT"),
        sorgente_finta("fotorilievo__ATTACH_2"),
    ])
    nomi = [layer.name() for layer in apri_wizard(monkeypatch).layer_filegdb()]
    assert nomi == ["fotorilievo", "fotorilievo__ATTACHMENT", "fotorilievo__ATTACH_2"]


def test_i_layer_non_filegdb_restano_fuori(monkeypatch):
    """Il filtro su FileGDB (ticket 03) non cambia: shapefile e raster restano fuori."""
    progetto_con(extra=[
        crea_layer_sorgente(nome="shape", source="/tmp/qualsiasi.shp"),
    ])
    nomi = [layer.name() for layer in apri_wizard(monkeypatch).layer_filegdb()]
    assert nomi == ["fotorilievo"]
