"""Score the saved real-brick photos through the deployed detector path (perception.inspector.Inspector).

    python -m bench.real_photos --cases runs/evaluate/real_cases.csv

The saved photos are already the 256x256 wrist crop, so the Inspector gets crop=(0, 0, 256) (the whole photo) in place
of the wrist-camera crop in config/models.yaml. CPU only, so it never competes with a running station for the NPU.
The deployed model was fitted on the good photos, so their scores here are in-sample: they show the wiring works, not
how a new good brick scores (that is runs/evaluate/patchcore/report.md, out-of-fold).
--cases writes the rows `python -m reasoner.evaluate` reads, image paths relative to --data.
"""

import argparse
import csv
import tempfile
from pathlib import Path

import cv2
import numpy as np

from perception.inspector import Inspector

XML = Path("runs/detector/ov/patchcore/model.xml")
THRESHOLDS = Path("perception/thresholds.yaml")
DATA = Path("data")
WHOLE_PHOTO = (0, 0, 256)


def score_photos(data: Path, xml: Path, thresholds: Path) -> list[dict]:
    """One row per photo in data/good and data/defective: truth, label, score, the band and the blob."""
    rows = []
    with tempfile.TemporaryDirectory() as heatmaps:
        inspector = Inspector(xml, thresholds, "patchcore", heatmap_dir=Path(heatmaps), crop=WHOLE_PHOTO, devices=("CPU",))
        for truth in ("good", "defective"):
            for path in sorted((data / truth).glob("*.png")):
                signal = inspector.inspect(cv2.imread(str(path)), "inspect", len(rows))
                rows.append({"image": f"{truth}/{path.name}", "truth": truth, "label": signal.label, "score": signal.score,
                             "t_low": signal.t_low, "t_high": signal.t_high,
                             "bbox": " ".join(map(str, signal.bbox)) if signal.bbox else ""})
    return rows


def summary(rows: list[dict]) -> str:
    t_low, t_high = rows[0]["t_low"], rows[0]["t_high"]
    lines = [f"t_low {t_low:.2f}, t_high {t_high:.2f}", "",
             "| truth | n | min | median | max | perfect | uncertain | defective |", "|---|---|---|---|---|---|---|---|"]
    for truth in ("good", "defective"):
        group = [r for r in rows if r["truth"] == truth]
        if not group:
            continue
        s = np.array([r["score"] for r in group])
        counts = [sum(r["label"] == label for r in group) for label in ("perfect", "uncertain", "defective")]
        lines.append(f"| {truth} | {len(group)} | {s.min():.2f} | {np.median(s):.2f} | {s.max():.2f} | "
                     + " | ".join(map(str, counts)) + " |")
    return "\n".join(lines)


def write_cases(rows: list[dict], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["image", "label", "score", "t_low", "t_high", "bbox"], extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", type=Path, default=DATA)
    ap.add_argument("--xml", type=Path, default=XML)
    ap.add_argument("--thresholds", type=Path, default=THRESHOLDS)
    ap.add_argument("--cases", type=Path, help="also write a cases.csv for reasoner.evaluate")
    args = ap.parse_args()
    rows = score_photos(args.data, args.xml, args.thresholds)
    print(summary(rows))
    if args.cases:
        write_cases(rows, args.cases)


if __name__ == "__main__":
    main()
