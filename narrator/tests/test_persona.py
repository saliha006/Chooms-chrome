import threading

import pytest

from narrator.lines import LINES
from narrator.persona import EXCLAIM, Persona


@pytest.fixture
def persona():
    said = []
    p = Persona(lambda event, persona=None, **kw: said.append((persona, event)))
    return p, said


def test_obstacle_flips_to_cowboy_with_one_exclamation(persona):
    p, said = persona
    p.trigger("obstacle")
    p.trigger("obstacle")  # still there on the next look: no second "Holy smokes!"
    assert p.current == "cowboy"
    assert said == [("cowboy", "obstacle")]


def test_stays_cowboy_while_the_obstacle_is_there(persona):
    p, said = persona
    p.trigger("obstacle")
    p.brick_done()
    assert p.current == "cowboy"


def test_back_to_calm_after_clear_and_one_brick_through_the_halfway_line(persona):
    p, said = persona
    p.trigger("obstacle")
    p.clear("obstacle")
    assert p.current == "cowboy"  # cleared, but no brick done yet
    p.brick_done()
    assert p.current == "calm"
    assert said[-1] == ("calm", "halfway")


def test_the_hat_stays_on_until_it_is_taken_off(persona):
    p, said = persona
    p.trigger("hat")
    assert said == [("cowboy", "hat_on")]
    p.brick_done()
    p.brick_done()
    assert p.current == "cowboy"  # "until further notice"
    p.take_off_hat()
    assert p.current == "calm" and said[-1] == ("calm", "hat_off")


def test_h_toggles_the_hat(persona):
    p, said = persona
    p.toggle_hat()
    assert p.hat_on and p.current == "cowboy"
    p.toggle_hat()
    assert not p.hat_on and p.current == "calm"


def test_taking_off_a_hat_that_is_not_on_says_nothing(persona):
    p, said = persona
    p.take_off_hat()
    assert said == [] and p.current == "calm"


def test_a_hat_on_an_already_cowboy_robot_still_gets_its_line(persona):
    p, said = persona
    p.trigger("obstacle")
    p.trigger("hat")
    assert said == [("cowboy", "obstacle"), ("cowboy", "hat_on")]


def test_hat_while_an_obstacle_stays_keeps_the_cowboy(persona):
    p, _ = persona
    p.trigger("obstacle")
    p.trigger("hat")
    p.take_off_hat()  # the obstacle is still there: stay the cowboy, no "no longer a cowboy" line
    p.brick_done()
    assert p.current == "cowboy"


def test_calm_brick_done_says_nothing(persona):
    p, said = persona
    p.brick_done()
    assert said == []


def test_every_exclamation_and_the_halfway_line_exist():
    assert all(key in LINES["cowboy"] for key in EXCLAIM.values())
    assert "halfway" in LINES["calm"]


def test_triggers_from_two_threads_say_each_line_at_most_once(persona):
    p, said = persona
    threads = [threading.Thread(target=p.trigger, args=(kind,)) for kind in ("obstacle", "hat") * 20]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert 1 <= len(said) <= 2 and len(set(said)) == len(said)
