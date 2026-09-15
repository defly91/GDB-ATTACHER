# test_wizard_montaggio.py — il wizard in 7 passi montato sui widget finti.
#
# PERCHE' ESISTE: fino a ieri il finto QGIS non permetteva di *istanziare* il
# wizard (`AttributeError: 'function' object has no attribute 'connect'`: gli
# stub Qt restituivano funzioni al posto dei segnali). I percorsi del wizard —
# scelta layer, verifica bloccante, conteggi, annullamento — non erano coperti
# da nessun test. Questi test coprono il montaggio; i difetti specifici stanno
# nei file `test_wizard_*.py` accanto a questo.
#
# Marcatura: tutti `unit` (girano su una macchina senza QGIS).

from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fake_qgis import FakeProject, crea_layer_attach, crea_layer_sorgente  # noqa: E402
from gdb_attacher.wizard import dialog, strings                            # noqa: E402

pytestmark = pytest.mark.unit

#: Origine tipica di un layer FileGDB caricato in QGIS.
GDB = "/tmp/campione.gdb"

#: pagine del wizard, nell'ordine letterale degli step.
PAGINE = ("pagina_layer", "pagina_verifica", "pagina_discovery", "pagina_campi",
          "pagina_naming", "pagina_esegui", "pagina_stile")


# ---------------------------------------------------------------------------
# Aiutanti condivisi dai test del wizard

def layer_sorgente(nome="fotorilievo", campi=None, feature=None):
    return crea_layer_sorgente(nome=nome, campi=campi, feature=feature,
                               source="%s|layername=%s" % (GDB, nome))


def layer_allegati(nome="fotorilievo__ATTACH", **kwargs):
    return crea_layer_attach(nome=nome, source="%s|layername=%s" % (GDB, nome), **kwargs)


def progetto_con(layer_sorgente=None, layer_allegati=None, extra=()):
    """Progetto finto con sorgente e/o tabella allegati (e altri layer).

    `layer_sorgente=False` / `layer_allegati=False` = non aggiungerli affatto.
    """
    progetto = FakeProject.instance()
    coppia = {}
    if layer_sorgente is not False:
        coppia["sorgente"] = (layer_sorgente if layer_sorgente is not None
                              else globals()["layer_sorgente"]())
        progetto.addMapLayer(coppia["sorgente"])
    if layer_allegati is not False:
        coppia["allegati"] = (layer_allegati if layer_allegati is not None
                              else globals()["layer_allegati"]())
        progetto.addMapLayer(coppia["allegati"])
    for layer in extra:
        progetto.addMapLayer(layer)
    return progetto, coppia


def apri_wizard(monkeypatch=None, lingua="it"):
    """Istanzia il wizard con il progetto finto corrente, nella lingua voluta.

    La lingua si fissa *prima* della costruzione: le pagine congelano i testi nel
    costruttore (`self.lingua`), come vuole la scelta del ticket 03.
    """
    if monkeypatch is not None:
        monkeypatch.setattr(dialog.strings, "lingua_corrente", lambda: lingua)
    return dialog.WizardAllegati(None)


# ---------------------------------------------------------------------------
# Il wizard si monta

def test_il_wizard_monta_le_sette_pagine(monkeypatch):
    wizard = apri_wizard(monkeypatch)
    assert len(wizard.pageIds()) == 7
    assert [p.title() for p in wizard.pagine] == [strings.tr(c, "it") for c in PAGINE]
    assert wizard.pagina_layer is wizard.page(0)
    assert wizard.pagina_stile is wizard.page(6)


def test_i_pulsanti_standard_del_wizard_hanno_il_testo_tradotto(monkeypatch):
    from qgis.PyQt.QtWidgets import QWizard

    wizard = apri_wizard(monkeypatch)
    assert wizard.buttonText(QWizard.NextButton) == strings.tr("avanti", "it")
    assert wizard.buttonText(QWizard.BackButton) == strings.tr("indietro", "it")
    assert wizard.buttonText(QWizard.CancelButton) == strings.tr("annulla", "it")
    assert wizard.button(QWizard.NextButton).text() == strings.tr("avanti", "it")


def test_il_wizard_si_monta_anche_in_inglese(monkeypatch):
    wizard = apri_wizard(monkeypatch, "en")
    assert [p.title() for p in wizard.pagine] == [strings.tr(c, "en") for c in PAGINE]
    assert wizard.pagina_layer.etichetta_vuoto.text() == strings.tr("nessun_layer_filegdb", "en")


def test_i_segnali_dei_widget_finti_funzionano_davvero():
    """Se i segnali fossero finti-finti, i test del wizard sarebbero una bugia."""
    from qgis.PyQt.QtWidgets import QComboBox, QLineEdit, QPushButton, QWizardPage

    combo = QComboBox()
    visti = []
    combo.currentIndexChanged.connect(visti.append)
    combo.addItem("primo", "id-1")
    combo.addItem("secondo", "id-2")
    combo.setCurrentIndex(1)
    assert visti == [0, 1]
    assert (combo.count(), combo.currentText(), combo.currentData()) == (2, "secondo", "id-2")
    assert combo.findData("id-1") == 0
    assert combo.findText("non c'è") == -1

    campo = QLineEdit()
    digitati = []
    campo.textChanged.connect(digitati.append)
    campo.setText("abc")
    assert digitati == ["abc"]

    cliccato = []
    pulsante = QPushButton("Esegui")
    pulsante.clicked.connect(lambda: cliccato.append(True))
    pulsante.click()
    pulsante.setEnabled(False)
    pulsante.click()                     # disabilitato: non emette
    assert cliccato == [True]

    pagina = QWizardPage()
    cambi = []
    pagina.completeChanged.connect(lambda: cambi.append(True))
    pagina.completeChanged.emit()
    assert cambi == [True]


def test_la_tabella_allegati_si_trova_dal_layer_sorgente():
    """Il progetto finto risponde come QGIS: `mapLayer(id)` ritrova il layer."""
    progetto, coppia = progetto_con()
    assert progetto.mapLayer(coppia["sorgente"].id()) is coppia["sorgente"]
    assert progetto.mapLayer("id-che-non-esiste") is None
