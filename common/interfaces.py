"""Contracts between the layers, copied from PRD 7.3.

Frozen since 01:00 Saturday: no renamed fields or methods. A change needs all three
builders, a `decision` entry in progress.md, then PRD 7.3 (CLAUDE.md §6).

Module-level functions owned elsewhere, same freeze:
    robot/io.py (Nate): connect(), observe(), act(), torque_off()
    narrator.say(event, text=None, persona=None, **kw) -> None   non-blocking (Harry)
    narrator.trigger(kind) -> None   kind "obstacle" | "hat"; CALM <-> COWBOY (Harry)
    telemetry.log(**row) -> None   non-blocking (Harry)
    reasoner.explain(signal, crop, persona) -> None   async, hands narrator a line or nothing (Saliha)
    reasoner.hat_seen(top_frame) -> bool | None   async, None = no answer in time (Saliha)
"""

from dataclasses import dataclass
from typing import Protocol, runtime_checkable


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


@runtime_checkable
class Inspector(Protocol):  # perception/ (Saliha)
    def inspect(self, frame, view: str, brick_id: int) -> DefectSignal: ...


@runtime_checkable
class Mover(Protocol):  # policies/ (Nate) and fallback/ (Harry)
    def pick_and_present(self) -> bool: ...
    def place(self, instruction: str) -> bool: ...

    # 0 = put the brick down in the pick zone and pick it again; ±90 = roll the wrist in place.
    # True only when the brick is back at the inspection pose (agreed 2026-11-14, decisions.md D7).
    def reinspect(self, angle_deg: int) -> bool: ...

    def gripper_empty(self) -> bool: ...
    def home(self) -> None: ...
    def estop(self) -> None: ...
