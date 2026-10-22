# Python Quest: tomorrow’s 60-minute lesson

Python Quest is now the main student experience. It is deliberately **four
substantial missions**, not a long ladder of nearly identical mazes. The old
levels still exist at `/classic` as optional practice; they are no longer the
default path.

The four missions form one progression:

1. **Pattern Foundry** — decompose a repeating shape into a function and loop.
2. **Search Protocol** — replace move counts with a general sensor-driven
   algorithm.
3. **The Sealed Archive** — discover where that algorithm fails, split the
   problem into phases, and debug a deliberate plan.
4. **Blackout Protocol** — explore an unseen system, gather evidence across
   runs, and refine the program.

**Bot Rally** at `/arena` is the optional finale: the exact same program is
tested on five tracks at once. It has three self-paced leagues (Rookie, Pro,
Expert); Gold in one league unlocks the next, so students spread out instead
of waiting for each other.

## Setup before students arrive

1. Put your laptop and student devices on the same Wi-Fi.
2. From this folder run:

   ```bash
   python3 server.py
   ```

3. Give students the **Python Quest** address printed in the terminal, including
   `:8000`. It will look like `http://192.168.1.42:8000`.
4. Open the same address on the projector for the first demo.
5. Keep these optional pages handy:
   - `/arena` — Bot Rally, three leagues of five tracks
   - `/cycles` — Light Cycles battle royale (project `/cycles/show`; see
     `LIGHT_CYCLES_GUIDE.md`)
   - `/planet` — Strange Planet, a rover in zones with hidden physics rules
     (teacher view `/planet/teacher`; see `STRANGE_PLANET_GUIDE.md`)
   - `/screen` — live overview of student maps and code
   - `/admin` — unlock a later mission for one advanced student
   - `/classic` — the old maze practice library

No packages or internet connection are needed after the server starts. Progress
and each student’s best runs are saved in `scores.json`. Code in the new editor
is also remembered per mission by that browser.

## The one-hour plan

| Time | Phase | Teacher move | Student work |
|---|---|---|---|
| 0–5 | Hook | Open Mission 1. Ask: “Where is the repeating shape? What should we teach once instead of type three times?” | Trace the map with a finger and describe one “tooth.” |
| 5–10 | Predict | Click **Load starter**. Read `def`, `pass`, `for`, and the indentation. Do not solve it yet. | Predict what `pass` will do and what belongs inside `tooth()`. |
| 10–22 | Modify | Live-code the first turn and deliberately make one wrong turn. Use the output/map to debug rather than immediately correcting it. | Finish Mission 1, preferably in driver/navigator pairs. |
| 22–27 | Investigate | Open Mission 2. Run a hard-coded idea or ask why the Mission 1 move counts cannot be trusted here. | Identify forks, dead ends, sensors, and the need for a repeated decision. |
| 27–42 | Make | Reveal the API drawer. Give the “one hand on a wall” idea only if needed. | Build and test a sensor-driven `while` algorithm. Aim to complete Mission 2. |
| 42–50 | Test broadly | Open `/arena`. Load the rookie bot first or paste the students’ algorithm. Ask for a 0–5 prediction before running. | Compare one program across five tracks; explain a miss using its path trace. |
| 50–57 | Two lanes | Most students improve reliability. Offer the advanced lane: Rookie Gold, then Pro League par stars, then Expert. | Debug, optimize, or improve clarity. |
| 57–60 | Demonstrate | Show one clearest solution and one clever optimization. Ask each author to explain a decision, not just the score. | Exit sentence: “My program became more general when…” |

Missions 3 and 4 are intentionally too substantial to rush through this first
hour. They are excellent continuation work—or an expert lane you can unlock
from `/admin` without making the experienced child wait through repetitive
levels.

## Pair programming

When possible, use one device for two students:

- The **driver** types and runs the program.
- The **navigator** reads the map, predicts the next result, watches for errors,
  and explains the rule.
- Swap once after about 7 minutes.

Do not automatically make the strongest student the room’s unpaid helper.
Give them a genuine problem first. They can choose to explain a solution after
they have had their own challenge.

## Mission 1 answer key

The supplied starter is incomplete. A clear solution is:

```python
def tooth():
    turn_left()
    move(2)
    turn_right()
    move(2)
    turn_right()
    move(2)
    turn_left()
    move(2)

for repeat in range(3):
    tooth()
```

Good questions:

- Why does the function finish facing the same direction it started?
- What breaks if the final `turn_left()` moves outside the function?
- Why is `repeat` allowed even though we never read its value?
- How is this different from copying the eight commands three times?

## Mission 2 answer key

A readable right-hand wall follower completes Mission 2 and clears all five
Rookie League tracks in Bot Rally:

```python
while not at_goal():
    turn_right()
    while wall_ahead():
        turn_left()
    move()
```

In Bot Rally this takes **342 actions**. The left-hand version also clears all
five, but takes 384. That supports a useful conversation: two correct algorithms
can differ in efficiency.

## Mission 3 answer key

The wall follower alone never reaches the uplink, but it does carry the bot
past the vault's doorway. Run it a fixed number of times, then finish with a
precise approach:

```python
def reach_courtyard():
    for step in range(60):
        turn_right()
        while wall_ahead():
            turn_left()
        move()

def enter_vault():
    turn_left()
    move(3)

reach_courtyard()
enter_vault()
```

Students find the number by experiment: run only `reach_courtyard()`, watch
where the bot stops, and adjust the range. A full hard-coded route (28 lines)
also works; compare the two and ask which one was easier to debug.

## Mission 4 answer key

Same idea, in the dark. Running the wall follower first lights up the map, and
the lit squares persist between runs, so the doorway becomes visible:

```python
def reach_courtyard():
    for step in range(131):
        turn_right()
        while wall_ahead():
            turn_left()
        move()

def enter_vault():
    turn_left()
    move(3)

reach_courtyard()
enter_vault()
```

`print(step)` inside the loop helps students find where to stop.

## Bot Rally leagues

Each league is built so the previous league's easy answer stops being enough.
The test suite checks every claim in this table.

| League | Tracks | Plain wall follower | What it takes |
|---|---|---|---|
| Rookie | five short World 1 tracks | Gold, 0 stars | any sensor-driven loop |
| Pro | World 2–3 labyrinths, two mirrored | Gold, **0 stars** | stars need fewer actions *and* the right hand per track |
| Expert | goal locked in a central vault | **0/5**, loops forever | a new strategy, e.g. the Bug algorithm |

**Par stars:** par is the fewest possible moves + turns plus 25%. A track
finished at or under par earns a ★. The leaderboard ranks tracks cleared,
then stars, then actions.

**Rally-only sensors.** These don't count as actions. The missions keep the
original three sensors.

- `wall_left()`, `wall_right()`: wall beside the bot, no turning needed
- `goal_ahead()`, `goal_left()`, `goal_right()`: the goal is somewhere that way
- `distance_to_goal()`: squares to the goal, ignoring walls
- `visited_ahead()`: the bot already stood on the square in front this run

**Hints:** each league has three, from a nudge to partial code. Students open
them whenever they want; using none earns a ✦ next to their name. `/admin`
shows each student's league progress and hints used, and can unlock the next
league for one student.

### Pro reference: 3 stars

Looking sideways instead of turning to check saves actions:

```python
while not at_goal():
    if not wall_right():
        turn_right()
        move()
    elif not wall_ahead():
        move()
    else:
        turn_left()
```

It misses par on the two mirrored tracks, where the left hand is far better
(177 actions against a par of 49 on Looking Glass).

### Pro reference: 5 stars

Choose a hand once, from where the goal is, then follow it:

```python
use_right = goal_right()
while not at_goal():
    if use_right:
        if not wall_right():
            turn_right()
            move()
        elif not wall_ahead():
            move()
        else:
            turn_left()
    else:
        if not wall_left():
            turn_left()
            move()
        elif not wall_ahead():
            move()
        else:
            turn_right()
```

### Expert reference: 5/5, 3 stars

The Bug algorithm: head for the goal; when blocked, follow the wall until the
bot is closer than where it got stuck.

```python
def toward_goal():
    if goal_ahead() and not wall_ahead():
        return True
    if goal_right() and not wall_right():
        turn_right()
        return True
    if goal_left() and not wall_left():
        turn_left()
        return True
    return False

while not at_goal():
    if toward_goal():
        move()
    else:
        stuck_at = distance_to_goal()
        turn_left()
        while not at_goal() and distance_to_goal() >= stuck_at:
            if not wall_right():
                turn_right()
                move()
            elif not wall_ahead():
                move()
            else:
                turn_left()
```

It misses par on Night Garden and Deep Mirror, so strong students still have
something to optimize. Simple walk-toward-the-goal programs and "go somewhere
unvisited" explorers fail every Expert track.

## What students can write

The game accepts real Python structure around a small, safe robot API:
variables, integer math, `if`/`elif`/`else`, `for`, `while`, functions,
`return`, `break`, `continue`, Boolean logic, comparisons, comments, and now
`print("debug note")`. The program runs in a whitelist interpreter, not as
arbitrary code on the teacher’s laptop.

## Advanced lane

Offer these independently; the student can choose a direction.

1. **Efficiency:** earn par stars in the Bot Rally Pro League (see below).
2. **New algorithm:** clear the Expert League, where every wall follower fails.
3. **Clarity:** write a named helper function and explain its contract.
4. **Failure analysis:** enter Mission 3 and explain why the wall follower loops
   around the outside of the freestanding vault.
5. **Hybrid design:** use a reusable exploration phase plus a precise second
   phase that enters the vault.
6. **Black-box work:** unlock Mission 4 and use repeated runs plus `print()` to
   gather evidence before writing a final route.

Recognize at least three achievements: **most reliable**, **most efficient**,
and **clearest explanation**. That makes the skilled student visible without
making speed or code golf the only definition of skill.

## Debugging prompts that teach

Instead of fixing the line for a student, ask one of these:

- “What did you predict, and where did the trace first disagree?”
- “Is this a syntax problem or a logic problem?”
- “Which fact can the robot sense right now?”
- “What must be true every time this loop begins?”
- “Can you use `print()` to test that belief?”
- “Is this code solving this map, or this kind of problem?”

## Troubleshooting

- **A device cannot connect:** check that it is on the same Wi-Fi and that the
  full printed address includes `:8000`.
- **A student sees another name:** use **Switch driver** in the top-right.
- **A loop never ends:** the server stops after 2,000 operations, so it cannot
  freeze the teacher laptop.
- **Syntax error:** read the reported line; check the colon after
  `if`/`while`/`for`/`def` and the indentation below it.
- **The advanced student needs to skip ahead:** use `/admin`, select **Python
  Quest — Mission Control**, and unlock Mission 3 or 4 for that student.
- **Competition is distracting:** remain in Python Quest and do not project the
  Bot Rally board. Ask for an explanation instead of a rank.
- **You want short drills later:** open `/classic`; all previous worlds and
  scores are still there.

## Research basis

The lesson uses **Predict, Run, Investigate, Modify, Make (PRIMM)**: learners
read and discuss working code before taking ownership, with difficulty and
independence increasing gradually. See the Raspberry Pi Foundation’s
[PRIMM summary](https://static.raspberrypi.org/files/curriculum/quickreads/11-Pedagogy_Summary_PRIMM_V4_2023.pdf).

The Foundation’s [computing pedagogy guidance](https://www.raspberrypi.org/teach/pedagogy)
also recommends code reading/tracing, structured lessons, pair programming,
and peer discussion. Its [review of programming pedagogy](https://www.raspberrypi.org/app/uploads/2021/11/Teaching-programming-in-schools-pedagogy-review-Raspberry-Pi-Foundation.pdf)
describes explicit driver/navigator roles and cautions that pairing needs clear
implementation.

The [K–12 Computer Science Framework](https://k12cs.org/framework-statements-by-concept/)
emphasizes algorithm design, abstraction, testing, debugging, and iterative
refinement. That is why Python Quest now has a few problems that require
prediction and revision, rather than many quick route-entry levels.

