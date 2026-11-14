"""Thermal headroom: one model run back to back on each device for minutes, to see whether it throttles (F12).

    python -m bench.sustained --xml runs/export/padim/int8/weights/openvino/model.xml --seconds 300

A device throttles when its latency late in the run is clearly above its latency at the start, so each row
compares the p50 of the first and last `--window-s` seconds. Appends a section to bench/results.md.
"""

import argparse
import time
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import openvino as ov

from bench.benchmark import compile_seconds, random_inputs
from bench.power import measure


@dataclass
class Sustained:
    device: str
    seconds: float
    inferences: int
    first_p50_ms: float
    last_p50_ms: float
    watts: float | None
    max_c: float | None

    @property
    def slowdown(self) -> float:
        return self.last_p50_ms / self.first_p50_ms


def window_p50s(stamps: np.ndarray, latencies_ms: np.ndarray, window_s: float) -> tuple[float, float]:
    """p50 latency of the inferences that finished in the first and in the last `window_s` seconds."""
    first = latencies_ms[stamps <= stamps[0] + window_s]
    last = latencies_ms[stamps >= stamps[-1] - window_s]
    return float(np.median(first)), float(np.median(last))


def run(xml: Path, device: str, seconds: float, window_s: float) -> Sustained:
    _, compiled = compile_seconds(xml, device, cache_dir=None)
    request = compiled.create_infer_request()
    inputs = random_inputs(compiled)
    request.infer(inputs)  # warm-up outside the measured run
    stamps, latencies = [], []
    with measure() as power:
        end = time.perf_counter() + seconds
        while (now := time.perf_counter()) < end:
            request.infer(inputs)
            done = time.perf_counter()
            stamps.append(done)
            latencies.append((done - now) * 1000)
    first, last = window_p50s(np.array(stamps), np.array(latencies), window_s)
    return Sustained(device, power.seconds, len(latencies), first, last, power.watts, power.max_c)


def to_markdown(rows: list[Sustained], label: str) -> str:
    def cell(v: float | None) -> str:
        return "n/a" if v is None else f"{v:.2f}"

    lines = [f"## Sustained load ({label})", "",
             "| device | seconds | inferences | first p50 ms | last p50 ms | slowdown | watts | max °C |",
             "|---|---|---|---|---|---|---|---|"]
    lines += [f"| {r.device} | {r.seconds:.0f} | {r.inferences} | {r.first_p50_ms:.2f} | {r.last_p50_ms:.2f} | "
              f"{r.slowdown:.2f}× | {cell(r.watts)} | {cell(r.max_c)} |" for r in rows]
    return "\n".join(lines)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--xml", type=Path, required=True)
    ap.add_argument("--seconds", type=float, default=300.0)
    ap.add_argument("--window-s", type=float, default=30.0)
    ap.add_argument("--cooldown-s", type=float, default=60.0, help="pause between devices so each starts cool")
    ap.add_argument("--out", type=Path, default=Path("bench/results.md"))
    args = ap.parse_args()
    devices = [d for d in ("CPU", "GPU", "NPU") if d in ov.Core().available_devices]
    rows = []
    for i, device in enumerate(devices):
        if i:
            time.sleep(args.cooldown_s)
        rows.append(run(args.xml, device, args.seconds, args.window_s))
        print(to_markdown(rows[-1:], device))
    section = to_markdown(rows, f"{time.strftime('%Y-%m-%d %H:%M')} · `{args.xml}` · {args.seconds:.0f} s per device")
    with args.out.open("a", encoding="utf-8") as f:
        f.write(f"\n{section}\n")
    print(section)


if __name__ == "__main__":
    main()
