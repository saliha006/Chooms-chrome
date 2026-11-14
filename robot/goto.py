"""Move the follower to a taught pose and hold it there, for the brick photos and for checking a pose.

    python -m robot.goto inspect --gripper 0   # brick in the jaws first; Enter sends the arm home and lets go

Moves at the robot.io speed cap. The arm goes limp at the end, so `home` must be a resting pose.
"""

import argparse
from pathlib import Path

import numpy as np
import yaml

from robot import io

CONFIG = Path(__file__).resolve().parents[1] / "config"


def pose(waypoints: Path, name: str) -> np.ndarray:
    value = (yaml.safe_load(waypoints.read_text()) or {}).get(name)
    if value is None:
        raise SystemExit(f"{waypoints}: '{name}' is not taught yet (python -m fallback.teach {name})")
    return np.asarray(value, float)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("name")
    ap.add_argument("--gripper", type=float, help="gripper target 0-100 (0 = closed on the brick); default: the taught value")
    ap.add_argument("--waypoints", type=Path, default=CONFIG / "waypoints.yaml")
    ap.add_argument("--calibration", default=str(CONFIG / "so101_follower.json"))
    ap.add_argument("--mock", action="store_true")
    args = ap.parse_args()
    target, home = pose(args.waypoints, args.name), pose(args.waypoints, "home")
    if args.gripper is not None:
        target[io.GRIPPER] = args.gripper
    io.connect(port=yaml.safe_load((CONFIG / "robot.yaml").read_text())["port"], calibration=args.calibration, mock=args.mock)
    try:
        reached = io.move_to(target, seconds=5.0)
        print(f"{args.name}: {'holding' if reached else 'stopped short (blocked or out of reach)'}", flush=True)
        input("Enter = go home and let go... ")
        io.move_to(home, seconds=5.0)
    finally:
        io.disconnect()


if __name__ == "__main__":
    main()
