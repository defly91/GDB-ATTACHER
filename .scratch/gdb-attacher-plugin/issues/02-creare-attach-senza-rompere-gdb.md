Map: [map](../map.md)
Type: research (AFK)
Status: open
Blocked by: none
Labels: wayfinder:research

## Question

Qual è lo schema canonico del layer `<layer>__ATTACH` in un FileGDB e come crearlo da QGIS/PyQGIS/GDAL senza corrompere il GDB?

Indagare sui due script esistenti come primary source: campi usati (REL_GLOBALID, ATT_NAME, DATA, CONTENT_TYPE, GLOBALID generato via uuid), ruolo di GLOBALID/REL_GLOBALID con braces `{...}`, mime-type, deduplica. Poi: esiste una API ufficiale (ArcPy `EnableAttachments`, GDAL, `QgsVectorLayer`) per creare la tabella ATTACH mancante? Cosa succede se la creiamo a mano (indici, GUID, metadata GDB_SYSTEM)? Output: definizione schema minimo sicuro + procedura crea-se-manca + cosa NON fare.
