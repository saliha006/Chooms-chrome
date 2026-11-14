"""Write a recorded dataset's Hugging Face card (its README.md) from the dataset itself and a fresh audit.

    python -m train.card <dataset folder> --kind pick      # ACT: pick and present
    python -m train.card <dataset folder> --kind place     # SmolVLA: place by instruction

Every number comes from the folder (meta/info.json, meta/tasks.parquet), train/rejected.md and `train.audit`; a dataset
that fails the audit gets no card. Publishing is public, so it stays a separate step you run yourself:
    huggingface-cli upload <hf_user>/sortsense-<kind> <dataset folder>/README.md README.md --repo-type dataset
"""

import argparse
import json
from datetime import date
from pathlib import Path

import pandas as pd
import yaml

from train.audit import audit

REPO = Path(__file__).resolve().parents[1]
REJECTED = REPO / "train" / "rejected.md"
CAMERAS = {"top": "RealSense D415 colour stream, looking down on the start zone and both bowls",
           "inspect": "webcam at the inspection mark", "wrist": "camera on the gripper"}
ABOUT = {
    "pick": ("Pick and present: from home, pick one Duplo brick at a taped start dot and hold it still at the inspection pose "
             "for about 1 s. 9 start positions on a 3 × 3 grid, recorded in rounds (one episode per position per round, the "
             "same order every round), so the first 18 / 36 / 54 episodes hold 2 / 4 / 6 per position. Off-grid test spots "
             "are never recorded.",
             "ACT, trained with Intel's Physical AI Studio on Modal and exported to OpenVINO; the demo-count sweep trains on "
             "the first 18, 36 and 54 episodes in parallel."),
    "place": ("Place by instruction: from the inspection pose, put the held brick in the bowl the task string names. The "
              "string carries the inspector's verdict, and the two strings alternate so neither bowl dominates.",
              "SmolVLA, fine-tuned from `lerobot/smolvla_base` with LeRobot on Modal and exported to OpenVINO."),
}


def rejected_count(name: str, log: Path = REJECTED) -> int:
    rows = [line.split("|") for line in log.read_text(encoding="utf-8").splitlines() if line.startswith("| 20")]
    return sum(1 for row in rows if row[2].strip(" `").endswith(name))


def card(root: Path, kind: str, licence: str = "apache-2.0", rejected_log: Path = REJECTED) -> str:
    """The card's markdown. Raises SystemExit with the audit's failures if the dataset does not pass."""
    tasks = None
    if kind == "place":
        rules = yaml.safe_load((REPO / "config" / "rules.yaml").read_text())
        tasks = [rules["perfect"], rules["defective"]]
    report = audit(root, kind, list(CAMERAS), tasks)
    if not report.ok:
        raise SystemExit("audit failed, no card written:\n" + "\n".join(f"FAIL {line}" for line in report.fails))

    info = json.loads((root / "meta" / "info.json").read_text())
    names = info["features"]["observation.state"].get("names")
    joints = f" ({', '.join(names)})" if names else ""
    found = sorted(pd.read_parquet(root / "meta" / "tasks.parquet").index.astype(str))
    frames = f"{info['total_frames']} at {info['fps']} Hz" if "total_frames" in info else f"{info['fps']} Hz"
    about, trains = ABOUT[kind]
    return "\n".join([
        "---", f"license: {licence}", "task_categories:", "- robotics",
        "tags:", "- LeRobot", "- so101", "- sortsense", "- junction-2026", "---", "",
        f"# SortSense: {kind}", "", about, "",
        "| | |", "|---|---|",
        f"| Robot | SO-101 follower ({info.get('robot_type', 'so101_follower')}), teleoperated with the SO-101 leader arm |",
        f"| Episodes | {report.episodes} kept; {rejected_count(root.name, rejected_log)} rejected on the spot and re-taken |",
        f"| Frames | {frames} |",
        "| Cameras | " + "; ".join(f"`{name}`: {what}" for name, what in CAMERAS.items()) + " |",
        f"| State and action | joint positions{joints}: arm joints normalized to -100..100 over each calibrated range, gripper on LeRobot's 0-100 scale |",
        "| Task strings | " + "; ".join(f"`{t}`" for t in found) + " |",
        f"| Audit | `python -m train.audit` passed on {date.today()}, {len(report.warnings)} warnings |", "",
        "Rejected on the spot: a dropped brick, a collision, a long hesitation, a wrong bowl, the brick out of the "
        "inspection camera's view, or a hand in a camera frame.", "",
        f"**Trains:** {trains}", "",
        "Part of SortSense (Junction 2026, Intel x Ignite Next: Physical AI): https://github.com/saliha006/Chooms-chrome", "",
    ])


def main() -> None:
    ap = argparse.ArgumentParser(description="Write a recorded dataset's Hugging Face card from its own metadata.")
    ap.add_argument("root", type=Path)
    ap.add_argument("--kind", choices=list(ABOUT), required=True)
    ap.add_argument("--licence", default="apache-2.0")
    args = ap.parse_args()
    (args.root / "README.md").write_text(card(args.root, args.kind, args.licence), encoding="utf-8")
    print(f"wrote {args.root / 'README.md'}")


if __name__ == "__main__":
    main()
