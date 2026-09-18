# test_icona_generata.py — l'icona versionata e' quella che lo script genera.
#
# Nasce da due difetti reali:
#   1. `scripts/genera_icona.py` disegnava a scala 1:1 unita'->pixel di un buffer
#      4x, quindi il PNG 64x64 conteneva l'icona rimpicciolita a un terzo in un
#      angolo: il file era un PNG valido e "abbastanza grande" per i test di
#      packaging, ma visivamente rotto. Nessuno se ne accorgeva perche' QGIS in
#      toolbar carica l'SVG, non il PNG;
#   2. con l'icona ridisegnata a mano, SVG e PNG possono divergere: si ritocca
#      l'uno e ci si dimentica dell'altro.
#
# Qui la geometria e' una sola (`scripts/genera_icona.py`): questi test
# rigenerano entrambi i file e li confrontano con quelli versionati.

from __future__ import annotations

import importlib.util
import os
import sys
import zlib

import pytest

RADICE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ICONE = os.path.join(RADICE, "gdb_attacher", "resources", "icone")
SVG = os.path.join(ICONE, "icona_plugin.svg")
PNG = os.path.join(ICONE, "icona_plugin.png")
GENERATORE = os.path.join(RADICE, "scripts", "genera_icona.py")

pytestmark = pytest.mark.unit


def generatore():
    """Carica `scripts/genera_icona.py` come modulo (non e' un pacchetto)."""
    if RADICE not in sys.path:
        sys.path.insert(0, RADICE)
    spec = importlib.util.spec_from_file_location("genera_icona", GENERATORE)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


def pixel_del_png(percorso):
    """Decodifica il PNG: righe RGBA, senza filtri (li scrive cosi' `scrivi_png`)."""
    dati = open(percorso, "rb").read()
    assert dati[:8] == b"\x89PNG\r\n\x1a\n", "non e' un PNG"
    larghezza = int.from_bytes(dati[16:20], "big")
    altezza = int.from_bytes(dati[20:24], "big")

    idat = b""
    posizione = 8
    while posizione < len(dati):
        lunghezza = int.from_bytes(dati[posizione:posizione + 4], "big")
        tipo = dati[posizione + 4:posizione + 8]
        if tipo == b"IDAT":
            idat += dati[posizione + 8:posizione + 8 + lunghezza]
        posizione += 12 + lunghezza

    grezzo = zlib.decompress(idat)
    lati = larghezza * 4
    righe = []
    for y in range(altezza):
        riga = grezzo[y * (lati + 1):(y + 1) * (lati + 1)]
        assert riga[0] == 0, "il PNG usa un filtro che questo test non prevede"
        righe.append([tuple(riga[1 + x * 4:1 + x * 4 + 4]) for x in range(larghezza)])
    return righe


def test_il_svg_versionato_e_quello_che_lo_script_genera():
    """Se il disegno cambia nello script, l'SVG versionato va rigenerato."""
    with open(SVG, encoding="utf-8") as file:
        versionato = file.read()

    assert versionato == generatore().svg(), (
        "l'SVG versionato non e' quello generato da scripts/genera_icona.py: "
        "rilancia `python3 scripts/genera_icona.py`"
    )


def test_il_png_versionato_e_quello_che_lo_script_genera(tmp_path):
    """Idem per il PNG: e' quello che la review di plugins.qgis.org mostra."""
    modulo = generatore()
    modulo.scrivi_png(modulo.disegna(), tmp_path / "icona.png")

    with open(PNG, "rb") as file:
        versionato = file.read()
    with open(tmp_path / "icona.png", "rb") as file:
        rigenerato = file.read()

    assert versionato == rigenerato, (
        "il PNG versionato non e' quello generato da scripts/genera_icona.py: "
        "rilancia `python3 scripts/genera_icona.py`"
    )


def test_l_icona_riempie_la_tela_invece_di_stare_in_un_angolo():
    """Il difetto: l'icona disegnata a scala sbagliata, minuscola in un angolo.

    Un PNG 64x64 con dentro un'icona da 24 pixel supera qualsiasi controllo di
    dimensione del file: si vede solo guardando quanta tela l'icona occupa.
    """
    righe = pixel_del_png(PNG)
    altezza = len(righe)
    larghezza = len(righe[0])

    opachi = [(x, y)
              for y, riga in enumerate(righe)
              for x, px in enumerate(riga)
              if px[3] > 0]
    assert opachi, "l'icona e' completamente trasparente"

    x_min = min(x for x, _ in opachi)
    x_max = max(x for x, _ in opachi)
    y_min = min(y for _, y in opachi)
    y_max = max(y for _, y in opachi)

    assert (x_max - x_min + 1) / larghezza >= 0.7, (
        f"l'icona occupa solo {x_max - x_min + 1}px in larghezza su {larghezza}"
    )
    assert (y_max - y_min + 1) / altezza >= 0.7, (
        f"l'icona occupa solo {y_max - y_min + 1}px in altezza su {altezza}"
    )
