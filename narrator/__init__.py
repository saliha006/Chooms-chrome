"""The robot's voice: say() and trigger() never block the control loop (PRD 7.3).

Fixed lines come from narrator/lines.py and play from the cached clips in narrator/clips (A6); every line
also goes to the console. Once enable_live() has run, verdicts are spoken live with this brick's numbers, and a
`text` line (the reasoner's) is spoken too; both fall back to the cached clip (narrator/live.py).
The voice follows the persona (narrator/persona.py): trigger() flips to the cowboy, clear() and brick_done()
bring it back.
"""

import logging
import os
import time

from narrator.cache import clip_path
from narrator.lines import key_for, line_for
from narrator.live import LIVE_EVENTS, Live, compose, elevenlabs_synth
from narrator.persona import EXCLAIM, Persona
from narrator.player import Player, system_player

_log = logging.getLogger("narrator")
PRIORITY = {"estop", "help", *EXCLAIM.values()}  # never dropped as stale
_player = Player(system_player())
_live: Live | None = None
_last: tuple[str, str, float] | None = None  # (line, persona, when) for the on-screen subtitle
SUBTITLE_S = 6.0


def say(event: str, text: str | None = None, persona: str | None = None, **kw) -> None:
    persona = persona or _persona.current
    reason = kw.get("reason")
    clip = clip_path(persona, key_for(event, reason))
    priority = event in PRIORITY
    spoken = text or (compose(persona, event, **kw) if _live is not None and event in LIVE_EVENTS else None)
    global _last
    shown = spoken or line_for(persona, event, reason) or event
    _last = (shown, persona, time.monotonic())
    _log.info("[%s] %s", persona, shown)
    if spoken is not None and _live is not None:
        _live.speak(spoken, persona, fallback=None if text else clip, priority=priority)
    elif text is None and clip.exists():
        _player.submit(clip, priority=priority)


_persona = Persona(say)


def subtitle(max_age_s: float = SUBTITLE_S) -> tuple[str, str] | None:
    """The line said in the last few seconds and its persona, for mission control."""
    last = _last
    if last is None or time.monotonic() - last[2] > max_age_s:
        return None
    return last[0], last[1]


def current_persona() -> str:
    return _persona.current


def trigger(kind: str) -> None:
    """kind "obstacle" | "hat" (PRD 7.3): the cowboy, at once."""
    _log.info("trigger: %s", kind)
    _persona.trigger(kind)


def clear(kind: str) -> None:
    """The trigger has gone (no obstacle any more); the cowboy stays until the next brick is done."""
    _persona.clear(kind)


def brick_done() -> None:
    _persona.brick_done()


def enable_live(voices: dict) -> bool:
    """Called once by run.py (never by tests, so they stay offline). False without a key: cached clips only."""
    global _live
    from dotenv import load_dotenv

    load_dotenv()
    key = os.environ.get("ELEVENLABS_API_KEY")
    if not key:
        _log.info("ELEVENLABS_API_KEY not set: cached lines only")
        return False
    _live = Live(elevenlabs_synth(voices, key), _player.submit)
    _live.warm_up()
    return True


def wait_idle(timeout_s: float = 10.0) -> bool:
    """End of a run: let the last line finish before the program exits."""
    started = time.monotonic()
    if _live is not None:
        _live.wait_idle(timeout_s)
    return _player.wait_idle(max(timeout_s - (time.monotonic() - started), 0.0))
