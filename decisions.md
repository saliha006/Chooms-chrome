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
- **Alternatives rejected:** RL fine-tuning of the policy (reward design plus many real-robot trials; no simulator in scope); hand-scripted motion only (kept as the fallback, D6, not as the main system).
- **Trade-off / risk:** an imitation policy is only as good as its demonstrations, so dataset quality matters (it is 20% of the Junction page rubric): tight 10×10 cm pick zone, rejected-episode log, dataset card, and a success-vs-number-of-demos sweep (D9).
- **Evidence:** TBD (10-trial gate results, `progress.md`).
- **Pitch line:** "We taught the arm by showing it, the way Intel designed the stack, and measured how few demonstrations are enough."

### D2 · Pipeline · ACT picks, Anomalib inspects, SmolVLA places — Status: Built (code, mock-tested) / Planned (trained policies) · Owner: @nate @saliha · Updated: 2026-11-14 01:30
- **Decision:** the pipeline from Intel's End Goal slide: ACT picks and presents the brick, Anomalib scores it, the verdict becomes a language instruction ("place the brick in the red/blue bowl") for SmolVLA, which places it.
- **Why:** it is the reference task, and the verdict-to-instruction step is exactly where a vision-language-action (VLA) model earns its place: one policy, two behaviours, chosen by language.
- **Alternatives rejected:** one policy for the whole loop (needs more demonstrations than we can record; kept as an extension idea).
- **Trade-off / risk:** SmolVLA export bugs (Studio issues #1384, #1414, #1169) and needs ~50 episodes; gate at Saturday 19:00 keeps it if ≥ 4/10 unless scripted placement is clearly better.
- **Evidence:** TBD (gate results).
- **Pitch line:** "The inspection result literally becomes the instruction the robot follows."

### D3 · Reliability · Scripted fallback behind the same interface — Status: Planned · Owner: @harry · Updated: 2026-11-14 01:30
- **Decision:** a scripted waypoint mover sits behind the same `Mover` interface as the learned policies, and a full scripted loop must pass by Saturday 15:30 before the learned policies are swapped in.
- **Why:** an earlier team on this challenge (ohong/intel-robotics) never moved its arm; the end-to-end criterion is 25 points. The loop must work even if a model fails.
- **Alternatives rejected:** learned policies only (a single export bug would sink the demo).
- **Trade-off / risk:** the demo must always say which mode ran; a scripted placement is never presented as SmolVLA.
- **Evidence:** TBD (15:30 gate).
- **Pitch line:** "Every learned part has a safe fallback, and we tell you which one is running."

### D4 · Safety and latency · Control never waits on the network — Status: Planned · Owner: @harry · Updated: 2026-11-14 01:30
- **Decision:** the control loop, inference and the arm never touch the network. Reasoning (Nemotron), voice (ElevenLabs) and telemetry (Aiven) run on their own threads and degrade to templates, cached clips and a local JSONL buffer.
- **Why:** venue Wi-Fi can drop or lag; the arm must stay responsive and safe (E = torque off). Cloud calls are tens to hundreds of milliseconds and variable.
- **Alternatives rejected:** calling the cloud inside the state machine.
- **Trade-off / risk:** the spoken line can be late; stale lines are dropped.
- **Evidence:** TBD (latency of each thread in the logs).
- **Pitch line:** "The robot's safety never depends on the internet."

## B. Perception ML (Anomalib)

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

### D7 · Reliability · Two-threshold uncertainty band and re-grasp — Status: Built (band) / Planned (re-grasp chain) · Owner: @saliha @nate · Updated: 2026-11-14 04:16
- **Decision:** `t_low` = 99th percentile of good-brick scores, `t_high` = 5th percentile of defective scores; below `t_low` perfect, above `t_high` defective, between uncertain. Uncertain → second camera view → re-grasp (Intel's own suggested idea: use the anomaly score to trigger a re-grasp) → wrist roll if time → defective, said aloud. Re-grasp and wrist roll share one motion call, `Mover.reinspect(angle_deg)`: `0` puts the brick down in the pick zone and picks it again, `±90` rolls the wrist in place, and it returns `True` only when the brick is back at the inspection pose (agreed by @nate and @saliha 2026-11-14 01:35, @harry 2026-11-14 04:16).
- **Why:** anomaly scores are distances, not probabilities, so thresholds must come from data; the rubric scores recovery from uncertain detections. One call keeps the `Mover` signature that froze at 01:00 Saturday, so the learned policies and the scripted fallback implement the same thing.
- **Alternatives rejected:** a single threshold (every borderline brick is a coin flip); a separate `regrasp()` method (reopens the frozen contract); re-grasping before every wrist roll (each roll would cost a full re-grasp).
- **Trade-off / risk:** a re-grasp costs cycle time; capped at one re-inspection.
- **Evidence:** TBD (planted borderline brick handled 3 times in a row).
- **Pitch line:** "When it isn't sure, it looks again instead of guessing."

## C. Edge optimization (OpenVINO)

### D8 · Deployment · Deliberate NPU / GPU / CPU placement with INT8 — Status: Built · Owner: @saliha · Updated: 2026-11-14 03:55
- **Decision:** Anomalib (small convolutional net, static 1×3×256×256) on the NPU with INT8 post-training quantisation; ACT and SmolVLA on the GPU; capture, state machine and serial on the CPU. Fallback chain NPU → GPU → CPU. Every optimisation claim gets a number: p50/p95 latency, model size, first vs cached compile time, bricks per minute.
- **Why:** the NPU is low power but needs static shapes (OpenVINO docs); the transformers are heavy and called often, so they get the GPU; control stays on the CPU for predictability. The rubric asks for appropriate use of all three.
- **Alternatives rejected:** everything on the GPU (wastes the NPU, no efficiency story).
- **Trade-off / risk:** operator support on the NPU is untested for our model; the GPU fallback is ready.
- **Built:** the export bakes a static 1×3×256×256 input into the IR (Anomalib leaves the batch dynamic by default, which the NPU cannot compile) and INT8 post-training quantisation calibrates at batch 1. The inspector compiles the IR itself on the first working device in NPU → GPU → CPU order with a compile cache, and records why each skipped device failed (Anomalib's `OpenVINOInferencer` has no fallback chain).
- **Evidence:** PaDiM IR size INT8 47 MB vs FP16 88 MB (file sizes). On Saliha's own laptop (not the Intel laptop, stand-in model): the compile cache cut GPU compile from ~10 s to ~1.5 s. Intel-laptop latency, NPU and energy table: TBD (Saturday 21:00 GPU slot, `bench/results.md`).
- **Pitch line:** "Each model runs on the chip it suits, and we have the numbers for every choice."

### D9 · Efficiency · Energy, thermal and demo-count measurements — Status: Built (energy/thermal harness, `bench/power.py`) / Planned (demo-count sweep) · Owner: @saliha @nate · Updated: 2026-11-14 01:30
- **Decision:** measure energy per inference and watts with Intel RAPL counters, peak temperature during the 20 trials, and success vs number of demonstrations (ACT trained on 18 / 36 / 54 episodes in parallel on Modal).
- **Why:** the Junction page scores inference latency, thermal headroom and power (20%), and Intel's challenge text asks "how few demonstrations are enough".
- **Alternatives rejected:** latency-only benchmarking.
- **Trade-off / risk:** RAPL and thermal readings exist only on the Intel Linux laptop; the sampler returns nothing elsewhere.
- **Evidence:** TBD (`bench/results.md`, success-vs-demos curve).
- **Pitch line:** "We report joules per brick and how few demos it takes, not just speed."

### D10 · Efficiency · One camera grab shared by the policy and the inspector — Status: Built · Owner: @harry · Updated: 2026-11-14 04:30
- **Decision:** each camera is read once per tick and the same frame goes to the policy and the inspector.
- **Why:** Intel lists "sharing cameras between policy and inspection" among the ideas it wants to see; it saves a USB stream and latency.
- **Alternatives rejected:** separate capture per consumer.
- **Trade-off / risk:** which physical camera is the RealSense is confirmed at the station.
- **Evidence:** built in `common/capture.py` (one grab thread per camera; consumers read the same frame and wait for one taken after the arm stopped); tested with mock cameras (two reads between frames return the same array, one grab). TBD (USB streams and latency saved, measured on the Intel laptop).
- **Pitch line:** "One camera feed, two jobs."

## D. Reasoning, voice and personality

### D11 · Reasoning · Nemotron 3.5 Super VL writes grounded live explanations — Status: Built (client) / Planned (grounding check, eval) · Owner: @saliha · Updated: 2026-11-14 03:55
- **Decision:** per brick, Nemotron (a vision-language model) gets the crop, the heatmap and the `DefectSignal` numbers and returns one short line in the current persona. We pass the numbers in so it cannot invent them, require JSON out, and reject a line that contradicts the label. It also answers "is the cowboy hat in view?" and, once, turns the kickoff rules text into a checked `rules.yaml`.
- **Why:** the NVIDIA track needs the model to do real work in the product, visibly; a vision-language model can describe where the defect is. Grounding in measured numbers keeps the explanation true.
- **Alternatives rejected:** fixed template sentences only (kept as the fallback); a text-only model (cannot see the brick).
- **Trade-off / risk:** the free NVIDIA Build tier is rate limited (about 40 requests per minute per key); requests start while the arm moves and are dropped if late.
- **Evidence so far (stand-in bricks, Saliha's laptop, NVIDIA Build API):** model `nvidia/nemotron-3.5-super-vl-120b-a12b`. Improvement 1: it is a reasoning model and spent the whole 80-token budget thinking (empty answer), so thinking is turned off for live speech; answers then take 1.7–2.7 s. Improvement 2: given only the score and thresholds, it read "below t_low" as bad and told a perfect brick to be set aside; passing the already-decided action and the band's meaning fixed it (4/4 correct on a small check, including an uncertain brick). Full 20-frame eval on real bricks: TBD (Saturday 22:00).
- **Pitch line:** "The model explains what it sees using our measured scores, so it can't make things up."

### D12 · Voice · Live reasoning through ElevenLabs, calm voice by default — Status: Planned · Owner: @harry · Updated: 2026-11-14 04:14
- **Decision:** explanations are spoken through the laptop speakers while the arm works. The robot talks through its thought process in a conversational way, like a person thinking aloud (what it sees, what the score means, what it will do and why), so the judges hear the reasoning behind each move. Default (calm) voice: a standard conversational ElevenLabs voice (`etWmxTqEKhIYyGKMpDcb`, chosen by @harry 2026-11-14 04:11, open to change); the cowboy persona uses David (D13). Live lines use a low-latency ElevenLabs model (`eleven_flash_v2_5`) with streaming and a 1.5 s timeout; exclamations and fallback phrases are pre-generated with the more expressive model and cached as audio. Stale lines are dropped so speech never lags the arm.
- **Why:** the ElevenLabs track rewards natural, emotionally expressive, fully autonomous audio; spoken reasoning makes the system's decisions legible to judges in real time.
- **Alternatives rejected:** a pre-recorded script (not live, not grounded); local text-to-speech only (kept as a stretch offline fallback). Calling the ElevenLabs REST API by hand with `requests` (we would write the audio streaming ourselves); we use the official `elevenlabs` Python SDK pinned to 2.78.0 instead (@harry, 2026-11-14 04:14).
- **Trade-off / risk:** network latency and quota; the cached clips cover it.
- **Evidence:** TBD (time from verdict to first audio).
- **Pitch line:** "You can hear it think, with the real numbers."

### D13 · Personality · Cowboy persona on obstacle or hat, instant in, gradual out — Status: Planned · Owner: @harry @saliha · Updated: 2026-11-14 04:11
- **Decision:** a persona state machine (CALM ↔ COWBOY). The cowboy voice is **David, deep southern cowboy**, from the ElevenLabs Voice Library (`0hh7H4ZVAtaGpm1VZyEN`, chosen by @harry 2026-11-14 03:45). Triggers: an obstacle (local RealSense depth: taller than a brick or not brick-shaped; the arm skips it, never picks it) or the cowboy hat (Nemotron on the top view, plus an H-key backup). Switching in is instant with a cached "Holy smokes!"; switching out waits until the trigger has cleared and one brick is done, then one half-way line, then calm.
- **Why:** it makes the robot memorable and shows the voice layer reacting to the physical world, without touching the control path. The obstacle trigger uses local depth so it works offline.
- **Alternatives rejected:** a persona picked by the operator only (not reactive).
- **Trade-off / risk:** the personality layer is cut before any task gate slips; a hat in the workspace must be allowed under the safety rules (asked at the mentor session).
- **Evidence:** TBD (switch time after a trigger).
- **Pitch line:** "The robot reacts to the world and changes its voice, then calms down."

## E. Data and cloud

### D14 · Streaming · Aiven Kafka for live events, PostgreSQL for the record — Status: Planned · Owner: @harry · Updated: 2026-11-14 01:30
- **Decision:** the telemetry thread produces every event to an Aiven for Apache Kafka topic; a consumer runs a drift check (recent perfect-brick scores creeping toward `t_low` → "lighting changed, rebaseline" alert, spoken) and writes rows to Aiven PostgreSQL for the trial report. If Kafka is not on our plan, PostgreSQL `LISTEN/NOTIFY` does the same job.
- **Why:** Aiven's rubric rewards meaningful use of its services; streaming lets other parts of the system react to the cell live, and the drift alarm changes what the robot does. It is not on the control path, so it does not add latency to the arm; honest framing: a cloud hop never makes the robot itself faster.
- **Alternatives rejected:** a plain log table only (low meaningful use).
- **Trade-off / risk:** offline → JSONL buffer, synced later.
- **Evidence:** TBD (events streamed, alert fired in the trial run).
- **Pitch line:** "Aiven carries the cell's live event stream and raises the alarm when lighting drifts."

### D15 · Training · Modal for training and logs only, no frontend — Status: Planned · Owner: @nate · Updated: 2026-11-14 01:30
- **Decision:** ACT and SmolVLA train on Modal GPUs from a reproducible script, with GPU type, time and cost logged. No dashboard or web app (the planned live dashboard was dropped).
- **Why:** Intel provides Modal GPUs for training; Modal's own page scores a deployed app (15%), but a frontend is out of scope for the team, so we accept losing those points rather than risk the main track.
- **Alternatives rejected:** a Modal-hosted dashboard (dropped); training on the laptop.
- **Trade-off / risk:** if Modal's prize needs a web app, we drop Modal.
- **Evidence:** TBD (`train/runs.md`).
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

### D19 · Safety · Every arm command is clipped to joint limits and a speed cap — Status: Built · Owner: @nate · Updated: 2026-11-14 05:15
- **Decision:** all motion, learned or scripted, goes through `robot/io.py`, which clips each command to the SO-101 driver's joint limits and moves no joint more than 5° per 30 Hz step; E turns torque off.
- **Why:** a policy can output any number; the printed safety rules and judges' reliability criterion need motion that is bounded no matter what the model does. Smooth motion is also part of the task-success score.
- **Alternatives rejected:** trusting the policy's output; limits inside each policy (easy to forget one).
- **Trade-off / risk:** the cap slows big moves; tuned on the station with the arm watched.
- **Evidence:** unit tests (`robot/tests/test_io.py`); on-arm value TBD.
- **Pitch line:** "Whatever the AI says, the arm stays inside safe limits."

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
