# Research: schema canonico `<layer>__ATTACH` e creazione sicura (ticket 02)

Domanda: qual è lo schema canonico della tabella `<layer>__ATTACH` in un FileGDB,
e come crearla (o evitarne la creazione) da QGIS/PyQGIS/GDAL senza corrompere il GDB?

Metodo (skill `research`): primary source prima di tutto — i due script nel repo —
poi confronto con docs ufficiali GDAL (OpenFileGDB, FileGDB) e ArcPy (Enable/Add Attachments).

## 1. Primary source: cosa fanno i due script del repo

### 1a. `Aggiungi singola doto al GDB.py` (tool interattivo click-su-feature)
- Risolve i campi **case-insensitive** (`find_field_ci`) e pretende questi 6 campi
  sull'attach layer: `GLOBALID`, `REL_GLOBALID`, `CONTENT_TYPE`, `DATA_SIZE`,
  `ATT_NAME`, `DATA`. Se manca uno → errore bloccante, nessuna scrittura.
- Normalizza i GUID: `normalize_guid()` accetta `{GUID}` o `GUID`, ritorna
  `UPPERCASE` senza graffe; `with_braces()` rimette le graffe: `{GUID-UPPER}`.
- Scrive: `GLOBALID = str(uuid.uuid4()).upper()` (**senza** graffe),
  `REL_GLOBALID = {PARENT-GUID}` (**con** graffe, uppercase),
  `CONTENT_TYPE` da estensione (jpg/png/tif/pdf, fallback `application/octet-stream`),
  `DATA_SIZE = len(bytes)`, `ATT_NAME` = nome file, `DATA = QByteArray(bytes)`.
- Deduplica su coppia `(REL_GLOBALID_con_graffe, ATT_NAME)` con cache precaricata.
- Rifiuta feature con GlobalID parent nullo/vuoto; verifica `os.path.isfile`.

### 1b. `Allega foto GDB.py` (batch su 3 layer `Ril_ApFp_*`)
- Usa gli **stessi 6 campi** con nomi esatti maiuscoli, senza risoluzione CI.
- `GLOBALID = str(uuid.uuid4()).upper()` (senza graffe) — uguale a (1a).
- `REL_GLOBALID = feature['GLOBALID']` **raw, senza normalizzazione/braces**:
  funziona solo se il parent memorizza già il GUID con graffe. Divergenza da (1a).
- `CONTENT_TYPE` **hardcoded `image/jpeg`** anche per altri formati. Divergenza da (1a).
- Deduplica su `(rel_raw, nomefile)` senza normalizzazione → stesso file visto con
  casing/braces diversi non viene riconosciuto come duplicato. Divergenza da (1a).
- Salta record con GlobalID nullo o file mancante, con statistiche
  aggiunti/duplicati/saltati.

### 1c. Schema minimo osservato (comune ai due script, quindi canonico de facto)

| Campo | Tipo visto da QGIS/PyQGIS | Valore |
|---|---|---|
| `OBJECTID` | auto (gestito dal GDB, mai scritto dagli script) | — |
| `GLOBALID` | stringa GUID | `str(uuid.uuid4()).upper()`, **senza** graffe |
| `REL_GLOBALID` | stringa GUID | GUID del parent, `UPPERCASE` **con** graffe `{...}` |
| `CONTENT_TYPE` | stringa | mime-type reale (`image/jpeg`, `image/png`, `application/pdf`, …) |
| `ATT_NAME` | stringa | nome file originale |
| `DATA_SIZE` | intero | `len(bytes)` — deve coincidere col blob |
| `DATA` | binario (`QByteArray`) | contenuto del file |

A corredo esiste la relationship class `<layer>__ATTACHREL` (mai toccata dagli
script: la danno per esistente, creata da ArcGIS all'abilitazione).

## 2. Confronto con le fonti ufficiali

### GDAL OpenFileGDB — https://gdal.org/en/stable/drivers/vector/openfilegdb.html
- Read + **write/update dal GDAL ≥ 3.6**; supporta `Create()`, domini, transazioni
  e CRUD sulle **relationship** (dal 3.6). La parola "attach" **non compare mai**
  nella pagina: il driver non ha alcun concetto di attachment table.
- Transazioni **emulate** (backup/restore stile RFC 54): rollback ok in
  single-connection, **comportamento indefinito con scritture concorrenti**.
- Implicazione: scrivere righe in una `__ATTACH` *esistente* via QGIS
  (provider OGR → OpenFileGDB) è supportato dal driver; **creare** una `__ATTACH`
  via `CreateLayer` produrrebbe una tabella ordinaria **senza** registrazione
  nei metadati di sistema (`GDB_Items` / `GDB_ItemRelationships`), senza
  relationship class `__ATTACHREL` e senza plumbing GlobalID — invisibile ad
  ArcGIS Pro come attachment e potenzialmente confondente per i client Esri.

### GDAL FileGDB (SDK Esri) — https://gdal.org/en/stable/drivers/vector/filegdb.html
- Richiede l'SDK proprietario Esri; anch'esso **non menziona mai gli attachment**.
  Non è la strada per creare attachment da QGIS: dipendenza chiusa, nessun
  vantaggio documentato sul tema.

### ArcPy `EnableAttachments` — https://pro.arcgis.com/en/pro-app/latest/tool-reference/data-management/enable-attachments.htm
- È l'**unica API ufficiale di creazione**: "creates the necessary attachment
  **relationship class and attachment table** that will store attachment files
  internally" (`arcpy.management.EnableAttachments(in_dataset)`).
- Precondizioni: dataset in geodatabase **versione ≥ 10**; se già abilitato,
  warning e **nessuna operazione** (idempotente e sicura da richiamare).
- Sintesi: la creazione corretta = tabella + relationship class + registrazione
  metadati, tutto insieme, solo da stack Esri.

### ArcPy `AddAttachments` — https://pro.arcgis.com/en/pro-app/latest/tool-reference/data-management/add-attachments.htm
- Richiede attach **già abilitati**; **copia** i file dentro il GDB (gli originali
  restano intoccati); supporta **N file per record** via match table.
- Conferma il modello degli script: un record attach per file, link logico
  verso il parent — mai un blob dentro la feature class.

### Attachments toolset (overview) — https://pro.arcgis.com/en/pro-app/latest/tool-reference/data-management/an-overview-of-the-attachments-toolset.htm
- `DisableAttachments` **cancella sia la relationship class sia la tabella**:
  ulteriore prova che i due oggetti vivono o muoiono insieme. Crearne uno solo
  a mano è per definizione uno stato inconsistente.

### QGIS / PyQGIS (evidenza dagli script, nessun costrutto dedicato trovato)
- `QgsVectorLayer` + `edit()` + `addFeature()` scrive correttamente i 6 campi
  (incluso blob via `QByteArray`) su tabelle esistenti — i due script sono la
  prova operativa. Non esiste in QGIS un'API "EnableAttachments": la creazione
  va delegata allo stack Esri.

## 3. Output decisionale

### Schema minimo sicuro (scrittura righe in `__ATTACH` esistente)
Vedi tabella §1c. Regole: `GLOBALID` = uuid4 upper senza graffe e mai riusato;
`REL_GLOBALID` = parent upper **con** graffe; `DATA_SIZE` == `len(DATA)`;
`CONTENT_TYPE` = mime reale da estensione; dedup su `(REL_GLOBALID, ATT_NAME)`
normalizzati; mai scrivere con parent-GUID nullo.

### Procedura crea-se-manca (raccomandata per il plugin)
1. `attach = QgsProject.instance().mapLayersByName(layer.name() + "__ATTACH")`.
2. Se manca → **NON creare nulla**: bloccare con messaggio che rimanda ad
   ArcGIS Pro / `arcpy.management.EnableAttachments(<layer>)` (idempotente,
   warning se già abilitato), poi ricaricare il GDB in QGIS.
3. Se presente → validare i 6 campi (§1c, matching case-insensitive come in
   script 1a); se incompleta → stesso blocco, non "riparare" a mano.
4. Backup del `.gdb` prima di ogni batch; batch in transazione singola senza
   scrittori concorrenti (transazioni GDAL emulate, §2).

### Cosa NON fare (mai)
- Creare `<layer>__ATTACH` a mano via GDAL/QGIS (`CreateLayer` + campi
  copiati): mancano `__ATTACHREL`, metadati `GDB_Items/ItemRelationships`,
  plumbing GlobalID → tabella fantasma per ArcGIS, rischio corruzione logica.
- Scrivere `REL_GLOBALID` senza graffe / lowercase / non normalizzato
  (bug latente dello script batch §1b — usare `normalize_guid`+`with_braces`).
- Hardcodare `CONTENT_TYPE` (bug §1b) o scrivere `DATA_SIZE` incoerente col blob.
- Riusare `GLOBALID`, allegare a parent senza GlobalID, ignorare i duplicati.
- Abilitare/disabilitare attach fuori dallo stack Esri; aprire il GDB in
  scrittura da due processi contemporaneamente.

## Fonti (tutte verificate il 2026-09-08)
- Repo, primary source: `Aggiungi singola doto al GDB.py`, `Allega foto GDB.py`
  (root del repo `GDB-ATTACHER`, branch `main`).
- https://gdal.org/en/stable/drivers/vector/openfilegdb.html (write/update ≥ 3.6,
  relationship CRUD ≥ 3.6, transazioni emulate, zero riferimenti ad attachments).
- https://gdal.org/en/stable/drivers/vector/filegdb.html (richiede SDK Esri,
  zero riferimenti ad attachments).
- https://pro.arcgis.com/en/pro-app/latest/tool-reference/data-management/enable-attachments.htm
  (crea relationship class + attachment table; GDB ≥ 10; no-op se già abilitato).
- https://pro.arcgis.com/en/pro-app/latest/tool-reference/data-management/add-attachments.htm
  (richiede attach abilitati; copia file nel GDB; N file per record).
- https://pro.arcgis.com/en/pro-app/latest/tool-reference/data-management/an-overview-of-the-attachments-toolset.htm
  (Disable cancella relationship class + tabella insieme).
