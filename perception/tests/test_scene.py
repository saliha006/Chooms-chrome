import cv2
import numpy as np
import pytest

from perception.scene import SceneLocator, Zone, analyse, brick_in_bowl, brick_px, most_isolated, tall_object

PX_PER_CM = 30
ORIGIN = (100, 60)  # zone top-left in pixels; the zone is 10 x 10 cm = 300 x 300 px


def zone() -> Zone:
    x, y = ORIGIN
    side = 10 * PX_PER_CM
    return Zone(np.array([[x, y], [x + side, y], [x + side, y + side], [x, y + side]]))


def table_image() -> np.ndarray:
    return np.full((480, 640, 3), (150, 150, 150), np.uint8)  # grey: not saturated


def draw_rect(img, cx_cm, cy_cm, w_cm, h_cm, colour=(30, 30, 210)):
    x, y = ORIGIN
    p1 = (int(x + (cx_cm - w_cm / 2) * PX_PER_CM), int(y + (cy_cm - h_cm / 2) * PX_PER_CM))
    p2 = (int(x + (cx_cm + w_cm / 2) * PX_PER_CM), int(y + (cy_cm + h_cm / 2) * PX_PER_CM))
    cv2.rectangle(img, p1, p2, colour, -1)


def test_a_duplo_footprint_is_a_brick():
    img = table_image()
    draw_rect(img, 5, 5, 3.2, 6.4)  # 2x4 brick
    scene = analyse(img, zone())
    assert len(scene.bricks) == 1 and not scene.obstacles
    assert np.allclose(scene.bricks[0].centre_cm, [5, 5], atol=0.3)


@pytest.mark.parametrize(("w", "h"), [(8.0, 8.0), (1.0, 7.0)])  # too big; too thin
def test_wrong_shapes_are_obstacles(w, h):
    img = table_image()
    draw_rect(img, 5, 5, w, h, colour=(200, 60, 20))
    scene = analyse(img, zone())
    assert not scene.bricks and len(scene.obstacles) == 1


def test_blobs_outside_the_zone_are_ignored():
    img = table_image()
    cv2.rectangle(img, (500, 400), (560, 460), (30, 30, 210), -1)
    scene = analyse(img, zone())
    assert not scene.bricks and not scene.obstacles


def test_most_isolated_brick_is_picked():
    img = table_image()
    draw_rect(img, 2, 2, 3.2, 3.2)
    draw_rect(img, 2, 5.5, 3.2, 3.2)  # close to the first
    draw_rect(img, 8, 8, 3.2, 3.2)  # far from both
    target = most_isolated(analyse(img, zone()))
    assert np.allclose(target.centre_cm, [8, 8], atol=0.3)


def test_empty_zone_has_no_target():
    assert most_isolated(analyse(table_image(), zone())) is None


def test_tall_object_from_depth():
    depth = np.full((480, 640), 800, np.uint16)  # table 800 mm away
    assert not tall_object(depth, 800.0)
    depth[100:130, 100:130] = 776  # a brick: 24 mm high
    assert not tall_object(depth, 800.0)
    depth[200:240, 200:240] = 700  # a hand: 100 mm high
    assert tall_object(depth, 800.0)
    assert not tall_object(depth, 800.0, mask=np.zeros(depth.shape, bool))  # outside the mask


def test_brick_in_bowl_detects_change_in_the_bowl_only():
    before = table_image()
    bowl = np.zeros(before.shape[:2], bool)
    cv2.circle(bowl.view(np.uint8), (520, 380), 60, 1, -1)
    after = before.copy()
    cv2.rectangle(after, (500, 360), (540, 400), (30, 30, 210), -1)
    assert brick_in_bowl(before, after, bowl)
    elsewhere = before.copy()
    cv2.rectangle(elsewhere, (20, 20), (60, 60), (30, 30, 210), -1)
    assert not brick_in_bowl(before, elsewhere, bowl)


class FakeCapture:
    def __init__(self, frame):
        self.frame_bgr = frame

    def frame(self, role, newer_than=0.0, timeout_s=1.0):
        return self.frame_bgr


def test_scene_locator_matches_the_count_locator_interface():
    img = table_image()
    draw_rect(img, 3, 7, 3.2, 3.2)
    locator = SceneLocator(FakeCapture(img), zone())
    assert locator.next_brick() is True
    assert np.allclose(locator.target, [3, 7], atol=0.3)
    locator.capture = FakeCapture(table_image())
    assert locator.next_brick() is False and locator.target is None


def test_brick_px_is_the_centre_of_the_largest_coloured_blob():
    img = table_image()
    cv2.rectangle(img, (400, 300), (440, 340), (30, 210, 30), -1)  # small green brick
    cv2.rectangle(img, (100, 100), (200, 160), (0, 120, 240), -1)  # big orange brick, centre (150, 130)
    assert brick_px(img) == (150, 130)


def test_brick_px_ignores_grey_and_specks():
    img = table_image()
    cv2.rectangle(img, (50, 50), (300, 300), (90, 90, 90), -1)  # grey object: not brick-coloured
    cv2.rectangle(img, (500, 400), (505, 405), (30, 30, 210), -1)  # a red speck under min_area_px
    assert brick_px(img) is None
