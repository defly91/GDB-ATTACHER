# Verifica con un QGIS reale (container, headless)

I test di `tests/` e `gdb_attacher/tests/` girano con un **finto QGIS**: verificano la logica, non le
API. Questa procedura copre il pezzo che i finti non possono dare — importazione contro le API vere,
caricamento del QML di stile, valutazione delle formule con `QgsExpression` e apertura del wizard —
usando l'immagine Docker ufficiale di QGIS, senza installare nulla sul MiniPC.

## Comandi

```bash
# QGIS 3.x (piattaforma di riferimento del plugin)
docker run --rm --memory=1500m -e QT_QPA_PLATFORM=offscreen \
  -e REPO=/repo -e PYTHONPATH=/repo:/usr/share/qgis/python \
  --entrypoint python3 \
  -v "$PWD":/repo:ro qgis/qgis:release-3_34 \
  /repo/scripts/verifica_qgis_reale.py

# QGIS 4.x (verifica di compatibilità futura)
docker run --rm --memory=1500m -e QT_QPA_PLATFORM=offscreen \
  -e REPO=/repo -e PYTHONPATH=/repo:/usr/share/qgis/python \
  --entrypoint python3 \
  -v "$PWD":/repo:ro qgis/qgis:stable \
  /repo/scripts/verifica_qgis_reale.py
```

Lo script stampa una riga `[PASS]`/`[FAIL]` per controllo e un riepilogo; esce con codice 1 se
qualcosa fallisce. Il secondo script, `scripts/probe_qml.py`, serve quando un QML viene rifiutato:
mostra il messaggio d'errore completo e distingue un QML rotto da un problema di geometria.

## Trappole già incontrate

- **`PYTHONPATH`**: le immagini QGIS lo impostano a `/usr/share/qgis/python`. Non sovrascriverlo:
  va esteso (`/repo:/usr/share/qgis/python`), altrimenti `import qgis.core` fallisce.
- **QML di tabella**: `stile_attach_variante_A.qml` è il QML della **tabella allegati**, che non ha
  geometria. Va caricato su un layer `None?field=...`, non su un layer di punti: QGIS lo rifiuta se
  la geometria non combacia (errore fuorviante, riportato come "Loading style file failed").
- **QGIS 4 = Qt6/PyQt6**: `qgis/qgis:stable` oggi è QGIS 4.2.2, dove `PyQt5` non esiste più. Il
  wizard (PyQt5) non si può istanziare lì: è atteso e non è un difetto del plugin. La verifica del
  wizard richiede un'immagine **3.x** (`release-3_34`).
- Il container va lanciato con `--entrypoint python3`: l'entrypoint dell'immagine avvia QGIS desktop.

## Test end-to-end su un FileGDB vero (senza ArcGIS)

`scripts/e2e_filegdb.py` crea un FileGDB con il driver `OpenFileGDB` di GDAL (serve GDAL ≥ 3.6,
quindi **non** l'immagine QGIS 3.34 che ha GDAL 3.4), carica i layer in QGIS e fa passare l'intero
percorso reale: verifica → naming → scrittura → rilettura indipendente con GDAL.

```bash
docker run --rm --memory=1500m -e QT_QPA_PLATFORM=offscreen \
  -e REPO=/repo -e PYTHONPATH=/repo:/usr/share/qgis/python \
  --entrypoint python3 -v "$PWD":/repo:ro qgis/qgis:stable \
  /repo/scripts/e2e_filegdb.py
```

Copre (esito registrato: **11/11**):

- la verifica del plugin accetta un FileGDB con `GLOBALID` e tabella `__ATTACH` con i 6 campi;
- la scrittura produce una riga valida: `ATT_NAME` verbatim (apice e spazi), `CONTENT_TYPE`
  dedotto dall'estensione, `DATA_SIZE` = dimensione reale, blob byte-identico al file,
  `REL_GLOBALID` maiuscolo e con graffe, `GLOBALID` maiuscolo e senza graffe;
- rilanciare lo stesso lavoro non duplica (deduplica idempotente, 1 "già presente");
- annullare durante il batch non lascia scritture parziali (`annullata=True`, 0 aggiunti).

**Trappola verificata**: il driver OpenFileGDB restituisce i campi binari da `GetField` come
**testo esadecimale** (1024 byte → 2048 caratteri). Un blob perfetto sembra quindi raddoppiato:
`scripts/probe_blob_gdal.py` è l'esperimento di controllo che lo dimostra (una scrittura fatta
con solo GDAL si comporta allo stesso modo). Non è un difetto del plugin.

**Cosa resta comunque da provare a mano** su un GDB creato da ArcGIS Pro: relationship class
`__ATTACHREL`, metadati `GDB_Items`, vincoli lato ArcGIS su `ATT_NAME`, e la visibilità
dell'allegato nell'applicazione Esri. Sono le cose che GDAL non sa creare, quindi nessun test
automatico può sostituirle.

## Esito registrato (2026-09-15)

- QGIS **4.2.2** (`qgis/qgis:stable`): 5/6 — import dei 9 moduli, `QgsExpression` sulla formula di
  naming, QML sulla tabella e `qgis.utils` tutti OK; fallisce solo il wizard per assenza di PyQt5
  (QGIS 4 è Qt6: il plugin è PyQt5, come da target 3.x).
- QGIS **3.34.5** (`qgis/qgis:release-3_34`): **6/6** — incluso il wizard: la finestra
  `WizardAllegati` si costruisce con tutte e 7 le pagine su Qt5 reale.
