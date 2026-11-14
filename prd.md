# PRD: SortSense, a closed-loop defect-sorting robot on Intel Core Ultra

| | |
|---|---|
| Event | Junction 2026, Espoo |
| Main track | **Intel x Ignite Next: Physical AI** (scored out of 100 by Intel) |
| Side tracks | **ElevenLabs** (MLH: live reasoning voice + the cowboy personality switch, F7/F18) · **NVIDIA Nemotron 3.5 Super VL** (the reasoning brain behind the voice, F17) · **Aiven** (live event streaming that the cell reacts to, F15) · **Modal** (training + training logs only, F10/F11; **no frontend ever**, dropped if it would need one). Nothing else. |
| Team | Saliha (perception ML, OpenVINO, Nemotron reasoning), Nate (robot and policies, Modal training), Harry (integration, ElevenLabs personality voice, Aiven streaming, demo) |
| Version | v2.3, Sat 14 Nov 00:55 (v2.2 + the team's product vision: Intel task first, then the personality layer; changes listed in §0) |
| **Hard deadline** | **Final submission SUNDAY 15 Nov 10:00** (Junction official). **Internal: everything submitted by 09:00 Sunday.** Ask the mentors whether 11:50 is our demo slot. |
| Work blocks | **Block A:** tonight 00:45–02:30, at home, **no Intel laptop, no arms**. **Block B:** Sat 08:00 → Sun 09:00, all hardware. **Feature freeze Sat 23:00.** |

---

## 0. NOW (decisions in force, pending, gates)
**In force**
- Only the follower arm moves; the leader is teleop only (Intel slides).
- Contracts in §7.3 frozen at 01:00 Sat; changes need all three and a `progress.md` decision entry.
- Docs: `CLAUDE.md`, `prd.md`, `builder-briefs/`, `skills/` live on the `context` branch; `progress.md` and code on `main` (a `.gitignore` keeps everything else local). **One branch per person:** `perception-ml-saliha`, `robot-policies-nate`, `integration-voice-harry`.
- v2.1 fixes (2026-11-14 00:10): ACT = **54** episodes (9 start positions × 6); SmolVLA 19:00 gate follows Nate's brief (keep at ≥ 4/10 unless scripted placement is clearly better); Modal added to §13 Q5; Saliha's §10 slots aligned with Saliha's brief. Where §10 and a brief still differ on times, **the brief wins**.

- **v2.2 (2026-11-14 00:30), from the Junction challenge page and side-track pages:**
  - **Two Intel rubrics exist.** The kickoff slides (§2: 25/20/20/20/10/5) and the Junction page (§2a: task success 30, Intel integration 30, dataset and pipeline quality 20, system efficiency 20). We plan to the slides and cover the page's extras: robustness to shifted and cluttered bricks, the Robotics AI Suite, clean teleop data, **power and thermal headroom**. Ask which one scores us (§13 Q6).
  - Objects are **Duplo** bricks; **we draw the defects ourselves with markers**. Cameras: one **top view**, one **inspection** (at least one is the RealSense D415), plus the wrist cam.
  - Intel's wish list, now in scope: **anomaly score triggers a re-grasp** (F4), **cameras shared between policy and inspection** (F13), **INT8 quantization** (F2), **"how few demonstrations are enough"** (F11), **bricks in new positions** (F14).
  - New features: F11 demo-count sweep on Modal (Nate) · F12 power, energy and thermal benchmark (Saliha) · F13 shared capture (Harry) · F14 shifted/cluttered test (Nate + Harry) · F15 Aiven as system of record + drift alarm (Harry + Saliha) · F16 Modal live dashboard (Harry, optional, after the freeze is safe) · F17 Nemotron (pending).
  - Anomalib model choice: if the good bricks come in **several colours**, PaDiM's one-Gaussian-per-patch assumption breaks; use PatchCore or one PaDiM per colour (§7.2, Saliha's brief).

- **v2.3 (2026-11-14 00:55), the team's vision (§1a):**
  - **Priority 1, always:** the Intel task done accurately, with smooth arm motion and a reasonable cycle time. Nothing in the personality layer may slow or risk it.
  - **Priority 2, the twist:** the robot **explains its reasoning out loud, live**, in a cool, collected voice; an **obstacle** or a **cowboy hat** flips it into a **cowboy persona** ("Holy smokes!", cowboy accent and wording) until the moment passes, then it drifts back to calm (F7, F18).
  - **NVIDIA is in:** Nemotron 3.5 Super VL writes the grounded live lines and spots the hat (F17). It is not a training track: the rules require the model in the working product, visible in the demo, plus a short written explanation.
  - **Aiven = streaming:** Aiven for Apache Kafka carries every event live; consumers act on it (drift alarm, persona alerts) and land it in Aiven PostgreSQL (F15). A cloud hop never makes the robot faster, so the robot never waits on it: control stays local, and the stream is how everything else sees and reacts to the cell.
  - **Modal = training + logs only.** F16 (dashboard) is dropped: **no frontend**. If Modal would need one, drop Modal.
  - **ElevenLabs page found (MLH):** "natural, emotionally expressive voices", fully autonomous audio. No scored rubric; prize = earbuds.
  - Items more than ~10 hours of work live in a local-only `extension-if-more-time.md` (never pushed). Items within ~1–2 hours of slack are the stretch list in §8a.

**Pending (confirm with mentors, §13)**
- Is 11:50 Sunday our demo slot? Is the 10:00 Sunday deadline on Espoo time, and does our plan clock match it?
- Challenge-Day task and kickoff sorting rules.
- Which Intel rubric is used (slides or Junction page)?
- Is a cowboy hat (soft, light) in the workspace OK under the printed safety rules?
- Aiven for Apache Kafka: free plan, or does it come out of the $50 credits? Fallback: PostgreSQL `LISTEN/NOTIFY` streaming on the free PostgreSQL plan.
- Side-track criteria: Aiven = meaningful use 40, technical 30, impact 20, creativity 10 · NVIDIA = meaningful Nemotron use 25, execution 25, output quality 25, creativity 25 · Modal = effective use 40, ambition 25, impact 20, deployed-app demo 15 (we accept losing that 15) · ElevenLabs (MLH) = no rubric published.

**Gates:** Sat 15:30 scripted full loop · 17:00 ACT ≥ 6/10 · 19:00 SmolVLA (Nate's brief) · 23:00 freeze · Sun 09:00 submit.

## 1. Summary
An SO-101 follower arm picks a Duplo brick (we mark the defective ones ourselves with markers) and holds it up to the inspection camera (ACT). Anomalib scores it as perfect, defective or uncertain. The verdict becomes a language instruction for SmolVLA, which places the brick in the blue bowl (perfect) or the red bowl (defective). The whole loop runs on the Core Ultra X9 388H with OpenVINO, with each model placed deliberately on the NPU, GPU or CPU, and it recovers from uncertain detections and failed grasps.

On top of that it has a personality. It **talks through its reasoning while it works**, in a cool, collected voice ("Score 0.81, well past my 0.55 line. Marker streak, top left. Red bowl."). When it meets an **obstacle** or spots the **cowboy hat**, it yells "Holy smokes!" and **switches into a cowboy**, with a new voice, accent and wording, until things are back to normal. Then it cools down and returns to its calm self.

## 1a. Vision and priority order (the team's words, made precise)
1. **The Intel task, perfectly.** Same task as every team: tell perfect from defective bricks and sort them by the kickoff rules, end to end. Accurate, smooth motion, reasonable cycle time. Every gate in §10 protects this.
2. **Live reasoning voice (ElevenLabs + Nemotron).** Each step is said as it happens, grounded in real numbers from `DefectSignal`. Calm persona by default.
3. **Cowboy personality switch (ElevenLabs).** Triggers: an obstacle in the workspace (local RealSense depth, F18) or the cowboy hat in view or touched (Nemotron VL on the top view, plus the H key as a demo-safe backup). In: instant, with a cached "Holy smokes!". Out: once the trigger has cleared and one brick is done, one half-way line, then calm. **The motion never waits for a word.**
4. **Side tracks ride on 2 and 3:** Nemotron is the brain (NVIDIA), the voice is the face (ElevenLabs), Kafka carries the events everyone reacts to (Aiven), and Modal trains the policies (Modal).
5. **Never:** a frontend, anything on the control path that needs the network, a gag that costs a gate.

## 2. Where we win: how we weight effort
Every criterion must be covered, but effort follows **points × how much we control the outcome**.

| Weight | Criterion (pts) | Why |
|---|---|---|
| ★★★★★ | **End-to-end loop (25)** | Biggest block. The last team on this challenge never moved its arm. A scripted loop is our insurance, and learned policies replace it. |
| ★★★★★ | **Anomalib (20)** | Fully controllable and deterministic. Max it: held-out AUROC, confusion matrix, heatmap, `DefectSignal` driving the robot, uncertainty band. |
| ★★★★★ | **OpenVINO (20)** | Software-only, measurable, and teams who fight the robot neglect it. A full CPU/GPU/NPU × FP16/INT8 table plus the reasoning behind each choice is our differentiator. |
| ★★★★ | VLA + Physical AI Studio (20) | Riskiest (export bugs). Studio must be **visibly used** for recording, training, export and runtime even if SmolVLA underperforms. A partly working SmolVLA beats a scripted placement. |
| ★★★ | Reliability (10) | The uncertainty band and grasp retry are cheap and named explicitly in the rubric. |
| ★ | Innovation (5) | The personality layer (live reasoning voice, cowboy switch) is our memorable moment, built only on top of a working loop. |

### 2a. The Junction page rubric (cover it with the same work)
| Junction page criterion | What scores it | Our features |
|---|---|---|
| Task success (30%): accuracy, cycle time, robustness to shifted or cluttered bricks | Correct-bowl rate, bricks per minute, a test on unseen start positions and a 3-brick pile | 20 trials, F9, F14 |
| Intel technology integration (30%): OpenVINO Physical AI, Robotics AI Suite, NPU and iGPU offload | `physicalai` runtime in `run.py`, device map, NPU + GPU both used | R5, R8, F2 |
| Dataset and pipeline quality (20%): clean teleop data, fine-tuning in Studio | Recording protocol, rejected-episode log, dataset card on the HF Hub, success vs number of demos | A5 (Nate), F11 |
| System efficiency (20%): inference latency, thermal headroom, power on Core Ultra | p50/p95 latency, **energy per inference and per brick, package power, temperature during the 20 trials** | F2, F12 |

## 3. Goals, non-goals, metrics
**Goals:** one integrated closed loop (PERCEIVE → DETECT → REASON → ACT → OPTIMIZE); measured detection; measured optimization; reliable live demo with a planned recovery.
**Non-goals (decided):** second actuated arm (the leader is a teleop device), freeing cables, removing obstacles (we detect them, react and skip them) or transparent objects, Lego reach tool, rolling plate, **any frontend or web app** (a side track that needs one gets dropped).

| Metric | Target | Minimum to demo |
|---|---|---|
| Correct bowl over 20 logged trials | ≥ 90% | ≥ 70% |
| Anomalib AUROC on held-out real bricks | ≥ 0.95 | ≥ 0.90 |
| Anomalib latency, best device | ≤ 15 ms | ≤ 50 ms |
| Cycle time per brick / throughput | ≤ 25 s / ≥ 2.4 bricks per min | ≤ 45 s |
| Unhandled failures | 0 | 0 |
| Correct bowl on **unseen start positions** (F14) | ≥ 80% | reported honestly |
| Energy per Anomalib inference, best device (F12) | lowest of CPU/GPU/NPU, reported in mJ | measured |
| Package temperature over 20 trials (F12) | no thermal throttling | logged |
| Reasoning line spoken after the verdict (F7/F17) | ≤ 2 s, never delays motion | template line ≤ 0.3 s |
| Cowboy switch after a trigger (F18) | ≤ 1 s (cached exclamation) | ≤ 2 s |

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
| R18 | Robustness to **shifted or cluttered** bricks (Junction page, task success) | 5, page 30% | Nate + Harry | F14 trials logged |
| R19 | **Thermal headroom and power** on Core Ultra (Junction page, system efficiency) | 4, page 20% | Saliha | F12 numbers in `bench/results.md` |
| R20 | **Clean teleop data** and fine-tuning in Studio; how few demos are enough (Junction page, dataset quality) | 3, page 20% | Nate | Rejected-episode log, dataset card, F11 curve |
| R21 | **ElevenLabs:** natural, emotionally expressive voice, fully autonomous (MLH page) | ElevenLabs, 6 | Harry | Live reasoning lines + cowboy switch on video |
| R22 | **NVIDIA:** Nemotron 3.5 Super VL in the working solution, its contribution visible in the demo, plus a written explanation (model, what it does, why it matters, how we improved its outputs) | NVIDIA | Saliha | Lines on screen tagged "Nemotron"; eval table; submission text |
| R23 | **Aiven:** at least one service as a meaningful part, with what it enables shown | Aiven | Harry | Kafka stream → drift and persona alerts → PostgreSQL report |

## 5. Judging evidence
| Criterion | What judges see |
|---|---|
| End-to-end (25) | One keypress, 5+ bricks sorted with no human touch; live state display |
| Anomalib (20) | Score histogram, held-out AUROC and confusion matrix, live heatmap, `DefectSignal` → instruction, uncertainty band |
| VLA + Studio (20) | Studio used for record/train/export (live view and screenshots); verdict → "place the brick in the red bowl" → SmolVLA; app built on the Studio runtime |
| OpenVINO (20) | PyTorch vs OV FP16 vs INT8 × CPU/GPU/NPU per stage; cycle time before and after; model size; compile time with cache; reason for each device choice |
| Reliability (10) | 20 logged trials (Aiven query); live uncertain-brick recovery; grasp retry; e-stop |
| Innovation (5) | Live spoken reasoning grounded in the numbers; the cowboy switch; mission control; one-slide architecture; success-vs-demos curve (F11); energy per brick (F12) |

## 6. Operator flow
1. Place 1–5 bricks in the taped pick zone and press **S**.
2. For each brick:
   - Localize the brick.
   - ACT picks it and presents it at the inspection pose.
   - Anomalib scores it; the screen shows the heatmap and score.
   - The voice explains the verdict live, in the current persona (calm by default).
   - The instruction goes to SmolVLA, which places the brick.
   - Log the result.
3. If the verdict is **uncertain**: score a second view from a shared camera (free, no motion). Still uncertain → **re-grasp** (put the brick back down, pick it again, re-inspect: Intel's "anomaly score triggers a re-grasp"); wrist roll ±90° if time allows. Still uncertain → red bowl, said aloud.
4. If the grasp fails (the gripper closes fully): retry once, then say "need help" and go home.
5. **Obstacle** in the workspace (depth says something taller than a brick, or not brick-shaped) or the **cowboy hat** in view → "Holy smokes!", cowboy persona; the arm skips the obstacle (never picks it) and carries on with the bricks. Trigger cleared + one brick done → half-way line → calm.
6. When the zone is empty, stop and speak the run summary. **P** pauses, **E** is the e-stop (torque off), **Q** goes home and quits.

## 7. Architecture

### 7.1 Diagram
```
Own laptops (Claude Code, git) --SSH+tmux--> INTEL LAPTOP = only runtime
 Inspection cam ─────┐            ┌────────────────────────────────────────────────┐
 Top view (RealSense)─┼─ capture ─▶│ run.py state machine (CPU) on physicalai runtime │
 Wrist cam ───────────┘   (CPU)    │ IDLE→LOCATE→PICK→VERIFY_GRASP→INSPECT→DECIDE     │
                                   │  →[REINSPECT]→PLACE→LOG→next | HOME on any error │
                                   │ PICK: ACT (OV, GPU) · PLACE: SmolVLA (OV GPU→CPU→PT)│
                                   │ INSPECT: Anomalib (OV INT8, NPU) → DefectSignal  │
                                   │ DECIDE: rules.yaml → instruction string          │
                                   │ fallback/: scripted waypoints (same Mover API)   │
                                   │ robot/io.py ↔ SO-101 follower (USB serial)       │
                                   │ threads: reasoner (Nemotron VL, async) → narrator│
                                   │ (persona; ElevenLabs stream + cached clips)      │
                                   │ telemetry (queue→JSONL→Aiven Kafka→PostgreSQL)   │
                                   │ ui (OpenCV, keys S/P/E/Q, H = hat backup)        │
                                   └────────────────────────────────────────────────┘
Modal GPU: ACT and SmolVLA training (datasets via HF Hub) → checkpoints → OpenVINO export
```
Control and inference never touch the network. Reasoner, narration and telemetry are non-blocking and degrade to local templates, cached clips and a JSONL buffer when offline.
**Cameras (F13):** one capture thread per camera grabs each frame once and hands the same frame to the policy (top + wrist) and the inspector (inspection cam; second view = whichever shared camera sees the held brick, checked Sat 08:00). Which physical camera is the RealSense: confirm at the station.

### 7.2 Device map
| Workload | Device | Why | Fallback |
|---|---|---|---|
| Anomalib (PaDiM/EfficientAd, static 1×3×256×256, INT8_PTQ; PatchCore or per-colour PaDiM if the good bricks come in several colours) | **NPU** | Small convolutional net with static shapes; low power (F12 measures it); frees the GPU | GPU → CPU |
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
# narrator.say(event, text=None, persona=None, **kw) and telemetry.log(**row): non-blocking (Harry)
# narrator.trigger(kind) -> None  # kind: "obstacle" | "hat"; persona state machine CALM <-> COWBOY (Harry)
# reasoner.explain(signal: DefectSignal, crop, persona) -> None  # async; hands narrator a grounded line or nothing (Saliha)
# reasoner.hat_seen(top_frame) -> bool | None  # async, None = no answer in time (Saliha)
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
| F4 | Re-inspection chain: second shared-camera view → **re-grasp triggered by the anomaly score** (Intel's named idea; Nate's `reinspect` primitive puts the brick down and picks it again) → wrist roll ±90° if time → defective. Saliha owns the decision logic, Nate the motion | 2–4 | Saliha + Nate | 5 |
| F5 | Grasp check (gripper position) plus one retry | 1–2 | Nate | 5 |
| F6 | Mission-control window, keys S/P/E/Q | 2–3 | Harry | 1, 6 |
| F7 | **Live reasoning voice (ElevenLabs):** two voices, **calm** (cool, collected) and **cowboy** (Voice Library western voice or Voice Design). Live lines through `eleven_flash_v2_5` streaming with a 1.5 s timeout; exclamations and fallback lines pre-generated (expressive model with emotion tags) and cached as WAV. A queue that drops stale lines, so speech never lags the arm | 2–3 | Harry | ElevenLabs, innovation |
| F8 | Telemetry writer: `queue.Queue` → `runs/events.jsonl` → Aiven (F15); success-rate query | 1–2 | Harry | 5, Aiven |
| F9 | Brick localization and empty-zone stop (R12) | 1–2 | Harry | 5, 1 |
| F10 | Modal side track: reproducible `train/modal_train.py`, ACT + SmolVLA trained in parallel on Modal GPUs, GPU type, time and cost in the README. (Modal's page scores a live deployed app at 15% but doesn't require one: see F16.) | 0.5 | Nate | side track |
| F11 | **"How few demos are enough"** (Intel's insight): Modal fans out ACT runs on 18 / 36 / 54 episodes in parallel (`.map`), each exported and tried 5 times → success-vs-demos curve in the README. Also scores Modal "scale out" and dataset quality | 1 (mostly waiting) | Nate | Junction 20%, Modal |
| F12 | **Power, energy and thermal benchmark:** sample Intel RAPL package energy (`/sys/class/powercap/intel-rapl*`) and temperatures (`/sys/class/thermal`) around every benchmark run → mJ per inference per device, watts during the loop, max temperature over the 20 trials, throttling yes/no | 1–1.5 | Saliha | Junction 20%, crit. 4 |
| F13 | **Shared cameras** (Intel's idea): one grab per camera, the same frame goes to the policy and the inspector; saves a USB stream and latency | 0.5–1 | Harry | crit. 4, Junction 30% |
| F14 | **Shifted and cluttered bricks:** 5 trials from start positions not in the recordings, 3 trials with a 3-brick pile (F9 picks the most isolated brick first) | 0.5 | Nate + Harry | Junction 30%, crit. 5 |
| F15 | **Aiven streaming:** the telemetry thread produces every event to an **Aiven for Apache Kafka** topic `sortsense.events`. A consumer on the laptop (1) runs the **drift check** (mean score of recent perfect bricks creeping toward `t_low` → `sortsense.alerts` → "lighting changed, rebaseline", spoken in persona) and (2) writes rows to **Aiven PostgreSQL** (`events`, `inspections`, `benchmarks`, `models`) for the trial report. Never on the control path; JSONL buffer when offline. No Kafka on our plan → PostgreSQL `LISTEN/NOTIFY` does the same job | 2 | Harry (Saliha writes the drift rule) | Aiven 40% |
| F16 | ~~Live dashboard on Modal~~ **Dropped 00:55: no frontend.** | — | — | — |
| F17 | **Nemotron 3.5 Super VL, the reasoning brain** (`reasoner/`, NVIDIA Build API, OpenAI-compatible): (a) per brick, from the crop + heatmap + the `DefectSignal` numbers, write one short grounded line in the current persona ("Score 0.81, past my 0.55 line, marker streak top left, red bowl"), JSON out, checked against the label before it is spoken; (b) is the cowboy hat in the top view? (c) once, before the run: turn the kickoff / Challenge-Day rules text into a checked `rules.yaml`. Requests start while the arm moves, so the line is ready by PLACE. **Improving its output** (the NVIDIA write-up): JSON schema, numbers passed in so it can't invent them, a few examples per persona, a 20-frame eval set (label agreement, region correct, length, latency), one prompt revision measured against it. Template fallback when slow, rate-limited (~40 requests per minute) or offline | 3 | Saliha | NVIDIA, ElevenLabs, innovation |
| F18 | **Cowboy triggers + persona state machine:** obstacle = local RealSense depth in the workspace (taller than a brick or not brick-shaped; from F9), hat = F17(b) or the H key. CALM → COWBOY instantly with a cached "Holy smokes!"; back after the trigger has cleared and one brick is done, through one half-way line. Obstacles are skipped, never picked | 1.5 | Harry (Saliha: hat check) | ElevenLabs, crit. 5 |

### 8a. Stretch (only after the gates pass; each ≤ ~2 h)
| # | Stretch | Hours | Owner |
|---|---|---|---|
| S1 | Wrist roll ±90° as the last re-inspection step (F4) | 1 | Nate + Saliha |
| S2 | More persona moments: "grumpy" after three defects in a row; a victory line at the run summary | 1 | Harry |
| S3 | Placement check: top camera confirms the brick landed in the bowl, said aloud if not | 1–1.5 | Harry |
| S4 | Local on-device TTS on OpenVINO (for example Kokoro-82M) as the offline voice fallback: more Intel story | 2 | Saliha |
| S5 | Workspace guard: an Anomalib model of the empty table flags any foreign object (a second obstacle detector) | 1.5 | Saliha |

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
| Nemotron slow, rate-limited or offline | Template lines from `DefectSignal`; one key per teammate; never awaited by the loop |
| ElevenLabs slow or offline | Cached WAV clips per persona; stale lines dropped |
| Aiven or Kafka unreachable | JSONL buffer, sync later; the loop never waits |
| The gag eats robot time | Personality work happens off the robot slots; it is cut before any gate slips |
| Our own earlier mistake: assuming two working arms | Only the follower moves; the leader is for teleop |
**Safety:** E = torque off; joint limits and a speed cap; one person always watches the arm; follow the printed guidelines.

## 10. Plan and hardware slots

### Block A: tonight 00:45–02:30 (no hardware). Each person works only in their own folders.
| Saliha | Nate | Harry |
|---|---|---|
| Full perception pipeline on stand-in images (own webcam plus any identical small objects): capture, train, thresholds, OV export, inspector, rebaseline, benchmark harness (CPU); if time, one Nemotron test call with an image | Modal training script smoke-tested on a public SO-100/101 dataset; **SmolVLA/ACT → OpenVINO export test** on a public checkpoint; `robot/io.py` with a mock; recording protocol | Repo, `interfaces.py` (01:00 freeze), `run.py` with mocks, mission control, scripted-fallback skeleton, Aiven (Kafka topic or PostgreSQL) and ElevenLabs set up (pick the calm and cowboy voices, cache the exclamations), README and diagram skeleton |

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
| 15:30–16:00 | **Nate** | Benchmark Anomalib (CPU/GPU/NPU) | Grasp retry test | Narration, persona and Aiven stream live |
| 16:00–17:00 | **Nate** | Benchmark (cont.); uncertainty band live | **Gate 17:00:** ACT export, 10 trials (≥6/10 keep) | Narration/telemetry; README |
| 17:00–19:00 | **Nate** | F4 logic offline (RealSense view); **Nemotron reasoner** (F17) | **Gate 19:00:** SmolVLA export, 10 trials (≥6/10 keep; ≥4/10 still keep unless scripted placement is clearly better; else scripted place) | Integrate the policies swap |
| 19:00–21:00 | **Nate + Harry** (+ Saliha at 20:30 for the F4 live test) | Async, PrePostProcessor, cache; F4 live test 20:30 | Integrate learned policies | Integrate |
| 21:00–22:00 | **Saliha** (GPU) | Benchmark ACT/SmolVLA, cycle time before and after | — | Diagram, README |
| 22:00–23:00 | all | Fix; Nemotron eval set + one prompt revision | Fix | Fix; persona triggers on the real table |
| **23:00** | **FEATURE FREEZE** | | | |
| 23:00–01:00 | Nate + Harry | Sleep 00:00–05:00 | 20 logged trials, then sleep 01:00–06:00 | Film good runs, then sleep 01:00–06:00 |
| 06:00–09:00 | all | `make rebaseline` on demo table; numbers into README | Final runs; recalibrate | Edit video; submission text |
| **09:00** | **SUBMIT** | | | |
After 09:00: rehearse 3–4 times, including the e-stop drill and the uncertain-brick moment.

### Conflict rules
- Folder ownership:
  - Saliha: `perception/`, `bench/`, `reasoner/`
  - Nate: `robot/`, `policies/`, `train/`
  - Harry: `run.py`, `common/`, `fallback/`, `ui/`, `narrator/`, `telemetry/`, `config/`, docs
- Commit only in your own folders; `git pull --rebase` before pushing; never force-push.
- Contract changes go through `progress.md` first.
- **`progress.md`** (on `main`) gets one entry per finished thing: who, what, when (date and time), and whether it conflicts with anyone. Format at the top of the file.

## 11. Demo script (2 minutes)
- 0:00 The problem (factory inspection by eye).
- 0:10 Press S: perfect brick → blue bowl, the calm voice explains why with the score.
- 0:30 Defective brick: heatmap → red bowl, explained.
- 0:45 Planted borderline brick: "taking a second look" → re-grasp → decision.
- 1:00 Drop the cowboy hat in view (or an obstacle): "Holy smokes!", cowboy voice sorts the next brick, then cools down.
- 1:20 Architecture and device map (NPU / GPU / CPU, Nemotron off the control path).
- 1:35 Benchmark before → after, energy per brick.
- 1:50 Reliability from the Aiven stream.
- 2:00 End.

Keep the backup video on a second screen.

## 12. Submission checklist (09:00 Sunday)
- [ ] Public MIT repo, with every reused repo credited
- [ ] README: how to run, architecture, device rationale, benchmark table, trial results
- [ ] Video ≤ 2 minutes
- [ ] Junction Platform: Intel challenge, plus ElevenLabs (MLH), Aiven, NVIDIA (text: model, what it does, why it matters, how we improved its outputs) and Modal if allowed
- [ ] PyTorch checkpoints backed up; OV models or HF links

## 13. Open questions for mentors (Saturday 08:00–09:00)
1. Is 11:50 our demo slot? What exactly is the **Challenge-Day task**, and does it use new bricks or positions?
2. Modal access, GPU hours, and whether Studio connects to it.
3. Is reuse of open-source code confirmed?
4. Is there a stack-verification script for Ubuntu 26.04 / Anomalib 2.7.0? Can policies export to the NPU?
5. Can we enter ElevenLabs (MLH), Aiven, NVIDIA and Modal alongside Intel? Is a soft cowboy hat in the workspace OK under the safety rules?
6. Which rubric scores us: the kickoff slides (25/20/20/20/10/5) or the Junction page (30/30/20/20)? How do you want power and thermal measured on the laptop? What should we use from the Robotics AI Suite?
7. Which station camera is the RealSense: the top view or the inspection camera? Do the good Duplo bricks come in one colour or several?

## 14. References
- Physical AI Studio: https://github.com/open-edge-platform/physical-ai-studio
- OpenVINO Physical AI runtime: https://github.com/openvinotoolkit/physicalai · https://docs.openvino.ai/2026/physical-ai.html
- LeRobot: https://github.com/huggingface/lerobot · https://huggingface.co/docs/lerobot/so101 · https://huggingface.co/docs/lerobot/smolvla
- Anomalib: https://github.com/open-edge-platform/anomalib · https://anomalib.readthedocs.io/en/latest/markdown/guides/reference/deploy/
- Prior attempt (ideas only): https://github.com/ohong/intel-robotics
- NPU limits: https://docs.openvino.ai/2025/openvino-workflow/running-inference/inference-devices-and-modes/npu-device.html
- ElevenLabs: https://elevenlabs.io/docs · MLH code: https://mlh.link/junction-26
- NVIDIA Build (Nemotron, OpenAI-compatible): https://integrate.api.nvidia.com/v1 · https://build.nvidia.com
- Aiven for Apache Kafka: https://aiven.io/docs/products/kafka · Aiven PostgreSQL: https://aiven.io/docs/products/postgresql
