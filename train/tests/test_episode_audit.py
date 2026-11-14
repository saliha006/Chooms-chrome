import json

import numpy as np
import pandas as pd
import pytest

pytest.importorskip("pyarrow")

from robot import io  # noqa: E402
from train.audit import audit  # noqa: E402

FPS = 30
TASKS = ["the brick is perfect, place it in the purple bowl", "the brick is defective, place it in the orange bowl"]


def episode(index, seconds=10.0, end_gripper=30.0, task=0, pause=False, jump=False):
    """A steady sweep in normalized units (every arm joint inside -100..100), ending at a given gripper value."""
    n = int(seconds * FPS)
    t = np.linspace(0, 1, n)
    state = np.stack([120 * t - 60, 90 * np.sin(3 * t), 40 * t, 30 * t, 180 * t - 90, np.full(n, 40.0)], axis=1)
    state[:, :5] += np.random.default_rng(index).normal(0, 0.05, (n, 5))  # no two real episodes are identical
    if pause:  # stand still for 3 s, then carry on from the same pose
        state = np.concatenate([state[: n // 3], np.repeat(state[n // 3: n // 3 + 1], 3 * FPS, axis=0), state[n // 3:]])
    n = len(state)
    state[-FPS:, :5] = state[-FPS, :5]  # the closing hold
    state[-FPS:, io.GRIPPER] = end_gripper
    if jump:
        state[n // 2:, 0] += 40
    return pd.DataFrame({"observation.state": list(state), "action": list(state), "timestamp": np.arange(n) / FPS,
                         "frame_index": np.arange(n), "episode_index": index, "task_index": task})


def write(root, episodes, fps=FPS, cameras=("top", "inspect", "wrist"), quantiles=True, tasks=TASKS):
    (root / "meta").mkdir(parents=True)
    (root / "data" / "chunk-000").mkdir(parents=True)
    features = {"observation.state": {}, "action": {}} | {f"observation.images.{c}": {} for c in cameras}
    (root / "meta" / "info.json").write_text(json.dumps({"fps": fps, "features": features}))
    stat = {"q01": [0], "q99": [1]} if quantiles else {}
    (root / "meta" / "stats.json").write_text(json.dumps({"observation.state": stat, "action": stat}))
    pd.DataFrame({"task_index": range(len(tasks))}, index=pd.Index(tasks)).to_parquet(root / "meta" / "tasks.parquet")
    pd.concat(episodes, ignore_index=True).to_parquet(root / "data" / "chunk-000" / "file-000.parquet")
    return root


def clean(root, n=6, **kw):
    return write(root, [episode(i, seconds=10 + (i % 3) * 0.5, task=i % 2) for i in range(n)], **kw)


def test_a_clean_pick_dataset_passes(tmp_path):
    report = audit(clean(tmp_path), "pick", ["top", "inspect", "wrist"], TASKS)
    assert report.ok and not report.warnings and report.episodes == 6


def test_missing_camera_wrong_fps_and_wrong_strings_fail(tmp_path):
    root = clean(tmp_path, cameras=("top", "wrist"), fps=25)
    report = audit(root, "pick", ["top", "inspect", "wrist"], ["a different string", TASKS[1]])
    text = " ".join(report.fails)
    assert "camera keys missing: inspect" in text and "fps is 25" in text and "task strings differ" in text


def test_pick_must_end_holding_and_place_must_end_open(tmp_path):
    root = write(tmp_path, [episode(i, end_gripper=io.GRIPPER_HOLD_MAX + 20, task=i % 2) for i in range(4)])
    assert any("outside the holding band" in f for f in audit(root, "pick").fails)
    assert not any("not open" in f for f in audit(root, "place").fails)
    assert any("not open" in f for f in audit(write(tmp_path / "b", [episode(i, end_gripper=5.0, task=i % 2) for i in range(4)]), "place").fails)


def test_hesitation_and_odd_length_warn_only(tmp_path):
    episodes = [episode(i, seconds=10, task=i % 2) for i in range(5)] + [episode(5, seconds=10, pause=True), episode(6, seconds=20)]
    report = audit(write(tmp_path, episodes), "pick")
    assert report.ok
    assert any("episode 5: stood still" in w for w in report.warnings)
    assert any("episode 6: 20.0 s against a median" in w for w in report.warnings)


def test_a_teleop_jump_fails(tmp_path):
    report = audit(write(tmp_path, [episode(0), episode(1, jump=True)]), "any")
    assert any("episode 1: a joint jumped" in f for f in report.fails)


def test_dropped_frames_fail_and_missing_quantiles_warn(tmp_path):
    late = episode(1)
    late["timestamp"] = late["timestamp"] + np.cumsum(np.where(np.arange(len(late)) % 8 == 0, 0.05, 0.0))  # every 8th frame arrives 50 ms late
    report = audit(write(tmp_path, [episode(0), late], quantiles=False), "any")
    assert any("episode 1" in f and "late" in f for f in report.fails)
    assert any("q01/q99" in w for w in report.warnings)


def test_degree_looking_units_and_copied_episodes_warn(tmp_path):
    wide = episode(0)
    wide["observation.state"] = [np.append(s[:5] * 1.5, s[5]) for s in wide["observation.state"]]
    wide["action"] = wide["observation.state"]
    twin = wide.assign(episode_index=1)
    report = audit(write(tmp_path, [wide, twin]), "any")
    assert any("looks like degrees" in w for w in report.warnings)
    assert any("identical to episode 0" in w for w in report.warnings)


def test_unbalanced_tasks_warn(tmp_path):
    report = audit(write(tmp_path, [episode(i, task=0) for i in range(4)] + [episode(4, task=1)]), "any")
    assert any("unbalanced" in w for w in report.warnings)
