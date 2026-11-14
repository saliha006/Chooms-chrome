"""The robot's voice: say() and trigger() never block the control loop (PRD 7.3).

Lines come from narrator/lines.py (H3). Until playback lands (A6) and the persona machine (A6b),
they go to the console.
"""

import logging

from narrator.lines import line_for

_log = logging.getLogger("narrator")
_persona = "calm"


def say(event: str, text: str | None = None, persona: str | None = None, **kw) -> None:
    persona = persona or _persona
    line = text or line_for(persona, event, kw.get("reason")) or event
    _log.info("[%s] %s", persona, line)


def trigger(kind: str) -> None:
    _log.info("trigger: %s", kind)
