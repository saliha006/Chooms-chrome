import numpy as np

from robot import goto, io
from robot.readings import window_medians


def test_window_medians_split_a_recording_by_time():
    stamps = np.arange(0.0, 4.0, 0.5)
    samples = np.array([[v] * 6 for v in (1, 1, 1, 1, 9, 9, 9, 9)], float)
    result = window_medians(stamps, samples, 2.0)
    assert [start for start, _ in result] == [0.0, 2.0]
    assert result[0][1][0] == 1.0 and result[1][1][0] == 9.0


def test_goto_holds_the_pose_then_goes_home(tmp_path, monkeypatch):
    waypoints = tmp_path / "waypoints.yaml"
    waypoints.write_text("home: [0, 0, 0, 0, 0, 50]\ninspect: [10, -20, 30, 5, 0, 40]\n")
    monkeypatch.setattr(io.time, "sleep", lambda s: None)
    monkeypatch.setattr("builtins.input", lambda prompt="": "")
    monkeypatch.setattr("sys.argv", ["goto", "inspect", "--gripper", "0", "--waypoints", str(waypoints), "--mock"])
    seen = []
    real_move_to = io.move_to
    monkeypatch.setattr(io, "move_to", lambda target, seconds=2.0: seen.append(np.asarray(target).copy()) or real_move_to(target, seconds))
    goto.main()
    assert seen[0].tolist() == [10, -20, 30, 5, 0, 0] and seen[1].tolist() == [0, 0, 0, 0, 0, 50]


def test_goto_refuses_an_untaught_pose(tmp_path):
    import pytest

    waypoints = tmp_path / "waypoints.yaml"
    waypoints.write_text("home: null\ninspect: null\n")
    with pytest.raises(SystemExit, match="not taught"):
        goto.pose(waypoints, "inspect")
