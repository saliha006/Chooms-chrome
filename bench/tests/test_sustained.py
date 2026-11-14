import numpy as np
import pytest

from bench.sustained import Sustained, run, to_markdown, window_p50s


def test_windows_take_the_first_and_last_seconds():
    stamps = np.arange(0.0, 10.0, 1.0)
    latencies = np.array([1, 1, 1, 5, 5, 5, 5, 9, 9, 9], float)
    assert window_p50s(stamps, latencies, 2.0) == (1.0, 9.0)


def test_slowdown_and_table():
    row = Sustained("NPU", 300.0, 40000, 7.0, 7.7, 11.0, None)
    assert row.slowdown == pytest.approx(1.1)
    table = to_markdown([row], "x")
    assert "| NPU | 300 | 40000 | 7.00 | 7.70 | 1.10× | 11.00 | n/a |" in table


def test_runs_a_tiny_model_on_the_cpu(tmp_path):
    import openvino as ov
    from openvino import opset13 as ops

    x = ops.parameter([1, 4], np.float32, name="x")
    xml = tmp_path / "m.xml"
    ov.save_model(ov.Model([ops.relu(x)], [x]), xml)
    row = run(xml, "CPU", seconds=0.3, window_s=0.1)
    assert row.inferences > 10 and row.first_p50_ms > 0
