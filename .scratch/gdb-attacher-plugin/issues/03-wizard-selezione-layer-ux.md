Map: [map](../map.md)
Type: grilling (HITL)
Status: resolved (2026-09-08, branch `grilling/03-wizard-selezione-layer-ux`)
Blocked by: 02
Labels: wayfinder:grilling

## Question

Com'è fatto il wizard? Quale layer seleziono, in che ordine avvengono verifica `_ATTACH`, styling, discovery campi e attach, e come gestiamo errori/annulla?

Decidere con l'umano: step della procedura guidata (selezione layer → check/crea _ATTACH → stile → discovery → selezione campi → naming/CSV → esegui), comportamento se il layer non è su GDB o ha già _ATTACH, preview e undo, testi IT/EN. Richiede `grilling` + `domain-modeling` (fissare termini: layer, _ATTACH, allegato, formula).

## Risoluzione (3 round di grilling, risposte umane: 1A 2A 3A 4A / 5B 6B 7A 8A / 9A 10B)

- **Sorgente layer**: solo layer vettoriali già caricati nel progetto, filtrati su FileGDB. Niente browse diretto del `.gdb` in v1.
- **Ordine step**: selezione layer → verifica bloccante (è FileGDB? ha GlobalID? `__ATTACH` presente con i 6 campi?) → discovery campi → scelta campi → naming (originale/formula/CSV, dettagli al ticket 06) → conferma ed esegui batch → stile `__ATTACH` applicato alla fine.
- **Casi anomali**: blocco duro in tutti i casi (non-GDB, senza GlobalID, `__ATTACH` mancante o incompleta), con rimando ad ArcGIS Pro / `EnableAttachments`. Estende la regola del ticket 02.
- **Preview**: solo conteggi totali (ok / mancanti / duplicati), niente righe di dettaglio. Il dettaglio di valorizzazione vive nella schermata naming (5 feature campione, obbligo ereditato dal ticket 06).
- **Sicurezza**: conferma prima di eseguire, backup `.gdb` proposto ma aggirabile con "continua senza backup" a rischio utente (IT/EN); esecuzione in un'unica transazione con progress bar; report finale aggiunti/duplicati/saltati con export CSV dei missing. Annulla = esci senza aver scritto nulla.
- **Stile**: QML di default applicato automaticamente alla fine, sovrascrivendo l'esistente (che in pratica non esiste mai su tabelle create da Pro).
- **Testi**: IT + EN da subito.
- **Glossario**: vedi `CONTEXT.md` (layer sorgente, tabella allegati, allegato, campo foto, formula).
- **Perimetro**: soglie discovery al ticket 05, sintassi formula al ticket 06, QML al ticket 04.
