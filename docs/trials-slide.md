# Reliability slide (n = 20): draft for H8

Fill from the 20 logged trials (Saturday 23:00–01:00). The numbers and their 95% intervals come from Saliha's
report, which reads the local event log and needs no network (run it on the Intel laptop):

```bash
python -m bench.trials runs/events.jsonl --truth truth.csv
```

`truth.csv` (`run_id,brick_id,truth`, truth = perfect or defective; `run_id` may be `*`) is written by whoever
places the bricks, before each trial. `telemetry/report.sql` on the Aiven table gives the latency and reason-code
breakdowns. Mock runs are excluded by their `mock-` run id in both.

## Morning steps (rehearsed 2026-11-14 20:15 on a 20-brick mock log: the report ran first time)

1. Before each trial, the person placing bricks adds a line to `truth.csv` (`*` = every run):
   ```
   run_id,brick_id,truth
   *,1,perfect
   *,2,defective
   ```
2. After the 20 trials, on the Intel laptop:
   ```bash
   .venv/bin/python -m bench.trials runs/events.jsonl --truth truth.csv
   ```
   It prints the table below (sorted without a human, correct bowl, mistakes by name, cycle time), each with its
   95% interval. Paste it into the slide and `docs/submission.md`.

## The slide

**SortSense sorted k of 20 bricks without a human (95% CI lo–hi%).**

| | Result | Source (`report.sql`) |
|---|---|---|
| Sorted without help | k / 20 (95% CI) | `bench.trials` |
| Correct bowl | k / 20 against `truth.csv` (95% CI), mistakes by name | `bench.trials` |
| Why it asked for help | reason codes and counts | query 2 |
| Needed a second look | n bricks, all resolved / flagged | query 4 |
| Inspection latency (p50 / p95) and device | ms on the NPU | query 3, `INSPECT` row |
| Cycle time | s per brick (bricks per minute) | `bench.trials` |
| Mode | which policy or scripted mover ran each stage | run header in the log |

Say "k of 20 with a 95% interval of lo–hi%": twenty trials can't support a single precise percentage, and
judges trust a stated interval more than a bare one.

## 95% intervals for k of 20 (exact Clopper–Pearson)

| Successes | Rate | 95% interval |
|---|---|---|
| 20/20 | 100% | 83–100% |
| 19/20 | 95% | 75–100% |
| 18/20 | 90% | 68–99% |
| 17/20 | 85% | 62–97% |
| 16/20 | 80% | 56–94% |
| 15/20 | 75% | 51–91% |
| 14/20 | 70% | 46–88% |
| 13/20 | 65% | 41–85% |
| 12/20 | 60% | 36–81% |
| 11/20 | 55% | 32–77% |
| 10/20 | 50% | 27–73% |

## Open before the trials

- **Who writes `truth.csv`** during the trials (the person placing the bricks): agree with Nate before 23:00.
- Which bricks and positions: the F14 shifted / pile trials use the off-grid spots only (Nate, D20).
