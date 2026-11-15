"""The inspection camera as a plate camera: which bricks sit where, and did one just leave the plate (Saliha, 2026-11-15).

The camera used to look at the gripper; it now looks down at the plate the bricks start on, so the old
"brick in the jaws" photo comparison (perception.grasp) no longer means anything. A grasp is judged here by what
the plate shows: a brick that was there and is gone is in the gripper, a brick that moved was only pushed.

    before = find_bricks(frame_before_the_pick, roi)
    verdict = compare(before, find_bricks(frame_after, roi))   # .lifted / .pushed / .untouched
    bowl_centre(scene["bowl_red"])                              # pixel centre of a clicked bowl region

Bricks are found by colour saturation, like perception.scene; `roi` (a polygon in this camera's pixels) keeps the
brown box and cables at the edge of the view out. Every number marked TUNE is a guess until it is checked live:
`python -m perception.plate` shows what the camera finds, with no arm involved.
"""

from dataclasses import dataclass

import cv2
import numpy as np

from perception.scene import SceneParams, _colour_contours

MIN_AREA_PX = 1200  # TUNE: the 2x2 brick covers ~2400 px at this camera height; stud speckle and cable glints are far smaller
MATCH_PX = 25  # TUNE: a brick that moved less than this between two looks is the same brick, not pushed
MAX_AREA_PX = 9000  # TUNE: larger than a 2x4 brick: a hand, the gripper, the box


@dataclass(frozen=True)
class Brick:
    x: int
    y: int
    area: float


@dataclass(frozen=True)
class Outcome:
    lifted: int  # bricks that were on the plate and are no longer anywhere in view
    pushed: int  # bricks still in view, but not where they were: a failed grasp that nudged them
    untouched: int


def find_bricks(frame_bgr: np.ndarray, roi: np.ndarray | None = None, params: SceneParams = SceneParams()) -> list[Brick]:
    mask = None if roi is None else cv2.fillPoly(np.zeros(frame_bgr.shape[:2], np.uint8), [np.asarray(roi, np.int32)], 1)
    bricks = []
    for contour in _colour_contours(frame_bgr, params):
        area = cv2.contourArea(contour)
        if not MIN_AREA_PX <= area <= MAX_AREA_PX:
            continue
        m = cv2.moments(contour)
        x, y = round(m["m10"] / m["m00"]), round(m["m01"] / m["m00"])
        if mask is None or mask[y, x]:
            bricks.append(Brick(x, y, area))
    return bricks


def compare(before: list[Brick], after: list[Brick], match_px: float = MATCH_PX) -> Outcome:
    """Pair each brick seen before with the nearest one seen now; the unpaired ones are gone."""
    free = list(after)
    lifted = pushed = untouched = 0
    for brick in sorted(before, key=lambda b: (b.x, b.y)):
        if not free:
            lifted += 1
            continue
        nearest = min(free, key=lambda a: (a.x - brick.x) ** 2 + (a.y - brick.y) ** 2)
        distance = np.hypot(nearest.x - brick.x, nearest.y - brick.y)
        if distance <= match_px:
            free.remove(nearest)
            untouched += 1
        elif distance <= 4 * match_px:
            free.remove(nearest)
            pushed += 1
        else:
            lifted += 1
    return Outcome(lifted, pushed, untouched)


def bowl_centre(corners_px) -> tuple[int, int]:
    """Pixel centre of a bowl region clicked with `python -m ui.click_regions` (the top camera's view)."""
    x, y = np.asarray(corners_px, float).mean(axis=0)
    return round(x), round(y)


def main() -> None:
    """Live check, no arm: the inspection camera with every brick it finds marked. Q quits, B stores the bricks seen
    now as the "before" look, after which the screen says what changed (lift a brick by hand to try it)."""
    import yaml

    cameras = yaml.safe_load(open("config/cameras.yaml"))
    scene = yaml.safe_load(open("config/scene.yaml"))
    roi = scene.get("plate")
    capture = cv2.VideoCapture(cameras["inspect"]["path"])
    before: list[Brick] | None = None
    while True:
        ok, frame = capture.read()
        if not ok:
            continue
        bricks = find_bricks(frame, roi)
        for b in bricks:
            cv2.circle(frame, (b.x, b.y), 8, (0, 255, 0), 2)
            cv2.putText(frame, f"{b.area:.0f}", (b.x + 10, b.y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
        if roi is not None:
            cv2.polylines(frame, [np.asarray(roi, np.int32)], True, (255, 160, 0), 1)
        text = f"{len(bricks)} bricks"
        if before is not None:
            o = compare(before, bricks)
            text += f" | lifted {o.lifted} pushed {o.pushed} untouched {o.untouched}"
        cv2.putText(frame, text, (10, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
        cv2.imshow("plate", frame)
        key = cv2.waitKey(30) & 0xFF
        if key == ord("q"):
            break
        if key == ord("b"):
            before = bricks
    capture.release()


if __name__ == "__main__":
    main()
