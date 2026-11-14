# Benchmark

2026-11-14 16:44 · devices CPU, GPU, NPU · n=100 warm runs, batch 1 · idle 2.3 W

**Read this first.** Intel laptop (Core Ultra X9 388H, Ubuntu 26.04, kernel 7.0.0-38, OpenVINO 2026.4.1, NPU driver 1.38.0), **on battery**, and the model is PaDiM trained on **stand-in synthetic bricks**: the latency, size, compile and operator rows are real measurements of this hardware; the final table is re-run on the real-brick model with the charger in. `benchmark_app -hint latency` cross-check on padim/int8, median: CPU 8.70 ms, GPU 0.92 ms, NPU 6.57 ms. Energy is package energy (RAPL) per inference; net = minus idle.

| model | device | p50_ms | p95_ms | size_mb | compile_s | cached_compile_s | mj_per_inference | net_mj_per_inference | watts | max_c |
|---|---|---|---|---|---|---|---|---|---|---|
| padim (PyTorch) | CPU | 18.39 | 72.19 | 176.68 | n/a | n/a | 793.72 | 732.55 | 29.41 | 68.00 |
| padim/fp16 | CPU | 6.35 | 7.09 | 88.30 | 0.06 | 0.03 | 260.38 | 245.66 | 40.11 | 70.00 |
| padim/fp16 | GPU | 1.51 | 1.71 | 88.30 | 0.17 | 0.06 | 46.62 | 43.13 | 30.25 | 61.05 |
| padim/fp16 | NPU | 7.17 | 8.79 | 88.30 | 0.02 | 0.02 | 87.74 | 71.32 | 12.11 | 64.05 |
| padim/fp16 + in-graph preprocessing | CPU | 6.39 | 7.06 | 88.30 | 0.06 | 0.03 | 260.00 | 245.33 | 40.16 | 71.00 |
| padim/fp16 + in-graph preprocessing | GPU | 1.45 | 2.08 | 88.30 | 0.34 | 0.06 | 44.80 | 41.37 | 29.61 | 65.05 |
| padim/fp16 + in-graph preprocessing | NPU | 7.17 | 8.70 | 88.30 | 2.83 | 0.02 | 85.25 | 68.73 | 11.70 | 64.05 |
| padim/int8 | CPU | 9.56 | 12.35 | 47.04 | 0.11 | 0.04 | 256.00 | 233.93 | 26.30 | 78.00 |
| padim/int8 | GPU | 1.02 | 1.85 | 47.04 | 0.17 | 0.03 | 33.20 | 30.67 | 29.71 | 65.05 |
| padim/int8 | NPU | 7.19 | 9.73 | 47.04 | 0.02 | 0.05 | 80.92 | 64.18 | 10.96 | 65.05 |
| padim/int8 + in-graph preprocessing | CPU | 9.40 | 11.27 | 47.04 | 0.11 | 0.04 | 250.17 | 228.61 | 26.30 | 80.00 |
| padim/int8 + in-graph preprocessing | GPU | 1.01 | 1.80 | 47.04 | 0.60 | 0.03 | 33.23 | 30.66 | 29.24 | 66.05 |
| padim/int8 + in-graph preprocessing | NPU | 7.28 | 10.20 | 47.04 | 4.62 | 0.05 | 82.04 | 65.07 | 10.96 | 66.05 |

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
