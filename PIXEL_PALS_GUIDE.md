# Pixel Pals: teacher guide

Students draw a character, code it with real Python, then hang out together. It was
made for students who find "get the robot to the exit" pointless: the goal is to make
your own character do something fun, and show the class.

## The pages

| Page | Who it's for |
|---|---|
| `/pixel` | Students: 🎨 Draw, 💻 Code, 🎉 Hang out |
| `/pixel/teacher` | You: who's stuck, opening missions, the Hang out. Needs the admin key |
| `/pixel/show` | The projector: the Hang out, the party meter and the class's recent moments |

Both teacher pages are linked from `/admin`.

## How a class goes

1. Students open `/pixel`, type their name and draw a pal. Anyone stuck at a blank
   page can pick one of 26 pals from the gallery, three ways: 🖍️ colour it in,
   🔢 by numbers, or ⭐ ready to change. In 🔢 by numbers, squares that are already right
   (the outline, and finished ones) can't be painted over, so a stray click never leaves the
   picture impossible to finish. Swap and Move wait until it's coloured in.
2. While they draw, the little pal in the corner comes alive. It watches the pen, and
   the row of chips under it (👀 👄 💪 🦵 🐰 🐾) lights up as each part is found.
3. They press ✨ Bring to life. The pal wakes up and says hello, and they try its moves
   and fix any part the computer got wrong.
4. They press 💻 Code my pal and work through the missions. Their newest drawing is
   their pal, and "My pal" at the top swaps it. Until they've drawn something, they play
   as Pip.
5. After 3 missions, the Hang out opens and stays open.
6. Mission 9 is **My Move**. They code their own routine and it becomes a big
   button in the Hang out. Thirty-three more missions come after it, for students who finish.

A big button at the top right always says what comes next. On Code, that's **💻 Next mission**
once the open mission is done, and 🎬 Free stage once every mission is finished, so
it never pulls a student out of a mission halfway. The 🎉 Hang out tab is always there too.

## The missions

42 missions and 126 stars. The first star opens the next mission, and the other two are
for going further.

| Chapter | Missions | What it teaches |
|---|---|---|
| 🎭 Opening Night | Say hello, Jump for joy, Find the spotlight | Commands, and lines running in order |
| ✨ Come Alive | Big wave, How do you feel?, Dance floor | `wave()`, `feel()`, `dance()`, `cheer()` |
| 🔁 Again! Again! | Bounce!, Side step | `for` loops |
| 🌟 My Move | My Move | Putting it together, their own way |
| 🎪 Encore! | Grow big, Who's there? | `grow()`, `shrink()`, `shake()`, `look()` |
| 🔢 Count on Me | Count with me, Hello, everyone | The loop's `i`, and looping over a list |
| 🏷️ Name Tags | Name tag, How many? | Variables, `.upper()`, f-strings |
| 🧠 Smart Pal | Make a move, Number three | `def`, and `if` inside a loop |
| 🎲 Surprise! | Surprise mood, Roll the dice, Lucky jumps | `choice()` and `randint()`: code that does something different each time |
| 🖱️ Click Me! | Poke me!, Count the pokes | Events (`def on_click():`), `clicks()` and `else` |
| ⏳ Keep Going | Walk to the edge, Countdown | `while` loops: going round as long as the answer is yes, with `x()` and a variable that changes |
| 📋 My List | Snack list, Who's coming?, First and last | A list kept in a variable: a `for` loop over it, `len()`, `.append()`, and `[0]` / `[-1]` |
| 🏆 Keep Score | Rack up points, Big, middle, small, Hop how many? | `+=` to change a number, `if` / `elif` / `else`, and `def hop(n):` that takes a number |
| 🪆 Loop in a Loop | Clap clap, jump, Times table, Stairs | A `for` loop inside another `for` loop: the inside loop runs all the way through each time the outside one goes round |
| 🎵 Make Music | First notes, Twinkle, Make a beat | `note()`: one note, a tune kept in a list, and a beat made with a `def` |
| 🔤 Word Play | Big name, How long?, First letter | Words: repeating with `*`, counting letters with `len()`, and `word[0]` / a loop over each letter |
| 📦 Give It Back | Double it, How many jumps?, Pick a mood | `return`: a `def` that hands a value back, used inside `say()` and `range()` |

The last thirty-three come after My Move on purpose, so a student who has already made their
move doesn't have it locked behind new missions. They start easy (one new command each)
and get harder.

**🎲 Surprise! is different every time.** Each Show time! picks a new mood, dice roll or
number of jumps, so pressing it again is part of the fun. The stars are checked on many
runs behind the scenes (12, or 30 for the dice), so they mean the code works every time,
not just that it got lucky once: cheering on a 6 only counts if it never cheers on anything
else. The Guess first questions ask what *can* happen ("What's the biggest number your pal
can say?"), since what *will* happen is a surprise.

**🖱️ Click Me! makes the pal wait for a click.** The lines under `def on_click():` don't run
straight away. Pip tests the code by clicking 3 or 4 times during the show (a 👆 shows each
click), and the stars are checked on those clicks. After the show, the stage gets a dashed
yellow edge and says **👆 Now click your pal**: each click on the stage runs the code again,
and the line that's running lights up, so they can see which lines a click runs. Count the
pokes is the first `else`: say the count, cheer on the 3rd click and jump on the others.
Clicks after the show aren't saved or paid; they're for trying it. A `def on_click():` on the
Free stage works the same way, and so does `def on_key(key):` there: after the show, the arrow
keys and space go to the pal (unless they click back into the code to type), so they can make a pal
they steer: a tiny game of their own. **💡 Give me an idea** has one, "Walk with the arrow keys".

**⏳ Keep Going is `while`.** Walk to the edge uses `x()`, the spot the pal is on, so the
loop stops when the pal gets there. Countdown makes a variable smaller each time round. A
`while` that never stops says so in plain words ("Your while loop never stopped! Something
pushed in under the while has to change each time round"), and that's the bug in both of
their Fix its.

**🪆 Loop in a Loop puts one loop inside another.** In Clap clap, jump, the inside loop
waves twice, and the jump line sits one step further out, so it jumps after each pair of
waves. The whole thing happens 3 times. Times table uses the outside loop for the rows and
the inside loop for each fact, and Stairs walks one more step right each time before it
jumps. The guide pushes each line in to the right depth, and Help me says which loop a line
belongs in.

**🎵 Make Music is the chapter of notes.** `note("C")` sings one note, `note("rest")` is a
short silence, and `note("E", 2)` holds a note for 2 beats. First notes sings C, D and E.
Twinkle keeps the tune in a list, and a `for` loop sings each note on it before a long G ("little star").
Make a beat puts C, rest, G in a `def beat():`, calls it 3 times in a loop, then finishes
on a long C. The guide pushes `beat()` in under the loop and the long note back out, so
they see where a `def` and a loop end.

**🔤 Word Play is the chapter of words.** Words are kept in a variable, just like numbers.
Big name uses `name = "Luna"` and `say(name * 3)` to say the name 3 times in one bubble.
How long? counts the letters with `len(word)` and jumps that many times with
`for i in range(len(word)):`. First letter says `word[0]`, then `for letter in word:`
says every letter, and ends with a cheer. The guide shows the `"` and `*` keys, and Help
me says where to put `len()` and which line belongs inside the loop.

**📦 Give It Back is the last chapter.** A `def` can hand a value back with `return`.
Double it puts `return n * 2` in `double(n)`, so `say(double(3))` says 6 and
`say(double(5))` says 10. How many jumps? hands back `len(word)` and uses it inside
`range(jumps_for("Pip"))`, so the pal jumps once for each letter. Pick a mood uses `if`
and two `return` lines to hand back "happy" for more than 5 points and "sad" for 5 or
fewer: `feel(mood_for(8))` feels happy and `feel(mood_for(2))` feels sad. The guide
pushes the lines in under the `def`, then moves the last `return` and the calls back out,
so they see where a `def` ends. A `return` outside a `def` says it only works inside
one, and a `def` that forgets to hand a value back makes the pal say "nothing" (Python's
None), or says the number never came back.

**Every mission walks them through it.** The top says the job in one plain sentence. Under
it, the guide gives one line at a time: what the line does, the exact keys as tiles, and
the next key lit up with how to press it ("Hold Shift and press 9"). Only the right key
goes in, and a wrong one says which key to find. Capitals don't matter, Enter moves on,
and lines inside a loop get pushed in for them. When the typing is done, ▶ Show time!
glows. Pressing it early says to finish typing first.

- **✋ I can type it myself** turns the guide off for that mission, and brings back the
  story, the stars, the command buttons, Help me and All words. **🖐 Show me step by
  step** turns it back on. Each new mission starts with the guide on.
- **My Move is different,** because it's meant to be their own: they click 3 or more green
  buttons, with a count of how many they have. **Show me step by step** walks them
  through a version with a sparkle trail and a big finish.
- **If the code stops matching the steps,** the guide says so and offers **↩ Go back to
  where it was right** (which removes what doesn't match) or **✋ Keep my code**.

The guide's lines live in `coach` on each mission in `pixel.py`, and a test checks they
always add up to the working answer, which earns all three stars.

The first finish of a mission gives the big win: stars, confetti, and a 🎁 box to tap
open with something to wear in the Hang out. **Open it later** is always there, and the
gift is theirs either way.

**🔮 Guess first: reading code before running it.** The first time a student presses
Show time! on code typed with the guide, the stage waits and asks one question about what
the code will do: "How many times will confetti fall?" (Once / 4 times / 8 times), "What
number will your pal say first?" (0 / 1 / 5). The guide box says to pick a guess under the
stage. Then the show runs, so they watch to find out. A right guess pays 5 🪙. A wrong one
costs nothing and says "Good guess! It was really: ...". Only the first guess on each mission
counts, and **Just show me** (or pressing Show time! again) skips it. My Move has no guess,
because its code is theirs. The questions are `GUESSES` in `pixel.py`, and a test runs each
mission's code to check that the right answer is what really happens.

**🎨 Your turn: changing the code themselves.** The guide means students copy code, which
is the right start but not the whole thing. Once a mission is finished, a purple card asks
for one small change, with the guide off: "Make your pal jump 10 times. Keep it 2 lines!",
"Count all the way to 10", "Jump on 5 instead of 3". **Try it!** keeps their code in the
editor, and **💡 Where do I change it?** says which line or number to change, not the answer.
It counts when the mission still works and the change is there: 15 🪙 once per mission,
a 🎨 Remixer trophy the first time, and 🎨 next to the mission in Missions. If the show works
but the change isn't there yet, it says what Your turn still wants. The guide's own code
never counts. They live in `REMIXES` in `pixel.py`, and `test_pixel_turn.py` checks every one.

**🐞 Fix it: finding a bug.** Once a mission's Your turn is done, the same box turns orange
and offers **Fix Pip's code**: Pip's code for that mission with one bug in it, like
"Pip wanted 5 jumps, but the pal jumps only once!" Half the bugs stop the show with a
message (a missing  "  , `wav()`, `Dance()`, `if i = 3:`), and half run but do the wrong
thing (`range(1)`, confetti pushed into the loop, `["Ana" "Ben", "Cy"]` saying "Hi AnaBen").
**💡 Where's the bug?** says which line or idea to look at, and **↩ Pip's code again** puts
the bug back. A fix pays 15 🪙 once, the 🐞 Bug Squasher trophy the first time, and 🐞 next
to the mission in Missions. It only counts once the mission itself is finished. My Move has
none. They live in `FIXES` in `pixel.py`, and `test_pixel_fix.py` checks that every bug really
breaks the show and that the guide's code fixes it.

**🎬 Free stage: any show at all.** Finishing My Move opens the Free stage, at the bottom of
Missions (the My Move win card has a button for it too). There are no stars, no guide and no
rules: every command the student has learned works, plus eleven **stage toys** to try:
`scene("beach")`, `sound("tada")`, `note("C")`, `rain()`, `snow()`, `friend("cat")`,
`friend_say("Hi!")`, `friend_jump()`, `bye()`, `hide()` and `appear()`. All words says what
each one does. `note()` sings C, D, E, F, G, A, B, the high `C2` or `rest`, and a second
number holds it for that many beats, like `note("E", 2)`; each beat is about 0.4 seconds.
Some places open with stars from missions: the stage, park, beach and night
are open from the start, then the wedding at 20 ★, snowy at 30, candy at 40, space at 50 and
the castle at 60. Asking for a locked one says how many stars it needs and which are open. **💡 Give me an idea** (where Help me usually is) offers eight small shows to
start from, one at a time: a day at the beach, a friend comes to play, a magic trick, Sing
Twinkle Twinkle and so on.
**Use this idea** puts it under their own code, never over it. **📼 My shows** keeps up to 6
shows besides the one they're making: **🆕 New show** puts this one away and starts an empty
stage, and clicking a kept show opens it and puts away the one they were making, so nothing
is ever lost. **🗑 Delete one…** asks which, with a **Don't delete** to back out. The first show of 5 steps or
more earns the 🎬 Show Maker trophy, and a show that long puts "🎬 Mia made a show on the Free
stage" on the projector's list of moments, at most once every 5 minutes for each student.
Their show's code is kept, and no coins are paid for it: it's for making things. A command from a mission they haven't reached yet says it
comes in a later chapter.

**🎤 Show my friends** takes a Free stage show into the Hang out, once the Hang out is
open. The button sits under 📼 My shows and plays the show on the student's own pal where
they are standing, so everyone there sees it and can 👏 Clap. It plays moves, feelings,
notes, waits, hearts, stars, confetti and walking; stage-only things like `scene()` and
`rain()` quietly stay on the Free stage. A show plays for at most about 20 seconds, a
student can start another after 30 seconds, and the first one earns the 🎤 Showtime badge.
Words follow the same rule as My Move, and a code error asks them to fix it on the Free
stage first. In the Hang out's 👋 Do, a **🎤 My show** button does the same once they have
a show.

**Error messages talk about the line itself:** `feel(happy)` says to write `feel("happy")`,
`right(five)` asks for a number, `name = Luna` says `name = "Luna"`, `Name` when the variable
is `name` says capitals matter, `say("I am " name)` says to add a `+`, using a `def` above
where it's made says to move it up, `name == "Luna"` on its own says one `=` keeps a value,
`"Luna" = name` says the name goes first, and a slip like `nam` for `name` asks "Did you mean
name?". A missing `}` in an f-string says to close its `{ }`, a line that stops after `=` or
`+` says what to put next, `break` or `continue` outside a loop says to put it under a
`for` or `while`, and `return` outside a `def` says it only works inside one. A `def` that
forgets `return` makes the pal say "nothing", and a loop that needs a number from it says
the number never came back. **🔈 Read it** on any error reads it out loud, saying a lone `)` as "close bracket".
After **three misses in a row** with the guide off, the result box offers **🖐 Show me step by
step** right there.

In the Hang out, a purple **💻 Next mission** button names the next mission and its prize
(up to 50 🪙, and a 🎁 box while there are boxes left) and opens it in one click. With every
mission done, it points to a Your turn not done yet, then a Fix it, and once those are done too,
it offers the 🎬 Free stage.

The Hang out's 👋 Do and 🎉 Party buttons show their Python under the name (`wave()`,
`feel("happy")`, `hearts()`), so playing keeps reminding them what the code looks like.
A student who has drawn something but hasn't finished a mission gets a **💻 Now code my
pal →** button at the top of Draw. Once they have a star, Draw shows **💻 Keep coding →**
instead, which goes straight to their next mission, so a student back the next lesson (who
always lands on Draw) has a way back. On the teacher page, **🎨 Your turns** counts the missions
where each student changed the code themselves, with 🐞 and the number of bugs they fixed.

**My Move gets better with better code:** a `for` loop adds a sparkle trail, and 8
actions or more adds a big finish. Running the mission again updates the move.

## The Hang out

Everyone's pal is in one soft little world, and what one child taps, everyone sees.
No code is needed once they're in. The first time a student comes in, a 🎉 Welcome banner
says to click the ground to walk and that today's 🎯 jobs are in Games, and Games opens.

- **One long world:** the places sit side by side, and the camera follows your pal. Walk
  to the edge of the screen to reach the next place. A full party meter makes the world
  longer. 🏞️ Go to jumps just that student somewhere, not the whole class. A student
  arriving, or jumping somewhere, lands on a free spot with room around it, so a whole
  class arriving at once fills the Park and then spills into the next place instead of
  landing in one heap.
- **Walking:** click the ground. Arrow keys work too. 🏞️ Go to also lists everyone outside under
  **👫 Go to a friend**, which puts your pal right next to them.
- **Toys (pink rings):** click the fountain, trampoline, snowman, rocket and so on. The pal
  walks over and it goes off for everyone nearby.
- **🖼️ Art:** a student picks one of their drawings and clicks the world to leave it
  there for everyone, up to 5 each. They stay between classes. Clicking one on the Art
  tab takes it back, and deleting the drawing removes it. On `/pixel/teacher` you can
  remove one student's, or all of them.
- **💎 Gems:** three in each place. Each student finds their own. All of them earns
  Treasure Hunter.
- **🧰 Code chests:** one treasure chest in each place, opened only with code. A shut chest
  has a **🧰 Code me open!** sign over it on the student's screen. A pal that walks onto a chest
  stops beside it, so the chest stays in view. The side panel then becomes the chest and nothing
  else: "Code the chest open!", what it wants in words and pictures ("🦘 jump 2 times"),
  numbered steps, and a code box with only the green buttons that puzzle needs (🔁 for only on
  loop chests). **← Leave** goes back to the usual buttons. A miss says in a pink box what the
  pal did, what the chest wants, and the one thing to change ("So close! Just one more: 🦘
  jump()", "That's 1 too many!", "Move 1 should be..."). The Code race uses the same messages.
  Small pop-ups like the star shower are skipped while a student codes a chest, and big ones
  (class party, unlocks) wait until the chest is open or they leave. 💡 Help gives a tip, and pressing More
  help after 30 seconds shows the whole answer. Opening a chest pays 10 coding coins (no
  daily limit), and the pal acts the code out in a spotlight, so friends nearby can clap.
  The Park chest is easiest (commands in order). Chests further along want a loop, then two
  things in a loop, and Candy land and Outer space ask for counting with `i`, two loops, or
  a loop inside a loop. Some puzzles sing notes too (`note("C")`, shown as 🎵 C), or ask for
  a word 3 times in one bubble (`say("Hi" * 3)`), and the green buttons show the note names.
  Each chest opens once a day for each student. Every chest locks again the next day with a
  new puzzle, the same for the whole class, so friends can help each other. Opening every
  chest in a day puts a line on the projector, and so does being the first in the class to
  open each chest that day. While a student is at a chest, the line under the world keeps its
  puzzle in view. After opening one, **🧰 Take me to the next chest** walks them on. When "Code a chest open" is one of today's 🎯 jobs, its **🧰 Take me** button
  walks the pal to the nearest chest still shut. On the projector, every chest has a sign over
  it with its puzzle and how many have opened it today (so you can point at one and read the
  code together), and the jobs card counts the chests opened today. The teacher page lists
  today's chest puzzles with how many opened each, and a 🧰 count for each student.
  Opening 5 chests unlocks Treasure sparkles,
  and 20 (a few days' worth) unlocks the Captain hat. The puzzles are `CHEST_JOBS` in
  `pixel.py` (the Code race's jobs plus a harder fourth set), and where each chest stands
  is `CHEST_SPOTS`.
- **High-fives:** click a classmate's pal. Your pal walks over, and a first high-five
  adds a friend for both of them.
- **Sitting and reading:** click a glowing spot in front of a bench, towel or snowman
  and the pal walks over and sits. 🪑 Sit and 📖 Read in the Do tab work anywhere. A pal
  stays put until it walks away.
- **Buddies:** with **👯 Buddies: on** (next to "You are..."), up to 3 of a student's other
  drawings come along, smaller, and wander near their pal. They join in with its dances and
  naps, and sit when it sits. A new drawing shows up the next time the student comes back to
  the Hang out.
- **✨ My Move:** the student's pal does their routine in a spotlight, and everyone else
  gets a 👏 Clap button while it plays. It can be pressed again after a few seconds.
- **🎤 My show:** a student with a Free stage show gets 🎤 My show in 👋 Do. Their pal
  acts it out where everyone is standing, with a 🎤 banner and a 👏 Clap for friends, for
  up to about 20 seconds. The first one earns 🎤 Showtime, and they can start another
  after 30 seconds.
- **🪩 Dance party:** when 3 pals in one place press 💃 Dance within 4 seconds of each other,
  everyone there gets confetti and a banner, and the class party meter goes up by 1 (at most once
  a minute). Nothing on screen says so, so it's a nice one to let the class discover.
- **👋 Do, 💬 Say, 🎉 Party, 🏞️ Go to:** moves, words to tap, things to throw, and where
  everyone is. 💬 Say puts the wedding words first in the Wedding garden, and last everywhere
  else.
- **🪑 Be a prop:** next to "You are...", this turns the pal into a still picture with no
  face and no name tag, for a made-up game of finding each other. **🙂 Be me again** turns it back.
- **🧢 Me:** pick which drawing they are (students with two or more drawings also see
  a **🔄 Switch** button above the tabs), gifts to wear, and friends they've high-fived.
- **🌠 Star showers:** stars fall by surprise every few minutes. Pals run under them, and
  catches close together climb: ×2, ×3, ×4.
- **🎉 Class party meter:** a mission's first finish adds 2, and a My Move adds 1 (at most
  once every 45 seconds for each student). A full meter is a party for everyone, and
  brings something new: Snowy hill, a Golden crown, Candy land, Rainbow sparkles, then
  Outer space. After those, it's just a party.

- **🪙 Coins:** coding pays the most. A mission's first finish pays 20 coins, and every
  star pays 10, so a three-star mission is 50. Playing pays a little: a gem 3, a new
  friend 3, a caught star 1, a fish 1 (5 the first time for each kind), a finished
  game 5 and 5 more for winning. Coins from playing stop at 40 a day for each student,
  and the coin bar then says missions still pay. Students who already had stars and
  gems were paid for them.
- **🛍️ Shop:** 17 things to wear, 8 rooms to build, 32 things for a home, and 13 walls
  and floors, from 15 to 180 coins, and a **✨ Fancy** shelf on top with 7 dear things to
  save up for (Sun hat, Sparkly mask, Princess hat, Music and Butterfly sparkles, Diamond
  tiara, and the Royal crown at 200). A student clicks a thing twice to buy it. Furniture
  can be bought again and again (two beds, three balloons); everything else is bought
  once. Shop things never come out of a gift box.
- **✏️ Wear your own drawing:** in 🧢 Me, a student picks one of their drawings and puts it
  **On my head** or **On my face**, for 40 coins. Everyone sees it on their pal. It's a copy,
  cut down to what's drawn, so changing or deleting the drawing later doesn't change it. Up
  to 6 each, and 🗑 Throw one away makes room. A drawing 16 squares wide is worn as wide as
  a 16 square pal. Like 🖼️ Art, it's a drawing everyone sees straight away.
- **🔓 Unlocks:** 🧢 Me shows every hat, face and sparkle, including the locked ones,
  with how to get each (🎁 gift box, 🛍️ price, 🎉 class party, or a goal). Nine
  things unlock by themselves at a goal: Gem crown (9 gems), Space helmet (all 21
  gems), Fish hat (5 kinds of fish), Friendship sparkles (5 high-fives), Gold shades
  (10 game rounds), Dragon horns (15 stars), Superstar sparkles (27 stars), Treasure
  sparkles (5 🧰 chests) and the Captain hat (20 chests). In winter three more: Santa hat
  (5 🎁 presents), Snowflake sparkles (15 presents) and Reindeer antlers (25 ⛄ snowballs). The
  three closest goals sit at the top of Me with a bar, and a big 🔓 UNLOCKED! banner
  shows in the Hang out when one is reached.
- **🏠 Home:** every student has a home that starts as one living room. Rooms bought in
  the Shop (Bedroom, Kitchen, Playroom, Garden, Attic, Game room, Pool room, Secret
  room) join on in a row with open doorways, so the pal just walks from room to room.
  Each kind of room looks different and comes with its own walls and floor. In a room a
  student picks a thing and clicks the floor to put it there (up to 12 things a room),
  changes that room's walls and floor, and hangs up to 5 drawings in each room with
  🖼️ Art. **✋ Move my things** picks a thing up to put it somewhere else or away;
  otherwise clicking a thing plays with it (balloons pop, the piano plays, the bed
  says Zzz...). A rug and a pot plant are free.
- **🏡 Home levels:** a home grows from Tiny hut to Dream castle (7 levels) on points:
  1 for each thing out, 2 for a drawing with code, 3 for each room built, and 1 for each
  ❤️ from a visitor (up to 10). Each level wins a prize that can't be bought (Gold
  trophy, Rainbow floor, Rainbow, Golden throne, Gold floor, Unicorn), and the class feed
  says so. A level is kept once reached. A visitor can give each home one ❤️, which pays
  its owner 2 coins.
- **Visiting:** friends visit from the Home tab, and the brown door in the living room
  goes back outside. A student's screen shows only the pals in the same place. The
  projector can look into any home: **Look at** lists Outside and every home with
  someone in it, and clicking a name in **Who's here** goes to that pal, inside or out.
  Each name says where they are and what they're doing (💃 Dancing, 🎣 Fishing,
  🛋️ Decorating...). 🎬 Auto takes turns with everyone, homes included, and the
  screen goes back outside when a home empties.
- **📷 Follow (projector):** the picker next to 🎬 Auto, under the picture, keeps the camera
  on one student wherever they go, into homes and back out, with "📷 Following Mia" in the
  corner. Clicking their name in Who's here does the same. 🎬 Auto, ◀ ▶, dragging the picture
  or "📷 Follow someone…" stops it, and it goes back to Auto by itself if they leave.
- **🎣 Fishing:** the pier at the Beach has a blue ring. The pal walks over and casts,
  and when ❗ A bite! shows, a click anywhere on the picture reels it in. There are 8
  things to catch, kept in the fish book in 🧢 Me.
- **Games:** any student can start a 💻 Code race, 🎨 Draw & guess, 🍎 Apple grab, ⚽ Pal ball, Tag, Hide & seek, Red
  light green light, or Copy the dance, and friends choose to join. While a game waits for players, the bar
  above the world turns yellow for everyone not in it ("👉 Tap here to join!"), and one tap
  joins. In the race, each press of Run or → is one short run, and moving on red sends a pal
  back a bit. In the dance, the moves stay on the screen with the next one lit, for 3 rounds
  that get longer. When a round starts, the side panel opens Games and hides My Move and
  Next mission until it ends, so the game's buttons fit on a small laptop, and the line
  under the world says what to do in that game ("You're IT! Click near a friend to tag
  them.").
- **🎯 Today's jobs:** three small things to do, at the top of Games, the same for the whole
  class each day so friends can help each other: high-five 2 friends, catch 3 falling stars,
  find a gem, catch something at the pier, finish a game with friends, grab 5 apples in
  🍎 Apple grab, score a goal in ⚽ Pal ball, solve a Code race job, earn a star in a coding
  mission, code a 🧰 chest open, clap for a friend's move, visit a friend's home, or dance at
  the same time as 2 friends (a 🪩 dance party). The apple and ball jobs happen in a game with
  2 or more players, like the game job. A goal counts for every player on the scoring
  team, so a teammate's kick helps everyone on that team. Every day has at least one coding job
  (a mission star, a Code race job or a chest), so playing leads back to coding. The apple job
  counts each apple a student's pal grabs, and the ball job counts a goal for each player on the
  scoring team, once a day. The star job has
  a **💻 Go code** button that opens the next mission. A gem job is swapped for another once
  a student has found every gem, and a star job for the Code race once they have every star.
  Each job pays 5 play coins, and all three open a 🎁 gift box (15 coins once every box gift
  is theirs) and add 2 to the class party meter. The bar above the world counts them ("🎯 1
  of 3 jobs"), the projector lists the day's three so you can point at them, and Just now
  cheers anyone who does all three. The jobs are `DAY_JOBS` in `server.py`.

**💻 Code race: coding together.** Everyone in the race gets the same small job, shown in the
bar above the world with pictures of the moves ("Jump 2 times. 🦘 🦘"). They build the code by
tapping green commands (typing works too). 🔁 for picks the 3 so they can type a new number,
and **⇤ Out of loop** sends the next command back out of the loop. ▶ Run my code checks it.
A miss says what the pal did against what the job wants ("Your pal did 🦘. The job is 🦘 🦘."),
or gives the bug and its line. A solve makes that pal do the code in a spotlight for
everyone, with a 👏 Clap button for the others, and pays 3 coding coins. Solving is 1 point
and solving first is 2. There are 3 rounds, each harder: commands in order, then a loop, then
more than one thing in a loop. New small jobs also sing notes (`note("C")`, with 🎵 C in the
bar and on the green buttons) and can say a word 3 times in one bubble (`say("Hi" * 3)`). A
close miss says what to change: "Move 2 should be 🎵 E, but your pal sang 🎵 D", or "So close!
Just one more: 🎵 C." For a job with a loop inside a loop, a miss says to put one loop inside
the other. Between jobs, everyone sees the fastest code, or one way to do it if time ran out.
A student who has solved the job gets a **🌟 Bonus**: do the whole job 2 times. Their code
stays in the box, so copying the lines again works, and putting it all
in a loop is the neat way. It pays 1 coding coin and plays in the spotlight, but gives no
race points, so it never changes who wins. 💡 Help gives a tip, and the whole answer after 30
seconds. Friends can join part way through, and players can clap and use 💬 Say while they
race. The jobs are `RACE_JOBS` in `pixel.py`. A solver's code is only shown to the class if
its words are on the tap list or are the job's own words, and it has no comments, unless
typing is on.

**🎨 Draw & guess.** Up to 5 pictures, one for each player, and whoever drew longest ago
draws first, so a big class takes turns across games. The drawer is shown a secret word
with its picture ("🤫 Draw this: 🐱 Cat") and clicks squares on a 12 by 12 grid, with 10
colours and a 🧽 to rub out (dragging works too, but is never needed). The picture grows on
a big easel in the middle of the Park, for everyone and on the projector. The others tap
one of 6 pictures with words, so nobody types or spells. A wrong guess greys the pictures
for 3 seconds, so tapping all of them isn't the way to win. The first right guess is 3
points, the second 2, then 1, and the drawer gets 1 for each friend who guesses. Each picture
has 60 seconds, then everyone sees what it was. The word is never sent to a guesser's screen
or the projector until then. The words are `GUESS_WORDS` in `pixel.py`. A drawer could still
write letters; the tip asks them not to.

**🍎 Apple grab.** A 60-second round for 2 or more players. Five apples lie in the Park and
Wedding garden, in new random spots each round, and a new one appears as soon as one is
taken. A pal grabs an apple by walking onto it (click the ground or use the arrow keys), and
the server decides the grab, so everyone sees the same apples. A ⭐ golden apple is worth 3.
The panel lists every player's count as it changes, so the class can see who is ahead. The
most apples when the 60 seconds end wins, and a tie shares the win. It pays coins and
class-party points, with the first-game gift and the 🍎 Apple Picker badge, exactly like the
other games. In 🌿 Calm the apples stay still.

**⚽ Pal ball.** A 90-second round for 2 or more players. Players are put on teams in join
order: the first is 🔵 Blue, the next 🟠 Orange, then Blue again, so odd numbers are fine.
Blue kicks right, into the blue goal; Orange kicks left, into the orange goal. One big ball
starts in the middle of the Park and Wedding garden, and a pal kicks it by walking into it
(click the ground or use the arrow keys). The server moves the ball, slows it with friction
and bounces it off the top and bottom of the ground, so everyone sees the same ball and the
same goals. A goal rests the ball in the net for 2 seconds, then puts it back in the middle
and adds 1 to that team's score. The team with more goals when the 90 seconds end wins, and
a draw shares the win. Each player's pal has a small blue or orange ring under it for the
round, and a sign over each goal says whose it is. It pays coins and class-party points,
with the first-game gift and the ⚽ Ball Player badge, exactly like the other games. In
🌿 Calm the ball does not spin.

**❄️ The Snow Village.** From 16 November to 31 December, the world has one more place at its
far end: a snowy evening village. Students get there by walking, from 🏞️ Go to, or with
**❄️ Take me** on the Snow Village card in Games, and each one sees a one-time banner saying
it's open. In it:
- **🎄 The class tree:** walking up to it (or clicking it) opens a pane where a student hangs
  one of their drawings on it. One each, swapped by picking another, and up to 28 on the tree,
  the oldest going first. The star on top lights up at 10. On `/pixel/teacher`, an ornament
  counts as one of the student's drawings left in the world, so **Remove (name)'s** and
  **Remove all** take ornaments down too.
- **⛄ The class snowman:** each click on it rolls one snowball onto the same snowman. 30
  finish it, with confetti and a banner for everyone, and it joins a row of finished snowmen
  at the back. The first 3 snowmen each day add 2 to the class party meter.
- **🎁 Presents:** five each day, one in each of the Park, Wedding, Beach, Night and the
  Snow Village, in new spots every day and the same spots for everyone. Each student finds
  their own, for 2 play coins.

The projector shows the snowman count and how many drawings are on the tree in the jobs
card. The dates are `WINTER_FROM` and `WINTER_TO` in `pixel.py`. The village is never part of
the gem hunt or the chests, so nothing anyone needs for a goal goes away in January. A
drawing left out with 🖼️ Art in the Snow Village moves into the next place if the class
party meter opens a new place, because the village always stays last.

On `/pixel/teacher` you can close the Hang out, start a party, a star shower or a **💻 Code
race for everyone** (everyone outside in the Hang out is put in it, and the race starts 15
seconds later; anyone can leave), and see who's there. When a student has a game going, the
page says which one and how long is left, and **⏹ End this game** stops it with no prizes,
so a Code race for everyone can start. **📸 Class photo** lines up everyone outside in the
Park in rows, in name order, and the projector looks there and says "Say cheese!" so you can
take a picture. For a minute and a half the projector also has **💾 Save the photo**, which downloads the picture
with everyone's name tags. Press 🎬 Auto on the projector afterwards. The Hang out column says where
each student is and what they're doing (🌳 Park, 💃 Dancing, 🎮 In a game), and how many of
today's jobs they've done (🎯 2 of 3). The Hang out reopens if the server restarts, and
nothing in the room itself is saved, but gifts, friends, My Moves, coins, homes, fish and
the party meter are. During any game, the projector has a card for it (who's IT, the light,
the dance, who's been found), and 🎬 Auto follows whoever is IT or seeking. During a Code
race, it shows the job, who has solved it, and the fastest code between jobs.

**📊 Where the class is** sits above Who's where. It has one small tile for each of the
17 chapters, with its icon, a short name and how many students have their open,
unfinished mission in that chapter. **🌱 Not started** counts students who haven't run
a mission yet, and **🏁 All done** counts students who have finished every mission. A
tile with 0 is faded. Click a tile to highlight those students in Who's where; click it
again to show everyone. It updates with the rest of the page every 8 seconds.

**Words:** students tap words from a list. `say()` takes any words, so a My Move only
shows lines that are on that list, and a line that isn't gets left out. **Let them type
their own words** turns typing on for the room and for My Moves, and what they say shows
on your page. A My Move's name is picked from a list.

**🌿 Calm** at the top of the page cuts the flying bits, stops the wiggling, and holds
the background still. It's remembered on each computer, and it starts on for anyone
whose computer is set to reduce motion. In the Hang out, **🏷️ Hide names** next to it hides the name tags
over the pals on that screen.

## How a pal comes alive

The computer reads the drawing and works out its parts, with no setup. Thin things
sticking out are arms, ears or tails, depending on where they join. Gaps at the bottom
are legs, and gaps at the top are ears. Two dark dots in a pair are eyes, and a mark
under them is the mouth. Everything stays on the drawing's own squares, so it still
looks like pixel art when it moves.

It's a good guess, not a perfect one. Arms drawn flat against the body have no gap to
find, and a long skirt can count as legs. After ✨ Bring to life, a student presses a
part (💪 Arm, say) and clicks the right squares, which overrules the guess. **Guess
again** clears those marks. A pal with no eyes can't blink, so the page asks for eyes.

**Turn into frames** puts a move into the student's frames to change by hand, and
**Download a GIF** saves it to keep.

A pal left alone is still alive: it fidgets, wanders, and falls asleep after 30 seconds
until someone moves the pointer over it. Clicking the ground makes it walk there, and
clicking the pal makes it giggle.

## Things worth knowing

- **Touchpads:** one click colours a square, and shapes go click-then-click. For
  drawing long lines, turn on **Easy pen**: click to put the pen down, slide, click
  to stop. It's remembered on each computer. A pinch zooms, and two fingers slide
  around a zoomed picture.
- **Tools worth showing the class:** Mirror draws both sides at once, so one eye stamp
  makes a pair. Shade makes colours darker or lighter. Swap recolours a whole pal in
  one click. Move picks up part of a drawing. More has Add outline.
- **Small school laptops:** on a 1366×768 or 1280×720 screen the Hang out cards
  shrink so the tabs and buttons stay in view. Games shows the games above the
  seasonal Snow Village card, 🎤 My show sits first in 👋 Do, and the Missions
  sheet keeps its title and Close button in view when it jumps to the mission
  the student is on.
- **Shared laptops:** a student who lands in someone else's account presses **Not (name)?**
  in My drawings and types their own name. Typing a name again brings back that
  student's work.
- **Reading:** the 🔈 Read button on a mission reads it aloud with the laptop's own voice.
- **🐢 Slow**, at the end of the bar under the stage, plays shows at half speed, so a student
  can follow the lit-up line as each one runs. It's remembered on each computer.
- **Stuck students:** the teacher page marks anyone with 3 misses or more on a
  mission, and shows their last error. With the guide off, Help me gives two or three
  hints, and the last one is a working answer.
- **If something goes wrong:** a muddled tap from a browser (a missing field, or a list
  where a word belongs) gets a short "bad" answer, not a dropped connection. A student
  who leaves in the middle of a race doesn't leave the round stuck: the next pal to the
  flag wins.
- **Opening missions:** "Open up to here" on the teacher page lets everyone reach a
  mission. Opening past Find the spotlight opens the Hang out for everyone too.

**🖨️ Print a class poster** on the teacher page prints everyone's current pal with
their name, so check it before pinning it up.

## A first lesson

1. **5 minutes, before they arrive:** start the server, open `/pixel/show` on the
   projector and `/pixel/teacher` on your laptop. Listen to the sound level.
2. **5 minutes:** students join and pick a gallery pal. Unsure students do 🔢 By numbers.
3. **15 minutes:** they change it or draw their own. Show Mirror and stamps on the
   projector. Point out the chips lighting up as parts appear.
4. **5 minutes:** ✨ Bring to life. Let them poke it and try every move.
5. **15 minutes:** 💻 Code, and the first three missions. The Hang out opens as they finish.
6. **15 minutes:** hang out, and keep going to My Move. Press 🌠 Star shower now if the
   room needs a lift. Anyone who finishes My Move has the 🎬 Free stage to make whatever
   they like, so fast finishers always have something to code.
7. **5 minutes, to finish:** press 💻 Code race for everyone and read the fastest code
   together on the projector between jobs.

## Off-screen fun

- **See the code** in 🎨 Draw shows the drawing as rows of letters. Change one and
  the picture changes.
- **Bead pattern** prints the drawing as a pegboard pattern with bead counts, for
  Perler beads or cross-stitch.
