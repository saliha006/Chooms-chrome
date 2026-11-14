"""build_real() with the hardware swapped for stand-ins: config checks, mover choice, a scripted run end to end."""

import shutil
import sys
import types

import numpy as np
import pytest
import yaml

import run
from common import capture
from common.mocks import MockCamera, MockInspector
from fallback.scripted import ScriptedMover
from robot import io

POSES = {
    "home": [0, 0, 0, 0, 0, 0], "pick_above": [10, 5, 0, 0, 0, 60], "pick": [10, 15, 0, 0, 0, 60],
    "pick_drop": [10, 15, 0, 0, 0, 60], "inspect": [-5, 5, 5, 0, 0, 0],
    "bowl_red": [-15, 5, 0, 0, 0, 0], "bowl_blue": [20, 5, 0, 0, 0, 0],
}


class BrickRobot(io.MockRobot):
    def send_action(self, action, *, goal_time=0.1):
        action = np.asarray(action, float).copy()
        action[io.GRIPPER] = max(action[io.GRIPPER], 30.0)  # a brick is always in the gripper's way
        super().send_action(action, goal_time=goal_time)


@pytest.fixture
def station(tmp_path, monkeypatch):
    """A filled-in copy of config/ and every hardware entry point replaced. Returns an edit helper."""
    config = tmp_path / "config"
    shutil.copytree(run.CONFIG, config)
    monkeypatch.setattr(run, "CONFIG", config)

    def edit(name, change):
        data = yaml.safe_load((config / name).read_text())
        change(data)
        (config / name).write_text(yaml.safe_dump(data))

    edit("cameras.yaml", lambda d: [cam.update(path=f"/dev/fake-{role}") for role, cam in d.items()])
    edit("robot.yaml", lambda d: d.update(port="/dev/fake-arm"))
    edit("waypoints.yaml", lambda d: d.update(POSES))

    monkeypatch.setattr(capture, "OpenCVCamera", lambda path, fourcc=None: MockCamera(size=(8, 8), fps=200))
    fake_perception = types.ModuleType("perception.inspector")
    fake_perception.Inspector = lambda xml, thresholds, model: MockInspector(("defective",))
    monkeypatch.setitem(sys.modules, "perception.inspector", fake_perception)

    def connect(port=None, calibration=None, mock=False):
        io._robot = BrickRobot()
        io._robot.connect()

    monkeypatch.setattr(io, "connect", connect)
    monkeypatch.setattr(run, "load_policy", lambda export_dir, devices: (f"policy from {export_dir}", devices[0]))
    yield edit
    io.disconnect()


def test_unset_camera_path_stops_before_anything_moves(station):
    station("cameras.yaml", lambda d: d["wrist"].update(path=None))
    with pytest.raises(SystemExit, match="wrist"):
        run.build_real({"pick", "place"}, 1, "t")
    assert io._robot is None


def test_missing_policy_export_suggests_scripted(station):
    with pytest.raises(SystemExit, match=r"act, smolvla.*--scripted pick,place"):
        run.build_real(set(), 1, "t")


def test_scripted_run_sorts_on_the_mock_arm(station):
    cell = run.build_real({"pick", "place"}, 1, "t")
    try:
        assert isinstance(cell.picker, ScriptedMover) and cell.placer is cell.picker
        cell.run()
    finally:
        cell.capture.stop()
    assert cell.sorted == 1
    assert np.allclose(io.observe()[:5], POSES["home"][:5], atol=2)  # homes at the end of the run


def test_learned_pick_with_scripted_place(station):
    station("models.yaml", lambda d: d["policies"].update(act="exports/act"))
    cell = run.build_real({"place"}, 1, "t")
    try:
        assert isinstance(cell.placer, ScriptedMover)
        assert type(cell.picker).__name__ == "LearnedMover"
        assert cell.picker.picker == "policy from exports/act" and cell.picker.placer is None
        assert cell.mode == "pick: act on GPU | place: scripted"  # the screen names the device it really loaded on
    finally:
        cell.capture.stop()


def test_clicked_zone_switches_to_the_scene_check(station):
    from perception.scene import SceneLocator

    station("scene.yaml", lambda d: d.update(zone=[[0, 0], [8, 0], [8, 8], [0, 8]]))
    cell = run.build_real({"pick", "place"}, 1, "t")
    try:
        assert isinstance(cell.locator, SceneLocator) and cell.finale is not None
    finally:
        cell.capture.stop()
