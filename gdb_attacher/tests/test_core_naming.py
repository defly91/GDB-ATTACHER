# -*- coding: utf-8 -*-
"""Test di logica pura su ``core/naming.py``: le tre modalità del ticket 06.

Coperti: multi-valore, variabili di formula, nome originale, formula con valutatore
iniettato, CSV (delimitatori, codifiche, colonne, chiavi), collisioni con suffisso,
deduplica degli allegati già presenti, nomi vuoti che saltano senza fermare il batch.
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from gdb_attacher.core import attach, discovery, naming  # noqa: E402


# ---------------------------------------------------------------- strumenti


def _risolutore(percorsi):
    """Risolutore finto: token → percorso, come ``discovery.risolutore_file``."""
    def _risolvi(token):
        return percorsi.get(token, "")
    return _risolvi


def _riga(id_parent, valore, campo="FILEFOTO", indice=1):
    return naming.RigaSorgente(id_parent=id_parent, campo_foto=campo, valore=valore,
                               indice_feature=indice)


def _percorso_finto(nome):
    return os.path.join("/finta", "cartella", nome)


# ---------------------------------------------------------------- multi-valore


@pytest.mark.parametrize("valore,atteso", [
    ("a.jpg;b.jpg", ["a.jpg", "b.jpg"]),
    ("a.jpg|b.jpg", ["a.jpg", "b.jpg"]),
    ("a.jpg\nb.jpg", ["a.jpg", "b.jpg"]),
    ("a.jpg, b.jpg", ["a.jpg, b.jpg"]),          # la virgola NON separa (ticket 06)
    ('"a.jpg"; b.jpg', ["a.jpg", "b.jpg"]),      # apici di contenimento tolti
    ("  a.jpg ; ; b.jpg ", ["a.jpg", "b.jpg"]),  # token vuoti scartati
    ("", []),
    ("   ", []),
    (None, []),
    ("NULL", []),                                 # sentinella QGIS
])
def test_dividi_multivalore(valore, atteso):
    assert naming.dividi_multivalore(valore) == atteso


def test_nome_da_percorso_e_suffisso():
    assert naming.nome_da_percorso("contatore/ACQ_1.jpg") == "ACQ_1.jpg"
    assert naming.nome_da_percorso(r"C:\Foto\ACQ_1.jpg") == "ACQ_1.jpg"
    assert naming.nome_da_percorso("") == ""
    assert naming.con_suffisso("foto.jpg", 2) == "foto_2.jpg"
    assert naming.con_suffisso("foto", 3) == "foto_3"
    assert naming.con_suffisso("archivio.tar.gz", 2) == "archivio.tar_2.gz"


def test_variabili_nome():
    variabili = naming.variabili_nome("contatore/ACQ_1.jpg", 2)
    assert variabili == {"original_name": "ACQ_1.jpg", "stem": "ACQ_1",
                         "ext": ".jpg", "index": 2}
    assert naming.variabili_nome("senza_estensione", 1)["ext"] == ""
    assert naming.VARIABILI_FORMULA == ("original_name", "stem", "ext", "index")


GUID_A = "{8AA1F6C0-1111-2222-3333-444455556666}"


def test_normalizza_chiave():
    """Chiave GUID normalizzata (graffe/case), chiave generica ripulita e basta.

    Il ``case`` vale per il GUID (default del ticket 06): ``{8aa1...}`` e
    ``8AA1...`` sono la stessa chiave. Per una chiave generica il confronto è esatto.
    """
    assert naming.normalizza_chiave(GUID_A) == "8AA1F6C0-1111-2222-3333-444455556666"
    assert naming.normalizza_chiave(GUID_A.lower()) == naming.normalizza_chiave(GUID_A)
    assert naming.normalizza_chiave("  codice1 ") == "codice1"
    assert naming.normalizza_chiave("codice1") != naming.normalizza_chiave("CODICE1")
    assert naming.normalizza_chiave(None) == ""


# ---------------------------------------------------------------- modalità originale


def test_modalita_originale_nome_verbatim():
    risolutore = _risolutore({"a.jpg": _percorso_finto("a.jpg"),
                              "contatore/ACQ_1.jpg": _percorso_finto("ACQ_1.jpg")})
    candidati = naming.candidati_da_campi([_riga("{A}", "a.jpg;contatore/ACQ_1.jpg")], risolutore)

    assert [c.nome_allegato for c in candidati] == ["a.jpg", "ACQ_1.jpg"]
    assert [c.indice_token for c in candidati] == [1, 2]
    assert all(c.stato == "ok" for c in candidati)
    # il nome viene dal file risolto, non dal valore del campo
    assert candidati[1].token == "contatore/ACQ_1.jpg"
    assert candidati[1].percorso_file == _percorso_finto("ACQ_1.jpg")


def test_file_mancante_salta_ma_non_trascina_gli_altri():
    """Ticket 06: i token sono indipendenti, uno mancante non ferma gli altri."""
    risolutore = _risolutore({"a.jpg": _percorso_finto("a.jpg")})
    candidati = naming.candidati_da_campi([_riga("{A}", "a.jpg;manca.jpg;b.jpg")], risolutore)
    stati = {c.token: c.stato for c in candidati}
    assert stati == {"a.jpg": "ok", "manca.jpg": "missing", "b.jpg": "missing"}
    assert candidati[1].nome_originale == "manca.jpg"


def test_campo_vuoto_produce_una_riga_saltata():
    candidati = naming.candidati_da_campi([_riga("{A}", "")], _risolutore({}))
    assert len(candidati) == 1
    assert candidati[0].stato == "vuoto"
    assert candidati[0].nome_allegato == ""


def test_una_riga_per_campo_foto_galleria():
    """Più campi foto = più allegati sulla stessa feature, in un solo giro."""
    risolutore = _risolutore({"a.jpg": _percorso_finto("a.jpg"),
                              "b.jpg": _percorso_finto("b.jpg")})
    righe = [_riga("{A}", "a.jpg", campo="FOTO_EST"),
             _riga("{A}", "b.jpg", campo="FOTO_INT")]
    candidati = naming.candidati_da_campi(righe, risolutore)
    assert [c.campo_foto for c in candidati] == ["FOTO_EST", "FOTO_INT"]
    assert naming.conteggi_per_campo(candidati) == {"FOTO_EST": 1, "FOTO_INT": 1}


def test_modalita_non_gestita():
    with pytest.raises(ValueError):
        naming.candidati_da_campi([_riga("{A}", "a.jpg")], _risolutore({}),
                                  modalita=naming.MODALITA_CSV)


# ---------------------------------------------------------------- modalità formula


def test_formula_riceve_variabili_e_campi():
    """Il valutatore è iniettato: la formula la valuta QGIS, qui si controlla il resto."""
    risolutore = _risolutore({"a.jpg": _percorso_finto("a.jpg"),
                              "b.png": _percorso_finto("b.png")})
    ricevute = []

    def valutatore(espressione, riga, variabili):
        ricevute.append((espressione, riga.id_parent, dict(variabili)))
        return f'{variabili["stem"]}_{variabili["index"]}{variabili["ext"]}'

    candidati = naming.candidati_da_campi(
        [_riga("{A}", "a.jpg;b.png")], risolutore,
        modalita=naming.MODALITA_FORMULA, espressione='@stem || "CODICE"',
        valutatore=valutatore,
    )
    assert [c.nome_allegato for c in candidati] == ["a_1.jpg", "b_2.png"]
    assert ricevute[0][0] == '@stem || "CODICE"'
    assert ricevute[1][2]["index"] == 2
    assert ricevute[1][2]["original_name"] == "b.png"


def test_formula_che_produce_nome_vuoto_salta_e_prosegue():
    risolutore = _risolutore({"a.jpg": _percorso_finto("a.jpg"),
                              "b.jpg": _percorso_finto("b.jpg")})

    def valutatore(espressione, riga, variabili):
        return "" if variabili["stem"] == "a" else "@stem@ext"

    candidati = naming.candidati_da_campi(
        [_riga("{A}", "a.jpg"), _riga("{B}", "b.jpg")], risolutore,
        modalita=naming.MODALITA_FORMULA, espressione="@stem", valutatore=valutatore,
    )
    assert [c.stato for c in candidati] == ["salta", "ok"]
    assert candidati[0].motivo
    assert naming.conteggi(candidati)["saltati"] == 1


def test_formula_rotta_finisce_nel_report_senza_fermare_il_batch():
    risolutore = _risolutore({"a.jpg": _percorso_finto("a.jpg"),
                              "b.jpg": _percorso_finto("b.jpg")})

    def valutatore(espressione, riga, variabili):
        if variabili["stem"] == "a":
            raise ValueError("attributo sconosciuto: CODICE")
        return "b@ext"

    candidati = naming.candidati_da_campi(
        [_riga("{A}", "a.jpg"), _riga("{B}", "b.jpg")], risolutore,
        modalita=naming.MODALITA_FORMULA, espressione="@stem", valutatore=valutatore,
    )
    assert [c.stato for c in candidati] == ["errore", "ok"]
    assert "attributo sconosciuto" in candidati[0].motivo


def test_formula_vuota_finisce_nel_report():
    """Una formula vuota è già bloccata dal wizard; qui non fa cadere il batch."""
    candidati = naming.candidati_da_campi([_riga("{A}", "a.jpg")], _risolutore({}),
                                          modalita=naming.MODALITA_FORMULA, espressione="",
                                          valutatore=lambda *a: "x")
    assert candidati[0].stato == "errore"
    assert candidati[0].motivo == "formula vuota"


def test_valutatore_qgis_non_esiste_fuori_da_qgis():
    """``verifica_formula`` non deve esplodere: fuori da QGIS ritorna un avviso."""
    errore, avviso = naming.verifica_formula('@stem || "CODICE"', None)
    assert errore == ""
    assert "non disponibile" in avviso
    errore, avviso = naming.verifica_formula("", None)
    assert errore == "formula vuota"


# ---------------------------------------------------------------- collisioni / dedup


def _candidato(id_parent, nome, stato="ok"):
    return naming.CandidatoAllegato(id_parent=id_parent, campo_foto="FILEFOTO",
                                    valore_campo=nome, token=nome, percorso_file=_percorso_finto(nome),
                                    nome_allegato=nome, nome_originale=nome,
                                    indice_token=1, indice_feature=1, stato=stato)


def test_collisione_dentro_il_lotto_suffisso_2():
    """Ticket 06: il primo tiene il nome pulito, il secondo prende ``_2``."""
    candidati = naming.risolvi_collisioni(
        [_candidato("{A}", "foto.jpg"), _candidato("{A}", "foto.jpg")], set()
    )
    assert [c.nome_allegato for c in candidati] == ["foto.jpg", "foto_2.jpg"]
    assert [c.stato for c in candidati] == ["ok", "collisione"]
    assert candidati[1].nome_originale == "foto.jpg"


def test_collisione_tre_volte():
    candidati = naming.risolvi_collisioni(
        [_candidato("{A}", "foto.jpg"), _candidato("{A}", "foto.jpg"),
         _candidato("{A}", "foto.jpg")], set()
    )
    assert [c.nome_allegato for c in candidati] == ["foto.jpg", "foto_2.jpg", "foto_3.jpg"]


def test_allegato_gia_presente_viene_saltato():
    """Dedup/idempotenza: rilanciare lo stesso batch non duplica nulla."""
    esistenti = {attach.chiave_dedup("{A}", "foto.jpg")}
    candidati = naming.risolvi_collisioni([_candidato("{A}", "foto.jpg")], esistenti)
    assert candidati[0].stato == "duplicato"
    assert candidati[0].nome_allegato == "foto.jpg"
    assert "già presente" in candidati[0].motivo


def test_allegato_gia_presente_con_option_rinomina():
    """La regola del suffisso resta disponibile (scelta esplicita dell'utente)."""
    esistenti = {attach.chiave_dedup("{a}", "foto.jpg")}
    candidati = naming.risolvi_collisioni([_candidato("{A}", "foto.jpg")], esistenti,
                                          rinomina_se_esistente=True)
    assert candidati[0].stato == "collisione"
    assert candidati[0].nome_allegato == "foto_2.jpg"


def test_il_guid_parent_e_normalizzato_nella_dedup():
    """Stesso allegato scritto con o senza graffe/case resta lo stesso allegato."""
    esistenti = {attach.chiave_dedup("AbC", "foto.jpg")}
    candidati = naming.risolvi_collisioni([_candidato("{abc}", "foto.jpg")], esistenti)
    assert candidati[0].stato == "duplicato"


def test_feature_diverse_non_collidono():
    candidati = naming.risolvi_collisioni(
        [_candidato("{A}", "foto.jpg"), _candidato("{B}", "foto.jpg")], set()
    )
    assert [c.stato for c in candidati] == ["ok", "ok"]


def test_le_righe_non_ok_non_vengono_rinominate():
    candidati = naming.risolvi_collisioni(
        [_candidato("{A}", "foto.jpg", stato="missing"),
         _candidato("{A}", "foto.jpg", stato="vuoto")], set()
    )
    assert [c.stato for c in candidati] == ["missing", "vuoto"]


# ---------------------------------------------------------------- CSV


def _scrivi_csv(tmp_path, contenuto, nome="allegati.csv", encoding="utf-8"):
    percorso = tmp_path / nome
    if isinstance(contenuto, bytes):
        percorso.write_bytes(contenuto)
    else:
        percorso.write_text(contenuto, encoding=encoding)
    return str(percorso)


def test_csv_punto_e_virgola_colonne_riconosciute(tmp_path):
    percorso = _scrivi_csv(tmp_path,
                           "GLOBALID;file;att_name\n"
                           "{A};foto1.jpg;Primo allegato.jpg\n"
                           "{B};foto2.jpg;\n")
    elenco = naming.leggi_csv_allegati(percorso)
    assert elenco.separatore == ";"
    assert elenco.colonna_chiave == "GLOBALID"
    assert elenco.colonna_file == "file"
    assert elenco.colonna_nome == "att_name"
    assert len(elenco.righe) == 2
    assert elenco.righe[0].nome == "Primo allegato.jpg"
    assert elenco.avvisi == []


def test_csv_virgola_e_colonne_inglesi(tmp_path):
    percorso = _scrivi_csv(tmp_path,
                           "globalid,path,name\n"
                           "{A},foto1.jpg,uno.jpg\n"
                           "{B},foto2.jpg,due.jpg\n")
    elenco = naming.leggi_csv_allegati(percorso)
    assert elenco.separatore == ","
    assert elenco.colonna_chiave == "globalid"
    assert elenco.colonna_file == "path"
    assert elenco.colonna_nome == "name"


def test_csv_encoding_bom_utf8(tmp_path):
    percorso = _scrivi_csv(tmp_path,
                           b"\xef\xbb\xbfGLOBALID;file\n{A};foto\xc3\xa9.jpg\n")
    elenco = naming.leggi_csv_allegati(percorso)
    assert elenco.encoding == "utf-8-sig"
    assert elenco.colonna_chiave == "GLOBALID"      # il BOM non sporca il nome colonna
    assert elenco.righe[0].percorso == "fotoé.jpg"


def test_csv_fallback_cp1252(tmp_path):
    percorso = _scrivi_csv(tmp_path, b"GLOBALID;file\n{A};foto\xe9.jpg\n")
    elenco = naming.leggi_csv_allegati(percorso)
    assert elenco.encoding == "cp1252"
    assert elenco.righe[0].percorso == "fotoé.jpg"


def test_csv_chiavi_duplicate_sono_un_avviso(tmp_path):
    """Più righe con la stessa chiave = più allegati sulla stessa feature."""
    percorso = _scrivi_csv(tmp_path,
                           "GLOBALID;file\n{A};foto1.jpg\n{A};foto2.jpg\n")
    elenco = naming.leggi_csv_allegati(percorso)
    assert elenco.chiavi_duplicate == ["{A}"]
    assert ("chiavi_duplicate", 1) in elenco.avvisi
    assert len(elenco.per_chiave["{A}"]) == 2


def test_csv_senza_colonna_chiave_blocca(tmp_path):
    percorso = _scrivi_csv(tmp_path, "CODICE;file\nX;foto1.jpg\n")
    with pytest.raises(ValueError):
        naming.leggi_csv_allegati(percorso, chiave="GLOBALID")


def test_csv_illeggibile_blocca(tmp_path):
    with pytest.raises(ValueError):
        naming.leggi_csv_allegati(str(tmp_path / "non_esiste.csv"))
    vuoto = _scrivi_csv(tmp_path, "", nome="vuoto.csv")
    with pytest.raises(ValueError):
        naming.leggi_csv_allegati(vuoto)


def test_csv_senza_colonna_file_avvisa_ma_non_blocca(tmp_path):
    percorso = _scrivi_csv(tmp_path, "GLOBALID;nota\n{A};ciao\n")
    elenco = naming.leggi_csv_allegati(percorso)
    assert ("colonna_file_da_indicare", "") in elenco.avvisi
    assert elenco.righe[0].percorso == ""


def test_csv_colonna_indicata_e_inesistente_avvisa(tmp_path):
    percorso = _scrivi_csv(tmp_path, "GLOBALID;file\n{A};foto1.jpg\n")
    elenco = naming.leggi_csv_allegati(percorso, colonna_file="percorso")
    assert ("colonna_mancante", "percorso") in elenco.avvisi


def test_intestazioni_csv(tmp_path):
    percorso = _scrivi_csv(tmp_path, "GLOBALID;file;nome\n{A};a.jpg;n\n")
    intestazioni, separatore, codifica = naming.intestazioni_csv(percorso)
    assert intestazioni == ["GLOBALID", "file", "nome"]
    assert separatore == ";" and codifica == "utf-8"

    intestazioni, messaggio, codifica = naming.intestazioni_csv(str(tmp_path / "manca.csv"))
    assert intestazioni == []
    assert "leggere" in messaggio


def test_candidati_da_csv_join_per_guid(tmp_path):
    """Chiave GUID normalizzata: graffe e case non contano."""
    risolutore = _risolutore({"foto1.jpg": _percorso_finto("foto1.jpg"),
                              "foto2.jpg": _percorso_finto("foto2.jpg")})
    guid_a = "{8AA1F6C0-1111-2222-3333-444455556666}"
    guid_b = "8AA1F6C0-AAAA-BBBB-CCCC-DDDDEEEEFFFF"
    guid_z = "{8AA1F6C0-9999-8888-7777-666655554444}"
    percorso = _scrivi_csv(tmp_path,
                           "GLOBALID;file;att_name\n"
                           f"{{{guid_a[1:-1].lower()}}};foto1.jpg;Primo.jpg\n"
                           f"{guid_b.lower()};foto2.jpg;\n"
                           f"{{{guid_z[1:-1].lower()}}};ignoto.jpg;\n")
    elenco = naming.leggi_csv_allegati(percorso)
    righe = [_riga(guid_a, "irrilevante"), _riga(guid_b, "irrilevante", indice=2)]
    candidati = naming.candidati_da_csv(elenco, righe, risolutore)

    per_parent = {c.id_parent: c for c in candidati}
    assert per_parent[guid_a].stato == "ok"
    assert per_parent[guid_a].nome_allegato == "Primo.jpg"   # nome dal CSV se c'è
    assert per_parent[guid_b].nome_allegato == "foto2.jpg"   # altrimenti nome del file
    ignote = [c for c in candidati if c.stato == "chiave_ignota"]
    assert len(ignote) == 1                       # la riga resta nel report, non blocca
    assert ignote[0].motivo


def test_candidati_da_csv_file_non_risolto(tmp_path):
    risolutore = _risolutore({})
    percorso = _scrivi_csv(tmp_path, "GLOBALID;file\n{A};manca.jpg\n")
    elenco = naming.leggi_csv_allegati(percorso)
    candidati = naming.candidati_da_csv(elenco, [_riga("{A}", "")], risolutore)
    assert candidati[0].stato == "file_ignoto"
    assert candidati[0].nome_allegato == ""


def test_candidati_da_csv_piu_allegati_per_feature(tmp_path):
    """Galleria: due righe CSV sulla stessa chiave → due allegati sulla stessa feature."""
    risolutore = _risolutore({"a.jpg": _percorso_finto("a.jpg"),
                              "b.jpg": _percorso_finto("b.jpg")})
    percorso = _scrivi_csv(tmp_path, "GLOBALID;file\n{A};a.jpg\n{A};b.jpg\n")
    elenco = naming.leggi_csv_allegati(percorso)
    candidati = naming.candidati_da_csv(elenco, [_riga("{A}", "")], risolutore)
    assert [c.nome_allegato for c in candidati] == ["a.jpg", "b.jpg"]
    assert naming.conteggi(candidati)["ok"] == 2


def test_candidati_da_csv_nome_vuoto_esplicito_salta(tmp_path):
    risolutore = _risolutore({"a.jpg": _percorso_finto("a.jpg")})
    percorso = _scrivi_csv(tmp_path, "GLOBALID;file;att_name\n{A};a.jpg; \n")
    elenco = naming.leggi_csv_allegati(percorso)
    candidati = naming.candidati_da_csv(elenco, [_riga("{A}", "")], risolutore)
    # la colonna nome vuota non azzera il nome: si ricade sul nome del file
    assert candidati[0].stato == "ok"
    assert candidati[0].nome_allegato == "a.jpg"


# ---------------------------------------------------------------- conteggi


def test_conteggi_e_saltati():
    candidati = [
        _candidato("{A}", "a.jpg", stato="ok"),
        _candidato("{A}", "b.jpg", stato="collisione"),
        _candidato("{B}", "c.jpg", stato="missing"),
        _candidato("{C}", "", stato="vuoto"),
        _candidato("{D}", "d.jpg", stato="duplicato"),
    ]
    conteggi = naming.conteggi(candidati)
    assert conteggi["ok"] == 1
    assert conteggi["collisione"] == 1
    assert conteggi["duplicato"] == 1
    assert conteggi["saltati"] == 1       # vuoto + salta + errori + chiavi ignote + file ignoti
    assert conteggi["totale"] == len(candidati)


def test_risolutore_vero_del_discovery_con_i_candidati(tmp_path):
    """Prova di integrazione naming + discovery: cartella base vera, file veri."""
    (tmp_path / "foto1.jpg").write_bytes(b"x")
    sottocartella = tmp_path / "sottosuolo"
    sottocartella.mkdir()
    (sottocartella / "SS_0001.jpg").write_bytes(b"x")
    risolutore = discovery.risolutore_file(str(tmp_path))

    candidati = naming.candidati_da_campi(
        [_riga("{A}", "foto1.jpg;SS_0001"), _riga("{B}", "assente.jpg")], risolutore
    )
    assert [c.nome_allegato for c in candidati] == ["foto1.jpg", "SS_0001.jpg", "assente.jpg"]
    assert [c.stato for c in candidati] == ["ok", "ok", "missing"]
    assert candidati[1].percorso_file == str(sottocartella / "SS_0001.jpg")
