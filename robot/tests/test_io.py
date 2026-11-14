import numpy as np
import pytest

from robot import io


@pytest.fixture(autouse=True)
def mock_arm():
    io.connect(mock=True)
    yield io.robot()
    io.disconnect()


def test_act_caps_the_step_and_respects_limits():
    sent = io.act(np.array([50.0, 0, 0, 0, 0, 0]))
    assert sent[0] == io.MAX_STEP_DEG
    io.robot().joints = np.array([108.0, 0, 0, 0, 0, 0])
    assert io.act(np.array([500.0, 0, 0, 0, 0, 0]))[0] == 110.0


def test_move_to_reaches_target(monkeypatch):
    monkeypatch.setattr(io.time, "sleep", lambda s: None)
    target = np.array([20.0, -10, 15, 0, 90, 40])
    assert io.move_to(target, seconds=2.0)
    assert np.allclose(io.observe(), target)


def test_torque_off_stops_motion(mock_arm):
    io.torque_off()
    io.act(np.full(6, 30.0))
    assert np.allclose(io.observe(), 0.0) and not mock_arm.torque


def test_observe_needs_connect():
    io.disconnect()
    with pytest.raises(RuntimeError):
        io.observe()
