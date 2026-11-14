"""Score the held-out folders, set the uncertainty band and plot it.

    python -m perception.calibrate --xml runs/export/padim/int8/weights/openvino/model.xml --root data
Writes perception/thresholds.yaml, bench/plots/score_hist.png and bench/plots/confusion.png.
Uses val_good/ (not the training good/) so the good-score spread isn't optimistic.
"""

import argparse
from pathlib import Path

import cv2
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from perception import thresholds
from perception.inspector import Scorer

PLOTS = Path("bench/plots")


def score_folder(scorer: Scorer, folder: Path) -> np.ndarray:
    paths = sorted(folder.glob("*.png"))
    if not paths:
        raise FileNotFoundError(f"no PNGs in {folder}")
    return np.array([scorer.score(cv2.imread(str(p)))[0] for p in paths])


def plot(good: np.ndarray, defective: np.ndarray, t_low: float, t_high: float, plots: Path) -> None:
    plots.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(6, 3.5))
    bins = np.linspace(min(good.min(), defective.min()), max(good.max(), defective.max()), 40)
    ax.hist(good, bins, alpha=0.7, label=f"good (n={len(good)})")
    ax.hist(defective, bins, alpha=0.7, label=f"defective (n={len(defective)})")
    ax.axvspan(t_low, t_high, color="grey", alpha=0.25, label="uncertain band")
    ax.set_xlabel("anomaly score")
    ax.legend()
    fig.tight_layout()
    fig.savefig(plots / "score_hist.png", dpi=120)
    plt.close(fig)

    table = thresholds.confusion(good, defective, t_low, t_high)
    grid = np.array([[table[t][label] for label in thresholds.LABELS] for t in ("good", "defective")])
    fig, ax = plt.subplots(figsize=(4.5, 2.6))
    ax.imshow(grid, cmap="Blues")
    ax.set_xticks(range(3), thresholds.LABELS)
    ax.set_yticks(range(2), ["good", "defective"])
    for (row, col), count in np.ndenumerate(grid):
        ax.text(col, row, str(count), ha="center", va="center")
    ax.set_xlabel("predicted")
    ax.set_ylabel("true")
    fig.tight_layout()
    fig.savefig(plots / "confusion.png", dpi=120)
    plt.close(fig)


def calibrate(xml: Path, root: Path, out: Path, plots: Path = PLOTS) -> tuple[float, float]:
    scorer = Scorer(xml, devices=("CPU",))  # calibration scores must not depend on which accelerator is free
    good, defective = score_folder(scorer, root / "val_good"), score_folder(scorer, root / "defective")
    t_low, t_high = thresholds.band(good, defective)
    thresholds.save(out, t_low, t_high, model_xml=str(xml), n_good=len(good), n_defective=len(defective))
    plot(good, defective, t_low, t_high, plots)
    return t_low, t_high


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--xml", type=Path, required=True)
    ap.add_argument("--root", type=Path, default=Path("data"))
    ap.add_argument("--out", type=Path, default=Path("perception/thresholds.yaml"))
    args = ap.parse_args()
    t_low, t_high = calibrate(args.xml, args.root, args.out)
    print(f"t_low={t_low:.4f} t_high={t_high:.4f} -> {args.out}")


if __name__ == "__main__":
    main()
