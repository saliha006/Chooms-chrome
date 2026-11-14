"""Train an Anomalib model on a Folder dataset and print held-out metrics.

    python -m perception.train --root data --model padim
Folders under --root: good/ (train), defective/ (test), val_good/ (held-out good, test).
Anomalib's metrics here are a quick look; perception.evaluate gives the brick-level numbers we report.
"""

import argparse
from pathlib import Path

from anomalib.data import Folder
from anomalib.engine import Engine
from anomalib.models import AnomalyDINO, Padim, Patchcore
from anomalib.post_processing import PostProcessor

# EfficientAd was dropped (needs ImageNette, teacher weights, batch 1); AnomalyDINO is the conditional third arm (decisions.md D6).
MODELS = {"padim": Padim, "patchcore": Patchcore, "anomalydino": AnomalyDINO}


def build_model(name: str):
    """Raw, unclamped scores: the default post-processor clamps every good brick to 0.0, which leaves t_low meaningless."""
    return MODELS[name](post_processor=PostProcessor(enable_normalization=False))


def datamodule(root: Path, batch_size: int = 32) -> Folder:
    return Folder(
        name="bricks",
        root=root,
        normal_dir="good",
        abnormal_dir="defective",
        normal_test_dir="val_good",
        train_batch_size=batch_size,
        eval_batch_size=batch_size,
        val_split_mode="same_as_test",  # the default (from_test) silently moves half the test images into validation
        num_workers=0,  # worker processes hang on Windows spawn; the dataset is small
    )


def train(root: Path, model_name: str, out: Path) -> tuple[Path, dict]:
    """Fit, test, and return (checkpoint path, test metrics)."""
    model = build_model(model_name)
    dm = datamodule(root)
    engine = Engine(default_root_dir=out / model_name, logger=False)
    engine.fit(model=model, datamodule=dm)
    metrics = engine.test(model=model, datamodule=dm)[0]
    return Path(engine.trainer.checkpoint_callback.best_model_path), metrics


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=Path, default=Path("data"))
    ap.add_argument("--model", choices=sorted(MODELS), default="padim")
    ap.add_argument("--out", type=Path, default=Path("runs/perception"))
    args = ap.parse_args()
    ckpt, metrics = train(args.root, args.model, args.out)
    print(f"checkpoint: {ckpt}")
    for name, value in sorted(metrics.items()):
        print(f"{name}: {value:.4f}")


if __name__ == "__main__":
    main()
