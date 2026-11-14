import threading

import numpy as np
import pytest

from common.interfaces import DefectSignal
from reasoner.live import LiveLine, grounded

CROP = np.zeros((8, 8, 3), np.uint8)


def signal(label="perfect", score=0.12):
    return DefectSignal(0, "inspect", label, score, 0.20, 0.63, (10, 20, 30, 40), None, "padim", "CPU", 40.0)


def wait_for(cond, seconds=2.0):
    done = threading.Event()
    for _ in range(int(seconds * 100)):
        if cond():
            return True
        done.wait(0.01)
    return False


@pytest.mark.parametrize("line,label,ok", [
    ("score 0.12 is under 0.2, so into the purple bowl", "perfect", True),
    ("looks clean, purple bowl", "perfect", True),
    ("it goes in the orange bowl", "perfect", False),
    ("a mark at 10 20, orange bowl", "defective", True),
    ("purple bowl for this one", "defective", False),
    ("score 0.99 is high", "perfect", False),
    ("taking a second look", "uncertain", True),
    ("into the purple bowl", "uncertain", False),
])
def test_grounding(line, label, ok):
    assert grounded(line, signal(label, 0.12 if label == "perfect" else 0.7)) is ok


def test_a_good_line_is_spoken_once():
    spoken = []
    live = LiveLine(lambda *a, **k: spoken.append((a, k)), ask=lambda *a, **k: ("clean, purple bowl", 900.0))
    live.submit(CROP, signal())
    assert wait_for(lambda: spoken)
    assert spoken == [(("perfect",), {"text": "clean, purple bowl", "persona": "calm"})]
    assert live.stats["spoken"] == 1 and live.stats["latency_ms"] == [900.0]


def test_a_contradicting_line_is_dropped_and_counted():
    spoken = []
    live = LiveLine(lambda *a, **k: spoken.append(a), ask=lambda *a, **k: ("orange bowl", 500.0))
    live.submit(CROP, signal())
    assert wait_for(lambda: live.stats["rejected"] == 1) and not spoken


def test_an_error_never_reaches_the_caller():
    def boom(*a, **k):
        raise TimeoutError("slow")
    spoken = []
    live = LiveLine(lambda *a, **k: spoken.append(a), ask=boom)
    live.submit(CROP, signal())
    assert wait_for(lambda: live.stats["failed"] == 1) and not spoken


def test_a_line_that_arrives_after_the_next_brick_started_is_late():
    gate, spoken = threading.Event(), []
    started = threading.Event()

    def slow(*a, **k):
        started.set()
        gate.wait(2)
        return "clean, purple bowl", 100.0
    live = LiveLine(lambda *a, **k: spoken.append(a), ask=slow)
    live.submit(CROP, signal())
    assert started.wait(2)
    live.submit(CROP, signal())  # brick n+1 arrives while n is still being asked
    gate.set()
    assert wait_for(lambda: live.stats["late"] >= 1)
    assert wait_for(lambda: live.stats["spoken"] + live.stats["late"] >= 2)
    assert live.stats["spoken"] <= 1


def test_submit_returns_at_once_even_when_the_ask_hangs():
    live = LiveLine(lambda *a, **k: None, ask=lambda *a, **k: threading.Event().wait(0.3) or ("x", 1.0))
    import time
    t = time.perf_counter()
    live.submit(CROP, signal())
    assert time.perf_counter() - t < 0.05
