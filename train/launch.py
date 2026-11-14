"""Start training on the deployed Modal app, so a job keeps running when this laptop drops off the network.

    modal deploy train/modal_train.py                  # once, and again after any change to train/
    python -m train.launch --dataset <hf_id> --policy act --steps 20000
    python -m train.launch --dataset <hf_id> --steps 20000 --sweep
    python -m train.launch --dataset <hf_id> --policy smolvla --steps 10000 --cameras top,wrist,inspect
    python -m train.launch --collect                   # log finished jobs to train/runs.md; run it any time

Job IDs wait in runs/modal_jobs.json (git-ignored) until --collect sees them finish; Modal keeps results for 7 days.
"""

import argparse
import json
from pathlib import Path

import modal
from modal.exception import OutputExpiredError
from modal.exception import TimeoutError as NotFinished

from train import commands
from train.modal_train import APP_NAME, log_run, plan

JOBS = Path(__file__).resolve().parents[1] / "runs" / "modal_jobs.json"


def _load() -> list[dict]:
    return json.loads(JOBS.read_text()) if JOBS.exists() else []


def _save(jobs: list[dict]) -> None:
    JOBS.parent.mkdir(exist_ok=True)
    JOBS.write_text(json.dumps(jobs, indent=1))


def start(dataset: str, policy: str, steps: int, lr: float | None, episodes: int, sweep: bool, sweep_sizes: str,
          cameras: str) -> list[dict]:
    policy, jobs, camera_order = plan(policy, steps, episodes, sweep, sweep_sizes, cameras)
    train = modal.Function.from_name(APP_NAME, f"train_{policy}")
    extra = (camera_order,) if policy == "smolvla" else ()
    started = [{"call_id": train.spawn(dataset, steps, lr, n, job, *extra).object_id, "job": job, "policy": policy,
                "dataset": dataset, "episodes": n, "steps": steps} for n, job in jobs]
    _save(_load() + started)
    return started


def collect() -> None:
    running = []
    for job in _load():
        try:
            seconds = modal.FunctionCall.from_id(job["call_id"]).get(timeout=0)
        except OutputExpiredError:  # a subclass of Modal's TimeoutError, so it is caught first
            print(f"{job['job']}: result expired (Modal keeps 7 days); see the Modal dashboard")
        except (TimeoutError, NotFinished):  # get(timeout=0) on a running job raises the built-in one (Modal 1.6.4)
            running.append(job)
            print(f"{job['job']}: still running")
        except Exception as e:  # the job itself failed; report it and keep collecting the others
            print(f"{job['job']}: FAILED: {type(e).__name__}: {e}")
        else:
            log_run(job["job"], job["policy"], job["dataset"], job["episodes"], job["steps"], seconds)
            print(f"{job['job']}: {seconds / 60:.1f} min -> volume sortsense-runs/{job['job']}")
    _save(running)


def main() -> None:
    ap = argparse.ArgumentParser(description="Start training on the deployed Modal app, or collect finished jobs.")
    ap.add_argument("--collect", action="store_true", help="log finished jobs to train/runs.md")
    ap.add_argument("--dataset")
    ap.add_argument("--policy", default="act")
    ap.add_argument("--steps", type=int, default=200)
    ap.add_argument("--lr", type=float)
    ap.add_argument("--episodes", type=int, default=0)
    ap.add_argument("--sweep", action="store_true")
    ap.add_argument("--sweep-sizes", default=",".join(map(str, commands.SWEEP_EPISODES)))
    ap.add_argument("--cameras", default="", help="SmolVLA only: dataset cameras in camera1, camera2, camera3 order")
    args = ap.parse_args()
    if args.collect:
        collect()
        return
    if not args.dataset:
        ap.error("--dataset is required to start a job")
    for job in start(args.dataset, args.policy, args.steps, args.lr, args.episodes, args.sweep, args.sweep_sizes, args.cameras):
        print(f"{job['job']}: started ({job['call_id']}); check later with `python -m train.launch --collect`")


if __name__ == "__main__":
    main()
