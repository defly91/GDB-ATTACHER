#!/usr/bin/env bash
# build_plugin_zip.sh — crea lo zip installabile del plugin QGIS GDB-Attacher.
#
# Lo zip si installa in QGIS da "Plugin > Gestisci e installa plugin > Installa
# da ZIP": dentro c'e' la cartella del plugin (es. gdb_attacher/) con
# metadata.txt, __init__.py, LICENSE, i moduli .py e i QML di default — e NIENTE
# tests/, docs/, .github/, cache o file di build.
#
# USO
#   scripts/build_plugin_zip.sh                      # gdb_attacher/ -> dist/
#   scripts/build_plugin_zip.sh percorso/plugin      # cartella del plugin
#   scripts/build_plugin_zip.sh percorso/plugin out/ # anche cartella di uscita
#   PLUGIN_DIR=... OUT_DIR=... scripts/build_plugin_zip.sh
#
# Lo zip si chiama <nome_cartella>-<versione>.zip dove la versione arriva da
# metadata.txt. Esce con codice 1 e messaggio chiaro se la cartella del plugin,
# metadata.txt o LICENSE mancano. Lo zip si costruisce con python3 (zipfile):
# nessuna dipendenza dal binario `zip`.

set -euo pipefail

RADICE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PLUGIN_DIR="${1:-${PLUGIN_DIR:-$RADICE/gdb_attacher}}"
OUT_DIR="${2:-${OUT_DIR:-$RADICE/dist}}"
NOME_PLUGIN="$(basename "$PLUGIN_DIR")"
# QGIS pretende il file LICENSE (senza estensione) nel pacchetto del plugin: la
# copia canonica sta nella radice del repo e viene inserita nello zip.
LICENZA="${LICENZA:-$RADICE/LICENSE}"

if [ ! -d "$PLUGIN_DIR" ]; then
  echo "ERRORE: cartella del plugin non trovata: $PLUGIN_DIR" >&2
  echo "        crea la cartella (di norma gdb_attacher/) oppure passala come" >&2
  echo "        primo argomento o in PLUGIN_DIR." >&2
  exit 1
fi

if [ ! -f "$PLUGIN_DIR/metadata.txt" ]; then
  echo "ERRORE: manca $PLUGIN_DIR/metadata.txt: senza metadata.txt QGIS non" >&2
  echo "        riconosce il plugin e lo zip non e' installabile." >&2
  exit 1
fi

VERSIONE="$(sed -n 's/^[[:space:]]*version[[:space:]]*=[[:space:]]*//p' \
            "$PLUGIN_DIR/metadata.txt" | head -1 | tr -d '\r' | tr -d '[:space:]')"
VERSIONE="${VERSIONE:-0.0.0}"

mkdir -p "$OUT_DIR"
ZIP="$OUT_DIR/${NOME_PLUGIN}-${VERSIONE}.zip"

python3 - "$PLUGIN_DIR" "$ZIP" "$NOME_PLUGIN" "$LICENZA" <<'PY'
"""Comprime la cartella del plugin escludendo i file che non devono uscire.

Controlla anche i file obbligatori del pacchetto QGIS: metadata.txt, __init__.py
e LICENSE (incluso nello zip, copiandolo dalla radice del repo se serve).
"""
import os
import sys
import zipfile

plugin_dir, zip_path, nome, licenza = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]

# Cartelle escluse a qualunque profondita' (tests e docs non finiscono nello zip).
DIR_ESCLUSE = {
    "tests", "test", "docs", ".github", "__pycache__", ".git", ".pytest_cache",
    ".venv", "venv", "dist", "build", ".mypy_cache", ".ruff_cache",
}
# Estensioni e nomi di file che non servono nel pacchetto.
EST_ESCLUSE = {".pyc", ".pyo", ".zip", ".egg-info", ".bak", ".tmp", ".orig", ".swp", ".log"}
NOMI_ESCLUSI = {".DS_Store", "Thumbs.db", ".gitignore"}
OBBLIGATORI = {"metadata.txt", "__init__.py", "LICENSE"}

if os.path.exists(zip_path):
    os.remove(zip_path)

inclusi = []
with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
    for radice, dirs, files in os.walk(plugin_dir):
        dirs[:] = sorted(d for d in dirs if d not in DIR_ESCLUSE)
        for f in sorted(files):
            if f in NOMI_ESCLUSI or os.path.splitext(f)[1].lower() in EST_ESCLUSE:
                continue
            percorso = os.path.join(radice, f)
            relativo = os.path.relpath(percorso, plugin_dir)
            # La cartella del plugin sta in cima allo zip: gdb_attacher/metadata.txt
            arcname = "/".join([nome] + relativo.split(os.sep))
            z.write(percorso, arcname)
            inclusi.append(arcname)

    # LICENSE: obbligatorio dentro il pacchetto (QGIS lo vuole senza estensione).
    dest = "/".join([nome, "LICENSE"])
    if dest not in inclusi:
        sorgente = licenza if os.path.isfile(licenza) else os.path.join(plugin_dir, "LICENSE")
        if not os.path.isfile(sorgente):
            sys.stderr.write(
                "ERRORE: manca il file LICENSE (cercato in %s e in %s).\n"
                "        QGIS richiede LICENSE nella radice del plugin.\n"
                % (licenza, os.path.join(plugin_dir, "LICENSE"))
            )
            sys.exit(1)
        z.write(sorgente, dest)
        inclusi.append(dest)

    # Controllo finale dei file obbligatori del pacchetto.
    mancanti = sorted(n for n in OBBLIGATORI if "/".join([nome, n]) not in inclusi)
    if mancanti:
        sys.stderr.write("ERRORE: file obbligatori mancanti nello zip: %s\n" % ", ".join(mancanti))
        sys.exit(1)

if not inclusi:
    sys.stderr.write("ERRORE: nessun file da impacchettare in %s\n" % plugin_dir)
    sys.exit(1)

print("file inclusi nello zip: %d" % len(inclusi))
print("obbligatori presenti: %s" % ", ".join(sorted(OBBLIGATORI)))
PY

echo "OK: creato $ZIP"
echo "    installalo in QGIS da: Plugin > Gestisci e installa plugin > Installa da ZIP"
