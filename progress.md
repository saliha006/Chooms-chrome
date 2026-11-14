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
| 2026-11-14 00:35 | @saliha | @all | 🔀 scope proposal | **PRD v2.2 on `context` (`84364a8`), re-sync.** New 🆕 items in every brief from the Junction challenge page + side-track pages: F11 demo-count sweep on Modal (@nate), F12 power/energy/thermal benchmark (@saliha), F13 shared cameras (@harry), F14 shifted + pile trials (@nate @harry), F15 Aiven drift alarm + more tables (@harry), F16 optional Modal dashboard (@harry), F4 now includes a re-grasp. Object = Duplo, cameras = top + inspection + wrist. Say no on this row if you object to any item in your brief | 2026-11-14 00:35 |
| 2026-11-14 00:35 | @saliha | @nate @harry | 📨 waiting on | Before the 01:00 freeze, agree what `Mover.reinspect(angle_deg)` does now that F4 includes a re-grasp (proposal: `0` = put down and pick again, ±90 = wrist roll) | 2026-11-14 00:35 |
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
| Saliha | `saliha006` | Perception, AI/ML, OpenVINO; doc owner | `perception-saliha` | `perception/`, `bench/` | Block A: perception pipeline on stand-in images |
| Nate | `{{github}}` | Robot and policies (Studio, ACT, SmolVLA, Modal) | `robot-nate` | `robot/`, `policies/`, `train/` | Block A: Modal script + policy export test |
| Harry | `{{github}}` | Integration, demo, side tracks (ElevenLabs, Aiven), submission | `integration-harry` | `run.py`, `common/`, `fallback/`, `ui/`, `narrator/`, `telemetry/`, `config/`, `README.md`, `docs/` | Block A: repo layout, interfaces, mock loop |

**Shared** (anyone may edit; flag it in ⚠️ Conflicts): `progress.md` (on `main`), `Makefile` (Harry creates it). Plan docs
on the `context` branch (`CLAUDE.md`, `prd.md`, `builder-briefs/`): doc owner publishes (CLAUDE.md 📤); your own
`handoff/<name>.md`: you.

## 🚀 Start here (new teammate, first 15 minutes)
1. Clone `https://github.com/saliha006/Chooms-chrome`. Set `git config user.email` to your GitHub email (commits are
   credited by author) and `git config team.builder <your-name>` (the agents and the Open board use it).
2. Keep plan docs out of code commits: `printf '%s\n' CLAUDE.md AGENTS.md prd.md builder-briefs/ skills/ handoff/ .claude/ .env >> .git/info/exclude`.
3. Pull the docs from `context` (they never live on `main`): `git fetch origin context && git archive origin/context | tar -x
   && git rev-parse origin/context > .git/context-synced`. Install the skills: `mkdir -p .claude/skills && cp -r skills/* .claude/skills/`.
   Then `git switch -c <your role branch>`.
4. Put the `.env` @saliha or @harry sends you (directly, not via git or chat) at the repo root. Never commit it; never paste a key.
5. Tell your agent "fetch the context": it reads `CLAUDE.md`, PRD §0 and your brief.
6. Read your brief's `▶ Current tasks`, then the 📌 Open board above.

## 📊 Latest (volatile facts live only here)
- **Plan (2026-11-14 00:35):** PRD v2.2 on `context` @ `84364a8`.
- **`main` (2026-11-14 00:10):** `README.md` + `progress.md` only; no code yet. Plan docs on `context`.

---

## Log (newest first)

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
