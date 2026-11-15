"""The one door to the SO-101 follower, shared by policies/ and fallback/ (PRD 7.3).

    from robot import io
    io.connect(port="/dev/ttyACM0", calibration="config/so101_follower.json")   # or io.connect(mock=True)
    joints = io.observe()            # (6,) normalized: arm joints -100..100 over each calibrated range, gripper 0-100
    io.act(target)                   # one step toward target, clipped to joint limits and the speed cap
    io.move_to(home, seconds=2.0)    # interpolated, blocking
    io.torque_off()                  # E key: arm goes limp

Uses the physicalai SO-101 driver (OpenVINO Physical AI runtime, R5). Only the follower is ever
connected here; the leader is teleop only and never driven (PRD §0).
Joints run in Studio's normalized unit, the convention most SO-101 datasets use (decisions.md D29, changed
2026-11-14). Safety numbers stay in degrees and are converted per joint with `units()`, so "5 degrees per step"
means the same angle on every joint whatever its calibrated range.
Once the E key has requested a stop (`common.estop`, D21), `act()` turns the torque off and raises
`EStopped`, so no motion path, learned or scripted, runs past it.
"""

import time
from dataclasses import dataclass

import numpy as np

from common import estop

JOINTS = ("shoulder_pan", "shoulder_lift", "elbow_flex", "wrist_flex", "wrist_roll", "gripper")
WRIST_ROLL = JOINTS.index("wrist_roll")
GRIPPER = JOINTS.index("gripper")

# Normalized limits = the calibrated range of each joint (gripper 0-100). Safety, PRD §9.
JOINT_MIN = np.array([-100.0, -100.0, -100.0, -100.0, -100.0, 0.0])
JOINT_MAX = np.array([100.0, 100.0, 100.0, 100.0, 100.0, 100.0])
MAX_STEP_DEG = 7.0  # speed cap: largest change per joint per act() call (210 deg/s at 30 Hz); raised from 5 at the station (Saliha, 06:40)
TICKS_PER_DEGREE = 4095 / 360  # the driver's own degree convention

# Shared by the learned and scripted movers, so a tune on the arm changes one place. TUNE (PRD v2.5 N8).
POSE_TOLERANCE_DEG = 8.0  # how close counts as "at the inspection pose"
GRIPPER_EMPTY_BELOW = 10.0  # F5: shut on nothing averages 1.5 (1.0-2.4), a Duplo brick 17.4 (15.2-19.8); N8, 3 runs, 2026-11-14
GRIPPER_HOLD_MAX = 23.0  # above this it is open, not holding: half open averages 29.4 (25.7-31.8), wide 96.3; midway from the brick max 19.8
GRIPPER_SETTLE_S = 0.3  # a held brick stops swinging after this long; read the band only then (decisions.md D22)
GRIPPER_OPEN = 60.0  # opening used to release a brick
CONTROL_HZ = 30
OBSERVE_RETRIES = 4  # extra reads after a failed one, OBSERVE_RETRY_S apart (~0.2 s in all)
OBSERVE_RETRY_S = 0.05


@dataclass
class MockObservation:
    joint_positions: np.ndarray
    timestamp: float


class MockRobot:
    """Same surface as physicalai's SO101, for runs without hardware. Joints jump to the commanded target."""

    def __init__(self, start: np.ndarray | None = None):
        self.joints = np.zeros(len(JOINTS)) if start is None else np.asarray(start, float).copy()
        self.connected = False
        self.torque = False
        self.commands: list[np.ndarray] = []

    def connect(self) -> None:
        self.connected, self.torque = True, True

    def disconnect(self) -> None:
        self.connected = False

    def is_connected(self) -> bool:
        return self.connected

    def get_observation(self) -> MockObservation:
        return MockObservation(self.joints.copy(), time.monotonic())

    def send_action(self, action: np.ndarray, *, goal_time: float = 0.1) -> None:
        if self.torque:
            self.joints = np.asarray(action, float).copy()
        self.commands.append(self.joints.copy())

    def set_torque(self, *, enabled: bool) -> None:
        self.torque = enabled


_robot = None
_per_degree = np.ones(len(JOINTS))  # normalized units per degree, from the calibration; the mock runs 1:1


def units(degrees: float) -> np.ndarray:
    """A size in degrees as normalized units for each joint (the gripper is a 0-100 percentage either way)."""
    return degrees * _per_degree


def per_degree(calibration_path: str) -> np.ndarray:
    """Normalized units per degree for each joint: 200 units span the calibrated range of an arm joint."""
    from physicalai.robot.so101 import SO101Calibration

    cal = SO101Calibration.from_path(calibration_path).joints
    spans = np.array([cal[name].range_max - cal[name].range_min for name in JOINTS[:GRIPPER]], float)
    return np.append(200.0 * TICKS_PER_DEGREE / spans, 1.0)


def connect(port: str | None = None, calibration: str | None = None, mock: bool = False) -> None:
    global _robot, _per_degree
    if mock:
        _robot, _per_degree = MockRobot(), np.ones(len(JOINTS))
    else:
        if calibration is None:
            raise ValueError("the follower needs its calibration file: normalized units and the speed cap come from it")
        from physicalai.robot.so101 import SO101  # hardware import stays out of mock runs and tests

        _per_degree = per_degree(calibration)
        _robot = SO101(port, calibration=calibration, role="follower", unit="normalized")
    _robot.connect()


def robot():
    if _robot is None:
        raise RuntimeError("robot.io.connect() first")
    return _robot


def observe() -> np.ndarray:
    # A knock on the arm dips the servo supply for tens of ms and the driver's own quick retries all land inside
    # the dip (Studio logged `comm result -6` this way); waiting a little rides through it, a dead bus still raises.
    for _ in range(OBSERVE_RETRIES):
        try:
            return np.asarray(robot().get_observation().joint_positions, float)
        except ConnectionError:
            time.sleep(OBSERVE_RETRY_S)
    return np.asarray(robot().get_observation().joint_positions, float)


def holding() -> bool:
    """A brick is in the gripper: closed on something, not on nothing and not open."""
    return bool(GRIPPER_EMPTY_BELOW <= observe()[GRIPPER] <= GRIPPER_HOLD_MAX)


def clamp_step(current: np.ndarray, target: np.ndarray) -> np.ndarray:
    """The next command toward target: inside joint limits, no joint moving more than MAX_STEP_DEG."""
    target = np.clip(np.asarray(target, float), JOINT_MIN, JOINT_MAX)
    step = units(MAX_STEP_DEG)
    return current + np.clip(target - current, -step, step)


def act(target: np.ndarray) -> np.ndarray:
    """Send one capped step toward target; returns the command actually sent."""
    if estop.requested():
        torque_off()
        raise estop.EStopped()
    command = clamp_step(observe(), target)
    robot().send_action(command, goal_time=1 / CONTROL_HZ)
    return command


def within(target: np.ndarray, tolerance_deg: float) -> np.ndarray:
    """Per joint: is the arm within tolerance_deg of target (the target clipped to the joint limits)?"""
    return np.abs(observe() - np.clip(target, JOINT_MIN, JOINT_MAX)) <= units(tolerance_deg)


def move_to(target: np.ndarray, seconds: float = 2.0, tolerance_deg: float = 2.0) -> bool:
    """Step toward target at CONTROL_HZ until within tolerance or the time runs out. True if reached."""
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        if within(target, tolerance_deg).all():
            return True
        act(target)
        time.sleep(1 / CONTROL_HZ)
    return bool(within(target, tolerance_deg).all())


def torque_off() -> None:
    robot().set_torque(enabled=False)


def disconnect() -> None:
    global _robot
    if _robot is not None:
        _robot.disconnect()
        _robot = None
