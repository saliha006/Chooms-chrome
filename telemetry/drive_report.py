"""How reliable the box-room drive is, from the event log: one line per attempt, then the success rate.

    python -m telemetry.drive_report runs/events.jsonl            # every real drive logged so far
    python -m telemetry.drive_report runs/events.jsonl --run <id>  # one session of --drive-trials

Reads the `DRIVE` rows run.py writes (outcome "arrived" or a failure reason, latency, and a note with the distance
travelled and how far the board stopped from the dock). Mock runs are left out.
"""

import argparse
import json
import re
import statistics
from dataclasses import dataclass
from pathlib import Path

_TRAVELLED = re.compile(r"([\d.]+) cm travelled")
_OFFSET = re.compile(r"([\d.]+) cm ([\d.]+) deg from the dock")


@dataclass(frozen=True)
class Attempt:
    run_id: str
    arrived: bool
    outcome: str
    seconds: float | None
    travelled_cm: float | None
    off_cm: float | None
    off_deg: float | None


def attempts(events: Path, run_id: str | None = None) -> list[Attempt]:
    found = []
    for line in events.read_text(encoding="utf-8").splitlines():
        row = json.loads(line) if line.strip() else None
        mock = str(row.get("run_id", "")).startswith("mock-") if row else False
        if not row or row.get("state") != "DRIVE" or (mock and run_id is None):
            continue
        if run_id is not None and row.get("run_id") != run_id:
            continue
        note = row.get("note") or ""
        travelled, offset = _TRAVELLED.search(note), _OFFSET.search(note)
        found.append(Attempt(
            run_id=row["run_id"], arrived=row.get("outcome") == "arrived", outcome=str(row.get("outcome")),
            seconds=None if row.get("latency_ms") is None else row["latency_ms"] / 1000,
            travelled_cm=float(travelled.group(1)) if travelled else None,
            off_cm=float(offset.group(1)) if offset else None, off_deg=float(offset.group(2)) if offset else None))
    return found


def _median(values: list[float | None]) -> float | None:
    values = [v for v in values if v is not None]
    return statistics.median(values) if values else None


def report(found: list[Attempt]) -> str:
    if not found:
        return "No drive attempts logged."
    n, k = len(found), sum(a.arrived for a in found)
    from perception.stats import interval

    low, high = interval(k, n)
    lines = [f"Drive arrived {k} of {n} ({100 * k / n:.0f}%, 95% interval {100 * low:.0f}-{100 * high:.0f}%)"]
    arrived = [a for a in found if a.arrived]
    for label, value, unit in (("time", _median([a.seconds for a in arrived]), "s"),
                               ("distance", _median([a.travelled_cm for a in arrived]), "cm"),
                               ("stop from the dock", _median([a.off_cm for a in arrived]), "cm"),
                               ("angle from the dock", _median([a.off_deg for a in arrived]), "deg")):
        if value is not None:
            lines.append(f"  median {label}: {value:.1f} {unit}")
    failures = [a.outcome for a in found if not a.arrived]
    if failures:
        counts = {reason: failures.count(reason) for reason in sorted(set(failures))}
        lines.append("  failed: " + ", ".join(f"{reason} x{count}" for reason, count in counts.items()))
    return "\n".join(lines)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("events", type=Path, nargs="?", default=Path("runs/events.jsonl"))
    ap.add_argument("--run", help="one run id (a --drive-trials session)")
    args = ap.parse_args()
    print(report(attempts(args.events, args.run)))


if __name__ == "__main__":
    main()
