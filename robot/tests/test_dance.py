import numpy as np
import pytest

from common import estop
from robot import dance, io

HOME = np.array([0.0, -20, 30, 10, 0, 20])


@pytest.fixture(autouse=True)
def mock_arm(monkeypatch):
    monkeypatch.setattr(io.time, "sleep", lambda s: None)
    io.connect(mock=True)
    io.robot().joints = HOME.copy()
    yield io.robot()
    io.disconnect()
    estop.clear()


def test_poses_sway_both_ways_bow_and_tilt_then_home():
    poses = dance.poses(HOME)
    assert len(poses) == 7  # 3 cycles x (left, right) + home
    left, right = poses[0], poses[1]
    assert left[dance.PAN] == 25 and right[dance.PAN] == -25
    assert left[dance.FLEX] == right[dance.FLEX] == HOME[dance.FLEX] + 10  # bowed on both sides
    assert left[dance.ROLL] == 10 and right[dance.ROLL] == -10  # tilted towards the side it faces
    assert np.array_equal(poses[-1], HOME)


def test_poses_stay_inside_joint_limits():
    near_limit = HOME.copy()
    near_limit[dance.PAN] = 100.0
    for pose in dance.poses(near_limit):
        assert np.all(pose >= io.JOINT_MIN) and np.all(pose <= io.JOINT_MAX)


def test_dance_ends_at_home_and_visits_both_sides(mock_arm):
    assert dance.dance(HOME, half_period_s=2.0)
    pans = [cmd[dance.PAN] for cmd in mock_arm.commands]
    assert max(pans) == pytest.approx(25, abs=2) and min(pans) == pytest.approx(-25, abs=2)  # move_to arrives within 2°
    assert np.allclose(io.observe(), HOME)


def test_every_step_respects_the_speed_cap(mock_arm):
    dance.dance(HOME, half_period_s=2.0)
    steps = np.diff(np.array([HOME, *mock_arm.commands]), axis=0)
    assert np.abs(steps).max() <= io.MAX_STEP_DEG + 1e-9


def test_e_stop_stops_the_dance():
    estop.request()
    with pytest.raises(estop.EStopped):
        dance.dance(HOME)
