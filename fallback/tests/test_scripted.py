from pathlib import Path

import numpy as np
import pytest
import yaml

from common.interfaces import Mover
from fallback import scripted
from fallback.scripted import ScriptedMover, load_waypoints
from fallback.teach import save_pose
from robot import io

# Small poses so the 5°-per-step speed cap keeps the tests quick.
POSES = {
    "home": [0, 0, 0, 0, 0, 0],
    "pick_above": [10, 5, 0, 0, 0, 60],
    "pick": [10, 15, 0, 0, 0, 60],
    "pick_drop": [10, 15, 0, 0, 0, 60],
    "inspect": [-5, 5, 5, 0, 0, 0],
    "bowl_red": [-15, 5, 0, 0, 0, 0],
    "bowl_blue": [20, 5, 0, 0, 0, 0],
}
BRICK_WIDTH = 30.0  # gripper reading when closed on a brick


class BrickRobot(io.MockRobot):
    """MockRobot whose gripper closes on a brick (stops at BRICK_WIDTH) while one is held."""

    def __init__(self, brick: bool = True):
        super().__init__()
        self.brick = brick

    def send_action(self, action, *, goal_time=0.1):
        action = np.asarray(action, float).copy()
        if self.brick:
            action[io.GRIPPER] = max(action[io.GRIPPER], BRICK_WIDTH)
        super().send_action(action, goal_time=goal_time)


@pytest.fixture
def arm():
    def make(brick=True):
        io.connect(mock=True)
        io._robot = BrickRobot(brick)
        io._robot.connect()
        return io._robot

    yield make
    io.disconnect()


@pytest.fixture
def mover():
    return ScriptedMover({k: np.asarray(v, float) for k, v in POSES.items()})


def at(name, robot):
    return np.allclose(robot.joints[:5], POSES[name][:5], atol=scripted.ARRIVE_TOLERANCE_DEG)


def test_satisfies_mover_contract(mover):
    assert isinstance(mover, Mover)


def test_pick_presents_a_held_brick_at_inspection(arm, mover):
    robot = arm()
    assert mover.pick_and_present()
    assert at("inspect", robot)
    assert robot.joints[io.GRIPPER] == pytest.approx(BRICK_WIDTH)


def test_pick_with_no_brick_reports_failure(arm, mover):
    arm(brick=False)
    assert not mover.pick_and_present()
    assert mover.gripper_empty()


def test_place_goes_to_the_bowl_the_instruction_names(arm, mover):
    robot = arm()
    mover.pick_and_present()
    assert mover.place("place the brick in the red bowl")
    assert at("bowl_red", robot)
    assert robot.joints[io.GRIPPER] >= io.GRIPPER_OPEN - io.POSE_TOLERANCE_DEG


@pytest.mark.parametrize("verdict, pose", [("perfect", "bowl_blue"), ("defective", "bowl_red")])
def test_rules_strings_reach_the_role_pose(arm, mover, verdict, pose):
    robot = arm()
    mover.pick_and_present()
    rules = yaml.safe_load((Path(__file__).resolve().parents[2] / "config" / "rules.yaml").read_text())
    assert mover.place(rules[verdict])
    assert at(pose, robot)


def test_place_rejects_an_instruction_without_a_bowl(arm, mover):
    arm()
    with pytest.raises(ValueError):
        mover.place("put it somewhere nice")


def test_regrasp_ends_back_at_inspection_holding_the_brick(arm, mover):
    robot = arm()
    mover.pick_and_present()
    assert mover.reinspect(0)
    assert at("inspect", robot) and not mover.gripper_empty()


def test_wrist_roll_stays_at_inspection(arm, mover):
    robot = arm()
    mover.pick_and_present()
    assert mover.reinspect(10)
    assert robot.joints[io.WRIST_ROLL] == pytest.approx(10, abs=scripted.ARRIVE_TOLERANCE_DEG)


def test_estop_turns_torque_off(arm, mover):
    robot = arm()
    mover.estop()
    assert robot.torque is False


def test_untaught_waypoints_are_named(tmp_path):
    path = tmp_path / "waypoints.yaml"
    path.write_text("home: [0, 0, 0, 0, 0, 0]\npick: null\n")
    with pytest.raises(ValueError, match="pick_above"):
        load_waypoints(path)


def test_teach_writes_poses_and_keeps_comments(tmp_path):
    path = tmp_path / "waypoints.yaml"
    path.write_text("# header\nhome: null   # rest pose\npick: null\n")
    save_pose(path, "home", [1, 2, 3, 4, 5, 6])
    text = path.read_text()
    assert "# header" in text and "# rest pose" in text
    assert yaml.safe_load(text)["home"] == [1.0, 2.0, 3.0, 4.0, 5.0, 6.0]
