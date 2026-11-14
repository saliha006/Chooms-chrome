import threading

import numpy as np
import pytest

from common import deadline
from common.interfaces import Mover
from policies import episode
from policies.mover import LearnedMover
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
    place_target = np.array([40.0, 10, 10, 0, 0, io.GRIPPER_OPEN + 10])
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


@pytest.mark.parametrize(("gripper", "held"), [(4.0, False), (io.GRIPPER_EMPTY_BELOW, True), (30.0, True),
                                               (io.GRIPPER_HOLD_MAX, True), (io.GRIPPER_HOLD_MAX + 1, False)])
def test_holding_is_a_band_not_just_not_closed(mover, gripper, held):
    joints = io.observe()
    joints[io.GRIPPER] = gripper
    io.robot().joints = joints
    assert io.holding() is held and mover.gripper_empty() is (not held)


def test_an_open_gripper_at_the_pose_is_not_a_grasp(mover):
    mover.picker.target = np.array([*INSPECT[:5], io.GRIPPER_HOLD_MAX + 20])
    assert not mover.pick_and_present()


def test_pick_ends_early_once_held_at_the_pose(mover):
    assert mover.pick_and_present()
    assert mover.picker.calls < mover.pick_steps


def test_place_ends_early_once_the_gripper_is_open(mover):
    assert mover.place("place the brick in the red bowl")
    assert mover.placer.calls < mover.place_steps


def test_place_rolls_the_wrist_back_before_the_policy_starts(mover):
    first_state = []

    class Recording(FakePolicy):
        def select_action(self, obs):
            first_state.append(obs["observation.state"][0].copy())
            return super().select_action(obs)

    mover.placer = Recording(mover.placer.target)
    mover.pick_and_present()
    assert mover.reinspect(90)
    assert mover.place("place the brick in the red bowl")
    assert first_state[0][io.WRIST_ROLL] == pytest.approx(INSPECT[io.WRIST_ROLL], abs=io.POSE_TOLERANCE_DEG)


@pytest.mark.parametrize("landed", [True, False])
def test_bowl_check_decides_a_place_when_given(mover, landed):
    seen = []
    mover.frames = lambda: {"top": np.zeros((4, 4, 3), np.uint8), "wrist": np.zeros((4, 4, 3), np.uint8)}
    mover.bowl_check = lambda instruction, before, after: seen.append((instruction, before.shape, after.shape)) or landed
    assert mover.place("place the brick in the red bowl") is landed
    assert seen == [("place the brick in the red bowl", (4, 4, 3), (4, 4, 3))]
