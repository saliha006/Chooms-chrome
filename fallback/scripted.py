"""Scripted Mover: replays taught waypoints through robot/io.py, no learned model (decisions.md D3).

The insurance for the 15:30 gate and for any policy that fails its gate. It must keep working after the
learned policies swap in, and the demo always says when it is the one moving the arm.
"""

import time
from pathlib import Path

import numpy as np
import yaml

from common import deadline as stage_deadline
from common import estop
from robot import io

POSES = ("home", "pick_above", "pick", "pick_drop", "inspect", "bowl_red", "bowl_blue")

# Gripper thresholds and the inspection-pose tolerance live in robot/io.py, shared with LearnedMover,
# so a tune on the arm (Nate's N8) changes one place.
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


def bowl_for(instruction: str) -> str:
    """The bowl pose (and scene.yaml region) an instruction names. The instruction is the same language SmolVLA
    gets (config/rules.yaml); names are roles (bowl_blue = perfect, bowl_red = defective), the real bowls are
    purple and orange."""
    for colour, pose in (("orange", "bowl_red"), ("purple", "bowl_blue"), ("red", "bowl_red"), ("blue", "bowl_blue")):
        if f"{colour} bowl" in instruction:
            return pose
    raise ValueError(f"no bowl named in instruction: {instruction!r}")


class ScriptedMover:
    def __init__(self, poses: dict[str, np.ndarray]):
        self.poses = poses

    def pick_and_present(self) -> bool:
        if not (self._go("pick_above", io.GRIPPER_OPEN) and self._go("pick", io.GRIPPER_OPEN)):
            return False
        self._set_gripper(GRIPPER_CLOSED)
        return self._go("pick_above", GRIPPER_CLOSED) and self._go("inspect", GRIPPER_CLOSED) and self._settled_holding()

    def place(self, instruction: str) -> bool:
        if not self._go(bowl_for(instruction), GRIPPER_CLOSED):
            return False
        self._set_gripper(io.GRIPPER_OPEN)
        return bool(io.observe()[io.GRIPPER] >= io.GRIPPER_OPEN - io.POSE_TOLERANCE_DEG)

    def reinspect(self, angle_deg: int) -> bool:
        if angle_deg == 0:
            if not self._go("pick_drop", GRIPPER_CLOSED):
                return False
            self._set_gripper(io.GRIPPER_OPEN)
            return self.pick_and_present()
        target = io.observe()
        target[io.WRIST_ROLL] += io.units(angle_deg)[io.WRIST_ROLL]
        target[io.GRIPPER] = GRIPPER_CLOSED
        self._move(target)
        return self._near(self.poses["inspect"], io.POSE_TOLERANCE_DEG, ignore_wrist_roll=True) and self._settled_holding()

    def gripper_empty(self) -> bool:
        return not io.holding()

    def home(self) -> None:
        self._go("home", io.observe()[io.GRIPPER])

    def estop(self) -> None:
        io.torque_off()

    @staticmethod
    def _settled_holding() -> bool:
        # Same grasp test as LearnedMover (io.holding band after the settle, decisions.md D22).
        time.sleep(io.GRIPPER_SETTLE_S)
        return io.holding()

    def _go(self, name: str, gripper: float) -> bool:
        target = self.poses[name].copy()
        target[io.GRIPPER] = gripper
        return self._move(target)

    def _move(self, target: np.ndarray) -> bool:
        """Step toward target until the arm joints arrive. The gripper is left out of the check: while
        carrying, it is commanded closed and the brick stops it short, which must not read as "stuck"."""
        return self._step_until(target, lambda: self._near(target, ARRIVE_TOLERANCE_DEG), MOVE_SECONDS)

    def _set_gripper(self, value: float) -> None:
        target = io.observe()
        target[io.GRIPPER] = value
        # Closing on a brick never reaches 0; the timeout is the settle time, so its result is ignored.
        self._step_until(target, lambda: abs(io.observe()[io.GRIPPER] - value) <= ARRIVE_TOLERANCE_DEG, 1.0)

    @staticmethod
    def _step_until(target: np.ndarray, arrived, seconds: float) -> bool:
        deadline = time.monotonic() + seconds
        while not arrived():
            if estop.requested():
                io.torque_off()
                raise estop.EStopped()
            if time.monotonic() > deadline or stage_deadline.expired():
                return False
            io.act(target)
            time.sleep(1 / io.CONTROL_HZ)
        return True

    @staticmethod
    def _near(target: np.ndarray, tolerance_deg: float, ignore_wrist_roll: bool = False) -> bool:
        near = io.within(target, tolerance_deg)
        near[io.GRIPPER] = True
        if ignore_wrist_roll:
            near[io.WRIST_ROLL] = True
        return bool(near.all())
