"""Lighting-drift alarm (PRD F15, decisions.md D14): perfect bricks scoring closer and closer to t_low.

Scores are distances, so the alarm measures how far the recent perfect bricks have crept from the
good-brick baseline towards t_low: 0 = at the baseline, 1 = at t_low. The baseline is the mean
out-of-fold good score that perception.evaluate saves as `good_mean` in thresholds.yaml.
Harry's consumer feeds it the `score` of INSPECT rows labelled perfect, oldest first; the first look
only, not the re-inspection looks, which are scored on purpose under different conditions.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from perception import thresholds

WINDOW = 8  # TUNE: how many of the latest perfect bricks are averaged
MIN_BRICKS = 5  # TUNE: fewer perfect bricks than this is too noisy to alarm on
ALERT_AT = 0.5  # TUNE: halfway from the baseline to t_low


@dataclass(frozen=True)
class Drift:
    fraction: float
    alert: bool
    bricks: int


def baseline(thresholds_path: Path) -> float:
    return float(thresholds.load_all(thresholds_path)["good_mean"])


def drift(perfect_scores: Sequence[float], good_mean: float, t_low: float,
          window: int = WINDOW, min_bricks: int = MIN_BRICKS, alert_at: float = ALERT_AT) -> Drift:
    """No alarm until `min_bricks` perfect bricks are in. t_low at or below the baseline cannot drift."""
    recent = np.asarray(perfect_scores[-window:], float)
    span = t_low - good_mean
    if len(recent) < min_bricks or span <= 0:
        return Drift(0.0, False, len(recent))
    fraction = float((recent.mean() - good_mean) / span)
    return Drift(fraction, fraction >= alert_at, len(recent))
