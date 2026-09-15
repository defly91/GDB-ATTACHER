# Ticket 05 — auto-discovery campi foto (task, AFK)

> Domanda: **quale euristica di auto-discovery dei campi foto/allegati implementiamo
> prima della schermata di selezione?**
> Risolto quando esiste una tabella campo → match-rate su layer di esempio.
> Le soglie e la UI restano fuori da questo ticket (sono del wizard).

Questo prototipo misura la funzione `suggerisci_campi()` sui layer di esempio e
produce la tabella. **Non** è codice di prodotto: è l'esperimento che rende la
decisione sul wizard basata su dati.

## Contenuto

| File | Cos'è |
|---|---|
| `suggerisci_campi.py` | L'euristica: funzione pura, un layout di `PunteggioCampo` per ogni campo del layer |
| `misura_euristiche.py` | Harness headless: gira l'euristica in 2 modalità, misura precision/recall, scrive la tabella |
| `esempi/genera_esempi.py` | Genera i layer di esempio + la cartella foto finta + `attesi.json` |
| `esempi/discovery_esempi.gpkg` | 3 layer di esempio (12 feature ciascuno), forme prese dai due script — **generato**, non in git |
| `esempi/foto/` | 43 file finti (jpg/pdf minuscoli) per la verifica su disco — **generati**, non in git |
| `esempi/attesi.json` | Verità attesa: campi foto veri (attesi) e campi che NON vanno preselezionati (trappole) — **generato** |
| `tabella-match-rate.md` | **Il deliverable**: tabella campo → match-rate, con la verifica contro la verità attesa |
| `tabella-match-rate.json` | La stessa misura in forma dati, per l'eventuale schermata del wizard |

## Come rigenerare (headless, QGIS 3.44.4)

```
cd prototype/05-field-discovery
PYTHONPATH="...QGIS.../apps/qgis/python" ".../apps/Python312/python.exe" misura_euristiche.py
```

`misura_euristiche.py` rigenera da sé le fixture se mancano (`esempi/foto/` è
volutamente fuori dal git: `.gitignore` esclude `*.jpg`/`*.pdf`), poi scrive
tabella e JSON. Per rigenerare solo le fixture: `esempi/genera_esempi.py`.

Da console QGIS basta `suggerisci_campi(layer)` (vedi l'header del modulo).

## L'euristica in due righe

Per ogni campo si misurano quattro segnali sui valori (campione di 500 feature) e
uno sul nome:

- `ext%` — quota di valori non nulli che finiscono con un'estensione allegabile
  (lista estesa: immagini, pdf, documenti, video…);
- `esiste%` — quota risolta a **un file reale** sotto la cartella base (percorso
  assoluto, `base/valore`, `base/valore.ext`, indice dei file per nome);
- `multi%` — quota con più file in un solo valore (`a.jpg;b.jpg`);
- segnali di **scarto**: `guid%` (probabile `GlobalID`), `num%`, `remoto%` (URL);
- `nome` — il nome del campo contiene una parola chiave (`foto`, `file`, `path`,
  `percorso`, `allegat`, `doc`, `immagine`, `scansion`…).

Da qui i 4 livelli, che sono la vera proposta per il wizard:

| Livello | Regola | Cosa fa la UI (proposta) |
|---|---|---|
| **A** | `esiste% ≥ 50%` e ≥ 2 file trovati | preselezionato ✅ (prova: i file ci sono) |
| **B** | `ext% ≥ 50%`, non verificati su disco | preselezionato con avviso ⚠️ |
| **C** | solo il nome suggerisce (o `ext% < 50%`) | mostrato, **non** preselezionato ⬜ |
| **D** | tipo non testuale, tutti nulli, GUID, numerico, URL | nascosto |

## Esito misurato

Su 3 layer × ~9 campi (26 campi totali, 7 sono campi foto veri secondo i due script):

| | Preselezionati A+B | Falsi positivi A+B | Attesi non preselezionati |
|---|---|---|---|
| **Con cartella base** | **7/7** | **0** | 0 |
| **Senza cartella base** | **6/7** | **0** | 1 (`foto_impianto`, solo C) |

In entrambe le modalità restano 2 soli suggerimenti soft di livello C
(`foto_note`, `note_doc`: nome sospetto, valori prosa) — mostrati ma non preselezionati.

Le trappole che l'euristica scarta correttamente: `GlobalID`/`GLOBALID` (per valori
GUID), `quota`/`fid`/`id_foto` (numerici), `data_*` (tipo data), `foto_archiviata`
(tutta nulla), `link_foto` (URL remoti), `note`/`descrizione` (prosa che cita un
`.jpg` in mezzo alla frase).

## Verdetti tecnici (chiusi da questo esperimento)

1. **La cartella base è il segnale più forte: senza, la discovery perde un livello.**
   `foto_impianto` contiene nomi senza estensione (`SS_0001`) — esattamente il caso
   che il primo script insinua col commento `# + '.jpg'` — e senza cartella base
   resta C. Con cartella base sale ad A. → *La cartella base va chiesta **prima o
   insieme** alla selezione dei campi, non dopo* (decisione di ordine del wizard).
2. **La soglia 0.5 sta in una banda vuota.** I campi foto veri misurano `esiste%`
   80–91% ed `ext%` 91–100%; le trappole di prosa misurano 0%; nessun campo cade tra
   8% e 67% in questa misura. La soglia 0.5 è quindi robusta su questi dati (ma la
   misura è su dati sintetici: da riconfermare su un GDB cliente).
3. **I valori nulli arrivano dal layer come sentinella `NULL` di QGIS, non come
   `None`.** Un `str(v)` ingenuo trasforma ogni campo vuoto in un valore `"NULL"`
   non nullo: `foto_archiviata` (12/12 nulli) risultava pieno e saliva a C. Va
   normalizzato (`== NULL`) prima di qualunque conteggio. Trappola reale, non di test.
4. **Un campo prosa che cita un filename genera falsi segnali.** `descrizione`
   ("vedi foto superficie/EST_0001.jpg") dava `ext% 8%` e — via fallback sul nome
   file — `esiste% 8%`. Regola adottata: un token con spazi vale come filename solo
   se il file esiste davvero; altrimenti è prosa.
5. **La lista di parole chiave non basta, e da sola fa danni.** `link_foto` e
   `id_foto` hanno il nome perfetto ma valori URL/numerici: senza i segnali di
   scarto finirebbero preselezionati (B). Il nome va usato per **ordinare e
   suggerire**, mai per decidere; il valore decide.
6. **`;` sì, `,` no.** I multi-valore separati da `;`/`|`/a capo sono rilevati
   (`multi% 60%`); quelli separati da virgola no (rischio prosa). Limite noto, non
   risolto.
7. **Costo**: una passata di 500 feature per layer, indice della cartella base
   costruito una volta e messo in cache. Nessun I/O oltre a `isfile`/`os.walk`.

## Cosa resta al wizard (non deciso qui)

- Dove si sceglie la cartella base nell'ordine degli step (vedi verdetto 1).
- Cosa mostra la preview quando la cartella base non c'è ancora (solo B/C?).
- Testi IT/EN dei livelli A/B/C e il wording dell'avviso su B.
- Esclusione esplicita del campo `fid`/pseudo-campo FID, che `layer.fields()` espone
  su alcuni provider (qui finisce in D da solo, ma è rumore in tabella).

## Non verificato

- GDB cliente reale (qui è tutto sintetico): percorsi UNC, accenti, nomi con spazi
  veri, campi con `\` finale, `.gdb` vs `.gpkg`.
- Campi foto con nome file spezzato su due campi (es. cartella + nome) — caso reale
  possibile, non coperto.
- Le soglie su layer molto piccoli (< 3 feature) o con pochi valori non nulli.
