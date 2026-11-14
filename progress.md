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
| 2026-11-14 05:15 | @saliha | @nate | 📨 waiting on | **Your Block A code is on `main` (`ac2e2f2`)**: review it; then `modal token new`, add a Modal secret `huggingface` (HF_TOKEN), run the A2 smoke (`modal run train/modal_train.py --dataset lerobot/svla_so100_pickplace --steps 200`) and the A3 export test on those checkpoints. Pick the 🟠 in `train/RECORDING.md` | 2026-11-14 05:15 |
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
| Nate | `aldrichbanas07` | **Robotics and robot learning**: robot I/O, imitation-learning policies (ACT, SmolVLA), Modal training + logs | `robotics-policies-nate` | `robot/`, `policies/`, `train/` | Block A code on `main` (written by Saliha's agent); next: Modal login + smoke run, export test |
| Harry | `Harryt3nn` | **Systems and integration**: orchestration, ElevenLabs voice (live reasoning + cowboy switch), Aiven streaming, demo, submission | `systems-voice-harry` | `run.py`, `common/`, `fallback/`, `ui/`, `narrator/`, `telemetry/`, `config/`, `README.md`, `docs/` | Block A: A1–A3, A7 done (scripted fallback + teach tool); next real-hardware mode in `run.py`, A4 mission control, A5 Aiven |

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
- **Plan (2026-11-14 01:35):** PRD v2.4 + `decisions.md` on `context` @ `c67ba2b` (Nate's brief and `decisions.md` D7 updated).
- **robot/policies/train (2026-11-14 05:15):** `main` @ `ac2e2f2`: whole suite 55 pass (4 slow skipped); Modal not yet run.
- **perception (2026-11-14 04:30):** `main` @ `99f1d09`: 28 tests pass (4 slow); live Nemotron line 1.7–2.7 s. Not yet run on the Intel laptop or real bricks.
- **`main` (2026-11-14 00:10):** `README.md` + `progress.md` only; no code yet. Plan docs on `context`.

---

## Log (newest first)

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
