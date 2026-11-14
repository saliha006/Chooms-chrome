"""SortSense cell: one brick at a time through the PRD 7.1 state machine.

    python run.py --mock                    # whole loop with stand-ins, no hardware
    python run.py --scripted pick,place     # real arm with scripted motion (Block B)

IDLE → LOCATE → PICK → VERIFY_GRASP → INSPECT → DECIDE → [REINSPECT] → PLACE → LOG → next.
Any error → HOME plus a spoken message, then the run stops for a person to look.
"""

import argparse
import logging
import sys
import time
import uuid
from contextlib import contextmanager
from pathlib import Path

import yaml

import narrator
import telemetry
from common.capture import SharedCapture
from common.interfaces import DefectSignal, Inspector, Mover

CONFIG = Path(__file__).parent / "config"
GRASP_ATTEMPTS = 2  # PRD §6: retry once, then ask for help
_log = logging.getLogger("run")


class HelpNeeded(Exception):
    """The cell can't carry on without a person."""


class Cell:
    def __init__(self, capture: SharedCapture, inspector: Inspector, picker: Mover, placer: Mover,
                 locator, rules: dict, views: dict[str, str], run_id: str):
        self.capture = capture
        self.inspector = inspector
        self.picker = picker
        self.placer = placer
        self.locator = locator
        self.rules = rules
        self.views = views
        self.run_id = run_id
        self.state = "IDLE"
        self.sorted = 0

    def run(self) -> None:
        try:
            while True:
                with self._stage("LOCATE", self.sorted + 1) as row:
                    present = self.locator.next_brick()
                    row["outcome"] = "brick" if present else "empty"
                if not present:
                    break
                self.sort_one(self.sorted + 1)
                self.sorted += 1
            narrator.say("empty", n=self.sorted)
        except Exception as exc:
            _log.exception("run stopped")
            narrator.say("help", reason=type(exc).__name__)
            self.state = "HOME"
            self.picker.home()
            raise
        finally:
            self.state = "IDLE"

    def sort_one(self, brick_id: int) -> None:
        self._pick(brick_id)
        arm_still = time.monotonic()
        signal = self._inspect(brick_id, "inspect", newer_than=arm_still)
        narrator.say(signal.label, score=signal.score, bbox=signal.bbox)

        with self._stage("DECIDE", brick_id, signal) as row:
            label = signal.label
            row["outcome"] = label
        if label == "uncertain":
            label = self._resolve_uncertain(brick_id)

        instruction = self.rules[label]
        with self._stage("PLACE", brick_id, note=instruction) as row:
            if not self.placer.place(instruction):
                raise HelpNeeded("place failed")
            row["outcome"] = "placed"
        with self._stage("LOG", brick_id, signal, label=label) as row:
            row["outcome"] = "sorted"

    def _pick(self, brick_id: int) -> None:
        for attempt in range(1, GRASP_ATTEMPTS + 1):
            with self._stage("PICK", brick_id, note=f"attempt {attempt}") as row:
                presented = self.picker.pick_and_present()
                row["outcome"] = "presented" if presented else "failed"
            with self._stage("VERIFY_GRASP", brick_id) as row:
                held = presented and not self.picker.gripper_empty()
                row["outcome"] = "held" if held else "empty"
            if held:
                return
            if attempt < GRASP_ATTEMPTS:
                narrator.say("grasp_fail")
        raise HelpNeeded("grasp failed twice")

    def _inspect(self, brick_id: int, role: str, newer_than: float = 0.0) -> DefectSignal:
        with self._stage("INSPECT", brick_id, note=role) as row:
            frame = self.capture.frame(role, newer_than=newer_than)
            signal = self.inspector.inspect(frame, self.views[role], brick_id)
            row.update(label=signal.label, score=signal.score, device=signal.device, outcome=signal.label)
        return signal

    def _resolve_uncertain(self, brick_id: int) -> str:
        """PRD §6 / F4: second view (free) → each reinspect motion → the rules' fallback label."""
        chain = self.rules["uncertain"]
        signal = self._inspect(brick_id, chain["second_view"])
        if signal.label != "uncertain":
            narrator.say(signal.label, score=signal.score, bbox=signal.bbox, after="second view")
            return signal.label
        for angle in chain["reinspect_angles"]:
            with self._stage("REINSPECT", brick_id, note=f"angle {angle}") as row:
                if not self.picker.reinspect(angle):
                    raise HelpNeeded(f"reinspect {angle} lost the brick")
                row["outcome"] = "back at inspection pose"
            signal = self._inspect(brick_id, "inspect", newer_than=time.monotonic())
            if signal.label != "uncertain":
                narrator.say(signal.label, score=signal.score, bbox=signal.bbox, after=f"reinspect {angle}")
                return signal.label
        narrator.say("still_uncertain", label=chain["then"])
        return chain["then"]

    @contextmanager
    def _stage(self, state: str, brick_id: int, signal: DefectSignal | None = None, **extra):
        """Sets the visible state, times the stage and writes one `events` row (PRD 7.3)."""
        self.state = state
        row = {"label": None, "score": None, "device": None, "outcome": None, "note": None}
        if signal is not None:
            row.update(label=signal.label, score=signal.score, device=signal.device)
        row.update(extra)
        start = time.perf_counter()
        try:
            yield row
        except Exception as exc:
            row["outcome"] = f"error: {exc}"
            raise
        finally:
            telemetry.log(run_id=self.run_id, brick_id=brick_id, ts=time.time(), state=state, stage=state.lower(),
                          latency_ms=round((time.perf_counter() - start) * 1000, 2), **row)


def parse_scripted(text: str) -> set[str]:
    parts = set(text.split(","))
    if not parts <= {"pick", "place"}:
        raise argparse.ArgumentTypeError("use pick, place or pick,place")
    return parts


def build_mock(bricks: int, run_id: str) -> Cell:
    from common.mocks import MockCamera, MockInspector, MockLocator, MockMover

    cameras = yaml.safe_load((CONFIG / "cameras.yaml").read_text())
    rules = yaml.safe_load((CONFIG / "rules.yaml").read_text())
    capture = SharedCapture({role: MockCamera(fps=30) for role in cameras}).start()
    mover = MockMover()
    return Cell(capture, MockInspector(), mover, mover, MockLocator(bricks), rules,
                {role: cam["view"] for role, cam in cameras.items()}, run_id)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--mock", action="store_true", help="stand-in cameras, inspector and arm")
    ap.add_argument("--scripted", type=parse_scripted, default=set(), help="pick, place or pick,place use waypoints")
    ap.add_argument("--bricks", type=int, default=5, help="bricks in the zone (mock only)")
    args = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s", datefmt="%H:%M:%S")

    if not args.mock:
        sys.exit("Real hardware wiring arrives in Block B (A7 scripted fallback, F9 localization). Use --mock.")

    run_id = time.strftime("%Y%m%d-%H%M%S-") + uuid.uuid4().hex[:4]
    telemetry.start(Path("runs/events.jsonl"))
    cell = build_mock(args.bricks, run_id)
    try:
        cell.run()
    except Exception:
        sys.exit(1)  # already logged, spoken and homed by Cell.run
    finally:
        cell.capture.stop()
        telemetry.stop()
        _log.info("run %s: %d bricks sorted", run_id, cell.sorted)


if __name__ == "__main__":
    main()
