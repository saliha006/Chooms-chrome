from pathlib import Path

import cv2
import numpy as np
import pytest
import yaml

from common.interfaces import Inspector, Mover
from common.mocks import MockCamera, MockInspector, MockMover

CONFIG = Path(__file__).resolve().parents[2] / "config"


def test_mocks_satisfy_the_contracts():
    assert isinstance(MockInspector(), Inspector)
    assert isinstance(MockMover(), Mover)


def test_camera_without_folder_gives_frames():
    frame = MockCamera(size=(48, 64)).read()
    assert frame.shape == (48, 64, 3)


def test_camera_cycles_folder_images(tmp_path):
    for i in range(2):
        cv2.imwrite(str(tmp_path / f"{i}.png"), np.full((8, 8, 3), i * 100, np.uint8))
    cam = MockCamera(tmp_path)
    firsts = [int(cam.read()[0, 0, 0]) for _ in range(3)]
    assert firsts == [0, 100, 0]


def test_camera_rejects_empty_folder(tmp_path):
    with pytest.raises(FileNotFoundError):
        MockCamera(tmp_path)


def test_inspector_scores_agree_with_labels():
    insp = MockInspector(labels=("perfect", "uncertain", "defective"))
    for _ in range(3):
        s = insp.inspect(None, "realsense", 1)
        if s.label == "perfect":
            assert s.score < s.t_low
        elif s.label == "defective":
            assert s.score > s.t_high
        else:
            assert s.t_low <= s.score <= s.t_high


def test_mover_fails_first_picks_then_succeeds():
    mover = MockMover(pick_failures=1)
    assert [mover.pick_and_present() for _ in range(2)] == [False, True]


def test_rules_cover_every_label():
    rules = yaml.safe_load((CONFIG / "rules.yaml").read_text())
    assert "purple" in rules["perfect"] and "orange" in rules["defective"]
    assert rules["uncertain"]["then"] == "defective"


def test_camera_roles_match_brief():
    cams = yaml.safe_load((CONFIG / "cameras.yaml").read_text())
    assert set(cams) == {"top", "inspect", "wrist"}
