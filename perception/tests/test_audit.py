import os

import cv2
import numpy as np
import pytest

from perception.audit import MIN_PER_BRICK, audit


def textured(seed: int, level: int = 110) -> np.ndarray:
    rng = np.random.default_rng(seed)
    base = rng.integers(level - 30, level + 30, (64, 64, 3), dtype=np.uint8)
    return cv2.GaussianBlur(base, (3, 3), 0)


def write(folder, name, image, order):
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / name
    cv2.imwrite(str(path), image)
    os.utime(path, (order, order))  # capture order is the modification time


def make_clean(root, bricks=2, per_brick=MIN_PER_BRICK):
    n = 0
    for b in range(bricks):
        for i in range(per_brick):
            write(root / "good", f"b{b:02d}_{i:04d}.png", textured(n), n)
            n += 1
    write(root / "defective", "b90_0000.png", textured(999), n)


def test_a_clean_capture_passes(tmp_path):
    make_clean(tmp_path)
    report = audit(tmp_path)
    assert report.ok and not report.warnings and report.images == 2 * MIN_PER_BRICK + 1


def test_missing_folder_and_empty_data_fail(tmp_path):
    report = audit(tmp_path)
    assert not report.ok and any("good/: folder missing" in f for f in report.fails)


def test_a_frozen_frame_fails(tmp_path):
    make_clean(tmp_path)
    write(tmp_path / "good", "b00_0003.png", textured(2), 2.5)  # same pixels as the frame before it
    assert any("identical to the previous frame" in f for f in audit(tmp_path).fails)


def test_clipped_exposure_fails(tmp_path):
    make_clean(tmp_path)
    write(tmp_path / "good", "b00_0000.png", np.full((64, 64, 3), 255, np.uint8), 0)
    assert any("clipped" in f for f in audit(tmp_path).fails)


def test_mixed_sizes_fail(tmp_path):
    make_clean(tmp_path)
    write(tmp_path / "good", "b00_0001.png", textured(1)[:32], 1)
    assert any("mixed image sizes" in f for f in audit(tmp_path).fails)


def test_blur_and_thin_bricks_only_warn(tmp_path):
    make_clean(tmp_path)
    write(tmp_path / "good", "b00_0002.png", cv2.GaussianBlur(textured(2), (31, 31), 0), 2)
    write(tmp_path / "good", "b77_0000.png", textured(500), 100)  # a brick with one image
    report = audit(tmp_path)
    assert report.ok
    assert any("b00_0002.png: blurred" in w for w in report.warnings)
    assert any("good/b77: only 1 images" in w for w in report.warnings)


def test_lighting_drift_warns(tmp_path):
    n = 0
    for b in range(2):
        for i in range(MIN_PER_BRICK):
            write(tmp_path / "good", f"b{b:02d}_{i:04d}.png", textured(n, level=70 + n * 6), n)
            n += 1
    write(tmp_path / "defective", "b90_0000.png", textured(999), n)
    assert any("brightness drifted" in w for w in audit(tmp_path).warnings)


@pytest.mark.parametrize("name", ["good", "defective"])
def test_unreadable_file_fails(tmp_path, name):
    make_clean(tmp_path)
    (tmp_path / name / "broken.png").write_bytes(b"not a png")
    assert any("broken.png: unreadable" in f for f in audit(tmp_path).fails)


def test_untagged_images_get_one_warning_not_one_per_image(tmp_path):
    for i in range(10):
        write(tmp_path / "good", f"{i:04d}.png", textured(i), i)
    write(tmp_path / "defective", "0000.png", textured(999), 50)
    report = audit(tmp_path)
    assert report.ok and sum("brick id" in w for w in report.warnings) == 1 and not any("only" in w for w in report.warnings)
