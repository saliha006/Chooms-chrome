import numpy as np
import pytest

from common import estop
from robot import io


@pytest.fixture(autouse=True)
def mock_arm():
    io.connect(mock=True)
    yield io.robot()
    io.disconnect()


def test_act_caps_the_step_and_respects_limits():
    sent = io.act(np.array([50.0, 0, 0, 0, 0, 0]))
    assert sent[0] == io.MAX_STEP_DEG
    io.robot().joints = np.array([98.0, 0, 0, 0, 0, 0])
    assert io.act(np.array([500.0, 0, 0, 0, 0, 0]))[0] == 100.0


def test_move_to_reaches_target(monkeypatch):
    monkeypatch.setattr(io.time, "sleep", lambda s: None)
    target = np.array([20.0, -10, 15, 0, 90, 40])
    assert io.move_to(target, seconds=2.0)
    assert np.allclose(io.observe(), target)


def test_torque_off_stops_motion(mock_arm):
    io.torque_off()
    io.act(np.full(6, 30.0))
    assert np.allclose(io.observe(), 0.0) and not mock_arm.torque


def test_requested_estop_turns_torque_off_and_sends_nothing(mock_arm):
    estop.request()
    try:
        with pytest.raises(estop.EStopped):
            io.act(np.full(6, 30.0))
        with pytest.raises(estop.EStopped):  # move_to and the policy loop go through act()
            io.move_to(np.full(6, 30.0))
    finally:
        estop.clear()
    assert not mock_arm.torque and mock_arm.commands == []


def test_observe_needs_connect():
    io.disconnect()
    with pytest.raises(RuntimeError):
        io.observe()


def test_degree_sizes_follow_each_joints_calibrated_range(tmp_path):
    import json

    pytest.importorskip("physicalai.robot.so101")  # the calibration reader is the robot package's

    joints = {name: {"id": i + 1, "drive_mode": 0, "homing_offset": 0, "range_min": 1000, "range_max": 3000}
              for i, name in enumerate(io.JOINTS)}
    joints["wrist_roll"].update(range_min=0, range_max=4095)  # full turn
    path = tmp_path / "cal.json"
    path.write_text(json.dumps(joints))
    per_degree = io.per_degree(str(path))
    # 2000 ticks = 175.8 degrees span 200 units; a full turn spans 360 degrees; the gripper stays a percentage
    assert per_degree[0] == pytest.approx(200 / (2000 * 360 / 4095))
    assert per_degree[io.WRIST_ROLL] == pytest.approx(200 / 360, rel=1e-3)
    assert per_degree[io.GRIPPER] == 1.0


def test_real_connect_needs_the_calibration():
    with pytest.raises(ValueError, match="calibration"):
        io.connect(port="/dev/ttyACM0", calibration=None)


def test_speed_cap_is_the_same_angle_on_every_joint(monkeypatch):
    monkeypatch.setattr(io, "_per_degree", np.array([2.0, 1.0, 1.0, 1.0, 0.5, 1.0]))
    step = io.clamp_step(np.zeros(6), np.full(6, 50.0))
    assert step.tolist() == (io.MAX_STEP_DEG * np.array([2.0, 1.0, 1.0, 1.0, 0.5, 1.0])).tolist()


class Flaky(io.MockRobot):
    def __init__(self, failures):
        super().__init__()
        self.failures = failures

    def get_observation(self):
        if self.failures:
            self.failures -= 1
            raise ConnectionError("Sync read failed with comm result -6")
        return super().get_observation()


def test_observe_rides_through_a_brief_bus_dropout(monkeypatch):
    monkeypatch.setattr(io.time, "sleep", lambda s: None)
    monkeypatch.setattr(io, "_robot", Flaky(failures=io.OBSERVE_RETRIES))
    assert io.observe().shape == (6,)


def test_observe_still_raises_on_a_dead_bus(monkeypatch):
    monkeypatch.setattr(io.time, "sleep", lambda s: None)
    monkeypatch.setattr(io, "_robot", Flaky(failures=io.OBSERVE_RETRIES + 1))
    with pytest.raises(ConnectionError):
        io.observe()


def test_the_camera_can_confirm_a_brick_the_gripper_reading_misses(monkeypatch):
    io.robot().joints = np.array([0.0, 0, 0, 0, 0, 2.0])  # held at the tips: reads like closed on nothing
    assert not io.holding()
    io.see_grip(lambda: True)
    try:
        assert io.holding()
        io.robot().joints = np.array([0.0, 0, 0, 0, 0, 90.0])  # wide open: never a grasp, whatever the camera says
        assert not io.holding()
    finally:
        io.see_grip(None)
