"""The robot's voice: say() and trigger() never block the control loop (PRD 7.3).

Fixed lines come from narrator/lines.py and play from the cached clips in narrator/clips (A6); every line
also goes to the console. A live line passed as `text` (the reasoner, later) is console-only for now.
"""

import logging

from narrator.cache import clip_path
from narrator.lines import key_for, line_for
from narrator.player import Player, system_player

_log = logging.getLogger("narrator")
_persona = "calm"
PRIORITY = {"estop", "help"}  # never dropped as stale
_player = Player(system_player())


def say(event: str, text: str | None = None, persona: str | None = None, **kw) -> None:
    persona = persona or _persona
    reason = kw.get("reason")
    line = text or line_for(persona, event, reason) or event
    _log.info("[%s] %s", persona, line)
    if text is None:
        clip = clip_path(persona, key_for(event, reason))
        if clip.exists():
            _player.submit(clip, priority=event in PRIORITY)


def trigger(kind: str) -> None:
    _log.info("trigger: %s", kind)


def wait_idle(timeout_s: float = 10.0) -> bool:
    """End of a run: let the last line finish before the program exits."""
    return _player.wait_idle(timeout_s)
