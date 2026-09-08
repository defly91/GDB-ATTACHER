# Prior art: QGDB (DGZ-Engineering-Lab/qgdb) — nota 2026-09-08

Fonte: https://github.com/DGZ-Engineering-Lab/qgdb (GPLv3, QGIS 3.22–3.44, ESRI GDB ↔ formato aperto `.qgdb`)

## Verdetto in breve

Nessun supporto agli attachment ESRI in QGDB (zero occorrenze di `attach` in codice e docs):
la via "scrivi su `__ATTACH` via PyQGIS" dei nostri script resta prior art originale.
Ma QGDB offre **pattern di codice riutilizzabili** per 4 ticket della mappa.

## Pattern utili per ticket

- **02/03/05 — ispezione GDB via `GDB_Items`** (`converters/gdb_analyzer.py`): apre il `.gdb`
  con `ogr.Open()` ed esegue `SELECT Name, Type, Path, Definition FROM GDB_Items`,
  parsando il `Definition` XML per dataset, domini e relationship class. Stessa tecnica
  per rilevare `<layer>__ATTACH` + `__ATTACHREL` senza toccare il GDB (read-only,
  nessun rischio corruzione) — base per "verifica _ATTACH" del wizard e per
  validare "manca/incompleta → rimanda a Pro".
- **04 — setup form/widget da codice** (`plugin/form_injector.py`): configura
  `QgsEditorWidgetSetup`, vincoli e relazioni 1:N sulle feature form via PyQGIS.
  Stesso punto di innesto per widget anteprima HTML foto su layer `_ATTACH`.
- **05 — enumerazione relazioni/domini** (`core/schema_builder.py`, `core/qgdb_engine.py`):
  esempio di scansione sistematica di campi/relazioni — spunto per euristica
  `suggerisci_campi()` (nomi, tipi, match-rate).
- **07 — packaging plugin** (`plugin/metadata.txt`): template completo di metadati
  (versione QGIS minima, categoria, tracker,_about con dipendenze dichiarate) —
  riferimento per pubblicazione su repo ufficiale QGIS.

## Avvertenza licenza

QGDB è **GPLv3**: non copiare codice verbatim nel nostro plugin (che punta a GPLv2+
per il repo QGIS) — reimplementare i pattern osservando il comportamento.
