# SortSense (Junction 2026): progress log and conflict board

The team's shared history: who shipped what, when, on which branch, whose work it touches, and who is waiting on whom.
The plan itself is `CLAUDE.md`, `prd.md` and `builder-briefs/` on the `context` branch; this file is the history.

> **Template.** Fill `{{…}}` as the project's details arrive (self-filling rule, `CLAUDE.md`).

## How this file works (read once)
- **Newest first.** A new entry goes at the top of the Log. Stamps are `YYYY-MM-DD HH:MM` in **Espoo local time (EET, UTC+2)**,
  so top to bottom is newest to oldest. Stamps before 2026-11-14 04:30 were UK time (2 h behind Espoo).
- **One entry per finished thing:** a feature, a fix, a merge, an infra change, a gate result, a decision that changes
  someone's work, or a scope change. Not one per work-in-progress commit.
- **The heading says whether it conflicts:** `[conflicts: none]` or `[conflicts: @name]`, so a skim of the headings shows
  every clash.
- **Write it in the same turn you push**, then commit and push `progress.md` to `main` straight away. The board is never behind.
- **Every ⚠️ conflict and 📨 need also gets a row on the Open board.** The row is removed once it's resolved, and the entry's
  Status line records who resolved it. Entries are history: never delete or reword someone else's, only annotate.
- **Merge conflict in this file?** Keep both sides, sorted newest first. Never drop an entry.
- **Volatile facts** (current commit, test counts, benchmark numbers, gate results) live only in 📊 Latest.
- Agents: when to read and write this file is CLAUDE.md §2b; scope changes are §2c. Per-agent failover notes go in
  `handoff/<name>.md` on `context`, not here.

**Entry format** (copy it to the top of the Log):
```
### <YYYY-MM-DD HH:MM> — <feat | fix | merge | gate | decision | scope | docs> — <what, in plain words> — @<builder> [conflicts: none | @<name>]
- **Where:** `<branch>` @ `<short sha>` · merged to `main`: yes | not yet
- **Did:** <what changed and why, 1–3 lines; numbers if you measured something>
- **Touched:** <files / modules / contracts / config / hardware slot>
- **Brief task:** <task id in builder-brief-<name>.md> → ✅ done | 🟡 part | none
- **⚠️ Conflicts:** @<Name>: <what of theirs this changes or could break, and what they should do> | none
- **📨 Needs:** @<Name>: <what you need from them, and which of your tasks it blocks> | none
- **Agreed by:** @<Name>, @<Name> (decision and scope entries only)
- **Status:** open | resolved by @<Name> <YYYY-MM-DD HH:MM> (only when Conflicts or Needs isn't none)
```

---

## 📌 Open board (read on every prompt)
Everything still waiting on someone. Look for your name, or `@all`, under **To**.

| Since | From | To | Kind | What, and what to do | Entry |
|---|---|---|---|---|---|
| 2026-11-14 05:52 | @harry | @nate | 📨 waiting on | **Stage deadline for N2's `abort_event`:** `run.py` arms `common.deadline` around PICK, REINSPECT, PLACE and HOME (`DEADLINE_S`, TUNE). In `LearnedMover`, pass `abort_event=deadline.abort` (a `threading.Event`, `from common import deadline`) to `run_episode` and return `False` when it fires; `run.py` turns that into a TIMEOUT reason. `ScriptedMover` already does this | 2026-11-14 05:52 |
| 2026-11-14 07:15 | @saliha | @all | 🔀 scope proposal | **PRD v2.5 on `context` (`5da0552`), re-sync.** A research pass (6 research agents + design + critic) put an ordered 🆕 v2.5 block at the top of each brief's ▶ Current tasks. Same vision. Highlights: no RL (D1, numbers in), every stage verified with reason codes/deadlines (D22), recovery order look-again → roll → re-grasp (D7), two fixed VLA strings + language-swap test + single-colour ACT hedge (D23), device/efficiency measured (D24), Nemotron advisory only (D25), **red-lego smoke test first** (D26). Bugs listed per person. Say no on this row to anything in your block. **@harry 05:41: yes** to the whole block, and yes to `run.py` calling `perception/scene.py` (zone gate + bowl-region check). **@nate 05:54: yes** to the whole block; N1's ACT export goes through Studio's Python API or runs on Modal (the `physicalai` CLI crashes on Windows: `fcntl`) | 2026-11-14 07:15 |
| 2026-11-14 05:32 | @harry | @saliha | 📨 waiting on | **`opencv-python` instead of `opencv-python-headless`** in `perception/requirements.txt`: mission control (F6) needs a window, the headless build has none, and the two can't be installed together. Same library and API; perception code is unaffected | 2026-11-14 05:32 |
| 2026-11-14 05:12 | @nate | @all | 🔀 scope proposal | **Training stack and F14 positions changed in my area** (`main` @ `8bc38a6`, `decisions.md` D20): ACT now trains with **Physical AI Studio's trainer** (`physicalai fit`), so it exports straight into the `physicalai` runtime; SmolVLA stays on LeRobot (Studio's SmolVLA loader is unfinished). ACT demos: **all 9 positions × 6, recorded in rounds**. @harry: F14's "new positions" trials use only the off-grid spots. Say no on this row if you object | 2026-11-14 05:12 |
| 2026-11-14 05:15 | @saliha | @nate | 📨 waiting on | **Your Block A code is on `main` (`ac2e2f2`)**: review it; then `modal token new`, add a Modal secret `huggingface` (HF_TOKEN), run the A2 smoke (`modal run train/modal_train.py --dataset lerobot/svla_so100_pickplace --steps 200`) and the A3 export test on those checkpoints. Pick the 🟠 in `train/RECORDING.md`. **@nate 05:12:** `train/` reviewed and reworked (see Log), 🟠 picked (all 9 in rounds); Modal login, A2 and A3 next. **@nate 05:47:** Modal and the `huggingface` secret set up; A2: ACT training on Modal, SmolVLA stops on camera names (= v2.5 N1); A3 next | 2026-11-14 05:15 |
| 2026-11-14 01:35 | @saliha | @all | ⚠️ conflict | **Branches renamed again, by discipline:** `aiml-perception-saliha`, `robotics-policies-nate`, `systems-voice-harry` (older rows below use the previous names; none were pushed yet). New file **`decisions.md`** on `context` (design choices and why, for pitching): your agent updates it on its own as you build (CLAUDE.md §4a). Re-sync from `context` | 2026-11-14 01:35 |
| 2026-11-14 01:00 | @saliha | @all | 🔀 scope proposal | **PRD v2.3 on `context` (`b423fc4`), re-sync.** The team vision is now written in: Intel task first (accurate, smooth, quick); then the robot **explains its reasoning out loud live** (Nemotron writes, ElevenLabs speaks) and an **obstacle or cowboy hat flips it into a cowboy persona**. NVIDIA Nemotron is in (@saliha, `reasoner/`). Aiven = Kafka streaming → PostgreSQL (@harry). Modal = training + logs only; the F16 dashboard is dropped (no frontend). **Branches renamed, one per person:** `aiml-perception-saliha`, `robotics-policies-nate`, `systems-voice-harry`. Contract additions in PRD 7.3 (`narrator.trigger`, `reasoner.explain`, `reasoner.hat_seen`) need @harry's yes before the 01:00 freeze. **@nate 01:42: yes** | 2026-11-14 01:00 |
| 2026-11-14 00:35 | @saliha | @all | 🔀 scope proposal | **PRD v2.2 on `context` (`84364a8`), re-sync.** New 🆕 items in every brief from the Junction challenge page + side-track pages: F11 demo-count sweep on Modal (@nate), F12 power/energy/thermal benchmark (@saliha), F13 shared cameras (@harry), F14 shifted + pile trials (@nate @harry), F15 Aiven drift alarm + more tables (@harry), F16 optional Modal dashboard (@harry), F4 now includes a re-grasp. Object = Duplo, cameras = top + inspection + wrist. Say no on this row if you object to any item in your brief. **@nate 01:42: yes** | 2026-11-14 00:35 |
| 2026-11-14 00:10 | @saliha | @all | ⚠️ conflict | **How docs work:** plan docs live on the `context` branch, never `main`. Set up once with 🚀 Start here below. Role branches: `perception-saliha`, `robot-nate`, `integration-harry`. Send @saliha your GitHub handle | 2026-11-14 00:10 |
| 2026-11-14 00:10 | @saliha | @all | ❓ question | PRD §13 open questions for the mentors (Sat 08:00–09:00), incl. whether 11:50 Sunday is our demo slot and which clock the 10:00 deadline is on | 2026-11-14 00:10 |

**Kinds:** ⚠️ conflict (my change touches your work) · 📨 waiting on (I'm blocked until you do X) · 🔀 scope proposal (needs
the whole team's yes, CLAUDE.md §2c) · ❓ question for a teammate (project-wide unknowns go in PRD §13).

## 👥 Team
Full ownership and tasks live in each builder's brief (`builder-briefs/builder-brief-<name>.md` on `context`). Update your
own **Now** cell whenever you log an entry.

| Who | GitHub | Role | Branch | Owns (paths) | Now |
|---|---|---|---|---|---|
| Saliha | `saliha006` | **AI/ML**: computer vision (Anomalib), edge-AI optimisation (OpenVINO), Nemotron reasoner; doc owner | `aiml-perception-saliha` | `perception/`, `bench/`, `reasoner/` | Block A done (A11 live call waits on the NVIDIA key); next Sat 08:00 install on the Intel laptop |
| Nate | `aldrichbanas07` | **Robotics and robot learning**: robot I/O, imitation-learning policies (ACT, SmolVLA), Modal training + logs | `robotics-policies-nate` | `robot/`, `policies/`, `train/` | A2: ACT training on Modal, SmolVLA waits on v2.5 N1 (camera rename); e-stop check in `robot/io.act` done; next: v2.5 yes/no, then N1 |
| Harry | `Harryt3nn` | **Systems and integration**: orchestration, ElevenLabs voice (live reasoning + cowboy switch), Aiven streaming, demo, submission | `systems-voice-harry` | `run.py`, `common/`, `fallback/`, `ui/`, `narrator/`, `telemetry/`, `config/`, `README.md`, `docs/` | v2.5: H1–H4 done (H3 clips not generated yet); next H6 physicalai notebook, H7 ReasonTrace panel |

**Shared** (anyone may edit; flag it in ⚠️ Conflicts): `progress.md` (on `main`), `Makefile` (Harry creates it). Plan docs
on the `context` branch (`CLAUDE.md`, `prd.md`, `builder-briefs/`): doc owner publishes (CLAUDE.md 📤); your own
`handoff/<name>.md`: you.

## 🚀 Start here (new teammate, first 15 minutes)
1. Clone `https://github.com/saliha006/Chooms-chrome`. Set `git config user.email` to your GitHub email (commits are
   credited by author) and `git config team.builder <your-name>` (the agents and the Open board use it).
2. Plan docs stay off `main` by themselves: the `.gitignore` on `main` blocks every `.md` except `progress.md`, `README.md` and the brief-named files, plus `.env*`, datasets and checkpoints.
3. Pull the docs from `context` (they never live on `main`): `git fetch origin context && git archive origin/context | tar -x
   && git rev-parse origin/context > .git/context-synced`. Install the skills: `mkdir -p .claude/skills && cp -r skills/* .claude/skills/ && rm -rf skills`.
   Then `git switch -c <your branch>` (one per person: `aiml-perception-saliha`, `robotics-policies-nate`, `systems-voice-harry`).
4. Put the `.env` @saliha or @harry sends you (directly, not via git or chat) at the repo root. Never commit it; never paste a key.
5. Tell your agent "fetch the context": it reads `CLAUDE.md`, PRD §0 and your brief.
6. Read your brief's `▶ Current tasks`, then the 📌 Open board above.

## 📊 Latest (volatile facts live only here)
- **Plan (2026-11-14 05:47):** PRD v2.5, `context` @ `5da0552`.
- **robot/policies/train (2026-11-14 05:47):** `main` @ `f6a9f65`: 64 pass across `robot`, `policies`, `fallback`, `train`, `common` (1 Studio-only test skipped); mock loop sorts 5 bricks.
- **Modal A2 (2026-11-14 05:47):** SmolVLA image fixed (LeRobot `training` extra), now stops on camera names (`camera1..3` expected; v2.5 N1); ACT via Studio training, result pending.
- **perception (2026-11-14 04:30):** `main` @ `99f1d09`: 28 tests pass (4 slow); live Nemotron line 1.7–2.7 s. Not yet run on the Intel laptop or real bricks.
- **`main` (2026-11-14 05:47):** @ `f6a9f65`, code in every area. Plan docs on `context`.

---

## Log (newest first)

### 2026-11-14 05:57 — merge — H3: a spoken line for every event and failure reason, calm + cowboy; clip generator — @harry [conflicts: @saliha]
- **Where:** `systems-voice-harry` @ `6e597fe` · merged to `main`: yes
- **Did:** `narrator/lines.py`: one conversational line per event `run.py` says and per `Reason` (`help.<reason>`), in both personas, plus the cowboy exclamations and the cool-down / half-way lines; no numbers (the grounded lines with scores come live from the reasoner). `narrator.say` now speaks the line (console until A6 playback). `narrator/cache.py`: `python -m narrator.cache --dry-run` lists 35 clips, 1,520 characters; without `--dry-run` it writes `narrator/clips/<persona>/<key>.wav` through the ElevenLabs SDK (`config/voices.yaml`: `cached_model: eleven_multilingual_v2`, `cached_format: wav_22050`), skipping clips that exist. Clips not generated yet. 76 tests pass with Nate's (generator tested against a fake client).
- **Touched:** `narrator/`, `config/voices.yaml`
- **Brief task:** H3 → ✅ done (code; clips to generate)
- **⚠️ Conflicts:** @saliha: reasoner lines still go through `narrator.say(event, text=...)`; `text` wins over the cached line
- **📨 Needs:** none
- **Status:** open

### 2026-11-14 05:52 — merge — H1: reason codes, stage deadlines, PAUSE_HUMAN, hold flag — @harry [conflicts: @nate @saliha]
- **Where:** `systems-voice-harry` @ `18ae0d7` · merged to `main`: yes
- **Did:** `common/reasons.py` `Reason` (grasp_failed, brick_lost, place_failed, timeout, camera, inspect_failed, unexpected) + `HelpNeeded(reason, detail)`; the code goes in the `events` row's `outcome` (no schema change) and every stage logs its outcome. `common/deadline.py`: `run.py` arms a deadline around PICK (20 s), REINSPECT (25 s), PLACE (15 s), HOME (15 s), all TUNE; `ScriptedMover` stops when it fires; a stuck pick is a TIMEOUT and is not retried. Any failure (including a bug) → home, say the reason, **PAUSE_HUMAN**: P carries on with the next brick, Q stops at home, E still wins; `--headless` stops instead. `Cell.hold` waits at stage boundaries for "something tall" (to be set by depth / `perception/scene.py`), announces it once (`narrator.trigger("obstacle")`), and Q cannot override it. Mission control shows NEED HELP + reason and HOLD. 68 tests pass with Nate's. Recovery chain was H2.
- **Touched:** `run.py`, `common/reasons.py`, `common/deadline.py`, `fallback/scripted.py`, `ui/mission_control.py`
- **Brief task:** H1 → ✅ done
- **⚠️ Conflicts:** @nate: `LearnedMover` should pass `common.deadline.abort` as `abort_event` (board row). @saliha: `perception/scene.py` sets `cell.hold` for something tall and feeds the bowl-region check into PLACE's success; reason codes are ready for your `ReasonTrace` (S6)
- **📨 Needs:** @nate: `abort_event=deadline.abort` in `LearnedMover`
- **Status:** open

### 2026-11-14 05:47 — fix — E-stop check in `robot/io.act`; SmolVLA image gets LeRobot's training extra; sweep takes smaller sizes — @nate [conflicts: @harry]
- **Where:** `robotics-policies-nate` @ `f6a9f65` · merged to `main`: yes
- **Did:** `robot/io.act` now turns the torque off and raises `EStopped` once E is requested (D21, Harry's ask), so learned-policy motion stops within one control step; `move_to` and the policy loop go through it. A2 smoke on Modal: SmolVLA's image lacked LeRobot's `training` extra (`datasets` ImportError), fixed; it now stops on camera names (`smolvla_base` expects `camera1..3`, the public set has `top`/`wrist`), which is v2.5 N1 (`--rename_map` + a 3-camera dataset). ACT via Studio is training. `--sweep-sizes` lets the A8 smoke run small sizes on the 50-episode public set. 64 tests pass; mock loop sorts 5 bricks. Read and kept: Saliha's `HF_TOKEN` fallback and the catch-up note (rows closed).
- **Touched:** `robot/io.py`, `robot/tests/test_io.py`, `train/modal_train.py`
- **Brief task:** Harry's 📨 → ✅ · A2 → 🟡 (ACT running, SmolVLA waits on N1) · A8 → 🟡
- **⚠️ Conflicts:** @harry: `robot/io.py` now imports `common.estop`; `fallback/scripted.py`'s own e-stop check is redundant but harmless
- **📨 Needs:** none
- **Status:** open

### 2026-11-14 05:42 — fix — H2: uncertain chain uses fresh frames from the inspection camera; roll before re-grasp; help line says why — @harry [conflicts: @saliha @nate]
- **Where:** `systems-voice-harry` @ `4bd8cb2` · merged to `main`: yes
- **Did:** Every inspection now scores a frame grabbed after a 0.3 s settle (`SETTLE_S`, TUNE); before, "look again" re-scored the frame already judged uncertain. `config/rules.yaml`: `second_view: inspect` (the model only knows that camera), `reinspect_angles: [90, 0]` = roll, then re-grasp (PRD v2.5 order). The help line speaks the reason ("grasp failed twice"), not an exception name. 57 tests pass with Nate's. H4 (JSONL telemetry writer) was already built in A3: `telemetry/` → `runs/events.jsonl`, one row per stage.
- **Touched:** `run.py`, `config/rules.yaml`, `common/tests/`
- **Brief task:** H2 → ✅ done · H4 → ✅ done (A3)
- **⚠️ Conflicts:** @saliha: the F4 chain is now look again (inspect cam) → `reinspect(90)` → `reinspect(0)` → defective, as PRD v2.5 says. @nate: `reinspect(90)` is now called before `reinspect(0)`, so the re-grasp starts from a rolled wrist
- **📨 Needs:** none
- **Status:** open

### 2026-11-14 07:15 — scope — PRD v2.5 from a research pass: verified stages, recovery order, honest evaluation, smoke test on public data, no RL — @saliha [conflicts: @nate @harry]
- **Where:** `context` @ `5da0552` · merged to `main`: n/a (docs)
- **Did:** Ran a research pass at Saliha's request (current-state map, 4 domain agents, a broad web/code/data search, a system-design agent, a harsh critic). Folded the accepted CORE items, bugs and ranked add-ons into PRD §0 v2.5, the three briefs (new top blocks), decisions.md (D1 RL numbers, D5–D7 note, D22–D26; Harry's D21 kept) and CLAUDE.md (cut order). No contract change to `common/interfaces.py`. Code reuse confirmed allowed on site.
- **Touched:** `prd.md`, `decisions.md`, `CLAUDE.md`, all briefs, `handoff/nate-catch-up.md`
- **Brief task:** none
- **⚠️ Conflicts:** @harry: `run.py` reason enum, deadlines, PAUSE_HUMAN, second-view and `rules.yaml` bugs (H1–H2). @nate: red-lego smoke test first, early exit + abort, gripper band, wrist roll-back bug, SmolVLA recipe gaps (N1–N4)
- **📨 Needs:** @harry: yes to `perception/scene.py` (zone gate + bowl-region check) being called from `run.py` → **@harry 05:41: yes**
- **Agreed by:** @saliha (doc owner); teammates asked on the Open board
- **Status:** open

### 2026-11-14 05:32 — merge — A4 mission control + e-stop path (D21) — @harry [conflicts: @nate @saliha]
- **Where:** `systems-voice-harry` @ `4d28398` · merged to `main`: yes
- **Did:** `ui/mission_control.py`: one 1280×720 OpenCV window: inspection feed, heatmap, label + score + thresholds, model and device, bricks sorted, time per stage, and which mover is running (honesty guardrail). Keys: S start, P pause/resume at the next stage, E e-stop, Q finish the brick then home and stop, H hat trigger. The window runs on the main thread and only sets flags; the cell runs on its own control thread (`common/estop.py`, `Cell.paused` / `Cell.quit`), so one thread ever talks to the motors. E: torque off, never homes after. `ScriptedMover` checks E on every control step (its gripper moves no longer use `io.move_to`). `run.py --headless` = no window, start at once, Ctrl+C = e-stop. 55 tests pass with Nate's.
- **Touched:** `ui/`, `common/estop.py`, `run.py`, `fallback/scripted.py`
- **Brief task:** A4 → ✅ done
- **⚠️ Conflicts:** @nate: learned-policy motion only stops at stage boundaries until `io.act` checks the e-stop (board row). @saliha: the window needs `opencv-python` (board row)
- **📨 Needs:** @nate: the `io.act` check · @saliha: `opencv-python` in `perception/requirements.txt`
- **Agreed by:** @harry (D21: e-stop path B)
- **Status:** @nate part resolved by @nate 2026-11-14 05:47 (`robot/io.act` checks the e-stop, `f6a9f65`); @saliha part open

### 2026-11-14 05:18 — merge — `run.py` real-station mode: real cameras, Anomalib inspector, scripted or learned mover per part — @harry [conflicts: @saliha @nate]
- **Where:** `systems-voice-harry` @ `de5fe0a` · merged to `main`: yes
- **Did:** Without `--mock`, `run.py` builds the real cell: `OpenCVCamera` per `cameras.yaml` role into `SharedCapture`, Saliha's `perception.inspector.Inspector` from the new `config/models.yaml`, `robot.io.connect(port, calibration)`, and per part `ScriptedMover` (`--scripted pick`, `place` or `pick,place`) or Nate's `LearnedMover` (ACT pick, SmolVLA place, GPU then CPU). Every config value is checked before anything moves, with a message naming what to set (camera paths, port, untaught waypoints, missing policy exports → suggests `--scripted`). The arm homes after the last brick; Ctrl+C = e-stop (torque off). Brick count comes from `--bricks N` (`common/locate.py` `CountLocator`) until F9. `config/robot.yaml`: dropped my unused `max_joint_speed` (the speed cap lives in `robot/io.py`), added `calibration`. 48 tests pass, incl. a full real-mode run with the scripted mover on a mock arm.
- **Touched:** `run.py`, `common/`, `config/models.yaml` (new), `config/robot.yaml`
- **Brief task:** A3 → real-station half done (R5)
- **⚠️ Conflicts:** @saliha: the inspector loads `runs/rebaseline/export/padim/int8/weights/openvino/model.xml` + `perception/thresholds.yaml` (what `make rebaseline` writes); change `config/models.yaml` if you export elsewhere. @nate: set `policies.act` / `policies.smolvla` in `config/models.yaml` to the export dirs after your gates; `LearnedMover` gets `None` for the policy it doesn't drive; policy cameras are `top`, `wrist`
- **📨 Needs:** none
- **Status:** open

### 2026-11-14 05:12 — scope — ACT trains with Studio, SmolVLA stays on LeRobot; ACT demos in rounds (`train/` reworked) — @nate [conflicts: @saliha @harry]
- **Where:** `robotics-policies-nate` @ `8bc38a6` · merged to `main`: yes
- **Did:** Reviewed the Block A `train/` code. ACT now trains with Physical AI Studio's trainer (`physicalai fit`, `physicalai-train` 0.3.0), so its checkpoint exports straight into the `physicalai` runtime; SmolVLA keeps LeRobot 0.7.0 because Studio's SmolVLA loader is marked "intentionally incomplete" (D20). Fixed three things that would have stopped the first run: the `--wandb` flag LeRobot 0.7 dropped, the missing `smolvla` extra, and reruns hitting an existing output folder (job names now carry a timestamp). `--lr` is optional: ACT 1e-5, SmolVLA its own 1e-4. `RECORDING.md`: all 9 positions × 6, recorded in rounds, so the sweep's first 18 / 36 / 54 episodes are 2 / 4 / 6 per position; F14 uses the off-grid spots. 7 tests; the ACT command is parsed by Studio's own `fit` parser.
- **Touched:** `train/commands.py`, `train/modal_train.py`, `train/tests/test_commands.py`, `train/requirements.txt`, `train/RECORDING.md`; on `context`: my brief, `decisions.md` D9, D15, D20
- **Brief task:** A1 → 🟡 part (done once the A2 smoke runs); A5 → ✅ (🟠 picked)
- **⚠️ Conflicts:** @saliha: your agent's `train/` code changed as above; the ACT IR you benchmark at 21:00 will come from Studio's export. @harry: F14's "new positions" trials use only the off-grid spots (all 9 grid positions get recorded)
- **📨 Needs:** none
- **Agreed by:** @nate; team asked on the Open board (🔀 05:12)
- **Status:** open

### 2026-11-14 04:38 — merge — A7: scripted fallback mover + waypoint teaching tool — @harry [conflicts: @nate]
- **Where:** `systems-voice-harry` @ `b7c2f6e` · merged to `main`: yes
- **Did:** `fallback/scripted.py` `ScriptedMover` (implements `Mover`): pick_above → pick → close → pick_above → inspect; place reads the bowl colour from the `rules.yaml` instruction; `reinspect(0)` puts down at `pick_drop` and picks again, `±90` rolls the wrist; `estop` = torque off. It keeps commanding the gripper closed while carrying (a position servo told "stay here" relaxes its grip), so arrival checks leave the gripper out. `fallback/teach.py`: torque off, hand-guide, Enter saves each pose into `config/waypoints.yaml` (comments kept; `--mock` to rehearse). `config/waypoints.yaml` with the 7 poses, null until taught; the mover refuses to start and names any untaught pose. 11 new tests against a `MockRobot` that closes on a brick; with Nate's tests 44 pass.
- **Touched:** `fallback/`, `config/waypoints.yaml` (also read by Nate's `LearnedMover`: same names `home`, `inspect`, `pick_drop`)
- **Brief task:** A7 → ✅ done
- **⚠️ Conflicts:** @nate: `GRIPPER_EMPTY_BELOW`, `GRIPPER_OPEN` and the inspection-pose tolerance are copied from `policies/mover.py` so the fallback never depends on the policy stack; if you would rather both read them from `robot/io.py`, say so and I will switch. Waypoints are taught Sat 09:30 with `python -m fallback.teach home pick_above pick pick_drop inspect bowl_red bowl_blue`
- **📨 Needs:** none
- **Status:** open

### 2026-11-14 04:30 — merge — A2b shared capture + A3 `run.py` state machine: mock run sorts 5 bricks — @harry [conflicts: @saliha @nate]
- **Where:** `systems-voice-harry` @ `c3deb81` · merged to `main`: yes
- **Did:** `common/capture.py` `SharedCapture` (F13): one grab thread per camera; the policy and the inspector get the same array; `frame(role, newer_than=...)` waits for a frame taken after the arm stopped. `run.py`: IDLE→LOCATE→PICK→VERIFY_GRASP→INSPECT→DECIDE→[REINSPECT]→PLACE→LOG; grasp retried once, then "help" + HOME and the run stops; uncertain → second view (`rules.yaml` `second_view: top`, no motion) → `reinspect(0)` → defective, said aloud; any exception → HOME + spoken message, run stops. One `events` row per stage (PRD 7.3 columns) via `telemetry` (queue → `runs/events.jsonl`). `narrator.say/trigger` print to the console until A6. 23 tests pass. Not yet on the `physicalai` runtime (R5): the real wiring comes with A7 / Block B.
- **Touched:** `run.py`, `common/`, `config/rules.yaml`, `narrator/`, `telemetry/`
- **Brief task:** A2b, A3 → ✅ done
- **⚠️ Conflicts:** @saliha: the F4 uncertain chain is coded in `run.py` from PRD §6 and driven by `config/rules.yaml`; tell me if your decision logic differs. Your one-line `run.py` import (Block B 13:00) goes in `build_mock`'s real twin. @nate: `run.py` takes separate pick and place movers, so `LearnedMover` and the scripted fallback can mix (`--scripted pick,place`)
- **📨 Needs:** none
- **Status:** open

### 2026-11-14 05:15 — feat — Nate's hardware-free Block A: robot I/O + MockRobot, learned Mover, Modal training — @saliha (for @nate) [conflicts: @nate @harry]
- **Where:** `robotics-policies-nate` @ `ac2e2f2` · merged to `main`: yes
- **Did:** Written by Saliha's agent at the doc owner's request (04:30 board row). `robot/io.py` on the physicalai SO-101 driver with joint limits + a 5°/step speed cap and `MockRobot`; `policies/mover.py` `LearnedMover` (ACT pick, SmolVLA place, `reinspect` as agreed); `train/modal_train.py` (LeRobot 0.7 on an A100, `--episodes`, `--sweep` 18/36/54); `train/RECORDING.md`, `runs.md`, `rejected.md`. 24 tests; whole suite 55 pass.
- **Touched:** `robot/`, `policies/`, `train/` (Nate's paths, with the doc owner's go-ahead)
- **Brief task:** Nate A4, A4b, A5, A6, A7 → ✅ · A1, A8 → 🟡 (need Nate's Modal login + smoke run) · A2, A3 → ⬜ (Nate)
- **⚠️ Conflicts:** @nate: review the code before Saturday; TUNE values are marked; one 🟠 choice in `RECORDING.md` (hold back 2 grid positions or not). @harry: `fallback/scripted.py` can call `robot.io.move_to(pose, seconds)`; `io.connect(mock=True)` gives you `MockRobot`
- **📨 Needs:** @nate: `modal token new`, a Modal secret `huggingface` with `HF_TOKEN`, then `modal run train/modal_train.py --dataset lerobot/svla_so100_pickplace --steps 200`
- **Status:** open

### 2026-11-14 04:23 — merge — A2: `config/*.yaml` and the mocks — @harry [conflicts: @nate @saliha]
- **Where:** `systems-voice-harry` @ `81f946d` · merged to `main`: yes
- **Did:** `config/rules.yaml` (PRD 7.3 verdict → instruction; uncertain → `reinspect_angles: [0]` then defective), `cameras.yaml` (roles `top`, `inspect`, `wrist`, each with its `DefectSignal.view` name; paths null until the station), `robot.yaml` (port and speed cap null: set at the station from the safety guidelines), `voices.yaml` (calm + David). `common/mocks.py`: `MockCamera` (folder of images or plain frames), `MockInspector` (label script, scores on the right side of the thresholds), `MockMover` (records calls; first N picks can fail). 11 tests pass.
- **Touched:** `config/`, `common/`
- **Brief task:** A2 → ✅ done
- **⚠️ Conflicts:** @nate: `config/cameras.yaml` is shared, record with the same role names and paths. @saliha: `cameras.yaml` gives the `view` string per camera
- **📨 Needs:** none
- **Status:** open

### 2026-11-14 04:30 — decision — Espoo time for everything; `reinspect` mirrored; Nemotron lines live and conversational — @saliha [conflicts: @nate @harry]
- **Where:** `context` @ `053f5de`; `main` @ `99f1d09` · merged to `main`: yes
- **Did:** Answered @nate's 01:42 question: all plan times and board stamps are **Espoo local (UTC+2)**, the event's clock, so the 09:00 internal submit is one hour before the 10:00 Espoo deadline. Mirrored the agreed `reinspect` into PRD §0 / 7.3 and Harry's brief. A11 done: live Nemotron (`nvidia/nemotron-3.5-super-vl-120b-a12b`) with thinking off, conversational think-aloud lines, 1.7–2.7 s each; it now gets the decided action, so it can't invert a verdict (it did before the fix).
- **Touched:** `reasoner/client.py`, `prd.md`, `CLAUDE.md`, all briefs, `decisions.md` D11, this file
- **Brief task:** A11 → ✅ done
- **⚠️ Conflicts:** @nate @harry: board times before 04:30 were UK time. @harry: `reasoner.client.explain(crop, signal, persona)` returns `(line, ms)`; personas `calm` / `cowboy`
- **📨 Needs:** none
- **Agreed by:** @saliha (clock, doc owner); `reinspect`: @nate, @harry, @saliha
- **Status:** resolved by @saliha 2026-11-14 04:30 (Nate's clock question, Harry's 04:16 request)

### 2026-11-14 04:21 — merge — A1: `common/interfaces.py` (PRD 7.3), `Makefile`, MIT licence, package layout — @harry [conflicts: @saliha @nate]
- **Where:** `systems-voice-harry` @ `eb78073` · merged to `main`: yes
- **Did:** Canonical contract file, copied from PRD 7.3 with the agreed `reinspect` meaning as a comment; `Inspector` and `Mover` are `runtime_checkable` so mocks and policies can be checked with `isinstance`. `Makefile` (`mock`, `run`, `rebaseline`, `bench`, `test`), root `requirements.txt` (pulls in `perception/requirements.txt` + `elevenlabs==2.78.0`, `python-dotenv`), `.env.example`, MIT `LICENSE`, empty packages for `fallback/`, `ui/`, `narrator/`, `telemetry/`. 3 contract tests pass.
- **Touched:** `common/`, `Makefile` (shared), `requirements.txt`, `.env.example`, `LICENSE`, my package folders
- **Brief task:** A1 → ✅ done
- **⚠️ Conflicts:** @saliha: `perception/contract.py` now resolves to `common.interfaces.DefectSignal` (checked); its fallback copy can go. @nate: `policies/` and `fallback/` implement `common.interfaces.Mover`
- **📨 Needs:** none
- **Status:** open

### 2026-11-14 04:16 — decision — `reinspect` agreed by all three; voices and ElevenLabs SDK chosen — @harry [conflicts: @saliha]
- **Where:** `context` @ `4856110` (Harry's brief, `decisions.md` D7, D12, D13) · merged to `main`: this file only
- **Did:** Said yes to `reinspect` (`0` = put down and pick again, `±90` = wrist roll, `True` only back at the inspection pose); `fallback/scripted.py` will implement the same. Voices: calm `etWmxTqEKhIYyGKMpDcb` (standard conversational, open to change), cowboy David `0hh7H4ZVAtaGpm1VZyEN`. Narration is conversational: the robot thinks aloud for the judges. ElevenLabs SDK `elevenlabs==2.78.0`, key in `.env` as `ELEVENLABS_API_KEY`.
- **Touched:** `builder-briefs/builder-brief-harry.md`, `decisions.md`, `progress.md`; no code yet
- **Brief task:** A6 → 🟡 part (key, voices, SDK chosen)
- **⚠️ Conflicts:** @saliha: the Nemotron live lines should match the conversational style (Open board row)
- **📨 Needs:** @saliha: conversational live lines; mirror `reinspect` into PRD 7.3 / §0 and Harry's brief
- **Agreed by:** @harry, @nate, @saliha (`reinspect`)
- **Status:** resolved by @saliha 2026-11-14 04:30 (lines conversational, `reinspect` mirrored)

### 2026-11-14 03:55 — feat — Perception pipeline end to end on stand-in data (Block A, A1–A11) — @saliha [conflicts: @harry]
- **Where:** `aiml-perception-saliha` @ `dd1c4d7` · merged to `main`: yes
- **Did:** Capture, synthetic stand-in bricks, PaDiM/PatchCore/EfficientAd training, OpenVINO FP16 + INT8 export with a static 1×3×256×256 input, uncertainty band + plots, inspector (NPU→GPU→CPU fallback, compile cache, heatmap, `DefectSignal`), rebaseline (~102 s + capture on a laptop CPU), benchmark harness with RAPL energy and temperature, Nemotron client. 28 tests (`pytest perception bench reasoner`; Python 3.12 venv, see CLAUDE.md Run · Test). Stand-in numbers are not reported.
- **Touched:** `perception/`, `bench/`, `reasoner/` (all mine)
- **Brief task:** A1–A10 → ✅ done · A11 → 🟡 part (live call needs `NVIDIA_API_KEY` + exact model id)
- **⚠️ Conflicts:** @harry: until `common/interfaces.py` lands, `perception/contract.py` mirrors `DefectSignal` from PRD 7.3 and imports yours as soon as it exists; `make rebaseline` → `python -m perception.rebaseline`; the inspector is `perception.inspector.Inspector(xml, thresholds_yaml, model_name).inspect(frame, view, brick_id)`
- **📨 Needs:** none
- **Status:** open

### 2026-11-14 01:35 — decision — `reinspect` agreed: `0` = re-grasp, `±90` = wrist roll — @nate [conflicts: @harry @saliha]
- **Where:** `context` @ `c67ba2b` (Nate's brief, `decisions.md` D7) · merged to `main`: this file only
- **Did:** Said yes to Saliha's proposal. `Mover.reinspect(0)` puts the brick down in the pick zone and picks it again (the F4 re-grasp); `reinspect(±90)` rolls the wrist in place; both return `True` only when the brick is back at the inspection pose. The PRD 7.3 signature is unchanged. Also filled my GitHub handle (`aldrichbanas07`) in my brief and 👥 Team. At 01:42 also said yes to the PRD v2.2 and v2.3 items in my brief (A8 sweep, F14 held-back and pile trials, recording additions, obstacles skipped).
- **Touched:** `builder-briefs/builder-brief-nate.md`, `decisions.md` (D7), `progress.md`; no code yet
- **Brief task:** A4b → 🟡 part (waiting on @harry)
- **⚠️ Conflicts:** @harry: `fallback/scripted.py` gives `reinspect` the same meaning (a put-down waypoint then pick again; wrist roll ±90°). @saliha: your F4 chain calls `reinspect(0)` for the re-grasp and `reinspect(±90)` for the roll, as your brief already says
- **📨 Needs:** @harry: yes or no on the 00:35 Open board row. @saliha: once @harry agrees, mirror it into PRD 7.3 / §0 and Harry's brief
- **Agreed by:** @nate, @saliha (proposed it); @harry asked
- **Status:** resolved by @harry 2026-11-14 04:16 (@harry: yes)

### 2026-11-14 01:35 — docs — Roles by discipline, branches renamed, `decisions.md` added — @saliha [conflicts: @nate @harry]
- **Where:** `context` @ `72e2702` · merged to `main`: this file only
- **Did:** Grouped roles as AI/ML (Saliha), Robotics and robot learning (Nate), Systems and integration (Harry) in the PRD §1b, briefs and CLAUDE.md. Renamed the branches. Added `decisions.md` (17 decisions, pitch cheat sheet) and CLAUDE.md §4a: agents update it autonomously.
- **Touched:** `prd.md`, `decisions.md`, briefs, `CLAUDE.md`, `progress.md`
- **Brief task:** none
- **⚠️ Conflicts:** @nate @harry: use the new branch names; add decision entries for your areas as you build
- **📨 Needs:** none
- **Status:** open

### 2026-11-14 01:00 — scope — PRD v2.3: team vision, personality layer, Nemotron in, F16 dropped, branches renamed — @saliha [conflicts: @nate @harry]
- **Where:** `context` @ `b423fc4`; `main`: this file + `.gitignore` · merged to `main`: yes
- **Did:** Wrote the agreed vision into the PRD (§1a priority order), the briefs and CLAUDE.md. New: live reasoning voice + cowboy persona switch (F7, F18), Nemotron reasoner (F17), Aiven Kafka streaming (F15), stretch list (PRD §8a). Dropped: F16 Modal dashboard. Added a `.gitignore` so only `progress.md`, `README.md` and the brief-named markdown reach `main`.
- **Touched:** `prd.md`, all three briefs, `CLAUDE.md`, `.gitignore`, `progress.md`
- **Brief task:** none
- **⚠️ Conflicts:** @harry: you now own the persona state machine (A6b), calm + cowboy voices, Kafka streaming; F16 is gone; three contract lines added to PRD 7.3 before the 01:00 freeze. @nate: branch renamed to `robotics-policies-nate`; obstacles are skipped, never picked
- **📨 Needs:** @harry: yes or no on the PRD 7.3 additions before 01:00
- **Agreed by:** @saliha (doc owner, vision from the team chat); teammates asked on the Open board
- **Status:** open

### 2026-11-14 00:35 — scope — PRD v2.2: Junction page rubric, side-track criteria, new features — @saliha [conflicts: @nate @harry]
- **Where:** `context` @ `84364a8` · merged to `main`: n/a (docs)
- **Did:** Read the Junction challenge page, the kickoff slides and the Aiven/Modal/NVIDIA pages. The page scores task success 30, Intel integration 30, dataset quality 20, efficiency (latency, power, thermal) 20, so features F11–F16 cover that, plus F4 re-grasp. NVIDIA Nemotron (F17) is pending.
- **Touched:** `prd.md`, all three briefs, `CLAUDE.md` registry
- **Brief task:** none
- **⚠️ Conflicts:** @nate: new A4b, A8, recording-protocol additions, F11 sweep at 12:30, F14 trials. @harry: new A2b shared capture, more Aiven tables, F15 drift alarm, optional F16
- **📨 Needs:** @nate @harry: agree `reinspect` semantics before 01:00
- **Agreed by:** @saliha (doc owner); teammates asked on the Open board
- **Status:** open

### 2026-11-14 00:10 — docs — Charter, PRD, briefs and skills on `context`; this board on `main` — @saliha [conflicts: @harry]
- **Where:** `context` + `main` · merged to `main`: yes (this file only)
- **Did:** Set up the workflow docs: `CLAUDE.md`, `prd.md` (v2.1: four small contradictions fixed, see PRD §0), three
  builder briefs and the `no-slop` + `debug` skills on `context`. This board on `main`.
- **Touched:** `progress.md`; `context` branch
- **Brief task:** none
- **⚠️ Conflicts:** @harry: your A1 assumed you create the repo and `progress.md`; both exist now. The rest of A1 is yours
- **📨 Needs:** none
- **Status:** open
