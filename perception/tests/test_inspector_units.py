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
    assert largest_blob(amap) == (50, 100, 20, 40)


def test_largest_blob_none_below_threshold():
    assert largest_blob(np.full((256, 256), 0.3, np.float32)) is None
