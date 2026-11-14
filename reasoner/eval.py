"""Nemotron eval: how often the live line is usable, on saved inspection crops (F17, NVIDIA write-up).

    python -m reasoner.eval runs/nemotron_eval/frames.csv                       # current prompt
    python -m reasoner.eval runs/nemotron_eval/frames.csv --system revised.txt  # a prompt revision, same frames

frames.csv columns: image,label,score,t_low,t_high (label is the inspector's verdict for that crop).
A line is usable when it is grounded (no wrong bowl, no invented number: the same check the live path applies)
and says the decided action. Appends a table to bench/results.md, so before/after prompt rows sit together.
"""

import argparse
import csv
import statistics
import time
from dataclasses import dataclass
from pathlib import Path

import cv2
from dotenv import load_dotenv

from common.interfaces import DefectSignal
from reasoner.client import SYSTEM, explain
from reasoner.live import grounded

ACTION_WORDS = {"perfect": ("purple",), "defective": ("orange",), "uncertain": ("look", "again", "second", "check")}


@dataclass
class Outcome:
    signal: DefectSignal
    line: str | None
    latency_ms: float | None

    @property
    def grounded(self) -> bool:
        return self.line is not None and grounded(self.line, self.signal)

    @property
    def names_action(self) -> bool:
        return self.line is not None and any(w in self.line.lower() for w in ACTION_WORDS[self.signal.label])

    @property
    def usable(self) -> bool:
        return self.grounded and self.names_action


def load_frames(manifest: Path) -> list[tuple[Path, DefectSignal]]:
    frames = []
    with manifest.open(newline="") as f:
        for i, row in enumerate(csv.DictReader(f)):
            signal = DefectSignal(i, "webcam", row["label"], float(row["score"]), float(row["t_low"]),
                                  float(row["t_high"]), None, None, "eval", "n/a", 0.0)
            frames.append((manifest.parent / row["image"], signal))
    return frames


def evaluate(frames: list[tuple[Path, DefectSignal]], system: str = SYSTEM, ask=explain, pause_s: float = 1.6) -> list[Outcome]:
    """pause_s keeps one key under NVIDIA Build's free tier of about 40 requests a minute."""
    outcomes = []
    for image, signal in frames:
        crop = cv2.imread(str(image))
        if crop is None:
            raise FileNotFoundError(image)
        try:
            line, ms = ask(crop, signal, "calm", timeout_s=10.0, system=system)
        except Exception as exc:  # a failed call is a result for this table, not a crash
            print(f"{image.name}: failed ({exc})")
            line, ms = None, None
        outcomes.append(Outcome(signal, line, ms))
        print(f"{image.name} [{signal.label}] {ms and round(ms)} ms: {line}")
        time.sleep(pause_s)
    return outcomes


def to_markdown(outcomes: list[Outcome], prompt_name: str) -> str:
    def share(n: int) -> str:
        return f"{n}/{len(outcomes)}"

    latencies = sorted(o.latency_ms for o in outcomes if o.latency_ms is not None)
    p50 = f"{statistics.median(latencies):.0f}" if latencies else "n/a"
    p95 = f"{latencies[min(len(latencies) - 1, round(0.95 * (len(latencies) - 1)))]:.0f}" if latencies else "n/a"
    return "\n".join([
        f"## Nemotron eval ({time.strftime('%Y-%m-%d %H:%M')} · prompt: {prompt_name})", "",
        "| frames | answered | grounded | names the action | usable | p50 ms | p95 ms |",
        "|---|---|---|---|---|---|---|",
        f"| {len(outcomes)} | {share(sum(o.line is not None for o in outcomes))} | {share(sum(o.grounded for o in outcomes))} | "
        f"{share(sum(o.names_action for o in outcomes))} | {share(sum(o.usable for o in outcomes))} | {p50} | {p95} |",
    ])


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("manifest", type=Path)
    ap.add_argument("--system", type=Path, help="a revised system prompt to compare against the current one")
    ap.add_argument("--out", type=Path, default=Path("bench/results.md"))
    args = ap.parse_args()
    load_dotenv()
    system = args.system.read_text().strip() if args.system else SYSTEM
    outcomes = evaluate(load_frames(args.manifest), system)
    table = to_markdown(outcomes, args.system.name if args.system else "current")
    with args.out.open("a", encoding="utf-8") as f:
        f.write(f"\n{table}\n")
    print(table)


if __name__ == "__main__":
    main()
