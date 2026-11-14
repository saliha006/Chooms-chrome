import json

import pytest

from bench.trials import load_events, load_truth, rate, summarise, to_markdown


def brick(run, brick_id, label, t0, help_pause=False, note=None):
    rows = [{"run_id": run, "brick_id": brick_id, "state": "LOCATE", "ts": t0, "label": None, "note": None},
            {"run_id": run, "brick_id": brick_id, "state": "INSPECT", "ts": t0 + 5, "label": label, "note": None}]
    if help_pause:
        rows.append({"run_id": run, "brick_id": brick_id, "state": "PAUSE_HUMAN", "ts": t0 + 8, "label": None, "note": None})
    rows.append({"run_id": run, "brick_id": brick_id, "state": "LOG", "ts": t0 + 20, "label": label, "note": note})
    return rows


def test_counts_sorted_without_help_and_cycle_time():
    events = brick("r1", 1, "perfect", 0) + brick("r1", 2, "defective", 30, help_pause=True) + brick("r1", 3, "perfect", 60)
    s = summarise(events)
    assert (s["bricks"], s["sorted_without_help"], s["helped"]) == (3, 2, 1)
    assert s["cycle_s"] == [20, 20, 20]


def test_a_brick_that_never_reached_the_log_is_attempted_but_not_sorted():
    events = brick("r1", 1, "perfect", 0) + [{"run_id": "r1", "brick_id": 2, "state": "PAUSE_HUMAN", "ts": 40, "label": None, "note": None}]
    s = summarise(events)
    assert (s["bricks"], s["sorted_without_help"], s["helped"]) == (2, 1, 1)


def test_mock_runs_are_ignored(tmp_path):
    path = tmp_path / "e.jsonl"
    rows = brick("mock-1", 1, "perfect", 0) + brick("real-1", 1, "perfect", 0)
    path.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")
    assert {r["run_id"] for r in load_events(path)} == {"real-1"}


def test_correct_bowl_uses_the_truth_file_and_names_the_mistakes(tmp_path):
    truth_path = tmp_path / "t.csv"
    truth_path.write_text("run_id,brick_id,truth\n*,1,perfect\n*,2,defective\nr1,3,defective\n", encoding="utf-8")
    events = brick("r1", 1, "perfect", 0) + brick("r1", 2, "defective", 30) + brick("r1", 3, "perfect", 60)
    s = summarise(events, load_truth(truth_path))
    assert (s["scored"], s["correct"]) == (3, 2)
    text = to_markdown(s)
    assert "2 of 3" in text and "defective brick to the purple bowl x1" in text


def test_bricks_without_truth_are_not_scored_and_the_report_says_so():
    s = summarise(brick("r1", 1, "perfect", 0))
    assert s["scored"] == 0 and "not scored" in to_markdown(s)


def test_second_look_is_counted_from_the_note():
    s = summarise(brick("r1", 1, "defective", 0, note="defective at top-left; look again 140.0"))
    assert s["second_look"] == 1


def test_a_truth_file_with_a_bad_value_is_rejected(tmp_path):
    path = tmp_path / "t.csv"
    path.write_text("run_id,brick_id,truth\n*,1,broken\n", encoding="utf-8")
    with pytest.raises(ValueError, match="perfect or defective"):
        load_truth(path)


def test_no_bricks_gives_a_clear_line_not_a_crash():
    assert "n/a" in rate(0, 0)
    assert "0 of 0" not in to_markdown(summarise([]))


def test_rate_matches_the_published_slide_table():
    assert rate(18, 20) == "18 of 20 (90%, 95% interval 68-99%)"
    assert rate(20, 20) == "20 of 20 (100%, 95% interval 83-100%)"


def test_an_empty_zone_look_is_not_a_brick():
    events = brick("r1", 1, "perfect", 0) + [{"run_id": "r1", "brick_id": 2, "state": "LOCATE", "ts": 40, "label": None, "note": None}]
    assert summarise(events)["bricks"] == 1
