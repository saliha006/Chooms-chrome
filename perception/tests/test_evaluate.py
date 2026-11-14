from pathlib import Path

import numpy as np
import pytest

from perception.evaluate import brick_bootstrap_auroc, evaluate, group_by_brick, interval, split_bricks, upper_bound
from perception.synth import generate
from perception.thresholds import load


def test_group_and_split_by_brick():
    groups = group_by_brick([Path("b01_0001.png"), Path("b01_0002.png"), Path("b02_0003.png")])
    assert {k: len(v) for k, v in groups.items()} == {"b01": 2, "b02": 1}
    parts = split_bricks(["b1", "b2", "b3", "b4", "b5"], 2)
    assert sorted(sum(parts, [])) == ["b1", "b2", "b3", "b4", "b5"] and not set(parts[0]) & set(parts[1])


def test_exact_bounds():
    assert upper_bound(0, 150) == pytest.approx(0.0198, abs=5e-4)  # the "about 2% at 95%" claim (decisions.md D5 note)
    assert upper_bound(5, 5) == 1.0
    low, high = interval(6, 10)
    assert low == pytest.approx(0.262, abs=2e-3) and high == pytest.approx(0.878, abs=2e-3)


def test_bootstrap_auroc_perfect_separation():
    good = {f"g{i}": [0.1, 0.2] for i in range(5)}
    bad = {f"d{i}": [0.9] for i in range(4)}
    assert brick_bootstrap_auroc(good, bad, n=50) == (1.0, 1.0)


@pytest.mark.slow
def test_evaluate_end_to_end_on_synthetic(tmp_path):
    generate(tmp_path / "data", ["red", "blue"], n_good=40, n_defective=16, n_val_good=0, seed=3)
    result = evaluate(tmp_path / "data", "padim", tmp_path / "t.yaml", tmp_path / "report.md", tmp_path / "work")
    t_low, t_high = load(tmp_path / "t.yaml")
    assert t_low <= t_high and result["pixel_threshold"] > 0
    assert result["good_bricks"] == 10 and result["defective_dev_bricks"] + result["defective_test_bricks"] == 4
    lo, hi = result["auroc_ci95"]
    assert 0.0 <= lo <= result["auroc"] <= hi <= 1.0
    assert Path(result["ckpt"]).exists() and "AUROC" in (tmp_path / "report.md").read_text()
    assert np.isfinite(result["t_high"])
