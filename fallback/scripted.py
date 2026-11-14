"""Scripted Mover: replays taught waypoints through robot/io.py, no learned model (decisions.md D3).

The insurance for the 15:30 gate and for any policy that fails its gate. It must keep working after the
learned policies swap in, and the demo always says when it is the one moving the arm.
"""

import time
from pathlib import Path

import numpy as np
import yaml

from robot import io

POSES = ("home", "pick_above", "pick", "pick_drop", "inspect", "bowl_red", "bowl_blue")

# Same physical facts as policies/mover.py, kept separate on purpose: the fallback must not
# break when the learned stack's imports or tuning change. TUNE both together.
POSE_TOLERANCE_DEG = 8.0  # "at the inspection pose" after a wrist roll
GRIPPER_EMPTY_BELOW = 5.0
GRIPPER_OPEN = 60.0

GRIPPER_CLOSED = 0.0
ARRIVE_TOLERANCE_DEG = 2.0  # a scripted move is done; matches robot.io.move_to
MOVE_SECONDS = 3.0  # TUNE: longest single move before it counts as blocked


def load_waypoints(path: Path) -> dict[str, np.ndarray]:
    raw = yaml.safe_load(path.read_text()) or {}
    missing = [name for name in POSES if raw.get(name) is None]
    if missing:
        raise ValueError(f"{path}: teach these poses first (python -m fallback.teach <name>): {', '.join(missing)}")
    poses = {name: np.asarray(raw[name], float) for name in POSES}
    wrong = [name for name, pose in poses.items() if pose.shape != (len(io.JOINTS),)]
    if wrong:
        raise ValueError(f"{path}: need {len(io.JOINTS)} joint values for {', '.join(wrong)}")
    return poses


class ScriptedMover:
    def __init__(self, poses: dict[str, np.ndarray]):
        self.poses = poses

    def pick_and_present(self) -> bool:
        if not (self._go("pick_above", GRIPPER_OPEN) and self._go("pick", GRIPPER_OPEN)):
            return False
        self._set_gripper(GRIPPER_CLOSED)
        return (self._go("pick_above", GRIPPER_CLOSED) and self._go("inspect", GRIPPER_CLOSED)
                and not self.gripper_empty())

    def place(self, instruction: str) -> bool:
        if not self._go(self._bowl_for(instruction), GRIPPER_CLOSED):
            return False
        self._set_gripper(GRIPPER_OPEN)
        return bool(io.observe()[io.GRIPPER] >= GRIPPER_OPEN - POSE_TOLERANCE_DEG)

    def reinspect(self, angle_deg: int) -> bool:
        if angle_deg == 0:
            if not self._go("pick_drop", GRIPPER_CLOSED):
                return False
            self._set_gripper(GRIPPER_OPEN)
            return self.pick_and_present()
        target = io.observe()
        target[io.WRIST_ROLL] += angle_deg
        target[io.GRIPPER] = GRIPPER_CLOSED
        self._move(target)
        return self._near(self.poses["inspect"], POSE_TOLERANCE_DEG, ignore_wrist_roll=True) and not self.gripper_empty()

    def gripper_empty(self) -> bool:
        return bool(io.observe()[io.GRIPPER] < GRIPPER_EMPTY_BELOW)

    def home(self) -> None:
        self._go("home", io.observe()[io.GRIPPER])

    def estop(self) -> None:
        io.torque_off()

    @staticmethod
    def _bowl_for(instruction: str) -> str:
        # The instruction is the same language SmolVLA gets (config/rules.yaml), so read the colour from it.
        for colour in ("red", "blue"):
            if f"{colour} bowl" in instruction:
                return f"bowl_{colour}"
        raise ValueError(f"no bowl named in instruction: {instruction!r}")

    def _go(self, name: str, gripper: float) -> bool:
        target = self.poses[name].copy()
        target[io.GRIPPER] = gripper
        return self._move(target)

    def _move(self, target: np.ndarray) -> bool:
        """Step toward target until the arm joints arrive. The gripper is left out of the check: while
        carrying, it is commanded closed and the brick stops it short, which must not read as "stuck"."""
        deadline = time.monotonic() + MOVE_SECONDS
        while not self._near(target, ARRIVE_TOLERANCE_DEG):
            if time.monotonic() > deadline:
                return False
            io.act(target)
            time.sleep(1 / io.CONTROL_HZ)
        return True

    def _set_gripper(self, value: float) -> None:
        target = io.observe()
        target[io.GRIPPER] = value
        io.move_to(target, seconds=1.0)  # closing on a brick never reaches 0; the timeout is the settle time

    @staticmethod
    def _near(target: np.ndarray, tolerance_deg: float, ignore_wrist_roll: bool = False) -> bool:
        diff = np.abs(io.observe() - np.clip(target, io.JOINT_MIN, io.JOINT_MAX))
        diff[io.GRIPPER] = 0.0
        if ignore_wrist_roll:
            diff[io.WRIST_ROLL] = 0.0
        return bool(diff.max() <= tolerance_deg)
