import cv2
import numpy as np
import pytest

from common import deadline, estop
from robot import drive, io

DOCK_Y = 100  # where the tag sits in the overhead image when the board is docked
SIDE = 60  # tag width in pixels: 6 px per cm


def scene(x=320.0, y=300.0, angle=0.0, tag_id=drive.TAG_ID):
    """A white overhead frame with the tag centred at (x, y), turned by `angle` degrees."""
    tag = cv2.aruco.generateImageMarker(drive._DICTIONARY, tag_id, SIDE)
    tag = cv2.copyMakeBorder(tag, SIDE, SIDE, SIDE, SIDE, cv2.BORDER_CONSTANT, value=255)
    half = tag.shape[0] / 2
    move = cv2.getRotationMatrix2D((half, half), angle, 1.0)
    move[:, 2] += (x - half, y - half)
    canvas = np.full((480, 640), 255, np.uint8)
    cv2.warpAffine(tag, move, (640, 480), dst=canvas, borderMode=cv2.BORDER_TRANSPARENT)
    return cv2.cvtColor(canvas, cv2.COLOR_GRAY2BGR)


class Board:
    """The board seen from above: every stroke moves its tag `step` pixels toward the dock."""

    def __init__(self, y=340.0, step=60.0, visible=True):
        self.y, self.step, self.visible, self.strokes = y, step, visible, 0

    def frame(self):
        return scene(y=self.y) if self.visible else np.full((480, 640, 3), 255, np.uint8)

    def stroke(self, poses):
        self.strokes += 1
        self.y = max(DOCK_Y, self.y - self.step)  # the corner stops
        return True


@pytest.fixture
def board(monkeypatch):
    def make(**kw):
        b = Board(**kw)
        monkeypatch.setattr(drive, "one_stroke", b.stroke)
        return b
    return make


DOCK = drive.find_tag(scene(y=DOCK_Y))
POSES = {name: np.full(6, float(i)) for i, name in enumerate(drive.STROKE)}


def test_the_tag_gives_its_centre_and_size():
    tag = drive.find_tag(scene(x=300, y=200))
    assert tag.x_px == pytest.approx(300, abs=1.5) and tag.y_px == pytest.approx(200, abs=1.5)
    assert tag.side_px == pytest.approx(SIDE, abs=2)


def test_turning_the_board_shows_up_as_heading():
    assert drive.find_tag(scene()).degrees_to(drive.find_tag(scene(angle=20))) == pytest.approx(20, abs=2)


def test_no_tag_or_another_tag_is_not_the_board():
    assert drive.find_tag(np.full((480, 640, 3), 255, np.uint8)) is None
    assert drive.find_tag(scene(tag_id=3)) is None


def test_distances_come_from_the_tags_printed_size():
    assert drive.find_tag(scene(y=340)).cm_to(drive.find_tag(scene(y=220))) == pytest.approx(20, abs=0.5)


def test_the_print_file_is_a_readable_ten_centimetre_tag():
    tag = drive.find_tag(cv2.cvtColor(drive.tag_image(dpi=50), cv2.COLOR_GRAY2BGR))
    assert tag is not None and tag.side_px == pytest.approx(drive.TAG_CM / 2.54 * 50, abs=2)


def test_it_strokes_until_docked_and_says_how_far_it_went(board):
    b = board(y=340, step=60)
    assert drive.approach(b.frame, DOCK, POSES) == pytest.approx(40, rel=0.03)  # corner-based scale: about 2%
    assert b.strokes == 4


def test_it_gives_up_when_the_board_stops_moving(board):
    b = board(step=0)
    assert drive.approach(b.frame, DOCK, POSES) is None
    assert b.strokes == drive.STALL_STROKES


def test_without_the_tag_it_trusts_the_corner_stops(board):
    b = board(visible=False)
    assert drive.approach(b.frame, DOCK, POSES) == drive.PLANNED_CM
    assert b.strokes == drive.BLIND_STROKES


def test_a_fired_deadline_stops_before_any_move(monkeypatch):
    moves = []
    monkeypatch.setattr(drive.io, "move_to", lambda pose, seconds: moves.append(pose))
    deadline.abort.set()
    try:
        assert drive.approach(Board().frame, DOCK, POSES) is None
    finally:
        deadline.abort.clear()
    assert moves == []


def test_a_stroke_is_reach_touch_drag_lift(monkeypatch):
    moves = []
    monkeypatch.setattr(drive.io, "move_to", lambda pose, seconds: moves.append(pose[0]))
    assert drive.one_stroke(POSES)
    assert moves == [0.0, 1.0, 2.0, 3.0]


def test_e_stops_a_stroke():
    io.connect(mock=True)
    estop.request()
    try:
        with pytest.raises(estop.EStopped):
            drive.one_stroke(POSES)
    finally:
        estop.clear()
        io.disconnect()


def test_missing_stroke_poses_are_named(tmp_path):
    path = tmp_path / "waypoints.yaml"
    path.write_text("drive_reach: [0, 0, 0, 0, 0, 0]\n")
    with pytest.raises(ValueError, match="drive_touch, drive_drag, drive_lift"):
        drive.load_stroke(path)


def test_the_dock_round_trips_and_says_how_to_teach_it(tmp_path):
    path = tmp_path / "dock.yaml"
    with pytest.raises(ValueError, match="--teach-dock"):
        drive.load_dock(path)
    drive.save_dock(DOCK, path)
    assert drive.load_dock(path) == DOCK


def test_run_once_drives_blind_without_a_taught_dock_then_goes_home(tmp_path, monkeypatch):
    import numpy as np
    import yaml

    from robot import drive, io

    waypoints = tmp_path / "waypoints.yaml"
    poses = {name: [0, 10, 10, 0, 0, 0] for name in drive.STROKE} | {"home": [0, 0, 0, 0, 0, 0]}
    waypoints.write_text(yaml.safe_dump(poses))
    monkeypatch.setattr(io, "connect", lambda **kw: setattr(io, "_robot", io.MockRobot()) or io._robot.connect())
    monkeypatch.setattr(io.time, "sleep", lambda s: None)
    monkeypatch.setattr(drive, "_top_frame", lambda: np.full((480, 640, 3), 255, np.uint8))  # no tag in view
    monkeypatch.setattr(io, "disconnect", lambda: None)  # keep the mock arm to read where it ended
    cm = drive.run_once(dock_path=tmp_path / "missing.yaml", waypoints=waypoints)
    assert cm == drive.PLANNED_CM  # blind strokes into the corner stops
    assert np.allclose(io.observe(), 0)  # ends at home


def test_typical_stroke_is_a_real_recorded_stroke_near_the_average():
    import numpy as np

    from robot import drive

    t = np.linspace(0, 2 * np.pi, 90)
    def drive_run(amplitude):  # three strokes: shoulder_lift swings from raised (-80) out to the floor and back
        lift = -80 + amplitude * (1 - np.cos(np.tile(t, 3))) / 2
        return np.stack([np.zeros_like(lift), lift, np.zeros_like(lift), np.zeros_like(lift), np.zeros_like(lift), np.full_like(lift, 14)], 1)
    strokes = drive.demo_strokes([drive_run(150), drive_run(160), drive_run(170)])
    assert len(strokes) == 3  # each run's middle stroke: the first and last have no trough on both sides
    best = drive.typical_stroke(strokes)
    assert any(np.array_equal(best, s) for s in strokes)  # a medoid, not a blend
    assert 160 - 8 < best[:, 1].max() - best[:, 1].min() < 160 + 8  # the middle amplitude wins
