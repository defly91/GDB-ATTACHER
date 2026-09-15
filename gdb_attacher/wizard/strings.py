# -*- coding: utf-8 -*-
"""wizard/strings.py — unico punto in cui vivono le stringhe di interfaccia (IT + EN).

Scelta del ticket 03: l'interfaccia è **bilingue da subito**. Tutte le stringhe
visibili all'utente stanno in questo dizionario, mai sparse nei widget: così
un'eventuale i18n con ``.ts``/``QTranslator`` è un lavoro meccanico su un file solo.

Regole:
- chiavi in ``snake_case`` e in italiano (coerenti col glossario di ``CONTEXT.md``);
- ``STRINGHE[lingua][chiave]``; le due lingue devono avere lo *stesso* insieme di
  chiavi (verificato da ``tests/test_core_stringhe.py``);
- segnaposto con ``str.format`` e ``{nome}``, non con ``%``.
"""

from __future__ import annotations

# ---------------------------------------------------------------- costanti

LINGUA_IT = "it"
LINGUA_EN = "en"
LINGUE = (LINGUA_IT, LINGUA_EN)
LINGUA_DEFAULT = LINGUA_IT

# Chiave usata in QSettings per ricordare la lingua scelta dal menu del plugin.
CHIAVE_IMPOSTAZIONE_LINGUA = "gdb_attacher/lingua"
ORGANIZZAZIONE_IMPOSTAZIONI = "GDB-Attacher"
APPLICAZIONE_IMPOSTAZIONI = "GDB-Attacher"

# Codici dei problemi strutturali prodotti dal core (ticket 03: blocco duro).
# Vivono qui perché il core non traduce: restituisce codici, la UI li rende.
TESTI_PROBLEMA = {
    "non_filegdb": "err_non_filegdb",
    "senza_globalid": "err_senza_globalid",
    "attach_assente": "err_attach_assente",
    "attach_incompleta": "err_attach_incompleta",
    "locale_non_scrivibile": "err_locale_non_scrivibile",
}

# Codici di stato di un allegato (core/report.py) → chiave di traduzione.
TESTI_STATO = {
    "ok": "stato_ok",
    "missing": "stato_missing",
    "collisione": "stato_collisione",
    "vuoto": "stato_vuoto",
    "salta": "stato_salta",
    "errore": "stato_errore",
    "duplicato": "stato_duplicato",
    "chiave_ignota": "stato_chiave_ignota",
    "file_ignoto": "stato_file_ignoto",
    "avviso": "stato_avviso",
}

# ---------------------------------------------------------------- dizionario

STRINGHE = {
    LINGUA_IT: {
        # --- menu / plugin
        "nome_plugin": "GDB-Attacher",
        "menu_root": "&GDB-Attacher",
        "azione_wizard": "Allega foto e file…",
        "azione_wizard_desc": "Wizard: allega foto e file alle feature di un FileGDB",
        "azione_lingua": "Lingua / Language",
        "azione_info": "Informazioni su GDB-Attacher…",
        "info_titolo": "GDB-Attacher 0.1.0",
        "titolo_wizard": "GDB-Attacher — allega foto e file al FileGDB",
        # --- pulsanti / generale
        "avanti": "Avanti",
        "indietro": "Indietro",
        "annulla": "Annulla",
        "fine": "Fine",
        "sfoglia": "Sfoglia…",
        "aggiorna": "Aggiorna",
        "nessuno": "—",
        "sì": "Sì",
        # Sottostringa che evidenzia in rosso una cella di tabella (`_riempi`).
        # Sta qui perché è testo che l'utente legge: in inglese non può essere
        # «mancante», o l'evidenziazione sparirebbe.
        "marcatore_errore": "mancante",
        "errore_titolo": "Errore",
        "attenzione_titolo": "Attenzione",
        # --- pagine
        "pagina_layer": "1. Layer sorgente",
        "pagina_verifica": "2. Verifica",
        "pagina_discovery": "3. Campi foto",
        "pagina_campi": "4. Scelta campi",
        "pagina_naming": "5. Nome allegato",
        "pagina_esegui": "6. Esegui",
        "pagina_stile": "7. Stile",
        # --- pagina layer
        "label_layer": "Layer sorgente (solo layer su FileGDB già caricati nel progetto):",
        "nessun_layer_filegdb": "Nessun layer vettoriale su FileGDB è caricato nel progetto. "
                                "Aggiungi prima il .gdb con «Layer → Aggiungi layer vettoriale».",
        "origine_layer": "Origine: {origine}",
        "nota_solo_filegdb": "Se il layer non è su FileGDB il wizard si blocca al passo successivo: "
                             "in v1 non si apre un .gdb a mano.",
        # --- pagina verifica
        "titolo_verifica": "Controlli bloccanti prima di scrivere qualcosa",
        "verifica_esegui": "Esegui le verifiche",
        "verifica_ok": "Tutto pronto: il layer sorgente e la tabella allegati sono a posto.",
        "verifica_bloccata": "Verifiche non superate: il wizard non può proseguire.",
        "col_controllo": "Controllo",
        "col_esito": "Esito",
        "col_dettaglio": "Dettaglio",
        "esito_ok": "OK",
        "esito_ko": "BLOCCA",
        "ctrl_filegdb": "Il layer sorgente è un FileGDB Esri",
        "ctrl_globalid": "Il layer sorgente ha il campo GlobalID",
        "ctrl_attach": "La tabella allegati esiste nel progetto",
        "ctrl_campi_attach": "La tabella allegati ha i 6 campi richiesti",
        "ctrl_scrittura": "Il layer sorgente dichiara di essere scrivibile",
        "msg_arcgis_pro": "Apri il GDB in ArcGIS Pro ed esegui\n\n"
                          "    arcpy.management.EnableAttachments('{layer}')\n\n"
                          "poi ricarica il .gdb in QGIS e riapri questo wizard.\n"
                          "Il comando è idempotente: se gli allegati sono già abilitati non fa nulla.\n\n"
                          "Il plugin non crea la tabella allegati a mano: una tabella creata con GDAL "
                          "sarebbe fantasma per ArcGIS (mancano la relationship class __ATTACHREL e i "
                          "metadati GDB_Items).",
        "err_non_filegdb": "Il layer «{layer}» non è su FileGDB (origine: {origine}). "
                           "Scegli un layer di un .gdb già abilitato agli allegati.",
        "err_senza_globalid": "Il layer «{layer}» non ha il campo GlobalID: senza GLOBALID non si può "
                              "collegare un allegato alla feature. Attiva «GlobalID abilitato» su "
                              "ArcGIS Pro e ricarica il layer.",
        "err_attach_assente": "La tabella allegati «{tabella}» non è caricata nel progetto.\n\n{come}",
        "err_attach_incompleta": "La tabella allegati «{tabella}» è incompleta: mancano i campi {campi}.\n\n"
                                 "Non si ripara a mano: {come}",
        "err_locale_non_scrivibile": "Il layer sorgente non dichiara la capacità di scrittura: "
                                     "verifica i permessi del .gdb o se un altro processo lo sta già scrivendo.",
        "come_abilitare": "come abilitare gli allegati",
        # --- pagina discovery
        "testo_discovery": "Il plugin legge un campione di valori per ogni campo e propone i campi che "
                           "contengono nomi o percorsi di file. La cartella base è il segnale più forte: "
                           "con la cartella base i nomi senza estensione diventano livello A.",
        "label_cartella_base": "Cartella base dei file:",
        "cartella_base_vuota": "(nessuna cartella base: discovery solo sintattica, niente livello A)",
        "scansiona": "Analizza i campi",
        "scansione_in_corso": "Analisi dei campi in corso…",
        "col_livello": "Liv.",
        "col_campo": "Campo",
        "col_tipo": "Tipo",
        "col_valori": "Non nulli",
        "col_esiste": "Su disco",
        "col_multi": "Multi",
        "col_nome": "Nome",
        "col_motivo": "Motivo",
        "col_esempi": "Esempi",
        "livello_a": "A — file trovati nella cartella base",
        "livello_b": "B — estensione di file, non verificati su disco",
        "livello_c": "C — solo il nome suggerisce (da rivedere a mano)",
        "livello_d": "D — nessun segnale (nascosto)",
        "legenda_livelli": "A e B vengono preselezionati; C resta da rivedere; D è nascosto.",
        "avviso_livello_b": "Livello B: i valori hanno un'estensione di file ma non sono stati trovati "
                            "sulla cartella base. Controlla la cartella prima di eseguire.",
        "nessun_campo_trovato": "Nessun campo candidato: scegli a mano i campi al passo successivo.",
        "cartella_base_non_valida": "La cartella «{cartella}» non esiste o non è leggibile.",
        "errore_scansione": "Errore imprevisto durante l'analisi dei campi: {errore}",
        # --- pagina campi
        "testo_campi": "Spunta i campi del layer sorgente che contengono il file da allegare. "
                       "Più campi spuntati = un allegato per campo (3 campi = 3 righe nella tabella allegati).",
        "col_scelto": "Usa",
        "preselezionati": "Preselezionati dalla discovery",
        "da_rivedere": "Da rivedere (livello C)",
        "altri_campi": "Altri campi (livello D, di solito non sensati)",
        "nessun_campo_scelto": "Spunta almeno un campo foto per proseguire.",
        "riepilogo_campi": "Campi scelti: {n} — cartella base: {cartella}",
        "nota_cartella_prima": "La cartella base è stata chiesta al passo precedente proprio perché "
                               "serve alla discovery: cambiarla qui non rifà l'analisi.",
        # --- pagina naming
        "titolo_naming": "Nome allegato",
        "testo_naming": "Il file da allegare è sempre risolto dal campo foto + cartella base. "
                        "Qui si decide solo il nome con cui il file viene riconosciuto dentro il GDB.",
        "modo_originale": "Nome originale (predefinito)",
        "modo_formula": "Formula QGIS (una per feature)",
        "modo_csv": "Elenco file da CSV (join su chiave)",
        "desc_originale": "ATT_NAME = nome reale del file risolto, estensione inclusa, senza modifiche.",
        "desc_formula": "ATT_NAME = risultato di un'espressione QGIS valutata per ogni feature.",
        "desc_csv": "Ogni riga del CSV è un allegato: il file viene dal CSV, il nome dal CSV o dal file. "
                    "In questa modalità i campi foto scelti non servono.",
        "aiuto_formula": "Variabili disponibili: @original_name (nome file risolto), @stem (senza estensione), "
                         "@ext (con il punto), @index (indice del token multi-valore, da 1) e tutti i campi "
                         "del layer.\n"
                         "ATTENZIONE: in QGIS i doppi apici \"campo\" indicano un CAMPO, gli apici singoli "
                         "'testo' indicano una STRINGA.\n"
                         "Esempio: @stem || '_' || \"CODICE\" || @ext",
        "formula_manca": "Scrivi una formula per proseguire.",
        "formula_non_valida": "Formula non valida: {errore}",
        "formula_non_valida_titolo": "Formula non valida",
        "formula_prova": "Prova",
        "formula_esempio": "@stem || \"_\" || \"CODICE\" || @ext",
        "csv_file": "File CSV:",
        "filtro_csv": "CSV (*.csv *.txt)",
        "filtro_csv_export": "CSV (*.csv)",
        "filtro_tutti_i_file": "Tutti i file (*)",
        "csv_chiave": "Colonna chiave da incrociare col layer:",
        "csv_col_file": "Colonna del file:",
        "csv_col_attname": "Colonna del nome allegato (facoltativa):",
        "csv_separatore": "Separatore: {separatore} (rilevato)",
        "csv_encoding": "Codifica: {encoding}",
        "csv_blocco_illegibile": "CSV illeggibile: {errore}",
        "csv_blocco_chiave": "Nel CSV non c'è la colonna chiave «{colonna}».",
        "csv_non_scelto": "Nessun CSV valido: scegli un file CSV leggibile.",
        "csv_avviso_chiave_mancante": "Il CSV non ha la colonna «{colonna}» indicata: controllo saltato.",
        "csv_avviso_chiavi_ignote": "{n} chiavi del CSV non esistono nel layer: verranno saltate.",
        "csv_avviso_chiavi_duplicate": "{n} chiavi del CSV sono ripetute (più allegati sulla stessa feature).",
        "csv_righe": "{n} righe valide nel CSV.",
        "anteprima_5": "5 feature di esempio: valore del campo → file risolto → nome allegato",
        "col_valore_campo": "Valore campo",
        "col_percorso": "File risolto",
        "col_nome_finale": "Nome allegato",
        "col_stato": "Stato",
        "conteggi_per_campo": "Conteggio per campo foto:",
        "totale_ok": "Da aggiungere: {n}",
        "totale_missing": "File mancanti: {n}",
        "totale_collisioni": "Nomi in collisione (rinominati con _2, _3…): {n}",
        "totale_saltati": "Righe saltate (valore o nome vuoto): {n}",
        "stato_ok": "ok",
        "stato_missing": "file mancante",
        "stato_collisione": "rinominato",
        "stato_vuoto": "valore vuoto",
        "stato_salta": "nome vuoto, saltato",
        "stato_errore": "errore",
        "stato_duplicato": "già presente",
        "stato_chiave_ignota": "chiave non nel layer",
        "stato_file_ignoto": "file non risolto",
        # --- pagina esegui
        "riepilogo_esecuzione": "Sto per scrivere {ok} allegati nella tabella «{tabella}», "
                                "in una sola transazione.",
        "backup_titolo": "Backup del .gdb prima di scrivere",
        "backup_desc": "Copia l'intero .gdb accanto all'originale. Puoi procedere senza backup: "
                       "la scelta è tua e il rischio è tuo.",
        "backup_attivo": "Fai il backup e prosegui",
        "backup_senza": "Continua senza backup",
        "backup_cartella": "Cartella destinazione del backup:",
        "backup_fatto": "Backup creato: {percorso}",
        "backup_errore": "Backup non riuscito: {errore}",
        "conferma_esecuzione": "Confermi la scrittura sul geodatabase?",
        "esegui": "Esegui",
        "esecuzione_in_corso": "Scrittura in corso…",
        "atto_totale_duplicati": "Già presenti (saltati): {n}",
        "nota_dedup": "Prima di scrivere si controlla la coppia (REL_GLOBALID, ATT_NAME): "
                      "un allegato già presente non viene riscritto.",
        "nota_galleria": "Galleria: più campi foto spuntati o valori multipli nello stesso campo "
                         "producono più righe di allegato per la stessa feature, in un solo giro.",
        "info_testo": "Wizard per allegare foto e file alle feature di un FileGDB Esri.\n\n"
                      "• verifica bloccante di FileGDB, GlobalID e tabella allegati (il plugin non la crea mai)\n"
                      "• discovery automatica dei campi foto, cartella base, anteprima con conteggi\n"
                      "• nome allegato: originale, formula QGIS per-feature o elenco file da CSV\n"
                      "• deduplica su (REL_GLOBALID, ATT_NAME), batch in una transazione con backup opzionale\n"
                      "• report finale esportabile in CSV, stile «variante A» applicato dopo la scrittura\n\n"
                      "Fuori perimetro in v1: QField (nessuna sincronizzazione sul campo, né raccolta offline).\n\n"
                      "GPLv2+ · https://github.com/defly91/GDB-ATTACHER",
        "esecuzione_annulla": "Annulla la scrittura",
        "esecuzione_annullata": "Scrittura annullata: la transazione è stata annullata, "
                                "il geodatabase è rimasto com'era.",
        "applica_stile_checkbox": "Applica lo stile «variante A» alla tabella allegati",
        "stile_salta": "Non applicare lo stile (potrai applicarlo dopo con «Carica stile»).",

        "esito_scrittura": "Scrittura conclusa: {aggiunti} aggiunti, {duplicati} già presenti, "
                           "{mancanti} file non trovati, {saltati} saltati, {errori} errori.",
        "esito_commit_fallito": "Commit non riuscito: nulla è stato scritto nel geodatabase.\n"
                                "Dettaglio: {errore}",
        "errore_esecuzione": "Errore imprevisto durante la scrittura: {errore}\n\n"
                             "Il wizard è ancora aperto: correggi e riprova.",
        "errore_export": "Report non salvato: {errore}",
        "annulla_zero_scritto": "Annullato prima di scrivere: nessuna modifica al geodatabase.",
        # --- pagina stile
        "testo_stile": "Alla fine viene applicato alla tabella allegati lo stile «variante A»: anteprima "
                       "della foto nel form, mapTip con miniatura, azioni Apri e Salva con nome. "
                       "Lo stile esistente viene sovrascritto.",
        "applica_stile": "Applica lo stile alla tabella allegati",
        "stile_applicato": "Stile applicato: {messaggio}",
        "stile_errore": "Stile non applicato: {errore}",
        "stile_saltato": "Stile non applicato (tabella allegati non disponibile).",
        "stile_qml_non_trovato": "QML non trovato nel plugin: {percorso}",
        # --- report
        "titolo_report": "Report",
        "export_missing": "Esporta i mancanti/gli errori in CSV…",
        "export_tutto": "Esporta tutto il report in CSV…",
        "report_salvato": "Report salvato: {percorso}",
        "report_vuoto": "Nessuna riga da esportare.",
        "report_apri_cartella": "I percorsi sono quelli risolti con la cartella base.",
        "col_tipo_riga": "Tipo",
        "col_feature": "Feature (GLOBALID)",
        "col_campo_foto": "Campo foto",
        "nomi_esistenti_titolo": "Se l'allegato è già nella tabella",
        "opzione_salta_duplicati": "Salta (già presente) — batch ripetibile",
        "opzione_rinomina_duplicati": "Rinomina con _2, _3… (nuovo allegato)",
        "nota_duplicati": "La coppia (REL_GLOBALID, ATT_NAME) viene confrontata con la tabella allegati: "
                          "saltare rende il batch ripetibile senza duplicare nulla.",
        "aggiorna_anteprima": "Aggiorna l'anteprima",
        "stato_avviso": "avviso",
        "esito_avvisi": "Avvisi: {n}",
        "col_valore": "Valore",
        "col_percorso_file": "Percorso file",
        "col_nome_allegato": "Nome allegato",
        "col_motivo": "Motivo",
    },
    LINGUA_EN: {
        # --- menu / plugin
        "nome_plugin": "GDB-Attacher",
        "menu_root": "&GDB-Attacher",
        "azione_wizard": "Attach photos and files…",
        "azione_wizard_desc": "Wizard: attach photos and files to Esri FileGDB features",
        "azione_lingua": "Lingua / Language",
        "azione_info": "About GDB-Attacher…",
        "info_titolo": "GDB-Attacher 0.1.0",
        "titolo_wizard": "GDB-Attacher — attach photos and files to the FileGDB",
        # --- buttons / general
        "avanti": "Next",
        "indietro": "Back",
        "annulla": "Cancel",
        "fine": "Finish",
        "sfoglia": "Browse…",
        "aggiorna": "Refresh",
        "nessuno": "—",
        "sì": "Yes",
        # Vedi la nota in italiano: è il marcatore evidenziato da `_riempi`.
        "marcatore_errore": "missing",
        "errore_titolo": "Error",
        "attenzione_titolo": "Warning",
        # --- pages
        "pagina_layer": "1. Source layer",
        "pagina_verifica": "2. Checks",
        "pagina_discovery": "3. Photo fields",
        "pagina_campi": "4. Field selection",
        "pagina_naming": "5. Attachment name",
        "pagina_esegui": "6. Run",
        "pagina_stile": "7. Style",
        # --- layer page
        "label_layer": "Source layer (only FileGDB layers already loaded in the project):",
        "nessun_layer_filegdb": "No FileGDB vector layer is loaded in the project. "
                                "Add the .gdb first with “Layer → Add Vector Layer”.",
        "origine_layer": "Source: {origine}",
        "nota_solo_filegdb": "If the layer is not on a FileGDB the wizard stops at the next step: "
                             "v1 never opens a .gdb by hand.",
        # --- checks page
        "titolo_verifica": "Blocking checks before anything is written",
        "verifica_esegui": "Run the checks",
        "verifica_ok": "All good: the source layer and the attachment table are fine.",
        "verifica_bloccata": "Checks failed: the wizard cannot continue.",
        "col_controllo": "Check",
        "col_esito": "Result",
        "col_dettaglio": "Detail",
        "esito_ok": "OK",
        "esito_ko": "BLOCKED",
        "ctrl_filegdb": "The source layer is an Esri FileGDB",
        "ctrl_globalid": "The source layer has a GlobalID field",
        "ctrl_attach": "The attachment table is loaded in the project",
        "ctrl_campi_attach": "The attachment table has the 6 required fields",
        "ctrl_scrittura": "The source layer reports itself as writable",
        "msg_arcgis_pro": "Open the GDB in ArcGIS Pro and run\n\n"
                          "    arcpy.management.EnableAttachments('{layer}')\n\n"
                          "then reload the .gdb in QGIS and reopen this wizard.\n"
                          "The command is idempotent: if attachments are already enabled it does nothing.\n\n"
                          "The plugin never creates the attachment table by hand: a table created with "
                          "GDAL would be a ghost for ArcGIS (no __ATTACHREL relationship class, no "
                          "GDB_Items metadata).",
        "err_non_filegdb": "Layer “{layer}” is not on a FileGDB (source: {origine}). "
                           "Pick a layer from a .gdb with attachments already enabled.",
        "err_senza_globalid": "Layer “{layer}” has no GlobalID field: without GLOBALID an attachment cannot "
                              "be linked to its feature. Enable “GlobalID” in ArcGIS Pro and reload the layer.",
        "err_attach_assente": "Attachment table “{tabella}” is not loaded in the project.\n\n{come}",
        "err_attach_incompleta": "Attachment table “{tabella}” is incomplete: missing fields {campi}.\n\n"
                                 "It is not fixed by hand: {come}",
        "err_locale_non_scrivibile": "The source layer does not report write capability: check the .gdb "
                                     "permissions or whether another process is already writing to it.",
        "come_abilitare": "how to enable attachments",
        # --- discovery page
        "testo_discovery": "The plugin samples each field's values and suggests the fields that contain file "
                           "names or paths. The base folder is the strongest signal: with it, names without "
                           "extension become level A.",
        "label_cartella_base": "Base folder of the files:",
        "cartella_base_vuota": "(no base folder: syntax-only discovery, no level A)",
        "scansiona": "Scan the fields",
        "scansione_in_corso": "Scanning the fields…",
        "col_livello": "Lvl",
        "col_campo": "Field",
        "col_tipo": "Type",
        "col_valori": "Not null",
        "col_esiste": "On disk",
        "col_multi": "Multi",
        "col_nome": "Name",
        "col_motivo": "Reason",
        "col_esempi": "Examples",
        "livello_a": "A — files found in the base folder",
        "livello_b": "B — file extension, not verified on disk",
        "livello_c": "C — only the name suggests it (review by hand)",
        "livello_d": "D — no signal (hidden)",
        "legenda_livelli": "A and B are pre-checked; C needs a look; D is hidden.",
        "avviso_livello_b": "Level B: values carry a file extension but were not found in the base folder. "
                            "Check the folder before running.",
        "nessun_campo_trovato": "No candidate field: choose the fields by hand in the next step.",
        "cartella_base_non_valida": "Folder “{cartella}” does not exist or is not readable.",
        "errore_scansione": "Unexpected error while scanning the fields: {errore}",
        # --- field selection page
        "testo_campi": "Tick the source-layer fields that hold the file to attach. "
                       "More fields = one attachment per field (3 fields = 3 rows in the attachment table).",
        "col_scelto": "Use",
        "preselezionati": "Pre-checked by discovery",
        "da_rivedere": "To review (level C)",
        "altri_campi": "Other fields (level D, usually meaningless)",
        "nessun_campo_scelto": "Tick at least one photo field to continue.",
        "riepilogo_campi": "Chosen fields: {n} — base folder: {cartella}",
        "nota_cartella_prima": "The base folder was asked in the previous step precisely because discovery "
                               "needs it: changing it here does not re-run the scan.",
        # --- naming page
        "titolo_naming": "Attachment name",
        "testo_naming": "The file to attach is always resolved from the photo field + base folder. "
                        "Here you only decide the name the file gets inside the GDB.",
        "modo_originale": "Original name (default)",
        "modo_formula": "QGIS formula (per feature)",
        "modo_csv": "File list from CSV (keyed join)",
        "desc_originale": "ATT_NAME = real name of the resolved file, extension included, untouched.",
        "desc_formula": "ATT_NAME = result of a QGIS expression evaluated for every feature.",
        "desc_csv": "Every CSV row is an attachment: the file comes from the CSV, the name from the CSV or "
                    "from the file. In this mode the chosen photo fields are not used.",
        "aiuto_formula": "Available variables: @original_name (resolved file name), @stem (without extension), "
                         "@ext (with the dot), @index (multi-value token index, from 1) and every layer field.\n"
                         "WARNING: in QGIS double quotes \"field\" mean a FIELD, single quotes 'text' mean a "
                         "STRING.\n"
                         "Example: @stem || '_' || \"CODE\" || @ext",
        "formula_manca": "Write a formula to continue.",
        "formula_non_valida": "Invalid formula: {errore}",
        "formula_non_valida_titolo": "Invalid formula",
        "formula_prova": "Test",
        "formula_esempio": "@stem || \"_\" || \"CODE\" || @ext",
        "csv_file": "CSV file:",
        "filtro_csv": "CSV (*.csv *.txt)",
        "filtro_csv_export": "CSV (*.csv)",
        "filtro_tutti_i_file": "All files (*)",
        "csv_chiave": "Key column to join with the layer:",
        "csv_col_file": "File column:",
        "csv_col_attname": "Attachment name column (optional):",
        "csv_separatore": "Delimiter: {separatore} (detected)",
        "csv_encoding": "Encoding: {encoding}",
        "csv_blocco_illegibile": "Unreadable CSV: {errore}",
        "csv_blocco_chiave": "The CSV has no key column “{colonna}”.",
        "csv_non_scelto": "No valid CSV: choose a readable CSV file.",
        "csv_avviso_chiave_mancante": "The CSV has no column “{colonna}”: check skipped.",
        "csv_avviso_chiavi_ignote": "{n} CSV keys do not exist in the layer: they will be skipped.",
        "csv_avviso_chiavi_duplicate": "{n} CSV keys are repeated (several attachments on the same feature).",
        "csv_righe": "{n} valid rows in the CSV.",
        "anteprima_5": "5 sample features: field value → resolved file → attachment name",
        "col_valore_campo": "Field value",
        "col_percorso": "Resolved file",
        "col_nome_finale": "Attachment name",
        "col_stato": "State",
        "conteggi_per_campo": "Count per photo field:",
        "totale_ok": "To add: {n}",
        "totale_missing": "Missing files: {n}",
        "totale_collisioni": "Name collisions (renamed with _2, _3…): {n}",
        "totale_saltati": "Skipped rows (empty value or name): {n}",
        "stato_ok": "ok",
        "stato_missing": "missing file",
        "stato_collisione": "renamed",
        "stato_vuoto": "empty value",
        "stato_salta": "empty name, skipped",
        "stato_errore": "error",
        "stato_duplicato": "already there",
        "stato_chiave_ignota": "key not in layer",
        "stato_file_ignoto": "file not resolved",
        # --- run page
        "riepilogo_esecuzione": "About to write {ok} attachments into table “{tabella}”, "
                                "in a single transaction.",
        "backup_titolo": "Back up the .gdb before writing",
        "backup_desc": "Copies the whole .gdb next to the original. You may proceed without a backup: "
                       "the choice and the risk are yours.",
        "backup_attivo": "Back up and continue",
        "backup_senza": "Continue without backup",
        "backup_cartella": "Backup destination folder:",
        "backup_fatto": "Backup created: {percorso}",
        "backup_errore": "Backup failed: {errore}",
        "conferma_esecuzione": "Confirm the write on the geodatabase?",
        "esegui": "Run",
        "esecuzione_in_corso": "Writing…",
        "atto_totale_duplicati": "Already there (skipped): {n}",
        "nota_dedup": "Before writing, the (REL_GLOBALID, ATT_NAME) pair is checked: an attachment already "
                      "present is not written again.",
        "nota_galleria": "Gallery: more ticked photo fields or multi-value fields produce several attachment "
                         "rows for the same feature, in one single pass.",
        "info_testo": "Wizard to attach photos and files to Esri FileGDB features.\n\n"
                      "• blocking checks on FileGDB, GlobalID and the attachment table (the plugin never creates it)\n"
                      "• automatic photo-field discovery, base folder, preview with counts\n"
                      "• attachment name: original, per-feature QGIS formula or file list from CSV\n"
                      "• dedup on (REL_GLOBALID, ATT_NAME), batch in a single transaction with optional backup\n"
                      "• final report exportable to CSV, “variant A” style applied after the write\n\n"
                      "Out of scope in v1: QField (no field sync, no offline collection).\n\n"
                      "GPLv2+ · https://github.com/defly91/GDB-ATTACHER",
        "esecuzione_annulla": "Cancel the write",
        "esecuzione_annullata": "Write cancelled: the transaction was rolled back, "
                                "the geodatabase is unchanged.",
        "applica_stile_checkbox": "Apply the “variant A” style to the attachment table",
        "stile_salta": "Do not apply the style (you can load it later with “Load style”).",
        "esito_scrittura": "Write finished: {aggiunti} added, {duplicati} already there, "
                           "{mancanti} missing files, {saltati} skipped, {errori} errors.",
        "esito_commit_fallito": "Commit failed: nothing was written to the geodatabase.\n"
                                "Detail: {errore}",
        "errore_esecuzione": "Unexpected error while writing: {errore}\n\n"
                             "The wizard is still open: fix it and try again.",
        "errore_export": "Report not saved: {errore}",
        "annulla_zero_scritto": "Cancelled before writing: no change to the geodatabase.",
        # --- style page
        "testo_stile": "At the end the “variant A” style is applied to the attachment table: photo preview in "
                       "the form, thumbnail mapTip, Open and Save-as actions. Any existing style is overwritten.",
        "applica_stile": "Apply the style to the attachment table",
        "stile_applicato": "Style applied: {messaggio}",
        "stile_errore": "Style not applied: {errore}",
        "stile_saltato": "Style not applied (attachment table not available).",
        "stile_qml_non_trovato": "QML not found in the plugin: {percorso}",
        # --- report
        "titolo_report": "Report",
        "export_missing": "Export missing/errors to CSV…",
        "export_tutto": "Export the whole report to CSV…",
        "report_salvato": "Report saved: {percorso}",
        "report_vuoto": "No rows to export.",
        "report_apri_cartella": "Paths are the ones resolved with the base folder.",
        "col_tipo_riga": "Type",
        "col_feature": "Feature (GLOBALID)",
        "col_campo_foto": "Photo field",
        "nomi_esistenti_titolo": "When the attachment is already in the table",
        "opzione_salta_duplicati": "Skip (already there) — repeatable batch",
        "opzione_rinomina_duplicati": "Rename with _2, _3… (new attachment)",
        "nota_duplicati": "The (REL_GLOBALID, ATT_NAME) pair is checked against the attachment table: "
                          "skipping makes the batch repeatable without duplicating anything.",
        "aggiorna_anteprima": "Refresh the preview",
        "stato_avviso": "warning",
        "esito_avvisi": "Warnings: {n}",
        "col_valore": "Value",
        "col_percorso_file": "File path",
        "col_nome_allegato": "Attachment name",
        "col_motivo": "Reason",
    },
}


# ---------------------------------------------------------------- API


def lingue_disponibili() -> tuple:
    """Le lingue supportate, nell'ordine in cui mostrarle nel menu."""
    return LINGUE


def _da_impostazioni() -> str:
    """Legge la lingua scelta dal menu (QSettings). Fuori da QGIS non fallisce."""
    try:
        from qgis.PyQt.QtCore import QSettings

        valore = QSettings(ORGANIZZAZIONE_IMPOSTAZIONI, APPLICAZIONE_IMPOSTAZIONI).value(
            CHIAVE_IMPOSTAZIONE_LINGUA, LINGUA_DEFAULT
        )
    except Exception:
        return LINGUA_DEFAULT
    valore = str(valore or LINGUA_DEFAULT).lower()
    return valore if valore in LINGUE else LINGUA_DEFAULT


def lingua_corrente() -> str:
    """Lingua attiva.

    Ordine di priorità (la scelta esplicita dell'utente vince sempre):
    1. lingua scelta dal menu del plugin (``QSettings``);
    2. lingua di QGIS (``locale/userLocale``), **predefinita italiano**;
    3. variabili d'ambiente ``LANG``/``LC_ALL``;
    4. italiano.
    """
    import os

    try:
        from qgis.PyQt.QtCore import QSettings
        impostazione = QSettings(ORGANIZZAZIONE_IMPOSTAZIONI, APPLICAZIONE_IMPOSTAZIONI)
        if impostazione.contains(CHIAVE_IMPOSTAZIONE_LINGUA):
            return str(impostazione.value(CHIAVE_IMPOSTAZIONE_LINGUA)).lower()
    except Exception:
        pass

    # Lingua di QGIS (es. "it_IT", "en_US"): vale solo se la conosciamo.
    try:
        from qgis.core import QgsSettings

        locale_qgis = str(QgsSettings().value("locale/userLocale") or "").lower()
        if len(locale_qgis) >= 2 and locale_qgis[:2] in LINGUE:
            return locale_qgis[:2]
    except Exception:
        pass

    ambiente = (os.environ.get("LANG") or os.environ.get("LC_ALL") or "").lower()
    if ambiente.startswith("en"):
        return LINGUA_EN
    return LINGUA_DEFAULT


def imposta_lingua(lingua: str) -> str:
    """Salva la lingua scelta dal menu. Ritorna la lingua effettivamente salvata."""
    lingua = str(lingua or "").lower()
    if lingua not in LINGUE:
        lingua = LINGUA_DEFAULT
    try:
        from qgis.PyQt.QtCore import QSettings

        impostazione = QSettings(ORGANIZZAZIONE_IMPOSTAZIONI, APPLICAZIONE_IMPOSTAZIONI)
        impostazione.setValue(CHIAVE_IMPOSTAZIONE_LINGUA, lingua)
    except Exception:
        pass
    return lingua


def tr(chiave: str, lingua: str = None, **valori) -> str:
    """Ritorna la stringa tradotta, con i segnaposto sostituiti.

    Una chiave mancante non fa mai crashare l'interfaccia: si ricade sull'italiano
    e, in ultima istanza, sulla chiave stessa (così il difetto si vede subito).
    """
    lingua = (lingua or lingua_corrente()).lower()
    if lingua not in LINGUE:
        lingua = LINGUA_DEFAULT
    testo = STRINGHE.get(lingua, {}).get(chiave)
    if testo is None:
        testo = STRINGHE[LINGUA_DEFAULT].get(chiave, chiave)
    if valori:
        try:
            return testo.format(**valori)
        except (KeyError, IndexError):
            return testo
    return testo


def chiavi_mancanti(lingua: str) -> list:
    """Chiavi presenti in IT e assenti nell'altra lingua (usata dai test)."""
    riferimento = set(STRINGHE[LINGUA_IT])
    return sorted(riferimento.symmetric_difference(set(STRINGHE[lingua])))
