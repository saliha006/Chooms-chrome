"""DefectSignal as frozen in PRD 7.3.

Harry owns the canonical copy in `common/interfaces.py`; until that lands on `main`,
this mirror keeps perception importable. Delete the fallback once his file exists.
"""

from dataclasses import dataclass

try:
    from common.interfaces import DefectSignal
except ImportError:

    @dataclass
    class DefectSignal:
        brick_id: int
        view: str  # "webcam" | "realsense" | "wrist"
        label: str  # "perfect" | "defective" | "uncertain"
        score: float
        t_low: float
        t_high: float
        bbox: tuple | None
        heatmap_path: str | None
        model: str
        device: str
        latency_ms: float


__all__ = ["DefectSignal"]
