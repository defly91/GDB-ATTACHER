# conftest.py — i test del pacchetto `gdb_attacher/` sono tutti di livello "unit".
#
# Servono i marker: senza, `pytest -m unit` (il comando documentato in
# docs/test-strategy.md e usato in CI) **salta** questi file, cioè proprio quelli che
# coprono il codice di produzione. Il marker si applica qui, in un punto solo, invece di
# ripetere `pytestmark` in sei file.

import pytest


def pytest_collection_modifyitems(items):
    for item in items:
        item.add_marker(pytest.mark.unit)
