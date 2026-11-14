"""Export a trained checkpoint from the `sortsense-runs` Volume to OpenVINO and check the IR runs (A3).

    modal run train/export.py --job <job> --policy act        # Studio ACT: the job's latest .ckpt
    modal run train/export.py --job <job> --policy smolvla    # LeRobot SmolVLA: the latest pretrained_model/
    modal volume get sortsense-runs <job>/openvino ./exports/<job>/   # then copy to the Intel laptop

Runs on Modal's Linux because the `physicalai` CLI does not start on Windows. The IR is device-independent; the
Intel laptop compiles it for CPU, GPU or NPU. Back up the checkpoint first (Studio PR #1403 could delete one).
"""

import time
from pathlib import Path

import modal

from train.modal_train import volume

app = modal.App("sortsense-export")
image = (
    modal.Image.debian_slim(python_version="3.12")
    .apt_install("ffmpeg", "git")
    .pip_install("physicalai-train[cpu,smolvla]==0.3.0")
    .add_local_python_source("train")
)


def checkpoint_for(policy: str, job_dir: Path) -> Path:
    """The latest checkpoint a training job left: Studio's Lightning .ckpt for ACT, LeRobot's pretrained_model/ for SmolVLA."""
    found = list(job_dir.rglob("*.ckpt")) if policy == "act" else list(job_dir.glob("checkpoints/*/pretrained_model"))
    if not found:
        raise FileNotFoundError(f"no {policy} checkpoint under {job_dir}")
    return max(found, key=lambda p: p.stat().st_mtime)  # names sort badly once step counts differ in digits


@app.function(image=image, volumes={"/runs": volume}, cpu=4.0, memory=16384, timeout=1800)
def export(job: str, policy: str) -> str:
    import numpy as np
    import openvino as ov

    job_dir = Path("/runs") / job
    checkpoint = checkpoint_for(policy, job_dir)
    if policy == "act":
        from physicalai.policies import ACT

        model = ACT.load_from_checkpoint(str(checkpoint), map_location="cpu")
    else:
        from physicalai.policies.smolvla import SmolVLA

        model = SmolVLA(pretrained_name_or_path=str(checkpoint), dtype="float32")  # f32: the CPU NaN bug (#1414)
    out = job_dir / "openvino"
    model.export(str(out), backend="openvino")
    volume.commit()

    report = [f"exported {checkpoint.relative_to(job_dir)} -> {out.relative_to(job_dir)}"]
    report += [f"  {p.relative_to(out)} ({p.stat().st_size / 1e6:.1f} MB)" for p in sorted(out.rglob("*")) if p.is_file()]
    for xml in sorted(out.rglob("*.xml")):
        compiled = ov.Core().compile_model(str(xml), "CPU")
        inputs = {port.any_name: np.zeros([d if d > 0 else 1 for d in port.partial_shape.get_min_shape()],
                                          dtype=port.element_type.to_dtype()) for port in compiled.inputs}
        start = time.monotonic()
        outputs = compiled(inputs)
        report.append(f"{xml.name}: CPU inference on zeros in {(time.monotonic() - start) * 1000:.0f} ms; "
                      f"inputs {[(k, v.shape) for k, v in inputs.items()]}; outputs {[o.shape for o in outputs.values()]}")
    return "\n".join(report)


@app.local_entrypoint()
def main(job: str, policy: str = "act"):
    if policy not in ("act", "smolvla"):
        raise SystemExit("--policy must be act or smolvla")
    print(export.remote(job, policy))
