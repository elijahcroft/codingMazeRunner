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
   🔢 by numbers, or ⭐ ready to change.
2. While they draw, the little pal in the corner comes alive. It watches the pen, and
   the row of chips under it (👀 👄 💪 🦵 🐰 🐾) lights up as each part is found.
3. They press ✨ Bring to life. The pal wakes up and says hello, and they try its moves
   and fix any part the computer got wrong.
4. They press 💻 Code my pal and work through the missions. Their newest drawing is
   their pal, and "My pal" at the top swaps it. Until they've drawn something, they play
   as Pip.
5. After 3 missions, the Hang out opens and stays open.
6. The last mission is **My Move**. They code their own routine and it becomes a big
   button in the Hang out.

A big button at the top right always says what comes next.

## The missions

9 missions and 27 stars. The first star opens the next mission, and the other two are
for going further.

| Chapter | Missions | What it teaches |
|---|---|---|
| 🎭 Opening Night | Say hello, Jump for joy, Find the spotlight | Commands, and lines running in order |
| ✨ Come Alive | Big wave, How do you feel?, Dance floor | `wave()`, `feel()`, `dance()`, `cheer()` |
| 🔁 Again! Again! | Bounce!, Side step | `for` loops |
| 🌟 My Move | My Move | Putting it together, their own way |

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
  (10 game rounds), Dragon horns (15 stars) and Superstar sparkles (all 27 stars). The
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
- **Games:** any student can start Tag, Hide & seek, Red light green light, or Copy the
  dance, and friends choose to join. In the race, each press of Run or → is one short
  run, and moving on red sends a pal back a bit. In the dance, the moves stay on the
  screen with the next one lit, for 3 rounds that get longer.

On `/pixel/teacher` you can close the Hang out, start a party or a star shower, and see
who's there. It reopens if the server restarts, and nothing in the room itself is saved,
but gifts, friends, My Moves, coins, homes, fish and the party meter are.

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
- **Reading:** the 🔈 button on a mission reads it aloud with the laptop's own voice.
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
   room needs a lift.

## Off-screen fun

- **See the code** in 🎨 Draw shows the drawing as rows of letters. Change one and
  the picture changes.
- **Bead pattern** prints the drawing as a pegboard pattern with bead counts, for
  Perler beads or cross-stitch.
