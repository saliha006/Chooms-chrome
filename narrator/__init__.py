"""The robot's voice: say() and trigger() never block the control loop (PRD 7.3).

Until the ElevenLabs voice lands (A6) and the persona machine (A6b), lines go to the console.
"""

import logging

_log = logging.getLogger("narrator")
_persona = "calm"


def say(event: str, text: str | None = None, persona: str | None = None, **kw) -> None:
    details = " ".join(f"{k}={v}" for k, v in kw.items())
    _log.info("[%s] %s %s", persona or _persona, text or event, details)


def trigger(kind: str) -> None:
    _log.info("trigger: %s", kind)
