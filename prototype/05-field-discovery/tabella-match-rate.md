# Ticket 05 — tabella campo → match-rate (auto-discovery campi foto)

Generato da `misura_euristiche.py` su `esempi/discovery_esempi.gpkg` (12 feature per layer, valori costruiti sulle forme reali dei due script).

Legenda livelli: **A** = file trovati nella cartella base (preselezionato) · **B** = valori con estensione, non verificati su disco (preselezionato con avviso) · **C** = solo il nome suggerisce (mostrato, NON preselezionato) · **D** = scartato.

Legenda colonne: `esiste%` = quota di valori non nulli risolti a un file reale · `ext%` = quota con estensione di file · `multi%` = valori con più file · `guid%/num%/remoto%` = quote dei segnali che fanno scartare.

## Senza cartella base (discovery sintattica)

### `Ril_ApFp_contatore`

| campo | tipo | valori | non nulli | esiste | nome | ext% | path% | esiste% | multi% | guid% | num% | remoto% | liv | motivo |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| filefoto | stringa | 12 | 11 | 0 | sì | 91% | 91% | 0% | 0% | 0% | 0% | 0% | **B** | valori con estensione di file, ma non verificati su disco |
| foto_note | stringa | 12 | 12 | 0 | sì | 0% | 0% | 0% | 0% | 0% | 0% | 0% | **C** | solo il nome suggerisce un campo foto |
| codice | stringa | 12 | 12 | 0 | – | 0% | 0% | 0% | 0% | 0% | 0% | 0% | **D** | nessun segnale di nome o di valore |
| data_rilievo | data | 12 | 12 | 0 | – | 0% | 0% | 0% | 0% | 0% | 0% | 0% | **D** | tipo non testuale (data) |
| fid | numerico | 12 | 12 | 0 | – | 0% | 0% | 0% | 0% | 0% | 100% | 0% | **D** | tipo non testuale (numerico) |
| GlobalID | stringa | 12 | 12 | 0 | – | 0% | 0% | 0% | 0% | 100% | 0% | 0% | **D** | valori GUID (probabile GlobalID, da escludere) |
| nome_operatore | stringa | 12 | 12 | 0 | – | 0% | 0% | 0% | 0% | 0% | 0% | 0% | **D** | nessun segnale di nome o di valore |
| note | stringa | 12 | 12 | 0 | – | 0% | 0% | 0% | 0% | 0% | 0% | 0% | **D** | nessun segnale di nome o di valore |
| quota | numerico | 12 | 12 | 0 | – | 0% | 0% | 0% | 0% | 0% | 100% | 0% | **D** | tipo non testuale (numerico) |

Preselezionati (A+B): filefoto  
Da rivedere (C): foto_note

### `Ril_ApFp_superficie`

| campo | tipo | valori | non nulli | esiste | nome | ext% | path% | esiste% | multi% | guid% | num% | remoto% | liv | motivo |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| FOTO_EST | stringa | 12 | 10 | 0 | sì | 100% | 100% | 0% | 0% | 0% | 0% | 0% | **B** | valori con estensione di file, ma non verificati su disco |
| FOTO_INT | stringa | 12 | 10 | 0 | sì | 100% | 100% | 0% | 0% | 0% | 0% | 0% | **B** | valori con estensione di file, ma non verificati su disco |
| foto_impianto | stringa | 12 | 10 | 0 | sì | 0% | 0% | 0% | 0% | 0% | 0% | 0% | **C** | solo il nome suggerisce un campo foto |
| link_foto | stringa | 12 | 12 | 0 | sì | 100% | 0% | 0% | 0% | 0% | 0% | 100% | **D** | URL remoti o percorso non locale |
| data_foto | data | 12 | 12 | 0 | sì | 0% | 0% | 0% | 0% | 0% | 0% | 0% | **D** | tipo non testuale (data) |
| fid | numerico | 12 | 12 | 0 | – | 0% | 0% | 0% | 0% | 0% | 100% | 0% | **D** | tipo non testuale (numerico) |
| foto_archiviata | stringa | 12 | 0 | 0 | sì | 0% | 0% | 0% | 0% | 0% | 0% | 0% | **D** | nessun valore non nullo |
| GLOBALID | stringa | 12 | 12 | 0 | – | 0% | 0% | 0% | 0% | 100% | 0% | 0% | **D** | valori GUID (probabile GlobalID, da escludere) |
| id_foto | stringa | 12 | 12 | 0 | sì | 0% | 0% | 0% | 0% | 0% | 100% | 0% | **D** | valori numerici |

Preselezionati (A+B): FOTO_EST, FOTO_INT  
Da rivedere (C): foto_impianto

### `Ril_ApFp_docs`

| campo | tipo | valori | non nulli | esiste | nome | ext% | path% | esiste% | multi% | guid% | num% | remoto% | liv | motivo |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| doc_allegato | stringa | 12 | 10 | 0 | sì | 100% | 100% | 0% | 0% | 0% | 0% | 0% | **B** | valori con estensione di file, ma non verificati su disco |
| foto_multiple | stringa | 12 | 10 | 0 | sì | 100% | 100% | 0% | 60% | 0% | 0% | 0% | **B** | valori con estensione di file, ma non verificati su disco; 60% valori multipli |
| riferimento_relazione | stringa | 12 | 10 | 0 | – | 100% | 100% | 0% | 0% | 0% | 0% | 0% | **B** | valori con estensione di file, ma non verificati su disco |
| note_doc | stringa | 12 | 12 | 0 | sì | 0% | 0% | 0% | 0% | 0% | 0% | 0% | **C** | solo il nome suggerisce un campo foto |
| data_doc | data | 12 | 12 | 0 | sì | 0% | 0% | 0% | 0% | 0% | 0% | 0% | **D** | tipo non testuale (data) |
| descrizione | stringa | 12 | 12 | 0 | – | 0% | 0% | 0% | 0% | 0% | 0% | 0% | **D** | nessun segnale di nome o di valore |
| fid | numerico | 12 | 12 | 0 | – | 0% | 0% | 0% | 0% | 0% | 100% | 0% | **D** | tipo non testuale (numerico) |
| GLOBALID | stringa | 12 | 12 | 0 | – | 0% | 0% | 0% | 0% | 100% | 0% | 0% | **D** | valori GUID (probabile GlobalID, da escludere) |

Preselezionati (A+B): doc_allegato, foto_multiple, riferimento_relazione  
Da rivedere (C): note_doc

## Con cartella base = esempi/foto

### `Ril_ApFp_contatore`

| campo | tipo | valori | non nulli | esiste | nome | ext% | path% | esiste% | multi% | guid% | num% | remoto% | liv | motivo |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| filefoto | stringa | 12 | 11 | 10 | sì | 100% | 100% | 91% | 0% | 0% | 0% | 0% | **A** | file trovati nella cartella base (10/11) |
| foto_note | stringa | 12 | 12 | 0 | sì | 0% | 0% | 0% | 0% | 0% | 0% | 0% | **C** | solo il nome suggerisce un campo foto |
| codice | stringa | 12 | 12 | 0 | – | 0% | 0% | 0% | 0% | 0% | 0% | 0% | **D** | nessun segnale di nome o di valore |
| data_rilievo | data | 12 | 12 | 0 | – | 0% | 0% | 0% | 0% | 0% | 0% | 0% | **D** | tipo non testuale (data) |
| fid | numerico | 12 | 12 | 0 | – | 0% | 0% | 0% | 0% | 0% | 100% | 0% | **D** | tipo non testuale (numerico) |
| GlobalID | stringa | 12 | 12 | 0 | – | 0% | 0% | 0% | 0% | 100% | 0% | 0% | **D** | valori GUID (probabile GlobalID, da escludere) |
| nome_operatore | stringa | 12 | 12 | 0 | – | 0% | 0% | 0% | 0% | 0% | 0% | 0% | **D** | nessun segnale di nome o di valore |
| note | stringa | 12 | 12 | 0 | – | 0% | 0% | 0% | 0% | 0% | 0% | 0% | **D** | nessun segnale di nome o di valore |
| quota | numerico | 12 | 12 | 0 | – | 0% | 0% | 0% | 0% | 0% | 100% | 0% | **D** | tipo non testuale (numerico) |

Preselezionati (A+B): filefoto  
Da rivedere (C): foto_note

### `Ril_ApFp_superficie`

| campo | tipo | valori | non nulli | esiste | nome | ext% | path% | esiste% | multi% | guid% | num% | remoto% | liv | motivo |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| FOTO_EST | stringa | 12 | 10 | 8 | sì | 100% | 100% | 80% | 0% | 0% | 0% | 0% | **A** | file trovati nella cartella base (8/10) |
| FOTO_INT | stringa | 12 | 10 | 8 | sì | 100% | 100% | 80% | 0% | 0% | 0% | 0% | **A** | file trovati nella cartella base (8/10) |
| foto_impianto | stringa | 12 | 10 | 8 | sì | 0% | 0% | 80% | 0% | 0% | 0% | 0% | **A** | file trovati nella cartella base (8/10) |
| link_foto | stringa | 12 | 12 | 0 | sì | 100% | 0% | 0% | 0% | 0% | 0% | 100% | **D** | URL remoti o percorso non locale |
| data_foto | data | 12 | 12 | 0 | sì | 0% | 0% | 0% | 0% | 0% | 0% | 0% | **D** | tipo non testuale (data) |
| fid | numerico | 12 | 12 | 0 | – | 0% | 0% | 0% | 0% | 0% | 100% | 0% | **D** | tipo non testuale (numerico) |
| foto_archiviata | stringa | 12 | 0 | 0 | sì | 0% | 0% | 0% | 0% | 0% | 0% | 0% | **D** | nessun valore non nullo |
| GLOBALID | stringa | 12 | 12 | 0 | – | 0% | 0% | 0% | 0% | 100% | 0% | 0% | **D** | valori GUID (probabile GlobalID, da escludere) |
| id_foto | stringa | 12 | 12 | 0 | sì | 0% | 0% | 0% | 0% | 0% | 100% | 0% | **D** | valori numerici |

Preselezionati (A+B): FOTO_EST, FOTO_INT, foto_impianto  
Da rivedere (C): —

### `Ril_ApFp_docs`

| campo | tipo | valori | non nulli | esiste | nome | ext% | path% | esiste% | multi% | guid% | num% | remoto% | liv | motivo |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| doc_allegato | stringa | 12 | 10 | 8 | sì | 100% | 100% | 80% | 0% | 0% | 0% | 0% | **A** | file trovati nella cartella base (8/10) |
| foto_multiple | stringa | 12 | 10 | 8 | sì | 100% | 100% | 80% | 60% | 0% | 0% | 0% | **A** | file trovati nella cartella base (8/10); 60% valori multipli |
| riferimento_relazione | stringa | 12 | 10 | 8 | – | 100% | 100% | 80% | 0% | 0% | 0% | 0% | **A** | file trovati nella cartella base (8/10) |
| note_doc | stringa | 12 | 12 | 0 | sì | 0% | 0% | 0% | 0% | 0% | 0% | 0% | **C** | solo il nome suggerisce un campo foto |
| data_doc | data | 12 | 12 | 0 | sì | 0% | 0% | 0% | 0% | 0% | 0% | 0% | **D** | tipo non testuale (data) |
| descrizione | stringa | 12 | 12 | 0 | – | 0% | 0% | 0% | 0% | 0% | 0% | 0% | **D** | nessun segnale di nome o di valore |
| fid | numerico | 12 | 12 | 0 | – | 0% | 0% | 0% | 0% | 0% | 100% | 0% | **D** | tipo non testuale (numerico) |
| GLOBALID | stringa | 12 | 12 | 0 | – | 0% | 0% | 0% | 0% | 100% | 0% | 0% | **D** | valori GUID (probabile GlobalID, da escludere) |

Preselezionati (A+B): doc_allegato, foto_multiple, riferimento_relazione  
Da rivedere (C): note_doc

## Verifica contro la verità attesa

`atteso` = campo che i due script userebbero davvero. `trappola` = campo che NON deve essere preselezionato.

### Senza cartella base (discovery sintattica)

| layer | campo | esito atteso | livello | match-rate (esiste/ext) |
|---|---|---|---|---|
| `Ril_ApFp_contatore` | filefoto | atteso | **B** | 0% / 91% |
| `Ril_ApFp_contatore` | foto_note | trappola (soft ok) | **C** | 0% / 0% |
| `Ril_ApFp_contatore` | codice | trappola | **D** | 0% / 0% |
| `Ril_ApFp_contatore` | data_rilievo | trappola | **D** | 0% / 0% |
| `Ril_ApFp_contatore` | fid | – | **D** | 0% / 0% |
| `Ril_ApFp_contatore` | GlobalID | trappola | **D** | 0% / 0% |
| `Ril_ApFp_contatore` | nome_operatore | trappola | **D** | 0% / 0% |
| `Ril_ApFp_contatore` | note | trappola | **D** | 0% / 0% |
| `Ril_ApFp_contatore` | quota | trappola | **D** | 0% / 0% |
| `Ril_ApFp_superficie` | FOTO_EST | atteso | **B** | 0% / 100% |
| `Ril_ApFp_superficie` | FOTO_INT | atteso | **B** | 0% / 100% |
| `Ril_ApFp_superficie` | foto_impianto | atteso | **C** | 0% / 0% |
| `Ril_ApFp_superficie` | link_foto | trappola | **D** | 0% / 100% |
| `Ril_ApFp_superficie` | data_foto | trappola | **D** | 0% / 0% |
| `Ril_ApFp_superficie` | fid | – | **D** | 0% / 0% |
| `Ril_ApFp_superficie` | foto_archiviata | trappola | **D** | 0% / 0% |
| `Ril_ApFp_superficie` | GLOBALID | trappola | **D** | 0% / 0% |
| `Ril_ApFp_superficie` | id_foto | trappola | **D** | 0% / 0% |
| `Ril_ApFp_docs` | doc_allegato | atteso | **B** | 0% / 100% |
| `Ril_ApFp_docs` | foto_multiple | atteso | **B** | 0% / 100% |
| `Ril_ApFp_docs` | riferimento_relazione | atteso | **B** | 0% / 100% |
| `Ril_ApFp_docs` | note_doc | trappola | **C** | 0% / 0% |
| `Ril_ApFp_docs` | data_doc | trappola | **D** | 0% / 0% |
| `Ril_ApFp_docs` | descrizione | trappola | **D** | 0% / 0% |
| `Ril_ApFp_docs` | fid | – | **D** | 0% / 0% |
| `Ril_ApFp_docs` | GLOBALID | trappola | **D** | 0% / 0% |

- Attesi trovati in A+B: **6/7** · falsi positivi in A+B: **0** · attesi non preselezionati: **1** (di cui alcuni in C) · trappole in C (non preselezionate): **1**

### Con cartella base = esempi/foto

| layer | campo | esito atteso | livello | match-rate (esiste/ext) |
|---|---|---|---|---|
| `Ril_ApFp_contatore` | filefoto | atteso | **A** | 91% / 100% |
| `Ril_ApFp_contatore` | foto_note | trappola (soft ok) | **C** | 0% / 0% |
| `Ril_ApFp_contatore` | codice | trappola | **D** | 0% / 0% |
| `Ril_ApFp_contatore` | data_rilievo | trappola | **D** | 0% / 0% |
| `Ril_ApFp_contatore` | fid | – | **D** | 0% / 0% |
| `Ril_ApFp_contatore` | GlobalID | trappola | **D** | 0% / 0% |
| `Ril_ApFp_contatore` | nome_operatore | trappola | **D** | 0% / 0% |
| `Ril_ApFp_contatore` | note | trappola | **D** | 0% / 0% |
| `Ril_ApFp_contatore` | quota | trappola | **D** | 0% / 0% |
| `Ril_ApFp_superficie` | FOTO_EST | atteso | **A** | 80% / 100% |
| `Ril_ApFp_superficie` | FOTO_INT | atteso | **A** | 80% / 100% |
| `Ril_ApFp_superficie` | foto_impianto | atteso | **A** | 80% / 0% |
| `Ril_ApFp_superficie` | link_foto | trappola | **D** | 0% / 100% |
| `Ril_ApFp_superficie` | data_foto | trappola | **D** | 0% / 0% |
| `Ril_ApFp_superficie` | fid | – | **D** | 0% / 0% |
| `Ril_ApFp_superficie` | foto_archiviata | trappola | **D** | 0% / 0% |
| `Ril_ApFp_superficie` | GLOBALID | trappola | **D** | 0% / 0% |
| `Ril_ApFp_superficie` | id_foto | trappola | **D** | 0% / 0% |
| `Ril_ApFp_docs` | doc_allegato | atteso | **A** | 80% / 100% |
| `Ril_ApFp_docs` | foto_multiple | atteso | **A** | 80% / 100% |
| `Ril_ApFp_docs` | riferimento_relazione | atteso | **A** | 80% / 100% |
| `Ril_ApFp_docs` | note_doc | trappola | **C** | 0% / 0% |
| `Ril_ApFp_docs` | data_doc | trappola | **D** | 0% / 0% |
| `Ril_ApFp_docs` | descrizione | trappola | **D** | 0% / 0% |
| `Ril_ApFp_docs` | fid | – | **D** | 0% / 0% |
| `Ril_ApFp_docs` | GLOBALID | trappola | **D** | 0% / 0% |

- Attesi trovati in A+B: **7/7** · falsi positivi in A+B: **0** · attesi non preselezionati: **0** (di cui alcuni in C) · trappole in C (non preselezionate): **1**
