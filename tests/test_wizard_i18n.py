# test_wizard_i18n.py — niente stringhe di interfaccia fuori da strings.py.
#
# Difetti coperti (dalla revisione indipendente):
#   - l'evidenziazione delle celle cercava la sottostringa italiana «mancante»:
#     in inglese non evidenziava nulla;
#   - «sì» scritto a mano nella tabella della discovery;
#   - «CSV mancante» in italiano dentro un messaggio tradotto;
#   - filtro «Tutti i file (*)» e placeholder «CODICE» non tradotti;
#   - QMessageBox col messaggio usato come titolo.
#
# Marcatura: `unit`.

from __future__ import annotations

import os
import re
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fake_qgis import NULL, REGISTRO_DIALOGHI, crea_layer_sorgente     # noqa: E402
from gdb_attacher.core import naming                                  # noqa: E402
from gdb_attacher.wizard import strings                               # noqa: E402
from test_wizard_montaggio import (                                   # noqa: E402
    apri_wizard, progetto_con,
)

pytestmark = pytest.mark.unit

RADICE = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DIALOG = os.path.join(RADICE, "gdb_attacher", "wizard", "dialog.py")


def sorgente_dialog():
    with open(DIALOG, encoding="utf-8") as flusso:
        return flusso.read()


def ultimo_dialogo(tipo=None):
    for dialogo in reversed(REGISTRO_DIALOGHI):
        if tipo is None or dialogo["tipo"] == tipo:
            return dialogo
    return None


# ---------------------------------------------------------------------------
# Sorgente: nessun letterale italiano di interfaccia

@pytest.mark.parametrize("letterale", ["Tutti i file", "CSV mancante", '"CODICE"',
                                       "Operazione in corso", "Sfoglia"])
def test_nessun_letterale_di_interfaccia_nel_codice(letterale):
    """Il testo di interfaccia vive in strings.py, non nel codice della pagina."""
    assert letterale not in sorgente_dialog(), \
        f"«{letterale}» è testo di interfaccia: deve stare in strings.py"


def test_i_dialoghi_di_file_usano_i_filtri_tradotti():
    sorgente = sorgente_dialog()
    assert "_filtro_csv(tutti=True)" in sorgente
    assert "_filtro_csv_export()" in sorgente


# ---------------------------------------------------------------------------
# Comportamento in inglese (dove i difetti si vedevano)

def test_in_inglese_le_celle_mancanti_sono_evidenziate(monkeypatch):
    from qgis.PyQt.QtCore import Qt

    wizard = apri_wizard(monkeypatch, "en")
    pagina = wizard.pagina_verifica
    pagina._riempi(pagina.tabella, [(strings.tr("stato_missing", "en"),)])

    cella = pagina.tabella.item(0, 0)
    assert cella.text() == "missing file"
    assert cella.foreground() == Qt.red


def test_in_italiano_l_evidenziazione_non_cambia(monkeypatch):
    from qgis.PyQt.QtCore import Qt

    wizard = apri_wizard(monkeypatch, "it")
    pagina = wizard.pagina_verifica
    pagina._riempi(pagina.tabella, [("file mancante",), ("ok",)])

    assert pagina.tabella.item(0, 0).foreground() == Qt.red
    assert pagina.tabella.item(1, 0).foreground() is None


def test_il_marcatore_arriva_dalla_lingua(monkeypatch):
    """Il marcatore dell'evidenziazione è testo utente, non codice."""
    for lingua in strings.LINGUE:
        assert isinstance(strings.STRINGHE[lingua]["marcatore_errore"], str)
    assert strings.tr("marcatore_errore", "it") != strings.tr("marcatore_errore", "en")


def test_il_si_della_tabella_discovery_e_tradotto(monkeypatch, tmp_path):
    cartella = tmp_path / "foto"
    cartella.mkdir()
    (cartella / "SS_0001.jpg").write_bytes(b"\xff\xd8\xff\xe0finto")
    sorgente = crea_layer_sorgente(source="/tmp/campione.gdb|layername=fotorilievo")
    progetto_con(layer_sorgente=sorgente)
    wizard = apri_wizard(monkeypatch, "en")
    wizard.layer_sorgente = sorgente
    pagina = wizard.pagina_discovery
    pagina.cartella.setText(str(cartella))
    pagina.scansiona()

    colonna_nome = [pagina.tabella.horizontalHeaderLabels().index(strings.tr("col_nome", "en"))]
    valori = {pagina.tabella.item(r, colonna_nome[0]).text()
              for r in range(pagina.tabella.rowCount())}
    assert strings.tr("sì", "en") in valori
    assert "sì" not in valori
    assert strings.tr("sì", "it") not in valori


def test_il_placeholder_della_formula_e_tradotto(monkeypatch):
    wizard = apri_wizard(monkeypatch, "en")
    assert wizard.pagina_naming.formula.placeholderText() == strings.tr("formula_esempio", "en")
    assert "CODICE" not in wizard.pagina_naming.formula.placeholderText()


def test_i_dialoghi_csv_usano_il_filtro_tradotto(monkeypatch):
    from qgis.PyQt.QtWidgets import QFileDialog

    wizard = apri_wizard(monkeypatch, "en")
    pagina = wizard.pagina_naming
    registrati = []

    def spia(parent, titolo, cartella="", filtro="", *args, **kwargs):
        registrati.append((titolo, filtro))
        return ("", "")               # dialogo annullato

    monkeypatch.setattr(QFileDialog, "getOpenFileName", staticmethod(spia))
    pagina.scegli_csv()

    assert registrati == [(strings.tr("csv_file", "en"),
                           f"{strings.tr('filtro_csv', 'en')};;"
                           f"{strings.tr('filtro_tutti_i_file', 'en')}")]


def test_in_modalita_csv_senza_file_il_messaggio_e_tradotto(monkeypatch):
    wizard = apri_wizard(monkeypatch, "en")
    pagina = wizard.pagina_naming
    pagina.radio_csv.setChecked(True)
    assert pagina.validatePage() is False

    dialogo = ultimo_dialogo("warning")
    assert dialogo["titolo"] == strings.tr("attenzione_titolo", "en")
    assert dialogo["testo"] == strings.tr("csv_non_scelto", "en")
    assert "CSV" in dialogo["testo"]


def test_in_modalita_formula_vuota_il_messaggio_e_tradotto(monkeypatch):
    wizard = apri_wizard(monkeypatch, "en")
    pagina = wizard.pagina_naming
    pagina.radio_formula.setChecked(True)
    assert pagina.validatePage() is False

    dialogo = ultimo_dialogo("warning")
    assert dialogo["testo"] == strings.tr("formula_manca", "en")


def test_prova_formula_non_usa_il_messaggio_come_titolo(monkeypatch):
    """Il titolo del QMessageBox è un titolo, non il messaggio ripetuto."""
    wizard = apri_wizard(monkeypatch, "it")
    pagina = wizard.pagina_naming
    pagina.formula.setText("")                 # formula vuota = errore, non avviso
    pagina.prova_formula()

    dialogo = ultimo_dialogo("warning")
    assert dialogo["titolo"] == strings.tr("formula_non_valida_titolo", "it")
    assert dialogo["testo"].startswith("Formula non valida: ")
    assert dialogo["titolo"] != dialogo["testo"]


def test_gli_avvisi_del_csv_finiscono_nei_conteggi(monkeypatch, tmp_path):
    """`esito_avvisi` non era mai mostrato: il numero di avvisi del CSV è utile."""
    wizard = apri_wizard(monkeypatch, "it")
    wizard.elenco_csv = naming.ElencoCsv(avvisi=[("chiavi_duplicate", "2"),
                                                 ("colonna_mancante", "NOME")])
    candidati = [naming.CandidatoAllegato(id_parent="{X}", campo_foto="filefoto",
                                          nome_allegato="a.jpg", nome_originale="a.jpg",
                                          stato="ok")]
    monkeypatch.setattr(wizard.pagina_naming, "costruisci_candidati",
                        lambda salva=True: list(candidati))
    wizard.pagina_naming.aggiorna_anteprima()

    assert strings.tr("esito_avvisi", "it", n=2) in wizard.pagina_naming.conteggi.text()
