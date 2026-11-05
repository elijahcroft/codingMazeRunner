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

SCENES = ("stage", "park", "beach", "night", "snowy", "candy", "space", "castle")
SOUNDS = ("ding", "boing", "pop", "tada", "meow", "drum", "whoosh", "yay")
FRIENDS = ("cat", "bunny", "kid", "bean")
PROPS = ("star", "gem", "cake", "ball")
EVENTS = ("click", "feed", "play", "sleep", "key")
KEYS = ("left", "right", "up", "down", "space")
FEELINGS = ("happy", "sad", "surprised", "angry", "sleepy", "silly", "cool", "calm")
LOOKS = ("left", "right", "up", "down", "front")

# What stars open. "class" counts the whole class's stars together.
UNLOCKS = [
    {"kind": "scene", "key": "beach", "stars": 6},
    {"kind": "sound", "key": "meow", "stars": 9},
    {"kind": "scene", "key": "night", "stars": 12},
    {"kind": "friend", "key": "bunny", "stars": 15},
    {"kind": "scene", "key": "snowy", "stars": 20},
    {"kind": "friend", "key": "kid", "stars": 25},
    {"kind": "scene", "key": "candy", "stars": 30},
    {"kind": "friend", "key": "bean", "stars": 40},
    {"kind": "scene", "key": "space", "stars": 50},
    {"kind": "scene", "key": "castle", "class": 150},
]
LOCKED = {(u["kind"], u["key"]) for u in UNLOCKS}


def open_unlocks(stars, class_stars):
    return {(u["kind"], u["key"]) for u in UNLOCKS
            if ("stars" in u and stars >= u["stars"]) or ("class" in u and class_stars >= u["class"])}


def unlock_hint(kind, key):
    u = next(x for x in UNLOCKS if (x["kind"], x["key"]) == (kind, key))
    return f"opens at {u['stars']} stars" if "stars" in u else f"opens when the class has {u['class']} stars"


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
    "cheer": "cheer()", "look": 'look("left")', "feel": 'feel("happy")',
}
COMMANDS = tuple(USAGE)
SENSORS = {"x": "x()", "clicks": "clicks()", "hungry": "hungry()", "sleepy": "sleepy()",
           "touching": 'touching("star")', "score": "score()", "weather": "weather()"}
USAGE.update(SENSORS)
EVERYTHING = COMMANDS + tuple(SENSORS)
HELPERS = ("len", "str", "int", "choice", "randint", "abs", "max", "min")
NO_ARGS = {"jump", "spin", "shake", "grow", "shrink", "hide", "appear", "play", "hearts",
           "stars", "confetti", "rain", "snow", "friend_jump", "bye", "eat", "nap", "point",
           "wave", "dance", "cheer"}


def word_list(words):
    return ", ".join(f'"{w}"' for w in words)


class Show:
    """What happens on stage. Every command is a step the browser plays back."""

    def __init__(self, pal, unlocked, seed, cast=None, stand_in=False):
        self.pal = pal
        self.cast = cast or {}       # classmates' pals, by lowercase name
        self.stand_in = stand_in     # a shared show keeps going if a classmate's pal has left
        self.unlocked = unlocked
        self.rng = random.Random(seed)
        self.steps = []
        self.mark = 0                # where the steps for this click start
        self.line = None
        self.x = START
        self.visible = True
        self.size = 1
        self.scene = "stage"
        self.friend = None
        self.props = {}              # spot -> what's there
        self.points = 0
        self.click_count = 0
        self.since_food = 3          # a new pet is hungry
        self.since_nap = 0
        self.forecast = None
        self.posed = set()           # faces and moves shown with pose(), not frames
        self.classmates = 0          # how many times a classmate's pal came on
        self.log = []                # (command, arguments) in order, for judging
        self.fired = []              # where in the log each click starts

    def step(self, do, **arg):
        if len(self.steps) - self.mark >= MAX_STEPS:
            raise BotError(f"That's a very long show! It stops at {MAX_STEPS} moves. "
                           f"Is a loop going round too many times?")
        if self.line:
            arg["line"] = self.line
        self.steps.append(dict(arg, do=do))

    def locked(self, kind, key, what):
        if (kind, key) in LOCKED and (kind, key) not in self.unlocked:
            raise BotError(f"🔒 {what} {unlock_hint(kind, key)}. Keep earning stars to open it!")

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

    def c_friend_say(self, name, *args):
        if len(args) != 1:
            raise BotError('friend_say() needs one thing to say, like  friend_say("Hi!")')
        if not self.friend:
            raise BotError('There\'s no friend on stage yet. Bring one on first, like  friend("cat")')
        self.step("friend_say", text=self.text(args[0]))

    def c_friend_jump(self):
        if not self.friend:
            raise BotError('There\'s no friend on stage yet. Bring one on first, like  friend("cat")')
        self.step("friend_jump")

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
        self.locked("sound", args[0], f'The "{args[0]}" sound')
        self.step("sound", name=args[0])

    def c_scene(self, name, *args):
        if len(args) != 1 or args[0] not in SCENES:
            raise BotError(f'Pick a place, like  scene("park"). The places are: {word_list(SCENES)}.')
        self.locked("scene", args[0], f'The "{args[0]}" scene')
        self.scene = args[0]
        self.step("scene", name=args[0])

    def c_friend(self, name, *args):
        who = args[0].strip().lower() if len(args) == 1 and isinstance(args[0], str) else ""
        if who in self.cast and who not in FRIENDS:
            pal = self.cast[who]
            self.friend = who
            self.classmates += 1
            self.step("friend", kind=who, pal={"size": pal["size"], "palette": pal["palette"], "frames": pal["frames"][:1],
                                               "marks": pal.get("marks", "")})
            return
        if self.stand_in and who and who not in FRIENDS:
            self.friend = "bean"
            self.step("friend", kind="bean")
            return
        if len(args) != 1 or args[0] not in FRIENDS:
            raise BotError(f'Pick a friend, like  friend("cat"). The friends are: {word_list(FRIENDS)}. '
                           f"A classmate's pal can come too, by name, once their show is in the Theatre.")
        self.locked("friend", args[0], f'The {args[0]} friend')
        self.friend = args[0]
        self.step("friend", kind=args[0])

    def c_bye(self):
        self.friend = None
        self.step("bye")

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


def perform(code, pal=PIP, events=(), seed=0, commands=EVERYTHING, unlocked=LOCKED, setup=None,
            cast=None, stand_in=False):
    """Run a program. `events` are clicks, like "click", "feed" or "key:left"."""
    show = Show(pal, unlocked, seed, cast, stand_in)
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


def used_classmate(result):
    return any(s["do"] == "friend" and "pal" in s for s in result["steps"])


# ---- Missions ------------------------------------------------------------------

def _mark(spot):
    def setup(show):
        show.step("mark", at=spot)
    return setup


def _anywhere(show):
    show.x = show.rng.randint(0, 6)
    show.step("place", at=show.x)
    show.step("mark", at=9)


def _three_ways(r):
    return len({tuple(o.log) for o in r.others}) >= 2


def _weather_fits(r):
    return all((o.forecast == "rain" and o.n("rain")) or (o.forecast == "snow" and o.n("snow"))
               or (o.forecast == "sun" and o.said and not o.n("rain") and not o.n("snow"))
               for o in r.others)


def _steps_grow(r):
    return len(r.walks) >= 3 and all(b > a for a, b in zip(r.walks, r.walks[1:]))


CHAPTERS = [
    {"key": "a", "name": "Opening Night", "icon": "🎭"},
    {"key": "h", "name": "Come Alive", "icon": "✨"},
    {"key": "b", "name": "Again! Again!", "icon": "🔁"},
    {"key": "c", "name": "Name Tags", "icon": "🏷️"},
    {"key": "d", "name": "Story Time", "icon": "📖"},
    {"key": "e", "name": "Surprise!", "icon": "🎲"},
    {"key": "f", "name": "Pet Pal", "icon": "🐾"},
    {"key": "g", "name": "Game Maker", "icon": "🕹️"},
]

# `adds` opens commands, and `python` opens the shapes of Python on the chips.
# A goal is (what it asks, check, and what Pip says when it's missing).
# The last hint is always a program that does the job.
LEVELS = [
    {"key": "a1", "chapter": 0, "name": "Say hello", "adds": ["say"], "python": [],
     "pip": "Hi, I'm Pip! Welcome to the Pixel Theatre. The crowd is here, and your pal goes first. "
            "Make your pal say hello!",
     "job": 'Type  say("Hello")  then press Show time!',
     "goals": [("Your pal says something", lambda r: r.n("say") >= 1, "Your pal didn't say anything yet. Type  say(\"Hello\")"),
               ("Your pal says two things", lambda r: r.n("say") >= 2, None),
               ("One of them has 3 words or more", lambda r: any(len(s.split()) >= 3 for s in r.said), None)],
     "hints": ['Commands have brackets. Words go inside the brackets, with  "  at both ends.',
               'say("Hello")\nsay("I am so happy to be here")'],
     "reference": 'say("Hello")\nsay("I am so happy to be here")'},

    {"key": "a2", "chapter": 0, "name": "Jump for joy", "adds": ["jump"], "python": [],
     "pip": "The crowd loves a jump! Each line runs one after the other, from top to bottom.",
     "job": "Make your pal jump two times.",
     "goals": [("Your pal jumps two times", lambda r: r.n("jump") >= 2, lambda r: f"I counted {r.n('jump')} jump{'' if r.n('jump') == 1 else 's'}. I need 2."),
               ("Your pal says something too", lambda r: r.n("say") >= 1, None),
               ("Your pal talks between the two jumps", lambda r: r.first("jump", "say", "jump"), None)],
     "hints": ["Put  jump()  on one line, then  jump()  again on the next line.",
               'jump()\nsay("Wheee!")\njump()'],
     "reference": 'jump()\nsay("Wheee!")\njump()'},

    {"key": "a3", "chapter": 0, "name": "Find the spotlight", "adds": ["right", "left"], "python": [],
     "setup": _mark(7),
     "pip": "See the spotlight? Your pal is on spot 2 and the light is on spot 7. The number says how far to walk.",
     "job": "Walk your pal into the spotlight, on spot 7.",
     "goals": [("Your pal goes to spot 7", lambda r: 7 in _visited(r), lambda r: f"Your pal stopped on spot {r.x}. The light is on spot 7. How many steps is that from spot 2?"),
               ("Your pal says something there", lambda r: r.first("right", "say"), None),
               ("Then your pal walks back to spot 2", lambda r: r.x == 2 and r.n("left") >= 1, None)],
     "hints": ["From 2 to 7 is 5 steps, so try  right(5)", 'right(5)\nsay("Here I am!")\nleft(5)'],
     "reference": 'right(5)\nsay("Here I am!")\nleft(5)'},

    {"key": "a4", "chapter": 0, "name": "Take a bow", "adds": ["spin", "hearts", "stars", "shake"], "python": [],
     "pip": "A great show ends with a big finish. Try the two new commands!",
     "job": "Spin, then fill the stage with hearts.",
     "goals": [("Your pal spins, then hearts appear", lambda r: r.first("spin", "hearts"), "I need  spin()  first, then  hearts()  on the line after."),
               ("Your pal jumps as well", lambda r: r.n("jump") >= 1, None),
               ("You use 5 lines or more", lambda r: r.lines >= 5, None)],
     "hints": ["Type  spin()  and then  hearts()  on the next line.",
               'say("Thank you!")\njump()\nspin()\nhearts()\nsay("Bye!")'],
     "reference": 'say("Thank you!")\njump()\nspin()\nhearts()\nsay("Bye!")'},

    {"key": "a5", "chapter": 0, "name": "Strike a pose", "adds": ["pose", "wait"], "python": [],
     "pip": "pose() shows a frame you drew, by its name or number. Your pal can make faces too, even with no frames at all.",
     "job": 'Strike a pose. Try "happy" and "sad".',
     "goals": [("Your pal shows a frame", lambda r: r.n("pose") >= 1, 'Try  pose("happy")  or use a frame number, like  pose(2)'),
               ("You use wait() after it", lambda r: r.first("pose", "wait"), None),
               ("Your pal shows two different frames", lambda r: len(r.poses) >= 2, None)],
     "hints": ['Type  pose("happy")  then  wait(2)  on the next line.',
               'pose("happy")\nwait(2)\npose("sad")'],
     "reference": 'pose("happy")\nwait(2)\npose("sad")'},

    {"key": "a6", "chapter": 0, "name": "Change the scene", "adds": ["scene", "sound"], "python": [],
     "pip": 'Time to leave the theatre! scene() changes the place and sound() plays a noise. '
            'The places open up as you earn stars.',
     "job": 'Take your pal to the park with  scene("park")',
     "goals": [("The scene changes", lambda r: r.n("scene") >= 1, 'Type  scene("park")'),
               ("You play a sound", lambda r: r.n("sound") >= 1, None),
               ("Your pal walks in the new scene", lambda r: r.first("scene", "right") or r.first("scene", "left"), None)],
     "hints": ['Type  scene("park")  on the first line.', 'scene("park")\nsound("tada")\nright(4)\nsay("Fresh air!")'],
     "reference": 'scene("park")\nsound("tada")\nright(4)\nsay("Fresh air!")'},

    {"key": "h1", "chapter": 1, "name": "Say hello", "adds": ["wave"], "python": [],
     "pip": "Your pal has real arms now! The computer found them when you drew it. If you drew no arms, it wiggles instead.",
     "job": "Say hello, then wave.",
     "goals": [("Your pal waves", lambda r: r.n("wave") >= 1, "Type  wave()  on a line of its own."),
               ("Your pal says something first", lambda r: r.first("say", "wave"), "Put  say()  on the line above  wave()"),
               ("Your pal waves two times", lambda r: r.n("wave") >= 2, None)],
     "hints": ["Type  say(\"Hello!\")  and then  wave()  on the next line.", 'say("Hello!")\nwave()\nwave()'],
     "reference": 'say("Hello!")\nwave()\nwave()'},

    {"key": "h2", "chapter": 1, "name": "Who's there?", "adds": ["look"], "python": [],
     "pip": "Your pal can move its eyes. Try  look(\"left\")  and see! The ways are left, right, up, down and front.",
     "job": "Look left, then look right.",
     "goals": [("Your pal looks left", lambda r: ("look", ("left",)) in r.log, 'Type  look("left")'),
               ("Then it looks right", lambda r: r.first("look", "look") and ("look", ("right",)) in r.log, 'Now add  look("right")  on the next line.'),
               ("Then it looks at us", lambda r: bool(r.log) and r.log[-1] == ("look", ("front",)) or ("look", ("front",)) in r.log, None)],
     "hints": ['look("left")  makes the eyes go left.', 'look("left")\nwait(1)\nlook("right")\nwait(1)\nlook("front")\nsay("Oh, it\'s you!")'],
     "reference": 'look("left")\nwait(1)\nlook("right")\nwait(1)\nlook("front")\nsay("Oh, it\'s you!")'},

    {"key": "h3", "chapter": 1, "name": "How do you feel?", "adds": ["feel"], "python": [],
     "pip": "Faces change too! feel() changes your pal's eyes and mouth. Watch them: it's your own drawing, moving.",
     "job": 'Make your pal sad, then happy.',
     "goals": [("Your pal feels sad", lambda r: ("feel", ("sad",)) in r.log, 'Type  feel("sad")'),
               ("Then your pal feels happy", lambda r: ("feel", ("happy",)) in r.log and r.log.index(("feel", ("happy",))) > (r.log.index(("feel", ("sad",))) if ("feel", ("sad",)) in r.log else 10**6), 'Put  feel("happy")  after  feel("sad")'),
               ("Three feelings or more", lambda r: len({a for c, a in r.log if c == "feel"}) >= 3, None)],
     "hints": ["The feelings are happy, sad, surprised, angry, sleepy, silly, cool and calm.",
               'feel("sad")\nwait(1)\nfeel("surprised")\nwait(1)\nfeel("happy")'],
     "reference": 'feel("sad")\nwait(1)\nfeel("surprised")\nwait(1)\nfeel("happy")'},

    {"key": "h4", "chapter": 1, "name": "Dance floor", "adds": ["dance", "cheer"], "python": [],
     "pip": "Time to move! dance() uses every part your pal has: arms, legs, ears and tail. cheer() throws its arms up.",
     "job": "Dance, then cheer.",
     "goals": [("Your pal dances", lambda r: r.n("dance") >= 1, "Type  dance()"),
               ("Then your pal cheers", lambda r: r.first("dance", "cheer"), "Add  cheer()  on the line after  dance()"),
               ("Hearts or stars at the end", lambda r: bool(r.log) and r.log[-1][0] in ("hearts", "stars"), None)],
     "hints": ["Type  dance()  then  cheer()  then  hearts()", "dance()\ncheer()\nhearts()"],
     "reference": "dance()\ncheer()\nhearts()"},

    {"key": "h5", "chapter": 1, "name": "A tiny play", "adds": [], "python": [],
     "pip": "Now put it all together. A play needs a sad bit, a surprise and a happy ending. It's your play, so you pick the words!",
     "job": "Make a little play: sad, then surprised, then happy.",
     "goals": [("Your pal feels sad first", lambda r: r.first("feel", "say") and any(c == "feel" and a == ("sad",) for c, a in r.log), 'Start with  feel("sad")  and then  say()  something.'),
               ("Something surprises it", lambda r: ("feel", ("surprised",)) in r.log or ("look", ("left",)) in r.log or ("look", ("right",)) in r.log, None),
               ("A happy ending with dancing", lambda r: ("feel", ("happy",)) in r.log and r.n("dance") >= 1, None)],
     "hints": ['feel("sad")  then  say("I lost my hat.")  . What happens next?',
               'feel("sad")\nsay("I lost my hat.")\nlook("left")\nfeel("surprised")\nsay("There it is!")\nfeel("happy")\ndance()'],
     "reference": 'feel("sad")\nsay("I lost my hat.")\nlook("left")\nfeel("surprised")\nsay("There it is!")\nfeel("happy")\ndance()'},

    {"key": "b1", "chapter": 2, "name": "Bounce!", "adds": [], "python": ["for"],
     "pip": "Five jumps would take five lines. A loop says it in two! The line under it is pushed in, and it repeats.",
     "job": "Make your pal jump 5 times with a for loop.",
     "goals": [("Your pal jumps 5 times", lambda r: r.n("jump") >= 5, lambda r: f"I counted {r.n('jump')} jumps. I need 5."),
               ("You use a for loop", lambda r: r.fors >= 1, "Try  for i in range(5):  and push  jump()  in under it."),
               ("Your whole program is 2 lines", lambda r: r.fors >= 1 and r.code_lines <= 2, None)],
     "hints": ["The number in  range(5)  is how many times it repeats.", "Press Tab to push a line in.",
               "for i in range(5):\n    jump()"],
     "reference": "for i in range(5):\n    jump()"},

    {"key": "b2", "chapter": 2, "name": "Side step", "adds": ["confetti"], "python": ["for"],
     "pip": "A loop can repeat lots of lines. Everything pushed in goes round together. A line that isn't pushed in runs once, after the loop.",
     "job": "Step right, then left, 4 times over, then throw confetti once.",
     "goals": [("Right and left, 4 times over", lambda r: r.n("right") >= 4 and r.n("left") >= 4, lambda r: f"I saw {r.n('right')} right and {r.n('left')} left. I need 4 of each."),
               ("Confetti comes once, at the end", lambda r: r.n("confetti") == 1 and r.log[-1][0] == "confetti", "Confetti should run once. Don't push it in. Line it up with the word for."),
               ("You use a for loop", lambda r: r.fors >= 1, None)],
     "hints": ["Push in  right(1)  and  left(1)  under the for line.", "for i in range(4):\n    right(1)\n    left(1)\nconfetti()"],
     "reference": "for i in range(4):\n    right(1)\n    left(1)\nconfetti()"},

    {"key": "b3", "chapter": 2, "name": "Count with me", "adds": [], "python": ["for"],
     "pip": "That i in the loop is a number that changes each time round. It starts at 0, so i + 1 starts at 1.",
     "job": "Make your pal count out loud from 1 to 5.",
     "goals": [("Your pal says 1, 2, 3, 4, 5", lambda r: all(str(n) in r.said for n in range(1, 6)), lambda r: f"I heard: {', '.join(r.said[:6]) or 'nothing'}. I need 1 to 5."),
               ("You use a for loop", lambda r: r.fors >= 1, None),
               ("Your pal jumps on every number", lambda r: r.n("jump") >= 5, None)],
     "hints": ["Inside the loop, try  say(i + 1)", "for i in range(5):\n    say(i + 1)\n    jump()"],
     "reference": "for i in range(5):\n    say(i + 1)\n    jump()"},

    {"key": "b4", "chapter": 2, "name": "Hello, everyone", "adds": [], "python": ["for", "list"],
     "pip": "Three friends came to see you! A list keeps them together in square brackets, and a loop can visit each one.",
     "job": 'Say hi to three names from a list, like  ["Ana", "Ben", "Cy"]',
     "goals": [("Your pal greets three different names", lambda r: len(set(r.said)) >= 3, "I need three different hellos."),
               ("You use a list and a for loop", lambda r: r.lists >= 1 and r.fors >= 1, "Try  for name in [\"Ana\", \"Ben\", \"Cy\"]:"),
               ("It's a wave for each one too", lambda r: r.n("spin") >= 3 or r.n("jump") >= 3, None)],
     "hints": ['for name in ["Ana", "Ben", "Cy"]:   then push in  say("Hi " + name)',
               'for name in ["Ana", "Ben", "Cy"]:\n    say("Hi " + name)\n    jump()'],
     "reference": 'for name in ["Ana", "Ben", "Cy"]:\n    say("Hi " + name)\n    jump()'},

    {"key": "b5", "chapter": 2, "name": "Flip book", "adds": ["play"], "python": ["for"],
     "pip": "Here's a secret: a walk is just two drawings swapped again and again. play() shows all your frames in order, like a flip book. "
            "Only one frame? In 💓 Life, press a move, then Turn into frames.",
     "job": "Use a loop to play your frames 3 times.",
     "goals": [("Your frames play 3 times", lambda r: r.n("play") >= 3, lambda r: f"They played {r.n('play')} times. I need 3."),
               ("You use a for loop", lambda r: r.fors >= 1, None),
               ("Your pal walks while it plays", lambda r: r.n("right") >= 3 or r.n("left") >= 3, None)],
     "hints": ["Push  play()  in under  for i in range(3):", "for i in range(3):\n    play()\n    right(1)"],
     "reference": "for i in range(3):\n    play()\n    right(1)"},

    {"key": "c1", "chapter": 3, "name": "Name tag", "adds": [], "python": ["variable"],
     "pip": "A variable is a name tag for something you want to keep. Say it once at the top, then use it anywhere.",
     "job": 'Keep your pal\'s name in a variable, like  name = "Luna"  , and use it in a say.',
     "goals": [("Your pal says its name from a variable", lambda r: r.said_var() >= 1, 'Try  name = "Luna"  and then  say("I am " + name)'),
               ("Your pal says it twice", lambda r: r.said_var() >= 2, None),
               ("One time it SHOUTS with .upper()", lambda r: r.upper >= 1, None)],
     "hints": ['name = "Luna"\nsay("I am " + name)', 'name = "Luna"\nsay("I am " + name)\nsay(name.upper() + " IS HERE")'],
     "reference": 'name = "Luna"\nsay("I am " + name)\nsay(name.upper() + " IS HERE")'},

    {"key": "c2", "chapter": 3, "name": "How many?", "adds": ["grow", "shrink"], "python": ["for", "variable", "fstring"],
     "pip": "If a number lives in a variable, you can change the whole show by changing one line. And an f in front of the quotes lets you put it inside words!",
     "job": "Keep a number in a variable, and jump that many times.",
     "goals": [("A variable sets how many times the loop goes", lambda r: r.range_name and r.n("jump") >= 1, "Try  jumps = 4  and then  for i in range(jumps):"),
               ("Your pal says the number with an f-string", lambda r: r.fstrings >= 1, 'Try  say(f"{jumps} jumps!")'),
               ("Your pal grows bigger too", lambda r: r.n("grow") >= 1, None)],
     "hints": ["jumps = 4\nfor i in range(jumps):\n    jump()", 'jumps = 4\nfor i in range(jumps):\n    jump()\ngrow()\nsay(f"{jumps} jumps!")'],
     "reference": 'jumps = 4\nfor i in range(jumps):\n    jump()\ngrow()\nsay(f"{jumps} jumps!")'},

    {"key": "c3", "chapter": 3, "name": "Bigger steps", "adds": ["hide", "appear"], "python": ["for", "variable"],
     "pip": "A variable can change as the show goes on. steps = steps + 1 means: take steps, add one, and keep the answer.",
     "job": "Walk 3 times, and make each walk longer than the last.",
     "goals": [("Each walk is longer than the last", _steps_grow, lambda r: f"Your walks were {r.walks or 'none yet'}. Each one needs to be longer."),
               ("A variable changes inside a loop", lambda r: r.changes >= 1 and r.fors >= 1, "Try  steps = steps + 1  inside the loop."),
               ("Your pal vanishes and comes back", lambda r: r.first("hide", "appear"), None)],
     "hints": ["Start with  steps = 1  , then push  right(steps)  and  steps = steps + 1  into a loop.",
               "steps = 1\nfor i in range(3):\n    right(steps)\n    steps = steps + 1\nhide()\nappear()"],
     "reference": "steps = 1\nfor i in range(3):\n    right(steps)\n    steps = steps + 1\nhide()\nappear()"},

    {"key": "c4", "chapter": 3, "name": "Where am I?", "adds": ["x"], "python": ["fstring"],
     "pip": "Some commands answer you! x() tells you which spot your pal is on.",
     "job": "Walk somewhere, then say which spot you're on, using x().",
     "goals": [("Your pal says its spot", lambda r: r.n("x") >= 1 and any(str(r.x) in s for s in r.said), 'Try  say(f"I am on spot {x()}")'),
               ("It walks first", lambda r: r.first("right", "x") or r.first("left", "x"), None),
               ("It tells you two different spots", lambda r: r.n("x") >= 2, None)],
     "hints": ['right(3)\nsay(f"I am on spot {x()}")', 'right(3)\nsay(f"I am on spot {x()}")\nleft(1)\nsay(f"Now spot {x()}")'],
     "reference": 'right(3)\nsay(f"I am on spot {x()}")\nleft(1)\nsay(f"Now spot {x()}")'},

    {"key": "d1", "chapter": 4, "name": "Make a move", "adds": [], "python": ["def"],
     "pip": "You can make your own commands! def teaches your pal a new word, like boogie. "
            "You're getting good, so from now on the command buttons only start the line, and you type the rest.",
     "job": "Teach your pal a move with def, then use it twice.",
     "goals": [("You make your own move and use it", lambda r: len(r.defs) >= 1 and sum(r.own_calls.values()) >= 1, "Try  def boogie():  with moves pushed in, then  boogie()  with no push."),
               ("You use it twice", lambda r: sum(r.own_calls.values()) >= 2, None),
               ("Your move has 3 lines or more", lambda r: r.n("jump") + r.n("spin") + r.n("right") + r.n("left") >= 6, None)],
     "hints": ["Lines pushed in under def don't run until you use the new word.", "def boogie():\n    jump()\n    spin()\n    jump()\n\nboogie()\nboogie()"],
     "reference": "def boogie():\n    jump()\n    spin()\n    jump()\n\nboogie()\nboogie()"},

    {"key": "d2", "chapter": 4, "name": "Say hi to a friend", "adds": ["friend", "friend_say"], "python": [],
     "pip": "Every story needs a friend. Bring the cat on, then the two can talk. Shows are best when someone has something to say!",
     "job": "Bring a friend on and have a little chat, taking turns.",
     "goals": [("A friend joins you", lambda r: r.n("friend") >= 1, 'Type  friend("cat")'),
               ("You take turns talking", lambda r: r.first("say", "friend_say", "say") or r.first("friend_say", "say", "friend_say"), "Your pal says something, then  friend_say(\"Hi!\")  , then your pal again."),
               ("4 lines of talking or more", lambda r: r.n("say") + r.n("friend_say") >= 4, None)],
     "hints": ['friend("cat")\nsay("Hi cat!")\nfriend_say("Meow!")\nsay("Nice to meet you")',
               'friend("cat")\nsay("Hi cat!")\nfriend_say("Meow!")\nsay("Want to dance?")\nfriend_say("Meow!!")'],
     "reference": 'friend("cat")\nsay("Hi cat!")\nfriend_say("Meow!")\nsay("Want to dance?")\nfriend_say("Meow!!")'},

    {"key": "d3", "chapter": 4, "name": "Hi, you!", "adds": [], "python": ["def"],
     "pip": "A move can take a word in its brackets, and do something different each time. It's like a blank to fill in.",
     "job": "Make  def greet(name):  and greet two people with it.",
     "goals": [("Your move takes a name", lambda r: r.params >= 1, "Put a word in the brackets:  def greet(name):"),
               ("You use it for two people", lambda r: len(set(r.said)) >= 2 and sum(r.own_calls.values()) >= 2, 'Try  greet("Ana")  and  greet("Ben")'),
               ("You use it in a loop or 3 times", lambda r: sum(r.own_calls.values()) >= 3 or r.fors >= 1, None)],
     "hints": ['def greet(name):\n    say("Hi " + name)\n\ngreet("Ana")', 'def greet(name):\n    say("Hi " + name)\n    jump()\n\ngreet("Ana")\ngreet("Ben")\ngreet("Cy")'],
     "reference": 'def greet(name):\n    say("Hi " + name)\n    jump()\n\ngreet("Ana")\ngreet("Ben")\ngreet("Cy")'},

    {"key": "d4", "chapter": 4, "name": "A story in two acts", "adds": ["friend_jump", "bye"], "python": ["def"],
     "pip": "Real shows have acts. Put each act in its own def, and the bottom of your program reads like a list of what happens.",
     "job": "Write two acts with def, in two different scenes, then run them.",
     "goals": [("Two acts made with def", lambda r: len(r.defs) >= 2 and sum(r.own_calls.values()) >= 2, "Make  def act_one():  and  def act_two():  and use them both."),
               ("The scene changes", lambda r: r.n("scene") >= 1, None),
               ("A friend comes on and says bye at the end", lambda r: r.first("friend", "bye"), None)],
     "hints": ['def act_one():\n    say("Once upon a time...")\n\ndef act_two():\n    scene("park")\n    say("The end")\n\nact_one()\nact_two()',
               'def act_one():\n    say("Once upon a time...")\n    friend("cat")\n\ndef act_two():\n    scene("park")\n    friend_jump()\n    say("The end")\n    bye()\n\nact_one()\nact_two()'],
     "reference": 'def act_one():\n    say("Once upon a time...")\n    friend("cat")\n\ndef act_two():\n    scene("park")\n    friend_jump()\n    say("The end")\n    bye()\n\nact_one()\nact_two()'},

    {"key": "e1", "chapter": 5, "name": "Happy or sad?", "adds": [], "python": ["if", "choice"], "seeds": range(12),
     "pip": "Let's make a show that's different every time! choice() picks one thing from a list, and if decides what to do about it.",
     "job": "Pick a mood at random, and do something different for each.",
     "goals": [("The show changes from run to run", _three_ways, 'Start with  mood = choice(["happy", "sad"])'),
               ("You use if and else", lambda r: r.ifs >= 1 and r.elses >= 1, 'Try  if mood == "happy":  and  else:'),
               ("Your pal tells you the mood too", lambda r: all(any(w in " ".join(o.said) for w in o.values.values() if isinstance(w, str)) for o in r.others), None)],
     "hints": ['Two equals signs ask a question:  if mood == "happy":', 'mood = choice(["happy", "sad"])\nsay("I feel " + mood)\nif mood == "happy":\n    hearts()\nelse:\n    shake()'],
     "reference": 'mood = choice(["happy", "sad"])\nsay("I feel " + mood)\nif mood == "happy":\n    hearts()\nelse:\n    shake()'},

    {"key": "e2", "chapter": 5, "name": "What's the weather?", "adds": ["weather", "rain", "snow"], "python": ["if", "elif"], "seeds": range(12),
     "pip": "weather() looks outside and tells you \"sun\", \"rain\" or \"snow\". You can't know which, so your show has to be ready for all three!",
     "job": 'Rain gets rain(), snow gets snow(), and sun gets a say.',
     "goals": [("The show fits all three kinds of weather", _weather_fits, 'Use  if weather() == "rain":  then  elif  and  else'),
               ("You use if and elif", lambda r: r.ifs >= 2, None),
               ("Your pal says something in rain and in snow too", lambda r: all(o.said for o in r.others), None)],
     "hints": ['now = weather()\nif now == "rain":\n    rain()\nelif now == "snow":\n    snow()\nelse:\n    say("Sunny!")',
               'now = weather()\nsay("It is " + now)\nif now == "rain":\n    rain()\nelif now == "snow":\n    snow()\nelse:\n    say("Sunny!")'],
     "reference": 'now = weather()\nsay("It is " + now)\nif now == "rain":\n    rain()\nelif now == "snow":\n    snow()\nelse:\n    say("Sunny!")'},

    {"key": "e3", "chapter": 5, "name": "Number three jumps", "adds": [], "python": ["for", "if"],
     "pip": "An if inside a loop asks its question every time round. It's like a game: count to 5, but jump only on 3.",
     "job": "Count to 5 out loud and jump only on 3.",
     "goals": [("Your pal counts to 5", lambda r: all(str(n) in r.said for n in range(1, 6)), "Try  for i in range(1, 6):  and  say(i)  pushed in."),
               ("It jumps only once, right after saying 3", lambda r: r.n("jump") == 1 and _after_three(r), "Try  if i == 3:  with  jump()  pushed in under it."),
               ("You use if in a loop", lambda r: r.ifs >= 1 and r.fors >= 1, None)],
     "hints": ["range(1, 6) counts 1, 2, 3, 4, 5.", "for i in range(1, 6):\n    say(i)\n    if i == 3:\n        jump()"],
     "reference": "for i in range(1, 6):\n    say(i)\n    if i == 3:\n        jump()"},

    {"key": "e4", "chapter": 5, "name": "Walk into the light", "adds": [], "python": ["while"], "setup": _anywhere, "seeds": range(8),
     "pip": "Your pal starts on a different spot each time, so right(5) won't always work! while keeps going until the answer changes.",
     "job": "Walk one step at a time until you reach spot 9.",
     "goals": [("Your pal always ends on spot 9", lambda r: all(o.x == 9 for o in r.others), "Try  while x() < 9:  and push  right(1)  in under it."),
               ("You use a while loop", lambda r: r.whiles >= 1, None),
               ("Your pal cheers when it gets there", lambda r: r.n("say") >= 1 or r.n("hearts") >= 1, None)],
     "hints": ["x() < 9 means: am I still before spot 9?", 'while x() < 9:\n    right(1)\nsay("Made it!")'],
     "reference": 'while x() < 9:\n    right(1)\nsay("Made it!")'},

    {"key": "f1", "chapter": 6, "name": "Hey, that tickles!", "adds": [], "python": ["on_click"], "rehearse": ["click"],
     "pip": "So far your pal only does what's written. Now it can wait for YOU. The lines under  def on_click():  run each time someone clicks your pal.",
     "job": "Make your pal react when it's clicked.",
     "goals": [("Your pal does something when clicked", lambda r: bool(r.reacts) and bool(r.reacts[0]), "Write  def on_click():  and push  say(\"That tickles!\")  in under it."),
               ("It says something", lambda r: r.did(0, "say"), None),
               ("And moves too", lambda r: r.did(0, "jump") or r.did(0, "spin") or r.did(0, "shake"), None)],
     "hints": ["Nothing happens until the click, so there's nothing to see at first. After Show time, click your pal!", 'def on_click():\n    say("That tickles!")\n    shake()'],
     "reference": 'def on_click():\n    say("That tickles!")\n    shake()'},

    {"key": "f2", "chapter": 6, "name": "Count the pokes", "adds": ["clicks"], "python": ["on_click", "if"], "rehearse": ["click", "click", "click"],
     "pip": "clicks() remembers how many times you've been clicked. On the third click, your pal should do something special.",
     "job": "Say how many clicks so far, and throw hearts on click number 3.",
     "goals": [("Your pal says the number of clicks", lambda r: r.n("clicks") >= 1 and {"1", "2", "3"} <= {w for s in r.said for w in s.split()}, 'Try  say(clicks())  inside on_click.'),
               ("Hearts come on click 3, not before", lambda r: r.did(2, "hearts") and not r.did(0, "hearts") and not r.did(1, "hearts"), "Try  if clicks() == 3:  with  hearts()  pushed in."),
               ("You use else as well", lambda r: r.elses >= 1, None)],
     "hints": ["def on_click():\n    say(clicks())\n    if clicks() == 3:\n        hearts()", "def on_click():\n    say(clicks())\n    if clicks() == 3:\n        hearts()\n    else:\n        jump()"],
     "reference": "def on_click():\n    say(clicks())\n    if clicks() == 3:\n        hearts()\n    else:\n        jump()"},

    {"key": "f3", "chapter": 6, "name": "Feed me", "adds": ["hungry", "eat"], "python": ["on_feed", "if"], "rehearse": ["feed", "feed"],
     "pip": "Your pal has become a pet! A Feed button shows up when you write  def on_feed():  Then  hungry()  says True or False. Pets don't eat when they're full.",
     "job": "If your pet is hungry it eats. If it's full, it says so.",
     "goals": [("A hungry pet eats", lambda r: r.did(0, "eat"), "Inside on_feed, try  if hungry():  with  eat()  pushed in."),
               ("A full pet doesn't eat", lambda r: not r.did(1, "eat") and r.did(1, "say"), 'Add  else:  with  say("I am full!")'),
               ("It shows it's happy after eating", lambda r: r.did(0, "hearts") or r.did(0, "spin") or r.did(0, "jump"), None)],
     "hints": ['def on_feed():\n    if hungry():\n        eat()\n    else:\n        say("I am full!")', 'def on_feed():\n    if hungry():\n        eat()\n        hearts()\n    else:\n        say("I am full!")'],
     "reference": 'def on_feed():\n    if hungry():\n        eat()\n        hearts()\n    else:\n        say("I am full!")'},

    {"key": "f4", "chapter": 6, "name": "Bedtime", "adds": ["sleepy", "nap"], "python": ["on_play", "on_sleep", "if"], "rehearse": ["play", "play", "play", "play", "sleep", "sleep"],
     "pip": "Pets get tired from playing. on_play and on_sleep add two more buttons. After a few games, sleepy() turns True.",
     "job": "Your pet plays when you press Play, and naps when it's sleepy.",
     "goals": [("Your pet does something on Play", lambda r: r.did(0, "spin") or r.did(0, "jump") or r.did(0, "say"), "Write  def on_play():  with a move pushed in."),
               ("A sleepy pet naps", lambda r: r.did(4, "nap"), "Write  def on_sleep():  and inside it  if sleepy():  then  nap()"),
               ("A wide-awake pet won't nap", lambda r: not r.did(5, "nap") and r.did(5, "say"), 'Add an else with  say("Not tired!")'),
               ],
     "hints": ['def on_play():\n    spin()\n\ndef on_sleep():\n    if sleepy():\n        nap()', 'def on_play():\n    spin()\n\ndef on_sleep():\n    if sleepy():\n        nap()\n    else:\n        say("Not tired!")'],
     "reference": 'def on_play():\n    spin()\n\ndef on_sleep():\n    if sleepy():\n        nap()\n    else:\n        say("Not tired!")'},

    {"key": "f5", "chapter": 6, "name": "The perfect pet", "adds": [], "python": ["on_click", "on_feed", "on_play", "on_sleep", "if"],
     "rehearse": ["click", "feed", "feed", "play", "play", "sleep", "sleep"],
     "pip": "This one is all yours. Build a whole pet that answers everything. Then press Add to the Theatre in Free Stage and let the class look after it!",
     "job": "Make click, Feed, Play and Sleep all work.",
     "goals": [("All four do something", lambda r: all(any(ev) for ev in r.reacts), lambda r: "Something didn't react. You need on_click, on_feed, on_play and on_sleep."),
               ("It's hungry or full, sleepy or not", lambda r: r.n("hungry") >= 1 and r.n("sleepy") >= 1, None),
               ("It starts with a hello", lambda r: bool(r.reacts) and r.n("say") > sum(1 for ev in r.reacts for n, _ in ev if n == "say"), None)],
     "hints": ["Copy the shape from Feed me and Bedtime, then add on_click.",
               'say("Hello! Look after me.")\n\ndef on_click():\n    jump()\n\ndef on_feed():\n    if hungry():\n        eat()\n    else:\n        say("Full!")\n\ndef on_play():\n    spin()\n\ndef on_sleep():\n    if sleepy():\n        nap()\n    else:\n        say("Not tired!")'],
     "reference": 'say("Hello! Look after me.")\n\ndef on_click():\n    jump()\n\ndef on_feed():\n    if hungry():\n        eat()\n    else:\n        say("Full!")\n\ndef on_play():\n    spin()\n\ndef on_sleep():\n    if sleepy():\n        nap()\n    else:\n        say("Not tired!")'},

    {"key": "g1", "chapter": 7, "name": "Arrow keys", "adds": [], "python": ["on_key", "if"], "rehearse": ["key:right", "key:right", "key:left", "key:space"],
     "pip": "Now YOU can steer! on_key runs each time a key is pressed, and key tells you which one.",
     "job": "Left and right arrows walk your pal. Space makes it jump.",
     "goals": [("The right arrow walks right", lambda r: r.did(0, "right"), 'Try  if key == "right":  with  right(1)  pushed in.'),
               ("The left arrow walks left", lambda r: r.did(2, "left"), None),
               ("Space jumps", lambda r: r.did(3, "jump"), None)],
     "hints": ['def on_key(key):\n    if key == "right":\n        right(1)', 'def on_key(key):\n    if key == "right":\n        right(1)\n    if key == "left":\n        left(1)\n    if key == "space":\n        jump()'],
     "reference": 'def on_key(key):\n    if key == "right":\n        right(1)\n    if key == "left":\n        left(1)\n    if key == "space":\n        jump()'},

    {"key": "g2", "chapter": 7, "name": "Grab the star", "adds": ["put", "take", "touching"], "python": ["on_key", "if"], "rehearse": ["key:right"] * 4,
     "pip": "A game needs something to get! put() places a star, and touching() checks if your pal is on it.",
     "job": 'Put a star on spot 6. When your pal reaches it, take it.',
     "goals": [("There's a star on spot 6", lambda r: ("put", ("star", 6)) in r.log, 'At the top, write  put("star", 6)'),
               ("Your pal takes it", lambda r: r.n("take") >= 1, 'Inside on_key, after moving:  if touching("star"):  and  take("star")'),
               ("Something great happens", lambda r: r.first("take", "hearts") or r.first("take", "say") or r.first("take", "confetti"), None)],
     "hints": ['put("star", 6)\n\ndef on_key(key):\n    if key == "right":\n        right(1)\n    if touching("star"):\n        take("star")',
               'put("star", 6)\n\ndef on_key(key):\n    if key == "right":\n        right(1)\n    if key == "left":\n        left(1)\n    if touching("star"):\n        take("star")\n        hearts()'],
     "reference": 'put("star", 6)\n\ndef on_key(key):\n    if key == "right":\n        right(1)\n    if key == "left":\n        left(1)\n    if touching("star"):\n        take("star")\n        hearts()'},

    {"key": "g3", "chapter": 7, "name": "Keep score", "adds": ["point", "score"], "python": ["on_key", "if"], "rehearse": ["key:right"] * 2 + ["key:left"] * 4,
     "pip": "point() adds one to the score on the screen, and score() tells you what it is. Two stars means you win!",
     "job": "Two stars on the stage: each one scores a point. Say you won on 2 points.",
     "goals": [("Two stars on the stage", lambda r: r.n("put") >= 2, 'put("star", 4)  and  put("star", 0)'),
               ("Each star scores a point", lambda r: r.score >= 2, "After take, add  point()"),
               ("Your pal says you won", lambda r: r.n("score") >= 1 and r.said, 'Try  if score() == 2:  with  say("You win!")')],
     "hints": ["Pal starts on spot 2. Two rights reach 4, then four lefts reach 0.",
               'put("star", 4)\nput("star", 0)\n\ndef on_key(key):\n    if key == "right":\n        right(1)\n    if key == "left":\n        left(1)\n    if touching("star"):\n        take("star")\n        point()\n    if score() == 2:\n        say("You win!")'],
     "reference": 'put("star", 4)\nput("star", 0)\n\ndef on_key(key):\n    if key == "right":\n        right(1)\n    if key == "left":\n        left(1)\n    if touching("star"):\n        take("star")\n        point()\n    if score() == 2:\n        say("You win!")'},

    {"key": "g4", "chapter": 7, "name": "Your own game", "adds": [], "python": ["on_key", "if", "randint"], "seeds": range(4),
     "rehearse": ["key:right"] * 8 + ["key:left"] * 10 + ["key:right"] * 10,
     "pip": "Your final show! randint(0, 10) picks a random spot, so the game is different every time. Make it, then put it in the Theatre for everyone to play.",
     "job": "Put a star on a random spot. Walking onto it scores a point.",
     "goals": [("The star lands somewhere new each time", _three_ways, 'Try  put("star", randint(0, 10))'),
               ("Reaching it scores a point", lambda r: all(o.score >= 1 for o in r.others), None),
               ("A new star appears after you score", lambda r: r.n("put") >= 2, 'After  point()  , put another star with randint.')],
     "hints": ['put("star", randint(0, 10))\n\ndef on_key(key):\n    if key == "right":\n        right(1)\n    if key == "left":\n        left(1)\n    if touching("star"):\n        take("star")\n        point()',
               'put("star", randint(0, 10))\n\ndef on_key(key):\n    if key == "right":\n        right(1)\n    if key == "left":\n        left(1)\n    if touching("star"):\n        take("star")\n        point()\n        put("star", randint(0, 10))'],
     "reference": 'put("star", randint(0, 10))\n\ndef on_key(key):\n    if key == "right":\n        right(1)\n    if key == "left":\n        left(1)\n    if touching("star"):\n        take("star")\n        point()\n        put("star", randint(0, 10))'},
]
LEVEL_ORDER = [lv["key"] for lv in LEVELS]
LEVEL_BY_KEY = {lv["key"]: lv for lv in LEVELS}
HELPERS_AT = {"choice": "e1", "randint": "g4"}


def _visited(r):
    spot, seen = START, {START}
    for name, args in r.log:
        if name in ("right", "left"):
            step = args[0] if args else 1
            spot = max(0, min(SPOTS - 1, spot + (step if name == "right" else -step)))
            seen.add(spot)
    return seen


def _after_three(r):
    was = None
    for name, args in r.log:
        if name == "jump":
            return was == "3"
        if name == "say" and args:
            was = str(args[0])
    return False


# Free Stage's Give me an idea button: little shows to start from.
IDEAS = [
    'scene("park")\nfeel("sleepy")\nsay("Yawn...")\nwait(2)\nfeel("happy")\nsay("Good morning!")\nwave()',
    'for i in range(3):\n    dance()\n    hearts()\ncheer()',
    'look("left")\nlook("right")\nfriend("cat")\nfriend_say("Boo!")\nfeel("surprised")\njump()\nsay("You scared me!")\nfeel("happy")',
    'say("Watch this!")\nspin()\njump()\nspin()\nconfetti()\nsay("Ta-da!")',
    'def on_click():\n    jump()\n    say("That tickles!")\n\nsay("Click me!")',
    'for i in range(3):\n    right(2)\n    jump()\nsay("I made it!")\nstars()',
    'scene("park")\nsnow()\nfeel("surprised")\nsay("Snow!")\ndance()',
    'feel("cool")\nsay("I am the coolest pal.")\nfeel("silly")\nsay("Just kidding!")\ncheer()',
]


def commands_for(key):
    """Every command open at this mission: everything up to it."""
    open_now = []
    for lv in LEVELS:
        open_now += lv["adds"]
        if lv["key"] == key:
            return tuple(open_now)
    return EVERYTHING


def run_level(lv, code, pal, unlocked=LOCKED, seed=0):
    """Run a mission. Random missions run on many seeds, so the stars mean the
    program works every time. The first run is the one the student watches."""
    commands = commands_for(lv["key"])
    seeds = list(lv.get("seeds", [0]))
    runs = [perform(code, pal, lv.get("rehearse", ()), s + seed, commands, unlocked, lv.get("setup"))
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
    return dict(out, stars=stars, reply=reply, seed=seeds[0] + seed,
                rehearsed=list(lv.get("rehearse", ())))


def run_free(code, pal, unlocked, seed=0, events=(), cast=None, stand_in=False):
    return public(perform(code, pal, events, seed, EVERYTHING, unlocked, None, cast, stand_in))


def react(code, pal, unlocked, seed, events, level=None, cast=None, stand_in=False):
    """One new click on a show that's already playing: replay it all, and send
    back only what the newest click did."""
    if len(events) > MAX_EVENTS:
        return {"steps": [], "error": None, "line": None, "full": True}
    lv = LEVEL_BY_KEY.get(level)
    result = perform(code, pal, events, seed, commands_for(level) if lv else EVERYTHING,
                     unlocked, lv.get("setup") if lv else None, cast, stand_in)
    return {"steps": result["after"], "error": result["error"], "line": result["line"]}


FREE_STARTER = '''# This is your own stage. Anything goes!
scene("park")
say("Welcome to my show")
jump()
'''
