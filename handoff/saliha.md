# Saliha: agent handoff notes

## 2026-11-14 16:58 · session on the Intel laptop itself
- **Done:** NPU driver, groups, RAPL, Wi-Fi power save; CPU / GPU / NPU all run the detector; stand-in pipeline and first `bench/results.md`; `.venv-robot`; Studio native install at `~/work/physical-ai-studio`; `physicalai[so101]==0.4.0` in `.venv`; board rows to Harry and Nate.
- **In progress:** nothing half-coded. Stand-in artefacts are in `runs/standin/` (git-ignored).
- **Next step:** once the inspection camera is mounted and a brick is held at the inspection pose: `python -m perception.capture --out data/good --brick N --n 12 --cam /dev/v4l/by-id/<inspect>` per brick, `python -m perception.audit --root data` after each batch, then `python -m perception.evaluate --root data --model padim` and `--model patchcore` (S4), export, then `python -m bench.benchmark --exports <export dir> --idle-s 60 --torch-ckpt <ckpt>` with the charger in (S7).
- **Gotchas:** the laptop had no `.env`, no GitHub login and was on battery; install `physicalai` after `requirements.txt`, never in the same resolve; `sudo chmod a+r /sys/class/powercap/intel-rapl*/energy_uj` again after a reboot; the clock here is right (another session stamped an entry 17:05 when it was about 16:45).
- **Open call (Saliha):** detector on the NPU or the GPU (numbers in the brief's S7 row and decisions.md D24).

## 2026-11-14 17:24 · station session, part 2
- **Done:** 5-minute thermal run (`bench/sustained.py`), ACT-on-NPU probe (`bench/act_npu_probe.py`, passes), mains device table, all in `bench/results.md`; `--system` on `reasoner.evaluate` and `cases.csv` from `perception.evaluate`; merged teammates' main (270 tests) and context. RealSense = `top`, webcam = `inspect` filled in `config/cameras.yaml` locally only (Harry's file). Studio in tmux `studio`.
- **Not pushed:** the laptop's `main` and a prepared `context` commit wait on `gh auth login`.
- **Next:** confirm which arm is on `ttyACM0`; wrist camera USB; calibration in Studio; teach the inspection pose; S3 capture.
