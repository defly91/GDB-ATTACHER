#!/usr/bin/env python3
"""Verifica del plugin GDB-Attacher dentro un QGIS vero (container, headless).

Esegue ciò che i test con i finti non possono coprire: importazione dei moduli
contro le API reali, caricamento del QML di stile, valutazione di una formula con
QgsExpression vero e apertura del wizard con un'istanza QgsApplication offscreen.

Ogni controllo è isolato: se uno fallisce gli altri continuano, e in fondo si
stampa un riepilogo PASS/FAIL.
"""
import os
import sys
import traceback
from unittest.mock import MagicMock

REPO = os.environ.get("REPO", "/repo")
esiti = []


def controllo(nome):
    def deco(fn):
        try:
            esito = fn()
            esiti.append((nome, True, esito or "ok"))
        except Exception as e:  # noqa: BLE001 — vogliamo vedere tutto
            esiti.append((nome, False, f"{type(e).__name__}: {e}"))
            traceback.print_exc()
        return fn
    return deco


@controllo("import qgis.core e versione")
def _1():
    from qgis.core import Qgis
    return f"QGIS {Qgis.QGIS_VERSION} (codename {Qgis.QGIS_RELEASE_NAME})"


@controllo("import del pacchetto plugin e dei suoi moduli")
def _2():
    sys.path.insert(0, REPO)
    import importlib
    moduli = [
        "gdb_attacher",
        "gdb_attacher.core.attach",
        "gdb_attacher.core.discovery",
        "gdb_attacher.core.naming",
        "gdb_attacher.core.report",
        "gdb_attacher.core.styles",
        "gdb_attacher.wizard.dialog",
        "gdb_attacher.wizard.strings",
        "gdb_attacher.plugin",
    ]
    for m in moduli:
        importlib.import_module(m)
    return f"{len(moduli)} moduli importati senza errori"


@controllo("formula di naming valutata con QgsExpression vero")
def _3():
    from gdb_attacher.core import naming
    errore, avviso = naming.verifica_formula('@stem || "CODICE"', None)
    if errore:
        raise AssertionError(f"formula rifiutata da QGIS reale: {errore}")
    if "non disponibile" in avviso:
        raise AssertionError("QgsExpression non disponibile: controllo non significativo")
    return f"errore='' avviso='{avviso}'"


@controllo("QML di stile caricato da QGIS")
def _4():
    from qgis.core import QgsVectorLayer
    qml = os.path.join(REPO, "gdb_attacher", "resources", "stile_attach_variante_A.qml")
    if not os.path.isfile(qml):
        raise FileNotFoundError(qml)
    # Il QML è quello della tabella allegati, che non ha geometria: va provato su un
    # layer senza geometria, altrimenti QGIS lo rifiuta per geometria incompatibile.
    layer = QgsVectorLayer(
        "None?field=ATT_NAME:string&field=REL_GLOBALID:string&field=REL_OBJECTID:integer",
        "prova", "memory",
    )
    if not layer.isValid():
        raise AssertionError("layer tabella di prova non valido")
    messaggio, ok = layer.loadNamedStyle(qml)
    if not ok:
        raise AssertionError(f"QGIS ha rifiutato il QML: {messaggio}")
    return f"stile applicato su tabella senza geometria ({messaggio or 'nessun messaggio'})"


@controllo("metadati del plugin letti dalle API QGIS")
def _5():
    from qgis.core import QgsApplication
    app = QgsApplication.instance() or QgsApplication([], False)
    QgsApplication.setPrefixPath("/usr", True)
    app.initQgis() if not QgsApplication.instance() else None
    from qgis.utils import plugin_paths  # noqa: F401 — verifica che qgis.utils sia disponibile
    return "QgsApplication e qgis.utils disponibili"


@controllo("wizard istanziato con QgsApplication offscreen")
def _6():
    from PyQt5.QtWidgets import QApplication
    from gdb_attacher.wizard.dialog import WizardAllegati
    app = QApplication.instance() or QApplication(sys.argv)
    iface = MagicMock()
    dlg = WizardAllegati(iface, None)
    pagine = dlg.pageIds()
    motivi = []
    for indice, pid in enumerate(pagine, start=1):
        pagina = dlg.page(pid)
        try:
            # Qt chiama `isComplete()` a ogni cambio di stato del wizard e `title()` per
            # l'intestazione: sono le due API che una pagina sbagliata fa saltare per prime.
            pagina.title()
            pagina.isComplete()
        except Exception as errore:  # noqa: BLE001
            motivi.append(f"pagina {indice}: {type(errore).__name__}: {errore}")
    titolo = dlg.windowTitle() if hasattr(dlg, "windowTitle") else ""
    dlg.close()
    if motivi:
        raise AssertionError("; ".join(motivi))
    return f"finestra creata, titolo='{titolo}', pagine={len(pagine)} tutte inizializzabili"


print("=" * 68)
for nome, ok, dettaglio in esiti:
    print(f"[{'PASS' if ok else 'FAIL'}] {nome}: {dettaglio}")
print("=" * 68)
falliti = [n for n, ok, _ in esiti if not ok]
print(f"RIEPILOGO: {len(esiti) - len(falliti)}/{len(esiti)} controlli superati")
if falliti:
    print("FALLITI: " + ", ".join(falliti))
sys.exit(1 if falliti else 0)
