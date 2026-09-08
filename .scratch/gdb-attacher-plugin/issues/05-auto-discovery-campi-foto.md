Map: [map](../map.md)
Type: task (AFK)
Status: open
Blocked by: 03
Labels: wayfinder:task

## Question

Quale euristica di auto-discovery dei campi foto/allegati implementiamo prima della schermata di selezione?

Lavoro manuale propedeutico alla decisione: scansionare i field del layer (nomi tipo filefoto/foto_*/path, valori con estensioni o path esistenti, conteggio match/missing), prototipare la funzione `suggerisci_campi()` riusando la logica dei due script. Risolto quando esiste tabella campo→match-rate su layer di esempio; la decisione su soglie e UI resta al ticket wizard.
