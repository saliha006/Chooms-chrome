"""Run one exported policy for a fixed number of control steps through robot.io.

Observation keys follow LeRobot's naming; check them against the export's manifest on the
station (InferenceModel orders cameras and applies the manifest's preprocessors).
"""

import time
from collections.abc import Callable

import numpy as np

from robot import io

STATE_KEY = "observation.state"
IMAGE_KEY = "observation.images.{}"
TASK_KEY = "task"


def observation(frames: dict[str, np.ndarray], task: str | None = None) -> dict:
    obs = {STATE_KEY: io.observe().astype(np.float32)[None]}
    obs |= {IMAGE_KEY.format(name): frame for name, frame in frames.items()}
    if task is not None:
        obs[TASK_KEY] = [task]  # SmolVLA needs the task string or export bug #1169 bites (KeyError: 'task')
    return obs


def run_episode(model, frames: Callable[[], dict[str, np.ndarray]], steps: int, task: str | None = None, hz: float = io.CONTROL_HZ) -> np.ndarray:
    """Return the joints at the end. `model` is a physicalai InferenceModel or anything with reset/select_action."""
    model.reset()
    for _ in range(steps):
        tick = time.monotonic()
        io.act(np.asarray(model.select_action(observation(frames(), task)), float).ravel())
        time.sleep(max(0.0, 1 / hz - (time.monotonic() - tick)))
    return io.observe()


def load(export_dir: str, device: str):
    """An exported policy on an OpenVINO device; GPU first per PRD 7.2, the caller falls back."""
    from physicalai.inference import InferenceModel

    return InferenceModel(export_dir, backend="openvino", device=device)
