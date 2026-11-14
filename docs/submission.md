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

**Intel technology.** OpenVINO for every model, measured on the Intel laptop (Core Ultra X9 388H, OpenVINO
2026.4.1, NPU driver 1.38.0, mains power; `bench/results.md`). Every operator of the detector runs on the CPU, GPU
and NPU. Detector (PaDiM, INT8, 47 MB, half the FP16 size), p50 per inference: **GPU 1.00 ms, NPU 7.17 ms, CPU
8.91 ms**, against 17.27 ms in PyTorch on the CPU. Net energy per inference: **GPU 33 mJ, NPU 68 mJ, CPU 300 mJ**,
at about 11 W of package power on the NPU against 32–35 W on the GPU and CPU. Five minutes at full load: the NPU
holds its speed (0.96×), the GPU slows to 1.43× and the CPU to 1.06×. ACT (Studio's export with our three cameras)
compiles on the NPU in 2.3 s and runs in 8.9 ms per call (GPU 4.2 ms, CPU 65.7 ms). These numbers come from a
detector trained on stand-in synthetic bricks; the table is re-run on the real-brick model (TBD). Placement:
Anomalib INT8 on the NPU (low power, steady under load, frees the GPU), ACT and SmolVLA on the iGPU with a CPU
fallback; Physical AI Studio (part of Intel's Robotics AI Suite) for recording and ACT training; the
`physicalai` runtime. Every real run measures its own package energy, average power and peak temperature and logs
joules per brick (`bench/power.py`, an `ENERGY` row per run); energy per brick over the 20 trials: TBD.

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

## NVIDIA Nemotron

Required: model, what it does, why it matters, how we improved its outputs.
- Model: `nvidia/nemotron-3.5-super-vl-120b-a12b` via NVIDIA Build.
- What it does: after each brick is inspected, Nemotron gets the brick crop plus the measured numbers (verdict, anomaly score, the two thresholds, defect box) and says one or two short sentences out loud: what it sees, what the score means against our thresholds, and what the robot will do. A text-to-speech voice (ElevenLabs) speaks it. It is advisory only: Anomalib and the thresholds decide, Nemotron explains and never changes the verdict (D25).
- Why it matters: a sorting robot that says why it chose a bowl can be checked by the person watching. Because the explanation uses our measured scores, it is a true account of the decision, not a guess.
- How we improved its outputs:
  1. **Thinking off for live speech.** Nemotron Super VL reasons by default and spent its whole 80-token budget thinking (empty answer). With thinking switched off, answers take 1.9-2.7 s.
  2. **Grounding in the decision.** Given only a score and thresholds, it read "below t_low" as bad and told a perfect brick to be set aside. Passing the already-decided action and what each band means fixed it (4 of 4 correct on a small check, including an uncertain brick).
  3. **A checker after the model.** `reasoner/live.py` throws away any line that names the wrong bowl or quotes a number we did not give it. It keeps only the newest request, so a slow answer never speaks over the next brick, and a late or failed call falls back to our fixed template lines.
- Measured so far (stand-in image, NVIDIA Build API, 6 calls over perfect, defective, uncertain): 6 of 6 lines consistent with the verdict, 1.9-2.7 s. **Real bricks, the 20-frame evaluation and the spoken time from verdict to first audio: TBD.**

## Modal

- **What runs on Modal:** all training, nothing at demo time. ACT (the pick policy) trains with Intel's Physical AI
  Studio trainer and SmolVLA (the place policy) fine-tunes from `lerobot/smolvla_base` with LeRobot, each in its own
  pinned image on an A100, from one script (`train/modal_train.py`). Checkpoints land on a Modal Volume, and a Modal
  CPU job exports them to OpenVINO and checks them (`train/export.py`), because Studio's tooling does not run on our
  Windows laptops. Inference stays on the Intel laptop: the robot never waits on the network.
- **Why it helped:** jobs start on a deployed app and keep running when the laptop's connection drops, which killed
  two runs before we moved to it. The demo-count sweep (ACT on 18, 36 and 54 demonstrations) runs as three jobs in
  parallel, so the "how much data is enough" question costs one training time, not three. Every run's GPU, time and
  cost goes to `train/runs.md`.
- **Measured so far:** SmolVLA smoke run, 200 steps in 1.8 min (about $0.06). A failed ACT run (about 38 min, about
  $1.33) found a video-decoding crash in forked data-loader workers; we reproduced it on a Modal CPU container and fixed
  it the same day. The SmolVLA export on Modal matches LeRobot's own policy to 2.6e-6 on identical inputs.
- **Real runs:** GPU time and cost for ACT, SmolVLA and the sweep: TBD (Nate, from `train/runs.md`).
- No frontend: we chose not to build a web app, so we accept losing the deployed-app points.
