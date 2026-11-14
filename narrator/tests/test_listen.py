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
