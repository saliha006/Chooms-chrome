"""The box-room drive (decisions.md D35): the arm pulls its wheeled board into the dock with floor strokes.

    python -m robot.drive --make-tag runs/markers/tag7.png   # print at 100%: the 10 cm tag (ArUco 4x4 set, ID 7)
    python -m robot.drive --teach-dock                         # board seated in the dock: save where the tag sits
    python -m robot.drive --check                              # where the tag is now, and how far from the dock

`approach(top_frame)` is what `cell.approach` runs (run.py): stroke until the overhead camera sees the tag at the
taught dock pose and return the centimetres travelled, or None if the board stalls, runs out of strokes or the stage
deadline fires. When the tag can't be seen it trusts the corner stops: after a fixed number of strokes it answers
with the planned distance, the only figure it has. Every arm move goes through robot.io, so E stops it within one
control step. --teach-dock and --check open the overhead camera themselves: run them only while run.py is not.
"""

import argparse
import math
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
STROKE_S = (1.5, 1.0, 2.0, 1.0)  # TUNE: a slow drag keeps the gripper from slipping on the floor
TAG_ID = 7
TAG_CM = 10.0  # side of the printed black square
PLANNED_CM = 41.0  # TUNE: 29 cm start area + 12 cm of travel, as built (D35)
BLIND_STROKES = 5  # TUNE: strokes from the start into the corner stops, used while the tag can't be seen
MAX_STROKES = 8  # TUNE
DOCK_CM = 1.0  # TUNE: this close to the taught pose counts as docked
DOCK_DEG = 5.0  # TUNE
PROGRESS_CM = 1.0  # TUNE: a stroke that gains less than this made no progress
STALL_STROKES = 2  # TUNE: strokes without progress before giving up (stuck on a guide, or slipping)

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


def one_stroke(poses: dict[str, np.ndarray]) -> bool:
    """Reach, touch the floor, drag back, lift. False if the stage deadline fired; E raises from robot.io."""
    for name, seconds in zip(STROKE, STROKE_S):
        if deadline.expired():
            return False
        io.move_to(poses[name], seconds)
    return True


def approach(top_frame: Callable[[], np.ndarray], dock: TagPose | None = None,
             poses: dict[str, np.ndarray] | None = None) -> float | None:
    """Stroke into the dock. Centimetres travelled, or None if the board stalled or ran out of strokes or time."""
    dock = dock or load_dock()
    poses = poses or load_stroke()
    start = find_tag(top_frame())
    closest, stalled = None, 0
    for strokes in range(MAX_STROKES + 1):
        tag = find_tag(top_frame())
        if tag is not None:
            gap = tag.cm_to(dock)
            if gap <= DOCK_CM and tag.degrees_to(dock) <= DOCK_DEG:
                return start.cm_to(tag) if start is not None else PLANNED_CM
            stalled = stalled + 1 if closest is not None and closest - gap < PROGRESS_CM else 0
            closest = gap if closest is None else min(closest, gap)
            if stalled >= STALL_STROKES:
                return None
        elif strokes >= BLIND_STROKES:
            return PLANNED_CM  # the tag is hidden or glared out: the corner stops did the docking (D35)
        if strokes == MAX_STROKES or not one_stroke(poses):
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


def main() -> None:
    ap = argparse.ArgumentParser(description="Box-room drive tools (decisions.md D35).")
    action = ap.add_mutually_exclusive_group(required=True)
    action.add_argument("--make-tag", type=Path, metavar="PNG", help="write the printable tag at 300 dpi")
    action.add_argument("--teach-dock", action="store_true", help="board seated in the dock: save the tag's pose")
    action.add_argument("--check", action="store_true", help="where the tag is now, and how far from the dock")
    args = ap.parse_args()
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
