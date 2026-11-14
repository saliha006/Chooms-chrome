"""E-stop request (decisions.md D21): any thread may ask, only the control thread talks to the motors.

The E key calls request(); the control thread sees it at its next check and turns the torque off.
Today the checks are in ScriptedMover's step loop and between run.py stages; once robot.io.act()
checks it too (asked of @nate), learned-policy motion stops within one control step as well.
"""

import threading

_requested = threading.Event()


class EStopped(BaseException):
    """Raised on the control thread after torque-off. A BaseException so no `except Exception`
    on the way up treats it as an ordinary failure and tries to move the arm home."""


def request() -> None:
    _requested.set()


def requested() -> bool:
    return _requested.is_set()


def clear() -> None:
    _requested.clear()
