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

# After ANY package install: anomalib pulls in opencv-python-headless, which can replace the cv2 module and
# leave mission control without a window ("The function is not implemented"). Put the window build back:
~/.local/bin/uv pip uninstall --python .venv opencv-python-headless
~/.local/bin/uv pip install --python .venv --reinstall opencv-python
.venv/bin/python -c "import cv2; print([l.strip() for l in cv2.getBuildInformation().splitlines() if 'GUI:' in l])"   # want QT or GTK, not NONE
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

## 1b. The box room (before anything is clicked or taught)

Waypoints, the clicked zone and every recording depend on where the arm sits relative to the plates after the
drive, so build the room first and never move it afterwards.
- Matte white card walls and floor, open top; lamp above, diffuse, no hard shadows.
- **Parked spot:** the place the base ends every drive, marked with tape and a **stop block** behind it. Everything
  below is clicked and taught with the base at the parked spot.
- **Overhead camera (`top`, the RealSense)** fixed above the room, seeing the plates, both bowls and the parked
  spot. **Inspection camera** mounted on the board, so it moves with the arm.
- Plates with the bricks, the purple (perfect) and orange (defective) bowls, all within reach from the parked spot.

## 2. Pick zone and bowls → `config/scene.yaml`

On the laptop's own screen (needs a display), base at the parked spot:
```bash
.venv/bin/python -m ui.click_regions          # 4 corners clockwise from top-left: zone, bowl_red (orange), bowl_blue (purple)
```
Enter saves once every region is clicked. Backspace undoes a click, R re-grabs the frame, Q quits without saving. Re-run for one region:
`python -m ui.click_regions zone`.

## 2b. Microphone (hat on / hat off by voice)

```bash
arecord -l                                      # which microphones there are; a USB mic shows as e.g. card 2
arecord -D default -f S16_LE -r 16000 -c 1 -d 4 /tmp/mic.wav && aplay /tmp/mic.wav   # say "I'm putting a cowboy hat on you"
```
Heard yourself? Put the device in `config/voices.yaml` `listen.device` (`default`, or e.g. `plughw:2,0`). Then run
a mock with the arm powered and moving nearby, and watch the log: `heard '…' -> hat_on` for your sentence, and no
`heard` lines from motor noise alone. Too many → raise `listen.threshold`; your sentence missed → lower it.
The **H** key toggles the hat if the room is too loud.

## 3. Arm → `config/robot.yaml`

Follower only (the leader is never driven). Already set on `main`: port = the follower board's by-id path
(serial `5AB0157419`; the leader is `5AE7045242`), calibration = `config/so101_follower.json` from Studio.
```bash
ls -l /dev/serial/by-id/       # both boards listed; the follower must be the one in robot.yaml
```

## 4. Waypoints → `config/waypoints.yaml`

Base at the parked spot. Torque goes off: **hold the arm** before pressing Enter at each pose.
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

## 7. The full box-room run

Base on its start side, bricks on the plates, laptop on a phone hotspot (live lines need a steady connection).
```bash
.venv/bin/python run.py --scripted pick,place       # with Nate's drive wired into cell.approach
```
Press **S**, say "I'm putting a cowboy hat on you" as it sets off, "I'm taking the hat off" mid-sort. Film it
(backup video v2). The beats and what to do if one fails: `docs/demo-script.md`.
