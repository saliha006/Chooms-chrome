"""E, P, Q and H: the flags the window sets and what the control thread does with them."""

import threading
import time

import numpy as np
import pytest
import yaml

import run
from common import estop
from common.capture import SharedCapture
from common.locate import CountLocator
from common.mocks import MockCamera, MockInspector, MockMover
from fallback.scripted import ScriptedMover
from robot import io
from ui import mission_control

RULES = yaml.safe_load((run.CONFIG / "rules.yaml").read_text())
VIEWS = {"top": "webcam", "inspect": "realsense", "wrist": "wrist"}


@pytest.fixture(autouse=True)
def clear_estop():
    estop.clear()
    yield
    estop.clear()


@pytest.fixture
def make_cell():
    captures = []

    def make(bricks=3, mover=None):
        cap = SharedCapture({r: MockCamera(size=(8, 8), fps=200) for r in VIEWS}).start()
        captures.append(cap)
        mover = mover or MockMover()
        return run.Cell(cap, MockInspector(("perfect",)), mover, mover, CountLocator(bricks), RULES, VIEWS, "t"), mover

    yield make
    for cap in captures:
        cap.stop()


class SlowMover(MockMover):
    """Each pick takes a moment, so a key can land mid-run."""

    def pick_and_present(self):
        time.sleep(0.05)
        return super().pick_and_present()


def test_estop_mid_run_torques_off_and_never_homes(make_cell):
    cell, mover = make_cell(bricks=50, mover=SlowMover())
    threading.Timer(0.1, estop.request).start()
    with pytest.raises(estop.EStopped):
        cell.run()
    assert mover.calls[-1] == ("estop",)
    assert ("home",) not in mover.calls
    assert cell.state == "E-STOP"


def test_quit_finishes_the_brick_then_homes(make_cell):
    cell, mover = make_cell(bricks=50, mover=SlowMover())
    threading.Timer(0.1, cell.quit.set).start()
    cell.run()
    assert 0 < cell.sorted < 50
    assert len([c for c in mover.calls if c[0] == "place"]) == cell.sorted  # no half-sorted brick
    assert mover.calls[-1] == ("home",) and cell.state == "DONE"


def test_pause_holds_at_a_stage_boundary(make_cell):
    cell, mover = make_cell(bricks=50, mover=SlowMover())
    cell.paused.set()
    worker = threading.Thread(target=cell.run, daemon=True)
    worker.start()
    time.sleep(0.2)
    assert mover.calls == []  # held before the first stage
    cell.paused.clear()
    time.sleep(0.2)
    cell.quit.set()
    worker.join(timeout=5)
    assert cell.sorted > 0


def test_scripted_move_stops_within_a_step_on_estop():
    io.connect(mock=True)
    try:
        far = np.array([100.0, 0, 0, 0, 0, 0])
        mover = ScriptedMover({"home": far})
        threading.Timer(0.1, estop.request).start()
        start = time.monotonic()
        with pytest.raises(estop.EStopped):
            mover.home()
        assert time.monotonic() - start < 0.5
        assert io.robot().torque is False
        assert io.observe()[0] < 100  # stopped part way
    finally:
        io.disconnect()


def test_keys_set_flags_only(make_cell):
    cell, mover = make_cell()
    control = mission_control.Control(cell)
    assert mission_control.handle_key(ord("p"), control) and cell.paused.is_set()
    mission_control.handle_key(ord("P"), control)
    assert not cell.paused.is_set()
    mission_control.handle_key(ord("e"), control)
    assert estop.requested() and mover.calls == []  # the window never touches the motors itself
    assert mission_control.handle_key(ord("q"), control) is False  # not running: Q closes


def test_s_starts_the_run_on_the_control_thread(make_cell):
    cell, _ = make_cell(bricks=2)
    control = mission_control.Control(cell)
    mission_control.handle_key(ord("s"), control)
    control.thread.join(timeout=5)
    assert control.thread.name == "control" and cell.sorted == 2 and control.error is None


def test_render_draws_every_state(make_cell):
    cell, _ = make_cell(bricks=1)
    control = mission_control.Control(cell)
    feed = np.zeros((480, 640, 3), np.uint8)
    assert mission_control.render(cell, control, feed).shape == (mission_control.HEIGHT, mission_control.WIDTH, 3)
    control.start()
    control.thread.join(timeout=5)
    img = mission_control.render(cell, control, None)  # after a brick: label, score, latencies
    assert img.shape == (mission_control.HEIGHT, mission_control.WIDTH, 3)


def test_render_shows_help_and_hold(make_cell):
    from common.reasons import Reason

    cell, _ = make_cell()
    control = mission_control.Control(cell)
    control.start()
    control.thread.join(timeout=5)
    cell.state, cell.help_reason = "PAUSE_HUMAN", Reason.GRASP_FAILED
    assert mission_control.render(cell, control, None).shape[0] == mission_control.HEIGHT
    cell.state = "HOLD"
    assert mission_control.render(cell, control, None).shape[0] == mission_control.HEIGHT
    cell.drift_alert = True
    assert mission_control.render(cell, control, None).shape[0] == mission_control.HEIGHT
