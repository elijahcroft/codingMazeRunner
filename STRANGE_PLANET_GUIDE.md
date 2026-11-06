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

## Since the first lesson (what students will notice)

**Your rover is your pupil.** It says what it learned at the beacon ("You taught me
to repeat!"), says which line confused it, says "Ow! Rock!" on its first bump, and
when nobody has touched anything for 30 seconds it asks what to do (three times at
most). The youngest (practice zones with arrows) see *steps*, not *ticks*, on the win card.

**Two levels where a loop is the only way.** After 1B, **1B1 Short Memory** and **1B2
Memory Full** give the rover a memory of 4 and 6 lines, shown above the editor. The long
way doesn't fit: the rover says "My memory is full!", and if the code repeats, the banner
offers the shortcut. Most students could finish every other level without a loop, and
most did. Anyone already past them isn't sent back.

**🧠 What your rover knows.** A chip beside the goals counts the big ideas a student
has used in a win (loops, variables, `while`, `if`, `def`, loops in loops, `print`), and
shows the next one to teach. Using a variable earns a new badge, Name Giver.

**🎯 Class challenge.** ⚙ Settings on your page: pick a level and it opens for everyone,
locked or not. Students get a gold chip within seconds, the class screen counts who's
finished it and names them, and the win card says what number they came. Pick *None* to
end it. Handy for "everyone try 1B1 now".

**🏁 Class race.** Press 🏁 Race beside the challenge and put that page on the class screen.
Everyone who has won the challenge is on it, each with their own map. Press 🏁 Start the race:
3, 2, 1, and every rover drives its student's quickest win at once. Tiles light up as they
finish, and the fastest get a gold edge. At the end it names ⚡ Fastest rover (fewest ticks) and
✂️ Shortest program (fewest letters, not counting spaces or comments), and **✂️ Show the
shortest program** puts that code up big to talk through. A win that wasn't sent
during this challenge isn't on it, so a student who won earlier has to Transmit again. It lasts
until you pick a new challenge, so you can pick *None* first.

**🔮 Predict it.** ⚙ Settings → pick a question, and press **📺 Show** beside it for the class
screen. Every student gets the code and four answers: how many squares will the rover drive?
The class screen counts the votes and keeps how they fell hidden, so nobody just copies the
crowd. Press **🎬 Reveal**, here or on the class screen if it's the same browser: the rover drives
it, the right answer lights up and the votes show. There are no names and nothing is earned, so a
wrong guess costs nothing. Ask "why?" before you reveal. Pick *None* to finish. The twelve
questions run from `east(3)` to loops inside loops, and each answer comes from running the code.

**🐛 Bug hunt.** A warm-up, and a challenge with a broken program. ⚙ Settings: pick one. Students
press the gold chip to open the level, then again to load the broken code (Ctrl+Z brings theirs
back). They Transmit to see what goes wrong, and fix it. After 2 misses in a row a 💡 clue names the
kind of mistake. It counts as the challenge, so the race works with it too. Every one is played in `test_team.py`. The answers:

| Level | The bug | The fix |
|---|---|---|
| 1A | A number that's one too small | `east(6)` should be `east(7)` |
| 1A | A wrong direction | The `north()` after `east(7)` should be `south()` |
| 1A | A missing bracket | `east(7` needs its `)` |
| 1B | A loop that stops too soon | `range(3)` should be `range(8)` |
| 1B | A missing colon | `for` line needs its `:` |
| 1B | A line that isn't indented | `south()` needs four spaces, to go inside the loop |
| 1B1 | A number inside the loop | `east()` should be `east(2)` |
| 1C | A loop that checks the wrong thing | `==` on the first `while` should be `!=` |
| 2B | A slide that goes the wrong way | The last `east()` should be `west()` |

**👀 Eyes up, ⏰ 5 minutes, 👋 Stop.** The buttons at the top of your page put that message on every
student's screen within about six seconds, over whatever they're doing, Team Mission and lounge
included. It's a fixed list.

**⏱ Minutes played.** A card says how long a student has played today, and "Today:" under the
crew adds up the class. It counts while the page is open and they've pressed something in the
last 90 seconds, so a laptop left open stops counting. It only counts from now on. **📋 Today's class**, near the bottom of your page, lists everyone
who played today with their minutes, runs, wins, new levels and where they are now, and under
that the class's Team Mission best times.

**Rovers have names.** The first win asks; the box is under the rover in the garage.
The name shows on the student's own screen, in the win card and when you click the
rover, and on the rover's tag in the 🛋 Rover Lounge. A student who feels they're
teaching someone tends to try harder for them.

**Shortcuts out of a student's own code.** After a win, code with the same lines over
and over gets a 🪄 box on the win card: "You wrote `east()` 6 times!" Pressing *Teach
your rover a shortcut* makes the copies vanish and leaves a loop, `for i in range(_):`,
with the number for the student to type. Transmit, and the card says how many lines it
saved. Wrong number? The banner says how many times it went round and how many times
they wrote it. The same few lines in places apart get *Name this move* instead: the
student types a word, and it becomes a `def`. Ctrl+Z brings the old code back. On last
term's code this fires on about 7% of wins: most students' programs don't repeat.
A student whose program ends with a `for` that reaches the beacon gets the next step:
*Teach your rover to look* swaps the count for `while not at_beacon():`, until they know `while`.

**Sending the same code after a miss doesn't send it.** The rover replays what happened,
says "Same code, same trip!", and the banner asks for a change. Half of all tries in a
row used to be the same code. After a miss the cursor is back in the code, at the end
of it if the program stopped short.

**One step at a time.** ⏭ next to Play moves the replay on by one step and lights up
the line that did it.

- **Measuring sites have numbered steps,** and everyone's number is their own
  (2A ice length, 3A gust timing, 7A beacon distance; 5A is still 2 for
  everyone). A classmate's number gets "That's the number on someone else's
  planet". Expect "why is mine different?": that's the point, see the
  lesson plan below.
- **1B and 1C show the shape of a loop** in the brief (`for` on 1B, the east
  half of the `while look()` loop on 1C). In the first lesson nobody used
  `for` on 1B or `look()` on 1C.
- **1C's challenge star is 🌍:** the same code must work on all 8 rock runs,
  so a route counted off the map completes the site but misses the star.
- **3B lists the method in three steps** (wait on the tick before a gust, a
  def called before every square, one square at a time). 3B cost 12 to 42
  runs last time.
- **Failure messages read the code:** a copied `tick() % 9` on a planet
  whose gusts come every 7 says so, a copied route says "this code works on
  1 other planet in the class, but yours is different", and `"wall"` or
  `"Rock"` in a look() check names the right word.
- **Your page** shows "hasn't run yet" for students who never pressed
  Transmit, and each student's last 6 tries (code and messages) one click
  away, so you know what they tried before you walk over.
- **Nobody loses anything:** completed sites and stars already earned stay,
  including 1C's old 🧱 star.
- **The editor works like a real one now.** Typing a few letters suggests
  commands, sensors, keywords and the student's own names and variables,
  each with a line saying what it does (Enter or Tab picks one, Esc closes
  the list, Ctrl+Space opens it). Picking `for`, `while`, `if` or `def` at
  the start of a line types its shape (`for i in range():` with the cursor
  in the brackets). Inside `look("`, `jump("`, `drill("` and `distance("`
  the four ways are offered, and after `look("east") == "` the words this
  map can give back. Brackets and quotes close themselves, `else:` and
  `elif` line up with their `if`, Enter in front of `):` finishes the line
  first, and Ctrl+/ turns lines into `#` notes. Inside a command's ( ) a
  tip says what goes there (`east(squares)`), and pointing at a word says
  what it does.
- **Slips show before Transmit:** once the cursor leaves a line, a missing
  `:` or bracket, an unclosed quote, `east 2` without brackets, `=` in an
  `if`, a line pushed in too far (or not pushed in under a `:`), a typo
  like `nroth()` ("did you mean north()?") and the maze game's `move()`
  get a wavy line, a ● in the margin and a few words at the end of the
  line. A ⚠ pill at the bottom of the editor names the first one and goes
  to it. A run's code error is also written on its line.
- **The replay follows the code:** the line that made each move lights up
  green as the rover drives. Clicking a line number jumps the replay to
  when that line ran (again for the next time), and clicking a telemetry
  line jumps to its tick: "what did line 3 do?" now has an answer on the map.
- **Help is easier to find:** after two misses in a row on a site not yet
  done, the 📻 button glows and says "Get a hint" until there are no hints
  left. Transmitting exactly the same code after a miss says "Same code as
  last time: change one thing".
- **Transmit is something you see happen:** dots of light fly from the button
  to the rover, and the button stays down until they land. An empty editor
  sends nothing: the rover asks for its code, and on Practice Park levels the
  arrow buttons stay (a miss there offers them straight away too). Pressing
  Transmit again while the same code is still driving just gets "I'm on it!".
- **More time to enjoy a win:** programs under 10 moves replay more slowly, so
  each line can be seen lighting up. A new win plays the victory dance twice
  before the card, and **Watch again** is on every win card and replays the run.
- **The win card shows the next unlock** (its name and a bar that fills as
  the new stars land, "2 ★ to go"). The buttons under the editor are
  coloured like the code: green commands, blue sensors.
- **Nobody sits stuck without a way on.** A student who hasn't pressed
  Transmit after 45 seconds sees Transmit glow and a line saying to press it
  (half the class never ran in the first lesson). After 8 misses in a row on
  a site, the banner names up to two classmates who cleared it today ("🙋 Ask
  Ada"). After 20, **⏭ Skip for now** opens the next site; the skipped one
  stays in the 🗺 Levels map to come back to, with no stars until it's done.
- **Missed runs that get further say so:** "🔥 Closest yet! 3 of 8 samples
  (before: 1 of 8)" or "4 squares from the beacon (before: 7)", only when a
  miss beats the student's best on that site. Long grinds like 3B now show
  progress before the win.
- **The first lesson's answers are named:** `report(6)` on 2A (and 5 on 3A,
  12 on 7A) says "That was the number before every planet got its own".
- **Clearer slips:** `if x() == 1 east()` on one line says to end it with
  `:` and put the commands under it; a long `for` loop that runs out of time
  says so, instead of blaming a while loop.

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
  mission after 5 different tries that didn't (**Never Give Up**), class records, all
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
- **Coding unlocks paint**: some garage items come from a badge, not stars,
  so the coding is the way to get them. Worth telling the class: a `for`
  loop earns the Cheetah paint, an `if` the Zebra, a `while` loop the Robot,
  fixing a code error the Ladybug, and beating a class record the Race Car.
  Silly ones: a mission with `print("moo")` in it earns the Cow paint, and
  `print("sssss")` the Creeper. Every locked item in the garage says how to
  get it. Earning every star in a zone (its Master badge) gives a legendary:
  a Frost Crown for the Ice Field, a Hero cape for Wind Canyon, Laser eyes
  for the Laser Range and more.
- **🎨 The Paint Shop** (top of the garage's Paint tab): students paint their
  own rover with code, `paint(x, y, "red")` on a 10 by 7 grid and
  `fill("navy")`, and watch the squares go on one at a time in the order
  their code painted them. Clicking a square writes the `paint()` line for
  it, so younger kids can start by clicking. Loops make stripes, a loop
  inside a loop and an `if` make checkers (there are six examples to load).
  **✓ Wear it** puts it on their rover everywhere, the class screen too, and
  painting with a loop earns 🎨 Pixel Artist. A great five minutes at the
  end of a lesson. If a painting isn't right for the projector, **🧽 Wipe
  paint** on the teacher page takes it off.
- **🛞 Wheels**: a garage slot of its own, from monster tyres and tank treads
  to hover pads and flame wheels.
- **🧩 Full sets**: wearing every piece of a pack (all four Ninja things, say)
  sends the pack's icon circling the rover. The garage says how many pieces
  are on.
- **Ranks**: the ★ button at the top shows a rank icon and a thin bar to the
  next one: Cadet, Rookie Pilot (10 ★), Pilot (25), Navigator (45), Explorer
  (70), Pathfinder (95), Commander (120), Star Captain (145) and Legend
  (every star). Ranking up says so on the celebration card with a fanfare,
  and earns a **🎉 reward to pick**: the garage offers three locked things
  and the student unlocks the one they like best.
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
- **🏁 Race the record ghost**: once a student has completed a site, its
  replay also shows the class record's rover, see-through and tagged with
  the holder's name and ticks, driving its route step for step. It only
  appears after they've done the site themselves, so it gives no route
  away, and never on per-student planets, where the maps differ.
- **Loadouts on the big screen**: every replay on the class screen and the
  teacher page shows the student's whole look from the garage: paint, hat,
  wheels, glow, pet, their trail behind the rover, their map look's colours
  and their own victory dance at the beacon. (Halloween levels keep their
  spooky streets.)
- **💾 Saved looks**: four slots under the garage preview. Pressing an empty
  one keeps everything the rover has on (Paint Shop painting included);
  pressing a full one puts that whole look back on. ✕ empties a slot.
  🧽 Wipe paint on the teacher page clears a painting from saved looks too.
- **Hide the camera**: a tick box under the garage preview takes the camera
  head off the front of the rover, so more of the paint shows (on the class
  screen too). Untick it to put it back.
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
  marks open sites that still hide one: on the route bar for the zone
  you're in, and on the 🗺 Levels map for all of them. The garage counts
  them ("3 of 8 found"), and finding all 8 earns the 🎁 **Treasure Hunter**
  badge. In easy mode each practice zone hides one too (P2, P10, P17, P26,
  P34, P43, P47), with a pet, a hat, a paint or a glow you can only find there. **🎲 Surprise me** in the garage picks a random look from
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
  what-happened and 👉 next-step line as a transmitted run. Where the rover
  can jump, space jumps the way it last went, and Shift+space waits. Where it
  can drill, E digs the same way. Before the first move, the next arrow picks
  the way. J or X then an arrow still works.
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
- **Sound** (⚙ Settings has a "Sound starts on" switch for the class, and a
  student's own choice with the 🔇 button always wins): every event has a synthesized sound effect. It starts **off**
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
- **The help comes off as they go.** Students write more by hand the further
  they get. Each piece goes when a student first reaches that zone, stays off
  even back on old sites, and a ✍️ note says so once:

  | Reached | They now type |
  | --- | --- |
  | Wind Canyon | their own `(`: picking a word adds no brackets, and a chip shows the code instead of typing it |
  | Solar Valley | the closing `)` too, and **📋 Use as code** goes (scouting stays) |
  | Signal Plains | both quotes (the engine still forgives `look(east)`, but the line gets a ⚠) |
  | Conveyor Works | the whole shape, `for i in range(3):`, colon and all |
  | Gate Station | indents, with Tab, and lining up `else:` |
  | Boulder Yard | the spelling: suggestions stop, but Ctrl+Space still lists them |

  The ⚠ slips, tips in the ( ), and Tab stay to the end. The drive-first
  practice sites keep all the help. The list is `TYPE_YOURSELF` in `planet.py`.
- **Written for a child who finds computers hard.** The **?** card starts with
  five plain steps and has two new folds: **What do the words mean?** and
  **Where are the keys?** (`(`, `"`, `:`, Tab and so on). While the replay plays,
  a caption on the map says which line the rover is on and what it's doing. The
  goals are labelled **Your job** and **Extra stars**, and the first two zones
  name the sample, beacon and crater on the map. A mistake says what to type,
  why the rover stopped, and that nothing is broken. The word "Telemetry" is
  now "What the rover did", and "Code error" is now "Line to fix".
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
| 1C Rock Run | 🧪 a sample in front of every rock | 🌍 the same code works on every rock run | 7 lines |
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

- [ ] `python3 server.py`. Note the **admin key** in the banner. A server that's already
      running keeps its old pages and rules, so stop it and start it again after any update.
      Mission Control shows a red warning if you've forgotten.
- [ ] Students go to **`http://<ip>:8000/planet`** (the banner prints it).
- [ ] If they've done the maze game, say so out loud: **"This rover never
      turns. North is up."** The Landing Site (3 short sites) is where they
      learn compass driving and `look()`, so nobody skips it.
- [ ] Ask them to join with their **full name**: two students who type the
      same name share one rover and one set of stars.
- [ ] Put **`http://localhost:8000/planet/show`** on the projector.
- [ ] Open **`http://localhost:8000/planet/teacher`** (Mission Control) on
      your laptop. At the top, every **Transmit** replays big: the student's
      name and rover, their route on the map, their code, and a stamp for how
      it ended (🎉 mission complete, 💥 fell in, 🐞 code error…) with what the
      game told them. Several runs at once queue up; **Recent runs** replays
      any of them, and so does **▶ Replay** on a student's card. Only you see
      misses: the projector cheers completed missions only.
- [ ] Under the replay: the numbers (active now, need help, idle), a
      **🙋 Worth a visit** strip (misses in a row: 8+, or 3+ in easy mode, and
      students who haven't pressed Transmit), and **Where everyone is**, zone
      by zone with names. Each student's card says how they're doing
      (🚀 just ran, ✎ typing, ✋ misses in a row, 💤 no run for 3+ min), the
      level they're really on (a practice level in easy mode too), their
      progress, and what their last missed run told them. A card flashes
      green or amber when they run. Sort by **Needs help first**, **Furthest
      along** or **A–Z**, or find a name.
- [ ] The admin key and the three class switches are under **⚙ Settings**.
- [ ] On a card, **Last tries on this level** opens their last 6 tries: how
      each ended, what it told them, and the code, newest first. After
      class, `scores.json` keeps them for every site (`planet` → `tries`).
- [ ] **Level by level** (at the bottom, click to open) is for after class:
      every site someone tried, how many cleared it, typical runs, who
      hasn't cleared it, the hints each zone took, and what the game told
      students most often when they missed. Use it to pick where the next
      lesson starts and what to explain on the board.
- [ ] **📽 Show code** on a student's row puts their last transmitted code
      on the class screen, big and without their name, with "it works ✓" or
      "not working yet: can we fix it?". Good for the end-of-lesson
      discussion. **📽 Stop showing code** at the top brings back the fleet.
      Both need the admin key, like Unlock next.
- [ ] Each time the server starts it copies `scores.json` to
      `scores.json.start-<date>-<time>` and keeps the last 5. To undo a bad
      day, stop the server and copy one back over `scores.json`.
- [ ] On a student laptop, join as "Test" and run the starter on 1A.
- [ ] Decide what to say when a student asks "what's the rule?":
      **"What did your last run show you?"** (see below).

### A class hour using all of it

1. **Warm-up, 5 minutes.** 🔮 Predict it for a question or two, then ⚙ Settings → 🐛 Bug hunt.
2. **The race, 2 minutes.** 🏁 Race on the class screen, then Start the race.
3. **Levels, most of the hour.** Their own route, with 👀 Eyes up when you need the room.
4. **Team Mission, last 15 minutes.** Open it with the switch, and 📺 Watch on the class screen.
5. **Lounge, if there's time.** ⏰ 5 minutes before the end, then 👋 Stop.

## How a site works

Each zone has three sites, and each site has a job:

| Site | Job | What students feel |
|---|---|---|
| **A · Notice** | A 📡 field measurement: the rule shows up, and the mission is to find its number and `report()` it. (Crumbling Crust and the Portal Fields notice it on a normal mission instead.) | "Wait, why did it do *that*? How much?" |
| **B · Use** | Only a program that uses the rule on purpose works. | "So I have to plan around it." |
| **C · Generalise** | The rule's details differ **per student** (a different field, lake, gust timing, sun, or portal wiring). | "My neighbour's code doesn't work on my planet." |

When a student opens a new site, **their code from the last site is
already loaded** and the map says *"The code from your last level is in the box. Will it
still work here?"*
That's deliberate: running the old program on the new ground is how they
notice each rule. Ask them to predict out loud before they press **Transmit**.

**When a run misses**, the banner under the map says what happened and where,
in plain words, then one thing to try (👉). It never asks a question. For example:
*"A belt carried the rover into a crater at x 12, y 5."* 👉 *"Belts carry the
rover the way their arrows point. Jump over a belt you don't want to ride."*
Or, for code that stops short: *"Your code finished before the beacon."* 👉 *"The
beacon is 5 squares east of the rover."* The rover shrugs, says how far is left
("5 more squares!"), and a dot on each square shows the way; a best try yet says
"🔥 Closest yet!" on the map. The exact spot is in the telemetry.
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
| 1 | **Landing Site** (1A–1C) → **Ice Field** (2A–2C) | "How did you measure the slide? Who made the rover measure it?" Everyone's 2A slide is a different length: ask two neighbours to compare numbers, then show that `report(x() - 1)` is right for both. |
| 2 | **Wind Canyon** (3A–3C) → **Crumbling Crust** (4A–4C) | "How did you find *when* the gusts came? What was your evidence?" (Everyone's 3A gusts keep their own time, so the answers differ; the method is the same.) |
| 3 | **Solar Valley** (5A–5C) → **Portal Fields** (6A–6C) | "How did you work out where each portal goes? How many runs did it take?" |
| 4 | **Signal Plains** (7A–7C): steering by coordinates on calm ground → **Crater Hops** (8A–8D): the new `jump()` | "When does your program jump, and how does it know?" |
| 5 | **Conveyor Works** (9A–9E) → **The Quarry** (10A–10E) → **Gate Station** (11A–11E) → **Flag Relay** (12A–12E) | "Which new thing changed your program most, and what stayed the same?" |
| 6 | **Boulder Yard** (13A–13E) → **Laser Range** (14A–14E) → **Cargo Run** (15A–15E) | "Where did a variable or a sum save you from counting?" |
| 7 | **Grand Tour** (16A–16D): everything at once → **Uncharted**: the same 5 planets every run | "Which square was hardest to plan for, and how did your code tell it apart?" |

Fast students will get ahead. That's fine, because each site opens only when
the one before is done. Slow students aren't stuck behind a wall: open the
next site for one student from `/planet/teacher` (type the admin key once,
then **Unlock next**).

## The screen, kept simple

- The **route bar** at the top shows the zone you're in as a row of dots,
  one per level; every other zone is just its icon (press it to go there,
  a gold dot means every level is done). **🗺 Levels** shows everything.
- The **◀ P6 ▶** arrows beside a level's name step to the level before or
  after.
- A status pill on the map only appears when there's news: Driving,
  Beacon reached, Code error and so on.
- An empty code box says what to do: write a command a line (or press one
  under the box), or on practice levels drive first and press 📋 Use as
  code.
- On practice levels the 🧰 Functions button and the line counter stay
  hidden (kids haven't met `def` yet, and practice levels have one star).

## Easy mode: practice zones for a younger class

Turn on **Easy mode** in ⚙ Settings on `/planet/teacher`. Seven practice zones
come before the Landing Site, every level open, and kids drive by hand first
(arrow keys or the buttons on the map), press **📋 Use as code**, finish the
words letter by letter and press **Transmit**:

| Zone | Levels | What's new |
|---|---|---|
| 🛝 Practice Park | P1–P8 | one-square drives, then `east(4)`, then a first `for` loop |
| 🌻 Loop Garden | P9–P16 | corners, a rock to go round, loops with a line after them |
| ⛸ Ice Rink | P17–P24 | one press slides until something stops it |
| 🔮 Pad Park | P25–P30 | magic pads: drive onto one, pop out of its partner; P30 is one drive in a loop |
| 🐸 Jump Park | P31–P38 | `jump("east")` over craters and rocks; while scouting, space (or 🦘 then an arrow, or Shift+arrow) jumps |
| 👀 Look-Out Point | P39–P46 | `look("east")` and `while` loops: everyone's paths are a different length, so a loop that looks beats counting |
| 🔀 Fork Road | P47–P51 | `if` and `else`: maps that differ between neighbours, a `for` loop with an `if` in it, and a path finder that works on any staircase |
| 🎓 Trick School | P52–P57 | `def`: teach the rover a trick, call it, put it in a loop, give it a number |
| 🔢 Number Lab | P58–P63 | variables: name a number, change one number to fit your own field, `n = n + 1` stairs and spirals |

Look-Out Point and Fork Road get the class ready for the Landing Site's
`look()` and `while`. Kids who had already moved on to the Landing Site
before they were added aren't sent back: the zones are open for them, but
they carry on where they were. The same goes for Trick School and Number Lab,
which show a **NEW** tag in Levels until someone tries them.

Look-Out Point, Fork Road, Trick School and Number Lab are typed: there's no
driving by hand first, because the code is the lesson (🕹 Scout is still there
for looking around). Trick School and Number Lab also give all three stars,
not one: the 🧩 or 🔢 star is for using the new idea, and ✂️ is for keeping it short.

Wind Canyon has two new levels before The Ledge: **3A1 Hold On!** (`wait()` by
hand) and **3A2 Gust Guard** (the `if tick() % 5 == 4` check), so The Ledge
only adds `def`. Saved games keep their place.

Students find every level in the **🗺 Levels** button at the top left: every
zone in one list that folds (where they are and where they're going start
open), a strip of zone icons to jump along it, and each level as a tile with
its stars, 🔒 for what's still locked,
and **▶ Play next**. The ◀ ▶ arrows beside a level's name go to the level
before or after.

## 🛋 The Rover Lounge: somewhere to show off

A room where everyone's rovers hang out together. It's for play, so nothing in it
earns stars or badges, and nothing is counted or ranked. Use it as a treat, like the
last ten minutes of class.

**Opening it:** turn on the **🛋 Rover Lounge** switch under ⚙ Settings on the teacher page. A pink
**🛋 Lounge** button comes up at the top of students' screens within about six
seconds. Turning it off sends everyone back to their level with their code as they
left it. It's always closed after a server restart.

**What students can do:**

- **Drive around.** Click the floor, or use the arrow keys. Everyone sees it move.
- **📯 Honk, 💃 Dance, 👋 Wave.** Their own horn and victory dance from the garage. A
  horn only sounds on that student's own computer, and everyone else sees a 📯, so
  the room stays quiet.
- **Click a rover** to see it up close: its name, the rarest thing it's wearing, its
  pet and its worn badge. Stars never show.
- **Send a cheer.** Five fixed choices (👏 🔥 ⭐ 🤩 ❤️), and no typing, so there's no
  chat to watch.
- **🎤 Take the stage.** Works for everyone. The rover rolls on and spins, does its
  dance, honks and waves. One rover at a time, with a queue.
- **🌀 Spin, 🦘 Jump and the emotes.** Six fixed faces (😂 😎 🥳 🙌 🤖 😴) float up over their
  rover, so there's still no typing.
- **Kick the ball.** Drive into it and it rolls away. Everyone sees the same ball. There's no
  goal and no score.
- **The dance floor.** The tile under a rover lights up as it drives across.
- **🎬 Make your own show.** An extra, only for those who want it. They write a short
  program with `spin()`, `dance()`, `honk()`, `wave()`, `wait()` and the four
  directions, and loops, `if` and `def` all work. **💾 Keep this show** makes it what
  their rover does on stage. A show is one turn, about 20 seconds or 30 moves, and a
  longer one just stops there. A show can't say anything, because there's no word for it.

**Keeping an eye on it:** tags read "Zoomer · Mia", rover name then student. A
student's rover name also shows on their card on the teacher page, with a **🧽 Wipe
name** button beside **🧽 Wipe paint**. Both change the room at once. Rover names
only allow letters, numbers and spaces, which won't stop a rude word, and a student
can type a new name after a wipe. If that keeps happening, close the lounge.

**On the class screen:** **📺 Watch the lounge** comes up on the teacher page while it's open. It
shows the room with no rover of its own.

**Trophies:** the shelf on the wall has one 🏆 for each Team Mission level, lit up once the class
has finished that level. They stay after a restart and after 🔄 Start again. A level finished
with 🔓 Open the doors doesn't earn one. They're for the whole class, so no names go on them.

## 🤝 The Team Mission: the whole class on one map, live

Everyone's rover is on the same map at the same moment, and everyone sees every rover and
every boulder move as it happens. There are eight levels. When enough rovers reach the gold
vault, the class gets a 10 second celebration and everyone rolls onto the next map together.
Nobody has to write code: they drive with the arrow keys, the on-screen arrows, or by clicking
a square, and 🤖 Code my rover is there for anyone who wants it. It earns no stars. All it keeps
is the class's trophies and best times.

**Opening it:** turn on **🤝 Team Mission** under ⚙ Settings on the teacher page. A
**🤝 Team Mission** button comes up at the top of students' screens within about six seconds.
Turning the switch off keeps the mission as it is until you open it again.

**📺 Watch** opens the live map for you or the class screen. Watching doesn't put a rover on it.

**What's on each student's screen:**

- **🧭 Next job.** One plain sentence on what the class needs to do now, with gold boxes pulsing
  round those squares on the map. It's personal too: a rover on a plate is told to stay there, a
  rover in the vault is told to wait, and the closest free rover is told the plate is theirs. It follows the game: a door a friend is holding says "Go
  through now!", and wide craters say to fill one row. It's on the class screen too.
- **Shouts.** 🆘 Help, ✋ Holding, 👀 Look, 🪨 Boulder and 🙌 Thanks put a bubble over the rover
  for everyone, by button or the keys 1 to 5. It's a fixed list, so there's no chat to watch,
  and one rover can shout every 2.5 seconds at most.
- **⏱ The clock and the class best.** The first finish sets the time to beat. Finishing with
  🔓 Open the doors doesn't count. Use the level list beside 📺 Watch to try a level again.
- **The win card** gives the time, the squares driven and the boulder pushes, and the map lights
  up everywhere the class drove.
- **🤖 Code my rover.** An extra. It opens a box beside the map, and the program drives their
  rover: `north(3)`, `south()`, `east()`, `west()`, `wait()`, plus `for`, `while`, `if`, `def` and
  variables. `look("east")` says `rock`, `door`, `crater`, `boulder`, `plate`, `vault` or `ground`.
  So `while look("east") == "ground":` then `east()` drives to the next thing. A program is
  worked out at the moment they press Run, and can do 60 moves. If it would hit something, it
  stops there and names the line. If the map changes on the way, the rover stops and says so.
  Keys or clicks take over at any time. It's handy for a long boulder push. A dotted line shows
  the way the rover is about to go, three buttons add a ready-made loop or check to the code, and
  `print()` shows beside the code, so `print(look("east"))` is a good way to find out what's there.

**The rules to tell the class:**

- Something heavy on a plate opens the door with the same letter.
- A rover on a plate holds the door open only while it stays there, so a friend can go through.
- A boulder pushed onto a plate sinks in and opens the door **for good**, which frees that friend.
- A door with two or three plates needs them all pressed at once.
- A boulder pushed into a crater fills it in, and then you can drive over it.
- Half the rovers need to be in the vault to finish a level, so one kid off doing something
  else can't hold up the class.

**When something goes wrong:**

- *A boulder is stuck.* Drive onto ♻. Every boulder nobody has pushed for 20 seconds goes back
  to where it started, including ones that went into a crater. Filled craters and sunk plates
  stay done, so this can never lose progress.
- *A rover is shut in.* **🏠 Back to the lander** works from anywhere.
- *Time's nearly up.* **🔓 Open the doors** opens every door and fills every crater on the level.
- *The class has done this level.* **⏭ Next level** skips ahead.
- **🔄 Start again** goes back to level 1. Restarting the server does too.

At least two rovers are needed, because some doors can't be opened alone. To try it by yourself
or with a very small class, press **🤖 Helper rover**: it stands on the plate that's needed next.
It doesn't count towards the vault, and a level it helps on earns no trophy or class best. You can
also join from a second computer, or use 🔓 Open the doors.

**Answer keys** (every one is played square by square in `test_team.py`, with two rovers):

1. **Landing Bay.** Push the boulder down onto plate A. One rover stands on plate B, and another
   goes through door B and pushes the boulder back left through the door onto it. Door C needs
   both its plates: push a boulder left onto each.
2. **Four Corners.** Door V has four plates, but there are only three boulders. Push the boulders
   onto three plates (up, up and down), and one rover stands on the fourth so the rest get through.
3. **Crater Crossing.** Push the boulder right into the crater to make a bridge, then push the
   boulder past it up onto plate A, which opens the top lane. Up there, push the boulder up and
   then left onto plate B, which opens the bottom lane. There, push the boulder up onto plate C,
   which opens the top lane again. Each lane then has a boulder to push down onto a plate V.
4. **The Long Road.** Push the boulder a long way right onto plate A, then down through the door.
   Push the boulder on the right into the crater, then the next boulder left onto plate B. Down
   again, push a boulder right onto each C plate.
5. **Three-Step Bridge.** The crater belt is three wide, so three boulders must end up in one row.
   Use the middle row: push the top and bottom boulders into that row first, then along. If they
   go into different rows, use ♻. Over the bridge, push the boulder onto one V plate and stand on
   the other.
6. **The Ring.** One rover stands on plate A. Another goes through door A, gets behind the boulder
   on that row and pushes it back out through the door onto the plate. Push a boulder down into
   a crater to cross to the bottom. There, push the two boulders apart onto the two V plates.
   The third V plate is on the far right of the outer road, with a boulder above it.
7. **Pass It Back.** Three doors in a row, and each one's boulder is on the far side. One rover
   stands on the plate, and the other goes through, pushes the boulder into row with the door,
   and rolls it back through onto the plate. Then the same again at the next door.
8. **The Big Vault.** Push boulders down onto plates A and B. One rover stands on plate D, and
   another goes through door D, pushes the hall's right-hand boulder left, then down through the
   door onto the plate. West: two boulders in one row bridge the double crater (two in different
   rows won't, so use ♻). Door C needs both its plates: push one boulder onto a plate, stand on
   the other, and a friend brings a boulder down through the door. East: swap doors E and F, where
   each door's plate is on the far side of the other door, so one rover stands while the other
   pushes a boulder through. Over the crater, boulder onto plate G. The three V plates are in the
   hall, the top left room and the top right room.

## 🎃 Halloween night: a limited-time event

Ten trick-or-treat levels (and four bonus ones) for the students **you** pick. Nobody sees them
until you invite them, so it works as a treat for students who are doing
well, while everyone else carries on with the main route.

**To send a student:** on `/planet/teacher` press **🎃 Invite** on their
card (or **🎃 Invite everyone** in the orange Halloween panel above the
crew). Within 15 seconds their screen shows an invitation with **🎃 Go
trick-or-treating!**; after that, the 🎃 candy counter at the top of their
screen takes them there. Press **🎃 Invited ✓** again to take an invitation
back. **Put it away** (or the 🎃 switch in ⚙ Settings) closes Halloween night
for everyone. Whatever students earned stays theirs; what they didn't earn
leaves the garage with it.

**The new command:** `knock("north")` knocks on the door of the house next to
the rover, that way. A lit house 🏠 gives candy (2 to 5, a surprise each
time). A haunted house 🏚 says **BOO!** and the run ends. Ghosts 👻 float to
and fro across the road: they drift straight through a rover that waits,
but driving *into* one is a BOO too. `look()` says `"house"`, `"haunted"`,
`"ghost"` and `"candy"`, and `candy()` says how much is in the bag. Scouting
can knock too (🚪 then an arrow, or K then an arrow).

| Zone | Level | What it asks for |
|---|---|---|
| 🎃 Trick-or-Treat Street | H1 Knock Knock | `east(4)` and one `knock("north")`; the 🎃 star is a golden pumpkin off the route |
| | H2 Candy Lane | five houses in a row: a `for` loop; the 🍬 star picks up candy in the nooks under them |
| | H3 Both Sides | knock north *and* south at every stop; the 🧩 star puts the two knocks in a `def` (a 🎁 gift here) |
| | H4 Spooky House | one or two haunted houses, different for each student: `if look("north") == "house":` |
| | H5 Ghost Crossing | three ghosts cross the road, timed differently for each student: `while look("east") == "ghost": wait()` |
| 👻 Haunted Hollow | H6 Pumpkin Patch | a field of 31 candies: sweep it with a loop (a breather, and lots of candy) |
| | H7 Long Street | a street of a different length for everyone: `while look("east") != "rock":` with an `if` inside |
| | H8 Trick or Trick | houses both sides, some haunted: two `if`s, or one `def visit(way):` for the 🧩 star (a 🎁 gift here) |
| | H9 Ghost Parade | ghosts *and* haunted houses: wait, drive, check, knock |
| | H10 Haunted Mansion | every house is a ❓ mystery and 4 are haunted, **new ones every run**: only code that checks every house gets round |
| 🧙 Witch's Woods (bonus) | H11 Candy Count | knock every door, then `report(candy())`: each student's street gives a different total, so a classmate's number fails |
| | H12 Witch's Path | a winding path, different for everyone, with houses along it: a path-follower (`while not at_beacon():` with `if`/`else`) that knocks too |
| | H13 Ghost Walk | ghosts walk *along* the road, coming at the rover or floating away: the same wait-then-drive loop, now it really matters |
| | H14 Witch's Party | mystery houses both sides, 3 haunted, new every run, then `report(candy())`: a function, a loop and a sensor together |

The 🌍 star on H4, H5, H7 and H9 tries the same code on every classmate's
street, so a route timed by hand for one street doesn't get it. Worth asking
the class: "how did your code know that house was haunted?"

**What they win.** Every level has its three stars (counted on their own, so
the event never changes ranks or the class star meter). Candy fills the
**🍬 candy road** (press the candy counter): a witch hat at 10 candy, then
Candy Corn paint, a black cat, a candy trail, pumpkin wheels, Mummy paint,
spooky fog, the Graveyard map, and Vampire paint at 165 (finishing every
level always gets there, whatever streets a student was given). Candy counts the
best run on each level, and a run that ends in a BOO drops its bag, so
grinding doesn't help but careful code does. Halloween badges give more:
Knock Knock (a doorbell horn), Boo'd! for getting spooked (a scream horn:
the funny one everyone gets), Haunt Detector for checking `look()` against
`"house"` (Ghost costume paint), Ghost Dodger (Zombie shuffle dance), Say
Boo for `print("boo")` in a finished mission (a witch's cackle), Mansion
Master (a haunted top hat), Witch's Apprentice for the witch's party (a
bubbling cauldron pet) and, for every Halloween star, **Pumpkin King**:
the legendary Jack-o'-lantern paint. All of it is marked 🎃 in the garage,
which has a Halloween tab while the event is out.

On your page, invited students' cards show their Halloween levels and candy,
and a run on a Halloween level plays on the big screen like any other, with
its houses and ghosts.

## Zone by zone

Each zone has three hints on the **mission control radio** (📻), from a nudge to partial
code. `/planet/teacher` shows how many each student opened.

### 1 · Landing Site: no strange rule (learning to drive)
Normal ground, so Zone 2's surprise has something to compare against. It's
where students meet compass driving, samples and `look()`.
- **1A Touchdown**: collect three samples. `south(2) east() south() east(7) south() north(3) west()`
- **1B Crystal Steps**: eight samples on a diagonal. The brief shows a
  `for` loop that drives east 3 times; students put both steps inside it.
  (In the first lesson nobody used `for` here.) *Find the repeat* →
  ```python
  for i in range(8):
      east()
      south()
  ```
- **1C Rock Run** (per student): a sample waits in front of each rock, at
  distances that differ for everyone. The brief shows the east half of the
  loop. Drive until the next square is rock:
  ```python
  for i in range(4):
      while look("east") != "rock":
          east()
      while look("south") != "rock":
          south()
  ```
  A route counted off the map works too (every student who solved it in the
  first lesson did that), but it misses the 🌍 star, which tries the code on
  all 8 rock runs, and at 8 lines the ✂️ star too.

### 2 · Ice Field: one `east()` slides until something stops it
New: `x()`, `y()` and `report()`.
- **2A First Frost** 📡: how many squares does one `east()` slide? Each
  student's ice is a different length (5, 7, 8 or 9), so a neighbour's
  number is wrong, and the rover says so ("That's the number on someone
  else's planet"). The brief walks it through in numbered steps; `east()`
  then `report(` the slide `)` completes it, and the 🔢 star wants
  `before = x()`, `east()`, `report(x() - before)`.
- **2B Glacier**: the beacon is two squares away, behind a rock. It takes
  **six slides**, using rocks as brakes: `north() east() south() east() south() west()`.
  *Plan backwards from the beacon.*
- **2C Frozen Lake** (per student, 8 lakes of 7–8 slides). One line per
  slide reads like a plan; ask students to say each slide's brake rock.

### 3 · Wind Canyon: every N ticks a gust pushes a *driving* rover one square east
New: `tick()`. A rover that `wait()`s holds on. Rock to the east shelters it.
- **3A Canyon Floor** 📡: how many ticks apart are the gusts? Each
  student's gusts keep their own time (4, 6, 7 or 8), and the brief's
  numbered steps start with `south(16)`, which shows two pushes on every
  planet (at 6, pushes on ticks 6 and 12). The 🔢 answer drives until
  it's pushed off its column, then reports the tick:
  ```python
  while x() == 2:
      south()
  report(tick())
  ```
- **3B The Ledge**: craters along a long ledge, with gusts every 5 ticks
  for everyone. The brief says so, and lists the three steps of the method
  without the code. Wait out each gust:
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
- **5A First Light** 📡: how much does one tick of `wait()` in the sun add? (2,
  the same for everyone, since the whole zone runs on it. The brief gives
  numbered steps.)
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
  beacon? Each student's beacon is a different distance away (9, 11, 14 or
  16), and the brief gives numbered steps. `report(beacon_x() - x())`.
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

#### The mixes: 8D and 9E to 15E
The last site of Zones 8 to 15 mixes that zone's new thing with one or two
from before, on a small planet with **more than one way through**. Any way
completes the mission; the challenge star picks out one of them, so it's a
good moment to ask "who got there a different way?"
- **8D Hop or Pad**: hop the three trenches, or the pad round them
  (`south(3) north() west()`, the ⚡ star).
- **9E Belt and Hop**: ride the belt and hop the trench (⚡), or drive round.
- **10E Through or Round**: drill the wall, or ride the belt round it and keep
  the drill (⛏ star): `south(3) north(2)`.
- **11E Two Ways In**: drill into the box, or fetch the key for the gate and
  keep the drill (⛏). Jumping the wall works too.
- **12E Flag Express**: after flag 2, the belt carries the rover to flag 3 (⚡).
- **13E Bridge or Tunnel**: push the boulder in and jump (⚡), or drill the two
  rocks under the trench.
- **14E Laser Locks**: key, gate, trench. Counting works; the 🔢 star wants
  `distance()`.
- **15E Express Delivery**: the belt along the bottom brings the rover home (⚡).

Students who had already passed one of these sites before it was added aren't
sent back for it: it opens for them, but they carry on where they were.

#### 16 · Grand Tour: everything at once
Nothing new: every site mixes several things from Zones 9 to 15, so the
work is planning and telling squares apart.
- **16A Locked Workshop**: drill into the key room (1 drill), pick up the
  key, then ride the one-way belt down to the gate:
  `east(3) drill("east") east(6) south(2) west(8)`. Riding the belt without
  the key strands the rover by a locked gate. The 💎 is on the other way
  onto the belt (`east(10)`).
- **16B Bridge Builder**: flags 1 to 3, a trench two wide, and two boulders.
  Only the one in the wall's gap can reach the trench (the other jams against
  rock). Push it in, then jump the other half: 9 drives by hand.
- **16C Supply Line**: Cargo Run's shuttle, but every row has a crater in a
  different place, so `distance()` finds it and `jump()` crosses it, both ways.
  The 🔢 star wants no typed-in numbers:
  ```python
  for i in range(4):
      south(i)
      east(distance("east"))
      jump("east")
      east(distance("east"))
      west(distance("west"))
      jump("west")
      west(distance("west"))
      north(i)
  ```
- **16D Your Expedition** (per student): two-thick rock, a crater trench, a
  belt into a crater, a boulder before a wide trench and a gate with its key
  on the way, in a different order on every planet. 9D's, 10D's, 13D's and
  14D's programs all miss; one loop that tells the squares apart reaches it:
  ```python
  while not at_beacon():
      if look("east") == "rock":
          drill("east")
      elif look("east") == "crater" or look("east") == "belt":
          jump("east")
      else:
          east()
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
