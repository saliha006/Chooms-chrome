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
BRICK_WIDTH = 17.0  # gripper reading when closed on a Duplo brick (N8 average 17.4, Intel laptop 2026-11-14)


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


def test_bricks_come_from_successive_pick_slots(monkeypatch):
    from fallback import scripted

    poses = {name: np.zeros(6) for name in scripted.POSES}
    poses["pick_above_2"], poses["pick_2"] = np.full(6, 2.0), np.full(6, 2.5)
    mover = scripted.ScriptedMover(poses)
    visited = []
    monkeypatch.setattr(mover, "_pick_from", lambda above, pick: visited.append(pick) or True)
    for _ in range(3):
        mover.pick_and_present()
    assert visited == ["pick", "pick_2", "pick"]  # cycles back to slot 1 after the last taught slot


def test_a_regrasp_does_not_use_up_a_slot(monkeypatch):
    from fallback import scripted

    poses = {name: np.zeros(6) for name in scripted.POSES}
    poses["pick_above_2"], poses["pick_2"] = np.full(6, 2.0), np.full(6, 2.5)
    mover = scripted.ScriptedMover(poses)
    visited = []
    monkeypatch.setattr(mover, "_pick_from", lambda above, pick: visited.append(pick) or True)
    monkeypatch.setattr(mover, "_go", lambda *a: True)
    monkeypatch.setattr(mover, "_set_gripper", lambda *a: None)
    mover.reinspect(0)
    mover.pick_and_present()
    assert visited == ["pick", "pick"]


class OffSpotRobot(io.MockRobot):
    """A brick lies at `brick_pan` on the slot-1 row: the gripper only closes on it when shut there at pick height."""

    def __init__(self, brick_pan):
        super().__init__()
        self.brick_pan, self.held = brick_pan, False

    def send_action(self, action, *, goal_time=0.1):
        action = np.asarray(action, float).copy()
        at_brick = abs(self.joints[0] - self.brick_pan) < 1.0 and self.joints[1] > POSES["pick_above"][1] + 4  # down at the slot
        if action[io.GRIPPER] < BRICK_WIDTH and at_brick:
            self.held = True
        if action[io.GRIPPER] > 30:
            self.held = False
        if self.held:
            action[io.GRIPPER] = max(action[io.GRIPPER], BRICK_WIDTH)
        super().send_action(action, goal_time=goal_time)


def search_mover(search_cm):
    poses = {k: np.asarray(v, float) for k, v in POSES.items()}
    poses["pick_above_2"], poses["pick_2"] = np.array([40.0, 5, 0, 0, 0, 60]), np.array([40.0, 15, 0, 0, 0, 60])
    return ScriptedMover(poses, search_cm)


@pytest.fixture
def off_spot():
    shift = float(np.degrees(1.5 / scripted.REACH_CM))  # the brick 1.5 cm to one side of slot 1

    def make(side):
        io.connect(mock=True)
        io._robot = OffSpotRobot(POSES["pick"][0] + side * shift)
        io._robot.connect()
        return io._robot

    yield make
    io.disconnect()


def test_without_search_a_miss_moves_on_to_the_next_slot(off_spot):
    robot = off_spot(+1)
    mover = search_mover(0.0)
    assert mover.pick_and_present() is False
    assert mover.pick_and_present() is False and robot.joints[0] != POSES["pick"][0]  # went to slot 2 instead
    assert not robot.held


def test_a_miss_is_searched_once_to_the_side_then_held(off_spot):
    robot = off_spot(+1)
    mover = search_mover(1.5)
    assert mover.pick_and_present() is False
    assert mover.pick_and_present() is True and robot.held
    assert at("inspect", robot)


def test_each_miss_is_searched_once_and_a_slot_alternates_sides(off_spot):
    robot = off_spot(-1)  # nothing on slot 2, slot 1's brick on the - side
    mover = search_mover(1.5)
    shift = float(np.degrees(1.5 / scripted.REACH_CM))
    pans = []
    send = robot.send_action
    robot.send_action = lambda action, **kw: pans.append(np.asarray(action)[0]) or send(action, **kw)

    def pick():
        pans.clear()
        return mover.pick_and_present()

    assert pick() is False and pick() is False  # slot 1, then its search to the + side
    assert np.isclose(pans, POSES["pick"][0] + shift).any()
    assert pick() is False and max(pans) == 40.0  # never searched twice: slot 2
    assert pick() is False and np.isclose(pans, 40.0 + shift).any()  # slot 2's own search
    assert pick() is False  # slot 1 again
    assert pick() is True and robot.held  # slot 1's second search tries the - side
