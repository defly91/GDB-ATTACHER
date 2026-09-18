#!/usr/bin/env python3
"""Genera l'icona del plugin GDB-Attacher: SVG + PNG, senza dipendenze esterne.

Concetto: una foto (cielo, sole, montagne) con una graffetta verde in alto a
destra — «allega questa foto a questa feature».

La geometria sta in un posto solo (`_foto`, `_graffetta`) e viene resa due volte:

* **SVG** — `resources/icone/icona_plugin.svg`, quello che QGIS carica nella
  toolbar (vettoriale, nitido a ogni dimensione e su ogni tema);
* **PNG 64x64** — `resources/icone/icona_plugin.png`, quello che pretende
  plugins.qgis.org e che il gestore dei plugin mostra nell'elenco.

Così le due versioni non possono divergere: chi cambia un colore o una curva lo
cambia per entrambe. Il disegno usa **solo riempimenti** (niente `clip-path`,
niente stroke sulla cornice): Qt sa renderizzarli sempre uguali, e i bordi
arrotondati restano tali anche dove il supporto SVG è parziale.

La graffetta è disegnata due volte, prima con un alone bianco più spesso: sul
tema chiaro di QGIS un tratto verde su foto azzurra si distingue, sul tema scuro
serve il distacco netto che dà l'alone.

Uso: python3 scripts/genera_icona.py [cartella di uscita]
     (default: gdb_attacher/resources/icone)
"""

from __future__ import annotations

import math
import struct
import sys
import zlib
from pathlib import Path

UNITA = 24.0       # lato della griglia di disegno (il viewBox dell'SVG)
LATO = 64          # lato finale del PNG in pixel
SCALA = 4          # supersampling: si disegna a 4x e si riduce con un box filter
L = LATO * SCALA   # lato del buffer di lavoro
S = L / UNITA      # pixel di lavoro per unita' di disegno

# Colori
BORDO = (0x1F, 0x4F, 0x7A, 255)     # blu scuro: cornice della foto
CIELO = (0x4A, 0x90, 0xD9, 255)     # azzurro: il cielo della foto
BIANCO = (0xFF, 0xFF, 0xFF, 255)    # sole, montagne e alone della graffetta
VERDE = (0x8A, 0xA6, 0x2F, 255)     # verde QGIS: il filo della graffetta
TRASPARENTE = (0, 0, 0, 0)

# Geometria della foto, in unita' di disegno (x0, y0, x1, y1, raggio)
FOTO = (1.8, 4.6, 18.2, 21.0, 2.0)
FOTO_INTERNA = (2.7, 5.5, 17.3, 20.1, 1.1)   # cornice di 0.9 di spessore
SOLE = (6.9, 10.1, 1.6)

# Geometria della graffetta: filo di una Gem clip in coordinate locali (centro
# nell'origine, alto ~7 unita'), poi ruotata e spostata sull'angolo della foto.
GRAFFETTA_CENTRO = (18.7, 6.3)
GRAFFETTA_ROT = -25.0        # gradi, orario (y cresce verso il basso)
GRAFFETTA_SCALA = 1.12       # la graffetta e' un po' piu' grande del disegno base:
                             # a 24 px in toolbar il filo sottile sparirebbe
GRAFFETTA_ALONE = 2.0        # spessore del tratto bianco sotto quello verde
GRAFFETTA_FILO = 1.5         # spessore del tratto verde


# --------------------------------------------------------------------- geometria

def _arco(cx, cy, raggio, da_gradi, a_gradi, passi=12):
    """Punti di un arco. Angoli in gradi, con y che cresce verso il basso.

    Quindi 0 = destra, 90 = sotto, 180 = sinistra, 270 = sopra.
    """
    punti = []
    for i in range(passi + 1):
        t = math.radians(da_gradi + (a_gradi - da_gradi) * i / passi)
        punti.append((cx + raggio * math.cos(t), cy + raggio * math.sin(t)))
    return punti


def _montagne():
    """La catena bianca in fondo alla foto.

    Il bordo inferiore segue gli angoli arrotondati della cornice interna invece
    di essere ritagliato: così la sagoma resta dentro la foto senza `clip-path`.
    """
    x0, y0, x1, y1, r = FOTO_INTERNA
    punti = [
        (x0, y1 - r - 0.1),        # sinistra, sopra l'angolo
        (6.6, 13.6),               # prima vetta
        (9.4, 16.9),               # valle
        (12.9, 12.9),              # vetta piu' alta
        (x1, 18.4),                # il crinale scende sul bordo destro
        (x1, y1 - r),              # fino all'inizio dell'angolo
    ]
    punti += _arco(x1 - r, y1 - r, r, 0, 90, 6)[1:]     # angolo basso a destra
    punti += [(x0 + r, y1)]                             # bordo inferiore
    punti += _arco(x0 + r, y1 - r, r, 90, 180, 6)[1:]   # angolo basso a sinistra
    return punti


def _graffetta():
    """Il filo della graffetta, gia' ruotato e posizionato sulla foto."""
    punti = [(-2.0, -3.4), (-2.0, 2.6)]
    punti += _arco(0.0, 2.6, 2.0, 180, 0, 10)[1:]      # curva in basso
    punti += [(2.0, -2.2)]
    punti += _arco(1.0, -2.2, 1.0, 0, -180, 10)[1:]    # curva in alto
    punti += [(0.0, 1.0)]

    coseno = math.cos(math.radians(GRAFFETTA_ROT))
    seno = math.sin(math.radians(GRAFFETTA_ROT))
    cx, cy = GRAFFETTA_CENTRO
    return [
        (cx + (x * coseno - y * seno) * GRAFFETTA_SCALA,
         cy + (x * seno + y * coseno) * GRAFFETTA_SCALA)
        for x, y in punti
    ]


# ------------------------------------------------------------------------- SVG

def _punti(punti):
    """Punti come comandi di un path SVG: `M x y L x y ...`."""
    prima, *resto = [f"{x:.2f} {y:.2f}" for x, y in punti]
    return "M " + prima + "".join(f" L {p}" for p in resto)


def _hex(colore):
    return "#%02x%02x%02x" % colore[:3]


def svg():
    """Il contenuto dell'SVG, generato dalla stessa geometria del PNG."""
    catena = _punti(_montagne()) + " Z"
    filo = _punti(_graffetta())
    x0, y0, x1, y1, r = FOTO
    xi, yi, x1i, y1i, ri = FOTO_INTERNA

    return f"""<?xml version="1.0" encoding="UTF-8"?>
<!-- Icona del plugin GDB-Attacher (GPL-2.0-or-later).
     AUTO-GENERATA da scripts/genera_icona.py: non modificarla a mano, la
     prossima rigenerazione la sovrascrive. Per cambiare qualcosa si tocca la
     geometria nello script, cosi' SVG e PNG restano identici.

     Concetto: foto + graffetta = «allega questa foto a questa feature».
     Solo riempimenti, nessun clip-path: Qt li rende uguali su ogni versione.
     La graffetta e' disegnata due volte, prima con un alone bianco piu'
     spesso, per restare leggibile sia sul tema chiaro sia sul tema scuro. -->
<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24">
  <title>GDB-Attacher</title>

  <!-- la foto: cornice, cielo, sole -->
  <rect x="{x0}" y="{y0}" width="{x1 - x0:.1f}" height="{y1 - y0:.1f}" rx="{r}" fill="{_hex(BORDO)}"/>
  <rect x="{xi}" y="{yi}" width="{x1i - xi:.1f}" height="{y1i - yi:.1f}" rx="{ri}" fill="{_hex(CIELO)}"/>
  <circle cx="{SOLE[0]}" cy="{SOLE[1]}" r="{SOLE[2]}" fill="{_hex(BIANCO)}"/>

  <!-- le montagne -->
  <path d="{catena}" fill="{_hex(BIANCO)}"/>

  <!-- la graffetta: prima l'alone bianco, poi il filo verde -->
  <path d="{filo}" fill="none" stroke="{_hex(BIANCO)}" stroke-width="{GRAFFETTA_ALONE}" stroke-linecap="round" stroke-linejoin="round"/>
  <path d="{filo}" fill="none" stroke="{_hex(VERDE)}" stroke-width="{GRAFFETTA_FILO}" stroke-linecap="round" stroke-linejoin="round"/>
</svg>
"""


# --------------------------------------------------------------------- raster

def nuovo_buffer():
    return [[TRASPARENTE for _ in range(L)] for _ in range(L)]


def _miscela(dst, src):
    """Alpha blending di src sopra dst."""
    if src[3] == 255:
        return src
    if src[3] == 0:
        return dst
    a = src[3] / 255.0
    return (
        int(src[0] * a + dst[0] * (1 - a)),
        int(src[1] * a + dst[1] * (1 - a)),
        int(src[2] * a + dst[2] * (1 - a)),
        max(dst[3], src[3]),
    )


def _area(buf, x0, y0, x1, y1):
    """Il rettangolo di pixel di lavoro da visitare per una forma, ritagliato."""
    return (
        max(0, int(math.floor(x0 * S))),
        max(0, int(math.floor(y0 * S))),
        min(L, int(math.ceil(x1 * S)) + 1),
        min(L, int(math.ceil(y1 * S)) + 1),
    )


def riempi(buf, dentro, colore, bbox):
    """Colora i pixel il cui centro cade dentro la forma `dentro(x, y)`.

    Le coordinate passate a `dentro` sono in unita' di disegno, non in pixel:
    il campionamento avviene a 4x e poi `riduci` media, quindi ogni pixel finale
    dell'icona e' la media di 16 campioni (bordi morbidi senza antialiasing a
    mano).
    """
    x0, y0, x1, y1 = _area(buf, *bbox)
    for j in range(y0, y1):
        y = (j + 0.5) / S
        riga = buf[j]
        for i in range(x0, x1):
            if dentro((i + 0.5) / S, y):
                riga[i] = _miscela(riga[i], colore)


def riempi_rettangolo_arrotondato(buf, x0, y0, x1, y1, raggio, colore):
    def dentro(x, y):
        if not (x0 <= x <= x1 and y0 <= y <= y1):
            return False
        cx = min(max(x, x0 + raggio), x1 - raggio)
        cy = min(max(y, y0 + raggio), y1 - raggio)
        return (x - cx) ** 2 + (y - cy) ** 2 <= raggio * raggio

    riempi(buf, dentro, colore, (x0, y0, x1, y1))


def riempi_cerchio(buf, cx, cy, raggio, colore):
    def dentro(x, y):
        return (x - cx) ** 2 + (y - cy) ** 2 <= raggio * raggio

    riempi(buf, dentro, colore, (cx - raggio, cy - raggio, cx + raggio, cy + raggio))


def riempi_poligono(buf, punti, colore):
    """Riempimento even-odd di un poligono (ray casting orizzontale)."""

    def dentro(x, y):
        esito = False
        for i, (ax, ay) in enumerate(punti):
            bx, by = punti[i - 1]
            if (ay > y) != (by > y):
                intersezione = (bx - ax) * (y - ay) / (by - ay) + ax
                if x < intersezione:
                    esito = not esito
        return esito

    xs = [p[0] for p in punti]
    ys = [p[1] for p in punti]
    riempi(buf, dentro, colore, (min(xs), min(ys), max(xs), max(ys)))


def tratto(buf, punti, spessore, colore):
    """Polilinea con estremi e giunzioni tondi: una capsula per segmento."""
    meta = spessore / 2.0

    for (ax, ay), (bx, by) in zip(punti, punti[1:]):
        dx, dy = bx - ax, by - ay
        lungo2 = dx * dx + dy * dy

        def dentro(x, y, ax=ax, ay=ay, dx=dx, dy=dy, lungo2=lungo2):
            if lungo2 == 0:
                return (x - ax) ** 2 + (y - ay) ** 2 <= meta * meta
            t = max(0.0, min(1.0, ((x - ax) * dx + (y - ay) * dy) / lungo2))
            return (x - ax - t * dx) ** 2 + (y - ay - t * dy) ** 2 <= meta * meta

        riempi(buf, dentro, colore,
               (min(ax, bx) - meta, min(ay, by) - meta,
                max(ax, bx) + meta, max(ay, by) + meta))


def disegna():
    """L'icona, nell'ordine in cui va sovrapposta."""
    buf = nuovo_buffer()

    # La foto: cornice scura, poi cielo, sole e montagne.
    riempi_rettangolo_arrotondato(buf, *FOTO, BORDO)
    riempi_rettangolo_arrotondato(buf, *FOTO_INTERNA, CIELO)
    riempi_cerchio(buf, *SOLE, BIANCO)
    riempi_poligono(buf, _montagne(), BIANCO)

    # La graffetta: alone bianco sotto, filo verde sopra.
    filo = _graffetta()
    tratto(buf, filo, GRAFFETTA_ALONE, BIANCO)
    tratto(buf, filo, GRAFFETTA_FILO, VERDE)

    return riduci(buf)


def riduci(buf):
    """Box filter SCALA x SCALA -> immagine finale."""
    out = []
    area = SCALA * SCALA
    for y in range(LATO):
        riga = []
        for x in range(LATO):
            r = g = b = a = 0
            for dy in range(SCALA):
                for dx in range(SCALA):
                    px = buf[y * SCALA + dy][x * SCALA + dx]
                    r += px[0] * px[3]
                    g += px[1] * px[3]
                    b += px[2] * px[3]
                    a += px[3]
            if a == 0:
                riga.append((0, 0, 0, 0))
            else:
                riga.append((r // a, g // a, b // a, a // area))
        out.append(riga)
    return out


def scrivi_png(immagine, percorso):
    """PNG RGBA minimale (stdlib)."""
    altezza = len(immagine)
    larghezza = len(immagine[0])
    grezzo = bytearray()
    for riga in immagine:
        grezzo.append(0)  # filtro "none"
        for px in riga:
            grezzo.extend(px)

    def chunk(tipo, dati):
        return (struct.pack(">I", len(dati)) + tipo + dati
                + struct.pack(">I", zlib.crc32(tipo + dati) & 0xFFFFFFFF))

    intestazione = struct.pack(">IIBBBBB", larghezza, altezza, 8, 6, 0, 0, 0)
    png = (b"\x89PNG\r\n\x1a\n"
           + chunk(b"IHDR", intestazione)
           + chunk(b"IDAT", zlib.compress(bytes(grezzo), 9))
           + chunk(b"IEND", b""))
    Path(percorso).write_bytes(png)


def main():
    cartella = Path(sys.argv[1]) if len(sys.argv) > 1 else \
        Path(__file__).resolve().parent.parent / "gdb_attacher" / "resources" / "icone"
    cartella.mkdir(parents=True, exist_ok=True)

    (cartella / "icona_plugin.svg").write_text(svg(), encoding="utf-8", newline="\n")
    scrivi_png(disegna(), cartella / "icona_plugin.png")
    print(f"icona scritta in {cartella}: icona_plugin.svg + icona_plugin.png "
          f"({LATO}x{LATO})")


if __name__ == "__main__":
    main()
