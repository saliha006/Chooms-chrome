"""Scripted Mover: replays taught waypoints through robot/io.py, no learned model (decisions.md D3).

The insurance for the 15:30 gate and for any policy that fails its gate. It must keep working after the
learned policies swap in, and the demo always says when it is the one moving the arm.
"""

import math
import time
from contextlib import contextmanager
from pathlib import Path

import numpy as np
import yaml

from common import deadline as stage_deadline
from common import estop
from robot import io

POSES = ("home", "pick_above", "pick", "pick_drop", "inspect", "bowl_red", "bowl_blue")
# Optional extra pick spots, so 5 bricks laid on 5 marked spots are sorted with no human: slot 1 is pick/pick_above.
SLOT_POSES = tuple(f"{kind}_{n}" for n in range(2, 6) for kind in ("pick_above", "pick"))

# Gripper thresholds and the inspection-pose tolerance live in robot/io.py, shared with LearnedMover,
# so a tune on the arm (Nate's N8) changes one place.
GRIPPER_CLOSED = 0.0
ARRIVE_TOLERANCE_DEG = 4.0  # a scripted move is done: the loaded shoulder settles up to 3.5° short (dry run, 2026-11-15 01:35)
MOVE_SECONDS = 3.0  # TUNE: shortest time a move gets before it counts as blocked
# io.act() steps from the observed position, so the servo only ever sees one cap of error and crawls:
# elbow 91 -> 58 units at a 4-unit cap took ~2.2 s on the follower (2026-11-15 08:08), not cap x 30 Hz.
ARM_SPEED_PER_CAP = 3.7  # TUNE: units per second per unit of step cap
REACH_CM = 25.0  # TUNE: shoulder axis to a pick slot, turns a sideways search in cm into shoulder_pan degrees
SHOULDER_PAN = io.JOINTS.index("shoulder_pan")
LIFT_JOINTS = [io.JOINTS.index(name) for name in ("shoulder_lift", "elbow_flex", "wrist_flex")]
# Station test 07:42: straight fast moves bumped the camera into the wall, slammed onto the brick (shoving the
# wheeled board) and flung a tip-held brick out on the way to the bowl.
APPROACH_STEP_DEG = 3.0  # TUNE (about 11 units/s on the arm): pick_above <-> pick, the last few cm onto and off the brick
CARRY_STEP_DEG = 4.0  # TUNE: any move while a brick is in the jaws
PRE_CLOSE_S = 0.3  # TUNE: let the arm stop over the brick before closing
POST_CLOSE_S = 0.5  # TUNE: let the grip settle before lifting
BOWL_SETTLE_S = 0.3  # TUNE: stop swinging over the bowl before opening
RELEASE_S = 0.5  # TUNE: let the brick fall clear before the arm leaves
# Depth along the taught pick_above -> pick line (1.0 = the taught pick). A retry, or jaws that shut on (almost)
# nothing, reach a little lower with the jaws wider: tonight's misses held the brick at the tips or not at all.
DEEPER = 0.1  # TUNE
MAX_DEPTH = 1.1  # never more than 10% past the taught pick
RETRY_OPEN = 80.0  # TUNE: gripper opening for a retry, wider than io.GRIPPER_OPEN


def load_waypoints(path: Path) -> dict[str, np.ndarray]:
    raw = yaml.safe_load(path.read_text()) or {}
    missing = [name for name in POSES if raw.get(name) is None]
    if missing:
        raise ValueError(f"{path}: teach these poses first (python -m fallback.teach <name>): {', '.join(missing)}")
    poses = {name: np.asarray(raw[name], float) for name in POSES + SLOT_POSES if raw.get(name) is not None}
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


@contextmanager
def step_cap(deg: float | None):
    """Slow robot.io's per-step cap to `deg` (never speed it up) for a block; restored even on an e-stop."""
    before = io.MAX_STEP_DEG
    if deg is not None:
        io.MAX_STEP_DEG = min(before, deg)
    try:
        yield
    finally:
        io.MAX_STEP_DEG = before


class ScriptedMover:
    """A missed slot is tried once more (the brick is still there), jaws wider and a little deeper, before the next
    slot. `search_cm` > 0 also shifts that retry sideways (the other side at that slot's next miss), for a brick laid
    a little off its marked spot.

    The retry is kept here, not passed in by run.py: pick_and_present() takes no arguments in the frozen Mover
    contract (common/interfaces.py), and run.py's second attempt always follows a miss straight away."""

    def __init__(self, poses: dict[str, np.ndarray], search_cm: float = 0.0):
        self.poses = poses
        self.slots = [("pick_above", "pick")] + [(f"pick_above_{n}", f"pick_{n}") for n in range(2, 6)
                                                 if f"pick_{n}" in poses and f"pick_above_{n}" in poses]
        self._next_slot = 0
        self._search_deg = np.degrees(search_cm / REACH_CM)
        self._missed: tuple[str, str] | None = None  # the slot the next pick retries
        self._side: dict[str, int] = {}  # pick pose -> the side its next search tries
        self._carrying = False  # from closing on a brick until the jaws open again: every move at CARRY_STEP_DEG

    def pick_and_present(self) -> bool:
        if self._missed is not None:
            above, pick = self._missed
            self._missed = None
            side = self._side.get(pick, 1)
            self._side[pick] = -side
            pan = side * io.units(self._search_deg)[SHOULDER_PAN]
            return self._pick_from(above, pick, pan, retry=True)
        above, pick = self.slots[self._next_slot % len(self.slots)]
        self._next_slot += 1
        held = self._pick_from(above, pick)
        if not held:
            self._missed = (above, pick)
        return held

    def _pick_from(self, above: str, pick: str, pan: float = 0.0, retry: bool = False) -> bool:
        self._carrying = False  # the jaws open on the way to pick_above
        opening, depth = (RETRY_OPEN, 1.0 + DEEPER) if retry else (io.GRIPPER_OPEN, 1.0)
        if not (self._go(above, opening, pan) and self._slow(self._along(above, pick, depth, opening, pan))):
            return False
        self._close()
        # Read the servo itself: io.holding()'s camera check is what lets a tip grasp through.
        if io.observe()[io.GRIPPER] < io.GRIPPER_EMPTY_BELOW:
            self._set_gripper(opening)
            self._slow(self._along(above, pick, depth + DEEPER, opening, pan))
            self._close()
        self._carrying = True
        time.sleep(POST_CLOSE_S)
        return (self._slow(self._pose(above, GRIPPER_CLOSED, pan)) and self._go("inspect", GRIPPER_CLOSED)
                and self._settled_holding())

    def _along(self, above: str, pick: str, depth: float, gripper: float, pan: float) -> np.ndarray:
        start = self.poses[above]
        target = start + min(depth, MAX_DEPTH) * (self.poses[pick] - start)
        target[io.GRIPPER] = gripper
        target[SHOULDER_PAN] += pan
        return target

    def _close(self) -> None:
        time.sleep(PRE_CLOSE_S)
        self._set_gripper(GRIPPER_CLOSED)

    def place(self, instruction: str) -> bool:
        if not self._go(bowl_for(instruction), GRIPPER_CLOSED):
            return False
        time.sleep(BOWL_SETTLE_S)
        self._release()
        time.sleep(RELEASE_S)
        return bool(io.observe()[io.GRIPPER] >= io.GRIPPER_OPEN - io.POSE_TOLERANCE_DEG)

    def _release(self) -> None:
        self._set_gripper(io.GRIPPER_OPEN)
        self._carrying = False

    def reinspect(self, angle_deg: int) -> bool:
        if angle_deg == 0:
            if not self._go("pick_drop", GRIPPER_CLOSED):
                return False
            self._release()
            return self._pick_from("pick_above", "pick")  # pick_drop is the slot-1 spot; a re-grasp must not use up a slot
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

    def _pose(self, name: str, gripper: float, pan: float) -> np.ndarray:
        target = self.poses[name].copy()
        target[io.GRIPPER] = gripper
        target[SHOULDER_PAN] += pan
        return target

    def _go(self, name: str, gripper: float, pan: float = 0.0) -> bool:
        """Raise to home's height (pan unchanged), turn, then lower onto the pose: never swing across low."""
        target = self._pose(name, gripper, pan)
        if not self._near(target, ARRIVE_TOLERANCE_DEG):
            raised = io.observe()
            raised[LIFT_JOINTS] = self.poses["home"][LIFT_JOINTS]
            raised[io.GRIPPER] = gripper
            turned = raised.copy()
            turned[SHOULDER_PAN] = target[SHOULDER_PAN]
            if not (self._move(raised) and self._move(turned)):
                return False
        return self._move(target)

    def _slow(self, target: np.ndarray) -> bool:
        """Straight and slow: the moves between pick_above and the brick."""
        with step_cap(APPROACH_STEP_DEG):
            return self._move(target)

    def _move(self, target: np.ndarray) -> bool:
        """Step toward target until the arm joints arrive. The gripper is left out of the check: while
        carrying, it is commanded closed and the brick stops it short, which must not read as "stuck"."""
        with step_cap(CARRY_STEP_DEG if self._carrying else None):
            if not self._step_until(target, lambda: self._near(target, ARRIVE_TOLERANCE_DEG), self._seconds_for(target)):
                return False
            # Arrived counts from 4° out, more than a search shift or the last of a slow descent: send a few more
            # steps toward the exact pose without waiting for it (a loaded elbow settles ~2 units short for good).
            for _ in range(math.ceil(ARRIVE_TOLERANCE_DEG / io.MAX_STEP_DEG)):
                io.act(target)
                time.sleep(1 / io.CONTROL_HZ)
            return True

    @staticmethod
    def _seconds_for(target: np.ndarray) -> float:
        """Twice what the arm needs for this move at the current step cap, and never under MOVE_SECONDS."""
        distance = np.abs(np.clip(target, io.JOINT_MIN, io.JOINT_MAX) - io.observe())[:io.GRIPPER]
        speed = ARM_SPEED_PER_CAP * io.units(io.MAX_STEP_DEG)[:io.GRIPPER]
        return max(MOVE_SECONDS, 2 * float((distance / speed).max()))

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
