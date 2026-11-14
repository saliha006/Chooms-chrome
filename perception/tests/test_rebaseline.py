import pytest

from perception.rebaseline import N_HELD_OUT, rebaseline, stage
from perception.synth import generate
from perception.thresholds import load


def test_stage_splits_captured_good_and_copies_defective(tmp_path):
    generate(tmp_path / "src", ["red"], n_good=20, n_defective=3, n_val_good=1)
    stage(tmp_path / "src/good", tmp_path / "src/defective", tmp_path / "root")
    counts = {d: len(list((tmp_path / "root" / d).glob("*.png"))) for d in ("good", "val_good", "defective")}
    assert counts == {"good": 20 - N_HELD_OUT, "val_good": N_HELD_OUT, "defective": 3}


def test_stage_needs_more_than_the_held_out_count(tmp_path):
    generate(tmp_path / "src", ["red"], n_good=N_HELD_OUT, n_defective=1, n_val_good=1)
    with pytest.raises(ValueError):
        stage(tmp_path / "src/good", tmp_path / "src/defective", tmp_path / "root")


@pytest.mark.slow
def test_rebaseline_end_to_end(tmp_path):
    generate(tmp_path / "src", ["red", "blue"], n_good=60, n_defective=8, n_val_good=1, seed=2)
    xml, timings = rebaseline(tmp_path / "src/good", tmp_path / "src/defective", tmp_path / "work", tmp_path / "t.yaml")
    assert xml.exists()
    t_low, t_high = load(tmp_path / "t.yaml")
    assert t_low <= t_high
    print(f"rebaseline timings: {timings}")
