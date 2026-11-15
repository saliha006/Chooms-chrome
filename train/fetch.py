"""Fetch a finished export from the `sortsense-runs` Volume to the laptop and check it loads on each device.

    .venv-robot/bin/python -m train.fetch <job> --modal .venv/bin/modal   # into runs/exports/<job>, then CPU and GPU
    .venv-robot/bin/python -m train.fetch <job> --no-fetch                # only re-check runs/exports/<job>
    .venv-robot/bin/python -m train.fetch <job> --no-fetch --devices GPU

Run it with .venv-robot: the app's .venv has an older jsonargparse that InferenceModel fails on ("'ArgumentParser'
object has no attribute 'instantiate'"), and only .venv has the modal CLI, hence --modal.

Each device gets a zero observation (SmolVLA also gets the `perfect` string from config/rules.yaml) through
`InferenceModel`, the call path `policies/episode.py` uses, and reports the inputs, the chunk and the first action.
The folder printed last is what config/models.yaml points at.
"""

import argparse
import subprocess
import time
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[1]
EXPORTS = REPO / "runs" / "exports"  # runs/ is git-ignored: the SmolVLA IR alone is 1.6 GB


def fetch_command(job: str, dest: Path, modal: str = "modal") -> list[str]:
    return [modal, "volume", "get", "sortsense-runs", f"{job}/openvino", str(dest)]


def find_export(dest: Path) -> Path:
    """The folder holding manifest.json: `modal volume get` may or may not nest it in an openvino/ folder."""
    manifests = sorted(dest.rglob("manifest.json"))
    if len(manifests) != 1:
        raise FileNotFoundError(f"expected one manifest.json under {dest}, found {len(manifests)}")
    return manifests[0].parent


def zero_observation(features, task: str) -> dict:
    return {f.name: [task] if f.ftype == "LANGUAGE" else np.zeros((1, *f.shape), np.float32) for f in features}


def check(export_dir: Path, device: str, task: str) -> str:
    from physicalai.inference import InferenceModel

    start = time.monotonic()
    model = InferenceModel(str(export_dir), backend="openvino", device=device)
    loaded = time.monotonic() - start
    observation = zero_observation(model.input_features, task)
    start = time.monotonic()
    chunk = model.predict_action_chunk(observation)
    inputs = ", ".join(f"{f.name} {tuple(f.shape)}" for f in model.input_features)
    return (f"{device}: loaded in {loaded:.1f} s; inputs {inputs}\n"
            f"{device}: action chunk {chunk.shape} in {(time.monotonic() - start) * 1000:.0f} ms (first call), "
            f"all finite: {bool(np.isfinite(chunk).all())}, first action {np.round(chunk[0].astype(float), 2).tolist()}")


def main() -> None:
    import yaml  # train/export.py imports this module inside its Modal image, which may lack PyYAML

    ap = argparse.ArgumentParser(description="Fetch a Modal export and check it loads with InferenceModel.")
    ap.add_argument("job")
    ap.add_argument("--no-fetch", action="store_true", help="skip modal volume get; check what is already here")
    ap.add_argument("--devices", default="CPU,GPU")
    ap.add_argument("--modal", default="modal", help="the modal CLI to fetch with")
    args = ap.parse_args()

    dest = EXPORTS / args.job
    if not args.no_fetch:
        dest.mkdir(parents=True, exist_ok=True)
        subprocess.run(fetch_command(args.job, dest, args.modal), check=True)
    export_dir = find_export(dest)
    task = yaml.safe_load((REPO / "config" / "rules.yaml").read_text())["perfect"]
    for device in args.devices.split(","):
        try:
            print(check(export_dir, device, task))
        except Exception as exc:  # the runtime raises several types; report this device and try the next
            print(f"{device}: failed: {exc}")
    print(f"export: {export_dir}")


if __name__ == "__main__":
    main()
