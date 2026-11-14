"""SortSense cell: one brick at a time through the PRD 7.1 state machine.

    python run.py --mock                    # whole loop with stand-ins, no hardware
    python run.py --mock --headless         # same, no window (tests, SSH without a display)
    python run.py --scripted pick,place     # real station, scripted motion (the 15:30 gate)
    python run.py --scripted place          # ACT picks, scripted placement
    python run.py                           # ACT picks, SmolVLA places

IDLE → LOCATE → PICK → VERIFY_GRASP → INSPECT → DECIDE → [REINSPECT] → PLACE → LOG → next.
Any failure → HOME, the reason said aloud, then PAUSE_HUMAN: P carries on, Q stops (--headless: stops).
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
from common import deadline
from common.locate import CountLocator
from common.reasons import HelpNeeded, Reason

CONFIG = Path(__file__).parent / "config"
GRASP_ATTEMPTS = 2  # PRD §6: retry once, then ask for help
SETTLE_S = 0.3  # TUNE: let the held brick stop swinging before a frame is scored (decisions.md D22)
_log = logging.getLogger("run")


# TUNE on the arm. Motion stages only: the deadline stops the motion loop, so a stuck move ends as TIMEOUT.
DEADLINE_S = {"PICK": 20.0, "REINSPECT": 25.0, "PLACE": 15.0, "HOME": 15.0}


class Cell:
    """One brick at a time. Failures end in PAUSE_HUMAN (D22): home, say why, wait for P (carry on) or Q (stop)."""

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
        self.next_brick = 1
        self.mode = "mock"
        self.pause_on_help = True  # False without a window (--headless): nobody can press P, so stop instead
        self.help_reason: Reason | None = None
        self.last_signal: DefectSignal | None = None
        self.trace: list[str] = []  # this brick's reasoning, one line per step (H7 panel)
        self.stage_ms: dict[str, float] = {}
        self.paused = threading.Event()  # P, or PAUSE_HUMAN: hold at the next stage boundary
        self.quit = threading.Event()  # Q: finish this brick, then home and stop
        self.hold = threading.Event()  # something tall in the zone (depth / scene check): wait until it clears

    def run(self) -> None:
        try:
            while not self.quit.is_set():
                brick_id = self.next_brick
                with self._stage("LOCATE", brick_id) as row:
                    present = self.locator.next_brick()
                    row["outcome"] = "brick" if present else "empty"
                if not present:
                    break
                self.next_brick += 1
                self.trace = []  # a new list, not clear(): the window may be drawing the old one
                try:
                    self.sort_one(brick_id)
                    self.sorted += 1
                except Exception as exc:
                    self._ask_for_help(brick_id, exc)
            narrator.say("quit" if self.quit.is_set() else "empty", n=self.sorted)
            self._home()
            self.state = "DONE"
        except estop.EStopped:
            self.state = "E-STOP"
            narrator.say("estop")
            raise

    def sort_one(self, brick_id: int) -> None:
        self._pick(brick_id)
        signal = self._inspect(brick_id, "inspect", "first look", newer_than=self._settle())
        narrator.say(signal.label, score=signal.score, bbox=signal.bbox)

        with self._stage("DECIDE", brick_id, signal) as row:
            label = signal.label
            row["outcome"] = label
        if label == "uncertain":
            label = self._resolve_uncertain(brick_id)

        instruction = self.rules[label]
        self.trace.append(f"decision: {instruction}")
        with self._stage("PLACE", brick_id, note=instruction) as row:
            placed = self.placer.place(instruction)
            timed_out = deadline.expired()
            row["outcome"] = "placed" if placed else "failed"
        if not placed:
            raise HelpNeeded(Reason.TIMEOUT if timed_out else Reason.PLACE_FAILED, instruction)
        with self._stage("LOG", brick_id, signal, label=label) as row:
            row["outcome"] = "sorted"

    def _pick(self, brick_id: int) -> None:
        for attempt in range(1, GRASP_ATTEMPTS + 1):
            with self._stage("PICK", brick_id, note=f"attempt {attempt}") as row:
                presented = self.picker.pick_and_present()
                timed_out = deadline.expired()
                row["outcome"] = "presented" if presented else "failed"
            if timed_out:
                raise HelpNeeded(Reason.TIMEOUT, f"pick attempt {attempt}")  # stuck, not a miss: don't retry
            with self._stage("VERIFY_GRASP", brick_id) as row:
                held = presented and not self.picker.gripper_empty()
                row["outcome"] = "held" if held else "empty"
            if held:
                return
            if attempt < GRASP_ATTEMPTS:
                narrator.say("grasp_fail")
        raise HelpNeeded(Reason.GRASP_FAILED, f"{GRASP_ATTEMPTS} attempts")

    def _inspect(self, brick_id: int, role: str, step: str, newer_than: float = 0.0) -> DefectSignal:
        with self._stage("INSPECT", brick_id, note=role) as row:
            try:
                frame = self.capture.frame(role, newer_than=newer_than)
            except TimeoutError as exc:
                raise HelpNeeded(Reason.CAMERA, role) from exc
            try:
                signal = self.inspector.inspect(frame, self.views[role], brick_id)
            except Exception as exc:
                raise HelpNeeded(Reason.INSPECT_FAILED, str(exc)) from exc
            self.last_signal = signal
            self.trace.append(f"{step}: {signal.score:.2f} vs {signal.t_low:.2f} / {signal.t_high:.2f} -> {signal.label}")
            row.update(label=signal.label, score=signal.score, device=signal.device, outcome=signal.label)
        return signal

    def _resolve_uncertain(self, brick_id: int) -> str:
        """PRD §0 v2.5 / D7: look again (fresh frame, no motion) → each reinspect motion → the rules' fallback label.

        Every score uses a frame grabbed after the arm settled: re-scoring the frame we already judged
        uncertain would just repeat the verdict."""
        chain = self.rules["uncertain"]
        signal = self._inspect(brick_id, chain["second_view"], "look again", newer_than=self._settle())
        if signal.label != "uncertain":
            narrator.say(signal.label, score=signal.score, bbox=signal.bbox, after="looked again")
            return signal.label
        for angle in chain["reinspect_angles"]:
            with self._stage("REINSPECT", brick_id, note=f"angle {angle}") as row:
                back = self.picker.reinspect(angle)
                timed_out = deadline.expired()
                row["outcome"] = "back at inspection pose" if back else "failed"
            if not back:
                raise HelpNeeded(Reason.TIMEOUT if timed_out else Reason.BRICK_LOST, f"reinspect {angle}")
            step = f"after wrist roll {angle}" if angle else "after re-grasp"
            signal = self._inspect(brick_id, "inspect", step, newer_than=self._settle())
            if signal.label != "uncertain":
                narrator.say(signal.label, score=signal.score, bbox=signal.bbox, after=f"reinspect {angle}")
                return signal.label
        narrator.say("still_uncertain", label=chain["then"])
        self.trace.append(f"still unsure: {chain['then']}, flagged")
        return chain["then"]

    def _ask_for_help(self, brick_id: int, exc: Exception) -> None:
        """Home, say why, then wait for a person. Called inside the `except`, so a bare raise re-raises exc."""
        reason = exc.reason if isinstance(exc, HelpNeeded) else Reason.UNEXPECTED
        if reason is Reason.UNEXPECTED:
            _log.exception("brick %d: unexpected error", brick_id)
        self.help_reason = reason
        self.trace.append(f"needs help: {reason.value.replace('_', ' ')}")
        self._event("PAUSE_HUMAN", brick_id, outcome=reason.value, note=str(exc))
        narrator.say("help", reason=reason.value)
        self._home()
        if not self.pause_on_help:
            self.state = "STOPPED"
            raise
        self.state = "PAUSE_HUMAN"
        self.paused.set()
        self._checkpoint()  # returns on P (carry on with the next brick) or Q
        self.help_reason = None

    def _home(self) -> None:
        self.state = "HOME"
        with deadline.armed(DEADLINE_S["HOME"]):
            self.picker.home()

    @staticmethod
    def _settle() -> float:
        time.sleep(SETTLE_S)
        return time.monotonic()

    @contextmanager
    def _stage(self, state: str, brick_id: int, signal: DefectSignal | None = None, **extra):
        """Acts on E, P and hold, sets the visible state, arms the stage deadline, times the stage and
        writes one `events` row (PRD 7.3; a failure's reason code goes in `outcome`)."""
        self._checkpoint()
        self.state = state
        row = {}
        if signal is not None:
            row.update(label=signal.label, score=signal.score, device=signal.device)
        row.update(extra)
        start = time.perf_counter()
        try:
            with deadline.armed(DEADLINE_S.get(state)):
                yield row
        except estop.EStopped:
            row["outcome"] = "e-stop"
            raise
        except HelpNeeded as exc:
            row["outcome"] = exc.reason.value
            raise
        except Exception as exc:
            row["outcome"] = f"error: {exc}"
            raise
        finally:
            self.stage_ms[state] = round((time.perf_counter() - start) * 1000, 2)
            self._event(state, brick_id, latency_ms=self.stage_ms[state], **row)

    def _event(self, state: str, brick_id: int, latency_ms: float | None = None, **row) -> None:
        row = {"label": None, "score": None, "device": None, "outcome": None, "note": None} | row
        _log.info("brick %d %-12s %s", brick_id, state, row["outcome"])
        telemetry.log(run_id=self.run_id, brick_id=brick_id, ts=time.time(), state=state, stage=state.lower(),
                      latency_ms=latency_ms, **row)

    def _checkpoint(self) -> None:
        """Runs on the control thread, the only one that talks to the motors (decisions.md D21).
        E always wins; a hold outlasts Q (never move into an obstacle); Q ends a pause."""
        announced_hold = False
        while True:
            if estop.requested():
                self.picker.estop()
                raise estop.EStopped()
            if self.hold.is_set():
                if not announced_hold:
                    self.state = "HOLD"
                    narrator.trigger("obstacle")
                    announced_hold = True
            elif self.quit.is_set() or not self.paused.is_set():
                self.paused.clear()
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
    """PRD 7.2: first device that loads the export wins (GPU, then CPU). Returns (policy, device)."""
    from policies.episode import load

    errors = []
    for device in devices:
        try:
            return load(export_dir, device), device
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
        loaded = {part: load_policy(pol[needed[part]], pol["devices"]) for part in learned}
        policy = {part: model for part, (model, _) in loaded.items()}
        learned_mover = LearnedMover(policy.get("pick"), policy.get("place"), poses,
                                     lambda: {role: capture.frame(role) for role in pol["cameras"]})
        movers |= {part: learned_mover for part in learned}
    cell = Cell(capture, inspector, movers["pick"], movers["place"], CountLocator(bricks), load_config("rules.yaml"),
                views_of(cameras), run_id)
    # Honesty guardrail: the screen and the log always say what moved the arm.
    cell.mode = "pick: {} | place: {}".format(
        *("scripted" if p in scripted else f"{needed[p]} on {loaded[p][1]}" for p in ("pick", "place")))
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
    cell.pause_on_help = not args.headless
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
