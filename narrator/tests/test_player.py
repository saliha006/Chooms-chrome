import threading
import time
from pathlib import Path

import narrator
from narrator.player import Player


class SlowSpeaker:
    """Records what it plays; each clip takes `seconds`, and the first can be held until released."""

    def __init__(self, seconds=0.0, hold_first=False):
        self.played: list[str] = []
        self.seconds = seconds
        self.release = threading.Event()
        if not hold_first:
            self.release.set()

    def __call__(self, path: Path):
        self.played.append(path.name)
        self.release.wait(5)
        time.sleep(self.seconds)


def test_submit_never_waits_for_audio():
    player = Player(SlowSpeaker(seconds=0.5))
    start = time.perf_counter()
    player.submit(Path("a.wav"))
    assert time.perf_counter() - start < 0.05
    assert player.wait_idle(5)


def test_newest_line_wins_over_stale_waiting_ones():
    speaker = SlowSpeaker(hold_first=True)
    player = Player(speaker)
    player.submit(Path("first.wav"))
    time.sleep(0.05)  # first.wav is playing
    for name in ("stale1.wav", "stale2.wav", "newest.wav"):
        player.submit(Path(name))
    speaker.release.set()
    player.wait_idle(5)
    assert speaker.played == ["first.wav", "newest.wav"]


def test_help_and_estop_lines_are_never_dropped():
    speaker = SlowSpeaker(hold_first=True)
    player = Player(speaker)
    player.submit(Path("first.wav"))
    time.sleep(0.05)
    player.submit(Path("help.wav"), priority=True)
    player.submit(Path("chatter.wav"))
    speaker.release.set()
    player.wait_idle(5)
    assert speaker.played == ["first.wav", "help.wav", "chatter.wav"]


def test_a_broken_speaker_does_not_stop_anything():
    def broken(path):
        raise OSError("no audio device")

    player = Player(broken)
    player.submit(Path("a.wav"))
    player.submit(Path("b.wav"))
    assert player.wait_idle(5)


def test_no_speaker_means_console_only():
    player = Player(None)
    player.submit(Path("a.wav"))
    assert player.wait_idle(0.1) and player._thread is None


def test_say_plays_the_cached_clip_for_the_line(monkeypatch):
    speaker = SlowSpeaker()
    monkeypatch.setattr(narrator, "_player", Player(speaker))
    narrator.say("help", reason="grasp_failed")
    narrator.say("perfect", text="a live line from the reasoner")  # no clip for live text yet
    narrator.wait_idle(5)
    assert speaker.played == ["help.grasp_failed.wav"]
