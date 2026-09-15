# test_regressioni_revisione.py — i difetti trovati da due revisioni indipendenti,
# bloccati da un test ciascuno.
#
# Ogni test qui corrisponde a un difetto *concreto* (con scenario riproducibile), non a
# un'ipotesi: se il difetto torna, il test rosseggia e dice quale comportamento è stato
# perso. I commenti spiegano cosa succedeva prima, perché è la parte che si dimentica.
#
# Aree coperte: allegati rinominati per collisione, GlobalID nullo, commit fallito,
# variabili di formula dal file risolto, colonne CSV indicate dall'utente, dedup Unicode,
# riconoscimento del .gdb, backup atomico, conteggi ed errori del report.

from __future__ import annotations

import contextlib
import os
import shutil
import sys
import unicodedata

import pytest

from fake_qgis import GUID_1, GUID_2, crea_layer_attach

pytestmark = pytest.mark.unit

from gdb_attacher.core import attach, naming, report  # noqa: E402


def candidati(valore, cartella, guid=GUID_1, modalita=naming.MODALITA_ORIGINALE, **extra):
    """Candidati come li costruisce il wizard: campo foto + cartella base."""
    righe = [naming.RigaSorgente(id_parent=guid, campo_foto="FOTO", valore=valore,
                                 indice_feature=1)]

    def risolutore(token):
        percorso = cartella / token
        return str(percorso) if percorso.is_file() else ""

    return naming.candidati_da_campi(righe, risolutore, modalita, **extra)


# --------------------------------------------------------------- scrittura: collisioni
def test_l_allegato_rinominato_per_collisione_viene_scritto(cartella_foto):
    """Difetto: `da_scrivere` accettava solo lo stato "ok", quindi un allegato rinominato
    per collisione (IMG_2.jpg) non veniva mai scritto: il report lo contava fra gli
    aggiunti e la foto spariva senza un errore."""
    layer = crea_layer_attach()
    pianificati = naming.risolvi_collisioni(
        candidati("SS_0001.jpg;SS_0001.jpg", cartella_foto),
        esistenti=attach.carica_chiavi_esistenti(layer),
    )
    assert [c.stato for c in pianificati] == ["ok", "collisione"]
    assert pianificati[1].da_scrivere, "un allegato rinominato deve essere scritto"

    statistica = attach.scrivi_allegati(layer, pianificati)

    assert statistica.aggiunti == 2
    nomi = sorted(f["ATT_NAME"] for f in layer.getFeatures())
    assert nomi == ["SS_0001.jpg", "SS_0001_2.jpg"]


def test_lo_stato_collisione_resta_contato_dal_report(cartella_foto):
    layer = crea_layer_attach()
    pianificati = naming.risolvi_collisioni(candidati("SS_0001.jpg;SS_0001.jpg", cartella_foto))
    statistica = attach.scrivi_allegati(layer, pianificati)
    finale = report.report_da_candidati(pianificati, statistica)

    assert finale.aggiunti == 2
    assert finale.collisioni == 1
    assert any(r.tipo == "collisione" for r in finale.righe)


# ------------------------------------------------------------------- GlobalID nullo
@pytest.mark.parametrize("valore", ["NULL", "null", " NULL ", "None", "<NULL>", ""])
def test_le_sentinelle_di_nullita_non_sono_guid(valore):
    """Difetto: un GlobalID presente ma nullo arriva come stringa "NULL", non come None:
    si scriveva un allegato orfano con REL_GLOBALID="{NULL}"."""
    assert attach.normalizza_guid(valore) == ""
    assert attach.guid_con_graffe(valore) == ""
    assert attach.chiave_dedup(valore, "foto.jpg") is None


def test_parent_con_globalid_nullo_non_finisce_nel_gdb(cartella_foto):
    layer = crea_layer_attach()
    pianificati = naming.risolvi_collisioni(candidati("SS_0001.jpg", cartella_foto, guid="NULL"))

    assert pianificati[0].stato == "errore"
    assert pianificati[0].motivo == "GlobalID parent nullo"
    assert not pianificati[0].da_scrivere

    statistica = attach.scrivi_allegati(layer, pianificati)
    assert statistica.aggiunti == 0
    assert layer.featureCount() == 0, "nessuna riga con {NULL} deve entrare nel GDB"


def test_guid_valido_con_graffe_o_case_resta_normalizzato():
    assert attach.normalizza_guid("{" + GUID_1.lower() + "}") == GUID_1
    assert attach.normalizza_guid(GUID_1) == GUID_1


# ------------------------------------------------------------------- commit fallito
def test_commit_fallito_non_esce_dal_core_e_riporta_l_errore(monkeypatch, cartella_foto):
    """Difetto: se `commitChanges()` falliva, QGIS solleva QgsEditError, che usciva da
    scrivi_allegati e da uno slot Qt: traceback, report perso, "aggiunti: N" con zero
    righe scritte. Ora l'esito finisce nella statistica."""

    class _CommitFallito(Exception):
        pass

    @contextlib.contextmanager
    def edit_che_fallisce(layer):
        istantanea = list(getattr(layer, "_features", []))
        layer.startEditing()
        try:
            yield
        finally:
            layer._features = istantanea
            layer.rollback()
        raise _CommitFallito("commitChanges() ha restituito False")

    monkeypatch.setattr(sys.modules["qgis.core"], "edit", edit_che_fallisce)

    layer = crea_layer_attach()
    statistica = attach.scrivi_allegati(layer, candidati("SS_0001.jpg", cartella_foto))

    assert statistica.aggiunti == 0, "il rollback ha annullato tutto"
    assert "commitChanges" in statistica.errore_commit
    assert layer.featureCount() == 0


def test_il_report_avverte_quando_il_commit_fallisce(cartella_foto):
    candidato = candidati("SS_0001.jpg", cartella_foto)
    statistica = attach.StatisticaScrittura(aggiunti=0, errore_commit="QgsEditError: disco pieno")
    finale = report.report_da_candidati(candidato, statistica)

    assert finale.aggiunti == 0
    assert "disco pieno" in finale.errore_commit
    assert any("commit fallito" in riga.motivo for riga in finale.righe)


# ------------------------------------------------------- variabili della formula
def test_le_variabili_della_formula_vengono_dal_file_risolto(cartella_foto):
    """Difetto: @original_name/@stem/@ext venivano dal token del campo, non dal file
    risolto: con token "SS_0001" e file "SS_0001.jpg" l'allegato perdeva l'estensione,
    incoerente con la modalità originale che scrive "SS_0001.jpg"."""

    def risolutore_completa_estensione(token):
        for candidato in (token, token + ".jpg"):
            percorso = cartella_foto / candidato
            if percorso.is_file():
                return str(percorso)
        return ""

    righe = [naming.RigaSorgente(id_parent=GUID_1, campo_foto="FOTO",
                                 valore="SS_0001", indice_feature=1)]
    esito = naming.candidati_da_campi(
        righe, risolutore_completa_estensione, naming.MODALITA_FORMULA,
        espressione="@original_name", valutatore=lambda espressione, riga, variabili: variabili["original_name"],
    )
    assert esito[0].nome_allegato == "SS_0001.jpg"


def test_una_formula_che_valuta_null_salta_la_riga(cartella_foto):
    """Difetto: la sentinella NULL valutata dalla formula diventava un allegato "NULL"."""
    esito = naming.candidati_da_campi(
        [naming.RigaSorgente(id_parent=GUID_1, campo_foto="FOTO",
                             valore="SS_0001.jpg", indice_feature=1)],
        lambda token: str(cartella_foto / token), naming.MODALITA_FORMULA,
        espressione="NULL", valutatore=lambda espressione, riga, variabili: "NULL",
    )
    assert esito[0].stato == "salta"
    assert esito[0].nome_allegato == ""


# --------------------------------------------------------------------------- CSV
def _csv(tmp_path, testo, nome="allegati.csv"):
    percorso = tmp_path / nome
    percorso.write_text(testo, encoding="utf-8")
    return str(percorso)


def test_la_colonna_scelta_dall_utente_ignora_le_maiuscole(tmp_path):
    """Difetto: con intestazione "file" e scelta "File" la colonna risultava assente,
    tutto il lotto finiva fra i file non trovati e l'avviso parlava di colonna mancante."""
    percorso = _csv(tmp_path, f"GLOBALID;file\n{GUID_1};POZZETTO_1.jpg\n")

    elenco = naming.leggi_csv_allegati(percorso, colonna_file="File")

    assert elenco.colonna_file == "file"
    assert ("colonna_mancante", "File") not in elenco.avvisi
    assert elenco.righe[0].percorso == "POZZETTO_1.jpg"


def test_la_colonna_att_name_scelta_dall_utente_ignora_le_maiuscole(tmp_path):
    percorso = _csv(tmp_path, f"GLOBALID;FILE;Nome file\n{GUID_1};a.jpg;Foto.JPG\n")

    elenco = naming.leggi_csv_allegati(percorso, colonna_file="file", colonna_att_name="nome file")

    assert elenco.colonna_nome == "Nome file"
    assert elenco.righe[0].nome == "Foto.JPG"


def test_il_csv_produce_un_solo_allegato_per_feature(cartella_foto):
    """Difetto: con più campi foto selezionati la stessa feature compariva una volta per
    campo e il CSV produceva allegati doppi (a.jpg, a_2.jpg, a_3.jpg)."""
    righe = [
        naming.RigaSorgente(id_parent=GUID_1, campo_foto="FOTO_ANTE", valore="SS_0001.jpg",
                            indice_feature=1),
        naming.RigaSorgente(id_parent=GUID_1, campo_foto="FOTO_POST", valore="ACQ_2.png",
                            indice_feature=1),
    ]
    elenco = naming.ElencoCsv(percorso="x.csv", colonna_file="file", colonna_chiave="GLOBALID",
                              righe=[naming.RigaCsv(numero=2, chiave=GUID_1,
                                                    percorso="SS_0001.jpg", nome="")])

    esito = naming.candidati_da_csv(elenco, righe, lambda token: str(cartella_foto / token))

    assert len(esito) == 1
    assert esito[0].nome_allegato == "SS_0001.jpg"


# ------------------------------------------------------------------------- dedup
def test_la_dedup_confronta_i_nomi_in_forma_unicode_nfc():
    """Due scritture dello stesso nome con accento composto/decomposto sono lo stesso file."""
    composto = unicodedata.normalize("NFC", "café.jpg")
    decomposto = unicodedata.normalize("NFD", "café.jpg")
    assert composto != decomposto
    assert attach.chiave_dedup(GUID_1, composto) == attach.chiave_dedup(GUID_1, decomposto)


def test_la_maiuscolatura_del_nome_resta_significativa():
    """Scelta esplicita (ticket 06, nome verbatim): O'Brien.JPG ≠ o'brien.jpg."""
    assert attach.chiave_dedup(GUID_1, "Foto.JPG") != attach.chiave_dedup(GUID_1, "foto.jpg")


# ------------------------------------------------- riconoscimento del .gdb
@pytest.mark.parametrize("origine,atteso", [
    ("D:/dati/pz.gdb", True),
    ("D:/dati/pz.gdb|layername=pozzetti", True),
    ("D:/dati/pz.gdb|layerid=0", True),
    ("/home/x/layer.gpkg", False),
    ("", False),
    ("D:/dati/export.gdb/shp/layer.shp", False),
])
def test_sembra_filegdb_solo_sull_ultimo_segmento(origine, atteso):
    """Difetto: uno shapefile dentro una cartella chiamata *.gdb passava per FileGDB."""
    assert attach.sembra_filegdb(origine) is atteso


def test_percorso_gdb_prende_l_ultimo_segmento():
    """Difetto: si prendeva il primo ".gdb" del testo, proponendo backup su cartelle
    inesistenti (D:/dati/vecchio.gdb invece di D:/dati/vecchio.gdb_old/layer.gdb)."""
    assert attach.percorso_gdb("D:/dati/vecchio.gdb_old/layer.gdb") == "D:/dati/vecchio.gdb_old/layer.gdb"
    assert attach.percorso_gdb("D:/dati/pz.gdb|layername=x") == "D:/dati/pz.gdb"
    assert attach.percorso_gdb("D:/dati/export.gdb/shp/layer.shp") == ""


# ------------------------------------------------------------------- backup
def test_backup_fallito_non_lascia_una_copia_parziale(monkeypatch, tmp_path):
    """Difetto: la copia parziale restava con il nome definitivo e il secondo tentativo
    moriva con "destinazione già esistente": l'utente credeva di avere un backup."""
    origine = tmp_path / "pz.gdb"
    origine.mkdir()
    (origine / "a.gdbtable").write_bytes(b"dati")
    destinazione = tmp_path / "pz_backup.gdb"

    def copytree_che_fallisce(sorgente, destinazione_arg, **kwargs):
        os.makedirs(destinazione_arg, exist_ok=True)
        with open(os.path.join(destinazione_arg, "mezzo.gdbtable"), "wb") as flusso:
            flusso.write(b"parziale")
        raise OSError("disco pieno")

    monkeypatch.setattr(shutil, "copytree", copytree_che_fallisce)

    with pytest.raises(OSError):
        attach.backup_gdb(str(origine), str(destinazione))

    assert not destinazione.exists(), "nessun backup con il nome definitivo"
    assert not (tmp_path / "pz_backup.gdb.parziale").exists(), "nessun residuo temporaneo"


def test_backup_riuscito_crea_la_cartella(tmp_path):
    origine = tmp_path / "pz.gdb"
    origine.mkdir()
    (origine / "a.gdbtable").write_bytes(b"dati")
    destinazione = tmp_path / "copia.gdb"

    creato = attach.backup_gdb(str(origine), str(destinazione))

    assert creato == str(destinazione)
    assert (destinazione / "a.gdbtable").read_bytes() == b"dati"
    assert not (tmp_path / "copia.gdb.parziale").exists()


# ------------------------------------------------------------------- report
def test_gli_aggiunti_del_report_vengono_dalla_statistica(cartella_foto):
    """Difetto: il report contava i candidati "ok", non ciò che è stato scritto: un file
    cancellato fra anteprima ed esecuzione o un annullo davano numeri falsi."""
    pianificati = candidati("SS_0001.jpg", cartella_foto)
    statistica = attach.StatisticaScrittura(aggiunti=0, saltati=1,
                                            errori=[("x", "file sparito", GUID_1, "FOTO")])
    finale = report.report_da_candidati(pianificati, statistica)
    assert finale.aggiunti == 0


def test_le_righe_di_errore_portano_feature_e_campo(cartella_foto):
    """Difetto: le righe d'errore perdevano id_parent e campo foto, quindi nel CSV
    "mancanti/errori" la colonna Feature restava vuota proprio sul caso più frequente."""
    layer = crea_layer_attach()
    candidato = candidati("SS_0001.jpg", cartella_foto)[0]
    candidato.percorso_file = str(cartella_foto / "sparito.jpg")   # file rimosso dopo l'anteprima

    statistica = attach.scrivi_allegati(layer, [candidato])
    voce = statistica.errori[0]

    assert voce[2] == GUID_1 and voce[3] == "FOTO"
    finale = report.report_da_candidati([candidato], statistica)
    riga = [r for r in finale.righe if r.tipo == "errore"][0]
    assert riga.id_parent == GUID_1 and riga.campo_foto == "FOTO"


def test_export_csv_fallito_non_lascia_file_a_meta(tmp_path):
    """Difetto: OSError non gestito nello slot Qt e possibile CSV parziale."""
    report_finto = report.ReportFinale(righe=[report.RigaReport(tipo="errore", motivo="x")])
    destinazione = tmp_path / "una_cartella"
    destinazione.mkdir()          # aprire un file su un percorso di cartella fallisce

    with pytest.raises(OSError) as errore:
        report.scrivi_report_csv(str(destinazione), report_finto.righe)

    assert "non riesco a scrivere il CSV" in str(errore.value)
    assert not (tmp_path / "una_cartella.parziale").exists()


def test_due_feature_diverse_non_sono_duplicati(cartella_foto):
    """Controllo di non-regressione: la chiave di dedup è la coppia GUID+nome."""
    pianificati = naming.risolvi_collisioni(
        candidati("SS_0001.jpg", cartella_foto, guid=GUID_1)
        + candidati("SS_0001.jpg", cartella_foto, guid=GUID_2)
    )
    layer = crea_layer_attach()
    statistica = attach.scrivi_allegati(layer, pianificati)
    assert statistica.aggiunti == 2
