import pytest

import run


@pytest.fixture(autouse=True)
def no_settle(monkeypatch):
    # The settle is a real-arm wait; tests still get a fresh frame, just without the 0.3 s sleep.
    monkeypatch.setattr(run, "SETTLE_S", 0.0)
