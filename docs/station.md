# Station bring-up: commands in order

Everything on the Intel laptop, in `~/Documents/Chooms-chrome` (`ssh intel@10.0.41.130`, or its own terminal).
One robot user at a time (PRD §10). Each step says how to tell it worked.

## 0. Once per laptop

```bash
# Charger in (it sleeps after 15 min idle on battery and drops off SSH).
gsettings set org.gnome.settings-daemon.plugins.power sleep-inactive-battery-timeout 0

# NPU user-space driver (kernel driver and firmware are already loaded).
cd ~/npu-driver && sudo apt install -y ./intel-fw-npu_*.deb ./intel-driver-compiler-npu_*.deb ./intel-level-zero-npu_*.deb
cd ~/Documents/Chooms-chrome
.venv/bin/python -c "import openvino as ov; print(ov.Core().available_devices)"   # want CPU, GPU, NPU (reboot if NPU is missing)

git pull origin main
.venv/bin/python -m pytest -q -m "not slow" common fallback narrator telemetry policies robot perception bench reasoner
.venv/bin/python run.py --mock --headless     # "5 bricks sorted"
```

## 1. Cameras → `config/cameras.yaml`

```bash
ls -l /dev/v4l/by-id/          # use the *-video-index0 entries; ignore HP_5MP_Camera (built-in)
v4l2-ctl --list-devices
lsusb | grep -i 8086           # 8086:0ad3 = the RealSense D415
```
Roles: RealSense → `top`, webcam → `inspect`, wrist cam → `wrist`. Never replug a camera after this:
recording and runtime use the same paths.

Nothing in `by-id` while cameras are plugged into the hub → the hub needs its own power, or plug the cameras
straight into the laptop.

## 2. Pick zone and bowls → `config/scene.yaml`

On the laptop's own screen (needs a display):
```bash
.venv/bin/python -m ui.click_regions          # 4 corners clockwise from top-left: zone, bowl_red (orange), bowl_blue (purple)
```
Enter saves once every region is clicked. Backspace undoes a click, R re-grabs the frame, Q quits without saving. Re-run for one region:
`python -m ui.click_regions zone`.

## 3. Arm → `config/robot.yaml`

Follower only (the leader is never driven). Power supply on, then USB-C from its board.
```bash
ls -l /dev/serial/by-id/       # put the full by-id path in robot.yaml `port:`
ls config/so101_follower.json  # calibration from Nate
```

## 4. Waypoints → `config/waypoints.yaml`

Torque goes off: **hold the arm** before pressing Enter at each pose.
```bash
.venv/bin/python -m fallback.teach home pick_above pick pick_drop inspect bowl_red bowl_blue
```
`bowl_red` = over the orange bowl, `bowl_blue` = over the purple bowl.

## 5. Detector

Saliha's real-brick capture, then `make rebaseline` (writes the model `config/models.yaml` points at).

## 6. The MVP gate

```bash
.venv/bin/python run.py --scripted pick,place
```
Press **S**. Five bricks, no human. **E** = e-stop (torque off), **P** pause, **Q** home and quit. Film it
(backup video v1). Problems → `runs/events.jsonl` has a reason code on every failure.

After a lighting or table change: `make rebaseline`. Before every run: check the home pose by eye.
