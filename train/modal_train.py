"""Train ACT or SmolVLA on a Modal GPU; checkpoints land in the `sortsense-runs` Volume.

    modal run train/modal_train.py --policy act --dataset lerobot/svla_so100_pickplace --steps 200
    modal run train/modal_train.py --policy smolvla --dataset <hf_id> --steps 10000
    modal run train/modal_train.py --dataset <hf_id> --steps 20000 --sweep      # F11: 18 / 36 / 54 episodes in parallel
    modal run train/modal_train.py --dataset lerobot/svla_so100_pickplace --steps 100 --sweep --sweep-sizes 2,4   # A8 smoke
    modal volume get sortsense-runs <job> ./checkpoints/                         # fetch, then back up before export

ACT trains with Physical AI Studio's trainer and SmolVLA with LeRobot (decisions.md D20), so each has its own image.
`--lr` is optional: ACT defaults to 1e-5, SmolVLA to its own 1e-4.
Needs `modal token new` once, and either a Modal secret named `huggingface` holding HF_TOKEN or HF_TOKEN set in the shell.
Each run appends GPU type and wall time to train/runs.md (the Modal side track, F10).
"""

import os
import subprocess
import time
from datetime import datetime
from pathlib import Path

import modal

from train import commands

GPU = "A100"
RUNS_MD = Path(__file__).with_name("runs.md")

app = modal.App("sortsense-train")
base_image = modal.Image.debian_slim(python_version="3.12").apt_install("ffmpeg", "git")  # LeRobot datasets store camera streams as video
studio_image = base_image.pip_install("physicalai-train[cu128]==0.3.0").add_local_python_source("train")
lerobot_image = base_image.pip_install("lerobot[smolvla,training]==0.7.0").add_local_python_source("train")  # lerobot-train needs the training extra (datasets)
volume = modal.Volume.from_name("sortsense-runs", create_if_missing=True)
# The named secret on the team's Modal account; on a fresh machine HF_TOKEN from the shell is forwarded instead.
hf_secret = modal.Secret.from_local_environ(["HF_TOKEN"]) if os.environ.get("HF_TOKEN") else modal.Secret.from_name("huggingface")
on_gpu = dict(gpu=GPU, timeout=4 * 3600, volumes={"/runs": volume}, secrets=[hf_secret])


def run(cmd: list[str]) -> float:
    start = time.monotonic()
    subprocess.run(cmd, check=True)
    volume.commit()
    return time.monotonic() - start


@app.function(image=studio_image, **on_gpu)
def train_act(dataset: str, steps: int, lr: float | None, episodes: int, job: str) -> float:
    return run(commands.act(dataset, steps, f"/runs/{job}", lr, episodes))


@app.function(image=lerobot_image, **on_gpu)
def train_smolvla(dataset: str, steps: int, lr: float | None, episodes: int, job: str) -> float:
    return run(commands.smolvla(dataset, steps, f"/runs/{job}", lr, episodes))


TRAINERS = {"act": train_act, "smolvla": train_smolvla}


def log_run(job: str, policy: str, dataset: str, episodes: int, steps: int, seconds: float) -> None:
    if not RUNS_MD.exists():
        RUNS_MD.write_text("# Modal training runs\n\n| When | Job | Policy | Dataset | Episodes | Steps | GPU | Wall time (min) | Cost |\n|---|---|---|---|---|---|---|---|---|\n")
    with RUNS_MD.open("a") as f:
        f.write(f"| {datetime.now():%Y-%m-%d %H:%M} | {job} | {policy} | {dataset} | {episodes or 'all'} | "
                f"{steps} | {GPU} | {seconds / 60:.1f} | TBD (Modal dashboard) |\n")


@app.local_entrypoint()
def main(dataset: str, policy: str = "act", steps: int = 200, lr: float | None = None, episodes: int = 0, sweep: bool = False,
         sweep_sizes: str = ",".join(map(str, commands.SWEEP_EPISODES))):  # smaller sizes fit a public set with fewer episodes
    if policy not in TRAINERS:
        raise SystemExit(f"--policy must be one of: {', '.join(TRAINERS)}")
    if sweep:
        policy, sizes = "act", tuple(int(n) for n in sweep_sizes.split(","))
    else:
        sizes = (episodes,)
    stamp = datetime.now().strftime("%m%d-%H%M%S")
    jobs = [commands.job_name(policy, n, steps, stamp) for n in sizes]
    seconds = TRAINERS[policy].starmap([(dataset, steps, lr, n, job) for n, job in zip(sizes, jobs)])
    for n, job, s in zip(sizes, jobs, seconds):
        log_run(job, policy, dataset, n, steps, s)
        print(f"{job}: {s / 60:.1f} min -> volume sortsense-runs/{job}")
