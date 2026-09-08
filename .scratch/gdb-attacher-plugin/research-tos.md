# Research TOS / Licenze — plugin QGIS che scrive attachment in FileGDB

Data: 2026-09-08 · Branch throwaway: `research/tos-licenze` (da `main`, NON mergiare senza review)
Ticket: `.scratch/gdb-attacher-plugin/issues/01-tos-licenze-filegdb-plugin.md`

## Sintesi (risposta breve)

**No, non risultano violazioni**, a condizione di rispettare questi 4 vincoli:

1. **Usare solo il driver GDAL OpenFileGDB** (reverse-engineered, built-in, senza librerie Esri) — niente SDK/binari chiusi nel plugin.
2. **Licenza del plugin: GPLv2 o successiva** (richiesta dal repo ufficiale QGIS).
3. **Dichiarare eventuali dipendenze Python esterne** nel campo `About` dei metadati.
4. **Niente binari** nel pacchetto plugin; solo codice sorgente + repo pubblico.

Scrivere attachment = scrivere normali feature + BLOB + relationship
(`__ATTACH` table + `GDB_Items` relationship) tramite API pubbliche GDAL/QGIS:
nessun reverse engineering da parte nostra, nessun bypass di protezioni.

## Findings con fonti

### 1. GDAL OpenFileGDB: scrittura supportata, nessuna libreria Esri

- Il driver OpenFileGDB "provides read, write and update access to vector
  layers of File Geodatabases (.gdb directories) created by ArcGIS 10 and
  above". Write/update dal GDAL ≥ 3.6, raster dal 3.7, relationships dal 3.6.
- "Advantages of the OpenFileGDB driver, compared to the FileGDB driver: …
  Does not depend on a third-party library" — quindi nessun vincolo di
  licenza Esri se usiamo questo driver.
- Limiti noti: SDC/CDF compressi non leggibili; OBJECTID 64-bit sparsi
  read-only. Nulla di specifico contro gli attachment: gli attachment sono
  tabelle/feature ordinarie + BLOB, quindi coperte dalle capacità generiche
  di scrittura.
- Fonte: https://gdal.org/en/stable/drivers/vector/openfilegdb.html
- Il driver linka apertamente la "Reverse-engineered specification of the
  FileGDB format" (stessa pagina, sezione Links): pratica tollerata e
  documentata da anni, anche dentro QGIS stesso.

### 2. Esri FileGDB SDK: Apache 2.0, ma da EVITARE nel plugin

- Il repo ufficiale `Esri/file-geodatabase-api` è sotto Apache License 2.0
  ("Copyright 2017 Esri … Licensed under the Apache License, Version 2.0").
- Fonte: https://github.com/Esri/file-geodatabase-api (sezione Licensing +
  `License.txt`); testo: https://raw.githubusercontent.com/Esri/file-geodatabase-api/master/License.txt
- Perché evitarlo comunque: il driver GDAL FileGDB basato su SDK richiede la
  libreria proprietaria ("Build dependencies: FileGDB API library"), non è
  built-in di default e ha limiti (SRS particolari, compressione). Inoltre
  distribuire binari SDK nel plugin violerebbe la regola QGIS "no binaries"
  (vedi sotto) e complicherebbe la compatibilità GPLv2.
- Nota storica: le vecchie versioni dell'SDK (pre-2017) avevano una licenza
  d'uso restrittiva Esri; dal 2017 il codice è Apache 2.0. In ogni caso, non
  ci serve: OpenFileGDB basta.
- Fonte driver SDK: https://gdal.org/en/stable/drivers/vector/filegdb.html

### 3. Reverse engineering del formato GDB: nessun TOS violato dal plugin

- Il plugin non fa reverse engineering: usa API pubbliche (PyQGIS / GDAL
  OpenFileGDB). Il reverse engineering è già stato fatto da terzi (driver
  OpenFileGDB, dentro ogni installazione QGIS/GDAL da anni) senza contestazioni
  note e con spec linkata dalla documentazione ufficiale GDAL.
- Gli attachment si creano con operazioni documentate (Enable Attachments /
  tabelle `__ATTACH` + relationship): flusso supportato da ArcGIS stesso,
  nessun bypass di DRM/licenze.
- Rischio residuo (basso): Esri potrebbe cambiare il formato in future versioni
  di ArcGIS Pro (cfr. opzione `TARGET_ARCGIS_VERSION` del driver, GDAL ≥ 3.9);
  mitigazione: testare il GDB risultante in ArcGIS Reader/Pro e restare su
  tipi di campo compatibili con `ALL`.

### 4. Regole repo ufficiale plugin QGIS (plugins.qgis.org/publish/)

- "The plugin license is compatible with the GPLv2 or later" + "Respect the
  licenses by libraries and other resources that your plugin uses".
- "If the plugin has an external dependency, this needs to be clearly stated
  in the About metadata field".
- "Plugins that utilize binaries will not be approved" (serve codice sorgente
  e repo pubblicamente accessibile).
- Approval umana (con contributor dedicato), pubblicazione anche giornaliera;
  versioni Experimental ammesse per le prime release.
- Fonte: https://plugins.qgis.org/publish/ (+ sottopagine approval/FAQ collegate)

## Vincoli operativi per il plugin (checklist)

- [ ] Licenza repo `GPL-2.0-or-later` (file LICENSE + header + metadata.txt).
- [ ] Solo PyQGIS + GDAL OpenFileGDB (niente SDK Esri, niente DLL/SO bundle).
- [ ] Verificare a runtime `gdal.VersionInfo() >= 3.6` per la scrittura (le QGIS
      correnti montano GDAL ≥ 3.8) e messaggio d'errore chiaro se inferiore.
- [ ] Dipendenze pip (se servono) dichiarate nel campo About + guida installazione.
- [ ] Test di non-corruzione: backup `.gdb` prima della scrittura, `REPACK` /
      `RECOMPUTE EXTENT` via SQL GDAL dopo batch consistenti.
- [ ] Pubblicare prima come Experimental, poi Stable.

## Fonti (URL primarie)

1. https://gdal.org/en/stable/drivers/vector/openfilegdb.html
2. https://gdal.org/en/stable/drivers/vector/filegdb.html
3. https://github.com/Esri/file-geodatabase-api
4. https://raw.githubusercontent.com/Esri/file-geodatabase-api/master/License.txt
5. https://plugins.qgis.org/publish/
6. https://www.apache.org/licenses/LICENSE-2.0 (richiamata dal repo Esri)
