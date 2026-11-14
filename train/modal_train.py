"""Train ACT or SmolVLA on a Modal GPU; checkpoints land in the `sortsense-runs` Volume.

    modal run train/modal_train.py --policy act --dataset lerobot/svla_so100_pickplace --steps 200
    modal run train/modal_train.py --policy smolvla --dataset eruedas/so101_3cams_pickplace-red-lego_real --steps 200 --cameras top,gripper,left
    modal run train/modal_train.py --dataset <hf_id> --steps 20000 --sweep      # F11: 18 / 36 / 54 episodes in parallel
    modal run train/modal_train.py --dataset lerobot/svla_so100_pickplace --steps 100 --sweep --sweep-sizes 2,4   # A8 smoke
    modal volume get sortsense-runs <job> ./checkpoints/                         # fetch, then back up before export

`modal run` is for a quick run you watch: it dies with this laptop's connection. Real runs go through the deployed
app (`modal deploy train/modal_train.py`, then `python -m train.launch`), which keeps going whatever the laptop does.
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

APP_NAME = "sortsense-train"
app = modal.App(APP_NAME)
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
def train_act(dataset: str, steps: int, lr: float | None, episodes: int, job: str, episode_ids: tuple[int, ...] = ()) -> float:
    return run(commands.act(dataset, steps, f"/runs/{job}", lr, episodes, episode_ids))


@app.function(image=lerobot_image, **on_gpu)
def train_smolvla(dataset: str, steps: int, lr: float | None, episodes: int, job: str, cameras: tuple[str, ...]) -> float:
    return run(commands.smolvla(dataset, steps, f"/runs/{job}", lr, episodes, cameras))


def log_run(job: str, policy: str, dataset: str, episodes: int, steps: int, seconds: float) -> None:
    if not RUNS_MD.exists():
        RUNS_MD.write_text("# Modal training runs\n\n| When | Job | Policy | Dataset | Episodes | Steps | GPU | Wall time (min) | Cost |\n|---|---|---|---|---|---|---|---|---|\n")
    with RUNS_MD.open("a") as f:
        f.write(f"| {datetime.now():%Y-%m-%d %H:%M} | {job} | {policy} | {dataset} | {episodes or 'all'} | "
                f"{steps} | {GPU} | {seconds / 60:.1f} | TBD (Modal dashboard) |\n")


def plan(policy: str, steps: int, episodes: int, sweep: bool, sweep_sizes: str, cameras: str) -> tuple[str, list[tuple[int, str]], tuple[str, ...]]:
    """Check the options and name each job: (policy, [(episodes, job name)], SmolVLA's camera order)."""
    if policy not in ("act", "smolvla"):
        raise SystemExit("--policy must be act or smolvla")
    if cameras and policy != "smolvla":
        raise SystemExit("--cameras maps SmolVLA's camera slots; ACT trains on the dataset's own camera names")
    if sweep:
        policy, sizes = "act", tuple(int(n) for n in sweep_sizes.split(","))
    else:
        sizes = (episodes,)
    stamp = datetime.now().strftime("%m%d-%H%M%S")
    return policy, [(n, commands.job_name(policy, n, steps, stamp)) for n in sizes], tuple(c for c in cameras.split(",") if c)


@app.local_entrypoint()
def main(dataset: str, policy: str = "act", steps: int = 200, lr: float | None = None, episodes: int = 0, sweep: bool = False,
         sweep_sizes: str = ",".join(map(str, commands.SWEEP_EPISODES)),  # smaller sizes fit a public set with fewer episodes
         cameras: str = "",  # SmolVLA only: the dataset's camera names in camera1, camera2, camera3 order
         episode_ids: str = "", tag: str = ""):  # ACT only: train on these episodes, e.g. the colour hedge (train/hedge.py prints them)
    if episode_ids:
        ids = commands.parse_episode_ids(episode_ids, policy, sweep)
        job = commands.job_name("act", len(ids), steps, datetime.now().strftime("%m%d-%H%M%S"), tag)
        seconds = train_act.remote(dataset, steps, lr, 0, job, ids)
        log_run(job, "act", dataset, len(ids), steps, seconds)
        print(f"{job}: {seconds / 60:.1f} min -> volume sortsense-runs/{job}")
        return
    policy, jobs, camera_order = plan(policy, steps, episodes, sweep, sweep_sizes, cameras)
    if policy == "smolvla":
        seconds = [train_smolvla.remote(dataset, steps, lr, n, job, camera_order) for n, job in jobs]
    else:
        seconds = train_act.starmap([(dataset, steps, lr, n, job) for n, job in jobs])
    for (n, job), s in zip(jobs, seconds):
        log_run(job, policy, dataset, n, steps, s)
        print(f"{job}: {s / 60:.1f} min -> volume sortsense-runs/{job}")
