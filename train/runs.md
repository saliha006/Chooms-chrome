# Modal training runs

| When | Job | Policy | Dataset | Episodes | Steps | GPU | Wall time (min) | Cost |
|---|---|---|---|---|---|---|---|---|
| 2026-11-14 03:59 UTC | smolvla-allep-200st-1114-035659 | smolvla | eruedas/so101_3cams_pickplace-red-lego_real | all | 200 | A100 | 1.8 | ≈ $0.06 (A100 $0.000583/s × wall time) |

## Notes
- **smolvla-allep-200st-1114-035659** (PRD v2.5 N1, LeRobot 0.7.0): AV1 video decoded fine. Cameras `top,gripper,left` → `camera1,camera2,camera3` (`--cameras`). 200 steps at about 5 steps/s, loss 0.287 at step 200; data loading 0.07 s per step on Modal's default CPU, so training was not CPU-bound. Checkpoint: `checkpoints/000200/pretrained_model`. Export to OpenVINO: not yet tried.
- Earlier attempts on `lerobot/svla_so100_pickplace` (03:35–03:42 UTC) stopped before training: missing `lerobot[training]` extra, then camera names (`top`/`wrist` vs `smolvla_base`'s `camera1..3`); both fixed.
