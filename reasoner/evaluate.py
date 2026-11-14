"""Does Nemotron's line tell the truth about the verdict? The NVIDIA track's evaluation table (decisions.md D11).

    python -m reasoner.evaluate cases.csv --persona calm
    python -m reasoner.evaluate cases.csv --system revised.txt   # a prompt revision, measured on the same frames

cases.csv columns: image,label,score,t_low,t_high and optionally bbox as "x y w h". `python -m perception.evaluate`
writes one (runs/evaluate/cases.csv) from the real-brick run: every honestly scored image with its verdict. Each row is sent through the same
call and the same checker the robot uses (reasoner.client.explain, reasoner.live.grounded); a request that fails
counts as failed, never as consistent. Needs NVIDIA_API_KEY and NEMOTRON_MODEL; each row is one API request.
"""

import argparse
import csv
from collections import defaultdict
from pathlib import Path

import cv2
import numpy as np

from common.interfaces import DefectSignal
from perception.stats import interval
from reasoner.client import SYSTEM, explain
from reasoner.live import grounded


def load_cases(path: Path) -> list[dict]:
    rows = list(csv.DictReader(path.open(encoding="utf-8")))
    for row in rows:
        if row["label"] not in ("perfect", "defective", "uncertain"):
            raise ValueError(f"{path}: label must be perfect, defective or uncertain, got {row['label']!r}")
    return rows


def signal_for(row: dict) -> DefectSignal:
    bbox = tuple(int(v) for v in row["bbox"].split()) if row.get("bbox") else None
    return DefectSignal(0, "inspect", row["label"], float(row["score"]), float(row["t_low"]), float(row["t_high"]),
                        bbox, None, "recorded", "-", 0.0)


def evaluate(rows: list[dict], root: Path, persona: str = "calm", ask=explain, system: str = SYSTEM) -> dict:
    per_label = defaultdict(lambda: {"n": 0, "ok": 0})
    latency, failures, bad = [], 0, []
    for row in rows:
        crop = cv2.imread(str(root / row["image"]))
        if crop is None:
            raise FileNotFoundError(root / row["image"])
        signal = signal_for(row)
        per_label[signal.label]["n"] += 1
        try:
            line, ms = ask(crop, signal, persona, system=system)
        except Exception:
            failures += 1
            continue
        latency.append(ms)
        if grounded(line, signal):
            per_label[signal.label]["ok"] += 1
        else:
            bad.append((row["image"], line))
    n = sum(v["n"] for v in per_label.values())
    return {"n": n, "ok": sum(v["ok"] for v in per_label.values()), "failed": failures, "per_label": dict(per_label),
            "latency_ms": latency, "inconsistent": bad, "persona": persona}


def to_markdown(r: dict) -> str:
    if not r["n"]:
        return "No cases."
    low, high = interval(r["ok"], r["n"])
    lines = [f"# Nemotron line check ({r['persona']} persona)", "",
             "| | Result |", "|---|---|",
             f"| Lines consistent with the verdict | {r['ok']} of {r['n']} ({100 * r['ok'] / r['n']:.0f}%, 95% interval {100 * low:.0f}-{100 * high:.0f}%) |",
             f"| Requests that failed or timed out | {r['failed']} |"]
    for label, v in sorted(r["per_label"].items()):
        lines.append(f"| {label} bricks | {v['ok']} of {v['n']} consistent |")
    if r["latency_ms"]:
        t = np.asarray(r["latency_ms"])
        lines.append(f"| Time to a line | p50 {np.percentile(t, 50):.0f} ms, p95 {np.percentile(t, 95):.0f} ms |")
    for image, line in r["inconsistent"]:
        lines.append(f"| Contradicted the verdict: {image} | {line} |")
    return "\n".join(lines)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("cases", type=Path)
    ap.add_argument("--persona", default="calm", choices=["calm", "cowboy"])
    ap.add_argument("--images", type=Path, help="folder the image column is relative to (default: next to cases.csv)")
    ap.add_argument("--system", type=Path, help="a revised system prompt, to compare with the current one")
    args = ap.parse_args()
    system = args.system.read_text().strip() if args.system else SYSTEM
    print(to_markdown(evaluate(load_cases(args.cases), args.images or args.cases.parent, args.persona, system=system)))


if __name__ == "__main__":
    main()
