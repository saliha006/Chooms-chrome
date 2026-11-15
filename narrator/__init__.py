"""The robot's voice: say() and trigger() never block the control loop (PRD 7.3).

Fixed lines come from narrator/lines.py and play from the cached clips in narrator/clips (A6); every line
also goes to the console. Once enable_live() has run, verdicts are spoken live with this brick's numbers, and a
`text` line (the reasoner's) is spoken too; both fall back to the cached clip (narrator/live.py).
The voice follows the persona (narrator/persona.py): trigger() flips to the cowboy, clear() and brick_done()
bring it back.
"""

import itertools
import logging
import os
import re
import time
from collections.abc import Callable

from narrator.cache import clip_path
from narrator.lines import key_for, line_for
from narrator.live import ACCOUNT_FLOOR_CHARS, LIVE_EVENTS, Live, compose, credits_left, elevenlabs_synth
from narrator.persona import EXCLAIM, Persona
from narrator.player import Player, system_player

_log = logging.getLogger("narrator")
PRIORITY = {"estop", "help", *EXCLAIM.values()}  # never dropped as stale
_player = Player(system_player())
_live: Live | None = None
# Trigger C (Saliha 21:35, Harry yes 23:30): every defective verdict in the calm voice gets one short cowboy
# exclamation first, rotating so it never repeats twice in a row; the explanation stays calm.
_defect_exclaims = itertools.cycle(("holy_smokes", "well_ill_be", "yeehaw"))  # short ones only: they lead into a verdict
_last: tuple[str, str, float] | None = None  # (line, persona, when) for the on-screen subtitle
_recent: list[tuple[float, set[str]]] = []  # (when, words) of what Pix said lately: the microphone hears it too
ECHO_S = 20.0
ECHO_SHARE = 0.7  # this share of a heard sentence's words in one of Pix's lines = Pix hearing itself
ECHO_MIN_WORDS = 5  # shorter sentences ("Hey Pix, why that bowl?") are never treated as an echo
SUBTITLE_S = 6.0


def say(event: str, text: str | None = None, persona: str | None = None, **kw) -> None:
    persona = persona or _persona.current
    reason = kw.get("reason")
    if event == "defective" and persona == "calm" and text is None:
        _exclaim()
    clip = clip_path(persona, key_for(event, reason))
    priority = event in PRIORITY
    spoken = text or (compose(persona, event, **kw) if _live is not None and event in LIVE_EVENTS else None)
    global _last
    shown = spoken or line_for(persona, event, reason) or event
    _last = (shown, persona, time.monotonic())
    _remember(shown)
    _log.info("[%s] %s", persona, shown)
    if spoken is not None and _live is not None:
        _live.speak(spoken, persona, fallback=None if text else clip, priority=priority)
    elif text is None and clip.exists():
        _player.submit(clip, priority=priority)


def _words(text: str) -> set[str]:
    return set(re.findall(r"[a-z']+", text.lower()))


def _remember(line: str) -> None:
    now = time.monotonic()
    _recent[:] = [(t, w) for t, w in _recent if now - t < ECHO_S] + [(now, _words(line))]


def said_recently(heard: str) -> bool:
    """True when the microphone picked up Pix's own voice rather than a person (so it never answers itself)."""
    words = _words(heard)
    if len(words) < ECHO_MIN_WORDS:
        return False
    now = time.monotonic()
    return any(now - t < ECHO_S and len(words & said) >= ECHO_SHARE * len(words) for t, said in _recent)


def interrupt() -> None:
    """Stop talking now: cut the clip playing, drop the queue and any live line still on its way."""
    _player.interrupt()
    if _live is not None:
        _live.cancel()


def _exclaim() -> None:
    key = next(_defect_exclaims)
    _log.info("[cowboy] %s", line_for("cowboy", key))
    _remember(line_for("cowboy", key))
    exclaim = clip_path("cowboy", key)
    if exclaim.exists():
        _player.submit(exclaim, priority=True)  # played before the calm explanation that follows it


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


def take_off_hat() -> None:
    _persona.take_off_hat()


def toggle_hat() -> None:
    """The H key: the backup for saying it out loud."""
    _persona.toggle_hat()


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
    left = credits_left(key)
    if left is not None and left < ACCOUNT_FLOOR_CHARS:
        _log.warning("only %d ElevenLabs credits left: cached lines only, keep them for the demo", left)
        return False
    _live = Live(elevenlabs_synth(voices, key), _player.submit)
    _live.warm_up()
    return True


def start_listening(voices: dict, answer: Callable[[str], str] | None = None):
    """Called once by run.py: "Hey Pix, …" by voice (narrator/listen.py). `answer(meaning)` returns what Pix says
    to a question; run.py builds it from the cell. None when listening can't run."""
    from dotenv import load_dotenv

    from narrator.listen import Listener, elevenlabs_transcriber, microphone

    load_dotenv()
    key = os.environ.get("ELEVENLABS_API_KEY")
    listen = voices.get("listen", {})
    mic = microphone(listen.get("device", "default"))
    if not key or mic is None:
        _log.info("not listening (%s): the H key toggles the hat", "no key" if not key else "no microphone")
        return None
    return Listener(mic, elevenlabs_transcriber(key, voices.get("stt_model", "scribe_v1")),
                    lambda meant: react(meant, answer), listen.get("threshold", 600), echo=said_recently)


def react(meant: str, answer: Callable[[str], str] | None) -> None:
    """What Pix does with something said to it: stop talking, then the hat or a spoken answer."""
    interrupt()
    if meant == "hat_on":
        trigger("hat")
    elif meant == "hat_off":
        take_off_hat()
    elif answer is not None:
        say("answer", text=answer(meant))


def wait_idle(timeout_s: float = 10.0) -> bool:
    """End of a run: let the last line finish before the program exits."""
    started = time.monotonic()
    if _live is not None:
        _live.wait_idle(timeout_s)
    return _player.wait_idle(max(timeout_s - (time.monotonic() - started), 0.0))
