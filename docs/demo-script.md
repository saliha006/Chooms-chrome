# Demo script (2:00): draft for H8

Built on PRD §11. **Draft**: rehearse on the real table (21:00–23:00 Saturday) and fix timings then.
Backup video on a second screen by 22:00, cued to the same beats.

## Before the judges arrive

1. Arm at home (check by eye), lamp on, bowls and tape where they were taught.
2. Lighting or table changed since the last run → `make rebaseline` (under 2 minutes).
3. Bricks in the zone: **one perfect, one defective, one planted borderline**, in that pick order
   (the picker takes the most isolated brick first, so space them to set the order).
4. Base in its start spot, away from the table (rehearse with `python run.py --mock --drive 42`).
5. `make run` (or `python run.py --scripted pick,place` if a policy missed its gate; the screen says which).
5. Cowboy hat and one obstacle (a cup) within reach, out of camera view.
6. **Intel laptop on a phone hotspot, not the venue Wi-Fi:** on the venue Wi-Fi, ElevenLabs requests stalled for 6–12 s at times (17:46–18:07), so live lines fell back or were dropped. Check: `python run.py --mock --headless` logs "live line ready" for most lines.
7. One person on the keyboard (**S**, **H**, **E**), one talking.

## The two minutes

| Time | Who does what | On screen | Robot says (calm unless noted) |
|---|---|---|---|
| 0:00 | Talk: factory inspection is done by eye; we built a cell that does it and explains itself | Mission control, "Press S to start" | — |
| 0:05 | Press **S**. The base drives the arm to the table (arm too far to reach from the start) | `DRIVE` | Live: "The bricks are about 42 centimetres out of my reach, so I'm driving over to them." then "Made it: 41 centimetres in 6 seconds. I'm in position, let's start sorting." |
| 0:15 | Perfect brick | Feed, heatmap, `PERFECT`, score vs `t_low / t_high`, reasoning panel | "Okay, that one looks clean. Purple bowl." |
| 0:30 | Defective brick | Heatmap lights up the marker defect, `DEFECTIVE` | "Hmm, there's a mark on this one. Orange bowl." |
| 0:45 | Borderline brick | `UNCERTAIN`; the panel lists each step: look again → wrist roll → re-grasp | "I'm not sure about this one. Let me take another look." then the verdict line |
| 1:00 | Put the cup in the zone (or press **H** with the hat in view) | Obstacle noted in the log row; the arm skips it | Cowboy: "Holy smokes!", next verdict in the cowboy voice; obstacle out → after one brick: "Right, partner... I mean, right." |
| 1:20 | Talk over the architecture slide: four layers, NPU / GPU / CPU, Nemotron off the control path | Slide (README diagram) | — |
| 1:35 | Benchmark before → after, energy per brick | Slide from `bench/results.md` | — |
| 1:50 | Reliability: the n = 20 slide (`docs/trials-slide.md`), straight from the Aiven `events` table | Slide | — |
| 2:00 | Zone empty | `DANCE` | "That's the zone empty. Time for a little victory dance." |

## If a beat goes wrong

| What happens | Do this | Say this |
|---|---|---|
| The base stops short | Robot says "I couldn't drive all the way to the table"; push it into its dock, press **P** | "It knows when it hasn't arrived, and asks." |
| A grasp misses | Nothing: it retries once on its own | "It checks its own grip and tries again." |
| `NEED HELP` banner | Fix the cause, press **P** | "Every failure has a reason code; it goes home and asks." |
| The arm does something unsafe | **E** (torque off) | "E-stop: motors off, always one key away." |
| The borderline brick lands clean on the first look | Carry on; show the recovery in the backup video | "This one didn't need it; here's one that did." |
| Voice silent | Carry on; the panel shows the same reasoning | — |
| Anything else | Switch to the backup video at the same beat | — |

## Honest caveats to keep in mind

- The spoken lines are cached clips: they say the verdict, not the score. The score is on screen. A live line
  with the numbers (Nemotron → ElevenLabs) is an add-on; say it only if it is in and working.
- The obstacle trigger today is the top camera's "not brick-shaped" check. The depth-based "something tall"
  hold needs RealSense depth in capture (not wired yet).
- Say which mode moved the arm (the header on screen): never call a scripted placement SmolVLA.
- The drift alarm only fires after the real-brick evaluation has saved `good_mean`; don't promise it live.
