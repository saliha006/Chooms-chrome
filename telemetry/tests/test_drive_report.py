import json

from telemetry.drive_report import attempts, report


def write(path, rows):
    path.write_text("".join(json.dumps(r) + "\n" for r in rows))


def drive(run_id, outcome, seconds, note):
    return {"run_id": run_id, "brick_id": 0, "state": "DRIVE", "outcome": outcome, "latency_ms": seconds * 1000, "note": note}


def test_report_counts_arrivals_and_reads_the_offsets(tmp_path):
    events = tmp_path / "events.jsonl"
    write(events, [
        drive("trials-1", "arrived", 24.0, "41 cm planned; 40.5 cm travelled; 0.6 cm 2 deg from the dock"),
        drive("trials-1", "arrived", 26.0, "41 cm planned; 41.5 cm travelled; 1.0 cm 4 deg from the dock"),
        drive("trials-1", "drive_failed", 12.0, "41 cm planned"),
        drive("mock-x", "arrived", 3.0, "42 cm planned; 42.0 cm travelled"),  # rehearsal: left out
        {"run_id": "trials-1", "brick_id": 1, "state": "PICK", "outcome": "presented"},
    ])
    found = attempts(events)
    assert len(found) == 3 and found[0].off_cm == 0.6 and found[0].off_deg == 2.0
    text = report(found)
    assert text.startswith("Drive arrived 2 of 3 (67%, 95% interval 9-99%)")
    assert "median time: 25.0 s" in text and "median stop from the dock: 0.8 cm" in text
    assert "failed: drive_failed x1" in text


def test_one_session_by_run_id_includes_a_mock_rehearsal(tmp_path):
    events = tmp_path / "events.jsonl"
    write(events, [drive("mock-x", "arrived", 3.0, "42.0 cm travelled"), drive("real-1", "arrived", 20.0, "")])
    assert [a.run_id for a in attempts(events, "mock-x")] == ["mock-x"]
    assert report([]) == "No drive attempts logged."
