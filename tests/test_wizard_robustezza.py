# test_wizard_robustezza.py — un errore imprevisto non deve uscire come traceback
# dallo slot Qt, e non deve portare via il report.
#
# Difetto: `scansiona()` e `esegui()` non avevano try/except. Un errore inatteso
# (disco pieno, tabella sparita, core che solleva) finiva come traceback nello slot
# Qt e il report costruito fino a lì andava perso.
#
# Marcatura: `unit`.

from __future__ import annotations

import os
import sys
import types

import pytest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fake_qgis import REGISTRO_DIALOGHI                              # noqa: E402
from gdb_attacher.core import attach, discovery, report as modulo_report  # noqa: E402
from gdb_attacher.wizard import strings                              # noqa: E402
from test_wizard_chiavi_stantie import esegui_senza_backup, wizard_pronto  # noqa: E402
from test_wizard_montaggio import apri_wizard, progetto_con          # noqa: E402

pytestmark = pytest.mark.unit


def statistica_finta(**campi):
    """Statistica di scrittura con `errore_commit` (il core vero lo espone)."""
    base = dict(aggiunti=0, duplicati=0, saltati=0, errori=[], annullata=False,
                errore_commit="")
    base.update(campi)
    return types.SimpleNamespace(**base)


def ultimo_dialogo(tipo=None):
    for dialogo in reversed(REGISTRO_DIALOGHI):
        if tipo is None or dialogo["tipo"] == tipo:
            return dialogo
    return None


# ---------------------------------------------------------------------------
# Scrittura: errore imprevisto

def test_errore_imprevisto_in_scrittura_non_esce_come_traceback(monkeypatch, tmp_path):
    wizard, tabella = wizard_pronto(monkeypatch, tmp_path)
    wizard.pagina_naming.aggiorna_anteprima()

    def esplode(*args, **kwargs):
        raise RuntimeError("disco pieno")

    monkeypatch.setattr(attach, "scrivi_allegati", esplode)

    pagina = esegui_senza_backup(wizard)          # non deve sollevare

    assert pagina.esito.text() == strings.tr("errore_esecuzione", "it",
                                             errore="disco pieno")
    assert pagina.in_corso() is False
    assert tabella.featureCount() == 0


def test_errore_imprevisto_non_perde_il_report(monkeypatch, tmp_path):
    wizard, _ = wizard_pronto(monkeypatch, tmp_path)
    wizard.pagina_naming.aggiorna_anteprima()
    monkeypatch.setattr(attach, "scrivi_allegati",
                        lambda *a, **k: (_ for _ in ()).throw(RuntimeError("boom")))

    pagina = esegui_senza_backup(wizard)

    assert wizard.report is not None
    assert wizard.report.righe                            # righe ancora esportabili
    assert pagina.bottone_export.isEnabled() is True
    assert pagina.bottone_export_tutto.isEnabled() is True


def test_dopo_un_errore_si_puo_ancora_esportare(monkeypatch, tmp_path, risposte_dialoghi):
    wizard, _ = wizard_pronto(monkeypatch, tmp_path)
    wizard.pagina_naming.aggiorna_anteprima()
    monkeypatch.setattr(attach, "scrivi_allegati",
                        lambda *a, **k: (_ for _ in ()).throw(RuntimeError("boom")))
    pagina = esegui_senza_backup(wizard)

    destinazione = tmp_path / "report.csv"
    risposte_dialoghi.file.append((str(destinazione), ""))
    pagina.esporta(solo_anomalie=True)

    assert destinazione.is_file()
    assert pagina.esito.text() == strings.tr("report_salvato", "it", percorso=str(destinazione))


# ---------------------------------------------------------------------------
# Commit fallito

def test_commit_fallito_dice_che_non_si_e_scritto(monkeypatch, tmp_path):
    wizard, tabella = wizard_pronto(monkeypatch, tmp_path)
    wizard.pagina_naming.aggiorna_anteprima()

    def scrive_ma_non_committa(layer_allegati, candidati, **kwargs):
        return statistica_finta(aggiunti=1, errore_commit="database is locked")

    monkeypatch.setattr(attach, "scrivi_allegati", scrive_ma_non_committa)
    pagina = esegui_senza_backup(wizard)

    assert pagina.esito.text() == strings.tr("esito_commit_fallito", "it",
                                             errore="database is locked")
    assert "nulla è stato scritto" in pagina.esito.text()
    assert "aggiunti" not in pagina.esito.text()
    # Il passo non si dichiara «eseguito»: alla chiusura l'avviso «nessuna modifica
    # al geodatabase» è di nuovo la verità.
    assert wizard.eseguito is False
    assert wizard.report is not None                   # il report resta esportabile


def test_commit_fallito_riportato_dal_report(monkeypatch, tmp_path):
    """Il core può esporre `errore_commit` sulla statistica o sul report."""
    wizard, _ = wizard_pronto(monkeypatch, tmp_path)
    wizard.pagina_naming.aggiorna_anteprima()
    vero = modulo_report.report_da_candidati

    def report_col_errore(*args, **kwargs):
        report = vero(*args, **kwargs)
        report.errore_commit = "commit rifiutato da QGIS"
        return report

    monkeypatch.setattr(modulo_report, "report_da_candidati", report_col_errore)
    pagina = esegui_senza_backup(wizard)

    assert pagina.esito.text() == strings.tr("esito_commit_fallito", "it",
                                             errore="commit rifiutato da QGIS")


def test_dopo_un_commit_fallito_chiudere_avvisa_che_non_si_e_scritto(monkeypatch, tmp_path):
    wizard, _ = wizard_pronto(monkeypatch, tmp_path)
    wizard.pagina_naming.aggiorna_anteprima()
    monkeypatch.setattr(attach, "scrivi_allegati",
                        lambda *a, **k: statistica_finta(aggiunti=1,
                                                         errore_commit="database is locked"))
    esegui_senza_backup(wizard)

    wizard.reject()

    assert ultimo_dialogo("information")["testo"] == strings.tr("annulla_zero_scritto", "it")
    assert wizard.chiusura == "rifiutato"


def test_scrittura_riuscita_mostra_i_numeri_del_report(monkeypatch, tmp_path):
    wizard, tabella = wizard_pronto(monkeypatch, tmp_path)
    wizard.pagina_naming.aggiorna_anteprima()
    pagina = esegui_senza_backup(wizard)

    assert tabella.featureCount() == 1
    assert pagina.esito.text() == strings.tr(
        "esito_scrittura", "it", aggiunti=wizard.report.aggiunti,
        duplicati=wizard.report.duplicati, mancanti=wizard.report.mancanti,
        saltati=wizard.report.saltati, errori=wizard.report.errori,
    )


# ---------------------------------------------------------------------------
# Scansione dei campi

def test_errore_nella_scansione_dei_campi_non_esce_come_traceback(monkeypatch, tmp_path):
    sorgente = wizard_pronto(monkeypatch, tmp_path)[0].layer_sorgente
    progetto_con(layer_sorgente=sorgente)
    wizard = apri_wizard(monkeypatch)
    wizard.layer_sorgente = sorgente
    monkeypatch.setattr(discovery, "suggerisci_campi",
                        lambda *a, **k: (_ for _ in ()).throw(RuntimeError("campo rotto")))

    wizard.pagina_discovery.scansiona()           # non deve sollevare

    assert wizard.pagina_discovery.stato.text() == strings.tr(
        "errore_scansione", "it", errore="campo rotto")
    assert wizard.righe_discovery == []
    assert wizard.pagina_discovery.isComplete() is False


# ---------------------------------------------------------------------------
# Export del report

def test_export_che_fallisce_non_perde_i_conteggi(monkeypatch, tmp_path, risposte_dialoghi):
    wizard, _ = wizard_pronto(monkeypatch, tmp_path)
    wizard.pagina_naming.aggiorna_anteprima()
    pagina = esegui_senza_backup(wizard)
    conteggi = pagina.esito.text()

    def non_si_puo_scrivere(*args, **kwargs):
        raise OSError("disco pieno")

    monkeypatch.setattr(modulo_report, "scrivi_report_csv", non_si_puo_scrivere)
    risposte_dialoghi.file.append((str(tmp_path / "report.csv"), ""))
    pagina.esporta(solo_anomalie=True)             # non deve sollevare

    dialogo = ultimo_dialogo("critical")
    assert dialogo["titolo"] == strings.tr("errore_titolo", "it")
    assert dialogo["testo"] == strings.tr("errore_export", "it", errore="disco pieno")
    assert pagina.esito.text() == conteggi         # i conteggi finali restano


def test_export_senza_righe_avvisa_e_non_apre_il_salva(monkeypatch, tmp_path, risposte_dialoghi):
    wizard = apri_wizard(monkeypatch)
    wizard.report = modulo_report.ReportFinale()
    pagina = wizard.pagina_esegui

    pagina.esporta(solo_anomalie=True)

    assert ultimo_dialogo("information")["testo"] == strings.tr("report_vuoto", "it")
    assert ultimo_dialogo("getSaveFileName") is None


def test_export_include_gli_avvisi_del_csv(monkeypatch, tmp_path, risposte_dialoghi):
    wizard, _ = wizard_pronto(monkeypatch, tmp_path)
    wizard.pagina_naming.aggiorna_anteprima()
    pagina = esegui_senza_backup(wizard)
    wizard.report.righe.append(modulo_report.RigaReport(tipo="avviso", motivo="chiavi_duplicate: 2"))

    destinazione = tmp_path / "anomalie.csv"
    risposte_dialoghi.file.append((str(destinazione), ""))
    pagina.esporta(solo_anomalie=True)

    testo = destinazione.read_text(encoding="utf-8-sig")
    assert "chiavi_duplicate" in testo
