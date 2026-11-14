# Benchmark

2026-11-14 16:59 · devices CPU, GPU, NPU · n=100 warm runs, batch 1 · idle 2.1 W

**Read this first.** Intel laptop (Core Ultra X9 388H, Ubuntu 26.04, kernel 7.0.0-38, OpenVINO 2026.4.1, NPU driver 1.38.0), on mains power. The detector is PaDiM trained on **stand-in synthetic bricks**: latency, size, compile, operator and thermal rows are real measurements of this hardware; the final table is re-run on the real-brick model. An earlier run on battery (16:44) gave the same latencies within a few percent. `benchmark_app -hint latency` cross-check on padim/int8, median: CPU 8.70 ms, GPU 0.92 ms, NPU 6.57 ms. Energy = package energy (RAPL) per inference; net = minus idle. `max_c` / max °C = the hottest thermal zone on the laptop, so it carries heat over from the run before.

| model | device | p50_ms | p95_ms | size_mb | compile_s | cached_compile_s | mj_per_inference | net_mj_per_inference | watts | max_c |
|---|---|---|---|---|---|---|---|---|---|---|
| padim (PyTorch) | CPU | 17.27 | 71.12 | 176.68 | n/a | n/a | 885.35 | 835.54 | 37.93 | 77.00 |
| padim/fp16 | CPU | 6.35 | 7.10 | 88.30 | 0.05 | 0.03 | 259.03 | 245.22 | 40.03 | 70.00 |
| padim/fp16 | GPU | 1.50 | 1.67 | 88.30 | 0.15 | 0.05 | 47.31 | 44.05 | 30.96 | 67.05 |
| padim/fp16 | NPU | 7.07 | 8.26 | 88.30 | 0.02 | 0.02 | 86.08 | 70.66 | 11.91 | 70.05 |
| padim/fp16 + in-graph preprocessing | CPU | 6.38 | 7.16 | 88.30 | 0.05 | 0.03 | 259.11 | 245.29 | 40.02 | 71.00 |
| padim/fp16 + in-graph preprocessing | GPU | 1.44 | 1.87 | 88.30 | 0.13 | 0.05 | 47.82 | 44.62 | 31.90 | 70.05 |
| padim/fp16 + in-graph preprocessing | NPU | 7.15 | 8.74 | 88.30 | 0.02 | 0.02 | 87.38 | 71.71 | 11.90 | 73.05 |
| padim/int8 | CPU | 8.91 | 11.37 | 47.04 | 0.10 | 0.04 | 319.62 | 300.05 | 34.86 | 92.00 |
| padim/int8 | GPU | 1.00 | 1.62 | 47.04 | 0.16 | 0.03 | 35.49 | 33.09 | 31.60 | 73.05 |
| padim/int8 | NPU | 7.17 | 10.54 | 47.04 | 0.02 | 0.02 | 83.51 | 67.64 | 11.23 | 77.05 |
| padim/int8 + in-graph preprocessing | CPU | 9.09 | 10.88 | 47.04 | 0.08 | 0.03 | 319.43 | 299.92 | 34.94 | 91.00 |
| padim/int8 + in-graph preprocessing | GPU | 0.95 | 1.78 | 47.04 | 0.15 | 0.03 | 33.73 | 31.44 | 31.36 | 79.05 |
| padim/int8 + in-graph preprocessing | NPU | 7.33 | 9.23 | 47.04 | 0.02 | 0.05 | 82.43 | 66.30 | 10.90 | 80.05 |

## Operator support

| model | device | operators | runnable | not supported (type x count) |
|---|---|---|---|---|
| padim/fp16 | CPU | 180 | 180 | none |
| padim/fp16 | GPU | 180 | 180 | none |
| padim/fp16 | NPU | 180 | 180 | none |
| padim/fp16 + in-graph preprocessing | CPU | 188 | 188 | none |
| padim/fp16 + in-graph preprocessing | GPU | 188 | 188 | none |
| padim/fp16 + in-graph preprocessing | NPU | 188 | 188 | none |
| padim/int8 | CPU | 348 | 348 | none |
| padim/int8 | GPU | 348 | 348 | none |
| padim/int8 | NPU | 348 | 348 | none |
| padim/int8 + in-graph preprocessing | CPU | 353 | 353 | none |
| padim/int8 + in-graph preprocessing | GPU | 353 | 353 | none |
| padim/int8 + in-graph preprocessing | NPU | 353 | 353 | none |

## Sustained load (2026-11-14 17:16 · `runs/standin/export/padim/int8/weights/openvino/model.xml` · 300 s per device)

| device | seconds | inferences | first p50 ms | last p50 ms | slowdown | watts | max °C |
|---|---|---|---|---|---|---|---|
| CPU | 300 | 26736 | 10.63 | 11.28 | 1.06× | 20.52 | 95.00 |
| GPU | 300 | 236154 | 1.00 | 1.43 | 1.43× | 20.13 | 66.00 |
| NPU | 300 | 43640 | 7.08 | 6.82 | 0.96× | 14.66 | 86.00 |

The sustained rows ran one after the other with 60 s pauses, so the NPU row's 86 °C is heat left over from the CPU run, not the NPU's own.

## ACT policy compile probe (2026-11-14 17:20, `bench/act_npu_probe.py`)

Studio's ACT with our inputs (6 joints; `top`, `inspect`, `wrist` cameras, resized to 384×384 by Studio's preprocessing), **random weights** (whether a graph compiles does not depend on the weights), exported with `policy.export(backend="openvino")` in 6.2 s, IR 133 MB (FP32). 30 runs after one warm-up:

| device | compile s | p50 ms per call |
|---|---|---|
| CPU | 0.7 | 65.7 |
| GPU | 3.4 | 4.2 |
| NPU | 2.3 | 8.9 |

ACT compiles and runs on the NPU. Trained-ACT numbers come with Nate's export (same shapes).
