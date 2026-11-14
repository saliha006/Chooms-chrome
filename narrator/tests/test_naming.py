import threading
import time

import numpy as np

from narrator.live import compose
from narrator.naming import ObjectNamer, clean, crop, with_article


def test_clean_keeps_a_short_spoken_noun_phrase():
    assert clean("A Coffee Mug.") == "coffee mug"
    assert clean("It's a red plastic water bottle with a lid") == "red plastic water bottle"
    assert clean("  ") is None and clean(None) is None and clean("123") is None


def test_article_follows_the_sound():
    assert with_article("apple") == "an apple" and with_article("cowboy hat") == "a cowboy hat"


def test_crop_adds_context_and_stays_inside_the_frame():
    frame = np.zeros((100, 200, 3), np.uint8)
    assert crop(frame, (10, 10, 40, 20)).shape == (30, 60, 3)  # rows 5-35, columns 0-60 (clipped at the left edge)
    assert crop(frame, None) is frame


def test_obstacle_line_names_the_object_in_each_persona():
    assert compose("cowboy", "obstacle_named", name="coffee mug") == \
        "Holy smokes, there's a coffee mug in my zone! That ain't no brick, so I'm leavin' it be."
    assert compose("calm", "obstacle_named", name="apple").startswith("There's an apple in my zone.")
    assert compose("calm", "obstacle_named") is None


def wait_for(said, n=1):
    deadline = time.monotonic() + 2
    while len(said) < n and time.monotonic() < deadline:
        time.sleep(0.01)


def test_a_named_object_is_said():
    said = []
    namer = ObjectNamer(lambda img: "A coffee mug", lambda event, **kw: said.append((event, kw)))
    namer.submit(lambda: np.zeros((10, 10, 3), np.uint8))
    wait_for(said)
    assert said == [("obstacle_named", {"name": "coffee mug"})]


def test_a_late_name_is_dropped():
    said = []

    def slow(img):
        time.sleep(0.2)
        return "mug"

    ObjectNamer(slow, lambda event, **kw: said.append(kw), timeout_s=0.05).submit(lambda: np.zeros((4, 4, 3), np.uint8))
    time.sleep(0.4)
    assert said == []


def test_a_failing_model_or_camera_says_nothing():
    said, done = [], threading.Event()

    def broken(img):
        done.set()
        raise OSError("network down")

    ObjectNamer(broken, lambda event, **kw: said.append(kw)).submit(lambda: np.zeros((4, 4, 3), np.uint8))
    assert done.wait(2)
    time.sleep(0.05)
    assert said == []
