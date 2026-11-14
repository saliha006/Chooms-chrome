from pathlib import Path

import numpy as np
import openvino as ov
import openvino.opset13 as ops
import pytest

from bench.benchmark import label
from bench.operators import Support, op_support, to_markdown


@pytest.fixture
def toy_xml(tmp_path) -> Path:
    x = ops.parameter([1, 4], ov.Type.f32, name="x")
    y = ops.relu(ops.multiply(x, ops.constant(np.full((1, 4), 2, np.float32))))
    xml = tmp_path / "toy.xml"
    ov.save_model(ov.Model([y], [x], "toy"), xml)
    return xml


def test_cpu_runs_every_operator_of_a_plain_model(toy_xml):
    support = op_support(toy_xml, "CPU")
    assert support.total >= 2 and support.unsupported == {} and support.supported == support.total


def test_markdown_lists_gaps_by_type():
    table = to_markdown([("padim/fp16", "NPU", Support(10, {"Interpolate": 2})), ("padim/fp16", "CPU", Support(10, {}))])
    assert "| padim/fp16 | NPU | 10 | 8 | Interpolate x2 |" in table
    assert "| padim/fp16 | CPU | 10 | 10 | none |" in table


def test_ppp_model_gets_its_own_label(tmp_path):
    base = tmp_path / "padim/fp16/weights/openvino"
    assert label(base / "model_ppp.xml", tmp_path) == "padim/fp16 + in-graph preprocessing"
    assert label(base / "model.xml", tmp_path) == "padim/fp16"
