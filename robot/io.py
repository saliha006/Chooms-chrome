"""The one door to the SO-101 follower, shared by policies/ and fallback/ (PRD 7.3).

    from robot import io
    io.connect(port="/dev/ttyACM0", calibration="config/so101_follower.json")   # or io.connect(mock=True)
    joints = io.observe()            # (6,) degrees, last = gripper (0-100)
    io.act(target)                   # one step toward target, clipped to joint limits and the speed cap
    io.move_to(home, seconds=2.0)    # interpolated, blocking
    io.torque_off()                  # E key: arm goes limp

Uses the physicalai SO-101 driver (OpenVINO Physical AI runtime, R5). Only the follower is ever
connected here; the leader is teleop only and never driven (PRD §0).
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

# Joint limits from physicalai_so101_plugin 0.3.0 (degrees; gripper 0-100). Safety, PRD §9.
JOINT_MIN = np.array([-110.0, -100.0, -97.0, -95.0, -157.0, 0.0])
JOINT_MAX = np.array([110.0, 100.0, 97.0, 95.0, 163.0, 100.0])
MAX_STEP_DEG = 5.0  # speed cap: largest change per joint per act() call (150 deg/s at 30 Hz). TUNE with the arm watched

# Shared by the learned and scripted movers, so a tune on the arm changes one place. TUNE (PRD v2.5 N8).
POSE_TOLERANCE_DEG = 8.0  # how close counts as "at the inspection pose"
GRIPPER_EMPTY_BELOW = 5.0  # F5: a fully closed gripper (0-100) means nothing is in it
GRIPPER_OPEN = 60.0  # opening used to release a brick
CONTROL_HZ = 30


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


def connect(port: str | None = None, calibration: str | None = None, mock: bool = False) -> None:
    global _robot
    if mock:
        _robot = MockRobot()
    else:
        from physicalai.robot.so101 import SO101  # hardware import stays out of mock runs and tests

        _robot = SO101(port, calibration=calibration, role="follower", unit="degrees")
    _robot.connect()


def robot():
    if _robot is None:
        raise RuntimeError("robot.io.connect() first")
    return _robot


def observe() -> np.ndarray:
    return np.asarray(robot().get_observation().joint_positions, float)


def clamp_step(current: np.ndarray, target: np.ndarray) -> np.ndarray:
    """The next command toward target: inside joint limits, no joint moving more than MAX_STEP_DEG."""
    target = np.clip(np.asarray(target, float), JOINT_MIN, JOINT_MAX)
    return current + np.clip(target - current, -MAX_STEP_DEG, MAX_STEP_DEG)


def act(target: np.ndarray) -> np.ndarray:
    """Send one capped step toward target; returns the command actually sent."""
    if estop.requested():
        torque_off()
        raise estop.EStopped()
    command = clamp_step(observe(), target)
    robot().send_action(command, goal_time=1 / CONTROL_HZ)
    return command


def move_to(target: np.ndarray, seconds: float = 2.0, tolerance_deg: float = 2.0) -> bool:
    """Step toward target at CONTROL_HZ until within tolerance or the time runs out. True if reached."""
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        if np.abs(observe() - np.clip(target, JOINT_MIN, JOINT_MAX)).max() <= tolerance_deg:
            return True
        act(target)
        time.sleep(1 / CONTROL_HZ)
    return bool(np.abs(observe() - np.clip(target, JOINT_MIN, JOINT_MAX)).max() <= tolerance_deg)


def torque_off() -> None:
    robot().set_torque(enabled=False)


def disconnect() -> None:
    global _robot
    if _robot is not None:
        _robot.disconnect()
        _robot = None
