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

- **Customers with personality.** Granny Rose, a cat who wants fish on the
  cake, a dragon turning 100 (100 candles, and only a loop will do), a zebra
  who wants stripes, a unicorn who wants a rainbow.
- **A big, pretty cake** that builds step by step: layers drop in, frosting
  spreads, sprinkles rain down, candles pop up and flicker, writing appears.
  Every step has a sound.
- **Your own touch** ✨: on most levels one star is for adding a decoration the
  customer *didn't* ask for. Being creative is part of the score.
- **Unlocks**: stars unlock new toppings (butterflies, ghosts, crowns,
  unicorns…), special frostings (glitter, galaxy, rainbow) and the look of
  your shop (cake stand, wallpaper). The class unlocks the last few together.
- **Name your bakery.** It shows on your page, in the shop window and on the projector.
- **Studio and the Shop Window**: free baking with everything unlocked, then
  put your best cake in the class shop window. Classmates can ❤️ it, view its
  recipe (code) and remix it.
- **Projector page**: the shop window as a slideshow, the class star meter and
  a live feed ("🐉 Mia made Ember the dragon very happy").

## Not too easy, not too hard

- Every level has starter code, a **Chef's tip** card with an example of the
  new idea, and three hints that go from a nudge to the answer.
- Error messages are friendly and say what to type (as in the other games).
- The customer says exactly what's wrong, so students can debug by reading.
- Depth comes from later chapters: dictionaries, lists, `if/elif/else`,
  `%`, functions with parameters, and one program that bakes for any customer.

## The Python it uses (more than the other games)

| Idea | Where |
|---|---|
| Commands with text arguments: `layer("chocolate")` | Ch 1 |
| `print()` | Ch 1 (a star) |
| `for` loops, loops with several lines inside | Ch 2 |
| Dictionaries: `order["flavour"]`, variables | Ch 3 |
| Joining text, f-strings, `.upper()` | Ch 3 |
| `True`/`False`, `if/elif/else`, `< <= >=` | Ch 4 |
| Loop counters and `%`, lists, `for x in list`, `len()` | Ch 5 |
| `def` with and without parameters | Ch 6 |
| One general program for any order | Finale |
| `choice()` and `randint()` for surprise cakes | Studio |

## The kitchen commands

```
layer("vanilla")        add a sponge layer (bottom first)
frosting("pink")        frost the cake (top and between layers)
drip("chocolate")       a drip running down the sides
sprinkles()             rainbow sprinkles; sprinkles("pink") for one colour
swirl("white")          one piped swirl on the rim; loop it for a ring
topping("cherry")       one topping on top; call it again for more
candle()                one candle; candle("blue") for a coloured one
write("Hi Gran")        write on the front of the cake
tier()                  start a smaller cake on top (wedding cakes)
```

Commands arrive chapter by chapter, as sensors do in Strange Planet.
Chapter 1: layer, frosting, drip, sprinkles, topping, write. Chapter 2: candle,
swirl. Chapter 6: tier. Studio: everything.
Colours can also be hex codes (`"#ff88cc"`) for anyone who wants a custom shade.

## Levels

Ch 1 and 2 have one customer each. From Ch 3 on, **the same program bakes for
3 to 5 customers** with different tickets (`order`), so hard-coding fails in
plain sight: one customer is happy, the next gets the wrong flavour.

| Lvl | Customer | Python idea | ★2 | ★3 |
|---|---|---|---|---|
| 1a | 👵 Granny Rose: 2 chocolate layers, white frosting | commands, quotes | own touch | `print()` a note |
| 1b | 🧒 Leo: vanilla, strawberry, vanilla, pink frosting, a cherry | order matters | own touch | write LEO |
| 1c | 🐱 Captain Whiskers: lemon ×2, white, chocolate drip, 3 fish, "MEOW" | putting it together | own touch | ≤ 9 lines |
| 2a | 👧 Ava turns 8: candles | `for` | own touch | ≤ 7 lines |
| 2b | 🐉 Ember the dragon turns 100 | big loops | own touch | ≤ 8 lines |
| 2c | 🦓 Zoe: 8 stripy layers, 12 swirls | two lines in a loop | own touch | ≤ 7 lines |
| 3a | Flavour of the day ×3 | `order["flavour"]` | own touch | use a variable |
| 3b | Birthday rush ×3 | `range(order["age"])`, `+` text | own touch | ≤ 8 lines |
| 3c | Party planner ×3 | f-strings / `str()` | name in CAPITALS (`.upper()`) | ≤ 6 lines |
| 4a | Sprinkles or not? ×4 | `if` with True/False | own touch | ≤ 7 lines |
| 4b | Party time ×4 | `if/elif/else` with `==` | write each name | uses `elif` |
| 4c | Age rules ×5 | `<`, boundaries | own touch | ≤ 13 lines |
| 5a | 🐧 Penguin Pete: alternating swirls | counter and `%` | own touch | ≤ 8 lines |
| 5b | 🦄 Rainbow: layers and swirls | lists, `for x in list` | own touch | ≤ 7 lines |
| 5c | Build your own ×4 | lists in the ticket | write the number of layers (`len`) | ≤ 6 lines |
| 6a | The menu ×4 | `def` | own touch | uses `def` |
| 6b | Any size ×4 | parameters | own touch | a def with parameters |
| 6c | 💍 Wedding bells ×3 | `tier()`, functions + lists | own touch | ≤ 12 lines |
| 🏆 | The Great Bake-Off: 5 random customers | one general program | 3 happy | all 5 happy |

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
