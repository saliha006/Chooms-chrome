"""CALM <-> COWBOY persona (PRD F18, A6b).

An obstacle or the hat flips the robot to the cowboy at once, with a cached exclamation. It drifts back to calm
through the half-way line once every trigger has cleared and one more brick is done. The hat has no "gone"
signal (the H key), so it counts as cleared the moment it is seen (Harry, 2026-11-14).

Called from the control thread (obstacles, bricks) and the window thread (H key), hence the lock.
"""

import threading
from collections.abc import Callable

EXCLAIM = {"obstacle": "obstacle", "hat": "yeehaw"}  # line keys in narrator/lines.py (cowboy)
ONE_SHOT = {"hat"}


class Persona:
    def __init__(self, say: Callable[..., None]):
        self._say = say
        self._lock = threading.Lock()
        self.current = "calm"
        self._active: set[str] = set()

    def trigger(self, kind: str) -> None:
        with self._lock:
            if kind not in ONE_SHOT:
                self._active.add(kind)
            flipped = self.current == "calm"
            self.current = "cowboy"
        if flipped:
            self._say(EXCLAIM[kind], persona="cowboy")

    def clear(self, kind: str) -> None:
        with self._lock:
            self._active.discard(kind)

    def brick_done(self) -> None:
        with self._lock:
            back = self.current == "cowboy" and not self._active
            if back:
                self.current = "calm"
        if back:
            self._say("halfway", persona="calm")
