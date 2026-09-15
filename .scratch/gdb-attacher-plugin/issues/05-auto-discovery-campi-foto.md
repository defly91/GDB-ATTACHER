Map: [map](../map.md)
Type: task (AFK)
Status: resolved (2026-02-20, branch `task/05-auto-discovery-campi-foto`)
Blocked by: 03
Labels: wayfinder:task

## Question

Quale euristica di auto-discovery dei campi foto/allegati implementiamo prima della schermata di selezione?

Lavoro manuale propedeutico alla decisione: scansionare i field del layer (nomi tipo filefoto/foto_*/path, valori con estensioni o path esistenti, conteggio match/missing), prototipare la funzione `suggerisci_campi()` riusando la logica dei due script. Risolto quando esiste tabella campo→match-rate su layer di esempio; la decisione su soglie e UI resta al ticket wizard.

## Risoluzione

Fatto: `prototype/05-field-discovery/` — funzione `suggerisci_campi()` + 3 layer di
esempio (12 feature, forme prese dai due script) + misura headless in 2 modalità.
Tabella campo→match-rate: [tabella-match-rate.md](../../prototype/05-field-discovery/tabella-match-rate.md)
(sintesi e verdetti: [README.md](../../prototype/05-field-discovery/README.md)).

Numeri: **7/7 campi foto veri preselezionati, 0 falsi positivi (A+B)** con cartella
base; 6/7 senza (il campo a nomi senza estensione resta C). 4 segnali sui valori
(ext%, esiste%, multi%, scarto guid/num/remoto) + 1 sul nome, 4 livelli A/B/C/D.

Verdetti che passano al wizard: (1) la cartella base va chiesta **prima o insieme**
alla selezione campi, altrimenti la discovery perde il livello A — l'ordine del
ticket 03 non dice dove sta la cartella base; (2) la soglia 0.5 sta in una banda
vuota (veri 80–91%, prosa 0%) ma va riconfermata su GDB cliente; (3) i nulli
arrivano come sentinella `NULL` di QGIS, non `None`; (4) il nome campo suggerisce,
non decide: `link_foto`/`id_foto` hanno il nome giusto e i valori sbagliati.

Non deciso qui (resta al wizard): soglie definitive, testi IT/EN dei livelli,
cosa mostrare quando la cartella base non c'è ancora.
