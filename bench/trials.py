"""The n = 20 reliability numbers from the event log, with exact 95% intervals (PRD §3, docs/trials-slide.md).

    python -m bench.trials runs/events.jsonl --truth truth.csv
`truth.csv` lists what each brick really is, written by the person placing the bricks: columns
run_id,brick_id,truth with truth = perfect or defective; run_id may be * for every run. Without it the report
still gives sorted-without-help and cycle time, but not the correct-bowl rate. Mock runs (run_id starts with
mock-) are ignored. Reads the JSONL file the control loop writes, so it works offline, without Aiven.
"""

import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path

import numpy as np

from perception.stats import interval

BOWL = {"perfect": "purple", "defective": "orange"}


def load_events(path: Path) -> list[dict]:
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    return [r for r in rows if not str(r["run_id"]).startswith("mock-")]


def load_truth(path: Path) -> dict[tuple[str, int], str]:
    truth = {}
    for row in csv.DictReader(path.open(encoding="utf-8")):
        if row["truth"] not in BOWL:
            raise ValueError(f"{path}: truth must be perfect or defective, got {row['truth']!r}")
        truth[(row["run_id"], int(row["brick_id"]))] = row["truth"]
    return truth


def truth_for(truth: dict, run_id: str, brick_id: int) -> str | None:
    return truth.get((run_id, brick_id)) or truth.get(("*", brick_id))


def summarise(events: list[dict], truth: dict | None = None) -> dict:
    every_row = defaultdict(list)
    for row in events:
        every_row[(row["run_id"], row["brick_id"])].append(row)
    # A LOCATE row alone is the loop looking at an empty zone, not a brick; it still starts a real brick's clock.
    bricks = {k: rows for k, rows in every_row.items() if any(r["state"] != "LOCATE" for r in rows)}
    sorted_ok, helped, correct, scored, confusion, seconds, looked = 0, 0, 0, 0, defaultdict(int), [], 0
    for (run_id, brick_id), rows in bricks.items():
        logged = next((r for r in rows if r["state"] == "LOG"), None)
        paused = any(r["state"] == "PAUSE_HUMAN" for r in rows)
        helped += paused
        if logged is None:
            continue
        sorted_ok += not paused
        seconds.append(max(r["ts"] for r in rows) - min(r["ts"] for r in rows))
        looked += "look again" in (logged.get("note") or "")
        real = truth_for(truth, run_id, brick_id) if truth else None
        if real is not None:
            scored += 1
            correct += logged["label"] == real
            confusion[(real, logged["label"])] += 1
    n = len(bricks)
    return {"bricks": n, "sorted_without_help": sorted_ok, "helped": helped, "second_look": looked, "scored": scored,
            "correct": correct, "confusion": dict(confusion), "cycle_s": seconds}


def rate(k: int, n: int) -> str:
    if n == 0:
        return "n/a (no bricks)"
    low, high = interval(k, n)
    return f"{k} of {n} ({100 * k / n:.0f}%, 95% interval {100 * low:.0f}-{100 * high:.0f}%)"


def to_markdown(s: dict) -> str:
    lines = ["| | Result |", "|---|---|", f"| Sorted without a human | {rate(s['sorted_without_help'], s['bricks'])} |",
             f"| Needed a person | {s['helped']} bricks |", f"| Needed a second look | {s['second_look']} bricks |"]
    if s["scored"]:
        lines.append(f"| Correct bowl (against what each brick really is) | {rate(s['correct'], s['scored'])} |")
        wrong = {k: v for k, v in s["confusion"].items() if k[0] != k[1]}
        lines.append("| Mistakes | " + (", ".join(f"{t} brick to the {BOWL.get(p, p)} bowl x{v}" for (t, p), v in sorted(wrong.items())) or "none") + " |")
    else:
        lines.append("| Correct bowl | not scored: no truth file for these bricks |")
    if s["cycle_s"]:
        times = np.asarray(s["cycle_s"])
        lines.append(f"| Cycle time per brick | p50 {np.percentile(times, 50):.1f} s, p95 {np.percentile(times, 95):.1f} s, {60 / times.mean():.1f} bricks per minute |")
    return "\n".join(lines)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("events", type=Path)
    ap.add_argument("--truth", type=Path)
    args = ap.parse_args()
    print(to_markdown(summarise(load_events(args.events), load_truth(args.truth) if args.truth else None)))


if __name__ == "__main__":
    main()
