# Junction Platform submission: draft

Due **Sunday 09:00** (internal), official deadline 10:00. Fill every `TBD` from a measured result only
(`bench/results.md`, `docs/trials-slide.md`, the Aiven report). Delete a sentence rather than keep a claim that
didn't come true. Owners per section: Intel + Aiven + ElevenLabs = Harry, NVIDIA = Saliha, Modal = Nate.

**Claims we must not make:** a scripted placement as SmolVLA · any number before it is measured · "faster
because of the cloud" · that the robot detects things it was not tested on.

## Links

- Repo (MIT): https://github.com/saliha006/Chooms-chrome
- Video (≤ 2 min): TBD
- Dataset cards on the Hugging Face Hub: TBD (Nate)

## One-liner

A robot arm that sorts Duplo bricks into perfect and defective, explains every decision out loud, and runs
every model on the Intel Core Ultra laptop's NPU, GPU or CPU on purpose.

## Short description (about 100 words)

SortSense is a closed-loop defect-sorting cell. An SO-101 arm picks a brick with an ACT policy and holds it up
to an inspection camera. Anomalib, trained only on good bricks and running INT8 on the NPU, scores it perfect,
defective or uncertain; uncertain bricks get a second look, a wrist roll and a re-grasp before a decision. The
verdict becomes the language instruction for SmolVLA, which places the brick in the right bowl. Every stage
proves it worked before the next one starts. On top, the robot talks through its reasoning, and an obstacle or a
cowboy hat flips it into a cowboy persona until the moment passes.

## Intel x Ignite Next: Physical AI

**What it does.** Pick (ACT, Physical AI Studio's trainer) → inspect (Anomalib) → decide (two thresholds from
the score histograms, `config/rules.yaml`) → place (SmolVLA). A state machine on the CPU runs it with a deadline
per stage, a reason code for every failure, and a recovery chain for uncertain bricks: look again, roll the
wrist 90°, re-grasp. A failure sends the arm home, says why, and waits for a person.

**The four layers.** Perception: three cameras (one grab each, shared by the policies and the inspector), a zone
gate and a "brick or not" check on the top camera, Anomalib as the only defect detector. Reasoning: the
uncertainty band and the rules turn a score into an instruction that carries the verdict ("the brick is
defective, place it in the orange bowl"). Planning: the state machine (next brick, recovery, deadlines, grasp and
place checks). Manipulation: ACT picks, SmolVLA places, a scripted mover behind the same interface as insurance.

**Intel technology.** OpenVINO for every model. Placement (confirm on the Intel laptop once the NPU driver is in): Anomalib INT8 on the NPU, ACT and SmolVLA on the iGPU with a CPU
fallback; Physical AI Studio for recording and ACT training; the `physicalai` runtime. Device table (p50 / p95,
model size, compile time): TBD. Energy per inference and per brick, package power, temperature over the trials:
TBD.

**Results.** Detector AUROC on held-out real bricks: TBD (interval TBD). Trials: k of 20 sorted without a human
(95% CI TBD). Cycle time: TBD s per brick. Unseen start positions and a 3-brick pile: TBD. Which mode moved the
arm in each trial is logged; scripted runs are reported as scripted.

**Data and training.** Planned (update to the recorded counts): 54 ACT demonstrations (9 start positions × 6, recorded in rounds) and 25 + 25 SmolVLA
demonstrations, every episode audited by code before training (`train/audit.py`). Success vs number of demos
(18 / 36 / 54, trained in parallel on Modal): TBD.

## ElevenLabs (MLH)

The robot explains itself out loud. Every event and every failure reason has a line in two voices, a calm one
and a cowboy (David, deep southern cowboy, from the Voice Library), pre-generated with `eleven_multilingual_v2`
so the voice works offline and never waits on the network (19 calm + 20 cowboy clips). An obstacle in the pick
zone or the cowboy hat flips the robot into the cowboy persona at once ("Holy smokes!"); once the obstacle is
gone and one more brick is done it drifts back through a half-way line ("Right, partner... I mean, right.").
Playback runs on its own thread, so speech never delays the arm.

The robot also explains each verdict live, with that brick's own numbers: "That scores 0.41, over my 0.63
line, with a mark at the top left. Orange bowl." These lines are synthesised on the fly with `eleven_flash_v2_5`
(625–1953 ms per line on the venue Wi-Fi); a warm-up call opens the connection before the first brick, and a line
not back within 3 s falls back to the cached clip, so the voice keeps up even when the network doesn't. On real
runs, NVIDIA Nemotron's explanation of what it sees follows in the same voice. Time from verdict to first audio
on the demo laptop: TBD.

## Aiven

Every stage of every brick is one row in an event log (run, brick, state, label, score, device, latency,
outcome). The cell appends locally and never waits; a side thread ships the rows to **Aiven for PostgreSQL**,
catching up after an outage without duplicates. The database changes what the cell does: after each batch it is
asked for this run's perfect bricks, and when their scores creep towards the decision threshold the **lighting
drift alarm** fires: the robot says "the light may have changed, please rebaseline me" and the screen shows it.
The same table produces the trial report (`telemetry/report.sql`): success rate, help pauses by reason, latency
per stage and device. Kafka stream (`sortsense.events`): TBD (only if the service is created). Drift alarm on
real bricks: TBD.

## NVIDIA Nemotron (Saliha to write)

Required: model, what it does, why it matters, how we improved its outputs.
- Model: `nvidia/nemotron-3.5-super-vl-120b-a12b` via NVIDIA Build.
- What it does: TBD (Saliha). Advisory only: it explains the measured verdict and never changes it (D25).
- How we improved its outputs: TBD (Saliha: grounding in the measured score and thresholds, eval table).

## Modal (Nate to write)

- What: ACT and SmolVLA trained on Modal GPUs from `train/modal_train.py`; the demo-count sweep fans out in
  parallel. GPU type, time and cost: TBD (Nate). No frontend (we accept losing the deployed-app points).
