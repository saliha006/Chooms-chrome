import numpy as np
import pytest

from pathlib import Path

from perception.capture import brick_id, parse_box, square_crop
from perception.synth import generate


def test_square_crop_centres_and_resizes():
    frame = np.zeros((480, 640, 3), np.uint8)
    frame[:, 80:560] = 255  # the centred 480x480 square
    out = square_crop(frame)
    assert out.shape == (256, 256, 3)
    assert out.min() == 255


def test_square_crop_uses_box():
    frame = np.zeros((480, 640, 3), np.uint8)
    frame[10:110, 20:120] = 200
    out = square_crop(frame, (20, 10, 100))
    assert (out == 200).all()


def test_square_crop_rejects_box_outside_frame():
    with pytest.raises(ValueError):
        square_crop(np.zeros((480, 640, 3), np.uint8), (600, 0, 100))


def test_parse_box():
    assert parse_box("1,2,3") == (1, 2, 3)
    assert parse_box(None) is None


def test_generate_writes_three_folders(tmp_path):
    generate(tmp_path, ["red", "blue"], n_good=4, n_defective=2, n_val_good=3)
    counts = {d: len(list((tmp_path / d).glob("*.png"))) for d in ("good", "defective", "val_good")}
    assert counts == {"good": 4, "defective": 2, "val_good": 3}


def test_generate_is_reproducible(tmp_path):
    generate(tmp_path / "a", ["red"], 2, 1, 1, seed=3)
    generate(tmp_path / "b", ["red"], 2, 1, 1, seed=3)
    assert (tmp_path / "a/defective/b00_0000.png").read_bytes() == (tmp_path / "b/defective/b00_0000.png").read_bytes()


def test_brick_id_from_filename():
    assert brick_id(Path("b07_0012.png")) == "b07"
    assert brick_id(Path("0012.png")) == "0012"


def test_synthetic_images_are_grouped_by_brick(tmp_path):
    generate(tmp_path, ["red"], n_good=8, n_defective=1, n_val_good=1)
    assert {brick_id(p) for p in (tmp_path / "good").glob("*.png")} == {"b00", "b01"}
