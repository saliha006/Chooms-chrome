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
| 2026-11-15 07:46 | @saliha | @nate @harry | ⚠️ conflict | **App `.venv` can't load any exported policy** (jsonargparse 4.46: `'ArgumentParser' object has no attribute 'instantiate'`); `.venv-robot` (4.53) can. Before running learned pick/place through `run.py`, upgrade jsonargparse in `.venv` or run it from `.venv-robot`. Also new: smoothing wrappers in `policies/episode.py`, snap to inspect after a learned pick | 2026-11-15 07:46 |
| 2026-11-15 06:55 | @nate | @saliha | 📨 for you | **SmolVLA launch failed: `6salis/sortsense-place` needs a version tag.** Job `smolvla-allep-10000st-1115-045013` (started 06:50) stopped after 2 min: LeRobot 0.7.0 on Modal only loads a Hub dataset tagged with its codebase version, and yours has no tags (`meta/info.json` says `v3.0`). Only the owner can tag it; with your Hugging Face login run `python -c "from huggingface_hub import HfApi; HfApi().create_tag('6salis/sortsense-place', tag='v3.0', repo_type='dataset')"`. Nate's agent is watching the Hub and relaunches your exact command as soon as the tag appears | 2026-11-15 06:55 |
| 2026-11-15 06:20 | @saliha | @nate | 📨 for you | **SmolVLA place data is on the Hub, launch it now from your PC:** `6salis/sortsense-place` (public; 50 episodes, 25 per instruction with the exact strings, recorded at the new inspect pose; audit: brick held and released in the wrist video, episodes 34-49 are fast). Run `python -m train.launch --dataset 6salis/sortsense-place --policy smolvla --steps 10000 --cameras top,wrist,inspect`; **after 3 minutes check the job log shows the step count rising** (Studio's local trainer froze at step 0 tonight; if Modal stalls, cancel, relaunch, post the error here). When done: `modal run train/export.py --job <job> --policy smolvla` and post the job name here; Saliha's agent copies it to the laptop and runs the gate | 2026-11-15 06:20 |
| 2026-11-15 04:10 | @harry | @saliha @nate | 📨 for you | **`docs/how-it-works.md` is on `main`** (linked from the README): the whole codebase for the Intel judges, one brick traced end to end, then each layer with its owner (perception and thresholds, Intel deployment and benchmarks, robot I/O and both movers, the drive, Modal training, telemetry and Aiven, Pix, mission control, safety). Written from your code; please read your sections (4, 5 for @saliha; 6, 7 for @nate) and fix anything I described wrongly | 2026-11-15 04:10 |
| 2026-11-15 03:55 | @harry | @nate @saliha | 📨 for you | **Drive reliability, measured:** `python run.py --scripted pick,place --base --drive-trials 20 --no-listen` runs only the drive 20 times (Enter between attempts, board back at the start by hand) and prints e.g. "Drive arrived 18 of 20 (90%, 95% interval 68-99%)", median time, distance travelled and how far the board stopped from the dock (your overhead tag), failures by reason; later `python -m telemetry.drive_report`. No change to `robot/drive.py`: it uses `find_tag`, `cm_to`, `degrees_to`. Use it for the go/no-go and the mobility slide; if the offsets point at a TUNE value in `drive.py`, that change is yours (`docs/station.md` 6b) | 2026-11-15 03:55 |
| 2026-11-15 02:20 | @harry | @saliha @nate | 🔀 scope proposal | **Object recognition for Pix, trained locally (Harry's call; overlaps perception, so @saliha please read).** On your 01:20 cut list, **object naming stays: Harry says no to cutting it.** Built in Harry's `narrator/vision.py` (not in `perception/`): CLIP's image encoder via OpenVINO (GPU→CPU, ~18 ms on CPU), regular objects brick / plate / purple bowl / orange bowl, anything else "unknown" with a best guess; zero-shot now, then `capture` ~20 wrist-camera photos per object and `train` a small classifier on the Intel laptop (seconds). "Hey Pix, what do you see now?" leads with it. No new library (transformers came with `physicalai`). Needs at the station: `python -m narrator.vision build` (~600 MB download) and ~10 min of wrist-camera photos (`docs/station.md` 5b). Say no or suggest a better home on this row | 2026-11-15 02:20 |
| 2026-11-15 01:20 | @saliha | @nate | 📨 for you | **Before tonight's Modal launches (research Pass 2 + critic, `Research-Context/`):** (1) training length: SmolVLA is set to batch 8 × 10k steps, about 1/16 of LeRobot's recipe, and ACT to 20k against LeRobot's 100k default; raise them if the GPU budget allows, or this is a retrain later. (2) Record **SmolVLA first** (it starts from a fixed pose and it is the VLA, 20 points), ACT second only if teleop is clean. (3) Anti-jitter, no retrain: run ACT with temporal ensembling or a short n_action_steps (our runner plays a 100-step chunk blind), SmolVLA through the runtime's `AsyncExecution`; add a smoothing filter. (4) LearnedMover: move to the taught `inspect` pose before scoring (an 8° tolerance shifts the brick in the close-up). Saliha's agent can code (3) and (4) while you record; say yes here | 2026-11-15 01:20 |
| 2026-11-15 01:20 | @saliha | @harry | ⚠️ conflict | **Merged into your folders tonight (tests green, 343 + 110):** `ui/click_regions.py` warms the camera up and stays live until the first click (the first frame was dark); `fallback/scripted.py` gets optional pick slots `pick_2`..`pick_5` (brick n from slot n, a re-grasp stays on slot 1) so five bricks sort with no human, and `fallback.teach` accepts them; the inspector now scores the same centred crop the training photos use (`perception/`). Also from the critic: say in the README/submission that Physical AI Studio is part of Intel's Robotics AI Suite (Intel's 2026.2 docs list it), run `bench/power.py` during the 20 trials, and a coloured base plate under the bricks reads as one obstacle to the zone gate (bricks go loose on white card) **@harry 01:40: read, thanks for the merges.** Critic items done: Studio named as part of Intel's Robotics AI Suite in the README and `docs/submission.md`; every real run now logs its energy, power, peak temperature and joules per brick as an `ENERGY` row (`bench/power.py` around `Cell.run`; `docs/station.md` has the once-per-boot RAPL chmod); the demo checklist says white plates or loose bricks. | 2026-11-15 01:20 |
| 2026-11-15 01:20 | @saliha | @all | 🔀 scope proposal | **Order and cut changes from the critic (say no on this row):** the drive leaves the critical path: if-time slot after the trials, go/no-go 3 of 3 at 05:40; swap the cut order so the drive is cut before the learned policies (one learned policy is worth more points); cut object naming, Kafka, the overhead tag tracking (the stops suffice), the colour hedge and the extra Studio SmolVLA job | 2026-11-15 01:20 |
| 2026-11-15 00:07 | @nate | @harry | 📨 for you | **`robot/drive.py` is on `main` (`73fd08a`); the wiring is yours:** in real mode, `from robot import drive`, then `cell.approach = lambda: drive.approach(lambda: capture.frame("top"))` and `cell.approach_cm = drive.PLANNED_CM` (41 cm). It also needs (1) `fallback.teach` to accept `drive_reach`, `drive_touch`, `drive_drag`, `drive_lift` (its choices are the 7 scripted poses today); (2) `config/dock.yaml`, written at the station by `python -m robot.drive --teach-dock`; (3) a `DRIVE` deadline of about 60 s (4–5 strokes of ~5.5 s; the code stops at 8). E stops it inside `robot.io` as it does the movers; a stall returns None. **Nate's agent is free for your hardware-free items:** say which (the wiring above, the voice-brief plays, `docs/`), and it stays out of everything else **@harry 01:40: wired** (`main`): `python run.py --scripted pick,place --base` runs `drive.approach(lambda: capture.frame("top"), dock, stroke)` as the `DRIVE` stage with `approach_cm = drive.PLANNED_CM`; `--base` checks `config/dock.yaml` and the four stroke poses first and stops with your message if either is missing; `DRIVE` deadline 60 s. Off unless `--base` is given, so the 05:40 go/no-go is just leaving the flag off. Teach support for the four poses was already merged by Saliha. Thanks for the agent offer: nothing hardware-free left on Harry's list right now. | 2026-11-15 {T} |
| 2026-11-15 00:10 | @saliha | @harry @nate | ⚠️ conflict | **Drive gaps found while reading `robot/drive.py` (Nate, `73fd08a`):** (1) its stroke poses could not be taught: `fallback.teach` only accepted the 7 sorting poses. Fixed on `systems-voice-harry` → `main`: `python -m fallback.teach drive_reach drive_touch drive_drag drive_lift` now works and `config/waypoints.yaml` has the four lines (340 + 108 tests). (2) **Still open, @harry:** `run.py` never sets `cell.approach`, so the drive isn't called; it needs `cell.approach = lambda: drive.approach(<top frame>)` plus `approach_cm = drive.PLANNED_CM` when a dock is taught. (3) @nate: D35 notes 4-5 strokes may exceed run.py's 30 s DRIVE deadline (5 × 5.5 s stroke time = 27.5 s before settling) **@harry 01:40:** (2) done, see Nate's 00:07 row; (3) the `DRIVE` deadline is now 60 s. | 2026-11-15 00:10 |
| 2026-11-14 23:49 | @nate | @harry | 📨 for you | **Box-room drive (D35), what touches your files:** (1) may the four stroke poses live in `config/waypoints.yaml` as `drive_reach`, `drive_touch`, `drive_drag`, `drive_lift`, taught with `python -m fallback.teach`? (2) `cell.approach` will come from `robot/drive.py` and needs the shared capture for the overhead tag; Nate's agent sends the one-line wiring with the code. (3) The drive is about 41 cm, 4–5 strokes, so the 30 s `DRIVE` deadline is likely too short. Build sheet: https://claude.ai/artifact/Db57fpWKR4MZkKe6zeT4y4 | 2026-11-14 23:49 |
| 2026-11-14 23:49 | @nate | @saliha | 📨 for you | **Box room as built, what it means for perception (D35):** the inspection camera rides on the board (Harry's plan), so capture only after it is mounted, the inspect pose is taught and the room is frozen; capture from real picks and include the 90° rolled view (the robot re-inspects rolled, `config/rules.yaml`). The yellow starting plate and the pale/yellow bricks: Nate will use a contrasting plate to start the test or put both together. A tag on the board gives the drive its distance, so plate distance may not be needed; say if you still want it. The overhead camera goes about 0.8–0.9 m up (your tall-object check uses the table distance). Doc owner: D35 is on `context`; PRD §0's 21:35 drive line already matches | 2026-11-14 {T} |
| 2026-11-14 23:20 | @harry | @saliha @nate | 📨 for you | **`physicalai` is not declared in any requirements file**, but `robot/io.py` (normalized units) now imports it in two `robot/tests/test_io.py` tests, so a fresh `.venv` fails them. Harry installed `physicalai[so101]==0.4.0` locally (the Intel laptop's version) and the full suite passes: 335 passed, 4 skipped. Please add it to the right requirements file (your call which). Heads-up: it pulls in `opencv-python-headless` again, so after installing put the window build back (`docs/station.md` step 0) | 2026-11-14 23:20 |
| 2026-11-14 21:35 | @saliha | @harry | 📨 for you | **Cowboy trigger decided (Saliha, option C; PRD §0, decisions.md D13):** keep the hat (voice + H) flipping the whole persona as you built it, and add **one short cowboy exclamation on every defective verdict** (a cached clip such as "Holy smokes!" / "Well I'll be"), played before the calm explanation; the score explanation itself stays in the calm voice. About 20 lines in `narrator/`; please build it after the MVP gate. Also in PRD §0: the drive is scripted and ends at a physical stop block; waypoints, clicked regions and recordings all happen at that parked spot | 2026-11-14 21:35 |
| 2026-11-14 21:35 | @saliha | @nate | ⚠️ conflict | **The follower still drops out in Studio** (`Sync read failed with comm result -6`, 10 times 18:59-21:23, during teleop and at session start). Power is right (all 6 follower motors at 12.2-12.3 V idle, 33-35 °C; leader 5.8 V) and USB never disconnects, so it points at a 3-pin servo cable or the brick sagging under load. Saliha is re-seating the cables; recording waits on a clean 2-minute teleop. Also PRD §0: record everything at the parked spot (stop block), never during the drive | 2026-11-14 21:35 |
| 2026-11-14 19:55 | @harry | @saliha @nate | 📨 for you | **Follower port and calibration are on `main`:** `config/robot.yaml` `port: /dev/serial/by-id/usb-1a86_USB_Single_Serial_5AB0157419-if00` (follower, `ttyACM0` today; the leader `5AE7045242` is never driven) and `config/so101_follower.json` copied byte for byte from the Intel laptop (Studio, 18:34). **@saliha, on the Intel laptop before the next `git pull`:** `mv config/so101_follower.json /tmp/` (it is untracked there and would block the pull; the same file arrives from `main`). @nate: say if Studio should keep its own copy elsewhere | 2026-11-14 19:55 |
| 2026-11-14 19:45 | @harry | @all | 🔀 scope proposal | **Workflow to the 10:00 demo (replaces Harry's 18:55 order). Key point: build the box room FIRST.** Waypoints, the clicked zone and Nate's recordings depend on where the arm sits relative to the plates *after* the drive, so: build the room, mark a **parked spot** with a stop block where the base always ends, and teach/record from there; mount the **inspection camera on the board** (it moves with the arm) and the **overhead camera fixed above the room**. **Now→20:30** Harry: room (matte white, open top, lamp), plates, numbered bricks, parked spot with @nate · Saliha: leader recalibration, cameras 640×480 · Nate: confirm the demo shape, scrape route. **20:30→21:15** Harry at the parked spot: mic test, `ui.click_regions`, teach 7 waypoints. **21:15→21:45** @saliha: real-brick capture at the inspect pose, train + export the detector. **21:45→22:15 MVP gate** Harry + Saliha: `run.py --scripted pick,place`, 5 bricks, no human, filmed (backup v1). **22:15→~00:15** @nate: rehearsal, ACT + SmolVLA recording, Modal training; Harry's agent wires `Cell.approach` (scrape), `Cell.namer` (naming model), plate distance as they land. **~00:15→01:00** first full box-room run (scripted), filmed (backup v2); bugs only after this. **01:00→06:00 sleep.** **06:00→07:30** policies if they pass their gates (scripted stays the fallback, labelled on screen), 20 logged trials + `truth.csv`, `make rebaseline` on the demo table. **07:30→09:00** video, README numbers, `docs/submission.md` (Saliha NVIDIA, Nate Modal). **09:00 submit; 09:00→10:00** rehearse, e-stop drill, backup video, laptop on a phone hotspot. **Cut order if late:** overhead drive tracking → object naming → learned policies → the room (table-top fallback in PRD §11). Never cut: scripted loop, 20 trials, spoken verdicts. **Settled (PRD §0, 15:08):** bricks start on the plates and are sorted into the purple (perfect) and orange (defective) bowls, which sit in the room by the plates within the arm's reach from the parked spot. **Open:** the 23:00 freeze now falls after the MVP gate, so the 00:15 room run counts as integration. Say no or reorder on this row · **@nate 23:49: yes** (the dock is your parked spot; design in D35) | 2026-11-14 19:45 |
| 2026-11-14 19:05 | @harry | @saliha | 🔀 scope proposal | **Draft for the PRD (doc owner publishes; Harry waits): the box-room demo, as Saliha described it and Harry answered.** (1) Room: white matte card walls and floor, open top for the overhead camera; diffuse light from above. (2) Robot on one side; bricks of different colours **on the plates** on the other side; it says the plates are too far, decides to go over, and the arm scrapes the board across the floor on a **pre-planned route** (Nate; narration built: `Cell.approach`). (3) Operator says "I'm putting a cowboy hat on you": robot hears it (ElevenLabs speech-to-text), says "Well I'll be, a cowboy hat!", stays cowboy **until told the hat is off** ("Ohhh, I'm no longer a cowboy"); H key = backup. Built: `main` `789142a`. (4) Sorting is the main event (Anomalib, live reasoning with scores). (5) Unfamiliar objects named out loud (voice built; naming model = Saliha's pick, local CLIP/SigLIP recommended: no training, offline). (6) Done: spoken summary + dance. **Open:** where sorted bricks go (still the purple/orange bowls?); overhead camera giving plate distance (Saliha). Core loop first: MVP target 00:00 **@harry 19:30: published to `context` on Saliha's behalf** (her API calls failed): PRD §0 NOW top entry + §11 box-room script, table-top script kept as the fallback; additions only. @saliha edit freely; @nate please confirm the demo shape here. | 2026-11-14 19:05 |
| 2026-11-14 18:55 | @harry | @all | 🔀 scope proposal | **Tonight's station order (the PRD §10 slot table is ~6 h behind). Target: MVP (scripted loop, real Anomalib, 5 bricks, no human) by 00:00; demo 10:00.** One person at the keyboard per slot, everyone else over SSH in their own tmux window; agents never open the cameras or arm during someone else's slot. (1) now ~30 min **Saliha**: leader recalibration, Studio cameras 640×480. (2) ~45 min **Harry**: `ui.click_regions` (zone + bowls), teach the 7 waypoints, a 2-min mic test. (3) ~30 min **Saliha**: real-brick capture at the inspect pose. (4) ~2 h **Nate**: teleop rehearsal, then ACT + SmolVLA recording (Saliha trains the detector off-robot meanwhile). (5) ~20 min when Nate pauses, **Harry + Saliha**: scripted gate, film it. (6) **Nate + Harry**: policies, box-room rehearsal, 20 trials. **Freeze clash:** the charter freezes features at 23:00, before a 00:00 MVP: move the freeze to ~01:00, or treat MVP work as bugs/tuning. Say no or reorder on this row **@harry 19:45: superseded by the 19:45 row.** · **@nate 19:30: yes** to the order; flexible on the freeze (MVP work past 23:00 is fine) | 2026-11-14 18:55 |
| 2026-11-14 18:38 | @saliha | @nate | 📨 for you | **Station state, read from Studio's API at 18:35.** (1) **Leader calibration is unusable:** shoulder_pan spans 13°, wrist_roll 12°, wrist_flex 71° (the joints were not moved end to end), while the follower's is good (192-215° per joint, wrist roll full turn). With normalized units the follower would swing its whole range when the leader moves 13°, so **recalibrate the leader before any teleop** (Saliha is doing it at the station now). The leader board changed: `/dev/ttyACM1` is now serial `5AE7045242`. (2) Follower calibration saved to `config/so101_follower.json` on the laptop (from Studio, not committed yet). (3) Studio cameras are set to 1920×1080: Studio's docs and our audit expect 640×480 at 30 fps; we are switching them and renaming them `top`, `inspect`, `wrist` (D29 keys). (4) **Your call:** Intel's `JUNCTION2026.md` says Studio trains SmolVLA (and ACT) on Modal itself (Settings → Training Targets → Modal Provider), which is what "fine-tuning in Studio" (20 points) rewards; move SmolVLA from LeRobot (D20) into Studio? PRD §0 has the rubric · **@nate 19:30:** (4) LeRobot SmolVLA stays the proven path (trained, exported, parity 2.6e-6); one Studio SmolVLA job on Modal runs on the same real data after a Studio-on-Modal smoke test; the better one at the gate ships (D20, Nate's N11). (1)–(3) noted | 2026-11-14 18:38 |
| 2026-11-14 17:55 | @nate | @harry @saliha | 📨 for you | **Voice research for the ElevenLabs selling point (Nate asked, outside MVP; ~120k credits left).** Full brief: https://claude.ai/artifact/QN6VX8sxuArUWyc785bs2y (Nate shares it with you). Ranked: (1) live model `eleven_flash_v2_5` → `eleven_v4_turbo`: same API price ($0.04/1K chars), ~100 ms, audio tags like `[excited]` `[hesitant]` chosen from the score margin; check `text_to_speech.convert` accepts it (the docs show v4 on the Text-to-Dialogue endpoints, one voice per connection); (2) name obstacles live: cached "Holy smokes!" at once, then crop from `top` → Nemotron VL name (@saliha: pixel box on `scene.Blob`; optional local SigLIP/CLIP on the Intel GPU/NPU via OpenVINO for an instant name) → cowboy line; (3) narrate intent at locate/pick/inspect/place from facts the cell has, synthesised as each stage starts so the latency hides under arm motion; (4) 3–4 takes per cached line (`eleven_v4`, ~19k credits) so nothing repeats; (5) ~12 sound effects (~1k credits); (6) one Finnish line in the summary; (7) stretch: push-to-talk question → Scribe STT → answer from the ReasonTrace. Budget: one live 20-brick run ≈ 5.5–11k credits; add a floor (stop live lines below ~10k, read `GET /v1/user/subscription`). Facts only from official ElevenLabs/OpenVINO pages; credits per char for v4 Turbo is inferred | 2026-11-14 {T} |
| 2026-11-14 17:55 | @harry | @nate | 📨 for you | **Seam for your wheeled-base driver (the demo opening, talked over live):** in `run.py`, set `cell.approach` to a function that drives the base to the table and returns the centimetres travelled (float), or `None` if it did not get there; optionally `cell.approach_cm` = the planned distance, said before it moves. It runs once before the first brick as a `DRIVE` stage: E is checked before it starts and the stage deadline (30 s, TUNE) is armed, so please check `common.estop.requested()` and `common.deadline.expired()` inside your drive loop, as the movers do. No hook = no drive, so nothing changes until you plug it in. Rehearse the voice with `python run.py --mock --drive 42` · **@nate 19:30: yes, Nate owns the drive** (N10): a `cell.approach` function that checks `estop.requested()` and `deadline.expired()`; design first, rehearsed with the base held | 2026-11-14 17:55 |
| 2026-11-14 17:55 | @harry | @all | 🔀 scope proposal | **The demo opens with the base driving the arm to the table** (Harry: the arm starts out of reach), talked over live by the robot. This moves the base move from "after the 23:00 freeze" (Nate's 16:15 row) into the demo path; the scripted loop without the drive stays the insurance. Demo script updated (`docs/demo-script.md` 0:05). Say no on this row if you object · **@nate 19:30: yes** to the box-room opening (D33 changed; recordings stay docked) | 2026-11-14 17:55 |
| 2026-11-14 17:49 | @nate | @harry @saliha | 🔀 scope proposal | **Nate wants objects named live, not only a fixed clip.** Today an object in the zone that isn't a brick is just a blob that failed the brick shape test (`perception/scene.py`, no name), and `run.py` plays the one cached cowboy clip "Holy smokes!" (`narrator.trigger("obstacle")`); live lines exist only for perfect, defective, uncertain, empty and quit, and the Nemotron line only sees the brick at the inspection camera. **Ask:** when the camera sees something new, the robot says live what it is (e.g. "Holy smokes, there's a coffee mug in my zone!"). **Suggested shape, same guardrails as the live voice:** keep the cached "Holy smokes!" playing at once; in parallel send the obstacle's crop from the `top` frame to the object-naming model (@saliha: Nemotron VL, which we already call, or a detector on the laptop) for a short name, then @harry composes the cowboy line and speaks it through ElevenLabs Flash; off the control thread, about 3 s timeout, offline = nothing extra, and the arm never waits (it already never picks an obstacle). @harry: yes or no and how long it takes (it is before the 23:00 freeze); @saliha: which model names the object **@harry 18:10: yes, and the voice side is built** (`main` `7821e3e`, ~1 h): cached "Holy smokes!" at once; `narrator.naming.ObjectNamer` asks the naming model off the control thread with the top frame (cropped to `getattr(blob, "box_px", None)` once `scene.Blob` has a pixel box, else the whole frame); a name back within 3 s is spoken live in the current persona ("Holy smokes, there's a coffee mug in my zone! That ain't no brick, so I'm leavin' it be."); late, missing or offline = nothing extra. @saliha: plug your model in as `cell.namer = ObjectNamer(name_fn, narrator.say)` where `name_fn(bgr_image) -> str | None` returns a short name; tell Harry and he wires it in `build_real`. | 2026-11-14 17:49 |
| 2026-11-14 17:43 | @nate | @harry @saliha | ⚠️ conflict | **Camera check on the Intel laptop (17:43, read-only, nothing was holding the devices):** `top` = `/dev/v4l/by-id/usb-Intel_R__RealSense_TM__Depth_Camera_415_Intel_R__RealSense_TM__Depth_Camera_415_310323024442-video-index0` (colour, 640×480 at 30 fps; `index2` is the IR stream with the dot pattern), `wrist` = `/dev/v4l/by-id/usb-Sonix_Technology_Co.__Ltd._USB2.0_CAM1_USB2.0_CAM1-video-index0` (**gives no frames in the default YUYV format, 640×480 works in MJPG**), `inspect` = `/dev/v4l/by-id/usb-Webcam_Webcam_Audio_01.00.00-video-index0` (640×480 at 30 fps; it points across the room right now, not at an inspection mark). @harry: `config/cameras.yaml` paths, and `common/capture.py`'s `OpenCVCamera` needs to request MJPG (`cv2.CAP_PROP_FOURCC`) or the wrist camera reads nothing in `run.py`. Nate records the wrist camera with MJPG too **@harry 18:10: done** (`main` `5391b38`): `config/cameras.yaml` `wrist: fourcc: MJPG`, and `OpenCVCamera` asks for it. Checked on the Intel laptop through OpenCV: the wrist gives 5 of 5 frames at 640×480 both in its default format and in MJPG, so it was not blank in `run.py`, but now it matches your recordings. | 2026-11-14 17:43 |
| 2026-11-14 17:35 | @harry | @saliha @nate | 📨 for you | **Two dependency notes (no code of yours changed).** @saliha: `anomalib` depends on `opencv-python-headless`, so a fresh `uv pip install -r requirements.txt` can replace the window build and mission control fails to open ("function is not implemented"); it bit Harry's laptop at 17:30, the Intel laptop is fine now (Qt build loaded). Fix in `docs/station.md` step 0; your call whether `perception/requirements.txt` should pin it another way. @nate: `train/audit.py` imports `pandas`, which no requirements file declares (it arrives only through another package); your call to add it to `train/requirements.txt`. Full suite on Harry's laptop: 283 passed, 4 skipped · **@nate 19:30:** pandas, pyarrow and pyyaml are declared in `train/requirements.txt` (this push) | 2026-11-14 17:35 |
| 2026-11-14 17:33 | @nate | @saliha @harry | 📨 for you | **SSH access to the Intel laptop for Nate (read-only camera check first):** Nate's PC is on the venue Wi-Fi and can't reach `intel@172.20.10.7`. Please tell Nate **in person or by DM, not here**: which network to join (the hotspot name and password) and how to log in (the password, or come by and run `ssh-copy-id intel@172.20.10.7` from his PC so his key works). First use: `ls /dev/v4l/by-id/` and one frame per camera, no robot and no one's tmux window. Clear once shared **@harry 17:45:** the Intel laptop is on the venue Wi-Fi now: `ssh intel@10.0.41.130` from `Junction2026` works (checked 17:44; it moves to Saliha's hotspot at times, then use `172.20.10.7` on that). No hotspot needed while it's on `Junction2026`. For your key: come to the station and Harry or Saliha types the password once while you run `ssh-copy-id intel@10.0.41.130` from your PC; password in person only. | 2026-11-14 17:33 |
| 2026-11-14 17:25 | @nate | @saliha | ⚠️ conflict | **SmolVLA on a CPU pauses ~7 s per 50-action chunk** (Core Ultra 5 125H, Nate's PC; ACT ~0.1 s). The demo laptop's GPU drivers decide whether placing looks smooth; for your D24 table. Nate's async option is parked until there is a demo-laptop number. Clear once read | 2026-11-14 17:25 |
| 2026-11-14 17:22 | @saliha | @nate | ⚠️ conflict | **ACT runs on the NPU** (probe, random weights, our three cameras, `bench/act_npu_probe.py`): compiles in 2.3 s, 8.9 ms per call (GPU 4.2 ms, CPU 65.7 ms). **The station is live:** one arm on `/dev/serial/by-id/usb-1a86_USB_Single_Serial_5AB0157419-if00` (leader or follower not yet confirmed; only one arm board is connected), Physical AI Studio running in tmux session `studio` (UI http://localhost:3000, backend healthy). No calibration file exists yet (`config/so101_follower.json`). One robot user at a time: say on this row when you take the arm | 2026-11-14 17:22 |
| 2026-11-14 17:15 | @nate | @saliha | 📨 for you | **Answers to your 17:12 questions:** No episode was recorded with the old blue/red strings (nothing is recorded yet), and the leader-teleop rehearsal has not happened yet; it is first in the manual queue, before episode 1. The audit runs after every batch, before any training. Clear this row once read | 2026-11-14 17:15 |
| 2026-11-14 17:00 | @harry | @all | 🔀 scope proposal | **Live voice moves up (Harry, for the ElevenLabs prize):** the "live voice line" leaves the cut order (CLAUDE.md item 4) because it is built and on `main`: each verdict is spoken live with its score, threshold and mark position, cached clip as fallback, the arm never waits. Doc owner: update the cut order if agreed. @saliha: `narrator.say(..., text=line)` now speaks your reasoner line live. Say no on this row if you object · **@nate: yes** (17:00) · **@saliha: yes** (17:12; cut order updated in `CLAUDE.md`) | 2026-11-14 17:00 |
| 2026-11-14 16:58 | @saliha | @all | ⚠️ conflict | **The Intel laptop is set up (done at the laptop, replaces the 16:01 driver row).** OpenVINO lists **CPU, GPU, NPU**; the detector compiles and runs on all three, FP16 and INT8 (`bench/results.md`). RAPL is readable (**re-run `sudo chmod a+r /sys/class/powercap/intel-rapl*/energy_uj` after every reboot**), Wi-Fi power saving is off, `intel` is in `render`, `video`, `dialout`. Station clone: `~/Documents/Chooms-chrome` on `main` (`.venv` = app, `.venv-robot` = robot and training). **Still missing on the laptop:** a `.env` (each key pasted by its owner), GitHub push credentials, the charger (it was on battery at 16:40), and the hardware: only one USB webcam is plugged in, no RealSense, no wrist camera, no arm | 2026-11-14 16:58 |
| 2026-11-14 16:58 | @saliha | @harry | 📨 for you | **`run.py` on the real arm needs `physicalai.robot.so101`, which `requirements.txt` does not install.** On the Intel laptop I ran `uv pip install --python .venv "physicalai[so101]==0.4.0"` (after the normal install; resolving both together downgrades OpenVINO to 2026.1 and adds the headless OpenCV). All 229 tests incl. the slow ones pass with it; `uv pip check` shows one declared clash (Anomalib wants `jsonargparse` < 4.47, it brings 4.53), harmless in the tests. Your call whether to pin it in `requirements.txt`. `docs/station.md` step 0 is done on the laptop; the SSH address there (`10.0.41.130`) differs from the hotspot one (`172.20.10.7`). H5 is still open: the one webcam plugged in is `/dev/v4l/by-id/usb-Webcam_Webcam_Audio_01.00.00-video-index0` (640×480 by default, MJPG up to 1920×1080), lying on the table, not mounted; I did not fill `config/cameras.yaml` because its role is yours to say | 2026-11-14 16:58 |
| 2026-11-14 16:58 | @saliha | @nate | 📨 for you | **Your environment on the Intel laptop is built:** `.venv-robot` in `~/Documents/Chooms-chrome` (`physicalai-train` 0.3.0, `physicalai` 0.3.0 with the SO-101 plugin, `lerobot` 0.6.0 incl. `lerobot-find-port` / `lerobot-calibrate`, `modal` 1.6.4, pandas, pyarrow; `pytest robot policies train` = 56 pass). **Physical AI Studio** is installed natively at `~/work/physical-ai-studio` (no Docker on the laptop): terminal 1 `cd ~/work/physical-ai-studio/application/backend && uv run --extra xpu physicalai-studio serve`, terminal 2 `cd ~/work/physical-ai-studio/application/ui && PATH=$HOME/.local/node/bin:$PATH npm run start`, then http://localhost:3000 (backend start checked, UI not opened yet). Needs from you: `modal token new` on the laptop if you launch from it, and the calibration file `config/so101_follower.json`. Version note: the app `.venv` has the `physicalai` 0.4.0 runtime while exports come from 0.3.0; I check an export loads under 0.4.0 as soon as one is on the laptop | 2026-11-14 16:58 |
| 2026-11-14 16:56 | @nate | @harry @saliha | ⚠️ conflict | **Policy observations now match the export (A3):** `policies/episode.py` sends `state`, `images.<camera>` (RGB, batch axis) and `task`, what the exported runtime reads; it was sending LeRobot's dataset keys and BGR frames. @harry: keep passing raw `SharedCapture` frames from `run.py` (no colour conversion there) and keep `config/models.yaml` `cameras: [top, wrist, inspect]` in that order. @saliha: use the same keys for any policy benchmark. Clear this row once read · @saliha read 17:12 (will use the same keys for any policy benchmark) | 2026-11-14 16:56 |
| 2026-11-14 16:50 | @harry | @saliha @nate | 📨 for you | **`docs/submission.md` is on `main`**: the Junction Platform text per track. Please write your section by Sunday 06:00: @saliha **NVIDIA** (model, what it does, why it matters, how we improved its outputs), @nate **Modal** (GPU type, time, cost, the sweep). Facts only, unmeasured numbers stay TBD · **@nate: Modal section written** (`925d0bc`; real-run GPU time and cost stay TBD until the runs) | 2026-11-14 16:50 |
| 2026-11-14 16:33 | @nate | @all | ⚠️ conflict | **Gates move (recording has not started at 16:33; the brief's rule):** ACT gate about **21:30** (was 17:00) and SmolVLA gate about **22:15** (was 19:00). Estimates: recording about 17:30–19:30 after the Intel laptop drivers, rehearsal and a test episode, then the brief's 2–3 h of training. The 23:00 freeze stays; the scripted loop is the insurance meanwhile **@harry 17:25: read.** The scripted loop stays the insurance until your gates. | 2026-11-14 16:33 |
| 2026-11-14 16:19 | @saliha | @nate | ⚠️ conflict | **N4 done on `main` (`668933e`): `train/commands.py` `smolvla()`** now passes `--policy.scheduler_decay_steps=<steps>` (LeRobot's default of 30,000 would leave a 10k run near the peak learning rate) and `--save_freq=2500`; the optional flags stay last (your tests read them by position); 14 train tests pass. Batch size stays 8: raise it only after you see the GPU memory (hyperparameters come after the data audit, D32). Not touched: your `launch.py` and `modal_train.py`. N5 (colour hedge) is still open: say if you want me to take it | 2026-11-14 16:19 |
| 2026-11-14 16:15 | @nate | @all | 🔀 scope proposal | **Base move (Saliha's parked wheeled-platform item, option b):** the mentors say unclamping is allowed (Nate asked). Nate's call: **dock now** (tape outline and a stop block behind the base; the base stays clamped in the dock for every recording and run), and **the move itself only after the 23:00 freeze**, on the parked item's conditions (20 trials logged, README and video safe, a free robot slot). @harry: yes or no. @saliha: please add the mentor answer and the dock to the parked item | 2026-11-14 16:15 |
| 2026-11-14 14:54 | @saliha | @nate | 📨 for you | **DO NOW (top of your brief, `context`): manual = you, agent = your coding agent in parallel.** Manual: rehearsal + N8 readings, test episode (unit check, 200-step ACT smoke), record the 54 ACT episodes, push, launch ACT; record the 50 SmolVLA episodes, push, launch SmolVLA; train both on Modal in parallel. Agent now: **A3 export test** (riskiest step, no robot needed), update `train/RECORDING.md` (new strings, N6 tips, audit step), review N3. Saliha's agent does N4, N5 and the episode audit. If recording has not started, tell us: the 17:00 and 19:00 gates move | 2026-11-14 14:54 |
| 2026-11-14 14:54 | @saliha | @harry | 📨 for you | **DO NOW (top of your brief, `context`).** Manual: H5 station (cameras, RealSense, click zone and bowls, waypoints), the scripted full loop once Saliha has real bricks captured, Kafka service if the plan has it. Agent now: wire `bowl_check` into `run.py` + `io.holding()` in the scripted mover, A6b persona machine, drift alarm calling `perception.drift`, A8 README + architecture diagram (four layers named), draft the demo script and n = 20 slide. Say so here if you want Saliha's agent to take A6b or A8 **@harry 16:10: agent items (a)–(e) done on `main` `ce9a437` (A6b built by Harry); manual items open.** | 2026-11-14 14:54 |
| 2026-11-14 14:39 | @saliha | @all | 🔀 scope proposal | **Data quality first, hyperparameters second (second mentor; decisions.md D32, PRD §0 and F21, `context`, re-sync).** Every dataset is audited by code before it trains anything (images: `perception/audit.py`; episodes: `train/audit.py`); no hyperparameter sweep before the audit passes, then one small Modal sweep; ACT stays at lr 1e-5 until a sweep beats it. Say no on this row to anything you object to. **@nate 16:16: yes** | 2026-11-14 14:39 |
| 2026-11-14 14:26 | @saliha | @nate | 📨 for you | **Do first, before the first recorded episode** (briefs top, decisions.md D23/D31): (1) record SmolVLA with exactly `"the brick is perfect, place it in the blue bowl"` and `"the brick is defective, place it in the red bowl"` (they carry the verdict; nothing is recorded yet, so it is free); (2) rehearse every stage by leader-follower teleop, about 15 min folded into your 6 practice runs, nothing recorded: 9 start dots, inspection hold + wrist roll ±90° in view, both bowls, gripper numbers (N8), unit check (D29), one e-stop press. A failure moves the tape or a bowl, not the policy. Reply here if you disagree | 2026-11-14 14:26 |
| 2026-11-14 14:19 | @saliha | @all | 🔀 scope proposal | **Mentor guidance, PRD §0 + decisions.md D31 on `context`, re-sync.** Anomalib is the only anomaly detector; the VLA (built in Studio) does the integration, translating perception results and the task instruction into robot actions; test a move with the leader first, then fine-tune. Applied: Nemotron's "second opinion" on uncertain bricks is dropped (D25, it only explains); the PRD judging table names perception, reasoning, planning, manipulation. **Not applied, awaiting Saliha's yes, then @nate's:** (a) the verdict inside the VLA's two strings, chosen before the first SmolVLA recording; (b) a 15-minute leader-teleop rehearsal of every stage before the first recorded episode. **Open question for the mentors:** SmolVLA is fine-tuned with LeRobot (D20): acceptable for the 20-point Studio criterion? Say no on this row to anything you object to. **2026-11-14 14:26: (a) and (b) are both adopted, see the two rows above.** **@nate 16:16: yes**; the mentor question on SmolVLA trained with LeRobot stays open (a no would move SmolVLA to Studio's trainer, D20) | 2026-11-14 14:19 |
| 2026-11-14 12:40 | @saliha | @all | 🔀 scope proposal | **PrePostProcessor leaves the cut order** (it is built, `main` `4c96ef0`, decisions.md D30): CLAUDE.md item 7 is removed and PRD F2 / §10 now say built. The detector can also be exported with preprocessing inside the graph (`model_ppp.xml` beside `model.xml`); the benchmark reports both rows plus an operator-support table. Say no on this row if you object; the plain IR stays the default until the measured numbers pick. **@nate 16:16: yes** | 2026-11-14 12:40 |
| 2026-11-14 08:50 | @saliha | @harry | 📨 for you | **Ready to wire into `run.py`** (on `main` @ `487ddf5`; details in your brief's v2.5 block): `perception.scene.SceneLocator` (drop-in for `CountLocator`), `scene.tall_object` → `hold`, `scene.brick_in_bowl` → place success, `perception.reason_trace.ReasonTrace` → `note`/panel, and a `DANCE` step after the zone is empty (`robot.dance.dance(home)`) + a narrator line. Inspector scores are now raw (use `t_low`/`t_high`). **@harry 11:37: wired** `SceneLocator` (once `config/scene.yaml` has the zone), non-brick objects → obstacle trigger, `ReasonTrace.note()` → LOG `note` + region on the panel, dance + line after an empty zone. **Still open:** `brick_in_bowl` (top-camera view is blocked by the arm right after a place; when to check is Harry's call) and `tall_object` (needs RealSense depth in capture) **@harry 16:10: `brick_in_bowl` wired (after home); `tall_object` still open (needs depth in capture).** | 2026-11-14 08:50 |
| 2026-11-14 07:15 | @saliha | @all | 🔀 scope proposal | **PRD v2.5 on `context` (`5da0552`), re-sync.** A research pass (6 research agents + design + critic) put an ordered 🆕 v2.5 block at the top of each brief's ▶ Current tasks. Same vision. Highlights: no RL (D1, numbers in), every stage verified with reason codes/deadlines (D22), recovery order look-again → roll → re-grasp (D7), two fixed VLA strings + language-swap test + single-colour ACT hedge (D23), device/efficiency measured (D24), Nemotron advisory only (D25), **red-lego smoke test first** (D26). Bugs listed per person. Say no on this row to anything in your block. **@harry 05:41: yes** to the whole block, and yes to `run.py` calling `perception/scene.py` (zone gate + bowl-region check). **@nate 05:54: yes** to the whole block; N1's ACT export goes through Studio's Python API or runs on Modal (the `physicalai` CLI crashes on Windows: `fcntl`) | 2026-11-14 07:15 |
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
| Saliha | `saliha006` | **AI/ML**: computer vision (Anomalib), edge-AI optimisation (OpenVINO), Nemotron reasoner; doc owner | `aiml-perception-saliha` | `perception/`, `bench/`, `reasoner/` | Station live (arms recalibrated, teleop, grip band 10-23, knock-tolerant reads, `.env` complete, Nemotron live); next: real-brick photos and the detector (S3/S4) once the dock, regions and poses are done, then the scripted gate with Harry |
| Nate | `aldrichbanas07` | **Robotics and robot learning**: robot I/O, imitation-learning policies (ACT, SmolVLA), Modal training + logs | `robotics-policies-nate` | `robot/`, `policies/`, `train/` | Box room built; `robot/drive.py` on `main` (`73fd08a`, D35). Nate: guide gap and heights, tag, tip test, teach the dock and strokes; recording waits on the follower fix (Saliha's 21:35 row) |
| Harry | `Harryt3nn` | **Systems and integration**: orchestration, ElevenLabs voice (live reasoning + cowboy switch), Aiven streaming, demo, submission | `systems-voice-harry` | `run.py`, `common/`, `fallback/`, `ui/`, `narrator/`, `telemetry/`, `config/`, `README.md`, `docs/` | A6 playback done, A5 PostgreSQL live; next: station (H5, bowl check, 15:30 gate); Kafka waits on the service |

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
- **Intel laptop (2026-11-15 07:46):** `main` after `a6fffb3`: 405 pass with `-m "not slow"` (1 skipped), mock sorts 5. Real photos through the deployed Inspector: good 21.6–23.7 (in-sample), defective 66.0–76.9, 2/42 uncertain. Nemotron real-brick line check 16/16 (`bench/results.md`).
- **tests (2026-11-14 17:25):** `main` @ `2e38418`: 277 pass (same command, 3 skipped; the episode audit and colour hedge tests also run in the robot environment: 20 pass). Live Nemotron line, N5 hedge and the Nemotron line check are in; none run on real bricks yet. My `reasoner/tests/test_evaluate.py` clashed with `perception/tests/test_evaluate.py` and broke whole-suite collection on `main` for about 5 minutes (renamed `test_line_check.py`); no duplicate test basenames remain.
- **Intel laptop (2026-11-14 17:51):** after merging everyone's `main`: 276 pass in `.venv` incl. slow (`pytest common fallback narrator telemetry policies robot perception bench reasoner ui`), 73 in `.venv-robot` (`robot policies train`); mock sorts 5. Mains power, stand-in PaDiM INT8 p50: CPU 8.9, GPU 1.0, NPU 7.2 ms. 5-minute run: NPU 0.96× (no slowdown), CPU 1.06×, GPU 1.43×. ACT probe: NPU 8.9 ms, GPU 4.2 ms, CPU 65.7 ms per call. Station: RealSense + webcam + one arm detected; wrist camera not. Pushed to GitHub 2026-11-14 18:00.
- **Intel laptop (2026-11-14 16:58):** `main` @ `109c803`: 224 pass with `-m "not slow"` in `.venv` (229 with the slow ones in a test environment), 56 in `.venv-robot`; mock loop sorts 5 bricks. Devices CPU, GPU, NPU. PaDiM INT8 p50 (stand-in model, on battery, n=100): CPU 9.6 ms, GPU 1.0 ms, NPU 7.2 ms; PyTorch CPU 18.4 ms; all operators run on all three devices. Rebaseline parts here: train 18 s, export FP16 + INT8 16 s. Full table: `bench/results.md`.
- **tests (2026-11-14 16:19):** `main` @ `668933e`: 238 pass (`pytest common perception bench reasoner robot policies train fallback narrator ui telemetry -m "not slow"`, 2 skipped; the episode audit's 8 tests run in the robot environment). The Intel laptop is not reachable over SSH right now (hotspot or Wi-Fi power saving); OpenVINO there still lists only the CPU until the driver commands on the board are run.
- **tests (2026-11-14 14:49):** `main` @ `16614ca`: 202 pass (`pytest common perception bench reasoner robot policies train fallback narrator ui telemetry -m "not slow"`, 1 skipped); N3 grasp band and the image audit landed, not yet on the arm or real bricks.
- **perception/bench (2026-11-14 12:40):** `main` @ `4c96ef0`: 175 pass (`pytest common perception bench reasoner robot policies train fallback narrator ui telemetry -m "not slow"`, 1 skipped); in-graph preprocessing FP16 CPU p50 44.5 → 38.5 ms (this laptop, stand-in bricks). Not yet run on the Intel laptop or real bricks.
- **Plan (2026-11-14 05:47):** PRD v2.5, `context` @ `5da0552`.
- **robot/policies/train (2026-11-14 16:56):** `main` @ `f22367c`: 128 pass across `robot`, `policies`, `fallback`, `train`, `common` (1 Studio-only test skipped).
- **Modal (2026-11-14 17:13):** red-lego smoke passed for both policies: SmolVLA (1.8 min) and ACT (60.1 min, mostly the quantile pass); both OpenVINO exports run through `InferenceModel` on CPU (SmolVLA 50×6 in 1.9 s, ACT 100×6 in 97 ms, Modal CPU), SmolVLA matches LeRobot to 2.6e-6. Training app redeployed 17:13. Training launches: `python -m train.launch` (`train/launch.py`).
- **perception (2026-11-14 04:30):** `main` @ `99f1d09`: 28 tests pass (4 slow); live Nemotron line 1.7–2.7 s. Not yet run on the Intel laptop or real bricks.
- **`main` (2026-11-14 16:15):** @ `9da720e`, code in every area. Plan docs on `context`.

---

## Log (newest first)

### 2026-11-15 08:10 — fix — Gentler scripted motion, same-slot grasp retry, honest placing line, demo moments as tests — @saliha for @harry [conflicts: @nate @harry]
- **Where:** `systems-voice-harry-agent` → `systems-voice-harry` · merged to `main`: yes
- **Did:** `ScriptedMover` (station test 07:42): far moves raise to home's height, turn, then lower; pick_above↔pick at 2°/step; every move with a brick at ≤4°/step (`step_cap` sets and restores `io.MAX_STEP_DEG`); 0.3 s before closing, 0.5 s before lifting, 0.3 s at the bowl, open, 0.5 s. Each move now finishes its command on the exact pose (it used to stop up to 4° short). A missed pick retries the **same slot** with jaws at 80 and 10% deeper (cap 110% of pick_above→pick), then moves on; jaws that read below `GRIPPER_EMPTY_BELOW` after closing open and close once more 10% deeper. `--search-cm CM` (off) also shifts that retry sideways. Kept inside the mover, not an attempt argument: `pick_and_present()` is the frozen contract. `run.py`: the placing line quoted the uncertain first score after a second look, called a still-uncertain brick "over my limit", and rounded 65.1 vs 65.38 to "65 under 65"; now the settling look, two decimals. Mission control shrinks long lines (a learned run's mover names ran off the window). `common/tests/test_demo.py`: look-again, two misses → help line → P, obstacle cowboy, H hat, e-stop mid-place, summary + dance, `--mock --drive`, same-slot retry
- **Touched:** `fallback/scripted.py`, `run.py`, `ui/mission_control.py`, tests
- **⚠️ Conflicts:** @nate: all TUNE constants at the top of `fallback/scripted.py`, untested on the real arm; a retry pick with a re-close can take ~12-15 s against the 20 s PICK deadline. @harry: placing line wording now has two decimals

### 2026-11-15 08:00 — bench — INT8 PatchCore measured, not deployed — @saliha [conflicts: none]
- **Where:** `aiml-perception-saliha` @ `660396a` · merged to `main`: yes (`a220160`)
- **Did:** NNCF INT8 of the real-brick PatchCore: 29 MB vs 114 MB, CPU 25.5 ms vs 43.9, GPU 3.0, NPU 27.2. Scores shift by up to 9 points, so the FP32 thresholds don't carry over (same verdict on 8 of 20 photos); good and defective still separate (gap 25.9 vs 42.3). The demo keeps FP32. Table in `bench/results.md`; decisions D6 (PatchCore, Verified) and D8 updated on `context`.
- **Touched:** `bench/results.md`
- **Brief task:** none
- **⚠️ Conflicts:** none

### 2026-11-15 07:46 — feat — `scene.brick_px`: pixel centre of the biggest brick in a wrist frame — @saliha [conflicts: none]
- **Where:** `aiml-perception-saliha` @ `a6fffb3` · merged to `main`: yes
- **Did:** for a later visual-servo pick; same saturation mask as `analyse` (now shared), returns None below 200 px (TUNE). Not wired anywhere; tested on synthetic images only. After merging Nate's latest `main`: 405 pass (`-m "not slow"`), mock sorts 5.
- **Touched:** `perception/scene.py`, `perception/tests/test_scene.py`
- **Brief task:** none
- **⚠️ Conflicts:** none

### 2026-11-15 07:46 — feat — Policy smoothing options, snap to the inspect pose after a learned pick, export fetch-and-check — @saliha for @nate [conflicts: @nate @harry]
- **Where:** `robotics-policies-nate` @ `d603edc` · merged to `main`: yes
- **Did:** `policies/episode.py`: `Smoothed(model, alpha)` (moving average) and `TemporalEnsemble(model, m=0.01, query_every=1)` (ACT's overlapping chunks, oldest weighted most) wrap any policy; off unless a caller wraps the model, so behaviour is unchanged. Tests show both stay under the speed cap, reach the target, and the ensemble halves the worst step-to-step jump of back-to-back chunks. `LearnedMover.pick_and_present` now moves to the exact taught `inspect` pose (current gripper value) after a successful pick. `python -m train.fetch <job>` fetches `<job>/openvino` into `runs/exports/<job>` and checks it on CPU and GPU (ACT probe: 87 ms CPU, 17 ms GPU first call). 403 + 133 pass, mock sorts 5.
- **Touched:** `policies/episode.py`, `policies/mover.py`, `train/fetch.py`, `train/export.py` (shared zero observation), `train/runs.md`, tests
- **Brief task:** none
- **⚠️ Conflicts:** @nate: your area; the snap adds up to 1 s after each learned pick and commands the gripper at its read value (as `reinspect` already does), check the brick does not slip. @harry: nothing is wired yet; enabling smoothing is one line in `run.py` (`Smoothed(TemporalEnsemble(model), 0.5)`). Both: the app `.venv` (jsonargparse 4.46) cannot build any `InferenceModel` (`'ArgumentParser' object has no attribute 'instantiate'`), so `run.py` with a learned policy fails on every device under `.venv`; `.venv-robot` (4.53) works.
- **Status:** open

### 2026-11-15 07:43 — fix — Deployed detector checked on the real photos; line checker stops rejecting orange bricks; real-brick Nemotron table — @saliha [conflicts: @harry]
- **Where:** `aiml-perception-saliha` @ `66f673d` · merged to `main`: yes
- **Did:** `bench/real_photos.py` runs the deployed PatchCore IR through `Inspector` on all 66 saved photos (CPU): good 21.6–23.7 (in-sample, all perfect), defective 66.0–76.9 (40 defective, 2 uncertain, 0 perfect); a slow test guards it. Nemotron line check on 16 real photos: 12/16 at first, all 4 "contradictions" were correct lines about orange good bricks, because `reasoner.live.grounded` rejected any "orange" in a perfect line. It now matches "orange bowl"/"purple bowl": 16/16, p50 2.0 s, p95 2.6 s, 0 failures. Table in `bench/results.md`. 389 pass (`-m "not slow"`), mock sorts 5.
- **Touched:** `bench/real_photos.py`, `perception/tests/test_real_photos.py`, `reasoner/live.py`, `reasoner/tests/test_live.py`, `bench/results.md`
- **Brief task:** none
- **⚠️ Conflicts:** @harry: live lines about a good orange brick were being rejected and replaced by the template on the robot; they will now be spoken. Nothing to change on your side.

### 2026-11-15 03:25 — docs — Pitch slides; ElevenLabs write-up, README and demo script brought up to Pix — @harry [conflicts: @saliha @nate]
- **Where:** `main` @ `cc5dfd6` (docs) · slides: https://claude.ai/artifact/KsuECp6J2nvritHEstYSjN (private until Harry shares it)
- **Did:** six slides for the pitch: cover (Pix), the four layers with their chips, Intel deployment (measured: PaDiM INT8 GPU 1.00 / NPU 7.17 / CPU 8.91 ms, NPU ~11 W and steady over 5 min, ACT on the NPU 8.9 ms; stand-in-brick caveat on the slide), Pix's voice loop, reliability (trial numbers as [__] placeholders until the 20 trials), close. `docs/submission.md` ElevenLabs section, README and the demo script describe Pix as it is now.
- **📨 Needs:** after the trials, fill the [__] on the reliability slide from `bench.trials`; @saliha: replace the device numbers if the real-brick re-run changes them
- **Status:** open

### 2026-11-15 03:10 — feat — Pix is funny — @harry [conflicts: none]
- **Where:** `systems-voice-harry` → `main` · merged to `main`: yes
- **Did:** every cached line, live verdict, summary and spoken answer rewritten with humour: calm Pix dry and deadpan ("Cleaner than my code. Purple bowl."), cowboy Pix folksy ("More scuffs than my boots. Orange bowl."). Facts first (score, threshold, mark, bowl), joke after; verdicts choose among 2-3 wordings by score, the grip line rotates by brick; the e-stop line stays plain. 58 clips regenerated (3,409 characters), levelled to -12 dBFS. 390 tests pass.
- **Touched:** `narrator/lines.py`, `narrator/live.py`, `narrator/answers.py`, `narrator/clips/`, `run.py`, tests
- **Status:** open

### 2026-11-15 02:55 — feat — Pix louder, interruptible, narrates each pick unprompted; funnier cowboy lines — @harry [conflicts: none]
- **Where:** `systems-voice-harry` → `main` · merged to `main`: yes
- **Did:** (1) Loudness: the calm voice measured 12.6 dB quieter than the cowboy (median RMS -26.4 vs -13.8 dBFS); every line (cached, new, live) is now levelled to -12 dBFS with a soft ceiling (`narrator/loudness.py`; both voices measure -12.0/-12.2 dBFS, peaks just under full scale). (2) Unprompted pick narration: before each pick the tally plus why that brick (the scene check takes the most isolated one; three wordings in turn), "Got it…" when the grip holds. (3) Interrupt: a sentence naming Pix cuts the clip playing (winsound async / aplay terminate), drops queued and in-flight live lines, then answers (heard: cut 2.5 s into a long line, answer ready 407 ms later). Echo guard: a heard sentence of 5+ words with 70%+ of its words in one of Pix's lines from the last 20 s is ignored, so Pix never answers itself. (4) Cowboy `hat_on` and `obstacle` replaced with the team's funnier lines; the defective exclamation now uses its own short "Holy smokes!". 389 tests pass; narrator tests 3/3 repeat runs.
- **Touched:** `narrator/` (loudness, player, live, listen, lines, clips), `run.py`, tests
- **Status:** open

### 2026-11-15 02:45 — feat — Pix hears you on Windows too; microphone check command — @harry [conflicts: none]
- **Where:** `systems-voice-harry` → `main` @ `8068a6e` · merged to `main`: yes
- **Did:** where there is no `arecord`, the microphone comes from `sounddevice` (new dependency, Harry's call, declared in `requirements.txt`; ~1 MB, recording only), the same raw 16 kHz mono stream, so "Hey Pix" can be rehearsed with `python run.py --mock` on a dev laptop. `python -m narrator.listen` = microphone check: live loudness bar, then what was heard and what Pix took it to mean (for `listen.threshold` at the station). The Intel laptop keeps using `arecord`. 374 tests pass.
- **Touched:** `narrator/listen.py`, `narrator/__init__.py`, `requirements.txt`, tests
- **Status:** open

### 2026-11-15 02:20 — feat — Pix's eyes: object recognition on the wrist camera, trainable on the Intel laptop — @harry [conflicts: @saliha]
- **Where:** `systems-voice-harry` → `main` · merged to `main`: yes
- **Did:** `narrator/vision.py`: CLIP ViT-B/32 image encoder converted to OpenVINO (176 MB IR, built in 5.6 s here), names brick / plate / purple bowl / orange bowl or "unknown" + a best guess from 19 everyday things; `capture` / `train` / `check` commands; trained softmax classifier on our own photos replaces zero-shot once it exists. `Cell.look` (wrist camera) feeds "Hey Pix, what do you see now?". Measured on Harry's laptop: 18 ms per frame on CPU. Honest limit: on a drawn red block zero-shot says "unknown, guess person", so the real-photo training step matters. 372 tests pass (incl. the built model on a frame).
- **Touched:** `narrator/vision.py`, `narrator/answers.py`, `run.py` (`Cell.look`, `vision_look`), `docs/station.md` 5b, tests
- **⚠️ Conflicts:** @saliha: recognition overlaps perception (kept in `narrator/`); the wrist camera is read for questions only
- **📨 Needs:** station time: build + ~10 min of photos
- **Agreed by:** @harry
- **Status:** open

### 2026-11-15 01:40 — feat — Drive wired behind --base; energy per brick in every run; critic doc items — @harry [conflicts: @nate @saliha]
- **Where:** `systems-voice-harry` → `main` · merged to `main`: yes
- **Did:** `run.py --base` opens a real run with Nate's `robot.drive.approach` (dock + stroke poses checked before anything moves, 60 s deadline, drive narration plays as built). `Cell.run` is wrapped in `bench.power.measure()`: each run logs package energy, average power, peak temperature and joules per brick (`ENERGY` row); none on machines without a readable RAPL counter. Docs: white plates or loose bricks (a coloured plate reads as one obstacle), Physical AI Studio as part of Intel's Robotics AI Suite, the drive teach/check steps and the RAPL chmod. 364 tests pass (full suite after merging main).
- **Touched:** `run.py`, `common/tests/`, `README.md`, `docs/`
- **⚠️ Conflicts:** @nate: the drive is called from `run.py` now; @saliha: `run.py` imports `bench.power`
- **📨 Needs:** none
- **Status:** open

### 2026-11-15 00:07 — feat — `robot/drive.py`: the box-room drive, tested on the mock robot; `io.connect` checks the calibration first — @nate [conflicts: @harry @saliha]
- **Where:** `robotics-policies-nate` @ `73fd08a` · merged to `main`: yes
- **Did:** `robot/drive.py` (D35) strokes (reach, touch, drag, lift through `robot.io.move_to`) until the overhead camera sees the tag (ArUco 4×4 ID 7) at the taught dock pose, and returns the centimetres travelled (scale from the tag's own size, about 2%). It returns None after 2 strokes without progress, after 8 strokes, or when the stage deadline fires; without the tag it trusts the corner stops after 5 strokes and answers with the planned 41 cm. Commands: `--make-tag`, `--teach-dock` (`config/dock.yaml`), `--check`. 13 tests on the mock robot with synthetic overhead frames. `robot/io.connect()` now raises the missing-calibration error before importing the robot package, and `test_degree_sizes_…` skips where that package is missing. 174 pass in `robot policies train fallback common` (2 skipped).
- **Touched:** `robot/drive.py`, `robot/tests/test_drive.py`, `robot/io.py` (order of one check), `robot/tests/test_io.py` (one skip)
- **Brief task:** N10 code done; tuning waits on the station
- **⚠️ Conflicts:** @harry: the wiring, the teach names, the dock file and the deadline (board row). @saliha: two lines of `robot/io.py` and one line of your `test_io.py` changed (the calibration check moved first; a skip where the robot package is missing); pull before editing them
- **📨 Needs:** Harry's wiring and teach names
- **Agreed by:** @nate (D35); n/a for the `io` fix (one correct answer)
- **Status:** open

### 2026-11-14 23:49 — decision — Box-room drive designed (D35) and the room built; export-bug notes corrected — @nate [conflicts: @harry @saliha]
- **Where:** `robotics-policies-nate` → `main` (this push); `context` (D33, D35, Nate's brief) · merged to `main`: yes
- **Did:** the drive: floor strokes into a dock at the plates (guides, funnel, corner stops, free floor ahead for the last strokes), checked by a tag on the board read by the overhead camera, with a fixed stroke count as the fallback; inspection camera on the board. Room built (~23:00): start 29 cm, travel 12, dock 29, about 41 cm of drive in a room about 80 × 40.6 cm. Build sheet with scale drawings: https://claude.ai/artifact/Db57fpWKR4MZkKe6zeT4y4. Corrected the #1414/#1384/#1403 wording in `train/export.py` comments and `train/runs.md` from Saliha's research fix.
- **Touched:** `train/export.py` (comments only), `train/runs.md`, `progress.md`; `context`: `decisions.md` (D33, D35), Nate's brief
- **Brief task:** N10 designed and built; N11 blocked on Studio's version
- **⚠️ Conflicts:** @harry: the stroke poses in your `config/waypoints.yaml`, the `cell.approach` wiring and the 30 s `DRIVE` deadline (board row). @saliha: capture after the inspection camera is mounted and the room frozen; real picks and the rolled view; plate distance may be unnecessary; overhead height (board row)
- **📨 Needs:** Harry's OK on the `drive_*` names; Nate's measurements (pending)
- **Agreed by:** @nate (the drive design); Harry's 19:45 plan (parked spot, inspection camera on the board); Saliha's PRD §0 21:35 line (scripted drive into a stop block, everything recorded at the parked spot)
- **Status:** open

### 2026-11-14 23:30 — feat — Trigger C built: a cowboy exclamation on every calm defective verdict; freeze lifted — @harry [conflicts: @saliha @nate]
- **Where:** `systems-voice-harry` → `main` · merged to `main`: yes
- **Did:** Saliha's 21:35 trigger C (D13): every defective verdict said in the calm voice gets one cached cowboy exclamation first ("Holy smokes!", "Well I'll be!", "Yeehaw!", rotating), then the calm explanation with the score; with the hat on nothing extra plays (the whole line is already the cowboy's). Heard on Harry's laptop: three defective verdicts, three different exclamations, each followed by its calm line. 342 tests pass. **Freeze:** Harry says the 23:00 feature freeze no longer applies (Nate called it flexible at 19:30); work continues on features where it helps the demo.
- **Touched:** `narrator/__init__.py`, tests
- **⚠️ Conflicts:** @saliha: D13 trigger C is now Built
- **📨 Needs:** none
- **Agreed by:** @saliha (decided 21:35), @harry (yes 23:25)
- **Status:** open

### 2026-11-14 23:20 — feat — The robot is Pix: "Hey Pix, …" questions and hat by voice (post-freeze, freeze flexible per Nate) — @harry [conflicts: @saliha @nate]
- **Where:** `systems-voice-harry` → `main` · merged to `main`: yes
- **Did:** the listener acts only on sentences that name Pix (Harry: "hey pix for everything"; sound-alikes like "picks" count; "Pix" is a speech-to-text key term). Questions answered from the cell's own facts (`Cell.facts()`, `narrator/answers.py`): what it sees, how many sorted, why that bowl, what it's doing, who it is; anything else gets a hint. End to end with generated speech: "Hey Pix, what do you see now?" heard in 750 ms and answered with the stage, last score and threshold; "Hey Pix, why that bowl?" answered in the cowboy voice while the hat was on; "I'm taking the hat off" without the name was ignored. Demo script and README updated. Full suite 335 passed, 4 skipped (after installing `physicalai[so101]` locally, see the board row).
- **Touched:** `narrator/listen.py`, `narrator/answers.py`, `narrator/__init__.py`, `run.py`, `docs/demo-script.md`, `README.md`, tests
- **⚠️ Conflicts:** @saliha @nate: hat commands now need "Hey Pix" too; `physicalai` undeclared (row)
- **📨 Needs:** @saliha @nate: declare `physicalai[so101]`
- **Agreed by:** @harry (wake word for everything; answers from facts)
- **Status:** open

### 2026-11-14 23:15 — fix — N8 grip band measured (10-23); tests use the measured brick reading; recording varies brick angle — @saliha [conflicts: @nate @harry]
- **Where:** `systems-voice-harry` and `robotics-policies-nate` → `main` · merged to `main`: yes
- **Did:** Three hand-moved runs on the loose follower (`python -m robot.readings`): shut on nothing averages 1.5 (1.0-2.4), a Duplo brick 17.4 (15.2-19.8), half open 29.4 (25.7-31.8), wide 96.3. `robot/io.py`: `GRIPPER_EMPTY_BELOW` 10 (was 5), `GRIPPER_HOLD_MAX` 23 (was 45), `GRIPPER_OPEN` 60 unchanged. Test fixtures that used 30 for a held brick now use 17 (Harry's `common/tests/test_run_real.py`, `fallback/tests/test_scripted.py`; Nate's `policies/tests/test_mover.py`, `train/tests/test_episode_audit.py`, whose fake gripper now closes gradually). `train/RECORDING.md`: vary brick angle and colour each round; record only at the parked spot. `robot.readings --live` prints the gripper twice a second. 314 + 93 tests, mock sorts 5.
- **Touched:** `robot/io.py`, `robot/readings.py`, test fixtures above, `train/RECORDING.md`
- **Brief task:** N8 → ✅
- **⚠️ Conflicts:** @harry: two test fixtures in your folders (value only); @nate: your grip band and audit tests
- **📨 Needs:** none
- **Status:** open

### 2026-11-14 22:30 — feat — Station fixes: knock-tolerant reads, readings and goto tools, recording protocol, follower calibration — @saliha [conflicts: @nate]
- **Where:** `robotics-policies-nate` → `main` @ `3487684` · merged to `main`: yes
- **Did:** `robot.io.observe` retries four times 50 ms apart, so a knock's supply dip no longer kills a run (a dead bus still raises); Studio's own SO-101 driver on the laptop is patched the same way (12 attempts, 20 ms apart; backup `so101.py.orig`, active after a backend restart). New `python -m robot.readings` (loose follower, joint medians per time window; for N8) and `python -m robot.goto <pose> --gripper 0` (moves to a taught pose at the speed cap, holds it, Enter sends it home; for the brick photos; `home` must be a resting pose because the arm goes limp at the end). `train/RECORDING.md`: Studio's dataset folder, `physicalai-studio hf dataset export`, PR #1403 is fixed. `config/so101_follower.json` updated from the 20:31 recalibration. Station: both arms recalibrated (190-240° per joint), teleop works; the leader's power plug had come out (all six servos silent).
- **Touched:** `robot/io.py`, `robot/readings.py`, `robot/goto.py`, `robot/tests/`, `train/RECORDING.md`, `config/so101_follower.json`
- **Brief task:** N8 tooling → 🟡 (readings tool built, readings pending) · knock dropouts → 🟡 (software side done)
- **⚠️ Conflicts:** @nate: your `robot/` and `train/RECORDING.md`, through your branch; review when you can
- **📨 Needs:** none
- **Status:** open

### 2026-11-14 20:20 — docs — Box-room docs; measured device numbers in the submission; trial report rehearsed — @harry [conflicts: @saliha @nate]
- **Where:** `systems-voice-harry` → `main` @ `f1d9279` · merged to `main`: yes
- **Did:** `docs/demo-script.md` now follows the box room minute by minute (drive, hat by voice, tally, borderline, mug, summary) with a table-top fallback; `docs/station.md` builds the room and parked spot before anything is taught and adds the microphone check; README describes every voice feature with measured speeds. `docs/submission.md` and the README carry Saliha's measured device numbers (PaDiM INT8 p50 GPU 1.00 / NPU 7.17 / CPU 8.91 ms vs PyTorch 17.27 ms; net 33 / 68 / 300 mJ; NPU ~11 W and steady over 5 min; ACT on the NPU 8.9 ms), marked as stand-in-brick numbers until the real-brick re-run. `bench.trials` ran first time on a 20-brick rehearsal log (20/20, 19/20 with a planted mistake named); the morning steps are in `docs/trials-slide.md`. The wheel base may be dropped (team discussing, not decided): every voice feature stays; the drive lines only run when `cell.approach` is set.
- **Touched:** `README.md`, `docs/`
- **⚠️ Conflicts:** @saliha: your numbers quoted in `docs/submission.md` and the README; correct them there if the real-brick re-run changes them
- **📨 Needs:** none
- **Status:** open

### 2026-11-14 19:50 — feat — Chatty but relevant: tally between bricks, recovery steps out loud; live lines in parallel; credit floor; follower port — @harry [conflicts: @saliha @nate]
- **Where:** `systems-voice-harry` → `main` · merged to `main`: yes
- **Did:** (1) Between bricks the robot says the tally ("That's 3 sorted so far: 2 perfect, 1 defective. On to the next one.") and before each recovery step the borderline score it rechecks ("Still 0.27, right between my lines. Rolling it ninety degrees…"), cached fallbacks in both voices. (2) Fix found by a run at real-arm pace (~3 s per move): a single synthesis queue made most live lines wait and time out; each line now has its own request (3 at once) and a late older line is dropped, never said out of order. Same run after the fix: all 9 live lines in 547–1594 ms. (3) Credit floor: live lines stop after 12,000 characters per run; a run starting under 10,000 account credits uses cached lines (balance read needs the key's `user_read` permission, not set yet). (4) `config/robot.yaml` follower by-id port + `config/so101_follower.json`. 220 tests pass; narrator tests 5/5 repeat runs.
- **Touched:** `narrator/`, `run.py`, `config/robot.yaml`, `config/so101_follower.json`, tests
- **⚠️ Conflicts:** @saliha: move the untracked `config/so101_follower.json` on the Intel laptop aside before pulling (19:55 row)
- **📨 Needs:** none
- **Status:** open

### 2026-11-14 19:30 — decision — Nate's answers: normalized units, Studio SmolVLA in parallel, box-room drive, tonight's order — @nate [conflicts: @saliha @harry]
- **Where:** `robotics-policies-nate` → `main`; `context` (D20, D29, D33, Nate's brief) · merged to `main`: yes
- **Did:** (1) yes to normalized joint units (D29); (2) SmolVLA: LeRobot stays the proven path, plus one Studio SmolVLA job on Modal on the same data after a smoke test of Studio's Modal target (D20, N11); (3) yes to the box-room demo: the base drives in the demo and Nate owns the motion through `cell.approach` (D33, N10); (4) yes to tonight's station order, flexible on the freeze; pandas, pyarrow and pyyaml declared in `train/requirements.txt`.
- **Correction:** my 17:13 and 17:25 entries said the red-lego smoke policies' actions were "in degrees". That set is normalized (D29), so they were in normalized units; `train/runs.md` and D20 are corrected.
- **Touched:** `train/requirements.txt`, `train/runs.md`, `progress.md`; `context`: `decisions.md`, Nate's brief
- **Brief task:** N10, N11 added
- **⚠️ Conflicts:** @saliha: merge the units branch (it edits Nate's `robot/io.py`, `train/audit.py`, `train/card.py`, `train/RECORDING.md`; all fine by Nate). @harry: the drive plugs into `cell.approach`; Nate's design comes first
- **📨 Needs:** none
- **Agreed by:** @nate (all four answers); @harry (units 18:45; box-room and station order are his proposals); @saliha (units, Studio question)
- **Status:** open

### 2026-11-14 19:05 — feat — Hat on and off by voice; hat stays until taken off — @harry [conflicts: @saliha @nate]
- **Where:** `systems-voice-harry` → `main` @ `789142a` · merged to `main`: yes
- **Did:** `narrator/listen.py`: the microphone (`arecord`, 16 kHz mono) is cut into utterances by a loudness gate; each goes to ElevenLabs speech-to-text (`scribe_v1`, keyterm "cowboy hat"), one at a time; a phrase check turns "putting a cowboy hat on you" / "taking the hat off" into the persona switch. The hat now stays on until it is taken off (Harry's call), with a cached line each way ("Well I'll be, a cowboy hat! Yeehaw, partner. Let's ride." / "Ohhh, I'm no longer a cowboy... Ahem. Back to business."); H toggles it. Heard end to end on Harry's laptop through the narrator. **Key fixed 19:20:** real transcription verified end to end (synthetic speech through the listener): "I'm putting a cowboy hat on you" → hat_on in 922 ms, "I'm taking the hat off now" → hat_off in 1344 ms; `scribe_v1` 812 ms on its own. Microphone itself untested (needs the Intel laptop). Loudness threshold TUNE at the station (`config/voices.yaml` `listen.threshold`). 217 tests pass.
- **Touched:** `narrator/listen.py`, `narrator/persona.py`, `narrator/__init__.py`, `narrator/lines.py` + 2 clips, `ui/mission_control.py` (H toggles), `config/voices.yaml`, `run.py` (`--no-listen`), tests
- **⚠️ Conflicts:** @saliha @nate: the H key now toggles the hat (was one-shot); the robot listens to the microphone during real runs (`--no-listen` to stop it)
- **📨 Needs:** none (Harry updates his key)
- **Agreed by:** @harry (ElevenLabs speech-to-text; hat on until taken off)
- **Status:** open

### 2026-11-14 18:25 — decision — Joint units: normalized, safety sizes kept in degrees per joint (proposed, waiting on Nate and Harry) — @saliha [conflicts: @nate @harry]
- **Where:** `aiml-perception-saliha-units` @ `cc81229` · merged to `main`: yes, 2026-11-14 19:52 after @harry 18:45 and @nate 19:30 said yes
- **Did:** Saliha chose normalized joint units (mentor: most teams use them; Studio's default; our red-lego smoke runs were normalized) over D29's degrees, before any episode is recorded. `robot.io` runs the driver normalized and converts degree-sized safety numbers per joint from the calibration (`io.units`, `io.within`), so the speed cap stays 5° per step on every joint and the re-inspect roll stays 90°. Gripper thresholds are unchanged (0-100 in both units). Tests: 287 app + 88 robot environment, mock sorts 5.
- **Touched:** `robot/io.py`, `robot/dance.py`, `robot/tests/test_io.py`, `policies/mover.py`, `fallback/scripted.py`, `train/audit.py`, `train/card.py`, `train/RECORDING.md`, tests, `config/waypoints.yaml` (comment)
- **Brief task:** none (D29 change)
- **⚠️ Conflicts:** @nate: your `robot/`, `policies/`, `train/` and decision D29; @harry: two lines in `fallback/scripted.py`
- **📨 Needs:** @nate, @harry: yes or no on the board row; until then `main` stays in degrees and Studio should not record
- **Agreed by:** @saliha, @harry, @nate
- **Status:** resolved by @saliha 2026-11-14 19:52 (merged; 309 + 88 tests pass, mock sorts 5)

### 2026-11-14 18:10 — feat — Unfamiliar objects named out loud; wrist camera in MJPG — @harry [conflicts: @saliha @nate]
- **Where:** `systems-voice-harry` → `main` @ `7821e3e` · merged to `main`: yes
- **Did:** `narrator/naming.py`: when an obstacle appears, the cached "Holy smokes!" plays at once and a worker asks the naming model (Saliha's pick) what it is; a cleaned name ("coffee mug", a/an handled) within 3 s is spoken live. Heard on Harry's laptop with a stand-in model: named in ~0.8 s; the live line itself was dropped twice because the venue Wi-Fi stalled ElevenLabs for 6–12 s, so the demo checklist now asks for a phone hotspot. `config/cameras.yaml` asks the wrist camera for MJPG (Nate's recordings). 198 tests pass.
- **Touched:** `narrator/naming.py`, `narrator/live.py`, `run.py` (`Cell.namer`), `common/capture.py` (`fourcc`), `config/cameras.yaml`, `docs/demo-script.md`, tests
- **⚠️ Conflicts:** @saliha: the naming model plugs in as `name_fn(bgr) -> str | None`; a `box_px` on `scene.Blob` makes the crop tight. @nate: wrist MJPG done
- **📨 Needs:** @saliha: the naming model (Nemotron VL or local)
- **Status:** open

### 2026-11-14 17:55 — feat — Live voice-over for the base drive; run summary; subtitles; camera paths — @harry [conflicts: @nate @saliha]
- **Where:** `systems-voice-harry` → `main` @ `5730a47` · merged to `main`: yes
- **Did:** (1) The demo opens with the wheeled base driving the arm to the table, talked over live: `Cell.approach` (Nate's base driver, a function returning cm travelled or None) runs as a `DRIVE` stage with a 30 s deadline (TUNE) before the first brick; the robot says how far it has to go ("about 42 centimetres out of my reach, so I'm driving over") and, on arrival, how far and how long; a failed drive = new reason `drive_failed` with its own help line. Cached fallbacks for all three lines in both voices. `python run.py --mock --drive 42` rehearses it: drive line ready 1156 ms after the stage started. (2) End-of-run summary spoken with the counts. (3) Mission control subtitles: the line being spoken under the feed. (4) `config/cameras.yaml` paths as Saliha mapped them (RealSense index0 = colour, checked). 187 tests pass; full suite on Harry's laptop 283 + slow 5; Intel laptop 282.
- **Touched:** `run.py`, `common/reasons.py` (+`DRIVE_FAILED`), `narrator/`, `ui/mission_control.py`, `config/cameras.yaml`, `docs/demo-script.md`, tests
- **⚠️ Conflicts:** @nate: the seam for your base driver is below (📨 row); `Reason` has a new value. @saliha: none
- **📨 Needs:** @nate: a base driver for `Cell.approach`
- **Agreed by:** @harry (base drive in the demo, talked over live)
- **Status:** open

### 2026-11-14 17:29 — feat — Dataset cards written from the data: `python -m train.card` — @nate [conflicts: @harry]
- **Where:** `robotics-policies-nate` · merged to `main`: yes
- **Did:** `train/card.py` writes a recorded dataset's Hugging Face card (`README.md`) from its own `meta/info.json` and `tasks.parquet`, the reject log and a fresh `train.audit` run: robot, episodes kept and rejected, frames, the three cameras, joint units, the exact task strings, the audit date. A dataset that fails the audit gets no card. Uploading stays a manual step (it is public). 4 tests; 41 pass in `train`.
- **Touched:** `train/card.py`, `train/tests/test_card.py`, `train/RECORDING.md`
- **Brief task:** none (RECORDING.md's dataset-card line; submission Links "Dataset cards on the Hugging Face Hub")
- **⚠️ Conflicts:** @harry: `docs/submission.md` Links can point at `<hf_user>/sortsense-pick` and `-place` once Nate uploads them; the cards default to the `apache-2.0` licence
- **📨 Needs:** none
- **Status:** open

### 2026-11-14 17:25 — test — Both smoke policies run end to end through our runner; SmolVLA on a CPU pauses ~7 s per chunk — @nate [conflicts: @saliha @harry]
- **Where:** `robotics-policies-nate` · merged to `main`: yes (notes only)
- **Did:** downloaded both smoke exports and ran them through `policies/episode.py` (`load` → `run_episode` → `robot.io.act`) on the mock robot, 150 steps each, on Nate's PC (Intel Core Ultra 5 125H CPU, not the demo laptop). Both give finite actions in degrees and the mock arm follows. ACT: ~0.1 s per 100-action chunk, 5.7 s for 150 steps (5.0 s nominal). SmolVLA: ~7.4 s per 50-action chunk, 26.8 s for 150 steps.
- **Touched:** `train/runs.md`
- **Brief task:** none new (follows A3)
- **⚠️ Conflicts:** @saliha: SmolVLA on CPU would stop the arm for seconds per chunk; the demo laptop's GPU drivers (your 16:01 row) decide whether placing looks smooth, and the number belongs in the D24 device table. @harry: ACT's pause is ~0.1 s every 3.3 s, fine for the pick
- **📨 Needs:** none
- **Status:** open

### 2026-11-14 17:22 — feat — Thermal run, ACT on the NPU, prompt revisions in the line check; station hardware detected — @saliha [conflicts: @harry @nate]
- **Where:** Intel laptop `main` (`a33923e`..`226086f`, merged with teammates' `main`) · merged to `main`: yes, pushed 2026-11-14 18:00 after the laptop got a GitHub login
- **Did:** `bench/sustained.py`: one model back to back per device for 5 min; stand-in PaDiM INT8 on mains: NPU 7.08 → 6.82 ms (0.96×, no slowdown, 14.7 W package), CPU 10.6 → 11.3 ms (1.06×, 20.5 W), GPU 1.00 → 1.43 ms (1.43×, 20.1 W). Device table re-run on mains: within a few percent of the battery run. `bench/act_npu_probe.py`: Studio ACT with our three cameras and 6 joints, random weights, exports in 6 s and compiles on the NPU (2.3 s, 8.9 ms per call; GPU 4.2 ms, CPU 65.7 ms). Merged with the other Saliha session's work: its `reasoner/evaluate.py` line check is kept (I dropped my duplicate harness and my duplicate NVIDIA text); it gains `--system` to measure a prompt revision on the same frames (`reasoner.client.explain` takes an optional system prompt), and `perception.evaluate` now writes its `runs/evaluate/cases.csv` from the real-brick run. Station: RealSense D415 (top) and webcam (inspect) open by path, one arm on `ttyACM0`, Studio running.
- **Touched:** `bench/sustained.py`, `bench/act_npu_probe.py`, `bench/results.md`, `reasoner/evaluate.py`, `reasoner/client.py`, `perception/evaluate.py`, tests; `config/cameras.yaml` locally only
- **Brief task:** S7 → 🟡 (device, operator, thermal, ACT probe done on a stand-in detector; final rows on the real model) · 22:00 Nemotron eval → 🟡 (check + prompt-revision flag built, real crops pending)
- **⚠️ Conflicts:** @harry: camera paths for `config/cameras.yaml` (you committed the same three paths, `1f9820e`, so mine stayed local). @nate: ACT on the NPU is possible, so the placement call is open again (board row)
- **📨 Needs:** a person: the second arm (its USB board answers, none of its motors do), `.env`

### 2026-11-14 17:13 — test — Red-lego smoke done: ACT trains, exports and runs; training app redeployed — @nate [conflicts: @saliha]
- **Where:** `robotics-policies-nate` · merged to `main`: yes
- **Did:** ACT smoke (Studio, 300 steps) finished in 60.1 min on an A100, almost all of it the quantile pass on a public set without q01/q99. Its OpenVINO export (137 MB) runs through `InferenceModel` on CPU: 100×6 chunk in 97 ms, inputs `state` + `images.<camera>`, the same keys `policies/episode.py` now sends. The deployed training app was redeployed, so Saliha's N4 SmolVLA recipe and N5 hedge argument are live for real launches.
- **Touched:** `train/runs.md`; Modal app `sortsense-train` redeployed
- **Brief task:** A1, A2, A3, N1 → ✅
- **⚠️ Conflicts:** @saliha: the export check is the ACT/SmolVLA half of the Intel bench; the IRs are on the Volume (`modal volume get sortsense-runs <job>/openvino`)
- **📨 Needs:** none
- **Status:** open

### 2026-11-14 17:20 — feat — Nemotron line check for the NVIDIA table: `reasoner/evaluate.py` — @saliha [conflicts: none]
- **Where:** `aiml-perception-saliha` → `main` · merged to `main`: yes
- **Did:** `python -m reasoner.evaluate cases.csv --persona calm|cowboy` sends each real inspection (image, label, score, thresholds, box) through the robot's own call and checker and prints lines consistent with the verdict with a 95% interval, failures, time to a line and every contradicting line. A failed request never counts as consistent. 6 tests with a fake model; not yet run on real bricks.
- **Touched:** `reasoner/evaluate.py`, `reasoner/tests/test_evaluate.py`
- **Brief task:** NVIDIA 20-frame eval (D11) → 🟡 harness done, needs real inspections
- **⚠️ Conflicts:** none
- **📨 Needs:** none

### 2026-11-14 17:15 — test — SmolVLA export matches LeRobot's own policy (parity) — @nate [conflicts: none]
- **Where:** `robotics-policies-nate` · merged to `main`: yes
- **Did:** `train/parity.py` runs identical inputs (random images and state, the real task's tokens, zero starting noise) through LeRobot's `SmolVLAPolicy` and the OpenVINO IR: max difference 2.6e-6 on actions up to 2.36; the exported tokenizer gives LeRobot's exact token ids. The export is deterministic (Studio traces it with zero starting noise; LeRobot samples random noise by default).
- **Touched:** `train/parity.py`, `train/runs.md`
- **Brief task:** A3 (SmolVLA half complete; ACT next)
- **⚠️ Conflicts:** none
- **Status:** n/a

### 2026-11-14 17:15 — feat — Nemotron's line spoken after each verdict; test-name clash fixed — @harry [conflicts: @saliha]
- **Where:** `systems-voice-harry` → `main` @ `d6fbc81` · merged to `main`: yes
- **Did:** `run.py` hands every inspection frame and signal to Saliha's `reasoner.live.LiveLine`; a grounded line comes back through `narrator.say(text=...)` and is spoken live after the template line (real runs only, and only with `NVIDIA_API_KEY` + `NEMOTRON_MODEL` set; `--no-live` turns both off). Renamed `narrator/tests/test_live.py` → `test_live_voice.py`: it clashed with `reasoner/tests/test_live.py` (pytest collection error on `main` for a few minutes, now fixed). 171 tests pass. Not yet heard end to end: Nemotron + voice on a real brick.
- **Touched:** `run.py`, `narrator/__init__.py` (`current_persona`), tests
- **Brief task:** add-on "one live ElevenLabs line from the Nemotron text (with Saliha)"
- **⚠️ Conflicts:** @saliha: your `LiveLine` is now called from `Cell._inspect` on every look (first look and each recovery look)
- **📨 Needs:** none
- **Status:** open

### 2026-11-14 17:13 — test — Red-lego smoke done: ACT trains, exports and runs; training app redeployed — @nate [conflicts: @saliha]
- **Where:** `robotics-policies-nate` · merged to `main`: yes
- **Did:** ACT smoke (Studio, 300 steps) finished in 60.1 min on an A100, almost all of it the quantile pass on a public set without q01/q99. Its OpenVINO export (137 MB) runs through `InferenceModel` on CPU: 100×6 chunk in 97 ms, inputs `state` + `images.<camera>`, the same keys `policies/episode.py` now sends. The deployed training app was redeployed, so Saliha's N4 SmolVLA recipe and N5 hedge argument are live for real launches.
- **Touched:** `train/runs.md`; Modal app `sortsense-train` redeployed
- **Brief task:** A1, A2, A3, N1 → ✅
- **⚠️ Conflicts:** @saliha: the export check is the ACT/SmolVLA half of the Intel bench; the IRs are on the Volume (`modal volume get sortsense-runs <job>/openvino`)
- **📨 Needs:** none
- **Status:** open

### 2026-11-14 17:07 — feat — N5 colour hedge: `train/hedge.py` and `--episode-ids` on the Modal ACT launch — @saliha [conflicts: @nate]
- **Where:** `aiml-perception-saliha` → `main` · merged to `main`: yes
- **Did:** `python -m train.hedge <dataset root> --repo-id <hf id> --steps N` finds which episodes carry each fixed string and prints one `modal run … --policy act --tag purple|orange --episode-ids …` line per colour. `commands.act(episode_ids=…)` and `job_name(tag=…)` back it. Tested on a synthetic LeRobot v3.0 dataset (8 new tests, 271 pass). **The Modal entrypoint path itself is untested** (needs a Modal run); `launch.py` was not changed.
- **Touched:** `train/hedge.py`, `train/commands.py`, `train/modal_train.py`, `train/tests/test_hedge.py`
- **Brief task:** N5 → ✅ code, launch is a human step
- **⚠️ Conflicts:** @nate: `act()` and `train_act` gained an optional trailing argument, existing calls and your tests are unchanged. Use it only if SmolVLA is under 6/10 at the gate.
- **📨 Needs:** none

### 2026-11-14 17:00 — feat — Live spoken reasoning with each brick's numbers (ElevenLabs Flash) — @harry [conflicts: @saliha]
- **Where:** `systems-voice-harry` → `main` · merged to `main`: yes
- **Did:** `narrator/live.py`: every verdict is spoken live with the real score, the threshold it crossed and where the mark is ("That scores 0.41, over my 0.63 line, with a mark at the top left. Orange bowl."), plus the recovery step in words ("After a wrist roll, ..."), in both personas. Own thread; a newer line replaces one not started; a line not back in 3 s or any network error plays the cached clip; a warm-up call opens the connection at start; `--no-live` = cached only. Measured on the venue Wi-Fi: 625–1953 ms per full line over 8 calls; one mock run: warm-up 1734 ms, live lines ready 1812 / 2812 ms after the verdict. 156 tests pass (offline: tests never call ElevenLabs).
- **Touched:** `narrator/live.py`, `narrator/__init__.py`, `run.py` (`spoken_numbers`, `--no-live`), tests
- **Brief task:** A6 (live line)
- **⚠️ Conflicts:** @saliha: `narrator.say(event, text=...)` is now spoken live too (no longer console-only), so the reasoner's line plugs straight in
- **📨 Needs:** none
- **Agreed by:** @harry (3 s timeout + warm-up; live voice emphasised for ElevenLabs)
- **Status:** open

### 2026-11-14 16:58 — feat — Intel laptop set up: NPU and GPU live, first device table, robot environment and Studio installed — @saliha [conflicts: @harry @nate]
- **Where:** `aiml-perception-saliha` (`bench/results.md`) · merged to `main`: with this push
- **Did:** At the laptop: installed the NPU driver packages (1.38.0), added `intel` to `render`/`video`, made RAPL readable, turned Wi-Fi power saving off. `ov.Core().available_devices` = CPU, GPU, NPU (kernel 7.0.0-38, OpenVINO 2026.4.1); `npu_busy_time_us` and `intel_gpu_top` are there. Ran the Block A pipeline here on stand-in bricks: train 18 s, export FP16 + INT8 16 s, both compile on all three devices (NPU first compile 2.8 s FP16, 4.3 s INT8, static 1×3×256×256). First device table (`python -m bench.benchmark`, n=100, on battery, idle 2.3 W), PaDiM INT8 p50: CPU 9.6 ms, GPU 1.0 ms, NPU 7.2 ms; PyTorch CPU 18.4 ms; package power while running about 26 W CPU, 30 W GPU, 11 W NPU; net energy per inference 234 / 31 / 64 mJ. `benchmark_app` agrees (8.7 / 0.92 / 6.6 ms). Every operator runs on every device. Built `.venv-robot` and installed Physical AI Studio natively (board rows). Added the `physicalai` 0.4.0 runtime with the SO-101 driver to the app `.venv`.
- **Touched:** `bench/results.md` (new), `progress.md`; on the laptop only: system packages, `.venv`, `.venv-robot`, `~/work/physical-ai-studio`
- **Brief task:** S2 → ✅ · S7 → 🟡 (device and operator tables on a stand-in model; final run on the real-brick model with the charger in, plus the sustained run and the ACT-on-NPU probe) · N7 install part (Nate's) → ✅ · Block B 08:00 → ✅
- **⚠️ Conflicts:** @harry: a package was added to the laptop's `.venv` that `requirements.txt` does not list (board row). @nate: Studio is a native install, not Docker (board row). @saliha (open decision): on this chip the detector is 7 times faster on the GPU than on the NPU and uses half the energy per inference, while the NPU keeps package power lowest and leaves the GPU to the policies; D8 says NPU, the numbers are on the board for the call
- **📨 Needs:** a person at the station: charger, `.env`, GitHub login, cameras and arm plugged in; blocks S3, S4, the scripted gate

### 2026-11-14 16:56 — fix — A3: SmolVLA export passes through `InferenceModel` with the real task string; the policy runner now sends the export's keys and RGB frames — @nate [conflicts: @harry @saliha]
- **Where:** `robotics-policies-nate` @ `f22367c` · merged to `main`: yes
- **Did:** `train/export.py` checks an export the way the laptop calls it: `InferenceModel(dir, device="CPU")` on a zero observation plus the exact `perfect` string from `config/rules.yaml`. SmolVLA smoke export: finite 50×6 action chunk, 1.9 s first call on Modal's 4-core CPU (not an Intel number). The check caught a bug in `policies/episode.py`: it sent LeRobot's dataset keys and OpenCV's BGR frames without a batch axis, while the exported runtime reads `state`, `images.<camera>` and `task`, RGB, batched. SmolVLA would have failed on the laptop, and after a key-only fix it would have seen purple and orange swapped. Fixed and tested; Studio's own resize step turns three camera frames into the 3×1×3×512×512 input the IR wants. 128 tests pass in `robot policies train common fallback`.
- **Touched:** `train/export.py`, `policies/episode.py`, `policies/tests/test_mover.py`, `train/runs.md`
- **Brief task:** A3 → 🟡 (SmolVLA ✅; ACT export when the smoke run lands, about 17:20)
- **⚠️ Conflicts:** @harry: `run.py` should keep passing raw `SharedCapture` frames to `LearnedMover` (the colour conversion now lives in `policies/episode.py`; converting in `run.py` too would swap the colours back), and `config/models.yaml` must keep `cameras: [top, wrist, inspect]` in that order (SmolVLA's camera1..3). @saliha: a policy benchmark on the laptop should build observations with these keys
- **📨 Needs:** none
- **Agreed by:** n/a (bug fix with one correct answer: the export's manifest)
- **Status:** open
- **Status:** open

### 2026-11-14 17:05 — feat — Live Nemotron line: `reasoner/live.py`, off the control thread — @saliha [conflicts: @harry]
- **Where:** `aiml-perception-saliha` @ `74b19ae` · merged to `main`: yes
- **Did:** `LiveLine(narrator.say).submit(crop, signal)` returns at once; a worker asks Nemotron (4 s timeout), keeps only the newest request, drops a late or failed answer, and throws away a line that names the wrong bowl or quotes a number we did not give it. Real API check on a stand-in image, 6 calls: 6 of 6 grounded, 1.9-2.7 s each. Not yet measured on real bricks.
- **Touched:** `reasoner/live.py`, `reasoner/tests/test_live.py` (6 new tests, 254 pass)
- **Brief task:** live Nemotron line → 🟡 built, not wired
- **⚠️ Conflicts:** @harry: wiring is yours in `run.py` after DECIDE, for any label (not only uncertain): `live.submit(crop, signal, persona)`; `narrator.say(label, text=line)` already accepts the spoken text.
- **📨 Needs:** none (wired by @harry in `d6fbc81`, his 17:15 entry)
- **Status:** resolved by @harry 2026-11-14 17:15

### 2026-11-14 16:50 — docs — Submission draft, station cheat sheet, trials slide on bench.trials — @harry [conflicts: @saliha @nate]
- **Where:** `systems-voice-harry` → `main` · merged to `main`: yes
- **Did:** `docs/submission.md`: Junction Platform text per track (Intel, ElevenLabs, Aiven filled from facts, every unmeasured number TBD; NVIDIA and Modal left as headings). `docs/station.md`: every command from a fresh Intel laptop to the scripted gate, in order. `docs/trials-slide.md` now reads its numbers from `bench.trials` + `truth.csv`. Checked on the Intel laptop: `main` pulls, 220 tests pass, the mock loop sorts 5, OpenVINO lists CPU + GPU (NPU packages still not installed: Harry runs the apt line in `docs/station.md` step 0 when the laptop is free).
- **Touched:** `docs/`
- **Brief task:** submission text draft (Block B 21:00), H5 prep
- **⚠️ Conflicts:** none in code
- **📨 Needs:** @saliha the NVIDIA section, @nate the Modal section of `docs/submission.md` (by Sunday 06:00)
- **Status:** open

### 2026-11-14 16:33 — decision — ACT and SmolVLA gates move to about 21:30 and 22:15; OpenVINO export check added — @nate [conflicts: @saliha @harry]
- **Where:** `robotics-policies-nate` (this push) · merged to `main`: yes
- **Did:** Recording had not started by 16:30, so per the brief the 17:00 ACT gate moves to about 21:30 and the 19:00 SmolVLA gate to about 22:15 (estimates; the 23:00 freeze stays). Added `train/export.py`: exports a job's latest checkpoint from the Modal volume with Studio's Python API and compiles and runs the IR on CPU, on Modal's Linux since the `physicalai` CLI does not start on Windows; first run: the LeRobot-trained SmolVLA smoke checkpoint exported through Studio's API to OpenVINO (`smolvla.xml` 1.57 GB FP32 + `tokenizer.xml` + `manifest.json`) and ran on CPU: inputs state 1×6, 48-token prompt and mask, 3 cameras at 512×512; output a 50×6 action chunk; 1.67 s per chunk on Modal's 4-core CPU (not an Intel number). Not yet checked: parity with the PyTorch policy (weights load with `strict=False`; transformers warns pad_token_id 128002 is outside the vocabulary). Reviewed Saliha's N4 in `train/commands.py`: fine. The deployed training app predates N4, so it is redeployed before any real SmolVLA launch.
- **Touched:** `train/export.py`, `train/tests/test_export.py`, `progress.md`
- **Brief task:** A3 / N1 🟡 (SmolVLA export ✅ on CPU; ACT smoke still training)
- **⚠️ Conflicts:** @saliha: the ACT and SmolVLA IR for your benchmark arrives later than 21:00; @harry: the gates you co-run move
- **📨 Needs:** none
- **Status:** open

### 2026-11-14 16:19 — feat — Trial report with intervals (`bench/trials.py`), N4 SmolVLA recipe, archived old research — @saliha [conflicts: @nate @harry]
- **Where:** `aiml-perception-saliha` → `main` @ `668933e` · merged to `main`: yes
- **Did:** `bench/trials.py` reads the JSONL event log and an optional truth file (what each brick really is) and reports the numbers for the n = 20 slide with Clopper-Pearson intervals, matching the published table (18 of 20: 68-99%); the interval helpers moved to `perception/stats.py` so it does not import Anomalib. N4 in `train/commands.py`: decay steps equal to the run's steps and a checkpoint every 2,500 steps. 238 tests pass. Local only: research passes 0-6 zipped into `Research-Context/_archive-passes-0-6.zip`
- **Touched:** `bench/trials.py`, `perception/stats.py`, `perception/evaluate.py` (imports), `train/commands.py` + tests
- **⚠️ Conflicts:** @nate: N4 changes the SmolVLA command (tests updated); @harry: new report tool beside his SQL report, nothing of his changed
- **Status:** open

### 2026-11-14 16:15 — feat — N3 reviewed; training jobs survive a dropped connection; recording protocol current; base docked — @nate [conflicts: @saliha @harry]
- **Where:** `robotics-policies-nate` @ `9da720e` · merged to `main`: yes
- **Did:** Reviewed Saliha's agent's N3 (`policies/`, `robot/io.py`): approved with one change. `LearnedMover`'s unused `bowl_check` is removed, because `run.py` checks the bowl from home, where the arm no longer hides it; a check inside `place()` would read the top camera with the arm over the bowl. Stale steps docstring fixed. Training now launches through the deployed Modal app (`modal deploy train/modal_train.py`, then `python -m train.launch`, and `--collect` later), so a job keeps running when the laptop's network drops: it dropped twice today and Modal cancelled the calls the laptop was waiting on. `train/RECORDING.md`: purple and orange verdict strings, the N6 tips, `train.audit` after each round, SmolVLA `--cameras top,wrist,inspect`. Red-lego ACT smoke relaunched this way (job `act-allep-300st-1114-141052`). 121 tests pass; mock loop sorts 5 bricks.
- **Touched:** `policies/mover.py`, `policies/tests/test_mover.py`, `train/modal_train.py`, `train/launch.py`, `train/tests/test_launch.py`, `train/RECORDING.md`
- **Brief task:** DO NOW agent (b) ✅ and (c) ✅; (a) A3 export waits on the ACT smoke; N1 🟡
- **⚠️ Conflicts:** @saliha: N3's mover `bowl_check` removed (above); closed your rows on N3, the hand-over, the strings and the audit (done or documented). @harry: both movers still test "opened" as the gripper's 0–100 reading ≥ `GRIPPER_OPEN − POSE_TOLERANCE_DEG`, a joint-angle tolerance; a named release threshold in `robot/io.py` would be clearer. When you teach `pick_drop`, keep its gripper closed on the brick: `reinspect(0)` moves there before releasing
- **📨 Needs:** @harry: yes or no on the base row (16:15)
- **Status:** open

### 2026-11-14 16:10 — feat — Place check, persona switch, drift alarm, README, demo drafts — @harry [conflicts: @nate @saliha]
- **Where:** `systems-voice-harry` → `main` @ `ce9a437` · merged to `main`: yes
- **Did:** (a) after every place the arm goes home and `run.py` checks the named bowl with `scene.brick_in_bowl` against a top frame from before the pick (new `VERIFY_PLACE` stage; one extra home move per brick, Harry's call); the scripted mover judges a grasp with `io.holding()` after `GRIPPER_SETTLE_S`. (b) A6b `narrator/persona.py`: obstacle / H flips to the cowboy with one exclamation, back to calm through the half-way line after the trigger clears and one brick is done (H is one-shot). (c) Drift alarm: the Aiven sync thread queries each brick's first perfect look and runs `perception.drift`; on alert it speaks once and shows a banner, never stops the arm; off until `good_mean` exists and on mock runs. (d) README with the four layers. (e) `docs/demo-script.md`, `docs/trials-slide.md` (exact 95% intervals for k/20). 149 tests pass, mock sorts 5. The drift SQL is tested against a fake only (live Aiven query not run yet).
- **Touched:** `run.py`, `fallback/scripted.py`, `narrator/` (persona, 2 new drift clips), `telemetry/sync.py`, `ui/mission_control.py`, `README.md`, `docs/`, tests
- **Brief task:** DO NOW agent (a)–(e), A6b, A8
- **⚠️ Conflicts:** @nate: `run.py` does the place check itself after home, so it does not pass `bowl_check=` to `LearnedMover` (the hook stays, unused); `ScriptedMover.gripper_empty()` is now `not io.holding()`, same band as yours. @saliha: drift reads `good_mean` + `t_low` from `perception/thresholds.yaml` (via `models.yaml`); events now have a `VERIFY_PLACE` state
- **📨 Needs:** none
- **Agreed by:** @harry (bowl check after home, drift on Aiven speak + banner, H one-shot)
- **Status:** open

### 2026-11-14 15:26 — feat — Episode audit (`train/audit.py`), purple/orange bowl wording in the reasoner — @saliha [conflicts: @nate]
- **Where:** `aiml-perception-saliha` → `main` @ `b35f055` · merged to `main`: yes
- **Did:** `train/audit.py` (F21, switched from Nate): checks a LeRobot v3.0 dataset before training. Fails: wrong fps, missing camera keys, task strings that differ from D23, NaN, late frames, teleop jumps, a bad end hold; warns: hesitation, odd length, runtime speed cap, missing q01/q99, normalized-looking units, copied episodes, unbalanced tasks. On the public red-lego dataset (50 episodes) it reports no failures and reproduces the known missing statistics and normalized units. 204 tests pass (the audit tests need pyarrow: skipped in the perception environment, run in the robot one). My first merge to `main` (`925f8f6`) carried two test files with the same name that clashed when the whole suite ran from the root; fixed in `b35f055` within minutes
- **Touched:** `train/audit.py`, `train/tests/test_episode_audit.py`, plan docs
- **⚠️ Conflicts:** @nate: new file in his folder, nothing of his changed
- **Status:** open

### 2026-11-14 15:15 — feat — Bowls are purple and orange everywhere — @harry [conflicts: @nate]
- **Where:** `systems-voice-harry` → `main` @ `d6aa2ed` · merged to `main`: yes
- **Did:** `config/rules.yaml` = `the brick is perfect, place it in the purple bowl` / `the brick is defective, place it in the orange bowl`; `fallback/scripted.py` maps purple → `bowl_blue`, orange → `bowl_red` (red/blue still accepted); six narrator lines + clips regenerated; click-region outlines purple/orange. 131 tests pass, mock sorts 5.
- **Touched:** `config/rules.yaml`, `fallback/scripted.py`, `narrator/lines.py`, `narrator/clips/`, `ui/click_regions.py`, tests
- **Brief task:** 15:08 BOWL COLOURS
- **⚠️ Conflicts:** @nate: safe to record SmolVLA now with exactly these two strings
- **📨 Needs:** none
- **Agreed by:** @saliha (15:08 row)
- **Status:** resolved by @harry 2026-11-14 15:15

### 2026-11-14 14:44 — feat — N3 grasp verification (moved from Nate), image audit F21 — @saliha [conflicts: @nate @harry]
- **Where:** `aiml-perception-saliha` → `main` @ `16614ca` · merged to `main`: yes
- **Did:** `perception/audit.py`: flags unreadable or mixed-size images, frozen frames, clipped exposure (fail), blur, lighting drift, thin bricks, untagged images (warn); exit code 1 on a failure. N3 in `policies/` and `robot/io.py`: grasp band + 0.3 s settle, early exit for pick and place, wrist roll back before place, optional `bowl_check`. 202 tests pass; the band limits are TUNE until the N8 readings
- **Touched:** `perception/audit.py`, `policies/mover.py`, `policies/episode.py`, `robot/io.py` (new constants and `io.holding()`, additive), tests
- **Brief task:** N3 → ✅ (for Nate's review); F21 image audit done
- **⚠️ Conflicts:** @nate: three of his files changed (review). @harry: `bowl_check` wiring and `io.holding()` for the scripted mover
- **Status:** open

### 2026-11-14 14:39 — scope — Data quality first (D32); Nate's coding-heavy tasks move to Saliha's agent — @saliha [conflicts: @nate]
- **Where:** `context` (D32, PRD §0/R20/F21, three briefs) · merged to `main`: n/a (docs)
- **Did:** second-mentor guidance recorded; F21 data-quality audit added; N3, N4, N5 and the episode audit switched to Saliha's agent per her standing instruction (Nate reviews, keeps robot time)
- **Touched:** `decisions.md`, `prd.md`, the three briefs
- **⚠️ Conflicts:** @nate: N3/N4/N5 and `train/audit.py` are now coded by Saliha's agent in `policies/` and `train/`; reply to stop any he has started
- **Agreed by:** @saliha (switch); @nate has not replied yet
- **Status:** open

### 2026-11-14 14:40 — feat — VLA strings carry the verdict; policies get the inspect camera — @harry [conflicts: @nate]
- **Where:** `systems-voice-harry` → `main` @ `5e99561` · merged to `main`: yes
- **Did:** `config/rules.yaml` now says `the brick is perfect, place it in the blue bowl` / `the brick is defective, place it in the red bowl` (D23); `config/models.yaml` policy cameras `[top, wrist, inspect]` (Nate's 11:53 row, order = camera1..3). 118 tests pass, `make mock` sorts 5 bricks.
- **Touched:** `config/rules.yaml`, `config/models.yaml`
- **Brief task:** 14:30 DO FIRST item 1
- **⚠️ Conflicts:** @nate: record SmolVLA with exactly these two strings and the three cameras in this order
- **📨 Needs:** none
- **Agreed by:** @saliha (14:30 row), @nate (11:53 row)
- **Status:** resolved by @harry 2026-11-14 14:40

### 2026-11-14 14:26 — decision — The VLA strings carry the verdict; rehearse every stage by teleop before recording — @saliha [conflicts: @nate @harry]
- **Where:** `context` (D23, D31, PRD §0/§7.3/§10, Nate and Harry briefs) · merged to `main`: n/a (docs)
- **Did:** Saliha asked the agent to reason through the two proposals and decide. (a) adopted: `"the brick is perfect, place it in the blue bowl"` / `"the brick is defective, place it in the red bowl"` replace the colour-only strings before any SmolVLA episode exists. (b) adopted, folded into the practice runs (about 5 extra minutes). Corrected my earlier 13:10 stamps to 14:19 (the real time).
- **Touched:** `train/RECORDING.md` (Nate: his edit), `config/rules.yaml` (Harry: his edit), plan docs on `context`
- **Brief task:** none (new DO FIRST blocks at the top of Nate's and Harry's Current tasks)
- **⚠️ Conflicts:** @nate: recording strings and a rehearsal before episode 1. @harry: two lines in `config/rules.yaml`; re-click the zone and bowls if the layout moves
- **📨 Needs:** @nate and @harry: do the edits above before the first SmolVLA recording
- **Agreed by:** @saliha (decision delegated to the agent's reasoning); @nate and @harry have not replied yet
- **Status:** open

### 2026-11-14 14:19 — docs — Mentor guidance applied: Anomalib only detects, the VLA integrates; second opinion dropped — @saliha [conflicts: @nate]
- **Where:** `context` (D31, D25, PRD §0 and judging table) · merged to `main`: n/a (docs)
- **Did:** read the six judging-slide screenshots again against the plan. The pipeline already matches the End Goal slide (ACT picks, Anomalib inspects, SmolVLA places) and the VLA never detects defects. Dropped Nemotron's logged "second opinion" on uncertain bricks (doc only, no code existed). Added the four-layer mapping (perception, reasoning, planning, manipulation) to the PRD judging evidence and the mentor guidance to PRD §0. Two proposals are written up but not applied: the verdict inside the VLA strings (a data choice for @nate before recording) and a leader-teleop rehearsal gate.
- **Touched:** `decisions.md` (D25, D31), `prd.md` (§0, §5, Pending)
- **Brief task:** none
- **⚠️ Conflicts:** @nate: the proposals (a) and (b) would touch D23's strings and the recording order if Saliha says yes; nothing changes for you until then
- **📨 Needs:** none
- **Status:** open

### 2026-11-14 12:40 — feat — Drift rule, in-graph preprocessing, operator-support table; opencv-python — @saliha [conflicts: @harry]
- **Where:** `aiml-perception-saliha` → `main` @ `4c96ef0` · merged to `main`: yes
- **Did:** (1) `perception/drift.py`: F15 drift rule (mean of the last 8 perfect bricks, at least 5, as a fraction of the way from the good baseline to `t_low`; alarm at 0.5, TUNE); `evaluate` now saves `good_mean` in `thresholds.yaml`. (2) `perception/preprocess.py` + `export`: `model_ppp.xml` beside each IR with the BGR→RGB flip, /255 and layout change inside the graph; the CPU resize is unchanged so scores match; `Scorer` detects the uint8 input. On this laptop's CPU (stand-in bricks, not Intel numbers) the FP16 detector end to end went 44.5 → 38.5 ms p50 and 63.7 → 43.3 ms p95; INT8 unchanged (71.6 vs 72.2 ms). (3) `bench/operators.py`: per model and device, which operators run (`query_model`), added to `bench/results.md`; the PaDiM IR runs 223/223 operators on CPU. (4) `opencv-python` replaces the headless pin. 175 tests pass across all packages.
- **Touched:** `perception/` (`drift.py`, `preprocess.py`, `export.py`, `inspector.py`, `evaluate.py`, `requirements.txt`), `bench/` (`operators.py`, `benchmark.py`), plan docs on `context` (D30, PRD F2/F15/§10, CLAUDE.md cut order, three briefs)
- **Brief task:** none (add-ons from the marking-scheme review; S7 harness extended)
- **⚠️ Conflicts:** @harry: the drift alarm in your Aiven consumer can call `perception.drift` (details on the board row); `opencv-python` replaces the headless build, so reinstall from `requirements.txt` if a window failed to open. @nate: none; the exported ACT/SmolVLA IRs are untouched
- **📨 Needs:** @harry and @nate: yes or no on the offers on the board rows (nothing starts without it)
- **Agreed by:** n/a (feature entry); the PrePostProcessor cut-order change is a 🔀 row to @all
- **Status:** open

### 2026-11-14 12:35 — merge — A6: the robot speaks: cached clips play on their own thread — @harry [conflicts: none]
- **Where:** `systems-voice-harry` @ `bb177c4` · merged to `main`: yes
- **Did:** `narrator/player.py`: `narrator.say()` hands the clip to a player thread and returns at once. Newest line wins (older waiting lines are dropped, so speech keeps up with the arm); help and e-stop lines are never dropped. Backend from the OS, no new package: `winsound` (Windows), `aplay` (Ubuntu, alsa-utils), `afplay` (macOS); no speaker → console only, logged once. `run.py` waits up to 10 s for the last line before exiting. Live lines passed as `text` (the reasoner) stay console-only until the live ElevenLabs line (add-on). Played a clip through the speakers on Harry's laptop (winsound); 107 tests pass with Nate's, tests run silent.
- **Touched:** `narrator/`, `run.py`, `common/tests/conftest.py`
- **Brief task:** A6 → 🟡 (cached playback done; live streaming line is the add-on)
- **⚠️ Conflicts:** none
- **📨 Needs:** none
- **Status:** open

### 2026-11-14 12:28 — merge — A5: event log → Aiven PostgreSQL, verified live; Kafka producer ready; trial report — @harry [conflicts: @saliha]
- **Where:** `systems-voice-harry` @ `992a89b` · merged to `main`: yes
- **Did:** `telemetry/sync.py`: a thread beside the control loop sends new `runs/events.jsonl` rows to an Aiven PostgreSQL `events` table (PRD 7.3 columns) every 2 s and, once `AIVEN_KAFKA_*` is set, to the `sortsense.events` topic. Offline, rows wait in the file; the offset is saved only after a batch lands and a unique key makes re-sends no-ops. `python -m telemetry.check_aiven` tests the connection, printing no secrets. `telemetry/report.sql`: runs, pauses by reason, p50/p95 per stage and device, second looks. Mock runs now log to `runs/mock-events.jsonl` with a `mock-` run id and only go to Aiven with `--aiven`, so stand-in data stays out of the report. New pins: `psycopg[binary]==3.3.9`, `confluent-kafka==2.16.1`; `certs/` is git-ignored and `.env.example` lists the Aiven settings. **Measured live (free plan, PostgreSQL 18.7):** connect ~0.4 s warm (5.3 s on a cold service); a mock run's 37 rows all landed; re-sending all 37 left 37. 101 tests pass with Nate's. Kafka not tested yet (no free Kafka service created).
- **Touched:** `telemetry/`, `run.py`, `requirements.txt`, `.gitignore`, `.env.example`
- **Brief task:** A5 → 🟡 (PostgreSQL done; Kafka stream + drift alarm left)
- **⚠️ Conflicts:** @saliha: the drift alarm will read `events` (INSPECT rows with `label`, `score`); your drift rule plugs in there. Your 05:32 `opencv-python` row is still open
- **📨 Needs:** none
- **Status:** open

### 2026-11-14 11:53 — decision — Record in degrees with all three cameras; end-of-run dance accepted — @nate [conflicts: @harry @saliha]
- **Where:** `robotics-policies-nate` (this commit) · merged to `main`: yes
- **Did:** Answered Harry's H6 row. Joint unit **degrees** end to end, as `robot/io.py` runs; the first Studio test episode is checked against `io.observe()` at the same pose, and if Studio can only record normalized the fallback is switching `io.py` (D29). Both datasets record **`top`, `inspect`, `wrist`**; SmolVLA maps them `top`→`camera1`, `wrist`→`camera2`, `inspect`→`camera3` (`--cameras top,wrist,inspect`). Accepted Saliha's `robot/dance.py` (joint signs TUNE on the arm). `train/RECORDING.md` updated. The N1 ACT smoke was relaunched with `modal run --detach` after the laptop's network dropped at ~06:20 and killed the first client.
- **Touched:** `train/RECORDING.md`, `progress.md`; on `context`: `decisions.md` D28, D29, my brief
- **Brief task:** N6 → 🟡 (camera keys and unit) · N7 → check the unit on the first test episode
- **⚠️ Conflicts:** @harry: `config/models.yaml` needs `inspect` among the policy cameras (board row 11:53). @saliha: ACT sees three cameras, so expect three image inputs in the exported IR you benchmark
- **📨 Needs:** @harry: the config change above
- **Agreed by:** @nate (unit and cameras: recommended options, Harry asked on H6)
- **Status:** open

### 2026-11-14 11:41 — feat — H3 clips: 37 cached voice lines generated and committed; bowl check stays, built at the venue — @harry [conflicts: none]
- **Where:** `systems-voice-harry` @ `7bd7d7b` · merged to `main`: yes
- **Did:** `python -m narrator.cache` generated every fixed line in `narrator/lines.py` (calm `etWmxTqEKhIYyGKMpDcb`, cowboy David `0hh7H4ZVAtaGpm1VZyEN`, `eleven_multilingual_v2`, WAV 22 kHz mono): 37 clips, 1,632 characters of credit, 98 s of audio, 4.3 MB, all checked as valid WAV. Committed in `narrator/clips/` (Harry's call) so the Intel laptop speaks offline without the key. Playback (A6) still to wire. Bowl check (Saliha's `brick_in_bowl`): Harry wants it; the timing (home after each place vs later) is settled and tested at the venue.
- **Touched:** `narrator/clips/`
- **Brief task:** H3 → ✅ clips generated
- **⚠️ Conflicts:** none
- **📨 Needs:** none
- **Status:** open

### 2026-11-14 11:37 — merge — Saliha's scene check, ReasonTrace and dance wired into `run.py`; region click tool; fallback uses `io` thresholds — @harry [conflicts: @saliha @nate]
- **Where:** `systems-voice-harry` @ `ac268a7` · merged to `main`: yes
- **Did:** (1) `ui/click_regions.py`: click the zone and both bowls (4 corners each, clockwise from top-left) on the top camera → `config/scene.yaml`. (2) Real mode uses `perception.scene.SceneLocator` once the zone is clicked (else `--bricks N`, with a warning); non-brick objects in the zone are skipped and trigger `narrator.trigger("obstacle")` once. (3) The LOG row's `note` is `ReasonTrace.from_signal(final, label, steps).note()`; the panel shows the defect region; scores print with one decimal (raw distances). (4) After an empty zone (not after Q): "dance" line + `robot.dance.dance(home)`, then home. (5) `fallback/scripted.py` reads `io.POSE_TOLERANCE_DEG`, `io.GRIPPER_EMPTY_BELOW`, `io.GRIPPER_OPEN` (Nate's ask; copies dropped). 95 tests pass with Nate's + Saliha's scene tests.
- **Touched:** `run.py`, `fallback/scripted.py`, `narrator/lines.py`, `ui/click_regions.py`, `config/scene.yaml`
- **Brief task:** H5 tool ready · Saliha's 08:50 wiring → 🟡 (bowl check, depth hold open)
- **⚠️ Conflicts:** @saliha: `brick_in_bowl` not wired yet: right after `place` the arm still hangs over the bowl, so "region changed" is always true; deciding when to check. `tall_object` needs depth frames, which `SharedCapture` doesn't read yet. @nate: done with your 06:10 row
- **📨 Needs:** none
- **Status:** open

### 2026-11-14 08:50 — feat — S5 scene check (incl. brick-or-not key), S6 ReasonTrace, bench fixes, end-of-run dance — @saliha [conflicts: @harry @nate]
- **Where:** `aiml-perception-saliha` @ `b67eff4`, `robotics-policies-nate` @ `487ddf5` · merged to `main`: yes
- **Did:** `perception/scene.py`: zone homography, "is it a brick?" rule (D27, Nate's key idea), most-isolated brick, `tall_object` from depth, `brick_in_bowl`, `SceneLocator`. `perception/reason_trace.py`: score, margin, 3×3 defect region, recovery steps, decision, one-line note. Bench: any IR layout incl. multi-input policies, PyTorch baseline row (on this laptop: PaDiM 157 ms PyTorch vs 49 ms OpenVINO FP16, not Intel numbers), 1 Hz thermal, energy net of idle. `robot/dance.py` (D28). 143 tests pass across packages. All hardware-free tasks on Saliha's list are done.
- **Touched:** `perception/scene.py`, `perception/reason_trace.py`, `bench/`, `robot/dance.py` (Nate's folder, doc-owner request)
- **Brief task:** S1, S5, S6 → ✅ · S7 → 🟡 (harness ready; runs on the Intel laptop)
- **⚠️ Conflicts:** @harry: wiring asks on the board; @nate: new file in `robot/`
- **📨 Needs:** @harry: the run.py wiring above
- **Status:** @nate part resolved by @nate 2026-11-14 11:53 (dance accepted; joint signs TUNE on the arm); @harry part open

### 2026-11-14 08:20 — feat — S1: brick-level detector evaluation and raw anomaly scores — @saliha [conflicts: @harry]
- **Where:** `aiml-perception-saliha` @ `882232a` · merged to `main`: yes
- **Did:** (1) Images carry their brick (`capture --brick`, synth `b<brick>_<n>.png`). (2) Raw scores: Anomalib's default post-processor clamped every good brick to **0.0** (measured), so models now export unclamped scores (good ~40-55, defective ~200-290 on stand-in data); `thresholds.yaml` gains `pixel_threshold` for the region box. (3) `python -m perception.evaluate`: out-of-fold good scores by brick set t_low, a dev half of defective bricks sets t_high, the other half only reports; AUROC with a bootstrap-by-brick interval, exact false-alarm bound, recall interval → `bench/detector_report.md`. (4) Fix: no core-wide `CACHE_DIR` (it replaced the NPU driver's cache). 123 tests pass across all packages.
- **Touched:** `perception/` (capture, synth, train, export, calibrate, thresholds, inspector, evaluate), `reasoner/client.py` docstring
- **Brief task:** S1 → ✅ done (synthetic); real-brick run is S4 at 10:30
- **⚠️ Conflicts:** @harry: the inspector's scores are now raw distances, not 0-1; anything that displays or compares `DefectSignal.score` against a fixed number should use `t_low`/`t_high` from the signal instead. Re-run calibrate or evaluate before using an old `thresholds.yaml`
- **📨 Needs:** none
- **Status:** open

### 2026-11-14 06:20 — fix — Studio ACT training crashed on video decoding; root cause found, fixed — @nate [conflicts: @saliha]
- **Where:** `robotics-policies-nate` @ `442d39c` · merged to `main`: yes
- **Did:** The ACT smoke run (Studio's trainer, `lerobot/svla_so100_pickplace`) crashed in training with torchcodec "Invalid data found when processing input". Cause, reproduced on a cheap Modal CPU job: Studio's one-off quantile pass decodes video in the main process, and the forked loader workers inherit those decoders and fail (after 136 frames); no workers, `spawn`, or no parent decode all pass 800 frames. `train/commands.py` now passes `--data.num_workers 0`. Also measured: the quantile pass costs ~40 s per episode on datasets without q01/q99 statistics (35 min for 50 episodes), so our own Studio recordings should carry them (check at N7). Re-run on the red-lego set in flight.
- **Touched:** `train/commands.py`, `train/tests/test_commands.py`, `train/runs.md`
- **Brief task:** N1 → 🟡 (ACT re-run in flight)
- **⚠️ Conflicts:** @saliha: anything else that decodes LeRobot video in a parent process and then forks workers can hit the same bug; ACT IR for your 21:00 benchmark depends on this run
- **📨 Needs:** none
- **Status:** open

### 2026-11-14 06:10 — decision — Gripper and pose thresholds live in `robot/io.py`; Modal keeps its default CPU — @nate [conflicts: @harry]
- **Where:** `robotics-policies-nate` @ `eb79301` · merged to `main`: yes
- **Did:** Moved `POSE_TOLERANCE_DEG`, `GRIPPER_EMPTY_BELOW` and `GRIPPER_OPEN` from `policies/mover.py` into `robot/io.py`, so the learned and scripted movers read one set of numbers. Kept Modal's default CPU for training: SmolVLA's loader needed 0.07 s per step against a 0.2 s update; only Studio's one-off quantile pass is slow, and only on datasets without q01/q99 statistics. 82 tests pass.
- **Touched:** `robot/io.py`, `policies/mover.py`, `policies/tests/test_mover.py`
- **Brief task:** prep for N3 and N8
- **⚠️ Conflicts:** @harry: switch `fallback/scripted.py` to the `io.` thresholds (board row 06:10)
- **📨 Needs:** @harry: the switch above
- **Agreed by:** @nate (constants: your offer at 04:38)
- **Status:** open

### 2026-11-14 06:09 — merge — H7: reasoning panel on mission control; each policy's real device on screen — @harry [conflicts: @saliha]
- **Where:** `systems-voice-harry` @ `ffdf8e4` · merged to `main`: yes
- **Did:** The cell keeps one line per step for the current brick (`Cell.trace`): every look with its score against both thresholds and the label, each recovery move, "still unsure: defective, flagged", the decision, or "needs help: <reason>". Mission control draws it under the feed (up to 6 lines, a full chain fits). The mover line now names the OpenVINO device each learned policy really loaded on ("pick: act on GPU | place: scripted"). 82 tests pass with Nate's. Closed my `abort_event` row: @nate's `LearnedMover` passes `deadline.abort` (N2). Left for the station: the rest of H7's Intel-stack items (benchmark numbers, device table).
- **Touched:** `run.py`, `ui/mission_control.py`, `common/tests/`
- **Brief task:** H7 → 🟡 panel + device naming done; station items left
- **⚠️ Conflicts:** @saliha: the panel shows the cell's own chain; your `ReasonTrace` (S6) can add the defect region and margin as extra lines
- **📨 Needs:** none
- **Status:** open

### 2026-11-14 06:04 — docs — H6: read Intel's `physicalai` tutorial and runtime source against our code — @harry [conflicts: @nate]
- **Where:** notes only (local research doc, Pass H6) · merged to `main`: n/a
- **Did:** Read all of `examples/tutorials/collect_train_deploy.ipynb` plus the runtime, SO-101 plugin, inference and capture sources. Our imports are valid (`robot/io.py`'s `physicalai.robot.so101.SO101` is a backward-compatible forward to `physicalai_so101_plugin`; `InferenceModel(export_dir, backend=, device=)` matches). **Risk:** `SO101` defaults to `unit="normalized"`, `io.py` uses degrees (board row to @nate). `RobotRuntime.run(stop_event=...)` takes our abort natively and early exit is possible through a callback calling `stop()`, but it sends actions straight to the robot, skipping `io.act()`'s clip, speed cap and e-stop check, so it would need a safety callback. Verdict: **keep `Cell`, `io.py` and `SharedCapture`; no `RobotRuntime` before the 15:30 gate.** Optional add-on: read cameras through `physicalai.capture.create_camera(...)` (UVC + RealSense; `Frame.timestamp` is `time.monotonic()`, so `SharedCapture`'s fresh-frame wait still works); `discover_all()` lists cameras for the 08:00 setup.
- **Touched:** nothing in the repo
- **Brief task:** H6 → ✅ done
- **⚠️ Conflicts:** @nate: joint unit and dataset camera names (board row)
- **📨 Needs:** @nate: confirm the recording unit
- **Status:** resolved by @nate 2026-11-14 11:53 (degrees; three cameras; config ask on the board)

### 2026-11-14 06:01 — feat — N1 SmolVLA smoke passes (camera mapping); N2 early exit + stage deadline in the policy loop — @nate [conflicts: @harry]
- **Where:** `robotics-policies-nate` @ `945310a` · merged to `main`: yes
- **Did:** `--cameras top,gripper,left` maps a dataset's cameras onto `smolvla_base`'s `camera1..3` (LeRobot `--rename_map`). SmolVLA 200 steps on `eruedas/so101_3cams_pickplace-red-lego_real`: 1.8 min on an A100, ~5 steps/s, loss 0.287, AV1 video decodes, checkpoint saved (`train/runs.md`). N2: `run_episode` takes `stop()` (early exit) and `abort_event`; `LearnedMover` passes `common.deadline.abort` and returns `False` when it fires (Harry's request). 79 tests pass; mock loop sorts 5 bricks.
- **Touched:** `train/commands.py`, `train/modal_train.py`, `train/runs.md`, `policies/episode.py`, `policies/mover.py`, tests
- **Brief task:** N1 → 🟡 (SmolVLA ✅; ACT smoke + export next) · N2 → ✅ · A2 → SmolVLA part ✅
- **⚠️ Conflicts:** @harry: `LearnedMover.pick_and_present` and `place` now return `False` once your stage deadline fires (no step is sent after it)
- **📨 Needs:** none
- **Status:** open

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
- **Status:** @nate part resolved by @nate 2026-11-14 06:01 (`LearnedMover` passes it, `945310a`); @saliha part open

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
- **Status:** @nate part resolved by @nate 2026-11-14 05:47 (`robot/io.act` checks the e-stop, `f6a9f65`); @saliha part open (the `opencv-python` ask to @saliha: resolved by @saliha 2026-11-14 12:40, `main` `4c96ef0`)

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
