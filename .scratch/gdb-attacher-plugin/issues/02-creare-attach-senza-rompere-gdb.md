Map: [map](../map.md)
Type: research (AFK)
Status: resolved
Blocked by: none
Labels: wayfinder:research

## Answer

Decisione: il plugin **non crea mai** la tabella `<layer>__ATTACH` a mano. Schema di scrittura: 6 campi (`GLOBALID` uuid4 upper senza graffe, `REL_GLOBALID` parent-GUID upper con graffe `{...}`, `CONTENT_TYPE` mime reale, `ATT_NAME`, `DATA_SIZE`, `DATA` blob), dedup su `(REL_GLOBALID, ATT_NAME)` normalizzati, rifiuto parent-GUID nullo (fa fede lo script click, non il batch). Se `__ATTACH` manca o è incompleta → bloccare e rimandare ad ArcGIS Pro (`EnableAttachments`), perché GDAL non conosce gli attachment e la tabella manuale risulta fantasma (mancano `__ATTACHREL` + metadati). Dettagli e fonti in `research-attach-schema.md`.

## Question

Qual è lo schema canonico del layer `<layer>__ATTACH` in un FileGDB e come crearlo da QGIS/PyQGIS/GDAL senza corrompere il GDB?

Indagare sui due script esistenti come primary source: campi usati (REL_GLOBALID, ATT_NAME, DATA, CONTENT_TYPE, GLOBALID generato via uuid), ruolo di GLOBALID/REL_GLOBALID con braces `{...}`, mime-type, deduplica. Poi: esiste una API ufficiale (ArcPy `EnableAttachments`, GDAL, `QgsVectorLayer`) per creare la tabella ATTACH mancante? Cosa succede se la creiamo a mano (indici, GUID, metadata GDB_SYSTEM)? Output: definizione schema minimo sicuro + procedura crea-se-manca + cosa NON fare.

## Findings (2026-09-08, branch `research/attach-schema`, NON mergiato)

Context pointer: full research in [`../research-attach-schema.md`](../research-attach-schema.md)
(sintesi + fonti con URL: GDAL OpenFileGDB/FileGDB, ArcPy Enable/Add Attachments).

- Schema minimo (6 campi, comune ai due script): `GLOBALID` = uuid4 upper senza
  graffe; `REL_GLOBALID` = parent-GUID upper **con** graffe `{...}`;
  `CONTENT_TYPE` = mime reale; `ATT_NAME` = nome file; `DATA_SIZE` = len(blob);
  `DATA` = blob (`QByteArray`). Plus `__ATTACHREL` creata da ArcGIS.
- Divergenze script batch (`Allega foto GDB.py`): `REL_GLOBALID` raw senza
  braces, `CONTENT_TYPE` hardcoded `image/jpeg`, dedup non normalizzata —
  usare la versione normalizzata di `Aggiungi singola doto al GDB.py`.
- Creazione: unica via ufficiale = `arcpy.management.EnableAttachments`
  (tabella + relationship class + metadati, idempotente). GDAL non conosce gli
  attachment; crearla a mano = tabella fantasma per ArcGIS. Plugin: se
  `__ATTACH` manca o è incompleta → bloccare e rimandare a Pro, mai creare.
- Status: open → pronto per decisione architetturale (dettagli nel research file).
