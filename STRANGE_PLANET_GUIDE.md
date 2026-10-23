# Strange Planet: teaching guide (about 4 lessons)

Students drive a rover with Python. Every zone hides **one physics rule**
that nobody explains: ice, wind, crumbling ground, sunlight, portals. They
find it by running code, watching the replay and reading the log, then
write a program that works *with* it. It needs no Python beforehand: Zone 1
teaches commands, `for` and `while` from scratch.

**It is deliberately not the maze game.** The rover never turns: it drives
by compass on open ground (`north()`, `south()`, `east(3)`, `west()`), and
it senses in words (`look("east")` says `"rock"`, `"ice"`, `"crater"`…) and
in coordinates (`x()` and `y()`). Each site is a **mission**, not a maze
exit: collect the samples, reach the beacon, or measure something strange
and `report()` the number to mission control. A student who types maze-game
code (`move()`, `turn_left()`, `wall_ahead()`) gets a message saying what
to write here instead.

The skill you're teaching is as much **experimenting** as coding:
*predict → run → watch → explain → change one thing → run again.*

## What students see

The planet fills the screen: the rover, its wheel tracks and each zone's
ground, with a compass in the corner and the squares numbered along the top
(x) and down the side (y). Pointing at a square shows its x and y. A
heads-up display shows the tick (plus battery and samples once they
matter), and a timeline under the map marks every slide, gust, portal, fall
and report with an icon, so students can jump straight to them. Code goes in
on the right and is sent with **Transmit** (F5 or Ctrl+Enter). Clicking a
command or sensor under the editor types it in, and a dot marks the sensors
that are new in the zone. The route along the top shows every site as a
waypoint.

## What keeps them coding

Every reward is for writing better code. Nothing is random, and nothing can be
lost.

- **Three stars per site**: the **mission** (🧪 collect every sample,
  🛰 reach the beacon, or 📡 report the right number), a **challenge** that
  changes from site to site (see the table below), and ✂️ **compact code**
  (that many lines or fewer, which means loops and functions). Stars add up
  across runs, so one run can grab the crystal and another can be compact.
  Going back for the missing star *is* the practice. The line counter above
  the editor turns gold when the code is short enough.
- **📡 Field measurements**: the first site of most zones asks a question
  ("how many squares does one `east()` slide on the ice?"). Any way of
  finding the number completes the mission; working it out **in code**,
  like `report(x() - before)`, earns the 🔢 star. A wrong number ends the run
  with "mission control measured something different", so guessing is slow.
- **The celebration**: the stars pop in one by one, with confetti for a
  perfect run or a class record.
- **Badges** for coding habits: first `for` loop, first `while`, first `if`,
  first function, using `print()`, **fixing a code error**, completing a
  mission after 5 tries that didn't (**Never Give Up**), class records, all
  crystals, zone masters. They're all listed, with how to earn them, in the
  garage.
- **📡 Anomalies**: the first time a zone's hidden rule shows up, the replay
  stops at that moment and asks *"What was it?"*, with a button to write a
  guess in the journal. It celebrates noticing without giving the rule away.
- **The garage** (★ at the top): stars unlock rover paint, toppers and
  trails. The last three paints unlock **for the whole class together** when
  the class star meter reaches 30, 90 and 180.
- **Class records**: the fewest ticks on each site, with the holder's name, in
  the corner of the map. Beating one is a big moment. (Field measurements
  have no records: they take a tick or two.)
- **🕹 Scouting**: drive by hand with the arrow keys (or the on-screen
  N, E, S, W buttons) to *feel* the strange physics. Nothing is saved, and
  only code completes a mission. Students who are stuck on "what is the
  rule?" should scout.
- **Brute force is allowed, on purpose.** Every site (but Uncharted) can be
  done with a plain list of commands, so nobody is locked out. Scout a
  route by hand (up to 150 moves), then **📋 Use as code** turns it into code
  (`east()` three times becomes `east(3)`, a long wait becomes a `for` loop).
  That completes the mission; the ✂️ star is where loops, sensors and
  functions pay off, and after a win the card suggests one next step ("find
  a chunk that repeats…"). Uncharted, with new planets every run, is where
  brute force finally stops working.
- **Sound**: every event has a synthesized sound effect. It starts **off**
  (a room of laptop speakers is a lot, and sudden sounds are hard for some
  students); 🔇 at the top turns it on, and each browser remembers.
  Headphones are best in a full room.
- **Replay speed**: the **1×** button beside the timeline cycles 1×, 2×, 4×
  and ½× (each browser remembers). A rover stuck in place, bumping or
  waiting, fast-forwards on its own, so a loop that never ends doesn't
  take half a minute to watch.
- **Calm mode** (tick it on the **?** card): no shaking, confetti, flashing
  or bobbing. It's on by itself when the computer asks for reduced motion.
  Worth pointing out to students who find busy screens hard.
- **Bigger text** (also on the **?** card) makes the code and telemetry larger.
- **The editor helps**: commands, sensors and the student's own functions
  light up when they're spelt right (so `eats()` stays plain), faint
  guides show the indentation, and Ctrl+Z undoes anything. A code error shows
  over the map with a **Go to line** button, and that line turns coral.
- **Help without waiting for you**: after 3 runs in a row that miss the
  mission, the result offers **🕹 Try it by hand** and **📻 Get a hint**. On
  Uncharted, every run says what stopped the other planets ("2 fell in a
  crater · 1 ran flat"), so students know which rule to handle next.

**Project `/planet/show`**: the class star meter with its shared unlocks,
everyone's rover in their own paint (in name order, with no individual star
counts, so nobody is ranked in front of the class), and a live feed of first
missions, records and three-star runs. It's a great thing to have on the
board while they work.

| Site | Mission | Challenge star | Compact star |
|---|---|---|---|
| 1A Touchdown | 🧪 3 samples | 💎 grab the crystal (a detour) | 7 lines |
| 1B Crystal Steps | 🧪 8 samples | 🧩 use a function you made with `def` (and call it) | 3 lines |
| 1C Boulder Run | 🧪 a sample at every boulder | 🧱 never bump into rock | 5 lines |
| 2A First Frost | 📡 how far one slide goes | 🔢 work the number out in code | 3 lines |
| 2B Glacier | 🛰 beacon | 💎 crystal in a far corner (one extra slide) | 6 lines |
| 2C Frozen Lake | 🛰 beacon | 🧱 never bump into rock | the student's shortest route + 1 |
| 3A Canyon Floor | 📡 ticks between gusts | 🔢 work the number out in code | 3 lines |
| 3B The Ledge | 🛰 beacon | 💨 never get blown off course | 16 lines |
| 3C Gale Ridge | 🛰 beacon | 💨 never get blown off course | 17 lines |
| 4A Thin Crust | 🛰 beacon, after the sample | ⚡ done in 14 ticks | 5 lines |
| 4B Three Pits | 🛰 beacon, after 3 samples | 🧩 use a function you made | 8 lines |
| 4C Sample Field | 🧪 a sample on every row | 🧱 never bump into rock | 8 lines |
| 5A First Light | 📡 charge from one tick of sun | 🔢 work the number out in code | 4 lines |
| 5B Shadow Steps | 🛰 beacon | ⚡ done in 80 ticks | 12 lines |
| 5C Moving Shadows | 🛰 beacon | 🔋 finish with 30 battery | 5 lines |
| 6A The Pads | 🛰 beacon | 💎 crystal behind a decoy pad | 4 lines |
| 6B Relay | 🛰 beacon | ⚡ done in 8 ticks (a quicker pad) | 5 lines |
| 6C Portal Maze | 🛰 beacon | 🧱 never bump into rock | the student's shortest route + 1 |
| Uncharted | 🛰 beacon on 5 planets | 1, then 3, then all 5 planets in one run | |

`test_planet.py` checks that every star on every planet can be earned.

## Pre-class checklist (5 minutes)

- [ ] `python3 server.py`. Note the **admin key** in the banner.
- [ ] Students go to **`http://<ip>:8000/planet`** (the banner prints it).
- [ ] If they've done the maze game, say so out loud: **"This rover never
      turns. North is up."** The Landing Site (3 short sites) is where they
      learn compass driving and `look()`, so nobody skips it.
- [ ] Ask them to join with their **full name**: two students who type the
      same name share one rover and one set of stars.
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
| **A · Notice** | A 📡 field measurement: the rule shows up, and the mission is to find its number and `report()` it. (Crumbling Crust and the Portal Fields notice it on a normal mission instead.) | "Wait, why did it do *that*? How much?" |
| **B · Use** | Only a program that uses the rule on purpose works. | "So I have to plan around it." |
| **C · Generalise** | The rule's details differ **per student** (a different field, lake, gust timing, sun, or portal wiring). | "My neighbour's code doesn't work on my planet." |

When a student opens a new site, **their code from the last site is
already loaded** and the map says *"Your last site's code is loaded. Will it
still work here?"*
That's deliberate: running the old program on the new ground is how they
notice each rule. Ask them to predict out loud before they press **Transmit**.

Copying is pointless on C sites, because the planet underneath is different:
each C site has 8 versions, and a classmate's hand-counted route works on
yours only when you happen to share a version. Explaining *why* your code
works is how to help a neighbour.

## The words to use

| Moment | Say this |
|---|---|
| "What's the rule?" | "What did your last run show you? Drag the timeline under the map back to the exact tick where it went wrong. **Show the moment** jumps there." |
| They have a guess | "Good. Write it in your **field journal** (📓), then design a run that would prove you wrong." |
| A field measurement | "Can you make the *rover* measure it? Remember `x()` before, drive, then compare." |
| They're changing everything at once | "Change one thing. Transmit. What changed?" |
| They want numbers | "`print()` between commands. The telemetry shows each line with its tick. Pause the replay and that tick's lines light up." |
| They're turning | "Which way is the sample: north, south, east or west? The compass is in the corner." |
| The C site | "Your planet isn't the same as your neighbour's. What's the same about the rule, and what's different?" |

## Lesson plan

| Lesson | Zones | Discussion at the end |
|---|---|---|
| 1 | **Landing Site** (1A–1C) → **Ice Field** (2A–2C) | "How did you measure the slide? Who made the rover measure it?" |
| 2 | **Wind Canyon** (3A–3C) → **Crumbling Crust** (4A–4C) | "How did you find *when* the gusts came? What was your evidence?" |
| 3 | **Solar Valley** (5A–5C) → **Portal Fields** (6A–6C) | "Read us your journal entry for the portals. How many runs did it take?" |
| 4 | **Uncharted**: 5 random planets each run, steered by coordinates | "Which rule broke your program most often, and what fixed it?" |

Fast students will get ahead. That's fine, because each site opens only when
the one before is done. Slow students aren't stuck behind a wall: open the
next site for one student from `/planet/teacher` (type the admin key once,
then **Unlock next**).

## Zone by zone

Each zone has three hints on the **mission control radio** (📻), from a nudge to partial
code. `/planet/teacher` shows how many each student opened.

### 1 · Landing Site: no strange rule (learning to drive)
Normal ground, so Zone 2's surprise has something to compare against. It's
where students meet compass driving, samples and `look()`.
- **1A Touchdown**: collect three samples. `south(2) east() south() east(7) south() north(3) west()`
- **1B Crystal Steps**: eight samples on a diagonal. *Find the repeat* →
  ```python
  for i in range(8):
      east()
      south()
  ```
- **1C Boulder Run** (per student): a sample waits at each boulder, at
  distances that differ for everyone. Drive until the next square is rock:
  ```python
  for i in range(4):
      while look("east") != "rock":
          east()
      while look("south") != "rock":
          south()
  ```
  A route counted off the map works too, but at 8 lines it misses the ✂️ star.

### 2 · Ice Field: one `east()` slides until something stops it
New: `x()`, `y()` and `report()`.
- **2A First Frost** 📡: how many squares does one `east()` slide? (6.)
  `east()` then `report(6)` completes it; the 🔢 star wants
  `before = x()`, `east()`, `report(x() - before)`.
- **2B Glacier**: the beacon is two squares away, behind a rock. It takes
  **six slides**, using rocks as brakes: `north() east() south() east() south() west()`.
  *Plan backwards from the beacon.*
- **2C Frozen Lake** (per student, 8 lakes of 7–8 slides). One line per
  slide reads like a plan; ask students to say each slide's brake rock.

### 3 · Wind Canyon: every N ticks a gust pushes a *driving* rover one square east
New: `tick()`. A rover that `wait()`s holds on. Rock to the east shelters it.
- **3A Canyon Floor** 📡: how many ticks apart are the gusts? (5.)
  `south(12)` shows pushes at ticks 5 and 10. The 🔢 answer drives until
  it's pushed off its column, then reports the tick:
  ```python
  while x() == 2:
      south()
  report(tick())
  ```
- **3B The Ledge**: craters along a long ledge. Wait out each gust:
  ```python
  def guard():
      if tick() % 5 == 4:
          wait()

  def go_south(n):
      for i in range(n):
          guard()
          south()
  ```
  (and `go_east(n)` the same way), then `go_south(6) go_east(5) go_south(6) go_east(4) go_south(5)`.
- **3C Gale Ridge** (per student): gusts every **4, 6, 7 or 9** ticks, on one
  of two ridges. The 3B program (5) fails on everyone's ridge. *Find your
  number, put it in one variable:* `GUST = 7` and `tick() % GUST == GUST - 1`.

### 4 · Crumbling Crust: ground cracks when you leave it; driving onto a crack = falling through
New: `samples_left()`, and `look()` says `"crack"`. The beacon won't open
until every sample is collected.
- **4A Thin Crust**: going into the pit and back out the same way falls.
  The pit is two wide: down one side, up the other.
  `east(4) south(3) east() north(3) east(3)`
- **4B Three Pits**: the same trick three times:
  ```python
  def pit():
      south(3)
      east()
      north(3)

  for i in range(3):
      east(4)
      pit()
  east(2)
  ```
- **4C Sample Field** (per student, 8 fields): a sample somewhere on every
  row. Driving round the edge comes back to the start and falls. Sweeping
  like mowing a lawn never crosses its own tracks:
  ```python
  while samples_left() > 0:
      while look("east") != "rock":
          east()
      south()
      while look("west") != "rock":
          west()
      south()
  ```

### 5 · Solar Valley: driving costs 1 battery a square; waiting is free; each tick in sunlight adds 2
New: `battery()` and `in_sun()`.
- **5A First Light** 📡: how much does one tick of `wait()` in the sun add? (2.)
  The 🔢 answer: `east()`, `before = battery()`, `wait()`, `report(battery() - before)`.
- **5B Shadow Steps**: charge on each sunny corner, just enough for the next
  stretch:
  ```python
  def charge_to(n):
      while battery() < n:
          wait()

  east(12)
  charge_to(5)
  south(5)
  charge_to(16)
  west(16)
  charge_to(5)
  south(5)
  charge_to(20)
  east(20)
  ```
- **5C Moving Shadows** (per student): a band of sunlight travels down the
  valley at a different speed on each planet. One charge stop is never
  enough. The neat answer rides with the light:
  ```python
  while not at_beacon():
      if in_sun() and battery() < 90:
          wait()
      else:
          east()
  ```

### 6 · Portal Fields: pads teleport you to their partner
Some pads only send one way, and some send nowhere. The telemetry gives the
x and y of both pads, and pointing at any square shows its x and y.
`look()` says `"pad"`.
- **6A The Pads**: one of three pads crosses the wall.
  `east(2) south(2) north(2) east(2)`
- **6B Relay**: two portals in a chain. `east(3) south(2) east(2) north(2) east()`
  (the ⚡ star wants a quicker pad: 8 ticks).
- **6C Portal Maze** (per student, 8 wirings, 2–3 trips each). This is a
  journal site: students should record each pad's destination, then write
  one function per trip.

### Uncharted: the finale
Every run lands on **5 new random planets**, so a list of moves can't work:
the program has to sense and decide. New: `beacon_x()` and `beacon_y()`
(where the beacon is) and `gust_in()` (ticks until the next gust). Rock
ridges, crater lines, ice, wind and sunlight are all there, the lander
sits in sunshine with too little battery to cross, and craters lie round
the beacon. Every planet is checked before it's used: the program below
reaches its beacon. Scored on planets reached, then ticks.

The idea is **compare coordinates**: if `x()` is less than `beacon_x()`,
the beacon is to the east. Go that way if it's safe, otherwise try another.
```python
def safe(way):
    return look(way) != "rock" and look(way) != "crater"

def ready():
    if gust_in() == 1:
        wait()
    if in_sun() and battery() < 30:
        while battery() < 80:
            wait()

while not at_beacon():
    ready()
    if x() < beacon_x() and safe("east"):
        east()
    elif y() < beacon_y() and safe("south"):
        south()
    elif x() > beacon_x() and safe("west"):
        west()
    elif y() > beacon_y() and safe("north"):
        north()
    elif safe("south"):
        south()
    else:
        north()
```
Each idea students add earns more planets, so there's always a next step:

| The program does | Planets reached (about) |
|---|---|
| compare x and y, and drive that way | 1 in 8 |
| + only drive a way that's `safe()` | 1 in 3 |
| + go round when no good way is safe | 3 in 8 |
| + wait out the gusts | 1 in 2 |
| + charge in the sun | all of them |

The first star (1 planet) comes early; all five in one run needs every idea.
`test_planet.py` checks that leaving any part out loses planets.

**Discussion:** "Your rover ran flat by the lander. Why? What did it need to
check before it set off?"

## What's checked automatically

`python3 -m unittest test_planet` proves every claim above. For each site
the reference program clears every planet, the obvious program from before
fails, and on per-student sites one student's route fails on the other
students' planets. It also checks that the opening sites are open ground,
not corridors, and that the maze game's commands explain what to use instead.
