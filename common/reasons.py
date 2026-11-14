"""Why the cell stopped to ask for help (decisions.md D22). One code per failure; each gets a spoken line (H3)
and goes into the `events` row's `outcome`, so the trial log counts failures by cause."""

from enum import Enum


class Reason(str, Enum):
    GRASP_FAILED = "grasp_failed"  # gripper empty after every pick attempt
    BRICK_LOST = "brick_lost"  # a reinspect motion didn't bring the brick back to the inspection pose
    PLACE_FAILED = "place_failed"  # the placer reported failure
    TIMEOUT = "timeout"  # a motion stage ran past its deadline
    CAMERA = "camera"  # no fresh frame from a camera in time
    INSPECT_FAILED = "inspect_failed"  # the inspector raised
    UNEXPECTED = "unexpected"  # anything else: a bug, logged with its traceback


class HelpNeeded(Exception):
    """The cell can't carry on without a person."""

    def __init__(self, reason: Reason, detail: str = ""):
        super().__init__(f"{reason.value}: {detail}" if detail else reason.value)
        self.reason = reason
