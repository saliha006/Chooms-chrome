"""Live spoken reasoning with this brick's numbers (A6, decisions.md D12).

The cached clips can only say the verdict. A live line says why, with the real score and thresholds, through
ElevenLabs Flash on its own thread. It gets TIMEOUT_S to come back; if the network is slow, down or the key is
missing, the cached clip for the same event plays instead, so the voice never waits and the arm never does.
"""

import logging
import tempfile
import threading
import time
from collections.abc import Callable
from pathlib import Path

from narrator.naming import with_article

_log = logging.getLogger("narrator.live")

# Flash took 625-1563 ms per full line on the venue Wi-Fi (4 calls, 2026-11-14); 3 s keeps nearly every live line
# while the voice lags the arm by about a second at most (Harry, 2026-11-14). The arm never waits either way.
TIMEOUT_S = 3.0
# Credits: a 20-brick run costs about 5.5-11k characters (Nate's estimate, 17:55). Past the run budget the cached
# clips take over; below the account floor the run starts on cached lines only. Both TUNE.
RUN_BUDGET_CHARS = 12_000
ACCOUNT_FLOOR_CHARS = 10_000
LIVE_EVENTS = {"perfect", "defective", "uncertain", "empty", "quit", "drive", "arrived", "obstacle_named",
               "next", "roll", "regrasp"}

# Conversational on purpose: the robot thinks aloud. {where} is empty or " at the top left".
TEMPLATES = {
    "calm": {
        "perfect": "That scores {score}, under my {t_low} line. It looks clean, so the purple bowl.",
        "defective": "That scores {score}, over my {t_high} line, with a mark{where}. Orange bowl.",
        "uncertain": "Hmm, {score}. That's between my two lines, so I'm not sure yet. Let me take another look.",
    },
    "cowboy": {
        "perfect": "Scorin' {score}, well under my {t_low} line. Clean as a whistle, partner. Purple bowl.",
        "defective": "Whoa, {score}, past my {t_high} line, got a mark{where}. Orange bowl it is.",
        "uncertain": "{score}? That's smack between my lines. Hold your horses, lemme look again.",
    },
}
SUMMARY = {
    "calm": {"empty": "That's the last one. {tally}.", "quit": "Stopping here. {tally} so far."},
    "cowboy": {"empty": "That's the whole herd. {tally}.", "quit": "Callin' it a day. {tally} so far."},
}

# The base drive (demo): what it's doing and, once there, how far it went. Numbers come from the base driver.
DRIVE = {
    "calm": {"drive": "The bricks are about {cm} centimetres out of my reach, so I'm driving over to them.",
             "arrived": "Made it: {cm} centimetres in {seconds} seconds. I'm in position, let's start sorting."},
    "cowboy": {"drive": "Them bricks are {cm} centimetres yonder, partner. Movin' the whole outfit over.",
               "arrived": "Whoa there. {cm} centimetres in {seconds} seconds. In position, let's get sortin'."},
}

# An unfamiliar object, once the naming model says what it is (narrator/naming.py). Live only: no cached clip.
OBSTACLE = {
    "calm": "There's {thing} in my zone. That's not a brick, so I'll leave it alone.",
    "cowboy": "Holy smokes, there's {thing} in my zone! That ain't no brick, so I'm leavin' it be.",
}

# Between bricks and during recovery: only facts the audience can't see yet (the tally, the borderline score).
STEPS = {
    "calm": {"next": "That's {n} sorted so far: {perfect} perfect, {defective} defective. On to the next one.",
             "roll": "Still {score}, right between my lines. Rolling it ninety degrees for a better look.",
             "regrasp": "Still undecided at {score}. I'll set it down and pick it up fresh."},
    "cowboy": {"next": "{n} down, partner: {perfect} clean, {defective} busted. Next one.",
               "roll": "Still {score}, smack between my lines. Turnin' it ninety degrees for a better look.",
               "regrasp": "Still can't call it at {score}. Settin' it down to grab it fresh."},
}

# run.py's `after` values -> what a person would say
AFTER = {"looked again": "Second look: ", "reinspect 90": "After a wrist roll, ", "reinspect 0": "After a re-grasp, "}


def _number(value: float) -> str:
    # Two significant decimals read naturally ("zero point four one"); more is noise to a listener.
    return f"{value:.2f}"


def _where(cell: str | None) -> str:
    if not cell:
        return ""
    return " in the centre" if cell == "middle-centre" else f" at the {cell.replace('-', ' ')}"


def _bricks(n: int) -> str:
    return f"{n} brick" + ("" if n == 1 else "s")


def summary(persona: str, event: str, n: int = 0, perfect: int = 0, defective: int = 0, rechecked: int = 0) -> str | None:
    """The end-of-run line with this run's counts; None for an empty run (the cached line says it)."""
    if not n or event not in SUMMARY.get(persona, {}):
        return None
    tally = f"{_bricks(n)} sorted: {perfect} perfect, {defective} defective"
    if rechecked:
        tally += f", and {rechecked} needed a second look"
    return SUMMARY[persona][event].format(tally=tally)


def compose(persona: str, event: str, score: float | None = None, t_low: float | None = None,
            t_high: float | None = None, where: str | None = None, after: str | None = None, **counts) -> str | None:
    """The live line for a verdict, or None when the numbers it needs are missing (then the cached clip plays)."""
    if event == "next":
        return STEPS[persona][event].format(**{k: counts.get(k, 0) for k in ("n", "perfect", "defective")})             if counts.get("n") else None
    if event in ("roll", "regrasp"):
        return None if score is None else STEPS[persona][event].format(score=_number(score))
    if event == "obstacle_named":
        name = counts.get("name")
        return OBSTACLE[persona].format(thing=with_article(name)) if name else None
    if event in ("drive", "arrived"):
        cm, seconds = counts.get("cm"), counts.get("seconds")
        if cm is None or (event == "arrived" and seconds is None):
            return None  # the cached line covers it
        return DRIVE[persona][event].format(cm=round(cm), seconds=round(seconds or 0))
    if event in ("empty", "quit"):
        return summary(persona, event, **{k: v for k, v in counts.items() if k in ("n", "perfect", "defective", "rechecked")})
    template = TEMPLATES.get(persona, {}).get(event)
    if template is None or score is None or t_low is None or t_high is None:
        return None
    line = template.format(score=_number(score), t_low=_number(t_low), t_high=_number(t_high),
                           where=_where(where))
    if after in AFTER:
        line = AFTER[after] + line[0].lower() + line[1:]
    return line


class Live:
    """Each line is synthesised on its own thread as soon as it is asked for, a few at once, so a line never waits
    behind the one before it (at one line every ~3 s, a single queue made most of them late). Whatever comes back,
    WAV or fallback, goes to `submit` only if no newer line has gone out already: the robot never says things out
    of order."""

    def __init__(self, synth: Callable[[str, str], bytes], submit: Callable[[Path, bool], None],
                 timeout_s: float = TIMEOUT_S, budget_chars: int = RUN_BUDGET_CHARS, parallel: int = 3):
        self._synth, self._submit, self.timeout_s = synth, submit, timeout_s
        self.budget_chars, self.spent_chars = budget_chars, 0
        self._dir = Path(tempfile.mkdtemp(prefix="sortsense-live-"))
        self._lock = threading.Lock()
        self._slots = threading.Semaphore(parallel)  # ElevenLabs limits concurrent requests per plan
        self._asked = self._sent = self._pending = 0
        self._idle = threading.Event()
        self._idle.set()

    def warm_up(self) -> None:
        """Open the connection before the first brick, so its set-up cost isn't paid on a real verdict."""
        threading.Thread(target=self._warm, name="narrator-warm-up", daemon=True).start()

    def _warm(self) -> None:
        try:
            started = time.monotonic()
            self._synth("Ready.", "calm")
            _log.info("live voice ready (warm-up %.0f ms)", (time.monotonic() - started) * 1000)
        except Exception as exc:
            _log.info("live voice warm-up failed (%s); cached lines will cover", type(exc).__name__)

    def speak(self, text: str, persona: str, fallback: Path | None, priority: bool = False) -> None:
        with self._lock:
            self._asked += 1
            self._pending += 1
            self._idle.clear()
            seq = self._asked
        threading.Thread(target=self._say, args=(seq, text, persona, fallback, priority, time.monotonic()),
                         name="narrator-live", daemon=True).start()

    def wait_idle(self, timeout_s: float) -> bool:
        """End of a run: the last line (the summary) is still being synthesised; let it reach the player."""
        return self._idle.wait(timeout_s)

    def _say(self, seq: int, text: str, persona: str, fallback: Path | None, priority: bool, asked: float) -> None:
        try:
            self._send(seq, self._clip(seq, text, persona, fallback, asked), priority)
        finally:
            with self._lock:
                self._pending -= 1
                if not self._pending:
                    self._idle.set()

    def _clip(self, seq: int, text: str, persona: str, fallback: Path | None, asked: float) -> Path | None:
        """The live WAV, or the fallback (None if there is none) when over budget, failed or late."""
        cached = fallback if fallback is not None and fallback.exists() else None
        with self._lock:
            over = self.spent_chars + len(text) > self.budget_chars
            if over and self.spent_chars <= self.budget_chars:
                _log.warning("live voice budget of %d characters spent: cached lines from here", self.budget_chars)
                self.spent_chars = self.budget_chars + 1
            elif not over:
                self.spent_chars += len(text)
        if over:
            return cached
        try:
            with self._slots:
                audio = self._synth(text, persona)
            took = time.monotonic() - asked
            if took > self.timeout_s:
                raise TimeoutError(f"{took:.2f} s")
        except Exception as exc:  # network, quota or timeout: the cached clip says the same thing, minus the numbers
            _log.info("live line %s (%s)", "fell back to the cached clip" if cached else "dropped, no cached clip",
                      type(exc).__name__)
            return cached
        path = self._dir / f"line-{seq % 8}.wav"  # a small ring: the player is done with older files
        path.write_bytes(audio)
        _log.info("live line ready in %.0f ms", took * 1000)
        return path

    def _send(self, seq: int, clip: Path | None, priority: bool) -> None:
        with self._lock:
            if clip is None or seq < self._sent:
                return  # nothing to say, or a newer line already went out
            self._sent = seq
        self._submit(clip, priority)


def credits_left(api_key: str) -> int | None:
    """Characters left on the account, or None when the key may not read it (needs the user_read permission)."""
    from elevenlabs.client import ElevenLabs

    try:
        sub = ElevenLabs(api_key=api_key).user.subscription.get(request_options={"timeout_in_seconds": 5, "max_retries": 0})
        return sub.character_limit - sub.character_count
    except Exception as exc:
        _log.info("can't read the credit balance (%s); the run budget still applies", type(exc).__name__)
        return None


def elevenlabs_synth(voices: dict, api_key: str, timeout_s: float = TIMEOUT_S) -> Callable[[str, str], bytes]:
    from elevenlabs.client import ElevenLabs

    client = ElevenLabs(api_key=api_key)

    def synth(text: str, persona: str) -> bytes:
        return b"".join(client.text_to_speech.convert(
            voice_id=voices[persona], text=text, model_id=voices["live_model"], output_format=voices["cached_format"],
            request_options={"timeout_in_seconds": timeout_s, "max_retries": 0},
        ))

    return synth
