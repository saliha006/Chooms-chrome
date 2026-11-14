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
- **Leader arm** for teleoperation only; it is never driven by code.

## ACT (pick and present): 54 episodes
- 9 start positions × 6 episodes each = 54. `[🟠 Nate's call]` The brief also says to hold back 2 of the 9 grid
  positions for F14. Either record all 9 and test F14 only on off-grid spots (keeps 6 per position), or hold back 2
  and record ~8 per position on the other 7 (a harder, more honest F14 test).
- Start: arm at home, one brick at the start dot. End: brick held still at the inspection pose for ~1 s.
- About **12 s** per episode, **10 s** reset. Smooth, unhurried motion: the policy copies the speed.
- Mix good and defective bricks so the grasp doesn't depend on the marking.

## SmolVLA (place by instruction): 50 episodes
- 25 + 25, each **starting at the inspection pose** holding a brick.
- Task strings exactly, character for character:
  - `place the brick in the red bowl`
  - `place the brick in the blue bowl`
- Alternate red and blue so neither bowl dominates; same bowl positions every time.

## Rejecting episodes
Re-record and log in `train/rejected.md` any episode with: a dropped brick, a collision, a long hesitation,
a wrong bowl, the brick out of the inspection camera's view, or the operator's hand in a camera frame.
Delete it from the dataset before pushing.

## Hugging Face datasets
- ACT: `{{hf_user}}/sortsense-pick` · SmolVLA: `{{hf_user}}/sortsense-place`
- Each gets a short dataset card: setup, episode counts, rejected count, task strings, cameras.

## Training (Modal)
```
modal run train/modal_train.py --policy act --dataset {{hf_user}}/sortsense-pick --steps 20000            # main ACT
modal run train/modal_train.py --dataset {{hf_user}}/sortsense-pick --steps 20000 --sweep                 # F11 curve
modal run train/modal_train.py --policy smolvla --dataset {{hf_user}}/sortsense-place --steps 10000
```
Back up every checkpoint before any OpenVINO export (Studio PR #1403 can delete it).
