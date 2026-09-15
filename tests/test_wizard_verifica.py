# test_wizard_verifica.py — passo 2: i messaggi di blocco dicono *cosa* manca.
#
# Il difetto: i testi dedicati a «tabella allegati assente» e «tabella allegati
# incompleta» esistevano in strings.py ma non erano raggiungibili — il core
# descrive la tabella con `EsitoTabellaAllegati`, non con un `Problema`. L'utente
# vedeva solo il rimando generico ad ArcGIS Pro, senza sapere quale tabella o
# quali campi mancavano (SPEC §12.6).
#
# Marcatura: `unit`.

from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fake_qgis import crea_layer_sorgente                        # noqa: E402
from gdb_attacher.core import attach                             # noqa: E402
from gdb_attacher.wizard import strings                          # noqa: E402
from test_wizard_montaggio import (                              # noqa: E402
    GDB, apri_wizard, layer_allegati, progetto_con,
)

pytestmark = pytest.mark.unit


def wizard_verificato(monkeypatch, tabella=None, sorgente=None, lingua="it"):
    """Wizard col passo 2 già eseguito sul layer sorgente del progetto.

    `tabella=None` = tabella allegati standard; `tabella=False` = assente;
    altrimenti passare il layer allegati da usare (per esempio incompleto).
    """
    progetto, coppia = progetto_con(layer_sorgente=sorgente, layer_allegati=tabella)
    wizard = apri_wizard(monkeypatch, lingua)
    wizard.layer_sorgente = coppia["sorgente"]
    wizard.pagina_verifica.esegui_verifiche()
    return wizard, coppia


# ---------------------------------------------------------------------------
# Tabella allegati assente

def test_tabella_assente_dice_quale_tabella_manca(monkeypatch):
    wizard, _ = wizard_verificato(monkeypatch, tabella=False)
    esito = wizard.pagina_verifica.messaggio.text()
    assert attach.nome_tabella_allegati("fotorilievo") in esito
    assert strings.tr("err_attach_assente", "it",
                      tabella="fotorilievo__ATTACH",
                      come=strings.tr("come_abilitare", "it")) in esito
    assert "EnableAttachments" in esito          # il come-fare resta
    assert wizard.pagina_verifica.isComplete() is False


def test_tabella_assente_non_ripete_il_messaggio(monkeypatch):
    wizard, _ = wizard_verificato(monkeypatch, tabella=False)
    esito = wizard.pagina_verifica.messaggio.text()
    assert esito.count(strings.tr("err_attach_assente", "it",
                                 tabella="fotorilievo__ATTACH",
                                 come=strings.tr("come_abilitare", "it"))) == 1


# ---------------------------------------------------------------------------
# Tabella allegati incompleta (caso distinto, con l'elenco dei campi)

def test_tabella_incompleta_elenca_i_campi_mancanti(monkeypatch):
    senza_nome = layer_allegati(campi=("GLOBALID", "REL_GLOBALID", "CONTENT_TYPE",
                                       "DATA_SIZE", "DATA"))
    wizard, _ = wizard_verificato(monkeypatch, tabella=senza_nome)
    esito = wizard.pagina_verifica.messaggio.text()
    assert "ATT_NAME" in esito
    assert strings.tr("err_attach_incompleta", "it",
                      tabella="fotorilievo__ATTACH", campi="ATT_NAME",
                      come=strings.tr("come_abilitare", "it")) in esito
    assert wizard.pagina_verifica.isComplete() is False


def test_due_campi_mancanti_sono_elencati_tutti(monkeypatch):
    senza_due = layer_allegati(campi=("GLOBALID", "REL_GLOBALID", "CONTENT_TYPE", "DATA"))
    wizard, _ = wizard_verificato(monkeypatch, tabella=senza_due)
    esito = wizard.pagina_verifica.messaggio.text()
    assert "ATT_NAME" in esito and "DATA_SIZE" in esito


def test_i_messaggi_della_tabella_arrivano_tradotti(monkeypatch):
    wizard, _ = wizard_verificato(monkeypatch, tabella=False, lingua="en")
    esito = wizard.pagina_verifica.messaggio.text()
    atteso = strings.tr("err_attach_assente", "en", tabella="fotorilievo__ATTACH",
                        come=strings.tr("come_abilitare", "en"))
    assert atteso in esito
    assert "non è caricata nel progetto" not in esito


# ---------------------------------------------------------------------------
# Casi del layer sorgente (già coperti dal core) e caso tutto a posto

def test_tutto_a_posto_il_passo_e_completo(monkeypatch):
    wizard, _ = wizard_verificato(monkeypatch)
    assert wizard.pagina_verifica.messaggio.text() == strings.tr("verifica_ok", "it")
    assert wizard.pagina_verifica.isComplete() is True


def test_layer_non_filegdb_blocca_col_suo_messaggio(monkeypatch):
    shape = crea_layer_sorgente(nome="shape", source="/tmp/qualsiasi.shp")
    wizard, _ = wizard_verificato(monkeypatch, tabella=False, sorgente=shape)
    esito = wizard.pagina_verifica.messaggio.text()
    assert strings.tr("err_non_filegdb", "it", layer="shape",
                      origine="/tmp/qualsiasi.shp") in esito
    assert wizard.pagina_verifica.isComplete() is False


def test_la_tabella_dei_controlli_mostra_gli_esiti(monkeypatch):
    senza_nome = layer_allegati(campi=("GLOBALID", "REL_GLOBALID", "CONTENT_TYPE",
                                       "DATA_SIZE", "DATA"))
    wizard, _ = wizard_verificato(monkeypatch, tabella=senza_nome)
    tabella = wizard.pagina_verifica.tabella
    assert tabella.rowCount() == 4
    assert tabella.horizontalHeaderLabels() == [strings.tr(c, "it") for c in
                                                ("col_controllo", "col_esito", "col_dettaglio")]
    # controllo «tabella allegati nel progetto» = OK, ma i 6 campi no
    assert tabella.item(2, 1).text() == strings.tr("esito_ok", "it")
    assert tabella.item(3, 1).text() == strings.tr("esito_ko", "it")
    assert tabella.item(3, 2).text() == "ATT_NAME"


def test_tabella_assente_la_riga_dei_campi_non_resta_muta(monkeypatch):
    """Senza tabella non ci sono «campi mancanti»: la cella dice almeno qualcosa."""
    wizard, _ = wizard_verificato(monkeypatch, tabella=False)
    tabella = wizard.pagina_verifica.tabella
    assert tabella.item(2, 1).text() == strings.tr("esito_ko", "it")
    assert tabella.item(3, 1).text() == strings.tr("esito_ko", "it")
    assert tabella.item(3, 2).text() == strings.tr("nessuno", "it")


def test_col_tutto_a_posto_gli_esiti_sono_ok(monkeypatch):
    wizard, _ = wizard_verificato(monkeypatch)
    tabella = wizard.pagina_verifica.tabella
    assert [tabella.item(r, 1).text() for r in range(4)] == \
        [strings.tr("esito_ok", "it")] * 4
