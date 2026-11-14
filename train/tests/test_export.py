import os

import pytest

from train.export import checkpoint_for


def touch(path, mtime):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.touch()
    os.utime(path, (mtime, mtime))


def test_act_takes_the_newest_checkpoint_even_when_names_sort_the_other_way(tmp_path):
    ckpts = tmp_path / "lightning_logs" / "version_0" / "checkpoints"
    touch(ckpts / "epoch=0-step=300.ckpt", 1_000)
    touch(ckpts / "epoch=3-step=1000.ckpt", 2_000)  # sorts before step=300 by name
    assert checkpoint_for("act", tmp_path).name == "epoch=3-step=1000.ckpt"


def test_smolvla_takes_the_newest_pretrained_model(tmp_path):
    for step, mtime in (("000100", 1_000), ("000200", 2_000)):
        folder = tmp_path / "checkpoints" / step / "pretrained_model"
        folder.mkdir(parents=True)
        os.utime(folder, (mtime, mtime))
    assert checkpoint_for("smolvla", tmp_path).parent.name == "000200"


def test_a_job_without_a_checkpoint_says_so(tmp_path):
    with pytest.raises(FileNotFoundError):
        checkpoint_for("act", tmp_path)
