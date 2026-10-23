# Cake Shop: design and build plan

Students run a bakery. Customers walk in with orders, and students write
Python that bakes and decorates the cake, layer by layer. The cake builds
itself on screen, one command at a time, and the customer reacts: delighted,
or politely puzzled ("I asked for 3 layers, but this has 2!"). That reaction
is the debugging feedback.

Made for the students who find "get the robot to the exit" pointless: the
goal is to **make something lovely for someone**, and there's room to be
creative at every step.

## What makes it fun

- **Customers with personality.** Granny Rose, Sir Hoot the owl who hates
  sprinkles, a dragon turning 100 (100 candles, and only a loop will do), a
  zebra who wants stripes, a penguin who wants candy-cane swirls.
- **A big, pretty cake** that builds step by step: layers drop in, frosting
  spreads, sprinkles rain down, candles pop up and flicker, writing appears.
  Every step has a sound.
- **Your own touch** ✨: on most levels one star is for adding a decoration the
  customer *didn't* ask for. Being creative is part of the score.
- **Unlocks**: stars unlock new toppings (butterflies, ghosts, crowns,
  unicorns…), special frostings (glitter, galaxy, rainbow) and the look of
  your shop (cake stand, wallpaper). The class unlocks the last few together.
- **Name your bakery** (✎ at the top): it shows on your page, in the shop window and on the projector.
- **Studio and the Shop Window**: free baking with everything unlocked, then
  put your best cake in the class shop window. Classmates can ❤️ it, view its
  recipe (code) and remix it.
- **Projector page**: the shop window as a slideshow, the class star meter and
  a live feed ("🐉 Mia made Ember the dragon very happy").

## Every level is one program for many customers (Oct 2026 rework)

The first version opened with two chapters of typing commands in order and
fixed-count loops, which students had already done in Python Quest, so the
programming only started at level 7. Now every level, from 1a, is a queue of
customers with tickets (`order`, a dictionary), and the SAME program bakes for
each. A hard-coded value pleases one customer and not the next, in plain sight.

- **Each starter runs**, and usually bakes right for one customer, so the
  first Bake! shows what's left to do. 1a's starter is the hard-coded answer
  for Sam; 2a's is `range(8)` with Ember turning 100; 3c's is a whole program
  with two `<=` bugs (a bug hunt).
- **One new idea per level**, on the task card with a short example, and three
  hints that go from a nudge to the answer.
- **The page explains itself**: no welcome card or shop-name step; one task
  card (the rules and the new idea), one ticket (as Python; click a line to
  insert `order["key"]`), one Output (prints, errors, how the bake went).
- **Watching the program run**: every bake step records its code line, and
  the editor lights that line up as the cake builds; prints appear as they run.
- Error messages are friendly and say what to type, and the customer says
  exactly what's wrong, so students debug by reading.

## The Python it uses

| Idea | Where |
|---|---|
| Dictionaries: `order["flavour"]`, one program for many inputs | Ch 1 (1a) |
| Variables, joining text, `.upper()` | Ch 1 |
| `range()` from ticket numbers, loop bodies, `for x in list`, `len()`, `*` | Ch 2 |
| `if` on `True`/`False`, `if/elif/else`, `==`, `<` vs `<=` (a bug hunt) | Ch 3 |
| `i % 2`, `in` | Ch 4 |
| `def` with and without parameters | Ch 5 |
| One general program for any order | Bake-Off |
| `choice()`, `randint()`, `tier()` | Studio |

## The kitchen commands

```
layer("vanilla")        add a sponge layer (bottom first)
frosting("pink")        frost the cake (top and between layers)
drip("chocolate")       a drip running down the sides
sprinkles()             rainbow sprinkles; sprinkles("pink") for one colour
swirl("white")          one piped swirl on the rim; loop it for a ring
topping("cherry")       one topping on top; call it again for more
candle()                one candle; candle("blue") for a coloured one
write("Hi Gran")        write on the front of the cake (a colour is optional)
tier()                  start a smaller cake on top (wedding cakes)
```

Every command works from level 1a; tier() is only in the Studio.
Colours can also be hex codes (`"#ff88cc"`) for anyone who wants a custom shade.

## Levels

Every level has 3 to 5 customers with tickets; the Bake-Off brings 5 random ones.

| Lvl | Level | Customers | ★2 | ★3 |
|---|---|---|---|---|
| 1a | Flavour of the Day | 3 | ✨ Your own touch: add something extra to every cake | 🖨 `print()` each customer's name |
| 1b | Pick Your Colours | 3 | ✨ Your own touch: add something extra to every cake | 🏷 Keep something from the ticket in a variable |
| 1c | Names on Cakes | 3 | ✨ Your own touch: add something extra to every cake | 📣 Write the name in CAPITALS with `.upper()` |
| 2a | Birthday Candles | 3 | ✨ Your own touch: add something extra to every cake | 🖊 Write their name and age, like "Ava is 8" |
| 2b | Stripes | 3 | ✨ Your own touch: add something extra to every cake | 🔢 Write how many layers it has |
| 2c | Build Your Own | 4 | ✨ Your own touch: add something extra to every cake | 🔢 Write how many toppings it has, using `len()` |
| 3a | Sprinkles or Not? | 4 | ✨ Your own touch: add something extra to every cake | ✂️ 7 lines of code or fewer |
| 3b | Party Time | 4 | 🖊 Write each customer's name on their cake | 🔀 Use `if`, `elif` and `else` |
| 3c | Bug Hunt: The Age Rules | 5 | ✨ Your own touch: add something extra to every cake | ✂️ 11 lines of code or fewer |
| 4a | Candy Canes | 3 | ✨ Your own touch: add something extra to every cake | ✂️ 9 lines of code or fewer |
| 4b | Pick and Mix | 4 | ✨ Your own touch: add something extra to every cake | ✂️ 10 lines of code or fewer |
| 5a | The Menu | 4 | ✨ Your own touch: add something extra to every cake | 🧩 Use a recipe you made with `def` |
| 5b | Any Size | 4 | ✨ Your own touch: add something extra to every cake | 🧩 Use a `def` with parameters |
| 6 | The Great Bake-Off | 5 random | 🏆 3 happy customers in one run | 🏆 All 5 happy in one run |

★1 is always "every customer happy" (on the Bake-Off, 1 happy).

## Judging a cake

The order lists what's **required**: exact layers bottom to top, frosting,
drip, sprinkles (yes / no / colour), candles, counts of named toppings, swirls
(count or colour pattern), the message and tiers. The message is compared
ignoring capitals, punctuation and extra spaces, so `"Happy birthday, Ava!"`
matches. Anything else on the cake is **your own touch**, which is welcome
unless the order says no (no sprinkles means no sprinkles).

## Safety

The same approach as the other games: student code is interpreted from its
parse tree by a whitelist (`cycles.Brain`), with no imports, no attribute
access except `.upper() .lower() .title() .append()`, and capped operations,
text length, list length and cake size.

## Pages

- `/cake`: the student page (orders, studio, shop window, pantry)
- `/cake/show`: the projector (shop window slideshow, class star meter, feed)
- `/cake/teacher`: who's stuck where, last error, hide a cake from the shop window, set the window theme, open levels

## Build order (each step verified before the next)

1. `cake.py`: interpreter, kitchen, judge, levels → `test_cake.py`: every
   level's reference earns all 3 stars; hard-coded answers fail the rush
   levels; the interpreter's new features and errors.
2. Server glue and endpoints → endpoint tests.
3. `cake.html`, `cake_show.html`, `cake_teacher.html` → driven in a real browser.
4. `CAKE_SHOP_GUIDE.md` for the lesson.
