# test_prototipo_discovery.py — il finto QGIS contro codice vero del repo.
#
# I prototipi in prototype/ sono l'unico codice eseguibile oggi in questo ramo.
# `prototype/05-field-discovery/suggerisci_campi.py` usa PyQGIS solo per leggere
# campi e feature, quindi con il finto QGIS gira davvero: questi test servono a
# dimostrare che l'impalcatura regge codice vero (import, campi, NULL, QMetaType,
# valori per campo) e in piu' fissano i livelli di discovery attesi sui casi
# sintetici (guid, numerico, campo foto con file reali, prosa).
#
# Non e' un test del plugin: e' un test di integrazione tra i fake e il prototipo.

from __future__ import annotations

from pathlib import Path

import pytest

from fake_qgis import GUID_1, crea_feature, crea_layer_sorgente

pytestmark = pytest.mark.unit

RADICE = Path(__file__).resolve().parent.parent
PROTOTIPO = RADICE / "prototype" / "05-field-discovery" / "suggerisci_campi.py"

pytestmark = [
    pytest.mark.unit,
    pytest.mark.skipif(not PROTOTIPO.is_file(),
                       reason="prototype/05-field-discovery/suggerisci_campi.py assente"),
]


@pytest.fixture
def suggerisci_campi(carica_modulo):
    """La funzione `suggerisci_campi` del prototipo ticket 05."""
    return carica_modulo(str(PROTOTIPO), nome_modulo="prototipo_suggerisci_campi")


def _layer():
    """Campi e valori scelti per coprire i livelli A, C e D dell'euristica."""
    campi = [
        ("GLOBALID", "stringa"),
        ("filefoto", "stringa"),
        ("note", "stringa"),
        ("quota", "numerico"),
        ("percorso_allegato", "stringa"),
    ]
    feature = [
        crea_feature(campi, {
            "GLOBALID": GUID_1,
            "filefoto": "SS_0001.jpg",
            "note": "controllare la foto SS_0001.jpg mancante nel rilievo",
            "quota": 12.5,
            "percorso_allegato": "contatore/ACQ_1.jpg",
        }),
        crea_feature(campi, {
            "GLOBALID": "1A2B3C4D-5E6F-7081-92A3-B4C5D6E7F809",
            "filefoto": "ACQ_2.png",
            "note": "secondo pozzetto",
            "quota": 13.0,
            "percorso_allegato": "documento.pdf",
        }, fid=2),
    ]
    return crea_layer_sorgente(campi=campi, feature=feature)


def test_il_prototipo_gira_sul_finto_qgis(suggerisci_campi):
    righe = suggerisci_campi.suggerisci_campi(_layer())
    nomi = [r.campo for r in righe]
    assert set(nomi) == {"GLOBALID", "filefoto", "note", "quota", "percorso_allegato"}
    assert all(r.livello in "ABCD" for r in righe)


def test_discovery_senza_cartella_base_non_promuove_a_livello_a(suggerisci_campi):
    """Senza cartella base vale solo la sintassi: nessun campo puo' essere livello A."""
    righe = suggerisci_campi.suggerisci_campi(_layer())
    assert [r.campo for r in righe if r.livello == "A"] == []


def test_discovery_con_cartella_base_trova_il_campo_foto(suggerisci_campi, cartella_foto):
    righe = suggerisci_campi.suggerisci_campi(_layer(), cartella_base=str(cartella_foto))
    per_campo = {r.campo: r for r in righe}

    foto = per_campo["filefoto"]
    assert foto.livello == "A"                    # file trovati in cartella_foto
    assert foto.esiste_rate == 1.0

    allegato = per_campo["percorso_allegato"]
    assert allegato.livello in ("A", "B")

    assert per_campo["quota"].livello == "D"      # numerico: scartato
    assert per_campo["GLOBALID"].livello == "D"   # GUID: scartato
    assert "GUID" in per_campo["GLOBALID"].motivo

    preselezionati = suggerisci_campi.riassunto(righe)["preselezionati"]
    assert "filefoto" in preselezionati
    assert "GLOBALID" not in preselezionati
    assert "quota" not in preselezionati


def test_discovery_ordina_per_livello(suggerisci_campi):
    righe = suggerisci_campi.suggerisci_campi(_layer())
    livelli = [r.livello for r in righe]
    assert livelli == sorted(livelli, key="ABCD".index)


def test_campo_vuoto_non_sfonda_la_divisione_per_zero(suggerisci_campi):
    """Campo foto tutto nullo: rate a 0, nessuna eccezione (le feature finte NON

    valorizzano i campi -> NULL, come fa QGIS con i campi non popolati).
    """
    campi = [("GLOBALID", "stringa"), ("filefoto", "stringa")]
    feature = [crea_feature(campi, {"GLOBALID": GUID_1})]
    righe = suggerisci_campi.suggerisci_campi(crea_layer_sorgente(campi=campi, feature=feature))
    foto = {r.campo: r for r in righe}["filefoto"]
    assert foto.n_non_null == 0
    assert foto.esiste_rate == 0.0
    assert foto.livello == "D"
