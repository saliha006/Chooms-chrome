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
from collections.abc import Callable
from contextlib import contextmanager
from pathlib import Path

import yaml

import narrator
import telemetry
from narrator import answers
from telemetry import sync as telemetry_sync
from common import estop
from common.capture import SharedCapture
from common.interfaces import DefectSignal, Inspector, Mover
from common import deadline
from common.locate import CountLocator
from common.reasons import HelpNeeded, Reason
from bench import power
from perception.reason_trace import ReasonTrace, region

CONFIG = Path(__file__).parent / "config"
GRASP_ATTEMPTS = 2  # PRD §6: retry once, then ask for help
SETTLE_S = 0.3  # TUNE: let the held brick stop swinging before a frame is scored (decisions.md D22)
_log = logging.getLogger("run")
MOCK_DRIVE_S = 3.0  # the stand-in base's drive, long enough to hear the opening line


# TUNE on the arm. Motion stages only: the deadline stops the motion loop, so a stuck move ends as TIMEOUT.
# DRIVE: 4-5 floor strokes of ~5.5 s each into the dock, plus settling (Nate, robot/drive.py).
DEADLINE_S = {"PICK": 20.0, "REINSPECT": 25.0, "PLACE": 15.0, "HOME": 15.0, "DRIVE": 60.0}


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
        self.tally = {"perfect": 0, "defective": 0, "rechecked": 0}  # for the spoken run summary
        self.decided: str | None = None  # the last brick's final label, for "Hey Pix, why that bowl?"
        self.look: Callable[[], object] | None = None  # narrator.vision: what the wrist camera shows now (a Sight)
        self.next_brick = 1
        self.mode = "mock"
        self.pause_on_help = True  # False without a window (--headless): nobody can press P, so stop instead
        self.help_reason: Reason | None = None
        self.last_signal: DefectSignal | None = None
        self.trace: list[str] = []  # this brick's reasoning, one line per step (H7 panel)
        self.steps: list[tuple[str, float]] = []  # recovery steps and the score after each (ReasonTrace)
        self.finale: Callable[[], object] | None = None  # the end-of-run dance on the real arm (D28)
        # (instruction, top_before, top_after) -> brick landed in that bowl; None = trust the mover (no bowls clicked)
        self.bowl_check: Callable[[str, object, object], bool] | None = None
        self.obstacle_seen = False
        self.drift_alert = False  # set by the Aiven sync thread (F15): lighting changed, rebaseline
        self.reasoner = None  # reasoner.live.LiveLine: Nemotron's explanation, spoken after the template line
        # The wheeled base (demo, Nate): drives to the table and returns centimetres travelled, or None if it
        # didn't get there. `approach_cm` is the planned distance, said before it moves. None = no base, no drive.
        self.approach: Callable[[], float | None] | None = None
        self.approach_cm: float | None = None
        self.dock_offset: Callable[[], tuple[float, float] | None] | None = None  # (cm, degrees) from the dock
        # narrator.naming.ObjectNamer around Saliha's naming model: says what an unfamiliar object is. None = off.
        self.namer = None
        self.stage_ms: dict[str, float] = {}
        self.paused = threading.Event()  # P, or PAUSE_HUMAN: hold at the next stage boundary
        self.quit = threading.Event()  # Q: finish this brick, then home and stop
        self.hold = threading.Event()  # something tall in the zone (depth / scene check): wait until it clears

    def run(self) -> None:
        """Measured as a whole (energy, power, peak temperature) so every logged trial carries its joules per brick."""
        with power.measure() as self.energy:
            self._run()
        self._report_energy()

    def _report_energy(self) -> None:
        e = self.energy
        if e.joules is None:  # no RAPL counter here (Windows, macOS) or it isn't readable
            return
        per_brick = f", {e.joules / self.sorted:.1f} J per brick" if self.sorted else ""
        note = f"{e.joules:.0f} J over {e.seconds:.0f} s, {e.watts:.1f} W average, peak {e.max_c} C{per_brick}"
        _log.info("energy: %s", note)
        self._event("ENERGY", 0, outcome=f"{self.sorted} bricks", note=note)

    def _run(self) -> None:
        try:
            if self.approach is not None:
                self._drive_to_table()
            while not self.quit.is_set():
                brick_id = self.next_brick
                with self._stage("LOCATE", brick_id) as row:
                    present = self.locator.next_brick()
                    row["outcome"] = "brick" if present else "empty"
                    self._notice_obstacles(row)
                if not present:
                    break
                self.next_brick += 1
                self.trace = []  # a new list, not clear(): the window may be drawing the old one
                self.steps = []
                try:
                    self.sort_one(brick_id)
                    self.sorted += 1
                    narrator.brick_done()
                except Exception as exc:
                    self._ask_for_help(brick_id, exc)
            narrator.say("quit" if self.quit.is_set() else "empty", n=self.sorted, **self.tally)
            if self.finale is not None and not self.quit.is_set():
                self.state = "DANCE"
                narrator.say("dance")
                self.finale()
            self._home()
            self.state = "DONE"
        except estop.EStopped:
            self.state = "E-STOP"
            narrator.say("estop")
            raise

    def facts(self) -> dict:
        """What Pix knows right now, for its spoken answers (narrator/answers.py). Read from the listener thread:
        each value is read once, so an answer may mix two moments a few ms apart, never a half-written value."""
        signal = self.last_signal
        sight = None
        if self.look is not None:
            try:
                sight = self.look()
            except Exception as exc:  # camera or model hiccup: answer from the other facts
                _log.info("couldn't look (%s)", type(exc).__name__)
        return {
            "sight": None if sight is None else {"name": sight.name, "guess": sight.guess},
            "state": self.state, "sorted": self.sorted, "tally": dict(self.tally), "decided": self.decided,
            "obstacles": len(getattr(self.locator, "obstacles", [])),
            "signal": None if signal is None else {"label": signal.label, "score": signal.score, "t_low": signal.t_low,
                                                   "t_high": signal.t_high, "where": region(signal.bbox)},
        }

    def _drive_to_table(self) -> None:
        """Before the first brick: the base drives the arm into reach, talked over live (the demo's opening)."""
        narrator.say("drive", cm=self.approach_cm)
        started = time.monotonic()
        try:
            with self._stage("DRIVE", 0) as row:
                travelled = self.approach()
                timed_out = deadline.expired()
                row["outcome"] = "arrived" if travelled is not None else "failed"
                row["note"] = self._drive_note(travelled)
            if travelled is None:
                raise HelpNeeded(Reason.TIMEOUT if timed_out else Reason.DRIVE_FAILED, "base")
        except Exception as exc:
            self._ask_for_help(0, exc)
            return
        narrator.say("arrived", cm=travelled, seconds=time.monotonic() - started)

    def _drive_note(self, travelled: float | None) -> str:
        """What the drive report reads back (telemetry/drive_report.py): planned, travelled, and where it stopped."""
        parts = [] if self.approach_cm is None else [f"{self.approach_cm:.0f} cm planned"]
        if travelled is not None:
            parts.append(f"{travelled:.1f} cm travelled")
        if self.dock_offset is not None:
            try:
                offset = self.dock_offset()
            except Exception as exc:  # the overhead frame or the marker: the drive result still counts
                _log.info("couldn't measure the dock offset (%s)", type(exc).__name__)
                offset = None
            if offset is not None:
                parts.append(f"{offset[0]:.1f} cm {offset[1]:.0f} deg from the dock")
        return "; ".join(parts)

    def drive_trials(self, n: int, ready: Callable[[str], str] = input) -> int:
        """Only the drive, n times, the board put back at the start by hand in between. Returns attempts made."""
        self.pause_on_help = False  # a failed attempt is logged and the next one starts
        for attempt in range(1, n + 1):
            if ready(f"Drive {attempt} of {n}: board at the start? Enter to drive, q to stop: ").strip().lower() == "q":
                return attempt - 1
            try:
                self._drive_to_table()
            except HelpNeeded as exc:
                _log.info("drive %d: %s", attempt, exc)
        return n

    def sort_one(self, brick_id: int) -> None:
        # Unprompted: why this brick. The scene check takes the most isolated brick (CountLocator chooses nothing).
        choice = {"chose": getattr(self.locator, "target", None) is not None,
                  "obstacles": len(getattr(self.locator, "obstacles", []))}
        if self.sorted:
            narrator.say("next", n=self.sorted, **self.tally, **choice)
        else:
            narrator.say("first", **choice)
        # The arm is home here (start, or after the last place), so the bowls are in clear view.
        bowls_before = self._top_frame() if self.bowl_check else None
        self._pick(brick_id)
        signal = self._inspect(brick_id, "inspect", "first look", newer_than=self._settle())
        narrator.say(signal.label, **spoken_numbers(signal))

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
        if self.bowl_check:
            self._verify_place(brick_id, instruction, bowls_before)
        final = self.last_signal  # the look that settled it, after any recovery
        with self._stage("LOG", brick_id, final, label=label) as row:
            row["outcome"] = "sorted"
            self.tally[label] += 1
            self.decided = label
            self.tally["rechecked"] += bool(self.steps)  # any look beyond the first
            row["note"] = ReasonTrace.from_signal(final, label, self.steps).note()

    def _verify_place(self, brick_id: int, instruction: str, before) -> None:
        """Home first: right after a place the arm hides the bowl from the top camera (Harry, 2026-11-14)."""
        self._home()
        with self._stage("VERIFY_PLACE", brick_id, note=instruction) as row:
            landed = self.bowl_check(instruction, before, self._top_frame())
            row["outcome"] = "in bowl" if landed else "not in bowl"
        if not landed:
            raise HelpNeeded(Reason.PLACE_FAILED, f"bowl unchanged: {instruction}")

    def _top_frame(self):
        try:
            return self.capture.frame("top", newer_than=self._settle())
        except TimeoutError as exc:
            raise HelpNeeded(Reason.CAMERA, "top") from exc

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
                narrator.say("grip", n=self.sorted)
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
            if self.reasoner is not None:
                self.reasoner.submit(frame, signal, persona=narrator.current_persona())
            where = region(signal.bbox)
            self.trace.append(f"{step}: {signal.score:.1f} vs {signal.t_low:.1f} / {signal.t_high:.1f} -> {signal.label}"
                              + (f" at {where}" if where else ""))
            if step != "first look":
                self.steps.append((step, signal.score))
            row.update(label=signal.label, score=signal.score, device=signal.device, outcome=signal.label)
        return signal

    def _resolve_uncertain(self, brick_id: int) -> str:
        """PRD §0 v2.5 / D7: look again (fresh frame, no motion) → each reinspect motion → the rules' fallback label.

        Every score uses a frame grabbed after the arm settled: re-scoring the frame we already judged
        uncertain would just repeat the verdict."""
        chain = self.rules["uncertain"]
        signal = self._inspect(brick_id, chain["second_view"], "look again", newer_than=self._settle())
        if signal.label != "uncertain":
            narrator.say(signal.label, **spoken_numbers(signal), after="looked again")
            return signal.label
        for angle in chain["reinspect_angles"]:
            narrator.say("roll" if angle else "regrasp", score=signal.score)
            with self._stage("REINSPECT", brick_id, note=f"angle {angle}") as row:
                back = self.picker.reinspect(angle)
                timed_out = deadline.expired()
                row["outcome"] = "back at inspection pose" if back else "failed"
            if not back:
                raise HelpNeeded(Reason.TIMEOUT if timed_out else Reason.BRICK_LOST, f"reinspect {angle}")
            step = f"after wrist roll {angle}" if angle else "after re-grasp"
            signal = self._inspect(brick_id, "inspect", step, newer_than=self._settle())
            if signal.label != "uncertain":
                narrator.say(signal.label, **spoken_numbers(signal), after=f"reinspect {angle}")
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

    def _notice_obstacles(self, row: dict) -> None:
        """Something in the zone that isn't a brick: never picked (SceneLocator skips it), but the cowboy notices once."""
        obstacles = getattr(self.locator, "obstacles", [])
        if obstacles:
            row["note"] = f"{len(obstacles)} non-brick object(s) in the zone, skipped"
            if not self.obstacle_seen:
                narrator.trigger("obstacle")
                if self.namer is not None:
                    box = getattr(obstacles[0], "box_px", None)  # Saliha's pixel box, once Blob has one
                    self.namer.submit(lambda: self.capture.frame("top"), box)
        elif not self.hold.is_set():
            narrator.clear("obstacle")
        self.obstacle_seen = bool(obstacles)

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


def spoken_numbers(signal: DefectSignal) -> dict:
    """What the live voice needs to explain a verdict (narrator/live.py)."""
    return {"score": signal.score, "t_low": signal.t_low, "t_high": signal.t_high, "where": region(signal.bbox)}


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


def build_real(scripted: set[str], bricks: int, run_id: str, base: bool = False) -> Cell:
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
    capture = SharedCapture({role: OpenCVCamera(cam["path"], cam.get("fourcc")) for role, cam in cameras.items()}).start()

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
    scene = load_config("scene.yaml")
    if scene["zone"] is not None:
        from perception.scene import SceneLocator, Zone

        locator = SceneLocator(capture, Zone(scene["zone"]))
    else:
        _log.warning("config/scene.yaml has no zone (python -m ui.click_regions): counting %d bricks instead", bricks)
        locator = CountLocator(bricks)
    cell = Cell(capture, inspector, movers["pick"], movers["place"], locator, load_config("rules.yaml"),
                views_of(cameras), run_id)
    from robot.dance import dance

    cell.finale = lambda: dance(poses["home"])
    if base:
        use_base(cell, capture)
    cell.look = vision_look(capture)
    cell.bowl_check = bowl_checker(scene)
    # Honesty guardrail: the screen and the log always say what moved the arm.
    cell.mode = "pick: {} | place: {}".format(
        *("scripted" if p in scripted else f"{needed[p]} on {loaded[p][1]}" for p in ("pick", "place")))
    _log.info(cell.mode)
    return cell


def vision_look(capture) -> Callable[[], object] | None:
    """Pix's eyes for "what do you see?": the wrist camera through narrator.vision. None until it has been built."""
    from narrator import vision

    if not (vision.MODEL_DIR / "clip_image.xml").exists():
        _log.info("narrator.vision not built (python -m narrator.vision build): Pix answers from the cell's facts only")
        return None
    recognizer = vision.Recognizer()
    _log.info("Pix's eyes: CLIP on %s, %s", recognizer.device, "trained classifier" if recognizer.probe else "zero-shot")
    return lambda: recognizer.recognise(capture.frame("wrist"))


def use_base(cell: Cell, capture) -> None:
    """The box-room opening (D35): the arm strokes its wheeled board into the dock before the first brick.
    Both the dock and the four stroke poses are checked here, so a missing one stops the run before anything moves."""
    from robot import drive

    try:
        dock, stroke = drive.load_dock(CONFIG / "dock.yaml"), drive.load_stroke(CONFIG / "waypoints.yaml")
    except ValueError as exc:
        sys.exit(f"--base: {exc}")
    cell.approach = lambda: drive.approach(lambda: capture.frame("top"), dock, stroke)
    cell.approach_cm = drive.PLANNED_CM

    def offset() -> tuple[float, float] | None:
        tag = drive.find_tag(capture.frame("top"))
        return None if tag is None else (tag.cm_to(dock), tag.degrees_to(dock))

    cell.dock_offset = offset


def bowl_checker(scene: dict) -> Callable[[str, object, object], bool] | None:
    """Place verification from the clicked bowl regions (perception.scene.brick_in_bowl, decisions.md D22)."""
    missing = [name for name in ("bowl_red", "bowl_blue") if scene.get(name) is None]
    if missing:
        _log.warning("config/scene.yaml has no %s (python -m ui.click_regions): places are not verified", ", ".join(missing))
        return None
    import numpy as np

    from fallback.scripted import bowl_for
    from perception.scene import Zone, brick_in_bowl

    bowls = {name: Zone(np.asarray(scene[name], float)) for name in ("bowl_red", "bowl_blue")}

    def check(instruction: str, before, after) -> bool:
        return brick_in_bowl(before, after, bowls[bowl_for(instruction)].mask(after.shape))

    return check


def nemotron_line():
    """Real runs only: a stand-in frame gives Nemotron nothing true to say. None without the NVIDIA settings."""
    import os

    from dotenv import load_dotenv

    load_dotenv()
    if not (os.environ.get("NVIDIA_API_KEY") and os.environ.get("NEMOTRON_MODEL")):
        _log.info("NVIDIA_API_KEY / NEMOTRON_MODEL not set: template lines only")
        return None
    from reasoner.live import LiveLine

    return LiveLine(narrator.say)


def drift_alarm(cell: Cell, run_id: str) -> telemetry_sync.DriftWatch | None:
    """Spoken and on screen only: the database never stops the arm (Harry, 2026-11-14)."""
    if run_id.startswith("mock-"):
        return None  # stand-in scores say nothing about the lighting

    def alert(_drift) -> None:
        cell.drift_alert = True
        narrator.say("drift")

    return telemetry_sync.drift_watch(run_id, Path(load_config("models.yaml")["inspector"]["thresholds"]), alert)


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
    ap.add_argument("--bricks", type=int, default=5, help="bricks in the zone when no zone is clicked (mock, or no scene.yaml)")
    ap.add_argument("--headless", action="store_true", help="no window: start at once, Ctrl+C = e-stop")
    ap.add_argument("--aiven", action="store_true", help="also send a mock run to Aiven (real runs always do)")
    ap.add_argument("--no-live", action="store_true", help="cached voice lines only: no ElevenLabs calls during the run")
    ap.add_argument("--no-listen", action="store_true", help="don't listen to the microphone (the H key still toggles the hat)")
    ap.add_argument("--drive", type=float, metavar="CM", help="--mock only: a stand-in base drives CM to the table first (rehearse the voice-over)")
    ap.add_argument("--base", action="store_true", help="real runs: the arm drives its wheeled board into the dock first (needs config/dock.yaml and the drive stroke)")
    ap.add_argument("--drive-trials", type=int, metavar="N", help="only the drive, N times (board back at the start by hand in between), then its success report")
    args = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s", datefmt="%H:%M:%S")

    # Mock runs get their own log and a mock- run id, so stand-in data never mixes into the trial report.
    run_id = ("mock-" if args.mock else "") + time.strftime("%Y%m%d-%H%M%S-") + uuid.uuid4().hex[:4]
    if args.base and args.mock:
        ap.error("--base drives the real board; rehearse the voice-over with --mock --drive CM")
    cell = build_mock(args.bricks, run_id) if args.mock else build_real(args.scripted, args.bricks, run_id, args.base)
    cell.pause_on_help = not args.headless
    if args.drive and args.mock:
        cell.approach_cm = args.drive
        cell.approach = lambda: time.sleep(MOCK_DRIVE_S) or args.drive
    if not args.no_live:
        narrator.enable_live(load_config("voices.yaml"))
        cell.reasoner = None if args.mock else nemotron_line()
    if not args.no_listen:
        narrator.start_listening(load_config("voices.yaml"), answer=lambda meaning: answers.answer(meaning, cell.facts()))
    events = Path("runs/mock-events.jsonl" if args.mock else "runs/events.jsonl")
    telemetry.start(events)
    sync_stop = threading.Event()
    # None when Aiven isn't configured: the JSONL file alone
    sync = telemetry_sync.start(sync_stop, events, drift_alarm(cell, run_id)) if args.aiven or not args.mock else None
    try:
        if args.drive_trials:
            if cell.approach is None:
                ap.error("--drive-trials needs the drive: --base on the station, or --mock --drive CM to rehearse")
            cell.drive_trials(args.drive_trials)
            telemetry.stop()  # flush, so the report sees the last attempt
            from telemetry import drive_report

            print(drive_report.report(drive_report.attempts(events, run_id)))
            return
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
        narrator.wait_idle()  # let the last line ("all done") finish before the program exits
        sync_stop.set()
        if sync is not None:
            sync.join(timeout=30)  # its last pass sends the run's final rows
        if not args.mock:
            from robot import io

            io.disconnect()
        _log.info("run %s: %d bricks sorted", run_id, cell.sorted)


if __name__ == "__main__":
    main()
