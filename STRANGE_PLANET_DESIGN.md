# Strange Planet: level design (draft for review)

Students drive a rover across an alien planet. Each zone has **one hidden
physics rule** that nobody explains. Students find it by running code,
watching the replay and reading the log, then write a program that works
*with* the rule.

Decided so far: standalone (Zone 1 teaches Python from zero), several lessons
(about 3–4 sessions), and a live teacher overview with no class battle.

## Design rules every zone follows

1. **The rule is never stated.** The log reports what happened ("moved 4
   squares", "battery 0"), never why. Hints (three per zone, from a nudge to
   partial code) are what eventually say it.
2. **The last zone's program fails here, and you can see it fail.** Students
   should be able to point at the replay and say "there, that's where it went
   wrong".
3. **Three sites per zone:**
   - **A: Notice.** The rule shows up in a simple setting, and the obvious
     program breaks in plain sight.
   - **B: Use.** The site can only be solved by using the rule on purpose.
   - **C: Generalise.** The rule's details are different for each student
     (and for some sites, different on every run). Memorised numbers and a
     neighbour's code both fail; only a program built on sensors and
     variables works.
4. **Every claim is a test.** For each site: the previous zone's reference
   program fails, this zone's reference program passes, and for C sites one
   student's hard-coded answer fails on another student's planet. Bot Rally
   already has tests like these.

## The program model

The program runs top to bottom with commands, like Python Quest, but the
rover **never turns**: it drives by compass (`north()`, `south()`,
`east(3)`, `west()`, `wait()`), senses in words (`look("east")` is
`"rock"`, `"ice"`, `"crater"`, `"crack"`, `"sun"`, `"pad"`...) and in
coordinates (`x()`, `y()`), and some missions end with `report(n)`. Every
square of driving (or wait) takes one **tick** of planet time, and the
time-based rules (wind, sun) run on ticks. See "Not the maze game" below
for why it changed.

*Why not a per-turn function like Light Cycles' `steer()`?* For students
who have never coded, commands in order are much easier to start with, and
planning a route is where these puzzles get their depth. (Decided: commands in order.)

## The zones

| Zone | Hidden rule | Python idea it forces |
|---|---|---|
| 1 Landing Site | none (normal ground) | commands in order → `for` → `while` + sensor |
| 2 Ice Field | `move()` slides until something stops you | predicting where a command leaves you |
| 3 Wind Canyon | a gust pushes you every few ticks | counters, `%`, `wait()` |
| 4 Crumbling Crust | ground you leave cracks; step on it again and you fall | `if` with `and` / `or`, check before you act |
| 5 Solar Valley | battery drains; sunlight recharges it, and the sunlit band moves | number variables, thresholds, functions with parameters |
| 6 Portal Fields | matching pads teleport you; the pairs are hidden | experimenting across runs, functions as named routes |
| 7 Uncharted | all of the above, with a random map each run | one general program |

### Zone 1: Landing Site (lesson 1, first half)
Teaches the basics with no strange physics, so Zone 2's surprise has
something normal to contrast with.
- **A:** a short route. *Commands run in order; a wrong turn shows on the replay.*
- **B:** a long route made of a repeated zig-zag. *Typing it out is painful, so use `for`.*
- **C:** corridors of different lengths, different for each student. *Counting
  breaks, so use `while not wall_ahead(): move()`.*

### Zone 2: Ice Field
**Rule:** on ice, one `move()` slides until the rover hits a rock or reaches
normal ground.
- **A:** the Zone 1 counting program flies past the goal. The replay shows one
  `move()` covering six squares. *"Wait, why did it go so far?"*
- **B:** a classic ice puzzle: the only way to stop is against rocks, so the
  route is chosen by which rocks to slide into. *Plan from the end backwards.*
- **C:** ice and ground mixed, different for each student. *Before moving,
  ask `on_ice()` and work out whether this move slides or steps.*

### Zone 3: Wind Canyon
**Rule:** every N ticks a gust pushes the rover one square east, unless a
rock shelters it. N is different for each student (4 to 7). There are
craters to the east of the path.
- **A:** a straight canyon. The rover drifts a little at a time and falls
  into a crater. *The replay shows sideways jumps. When do they happen?*
  (`print(tick())` gives the answer away to anyone who looks.)
- **B:** a narrow ledge. *Count ticks and `wait()` behind a rock just before
  a gust: `if tick() % 5 == 4: wait()`.*
- **C:** sheltering rocks are spaced irregularly. Two good strategies (time
  the gusts, or hop from shelter to shelter) both work, which makes a good
  class discussion.

### Zone 4: Crumbling Crust
**Rule:** every square the rover leaves cracks, and stepping on a cracked
square again means falling through.
- **A:** the Zone 1 wall follower goes into a dead end, turns back and falls.
  *Backtracking is now deadly.*
- **B:** collect three samples without crossing your own path. *Plan the
  order, and check `cracked_ahead()` before moving.*
- **C:** the layout is different for each student. *Combine sensors:
  `if not wall_ahead() and not cracked_ahead():`.*

### Zone 5: Solar Valley
**Rule:** every action costs 1 battery, and standing in sunlight adds 3. Cliff
shadows move across the valley every few ticks. At 0 battery the rover stops.
- **A:** the shortest route runs out of battery in the shade. *`print(battery())`
  shows it falling.*
- **B:** wait in the sun before crossing the shadow:
  `while battery() < 20: wait()`. *A threshold in a variable.*
- **C:** the shadow timing is different for each student. *Write
  `charge_to(n)` and `cross(steps)` functions; a better program arrives with
  less waste and earns par stars.*

### Zone 6: Portal Fields
**Rule:** stepping on a pad teleports the rover to its partner. All pads look
the same, and the pairs are different for each student.
- **A:** the rover vanishes and reappears somewhere else. *Which pad goes
  where?* The map stays lit between runs (as in Blackout Protocol), so
  evidence builds up.
- **B:** reaching the goal needs a chain of two portals. *Run experiments,
  write down the pairs, plan a route.*
- **C:** some pads only work one way. *Name each route as a function
  (`to_north_ridge()`) and build the full trip from them.*

### Zone 7: Uncharted (the finale)
Each run is a new random planet with fog and any of the rules. The program is
tested on 5 planets at once, like Bot Rally, and scored on planets reached,
then samples collected, then ticks. *Only a program built from sensors and
general rules gets through.*

## Lesson pacing (rough)
- **Lesson 1:** Zones 1–2
- **Lesson 2:** Zones 3–4
- **Lesson 3:** Zones 5–6
- **Lesson 4:** Zone 7, with fast students pushing for par stars

Each zone has a discussion moment: "What did you think the rule was, and what
run proved it?"

## Teacher overview
A `/screen`-style page listing each student's zone and site, the number of
runs since their last progress (so stuck students stand out), and hints
opened. Optional: a one-line **field journal** box where each student types
their guess at the hidden rule, shown on the overview so the teacher can see
the thinking, not only the score. (Decided: yes.)

## Build shape (detail comes in the build plan)
A new `planet.py` engine and `/planet` page that reuse the existing safe
interpreter style, plus tests that prove every site's claim before any UI
work starts.

## Decisions (ej: "go with your recommendations")
1. **Commands in order**, like Python Quest. Every command is one tick.
2. **Per-student details on every C site** (variant picked from the student's id,
   the same every time).
3. **No lists or dicts.** Portal routes are functions.
4. **Field journal: yes.** One note per zone, shown on `/planet/teacher`.
5. **All seven zones kept.**

## What changed while building (each one forced by a test)
- **2C** is a per-student ice puzzle (4 lakes, 7–8 slides each) instead of
  mixed ice and ground: a general sensor program for mixed ice turned out
  to be either trivial or impossible.
- **3C** gust intervals are 4, 6, 7 and 9: no interval divides another (an
  "every 4" program accidentally survived "every 8"), and 5 is left out so
  3B's answer can't be reused. The "hop from shelter to shelter" strategy was
  dropped. Rock still shelters, but the sites are built around timing.
- **Wind only catches a rover that is driving**, so `wait()` is the counter.
- **4A**: a right-hand wall follower solves it by looping through the
  two-wide pit. That counts as a good answer, not a bug.
- **4B** is three pits solved with one `pit()` function in a loop, rather than a
  plan-the-order puzzle.
- **Solar**: waiting is free, so charging always works, and sunlight
  adds 2 per tick. In 5C one charge stop is never enough: the rover has to
  ride the moving light. A replayed plan still fits some other planets, so
  the test claims only that **no hard-coded plan works on every planet**.
- **6C** pads sit in different places in each field, so one wiring's
  moves can't happen to fit another.
- **Uncharted** mixes ice, craters, wind and sunlight. Crumbling ground and
  portals are left out because a wall follower must backtrack. It adds the
  `gust_in()` sensor, and every random planet is checked solvable before it's used.
- **No par stars and no fog** in v1. Each site keeps the student's best ticks.

## Not the maze game (the compass redesign, October 2026)

ej: "the new game is too much like the old one". The class had already done
the Python Quest maze game, and Strange Planet opened the same way: a
corridor, an arrow, `move(3)`, `turn_left()`, `wall_ahead()`, "reach the
goal". So what students *do* changed, and the zones and their hidden rules
stayed:

- **Compass driving, no turning.** `north() south() east() west()`. It looks
  different from the first screen, and it's easier for beginners (no turning
  in your head). The maze game's commands give a message saying what to
  write instead.
- **Open ground, not corridors.** The opening sites are fields with
  boulders, samples and ice, checked by a test that most squares have
  three or four open neighbours.
- **Missions, not exits.** Each site is 🧪 collect every sample,
  🛰 reach the beacon, or 📡 a field measurement: find the rule's number
  and `report()` it. Measuring it in code earns the 🔢 star, so the A site
  of Ice, Wind and Solar *is* the experiment.
- **Sensing in words and coordinates.** `look(way)` returns text, so
  students compare strings (`!= "rock"`), which the maze game never needed.
  The map is numbered along the top and side for `x()` and `y()`.
- **Uncharted steers by coordinates** (`beacon_x()`, `beacon_y()`) instead
  of hotter or colder.
- The Landing Site is no longer a skippable warm-up: it's where compass
  driving and `look()` are learnt.

## Zones 9 to 12: one new thing each (October 2026)

ej asked for many more levels whose mechanics scale, are easy for the class,
are explained simply, and fail with a clearer report. The new zones sit
between Crater Hops and Uncharted, and each adds **one** thing, told and
drawn rather than hidden: belts (Conveyor Works), `drill()` (The Quarry),
keys and gates (Gate Station) and numbered flags with `next_x()`/`next_y()`
(Flag Relay). Each zone's last site reuses the zone before it with one change
(8C's jump loop → 9D, plus an `elif` → 10D, Signal Plains' steering as
`go_to()` → 11D, `go_to()` in a loop and 7C's going round → 12C/12D →
Uncharted). They have four sites in smaller steps: try it, use it, loop it,
your planet. There are no 📡 report() sites, which the class found confusing.

Every site's brief now says what to do in plain words.

**Failure messages.** `planet.explain()` turns a run that didn't finish
into `{"what", "next"}`: what happened and where (x, y), then one thing to try.
It never asks a question. The engine records how the rover got onto its last
square (driving, a jump, a gust, an ice slide, a belt), so a fall says what
caused it. Stopping short gives the distance to the beacon, the nearest
sample, the next flag, or the key for a locked gate, or suggests drill() when
rock stopped a rover that has drills. A fall from driving names the way it
drove, and once jump() has arrived, a one-square crater says where to jump
from. It also notes bumps into rock and running out of drills. A while loop
that exhausts the budget after planet time stopped gets `stalled()` instead of
"ran too long": where the rover stopped, and the drive that went 0 squares.

Sensors now arrive by zone key (`SENSOR_ARRIVES`, `ZONE_ORDER`), so adding
a zone can't shift their numbers.

## Zones 13 to 15: push, measure, carry (October 2026)

ej asked for more, and picked boulders, a laser and cargo runs. They follow
the same four-site shape and come between the Flag Relay and Uncharted:

- **Boulder Yard**: driving into a boulder (`B`) pushes it; pushed into a
  crater, it fills it. A two-wide trench needs a boulder and a jump, so 13D is
  Crater Hops' loop again (driving pushes), and jumping at anything that isn't
  ground fails.
- **Laser Range**: `distance(way)` counts the open squares up to rock, a
  crater, a boulder or a gate, and the replay draws the beam. The new 🔢
  "measured" star wants no typed-in numbers in drives. 14C puts each sample one
  short of the rock, so `distance() - 1` is the idea and 1C's loops overshoot.
- **Cargo Run**: the rover starts at home (`H`) and carries 3 samples at most
  (`cargo()`); the 📦 mission counts samples brought home. 15C needs the loop's
  `i`; 15D is `go_to()` with an if that picks home or the nearest sample
  (`sample_x()`, `sample_y()`).

Sample pick-ups are now in the replay frames (`p`), since a full bay drives
over a sample without taking it.

## More rewards (October 2026)

ej saw the class respond to the gifts, garage and talking rover, and asked
for more. The rule kept: rewards are positive only, never a ranking in front
of the class, and calm mode removes the motion but keeps the words.

- **A reward all the way up.** Personal unlocks stopped at 60 ★ while a
  student can earn 159, so zones 9 to 15 paid nothing new. Ten more items
  now arrive between 65 and 150 ★.
- **Class goals that last.** The meter's last goal was 180 ★, which a class
  passes in a lesson. Goals now go to 2400 ★, and the projector shows one
  stage at a time (last goal reached to the next two), so it always moves.
  A crossed goal is a projector card and a toast for everyone.
- **Ranks** (`server.RANKS`, `rank_for`) every 10 to 25 stars, with a bar to
  the next on the ★ button. Student's own screen only.
- **First try** (`first_try` in the rewards: first transmit on a site never
  completed) and the 🎯 Sharpshooter badge for 5.
- **Combos**: pick-ups within 4 ticks of each other climb in pitch and float
  "×n"; unloading cargo goes ka-ching. Stars fly to the counter.

While testing, list paints (Aurora, Nebula, Supernova and the rest) turned
out to have drawn black for a while: arrays have their own `.fill`, so
`bodyPaint` took them for a fill function. It now checks for an array first.
A test checks every garage item has drawing code.

Then, to give a reason to come back and to keep a stuck student going:
**today's missions** (`server.MISSIONS`, `todays_missions()` seeded by the
date so the class shares them; all but a first try work on solved sites),
mission-day trophies with a medal at 3, a **zone cleared** card with a
teaser for the next zone, and the rover's cheer at the beacon (a 0.9 s beat
before the card, none in calm mode).

Then choices in the fun moments: a **victory dance** slot (`dance(kind, u)`
in the page; some dances are earned with a badge, `"badge"` in GARAGE) and
one earned badge **worn on the class screen** (`entry["showoff"]`).

And a **record ghost**: each student's best route on a shared-map site is
kept (`entry["routes"]`, up to 400 frames), and `ghost_for()` sends the class
record's route to anyone who has completed the site, to race in the replay.

## Measuring your own planet (October 2026)

The class's saved runs showed the 📡 sites being guessed or copied: every
student's 2A answer was `report(6)`, Harvey took 85 runs on 5A with
`report(1+1)`, and one student used a classmate's `tick() % 9` on a 3C
ridge whose gusts come every 7 (26 runs). (The step-by-step coach landed the
evening after that lesson, so the class hadn't seen it yet.) ej: "we need
to explain steps more clearly to them".

- **Per-student numbers** on 2A (ice 5, 7, 8 or 9 long), 3A (gusts every 4,
  6, 7 or 8) and 7A (beacon 9, 11, 14 or 16 away). The old shared answers
  are left out. 5A stays at 2 for everyone, because the whole Solar zone
  runs on it. A test reports each variant's number on every other one.
- **A classmate's number is named as one.** Each per-student 📡 variant
  knows the others' answers (`others`, never sent to the page); reporting
  one says "That's the number on someone else's planet" in the telemetry and
  at the front of the coach's tip. The briefs say each planet's number is its
  own. On the other per-student sites, a run that misses but whose code
  works on classmates' planets (`elsewhere()`, under 100 ms for 7 planets,
  outside the lock) starts its next step with "This code works on 2 other
  planets in the class, but yours is different."
- **Numbered steps in the brief** of all four 📡 sites, one per line
  (`#siteBrief` keeps the line breaks). The coach still goes further after
  each miss.
- **3B's brief says the gusts come every 5 ticks**, since 3A's number is now
  the student's own, and gives three numbered steps (wait on the tick before
  a gust, put the check in a def called before every square, drive each part
  one square at a time): 3B cost 12 to 42 runs even for students who opened
  every hint. 3C's brief says to measure your gusts and reuse The Ledge's
  check, in two lines, because a longer brief would make its ridge zoom.
- **A gust fall reads the code.** When a gust (or a drive after one) ends in
  a crater, `gust_next()` finds the `tick() % n` in the program: a number
  from another planet is named as wrong here, with the ticks the gusts come
  on ("5, 10, 15 and so on", which the telemetry's 💨 lines already show);
  the right number gets which tick to wait on, and no number gets when they
  come.
- **Clearer slips:** an unquoted look() word (`!= rock`), commands joined by
  a comma, `range 8` and `=!` each say the fix. look() compared with a word
  it never gives back (`"wall"` from the maze game, `"Rock"`, `"empty"`) is an
  error that names the right word, instead of a loop that runs into rock
  until time runs out. A line that works something out and drops it (`x() == 3` on its
  own) shows where it could go (`if x() == 3:`, `n = ...`), quoting the
  student's own text, instead of Light Cycles' "Did you mean to return it?".
  The `!` hint's example is `while not at_beacon():`, not the maze game's
  `wall_ahead()`. A hint's `...` placeholder, copied in, says to replace it with
  your own lines. A test runs every code snippet in a hint, coach step or
  brief on its site. `**` and `^` say to multiply instead (in every game: "That kind of
  math isn't allowed here" said nothing), and `&` / `|` give a look() example
  instead of Light Cycles' `wall_ahead()`. A drive command in a sum
  (`east(2) + south(2)`, `n = east() + 1`) says it gives back no number and
  to put each command on its own line, instead of `n = ...` or "not None". Huge numbers, `range(999999999)`
  and runaway recursion were tried too: each stops at once with a message,
  so one student can't freeze the class's server.
- **The teacher's page** marks students who haven't pressed Transmit yet.
- **The last 6 tries on each site are kept** (`entry["tries"]`: code, end,
  banner words). The first lesson kept only each site's last program, so
  Harvey's 85 runs on 5A left one line of evidence. The teacher's page shows
  the tries for the site each student is on (a `<details>` that stays open
  across its 5-second refresh); student pages never get them.
- **1C's challenge star is 🌍** (the same code on all 8 rock runs) instead of
  no-bump: every student who solved 1C counted squares off their own map
  and never used look(). The 🌍 telemetry line now names the site's
  mission instead of always saying "reached the beacon".
- **The coach remembers** misses across a reload: it starts from the
  server's count of misses in a row.
- **1B and 1C show the loop's shape** in the brief (a sentence, a blank line,
  then code in the editor's font, like a hint). No student used `for` on 1B
  (one typed 100 lines) or `look()` on 1C. The examples aren't the answer:
  1B's drives east 3 times, 1C's goes east only. The brief sits beside the
  site's name when there's room, with the code beside its words, so the map
  keeps its height: measured at 1366×768, every site that showed its whole
  map before still does, except 3A, whose longer canyon (19 rows, for
  south(16)) now zooms and follows the rover like 3B.
- **Out of time on two or three squares** says which squares the rover went
  back and forth on (`pacing()`), and once jump() has arrived, which crater
  to jump from: 7C's steering on 8A used to get "a while loop is probably
  going round forever".

## A real editor, and help in plain sight (October 2026)

ej asked for learning to be easier, help for stuck students to be obvious,
and the editor to feel like a real one (autocomplete, closing brackets).
The editor is still a textarea with a coloured copy behind it, so every
change goes through the browser's own typing and Ctrl+Z undoes it.

- **Suggestions** come from what the student can use here: the zone's
  commands and sensors, Python's words, the builtins the interpreter allows
  (`print range abs min max`), and the student's own defs and variables.
  Each shows its `HELP` line. A word that's already a whole name never opens
  the list, so Enter after a variable is still a new line.
- **The rule stays hidden.** Suggestions say what a command *is* (the kit's
  wording), never how the zone treats it, and the look() words offered are
  the squares on this map.
- **Slips while typing** are checked in the page (`problemsIn`) only on lines
  the cursor has left, and only for things that are always wrong in Python
  here; anything subtler is still the run's job, whose messages say more.
  While a run's error is on screen the page's own checks step aside.
- **Each frame knows its line** (`"ln"` in `World.frame()`, set by
  `Rover.run_statement`): a drive inside a def is its line in the def, and a
  gust's push stays with the drive it interrupted. The editor lights that
  line during the replay, but only while the code is the code that ran.

## Nobody stuck in one place (October 2026)

The first lesson's save: 6 of 12 students opened the planet and never pressed
Transmit, Harvey missed Uncharted 59 times in a row, and 3B took 12 to 42 runs.
Replaying every student's saved code through the current engine found four
messages that were wrong or empty for real programs.

- **A first-run nudge:** 45 seconds on a site without ever transmitting
  (`state.you.ran`) makes Transmit glow and the banner say to press it.
- **Ask a classmate:** from 8 misses in a row (`HELP_AFTER`), a missed run
  names up to two classmates who cleared the site and ran in the last hour.
  Names only, on the student's own page; the projector never shows misses.
- **Skip for now:** from 20 misses in a row (`SKIP_AFTER`) on the site a
  student is up to, ⏭ opens the next one (`/planet/skip`, recorded in
  `entry["skipped"]` for the teacher). No stars, and the finale can't be
  skipped. Brute force stays allowed; this only stops a rut.
- **The old answers** (2A 6, 3A 5, 7A 12: a variant's `old`) say they were
  the number before every planet got its own. Copy messages (old or a
  classmate's) need a typed number (`fixed()`: no sensor or variable, sums
  like `1+5` count); `report(y())` landing on 5 is only wrong.
- **Out of time** with no while loop in the code names the for loop's count
  (`out_of_time()`), instead of "a while loop is probably going round forever".
- **One-line if/while/for** with a command after the condition (`if x() == 1
  east()`) says to end the line with `:` and put the commands under it; `: ...
  else:` on one line says else goes on its own line (shared `LINE_HINTS`).
- **No real answer in examples:** the no-report tip no longer says
  `report(4)`, which is someone's 3A answer.
- **The teacher's page** marks 3 minutes without a run (in the last hour) in
  amber, with "✎ typing" from `/planet/typing`, and shows skipped sites.
- **Backups:** each server start copies the save to `.start-<time>`, keeping 5.
- **Site by site** (`/planet/report`, a `<details>` on the teacher's page,
  fetched when opened and every 30 s): tried / cleared, median and most
  runs, who tried and hasn't cleared it, skips, hints per zone, and the
  three commonest miss messages from `entry["tries"]`, grouped with their
  numbers taken out so "at x 2, y 1" and "at x 4, y 1" count as one.
- **Beginner slips:** a def of drives called once outside a loop
  (`called_once()`) says it ran once and to call it again or loop it;
  `east(1.5)` asks for a whole number; `east(-1)` points at `west(1)`.
- **Load:** 30 students on one server, all transmitting 7C's 🌍 reference
  in the same second, finished in 0.7 s; two minutes of mixed class use
  (Uncharted, stuck while loops, per-student misses, typing every run)
  kept runs under 0.4 s with no errors. The save was 220 KB.
- **Closest yet:** a missed run on a site not yet done is measured by
  `planet.progress()` (samples collected, or squares from the beacon by
  open ground, walking round rock and craters; none on maps with portal
  pads, report or deliver sites, or Uncharted). Beating the student's best
  miss (`entry["closest"]`) gives a 🔥 toast with the old mark; the first
  miss only sets it. A reward for getting further, not for trying again.
- **Spotlight:** the admin actions `planet_spotlight` (a student's last
  transmitted code on the site they're on) and `planet_spotlight_off` set
  `planet_spotlight`, sent with `/planet/overview`. The projector shows it
  full-screen with the site and whether it works, never the name. It isn't
  saved: a restart clears it.
- **A reading sent as it was:** `report(battery())`, `report(x())`,
  `report(beacon_x())` (a bare sensor in `READINGS`) that isn't the answer
  says it sent what the sensor reads now, not the change (or, for the
  beacon, not how far away it is), and the coach leads with that.

