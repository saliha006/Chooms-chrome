import io
import wave

import numpy as np

from narrator.loudness import CEILING, TARGET_DBFS, level, level_wav


def wav(samples: np.ndarray, rate: int = 22050) -> bytes:
    out = io.BytesIO()
    with wave.open(out, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes((samples * 32767).astype(np.int16).tobytes())
    return out.getvalue()


def rms_dbfs(data: bytes) -> float:
    with wave.open(io.BytesIO(data)) as w:
        s = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float32) / 32768
    return 20 * np.log10(np.sqrt(np.mean(s ** 2)))


def speech_like(amplitude: float) -> np.ndarray:
    t = np.arange(22050) / 22050
    return amplitude * np.sin(2 * np.pi * 220 * t) * (0.5 + 0.5 * np.sin(2 * np.pi * 3 * t))


def test_a_quiet_and_a_loud_voice_come_out_equally_loud():
    quiet, loud = level_wav(wav(speech_like(0.05))), level_wav(wav(speech_like(0.6)))
    assert abs(rms_dbfs(quiet) - TARGET_DBFS) < 1.0 and abs(rms_dbfs(loud) - TARGET_DBFS) < 1.0


def test_boosted_peaks_are_rounded_off_not_clipped_flat():
    out = level(np.array([0.001] * 1000 + [0.9], np.float32))  # one big peak in a quiet clip
    assert CEILING < np.abs(out).max() <= 1.0  # rounded towards full scale, never past it


def test_silence_and_the_wav_format_survive():
    silent = wav(np.zeros(1000))
    assert level_wav(silent) == silent or rms_dbfs(level_wav(silent)) == -np.inf
    with wave.open(io.BytesIO(level_wav(wav(speech_like(0.1))))) as w:
        assert (w.getnchannels(), w.getsampwidth(), w.getframerate()) == (1, 2, 22050)


def test_anything_that_is_not_a_wav_passes_through():
    assert level_wav(b"RIFF-not-really") == b"RIFF-not-really"
