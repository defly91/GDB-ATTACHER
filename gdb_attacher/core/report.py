# -*- coding: utf-8 -*-
"""core/report.py — anteprima (5 esempi + conteggi) e report finale esportabile.

Ticket 03: l'anteprima mostra **solo conteggi** nella fase di conferma; il dettaglio
di valorizzazione (5 feature campione) vive nella schermata del naming e obbliga a
mostrare *valore del campo → file risolto → nome allegato* (ticket 06), più **quale
campo foto** e il **conteggio per campo**.

Il report finale conta aggiunti / già presenti / collisioni / saltati / errori e
porta con sé una riga per ogni anomalia, esportabile in CSV (righe mancanti ed
errate con feature, campo, file atteso e motivo — con BOM UTF-8, così Excel apre
accenti e apici senza chiedere nulla).

Il modulo è puro Python: nessun import di QGIS, nessun testo di interfaccia (le
intestazioni del CSV le passa il wizard, già tradotte).
"""

from __future__ import annotations

import csv
import os
from dataclasses import dataclass, field

from . import naming

#: Intestazioni del CSV di report (italiano: usate quando il chiamante non le passa).
INTESTAZIONI_CSV = ("Tipo", "Feature (GLOBALID)", "Campo foto", "Valore",
                    "Percorso file", "Nome allegato", "Motivo")

#: Stati che NON sono anomalie (una riga scritta, o una collisione risolta).
STATI_SCRITTI = ("ok", "collisione")

#: Stati che finiscono nell'export dei «mancanti/errori».
STATI_ANOMALI = ("missing", "file_ignoto", "vuoto", "salta", "errore",
                 "chiave_ignota", "duplicato")


@dataclass
class EsempioAnteprima:
    """Una riga dell'anteprima a 5 esempi."""

    campo_foto: str = ""
    valore_campo: str = ""
    percorso_file: str = ""
    nome_allegato: str = ""
    stato: str = "ok"
    motivo: str = ""


@dataclass
class Anteprima:
    """Anteprima di un lotto: esempi, conteggi totali e conteggi per campo foto."""

    esempi: list = field(default_factory=list)
    conteggi: dict = field(default_factory=dict)
    conteggi_per_campo: dict = field(default_factory=dict)
    avvisi: list = field(default_factory=list)


@dataclass
class RigaReport:
    """Una riga del report finale."""

    tipo: str = ""               # codice di stato (tradotto dalla UI)
    id_parent: str = ""
    campo_foto: str = ""
    valore: str = ""
    percorso_file: str = ""
    nome_allegato: str = ""
    motivo: str = ""


@dataclass
class ReportFinale:
    """Numeri e righe di dettaglio di un'esecuzione."""

    aggiunti: int = 0
    duplicati: int = 0            # «già presenti» (deduplica e idempotenza)
    collisioni: int = 0          # rinominate con _2, _3…
    mancanti: int = 0            # file atteso non trovato (missing / file_ignoto)
    saltati: int = 0             # valori vuoti, nomi vuoti, chiavi del CSV fuori dal layer
    errori: int = 0
    righe: list = field(default_factory=list)
    annullata: bool = False

    def anomalie(self) -> list:
        """Righe da esportare come «mancanti/errate»."""
        return [riga for riga in self.righe if riga.tipo in STATI_ANOMALI]


# ---------------------------------------------------------------- anteprima


def _scegli_esempi(candidati, n_esempi: int) -> list:
    """Sceglie fino a ``n_esempi`` feature diverse per l'anteprima.

    Ordine di priorità: prima quello che si scrive (``ok``/``collisione``), poi i
    file mancanti, poi il resto. Una feature compare una volta sola: l'anteprima
    deve mostrare il *percorso* di lavorazione, non ripetere due token dello stesso
    campo multi-valore.
    """
    preferiti = [c for c in candidati if c.stato in STATI_SCRITTI]
    mancanti = [c for c in candidati if c.stato in ("missing", "file_ignoto")]
    altri = [c for c in candidati if c.stato not in STATI_SCRITTI + ("missing", "file_ignoto")]

    scelti, viste = [], set()
    for gruppo in (preferiti, mancanti, altri):
        for candidato in gruppo:
            if len(scelti) >= n_esempi:
                break
            chiave = (candidato.id_parent, candidato.indice_feature)
            if chiave in viste:
                continue
            viste.add(chiave)
            scelti.append(EsempioAnteprima(
                campo_foto=candidato.campo_foto,
                valore_campo=candidato.valore_campo,
                percorso_file=candidato.percorso_file,
                nome_allegato=candidato.nome_allegato or candidato.nome_originale,
                stato=candidato.stato,
                motivo=candidato.motivo,
            ))
    return scelti


def costruisci_anteprima(candidati, n_esempi: int = 5, avvisi=None) -> Anteprima:
    """Anteprima completa: esempi + conteggi (ticket 03 e 06)."""
    candidati = list(candidati)
    return Anteprima(
        esempi=_scegli_esempi(candidati, n_esempi),
        conteggi=naming.conteggi(candidati),
        conteggi_per_campo=naming.conteggi_per_campo(candidati),
        avvisi=list(avvisi or []),
    )


# ---------------------------------------------------------------- report


def report_da_candidati(candidati, statistica=None, avvisi=None) -> ReportFinale:
    """Costruisce il report finale dai candidati (e dalla statistica di scrittura).

    I conteggi vengono dai candidati — così il report a video e l'anteprima dicono
    la stessa cosa — e dalla statistica di scrittura per ciò che si sa solo dopo il
    commit (errori di ``addFeature``, eventuali duplicati sfuggiti alla preview).

    Distinzione dei «salti», come nei due script in repo: i **file non trovati**
    finiscono in ``mancanti`` (è il caso più frequente e merita un numero suo, il
    «Saltati (foto mancante o dati nulli)» dello script batch), gli altri — valori
    vuoti, nomi vuoti dalla formula, chiavi del CSV fuori dal layer — in ``saltati``.
    """
    candidati = list(candidati)
    conteggi = naming.conteggi(candidati)

    report = ReportFinale(
        aggiunti=conteggi["ok"] + conteggi["collisione"],
        duplicati=conteggi["duplicato"],
        collisioni=conteggi["collisione"],
        mancanti=conteggi["missing"] + conteggi["file_ignoto"],
        saltati=conteggi["vuoto"] + conteggi["salta"] + conteggi["chiave_ignota"],
        errori=conteggi["errore"],
        righe=[
            RigaReport(
                tipo=candidato.stato,
                id_parent=candidato.id_parent,
                campo_foto=candidato.campo_foto,
                valore=candidato.valore_campo,
                percorso_file=candidato.percorso_file,
                nome_allegato=candidato.nome_allegato or candidato.nome_originale,
                motivo=candidato.motivo,
            )
            for candidato in candidati
            if candidato.stato not in ("ok", "collisione")
        ] + [
            RigaReport(
                tipo="collisione",
                id_parent=candidato.id_parent,
                campo_foto=candidato.campo_foto,
                valore=candidato.valore_campo,
                percorso_file=candidato.percorso_file,
                nome_allegato=candidato.nome_allegato,
                motivo=candidato.motivo,
            )
            for candidato in candidati
            if candidato.stato == "collisione"
        ],
    )

    if statistica is not None:
        report.duplicati += getattr(statistica, "duplicati", 0)
        report.saltati += getattr(statistica, "saltati", 0)
        report.errori += len(getattr(statistica, "errori", []) or [])
        report.annullata = bool(getattr(statistica, "annullata", False))
        for descrizione, errore in (getattr(statistica, "errori", []) or []):
            report.righe.append(RigaReport(
                tipo="errore", id_parent="", campo_foto="",
                valore=descrizione, percorso_file="", nome_allegato="",
                motivo=str(errore),
            ))

    for avviso in (avvisi or []):
        codice, dettaglio = (avviso if isinstance(avviso, (tuple, list)) else (avviso, ""))
        report.righe.append(RigaReport(
            tipo="avviso",
            motivo=f"{codice}: {dettaglio}".strip(": "),
        ))

    return report


# ---------------------------------------------------------------- export CSV


def scrivi_report_csv(percorso: str, righe, intestazioni=None, traduttore=None,
                      solo_anomalie: bool = True) -> str:
    """Esporta le righe del report in CSV (UTF-8 con BOM, apribile in Excel).

    :param righe: iterabile di :class:`RigaReport`
    :param intestazioni: intestazioni già tradotte (default: quelle italiane)
    :param traduttore: ``f(codice_stato) -> testo`` per la colonna *Tipo*
    :param solo_anomalie: esporta solo i mancanti/gli errori (default), oppure tutto
    :return: il percorso scritto
    """
    righe = list(righe)
    if solo_anomalie:
        righe = [r for r in righe if r.tipo in STATI_ANOMALI + ("avviso",)]
    traduttore = traduttore or (lambda codice: codice)

    cartella = os.path.dirname(os.path.abspath(percorso))
    if cartella:
        os.makedirs(cartella, exist_ok=True)
    with open(percorso, "w", encoding="utf-8-sig", newline="") as flusso:
        scrittore = csv.writer(flusso, delimiter=";")
        scrittore.writerow(list(intestazioni or INTESTAZIONI_CSV))
        for riga in righe:
            scrittore.writerow([
                traduttore(riga.tipo), riga.id_parent, riga.campo_foto, riga.valore,
                riga.percorso_file, riga.nome_allegato, riga.motivo,
            ])
    return percorso


def righe_da_esportare(report: ReportFinale, solo_anomalie: bool = True) -> list:
    """Le righe da esportare, per la UI (e per i test)."""
    if solo_anomalie:
        return report.anomalie()
    return list(report.righe)
