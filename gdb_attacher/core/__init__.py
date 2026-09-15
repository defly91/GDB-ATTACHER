# -*- coding: utf-8 -*-
"""core/ — logica del plugin, senza alcuna dipendenza dall'interfaccia.

Regola di casa: i moduli di pura logica (``naming``, ``discovery``, ``report``,
``attach``) si importano anche fuori da QGIS. Gli import di ``qgis.core`` stanno
dentro le funzioni che ne hanno davvero bisogno, oppure in ``try/except ImportError``
quando esiste un ripiego ragionevole. Così la logica si può testare con ``pytest``
su una macchina senza QGIS.
"""
