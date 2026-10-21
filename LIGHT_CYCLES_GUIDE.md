# Light Cycles: the 60-minute lesson script

Each student writes **one function**, `steer()`. The game calls it every
turn, and it **returns** `"left"`, `"right"` or `"straight"`. Cycles never
stop, trails are walls, last cycle riding wins. Two ideas are new: **the game
calls their function** (so `return` is the whole point), and **left/right are
the cycle's, not the screen's**. This script is built around those two.

## 5-minute pre-class checklist

- [ ] `python3 server.py`. Note the **admin key** and the student address in
      the banner (`http://<ip>:8000/cycles`).
- [ ] Project **`http://localhost:8000/cycles/show`** and type the admin key
      once (it's remembered). The header shows the student address.
- [ ] On a student laptop, open `/cycles`, join as "Test", **Load starter**,
      **Test drive**. You should see 3 heats and a replay.
- [ ] Start one round on the projector to check it plays (3-2-1, then up to
      about 20 s). Then **Reset season** so the class starts at 0.
- [ ] Print the cheat sheet: the link under the join form on `/cycles`
      (or 🖨 in the *Sensors* drawer). One A4 page, one per pair.
- [ ] Clear a space at the front for the warm-up.

## The words to use

| Idea | Say this |
|---|---|
| The game calls `steer()` | "The game is the driving instructor. Every turn it asks your `steer()` *'Which way?'*, and `return` is your function saying the answer out loud." |
| You never call it | "You don't run `steer()`. You write the answer. The game asks, every turn, all game long." |
| `print` vs `return` | "`print()` is talking to yourself. The instructor never hears it. Only `return` answers." |
| Relative left/right | "Left means **the cycle's** left. Pretend you're riding it. Look at the arrow on its head." |
| Trails | "Your cycle never stops, and every square it drives over becomes a wall. Even for you." |

## Warm-up: be the cycle (3 min)

1. A volunteer is the cycle. They take one step per clap and may only turn
   when the class shouts a return value.
2. Class shouts `"straight"`, `"straight"`, `"left"`. Have the volunteer
   **face the class** first, so their left is the class's right. Ask
   "Whose left?" Answer: *the cycle's*.
3. Put a chair in front of them: "What should `steer()` return now?" Then
   ask how the cycle *knows* there's a chair. That's `wall_ahead()`.

## Minute-by-minute plan (PRIMM)

| Min | Phase | You | Students (in pairs) |
|---|---|---|---|
| 0–3 | Hook | Project `/cycles/show`. Rules in one breath. | Join `/cycles`. Read the 3-step "How it works" card. |
| 3–6 | Warm-up | *Be the cycle* (above). | Shout return values. |
| 6–10 | **Predict** | "Load starter. Don't run it yet. What will it do? Who calls `steer()`?" | Write a one-line prediction. |
| 10–12 | **Run** | "Test drive." | The starter rides into a wall in every heat (4th, 4th, 4th). |
| 12–18 | **Investigate** | Point at the arrow on each head and the left/right key under the replay. "When it faces right, which way is its left?" (Up the screen.) | Watch the replay. Tick *show on the map*. Read the crash cause in the output. |
| 18–25 | **Modify** | "Add `if wall_ahead(): return "left"`." Then: "Why might it still crash?" (It can turn left into a wall.) | Goal: **SURVIVOR** (PODIUM comes with it). |
| 25–28 | **Round 1** | Start a round now, even with weak bots. | Watch, cheer, find their own cycle. |
| 28–42 | **Make** | Number sensors: compare `space_left()` with `space_right()`. Show `print()` for debugging: pause the replay (⏸, then −1 / +1) and that turn's print lines light up. | Goals: **CHAMPION**, then **SWEEP**. Hints in *Challenges*. |
| 42–45 | **Round 2** | Before you start: "What did you change, and why should it help?" | Watch, then open *Round 2 replay* on their own page. |
| 45–53 | Improve | Lanes (below). | Predict → test → read the replay. The line under the badges says if the new bot beat their last one. |
| 53–56 | **Final round** | 1–2 rounds. | |
| 56–60 | Debrief | The winner and one "most improved" explain one decision in their code. | Exit sentence: "`return` sends back… The game calls my function because…" |

## Pair programming

- **Driver** types. **Navigator** watches the replay and the output, says
  what to try next, and holds the cheat sheet.
- **Swap at every Test drive.** That's a swap every few minutes, in line
  with the usual 5–10 minute advice.

## Battle rounds

- Run them **often**: around minutes 25, 42 and 53. Each takes under half a
  minute. Start Round 1 before bots are good: it's the hook.
- **A student's entry** is their last test drive **whose code loaded**. If a
  later test drive has a code error, the previous working bot stays entered.
  Their page says which, under the Test drive button ("✅ Entered for the
  next battle", or "⚠️ This code has an error. Your previous working bot is
  still entered"). Clicking that line shows the entered code.
- With **two riders left**, playback speeds up 4× and a *FINAL TWO* banner
  names them.
- If a round hits its time limit with several cycles still riding, they
  **share the win** ("time's up").
- Code errors show on the projector only as "had a code error. Check your
  console!" The details are on that student's own page.

## Three lanes

| Lane | Who | Task |
|---|---|---|
| Struggling | Still mixing up return or left/right | *Challenges* → SURVIVOR → Hint 1, 2, 3 (Hint 3 is fill-in-the-blanks). Tick *show on the map*. |
| Core | Has SURVIVOR | CHAMPION: compare `space_left()` and `space_right()` before turning. |
| Advanced | Has CHAMPION | SWEEP, then the class battle: "Your bot sweeps practice. Why doesn't it always win the battle?" Try `global` counters and helper `def`s. |

Hints are free and each one opens the next. Every hint skeleton was tested
on the real game.

## Misconceptions → what to say

| You see | Say |
|---|---|
| "It turned the wrong way!" | "Whose left? Look at the arrow. When it faces right on the screen, its left is **up**." Point at the left/right key. |
| `print("left")` instead of `return "left"` | "`print` talks to you. The game only hears `return`." |
| `return left` or `return "Left"` | "Words need quotes, and lowercase. The game knows exactly three words." |
| `if wall_ahead:` (no brackets) | "A sensor is a question you ask. Asking needs `( )`." |
| Calls `steer()` themselves | "The game calls it. You only write the answer." |
| `move()` / `turn_left()` from the missions | "No commands here: your cycle always moves. You **answer** with return." |
| Turns at every wall without looking | "You turned left into another wall. Check `wall_left()` first." |

## What the game says (in the student's output)

| Student writes | The game says |
|---|---|
| No `return`, or one only inside an `if` | `⚠️ steer() returned None. Return "left", "right" or "straight" — going straight.` (once, then it goes straight) |
| `return left` | `Put quotes round words:  return "left"` |
| `return "Left"` | `⚠️ steer() returned 'Left'. …going straight.` |
| `turn_left()` | `There's no turn_left() in Light Cycles. Your cycle always moves…` |
| `count += 1` in `steer()` without `global` | `'count' is a variable from the top of your program… put  global count  as the function's first line.` |
| A `while` loop that never stops | `steer() took too long to decide — is a while loop stuck going round forever?` |
| Missing `:`, bad indent, `print "hi"` | `Syntax error on line N: …` The cycle never starts (out on turn 0). |
| Misspelled sensor (`space_ahaed()`) | `I don't know the command 'space_ahaed'. Check the sensor list…` |
| No `def steer():` | `Your program needs a  def steer():  that returns "left", "right" or "straight".` |

## Answer keys (checked on the real game)

**Starter** (`return "straight"`): 4th in all three heats, no badges.

**SURVIVOR + PODIUM** (2nd, 2nd, 3rd). Plain `if wall_ahead(): return "left"`
already earns both. The safer version:

```python
def steer():
    if wall_ahead():
        if wall_left():
            return "right"
        return "left"
    return "straight"
```

**CHAMPION** (2nd, 1st, 3rd): when you must turn, take the roomier side.

```python
def steer():
    if wall_ahead():
        if space_left() > space_right():
            return "left"
        return "right"
    return "straight"
```

**SWEEP** (1st, 1st, 1st): don't turn while there's lots of room ahead.
Turning whenever one side looks a bit bigger zigzags you into a corner.

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

The 8 matters: 6, 7 or 8 sweep, much bigger numbers don't. Discussion
point: this bot sweeps practice but **doesn't always win the class battle**.
Testing against three bots isn't testing against everyone.

## Troubleshooting

| Problem | Fix |
|---|---|
| A student isn't in the battle | They must **Test drive** once with code that loads. The projector lists everyone entered before you press Start. |
| "had a code error" on the projector | Their entered bot can't run. They read their own output, fix it, and test drive again. |
| Wrong admin key | It's in the terminal banner, and stays the same after a restart. |
| "A round is already running" | Wait for it to finish: one round at a time. |
| Server restarted mid-lesson | Points, the round number and the last replay are saved. Students reload the page. |
| The "How it works" card keeps coming back | That browser blocks storage (e.g. a private window). Close it with the button. Harmless. |
| New class, fresh scores | **Reset season** on the projector page. |
