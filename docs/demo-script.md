# Demo script (2:00): the box room

Built on PRD §0 and §11 (box-room demo, 2026-11-14). **Draft:** set the timings at the first full rehearsal.
Backup video on a second screen, cued to the same beats. If the room or the drive is not ready, use the
table-top fallback at the end of this page.

The story: a robot that sees, decides and explains itself. It notices the bricks are out of reach, drives over,
puts on a cowboy persona when you hand it a hat, and sorts every brick with anomaly detection, saying why as it goes.

## Before the judges arrive

1. **Room:** matte white walls and floor, open top, lamp on and not moved since `make rebaseline`.
2. **Robot** on its start side; **plates with the bricks** and the **purple (perfect) and orange (defective)
   bowls** on the far side, within reach of the parked spot (stop block in place).
3. **Plates must be white** (or the bricks sit loose on the white card): the zone check finds objects by colour,
   so a coloured plate reads as one big obstacle and nothing gets picked (critic, 01:20).
   **Bricks on the plates:** one perfect, one defective, one planted borderline (a faint mark), spaced so the
   picker takes them in that order (it picks the most isolated brick first). Bricks numbered underneath; the
   trial operator has `truth.csv` ready.
4. Lighting or table changed since the last run → `make rebaseline` (under 2 minutes).
5. **Intel laptop on a phone hotspot, not the venue Wi-Fi.** On the venue Wi-Fi, ElevenLabs stalled for 6–12 s
   at times; on a good connection live lines arrive in 0.5–1.6 s. Check with a mock run: `python run.py --mock
   --drive 42` should log "live line ready" for most lines.
6. **Microphone** plugged in and tested (`docs/station.md` step 2b); speak from where you will stand.
7. Cowboy hat and one unfamiliar object (a mug) within reach, out of camera view.
8. `python run.py --base` (learned policies) or `python run.py --scripted pick,place --base` if a policy missed its
   gate. If the drive failed its 05:40 go/no-go, run the same without `--base`, starting from the dock. The screen header says
   which mode moves the arm; say the same out loud.
9. One person on the keyboard (**S**, **H**, **E**), one talking and handing over the hat.

## The two minutes

| Time | Who does what | On screen | Robot says (live lines use the real numbers) |
|---|---|---|---|
| 0:00 | Talk: factory inspection is done by eye; this robot sees, decides and explains. Ask **"Hey Pix, who are you?"** | Mission control, "Press S to start" | "I'm Pix. I spot defects in bricks, sort them into the right bowl and tell you why, and I'm partial to a cowboy hat." |
| 0:10 | Press **S** | `DRIVE`, subtitles under the feed | "The bricks are about 80 centimetres out of my reach, so I'm driving over to them." |
| 0:15 | As it sets off, say **"Hey Pix, I'm putting a cowboy hat on you"** and put it on | Subtitle turns amber | "Well I'll be, a cowboy hat! Yeehaw, partner. Let's ride." |
| 0:20 | The arm scrapes the base across the floor | `DRIVE` | Cowboy: "Whoa there. 80 centimetres in 12 seconds. In position, let's get sortin'." |
| 0:35 | First brick (perfect) | Feed, heatmap, `PERFECT`, score vs `t_low / t_high`, reasoning panel | "First critter of the day…" then "Scorin' 0.12, well under my 0.20 line. Clean as a whistle, partner. Purple bowl." |
| 0:50 | Defective brick | Heatmap lights up the marker, `DEFECTIVE` | Tally: "1 down, partner: 1 clean, 0 busted. Next one." then "Whoa, 0.41, past my 0.33 line, got a mark at the top left. Orange bowl it is." |
| 1:05 | Say **"Hey Pix, I'm taking the hat off"** and take it off | Subtitle back to white | "Ohhh, I'm no longer a cowboy… Ahem. Back to business." |
| 1:10 | Borderline brick | `UNCERTAIN`; the panel lists look again → wrist roll → re-grasp | "Hmm, 0.27. That's between my two lines…" then "Still 0.27, right between my lines. Rolling it ninety degrees for a better look." then the verdict |
| 1:20 | Ask **"Hey Pix, why that bowl?"** (or "what do you see now?") | Subtitles | "Because the last brick scored 0.41, over my 0.33 line, with a mark at the top left. That's why it went in the orange bowl." |
| 1:25 | Put the mug on a plate | Obstacle noted; the arm skips it | "Holy smokes!" then, if the naming model is in: "…there's a coffee mug in my zone! That ain't no brick, so I'm leavin' it be." |
| 1:35 | Talk over the architecture slide: four layers, NPU / GPU / CPU; speech and Nemotron off the control path | Slide (README diagram) | — |
| 1:45 | Benchmark and reliability: device table, energy per brick, the n = 20 slide | Slides (`bench/results.md`, `docs/trials-slide.md`) | — |
| 1:55 | Zone empty | `DANCE` | "That's the last one. 3 bricks sorted: 2 perfect, 1 defective, and 1 needed a second look." then the dance |

## If a beat goes wrong

| What happens | Do this | Say this |
|---|---|---|
| It doesn't hear "Hey Pix, …" | Say it again closer to the mic; for the hat press **H** | "It also has a button, for noisy rooms." |
| The base stops short | It says "I couldn't drive all the way to the table"; push it to the parked spot, press **P** | "It knows when it hasn't arrived, and asks." |
| A grasp misses | Nothing: it retries once on its own | "It checks its own grip and tries again." |
| `NEED HELP` banner | Fix the cause, press **P** | "Every failure has a reason code; it goes home and asks." |
| The arm does something unsafe | **E** (torque off) | "E-stop: motors off, always one key away." |
| The borderline brick lands clean on the first look | Carry on; show the recovery in the backup video | "This one didn't need it; here's one that did." |
| Live lines fall back to short cached ones | Carry on: the cached lines say the same verdicts, the numbers stay on screen | — |
| Voice silent | Carry on; the subtitles and the panel show the same reasoning | — |
| Anything else | Switch to the backup video at the same beat | — |

## Say only what is true on the day

- Which mode moved the arm (the header on screen): never call a scripted placement SmolVLA.
- The object naming line plays only once Saliha's naming model is wired in (`Cell.namer`); until then it is just
  "Holy smokes!".
- The drift alarm fires only after the real-brick evaluation has saved `good_mean`; don't promise it live.
- The depth-based "something tall" hold is not wired yet: obstacles are found by shape and colour on the top
  camera.

## Fallback: table-top demo (if the room or the drive is not ready)

Same as above without the drive beat: the bricks start in the taped pick zone on the table, the robot starts at
home beside them. Keep the hat beat (by voice, or **H**) and the sorting, borderline, mug and summary beats. Run
without `--drive` and without a `cell.approach`, so no `DRIVE` stage runs.
