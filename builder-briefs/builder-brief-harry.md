> **Status, 2026-11-14 00:10.** Repo exists (`saliha006/Chooms-chrome`; `main` has `README.md` + `progress.md`). The rest of Block A starts 00:45. Docs on `context`.

# Harry: integration, demo and side tracks (ElevenLabs, Aiven) + submission
**GitHub:** `{{github}}` · **Branch:** `integration-harry` · **Tool:** {{Claude Code / Codex}} · **Brief last updated:** 2026-11-14 00:10 by saliha
**Spec:** `prd.md` (on `context`). A bare § means the PRD; CLAUDE.md and this brief's own sections are always named.

## 0. How the agent reads this brief (every task)
1. `CLAUDE.md` is already loaded (don't re-read it); read this brief once. Follow both.
2. Read `prd.md` sections 2, 6, 7, 9 and 10 first. **Work `▶ Current tasks` top to bottom** (Block A, then Block B).
3. **Want a different route, more features or another decision in your area? Go ahead.** Your Claude always asks first: "Have you told the team? Who agreed?" (CLAUDE.md §2c). Changes to another builder's path or a shared contract wait for that owner's yes.
4. Before starting, read `progress.md`'s 📌 Open board (CLAUDE.md §2b). Rows To @harry come first: tell the user, then resolve or schedule them.
5. Ship each task with the CLAUDE.md §7 sequence (code → `no-slop` → test → push → merge if safe), then log it (CLAUDE.md §2b). Use the `debug` skill on every issue.
6. Times are on the plan clock of PRD §10.

**Task tags:** `[⚠ touches @name: what]` = changes someone else's area or a shared contract; get that owner's yes before merging (§2c). `[⏸ waits on @name: what]` = blocked until they deliver (a 📨 row on the Open board). `[🟠 your call]` = a design decision for the user (CLAUDE.md §1).

---

## 1. Ownership
You own **R5 (with Nate), R11, R12, R14, R17, F6, F7, F8, F9**, the scripted fallback and the submission. Criterion 1 (25 points) is your loop.

**Owns:**
- `run.py`, `common/` (you own `common/interfaces.py`; freeze it at **01:00**), `fallback/`, `ui/`, `narrator/`, `telemetry/`, `config/`
- `README.md`, `docs/`, `Makefile`, the video and the Junction Platform submission

**Does NOT touch:**
| Area / path | Owner | Why it's theirs |
|---|---|---|
| `perception/`, `bench/` | @saliha | Anomalib, OpenVINO, benchmarks |
| `robot/`, `policies/`, `train/` | @nate | robot I/O, ACT/SmolVLA, Modal training |

Exception: Saliha adds one import line to `run.py` (agreed in `progress.md`, Saliha's Block B 13:00).
**Shared** (flag in `progress.md` ⚠️ Conflicts): `Makefile`, `config/cameras.yaml` (Nate records with the same paths).

## 2. Contract & Guardrails
**Contracts:** `common/interfaces.py` copied from PRD 7.3, frozen at 01:00. `narrator.say(event, **kw)` and `telemetry.log(**row)` are non-blocking.

**Guardrails:**
- ⛔ **Off-plan → CLAUDE.md §2c.**
- Never block the control loop on the network, TTS or the database.
- `--scripted` always keeps working, even after the learned policies swap in.
- Never commit keys (ElevenLabs, Aiven).

---

## 3. ▶ Current tasks (2026-11-14 00:10)
*Status: ⬜ not started · 🟡 in progress · ⏸ blocked · ✅ done*

### BLOCK A: tonight 00:45–02:30 (own laptop, no hardware)
Goal: the whole application runs in `--mock` mode, so on Saturday only the real parts plug in.

| # | Status | Task | Est. | Done when |
|---|---|---|---|---|
| A1 | 🟡 | GitHub repo (MIT), folders per PRD 10, `progress.md`, `Makefile` (`mock`, `run`, `rebaseline` → `python -m perception.rebaseline`), `common/interfaces.py` copied from PRD 7.3; tell the team "frozen" at 01:00. *(2026-11-14 00:10: repo and `progress.md` already exist; MIT licence, folders, `Makefile`, `interfaces.py` still to do.)* | 15 min | Others can pull |
| A2 | ⬜ | `config/{cameras,rules,robot}.yaml` (camera paths as placeholders); `MockCamera` (folder of images), `MockInspector`, `MockMover` | 15 min | — |
| A3 | ⬜ | `run.py` state machine `IDLE→LOCATE→PICK→VERIFY_GRASP→INSPECT→DECIDE→[REINSPECT]→PLACE→LOG→next`; every exception → `HOME` plus a spoken message; flags `--mock`, `--scripted pick,place`. Build it on the `physicalai` runtime pieces (`InferenceModel`, `RobotRuntime`) where they fit (R5). | 30 min | Mock run sorts 5 fake bricks |
| A4 | ⬜ | `ui/mission_control.py`: one OpenCV window (feed, heatmap overlay, label and score, state, per-stage latency, bricks done); keys S/P/E/Q on the control thread | 20 min | Readable at 2 m |
| A5 | ⬜ | **Aiven:** free-tier PostgreSQL; table `events` (PRD 7.3); `telemetry/writer.py`: `queue.Queue` → `runs/events.jsonl` → batch insert; offline = JSONL only, sync later; `telemetry/report.sql` (success rate, latency per stage and device) | 20 min | Rows in Aiven from a mock run |
| A6 | ⬜ | **ElevenLabs:** API key; pick 2 voices (cheerful = perfect, gloomy = defective); `narrator/cache.py` pre-generates about 12 template phrases with `eleven_flash_v2_5` → WAV; `narrator/say.py` plays on a thread; brick IDs and scores come from short cached number clips or a live call with a 1.5 s timeout, falling back to the generic phrase | 20 min | Narration never blocks a state transition |
| A7 | ⬜ | `fallback/scripted.py` skeleton: replays named joint waypoints from `config/waypoints.yaml` via Nate's `robot/io.py` (use his `MockRobot` once pushed around 02:00; until then a local stub with the same 4 methods) `[⏸ waits on @nate: MockRobot]` | 10 min | Works against the mock |
| A8 | ⬜ | README skeleton and architecture diagram (from PRD 7.1) | 10 min | Committed |

### BLOCK B: Saturday 08:00 → Sunday 09:00 (follow the slot table in PRD 10)
| Time | Status | Task | Done when |
|---|---|---|---|
| 08:00–09:00 | ⬜ | Mount the cameras and lamp, tape the pick zone (10×10 cm), inspection mark and bowls; `ls /dev/v4l/by-id/` → `cameras.yaml`; RealSense via `pyrealsense2`; SSH plus tmux set up for everyone | All 3 streams open by path |
| 09:30–10:00 (robot) | ⬜ | Teach waypoints by hand-guiding: pick spot, inspection pose, red bowl, blue bowl, home | Scripted sort works |
| 10:00–10:30 | ⬜ | Hold the inspection pose for Saliha's capture | — |
| 10:30–14:00 | ⬜ | Resets for Nate's recordings; in between, **F9 localization**: colour blob in the pick zone (overhead webcam) plus RealSense depth → brick present and position; stop when empty | Position logged |
| **15:30 gate (robot)** | ⬜ | With Saliha: **scripted full loop with real Anomalib, 5 bricks, no human** | Pass; film it as the backup video v1 |
| 15:30–19:00 | ⬜ | Mission control on the real feed; live narration and telemetry; tune the spoken lines | Live |
| 19:00–21:00 (robot) | ⬜ | Swap in Nate's policies behind `Mover`; keep `--scripted` working | Both modes |
| 21:00–23:00 | ⬜ | Architecture slide, README (run steps, device rationale, benchmark placeholder for Saliha, credits), submission text draft | Drafts ready |
| 23:00–01:00 | ⬜ | **Freeze**; 20 logged trials with Nate; film the best runs; sleep 01:00–06:00 | Trial table from `report.sql` |
| 06:00–09:00 | ⬜ | Edit the 2-minute video; finish the README; Junction Platform submission (Intel, plus ElevenLabs and Aiven if allowed) **by 09:00** | Submitted |
| 09:00 → demo | ⬜ | Lead rehearsals: the script in PRD 11, the e-stop drill, the backup video on a second screen | — |

**Seams** (the same note is in the other two briefs):
- @saliha: `run.py` calls `Inspector.inspect(frame, view, brick_id)` → `DefectSignal`; `label` → instruction via `config/rules.yaml` (F1); mission control draws `heatmap_path`, `bbox`, `score`; `make rebaseline` → `python -m perception.rebaseline`.
- @nate: `fallback/scripted.py` replays waypoints through Nate's `robot/io.py`; learned policies arrive through `Mover`; `--scripted pick,place` stays available.

## 4. Done log (newest first)
- *(empty)*

## 5. Working-style notes for the agent
- Options + a recommendation, no teaching notes unless asked. Flag scope creep at once. Spell out abbreviations once.
- Hackathon pace: the smallest thing that passes its *Done when*.

## 6. Open blanks (fill when the chat or repo answers them, CLAUDE.md 🔁)
- GitHub handle and agent tool: {{github}} · {{tool}}
- Camera by-id paths: {{paths}} · ElevenLabs voice IDs: {{voices}} · Aiven service name and env var: {{aiven}}

## 6a. Reference
### Narrator templates (deterministic; no LLM)
- `perfect`: "Looks perfect. Blue bowl."
- `defective`: "Defect near the {region}. Red bowl."
- `uncertain`: "Not sure about this one, taking a second look."
- `grasp_fail`: "Missed it, trying again."
- `help`: "I need a hand, going home."
- `empty`: "All done. {n} sorted."

### Remote setup
- **On the Intel laptop:** `sudo apt install openssh-server`, then `ssh-copy-id`. If the venue Wi-Fi blocks laptop-to-laptop traffic, use a phone hotspot or a cable.
- **Run Claude Code on the Intel laptop in `tmux`**, and give each person a named tmux window.
- **Studio UI:** forward it with `ssh -L`.
- **Mission control:** show it on the Intel laptop screen with `DISPLAY=:0`.

### Pitfalls
- Never block the control loop on the network, TTS or the database.
- Re-check camera paths after every replug; check the home pose before every run.
- Only one person drives the robot at a time; follow the slot table.

### Links
- Runtime (`RobotRuntime`, `RealSenseCamera`, `UVCCamera`): https://github.com/openvinotoolkit/physicalai
- LeRobot SO-101: https://huggingface.co/docs/lerobot/so101 · scripted references (read and reimplement; licences unclear): https://github.com/vi-vi-3482/so101-control · https://github.com/oliver-ng01/pick_and_place_SO-101
- Mission-control reference: https://github.com/ohong/intel-robotics
- ElevenLabs: https://elevenlabs.io/docs · Aiven pricing (free PostgreSQL): https://aiven.io/pricing

---
── Archived (superseded — do NOT action) ──
- *(none yet)*
