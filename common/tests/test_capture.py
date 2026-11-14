import time

import pytest

from common.capture import SharedCapture
from common.mocks import MockCamera


@pytest.fixture
def capture():
    cap = SharedCapture({"top": MockCamera(size=(8, 8), fps=200), "inspect": MockCamera(size=(8, 8), fps=200)}).start()
    yield cap
    cap.stop()


def test_consumers_share_one_grab():
    cap = SharedCapture({"top": MockCamera(size=(8, 8), fps=2)}).start()
    try:
        policy_frame = cap.frame("top", timeout_s=2)
        inspector_frame = cap.frame("top")
        # Between two camera frames, the policy and the inspector get the very same array.
        assert inspector_frame is policy_frame
        assert cap.grabs["top"] == 1
    finally:
        cap.stop()


def test_reads_do_not_drive_grabs(capture):
    capture.frame("top")
    before = dict(capture.grabs)
    for _ in range(50):
        capture.frame("top")
        capture.frame("inspect")
    after = dict(capture.grabs)
    # 100 reads cost no more grabs than the cameras' own frame rate produced in that time.
    assert after["top"] - before["top"] < 50


def test_frame_waits_for_one_newer_than_the_stamp(capture):
    capture.frame("inspect")
    stamp = time.monotonic()
    frame = capture.frame("inspect", newer_than=stamp)
    assert frame is not None


def test_frame_times_out_when_camera_is_silent():
    cap = SharedCapture({"top": MockCamera(size=(8, 8), fps=1)}).start()
    try:
        cap.frame("top", timeout_s=2)
        with pytest.raises(TimeoutError):
            cap.frame("top", newer_than=time.monotonic(), timeout_s=0.05)
    finally:
        cap.stop()
