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
    # ENERGY only appears where RAPL is readable (the Intel laptop, not a dev PC)
    assert [r["state"] for r in rows if r["state"] != "ENERGY"] == ["LOCATE", "PICK", "VERIFY_GRASP", "INSPECT", "DECIDE", "PLACE", "LOG", "LOCATE"]
    columns = {"run_id", "brick_id", "ts", "state", "label", "score", "device", "stage", "latency_ms", "outcome", "note"}
    assert all(set(r) == columns for r in rows)


def test_parse_scripted_rejects_unknown_parts():
    assert run.parse_scripted("pick,place") == {"pick", "place"}
    with pytest.raises(Exception):
        run.parse_scripted("pick,dance")


def test_trace_records_the_whole_chain_for_the_panel(make_cell):
    cell, _ = make_cell(("uncertain",))
    cell.run()
    steps = [line.split(":")[0] for line in cell.trace]
    assert steps == ["first look", "look again", "after wrist roll 90", "after re-grasp", "still unsure", "decision"]
    assert cell.trace[-1] == f"decision: {RULES['defective']}"


def test_trace_starts_fresh_for_each_brick(make_cell):
    cell, _ = make_cell(("perfect",), bricks=2)
    cell.run()
    assert cell.trace == ["first look: 0.2 vs 0.4 / 0.7 -> perfect", f"decision: {RULES['perfect']}"]


def test_trace_says_why_help_was_needed(make_cell):
    cell, _ = make_cell(("perfect",), mover=MockMover(pick_failures=2))
    with pytest.raises(run.HelpNeeded):
        cell.run()
    assert cell.trace == ["needs help: grasp failed"]


def test_log_row_carries_the_reason_trace(make_cell, tmp_path):
    path = tmp_path / "events.jsonl"
    telemetry.start(path)
    cell, _ = make_cell(("uncertain", "uncertain", "defective"))
    cell.run()
    telemetry.stop()
    log_row = next(json.loads(line) for line in path.read_text().splitlines() if json.loads(line)["state"] == "LOG")
    assert log_row["note"] == "defective: score 0.9 vs 0.4/0.7 (margin +0.2) | look again 0.6 > after wrist roll 90 0.9"


def test_obstacle_noticed_once_while_it_stays(make_cell, monkeypatch):
    triggers = []
    monkeypatch.setattr(run.narrator, "trigger", triggers.append)

    class Cluttered(CountLocator):
        obstacles = ["hand"]

    cell, _ = make_cell(("perfect",), bricks=3)
    cell.locator = Cluttered(3)
    cell.run()
    assert triggers == ["obstacle"] and cell.sorted == 3


def test_dance_only_after_an_empty_zone(make_cell):
    danced = []
    cell, mover = make_cell(("perfect",), bricks=2)
    cell.finale = lambda: danced.append(True)
    cell.run()
    assert danced == [True] and mover.calls[-1] == ("home",)

    cell, _ = make_cell(("perfect",), bricks=5)
    cell.finale = lambda: danced.append(True)
    cell.quit.set()
    cell.run()
    assert danced == [True]  # Q: no dance


def test_place_is_checked_from_home_against_a_frame_from_before_the_pick(make_cell):
    cell, mover = make_cell(("defective",))
    seen = []

    def check(instruction, before, after):
        seen.append((instruction, mover.calls[-1]))
        return True

    cell.bowl_check = check
    cell.run()
    assert cell.sorted == 1
    assert seen == [(RULES["defective"], ("home",))]  # the arm was home when the bowl was looked at


def test_brick_missing_from_the_bowl_is_place_failed(make_cell):
    cell, mover = make_cell(("perfect",))
    cell.bowl_check = lambda instruction, before, after: False
    with pytest.raises(run.HelpNeeded) as err:
        cell.run()
    assert err.value.reason is run.Reason.PLACE_FAILED
    assert cell.sorted == 0


def test_no_clicked_bowls_means_no_place_check():
    assert run.bowl_checker({"zone": None, "bowl_red": None, "bowl_blue": None}) is None


def test_bowl_checker_looks_only_at_the_named_bowl():
    import numpy as np

    square = lambda x: [[x, 0], [x + 10, 0], [x + 10, 10], [x, 10]]
    check = run.bowl_checker({"bowl_red": square(0), "bowl_blue": square(20)})
    before = np.zeros((10, 40, 3), np.uint8)
    after = before.copy()
    after[:, 0:10] = 255  # a brick appears in the red-role bowl only
    assert check(RULES["defective"], before, after)  # orange bowl = bowl_red
    assert not check(RULES["perfect"], before, after)  # purple bowl = bowl_blue, unchanged


def test_cowboy_returns_to_calm_once_the_obstacle_has_gone_and_a_brick_is_done(make_cell, monkeypatch):
    from narrator.persona import Persona

    said = []
    persona = Persona(lambda event, persona=None, **kw: said.append((persona, event)))
    monkeypatch.setattr(run.narrator, "trigger", persona.trigger)
    monkeypatch.setattr(run.narrator, "clear", persona.clear)
    monkeypatch.setattr(run.narrator, "brick_done", persona.brick_done)

    class HandThenGone(CountLocator):
        looks = 0

        @property
        def obstacles(self):
            self.looks += 1
            return ["hand"] if self.looks == 1 else []

    cell, _ = make_cell(("perfect",), bricks=3)
    cell.locator = HandThenGone(3)
    cell.run()
    assert said == [("cowboy", "obstacle"), ("calm", "halfway")]
    assert persona.current == "calm"


def test_mock_runs_never_raise_the_drift_alarm(make_cell):
    cell, _ = make_cell(("perfect",))
    assert run.drift_alarm(cell, "mock-20261114") is None


def test_every_inspection_goes_to_the_reasoner_with_its_frame(make_cell):
    seen = []

    class Reasoner:
        def submit(self, crop, signal, persona="calm"):
            seen.append((crop.shape, signal.label, persona))

    cell, _ = make_cell(("uncertain", "perfect"))
    cell.reasoner = Reasoner()
    cell.run()
    assert [label for _, label, _ in seen] == ["uncertain", "perfect"]
    assert all(shape == (8, 8, 3) and persona == "calm" for shape, _, persona in seen)


def test_run_summary_gets_the_tally(make_cell, monkeypatch):
    said = []
    monkeypatch.setattr(run.narrator, "say", lambda event, **kw: said.append((event, kw)))
    cell, _ = make_cell(("perfect", "defective", "uncertain", "perfect"), bricks=3)
    cell.run()
    assert said[-1] == ("empty", {"n": 3, "perfect": 2, "defective": 1, "rechecked": 1})


def test_the_base_drives_first_and_is_talked_over(make_cell, monkeypatch):
    said = []
    monkeypatch.setattr(run.narrator, "say", lambda event, **kw: said.append((event, kw)))
    cell, mover = make_cell(("perfect",))
    cell.approach_cm = 42.0
    cell.approach = lambda: (said.append(("driving", {})), 41.0)[1]
    cell.run()
    events = [event for event, _ in said]
    assert events[:3] == ["drive", "driving", "arrived"]
    assert said[0][1] == {"cm": 42.0} and said[2][1]["cm"] == 41.0 and "seconds" in said[2][1]
    assert cell.sorted == 1


def test_a_failed_drive_asks_for_help_before_any_pick(make_cell):
    cell, mover = make_cell(("perfect",))
    cell.approach = lambda: None
    with pytest.raises(run.HelpNeeded) as err:
        cell.run()
    assert err.value.reason is run.Reason.DRIVE_FAILED
    assert not any(call[0] == "pick_and_present" for call in mover.calls)


def test_no_base_means_no_drive_stage(make_cell, tmp_path):
    events = tmp_path / "events.jsonl"
    telemetry.start(events)
    cell, _ = make_cell(("perfect",))
    cell.run()
    telemetry.stop()
    assert "DRIVE" not in events.read_text()


def test_a_new_obstacle_is_sent_to_the_namer_once(make_cell, monkeypatch):
    monkeypatch.setattr(run.narrator, "trigger", lambda kind: None)
    sent = []

    class Namer:
        def submit(self, grab, box=None):
            sent.append((grab().shape, box))

    class Cluttered(CountLocator):
        obstacles = ["mug"]

    cell, _ = make_cell(("perfect",), bricks=2)
    cell.locator = Cluttered(2)
    cell.namer = Namer()
    cell.run()
    assert sent == [((8, 8, 3), None)]  # once while it stays; no pixel box until scene.Blob has one


def test_the_robot_says_the_tally_between_bricks_and_each_recovery_step(make_cell, monkeypatch):
    said = []
    monkeypatch.setattr(run.narrator, "say", lambda event, **kw: said.append((event, kw)))
    cell, _ = make_cell(("perfect", "uncertain", "uncertain", "uncertain", "uncertain"), bricks=2)
    cell.run()
    events = [event for event, _ in said]
    assert events[0] == "first"
    assert ("next", {"n": 1, "perfect": 1, "defective": 0, "rechecked": 0, "chose": False, "obstacles": 0}) in said
    assert "grip" in events  # said once the gripper holds the brick
    assert events.index("roll") < events.index("regrasp")
    assert set(said[events.index("roll")][1]) == {"score"}  # the borderline score it is about to recheck


def test_facts_for_pix_follow_the_run(make_cell):
    cell, _ = make_cell(("defective",))
    assert cell.facts()["signal"] is None and cell.facts()["sorted"] == 0
    cell.run()
    facts = cell.facts()
    assert facts["sorted"] == 1 and facts["decided"] == "defective" and facts["tally"]["defective"] == 1
    assert facts["signal"]["label"] == "defective" and facts["state"] == "DONE"


def test_a_finished_run_logs_its_energy_per_brick(make_cell, tmp_path, monkeypatch):
    from contextlib import contextmanager

    from bench.power import Reading

    @contextmanager
    def fake_measure():
        yield Reading(seconds=40.0, joules=1200.0, watts=30.0, max_c=71.0)

    monkeypatch.setattr(run.power, "measure", fake_measure)
    events = tmp_path / "events.jsonl"
    telemetry.start(events)
    cell, _ = make_cell(("perfect", "defective", "perfect"), bricks=3)
    cell.run()
    telemetry.stop()
    rows = [json.loads(line) for line in events.read_text().splitlines()]
    energy = [r for r in rows if r["state"] == "ENERGY"]
    assert len(energy) == 1 and energy[0]["outcome"] == "3 bricks" and "400.0 J per brick" in energy[0]["note"]


def test_no_energy_row_without_a_power_counter(make_cell, tmp_path, monkeypatch):
    from contextlib import contextmanager

    from bench.power import Reading

    @contextmanager
    def no_counter():  # Windows, macOS, or RAPL not readable: every reading stays None
        yield Reading(seconds=5.0)

    monkeypatch.setattr(run.power, "measure", no_counter)
    events = tmp_path / "events.jsonl"
    telemetry.start(events)
    cell, _ = make_cell(("perfect",))
    cell.run()
    telemetry.stop()
    assert "ENERGY" not in events.read_text() and cell.sorted == 1


def test_facts_include_what_pix_sees_and_survive_a_camera_failure(make_cell):
    from narrator.vision import Sight

    cell, _ = make_cell(("perfect",))
    cell.look = lambda: Sight("unknown", 0.7, "mug")
    assert cell.facts()["sight"] == {"name": "unknown", "guess": "mug"}

    def broken():
        raise TimeoutError("no wrist frame")

    cell.look = broken
    assert cell.facts()["sight"] is None


def test_drive_trials_log_every_attempt_and_carry_on_after_a_failure(make_cell, tmp_path, monkeypatch):
    monkeypatch.setattr(run.narrator, "say", lambda event, **kw: None)
    events = tmp_path / "events.jsonl"
    telemetry.start(events)
    cell, _ = make_cell(("perfect",))
    results = iter([41.0, None, 40.5])
    cell.approach, cell.approach_cm = (lambda: next(results)), 41.0
    cell.dock_offset = lambda: (0.6, 2.0)
    made = cell.drive_trials(3, ready=lambda prompt: "")
    telemetry.stop()
    drives = [json.loads(line) for line in events.read_text().splitlines() if '"DRIVE"' in line]
    assert made == 3 and [d["outcome"] for d in drives] == ["arrived", "failed", "arrived"]
    assert "41.0 cm travelled" in drives[0]["note"] and "0.6 cm 2 deg from the dock" in drives[0]["note"]


def test_drive_trials_stop_on_q(make_cell, monkeypatch):
    monkeypatch.setattr(run.narrator, "say", lambda event, **kw: None)
    cell, _ = make_cell(("perfect",))
    cell.approach = lambda: 41.0
    answers = iter(["", "q"])
    assert cell.drive_trials(5, ready=lambda prompt: next(answers)) == 1


def test_a_broken_dock_measurement_does_not_spoil_the_attempt(make_cell):
    cell, _ = make_cell(("perfect",))
    cell.approach_cm = 41.0

    def blind():
        raise TimeoutError("no top frame")

    cell.dock_offset = blind
    assert cell._drive_note(40.0) == "41 cm planned; 40.0 cm travelled"


def test_placing_line_names_the_bowl_and_the_deciding_number():
    from common.interfaces import DefectSignal

    def sig(score):
        return DefectSignal(1, "wrist", "x", score, 65.4, 67.1, None, None, "patchcore", "NPU", 1.0)
    assert run.placing_line("purple", "perfect", sig(22.4)) == "Heading to the purple bowl: it scored 22, under my limit of 65."
    assert run.placing_line("orange", "defective", sig(72.9)) == "Heading to the orange bowl: it scored 73, over my limit of 67."
    assert "to be safe" in run.placing_line("orange", "uncertain", sig(66.0))
