"""The box-room drive (decisions.md D35): the arm pulls its wheeled board into the dock with floor strokes.

    python -m robot.drive --make-tag runs/markers/tag7.png   # print at 100%: the 10 cm tag (ArUco 4x4 set, ID 7)
    python -m robot.drive --teach-dock                         # board seated in the dock: save where the tag sits
    python -m fallback.teach drive_reach drive_touch drive_drag drive_lift   # the stroke, board free to roll
    python -m robot.drive --check                              # where the tag is now, and how far from the dock
    python -m robot.drive --run                                # the drive alone from the start area, then home

`approach(top_frame)` is what `cell.approach` runs (run.py): stroke until the overhead camera sees the tag at the
taught dock pose and return the centimetres travelled. It never gives up by itself: a stroke that gains nothing is
followed by one that presses longer, and only the stage deadline (the answer is then None) or E ends a drive short
of the dock. When the tag can't be seen it trusts the corner stops: after a fixed number of blind strokes in a row
it answers with the planned distance, the only figure it has. Every arm move goes through robot.io, so E stops it
within one control step. --teach-dock, --check and --run with a taught dock open the overhead camera themselves:
run them only while run.py is not.
"""

import argparse
import math
import time
from collections.abc import Callable
from dataclasses import asdict, dataclass
from pathlib import Path

import cv2
import numpy as np
import yaml

from common import deadline
from robot import io

CONFIG = Path(__file__).resolve().parents[1] / "config"
STROKE = ("drive_reach", "drive_touch", "drive_drag", "drive_lift")  # taught by hand into config/waypoints.yaml
ARRIVE_TOLERANCE_DEG = 4.0  # a loaded joint settles 2 or more units short for good: never wait for exact arrival
# TUNE, measured on the follower 2026-11-15: io.act() steps from the observed position, so the arm does about
# 8 units/s per degree of io.MAX_STEP_DEG at cap 7 (~60 units/s; only ~15 at cap 4), not cap x 30 Hz.
ARM_SPEED_PER_DEG = 8.0
MIN_MOVE_S = 1.0  # TUNE: shortest time a move gets
PRESS_MORE_S = 0.3  # TUNE: a stroke that made no progress adds this much press on the floor before the next drag
PRESS_MAX_S = 1.5  # TUNE
RUN_S = 120.0  # --run strokes for this long at most, the time run.py gives its DRIVE stage
TAG_ID = 7
TAG_CM = 10.0  # side of the printed black square
DEMO_STROKE = CONFIG / "drive_stroke.yaml"  # written by --learn-stroke from the recorded drives
PLANNED_CM = 41.0  # TUNE: 29 cm start area + 12 cm of travel, as built (D35)
BLIND_STROKES = 10  # strokes in a row with the tag out of sight before the corner stops are trusted (was 5: short)
DOCK_CM = 1.0  # TUNE: this close to the taught pose counts as docked
DOCK_DEG = 5.0  # TUNE
PROGRESS_CM = 1.0  # TUNE: a stroke that gains less than this made no progress

_DICTIONARY = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)
_DETECTOR = cv2.aruco.ArucoDetector(_DICTIONARY)


@dataclass
class TagPose:
    """Where the tag sits in the overhead image."""

    x_px: float
    y_px: float
    heading_deg: float
    side_px: float

    def cm_to(self, other: "TagPose") -> float:
        # The tag's own printed size sets the scale, so the overhead camera needs no calibration
        return math.hypot(self.x_px - other.x_px, self.y_px - other.y_px) * TAG_CM * 2 / (self.side_px + other.side_px)

    def degrees_to(self, other: "TagPose") -> float:
        return abs((self.heading_deg - other.heading_deg + 180) % 360 - 180)


def tag_image(dpi: int = 300) -> np.ndarray:
    """The tag to print: the black square TAG_CM wide plus a 1.5 cm white margin, which the detector needs."""
    side = round(TAG_CM / 2.54 * dpi)
    margin = round(1.5 / 2.54 * dpi)
    tag = cv2.aruco.generateImageMarker(_DICTIONARY, TAG_ID, side)
    return cv2.copyMakeBorder(tag, margin, margin, margin, margin, cv2.BORDER_CONSTANT, value=255)


def find_tag(frame: np.ndarray) -> TagPose | None:
    corners, ids, _ = _DETECTOR.detectMarkers(frame)
    if ids is None:
        return None
    for quad, tag_id in zip(corners, ids.ravel()):
        if tag_id == TAG_ID:
            c = quad.reshape(4, 2)
            top = c[1] - c[0]
            side = float(np.mean([np.linalg.norm(c[i] - c[(i + 1) % 4]) for i in range(4)]))
            return TagPose(float(c[:, 0].mean()), float(c[:, 1].mean()), math.degrees(math.atan2(top[1], top[0])), side)
    return None


def load_stroke(path: Path = CONFIG / "waypoints.yaml") -> dict[str, np.ndarray]:
    raw = yaml.safe_load(path.read_text()) or {}
    missing = [name for name in STROKE if raw.get(name) is None]
    if missing:
        raise ValueError(f"{path}: teach the drive stroke first: {', '.join(missing)}")
    poses = {name: np.asarray(raw[name], float) for name in STROKE}
    wrong = [name for name, pose in poses.items() if pose.shape != (len(io.JOINTS),)]
    if wrong:
        raise ValueError(f"{path}: need {len(io.JOINTS)} joint values for {', '.join(wrong)}")
    return poses


def load_dock(path: Path = CONFIG / "dock.yaml") -> TagPose:
    if not path.exists():
        raise ValueError(f"{path} is missing: seat the board in the dock and run python -m robot.drive --teach-dock")
    return TagPose(**yaml.safe_load(path.read_text()))


def save_dock(pose: TagPose, path: Path = CONFIG / "dock.yaml") -> None:
    path.write_text(yaml.safe_dump(asdict(pose)))


def one_stroke(poses: dict[str, np.ndarray], press_s: float = 0.0) -> bool:
    """Reach, touch the floor, drag back, lift, in one swoop: each pose is left as soon as the arm is within
    ARRIVE_TOLERANCE_DEG of it. `press_s` keeps pushing on the floor that long before the drag. False, without
    moving, if the stage deadline has fired; a stroke once begun is finished, so the arm is never left on the
    floor for the move home. E raises from robot.io.
    With a stroke learned from the recorded drives (`--learn-stroke`), that recorded path is replayed instead."""
    if DEMO_STROKE.exists():
        return _replay(np.asarray(yaml.safe_load(DEMO_STROKE.read_text())["path"], float))
    if deadline.expired():
        return False
    for name in STROKE:
        io.move_to(poses[name], _seconds_for(poses[name]), ARRIVE_TOLERANCE_DEG)
        if name == "drive_touch":
            for _ in range(round(press_s * io.CONTROL_HZ)):
                io.act(poses[name])
                time.sleep(1 / io.CONTROL_HZ)
    return True


def _seconds_for(target: np.ndarray) -> float:
    """Twice what the arm needs to get there from where it is, and never under MIN_MOVE_S."""
    distance = float(np.abs(target - io.observe()).max())
    return max(MIN_MOVE_S, 2 * distance / (ARM_SPEED_PER_DEG * io.MAX_STEP_DEG))


def _replay(path: np.ndarray) -> bool:
    io.move_to(path[0], seconds=2.0)
    for target in path[1:]:  # recorded at 30 Hz; robot.io's speed cap still bounds every step
        if deadline.expired():
            return False
        io.act(target)
        time.sleep(1 / io.CONTROL_HZ)
    return True


def demo_strokes(states: list[np.ndarray], min_reach: float = 40.0) -> list[np.ndarray]:
    """Cut recorded drives into single strokes: shoulder_lift troughs (arm raised) separate them, and a stroke
    must reach out past `min_reach` between two troughs. Each state array is (frames, 6) in normalized units."""
    strokes = []
    for s in states:
        lift = np.convolve(s[:, 1], np.ones(9) / 9, mode="same")
        troughs = [i for i in range(10, len(lift) - 10) if lift[i] == lift[i - 10:i + 11].min()]
        troughs = [t for k, t in enumerate(troughs) if k == 0 or t - troughs[k - 1] > 15]
        strokes += [s[a:b] for a, b in zip(troughs, troughs[1:]) if s[a:b, 1].max() > min_reach and 20 <= b - a <= 150]
    return strokes


def typical_stroke(strokes: list[np.ndarray], samples: int = 60) -> np.ndarray:
    """The real stroke closest to the average shape (a medoid): a move that physically worked, unlike a plain
    average, which can blend two strokes into one that never reaches the floor."""
    def shape(x: np.ndarray) -> np.ndarray:
        grid = np.linspace(0, len(x) - 1, samples)
        return np.stack([np.interp(grid, np.arange(len(x)), x[:, j]) for j in range(x.shape[1])], 1)
    shapes = np.stack([shape(x) for x in strokes])
    mean = shapes.mean(0)
    return strokes[int(np.argmin([np.abs(sh - mean).mean() for sh in shapes]))]


def approach(top_frame: Callable[[], np.ndarray], dock: TagPose | None = None,
             poses: dict[str, np.ndarray] | None = None) -> float | None:
    """Stroke into the dock for as long as it takes. Centimetres travelled, or None once the stage deadline fires."""
    dock = dock or load_dock()
    poses = poses or ({} if DEMO_STROKE.exists() else load_stroke())  # a learned stroke needs no taught poses
    start = find_tag(top_frame())
    closest, blind, press_s = None, 0, 0.0
    while True:
        tag = find_tag(top_frame())
        if tag is None:
            if blind >= BLIND_STROKES:
                return PLANNED_CM  # the tag is hidden or glared out: the corner stops did the docking (D35)
            blind += 1
        else:
            blind = 0  # one glared frame after many seen ones must not read as docked
            gap = tag.cm_to(dock)
            if gap <= DOCK_CM and tag.degrees_to(dock) <= DOCK_DEG:
                return start.cm_to(tag) if start is not None else PLANNED_CM
            if closest is not None and closest - gap < PROGRESS_CM:
                press_s = min(press_s + PRESS_MORE_S, PRESS_MAX_S)
            closest = gap if closest is None else min(closest, gap)
        if not one_stroke(poses, press_s):
            return None


def _top_frame() -> np.ndarray:
    from common.capture import OpenCVCamera

    camera = OpenCVCamera(yaml.safe_load((CONFIG / "cameras.yaml").read_text())["top"]["path"])
    try:
        frames = [camera.read() for _ in range(10)]  # the first frames come while the exposure settles
    finally:
        camera.release()
    if frames[-1] is None:
        raise SystemExit("the overhead camera opened but sent no frame")
    return frames[-1]


def run_once(dock_path: Path = CONFIG / "dock.yaml", waypoints: Path = CONFIG / "waypoints.yaml") -> float | None:
    """The drive alone, from the start area, as `run.py --base` would do it (RUN_S at most), then home. Prints
    what happened."""
    poses = {} if DEMO_STROKE.exists() else load_stroke(waypoints)
    home = yaml.safe_load(waypoints.read_text())["home"]
    taught = dock_path.exists()
    # No taught dock yet: nothing to measure against, so the camera stays shut and every look is blank, which ends
    # the drive on the blind stroke count (corner stops).
    dock = load_dock(dock_path) if taught else TagPose(x_px=0.0, y_px=0.0, heading_deg=0.0, side_px=1.0)
    look = _top_frame if taught else lambda: np.full((8, 8), 255, np.uint8)
    robot = yaml.safe_load((CONFIG / "robot.yaml").read_text())
    io.connect(port=robot["port"], calibration=robot["calibration"])
    start = time.monotonic()
    try:
        with deadline.armed(RUN_S):
            cm = approach(look, dock, poses)
        print(f"drive: {'docked, ' + format(cm, '.0f') + ' cm' if cm is not None else 'did not arrive'} "
              f"in {time.monotonic() - start:.0f} s ({'tag dock' if taught else 'blind, no dock taught'})")
        io.move_to(np.asarray(home, float), seconds=4.0)
    finally:
        io.disconnect()
    return cm


def learn_stroke(dataset: Path, skip: set[int], out: Path = DEMO_STROKE) -> np.ndarray:
    import pandas as pd

    frames = pd.concat([pd.read_parquet(f) for f in sorted((dataset / "data").rglob("*.parquet"))])
    states = [np.stack(g.sort_values("frame_index")["observation.state"].to_numpy())
              for ep, g in frames.groupby("episode_index") if ep not in skip]
    strokes = demo_strokes(states)
    if not strokes:
        raise SystemExit(f"no strokes found in {dataset}")
    best = typical_stroke(strokes)
    out.write_text(yaml.safe_dump({"source": str(dataset), "strokes_seen": len(strokes),
                                   "path": [[round(float(v), 2) for v in row] for row in best]}))
    print(f"{len(strokes)} strokes in {len(states)} drives; saved the typical one ({len(best) / io.CONTROL_HZ:.1f} s) to {out}")
    return best


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    action = ap.add_mutually_exclusive_group(required=True)
    action.add_argument("--make-tag", type=Path, metavar="PNG", help="write the printable tag at 300 dpi")
    action.add_argument("--teach-dock", action="store_true", help="board seated in the dock: save the tag's pose")
    action.add_argument("--check", action="store_true", help="where the tag is now, and how far from the dock")
    action.add_argument("--run", action="store_true", help=f"the drive alone, no sorting: {RUN_S:.0f} s at most, then home")
    action.add_argument("--learn-stroke", type=Path, metavar="DATASET", help="pick the typical stroke from recorded drives")
    ap.add_argument("--skip", default="", help="--learn-stroke: episode indices to leave out, e.g. 2,9 (audit warnings)")
    args = ap.parse_args()
    if args.run:
        run_once()
        return
    if args.learn_stroke:
        learn_stroke(args.learn_stroke, {int(e) for e in args.skip.split(",") if e})
        return
    if args.make_tag:
        args.make_tag.parent.mkdir(parents=True, exist_ok=True)
        cv2.imwrite(str(args.make_tag), tag_image())
        print(f"wrote {args.make_tag}: print at 100% and check the black square measures {TAG_CM:.0f} cm")
        return
    tag = find_tag(_top_frame())
    if tag is None:
        raise SystemExit(f"the overhead camera can't see tag {TAG_ID}: check that it's flat, matte and not in glare")
    if args.teach_dock:
        save_dock(tag)
        print(f"dock saved to config/dock.yaml: tag at ({tag.x_px:.0f}, {tag.y_px:.0f}) px, {tag.side_px:.0f} px wide")
    else:
        dock = load_dock()
        print(f"tag at ({tag.x_px:.0f}, {tag.y_px:.0f}) px: "
              f"{tag.cm_to(dock):.1f} cm and {tag.degrees_to(dock):.1f}° from the dock")


if __name__ == "__main__":
    main()
