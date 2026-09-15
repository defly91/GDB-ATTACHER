# -*- coding: utf-8 -*-
"""wizard/dialog.py — il wizard in 7 passi (ordine deciso dal ticket 03).

Ordine letterale degli step:

1. **Layer sorgente** — solo layer vettoriali già in progetto su FileGDB (in v1 non si
   apre un ``.gdb`` a mano);
2. **Verifica bloccante** — è FileGDB? ha GlobalID? la tabella allegati c'è con i 6
   campi? Se qualcosa non torna il wizard si ferma e rimanda ad ArcGIS Pro;
3. **Discovery campi foto** — cartella base + euristica (la cartella base sta *qui*,
   non al passo 4: il verdetto 1 del ticket 05 dice che serve alla discovery);
4. **Scelta campi** — A/B preselezionati, C da rivedere, D nascosto (mostrabile);
5. **Naming** — tre modalità esclusive, anteprima con 5 feature campione e conteggi;
6. **Esegui** — riepilogo, backup proposto e aggirabile, conferma, batch in una sola
   transazione con barra di avanzamento annullabile, report finale ed export CSV;
7. **Stile** — QML «variante A» incluso nel plugin, applicato alla fine (o saltato).

Lingua: le stringhe arrivano tutte da ``wizard/strings.py`` (IT/EN); il wizard le
congela all'apertura (``self.lingua``), così la UI non può restare a metà fra due
lingue.
"""

from __future__ import annotations

import os

from qgis.core import QgsProject
from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtWidgets import (QApplication, QCheckBox, QComboBox, QFileDialog, QGridLayout,
                                 QGroupBox, QHBoxLayout, QLabel, QLineEdit, QMessageBox,
                                 QProgressBar, QPushButton, QRadioButton, QTableWidget,
                                 QTableWidgetItem, QVBoxLayout, QWizard, QWizardPage)

from ..core import attach, discovery, naming, report as modulo_report, styles
from . import strings


def t_livello(codice, lingua):
    """Etichetta leggibile di un livello di discovery (A/B/C/D)."""
    chiave = {"A": "livello_a", "B": "livello_b", "C": "livello_c", "D": "livello_d"}
    return strings.tr(chiave.get(codice, "livello_d"), lingua)


def righe_da_layer(layer, campi_foto, campo_globalid):
    """Estrae dal layer sorgente le coppie (feature, campo foto) da elaborare.

    Galleria multi-foto: più campi foto selezionati producono più righe per la
    stessa feature, quindi più allegati, in un solo giro (ticket 07).
    """
    righe = []
    for indice, feature in enumerate(layer.getFeatures(), start=1):
        id_parent = feature[campo_globalid]
        for campo in campi_foto:
            righe.append(naming.RigaSorgente(
                id_parent="" if id_parent is None else str(id_parent),
                campo_foto=campo,
                valore=feature[campo],
                indice_feature=indice,
                feature=feature,
            ))
    return righe


class PaginaBase(QWizardPage):
    """Base comune: accesso al wizard, alla lingua e ai traduttori."""

    def __init__(self, wizard, chiave_titolo):
        super().__init__(wizard)
        self.w = wizard
        self.setTitle(self.t(chiave_titolo))

    def t(self, chiave, **valori):
        return self.w.t(chiave, **valori)

    # -------------------------------------------------- utilità comuni

    def _tabella(self, intestazioni, altezza_riga=None):
        tabella = QTableWidget(0, len(intestazioni))
        tabella.setHorizontalHeaderLabels(list(intestazioni))
        tabella.setEditTriggers(QTableWidget.NoEditTriggers)
        tabella.setSelectionMode(QTableWidget.NoSelection)
        tabella.verticalHeader().setVisible(False)
        if altezza_riga:
            tabella.verticalHeader().setDefaultSectionSize(altezza_riga)
        return tabella

    def _riempi(self, tabella, righe):
        tabella.setRowCount(0)
        for numero, celle in enumerate(righe):
            tabella.insertRow(numero)
            for colonna, valore in enumerate(celle):
                testo = "" if valore is None else str(valore)
                elemento = QTableWidgetItem(testo)
                if testo and "mancante" in testo.lower():
                    elemento.setForeground(Qt.red)
                tabella.setItem(numero, colonna, elemento)
        tabella.resizeColumnsToContents()


class PaginaLayer(PaginaBase):
    """Passo 1 — scelta del layer sorgente fra quelli già in progetto su FileGDB."""

    def __init__(self, wizard):
        super().__init__(wizard, "pagina_layer")

        self.combo = QComboBox()
        self.combo.currentIndexChanged.connect(self._aggiorna_origine)
        self.etichetta_origine = QLabel()
        self.etichetta_origine.setWordWrap(True)
        self.etichetta_vuoto = QLabel(self.t("nessun_layer_filegdb"))
        self.etichetta_vuoto.setWordWrap(True)
        self.bottone_aggiorna = QPushButton(self.t("aggiorna"))
        self.bottone_aggiorna.clicked.connect(self.ricarica)

        disposizione = QVBoxLayout(self)
        disposizione.addWidget(QLabel(self.t("label_layer")))
        riga = QHBoxLayout()
        riga.addWidget(self.combo, 1)
        riga.addWidget(self.bottone_aggiorna)
        disposizione.addLayout(riga)
        disposizione.addWidget(self.etichetta_origine)
        disposizione.addWidget(self.etichetta_vuoto)
        nota = QLabel(self.t("nota_solo_filegdb"))
        nota.setWordWrap(True)
        nota.setStyleSheet("color:#555")
        disposizione.addWidget(nota)
        disposizione.addStretch(1)

    def ricarica(self):
        """Ripopola l'elenco con i soli layer vettoriali su FileGDB.

        La scelta non si perde: tornando indietro dal passo 2 (o premendo
        «Aggiorna») il combo si riempie di nuovo ma resta selezionato lo stesso
        layer. Senza questo, la scelta cadeva sul primo della lista e si
        proseguiva scrivendo su un altro GDB.
        """
        scelto = self._id_da_riselezionare()
        self.combo.blockSignals(True)
        try:
            self.combo.clear()
            for layer in self.w.layer_filegdb():
                self.combo.addItem(
                    f"{_nome(layer)}  —  "
                    f"{os.path.basename(attach.percorso_gdb(layer.source()) or layer.source())}",
                    layer.id(),
                )
            indice = self.combo.findData(scelto) if scelto else -1
            if indice < 0 and self.combo.count():
                indice = 0
            self.combo.setCurrentIndex(indice)
        finally:
            self.combo.blockSignals(False)
        self.etichetta_vuoto.setVisible(self.combo.count() == 0)
        self.bottone_aggiorna.setEnabled(True)
        self._aggiorna_origine()
        self.completeChanged.emit()

    def _id_da_riselezionare(self):
        """Id del layer da riselezionare dopo il ripopolamento.

        Prima la scelta corrente del combo, poi il layer su cui il wizard sta
        lavorando: la selezione non deve mai ``cadere`` su un altro layer.
        """
        if self.combo.count():
            corrente = self.combo.currentData()
            if corrente:
                return corrente
        layer = getattr(self.w, "layer_sorgente", None)
        if layer is not None:
            try:
                return layer.id()
            except Exception:
                return None
        return None

    def initializePage(self):  # noqa: N802
        self.ricarica()

    def _aggiorna_origine(self):
        layer = self.layer_scelto()
        self.etichetta_origine.setText(
            self.t("origine_layer", origine=layer.source() if layer is not None else "—")
        )

    def layer_scelto(self):
        if self.combo.count() == 0 or self.combo.currentIndex() < 0:
            return None
        return self.w.progetto.mapLayer(self.combo.currentData())

    def isComplete(self):  # noqa: N802
        return self.layer_scelto() is not None

    def validatePage(self):  # noqa: N802
        layer = self.layer_scelto()
        if layer is None:
            return False
        self.w.layer_sorgente = layer
        self.w.esito = None
        self.w.cartella_base = ""
        self.w.righe_discovery = []
        self.w.candidati = []
        self.w.report = None
        self.w.eseguito = False
        return True


class PaginaVerifica(PaginaBase):
    """Passo 2 — verifica bloccante (ticket 02 e 03): qui non si scrive niente."""

    def __init__(self, wizard):
        super().__init__(wizard, "pagina_verifica")
        self.bottone = QPushButton(self.t("verifica_esegui"))
        self.bottone.clicked.connect(self.esegui_verifiche)
        self.tabella = self._tabella((self.t("col_controllo"), self.t("col_esito"), self.t("col_dettaglio")))
        self.messaggio = QLabel()
        self.messaggio.setWordWrap(True)
        self.messaggio.setOpenExternalLinks(False)
        self.messaggio.setTextInteractionFlags(Qt.TextSelectableByMouse)

        disposizione = QVBoxLayout(self)
        disposizione.addWidget(QLabel(self.t("titolo_verifica")))
        disposizione.addWidget(self.bottone)
        disposizione.addWidget(self.tabella, 1)
        disposizione.addWidget(self.messaggio, 1)

    def initializePage(self):  # noqa: N802
        self.esegui_verifiche()

    def esegui_verifiche(self):
        """Esegue i controlli e li mostra tutti in tabella (nessun blocco silenzioso)."""
        layer = self.w.layer_sorgente
        if layer is None:
            return
        esito = attach.verifica_completa(self.w.progetto, layer)
        self.w.esito = esito

        righe = [
            (self.t("ctrl_filegdb"), self._esito(esito.layer.e_filegdb),
             attach.percorso_gdb(layer.source()) or layer.source()),
            (self.t("ctrl_globalid"), self._esito(bool(esito.layer.campo_globalid)),
             esito.layer.campo_globalid or "—"),
            (self.t("ctrl_attach"), self._esito(esito.tabella.presente),
             attach.nome_tabella_allegati(layer.name())),
            (self.t("ctrl_campi_attach"), self._esito(esito.tabella.completa),
             "—" if esito.tabella.completa else ", ".join(esito.tabella.mancanti)),
        ]
        if any(problema.codice == "locale_non_scrivibile" for problema in esito.layer.problemi):
            righe.append((self.t("ctrl_scrittura"), self._esito(False), ""))
        self._riempi(self.tabella, righe)

        if esito.bloccante:
            self.messaggio.setText(self._testo_blocco(esito))
            self.messaggio.setStyleSheet("color:#a00")
        else:
            self.messaggio.setText(self.t("verifica_ok"))
            self.messaggio.setStyleSheet("color:#060")
        self.completeChanged.emit()

    def _esito(self, ok):
        return self.t("esito_ok") if ok else self.t("esito_ko")

    def _testo_blocco(self, esito):
        """Messaggio di blocco, con il rimando ad ArcGIS Pro quando c'entra la tabella."""
        pezzi = [self.t("verifica_bloccata")]
        nome_tabella = attach.nome_tabella_allegati(
            self.w.layer_sorgente.name() if self.w.layer_sorgente else ""
        )
        for problema in esito.layer.problemi:
            chiave = strings.TESTI_PROBLEMA.get(problema.codice)
            if not chiave:
                continue
            pezzi.append(self.t(
                chiave,
                layer=self.w.layer_sorgente.name() if self.w.layer_sorgente else "",
                origine=problema.dettaglio or "—",
                tabella=nome_tabella,
                campi=", ".join(esito.tabella.mancanti) or "—",
                come=self.t("come_abilitare"),
            ))
        if not esito.tabella.presente or not esito.tabella.completa:
            pezzi.append(attach.messaggio_abilitazione(
                self.w.layer_sorgente.name() if self.w.layer_sorgente else "", self.w.lingua
            ))
        return "\n\n".join(pezzi)

    def isComplete(self):  # noqa: N802
        esito = self.w.esito
        return bool(esito) and not esito.bloccante

    def validatePage(self):  # noqa: N802
        return self.isComplete()


class PaginaDiscovery(PaginaBase):
    """Passo 3 — cartella base + euristica di discovery (ticket 05)."""

    def __init__(self, wizard):
        super().__init__(wizard, "pagina_discovery")

        self.cartella = QLineEdit()
        self.cartella.editingFinished.connect(self._cambia_cartella)
        self.bottone_cartella = QPushButton(self.t("sfoglia"))
        self.bottone_cartella.clicked.connect(self.scegli_cartella)
        self.bottone = QPushButton(self.t("scansiona"))
        self.bottone.clicked.connect(self.scansiona)
        self.tabella = self._tabella((
            self.t("col_livello"), self.t("col_campo"), self.t("col_tipo"), self.t("col_valori"),
            self.t("col_esiste"), self.t("col_multi"), self.t("col_nome"), self.t("col_motivo"),
            self.t("col_esempi"),
        ))
        self.legenda = QLabel(self.t("legenda_livelli"))
        self.legenda.setWordWrap(True)
        self.stato = QLabel("")

        disposizione = QVBoxLayout(self)
        testo = QLabel(self.t("testo_discovery"))
        testo.setWordWrap(True)
        disposizione.addWidget(testo)
        riga = QHBoxLayout()
        riga.addWidget(QLabel(self.t("label_cartella_base")))
        riga.addWidget(self.cartella, 1)
        riga.addWidget(self.bottone_cartella)
        disposizione.addLayout(riga)
        disposizione.addWidget(self.bottone)
        disposizione.addWidget(self.tabella, 1)
        disposizione.addWidget(self.legenda)
        disposizione.addWidget(self.stato)

    def initializePage(self):  # noqa: N802
        self.cartella.setText(self.w.cartella_base)
        if not self.w.righe_discovery:
            self.scansiona()

    def scegli_cartella(self):
        cartella = QFileDialog.getExistingDirectory(self, self.t("label_cartella_base"),
                                                    self.cartella.text() or "")
        if cartella:
            self.cartella.setText(cartella)
            self._cambia_cartella()

    def _cambia_cartella(self):
        """Cambiare cartella invalida la misura: la cache dell'indice va svuotata."""
        cartella = self.cartella.text().strip()
        if cartella == self.w.cartella_base:
            return
        discovery.IndiceFile.pulisci_cache()
        self.w.cartella_base = cartella
        self.w.righe_discovery = []
        self.completeChanged.emit()

    def scansiona(self):
        cartella = self.cartella.text().strip()
        if cartella and not os.path.isdir(cartella):
            QMessageBox.warning(self, self.t("attenzione_titolo"),
                                self.t("cartella_base_non_valida", cartella=cartella))
            return
        self.w.cartella_base = cartella
        self.stato.setText(self.t("scansione_in_corso"))
        QApplication.processEvents()
        self.w.righe_discovery = discovery.suggerisci_campi(self.w.layer_sorgente, cartella)
        righe = [
            (t_livello(r.livello, self.w.lingua), r.campo, r.tipo, f"{r.n_non_null}/{r.n_valori}",
             f"{r.esiste_rate:.0%}", f"{r.multi_rate:.0%}", "sì" if r.nome_match else "—",
             r.motivo, " · ".join(r.esempi))
            for r in self.w.righe_discovery
        ]
        self._riempi(self.tabella, righe)
        if not cartella:
            self.stato.setText(self.t("cartella_base_vuota"))
        elif not righe:
            self.stato.setText(self.t("nessun_campo_trovato"))
        elif any(r.livello == "B" for r in self.w.righe_discovery):
            self.stato.setText(self.t("avviso_livello_b"))
        else:
            self.stato.setText(self.t("legenda_livelli"))
        self.completeChanged.emit()

    def isComplete(self):  # noqa: N802
        return bool(self.w.righe_discovery)


class PaginaCampi(PaginaBase):
    """Passo 4 — selezione dei campi foto (A/B preselezionati, C da rivedere, D nascosto)."""

    def __init__(self, wizard):
        super().__init__(wizard, "pagina_campi")

        self.mostra_d = QCheckBox(self.t("altri_campi"))
        self.mostra_d.stateChanged.connect(self._riempi_tabella)
        self.tabella = self._tabella((self.t("col_scelto"), self.t("col_campo"), self.t("col_livello"),
                                      self.t("col_motivo")))
        self.tabella.itemChanged.connect(lambda _i: self.completeChanged.emit())
        self.riepilogo = QLabel("")
        self.riepilogo.setWordWrap(True)

        disposizione = QVBoxLayout(self)
        testo = QLabel(self.t("testo_campi"))
        testo.setWordWrap(True)
        disposizione.addWidget(testo)
        nota = QLabel(self.t("nota_cartella_prima"))
        nota.setWordWrap(True)
        nota.setStyleSheet("color:#555")
        disposizione.addWidget(nota)
        disposizione.addWidget(self.mostra_d)
        disposizione.addWidget(self.tabella, 1)
        disposizione.addWidget(self.riepilogo)

    def initializePage(self):  # noqa: N802
        self._riempi_tabella()

    def _righe_visibili(self):
        righe = self.w.righe_discovery
        return [r for r in righe if self.mostra_d.isChecked() or r.livello != "D"]

    def _riempi_tabella(self):
        righe = self._righe_visibili()
        self.tabella.blockSignals(True)
        self.tabella.setRowCount(0)
        for numero, riga in enumerate(righe):
            self.tabella.insertRow(numero)
            elemento = QTableWidgetItem()
            elemento.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
            elemento.setCheckState(Qt.Checked if riga.preselezionato else Qt.Unchecked)
            self.tabella.setItem(numero, 0, elemento)
            for colonna, testo in enumerate(
                (riga.campo, t_livello(riga.livello, self.w.lingua), riga.motivo), start=1
            ):
                self.tabella.setItem(numero, colonna, QTableWidgetItem(str(testo)))
        self.tabella.resizeColumnsToContents()
        self.tabella.blockSignals(False)
        self.completeChanged.emit()

    def campi_scelti(self):
        scelti = []
        for numero, riga in enumerate(self._righe_visibili()):
            elemento = self.tabella.item(numero, 0)
            if elemento is not None and elemento.checkState() == Qt.Checked:
                scelti.append(riga.campo)
        return scelti

    def isComplete(self):  # noqa: N802
        return bool(self.campi_scelti())

    def validatePage(self):  # noqa: N802
        scelti = self.campi_scelti()
        if not scelti:
            QMessageBox.warning(self, self.t("attenzione_titolo"), self.t("nessun_campo_scelto"))
            return False
        self.w.campi_scelti = scelti
        self.riepilogo.setText(self.t("riepilogo_campi", n=len(scelti),
                                      cartella=self.w.cartella_base or self.t("nessuno")))
        return True


class PaginaNaming(PaginaBase):
    """Passo 5 — tre modalità di nome allegato, anteprima a 5 esempi e conteggi."""

    def __init__(self, wizard):
        super().__init__(wizard, "pagina_naming")

        # --- modalità
        self.radio_originale = QRadioButton(self.t("modo_originale"))
        self.radio_originale.setChecked(True)
        self.radio_formula = QRadioButton(self.t("modo_formula"))
        self.radio_csv = QRadioButton(self.t("modo_csv"))
        for radio in (self.radio_originale, self.radio_formula, self.radio_csv):
            radio.toggled.connect(self._cambia_modalita)

        gruppo = QGroupBox(self.t("titolo_naming"))
        disposizione_gruppo = QVBoxLayout(gruppo)
        for radio, chiave in ((self.radio_originale, "desc_originale"),
                              (self.radio_formula, "desc_formula"),
                              (self.radio_csv, "desc_csv")):
            disposizione_gruppo.addWidget(radio)
            descrizione = QLabel("    " + self.t(chiave))
            descrizione.setWordWrap(True)
            descrizione.setStyleSheet("color:#555")
            disposizione_gruppo.addWidget(descrizione)

        # --- formula
        self.formula = QLineEdit()
        self.formula.setPlaceholderText('@stem || "_" || "CODICE" || @ext')
        self.formula.textChanged.connect(lambda _t: self.completeChanged.emit())
        self.aiuto_formula = QLabel(self.t("aiuto_formula"))
        self.aiuto_formula.setWordWrap(True)
        self.bottone_prova = QPushButton(self.t("formula_prova"))
        self.bottone_prova.clicked.connect(self.prova_formula)
        self.gruppo_formula = QGroupBox()
        disposizione_formula = QVBoxLayout(self.gruppo_formula)
        disposizione_formula.addWidget(self.formula)
        disposizione_formula.addWidget(self.aiuto_formula)
        disposizione_formula.addWidget(self.bottone_prova)

        # --- CSV
        self.csv_percorso = QLineEdit()
        self.csv_percorso.editingFinished.connect(self._carica_csv)
        self.bottone_csv = QPushButton(self.t("sfoglia"))
        self.bottone_csv.clicked.connect(self.scegli_csv)
        self.csv_chiave = QComboBox()
        self.csv_chiave.currentIndexChanged.connect(self._carica_csv)
        self.csv_colonna_file = QComboBox()
        self.csv_colonna_file.currentIndexChanged.connect(lambda _i: self.completeChanged.emit())
        self.csv_colonna_nome = QComboBox()
        self.csv_info = QLabel("")
        self.csv_info.setWordWrap(True)
        self.gruppo_csv = QGroupBox()
        disposizione_csv = QGridLayout(self.gruppo_csv)
        disposizione_csv.addWidget(QLabel(self.t("csv_file")), 0, 0)
        disposizione_csv.addWidget(self.csv_percorso, 0, 1)
        disposizione_csv.addWidget(self.bottone_csv, 0, 2)
        disposizione_csv.addWidget(QLabel(self.t("csv_chiave")), 1, 0)
        disposizione_csv.addWidget(self.csv_chiave, 1, 1)
        disposizione_csv.addWidget(QLabel(self.t("csv_col_file")), 2, 0)
        disposizione_csv.addWidget(self.csv_colonna_file, 2, 1)
        disposizione_csv.addWidget(QLabel(self.t("csv_col_attname")), 3, 0)
        disposizione_csv.addWidget(self.csv_colonna_nome, 3, 1)
        disposizione_csv.addWidget(self.csv_info, 4, 0, 1, 3)

        # --- comportamento sui nomi già presenti (dedup, ticket 07)
        self.nomi_esistenti = QComboBox()
        self.nomi_esistenti.addItem(self.t("opzione_salta_duplicati"), False)
        self.nomi_esistenti.addItem(self.t("opzione_rinomina_duplicati"), True)
        self.nomi_esistenti.currentIndexChanged.connect(lambda _i: self.aggiorna_anteprima())
        nota_duplicati = QLabel(self.t("nota_duplicati"))
        nota_duplicati.setWordWrap(True)
        nota_duplicati.setStyleSheet("color:#555")
        gruppo_dedup = QGroupBox(self.t("nomi_esistenti_titolo"))
        disposizione_dedup = QVBoxLayout(gruppo_dedup)
        disposizione_dedup.addWidget(self.nomi_esistenti)
        disposizione_dedup.addWidget(nota_duplicati)

        # --- anteprima
        self._cache_chiavi = None
        self.bottone_anteprima = QPushButton(self.t("aggiorna_anteprima"))
        self.bottone_anteprima.clicked.connect(self.aggiorna_anteprima)
        self.etichetta_anteprima = QLabel(self.t("anteprima_5"))
        self.tabella = self._tabella((self.t("col_campo_foto"), self.t("col_valore_campo"),
                                      self.t("col_percorso"), self.t("col_nome_finale"),
                                      self.t("col_stato")))
        self.conteggi = QLabel("")
        self.conteggi.setWordWrap(True)
        self.per_campo = QLabel("")
        self.per_campo.setWordWrap(True)

        disposizione = QVBoxLayout(self)
        intestazione = QLabel(self.t("testo_naming"))
        intestazione.setWordWrap(True)
        disposizione.addWidget(intestazione)
        disposizione.addWidget(gruppo)
        disposizione.addWidget(self.gruppo_formula)
        disposizione.addWidget(self.gruppo_csv)
        disposizione.addWidget(gruppo_dedup)
        disposizione.addWidget(self.bottone_anteprima)
        disposizione.addWidget(self.etichetta_anteprima)
        disposizione.addWidget(self.tabella, 1)
        disposizione.addWidget(self.conteggi)
        disposizione.addWidget(self.per_campo)

    # -------------------------------------------------- modalità

    def initializePage(self):  # noqa: N802
        self._cambia_modalita()
        self.aggiorna_anteprima()

    def modalita(self):
        if self.radio_formula.isChecked():
            return naming.MODALITA_FORMULA
        if self.radio_csv.isChecked():
            return naming.MODALITA_CSV
        return naming.MODALITA_ORIGINALE

    def _cambia_modalita(self, *_):
        modalita = self.modalita()
        self.gruppo_formula.setVisible(modalita == naming.MODALITA_FORMULA)
        self.gruppo_csv.setVisible(modalita == naming.MODALITA_CSV)
        self.w.modalita = modalita
        self.completeChanged.emit()

    # -------------------------------------------------- formula

    def prova_formula(self):
        errore, avviso = naming.verifica_formula(self.formula.text(), self.w.layer_sorgente)
        if errore:
            QMessageBox.warning(self, self.t("formula_non_valida", errore=errore), errore)
        elif avviso:
            QMessageBox.information(self, self.t("attenzione_titolo"), avviso)
        else:
            QMessageBox.information(self, self.t("formula_prova"), self.t("verifica_ok"))
        self.completeChanged.emit()

    # -------------------------------------------------- CSV

    def scegli_csv(self):
        percorso, _filtro = QFileDialog.getOpenFileName(
            self, self.t("csv_file"), self.csv_percorso.text() or "", "CSV (*.csv *.txt);;Tutti i file (*)"
        )
        if percorso:
            self.csv_percorso.setText(percorso)
            self._carica_csv()

    def _carica_csv(self):
        """Legge il CSV: popola le colonne e blocca solo se è illeggibile o senza chiave."""
        percorso = self.csv_percorso.text().strip()
        self.w.elenco_csv = None
        if not percorso:
            self.csv_info.setText("")
            self.completeChanged.emit()
            return

        intestazioni, separatore, codifica = naming.intestazioni_csv(percorso)
        if not intestazioni:
            self.csv_info.setText(self.t("csv_blocco_illegibile", errore=separatore))
            self.completeChanged.emit()
            return

        self._riempi_combo(self.csv_chiave, intestazioni, preferiti=naming.NOMI_COLONNA_CHIAVE,
                           predefinito="GLOBALID")
        self._riempi_combo(self.csv_colonna_file, intestazioni, preferiti=naming.NOMI_COLONNA_FILE)
        self._riempi_combo(self.csv_colonna_nome, intestazioni, preferiti=naming.NOMI_COLONNA_NOME,
                           vuoto=self.t("nessuno"))

        chiave = self.csv_chiave.currentText()
        try:
            elenco = naming.leggi_csv_allegati(
                percorso, chiave=chiave,
                colonna_file=self.csv_colonna_file.currentText() or None,
                colonna_att_name=self.csv_colonna_nome.currentText() or None,
            )
        except ValueError as errore:
            testo = str(errore)
            chiave_assente = "chiave" in testo
            self.csv_info.setText(
                self.t("csv_blocco_chiave", colonna=chiave) if chiave_assente
                else self.t("csv_blocco_illegibile", errore=testo)
            )
            self.completeChanged.emit()
            return

        self.w.elenco_csv = elenco
        self.w.colonna_chiave_csv = chiave
        messaggi = [self.t("csv_separatore", separatore=elenco.separatore),
                    self.t("csv_encoding", encoding=elenco.encoding),
                    self.t("csv_righe", n=len(elenco.righe))]
        for codice, dettaglio in elenco.avvisi:
            if codice == "chiavi_duplicate":
                messaggi.append(self.t("csv_avviso_chiavi_duplicate", n=dettaglio))
            elif codice == "colonna_file_da_indicare":
                messaggi.append(self.t("csv_avviso_chiave_mancante", colonna=naming.NOMI_COLONNA_FILE[0]))
            elif codice == "colonna_mancante":
                messaggi.append(self.t("csv_avviso_chiave_mancante", colonna=dettaglio))
        self.csv_info.setText(" · ".join(messaggi))
        self.completeChanged.emit()

    def _riempi_combo(self, combo, valori, preferiti=(), predefinito="", vuoto=""):
        combo.blockSignals(True)
        combo.clear()
        if vuoto:
            combo.addItem(vuoto)
        for valore in valori:
            combo.addItem(valore)
        scelto = _trova_preferito(valori, preferiti) or predefinito
        if scelto:
            indice = combo.findText(scelto)
            if indice >= 0:
                combo.setCurrentIndex(indice)
        combo.blockSignals(False)

    # -------------------------------------------------- candidati e anteprima

    def comportamento_rinomina(self):
        return bool(self.nomi_esistenti.currentData())

    def chiavi_tabella_esistenti(self, forza: bool = False):
        """Coppie ``(REL_GLOBALID, ATT_NAME)`` già nella tabella allegati (deduplica).

        La lettura è in cache: la tabella non cambia mentre si costruisce l'anteprima,
        e su tabelle grandi una passata sola è già abbastanza.
        """
        if self._cache_chiavi is not None and not forza:
            return self._cache_chiavi
        layer_allegati = getattr(self.w.esito, "layer_allegati", None) if self.w.esito else None
        if layer_allegati is None:
            self._cache_chiavi = set()
            return self._cache_chiavi
        campi = attach.risolvi_campi_allegati(layer_allegati)[0]
        self._cache_chiavi = attach.carica_chiavi_esistenti(layer_allegati, campi)
        return self._cache_chiavi

    def costruisci_candidati(self, salva=True):
        """Costruisce i candidati secondo modalità, campi, cartella base e CSV."""
        w = self.w
        risolutore = discovery.risolutore_file(w.cartella_base)
        if w.modalita == naming.MODALITA_CSV and w.elenco_csv is None:
            return []

        if w.modalita == naming.MODALITA_CSV:
            righe = righe_da_layer(w.layer_sorgente, w.campi_scelti,
                                   w.esito.layer.campo_globalid)
            candidati = naming.candidati_da_csv(w.elenco_csv, righe, risolutore)
        else:
            righe = righe_da_layer(w.layer_sorgente, w.campi_scelti,
                                   w.esito.layer.campo_globalid)
            valutatore = (naming.valutatore_qgis(w.layer_sorgente)
                          if w.modalita == naming.MODALITA_FORMULA else None)
            candidati = naming.candidati_da_campi(
                righe, risolutore, modalita=w.modalita,
                espressione=self.formula.text(), valutatore=valutatore,
            )

        esistenti = self.chiavi_tabella_esistenti()
        candidati = naming.risolvi_collisioni(
            candidati, esistenti, self.comportamento_rinomina()
        )
        if salva:
            w.candidati = candidati
            w.chiavi_esistenti = set(esistenti)
        return candidati

    def aggiorna_anteprima(self):
        try:
            candidati = self.costruisci_candidati()
        except Exception as errore:
            # Un errore di costruzione (formula rotta, CSV sparito) si mostra e basta:
            # il wizard resta aperto e l'utente corregge.
            self.conteggi.setText(self.t("formula_non_valida", errore=errore))
            self.conteggi.setStyleSheet("color:#a00")
            return
        avvisi = list(self.w.elenco_csv.avvisi) if self.w.elenco_csv else []
        anteprima = modulo_report.costruisci_anteprima(candidati, 5, avvisi)
        righe = [
            (e.campo_foto, e.valore_campo, e.percorso_file or "—",
             e.nome_allegato or "—", self._stato(e.stato))
            for e in anteprima.esempi
        ]
        self._riempi(self.tabella, righe)

        conteggi = anteprima.conteggi
        self.conteggi.setText("   ".join([
            self.t("totale_ok", n=conteggi["ok"] + conteggi["collisione"]),
            self.t("atto_totale_duplicati", n=conteggi["duplicato"]),
            self.t("totale_missing", n=conteggi["missing"] + conteggi["file_ignoto"]),
            self.t("totale_collisioni", n=conteggi["collisione"]),
            self.t("totale_saltati", n=conteggi["saltati"] + conteggi["salta"]),
        ]))
        per_campo = " · ".join(f"{campo}: {n}" for campo, n in anteprima.conteggi_per_campo.items())
        self.per_campo.setText(f"{self.t('conteggi_per_campo')} {per_campo or '—'}   "
                               f"{self.t('nota_galleria')}")
        self.completeChanged.emit()

    def _stato(self, codice):
        return strings.tr(strings.TESTI_STATO.get(codice, "stato_ok"), self.w.lingua)

    def isComplete(self):  # noqa: N802
        modalita = self.modalita()
        if modalita == naming.MODALITA_FORMULA:
            return bool(self.formula.text().strip())
        if modalita == naming.MODALITA_CSV:
            return self.w.elenco_csv is not None
        return True

    def validatePage(self):  # noqa: N802
        self.w.modalita = self.modalita()
        self.w.formula = self.formula.text()
        self.w.rinomina_se_esistente = self.comportamento_rinomina()
        self.aggiorna_anteprima()
        if self.w.modalita == naming.MODALITA_CSV and self.w.elenco_csv is None:
            QMessageBox.warning(self, self.t("attenzione_titolo"), self.t("csv_blocco_illegibile",
                                                                          errore="CSV mancante"))
            return False
        return True


class PaginaEsegui(PaginaBase):
    """Passo 6 — conferma, backup aggirabile, batch in transazione unica, report."""

    def __init__(self, wizard):
        super().__init__(wizard, "pagina_esegui")

        self.riepilogo = QLabel("")
        self.riepilogo.setWordWrap(True)
        self.contatori = QLabel("")
        self.contatori.setWordWrap(True)

        self.radio_backup = QRadioButton(self.t("backup_attivo"))
        self.radio_backup.setChecked(True)
        self.radio_senza_backup = QRadioButton(self.t("backup_senza"))
        self.cartella_backup = QLineEdit()
        self.bottone_cartella_backup = QPushButton(self.t("sfoglia"))
        self.bottone_cartella_backup.clicked.connect(self.scegli_cartella_backup)
        gruppo_backup = QGroupBox(self.t("backup_titolo"))
        disposizione_backup = QGridLayout(gruppo_backup)
        disposizione_backup.addWidget(self.radio_backup, 0, 0)
        disposizione_backup.addWidget(self.radio_senza_backup, 1, 0)
        disposizione_backup.addWidget(QLabel(self.t("backup_cartella")), 2, 0)
        disposizione_backup.addWidget(self.cartella_backup, 2, 1)
        disposizione_backup.addWidget(self.bottone_cartella_backup, 2, 2)
        avviso_backup = QLabel(self.t("backup_desc"))
        avviso_backup.setWordWrap(True)
        avviso_backup.setStyleSheet("color:#555")
        disposizione_backup.addWidget(avviso_backup, 3, 0, 1, 3)
        self.radio_backup.toggled.connect(lambda acceso: self.cartella_backup.setEnabled(acceso))

        self.conferma = QCheckBox(self.t("conferma_esecuzione"))
        self.conferma.stateChanged.connect(lambda _s: self._aggiorna_bottone())
        self.bottone_esegui = QPushButton(self.t("esegui"))
        self.bottone_esegui.clicked.connect(self.esegui)
        self.bottone_annulla = QPushButton(self.t("esecuzione_annulla"))
        self.bottone_annulla.clicked.connect(self.annulla_esecuzione)
        self.bottone_annulla.setEnabled(False)
        self.barra = QProgressBar()
        self.barra.setVisible(False)
        self.esito = QLabel("")
        self.esito.setWordWrap(True)
        self.bottone_export = QPushButton(self.t("export_missing"))
        self.bottone_export.clicked.connect(lambda: self.esporta(solo_anomalie=True))
        self.bottone_export.setEnabled(False)
        self.bottone_export_tutto = QPushButton(self.t("export_tutto"))
        self.bottone_export_tutto.clicked.connect(lambda: self.esporta(solo_anomalie=False))
        self.bottone_export_tutto.setEnabled(False)

        disposizione = QVBoxLayout(self)
        disposizione.addWidget(self.riepilogo)
        disposizione.addWidget(self.contatori)
        disposizione.addWidget(gruppo_backup)
        disposizione.addWidget(self.conferma)
        riga = QHBoxLayout()
        riga.addWidget(self.bottone_esegui)
        riga.addWidget(self.bottone_annulla)
        riga.addWidget(self.barra, 1)
        disposizione.addLayout(riga)
        disposizione.addWidget(self.esito, 1)
        riga_export = QHBoxLayout()
        riga_export.addWidget(self.bottone_export)
        riga_export.addWidget(self.bottone_export_tutto)
        riga_export.addStretch(1)
        disposizione.addLayout(riga_export)
        nota_report = QLabel(self.t("report_apri_cartella"))
        nota_report.setWordWrap(True)
        nota_report.setStyleSheet("color:#555")
        disposizione.addWidget(nota_report)
        self._annulla_richiesto = False

    # -------------------------------------------------- preparazione

    def initializePage(self):  # noqa: N802
        self.w.report = None
        self.w.eseguito = False
        layer = self.w.layer_sorgente
        tabella = attach.nome_tabella_allegati(layer.name()) if layer else "—"
        da_scrivere = sum(1 for c in self.w.candidati if c.da_scrivere)
        self.riepilogo.setText(self.t("riepilogo_esecuzione", ok=da_scrivere, tabella=tabella))
        # Conferma a conteggi (ticket 03): qui solo i numeri, il dettaglio sta nel naming.
        conteggi = naming.conteggi(self.w.candidati)
        self.contatori.setText("   ".join([
            self.t("totale_ok", n=conteggi["ok"] + conteggi["collisione"]),
            self.t("atto_totale_duplicati", n=conteggi["duplicato"]),
            self.t("totale_missing", n=conteggi["missing"] + conteggi["file_ignoto"]),
            self.t("totale_collisioni", n=conteggi["collisione"]),
            self.t("totale_saltati", n=conteggi["saltati"] + conteggi["salta"]),
        ]))
        self.contatori.setStyleSheet("color:#555")
        self.cartella_backup.setText(
            os.path.dirname(attach.percorso_gdb(layer.source())) if layer
            and attach.percorso_gdb(layer.source()) else ""
        )
        self.esito.setText("")
        self.esito.setStyleSheet("")
        self.barra.setVisible(False)
        self.barra.setValue(0)
        self.bottone_export.setEnabled(False)
        self.bottone_export_tutto.setEnabled(False)
        self._aggiorna_bottone()
        self.completeChanged.emit()

    def scegli_cartella_backup(self):
        cartella = QFileDialog.getExistingDirectory(self, self.t("backup_cartella"),
                                                    self.cartella_backup.text() or "")
        if cartella:
            self.cartella_backup.setText(cartella)

    def _aggiorna_bottone(self):
        self.bottone_esegui.setEnabled(
            self.conferma.isChecked() and not self.w.eseguito
            and any(c.da_scrivere for c in self.w.candidati)
        )

    # -------------------------------------------------- esecuzione

    def annulla_esecuzione(self):
        """Chiede l'annullo del batch: la transazione viene annullata, non committata."""
        self._annulla_richiesto = True
        self.bottone_annulla.setEnabled(False)

    def esegui(self):
        layer = self.w.layer_sorgente
        layer_allegati = self.w.esito.layer_allegati

        if self.radio_backup.isChecked():
            percorso_gdb = attach.percorso_gdb(layer.source()) if layer else ""
            if not percorso_gdb:
                QMessageBox.warning(self, self.t("attenzione_titolo"),
                                    self.t("backup_errore", errore=layer.source() if layer else ""))
                return
            try:
                destinazione = attach.backup_gdb(percorso_gdb, self.cartella_backup.text().strip() or None)
                self.esito.setText(self.t("backup_fatto", percorso=destinazione))
            except OSError as errore:
                QMessageBox.critical(self, self.t("backup_errore", errore=errore), str(errore))
                return

        candidati = [c for c in self.w.candidati if c.da_scrivere]
        campi = attach.risolvi_campi_allegati(layer_allegati)[0]

        self._annulla_richiesto = False
        self.barra.setVisible(True)
        self.barra.setRange(0, max(1, len(candidati)))
        self.barra.setValue(0)
        self.bottone_annulla.setEnabled(True)
        self.bottone_esegui.setEnabled(False)
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            statistica = attach.scrivi_allegati(
                layer_allegati, candidati, campi=campi,
                chiavi_esistenti=set(self.w.chiavi_esistenti),
                callback_progresso=self._progresso,
            )
        finally:
            QApplication.restoreOverrideCursor()
            self.bottone_annulla.setEnabled(False)

        self.w.statistica = statistica
        self.w.report = modulo_report.report_da_candidati(
            self.w.candidati, statistica,
            avvisi=list(self.w.elenco_csv.avvisi) if self.w.elenco_csv else [],
        )
        self.w.eseguito = True

        self.barra.setVisible(False)
        if statistica.annullata:
            self.esito.setText(self.t("esecuzione_annullata"))
            self.esito.setStyleSheet("color:#a60")
        else:
            self.esito.setText(self.t(
                "esito_scrittura",
                aggiunti=statistica.aggiunti,
                duplicati=self.w.report.duplicati,
                mancanti=self.w.report.mancanti,
                saltati=self.w.report.saltati,
                errori=self.w.report.errori,
            ))
            self.esito.setStyleSheet("color:#060")

        vuoto = not self.w.report.righe
        self.bottone_export.setEnabled(not vuoto)
        self.bottone_export_tutto.setEnabled(not vuoto)
        self.completeChanged.emit()

    def _progresso(self, indice, totale, candidato):
        """Aggiorna la barra e tiene viva la UI (batch di migliaia di file).

        Ritornare ``False`` annulla la scrittura: ``scrivi_allegati`` solleva
        ``EsecuzioneAnnullata`` e la transazione non viene committata.
        """
        if self._annulla_richiesto:
            return False
        if indice == 1 or indice % 10 == 0 or indice == totale:
            self.barra.setValue(indice)
            self.barra.setFormat(f"{indice}/{totale} — {candidato.nome_allegato}")
            QApplication.processEvents()
        return True

    # -------------------------------------------------- export

    def esporta(self, solo_anomalie=True):
        if self.w.report is None:
            return
        intestazioni = (self.t("col_tipo_riga"), self.t("col_feature"), self.t("col_campo_foto"),
                        self.t("col_valore"), self.t("col_percorso_file"),
                        self.t("col_nome_allegato"), self.t("col_motivo"))
        percorso, _filtro = QFileDialog.getSaveFileName(
            self, self.t("export_missing"), "report_allegati.csv", "CSV (*.csv)"
        )
        if not percorso:
            return
        modulo_report.scrivi_report_csv(
            percorso, self.w.report.righe, intestazioni=intestazioni,
            traduttore=lambda codice: strings.tr(strings.TESTI_STATO.get(codice, "stato_ok"),
                                                  self.w.lingua),
            solo_anomalie=solo_anomalie,
        )
        self.esito.setText(self.t("report_salvato", percorso=percorso))

    def isComplete(self):  # noqa: N802
        return self.w.eseguito


class PaginaStile(PaginaBase):
    """Passo 7 — stile «variante A» (QML incluso nel plugin), applicato alla fine."""

    def __init__(self, wizard):
        super().__init__(wizard, "pagina_stile")
        self.check = QCheckBox(self.t("applica_stile_checkbox"))
        self.check.setChecked(True)
        self.bottone = QPushButton(self.t("applica_stile"))
        self.bottone.clicked.connect(self.applica_ora)
        self.esito = QLabel("")
        self.esito.setWordWrap(True)

        disposizione = QVBoxLayout(self)
        testo = QLabel(self.t("testo_stile"))
        testo.setWordWrap(True)
        disposizione.addWidget(testo)
        disposizione.addWidget(self.check)
        riga = QHBoxLayout()
        riga.addWidget(self.bottone)
        riga.addStretch(1)
        disposizione.addLayout(riga)
        disposizione.addWidget(self.esito)
        nota = QLabel(self.t("stile_salta"))
        nota.setWordWrap(True)
        nota.setStyleSheet("color:#555")
        disposizione.addWidget(nota)
        disposizione.addStretch(1)

    def applica_ora(self):
        """Applica subito lo stile (l'applicazione automatica avviene alla chiusura)."""
        ok, messaggio = self.applica()
        if ok:
            self.esito.setText(self.t("stile_applicato", messaggio=messaggio))
            self.esito.setStyleSheet("color:#060")
        else:
            self.esito.setText(self.t("stile_errore", errore=messaggio))
            self.esito.setStyleSheet("color:#a00")

    def applica(self):
        """Applica il QML di default alla tabella allegati. Ritorna ``(ok, messaggio)``."""
        layer_allegati = getattr(self.w.esito, "layer_allegati", None) if self.w.esito else None
        if layer_allegati is None:
            return False, self.t("stile_saltato")
        if not styles.esiste_qml():
            return False, self.t("stile_qml_non_trovato", percorso=styles.percorso_qml_default())
        return styles.applica_stile_predefinito(layer_allegati)

    def stile_richiesto(self):
        return self.check.isChecked()


class WizardAllegati(QWizard):
    """Wizard completo: 7 pagine, stato condiviso e report finale."""

    def __init__(self, iface, parent=None):
        super().__init__(parent)
        self.iface = iface
        self.progetto = QgsProject.instance()
        self.lingua = strings.lingua_corrente()

        # --- stato condiviso fra le pagine
        self.layer_sorgente = None
        self.esito = None
        self.cartella_base = ""
        self.righe_discovery = []
        self.campi_scelti = []
        self.modalita = naming.MODALITA_PREDEFINITA
        self.formula = ""
        self.elenco_csv = None
        self.colonna_chiave_csv = "GlobalID"
        self.rinomina_se_esistente = False
        self.candidati = []
        self.chiavi_esistenti = set()
        self.statistica = None
        self.report = None
        self.eseguito = False

        self.pagina_layer = PaginaLayer(self)
        self.pagina_verifica = PaginaVerifica(self)
        self.pagina_discovery = PaginaDiscovery(self)
        self.pagina_campi = PaginaCampi(self)
        self.pagina_naming = PaginaNaming(self)
        self.pagina_esegui = PaginaEsegui(self)
        self.pagina_stile = PaginaStile(self)
        for pagina in (self.pagina_layer, self.pagina_verifica, self.pagina_discovery,
                       self.pagina_campi, self.pagina_naming, self.pagina_esegui,
                       self.pagina_stile):
            self.addPage(pagina)

        self.setWindowTitle(self.t("titolo_wizard"))
        self.setWizardStyle(QWizard.ModernStyle)
        self.setOption(QWizard.NoBackButtonOnStartPage, True)
        self.setButtonText(QWizard.NextButton, self.t("avanti"))
        self.setButtonText(QWizard.BackButton, self.t("indietro"))
        self.setButtonText(QWizard.CancelButton, self.t("annulla"))
        self.setButtonText(QWizard.FinishButton, self.t("fine"))
        self.resize(1000, 720)

    # -------------------------------------------------- utilità

    def t(self, chiave, **valori):
        return strings.tr(chiave, self.lingua, **valori)

    def layer_filegdb(self):
        """Solo i layer vettoriali già in progetto che stanno su un FileGDB (ticket 03).

        La tabella allegati ``<layer>__ATTACH`` **non** è un layer sorgente: se la
        si scegliesse, il wizard cercherebbe ``<layer>__ATTACH__ATTACH`` e
        bloccherebbe con un messaggio incomprensibile. Si esclude qui, una volta
        sola, con lo stesso suffisso che usa il core.
        """
        trovati = []
        for layer in self.progetto.mapLayers().values():
            if not _e_vettoriale(layer):
                continue
            if _e_tabella_allegati(_nome(layer)):
                continue
            if attach.sembra_filegdb(layer.source()):
                trovati.append(layer)
        return trovati

    # -------------------------------------------------- chiusura

    def accept(self):
        """Chiude il wizard applicando lo stile se richiesto (ticket 03: stile alla fine)."""
        if self.report is not None and self.report.annullata:
            QMessageBox.information(self, self.t("attenzione_titolo"), self.t("esecuzione_annullata"))
        if self.pagina_stile.stile_richiesto():
            ok, messaggio = self.pagina_stile.applica()
            if not ok:
                QMessageBox.warning(self, self.t("attenzione_titolo"),
                                    self.t("stile_errore", errore=messaggio))
        super().accept()

    def reject(self):
        """Annulla = esci senza aver scritto nulla (ticket 03)."""
        if not self.eseguito and self.candidati:
            QMessageBox.information(self, self.t("attenzione_titolo"), self.t("annulla_zero_scritto"))
        super().reject()


# ---------------------------------------------------------------- helper


def _nome(layer) -> str:
    """Nome del layer, senza far esplodere il wizard se il layer è strano."""
    try:
        return str(layer.name())
    except Exception:
        return ""


def _e_tabella_allegati(nome: str) -> bool:
    """Vero se il nome del layer è quello di una tabella allegati (``...__ATTACH``).

    Il confronto è case-insensitive: il suffisso lo dichiara il core
    (``attach.SUFFISSO_TABELLA_ALLEGATI``), la maiuscola la decide ArcGIS.
    """
    suffisso = str(attach.SUFFISSO_TABELLA_ALLEGATI or "").upper()
    return bool(suffisso) and str(nome or "").upper().endswith(suffisso)


def _e_vettoriale(layer) -> bool:
    """Vero se il layer è vettoriale (compatibile fra le varianti di enum di QGIS)."""
    try:
        return layer.type() == layer.VectorLayer
    except Exception:
        try:
            from qgis.core import QgsMapLayerType

            return layer.type() == QgsMapLayerType.VectorLayer
        except Exception:
            return False


def _trova_preferito(valori, preferiti) -> str:
    """Primo valore presente in ``valori`` fra i nomi preferiti (case-insensitive)."""
    lut = {str(v).strip().lower(): v for v in valori}
    for preferito in preferiti:
        trovato = lut.get(str(preferito).lower())
        if trovato:
            return trovato
    return ""
