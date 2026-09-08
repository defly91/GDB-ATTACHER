Map: [map](../map.md)
Type: prototype (HITL)
Status: open
Blocked by: 02
Labels: wayfinder:prototype

## Prototype (2026-09-08, branch `prototype/04-stile-html-anteprime`, IN ATTESA di reazione umana)

Artefatto: `prototype/04-attach-style/` — 3 varianti QML + `test_attach.gdb` + `applica_stile.py` + `anteprima_demo.html`. Dettagli, confronto e domande in `prototype/04-attach-style/README.md`.

- A `variante_A_anteprima.qml`: 2 tab, dossier HTML inline + dati tecnici.
- B `variante_B_essenziale.qml`: gruppo unico senza HTML, anteprima solo in mapTip.
- C `variante_C_blindata.qml`: 3 tab, `ATT_NAME` obbligatorio, pulsante Apri nel form.
- Verdetti chiusi: `to_base64("DATA")` fedele ai byte (4/4 round-trip su GDB); ExternalResource NON applicabile al blob (solo nome, non percorso); PDF/TIFF/MP4 solo via azione Apri (export temp + programma predefinito); limite noto nomi con apice → ticket 06.
- Validazione headless: 3/3 reload QML OK, vincoli/azioni/alias serializzati. Non verificato: resa visiva reale — serve prova in QGIS (`applica('A'/'B'/'C')`).

## Question

Quale stile diamo al layer `_ATTACH` per vedere le foto come HTML e aprire gli altri formati?

Produrre con `prototype` un artefatto concreto: QML di esempio + form con widget HTML/External Resource per JPG/PNG, azione "apri file" per PDF/TIFF/MP4, su un GDB di test. L'umano reagisce all'artefatto. Collegare l'asset al ticket alla risoluzione.
