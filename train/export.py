"""Export a trained checkpoint from the `sortsense-runs` Volume to OpenVINO and check the IR runs (A3).

    modal run train/export.py --job <job> --policy act        # Studio ACT: the job's latest .ckpt
    modal run train/export.py --job <job> --policy smolvla    # LeRobot SmolVLA: the latest pretrained_model/
    modal volume get sortsense-runs <job>/openvino ./exports/<job>/   # then copy to the Intel laptop

The check loads the export with Studio's `InferenceModel` on CPU, the call path the laptop uses, gives it a zero
observation (SmolVLA also gets the exact `perfect` task string from config/rules.yaml, or --task) and reports whether
the action chunk is finite. A job is exported once and later runs only re-check it, so delete <job>/openvino on the
Volume to export a newer checkpoint.

Runs on Modal's Linux because the `physicalai` CLI does not start on Windows. The IR is device-independent; the
Intel laptop compiles it for CPU, GPU or NPU. Back up the checkpoint first: older Studio exports could delete it
on a crash (fixed by Studio PR #1403).
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
def export(job: str, policy: str, task: str) -> str:
    import numpy as np
    from physicalai.inference import InferenceModel

    job_dir = Path("/runs") / job
    out = job_dir / "openvino"
    report = []
    if not any(out.rglob("*.xml")):
        checkpoint = checkpoint_for(policy, job_dir)
        if policy == "act":
            from physicalai.policies import ACT

            model = ACT.load_from_checkpoint(str(checkpoint), map_location="cpu")
        else:
            from physicalai.policies.smolvla import SmolVLA

            # float32: the CPU fallback (PRD 7.2) runs at full precision
            model = SmolVLA(pretrained_name_or_path=str(checkpoint), dtype="float32")
        model.export(str(out), backend="openvino")
        volume.commit()
        report.append(f"exported {checkpoint.relative_to(job_dir)} -> openvino")
    else:
        report.append("existing export, re-checked only")
    report += [f"  {p.relative_to(out)} ({p.stat().st_size / 1e6:.1f} MB)" for p in sorted(out.rglob("*")) if p.is_file()]

    # The laptop's call path: the manifest's own preprocessing (resize, newline, normalise, tokenise) and denormalising
    runtime = InferenceModel(str(out), device="CPU")
    observation = {f.name: [task] if f.ftype == "LANGUAGE" else np.zeros((1, *f.shape), np.float32)
                   for f in runtime.input_features}
    start = time.monotonic()
    chunk = runtime.predict_action_chunk(observation)
    report.append(f"InferenceModel on CPU, first call: {', '.join(observation)} -> action chunk {chunk.shape} in "
                  f"{(time.monotonic() - start) * 1000:.0f} ms; all finite: {bool(np.isfinite(chunk).all())}")
    return "\n".join(report)


@app.local_entrypoint()
def main(job: str, policy: str = "act", task: str = ""):
    import yaml

    if policy not in ("act", "smolvla"):
        raise SystemExit("--policy must be act or smolvla")
    rules = yaml.safe_load((Path(__file__).resolve().parents[1] / "config" / "rules.yaml").read_text())
    print(export.remote(job, policy, task or rules["perfect"]))
