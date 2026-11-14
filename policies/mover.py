"""Learned Mover: ACT picks and presents, SmolVLA places by instruction (PRD 7.3, decisions.md D2).

reinspect (agreed by all three, 2026-11-14 04:16): 0 = put the brick down in the pick zone and
pick it again (the F4 re-grasp); ±90 = roll the wrist in place. True only when the brick is back
at the inspection pose.
"""

from collections.abc import Callable

import numpy as np

from common import deadline
from policies.episode import run_episode
from robot import io


class LearnedMover:
    def __init__(self, picker, placer, poses: dict[str, np.ndarray], frames: Callable[[], dict[str, np.ndarray]],
                 pick_steps: int = 360, place_steps: int = 360):
        """poses needs "home", "inspect" and "pick_drop" (joint vectors from config/waypoints.yaml).
        Default steps = 12 s at 30 Hz, the episode length in train/RECORDING.md."""
        self.picker, self.placer, self.frames = picker, placer, frames
        self.poses = {k: np.asarray(v, float) for k, v in poses.items()}
        self.pick_steps, self.place_steps = pick_steps, place_steps

    def _at_inspect(self, ignore_wrist_roll: bool = False) -> bool:
        diff = np.abs(io.observe() - self.poses["inspect"])
        diff[io.GRIPPER] = 0.0
        if ignore_wrist_roll:
            diff[io.WRIST_ROLL] = 0.0
        return bool(diff.max() <= io.POSE_TOLERANCE_DEG)

    # A fired stage deadline (run.py arms it) returns False, which run.py reports as a TIMEOUT.
    def pick_and_present(self) -> bool:
        run_episode(self.picker, self.frames, self.pick_steps, abort_event=deadline.abort)
        return not deadline.expired() and self._at_inspect() and not self.gripper_empty()

    def place(self, instruction: str) -> bool:
        joints = run_episode(self.placer, self.frames, self.place_steps, task=instruction, abort_event=deadline.abort)
        return not deadline.expired() and bool(joints[io.GRIPPER] >= io.GRIPPER_OPEN)

    def reinspect(self, angle_deg: int) -> bool:
        if angle_deg == 0:
            io.move_to(self.poses["pick_drop"])
            release = io.observe()
            release[io.GRIPPER] = io.GRIPPER_OPEN
            io.move_to(release, seconds=1.0)
            return self.pick_and_present()
        target = io.observe()
        target[io.WRIST_ROLL] += angle_deg
        io.move_to(target, seconds=1.5)
        return self._at_inspect(ignore_wrist_roll=True) and not self.gripper_empty()

    def gripper_empty(self) -> bool:
        return bool(io.observe()[io.GRIPPER] < io.GRIPPER_EMPTY_BELOW)

    def home(self) -> None:
        io.move_to(self.poses["home"])

    def estop(self) -> None:
        io.torque_off()
