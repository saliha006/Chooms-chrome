import pytest

import narrator
import run
from narrator.player import Player


@pytest.fixture(autouse=True)
def no_settle(monkeypatch):
    # The settle is a real-arm wait; tests still get a fresh frame, just without the 0.3 s sleep.
    monkeypatch.setattr(run, "SETTLE_S", 0.0)


@pytest.fixture(autouse=True)
def silent(monkeypatch):
    # Mock runs say a line per step; tests check the words, not the speakers.
    monkeypatch.setattr(narrator, "_player", Player(None))
