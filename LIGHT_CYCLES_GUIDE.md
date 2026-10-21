# Light Cycles: a 60-minute lesson

Light Cycles is a Tron-style battle royale. Each student writes **one
function**, `steer()`. The game calls it every turn and the function
**returns** `"left"`, `"right"` or `"straight"`. Every cycle leaves a solid
trail of light. Hit a wall or any trail and you're out. Last cycle riding wins.

It's new to students in two ways:

- **The game calls their function.** In the missions and Bot Rally, students
  call commands (`move()`). Here, their function answers a question. That
  makes `return` values the core idea.
- **Their code races their classmates' code.** You project rounds where every
  student's bot rides in the same arena at once.

## Setup

1. Run `python3 server.py` as usual (same Wi-Fi, no internet needed).
2. Students open **`http://<your-ip>:8000/cycles`**. The banner prints the
   full address. They join with the same name they used in Python Quest.
3. Project **`http://localhost:8000/cycles/show`**. It shows the student
   address in the header. Type the admin key from the terminal banner once.
   The page remembers it.

How it works:

- **Test drive** (student page) races their bot against three house bots,
  Rex, Cora and Hugo, in three heats. It shows a replay, the crash cause and
  their `print()` output.
- **The code a student last test-drove is their entry** for the next class
  battle. No separate submit step.
- **▶ Start round** (projector) puts every entered bot in one arena. A round
  replays in about 20 seconds with name tags and a crash feed. **Skip** jumps
  to the end.
- **Season points:** one point for every rider you outlast, added up over
  rounds. **Reset season** sets them back to 0, e.g. for your next class.
- Students can watch the last round on their own screen. The left sidebar
  has a **Round N replay** button, and it shows only that student's own
  `print()` output.

## The one-hour plan

| Time | Phase | Teacher move | Student work |
|---|---|---|---|
| 0–5 | Hook | Project `/cycles/show`. Explain the rules in one breath: always moving, trails are walls, last one riding wins. | Join `/cycles`. |
| 5–10 | Predict | Everyone clicks **Load starter**. Ask: "Who calls `steer()`? What does `return` do with the word?" Predict what the starter does. | Predict, then Test drive. It crashes straight into the wall. |
| 10–18 | Modify | Add `if wall_ahead(): return "left"`. Test. "Why did it still crash?" (It turned left into a wall.) | Fix it with `elif`/nested `if`. Goal: **SURVIVOR** badge. |
| 18–21 | **Round 1** | Start a round now, even with weak bots. It's the hook for the rest of the hour. | Watch, cheer, read the crash feed. |
| 21–33 | Make | Open the *Sensors* drawer. Introduce number sensors: compare `space_left()` with `space_right()`. Show `print()` for debugging. | Goals: **PODIUM**, then **CHAMPION**. |
| 33–36 | **Round 2** | Before you start: "What did you change, and why should it help?" | Watch their own replay afterwards. |
| 36–50 | Improve | Students choose: beat all three heats (**SWEEP**), study why they crashed in the class battle, or (advanced) use `global` to remember things between turns. | Iterate: predict → test → read the replay. |
| 50–55 | **Final round** | Run 1–2 rounds. | |
| 55–60 | Debrief | Ask the winner and one "most improved" student to explain one decision in their code. | Exit sentence: "`return` sends back… The game calls my function because…" |

Tip: run rounds often. Each one is a natural checkpoint and a reason to
improve the code.

## Answer key

**SURVIVOR** (last 30 turns in every heat): check before turning.

```python
def steer():
    if wall_ahead():
        if wall_left():
            return "right"
        return "left"
    return "straight"
```

This also earns **PODIUM** (2nd place in two heats).

**CHAMPION** (win a heat). The house bot Cora is a good reference: always
take the way with the most room. She wins two of the three heats.

```python
def steer():
    ahead = space_ahead()
    left = space_left()
    right = space_right()
    if ahead >= left and ahead >= right:
        return "straight"
    if left > right:
        return "left"
    return "right"
```

**SWEEP** (win all three heats). The insight: Cora turns every time a side
looks a little bigger. She zigzags and walls herself in. Don't turn while
there's plenty of room ahead:

```python
def steer():
    a = space_ahead()
    l = space_left()
    r = space_right()
    if a > 8 or (a > 0 and a >= max(l, r)):
        return "straight"
    if l >= r:
        return "left"
    return "right"
```

Good discussion point: this bot wins every practice heat but **does not
always win the class battle.** Other students' bots make the arena
different from the practice heats. Testing against one opponent isn't
testing against everyone.

## What students can write

`def`, `return`, `if`/`elif`/`else`, `while`, `for i in range(n)`, variables,
whole-number math, `and`/`or`/`not`, comparisons, text in quotes, `print()`,
`max()`, `min()`, `abs()`, their own helper functions, and `global`. It runs
in the same kind of safe whitelist interpreter as the missions. No imports,
nothing touches your laptop.

Sensors (`wall_*` and `space_*`) look from the cycle's point of view: left
means the cycle's left.

To remember things between turns, students need `global`, just like real
Python:

```python
turns = 0

def steer():
    global turns
    turns += 1
    print("turn", turns, "room ahead", space_ahead())
    return "straight"
```

## Common errors (and what the game says)

| Student writes | What happens |
|---|---|
| No `return`, or `return` only inside an `if` | A one-time warning, `steer() returned None`, and the cycle goes straight. |
| `return left` (no quotes) | `Put quotes round words: return "left"` |
| `return "Left"` | Warning that `'Left'` isn't an option, and it goes straight. Text is case-sensitive. |
| `turn_left()` (from the missions) | Explains that `steer()` returns a direction instead. |
| `count += 1` inside `steer()` without `global` | Explains that it needs `global count`. |
| A `while` loop that never ends | Crashes that turn: "steer() took too long to decide". |
| Syntax error | The cycle never starts. The crash feed on the projector shows the line number, so check the console. |

## Troubleshooting

- **A student isn't in the battle:** they must press **Test drive** at least
  once. The projector lists everyone entered before you press Start.
- **A student's bot crashes at turn 0 in the battle:** their last test-drive
  code has an error. They fix it and test again before the next round.
- **Wrong admin key:** it's printed in the terminal banner when the server
  starts.
