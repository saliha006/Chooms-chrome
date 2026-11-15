"""Is a brick in the jaws? Seen by the inspection camera at the inspect pose, against a photo of the empty gripper.

Only valid while that camera looks at the gripper. With a `plate:` region in config/scene.yaml run.py uses
perception.plate instead (the camera now looks at the plate).

The gripper's position can't tell: a Duplo held at the jaw tips reads ~2, the same as closed on nothing (N8 measured
~17 only for a brick held deeper). The wrist camera can: with a brick, the crop differs strongly from the empty one.
"""

from pathlib import Path

import cv2
import numpy as np

from perception.capture import square_crop

EMPTY_JAWS = Path("runs/empty_jaws.png")  # perception.shoot keeps it: the closed, empty gripper at the inspect pose
EMPTY_DIFF = 18.0  # TUNE: brick photos differ by 29-33 grey levels on average, the empty gripper by ~0


def brick_in_jaws(frame_bgr: np.ndarray, crop: tuple[int, int, int] | None, reference: Path = EMPTY_JAWS) -> bool:
    if not reference.exists():
        return False
    now = cv2.cvtColor(square_crop(frame_bgr, crop), cv2.COLOR_BGR2GRAY).astype(float)
    empty = cv2.cvtColor(cv2.imread(str(reference)), cv2.COLOR_BGR2GRAY).astype(float)
    return float(np.abs(now - empty).mean()) >= EMPTY_DIFF
