# Junction 2026 — Working Charter

**SortSense** is a closed-loop defect-sorting robot with a personality. An SO-101 follower arm picks a Duplo brick and shows it to the inspection camera (ACT policy), Anomalib scores it perfect, defective or uncertain, and SmolVLA (a vision-language-action model) places it in the purple bowl (perfect) or the orange bowl (defective), all on an Intel Core Ultra X9 388H with OpenVINO, each model on the NPU, GPU or CPU on purpose. **The Intel task comes first, done accurately and smoothly.** On top, the robot explains its reasoning out loud, live, in a calm voice (Nemotron writes the line, ElevenLabs speaks it), and an obstacle or a cowboy hat flips it into a cowboy persona ("Holy smokes!") until the moment passes. *(Mirror of PRD §1 / §1a; change both together.)*

`{{…}}` is a blank: fill it the moment the chat or repo answers it (Self-filling, below). "The PRD", "the brief", "the research doc", "the doc owner" are the Registry values. A teammate on Codex: `cp CLAUDE.md AGENTS.md` locally (never committed separately; `CLAUDE.md` is the source).

## 📋 Registry

| Slot | Value |
|---|---|
| Project | **SortSense** · **Junction 2026**, Espoo, 13–15 Nov 2026. Main track **Intel x Ignite Next: Physical AI** (scored /100 by Intel; two rubrics, PRD §2 and §2a). Side tracks: **ElevenLabs** (MLH; live reasoning voice + cowboy switch), **NVIDIA Nemotron 3.5 Super VL** (the reasoning brain), **Aiven** (Kafka event streaming → PostgreSQL), **Modal** (training + logs only; **no frontend ever**, drop Modal before building one). Nothing else. Feature freeze **Sat 23:00**; internal submit **Sun 09:00**; official deadline **Sun 15 Nov 10:00** (all times Espoo local, EET = UTC+2; decided 2026-11-14 04:30). Demo slot {{11:50 Sunday? confirm with mentors}}. Team name {{team name}} |
| Team | **saliha** (`saliha006`): **AI/ML** = computer vision (Anomalib), edge-AI optimisation (OpenVINO), Nemotron reasoner (`perception/`, `bench/`, `reasoner/`), **doc owner**, vault owner · **nate** (`aldrichbanas07`): **robotics and robot learning** = robot I/O, imitation-learning policies, Modal training (`robot/`, `policies/`, `train/`) · **harry** (`Harryt3nn`): **systems and integration** = orchestration, ElevenLabs voice, Aiven streaming, demo (`run.py`, `common/`, `fallback/`, `ui/`, `narrator/`, `telemetry/`, `config/`, `README.md`, `docs/`). Owned paths and **Now**: `progress.md` → 👥 Team |
| Repo | `https://github.com/saliha006/Chooms-chrome` · `main` (code + `progress.md` + `.gitignore`) · `context` (plan docs only) · **one branch per person, `<what you build>-<name>`:** `aiml-perception-saliha`, `robotics-policies-nate`, `systems-voice-harry`. A second agent in a worktree uses `<branch>-<task>` and merges back into that person's branch |
| Where docs live | **`context` branch** (docs only, **never merged to `main`**): `CLAUDE.md`, `prd.md`, **`decisions.md`** (design choices and why, for pitching), `builder-briefs/builder-brief-<name>.md`, `skills/` (`no-slop`, `debug`), `handoff/<name>.md` (agent handoff notes). **`main`**: code, `progress.md`, `README.md` and the code-adjacent markdown the briefs name (`bench/results.md`, `train/RECORDING.md`, `train/runs.md`, `train/rejected.md`, `docs/`); the `.gitignore` on `main` blocks every other `.md`. **Local only, never committed:** `.claude/`, `.env*`, `Research-Context/`, `intel track & others/`, `neuron/`, `saved for later + agents/` (overflow ideas and multi-agent notes; read only when the user says so), datasets, checkpoints, `runs/` |
| Secrets | `.env` at the repo root on each machine, git-ignored: `ELEVENLABS_API_KEY`, `NVIDIA_API_KEY`, `AIVEN_KAFKA_*` / `AIVEN_PG_URI` {{exact Aiven names}}, `NEMOTRON_MODEL` (exact Super VL id), `HF_TOKEN`, Modal token {{name}}. **Keys are used, never shown:** code loads them with `python-dotenv` or the environment; to check one exists, test presence only (`grep -c '^NVIDIA_API_KEY=' .env`), never `cat`, `echo` or print a value; never paste a key into chat, docs, commits, logs or memory. Keys are shared person to person, never through git |
| Vault | `C:\Users\Salih\OneDrive\Documents\Sali's vault\Choom's chrome` (**saliha only**: `Choom's chrome — Hub` = status + ▶ START HERE, `Choom's chrome — Log` = ADRs, Unconfirmed, ▶ RESUME HERE; `_reference/` = private notes). Saliha's personal task context goes here, never on `context`. No vault (everyone else) → save notes to your agent's memory; send decisions to the doc owner as a `decision` entry + 📨 row |
| PRD | `prd.md`: §0 NOW (decisions in force, pending, active gates) at the top, then the spec |
| Briefs | `builder-briefs/builder-brief-<name>.md`: `saliha`, `nate`, `harry` |
| Event doc | `Research-Context/Junction2026-CONTEXT.md` (local only; create when rules, judging or side-track criteria are pasted) |
| Research doc | `Research-Context/Junction2026-research.md` (local only; create on the first pass). A pass is deleted once the feature it serves is on `main` (§10) |
| Progress doc | `progress.md` on `main`: 📌 Open board, 👥 Team, 📊 Latest, Log |
| Decisions | **Team-visible, pitch-ready: `decisions.md`** (updated autonomously, §4a). Saliha's personal ADRs: vault Log. Team mirror: PRD §0 NOW. Contract changes (`common/interfaces.py`, `robot/io.py`): a `decision` entry in `progress.md` first, then PRD §7.3 |
| Mirror docs | PRD §0/§1 ↔ top of this file; `decisions.md` ↔ PRD §8 features and §0 decisions; briefs ↔ `progress.md` 👥 Team; vault Hub + Log; `progress.md` 👥 Team + 📊 Latest. Update every mirror when a decision, owner or status changes |
| Run · Test | Python **3.12** venv (perception; policy training runs on Modal GPUs, not the laptop): `uv venv --python 3.12 .venv && uv pip install --python .venv -r perception/requirements.txt` · Tests: `pytest perception bench reasoner` (`-m "not slow"` skips the ~3 min end-to-end training tests) · On Windows set `PYTHONUTF8=1` · Mock loop: `make mock` (`python run.py --mock`) · Real loop: `make run` · Rebaseline: `make rebaseline` (`python -m perception.rebaseline`) · Benchmark: `python -m bench.benchmark` |
| Hardware | Intel laptop (Core Ultra X9 388H, Ubuntu 26.04, NPU + iGPU) = the only runtime; reach it by SSH + tmux (one window per person). SO-101 **follower moves; the leader is teleop only, never driven**. Cameras: **top view** + **inspection** (the RealSense D415 is `top`) + wrist cam, by `/dev/v4l/by-id` paths in `config/cameras.yaml`, shared between policy and inspector (PRD F13). Objects: **Duplo** bricks, defects drawn by us with markers. **One robot user at a time** (PRD §10 slot table) |
| Scale | One live demo table; 20 logged trials (PRD §3) |
| Deploy | On-device on the Intel laptop; no web deploy (non-goal) |
| Verbosity | **Level 0** (§3) |

**Skills** (shared on `context` in `skills/`; after each sync move them to where Claude loads them: `mkdir -p .claude/skills && cp -r skills/* .claude/skills/ && rm -rf skills`; Codex reads `.claude/skills/<name>/SKILL.md`; load when the trigger fires). Always-on skills: `no-slop` after every code change, before testing, and before every commit/push/merge (nothing reaches `main` without it) · `debug` every time you hit an issue: an error, a failing or flaky test, odd output, a stuck moment, a robot or camera misbehaving. No guess-and-retry outside it. This file wins over a skill; never edit a skill. `no-slop` fixes only your own diff in your owned paths and reports the rest.

### 🔑 Triggers
**"Fetch the context"** (*"let's start"*). Read first, code second:
1. **Who am I working with?** `git config team.builder`; unset → ask the user's name and set it. Read **only** your brief's `▶ Current tasks`, Ownership and Seams, plus `handoff/<name>.md` if it exists (a previous agent left notes).
2. **Decisions + tasks:** run the Context sync, then PRD §0 NOW and only the PRD sections your brief names.
3. **Local vs repo:** does the tree match `origin/main` and your branch? Note what's shipped vs local-only.
4. **Board:** `progress.md` Open board rows To you + the Log top (sync step 5).
5. **Vault** (if set): Hub ▶ START HERE and Log ▶ RESUME HERE; name its "Unconfirmed" items so nothing sits unconfirmed forever.
Then give one clear starting point and proceed.

**"What's next" / "what's left"**: your brief's `▶ Current tasks` is the ranked list (PRD §10 slot table for the team view). Work the top open item unless told otherwise; drive every 🟠 part through §1; mark it done in the brief and `progress.md` when it moves. Behind schedule → the gates in PRD §10 decide what falls back to scripted. **Cut order** (cut from the top): 1 AnomalyDINO, 2 Aiven drift alarm, 3 persona switch, 4 rule-text compiler, 5 Nemotron advisory, 6 demo-count sweep (F11), 7 repeatability test (PrePostProcessor: built 2026-11-14, D30; live voice line: built and on `main` 2026-11-14 17:00, Harry's proposal, Nate yes, D12; neither is cuttable). **Never cut:** the state machine with deadlines, grasp and place verification, the localisation gate, the scripted fallback, the 20-trial log, the detector evaluation. Nothing active left → offer the parked ideas (§4).

**"Handoff"** (usage limit near, or the human says it): append to `handoff/<name>.md`: **Done · In progress (file, function, what's left) · Next step · Gotchas · Commands to run**. Max ~15 lines. Publish it to `context`. Then stop; the next agent reads it.

**"Start the demo" / "run the demo" / anything demo-related**: follow PRD §11 (demo script, 2:00) on the Intel laptop. Steps: home pose check → `make rebaseline` if the lighting or table changed → `make run` → press **S**. **E** = e-stop (torque off), **P** pause, **Q** home and quit. Backup video on a second screen. Change the demo path only on the user's say-so.

### 🛠 Station debugging (Intel laptop; Saliha, 2026-11-14)
Read the real log first (Studio: the terminal it runs in, or `~/work/studio-backend.log`; kernel: `sudo dmesg`), find the *first* error, reproduce the device outside the app (pyserial for an arm, pyrealsense2 or OpenCV for a camera), then fix the narrowest layer.
- **"Permission denied: /dev/ttyACM*"**: a group added with `usermod` only reaches new logins. Fixed for good by `/etc/udev/rules.d/99-so101-arms.rules` (`SUBSYSTEM=="tty", ATTRS{idVendor}=="1a86", ATTRS{idProduct}=="55d3", MODE="0666"`). Check a process's groups with `grep Groups /proc/<pid>/status`.
- **Studio camera "no publisher responded within timeout"**: stop Studio, `rm -rf /tmp/iceoryx2 /dev/shm/iox2_*`, start it again; also check the camera still exists (`ls /dev/v4l/by-id/`), because a re-plugged camera gets a new `/dev/videoN`.
- **Arm "Sync read failed with comm result -6"** or cameras dropping out in `dmesg`: USB power or a tugged cable (powered hub; RealSense and wrist camera straight on the laptop), not code.
- **"Servo ID 1 did not respond" / all six motors silent while the USB board still shows up:** the arm's power plug or the board → base-motor cable is out (2026-11-14: the leader's plug). Ping read-only before blaming software.
- **One owner per port:** Studio (an open robot page or session) and our scripts can't hold an arm at the same time; leave the Studio page before `fallback.teach` or `run.py`.
- **Agent traps:** `printf pw | sudo -S tee file` writes an empty file (use `sudo -S sh -c 'echo ... > file'`); `pkill -f <pattern>` kills the agent's own shell when the pattern is in its command line. Don't start Studio's backend from an agent session unless asked; never store a sudo password.

### 🔄 Context sync (session start, before each new brief task, and before editing a shared doc)
Never work from a stale plan: fetch fresh context at least at those three points (and every ~30 min in a long task). Plain git, no scripts. The synced commit is kept in `.git/context-synced`.
1. `git fetch -q origin context`. If `git rev-parse origin/context` equals the stamp (`cat .git/context-synced`), you're current.
2. Else tell the user in 1–2 lines **first** (`git log --oneline <stamp>..origin/context`, `git diff --stat <stamp> origin/context`). A shared doc you edited but haven't published: copy it aside before unpacking.
3. Unpack: `git archive origin/context | tar -x`, then `git rev-parse origin/context > .git/context-synced` and move the skills into `.claude/skills/` (above). A changed `CLAUDE.md` is already loaded: act on the changed lines only. Read at least PRD §0 NOW and your own brief.
4. Never `git checkout origin/context -- <file>` (it stages docs into your code branch). Fetch fails → say so in one line, use local copies, and say any board check was local-only.
5. Board: `git fetch -q origin main`, then read the Open board rows To you and the Log top: `git show origin/main:progress.md | sed -n '/Open board/,/^## 👥/p;/^## Log/,+40p'`.

### 🪙 Token budget (the limit burns on re-sent context)
Every request re-sends the whole conversation, so one big read is paid again on every later call. Cost = tool calls × context size: batch independent calls, keep prompts specific, keep big text out of the context.
- **Read only what the task needs:** `Grep`, or `Read` with `offset`/`limit`. `CLAUDE.md` is already loaded. Read PRD §0 and your brief once per session. Never read all of `progress.md`: Log top only (sync step 5).
- **Never `Read`:** a research agent's raw output, a session transcript (`.jsonl`), image folders, training logs in full, a whole `Research-Context/` note or the research doc (grep it by pass number).
- **Agents are for research (§10) or when the user asks**; everyday edits stay in the main session. Research agents write to files and report ≤300 words; at most 4 unless the user asks for more.
- **Max 2 coding agents per person at once, on disjoint files, each in its own git worktree.** One model and effort per session; new task → `/clear`; `/compact` past ~100k tokens.

### 📤 Publish every shared-doc edit (same turn)
Shared docs = everything on `context`: `CLAUDE.md`, `prd.md`, `decisions.md`, `builder-briefs/`, `handoff/` (and `skills/`, which nobody edits). Publish **any** edit to them before ending the turn (yours, or one the user made by hand) so every teammate's agent gets it on its next sync. Plain git from the repo root through a temporary index, no worktree, no branch switch:
1. Sync first (above).
2. `export GIT_INDEX_FILE=.git/context-index && git read-tree origin/context && git add -f CLAUDE.md prd.md decisions.md builder-briefs && git diff --cached --stat origin/context` (add `handoff` once it exists; skills are never edited, so they stay as they are on `context`). Check the diff, and for secrets. A removed doc: `git rm --cached <path>` in the same index. 
3. `c=$(git commit-tree $(git write-tree) -p origin/context -m "<short human message>") && unset GIT_INDEX_FILE && git push origin $c:refs/heads/context`, then `git fetch origin context && git rev-parse origin/context > .git/context-synced`. Rejected → sync, merge the two versions by hand, repeat; never `force`.
Research, the event doc, the vault, `.claude/` and `.env` never go to `context`. Context docs never go to `main` or a role branch: never `git add -f` there, never copy them into a code commit, never merge `context` anywhere.

| Change | Who publishes | Gate |
|---|---|---|
| PRD, `CLAUDE.md`, another builder's brief | **Doc owner** | Plan changes need the team's yes (§2c); a builder posts the agreed change as a 🔀/📨 row To the doc owner |
| Contracts in PRD §7.3 (`common/interfaces.py`, `robot/io.py`) after the 01:00 Sat freeze | Doc owner (+ Harry edits the file) | All three humans agree; `decision` entry in `progress.md` first (§6) |
| Your own brief: add or change tasks, features or decisions in your area | You | Always ask "have you told the team? who agreed?" first (§2c) |
| Your own brief: ownership, or anything another builder depends on | Doc owner | The affected owner's yes (§2c) |
| Your own brief: finished task to Done, blank filled with a stated fact | You | None |
| `decisions.md` | **Any agent, autonomously**: add or update the entry for what you decided or built, then publish | None; facts and measured numbers only (§4a) |
| Your own `handoff/<name>.md` | You (publish to `context`) | None |
| `progress.md` (on `main`) | Anyone: your entries and rows; annotate others | None |

### 🔁 Self-filling rule
- **Watch for missing info.** When the user says something (or the repo shows something) that answers a blank (path, name, command, URL, stack choice, teammate), fill that `{{…}}` everywhere it belongs: this file, `progress.md`, the PRD, the briefs.
- **Fit, don't grab.** Only an empty blank filled with a stated fact is free; changing a filled plan value is §2c. A passing mention ("maybe PatchCore") goes to the vault Log as *not finalized* and PRD §0 Pending, not into the spec. Don't fill several slots with the first thing you hear.
- **Say what you filled**, in one line: "Filled Repo = `https://github.com/…`."
- **Unsure which slot → ask one short question** (§12). One question beats a wrong slot.
- **Missing files get created:** no `progress.md`, PRD, brief, handoff note or research doc when a rule needs it → create it from the starter.

---

## 0. THE ONE RULE — the user owns every design decision, Claude owns the typing
The person at the keyboard (named in their brief; "the user" here) wants to be a real software engineer: someone who **decides what to build and why** and uses AI to write the code, not an "AI prompter" who accepts whatever the model picks. This file enforces that split.

**A design decision is any choice a real SWE would pause on**: not the syntax, the *shape*. If a task contains one, **don't silently pick.** Stop, hand it over (§1), wait. Claude proposes and explains; the user disposes. Even with a strong recommendation, the choice is logged as theirs (§4), because owning the *reasoning* is the skill being built. **The brief already made many calls** (PRD + `▶ Current tasks`): implementing those is 🟢, not a new decision.

## 1. Decision Handoff
When you hit a design decision, stop coding and surface it like this:
> **🟠 DECISION — <name>** *(your call)*
> **What's being decided:** one plain sentence.
> **Options:** 2–4 realistic ones, no strawmen: **A — <name>:** what · ✅ upside · ⚠️ cost/risk.
> **My recommendation:** X, because … (tie it to the PRD section, the research doc by pass, or a concrete failure mode: a broken demo beat, a missed gate, a lost judging criterion).
> **🧭 What this entails** *(§3 depth; omit at Level 0)*
> **What I need from you:** pick A/B/…, or "you decide".

Then **wait**: no implementation until they pick, and log it the moment they do (§4). Keep the ask clean: short bullets, whitespace. Several decisions → separate titled blocks in a queue.

## 2. Whose call
**System design choices** are owned by the area's owner (👥 Team); a cross-area choice needs all three. Show the owner the options; others hear through a 📨 row.

**🟠 Always the user's** (stop and hand off):
- **Data & storage:** what's captured and kept (datasets, held-out split, thresholds in `perception/thresholds.yaml`, checkpoints, the Aiven `events` table, JSONL buffers), where, and for how long.
- **Interface contracts:** PRD §7.3 (`DefectSignal`, `Inspector`, `Mover`, `robot/io.py`, `narrator.say`, `telemetry.log`), `config/rules.yaml` semantics: what a caller can rely on.
- **Trust & access:** API keys (ElevenLabs, Aiven, HF, Modal) never in code or logs; what leaves the laptop (control and inference never touch the network).
- **Where computation runs:** NPU vs GPU vs CPU per workload (PRD §7.2), on-device vs Modal, inference on or off the control thread.
- **Failure modes:** NPU compile fails, export bugs, NaNs, uncertain detections, failed grasps, camera path changes, network down; the fallback chain for each.
- **Robot motion and safety:** anything that moves the arm, changes speed caps, joint limits or the e-stop path. Follow the printed safety guidelines.
- **Adding any dependency, library, framework or service**: every one is a long-term liability.
- **Anything touching a Locked Decision** (§6).
- **Correctness vs speed vs cost:** model choice (PaDiM / PatchCore / EfficientAd), precision (FP16 vs INT8), thresholds marked (TUNE), Modal GPU spend.
- **Anything the PRD flags as a demo-vs-product gap** (stand-in data, scripted fallback shown as learned, untested numbers).

**🟢 Just do it** (say what and why in one line): bug with exactly one correct answer · zero-behaviour refactor · implementing a decision already made (don't re-litigate it) · tests for existing behaviour · formatting, typos, comments, `no-slop` cleanups · correct-shaped stubs and mocks the brief asks for ("stubs first, real later").

**Unsure which → treat it as 🟠.** Erring toward handoff is how the user learns; a silent choice is the failure this file exists to prevent.

### 2a. Work for a teammate
A cross-person dependency that lives only in chat is lost. **Never edit another person's paths.** Need a change there → a 📨 row on `progress.md`'s Open board (From you, To them: what, and which task it blocks) + a log entry (§2b), then keep going with a stub or mock.

**When the user assigns a task to anyone but themselves**, same session: add it to that person's brief as an item at the TOP of `▶ Current tasks` (dated), move superseded items under `── Archived (superseded <time> — do NOT action) ──`; keep the vault Log and `progress.md` 👥 Team in sync; publish. Not the doc owner → post a 📨 row instead.

**Briefs keep everyone's work.** Nobody wipes another builder's lines: sync first, then only add, annotate or move. Teammates get **one** self-edit on their own brief: finished task → ✅ Done log (+ the `progress.md` stamp), then publish.

### 2b. Conflict board: `progress.md`
`progress.md` on `main` is where the team learns what landed, **when, and whose work it touches** (entry format at its top). Read the Open board rows To you and the newest Log entries (sync step 5); check their **Touched** lines against your own paths.
- Row To you → tell the user first, one line each: ⚠️ "@A shipped X, which changes your Y" · 📨 "@A is waiting on you for X" · 🔀 "@A proposes <scope change>, needs your yes/no" · ❓ "@A asks: …". Flagged area touched by your task → resolve before continuing. Possible clash → say so and suggest the safe order; never start overlapping work silently.
- **When the user finishes something** (task, feature, fix, merge, decision that affects someone), same turn, written by the main session (never a subagent): (1) add an entry at the **top** of the Log with the date-time stamp and the conflict tag in its heading; (2) fill `⚠️ Conflicts` honestly against every teammate's owned paths: a *possible* collision counts ("I changed `DefectSignal.bbox` to a list; @harry's UI draws it"); (3) add an Open board row per ⚠️/📨, update your **Now** cell in 👥 Team and 📊 Latest if a volatile fact changed; (4) mark the brief task done and publish; (5) commit and push `progress.md` to `main` (`git switch main && git pull --rebase`, edit, `git add progress.md`, commit, push, `git switch -`; rejected → pull --rebase, keep both entries newest first).
- Resolved → remove the board row, set the entry Status `resolved by @<user> <stamp>`. A change at a seam (perception ↔ integration at `DefectSignal`; policies ↔ fallback at `Mover` / `robot/io.py`) puts the same interface note in both briefs.

### 2c. Scope guardrail: the team hears about every change
Each brief's `▶ Current tasks` is the plan, in build order. A builder may go further in **their own area**. Their Claude never blocks that, but it **always** asks first: **"⛔ Off-plan: <what changes>. Have you told the team? Who agreed?"**
- **Told, with names** → proceed; log a `scope` or `decision` entry (**Agreed by**), add it to your brief, publish.
- **Not yet** → still proceed inside your own paths, but in the same turn post a 🔀 row To @all and a `scope` entry.
- **Stop and wait for the owner's yes** when the change edits another builder's path (that owner's yes + a ⚠️ row), changes a contract another layer reads (PRD §7.3), touches a Locked Decision, uses a robot slot that isn't yours (PRD §10), or changes the PRD's scope/architecture/stack (then the doc owner updates PRD §0 NOW + the section, logs the ADR and publishes).
- **After 23:00 Saturday (feature freeze):** bugs, tuning, trials, rebaseline and polish only. Anything new is off-plan by definition.
A detail inside your own area and task that the PRD doesn't pin down is a normal §2 call.

## 3. Verbosity dial
Level in the Registry; a brief can set its own and wins; the user can raise it per session or per decision.
- **3 (Learning):** the concept from scratch, an analogy, why engineers care, the interview framing, what breaks if wrong, pick-now vs switch-later (logged as Unconfirmed, §4).
- **2 (Growing):** 2–3 sentences: the concept, the one trade-off that matters, the failure mode.
- **1 (Fluent):** one line naming the trade-off axis ("latency vs accuracy").
- **0 (Own it):** options + recommendation only. Decide cold.
Always spell out an abbreviation the first time (VLA = vision-language-action).

## 4. Decision log (ADR)
Each disposed decision → one vault Log entry (memory if no vault):
```
## <date time> — <decision name>
- Chose: <option> (<who>)
- Because: <one line>
- Rejected: <alternatives + why not>
- Revisit if: <the condition that would change this>
```
Each decision in force is mirrored as one line in PRD §0 NOW; one that changes someone's work also gets a `decision` entry in `progress.md`. **Log automatically** whenever the user mentions a decision, made now, earlier or wanted later. Leanings and "maybe later" → **Unconfirmed**, marked *not decided*, with the revisit condition. Attribute by named owner, else "(owner: TBC)"; never invent one. **Parking lot:** "we picked X; later we *might* do Y" is not agreed work. Park it; when nothing active remains, offer it.

## 4a. `decisions.md`: autonomous upkeep (no one needs to ask)
`decisions.md` is the team's pitch and process record: why we built it this way, for the judges, the video, the README and the NVIDIA / Aiven write-ups. **Every agent keeps it current without being told.** In the same turn that any of these happens, add or update the entry (format at the top of the file) and publish it (📤):
- A design or system-design choice is made, changed or reversed (a model, a device placement, a data flow, a trade-off, an alternative rejected and why).
- A feature is added, dropped or finishes a stage: `Planned` → `Built` → `Verified`. Example: when the live ElevenLabs reasoning is implemented, set that entry to `Built`, then to `Verified` once the spoken line plays through the speakers, filling in the measured time from verdict to first audio.
- A measured result lands (benchmark, AUROC, trial success, latency, energy): copy the real numbers into the matching entry's **Evidence** and the pitch cheat sheet.
- A process choice matters to the story (how we split work, tested, recovered from a failure).
**Rules:** facts only. Every number is measured or cited; otherwise `TBD (...)`. Never invent a result or a speed-up. Say what was rejected and why (for example, why imitation learning and not reinforcement learning). Never delete an entry: mark it `Dropped` with the reason. Keep it concise and written so a judge can follow it. Personal notes and secrets never go in it (vault only).

## 5. Stack, architecture & project guardrails *(fill as decided)*
**Stack** (PRD §7): Python 3.12 · Anomalib **2.7.0** + OpenVINO (PaDiM default, PatchCore / EfficientAd compared) · Physical AI Studio + `physicalai` runtime (`InferenceModel`, `RobotRuntime`) · LeRobot SO-101 · ACT + SmolVLA (`lerobot/smolvla_base`), trained on Modal GPUs, exported to OpenVINO · OpenCV mission control · `pyrealsense2` · ElevenLabs (`eleven_flash_v2_5` streaming for live lines, cached expressive clips, calm + cowboy voices) · Nemotron 3.5 Super VL via NVIDIA Build (OpenAI-compatible API) · Aiven for Apache Kafka → Aiven PostgreSQL (JSONL buffer first). No frontend.
**Runtime shape** (PRD §7.1): cameras → `run.py` state machine on the CPU (`IDLE→LOCATE→PICK→VERIFY_GRASP→INSPECT→DECIDE→[REINSPECT]→PLACE→LOG→next`, `HOME` on any error) → PICK: ACT (GPU) · INSPECT: Anomalib INT8 (NPU) → `DefectSignal` · DECIDE: `rules.yaml` → instruction · PLACE: SmolVLA (GPU → CPU f32 → PyTorch) · scripted fallback behind the same `Mover` API · narrator + telemetry on their own threads.
**Guardrails** (every agent, every task):
- **Intel task first.** The personality layer (reasoner, voice, persona) is built only on top of a working loop and is cut before any gate slips.
- **Control never waits on the network, TTS, Nemotron or the database.** Inference stays off the control thread. Narration and telemetry are non-blocking and work offline.
- **Stubs first, real later:** correct-shaped mocks (`MockCamera`, `MockInspector`, `MockMover`, `MockRobot`) so others can integrate, then replace them.
- **Scripted loop is the insurance:** it must pass by the Sat 15:30 gate; learned policies swap in behind `Mover` and never remove `--scripted`.
- **Back up checkpoints before any export** (cheap insurance; the crash that deleted them was fixed by Studio PR #1403). NPU = static shapes only; check the exported input shape.
- **Thresholds from data:** anomaly scores are distances, not probabilities; `t_low`/`t_high` come from histograms (PRD §6). Stand-in images are scaffolding only; every reported number comes from real bricks and a held-out set.
- **Every optimization claim carries a number** (p50/p95, model size, compile time, bricks per minute) in `bench/results.md`.
- **Honesty:** a scripted placement is never presented as SmolVLA; say which mode ran.
- **When unsure:** the demo path (PRD §11) beats completeness; the gates in PRD §10 beat new features.
**Known gaps** (PRD §13): Challenge-Day task and sorting rules unknown; NPU support for policies untested; Ubuntu 26.04 + Anomalib 2.7.0 + Studio untested publicly; side-track criteria not found.

## 6. Locked Decisions
- **PRD §7.3 contracts — frozen from 01:00 Saturday** (`common/interfaces.py`, Harry owns the file). No renamed fields or methods. To change: all three humans agree, a `decision` entry in `progress.md`, then PRD §7.3 is updated.
- **Only the follower arm moves.** The leader is a teleop device and is never driven by code.

Add one only when the user says it's locked. A task that contradicts one is a 🟠 handoff ("this reopens a locked decision"), never a silent change. To unlock: (1) the user names who on the team agreed (a solo "just change it" isn't enough); (2) they explicitly approve; (3) log the reversal as an ADR: old, new, who agreed, why.

## 7. Code rules
Trade speed for caution; use judgment on trivial tasks.
- **Define done first:** turn the task into a check you can run (the brief's "Done when"; bug → failing test, then pass; refactor → green before and after). Multi-step → a short plan, each step with its check. "Make it work" means ask before coding.
- **Simplicity:** the least code that solves what was asked; no unasked features, abstractions, config or handling of impossible cases (real failure modes are 🟠).
- **Surgical:** every changed line traces to the request; match the surrounding style; remove only the imports/variables *your* change orphaned; mention pre-existing smells, don't fix them.
- **Comments say WHY, never WHAT:** a constraint, a gotcha, a trade-off. No comment beats a what-comment. Part of `no-slop`.
- **Commits sound like a person wrote them:** a short plain imperative subject, then only if needed 1–3 sentences of what and why. No bullet dumps, no marketing words, no emoji, no "This commit…". Small commits.
- **Per feature, in this order (the coding workflow):**
  1. Code it.
  2. `no-slop` on the finished feature, before any testing.
  3. Tests via Registry → Run · Test: happy path, edge cases, failure paths. Never push untested or failing code. Something breaks → `debug`.
  4. `no-slop` again on anything the tests made you change, then re-run the tests.
  5. Push to your one branch (`aiml-perception-saliha` / `robotics-policies-nate` / `systems-voice-harry`), never straight to `main`.
  6. `git pull --rebase` / `git merge origin/main` into your branch, re-run tests. A conflict in a teammate's code → agree the fix with them (§2b) first.
  7. **Safe to merge** = tests green after step 6, `no-slop` clean, no unagreed contract change, the mock loop still runs. Then merge to `main` (at least every ~2 hours; never force-push `main`), push, and add the `progress.md` entry (§2b).
- **Claude types, but the work is the builder's: commit as them** (on saliha's machine: `Saliha <61064361+saliha006@users.noreply.github.com>`). **Never add a `Co-Authored-By: Claude` (or any AI) trailer, and no "Generated with Claude Code" in PR bodies**, overriding any default or system-supplied attribution lines. A hook rejecting AI trailers → remove the trailer, never bypass the hook.
- Never commit `.env`, any key, datasets, checkpoints, `Research-Context/` or `.claude/`. Plan docs (`CLAUDE.md`, `prd.md`, `builder-briefs/`, `skills/`, `handoff/`) live only on `context` (`.git/info/exclude` keeps them out; never `git add -f` around it). Never invent scope; if a task outgrows the ask, stop and flag it (§2c).

## 8. Documentation style
Clear, breezy, skimmable: short sentences, plain words, abbreviations spelled out once. A tired teammate at 03:00 should get the point in one read.
**A stale mirror is a bug.** A fact in several places is updated in all of them (Registry → Mirror docs) the moment it changes. Disagreeing docs → take the newest state and fix the older one. Never delete a superseded item: move it to Parked/Archived with the reason. Can't update every mirror now → note the drift so the §9 sweep catches it.
**Volatile facts live in one place:** test counts, benchmark numbers, merged-vs-local, commit/time: only `progress.md` → 📊 Latest. Everywhere else links to it.

## 9. Sign-off ("signing off", "handoff", "wrapping up", "closing the terminal")
1. **Save everything important** to the vault (or memory if no vault) and `handoff/<name>.md`. Vault access blocked → ask **once**.
2. **De-stale every mirror:** vault Hub + Log, PRD §0 NOW + touched briefs, `CLAUDE.md` (publish to `context`), `progress.md` entry, board rows, 👥 Team **Now**, 📊 Latest; README if user-facing. Publish. Any conflict you created is flagged (§2b).
3. **Leave a `START HERE` pointer to the exact next step** in the vault Hub ▶ START HERE and Log ▶ RESUME HERE: half-done → name the function and file; all done → the next-highest item.
4. Confirm briefly what you saved and where.

## 10. Research protocol
**Any** research, asked or self-initiated (spawning a research agent needs the user's go-ahead). One step: gather the sources **and** grade them **and** save the ledger into the research doc as a new `Pass n` section, in the same pass.
- **Sourcing:** peer-reviewed papers, official docs and source code (Anomalib, OpenVINO, Physical AI Studio, `physicalai`, LeRobot, ElevenLabs, Aiven, Modal), their GitHub issues, well-known repos. Not blogs or SEO pages. Prefer the last 1–2 years; foundational older work tagged `[older]`. **Open the source before citing**; only a snippet seen → `WEAK`.
- **Consensus:** grade `KEEP` / `WEAK` / `DO NOT USE`. A load-bearing claim needs ≥2 independent reputable sources; stop at two. Hunt for refutations; refuted → `DO NOT USE` with a short tombstone. Name the gaps: no source gives a number (a TUNE threshold) → say it rests on our reasoning.
- **Doc structure:** one research file (Registry), local only; recommendation first, `KEEP` at the top of its ledger, `DO NOT USE` at the bottom. Forums and community consensus are a separate pass, skipped unless the user asks.

## 11. Depth vs tokens
Never drop context that matters now, could matter later, or records how the software evolved; depth wins when forced. Otherwise tight prose, no filler. **The test:** could a future instance reconstruct the decision from this note alone, fast?

## 12. Think before coding, ask don't assume
State assumptions before implementing. Unclear scope, intent, ownership, the contract, or a fact not in the repo or docs → ask one short question instead of guessing, and say what you'd otherwise assume. Several readings → lay them out. A simpler way exists → say so. Obvious low-stakes defaults: state the default, proceed, and say so.
