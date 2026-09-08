## Destination

Spec decisionale pronta per il plugin QGIS GDB-Attacher: wizard che seleziona un layer GDB, verifica/crea il layer `_ATTACH` senza corrompere il GDB, lo stilizza per anteprime HTML, auto-rileva campi foto/allegati, applica naming via nome originale/formula/CSV join, nel rispetto di TOS e licenze.

## Notes

- Dominio: QGIS PyQGIS, GDAL OpenFileGDB vs Esri FileGDB SDK, schema `_ATTACH` (GLOBALID, REL_GLOBALID, ATT_NAME, DATA, CONTENT_TYPE), QML/style HTML, CSV join.
- Skill da consultare ogni sessione: `research` per fatti esterni, `prototype` per artefatti UX, `grilling` + `domain-modeling` per decisioni; `CONTEXT.md` da creare al primo ticket grilling.
- Preferenze standing: progetto a tempo perso, plugin open per tutti, script esistenti in repo come primary source (`Aggiungi singola doto al GDB.py`, `Allega foto GDB.py`), non rompere mai il GDB, verifica TOS prima di qualsiasi pubblicazione.
- Tracker: local-markdown (`.scratch/gdb-attacher-plugin/`), in attesa di `/setup-matt-pocock-skills` per eventuale passaggio a GitHub Issues.

## Decisions so far

- [Creare _ATTACH senza rompere il GDB](issues/02-creare-attach-senza-rompere-gdb.md): mai creare `__ATTACH` a mano; se manca/incompleta bloccare e rimandare a Pro, scrivere con i 6 campi normalizzati.

## Not yet specified

- Performance e batch: migliaia di foto, transazioni `edit()`, rollback, deduplica su `(REL_GLOBALID, ATT_NAME)`, resume dopo crash.
- Dettagli stile: widget HTML vs form custom, comportamento per PDF/TIFF/MP4, QML di default versionato, anteprima su canvas vs form feature.
- Formula di naming: sintassi (espressioni QGIS?), univocità, sanitizzazione caratteri, cosa fare con collisioni.
- CSV join: chiave univoca (GLOBALID?), separatore/encoding, validazione path, preview prima dell'attach.
- Altre idee da valutare: galleria multi-foto, supporto QField, test su GDB campioni, i18n IT/EN, pubblicazione su repo ufficiale QGIS, licenza plugin (GPL2).
- Strategia test senza GDB reale: GDB sintetico minimo, fixture, CI.

## Out of scope

- Enterprise geodatabase versioned / ArcSDE e parity ArcGIS Pro: questo effort mira a FileGDB letto/scritto da QGIS/GDAL.
