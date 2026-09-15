#!/usr/bin/env python3
"""Genera l'icona PNG del plugin GDB-Attacher senza dipendenze esterne.

Ricrea l'SVG `icona_plugin.svg` (documento + cerchio con spunta) a 64x64 usando
solo la libreria standard: si disegna a 4x (256x256) e si riduce con un box filter,
così i bordi risultano morbidi. Serve perché plugins.qgis.org vuole un PNG.

Uso: python3 scripts/genera_icona.py [uscita.png]
"""
import struct
import sys
import zlib
from pathlib import Path

SCALA = 4          # supersampling
LATO = 64          # lato finale in pixel
L = LATO * SCALA   # lato del buffer di lavoro

# Colori (RGBA)
TRATTO = (0x2B, 0x2B, 0x2B, 255)
VERDE = (0x8A, 0xA6, 0x2F, 255)
BIANCO = (0xFF, 0xFF, 0xFF, 255)
TRASPARENTE = (0, 0, 0, 0)


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


def metti(buf, x, y, colore):
    if 0 <= x < L and 0 <= y < L:
        buf[y][x] = _miscela(buf[y][x], colore)


def rettangolo(buf, x0, y0, x1, y1, colore):
    for y in range(int(y0), int(y1)):
        for x in range(int(x0), int(x1)):
            metti(buf, x, y, colore)


def contorno_rettangolo(buf, x0, y0, x1, y1, spessore, colore):
    rettangolo(buf, x0, y0, x1, y0 + spessore, colore)
    rettangolo(buf, x0, y1 - spessore, x1, y1, colore)
    rettangolo(buf, x0, y0, x0 + spessore, y1, colore)
    rettangolo(buf, x1 - spessore, y0, x1, y1, colore)


def disco(buf, cx, cy, raggio, colore):
    r2 = raggio * raggio
    for y in range(int(cy - raggio) - 1, int(cy + raggio) + 2):
        for x in range(int(cx - raggio) - 1, int(cx + raggio) + 2):
            if (x - cx) ** 2 + (y - cy) ** 2 <= r2:
                metti(buf, x, y, colore)


def segmento(buf, x0, y0, x1, y1, spessore, colore):
    """Segmento spesso, disegnato per interpolazione."""
    passi = int(max(abs(x1 - x0), abs(y1 - y0)) * 2) + 1
    meta = spessore / 2.0
    for i in range(passi + 1):
        t = i / passi
        cx = x0 + (x1 - x0) * t
        cy = y0 + (y1 - y0) * t
        for dy in range(int(-meta) - 1, int(meta) + 2):
            for dx in range(int(-meta) - 1, int(meta) + 2):
                if dx * dx + dy * dy <= meta * meta:
                    metti(buf, int(cx) + dx, int(cy) + dy, colore)


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
    destinazione = sys.argv[1] if len(sys.argv) > 1 else \
        "gdb_attacher/resources/icone/icona_plugin.png"
    s = SCALA  # scorciatoia: le coordinate sono quelle dell'SVG 24x24, scalate

    buf = nuovo_buffer()

    # Foglio (rettangolo 1.5,7.5 -> 14.5,20.5) con contorno
    contorno_rettangolo(buf, 1.5 * s, 7.5 * s, 14.5 * s, 20.5 * s, 1.6 * s, TRATTO)
    # Tre righe di testo
    for y, x1 in ((10.5, 11.5), (13.5, 11.5), (16.5, 8.5)):
        segmento(buf, 4.5 * s, y * s, x1 * s, y * s, 1.4 * s, TRATTO)
    # Cerchio verde con spunta
    disco(buf, 18 * s, 8 * s, 4.5 * s, VERDE)
    contorno_cerchio(buf, 18 * s, 8 * s, 4.5 * s, 1.4 * s, TRATTO)
    segmento(buf, 15.6 * s, 8.2 * s, 17.2 * s, 9.8 * s, 1.7 * s, BIANCO)
    segmento(buf, 17.2 * s, 9.8 * s, 20.2 * s, 6.6 * s, 1.7 * s, BIANCO)

    scrivi_png(riduci(buf), destinazione)
    print(f"icona scritta: {destinazione}")


def contorno_cerchio(buf, cx, cy, raggio, spessore, colore):
    """Anello del cerchio (per il bordo scuro)."""
    esterno = raggio
    interno = raggio - spessore
    for y in range(int(cy - esterno) - 1, int(cy + esterno) + 2):
        for x in range(int(cx - esterno) - 1, int(cx + esterno) + 2):
            d2 = (x - cx) ** 2 + (y - cy) ** 2
            if interno ** 2 <= d2 <= esterno ** 2:
                metti(buf, x, y, colore)


if __name__ == "__main__":
    main()
