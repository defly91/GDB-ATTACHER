#!/usr/bin/env bash
# verifica_tutto.sh — tutte le verifiche del plugin, in ordine di costo.
#
#   1. suite pytest (finto QGIS): veloce, sempre eseguibile;
#   2. verifica dentro un QGIS 3.x vero (container): import, QgsExpression, QML, wizard;
#   3. end-to-end su un FileGDB vero creato con GDAL (container): scrittura, dedup, annullo.
#
# I passi 2 e 3 si saltano con un avviso se Docker non c'e' o se l'immagine QGIS non e'
# stata scaricata: la suite pytest resta comunque il risultato principale.
#
# USO
#   scripts/verifica_tutto.sh                 # tutto
#   SOLO_PYTEST=1 scripts/verifica_tutto.sh   # solo la suite veloce
#   IMMAGINE_QGIS3=qgis/qgis:release-3_34 IMMAGINE_QGIS4=qgis/qgis:stable scripts/verifica_tutto.sh
#
# Immagini di riferimento:
#   docker pull qgis/qgis:release-3_34   # QGIS 3.x (target del plugin, GDAL 3.4)
#   docker pull qgis/qgis:stable         # QGIS 4.x ma GDAL ≥ 3.6: serve per l'end-to-end

set -uo pipefail

RADICE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
IMMAGINE_QGIS3="${IMMAGINE_QGIS3:-qgis/qgis:release-3_34}"
IMMAGINE_QGIS4="${IMMAGINE_QGIS4:-qgis/qgis:stable}"
esiti=()

registra() { esiti+=("$1|$2|$3"); }

# ---------------------------------------------------------------- 1. pytest
if [ -n "${PYTHON_VENV:-}" ] && [ -x "${PYTHON_VENV}/bin/python" ]; then
  PY="${PYTHON_VENV}/bin/python"
else
  PY="$(command -v python3)"
fi

echo "== 1/3 suite pytest (finto QGIS) =="
if [ -z "$PY" ]; then
  registra "pytest" "SALTATO" "python3 non trovato"
else
  if (cd "$RADICE" && "$PY" -m pytest -q); then
    registra "pytest" "OK" "suite verde"
  else
    registra "pytest" "FALLITO" "vedi output sopra"
  fi
fi

if [ -n "${SOLO_PYTEST:-}" ]; then
  printf '\n== Riepilogo ==\n'
  for riga in "${esiti[@]}"; do
    printf '  %-10s %-9s %s\n' "${riga%%|*}" "$(echo "$riga" | cut -d'|' -f2)" "${riga##*|}"
  done
  exit 0
fi

# ---------------------------------------------------------------- 2. QGIS 3.x
echo
echo "== 2/3 verifica in QGIS 3.x vero ($IMMAGINE_QGIS3) =="
if ! command -v docker >/dev/null; then
  registra "qgis3" "SALTATO" "docker non disponibile"
elif ! docker image inspect "$IMMAGINE_QGIS3" >/dev/null 2>&1; then
  registra "qgis3" "SALTATO" "immagine assente: docker pull $IMMAGINE_QGIS3"
elif docker run --rm --memory=1500m -e QT_QPA_PLATFORM=offscreen -e REPO=/repo \
      -e PYTHONPATH=/repo:/usr/share/qgis/python --entrypoint python3 \
      -v "$RADICE":/repo:ro "$IMMAGINE_QGIS3" /repo/scripts/verifica_qgis_reale.py; then
  registra "qgis3" "OK" "6 controlli su 6"
else
  registra "qgis3" "FALLITO" "vedi output sopra"
fi

# ---------------------------------------------------------------- 3. end-to-end
echo
echo "== 3/3 end-to-end su FileGDB vero ($IMMAGINE_QGIS4) =="
if ! command -v docker >/dev/null; then
  registra "e2e" "SALTATO" "docker non disponibile"
elif ! docker image inspect "$IMMAGINE_QGIS4" >/dev/null 2>&1; then
  registra "e2e" "SALTATO" "immagine assente: docker pull $IMMAGINE_QGIS4"
elif docker run --rm --memory=1500m -e QT_QPA_PLATFORM=offscreen -e REPO=/repo \
      -e PYTHONPATH=/repo:/usr/share/qgis/python --entrypoint python3 \
      -v "$RADICE":/repo:ro "$IMMAGINE_QGIS4" /repo/scripts/e2e_filegdb.py; then
  registra "e2e" "OK" "11 controlli su 11"
else
  registra "e2e" "FALLITO" "vedi output sopra (servono GDAL >= 3.6 e driver OpenFileGDB scrivibile)"
fi

printf '\n== Riepilogo ==\n'
uscita=0
for riga in "${esiti[@]}"; do
  nome="${riga%%|*}"
  resto="${riga#*|}"
  stato="${resto%%|*}"
  dettaglio="${resto#*|}"
  printf '  %-10s %-9s %s\n' "$nome" "$stato" "$dettaglio"
  [ "$stato" = "FALLITO" ] && uscita=1
done
exit $uscita
