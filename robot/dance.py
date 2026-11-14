"""The end-of-run dance: the base sways left and right while the head bows and tilts to each side, then home.

Saliha's spec (2026-11-14): sway ±25°, 3 cycles, bow (wrist flex) 10° and tilt (wrist roll) ±10° to the side the
base is facing, about 6 s, then back home. Called by run.py once the zone is empty, after the last place, so
the gripper is already empty. All motion goes through robot.io, so joint limits, the speed cap and the e-stop
apply as everywhere else (decisions.md D19, D21). Joint signs are TUNE: flip a sign if a move goes the wrong way.
"""

import numpy as np

from robot import io

PAN = io.JOINTS.index("shoulder_pan")
FLEX = io.JOINTS.index("wrist_flex")
ROLL = io.WRIST_ROLL


def poses(home: np.ndarray, cycles: int = 3, sway_deg: float = 25, nod_deg: float = 10, tilt_deg: float = 10) -> list[np.ndarray]:
    """Left, right, left, right ... then home. Each side: base turned, head bowed and tilted towards that side."""
    home = np.asarray(home, float)
    sequence = []
    for _ in range(cycles):
        for side in (1, -1):
            pose = home.copy()
            pose[PAN] += side * sway_deg
            pose[FLEX] += nod_deg
            pose[ROLL] += side * tilt_deg
            sequence.append(np.clip(pose, io.JOINT_MIN, io.JOINT_MAX))
    return [*sequence, home]


def dance(home: np.ndarray, half_period_s: float = 1.0, **shape) -> bool:
    """True if every pose was reached in time. An E press raises estop.EStopped from io.act, as for any motion."""
    reached = [io.move_to(pose, seconds=half_period_s) for pose in poses(home, **shape)]
    return all(reached)
