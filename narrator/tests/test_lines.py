import sys

import pytest

import narrator
from common.reasons import Reason
from narrator import cache
from narrator.lines import EVENTS, LINES, line_for


@pytest.mark.parametrize("persona", ["calm", "cowboy"])
def test_every_event_and_reason_has_a_line(persona):
    missing = [event for event in EVENTS if event not in LINES[persona]]
    assert missing == []


def test_every_reason_is_an_event():
    assert {f"help.{r.value}" for r in Reason} <= set(EVENTS)


def test_cached_lines_hold_no_placeholders():
    assert not [text for lines in LINES.values() for text in lines.values() if "{" in text]


def test_help_resolves_by_reason():
    assert line_for("calm", "help", "camera") == LINES["calm"]["help.camera"]


def test_say_speaks_the_line_not_the_event(caplog):
    with caplog.at_level("INFO", logger="narrator"):
        narrator.say("help", reason="grasp_failed")
    assert LINES["calm"]["help.grasp_failed"] in caplog.text


def test_generation_writes_one_wav_per_line_and_skips_existing(tmp_path, monkeypatch):
    calls = []

    class FakeTTS:
        def convert(self, **kw):
            calls.append(kw)
            return iter([b"RIFF", b"fake"])

    class FakeClient:
        def __init__(self, api_key):
            self.text_to_speech = FakeTTS()

    import elevenlabs.client

    monkeypatch.setattr(elevenlabs.client, "ElevenLabs", FakeClient)
    monkeypatch.setattr(cache, "CLIPS", tmp_path)
    monkeypatch.setattr(cache, "load_dotenv", lambda: None)
    monkeypatch.setenv("ELEVENLABS_API_KEY", "test")
    monkeypatch.setattr(sys, "argv", ["cache"])

    cache.main()
    total = sum(len(lines) for lines in LINES.values())
    assert len(calls) == total
    assert (tmp_path / "cowboy" / "obstacle.wav").read_bytes() == b"RIFFfake"
    assert {c["output_format"] for c in calls} == {"wav_22050"}

    calls.clear()
    cache.main()
    assert calls == []  # nothing regenerated without --force
