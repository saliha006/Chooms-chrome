"""Read the follower's joints with its motors loose, for the gripper readings (N8) and pose checks. Never moves it.

    python -m robot.readings --seconds 40 --window 8   # median of every joint per 8 s window, in normalized units

Close any Studio page that uses the follower first: one program per serial port.
"""

import argparse
import time
from pathlib import Path

import numpy as np
import yaml

from robot import io

CONFIG = Path(__file__).resolve().parents[1] / "config"


def window_medians(stamps: np.ndarray, samples: np.ndarray, window_s: float) -> list[tuple[float, np.ndarray]]:
    """(window start in s, median joints) for each window_s slice of a recording."""
    elapsed = stamps - stamps[0]
    starts = np.arange(0.0, elapsed[-1] + 1e-9, window_s)
    return [(start, np.median(samples[(elapsed >= start) & (elapsed < start + window_s)], axis=0))
            for start in starts if np.any((elapsed >= start) & (elapsed < start + window_s))]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--seconds", type=float, default=40.0)
    ap.add_argument("--window", type=float, default=8.0)
    ap.add_argument("--calibration", default=str(CONFIG / "so101_follower.json"))
    ap.add_argument("--mock", action="store_true")
    args = ap.parse_args()
    io.connect(port=yaml.safe_load((CONFIG / "robot.yaml").read_text())["port"], calibration=args.calibration, mock=args.mock)
    try:
        io.torque_off()
        print(f"motors loose; recording {args.seconds:.0f} s", flush=True)
        stamps, samples = [], []
        end = time.monotonic() + args.seconds
        while time.monotonic() < end:
            samples.append(io.observe())
            stamps.append(time.monotonic())
            time.sleep(1 / io.CONTROL_HZ)
    finally:
        io.disconnect()
    print("window  " + "  ".join(f"{name[:11]:>11}" for name in io.JOINTS))
    for start, median in window_medians(np.array(stamps), np.array(samples), args.window):
        print(f"{start:5.1f}s  " + "  ".join(f"{v:11.1f}" for v in median))


if __name__ == "__main__":
    main()
