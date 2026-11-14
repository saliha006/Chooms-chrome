"""Check a SmolVLA OpenVINO export computes what LeRobot's own policy computes (A3 parity).

    modal run train/parity.py --job <smolvla job>      # after train/export.py exported that job

Studio traces the export with zero starting noise, so LeRobot gets zero noise too and both should agree. Both get the
same preprocessed inputs (random images and state, the real task's tokens), so this checks the weights Studio loaded
from LeRobot's checkpoint (#1384) and the traced network, not the preprocessing.
"""

from pathlib import Path

import modal

from train.export import checkpoint_for
from train.export import image as studio_image
from train.modal_train import lerobot_image, volume

app = modal.App("sortsense-parity")
NAMED_INPUTS = ("tokenized_prompt", "tokenized_prompt_mask", "images", "image_masks")


@app.function(image=studio_image, volumes={"/runs": volume}, cpu=4.0, memory=16384, timeout=1200)
def openvino_side(job: str, task: str) -> dict:
    import numpy as np
    import openvino as ov
    import openvino_tokenizers  # noqa: F401  registers the tokenizer ops

    out = Path("/runs") / job / "openvino"
    core = ov.Core()
    ids, mask = core.compile_model(str(out / "tokenizer.xml"), "CPU")([np.array([task + "\n"])]).values()  # the runtime appends "\n"
    rng = np.random.default_rng(0)
    inputs = {"tokenized_prompt": ids, "tokenized_prompt_mask": mask, "image_masks": np.ones((3, 1), bool),
              "images": rng.uniform(-1, 1, (3, 1, 3, 512, 512)), "state": rng.standard_normal((1, 6))}
    compiled = core.compile_model(str(out / "smolvla.xml"), "CPU", {"INFERENCE_PRECISION_HINT": "f32"})
    feed = {}
    for port in compiled.inputs:
        name = port.any_name if port.any_name in NAMED_INPUTS else "state"  # the IR leaves the state input unnamed
        inputs[name] = inputs[name].astype(port.element_type.to_dtype())
        feed[port.any_name] = inputs[name]
    return inputs | {"actions": compiled(feed)[0]}


@app.function(image=lerobot_image, volumes={"/runs": volume}, cpu=4.0, memory=16384, timeout=1200)
def lerobot_side(job: str, task: str, inputs: dict) -> str:
    import numpy as np
    import torch
    from lerobot.policies.smolvla.modeling_smolvla import SmolVLAPolicy, pad_vector
    from transformers import AutoTokenizer

    policy = SmolVLAPolicy.from_pretrained(str(checkpoint_for("smolvla", Path("/runs") / job))).float().eval()
    cfg = policy.config
    tokens = AutoTokenizer.from_pretrained(cfg.vlm_model_name)(
        task + "\n", max_length=cfg.tokenizer_max_length, padding="max_length", truncation=True, padding_side="right")
    same_tokens = tokens["input_ids"] == inputs["tokenized_prompt"][0].tolist()

    t = {k: torch.from_numpy(np.asarray(v)) for k, v in inputs.items()}
    with torch.no_grad():
        actions = policy.model.sample_actions(
            list(t["images"].float()), list(t["image_masks"].bool()), t["tokenized_prompt"].long(),
            t["tokenized_prompt_mask"].bool(), pad_vector(t["state"].float(), cfg.max_state_dim),
            noise=torch.zeros(1, cfg.chunk_size, cfg.max_action_dim))[:, :, :6].numpy()
    diff = np.abs(actions - inputs["actions"])
    return (f"tokens match LeRobot's tokenizer: {same_tokens}\n"
            f"normalised action chunk {actions.shape}: max |LeRobot - OpenVINO| = {diff.max():.2e}, "
            f"mean {diff.mean():.2e}, LeRobot max |action| = {np.abs(actions).max():.2f}")


@app.local_entrypoint()
def main(job: str, task: str = ""):
    import yaml

    rules = yaml.safe_load((Path(__file__).resolve().parents[1] / "config" / "rules.yaml").read_text())
    task = task or rules["perfect"]
    print(lerobot_side.remote(job, task, openvino_side.remote(job, task)))
