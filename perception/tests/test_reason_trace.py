import pytest

from common.interfaces import DefectSignal
from perception.reason_trace import ReasonTrace, margin, region


def signal(label, score, bbox=None):
    return DefectSignal(4, "webcam", label, score, 50.0, 200.0, bbox, None, "padim", "NPU", 3.0)


@pytest.mark.parametrize(("bbox", "cell"), [((0, 0, 20, 20), "top-left"), ((118, 118, 20, 20), "middle-centre"),
                                            ((230, 230, 20, 20), "bottom-right"), (None, None)])
def test_region_grid(bbox, cell):
    assert region(bbox) == cell


def test_margin_sign():
    assert margin(30, 50, 200) == 20  # clearly perfect
    assert margin(260, 50, 200) == 60  # clearly defective
    assert margin(120, 50, 200) == -70  # in the band: negative, distance to the nearer line


def test_trace_for_a_clear_defect():
    t = ReasonTrace.from_signal(signal("defective", 250.0, (10, 10, 30, 30)), "defective")
    assert t.region == "top-left" and t.margin == 50
    assert "above my defect line" in t.reason and "top-left" in t.reason
    assert t.note().startswith("defective at top-left: score 250.0 vs 50.0/200.0 (margin +50.0)")


def test_trace_for_a_recovered_uncertain_brick():
    steps = [("look again", 140.0), ("roll 90", 150.0), ("re-grasp", 160.0)]
    t = ReasonTrace.from_signal(signal("uncertain", 130.0), "defective", steps)
    assert "Still unsure after 3 more looks" in t.reason
    assert t.note().endswith("look again 140.0 > roll 90 150.0 > re-grasp 160.0")
    assert t.as_dict()["steps"] == steps


def test_trace_for_a_clean_brick():
    t = ReasonTrace.from_signal(signal("perfect", 30.0), "perfect")
    assert t.reason == "Score 30.0 is below my clean line of 50.0." and t.region is None
