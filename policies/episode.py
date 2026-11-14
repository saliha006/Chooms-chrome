"""Run one exported policy for up to a fixed number of control steps through robot.io.

Observation keys are the export manifest's, not LeRobot's dataset keys (checked through InferenceModel on the
SmolVLA export, 2026-11-14). Cameras keep the order of `frames`, which SmolVLA's runtime fills into camera1..3.
"""

import threading
import time
from collections.abc import Callable

import cv2
import numpy as np

from robot import io

STATE_KEY = "state"
IMAGE_KEY = "images.{}"
TASK_KEY = "task"


def observation(frames: dict[str, np.ndarray], task: str | None = None) -> dict:
    obs = {STATE_KEY: io.observe().astype(np.float32)[None]}
    # OpenCV grabs BGR; LeRobot recorded the training frames as RGB
    obs |= {IMAGE_KEY.format(name): cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)[None] for name, frame in frames.items()}
    if task is not None:
        obs[TASK_KEY] = [task]  # SmolVLA needs the task string or export bug #1169 bites (KeyError: 'task')
    return obs


def sustained(predicate: Callable[[], bool], ticks: int) -> Callable[[], bool]:
    """True once `predicate` has held for `ticks` calls in a row, so a pose passed through on the way does not end an episode."""
    run = 0

    def check() -> bool:
        nonlocal run
        run = run + 1 if predicate() else 0
        return run >= ticks

    return check


def run_episode(model, frames: Callable[[], dict[str, np.ndarray]], steps: int, task: str | None = None, hz: float = io.CONTROL_HZ,
                stop: Callable[[], bool] | None = None, abort_event: threading.Event | None = None) -> np.ndarray:
    """Return the joints at the end. `model` is a physicalai InferenceModel or anything with reset/select_action.

    Ends early once `stop()` says the stage has succeeded, or when `abort_event` is set (the stage deadline);
    the caller tells the two apart with `abort_event.is_set()`.
    """
    model.reset()
    for _ in range(steps):
        if (abort_event is not None and abort_event.is_set()) or (stop is not None and stop()):
            break
        tick = time.monotonic()
        io.act(np.asarray(model.select_action(observation(frames(), task)), float).ravel())
        time.sleep(max(0.0, 1 / hz - (time.monotonic() - tick)))
    return io.observe()


def load(export_dir: str, device: str):
    """An exported policy on an OpenVINO device; GPU first per PRD 7.2, the caller falls back."""
    from physicalai.inference import InferenceModel

    return InferenceModel(export_dir, backend="openvino", device=device)
