"""CALM <-> COWBOY persona (PRD F18, A6b).

An obstacle or the hat flips the robot to the cowboy at once, with a cached line. The hat stays on until someone
says it's off (or presses H again), and taking it off brings the calm voice straight back (Harry, 2026-11-14 18:45:
"on until further notice"). An obstacle drifts back to calm through the half-way line once it has gone and one more
brick is done.

Called from the control thread (obstacles, bricks), the window thread (H key) and the listener (voice), hence the lock.
"""

import threading
from collections.abc import Callable

EXCLAIM = {"obstacle": "obstacle", "hat": "hat_on"}  # line keys in narrator/lines.py (cowboy)


class Persona:
    def __init__(self, say: Callable[..., None]):
        self._say = say
        self._lock = threading.Lock()
        self.current = "calm"
        self._active: set[str] = set()

    @property
    def hat_on(self) -> bool:
        return "hat" in self._active

    def trigger(self, kind: str) -> None:
        with self._lock:
            first = kind not in self._active
            self._active.add(kind)
            flipped = self.current == "calm"
            self.current = "cowboy"
        if flipped or (kind == "hat" and first):  # a hat on an already-cowboy robot still gets its line
            self._say(EXCLAIM[kind], persona="cowboy")

    def clear(self, kind: str) -> None:
        with self._lock:
            self._active.discard(kind)

    def take_off_hat(self) -> None:
        """Straight back to calm, unless an obstacle is still keeping the cowboy around."""
        with self._lock:
            had_it = "hat" in self._active
            self._active.discard("hat")
            back = had_it and self.current == "cowboy" and not self._active
            if back:
                self.current = "calm"
        if back:
            self._say("hat_off", persona="calm")

    def toggle_hat(self) -> None:
        if self.hat_on:
            self.take_off_hat()
        else:
            self.trigger("hat")

    def brick_done(self) -> None:
        with self._lock:
            back = self.current == "cowboy" and not self._active
            if back:
                self.current = "calm"
        if back:
            self._say("halfway", persona="calm")
