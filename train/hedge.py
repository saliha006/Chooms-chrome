"""The colour hedge (D23, N5): which episodes of the SmolVLA dataset belong to each fixed string.

    python -m train.hedge path/to/dataset --repo-id user/sortsense-smolvla

Prints one Modal command per task string, so each single-colour ACT place policy trains only on its own
episodes. Launch them in parallel with SmolVLA and evaluate them at the SmolVLA gate only if SmolVLA is below 6/10.
"""

import argparse
import sys
from pathlib import Path

import pandas as pd


COLOURS = ("purple", "orange")


def episodes_by_task(root: Path) -> dict[str, list[int]]:
    data = pd.concat([pd.read_parquet(p, columns=["episode_index", "task_index"]) for p in sorted((root / "data").rglob("*.parquet"))])
    names = pd.read_parquet(root / "meta" / "tasks.parquet")["task_index"]
    found = {}
    for task, index in names.items():
        ids = sorted(int(i) for i in data.loc[data["task_index"] == index, "episode_index"].unique())
        if ids:
            found[str(task)] = ids
    return found


def tag_for(task: str) -> str:
    for colour in COLOURS:
        if colour in task:
            return colour
    raise ValueError(f"no bowl colour in the task string {task!r}")


def modal_commands(repo_id: str, per_task: dict[str, list[int]], steps: int) -> list[str]:
    return [f"modal run train/modal_train.py --dataset {repo_id} --policy act --steps {steps} --tag {tag_for(task)} "
            f"--episode-ids {','.join(map(str, ids))}" for task, ids in per_task.items()]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("root", type=Path)
    ap.add_argument("--repo-id", required=True, help="the dataset's Hugging Face id, as Modal pulls it")
    ap.add_argument("--steps", type=int, required=True, help="the same count as the SmolVLA run")
    args = ap.parse_args()
    per_task = episodes_by_task(args.root)
    if len(per_task) != 2:
        sys.exit(f"expected the two fixed strings, found {len(per_task)} task strings: {sorted(per_task)}")
    for line in modal_commands(args.repo_id, per_task, args.steps):
        print(line)


if __name__ == "__main__":
    main()
