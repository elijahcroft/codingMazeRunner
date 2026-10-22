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

Same as Python Quest: the program runs top to bottom with commands
(`move()`, `turn_left()`, `turn_right()`, `wait()`) and yes/no or number
sensors. Every command takes one **tick** of planet time, and the time-based
rules (wind, sun) run on ticks.

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
