"""Per-stage deadline (decisions.md D22). The cell arms it around a motion stage; motion loops check it each
step and stop, so a stuck move ends as a TIMEOUT instead of hanging the cell.

ScriptedMover checks expired(); LearnedMover passes `abort` to run_episode as its abort_event (Nate, N2).
"""

import threading
from contextlib import contextmanager

abort = threading.Event()


def expired() -> bool:
    return abort.is_set()


@contextmanager
def armed(seconds: float | None):
    """Set `abort` after `seconds` (None: no deadline). Cleared on entry and exit, so it never leaks."""
    abort.clear()
    timer = threading.Timer(seconds, abort.set) if seconds is not None else None
    if timer is not None:
        timer.daemon = True
        timer.start()
    try:
        yield
    finally:
        if timer is not None:
            timer.cancel()
        abort.clear()
