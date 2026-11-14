import yaml

from fallback import teach


def test_teaches_a_drive_stroke_pose_into_the_waypoints_file(tmp_path, monkeypatch):
    waypoints = tmp_path / "waypoints.yaml"
    waypoints.write_text("home: null\ndrive_reach: null   # comment kept\n")
    monkeypatch.setattr("builtins.input", lambda prompt="": "")
    monkeypatch.setattr("sys.argv", ["teach", "drive_reach", "drive_touch", "--mock", "--file", str(waypoints)])
    teach.main()
    saved = yaml.safe_load(waypoints.read_text())
    assert len(saved["drive_reach"]) == 6 and len(saved["drive_touch"]) == 6
    assert "# comment kept" in waypoints.read_text()


def test_every_drive_stroke_pose_is_teachable():
    from robot.drive import STROKE

    assert set(STROKE) <= set(teach.TEACHABLE)
