## Destination

Spec decisionale pronta per il plugin QGIS GDB-Attacher: wizard che seleziona un layer GDB, verifica/crea il layer `_ATTACH` senza corrompere il GDB, lo stilizza per anteprime HTML, auto-rileva campi foto/allegati, applica naming via nome originale/formula/CSV join, nel rispetto di TOS e licenze.

## Notes

- Dominio: QGIS PyQGIS, GDAL OpenFileGDB vs Esri FileGDB SDK, schema `_ATTACH` (GLOBALID, REL_GLOBALID, ATT_NAME, DATA, CONTENT_TYPE), QML/style HTML, CSV join.
- Skill da consultare ogni sessione: `research` per fatti esterni, `prototype` per artefatti UX, `grilling` + `domain-modeling` per decisioni; `CONTEXT.md` da creare al primo ticket grilling.
- Preferenze standing: progetto a tempo perso, plugin open per tutti, script esistenti in repo come primary source (`Aggiungi singola doto al GDB.py`, `Allega foto GDB.py`), non rompere mai il GDB, verifica TOS prima di qualsiasi pubblicazione.
- Tracker: local-markdown (`.scratch/gdb-attacher-plugin/`), in attesa di `/setup-matt-pocock-skills` per eventuale passaggio a GitHub Issues.

## Decisions so far

- [Creare _ATTACH senza rompere il GDB](issues/02-creare-attach-senza-rompere-gdb.md): mai creare `__ATTACH` a mano; se manca/incompleta bloccare e rimandare a Pro, scrivere con i 6 campi normalizzati.
- [TOS e licenze FileGDB per il plugin](issues/01-tos-licenze-filegdb-plugin.md): nessuna violazione con solo GDAL OpenFileGDB, licenza GPLv2+, dipendenze dichiarate, niente binari.
- [Wizard selezione layer e UX](issues/03-wizard-selezione-layer-ux.md): solo layer in progetto su FileGDB; verifica bloccante → discovery → campi → naming → esegui → stile; blocco duro sui casi anomali; preview a conteggi + esempi naming su 5 feature; backup aggirabile, transazione unica, report con export missing; QML auto-applicato; IT+EN; glossario in `CONTEXT.md`.
- [Stile `_ATTACH` e anteprime altri formati](issues/04-stile-html-anteprime-altri-formati.md): variante A (anteprima in testa, HTML inline + mapTip); nel form non vale `[% %]` → bridge JS `expression.evaluate`; ExternalResource non applicabile al blob; PDF/TIFF/MP4 solo via azione *Apri*; nomi con apice → ticket 06.
- [Auto-discovery campi foto](issues/05-auto-discovery-campi-foto.md): euristica a 4 segnali sui valori (ext%, esiste%, multi%, scarto guid/num/remoto) + nome campo; 4 livelli A/B/C/D; misurato 7/7 attesi e 0 falsi positivi con cartella base (6/7 senza); dettagli e tabella in `prototype/05-field-discovery/`.

## Not yet specified

- Performance e batch: migliaia di foto, transazioni `edit()`, rollback, deduplica su `(REL_GLOBALID, ATT_NAME)`, resume dopo crash.
- Discovery: dove si sceglie la cartella base nell'ordine del wizard e cosa mostrare quando non c'è ancora (emerso dal ticket 05: senza cartella base il livello A non esiste e i nomi senza estensione restano C).
- Stile: QML di default versionato/incluso nel plugin (packaging, vedi ticket 07).
- Formula di naming: sintassi (espressioni QGIS?), univocità, sanitizzazione caratteri, cosa fare con collisioni.
- CSV join: chiave univoca (GLOBALID?), separatore/encoding, validazione path, preview prima dell'attach.
- Altre idee da valutare: galleria multi-foto, supporto QField, test su GDB campioni, i18n IT/EN, pubblicazione su repo ufficiale QGIS, licenza plugin (GPL2).
- Strategia test senza GDB reale: GDB sintetico minimo, fixture, CI.

## Out of scope

- Enterprise geodatabase versioned / ArcSDE e parity ArcGIS Pro: questo effort mira a FileGDB letto/scritto da QGIS/GDAL.
