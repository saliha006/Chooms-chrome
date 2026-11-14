"""Train ACT or SmolVLA on a Modal GPU; checkpoints land in the `sortsense-runs` Volume.

    modal run train/modal_train.py --policy act --dataset lerobot/svla_so100_pickplace --steps 200
    modal run train/modal_train.py --policy smolvla --dataset <hf_id> --steps 10000
    modal run train/modal_train.py --dataset <hf_id> --steps 20000 --sweep      # F11: 18 / 36 / 54 episodes in parallel
    modal volume get sortsense-runs <job_name> ./checkpoints/                    # fetch, then back up before export

Needs `modal token new` once, and a Modal secret named `huggingface` holding HF_TOKEN.
Each run appends GPU type and wall time to train/runs.md (the Modal side track, F10).
"""

import subprocess
import time
from datetime import datetime
from pathlib import Path

import modal

from train.commands import SWEEP_EPISODES, build, job_name

GPU = "A100"
RUNS_MD = Path(__file__).with_name("runs.md")

app = modal.App("sortsense-train")
image = (
    modal.Image.debian_slim(python_version="3.12")
    .apt_install("ffmpeg", "git")  # LeRobot datasets store camera streams as video
    .pip_install("lerobot==0.7.0")
    .add_local_python_source("train")
)
volume = modal.Volume.from_name("sortsense-runs", create_if_missing=True)


@app.function(image=image, gpu=GPU, timeout=4 * 3600, volumes={"/runs": volume}, secrets=[modal.Secret.from_name("huggingface")])
def train(policy: str, dataset: str, steps: int, lr: float, episodes: int) -> dict:
    job = job_name(policy, episodes, steps)
    start = time.monotonic()
    subprocess.run(build(policy, dataset, steps, lr, f"/runs/{job}", episodes), check=True)
    volume.commit()
    return {"job": job, "policy": policy, "dataset": dataset, "episodes": episodes or "all", "steps": steps, "seconds": time.monotonic() - start}


def log_run(result: dict) -> None:
    if not RUNS_MD.exists():
        RUNS_MD.write_text("# Modal training runs\n\n| When | Job | Policy | Dataset | Episodes | Steps | GPU | Wall time (min) | Cost |\n|---|---|---|---|---|---|---|---|---|\n")
    with RUNS_MD.open("a") as f:
        f.write(f"| {datetime.now():%Y-%m-%d %H:%M} | {result['job']} | {result['policy']} | {result['dataset']} | {result['episodes']} | "
                f"{result['steps']} | {GPU} | {result['seconds'] / 60:.1f} | TBD (Modal dashboard) |\n")


@app.local_entrypoint()
def main(dataset: str, policy: str = "act", steps: int = 200, lr: float = 1e-5, episodes: int = 0, sweep: bool = False):
    if sweep:
        results = list(train.starmap([("act", dataset, steps, lr, n) for n in SWEEP_EPISODES]))
    else:
        results = [train.remote(policy, dataset, steps, lr, episodes)]
    for result in results:
        log_run(result)
        print(f"{result['job']}: {result['seconds'] / 60:.1f} min -> volume sortsense-runs/{result['job']}")
