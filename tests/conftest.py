# conftest.py — fondamenta dei test: finto QGIS + fixture condivise.
#
# pytest carica questo file PRIMA di raccogliere i test, quindi i moduli finti
# finiscono in sys.modules prima che qualsiasi test importi `qgis.*`. Cosi' i
# test girano su una macchina senza QGIS/GDAL (questa VM e la CI).
#
# Nulla qui dentro conosce i nomi interni del plugin: le fixture costruiscono
# layer e tabelle allegati generici e li mettono a disposizione dei test.

from __future__ import annotations

import sys
from pathlib import Path

import pytest

_RADICE = Path(__file__).resolve().parent.parent
_CARTELLA_TEST = Path(__file__).resolve().parent

# `import gdb_attacher...` deve funzionare senza installare il pacchetto.
for _percorso in (str(_RADICE), str(_CARTELLA_TEST)):
    if _percorso not in sys.path:
        sys.path.insert(0, _percorso)

import fake_qgis                                            # noqa: E402

fake_qgis.install()                                         # noqa: E402

from fake_qgis import (                                     # noqa: E402
    GUID_1, GUID_2, NULL, FakeProject, REGISTRO_DIALOGHI,
    crea_layer_attach, crea_layer_sorgente, risposte,
)


# ---------------------------------------------------------------------------
# Isolamento: ogni test parte da progetto/dialoghi/risposte puliti.

@pytest.fixture(autouse=True)
def stato_qgis_pulito():
    fake_qgis.azzera_tutto()
    yield
    fake_qgis.azzera_tutto()


# ---------------------------------------------------------------------------
# Fixture base

@pytest.fixture
def qcore():
    """Il modulo finto `qgis.core`."""
    import qgis.core
    return sys.modules["qgis.core"]


@pytest.fixture
def qgis_finto():
    """L'intero pacchetto finto `qgis` (per testare il finto stesso)."""
    import qgis
    return sys.modules["qgis"]


@pytest.fixture
def progetto():
    """`QgsProject.instance()` ripulito: registra layer con addMapLayer()."""
    return FakeProject.instance()


@pytest.fixture
def layer_sorgente():
    """Layer sorgente finto: GLOBALID + campi foto, 2 feature di default."""
    return crea_layer_sorgente()


@pytest.fixture
def layer_attach():
    """Tabella allegati finta (6 campi standard), di default vuota."""
    return crea_layer_attach()


@pytest.fixture
def progetto_con_layer(progetto):
    """Progetto con layer sorgente + tabella allegati gia' caricati.

    Riproduce lo stato in cui il wizard trova i layer: gli stessi nomi che i due
    script in repo si aspettano (`<layer>` e `<layer>__ATTACH`).
    """
    sorgente = crea_layer_sorgente()
    allegati = crea_layer_attach()
    progetto.addMapLayer(sorgente)
    progetto.addMapLayer(allegati)
    return {"progetto": progetto, "sorgente": sorgente, "allegati": allegati}


@pytest.fixture
def cartella_foto(tmp_path):
    """Cartella con file finti da allegare: foto, sottocartella, pdf, nome con apice."""
    base = tmp_path / "foto"
    base.mkdir()
    (base / "SS_0001.jpg").write_bytes(b"\xff\xd8\xff\xe0 finto-jpeg")
    (base / "ACQ_2.png").write_bytes(b"\x89PNG finto-png")
    (base / "documento.pdf").write_bytes(b"%PDF-1.4 finto-pdf")
    (base / "foto d'interno.jpg").write_bytes(b"\xff\xd8\xff\xe0 apice")
    sottocartella = base / "contatore"
    sottocartella.mkdir()
    (sottocartella / "ACQ_1.jpg").write_bytes(b"\xff\xd8\xff\xe0 sottocartella")
    return base


@pytest.fixture
def carica_modulo():
    """Funzione per importare un file .py del plugin per percorso.

    Esempio: `mod = carica_modulo("gdb_attacher/naming.py")`
    """
    return fake_qgis.carica


# ---------------------------------------------------------------------------
# Comodita' per asserzioni

@pytest.fixture
def dialoghi():
    """Registro dei QMessageBox/QInputDialog/QFileDialog aperti durante il test."""
    return REGISTRO_DIALOGHI


@pytest.fixture
def risposte_dialoghi():
    """Code di risposte da preimpostare (item/testo/directory/file/si_no)."""
    return risposte


# Riesportati per comodita' dei test (`from conftest import GUID_1` non si usa:
# i test importano direttamente da fake_qgis).
__all__ = [
    "NULL", "GUID_1", "GUID_2", "crea_layer_sorgente", "crea_layer_attach",
]
