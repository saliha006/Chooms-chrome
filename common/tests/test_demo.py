"""The demo's moments, end to end on the stand-ins, checked by what Pix says (the narrator's console line) and shows."""

import json
import logging
import sys
import time

import numpy as np
import pytest
import yaml

import narrator
import run
import telemetry
from common import estop
from common.capture import SharedCapture
from common.locate import CountLocator
from common.mocks import MockCamera, MockInspector, MockMover
from fallback import scripted
from narrator.persona import Persona
from robot import io
from ui import mission_control

RULES = yaml.safe_load((run.CONFIG / "rules.yaml").read_text())
VIEWS = {"top": "webcam", "inspect": "realsense", "wrist": "wrist"}


@pytest.fixture(autouse=True)
def fresh_robot_state(monkeypatch):
    estop.clear()
    monkeypatch.setattr(narrator, "_persona", Persona(narrator.say))  # every test starts calm, hat off
    yield
    estop.clear()


@pytest.fixture
def spoken(caplog):
    """Everything Pix said so far, as (persona, line)."""
    caplog.set_level(logging.INFO, logger="narrator")

    def lines():
        said = [r.getMessage() for r in caplog.records if r.name == "narrator" and r.getMessage().startswith("[")]
        return [tuple(m[1:].split("] ", 1)) for m in said]

    return lines


@pytest.fixture
def make_cell():
    captures = []

    def make(labels=("perfect",), bricks=1, mover=None):
        cap = SharedCapture({r: MockCamera(size=(8, 8), fps=200) for r in VIEWS}).start()
        captures.append(cap)
        mover = mover or MockMover()
        cell = run.Cell(cap, MockInspector(labels), mover, mover, CountLocator(bricks), RULES, VIEWS, "demo")
        return cell, mover

    yield make
    for cap in captures:
        cap.stop()


def wait_for(predicate, timeout=5.0):
    end = time.monotonic() + timeout
    while not predicate():
        assert time.monotonic() < end, "timed out waiting"
        time.sleep(0.01)


def said(lines, text):
    return any(text in line for _, line in lines)


def test_uncertain_brick_settled_by_a_second_look(make_cell, spoken):
    cell, mover = make_cell(("uncertain", "perfect"))
    cell.run()
    lines = [line for _, line in spoken()]
    assert not any(c[0] == "reinspect" for c in mover.calls)
    assert mover.calls[-2] == ("place", RULES["perfect"])
    # The placing line quotes the look that settled it, not the uncertain first look.
    assert "Heading to the purple bowl: it scored 0.20, under my limit of 0.40." in lines
    assert lines.index("Heading to the purple bowl: it scored 0.20, under my limit of 0.40.") < lines.index(
        "It's in the purple bowl.")
    assert cell.tally == {"perfect": 1, "defective": 0, "rechecked": 1}


def test_still_uncertain_goes_to_orange_said_as_playing_safe(make_cell, spoken):
    cell, mover = make_cell(("uncertain",))
    cell.run()
    assert mover.calls[-2] == ("place", RULES["defective"])
    assert said(spoken(), "Still unsure after looking again, so it goes to the orange bowl to be safe.")
    assert not said(spoken(), "over my limit")


def test_two_missed_grasps_ask_for_a_hand_then_p_carries_on(make_cell, spoken):
    cell, mover = make_cell(bricks=2, mover=MockMover(pick_failures=2))
    control = mission_control.Control(cell)
    mission_control.handle_key(ord("s"), control)
    wait_for(lambda: cell.state == "PAUSE_HUMAN")
    lines = [line for _, line in spoken()]
    assert "Missed it. In my defence, it's very small. Again." in lines
    assert lines[-1].startswith("I can't get a grip on that brick, and I've tried twice.")
    assert mover.calls[-1] == ("home",)
    mission_control.render(cell, control, None)  # the banner: NEED HELP: grasp failed (P go on, Q stop)
    mission_control.handle_key(ord("p"), control)
    control.thread.join(timeout=5)
    assert control.error is None and cell.state == "DONE" and cell.sorted == 1


def test_something_in_the_zone_gets_the_cowboy_once_and_is_never_picked(make_cell, spoken, tmp_path):
    class MugInTheZone(CountLocator):
        obstacles = ["mug"]

    cell, mover = make_cell(bricks=2)
    cell.locator = MugInTheZone(2)
    telemetry.start(tmp_path / "events.jsonl")
    cell.run()
    telemetry.stop()
    exclaims = [line for _, line in spoken() if line.startswith("Holy smokes! There ain't enough room")]
    assert len(exclaims) == 1 and spoken()[0] == ("cowboy", exclaims[0])
    assert sum(c[0] == "pick_and_present" for c in mover.calls) == 2  # only the two bricks
    rows = [json.loads(line) for line in (tmp_path / "events.jsonl").read_text().splitlines()]
    assert all(r["note"] == "1 non-brick object(s) in the zone, skipped" for r in rows if r["state"] == "LOCATE")


def test_h_puts_the_hat_on_and_takes_it_off(make_cell, spoken):
    cell, _ = make_cell()
    control = mission_control.Control(cell)
    mission_control.handle_key(ord("h"), control)
    assert spoken()[-1] == ("cowboy", narrator.lines.line_for("cowboy", "hat_on"))
    assert narrator.subtitle()[1] == "cowboy"
    cell.run()
    assert ("cowboy", narrator.lines.line_for("cowboy", "first")) in spoken()  # the hat stays on through a brick
    mission_control.handle_key(ord("h"), control)
    assert spoken()[-1] == ("calm", narrator.lines.line_for("calm", "hat_off"))
    assert narrator.current_persona() == "calm"


class EStopWhilePlacing(scripted.ScriptedMover):
    """The real scripted mover: E is pressed while the arm carries the brick to the bowl."""

    def place(self, instruction):
        estop.request()
        return super().place(instruction)


POSES = {
    "home": [0, 0, 0, 0, 0, 0], "pick_above": [10, 5, 0, 0, 0, 60], "pick": [10, 15, 0, 0, 0, 60],
    "pick_drop": [10, 15, 0, 0, 0, 60], "inspect": [-5, 5, 5, 0, 0, 0],
    "bowl_red": [-15, 5, 0, 0, 0, 0], "bowl_blue": [20, 5, 0, 0, 0, 0],
}


class BrickRobot(io.MockRobot):
    def send_action(self, action, *, goal_time=0.1):
        action = np.asarray(action, float).copy()
        action[io.GRIPPER] = max(action[io.GRIPPER], 17.0)
        super().send_action(action, goal_time=goal_time)


@pytest.fixture
def arm():
    io.connect(mock=True)
    io._robot = BrickRobot()
    io._robot.connect()
    yield io._robot
    io.disconnect()


def test_estop_mid_place_cuts_torque_and_never_homes(make_cell, spoken, arm, tmp_path):
    mover = EStopWhilePlacing({k: np.asarray(v, float) for k, v in POSES.items()})
    cell, _ = make_cell(mover=mover)
    telemetry.start(tmp_path / "events.jsonl")
    with pytest.raises(estop.EStopped):
        cell.run()
    telemetry.stop()
    assert cell.state == "E-STOP" and not arm.torque
    assert spoken()[-1] == ("calm", "Emergency stop. Motors off.")
    rows = [json.loads(line) for line in (tmp_path / "events.jsonl").read_text().splitlines()]
    assert rows[-1]["state"] == "PLACE" and rows[-1]["outcome"] == "e-stop"  # no HOME, no LOG after it
    assert cell.sorted == 0


def test_empty_zone_says_the_summary_then_dances_then_homes(make_cell, spoken):
    order = []
    cell, mover = make_cell(("perfect", "defective"), bricks=2)
    cell.finale = lambda: order.append(("dance", spoken()[-1][1], len(mover.calls)))
    cell.run()
    lines = [line for _, line in spoken()]
    assert lines.index(narrator.lines.line_for("calm", "empty")) < lines.index(narrator.lines.line_for("calm", "dance"))
    assert order == [("dance", narrator.lines.line_for("calm", "dance"), len(mover.calls) - 1)]
    assert mover.calls[-1] == ("home",) and cell.state == "DONE"
    assert cell.tally == {"perfect": 1, "defective": 1, "rechecked": 0}


def test_a_brick_off_its_spot_is_found_by_the_slot_search(make_cell, spoken):
    from fallback.tests.test_scripted import OffSpotRobot, search_mover

    io.connect(mock=True)
    io._robot = OffSpotRobot(10 + float(np.degrees(1.5 / scripted.REACH_CM)))
    io._robot.connect()
    try:
        cell, _ = make_cell(mover=search_mover(1.5))
        cell.pause_on_help = False
        cell.run()
    finally:
        io.disconnect()
    assert cell.sorted == 1
    assert said(spoken(), "Missed it.") and not said(spoken(), "I can't get a grip")


def test_mock_drive_opens_the_run(monkeypatch, tmp_path, spoken):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(run, "MOCK_DRIVE_S", 0.0)
    monkeypatch.setattr(sys, "argv", ["run.py", "--mock", "--headless", "--no-listen", "--no-live",
                                      "--drive", "41", "--bricks", "2"])
    run.main()
    lines = [line for _, line in spoken()]
    assert lines[0] == narrator.lines.line_for("calm", "drive")
    assert lines[1] == narrator.lines.line_for("calm", "arrived")
    rows = [json.loads(line) for line in (tmp_path / "runs/mock-events.jsonl").read_text().splitlines()]
    drive = next(r for r in rows if r["state"] == "DRIVE")
    assert drive["outcome"] == "arrived" and drive["note"] == "41 cm planned; 41.0 cm travelled"
    assert sum(r["state"] == "LOG" for r in rows) == 2
