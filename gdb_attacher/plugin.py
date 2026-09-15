# -*- coding: utf-8 -*-
"""plugin.py — ciclo di vita del plugin QGIS e voci di menu.

Il plugin non fa nulla da sé: aggiunge al menu una voce che apre il wizard e una
voce che cambia lingua (IT/EN, ticket 03). Tutta la logica sta in ``core/`` e
``wizard/``.
"""

from __future__ import annotations

import os

from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QAction, QActionGroup, QMessageBox

from .wizard import strings

ICONA_PLUGIN = os.path.join(os.path.dirname(__file__), "resources", "icone", "icona_plugin.svg")


class GDBAttacherPlugin:
    """Plugin QGIS «GDB-Attacher»."""

    def __init__(self, iface):
        self.iface = iface
        self.azioni = []
        self.gruppo_lingua = None
        self.menu = None

    # ------------------------------------------------------------ ciclo di vita

    def initGui(self):  # noqa: N802 — nome imposto dall'API QGIS
        """Crea menu, azioni e icona in barra degli strumenti."""
        icona = QIcon(ICONA_PLUGIN) if os.path.exists(ICONA_PLUGIN) else QIcon()

        self.azione_wizard = QAction(
            icona,
            strings.tr("azione_wizard"),
            self.iface.mainWindow(),
        )
        self.azione_wizard.setObjectName("gdb_attacher_azione_wizard")
        self.azione_wizard.setStatusTip(strings.tr("azione_wizard_desc"))
        self.azione_wizard.triggered.connect(self.apri_wizard)
        self.iface.addPluginToMenu(strings.tr("menu_root"), self.azione_wizard)
        self.iface.addToolBarIcon(self.azione_wizard)
        self.azioni.append(self.azione_wizard)

        self.menu_lingua = self._crea_menu_lingua()
        if self.menu_lingua is not None:
            self.iface.addPluginToMenu(strings.tr("menu_root"), self.menu_lingua.menuAction())

        self.azione_info = QAction(strings.tr("azione_info"), self.iface.mainWindow())
        self.azione_info.triggered.connect(self.mostra_info)
        self.iface.addPluginToMenu(strings.tr("menu_root"), self.azione_info)
        self.azioni.append(self.azione_info)

    def unload(self):
        """Rimuove menu, azioni e icona."""
        for azione in self.azioni:
            self.iface.removePluginMenu(strings.tr("menu_root"), azione)
            self.iface.removeToolBarIcon(azione)
        self.azioni = []
        if self.menu_lingua is not None:
            self.iface.removePluginMenu(strings.tr("menu_root"), self.menu_lingua.menuAction())
            self.menu_lingua.deleteLater()
            self.menu_lingua = None

    # ------------------------------------------------------------ menu lingua

    def _crea_menu_lingua(self):
        """Sottomenu con le due lingue disponibili (radio).

        La lingua viene salvata in QSettings e riletta all'apertura del wizard: niente
        retranslate a caldo, così la UI non può restare a metà fra due lingue.
        """
        from qgis.PyQt.QtWidgets import QMenu

        menu = QMenu(strings.tr("azione_lingua"), self.iface.mainWindow())
        self.gruppo_lingua = QActionGroup(menu)
        self.gruppo_lingua.setExclusive(True)
        etichette = {"it": "Italiano", "en": "English"}
        for codice in strings.lingue_disponibili():
            azione = QAction(etichette.get(codice, codice), menu)
            azione.setCheckable(True)
            azione.setChecked(strings.lingua_corrente() == codice)
            azione.setData(codice)
            azione.triggered.connect(lambda _spuntato, c=codice: self._cambia_lingua(c))
            self.gruppo_lingua.addAction(azione)
            menu.addAction(azione)
        return menu

    def _cambia_lingua(self, codice):
        strings.imposta_lingua(codice)
        QMessageBox.information(
            self.iface.mainWindow(),
            strings.tr("nome_plugin", codice),
            "Lingua impostata" if codice == "it" else "Language set to English",
        )

    # ------------------------------------------------------------ azioni

    def apri_wizard(self):
        """Apre il wizard. Import locale: senza QGIS il pacchetto resta importabile."""
        from .wizard.dialog import WizardAllegati

        wizard = WizardAllegati(self.iface, self.iface.mainWindow())
        wizard.exec_()

    def mostra_info(self):
        QMessageBox.information(
            self.iface.mainWindow(),
            strings.tr("info_titolo"),
            strings.tr("info_testo"),
        )
