# SortSense in numbers

Measured on the team's Intel Core Ultra laptop, 14–15 Nov 2026. Each line: the number, then where it comes from. Full tables in `bench/results.md`.

## Anomalib detection

- **AUROC 1.000** for PatchCore (Anomalib 2.7.0) on real Duplo bricks, wrist camera, brick-level held-out. `runs/evaluate/patchcore/report.md`
- **0/24 false alarms** on good bricks (at most 11.7% at 95% confidence). Same report
- **18/18 held-out defective bricks caught** (81–100% at 95%). Same report
- **AUROC 0.431 for PaDiM** on the same split, so PatchCore was chosen. `runs/evaluate/padim/report.md`
- Thresholds **t_low 65.38 / t_high 67.15**, with a second-look band in between. `perception/thresholds.yaml`
- Dataset: **2 good bricks (24 images), 4 defective bricks with marker crosses (42 images)**. A small sample, so read these as a first result

## OpenVINO and Core Ultra

- PatchCore **GPU p50 2.94 ms**, p95 2.97 ms, **89 mJ** net per inference. `bench/results.md`, n=100
- PatchCore **NPU p50 28.94 ms**, p95 29.44 ms, **206 mJ** net per inference at **9.2 W**, the lowest power of the three. Same
- PatchCore **CPU p50 36.48 ms**, p95 39.60 ms, 1372 mJ net per inference. Same
- **378/378 operators run on CPU, GPU and NPU**. Same, operator-support table
- First compile: NPU 9.4 s, GPU 1.3 s, CPU 0.1 s (20-run check tonight: GPU 4.1 ms, NPU 28.1 ms, CPU 43.9 ms). `bench/results.md`
- PatchCore's ONNX export fails in Anomalib (issue #3883); **converted straight from PyTorch** and OpenVINO scores match Anomalib's to 2 decimals on real photos. `perception/export_direct.py`
- 5-minute sustained run (stand-in model): **NPU 0.96×, CPU 1.06×, GPU 1.43×** slowdown. `bench/results.md`, stand-in section

## VLA and Studio

- ACT compile probe, random weights: **NPU 8.9 ms**, GPU 4.2 ms, CPU 65.7 ms per call. `bench/act_npu_probe.py`
- SmolVLA place dataset: **50 episodes, 25 per instruction**, public at huggingface.co/datasets/6salis/sortsense-place. Audit: **0 failures** after re-check (fast episodes noted)
- Drive dataset: **12 episodes** recorded
- Physical AI Studio: Intel's robotics developer site points to it for fine-tuning models ("Fine-tune your model in just a click with Physical AI Studio"). https://developer.robotics.intel.com/ (where https://docs.openedgeplatform.intel.com/dev/ai-suite-robotics.html redirects)

## Reliability

- Grip band: **empty 1.5, brick 17.4, half open 29.4, wide 96.3** (gripper reading, three runs)
- Wrist camera locked at **30 ms exposure, 31 fps**

## Voice and reasoning

- Nemotron live line: **1.7 s** (stand-in brick)
- ElevenLabs live voice warm-up: **739 ms**

## Not measured yet

- 20-trial pick-and-sort success rate: **TBD**
- Joules per brick, end to end: **TBD**
- SmolVLA gate: **TBD**
