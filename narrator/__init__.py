"""The robot's voice: say() and trigger() never block the control loop (PRD 7.3).

Fixed lines come from narrator/lines.py and play from the cached clips in narrator/clips (A6); every line
also goes to the console. A live line passed as `text` (the reasoner, later) is console-only for now.
The voice follows the persona (narrator/persona.py): trigger() flips to the cowboy, clear() and brick_done()
bring it back.
"""

import logging

from narrator.cache import clip_path
from narrator.lines import key_for, line_for
from narrator.persona import EXCLAIM, Persona
from narrator.player import Player, system_player

_log = logging.getLogger("narrator")
PRIORITY = {"estop", "help", *EXCLAIM.values()}  # never dropped as stale
_player = Player(system_player())


def say(event: str, text: str | None = None, persona: str | None = None, **kw) -> None:
    persona = persona or _persona.current
    reason = kw.get("reason")
    line = text or line_for(persona, event, reason) or event
    _log.info("[%s] %s", persona, line)
    if text is None:
        clip = clip_path(persona, key_for(event, reason))
        if clip.exists():
            _player.submit(clip, priority=event in PRIORITY)


_persona = Persona(say)


def trigger(kind: str) -> None:
    """kind "obstacle" | "hat" (PRD 7.3): the cowboy, at once."""
    _log.info("trigger: %s", kind)
    _persona.trigger(kind)


def clear(kind: str) -> None:
    """The trigger has gone (no obstacle any more); the cowboy stays until the next brick is done."""
    _persona.clear(kind)


def brick_done() -> None:
    _persona.brick_done()


def wait_idle(timeout_s: float = 10.0) -> bool:
    """End of a run: let the last line finish before the program exits."""
    return _player.wait_idle(timeout_s)
