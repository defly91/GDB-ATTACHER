# Strategia di test senza un GDB reale

Come si testa GDB-Attacher **senza avere QGIS, GDAL e un FileGDB con allegati veri** — e cosa invece resta da verificare a mano, dall'utente, su un GDB campione creato da ArcGIS Pro.

Viene dal punto *"Strategia test senza GDB reale: GDB sintetico minimo, fixture, CI"* della mappa (`.scratch/gdb-attacher-plugin/map.md`).

## Il problema

Tre cose non si possono fare su una macchina di CI (né su questa VM):

1. **importare PyQGIS** — `qgis.core`, `qgis.PyQt.*` esistono solo dentro l'installazione di QGIS;
2. **leggere/scrivere un FileGDB** — serve GDAL compilato con il driver OpenFileGDB;
3. **verificare la resa in QGIS** — form, anteprima HTML, mapTip, QML, azioni sui file: serve l'occhio di una persona davanti al programma.

La strategia copre i primi due punti con i **fake** e delega il terzo a una **checklist manuale** su un GDB campione.

## Livelli di test

| Livello | Dove gira | Cosa copre | Marcatore pytest |
|---|---|---|---|
| **unit** (fake QGIS) | CI, ogni push | logica pura: euristiche di discovery, naming, collisioni, deduplica, risoluzione dei file, parser CSV, messaggi, costruzione del report **e i percorsi del wizard** (7 pagine montate sui widget finti: scelta layer, verifica bloccante, anteprima, annullamento, errori) | `unit` |
| **packaging** | CI, ogni push | build dello zip, contenuto del pacchetto, coerenza di `metadata.txt` | `packaging` |
| **richiede_qgis** | QGIS vero, a mano | applicazione dello stile QML, apertura del form, azioni, anteprima HTML, formula QgsExpression | `richiede_qgis` |
| **richiede_gdb** | GDB campione + QGIS vero, a mano | scrittura reale dei blob nella tabella allegati, comportamento su GDB creato da ArcGIS Pro | `richiede_gdb` |

I marcatori sono dichiarati in `pyproject.toml` (`--strict-markers`): un test che usa un marcatore **non dichiarato** fallisce in raccolta, quindi non si inventano livelli a metà. Attenzione a non leggere quella regola come "nessun test senza livello": il marcatore è dichiarato a livello di file (`pytestmark`) e **non** è obbligatorio, quindi la suite del core (`gdb_attacher/tests/`) non lo porta e resta fuori da `-m unit`.

Oggi la selezione dà questo (numeri verificati, `351` test in totale):

```bash
pytest -q -m unit            # 190 test: logica pura + percorsi del wizard (velocissimo)
pytest -q -m packaging       # 11 test: build dello zip e pacchetto
pytest -q -m "not unit and not packaging"   # 150 test: suite del core in gdb_attacher/tests/
pytest -q                    # 351 test, 0 saltati
```

I marcatori `richiede_qgis` e `richiede_gdb` **non hanno ancora test**: quei casi sono la checklist manuale più sotto (si scriveranno come test automatici quando ci sarà un ambiente con QGIS vero). La selezione `-m richiede_qgis` quindi non raccoglie nulla — serve a fissare dove andranno quei test.

## I fake: come funziona

`tests/conftest.py` viene caricato da pytest prima di raccogliere i test e chiama `fake_qgis.install()`, che **inietta in `sys.modules`** i moduli finti:

- `qgis`, `qgis.core`, `qgis.gui`, `qgis.utils`
- `qgis.PyQt`, `qgis.PyQt.QtCore`, `qgis.PyQt.QtGui`, `qgis.PyQt.QtWidgets`, `qgis.PyQt.Qt`, `QtNetwork`, `QtXml`, `QtSql`, `QtSvg`, `QtPrintSupport`

Quindi `import qgis.core` funziona **senza QGIS installato** e il codice del plugin si importa normalmente.

Cosa c'è dentro (`tests/fake_qgis.py`):

- **`FakeLayer`** — layer vettoriale con campi e feature; `name()`, `source()`, `providerType()`, `id()`, `type()`, `isValid()`, `fields()`, `featureCount()`, `getFeatures()`, `addFeature()`, `updateFeature()`, `deleteFeature()`, `loadNamedStyle()`, `dataProvider()`. I metodi QGIS non implementati diventano **no-op registrati** in `layer.chiamate_sconosciute` (utile per capire cosa il plugin si aspetta).
- **`FakeFeature`** — lettura/scrittura per nome o indice, `attribute()`, `setAttribute()`, `id()`, `geometry()`. Un campo esistente ma non valorizzato restituisce **`NULL`** (la sentinella QGIS), non `None`: è il comportamento reale su cui si appoggia `_e_null()` del prototipo 05.
- **`FakeField` / `FakeFields`** — `name()`, `type()` (che risponde con `QMetaType.Type.*`), `typeName()`, `alias()`, `indexFromName()`, indicizzazione per nome o indice. Scrivibili come tuple `("filefoto", "stringa")`.
- **`FakeProject`** — `QgsProject.instance()` singleton con `mapLayers()`, `mapLayersByName()`, `addMapLayer()`.
- **`edit(layer)`** — context manager che **fa rollback** se il blocco solleva: permette di testare "annulla = non si è scritto nulla".
- **`NULL`, `QByteArray`** — `QByteArray` si confronta direttamente con `bytes`, quindi si verifica il round-trip dei blob senza GDAL.
- **dialoghi finti** — `QMessageBox`, `QInputDialog`, `QFileDialog` non aprono nulla: **registrano** la chiamata in `REGISTRO_DIALOGHI` (tipo, titolo, testo) e restituiscono risposte preimpostabili (`risposte.item`, `risposte.directory`, ...). È così che si testano i percorsi del wizard e i messaggi d'errore.
- **widget finti con segnali veri** — `QWizard`, `QWizardPage`, `QTableWidget` (+`QTableWidgetItem`), `QComboBox`, `QProgressBar`, `QLabel`, `QLineEdit`, `QPushButton`, `QCheckBox`, `QRadioButton`, `QGroupBox`, i layout e `QApplication` hanno **stato vero** (testo, voci, celle, titoli, abilitazione, visibilità) e **segnali veri** (`connect`/`emit`, con `blockSignals` rispettato). `QApplication.processEvents()` incrementa un contatore invece di girare la loop; i cursori di attesa si possono leggere (`QApplication.overrideCursor()`). Senza questi, `WizardAllegati(...)` non era nemmeno istanziabile (`AttributeError: 'function' object has no attribute 'connect'`) e nessun percorso del wizard era coperto.
- **`FakeProject.mapLayer(id)` / `FakeLayerTree.findLayer(id)`** — come QGIS: restituiscono il layer con quell'id (o `None`). `PaginaLayer` ci si appoggia per sapere quale layer è selezionato.
- **stub automatici** — un nome di `qgis.*` che i fake non conoscono viene generato al volo: un import non previsto non fa fallire la raccolta dei test.

### Fixture disponibili (da `tests/conftest.py`)

| Fixture | Cosa dà |
|---|---|
| `qcore` | il modulo finto `qgis.core` |
| `progetto` | `QgsProject.instance()` ripulito prima di ogni test |
| `layer_sorgente` | layer con `GLOBALID`, `Nome`, `filefoto`, `FOTO_EST` e 2 feature |
| `layer_attach` | tabella allegati finta con i **6 campi** (GLOBALID, REL_GLOBALID, CONTENT_TYPE, DATA_SIZE, ATT_NAME, DATA) |
| `progetto_con_layer` | progetto con sorgente + `<layer>__ATTACH` già caricati, con le chiavi `sorgente`/`allegati` |
| `cartella_foto` | cartella con file finti: `SS_0001.jpg`, `ACQ_2.png`, `documento.pdf`, `foto d'interno.jpg` e `contatore/ACQ_1.jpg` |
| `carica_modulo` | importa un file `.py` del plugin per percorso (il pacchetto non è installato) |
| `dialoghi` / `risposte_dialoghi` | registro dei dialoghi aperti e code delle risposte |
| `stato_qgis_pulito` (autouse) | azzera progetto, dialoghi, risposte, registro sorgenti e i cursori/contatori di `QApplication` prima e dopo ogni test |

Isolamento: nessun test scrive su file del repo, i dati stanno in `tmp_path`, e `FakeProject` viene azzerato a ogni test.

### Patchare un import nel test

Per simulare "manca la tabella allegati" o "il layer non è valido" non serve altro che costruire il layer finto come serve (o `layer.setValid(False)`), senza `unittest.mock` sul modulo `qgis`: il fake **è** il doppio.

## Cosa gira in CI

``.github/workflows/ci.yml` (in questo ramo il file è versionato come `ci/github-actions.yml` e va copiato lì: vedi `docs/pubblicazione-qgis.md`) su `ubuntu-latest`, Python 3.11:

1. `pip install -r requirements-dev.txt` (solo pytest: nessun GDAL, nessun QGIS);
2. un **guard**: verifica che `qgis` e `osgeo` **non** siano importabili, così i test non possono "passare per sbaglio" usando un QGIS vero;
3. `pytest -q`;
4. lo zip del plugin: lo costruisce e controlla che dentro ci siano `metadata.txt` e non `tests/`, `docs/`, `.github/` (nel workflow il passo è condizionato all'esistenza di `gdb_attacher/`, che in questo ramo c'è).

Copertura automatica attuale in questo ramo: **351 test verdi, 0 saltati** — 190 con marcatore `unit` (fake QGIS, contratto v1/v1-sul-plugin, prototipo 05, **wizard**), 11 `packaging` (build dello zip e pacchetto), 150 nella suite del core (`gdb_attacher/tests/`, senza marcatore). QGIS e GDAL non servono: i moduli `qgis.*` sono quelli finti.

### Cosa coprono i test del wizard

Il wizard (`gdb_attacher/wizard/dialog.py`) viene **istanziato** nei test, con le sette pagine montate sui widget finti:

| File | Cosa difende |
|---|---|
| `tests/test_wizard_montaggio.py` | le 7 pagine esistono (IT ed EN), testi dei pulsanti, segnali dei widget finti |
| `tests/test_wizard_pagina_layer.py` | si scelgono solo layer FileGDB, la tabella `__ATTACH` è esclusa, la scelta non si perde tornando indietro |
| `tests/test_wizard_verifica.py` | messaggi di blocco distinti: tabella allegati assente vs incompleta con l'elenco dei campi |
| `tests/test_wizard_conteggi.py` | anteprima e riepilogo contano gli stessi numeri (i «saltati» non si sommano due volte) |
| `tests/test_wizard_chiavi_stantie.py` | la cache delle chiavi esistenti non sopravvive a un'esecuzione: rieseguire non duplica gli allegati |
| `tests/test_wizard_annullamento.py` | durante il batch i pulsanti sono bloccati e chiudere = chiedere l'annullo; annullare non lascia righe |
| `tests/test_wizard_robustezza.py` | un errore imprevisto si mostra tradotto e non porta via il report; commit fallito = «nulla è stato scritto» |
| `tests/test_wizard_csv.py` | le chiavi del CSV assenti dal layer sono avvisate a video |
| `tests/test_wizard_i18n.py` | niente stringhe italiane nel codice, evidenziazione e messaggi tradotti |
| `tests/test_wizard_stringhe.py` | dizionario IT/EN allineato: chiavi, segnaposto, nessuna chiave morta |

### Contratto v1 vs implementazione

`gdb_attacher/` è **in questo ramo** e i test lo esercitano: `tests/oracolo_v1.py` è l'**oracolo eseguibile** del contratto (naming nelle tre modalità, deduplica, collisioni), `tests/test_contratto_v1.py` lo fa girare sul finto QGIS e `tests/test_contratto_plugin.py` punta gli stessi `CASI_NAMING` sulle funzioni reali del plugin. Il wizard completo è coperto dai `tests/test_wizard_*.py` (tabella qui sopra); quello che resta a mano è la resa in QGIS vero (form, anteprima HTML, QML, azioni sui file).

## Cosa NON si può testare senza un GDB reale

Da fare **a mano**, in QGIS, su un GDB campione. Attenzione: la *logica* del wizard (scelte, conteggi, blocco, annullamento, deduplica) è coperta dai test con il finto QGIS; qui resta la parte che dipende da QGIS/GDAL veri:

- scrittura reale dei blob nella tabella allegati (con il fake si verifica la logica, non il driver OGR);
- che ArcGIS Pro **riconosca** gli allegati scritti da QGIS (relazione `__ATTACHREL`, metadati di sistema);
- stile QML applicato alla tabella vera, anteprima HTML nel form, mapTip sul canvas, azioni *Apri* / *Salva con nome*;
- esecuzione delle formule con `QgsExpression` (`@original_name`, `@stem`, `@ext`, `@index`);
- vincoli di ArcGIS su `ATT_NAME` (lunghezza massima, unicità, caratteri);
- comportamento su tabelle grandi (tempi, memoria della barra di avanzamento, dimensione del form con foto da MB).

## Il GDB campione

Da preparare **una volta** con ArcGIS Pro:

1. crea un FileGDB `campione.gdb` e un feature class **`fotorilievo`** (punti), con un campo testo `filefoto` e qualche feature con campi sensati (uno con foto singola, uno con più file separati da `;`, uno con il campo foto vuoto, uno con nome contenente un apice);
2. abilita gli allegati con `arcpy.management.EnableAttachments` sul layer (crea `fotorilievo__ATTACH`, `__ATTACHREL` e i metadati): **non** creare la tabella a mano;
3. aggiungi 1-2 allegati di prova da Pro, così la deduplica ha qualcosa da incontrare;
4. prepara una cartella `foto/` con i file citati dai campi (incluso un file **mancante** di proposito e un file in sottocartella);
5. verifica di **saper aprire GDB + tabella allegati in QGIS** prima di iniziare i test.

Il `test_attach.gdb` in `prototype/04-attach-style/` **non** è un GDB campione valido per questi test: è una tabella fantasma creata da GDAL (senza `__ATTACHREL` né metadati), buona solo per provare i QML.

## Casi di test manuali

Da eseguire sul GDB campione, con QGIS vero. Per ogni caso: cosa fare, cosa si deve vedere.

### 1. Nuovo allegato

1. Wizard → layer `fotorilievo` → cartella base `foto/` → campo `filefoto` → naming *originale*.
2. Anteprima: conteggi coerenti (da allegare / mancanti / duplicati) e i 5 esempi di naming corretti.
3. Esegui.
4. Atteso: le righe compaiono in `fotorilievo__ATTACH` con `REL_GLOBALID` = GLOBALID della feature **fra graffe**, `ATT_NAME` = nome file, `DATA_SIZE` = dimensione reale, `CONTENT_TYPE` = mime corretto; il form mostra l'anteprima della foto; riaperto il GDB in ArcGIS Pro gli allegati si vedono.

### 2. Campo multivalore

1. Feature con `filefoto = "SS_0001.jpg;ACQ_2.png|contatore/ACQ_1.jpg"` (e una variante con valori su righe diverse).
2. Atteso: **3 allegati** per quella feature, uno per token, con i nomi corretti; un token mancante su disco finisce nell'export CSV dei mancanti e non blocca gli altri.

### 3. Nome con apice

1. Feature con `filefoto = "foto d'interno.jpg"` (apice singolo nel nome).
2. Atteso: `ATT_NAME` è **verbatim** (`foto d'interno.jpg`); l'anteprima nel form si vede lo stesso; le azioni *Apri allegato* / *Salva allegato con nome…* funzionano e non sollevano errori di espressione Python; il report non salta la riga.

### 4. Collisione di nome

1. Feature con due token che danno lo stesso nome (es. `"SS_0001.jpg;contatore/SS_0001.jpg"`).
2. Atteso: primo allegato `SS_0001.jpg`, secondo `SS_0001_2.jpg`; nessuno dei due file viene perso; entrambi i blob corrispondono ai file giusti (aprirli e confrontare).
3. Limite noto da confermare: se `SS_0001.jpg` **esiste già** nella tabella e il campo ha due token omonimi, entrambi vengono **saltati** (il nome non dice da quale token viene). Verifica che il report li conti come duplicati e che cambiando modalità (formula con `@index`) i due file entrino entrambi.

### 5. Campo foto vuoto

1. Feature con `filefoto` vuoto o nullo, insieme ad altre con valore.
2. Atteso: la feature vuota viene **saltata** senza errori, non crea righe, non blocca il lotto; il conteggio dei "saltati" la include.

### 6. Tabella allegati mancante

1. GDB (o layer) **senza** `fotorilievo__ATTACH`, oppure con una tabella incompleta (manca un campo dei 6).
2. Atteso: blocco duro con messaggio che rimanda ad ArcGIS Pro / `EnableAttachments`, **nessuna scrittura**, nessuna tabella creata dal plugin (verificare che il GDB non sia cambiato); il caso "tabella incompleta" è distinto e dice quali campi mancano.

### 7. Galleria multi-foto

1. Feature con 3-4 foto allegate (o più feature con foto ciascuna).
2. Atteso: la galleria mostra **tutte** le foto della feature, in modo scorrevole, con i nomi; le foto grandi non bloccano l'apertura del form; passare da una feature all'altra aggiorna la galleria; un allegato non-immagine (PDF) compare come voce da aprire, non come immagine rotta.

### 8. Deduplica (rilancio senza doppioni)

1. Esegui un lotto, poi **rilancia lo stesso wizard con gli stessi dati**.
2. Atteso: conteggio "duplicati" uguale al numero di allegati già presenti, **zero righe nuove** in `fotorilievo__ATTACH` (confronta il numero di righe prima/dopo); vale anche per un allegato aggiunto a mano da ArcGIS Pro.
3. Verifica la tolleranza alla normalizzazione: un `REL_GLOBALID` con graffe e uno senza (o con maiuscole diverse) sulla stessa feature contano come lo stesso allegato.

### 9. Batch su molte feature con annullamento

1. Prepara un lotto consistente (es. 200+ feature con foto, meglio se foto da qualche MB).
2. Atteso: barra di avanzamento che **avanza** e resta reattiva; QGIS non si blocca; *Annulla* ferma il lavoro ed è possibile chiudere senza errori.
3. Dopo un annullamento: **niente scritture parziali** (conta le righe prima/dopo), oppure — se la scelta di prodotto è il commit a blocchi — il report dice chiaramente quante righe sono state scritte.
4. Rifai il giro fino in fondo: tempi accettabili e conteggi finali coerenti con l'anteprima.

### 10. Switch lingua IT/EN

1. Con QGIS in italiano e poi in inglese (o dal selettore del plugin), apri il wizard.
2. Atteso: testi, etichette dei passi, messaggi d'errore, nomi dei pulsanti e report **tutti** tradotti, senza stringhe rimaste in italiano nell'interfaccia inglese (o viceversa) e senza segnaposto non risolti nel report e nell'export CSV.

### 11. Casi anomali del GDB (dal ticket 03)

- layer **non** su FileGDB (shapefile/GPKG): blocco con messaggio chiaro;
- layer FileGDB **senza campo GlobalID**: blocco;
- `__ATTACH` presente ma con campi rinominati/assenti: blocco con elenco dei campi mancanti;
- GLOBALID **nullo** su una feature: quella feature viene saltata (nessun `REL_GLOBALID` inventato), il resto del lotto prosegue.

### 12. Backup, rollback e integrità

- accetta il backup proposto: il file/cartella di backup esiste ed è integro;
- prova "continua senza backup" e verifica che il messaggio di rischio sia chiaro;
- con *Annulla* a metà: il GDB resta identico a prima (conta righe e riapri in QGIS senza errori);
- dopo l'esecuzione, riapri il GDB in **ArcGIS Pro** e controlla che gli allegati siano visibili e scaricabili (è la prova che la scrittura è "vera", non solo visibile da QGIS).

### 13. Naming formula e CSV

- modalità **formula**: prova `@stem_@index@ext` e `@stem_copia@ext` e confronta i nomi attesi con quelli scritti (è l'unica parte coperta in CI solo a livello di contratto);
- modalità **CSV**: CSV con chiave `GLOBALID`; verifica le righe senza corrispondenza (devono essere contate come saltate e finire nell'export) e il comportamento su CSV con intestazione diversa dal default.

### 14. Performance e form

- 10-20 foto da 3-5 MB: apertura del form e anteprima in tempi accettabili (limite noto: l'anteprima base64 pesa);
- molte righe nella tabella allegati: la tabella attributi resta navigabile e la colonna del blob non appesantisce.

## Come riportare l'esito

Per ogni caso: esito (ok / ko / non verificato), versione di QGIS, se il GDB ha allegati creati da Pro, il messaggio d'errore completo se c'è, ed eventuali screenshot del form. I casi falliti diventano ticket con la riproduzione minima; i casi verificati vanno spuntati qui.

## Riferimenti

- `.scratch/gdb-attacher-plugin/map.md` — decisioni e perimetro v1
- `.scratch/gdb-attacher-plugin/issues/02-creare-attach-senza-rompere-gdb.md` — schema dei 6 campi e perché il plugin non crea la tabella
- `.scratch/gdb-attacher-plugin/issues/06-naming-formula-vs-originale-csv.md` — naming, multi-valore, collisioni, apice
- `prototype/05-field-discovery/` — euristica di discovery ora esercitata dai test sui fake
- `tests/fake_qgis.py` — il finto QGIS (layer, feature, dialoghi e widget Qt con segnali veri)
- `tests/test_wizard_*.py` — i percorsi del wizard montati sui finti
