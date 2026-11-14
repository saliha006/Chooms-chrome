"""Training command lines, one builder per policy. Pure, so they are testable without Modal.

ACT trains with Physical AI Studio's trainer (`physicalai fit`), so its checkpoint exports straight into the
`physicalai` runtime. SmolVLA fine-tunes `lerobot/smolvla_base` with LeRobot, because Studio's SmolVLA weight
loader is unfinished (decisions.md D20).
"""

import json

SWEEP_EPISODES = (18, 36, 54)  # F11: success vs number of demonstrations (decisions.md D9)
ACT_LR = 1e-5  # 1e-4 makes ACT output one pose whatever it sees (Studio #998)
BATCH_SIZE = 8


def job_name(policy: str, episodes: int, steps: int, stamp: str) -> str:
    # The stamp keeps re-runs apart: LeRobot refuses to write into an existing output directory.
    return f"{policy}-{episodes or 'all'}ep-{steps}st-{stamp}"


def _first_episodes(episodes: int) -> str:
    return f"[{','.join(str(i) for i in range(episodes))}]"


def act(dataset: str, steps: int, output_dir: str, lr: float | None = None, episodes: int = 0) -> list[str]:
    cmd = [
        "physicalai", "fit",
        "--model", "physicalai.policies.ACT",
        "--model.optimizer_lr", str(lr or ACT_LR),
        "--data", "physicalai.data.lerobot.LeRobotDataModule",
        "--data.repo_id", dataset,
        "--data.train_batch_size", str(BATCH_SIZE),
        # Forked loader workers inherit the video decoders Studio's quantile pass opened and fail with
        # "Invalid data found when processing input" (reproduced 2026-11-14); no workers, no fork.
        "--data.num_workers", "0",
        "--trainer.max_steps", str(steps),
        "--trainer.accelerator", "gpu",
        "--trainer.devices", "1",
        "--trainer.default_root_dir", output_dir,
    ]
    if episodes:
        cmd += ["--data.episodes", _first_episodes(episodes)]
    return cmd


def smolvla(dataset: str, steps: int, output_dir: str, lr: float | None = None, episodes: int = 0,
            cameras: tuple[str, ...] = ()) -> list[str]:
    cmd = [
        "lerobot-train",
        "--policy.path=lerobot/smolvla_base",
        f"--dataset.repo_id={dataset}",
        f"--steps={steps}",
        f"--batch_size={BATCH_SIZE}",
        "--policy.device=cuda",
        "--policy.push_to_hub=false",
        f"--output_dir={output_dir}",
    ]
    if lr:  # otherwise SmolVLA keeps its own default (1e-4)
        cmd.append(f"--policy.optimizer_lr={lr}")
    if episodes:
        cmd.append(f"--dataset.episodes={_first_episodes(episodes)}")
    if cameras:  # smolvla_base was pretrained on camera1..3; LeRobot rejects other camera names
        rename = {f"observation.images.{name}": f"observation.images.camera{i}" for i, name in enumerate(cameras, 1)}
        cmd.append(f"--rename_map={json.dumps(rename)}")
    return cmd
