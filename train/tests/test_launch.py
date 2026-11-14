import pytest

from train import launch, modal_train


class FakeCall:
    def __init__(self, object_id, result=None, error=None):
        self.object_id, self.result, self.error = object_id, result, error

    def get(self, timeout=None):
        if self.error:
            raise self.error
        return self.result


@pytest.fixture
def deployed(monkeypatch, tmp_path):
    """The deployed app, faked: records spawns and keeps job IDs and runs.md in a temp folder."""
    monkeypatch.setattr(launch, "JOBS", tmp_path / "jobs.json")
    monkeypatch.setattr(modal_train, "RUNS_MD", tmp_path / "runs.md")
    spawned, names = [], []

    class FakeFunction:
        def spawn(self, *args):
            spawned.append(args)
            return FakeCall(f"fc-{len(spawned)}")

    monkeypatch.setattr(launch.modal.Function, "from_name", lambda app, name: names.append((app, name)) or FakeFunction())
    return spawned, names


def test_sweep_spawns_one_act_job_per_size_on_the_deployed_app(deployed):
    spawned, names = deployed
    launch.start("user/bricks", "act", 100, None, 0, True, "2,4", "")
    assert names == [(modal_train.APP_NAME, "train_act")]
    assert [args[3] for args in spawned] == [2, 4]  # episodes per job
    assert [job["call_id"] for job in launch._load()] == ["fc-1", "fc-2"]


def test_smolvla_jobs_carry_the_camera_order(deployed):
    spawned, names = deployed
    launch.start("user/place", "smolvla", 10, None, 0, False, "18", "top,wrist,inspect")
    assert names == [(modal_train.APP_NAME, "train_smolvla")]
    assert spawned[0][-1] == ("top", "wrist", "inspect")


def test_cameras_are_refused_for_act(deployed):
    with pytest.raises(SystemExit):
        launch.start("user/bricks", "act", 10, None, 0, False, "18", "top")


def test_collect_logs_finished_jobs_and_keeps_the_running_ones(deployed, monkeypatch, tmp_path):
    def job(call_id):
        return {"call_id": call_id, "job": f"act-{call_id}", "policy": "act", "dataset": "d", "episodes": 0, "steps": 100}

    launch._save([job("done"), job("busy"), job("broken")])
    calls = {"done": FakeCall("done", result=120.0), "busy": FakeCall("busy", error=launch.NotFinished("not yet")),
             "broken": FakeCall("broken", error=RuntimeError("boom"))}
    monkeypatch.setattr(launch.modal.FunctionCall, "from_id", lambda call_id: calls[call_id])
    launch.collect()
    assert [j["call_id"] for j in launch._load()] == ["busy"]
    assert "act-done" in (tmp_path / "runs.md").read_text()
