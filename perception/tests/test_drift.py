import pytest

from perception import thresholds
from perception.drift import Drift, baseline, drift

GOOD_MEAN, T_LOW = 40.0, 100.0


def test_scores_at_the_baseline_do_not_alarm():
    assert drift([40.0] * 8, GOOD_MEAN, T_LOW) == Drift(0.0, False, 8)


def test_creeping_towards_t_low_alarms_at_halfway():
    reading = drift([70.0] * 8, GOOD_MEAN, T_LOW)
    assert reading.fraction == pytest.approx(0.5) and reading.alert
    assert not drift([69.0] * 8, GOOD_MEAN, T_LOW).alert


def test_only_the_latest_window_counts():
    early_dip_then_fine = [10.0] * 20 + [40.0] * 8
    assert drift(early_dip_then_fine, GOOD_MEAN, T_LOW).fraction == pytest.approx(0.0)
    late_rise = [40.0] * 20 + [80.0] * 8
    assert drift(late_rise, GOOD_MEAN, T_LOW).alert


def test_too_few_bricks_never_alarm():
    assert drift([95.0] * 4, GOOD_MEAN, T_LOW) == Drift(0.0, False, 4)


def test_a_threshold_at_or_below_the_baseline_cannot_drift():
    assert not drift([90.0] * 8, GOOD_MEAN, 40.0).alert
    assert not drift([90.0] * 8, GOOD_MEAN, 30.0).alert


def test_baseline_reads_good_mean_from_thresholds(tmp_path):
    path = tmp_path / "t.yaml"
    thresholds.save(path, 100.0, 200.0, good_mean=41.5)
    assert baseline(path) == 41.5
