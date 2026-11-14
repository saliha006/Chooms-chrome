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
Playback runs on its own thread, so speech never delays the arm. Live lines streamed with `eleven_flash_v2_5`
from Nemotron's explanation: TBD (keep only if it works in the demo; then add the measured time from verdict to
first audio).

## Aiven

Every stage of every brick is one row in an event log (run, brick, state, label, score, device, latency,
outcome). The cell appends locally and never waits; a side thread ships the rows to **Aiven for PostgreSQL**,
catching up after an outage without duplicates. The database changes what the cell does: after each batch it is
asked for this run's perfect bricks, and when their scores creep towards the decision threshold the **lighting
drift alarm** fires: the robot says "the light may have changed, please rebaseline me" and the screen shows it.
The same table produces the trial report (`telemetry/report.sql`): success rate, help pauses by reason, latency
per stage and device. Kafka stream (`sortsense.events`): TBD (only if the service is created). Drift alarm on
real bricks: TBD.

## NVIDIA Nemotron

**Model.** Nemotron 3.5 Super VL (`nvidia/nemotron-3.5-super-vl-120b-a12b`) through NVIDIA Build's
OpenAI-compatible API.

**What it does.** After the detector decides, Nemotron gets the brick crop plus the measured facts (label,
anomaly score, both thresholds, defect box, the action already chosen) and writes one or two spoken sentences:
what it sees on the brick, what the score means against the thresholds, and where the brick goes. ElevenLabs speaks
the line while the arm places the brick. It explains the verdict and never changes it (decisions.md D25): Anomalib
decides, Nemotron makes the decision understandable to a person standing at the table.

**Why it matters.** A sorting robot that says *why* ("the score is 0.71, above my 0.63 limit, there's a mark
near the stud, orange bowl") is one an operator can trust and correct. The vision-language model links the
picture to the numbers, which a fixed template cannot do.

**How it stays out of the way.** The call runs on its own thread after the verdict, with a 4 s timeout; only the
newest request is kept, so a slow answer never talks over the next brick. If it is late or fails, the cached line
already played. The arm never waits for it.

**How we improved its outputs.**
1. *It thought instead of talking.* Super VL reasons by default and spent the whole 80-token budget thinking,
   returning no line. We turned thinking off (`enable_thinking: false`) and ask for JSON with one `line` field.
2. *It contradicted the verdict.* With only the score, it called a perfect brick defective. Passing in the decided
   action and what the threshold band means fixed it: 4 of 4 correct on stand-in bricks, 1.7–2.7 s per line.
3. *A guard on every line.* A line that names the wrong bowl or quotes a number we never gave it is thrown away
   and counted (`reasoner/live.py`). Live check on a stand-in image: 6 of 6 calls grounded, 1.9–2.7 s each.
4. *Measured, not eyeballed.* `python -m reasoner.eval` runs saved inspection crops through the model and reports
   answered, grounded, names the action, usable, p50 and p95 latency, once per prompt version on the same frames.
   Real-brick table: TBD (needs the real-brick crops).

## Modal (Nate to write)

- What: ACT and SmolVLA trained on Modal GPUs from `train/modal_train.py`; the demo-count sweep fans out in
  parallel. GPU type, time and cost: TBD (Nate). No frontend (we accept losing the deployed-app points).
