# test_wizard_stringhe.py — il dizionario IT/EN è un contratto: o è allineato, o
# in interfaccia compare una chiave grezza.
#
# Verifica sistematica (indipendente dal contenuto delle singole stringhe):
#   1. le due lingue hanno lo stesso insieme di chiavi;
#   2. ogni segnaposto combacia fra IT ed EN;
#   3. ogni chiave usata dal wizard (`self.t(...)`, `strings.tr(...)`) esiste in
#      entrambe le lingue — così un refuso non passa la revisione;
#   4. nessuna chiave morta: ogni chiave del dizionario è usata da qualche parte
#      (a parte quelle risolte a runtime dalle mappe codice → chiave).
#
# Marcatura: `unit`.

from __future__ import annotations

import glob
import os
import re
import string as modulo_string
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from gdb_attacher.wizard import strings                             # noqa: E402

pytestmark = pytest.mark.unit

RADICE = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DIALOG = os.path.join(RADICE, "gdb_attacher", "wizard", "dialog.py")

#: Chiavi che il wizard usa per nome dentro il codice (`self.t("...")`).
CHIAVI_NEL_CODICE = re.compile(r"""(?:\.t\(|strings\.tr\()\s*["']([a-zà-ùA-Z_0-9]+)["']""")


def segnaposto(testo):
    return {nome for _, nome, _, _ in modulo_string.Formatter().parse(testo) if nome}


def sorgenti_del_repo():
    """Tutti i file di testo del repo (codice, test, script, documentazione)."""
    modelli = ("gdb_attacher/**/*.py", "tests/**/*.py", "scripts/*.py", "ci/*",
               "*.md", "docs/**/*.md", ".scratch/gdb-attacher-plugin/**/*.md",
               "prototype/**/*.py")
    percorsi = []
    for modello in modelli:
        percorsi += glob.glob(os.path.join(RADICE, modello), recursive=True)
    return [p for p in percorsi
            if "__pycache__" not in p
            and os.path.basename(p) != "strings.py"]


# ---------------------------------------------------------------------------
# 1-2. Le due lingue sono lo specchio l'una dell'altra

def test_le_due_lingue_hanno_le_stesse_chiavi():
    assert strings.chiavi_mancanti("it") == []
    assert strings.chiavi_mancanti("en") == []
    assert set(strings.STRINGHE["it"]) == set(strings.STRINGHE["en"])


def test_nessun_testo_vuoto():
    for lingua, dizionario in strings.STRINGHE.items():
        for chiave, testo in dizionario.items():
            assert isinstance(testo, str) and testo.strip(), f"{lingua}/{chiave} vuoto"


def test_stessi_segnaposto_nelle_due_lingue():
    for chiave, testo_it in strings.STRINGHE["it"].items():
        testo_en = strings.STRINGHE["en"][chiave]
        assert segnaposto(testo_it) == segnaposto(testo_en), chiave


def test_le_chiavi_delle_mappe_codice_chiave_esistono_in_entrambe_le_lingue():
    for mappa in (strings.TESTI_STATO, strings.TESTI_PROBLEMA):
        for codice, chiave in mappa.items():
            for lingua in strings.LINGUE:
                assert chiave in strings.STRINGHE[lingua], f"{codice} → {chiave} ({lingua})"


# ---------------------------------------------------------------------------
# 3. Le chiavi usate dal wizard esistono davvero

def test_le_chiavi_usate_dal_wizard_esistono():
    with open(DIALOG, encoding="utf-8") as flusso:
        sorgente = flusso.read()
    usate = set(CHIAVI_NEL_CODICE.findall(sorgente))
    assert usate, "nessuna chiave trovata nel wizard: il test non sta guardando nulla"

    for chiave in sorted(usate):
        for lingua in strings.LINGUE:
            assert chiave in strings.STRINGHE[lingua], f"{chiave} manca in {lingua}"


def test_ogni_chiave_usata_dal_wizard_ha_un_testo_utilizzabile():
    """Il testo non è la chiave stessa (refuso) e non lascia segnaposto vuoti."""
    with open(DIALOG, encoding="utf-8") as flusso:
        usate = set(CHIAVI_NEL_CODICE.findall(flusso.read()))
    for chiave in sorted(usate):
        for lingua in strings.LINGUE:
            assert strings.STRINGHE[lingua][chiave] != chiave


# ---------------------------------------------------------------------------
# 4. Nessuna chiave morta

def _chiavi_indirette():
    """Chiavi risolte a runtime dalle mappe codice → chiave."""
    return set(strings.TESTI_STATO.values()) | set(strings.TESTI_PROBLEMA.values())


def test_nessuna_chiave_morta():
    """Una chiave che nessuno usa è codice morto: prima o poi diverge.

    Restano fuori solo le chiavi risolte a runtime (`TESTI_STATO`,
    `TESTI_PROBLEMA`), che non compaiono come letterale ma sono usate eccome.
    """
    testo = ""
    for percorso in sorgenti_del_repo():
        with open(percorso, encoding="utf-8", errors="ignore") as flusso:
            testo += flusso.read() + "\n"

    indirette = _chiavi_indirette()
    morte = [chiave for chiave in sorted(strings.STRINGHE["it"])
             if chiave not in indirette
             and f'"{chiave}"' not in testo and f"'{chiave}'" not in testo]
    assert morte == [], f"chiavi mai usate: {morte}"


def test_il_dizionario_vale_per_entrambe_le_lingue_anche_dopo_modifiche():
    """Il numero di chiavi è lo stesso: un'aggiunta a metà si vede subito."""
    assert len(strings.STRINGHE["it"]) == len(strings.STRINGHE["en"])
    assert len(strings.STRINGHE["it"]) >= 180
