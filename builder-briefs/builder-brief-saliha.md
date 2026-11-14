> **Status, 2026-11-14 04:30.** Block A fully done on `main` @ `99f1d09`, including the live Nemotron call (`nvidia/nemotron-3.5-super-vl-120b-a12b`, ~1.7–2.7 s per line, thinking off). Next: Saturday 08:00 on the Intel laptop. Branch renamed by discipline; `decisions.md` is the team's pitch record (agents update it as you build). PRD v2.3 (team vision: Intel task first, then the live reasoning voice and the cowboy switch). You now also own the Nemotron reasoner. Nothing built yet. Block A (stand-in pipeline) starts 00:45. Docs on `context`, board on `main`.

# Saliha: AI/ML (computer vision, edge-AI optimisation, LLM reasoning) + doc owner
**GitHub:** `saliha006` · **Branch:** `aiml-perception-saliha` (one branch for all your work) · **Tool:** Claude Code · **Brief last updated:** 2026-11-14 12:40 by saliha
**Spec:** `prd.md` (on `context`). A bare § means the PRD; CLAUDE.md and this brief's own sections are always named.

## 0. How the agent reads this brief (every task)
1. `CLAUDE.md` is already loaded (don't re-read it); read this brief once. Follow both.
2. Read `prd.md` sections 2, 4, 7 and 10 first. **Work `▶ Current tasks` top to bottom** (Block A, then Block B).
3. **Want a different route, more features or another decision in your area? Go ahead.** Your Claude always asks first: "Have you told the team? Who agreed?" (CLAUDE.md §2c). Changes to another builder's path or a shared contract wait for that owner's yes.
4. Before starting, read `progress.md`'s 📌 Open board (CLAUDE.md §2b). Rows To @saliha come first: tell the user, then resolve or schedule them.
5. Ship each task with the CLAUDE.md §7 sequence (code → `no-slop` → test → push → merge if safe), then log it (CLAUDE.md §2b). Use the `debug` skill on every issue.
6. Times are **Espoo local (EET, UTC+2)**, the event's clock (PRD §0).

**Task tags:** `[⚠ touches @name: what]` = changes someone else's area or a shared contract; get that owner's yes before merging (§2c). `[⏸ waits on @name: what]` = blocked until they deliver (a 📨 row on the Open board). `[🟠 your call]` = a design decision for the user (CLAUDE.md §1).

---

## 1. Ownership
You own **R2, R3, R7, R8 (devices), R9, R13 (uncertainty band), R19 (power and thermal), F1, F2, F3, F4 (decision logic) F12 and F17 (Nemotron reasoner, NVIDIA track) and R22**, and write the F15 drift rule and the F18 hat check: about 40 points (criteria 2 and 4), the two criteria we weight highest after the loop.

**Owns:**
- `perception/`: capture, train, calibrate, export, inspector, rebaseline, re-inspection (F4)
- `bench/`: benchmark harness, `bench/results.md`, `bench/plots/`
- `reasoner/`: Nemotron 3.5 Super VL client, prompts, eval set (F17), hat check (F18)
- PRD, CLAUDE.md, briefs, skills, `progress.md` upkeep (doc owner)

**Does NOT touch:**
| Area / path | Owner | Why it's theirs |
|---|---|---|
| `robot/`, `policies/`, `train/` | @nate | robot I/O, ACT/SmolVLA, Modal training |
| `run.py`, `common/` (incl. `interfaces.py`), `fallback/`, `ui/`, `narrator/`, `telemetry/`, `config/`, `README.md`, `docs/` | @harry | integration, contracts file, demo, side tracks |

Exception: the one import line in `run.py`, agreed in `progress.md` (Block B 13:00).
**Shared** (flag in `progress.md` ⚠️ Conflicts): `Makefile` (`rebaseline` target), `config/rules.yaml` semantics.

## 2. Contract & Guardrails
**Contract:** `Inspector.inspect(frame, view, brick_id) -> DefectSignal` (PRD 7.3).

**Guardrails:**
- ⛔ **Off-plan → CLAUDE.md §2c.**
- Tonight is scaffolding only; every reported number comes from real bricks and a held-out set.
- Static input shape 1×3×256×256, batch 1, for anything that targets the NPU.
- Never commit datasets, checkpoints or keys.

---

## 3. ▶ Current tasks (2026-11-14 07:10)
### 🆕 v2.5 research pass (2026-11-14 07:10): do these first, in order (same vision; PRD §0 v2.5, decisions.md D1, D7, D22–D26)
*Must exist by 15:30: real Inspector with measured thresholds; `scene.py` zone gate + bowl-region check for Harry's loop.*
| # | Status | Task | Hours | Done when |
|---|---|---|---|---|
| S1 | ✅ | **Evaluation harness + raw scores** (fixes bugs below): own brick-level splits (no Anomalib `Folder` val split), raw unclamped scores (check `Padim(post_processor=...)` accepts normalisation off in 2.7.0, 15 min; fallback: keep the clamp and say so), out-of-fold `t_low`, `t_high` from a dev split, bootstrap-by-brick AUROC interval, Clopper-Pearson false-alarm bound. Also check `from anomalib.models import AnomalyDino` imports. Built and tested tonight on synthetic data | 3.25 | Tests green on synthetic |
| S2 | ⬜ | 08:00 Intel laptop: install, NPU compile, check RAPL readable, `intel_vpu` sysfs (`npu_busy_time_us`), `uname -r`, `intel_gpu_top` | 1 | Notes in `progress.md` |
| S3 | ⬜ | 10:00–10:30 capture (robot 30 min): ~12 good bricks × 4 real grasps × 3 frames, 3 whole good bricks held out, ~12 defective bricks; ledger prepared beforehand (0.5 h) | 0.5 + slot | Data saved |
| S4 | ⬜ | 10:30–12:00 bake-off PaDiM vs PatchCore, thresholds, FP16/INT8 parity (INT8 only if ΔAUROC ≤ 0.01) | 3 | Model chosen with intervals |
| S5 | ✅ | `perception/scene.py`: colour blob, table homography from taped corners, most-isolated brick, `brick_in_bowl` (bowl-region change), "something tall is here" from depth. Parallel agent session; Harry's loop calls it (his yes) | 3 | Works on synthetic, then real frames |
| S6 | ✅ | `ReasonTrace` assembly (score, band, margin, region, chain steps, decision) for the panel and the log | 0.5 | Logged per brick |
| S7 | 🟡 | From 15:30: device table (`benchmark_app` + PyTorch baseline row; extend the bench glob to the `physicalai` IR layout) 2.5 h · efficiency protocol (idle baseline, 1 Hz power/thermal, NPU busy, J per brick net of idle; the 20 trials are the sustained run) 2 h · ACT-on-NPU compile probe 0.5 h · Intel-stack slide with the honest "not used" list 1 h | 6 | `bench/results.md` complete |
**Your bugs to fix (critic):** `perception/inspector.py`: `MAP_THRESHOLD` and clamped scores depend on Anomalib normalisation; the global `CACHE_DIR` replaces the NPU driver's cache (set it per compile); compile loop catches only `RuntimeError`. `train.py` + `calibrate.py`: the same defectives set `t_high` and are the test set. `bench/benchmark.py`: no PyTorch baseline, wrong glob for policy IRs; `bench/power.py`: temperature only at start and end.
**Add-ons (in order, each stop leaves the product working):** live Nemotron line, uncertain bricks only, 4 s timeout (1 h, with Harry) · ACT on NPU in the loop if the probe passes (1.5 h, with Nate) · rule-text compiler only if Challenge-Day rules differ (1.5 h) · AnomalyDINO only if PaDiM's lower interval < 0.90 (0.75 h) · spatial-lift check (0.5 h).
**Parallel sessions:** your load is ~16 h; run 2 agent sessions in separate git worktrees on disjoint files (S1 and S5 in parallel). Local notes for this: `saved for later + agents/multi-agent-workflow.md` (read when you say so).

🆕 **Vision (PRD v2.3 §1a):** (1) the Intel task done accurately, smoothly and in reasonable time, always first; (2) the robot explains its reasoning out loud, live, in a calm voice; (3) an obstacle or the cowboy hat flips it into a cowboy persona ("Holy smokes!") until the moment passes. Personality never slows the arm or costs a gate. No frontend, ever.
🆕 **What changed (PRD v2.2):** objects are **Duplo bricks with marker-drawn defects**; the Junction page scores **power, thermal headroom and latency** (20%), so the benchmark gains energy and temperature (A10, F12); Intel asks for **re-grasp on the anomaly score** (F4 chain below); if the good bricks come in **several colours**, PaDiM is the wrong default (10:30 row).
*Status: ⬜ not started · 🟡 in progress · ⏸ blocked · ✅ done*

### BLOCK A: tonight 00:45–02:30 (own laptop, no hardware)
Goal: the whole pipeline runs end-to-end on **stand-in images**, so on Saturday you only swap in real brick photos.
🆕 **Must by 02:30:** A1–A6 + A9 (≈ 1 h 45, the whole window). **If time:** A7, A8, A10, A11; anything left moves to Saturday 08:00–09:30 (installs leave room). Stand-in data = your webcam plus about 40 identical small objects (coins, bottle caps, Lego if you have any). Make "defects" with a marker scribble, a sticker, or a chipped or turned item. 🆕 Marker strokes match the real defects best (Intel: "markers to create your own defects"), so use mostly those, and use **two or three object colours** if you can, to test the multi-colour case tonight.

| # | Status | Task | Est. | Done when |
|---|---|---|---|---|
| A1 | ✅ | `python -m venv .venv && pip install "anomalib[openvino]==2.7.0"` (needs PyTorch ≥ 2.10) | 15 min | `import anomalib, openvino` works |
| A2 | ✅ | `perception/capture.py --out data/good --n 150 --cam <path>`: fixed square crop, saves PNGs. Reused on Saturday. | 15 min | Folders fill |
| A3 | ✅ | `perception/train.py`: Folder datamodule (`good/`, `defective/`, `val_good/`), PaDiM default, `--model patchcore\|efficientad` | 20 min | AUROC printed |
| A4 | ✅ | `perception/calibrate.py`: score histograms → `t_low` = 99th percentile of good, `t_high` = 5th percentile of defective → `perception/thresholds.yaml` plus `bench/plots/score_hist.png` and the confusion matrix | 15 min | yaml plus plots |
| A5 | ✅ | `perception/export.py`: OpenVINO FP16 and INT8_PTQ, static `input_size=(256,256)`, batch 1; assert a static input shape | 15 min | `.xml` files load |
| A6 | ✅ | `perception/inspector.py`: `OpenVINOInferencer`, device chain `NPU→GPU→CPU`, `CACHE_DIR`; returns a `DefectSignal` (bbox = largest blob of the thresholded anomaly map; heatmap PNG saved) | 20 min | Unit test passes on the CPU |
| A7 | ✅ | `python -m perception.rebaseline` (Harry wires it to `make rebaseline`): capture 60 good → retrain PaDiM → recalibrate, in under 2 minutes | 10 min | Timed |
| A8 | ✅ | `bench/benchmark.py`: N=100 warm runs per (model × precision × device); p50/p95; model size; first vs cached compile; writes `bench/results.md` | 15 min | CPU rows filled |
| A9 | ✅ | Commit; post status in `progress.md` | 5 min | — |
| A11 🆕 | ✅ | *(if time)* NVIDIA Build key (`NVIDIA_API_KEY` in `.env`); `reasoner/client.py`: one call to Nemotron 3.5 Super VL with a stand-in crop + its `DefectSignal` as JSON → one short line back; print the latency | 10 min | A line comes back, latency known |
| A10 🆕 | ✅ | `bench/power.py`: a context manager that reads Intel RAPL package energy (`/sys/class/powercap/intel-rapl:0/energy_uj`, which wraps around) and the max of `/sys/class/thermal/thermal_zone*/temp` before and after a run → joules, average watts, peak °C. Returns `None` off Linux (this laptop), so the benchmark still runs. `benchmark.py` adds mJ-per-inference columns | 15 min | Unit test with a fake sysfs folder passes |

### BLOCK B: Saturday 08:00 → Sunday 09:00 (Intel laptop and robot; follow the slot table in PRD 10)
| Time | Status | Task | Done when |
|---|---|---|---|
| 08:00–09:30 | ⬜ | Install on the Intel laptop; `ov.Core().available_devices` → CPU, GPU, NPU; run the Block A pipeline on the stand-in data there | NPU compiles, or the reason it fails is logged |
| 10:00–10:30 (robot slot) | ⬜ | Capture **real bricks at the inspection pose** (Harry's waypoint holds the brick): ~150 good, ~40 defective, ~30 held-out good; same lamp and crop | Data saved |
| 10:30–12:00 | ⬜ | Train PaDiM, PatchCore, EfficientAd → choose by AUROC and latency; calibrate; export; NPU parity check `[🟠 your call: which model]`. 🆕 **If the good bricks come in several colours:** PaDiM fits one Gaussian per patch position, so mixed colours blur "normal" and marker strokes hide in the spread. Compare PatchCore (nearest-neighbour memory bank, copes with several normal looks; check the batch-2 export, #3883) against **one PaDiM per colour** picked by mean hue (keeps the small NPU model). One colour → PaDiM stays the default. 🆕 Crop to the brick (fixed inspection pose; RealSense depth mask if the gripper or background lights up the heatmap) | Held-out AUROC ≥ 0.90 |
| 12:00–13:00 | ⬜ | **Intel workshop**. Ask: NPU and policy export, best Anomalib model on the NPU, what judges want in the optimization table | Notes in `progress.md` |
| 13:00–14:00 | ⬜ | Wire `inspect()` into `run.py` (Harry's state machine calls it; you don't edit `run.py` except the import line agreed in `progress.md`) `[⚠ touches @harry: run.py import line]` | Live verdict on screen |
| **15:30 gate** | ⬜ | With Harry: scripted full loop with real Anomalib, 5 bricks, no human | Pass |
| 15:30–17:00 | ⬜ | Anomalib benchmark across all devices and precisions; uncertainty band live. 🆕 **F12:** every row also gets mJ per inference and watts (A10); run a 5-minute sustained load per device for the thermal-headroom line. Cross-check one row with OpenVINO's `benchmark_app` | Table rows incl. energy |
| 17:00–19:00 | ⬜ | **F4 re-inspection logic (no robot needed):** if uncertain → score the RealSense colour view → max score → still uncertain = defective. Add the wrist-roll call (Nate's `reinspect(±90)`) behind a flag. 🆕 **Chain (PRD v2.2):** second shared-camera view (no motion) → **re-grasp** via Nate's primitive and re-inspect (Intel's named idea: "anomaly score triggers a re-grasp") → wrist roll if enabled → defective. Each step logged with its score. 🆕 **F15:** write the drift-alarm SQL for Harry (mean score of the last N perfect bricks vs `t_low`) | Unit test on saved borderline images |
| 19:00–21:00 | ⬜ | **20:30: live F4 test in the integration slot** (borderline brick works 3 times in a row). Before that, optimizations, each with a number: `AsyncInferQueue` so inference overlaps arm motion; (PrePostProcessor in-graph preprocessing already built, D30: only needs its Intel-laptop numbers) compile `CACHE_DIR`; `PERFORMANCE_HINT` LATENCY vs THROUGHPUT | Cycle time drop measured |
| 17:00–19:00 (same window, 🆕) | ⬜ | **F17 Nemotron reasoner:** `reasoner.explain(signal, crop, persona)` → async → narrator gets one grounded line (numbers passed in, JSON out, line rejected if it contradicts the label; template fallback on timeout or rate limit). `reasoner.hat_seen(top_frame)` for the cowboy trigger. `reasoner/rules.py`: kickoff rules text → checked `rules.yaml` | Lines arrive before PLACE in a mock run |
| 21:00–22:00 (GPU slot) | ⬜ | Benchmark Nate's ACT/SmolVLA IR on CPU and GPU (PyTorch vs OV FP16/INT8); end-to-end cycle before and after; bricks per minute `[⏸ waits on @nate: IR files]` | `bench/results.md` complete |
| 22:00–23:00 🆕 | ⬜ | **Nemotron eval:** 20 saved frames (perfect, defective, borderline, hat, no hat) → label agreement, region correct, hat accuracy, p50 latency; one prompt revision measured against it. This table is the NVIDIA write-up's "how we improved its outputs" | Table in `bench/results.md` |
| 23:00 | ⬜ | **Freeze.** 🆕 Leave the F12 sampler logging during Nate and Harry's 20 trials (peak °C, throttling yes/no). Sleep 00:00–05:00 | — |
| 06:00–09:00 | ⬜ | `make rebaseline` on the **demo table**; final numbers and plots into the README; check the submission | Done by 09:00 |

**Seams** (the same note is in the other two briefs):
- @harry: `run.py` calls `Inspector.inspect(frame, view, brick_id)` and turns `DefectSignal.label` into the instruction via `config/rules.yaml` (F1); mission control draws `heatmap_path`, `bbox`, `score`; telemetry logs `label`, `score`, `device`, `latency_ms`; `make rebaseline` → `python -m perception.rebaseline`.
- @harry 🆕: F13 shared capture hands you the same frames the policy sees; F15 needs your drift rule; the narrator takes your reasoner lines (`narrator.say(event, text=..., persona=...)`) and your `hat_seen` feeds his persona state machine (F18). Contract lines in PRD 7.3.
- @nate: F4 re-grasp and wrist roll call Nate's `Mover.reinspect(angle_deg)` (🆕 re-grasp = put down and pick again; exact signature agreed in `progress.md` before the 01:00 freeze); Nate's ACT/SmolVLA OpenVINO IR files come to `bench/` for the 21:00 GPU-slot benchmark.

## 4. Done log (newest first)
- ✅ **Drift rule, in-graph preprocessing, operator support** (2026-11-14 12:40, on `main` `4c96ef0`, 175 tests): `perception/drift.py` (F15, plugs into Harry's consumer; `good_mean` now saved by evaluate); `perception/preprocess.py` writes `model_ppp.xml` beside each IR (FP16 44.5 → 38.5 ms p50 on this laptop's CPU, scores identical); `bench/operators.py` adds an "Operator support" table to `bench/results.md` (CPU rows measured, GPU/NPU rows on the Intel laptop); `opencv-python` replaces the headless build (Harry's 05:32 ask). Still hardware-only: S2, S3, S4, S7 runs.
- ✅ **S1, S5, S6, bug fixes, dance** (2026-11-14 08:50, all on `main`, 143 tests across packages): S1 `perception/evaluate.py` (brick folds, out-of-fold t_low, dev/test defectives, bootstrap-by-brick AUROC, exact bounds) + raw scores (default export clamped good bricks to 0.0, measured) + `pixel_threshold`; S5 `perception/scene.py` (zone homography, brick-or-not key check D27, most isolated, `tall_object`, `brick_in_bowl`, `SceneLocator` = drop-in for `CountLocator`); S6 `perception/reason_trace.py`; inspector cache per device (NPU keeps its own); bench: any IR layout, multi-input policies, PyTorch baseline row, 1 Hz thermal, idle-net energy (S7 harness ready, Intel runs pending); dance `robot/dance.py` (D28). Waiting on @harry to wire `SceneLocator`, `tall_object`, `brick_in_bowl`, `ReasonTrace` and the dance into `run.py`.
- ✅ **A11 live + conversational lines** (2026-11-14 04:30, `main` @ `99f1d09`): Super VL is a reasoning model and spent all 80 tokens thinking, so thinking is off (`chat_template_kwargs.enable_thinking=false`). Lines think aloud (what it sees, what the score means, what it will do). It inverted a perfect verdict until the decided action and the band's meaning were passed in; now 4/4 correct on stand-in bricks, 1.7–2.7 s per line. Answers @harry's 04:16 request.
- ✅ **Block A, A1–A10 + A11 client** (2026-11-14 03:55, `main` @ `dd1c4d7`, 28 tests incl. a slow end-to-end pipeline test). Python 3.12 venv via `uv` (`perception/requirements.txt`). Stand-in data = `perception/synth.py` (synthetic bricks with marker strokes; scaffolding only, no number reported). Export is static 1×3×256×256 via `ov_kwargs`; INT8 calibration needs batch 1. The inspector compiles the IR itself (NPU→GPU→CPU, `runs/ov_cache`), not `OpenVINOInferencer` (no fallback). Rebaseline on this laptop: train 26 s + INT8 export 71 s + calibrate ≈ 102 s, plus ~18 s capture. A11: `reasoner/client.py` built and tested with a fake response; the live call waits on the key and the exact model id. **Gotchas:** run with `PYTHONUTF8=1` on Windows (torch's ONNX exporter prints emoji); the Intel GPU compiler drops `kernel.errors.txt` in the cwd (harmless, delete); RAPL `energy_uj` is root-only on Linux (`sudo chmod a+r`).

## 5. Working-style notes for the agent
- When you decide or finish something that changes the design, add or update its entry in `decisions.md` the same turn (CLAUDE.md §4a): facts and measured numbers only.
- Verbosity Level 0: options + a recommendation, no teaching notes. Flag scope creep at once. Spell out abbreviations once.
- Hackathon pace: the smallest thing that passes its *Done when*.

## 6. Open blanks (fill when the chat or repo answers them, CLAUDE.md 🔁)
- Stand-in objects and webcam path for Block A: {{objects}} · {{cam path}}
- Which Anomalib model ships (Block B 10:30): {{model}}
- Plan clock vs Espoo time for the Sunday 10:00 deadline: {{timezone}}
- Good bricks: one colour or several? {{colours}} · Which station camera is the RealSense? {{camera}}
- Nemotron model id: `nvidia/nemotron-3.5-super-vl-120b-a12b` (in `.env` as `NEMOTRON_MODEL`)

## 6a. Reference
### Minimal code (check names against the 2.7.0 docs)
```python
from anomalib.data import Folder; from anomalib.models import Padim; from anomalib.engine import Engine
from anomalib.deploy import ExportType, CompressionType, OpenVINOInferencer
dm = Folder(name="lego", root="data", normal_dir="good", abnormal_dir="defective")
m, e = Padim(), Engine(); e.fit(model=m, datamodule=dm)
e.export(model=m, export_type=ExportType.OPENVINO, compression_type=CompressionType.INT8_PTQ,
         datamodule=dm, input_size=(256, 256))
inf = OpenVINOInferencer(path=".../openvino/model.xml", device="NPU"); p = inf.predict(img)
```

### Pitfalls
- A previous team's Anomalib was "bring-up evidence, not a LEGO detector". Tonight is scaffolding only; your score comes from real bricks.
- The NPU accepts static shapes only. PatchCore can export with batch 2 (#3883), so check it. Prefer PaDiM or EfficientAd on the NPU.
- Scores are distances, not probabilities, so set thresholds from data.
- Benchmark only in your GPU slot (21:00), unless the measurement under load is intended.

### Nemotron notes (NVIDIA track rules)
- Must use **Nemotron 3.5 Super VL** in the working solution, make its contribution visible in the demo, and submit a short text: model, what it does, why it matters, how we improved its outputs.
- It is not a training track. NVIDIA Build API is OpenAI-compatible (`https://integrate.api.nvidia.com/v1`), free tier about 40 requests per minute per key: retries with backoff, one key per teammate.
- Never on the control path: start the request when INSPECT ends, speak it during PLACE, drop it if late.

### Links
- Anomalib: https://github.com/open-edge-platform/anomalib · Deploy: https://anomalib.readthedocs.io/en/latest/markdown/guides/reference/deploy/ · https://pypi.org/project/anomalib/2.7.0/
- PaDiM about 30× faster to train than PatchCore: https://datature.io/blog/visual-anomaly-detection-with-anomalib-a-hands-on-guide-2026
- NPU limits: https://docs.openvino.ai/2025/openvino-workflow/running-inference/inference-devices-and-modes/npu-device.html
- Band and parity reference (ideas only): https://github.com/ohong/intel-robotics
- Latency benchmark class: https://github.com/openvinotoolkit/physicalai

---
── Archived (superseded — do NOT action) ──
- *(none yet)*
