# test_wizard_campi_manuali.py — scegliere a mano un campo foto che la discovery non trova.
#
# PERCHE' ESISTE (segnalazione dall'uso reale, non da una revisione): in un layer
# FileGDB vero il campo foto conteneva un percorso assoluto con spazi
# (`Creator = C:\Users\...\WhatsApp Image 2026-09-15 at 13.06.13.jpeg`). La discovery
# lo classificava D — livello *nascosto* — e al passo «Scelta campi» la tabella era
# vuota: niente campo da spuntare e nessuna spiegazione di come forzarlo a mano.
#
# Due difetti distinti, un test ciascuno:
#   1. il campo con percorso assoluto non veniva riconosciuto (in `core/discovery.py`,
#      coperto da `gdb_attacher/tests/test_core_discovery.py`);
#   2. con tutto in D la pagina restava vuota invece di mostrare i campi e dire perché.
#
# Marcatura: `unit`.
from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fake_qgis import crea_feature                                   # noqa: E402
from gdb_attacher.core import discovery                              # noqa: E402
from gdb_attacher.wizard import strings                              # noqa: E402
from test_wizard_montaggio import (                                  # noqa: E402
    apri_wizard, layer_sorgente, progetto_con,
)

pytestmark = pytest.mark.unit


def layer_senza_candidati():
    """Layer con un solo campo testuale senza segnali: la discovery lo mette in D.

    Il nome del campo non contiene parole chiave e il valore non esiste su disco:
    esattamente il caso reale (`Creator` con un percorso non raggiungibile), senza
    dipendere dal filesystem della macchina che esegue i test.
    """
    campi = {"GLOBALID": "Stringa", "Creator": "Stringa"}
    feature = [crea_feature(campi, {"GLOBALID": "{6E7DE81F-1947-43A8-BD51-FF70846EF6C6}",
                                    "Creator": r"C:\Foto\la mia foto.jpg"})]
    return layer_sorgente(campi=campi, feature=feature)


@pytest.fixture()
def pagina_campi(monkeypatch):
    """Il passo 4 con la discovery fatta su un layer che non ha campi candidati."""
    sorgente = layer_senza_candidati()
    progetto_con(layer_sorgente=sorgente)
    wizard = apri_wizard(monkeypatch)
    wizard.layer_sorgente = sorgente
    wizard.righe_discovery = discovery.suggerisci_campi(sorgente, None)
    assert all(riga.livello == "D" for riga in wizard.righe_discovery), \
        "il layer di prova deve avere tutti i campi in D"
    return wizard.pagina_campi


def test_il_passo_discovery_avvisa_che_si_potra_scegliere_a_mano(monkeypatch, tmp_path):
    """Il passo 3 non deve zittirsi quando nessun campo è candidato: lo dice lì."""
    sorgente = layer_senza_candidati()
    progetto_con(layer_sorgente=sorgente)
    wizard = apri_wizard(monkeypatch)
    wizard.layer_sorgente = sorgente
    pagina = wizard.pagina_discovery
    pagina.cartella.setText(str(tmp_path))
    pagina.scansiona()

    assert pagina.stato.text() == strings.tr("nessun_campo_candidato", "it")
    assert pagina.tabella.rowCount() == len(wizard.righe_discovery), \
        "la tabella del passo 3 mostra anche i campi di livello D"


def test_con_tutti_i_campi_in_d_la_tabella_non_resta_vuota(pagina_campi):
    """Difetto: tabella vuota e nessun modo di capire come forzare il campo."""
    pagina_campi.initializePage()

    assert pagina_campi.mostra_d.isChecked(), \
        "senza candidati la spunta «mostra gli altri campi» deve essere già attiva"
    assert pagina_campi.tabella.rowCount() == 2, "i campi del layer devono essere spuntabili"
    assert pagina_campi.nota.isVisible() is False, "c'è qualcosa da spuntare: niente avviso"
    assert pagina_campi.campi_scelti() == [], "mostrare i campi non significa sceglierli"


def test_il_campo_si_puo_forzare_a_mano(pagina_campi):
    """L'utente spunta il campo che vuole: il wizard lo accetta e prosegue."""
    from qgis.PyQt.QtCore import Qt

    pagina_campi.initializePage()
    # Riga 0 = `Creator` (a pari livello l'ordine e' alfabetico: creator < globalid).
    assert pagina_campi.tabella.item(0, 1).text() == "Creator"
    pagina_campi.tabella.item(0, 0).setCheckState(Qt.Checked)

    assert pagina_campi.campi_scelti() == ["Creator"]
    assert pagina_campi.isComplete() is True
    assert pagina_campi.validatePage() is True


def test_togliendo_la_spunta_la_pagina_spiega_perche_e_vuota(pagina_campi):
    """Chi nasconde i campi deve sapere perché non vede niente, non trovare il vuoto."""
    pagina_campi.initializePage()
    pagina_campi.mostra_d.setChecked(False)
    pagina_campi._riempi_tabella()

    assert pagina_campi.tabella.rowCount() == 0
    assert pagina_campi.nota.isVisible() is True
    assert pagina_campi.nota.text() == strings.tr("nessun_campo_visibile", "it")
    assert pagina_campi.isComplete() is False
