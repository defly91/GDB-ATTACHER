# -*- coding: utf-8 -*-
"""core/discovery.py — auto-discovery dei **campi foto** (porta del prototipo, ticket 05).

Euristica a **4 segnali sui valori + 1 sul nome del campo** (misurata 7/7 campi foto
veri preselezionati e 0 falsi positivi con la cartella base, 6/7 senza):

- ``ext%``    quota di valori non nulli che finiscono con un'estensione allegabile;
- ``esiste%`` quota risolta a un file reale sotto la cartella base;
- ``multi%``  quota con più file nello stesso valore (``a.jpg;b.jpg``);
- ``guid%`` / ``num%`` / ``remoto%`` — segnali di **scarto** (GlobalID, numeri, URL);
- ``nome``    il nome del campo contiene una parola chiave (``foto``, ``file``,
  ``path``, ``percorso``, ``allegat``, ``doc``…), che **suggerisce ma non decide**.

Da qui i 4 livelli del wizard: **A** preselezionato (i file ci sono), **B**
preselezionato con avviso (estensione ma non verificati su disco), **C** solo il
nome (da rivedere), **D** nascosto.

Verdetti del prototipo recepiti qui:
1. la cartella base è il segnale più forte → il wizard la chiede *prima* della
   selezione dei campi (passo 3, non 4);
2. i valori nulli arrivano da QGIS come sentinella ``NULL``, non ``None``;
3. un token con spazi vale come nome file solo se il file esiste davvero
   (altrimenti è prosa che cita un ``.jpg``);
4. il campo pseudo-``fid`` che alcuni provider espongono è rumore: escluso.

Il modulo è importabile senza QGIS: ``qgis.*`` compare solo dentro ``_e_null()`` e
dentro il rilevatore di tipo predefinito, entrambi in ``try/except``.
"""

from __future__ import annotations

import os
import re
from dataclasses import asdict, dataclass
from dataclasses import field as _field

# ---------------------------------------------------------------- costanti

#: Estensioni considerate allegabili. Volutamente larga: il plugin allega
#: qualsiasi file, non solo immagini.
ESTENSIONI = (
    "jpg", "jpeg", "png", "tif", "tiff", "bmp", "gif", "webp", "heic", "heif",
    "pdf", "doc", "docx", "xls", "xlsx", "odt", "ods", "txt", "dwg", "dxf", "dgn",
    "zip", "7z", "mp4", "mov", "avi", "mkv", "mp3", "wav",
)

#: Parole chiave nel nome del campo (sotto-stringa, case-insensitive).
PAROLE_CHIAVE = (
    "foto", "photo", "immagine", "image", "img", "file", "filename", "nomefile",
    "path", "percorso", "allegat", "attach", "document", "doc", "scansion", "scan",
    "planimetr", "raster", "immagini",
)

#: Separatori dei valori multi-file. La virgola è **esclusa** di proposito
#: (rischio prosa, ticket 06).
SEPARATORI_MULTIVALORE = (";", "|", "\n")

GUID_RE = re.compile(
    r"^\{?[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-"
    r"[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\}?$"
)
URL_RE = re.compile(r"^[a-zA-Z][a-zA-Z0-9+.\-]*://")
SEPARATORI_RE = re.compile(r"[;|\n]")
NUM_RE = re.compile(r"^[+-]?\d+([.,]\d+)?$")

#: Livelli, dal più forte al più debole.
LIVELLI = ("A", "B", "C", "D")

#: Soglia unica dell'euristica (sta in una banda vuota: veri 80-91%, prosa 0%).
SOGLIA = 0.5

#: Campi che il provider espone ma che non sono mai campi foto (ticket 05,
#: «cosa resta al wizard»): pseudo-campo FID.
NOMI_DA_ESCLUDERE = ("fid",)


# ---------------------------------------------------------------- strutture


@dataclass
class PunteggioCampo:
    """Una riga della tabella campo → match-rate."""

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

    @property
    def preselezionato(self) -> bool:
        """A e B sono preselezionati dalla discovery; C no; D è nascosto."""
        return self.livello in ("A", "B")

    def dict(self) -> dict:
        return asdict(self)


# ---------------------------------------------------------------- utility


def _normalizza(testo: str) -> str:
    return "".join(c for c in str(testo).lower() if c.isalnum() or c in " _-")


def _nome_match(nome: str, parole_chiave) -> bool:
    n = _normalizza(nome)
    return any(k in n for k in parole_chiave)


def _e_null(valore) -> bool:
    """QGIS consegna i valori nulli come sentinella ``NULL`` (non ``None``)."""
    if valore is None:
        return True
    if isinstance(valore, str):
        return valore.strip() == ""
    try:
        from qgis.core import NULL

        return bool(valore == NULL)
    except Exception:
        return False


def _tokenizza(valore) -> list:
    """Un valore può contenere più file (``a.jpg;b.jpg``) → token non vuoti."""
    if _e_null(valore):
        return []
    testo = str(valore).strip()
    if not testo:
        return []
    return [t.strip().strip('"').strip("'") for t in SEPARATORI_RE.split(testo) if t.strip()]


def _sembra_url(token: str) -> bool:
    return bool(URL_RE.match(token))


def _ha_estensione(token: str, estensioni) -> bool:
    if _sembra_url(token):
        percorso = token.split("?", 1)[0].split("#", 1)[0]
    else:
        percorso = token
    estensione = os.path.splitext(percorso)[1].lstrip(".").lower()
    return estensione in estensioni


def _candidato_file(token: str, indice, estensioni) -> bool:
    """Un token con spazi è un nome file solo se il file esiste davvero.

    Altrimenti è prosa che cita un'estensione («manca la foto X.jpg»).
    """
    if not re.search(r"\s", token):
        return True
    return bool(indice and indice.risolvi(token, estensioni))


class IndiceFile:
    """Indice pigro dei file sotto la cartella base (profondità 2), con cache.

    Serve a risolvere i nomi senza estensione (``SS_0001`` → ``sottosuolo/SS_0001.jpg``)
    e i percorsi relativi (``contatore/ACQ_1.jpg``), come fanno i due script in repo.
    """

    _cache: dict = {}

    def __init__(self, cartella_base: str, estensioni=None):
        self.cartella_base = os.path.normpath(cartella_base)
        self.estensioni = tuple(estensioni or ESTENSIONI)
        self.percorsi = {}   # path relativo minuscolo (sep '/') -> percorso assoluto
        self.nomi = {}       # basename minuscolo -> primo percorso assoluto
        for radice_abs, dirs, files in os.walk(self.cartella_base):
            rel_radice = os.path.relpath(radice_abs, self.cartella_base).replace("\\", "/")
            if rel_radice.count("/") > 1:      # profondità massima 2
                dirs[:] = []                   # pota: non scendere oltre
                continue
            for nome_file in files:
                rel = nome_file if rel_radice == "." else f"{rel_radice}/{nome_file}"
                self.percorsi.setdefault(rel.lower(), os.path.join(radice_abs, nome_file))
                self.nomi.setdefault(nome_file.lower(), os.path.join(radice_abs, nome_file))

    @classmethod
    def per_cartella(cls, cartella_base: str, estensioni=None) -> "IndiceFile":
        """Indice in cache per cartella (una scansione per sessione, non una per campo)."""
        chiave = (os.path.normpath(str(cartella_base)).lower(), tuple(estensioni or ESTENSIONI))
        if chiave not in cls._cache:
            cls._cache[chiave] = cls(cartella_base, estensioni)
        return cls._cache[chiave]

    @classmethod
    def pulisci_cache(cls):
        """Svuota la cache (usata dai test e dopo aver cambiato cartella base)."""
        cls._cache = {}

    def risolvi(self, token: str, estensioni=None) -> str:
        """Token → percorso esistente, oppure ``""``.

        Cascata identica a quella dei due script: percorso assoluto, ``base/token``,
        percorso relativo indicizzato, ``token + estensione`` per i nomi senza
        estensione, e infine il basename indicizzato.
        """
        estensioni = tuple(estensioni or self.estensioni)
        if not token or _sembra_url(token):
            return ""
        rel = token.replace("\\", "/").strip()
        if os.path.isabs(token) and os.path.isfile(token):
            return token
        # 1) base + token (con o senza sottocartella)
        candidato = os.path.join(self.cartella_base, *rel.split("/"))
        if os.path.isfile(candidato):
            return candidato
        # 2) token come percorso relativo già indicizzato
        trovato = self.percorsi.get(rel.lower())
        if trovato:
            return trovato
        # 3) nome senza estensione: prova le estensioni note (solo token senza spazi)
        if not os.path.splitext(rel)[1] and not re.search(r"\s", rel):
            for estensione in estensioni:
                candidato = os.path.join(self.cartella_base, *rel.split("/")) + "." + estensione
                if os.path.isfile(candidato):
                    return candidato
                trovato = self.percorsi.get((rel + "." + estensione).lower())
                if trovato:
                    return trovato
                trovato = self.nomi.get((os.path.basename(rel) + "." + estensione).lower())
                if trovato:
                    return trovato
        # 4) basename indicizzato (cartella giusta, valore senza sottocartella)
        if re.search(r"\s", rel):
            return ""
        return self.nomi.get(os.path.basename(rel).lower(), "")


def risolutore_file(cartella_base: str, estensioni=None):
    """Ritorna una funzione ``token -> percorso`` (o ``""``) sulla cartella base.

    Se la cartella non esiste, il risolutore risolve solo i percorsi assoluti
    esistenti: è il comportamento "senza cartella base" della discovery.
    """
    estensioni = tuple(estensioni or ESTENSIONI)
    if cartella_base and os.path.isdir(cartella_base):
        indice = IndiceFile.per_cartella(cartella_base, estensioni)

        def _risolvi(token: str) -> str:
            return indice.risolvi(token, estensioni)

        return _risolvi

    def _risolvi_assoluti(token: str) -> str:
        token = str(token or "").strip()
        if token and os.path.isabs(token) and os.path.isfile(token):
            return token
        return ""

    return _risolvi_assoluti


# ---------------------------------------------------------------- tipo campo


def tipo_leggibile(campo) -> str:
    """Tipo leggibile del campo: ``stringa``, ``numerico``, ``data``, ``blob``…

    Fuori da QGIS (test di logica pura) ripiega su ``campo.tipo`` se presente,
    altrimenti su ``stringa``.
    """
    try:
        from qgis.PyQt.QtCore import QMetaType

        tipo = campo.type()
        if tipo in (QMetaType.Type.QString, QMetaType.Type.QChar):
            return "stringa"
        if tipo in (QMetaType.Type.Int, QMetaType.Type.LongLong, QMetaType.Type.Double,
                    QMetaType.Type.UInt, QMetaType.Type.ULongLong, QMetaType.Type.Float):
            return "numerico"
        if tipo in (QMetaType.Type.QDate, QMetaType.Type.QDateTime, QMetaType.Type.QTime):
            return "data"
        if tipo == QMetaType.Type.Bool:
            return "booleano"
        if tipo == QMetaType.Type.QByteArray:
            return "blob"
        return "altro"
    except Exception:
        # Fuori da QGIS (test di logica pura) o con oggetti finti: ripiego esplicito.
        return str(getattr(campo, "tipo", "stringa"))


# ---------------------------------------------------------------- motore


def punteggio_campo(nome, tipo, valori, cartella_base=None, estensioni=None,
                    parole_chiave=None) -> PunteggioCampo:
    """Punteggio di un singolo campo: la regola dei 4 livelli, in un posto solo."""
    estensioni = tuple(e.lower().lstrip(".") for e in (estensioni or ESTENSIONI))
    parole_chiave = tuple(parole_chiave or PAROLE_CHIAVE)

    n_valori = len(valori)
    non_nulli = [v for v in valori if _tokenizza(v)]
    n_non_null = len(non_nulli)

    guid = num = remoto = ext = percorso = esiste = multi = 0
    n_esistenti = 0
    esempi = []

    indice = IndiceFile.per_cartella(cartella_base, estensioni) if (
        cartella_base and os.path.isdir(cartella_base)) else None

    for valore in non_nulli:
        token = _tokenizza(valore)
        token_file = [t for t in token if _candidato_file(t, indice, estensioni)]
        if len(esempi) < 2:
            esempi.append(str(valore).strip())
        if len(token) == 1 and GUID_RE.match(token[0]):
            guid += 1
        if all(NUM_RE.match(t) for t in token):
            num += 1
        if token and all(_sembra_url(t) for t in token):
            remoto += 1
        if any(_ha_estensione(t, estensioni) for t in token_file):
            ext += 1
        if any(("/" in t or "\\" in t) and not _sembra_url(t) for t in token_file):
            percorso += 1
        esistenti_token = sum(1 for t in token_file if indice and indice.risolvi(t, estensioni))
        if esistenti_token:
            esiste += 1
            n_esistenti += 1
        if esistenti_token >= 2 or sum(
                1 for t in token_file if _ha_estensione(t, estensioni)) >= 2:
            multi += 1

    def rate(n):
        return round(n / n_non_null, 3) if n_non_null else 0.0

    nome_match = _nome_match(nome, parole_chiave)
    ext_rate, esiste_rate = rate(ext), rate(esiste)

    # I segnali di scarto vengono prima: un campo con valori GUID/numero/URL non è
    # un campo foto nemmeno se si chiama «foto» (lezione n. 5 del prototipo).
    if tipo != "stringa":
        livello, motivo = "D", f"tipo non testuale ({tipo})"
    elif n_non_null == 0:
        livello, motivo = "D", "nessun valore non nullo"
    elif rate(guid) >= SOGLIA:
        livello, motivo = "D", "valori GUID (probabile GlobalID, da escludere)"
    elif rate(num) >= 0.8:
        livello, motivo = "D", "valori numerici"
    elif rate(remoto) >= SOGLIA:
        livello, motivo = "D", "URL remoti o percorso non locale"
    elif esiste_rate >= SOGLIA and (n_esistenti >= 2 or n_non_null <= 2):
        livello, motivo = "A", f"file trovati nella cartella base ({n_esistenti}/{n_non_null})"
    elif ext_rate >= SOGLIA and n_non_null >= 2:
        livello, motivo = "B", "valori con estensione di file, ma non verificati su disco"
    elif nome_match:
        livello, motivo = "C", "solo il nome suggerisce un campo foto"
    else:
        livello, motivo = "D", "nessun segnale di nome o di valore"

    multi_rate = rate(multi)
    if multi and livello in ("A", "B", "C"):
        motivo += f"; {multi_rate:.0%} valori multipli"

    return PunteggioCampo(
        campo=nome, tipo=tipo, n_valori=n_valori, n_non_null=n_non_null,
        n_esistenti=n_esistenti, nome_match=nome_match,
        ext_rate=ext_rate, path_rate=rate(percorso), esiste_rate=esiste_rate,
        multi_rate=multi_rate, guid_rate=rate(guid), num_rate=rate(num),
        remoto_rate=rate(remoto), livello=livello, motivo=motivo, esempi=esempi,
    )


def suggerisci_campi(layer, cartella_base: str = None, max_feature: int = 500,
                     estensioni=None, parole_chiave=None, tipo_fn=None,
                     escludi_fid: bool = True) -> list:
    """Righe di punteggio per **tutti** i campi del layer, ordinate per livello (A..D).

    :param layer: layer sorgente (QGIS, o qualunque oggetto con ``fields()`` e
        ``getFeatures()`` iterabile)
    :param cartella_base: cartella dei file; senza di essa la discovery è solo
        sintattica (nessuna verifica su disco → niente livello A)
    :param max_feature: campione massimo di feature lette (performance su GDB grandi)
    :param tipo_fn: funzione ``campo -> tipo`` (iniettabile nei test senza QGIS)
    :param escludi_fid: scarta il pseudo-campo ``fid`` che alcuni provider espongono
    """
    estensioni = tuple(e.lower().lstrip(".") for e in (estensioni or ESTENSIONI))
    parole_chiave = tuple(parole_chiave or PAROLE_CHIAVE)
    tipo_fn = tipo_fn or tipo_leggibile

    campi = layer.fields()
    valori_per_campo = {campo.name(): [] for campo in campi}
    for indice, feature in enumerate(layer.getFeatures()):
        if indice >= max_feature:
            break
        for campo in campi:
            valori_per_campo[campo.name()].append(feature[campo.name()])

    righe = [
        punteggio_campo(
            campo.name(), tipo_fn(campo), valori_per_campo[campo.name()],
            cartella_base, estensioni, parole_chiave,
        )
        for campo in campi
        if not (escludi_fid and campo.name().lower() in NOMI_DA_ESCLUDERE)
    ]
    righe.sort(key=lambda r: (LIVELLI.index(r.livello), -r.esiste_rate, -r.ext_rate, r.campo.lower()))
    return righe


def riassunto(righe) -> dict:
    """Campi per livello + i due insiemi che servono alla UI."""
    per_livello = {livello: [r.campo for r in righe if r.livello == livello] for livello in LIVELLI}
    return {
        "per_livello": per_livello,
        "preselezionati": per_livello["A"] + per_livello["B"],
        "da_rivedere": per_livello["C"],
        "nascosti": per_livello["D"],
    }


# ---------------------------------------------------------------- resa (log/markdown)

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
    """La tabella del prototipo, in markdown: utile per i log e per i test a occhio."""
    out = []
    if titolo:
        out += [f"### {titolo}", ""]
    out += ["| " + " | ".join(INTESTAZIONE) + " |", "|" + "---|" * len(INTESTAZIONE)]
    out += [_riga_md(r) for r in righe]
    s = riassunto(righe)
    out += ["", f"Preselezionati (A+B): {', '.join(s['preselezionati']) or '—'}  ",
            f"Da rivedere (C): {', '.join(s['da_rivedere']) or '—'}"]
    return "\n".join(out)


def tabella_dict(righe) -> list:
    """Le righe in forma dati (per la UI: niente dipendenze da dataclass)."""
    return [r.dict() for r in righe]
