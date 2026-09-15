# test_packaging.py — verifica lo zip installabile e metadata.txt.
#
# Lo script `scripts/build_plugin_zip.sh` viene eseguito davvero (subprocess) su
# una finta cartella di plugin in una tmp_path: cosi' si controlla il
# comportamento reale del build senza dipendere da gdb_attacher/ (che vive nel
# ramo di lavoro del plugin) e senza toccare il repo.
#
# Gli altri test su metadata.txt si saltano da soli se gdb_attacher/ non c'e'.

from __future__ import annotations

import re
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest

pytestmark = pytest.mark.packaging

RADICE = Path(__file__).resolve().parent.parent
SCRIPT = RADICE / "scripts" / "build_plugin_zip.sh"
PLUGIN_REALE = RADICE / "gdb_attacher"

METADATA_FINTO = """\
[general]
name=GDB-Attacher
qgisMinimumVersion=3.28
description=Allega foto e file alle feature di un FileGDB
version=1.2.3
author=Stefano
email=stefano@example.com
about=Plugin di prova
tracker=https://example.com/issues
repository=https://example.com/repo
license=GPL-2.0-or-later
"""


def esegui(args=(), **env_extra):
    """Lancia lo script di build e restituisce il CompletedProcess."""
    import os

    ambiente = dict(os.environ)
    ambiente.update({k: str(v) for k, v in env_extra.items()})
    return subprocess.run(
        ["bash", str(SCRIPT), *[str(a) for a in args]],
        capture_output=True, text=True, env=ambiente, timeout=120,
    )


def crea_plugin_finto(cartella: Path, nome: str = "gdb_attacher",
                      metadata: str = METADATA_FINTO) -> Path:
    """Costruisce una finta cartella di plugin, con anche robaccia da escludere."""
    plugin = cartella / nome
    plugin.mkdir(parents=True)
    if metadata is not None:
        (plugin / "metadata.txt").write_text(metadata, encoding="utf-8")
    (plugin / "__init__.py").write_text(
        "def classFactory(iface):\n    return None\n", encoding="utf-8")
    (plugin / "core").mkdir()
    (plugin / "core" / "naming.py").write_text(
        "MODALITA = ('originale', 'formula', 'csv')\n", encoding="utf-8")
    (plugin / "stile_allegati.qml").write_text("<qgis/>", encoding="utf-8")

    # Roba che NON deve finire nello zip.
    (plugin / "tests").mkdir()
    (plugin / "tests" / "test_x.py").write_text("def test_x(): pass\n", encoding="utf-8")
    (plugin / "docs").mkdir()
    (plugin / "docs" / "guida.md").write_text("# guida\n", encoding="utf-8")
    (plugin / ".github").mkdir()
    (plugin / ".github" / "workflows").mkdir()
    (plugin / ".github" / "workflows" / "ci.yml").write_text("name: x\n", encoding="utf-8")
    (plugin / "__pycache__").mkdir()
    (plugin / "__pycache__" / "naming.cpython-311.pyc").write_bytes(b"\x00\x00")
    (plugin / "note.ipynb.bak").write_text("x", encoding="utf-8")
    return plugin


# ---------------------------------------------------------------------------
# Lo script esiste ed e' eseguibile

def test_lo_script_esiste_ed_e_eseguibile():
    assert SCRIPT.is_file(), "manca scripts/build_plugin_zip.sh"
    assert SCRIPT.stat().st_mode & 0o111, "lo script non e' eseguibile (chmod +x)"


# ---------------------------------------------------------------------------
# Build riuscita

def test_zip_creato_con_contenuto_giusto(tmp_path):
    plugin = crea_plugin_finto(tmp_path)
    uscita = tmp_path / "dist"

    esito = esegui([plugin, uscita])

    assert esito.returncode == 0, esito.stderr
    zip_path = uscita / "gdb_attacher-1.2.3.zip"       # nome-<versione>.zip
    assert zip_path.is_file(), esito.stdout + esito.stderr

    with zipfile.ZipFile(zip_path) as z:
        nomi = z.namelist()
        radici = {n.split("/")[0] for n in nomi}
        assert radici == {"gdb_attacher"}, "unica cartella in cima allo zip"
        assert "gdb_attacher/metadata.txt" in nomi
        assert "gdb_attacher/__init__.py" in nomi
        assert "gdb_attacher/core/naming.py" in nomi
        assert "gdb_attacher/stile_allegati.qml" in nomi
        # metadata.txt dentro lo zip resta leggibile
        assert "GDB-Attacher" in z.read("gdb_attacher/metadata.txt").decode("utf-8")

        for escluso in ("tests/", "docs/", ".github/", "__pycache__/"):
            assert not any(escluso in n for n in nomi), "%s non escluso: %s" % (escluso, nomi)
        assert not any(n.endswith((".pyc", ".bak")) for n in nomi), nomi


def test_zip_usa_il_nome_della_cartella_come_radice(tmp_path):
    plugin = crea_plugin_finto(tmp_path, nome="mio_plugin")
    uscita = tmp_path / "out"

    esito = esegui([plugin, uscita])

    assert esito.returncode == 0, esito.stderr
    with zipfile.ZipFile(uscita / "mio_plugin-1.2.3.zip") as z:
        assert all(n.startswith("mio_plugin/") for n in z.namelist())


def test_variabili_di_ambiente_al_posto_degli_argomenti(tmp_path):
    plugin = crea_plugin_finto(tmp_path)
    uscita = tmp_path / "da_env"

    esito = esegui([], PLUGIN_DIR=plugin, OUT_DIR=uscita)

    assert esito.returncode == 0, esito.stderr
    assert (uscita / "gdb_attacher-1.2.3.zip").is_file()


def test_versione_assente_diventa_0_0_0(tmp_path):
    plugin = crea_plugin_finto(tmp_path)
    testo = METADATA_FINTO.replace("version=1.2.3\n", "")
    (plugin / "metadata.txt").write_text(testo, encoding="utf-8")
    uscita = tmp_path / "dist"

    esito = esegui([plugin, uscita])

    assert esito.returncode == 0, esito.stderr
    assert (uscita / "gdb_attacher-0.0.0.zip").is_file()


# ---------------------------------------------------------------------------
# Errori: messaggi chiari e codice di uscita non zero

def test_cartella_plugin_mancante_da_errore_chiaro(tmp_path):
    mancante = tmp_path / "gdb_attacher_che_non_esiste"

    esito = esegui([mancante, tmp_path / "dist"])

    assert esito.returncode != 0
    assert "ERRORE" in esito.stderr
    assert "non trovata" in esito.stderr
    assert str(mancante) in esito.stderr          # dice quale percorso manca
    assert not (tmp_path / "dist").exists() or not list((tmp_path / "dist").glob("*.zip"))


def test_metadata_txt_mancante_da_errore_chiaro(tmp_path):
    plugin = crea_plugin_finto(tmp_path, metadata=None)

    esito = esegui([plugin, tmp_path / "dist"])

    assert esito.returncode != 0
    assert "ERRORE" in esito.stderr
    assert "metadata.txt" in esito.stderr
    assert not list((tmp_path / "dist").glob("*.zip"))


def test_metadata_txt_senza_version_e_solo_un_avviso(tmp_path):
    """metadata.txt senza chiave version non deve rompere il build."""
    plugin = crea_plugin_finto(tmp_path, metadata="[general]\nname=SenzaVersione\n")

    esito = esegui([plugin, tmp_path / "dist"])

    assert esito.returncode == 0, esito.stderr


# ---------------------------------------------------------------------------
# metadata.txt del plugin vero: controlli di coerenza (se il pacchetto c'e')

def leggi_metadata(percorso: Path) -> dict:
    """Parser minimo INI: chiave=valore, ignorando sezioni e commenti."""
    valori = {}
    for riga in percorso.read_text(encoding="utf-8").splitlines():
        riga = riga.strip()
        if not riga or riga.startswith(("#", ";", "[")):
            continue
        if "=" in riga:
            chiave, _, valore = riga.partition("=")
            valori[chiave.strip()] = valore.strip()
    return valori


@pytest.mark.skipif(not (PLUGIN_REALE / "metadata.txt").is_file(),
                    reason="gdb_attacher/metadata.txt non esiste in questo ramo")
def test_metadata_del_plugin_e_coerente():
    metadata = leggi_metadata(PLUGIN_REALE / "metadata.txt")

    obbligatorie = (
        "name", "qgisMinimumVersion", "description", "version", "author", "email",
        "about", "tracker", "repository", "license",
    )
    mancanti = [c for c in obbligatorie if not metadata.get(c)]
    assert not mancanti, "chiavi mancanti in metadata.txt: %s" % mancanti

    assert re.fullmatch(r"\d+(\.\d+)*", metadata["version"]), \
        "version non e' numerica: %r" % metadata["version"]
    assert metadata["license"].startswith("GPL-2"), \
        "licenza attesa GPLv2+: %r" % metadata["license"]
    assert metadata["name"] == "GDB-Attacher"


@pytest.mark.skipif(not (PLUGIN_REALE / "metadata.txt").is_file(),
                    reason="gdb_attacher/metadata.txt non esiste in questo ramo")
def test_la_cartella_del_plugin_e_quella_giusta():
    """gdb_attacher/ deve contenere __init__.py con classFactory (contratto QGIS)."""
    init = PLUGIN_REALE / "__init__.py"
    assert init.is_file(), "manca gdb_attacher/__init__.py"
    assert "classFactory" in init.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Lo zip del plugin vero (saltato finche' gdb_attacher/ non esiste)

@pytest.mark.skipif(not (PLUGIN_REALE / "metadata.txt").is_file(),
                    reason="gdb_attacher/metadata.txt non esiste in questo ramo")
def test_zip_del_plugin_vero_si_costruisce(tmp_path):
    esito = esegui([PLUGIN_REALE, tmp_path / "dist"])

    assert esito.returncode == 0, esito.stderr
    zip_path = next((tmp_path / "dist").glob("*.zip"))
    with zipfile.ZipFile(zip_path) as z:
        nomi = z.namelist()
    assert "gdb_attacher/metadata.txt" in nomi
    assert not any(vietato in n for n in nomi for vietato in ("tests/", "docs/", ".github/"))


if __name__ == "__main__":       # pragma: no cover
    sys.exit(pytest.main([__file__, "-v"]))
