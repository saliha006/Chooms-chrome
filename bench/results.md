# Benchmark

## INT8 quantisation of the real-brick PatchCore (2026-11-15 07:55)

NNCF post-training quantisation (`nncf.quantize`, MIXED preset, calibrated on the 24 good photos) of `runs/detector/ov/patchcore/model.xml`, compared with the deployed FP32 IR on the real photos (CPU):

| | FP32 (deployed) | INT8 |
|---|---|---|
| Model size | 114 MB | 29 MB |
| p50 CPU / GPU / NPU | 43.9 / 4.1 / 28.1 ms | 25.5 / 3.0 / 27.2 ms |
| Good photos score | 21.6–23.6 | 23.4–34.2 |
| Defective photos score | 66.0–76.9 | 60.0–69.6 |
| Gap between the two | 42.3 | 25.9 |
| Same verdict as FP32 at the FP32 thresholds | — | 8 of 20 sampled photos |

INT8 keeps good and defective apart (good photos are in-sample for both), but shifts scores by up to 9 points, so the FP32 thresholds don't carry over. Not deployed: it needs its own held-out threshold evaluation first (`perception.evaluate` on INT8 scores). The demo runs FP32.

## Real-brick detector (2026-11-15)

PatchCore (Anomalib 2.7.0) trained on **real Duplo bricks** seen by the wrist camera, crop [140, 80, 400]. Same laptop as below (Core Ultra X9 388H, OpenVINO 2026.4.1, on mains). Small sample: 2 good bricks (24 images) and 4 defective bricks with marker crosses (42 images), so treat the accuracy rows as a first result, not a rate.

### Accuracy, brick-level held-out (`runs/evaluate/patchcore/report.md`, `runs/evaluate/padim/report.md`)

| metric | PatchCore | PaDiM |
|---|---|---|
| AUROC (held-out defectives vs out-of-fold good) | 1.000 | 0.431 |
| False alarms (good scored defective) | 0/24 (at most 11.7% at 95%) | 1/24 (at most 18.3%) |
| Held-out defectives caught at t_high | 18/18 (81–100% at 95%) | 0/18 (0–19%) |
| Good bricks sent to a second look | 1/24 | 17/24 |
| t_low / t_high | 65.38 / 67.15 (`perception/thresholds.yaml`) | 155.09 / 209.60 |

Two defective bricks set t_high; the other two are only scored. PatchCore is the detector; PaDiM does not separate real bricks.

### Export

PatchCore's ONNX export fails in Anomalib (issue #3883), so the IR is converted straight from PyTorch with `perception/export_direct.py`. On real photos the OpenVINO scores equal Anomalib's to 2 decimals.

### Latency, energy and operators (`python -m bench.benchmark --exports runs/detector/ov --n 100 --idle-s 20`, 07:24, idle 2.1 W)

`patchcore` is the deployed IR `runs/detector/ov/patchcore/model.xml`; `patchcore_fp32` is the FP32 conversion beside it. n=100 warm runs, batch 1, random input.

| model | device | p50_ms | p95_ms | size_mb | compile_s | cached_compile_s | mj_per_inference | net_mj_per_inference | watts | max_c |
|---|---|---|---|---|---|---|---|---|---|---|
| patchcore | CPU | 36.48 | 39.60 | 114.48 | 0.13 | 0.05 | 1448.21 | 1372.09 | 39.73 | 70.00 |
| patchcore | GPU | 2.94 | 2.97 | 114.48 | 0.25 | 0.10 | 95.23 | 89.06 | 32.20 | 60.05 |
| patchcore | NPU | 28.94 | 29.44 | 114.48 | 0.02 | 0.02 | 266.08 | 205.68 | 9.20 | 95.05 |
| patchcore_fp32 | CPU | 36.23 | 40.08 | 114.48 | 0.11 | 0.05 | 1466.32 | 1389.45 | 39.84 | 78.05 |
| patchcore_fp32 | GPU | 2.93 | 3.09 | 114.48 | 0.63 | 0.10 | 99.28 | 93.09 | 33.50 | 72.05 |
| patchcore_fp32 | NPU | 28.92 | 29.37 | 114.48 | 9.16 | 0.02 | 289.99 | 229.72 | 10.05 | 96.05 |

| model | device | operators | runnable | not supported |
|---|---|---|---|---|
| patchcore | CPU / GPU / NPU | 378 | 378 | none |
| patchcore_fp32 | CPU / GPU / NPU | 374 | 374 | none |

Earlier tonight, 20 runs after warm-up on `patchcore/model.xml`: CPU p50 43.9 ms (compile 0.1 s), GPU 4.1 ms (compile 1.3 s), NPU 28.1 ms (compile 9.4 s). The 0.02 s NPU compile for `patchcore` above came after that first 9.4 s compile; the fp32 IR's first NPU compile took 9.16 s. `max_c` is the hottest zone on the laptop and carries heat from the run before (the NPU rows follow the CPU and GPU rows).

### Deployed path on the saved photos (`python -m bench.real_photos`, 07:37)

The deployed IR through `perception.inspector.Inspector` on CPU, every saved photo (already the 256x256 crop, so `crop=(0, 0, 256)`). The good photos trained the deployed model, so their scores are in-sample and far lower than the out-of-fold good scores in the report above; this checks the wiring, not accuracy.

| truth | n | min | median | max | perfect | uncertain | defective |
|---|---|---|---|---|---|---|---|
| good | 24 | 21.60 | 22.18 | 23.65 | 24 | 0 | 0 |
| defective | 42 | 65.97 | 70.00 | 76.86 | 0 | 2 | 40 |

The two uncertain photos are brick b03 (65.97 and 67.14, just under t_high 67.15). No defective photo scored perfect.

## Nemotron line check on real bricks (2026-11-15)

`python -m reasoner.evaluate cases.csv --timeout 8`, calm persona, live NVIDIA API (`nvidia/nemotron-3.5-super-vl-120b-a12b`), 07:38. 16 real photos picked from the run above: 7 perfect, 7 defective, 2 uncertain (the only two), spread over the bricks. Labels and scores come from the deployed detector; consistency is the robot's own checker (`reasoner.live.grounded`).

| | First run (07:37) | After the checker fix (07:39) |
|---|---|---|
| Lines consistent with the verdict | 12 of 16 (75%, 95% interval 48-93%) | 16 of 16 (100%, 95% interval 79-100%) |
| perfect / defective / uncertain | 3 of 7 / 7 of 7 / 2 of 2 | 7 of 7 / 7 of 7 / 2 of 2 |
| Requests that failed or timed out | 0 | 0 |
| Time to a line | p50 1939 ms, p95 4474 ms | p50 1980 ms, p95 2592 ms |

The four "contradictions" in the first run were all orange good bricks, and each line was right ("I see an orange brick ... score of 21.60 is well below the low threshold of 65.38 ... purple bowl"). The checker rejected any line containing "orange" for a perfect verdict, so it was flagging the brick's colour, not a wrong bowl. It now looks for "orange bowl" / "purple bowl". On the robot the same bug would have replaced every live line about a good orange brick with the template. The first run's p95 (4.5 s) is over the robot's 4 s wait; the second run's is 2.6 s. Small sample, one persona.

## Stand-in measurements (2026-11-14, synthetic bricks)

Everything below was measured on the **stand-in PaDiM model trained on synthetic bricks** and a random-weight ACT probe. The hardware rows are real; the model is not the real-brick detector.

2026-11-14 16:59 · devices CPU, GPU, NPU · n=100 warm runs, batch 1 · idle 2.1 W

**Stand-in model.** Intel laptop (Core Ultra X9 388H, Ubuntu 26.04, kernel 7.0.0-38, OpenVINO 2026.4.1, NPU driver 1.38.0), on mains power. The detector is PaDiM trained on **stand-in synthetic bricks**: latency, size, compile, operator and thermal rows are real measurements of this hardware; the final table is re-run on the real-brick model. An earlier run on battery (16:44) gave the same latencies within a few percent. `benchmark_app -hint latency` cross-check on padim/int8, median: CPU 8.70 ms, GPU 0.92 ms, NPU 6.57 ms. Energy = package energy (RAPL) per inference; net = minus idle. `max_c` / max °C = the hottest thermal zone on the laptop, so it carries heat over from the run before.

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

### Operator support (stand-in PaDiM)

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

### Sustained load, stand-in PaDiM (2026-11-14 17:16 · `runs/standin/export/padim/int8/weights/openvino/model.xml` · 300 s per device)

| device | seconds | inferences | first p50 ms | last p50 ms | slowdown | watts | max °C |
|---|---|---|---|---|---|---|---|
| CPU | 300 | 26736 | 10.63 | 11.28 | 1.06× | 20.52 | 95.00 |
| GPU | 300 | 236154 | 1.00 | 1.43 | 1.43× | 20.13 | 66.00 |
| NPU | 300 | 43640 | 7.08 | 6.82 | 0.96× | 14.66 | 86.00 |

The sustained rows ran one after the other with 60 s pauses, so the NPU row's 86 °C is heat left over from the CPU run, not the NPU's own.

### ACT policy compile probe, random weights (2026-11-14 17:20, `bench/act_npu_probe.py`)

Studio's ACT with our inputs (6 joints; `top`, `inspect`, `wrist` cameras, resized to 384×384 by Studio's preprocessing), **random weights** (whether a graph compiles does not depend on the weights), exported with `policy.export(backend="openvino")` in 6.2 s, IR 133 MB (FP32). 30 runs after one warm-up:

| device | compile s | p50 ms per call |
|---|---|---|
| CPU | 0.7 | 65.7 |
| GPU | 3.4 | 4.2 |
| NPU | 2.3 | 8.9 |

ACT compiles and runs on the NPU. Trained-ACT numbers come with Nate's export (same shapes).
