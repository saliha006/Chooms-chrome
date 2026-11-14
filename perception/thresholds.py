"""The uncertainty band (PRD §6, decisions.md D7): two thresholds set from data.

Scores are distances, not probabilities, so the band comes from percentiles of held-out
scores: t_low = 99th percentile of good, t_high = 5th percentile of defective.
"""

from pathlib import Path

import numpy as np
import yaml

LABELS = ("perfect", "uncertain", "defective")


def band(good: np.ndarray, defective: np.ndarray) -> tuple[float, float]:
    """Return (t_low, t_high). Overlapping distributions put the overlap in the uncertain band."""
    if len(good) == 0 or len(defective) == 0:
        raise ValueError("need at least one good and one defective score")
    a, b = float(np.percentile(good, 99)), float(np.percentile(defective, 5))
    return min(a, b), max(a, b)


def classify(score: float, t_low: float, t_high: float) -> str:
    if score < t_low:
        return "perfect"
    if score > t_high:
        return "defective"
    return "uncertain"


def confusion(good: np.ndarray, defective: np.ndarray, t_low: float, t_high: float) -> dict[str, dict[str, int]]:
    """Rows = true class, columns = predicted label."""
    return {
        truth: {label: sum(classify(s, t_low, t_high) == label for s in scores) for label in LABELS}
        for truth, scores in (("good", good), ("defective", defective))
    }


def save(path: Path, t_low: float, t_high: float, **extra) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump({"t_low": t_low, "t_high": t_high, **extra}, sort_keys=False))


def load_all(path: Path) -> dict:
    return yaml.safe_load(path.read_text())


def load(path: Path) -> tuple[float, float]:
    data = load_all(path)
    return float(data["t_low"]), float(data["t_high"])
