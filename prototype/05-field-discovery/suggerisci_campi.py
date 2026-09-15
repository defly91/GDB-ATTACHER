# suggerisci_campi.py — PROTOTIPO throwaway (ticket 05)
# "Quale euristica di auto-discovery dei campi foto/allegati, prima della schermata
#  di selezione?" — funzione pura, niente UI, niente scrittura: legge un layer e
#  restituisce una riga di punteggio per OGNI campo, con il match-rate dei valori.
#
# Ereditata dalla logica dei due script in repo:
#   - "Allega foto GDB.py": il campo foto contiene un nome file (a volte senza
#     estensione, cfr. il commento `# + '.jpg'`), risolto contro una cartella base.
#   - "Aggiungi singola doto al GDB.py": scelta manuale del campo + cartella base,
#     con `find_field_ci()` case-insensitive e `guess_content_type()` per estensione.
#
# Uso da console QGIS / script headless:
#     righe = suggerisci_campi(layer)
#     righe = suggerisci_campi(layer, cartella_base=r"C:\...\Foto")
#     print(tabella_markdown(righe))
#
# Nessuna decisione di soglia/UI vive qui: le soglie sono parametri espliciti.

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field as _field, asdict

# ---------------------------------------------------------------- costanti

# Estensioni considerate "allegabili" (foto + documenti + video). Volutamente
# larga: il plugin allega qualsiasi file, non solo immagini.
ESTENSIONI = (
    "jpg", "jpeg", "png", "tif", "tiff", "bmp", "gif", "webp", "heic", "heif",
    "pdf", "doc", "docx", "xls", "xlsx", "odt", "ods", "txt", "dwg", "dxf", "dgn",
    "zip", "7z", "mp4", "mov", "avi", "mkv", "mp3", "wav",
)

# Parole chiave nel NOME del campo. Sotto-stringa, case-insensitive.
# 'doc' e' volutamente incluso: in italiano "documento/allegato".
PAROLE_CHIAVE = (
    "foto", "photo", "immagine", "image", "img", "file", "filename", "nomefile",
    "path", "percorso", "allegat", "attach", "document", "doc", "scansion", "scan",
    "planimetr", "raster", "immagini",
)

GUID_RE = re.compile(
    r"^\{?[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-"
    r"[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\}?$"
)
URL_RE = re.compile(r"^[a-zA-Z][a-zA-Z0-9+.\-]*://")
SEPARATORI_RE = re.compile(r"[;|\n]")
NUM_RE = re.compile(r"^[+-]?\d+([.,]\d+)?$")

LIVELLI = ("A", "B", "C", "D")

# ---------------------------------------------------------------- strutture


@dataclass
class PunteggioCampo:
    """Una riga della tabella campo -> match-rate."""

    campo: str
    tipo: str
    n_valori: int
    n_non_null: int
    n_esistenti: int
    nome_match: bool
    ext_rate: float
    path_rate: float
    esiste_rate: float
    multi_rate: float
    guid_rate: float
    num_rate: float
    remoto_rate: float
    livello: str
    motivo: str
    esempi: list = _field(default_factory=list)

    def dict(self) -> dict:
        return asdict(self)


# ---------------------------------------------------------------- utility


def _normalizza(testo: str) -> str:
    return "".join(
        c for c in str(testo).lower()
        if c.isalnum() or c in " _-"
    )


def _nome_match(nome: str, parole_chiave) -> bool:
    n = _normalizza(nome)
    return any(k in n for k in parole_chiave)


def _tokenizza(valore) -> list:
    """Un valore puo' contenere piu' file ('a.jpg;b.jpg'). Ritorna i token non vuoti."""
    if _e_null(valore):
        return []
    testo = str(valore).strip()
    if not testo:
        return []
    return [t.strip().strip('"').strip("'") for t in SEPARATORI_RE.split(testo) if t.strip()]


def _e_null(valore) -> bool:
    """QGIS consegna i valori nulli come sentinella `NULL` (non None) via
    feat[campo] / feat.attribute(); vanno trattati come vuoti."""
    if valore is None:
        return True
    if isinstance(valore, str):
        return valore.strip() == ""
    try:
        from qgis.core import NULL
        return bool(valore == NULL)
    except Exception:
        return False


def _sembra_url(token: str) -> bool:
    return bool(URL_RE.match(token))


def _candidato_file(token: str, indice, estensioni) -> bool:
    """Un token con spazi e' un nome file solo se il file esiste davvero;
    altrimenti e' prosa che cita un'estensione (es. "manca la foto X.jpg")."""
    if not re.search(r"\s", token):
        return True
    return bool(indice and indice.risolvi(token, estensioni))


def _ha_estensione(token: str, estensioni) -> bool:
    if _sembra_url(token):
        # per un URL conta comunque l'estensione finale (es. .../foto.jpg)
        path = token.split("?", 1)[0].split("#", 1)[0]
    else:
        path = token
    ext = os.path.splitext(path)[1].lstrip(".").lower()
    return ext in estensioni


class _IndiceFile:
    """Indice pigro dei file sotto la cartella base (2 livelli), con cache.

    Serve a risolvere i nomi senza estensione ('SS_0001' -> sottosuolo/SS_0001.jpg)
    e i percorsi relativi ('contatore/ACQ_1.jpg'), come fanno i due script.
    """

    _cache: dict = {}

    def __init__(self, cartella_base: str, estensioni):
        self.cartella_base = os.path.normpath(cartella_base)
        self.percorsi = {}   # chiave: path relativo minuscolo, con separatore '/'
        self.nomi = {}       # chiave: basename minuscolo -> primo percorso assoluto
        for radice_abs, _dirs, files in os.walk(self.cartella_base):
            rel_radice = os.path.relpath(radice_abs, self.cartella_base).replace("\\", "/")
            if rel_radice.count("/") > 1:      # profondita' massima 2
                continue
            for f in files:
                rel = f if rel_radice == "." else f"{rel_radice}/{f}"
                self.percorsi.setdefault(rel.lower(), os.path.join(radice_abs, f))
                self.nomi.setdefault(f.lower(), os.path.join(radice_abs, f))

    @classmethod
    def per_cartella(cls, cartella_base: str, estensioni) -> "_IndiceFile":
        chiave = os.path.normpath(cartella_base).lower()
        if chiave not in cls._cache:
            cls._cache[chiave] = cls(cartella_base, estensioni)
        return cls._cache[chiave]

    def risolvi(self, token: str, estensioni) -> str | None:
        """Token -> percorso esistente, o None. Cascata identica ai due script."""
        if _sembra_url(token):
            return None
        rel = token.replace("\\", "/").strip()
        if os.path.isabs(token) and os.path.isfile(token):
            return token
        # 1) base + token (con o senza sottocartella)
        cand = os.path.join(self.cartella_base, *rel.split("/"))
        if os.path.isfile(cand):
            return cand
        # 2) token come percorso relativo indicizzato
        hit = self.percorsi.get(rel.lower())
        if hit:
            return hit
        # 3) nome senza estensione: prova le estensioni note (solo token senza spazi:
        #    un token con spazi e' un filename vero solo se combacia esattamente sopra)
        if not os.path.splitext(rel)[1] and not re.search(r"\s", rel):
            for e in estensioni:
                cand = os.path.join(self.cartella_base, *rel.split("/")) + "." + e
                if os.path.isfile(cand):
                    return cand
                hit = self.percorsi.get((rel + "." + e).lower())
                if hit:
                    return hit
                hit = self.nomi.get((os.path.basename(rel) + "." + e).lower())
                if hit:
                    return hit
        # 4) basename indicizzato (l'utente ha scelto la cartella giusta ma il
        #    valore non porta la sottocartella)
        if re.search(r"\s", rel):
            return None
        hit = self.nomi.get(os.path.basename(rel).lower())
        return hit


# ---------------------------------------------------------------- motore


def _punteggio_campo(nome, tipo, valori, cartella_base, estensioni, parole_chiave) -> PunteggioCampo:
    n_valori = len(valori)
    non_nulli = [v for v in valori if _tokenizza(v)]
    n_non_null = len(non_nulli)

    guid = num = remoto = ext = path = esiste = multi = 0
    n_esistenti = 0
    esempi = []

    indice = _IndiceFile.per_cartella(cartella_base, estensioni) if (
        cartella_base and os.path.isdir(cartella_base)) else None

    for v in non_nulli:
        token = _tokenizza(v)
        tok_file = [t for t in token if _candidato_file(t, indice, estensioni)]
        if len(esempi) < 2:
            esempi.append(str(v).strip())
        if len(token) == 1 and GUID_RE.match(token[0]):
            guid += 1
        if all(NUM_RE.match(t) for t in token):
            num += 1
        if token and all(_sembra_url(t) for t in token):
            remoto += 1
        if any(_ha_estensione(t, estensioni) for t in tok_file):
            ext += 1
        if any(("/" in t or "\\" in t) and not _sembra_url(t) for t in tok_file):
            path += 1
        esistenti_token = 0
        for t in tok_file:
            if indice and indice.risolvi(t, estensioni):
                esistenti_token += 1
        if esistenti_token:
            esiste += 1
            n_esistenti += 1
        if esistenti_token >= 2 or sum(
                1 for t in tok_file if _ha_estensione(t, estensioni)) >= 2:
            multi += 1

    def rate(n):
        return round(n / n_non_null, 3) if n_non_null else 0.0

    nome_match = _nome_match(nome, parole_chiave)
    ext_rate, esiste_rate = rate(ext), rate(esiste)

    if tipo != "stringa":
        livello, motivo = "D", f"tipo non testuale ({tipo})"
    elif n_non_null == 0:
        livello, motivo = "D", "nessun valore non nullo"
    elif rate(guid) >= 0.5:
        livello, motivo = "D", "valori GUID (probabile GlobalID, da escludere)"
    elif rate(num) >= 0.8:
        livello, motivo = "D", "valori numerici"
    elif rate(remoto) >= 0.5:
        livello, motivo = "D", "URL remoti o percorso non locale"
    elif esiste_rate >= 0.5 and (n_esistenti >= 2 or n_non_null <= 2):
        livello, motivo = "A", f"file trovati nella cartella base ({n_esistenti}/{n_non_null})"
    elif ext_rate >= 0.5 and n_non_null >= 2:
        livello, motivo = "B", "valori con estensione di file, ma non verificati su disco"
    elif nome_match:
        livello, motivo = "C", "solo il nome suggerisce un campo foto"
    else:
        livello, motivo = "D", "nessun segnale di nome o di valore"

    if multi and livello in "ABC":
        motivo += f"; {rate(multi):.0%} valori multipli"

    return PunteggioCampo(
        campo=nome, tipo=tipo, n_valori=n_valori, n_non_null=n_non_null,
        n_esistenti=n_esistenti, nome_match=nome_match,
        ext_rate=ext_rate, path_rate=rate(path), esiste_rate=esiste_rate,
        multi_rate=rate(multi), guid_rate=rate(guid), num_rate=rate(num),
        remoto_rate=rate(remoto), livello=livello, motivo=motivo, esempi=esempi,
    )


def _tipo_leggibile(campo) -> str:
    from qgis.PyQt.QtCore import QMetaType
    t = campo.type()
    if t in (QMetaType.Type.QString, QMetaType.Type.QChar):
        return "stringa"
    if t in (QMetaType.Type.Int, QMetaType.Type.LongLong, QMetaType.Type.Double,
             QMetaType.Type.UInt, QMetaType.Type.ULongLong, QMetaType.Type.Float):
        return "numerico"
    if t in (QMetaType.Type.QDate, QMetaType.Type.QDateTime, QMetaType.Type.QTime):
        return "data"
    if t == QMetaType.Type.Bool:
        return "booleano"
    if t == QMetaType.Type.QByteArray:
        return "blob"
    return "altro"


def suggerisci_campi(layer, cartella_base: str | None = None, max_feature: int = 500,
                     estensioni=None, parole_chiave=None) -> list:
    """Righe di punteggio per TUTTI i campi del layer, ordinate per livello (A..D).

    :param layer: QgsVectorLayer (il "layer sorgente" del glossario)
    :param cartella_base: cartella delle foto; se None la discovery e' solo sintattica
                          (nessuna verifica su disco -> niente livello A)
    :param max_feature: campione massimo di feature lette (performance)
    """
    estensioni = tuple(e.lower().lstrip(".") for e in (estensioni or ESTENSIONI))
    parole_chiave = tuple(parole_chiave or PAROLE_CHIAVE)

    campi = layer.fields()
    valori_per_campo = {c.name(): [] for c in campi}
    for i, feat in enumerate(layer.getFeatures()):
        if i >= max_feature:
            break
        for c in campi:
            valori_per_campo[c.name()].append(feat[c.name()])

    righe = [
        _punteggio_campo(c.name(), _tipo_leggibile(c), valori_per_campo[c.name()],
                         cartella_base, estensioni, parole_chiave)
        for c in campi
    ]
    righe.sort(key=lambda r: (LIVELLI.index(r.livello), -r.esiste_rate, -r.ext_rate, r.campo.lower()))
    return righe


# ---------------------------------------------------------------- resa


def riassunto(righe) -> dict:
    per_livello = {lv: [r.campo for r in righe if r.livello == lv] for lv in LIVELLI}
    return {
        "per_livello": per_livello,
        "preselezionati": per_livello["A"] + per_livello["B"],
        "da_rivedere": per_livello["C"],
    }


INTESTAZIONE = ("campo", "tipo", "valori", "non nulli", "esiste", "nome", "ext%",
                "path%", "esiste%", "multi%", "guid%", "num%", "remoto%", "liv", "motivo")


def _riga_md(r: PunteggioCampo) -> str:
    return "| {} | {} | {} | {} | {} | {} | {} | {} | {} | {} | {} | {} | {} | **{}** | {} |".format(
        r.campo, r.tipo, r.n_valori, r.n_non_null, r.n_esistenti,
        "sì" if r.nome_match else "–",
        f"{r.ext_rate:.0%}", f"{r.path_rate:.0%}", f"{r.esiste_rate:.0%}",
        f"{r.multi_rate:.0%}", f"{r.guid_rate:.0%}", f"{r.num_rate:.0%}",
        f"{r.remoto_rate:.0%}", r.livello, r.motivo,
    )


def tabella_markdown(righe, titolo: str = "") -> str:
    out = []
    if titolo:
        out += [f"### {titolo}", ""]
    out += ["| " + " | ".join(INTESTAZIONE) + " |",
            "|" + "---|" * len(INTESTAZIONE)]
    out += [_riga_md(r) for r in righe]
    s = riassunto(righe)
    out += ["", f"Preselezionati (A+B): {', '.join(s['preselezionati']) or '—'}  ",
            f"Da rivedere (C): {', '.join(s['da_rivedere']) or '—'}"]
    return "\n".join(out)


def tabella_dict(righe) -> list:
    return [r.dict() for r in righe]
