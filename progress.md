# SortSense (Junction 2026): progress log and conflict board

The team's shared history: who shipped what, when, on which branch, whose work it touches, and who is waiting on whom.
The plan itself is `CLAUDE.md`, `prd.md` and `builder-briefs/` on the `context` branch; this file is the history.

> **Template.** Fill `{{…}}` as the project's details arrive (self-filling rule, `CLAUDE.md`).

## How this file works (read once)
- **Newest first.** A new entry goes at the top of the Log. Stamps are `YYYY-MM-DD HH:MM` on the plan clock (PRD §10),
  so top to bottom is newest to oldest.
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
| 2026-11-14 04:16 | @harry | @saliha | 📨 waiting on | **Conversational live lines + `reinspect` mirror.** (1) Please make the Nemotron live lines (F17, `reasoner/`) conversational: the robot thinks aloud like a person (what it sees, what the score means, what it will do and why), short enough to speak in a few seconds; voices are calm `etWmxTqEKhIYyGKMpDcb` and cowboy David `0hh7H4ZVAtaGpm1VZyEN` (D12, D13). (2) @harry agreed `reinspect` at 04:16: mirror it into PRD 7.3 / §0 and Harry's brief as Nate's 01:35 entry asks | 2026-11-14 04:16 |
| 2026-11-14 01:42 | @nate | @all | ❓ question | **Which clock do our plan times use?** Board stamps so far track UTC (the 00:10 entry was committed at 00:07 UTC), but Espoo is UTC+2 and Saliha's commits since 03:11 carry +02:00. If the plan runs on UTC, our 09:00 internal submit is 11:00 in Espoo, after a 10:00 Espoo deadline. (My laptop is on UTC.) | 2026-11-14 01:42 |
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
| Nate | `aldrichbanas07` | **Robotics and robot learning**: robot I/O, imitation-learning policies (ACT, SmolVLA), Modal training + logs | `robotics-policies-nate` | `robot/`, `policies/`, `train/` | Block A: `reinspect` agreed (waiting on @harry); next the Modal script and `MockRobot` |
| Harry | `Harryt3nn` | **Systems and integration**: orchestration, ElevenLabs voice (live reasoning + cowboy switch), Aiven streaming, demo, submission | `systems-voice-harry` | `run.py`, `common/`, `fallback/`, `ui/`, `narrator/`, `telemetry/`, `config/`, `README.md`, `docs/` | Block A: A1 done (`common/interfaces.py` on `main`); next A2 configs + mocks |

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
- **perception (2026-11-14 03:55):** `main` @ `dd1c4d7`: 28 tests pass (4 slow). Not yet run on the Intel laptop or real bricks.
- **`main` (2026-11-14 00:10):** `README.md` + `progress.md` only; no code yet. Plan docs on `context`.

---

## Log (newest first)

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
- **Status:** open

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
