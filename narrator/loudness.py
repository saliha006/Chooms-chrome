"""Every line at the same loudness: the calm voice came out of ElevenLabs about 12.6 dB quieter than the cowboy
(median RMS -26.4 vs -13.8 dBFS over the cached clips, 2026-11-15), so Pix's own voice was the hard one to hear.

    python -m narrator.loudness            # re-level every cached clip in narrator/clips (idempotent)
"""

import io
import sys
import wave
from pathlib import Path

import numpy as np

TARGET_DBFS = -12.0  # speech loudness (RMS) for every line; was -18, Harry 2026-11-15: "much louder" for a noisy hall
CEILING = 10 ** (-1.0 / 20)  # peaks above -1 dBFS are rounded off rather than clipped


def level(samples: np.ndarray) -> np.ndarray:
    """Float samples in [-1, 1] brought to TARGET_DBFS, with a soft ceiling so a boosted peak never distorts."""
    rms = float(np.sqrt(np.mean(samples ** 2))) if samples.size else 0.0
    if rms < 1e-6:
        return samples  # silence stays silence
    out = samples * (10 ** (TARGET_DBFS / 20) / rms)
    loud = np.abs(out) > CEILING
    # above the ceiling, compress smoothly towards full scale instead of cutting the wave flat
    out[loud] = np.sign(out[loud]) * (CEILING + (1 - CEILING) * np.tanh((np.abs(out[loud]) - CEILING) / (1 - CEILING)))
    return out


def level_wav(data: bytes) -> bytes:
    """A 16-bit PCM WAV (as ElevenLabs returns it) re-levelled; anything else is returned unchanged, so an odd
    response plays as it came rather than silencing the live voice."""
    try:
        with wave.open(io.BytesIO(data)) as w:
            params = w.getparams()
            frames = w.readframes(w.getnframes())
    except (wave.Error, EOFError):
        return data
    if params.sampwidth != 2:
        return data
    samples = np.frombuffer(frames, np.int16).astype(np.float32) / 32768
    leveled = (np.clip(level(samples), -1, 32767 / 32768) * 32768).astype(np.int16)
    out = io.BytesIO()
    with wave.open(out, "wb") as w:
        w.setparams(params)
        w.writeframes(leveled.tobytes())
    return out.getvalue()


def main() -> None:
    clips = sorted((Path(__file__).parent / "clips").glob("*/*.wav"))
    for clip in clips:
        clip.write_bytes(level_wav(clip.read_bytes()))
    print(f"re-levelled {len(clips)} clips to {TARGET_DBFS} dBFS")


if __name__ == "__main__":
    sys.exit(main())
