# Ticket 04 — prototipo stile tabella allegati (throwaway)

> Domanda: quale stile diamo alla tabella allegati per vedere le foto come HTML
> e aprire gli altri formati? Tre varianti QML su GDB di test — reagisci e scegli.

## Contenuto

| File | Cos'è |
|---|---|
| `variante_A_anteprima.qml` | A — Anteprima in testa (2 tab, dossier HTML grande) |
| `variante_B_essenziale.qml` | B — Essenziale da tabella (gruppo unico, niente HTML nel form) |
| `variante_C_blindata.qml` | C — Scheda blindata (3 tab, vincoli, pulsante Apri nel form) |
| `test_attach.gdb/` | GDB di test: `fotorilievo_test` (2 feature) + `fotorilievo_test__ATTACH` (4 allegati: JPG, PNG, PDF, TIFF) |
| `anteprima_demo.html` | Dossier HTML statico (doppio click, niente QGIS) — come appare il riquadro foto |
| `applica_stile.py` | 2 righe in console QGIS: carica test + applica variante + apre il form |
| `genera_prototipo.py` | Generatore (PyQGIS): rigenera QML + GDB + demo; include la validazione headless |

## Come provare (3 minuti)

1. Apri QGIS, poi console Python (`Ctrl+Alt+P`).
2. Incolla (adatta il percorso se serve):
   `exec(open(r'C:/Users/Stefano/Documents/Prove Claude/GDB-ATTACHER/prototype/04-attach-style/applica_stile.py', encoding='utf-8').read())`
3. `applica('A')` — poi `applica('B')`, `applica('C')`. Il form si apre da solo;
   prova anche hover col mouse (mapTip con miniatura) e le azioni
   (click destro riga → Azioni → *Apri allegato* / *Salva allegato con nome…*).

## Le 3 varianti a confronto

| | A — Anteprima in testa | B — Essenziale da tabella | C — Scheda blindata |
|---|---|---|---|
| Form | 2 tab: *Anteprima* (HTML + nome/tipo/dimensione) + *Dati tecnici* (GUID, blob visibile) | 1 gruppo *Allegato* + gruppo collassato *Tecnici*; **niente HTML nel form** | 3 tab: *Foto* (HTML + nome + tipo + **pulsante Apri**) / *File* (dimensione + nota) / *Collegamento* (GUID) |
| Anteprima foto | HTML inline nel form + mapTip | **solo mapTip** (hover) — form leggerissimo | HTML inline nel form + mapTip |
| Altri formati (PDF/TIFF/MP4) | testo fallback + azione *Apri allegato* | azione *Apri allegato* (default, doppio click) | testo fallback + pulsante nel form + azione |
| Blob `DATA` | widget Binary visibile (si vede, non si tocca: GUID/dimensione in sola lettura) | widget Hidden (sparito) | Hidden + nota esplicativa + `ATT_NAME` obbligatorio |
| Azioni | Apri (default) + Salva con nome | Apri (default) + Salva con nome | Apri (default, anche pulsante) + Salva con nome |
| Pensata per | operatore che sfoglia foto una a una | controllo massivo righe in tabella attributi | uso condiviso / mani inesperte |

Comune a tutte: alias in italiano, `CONTENT_TYPE` con menu (ValueMap, corregge il mime),
GUID e dimensione in sola lettura, colonna blob nascosta in tabella, titolo feature = nome file.

## Verdetti tecnici (già chiusi dal prototipo, non da ridiscutere)

1. **Anteprima inline via `data:`-URI funziona, ma nel form NON vale `[% %]`**
   (quella sintassi è di mapTip e layout di stampa). Il riquadro HTML del form è
   un web view QtWebKit: i valori si leggono da JavaScript con
   `expression.evaluate('"CAMPO"')` (cfr. `qgshtmlwidgetwrapper.cpp`).
   `to_base64("DATA")` fa round-trip fedele ai byte (4/4 sul GDB); il ramo
   img/fallback vive in un `if` JavaScript sul `CONTENT_TYPE`.
2. **Widget ExternalResource: NON applicabile.** Si aspetta un percorso file, ma
   `ATT_NAME` è solo un nome dentro il GDB (il blob non sta sul filesystem).
   Metterlo mostrerebbe un selettore file rotto. HTML + azioni coprono il requisito
   del ticket («widget HTML/External Resource») senza finte.
3. **TIFF/MP4/PDF: niente inline** (i browser integrati non renderizzano TIFF; PDF/MP4
   dipendono dai plugin) → fallback testuale + azione *Apri allegato* che esporta
   il blob in temp e lo apre col programma predefinito. Vale per **tutti** i formati.
4. **Limite noto**: nomi file con apice (`'`) rompono le azioni Python (sostituzione
   `[% %]` dentro stringa). Sanitizzazione nomi → da decidere al ticket 06 con le
   collisioni; qui documentato, non risolto.
5. **Costo base64**: l'anteprima incolla il file codificato nel form; con foto da MB
   il form pesa (performance batch → fuori perimetro, vedi mappa).

## Avvertenza (ticket 02)

`test_attach.gdb` è una tabella **fantasma**: creata via GDAL, senza `__ATTACHREL`
né metadati `GDB_Items`. Serve solo a provare i QML. La vera tabella allegati nasce
solo da ArcGIS Pro (`EnableAttachments`) — il plugin non la creerà mai.

## Validazione già fatta (headless, QGIS 3.44.4)

- 3/3 QML ricaricati con `loadNamedStyle` OK su layer fresco **e applicati alla vera
  tabella `fotorilievo_test__ATTACH` del GDB** (regressione: niente più "geom. sbagliata").
- 4/4 blob del GDB: `to_base64` → decode identico agli originali; ramo CASE WHEN
  corretto per tutti (2 img / 2 fallback).
- Vincoli (C), azione default (tutte), alias IT, colonna DATA nascosta: serializzati.

**Non verificato**: resa visiva reale del form, HTML con foto grandi, azioni su file
veri, mapTip su canvas. Serve il tuo occhio in QGIS.

## Domande per te (reagisci qui)

1. Quale variante vince? (vale anche «testata di B + tab Foto di C», i pezzi si ricombinano)
2. Anteprima anche in **tabella attributi** o basta form + mapTip?
3. Il pulsante *Apri* dentro il form (C) è utile o basta il menu Azioni?
4. QML unico per tutti i mime o stili separati per foto vs documenti?
