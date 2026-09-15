# GDB-Attacher

Plugin QGIS per **allegare foto e file alle feature di un FileGDB Esri** (`*.gdb`), usando i veri allegati del geodatabase (tabella `<layer>__ATTACH`) invece di copiare i file accanto al progetto.

> GDB-Attacher is a QGIS plugin that attaches photos and documents to Esri FileGDB features through the geodatabase's native attachment table.

## A cosa serve

Allega a ogni feature i file elencati in un **campo foto** del layer: il plugin legge il valore (nome file, percorso relativo o assoluto), risolve il file in una **cartella base**, ne scrive i byte nella **tabella allegati** del GDB e applica uno stile che mostra le foto come anteprima HTML nel form.

Serve a chi raccoglie foto sul campo e deve consegnare un `.gdb` con gli allegati dentro, senza passare da ArcGIS Pro per il caricamento dei file.

## Prerequisiti

- **QGIS 3.x** (il prototipo è stato provato su 3.44; la versione minima esatta va fissata in `metadata.txt`).
- Un **FileGDB con gli allegati già abilitati da ArcGIS Pro** (`EnableAttachments` sul layer sorgente): il plugin non crea né modifica lo schema della tabella allegati.
- Le **foto/file su disco**, in una cartella base (anche con sottocartelle).
- Su Windows/nell'ambiente di consegna tipico: nessuna installazione di ArcGIS richiesta per usare il plugin, ma il GDB deve essere stato preparato una volta con Pro.

## Installazione

**Dallo zip (consigliato)**

1. Genera lo zip: `bash scripts/build_plugin_zip.sh` → `dist/gdb_attacher-<versione>.zip`
2. In QGIS: *Plugin → Gestisci e installa plugin → Installa da ZIP* e scegli il file.

**Copia manuale** (per lo sviluppo)

Copia la cartella `gdb_attacher/` dentro il profilo QGIS:

- Windows: `%APPDATA%\QGIS\QGIS3\profiles\default\python\plugins\`
- Linux: `~/.local/share/QGIS/QGIS3/profiles/default/python/plugins/`
- macOS: `~/Library/Application Support/QGIS/QGIS3/profiles/default/python/plugins/`

Poi riavvia QGIS e attiva *GDB-Attacher* in *Gestisci e installa plugin*.

## Uso (wizard)

1. Carica nel progetto il **layer sorgente** del GDB (e, se già presente, la sua tabella `<layer>__ATTACH`).
2. Avvia il wizard GDB-Attacher e **seleziona il layer sorgente** tra quelli su FileGDB già nel progetto.
3. Il plugin esegue la **verifica bloccante**: è un FileGDB? ha il campo GlobalID? la tabella allegati è presente e completa (GLOBALID, REL_GLOBALID, CONTENT_TYPE, DATA_SIZE, ATT_NAME, DATA)? Se qualcosa manca si ferma e rimanda ad ArcGIS Pro: non crea la tabella da sé.
4. **Scelta della cartella base** delle foto e **auto-discovery dei campi foto** (l'euristica propone i campi, tu confermi).
5. **Naming**: decidi come si chiamerà l'allegato dentro il GDB —
   *nome originale* (default), *formula* QGIS per feature (`@original_name`, `@stem`, `@ext`, `@index`) oppure *CSV* con l'elenco dei file su chiave `GLOBALID`.
6. **Conferma ed esegui**: anteprima con i conteggi (da allegare / mancanti / duplicati), esecuzione in una sola transazione con barra di avanzamento, report finale esportabile in CSV.
7. Alla fine il plugin **applica lo stile della tabella allegati**, così le foto si vedono come anteprima nel form delle feature.

## Stato: v1 in sviluppo

Il pacchetto del plugin e la v1 sono **in sviluppo**: API e nomi dei file possono ancora cambiare.

Funzioni previste nella v1:

- wizard completo (verifica → discovery → campi → naming → esecuzione → stile);
- **deduplica** su `(REL_GLOBALID, ATT_NAME)`: rilanciare lo stesso lavoro non crea doppioni;
- **export CSV** dei file mancanti e degli errori;
- **batch** su molte feature con barra di avanzamento **annullabile** (annullare = non si è scritto nulla);
- **i18n IT/EN** (interfaccia e messaggi, da subito);
- **galleria multi-foto** per feature (più allegati nella stessa schermata);
- **QML variante A** incluso nel plugin e applicato automaticamente alla tabella allegati;
- naming: nome originale, formula QGIS per feature, CSV join su `GLOBALID`; multi-valore con `;`, `|` o a capo; nomi con apice lasciati verbatim e gestiti nelle azioni.

Rinviato a dopo la v1: **QField** e la galleria su mobile.

La **pubblicazione sul repository ufficiale dei plugin QGIS** avverrà **dopo i test dell'utente su un GDB reale** creato da ArcGIS Pro: prima di allora il plugin si installa solo da zip o copia nel profilo.

## Limiti noti

- **GDAL/OpenFileGDB non conosce gli allegati e non può creare la tabella `__ATTACH`**: se manca, il plugin si blocca e chiede di abilitarla da ArcGIS Pro. Una tabella creata a mano risulta "fantasma" (mancano `__ATTACHREL` e i metadati del GDB) e ArcGIS la ignora.
- L'**anteprima HTML funziona per le immagini**; PDF, TIFF, MP4 e gli altri formati si aprono con l'azione *Apri allegato* (i browser integrati in Qt non li renderizzano).
- Il **naming "nome originale" è verbatim**: se nella stessa feature due file hanno lo stesso nome il secondo prende il suffisso `_2`; con un nome già allegato il token ambiguo viene saltato (usare la modalità formula con `@index` per evitarlo).
- I **vincoli lato ArcGIS su `ATT_NAME`** (lunghezza, unicità, caratteri) non sono ancora stati riconfermati su un GDB creato da Pro.

## Sviluppo e test

I test **girano senza QGIS e senza GDAL** grazie a un finto QGIS iniettato in `sys.modules` (`tests/fake_qgis.py`): servono solo Python 3 e pytest.

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements-dev.txt
.venv/bin/pytest -q
```

Build dello zip del plugin: `bash scripts/build_plugin_zip.sh` (vedi `ci/github-actions.yml` per la CI; il workflow va copiato in `.github/workflows/ci.yml`, perché questo token di push non ha lo scope `workflow`).

Cosa si può testare in CI e quali casi richiedono invece un GDB reale: **`docs/test-strategy.md`**.

## Licenza

**GPL-2.0-or-later** (GPLv2+), come i plugin del repository ufficiale QGIS.
