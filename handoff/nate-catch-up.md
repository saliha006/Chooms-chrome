# Nate catch-up (read this first, then your brief)

> **07:10 update:** a research pass (PRD v2.5) put a new ordered block **N1–N9** at the top of your brief's ▶ Current tasks. It supersedes §3 below: start with **N1, the red-lego smoke test** (`eruedas/so101_3cams_pickplace-red-lego_real`, exact commands in the brief), then early exit + abort, the gripper band and the wrist roll-back bug. RL was researched and rejected (decisions.md D1).

Written 2026-11-14 ~05:50 Espoo by Saliha's agent, which wrote the first version of your hardware-free Block A code at
Saliha's request (Saliha has the most Claude usage). **You have since reworked `train/` (D20, `main` @ `c65c275`); your
version is the one in force.** Everything below is on `main` / `robotics-policies-nate` and the `context` branch.
Your agent: read this, then `builder-briefs/builder-brief-nate.md` (▶ Current tasks + §4 Done log), then the
`progress.md` Open board rows To @nate. Times are **Espoo local (UTC+2)**.

## 1. What is already done for you (review it, it is yours now)
| Path | What it does | Tests |
|---|---|---|
| `robot/io.py` | `connect / observe / act / move_to / torque_off / disconnect` on Intel's **physicalai SO-101 driver** (degrees, follower only). Every command is clipped to the driver's joint limits and a **5°/step speed cap at 30 Hz**. `connect(mock=True)` gives `MockRobot` | `robot/tests/test_io.py` |
| `policies/episode.py` | Runs an exported policy (`physicalai.inference.InferenceModel`, OpenVINO backend) step by step through `robot.io`; LeRobot key names `observation.state`, `observation.images.<cam>`, `task` | via mover tests |
| `policies/mover.py` | `LearnedMover`: ACT `pick_and_present`, SmolVLA `place(instruction)`, `reinspect(0)` = put down at `pick_drop` + pick again, `reinspect(±90)` = wrist roll (agreed by all three 04:16), `gripper_empty`, `home`, `estop`. Passes `isinstance(..., common.interfaces.Mover)` | `policies/tests/test_mover.py` |
| `train/commands.py` + `train/modal_train.py` | **Your D20 rework:** ACT via Studio's `physicalai fit`, SmolVLA via `lerobot-train` 0.7.0, each in its own Modal image on an A100; `--episodes N`; `--sweep`; logs to `train/runs.md`; needs the Modal secret `huggingface` | `train/tests/test_commands.py` |
| `train/RECORDING.md`, `train/rejected.md`, `train/runs.md` | Recording protocol, rejected-episode log, run log | — |

## 2. Set up your machine (once)
```bash
git clone https://github.com/saliha006/Chooms-chrome && cd Chooms-chrome
git config user.email <your GitHub email> && git config team.builder nate
git fetch origin context && git archive origin/context | tar -x && git rev-parse origin/context > .git/context-synced
mkdir -p .claude/skills && cp -r skills/* .claude/skills/ && rm -rf skills      # no-slop + debug skills
git switch robotics-policies-nate && git pull
# Python 3.12 (uv: https://docs.astral.sh/uv/)
uv venv --python 3.12 .venv
uv pip install --python .venv -r train/requirements.txt                 # modal==1.6.4 + pytest
uv pip install --python .venv numpy pyyaml opencv-python-headless       # for robot/ and policies/ tests
.venv/bin/python -m pytest robot policies train -q                     # expect all green (Windows: .venv/Scripts/python)
```
- Windows only: `set PYTHONUTF8=1` (torch's ONNX exporter prints emoji).
- `.env` at the repo root (never committed, never pasted in chat): `HF_TOKEN=...` for your private datasets.

## 3. Your next steps, in order
1. **Modal** (you already ran a first job): keep the secret `huggingface` (HF_TOKEN) in Modal; redeem the Junction $100 credits.
2. **A2 smoke runs** to green: `modal run train/modal_train.py --dataset lerobot/svla_so100_pickplace --steps 200`, the same with
   `--policy smolvla`, then `--steps 100 --sweep` (A8: three runs in parallel). Fill **Cost** in `train/runs.md`.
3. **A3 export test** on those checkpoints: `modal volume get sortsense-runs <job_name> ./checkpoints/`, back them up,
   then export to OpenVINO and run `InferenceModel(..., device="CPU")` on a dummy observation **with a task string**.
   Record which known bug you hit (#1384 key map, #1414 NaN on CPU → `INFERENCE_PRECISION_HINT=f32`, #1169 `KeyError: 'task'`).
   See §5 for what Saliha's agent already learned about export.
4. ~~Hold-back decision~~ done: rounds over all nine positions, F14 on off-grid spots (your 8bc38a6).
5. Saturday 08:00 on the Intel laptop: Studio install (`docker --profile xpu` or `uv run --extra xpu physicalai-studio serve`),
   `lerobot-find-port`, calibrate leader + follower, save the calibration JSON (pass it to `robot.io.connect(port, calibration)`).

## 4. Open decisions (yours; don't let an agent pick them silently)
- ✅ Decided by you (D20): Studio's trainer for ACT, LeRobot for SmolVLA. Evidence that agrees: `physicalai-train` 0.3.0's
  LeRobot wrapper exports **torch only** (`NotImplementedError` for OpenVINO), while the native `physicalai.policies.act.ACT`
  supports OpenVINO and ONNX, and the native `physicalai.policies.smolvla.SmolVLA` lists torch + OpenVINO.
- Open: SmolVLA's route to OpenVINO (A3) given LeRobot-trained weights; fallback is SmolVLA in PyTorch (PRD 7.2).
- TUNE on the arm, with someone watching: `robot/io.py MAX_STEP_DEG`, `policies/mover.py POSE_TOLERANCE_DEG`,
  `GRIPPER_EMPTY_BELOW`, `GRIPPER_OPEN`. Observation key names in `policies/episode.py` vs the export's `manifest`.

## 5. Gotchas already found
- **Policy training runs on Modal GPUs, never on a laptop.** The Intel laptop runs inference, exports and benchmarks.
- A research pass (4 agents, Saliha's request) is reviewing robot learning incl. RL; its in-scope results land in your brief.
- `physicalai` (runtime, 0.4.0) has the SO-101 driver (`physicalai.robot.so101.SO101`, plugin `physicalai-so101-plugin`) and
  `InferenceModel`; **export lives in `physicalai-train`** (`policy.export(path, backend="openvino")`), not in the runtime.
- LeRobot 0.7's ACT default lr is already 1e-5 (the #998 fix); SmolVLA's is 1e-4.
- Back up checkpoints **before** any export (Studio PR #1403 can delete them).
- The leader arm is teleop only; code never drives it.

## 6. Workflow rules (CLAUDE.md, short)
Your branch only (`robotics-policies-nate`); your folders only (`robot/`, `policies/`, `train/`). Per feature: code → `no-slop`
→ tests → push → merge to `main` if green → `progress.md` entry (with `[conflicts: ...]`) + mark the brief task done.
`debug` skill on every error. Never commit `.env`, datasets or checkpoints. No AI co-author trailers on commits.
