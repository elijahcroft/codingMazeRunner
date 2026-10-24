# Strange Planet: teaching guide (about 6 lessons)

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
  the editor turns gold when the code is short enough. Where ✂️ needs a loop,
  `def` or sensor, it leaves up to 2 spare lines over the shortest program,
  but a route counted out by hand still misses it. A student who comes back to
  a completed site, or finishes a run without all three stars, gets a 💡 hint
  for each missing star: the idea that earns it, not the code, and for ✂️ how
  many lines to cut.
- **📡 Field measurements**: the first site of most zones asks a question
  ("how many squares does one `east()` slide on the ice?"). Any way of
  finding the number completes the mission; working it out **in code**,
  like `report(x() - before)`, earns the 🔢 star. A wrong number ends the run
  with "mission control measured something different", so guessing is slow.
  These sites **coach step by step**. Opening one says how to read the
  measurement: x along the top of the map (ice), the battery gauge (sun),
  and on Wind Canyon what a **tick** is, before the rover is ever pushed.
  Each wrong number then gets a tip that goes one step further: first where
  to look, then how to work it out (with made-up numbers), and on the third
  miss the code that measures it. A run with no `report()` gets its own tip
  the first time. Each wind push has its own telemetry line, with the tick
  it came on.
- **The celebration**: the stars pop in one by one, with confetti for a
  perfect run or a class record.
- **Badges** for coding habits: first `for` loop, first `while`, first `if`,
  first function, using `print()`, **fixing a code error**, completing a
  mission after 5 tries that didn't (**Never Give Up**), class records, all
  crystals, zone masters. They're all listed, with how to earn them, in the
  garage.
- **🧰 Functions**: a student who writes a good `def` can save it and add
  it to their code on any later site with one click. It goes at the top of
  the program, in plain sight, and counts toward the ✂️ line limit like any
  other code. Up to 12 saved functions each; saving one with the same name
  again updates it.
- **The garage** (★ at the top): stars unlock rover paint (Galaxy, Lava,
  Pizza, RGB Gamer...), toppers (party hat, cat ears, wizard hat, shark
  fin, pumpkin...), trails (hearts, paw prints, slime, pixel blocks...) and
  a **map look** that redraws every zone (Moon, Snow Day, Candy Land,
  Volcano, Deep Space). Every map look keeps rock darker than the ground, or
  outlined in a bright colour, so the map stays readable. Personal unlocks
  keep coming all the way to 150 ★ (Ocean, Chrome and Hologram paints,
  headphones, a halo and a rocket, music-note and star-dust trails, Jungle
  and Cloud Kingdom), so the hard zones still pay out. Some unlock **for the
  whole class together** on the class star meter: paints at 30, 90, 180 and
  300 ★, Starry Night at 600, a Fireworks trail at 1000, a UFO at 1600 and
  Legendary paint at 2400. When the class crosses one, the projector shows a
  big **🎉 Class unlock!** card, and every student gets a toast the next time
  their page loads or they transmit.
- **Ranks**: the ★ button at the top shows a rank icon and a thin bar to the
  next one: Cadet, Rookie Pilot (10 ★), Pilot (25), Navigator (45), Explorer
  (70), Pathfinder (95), Commander (120), Star Captain (145) and Legend
  (every star). Ranking up says so on the celebration card with a fanfare.
  Ranks only show on the student's own screen, never on the projector.
- **Little wins in a run**: clearing a site on its first transmit says
  **🎯 First try!** (5 of those earn the 🎯 Sharpshooter badge). Samples,
  keys and flags picked up close together make a combo: each pick-up sounds
  a step higher and "×2", "×3" floats up over the rover. Unloading at home
  goes ka-ching with "+3 📦". New stars fly from the card into the ★ counter.
  In calm mode none of it moves: the words still appear, without motion.
- **📋 Today's missions**: three small goals a day, the same for the whole
  class, behind the 📋 chip at the end of the goals row. One is progress
  (earn 3 new stars, complete 2 different sites, or a first try), two are
  ideas (a mission with a `while` loop, with `print()`, with your own `def`,
  fixing an error...). Every one but a first try can be done on a site
  already solved, so a student who is stuck still has something to aim for.
  Each one done is a toast; all three is a 🏆 mission day (the first earns
  the Mission Day badge, three unlock the Gold medal topper). They reset at
  midnight on your laptop's clock.
- **Victory dances**: a fifth garage slot picks what the rover does at the
  beacon: Hop & spin, Happy wiggle (16 ★), Moonwalk (40 ★), Firework
  (75 ★), Backflip (the Triple Star badge), Zoomies (the Never Give Up
  badge, so sticking with a hard site pays off) and Disco spin (a mission
  day). The garage preview shows the dance every few seconds.
- **Wear a badge**: pressing an earned badge in the garage puts its icon
  next to the student's name on the class screen. One at a time; pressing
  it again takes it off. It shows something they did, not a score.
- **Zone cleared**: the last site of a zone gets its own card ("🪂 Landing
  Site cleared!") with a look at the next zone, and the rover cheers ("Beep
  boop! Nailed it!") at every beacon before the card.
- **🎁 Mystery gifts**: one site in each zone has a wrapped gift on the map
  (1A, 2B, 3B, 4C, 5B, 6A, 7B, 8B). A transmitted run that drives over it
  finds a garage item you can't get any other way: Grass Block, Diamond and
  TNT paints, a propeller cap, a pixel sword, a fire trail, and the Neon
  Grid and Blocky World map looks. The mission doesn't have to be finished,
  so a student can write a short program just to grab the gift. Scouting
  by hand drives past it without opening it. On 4C and 7B, where each
  student has their own planet, the gift is a short detour from the route
  on that planet. On 3B, 5B and some 4C planets it's on the way. A small 🎁
  on the route bar marks open sites that still hide one. The garage counts
  them ("3 of 8 found"), and finding all 8 earns the 🎁 **Treasure Hunter**
  badge. **🎲 Surprise me** in the garage picks a random look from
  everything a student has unlocked.
- **The rover talks**: each `print()` shows in a speech bubble over the
  rover during the replay, at the tick it happened, so printing a sensor
  shows *where* it read that value. Clicking the rover makes it beep,
  wiggle and say hello. At a beacon it does a little hop and spin. Calm
  mode keeps it still.
- **Class records**: the fewest ticks on each site, with the holder's name, in
  the corner of the map. Beating one is a big moment. (Field measurements
  have no records: they take a tick or two.)
- **🕹 Scouting**: drive by hand with the arrow keys (or the on-screen
  N, E, S, W buttons) to *feel* the strange physics. Nothing is saved, and
  only code completes a mission. Students who are stuck on "what is the
  rule?" should scout. A scout that falls or runs flat gets the same
  what-happened and 👉 next-step line as a transmitted run. Scouting has no
  jump button, so on jump sites it says "Scouting can't jump, but code can"
  and where to jump from.
- **Brute force is allowed, on purpose.** Every site (but Uncharted) can be
  done with a plain list of commands, so nobody is locked out. Scout a
  route by hand (up to 150 moves), then **📋 Use as code** turns it into code
  with **a few words left for the student to finish**: one to three, never
  all of them, cut to their first letter with one `_` per missing letter
  (`for i in r____(2):`, `e___(3)`). `east()` three times becomes
  `east(3)`, a long wait becomes a `for` loop, and a chunk of the route that
  repeats becomes a `for` loop too; `range` is the first word to go, then
  the commands, then `for`. Transmit won't send code with an unfinished
  word in it, and says what to do. That completes the mission; the ✂️ star is
  where loops, sensors and functions pay off, and after a win the card
  suggests one next step ("find a chunk that repeats…"). On Signal Plains
  (7B, 7C) a list of commands still reaches the beacon, but the 🌍 star
  only goes to code that reaches it on every classmate's plain too (8C
  does the same with fields). On Uncharted one program has to reach five
  planets, which is where brute force finally stops working.
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

**Project `/planet/show`**: the class star meter with its shared unlocks
(it shows one stage at a time, from the last goal reached to the next two,
so it visibly fills during a lesson),
a card for every student like Python Quest's big screen (their rover in its
garage paint and topper, their site, its map
with their rover where the last run left it, and the code in their editor as
they type), in name order with no individual star counts, so nobody is
ranked in front of the class, and a live feed of first missions, records and
three-star runs. It's a great thing to have on the
board while they work.

| Site | Mission | Challenge star | Compact star |
|---|---|---|---|
| 1A Touchdown | 🧪 3 samples | 💎 grab the crystal (a detour) | 7 lines |
| 1B Crystal Steps | 🧪 8 samples | 🧩 use a function you made with `def` (and call it) | 3 lines |
| 1C Rock Run | 🧪 a sample in front of every rock | 🧱 never bump into rock | 7 lines |
| 2A First Frost | 📡 how far one slide goes | 🔢 work the number out in code | 3 lines |
| 2B Glacier | 🛰 beacon | 💎 crystal in a far corner (one extra slide) | 6 lines |
| 2C Frozen Lake | 🛰 beacon | 🧱 never bump into rock | the student's shortest route + 1 |
| 3A Canyon Floor | 📡 ticks between gusts | 🔢 work the number out in code | 3 lines |
| 3B The Ledge | 🛰 beacon | 💨 never get blown off course | 16 lines |
| 3C Gale Ridge | 🛰 beacon | 💨 never get blown off course | 17 lines |
| 4A Thin Crust | 🛰 beacon, after the sample | ⚡ done in 14 ticks | 5 lines |
| 4B Three Pits | 🛰 beacon, after 3 samples | 🧩 use a function you made | 10 lines |
| 4C Sample Field | 🧪 a sample on every row | 🧱 never bump into rock | 9 lines |
| 5A First Light | 📡 charge from one tick of sun | 🔢 work the number out in code | 4 lines |
| 5B Shadow Steps | 🛰 beacon | ⚡ done in 80 ticks | 14 lines |
| 5C Moving Shadows | 🛰 beacon | 🔋 finish with 30 battery | 7 lines |
| 6A The Pads | 🛰 beacon | 💎 crystal behind a decoy pad | 4 lines |
| 6B Relay | 🛰 beacon | ⚡ done in 8 ticks (a quicker pad) | 5 lines |
| 6C Portal Maze | 🛰 beacon | 🧱 never bump into rock | the student's shortest route + 1 |
| 7A Homing Signal | 📡 how far east the beacon is | 🔢 work the number out in code | 2 lines |
| 7B Open Plain | 🛰 beacon | 🌍 the same code works on all 8 plains | 10 lines |
| 7C Rocky Plain | 🛰 beacon | 🌍 the same code works on all 8 plains | 17 lines |
| 8A The Trench | 🛰 beacon | ⚡ done in 4 ticks (jump all the way) | 3 lines |
| 8B Stepping Stones | 🛰 beacon | 🧩 use a function you made | 4 lines |
| 8C Crater Field | 🛰 beacon | 🌍 the same code works on all 8 fields | 7 lines |
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
      (amber at 8+, red at 15+: go and visit) and hints opened. Under
      **Last run** is what their last missed run told them (the error, or
      what happened and where), so you know before you walk over. Only you
      see it: the projector never shows it. It refreshes every 5 seconds.
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

**When a run misses**, the banner under the map says what happened and where,
in plain words, then one thing to try (👉). It never asks a question. For example:
*"A belt carried the rover into a crater at x 12, y 5."* 👉 *"Belts carry the
rover the way their arrows point. Jump over a belt you don't want to ride."*
Or, for code that stops short: *"Your code finished with the rover at x 4, y 2,
away from the beacon at x 9, y 2."* 👉 *"The beacon is 5 squares east of there."*
Where the zone's new idea is the way through, the 👉 says so: rock with drills
left suggests `drill("east")`, a locked gate points at the key, and once jump()
has arrived a crater one square wide says where to jump from. A flat battery
says where and when the rover last stood in the sun, with the loop that
charges it, and on Uncharted a gust points at `gust_in()`. It also mentions
bumping into rock (the rover doesn't move when it bumps) and running out of
drills. **Show me** jumps the replay to that moment and rings the rover. Field
measurements still get their step-by-step coach tips, and code errors still say
the line. A while loop that keeps going after the rover stopped moving (often
`east(distance("east"))` driving 0 squares at a trench edge) says where the
rover stopped and why, instead of just "ran too long": the drive that went 0
squares, a way to the target that the code never drives (an `if` with only
east and south), or what its `look()` saw that no branch handles.

In Laser Range the replay keeps the red beam on while the rover drives the
distance it measured, ending in a dot on what it hit.

The command buttons under the code only show sensors for things on the current
map: no key buttons without keys, no cargo buttons without a home. Typing any
unlocked sensor still works.

Copying is pointless on C sites, because the planet underneath is different:
each C site has 8 versions, and a classmate's hand-counted route works on
yours only when you happen to share a version. Explaining *why* your code
works is how to help a neighbour.

## The words to use

| Moment | Say this |
|---|---|
| "What's the rule?" | "What did your last run show you? Drag the timeline under the map back to the exact tick where it went wrong. **Show me** jumps there." |
| They have a guess | "Good. Write it down, then design a run that would prove you wrong." |
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
| 3 | **Solar Valley** (5A–5C) → **Portal Fields** (6A–6C) | "How did you work out where each portal goes? How many runs did it take?" |
| 4 | **Signal Plains** (7A–7C): steering by coordinates on calm ground → **Crater Hops** (8A–8C): the new `jump()` | "When does your program jump, and how does it know?" |
| 5 | **Conveyor Works** (9A–9D) → **The Quarry** (10A–10D) → **Gate Station** (11A–11D) → **Flag Relay** (12A–12D) | "Which new thing changed your program most, and what stayed the same?" |
| 6 | **Boulder Yard** (13A–13D) → **Laser Range** (14A–14D) → **Cargo Run** (15A–15D) → **Uncharted**: the same 5 planets every run | "Where did a variable or a sum save you from counting?" |

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
- **1C Rock Run** (per student): a sample waits in front of each rock, at
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
- **6C Portal Maze** (per student, 8 wirings, 2–3 trips each). Students
  should write down each pad's destination, then write one function per
  trip.

### 7 · Signal Plains: no strange rule (the ramp to Uncharted)
Calm ground, so the only new thing is steering. New: `beacon_x()` and
`beacon_y()`, the beacon's column and row. Each site takes one of
Uncharted's ideas at a time.
- **7A Homing Signal**: 📡 how many squares east of the lander is the
  beacon? `report(beacon_x() - x())` (answer 12).
- **7B Open Plain** (per student, 8 plains, the beacon in a different
  direction on each). Nothing is in the way, so comparing is enough:
  ```python
  while x() < beacon_x():
      east()
  while x() > beacon_x():
      west()
  while y() < beacon_y():
      south()
  while y() > beacon_y():
      north()
  ```
- **7C Rocky Plain** (per student, 8 wide fields of rock ridges and
  crater lines). Only drive a way that's `safe()`, and step south or north
  when no good way is: Uncharted's program without the gusts and charging.
  7B's code, or leaving out the crater check or the going round, fails on
  every field.

On 7B and 7C the 🌍 star runs the code on all 8 plains, and the telemetry
says how many it reached ("1 of the 8 plains (7 stopped short)"), so a
counted route gets the mission but not the star.

### 8 · Crater Hops: a new trick, not a new rule
The rover can jump: `jump("east")` leaps two squares in one tick, right over
whatever is in between (a crater, a rock, a sample it doesn't pick up). It
needs ground to land on: it can't land on rock (the telemetry says so), and
landing in a crater is still a fall. The replay shows the rover up in the
air, with a 🦘 on the timeline.
- **8A The Trench**: a crater trench from wall to wall.
  `east(4) jump("east") east(2)`. The ⚡ star wants 4 ticks:
  `for i in range(4): jump("east")`, jumping all the way.
- **8B Stepping Stones**: five walls, craters and rock in turn, three
  squares apart. `for i in range(5): east() jump("east")` then `east()`.
  The 🧩 star wants it as a function.
- **8C Crater Field** (per student, 8 fields of walls and trenches). Let
  `look()` decide:
  ```python
  while not at_beacon():
      if look("east") == "crater" or look("east") == "rock":
          jump("east")
      else:
          east()
  ```
  The trap: `if look("east") != "ground"` also jumps when the next square
  is the **beacon**, and sails right over it.

Uncharted has `jump()` too: jumping over a rock is another way round it.

### Zones 9 to 15: one new thing each, told and drawn
These four zones don't hide anything. Each brings one new thing, and the map
draws it, a line under the goals names it ("🛤 belt: carries you the way its
arrows point"), and the zone's first site opens with a **🆕 card** that says
what it does and gives a line to try. Each zone has **four** sites, in
smaller steps than before:

| Site | Job |
|---|---|
| **A · Try it** | The new thing once, in 1–3 lines. The brief shows the line. |
| **B · Use it** | A few times, with a choice to make. |
| **C · Loop it** | The same step repeats, so a loop or a `def` earns ✂️. |
| **D · Your planet** | Per student (8 versions) and the last zone's program fails here. |

There are no 📡 field measurements in these zones.

#### 9 · Conveyor Works: belts carry the rover the way their arrows point
Belts (`> < ^ v` on the map, drawn as rolling chevrons) carry the rover to the
square after the last arrow, round corners too, all in one tick. `look()`
says `"belt"`.
- **9A First Ride**: `east(2)`, and the belt does the rest, round two corners.
- **9B Two Belts**: one belt carries you to the field, the other into a
  crater. `west() north() east(3) south(2) east(2)`
- **9C Belt Steps**: 1B's loop again (`for i in range(5): east() south()`),
  with belts doing the long part. The 🧩 star wants it as a function.
- **9D Cross Belts** (per student): belts cross the lane and run into
  craters. 8C's program with `"belt"` added to the jump test.

#### 10 · The Quarry: `drill("east")` turns the next rock into ground
Each site has a few drills (the ⛏ gauge, `drills_left()`). Drilling ground
costs a tick but no drill.
- **10A First Drill**: `east(3) drill("east") east(5)`
- **10B Drill or Go Round**: three walls, 2 drills; the middle wall has a gap.
  Drilling it leaves you one short at the last wall.
- **10C Tunnel**: `for i in range(6): drill("east") east(2)`. ⛏ star: 2 drills to spare.
- **10D Your Quarry** (per student): rock walls two thick (too thick to jump)
  and crater trenches (can't be drilled):
  ```python
  while not at_beacon():
      if look("east") == "rock":
          drill("east")
      elif look("east") == "crater":
          jump("east")
      else:
          east()
  ```

#### 11 · Gate Station: keys open gates
Driving over a 🔑 picks it up; driving into a 🚪 with a key opens it (and
uses the key). Without one, the gate stops the rover like rock, and nothing
can jump a gate. New: `has_key()`, `key_x()`, `key_y()`.
- **11A The Gate**: `east(9)` picks up the key on the way.
- **11B Key First**: `north(2) east(2) south(2) east(7)`
- **11C Three Rooms**: one `def room():` (step in, up for the key, back,
  through the gate) called three times.
- **11D Your Key** (per student): Signal Plains' steering twice, as one function:
  ```python
  def go_to(tx, ty):
      while x() < tx:
          east()
      while x() > tx:
          west()
      while y() < ty:
          south()
      while y() > ty:
          north()

  go_to(key_x(), key_y())
  go_to(beacon_x(), beacon_y())
  ```

#### 12 · Flag Relay: flags count only in order
The beacon needs every flag first. Driving over a later flag is harmless
(the telemetry says which one comes first). New: `next_x()` and `next_y()`
(the next flag, or the beacon once every flag is done) and `flags_left()`.
- **12A First Flags**: `east(9) south(2)`
- **12B Zig-Zag**: four flags out of order across the field, by hand.
- **12C Long Relay**: seven flags. `go_to()` from 11D in a loop is 11 lines,
  where steering by hand is 16:
  `while not at_beacon(): go_to(next_x(), next_y())`
- **12D Your Relay** (per student, rock in the way): 7C's program with
  `next_x()` and `next_y()` in place of the beacon's. That's most of
  Uncharted's program.

#### 13 · Boulder Yard: drive into a boulder to push it
A boulder (🪨, `look()` says `"boulder"`) moves one square when the rover
drives into it, unless something is behind it. Pushed into a crater, it fills
it in. A jump can't land on one.
- **13A First Push**: `east(8)` pushes it into the trench and drives on.
- **13B Push South**: a trench two deep, too far to jump. Get above the
  boulder: `east(3) south(3) jump("south")`.
- **13C Boulder Steps**: `for i in range(4): east(2) jump("east")`, then
  `east()`. The 🧩 star wants it as a function.
- **13D Your Boulders** (per student): wide trenches with a boulder, narrow
  ones without. Crater Hops' loop, since driving pushes:
  `if look("east") == "crater": jump("east") else: east()`. Jumping at
  anything that isn't ground jumps the boulder into the trench.

#### 14 · Laser Range: `distance("east")` measures how far the rover can drive
`distance(way)` counts the squares up to rock, a crater, a boulder or a gate.
Every drive's number can come from it: the 🔢 star wants **no typed-in
numbers** in the drives. The replay shows the beam.
- **14A First Laser**: `east(distance("east"))`.
- **14B Crater Edge**: `while not at_beacon(): east(distance("east")) jump("east")`
- **14C Laser Steps**: each sample is one square short of the rock:
  `for i in range(3): east(distance("east") - 1) south(distance("south") - 1)`.
  1C's while loops overshoot every sample.
- **14D Your Range** (per student): 14B's loop on every field.

#### 15 · Cargo Run: three samples at a time, brought home to 📦
The rover starts at home. Samples go in the cargo bay (`cargo()`, 3 at most);
with a full bay the rover drives over a sample and leaves it. Driving onto
home unloads. New: `cargo()`, `home_x()`, `home_y()`, and `sample_x()`,
`sample_y()` (the nearest sample).
- **15A First Load**: `east(7) west(7)`
- **15B Two Trips**: one row out and back, then the other: 6 drives.
- **15C Shuttle**: each trip goes one row further, so the loop's `i` does it:
  `for i in range(4): south(i) east(6) west(6) north(i)`. The 🧩 star wants
  `def trip(n)`.
- **15D Your Cargo** (per student): `go_to()` from 11D, and a decision each trip:
  ```python
  while True:
      if cargo() == 3 or samples_left() == 0:
          go_to(home_x(), home_y())
      else:
          go_to(sample_x(), sample_y())
  ```

### Uncharted: the finale
Every run lands on **the same 5 planets** (they used to be new random ones
every run, which was too hard). Five different planets still mean a list of
moves can't work: the program has to sense and decide. Students see the
first planet before they run, and all five after the first run. New:
`gust_in()` (ticks until the next gust). Rock
ridges, crater lines, ice, wind and sunlight are all there, the lander
sits in sunshine with too little battery to cross, and craters lie round
the beacon. The program below reaches all five. Scored on planets reached,
then ticks.

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
Students arrive with 7C's program, which already compares, checks
`safe()` and goes round. On these five planets it reaches **2**, so the
first star comes on the first run. Waiting out the gusts and charging in
the sun win the rest, and `test_planet.py` checks that leaving out any idea
(sun, wind, craters, going round) loses a planet.

**Discussion:** "Your rover ran flat by the lander. Why? What did it need to
check before it set off?"

## What's checked automatically

`python3 -m unittest test_planet` proves every claim above. For each site
the reference program clears every planet, the obvious program from before
fails, and on per-student sites one student's route fails on the other
students' planets. It also checks that the opening sites are open ground,
not corridors, and that the maze game's commands explain what to use instead.
