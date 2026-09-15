# oracolo_v1.py — oracolo eseguibile del contratto v1 per naming e deduplica.
#
# PERCHE' UN ORACOLO
# Il pacchetto del plugin (gdb_attacher/) e' scritto in un altro ramo di lavoro e
# qui non esiste: non c'e' codice da testare direttamente. Questi test quindi non
# verificano l'implementazione, verificano il CONTRATTO scritto nelle decisioni
# della mappa (ticket 06 naming, ticket 07 perimetro v1, ticket 02 schema):
#
#   - il file e' risolto da campo foto + cartella base; la modalita' decide solo
#     il NOME ALLEGATO (ATT_NAME);
#   - tre modalita' esclusive: `originale` (default), `formula` (variabili
#     @original_name / @stem / @ext / @index), `csv` (elenco file su chiave
#     GLOBALID);
#   - multi-valore diviso su ';' '|' e a capo;
#   - ATT_NAME verbatim: nessuna sanitizzazione, apice compreso;
#   - collisioni sulla coppia (REL_GLOBALID, ATT_NAME) -> suffisso `_2`, `_3`...;
#   - nome vuoto -> salta e prosegue;
#   - deduplica su (REL_GLOBALID, ATT_NAME) normalizzati: rilanciare non crea
#     doppioni.
#
# Quando `gdb_attacher/` arrivera' su questo ramo, i CASI di questo file sono la
# specifica da far combaciare: `tests/test_contratto_v1.py` contiene i casi
# parametrizzati pronti a essere puntati anche sulle funzioni del plugin.

from __future__ import annotations

import os

#: Modalita' di naming della v1 (esclusive, la prima e' il default).
MODALITA = ("originale", "formula", "csv")

#: Separatori dei valori multi-allegato (decisione ticket 06).
SEPARATORI = (";", "|", "\n")


# ---------------------------------------------------------------------------
# Valori e nomi


def dividi_multivalore(valore) -> list:
    """Un valore puo' contenere piu' file: 'a.jpg;b.jpg', 'a|b', righe a capo."""
    if valore is None:
        return []
    testo = str(valore)
    for separatore in SEPARATORI:
        testo = testo.replace(separatore, "\n")
    return [token.strip() for token in testo.split("\n") if token.strip()]


def normalizza_nome(nome) -> str:
    """ATT_NAME e' verbatim: l'unica normalizzazione e' togliere gli spazi ai bordi."""
    return str(nome).strip() if nome is not None else ""


def nome_originale(token: str) -> str:
    """Modalita' `originale`: il nome del file cosi' com'e' (basename, verbatim)."""
    return normalizza_nome(os.path.basename(str(token).replace("\\", "/")))


def nome_formula(token: str, formula: str, indice: int = 0) -> str:
    """Modalita' `formula`: composizione con @original_name / @stem / @ext / @index.

    Nel plugin la formula e' eseguita da QgsExpression per-feature (cosa che la CI
    non puo' fare): qui la sostituzione e' volutamente minima, serve a fissare le
    variabili disponibili e il risultato atteso.
    """
    originale = nome_originale(token)
    radice, ext = os.path.splitext(originale)
    contesto = {
        "@original_name": originale,
        "@stem": radice,
        "@ext": ext,
        "@index": str(indice),
    }
    for variabile, valore in contesto.items():
        formula = formula.replace(variabile, valore)
    return normalizza_nome(formula)


def nome_da_csv(chiave: str, indice_csv: dict):
    """Modalita' `csv`: il nome arriva dall'elenco file, indicizzato per GLOBALID."""
    if chiave is None:
        return ""
    return normalizza_nome(indice_csv.get(str(chiave).strip()))


def calcola_nome(modalita: str, token: str, indice: int = 0, formula: str = "",
                 chiave: str = "", indice_csv=None) -> str:
    """Nome allegato per un token, secondo la modalita' scelta."""
    if modalita not in MODALITA:
        raise ValueError("modalita' di naming sconosciuta: %r" % (modalita,))
    if modalita == "originale":
        return nome_originale(token)
    if modalita == "formula":
        return nome_formula(token, formula or "@original_name", indice)
    return nome_da_csv(chiave, indice_csv or {})


# ---------------------------------------------------------------------------
# Collisioni e deduplica


def chiave_dedup(rel_globalid, att_name) -> tuple:
    """Chiave di deduplica: parent-GUID normalizzato con graffe + ATT_NAME verbatim.

    Normalizzazione identica a quella dei due script in repo: GUID maiuscolo,
    graffe aggiunte una volta sola, nome alleggerito dagli spazi ai bordi.
    """
    guid = str(rel_globalid or "").strip().strip("{}").upper()
    return ("{%s}" % guid if guid else None, normalizza_nome(att_name))


def suffisso_collisione(nome: str, usati) -> str:
    """Nome libero nella forma `nome_2`, `nome_3`... (il primo resta invariato).

    Un nome vuoto resta vuoto: chi chiama lo salta, qui non si inventa un nome.
    """
    nome = normalizza_nome(nome)
    if not nome:
        return ""
    if nome not in usati:
        return nome
    radice, ext = os.path.splitext(nome)
    contatore = 2
    while True:
        candidato = "%s_%d%s" % (radice, contatore, ext)
        if candidato not in usati:
            return candidato
        contatore += 1


# ---------------------------------------------------------------------------
# Pianificazione di un lotto (la parte che i test usano sulle tabelle finte)


class PianificatoreAllegati:
    """Costruisce le righe da scrivere nella tabella allegati, senza scriverle.

    Fa quello che dovra' fare il plugin: per ogni feature risolve i token del
    campo foto, calcola i nomi secondo la modalita', scarta i nomi vuoti, salta i
    duplicati gia' presenti e risolve le collisioni.
    """

    def __init__(self, modalita="originale", formula="", indice_csv=None,
                 campo_foto="filefoto", campo_chiave="GLOBALID"):
        if modalita not in MODALITA:
            raise ValueError("modalita' di naming sconosciuta: %r" % (modalita,))
        self.modalita = modalita
        self.formula = formula
        self.indice_csv = indice_csv or {}
        self.campo_foto = campo_foto
        self.campo_chiave = campo_chiave

    def righe_da_aggiungere(self, layer_sorgente, esistenti=()) -> list:
        """Elenco di dict {REL_GLOBALID, ATT_NAME, token} per il lotto corrente.

        `esistenti` sono le chiavi (REL_GLOBALID, ATT_NAME) gia' nella tabella
        allegati (vedi `chiavi_presenti`). Le due regole e la loro precedenza:

        1. **collisione dentro lo stesso lotto** (due token diversi che danno lo
           stesso nome, per esempio 'a.jpg' e 'sub/a.jpg'): il secondo prende il
           suffisso `_2`, perche' sono due file diversi;
        2. **idempotenza** contro la tabella esistente: la coppia normalizzata
           (REL_GLOBALID, ATT_NAME) gia' presente viene saltata, cosi' rilanciare
           lo stesso lavoro non crea doppioni.

        Limite noto e voluto: il suffisso nasce solo tra token dello *stesso*
        lotto. Se a monte esiste gia' 'a.jpg' e nel lotto ci sono due file che si
        chiamano 'a.jpg', entrambi vengono saltati — dalla sola tabella allegati
        non si puo' sapere quale dei due sia gia' allegato (il nome non porta la
        provenienza). Caso da verificare a mano, vedi docs/test-strategy.md.
        """
        gia_presenti = set(esistenti)
        usati_per_feature = {}
        nominati_per_feature = {}
        righe = []
        for feature in layer_sorgente.getFeatures():
            chiave = feature[self.campo_chiave]
            if chiave is None or str(chiave).strip() in ("", "NULL"):
                continue                       # senza GLOBALID non si allega nulla
            rel_globalid = "{%s}" % str(chiave).strip().strip("{}").upper()
            if rel_globalid not in usati_per_feature:
                usati_per_feature[rel_globalid] = {
                    nome for (rel, nome) in gia_presenti if rel == rel_globalid
                }
                nominati_per_feature[rel_globalid] = set()
            usati = usati_per_feature[rel_globalid]
            nominati = nominati_per_feature[rel_globalid]
            token = feature[self.campo_foto]
            for indice, singolo in enumerate(dividi_multivalore(token)):
                nome = calcola_nome(
                    self.modalita, singolo, indice=indice + 1, formula=self.formula,
                    chiave=chiave, indice_csv=self.indice_csv)
                if not nome:
                    continue                   # nome vuoto: salta e prosegue
                if nome in nominati:
                    nome = suffisso_collisione(nome, usati)
                if chiave_dedup(rel_globalid, nome) in gia_presenti:
                    continue                   # gia' allegato: idempotenza
                righe.append({"REL_GLOBALID": rel_globalid, "ATT_NAME": nome,
                              "token": singolo})
                usati.add(nome)
                nominati.add(nome)
                gia_presenti.add(chiave_dedup(rel_globalid, nome))
        return righe


def chiavi_presenti(layer_attach) -> set:
    """Coppie (REL_GLOBALID, ATT_NAME) gia' nella tabella allegati finta."""
    return {
        chiave_dedup(f["REL_GLOBALID"], f["ATT_NAME"])
        for f in layer_attach.getFeatures()
    }
