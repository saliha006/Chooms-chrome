import io
import json

import numpy as np

from perception.contract import DefectSignal
from reasoner import client

SIGNAL = DefectSignal(3, "webcam", "defective", 0.64, 0.2, 0.63, (1, 2, 3, 4), None, "padim", "CPU", 50.0)


def reply(content: str) -> dict:
    return {"choices": [{"message": {"content": content}}]}


def test_request_carries_numbers_image_and_persona():
    body = client.request_body(np.zeros((8, 8, 3), np.uint8), SIGNAL, "cowboy", "some/model")
    facts = json.loads(body["messages"][1]["content"][0]["text"])
    assert facts == {"view": "webcam", "label": "defective", "score": 0.64, "t_low": 0.2, "t_high": 0.63, "bbox": [1, 2, 3, 4]}
    assert body["messages"][1]["content"][1]["image_url"]["url"].startswith("data:image/png;base64,")
    assert "Persona: cowboy" in body["messages"][0]["content"]
    assert body["chat_template_kwargs"] == {"enable_thinking": False}


def test_parse_line_reads_json_even_inside_prose():
    assert client.parse_line(reply('Sure! {"line": "Red bowl, partner."}')) == "Red bowl, partner."


def test_parse_line_falls_back_to_raw_text():
    assert client.parse_line(reply("Red bowl.")) == "Red bowl."


def test_explain_posts_with_key_and_returns_line(monkeypatch):
    seen = {}

    def fake_urlopen(req, timeout):
        seen["auth"], seen["timeout"] = req.get_header("Authorization"), timeout
        return io.BytesIO(json.dumps(reply('{"line": "Score 0.64, past 0.63. Red bowl."}')).encode())

    monkeypatch.setenv("NVIDIA_API_KEY", "test-key")
    monkeypatch.setenv("NEMOTRON_MODEL", "some/model")
    monkeypatch.setattr(client.urllib.request, "urlopen", fake_urlopen)
    line, ms = client.explain(np.zeros((8, 8, 3), np.uint8), SIGNAL, timeout_s=2.0)
    assert line == "Score 0.64, past 0.63. Red bowl."
    assert seen == {"auth": "Bearer test-key", "timeout": 2.0} and ms >= 0
