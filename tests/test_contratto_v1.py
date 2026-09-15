# test_contratto_v1.py — contratto v1 di naming e deduplica, eseguito sui fake.
#
# ATTENZIONE al perimetro: questi test NON esercitano l'implementazione del plugin
# (gdb_attacher/ e' scritto in un altro ramo di lavoro e qui non esiste). Fissano
# il contratto deciso nella mappa — `tests/oracolo_v1.py` ne e' la versione
# eseguibile — e usano il finto QGIS per la parte "tabella allegati" (feature,
# edit(), blob, DATA_SIZE), cioe' la stessa meccanica che useranno gli script del
# plugin. Quando il pacchetto arrivera', i CASI_NAMING qui sotto sono la specifica
# da far combaciare.
#
# Copertura: naming in tutte e tre le modalita' (originale / formula / csv),
# multi-valore, nome con apice, collisione, nome vuoto, deduplica al rilancio.

from __future__ import annotations

import os

import pytest

from fake_qgis import GUID_1, GUID_2, crea_feature, crea_layer_attach, crea_layer_sorgente
from oracolo_v1 import (
    MODALITA, PianificatoreAllegati, calcola_nome, chiave_dedup, chiavi_presenti,
    dividi_multivalore, nome_da_csv, nome_formula, nome_originale,
    suffisso_collisione,
)

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Specifica del naming: (id, modalita, token, extra, atteso)

CASI_NAMING = [
    ("originale-semplice", "originale", "SS_0001.jpg", {}, "SS_0001.jpg"),
    ("originale-senza-estensione", "originale", "SS_0001", {}, "SS_0001"),
    ("originale-con-percorso", "originale", "contatore/ACQ_1.jpg", {}, "ACQ_1.jpg"),
    ("originale-percorso-windows", "originale", r"contatore\ACQ_1.jpg", {}, "ACQ_1.jpg"),
    ("originale-spazi-ai-bordi", "originale", "  ACQ_2.png  ", {}, "ACQ_2.png"),
    ("originale-apice-verbatim", "originale", "foto d'interno.jpg", {},
     "foto d'interno.jpg"),
    ("originale-pdf", "originale", "documento.pdf", {}, "documento.pdf"),
    ("formula-stem-index-ext", "formula", "SS_0001.jpg",
     {"formula": "@stem_@index@ext", "indice": 1}, "SS_0001_1.jpg"),
    ("formula-solo-index", "formula", "SS_0001.jpg",
     {"formula": "@index", "indice": 3}, "3"),
    ("formula-suffisso-copia", "formula", "SS_0001.jpg",
     {"formula": "@stem_copia@ext", "indice": 1}, "SS_0001_copia.jpg"),
    ("formula-original-name", "formula", "ACQ_2.png",
     {"formula": "@original_name", "indice": 1}, "ACQ_2.png"),
    ("formula-default-senza-formula", "formula", "documento.pdf", {}, "documento.pdf"),
    ("csv-chiave-trovata", "csv", "ignorato.jpg",
     {"chiave": GUID_1, "indice_csv": {GUID_1: "POZZETTO_1.jpg"}}, "POZZETTO_1.jpg"),
    ("csv-chiave-assente", "csv", "ignorato.jpg",
     {"chiave": GUID_2, "indice_csv": {GUID_1: "POZZETTO_1.jpg"}}, ""),
    ("csv-indice-vuoto", "csv", "ignorato.jpg",
     {"chiave": GUID_1, "indice_csv": {}}, ""),
]


@pytest.mark.parametrize(
    "modalita,token,extra,atteso",
    [c[1:] for c in CASI_NAMING],
    ids=[c[0] for c in CASI_NAMING],
)
def test_naming_per_modalita(modalita, token, extra, atteso):
    assert calcola_nome(
        modalita, token,
        indice=extra.get("indice", 0),
        formula=extra.get("formula", ""),
        chiave=extra.get("chiave", ""),
        indice_csv=extra.get("indice_csv"),
    ) == atteso


def test_le_modalita_sono_tre_e_esclusive():
    assert MODALITA == ("originale", "formula", "csv")
    with pytest.raises(ValueError):
        calcola_nome("inventata", "a.jpg")


def test_multi_valore_si_divide_su_punto_e_virgola_pipe_e_a_capo():
    assert dividi_multivalore("a.jpg;b.jpg|c.png\nd.pdf") == \
        ["a.jpg", "b.jpg", "c.png", "d.pdf"]
    assert dividi_multivalore("  a.jpg ;; b.jpg  ") == ["a.jpg", "b.jpg"]
    assert dividi_multivalore(None) == []
    assert dividi_multivalore("") == []


def test_variabili_formula():
    assert nome_formula("contatore/ACQ_1.jpg", "@stem") == "ACQ_1"
    assert nome_formula("contatore/ACQ_1.jpg", "@ext") == ".jpg"
    assert nome_formula("contatore/ACQ_1.jpg", "@original_name") == "ACQ_1.jpg"
    assert nome_formula("ACQ_1", "@stem@ext") == "ACQ_1"


def test_nome_csv_e_verbatim():
    assert nome_da_csv(GUID_1, {GUID_1: "  Foto d'interno.JPG "}) == "Foto d'interno.JPG"
    assert nome_originale("Foto d'interno.JPG") == "Foto d'interno.JPG"


# ---------------------------------------------------------------------------
# Collisioni e chiave di deduplica (funzioni sole)

def test_suffisso_collisione():
    assert suffisso_collisione("a.jpg", set()) == "a.jpg"
    assert suffisso_collisione("a.jpg", {"a.jpg"}) == "a_2.jpg"
    assert suffisso_collisione("a.jpg", {"a.jpg", "a_2.jpg"}) == "a_3.jpg"
    assert suffisso_collisione("senzaestensione", {"senzaestensione"}) == "senzaestensione_2"
    assert suffisso_collisione("", set()) == ""


def test_chiave_dedup_normalizza_guid_e_nome():
    attesa = "{%s}" % GUID_1.upper()
    assert chiave_dedup(GUID_1, "a.jpg") == (attesa, "a.jpg")
    assert chiave_dedup(GUID_1.lower(), " a.jpg ") == (attesa, "a.jpg")
    assert chiave_dedup("{%s}" % GUID_1.lower(), "a.jpg") == (attesa, "a.jpg")
    assert chiave_dedup(None, "a.jpg") == (None, "a.jpg")


# ---------------------------------------------------------------------------
# Pianificatore su layer finti

def _sorgente(valori_per_feature):
    """Layer sorgente finto con una feature per elemento della lista."""
    campi = [("GLOBALID", "stringa"), ("filefoto", "stringa")]
    feature = [
        crea_feature(campi, {"GLOBALID": guid, "filefoto": valore}, fid=i + 1)
        for i, (guid, valore) in enumerate(valori_per_feature)
    ]
    return crea_layer_sorgente(campi=campi, feature=feature)


def test_pianificatore_originale():
    sorgente = _sorgente([(GUID_1, "SS_0001.jpg;contatore/ACQ_1.jpg")])
    righe = PianificatoreAllegati("originale").righe_da_aggiungere(sorgente)
    assert [r["ATT_NAME"] for r in righe] == ["SS_0001.jpg", "ACQ_1.jpg"]
    assert righe[0]["REL_GLOBALID"] == "{%s}" % GUID_1


def test_pianificatore_formula():
    sorgente = _sorgente([(GUID_1, "SS_0001.jpg")])
    righe = PianificatoreAllegati("formula", formula="@stem_@index@ext").righe_da_aggiungere(sorgente)
    assert [r["ATT_NAME"] for r in righe] == ["SS_0001_1.jpg"]


def test_pianificatore_csv():
    sorgente = _sorgente([(GUID_1, "qualsiasi.jpg"), (GUID_2, "qualsiasi.jpg")])
    pianificatore = PianificatoreAllegati("csv", indice_csv={GUID_1: "POZZETTO_1.jpg"})
    righe = pianificatore.righe_da_aggiungere(sorgente)
    assert [r["ATT_NAME"] for r in righe] == ["POZZETTO_1.jpg"]      # GUID_2 non e' in CSV


def test_nome_vuoto_viene_saltato_e_si_prosegue():
    """Il campo foto vuoto non blocca il lotto (decisione ticket 06)."""
    sorgente = _sorgente([(GUID_1, ""), (GUID_2, "ACQ_2.png")])
    righe = PianificatoreAllegati("originale").righe_da_aggiungere(sorgente)
    assert [r["ATT_NAME"] for r in righe] == ["ACQ_2.png"]


def test_feature_senza_globalid_viene_saltata():
    sorgente = _sorgente([("", "ACQ_2.png"), (GUID_2, "documento.pdf")])
    righe = PianificatoreAllegati("originale").righe_da_aggiungere(sorgente)
    assert [r["ATT_NAME"] for r in righe] == ["documento.pdf"]


def test_collisione_dentro_lo_stesso_lotto():
    """Due token diversi con lo stesso basename: il secondo prende _2."""
    sorgente = _sorgente([(GUID_1, "SS_0001.jpg;contatore/SS_0001.jpg")])
    righe = PianificatoreAllegati("originale").righe_da_aggiungere(sorgente)
    assert [r["ATT_NAME"] for r in righe] == ["SS_0001.jpg", "SS_0001_2.jpg"]


def test_stesso_nome_su_feature_diverse_non_e_collisione():
    """ATT_NAME e' unico per feature: due feature possono avere lo stesso nome."""
    sorgente = _sorgente([(GUID_1, "SS_0001.jpg"), (GUID_2, "SS_0001.jpg")])
    righe = PianificatoreAllegati("originale").righe_da_aggiungere(sorgente)
    assert [r["ATT_NAME"] for r in righe] == ["SS_0001.jpg", "SS_0001.jpg"]
    assert {r["REL_GLOBALID"] for r in righe} == {"{%s}" % GUID_1, "{%s}" % GUID_2}


# ---------------------------------------------------------------------------
# Deduplica contro la tabella allegati finta

def _attach_con(righe):
    allegati = crea_layer_attach()
    for i, (rel, nome) in enumerate(righe, start=1):
        allegati.addFeature(crea_feature(allegati.fields(),
                                         {"REL_GLOBALID": rel, "ATT_NAME": nome}, fid=i))
    return allegati


def test_dedup_salta_la_coppia_gia_presente():
    sorgente = _sorgente([(GUID_1, "SS_0001.jpg"), (GUID_2, "ACQ_2.png")])
    allegati = _attach_con([("{%s}" % GUID_1, "SS_0001.jpg")])

    righe = PianificatoreAllegati("originale").righe_da_aggiungere(
        sorgente, esistenti=chiavi_presenti(allegati))

    assert [r["ATT_NAME"] for r in righe] == ["ACQ_2.png"]


def test_dedup_tollera_guid_minuscolo_e_senza_graffe():
    """La normalizzazione della chiave e' quella dei due script in repo."""
    sorgente = _sorgente([(GUID_1, "SS_0001.jpg")])
    allegati = _attach_con([(GUID_1.lower(), " SS_0001.jpg ")])

    righe = PianificatoreAllegati("originale").righe_da_aggiungere(
        sorgente, esistenti=chiavi_presenti(allegati))

    assert righe == []


def test_dedup_rilancio_completo_non_crea_doppioni():
    """Il caso d'uso della v1: rilanciare lo stesso lavoro non aggiunge nulla."""
    sorgente = _sorgente([
        (GUID_1, "SS_0001.jpg"),
        (GUID_2, "ACQ_2.png;contatore/ACQ_1.jpg"),
    ])
    pianificatore = PianificatoreAllegati("originale")

    primo = pianificatore.righe_da_aggiungere(sorgente)
    allegati = _attach_con([(r["REL_GLOBALID"], r["ATT_NAME"]) for r in primo])
    secondo = PianificatoreAllegati("originale").righe_da_aggiungere(
        sorgente, esistenti=chiavi_presenti(allegati))

    assert [r["ATT_NAME"] for r in primo] == ["SS_0001.jpg", "ACQ_2.png", "ACQ_1.jpg"]
    assert secondo == []


def test_dedup_e_collisione_al_rilancio():
    """Prima esecuzione: collisione risolta con _2. Rilancio: zero doppioni."""
    sorgente = _sorgente([(GUID_1, "SS_0001.jpg;contatore/SS_0001.jpg")])
    primo = PianificatoreAllegati("originale").righe_da_aggiungere(sorgente)
    assert [r["ATT_NAME"] for r in primo] == ["SS_0001.jpg", "SS_0001_2.jpg"]

    allegati = _attach_con([(r["REL_GLOBALID"], r["ATT_NAME"]) for r in primo])
    secondo = PianificatoreAllegati("originale").righe_da_aggiungere(
        sorgente, esistenti=chiavi_presenti(allegati))
    assert secondo == []


def test_dedup_nome_gia_presente_vince_sulla_collisione():
    """Limite noto del naming originale (verbatim): se a monte c'e' 'a.jpg' e nel

    lotto due token danno lo stesso nome, entrambi vengono saltati perche' dalla
    tabella non si sa quale dei due sia allegato. Con la modalita' formula il
    problema non esiste (@index distingue i nomi): caso da verificare a mano su un
    GDB reale (vedi docs/test-strategy.md).
    """
    sorgente = _sorgente([(GUID_1, "SS_0001.jpg;contatore/SS_0001.jpg")])
    allegati = _attach_con([("{%s}" % GUID_1, "SS_0001.jpg")])

    originale = PianificatoreAllegati("originale").righe_da_aggiungere(
        sorgente, esistenti=chiavi_presenti(allegati))
    assert originale == []

    # con la formula i due file restano distinti: nessun nome e' ambigua
    formula = PianificatoreAllegati("formula", formula="@stem_@index@ext").righe_da_aggiungere(
        sorgente, esistenti=chiavi_presenti(allegati))
    assert [r["ATT_NAME"] for r in formula] == ["SS_0001_1.jpg", "SS_0001_2.jpg"]


# ---------------------------------------------------------------------------
# Scrittura vera sulla tabella allegati finta (edit + blob + DATA_SIZE)

MIME = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png",
        ".pdf": "application/pdf"}


def _risolvi(cartella, token):
    """Risolve il token a un file reale, come fa il plugin con la cartella base."""
    candidato = cartella / token
    if candidato.is_file():
        return candidato
    for trovato in sorted(cartella.rglob(os.path.basename(token))):
        return trovato
    return None


def _scrivi_allegati(layer_attach, righe, cartella):
    """Scrive le righe pianificate sulla tabella finta e conta mancanti/saltati."""
    from qgis.PyQt.QtCore import QByteArray
    from qgis.core import QgsFeature, edit

    aggiunti, mancanti = 0, []
    with edit(layer_attach):
        for riga in righe:
            percorso = _risolvi(cartella, riga["token"])
            if percorso is None:
                mancanti.append(riga["token"])
                continue
            contenuto = percorso.read_bytes()
            nuova = QgsFeature(layer_attach.fields())
            nuova["GLOBALID"] = "AABBCCDD-1111-2222-3333-444455556666"
            nuova["REL_GLOBALID"] = riga["REL_GLOBALID"]
            nuova["CONTENT_TYPE"] = MIME.get(percorso.suffix.lower(),
                                             "application/octet-stream")
            nuova["DATA_SIZE"] = len(contenuto)
            nuova["ATT_NAME"] = riga["ATT_NAME"]
            nuova["DATA"] = QByteArray(contenuto)
            assert layer_attach.addFeature(nuova) is True
            aggiunti += 1
    return aggiunti, mancanti


def test_scrittura_sulla_tabella_allegati_finta(cartella_foto):
    sorgente = _sorgente([(GUID_1, "SS_0001.jpg;documento.pdf;manca.jpg")])
    allegati = crea_layer_attach()

    righe = PianificatoreAllegati("originale").righe_da_aggiungere(sorgente)
    aggiunti, mancanti = _scrivi_allegati(allegati, righe, cartella_foto)

    assert aggiunti == 2
    assert mancanti == ["manca.jpg"]
    assert allegati.featureCount() == 2

    righe_scritte = {f["ATT_NAME"]: f for f in allegati.getFeatures()}
    assert set(righe_scritte) == {"SS_0001.jpg", "documento.pdf"}
    foto = righe_scritte["SS_0001.jpg"]
    assert foto["REL_GLOBALID"] == "{%s}" % GUID_1
    assert foto["CONTENT_TYPE"] == "image/jpeg"
    assert bytes(foto["DATA"]) == (cartella_foto / "SS_0001.jpg").read_bytes()
    assert foto["DATA_SIZE"] == len(bytes(foto["DATA"]))
    assert righe_scritte["documento.pdf"]["CONTENT_TYPE"] == "application/pdf"


def test_risoluzione_del_file_in_sottocartella(cartella_foto):
    sorgente = _sorgente([(GUID_1, "contatore/ACQ_1.jpg")])
    allegati = crea_layer_attach()

    righe = PianificatoreAllegati("originale").righe_da_aggiungere(sorgente)
    aggiunti, mancanti = _scrivi_allegati(allegati, righe, cartella_foto)

    assert (aggiunti, mancanti) == (1, [])
    scritta = next(allegati.getFeatures())
    assert scritta["ATT_NAME"] == "ACQ_1.jpg"
    assert scritta["DATA"] == (cartella_foto / "contatore" / "ACQ_1.jpg").read_bytes()
