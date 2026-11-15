"""Export an Anomalib checkpoint straight from PyTorch to OpenVINO, for models whose ONNX export breaks.

    python -m perception.export_direct --model patchcore --ckpt <model.ckpt> --out runs/detector/ov/patchcore

PatchCore's ONNX route traces part of the network with a batch of 2 and OpenVINO rejects it (Anomalib #3883). This
converts the torch network with a fixed 1x3x256x256 input instead and bakes in Anomalib's ImageNet normalisation, so
it takes the same [0, 1] RGB input as perception.inspector and returns the same pred_score and anomaly_map.
"""

import argparse
from pathlib import Path

import openvino as ov
import torch

from perception.train import MODELS

MEAN = torch.tensor([0.485, 0.456, 0.406]).view(1, 3, 1, 1)
STD = torch.tensor([0.229, 0.224, 0.225]).view(1, 3, 1, 1)


class Scored(torch.nn.Module):
    def __init__(self, network: torch.nn.Module):
        super().__init__()
        self.network = network

    def forward(self, rgb: torch.Tensor):
        result = self.network((rgb - MEAN) / STD)
        return result.pred_score, result.anomaly_map


def export_direct(model: str, ckpt: Path, out: Path) -> Path:
    network = MODELS[model].load_from_checkpoint(str(ckpt), map_location="cpu").model.eval()
    converted = ov.convert_model(Scored(network).eval(), example_input=torch.rand(1, 3, 256, 256), input=[1, 3, 256, 256])
    converted.outputs[0].get_tensor().set_names({"pred_score"})
    converted.outputs[1].get_tensor().set_names({"anomaly_map"})
    out.mkdir(parents=True, exist_ok=True)
    xml = out / "model.xml"
    ov.save_model(converted, xml, compress_to_fp16=False)
    return xml


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--model", choices=sorted(MODELS), default="patchcore")
    ap.add_argument("--ckpt", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    print(export_direct(args.model, args.ckpt, args.out))


if __name__ == "__main__":
    main()
