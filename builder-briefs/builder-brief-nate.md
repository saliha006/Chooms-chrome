> **Status, 2026-11-14 01:30.** Branch renamed by discipline; `decisions.md` is the team's pitch record (agents update it as you build). PRD v2.3: Intel task first (accurate, smooth, quick), personality layer on top; Modal = training + logs only, no frontend. Nothing built yet. Block A (Modal + export test) starts 00:45. Docs on `context`, board on `main`.

# Nate: robotics and robot learning (robot I/O, imitation-learning policies, Modal training)
**GitHub:** `{{github}}` · **Branch:** `robotics-policies-nate` (one branch for all your work) · **Tool:** {{Claude Code / Codex}} · **Brief last updated:** 2026-11-14 01:30 by saliha
**Spec:** `prd.md` (on `context`). A bare § means the PRD; CLAUDE.md and this brief's own sections are always named.

## 0. How the agent reads this brief (every task)
1. `CLAUDE.md` is already loaded (don't re-read it); read this brief once. Follow both.
2. Read `prd.md` sections 2, 4, 7 and 10 first. **Work `▶ Current tasks` top to bottom** (Block A, then Block B).
3. **Want a different route, more features or another decision in your area? Go ahead.** Your Claude always asks first: "Have you told the team? Who agreed?" (CLAUDE.md §2c). Changes to another builder's path or a shared contract wait for that owner's yes.
4. Before starting, read `progress.md`'s 📌 Open board (CLAUDE.md §2b). Rows To @nate come first: tell the user, then resolve or schedule them.
5. Ship each task with the CLAUDE.md §7 sequence (code → `no-slop` → test → push → merge if safe), then log it (CLAUDE.md §2b). Use the `debug` skill on every issue.
6. Times are on the plan clock of PRD §10.

**Task tags:** `[⚠ touches @name: what]` = changes someone else's area or a shared contract; get that owner's yes before merging (§2c). `[⏸ waits on @name: what]` = blocked until they deliver (a 📨 row on the Open board). `[🟠 your call]` = a design decision for the user (CLAUDE.md §1).

---

## 1. Ownership
You own **R1 (Studio), R4, R6, R10, R15, R20 (data quality), F5 and F11**, and you co-own R5, R18, F4 (re-grasp motion) and F14: criterion 3 (20) and most of criterion 5 (10).

**Owns:**
- `robot/`: `io.py` (connect, observe, act, torque_off) + `MockRobot`
- `policies/`: `act.py`, `smolvla.py` (implement `Mover`)
- `train/`: `modal_train.py`, `RECORDING.md`, `runs.md`

**Does NOT touch:**
| Area / path | Owner | Why it's theirs |
|---|---|---|
| `perception/`, `bench/` | @saliha | Anomalib, OpenVINO, benchmarks |
| `run.py`, `common/` (incl. `interfaces.py`), `fallback/`, `ui/`, `narrator/`, `telemetry/`, `config/`, `README.md`, `docs/` | @harry | integration, contracts file, demo, side tracks |

**Shared** (flag in `progress.md` ⚠️ Conflicts): `config/cameras.yaml` (Harry's file; same paths for recording and runtime).

## 2. Contract & Guardrails
**Contracts:** `robot/io.py` (connect, observe, act, torque_off), shared with Harry's fallback; `Mover` (PRD 7.3) for the learned policies.

**Guardrails:**
- ⛔ **Off-plan → CLAUDE.md §2c.**
- The leader is teleop only. Never drive it.
- Back up checkpoints before any export.
- Never commit datasets, checkpoints or tokens.

---

## 3. ▶ Current tasks (2026-11-14 00:55)
🆕 **Vision (PRD v2.3 §1a):** (1) the Intel task done accurately, smoothly and in reasonable time, always first; (2) the robot explains its reasoning out loud, live, in a calm voice; (3) an obstacle or the cowboy hat flips it into a cowboy persona ("Holy smokes!") until the moment passes. Personality never slows the arm or costs a gate. No frontend, ever.
🆕 **For you:** smooth motion matters to the judges (speed cap, temporal ensembling); obstacles are **skipped, never picked** (Harry's F18 tells `run.py`); personality work never takes a robot slot.
🆕 **What changed (PRD v2.2):** the Junction page scores **dataset and pipeline quality (20%)**: clean teleop data, fine-tuning in Studio, "how few demonstrations are enough"; and **task success (30%)** includes **shifted or cluttered bricks**. Objects are **Duplo** (bigger, easier grasp). Cameras: top view + inspection + wrist. Modal's page gives every participant $100 credits and scores scale-out.
*Status: ⬜ not started · 🟡 in progress · ⏸ blocked · ✅ done*

### BLOCK A: tonight 00:45–02:30 (own laptop, no hardware)
Goal: remove the two biggest unknowns before the robot exists: **Modal training** and **SmolVLA/ACT → OpenVINO export**.

| # | Status | Task | Est. | Done when |
|---|---|---|---|---|
| A1 | ⬜ | Get Modal access (ask in the Intel Discord, or use a personal account for tonight's test) plus an HF token. `train/modal_train.py`: image with `lerobot`, HF secret, Volume for outputs, args `--policy act\|smolvla --dataset <hf_id> --steps --lr`, A100 | 30 min | Script runs |
| A2 | ⬜ | Smoke-train on a public dataset (e.g. `lerobot/svla_so100_pickplace`): ACT 200 steps (`optimizer_lr=1e-5`), SmolVLA 200 steps from `lerobot/smolvla_base` | 20 min (runs alone) | Checkpoints in the Volume |
| A3 | ⬜ | **Export test** on your laptop: `pip install physicalai` (and/or Studio); export the smoke checkpoints with `backend="openvino"`; `InferenceModel(..., device="CPU")` on a dummy observation **with a task string**. Record which of the known bugs (#1384, #1414, #1169) you hit and the workaround. | 30 min | OV inference returns an action |
| A4 | ⬜ | `robot/io.py` on the LeRobot SO-101 API plus `MockRobot` (same methods); `policies/act.py`, `policies/smolvla.py` implementing `Mover` against the mock | 20 min | `run.py --mock` works with your policies |
| A4b 🆕 | ⬜ | Agree with Saliha and Harry **before the 01:00 freeze** what `reinspect` means now that it also covers the **re-grasp** (Intel's "anomaly score triggers a re-grasp"), e.g. `reinspect(angle_deg)` with `0` = put down and pick again. Post it in `progress.md` | 5 min | Agreed |
| A5 | ⬜ | `train/RECORDING.md` (page 1 of the plan):<br>• 10×10 cm pick zone, 9 start positions × 6 = 54 ACT episodes, each ending at the marked inspection pose<br>• SmolVLA: 25 + 25, starting at the inspection pose<br>• Task strings exactly `"place the brick in the red bowl"` / `"…blue bowl"`<br>• Episode about 12 s, reset about 10 s<br>• HF repo names<br>🆕 • Hold back 2 of the 9 start positions plus a few off-grid spots for the F14 test (never recorded)<br>🆕 • Reject and log bad episodes (dropped brick, collision, hesitation) in `train/rejected.md`; a short dataset card on the HF Hub (dataset quality 20%) | 10 min | Shared |
| A6 | ⬜ | Commit; status in `progress.md` | 5 min | — |
| A7 | ⬜ | Modal side track (F10): log GPU type, wall time and cost for every run into `train/runs.md` (it goes in the README). No frontend. 🆕 Modal stays **training + logs only**; if its prize ever needs a web app, we drop Modal, not add one | 5 min | File exists |
| A8 🆕 | ⬜ | Make `modal_train.py` take `--episodes N` (first N episodes) and add a `sweep` entrypoint that `.map`s ACT over `[18, 36, 54]` in parallel (F11). Smoke it on the public dataset with 2 small values | 10 min | Two runs finish in parallel |

### BLOCK B: Saturday 08:00 → Sunday 09:00 (follow the slot table in PRD 10)
| Time | Status | Task | Done when |
|---|---|---|---|
| 08:00–09:00 | ⬜ | Install Studio on the Intel laptop (Docker `--profile xpu` or `uv run --extra xpu physicalai-studio serve`); `lerobot-find-port`; calibrate leader and follower; save calibration; read the safety guidelines | Smooth teleop |
| 09:00–09:30 (robot) | ⬜ | 5 test episodes in Studio → push → Modal 200-step run with **your** data shape | Checkpoint back |
| 10:30–12:30 (robot) | ⬜ | Record **54 ACT** episodes (Harry resets) | Dataset on the HF Hub |
| 12:30 | ⬜ | **Launch ACT** on Modal (lr 1e-5; about 2–3 h). 🆕 Launch the **F11 sweep** (18 / 36 / 54 episodes) in parallel at the same time; the 54 run is the main policy | Running |
| 12:30–14:00 (robot) | ⬜ | Record **50 SmolVLA** episodes | Dataset pushed |
| 14:00 | ⬜ | **Launch SmolVLA** (10k steps, about 2–2.5 h). **Back up checkpoints before any export.** | Running |
| 14:00–16:00 | ⬜ | F5 grasp check (gripper position after close below the empty threshold → retry once); `reinspect(±90°)` wrist-roll primitive; test both in the 15:30 robot slot | Works 3 times in a row |
| **17:00 gate** | ⬜ | ACT → OpenVINO (GPU) → 10 trials. ≥6/10 → keep; else scripted pick (no time for a retrain). 🆕 Also 5 tries each of the 18- and 36-episode checkpoints → success-vs-demos curve (F11) | Logged in `progress.md` |
| **19:00 gate** | ⬜ | SmolVLA → OV on GPU → CPU f32 → PyTorch; 10 trials. ≥6/10 correct bowl → keep. Below that, **still use SmolVLA if it is ≥4/10 and the scripted placement is not clearly better** (criterion 3 rewards the real VLA); otherwise scripted placement chosen by the same instruction | Logged |
| 19:00–21:00 | ⬜ | Integrate the policies with Harry through `Mover` (`--scripted pick,place` stays available) | Both modes run |
| 21:00–22:00 | ⬜ | Hand the IR files to Saliha for benchmarking; don't use the GPU | — |
| 23:00–01:00 | ⬜ | **Freeze**; 20 logged trials with Harry; 🆕 plus F14: 5 trials from held-back start positions and 3 with a 3-brick pile; sleep 01:00–06:00 | Success rates in Aiven |
| 06:00–09:00 | ⬜ | Check the home pose and recalibrate on the demo table; final runs | Ready |

**Seams** (the same note is in the other two briefs):
- @harry: `fallback/scripted.py` replays waypoints through your `robot/io.py`; push `MockRobot` around 02:00 so Harry's stub can go. `run.py` calls your policies through `Mover`; `--scripted pick,place` must keep working.
- @saliha: F4 re-grasp (🆕) and wrist roll call your `Mover.reinspect(angle_deg)`; your ACT/SmolVLA OpenVINO IR files go to Saliha for the 21:00 GPU-slot benchmark.

## 4. Done log (newest first)
- *(empty)*

## 5. Working-style notes for the agent
- When you decide or finish something that changes the design, add or update its entry in `decisions.md` the same turn (CLAUDE.md §4a): facts and measured numbers only.
- Options + a recommendation, no teaching notes unless asked. Flag scope creep at once. Spell out abbreviations once.
- Hackathon pace: the smallest thing that passes its *Done when*.

## 6. Open blanks (fill when the chat or repo answers them, CLAUDE.md 🔁)
- GitHub handle and agent tool: {{github}} · {{tool}}
- Modal access (Intel-provided or personal) and GPU hours: {{modal}}
- HF dataset repo names: {{hf repos}}
- Can ACT or SmolVLA run on the NPU? (Intel workshop) {{npu policies}}

## 6a. Reference
### Pitfalls
- ACT outputs the same pose whatever the input at lr 1e-4 (#998). Use **1e-5**.
- SmolVLA export bugs: #1384 (key map), PR #1403 (crash could delete the checkpoint), #1414 (NaN on CPU, so set `INFERENCE_PRECISION_HINT=f32`), #1169 (`KeyError: 'task'`, so pass a task string), physicalai #174 (GPU build failure).
- Keep starts tight (about 10 cm). A 30 cm spread "grasped at air". 25 episodes are too few for SmolVLA.
- ACT runs chunks open-loop, so use temporal ensembling or fewer `n_action_steps` if it overshoots.
- Cameras: use the `/dev/v4l/by-id` paths in `config/cameras.yaml`, the same for recording and runtime.
- The leader is teleop only. Never drive it.

### Links
- Studio: https://github.com/open-edge-platform/physical-ai-studio (issues #998, #1384, #1169; PRs #1403, #1414)
- Runtime: https://github.com/openvinotoolkit/physicalai · https://docs.openvino.ai/2026/physical-ai.html
- LeRobot: https://github.com/huggingface/lerobot · https://huggingface.co/docs/lerobot/so101 · https://huggingface.co/docs/lerobot/smolvla
- Base model: https://huggingface.co/lerobot/smolvla_base · public smoke dataset: https://huggingface.co/datasets/lerobot/svla_so100_pickplace
- SO-101 SmolVLA bowl references (config only): https://huggingface.co/shinba/smolvla_so101_red_cube_bowl_v2 · https://huggingface.co/jiajinda/so101-04-smolvla-red-block-to-target-v234
- Lessons: https://ggando.com/blog/smolvla-so101/ · training times: https://wiki.seeedstudio.com/lerobot_so100m/

---
── Archived (superseded — do NOT action) ──
- *(none yet)*
