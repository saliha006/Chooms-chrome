"""Name an unfamiliar object live (Nate's 17:49 ask): "Holy smokes, there's a coffee mug in my zone!"

The cached "Holy smokes!" plays the moment something that isn't a brick shows up. In parallel, this worker
asks a naming model (Saliha's pick: Nemotron VL or a local model) what it is, off the control thread, and the
name becomes a live line. A late or missing answer says nothing extra; the arm never waits (it already never
picks an obstacle).
"""

import logging
import re
import threading
import time
from collections.abc import Callable

import numpy as np

_log = logging.getLogger("narrator.naming")
TIMEOUT_S = 3.0  # same budget as the live voice: past it, the moment has gone
MAX_WORDS = 4


def clean(name: str | None) -> str | None:
    """A short spoken noun phrase from whatever the model returned, or None if nothing usable is left."""
    if not name:
        return None
    words = re.sub(r"[^a-z' -]", " ", name.lower()).split()
    while words and words[0] in ("a", "an", "the", "it's", "its", "this", "is"):
        words = words[1:]
    return " ".join(words[:MAX_WORDS]) or None


def with_article(name: str) -> str:
    return ("an " if name[0] in "aeiou" else "a ") + name


def crop(frame: np.ndarray, box: tuple[int, int, int, int] | None, margin: float = 0.25) -> np.ndarray:
    """The object with some context around it; the whole frame when the scene check gave no pixel box."""
    if box is None:
        return frame
    x, y, w, h = box
    dx, dy = int(w * margin), int(h * margin)
    return frame[max(y - dy, 0):y + h + dy, max(x - dx, 0):x + w + dx]


class ObjectNamer:
    """Newest request only; speaks through `say("obstacle_named", name=...)` when an answer comes back in time."""

    def __init__(self, name_fn: Callable[[np.ndarray], str | None], say: Callable[..., None],
                 timeout_s: float = TIMEOUT_S):
        self._name_fn, self._say, self.timeout_s = name_fn, say, timeout_s
        self._pending: tuple[Callable[[], np.ndarray], tuple | None, float] | None = None
        self._wake = threading.Event()
        threading.Thread(target=self._work, name="object-namer", daemon=True).start()

    def submit(self, grab: Callable[[], np.ndarray], box: tuple | None = None) -> None:
        """`grab` returns the top frame; it runs on this worker, so the control thread never waits for a camera."""
        self._pending = (grab, box, time.monotonic())
        self._wake.set()

    def _work(self) -> None:
        while True:
            self._wake.wait()
            self._wake.clear()
            job, self._pending = self._pending, None
            if job is None:
                continue
            grab, box, asked = job
            try:
                name = clean(self._name_fn(crop(grab(), box)))
            except Exception as exc:  # network, model or camera: the cached "Holy smokes!" already played
                _log.info("no name for the object (%s)", type(exc).__name__)
                continue
            took = time.monotonic() - asked
            if name is None or took > self.timeout_s or self._pending is not None:
                _log.info("object name dropped (%s, %.1f s)", name, took)
                continue
            _log.info("named the object '%s' in %.0f ms", name, took * 1000)
            self._say("obstacle_named", name=name)
