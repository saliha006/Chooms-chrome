"""The live reasoning line: off the control thread, checked against the verdict, dropped if late (D4, D11, D25).

    line = LiveLine(narrator.say)
    line.submit(crop, signal)      # returns at once; the spoken template line already covered the brick

The worker keeps only the newest request, so a slow answer for brick n never speaks over brick n+1.
A line that names the wrong bowl, or quotes a number we did not give it, is thrown away and counted.
"""

import logging
import re
import threading
import time
from collections.abc import Callable

import numpy as np

from common.interfaces import DefectSignal
from reasoner.client import explain

_log = logging.getLogger("reasoner")
# "bowl" is part of the match because the bricks themselves can be orange or purple
WRONG_ACTION = {"perfect": ("orange bowl",), "defective": ("purple bowl",), "uncertain": ("purple bowl", "orange bowl")}
NUMBER = re.compile(r"\d+(?:\.\d+)?")


def grounded(line: str, signal: DefectSignal) -> bool:
    """True when the line does not contradict the verdict: wrong bowl colour, or a number we never supplied."""
    text = line.lower()
    if any(word in text for word in WRONG_ACTION[signal.label]):
        return False
    given = [signal.score, signal.t_low, signal.t_high, *(signal.bbox or ())]
    # the model may round a score to fewer decimals, never to a different value
    return all(any(abs(float(n) - g) <= 0.005 + 0.0051 * abs(g) * (g >= 10) for g in given) for n in NUMBER.findall(text))


class LiveLine:
    def __init__(self, speak: Callable[..., None], timeout_s: float = 4.0, ask=explain):
        self._speak, self._timeout_s, self._ask = speak, timeout_s, ask
        self._pending: tuple[np.ndarray, DefectSignal, str] | None = None
        self._wake = threading.Event()
        self.stats = {"spoken": 0, "late": 0, "rejected": 0, "failed": 0, "latency_ms": []}
        threading.Thread(target=self._work, daemon=True, name="reasoner").start()

    def submit(self, crop: np.ndarray, signal: DefectSignal, persona: str = "calm") -> None:
        self._pending = (crop, signal, persona)
        self._wake.set()

    def _work(self) -> None:
        while True:
            self._wake.wait()
            self._wake.clear()
            job, self._pending = self._pending, None
            if job is None:
                continue
            crop, signal, persona = job
            started = time.perf_counter()
            try:
                line, ms = self._ask(crop, signal, persona, timeout_s=self._timeout_s)
            except Exception as exc:  # network, rate limit, bad JSON: the template line already played
                self.stats["failed"] += 1
                _log.warning("no live line: %s", exc)
                continue
            self.stats["latency_ms"].append(ms)
            if self._pending is not None or time.perf_counter() - started > self._timeout_s:
                self.stats["late"] += 1
            elif not grounded(line, signal):
                self.stats["rejected"] += 1
                _log.warning("rejected a line that contradicts %s: %r", signal.label, line)
            else:
                self.stats["spoken"] += 1
                self._speak(signal.label, text=line, persona=persona)
