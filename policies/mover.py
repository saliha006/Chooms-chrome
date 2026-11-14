"""Learned Mover: ACT picks and presents, SmolVLA places by instruction (PRD 7.3, decisions.md D2).

reinspect (agreed by all three, 2026-11-14 04:16): 0 = put the brick down in the pick zone and
pick it again (the F4 re-grasp); ±90 = roll the wrist in place. True only when the brick is back
at the inspection pose.
"""

from collections.abc import Callable

import time

import numpy as np

from common import deadline
from policies.episode import run_episode, sustained
from robot import io

SETTLE_TICKS = round(io.GRIPPER_SETTLE_S * io.CONTROL_HZ)


class LearnedMover:
    def __init__(self, picker, placer, poses: dict[str, np.ndarray], frames: Callable[[], dict[str, np.ndarray]],
                 pick_steps: int = 360, place_steps: int = 360,
                 bowl_check: Callable[[str, np.ndarray, np.ndarray], bool] | None = None):
        """poses needs "home", "inspect" and "pick_drop" (joint vectors from config/waypoints.yaml).
        Default steps = 12 s at 30 Hz, the episode length in train/RECORDING.md.
        bowl_check(instruction, top_before, top_after) says the brick landed in the right bowl (scene.brick_in_bowl);
        without it a place counts once the gripper has opened."""
        self.picker, self.placer, self.frames = picker, placer, frames
        self.poses = {k: np.asarray(v, float) for k, v in poses.items()}
        self.pick_steps, self.place_steps = pick_steps, place_steps
        self.bowl_check = bowl_check

    def _at_inspect(self, ignore_wrist_roll: bool = False) -> bool:
        diff = np.abs(io.observe() - self.poses["inspect"])
        diff[io.GRIPPER] = 0.0
        if ignore_wrist_roll:
            diff[io.WRIST_ROLL] = 0.0
        return bool(diff.max() <= io.POSE_TOLERANCE_DEG)

    # A fired stage deadline (run.py arms it) returns False, which run.py reports as a TIMEOUT.
    def pick_and_present(self) -> bool:
        presented = sustained(lambda: self._at_inspect() and io.holding(), SETTLE_TICKS)
        run_episode(self.picker, self.frames, self.pick_steps, stop=presented, abort_event=deadline.abort)
        if not presented():  # ran out of steps: give the brick the settle time an early exit already had
            time.sleep(io.GRIPPER_SETTLE_S)
        return not deadline.expired() and self._at_inspect() and io.holding()

    def place(self, instruction: str) -> bool:
        if not self._roll_back_to_inspect():
            return False
        before = self.frames()["top"] if self.bowl_check else None  # KeyError beats handing the check a None frame
        opened = sustained(lambda: io.observe()[io.GRIPPER] >= io.GRIPPER_OPEN - io.POSE_TOLERANCE_DEG, SETTLE_TICKS)
        joints = run_episode(self.placer, self.frames, self.place_steps, task=instruction, stop=opened, abort_event=deadline.abort)
        if deadline.expired() or joints[io.GRIPPER] < io.GRIPPER_OPEN - io.POSE_TOLERANCE_DEG:
            return False
        return self.bowl_check is None or bool(self.bowl_check(instruction, before, self.frames()["top"]))

    def _roll_back_to_inspect(self) -> bool:
        """SmolVLA's place demos all start at the inspection pose, so undo a wrist roll from reinspect first."""
        roll = self.poses["inspect"][io.WRIST_ROLL]
        if abs(io.observe()[io.WRIST_ROLL] - roll) <= io.POSE_TOLERANCE_DEG:
            return True
        target = io.observe()
        target[io.WRIST_ROLL] = roll
        return io.move_to(target, seconds=1.5)

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
        return self._at_inspect(ignore_wrist_roll=True) and io.holding()

    def gripper_empty(self) -> bool:
        """True unless a brick is held (closed on nothing and open both count as empty); run.py reads this after the grasp."""
        return not io.holding()

    def home(self) -> None:
        io.move_to(self.poses["home"])

    def estop(self) -> None:
        io.torque_off()
