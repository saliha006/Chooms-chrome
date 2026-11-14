# PRD: SortSense, a closed-loop defect-sorting robot on Intel Core Ultra

| | |
|---|---|
| Event | Junction 2026, Espoo |
| Main track | **Intel x Ignite Next: Physical AI** (scored out of 100 by Intel) |
| Side tracks | ElevenLabs (voice narration), Aiven (managed PostgreSQL), Modal (training; no extra build). Nothing else. |
| Team | Saliha (perception, AI/ML, OpenVINO), Nate (robot and policies), Harry (integration, demo, side tracks) |
| Version | v2.1, Sat 14 Nov 00:10 (v2.0 + Modal side track + the §0 contradiction fixes) |
| **Hard deadline** | **Final submission SUNDAY 15 Nov 10:00** (Junction official). **Internal: everything submitted by 09:00 Sunday.** Ask the mentors whether 11:50 is our demo slot. |
| Work blocks | **Block A:** tonight 00:45–02:30, at home, **no Intel laptop, no arms**. **Block B:** Sat 08:00 → Sun 09:00, all hardware. **Feature freeze Sat 23:00.** |

---

## 0. NOW (decisions in force, pending, gates)
**In force**
- Only the follower arm moves; the leader is teleop only (Intel slides).
- Contracts in §7.3 frozen at 01:00 Sat; changes need all three and a `progress.md` decision entry.
- Docs: `CLAUDE.md`, `prd.md`, `builder-briefs/`, `skills/` live on the `context` branch; `progress.md` and code on `main`. Branches `perception-saliha`, `robot-nate`, `integration-harry`.
- v2.1 fixes (2026-11-14 00:10): ACT = **54** episodes (9 start positions × 6); SmolVLA 19:00 gate follows Nate's brief (keep at ≥ 4/10 unless scripted placement is clearly better); Modal added to §13 Q5; Saliha's §10 slots aligned with Saliha's brief. Where §10 and a brief still differ on times, **the brief wins**.

**Pending (confirm with mentors, §13)**
- Is 11:50 Sunday our demo slot? Is the 10:00 Sunday deadline on Espoo time, and does our plan clock match it?
- Challenge-Day task and kickoff sorting rules.
- ElevenLabs, Aiven and Modal criteria.

**Gates:** Sat 15:30 scripted full loop · 17:00 ACT ≥ 6/10 · 19:00 SmolVLA (Nate's brief) · 23:00 freeze · Sun 09:00 submit.

## 1. Summary
An SO-101 follower arm picks a Lego brick and holds it up to the camera (ACT). Anomalib scores it as perfect, defective or uncertain. The verdict becomes a language instruction for SmolVLA, which places the brick in the blue bowl (perfect) or the red bowl (defective). The whole loop runs on the Core Ultra X9 388H with OpenVINO, with each model placed deliberately on the NPU, GPU or CPU, and it recovers from uncertain detections and failed grasps.

## 2. Where we win: how we weight effort
Every criterion must be covered, but effort follows **points × how much we control the outcome**.

| Weight | Criterion (pts) | Why |
|---|---|---|
| ★★★★★ | **End-to-end loop (25)** | Biggest block. The last team on this challenge never moved its arm. A scripted loop is our insurance, and learned policies replace it. |
| ★★★★★ | **Anomalib (20)** | Fully controllable and deterministic. Max it: held-out AUROC, confusion matrix, heatmap, `DefectSignal` driving the robot, uncertainty band. |
| ★★★★★ | **OpenVINO (20)** | Software-only, measurable, and teams who fight the robot neglect it. A full CPU/GPU/NPU × FP16/INT8 table plus the reasoning behind each choice is our differentiator. |
| ★★★★ | VLA + Physical AI Studio (20) | Riskiest (export bugs). Studio must be **visibly used** for recording, training, export and runtime even if SmolVLA underperforms. A partly working SmolVLA beats a scripted placement. |
| ★★★ | Reliability (10) | The uncertainty band and grasp retry are cheap and named explicitly in the rubric. |
| ★ | Innovation (5) | Comes for free from narration, mission control and a clear explanation. |

## 3. Goals, non-goals, metrics
**Goals:** one integrated closed loop (PERCEIVE → DETECT → REASON → ACT → OPTIMIZE); measured detection; measured optimization; reliable live demo with a planned recovery.
**Non-goals (decided):** second actuated arm (the leader is a teleop device), freeing cables, removing obstacles or transparent objects, Lego reach tool, rolling plate, web frontend.

| Metric | Target | Minimum to demo |
|---|---|---|
| Correct bowl over 20 logged trials | ≥ 90% | ≥ 70% |
| Anomalib AUROC on held-out real bricks | ≥ 0.95 | ≥ 0.90 |
| Anomalib latency, best device | ≤ 15 ms | ≤ 50 ms |
| Cycle time per brick / throughput | ≤ 25 s / ≥ 2.4 bricks per min | ≤ 45 s |
| Unhandled failures | 0 | 0 |

## 4. Requirements traceability (re-checked against every Intel slide)
| ID | Requirement (slide) | Crit. | Owner | Test |
|---|---|---|---|---|
| R1 | Install **Physical AI Studio** and **Anomalib v2.7.0** (HW/SW) | 2, 3 | Nate / Saliha | `pip show anomalib` = 2.7.0; Studio UI opens |
| R2 | Capture workspace images; Anomalib flags defects, **trained on our real bricks** (Expectation 1) | 2 | Saliha | Held-out AUROC and confusion matrix |
| R3 | Defect output downstream as a **structured signal, label, score or localized region** (Expectation 1) | 2, 1 | Saliha | `DefectSignal` logged for every brick |
| R4 | **VLA via Physical AI Studio** interprets the task instruction plus the perception result → action intent (Expectation 2) | 3 | Nate | Instruction built from the verdict drives SmolVLA |
| R5 | **Studio stack builds the application flow** ("perception, task reasoning, robot control, orchestration"): `run.py` uses the Studio runtime (`physicalai` `InferenceModel` / `RobotRuntime`) | 3 | Harry + Nate | Shown on the architecture slide; code uses the runtime |
| R6 | Action → SO-101 motion, grasp, sort (Expectation 3) | 1, 5 | Nate | Brick in the correct bowl |
| R7 | OpenVINO: conversion, precision, graph optimization, **pre/post-processing**, device selection (Expectation 4) | 4 | Saliha | Benchmark table (section 7.4) |
| R8 | Deploy on Core Ultra 3 using NPU/GPU/CPU by workload and **operator support**, keeping **control responsive** (Expectation 5) | 4 | Saliha + Harry | Device map; inference off the control thread |
| R9 | Report **latency, throughput, deployment efficiency** (criterion 4) | 4 | Saliha | p50/p95, bricks per min, model size and compile time, FP16 vs INT8 |
| R10 | Pipeline per End Goal: **ACT** pick and present → **Anomalib** → **SmolVLA** place | 1, 3 | Nate | Each stage visible live |
| R11 | Sort **per kickoff rules**; ready for the **Challenge-Day task** | 1 | Harry | `config/rules.yaml`, editable in 1 minute; Challenge-Day task confirmed with mentors |
| R12 | **Object localization** (criterion 5): brick presence and position in the pick zone before each pick; stop when the zone is empty | 5 | Harry | Colour-blob position (plus RealSense depth) shown and logged |
| R13 | **Recovery from incorrect or uncertain detections** plus repeatability (criterion 5) | 5 | Saliha (band), Nate (retry) | Planned borderline brick handled 3 times in a row |
| R14 | Closed-loop demo, then explain architecture and optimization (Expectation 6, End Goal) | 1, 6 | Harry | Rehearsed 2-minute script (section 11) |
| R15 | Train on the provided **Modal** GPU (HW/SW) | 3 | Nate | Checkpoints back and exported |
| R16 | Follow the **printed robot safety guidelines** (HW/SW) | — | All | E-stop drill; speed cap |
| R17 | Deliverables: prototype, VLA + Anomalib integration, OpenVINO deployment, live demo (End Goal) | all | Harry | Section 12 checklist |

## 5. Judging evidence
| Criterion | What judges see |
|---|---|
| End-to-end (25) | One keypress, 5+ bricks sorted with no human touch; live state display |
| Anomalib (20) | Score histogram, held-out AUROC and confusion matrix, live heatmap, `DefectSignal` → instruction, uncertainty band |
| VLA + Studio (20) | Studio used for record/train/export (live view and screenshots); verdict → "place the brick in the red bowl" → SmolVLA; app built on the Studio runtime |
| OpenVINO (20) | PyTorch vs OV FP16 vs INT8 × CPU/GPU/NPU per stage; cycle time before and after; model size; compile time with cache; reason for each device choice |
| Reliability (10) | 20 logged trials (Aiven query); live uncertain-brick recovery; grasp retry; e-stop |
| Innovation (5) | Spoken reasoning; mission control; one-slide architecture |

## 6. Operator flow
1. Place 1–5 bricks in the taped pick zone and press **S**.
2. For each brick:
   - Localize the brick.
   - ACT picks it and presents it at the inspection pose.
   - Anomalib scores it; the screen shows the heatmap and score.
   - The voice states the verdict.
   - The instruction goes to SmolVLA, which places the brick.
   - Log the result.
3. If the verdict is **uncertain**: take a second view (RealSense, or a wrist roll) and re-score. If it is still uncertain, put it in the red bowl and say so.
4. If the grasp fails (the gripper closes fully): retry once, then say "need help" and go home.
5. When the zone is empty, stop and speak the run summary. **P** pauses, **E** is the e-stop (torque off), **Q** goes home and quits.

## 7. Architecture

### 7.1 Diagram
```
Own laptops (Claude Code, git) --SSH+tmux--> INTEL LAPTOP = only runtime
 Webcam 2K (inspect) ─┐            ┌────────────────────────────────────────────────┐
 RealSense D415 ──────┼─ capture ─▶│ run.py state machine (CPU) on physicalai runtime │
 Wrist cam ───────────┘   (CPU)    │ IDLE→LOCATE→PICK→VERIFY_GRASP→INSPECT→DECIDE     │
                                   │  →[REINSPECT]→PLACE→LOG→next | HOME on any error │
                                   │ PICK: ACT (OV, GPU) · PLACE: SmolVLA (OV GPU→CPU→PT)│
                                   │ INSPECT: Anomalib (OV INT8, NPU) → DefectSignal  │
                                   │ DECIDE: rules.yaml → instruction string          │
                                   │ fallback/: scripted waypoints (same Mover API)   │
                                   │ robot/io.py ↔ SO-101 follower (USB serial)       │
                                   │ threads: narrator (ElevenLabs cache) · telemetry │
                                   │ (queue→JSONL→Aiven PG) · ui (OpenCV, keys S/P/E/Q)│
                                   └────────────────────────────────────────────────┘
Modal GPU: ACT and SmolVLA training (datasets via HF Hub) → checkpoints → OpenVINO export
```
Control and inference never touch the network. Narration and telemetry are non-blocking and work offline.

### 7.2 Device map
| Workload | Device | Why | Fallback |
|---|---|---|---|
| Anomalib (PaDiM/EfficientAd, static 1×3×256×256, INT8_PTQ) | **NPU** | Small convolutional net with static shapes; low power; frees the GPU | GPU → CPU |
| ACT | **GPU** | Transformer, called often | CPU |
| SmolVLA (450M parameters) | **GPU** | Heaviest model | CPU with f32 hint → PyTorch |
| Capture, pre-processing, state machine, serial | **CPU** | Control-critical | n/a |

### 7.3 Contracts (frozen at 01:00 Saturday; change only via `progress.md`)
```python
# common/interfaces.py (Harry owns)
@dataclass
class DefectSignal:
    brick_id: int; view: str            # "webcam" | "realsense" | "wrist"
    label: str                          # "perfect" | "defective" | "uncertain"
    score: float; t_low: float; t_high: float
    bbox: tuple | None; heatmap_path: str | None
    model: str; device: str; latency_ms: float
class Inspector(Protocol):               # perception/ (Saliha)
    def inspect(self, frame, view: str, brick_id: int) -> DefectSignal: ...
class Mover(Protocol):                   # policies/ (Nate) and fallback/ (Harry)
    def pick_and_present(self) -> bool: ...
    def place(self, instruction: str) -> bool: ...
    def reinspect(self, angle_deg: int) -> bool: ...
    def gripper_empty(self) -> bool: ...
    def home(self) -> None: ...
    def estop(self) -> None: ...
# robot/io.py (Nate): connect(), observe(), act(), torque_off(); shared by policies/ and fallback/
# narrator.say(event, **kw) and telemetry.log(**row): non-blocking (Harry)
```
`rules.yaml`: `perfect → "place the brick in the blue bowl"`, `defective → "place the brick in the red bowl"`, `uncertain → reinspect once, then defective`.
Telemetry table `events`: `run_id, brick_id, ts, state, label, score, device, stage, latency_ms, outcome, note`.

### 7.4 Benchmark table (Saliha; goes in the README)
| Stage | PyTorch CPU | OV FP16 CPU | OV FP16 GPU | OV INT8 NPU | Chosen |
|---|---|---|---|---|---|
| Anomalib | | | | | |
| ACT / chunk | | | | n/a | |
| SmolVLA / chunk | | | | n/a | |
| Cycle time, bricks per min | before | | | after | |
Plus p50/p95, model size (MB) FP32 vs INT8, first-compile vs cached-compile time.

## 8. Features beyond the baseline (all in scope)
| # | Feature | Person-hours | Owner | Crit. |
|---|---|---|---|---|
| F1 | `DefectSignal` → instruction | 1–2 | Saliha → Harry | 2, 3 |
| F2 | Device map, INT8, async, PrePostProcessor, compile cache, benchmark | 4–6 | Saliha | 4 |
| F3 | Uncertainty band (thresholds from histograms) | 0.5–1 | Saliha | 2, 5 |
| F4 | Re-inspection: RealSense second view first, wrist roll ±90° if time allows | 2–4 | Saliha + Nate | 5 |
| F5 | Grasp check (gripper position) plus one retry | 1–2 | Nate | 5 |
| F6 | Mission-control window, keys S/P/E/Q | 2–3 | Harry | 1, 6 |
| F7 | ElevenLabs narration (template text, 2 voices, cached clips) | 1–2 | Harry | 6, side track |
| F8 | Aiven telemetry plus success-rate query | 1–2 | Harry | 5, side track |
| F9 | Brick localization and empty-zone stop (R12) | 1–2 | Harry | 5, 1 |
| F10 | Modal side track: reproducible `train/modal_train.py`, ACT + SmolVLA trained in parallel on Modal GPUs, GPU type, time and cost in the README. **No frontend, no extra endpoint.** Drop it if the Modal brief requires a deployed web app. | 0.5 | Nate | side track |

## 9. Fail-safes (from teams that failed this before, and from our own mistakes)
| Risk | Guard |
|---|---|
| Arm never moved by the app (ohong/intel-robotics) | **Scripted full loop by Sat 15:30**; learned policies swap in behind the same `Mover` API |
| Anomalib "bring-up evidence, not a LEGO detector" (previous team) | Tonight's stand-in data is scaffolding only; **retrain on real bricks Saturday**; report held-out metrics |
| ACT outputs the same pose whatever the input (Studio #998) | `optimizer_lr=1e-5`; 10 rollouts before integrating |
| SmolVLA export errors, NaNs, deleted checkpoint (#1384, PR #1403, #1414, #1169, physicalai #174) | **Test the export tonight on a public checkpoint**; back up before export; task string at warm-up; GPU → CPU f32 → PyTorch |
| SmolVLA "grasped at air" with wide starts | Taped pick zone of about 10 cm |
| NPU needs static shapes | Static export; check the shape; GPU fallback |
| Camera index changes, lighting changes, calibration drift | `/dev/v4l/by-id` paths; own lamp; **`make rebaseline`** (60 images, under 2 minutes) on the demo table; check the home pose before every run |
| Modal or upload surprises | **Modal script smoke-tested tonight** on a public dataset |
| Venue Wi-Fi blocks SSH | Phone hotspot or cable; the runtime needs no network |
| Our own earlier mistake: assuming two working arms | Only the follower moves; the leader is for teleop |
**Safety:** E = torque off; joint limits and a speed cap; one person always watches the arm; follow the printed guidelines.

## 10. Plan and hardware slots

### Block A: tonight 00:45–02:30 (no hardware). Each person works only in their own folders.
| Saliha | Nate | Harry |
|---|---|---|
| Full perception pipeline on stand-in images (own webcam plus any identical small objects): capture, train, thresholds, OV export, inspector, rebaseline, benchmark harness (CPU) | Modal training script smoke-tested on a public SO-100/101 dataset; **SmolVLA/ACT → OpenVINO export test** on a public checkpoint; `robot/io.py` with a mock; recording protocol | Repo, `interfaces.py` (01:00 freeze), `run.py` with mocks, mission control, scripted-fallback skeleton, Aiven and ElevenLabs set up and wired, README and diagram skeleton |

### Block B: Saturday 08:00 → Sunday 09:00. Hardware slot table (one robot user at a time)
| Time | Robot / Intel laptop GPU | Saliha | Nate | Harry |
|---|---|---|---|---|
| 08:00–09:00 | installs, no robot motion | Install Anomalib on the Intel laptop; verify NPU | Install Studio (xpu); calibrate both arms | Mount cameras, by-id paths, lamp, tape |
| 09:00–09:30 | **Nate** | Port pipeline; device check | 5 test episodes → Modal smoke | Configs on the real laptop |
| 09:30–10:00 | **Harry** | — | — | Teach waypoints (pick, inspect pose, bowls, home) |
| 10:00–10:30 | **Saliha** | Capture about 150 good, 40 defective, 30 held-out images at the inspection pose | Prep recording | Hold the inspect pose via waypoints |
| 10:30–12:30 | **Nate** | Train, thresholds, export, NPU (until 12:00) | Record 54 ACT episodes | Resets |
| 12:00–13:00 | — | **Intel workshop** (Hardware Lab) | — | — |
| 12:30 | — | — | **Launch ACT training** | — |
| 12:30–14:00 | **Nate** | Wire `inspect()` into `run.py` | Record 50 SmolVLA episodes (25/25) | Resets |
| 14:00 | — | — | **Launch SmolVLA training** (10k steps) | — |
| 14:00–15:30 | **Harry + Saliha** | **Gate 15:30: scripted full loop with real Anomalib, 5 bricks, no human** | Grasp check, wrist-roll primitive (offline code) | Localization, mission control on real feed |
| 15:30–16:00 | **Nate** | Benchmark Anomalib (CPU/GPU/NPU) | Grasp retry test | Narration and telemetry live |
| 16:00–17:00 | **Nate** | Benchmark (cont.); uncertainty band live | **Gate 17:00:** ACT export, 10 trials (≥6/10 keep) | Narration/telemetry; README |
| 17:00–19:00 | **Nate** | F4 logic offline (RealSense view) | **Gate 19:00:** SmolVLA export, 10 trials (≥6/10 keep; ≥4/10 still keep unless scripted placement is clearly better; else scripted place) | Integrate the policies swap |
| 19:00–21:00 | **Nate + Harry** (+ Saliha at 20:30 for the F4 live test) | Async, PrePostProcessor, cache; F4 live test 20:30 | Integrate learned policies | Integrate |
| 21:00–22:00 | **Saliha** (GPU) | Benchmark ACT/SmolVLA, cycle time before and after | — | Diagram, README |
| 22:00–23:00 | all | Fix | Fix | Fix |
| **23:00** | **FEATURE FREEZE** | | | |
| 23:00–01:00 | Nate + Harry | Sleep 00:00–05:00 | 20 logged trials, then sleep 01:00–06:00 | Film good runs, then sleep 01:00–06:00 |
| 06:00–09:00 | all | `make rebaseline` on demo table; numbers into README | Final runs; recalibrate | Edit video; submission text |
| **09:00** | **SUBMIT** | | | |
After 09:00: rehearse 3–4 times, including the e-stop drill and the uncertain-brick moment.

### Conflict rules
- Folder ownership:
  - Saliha: `perception/`, `bench/`
  - Nate: `robot/`, `policies/`, `train/`
  - Harry: `run.py`, `common/`, `fallback/`, `ui/`, `narrator/`, `telemetry/`, `config/`, docs
- Commit only in your own folders; `git pull --rebase` before pushing; never force-push.
- Contract changes go through `progress.md` first.
- **`progress.md`** (on `main`) gets one entry per finished thing: who, what, when (date and time), and whether it conflicts with anyone. Format at the top of the file.

## 11. Demo script (2 minutes)
- 0:00 The problem.
- 0:10 Press S: perfect brick → blue bowl, narrated.
- 0:35 Defective brick: heatmap → red bowl.
- 0:55 Planted borderline brick: "taking a second look" → decision.
- 1:15 Architecture and device map.
- 1:35 Benchmark before → after.
- 1:50 Reliability from Aiven.
- 2:00 End.

Keep the backup video on a second screen.

## 12. Submission checklist (09:00 Sunday)
- [ ] Public MIT repo, with every reused repo credited
- [ ] README: how to run, architecture, device rationale, benchmark table, trial results
- [ ] Video ≤ 2 minutes
- [ ] Junction Platform: Intel challenge, plus ElevenLabs and Aiven if allowed
- [ ] PyTorch checkpoints backed up; OV models or HF links

## 13. Open questions for mentors (Saturday 08:00–09:00)
1. Is 11:50 our demo slot? What exactly is the **Challenge-Day task**, and does it use new bricks or positions?
2. Modal access, GPU hours, and whether Studio connects to it.
3. Is reuse of open-source code confirmed?
4. Is there a stack-verification script for Ubuntu 26.04 / Anomalib 2.7.0? Can policies export to the NPU?
5. ElevenLabs, Aiven and Modal challenge criteria, and whether we can enter them alongside Intel (Modal: does it need a deployed web app?).

## 14. References
- Physical AI Studio: https://github.com/open-edge-platform/physical-ai-studio
- OpenVINO Physical AI runtime: https://github.com/openvinotoolkit/physicalai · https://docs.openvino.ai/2026/physical-ai.html
- LeRobot: https://github.com/huggingface/lerobot · https://huggingface.co/docs/lerobot/so101 · https://huggingface.co/docs/lerobot/smolvla
- Anomalib: https://github.com/open-edge-platform/anomalib · https://anomalib.readthedocs.io/en/latest/markdown/guides/reference/deploy/
- Prior attempt (ideas only): https://github.com/ohong/intel-robotics
- NPU limits: https://docs.openvino.ai/2025/openvino-workflow/running-inference/inference-devices-and-modes/npu-device.html
