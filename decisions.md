# Decisions: why we built it this way (pitch and process record)

**What this file is for.** The team-visible record of design choices, features we add, trade-offs and the reasons behind them. We read it when pitching to judges, writing the README, the video script and the Devpost / NVIDIA / Aiven write-ups. It lives on the `context` branch.
**Who keeps it current.** Every agent, autonomously (CLAUDE.md §4a): the same turn a decision is made or a feature is implemented, add or update its entry. Nobody has to ask.
**Rules for entries.**
- **Facts only.** A number appears only if it was measured or comes from a source named next to it. Otherwise write `TBD (measure in <where>)`. Never invent a metric, a speed-up or a result.
- **Status** is `Planned` (decided, not built) · `Built` (code exists) · `Verified` (measured on the real station, numbers filled in) · `Dropped` (kept, with the reason).
- When a feature goes `Verified`, fill **Evidence** with the real numbers and where they live (`progress.md` 📊 Latest, `bench/results.md`, Aiven report).
- Never delete an entry; mark it `Dropped` with why. Personal notes go in the vault, not here.

**Entry format**
```
### D<n> · <area> · <short title> — Status: <Planned|Built|Verified|Dropped> · Owner: @<name> · Updated: <YYYY-MM-DD HH:MM>
- **Decision:** what we chose.
- **Why:** the reasoning, tied to the task, a judging criterion or a measured fact.
- **Alternatives rejected:** what else, and why not.
- **Trade-off / risk:** what it costs us, and the fallback.
- **Evidence:** numbers and source, or `TBD (...)`.
- **Pitch line:** one sentence a judge can repeat.
```

---

## A. Task and architecture

### D1 · Learning method · Imitation learning, not reinforcement learning — Status: Planned · Owner: @nate · Updated: 2026-11-14 01:30
- **Decision:** the arm learns from human teleoperated demonstrations (behaviour cloning): ACT for the pick, SmolVLA for the place. No reinforcement learning (RL).
- **Why:** Intel's challenge page frames the task as "show a robot a task a few dozen times and it learns a policy", and Physical AI Studio is built around recording demonstrations and fine-tuning. RL needs a reward signal and very many trials; on a real arm with a 48-hour budget, one station per team and the printed safety rules, that is slow and risks the hardware. Demonstrations give a usable policy from ~54 episodes.
- **Alternatives rejected:** RL fine-tuning of the policy (reward design plus many real-robot trials; no simulator in scope); hand-scripted motion only (kept as the fallback, D3, not as the main system).
- **Why not reinforcement learning, with numbers (research pass, 2026-11-14 07:10):** the most sample-efficient real-robot method, HIL-SERL (arXiv 2410.21845), needs 1–2.5 h of online training per task with a person intervening, i.e. 22–55% of our ~4.5 h robot allowance before a single scoring trial; its LeRobot implementation is SAC from scratch with a reward classifier (~200 positive / 1,000 negative frames), not ACT, SmolVLA or Physical AI Studio, so it would give up the Studio/VLA story (20 + 20 points). Our anomaly score measures defects, not grasp or placement success, so it is not a usable reward. Residual RL and ConRFT were only seen as snippets (WEAK). **Kept from the idea:** automatic success labels (gripper band, bowl region) and one correction round (DAgger, LeRobot HIL docs) if ACT misses its 17:00 gate. Pitch: "Failures become demonstrations, not gradient steps."
- **Trade-off / risk:** an imitation policy is only as good as its demonstrations, so dataset quality matters (it is 20% of the Junction page rubric): tight 10×10 cm pick zone, rejected-episode log, dataset card, and a success-vs-number-of-demos sweep (D9).
- **Evidence:** TBD (10-trial gate results, `progress.md`).
- **Pitch line:** "We taught the arm by showing it, the way Intel designed the stack, and measured how few demonstrations are enough."

### D2 · Pipeline · ACT picks, Anomalib inspects, SmolVLA places — Status: Built (code, mock-tested) / Planned (trained policies) · Owner: @nate @saliha · Updated: 2026-11-14 01:30
- **Decision:** the pipeline from Intel's End Goal slide: ACT picks and presents the brick, Anomalib scores it, the verdict becomes a language instruction ("place the brick in the orange/purple bowl") for SmolVLA, which places it.
- **Why:** it is the reference task, and the verdict-to-instruction step is exactly where a vision-language-action (VLA) model earns its place: one policy, two behaviours, chosen by language.
- **Alternatives rejected:** one policy for the whole loop (needs more demonstrations than we can record; kept as an extension idea).
- **Trade-off / risk:** SmolVLA export bugs (Studio issues #1384, #1414, #1169) and needs ~50 episodes; gate at Saturday 19:00 keeps it if ≥ 4/10 unless scripted placement is clearly better.
- **Evidence:** TBD (gate results).
- **Pitch line:** "The inspection result literally becomes the instruction the robot follows."

### D3 · Reliability · Scripted fallback behind the same interface — Status: Built · Owner: @harry · Updated: 2026-11-14 04:38
- **Decision:** a scripted waypoint mover sits behind the same `Mover` interface as the learned policies, and a full scripted loop must pass by Saturday 15:30 before the learned policies are swapped in.
- **Why:** an earlier team on this challenge (ohong/intel-robotics) never moved its arm; the end-to-end criterion is 25 points. The loop must work even if a model fails.
- **Alternatives rejected:** learned policies only (a single export bug would sink the demo).
- **Trade-off / risk:** the demo must always say which mode ran; a scripted placement is never presented as SmolVLA.
- **Evidence:** built in `fallback/scripted.py` behind the same `Mover` interface; tested against a mock arm that closes on a brick (pick, place by instruction colour, re-grasp, wrist roll, e-stop). Poses are taught by hand with `fallback/teach.py`. TBD (15:30 gate on the real arm).
- **Pitch line:** "Every learned part has a safe fallback, and we tell you which one is running."

### D4 · Safety and latency · Control never waits on the network — Status: Planned · Owner: @harry · Updated: 2026-11-14 01:30
- **Decision:** the control loop, inference and the arm never touch the network. Reasoning (Nemotron), voice (ElevenLabs) and telemetry (Aiven) run on their own threads and degrade to templates, cached clips and a local JSONL buffer.
- **Why:** venue Wi-Fi can drop or lag; the arm must stay responsive and safe (E = torque off). Cloud calls are tens to hundreds of milliseconds and variable.
- **Alternatives rejected:** calling the cloud inside the state machine.
- **Trade-off / risk:** the spoken line can be late; stale lines are dropped.
- **Evidence:** TBD (latency of each thread in the logs).
- **Pitch line:** "The robot's safety never depends on the internet."

## B. Perception ML (Anomalib)

> **08:50 measured (stand-in data, Saliha's laptop):** with Anomalib's default post-processor every good brick scored exactly **0.0** after export, so t_low was set on a pile of zeros; with `PostProcessor(enable_normalization=False)` the same model exports raw distances (good ≈ 41–54, defective ≈ 198–289). Shipped in `perception/train.py`; the region box now uses a measured `pixel_threshold`. `python -m perception.evaluate` implements the brick-level protocol below (`main` @ `882232a`). On this laptop's CPU the OpenVINO FP16 detector ran in 49 ms vs 157 ms for PyTorch (not Intel-laptop numbers).

> **07:10 update to D5–D7 (research pass):** evaluation uses our own brick-level splits, raw (unclamped) scores, out-of-fold `t_low` and intervals (bootstrap by brick for AUROC, Clopper-Pearson for false alarms): Anomalib's `Folder` default silently moves half the test set into validation, and the exported score is clamped to [0, 1]. With ~150 good normals the honest claim is about 2% false alarms at 95% confidence (299 needed for 1%; Deng 2026). The AUROC target is now the lower end of the interval. Recovery chain order (D7): fresh same-camera look → wrist roll 90° → re-grasp → defective and flagged; a second camera can't be scored by a model trained on the inspection camera. EfficientAd dropped; AnomalyDINO only if PaDiM's lower interval < 0.90.

### D5 · Detector · Anomaly detection trained on good bricks, not a defect classifier — Status: Built · Owner: @saliha · Updated: 2026-11-14 03:55
- **Decision:** Anomalib learns what a good brick looks like and flags deviations. We use our marker-drawn defective bricks to set thresholds and measure quality, not as the main training signal.
- **Why:** in inspection, defects are rare and varied; the task says we draw our own defects with markers, so a supervised classifier would only learn our marker style. Anomaly detection generalises to new marks.
- **Alternatives rejected:** a supervised good/defective classifier (needs many labelled defects, overfits to our pen).
- **Trade-off / risk:** colour variation in the good bricks can blur "normal" (D6). Mitigation: real-brick data in the same lamp and crop, held-out good set.
- **Evidence:** pipeline built and tested end to end on synthetic stand-in bricks (`perception/train.py`, `calibrate.py`, `inspector.py`); held-out AUROC on real bricks TBD (Saturday 10:30, targets ≥ 0.95, minimum 0.90). Stand-in scores are not evidence.
- **Pitch line:** "It learned what good looks like, so any new kind of defect stands out."

### D6 · Detector · Model choice decided by measurement (PaDiM default) — Status: Planned · Owner: @saliha · Updated: 2026-11-14 01:30
- **Decision:** train PaDiM, PatchCore and EfficientAd on real bricks on Saturday and pick by held-out AUROC and latency. PaDiM is the default (the guide we cite reports it trains about 30× faster than PatchCore) and exports with static shapes for the NPU. If the good bricks come in several colours, compare PatchCore and one PaDiM per colour, because PaDiM fits one Gaussian per patch position.
- **Why:** Anomalib's models trade accuracy, speed and export friendliness; the NPU needs static shapes, and PatchCore can export with batch 2 (Anomalib issue #3883).
- **Alternatives rejected:** choosing before seeing the real bricks.
- **Trade-off / risk:** the training window is 10:30–12:00 Saturday.
- **Evidence:** TBD (comparison table in `bench/results.md`).
- **Pitch line:** "We chose the model by measuring three on our own bricks, not by guessing."

### D7 · Reliability · Two-threshold uncertainty band and recovery chain (order changed 07:10) — Status: Built (band) / Planned (re-grasp chain) · Owner: @saliha @nate · Updated: 2026-11-14 04:16
- **Decision:** `t_low` = 99th percentile of good-brick scores, `t_high` = 5th percentile of defective scores; below `t_low` perfect, above `t_high` defective, between uncertain. Uncertain → second camera view → re-grasp (Intel's own suggested idea: use the anomaly score to trigger a re-grasp) → wrist roll if time → defective, said aloud. Re-grasp and wrist roll share one motion call, `Mover.reinspect(angle_deg)`: `0` puts the brick down in the pick zone and picks it again, `±90` rolls the wrist in place, and it returns `True` only when the brick is back at the inspection pose (agreed by @nate and @saliha 2026-11-14 01:35, @harry 2026-11-14 04:16).
- **Why:** anomaly scores are distances, not probabilities, so thresholds must come from data; the rubric scores recovery from uncertain detections. One call keeps the `Mover` signature that froze at 01:00 Saturday, so the learned policies and the scripted fallback implement the same thing.
- **Alternatives rejected:** a single threshold (every borderline brick is a coin flip); a separate `regrasp()` method (reopens the frozen contract); re-grasping before every wrist roll (each roll would cost a full re-grasp).
- **Trade-off / risk:** a re-grasp costs cycle time; capped at one re-inspection.
- **Evidence:** TBD (planted borderline brick handled 3 times in a row).
- **Pitch line:** "When it isn't sure, it looks again instead of guessing."

## C. Edge optimization (OpenVINO)

### D8 · Deployment · Deliberate NPU / GPU / CPU placement with INT8 — Status: Built · Owner: @saliha · Updated: 2026-11-14 16:58
- **Decision:** Anomalib (small convolutional net, static 1×3×256×256) on the NPU with INT8 post-training quantisation; ACT and SmolVLA on the GPU; capture, state machine and serial on the CPU. Fallback chain NPU → GPU → CPU. Every optimisation claim gets a number: p50/p95 latency, model size, first vs cached compile time, bricks per minute.
- **Why:** the NPU is low power but needs static shapes (OpenVINO docs); the transformers are heavy and called often, so they get the GPU; control stays on the CPU for predictability. The rubric asks for appropriate use of all three.
- **Alternatives rejected:** everything on the GPU (wastes the NPU, no efficiency story).
- **Trade-off / risk:** operator support on the NPU is untested for our model; the GPU fallback is ready.
- **Built:** the export bakes a static 1×3×256×256 input into the IR (Anomalib leaves the batch dynamic by default, which the NPU cannot compile) and INT8 post-training quantisation calibrates at batch 1. The inspector compiles the IR itself on the first working device in NPU → GPU → CPU order with a compile cache, and records why each skipped device failed (Anomalib's `OpenVINOInferencer` has no fallback chain).
- **Evidence:** PaDiM IR size INT8 47 MB vs FP16 88 MB (file sizes). On Saliha's own laptop (not the Intel laptop, stand-in model): the compile cache cut GPU compile from ~10 s to ~1.5 s. **Intel laptop, first run (2026-11-14 16:44, stand-in model, on battery, n=100, `bench/results.md`):** PaDiM INT8 p50 CPU 9.6 ms, GPU 1.0 ms, NPU 7.2 ms; FP16 6.4 / 1.5 / 7.2 ms; PyTorch on the CPU 18.4 ms. NPU first compile 2.8 s (FP16) and 4.3 s (INT8), 0.02–0.05 s cached. Every operator of both IRs runs on all three devices. To be re-run on the real-brick model with the charger in.
- **Pitch line:** "Each model runs on the chip it suits, and we have the numbers for every choice."

### D9 · Efficiency · Energy, thermal and demo-count measurements — Status: Built (energy/thermal harness, `bench/power.py`; demo-count sweep, `train/modal_train.py --sweep`) · Owner: @saliha @nate · Updated: 2026-11-14 05:11
- **Decision:** measure energy per inference and watts with Intel RAPL counters, peak temperature during the 20 trials, and success vs number of demonstrations (ACT trained on 18 / 36 / 54 episodes in parallel on Modal). ACT demos are recorded in rounds (one episode per start position per round), so the first 18 / 36 / 54 episodes are exactly 2 / 4 / 6 per position; the "new positions" test uses off-grid spots that are never recorded.
- **Why:** the Junction page scores inference latency, thermal headroom and power (20%), and Intel's challenge text asks "how few demonstrations are enough".
- **Alternatives rejected:** latency-only benchmarking.
- **Trade-off / risk:** RAPL and thermal readings exist only on the Intel Linux laptop; the sampler returns nothing elsewhere.
- **Evidence:** TBD (`bench/results.md`, success-vs-demos curve).
- **Pitch line:** "We report joules per brick and how few demos it takes, not just speed."

### D10 · Efficiency · One camera grab shared by the policy and the inspector — Status: Built · Owner: @harry · Updated: 2026-11-14 04:30
- **Decision:** each camera is read once per tick and the same frame goes to the policy and the inspector.
- **Why:** Intel lists "sharing cameras between policy and inspection" among the ideas it wants to see; it saves a USB stream and latency.
- **Alternatives rejected:** separate capture per consumer.
- **Trade-off / risk:** which physical camera is the RealSense is confirmed at the station. **2026-11-14 15:40 (@harry):** three cameras, one of each: RealSense D415 = `top` (looking down, so its depth sees tall things in the zone), webcam = `inspect`, wrist cam = `wrist`; `config/cameras.yaml` on `main`, paths filled once plugged in.
- **Evidence:** built in `common/capture.py` (one grab thread per camera; consumers read the same frame and wait for one taken after the arm stopped); tested with mock cameras (two reads between frames return the same array, one grab). TBD (USB streams and latency saved, measured on the Intel laptop).
- **Pitch line:** "One camera feed, two jobs."

## D. Reasoning, voice and personality

### D11 · Reasoning · Nemotron 3.5 Super VL writes grounded live explanations — Status: Built (client, grounding checker, live thread; wired into run.py by @harry) / Planned (20-frame eval on real bricks) · Owner: @saliha · Updated: 2026-11-14 17:22
- **Decision:** per brick, Nemotron (a vision-language model) gets the crop, the heatmap and the `DefectSignal` numbers and returns one short line in the current persona. We pass the numbers in so it cannot invent them, require JSON out, and reject a line that contradicts the label. It also answers "is the cowboy hat in view?" and, once, turns the kickoff rules text into a checked `rules.yaml`.
- **Why:** the NVIDIA track needs the model to do real work in the product, visibly; a vision-language model can describe where the defect is. Grounding in measured numbers keeps the explanation true.
- **Alternatives rejected:** fixed template sentences only (kept as the fallback); a text-only model (cannot see the brick).
- **Trade-off / risk:** the free NVIDIA Build tier is rate limited (about 40 requests per minute per key); requests start while the arm moves and are dropped if late.
- **Evidence so far (stand-in bricks, Saliha's laptop, NVIDIA Build API):** model `nvidia/nemotron-3.5-super-vl-120b-a12b`. Improvement 1: it is a reasoning model and spent the whole 80-token budget thinking (empty answer), so thinking is turned off for live speech; answers then take 1.7–2.7 s. Improvement 2: given only the score and thresholds, it read "below t_low" as bad and told a perfect brick to be set aside; passing the already-decided action and the band's meaning fixed it (4/4 correct on a small check, including an uncertain brick). Improvement 3 (`reasoner/live.py`): a checker drops any line that names the wrong bowl or quotes a number we did not supply; the worker keeps only the newest request and drops a late or failed answer, so the template line stands. Re-check on a stand-in image through the live path, 6 calls (perfect, defective, uncertain, twice): 6 of 6 consistent with the verdict, 1.9-2.7 s. The 20-frame evaluation is one command once real inspections exist: `python -m reasoner.evaluate cases.csv --persona calm|cowboy` (consistent lines with a 95% interval, failures, time to a line, every contradiction; tested with a fake model). Real-brick run and the verdict-to-first-audio time: TBD (Saturday 22:00). Prompt revisions (2026-11-14 17:22): `python -m reasoner.evaluate cases.csv --system revised.txt` measures a revised prompt on the same frames; `python -m perception.evaluate` writes `runs/evaluate/cases.csv` from the real-brick run.
- **Re-run 17:44 (stand-in images, made-up scores, 12 cases, 20 s timeout; not real bricks):** calm persona 12 of 12 consistent with the verdict (95% interval 74-100%), time to a line p50 2.8 s, p95 4.1 s; cowboy persona 11 of 12 (62-100%, the miss was a timeout), p50 4.8 s, p95 10.6 s. The cowboy lines take longer, so with the robot's 4 s wait many would fall back to the fixed cowboy line. Real-brick run: TBD.
- **Measured risk (2026-11-14 17:35, venue Wi-Fi):** the NVIDIA Build endpoint got slow: a 12-case check with a 15 s timeout failed 11 of 12 (timeouts) and one single request took 32 s, against 1.9-2.7 s earlier in the day; the venue network itself was slow (ping average 322 ms). The robot waits 4 s, so under that load almost every live line falls back to the fixed template line, and the arm never waits. Re-measure on the demo network before claiming a live-line time.
- **Pitch line:** "The model explains what it sees using our measured scores, so it can't make things up."

### D12 · Voice · Live reasoning through ElevenLabs, calm voice by default — Status: Built (live numbered lines, measured on the venue Wi-Fi; Nemotron line wired) / Planned (heard on the real table) · Owner: @harry · Updated: 2026-11-14 17:15
- **Decision:** explanations are spoken through the laptop speakers while the arm works. The robot talks through its thought process in a conversational way, like a person thinking aloud (what it sees, what the score means, what it will do and why), so the judges hear the reasoning behind each move. Default (calm) voice: a standard conversational ElevenLabs voice (`etWmxTqEKhIYyGKMpDcb`, chosen by @harry 2026-11-14 04:11, open to change); the cowboy persona uses David (D13). Live lines use a low-latency ElevenLabs model (`eleven_flash_v2_5`) with streaming and a 1.5 s timeout; exclamations and fallback phrases are pre-generated with the more expressive model and cached as audio. Stale lines are dropped so speech never lags the arm.
- **Why:** the ElevenLabs track rewards natural, emotionally expressive, fully autonomous audio; spoken reasoning makes the system's decisions legible to judges in real time.
- **Alternatives rejected:** a pre-recorded script (not live, not grounded); local text-to-speech only (kept as a stretch offline fallback). Calling the ElevenLabs REST API by hand with `requests` (we would write the audio streaming ourselves); we use the official `elevenlabs` Python SDK pinned to 2.78.0 instead (@harry, 2026-11-14 04:14).
- **Trade-off / risk:** network latency and quota; the cached clips cover it.
- **Evidence:** 37 fixed lines (every event and failure reason, both personas) cached as WAV with `eleven_multilingual_v2`: 1,632 characters of credit, 98 s of audio, committed in `narrator/clips/` so the robot speaks with no network. **Live line (2026-11-14 17:00, `main`):** every verdict is spoken with its own score, the threshold it crossed and where the mark is, through `eleven_flash_v2_5` on its own thread; Nemotron's grounded line follows on real runs (Saliha's `LiveLine`). Full-line synthesis on the venue Wi-Fi: 625–1953 ms over 8 calls; in a mock run the warm-up took 1734 ms and two live lines were ready 1812 and 2812 ms after the verdict. Timeout 3 s (was 1.5 s in the brief; Harry chose 3 s + a warm-up call after measuring), then the cached clip plays; the arm never waits. Time to first audio on the Intel laptop speakers: TBD. **17:55:** the run ends with a spoken summary of the counts ("5 bricks sorted: 3 perfect, 2 defective, and 1 needed a second look"); mission control shows each spoken line as a subtitle (amber for the cowboy); the demo opens with the wheeled base driving the arm to the table, talked over live ("about 42 centimetres out of my reach, so I'm driving over", then distance and time on arrival); mock rehearsal: drive line ready 1156 ms after the stage started. Live line check at 17:46: 609 ms (warm connection), 1922 ms (cold).
- **Pitch line:** "You can hear it think, with the real numbers."

### D13 · Personality · Cowboy persona on obstacle or hat, instant in, gradual out — Status: Built (code, mock-tested) / Planned (on the real table) · Owner: @harry @saliha · Updated: 2026-11-14 16:10
- **Decision:** a persona state machine (CALM ↔ COWBOY). The cowboy voice is **David, deep southern cowboy**, from the ElevenLabs Voice Library (`0hh7H4ZVAtaGpm1VZyEN`, chosen by @harry 2026-11-14 03:45). Triggers: an obstacle (local RealSense depth: taller than a brick or not brick-shaped; the arm skips it, never picks it) or the cowboy hat (Nemotron on the top view, plus an H-key backup). Switching in is instant with a cached "Holy smokes!"; switching out waits until the trigger has cleared and one brick is done, then one half-way line, then calm.
- **Why:** it makes the robot memorable and shows the voice layer reacting to the physical world, without touching the control path. The obstacle trigger uses local depth so it works offline.
- **Alternatives rejected:** a persona picked by the operator only (not reactive).
- **Trade-off / risk:** the personality layer is cut before any task gate slips; a hat in the workspace must be allowed under the safety rules (asked at the mentor session).
- **Evidence:** `narrator/persona.py` (@harry, `main` `ce9a437`): obstacle or H → cowboy with one cached exclamation; back to calm through the half-way line once every trigger has cleared and one brick is done; H is one-shot (no "hat gone" signal; Harry 16:00). 9 tests incl. two threads triggering at once. Switch time on the real table: TBD. **18:10:** an unfamiliar object is now named out loud: the cached "Holy smokes!" at once, then a naming model (Saliha's pick) gives a short name off the control thread and the cowboy says "Holy smokes, there's a coffee mug in my zone!" if it comes back within 3 s (`narrator/naming.py`; stand-in model named it in ~0.8 s). On the venue Wi-Fi ElevenLabs stalled 6–12 s at times, so the live line was dropped; the demo runs on a phone hotspot.
- **Pitch line:** "The robot reacts to the world and changes its voice, then calms down."

## E. Data and cloud

### D14 · Streaming · Aiven Kafka for live events, PostgreSQL for the record — Status: Built (PostgreSQL record, verified live; drift alarm, fake-DB tested) / Planned (Kafka stream; drift alarm on real bricks) · Owner: @harry · Updated: 2026-11-14 16:10
- **Decision:** the telemetry thread produces every event to an Aiven for Apache Kafka topic; a consumer runs a drift check (recent perfect-brick scores creeping toward `t_low` → "lighting changed, rebaseline" alert, spoken) and writes rows to Aiven PostgreSQL for the trial report. If Kafka is not on our plan, PostgreSQL `LISTEN/NOTIFY` does the same job.
- **Why:** Aiven's rubric rewards meaningful use of its services; streaming lets other parts of the system react to the cell live, and the drift alarm changes what the robot does. It is not on the control path, so it does not add latency to the arm; honest framing: a cloud hop never makes the robot itself faster.
- **Alternatives rejected:** a plain log table only (low meaningful use).
- **Trade-off / risk:** offline → JSONL buffer, synced later.
- **Evidence:** live on Aiven's free PostgreSQL plan (18.7): a mock run's 37 events all landed, re-sending them all left 37 (duplicate-free), connect ~0.4 s warm, 5.3 s cold; the robot never waits on it (a separate sync thread reads the local JSONL buffer). Both Aiven services we need have free plans with no card. TBD (Kafka events streamed, drift alert fired in the trial run). **Drift alarm (16:10, `main` `ce9a437`):** after each batch the sync thread asks PostgreSQL for this run's first-look perfect scores and runs `perception.drift`; an alert is spoken once and shown as a banner, the arm never stops (Harry 16:00: speak + banner only). A failed drift query sits in a savepoint, so the events still land. Off until `good_mean` is saved and on mock runs. Live query against Aiven: TBD.
- **Pitch line:** "Aiven carries the cell's live event stream and raises the alarm when lighting drifts."

### D15 · Training · Modal for training and logs only, no frontend — Status: Built · Owner: @nate · Updated: 2026-11-14 16:15
- **Decision:** ACT and SmolVLA train on Modal GPUs from a reproducible script, with GPU type, time and cost logged. No dashboard or web app (the planned live dashboard was dropped). Real runs are started on the deployed app (`modal deploy`, then `python -m train.launch` spawns each job), not from a client that waits: twice on 2026-11-14 the laptop's network dropped and Modal cancelled the training call it was waiting on.
- **Why:** Intel provides Modal GPUs for training; Modal's own page scores a deployed app (15%), but a frontend is out of scope for the team, so we accept losing those points rather than risk the main track.
- **Alternatives rejected:** a Modal-hosted dashboard (dropped); training on the laptop.
- **Trade-off / risk:** if Modal's prize needs a web app, we drop Modal. Training containers keep Modal's default CPU: on it, SmolVLA's loader took 0.07 s per step against a 0.2 s update, so the GPU was not starved; revisit if a dataset lacks q01/q99 statistics (Studio then spends ~40 s per episode on a one-off pass).
- **Evidence:** first Modal runs in `train/runs.md` (SmolVLA smoke: 200 steps, 1.8 min, ≈ $0.06).
- **Pitch line:** "Training scales out in the cloud, inference stays on the device."

## F. Team and process

### D16 · Process · Roles split by discipline, one branch per person — Status: Built · Owner: @saliha · Updated: 2026-11-14 01:30
- **Decision:** AI/ML (perception, edge optimisation, reasoning) = Saliha; Robotics and robot learning (robot I/O, policies, training) = Nate; Systems and integration (state machine, voice, streaming, demo) = Harry. One branch each: `aiml-perception-saliha`, `robotics-policies-nate`, `systems-voice-harry`. Plan docs on a `context` branch, `progress.md` on `main`.
- **Why:** disjoint folders mean few merge conflicts; the board shows who shipped what and whether it conflicts; two agent skills (`no-slop`, `debug`) keep code and debugging disciplined.
- **Alternatives rejected:** sharing docs over chat (drift).
- **Trade-off / risk:** contract changes after the 01:00 Saturday freeze need all three to agree.
- **Evidence:** `progress.md` log.
- **Pitch line:** "Three owners, clean interfaces, and a live board of who changed what."

### D17 · Priority · The Intel task comes first; personality is built on top — Status: Built · Owner: @saliha · Updated: 2026-11-14 01:30
- **Decision:** the personality layer (reasoner, voice, persona) is built only on a working loop and is cut before any gate slips. Features over ~10 hours are parked in a local-only extension file.
- **Why:** the main track is scored out of 100 and the side tracks ride on the same project.
- **Evidence:** gates in PRD §10.
- **Pitch line:** "The sorting works first; the character is the cherry on top."

---

### D18 · Process · Perception pipeline built end to end before the hardware existed — Status: Built · Owner: @saliha · Updated: 2026-11-14 03:55
- **Decision:** on Friday night, with no Intel laptop and no robot, build the whole perception path (capture → train → export → calibrate → inspect → benchmark → rebaseline) against synthetic stand-in bricks (`perception/synth.py`: coloured bricks with marker strokes), with an automated end-to-end test. On Saturday only the photos change.
- **Why:** the robot slots are scarce (one user at a time); every hour of setup moved off the hardware is an hour for real data and trials.
- **Alternatives rejected:** waiting for the station; a public dataset (different objects, no marker defects).
- **Trade-off / risk:** nothing measured on synthetic bricks is reported; real-brick numbers replace them.
- **Evidence:** 28 automated tests including a full train → export → calibrate → inspect run (`main` @ `dd1c4d7`).
- **Pitch line:** "Our perception pipeline was tested end to end before we touched the robot."

### D19 · Safety · Every arm command is clipped to joint limits and a speed cap — Status: Built · Owner: @nate · Updated: 2026-11-14 06:12
- **Decision:** all motion, learned or scripted, goes through `robot/io.py`, which clips each command to the SO-101 driver's joint limits and moves no joint more than 5° per 30 Hz step; E turns torque off. The gripper and inspection-pose thresholds live there too, so the learned and scripted movers judge "holding" and "at the pose" by the same numbers.
- **Why:** a policy can output any number; the printed safety rules and judges' reliability criterion need motion that is bounded no matter what the model does. Smooth motion is also part of the task-success score.
- **Alternatives rejected:** trusting the policy's output; limits inside each policy (easy to forget one).
- **Trade-off / risk:** the cap slows big moves; tuned on the station with the arm watched.
- **Evidence:** unit tests (`robot/tests/test_io.py`); on-arm value TBD.
- **Pitch line:** "Whatever the AI says, the arm stays inside safe limits."

### D20 · Training · Studio's trainer for ACT, LeRobot for SmolVLA — Status: Built · Owner: @nate · Updated: 2026-11-14 17:25
- **Decision:** `train/modal_train.py` trains ACT with Physical AI Studio's own trainer (`physicalai fit`, `physicalai-train` 0.3.0) and fine-tunes SmolVLA from `lerobot/smolvla_base` with LeRobot 0.7.0, each in its own Modal image on an A100.
- **Why:** the runtime on the laptop (`physicalai` `InferenceModel`) loads policies exported by Studio, and Studio's ACT exports to OpenVINO with one documented call, so the pick policy needs no conversion step; it also makes Studio visibly part of training (criterion 3). Studio's SmolVLA weight loader is marked "intentionally incomplete" in its source, so SmolVLA stays on LeRobot, where fine-tuning `smolvla_base` is the standard path.
- **Alternatives rejected:** LeRobot for both (no documented route from its checkpoints into the `physicalai` export; confirmed 05:45 by Saliha's agent: `physicalai-train` 0.3.0's LeRobot wrapper `physicalai.policies.lerobot.ACT.from_pretrained("lerobot/act_aloha_sim_transfer_cube_human").export(..., backend="openvino")` raises `NotImplementedError ... Supported backends: [torch]`, while the native `physicalai.policies.act.ACT` lists OpenVINO and ONNX); Studio for both (SmolVLA could not start from `smolvla_base`).
- **Trade-off / risk:** two dependency stacks to keep working; SmolVLA's export route is proven on CPU through `InferenceModel` (A3) but not yet on the Intel GPU or NPU, with the PRD's fallback of running SmolVLA in PyTorch.
- **Evidence:** a unit test parses the ACT command with Studio's own `fit` parser. SmolVLA on LeRobot trained 200 steps on Modal in 1.8 min (A100, ~5 steps/s, 2026-11-14, `train/runs.md`). Studio's trainer spends ~40–70 s per episode on a one-off quantile pass when a dataset has no q01/q99 statistics (public sets; ~70 s without loader workers on the ACT smoke run, so 50 episodes cost ~1 h before step 1). That pass opens video decoders in the main process, and forked loader workers inherited them and crashed the first ACT run ("Invalid data found when processing input"); reproduced on Modal and fixed by training without loader workers (`--data.num_workers 0`). The LeRobot-trained SmolVLA smoke checkpoint loads into Studio's SmolVLA (`pretrained_name_or_path`, float32) and exports to OpenVINO (1.57 GB FP32 IR plus a tokenizer IR); compiled on CPU it returns a 50×6 action chunk from three 512×512 camera inputs and a 48-token prompt, 1.67 s per chunk on Modal's 4-core CPU (not an Intel number; `train/export.py`, `train/runs.md`). Loaded through `InferenceModel(..., device="CPU")`, the laptop's call path, a zero observation plus the real task string gives a finite 50×6 chunk (1.9 s first call, 2026-11-14 16:50). That test also caught a mismatch: the exported runtime reads `state`, `images.<camera>` and `task` with RGB frames, while the policy runner sent LeRobot's dataset keys and OpenCV's BGR frames (fixed in `policies/episode.py`, `f22367c`). Parity (`train/parity.py`, 17:15): on identical inputs with zero starting noise, LeRobot's own SmolVLA and the IR agree to 2.6e-6 on actions up to 2.36, and the exported tokenizer matches LeRobot's token ids, so the weights survive LeRobot → Studio → OpenVINO. The ACT smoke checkpoint exports too: 137 MB IR, a 100×6 chunk in 97 ms through `InferenceModel` on Modal's CPU (17:12). Through our own runner (`policies/episode.py`) on a mock robot both exports drive the arm in degrees; on an Intel Core Ultra 5 125H CPU (Nate's PC, not the demo laptop) a SmolVLA chunk takes about 7.4 s and an ACT chunk about 0.1 s (17:25). TBD: the demo laptop's GPU latency, real-data runs.
- **Pitch line:** "The pick policy is trained in Intel's Physical AI Studio and exported straight to OpenVINO."

### D21 · Safety · E-stop: keys set a flag, only the control thread talks to the motors — Status: Built · Owner: @harry @nate · Updated: 2026-11-14 05:47
- **Decision:** pressing E (or Ctrl+C) sets an e-stop flag; the control thread checks it on every scripted control step and at every stage boundary, turns the torque off and stops, and never homes afterwards. The mission-control window runs on the main thread and only sets flags (S, P, E, Q, H). Since 05:47 `robot/io.act()` checks the same flag too (@nate), so learned-policy motion, `move_to` and the scripted fallback all stop within one control step.
- **Why:** the motor driver was never checked for two threads writing to the serial bus at once; a garbled command at the moment of an e-stop is the worst case. A flag costs at most one control step (about 33 ms at 30 Hz), in which the 5° per step speed cap limits motion.
- **Alternatives rejected:** calling torque-off straight from the window thread (fastest, but two writers on the bus); a lock around every motor call plus the direct call (more code in the shared robot layer for at most 33 ms).
- **Trade-off / risk:** a stop can take up to one control step (about 33 ms); learned policies used to stop only at the next stage boundary, closed at 05:47 by the `io.act` check. E = torque off, so the arm drops: a person always watches it (PRD §9).
- **Evidence:** tests: a scripted move stops part way within 0.5 s of E with torque off; E mid-run never homes; Q finishes the brick and homes; P holds at a stage boundary; with E requested, `io.act` and `io.move_to` raise with torque off and no command sent (`robot/tests/test_io.py`). TBD (stop latency on the real arm).
- **Pitch line:** "The stop button never fights the robot for the wire: one thread drives the motors, and it checks for the stop every step."

### D22 · Reliability · Every stage verified: grasp band, bowl-region check, early exit, reason codes — Status: Built (reasons, deadlines, PAUSE_HUMAN in `run.py`; grasp band, early exit and the bowl-check hook in `policies/mover.py`, 2026-11-14 14:44) / Built (bowl check in `run.py` after home, scripted grasp via `io.holding()`, 2026-11-14 16:10) / Planned (band limits from the N8 readings) · Owner: @nate @harry @saliha · Updated: 2026-11-14 05:53
- **Decision:** grasp = gripper position inside a band (not just "not fully closed") after a 0.3 s settle; place = the bowl region on the top camera changes and the gripper is open; policies stop early when their stage succeeds; every failure gets a reason code, a deadline and a retry budget, ending in "I need help" (PAUSE_HUMAN) rather than a crash.
- **Why:** "correct bowl" can't be counted automatically otherwise, and fixed 12 s episodes made 24 s per brick a floor against a 25 s target. A gripper watchdog paper (arXiv 2604.07395) detected 43/50 empty grasps with 5/50 false alarms; a 2026 SO-101 benchmark (arXiv 2606.08881) measured learned recovery at 3–6%, so recovery belongs in the state machine.
- **Alternatives rejected:** servo-current grasp detection (no source for the STS3215; saved); a behaviour tree (more machinery for a short controlled task).
- **Trade-off / risk:** thresholds are TUNE on the arm; bowl-region check needs a lit, fixed top camera.
- **Evidence:** `run.py` (@harry): seven reason codes in every `events` outcome, deadlines on PICK/REINSPECT/PLACE/HOME that stop the scripted motion loop, PAUSE_HUMAN with P/Q, a hold flag; tested on mocks (stuck pick → timeout in < 2 s, no retry; bug → paused, not crashed). TBD (20-trial log with per-stage reasons). **Place check (16:10, @harry):** after a place the arm goes home and `run.py` compares the named bowl region with a top frame from before the pick (`VERIFY_PLACE`); the arm would otherwise hide the bowl. Costs one home move per brick (TUNE, measured on the arm: TBD). Bowl → region via the same colour lookup as the scripted mover.
- **Pitch line:** "Every step proves it worked before the next one starts."

### D23 · VLA · Two fixed instructions that carry the verdict, a language-swap test, and a colour hedge — Status: Planned · Owner: @nate · Updated: 2026-11-14 17:12
- **Decision:** perception picks one of two fixed strings that carry its verdict, `"the brick is perfect, place it in the purple bowl"` and `"the brick is defective, place it in the orange bowl"` (changed 2026-11-14 14:26 from the colour-only wording, before any SmolVLA episode was recorded; D31); at the 19:00 gate a language-swap test (same brick, swapped string) proves SmolVLA reads the instruction. Hedge: two single-colour ACT place policies trained on Modal in parallel from the same data (no extra robot time), evaluated only if SmolVLA < 6/10; scripted placement remains the fallback.
- **Why:** SmolVLA's tokenizer is capped at 48 tokens and we have 25 episodes per string, so scores or regions in the string would be unseen text. A 2026 SO-101 benchmark (arXiv 2606.08881, 20 trials per cell) got ACT 0% and SmolVLA 5% on a colour-sorting task, so the language-chosen bowl is the riskiest step.
- **Bowl colours (2026-11-14 15:08):** the strings use the physical bowl colours, `"the brick is perfect, place it in the purple bowl"` and `"the brick is defective, place it in the orange bowl"` (our bowls are purple and orange, not the slides' blue and red). Nothing had been recorded with the earlier wording.
- **Why the verdict is in the string (D31):** Intel's expectation 2 and the 20-point criterion say the VLA translates perception results and the task instruction into actions; both words are perfectly correlated, so it costs no data and no extra learning, and `fallback/scripted.py` still finds "orange bowl" / "purple bowl" in the text. Uncertain bricks go through the recovery chain and end as defective, so they use the defective string.
- **Colour hedge code (2026-11-14 17:07, `main`):** `python -m train.hedge <dataset> --repo-id <id> --steps N` lists each string's episodes and prints one Modal ACT launch per colour (`--episode-ids`, `--tag`); tested on a synthetic dataset, the Modal path itself untested. Launch only if SmolVLA is under 6/10 at its gate.
- **Alternatives rejected:** region- or score-conditioned instructions; co-training with public SO-101 data (saved for later).
- **Evidence:** both strings live in `config/rules.yaml` on `main` (`5e99561`, 14:40); swap test TBD (19:00 gate).
- **Pitch line:** "We prove the robot listens: swap the words, the brick goes to the other bowl."

### D24 · Deployment · Device placement measured, no overlap claims — Status: Built (harness, first Intel-laptop run on a stand-in model) / Planned (real model, policies) · Owner: @saliha · Updated: 2026-11-14 17:22
- **Decision:** detector on the NPU (GPU, CPU fallback); ACT on the GPU with a 30-minute NPU compile probe (a failed compile is a reported result); SmolVLA on the GPU via OpenVINO if its export works, otherwise PyTorch, and the table says which. Device table from OpenVINO `benchmark_app` plus a PyTorch baseline row; efficiency = idle baseline, 1 Hz power and thermal series, NPU busy time, joules per brick net of idle. No AsyncInferQueue headline, no cross-device "overlap" (the loop is sequential), no HETERO/MULTI/NPU_TURBO.
- **Why:** the rubric asks for appropriate NPU/GPU/CPU use and efficiency evidence; OpenVINO's own hints guide says async only helps with several requests in flight.
- **Evidence (2026-11-14 16:44, Intel laptop, stand-in PaDiM INT8, on battery, idle 2.3 W):** package power while running about 26 W on the CPU, 30 W on the GPU, 11 W on the NPU; energy per inference net of idle 234 mJ (CPU), 31 mJ (GPU), 64 mJ (NPU); OpenVINO `benchmark_app` medians 8.7 / 0.92 / 6.6 ms agree with our harness (9.6 / 1.0 / 7.2 ms). **Open, Saliha's call:** on this chip the GPU is about 7 times faster than the NPU for the detector and uses about half the energy per inference; the NPU keeps package power lowest and leaves the GPU free for ACT and SmolVLA. The placement stays NPU until she decides. **5-minute sustained run (17:16, mains, `bench/sustained.py`):** latency late vs early in the run: NPU 0.96× (no slowdown, 14.7 W package), CPU 1.06× (20.5 W), GPU 1.43× (1.00 → 1.43 ms, 20.1 W). **ACT-on-NPU probe (17:20, `bench/act_npu_probe.py`):** Studio's ACT with our three cameras and random weights compiles on the NPU in 2.3 s and runs at 8.9 ms per call (GPU 4.2 ms, CPU 65.7 ms), so ACT on the NPU is a real option, not only a probe. Joules per brick: TBD (real model, trained policies).
- **Pitch line:** "Each model is on the chip that suits it, and we measured joules per brick."

### D25 · Reasoning · Nemotron is advisory, never gating — Status: Planned · Owner: @saliha · Updated: 2026-11-14 07:10
- **Decision:** the decision is always the thresholds + rules; Nemotron only explains, never judges a brick (the "second opinion on uncertain bricks" was dropped 2026-11-14 14:19 on mentor guidance, D31: Anomalib is the only anomaly detector), with a 4 s timeout and a template fallback. Camera-based hat detection is saved for later; the H key triggers the cowboy persona.
- **Why:** control must never wait on the network (D4); the live line is the personality layer, not the sorter.
- **Pitch line:** "The robot decides with measured thresholds and explains itself out loud."

### D26 · Process · Pipeline smoke-tested on public SO-101 data before robot time — Status: Built (SmolVLA trained and exported to OpenVINO; ACT pending) · Owner: @nate · Updated: 2026-11-14 16:35
- **Decision:** train ACT (Studio) and SmolVLA (LeRobot) for a few hundred steps on `eruedas/so101_3cams_pickplace-red-lego_real` (Apache-2.0, SO-101, 50 episodes, top + gripper + side cameras, 30 fps), export, and run the `physicalai` runtime on it before our own recording. Not used for final training. Starting SmolVLA from someone else's SO-101 fine-tune and co-training with public data were researched and saved for later (no evidence they beat the base model; choosing by trials would need ~78 trials per arm).
- **Why:** the SmolVLA export is the biggest unknown; finding it at 09:00 beats finding it at 19:00.
- **Evidence:** SmolVLA 200 steps on the red-lego set: AV1 video decodes, cameras `top,gripper,left` mapped onto `smolvla_base`'s `camera1..3`, loss 0.287 at step 200, 1.8 min on an A100 (`train/runs.md`). It also caught two real problems before robot time: a missing `lerobot[training]` extra and the camera-name mismatch. The same checkpoint exported to OpenVINO through Studio and returned an action chunk on CPU (D20). The ACT smoke caught a third: Studio's trainer crashing on video decoding in forked loader workers (D20).
- **Pitch line:** "We proved the whole train-export-deploy chain before the robot moved."

### D27 · Perception · "Is it a brick?" check before inspection (Nate's key-system idea) — Status: Built · Owner: @saliha · Updated: 2026-11-14 08:50
- **Decision:** before picking, the top camera classifies every saturated blob in the zone as brick or not-brick by rule: footprint 2×2 to 2×4 Duplo (±40%, TUNE), aspect ≤ 2.5, solidity ≥ 0.8. Bricks go to the most-isolated pick; anything else is an obstacle (skipped, and it can trigger the cowboy persona). No learned classifier.
- **Why:** the slides' defects are defective *bricks*; a non-brick object must never reach the defect detector or the gripper. The colour-blob step already exists, so the rule costs ~0.5 h, where a trained classifier would need data we don't have.
- **Alternatives rejected:** a learned brick/not-brick classifier; fiducial markers (research graded ArUco evidence weak).
- **Trade-off / risk:** unsaturated objects (grey, skin) are invisible to colour; depth (`tall_object`) covers anything taller than a brick.
- **Evidence:** `perception/scene.py`, 9 tests on synthetic top views; on-station thresholds TUNE.
- **Pitch line:** "It checks it's holding a brick before it judges the brick."

### D28 · Personality · End-of-run dance — Status: Built (code; accepted by @nate 11:53) · Owner: @saliha (code in Nate's `robot/`) · Updated: 2026-11-14 11:53
- **Decision:** when the zone is empty after the last place, the arm dances: base sways ±25° for 3 cycles while the head bows 10° and tilts 10° towards each side, ~6 s, then home. Pure `robot.io` motion.
- **Why:** a memorable, safe sign-off for the demo and video that costs no robot time to build; it reuses the joint limits, 5°/step speed cap and e-stop (D19, D21).
- **Trade-off / risk:** joint sign conventions are TUNE (a move may go the wrong way the first time); never runs while holding a brick (run.py calls it only after the final place).
- **Evidence:** `robot/dance.py`, 5 tests on the mock arm (speed cap, limits, e-stop, ends at home).
- **Pitch line:** "And when the job's done, it celebrates."

### D29 · Data · Degrees end to end, three cameras in every recording — Status: Planned · Owner: @nate · Updated: 2026-11-14 11:53
- **Decision:** record joint positions in degrees, the unit `robot/io.py` drives the follower in, and record all three cameras (`top`, `inspect`, `wrist`) under exactly those keys in both datasets. SmolVLA maps them onto its pretrained slots as `top`→`camera1`, `wrist`→`camera2`, `inspect`→`camera3`.
- **Why:** a policy trained on one joint unit and run in another commands the wrong positions; degrees keep the joint limits and the 5°/step speed cap in real angles (D19). `smolvla_base` was pretrained with three camera slots, and LeRobot rejected a two-camera dataset in our smoke run; one camera setup for both datasets keeps recording simple.
- **Alternatives rejected:** normalized units end to end (Studio's driver default; every limit and tuning value would change, and "5 per step" would mean a different angle per joint), kept as the fallback if Studio can't record degrees; two cameras only (SmolVLA's third slot would be empty).
- **Trade-off / risk:** ACT processes three images per step (more inference time; Saliha's benchmark measures it). Whether Studio records degrees is unverified until the first test episode is compared with `robot.io.observe()`. The public red-lego set is normalized, harmless because its models never drive our arm.
- **Evidence:** TBD (first Studio test episode).
- **Pitch line:** "What we record is exactly what the robot runs: same units, same cameras."

### D30 · Efficiency · Preprocessing inside the OpenVINO graph, operator-support table, drift rule — Status: Built (code, CPU numbers) / Planned (Intel laptop runs) · Owner: @saliha · Updated: 2026-11-14 12:40
- **Decision:** `perception/preprocess.py` writes `model_ppp.xml` beside each exported IR: the BGR→RGB flip, the /255 scaling and the NHWC→NCHW layout change run inside the graph (OpenVINO `PrePostProcessor`), so the model takes the resized frame as 1×256×256×3 uint8. Resizing stays on the CPU with the same INTER_AREA call, because OpenVINO's resize modes differ and would shift the scores `t_low`/`t_high` were measured with. `bench/operators.py` lists, per model and device, which operators the plugin can run (`query_model`) and which are left out, appended to `bench/results.md`. `perception/drift.py` is the F15 drift rule: how far the last 8 perfect bricks (at least 5) have crept from the good baseline (`good_mean` in `thresholds.yaml`) towards `t_low`; alarm at 0.5 (TUNE).
- **Why:** the Intel slide names pre/post-processing and device choice "by operator support" (R7, R8); Aiven's meaningful-use score needs the stream to change what the cell does, and the drift alarm is that.
- **Alternatives rejected:** moving the resize into the graph too (changes the scores); replacing the plain IR (both stay, the benchmark shows both rows and the measured numbers pick the deployed one).
- **Trade-off / risk:** a second IR per model to keep in step; all thresholds TUNE on real bricks; NPU and GPU operator rows need the Intel laptop.
- **Evidence (this laptop's CPU, stand-in bricks, not Intel numbers):** FP16 detector end-to-end p50 44.5 ms → 38.5 ms and p95 63.7 → 43.3 ms with preprocessing in the graph; INT8 unchanged (71.6 vs 72.2 ms, and slower than FP16 here); scores identical to 4 decimals in both; the PaDiM IR runs all 223 operators on CPU. A unit test on a toy model fails if the colour flip or the scaling is dropped. TBD (GPU and NPU rows on the Intel laptop).
- **Pitch line:** "The model takes the raw camera frame; the Intel toolchain does the maths."

### D31 · Architecture · Mentor guidance: Anomalib is the only detector, the VLA does the integration, rehearse a move with the leader first — Status: In force; both proposals adopted 2026-11-14 14:26 · Owner: @saliha · Updated: 2026-11-14 14:19
- **Decision:** an Intel organiser-mentor told Saliha (relayed 2026-11-14 14:19) that (1) Anomalib alone finds anomalies and the VLA must never do anomaly detection; (2) the VLA layer, built in Intel Physical AI Studio, does the integration across perception, reasoning, planning and manipulation: it translates perception results and the task instruction into robot actions (slide "VLA Reasoning & Task Planning", criterion "VLA & Physical AI Studio Integration", 20 pts); (3) a move can be tested first by teleoperating with the leader arm, then fine-tuned from the recorded demonstrations.
- **What the plan already does:** Anomalib is the only detector (D5); SmolVLA only places, ACT only picks (D2, End Goal slide); recording is leader-follower teleop followed by fine-tuning (D20, N6, N7). Changed now: Nemotron's logged "second opinion" on uncertain bricks is dropped (D25), because a vision-language model giving a defect opinion blurs rule (1). The PRD judging table now names which part of the system is perception, reasoning, planning and manipulation.
- **Decided 2026-11-14 14:26 (Saliha asked Claude to reason it through and decide):** (a) YES: the two VLA strings carry the verdict (`"the brick is perfect, place it in the purple bowl"`, `"the brick is defective, place it in the orange bowl"`, D23). Reasoning: it is free before recording, it makes the VLA literally translate a perception result, the scripted fallback and tests still work, the language-swap test still proves the instruction is read; the only risk is the existing colour-sorting risk, not a new one. (b) YES, folded into the practice runs so it adds about 5 minutes, not 15: before the first recorded episode, rehearse every stage with leader-follower teleop (all 9 start dots, the inspection hold with the wrist roll, both bowl drops, the gripper readings, the joint-unit check, one e-stop press). Reasoning: the 54 + 50 demos are the expensive step, and a position the arm cannot reach or a pose the camera cannot see would be found after recording otherwise. Failures move the tape or bowl, not the policy; nothing from the rehearsal is recorded.
- **Open question for the mentors (PRD §0 Pending):** SmolVLA is fine-tuned with LeRobot because Studio's SmolVLA loader is marked incomplete (D20); is that acceptable for "VLA & Physical AI Studio Integration", or is there a Studio route in the installed version?
- **Evidence:** the six judging-slide screenshots (Overview, Required Technology Stack, Technical Implementation Expectations, Judging Criteria, HW/SW, End Goal) read on 2026-11-14 14:19; no measured result yet.

### D32 · Data · Data quality first, hyperparameters second, audited automatically — Status: Planned (auditors being built) · Owner: @saliha (image audit), @nate (protocol, episodes) · Updated: 2026-11-14 14:39
- **Decision:** a second mentor told Saliha (relayed 2026-11-14 14:39) that data quality matters more than quantity, and that hyperparameter tuning comes second. So: (1) every dataset is audited by code before it trains anything: perception images (blur, exposure, near-duplicates, lighting drift across the session, per-brick coverage) and robot episodes (duration, hesitation, cadence, joint-unit range, end-of-episode hold, balance between the two task strings, exact task strings, camera keys, statistics present); (2) the audit runs before episode 1 on the rehearsal-quality checks, after every recording round, and before every Modal launch; a failing episode is re-taken at the same position (the rejected-episode log stays); (3) no hyperparameter sweep before the audit passes; after that, one small Modal sweep (learning rate and steps, chunk size for ACT) on the same data, run in parallel so it costs no robot time, picked by offline validation loss and confirmed with at most 10 trials; ACT stays at lr 1e-5 until a sweep beats it (1e-4 collapsed to a constant pose in Studio issue #998).
- **Why:** the Junction page gives 20% to "clean teleoperation data and fine-tuning"; an imitation policy is only as good as its demos (D1); robot time is the scarcest resource (about 4.5 h), while Modal time is cheap.
- **Alternatives rejected:** tuning first (cannot fix bad demos); more episodes without checking them (the F11 curve would then measure noise).
- **Trade-off / risk:** the thresholds in the audit (hesitation, blur) are TUNE until real data exists; an audit can flag good episodes, so it flags and a person decides.
- **Evidence:** `perception/audit.py` and `train/audit.py` built (2026-11-14 15:25, 204 tests pass); on the public SO-101 red-lego dataset (50 episodes) the episode audit reproduces what the smoke run found by hand: no q01/q99 statistics, normalized units, one 2 s hesitation, no failures. TBD (first report on our own episodes).
- **Pitch line:** "We checked every demonstration by code before we trusted it."

### D33 · Process · Base docked for recording; a base move waits until after the freeze — Status: Planned · Owner: @nate · Updated: 2026-11-14 16:15
- **Decision:** the follower's base sits in a dock (taped outline and a stop block behind it) and stays clamped there for every recorded episode and every run. Moving the base (the parked wheeled-platform idea, option b in PRD §0) happens only after the 23:00 freeze, on the parked item's conditions, and always re-docks before any learned policy runs. The mentors said unclamping is allowed (Nate asked, 2026-11-14).
- **Why:** every learned policy, taught waypoint and camera view assumes the base never moves; the dock makes its position repeatable, so a later move costs no recorded data. Moving it before the gates would take robot time while nothing is recorded.
- **Alternatives rejected:** building the move before recording (robot time, gate risk); dropping it (loses a distinctive demo moment).
- **Trade-off / risk:** the arm's mass sits high and forward when it reaches, so an unclamped base can tip; E turns the torque off and the arm drops. Any move is rehearsed clamped first, with someone holding the cables. Needs Harry's yes (board row 16:15).
- **Evidence:** TBD.
- **Pitch line:** "It can leave its station and come back to exactly where it learned."

## Pitch cheat sheet (fill the numbers only when measured)
| Judge cares about | Our answer | Where the proof will be |
|---|---|---|
| Does it work end to end? | Pick → inspect → place with learned policies and a scripted fallback | 20 logged trials (Aiven report) |
| Defect detection quality | Anomaly detection on real bricks; two-threshold band | AUROC, confusion matrix, heatmap |
| Intel deployment | NPU / GPU / CPU on purpose, INT8, compile cache | Benchmark table, p50/p95 |
| Efficiency | Energy per inference, temperature over the trials | `bench/results.md` |
| Data and training | Clean demos, rejected-episode log, success vs demos | `train/`, HF dataset card |
| Reliability | Re-inspect and re-grasp, grasp retry, e-stop | Live demo, trial log |
| Nemotron | Grounded live reasoning, evaluated | Eval table, on-screen lines |
| ElevenLabs | Live spoken reasoning, cowboy switch | Video |
| Aiven | Live event stream and drift alarm | Kafka topic, alert in the video |

**Claims we must not make:** a scripted placement as SmolVLA; any number before it is measured; "faster because of the cloud"; that the robot detects things it was not tested on.
