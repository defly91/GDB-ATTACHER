# -*- coding: utf-8 -*-
"""Test di logica pura sull'euristica di discovery (``core/discovery.py``).

I verdetti del ticket 05 recepiti qui sono quattro: la cartella base alza il livello
(A vs B/C), i nulli arrivano come sentinella e non come ``None``, un token con spazi
vale solo se il file esiste, il nome del campo suggerisce ma non decide.

Niente QGIS: il tipo del campo è iniettato con ``tipo_fn``, i layer sono finti.
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from gdb_attacher.core import discovery  # noqa: E402


# ---------------------------------------------------------------- finte


class _Campo:
    def __init__(self, nome, tipo="stringa"):
        self._nome = nome
        self.tipo = tipo

    def name(self):
        return self._nome


class _Feature(dict):
    """Feature finta: ``feat["CAMPO"]`` come in PyQGIS."""


class _Layer:
    def __init__(self, campi, features):
        self._campi = campi
        self._features = features

    def fields(self):
        return list(self._campi)

    def getFeatures(self):  # noqa: N802 — nome dell'API QGIS
        return list(self._features)


def _layer(valori_per_campo, tipi=None):
    """Costruisce un layer finto da ``{campo: [valori]}``."""
    tipi = tipi or {}
    nomi = list(valori_per_campo)
    lunghezza = max((len(v) for v in valori_per_campo.values()), default=0)
    features = []
    for i in range(lunghezza):
        feature = _Feature()
        for nome in nomi:
            valori = valori_per_campo[nome]
            feature[nome] = valori[i] if i < len(valori) else None
        features.append(feature)
    campi = [_Campo(nome, tipi.get(nome, "stringa")) for nome in nomi]
    return _Layer(campi, features)


def _tipo(campo):
    return campo.tipo


def _punteggio(righe, campo):
    return next(r for r in righe if r.campo == campo)


# ---------------------------------------------------------------- cartella base


@pytest.fixture()
def cartella(tmp_path):
    """Cartella base con foto vere, anche in sottocartella, anche senza estensione."""
    (tmp_path / "foto1.jpg").write_bytes(b"x")
    (tmp_path / "foto2.jpg").write_bytes(b"x")
    (tmp_path / "SS_0001.jpg").write_bytes(b"x")
    sottocartella = tmp_path / "contatore"
    sottocartella.mkdir()
    (sottocartella / "ACQ_1.jpg").write_bytes(b"x")
    return str(tmp_path)


def test_livello_a_senza_cartella_base_non_esiste(cartella):
    """Verdetto 1 del ticket 05: senza cartella base la discovery perde il livello A."""
    layer = _layer({"foto_impianto": ["SS_0001", "SS_0001"]})

    senza = discovery.suggerisci_campi(layer, None, tipo_fn=_tipo)
    assert _punteggio(senza, "foto_impianto").livello in ("C", "D")

    con = discovery.suggerisci_campi(layer, cartella, tipo_fn=_tipo)
    riga = _punteggio(con, "foto_impianto")
    assert riga.livello == "A"
    assert riga.n_esistenti == 2
    assert riga.preselezionato is True


def test_livello_b_estensioni_senza_verifica_su_disco():
    layer = _layer({"filefoto": ["a.jpg", "b.pdf"]})
    riga = _punteggio(discovery.suggerisci_campi(layer, tipo_fn=_tipo), "filefoto")
    assert riga.livello == "B"
    assert riga.ext_rate == 1.0 and riga.esiste_rate == 0.0
    assert riga.preselezionato is True


def test_livello_c_solo_il_nome():
    """``foto_note``: nome sospetto, valori prosa → mostrato ma non preselezionato."""
    layer = _layer({"foto_note": ["vedi cartello", "controllare"]})
    riga = _punteggio(discovery.suggerisci_campi(layer, tipo_fn=_tipo), "foto_note")
    assert riga.livello == "C"
    assert riga.nome_match is True
    assert riga.preselezionato is False


def test_livello_d_per_tipo_non_testuale():
    layer = _layer({"foto_binaria": ["x", "y"]}, tipi={"foto_binaria": "blob"})
    riga = _punteggio(discovery.suggerisci_campi(layer, tipo_fn=_tipo), "foto_binaria")
    assert riga.livello == "D"


def test_livello_d_per_valori_guid_numerici_e_url():
    """I segnali di scarto vincono sul nome: ``link_foto``/``id_foto`` non passano."""
    layer = _layer({
        "GLOBALID": ["{8aa1f6c0-0000-0000-0000-000000000001}",
                     "{8aa1f6c0-0000-0000-0000-000000000002}"],
        "id_foto": ["1", "2"],
        "link_foto": ["https://x/y.jpg", "https://x/z.jpg"],
    })
    righe = discovery.suggerisci_campi(layer, tipo_fn=_tipo)
    assert _punteggio(righe, "GLOBALID").livello == "D"
    assert "GUID" in _punteggio(righe, "GLOBALID").motivo
    assert _punteggio(righe, "id_foto").livello == "D"
    assert _punteggio(righe, "link_foto").livello == "D"


def test_none_e_vuoti_non_alzano_il_livello():
    """Verdetto 3: i nulli arrivano come sentinella; un campo tutto nullo resta D."""
    layer = _layer({"foto_archiviata": [None, "", None],
                    "foto_piena": ["foto1.jpg", "foto2.jpg"]}, tipi={})
    righe = discovery.suggerisci_campi(layer, tipo_fn=_tipo)
    vuoto = _punteggio(righe, "foto_archiviata")
    assert vuoto.n_non_null == 0 and vuoto.livello == "D"


def test_multivalore_separato_da_punto_e_virgola(cartella):
    layer = _layer({"foto_est": ["foto1.jpg;foto2.jpg", "foto1.jpg|foto2.jpg"]})
    riga = _punteggio(discovery.suggerisci_campi(layer, cartella, tipo_fn=_tipo), "foto_est")
    assert riga.livello == "A"
    assert riga.multi_rate == 1.0
    assert "multipli" in riga.motivo


def test_la_virgola_non_e_un_separatore(cartella):
    """Verdetto 6: ``;`` sì, ``,`` no (rischio prosa)."""
    layer = _layer({"foto_est": ["foto1.jpg,foto2.jpg"]})
    riga = _punteggio(discovery.suggerisci_campi(layer, cartella, tipo_fn=_tipo), "foto_est")
    assert riga.multi_rate == 0.0


def test_token_con_spazi_vale_solo_se_il_file_esiste(cartella):
    """Verdetto 4: «vedi foto pianta.jpg» è prosa finché quel nome non esiste davvero."""
    prosa = _layer({"descrizione": ["vedi foto pianta.jpg", "vedi foto pianta.jpg"]})
    riga = _punteggio(discovery.suggerisci_campi(prosa, cartella, tipo_fn=_tipo), "descrizione")
    assert riga.ext_rate == 0.0
    assert riga.livello == "D"

    percorso = os.path.join(cartella, "vedi foto pianta.jpg")
    with open(percorso, "wb") as flusso:
        flusso.write(b"x")
    try:
        riga = _punteggio(discovery.suggerisci_campi(prosa, cartella, tipo_fn=_tipo), "descrizione")
        assert riga.livello == "A"
    finally:
        os.remove(percorso)


def test_percorso_assoluto_con_spazi_vale_anche_senza_cartella_base(tmp_path):
    """Difetto trovato sul campo: un campo con un percorso assoluto **con spazi** spariva.

    Il valore reale era ``Creator = C:\\Users\\...\\WhatsApp Image 2026-09-15 at 13.06.13.jpeg``.
    Senza cartella base l'indice era ``None``, il token con spazi veniva scartato e il campo
    finiva in **D** (livello nascosto: nessun modo di sapere perché, né di sceglierlo a
    mano). Con la cartella base invece era livello A: discovery e scrittura vedevano cose
    diverse sugli stessi valori.
    """
    foto = tmp_path / "WhatsApp Image 2026-09-15 at 13.06.13.jpeg"
    foto.write_bytes(b"x")
    layer = _layer({"Creator": [str(foto), str(foto)]})

    riga = _punteggio(discovery.suggerisci_campi(layer, None, tipo_fn=_tipo), "Creator")
    assert riga.livello == "A"
    assert riga.n_esistenti == 2
    assert riga.ext_rate == 1.0 and riga.esiste_rate == 1.0

    # Con una cartella base qualsiasi il verdetto non cambia: il percorso è già completo.
    con_base = _punteggio(discovery.suggerisci_campi(layer, str(tmp_path), tipo_fn=_tipo),
                          "Creator")
    assert (con_base.livello, con_base.n_esistenti) == ("A", 2)


def test_percorso_assoluto_inesistente_con_spazi_resta_escluso(tmp_path):
    """La protezione dalla prosa resta: un percorso che non esiste non è un campo foto."""
    layer = _layer({"Creator": [r"C:\Foto\la mia foto.jpg", r"C:\Foto\la mia foto.jpg"]})

    riga = _punteggio(discovery.suggerisci_campi(layer, None, tipo_fn=_tipo), "Creator")
    assert riga.livello == "D"
    assert riga.n_esistenti == 0


def test_sottocartelle_e_percorsi_relativi(cartella):
    layer = _layer({"foto_contatore": ["contatore/ACQ_1.jpg", "ACQ_1.jpg"]})
    riga = _punteggio(discovery.suggerisci_campi(layer, cartella, tipo_fn=_tipo), "foto_contatore")
    assert riga.livello == "A"
    assert riga.n_esistenti == 2


# ---------------------------------------------------------------- risolutore


def test_risolutore_file_cascata(tmp_path):
    (tmp_path / "foto.jpg").write_bytes(b"x")
    sottocartella = tmp_path / "sotto"
    sottocartella.mkdir()
    (sottocartella / "ACQ_1.jpg").write_bytes(b"x")
    risolvi = discovery.risolutore_file(str(tmp_path))

    assert risolvi("foto.jpg") == str(tmp_path / "foto.jpg")
    assert risolvi("ACQ_1.jpg") == str(sottocartella / "ACQ_1.jpg")   # basename indicizzato
    assert risolvi("sotto/ACQ_1.jpg") == str(sottocartella / "ACQ_1.jpg")
    assert risolvi("manca.jpg") == ""
    # percorso assoluto esistente
    assoluto = str(tmp_path / "foto.jpg")
    assert risolvi(assoluto) == assoluto
    # URL remoti non si risolvono
    assert risolvi("https://x/y.jpg") == ""


def test_risolutore_senza_cartella_base(tmp_path):
    """Senza cartella base si risolvono solo i percorsi assoluti esistenti."""
    percorso = tmp_path / "foto.jpg"
    percorso.write_bytes(b"x")
    risolvi = discovery.risolutore_file(None)
    assert risolvi(str(percorso)) == str(percorso)
    assert risolvi("foto.jpg") == ""


def test_cache_dell_indice_evita_riscansioni(tmp_path):
    (tmp_path / "a.jpg").write_bytes(b"x")
    discovery.IndiceFile.pulisci_cache()
    primo = discovery.risolutore_file(str(tmp_path))
    secondo = discovery.risolutore_file(str(tmp_path))
    assert discovery.IndiceFile._cache
    assert primo("a.jpg") == secondo("a.jpg") == str(tmp_path / "a.jpg")
    discovery.IndiceFile.pulisci_cache()
    assert not discovery.IndiceFile._cache


# ---------------------------------------------------------------- selezione/ordine


def test_fid_escluso_di_default(cartella):
    layer = _layer({"fid": ["1", "2"], "foto_a": ["foto1.jpg", "foto2.jpg"]})
    campi = [r.campo for r in discovery.suggerisci_campi(layer, cartella, tipo_fn=_tipo)]
    assert "fid" not in campi
    campi = [r.campo for r in discovery.suggerisci_campi(layer, cartella, tipo_fn=_tipo,
                                                         escludi_fid=False)]
    assert "fid" in campi


def test_le_righe_sono_ordinate_per_livello(cartella):
    layer = _layer({
        "foto_vera": ["foto1.jpg", "foto2.jpg"],
        "foto_ext": ["x.jpg", "y.jpg"],
        "foto_note": ["prosa", "prosa"],
        "fid": ["1", "2"],
    })
    righe = discovery.suggerisci_campi(layer, cartella, tipo_fn=_tipo)
    livelli = [r.livello for r in righe]
    assert livelli == sorted(livelli, key=lambda l: discovery.LIVELLI.index(l))


def test_riassunto_preseleziona_a_e_b(cartella):
    layer = _layer({"foto_vera": ["foto1.jpg", "foto2.jpg"],
                    "foto_ext": ["x.jpg", "y.jpg"],
                    "foto_note": ["prosa", "prosa"]})
    riassunto = discovery.riassunto(discovery.suggerisci_campi(layer, cartella, tipo_fn=_tipo))
    assert "foto_vera" in riassunto["preselezionati"]
    assert "foto_ext" in riassunto["preselezionati"]
    assert riassunto["da_rivedere"] == ["foto_note"]


def test_campione_massimo_di_feature(tmp_path):
    """``max_feature`` limita la lettura: su GDB grandi la discovery non si blocca."""
    layer = _layer({"foto": [f"f{i}.jpg" for i in range(50)]})
    righe = discovery.suggerisci_campi(layer, None, max_feature=10, tipo_fn=_tipo)
    assert _punteggio(righe, "foto").n_valori == 10


def test_soglia_e_livelli_dichiarati():
    assert discovery.SOGLIA == 0.5
    assert discovery.LIVELLI == ("A", "B", "C", "D")
