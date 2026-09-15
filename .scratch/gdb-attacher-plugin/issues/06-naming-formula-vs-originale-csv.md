Map: [map](../map.md)
Type: grilling (HITL)
Status: resolved (2026-09-15, branch `grilling/06-naming-formula-vs-originale-csv`)
Blocked by: 03, 05
Labels: wayfinder:grilling

## Question

Naming degli allegati: teniamo il nome originale, applichiamo una formula, o join via CSV su identificativo univoco?

Decidere con l'umano: default (nome originale), sintassi formula (espressioni QGIS? campi disponibili?), sanitizzazione e collisioni, formato CSV atteso (colonne, chiave GLOBALID vs altro ID, encoding/separatore, validazione), preview prima dell'attach. Richiede `grilling` + `domain-modeling`.

## Risoluzione (3 round di grilling; risposte umane: `1A 2A 4A 5A 6A` / `8A 9A 10A 11A 12C` / `7A 13A 15A`)

**Principio di separazione.** Il *file da allegare* è sempre risolto dal **campo foto + cartella base** (ticket 05); il naming calcola **solo il nome allegato**. Più campi foto selezionati → un allegato per campo (3 campi = 3 righe nella tabella allegati).

**Tre modalità esclusive** (una per esecuzione):
- **Nome originale** (default): `ATT_NAME` = nome file reale risolto, **estensione inclusa**, verbatim.
- **Formula**: espressione **QGIS** per feature, precompilata `@original_name`; variabili `@original_name`, `@stem`, `@ext` (col punto), `@index` (1-based) + i campi del layer; può riscrivere anche l'estensione; validata nella preview. In QGIS `'…'` = stringa, `"…"` = campo (trappola documentata nel testo di aiuto).
- **CSV**: è la **fonte dell'elenco file** (non un semplice rename): una riga per allegato, più righe con la stessa chiave = più allegati; chiave selezionabile, **default `GLOBALID`** normalizzato (con/senza graffe, case); nomi colonna configurabili; colonna `att_name` opzionale (altrimenti nome file).

**Multi-valore.** Un campo con più nomi file (`a.jpg;b.jpg`) si spezza su `;`, `|` e a capo (**virgola esclusa**, rischio prosa) → un allegato per token, `@index` 1-based; i token sono indipendenti (uno mancante va nei missing senza trascinare gli altri).

**CSV robustezza.** Accetta `;` e `,` (rilevati dal file), encoding auto (UTF-8 con/senza BOM, fallback cp1252); validazione non bloccante: chiavi del CSV assenti nel layer → avviso, chiavi duplicate → avviso, file non trovato → missing. Blocco solo per CSV illeggibile o privo della colonna chiave.

**Caratteri.** `ATT_NAME` conservato **verbatim nel GDB** (accenti, apici, spazi): nessuna sanitizzazione in scrittura. Il limite apice del ticket 04 è lato azione e si risolve con `[% to_base64("ATT_NAME") %]` + `base64.b64decode(...)` (verificato 8/8 su QGIS 3.44.4, incl. apice/accenti/newline; alternativa `json.dumps`). `QgsExpression.quotedString` **non** è affidabile come literal Python (corrompe in silenzio `O'Brien`).

**Collisioni ed errori.** Collisione sullo stesso `(REL_GLOBALID, ATT_NAME)` (ticket 02) → suffisso **`nome_2.ext`/`nome_3.ext`** (1-based, il primo tiene il nome pulito), contata in preview e report. Formula/CSV che produce nome vuoto/nullo → **salta e prosegue** con riga nel report; il blocco duro resta per i casi strutturali del ticket 03.

**Preview.** 5 feature campione con colonne *valore campo → file risolto (percorso) → nome allegato finale*, più **quale campo foto** e **conteggio per campo**; collisioni/missing evidenziati; conteggi totali ok/missing/duplicati (ticket 03).

**Verdetti tecnici (chiusi, headless QGIS 3.44.4).** Naming per-feature via `QgsExpression.evaluate(context)` / `prepare(context)` (in 3.44.4 **non** esiste `setExpressionContext`); variabili custom via `QgsExpressionContextScope().setVariable(name, value, False)` + `ctx.appendScope(scope)`; il pattern feature-based è già usato in `prototype/04-attach-style/genera_prototipo.py`. Nessun vincolo `ATT_NAME` (lunghezza max, unicità, caratteri) documentato da fonti locali; i due script scrivono verbatim senza sanitizzare; la dedup `(REL_GLOBALID, ATT_NAME)` è una scelta di progetto, non un vincolo ArcGIS.

**Glossario.** `CONTEXT.md`: nuovo termine **Nome allegato**; **Formula** ora "calcola il **nome allegato**" (non il file).

**Resta aperto (non deciso qui).** Dove si sceglie la cartella base nell'ordine del wizard (punto del ticket 03 emerso dal ticket 05); vincoli `ATT_NAME` lato ArcGIS su un `__ATTACH` vero creato da Pro; performance/batch e resume (mappa).
