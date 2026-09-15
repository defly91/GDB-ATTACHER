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
