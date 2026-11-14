"""Check a capture folder before anything trains on it (decisions.md D32: data quality first).

    python -m perception.audit --root data
Reads root/good and root/defective (the layout capture.py writes) and flags what would quietly hurt the
detector: unreadable or mixed-size images, frozen frames, clipped exposure, blur, lighting that drifts
over the session, and bricks with too few images. The audit flags and a person decides; the limits are
TUNE until real bricks exist. Exit code 1 if anything fails, so it can gate a training launch.
"""

import argparse
import statistics
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path

import cv2
import numpy as np

from perception.capture import brick_id

CLIPPED_FRACTION = 0.02  # TUNE: share of pixels at 0 or 255 that counts as clipped
BLUR_RATIO = 0.5  # TUNE: sharper-than-median fraction below which an image counts as blurred
DRIFT_RATIO = 0.10  # TUNE: last third vs first third mean brightness, as a share of the mean
MIN_PER_BRICK = 8  # TUNE: images per good brick (about 4 grasps x 2 frames) before it is a warning


@dataclass
class Report:
    images: int = 0
    fails: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.fails


def sharpness(gray: np.ndarray) -> float:
    return float(cv2.Laplacian(gray, cv2.CV_64F).var())


def audit_folder(folder: Path, report: Report, check_per_brick: bool) -> None:
    paths = sorted(folder.glob("*.png"), key=lambda p: (p.stat().st_mtime, p.name))
    sizes, gray_by_path = Counter(), {}
    for path in paths:
        image = cv2.imread(str(path))
        if image is None:
            report.fails.append(f"{path.name}: unreadable")
            continue
        sizes[image.shape[:2]] += 1
        gray_by_path[path] = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    report.images += len(gray_by_path)
    if len(sizes) > 1:
        report.fails.append(f"{folder.name}: mixed image sizes {dict(sizes)} (the crop changed during capture)")

    previous = None
    for path, gray in gray_by_path.items():
        if previous is not None and previous.shape == gray.shape and np.array_equal(previous, gray):
            report.fails.append(f"{path.name}: identical to the previous frame (camera frozen or saved twice)")
        previous = gray
        clipped = float(np.mean((gray == 0) | (gray == 255)))
        if clipped > CLIPPED_FRACTION:
            report.fails.append(f"{path.name}: {clipped:.0%} of pixels clipped (exposure)")

    if len(gray_by_path) >= 4:
        scores = {p: sharpness(g) for p, g in gray_by_path.items()}
        median = statistics.median(scores.values())
        report.warnings += [f"{p.name}: blurred (sharpness {s:.0f} vs median {median:.0f})" for p, s in scores.items() if s < BLUR_RATIO * median]
        means = [float(g.mean()) for g in gray_by_path.values()]
        third = len(means) // 3
        first, last = np.mean(means[:third]), np.mean(means[-third:])
        if third and abs(last - first) > DRIFT_RATIO * np.mean(means):
            report.warnings.append(f"{folder.name}: brightness drifted from {first:.0f} to {last:.0f} over the session (lighting changed)")

    if check_per_brick:
        per_brick = defaultdict(int)
        for path in gray_by_path:
            if brick_id(path) != path.stem:  # untagged images are their own brick
                per_brick[brick_id(path)] += 1
        if not per_brick and gray_by_path:
            report.warnings.append(f"{folder.name}: no image carries a brick id, so brick-level evaluation is impossible (capture with --brick N)")
        report.warnings += [f"{folder.name}/{b}: only {n} images (want at least {MIN_PER_BRICK})" for b, n in sorted(per_brick.items()) if n < MIN_PER_BRICK]


def audit(root: Path) -> Report:
    report = Report()
    for name in ("good", "defective"):
        folder = root / name
        if not folder.is_dir():
            report.fails.append(f"{name}/: folder missing")
            continue
        audit_folder(folder, report, check_per_brick=name == "good")
    if not report.images:
        report.fails.append("no readable images")
    return report


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=Path, default=Path("data"))
    args = ap.parse_args()
    report = audit(args.root)
    print(f"{report.images} images, {len(report.fails)} failures, {len(report.warnings)} warnings")
    for line in report.fails:
        print("FAIL", line)
    for line in report.warnings:
        print("warn", line)
    raise SystemExit(0 if report.ok else 1)


if __name__ == "__main__":
    main()
