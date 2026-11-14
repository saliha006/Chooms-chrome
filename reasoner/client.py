"""One Nemotron 3.5 Super VL call: brick crop + DefectSignal in, one short spoken line out.

NVIDIA Build is OpenAI-compatible; stdlib HTTP keeps the dependency list unchanged.
Needs NVIDIA_API_KEY and NEMOTRON_MODEL (the exact Super VL id from build.nvidia.com) in the
environment. Never call this from the control loop (decisions.md D4, D11).

    python -m reasoner.client data/defective/0000.png
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

from perception.contract import DefectSignal

BASE_URL = "https://integrate.api.nvidia.com/v1/chat/completions"
SYSTEM = (
    "You are the voice of a brick-sorting robot. In one sentence of at most 20 words, explain the verdict "
    "using only the numbers given (score, thresholds) and what you see in the image. Never contradict the label. "
    'Reply as JSON: {"line": "..."}'
)


def _image_url(crop_bgr: np.ndarray) -> str:
    ok, png = cv2.imencode(".png", crop_bgr)
    if not ok:
        raise ValueError("could not encode the crop")
    return "data:image/png;base64," + base64.b64encode(png.tobytes()).decode()


def request_body(crop_bgr: np.ndarray, signal: DefectSignal, persona: str, model: str) -> dict:
    facts = {k: v for k, v in asdict(signal).items() if k in ("label", "score", "t_low", "t_high", "bbox", "view")}
    return {
        "model": model,
        "max_tokens": 80,
        "temperature": 0.3,
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
