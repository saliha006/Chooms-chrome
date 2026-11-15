"""Detector photos at the station in one command per brick: the arm carries the held brick to the inspect pose,
the inspection camera (config/models.yaml inspector.camera) takes the photos, then the arm goes home and opens.

    python -m perception.shoot good 3          # brick 3 is good: 12 photos into data/good/b03_*.png
    python -m perception.shoot defective 14    # into data/defective/
    python -m perception.shoot --lock          # once, brick held: fix exposure and white balance at the inspect pose

Each run opens the jaws for INSERT_S to swap bricks, closes, photographs, and comes home still holding.
Studio must not be holding the follower or the camera.
"""

import argparse
import subprocess
import time
from pathlib import Path

import cv2
import numpy as np
import yaml

from perception.capture import capture, open_camera, square_crop
from robot import io

CONFIG = Path(__file__).resolve().parents[1] / "config"
TARGET_BRIGHTNESS = 125  # mean grey level of the crop the detector sees
INSERT_S = 4.0  # time to swap the brick while the jaws are open
CARRY_STEP_DEG = 4.0  # gentler than the runtime cap while carrying: a brick held at the jaw tips slips out
EMPTY_JAWS = Path("runs/empty_jaws.png")  # a photo of the closed, empty gripper at the inspect pose
EMPTY_DIFF = 18.0  # TUNE: mean grey difference below this = the photos show no brick


def camera() -> dict:
    role = yaml.safe_load((CONFIG / "models.yaml").read_text())["inspector"].get("camera", "inspect")
    return yaml.safe_load((CONFIG / "cameras.yaml").read_text())[role]


def crop() -> tuple[int, int, int] | None:
    box = yaml.safe_load((CONFIG / "models.yaml").read_text())["inspector"].get("crop")
    return tuple(box) if box else None


def lock_exposure(cam: dict, box) -> int:
    """Fixed 30 ms exposure (longer drops the camera below the 30 fps the policies record at) and white balance,
    then gain chosen by bisection so the crop's mean brightness is near TARGET_BRIGHTNESS."""
    def v4l2(**controls):
        subprocess.run(["v4l2-ctl", "-d", cam["path"], "--set-ctrl", ",".join(f"{k}={v}" for k, v in controls.items())], check=True)
    v4l2(white_balance_automatic=0, white_balance_temperature=4600, auto_exposure=1, exposure_dynamic_framerate=0,
         exposure_time_absolute=300)
    low, high = 0, 100
    for _ in range(7):
        gain = (low + high) // 2
        v4l2(gain=gain)
        cap = open_camera(cam["path"], cam.get("fourcc"))
        frames = [cap.read()[1] for _ in range(8)]
        cap.release()
        brightness = float(square_crop(frames[-1], box).mean())
        low, high = (gain, high) if brightness < TARGET_BRIGHTNESS else (low, gain)
    print(f"locked: exposure 30 ms, gain {gain} (crop brightness {brightness:.0f}), white balance 4600 K")
    return gain


def looks_empty(photo: Path) -> bool:
    """True when the photo matches the empty-gripper reference: the brick fell out on the way up."""
    if not EMPTY_JAWS.exists():
        return False
    a = cv2.cvtColor(cv2.imread(str(photo)), cv2.COLOR_BGR2GRAY).astype(float)
    b = cv2.cvtColor(cv2.imread(str(EMPTY_JAWS)), cv2.COLOR_BGR2GRAY).astype(float)
    return float(np.abs(a - b).mean()) < EMPTY_DIFF


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("kind", nargs="?", choices=("good", "defective"))
    ap.add_argument("brick", nargs="?", type=int)
    ap.add_argument("--n", type=int, default=6)
    ap.add_argument("--lock", action="store_true")
    ap.add_argument("--root", type=Path, default=Path("data"))
    args = ap.parse_args()
    if not args.lock and (args.kind is None or args.brick is None):
        ap.error("say which: good|defective and the brick number, or --lock")
    wp = yaml.safe_load((CONFIG / "waypoints.yaml").read_text())
    robot = yaml.safe_load((CONFIG / "robot.yaml").read_text())
    cam, box = camera(), crop()
    io.connect(port=robot["port"], calibration=robot["calibration"])
    try:
        hand = io.observe()
        hand[io.GRIPPER] = io.GRIPPER_OPEN
        io.move_to(hand, seconds=1.5)  # opens: take the last brick out, put this one between the jaws
        print(f"jaws open: put the brick in now, {INSERT_S:.0f} s", flush=True)
        time.sleep(INSERT_S)
        hand[io.GRIPPER] = 0.0  # closes on the brick (a Duplo held at the tips reads ~2, deeper in ~17)
        io.move_to(hand, seconds=1.5)
        time.sleep(1.0)  # grip settles before lifting
        io.MAX_STEP_DEG = CARRY_STEP_DEG
        held = np.asarray(wp["inspect"], float)
        held[io.GRIPPER] = 0.0
        io.move_to(held, seconds=5.0)
        time.sleep(0.5)  # let the brick stop swinging
        if args.lock:
            lock_exposure(cam, box)
        else:
            saved = capture(args.root / args.kind, args.n, cam["path"], box, interval_s=0.12, brick=args.brick, fourcc=cam.get("fourcc"))
            if looks_empty(saved[0]):
                for path in saved:
                    path.unlink()
                print(f"NO BRICK in the jaws: the {len(saved)} photos were deleted. Redo brick {args.brick} (push it deeper in).")
            else:
                print(f"{len(saved)} photos of {args.kind} brick {args.brick} -> {args.root / args.kind}")
        home = np.asarray(wp["home"], float)
        home[io.GRIPPER] = 0.0  # keeps holding the brick; the next run opens first
        io.move_to(home, seconds=5.0)
    finally:
        io.disconnect()


if __name__ == "__main__":
    main()
