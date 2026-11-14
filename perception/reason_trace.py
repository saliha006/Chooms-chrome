"""Why the cell decided what it did, per brick (decisions.md D22, D25): the numbers, where the defect is, every
recovery step and the final call. Shown on the mission-control panel, logged in the telemetry `note` column, and
the facts the spoken line is built from. Derived from DefectSignal; no contract change.
"""

from dataclasses import asdict, dataclass, field

from common.interfaces import DefectSignal

ROWS = ("top", "middle", "bottom")
COLS = ("left", "centre", "right")
INPUT_SIDE = 256  # the inspection crop the bbox refers to (perception.inspector)


def region(bbox: tuple | None, side: int = INPUT_SIDE) -> str | None:
    """Where the defect sits on the inspection image, as a 3 x 3 grid cell: 'top-left' ... 'bottom-right'."""
    if bbox is None:
        return None
    x, y, w, h = bbox
    col = min(int((x + w / 2) / side * 3), 2)
    row = min(int((y + h / 2) / side * 3), 2)
    return f"{ROWS[row]}-{COLS[col]}"


def margin(score: float, t_low: float, t_high: float) -> float:
    """Signed distance to the nearest threshold: positive = clearly on one side, near 0 = borderline."""
    if score < t_low:
        return t_low - score
    if score > t_high:
        return score - t_high
    return -min(score - t_low, t_high - score)  # inside the uncertain band


@dataclass
class ReasonTrace:
    brick_id: int
    score: float
    t_low: float
    t_high: float
    margin: float
    region: str | None
    decision: str  # "perfect" | "defective"
    reason: str  # one plain sentence
    steps: list[tuple[str, float]] = field(default_factory=list)  # (recovery step, score after it)

    @classmethod
    def from_signal(cls, signal: DefectSignal, decision: str, steps: list[tuple[str, float]] = (), reason: str = "") -> "ReasonTrace":
        return cls(signal.brick_id, signal.score, signal.t_low, signal.t_high, margin(signal.score, signal.t_low, signal.t_high),
                   region(signal.bbox), decision, reason or default_reason(signal, decision, steps), list(steps))

    def note(self) -> str:
        chain = " > ".join(f"{name} {score:.1f}" for name, score in self.steps)
        where = f" at {self.region}" if self.region else ""
        return (f"{self.decision}{where}: score {self.score:.1f} vs {self.t_low:.1f}/{self.t_high:.1f} "
                f"(margin {self.margin:+.1f}){' | ' + chain if chain else ''}")

    def as_dict(self) -> dict:
        return asdict(self)


def default_reason(signal: DefectSignal, decision: str, steps) -> str:
    if steps and decision == "defective" and signal.label == "uncertain":
        return f"Still unsure after {len(steps)} more looks, so it goes to the defective bowl to be safe."
    if decision == "defective":
        where = region(signal.bbox)
        return f"Score {signal.score:.1f} is above my defect line of {signal.t_high:.1f}" + (f", mark at the {where}." if where else ".")
    return f"Score {signal.score:.1f} is below my clean line of {signal.t_low:.1f}."
