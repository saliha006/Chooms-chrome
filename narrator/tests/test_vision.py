import numpy as np
import pytest

from narrator import vision
from narrator.vision import KNOWN, Sight, classify, preprocess, train_probe, zero_shot

NAMES = [*KNOWN, "mug", "hand"]


def text_for(names, dims=8):
    """One unit vector per name, all orthogonal: a clean stand-in for CLIP's text embeddings."""
    return np.eye(dims, dtype=np.float32)[: len(names)]


def test_preprocess_gives_clip_input_in_rgb_order():
    blue = np.zeros((480, 640, 3), np.uint8)
    blue[..., 0] = 255  # OpenCV frames are BGR: channel 0 is blue
    x = preprocess(blue)
    assert x.shape == (1, 3, 224, 224) and x.dtype == np.float32
    assert np.allclose(x[0, 2], (1.0 - vision.MEAN[2]) / vision.STD[2])  # blue lands in CLIP's third channel
    assert np.allclose(x[0, 0], (0.0 - vision.MEAN[0]) / vision.STD[0])  # and red is empty


def test_a_clear_regular_object_is_named():
    text = text_for(NAMES)
    assert zero_shot(text[0] * 3, NAMES, text) == Sight("brick", pytest.approx(1.0, abs=1e-3))


def test_anything_else_is_unknown_with_a_best_guess():
    text = text_for(NAMES)
    sight = zero_shot(text[NAMES.index("mug")], NAMES, text)
    assert sight.name == "unknown" and sight.guess == "mug"


def test_an_unsure_regular_object_counts_as_unknown():
    text = text_for(NAMES)
    between = text[0] + text[1]  # half brick, half plate: neither clearly wins
    assert zero_shot(between, NAMES, text).name == "unknown"


def test_the_trained_classifier_learns_our_objects():
    rng = np.random.default_rng(0)
    centres = {"brick": rng.normal(size=16), "plate": rng.normal(size=16), "unknown": rng.normal(size=16)}
    x = np.stack([c + 0.1 * rng.normal(size=16) for c in centres.values() for _ in range(15)])
    labels = [name for name in centres for _ in range(15)]
    probe = train_probe(x, labels)
    text = np.eye(16, dtype=np.float32)[: len(NAMES)]
    assert classify(centres["plate"], probe, NAMES, text).name == "plate"
    assert classify(centres["unknown"], probe, NAMES, text).name == "unknown"


@pytest.mark.skipif(not (vision.MODEL_DIR / "clip_image.xml").exists(), reason="python -m narrator.vision build first")
def test_the_built_model_recognises_a_frame():
    rec = vision.Recognizer(devices=("CPU",))
    frame = np.full((480, 640, 3), 255, np.uint8)
    frame[180:300, 260:380] = (0, 0, 220)  # a red block on white
    sight = rec.recognise(frame)
    assert sight.name in [*KNOWN, "unknown"] and 0.0 <= sight.confidence <= 1.0
    assert rec.embed(frame).shape == (512,)
