"""Check a recorded LeRobot dataset before anything trains on it (decisions.md D32: data quality first).

    python -m train.audit <dataset folder> --kind pick --cameras top,inspect,wrist
    python -m train.audit <dataset folder> --kind place --tasks "<string 1>" "<string 2>"
Reads meta/info.json, meta/stats.json, meta/tasks.parquet and data/**/*.parquet (LeRobot v3.0), never the videos.
It flags and a person decides: the limits are TUNE until real episodes exist. Exit code 1 if anything fails,
so it can gate a Modal launch. Needs pandas and pyarrow (the robot environment has both).
"""

import argparse
import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd

from robot import io

LENGTH_SPREAD = 0.4  # TUNE: episode length more than this far from the median counts as odd
# Joint thresholds are in recorded normalized units, which on SO-101 arm joints are close to degrees (200 units
# span a ~180-260 degree calibrated range), so the degree-sized numbers carry over.
STILL_DEG = 0.5  # TUNE: a joint moving less than this per frame counts as standing still
HESITATION_S = 2.0  # TUNE: standing still this long in the middle of an episode is a hesitation
EDGE_S = 1.5  # the start and the end of an episode may stand still (the ~1 s hold at the inspection pose)
GAP_FACTOR = 1.5  # a frame gap this many times the frame period is a dropped frame
GAP_SHARE = 0.02  # TUNE: more dropped frames than this share of an episode is a fail
GLITCH_DEG = 15.0  # TUNE: a joint jumping this much in one frame is a teleop dropout, not motion
OVER_CAP_SHARE = 0.05  # TUNE: share of frames whose commanded step exceeds the runtime speed cap before it warns


@dataclass
class Report:
    episodes: int = 0
    fails: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.fails


def stack(column: pd.Series) -> np.ndarray:
    return np.stack(column.to_numpy()).astype(float)


def check_metadata(root: Path, report: Report, cameras: list[str], tasks: list[str] | None) -> int:
    info = json.loads((root / "meta" / "info.json").read_text())
    fps = int(info["fps"])
    if fps != io.CONTROL_HZ:
        report.fails.append(f"fps is {fps}, the runtime controls at {io.CONTROL_HZ} Hz")
    missing = [c for c in cameras if f"observation.images.{c}" not in info["features"]]
    if missing:
        report.fails.append(f"camera keys missing: {', '.join(missing)} (D29 wants top, inspect, wrist in both datasets)")
    stats_file = root / "meta" / "stats.json"
    stats = json.loads(stats_file.read_text()) if stats_file.exists() else {}
    if not all("q01" in stats.get(key, {}) and "q99" in stats.get(key, {}) for key in ("observation.state", "action")):
        report.warnings.append("no q01/q99 statistics: Studio will add about 40 s per episode before training (N7)")
    if tasks is not None:
        found = sorted(pd.read_parquet(root / "meta" / "tasks.parquet").index.astype(str))
        if found != sorted(tasks):
            report.fails.append(f"task strings differ from the agreed ones (D23): found {found}")
    return fps


def still_runs(state: np.ndarray, fps: int) -> float:
    """Longest stretch (seconds) in the middle of an episode where no joint moves more than STILL_DEG per frame."""
    edge = int(EDGE_S * fps)
    middle = state[edge:-edge] if len(state) > 2 * edge else state[:0]
    if len(middle) < 2:
        return 0.0
    still = (np.abs(np.diff(middle, axis=0)).max(axis=1) < STILL_DEG).astype(int)
    longest = run = 0
    for flag in still:
        run = run + 1 if flag else 0
        longest = max(longest, run)
    return longest / fps


def check_episode(index: int, frames: pd.DataFrame, fps: int, kind: str, report: Report) -> None:
    state, action = stack(frames["observation.state"]), stack(frames["action"])
    name = f"episode {index}"
    if not (np.isfinite(state).all() and np.isfinite(action).all()):
        report.fails.append(f"{name}: NaN or infinite values")
        return
    gaps = np.diff(frames["timestamp"].to_numpy(float))
    if len(gaps) and np.mean(gaps > GAP_FACTOR / fps) > GAP_SHARE:
        report.fails.append(f"{name}: {np.mean(gaps > GAP_FACTOR / fps):.0%} of frames arrived late (cadence)")
    if len(state) > 1 and np.abs(np.diff(state, axis=0)).max() > GLITCH_DEG:
        report.fails.append(f"{name}: a joint jumped more than {GLITCH_DEG:.0f} units (about degrees) in one frame (teleop dropout)")
    if len(action) > 1:
        over = np.mean(np.abs(np.diff(action, axis=0)).max(axis=1) > io.MAX_STEP_DEG)
        if over > OVER_CAP_SHARE:
            report.warnings.append(f"{name}: {over:.0%} of frames ask for more than the runtime speed cap (about {io.MAX_STEP_DEG:.0f} units, i.e. degrees), so replay would be slowed (move slower)")
    hesitation = still_runs(state, fps)
    if hesitation >= HESITATION_S:
        report.warnings.append(f"{name}: stood still for {hesitation:.1f} s in the middle (hesitation)")
    end_gripper = state[-1, io.GRIPPER]
    if kind == "pick" and not io.GRIPPER_EMPTY_BELOW <= end_gripper <= io.GRIPPER_HOLD_MAX:
        report.fails.append(f"{name}: ends with the gripper at {end_gripper:.0f}, outside the holding band {io.GRIPPER_EMPTY_BELOW:.0f}-{io.GRIPPER_HOLD_MAX:.0f} (no brick held)")
    if kind == "place" and end_gripper < io.GRIPPER_OPEN - io.POSE_TOLERANCE_DEG:
        report.fails.append(f"{name}: ends with the gripper at {end_gripper:.0f}, not open (brick not released)")


def audit(root: Path, kind: str = "any", cameras: list[str] | None = None, tasks: list[str] | None = None) -> Report:
    report = Report()
    fps = check_metadata(root, report, cameras or [], tasks)
    data = pd.concat([pd.read_parquet(p) for p in sorted((root / "data").rglob("*.parquet"))], ignore_index=True)
    arm = stack(data["observation.state"])[:, : io.GRIPPER]
    if np.abs(arm).max() > 100.0:
        report.warnings.append("an arm joint goes beyond -100..100: this looks like degrees, but D29 expects the normalized unit (compare with robot.io.observe())")
    lengths, seen = {}, {}
    for index, frames in data.groupby("episode_index"):
        frames = frames.sort_values("frame_index")
        lengths[index] = len(frames)
        check_episode(int(index), frames, fps, kind, report)
        digest = hashlib.sha1(stack(frames["observation.state"])[:30].tobytes()).hexdigest()
        if digest in seen:
            report.warnings.append(f"episode {index}: the first second is identical to episode {seen[digest]} (copied?)")
        seen.setdefault(digest, int(index))
    report.episodes = len(lengths)
    median = float(np.median(list(lengths.values())))
    report.warnings += [f"episode {i}: {n / fps:.1f} s against a median of {median / fps:.1f} s" for i, n in lengths.items() if abs(n - median) > LENGTH_SPREAD * median]
    if "task_index" in data and data["task_index"].nunique() > 1:
        per_task = data.groupby("task_index")["episode_index"].nunique()
        if per_task.max() - per_task.min() > 1:
            report.warnings.append(f"episodes per task are unbalanced: {per_task.to_dict()} (alternate the two strings)")
    return report


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("root", type=Path)
    ap.add_argument("--kind", choices=["pick", "place", "any"], default="any")
    ap.add_argument("--cameras", default="", help="comma list, e.g. top,inspect,wrist")
    ap.add_argument("--tasks", nargs="*", help="the exact task strings the dataset must contain")
    args = ap.parse_args()
    report = audit(args.root, args.kind, [c for c in args.cameras.split(",") if c], args.tasks)
    print(f"{report.episodes} episodes, {len(report.fails)} failures, {len(report.warnings)} warnings")
    for line in report.fails:
        print("FAIL", line)
    for line in report.warnings:
        print("warn", line)
    raise SystemExit(0 if report.ok else 1)


if __name__ == "__main__":
    main()
