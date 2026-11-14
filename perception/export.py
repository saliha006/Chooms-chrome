"""Export a trained checkpoint to OpenVINO IR at FP16 and INT8 (post-training quantisation).

    python -m perception.export --ckpt runs/perception/padim/.../model.ckpt --model padim --root data
Writes <out>/<model>/<precision>/weights/openvino/model.xml with a static 1x3x256x256 input,
because the NPU compiles static shapes only (decisions.md D8).
"""

import argparse
from pathlib import Path

import openvino as ov
from anomalib.deploy import CompressionType, ExportType
from anomalib.engine import Engine

from perception.train import MODELS, build_model, datamodule

INPUT_SIZE = (256, 256)
STATIC_INPUT = (1, 3, *INPUT_SIZE)
PRECISIONS = {"fp16": CompressionType.FP16, "int8": CompressionType.INT8_PTQ}


def ensure_static(xml: Path) -> None:
    shape = ov.Core().read_model(xml).inputs[0].get_partial_shape()
    if not shape.is_static:
        raise RuntimeError(f"{xml} has a dynamic input shape {shape}; the NPU needs a static one")


def export(ckpt: Path, model_name: str, root: Path, out: Path, precision: str) -> Path:
    engine = Engine(logger=False)
    xml = engine.export(
        model=build_model(model_name),
        export_type=ExportType.OPENVINO,
        export_root=out / model_name / precision,
        input_size=INPUT_SIZE,
        compression_type=PRECISIONS[precision],
        datamodule=datamodule(root, batch_size=1),  # INT8 calibration feeds the static batch-1 input
        ckpt_path=str(ckpt),
        ov_kwargs={"input": [STATIC_INPUT]},  # Anomalib leaves the batch dynamic by default
    )
    xml = Path(xml)
    ensure_static(xml)
    return xml


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ckpt", type=Path, required=True)
    ap.add_argument("--model", choices=sorted(MODELS), default="padim")
    ap.add_argument("--root", type=Path, default=Path("data"))
    ap.add_argument("--out", type=Path, default=Path("runs/export"))
    ap.add_argument("--precision", choices=[*PRECISIONS, "all"], default="all")
    args = ap.parse_args()
    for precision in PRECISIONS if args.precision == "all" else [args.precision]:
        print(export(args.ckpt, args.model, args.root, args.out, precision))


if __name__ == "__main__":
    main()
