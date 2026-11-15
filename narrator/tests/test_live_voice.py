import threading
import time

import pytest

import narrator
from narrator.live import TEMPLATES, Live, compose

NUMBERS = {"score": 0.4123, "t_low": 0.2, "t_high": 0.63, "where": "top-left"}


def test_defective_line_says_the_score_the_threshold_and_where():
    line = compose("calm", "defective", **NUMBERS)
    assert "0.41" in line and "0.63" in line and "top left" in line and "Orange bowl" in line


def test_perfect_line_compares_with_t_low():
    line = compose("cowboy", "perfect", score=0.11, t_low=0.2, t_high=0.63, where=None)
    assert "0.11" in line and "0.20" in line and "Purple bowl" in line and " at the " not in line


def test_recovery_step_is_said_in_words():
    assert compose("calm", "perfect", score=0.1, t_low=0.2, t_high=0.6, after="reinspect 90").startswith("After a wrist roll, that")
    assert compose("calm", "perfect", score=0.1, t_low=0.2, t_high=0.6, after="looked again").startswith("Second look: ")


def test_no_numbers_means_no_live_line():
    assert compose("calm", "defective", score=None, t_low=0.2, t_high=0.6) is None
    assert compose("calm", "grasp_fail", **NUMBERS) is None


def test_every_persona_has_every_live_verdict():
    assert {tuple(sorted(lines)) for lines in TEMPLATES.values()} == {("defective", "perfect", "uncertain")}


class Spy:
    def __init__(self):
        self.played = []
        self.done = threading.Event()

    def __call__(self, path, priority=False):
        self.played.append((path, path.read_bytes() if path.exists() else None))
        self.done.set()


def test_a_live_line_is_played_from_the_synthesised_audio():
    spy = Spy()
    Live(lambda text, persona: b"RIFF-live", spy).speak("hello", "calm", fallback=None)
    assert spy.done.wait(2)
    assert spy.played[0][1] == b"RIFF-live"


def test_network_failure_plays_the_cached_clip(tmp_path):
    clip = tmp_path / "defective.wav"
    clip.write_bytes(b"RIFF-cached")
    spy = Spy()

    def down(text, persona):
        raise OSError("network down")

    Live(down, spy).speak("hello", "calm", fallback=clip)
    assert spy.done.wait(2)
    assert spy.played == [(clip, b"RIFF-cached")]


def test_a_late_line_is_dropped_for_the_cached_clip(tmp_path):
    clip = tmp_path / "perfect.wav"
    clip.write_bytes(b"RIFF-cached")
    spy = Spy()

    def slow(text, persona):
        time.sleep(0.2)
        return b"RIFF-late"

    Live(slow, spy, timeout_s=0.05).speak("hello", "calm", fallback=clip)
    assert spy.done.wait(2)
    assert spy.played == [(clip, b"RIFF-cached")]


def test_a_line_does_not_wait_behind_a_slow_one():
    """At real pace a line arrives every ~3 s; a single queue made each wait for the last one and time out."""
    spy, release = Spy(), threading.Event()

    def synth(text, persona):
        if text == "slow":
            release.wait(2)
        return text.encode()

    live = Live(synth, spy, timeout_s=1.0)
    live.speak("slow", "calm", fallback=None)
    time.sleep(0.05)
    live.speak("quick", "calm", fallback=None)
    assert spy.done.wait(1) and spy.played[0][1] == b"quick"
    release.set()
    assert live.wait_idle(3)
    assert [audio for _, audio in spy.played] == [b"quick"]  # "slow" finished after a newer line: dropped


@pytest.fixture
def fake_live(monkeypatch):
    calls = []

    class FakeLive:
        def speak(self, text, persona, fallback, priority=False):
            calls.append((text, persona, fallback.name if fallback else None))

    monkeypatch.setattr(narrator, "_live", FakeLive())
    return calls


def test_verdicts_go_live_with_the_cached_clip_as_fallback(fake_live):
    narrator.say("defective", **NUMBERS)
    text, persona, fallback = fake_live[0]
    assert "0.41" in text and fallback == "defective.wav"


def test_other_events_stay_cached(fake_live, monkeypatch):
    submitted = []
    monkeypatch.setattr(narrator._player, "submit", lambda clip, priority=False: submitted.append(clip.name))
    narrator.say("grasp_fail")
    assert fake_live == [] and submitted == ["grasp_fail.wav"]


def test_a_reasoner_line_is_spoken_live_without_a_fallback(fake_live):
    narrator.say("defective", text="The marker line runs along the top edge.")
    assert fake_live == [("The marker line runs along the top edge.", "calm", None)]


def test_warm_up_makes_one_call_and_plays_nothing():
    calls, spy = [], Spy()
    live = Live(lambda text, persona: calls.append(text) or b"RIFF", spy)
    live.warm_up()
    deadline = time.monotonic() + 2
    while not calls and time.monotonic() < deadline:
        time.sleep(0.01)
    assert calls == ["Ready."] and spy.played == []


def test_a_failed_warm_up_is_harmless():
    def down(text, persona):
        raise OSError("network down")

    Live(down, Spy()).warm_up()  # must not raise on this thread or the worker's


def test_a_centre_mark_is_said_naturally():
    assert "in the centre" in compose("calm", "defective", score=0.9, t_low=0.2, t_high=0.6, where="middle-centre")


def test_run_summary_says_the_counts():
    line = compose("calm", "empty", n=5, perfect=3, defective=2, rechecked=1)
    assert line == "That's the last one. 5 bricks sorted: 3 perfect, 2 defective, and 1 needed a second look."
    assert compose("cowboy", "quit", n=1, perfect=1, defective=0).startswith("Callin' it a day. 1 brick sorted")


def test_an_empty_run_keeps_the_cached_summary():
    assert compose("calm", "empty", n=0) is None


def test_the_last_line_said_becomes_the_subtitle(monkeypatch):
    monkeypatch.setattr(narrator, "_live", None)
    narrator.say("grasp_fail")
    assert narrator.subtitle() == ("Missed it. Let me try that again.", "calm")
    assert narrator.subtitle(max_age_s=-1) is None  # older than the window


def test_wait_idle_holds_until_the_last_line_reaches_the_player():
    spy = Spy()

    def slow(text, persona):
        time.sleep(0.2)
        return b"RIFF"

    live = Live(slow, spy, timeout_s=5)
    live.speak("summary", "calm", fallback=None)
    assert live.wait_idle(2)
    assert len(spy.played) == 1


def test_drive_lines_say_the_distance_and_time():
    assert compose("calm", "drive", cm=42.4) == "The bricks are about 42 centimetres out of my reach, so I'm driving over to them."
    assert compose("cowboy", "arrived", cm=41.0, seconds=6.2) == "Whoa there. 41 centimetres in 6 seconds. In position, let's get sortin'."
    assert compose("calm", "drive", cm=None) is None  # the cached line, without a number
    assert compose("calm", "arrived", cm=41.0) is None


def test_past_the_run_budget_the_cached_clip_plays(tmp_path):
    clip = tmp_path / "perfect.wav"
    clip.write_bytes(b"RIFF-cached")
    synthesised, spy = [], Spy()

    def synth(text, persona):
        synthesised.append(text)
        return b"RIFF-live"

    live = Live(synth, spy, budget_chars=12)
    live.speak("ten chars.", "calm", clip)  # 10 of 12
    assert live.wait_idle(2)
    live.speak("five!", "calm", clip)  # would make 15: over budget
    assert live.wait_idle(2)
    assert synthesised == ["ten chars."]
    assert spy.played[-1] == (clip, b"RIFF-cached")


def test_step_lines_carry_the_tally_and_the_borderline_score():
    assert compose("calm", "next", n=3, perfect=2, defective=1) == \
        "That's 3 sorted: 2 perfect, 1 defective. On to the next one."  # no scene check: no choice to explain
    assert compose("cowboy", "roll", score=0.271) == \
        "Still 0.27, smack between my lines. Turnin' it ninety degrees for a better look."
    assert compose("calm", "regrasp", score=0.26).startswith("Still undecided at 0.26.")
    assert compose("calm", "first") is None and compose("calm", "roll") is None  # the cached line covers it


def test_before_a_pick_pix_says_why_this_brick():
    assert compose("calm", "first", chose=True) == \
        "First brick. I'm going for the brick with the most room around it, so I won't knock the others."
    assert compose("cowboy", "next", n=2, perfect=1, defective=1, chose=True, obstacles=1) == (
        "2 down, partner: 1 clean, 1 busted. Pickin' the one with the most open range around it. "
        "And I'm steerin' clear of that critter that ain't a brick.")
    wordings = {compose("calm", "next", n=n, chose=True) for n in range(1, 4)}
    assert len(wordings) == 3  # three bricks in a row, three different wordings


def test_a_calm_defective_verdict_gets_a_rotating_cowboy_exclamation_first(fake_live, monkeypatch):
    submitted = []
    monkeypatch.setattr(narrator._player, "submit", lambda clip, priority=False: submitted.append((clip.parent.name, clip.stem, priority)))
    for _ in range(3):
        narrator.say("defective", **NUMBERS)
    # the rotation is shared by the whole program, so only the order-free part is fixed: three in a row, all different
    assert {s[:2] for s in submitted} == {("cowboy", "holy_smokes"), ("cowboy", "well_ill_be"), ("cowboy", "yeehaw")}
    assert all(priority for _, _, priority in submitted)
    assert len(fake_live) == 3  # each explanation still goes out, in the calm voice
    assert all(persona == "calm" for _, persona, _ in fake_live)


def test_no_extra_exclamation_when_already_the_cowboy_or_for_other_verdicts(fake_live, monkeypatch):
    submitted = []
    monkeypatch.setattr(narrator._player, "submit", lambda clip, priority=False: submitted.append(clip.stem))
    narrator.say("defective", persona="cowboy", **NUMBERS)
    narrator.say("perfect", **NUMBERS)
    assert submitted == []


def test_cancel_drops_lines_still_being_synthesised():
    spy, release = Spy(), threading.Event()

    def slow(text, persona):
        release.wait(2)
        return text.encode()

    live = Live(slow, spy, timeout_s=5)
    live.speak("old line", "calm", fallback=None)
    time.sleep(0.05)
    live.cancel()  # "Hey Pix" came in while "old line" was on its way
    release.set()
    assert live.wait_idle(3) and spy.played == []
    live.speak("answer", "calm", fallback=None)  # lines asked after the interrupt still play
    assert spy.done.wait(2) and spy.played[-1][1] == b"answer"
