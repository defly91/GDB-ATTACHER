# GDB-Attacher

Glossario del plugin QGIS che allega foto e file alle feature di un FileGDB Esri. I termini qui fissano la lingua di wizard, codice e documentazione.

## Language

**Layer sorgente**:
Il layer vettoriale del FileGDB le cui feature ricevono gli allegati.
_Avoid_: layer GDB, feature class, layer principale

**Tabella allegati**:
La tabella `<layer>__ATTACH` creata da ArcGIS all'abilitazione degli allegati, che li conserva come righe con BLOB.
_Avoid_: attach layer, layer _ATTACH, tabella ATTACH

**Allegato**:
Una riga della tabella allegati, cioè un singolo file conservato nel GDB e collegato a una feature.
_Avoid_: attachment, record allegato, file allegato

**Campo foto**:
Un campo del layer sorgente i cui valori contengono nomi o percorsi di file da allegare.
_Avoid_: campo file, campo path, campo immagine

**Formula**:
La regola di naming che calcola il nome di un allegato a partire dai campi della feature.
_Avoid_: espressione di naming, pattern, template
