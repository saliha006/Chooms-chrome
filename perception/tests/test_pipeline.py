"""End to end on a small synthetic set: train -> export -> calibrate -> inspect (A3-A6 done-when check).

Slow (about 2 minutes on a laptop CPU). Skip with `pytest -m "not slow"`.
"""

from pathlib import Path

import cv2
import pytest

from perception.calibrate import calibrate
from perception.export import export
from perception.inspector import Inspector
from perception.synth import generate
from perception.train import train

pytestmark = pytest.mark.slow


@pytest.fixture(scope="module")
def pipeline(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("pipeline")
    data = tmp / "data"
    generate(data, ["red", "blue"], n_good=24, n_defective=8, n_val_good=8, seed=1)
    ckpt, metrics = train(data, "padim", tmp / "runs")
    xml = export(ckpt, "padim", data, tmp / "export", "fp16")
    thresholds = tmp / "thresholds.yaml"
    calibrate(xml, data, thresholds, plots=tmp / "plots")
    return data, xml, thresholds, metrics, tmp


def test_training_reports_auroc(pipeline):
    _, _, _, metrics, _ = pipeline
    assert 0.0 <= metrics["image_AUROC"] <= 1.0


def test_export_is_static_and_calibration_writes_plots(pipeline):
    _, xml, thresholds, _, tmp = pipeline
    assert xml.exists() and thresholds.exists()
    assert (tmp / "plots/score_hist.png").exists() and (tmp / "plots/confusion.png").exists()


def test_inspector_returns_a_defect_signal(pipeline):
    data, xml, thresholds, _, tmp = pipeline
    inspector = Inspector(xml, thresholds, "padim-fp16", heatmap_dir=tmp / "heatmaps", devices=("CPU",))
    signal = inspector.inspect(cv2.imread(str(data / "defective/0000.png")), "webcam", 7)
    assert signal.label in {"perfect", "uncertain", "defective"}
    assert signal.device == "CPU" and signal.latency_ms > 0
    assert signal.t_low <= signal.t_high
    assert Path(signal.heatmap_path).exists()
