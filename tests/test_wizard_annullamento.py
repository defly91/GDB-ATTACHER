# test_wizard_annullamento.py — annullare la scrittura non deve committare, e
# non si deve poter chiudere il wizard a metà batch.
#
# Difetto: durante il batch i pulsanti del wizard restavano attivi e la chiusura
# non chiedeva l'annullo: l'utente leggeva «annulla = nulla è stato scritto» e il
# batch intanto committava.
#
# Marcatura: `unit`.

from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fake_qgis import REGISTRO_DIALOGHI                              # noqa: E402
from gdb_attacher.core import attach                                 # noqa: E402
from gdb_attacher.wizard import strings                              # noqa: E402
from test_wizard_chiavi_stantie import esegui_senza_backup, wizard_pronto  # noqa: E402

pytestmark = pytest.mark.unit

#: Pulsanti standard del wizard che non devono essere attivi durante il batch.
PULSANTI = ("BackButton", "NextButton", "CancelButton", "FinishButton")


def qwizard():
    from qgis.PyQt.QtWidgets import QWizard
    return QWizard


def stati_pulsanti(wizard):
    return {nome: wizard.button(getattr(qwizard(), nome)).isEnabled() for nome in PULSANTI}


# ---------------------------------------------------------------------------
# Durante il batch i pulsanti sono bloccati

def test_durante_il_batch_i_pulsanti_del_wizard_sono_bloccati(monkeypatch, tmp_path):
    wizard, _ = wizard_pronto(monkeypatch, tmp_path)
    wizard.pagina_naming.aggiorna_anteprima()
    vero = attach.scrivi_allegati
    visto = {}

    def spia(layer_allegati, candidati, **kwargs):
        def callback(indice, totale, candidato):
            if indice == 1:
                visto["durante"] = stati_pulsanti(wizard)
                visto["annulla_scrittura"] = wizard.pagina_esegui.bottone_annulla.isEnabled()
                visto["conferma"] = wizard.pagina_esegui.conferma.isEnabled()
            return True

        kwargs["callback_progresso"] = callback
        return vero(layer_allegati, candidati, **kwargs)

    monkeypatch.setattr(attach, "scrivi_allegati", spia)
    esegui_senza_backup(wizard)

    assert visto["durante"] == {nome: False for nome in PULSANTI}
    assert visto["annulla_scrittura"] is True
    assert visto["conferma"] is False
    assert stati_pulsanti(wizard) == {nome: True for nome in PULSANTI}
    assert wizard.pagina_esegui.conferma.isEnabled() is True
    assert wizard.pagina_esegui.bottone_annulla.isEnabled() is False
    assert wizard.pagina_esegui.in_corso() is False


def test_i_pulsanti_tornano_attivi_anche_se_la_scrittura_solleva(monkeypatch, tmp_path):
    """Aggiornato con la correzione 7: `esegui()` ora **cattura** l'imprevisto e lo
    mostra tradotto, invece di lasciarlo uscire come traceback. La proprietà che
    questo test difende non cambia: i pulsanti bloccati dal batch si riabilitano
    sempre, anche quando la scrittura muore a metà."""
    wizard, _ = wizard_pronto(monkeypatch, tmp_path)
    wizard.pagina_naming.aggiorna_anteprima()

    def esplode(*args, **kwargs):
        raise RuntimeError("errore a metà scrittura")

    monkeypatch.setattr(attach, "scrivi_allegati", esplode)
    esegui_senza_backup(wizard)
    assert stati_pulsanti(wizard) == {nome: True for nome in PULSANTI}
    assert wizard.pagina_esegui.in_corso() is False


# ---------------------------------------------------------------------------
# Chiudere durante il batch = chiedere l'annullo

def test_chiudere_durante_il_batch_chiede_l_annullo(monkeypatch, tmp_path):
    wizard, _ = wizard_pronto(monkeypatch, tmp_path)
    pagina = wizard.pagina_esegui
    pagina._imposta_in_corso(True)

    wizard.reject()                    # come la X della finestra
    assert pagina._annulla_richiesto is True
    assert wizard.chiusura is None     # la finestra non si è chiusa
    assert not any(d["testo"] == strings.tr("annulla_zero_scritto", "it")
                   for d in REGISTRO_DIALOGHI)

    pagina._imposta_in_corso(False)
    wizard.reject()
    assert wizard.chiusura == "rifiutato"


def test_accettare_durante_il_batch_chiede_l_annullo(monkeypatch, tmp_path):
    wizard, _ = wizard_pronto(monkeypatch, tmp_path)
    pagina = wizard.pagina_esegui
    pagina._imposta_in_corso(True)
    wizard.accept()
    assert pagina._annulla_richiesto is True
    assert wizard.chiusura is None


def test_chiudere_prima_di_scrivere_avvisa_che_non_si_e_scritto(monkeypatch, tmp_path):
    wizard, _ = wizard_pronto(monkeypatch, tmp_path)
    wizard.candidati = [object()]      # c'è un lotto pronto ma non eseguito
    wizard.reject()
    assert any(d["testo"] == strings.tr("annulla_zero_scritto", "it")
               for d in REGISTRO_DIALOGHI)
    assert wizard.chiusura == "rifiutato"


def test_dopo_una_scrittura_chiudere_non_avvisa_piu(monkeypatch, tmp_path):
    wizard, _ = wizard_pronto(monkeypatch, tmp_path)
    wizard.pagina_naming.aggiorna_anteprima()
    esegui_senza_backup(wizard)
    wizard.reject()
    assert wizard.chiusura == "rifiutato"
    assert not any(d["testo"] == strings.tr("annulla_zero_scritto", "it")
                   for d in REGISTRO_DIALOGHI)


# ---------------------------------------------------------------------------
# «Annulla la scrittura»: la transazione non committa

def test_annullare_a_meta_batch_non_lascia_righe(monkeypatch, tmp_path):
    wizard, tabella = wizard_pronto(monkeypatch, tmp_path)
    wizard.pagina_naming.aggiorna_anteprima()
    pagina = wizard.pagina_esegui
    vero_progresso = pagina._progresso

    def progresso_che_annulla(indice, totale, candidato):
        if indice == 1:
            pagina.annulla_esecuzione()
        return vero_progresso(indice, totale, candidato)

    monkeypatch.setattr(pagina, "_progresso", progresso_che_annulla)
    esegui_senza_backup(wizard)

    assert tabella.featureCount() == 0                      # rollback, nessuna riga
    assert wizard.report.annullata is True
    assert pagina.esito.text() == strings.tr("esecuzione_annullata", "it")
    assert stati_pulsanti(wizard) == {nome: True for nome in PULSANTI}
    assert pagina.in_corso() is False
