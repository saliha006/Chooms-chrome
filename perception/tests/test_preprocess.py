import numpy as np
import openvino as ov
import openvino.opset13 as ops
import pytest

from perception.inspector import Scorer, to_input
from perception.preprocess import with_preprocessing


def toy_ir(path):
    """Two outputs shaped like Anomalib's. The anomaly map weights R, G, B by 1, 2, 3, so a swapped
    channel, a missing /255 or a wrong layout all change the numbers."""
    x = ops.parameter([1, 3, 256, 256], ov.Type.f32, name="input")
    weights = ops.constant(np.array([1, 2, 3], np.float32).reshape(1, 3, 1, 1))
    amap = ops.reduce_sum(ops.multiply(x, weights), ops.constant(np.array([1])), keep_dims=True)
    score = ops.reduce_max(amap, ops.constant(np.array([1, 2, 3])), keep_dims=False)
    amap.output(0).get_tensor().set_names({"anomaly_map"})
    score.output(0).get_tensor().set_names({"pred_score"})
    ov.save_model(ov.Model([score, amap], [x], "toy"), path)
    return path


@pytest.fixture
def irs(tmp_path):
    plain = toy_ir(tmp_path / "model.xml")
    return plain, with_preprocessing(plain)


def test_ppp_ir_takes_a_resized_bgr_uint8_frame(irs):
    model = ov.Core().read_model(irs[1])
    assert model.inputs[0].get_element_type() == ov.Type.u8
    assert list(model.inputs[0].get_shape()) == [1, 256, 256, 3]


def test_scores_match_the_cpu_preprocessing_path(irs):
    frame = np.random.default_rng(1).integers(0, 256, (480, 640, 3), dtype=np.uint8)
    plain, ppp = (Scorer(xml, devices=("CPU",)) for xml in irs)
    assert not plain.in_graph_preprocessing and ppp.in_graph_preprocessing
    s0, map0, _ = plain.score(frame)
    s1, map1, _ = ppp.score(frame)
    assert s1 == pytest.approx(s0, rel=1e-5)
    np.testing.assert_allclose(map1, map0, rtol=1e-5, atol=1e-5)


def test_to_input_in_graph_is_uint8_nhwc_bgr_untouched():
    frame = np.zeros((480, 640, 3), np.uint8)
    frame[..., 2] = 255
    x = to_input(frame, in_graph=True)
    assert x.shape == (1, 256, 256, 3) and x.dtype == np.uint8 and x[0, 0, 0, 2] == 255


def test_original_ir_is_left_alone(irs):
    assert ov.Core().read_model(irs[0]).inputs[0].get_element_type() == ov.Type.f32
