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
| 2026-11-14 01:42 | @nate | @all | ❓ question | **Which clock do our plan times use?** Board stamps so far track UTC (the 00:10 entry was committed at 00:07 UTC), but Espoo is UTC+2 and Saliha's commits since 03:11 carry +02:00. If the plan runs on UTC, our 09:00 internal submit is 11:00 in Espoo, after a 10:00 Espoo deadline. (My laptop is on UTC.) | 2026-11-14 01:42 |
| 2026-11-14 01:35 | @nate | @harry @saliha | ⚠️ conflict | **`reinspect` meaning agreed by @nate (Saliha's proposal):** `0` = put the brick down in the pick zone and pick it again, `±90` = wrist roll in place; returns `True` only when the brick is back at the inspection pose. Signature unchanged. @harry: `fallback/` implements the same meaning; yes or no on the 00:35 row. @saliha: once @harry agrees, mirror it into PRD 7.3 / §0 and Harry's brief | 2026-11-14 01:35 (@nate) |
| 2026-11-14 01:35 | @saliha | @all | ⚠️ conflict | **Branches renamed again, by discipline:** `aiml-perception-saliha`, `robotics-policies-nate`, `systems-voice-harry` (older rows below use the previous names; none were pushed yet). New file **`decisions.md`** on `context` (design choices and why, for pitching): your agent updates it on its own as you build (CLAUDE.md §4a). Re-sync from `context` | 2026-11-14 01:35 |
| 2026-11-14 01:00 | @saliha | @all | 🔀 scope proposal | **PRD v2.3 on `context` (`b423fc4`), re-sync.** The team vision is now written in: Intel task first (accurate, smooth, quick); then the robot **explains its reasoning out loud live** (Nemotron writes, ElevenLabs speaks) and an **obstacle or cowboy hat flips it into a cowboy persona**. NVIDIA Nemotron is in (@saliha, `reasoner/`). Aiven = Kafka streaming → PostgreSQL (@harry). Modal = training + logs only; the F16 dashboard is dropped (no frontend). **Branches renamed, one per person:** `aiml-perception-saliha`, `robotics-policies-nate`, `systems-voice-harry`. Contract additions in PRD 7.3 (`narrator.trigger`, `reasoner.explain`, `reasoner.hat_seen`) need @harry's yes before the 01:00 freeze. **@nate 01:42: yes** | 2026-11-14 01:00 |
| 2026-11-14 00:35 | @saliha | @all | 🔀 scope proposal | **PRD v2.2 on `context` (`84364a8`), re-sync.** New 🆕 items in every brief from the Junction challenge page + side-track pages: F11 demo-count sweep on Modal (@nate), F12 power/energy/thermal benchmark (@saliha), F13 shared cameras (@harry), F14 shifted + pile trials (@nate @harry), F15 Aiven drift alarm + more tables (@harry), F16 optional Modal dashboard (@harry), F4 now includes a re-grasp. Object = Duplo, cameras = top + inspection + wrist. Say no on this row if you object to any item in your brief. **@nate 01:42: yes** | 2026-11-14 00:35 |
| 2026-11-14 00:35 | @saliha | ~~@nate~~ @harry | 📨 waiting on | Before the 01:00 freeze, agree what `Mover.reinspect(angle_deg)` does now that F4 includes a re-grasp (proposal: `0` = put down and pick again, ±90 = wrist roll). **@nate 01:35: yes** (see the Log) | 2026-11-14 00:35 |
| 2026-11-14 00:10 | @saliha | @harry | ⚠️ conflict | The repo already exists (`saliha006/Chooms-chrome`, `main` has `README.md` + this file). Your A1 still owns: MIT licence, folders per PRD §10, `Makefile`, `common/interfaces.py`. Pull before you push | 2026-11-14 00:10 |
| 2026-11-14 00:10 | @saliha | @all | ⚠️ conflict | **How docs work:** plan docs live on the `context` branch, never `main`. Set up once with 🚀 Start here below. Role branches: `perception-saliha`, `robot-nate`, `integration-harry`. Send @saliha your GitHub handle | 2026-11-14 00:10 |
| 2026-11-14 00:10 | @saliha | @all | ❓ question | PRD §13 open questions for the mentors (Sat 08:00–09:00), incl. whether 11:50 Sunday is our demo slot and which clock the 10:00 deadline is on | 2026-11-14 00:10 |

**Kinds:** ⚠️ conflict (my change touches your work) · 📨 waiting on (I'm blocked until you do X) · 🔀 scope proposal (needs
the whole team's yes, CLAUDE.md §2c) · ❓ question for a teammate (project-wide unknowns go in PRD §13).

## 👥 Team
Full ownership and tasks live in each builder's brief (`builder-briefs/builder-brief-<name>.md` on `context`). Update your
own **Now** cell whenever you log an entry.

| Who | GitHub | Role | Branch | Owns (paths) | Now |
|---|---|---|---|---|---|
| Saliha | `saliha006` | **AI/ML**: computer vision (Anomalib), edge-AI optimisation (OpenVINO), Nemotron reasoner; doc owner | `aiml-perception-saliha` | `perception/`, `bench/`, `reasoner/` | Block A: perception pipeline on stand-in images |
| Nate | `aldrichbanas07` | **Robotics and robot learning**: robot I/O, imitation-learning policies (ACT, SmolVLA), Modal training + logs | `robotics-policies-nate` | `robot/`, `policies/`, `train/` | Block A: `reinspect` agreed (waiting on @harry); next the Modal script and `MockRobot` |
| Harry | `{{github}}` | **Systems and integration**: orchestration, ElevenLabs voice (live reasoning + cowboy switch), Aiven streaming, demo, submission | `systems-voice-harry` | `run.py`, `common/`, `fallback/`, `ui/`, `narrator/`, `telemetry/`, `config/`, `README.md`, `docs/` | Block A: repo layout, interfaces, mock loop, voices |

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
- **`main` (2026-11-14 00:10):** `README.md` + `progress.md` only; no code yet. Plan docs on `context`.

---

## Log (newest first)

### 2026-11-14 01:35 — decision — `reinspect` agreed: `0` = re-grasp, `±90` = wrist roll — @nate [conflicts: @harry @saliha]
- **Where:** `context` @ `c67ba2b` (Nate's brief, `decisions.md` D7) · merged to `main`: this file only
- **Did:** Said yes to Saliha's proposal. `Mover.reinspect(0)` puts the brick down in the pick zone and picks it again (the F4 re-grasp); `reinspect(±90)` rolls the wrist in place; both return `True` only when the brick is back at the inspection pose. The PRD 7.3 signature is unchanged. Also filled my GitHub handle (`aldrichbanas07`) in my brief and 👥 Team. At 01:42 also said yes to the PRD v2.2 and v2.3 items in my brief (A8 sweep, F14 held-back and pile trials, recording additions, obstacles skipped).
- **Touched:** `builder-briefs/builder-brief-nate.md`, `decisions.md` (D7), `progress.md`; no code yet
- **Brief task:** A4b → 🟡 part (waiting on @harry)
- **⚠️ Conflicts:** @harry: `fallback/scripted.py` gives `reinspect` the same meaning (a put-down waypoint then pick again; wrist roll ±90°). @saliha: your F4 chain calls `reinspect(0)` for the re-grasp and `reinspect(±90)` for the roll, as your brief already says
- **📨 Needs:** @harry: yes or no on the 00:35 Open board row. @saliha: once @harry agrees, mirror it into PRD 7.3 / §0 and Harry's brief
- **Agreed by:** @nate, @saliha (proposed it); @harry asked
- **Status:** open

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
