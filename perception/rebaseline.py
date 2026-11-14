"""Re-fit the detector to the current table and lighting: capture good bricks, retrain PaDiM, re-export, recalibrate.

    python -m perception.rebaseline --cam /dev/v4l/by-id/... --defective data/defective
Target: under 2 minutes on the Intel laptop (PRD §9). The 60 new good images are split 45 train / 15
held-out; the defective set is reused from the last full capture, so it may lag the new lighting.
"""

import argparse
import shutil
import time
from pathlib import Path

from perception.calibrate import calibrate
from perception.capture import capture, parse_box
from perception.export import export
from perception.train import train

N_GOOD = 60
N_HELD_OUT = 15


def stage(captured: Path, defective: Path, root: Path) -> None:
    """Lay out root/{good, val_good, defective} from a folder of freshly captured good images."""
    shots = sorted(captured.glob("*.png"))
    if len(shots) <= N_HELD_OUT:
        raise ValueError(f"need more than {N_HELD_OUT} good images in {captured}, found {len(shots)}")
    for name in ("good", "val_good", "defective"):
        shutil.rmtree(root / name, ignore_errors=True)
        (root / name).mkdir(parents=True)
    for i, shot in enumerate(shots):
        shutil.copy(shot, root / ("val_good" if i >= len(shots) - N_HELD_OUT else "good") / shot.name)
    for shot in defective.glob("*.png"):
        shutil.copy(shot, root / "defective" / shot.name)


def rebaseline(captured: Path, defective: Path, work: Path, thresholds_out: Path, precision: str = "int8") -> tuple[Path, dict[str, float]]:
    """Return (new IR path, seconds per stage)."""
    timings = {}
    start = time.perf_counter()
    root = work / "data"
    stage(captured, defective, root)
    ckpt, _ = train(root, "padim", work / "runs")
    timings["train_s"] = time.perf_counter() - start
    xml = export(ckpt, "padim", root, work / "export", precision)
    timings["export_s"] = time.perf_counter() - start - timings["train_s"]
    calibrate(xml, root, thresholds_out, plots=work / "plots")
    timings["total_s"] = time.perf_counter() - start
    return xml, timings


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cam", default="0")
    ap.add_argument("--crop", help="x,y,side; must match the crop used for the defective set")
    ap.add_argument("--defective", type=Path, default=Path("data/defective"))
    ap.add_argument("--work", type=Path, default=Path("runs/rebaseline"))
    ap.add_argument("--thresholds", type=Path, default=Path("perception/thresholds.yaml"))
    ap.add_argument("--precision", choices=("fp16", "int8"), default="int8")
    args = ap.parse_args()
    captured = args.work / "captured"
    shutil.rmtree(captured, ignore_errors=True)
    t0 = time.perf_counter()
    capture(captured, N_GOOD, args.cam, parse_box(args.crop), interval_s=0.3)
    capture_s = time.perf_counter() - t0
    xml, timings = rebaseline(captured, args.defective, args.work, args.thresholds, args.precision)
    print(f"capture {capture_s:.0f}s · train {timings['train_s']:.0f}s · export {timings['export_s']:.0f}s · "
          f"total {capture_s + timings['total_s']:.0f}s -> {xml}")


if __name__ == "__main__":
    main()
