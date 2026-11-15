import cv2
import numpy as np

from perception.plate import Brick, bowl_centre, compare, find_bricks


def plate(*bricks_at):
    frame = np.full((480, 640, 3), 235, np.uint8)  # white plate: no saturation
    for x, y in bricks_at:
        cv2.rectangle(frame, (x - 30, y - 25), (x + 30, y + 25), (30, 30, 200), -1)  # a red 60 x 50 px brick
    return frame


def test_finds_each_brick_and_ignores_speckle():
    frame = plate((200, 300), (400, 250))
    cv2.circle(frame, (50, 50), 5, (30, 30, 200), -1)
    found = find_bricks(frame)
    assert sorted((b.x, b.y) for b in found) == [(200, 300), (400, 250)]


def test_the_region_keeps_edge_clutter_out():
    frame = plate((200, 300), (40, 300))
    roi = np.array([[100, 100], [600, 100], [600, 450], [100, 450]])
    assert [(b.x, b.y) for b in find_bricks(frame, roi)] == [(200, 300)]


def test_a_brick_that_left_the_plate_is_lifted():
    before = find_bricks(plate((200, 300), (400, 250)))
    outcome = compare(before, find_bricks(plate((400, 250))))
    assert (outcome.lifted, outcome.pushed, outcome.untouched) == (1, 0, 1)


def test_a_nudged_brick_is_pushed_not_lifted():
    before = find_bricks(plate((200, 300), (400, 250)))
    outcome = compare(before, find_bricks(plate((200, 300), (440, 250))))
    assert (outcome.lifted, outcome.pushed, outcome.untouched) == (0, 1, 1)


def test_nothing_changed_is_untouched():
    before = find_bricks(plate((200, 300)))
    assert compare(before, find_bricks(plate((203, 301)))).untouched == 1


def test_an_empty_plate_after_means_every_brick_left():
    assert compare([Brick(10, 10, 2000), Brick(300, 300, 2000)], []).lifted == 2


def test_bowl_centre_is_the_middle_of_the_clicked_corners():
    assert bowl_centre([[450, 137], [544, 190], [510, 272], [393, 224]]) == (474, 206)
