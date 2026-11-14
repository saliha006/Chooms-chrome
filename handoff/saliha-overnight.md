# Saliha overnight / unattended task list (hardware-free only)

Written 2026-11-14 ~07:40 Espoo. For a `/goal` or unattended session on Saliha's laptop. **Do exactly O1–O6, in this order: O4, O2, O3, O5, O1, O6
(Saliha's own tasks first; O1 last because it lives in Nate's folder), then stop.** Nothing here needs the Intel laptop or the arm; anything that would need them is out of scope.
Every decision below is already made by Saliha (the doc owner); do not re-open them. If something is genuinely
ambiguous, check the code (`Grep`) and do one targeted web search; if still unclear, skip that sub-item, log why in
`handoff/SALIHA.md`, and continue.

**Rules (CLAUDE.md):** branch `aiml-perception-saliha` (O1 is on `robotics-policies-nate`, see below); per feature:
code → `no-slop` → tests (`.venv/Scripts/python -m pytest <pkg> -q -p no:warnings`, Windows: `PYTHONUTF8=1`) →
commit as Saliha (no AI trailer) → `git fetch` + merge `origin/main` → re-test → push → fast-forward `main` if green →
`progress.md` entry with `[conflicts: ...]` → mark the brief task (`builder-briefs/builder-brief-saliha.md`, v2.5
block) done → `decisions.md` entry status → publish docs to `context`. **Always fetch before editing and merge before
pushing** (teammates push often). Say in one line in the chat what each step does.

## O1 · End-of-task dance (`robot/dance.py`, Nate's folder: approved by the doc owner, post a ⚠️ row to @nate)
- Runs once when the pick zone is empty and the gripper is empty, starting from the home pose.
- Motion (Saliha's spec): base (`shoulder_pan`) sways **±25°** left-right, **3 cycles**; on each side the head bows
  (`wrist_flex` **+10°**) and tilts to that side (`wrist_roll` **±10°**); about **6 s** total; then back to home.
- Use only `robot.io.move_to` (joint limits, the 5°/step speed cap and the e-stop check are already there); compute
  targets as home + offsets, clipped by `io`. `dance(home, cycles=3, sway_deg=25, nod_deg=10, tilt_deg=10, half_period_s=1.0) -> bool`.
- Refuse to dance (return False) if the gripper isn't empty (gripper reading > 5).
- Tests with `io.connect(mock=True)`: visits both sides, never exceeds limits, ends at home, stops on e-stop.
- Board row to @harry: add a `DANCE` step in `run.py` after the zone is empty (his file), plus a narrator line.

## O2 · S5 `perception/scene.py` + the "key" check (brick or not)
- Top-camera only, pure functions + `SceneLocator` with the same interface as `common.locate.CountLocator`
  (`next_brick() -> bool`) so Harry can swap it in; extra: `.target` (table cm), `.obstacles`, `tall_object(depth)`.
- Zone: 4 clicked image corners of the taped 10×10 cm square → `cv2.getPerspectiveTransform` to table cm.
- Blobs: HSV, saturation above a TUNE threshold (bricks are saturated, the table isn't), morphology, contours.
- **Key check = brick or not-brick, rule-based (no model):** footprint area in cm² within the Duplo range
  (2×2 ≈ 3.2×3.2 cm to 2×4 ≈ 3.2×6.4 cm, TUNE ±40%), `minAreaRect` aspect ≤ 2.5, solidity ≥ 0.8. Fails → obstacle.
- `next_brick()`: True if at least one brick is inside the zone; `.target` = the **most isolated** brick (largest
  distance to any other blob, bricks and obstacles).
- `tall_object(depth_mm, table_mm)`: True if any zone pixel is more than 40 mm (TUNE) above the table plane: Duplo is
  ~24 mm with studs. Feeds Harry's `hold` flag.
- `brick_in_bowl(before, after, bowl_mask)`: changed-pixel fraction in the bowl region > 2% (TUNE) after a place.
- Synthetic top-view test images generated in the tests (coloured rectangles = bricks, a grey disc = obstacle).
- Board row to @harry: swap `CountLocator` for `SceneLocator`, wire `tall_object` to `hold`, `brick_in_bowl` to place.

## O3 · S6 `perception/reason_trace.py`
- `ReasonTrace` dataclass: `brick_id, score, t_low, t_high, margin` (signed distance to the nearest threshold),
  `region` (bbox centre in a 3×3 grid of the inspection image: "top-left" … "bottom-right", None if no bbox),
  `steps` (list of (step, score)), `decision`, `reason`. `from_signal(signal, steps, decision)`, `note()` one-line
  string for the telemetry `note` column, `as_dict()`. No contract change.

## O4 · S1 honest detector evaluation (`perception/`)
- `capture.py`: add `--brick N` → files `b{N:02d}_{i:04d}.png` so every image knows its brick.
- **Raw scores:** train/export with `Padim(post_processor=PostProcessor(enable_normalization=False))` (signature
  verified in 2.7.0). Verify on synthetic data that exported `pred_score` is unclamped; if the export still clamps,
  keep normalisation and record that in decisions.md D5 note (fallback agreed).
- `perception/evaluate.py`: brick-level splits (good bricks → k=5 folds for **out-of-fold good scores**; defective
  bricks → dev half sets `t_high`, test half only reports); `t_low` = 99th percentile of OOF good scores; `t_high` =
  5th percentile of dev defectives; **pixel threshold** for the region = 99th percentile of good anomaly-map pixels
  (saved in `thresholds.yaml` as `pixel_threshold`, used by the inspector instead of `MAP_THRESHOLD`); report AUROC
  with a **bootstrap-by-brick 95% interval** (1,000 resamples, seed 0), false-alarm rate with a **Clopper-Pearson**
  upper bound, recall at `t_high` with an interval; writes `bench/detector_report.md`.
- Works with `perception.synth` data (add brick IDs to synth filenames). Tests on a tiny synthetic set (slow-marked).

## O5 · Bug fixes (from the critic)
- `perception/inspector.py`: don't set a global `CACHE_DIR` on the core; pass it per `compile_model` for CPU/GPU only
  (the NPU driver keeps its own cache). Use `pixel_threshold` from `thresholds.yaml` when present.
- `bench/benchmark.py`: glob any `model.xml` under `--exports` (anomalib and `physicalai` layouts); optional
  `--torch-ckpt` row for a PyTorch CPU baseline of the Anomalib model.
- `bench/power.py`: a 1 Hz background sampler so `max_c` is the true peak; `idle_baseline(seconds)` to report
  joules net of idle.

## O6 · Close out
- Update `decisions.md` (D5 note: raw scores result; D21/D22 reference for scene checks; a short entry for the dance
  and the brick-or-not key check), the Saliha brief v2.5 statuses, `progress.md`, vault Hub ▶ START HERE. Then stop.
