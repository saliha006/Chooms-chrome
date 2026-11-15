"""H1: reason codes, stage deadlines, PAUSE_HUMAN and the hold flag."""

import json
import threading
import time

import numpy as np
import pytest
import yaml

import run
import telemetry
from common import deadline, estop
from common.capture import SharedCapture
from common.locate import CountLocator
from common.mocks import MockCamera, MockInspector, MockMover
from common.reasons import HelpNeeded, Reason
from fallback.scripted import ScriptedMover
from robot import io

RULES = yaml.safe_load((run.CONFIG / "rules.yaml").read_text())
VIEWS = {"top": "webcam", "inspect": "realsense", "wrist": "wrist"}


@pytest.fixture(autouse=True)
def clean_flags():
    estop.clear()
    yield
    estop.clear()


@pytest.fixture
def make_cell():
    captures = []

    def make(mover=None, inspector=None, bricks=2, capture=None):
        cap = capture or SharedCapture({r: MockCamera(size=(8, 8), fps=200) for r in VIEWS}).start()
        captures.append(cap)
        mover = mover or MockMover()
        cell = run.Cell(cap, inspector or MockInspector(("perfect",)), mover, mover, CountLocator(bricks),
                        RULES, VIEWS, "t")
        return cell, mover

    yield make
    for cap in captures:
        cap.stop()


def run_in_background(cell):
    worker = threading.Thread(target=cell.run, daemon=True)
    worker.start()
    return worker


def wait_for(predicate, timeout=5.0):
    end = time.monotonic() + timeout
    while not predicate():
        assert time.monotonic() < end, "timed out waiting"
        time.sleep(0.01)


def test_failure_pauses_for_a_human_then_p_carries_on(make_cell):
    cell, mover = make_cell(mover=MockMover(pick_failures=2), bricks=2)
    worker = run_in_background(cell)
    wait_for(lambda: cell.state == "PAUSE_HUMAN")
    assert cell.help_reason is Reason.GRASP_FAILED
    assert mover.calls[-1] == ("home",)  # homed before waiting
    cell.paused.clear()  # P
    worker.join(timeout=5)
    assert cell.sorted == 1 and cell.state == "DONE"  # brick 1 skipped, brick 2 sorted


def test_q_during_pause_stops_at_home(make_cell):
    cell, mover = make_cell(mover=MockMover(pick_failures=2), bricks=3)
    worker = run_in_background(cell)
    wait_for(lambda: cell.state == "PAUSE_HUMAN")
    cell.quit.set()
    worker.join(timeout=5)
    assert cell.sorted == 0 and cell.state == "DONE" and mover.calls[-1] == ("home",)


def test_pause_row_carries_the_reason(make_cell, tmp_path):
    path = tmp_path / "events.jsonl"
    telemetry.start(path)
    cell, _ = make_cell(mover=MockMover(pick_failures=2), bricks=1)
    cell.pause_on_help = False
    with pytest.raises(HelpNeeded):
        cell.run()
    telemetry.stop()
    rows = [json.loads(line) for line in path.read_text().splitlines()]
    pause = [r for r in rows if r["state"] == "PAUSE_HUMAN"]
    assert len(pause) == 1 and pause[0]["outcome"] == "grasp_failed"


class StuckMover(MockMover):
    """A pick that never finishes on its own; it only returns when the stage deadline fires."""

    def pick_and_present(self):
        self.calls.append(("pick_and_present",))
        deadline.abort.wait(5)
        return False


def test_stuck_pick_ends_as_timeout_without_retry(make_cell, monkeypatch):
    monkeypatch.setitem(run.DEADLINE_S, "PICK", 0.1)
    cell, mover = make_cell(mover=StuckMover(), bricks=1)
    cell.pause_on_help = False
    start = time.monotonic()
    with pytest.raises(HelpNeeded) as err:
        cell.run()
    assert err.value.reason is Reason.TIMEOUT
    assert time.monotonic() - start < 2
    assert mover.calls.count(("pick_and_present",)) == 1


def test_silent_camera_is_a_camera_reason(make_cell):
    class SilentCapture:
        def frame(self, role, newer_than=0.0, timeout_s=1.0):
            raise TimeoutError(role)

        def stop(self):
            pass

    cell, _ = make_cell(capture=SilentCapture(), bricks=1)
    cell.pause_on_help = False
    with pytest.raises(HelpNeeded) as err:
        cell.run()
    assert err.value.reason is Reason.CAMERA


def test_inspector_crash_is_inspect_failed(make_cell):
    class Broken(MockInspector):
        def inspect(self, frame, view, brick_id):
            raise RuntimeError("NPU fell over")

    cell, _ = make_cell(inspector=Broken(), bricks=1)
    cell.pause_on_help = False
    with pytest.raises(HelpNeeded) as err:
        cell.run()
    assert err.value.reason is Reason.INSPECT_FAILED


def test_a_bug_is_unexpected_and_still_pauses(make_cell):
    class Buggy(MockMover):
        def place(self, instruction):
            raise KeyError("oops")

    cell, _ = make_cell(mover=Buggy(), bricks=1)
    worker = run_in_background(cell)
    wait_for(lambda: cell.state == "PAUSE_HUMAN")
    assert cell.help_reason is Reason.UNEXPECTED
    cell.quit.set()
    worker.join(timeout=5)


def test_hold_waits_outlasts_q_and_resumes_when_clear(make_cell, monkeypatch):
    triggers = []
    monkeypatch.setattr(run.narrator, "trigger", triggers.append)
    cell, mover = make_cell(bricks=1)
    cell.hold.set()
    worker = run_in_background(cell)
    wait_for(lambda: cell.state == "HOLD")
    cell.quit.set()  # Q must not move the arm into an obstacle
    time.sleep(0.2)
    assert mover.calls == [] and triggers == ["obstacle"]
    cell.hold.clear()
    worker.join(timeout=5)
    assert cell.state == "DONE" and mover.calls[-1] == ("home",)


def test_estop_beats_pause(make_cell):
    cell, mover = make_cell(mover=MockMover(pick_failures=2), bricks=2)
    raised = []

    def control():
        try:
            cell.run()
        except estop.EStopped as exc:
            raised.append(exc)

    worker = threading.Thread(target=control, daemon=True)
    worker.start()
    wait_for(lambda: cell.state == "PAUSE_HUMAN")
    estop.request()
    worker.join(timeout=5)
    assert raised and cell.state == "E-STOP" and mover.calls[-1] == ("estop",)


def test_deadline_stops_a_scripted_move():
    io.connect(mock=True)
    try:
        mover = ScriptedMover({"home": np.array([100.0, 0, 0, 0, 0, 0])})
        with deadline.armed(0.1):
            assert mover._go("home", 0.0) is False
        assert 0 < io.observe()[0] < 100
        assert not deadline.expired()  # cleared on exit
    finally:
        io.disconnect()


def test_a_drive_that_runs_out_of_time_pauses_then_p_sorts_from_where_it_parked(make_cell, monkeypatch, tmp_path):
    from robot import drive

    monkeypatch.setattr(drive, "DEMO_STROKE", tmp_path / "no_stroke.yaml")  # the station's learned stroke stays out
    monkeypatch.setitem(run.DEADLINE_S, "DRIVE", 0.2)
    seen = drive.tag_image(dpi=50)  # the tag in view, never any nearer the dock
    dock = drive.TagPose(x_px=5000.0, y_px=0.0, heading_deg=0.0, side_px=200.0)
    stroke = {name: np.full(6, 10.0 * i) for i, name in enumerate(drive.STROKE)}
    io.connect(mock=True)
    try:
        cell, mover = make_cell(bricks=2)
        cell.approach = lambda: drive.approach(lambda: seen, dock, stroke)
        worker = run_in_background(cell)
        wait_for(lambda: cell.state == "PAUSE_HUMAN")
        assert cell.help_reason is Reason.TIMEOUT
        assert mover.calls == [("home",)]  # homed, and nothing picked while it waits
        cell.paused.clear()  # P
        worker.join(timeout=5)
        assert cell.sorted == 2 and cell.state == "DONE"
    finally:
        io.disconnect()
