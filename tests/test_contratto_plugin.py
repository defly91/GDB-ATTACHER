# test_contratto_plugin.py — il contratto v1 verificato sul plugin VERO.
#
# `tests/test_contratto_v1.py` esegue il contratto sull'oracolo (`tests/oracolo_v1.py`)
# perché, quando fu scritto, il pacchetto `gdb_attacher/` viveva in un altro ramo e qui
# non esisteva. Ora esiste: questo modulo ripete gli stessi casi attraversando le
# funzioni reali di `gdb_attacher/core/naming.py`, così il contratto vincola
# l'implementazione e non solo la sua descrizione.
#
# I casi passano dalle stesse porte usate dal wizard (`candidati_da_campi` per le
# modalità originale/formula, `candidati_da_csv` per la modalità csv, `risolvi_collisioni`
# per collisioni e deduplica): niente percorsi privilegiati che l'utente non ha.
#
# Scostamento noto dall'oracolo: l'oracolo prevede "formula vuota → nome originale",
# il plugin la tratta come errore. Nel wizard la formula vuota blocca il passo
# (`PaginaNaming.isComplete`), quindi quello stato non è raggiungibile dall'interfaccia:
# il caso è documentato in fondo al file invece di essere nascosto.

from __future__ import annotations

import os
import sys

import pytest

from fake_qgis import GUID_1, GUID_2

RADICE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if RADICE not in sys.path:
    sys.path.insert(0, RADICE)

from gdb_attacher.core import naming  # noqa: E402
from gdb_attacher.core.attach import chiave_dedup  # noqa: E402

pytestmark = pytest.mark.unit

CAMPO_FOTO = "FOTO"


def risolutore(token):
    """Tutti i token esistono sulla cartella base: la risoluzione file non è oggetto di questi casi."""
    return token


def valutatore_finto(espressione, riga, variabili):
    """Emula QGIS per le sole variabili del contratto (@original_name, @stem, @ext, @index)."""
    testo = str(espressione)
    for nome in sorted(variabili, key=len, reverse=True):  # @index prima di @index_ext
        testo = testo.replace("@" + nome, str(variabili[nome]))
    return testo


def riga(token, id_parent=GUID_1, indice_feature=1):
    return naming.RigaSorgente(
        id_parent=id_parent, campo_foto=CAMPO_FOTO, valore=token, indice_feature=indice_feature,
    )


def nomi(candidati):
    return [c.nome_allegato for c in candidati]


# --------------------------------------------------------------------------- naming
# (id, modalità, valore del campo, extra, atteso) — stessa tabella dell'oracolo.

CASI_NAMING = [
    ("originale-semplice", "originale", "SS_0001.jpg", {}, "SS_0001.jpg"),
    ("originale-senza-estensione", "originale", "SS_0001", {}, "SS_0001"),
    ("originale-con-percorso", "originale", "contatore/ACQ_1.jpg", {}, "ACQ_1.jpg"),
    ("originale-percorso-windows", "originale", r"contatore\ACQ_1.jpg", {}, "ACQ_1.jpg"),
    ("originale-spazi-ai-bordi", "originale", "  ACQ_2.png  ", {}, "ACQ_2.png"),
    ("originale-apice-verbatim", "originale", "foto d'interno.jpg", {}, "foto d'interno.jpg"),
    ("originale-pdf", "originale", "documento.pdf", {}, "documento.pdf"),
    ("formula-stem-index-ext", "formula", "SS_0001.jpg",
     {"formula": "@stem_@index@ext"}, "SS_0001_1.jpg"),
    ("formula-suffisso-copia", "formula", "SS_0001.jpg",
     {"formula": "@stem_copia@ext"}, "SS_0001_copia.jpg"),
    ("formula-original-name", "formula", "ACQ_2.png",
     {"formula": "@original_name"}, "ACQ_2.png"),
]


@pytest.mark.parametrize(
    "modalita,valore,extra,atteso",
    [c[1:] for c in CASI_NAMING],
    ids=[c[0] for c in CASI_NAMING],
)
def test_naming_del_plugin_rispetta_il_contratto(modalita, valore, extra, atteso):
    candidati = naming.candidati_da_campi(
        [riga(valore)], risolutore, modalita,
        espressione=extra.get("formula"),
        valutatore=valutatore_finto if modalita == naming.MODALITA_FORMULA else None,
    )
    assert len(candidati) == 1
    assert candidati[0].stato == "ok"
    assert candidati[0].nome_allegato == atteso


def test_index_e_uno_based_sul_ordine_dei_token():
    """``@index`` conta i token della stessa feature, non le feature."""
    candidati = naming.candidati_da_campi(
        [riga("f1.jpg;f2.jpg;SS_0001.jpg")], risolutore, naming.MODALITA_FORMULA,
        espressione="@index", valutatore=valutatore_finto,
    )
    assert nomi(candidati) == ["1", "2", "3"]


def test_le_modalita_sono_tre_e_candidati_da_campi_ne_accetta_due():
    assert (naming.MODALITA_ORIGINALE, naming.MODALITA_FORMULA, naming.MODALITA_CSV) == \
        ("originale", "formula", "csv")
    with pytest.raises(ValueError):
        naming.candidati_da_campi([riga("a.jpg")], risolutore, "inventata")


def test_multi_valore_si_divide_su_punto_virgola_pipe_e_a_capo():
    candidati = naming.candidati_da_campi(
        [riga("a.jpg;b.jpg|c.png\nd.pdf")], risolutore, naming.MODALITA_ORIGINALE,
    )
    assert nomi(candidati) == ["a.jpg", "b.jpg", "c.png", "d.pdf"]
    assert all(c.stato == "ok" for c in candidati)


def test_token_vuoti_scartati_e_virgola_non_e_separatore():
    """La virgola è esclusa di proposito (rischio prosa nel campo, ticket 06)."""
    candidati = naming.candidati_da_campi(
        [riga("  a.jpg ;; b.jpg  ")], risolutore, naming.MODALITA_ORIGINALE,
    )
    assert nomi(candidati) == ["a.jpg", "b.jpg"]
    singolo = naming.candidati_da_campi(
        [riga("a.jpg, b.jpg")], risolutore, naming.MODALITA_ORIGINALE,
    )
    assert nomi(singolo) == ["a.jpg, b.jpg"]


def test_sentinella_null_e_campo_vuoto_danno_stato_vuoto():
    for valore in (None, "", "NULL", "   "):
        candidati = naming.candidati_da_campi([riga(valore)], risolutore, naming.MODALITA_ORIGINALE)
        assert len(candidati) == 1, valore
        assert candidati[0].stato == "vuoto", valore
        assert not candidati[0].da_scrivere


def test_nome_con_apice_resta_verbatim_anche_in_formula():
    candidati = naming.candidati_da_campi(
        [riga("foto d'interno.jpg")], risolutore, naming.MODALITA_FORMULA,
        espressione="@original_name", valutatore=valutatore_finto,
    )
    assert candidati[0].nome_allegato == "foto d'interno.jpg"


def test_file_non_risolto_non_blocca_ma_finisce_fra_i_mancanti():
    candidati = naming.candidati_da_campi(
        [riga("assente.jpg")], lambda token: "", naming.MODALITA_ORIGINALE,
    )
    assert candidati[0].stato == "missing"
    assert candidati[0].nome_allegato == "assente.jpg"   # nome noto, file no
    assert not candidati[0].da_scrivere


# --------------------------------------------------------------------------- csv
def elenco(righe_csv, colonna_file=CAMPO_FOTO):
    return naming.ElencoCsv(
        percorso="allegati.csv", colonna_file=colonna_file, colonna_chiave="GLOBALID",
        righe=righe_csv,
    )


def test_csv_chiave_trovata_usa_il_nome_indicato_e_tiene_la_forma_verbatim():
    lettura = elenco([naming.RigaCsv(numero=1, chiave=GUID_1,
                                     percorso="POZZETTO_1.jpg", nome="  Foto d'interno.JPG ")])
    candidati = naming.candidati_da_csv(lettura, [riga("x.jpg")], risolutore)
    assert len(candidati) == 1
    assert candidati[0].stato == "ok"
    assert candidati[0].nome_allegato == "Foto d'interno.JPG"


def test_csv_senza_nome_ricade_sul_nome_del_file():
    lettura = elenco([naming.RigaCsv(numero=1, chiave=GUID_1, percorso="POZZETTO_1.jpg", nome="")])
    candidati = naming.candidati_da_csv(lettura, [riga("x.jpg")], risolutore)
    assert candidati[0].nome_allegato == "POZZETTO_1.jpg"


def test_csv_con_chiave_assente_dal_layer_non_blocca():
    """Chiave del CSV non presente nel layer: candidato contato come chiave ignota."""
    lettura = elenco([naming.RigaCsv(numero=1, chiave=GUID_2,
                                     percorso="POZZETTO_1.jpg", nome="POZZETTO_1.jpg")])
    candidati = naming.candidati_da_csv(lettura, [riga("x.jpg")], risolutore)
    assert candidati[0].stato == "chiave_ignota"
    assert candidati[0].nome_allegato == ""


def test_csv_vuoto_non_produce_candidati():
    assert naming.candidati_da_csv(elenco([]), [riga("x.jpg")], risolutore) == []


def test_csv_file_non_trovato_finisce_fra_i_mancanti():
    lettura = elenco([naming.RigaCsv(numero=1, chiave=GUID_1,
                                     percorso="assente.jpg", nome="assente.jpg")])
    candidati = naming.candidati_da_csv(lettura, [riga("x.jpg")], lambda token: "")
    assert candidati[0].stato == "file_ignoto"


# ------------------------------------------------------- collisioni e deduplica
def test_collisione_dentro_il_lotto_rinomina_con_suffisso_prima_dell_estensione():
    candidati = naming.candidati_da_campi(
        [riga("IMG.jpg;IMG.jpg")], risolutore, naming.MODALITA_ORIGINALE,
    )
    esito = naming.risolvi_collisioni(candidati)
    assert nomi(esito) == ["IMG.jpg", "IMG_2.jpg"]
    assert [c.stato for c in esito] == ["ok", "collisione"]


def test_dedup_idempotente_contro_la_tabella_allegati():
    """Rilanciare lo stesso lavoro non duplica: la coppia già presente non si riscrive."""
    candidati = naming.candidati_da_campi(
        [riga("IMG.jpg")], risolutore, naming.MODALITA_ORIGINALE,
    )
    esistenti = [chiave_dedup(GUID_1, "IMG.jpg")]
    esito = naming.risolvi_collisioni(candidati, esistenti=esistenti)
    assert esito[0].stato == "duplicato"
    assert not esito[0].da_scrivere


def test_dedup_su_guidata_con_graffe_o_case_diverso_non_e_un_doppione():
    candidati = naming.candidati_da_campi(
        [riga("IMG.jpg")], risolutore, naming.MODALITA_ORIGINALE,
    )
    esistenti = [chiave_dedup("{" + GUID_1.lower() + "}", "IMG.jpg")]
    esito = naming.risolvi_collisioni(candidati, esistenti=esistenti)
    assert esito[0].stato == "duplicato"


def test_rinomina_esistente_su_richiesta_usa_il_suffisso():
    candidati = naming.candidati_da_campi(
        [riga("IMG.jpg")], risolutore, naming.MODALITA_ORIGINALE,
    )
    esistenti = [chiave_dedup(GUID_1, "IMG.jpg")]
    esito = naming.risolvi_collisioni(candidati, esistenti=esistenti, rinomina_se_esistente=True)
    assert esito[0].nome_allegato == "IMG_2.jpg"
    assert esito[0].stato == "collisione"


def test_due_feature_diverse_possono_avere_lo_stesso_nome():
    """La chiave è la coppia: stesso nome su feature diverse non collide."""
    candidati = naming.candidati_da_campi(
        [riga("IMG.jpg", id_parent=GUID_1), riga("IMG.jpg", id_parent=GUID_2)],
        risolutore, naming.MODALITA_ORIGINALE,
    )
    esito = naming.risolvi_collisioni(candidati)
    assert nomi(esito) == ["IMG.jpg", "IMG.jpg"]
    assert all(c.stato == "ok" for c in esito)


# ------------------------------------------------------- scostamento documentato
def test_formula_vuota_e_un_errore_non_un_ripiego_sul_nome_originale():
    """Divergenza consapevole dall'oracolo.

    L'oracolo prevede che, con modalità formula e formula vuota, si ricada sul nome
    originale. Nel plugin non esiste quel ripiego: la formula vuota produce stato
    ``errore``. Non è un caso raggiungibile dall'interfaccia, perché il passo del
    naming blocca l'avanzamento finché la formula è vuota (`PaginaNaming.isComplete`)
    e il wizard non permette di arrivare all'esecuzione in quello stato. Il test fissa
    il comportamento reale, così se un domani il ripiego venisse implementato questo
    test fallisce e la divergenza torna a essere una decisione, non un dettaglio.
    """
    candidati = naming.candidati_da_campi(
        [riga("documento.pdf")], risolutore, naming.MODALITA_FORMULA,
        espressione="", valutatore=valutatore_finto,
    )
    assert candidati[0].stato == "errore"
    assert candidati[0].motivo == "formula vuota"


def test_formula_mode_senza_valutatore_e_un_errore_di_programmazione():
    with pytest.raises(ValueError):
        naming.candidati_da_campi([riga("a.jpg")], risolutore, naming.MODALITA_FORMULA)
