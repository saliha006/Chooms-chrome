import numpy as np
import pytest

from policies import episode
from policies.episode import Smoothed, TemporalEnsemble
from robot import io

TARGET = np.array([60.0, -40, 50, 30, 20, 17])


class Steps:
    """A policy that plays a fixed list of actions, one per call."""

    def __init__(self, actions):
        self.actions, self.calls, self.resets = [np.asarray(a, float) for a in actions], 0, 0

    def reset(self):
        self.resets += 1

    def select_action(self, obs):
        self.calls += 1
        return self.actions[min(self.calls, len(self.actions)) - 1]


class Chunks:
    """Like InferenceModel: each chunk heads from the observed state to TARGET, off by +-`jitter` in turn
    (a fresh observation shifts the whole prediction a little: the jump at every chunk boundary)."""

    def __init__(self, length=10, jitter=0.0):
        self.length, self.jitter, self.queries, self.resets = length, jitter, 0, 0

    def reset(self):
        self.resets += 1

    def predict_action_chunk(self, obs):
        state = obs[episode.STATE_KEY][0].astype(float)
        sign = 1 if self.queries % 2 == 0 else -1
        self.queries += 1
        fractions = np.arange(1, self.length + 1)[:, None] / self.length
        return state + (TARGET - state) * fractions + sign * self.jitter


class Constant:
    """A chunk model whose chunk q is filled with the value q, so the ensemble's weights can be checked exactly."""

    def __init__(self, length):
        self.length, self.queries = length, 0

    def reset(self):
        pass

    def predict_action_chunk(self, obs):
        self.queries += 1
        return np.full((self.length, 1), self.queries - 1.0)


@pytest.fixture
def arm(monkeypatch):
    monkeypatch.setattr(episode.time, "sleep", lambda s: None)
    io.connect(mock=True)
    yield
    io.disconnect()


def frames():
    return {"wrist": np.zeros((4, 4, 3), np.uint8)}


def test_smoothing_blends_each_action_with_the_last():
    smoothed = Smoothed(Steps([[0.0], [10.0], [10.0]]), alpha=0.5)
    assert [smoothed.select_action({})[0] for _ in range(3)] == [0.0, 5.0, 7.5]


def test_reset_forgets_the_smoothed_action():
    smoothed = Smoothed(Steps([[0.0], [10.0]]), alpha=0.5)
    smoothed.select_action({})
    smoothed.reset()
    assert smoothed.select_action({})[0] == 10.0
    assert smoothed.model.resets == 1


@pytest.mark.parametrize("alpha", [0.0, 1.5])
def test_alpha_outside_the_range_is_refused(alpha):
    with pytest.raises(ValueError):
        Smoothed(Steps([[0.0]]), alpha)


def test_ensemble_weights_older_chunks_more():
    ensemble = TemporalEnsemble(Constant(length=3), m=0.5)
    out = [ensemble.select_action({})[0] for _ in range(4)]
    w = np.exp(-0.5 * np.arange(3))
    assert out[0] == 0.0
    assert out[1] == pytest.approx(w[:2] @ [0, 1] / w[:2].sum())
    assert out[3] == pytest.approx(w @ [1, 2, 3] / w.sum())  # chunk 0 has run out by step 3
    assert len(ensemble.chunks) == 3


def test_ensemble_can_query_less_often():
    model = Constant(length=4)
    ensemble = TemporalEnsemble(model, query_every=2)
    for _ in range(6):
        ensemble.select_action({})
    assert model.queries == 3


def test_ensemble_refuses_a_gap_between_chunks():
    ensemble = TemporalEnsemble(Constant(length=2), query_every=3)
    for _ in range(2):
        ensemble.select_action({})
    with pytest.raises(ValueError):
        ensemble.select_action({})


def test_ensemble_reset_starts_over():
    ensemble = TemporalEnsemble(Constant(length=3))
    ensemble.select_action({})
    ensemble.reset()
    assert ensemble.chunks == [] and ensemble.step == 0


@pytest.mark.parametrize("make", [lambda: TemporalEnsemble(Chunks(jitter=6)),
                                  lambda: Smoothed(TemporalEnsemble(Chunks(jitter=6), query_every=5), alpha=0.3),
                                  lambda: Smoothed(Steps([TARGET]), alpha=0.2)])
def test_smoothed_commands_stay_under_the_speed_cap_and_reach_the_target(arm, make):
    episode.run_episode(make(), frames, steps=150)
    sent = np.array(io.robot().commands)
    assert np.abs(np.diff(sent, axis=0)).max() <= io.MAX_STEP_DEG + 1e-9
    assert np.abs(sent[0]).max() <= io.MAX_STEP_DEG + 1e-9  # first step from the zero start pose
    assert np.allclose(io.observe(), TARGET, atol=io.POSE_TOLERANCE_DEG)


def test_the_ensemble_jitters_less_than_playing_chunks_back_to_back(arm):
    def swing(policy):
        io.robot().joints, io.robot().commands = TARGET.copy(), []
        episode.run_episode(policy, frames, steps=60)
        return np.abs(np.diff(np.array(io.robot().commands), axis=0)).max()

    class BackToBack(Chunks):  # what InferenceModel.select_action does: play a whole chunk, then ask again
        def __init__(self, **kwargs):
            super().__init__(**kwargs)
            self.buffer = []

        def select_action(self, obs):
            if not self.buffer:
                self.buffer = list(self.predict_action_chunk(obs))
            return self.buffer.pop(0)

    assert swing(TemporalEnsemble(Chunks(jitter=6))) < swing(BackToBack(jitter=6)) / 1.5
