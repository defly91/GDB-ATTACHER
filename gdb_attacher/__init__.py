# -*- coding: utf-8 -*-
"""GDB-Attacher — pacchetto plugin QGIS.

Punto d'ingresso standard dei plugin QGIS: ``classFactory(iface)`` viene chiamata
da QGIS quando il plugin viene abilitato dal gestore dei plugin.

L'import del modulo ``plugin`` sta *dentro* la funzione: così il pacchetto resta
importabile anche fuori da QGIS (per esempio dagli unit test di logica pura).
"""


def classFactory(iface):  # noqa: N802 — nome imposto dall'API QGIS
    """Crea l'istanza del plugin.

    :param iface: ``QgisInterface`` di QGIS.
    """
    from .plugin import GDBAttacherPlugin

    return GDBAttacherPlugin(iface)
