from types import SimpleNamespace

import numpy as np
import pytest

from train.fetch import fetch_command, find_export, zero_observation


def test_fetch_command_gets_the_jobs_openvino_folder(tmp_path):
    assert fetch_command("smolvla-place-50ep", tmp_path, ".venv/bin/modal") == [
        ".venv/bin/modal", "volume", "get", "sortsense-runs", "smolvla-place-50ep/openvino", str(tmp_path)]


@pytest.mark.parametrize("nested", ["", "openvino"])
def test_find_export_finds_the_manifest_nested_or_not(tmp_path, nested):
    folder = tmp_path / nested
    folder.mkdir(exist_ok=True)
    (folder / "manifest.json").write_text("{}")
    assert find_export(tmp_path) == folder


def test_find_export_says_when_there_is_nothing(tmp_path):
    with pytest.raises(FileNotFoundError):
        find_export(tmp_path)


def test_zero_observation_has_a_batch_axis_and_the_task():
    features = [SimpleNamespace(name="state", ftype="STATE", shape=[6]),
                SimpleNamespace(name="images.top", ftype="VISUAL", shape=[3, 480, 640]),
                SimpleNamespace(name="task", ftype="LANGUAGE", shape=[1])]
    obs = zero_observation(features, "the brick is perfect")
    assert obs["state"].shape == (1, 6) and obs["images.top"].shape == (1, 3, 480, 640)
    assert obs["state"].dtype == np.float32 and obs["task"] == ["the brick is perfect"]
