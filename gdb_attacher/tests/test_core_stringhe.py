# -*- coding: utf-8 -*-
"""Test sul modulo delle stringhe (``wizard/strings.py``).

Le stringhe sono il contratto IT/EN del ticket 03: se le due lingue divergono, in
interfaccia compare una chiave grezza. Questi test bloccano quella regressione senza
aprire QGIS (il modulo non importa Qt a livello di modulo).
"""

import os
import string as modulo_string
import sys

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from gdb_attacher.wizard import strings  # noqa: E402


def _segnaposto(testo):
    return {nome for _, nome, _, _ in modulo_string.Formatter().parse(testo) if nome}


def test_le_due_lingue_hanno_le_stesse_chiavi():
    """``chiavi_mancanti`` è vuoto: nessuna chiave presente in una lingua e non nell'altra."""
    assert strings.chiavi_mancanti("it") == []
    assert strings.chiavi_mancanti("en") == []
    assert set(strings.STRINGHE["it"]) == set(strings.STRINGHE["en"])


def test_nessun_testo_vuoto():
    for lingua, dizionario in strings.STRINGHE.items():
        for chiave, testo in dizionario.items():
            assert isinstance(testo, str) and testo.strip(), f"{lingua}/{chiave} vuoto"


def test_stessi_segnaposto_nelle_due_lingue():
    """Un segnaposto dimenticato in traduzione darebbe un ``KeyError`` a runtime."""
    for chiave, testo_it in strings.STRINGHE["it"].items():
        testo_en = strings.STRINGHE["en"][chiave]
        assert _segnaposto(testo_it) == _segnaposto(testo_en), chiave


def test_chiavi_usate_dai_codici_di_stato():
    """Ogni codice di stato/problema del core ha la sua traduzione, in entrambe le lingue."""
    for codice, chiave in strings.TESTI_STATO.items():
        for lingua in strings.LINGUE:
            assert chiave in strings.STRINGHE[lingua], f"{codice} -> {chiave} ({lingua})"
    for codice, chiave in strings.TESTI_PROBLEMA.items():
        for lingua in strings.LINGUE:
            assert chiave in strings.STRINGHE[lingua], f"{codice} -> {chiave} ({lingua})"


def test_lingue_disponibili():
    assert strings.lingue_disponibili() == ("it", "en")
    assert strings.LINGUA_DEFAULT == "it"


def test_tr_traduce_e_sostituisce():
    assert strings.tr("totale_ok", "it", n=3) == "Da aggiungere: 3"
    assert strings.tr("totale_ok", "en", n=3) == "To add: 3"


def test_tr_ricade_sull_italiano_e_poi_sulla_chiave():
    """Una chiave mancante non fa crashare l'interfaccia: si vede il difetto, non un errore."""
    assert strings.tr("chiave_del_tutto_inesistente", "it") == "chiave_del_tutto_inesistente"
    assert strings.tr("menu_root", "zz") == strings.STRINGHE["it"]["menu_root"]


def test_tr_con_segnaposto_mancante_non_esplode():
    assert strings.tr("totale_ok", "it") == "Da aggiungere: {n}"


def test_imposta_lingua_rifiuta_valori_ignoti():
    """Fuori da QGIS il salvataggio non è possibile: la funzione ritorna il default."""
    assert strings.imposta_lingua("zz") == "it"
    assert strings.imposta_lingua("EN") == "en"


def test_lingua_corrente_predefinita_italiano(monkeypatch):
    monkeypatch.setenv("LANG", "it_IT.UTF-8")
    monkeypatch.delenv("LC_ALL", raising=False)
    assert strings.lingua_corrente() == "it"


def test_le_etichette_del_menu_esistono():
    for chiave in ("menu_root", "azione_wizard", "azione_info", "azione_lingua", "info_testo"):
        assert strings.tr(chiave, "it") != chiave
        assert strings.tr(chiave, "en") != chiave


def test_i_qfield_resta_fuori_perimetro_dal_testo_informativo():
    """Ticket 07: QField non è in v1, e l'informativa del plugin lo dice."""
    for lingua in strings.LINGUE:
        assert "QField" in strings.STRINGHE[lingua]["info_testo"]


@pytest.mark.parametrize("chiave", ["titolo_wizard", "pagina_layer", "pagina_verifica",
                                    "pagina_discovery", "pagina_campi", "pagina_naming",
                                    "pagina_esegui", "pagina_stile"])
def test_le_pagine_del_wizard_hanno_un_titolo(chiave):
    for lingua in strings.LINGUE:
        assert strings.STRINGHE[lingua][chiave].strip()
