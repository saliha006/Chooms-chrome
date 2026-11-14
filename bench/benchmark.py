"""Latency, size, compile time and energy for every exported model on every device.

    python -m bench.benchmark --exports runs/export --n 100
Writes bench/results.md. Run it in the GPU slot (PRD §10) so nothing else loads the laptop.
"""

import argparse
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import openvino as ov

from bench.power import measure

WARMUP = 10
COLUMNS = ("model", "precision", "device", "p50_ms", "p95_ms", "size_mb", "compile_s", "cached_compile_s", "mj_per_inference", "watts", "max_c")


@dataclass
class Row:
    model: str
    precision: str
    device: str
    p50_ms: float
    p95_ms: float
    size_mb: float
    compile_s: float
    cached_compile_s: float
    mj_per_inference: float | None
    watts: float | None
    max_c: float | None


def compile_seconds(xml: Path, device: str, cache_dir: str | None) -> tuple[float, ov.CompiledModel]:
    core = ov.Core()
    if cache_dir:
        core.set_property({"CACHE_DIR": cache_dir})
    start = time.perf_counter()
    compiled = core.compile_model(core.read_model(xml), device)
    return time.perf_counter() - start, compiled


def bench_one(xml: Path, device: str, n: int) -> Row:
    with tempfile.TemporaryDirectory() as cache:
        compile_s, _ = compile_seconds(xml, device, None)
        compile_seconds(xml, device, cache)  # fills the cache
        cached_s, compiled = compile_seconds(xml, device, cache)
    x = np.random.default_rng(0).random(tuple(compiled.input(0).shape), dtype=np.float32)
    for _ in range(WARMUP):
        compiled(x)
    times = []
    with measure() as power:
        for _ in range(n):
            start = time.perf_counter()
            compiled(x)
            times.append((time.perf_counter() - start) * 1000)
    precision = xml.parents[2].name  # <exports>/<model>/<precision>/weights/openvino/model.xml
    return Row(
        model=xml.parents[3].name,
        precision=precision,
        device=device,
        p50_ms=float(np.percentile(times, 50)),
        p95_ms=float(np.percentile(times, 95)),
        size_mb=xml.with_suffix(".bin").stat().st_size / 1e6,
        compile_s=compile_s,
        cached_compile_s=cached_s,
        mj_per_inference=power.joules * 1000 / n if power.joules is not None else None,
        watts=power.watts,
        max_c=power.max_c,
    )


def to_markdown(rows: list[Row]) -> str:
    def cell(v) -> str:
        if v is None:
            return "n/a"
        return f"{v:.2f}" if isinstance(v, float) else str(v)

    lines = ["| " + " | ".join(COLUMNS) + " |", "|" + "---|" * len(COLUMNS)]
    lines += ["| " + " | ".join(cell(getattr(r, c)) for c in COLUMNS) + " |" for r in rows]
    return "\n".join(lines)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--exports", type=Path, default=Path("runs/export"))
    ap.add_argument("--n", type=int, default=100)
    ap.add_argument("--out", type=Path, default=Path("bench/results.md"))
    args = ap.parse_args()
    devices = [d for d in ("CPU", "GPU", "NPU") if d in ov.Core().available_devices]
    rows, failures = [], []
    for xml in sorted(args.exports.glob("*/*/weights/openvino/model.xml")):
        for device in devices:
            try:
                rows.append(bench_one(xml, device, args.n))
            except RuntimeError as err:  # e.g. an op the NPU doesn't support; record it, keep going
                failures.append(f"- {xml.parents[3].name}/{xml.parents[2].name} on {device}: {str(err).splitlines()[0]}")
    host = f"{time.strftime('%Y-%m-%d %H:%M')} · devices {', '.join(devices)} · n={args.n} warm runs, batch 1"
    body = f"# Benchmark\n\n{host}\n\n{to_markdown(rows)}\n"
    if failures:
        body += "\n## Did not compile\n" + "\n".join(failures) + "\n"
    args.out.write_text(body, encoding="utf-8")
    print(body)


if __name__ == "__main__":
    main()
