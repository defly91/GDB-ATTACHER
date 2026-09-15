# -*- coding: utf-8 -*-
"""Test di logica pura su ``core/report.py``: anteprima a 5 esempi e report/export.

Ticket 03: l'anteprima di conferma è **a conteggi**; il dettaglio (5 feature campione
con *valore del campo → file risolto → nome allegato*) sta nella schermata del naming
(ticket 06). Ticket 07: l'export CSV porta le righe mancanti/errate.
"""

import csv
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from gdb_attacher.core import naming, report  # noqa: E402


def _candidato(id_parent, nome, stato="ok", campo="FILEFOTO", feature=1,
               percorso=None, motivo="", valore=None):
    return naming.CandidatoAllegato(
        id_parent=id_parent, campo_foto=campo,
        valore_campo=nome if valore is None else valore, token=nome,
        percorso_file=percorso if percorso is not None else f"/finta/{nome}",
        nome_allegato=nome if stato in ("ok", "collisione", "duplicato") else "",
        nome_originale=nome, indice_token=1, indice_feature=feature,
        stato=stato, motivo=motivo,
    )


# ---------------------------------------------------------------- anteprima


def test_anteprima_mostra_al_massimo_cinque_feature_diverse():
    candidati = [_candidato(f"{{F{i}}}", f"foto{i}.jpg", feature=i) for i in range(1, 9)]
    anteprima = report.costruisci_anteprima(candidati)
    assert len(anteprima.esempi) == 5
    assert len({e.campo_foto for e in anteprima.esempi}) == 1
    assert [e.nome_allegato for e in anteprima.esempi] == [f"foto{i}.jpg" for i in range(1, 6)]


def test_anteprima_una_riga_per_feature_anche_con_multivalore():
    """Il multi-valore fa più allegati ma l'anteprima non ripete la stessa feature."""
    candidati = [
        _candidato("{A}", "a.jpg", feature=1),
        naming.CandidatoAllegato(id_parent="{A}", campo_foto="FILEFOTO", valore_campo="a.jpg;b.jpg",
                                 token="b.jpg", percorso_file="/finta/b.jpg",
                                 nome_allegato="b.jpg", indice_token=2, indice_feature=1),
        _candidato("{B}", "c.jpg", feature=2),
    ]
    anteprima = report.costruisci_anteprima(candidati)
    assert [e.nome_allegato for e in anteprima.esempi] == ["a.jpg", "c.jpg"]


def test_anteprima_mette_prima_quello_che_si_scrive():
    candidati = [
        _candidato("{A}", "vuoto.jpg", stato="vuoto", feature=1),
        _candidato("{B}", "manca.jpg", stato="missing", feature=2),
        _candidato("{C}", "ok.jpg", stato="ok", feature=3),
    ]
    anteprima = report.costruisci_anteprima(candidati)
    assert anteprima.esempi[0].stato == "ok"
    assert anteprima.esempi[1].stato == "missing"


def test_anteprima_conteggi_e_conteggi_per_campo():
    candidati = [
        _candidato("{A}", "a.jpg", campo="FOTO_EST"),
        _candidato("{A}", "b.jpg", campo="FOTO_INT"),
        _candidato("{B}", "c.jpg", campo="FOTO_EST"),
        _candidato("{C}", "m.jpg", stato="missing", campo="FOTO_EST"),
    ]
    anteprima = report.costruisci_anteprima(candidati)
    assert anteprima.conteggi["ok"] == 3
    assert anteprima.conteggi["missing"] == 1
    assert anteprima.conteggi_per_campo == {"FOTO_EST": 2, "FOTO_INT": 1}


def test_anteprima_porta_gli_avvisi_del_csv():
    anteprima = report.costruisci_anteprima([_candidato("{A}", "a.jpg")],
                                            avvisi=[("chiavi_duplicate", 2)])
    assert anteprima.avvisi == [("chiavi_duplicate", 2)]


def test_anteprima_usa_il_nome_originale_quando_manca_il_finale():
    candidato = _candidato("{A}", "foto_2.jpg", stato="collisione")
    candidato.nome_originale = "foto.jpg"
    assert report.costruisci_anteprima([candidato]).esempi[0].nome_allegato == "foto_2.jpg"


# ---------------------------------------------------------------- report


def test_report_conta_aggiunti_duplicati_collisioni_saltati_errori():
    candidati = [
        _candidato("{A}", "a.jpg"),                               # ok -> aggiunto
        _candidato("{B}", "b_2.jpg", stato="collisione"),         # rinominato -> aggiunto
        _candidato("{C}", "c.jpg", stato="duplicato"),            # già presente
        _candidato("{D}", "d.jpg", stato="missing"),              # file mancante
        _candidato("{E}", "", stato="vuoto"),                     # campo vuoto
        _candidato("{F}", "f.jpg", stato="chiave_ignota"),        # chiave non nel layer
        _candidato("{G}", "g.jpg", stato="errore", motivo="formula rotta"),
    ]
    finale = report.report_da_candidati(candidati)

    assert finale.aggiunti == 2
    assert finale.duplicati == 1
    assert finale.collisioni == 1
    assert finale.mancanti == 1        # file atteso non trovato
    assert finale.saltati == 2         # vuoto + chiave del CSV fuori dal layer
    assert finale.errori == 1
    assert not finale.annullata


def test_report_righe_per_le_anomalie_e_per_i_rinominati():
    candidati = [
        _candidato("{A}", "a.jpg"),
        _candidato("{B}", "b_2.jpg", stato="collisione", motivo="rinominato in b_2.jpg"),
        _candidato("{C}", "c.jpg", stato="missing", motivo="file non trovato"),
    ]
    finale = report.report_da_candidati(candidati)
    tipi = sorted(riga.tipo for riga in finale.righe)
    assert tipi == ["collisione", "missing"]
    anomalie = finale.anomalie()
    assert [riga.tipo for riga in anomalie] == ["missing"]
    assert anomalie[0].motivo == "file non trovato"


def test_report_unisce_la_statistica_di_scrittura():
    class _Statistica:
        aggiunti = 1
        duplicati = 2
        saltati = 1
        errori = [("x.jpg", "addFeature() ha restituito False")]
        annullata = False

    finale = report.report_da_candidati([_candidato("{A}", "a.jpg")], _Statistica())
    assert finale.duplicati == 2
    assert finale.errori == 1
    assert any("addFeature" in riga.motivo for riga in finale.righe)


def test_report_annullato():
    class _Statistica:
        aggiunti = 0
        duplicati = 0
        saltati = 0
        errori = []
        annullata = True

    finale = report.report_da_candidati([], _Statistica())
    assert finale.annullata is True


def test_report_avvisi_diventano_righe():
    finale = report.report_da_candidati([], avvisi=[("chiavi_duplicate", 3)])
    assert finale.righe[-1].tipo == "avviso"
    assert "chiavi_duplicate" in finale.righe[-1].motivo


# ---------------------------------------------------------------- export CSV


def test_export_csv_anomalie(tmp_path):
    candidati = [
        _candidato("{A}", "a.jpg"),
        _candidato("{B}", "b.jpg", stato="missing", motivo="file non trovato",
                   percorso="", feature=2),
        _candidato("{C}", "", stato="vuoto", motivo="campo foto vuoto", feature=3),
    ]
    finale = report.report_da_candidati(candidati)
    percorso = str(tmp_path / "sottocartella" / "report.csv")
    report.scrivi_report_csv(percorso, finale.righe)

    assert os.path.isfile(percorso)
    with open(percorso, encoding="utf-8-sig", newline="") as flusso:
        righe = list(csv.reader(flusso, delimiter=";"))
    assert righe[0] == list(report.INTESTAZIONI_CSV)
    assert len(righe) == 3                     # intestazione + 2 anomalie
    assert righe[1][0] == "missing"
    assert righe[1][2] == "FILEFOTO"
    assert righe[1][6] == "file non trovato"


def test_export_csv_ha_il_bom_per_excel(tmp_path):
    finale = report.report_da_candidati([_candidato("{A}", "a.jpg", stato="missing")])
    percorso = str(tmp_path / "report.csv")
    report.scrivi_report_csv(percorso, finale.righe)
    assert open(percorso, "rb").read().startswith(b"\xef\xbb\xbf")


def test_export_csv_tutte_le_righe(tmp_path):
    candidati = [_candidato("{A}", "a.jpg"), _candidato("{B}", "b.jpg", stato="missing")]
    finale = report.report_da_candidati(candidati)
    percorso = str(tmp_path / "report.csv")
    report.scrivi_report_csv(percorso, finale.righe, solo_anomalie=False)
    with open(percorso, encoding="utf-8-sig", newline="") as flusso:
        righe = list(csv.reader(flusso, delimiter=";"))
    assert len(righe) == 2                     # intestazione + missing (gli ok non hanno riga)


def test_export_csv_intestazioni_e_traduttore(tmp_path):
    finale = report.report_da_candidati([_candidato("{A}", "a.jpg", stato="missing")])
    percorso = str(tmp_path / "report.csv")
    report.scrivi_report_csv(
        percorso, finale.righe,
        intestazioni=("State", "Feature", "Field", "Value", "File", "Name", "Reason"),
        traduttore=lambda codice: {"missing": "missing file"}.get(codice, codice),
    )
    with open(percorso, encoding="utf-8-sig", newline="") as flusso:
        righe = list(csv.reader(flusso, delimiter=";"))
    assert righe[0][0] == "State"
    assert righe[1][0] == "missing file"


def test_righe_da_esportare():
    finale = report.report_da_candidati([
        _candidato("{A}", "a.jpg"),
        _candidato("{B}", "b.jpg", stato="missing"),
        _candidato("{C}", "c.jpg", stato="collisione"),
    ])
    assert len(report.righe_da_esportare(finale, solo_anomalie=True)) == 1
    assert len(report.righe_da_esportare(finale, solo_anomalie=False)) == 2


def test_stati_anomali_includono_il_duplicato():
    """Il «già presente» resta nel report: serve a capire perché non si è scritto nulla."""
    assert "duplicato" in report.STATI_ANOMALI
    assert "collisione" not in report.STATI_ANOMALI
    assert set(report.STATI_ANOMALI) <= set(naming.STATI)
