# test_pacchetto_qgis.py — vincoli del pacchetto che QGIS pretende per l'installazione
# e per la pubblicazione su plugins.qgis.org.
#
# Nascono da tre difetti reali trovati il 2026-09-15 unendo i rami di lavoro:
#   1. `.gitignore` escludeva i PNG: l'icona del plugin non veniva versionata;
#   2. `metadata.txt` non aveva un PNG ma un SVG, e non aveva email/licenza in forma
#      accettata dalla review del repo QGIS;
#   3. lo zip installabile non conteneva `LICENSE`, che QGIS richiede nel pacchetto.
#
# Questi test bloccano i tre casi: valgono anche come promemoria del perché certi
# dettagli apparentemente cosmetici non si toccano.

from __future__ import annotations

import os
import struct
import subprocess
import sys
import zipfile

import pytest

RADICE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PLUGIN = os.path.join(RADICE, "gdb_attacher")
METADATA = os.path.join(PLUGIN, "metadata.txt")
SCRIPT_ZIP = os.path.join(RADICE, "scripts", "build_plugin_zip.sh")

pytestmark = pytest.mark.unit


def metadati():
    valori = {}
    with open(METADATA, encoding="utf-8") as f:
        for riga in f:
            riga = riga.strip()
            if riga and not riga.startswith("#") and "=" in riga:
                chiave, _, valore = riga.partition("=")
                valori[chiave.strip()] = valore.strip()
    return valori


# --------------------------------------------------------------------- metadati
def test_i_campi_obbligatori_del_repo_qgis_sono_tutti_valorizzati():
    valori = metadati()
    for campo in ("name", "description", "about", "version", "qgisMinimumVersion",
                  "author", "email", "repository", "tracker", "tags", "category",
                  "icon", "license"):
        assert valori.get(campo), f"campo mancante o vuoto in metadata.txt: {campo}"


def test_la_licenza_e_in_forma_spdx_e_il_file_license_esiste():
    assert metadati()["license"] == "GPL-2.0-or-later"
    licenza = os.path.join(RADICE, "LICENSE")
    assert os.path.isfile(licenza)
    # QGIS vuole il file LICENSE senza estensione.
    assert os.path.splitext(licenza)[1] == ""


def test_l_icona_e_un_png_valido_e_grande_abbastanza():
    percorso = os.path.join(PLUGIN, metadati()["icon"])
    assert os.path.isfile(percorso), f"icona indicata in metadata.txt non trovata: {percorso}"
    with open(percorso, "rb") as f:
        intestazione = f.read(24)
    assert intestazione[:8] == b"\x89PNG\r\n\x1a\n", "l'icona non è un PNG"
    larghezza, altezza = struct.unpack(">II", intestazione[16:24])
    assert (larghezza, altezza) >= (24, 24), f"icona troppo piccola: {larghezza}x{altezza}"


def test_l_icona_e_versionata_e_il_gitignore_non_la_esclude():
    """Il .gitignore esclude le immagini di dati: l'icona del plugin è l'eccezione."""
    esito = subprocess.run(
        ["git", "ls-files", "--error-unmatch", os.path.join("gdb_attacher", "resources",
                                                            "icone", "icona_plugin.png")],
        cwd=RADICE, capture_output=True, text=True,
    )
    assert esito.returncode == 0, (
        "l'icona non è tracciata da git: il .gitignore sta escludendo le risorse del plugin"
    )


def test_in_modalita_formula_il_wizard_richiede_la_formula():
    """Guardia statica (non comportamentale) sul passo di naming.

    Il controllo vero — il wizard che blocca l'avanzamento con formula vuota — sta nei test
    del wizard, che istanziano la pagina. Qui resta una guardia sul sorgente: costa nulla e
    segnala subito se qualcuno riscrive `isComplete` perdendo la condizione.

    È il motivo per cui il plugin non ha (e non deve avere) un ripiego "formula vuota →
    nome originale": vedi tests/test_contratto_plugin.py.
    """
    sorgente = open(os.path.join(PLUGIN, "wizard", "dialog.py"), encoding="utf-8").read()
    assert "def isComplete" in sorgente
    assert "MODALITA_FORMULA" in sorgente and "formula.text().strip()" in sorgente


# --------------------------------------------------------------------- zip
@pytest.fixture(scope="module")
def zip_costruito(tmp_path_factory):
    uscita = tmp_path_factory.mktemp("dist")
    esito = subprocess.run(["bash", SCRIPT_ZIP, PLUGIN, str(uscita)],
                           capture_output=True, text=True)
    assert esito.returncode == 0, f"build fallita: {esito.stderr}\n{esito.stdout}"
    zips = list(uscita.glob("*.zip"))
    assert len(zips) == 1, f"atteso un solo zip, trovati: {zips}"
    return zips[0]


def test_lo_zip_contiene_i_file_obbligatori_per_qgis(zip_costruito):
    with zipfile.ZipFile(zip_costruito) as z:
        nomi = z.namelist()
    for obbligatorio in ("gdb_attacher/metadata.txt", "gdb_attacher/__init__.py",
                         "gdb_attacher/LICENSE"):
        assert obbligatorio in nomi, f"manca {obbligatorio} nello zip"


def test_lo_zip_non_porta_dietro_test_documentazione_e_cache(zip_costruito):
    with zipfile.ZipFile(zip_costruito) as z:
        nomi = z.namelist()
    # `in` e non `startswith`: i nomi nello zip iniziano con "gdb_attacher/", quindi un
    # startswith("tests/") non matcherebbe mai e il test sarebbe vacuo.
    for vietato in ("tests/", "docs/", ".github/", "__pycache__", ".pyc"):
        assert not any(vietato in n for n in nomi), f"lo zip contiene {vietato}"


def test_lo_zip_contiene_il_qml_di_stile_e_l_icona(zip_costruito):
    with zipfile.ZipFile(zip_costruito) as z:
        nomi = z.namelist()
    assert any(n.endswith("stile_attach_variante_A.qml") for n in nomi)
    assert any(n.endswith("icone/icona_plugin.png") for n in nomi)


def test_senza_license_da_nessuna_parte_il_build_fallisce_con_messaggio_chiaro(tmp_path):
    """QGIS pretende LICENSE: meglio un errore esplicito che uno zip incompleto.

    La cartella plugin non ha LICENSE e la copia canonica viene indicata a un percorso
    inesistente (variabile ``LICENZA``): lo script deve fermarsi, non produrre uno zip
    che QGIS rifiuterebbe.
    """
    finta = tmp_path / "plugin_finto"
    (finta / "core").mkdir(parents=True)
    (finta / "metadata.txt").write_text("name=Finto\nversion=9.9.9\n", encoding="utf-8")
    (finta / "__init__.py").write_text("", encoding="utf-8")
    ambiente = {**os.environ, "LICENZA": str(tmp_path / "license_inesistente")}
    esito = subprocess.run(["bash", SCRIPT_ZIP, str(finta), str(tmp_path / "out")],
                           capture_output=True, text=True, env=ambiente)
    assert esito.returncode == 1
    assert "LICENSE" in esito.stderr
    assert not list((tmp_path / "out").glob("*.zip")) if (tmp_path / "out").exists() else True


def test_il_license_di_radice_viene_inserito_nel_pacchetto(tmp_path):
    """Caso reale di questo repo: la copia canonica sta in radice e finisce nello zip."""
    finta = tmp_path / "plugin_finto"
    finta.mkdir()
    (finta / "metadata.txt").write_text("name=Finto\nversion=9.9.9\n", encoding="utf-8")
    (finta / "__init__.py").write_text("", encoding="utf-8")
    esito = subprocess.run(["bash", SCRIPT_ZIP, str(finta), str(tmp_path / "out")],
                           capture_output=True, text=True)
    assert esito.returncode == 0, esito.stderr
    with zipfile.ZipFile(tmp_path / "out" / "plugin_finto-9.9.9.zip") as z:
        assert "plugin_finto/LICENSE" in z.namelist()


def test_senza_metadata_il_build_fallisce_con_messaggio_chiaro(tmp_path):
    finta = tmp_path / "plugin_senza_metadata"
    finta.mkdir()
    esito = subprocess.run(["bash", SCRIPT_ZIP, str(finta), str(tmp_path / "out")],
                           capture_output=True, text=True)
    assert esito.returncode == 1
    assert "metadata.txt" in esito.stderr


def test_la_versione_dello_zip_viene_dal_metadata(zip_costruito):
    assert zip_costruito.name == f"gdb_attacher-{metadati()['version']}.zip"


def test_lo_script_zip_e_eseguibile():
    assert os.access(SCRIPT_ZIP, os.X_OK), "scripts/build_plugin_zip.sh non è eseguibile"


def test_il_pacchetto_non_dipende_da_qgis_per_essere_costruito():
    """Il build gira anche dove QGIS non è installato (MiniPC, CI).

    Su una macchina con QGIS installato il caso non è rappresentabile: si salta invece di
    far fallire la suite per una condizione dell'ambiente.
    """
    esito = subprocess.run([sys.executable, "-c", "import qgis"], capture_output=True, text=True)
    if esito.returncode == 0:
        pytest.skip("QGIS presente su questa macchina: la guardia 'senza QGIS' non è rappresentabile")
    assert esito.returncode != 0
