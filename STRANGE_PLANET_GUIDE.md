# Strange Planet: teaching guide (about 4 lessons)

Students drive a rover with Python. Every zone hides **one physics rule**
that nobody explains: ice, wind, crumbling ground, sunlight, portals. They
find it by running code, watching the replay and reading the log, then
write a program that works *with* it. It needs no Python beforehand: Zone 1
teaches `move()`, `for` and `while` from scratch.

The skill you're teaching is as much **experimenting** as coding:
*predict → run → watch → explain → change one thing → run again.*

## What students see

The planet fills the screen: the rover, its wheel tracks and each zone's
ground. A heads-up display shows the tick (plus battery and samples once they
matter), and a timeline under the map marks every slide, gust, portal and
fall with an icon, so students can jump straight to them. Code goes in on
the right and is sent with **Transmit** (F5 or Ctrl+Enter). Clicking a
command or sensor under the editor types it in, and a dot marks the sensors
that are new in the zone. The route along the top shows every site as a
waypoint.

## What keeps them coding

Every reward is for writing better code. Nothing is random, and nothing can be
lost.

- **Three stars per site**: 🛰 reach the beacon, a **challenge** that changes
  from site to site (see the table below), and ✂️ **compact code** (that many
  lines or fewer, which means loops and functions). Stars add up across runs,
  so one run can grab the crystal and another can be compact. Going back for
  the missing star *is* the practice. The line counter above the editor turns
  gold when the code is short enough.
- **The celebration**: the stars pop in one by one, with confetti for a
  perfect run or a class record.
- **Badges** for coding habits: first `for` loop, first `while`, first `if`,
  first function, using `print()`, **fixing a code error**, reaching a beacon
  after 5 tries that didn't (**Never Give Up**), class records, all crystals,
  zone masters. They're all listed, with how to earn them, in the garage.
- **📡 Anomalies**: the first time a zone's hidden rule shows up, the replay
  stops at that moment and asks *"What was it?"*, with a button to write a
  guess in the journal. It celebrates noticing without giving the rule away.
- **The garage** (★ at the top): stars unlock rover paint, toppers and
  trails. The last three paints unlock **for the whole class together** when
  the class star meter reaches 30, 90 and 180.
- **Class records**: the fewest ticks on each site, with the holder's name, in
  the corner of the map. Beating one is a big moment.
- **🕹 Scouting**: drive by hand with the arrow keys (or the on-screen
  buttons) to *feel* the strange physics. Nothing is saved, and only code opens
  the beacon. Students who are stuck on "what is the rule?" should scout.
- **Sound**: every event has a synthesized sound effect, quiet by default. 🔇
  at the top mutes it (each browser remembers). Headphones are best in a
  full room.

**Project `/planet/show`**: the class star meter with its shared unlocks,
everyone's rover in their own paint, and a live feed of first beacons,
records and three-star runs. It's a great thing to have on the board while
they work.

| Site | Challenge star | Compact star |
|---|---|---|
| 1A Touchdown | 💎 grab the crystal (a side pocket) | 5 lines |
| 1B Ridge Steps | 🧩 use a function you made with `def` | 6 lines |
| 1C Long Corridors | 🧱 never bump into rock | 9 lines |
| 2A First Frost | 💎 crystal at the end of the slide | 6 lines |
| 2B Glacier | 💎 crystal in a far corner (one extra slide) | 12 lines |
| 2C Frozen Lake | 🧱 never bump into rock | the student's shortest route + 1 |
| 3A Canyon Floor | ⚡ beacon in 14 ticks | 5 lines |
| 3B The Ledge | 💨 never get blown off course | 16 lines |
| 3C Gale Ridge | 💨 never get blown off course | 17 lines |
| 4A Thin Crust | ⚡ beacon in 18 ticks | 9 lines |
| 4B Three Pits | ⚡ beacon in 47 ticks | 12 lines |
| 4C Sample Field | 🧱 never bump into rock | 5 lines |
| 5A First Light | 🔋 finish with 20 battery | 4 lines |
| 5B Shadow Steps | ⚡ beacon in 80 ticks | 16 lines |
| 5C Moving Shadows | 🔋 finish with 30 battery | 5 lines |
| 6A The Pads | 💎 crystal behind a decoy pad | 7 lines |
| 6B Relay | ⚡ beacon in 13 ticks | 8 lines |
| 6C Portal Maze | 🧱 never bump into rock | the student's shortest route + 1 |
| Uncharted | 1, then 3, then all 5 planets in one run | |

`test_planet.py` checks that every star on every planet can be earned.

## Pre-class checklist (5 minutes)

- [ ] `python3 server.py`. Note the **admin key** in the banner.
- [ ] Students go to **`http://<ip>:8000/planet`** (the banner prints it).
- [ ] Put **`http://localhost:8000/planet/show`** on the projector.
- [ ] Open **`http://localhost:8000/planet/teacher`** on your laptop. It
      lists every student, the site they're on, **runs on that site**
      (amber at 8+, red at 15+: go and visit), hints opened, and their
      **field journal** guesses. It refreshes every 5 seconds.
- [ ] On a student laptop, join as "Test" and run the starter on 1A.
- [ ] Decide what to say when a student asks "what's the rule?":
      **"What did your last run show you?"** (see below).

## How a site works

Each zone has three sites, and each site has a job:

| Site | Job | What students feel |
|---|---|---|
| **A · Notice** | The rule appears, and their last program breaks in plain sight. | "Wait, why did it do *that*?" |
| **B · Use** | Only a program that uses the rule on purpose works. | "So I have to plan around it." |
| **C · Generalise** | The rule's details differ **per student** (a different lake, gust timing, sun, or portal wiring). | "My neighbour's code doesn't work on my planet." |

When a student opens a new site, **their code from the last site is
already loaded** and the map says *"Your last site's code is loaded. Will it
still work here?"*
That's deliberate: running the old program on the new ground is how they
notice each rule. Ask them to predict out loud before they press **Transmit**.

Copying is pointless on C sites, because the planet underneath is different.
Explaining *why* your code works is how to help a neighbour.

## The words to use

| Moment | Say this |
|---|---|
| "What's the rule?" | "What did your last run show you? Drag the timeline under the map back to the exact tick where it went wrong. **Show the moment** jumps there." |
| They have a guess | "Good. Write it in your **field journal** (📓), then design a run that would prove you wrong." |
| They're changing everything at once | "Change one thing. Transmit. What changed?" |
| They want numbers | "`print()` between commands. The telemetry shows each line with its tick. Pause the replay and that tick's lines light up." |
| The C site | "Your planet isn't the same as your neighbour's. What's the same about the rule, and what's different?" |

## Lesson plan

| Lesson | Zones | Discussion at the end |
|---|---|---|
| 1 | **Landing Site** (1A–1C) → **Ice Field** (2A–2C) | "When can't you count squares? What did you use instead?" |
| 2 | **Wind Canyon** (3A–3C) → **Crumbling Crust** (4A–4C) | "How did you find *when* the gusts came? What was your evidence?" |
| 3 | **Solar Valley** (5A–5C) → **Portal Fields** (6A–6C) | "Read us your journal entry for the portals. How many runs did it take?" |
| 4 | **Uncharted**: 5 random planets each run | "Which rule broke your program most often, and what fixed it?" |

Fast students will get ahead. That's fine, because each site opens only when
the one before is solved. Slow students aren't stuck behind a wall: open the
next site for one student from `/planet/teacher` (type the admin key once,
then **Unlock next**).

## Zone by zone

Each zone has three hints on the **mission control radio** (📻), from a nudge to partial
code. `/planet/teacher` shows how many each student opened.

### 1 · Landing Site: no strange rule
Teaches the basics so Zone 2's surprise has something normal to compare
against.
- **1A Touchdown**: commands in order. `move(3) turn_right() move(2) turn_left() move(5)`
- **1B Ridge Steps**: one step repeats 7 times, then one `move()`. *Find the repeat* → `for`.
- **1C Long Corridors** (per student): leg lengths differ, so counting breaks.
  `while not wall_ahead(): move()`, then turn, twice, then one more drive.

### 2 · Ice Field: one `move()` slides until something stops it
- **2A First Frost**: the counting program slides past the turn. The log
  says *"one move() slid 7 squares"*. Answer: take the ground
  route round the bottom: `turn_right() move(3) turn_left() move(4) turn_left() move()`.
- **2B Glacier**: the beacon is two squares away, behind a rock. It takes
  **six slides**, using rocks as brakes. *Plan backwards from the beacon.*
- **2C Frozen Lake** (per student, 4 lakes of 7–8 slides). Encourage one
  function per direction (`slide_up()` etc.) so the plan reads like a plan.

### 3 · Wind Canyon: every N ticks a gust pushes a *driving* rover one square east
A rover that `wait()`s holds on. Rock to the east shelters it.
- **3A Canyon Floor**: `move(12)` falls into a crater at tick 10. Gusts come
  every 5 ticks. Answer: `move(4) wait() move(4) wait() move(4)`.
- **3B The Ledge**: too many gusts to dodge by hand:
  ```python
  def step():
      if tick() % 5 == 4:
          wait()
      move()
  ```
- **3C Gale Ridge** (per student): gusts every **4, 6, 7 or 9** ticks. The 3B
  program (5) fails on everyone's ridge. *Find your number, put it in one
  variable:* `GUST = 7` and `tick() % GUST == GUST - 1`.

### 4 · Crumbling Crust: ground cracks when you leave it; stepping on a crack again = falling through
The beacon won't open until every sample is collected.
- **4A Thin Crust**: going into the pit and back out the same way falls.
  The pit is two wide: down one side, up the other.
- **4B Three Pits**: the same trick three times: a `pit()` function in a
  `for` loop.
- **4C Sample Field** (per student, 4 room sizes): following the edge comes
  back round to the start and falls. Treating cracks like rock makes the
  rover spiral in over every square:
  ```python
  while not at_goal():
      if wall_ahead() or cracked_ahead():
          turn_right()
      else:
          move()
  ```

### 5 · Solar Valley: driving and turning cost 1 battery; waiting is free; each tick in sunlight adds 2
- **5A First Light**: `move(29)` runs flat. Wait on the sunny squares first.
- **5B Shadow Steps**: charge on each sunny corner, just enough for the next
  stretch: `def charge_to(n): while battery() < n: wait()`.
- **5C Moving Shadows** (per student): a band of sunlight travels down the
  valley at a different speed on each planet. One charge stop is never enough. The neat answer
  rides with the light:
  ```python
  while not at_goal():
      if in_sun() and battery() < 90:
          wait()
      else:
          move()
  ```

### 6 · Portal Fields: pads teleport you to their partner
Some pads only send one way, and some send nowhere. The telemetry gives the
row and col of both pads, and pointing at any square shows its row and col.
- **6A The Pads**: one of three pads crosses the wall.
  `move(2) turn_right() move(2) turn_left() move(2) turn_left() move(2)`
- **6B Relay**: two portals in a chain. `move(3) turn_right() move(2) turn_left() move(3) turn_left() move(2)`
- **6C Portal Maze** (per student, 4 wirings, 2–3 trips each). This is a
  journal site: students should record each pad's destination, then write
  one function per trip.

### Uncharted: the finale
Every run lands on **5 new random planets**: mazes with ice, craters, wind
(a new sensor, `gust_in()`, says how many ticks until the next gust) and
sunlight. Every planet is checked before it's used: the program below reaches
its beacon. Scored on planets reached, then ticks.
```python
def blocked():
    return wall_ahead() or crater_ahead()

def step():
    if gust_in() == 1:
        wait()
    move()

while not at_goal():
    if in_sun() and battery() < 60:
        while battery() < 95:
            wait()
    if not wall_right():
        turn_right()
        if blocked():
            turn_left()
    if blocked():
        turn_left()
    else:
        step()
```
Leaving out the battery, crater or wind handling loses a large share of
planets (`test_planet.py` checks this), so every part earns its place.

## What's checked automatically

`python3 -m unittest test_planet` proves every claim above. For each site
the reference program clears every planet, the obvious program from before
fails, and on per-student sites one student's route fails on the other
students' planets.
