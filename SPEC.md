# GDB-Attacher — Specifica v1

Specifica decisionale per il plugin QGIS **GDB-Attacher**: allega foto e file alle feature di un
FileGDB Esri, scrivendo nella tabella allegati `<layer>__ATTACH`.

Stato: mappa wayfinder **chiusa** (ticket 01–07 risolti, tracker in `.scratch/gdb-attacher-plugin/`).
Questa spec consolida le decisioni prese; non introduce scelte nuove. Glossario e lingua dei termini:
`CONTEXT.md`.

---

## 1. Perimetro v1

Dentro la v1:

- wizard guidato su un **layer sorgente** già caricato in QGIS e su FileGDB;
- verifica bloccante della struttura GDB e scrittura nella **tabella allegati** esistente;
- **auto-discovery** dei campi foto con livelli di confidenza;
- **naming** dell'allegato in tre modalità esclusive (originale / formula / CSV);
- **galleria multi-foto**: più foto per feature nello stesso passaggio;
- **deduplica** `(REL_GLOBALID, ATT_NAME)`, batch con barra di avanzamento annullabile;
- **report** finale con conteggi ed **export CSV** dei mancanti/errori;
- **stile** del layer allegati: QML variante A incluso e applicato automaticamente;
- interfaccia **IT + EN**.

Fuori v1: QField (da valutare dopo), pubblicazione sul repo ufficiale QGIS (dopo i test su GDB reale),
creazione della tabella allegati (mai: la crea ArcGIS Pro), anteprime dedicate a video/audio.

---

## 2. Architettura del plugin

```
gdb_attacher/
├── metadata.txt            # name, qgisMinimumVersion, version, license GPLv2+, repository
├── __init__.py             # classFactory(iface)
├── plugin.py               # registrazione QAction / menu
├── core/
│   ├── attach.py           # verifica struttura GDB + scrittura allegati (6 campi)
│   ├── discovery.py        # euristica suggerisci_campi() (portata dal prototipo 05)
│   ├── naming.py           # tre modalità di nome allegato + collisioni
│   ├── styles.py           # applicazione QML variante A
│   └── report.py           # conteggi, motivi di scarto, export CSV
├── wizard/
│   ├── strings.py          # stringhe IT/EN centralizzate
│   └── dialogs           # step della procedura guidata
└── resources/
    ├── qml/variante_A_anteprima.qml
    └── icons/
```

Regole di dipendenza: `core/naming.py`, `core/discovery.py` e `core/report.py` devono restare
**testabili senza QGIS** (import di `qgis` dentro le funzioni o protetti da `try/except ImportError`),
come già fanno i prototipi.

## 3. Flusso del wizard

Ordine degli step (decisione ticket 03):

1. **Selezione layer sorgente** — solo layer vettoriali già nel progetto, filtrati su FileGDB.
   Nessuna navigazione diretta del `.gdb` in questa versione.
2. **Verifica bloccante** (blocco duro + rimando ad ArcGIS Pro / `EnableAttachments`):
   - il layer non è su FileGDB;
   - manca `GLOBALID`;
   - la **tabella allegati** è assente o incompleta (non ha i 6 campi).
3. **Cartella base dei file** — richiesta prima o insieme alla selezione dei campi (senza cartella base
   il livello A della discovery non esiste).
4. **Auto-discovery dei campi foto** → proposta con livello di confidenza.
5. **Scelta dei campi** (più campi = un allegato per campo).
6. **Naming** — originale / formula / CSV, con **preview**: 5 feature campione, colonne
   *valore campo → file risolto (percorso) → nome allegato finale*, campo foto di origine e conteggio per campo.
7. **Conferma ed esecuzione** — conteggi totali (ok / mancanti / duplicati), backup proposto ma
   aggirabile ("continua senza backup", a rischio dell'utente), transazione unica, progress bar annullabile.
8. **Stile** — QML variante A applicato automaticamente alla fine (sovrascrive l'esistente),
   con possibilità di non applicarlo.
9. **Report finale** — aggiunti / già presenti (dedup) / saltati / errori, con export CSV.

Annulla = uscire senza aver scritto nulla.

## 4. Scrittura nella tabella allegati

- Il plugin **non crea mai** la tabella `<layer>__ATTACH`: la crea solo ArcGIS Pro (`EnableAttachments`),
  che genera anche `__ATTACHREL` e i metadati di sistema. Crearla a mano produce una tabella fantasma
  per ArcGIS: se manca o è incompleta → **blocco**.
- Campi scritti (6, normalizzati):

  | Campo | Contenuto |
  | --- | --- |
  | `GLOBALID` | uuid4 upper, **senza** graffe |
  | `REL_GLOBALID` | GUID della feature padre, upper, **con** graffe `{...}` |
  | `ATT_NAME` | nome allegato (verbatim, cfr. §6) |
  | `CONTENT_TYPE` | mime reale del file |
  | `DATA_SIZE` | dimensione del blob |
  | `DATA` | contenuto del file (`QByteArray`) |

- Parent-GUID nullo → la riga viene rifiutata (fa fede lo script a click, non il batch).
- Deduplica su `(REL_GLOBALID, ATT_NAME)` **normalizzati**: se l'allegato esiste già, si salta e si conta
  come "già presente".
- Scrittura in un'unica transazione `edit()`; in caso di annullamento nessuna riga resta scritta.

## 5. Auto-discovery dei campi foto

- Quattro segnali **sui valori** (percentuale con estensione, percentuale di file esistenti,
  percentuale multivalore, scarto di GUID/numerici/percorsi remoti) più un segnale **sul nome del campo**.
- Livelli di confidenza **A / B / C / D**; soglia di preselezione **0.5** (banda misurata e vuota:
  campi veri 80–91%, prosa 0%), da riconfermare su un GDB cliente.
- Misura già fatta: 7/7 campi foto veri preselezionati e 0 falsi positivi con cartella base (6/7 senza).
- Attenzione: i valori nulli arrivano dalla sentinella `NULL` di QGIS, non da `None`; il nome del campo
  suggerisce ma non decide (`link_foto` / `id_foto` hanno il nome giusto e i valori sbagliati).
- UI: livello mostrato accanto al campo, testi IT/EN.

## 6. Naming dell'allegato

Principio di separazione: il **file da allegare** è sempre risolto da campo foto + cartella base;
il naming decide **solo il nome allegato** (`ATT_NAME`).

Tre modalità **esclusive per esecuzione**:

1. **Nome originale** (default): `ATT_NAME` = nome file reale risolto, **con estensione**, verbatim.
2. **Formula**: espressione **QGIS** valutata per feature, precompilata `@original_name`.
   Variabili disponibili: `@original_name`, `@stem`, `@ext` (con il punto), `@index` (1-based) e i campi
   del layer; può riscrivere anche l'estensione; validata nella preview.
   Trappola da documentare nell'aiuto: in QGIS `'…'` è stringa e `"…"` è campo.
   Valutazione per-feature: `QgsExpression.evaluate(context)` / `prepare(context)`; variabili custom via
   `QgsExpressionContextScope().setVariable(name, value, False)` + `appendScope(scope)`.
3. **CSV**: è la **fonte dell'elenco dei file** (non un semplice rename). Una riga per allegato; più righe
   con la stessa chiave = più allegati. Chiave selezionabile, default `GLOBALID` normalizzato
   (con/senza graffe, case-insensitive); nomi colonna configurabili; colonna `att_name` opzionale
   (altrimenti si usa il nome file).

Multi-valore: un campo con più nomi (`a.jpg;b.jpg`) si spezza su `;`, `|` e a capo (**virgola esclusa**,
rischio prosa) → un allegato per token, `@index` 1-based, token indipendenti (un mancante non trascina gli altri).

CSV — robustezza: separatore `;` o `,` rilevato dal file; encoding automatico (UTF-8 con/senza BOM,
fallback cp1252); validazione non bloccante (chiavi del CSV assenti nel layer → avviso; chiavi duplicate →
avviso; file non trovato → missing); blocco solo se il CSV è illeggibile o privo della colonna chiave.

Caratteri: `ATT_NAME` conservato **verbatim** nel GDB (accenti, apici, spazi), nessuna sanitizzazione in
scrittura. Il limite con l'apice riguarda solo le azioni del form e si risolve con
`[% to_base64("ATT_NAME") %]` + `base64.b64decode(...)` (`QgsExpression.quotedString` non è affidabile
come literal Python: corrompe in silenzio `O'Brien`).

Collisioni: stessa coppia `(REL_GLOBALID, ATT_NAME)` → suffisso `nome_2.ext` / `nome_3.ext` (1-based, il
primo tiene il nome pulito), contata in preview e nel report. Formula o CSV che produce un nome
vuoto/nullo → si salta e si prosegue, con riga nel report.

## 7. Stile e anteprime

Variante **A — Anteprima in testa** (scelta dal ticket 04), inclusa nel plugin e applicata in automatico:

- due tab: *Anteprima* (HTML inline) e *Dati tecnici*; mapTip con miniatura;
- azioni *Apri* e *Salva con nome*; blob visibile ma in sola lettura;
- form HTML costruito via **bridge JS `expression.evaluate`**, mai `[% %]` nel form;
- `ExternalResource` **non** applicabile al blob (conosce solo il nome, non il percorso);
- PDF / TIFF / MP4 solo tramite azione *Apri* (export temporaneo + programma predefinito);
- niente HTML nella tabella attributi; QML unico (non per-mime).

## 8. Report

- Conteggi finali: **aggiunti**, **già presenti** (dedup), **saltati**, **errori/mancanti**.
- Righe di dettaglio per mancanti/errori: feature, campo foto, file atteso, motivo.
- **Export CSV** del dettaglio (richiesta esplicita in v1), con separatore compatibile con Excel italiano.

## 9. Batch e prestazioni

- Migliaia di foto elaborate in **una transazione** con barra di avanzamento **annullabile**;
- interfaccia QGIS non bloccata durante l'esecuzione;
- l'ordine di scrittura segue i campi foto selezionati e i token multi-valore;
- nessuna riga scritta se l'utente annulla.

## 10. Internazionalizzazione

- Tutte le stringhe utente in `wizard/strings.py` (o modulo equivalente) con dizionario `it` e `en`;
- lingua iniziale = lingua di QGIS, default **italiano**;
- testi degli step, dei livelli di confidenza, degli errori e del report tradotti in entrambe le lingue.

## 11. Vincoli, licenze e limiti noti

- Solo **GDAL OpenFileGDB**: nessun binario Esri, nessuna dipendenza dal FileGDB SDK; licenza plugin **GPLv2+**,
  dipendenze dichiarate in `metadata.txt`; nessuna violazione TOS rilevata (ticket 01).
- GDAL **non conosce** gli attachment: la lettura/scrittura passa dalla tabella allegati, non da API dedicate.
- Vincoli `ATT_NAME` lato ArcGIS (lunghezza massima, unicità per feature, caratteri) **non verificati**:
  il GDB di test del prototipo è una tabella fantasma GDAL; da riconfermare su un `__ATTACH` creato da Pro.

## 12. Criteri di accettazione

Test manuali da fare su un **GDB reale** con allegati abilitati da ArcGIS Pro (prerequisito alla pubblicazione):

1. tabella allegati assente → blocco con messaggio che rimanda a Pro;
2. layer non FileGDB o senza `GLOBALID` → blocco;
3. singolo campo foto, nomi con estensione → allegati creati e visibili in ArcGIS Pro;
4. campo multi-valore (`;`, `|`, a capo) → un allegato per token;
5. nome con apice (`O'Brien.jpg`) → allegato leggibile e anteprima funzionante;
6. collisione di nome sulla stessa feature → suffisso `_2`;
7. campo foto vuoto/nullo → riga saltata nel report, nessun blocco;
8. formula QGIS con `@stem`/`@ext`/`@index` → nomi coerenti nella preview;
9. CSV come fonte elenco file (chiave `GLOBALID`, con e senza graffe) → allegati corretti;
10. rilancio identico dell'operazione → nessun doppione (dedup);
11. annullamento a metà batch → nessuna riga scritta;
12. galleria multi-foto (più campi foto) → più allegati per la stessa feature;
13. switch lingua IT/EN → tutte le stringhe tradotte;
14. stile: QML variante A applicato automaticamente, anteprima e *Apri* funzionanti.

Test automatici (CI, senza QGIS/GDAL): logica pura di naming (tre modalità, collisioni, split multi-valore),
discovery sui fake, dedup, calcolo del report. Vedi `docs/test-strategy.md`.

## 13. Riferimenti

- Tracker e decisioni: `.scratch/gdb-attacher-plugin/map.md` + `issues/01…07`.
- Research: `research-attach-schema.md` (schema `__ATTACH`), `research-tos.md` (licenze),
  `research-qgdb-prior-art.md` (prior art QGDB).
- Prototipi: `prototype/04-attach-style/` (QML variante A + `test_attach.gdb`), `prototype/05-field-discovery/`
  (`suggerisci_campi.py`, tabella match-rate).
- Script primary source: `Allega foto GDB.py`, `Aggiungi singola doto al GDB.py`.
- Glossario: `CONTEXT.md`.
