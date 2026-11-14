"""Train an Anomalib model on a Folder dataset and print held-out metrics.

    python -m perception.train --root data --model padim
Folders under --root: good/ (train), defective/ (test), val_good/ (held-out good, test).
"""

import argparse
from pathlib import Path

from anomalib.data import Folder
from anomalib.engine import Engine
from anomalib.models import EfficientAd, Padim, Patchcore

MODELS = {"padim": Padim, "patchcore": Patchcore, "efficientad": EfficientAd}


def datamodule(root: Path, model_name: str, batch_size: int = 32) -> Folder:
    return Folder(
        name="bricks",
        root=root,
        normal_dir="good",
        abnormal_dir="defective",
        normal_test_dir="val_good",
        train_batch_size=1 if model_name == "efficientad" else batch_size,  # EfficientAd only trains with batch 1
        eval_batch_size=batch_size,
        num_workers=0,  # worker processes hang on Windows spawn; the dataset is small
    )


def train(root: Path, model_name: str, out: Path) -> tuple[Path, dict]:
    """Fit, test, and return (checkpoint path, test metrics)."""
    model = MODELS[model_name]()
    dm = datamodule(root, model_name)
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
