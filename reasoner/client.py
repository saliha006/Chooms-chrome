"""One Nemotron 3.5 Super VL call: brick crop + DefectSignal in, one short spoken line out.

NVIDIA Build is OpenAI-compatible; stdlib HTTP keeps the dependency list unchanged.
Needs NVIDIA_API_KEY and NEMOTRON_MODEL (nvidia/nemotron-3.5-super-vl-120b-a12b) in the environment. Never call this from the control loop (decisions.md D4, D11).

    python -m reasoner.client data/defective/b00_0000.png
"""

import base64
import json
import os
import sys
import time
import urllib.request
from dataclasses import asdict

import cv2
import numpy as np

from common.interfaces import DefectSignal

BASE_URL = "https://integrate.api.nvidia.com/v1/chat/completions"
ACTIONS = {"perfect": "place it in the blue bowl", "defective": "place it in the red bowl", "uncertain": "take a second look"}
BAND = "score below t_low means perfect, above t_high means defective, in between means uncertain"
SYSTEM = (
    "You are a brick-sorting robot thinking aloud while you work. In one or two short sentences (at most 30 words), "
    "say what you see on the brick, what the score means against your thresholds, and what you will do and why. "
    "The label and action are already decided: explain them, never change them. Use only the numbers given. "
    "Sound like a person talking, not a report. "
    'Reply as JSON: {"line": "..."}'
)


def _image_url(crop_bgr: np.ndarray) -> str:
    ok, png = cv2.imencode(".png", crop_bgr)
    if not ok:
        raise ValueError("could not encode the crop")
    return "data:image/png;base64," + base64.b64encode(png.tobytes()).decode()


def request_body(crop_bgr: np.ndarray, signal: DefectSignal, persona: str, model: str) -> dict:
    facts = {k: v for k, v in asdict(signal).items() if k in ("label", "score", "t_low", "t_high", "bbox", "view")}
    facts |= {"action": ACTIONS[signal.label], "meaning": BAND}
    return {
        "model": model,
        "max_tokens": 120,
        "temperature": 0.3,
        "chat_template_kwargs": {"enable_thinking": False},  # Super VL reasons by default and spends max_tokens thinking
        "messages": [
            {"role": "system", "content": f"{SYSTEM} Persona: {persona}."},
            {"role": "user", "content": [
                {"type": "text", "text": json.dumps(facts)},
                {"type": "image_url", "image_url": {"url": _image_url(crop_bgr)}},
            ]},
        ],
    }


def parse_line(response: dict) -> str:
    text = response["choices"][0]["message"]["content"].strip()
    start, end = text.find("{"), text.rfind("}")
    return json.loads(text[start : end + 1])["line"] if start != -1 and end > start else text


def explain(crop_bgr: np.ndarray, signal: DefectSignal, persona: str = "calm", timeout_s: float = 5.0) -> tuple[str, float]:
    """Return (line, latency in ms). Raises on HTTP errors and timeouts; the caller falls back to a template."""
    body = json.dumps(request_body(crop_bgr, signal, persona, os.environ["NEMOTRON_MODEL"])).encode()
    req = urllib.request.Request(
        BASE_URL,
        data=body,
        headers={"Authorization": f"Bearer {os.environ['NVIDIA_API_KEY']}", "Content-Type": "application/json"},
    )
    start = time.perf_counter()
    with urllib.request.urlopen(req, timeout=timeout_s) as resp:
        response = json.load(resp)
    return parse_line(response), (time.perf_counter() - start) * 1000


def main() -> None:
    crop = cv2.imread(sys.argv[1])
    signal = DefectSignal(0, "webcam", "defective", 0.64, 0.20, 0.63, (69, 131, 39, 37), None, "padim-int8", "CPU", 50.0)
    line, ms = explain(crop, signal)
    print(f"{ms:.0f} ms: {line}")


if __name__ == "__main__":
    main()
