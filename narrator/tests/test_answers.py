from narrator.answers import answer

SIGNAL = {"label": "defective", "score": 0.4123, "t_low": 0.2, "t_high": 0.33, "where": "top-left"}
BUSY = {"state": "PLACE", "sorted": 3, "tally": {"perfect": 2, "defective": 1, "rechecked": 1},
        "decided": "defective", "obstacles": 1, "signal": SIGNAL}
FRESH = {"state": "LOCATE", "sorted": 0, "tally": {}, "decided": None, "obstacles": 0, "signal": None}


def test_what_do_you_see_says_the_stage_the_last_score_and_any_obstacle():
    assert answer("see", BUSY) == ("Right now I'm putting a brick in its bowl. The last brick scored 0.41, over my "
                                   "0.33 line, with a mark at the top left. There's also something on the plates "
                                   "that isn't a brick, so I'm leaving it alone.")
    assert answer("see", FRESH) == "Right now I'm looking for the next brick. I haven't inspected a brick yet."


def test_tally():
    assert answer("tally", BUSY) == "I've sorted 3: 2 perfect and 1 defective, and 1 needed a second look."
    assert answer("tally", FRESH) == "None sorted yet. Give me a moment."


def test_why_that_bowl():
    assert answer("why", BUSY) == ("Because the last brick scored 0.41, over my 0.33 line, with a mark at the top "
                                   "left. That's why it went in the orange bowl.")
    assert answer("why", FRESH).startswith("I haven't made a call yet")


def test_doing_who_and_unknown():
    assert answer("doing", BUSY) == "I'm putting a brick in its bowl."
    assert answer("who", FRESH).startswith("I'm Pix.")
    assert answer("unknown", FRESH).startswith("Sorry, I didn't catch that.")


def test_what_do_you_see_leads_with_what_the_camera_shows():
    known = dict(BUSY, sight={"name": "orange bowl", "guess": None})
    assert answer("see", known).startswith("I can see an orange bowl in front of my camera. Right now I'm")
    unknown = dict(FRESH, sight={"name": "unknown", "guess": "mug"})
    assert answer("see", unknown).startswith("There's something in front of my camera I don't recognise. My best guess is a mug.")
