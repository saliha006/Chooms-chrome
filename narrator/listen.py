"""Hear the operator: "Hey Pix, I'm putting a cowboy hat on you", "Hey Pix, what do you see now?" (Harry, 2026-11-14).

The robot is called Pix and acts only on sentences that name it (Harry: "hey pix for everything"), so the crowd
and the team talking nearby never trigger it.

The microphone is read continuously (`arecord`, raw 16 kHz mono), but only stretches loud enough to be speech
are sent to ElevenLabs speech-to-text, one at a time; anything said while one is being transcribed is dropped.
A short phrase check, not a language model, decides what was meant: on stage it has to be predictable.
Everything runs on its own thread; the arm never waits for it. The microphone is `arecord` on Linux (the Intel laptop)
and `sounddevice` elsewhere (Windows dev laptops), both raw 16 kHz mono. No key: off, H still works.
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
WAKE_S = 8.0  # after a bare "Hey Pix", the next sentence counts as said to Pix even without the name
GREETING = {"hey", "hi", "hello", "ok", "okay"}

# Speech-to-text sometimes writes the name as a sound-alike; "Pix" is also passed to it as a key term.
NAMES = {"pix", "picks", "pics", "pixs", "pyx", "pixie"}
HAT_OFF = {"off", "take", "taking", "took", "remove", "removing", "stop", "longer", "anymore", "normal"}
HAT_ON = {"on", "put", "putting", "give", "giving", "wear", "wearing", "here's"}
# First match wins; each entry is (meaning, word stems that must all appear: "see" also hears "seeing", "sort" "sorted").
QUESTIONS = (
    ("see", {"see"}), ("see", {"looking", "at"}), ("see", {"look", "at"}),
    ("tally", {"how", "many"}), ("tally", {"sort"}), ("tally", {"score"}),
    ("why", {"why"}),
    ("doing", {"doing"}),
    ("who", {"who"}), ("who", {"your", "name"}),
)


def intent(text: str | None) -> str | None:
    """None unless Pix is named; then 'hat_on', 'hat_off', a question ('see', 'tally', 'why', 'doing', 'who') or
    'unknown'. For the hat, "off" wins, so "take the hat off" never reads as "on"."""
    words = set(re.findall(r"[a-z']+", (text or "").lower()))
    if not words & NAMES:
        return None
    if "hat" in words or "cowboy" in words:  # "turning you into a cowboy" means the hat too (heard 02:50)
        if words & HAT_OFF:
            return "hat_off"
        if words & HAT_ON or "cowboy" in words:
            return "hat_on"
    for meaning, needed in QUESTIONS:
        if all(any(w.startswith(stem) for w in words) for stem in needed):
            return meaning
    return "unknown"


def only_the_name(text: str | None) -> bool:
    """"Hey, Pix" and nothing else: the question follows after a pause, as a sentence of its own."""
    words = set(re.findall(r"[a-z']+", (text or "").lower()))
    return bool(words & NAMES) and words <= NAMES | GREETING


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
                 threshold: float = THRESHOLD, echo: Callable[[str], bool] = lambda heard: False):
        self._stream, self._transcribe, self._act, self._threshold = stream, transcribe, act, threshold
        self._echo = echo  # True for Pix's own voice coming back through the microphone
        self._busy = threading.Lock()
        self._awake_until = 0.0
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
            if self._echo(text):
                _log.info("ignored %r: Pix's own voice", text)
                return
            now = time.monotonic()
            if only_the_name(text):
                self._awake_until = now + WAKE_S
            meant = intent(text)
            if meant is None and now < self._awake_until:
                self._awake_until = 0.0
                meant = intent(f"pix {text}")
            _log.info("heard %r -> %s (%.0f ms)", text, meant, (time.monotonic() - started) * 1000)
            self.heard.append(text)
            if meant:
                self._act(meant)


def elevenlabs_transcriber(api_key: str, model: str, timeout_s: float = 8.0) -> Callable[[bytes], str]:
    from elevenlabs.client import ElevenLabs

    client = ElevenLabs(api_key=api_key)

    def transcribe(wav: bytes) -> str:
        return client.speech_to_text.convert(
            model_id=model, file=("speech.wav", wav, "audio/wav"), language_code="en", keyterms=["Pix", "cowboy hat"],
            request_options={"timeout_in_seconds": timeout_s, "max_retries": 0},
        ).text

    return transcribe


class SoundDeviceMic:
    """The same raw 16 kHz mono stream as arecord's, through PortAudio: lets a Windows laptop rehearse "Hey Pix"."""

    def __init__(self, device: str | int | None = None):
        import sounddevice

        self._stream = sounddevice.RawInputStream(samplerate=RATE, channels=1, dtype="int16", device=device,
                                                  blocksize=int(RATE * FRAME_S))
        self._stream.start()

    def read(self, n: int) -> bytes:
        data, _overflowed = self._stream.read(n // 2)  # frames of 2 bytes; an overflow only loses a few ms
        return bytes(data)


def microphone(device: str = "default"):
    """arecord's raw stream on Linux, PortAudio's elsewhere, or None when neither can open a microphone."""
    if shutil.which("arecord") is not None:
        process = subprocess.Popen(["arecord", "-q", "-D", device, "-f", "S16_LE", "-r", str(RATE), "-c", "1", "-t", "raw"],
                                   stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        return process.stdout
    try:
        return SoundDeviceMic(None if device == "default" else device)
    except Exception as exc:  # no sounddevice installed, or no input device: the H key still works
        _log.info("no microphone (%s)", type(exc).__name__)
        return None


def main() -> None:
    """Microphone check, out loud: a live loudness bar, what was heard, what Pix took it to mean, and Pix's spoken
    reply (as before a run starts: no brick yet). Ctrl+C to stop.

        python -m narrator.listen               # speak normally from where you'll stand; tune listen.threshold
    """
    import os

    import yaml
    from dotenv import load_dotenv

    load_dotenv()
    voices = yaml.safe_load(open("config/voices.yaml"))
    listen = voices.get("listen", {})
    threshold = listen.get("threshold", THRESHOLD)
    mic = microphone(listen.get("device", "default"))
    if mic is None:
        raise SystemExit("no microphone could be opened")
    transcribe = elevenlabs_transcriber(os.environ["ELEVENLABS_API_KEY"], voices.get("stt_model", "scribe_v1"))
    import narrator
    from narrator import answers

    narrator.enable_live(voices)
    before_a_run = {"state": "IDLE", "sorted": 0, "tally": {}, "decided": None, "obstacles": 0, "signal": None}

    class Metered:  # prints a loudness bar every ~0.3 s so the threshold can be set by eye
        def __init__(self, stream):
            self.stream, self.n = stream, 0

        def read(self, size):
            chunk = self.stream.read(size)
            self.n += 1
            if chunk and self.n % 10 == 0:
                level = float(np.sqrt(np.mean(np.frombuffer(chunk, np.int16).astype(np.float32) ** 2)))
                bar = "#" * min(int(level / 100), 40)
                print(f"\rloudness {level:6.0f} {bar:40} threshold {threshold}", end="", flush=True)
            return chunk

    print('Say: "Hey Pix, what do you see now?"  (Ctrl+C to stop)')
    try:
        for utterance in utterances(Metered(mic), threshold):
            text = transcribe(utterance)
            if narrator.said_recently(text):
                print(f"\nignored {text!r} (Pix's own voice)")
                continue
            meant = intent(text)
            print(f"\nheard {text!r} -> {meant}")
            if meant:
                narrator.react(meant, lambda m: answers.answer(m, before_a_run))
    except KeyboardInterrupt:
        print()
    narrator.wait_idle(10)


if __name__ == "__main__":
    main()
