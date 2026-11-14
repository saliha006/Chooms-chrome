"""Brick-level detector evaluation and thresholds (decisions.md D5-D7, PRD v2.5).

    python -m perception.evaluate --root data --model padim

root/good (and root/val_good if present): every good image, named b<brick>_<n>.png (perception.capture --brick).
root/defective: defective images, same naming.

- Good bricks are split into k folds; each fold is scored by a model trained without it, so every good score is
  out-of-fold. t_low = 99th percentile of those scores.
- Defective bricks are split in half by brick: the dev half sets t_high (5th percentile), the test half only reports.
- The region threshold is the 99th percentile of out-of-fold good images' maximum anomaly-map pixel.
- AUROC gets a bootstrap-by-brick 95% interval; false alarms an exact (Clopper-Pearson) one-sided upper bound;
  recall at t_high an exact two-sided interval. A brick, not an image, is the independent unit.
Writes the thresholds YAML the inspector reads and a markdown report. Prints the final model's checkpoint for export.
"""

import argparse
import shutil
from collections import defaultdict
from pathlib import Path

import numpy as np
from anomalib.data import Folder
from anomalib.engine import Engine
from scipy.stats import beta
from sklearn.metrics import roc_auc_score

from perception import thresholds
from perception.capture import brick_id
from perception.train import MODELS, build_model

FOLDS = 5
BOOTSTRAP = 1000
GOOD_QUANTILE = 99  # t_low and the pixel threshold
DEFECT_QUANTILE = 5  # t_high


def group_by_brick(paths: list[Path]) -> dict[str, list[Path]]:
    groups = defaultdict(list)
    for p in sorted(paths):
        groups[brick_id(p)].append(p)
    return dict(groups)


def split_bricks(bricks: list[str], parts: int, seed: int = 0) -> list[list[str]]:
    order = np.random.default_rng(seed).permutation(sorted(bricks))
    return [list(order[i::parts]) for i in range(parts)]


def _stage(files: dict[str, list[Path]], root: Path) -> None:
    for folder, paths in files.items():
        (root / folder).mkdir(parents=True)
        for p in paths:
            shutil.copy(p, root / folder / p.name)


def fit_and_score(model_name: str, train: list[Path], score: list[Path], defective_dev: list[Path], work: Path) -> tuple[dict[Path, float], dict[Path, float], Path]:
    """Train on `train` (good only), return (score per image, max map pixel per image, checkpoint) for `score`."""
    _stage({"train": train, "score": score, "defective": defective_dev}, work / "data")
    dm = Folder(name="eval", root=work / "data", normal_dir="train", normal_test_dir="score", abnormal_dir="defective",
                train_batch_size=32, eval_batch_size=32, num_workers=0, val_split_mode="same_as_test")
    engine = Engine(default_root_dir=work / "runs", logger=False)
    model = build_model(model_name)
    engine.fit(model=model, datamodule=dm)
    scores, peaks = {}, {}
    by_name = {p.name: p for p in score}
    for batch in engine.predict(model=model, data_path=work / "data" / "score"):
        for path, s, amap in zip(batch.image_path, batch.pred_score, batch.anomaly_map, strict=True):
            original = by_name[Path(path).name]
            scores[original] = float(s)
            peaks[original] = float(amap.max())
    return scores, peaks, Path(engine.trainer.checkpoint_callback.best_model_path)


def brick_bootstrap_auroc(good: dict[str, list[float]], bad: dict[str, list[float]], n: int = BOOTSTRAP, seed: int = 0) -> tuple[float, float]:
    rng = np.random.default_rng(seed)
    good_keys, bad_keys = list(good), list(bad)
    values = []
    for _ in range(n):
        g = [s for k in rng.choice(good_keys, len(good_keys)) for s in good[k]]
        b = [s for k in rng.choice(bad_keys, len(bad_keys)) for s in bad[k]]
        values.append(roc_auc_score([0] * len(g) + [1] * len(b), g + b))
    return float(np.percentile(values, 2.5)), float(np.percentile(values, 97.5))


def upper_bound(k: int, n: int, confidence: float = 0.95) -> float:
    """Exact one-sided upper bound on a rate seen k times in n."""
    return 1.0 if k >= n else float(beta.ppf(confidence, k + 1, n - k))


def interval(k: int, n: int, confidence: float = 0.95) -> tuple[float, float]:
    tail = (1 - confidence) / 2
    low = 0.0 if k == 0 else float(beta.ppf(tail, k, n - k + 1))
    high = 1.0 if k == n else float(beta.ppf(1 - tail, k + 1, n - k))
    return low, high


def evaluate(root: Path, model_name: str, out_yaml: Path, report: Path, work: Path) -> dict:
    good = group_by_brick([*root.glob("good/*.png"), *root.glob("val_good/*.png")])
    bad = group_by_brick(list(root.glob("defective/*.png")))
    if len(good) < 2 or not bad:
        raise ValueError(f"need >= 2 good bricks and >= 1 defective brick under {root}, found {len(good)} and {len(bad)}")
    dev_ids, test_ids = split_bricks(list(bad), 2) if len(bad) > 1 else (list(bad), list(bad))
    dev = [p for b in dev_ids for p in bad[b]]
    test = [p for b in test_ids for p in bad[b]]

    oof_scores, oof_peaks = {}, {}
    for i, fold in enumerate(split_bricks(list(good), min(FOLDS, len(good)))):
        held = [p for b in fold for p in good[b]]
        rest = [p for b, ps in good.items() if b not in fold for p in ps]
        s, peaks, _ = fit_and_score(model_name, rest, held, dev, work / f"fold{i}")
        oof_scores |= s
        oof_peaks |= peaks
        shutil.rmtree(work / f"fold{i}", ignore_errors=True)  # fold models are throwaway; only the final one is exported
    final_scores, _, ckpt = fit_and_score(model_name, [p for ps in good.values() for p in ps], dev + test, dev, work / "final")

    good_scores = np.array(list(oof_scores.values()))
    t_low = float(np.percentile(good_scores, GOOD_QUANTILE))
    t_high = float(np.percentile([final_scores[p] for p in dev], DEFECT_QUANTILE))
    t_low, t_high = min(t_low, t_high), max(t_low, t_high)
    pixel = float(np.percentile(list(oof_peaks.values()), GOOD_QUANTILE))

    test_scores = [final_scores[p] for p in test]
    good_by_brick = {b: [oof_scores[p] for p in ps] for b, ps in good.items()}
    test_by_brick = {b: [final_scores[p] for p in bad[b]] for b in test_ids}
    auroc = float(roc_auc_score([0] * len(good_scores) + [1] * len(test_scores), [*good_scores, *test_scores]))
    auroc_ci = brick_bootstrap_auroc(good_by_brick, test_by_brick)
    false_alarms = int((good_scores > t_high).sum())
    good_uncertain = int(((good_scores >= t_low) & (good_scores <= t_high)).sum())
    caught = sum(s > t_high for s in test_scores)
    test_uncertain = sum(t_low <= s <= t_high for s in test_scores)

    result = {
        "model": model_name, "ckpt": str(ckpt), "t_low": t_low, "t_high": t_high, "pixel_threshold": pixel,
        "good_images": len(good_scores), "good_bricks": len(good), "defective_dev_bricks": len(dev_ids), "defective_test_bricks": len(test_ids),
        "auroc": auroc, "auroc_ci95": list(auroc_ci),
        "false_alarm": f"{false_alarms}/{len(good_scores)}", "false_alarm_upper95": upper_bound(false_alarms, len(good_scores)),
        "good_uncertain": f"{good_uncertain}/{len(good_scores)}",
        "recall": f"{caught}/{len(test_scores)}", "recall_ci95": list(interval(caught, len(test_scores))),
        "defective_uncertain": f"{test_uncertain}/{len(test_scores)}",
    }
    thresholds.save(out_yaml, t_low, t_high, pixel_threshold=pixel, model=model_name, ckpt=str(ckpt),
                    good_images=len(good_scores), defective_dev_images=len(dev))
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(to_markdown(result), encoding="utf-8")
    return result


def to_markdown(r: dict) -> str:
    lo, hi = r["auroc_ci95"]
    rlo, rhi = r["recall_ci95"]
    return (
        f"# Detector evaluation ({r['model']})\n\n"
        f"Brick-level: {r['good_bricks']} good bricks ({r['good_images']} images, out-of-fold), "
        f"{r['defective_dev_bricks']} defective bricks set t_high, {r['defective_test_bricks']} defective bricks only report.\n\n"
        f"| Metric | Value |\n|---|---|\n"
        f"| AUROC (test defectives vs out-of-fold good) | {r['auroc']:.3f} (95% interval by brick {lo:.3f}–{hi:.3f}) |\n"
        f"| False alarms (good scored defective) | {r['false_alarm']}, at most {r['false_alarm_upper95']:.1%} at 95% confidence |\n"
        f"| Good bricks sent to a second look | {r['good_uncertain']} |\n"
        f"| Recall at t_high (test defectives) | {r['recall']} (95% interval {rlo:.0%}–{rhi:.0%}) |\n"
        f"| Defectives sent to a second look | {r['defective_uncertain']} |\n"
        f"| t_low / t_high / pixel threshold | {r['t_low']:.2f} / {r['t_high']:.2f} / {r['pixel_threshold']:.2f} |\n"
    )


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=Path, default=Path("data"))
    ap.add_argument("--model", choices=sorted(MODELS), default="padim")
    ap.add_argument("--out", type=Path, default=Path("perception/thresholds.yaml"))
    ap.add_argument("--report", type=Path, default=Path("bench/detector_report.md"))
    ap.add_argument("--work", type=Path, default=Path("runs/evaluate"), help="the final model's checkpoint stays here")
    args = ap.parse_args()
    work = args.work / args.model
    shutil.rmtree(work, ignore_errors=True)
    result = evaluate(args.root, args.model, args.out, args.report, work)
    print(to_markdown(result))
    print(f"export this checkpoint: python -m perception.export --model {args.model} --ckpt {result['ckpt']} --root {args.root}")


if __name__ == "__main__":
    main()
