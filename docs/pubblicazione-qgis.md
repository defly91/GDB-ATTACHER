# Pubblicazione sul repo ufficiale plugin QGIS — checklist

Promemoria operativo per il giorno in cui si pubblica **GDB-Attacher** su
[plugins.qgis.org](https://plugins.qgis.org). La decisione (ticket 07) è: si pubblica **dopo** i test
dell'utente su un GDB reale con allegati creati da ArcGIS Pro.

## 1. Prerequisiti bloccanti

- [ ] Tutti i test manuali di `SPEC.md` §12 eseguiti su un GDB reale (14 casi).
- [ ] `attachments` abilitati da ArcGIS Pro su un layer di prova: verifica che l'allegato scritto dal
      plugin sia **visibile e apribile in ArcGIS Pro** (prova che la tabella non è "fantasma").
- [ ] Vincoli `ATT_NAME` su un `__ATTACH` vero: lunghezza massima ammessa, unicità per feature,
      caratteri accettati (voce ancora aperta in `map.md` → "Not yet specified").
- [ ] Nessun dato reale di cliente nel repo o nello zip (il `.gitignore` esclude `*.gdb/`, immagini, PDF).

## 2. Metadati richiesti da plugins.qgis.org

Da controllare in `gdb_attacher/metadata.txt` prima dell'upload:

| Campo | Vincolo / nota |
| --- | --- |
| `name` | uguale al **nome della cartella** del plugin (`gdb_attacher`) |
| `description` | breve, una riga, senza ritorni a capo |
| `about` | descrizione lunga (supporta testo semplice) |
| `version` | semver; deve **crescere** a ogni upload |
| `qgisMinimumVersion` | versione minima reale di QGIS su cui è stato provato |
| `author` / `email` | contatto valido (il repo QGIS può scriverti per la review) |
| `repository` | URL del repo pubblico |
| `tracker` | URL delle issue (se disabilitate, indicare il repo) |
| `homepage` | opzionale |
| `tags` | separati da virgola, max 20 caratteri ciascuno |
| `category` | una tra quelle ammesse (per questo plugin: *Vector* o *Database*) |
| `experimental` | `False` solo quando è pronto per tutti; `True` finché è in rodaggio |
| `icon` | PNG nell'ambito `resources/` (lo zip deve contenerlo) |
| `license` | `GPL-2.0-or-later` (file `LICENSE` presente in repo) |

## 3. Contenuto dello zip

- Radice dello zip = **cartella `gdb_attacher/`** (non il repo intero).
- Dentro: `metadata.txt`, `__init__.py`, `plugin.py`, `core/`, `wizard/`, `resources/` (QML + icone).
- **Fuori**: `tests/`, `docs/`, `prototype/`, `.scratch/`, `scripts/`, `.github/`, `ci/`.
- Lo zip si produce con `scripts/build_plugin_zip.sh` e deve fallire con messaggio chiaro se
  `metadata.txt` non esiste.

## 4. Passi di pubblicazione

1. Bump di `version` in `metadata.txt` e `pyproject.toml`, commit e tag (`git tag v0.1.0`).
2. `scripts/build_plugin_zip.sh` → zip installabile, provato **a mano** su un profilo QGIS pulito
   (Install from ZIP).
3. Upload su plugins.qgis.org (serve un account QGIS; l'account richiede l'accesso via
   GitHub/Google e la verifica email).
4. Compilare la pagina del plugin: descrizione, link al repo, tracker, changelog della versione.
5. Attendere la review automatica (controlli su metadati, zip, licenza) e, se richiesto, quella manuale.
6. Dopo l'approvazione: la scheda del plugin compare con il pulsante di installazione automatica.

## 5. Dopo la pubblicazione

- Le versioni successive si caricano con lo stesso flusso (bump `version` → zip → upload).
- Mantenere un changelog in `README.md` o in una sezione dedicata della pagina plugin.
- Il workflow CI versionato in `ci/github-actions.yml` va copiato in `.github/workflows/ci.yml`
  quando si pusha con un token che ha anche lo scope `workflow` (oggi il token ha solo `repo`:
  GitHub rifiuta i push in `.github/workflows/*`).

## 6. Nota sul marchio Esri

Il plugin usa **solo GDAL/OpenFileGDB**: nessun binario Esri, nessuna dipendenza dal FileGDB SDK,
nessun marchio Esri nel nome o nell'icona del plugin. La creazione della tabella allegati resta
operazione di ArcGIS Pro (`EnableAttachments`) e il plugin lo dice esplicitamente all'utente
(decisione dei ticket 01 e 02).
