Map: [map](../map.md)
Type: grilling (HITL)
Status: resolved (2026-09-15, branch `grilling/07-perimetro-v1-e-altre-idee`)
Blocked by: 01, 06
Labels: wayfinder:grilling

## Question

Altre idee e perimetro v1: cosa entra nel primo rilascio pubblico e cosa resta fog?

## Decisioni (con l'umano, round unico)

**Dentro la v1 (tutto confermato):**
- **Deduplica/idempotenza**: prima di scrivere si verifica che non esista già un allegato con la coppia `(REL_GLOBALID, ATT_NAME)`; se esiste si salta e si conta come "già presente" nel report.
- **Export CSV del report**: oltre al report a video, CSV con le righe mancanti/errate (feature, campo, file atteso, motivo).
- **Batch + barra di avanzamento**: migliaia di foto in transazione unica, avanzamento annullabile, UI QGIS non bloccata.
- **i18n IT/EN** completa (stringhe centralizzate, default italiano).
- **Galleria multi-foto**: più foto per feature nello stesso passaggio (campo multivalore o più campi foto → più righe allegato, un solo giro).
- **QML variante A incluso nel plugin e applicato automaticamente** dopo la scrittura, con possibilità di non applicarlo.
- Restano dentro anche le decisioni già prese: wizard (03), stile/anteprime (04), auto-discovery campi (05), naming originale/formula/CSV (06), regole di sicurezza sulla tabella allegati (02).

**Fuori v1 / fog:**
- **QField**: da valutare più avanti, non decidere ora (nessuna implementazione in v1).
- **Pubblicazione sul repo ufficiale QGIS**: si pubblica **dopo** i test dell'utente su un GDB reale; per ora esecuzione locale/zip.
- Video/audio e altri formati: restano come oggi (aperti via azione *Apri*, nessuna anteprima dedicata — decisione 04).

## Nota

La mappa è chiusa: non resta nulla da decidere prima di passare a `to-spec`.
