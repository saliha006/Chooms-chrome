"""Teach waypoints by hand-guiding the follower arm (Saturday 09:30).

    python -m fallback.teach home pick_above pick pick_drop inspect bowl_red bowl_blue
    python -m fallback.teach inspect --port /dev/ttyACM0 --calibration config/so101_follower.json

Torque goes off so the arm can be moved by hand: hold it before pressing Enter. Each pose is written
into config/waypoints.yaml in place, keeping the file's comments.
"""

import argparse
import re
from pathlib import Path

import yaml

from fallback.scripted import POSES
from robot import io

CONFIG = Path(__file__).resolve().parents[1] / "config"


def save_pose(path: Path, name: str, joints) -> None:
    values = "[" + ", ".join(f"{v:.1f}" for v in joints) + "]"
    text = path.read_text(encoding="utf-8")
    text, count = re.subn(rf"^{name}:[^#\n]*", f"{name}: {values}   ", text, count=1, flags=re.M)
    if count == 0:
        text += f"{name}: {values}\n"
    path.write_text(text, encoding="utf-8")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("names", nargs="+", choices=POSES, metavar="pose", help=f"any of: {', '.join(POSES)}")
    ap.add_argument("--port", help="follower serial port (default: config/robot.yaml)")
    ap.add_argument("--calibration", default=str(CONFIG / "so101_follower.json"))
    ap.add_argument("--mock", action="store_true", help="MockRobot, to try the flow without the arm")
    ap.add_argument("--file", type=Path, default=CONFIG / "waypoints.yaml")
    args = ap.parse_args()

    port = args.port or yaml.safe_load((CONFIG / "robot.yaml").read_text())["port"]
    if not args.mock and port is None:
        ap.error("set port in config/robot.yaml or pass --port")
    io.connect(port=port, calibration=args.calibration, mock=args.mock)
    try:
        input("Torque goes OFF next and the arm will go limp. Hold the arm, then press Enter... ")
        io.torque_off()
        for name in args.names:
            input(f"Guide the arm to '{name}' and press Enter to save it... ")
            joints = io.observe()
            save_pose(args.file, name, joints)
            print(f"  saved {name}: {[round(v, 1) for v in joints]}")
    finally:
        io.disconnect()


if __name__ == "__main__":
    main()
