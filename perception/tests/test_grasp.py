import cv2
import numpy as np

from perception.grasp import brick_in_jaws


def test_a_frame_like_the_empty_gripper_is_not_a_grasp(tmp_path):
    empty = np.full((480, 640, 3), 120, np.uint8)
    ref = tmp_path / "empty.png"
    from perception.capture import square_crop
    cv2.imwrite(str(ref), square_crop(empty, (140, 80, 400)))
    assert not brick_in_jaws(empty, (140, 80, 400), ref)
    held = empty.copy()
    held[100:480, 150:530] = (30, 40, 220)  # a red brick filling the jaws
    assert brick_in_jaws(held, (140, 80, 400), ref)


def test_without_a_reference_the_camera_says_nothing(tmp_path):
    assert not brick_in_jaws(np.zeros((480, 640, 3), np.uint8), None, tmp_path / "missing.png")
