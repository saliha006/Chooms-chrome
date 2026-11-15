"""What the top camera says about the workspace (F9, decisions.md D22): where the bricks are, which one to pick,
whether something that isn't a brick is in the way, and whether a placed brick landed in its bowl.

Rule-based on purpose: localisation is a zone gate and brick picker, never a policy input (PRD v2.5).

    zone = Zone(corners_px)                     # the 4 taped corners of the 10 x 10 cm pick zone, clicked once
    locator = SceneLocator(capture, zone)       # drop-in for common.locate.CountLocator
    if locator.next_brick(): locator.target     # table cm of the most isolated brick
    tall_object(depth_mm, table_mm, zone.mask(depth_mm.shape))   # -> run.py's hold flag
    brick_in_bowl(before, after, bowl_mask)     # place verification
    brick_px(wrist_frame)                       # pixel centre of the biggest brick (not wired yet: visual-servo pick)

Bricks are found by colour saturation, so a grey or skin-coloured object only shows up through depth.
Every number marked TUNE is a guess until it is checked on the station.
"""

import time
from dataclasses import dataclass, field

import cv2
import numpy as np

DUPLO_2X2_CM2 = 3.2 * 3.2  # footprint of the smallest brick we expect
DUPLO_2X4_CM2 = 3.2 * 6.4  # footprint of the largest


@dataclass(frozen=True)  # shared as a default argument, so it must not change
class SceneParams:
    saturation_min: int = 80  # TUNE: bricks are saturated, the table is not
    value_min: int = 40  # TUNE: ignore dark shadows
    brick_area_cm2: tuple[float, float] = (DUPLO_2X2_CM2 * 0.6, DUPLO_2X4_CM2 * 1.4)  # TUNE: ±40% for perspective and blur
    max_aspect: float = 2.5  # a 2x4 brick is 2:1
    min_solidity: float = 0.8  # bricks are convex; hands and cables aren't
    tall_mm: float = 40.0  # TUNE: Duplo stands ~24 mm with studs
    tall_min_pixels: int = 50  # TUNE: ignore depth speckle
    pixel_change: int = 25  # TUNE: grey-level difference that counts as "changed"
    bowl_change_fraction: float = 0.02  # TUNE: share of the bowl region that must change after a place


@dataclass
class Blob:
    centre_cm: np.ndarray
    area_cm2: float
    aspect: float
    solidity: float
    is_brick: bool


@dataclass
class Scene:
    bricks: list[Blob] = field(default_factory=list)
    obstacles: list[Blob] = field(default_factory=list)


class Zone:
    """The taped pick zone: image corners (clockwise from top-left) mapped to table centimetres."""

    def __init__(self, corners_px: np.ndarray, side_cm: float = 10.0):
        self.corners_px = np.asarray(corners_px, np.float32).reshape(4, 2)
        square = np.array([[0, 0], [side_cm, 0], [side_cm, side_cm], [0, side_cm]], np.float32)
        self.to_cm = cv2.getPerspectiveTransform(self.corners_px, square)
        self.side_cm = side_cm

    def table(self, points_px: np.ndarray) -> np.ndarray:
        return cv2.perspectiveTransform(np.asarray(points_px, np.float32).reshape(-1, 1, 2), self.to_cm).reshape(-1, 2)

    def contains(self, point_cm: np.ndarray) -> bool:
        return bool(np.all(point_cm >= 0) and np.all(point_cm <= self.side_cm))

    def mask(self, shape: tuple[int, ...]) -> np.ndarray:
        mask = np.zeros(shape[:2], np.uint8)
        cv2.fillPoly(mask, [self.corners_px.astype(np.int32)], 1)
        return mask.astype(bool)


def _measure(contour: np.ndarray, zone: Zone, params: SceneParams) -> Blob:
    table = zone.table(contour.reshape(-1, 2))
    area = float(cv2.contourArea(table))
    hull = float(cv2.contourArea(cv2.convexHull(table)))
    (_, _), (w, h), _ = cv2.minAreaRect(table)
    aspect = max(w, h) / max(min(w, h), 1e-6)
    solidity = area / hull if hull > 0 else 0.0
    low, high = params.brick_area_cm2
    is_brick = low <= area <= high and aspect <= params.max_aspect and solidity >= params.min_solidity
    return Blob(table.mean(axis=0), area, aspect, solidity, is_brick)


def _colour_contours(bgr: np.ndarray, params: SceneParams) -> tuple[np.ndarray, ...]:
    hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
    mask = ((hsv[..., 1] >= params.saturation_min) & (hsv[..., 2] >= params.value_min)).astype(np.uint8)
    kernel = np.ones((5, 5), np.uint8)
    mask = cv2.morphologyEx(cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel), cv2.MORPH_CLOSE, kernel)
    return cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)[0]


def analyse(top_bgr: np.ndarray, zone: Zone, params: SceneParams = SceneParams()) -> Scene:
    """Saturated blobs inside the zone, each classified brick or obstacle (the "is it a brick?" key check)."""
    scene = Scene()
    for contour in _colour_contours(top_bgr, params):
        if cv2.contourArea(contour) < 20:  # speckle
            continue
        blob = _measure(contour, zone, params)
        if zone.contains(blob.centre_cm):
            (scene.bricks if blob.is_brick else scene.obstacles).append(blob)
    return scene


def brick_px(frame_bgr: np.ndarray, min_area_px: float = 200, params: SceneParams = SceneParams()) -> tuple[int, int] | None:
    """Pixel (x, y) centre of the largest brick-coloured blob in a wrist-camera frame, for a visual-servo pick.
    None when nothing saturated is at least min_area_px (TUNE) big."""
    contours = [c for c in _colour_contours(frame_bgr, params) if cv2.contourArea(c) >= min_area_px]
    if not contours:
        return None
    m = cv2.moments(max(contours, key=cv2.contourArea))
    return round(m["m10"] / m["m00"]), round(m["m01"] / m["m00"])


def most_isolated(scene: Scene) -> Blob | None:
    """The brick farthest from every other blob: the safest one to grasp in a pile."""
    if not scene.bricks:
        return None
    everything = scene.bricks + scene.obstacles

    def clearance(brick: Blob) -> float:
        others = [np.linalg.norm(brick.centre_cm - o.centre_cm) for o in everything if o is not brick]
        return min(others, default=np.inf)

    return max(scene.bricks, key=clearance)


def tall_object(depth_mm: np.ndarray, table_mm: float, mask: np.ndarray | None = None, params: SceneParams = SceneParams()) -> bool:
    """Something taller than a brick (a hand, a cup, the hat) inside the mask. Zero depth = no reading."""
    valid = depth_mm > 0
    if mask is not None:
        valid &= mask
    height = table_mm - depth_mm.astype(np.float32)
    return int(np.count_nonzero(valid & (height > params.tall_mm))) >= params.tall_min_pixels


def brick_in_bowl(before_bgr: np.ndarray, after_bgr: np.ndarray, bowl_mask: np.ndarray, params: SceneParams = SceneParams()) -> bool:
    """True if the bowl region changed after a place: the brick is in it."""
    diff = cv2.absdiff(cv2.cvtColor(before_bgr, cv2.COLOR_BGR2GRAY), cv2.cvtColor(after_bgr, cv2.COLOR_BGR2GRAY))
    changed = np.count_nonzero((diff > params.pixel_change) & bowl_mask)
    return changed / max(int(np.count_nonzero(bowl_mask)), 1) > params.bowl_change_fraction


class SceneLocator:
    """Drop-in for common.locate.CountLocator: next_brick() -> bool, plus where the brick and any obstacles are."""

    def __init__(self, capture, zone: Zone, params: SceneParams = SceneParams(), role: str = "top"):
        self.capture, self.zone, self.params, self.role = capture, zone, params, role
        self.target: np.ndarray | None = None
        self.obstacles: list[Blob] = []

    def next_brick(self) -> bool:
        scene = analyse(self.capture.frame(self.role, newer_than=time.monotonic()), self.zone, self.params)
        brick = most_isolated(scene)
        self.target = None if brick is None else brick.centre_cm
        self.obstacles = scene.obstacles
        return brick is not None
