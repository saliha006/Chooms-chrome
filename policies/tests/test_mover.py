import threading

import numpy as np
import pytest

from common import deadline
from common.interfaces import Mover
from policies import episode
from policies.mover import GRIPPER_OPEN, LearnedMover
from robot import io

HOME = np.zeros(6)
INSPECT = np.array([0.0, -30, 40, 20, 0, 30])  # gripper 30 = holding a brick
DROP = np.array([10.0, 20, 20, 0, 0, 30])


class FakePolicy:
    """Stands in for an exported InferenceModel: always heads to one target."""

    def __init__(self, target):
        self.target, self.resets, self.calls, self.last_obs = np.asarray(target, float), 0, 0, None

    def reset(self):
        self.resets += 1

    def select_action(self, obs):
        self.last_obs = obs
        self.calls += 1
        return self.target


@pytest.fixture
def mover(monkeypatch):
    monkeypatch.setattr(io.time, "sleep", lambda s: None)
    monkeypatch.setattr(episode.time, "sleep", lambda s: None)
    io.connect(mock=True)
    place_target = np.array([40.0, 10, 10, 0, 0, GRIPPER_OPEN + 10])
    yield LearnedMover(FakePolicy(INSPECT), FakePolicy(place_target), {"home": HOME, "inspect": INSPECT, "pick_drop": DROP},
                       frames=lambda: {"wrist": np.zeros((4, 4, 3), np.uint8)}, pick_steps=40, place_steps=40)
    io.disconnect()


def test_is_a_mover(mover):
    assert isinstance(mover, Mover)


def test_pick_reaches_inspect_pose_holding_a_brick(mover):
    assert mover.pick_and_present()
    assert mover.picker.resets == 1
    assert set(mover.picker.last_obs) == {"observation.state", "observation.images.wrist"}


def test_place_passes_the_instruction_and_opens(mover):
    assert mover.place("place the brick in the red bowl")
    assert mover.placer.last_obs["task"] == ["place the brick in the red bowl"]


def test_reinspect_zero_regrasps(mover):
    mover.pick_and_present()
    assert mover.reinspect(0)
    assert mover.picker.resets == 2


def test_reinspect_roll_keeps_inspect_pose(mover):
    mover.pick_and_present()
    assert mover.reinspect(90)
    assert io.observe()[io.WRIST_ROLL] == pytest.approx(90)


def test_empty_gripper_fails_the_pick(mover):
    mover.picker.target = np.array([*INSPECT[:5], 0.0])  # closes fully: nothing grasped
    assert not mover.pick_and_present()
    assert mover.gripper_empty()


def test_episode_ends_early_once_the_stage_succeeds(mover):
    policy = FakePolicy(INSPECT)
    episode.run_episode(policy, mover.frames, steps=40, stop=lambda: policy.calls >= 3)
    assert policy.calls == 3


def test_episode_stops_when_the_deadline_fires(mover):
    abort = threading.Event()

    class FiresDuringStepTwo(FakePolicy):
        def select_action(self, obs):
            if self.calls == 1:
                abort.set()
            return super().select_action(obs)

    policy = FiresDuringStepTwo(INSPECT)
    episode.run_episode(policy, mover.frames, steps=40, abort_event=abort)
    assert policy.calls == 2


def test_a_fired_stage_deadline_fails_the_pick(mover):
    deadline.abort.set()
    try:
        assert not mover.pick_and_present()
        assert mover.picker.calls == 0  # no step was sent
    finally:
        deadline.abort.clear()


def test_estop_and_home(mover):
    mover.pick_and_present()
    mover.home()
    assert np.allclose(io.observe(), HOME, atol=2)
    mover.estop()
    assert not io.robot().torque
