# -*- coding: utf-8 -*-
"""Test di logica pura su ``core/attach.py`` (GUID, mime, riconoscimento FileGDB, backup).

Niente QGIS: le funzioni di verifica/scrittura che hanno bisogno di QGIS non vengono
toccate qui (le prova l'utente in QGIS). Le funzioni provate sono quelle che decidono
*cosa* si scrive nel geodatabase: normalizzazione dei GUID, mime, chiave di
deduplicazione e il backup del ``.gdb``.
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from gdb_attacher.core import attach  # noqa: E402


# ---------------------------------------------------------------- GUID


@pytest.mark.parametrize("grezzo,atteso", [
    ("{AbC-Def}", "ABC-DEF"),
    ("abc-def", "ABC-DEF"),
    ("  { ABC }  ", "ABC"),
    (None, ""),
    ("", ""),
    ("   ", ""),
])
def test_normalizza_guid(grezzo, atteso):
    assert attach.normalizza_guid(grezzo) == atteso


@pytest.mark.parametrize("grezzo,atteso", [
    ("abc-def", "{ABC-DEF}"),
    ("{AbC-Def}", "{ABC-DEF}"),
    (None, ""),
    ("", ""),
])
def test_guid_con_graffe(grezzo, atteso):
    """``REL_GLOBALID`` va scritto **con** le graffe e in maiuscolo (ticket 02)."""
    assert attach.guid_con_graffe(grezzo) == atteso


def test_chiave_dedup_normalizza_il_guid_e_lascia_il_nome_verbatim():
    """Il GUID è normalizzato (graffe/case), ``ATT_NAME`` resta com'è (ticket 06)."""
    assert attach.chiave_dedup("abc", "O'Brien.JPG") == attach.chiave_dedup("{ABC}", "O'Brien.JPG")
    assert attach.chiave_dedup("abc", "a.jpg") != attach.chiave_dedup("abc", "A.jpg")


def test_chiave_dedup_rifiuta_parent_nullo():
    """Senza GlobalID non si scrive: la chiave è ``None`` e il batch salta la riga."""
    assert attach.chiave_dedup("", "a.jpg") is None
    assert attach.chiave_dedup(None, "a.jpg") is None


# ---------------------------------------------------------------- mime


@pytest.mark.parametrize("percorso,atteso", [
    ("foto.JPG", "image/jpeg"),
    ("foto.jpeg", "image/jpeg"),
    ("pianta.png", "image/png"),
    ("scansione.tiff", "image/tiff"),
    ("relazione.pdf", "application/pdf"),
    ("video.mp4", "video/mp4"),
    ("senza_estensione", "application/octet-stream"),
    ("strano.xyz", "application/octet-stream"),
])
def test_indovina_content_type(percorso, atteso):
    """Corregge il difetto dello script batch (``image/jpeg`` hardcoded anche per i PDF)."""
    assert attach.indovina_content_type(percorso) == atteso


# ---------------------------------------------------------------- FileGDB


@pytest.mark.parametrize("origine,atteso", [
    ("C:/dati/mio.gdb", True),
    ("C:/dati/mio.gdb|layername=fotorilievo", True),
    ("C:/dati/mio.gdb|layerid=0", True),
    ("/home/x/mio.GDB", True),
    ("C:/dati/mio.gpkg", False),
    ("C:/dati/mio.gpkg|layername=x", False),
    ("C:/dati/mio.shp", False),
    ("", False),
])
def test_sembra_filegdb(origine, atteso):
    """Solo i layer su ``.gdb`` passano la verifica bloccante (ticket 03)."""
    assert attach.sembra_filegdb(origine) is atteso


@pytest.mark.parametrize("origine,atteso", [
    ("C:/dati/mio.gdb|layername=fotorilievo", "C:/dati/mio.gdb"),
    ("/mnt/x/Area.gdb|layerid=3", "/mnt/x/Area.gdb"),
    ("C:/dati/mio.gpkg", ""),
])
def test_percorso_gdb(origine, atteso):
    """Il percorso del ``.gdb`` serve al backup e alla destinazione predefinita."""
    assert attach.percorso_gdb(origine) == atteso


def test_percorso_backup_predefinito(tmp_path):
    from datetime import datetime

    percorso = str(tmp_path / "Area.gdb")
    backup = attach.percorso_backup_predefinito(percorso, datetime(2026, 9, 15, 14, 30, 5))
    assert backup == str(tmp_path / "Area_backup_20260915_143005.gdb")


def test_backup_gdb_copia_la_cartella(tmp_path):
    """Il backup è una copia fedele della cartella ``.gdb`` (proposto ma aggirabile)."""
    origine = tmp_path / "Area.gdb"
    origine.mkdir()
    (origine / "gdb").write_bytes(b"file di sistema")
    (origine / "a00000001.gdbtable").write_bytes(b"tabella")

    destinazione = attach.backup_gdb(str(origine), str(tmp_path / "copia.gdb"))

    assert os.path.isdir(destinazione)
    assert sorted(os.listdir(destinazione)) == ["a00000001.gdbtable", "gdb"]
    assert (tmp_path / "copia.gdb" / "a00000001.gdbtable").read_bytes() == b"tabella"
    # l'originale non viene toccato
    assert (origine / "a00000001.gdbtable").read_bytes() == b"tabella"


def test_backup_gdb_non_sovrascrive(tmp_path):
    origine = tmp_path / "Area.gdb"
    origine.mkdir()
    destinazione = tmp_path / "esiste.gdb"
    destinazione.mkdir()
    with pytest.raises(OSError):
        attach.backup_gdb(str(origine), str(destinazione))


def test_backup_gdb_cartella_inesistente(tmp_path):
    with pytest.raises(OSError):
        attach.backup_gdb(str(tmp_path / "non_esiste.gdb"))


# ---------------------------------------------------------------- campi (oggetti finti)


class _Campo:
    def __init__(self, nome):
        self._nome = nome

    def name(self):
        return self._nome


class _Campi:
    def __init__(self, nomi):
        self._nomi = list(nomi)

    def __iter__(self):
        return iter(_Campo(n) for n in self._nomi)


class _LayerFinto:
    def __init__(self, nome, campi=()):
        self._nome = nome
        self._campi = _Campi(campi)

    def name(self):
        return self._nome

    def fields(self):
        return self._campi


def test_nome_campo_ignora_il_case():
    """Porta di ``find_field_ci()`` dello script click."""
    layer = _LayerFinto("fotorilievo", ["GLOBALID", "FileFoto", "CODICE"])
    assert attach.nome_campo(layer, attach.NOMI_GLOBALID_SORGENTE) == "GLOBALID"
    assert attach.nome_campo(layer, ("filefoto",)) == "FileFoto"
    assert attach.nome_campo(layer, ("INESISTENTE",)) == ""


def test_risolvi_campi_allegati_rileva_i_mancanti():
    """La tabella allegati deve avere tutti e 6 i campi, altrimenti blocco (ticket 02)."""
    completa = _LayerFinto("x__ATTACH", list(attach.CAMPI_ALLEGATI))
    campi, mancanti = attach.risolvi_campi_allegati(completa)
    assert mancanti == []
    assert campi["ATT_NAME"] == "ATT_NAME"

    parziale = _LayerFinto("x__ATTACH", ["GLOBALID", "ATT_NAME", "DATA"])
    campi, mancanti = attach.risolvi_campi_allegati(parziale)
    assert sorted(mancanti) == ["CONTENT_TYPE", "DATA_SIZE", "REL_GLOBALID"]
    assert set(campi) == {"GLOBALID", "ATT_NAME", "DATA"}


def test_risolvi_campi_allegati_ignora_il_case():
    layer = _LayerFinto("x__ATTACH", [c.lower() for c in attach.CAMPI_ALLEGATI])
    campi, mancanti = attach.risolvi_campi_allegati(layer)
    assert mancanti == []
    assert campi["REL_GLOBALID"] == "rel_globalid"


def test_nome_tabella_allegati():
    assert attach.nome_tabella_allegati("fotorilievo") == "fotorilievo__ATTACH"


def test_verifica_tabella_allegati_assenza_e_incompletezza():
    esito = attach.verifica_tabella_allegati(_LayerFinto("x__ATTACH", ["GLOBALID"]))
    assert esito.presente and not esito.completa
    assert "ATT_NAME" in esito.mancanti

    assente = attach.verifica_tabella_allegati(None)
    assert not assente.presente and not assente.completa


# ---------------------------------------------------------------- lettura file


def test_leggi_bytes(tmp_path):
    percorso = tmp_path / "foto.bin"
    percorso.write_bytes(b"\x00\x01\x02")
    assert attach.leggi_bytes(str(percorso)) == b"\x00\x01\x02"
    with pytest.raises(OSError):
        attach.leggi_bytes(str(tmp_path / "manca.bin"))
