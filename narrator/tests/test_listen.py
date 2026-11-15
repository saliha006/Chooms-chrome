import io
import threading
import time
import wave

import numpy as np
import pytest

from narrator.listen import RATE, Listener, intent, utterances


@pytest.mark.parametrize("text, meant", [
    ("Hey Pix, I'm putting a cowboy hat on you.", "hat_on"),
    ("Hey picks, here's a cowboy hat for you", "hat_on"),  # a sound-alike of the name still counts
    ("Okay Pix, I'm taking the cowboy hat off now.", "hat_off"),
    ("Hey Pix, what do you see now?", "see"),
    ("Pix, what are you looking at?", "see"),
    ("Hey Pix, how many have you sorted?", "tally"),
    ("Hey Pix, why that bowl?", "why"),
    ("Pix, what are you doing?", "doing"),
    ("Hey Pix, who are you?", "who"),
    ("Hey, Pix, I'm turning you into a cowboy", "hat_on"),  # heard in the 02:50 microphone check
    ("Hey Pix, you're a cowboy now", "hat_on"),
    ("Hey Pix, stop being a cowboy", "hat_off"),
    ("Hey Pix, you're no longer a cowboy", "hat_off"),
    ("Hey Pix, sing me a song", "unknown"),
    ("I'm putting a cowboy hat on you.", None),  # not addressed to Pix: ignored
    ("What do you see now?", None),
    ("", None),
    (None, None),
])
def test_intent(text, meant):
    assert intent(text) == meant


def pcm(*parts):
    """(seconds, loud?) parts -> raw 16-bit mono at RATE: a 440 Hz tone for speech, near-silence otherwise."""
    out = []
    for seconds, loud in parts:
        t = np.arange(int(seconds * RATE)) / RATE
        out.append((np.sin(2 * np.pi * 440 * t) * (8000 if loud else 50)).astype(np.int16))
    return np.concatenate(out).tobytes()


def test_speech_between_silences_becomes_one_utterance():
    found = list(utterances(io.BytesIO(pcm((1, False), (1.5, True), (1.2, False)))))
    assert len(found) == 1
    with wave.open(io.BytesIO(found[0])) as w:
        assert w.getframerate() == RATE and 1.5 <= w.getnframes() / RATE <= 2.5


def test_a_clack_and_silence_are_ignored():
    assert list(utterances(io.BytesIO(pcm((1, False), (0.1, True), (1.5, False))))) == []


def test_two_sentences_are_two_utterances():
    assert len(list(utterances(io.BytesIO(pcm((1, True), (1, False), (1, True), (1, False)))))) == 2


def test_listener_acts_on_what_it_hears():
    acted, done = [], threading.Event()

    def act(meant):
        acted.append(meant)
        done.set()

    Listener(io.BytesIO(pcm((1, True), (1, False))), lambda wav: "Hey Pix, I'm putting a cowboy hat on you", act)
    assert done.wait(3)
    assert acted == ["hat_on"]


def test_a_failed_transcription_does_nothing():
    acted, tried = [], threading.Event()

    def broken(wav):
        tried.set()
        raise PermissionError("missing the permission speech_to_text")

    Listener(io.BytesIO(pcm((1, True), (1, False))), broken, acted.append)
    assert tried.wait(3)
    time.sleep(0.05)
    assert acted == []


def test_speech_while_still_transcribing_is_dropped():
    calls, release = [], threading.Event()

    def slow(wav):
        calls.append(1)
        release.wait(2)
        return "hat on"

    stream = io.BytesIO(pcm((1, True), (1, False), (1, True), (1, False)))
    listener = Listener(stream, slow, lambda meant: None)
    listener.thread.join(3)  # the whole stream is read while the first transcription is still running
    release.set()
    assert calls == [1]


def test_without_arecord_the_microphone_comes_from_sounddevice(monkeypatch):
    from narrator import listen

    opened = []

    class FakeMic:
        def __init__(self, device=None):
            opened.append(device)

    monkeypatch.setattr(listen.shutil, "which", lambda tool: None)
    monkeypatch.setattr(listen, "SoundDeviceMic", FakeMic)
    assert isinstance(listen.microphone("default"), FakeMic) and opened == [None]


def test_no_microphone_at_all_means_none(monkeypatch):
    from narrator import listen

    def broken(device=None):
        raise OSError("no input device")

    monkeypatch.setattr(listen.shutil, "which", lambda tool: None)
    monkeypatch.setattr(listen, "SoundDeviceMic", broken)
    assert listen.microphone("default") is None


def test_react_puts_on_the_hat_takes_it_off_and_answers(monkeypatch):
    import narrator

    done = []
    monkeypatch.setattr(narrator, "trigger", lambda kind: done.append(("trigger", kind)))
    monkeypatch.setattr(narrator, "take_off_hat", lambda: done.append(("off",)))
    monkeypatch.setattr(narrator, "say", lambda event, text=None, **kw: done.append((event, text)))
    monkeypatch.setattr(narrator, "interrupt", lambda: None)
    narrator.react("hat_on", None)
    narrator.react("hat_off", None)
    narrator.react("who", lambda meaning: f"answer to {meaning}")
    narrator.react("who", None)  # no answer function: nothing said
    assert done == [("trigger", "hat"), ("off",), ("answer", "answer to who")]


def test_pix_does_not_answer_its_own_voice(monkeypatch):
    import narrator

    monkeypatch.setattr(narrator, "_recent", [])
    narrator._remember("I'm Pix. I spot defects in bricks, sort them into the right bowl and tell you why.")
    assert narrator.said_recently("I'm Pix, I spot defects in bricks, sort them into the right bowl")
    assert not narrator.said_recently("Hey Pix, why that bowl?")  # short questions are never echoes
    assert not narrator.said_recently("Hey Pix, what did you just put in the orange bowl for?")


def test_the_listener_skips_an_echo(monkeypatch):
    acted, tried = [], threading.Event()

    def transcribe(wav):
        tried.set()
        return "Hey Pix, I'm putting a cowboy hat on you"

    Listener(io.BytesIO(pcm((1, True), (1, False))), transcribe, acted.append, echo=lambda heard: True)
    assert tried.wait(3)
    time.sleep(0.05)
    assert acted == []


def test_react_interrupts_before_it_answers(monkeypatch):
    import narrator

    order = []
    monkeypatch.setattr(narrator, "interrupt", lambda: order.append("interrupt"))
    monkeypatch.setattr(narrator, "say", lambda event, text=None, **kw: order.append(event))
    narrator.react("who", lambda meaning: "I'm Pix.")
    assert order == ["interrupt", "answer"]
