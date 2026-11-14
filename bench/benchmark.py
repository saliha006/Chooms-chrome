"""Latency, size, compile time and energy for every exported model on every device.

    python -m bench.benchmark --exports runs/export --n 100 --idle-s 60 --torch-ckpt runs/evaluate/padim/.../model.ckpt
Finds every model.xml under --exports (Anomalib and physicalai layouts, any number of inputs), adds an optional
PyTorch CPU baseline row, and reports energy net of idle power. Writes bench/results.md. Run it in the GPU slot
(PRD §10) so nothing else loads the laptop.
"""

import argparse
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import openvino as ov

from bench.power import idle_watts, measure

WARMUP = 10
COLUMNS = ("model", "device", "p50_ms", "p95_ms", "size_mb", "compile_s", "cached_compile_s", "mj_per_inference", "net_mj_per_inference", "watts", "max_c")


@dataclass
class Row:
    model: str
    device: str
    p50_ms: float
    p95_ms: float
    size_mb: float
    compile_s: float | None
    cached_compile_s: float | None
    mj_per_inference: float | None
    net_mj_per_inference: float | None
    watts: float | None
    max_c: float | None


def compile_seconds(xml: Path, device: str, cache_dir: str | None) -> tuple[float, ov.CompiledModel]:
    core = ov.Core()
    if cache_dir:
        core.set_property({"CACHE_DIR": cache_dir})
    start = time.perf_counter()
    compiled = core.compile_model(core.read_model(xml), device)
    return time.perf_counter() - start, compiled


def label(xml: Path, exports: Path) -> str:
    """'padim/int8' for <exports>/padim/int8/weights/openvino/model.xml; the folder path for other layouts."""
    parts = xml.relative_to(exports).parent.parts
    return "/".join(parts[:-2] if parts[-2:] == ("weights", "openvino") else parts) or xml.stem


def random_inputs(compiled: ov.CompiledModel) -> dict[str, np.ndarray]:
    """One random tensor per model input: images and state for policies, the image for the detector."""
    rng = np.random.default_rng(0)
    inputs = {}
    for port in compiled.inputs:
        if not port.get_partial_shape().is_static:
            raise ValueError(f"input {port.get_any_name()} has a dynamic shape {port.get_partial_shape()}")
        shape = tuple(port.shape)
        dtype = port.get_element_type().to_dtype()
        inputs[port.get_any_name()] = rng.random(shape, dtype=np.float32).astype(dtype) if np.issubdtype(dtype, np.floating) else np.zeros(shape, dtype)
    return inputs


def _net_mj(joules: float | None, seconds: float, n: int, idle_w: float | None) -> float | None:
    return None if joules is None or idle_w is None else (joules - idle_w * seconds) * 1000 / n


def bench_one(xml: Path, device: str, n: int, exports: Path, idle_w: float | None = None) -> Row:
    with tempfile.TemporaryDirectory() as cache:
        compile_s, _ = compile_seconds(xml, device, None)
        compile_seconds(xml, device, cache)  # fills the cache
        cached_s, compiled = compile_seconds(xml, device, cache)
    x = random_inputs(compiled)
    for _ in range(WARMUP):
        compiled(x)
    times = []
    with measure() as power:
        for _ in range(n):
            start = time.perf_counter()
            compiled(x)
            times.append((time.perf_counter() - start) * 1000)
    return Row(
        model=label(xml, exports),
        device=device,
        p50_ms=float(np.percentile(times, 50)),
        p95_ms=float(np.percentile(times, 95)),
        size_mb=xml.with_suffix(".bin").stat().st_size / 1e6,
        compile_s=compile_s,
        cached_compile_s=cached_s,
        mj_per_inference=power.joules * 1000 / n if power.joules is not None else None,
        net_mj_per_inference=_net_mj(power.joules, power.seconds, n, idle_w),
        watts=power.watts,
        max_c=power.max_c,
    )


def bench_torch(ckpt: Path, model_name: str, n: int, idle_w: float | None = None) -> Row:
    """The PyTorch CPU baseline for the Anomalib model, so the table shows what OpenVINO bought."""
    import torch

    from perception.train import MODELS

    model = MODELS[model_name].load_from_checkpoint(ckpt, map_location="cpu").eval()
    x = torch.rand(1, 3, 256, 256)
    times = []
    with torch.no_grad():
        for _ in range(WARMUP):
            model(x)
        with measure() as power:
            for _ in range(n):
                start = time.perf_counter()
                model(x)
                times.append((time.perf_counter() - start) * 1000)
    return Row(f"{model_name} (PyTorch)", "CPU", float(np.percentile(times, 50)), float(np.percentile(times, 95)),
               ckpt.stat().st_size / 1e6, None, None, power.joules * 1000 / n if power.joules is not None else None,
               _net_mj(power.joules, power.seconds, n, idle_w), power.watts, power.max_c)


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
    ap.add_argument("--idle-s", type=float, default=0.0, help="seconds of idle power to measure first (60 on the Intel laptop)")
    ap.add_argument("--torch-ckpt", type=Path, help="Anomalib checkpoint for the PyTorch CPU baseline row")
    ap.add_argument("--torch-model", default="padim")
    args = ap.parse_args()
    devices = [d for d in ("CPU", "GPU", "NPU") if d in ov.Core().available_devices]
    idle_w = idle_watts(args.idle_s) if args.idle_s > 0 else None
    rows, failures = [], []
    if args.torch_ckpt:
        rows.append(bench_torch(args.torch_ckpt, args.torch_model, args.n, idle_w))
    for xml in sorted(args.exports.rglob("*.xml")):
        for device in devices:
            try:
                rows.append(bench_one(xml, device, args.n, args.exports, idle_w))
            except (RuntimeError, ValueError) as err:  # an op the NPU doesn't support, a dynamic shape: a result, keep going
                failures.append(f"- {label(xml, args.exports)} on {device}: {str(err).splitlines()[0]}")
    idle = f" · idle {idle_w:.1f} W" if idle_w is not None else ""
    host = f"{time.strftime('%Y-%m-%d %H:%M')} · devices {', '.join(devices)} · n={args.n} warm runs, batch 1{idle}"
    body = f"# Benchmark\n\n{host}\n\n{to_markdown(rows)}\n"
    if failures:
        body += "\n## Did not compile\n" + "\n".join(failures) + "\n"
    args.out.write_text(body, encoding="utf-8")
    print(body)


if __name__ == "__main__":
    main()
