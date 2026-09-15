# test_wizard_conteggi.py — i numeri mostrati devono venire dal core, una volta sola.
#
# Difetto: anteprima (passo 5) e riepilogo di esecuzione (passo 6) sommavano
# `conteggi["saltati"] + conteggi["salta"]`, ma `conteggi["saltati"]` include già
# `salta`: gli stessi dati mostravano numeri diversi (e sbagliati) nei due passi.
#
# Marcatura: `unit`.

from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from gdb_attacher.core import naming                               # noqa: E402
from gdb_attacher.wizard import strings                            # noqa: E402
from test_wizard_montaggio import apri_wizard, progetto_con        # noqa: E402

pytestmark = pytest.mark.unit

#: Un candidato per ogni stato, così i conteggi coprono tutto il vocabolario.
STATI = ("ok", "missing", "collisione", "vuoto", "salta", "errore", "chiave_ignota",
         "file_ignoto", "duplicato")


def candidato(stato, indice=1, campo="filefoto"):
    return naming.CandidatoAllegato(
        id_parent="{%s}" % ("0F1E2D3C-4B5A-6978-8796-A5B4C3D2E1F0" if indice == 1
                            else "1A2B3C4D-5E6F-7081-92A3-B4C5D6E7F809"),
        campo_foto=campo,
        valore_campo="SS_000%d.jpg" % indice,
        token="SS_000%d.jpg" % indice,
        percorso_file="/tmp/foto/SS_000%d.jpg" % indice,
        nome_allegato="SS_000%d.jpg" % indice,
        nome_originale="SS_000%d.jpg" % indice,
        indice_feature=indice,
        stato=stato,
        motivo="",
    )


def etichette(wizard, candidati, monkeypatch):
    """Etichetta dei conteggi dell'anteprima e del riepilogo di esecuzione."""
    wizard.candidati = list(candidati)
    pagina = wizard.pagina_naming
    monkeypatch.setattr(pagina, "costruisci_candidati", lambda salva=True: list(candidati))
    pagina.aggiorna_anteprima()
    wizard.pagina_esegui.initializePage()
    return pagina.conteggi.text(), wizard.pagina_esegui.contatori.text()


@pytest.mark.parametrize("misto", [
    ["salta"],
    ["vuoto", "salta"],
    ["ok", "salta", "vuoto", "errore"],
    list(STATI),
])
def test_i_saltati_non_sono_contati_due_volte(monkeypatch, misto):
    progetto_con()
    wizard = apri_wizard(monkeypatch)
    candidati = [candidato(stato, indice=i + 1) for i, stato in enumerate(misto)]

    testo_anteprima, testo_esegui = etichette(wizard, candidati, monkeypatch)
    saltati = naming.conteggi(candidati)["saltati"]
    pezzo = strings.tr("totale_saltati", "it", n=saltati)

    assert pezzo in testo_anteprima
    assert pezzo in testo_esegui
    # il numero gonfiato dal doppio conteggio non deve comparire in nessuno dei due
    gonfiato = strings.tr("totale_saltati", "it",
                          n=saltati + naming.conteggi(candidati)["salta"])
    if saltati + naming.conteggi(candidati)["salta"] != saltati:
        assert gonfiato not in testo_anteprima
        assert gonfiato not in testo_esegui


def test_anteprima_e_riepilogo_dicono_la_stessa_cosa(monkeypatch):
    """La proprietà che conta: sugli stessi dati, gli stessi numeri."""
    progetto_con()
    wizard = apri_wizard(monkeypatch)
    candidati = [candidato("ok"), candidato("salta", 2), candidato("vuoto", 3),
                 candidato("missing", 4), candidato("file_ignoto", 5),
                 candidato("duplicato", 6)]

    testo_anteprima, testo_esegui = etichette(wizard, candidati, monkeypatch)
    conteggi = naming.conteggi(candidati)
    for chiave, valore in (("totale_ok", conteggi["ok"] + conteggi["collisione"]),
                           ("atto_totale_duplicati", conteggi["duplicato"]),
                           ("totale_missing", conteggi["missing"] + conteggi["file_ignoto"]),
                           ("totale_collisioni", conteggi["collisione"]),
                           ("totale_saltati", conteggi["saltati"])):
        pezzo = strings.tr(chiave, "it", n=valore)
        assert pezzo in testo_anteprima, (chiave, "anteprima")
        assert pezzo in testo_esegui, (chiave, "riepilogo")


def test_il_riepilogo_di_esecuzione_non_riguarda_il_layer(monkeypatch):
    """Senza layer sorgente il riepilogo regge lo stesso (nessun crash)."""
    progetto_con(layer_sorgente=False, layer_allegati=False)
    wizard = apri_wizard(monkeypatch)
    wizard.candidati = [candidato("ok")]
    wizard.pagina_esegui.initializePage()
    assert strings.tr("totale_ok", "it", n=1) in wizard.pagina_esegui.contatori.text()
