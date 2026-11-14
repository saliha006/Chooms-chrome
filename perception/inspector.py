"""OpenVINO inference for the INSPECT state: frame in, DefectSignal out (PRD 7.3).

Compiles the exported IR on the first device that works in NPU -> GPU -> CPU order (decisions.md D8),
with a compile cache so the second start is fast. Anomalib's exported graph already normalises the
score and the anomaly map to [0, 1]; the band in thresholds.yaml is set on those same scores.
"""

import time
from pathlib import Path

import cv2
import numpy as np
import openvino as ov

from perception import thresholds
from common.interfaces import DefectSignal

DEVICE_CHAIN = ("NPU", "GPU", "CPU")
INPUT_SIDE = 256
NORMALISED_PIXEL_THRESHOLD = 0.5  # only for old IRs exported with normalisation; raw-score IRs carry pixel_threshold in thresholds.yaml


def to_input(frame_bgr: np.ndarray) -> np.ndarray:
    rgb = cv2.cvtColor(cv2.resize(frame_bgr, (INPUT_SIDE, INPUT_SIDE), interpolation=cv2.INTER_AREA), cv2.COLOR_BGR2RGB)
    return (rgb.astype(np.float32) / 255.0).transpose(2, 0, 1)[None]


def largest_blob(anomaly_map: np.ndarray, threshold: float) -> tuple[int, int, int, int] | None:
    """(x, y, w, h) of the biggest region above the pixel threshold, in input-image pixels."""
    mask = (anomaly_map >= threshold).astype(np.uint8)
    count, _, stats, _ = cv2.connectedComponentsWithStats(mask)
    if count < 2:
        return None
    biggest = 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))
    x, y, w, h = (int(v) for v in stats[biggest, :4])
    return x, y, w, h


class Scorer:
    def __init__(self, xml: Path, devices: tuple[str, ...] = DEVICE_CHAIN, cache_dir: Path = Path("runs/ov_cache")):
        core = ov.Core()
        cache_dir.mkdir(parents=True, exist_ok=True)
        model = core.read_model(xml)
        self.skipped: list[tuple[str, str]] = []  # (device, reason) for each device that failed to compile
        for device in devices:
            if device not in core.available_devices:
                self.skipped.append((device, "not available"))
                continue
            try:
                # Per-compile cache for CPU/GPU only: a core-wide CACHE_DIR would replace the NPU driver's own cache.
                config = {} if device == "NPU" else {"CACHE_DIR": str(cache_dir)}
                self.compiled = core.compile_model(model, device, config)
            except RuntimeError as err:
                self.skipped.append((device, str(err).splitlines()[0]))
                continue
            self.device = device
            break
        else:
            raise RuntimeError(f"no device could compile {xml}: {self.skipped}")

    def score(self, frame_bgr: np.ndarray) -> tuple[float, np.ndarray, float]:
        """Return (score, anomaly map HxW, latency in ms)."""
        start = time.perf_counter()
        out = self.compiled(to_input(frame_bgr))
        latency_ms = (time.perf_counter() - start) * 1000
        return float(out["pred_score"].ravel()[0]), out["anomaly_map"][0, 0], latency_ms


class Inspector:
    def __init__(self, xml: Path, thresholds_path: Path, model_name: str, heatmap_dir: Path = Path("runs/heatmaps"), **scorer_kwargs):
        self.scorer = Scorer(xml, **scorer_kwargs)
        self.t_low, self.t_high = thresholds.load(thresholds_path)
        self.pixel_threshold = thresholds.load_all(thresholds_path).get("pixel_threshold", NORMALISED_PIXEL_THRESHOLD)
        self.model_name = model_name
        self.heatmap_dir = heatmap_dir
        heatmap_dir.mkdir(parents=True, exist_ok=True)

    def inspect(self, frame: np.ndarray, view: str, brick_id: int) -> DefectSignal:
        score, anomaly_map, latency_ms = self.scorer.score(frame)
        label = thresholds.classify(score, self.t_low, self.t_high)
        heatmap = self.heatmap_dir / f"brick{brick_id:04d}_{view}.png"
        self._save_heatmap(frame, anomaly_map / (2 * self.pixel_threshold), heatmap)  # threshold sits mid-scale
        return DefectSignal(
            brick_id=brick_id,
            view=view,
            label=label,
            score=score,
            t_low=self.t_low,
            t_high=self.t_high,
            bbox=None if label == "perfect" else largest_blob(anomaly_map, self.pixel_threshold),
            heatmap_path=str(heatmap),
            model=self.model_name,
            device=self.scorer.device,
            latency_ms=latency_ms,
        )

    @staticmethod
    def _save_heatmap(frame_bgr: np.ndarray, anomaly_map: np.ndarray, path: Path) -> None:
        base = cv2.resize(frame_bgr, (INPUT_SIDE, INPUT_SIDE), interpolation=cv2.INTER_AREA)
        colour = cv2.applyColorMap((np.clip(anomaly_map, 0, 1) * 255).astype(np.uint8), cv2.COLORMAP_JET)
        cv2.imwrite(str(path), cv2.addWeighted(base, 0.6, colour, 0.4, 0))
