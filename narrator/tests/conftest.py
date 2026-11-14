import pytest

import narrator
from narrator.player import Player


@pytest.fixture(autouse=True)
def silent(monkeypatch):
    monkeypatch.setattr(narrator, "_player", Player(None))
