Map: [map](../map.md)
Type: prototype (HITL)
Status: resolved (2026-09-15, branch `prototype/04-stile-html-anteprime`, variante **A**)
Blocked by: 02
Labels: wayfinder:prototype

## Prototype (2026-09-08, branch `prototype/04-stile-html-anteprime`, IN ATTESA di reazione umana)

Artefatto: `prototype/04-attach-style/` — 3 varianti QML + `test_attach.gdb` + `applica_stile.py` + `anteprima_demo.html`. Dettagli, confronto e domande in `prototype/04-attach-style/README.md`.

- A `variante_A_anteprima.qml`: 2 tab, dossier HTML inline + dati tecnici.
- B `variante_B_essenziale.qml`: gruppo unico senza HTML, anteprima solo in mapTip.
- C `variante_C_blindata.qml`: 3 tab, `ATT_NAME` obbligatorio, pulsante Apri nel form.
- Verdetti chiusi: `to_base64("DATA")` fedele ai byte (4/4 round-trip su GDB); **form HTML via `expression.evaluate` JS, mai `[% %]`** (sintassi mapTip/stampa; cfr. qgshtmlwidgetwrapper.cpp); ExternalResource NON applicabile al blob (solo nome, non percorso); PDF/TIFF/MP4 solo via azione Apri (export temp + programma predefinito); limite noto nomi con apice → ticket 06.
- Validazione headless: 3/3 reload QML OK, vincoli/azioni/alias serializzati. Non verificato: resa visiva reale — serve prova in QGIS (`applica('A'/'B'/'C')`).

## Risoluzione (reazione umana 2026-09-15)

- **Variante scelta: A — Anteprima in testa** (2 tab: *Anteprima* HTML inline + *Dati tecnici*; mapTip con miniatura; azioni *Apri*/*Salva con nome*; blob visibile ma in sola lettura).
- Le altre due varianti restano nell'artefatto come riferimento, non si applicano di default.
- Sotto-domande del README non discusse esplicitamente (restano ricombinabili in implementazione): anteprima in tabella attributi, pulsante *Apri* dentro il form, QML unico vs per-mime. La variante A implica: niente HTML in tabella attributi, *Apri* via menu Azioni, QML unico.
- Verdetti tecnici e limite apice/nomi confermati come da prototipo (dettaglio nel `prototype/04-attach-style/README.md`).

## Question

Quale stile diamo al layer `_ATTACH` per vedere le foto come HTML e aprire gli altri formati?

Produrre con `prototype` un artefatto concreto: QML di esempio + form con widget HTML/External Resource per JPG/PNG, azione "apri file" per PDF/TIFF/MP4, su un GDB di test. L'umano reagisce all'artefatto. Collegare l'asset al ticket alla risoluzione.
