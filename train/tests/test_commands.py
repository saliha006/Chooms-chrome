import json

import pytest

from train.commands import ACT_LR, SWEEP_EPISODES, act, job_name, smolvla


def arg(cmd: list[str], flag: str) -> str:
    return cmd[cmd.index(flag) + 1]


def test_act_trains_with_studio_at_the_safe_lr():
    cmd = act("user/bricks", 200, "/runs/x")
    assert cmd[:2] == ["physicalai", "fit"]
    assert arg(cmd, "--model.optimizer_lr") == str(ACT_LR)
    assert arg(cmd, "--trainer.default_root_dir") == "/runs/x"
    assert "--data.episodes" not in cmd


def test_act_lr_can_be_overridden():
    assert arg(act("user/bricks", 200, "/runs/x", lr=2e-5), "--model.optimizer_lr") == "2e-05"


def test_smolvla_fine_tunes_the_base_model_with_lerobot():
    cmd = smolvla("user/bricks", 10, "/runs/y")
    assert cmd[:2] == ["lerobot-train", "--policy.path=lerobot/smolvla_base"]
    assert "--policy.push_to_hub=false" in cmd
    # LeRobot 0.7 has no wandb section, and SmolVLA keeps its own learning rate unless asked
    assert not any(c.startswith(("--wandb", "--policy.optimizer_lr")) for c in cmd)


def test_smolvla_lr_only_when_asked():
    assert "--policy.optimizer_lr=0.0001" in smolvla("user/bricks", 10, "/runs/y", lr=1e-4)


def test_smolvla_maps_dataset_cameras_onto_the_pretrained_slots():
    flag = smolvla("user/bricks", 10, "/runs/y", cameras=("top", "gripper", "left"))[-1]
    assert flag.startswith("--rename_map=")
    assert json.loads(flag.removeprefix("--rename_map=")) == {
        "observation.images.top": "observation.images.camera1",
        "observation.images.gripper": "observation.images.camera2",
        "observation.images.left": "observation.images.camera3",
    }
    assert not any(c.startswith("--rename_map") for c in smolvla("user/bricks", 10, "/runs/y"))


def test_episode_subset_takes_the_first_n():
    assert arg(act("user/bricks", 10, "/runs/z", episodes=3), "--data.episodes") == "[0,1,2]"
    assert smolvla("user/bricks", 10, "/runs/z", episodes=3)[-1] == "--dataset.episodes=[0,1,2]"


def test_job_names_are_unique_per_size_and_per_run():
    assert SWEEP_EPISODES == (18, 36, 54)
    assert len({job_name("act", n, 100, "1114-050000") for n in SWEEP_EPISODES}) == 3
    assert job_name("act", 0, 100, "a") != job_name("act", 0, 100, "b")


def test_act_command_parses_with_studios_own_parser():
    fit = pytest.importorskip("physicalai.cli.fit")  # only where physicalai-train is installed
    cfg = fit.build_parser().parse_args(act("user/bricks", 200, "/runs/x", episodes=3)[2:])
    assert cfg.model.class_path == "physicalai.policies.ACT"
    assert cfg.model.init_args.optimizer_lr == ACT_LR
    assert cfg.data.init_args.episodes == [0, 1, 2]
    assert cfg.trainer.max_steps == 200
