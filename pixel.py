"""Pixel Pals: students draw characters, then bring them to life with Python.

The Studio at /pixel is the drawing app. A drawing is a palette and a list of
frames, and a frame is a string with one letter per square, left to right and
top to bottom: "." is an empty square and any other letter is a place in the
palette. Frames can have a name, so code can say  pose("happy").

The Stage is where a program runs. Like Cake Shop, a program runs once on the
server inside the whitelist interpreter, and its commands build a list of steps
that the browser plays back. Pets and mini games need clicks and keys, which
can come in any order, so those work by replaying: each new click runs the
program again with every click so far, and sends back only the newest answer.
Nothing is kept running between clicks, so the server has nothing to clean up.
"""

import ast
import difflib
import random
import re
from collections import Counter

from cycles import Brain, BotError, _Frame, _TooLong, syntax_message

SIZES = (16, 24, 32, 48)
SPEEDS = (3, 6, 10)         # frames a second: slow, medium, fast
MAX_DRAWINGS = 12
MAX_FRAMES = 12
TITLE_MAX = 24
POSE_NAMES = ("happy", "sad", "wave", "cool", "surprised", "sleepy", "angry", "silly",
              "walk", "jump", "dance", "hello")
LETTERS = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
MAX_COLOURS = len(LETTERS)
MARK_LETTERS = ".aletwomb"

_KEY = re.compile(r"[a-z0-9]{1,12}\Z")
_COLOUR = re.compile(r"#[0-9a-f]{6}\Z")


def clean_drawing(raw):
    """A drawing that's safe to keep, or None if this one isn't."""
    if not isinstance(raw, dict):
        return None
    key, size, speed = raw.get("key"), raw.get("size"), raw.get("speed")
    palette, frames = raw.get("palette"), raw.get("frames")
    if not isinstance(key, str) or not _KEY.match(key):
        return None
    if size not in SIZES or speed not in SPEEDS:
        return None
    if not isinstance(palette, list) or not 1 <= len(palette) <= MAX_COLOURS:
        return None
    if not all(isinstance(c, str) and _COLOUR.match(c) for c in palette):
        return None
    if not isinstance(frames, list) or not 1 <= len(frames) <= MAX_FRAMES:
        return None
    allowed = set(LETTERS[:len(palette)]) | {"."}
    for frame in frames:
        if not isinstance(frame, str) or len(frame) != size * size or set(frame) - allowed:
            return None
    title = raw.get("title")
    title = title.strip()[:TITLE_MAX] if isinstance(title, str) else ""
    # One name per frame, or "" for none. Older drawings have no names at all.
    names = raw.get("names")
    if not isinstance(names, list) or len(names) != len(frames):
        names = [""] * len(frames)
    names = [n if n in POSE_NAMES else "" for n in names]
    # Which squares the student marked as arms, legs and so on. Empty means the
    # computer works it all out by itself.
    marks = raw.get("marks")
    if not isinstance(marks, str) or len(marks) != size * size or set(marks) - set(MARK_LETTERS):
        marks = ""
    # The finished picture, for a colour-by-numbers that's still being coloured.
    guide = raw.get("guide")
    if not isinstance(guide, str) or len(guide) != size * size or set(guide) - allowed:
        guide = ""
    return {"key": key, "title": title, "size": size, "speed": speed, "palette": palette,
            "frames": frames, "names": names, "marks": marks, "guide": guide}


def save_drawing(drawings, raw):
    """Keep a drawing, newest first. Returns an error word, or None if it went in."""
    drawing = clean_drawing(raw)
    if not drawing:
        return "bad"
    rest = [d for d in drawings if d["key"] != drawing["key"]]
    if len(rest) >= MAX_DRAWINGS:
        return "full"
    drawings[:] = [drawing] + rest
    return None


def delete_drawing(drawings, key):
    drawings[:] = [d for d in drawings if d["key"] != key]


# ---- Pip: the pal everyone starts with, until they've drawn their own ---------

def _pip_rows(eyes="kwwwkwwwwkwwwk", mouth=".kwwwwkkkkwwwwk.", cheek=".kwwwkwwwwkwwwk."):
    return ["................", ".....kkkkkk.....", "...kkwwwwwwkk...", "..kwwwwwwwwwwk..",
            "..kwwwwwwwwwwk..", "." + eyes + ".", "." + eyes + ".", ".kwwwwwwwwwwwwk.",
            cheek, mouth, ".kwwwwwwwwwwwwk.", ".kwwwwwwwwwwwwk.", "..kwwwwwwwwwwk..",
            "...kkkwwwwkkk...", "..kwwk.kk.kwwk..", "...kk......kk..."]


def _pip_frame(rows):
    return "".join(rows).replace("k", "0").replace("w", "1")


_PIP_SAD = _pip_rows(mouth=".kwwwkwwwwkwwwk.", cheek=".kwwwwkkkkwwwwk.")
_PIP_WAVE = _pip_rows()
_PIP_WAVE[6:9] = [".kwwwkwwwwkwwwkk", ".kwwwwwwwwwwwkwk", ".kwwwkwwwwkwwwk."]
PIP = {"key": "pip", "title": "Pip", "size": 16, "speed": 6,
       "palette": ["#1b1530", "#ff8fc7"],
       "frames": [_pip_frame(_pip_rows()), _pip_frame(_pip_rows(mouth=".kwwwwkkkkwwwwk.", eyes="kwwwwwwwwwwwwk")),
                  _pip_frame(_PIP_SAD), _pip_frame(_PIP_WAVE)],
       "names": ["", "happy", "sad", "wave"]}


# ---- The stage ----------------------------------------------------------------

PROGRAM_BUDGET = 60_000    # interpreter operations for one whole run
MAX_CODE = 4000
MAX_STEPS = 400            # things that happen between one click and the next
MAX_EVENTS = 200           # clicks and keys in one show before it asks to start again
MAX_SAY = 60
MAX_TEXT = 200
MAX_LIST = 100
SPOTS = 11                 # the stage is 11 spots wide: 0 on the left to 10 on the right
START = 2

SCENES = ("stage", "wedding", "park", "beach", "night", "snowy", "candy", "space", "castle")
SOUNDS = ("ding", "boing", "pop", "tada", "meow", "drum", "whoosh", "yay")
FRIENDS = ("cat", "bunny", "kid", "bean")
PROPS = ("star", "gem", "cake", "ball")
EVENTS = ("click", "feed", "play", "sleep", "key")
KEYS = ("left", "right", "up", "down", "space")
FEELINGS = ("happy", "sad", "surprised", "angry", "sleepy", "silly", "cool", "calm")
LOOKS = ("left", "right", "up", "down", "front")
EVERYONE = ("dance", "wave", "cheer", "jump")
MAX_CREW = 3

# Each command: what it needs, in words a child can copy. None in `numbers`
# means the command takes no number.
USAGE = {
    "say": 'say("Hello")', "right": "right(3)", "left": "left(3)", "jump": "jump()",
    "spin": "spin()", "shake": "shake()", "grow": "grow()", "shrink": "shrink()",
    "hide": "hide()", "appear": "appear()", "pose": 'pose("happy")', "play": "play()",
    "wait": "wait(2)", "hearts": "hearts()", "stars": "stars()", "confetti": "confetti()",
    "rain": "rain()", "snow": "snow()", "sound": 'sound("ding")', "scene": 'scene("park")',
    "friend": 'friend("cat")', "friend_say": 'friend_say("Hi!")', "friend_jump": "friend_jump()",
    "bye": "bye()", "eat": "eat()", "nap": "nap()", "put": 'put("star", 7)',
    "take": 'take("star")', "point": "point()", "wave": "wave()", "dance": "dance()",
    "cheer": "cheer()", "look": 'look("left")', "feel": 'feel("happy")', "everyone": 'everyone("dance")',
}
COMMANDS = tuple(USAGE)
SENSORS = {"x": "x()", "clicks": "clicks()", "hungry": "hungry()", "sleepy": "sleepy()",
           "touching": 'touching("star")', "score": "score()", "weather": "weather()"}
USAGE.update(SENSORS)
EVERYTHING = COMMANDS + tuple(SENSORS)
HELPERS = ("len", "str", "int", "choice", "randint", "abs", "max", "min")
NO_ARGS = {"jump", "spin", "shake", "grow", "shrink", "hide", "appear", "play", "hearts",
           "stars", "confetti", "rain", "snow", "eat", "nap", "point",
           "wave", "dance", "cheer"}


def word_list(words):
    return ", ".join(f'"{w}"' for w in words)


class Show:
    """What happens on stage. Every command is a step the browser plays back."""

    def __init__(self, pal, seed):
        self.pal = pal
        self.rng = random.Random(seed)
        self.steps = []
        self.mark = 0                # where the steps for this click start
        self.line = None
        self.x = START
        self.visible = True
        self.size = 1
        self.scene = "stage"
        self.crew = []               # friends on stage, newest last
        self.props = {}              # spot -> what's there
        self.points = 0
        self.click_count = 0
        self.since_food = 3          # a new pet is hungry
        self.since_nap = 0
        self.forecast = None
        self.posed = set()           # faces and moves shown with pose(), not frames
        self.log = []                # (command, arguments) in order, for judging
        self.fired = []              # where in the log each click starts

    def step(self, do, **arg):
        if len(self.steps) - self.mark >= MAX_STEPS:
            raise BotError(f"That's a very long show! It stops at {MAX_STEPS} moves. "
                           f"Is a loop going round too many times?")
        if self.line:
            arg["line"] = self.line
        self.steps.append(dict(arg, do=do))

    def do(self, name, args):
        if name in NO_ARGS and args:
            extra = " To do it more than once, use a loop." if name in ("jump", "spin", "shake") else ""
            raise BotError(f"{name}() doesn't need anything in its brackets. "
                           f"Write  {name}()  with nothing in between.{extra}")
        self.log.append((name, tuple(a for a in args if isinstance(a, (str, int)))))
        method = getattr(self, "c_" + name, None)
        if name not in NO_ARGS:
            method(name, *args)
        elif method:
            method()
        else:
            self.step(name)

    @staticmethod
    def text(value):
        return show_value(value)[:MAX_SAY]

    def walk_to(self, spot):
        spot = max(0, min(SPOTS - 1, spot))
        self.step("walk", to=spot, by=abs(spot - self.x))
        self.x = spot

    def count_of(self, name, args, default=1):
        if len(args) > 1:
            raise BotError(f"{name}() takes just one number, like  {USAGE[name]}")
        n = args[0] if args else default
        if isinstance(n, bool) or not isinstance(n, int):
            raise BotError(f"{name}() needs a whole number, like  {USAGE[name]}  "
                           f"Numbers don't have quotes round them.")
        return n

    def c_say(self, name, *args):
        if len(args) != 1:
            raise BotError('say() needs one thing to say, like  say("Hello")')
        self.step("say", text=self.text(args[0]))

    def on_stage(self, word):
        who = str(word).strip().lower()
        if who not in self.crew:
            raise BotError(f"{word} isn't on stage. Bring them on first, like  friend(\"{word}\")")
        return who

    def named_friend(self, args, what):
        """The friend a command is for: the one named, or the newest."""
        if not self.crew:
            raise BotError('There\'s no friend on stage yet. Bring one on first, like  friend("cat")')
        return self.on_stage(args[0]) if args else self.crew[-1]

    def c_friend_say(self, name, *args):
        if len(args) not in (1, 2):
            raise BotError('friend_say() needs one thing to say, like  friend_say("Hi!")  or  friend_say("cat", "Hi!")')
        who = self.named_friend(args[:-1], "say")
        self.step("friend_say", text=self.text(args[-1]), who=who)

    def c_friend_jump(self, name, *args):
        if len(args) > 1:
            raise BotError('friend_jump() can take one name, like  friend_jump("cat")')
        self.step("friend_jump", who=self.named_friend(args, "jump"))

    def c_everyone(self, name, *args):
        if len(args) != 1 or args[0] not in EVERYONE:
            raise BotError(f'Pick a move for everyone, like  everyone("dance"). The moves are: {word_list(EVERYONE)}.')
        self.step("everyone", move=args[0])

    def c_right(self, name, *args):
        self.walk_to(self.x + self.count_of(name, args))

    def c_left(self, name, *args):
        self.walk_to(self.x - self.count_of(name, args))

    def c_wait(self, name, *args):
        n = self.count_of(name, args)
        if not 1 <= n <= 5:
            raise BotError("wait() takes a number from 1 to 5, like  wait(2)")
        self.step("wait", beats=n)

    def c_grow(self):
        self.size = min(3, self.size + 1)
        self.step("size", to=self.size)

    def c_shrink(self):
        self.size = max(1, self.size - 1)
        self.step("size", to=self.size)

    def c_hide(self):
        self.visible = False
        self.step("hide")

    def c_appear(self):
        self.visible = True
        self.step("appear")

    def c_pose(self, name, *args):
        if len(args) != 1:
            raise BotError('pose() needs the name of a frame, like  pose("happy")')
        which = args[0]
        names, count = self.pal.get("names") or [], len(self.pal["frames"])
        if isinstance(which, bool) or not isinstance(which, (str, int)):
            raise BotError('pose() needs the name of a frame, like  pose("happy")')
        if isinstance(which, int):
            if not 1 <= which <= count:
                raise BotError(f"Your pal has {count} frame{'' if count == 1 else 's'}, so "
                               f"pose({which}) can't work. Try a number from 1 to {count}.")
            frame = which - 1
        elif which in names:
            frame = names.index(which)
        elif which in FEELINGS:              # no frame drawn? The rig can make that face.
            self.step("feel", mood=which)
            self.posed.add(which)
            return
        elif which in ("wave", "hello", "dance", "jump"):
            self.step("wave" if which == "hello" else which)
            self.posed.add(which)
            return
        else:
            have = [n for n in names if n]
            also = f" Your pal's frames are called: {word_list(have)}." if have else ""
            raise BotError(f'Your pal has no "{which}" frame yet.{also} To make one, go to '
                           f"🎨 Draw, press + Copy frame, change it, then press ⋯ and name it {which}.")
        self.step("pose", frame=frame)

    def c_play(self):
        self.step("play")

    def c_look(self, name, *args):
        if len(args) != 1 or args[0] not in LOOKS:
            raise BotError(f'Pick a way to look, like  look("left"). The ways are: {word_list(LOOKS)}.')
        self.step("look", way=args[0])

    def c_feel(self, name, *args):
        if len(args) != 1 or args[0] not in FEELINGS:
            raise BotError(f'Pick a feeling, like  feel("happy"). The feelings are: {word_list(FEELINGS)}.')
        self.step("feel", mood=args[0])

    def c_sound(self, name, *args):
        if len(args) != 1 or args[0] not in SOUNDS:
            raise BotError(f'Pick a sound, like  sound("ding"). The sounds are: {word_list(SOUNDS)}.')
        self.step("sound", name=args[0])

    def c_scene(self, name, *args):
        if len(args) != 1 or args[0] not in SCENES:
            raise BotError(f'Pick a place, like  scene("park"). The places are: {word_list(SCENES)}.')
        self.scene = args[0]
        self.step("scene", name=args[0])

    def bring(self, who, **extra):
        if who in self.crew:
            return
        if len(self.crew) >= MAX_CREW:
            raise BotError(f"There's only room for {MAX_CREW} friends on stage. Use  bye()  to send one off first.")
        self.crew.append(who)
        self.step("friend", kind=who, **extra)

    def c_friend(self, name, *args):
        who = args[0].strip().lower() if len(args) == 1 and isinstance(args[0], str) else ""
        if who in FRIENDS:
            self.bring(who)
        else:
            raise BotError(f'Pick a friend, like  friend("cat"). The friends are: {word_list(FRIENDS)}.')

    def c_bye(self, name, *args):
        if len(args) > 1:
            raise BotError('bye() can take one name, like  bye("cat")')
        if not self.crew:
            return
        who = self.on_stage(args[0]) if args else self.crew[-1]
        self.crew.remove(who)
        self.step("bye", who=who)

    def c_eat(self):
        self.since_food = 0
        self.step("eat")

    def c_nap(self):
        self.since_nap = 0
        self.step("nap")

    def prop_word(self, name, args):
        if not args or args[0] not in PROPS:
            raise BotError(f'Pick a thing, like  {USAGE[name]}. The things are: {word_list(PROPS)}.')
        return args[0]

    def c_put(self, name, *args):
        prop = self.prop_word(name, args)
        if len(args) != 2 or isinstance(args[1], bool) or not isinstance(args[1], int):
            raise BotError('put() needs a thing and a spot, like  put("star", 7)')
        if not 0 <= args[1] < SPOTS:
            raise BotError(f"The stage has spots 0 to {SPOTS - 1}, so spot {args[1]} is off the edge.")
        self.props[args[1]] = prop
        self.step("put", prop=prop, at=args[1])

    def c_take(self, name, *args):
        prop = self.prop_word(name, args)
        if self.props.get(self.x) != prop:
            raise BotError(f'There\'s no {prop} where your pal is standing. Check first with  '
                           f'if touching("{prop}"):')
        del self.props[self.x]
        self.step("take", at=self.x)

    def c_point(self):
        self.points += 1
        self.step("point", score=self.points)


def show_value(value):
    if value is True:
        return "True"
    if value is False:
        return "False"
    if value is None:
        return "nothing"
    if isinstance(value, list):
        return "[" + ", ".join(show_value(v) for v in value[:20]) + "]"
    return str(value)


def plain_syntax(code, e):
    """Why a line can't be read and what to press, for a child who has never
    met a syntax error."""
    lines = code.split("\n")
    n = e.lineno or 1
    line = lines[n - 1].strip() if n <= len(lines) else ""
    bare = re.fullmatch(r"([A-Za-z_]+)\s+(\w+)", line)
    known = list(COMMANDS) + list(SENSORS)
    near = bare and difflib.get_close_matches(bare[1].lower(), known, 1, 0.7)
    if near:
        return f"Commands have brackets. Write  {USAGE.get(near[0], near[0] + '()')}"
    said = re.fullmatch(r"say\s+(.+)", line)
    if said:
        return 'Words go inside brackets and quotes. Write  say("Hello")'
    if re.match(r"say\([^\"']*\"?[^\"']*$", line) and line.count('"') == 1:
        return 'Words need a  "  at both ends. Add the missing one. Hold Shift and press the  "  key.'
    if re.match(r"(repeat|loop)\b", line) or (re.match(r"for\b", line) and " in " not in line):
        return "To repeat lines, write it like this:  for i in range(3):"
    hint = re.sub(r"^Syntax error on line \S+: ", "", syntax_message(e, "def my_move():")).rstrip(".")
    plainer = {
        "a bracket  (  is never closed with  )":
            "This line opens a bracket  (  but never closes it. Add a  )  at the end: hold Shift and press 0",
        "a line that starts with def, if, elif, else, while or for has to end with a  :":
            "Add a  :  at the very end of this line (hold Shift and press the ; key). It "
            "means more lines are coming under this one",
        "the lines inside it need pushing in (indenting) with spaces":
            "The line above ends with a  :  so this line has to be pushed in. Click at the "
            "start of this line and press Tab",
        "this line is pushed in further than the line above it":
            "This line starts too far to the right. Click at the start of it and press "
            "Backspace until it lines up with the line above",
        "this line doesn't line up with the lines above it — check its spaces":
            "This line doesn't line up with the lines above it. Click at the start of it "
            "and use Tab or Backspace to move it",
        'some text is missing its closing quote  "':
            'Words need a  "  at both ends. Add the missing  "  at the end of the words',
        "there's a  )  with no  (  before it":
            "This line has a  )  with no  (  to match it. Add the  (  or delete the  )",
        "put each command on its own line":
            "Only one command fits on a line. Press Enter to start a new line for the next one",
    }
    hint = plainer.get(hint, hint)
    if "rover" in hint or "compass" in hint or hint.startswith("Python couldn't read it"):
        hint = (f"Your pal doesn't understand  {line}  . Commands look like  jump()  or  "
                f"right(3) : a word with brackets straight after it. Check the spelling")
    return hint + ("" if hint[-1] in ':)"' else ".")


class Director(Brain):
    """One student's program running one show, from top to bottom. Their defs
    called on_click and so on run later, when a click comes in."""

    def __init__(self, code, show, commands):
        self.show = show
        self.commands = set(commands)
        self.sensors = {n: None for n in COMMANDS + tuple(SENSORS) + HELPERS}
        self.prints = []
        self.globals = _Frame(module=True)
        self.funcs = {}
        self.ops = 0
        self.budget = PROGRAM_BUDGET
        self.steering = False
        self.depth = 0
        self.own_calls = Counter()
        if len(code) > MAX_CODE:
            raise BotError(f"Your program is too long: {MAX_CODE} letters is the most "
                           f"(about 100 lines). Delete some lines you don't need.")
        code = code.replace(" ", " ").replace("​", "").replace("﻿", "")
        try:
            self.tree = ast.parse(code)
        except SyntaxError as e:
            raise_at(e.lineno or 1, plain_syntax(code, e))
        self.named = {n.id for n in ast.walk(self.tree)
                      if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Store)}
        self.named |= {n.name for n in ast.walk(self.tree) if isinstance(n, ast.FunctionDef)}
        self.named |= {a.arg for n in ast.walk(self.tree) if isinstance(n, ast.FunctionDef)
                       for a in n.args.args}
        for fn in ast.walk(self.tree):
            if isinstance(fn, ast.FunctionDef) and fn.name.startswith("on_") \
                    and fn.name[3:] not in EVENTS:
                near = difflib.get_close_matches(fn.name[3:], EVENTS, 1, 0.5)
                tip = f" Did you mean  def on_{near[0]}():  ?" if near else ""
                raise_at(fn.lineno, f"{fn.name} isn't an event your pal can hear.{tip}")

    def run(self):
        self.run_block(self.tree.body, self.globals)

    def tick(self):
        self.ops += 1
        if self.ops > self.budget:
            raise _TooLong("Your program went round and round and never finished")

    def fire(self, event, key=None):
        """A click or a key arrives. It runs that def, if there is one."""
        show = self.show
        show.mark = len(show.steps)
        show.fired.append(len(show.log))
        show.step("event", name=event, key=key)
        if event == "click":
            show.click_count += 1
        show.since_food += 1
        show.since_nap += 1
        fn = self.funcs.get("on_" + event)
        if fn is None:
            return
        wants = len(fn.args.args)
        if event == "key":
            if wants != 1:
                raise_at(fn.lineno, "on_key needs a name in its brackets for the key, like  def on_key(key):")
            self.call_user(fn, [key])
        else:
            if wants:
                raise_at(fn.lineno, f"on_{event} doesn't need anything in its brackets. "
                                    f"Write  def on_{event}():")
            self.call_user(fn, [])

    # ---- words ---------------------------------------------------------------

    def lookup(self, name, frame):
        if name in ("True", "False", "None"):
            return {"True": True, "False": False, "None": None}[name]
        try:
            return super().lookup(name, frame)
        except BotError as err:
            text = str(err)
            if "command" in text or "global" in text or "before giving" in text:
                raise
            if name in self.named and "Did you mean" in text:
                raise
            if name not in self.named:
                raise BotError(f'Words need quotes round them, like  say("{name}")  '
                               f'If {name} is meant to be a variable, set it first, like  {name} = 3')
            raise BotError(f"I don't know '{name}' yet. Set it on a line above this one, "
                           f"like  {name} = 3")

    def assign(self, name, value, frame):
        if name in self.sensors:
            raise BotError(f"{name} is already a command, so pick another name for your variable.")
        super().assign(name, value, frame)

    def math(self, op, a, b):
        if isinstance(op, ast.Add) and isinstance(a, str) and isinstance(b, str):
            if len(a) + len(b) > MAX_TEXT:
                raise BotError("That text got too long.")
            return a + b
        if isinstance(op, ast.Add) and isinstance(a, list) and isinstance(b, list):
            return self.fits(a + b)
        if isinstance(op, ast.Add) and (isinstance(a, str) or isinstance(b, str)):
            raise BotError('Words and numbers can\'t be joined with +. Put an f in front of '
                           'the quotes and the name in curly brackets, like  say(f"I am {age}")')
        if isinstance(op, ast.Mult) and isinstance(a, (str, list)) != isinstance(b, (str, list)):
            seq, n = (a, b) if isinstance(a, (str, list)) else (b, a)
            n = self.number(n, "Repeating with *")
            if len(seq) * max(n, 0) > (MAX_TEXT if isinstance(seq, str) else MAX_LIST):
                raise BotError("That got too long.")
            return seq * n
        if isinstance(a, (str, list)) or isinstance(b, (str, list)):
            raise BotError("You can only do sums with numbers, not with words or lists.")
        return super().math(op, a, b)

    def compare(self, op, a, b):
        if isinstance(op, (ast.In, ast.NotIn)):
            if not isinstance(b, (str, list)) or (isinstance(b, str) and not isinstance(a, str)):
                raise BotError('in needs a list on its right, like  if mood in ["happy", "silly"]:')
            found = a in b
            return found if isinstance(op, ast.In) else not found
        return super().compare(op, a, b)

    def fits(self, items):
        if len(items) > MAX_LIST:
            raise BotError(f"That list got too long: {MAX_LIST} things is the most.")
        return items

    def eval(self, node, frame):
        if isinstance(node, ast.List):
            self.tick()
            return self.fits([self.eval(e, frame) for e in node.elts])
        if isinstance(node, ast.Subscript):
            self.tick()
            return self.item(self.eval(node.value, frame), node.slice, frame)
        if isinstance(node, ast.JoinedStr):
            self.tick()
            parts = []
            for v in node.values:
                if isinstance(v, ast.Constant):
                    parts.append(str(v.value))
                elif isinstance(v, ast.FormattedValue) and v.format_spec is None:
                    parts.append(show_value(self.eval(v.value, frame)))
                    self.ops += len(parts[-1])
                else:
                    raise BotError('Keep f-strings simple, like  f"Hi {name}"')
            text = "".join(parts)
            if len(text) > MAX_TEXT:
                raise BotError("That text got too long.")
            return text
        if isinstance(node, (ast.Tuple, ast.Set, ast.Dict)):
            raise BotError('Use a list in square brackets, like  ["red", "blue"]')
        if isinstance(node, (ast.ListComp, ast.DictComp, ast.SetComp, ast.GeneratorExp, ast.Lambda)):
            raise BotError("That shortcut isn't part of Pixel Pals. Use a for loop instead.")
        if isinstance(node, ast.Attribute):
            raise BotError("Dots aren't part of Pixel Pals, except  name.upper()  and  name.lower()")
        if isinstance(node, ast.Constant) and isinstance(node.value, float):
            raise BotError("Use whole numbers here, like 3 (not 3.5).")
        if type(node).__name__ in ("TemplateStr", "NamedExpr", "Await", "Yield", "YieldFrom", "Starred"):
            raise BotError("That isn't part of Pixel Pals.")
        return super().eval(node, frame)

    def item(self, target, index, frame):
        if isinstance(index, ast.Slice) or not isinstance(target, (list, str)):
            raise BotError('[ ] picks one thing from a list, like  names[0]  (the first one is 0)')
        key = self.eval(index, frame)
        if isinstance(key, bool) or not isinstance(key, int):
            raise BotError("Use a whole number in the [ ], like  names[0]  (the first one is 0)")
        if -len(target) <= key < len(target):
            return target[key]
        if not target:
            raise BotError(f"[{key}] can't work because it's empty.")
        raise BotError(f"There's nothing at position {key}. It has {len(target)} "
                       f"thing{'s' if len(target) != 1 else ''}, so the positions go from "
                       f"0 to {len(target) - 1}.")

    def call(self, node, frame):
        if node.keywords:
            raise BotError("Commands don't take name=value here. Just put the value in the brackets.")
        if any(isinstance(a, ast.Starred) for a in node.args):
            raise BotError("* in a command isn't part of Pixel Pals.")
        if isinstance(node.func, ast.Attribute):
            return self.method(node, frame)
        if not isinstance(node.func, ast.Name):
            raise BotError('I can only run plain commands, like  jump()')
        name = node.func.id
        if name in self.funcs:
            self.own_calls[name] += 1
            return self.call_user(self.funcs[name], [self.eval(a, frame) for a in node.args])
        args = [self.eval(a, frame) for a in node.args]
        if name in COMMANDS or name in SENSORS:
            if name not in self.commands:
                raise BotError(f"{name}() isn't open yet. You'll get it in a later chapter.")
            self.show.line = node.lineno
            if name in COMMANDS:
                self.show.do(name, args)
                return None
            return self.sensor(name, args)
        return self.helper(name, args, node, frame)

    def sensor(self, name, args):
        show = self.show
        if name == "touching":
            if len(args) != 1 or args[0] not in PROPS:
                raise BotError(f'touching() needs a thing, like  touching("star"). '
                               f"The things are: {word_list(PROPS)}.")
            show.log.append(("touching", (args[0],)))
            return show.props.get(show.x) == args[0]
        if args:
            raise BotError(f"{name}() doesn't need anything in its brackets.")
        show.log.append((name, ()))
        if name == "x":
            return show.x
        if name == "clicks":
            return show.click_count
        if name == "score":
            return show.points
        if name == "hungry":
            return show.since_food >= 3
        if name == "sleepy":
            return show.since_nap >= 4
        if not show.forecast:           # weather()
            show.forecast = show.rng.choice(["sun", "rain", "snow"])
            show.step("weather", kind=show.forecast)
        return show.forecast

    def helper(self, name, args, node, frame):
        if name == "len":
            if len(args) != 1 or not isinstance(args[0], (list, str)):
                raise BotError('len() counts a list or some words, like  len(names)')
            return len(args[0])
        if name == "str":
            if len(args) != 1:
                raise BotError("str() takes one thing, like  str(8)")
            return show_value(args[0])
        if name == "int":
            if len(args) != 1:
                raise BotError('int() takes one thing, like  int("8")')
            if isinstance(args[0], str) and re.fullmatch(r"\s*-?\d{1,9}\s*", args[0]):
                return int(args[0])
            return self.number(args[0], "int()")
        if name == "choice":
            if len(args) != 1 or not isinstance(args[0], (list, str)) or not args[0]:
                raise BotError('choice() picks from a list, like  choice(["happy", "silly"])')
            return self.show.rng.choice(args[0])
        if name == "randint":
            if len(args) != 2:
                raise BotError("randint() takes two numbers, like  randint(1, 6)")
            lo, hi = (self.number(a, "randint()") for a in args)
            if lo > hi:
                raise BotError("randint(a, b) needs a to be no bigger than b.")
            return self.show.rng.randint(lo, hi)
        if name in ("max", "min", "abs"):
            return super().call(node, frame)
        if name == "print":
            raise BotError('Your pal talks with say(), not print(). Try  say("Hello")')
        if name == "range":
            raise BotError("range() goes in a for loop, like  for i in range(4):")
        if name in ("walk", "move", "go"):
            raise BotError(f"There's no {name}(). Your pal walks with  right(3)  or  left(3)")
        known = [c for c in COMMANDS + tuple(SENSORS) if c in self.commands] + list(self.funcs) + list(HELPERS)
        near = difflib.get_close_matches(name.lower(), known, 1, 0.65)
        if near:
            raise BotError(f"I don't know '{name}'. Did you mean  {USAGE.get(near[0], near[0] + '()')}  ?")
        raise BotError(f"I don't know the command '{name}'. Check the spelling, or make it "
                       f"yourself with  def {name}():")

    def method(self, node, frame):
        name = node.func.attr
        target = self.eval(node.func.value, frame)
        if isinstance(target, str) and name in ("upper", "lower") and not node.args:
            self.tick()
            return getattr(target, name)()
        if isinstance(target, list) and name == "append" and len(node.args) == 1:
            target.append(self.eval(node.args[0], frame))
            self.fits(target)
            return None
        raise BotError(f".{name}() isn't part of Pixel Pals. You can use .upper(), .lower() "
                       f"and, on a list, .append()")

    def run_statement(self, node, frame):
        if isinstance(node, ast.For):
            self.tick()
            if not isinstance(node.target, ast.Name):
                raise BotError("A for loop needs one simple name, like  for name in names:")
            if node.orelse:
                raise BotError("for ... else isn't part of Pixel Pals.")
            it = node.iter
            if isinstance(it, ast.Call) and isinstance(it.func, ast.Name) and it.func.id == "range":
                nums = [self.number(self.eval(a, frame), "range()") for a in it.args]
                if it.keywords or not 1 <= len(nums) <= 3 or (len(nums) == 3 and nums[2] == 0):
                    raise BotError("range() takes 1 to 3 numbers, and the step can't be 0.")
                values = range(*nums)
            else:
                seq = self.eval(it, frame)
                if isinstance(seq, int) and not isinstance(seq, bool):
                    raise BotError(f"To repeat {seq} times write  for i in range({seq}):")
                if not isinstance(seq, (list, str)):
                    raise BotError("A for loop goes through a list or range(), like  for i in range(4):")
                values = list(seq)
            for value in values:
                self.tick()
                self.assign(node.target.id, value, frame)
                if not self.run_loop_body(node.body, frame):
                    break
            return
        if isinstance(node, ast.While) and node.orelse:
            raise BotError("while ... else isn't part of Pixel Pals.")
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            raise BotError("You don't need import here. choice() and randint() are already ready to use.")
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Subscript) for t in node.targets):
            raise BotError("Changing one thing in a list isn't part of Pixel Pals. Make a new variable instead.")
        if isinstance(node, ast.Assign) and any(isinstance(t, (ast.Tuple, ast.List)) for t in node.targets):
            raise BotError("Give each variable its own line, like  a = 1")
        if isinstance(node, ast.FunctionDef) and node.name in self.sensors:
            raise BotError(f"{node.name}() is already a command, so give your move another "
                           f"name, like  def my_{node.name}():")
        if isinstance(node, ast.Expr) and not isinstance(node.value, ast.Call) and not (
                isinstance(node.value, ast.Constant) and isinstance(node.value.value, str)):
            v = node.value
            if isinstance(v, ast.Name) and (v.id in self.sensors or v.id in self.funcs):
                raise BotError(f"To use {v.id}, add brackets:  {v.id}()")
            raise BotError('That line doesn\'t do anything on its own. Words need  say("...")  '
                           'and commands need brackets, like  jump()')
        if isinstance(node, (ast.Try, ast.With, ast.ClassDef, ast.Delete, ast.Raise,
                             ast.Assert, ast.Nonlocal, ast.AsyncFunctionDef)) or \
                type(node).__name__ in ("Match", "TypeAlias", "TryStar"):
            raise BotError("That kind of line isn't part of Pixel Pals.")
        super().run_statement(node, frame)


def raise_at(line, text):
    error = BotError(text)
    error.line = line
    raise error


# ---- Running a show ---------------------------------------------------------------

class Report:
    """What happened in one run, in the terms a mission's stars ask about."""

    def __init__(self, show, tree, director, code=""):
        self.log = show.log
        self.counts = Counter(name for name, _ in show.log)
        self.said = [str(s["text"]) for s in show.steps if s["do"] == "say"]
        self.walks = [s["by"] for s in show.steps if s["do"] == "walk"]
        self.poses = {s["frame"] for s in show.steps if s["do"] == "pose"} | show.posed
        self.x = show.x
        self.score = show.points
        self.forecast = show.forecast
        self.friend_said = [str(s["text"]) for s in show.steps if s["do"] == "friend_say"]
        self.reacts = [show.log[a:b] for a, b in zip(show.fired, show.fired[1:] + [len(show.log)])]
        self.others = [self]
        self.own_calls = director.own_calls if director else Counter()
        self.values = dict(director.globals.vars) if director else {}
        nodes = list(ast.walk(tree)) if tree else []
        count = lambda kind: sum(isinstance(n, kind) for n in nodes)
        self.fors, self.whiles, self.ifs = count(ast.For), count(ast.While), count(ast.If)
        self.elses = sum(1 for n in nodes if isinstance(n, ast.If) and n.orelse)
        defs = [n for n in nodes if isinstance(n, ast.FunctionDef)]
        self.defs = [d.name for d in defs if not d.name.startswith("on_")]
        self.events = sorted(d.name[3:] for d in defs if d.name.startswith("on_"))
        self.params = sum(len(d.args.args) for d in defs if not d.name.startswith("on_"))
        self.fstrings = count(ast.JoinedStr)
        self.lists = count(ast.List)
        self.changes = count(ast.AugAssign) + sum(
            1 for n in nodes if isinstance(n, ast.Assign) and any(
                isinstance(m, ast.Name) and m.id in [getattr(t, "id", "") for t in n.targets]
                for m in ast.walk(n.value)))
        self.range_name = any(
            isinstance(n, ast.For) and isinstance(n.iter, ast.Call)
            and any(isinstance(a, ast.Name) for a in n.iter.args) for n in nodes)
        self.upper = sum(1 for n in nodes if isinstance(n, ast.Attribute) and n.attr in ("upper", "lower"))
        self.lines = len(tree.body) if tree else 0
        self.code_lines = sum(1 for line in code.split("\n")
                              if line.strip() and not line.strip().startswith("#"))

    def n(self, name):
        return self.counts[name]

    def said_var(self):
        words = [v for v in self.values.values() if isinstance(v, str) and v]
        return sum(1 for s in self.said for w in words if w in s or w.upper() in s or w.lower() in s)

    def did(self, event_number, name):
        return event_number < len(self.reacts) and \
            any(n == name for n, _ in self.reacts[event_number])

    def first(self, *names):
        """True if these commands happened, in this order."""
        at = 0
        for name, _ in self.log:
            if at < len(names) and name == names[at]:
                at += 1
        return at == len(names)


def perform(code, pal=PIP, events=(), seed=0, commands=EVERYTHING, setup=None):
    """Run a program. `events` are clicks, like "click", "feed" or "key:left"."""
    show = Show(pal, seed)
    error, line, director = None, None, None
    if setup:
        setup(show)
    try:
        director = Director(code, show, commands)
        director.run()
        for event in list(events)[:MAX_EVENTS]:
            kind, _, key = str(event).partition(":")
            if kind not in EVENTS or (kind == "key" and key not in KEYS):
                continue
            director.fire(kind, key or None)
    except _TooLong as e:
        error, line = str(e), e.line
    except BotError as e:
        error, line = str(e), e.line
    except RecursionError:
        error = "Your program called itself too many times."
    return {"steps": show.steps, "after": show.steps[show.mark:], "error": error, "line": line,
            "events": sorted(f[3:] for f in (director.funcs if director else {}) if f[3:] in EVENTS
                             and f.startswith("on_")),
            "report": Report(show, getattr(director, "tree", None), director, code)}


def public(result):
    """What the browser gets of a run."""
    return {k: result[k] for k in ("steps", "error", "line", "events")}


# ---- Missions ------------------------------------------------------------------

def _mark(spot):
    def setup(show):
        show.step("mark", at=spot)
    return setup


# What counts as one action in a My Move.
MOVE_ACTIONS = ("say", "jump", "right", "left", "wave", "dance", "cheer", "spin", "hearts", "stars", "confetti", "feel")
MOVE_BIG = 8               # this many actions earns a big finish


def _actions(r):
    return sum(r.n(name) for name in MOVE_ACTIONS)


CHAPTERS = [
    {"key": "a", "name": "Opening Night", "icon": "🎭"},
    {"key": "h", "name": "Come Alive", "icon": "✨"},
    {"key": "b", "name": "Again! Again!", "icon": "🔁"},
    {"key": "m", "name": "My Move", "icon": "🌟"},
    {"key": "t", "name": "Encore!", "icon": "🎪"},
    {"key": "l", "name": "Count on Me", "icon": "🔢"},
    {"key": "v", "name": "Name Tags", "icon": "🏷️"},
    {"key": "w", "name": "Smart Pal", "icon": "🧠"},
]

# `adds` opens commands, and `python` opens the shapes of Python on the chips.
# A goal is (what it asks, check, and what Pip says when it's missing).
# The last hint is always a program that does the job.
# `coach` is that program again, one line at a time with what each line does, and
# the page walks a student through typing it. `build` missions start with buttons instead.
LEVELS = [
    {"key": "a1", "chapter": 0, "name": "Say hello", "adds": ["say"], "python": [],
     "pip": "Hi, I'm Pip! The crowd is here, and your pal goes first. "
            "Make your pal say hello!",
     "job": "Make your pal say two things.",
     "coach": [
               ('say("Hello")', 'This line makes your pal talk. The words go inside the " marks.'),
               ('say("I am so happy to be here")', 'Now your pal says something longer. This line gets you all 3 stars!'),
     ],
     "goals": [("Your pal says something", lambda r: r.n("say") >= 1, "Your pal didn't say anything yet. Type  say(\"Hello\")"),
               ("Your pal says two things", lambda r: r.n("say") >= 2, None),
               ("One of them has 3 words or more", lambda r: any(len(s.split()) >= 3 for s in r.said), None)],
     "hints": ['Commands have brackets. Words go inside the brackets, with  "  at both ends.',
               'say("Hello")\nsay("I am so happy to be here")'],
     "reference": 'say("Hello")\nsay("I am so happy to be here")'},

    {"key": "a2", "chapter": 0, "name": "Jump for joy", "adds": ["jump"], "python": [],
     "pip": "The crowd loves a jump! Each line runs one after the other, from top to bottom.",
     "job": "Make your pal jump, say something, then jump again.",
     "coach": [
               ('jump()', 'This line makes your pal jump. Every command ends with ( ) marks.'),
               ('say("Wheee!")', 'Now your pal talks. Lines run from top to bottom, one at a time.'),
               ('jump()', 'Jump one more time!'),
     ],
     "goals": [("Your pal jumps two times", lambda r: r.n("jump") >= 2, lambda r: f"I counted {r.n('jump')} jump{'' if r.n('jump') == 1 else 's'}. I need 2."),
               ("Your pal says something too", lambda r: r.n("say") >= 1, None),
               ("Your pal talks between the two jumps", lambda r: r.first("jump", "say", "jump"), None)],
     "hints": ["Put  jump()  on one line, then  jump()  again on the next line.",
               'jump()\nsay("Wheee!")\njump()'],
     "reference": 'jump()\nsay("Wheee!")\njump()'},

    {"key": "a3", "chapter": 0, "name": "Find the spotlight", "adds": ["right", "left"], "python": [],
     "setup": _mark(7),
     "pip": "See the spotlight? Your pal is on spot 2 and the light is on spot 7. The number says how far to walk.",
     "job": "Walk to the spotlight, say something, then walk back.",
     "coach": [
               ('right(5)', 'Your pal is on spot 2. The light is on spot 7. That is 5 steps to the right.'),
               ('say("Here I am!")', 'Your pal talks when it gets to the light.'),
               ('left(5)', 'Now walk 5 steps left, back to where it started.'),
     ],
     "goals": [("Your pal goes to spot 7", lambda r: 7 in _visited(r), lambda r: f"Your pal stopped on spot {r.x}. The light is on spot 7. How many steps is that from spot 2?"),
               ("Your pal says something there", lambda r: r.first("right", "say"), None),
               ("Then your pal walks back to spot 2", lambda r: r.x == 2 and r.n("left") >= 1, None)],
     "hints": ["From 2 to 7 is 5 steps, so try  right(5)", 'right(5)\nsay("Here I am!")\nleft(5)'],
     "reference": 'right(5)\nsay("Here I am!")\nleft(5)'},

    {"key": "h1", "chapter": 1, "name": "Big wave", "adds": ["wave"], "python": [],
     "pip": "Your pal has real arms now! The computer found them when you drew it. If you drew no arms, it wiggles instead.",
     "job": "Say hello, then wave two times.",
     "coach": [
               ('say("Hello!")', 'First your pal says hello.'),
               ('wave()', 'This line makes your pal wave its arm.'),
               ('wave()', 'Wave one more time!'),
     ],
     "goals": [("Your pal waves", lambda r: r.n("wave") >= 1, "Type  wave()  on a line of its own."),
               ("Your pal says something first", lambda r: r.first("say", "wave"), "Put  say()  on the line above  wave()"),
               ("Your pal waves two times", lambda r: r.n("wave") >= 2, None)],
     "hints": ["Type  say(\"Hello!\")  and then  wave()  on the next line.", 'say("Hello!")\nwave()\nwave()'],
     "reference": 'say("Hello!")\nwave()\nwave()'},

    {"key": "h3", "chapter": 1, "name": "How do you feel?", "adds": ["feel", "wait"], "python": [],
     "pip": "Faces change too! feel() changes your pal's eyes and mouth. Watch them: it's your own drawing, moving.",
     "job": "Make your pal sad, then surprised, then happy.",
     "coach": [
               ('feel("sad")', "This line changes your pal's face to sad."),
               ('wait(1)', 'This line makes your pal wait, so we can see the face.'),
               ('feel("surprised")', 'Now change the face to surprised.'),
               ('wait(1)', 'Wait again, so we can see it.'),
               ('feel("happy")', 'Last, a happy face!'),
     ],
     "goals": [("Your pal feels sad", lambda r: ("feel", ("sad",)) in r.log, 'Type  feel("sad")'),
               ("Then your pal feels happy", lambda r: ("feel", ("happy",)) in r.log and r.log.index(("feel", ("happy",))) > (r.log.index(("feel", ("sad",))) if ("feel", ("sad",)) in r.log else 10**6), 'Put  feel("happy")  after  feel("sad")'),
               ("Three feelings or more", lambda r: len({a for c, a in r.log if c == "feel"}) >= 3, None)],
     "hints": ["The feelings are happy, sad, surprised, angry, sleepy, silly, cool and calm.",
               'feel("sad")\nwait(1)\nfeel("surprised")\nwait(1)\nfeel("happy")'],
     "reference": 'feel("sad")\nwait(1)\nfeel("surprised")\nwait(1)\nfeel("happy")'},

    {"key": "h4", "chapter": 1, "name": "Dance floor", "adds": ["dance", "cheer", "hearts"], "python": [],
     "pip": "Time to move! dance() uses every part your pal has: arms, legs, ears and tail. cheer() throws its arms up.",
     "job": "Dance, then cheer, then fill the stage with hearts.",
     "coach": [
               ('dance()', 'This line makes every part of your pal dance.'),
               ('cheer()', 'This line makes your pal throw its arms up.'),
               ('hearts()', 'This line fills the stage with hearts.'),
     ],
     "goals": [("Your pal dances", lambda r: r.n("dance") >= 1, "Type  dance()"),
               ("Then your pal cheers", lambda r: r.first("dance", "cheer"), "Add  cheer()  on the line after  dance()"),
               ("Hearts or stars at the end", lambda r: bool(r.log) and r.log[-1][0] in ("hearts", "stars"), None)],
     "hints": ["Type  dance()  then  cheer()  then  hearts()", "dance()\ncheer()\nhearts()"],
     "reference": "dance()\ncheer()\nhearts()"},

    {"key": "b1", "chapter": 2, "name": "Bounce!", "adds": [], "python": ["for"],
     "pip": "Five jumps would take five lines. A loop says it in two! The line under it is pushed in, and it repeats.",
     "job": "Make your pal jump 5 times with a loop.",
     "coach": [
               ('for i in range(5):', 'A loop repeats things. This line means: do this 5 times. It ends with a : mark.'),
               ('    jump()', 'This line is pushed in, so it is inside the loop. I pushed it in for you. Now type jump().'),
     ],
     "goals": [("Your pal jumps 5 times", lambda r: r.n("jump") >= 5, lambda r: f"I counted {r.n('jump')} jumps. I need 5."),
               ("You use a for loop", lambda r: r.fors >= 1, "Try  for i in range(5):  and push  jump()  in under it."),
               ("Your whole program is 2 lines", lambda r: r.fors >= 1 and r.code_lines <= 2, None)],
     "hints": ["The number in  range(5)  is how many times it repeats.", "Press Tab to push a line in.",
               "for i in range(5):\n    jump()"],
     "reference": "for i in range(5):\n    jump()"},

    {"key": "b2", "chapter": 2, "name": "Side step", "adds": ["confetti"], "python": ["for"],
     "pip": "A loop can repeat lots of lines. Everything pushed in goes round together. A line that isn't pushed in runs once, after the loop.",
     "job": "Step right and left 4 times with a loop, then throw confetti.",
     "coach": [
               ('for i in range(4):', 'This loop goes round 4 times.'),
               ('    right(1)', 'This line is pushed in, so it is inside the loop. Step right.'),
               ('    left(1)', 'This line is inside the loop too. Step left.'),
               ('confetti()', 'This line is NOT pushed in, so it runs once, after the loop. I moved it back for you.'),
     ],
     "goals": [("Right and left, 4 times over", lambda r: r.n("right") >= 4 and r.n("left") >= 4, lambda r: f"I saw {r.n('right')} right and {r.n('left')} left. I need 4 of each."),
               ("Confetti comes once, at the end", lambda r: r.n("confetti") == 1 and r.log[-1][0] == "confetti", "Confetti should run once. Don't push it in. Line it up with the word for."),
               ("You use a for loop", lambda r: r.fors >= 1, None)],
     "hints": ["Push in  right(1)  and  left(1)  under the for line.", "for i in range(4):\n    right(1)\n    left(1)\nconfetti()"],
     "reference": "for i in range(4):\n    right(1)\n    left(1)\nconfetti()"},

    {"key": "m1", "chapter": 3, "name": "My Move", "adds": ["spin", "stars"], "python": ["for"],
     "pip": "This one is all yours! Code your own routine. It becomes a big button in the Hang out, and when you press it, "
            "everyone sees your pal do it. A loop gives it a sparkle trail, and a long routine gets a big finish.",
     "job": "Make up your own move. Use 3 actions or more.",
     "coach": [
               ('spin()', 'Your pal starts with a spin.'),
               ('for i in range(3):', 'This loop goes round 3 times. A loop gives your move a sparkle trail!'),
               ('    jump()', 'This line is inside the loop. Jump!'),
               ('    hearts()', 'This line is inside the loop too. Hearts!'),
               ('dance()', 'This line is NOT pushed in, so it runs after the loop. I moved it back for you.'),
               ('cheer()', 'One last move. Now you have enough for a big finish!'),
     ],
     "build": True,
     "goals": [("Your move has 3 actions or more", lambda r: _actions(r) >= 3, lambda r: f"I counted {_actions(r)} action{'' if _actions(r) == 1 else 's'}. I need 3. Try  jump()  spin()  dance()"),
               ("It uses a for loop: sparkle trail!", lambda r: r.fors >= 1, None),
               (f"It has {MOVE_BIG} actions or more: big finish!", lambda r: _actions(r) >= MOVE_BIG, None)],
     "hints": ["Pick three things your pal can do, and put each on its own line.",
               "A loop repeats the lines pushed in under it. Try  for i in range(3):  and push  jump()  in under it.",
               "spin()\nfor i in range(3):\n    jump()\n    hearts()\ndance()\ncheer()"],
     "reference": "spin()\nfor i in range(3):\n    jump()\n    hearts()\ndance()\ncheer()"},
    # After My Move: more to code for students who have finished it. Easy first, then harder.
    {"key": "t1", "chapter": 4, "name": "Grow big", "adds": ["grow", "shrink", "shake"], "python": [],
     "pip": "Encore! The crowd wants more. Your pal can change size: grow() makes it bigger and shrink() makes it small again. shake() gives it the wobbles.",
     "job": "Grow big, shake, then shrink back and say something.",
     "coach": [
               ('grow()', 'This line makes your pal bigger.'),
               ('shake()', 'Now your pal shakes, like a jelly!'),
               ('shrink()', 'This line makes your pal small again.'),
               ('say("Ta-da!")', 'Last, your pal says Ta-da!'),
     ],
     "goals": [("Your pal grows", lambda r: r.n("grow") >= 1, "Type  grow()"),
               ("Then it shakes", lambda r: r.first("grow", "shake"), "Put  shake()  on the line after  grow()"),
               ("Then it shrinks back and says something", lambda r: r.first("grow", "shake", "shrink", "say"), None)],
     "hints": ["grow() makes your pal bigger, and shrink() makes it smaller.", 'grow()\nshake()\nshrink()\nsay("Ta-da!")'],
     "reference": 'grow()\nshake()\nshrink()\nsay("Ta-da!")'},

    {"key": "t2", "chapter": 4, "name": "Who's there?", "adds": ["look"], "python": [],
     "pip": 'Your pal can move its eyes! look("left") makes them look left. The ways are left, right, up, down and front.',
     "job": "Look left, then right, then look at us and say hello.",
     "coach": [
               ('look("left")', "This line makes your pal's eyes look left."),
               ('wait(1)', 'Wait, so we can see it.'),
               ('look("right")', 'Now the eyes look right.'),
               ('wait(1)', 'Wait again.'),
               ('look("front")', 'Now your pal looks right at us!'),
               ('say("Oh, hello!")', 'Last, your pal says hello.'),
     ],
     "goals": [("Your pal looks left", lambda r: ("look", ("left",)) in r.log, 'Type  look("left")'),
               ("Then it looks right", lambda r: _in_order(r, ("look", ("left",)), ("look", ("right",))), 'Add  look("right")  after  look("left")'),
               ("Then it looks at us and talks", lambda r: _in_order(r, ("look", ("right",)), ("look", ("front",))) and r.first("look", "look", "look", "say"), None)],
     "hints": ['The ways are "left", "right", "up", "down" and "front".',
               'look("left")\nwait(1)\nlook("right")\nwait(1)\nlook("front")\nsay("Oh, hello!")'],
     "reference": 'look("left")\nwait(1)\nlook("right")\nwait(1)\nlook("front")\nsay("Oh, hello!")'},

    {"key": "l1", "chapter": 5, "name": "Count with me", "adds": [], "python": ["for"],
     "pip": "A loop has a secret: i is a number that changes each time round. It starts at 0, so i + 1 starts at 1.",
     "job": "Make your pal count out loud from 1 to 5, and jump on every number.",
     "coach": [
               ('for i in range(5):', 'This loop goes round 5 times. Each time round, i is the next number: 0, 1, 2, 3, 4.'),
               ('    say(i + 1)', 'i starts at 0, so i + 1 says 1, then 2, then 3. The + adds one.'),
               ('    jump()', 'This line is inside the loop too. Jump on every number!'),
     ],
     "goals": [("Your pal says 1, 2, 3, 4, 5", lambda r: all(str(n) in r.said for n in range(1, 6)), lambda r: f"I heard: {', '.join(r.said[:6]) or 'nothing'}. I need 1 to 5."),
               ("You use a for loop", lambda r: r.fors >= 1, "Try  for i in range(5):  and push  say(i + 1)  in under it."),
               ("Your pal jumps on every number", lambda r: r.n("jump") >= 5, None)],
     "hints": ["Inside the loop, try  say(i + 1)", "for i in range(5):\n    say(i + 1)\n    jump()"],
     "reference": "for i in range(5):\n    say(i + 1)\n    jump()"},

    {"key": "l2", "chapter": 5, "name": "Hello, everyone", "adds": [], "python": ["for", "list"],
     "pip": "Three friends came to see you! A list keeps them together in [ ] brackets, and a loop can visit each one.",
     "job": 'Say hi to three names from a list, like  ["Ana", "Ben", "Cy"]',
     "coach": [
               ('for name in ["Ana", "Ben", "Cy"]:', 'A list goes in [ ] brackets, with a comma between the names. The loop visits each name, one at a time.'),
               ('    say("Hi " + name)', 'name is a different friend each time round. The + sticks the words together.'),
               ('    jump()', 'This line is inside the loop too. A jump for each friend!'),
     ],
     "goals": [("Your pal greets three different names", lambda r: len(set(r.said)) >= 3, "I need three different hellos."),
               ("You use a list and a for loop", lambda r: r.lists >= 1 and r.fors >= 1, 'Try  for name in ["Ana", "Ben", "Cy"]:'),
               ("A jump for each one too", lambda r: r.n("jump") >= 3, None)],
     "hints": ['for name in ["Ana", "Ben", "Cy"]:   then push in  say("Hi " + name)',
               'for name in ["Ana", "Ben", "Cy"]:\n    say("Hi " + name)\n    jump()'],
     "reference": 'for name in ["Ana", "Ben", "Cy"]:\n    say("Hi " + name)\n    jump()'},

    {"key": "v1", "chapter": 6, "name": "Name tag", "adds": [], "python": ["variable"],
     "pip": "A variable is a name tag for something you want to keep. Give it a name once at the top, then use it anywhere.",
     "job": 'Keep your pal\'s name in a variable, like  name = "Luna"  , and use it in a say.',
     "coach": [
               ('name = "Luna"', 'This is a variable. It is like a name tag: now name means "Luna".'),
               ('say("I am " + name)', 'Your pal says I am, then the word kept in name.'),
               ('say(name.upper() + " IS HERE")', '.upper() makes the word SHOUT in big letters.'),
     ],
     "goals": [("Your pal says its name from a variable", lambda r: r.said_var() >= 1, 'Try  name = "Luna"  and then  say("I am " + name)'),
               ("Your pal says it twice", lambda r: r.said_var() >= 2, None),
               ("One time it SHOUTS with .upper()", lambda r: r.upper >= 1, None)],
     "hints": ['name = "Luna"\nsay("I am " + name)', 'name = "Luna"\nsay("I am " + name)\nsay(name.upper() + " IS HERE")'],
     "reference": 'name = "Luna"\nsay("I am " + name)\nsay(name.upper() + " IS HERE")'},

    {"key": "v2", "chapter": 6, "name": "How many?", "adds": [], "python": ["for", "variable", "fstring"],
     "pip": "If a number lives in a variable, you can change the whole show by changing one line. And an f in front of the quotes lets you put it inside words!",
     "job": "Keep a number in a variable, and jump that many times.",
     "coach": [
               ('jumps = 4', 'A variable can keep a number. Now jumps means 4.'),
               ('for i in range(jumps):', 'The loop goes round jumps times. Change the 4 later, and the loop changes too!'),
               ('    jump()', 'This line is inside the loop. Jump!'),
               ('grow()', 'This line is NOT pushed in, so it runs once, after the loop. I moved it back for you.'),
               ('say(f"{jumps} jumps!")', 'The f lets you put the variable inside the words, in { } brackets.'),
     ],
     "goals": [("A variable sets how many times the loop goes", lambda r: r.range_name and r.n("jump") >= 1, "Try  jumps = 4  and then  for i in range(jumps):"),
               ("Your pal says the number with an f-string", lambda r: r.fstrings >= 1, 'Try  say(f"{jumps} jumps!")'),
               ("Your pal grows bigger too", lambda r: r.n("grow") >= 1, None)],
     "hints": ["jumps = 4\nfor i in range(jumps):\n    jump()", 'jumps = 4\nfor i in range(jumps):\n    jump()\ngrow()\nsay(f"{jumps} jumps!")'],
     "reference": 'jumps = 4\nfor i in range(jumps):\n    jump()\ngrow()\nsay(f"{jumps} jumps!")'},

    {"key": "w1", "chapter": 7, "name": "Make a move", "adds": [], "python": ["def"],
     "pip": "You can make your own commands! def teaches your pal a new word, like boogie. The lines pushed in under it are what the word does.",
     "job": "Teach your pal a move with def, then use it twice.",
     "coach": [
               ('def boogie():', 'def makes a new command called boogie. It ends with a : mark.'),
               ('    jump()', 'Lines pushed in under def are what boogie does. They wait until you use it.'),
               ('    spin()', 'boogie spins too.'),
               ('    jump()', 'And one more jump.'),
               ('boogie()', 'This line is NOT pushed in. It uses your new command! I moved it back for you.'),
               ('boogie()', 'Use it one more time. Now your pal does the whole move again.'),
     ],
     "goals": [("You make your own move and use it", lambda r: len(r.defs) >= 1 and sum(r.own_calls.values()) >= 1, "Try  def boogie():  with moves pushed in, then  boogie()  with no push."),
               ("You use it twice", lambda r: sum(r.own_calls.values()) >= 2, None),
               ("Your move has 3 lines or more", lambda r: r.n("jump") + r.n("spin") + r.n("right") + r.n("left") >= 6, None)],
     "hints": ["Lines pushed in under def don't run until you use the new word.", "def boogie():\n    jump()\n    spin()\n    jump()\nboogie()\nboogie()"],
     "reference": "def boogie():\n    jump()\n    spin()\n    jump()\nboogie()\nboogie()"},

    {"key": "w2", "chapter": 7, "name": "Number three", "adds": [], "python": ["for", "if"],
     "pip": "An if asks a question. Inside a loop, it asks every time round. Count to 5, but jump only on 3!",
     "job": "Count to 5 out loud and jump only on 3.",
     "coach": [
               ('for i in range(1, 6):', 'range(1, 6) counts 1, 2, 3, 4, 5. It stops just before 6.'),
               ('    say(i)', 'Your pal says the number.'),
               ('    if i == 3:', 'if asks a question. == means "is it the same?" So this asks: is i 3?'),
               ('        jump()', 'This line is pushed in under the if, so it only runs when i is 3.'),
     ],
     "goals": [("Your pal counts to 5", lambda r: all(str(n) in r.said for n in range(1, 6)), "Try  for i in range(1, 6):  and  say(i)  pushed in."),
               ("It jumps only once, right after saying 3", lambda r: r.n("jump") == 1 and _after_three(r), "Try  if i == 3:  with  jump()  pushed in under it."),
               ("You use if in a loop", lambda r: r.ifs >= 1 and r.fors >= 1, None)],
     "hints": ["range(1, 6) counts 1, 2, 3, 4, 5.", "for i in range(1, 6):\n    say(i)\n    if i == 3:\n        jump()"],
     "reference": "for i in range(1, 6):\n    say(i)\n    if i == 3:\n        jump()"},
]

# "Your turn": after a mission, one change for the student to make with the guide off.
# (what it asks, check, a hint that says where to change). The guide's own code never passes.
REMIXES = {
    "a1": ("Make your pal say 3 things.", lambda r: r.n("say") >= 3,
           'Add one more  say("...")  line at the bottom, with your own words.'),
    "a2": ("Make your pal jump 3 times.", lambda r: r.n("jump") >= 3,
           "Add one more  jump()  line."),
    "a3": ("After the spotlight, walk on to spot 10, the edge. Then come back to spot 2.",
           lambda r: 10 in _visited(r) and r.x == 2,
           "From spot 7 to spot 10 is 3 steps: add  right(3)  under the say line. Then change the number in  left(5)  so your pal gets back to spot 2."),
    "h1": ("Wave 3 times, then jump.", lambda r: r.n("wave") >= 3 and r.first("wave", "wave", "wave", "jump"),
           "Add one more  wave()  line, then  jump()  at the bottom."),
    "h3": ("Use a feeling you haven't used yet: angry, sleepy, silly, cool or calm.",
           lambda r: any(c == "feel" and a and a[0] in ("angry", "sleepy", "silly", "cool", "calm") for c, a in r.log),
           'Change the middle feeling, like  feel("silly")'),
    "h4": ("Dance two times before you cheer.", lambda r: r.first("dance", "dance", "cheer"),
           "Add one more  dance()  line under the first one."),
    "b1": ("Make your pal jump 10 times. Keep it 2 lines!", lambda r: r.n("jump") >= 10 and r.fors >= 1 and r.code_lines <= 2,
           "Change only one thing: the number in  range(5)"),
    "b2": ("Put a jump inside the loop too, so your pal jumps 4 times.",
           lambda r: r.n("jump") >= 4 and r.fors >= 1 and r.n("confetti") == 1,
           "Add  jump()  pushed in under the for line, next to  right(1)  and  left(1)"),
    "m1": ("Make your pal say something in its move.", lambda r: r.n("say") >= 1 and _actions(r) >= 3,
           'Add a  say("...")  line anywhere in your move.'),
    "t1": ("Grow two times, then shrink two times.", lambda r: r.n("grow") >= 2 and r.n("shrink") >= 2,
           "Add one more  grow()  and one more  shrink()"),
    "t2": ("Make your pal look up, then down.", lambda r: _in_order(r, ("look", ("up",)), ("look", ("down",))),
           'Try  look("up")  and then  look("down")'),
    "l1": ("Count all the way to 10.", lambda r: all(str(n) in r.said for n in range(1, 11)),
           "Change only one thing: the number in  range(5)"),
    "l2": ("Add a 4th name to the list. Try your own name!", lambda r: len(set(r.said)) >= 4 and r.lists >= 1,
           'Put a comma after "Cy" and add a name in  " marks, inside the [ ]'),
    "v1": ("Give your pal a new name: change Luna to any name you like.",
           lambda r: r.said_var() >= 2 and not any("luna" in s.lower() for s in r.said),
           'Change only the first line, like  name = "Sparkle"'),
    "v2": ("Change one line so your pal jumps 7 times.",
           lambda r: r.n("jump") == 7 and r.range_name and r.fstrings >= 1,
           "Change only the first line:  jumps = 7"),
    "w1": ("Use your move 3 times.", lambda r: sum(r.own_calls.values()) >= 3,
           "Add one more  boogie()  line at the bottom, not pushed in."),
    "w2": ("Jump on 5 instead of 3.", lambda r: r.n("jump") == 1 and _after_number(r, "5"),
           "Change only one thing: the 3 in  if i == 3:"),
}
# "Guess first": before the first run of the guide's code, one question about what it will do.
# (question, choices, the right choice). test_pixel_turn.py checks each answer against a real run.
# My Move has none: its code is the student's own.
GUESSES = {
    "a1": ("How many speech bubbles will you see?", ["1", "2", "3"], 1),
    "a2": ("What happens between the two jumps?", ["Your pal talks", "Nothing", "Your pal spins"], 0),
    "a3": ("Where will your pal be at the end?", ["On the spotlight, spot 7", "Back on spot 2", "Off the stage"], 1),
    "h1": ("How many times will your pal wave?", ["1", "2", "3"], 1),
    "h3": ("Which face will your pal have at the end?", ["Sad", "Surprised", "Happy"], 2),
    "h4": ("What comes last?", ["Dancing", "Cheering", "Hearts"], 2),
    "b1": ("There is one jump() inside the loop. How many jumps will you see?", ["1", "5", "2"], 1),
    "b2": ("How many times will confetti fall?", ["Once", "4 times", "8 times"], 0),
    "t1": ("Will your pal be big or small at the end?", ["Big", "Small, like at the start"], 1),
    "t2": ("Where will the eyes look at the end?", ["Left", "Right", "At us"], 2),
    "l1": ("What number will your pal say first?", ["0", "1", "5"], 1),
    "l2": ("What will your pal say first?", ["Hi Ana", "Hi name", "Hi Cy"], 0),
    "v1": ("What will the first speech bubble say?", ["I am name", "I am Luna", "Luna"], 1),
    "v2": ("What will your pal say at the end?", ["{jumps} jumps!", "4 jumps!", "jumps jumps!"], 1),
    "w1": ("boogie has 2 jumps in it. How many jumps in the whole show?", ["2", "3", "4"], 2),
    "w2": ("How many times will your pal jump?", ["Once", "3 times", "5 times"], 0),
}
for _lv in LEVELS:
    _lv["remix"] = REMIXES[_lv["key"]]
    _lv["guess"] = GUESSES.get(_lv["key"])

LEVEL_ORDER = [lv["key"] for lv in LEVELS]
LEVEL_BY_KEY = {lv["key"]: lv for lv in LEVELS}
REMIX_COINS = 15           # once per mission, for doing its Your turn
GUESS_COINS = 5            # for a right first guess on a mission


def _in_order(r, first, then):
    """True if `first` is in the log and `then` comes after it."""
    return first in r.log and then in r.log[r.log.index(first) + 1:]


def _after_three(r):
    """True if the first jump comes right after saying 3."""
    return _after_number(r, "3")


def _after_number(r, number):
    """True if the first jump comes right after saying this number."""
    was = None
    for name, args in r.log:
        if name == "jump":
            return was == number
        if name == "say" and args:
            was = str(args[0])
    return False


def _visited(r):
    spot, seen = START, {START}
    for name, args in r.log:
        if name in ("right", "left"):
            step = args[0] if args else 1
            spot = max(0, min(SPOTS - 1, spot + (step if name == "right" else -step)))
            seen.add(spot)
    return seen


# The live room. Words are tapped, not typed, unless the teacher turns typing on.
ROOM_WORDS = {
    "Wedding": ["Here comes the bride!", "Do you promise?", "I do!", "I do too!", "You look beautiful!", "Congratulations!",
                "Let's eat cake!", "Best wedding ever!", "Catch the flowers!"],
    "Happy": ["Hello!", "Hooray!", "I love you!", "Thank you!", "Ha ha ha!", "Wow!", "Yes!", "You're my best friend!"],
    "Story": ["Look over there!", "Come with me!", "Oh no!", "Help!", "I have an idea!", "Follow me!", "What was that?", "We did it!", "Bye bye!"],
}
ROOM_SAYS = {word for words in ROOM_WORDS.values() for word in words}
ROOM_MOVES = ("wave", "dance", "jump", "cheer", "spin", "nap")
ROOM_RESTS = ("sit", "read")
ROOM_BUDDIES = 3           # how many of a student's other drawings come to the Hang out
ROOM_FX = ("hearts", "stars", "confetti", "petals", "bouquet", "bells", "march", "cake")
LIVE_WORDS_MAX = 60

# ---- Hang out ------------------------------------------------------------------
HANG_AFTER = "a3"          # finishing this mission opens the Hang out
HANG_PLACES = ("park", "wedding", "beach", "night")

# Each mission's first finish opens a box with one of these. "class" ones come
# from the class party meter, for everyone at once.
GIFTS = {
    "party": {"name": "Party hat", "slot": "hat"}, "tophat": {"name": "Top hat", "slot": "hat"},
    "flower": {"name": "Flower", "slot": "hat"}, "bow": {"name": "Big bow", "slot": "hat"},
    "cap": {"name": "Cool cap", "slot": "hat"}, "wizard": {"name": "Wizard hat", "slot": "hat"},
    "shades": {"name": "Cool shades", "slot": "face"}, "heartglasses": {"name": "Heart glasses", "slot": "face"},
    "moustache": {"name": "Silly moustache", "slot": "face"},
    "goldspark": {"name": "Gold sparkles", "slot": "sparkle"}, "heartspark": {"name": "Heart sparkles", "slot": "sparkle"},
    "crown": {"name": "Golden crown", "slot": "hat", "class": True}, "rainbow": {"name": "Rainbow sparkles", "slot": "sparkle", "class": True},
    # These have a price: they come from the shop, never from a box.
    "beanie": {"name": "Rainbow hat", "slot": "hat", "price": 40}, "bunny": {"name": "Bunny ears", "slot": "hat", "price": 50},
    "catears": {"name": "Cat ears", "slot": "hat", "price": 50}, "pirate": {"name": "Pirate hat", "slot": "hat", "price": 60},
    "halo": {"name": "Halo", "slot": "hat", "price": 80}, "starglasses": {"name": "Star glasses", "slot": "face", "price": 60},
    "icespark": {"name": "Ice sparkles", "slot": "sparkle", "price": 70}, "leafspark": {"name": "Leaf sparkles", "slot": "sparkle", "price": 70},
    "frog": {"name": "Frog hat", "slot": "hat", "price": 55}, "witch": {"name": "Witch hat", "slot": "hat", "price": 60},
    "flowercrown": {"name": "Flower crown", "slot": "hat", "price": 70}, "unicorn": {"name": "Unicorn horn", "slot": "hat", "price": 90},
    "monocle": {"name": "Fancy monocle", "slot": "face", "price": 45}, "heromask": {"name": "Hero mask", "slot": "face", "price": 55},
    "galaxyspark": {"name": "Galaxy sparkles", "slot": "sparkle", "price": 90},
    # More for gift boxes.
    "tiara": {"name": "Tiara", "slot": "hat"}, "chef": {"name": "Chef hat", "slot": "hat"},
    "cowboy": {"name": "Cowboy hat", "slot": "hat"}, "headphones": {"name": "Headphones", "slot": "hat"},
    "roundglasses": {"name": "Round glasses", "slot": "face"}, "clownnose": {"name": "Clown nose", "slot": "face"},
    "blush": {"name": "Rosy cheeks", "slot": "face"},
    "candyspark": {"name": "Candy sparkles", "slot": "sparkle"}, "firespark": {"name": "Fire sparkles", "slot": "sparkle"},
    # These unlock by themselves when a goal is reached: [what is counted, how many].
    "gemcrown": {"name": "Gem crown", "slot": "hat", "goal": ["gems", 9]},
    "fishhat": {"name": "Fish hat", "slot": "hat", "goal": ["fish", 5]},
    "friendspark": {"name": "Friendship sparkles", "slot": "sparkle", "goal": ["friends", 5]},
    "goldshades": {"name": "Gold shades", "slot": "face", "goal": ["rounds", 10]},
    "dragon": {"name": "Dragon horns", "slot": "hat", "goal": ["stars", 15]},
    "astro": {"name": "Space helmet", "slot": "hat", "goal": ["gems", 21]},
    "superspark": {"name": "Superstar sparkles", "slot": "sparkle", "goal": ["stars", 27]},
}
BOX_GIFTS = tuple(key for key, gift in GIFTS.items() if not gift.get("class") and not gift.get("price") and not gift.get("goal"))
GOAL_GIFTS = tuple(key for key, gift in GIFTS.items() if gift.get("goal"))
WEAR_SLOTS = ("hat", "face", "sparkle")

# What each full party meter brings, in order. After these it's just a party.
HANG_REWARDS = [{"kind": "place", "key": "snowy", "name": "Snowy hill"}, {"kind": "gift", "key": "crown", "name": "Golden crown"},
                {"kind": "place", "key": "candy", "name": "Candy land"}, {"kind": "gift", "key": "rainbow", "name": "Rainbow sparkles"},
                {"kind": "place", "key": "space", "name": "Outer space"}]
# The Hang out is one long world: each place sits beside the last, and a new place
# from the party meter makes it longer.
PLACE_W = 320
HANG_WORLD = HANG_PLACES + tuple(r["key"] for r in HANG_REWARDS if r["kind"] == "place")
HANG_FINDS = tuple(f"{place}{i}" for place in HANG_WORLD for i in range(3))     # gems to find, three in each place
HANG_TOYS = ("splash", "bounce", "apples", "bells", "cake", "petals", "sand", "coconut", "sparks", "fireflies", "stars", "snow", "candy", "rocket")
PLACED_EACH = 5            # drawings each student can leave out in the world
PLACED_ALL = 60            # and in the whole world, oldest going first
PLACE_GAP = .5             # seconds between placing drawings
TOY_GAP = 1                # seconds between toys
MISSION_POINTS = 2         # a mission's first finish fills the meter this much
MOVE_POINTS = 1            # and a My Move this much, once in a while per student
MOVE_POINT_GAP = 45        # seconds


# ---- Coins, the shop and homes ---------------------------------------------------
# Coding pays the most. Coins from playing stop at PLAY_COINS_DAY each day, so the
# way to more is always a mission.
COINS_FIRST = 20           # a mission's first finish
COINS_STAR = 10            # and each new star
COINS_GEM = 3
COINS_CATCH = 1            # a star in a star shower
COINS_FRIEND = 3           # a first high-five with someone
COINS_ROUND = 5            # finishing a round of a game
COINS_WIN = 5              # and winning it
COINS_FISH = 1
COINS_NEW_FISH = 4         # more, the first time for each kind
PLAY_COINS_DAY = 40

# Things for a home. A price of 0 is there from the start.
FURNITURE = {
    "rug": {"name": "Round rug", "price": 0}, "plant": {"name": "Pot plant", "price": 0},
    "balloons": {"name": "Balloons", "price": 15}, "lamp": {"name": "Lamp", "price": 20}, "teddy": {"name": "Teddy", "price": 20},
    "table": {"name": "Table", "price": 25}, "beanbag": {"name": "Bean bag", "price": 25}, "toybox": {"name": "Toy box", "price": 30},
    "shelf": {"name": "Bookshelf", "price": 35}, "bed": {"name": "Bed", "price": 40}, "sofa": {"name": "Sofa", "price": 40},
    "tv": {"name": "TV", "price": 45}, "tank": {"name": "Fish tank", "price": 50}, "disco": {"name": "Disco ball", "price": 60},
}
HOME_WALLS = {"w_cream": {"name": "Cream walls", "price": 0}, "w_pink": {"name": "Pink walls", "price": 30},
              "w_blue": {"name": "Blue walls", "price": 30}, "w_night": {"name": "Starry walls", "price": 40}}
HOME_FLOORS = {"f_wood": {"name": "Wood floor", "price": 0}, "f_check": {"name": "Checked floor", "price": 30},
               "f_grass": {"name": "Grass floor", "price": 30}, "f_cloud": {"name": "Cloud floor", "price": 40}}
# More rooms, bought in the shop. Each has its own walls, floor and things. They join on
# in the order they're bought: the door on the right of a room goes to the next one.
HOME_ROOMS = {"r_bed": {"name": "Bedroom", "price": 50}, "r_play": {"name": "Playroom", "price": 70},
              "r_attic": {"name": "Attic", "price": 90}}
HOME_FIRST = "Living room"
# Everything with a price, and which shelf of the shop it's on.
SHOP = dict({key: dict(gift, kind="wear") for key, gift in GIFTS.items() if gift.get("price")},
            **{key: dict(item, kind="furniture") for key, item in FURNITURE.items() if item["price"]},
            **{key: dict(item, kind="wall") for key, item in HOME_WALLS.items() if item["price"]},
            **{key: dict(item, kind="floor") for key, item in HOME_FLOORS.items() if item["price"]},
            **{key: dict(item, kind="room") for key, item in HOME_ROOMS.items()})
HOME_ART = 5               # drawings a student can hang up at home

# Fishing at the beach: (picture, name, how often out of 100).
FISH = {"minnow": ("🐟", "Little fish", 34), "stripy": ("🐠", "Stripy fish", 22), "shell": ("🐚", "Shell", 12), "boot": ("🥾", "Old boot", 10),
        "puffer": ("🐡", "Puffer fish", 9), "crab": ("🦀", "Crab", 7), "octopus": ("🐙", "Octopus", 4), "whale": ("🐳", "Tiny whale", 2)}
FISH_X = 140               # where the pier is, from the left of the Beach
FISH_WAIT = (2, 5)         # seconds until a bite
FISH_BITE = 2.5            # seconds to reel it in
DANCE_MOVES = ("wave", "jump", "spin", "cheer")

# ---- Code race: a Hang out game where everyone codes the same little job ----------
# Round 1 takes a job from the first list (commands in order), round 2 from the
# second (a loop), round 3 from the third (more than one thing in a loop). A job is
# what the pal must do, in order, and how many loops it must use. `said` is what its
# say() lines must be, and those words may show in the room even with typing off.
RACE_COMMANDS = ("say", "jump", "wave", "spin", "dance", "cheer", "hearts", "stars", "confetti")
RACE_ICONS = {"say": "💬", "jump": "🦘", "wave": "👋", "spin": "🌀", "dance": "💃", "cheer": "🎉",
              "hearts": "💕", "stars": "⭐", "confetti": "🎊"}
RACE_JOBS = (
    ({"job": "Jump 2 times.", "want": ["jump"] * 2, "answer": "jump()\njump()"},
     {"job": "Wave, then spin.", "want": ["wave", "spin"], "answer": "wave()\nspin()"},
     {"job": 'Say "Hello!", then jump.', "want": ["say", "jump"], "said": ["Hello!"], "answer": 'say("Hello!")\njump()'},
     {"job": "Cheer, then make hearts.", "want": ["cheer", "hearts"], "answer": "cheer()\nhearts()"},
     {"job": "Spin 3 times.", "want": ["spin"] * 3, "answer": "spin()\nspin()\nspin()"}),
    ({"job": "Jump 5 times. Use a loop!", "want": ["jump"] * 5, "loops": 1, "answer": "for i in range(5):\n    jump()"},
     {"job": "Spin 4 times with a loop. Then cheer!", "want": ["spin"] * 4 + ["cheer"], "loops": 1,
      "answer": "for i in range(4):\n    spin()\ncheer()"},
     {"job": "Wave 3 times. Use a loop!", "want": ["wave"] * 3, "loops": 1, "answer": "for i in range(3):\n    wave()"},
     {"job": "Jump 10 times! Use a loop.", "want": ["jump"] * 10, "loops": 1, "answer": "for i in range(10):\n    jump()"},
     {"job": "Make stars 4 times with a loop. Then jump!", "want": ["stars"] * 4 + ["jump"], "loops": 1,
      "answer": "for i in range(4):\n    stars()\njump()"}),
    ({"job": "Jump, then spin. Do that 3 times with a loop!", "want": ["jump", "spin"] * 3, "loops": 1,
      "answer": "for i in range(3):\n    jump()\n    spin()"},
     {"job": "Count 1, 2, 3 with say(). Use a loop!", "want": ["say"] * 3, "said": ["1", "2", "3"], "loops": 1,
      "chips": ["say(i + 1)"], "answer": "for i in range(3):\n    say(i + 1)"},
     {"job": "Wave 2 times, then jump 2 times. Use 2 loops!", "want": ["wave"] * 2 + ["jump"] * 2, "loops": 2,
      "answer": "for i in range(2):\n    wave()\nfor i in range(2):\n    jump()"},
     {"job": "Make hearts, then cheer. Do that 3 times with a loop!", "want": ["hearts", "cheer"] * 3, "loops": 1,
      "answer": "for i in range(3):\n    hearts()\n    cheer()"},
     {"job": 'Say "Hooray!", then jump. Do that 3 times with a loop!', "want": ["say", "jump"] * 3, "said": ["Hooray!"] * 3,
      "loops": 1, "answer": 'for i in range(3):\n    say("Hooray!")\n    jump()'}),
)
RACE_ROUNDS = len(RACE_JOBS)


def _plain(text):
    return re.sub(r"[^a-z0-9]", "", str(text).lower())


def race_icons(names):
    shown = " ".join(RACE_ICONS.get(n, "❓") for n in names[:12])
    return shown + (" ..." if len(names) > 12 else "")


def race_check(job, code):
    """Runs a student's code for a Code race job. Returns whether it does the job,
    a message for the student, the error's line, and the steps for the Hang out."""
    out = perform(code, PIP, commands=RACE_COMMANDS)
    r, error = out["report"], out["error"]
    did = [name for name, _ in r.log]
    if error:
        closed = re.search(r"(\w+)\(\) isn't open yet.*", error)
        if closed:
            error = error[:closed.start()] + ("The Code race uses " + ", ".join(f"{c}()" for c in RACE_COMMANDS) + ".")
        return {"ok": False, "message": "🐞 " + error, "line": out["line"]}
    want = job["want"]
    if not did:
        message = "Your pal didn't do anything yet. Tap a green command to add it."
    elif did != want:
        message = f"Your pal did {race_icons(did)}. The job is {race_icons(want)}."
    elif job.get("said") and [_plain(s) for s in r.said] != [_plain(s) for s in job["said"]]:
        message = ("Your pal said " + ", ".join(f'"{s}"' for s in r.said) + ". The job wants "
                   + ", ".join(f'"{s}"' for s in job["said"]) + ".")
    elif r.fors + r.whiles < job.get("loops", 0):
        message = ("That's the right moves! Now use a loop: tap 🔁 for." if job["loops"] == 1
                   else f"That's the right moves! Now use {job['loops']} loops, one for each move.")
    else:
        return {"ok": True, "message": "⭐ You solved it! Watch your pal.", "steps": compile_move(out["steps"])}
    return {"ok": False, "message": message, "line": None}


def party_goal(level):
    return min(10 + 5 * level, 30)


MOVE_NAMES = ("Moon Hop", "Super Spin", "Wiggle Blast", "Star Dance", "Happy Stomp", "Noodle Arms", "Sparkle Slide", "Turbo Twirl",
              "Bunny Bounce", "Disco Dash", "Jelly Jump", "Rocket Roll", "Silly Shuffle", "Thunder Clap", "Cloud Skip", "Pixel Party")
MOVE_MAX = 24              # the most steps one My Move can play
MOVE_GAP = 6               # seconds between presses, however short the move is
MOVE_MS = {"jump": 650, "wave": 1400, "dance": 2400, "cheer": 1400, "spin": 600, "hearts": 600, "stars": 600, "confetti": 600}
ROOM_SPOT = 26             # how far one spot on the Code stage is in the Hang out
WALK_MS_PER_PIXEL = 12


def compile_move(steps):
    """A finished program's steps, as the list the Hang out replays."""
    out, spot = [], START
    for s in steps:
        do = s["do"]
        if do == "walk":
            out.append({"do": "walk", "dx": (s["to"] - spot) * ROOM_SPOT,
                        "ms": max(200, abs(s["to"] - spot) * ROOM_SPOT * WALK_MS_PER_PIXEL)})
            spot = s["to"]
        elif do == "say":
            out.append({"do": "say", "text": str(s["text"])[:LIVE_WORDS_MAX], "ms": 1200})
        elif do == "feel":
            out.append({"do": "feel", "mood": s["mood"], "ms": 400})
        elif do == "wait":
            out.append({"do": "wait", "ms": min(2000, int(s["beats"] * 450))})
        elif do in MOVE_MS:
            out.append({"do": do, "ms": MOVE_MS[do]})
    return out[:MOVE_MAX]


def stage_move(steps, x, words_allowed, max_x=312):
    """A saved move, ready for this pal at this spot in the room. say() takes
    any words, so only words from the tap list show unless typing is on.
    Returns the steps, where the pal ends up, and how long it all takes."""
    played, total = [], 0
    for s in steps:
        if s["do"] == "say" and not (words_allowed or s["text"] in ROOM_SAYS):
            continue
        s = dict(s)
        if s["do"] == "walk":
            x = max(8, min(max_x, x + s.pop("dx")))
            s["x"] = x
        played.append(s)
        total += s["ms"]
    return played, x, total


def commands_for(key):
    """Every command open at this mission: everything up to it."""
    open_now = []
    for lv in LEVELS:
        open_now += lv["adds"]
        if lv["key"] == key:
            return tuple(open_now)
    return EVERYTHING


def run_level(lv, code, pal, seed=0):
    """Run a mission. Random missions run on many seeds, so the stars mean the
    program works every time. The first run is the one the student watches."""
    commands = commands_for(lv["key"])
    seeds = list(lv.get("seeds", [0]))
    runs = [perform(code, pal, lv.get("rehearse", ()), s + seed, commands, lv.get("setup"))
            for s in seeds]
    main = runs[0]
    report = main["report"]
    report.others = [r["report"] for r in runs]
    good = not any(r["error"] for r in runs)
    stars, reply = [], None
    for text, check, miss in lv["goals"]:
        got = bool(good and check(report))
        stars.append(got)
        if not got and reply is None and miss and good:
            reply = miss(report) if callable(miss) else miss
    out = public(main)
    if not main["error"] and good is False:
        bad = next(r for r in runs if r["error"])
        out["error"], out["line"] = bad["error"], bad["line"]
    remix = lv.get("remix")
    out["remix"] = bool(good and remix and remix[1](report))
    return dict(out, stars=stars, reply=reply, seed=seeds[0] + seed,
                rehearsed=list(lv.get("rehearse", ())))


# ---- Furniture students draw and code ----------------------------------------------
# Any drawing put out at home (or in the world) can have a program. Clicking it
# runs the program's on_click, and everyone in that place sees what it does.
THING_COMMANDS = ("say", "sound", "jump", "spin", "shake", "grow", "shrink", "hide", "appear",
                  "pose", "play", "wait", "hearts", "stars", "confetti", "clicks") + HELPERS
THING_FRAMES = 4           # frames a placed drawing keeps, for pose() and play()
THING_STEPS = 30           # the most steps one click can play
THING_GAP = .6             # seconds between one student's clicks on things
THING_MS = {"jump": 620, "spin": 560, "shake": 500, "hearts": 600, "stars": 600, "confetti": 600,
            "sound": 250, "size": 300, "hide": 300, "appear": 300, "pose": 350}
THING_START = 'def on_click():\n    jump()\n    sound("boing")\n    say("Hello!")\n'


def run_thing(code, drawing, clicks, seed=0):
    """One click on a thing a student drew and coded. The program replays every
    click so far, so clicks() and the program's variables carry on from last time.
    Returns the steps this click makes, or an error with its line."""
    clicks = (max(1, clicks) - 1) % MAX_EVENTS + 1
    out = perform(code, drawing, ["click"] * clicks, seed, THING_COMMANDS)
    error = out["error"]
    closed = re.search(r"(\w+)\(\) isn't open yet.*", error or "")
    if closed:
        error = error[:closed.start()] + (f"Furniture can't {closed[1]}(). It can do: "
                                          + ", ".join(f"{c}()" for c in THING_COMMANDS if c not in HELPERS) + ".")
    elif error:
        error = error.replace("Your pal has", "Your drawing has")
        if "can't work" in error:
            error += " To draw another frame, open it in 🎨 Draw and press + Copy frame."
    if not error and "click" not in out["events"]:
        error = "Nothing happens when it's clicked yet. Put your code under  def on_click():"
    return {"steps": [] if error else [s for s in out["after"] if s["do"] != "event"],
            "error": error, "line": out["line"]}


def thing_steps(steps, frames, words_allowed, look=None):
    """A click's steps, ready for the Hang out, and how the thing looks after them.
    say() takes any words, so only words from the tap list show unless typing is on."""
    look = dict(look or {"frame": 0, "size": 1, "hidden": False})
    out = []
    for s in steps:
        do = s["do"]
        if do == "say":
            if not (words_allowed or s["text"] in ROOM_SAYS):
                continue
            step = {"do": "say", "text": str(s["text"])[:LIVE_WORDS_MAX], "ms": 1300}
        elif do == "wait":
            step = {"do": "wait", "ms": min(2000, s["beats"] * 450)}
        elif do == "sound":
            step = {"do": "sound", "name": s["name"], "ms": THING_MS["sound"]}
        elif do == "size":
            look["size"] = s["to"]
            step = {"do": "size", "to": s["to"], "ms": THING_MS["size"]}
        elif do in ("hide", "appear"):
            look["hidden"] = do == "hide"
            step = {"do": do, "ms": THING_MS[do]}
        elif do == "pose":
            if s["frame"] >= frames:
                continue
            look["frame"] = s["frame"]
            step = {"do": "pose", "frame": s["frame"], "ms": THING_MS["pose"]}
        elif do == "play":
            step = {"do": "play", "ms": 250 * max(2, frames)}
        elif do in THING_MS:
            step = {"do": do, "ms": THING_MS[do]}
        else:
            continue                 # a face made with pose("happy"), say: nothing to show on a thing
        out.append(step)
        if len(out) >= THING_STEPS:
            break
    return out, look
