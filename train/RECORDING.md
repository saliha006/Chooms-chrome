# Recording protocol (page 1 of the plan)

Clean teleoperated demonstrations are 20% of the Junction page rubric (dataset and pipeline quality),
and an imitation policy is only as good as its demos (decisions.md D1). Same cameras, lamp and table
for recording and runtime.

## Setup
- **Pick zone:** taped 10 × 10 cm square. Starts wider than ~10 cm make SmolVLA "grasp at air".
- **Start grid:** 9 positions (3 × 3) inside the zone, marked with tape dots, plus a few **off-grid spots that are never
  recorded** (the F14 "new positions" test).
- **Inspection pose:** marked with tape on the table under the inspection camera; every ACT episode ends there.
- **Cameras:** the `/dev/v4l/by-id` paths in `config/cameras.yaml` (roles `top`, `inspect`, `wrist`). Never replug between recording and runtime.
  Record all three, with exactly these keys, in both datasets. SmolVLA maps them onto its pretrained slots in this order:
  `--cameras top,wrist,inspect` → `camera1`, `camera2`, `camera3` (Nate, 2026-11-14).
- **Joint unit: degrees**, the same as `robot/io.py`. On the first test episode, compare its `observation.state` with
  `robot.io.observe()` at the same pose: they must agree within a couple of degrees. If Studio can only record
  normalized (−100 to 100), stop and tell the team: the fallback is switching `robot/io.py` to normalized (decisions.md D29).
- **Leader arm** for teleoperation only; it is never driven by code.

## Before episode 1 (N6, decisions.md D32: clean demos beat more demos)
- Constant, neutral light from our own lamp; camera exposure and white balance fixed, not automatic; no window light.
- Static background: matte boards behind and beside the workspace, nothing moving in any frame. The leader arm and
  the operator's hands stay out of every camera's view.
- Cameras at 640 × 480 or more.
- Six practice runs first (not recorded), then a steady pace. A break at episode 27.
- Cadence check: the recorded frame rate matches 30 Hz (`lerobot-replay` on a test episode, or the audit below).

## ACT (pick and present): 54 episodes
- All 9 start positions × 6 episodes = 54, **recorded in rounds**: one episode per position per round, the same
  position order every round, 6 rounds. The F11 sweep trains on the first 18 / 36 / 54 episodes, which is then
  exactly 2 / 4 / 6 per position. F14 tests only the off-grid spots, which are never recorded (Nate, 2026-11-14).
- Start: arm at home, one brick at the start dot. End: brick held still at the inspection pose for ~1 s.
- About **8–10 s** per episode after the practice runs, ~10 s reset. Smooth, unhurried motion: the policy copies the speed.
- Mix good and defective bricks so the grasp doesn't depend on the marking.
- After each round: `python -m train.audit <dataset folder> --kind pick --cameras top,inspect,wrist`. It exits 1 on a
  failure; fix that before the next round.

## SmolVLA (place by instruction): 50 episodes
- 25 + 25, each **starting at the inspection pose** holding a brick.
- Task strings exactly, character for character (decisions.md D23: they carry the verdict):
  - `the brick is perfect, place it in the purple bowl`
  - `the brick is defective, place it in the orange bowl`
- Alternate purple and orange so neither bowl dominates; same bowl positions every time.
- After each round: `python -m train.audit <dataset folder> --kind place --tasks "the brick is perfect, place it in the
  purple bowl" "the brick is defective, place it in the orange bowl"`.

## Rejecting episodes
Reject on the spot, and log in `train/rejected.md`, any episode with: a dropped brick, a collision, a long hesitation,
a wrong bowl, the brick out of the inspection camera's view, or the operator's hand in a camera frame.
Re-take it at the same position before moving on, so the round order (and the sweep's first-N subsets) holds.

## Hugging Face datasets
- ACT: `{{hf_user}}/sortsense-pick` · SmolVLA: `{{hf_user}}/sortsense-place`
- Each gets a short dataset card: setup, episode counts, rejected count, task strings, cameras.

## Training (Modal)
```
modal run train/modal_train.py --policy act --dataset {{hf_user}}/sortsense-pick --steps 20000            # main ACT
modal run train/modal_train.py --dataset {{hf_user}}/sortsense-pick --steps 20000 --sweep                 # F11 curve
modal run train/modal_train.py --policy smolvla --dataset {{hf_user}}/sortsense-place --steps 10000 --cameras top,wrist,inspect
```
Back up every checkpoint before any OpenVINO export (Studio PR #1403 can delete it).
