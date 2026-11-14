import pytest

pytest.importorskip("pyarrow")

from train.commands import act, parse_episode_ids  # noqa: E402
from train.hedge import episodes_by_task, modal_commands, tag_for  # noqa: E402
from train.tests.test_episode_audit import TASKS, clean  # noqa: E402


def test_each_string_gets_its_own_episodes(tmp_path):
    found = episodes_by_task(clean(tmp_path, n=6))
    assert found == {TASKS[0]: [0, 2, 4], TASKS[1]: [1, 3, 5]}


def test_a_task_with_no_episodes_is_left_out(tmp_path):
    root = clean(tmp_path, n=1)
    assert list(episodes_by_task(root)) == [TASKS[0]]


def test_modal_commands_name_the_colour_and_the_ids():
    lines = modal_commands("me/ds", {TASKS[0]: [0, 2], TASKS[1]: [1, 3]}, 5000)
    assert "--tag purple --episode-ids 0,2" in lines[0] and "--tag orange --episode-ids 1,3" in lines[1]
    assert all("--steps 5000" in line and "--dataset me/ds" in line for line in lines)


def test_a_string_without_a_colour_is_refused():
    with pytest.raises(ValueError, match="no bowl colour"):
        tag_for("the brick is fine")


def test_act_command_uses_the_exact_episode_list():
    cmd = act("u/d", 10, "/runs/z", episode_ids=(1, 3, 5))
    assert cmd[cmd.index("--data.episodes") + 1] == "[1,3,5]"


def test_episode_ids_override_the_first_n():
    cmd = act("u/d", 10, "/runs/z", episodes=9, episode_ids=(4,))
    assert cmd.count("--data.episodes") == 1 and cmd[cmd.index("--data.episodes") + 1] == "[4]"


@pytest.mark.parametrize("text,policy,sweep", [("1,x", "act", False), ("1,1", "act", False), ("-1,2", "act", False),
                                               ("1,2", "smolvla", False), ("1,2", "act", True)])
def test_bad_episode_ids_are_refused(text, policy, sweep):
    with pytest.raises(SystemExit):
        parse_episode_ids(text, policy, sweep)


def test_good_episode_ids_parse():
    assert parse_episode_ids("0,2,4", "act", False) == (0, 2, 4)
