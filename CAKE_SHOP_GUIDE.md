# Cake Shop: teaching guide

Students write **one Python program that bakes the right cake for every
customer**. Each customer brings a ticket, `order`, which is a Python
dictionary: `{"name": "Priya", "flavour": "blueberry"}`. The same program runs
once per customer, so a hard-coded `layer("lemon")` makes Sam happy and Priya
says *"Layer 1 from the bottom should be blueberry, not lemon."* That moment,
when one program has to work for different inputs, is what the whole game is
about, from the very first level.

It follows Python Quest: students already know commands, loops and `def`, so
nothing here is "type commands in order". Every level teaches one real idea:
reading data, variables, joining text, loops driven by data, `if/elif`, `%`,
`in`, and `def` with parameters. The page is built to explain itself, so you
shouldn't need to introduce each part.

## Running it

It's part of the same server as everything else:

    python3 server.py

| Page | Who | What |
|---|---|---|
| `http://<your-ip>:8000/cake` | students | the game |
| `http://localhost:8000/cake/teacher` | you | who's where, who's stuck, their last error and code, the shop window |
| `http://localhost:8000/cake/show` | the projector | the class shop window, the class star meter, a live feed |

Students type their name (the same name brings back their progress) and go
straight to level 1a. Calm mode and bigger text are ticks under the name box.
The admin key printed in the terminal unlocks the teacher actions.

## What students see

The screen has two halves.

- **Left: the shop.** The customers in the queue at the top, the cake, and the
  current customer's **ticket**, written as the Python dictionary their code
  reads. **Clicking a line of the ticket puts `order["that key"]` into the
  code.** If the cursor is on a quoted word, it replaces it, so
  `layer("lemon")` becomes `layer(order["flavour"])` in one click.
- **Right: the kitchen.** From the top:
  1. **The task card.** What every cake needs ("One program, 3 customers.
     Each cake: …"), and under it the level's **NEW** idea with a small code
     example. It's open the first time, and *show/hide* folds it.
  2. **The editor.** Colour-coded, with line numbers. Every starter runs, and
     most bake correctly for at least one customer, so the first Bake! always
     shows something.
  3. **📖 Commands, flavours, colours and toppings**, folded away. Click a
     command to add it, then a flavour or colour to fill it in.
  4. **Bake!** (Ctrl+Enter), **💡 Hint** and **↺ Start again**.
  5. **Output.** `print()` output, mistakes in the code (in red, with the
     line picked out in the editor), and how the bake went: *"😕 1 of 3
     happy. Priya: …"*.

**Watching the program run.** While a cake bakes, the line of code that made
each step lights up green in the editor, and `print()` output appears as it
happens. Students can see a loop go round 100 times for Ember the dragon, an
`if` skip its lines, and a `def` run when it's called. Each customer is baked
in turn. Afterwards their face gets 😊 or 😕, and their ticket ticks off ✓ or
✗ for every part of the order. Click any customer to see their cake.

## What keeps them coding

Every reward is for writing code. Nothing is random and nothing is taken away.

- **Three stars per level**: 😊 make every customer happy, a second star (often
  **✨ your own touch**: a decoration nobody asked for, on every cake), and a
  third star for using the new idea well: `print()` each name, a variable,
  `.upper()`, "Ava is 8" (text and a number), a number worked out with `*` or
  `len()`, `elif`, compact code, or `def` with parameters. Stars add up across
  bakes. Going back for the missing star *is* the practice.
- **Unlocks.** Stars unlock new toppings, special frostings, cake stands and
  shop wallpapers (the ★ button shows them). The last few unlock for **the
  whole class together** on the class star meter (40, 120 and 240 stars).
- **Badges** for coding habits: first loop, first `if`, first list, first
  f-string, `def`, `print()`, fixing an error, **Never Give Up** (succeed
  after 5 bakes that didn't), Dragon Tamer, chapter masters, shop window ones.
- **🎨 The Studio**: free baking with every command (including `tier()` for
  tall cakes), `choice()` and `randint()`, and ready-made ideas to remix.
  **🪟 The Shop Window**: put your best Studio cake up for the class to ❤️,
  read its recipe and remix it. Fast finishers live here.
- **Sound** (🔊 mutes it), **calm mode** (no hopping, shaking, confetti or
  flickering candles; already on for computers set to reduce motion) and
  **bigger text**. The last two are ticks on the join screen and in the ★
  panel. Each browser remembers.

## The kitchen commands

All of them work from level 1a. `tier()` is for the Studio.

```python
layer("vanilla")        # add a sponge layer (bottom first)
frosting("pink")        # frost the cake
drip("chocolate")       # a drip running down the sides
sprinkles()             # rainbow sprinkles, or sprinkles("pink")
swirl("white")          # one piped swirl on the rim: loop it for a ring
topping("cherry")       # ONE topping on top: call it again for more
candle()                # one candle, or candle("blue")
write("Hi Gran")        # writing on the front of the cake
tier()                  # (Studio) start a smaller cake on top
```

The code is interpreted safely and never runs as real Python on your laptop.

## Lesson plan (about 60 minutes)

**0–5. Hook (projector).** Open 1a, press **Bake!** without changing anything.
Sam is happy and Priya isn't. Ask *"How can ONE program know what each customer
wants?"* Point at Priya's ticket. That's all the introduction it needs.

**5–35. Chapters 1–2 (the ticket, variables, text, loops from data).** Students
work on their own or in driver/navigator pairs. Things worth saying out loud
to the room as they come up:
- 1c: `"Happy Birthday" + order["name"]` with no space. Read the ✗ on the ticket.
- 2a: `range(8)` works for Ava but not Ember (100). Numbers can come from data.
- 2b: two lines inside one loop make TWO layers each time round.

**35–55. Chapters 3–4 (`if/elif`, a bug hunt, `%`, `in`).** 3c is a **bug
hunt**: the starter is a full program with two `<=` mistakes. Max is exactly
10 and Omar exactly 18. Ask *"which line made Max unhappy?"* and let them
watch the green line go through the `if`.

**55–60. Show and tell.** Put a shop window cake on the projector, or show
two different correct programs for the same level.

Chapter 5 (`def`, parameters) and the Bake-Off are for a second lesson or
fast finishers. To start a later lesson at a chapter, use **Open levels for
everyone** on the teacher page. Open student pages pick it up within 20
seconds.

## Level by level

| Level | Teaches | Starter | ★2 / ★3 | Watch for |
|---|---|---|---|---|
| 1a Flavour of the Day | `order["flavour"]`: one program, many tickets | bakes lemon for everyone: Sam is happy | own touch / `print()` each name | changing only one of the two `layer` lines |
| 1b Pick Your Colours | more keys, variables | flavour done, frosting fixed to pink | own touch / a variable | `topping(order["topping"])` |
| 1c Names on Cakes | joining text with `+` | writes "Happy Birthday Ava" on every cake | own touch / name in CAPITALS (`.upper()`) | the missing space after Birthday |
| 2a Birthday Candles | a number from the ticket in `range()` | `range(8)`: Ava happy, Ember (100) not | own touch / write "Ava is 8" | `"is " + 8`: the error suggests `str()` or an f-string |
| 2b Stripes | two lines inside one loop | one layer per stripe | own touch / write the number of layers (`* 2`) | dark before light: the ✗ names the layer |
| 2c Build Your Own | `for x in` a list from the ticket | prints the list | own touch / write how many toppings, `len()` | Bramble's empty topping list: a loop over `[]` does nothing, which is right |
| 3a Sprinkles or Not? | `if` with `True`/`False` | sprinkles for everyone | own touch / ≤ 7 lines | Sir Hoot: "NO sprinkles!" |
| 3b Party Time | `if/elif/else`, `==` | only the birthday branch | each name on the cake / uses `elif` | candles on the wedding cake |
| 3c Bug Hunt: The Age Rules | `<` vs `<=`, finding a bug | a full program with two bugs | own touch / ≤ 11 lines (needs a rethink) | Max (10) and Omar (18) are the edges |
| 4a Candy Canes | `i % 2` in a loop | prints `i, i % 2` | own touch / ≤ 9 lines | colours swapped: the first colour goes first |
| 4b Pick and Mix | `in` a list | no extras, prints the list | own touch / ≤ 10 lines | a cherry for everyone upsets Sir Hoot and Lily |
| 5a The Menu | `def` | half-written recipes | own touch / uses `def` | defining a recipe but never calling it |
| 5b Any Size | parameters | a `def` that only prints | own touch / a `def` with parameters | the numbers for each size |
| 6 The Great Bake-Off | one general program | `print(order)` | 3 happy / all 5 happy | forgetting one part of the ticket: some runs pass, some don't |

Every level has three hints, from a nudge to the full answer. After 3 bakes in
a row that don't make everyone happy, the Hint button lights up and the Output
offers "💡 Want a hint?".

## The teacher page

- **The table** is sorted with the furthest-behind first. **Tries** counts
  bakes in a row on the same level that didn't make every customer happy. The
  row turns amber at 4 and pink at 8, which is a good time to visit. **Last
  error** is the most recent error from their code.
- **👀 Code** shows the student's code for the level they're on, with the line
  their last error names picked out.
- **Open next** lets one student skip ahead. **Open levels for everyone** does
  it for the class.
- **Shop window theme** shows in the window and on the projector.
- **In the shop window**, **Hide** takes a cake out of the window at once.

## Troubleshooting

- *"It worked for one customer but not the others."* That's the point. Click
  the unhappy customer at the top of the shop: their ticket says what their
  code read, and the ✗ says what was wrong.
- *"Where do I see my mistake?"* In red at the bottom of the kitchen (the
  Output), and the line is marked red in the editor.
- *A student lost their code.* It's saved in their browser and on the server
  with each bake. Joining with the same name brings it back. **Ctrl+Z** undoes
  anything, including ↺ Start again.
- The game keeps everyone's progress in `scores.json` with the other games.

## Answers

One way to earn all three stars on each level (there are others, and
students' own versions are often nicer).

<details><summary><b>1a Flavour of the Day</b></summary>

```python
layer(order["flavour"])
layer(order["flavour"])
frosting("white")
sprinkles()
print(order["name"])
```
</details>

<details><summary><b>1b Pick Your Colours</b></summary>

```python
flavour = order["flavour"]
layer(flavour)
layer(flavour)
frosting(order["frosting"])
topping(order["topping"])
sprinkles()
```
</details>

<details><summary><b>1c Names on Cakes</b></summary>

```python
layer(order["flavour"])
layer(order["flavour"])
frosting("pink")
name = order["name"].upper()
write("Happy Birthday " + name)
topping("heart")
```
</details>

<details><summary><b>2a Birthday Candles</b></summary>

```python
layer(order["flavour"])
layer(order["flavour"])
frosting("pink")
for i in range(order["age"]):
    candle()
name = order["name"]
age = order["age"]
write(f"{name} is {age}")
sprinkles()
```
</details>

<details><summary><b>2b Stripes</b></summary>

```python
for i in range(order["stripes"]):
    layer(order["dark"])
    layer(order["light"])
frosting("white")
write(order["stripes"] * 2)
swirl("black")
```
</details>

<details><summary><b>2c Build Your Own</b></summary>

```python
for flavour in order["layers"]:
    layer(flavour)
frosting(order["frosting"])
for t in order["toppings"]:
    topping(t)
write(len(order["toppings"]))
sprinkles()
```
</details>

<details><summary><b>3a Sprinkles or Not?</b></summary>

```python
for i in range(2):
    layer(order["flavour"])
frosting("white")
if order["sprinkles"]:
    sprinkles()
topping("strawberry")
```
</details>

<details><summary><b>3b Party Time</b></summary>

```python
layer(order["flavour"])
layer(order["flavour"])
if order["party"] == "birthday":
    frosting("pink")
    for i in range(order["age"]):
        candle()
elif order["party"] == "wedding":
    frosting("white")
    topping("heart")
    topping("heart")
else:
    frosting("yellow")
    topping("flower")
write(order["name"])
```
</details>

<details><summary><b>3c Bug Hunt: The Age Rules</b></summary>

```python
for i in range(2):
    layer(order["flavour"])
frosting("white")
age = order["age"]
if age < 18:
    sprinkles()
if age >= 10:
    drip("chocolate")
if age >= 18:
    topping("cherry")
swirl("pink")
```
</details>

<details><summary><b>4a Candy Canes</b></summary>

```python
for i in range(2):
    layer("vanilla")
frosting("white")
for i in range(order["swirls"]):
    if i % 2 == 0:
        swirl(order["first"])
    else:
        swirl(order["second"])
topping("star")
```
</details>

<details><summary><b>4b Pick and Mix</b></summary>

```python
layer(order["flavour"])
layer(order["flavour"])
frosting("white")
if "sprinkles" in order["extras"]:
    sprinkles()
if "drip" in order["extras"]:
    drip("chocolate")
if "cherry" in order["extras"]:
    topping("cherry")
swirl("pink")
```
</details>

<details><summary><b>5a The Menu</b></summary>

```python
def choco_bomb():
    for i in range(3):
        layer("chocolate")
    frosting("chocolate")
    for i in range(6):
        topping("cherry")

def lemon_cloud():
    layer("lemon")
    layer("lemon")
    frosting("white")
    sprinkles("yellow")

if order["cake"] == "Choco Bomb":
    choco_bomb()
else:
    lemon_cloud()
write("Enjoy!")
```
</details>

<details><summary><b>5b Any Size</b></summary>

```python
def cake(layers, swirls):
    for i in range(layers):
        layer(order["flavour"])
    frosting("white")
    for i in range(swirls):
        swirl("pink")

if order["size"] == "small":
    cake(2, 6)
elif order["size"] == "medium":
    cake(3, 8)
else:
    cake(4, 10)
topping("bow")
```
</details>

<details><summary><b>6 The Great Bake-Off</b></summary>

```python
for flavour in order["layers"]:
    layer(flavour)
frosting(order["frosting"])
if order["drip"] != "":
    drip(order["drip"])
if order["sprinkles"]:
    sprinkles()
for i in range(order["candles"]):
    candle()
for t in order["toppings"]:
    topping(t)
if order["message"] != "":
    write(order["message"])
```
</details>
