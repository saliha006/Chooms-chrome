> **Status, 2026-11-14 01:30.** Branch renamed by discipline; `decisions.md` is the team's pitch record (agents update it as you build). PRD v2.3: you own the personality layer: live reasoning voice and the cowboy switch (ElevenLabs), plus Aiven streaming. F16 dashboard dropped: no frontend. Repo exists (`saliha006/Chooms-chrome`; `main` has `README.md` + `progress.md`). The rest of Block A starts 00:45. Docs on `context`.

# Harry: systems and integration (orchestration, ElevenLabs voice, Aiven streaming, demo) + submission
**GitHub:** `Harryt3nn` · **Branch:** `systems-voice-harry` (one branch for all your work) · **Tool:** Claude Code · **Brief last updated:** 2026-11-14 07:10 by saliha
**Spec:** `prd.md` (on `context`). A bare § means the PRD; CLAUDE.md and this brief's own sections are always named.

## 0. How the agent reads this brief (every task)
1. `CLAUDE.md` is already loaded (don't re-read it); read this brief once. Follow both.
2. Read `prd.md` sections 2, 6, 7, 9 and 10 first. **Work `▶ Current tasks` top to bottom** (Block A, then Block B).
3. **Want a different route, more features or another decision in your area? Go ahead.** Your Claude always asks first: "Have you told the team? Who agreed?" (CLAUDE.md §2c). Changes to another builder's path or a shared contract wait for that owner's yes.
4. Before starting, read `progress.md`'s 📌 Open board (CLAUDE.md §2b). Rows To @harry come first: tell the user, then resolve or schedule them.
5. Ship each task with the CLAUDE.md §7 sequence (code → `no-slop` → test → push → merge if safe), then log it (CLAUDE.md §2b). Use the `debug` skill on every issue.
6. Times are **Espoo local (EET, UTC+2)**, the event's clock (PRD §0).

**Task tags:** `[⚠ touches @name: what]` = changes someone else's area or a shared contract; get that owner's yes before merging (§2c). `[⏸ waits on @name: what]` = blocked until they deliver (a 📨 row on the Open board). `[🟠 your call]` = a design decision for the user (CLAUDE.md §1).

---

## 1. Ownership
You own **R5 (with Nate), R11, R12, R14, R17, F6, F7, F8, F9, F13, F15, F18 and R21/R23**, co-own R18/F14 with Nate, the scripted fallback and the submission. Criterion 1 (25 points) is your loop.

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

## 3. ▶ Current tasks (2026-11-14 07:10)
### 🆕 v2.5 research pass (2026-11-14 07:10): do these first, in order (same vision; PRD §0 v2.5, decisions.md D1, D7, D22–D26)
*Must exist by 15:30: real-wired `run.py` with the scripted mover, shared capture on real cameras, real Inspector, localisation zone gate, grasp band and bowl-region checks, reason codes and deadlines, the recovery chain, JSONL telemetry, cached lines.*
| # | Status | Task | Hours | Done when |
|---|---|---|---|---|
| H1 | ✅ | `run.py`: `HelpNeeded` with a **reason enum**, per-state deadlines and retry budget, `PAUSE_HUMAN` instead of exit-after-home, hold flag checked at stage boundaries (depth/blob "something tall"), `abort_event` into episodes, recovery chain `[look again, roll 90, re-grasp]` | 4 | Mock run shows reasons per stage |
| H2 | ✅ | Bug fixes: `_resolve_uncertain` re-scores a stale frame (pass `newer_than=time.monotonic()` after a settle); `config/rules.yaml` `second_view: inspect` (not `top`) and add the roll to `reinspect_angles`; the help line speaks a reason, not an exception class name | 0.5 | Tests |
| H3 | ✅ | Cached-WAV table keyed by reason (calm + cowboy) | 1 | Every reason has a line |
| H4 | ✅ | JSONL telemetry writer (Aiven later, after the gate) | 1 | Rows per stage |
| H5 | ⬜ | 08:00–10:00 cameras by-id, decide which is the RealSense, click the zone corners (homography), waypoints | — | All streams open by path |
| H6 | ✅ | Read Intel's `physicalai/examples/tutorials/collect_train_deploy.ipynb` cells 5–9 (0.5 h) to confirm import paths and camera API; adopt `RobotRuntime` only if it accepts our abort and early-exit callbacks (add-on, 1 h max). Keep `Cell`, the `robot/io.py` clip + speed cap and shared capture | 0.5 | Notes |
| H7 | ⬜ | Intel-stack items wired where we really call them (time-boxed 2 h); `ReasonTrace` panel (0.5 h) | 2.5 | On screen |
| H8 | ⬜ | 21:00–23:00 demo script built around a real borderline-brick recovery, a disturbance pause, and an n = 20 slide with intervals; backup video by 22:00 | 2 | Rehearsed |
**If you're behind at 12:00:** Saliha's agent takes the telemetry writer and the cached-WAV table.
**Add-ons (after the 15:30 gate, in order):** persona obstacle trigger + cowboy voice on the hold flag, H key for the hat (1 h) · one live ElevenLabs line from the Nemotron text (1 h, with Saliha) · Aiven producer thread + drift alarm, JSONL stays the default (2 h; Kafka free plan unconfirmed, fallback LISTEN/NOTIFY) · IK scripted pick only if ACT misses 17:00 (2 h).
**Saved for later:** camera-based hat detection (H key instead).

🆕 **Vision (PRD v2.3 §1a):** (1) the Intel task done accurately, smoothly and in reasonable time, always first; (2) the robot explains its reasoning out loud, live, in a calm voice; (3) an obstacle or the cowboy hat flips it into a cowboy persona ("Holy smokes!") until the moment passes. Personality never slows the arm or costs a gate. No frontend, ever.
🆕 **What changed (PRD v2.2):** Aiven's page scores **meaningful use (40%)**, so the database must change what the cell does, not only log (F15). Modal scores a **live deployed app (15%)**: an optional read-only dashboard (F16) covers that and Aiven's impact at once. Intel wants **cameras shared between policy and inspection** (F13). Cameras at the station: **top view + inspection + wrist**; objects are Duplo.
*Status: ⬜ not started · 🟡 in progress · ⏸ blocked · ✅ done*

### BLOCK A: tonight 00:45–02:30 (own laptop, no hardware)
Goal: the whole application runs in `--mock` mode, so on Saturday only the real parts plug in.

| # | Status | Task | Est. | Done when |
|---|---|---|---|---|
| A1 | ✅ | GitHub repo (MIT), folders per PRD 10, `progress.md`, `Makefile` (`mock`, `run`, `rebaseline` → `python -m perception.rebaseline`), `common/interfaces.py` copied from PRD 7.3; tell the team "frozen" at 01:00. *(2026-11-14 00:10: repo and `progress.md` already exist; MIT licence, folders, `Makefile`, `interfaces.py` still to do.)* | 15 min | Others can pull |
| A2 | ✅ | `config/{cameras,rules,robot}.yaml` (camera paths as placeholders); `MockCamera` (folder of images), `MockInspector`, `MockMover` | 15 min | — |
| A2b 🆕 | ✅ | **F13 shared capture:** `common/capture.py` (or in `run.py`), one thread per camera keeps the latest frame; the policy and the inspector both read it, no second grab. Roles in `cameras.yaml`: `top`, `inspect`, `wrist` | 15 min | Mock run reads each camera once per tick |
| A3 | ✅ | `run.py` state machine `IDLE→LOCATE→PICK→VERIFY_GRASP→INSPECT→DECIDE→[REINSPECT]→PLACE→LOG→next`; every exception → `HOME` plus a spoken message; flags `--mock`, `--scripted pick,place`. Build it on the `physicalai` runtime pieces (`InferenceModel`, `RobotRuntime`) where they fit (R5). | 30 min | Mock run sorts 5 fake bricks |
| A4 | ✅ | `ui/mission_control.py`: one OpenCV window (feed, heatmap overlay, label and score, state, per-stage latency, bricks done); keys S/P/E/Q on the control thread | 20 min | Readable at 2 m |
| A5 | ⬜ | **Aiven:** 🆕 **Aiven for Apache Kafka** topic `sortsense.events` (+ `sortsense.alerts`) for live streaming, plus free-tier PostgreSQL ($50 credits on sign-up; no Kafka on our plan → PostgreSQL `LISTEN/NOTIFY` instead); producer on the telemetry thread, a consumer that writes rows and runs the drift rule (PRD F15); table `events` (PRD 7.3) 🆕 plus `inspections`, `benchmarks`, `models` (PRD F15); `telemetry/writer.py`: `queue.Queue` → `runs/events.jsonl` → batch insert; offline = JSONL only, sync later; `telemetry/report.sql` (success rate, latency per stage and device) | 20 min | Rows in Aiven from a mock run |
| A6 | 🟡 | **ElevenLabs:** ~~API key~~ *(2026-11-14 03:33: key in Harry's `.env` as `ELEVENLABS_API_KEY`, 130k credits)* (MLH code: https://mlh.link/junction-26); 🆕 pick 2 voices: **calm** (cool, collected) and **cowboy** (Voice Library western voice, or Voice Design) *(2026-11-14 03:45, Harry: cowboy = **David, deep southern cowboy** (Voice Library), voice ID `0hh7H4ZVAtaGpm1VZyEN`; calm = a standard conversational voice, ID `etWmxTqEKhIYyGKMpDcb` (open to change). **SDK:** official `elevenlabs==2.78.0` (pinned; Harry agreed 2026-11-14 04:14) + `python-dotenv` to load the key. Every spoken line is **conversational**: the robot talks through its thought process like a person thinking aloud, so the judges hear why it does each thing)*; `narrator/cache.py` pre-generates the template phrases below **in both personas** plus the exclamations ("Holy smokes!", "Well I'll be", "Yeehaw") with the most expressive model → WAV; `narrator/say.py` plays on a thread; live lines (from Saliha's reasoner, or templates with the numbers) via `eleven_flash_v2_5` streaming with a 1.5 s timeout, falling back to the cached phrase; a queue that drops stale lines | 30 min | Narration never blocks a state transition |
| A6b 🆕 | ⬜ | **F18 persona state machine** `narrator/persona.py`: CALM → COWBOY on `narrator.trigger("obstacle"\|"hat")` (instant, cached exclamation); back after the trigger has cleared and one brick is done, through one half-way line; H key = hat trigger for the demo. Mock test: trigger → cowboy lines → cool-down → calm | 15 min | Mock run switches and returns |
| A7 | ✅ | `fallback/scripted.py` skeleton: replays named joint waypoints from `config/waypoints.yaml` via Nate's `robot/io.py` (use his `MockRobot` once pushed around 02:00; until then a local stub with the same 4 methods) `[⏸ waits on @nate: MockRobot]` | 10 min | Works against the mock |
| A8 | ⬜ | README skeleton and architecture diagram (from PRD 7.1) | 10 min | Committed |

### BLOCK B: Saturday 08:00 → Sunday 09:00 (follow the slot table in PRD 10)
| Time | Status | Task | Done when |
|---|---|---|---|
| 08:00–09:00 | ⬜ | Mount the cameras and lamp, tape the pick zone (10×10 cm), inspection mark and bowls; `ls /dev/v4l/by-id/` → `cameras.yaml`; RealSense via `pyrealsense2`; SSH plus tmux set up for everyone | All 3 streams open by path |
| 09:30–10:00 (robot) | ⬜ | Teach waypoints by hand-guiding: pick spot, inspection pose, red bowl, blue bowl, home | Scripted sort works |
| 10:00–10:30 | ⬜ | Hold the inspection pose for Saliha's capture | — |
| 10:30–14:00 | ⬜ | Resets for Nate's recordings; in between, **F9 localization**: colour blob in the pick zone (overhead webcam) plus RealSense depth → brick present and position; stop when empty | Position logged |
| **15:30 gate (robot)** | ⬜ | With Saliha: **scripted full loop with real Anomalib, 5 bricks, no human** | Pass; film it as the backup video v1 |
| 15:30–19:00 | ⬜ | Mission control on the real feed; live narration and telemetry; tune the spoken lines. 🆕 **F18 obstacle trigger:** RealSense depth in the workspace (taller than a brick, or not brick-shaped) → `narrator.trigger("obstacle")` and the loop skips it; wire Saliha's `hat_seen` (from 19:00). 🆕 **F15 drift alarm:** run Saliha's drift query every few bricks on the telemetry thread → "lighting changed, rebaseline" on screen and spoken | Live |
| 19:00–21:00 (robot) | ⬜ | Swap in Nate's policies behind `Mover`; keep `--scripted` working | Both modes |
| 21:00–23:00 | ⬜ | ~~F16 Modal dashboard~~ (dropped: no frontend). 🆕 Rehearse the cowboy beat (PRD §11, 1:00) on the real table. Architecture slide, README (run steps, device rationale, benchmark placeholder for Saliha), submission text draft | Drafts ready |
| 23:00–01:00 | ⬜ | **Freeze**; 20 logged trials with Nate; 🆕 F14 shifted and pile trials (F9 picks the most isolated brick first); film the best runs; sleep 01:00–06:00 | Trial table from `report.sql` |
| 06:00–09:00 | ⬜ | Edit the 2-minute video; finish the README; Junction Platform submission (Intel, plus ElevenLabs, Aiven, Modal, and NVIDIA if we enter it; Nemotron needs a short text on model, role and how we improved its output) **by 09:00** | Submitted |
| 09:00 → demo | ⬜ | Lead rehearsals: the script in PRD 11, the e-stop drill, the backup video on a second screen | — |

**Seams** (the same note is in the other two briefs):
- @saliha 🆕: F15 drift rule comes from Saliha; F12 energy numbers go in the `benchmarks` table; F17 reasoner lines arrive through `narrator.say(event, text=..., persona=...)`; `reasoner.hat_seen(top_frame)` feeds F18. Contract lines in PRD 7.3, freeze 01:00.
- @saliha: `run.py` calls `Inspector.inspect(frame, view, brick_id)` → `DefectSignal`; `label` → instruction via `config/rules.yaml` (F1); mission control draws `heatmap_path`, `bbox`, `score`; `make rebaseline` → `python -m perception.rebaseline`.
- @nate: `reinspect(0)` = put down + pick again, `reinspect(±90)` = wrist roll, `True` only back at the inspection pose (agreed by all three 04:16); `fallback/scripted.py` implements the same.
- @nate: `fallback/scripted.py` replays waypoints through Nate's `robot/io.py`; learned policies arrive through `Mover`; `--scripted pick,place` stays available.

## 4. Done log (newest first)
- 2026-11-14 06:04 · H6 · read the `physicalai` tutorial + runtime source: imports valid; keep `Cell`/`io.py`/`SharedCapture`, no `RobotRuntime` before 15:30 (it bypasses `io.act`'s clip and e-stop); joint-unit risk flagged to @nate (`SO101` defaults to normalized, `io.py` uses degrees); optional `create_camera` adapter for UVC + RealSense
- 2026-11-14 05:58 · H3 · `narrator/lines.py` (every event and `Reason`, calm + cowboy) + `narrator/cache.py` (35 WAV clips, 1,520 characters; not generated yet); merged to `main` (`6e597fe`), 76 tests pass
- 2026-11-14 05:52 · H1 · `Reason` codes in every `events` outcome, stage deadlines (`common/deadline.py`), PAUSE_HUMAN (P go on, Q stop), hold flag; merged to `main` (`18ae0d7`), 68 tests pass. Waiting: @nate `abort_event=deadline.abort` in `LearnedMover`
- 2026-11-14 05:42 · H2 · fresh frame after a 0.3 s settle for every inspection, `second_view: inspect`, `reinspect_angles: [90, 0]`, help line says the reason; merged to `main` (`4bd8cb2`), 57 tests pass · H4 was already built in A3 (`telemetry/` → `runs/events.jsonl`)
- 2026-11-14 05:32 · A4 · `ui/mission_control.py` (feed, heatmap, verdict, stage times, mover mode; S/P/E/Q/H) + e-stop path B (D21: keys set flags, control thread acts); merged to `main` (`4d28398`), 55 tests pass. Waiting: @nate `io.act` e-stop check, @saliha `opencv-python`
- 2026-11-14 05:18 · A3 real-station half (R5) · `run.py` without `--mock`: real cameras, Saliha's inspector via `config/models.yaml`, scripted or learned mover per part (`--scripted`), config checked before anything moves, Ctrl+C = e-stop; merged to `main` (`de5fe0a`), 48 tests pass
- 2026-11-14 04:38 · A7 · `fallback/scripted.py` `ScriptedMover` (all 6 `Mover` methods, gripper kept closed while carrying) + `fallback/teach.py` (hand-guide, Enter saves into `config/waypoints.yaml`); merged to `main` (`b7c2f6e`), 44 tests pass with Nate's
- 2026-11-14 04:30 · A2b, A3 · `common/capture.py` (shared grab, fresh-frame wait), `run.py` state machine with grasp retry, uncertain chain, help + HOME; `python run.py --mock` sorts 5 bricks; merged to `main` (`c3deb81`), 23 tests pass
- 2026-11-14 04:23 · A2 · `config/{cameras,rules,robot,voices}.yaml`, `common/mocks.py` (`MockCamera`, `MockInspector`, `MockMover`); merged to `main` (`81f946d`), 11 tests pass
- 2026-11-14 04:21 · A1 · `common/interfaces.py` (PRD 7.3), `Makefile`, MIT licence, package layout; merged to `main` (`eb78073`), 3 contract tests pass

## 5. Working-style notes for the agent
- When you decide or finish something that changes the design, add or update its entry in `decisions.md` the same turn (CLAUDE.md §4a): facts and measured numbers only.
- Options + a recommendation, no teaching notes unless asked. Flag scope creep at once. Spell out abbreviations once.
- Hackathon pace: the smallest thing that passes its *Done when*.

## 6. Open blanks (fill when the chat or repo answers them, CLAUDE.md 🔁)
- GitHub handle and agent tool: `Harryt3nn` · Claude Code
- Camera by-id paths: {{paths}} · ElevenLabs voice IDs: cowboy = David (deep southern cowboy) `0hh7H4ZVAtaGpm1VZyEN` · calm = standard conversational `etWmxTqEKhIYyGKMpDcb` (open to change) · Aiven service name and env var: {{aiven}}

## 6a. Reference
### Narrator templates (deterministic fallback when the reasoner is late; no LLM)
| Event | Calm | Cowboy 🆕 |
|---|---|---|
| `perfect` | "Looks perfect. Blue bowl." | "Clean as a whistle. Blue bowl, partner." |
| `defective` | "Defect near the {region}. Red bowl." | "Well I'll be, a mark near the {region}. Red bowl it is." |
| `uncertain` | "Not sure about this one, taking a second look." | "Hold your horses, lemme look again." |
| `grasp_fail` | "Missed it, trying again." | "Dang, slipped. One more go." |
| `help` | "I need a hand, going home." | "Need a hand here, headin' home." |
| `empty` | "All done. {n} sorted." | "That's the herd. {n} sorted." |
| trigger 🆕 | — | "Holy smokes!" / "Yeehaw!" |
| cool-down 🆕 | "Ahem. Where was I. Back to work." | (half-way line, calm voice: "Right, partner... I mean, right.") |

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
