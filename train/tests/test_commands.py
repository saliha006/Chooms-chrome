import pytest

from train.commands import SWEEP_EPISODES, build, job_name


def test_act_command_uses_safe_lr_and_no_hub_push():
    cmd = build("act", "user/bricks", 200, 1e-5, "/runs/x")
    assert cmd[:2] == ["lerobot-train", "--policy.type=act"]
    assert "--policy.optimizer_lr=1e-05" in cmd
    assert "--policy.push_to_hub=false" in cmd
    assert not any(c.startswith("--dataset.episodes") for c in cmd)


def test_smolvla_starts_from_the_base_model():
    assert "--policy.path=lerobot/smolvla_base" in build("smolvla", "user/bricks", 10, 1e-4, "/runs/y")


def test_episode_subset_takes_the_first_n():
    cmd = build("act", "user/bricks", 10, 1e-5, "/runs/z", episodes=3)
    assert cmd[-1] == "--dataset.episodes=[0,1,2]"
    assert "--job_name=act-3ep-10st" in cmd


def test_unknown_policy_rejected():
    with pytest.raises(ValueError):
        build("diffusion", "user/bricks", 10, 1e-5, "/runs/w")


def test_sweep_sizes_and_job_names_are_distinct():
    assert SWEEP_EPISODES == (18, 36, 54)
    assert len({job_name("act", n, 100) for n in SWEEP_EPISODES}) == 3
