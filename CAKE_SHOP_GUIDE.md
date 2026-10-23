# Cake Shop: teaching guide (about 3 lessons)

Students run a bakery. Customers come in with orders, and students write
Python that bakes the cake. The cake builds itself on the counter one step at
a time, and the customer reacts. They're either delighted, or politely puzzled
(*"Layer 2 from the bottom should be strawberry, not lemon."*). That reaction
is the debugging feedback, so students learn to **read what went wrong and fix
it**.

It was made for the students who find "get the robot to the exit" pointless.
Here the goal is to make something lovely for someone, and there's room to be
creative at every step. It needs no Python beforehand: Chapter 1 starts from
a single line of code.

## Running it

It's part of the same server as everything else:

    python3 server.py

| Page | Who | What |
|---|---|---|
| `http://<your-ip>:8000/cake` | students | the game |
| `http://localhost:8000/cake/teacher` | you | who's where, who's stuck, their last error, the shop window |
| `http://localhost:8000/cake/show` | the projector | the class shop window as a slideshow, the class star meter, a live feed |

Students join with their name, as in the other games (the same name brings
back their progress), then name their bakery. The admin key printed in the
terminal unlocks the teacher actions.

## What students see

- **The shop.** The customer stands at the counter with a speech bubble
  saying what they want. A chalkboard shows the chapter or the shop's **house
  rules**, and a pinned **ticket** shows the order. From Chapter 3 that's the
  actual Python dictionary, `order = {...}`.
- **The kitchen** (on the right). There's a **Chef's tip** with an example of the
  level's new idea, the editor (colour-coded, with line numbers), a **recipe
  book** of commands to click, and an **ingredients** list of flavours, colours
  and toppings (click to type one in). Then come **Bake!** (Ctrl+Enter), **hints**,
  and the **Kitchen notes**, where `print()` output and errors appear.
- **Baking.** Each command is a step: layers drop in, frosting spreads,
  sprinkles rain down, candles pop up and flicker, writing appears on the front
  of the cake. After that the customer hops for joy or looks puzzled. The ticket
  then ticks off ✓ or ✗ every part of the order, so students can see *exactly*
  what's wrong.
- **Queues** (Chapter 3 onwards). The same program bakes for 3–5 customers with
  different tickets. A hard-coded program makes the first customer happy and
  the next one says *"I wanted blueberry, not lemon"*. That moment is the
  lesson. Click a customer at the top to see their cake and ticket.

## What keeps them coding

Every reward is for writing code. Nothing is random and nothing is taken away.

- **Three stars per level**: 😊 make every customer happy, a level-specific
  second star, and a third star for compact code or for using the new idea
  (a variable, `elif`, `def`, parameters). Stars add up across bakes, so a
  student can get them in different runs. Going back for the missing star *is*
  the practice.
- **✨ Your own touch.** On most levels the second star is for adding a
  decoration the customer *didn't* ask for, like sprinkles, a swirl or a topping.
  Creativity is part of the score. (On rush levels it has to be on every cake,
  which nudges them to add it outside any `if`.)
- **Unlocks.** Stars unlock new toppings (🦋 👻 🎃 🌈 👑 🦄 💎 …), special
  frostings (✨ glitter, 🌌 galaxy, 🌈 rainbow, 🥇 gold), cake stands and shop
  wallpapers. The ★ button at the top shows them all. The last few unlock for
  **the whole class together** on the class star meter (40, 120 and 240
  stars), which the projector shows.
- **Badges** for coding habits: first loop, first `if`, first list, first
  f-string, a recipe made with `def`, `print()`, fixing an error, **Never Give
  Up** (succeed after 5 bakes that didn't), Dragon Tamer, putting a cake in
  the window, giving and getting hearts, chapter masters.
- **🎨 The Studio.** Free baking with every command, plus `choice()` and
  `randint()` for surprise cakes (🎲 Again re-bakes with new random picks).
  Fast finishers live here.
- **🪟 The Shop Window.** Students name their best Studio cake and put it in
  the window. Classmates can ❤️ it, open it to **read its recipe**, and
  **Remix it** into their own Studio. Reading each other's code is a great
  habit to encourage.
- **Sound.** Every step makes a small sound. 🔊 at the top mutes it (each
  browser remembers). Headphones help in a full room.

## The kitchen commands

```python
layer("vanilla")        # add a sponge layer (bottom first)
frosting("pink")        # frost the cake (top and between the layers)
drip("chocolate")       # a drip running down the sides
sprinkles()             # rainbow sprinkles, or sprinkles("pink")
swirl("white")          # one piped swirl on the rim — loop it for a ring
topping("cherry")       # ONE topping on top — call it again for more
candle()                # one candle, or candle("blue")
write("Hi Gran")        # writing on the front of the cake (40 letters max)
tier()                  # start a smaller cake on top (Chapter 6)
```

Colours can also be hex codes like `"#ff88cc"`. The Python that works:
variables, `+ - * // %`, text with `+`, f-strings, `str()` `int()` `len()`,
lists (`[ ]`, `for x in list`, `.append()`, `[0]`, `[1:]`), dictionaries
(`order["name"]`), `if/elif/else`, `and/or/not`, `in`, `for`, `while`,
`def` with parameters and `return`, `print()`, and `.upper() .lower()
.title() .replace()` on text. There are no imports. Like the other games, the
code is interpreted safely and never runs as real Python on your laptop.

## Lesson plan

**Lesson 1: Chapters 1–2 (commands, text, `for` loops).** Do level 1a together
on the board. Granny Rose's starter already has one line; ask *"what's missing?"*
Then let them go. Point out the ticket ticks: *"which line made that ✗?"*. Ember
the dragon (100 candles) is the moment loops click. Finish with 10 minutes of
Studio and the first shop window cakes on the projector.

**Lesson 2: Chapters 3–4 (dictionaries, `if/elif/else`).** Open on the
projector with level 3a: run a program that says `layer("lemon")` and let
the class watch Priya's face. *"How can ONE program know what each customer
wants?"* Then `print(order)`. Chapter 4's **Age Rules** (4c) is a great
discussion: Max is exactly 10 and Omar exactly 18. *Which group are they in,
and which comparison puts them there?*

**Lesson 3: Chapters 5–6 and the Bake-Off (`%`, lists, functions).** 5a
(`i % 2`) is worth a demo: `print(i, i % 2)` in the Studio. The Bake-Off is the
finale. Five random customers each bake, so only a program that reads every
part of the ticket gets all five. Fast finishers: Studio and a themed window.

If a class needs to start at a later chapter, use **Open levels for
everyone** on the teacher page.

## Level by level

| Level | Teaches | ★2 / ★3 | Watch for |
|---|---|---|---|
| 1a Granny Rose | one command per line, quotes | own touch / `print()` | `layer(chocolate)` without quotes (the error says so) |
| 1b Leo | order matters (first layer = bottom) | own touch / write LEO | layers in the wrong order: the ticket's ✗ names the layer |
| 1c Captain Whiskers | drips, toppings, `write()` | own touch / ≤ 9 lines | `topping("fish")` once, not three times |
| 2a Ava turns 8 | `for i in range(8):` | own touch / ≤ 7 lines | `write()` pushed into the loop (it writes 8 times, harmlessly, but it's a good talk) |
| 2b Ember the dragon | loops for anything | own touch / ≤ 8 lines | typing candles by hand; the ≤ 8 lines star needs a loop for the layers too |
| 2c Zoe's stripes | two lines inside one loop | own touch / ≤ 7 lines | `range(8)` with two layers inside makes 16 |
| 3a Flavour of the day | `order["flavour"]`, variables | own touch / a variable | hard-coding `"lemon"`: only Sam is happy |
| 3b Birthday rush | `range(order["age"])`, joining text | own touch / ≤ 8 lines | `"Happy Birthday" + name` with no space |
| 3c Party planner | f-strings or `str()` | name in CAPITALS (`.upper()`) / ≤ 6 lines | `"is " + order["age"]` (text + number): the error suggests `str()` |
| 4a Sprinkles or not? | `if` with True/False | own touch / ≤ 7 lines | sprinkles for everyone: Sir Hoot complains |
| 4b Party time | `if/elif/else`, `==` | write each name / uses `elif` | candles on the wedding cake ("Candles? It isn't my birthday!") |
| 4c Age rules | `<`, edges of ranges | own touch / ≤ 13 lines | `age <= 10` gets Max wrong |
| 5a Penguin Pete | `i % 2` | own touch / ≤ 9 lines | red/white swapped: red comes first |
| 5b Rainbow the unicorn | lists, `for x in list` | own touch / ≤ 8 lines | flavours vs colours (`layer("red")` explains the difference) |
| 5c Build your own | lists inside the ticket, `len()` | write the layer count / ≤ 6 lines | Bramble's empty topping list (a loop over `[]` does nothing, which is right) |
| 6a The menu | `def` | own touch / uses `def` | defining the recipe but never calling it |
| 6b Any size | parameters | own touch / a `def` with parameters | the sizes' numbers |
| 6c Wedding bells | `tier()`, functions + lists | own touch / ≤ 15 lines | writing the names on the top tier instead of the bottom |
| 7 The Great Bake-Off | one general program | 3 happy / all 5 happy | forgetting one part of the ticket: some runs pass, some don't |

Every level has three hints that go from a nudge to the full answer, and the
teacher page counts the hints each student opens. A student on their 3rd bake
in a row without success gets a "💡 Want a hint?" nudge.

## The teacher page

- **The table** is sorted with the furthest-behind first. **Tries** counts
  bakes in a row on the same level that didn't make every customer happy. The
  row turns amber at 4 and pink at 8, which is a good time to visit. **Last error** is
  the most recent error from their code.
- **Open next** lets one student skip ahead.
- **Shop window theme** shows at the top of the window and on the projector.
  Halloween idea: *"Spooky cakes 🎃"* (the ghost and pumpkin toppings unlock at
  4 and 6 stars).
- **In the shop window.** Everything written on a cake is visible to the class.
  **Hide** takes a cake out of the window at once. The student can put up a
  new one.

## Troubleshooting

- *"My code worked for one customer but not the others."* That's the point of
  Chapter 3 onwards. Click the unhappy customer at the top of the shop to see
  their ticket and what they said.
- *"It says 🔒 … unlocks at 12 stars."* Locked toppings and frostings work
  everywhere once unlocked. Stars come from levels.
- *A student lost their code.* It's saved in their browser and on the server
  with each bake. Joining with the same name brings it back.
- The game keeps everyone's progress in `scores.json` with the other games.

## Answers

One way to earn all three stars on each level (there are others, and
students' own versions are often nicer).

<details><summary><b>1a Granny Rose</b></summary>

```python
layer("chocolate")
layer("chocolate")
frosting("white")
sprinkles()
print("Enjoy your cake, Granny!")
```
</details>

<details><summary><b>1b Leo's Sandwich Cake</b></summary>

```python
layer("vanilla")
layer("strawberry")
layer("vanilla")
frosting("pink")
topping("cherry")
write("LEO")
```
</details>

<details><summary><b>1c Captain Whiskers</b></summary>

```python
layer("lemon")
layer("lemon")
frosting("white")
drip("chocolate")
topping("fish")
topping("fish")
topping("fish")
write("MEOW")
sprinkles("blue")
```
</details>

<details><summary><b>2a Ava Turns 8</b></summary>

```python
layer("strawberry")
layer("strawberry")
frosting("pink")
for i in range(8):
    candle()
write("Happy Birthday Ava")
swirl("white")
```
</details>

<details><summary><b>2b Ember the Dragon</b></summary>

```python
for i in range(3):
    layer("chocolate")
frosting("orange")
for i in range(100):
    candle()
for i in range(10):
    topping("coin")
drip("red")
```
</details>

<details><summary><b>2c Zoe Loves Stripes</b></summary>

```python
for i in range(4):
    layer("chocolate")
    layer("vanilla")
frosting("white")
for i in range(12):
    swirl("black")
topping("star")
```
</details>

<details><summary><b>3a Flavour of the Day</b></summary>

```python
flavour = order["flavour"]
layer(flavour)
layer(flavour)
frosting("white")
topping("heart")
```
</details>

<details><summary><b>3b Birthday Rush</b></summary>

```python
layer(order["flavour"])
layer(order["flavour"])
frosting("pink")
for i in range(order["age"]):
    candle()
write("Happy Birthday " + order["name"])
sprinkles()
```
</details>

<details><summary><b>3c Party Planner</b></summary>

```python
for i in range(order["layers"]):
    layer(order["flavour"])
frosting(order["frosting"])
name = order["name"].upper()
age = order["age"]
write(f"{name} is {age}")
```
</details>

<details><summary><b>4a Sprinkles or Not?</b></summary>

```python
for i in range(2):
    layer(order["flavour"])
frosting("white")
if order["sprinkles"]:
    sprinkles()
topping("strawberry")
```
</details>

<details><summary><b>4b Party Time</b></summary>

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

<details><summary><b>4c The Age Rules</b></summary>

```python
layer(order["flavour"])
layer(order["flavour"])
frosting("white")
age = order["age"]
if age < 10:
    sprinkles()
elif age < 18:
    sprinkles()
    drip("chocolate")
else:
    drip("chocolate")
    topping("cherry")
swirl("pink")
```
</details>

<details><summary><b>5a Penguin Pete</b></summary>

```python
for i in range(2):
    layer("vanilla")
frosting("white")
for i in range(12):
    if i % 2 == 0:
        swirl("red")
    else:
        swirl("white")
topping("star")
```
</details>

<details><summary><b>5b Rainbow the Unicorn</b></summary>

```python
layers = ["cherry", "orange", "lemon", "lime", "blueberry", "grape"]
colours = ["red", "orange", "yellow", "green", "blue", "purple"]
for flavour in layers:
    layer(flavour)
frosting("white")
for colour in colours:
    swirl(colour)
sprinkles()
```
</details>

<details><summary><b>5c Build Your Own</b></summary>

```python
for flavour in order["layers"]:
    layer(flavour)
frosting(order["frosting"])
for t in order["toppings"]:
    topping(t)
write(len(order["layers"]))
```
</details>

<details><summary><b>6a The Menu</b></summary>

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

<details><summary><b>6b Any Size</b></summary>

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

<details><summary><b>6c Wedding Bells</b></summary>

```python
def one_tier(flavour):
    layer(flavour)
    layer(flavour)
    frosting("white")
    for i in range(8):
        swirl("white")

flavours = order["flavours"]
one_tier(flavours[0])
write(order["names"])
for flavour in flavours[1:]:
    tier()
    one_tier(flavour)
for i in range(2):
    topping("heart")
sprinkles("white")
```
</details>

<details><summary><b>7 The Great Bake-Off</b></summary>

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

