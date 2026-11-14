"""SortSense cell: one brick at a time through the PRD 7.1 state machine.

    python run.py --mock                    # whole loop with stand-ins, no hardware
    python run.py --mock --headless         # same, no window (tests, SSH without a display)
    python run.py --scripted pick,place     # real station, scripted motion (the 15:30 gate)
    python run.py --scripted place          # ACT picks, scripted placement
    python run.py                           # ACT picks, SmolVLA places

IDLE → LOCATE → PICK → VERIFY_GRASP → INSPECT → DECIDE → [REINSPECT] → PLACE → LOG → next.
Any error → HOME plus a spoken message, then the run stops for a person to look.
"""

import argparse
import logging
import sys
import threading
import time
import uuid
from contextlib import contextmanager
from pathlib import Path

import yaml

import narrator
import telemetry
from common import estop
from common.capture import SharedCapture
from common.interfaces import DefectSignal, Inspector, Mover
from common.locate import CountLocator

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
        self.mode = "mock"
        self.last_signal: DefectSignal | None = None
        self.stage_ms: dict[str, float] = {}
        self.paused = threading.Event()  # P: hold at the next stage boundary
        self.quit = threading.Event()  # Q: finish this brick, then home and stop

    def run(self) -> None:
        try:
            while not self.quit.is_set():
                with self._stage("LOCATE", self.sorted + 1) as row:
                    present = self.locator.next_brick()
                    row["outcome"] = "brick" if present else "empty"
                if not present:
                    break
                self.sort_one(self.sorted + 1)
                self.sorted += 1
            narrator.say("quit" if self.quit.is_set() else "empty", n=self.sorted)
            self.state = "HOME"
            self.picker.home()
            self.state = "DONE"
        except estop.EStopped:
            self.state = "E-STOP"
            narrator.say("estop")
            raise
        except Exception as exc:
            _log.exception("run stopped")
            narrator.say("help", reason=type(exc).__name__)
            self.state = "HOME"
            self.picker.home()
            self.state = "STOPPED"
            raise

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
            self.last_signal = signal
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
        """Acts on E and P, sets the visible state, times the stage and writes one `events` row (PRD 7.3)."""
        self._checkpoint()
        self.state = state
        row = {"label": None, "score": None, "device": None, "outcome": None, "note": None}
        if signal is not None:
            row.update(label=signal.label, score=signal.score, device=signal.device)
        row.update(extra)
        start = time.perf_counter()
        try:
            yield row
        except estop.EStopped:
            row["outcome"] = "e-stop"
            raise
        except Exception as exc:
            row["outcome"] = f"error: {exc}"
            raise
        finally:
            self.stage_ms[state] = round((time.perf_counter() - start) * 1000, 2)
            telemetry.log(run_id=self.run_id, brick_id=brick_id, ts=time.time(), state=state, stage=state.lower(),
                          latency_ms=self.stage_ms[state], **row)

    def _checkpoint(self) -> None:
        """Runs on the control thread, the only one that talks to the motors (decisions.md D21)."""
        while True:
            if estop.requested():
                self.picker.estop()
                raise estop.EStopped()
            if not self.paused.is_set():
                return
            time.sleep(0.05)


def parse_scripted(text: str) -> set[str]:
    parts = set(text.split(","))
    if not parts <= {"pick", "place"}:
        raise argparse.ArgumentTypeError("use pick, place or pick,place")
    return parts


def load_config(name: str) -> dict:
    return yaml.safe_load((CONFIG / name).read_text())


def views_of(cameras: dict) -> dict[str, str]:
    return {role: cam["view"] for role, cam in cameras.items()}


def build_mock(bricks: int, run_id: str) -> Cell:
    from common.mocks import MockCamera, MockInspector, MockMover

    cameras = load_config("cameras.yaml")
    capture = SharedCapture({role: MockCamera(fps=30) for role in cameras}).start()
    mover = MockMover()
    return Cell(capture, MockInspector(), mover, mover, CountLocator(bricks), load_config("rules.yaml"),
                views_of(cameras), run_id)


def load_policy(export_dir: str, devices: list[str]):
    """PRD 7.2: first device that loads the export wins (GPU, then CPU)."""
    from policies.episode import load

    errors = []
    for device in devices:
        try:
            return load(export_dir, device)
        except Exception as exc:  # the runtime raises several types; any of them means "try the next device"
            errors.append(f"{device}: {exc}")
    raise RuntimeError(f"no device could load {export_dir}: {errors}")


def build_real(scripted: set[str], bricks: int, run_id: str) -> Cell:
    """Real station. Checks every config value first, so a missing one fails before anything moves."""
    from common.capture import OpenCVCamera
    from fallback.scripted import ScriptedMover, load_waypoints
    from robot import io

    cameras, robot, models = load_config("cameras.yaml"), load_config("robot.yaml"), load_config("models.yaml")
    unset = [role for role, cam in cameras.items() if cam["path"] is None]
    if unset:
        sys.exit(f"config/cameras.yaml: set the path for {', '.join(unset)} (ls /dev/v4l/by-id/)")
    if robot["port"] is None:
        sys.exit("config/robot.yaml: set the follower's port")
    learned = {"pick", "place"} - scripted
    needed = {"pick": "act", "place": "smolvla"}
    untrained = [needed[part] for part in sorted(learned) if models["policies"][needed[part]] is None]
    if untrained:
        sys.exit(f"config/models.yaml: no export for {', '.join(untrained)}; "
                 f"set it, or run with --scripted {','.join(sorted(scripted | learned))}")
    poses = load_waypoints(CONFIG / "waypoints.yaml")

    from perception.inspector import Inspector as AnomalibInspector  # slow import: OpenVINO compile

    insp = models["inspector"]
    inspector = AnomalibInspector(Path(insp["xml"]), Path(insp["thresholds"]), insp["model"])
    io.connect(port=robot["port"], calibration=robot["calibration"])
    capture = SharedCapture({role: OpenCVCamera(cam["path"]) for role, cam in cameras.items()}).start()

    movers = {}
    if scripted:
        scripted_mover = ScriptedMover(poses)
        movers |= {part: scripted_mover for part in scripted}
    if learned:
        from policies.mover import LearnedMover

        pol = models["policies"]
        policy = {part: load_policy(pol[needed[part]], pol["devices"]) for part in learned}
        learned_mover = LearnedMover(policy.get("pick"), policy.get("place"), poses,
                                     lambda: {role: capture.frame(role) for role in pol["cameras"]})
        movers |= {part: learned_mover for part in learned}
    cell = Cell(capture, inspector, movers["pick"], movers["place"], CountLocator(bricks), load_config("rules.yaml"),
                views_of(cameras), run_id)
    # Honesty guardrail: the screen and the log always say what moved the arm.
    cell.mode = "pick: {} | place: {}".format(*("scripted" if p in scripted else needed[p] for p in ("pick", "place")))
    _log.info(cell.mode)
    return cell


def headless(cell: Cell) -> BaseException | None:
    try:
        cell.run()
    except KeyboardInterrupt:
        # Ctrl+C is the terminal's stop button: treat it like E (torque off). This is the control thread.
        cell.picker.estop()
        _log.warning("Ctrl+C: e-stop, torque off")
        return estop.EStopped()
    except (Exception, estop.EStopped) as exc:
        return exc
    return None


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--mock", action="store_true", help="stand-in cameras, inspector and arm")
    ap.add_argument("--scripted", type=parse_scripted, default=set(), help="pick, place or pick,place use waypoints")
    ap.add_argument("--bricks", type=int, default=5, help="bricks in the zone (until F9 localization)")
    ap.add_argument("--headless", action="store_true", help="no window: start at once, Ctrl+C = e-stop")
    args = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s", datefmt="%H:%M:%S")

    run_id = time.strftime("%Y%m%d-%H%M%S-") + uuid.uuid4().hex[:4]
    cell = build_mock(args.bricks, run_id) if args.mock else build_real(args.scripted, args.bricks, run_id)
    telemetry.start(Path("runs/events.jsonl"))
    try:
        if args.headless:
            error = headless(cell)
        else:
            from ui import mission_control

            error = mission_control.run(cell)
        if error is not None:
            sys.exit(1)  # already logged, spoken and homed (or torqued off) by Cell.run
    finally:
        cell.capture.stop()
        telemetry.stop()
        if not args.mock:
            from robot import io

            io.disconnect()
        _log.info("run %s: %d bricks sorted", run_id, cell.sorted)


if __name__ == "__main__":
    main()
