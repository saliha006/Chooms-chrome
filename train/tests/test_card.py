import json

import pytest

pytest.importorskip("pyarrow")

from robot import io  # noqa: E402
from train.card import card, rejected_count  # noqa: E402
from train.tests.test_episode_audit import TASKS, clean, episode, write  # noqa: E402

LOG = """# Rejected episodes

| When | Dataset | Episode | Reason |
|---|---|---|---|
| 2026-11-14 18:02 | `nate/sortsense-place` | 3 | dropped brick |
| 2026-11-14 18:09 | `nate/sortsense-pick` | 7 | hand in frame |
| 2026-11-14 18:15 | `nate/sortsense-place` | 9 | wrong bowl |
"""


def placed(root, **kw):
    """Place episodes end released: just inside the open band, so the fixture's step to it is not a teleop jump."""
    return write(root, [episode(i, end_gripper=io.GRIPPER_OPEN - io.POSE_TOLERANCE_DEG, task=i % 2) for i in range(6)], **kw)


@pytest.fixture
def log(tmp_path):
    path = tmp_path / "rejected.md"
    path.write_text(LOG, encoding="utf-8")
    return path


def test_rejections_are_counted_per_dataset(log):
    assert rejected_count("sortsense-place", log) == 2
    assert rejected_count("sortsense-pick", log) == 1


def test_a_clean_place_dataset_gets_a_card_with_its_own_facts(tmp_path, log):
    root = placed(tmp_path / "sortsense-place")
    text = card(root, "place", rejected_log=log)
    assert text.startswith("---\nlicense: apache-2.0")
    assert "| Episodes | 6 kept; 2 rejected on the spot and re-taken |" in text
    assert "| Frames | 30 Hz |" in text  # the fixture has no total_frames: no number is invented
    assert all(f"`{t}`" in text for t in TASKS) and "normalized to -100..100" in text and "`inspect`: webcam" in text
    assert "`python -m train.audit` passed" in text


def test_frames_come_from_the_metadata_when_present(tmp_path, log):
    root = clean(tmp_path / "sortsense-pick")
    info = json.loads((root / "meta" / "info.json").read_text())
    (root / "meta" / "info.json").write_text(json.dumps(info | {"total_frames": 1830}))
    assert "| Frames | 1830 at 30 Hz |" in card(root, "pick", rejected_log=log)


def test_a_dataset_that_fails_the_audit_gets_no_card(tmp_path, log):
    root = placed(tmp_path / "sortsense-place", cameras=("top", "wrist"))
    with pytest.raises(SystemExit, match="camera keys missing: inspect"):
        card(root, "place", rejected_log=log)
