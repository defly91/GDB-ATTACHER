# -*- coding: utf-8 -*-
"""core/styles.py — stile della tabella allegati.

Decisione del ticket 04 (reazione umana del 2026-09-15): si applica la **variante A
— anteprima in testa** (2 tab: *Anteprima* con dossier HTML inline + *Dati tecnici*;
mapTip con miniatura; azioni *Apri allegato* e *Salva allegato con nome…*; blob
visibile ma in sola lettura).

Verdetti tecnici già chiusi dal prototipo e recepiti nel QML incluso:

- nel riquadro HTML del form **non vale** ``[% %]``: i valori si leggono da JS con
  ``expression.evaluate('"CAMPO"')``;
- ``to_base64("DATA")`` fa round-trip fedele ai byte;
- il widget *External Resource* **non** è applicabile al blob (``ATT_NAME`` è un nome
  dentro il GDB, non un percorso) → l'apertura dei formati non anteprimabili
  (PDF/TIFF/MP4) passa dall'azione *Apri allegato*, che esporta in temp;
- i nomi con apice non rompono le azioni perché il nome passa da
  ``to_base64("ATT_NAME")`` + ``base64.b64decode`` (ticket 06).

Lo stile viene applicato **alla fine** della procedura (ticket 03) e **sovrascrive**
lo stile esistente; il wizard lascia la possibilità di non applicarlo.

``resources/stile_attach_variante_A.qml`` è il QML del prototipo scelto **con una sola
differenza**: le due azioni leggono il **nome allegato** da
``[% to_base64("ATT_NAME") %]`` + ``base64.b64decode(...)`` invece che da un literal
Python, come deciso dal ticket 06 dopo la verifica 8/8 in QGIS 3.44.4 (nomi con apice,
accenti e a capo). Tutto il resto del QML — alias, ValueMap su ``CONTENT_TYPE``,
widget Binary, tab *Anteprima*/*Dati tecnici*, mapTip, colonna ``DATA`` nascosta — è
identico al prototipo validato a headless.
"""

from __future__ import annotations

import os

#: Nome del QML incluso nel plugin (variante A, quella scelta).
QML_PREDEFINITO = "stile_attach_variante_A.qml"


def percorso_qml_default() -> str:
    """Percorso assoluto del QML di default dentro il pacchetto del plugin."""
    return os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        "resources", QML_PREDEFINITO)


def esiste_qml(percorso: str = None) -> bool:
    """Vero se il QML di default esiste davvero (il packaging lo deve includere)."""
    return os.path.isfile(percorso or percorso_qml_default())


def applica_stile(layer, percorso_qml: str = None) -> tuple:
    """Applica il QML alla tabella allegati.

    :return: ``(ok, messaggio)`` — ``ok`` è il valore che QGIS stesso ritorna da
        ``loadNamedStyle``; il messaggio è quello di QGIS (già in lingua) o l'errore.
    """
    percorso = percorso_qml or percorso_qml_default()
    if not os.path.isfile(percorso):
        return False, f"QML non trovato: {percorso}"
    try:
        messaggio, ok = layer.loadNamedStyle(percorso)
        return bool(ok), str(messaggio or "")
    except Exception as errore:
        return False, str(errore)


def applica_stile_predefinito(layer) -> tuple:
    """Scorciatoia: variante A inclusa nel plugin."""
    return applica_stile(layer, percorso_qml_default())
