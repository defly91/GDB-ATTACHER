# test_wizard_csv.py — le chiavi del CSV che non esistono nel layer si dicono.
#
# Difetto: `csv_avviso_chiavi_ignote` stava in strings.py ma non arrivava mai a
# video. Le righe del CSV senza corrispondenza nel layer finivano contate come
# `chiave_ignota` e visibili solo nell'export, non nel punto in cui l'utente
# sceglie il CSV (SPEC §6).
#
# Marcatura: `unit`.

from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fake_qgis import GUID_1, GUID_2, FakeProject                    # noqa: E402
from gdb_attacher.core import attach, naming                         # noqa: E402
from gdb_attacher.wizard import strings                              # noqa: E402
from test_wizard_montaggio import apri_wizard                        # noqa: E402
from test_wizard_chiavi_stantie import wizard_pronto                 # noqa: E402

pytestmark = pytest.mark.unit

#: CSV di prova: la chiave è il GLOBALID della feature, il file sta nella cartella base.
INTESTAZIONE = "GLOBALID;file"


def scrivi_csv(tmp_path, righe, nome="elenco.csv"):
    percorso = tmp_path / nome
    percorso.write_text(INTESTAZIONE + "\n" + "\n".join(righe) + "\n", encoding="utf-8")
    return percorso


def wizard_con_csv(monkeypatch, tmp_path, righe, lingua="it"):
    """Wizard in modalità CSV, con l'elenco già letto come fa `_carica_csv`."""
    wizard, _ = wizard_pronto(monkeypatch, tmp_path)
    wizard.lingua = lingua
    wizard.modalita = naming.MODALITA_CSV
    wizard.pagina_naming.radio_csv.setChecked(True)
    wizard.elenco_csv = naming.leggi_csv_allegati(
        str(scrivi_csv(tmp_path, righe)), chiave="GLOBALID", colonna_file="file",
    )
    return wizard


# ---------------------------------------------------------------------------

def test_le_chiavi_del_csv_assenti_dal_layer_sono_avvisate(monkeypatch, tmp_path):
    wizard = wizard_con_csv(monkeypatch, tmp_path,
                            ["%s;SS_0001.jpg" % GUID_1, "CHIAVE-IGNOTA;SS_0001.jpg"])
    wizard.pagina_naming.aggiorna_anteprima()

    testo = wizard.pagina_naming.conteggi.text()
    assert strings.tr("csv_avviso_chiavi_ignote", "it", n=1) in testo
    assert strings.tr("totale_saltati", "it", n=1) in testo


def test_piu_chiavi_ignote_sono_contate_tutte(monkeypatch, tmp_path):
    wizard = wizard_con_csv(monkeypatch, tmp_path,
                            ["%s;SS_0001.jpg" % GUID_1,
                             "IGNOTA-1;SS_0001.jpg",
                             "IGNOTA-2;SS_0001.jpg"])
    wizard.pagina_naming.aggiorna_anteprima()

    assert strings.tr("csv_avviso_chiavi_ignote", "it", n=2) in \
        wizard.pagina_naming.conteggi.text()


def test_senza_chiavi_ignote_non_si_avvisa(monkeypatch, tmp_path):
    wizard = wizard_con_csv(monkeypatch, tmp_path,
                            ["%s;SS_0001.jpg" % GUID_1, "%s;SS_0001.jpg" % GUID_2])
    wizard.pagina_naming.aggiorna_anteprima()

    testo = wizard.pagina_naming.conteggi.text()
    assert "csv_avviso_chiavi_ignote" not in testo
    assert strings.tr("csv_avviso_chiavi_ignote", "it", n=0) not in testo
    assert strings.tr("totale_ok", "it", n=2) in testo


def test_l_avviso_e_tradotto(monkeypatch, tmp_path):
    wizard = wizard_con_csv(monkeypatch, tmp_path, ["IGNOTA;SS_0001.jpg"], lingua="en")
    wizard.pagina_naming.aggiorna_anteprima()

    testo = wizard.pagina_naming.conteggi.text()
    assert strings.tr("csv_avviso_chiavi_ignote", "en", n=1) in testo
    assert "non esistono nel layer" not in testo


def test_l_avviso_finisce_anche_nel_report(monkeypatch, tmp_path):
    """Il numero è coerente col report: le stesse righe sono esportabili."""
    wizard = wizard_con_csv(monkeypatch, tmp_path, ["IGNOTA;SS_0001.jpg"])
    wizard.pagina_naming.aggiorna_anteprima()
    wizard.layer_sorgente = wizard.pagina_layer.layer_scelto() or wizard.layer_sorgente
    wizard.esito = attach.verifica_completa(FakeProject.instance(), wizard.layer_sorgente)

    wizard.pagina_naming.aggiorna_anteprima()
    wizard.pagina_esegui.initializePage()
    wizard.pagina_esegui.radio_senza_backup.setChecked(True)
    wizard.pagina_esegui.esegui()

    assert wizard.report.saltati == 1
    assert [riga.tipo for riga in wizard.report.righe] == ["chiave_ignota"]
