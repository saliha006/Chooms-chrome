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


def test_a_newer_line_replaces_one_not_started_yet():
    spoken, gate = [], threading.Event()

    def synth(text, persona):
        gate.wait(2)
        spoken.append(text)
        return b"RIFF"

    spy = Spy()
    live = Live(synth, spy, timeout_s=5)
    live.speak("first", "calm", fallback=None)
    time.sleep(0.05)  # "first" is now being synthesised
    live.speak("stale", "calm", fallback=None)
    live.speak("newest", "calm", fallback=None)
    gate.set()
    deadline = time.monotonic() + 2
    while len(spoken) < 2 and time.monotonic() < deadline:
        time.sleep(0.01)
    assert spoken == ["first", "newest"]


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
