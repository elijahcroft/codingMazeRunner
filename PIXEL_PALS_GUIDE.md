# Pixel Pals: teacher guide

Students draw a character, then bring it to life with real Python. It was made
for students who find "get the robot to the exit" pointless: the goal is to make
your own character do something lovely, funny or playable, and show the class.

## The pages

| Page | Who it's for |
|---|---|
| `/pixel` | Students: 🎨 Draw, 💓 Life, 🎭 Stage, 🎟️ Theatre |
| `/pixel/teacher` | You: who's stuck, opening missions, hiding shows. Needs the admin key |
| `/pixel/show` | The projector: class shows on a loop, the star meter and a parade of pals |

Both teacher pages are linked from `/admin`.

## How a class goes

1. Students open `/pixel`, type their name and draw a pal. Anyone stuck at a blank
   page can pick one of 18 pals from the gallery, three ways: 🖍️ colour it in,
   🔢 by numbers, or ⭐ ready to change.
2. While they draw, the little pal in the corner comes alive. It watches the pen, and
   the row of chips under it (👀 👄 💪 🦵 🐰 🐾) lights up as each part is found.
3. They press ✨ Bring to life. On the 💓 Life tab the pal wakes up and says hello, and
   they try its moves, make it talk, and fix any part the computer got wrong.
4. They press 🎭 Stage. Their newest drawing is their pal, and "My pal" at the top
   swaps it. Until they've drawn something, they play as Pip.
5. They work through the missions. The first star opens the next one, and the
   other two are for going further.
6. Free Stage opens after Jump for joy. From there they can add one show to the
   Theatre, for the class to watch, ♥ and remix. Their pal also joins the Class Park
   at the top of the Theatre, where shared pals wander about together.

## How a pal comes alive

The computer reads the drawing and works out its parts, with no setup. Thin things
sticking out are arms, ears or tails, depending on where they join. Gaps at the bottom
are legs, and gaps at the top are ears. Two dark dots in a pair are eyes, and a mark
under them is the mouth. Everything stays on the drawing's own squares, so it still
looks like pixel art when it moves.

It's a good guess, not a perfect one. Arms drawn flat against the body have no gap to
find, and a long skirt can count as legs. On the Life tab a student presses a part
(💪 Arm, say) and clicks the right squares, which overrules the guess. **Guess again**
clears those marks. A pal with no eyes can't blink, so the page asks for eyes.

**Turn into frames** puts a move into the student's frames to change by hand, and
**Download a GIF** saves it to keep.

A pal left alone is still alive: it fidgets, wanders, and falls asleep after 30 seconds
until someone moves the pointer over it. Clicking the ground makes it walk there, and
clicking the pal makes it giggle.

## For fast finishers

All of these are on the 💓 Life tab, with no code needed:

- **🌟 Catch stars:** 30 seconds of running under falling stars by sliding a finger on
  the touchpad. A student's new best score goes on the projector's feed.
- **🧠 Copy me:** the pal does a row of moves and the student presses them back. The
  row grows each time. It's the idea of running commands in order, in disguise.
- **🃏 Pal card:** a trading card of their pal to print or download.
- **🏞️ Place:** takes the pal to the next scene they've opened.

## The missions

37 missions in 8 chapters, 111 stars.

| Chapter | What it teaches |
|---|---|
| 🎭 Opening Night | Commands, and lines running in order |
| ✨ Come Alive | `wave()`, `look()`, `feel()`, `dance()`, `cheer()`: the pal's own parts |
| 🔁 Again! Again! | `for` loops, lists, and why animation is a loop |
| 🏷️ Name Tags | Variables, f-strings, `x()` |
| 📖 Story Time | `def`, parameters, two-character stories |
| 🎲 Surprise! | `if`, `elif`, `else`, `while`, `choice()` |
| 🐾 Pet Pal | `on_click`, `on_feed` and friends: code that waits for you |
| 🕹️ Game Maker | `on_key`, `randint()`, and a real little game |

The help comes off slowly. Up to Name Tags a command button writes the whole line.
From Story Time it starts the line and the student types the rest. Only the
chapter's new words stay by the editor, and All words holds everything else.

## Things worth knowing

- **Touchpads:** one click colours a square, and shapes go click-then-click. For
  drawing long lines, turn on **Easy pen**: click to put the pen down, slide, click
  to stop. It's remembered on each computer. A pinch zooms, and two fingers slide
  around a zoomed picture.
- **Tools worth showing the class:** Mirror draws both sides at once, so one eye stamp
  makes a pair. Shade makes colours darker or lighter. Swap recolours a whole pal in
  one click. Move picks up part of a drawing. More has Add outline.
- **Poses:** `pose("happy")` shows a frame named happy if there is one. If not, the
  pal makes that face by itself. In 🎨 Draw, press ⋯ beside the frames to name one.
  `pose(2)` works with no name at all.
- **Checking shows:** drawings are private until a student adds a show to the Theatre.
  `say()` takes any words, so a new show waits on `/pixel/teacher` until you press
  **Let it in**. Nothing about it appears in the Theatre, the Class Park or on the
  projector until then. Untick **Check shows before the class sees them** and shows
  go straight up, and you can still Hide one later. Words typed on the Life tab stay
  on that student's screen.
- **Shared laptops:** a student who lands in someone else's account presses **Not (name)?**
  in My drawings and types their own name. Typing a name again brings back that
  student's work.
- **Pals visiting each other:** in Free Stage, `friend("Mia")` brings Mia's own pal on
  stage, once her show is in the Theatre. All words lists who can come. If her show
  is taken down later, shows that used her pal carry on with a stand-in.
- **Easy pen:** it starts off, because a first click that leaves a line following the
  finger is confusing. A student clicking along a line square by square gets offered
  it once, with a button.
- **Reading:** the 🔈 button on a mission reads it aloud with the laptop's own voice.
- **Stuck students:** the teacher page marks anyone with 3 misses or more on a
  mission, and shows their last error. Help me gives two or three hints, and the
  last one is a working answer.
- **Opening missions:** "Open up to here" on the teacher page lets everyone reach a
  mission, so a class can start at Pet Pal if you like.
- **Unlocks:** stars open scenes, sounds and friends. The castle opens for everyone
  at 150 class stars.

## A first lesson

1. **5 minutes, before they arrive:** start the server, open `/pixel/show` on the
   projector and `/pixel/teacher` on your laptop. Try a Bunny yourself and listen to the
   sound level.
2. **5 minutes:** students join and pick a gallery pal. Unsure students do 🔢 By numbers.
3. **15 minutes:** they change it or draw their own. Show Mirror and stamps on the
   projector. Point out the chips lighting up as parts appear.
4. **10 minutes:** ✨ Bring to life. Let them poke it and try every move.
5. **15 minutes:** 🎭 Stage, Opening Night and Come Alive. Fast finishers go to the
   Life games.
6. **5 minutes:** students add a show to the Theatre. Let some in, press 🎉 Dance party,
   and let the projector do the rest.

## Off-screen fun

- **See the code** in 🎨 Draw shows the drawing as rows of letters. Change one and
  the picture changes.
- **Bead pattern** prints the drawing as a pegboard pattern with bead counts, for
  Perler beads or cross-stitch.
