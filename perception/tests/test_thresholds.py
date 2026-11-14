import numpy as np
import pytest

from perception.thresholds import band, classify, confusion, load, save


def test_band_from_percentiles():
    good = np.linspace(0.0, 0.4, 101)
    defective = np.linspace(0.6, 1.0, 101)
    t_low, t_high = band(good, defective)
    assert t_low == pytest.approx(0.396)
    assert t_high == pytest.approx(0.62)


def test_overlap_becomes_uncertain_band():
    t_low, t_high = band(np.array([0.1, 0.7]), np.array([0.3, 0.9]))
    assert t_low < t_high
    assert classify(0.5, t_low, t_high) == "uncertain"


def test_band_needs_both_classes():
    with pytest.raises(ValueError):
        band(np.array([]), np.array([0.5]))


@pytest.mark.parametrize(("score", "label"), [(0.1, "perfect"), (0.3, "uncertain"), (0.6, "uncertain"), (0.9, "defective")])
def test_classify(score, label):
    assert classify(score, 0.3, 0.6) == label


def test_confusion_counts():
    table = confusion(np.array([0.1, 0.2, 0.5]), np.array([0.9, 0.4]), 0.3, 0.6)
    assert table["good"] == {"perfect": 2, "uncertain": 1, "defective": 0}
    assert table["defective"] == {"perfect": 0, "uncertain": 1, "defective": 1}


def test_save_and_load_roundtrip(tmp_path):
    path = tmp_path / "t.yaml"
    save(path, 0.25, 0.75, model="padim")
    assert load(path) == (0.25, 0.75)
