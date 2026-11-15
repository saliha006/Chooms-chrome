"""Plays cached clips on its own thread so speech never blocks or lags the arm (A6, decisions.md D12).

Newest line wins: when lines pile up behind the one playing, the older waiting ones are dropped, because a
line about a brick the arm has already moved past is noise. E-stop and help lines are never dropped.
Playback uses what the OS already has: winsound on Windows, aplay on Linux (alsa-utils), afplay on macOS.
interrupt() cuts the line playing and drops the queue: Pix stops talking when someone says "Hey Pix".
"""

import logging
import shutil
import subprocess
import sys
import threading
import wave
from collections.abc import Callable
from pathlib import Path

_log = logging.getLogger("narrator")


def _seconds(path: Path) -> float:
    with wave.open(str(path)) as w:
        return w.getnframes() / w.getframerate()


def system_player() -> Callable[[Path, threading.Event], None] | None:
    """play(path, stop): returns when the clip ends or as soon as `stop` is set."""
    if sys.platform == "win32":
        import winsound

        def play(path: Path, stop: threading.Event) -> None:
            winsound.PlaySound(str(path), winsound.SND_FILENAME | winsound.SND_ASYNC)  # async, so it can be cut
            if stop.wait(_seconds(path) + 0.05):
                winsound.PlaySound(None, 0)

        return play
    for tool, args in (("aplay", ["-q"]), ("afplay", [])):
        if shutil.which(tool):
            def play(path: Path, stop: threading.Event, tool=tool, args=args) -> None:
                process = subprocess.Popen([tool, *args, str(path)])
                while process.poll() is None:
                    if stop.wait(0.05):
                        process.terminate()
                        break

            return play
    return None


class Player:
    def __init__(self, play: Callable[[Path, threading.Event], None] | None):
        self._play = play
        self._stop = threading.Event()  # set by interrupt(): cuts the clip playing now
        self._queue: list[tuple[Path, bool]] = []  # (clip, priority), oldest first
        self._changed = threading.Condition()
        self._busy = False
        self._thread: threading.Thread | None = None
        self._failed = False

    def submit(self, clip: Path, priority: bool = False) -> None:
        if self._play is None:
            return
        with self._changed:
            self._queue.append((clip, priority))
            if self._thread is None:
                self._thread = threading.Thread(target=self._run, name="narrator", daemon=True)
                self._thread.start()
            self._changed.notify_all()

    def interrupt(self) -> None:
        """Stop mid-sentence and forget what was waiting."""
        with self._changed:
            self._queue.clear()
            self._stop.set()

    def wait_idle(self, timeout_s: float) -> bool:
        """Let the last line finish (end of a run) without waiting forever."""
        with self._changed:
            return self._changed.wait_for(lambda: not self._queue and not self._busy, timeout_s)

    def _next(self) -> Path:
        """The newest priority line if one is waiting, else the newest line; everything older is dropped."""
        index = max((i for i, (_, priority) in enumerate(self._queue) if priority), default=len(self._queue) - 1)
        clip = self._queue[index][0]
        del self._queue[:index + 1]
        return clip

    def _run(self) -> None:
        while True:
            with self._changed:
                self._changed.wait_for(lambda: self._queue)
                clip = self._next()
                self._busy = True
                self._stop.clear()  # an interrupt only cuts what was playing when it came
            try:
                self._play(clip, self._stop)
            except Exception as exc:  # no speaker, busy device, bad file: the voice is never worth stopping for
                if not self._failed:
                    _log.warning("audio playback failed (%s); lines go to the console only", type(exc).__name__)
                self._failed = True
            finally:
                with self._changed:
                    self._busy = False
                    self._changed.notify_all()
