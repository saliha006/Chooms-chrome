"""Correct-shaped stand-ins so the whole loop runs with no hardware (`run.py --mock`)."""

import time
from itertools import cycle
from pathlib import Path

import cv2
import numpy as np

from common.interfaces import DefectSignal

IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".bmp"}


class MockCamera:
    """Cycles through a folder of images, or plain numbered frames when no folder is given."""

    def __init__(self, folder: str | Path | None = None, size: tuple[int, int] = (480, 640), fps: float | None = None):
        self._size = size
        self._period = 1 / fps if fps else 0.0
        self._count = 0
        self._paths = None
        if folder is not None:
            paths = sorted(p for p in Path(folder).iterdir() if p.suffix.lower() in IMAGE_SUFFIXES)
            if not paths:
                raise FileNotFoundError(f"no images in {folder}")
            self._paths = cycle(paths)

    def read(self) -> np.ndarray:
        # A real camera blocks until its next frame; pacing keeps a capture thread from spinning.
        time.sleep(self._period)
        self._count += 1
        if self._paths is not None:
            return cv2.imread(str(next(self._paths)))
        frame = np.full((*self._size, 3), 90, np.uint8)
        cv2.putText(frame, f"mock {self._count}", (20, 60), cv2.FONT_HERSHEY_SIMPLEX, 1.5, (255, 255, 255), 2)
        return frame


class MockInspector:
    """Returns verdicts from a repeating label script, with scores on the right side of the thresholds."""

    T_LOW, T_HIGH = 0.4, 0.7
    SCORES = {"perfect": 0.2, "uncertain": 0.55, "defective": 0.9}

    def __init__(self, labels=("perfect", "defective", "uncertain", "perfect", "defective")):
        self._labels = cycle(labels)

    def inspect(self, frame, view: str, brick_id: int) -> DefectSignal:
        label = next(self._labels)
        return DefectSignal(
            brick_id=brick_id, view=view, label=label, score=self.SCORES[label],
            t_low=self.T_LOW, t_high=self.T_HIGH, bbox=None, heatmap_path=None,
            model="mock", device="CPU", latency_ms=0.0,
        )


class MockLocator:
    """Reports `n` bricks in the pick zone, then an empty zone."""

    def __init__(self, n: int = 5):
        self._left = n

    def next_brick(self) -> bool:
        if self._left == 0:
            return False
        self._left -= 1
        return True


class MockMover:
    """Records every call; the first `pick_failures` picks fail so the retry path gets exercised."""

    def __init__(self, pick_failures: int = 0):
        self.calls: list[tuple] = []
        self._pick_failures = pick_failures

    def pick_and_present(self) -> bool:
        self.calls.append(("pick_and_present",))
        if self._pick_failures:
            self._pick_failures -= 1
            return False
        return True

    def place(self, instruction: str) -> bool:
        self.calls.append(("place", instruction))
        return True

    def reinspect(self, angle_deg: int) -> bool:
        self.calls.append(("reinspect", angle_deg))
        return True

    def gripper_empty(self) -> bool:
        return False

    def home(self) -> None:
        self.calls.append(("home",))

    def estop(self) -> None:
        self.calls.append(("estop",))
