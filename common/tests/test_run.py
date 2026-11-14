import json
import time

import pytest
import yaml

import run
import telemetry
from common.capture import SharedCapture
from common.locate import CountLocator
from common.mocks import MockCamera, MockInspector, MockMover

RULES = yaml.safe_load((run.CONFIG / "rules.yaml").read_text())
VIEWS = {"top": "webcam", "inspect": "realsense", "wrist": "wrist"}


class StuckMover(MockMover):
    """Reinspect never gets the brick back to the inspection pose."""

    def reinspect(self, angle_deg):
        super().reinspect(angle_deg)
        return False


@pytest.fixture
def make_cell():
    captures = []

    def make(labels, bricks=1, mover=None):
        cap = SharedCapture({r: MockCamera(size=(8, 8), fps=200) for r in VIEWS}).start()
        captures.append(cap)
        mover = mover or MockMover()
        cell = run.Cell(cap, MockInspector(labels), mover, mover, CountLocator(bricks), RULES, VIEWS, "test")
        cell.pause_on_help = False  # these tests check the failure itself; test_help.py covers PAUSE_HUMAN
        return cell, mover

    yield make
    for cap in captures:
        cap.stop()


def places(mover):
    return [c[1] for c in mover.calls if c[0] == "place"]


def test_mock_run_sorts_five_bricks(make_cell):
    cell, mover = make_cell(("perfect", "defective", "perfect", "perfect", "defective"), bricks=5)
    cell.run()
    assert cell.sorted == 5
    assert places(mover) == [RULES[l] for l in ("perfect", "defective", "perfect", "perfect", "defective")]


def test_second_view_settles_uncertain_without_motion(make_cell):
    cell, mover = make_cell(("uncertain", "perfect"))
    cell.run()
    assert places(mover) == [RULES["perfect"]]
    assert not any(c[0] == "reinspect" for c in mover.calls)


def test_still_uncertain_rolls_then_regrasps_then_red_bowl(make_cell):
    cell, mover = make_cell(("uncertain",))
    cell.run()
    assert [c for c in mover.calls if c[0] == "reinspect"] == [("reinspect", 90), ("reinspect", 0)]
    assert places(mover) == [RULES["defective"]]


def test_look_again_scores_a_fresh_frame_from_the_inspection_camera(make_cell):
    class Recording(MockInspector):
        def __init__(self):
            super().__init__(("uncertain", "perfect"))
            self.seen = []

        def inspect(self, frame, view, brick_id):
            self.seen.append((view, frame))
            return super().inspect(frame, view, brick_id)

    cell, _ = make_cell(("uncertain", "perfect"))
    cell.inspector = Recording()
    cell.run()
    (view1, frame1), (view2, frame2) = cell.inspector.seen
    assert view1 == view2 == VIEWS["inspect"]
    assert frame2 is not frame1


def test_help_line_says_why(make_cell, monkeypatch):
    said = []
    monkeypatch.setattr(run.narrator, "say", lambda event, **kw: said.append((event, kw)))
    cell, _ = make_cell(("perfect",), mover=MockMover(pick_failures=2))
    with pytest.raises(run.HelpNeeded):
        cell.run()
    assert ("help", {"reason": "grasp_failed"}) in said


def test_grasp_retried_once(make_cell):
    cell, mover = make_cell(("perfect",), mover=MockMover(pick_failures=1))
    cell.run()
    assert cell.sorted == 1


def test_two_failed_grasps_stop_the_run_at_home(make_cell):
    cell, mover = make_cell(("perfect",), mover=MockMover(pick_failures=2))
    with pytest.raises(run.HelpNeeded):
        cell.run()
    assert mover.calls[-1] == ("home",)
    assert places(mover) == []


def test_lost_brick_on_reinspect_stops_the_run(make_cell):
    cell, mover = make_cell(("uncertain",), mover=StuckMover())
    with pytest.raises(run.HelpNeeded):
        cell.run()
    assert mover.calls[-1] == ("home",)


def test_every_stage_writes_an_events_row(make_cell, tmp_path):
    path = tmp_path / "events.jsonl"
    telemetry.start(path)
    cell, _ = make_cell(("perfect",))
    cell.run()
    telemetry.stop()
    rows = [json.loads(line) for line in path.read_text().splitlines()]
    assert [r["state"] for r in rows] == ["LOCATE", "PICK", "VERIFY_GRASP", "INSPECT", "DECIDE", "PLACE", "LOG", "LOCATE"]
    columns = {"run_id", "brick_id", "ts", "state", "label", "score", "device", "stage", "latency_ms", "outcome", "note"}
    assert all(set(r) == columns for r in rows)


def test_parse_scripted_rejects_unknown_parts():
    assert run.parse_scripted("pick,place") == {"pick", "place"}
    with pytest.raises(Exception):
        run.parse_scripted("pick,dance")
