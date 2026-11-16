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
   page can pick one of 20 pals from the gallery, three ways: 🖍️ colour it in,
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
   button in the Hang out. Fifteen more missions come after it, for students who finish.

A big button at the top right always says what comes next. On Code, that's **💻 Next mission**
once the open mission is done, and 🎬 Free stage once every mission is finished, so
it never pulls a student out of a mission halfway. The 🎉 Hang out tab is always there too.

## The missions

24 missions and 72 stars. The first star opens the next mission, and the other two are
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

The last fifteen come after My Move on purpose, so a student who has already made their
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
rules: every command the student has learned works, plus ten **stage toys** no mission
teaches: `scene("beach")`, `sound("tada")`, `rain()`, `snow()`, `friend("cat")`,
`friend_say("Hi!")`, `friend_jump()`, `bye()`, `hide()` and `appear()`. All words says what
each one does. Some places open with stars from missions: the stage, park, beach and night
are open from the start, then the wedding at 20 ★, snowy at 30, candy at 40, space at 50 and
the castle at 60. Asking for a locked one says how many stars it needs and which are open. **💡 Give me an idea** (where Help me usually is) offers seven small shows to
start from, one at a time: a day at the beach, a friend comes to play, a magic trick and so on.
**Use this idea** puts it under their own code, never over it. The first show of 5 steps or
more earns the 🎬 Show Maker trophy, and a show that long puts "🎬 Mia made a show on the Free
stage" on the projector's list of moments, at most once every 5 minutes for each student.
Their show's code is kept, and no coins are paid for it: it's for making things. A command from a mission they haven't reached yet says it
comes in a later chapter.

**Error messages talk about the line itself:** `feel(happy)` says to write `feel("happy")`,
`right(five)` asks for a number, `name = Luna` says `name = "Luna"`, `Name` when the variable
is `name` says capitals matter, `say("I am " name)` says to add a `+`, using a `def` above
where it's made says to move it up, `name == "Luna"` on its own says one `=` keeps a value,
`"Luna" = name` says the name goes first, and a slip like `nam` for `name` asks "Did you mean
name?". **🔈 Read it** on any error reads it out loud, saying a lone `)` as "close bracket".
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
No code is needed once they're in.

- **One long world:** the places sit side by side, and the camera follows your pal. Walk
  to the edge of the screen to reach the next place. A full party meter makes the world
  longer. 🏞️ Place jumps just that student somewhere, not the whole class.
- **Walking:** click the ground. Arrow keys work too.
- **Toys (pink rings):** click the fountain, trampoline, snowman, rocket and so on. The pal
  walks over and it goes off for everyone nearby.
- **🖼️ Art:** a student picks one of their drawings and clicks the world to leave it
  there for everyone, up to 5 each. They stay between classes. Clicking one on the Art
  tab takes it back, and deleting the drawing removes it. On `/pixel/teacher` you can
  remove one student's, or all of them.
- **💎 Gems:** three in each place. Each student finds their own. All of them earns
  Treasure Hunter.
- **High-fives:** click a classmate's pal. Your pal walks over, and a first high-five
  adds a friend for both of them.
- **Sitting and reading:** click a glowing spot in front of a bench, towel or snowman
  and the pal walks over and sits. 🪑 Sit and 📖 Read in the Do tab work anywhere. A pal
  stays put until it walks away.
- **Buddies:** up to 3 of a student's other drawings come along, smaller, and wander
  near their pal. They join in with its dances and naps, and sit when it sits. A new
  drawing shows up the next time the student comes back to the Hang out.
- **✨ My Move:** the student's pal does their routine in a spotlight, and everyone else
  gets a 👏 Clap button while it plays. It can be pressed again after a few seconds.
- **👋 Do, 💬 Say, 🎉 Party, 🏞️ Place:** moves, words to tap, things to throw, and where
  everyone is.
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
- **🛍️ Shop:** 15 things to wear, 12 things for a home, and 6 walls and floors, from 15
  to 90 coins. A student clicks a thing twice to buy it. Shop things never come out of
  a gift box.
- **🔓 Unlocks:** 🧢 Me shows every hat, face and sparkle, including the locked ones,
  with how to get each (🎁 gift box, 🛍️ price, 🎉 class party, or a goal). Seven
  things unlock by themselves at a goal: Gem crown (9 gems), Space helmet (all 21
  gems), Fish hat (5 kinds of fish), Friendship sparkles (5 high-fives), Gold shades
  (10 game rounds), Dragon horns (15 stars) and Superstar sparkles (27 stars). The
  three closest goals sit at the top of Me with a bar, and a big 🔓 UNLOCKED! banner
  shows in the Hang out when one is reached.
- **🏠 Home:** every student has a room of their own. In it they pick a thing and click
  the floor to put it there, change the walls and floor, and hang up to 5 drawings with
  🖼️ Art. A rug and a pot plant are free. Friends visit from the Home tab, and the door
  goes back outside. A student's screen shows only the pals in the same place. The
  projector can look into any home: **Look at** lists Outside and every home with
  someone in it, and clicking a name in **Who's here** goes to that pal, inside or out.
  Each name says where they are and what they're doing (💃 Dancing, 🎣 Fishing,
  🛋️ Decorating...). 🎬 Auto takes turns with everyone, homes included, and the
  screen goes back outside when a home empties.
- **🎣 Fishing:** the pier at the Beach has a blue ring. The pal walks over and casts,
  and when ❗ A bite! shows, a click anywhere on the picture reels it in. There are 8
  things to catch, kept in the fish book in 🧢 Me.
- **Games:** any student can start a 💻 Code race, Tag, Hide & seek, Red light green light,
  or Copy the dance, and friends choose to join. In the race, each press of Run or → is one short
  run, and moving on red sends a pal back a bit. In the dance, the moves stay on the
  screen with the next one lit, for 3 rounds that get longer.

**💻 Code race: coding together.** Everyone in the race gets the same small job, shown
in the bar above the world with pictures of the moves ("Jump 2 times. 🦘 🦘"). They build
the code by tapping green commands (typing works too). 🔁 for picks the 3 so they can type
a new number, and **⇤ Out of loop** sends the next command back out of the loop. ▶ Run
my code checks it. A miss says what the pal did against what the job wants ("Your pal
did 🦘. The job is 🦘 🦘."), or gives the bug and its line. A solve makes that pal do the
code in a spotlight for everyone, with a 👏 Clap button for the others, and pays 3 coding
coins. Solving is 1 point and solving first is 2. There are 3 jobs, each harder: commands
in order, then a loop, then more than one thing in a loop. Between jobs, everyone sees the
fastest code, or one way to do it if time ran out. 💡 Help gives a tip, and the whole
answer after 30 seconds. Friends can join part way through, and players can clap and use
💬 Say while they race. The jobs are `RACE_JOBS` in `pixel.py`. A solver's code is only
shown to the class if its words are on the tap list or are the job's own words, and it
has no comments, unless typing is on.

On `/pixel/teacher` you can close the Hang out, start a party, a star shower or a
**💻 Code race for everyone** (everyone outside in the Hang out is put in it, and the race
starts 15 seconds later; anyone can leave), and see who's there. The Hang out reopens if
the server restarts, and nothing in the room itself is saved, but gifts, friends, My Moves,
coins, homes, fish and the party meter are. During a Code race, the projector shows the
job, who has solved it, and the fastest code between jobs.

**Words:** students tap words from a list. `say()` takes any words, so a My Move only
shows lines that are on that list, and a line that isn't gets left out. **Let them type
their own words** turns typing on for the room and for My Moves, and what they say shows
on your page. A My Move's name is picked from a list.

**🌿 Calm** at the top of the page cuts the flying bits, stops the wiggling, and holds
the background still. It's remembered on each computer, and it starts on for anyone
whose computer is set to reduce motion.

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
- **Shared laptops:** a student who lands in someone else's account presses **Not (name)?**
  in My drawings and types their own name. Typing a name again brings back that
  student's work.
- **Reading:** the 🔈 Read button on a mission reads it aloud with the laptop's own voice.
- **🐢 Slow**, at the end of the bar under the stage, plays shows at half speed, so a student
  can follow the lit-up line as each one runs. It's remembered on each computer.
- **Stuck students:** the teacher page marks anyone with 3 misses or more on a
  mission, and shows their last error. With the guide off, Help me gives two or three
  hints, and the last one is a working answer.
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
