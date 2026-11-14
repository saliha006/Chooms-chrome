"""Hear the operator: "I'm putting a cowboy hat on you" / "I'm taking the hat off" (Harry, 2026-11-14 18:45).

The microphone is read continuously (`arecord`, raw 16 kHz mono), but only stretches loud enough to be speech
are sent to ElevenLabs speech-to-text, one at a time; anything said while one is being transcribed is dropped.
A short phrase check, not a language model, decides what was meant: on stage it has to be predictable.
Everything runs on its own thread; the arm never waits for it. No `arecord` (Windows) or no key: off, H still works.
"""

import io
import logging
import re
import shutil
import subprocess
import threading
import time
import wave
from collections.abc import Callable, Iterator

import numpy as np

_log = logging.getLogger("narrator.listen")

RATE = 16_000
FRAME_S = 0.03
THRESHOLD = 600  # TUNE at the station: RMS of 16-bit samples; above the room and the servos, below a voice
SILENCE_S = 0.8  # this long below the threshold ends an utterance
MIN_S = 0.4  # shorter is a clack, not a sentence
MAX_S = 6.0

HAT_OFF = {"off", "take", "taking", "took", "remove", "removing"}
HAT_ON = {"on", "put", "putting", "give", "giving", "wear", "wearing", "here's"}


def intent(text: str | None) -> str | None:
    """'hat_on', 'hat_off' or None. "Off" wins, so "take the hat off" never reads as "on"."""
    words = set(re.findall(r"[a-z']+", (text or "").lower()))
    if "hat" not in words:
        return None
    if words & HAT_OFF:
        return "hat_off"
    if words & HAT_ON:
        return "hat_on"
    return None


def wav_bytes(pcm: bytes, rate: int = RATE) -> bytes:
    out = io.BytesIO()
    with wave.open(out, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(pcm)
    return out.getvalue()


def utterances(stream, threshold: float = THRESHOLD, rate: int = RATE) -> Iterator[bytes]:
    """Cut a raw 16-bit mono stream into spoken utterances (WAV bytes); silence and clacks are skipped."""
    frame_bytes = int(rate * FRAME_S) * 2
    voiced, quiet = bytearray(), 0
    while chunk := stream.read(frame_bytes):
        loud = np.sqrt(np.mean(np.frombuffer(chunk, np.int16).astype(np.float32) ** 2)) > threshold
        if loud or voiced:
            voiced += chunk
            quiet = 0 if loud else quiet + 1
        seconds = len(voiced) / 2 / rate
        if voiced and (quiet * FRAME_S >= SILENCE_S or seconds >= MAX_S):
            if seconds - quiet * FRAME_S >= MIN_S:  # the speech itself, not the silence that ended it
                yield wav_bytes(bytes(voiced), rate)
            voiced, quiet = bytearray(), 0


class Listener:
    def __init__(self, stream, transcribe: Callable[[bytes], str], act: Callable[[str], None],
                 threshold: float = THRESHOLD):
        self._stream, self._transcribe, self._act, self._threshold = stream, transcribe, act, threshold
        self._busy = threading.Lock()
        self.heard: list[str] = []
        self.thread = threading.Thread(target=self._run, name="listener", daemon=True)
        self.thread.start()

    def _run(self) -> None:
        for utterance in utterances(self._stream, self._threshold):
            if self._busy.locked():
                continue  # still transcribing the last one: the moment for this one has passed
            threading.Thread(target=self._handle, args=(utterance,), daemon=True).start()

    def _handle(self, utterance: bytes) -> None:
        with self._busy:
            started = time.monotonic()
            try:
                text = self._transcribe(utterance)
            except Exception as exc:  # network or permission: the H key still works
                _log.info("could not transcribe (%s)", type(exc).__name__)
                return
            meant = intent(text)
            _log.info("heard %r -> %s (%.0f ms)", text, meant, (time.monotonic() - started) * 1000)
            self.heard.append(text)
            if meant:
                self._act(meant)


def elevenlabs_transcriber(api_key: str, model: str, timeout_s: float = 8.0) -> Callable[[bytes], str]:
    from elevenlabs.client import ElevenLabs

    client = ElevenLabs(api_key=api_key)

    def transcribe(wav: bytes) -> str:
        return client.speech_to_text.convert(
            model_id=model, file=("speech.wav", wav, "audio/wav"), language_code="en", keyterms=["cowboy hat"],
            request_options={"timeout_in_seconds": timeout_s, "max_retries": 0},
        ).text

    return transcribe


def microphone(device: str = "default"):
    """arecord's raw stream, or None where there is no arecord (Windows dev laptops)."""
    if shutil.which("arecord") is None:
        return None
    process = subprocess.Popen(["arecord", "-q", "-D", device, "-f", "S16_LE", "-r", str(RATE), "-c", "1", "-t", "raw"],
                               stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    return process.stdout
