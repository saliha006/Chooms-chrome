import numpy as np
import yaml

from perception.scene import Zone
from ui.click_regions import Clicker, save_regions


def test_four_corners_per_region_in_order():
    clicker = Clicker(("zone", "bowl_red"))
    for i in range(4):
        assert clicker.current == "zone"
        clicker.click(10 * i, 5)
    assert clicker.prompt() == "bowl_red: click top-left"
    for i in range(4):
        clicker.click(100 + i, 50)
    assert clicker.current is None
    clicker.click(1, 1)  # extra clicks are ignored
    assert len(clicker.points["bowl_red"]) == 4


def test_undo_steps_back_across_regions():
    clicker = Clicker(("zone", "bowl_red"))
    for i in range(5):
        clicker.click(i, i)
    clicker.undo()
    clicker.undo()
    assert len(clicker.points["zone"]) == 3 and clicker.points["bowl_red"] == []


def test_draw_does_not_touch_the_frame():
    frame = np.zeros((48, 64, 3), np.uint8)
    clicker = Clicker()
    clicker.click(5, 5)
    clicker.draw(frame)
    assert not frame.any()


def test_saved_regions_load_as_a_zone_and_keep_comments(tmp_path):
    path = tmp_path / "scene.yaml"
    path.write_text("# header\nzone: null   # pick zone\nbowl_red: null\n")
    corners = [(100, 100), (200, 100), (200, 200), (100, 200)]
    save_regions(path, {"zone": corners})
    text = path.read_text()
    assert "# header" in text and "# pick zone" in text
    zone = Zone(yaml.safe_load(text)["zone"])
    assert np.allclose(zone.table(np.array([[150, 150]])), [[5, 5]])  # centre of the zone = 5 cm, 5 cm
