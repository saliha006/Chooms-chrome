import numpy as np

from perception.inspector import largest_blob, to_input


def test_to_input_is_static_nchw_rgb_in_unit_range():
    frame = np.zeros((480, 640, 3), np.uint8)
    frame[..., 2] = 255  # pure red in BGR
    x = to_input(frame)
    assert x.shape == (1, 3, 256, 256) and x.dtype == np.float32
    assert x[0, 0].min() == 1.0 and x[0, 2].max() == 0.0  # red lands in the R channel


def test_largest_blob_picks_the_biggest_region():
    amap = np.zeros((256, 256), np.float32)
    amap[10:14, 10:14] = 0.9
    amap[100:140, 50:70] = 0.8
    assert largest_blob(amap, 0.5) == (50, 100, 20, 40)


def test_largest_blob_none_below_threshold():
    assert largest_blob(np.full((256, 256), 0.3, np.float32), 0.5) is None


def test_largest_blob_uses_raw_scale_threshold():
    amap = np.full((256, 256), 40.0, np.float32)
    amap[0:10, 0:10] = 250.0
    assert largest_blob(amap, 120.0) == (0, 0, 10, 10)


def test_inspect_scores_the_same_crop_capture_saves(tmp_path):
    from perception.capture import square_crop
    from perception.inspector import Inspector

    seen = []

    class FakeScorer:
        device = "CPU"

        def score(self, frame):
            seen.append(frame)
            return 0.1, np.zeros((256, 256), np.float32), 1.0

    inspector = Inspector.__new__(Inspector)
    inspector.scorer, inspector.crop = FakeScorer(), None
    inspector.t_low, inspector.t_high, inspector.pixel_threshold = 0.2, 0.6, 0.5
    inspector.model_name, inspector.heatmap_dir = "padim", tmp_path
    frame = np.random.default_rng(0).integers(0, 255, (480, 640, 3), dtype=np.uint8)
    signal = inspector.inspect(frame, "webcam", 1)
    assert signal.label == "perfect"
    assert np.array_equal(seen[0], square_crop(frame))  # centred 480x480 square, resized to 256: what capture saves
