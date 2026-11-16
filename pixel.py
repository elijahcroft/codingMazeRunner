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
        self.stars = None            # on the Free stage: the student's stars, which open more places

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
        words = show_value(value)
        return words if len(words) <= MAX_SAY else words[:MAX_SAY - 1].rstrip() + "…"   # the … shows there was more

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
        need = SCENE_STARS.get(args[0], 0)
        if self.stars is not None and self.stars < need:
            raise BotError(f"🔒 {args[0]} opens at {need} ★, and you have {self.stars}. Missions give stars! "
                           f"Open now: {word_list([p for p in SCENES if SCENE_STARS.get(p, 0) <= self.stars])}.")
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
    if re.search(r"""["'][^"']*["']\s+[A-Za-z_]\w*\s*\)|[A-Za-z_]\w*\s+["']""", line) and "(" in line:
        return 'To join words and a name, put a  +  between them, like  say("I am " + name)'
    twice = re.fullmatch(r"([A-Za-z_]\w*)\s*(--|\+\+)", line)
    if twice:
        sign = "-" if twice[2] == "--" else "+"
        return f"Python doesn't have  {twice[2]}  . Write  {twice[1]} = {twice[1]} {sign} 1"
    if line.count("[") > line.count("]"):
        return "This line opens a list with  [  but never closes it. Add a  ]  after the last thing in the list"
    flipped = re.fullmatch(r"""(".*"|'.*'|\d+)\s*=\s*([A-Za-z_]\w*)""", line)
    if flipped:
        return f"The name goes first, then the  =  then what to keep in it. Write  {flipped[2]} = {flipped[1]}"
    if re.fullmatch(r"[A-Za-z_]\w*\(\s*\w*\s*\):", line) and not re.match(r"(if|elif|while|for)\b", line):
        return f"To make a new command, start the line with  def  , like  def {line}"
    if re.match(r"for\s+in\b", line):
        return "A for loop needs a name to count with. Write it like this:  " + re.sub(r"^for\s+in\b", "for i in", line)
    if line.endswith(":") and not any(l.strip() for l in lines[n:]):
        return ("This line ends with a  :  so it needs a line under it, pushed in. "
                "Press Enter, then Tab, and add a command like  jump()")
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
        # Where each name sits, so a mistake with it can be told in its own words.
        self.parent = {id(child): n for n in ast.walk(self.tree) for child in ast.iter_child_nodes(n)}
        self.at_name = None
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
            mine = difflib.get_close_matches(name, [n for n in self.named if n not in self.funcs and n != name], 1, 0.8)
            if "is a command" in text and mine:      # f"{jump} jumps!" when the variable is jumps
                raise BotError(f"{name} is a command, not one of your variables. Did you mean  {mine[0]}  ?")
            up = self.parent.get(id(self.at_name)) if self.at_name is not None and self.at_name.id == name else None
            if name not in self.named and isinstance(up, ast.Call) and isinstance(up.func, ast.Name) \
                    and up.func.id != "say" and '"' in USAGE.get(up.func.id, ""):
                raise BotError(f'Words need quotes round them, like  {up.func.id}("{name}")')
            if "command" in text or "global" in text or "before giving" in text:
                raise
            if name in self.named and "Did you mean" in text:
                raise
            if name not in self.named:
                raise BotError(self.unknown_word(name))
            raise BotError(f"I don't know '{name}' yet. Set it on a line above this one, "
                           f"like  {name} = 3")

    def unknown_word(self, name):
        """A bare word that isn't a variable: say what the line probably meant."""
        same = [n for n in self.named if n.lower() == name.lower()]
        if same:
            return f"Capital letters matter in names. You made  {same[0]}  , so write  {same[0]}  here, not  {name}"
        typo = difflib.get_close_matches(name, [n for n in self.named if n not in self.funcs], 1, 0.75)
        if typo:
            return f"I don't know  {name}  . Did you mean  {typo[0]}  ? Check the spelling: it has to match exactly."
        node = self.at_name if self.at_name is not None and self.at_name.id == name else None
        up = self.parent.get(id(node))
        if isinstance(up, ast.List):
            return f'Words in a list need quotes round each one, like  ["{name}", "Ben"]'

        if isinstance(up, ast.Call) and isinstance(up.func, ast.Name) and up.func.id in USAGE \
                and up.func.id != "say":
            command = up.func.id
            if command in ("right", "left", "wait"):
                return f"{command}() needs a number in its brackets, like  {USAGE[command]}"
            return f'Words need quotes round them, like  {command}("{name}")'
        if isinstance(up, ast.Assign) and up.value is node and len(up.targets) == 1 \
                and isinstance(up.targets[0], ast.Name):
            return (f'Words need quotes round them, like  {up.targets[0].id} = "{name}"  '
                    f'For a number, leave the quotes off, like  {up.targets[0].id} = 3')
        return (f'Words need quotes round them, like  say("{name}")  '
                f'If {name} is meant to be a variable, set it first, like  {name} = 3')

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
        if isinstance(node, ast.Name):
            self.at_name = node
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
        if isinstance(node, ast.Constant) and isinstance(node.value, str) and len(node.value) > MAX_TEXT:
            raise BotError(f"That's a lot of words! Keep each one under {MAX_TEXT} letters, "
                           f"or split them into two  say()  lines.")
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "input" \
                and "input" not in self.funcs:
            raise BotError('Your pal can\'t ask questions with input(). Put the words in a variable '
                           'instead, like  name = "Luna"')
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

    def call_user(self, fn, args):
        need = len(fn.args.args)
        if len(args) != need:          # plainer than "expected 1 thing(s) but got 0"
            if not need:
                raise BotError(f"{fn.name}() doesn't take anything in its ( ). Try  {fn.name}()")
            raise BotError(f"{fn.name}() needs {need} thing{'s' if need != 1 else ''} in its ( ), like  "
                           f"{fn.name}({', '.join(['3'] * need)})  . You gave it {len(args) or 'nothing'}.")
        return super().call_user(fn, args)

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
        if name in ("random", "rand", "dice") and name not in self.funcs:
            raise BotError("For a surprise number, use  randint(1, 6)  : the two numbers are the smallest and biggest it can be.")
        if name in ("walk", "move", "go"):
            raise BotError(f"There's no {name}(). Your pal walks with  right(3)  or  left(3)")
        known = [c for c in COMMANDS + tuple(SENSORS) if c in self.commands] + list(self.funcs) + list(HELPERS)
        near = difflib.get_close_matches(name.lower(), known, 1, 0.65)
        if near:
            raise BotError(f"I don't know '{name}'. Did you mean  {USAGE.get(near[0], near[0] + '()')}  ?")
        if name in self.named:
            raise BotError(f"Your new command {name} is made further down. Python reads from the top, "
                           f"so move the  def {name}():  lines up above the line that uses it.")
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
            if isinstance(v, ast.BinOp) and isinstance(v.left, ast.Name) and isinstance(v.op, (ast.Add, ast.Sub)):
                raise BotError(f"To change {v.left.id}, keep the answer in it:  {v.left.id} = {ast.unparse(v)}")
            if isinstance(v, ast.Compare) and isinstance(v.left, ast.Name) and len(v.ops) == 1 \
                    and isinstance(v.ops[0], ast.Eq):
                right = v.comparators[0]
                shown = f'"{right.value}"' if isinstance(right, ast.Constant) and isinstance(right.value, str) else ast.unparse(right)
                raise BotError(f"To keep something in  {v.left.id}  use one  =  like  "
                               f"{v.left.id} = {shown}   Two  ==  is for asking if two things are the same.")
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
        self.randoms = sum(1 for n in nodes if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
                           and n.func.id in ("choice", "randint"))
        self.calls = Counter(n.func.id for n in nodes if isinstance(n, ast.Call) and isinstance(n.func, ast.Name))
        self.methods = Counter(n.func.attr for n in nodes if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute))
        self.adds = count(ast.AugAssign)
        self.elifs = sum(1 for n in nodes if isinstance(n, ast.If) and len(n.orelse) == 1
                         and isinstance(n.orelse[0], ast.If) and n.orelse[0].col_offset == n.col_offset)
        self.positions = set()          # numbers used in [ ], like the 0 in moods[0]
        for n in nodes:
            if isinstance(n, ast.Subscript):
                try:
                    self.positions.add(ast.literal_eval(n.slice))
                except (ValueError, TypeError, SyntaxError):
                    pass
        self.loops_over = [n.iter.id for n in nodes if isinstance(n, ast.For) and isinstance(n.iter, ast.Name)]
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
        if "That's a very long show" in error and director and any(isinstance(n, ast.While) for n in ast.walk(director.tree)):
            why = ("Your pal got to the edge and can't walk any further, so the loop's question stays yes. "
                   "Check which way it walks, and the number and the  <  or  >  in the while line." if "x()" in code and show.x in (0, SPOTS - 1)
                   else "Something pushed in under the  while  has to change each time round, so its question ends up no.")
            error = re.sub(r"That's a very long show!.*", "Your while loop never stopped! " + why, error)
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
    {"key": "r", "name": "Surprise!", "icon": "🎲"},
    {"key": "k", "name": "Click Me!", "icon": "🖱️"},
    {"key": "c", "name": "Keep Going", "icon": "⏳"},
    {"key": "j", "name": "My List", "icon": "📋"},
    {"key": "s", "name": "Keep Score", "icon": "🏆"},
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

    # Surprise! Each run can be different. The stars are checked on many runs (`seeds`),
    # so they mean the code works every time, and the student watches one more, picked at random.
    {"key": "r1", "chapter": 8, "name": "Surprise mood", "adds": [], "python": ["random"], "seeds": range(12),
     "pip": "Surprise! choice() picks one thing from a list, and you never know which. Press Show time! again and you might get a different one.",
     "job": "Let choice() pick your pal's mood, then say which one it got.",
     "coach": [
               ('mood = choice(["happy", "silly", "cool"])', 'choice() picks one thing from the list, by surprise. Now mood is one of them.'),
               ('feel(mood)', 'Your pal makes the face that was picked.'),
               ('say("I feel " + mood)', 'Your pal says which one it got. Press Show time! again for a new surprise!'),
     ],
     "goals": [("choice() picks your pal's mood", lambda r: r.randoms >= 1 and r.n("feel") >= 1, 'Try  mood = choice(["happy", "silly", "cool"])  and then  feel(mood)'),
               ("Your pal says the mood it got", lambda r: all(any(o.log[i][1][0] in s for s in o.said for i in range(len(o.log)) if o.log[i][0] == "feel") for o in r.others), 'Add  say("I feel " + mood)'),
               ("It can pick 3 different moods", lambda r: len(_moods(r)) >= 3, None)],
     "hints": ['choice() needs a list in [ ] brackets:  choice(["happy", "silly", "cool"])',
               'mood = choice(["happy", "silly", "cool"])\nfeel(mood)\nsay("I feel " + mood)'],
     "reference": 'mood = choice(["happy", "silly", "cool"])\nfeel(mood)\nsay("I feel " + mood)'},

    {"key": "r2", "chapter": 8, "name": "Roll the dice", "adds": [], "python": ["random", "if"], "seeds": range(30),
     "pip": "randint(1, 6) picks a whole number from 1 to 6, like rolling a dice. Then an if can ask what you rolled!",
     "job": "Roll a dice, say the number, and cheer only on a 6.",
     "coach": [
               ('roll = randint(1, 6)', 'randint(1, 6) picks a number from 1 to 6, like a dice. roll keeps it.'),
               ('say(roll)', 'Your pal says the number it rolled.'),
               ('if roll == 6:', 'if asks a question: did we roll a 6?'),
               ('    cheer()', 'This line is pushed in under the if, so your pal only cheers on a 6.'),
     ],
     "goals": [("Your pal says a dice number from randint()", lambda r: r.randoms >= 1 and all(o.said and o.said[0] in "123456" for o in r.others), "Try  roll = randint(1, 6)  and then  say(roll)"),
               ("It cheers on a 6, and only on a 6", lambda r: r.randoms >= 1 and all((o.n("cheer") > 0) == (o.said[:1] == ["6"]) for o in r.others), "Try  if roll == 6:  with  cheer()  pushed in under it."),
               ("You use if", lambda r: r.ifs >= 1, None)],
     "hints": ["randint(1, 6) gives 1, 2, 3, 4, 5 or 6.", "roll = randint(1, 6)\nsay(roll)\nif roll == 6:\n    cheer()"],
     "reference": "roll = randint(1, 6)\nsay(roll)\nif roll == 6:\n    cheer()"},

    {"key": "r3", "chapter": 8, "name": "Lucky jumps", "adds": [], "python": ["random", "for", "variable", "fstring"], "seeds": range(12),
     "pip": "A surprise number can go in a loop too! Then nobody knows how many jumps are coming, not even you.",
     "job": "Jump a surprise number of times, from 2 to 5, then say how many.",
     "coach": [
               ('jumps = randint(2, 5)', 'A surprise number from 2 to 5, kept in a variable called jumps.'),
               ('for i in range(jumps):', 'The loop goes round jumps times.'),
               ('    jump()', 'This line is inside the loop. Jump!'),
               ('say(f"{jumps} lucky jumps!")', 'This line is NOT pushed in, so it runs once, after the loop. I moved it back for you.'),
     ],
     "goals": [("A surprise number of jumps", lambda r: r.randoms >= 1 and r.range_name and r.n("jump") >= 1, "Try  jumps = randint(2, 5)  and then  for i in range(jumps):"),
               ("Your pal says how many, once, at the end", lambda r: all(o.said and o.n("say") == 1 and o.log[-1][0] == "say" and o.said[-1].split()[0] == str(o.n("jump")) for o in r.others),
                'After the loop, not pushed in:  say(f"{jumps} lucky jumps!")'),
               ("Different runs jump a different number of times", lambda r: len({o.n("jump") for o in r.others}) >= 2, None)],
     "hints": ["jumps = randint(2, 5)\nfor i in range(jumps):\n    jump()", 'jumps = randint(2, 5)\nfor i in range(jumps):\n    jump()\nsay(f"{jumps} lucky jumps!")'],
     "reference": 'jumps = randint(2, 5)\nfor i in range(jumps):\n    jump()\nsay(f"{jumps} lucky jumps!")'},

    # Click Me!: events. Lines under def on_click(): wait for a click. Pip clicks to test the
    # stars (the "rehearse" clicks), and after the show the student can click their pal too.
    {"key": "k1", "chapter": 9, "name": "Poke me!", "adds": [], "python": ["click"],
     "rehearse": ("click", "click", "click"),
     "pip": "Your pal can wait for a click! Lines pushed in under  def on_click():  don't run straight away. "
            "They run every time someone clicks your pal. I'll click it 3 times to test it, then you try!",
     "job": "Make your pal jump and say something every time it's clicked.",
     "coach": [
               ('def on_click():', "This line means: every time someone clicks your pal, run the lines under me."),
               ('    jump()', "This line is pushed in, so it waits for a click. Then your pal jumps."),
               ('    say("Hee hee!")', "And it giggles! After the show, click your pal on the stage yourself."),
     ],
     "goals": [("Your pal does something when it's clicked", lambda r: _click_moves(r, 0) >= 1,
                lambda r: _click_name_slip(r) or "Nothing happens when I click your pal. Put  def on_click():  on its own line, and push in the lines under it."
                          if "click" not in r.events else "I clicked, but your pal didn't do anything. Push some lines in under  def on_click():"),
               ("It says something on every click", lambda r: len(r.reacts) >= 3 and all(r.did(i, "say") for i in range(3)), None),
               ("It does 2 things or more on every click", lambda r: len(r.reacts) >= 3 and all(_click_moves(r, i) >= 2 for i in range(3)), None)],
     "hints": ["Put  def on_click():  on a line of its own. The lines under it, pushed in, run on every click.",
               'def on_click():\n    jump()\n    say("Hee hee!")'],
     "reference": 'def on_click():\n    jump()\n    say("Hee hee!")'},

    {"key": "k2", "chapter": 9, "name": "Count the pokes", "adds": ["clicks"], "python": ["else"],
     "rehearse": ("click", "click", "click", "click"),
     "pip": "clicks() is how many times your pal has been clicked so far. And here's  else:  . "
            "The lines under  else:  run when the  if  isn't true. I'll click 4 times to test it.",
     "job": "Say how many clicks. Cheer on the 3rd click, and jump on every other one.",
     "coach": [
               ('def on_click():', "Every click runs the lines under here."),
               ('    say(clicks())', "Your pal says how many clicks so far: 1, then 2, then 3..."),
               ('    if clicks() == 3:', "Is this the 3rd click?"),
               ('        cheer()', "Yes? Then cheer!"),
               ('    else:', "else means: if not. It lines up with the if. I moved it back for you."),
               ('        jump()', "On every other click, your pal jumps."),
     ],
     "goals": [("Your pal cheers on the 3rd click, and only then", lambda r: len(r.reacts) >= 4 and [r.did(i, "cheer") for i in range(4)] == [False, False, True, False],
                "I clicked 4 times. Your pal should cheer on click 3, and not on the others. Try  if clicks() == 3:"),
               ("It jumps on the other clicks, with else", lambda r: r.elses >= 1 and len(r.reacts) >= 4 and all(r.did(i, "jump") for i in (0, 1, 3)), None),
               ("It says how many clicks, every time", lambda r: len(r.reacts) >= 4 and all(_click_said(r, i, i + 1) for i in range(4)), None)],
     "hints": ["clicks() is a number. Ask  if clicks() == 3:  then put  else:  under it, lined up with the if.",
               'def on_click():\n    say(clicks())\n    if clicks() == 3:\n        cheer()\n    else:\n        jump()'],
     "reference": 'def on_click():\n    say(clicks())\n    if clicks() == 3:\n        cheer()\n    else:\n        jump()'},

    # Keep Going: while loops, which go round as long as their question is yes.
    {"key": "c1", "chapter": 10, "name": "Walk to the edge", "adds": ["x"], "python": ["while"],
     "pip": "A while loop keeps going round as long as its question is yes. x() is the spot your pal is on. "
            "It starts on spot 2, and the edge of the stage is spot 10.",
     "job": "Walk right until you get to the edge, then say something.",
     "coach": [
               ('while x() < 10:', "x() is the spot your pal is on. While it's less than 10, keep going round!"),
               ('    right(1)', "One step right. After every step, the loop asks its question again."),
               ('say("The edge!")', "This line isn't pushed in, so it runs when the loop is done. I moved it back for you."),
     ],
     "goals": [("Your pal gets to the edge, spot 10", lambda r: 10 in _visited(r),
                lambda r: f"Your pal stopped on spot {r.x}. The edge is spot 10."),
               ("It uses a while loop", lambda r: r.whiles >= 1, None),
               ("It says something when it gets there", lambda r: r.x == 10 and bool(r.log) and r.log[-1][0] == "say", None)],
     "hints": ["Try  while x() < 10:  and push  right(1)  in under it.",
               'while x() < 10:\n    right(1)\nsay("The edge!")'],
     "reference": 'while x() < 10:\n    right(1)\nsay("The edge!")'},

    {"key": "c2", "chapter": 10, "name": "Countdown", "adds": [], "python": [],
     "pip": "A countdown! Each time round, n gets 1 smaller. When n gets to 0, the question  n > 0  is no, "
            "and the loop stops.",
     "job": "Count down from 5 to 1, then cheer.",
     "coach": [
               ('n = 5', "n is a variable. It starts at 5."),
               ('while n > 0:', "Keep going round while n is more than 0."),
               ('    say(n)', "Say the number."),
               ('    n = n - 1', "Make n one smaller. Without this line, the loop would never stop!"),
               ('cheer()', "Not pushed in: when the countdown is done, cheer! I moved it back for you."),
     ],
     "goals": [("Your pal counts down to 1, from 5 or more", lambda r: _countdown(r) >= 5,
                lambda r: f"Your pal said {', '.join(r.said[:6]) or 'nothing'}. I want 5, 4, 3, 2, 1."),
               ("It uses a while loop", lambda r: r.whiles >= 1, None),
               ("It cheers once, at the very end", lambda r: r.n("cheer") == 1 and r.log[-1][0] == "cheer", None)],
     "hints": ["Start with  n = 5  . Under  while n > 0:  say n, then make it smaller with  n = n - 1",
               'n = 5\nwhile n > 0:\n    say(n)\n    n = n - 1\ncheer()'],
     "reference": 'n = 5\nwhile n > 0:\n    say(n)\n    n = n - 1\ncheer()'},

    # My List: a list kept in a variable, gone through, added to, and looked into by position.
    {"key": "j1", "chapter": 11, "name": "Snack list", "adds": [], "python": ["list", "len"],
     "pip": "A list can have a name, like any variable. Then a for loop can visit each thing on it, "
            "and len() tells you how many things are on it.",
     "job": "Say yum for every snack on your list, then say how many snacks there are.",
     "coach": [
               ('snacks = ["cake", "apple", "pie"]', "A list called snacks, with 3 things in the [ ] brackets. Commas go between them."),
               ('for snack in snacks:', "Visit each snack on the list, one at a time. snack is the one we're on."),
               ('    say("Yum, " + snack)', "Pushed in, so it happens for every snack."),
               ('say(len(snacks))', "Not pushed in: once, after the loop. len() counts the list. I moved it back for you."),
     ],
     "goals": [("Your pal says yum for every snack on the list", lambda r: len(_the_list(r)) >= 2 and _says_each(r),
                'Try  for snack in snacks:  and push  say("Yum, " + snack)  in under it.'),
               ("It goes through the list with a for loop", lambda r: any(isinstance(r.values.get(name), list) for name in r.loops_over),
                "Give the list a name first, like  snacks = [...]  , then  for snack in snacks:"),
               ("It says how many snacks with len()", lambda r: r.calls["len"] >= 1 and bool(r.said) and r.said[-1] == str(len(_the_list(r))),
                "After the loop, not pushed in:  say(len(snacks))")],
     "hints": ["Make the list first:  snacks = [\"cake\", \"apple\", \"pie\"]  . Then  for snack in snacks:",
               'snacks = ["cake", "apple", "pie"]\nfor snack in snacks:\n    say("Yum, " + snack)\nsay(len(snacks))'],
     "reference": 'snacks = ["cake", "apple", "pie"]\nfor snack in snacks:\n    say("Yum, " + snack)\nsay(len(snacks))'},

    {"key": "j2", "chapter": 11, "name": "Who's coming?", "adds": [], "python": ["append"],
     "pip": "A list can grow! .append() adds one more thing to the end of a list. "
            "Start a party list with one friend, then add more.",
     "job": "Start a list with one friend, add 2 more with .append(), say hi to everyone, then wave.",
     "coach": [
               ('guests = ["Ana"]', "A list with one friend on it so far."),
               ('guests.append("Ben")', ".append() adds Ben to the end of the list."),
               ('guests.append("Cy")', "And Cy. Now the list is Ana, Ben, Cy."),
               ('for guest in guests:', "Visit everyone on the list."),
               ('    say("Hi " + guest)', "Say hi to each one."),
               ('wave()', "Not pushed in: one wave at the end. I moved it back for you."),
     ],
     "goals": [("You add to the list with .append()", lambda r: r.methods["append"] >= 1, 'Try  guests.append("Ben")  under the first line.'),
               ("Your pal says hi to everyone on the list, added ones too", lambda r: len(_the_list(r)) >= 3 and _says_each(r),
                lambda r: f"Your list ended up as {show_value(_the_list(r))}. Add 2 friends, then say hi to each one in a for loop."),
               ("It waves once, after all the hellos", lambda r: r.n("wave") == 1 and r.log[-1][0] == "wave", "Put  wave()  at the bottom, not pushed in.")],
     "hints": ['.append() goes after the list\'s name and a dot:  guests.append("Ben")',
               'guests = ["Ana"]\nguests.append("Ben")\nguests.append("Cy")\nfor guest in guests:\n    say("Hi " + guest)\nwave()'],
     "reference": 'guests = ["Ana"]\nguests.append("Ben")\nguests.append("Cy")\nfor guest in guests:\n    say("Hi " + guest)\nwave()'},

    {"key": "j3", "chapter": 11, "name": "First and last", "adds": [], "python": ["index"],
     "pip": "Every thing on a list has a position. The first is [0], not [1]! And [-1] is always the last one, "
            "however long the list is.",
     "job": "Feel the first mood on the list and say it. Then feel the last one and say it.",
     "coach": [
               ('moods = ["happy", "sad", "silly"]', "A list of 3 moods. Their positions are 0, 1 and 2."),
               ('feel(moods[0])', "moods[0] is the first one on the list: happy."),
               ('say("First: " + moods[0])', "Say it too."),
               ('feel(moods[-1])', "moods[-1] is the last one on the list: silly."),
               ('say("Last: " + moods[-1])', "And say that one."),
     ],
     "goals": [("Your pal feels the first mood on the list, with [0]", lambda r: 0 in r.positions and bool(_the_list(r)) and _feels(r)[:1] == _the_list(r)[:1],
                "Try  feel(moods[0])  . Position 0 is the first thing on a list."),
               ("Then the last mood, with [-1]", lambda r: -1 in r.positions and len(_the_list(r)) >= 2 and _feels(r)[-1:] == _the_list(r)[-1:],
                "Try  feel(moods[-1])  . -1 means the last thing, however long the list is."),
               ("It says the first and last moods out loud", lambda r: len(_the_list(r)) >= 2 and all(any(m in s for s in r.said) for m in (_the_list(r)[0], _the_list(r)[-1])), None)],
     "hints": ["moods[0] is the first mood, and moods[-1] is the last.",
               'moods = ["happy", "sad", "silly"]\nfeel(moods[0])\nsay("First: " + moods[0])\nfeel(moods[-1])\nsay("Last: " + moods[-1])'],
     "reference": 'moods = ["happy", "sad", "silly"]\nfeel(moods[0])\nsay("First: " + moods[0])\nfeel(moods[-1])\nsay("Last: " + moods[-1])'},

    # Keep Score: a number that changes as the show goes, choices with elif, and a def that takes a number.
    {"key": "s1", "chapter": 12, "name": "Rack up points", "adds": [], "python": ["change"],
     "pip": "A variable can change while the show runs. points += 2 means: add 2 to points. "
            "(score is already a word your pal knows, so call it points.)",
     "job": "Start at 0 points. Jump 5 times, get 2 points each jump, and say the points. Then cheer.",
     "coach": [
               ('points = 0', "points starts at 0."),
               ('for i in range(5):', "Go round 5 times."),
               ('    jump()', "Jump!"),
               ('    points += 2', "Add 2 to points. Now it's 2, then 4, then 6..."),
               ('    say(points)', "Say the points so far."),
               ('cheer()', "Not pushed in: cheer once at the end. I moved it back for you."),
     ],
     "goals": [("Your pal counts up its points: 2, 4, 6...", lambda r: _counts_up(r) >= 5,
                lambda r: f"Your pal said {', '.join(r.said[:6]) or 'nothing'}. The points should go up after every jump."),
               ("Points go up with +=", lambda r: r.adds >= 1, "Try  points += 2  inside the loop. It means: add 2 to points."),
               ("It cheers once, at the very end", lambda r: r.n("cheer") == 1 and r.log[-1][0] == "cheer", None)],
     "hints": ["points = 0  goes before the loop. Inside the loop:  points += 2  and then  say(points)",
               'points = 0\nfor i in range(5):\n    jump()\n    points += 2\n    say(points)\ncheer()'],
     "reference": 'points = 0\nfor i in range(5):\n    jump()\n    points += 2\n    say(points)\ncheer()'},

    {"key": "s2", "chapter": 12, "name": "Big, middle, small", "adds": [], "python": ["elif"], "seeds": range(30),
     "pip": "elif means: else, if. It asks a second question, only when the first answer was no. "
            "So your pal can do 3 different things!",
     "job": "Roll a dice and say it. Cheer on a 6, jump on a 4 or 5, and feel sad on 1, 2 or 3.",
     "coach": [
               ('roll = randint(1, 6)', "A dice roll from 1 to 6."),
               ('say(roll)', "Say what you rolled."),
               ('if roll == 6:', "First question: is it a 6?"),
               ('    cheer()', "Yes? Cheer!"),
               ('elif roll >= 4:', "If not a 6, next question: is it 4 or more? elif lines up with the if. I moved it back for you."),
               ('    jump()', "Yes? Jump."),
               ('else:', "Not 6, not 4 or 5. That leaves 1, 2 or 3."),
               ('    feel("sad")', "Aww."),
     ],
     "goals": [("It cheers on a 6, and only on a 6", lambda r: r.randoms >= 1 and all((o.n("cheer") > 0) == (_roll(o) == 6) for o in r.others),
                "Try  if roll == 6:  with  cheer()  pushed in under it."),
               ("It jumps on a 4 or 5, with elif", lambda r: r.elifs >= 1 and all((o.n("jump") > 0) == (_roll(o) in (4, 5)) for o in r.others),
                "Under the if, lined up with it:  elif roll >= 4:  and push  jump()  in under it."),
               ("It does something else on 1, 2 or 3, with else", lambda r: r.elses >= 1 and all(
                   _roll(o) > 3 or (o.n("cheer") == 0 and o.n("jump") == 0 and len(o.log) >= 2) for o in r.others), None)],
     "hints": ["if roll == 6:  then  elif roll >= 4:  then  else:  . All three line up, and the moves are pushed in under them.",
               'roll = randint(1, 6)\nsay(roll)\nif roll == 6:\n    cheer()\nelif roll >= 4:\n    jump()\nelse:\n    feel("sad")'],
     "reference": 'roll = randint(1, 6)\nsay(roll)\nif roll == 6:\n    cheer()\nelif roll >= 4:\n    jump()\nelse:\n    feel("sad")'},

    {"key": "s3", "chapter": 12, "name": "Hop how many?", "adds": [], "python": ["param"],
     "pip": "A def can take a number! In  def hop(n):  , n is whatever number you put in the ( ). "
            "So hop(2) hops 2 times, and hop(4) hops 4.",
     "job": "Make hop(n) jump n times and say how many. Then use it with 2, and with 4.",
     "coach": [
               ('def hop(n):', "A new command, hop. n is the number you give it."),
               ('    for i in range(n):', "Go round n times."),
               ('        jump()', "Jump!"),
               ('    say(f"{n} hops!")', "After the loop, still inside the def: say how many. I moved it back for you."),
               ('hop(2)', "Not pushed in: use it! n is 2 this time. I moved it back for you."),
               ('hop(4)', "And again, with 4."),
     ],
     "goals": [("You make a command with a number in its ( )", lambda r: r.params >= 1, "Try  def hop(n):  . n is a name for the number you give it."),
               ("You use it 2 times, with different numbers", lambda r: sum(r.own_calls.values()) >= 2 and len({c for c, _ in _hops(r)}) >= 2,
                "Under the def, not pushed in:  hop(2)  and then  hop(4)"),
               ("Your pal says how many hops after each one", lambda r: len(_hops(r)) >= 2 and all(c > 0 and str(t).split()[:1] == [str(c)] for c, t in _hops(r)),
                'Inside the def, after the loop:  say(f"{n} hops!")')],
     "hints": ["Inside the def, use n where the number goes:  for i in range(n):",
               'def hop(n):\n    for i in range(n):\n        jump()\n    say(f"{n} hops!")\nhop(2)\nhop(4)'],
     "reference": 'def hop(n):\n    for i in range(n):\n        jump()\n    say(f"{n} hops!")\nhop(2)\nhop(4)'},
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
    "m1": ("Make your pal change its face in its move, like  feel(\"silly\")  .", lambda r: r.n("feel") >= 1 and _actions(r) >= 3,
           'Add a  feel("...")  line anywhere in your move. The faces are happy, sad, surprised, angry, sleepy, silly, cool and calm.'),
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
    "r1": ('Add a 4th mood to the list, like  "sleepy"  .', lambda r: len(_moods(r)) >= 4,
           'Put a comma after "cool" and add another feeling in  " marks, inside the [ ]'),
    "r2": ("Make your pal jump when it rolls a 1, and still cheer on a 6.",
           lambda r: r.randoms >= 1 and any(o.n("jump") for o in r.others) and all((o.n("jump") > 0) == (o.said[:1] == ["1"]) and (o.n("cheer") > 0) == (o.said[:1] == ["6"]) for o in r.others),
           "Add another if at the bottom, not pushed in:  if roll == 1:  with  jump()  pushed in under it."),
    "r3": ("Make it a surprise from 5 to 10 jumps.", lambda r: all(5 <= o.n("jump") <= 10 for o in r.others) and len({o.n("jump") for o in r.others}) >= 2,
           "Change only the two numbers in  randint(2, 5)"),
    "k1": ("Make your pal do 3 things on every click.", lambda r: len(r.reacts) >= 3 and all(_click_moves(r, i) >= 3 for i in range(3)),
           "Add one more line under  def on_click():  , pushed in like the others. Try  spin()"),
    "c1": ("Then walk all the way back to spot 0, with a second while loop.", lambda r: r.whiles >= 2 and 10 in _visited(r) and r.x == 0,
           "Add  while x() > 0:  at the bottom, with  left(1)  pushed in under it."),
    "c2": ("Count down from 10 instead of 5.", lambda r: _countdown(r) >= 10, "Change only one thing: the 5 in the first line."),
    "j1": ("Add a 4th snack to the list. Change nothing else.", lambda r: len(_the_list(r)) >= 4 and _says_each(r) and r.said[-1] == str(len(_the_list(r))),
           "Inside the [ ] brackets, put a comma and one more snack in quotes."),
    "j2": ("Add yourself to the party with one more .append().", lambda r: r.methods["append"] >= 3 and len(_the_list(r)) >= 4 and _says_each(r),
           'Add  guests.append("...")  with your name, above the for line.'),
    "j3": ("Feel the middle mood too, in between, with [1].", lambda r: 1 in r.positions and len(_the_list(r)) >= 3
           and _feels(r)[:3] == [_the_list(r)[0], _the_list(r)[1], _the_list(r)[-1]],
           "Add  feel(moods[1])  just above the line with moods[-1]."),
    "s1": ("Make every jump worth 5 points instead of 2.", lambda r: _nums(r)[:2] == [5, 10], "Change only one thing: the number after +="),
    "s2": ("Add one more elif, so your pal spins on a 1.", lambda r: r.elifs >= 2 and all((o.n("spin") > 0) == (_roll(o) == 1) for o in r.others),
           "Add  elif roll == 1:  with  spin()  pushed in under it, just above the else."),
    "s3": ("Add a third hop with a bigger number, like hop(6).", lambda r: sum(r.own_calls.values()) >= 3 and max((c for c, _ in _hops(r)), default=0) >= 5,
           "Add one more line at the bottom, not pushed in, like  hop(6)"),
    "k2": ("Make your pal spin on the 3rd click, as well as cheer.", lambda r: len(r.reacts) >= 4 and [r.did(i, "spin") for i in range(4)] == [False, False, True, False],
           "Add  spin()  under  cheer()  , pushed in just as far."),
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
    "r1": ("Which face can your pal NOT make with this code?", ["Happy", "Silly", "Sad"], 2),
    "r2": ("What's the biggest number your pal can say?", ["5", "6", "7"], 1),
    "r3": ("What's the fewest jumps your pal can do?", ["0", "2", "5"], 1),
    "k1": ("Pip clicks your pal 3 times. How many times will it jump?", ["Never", "Once", "3 times"], 2),
    "k2": ("What does your pal do on the 2nd click?", ["Cheers", "Jumps", "Nothing"], 1),
    "c1": ("How many steps will your pal take?", ["2", "8", "10"], 1),
    "c2": ("What's the last number your pal says?", ["0", "1", "5"], 1),
    "j1": ("What's the last thing your pal says?", ["pie", "3", "Yum, cake"], 1),
    "j2": ("How many hellos will your pal say?", ["1", "2", "3"], 2),
    "j3": ("Which face will your pal have at the end?", ["Happy", "Sad", "Silly"], 2),
    "s1": ("What's the last number your pal says?", ["5", "10", "2"], 1),
    "s2": ("What does your pal do when it rolls a 5?", ["Cheers", "Jumps", "Feels sad"], 1),
    "s3": ("How many jumps in the whole show?", ["4", "6", "2"], 1),
}
# "Fix it": after a mission, Pip's code for it with one bug in it, to find and fix.
# (what went wrong, the code with the bug, check that it's fixed, a hint that says where to look).
# Half stop the show with a message, half run but do the wrong thing. test_pixel_fix.py
# checks every bug really breaks its check and the guide's code passes it.
# My Move has none: its code is the student's own.
FIXES = {
    "a1": ("Pip's show won't even start!", 'say("Hello)\nsay("I am so happy to be here")',
           lambda r: r.n("say") >= 2, 'Look at line 1. Words need a  "  at both ends.'),
    "a2": ("Pip wanted jump, talk, jump. The show stops before the last jump!", 'jump()\nsay("Wheee!")\njump',
           lambda r: r.first("jump", "say", "jump"), "Line 3 is missing something every command needs."),
    "a3": ("Pip's pal walks right past the spotlight!", 'right(6)\nsay("Here I am!")\nleft(6)',
           lambda r: 7 in _visited(r) and r.first("right", "say") and r.x == 2,
           "The pal starts on spot 2 and the light is on spot 7. Count the steps, then fix both numbers."),
    "h1": ("Pip's pal says hello, then the show stops!", 'say("Hello!")\nwav()\nwave()',
           lambda r: r.n("wave") >= 2 and r.first("say", "wave"), "Look closely at the spelling on line 2."),
    "h3": ("Pip's pal can't find its first feeling!", 'feel(sad)\nwait(1)\nfeel("surprised")\nwait(1)\nfeel("happy")',
           lambda r: _in_order(r, ("feel", ("sad",)), ("feel", ("happy",))), 'Feelings are words. Words need  "  marks at both ends.'),
    "h4": ("Pip's pal won't dance!", "Dance()\ncheer()\nhearts()",
           lambda r: r.first("dance", "cheer", "hearts"), "Python cares about capital letters. Commands start with a small letter."),
    "b1": ("Pip wanted 5 jumps, but the pal jumps only once!", "for i in range(1):\n    jump()",
           lambda r: r.n("jump") >= 5 and r.fors >= 1, "The number in  range( )  is how many times the loop goes round."),
    "b2": ("Pip wanted confetti once, at the end. It falls 4 times!", "for i in range(4):\n    right(1)\n    left(1)\n    confetti()",
           lambda r: r.n("right") >= 4 and r.n("confetti") == 1 and r.log[-1][0] == "confetti",
           "Lines pushed in are inside the loop. Should confetti be inside?"),
    "t1": ("Pip's pal should end up small again, but it stays big!", 'grow()\nshake()\ngrow()\nsay("Ta-da!")',
           lambda r: r.first("grow", "shake", "shrink", "say"), "Which line should make the pal small again?"),
    "t2": ("Pip's pal looks left, and then the show stops!", 'look("left")\nwait(1)\nlook("rigth")\nwait(1)\nlook("front")\nsay("Oh, hello!")',
           lambda r: _in_order(r, ("look", ("left",)), ("look", ("right",))) and ("look", ("front",)) in r.log,
           "Look closely at the spelling on line 3."),
    "l1": ("Pip's pal should count 1 to 5, but it starts at 0!", "for i in range(5):\n    say(i)\n    jump()",
           lambda r: all(str(n) in r.said for n in range(1, 6)) and "0" not in r.said,
           "i starts at 0. What can you add to i so it starts at 1?"),
    "l2": ('Pip\'s pal says "Hi AnaBen"! Ana and Ben got stuck together.', 'for name in ["Ana" "Ben", "Cy"]:\n    say("Hi " + name)\n    jump()',
           lambda r: len(set(r.said)) >= 3 and not any("AnaBen" in s for s in r.said),
           "Look at the list. Something goes between every name."),
    "v1": ("Pip's pal forgot its own name!", 'name = "Luna"\nsay("I am " + Name)\nsay(name.upper() + " IS HERE")',
           lambda r: r.said_var() >= 2, "Capital letters matter in names. Is it  name  or  Name  ?"),
    "v2": ('Pip changed jumps to 7. The pal says "7 jumps!" but only jumps 4 times!',
           'jumps = 7\nfor i in range(4):\n    jump()\ngrow()\nsay(f"{jumps} jumps!")',
           lambda r: r.range_name and any(s.split()[0] == str(r.n("jump")) for s in r.said if s.split()), "range(4) always goes round 4 times. Put the variable's name in the brackets instead."),
    "w1": ("Pip made a move called boogie, but the show stops when it's time to use it!",
           "def boogie():\n    jump()\n    spin()\n    jump()\nboogie\nboogie",
           lambda r: sum(r.own_calls.values()) >= 2, "To use a command, it needs  ( )  after its name."),
    "r1": ("Pip's surprise won't even start!", 'mood = choice("happy", "silly", "cool")\nfeel(mood)\nsay("I feel " + mood)',
           lambda r: r.randoms >= 1 and len(_moods(r)) >= 2, "choice() needs a list, and a list goes in  [ ]  brackets."),
    "r2": ("Pip's pal cheers when it rolls a 1, not a 6!", "roll = randint(1, 6)\nsay(roll)\nif roll == 1:\n    cheer()",
           lambda r: r.randoms >= 1 and any(o.n("cheer") for o in r.others)
           and all((o.n("cheer") > 0) == (o.said[:1] == ["6"]) for o in r.others), "Look at the number in the if line."),
    "r3": ("Pip's pal says how many after every single jump!", 'jumps = randint(2, 5)\nfor i in range(jumps):\n    jump()\n    say(f"{jumps} lucky jumps!")',
           lambda r: all(o.n("say") == 1 and o.log[-1][0] == "say" for o in r.others), "Lines pushed in are inside the loop. Should the say line be inside?"),
    "w2": ("Pip's count stops at 1!", "for i in range(1, 6):\n    say(i)\n    if i = 3:\n        jump()",
           lambda r: r.n("jump") == 1 and _after_three(r), "To ask if two things are the same, Python uses  ==  , two equals signs."),
    "c1": ("Pip's pal walks the wrong way, and the show never ends!", 'while x() < 10:\n    left(1)\nsay("The edge!")',
           lambda r: 10 in _visited(r) and r.log[-1][0] == "say", "Which way is the edge? Look at the line inside the loop."),
    "c2": ("Pip's countdown says 5 again and again and never stops!", 'n = 5\nwhile n > 0:\n    say(n)\nn = n - 1\ncheer()',
           lambda r: _countdown(r) >= 5 and r.n("cheer") == 1, "The line that makes n smaller has to go round with the loop. Is it pushed in?"),
    "k1": ("Pip's pal giggles once at the very start, and never when it's clicked!", 'def on_click():\n    jump()\nsay("Hee hee!")',
           lambda r: len(r.reacts) >= 3 and all(r.did(i, "jump") and r.did(i, "say") for i in range(3)),
           "Only lines pushed in under  def on_click():  wait for a click. Is the say line pushed in?"),
    "k2": ("Pip's show won't even start! Something is wrong near the end.", 'def on_click():\n    say(clicks())\n    if clicks() == 3:\n        cheer()\n    else:\n    jump()',
           lambda r: len(r.reacts) >= 4 and all(r.did(i, "jump") for i in (0, 1, 3)), "Look at the last line. What's under  else:  has to be pushed in."),
    "j1": ("Pip's pal says yum only 2 times, and two snacks are squashed together!", 'snacks = ["cake" "apple", "pie"]\nfor snack in snacks:\n    say("Yum, " + snack)\nsay(len(snacks))',
           lambda r: len(_the_list(r)) >= 3 and _says_each(r), "Look at the list on line 1. Every snack needs a comma after it, except the last."),
    "j2": ("Pip's pal only says hi to Cy!", 'guests = ["Ana"]\nguests.append("Ben")\nguests = ["Cy"]\nfor guest in guests:\n    say("Hi " + guest)\nwave()',
           lambda r: len(_the_list(r)) >= 3 and _says_each(r), "Line 3 makes a brand new list with only Cy on it. Use  .append()  to add to the list instead."),
    "j3": ("Pip's show stops with a message about position 3!", 'moods = ["happy", "sad", "silly"]\nfeel(moods[0])\nsay("First: " + moods[0])\nfeel(moods[3])\nsay("Last: " + moods[-1])',
           lambda r: len(_the_list(r)) >= 2 and _feels(r)[-1:] == _the_list(r)[-1:], "Positions start at 0, so 3 moods are at 0, 1 and 2. Use [-1] for the last one."),
    "s1": ("Pip's pal says 2 every time. The points never add up!", 'for i in range(5):\n    points = 0\n    jump()\n    points += 2\n    say(points)\ncheer()',
           lambda r: _counts_up(r) >= 5, "Where is  points = 0  ? Inside the loop, points starts again from 0 every time round."),
    "s2": ("Pip's pal cheers on a 6, and then jumps too!", 'roll = randint(1, 6)\nsay(roll)\nif roll == 6:\n    cheer()\nif roll >= 4:\n    jump()\nelse:\n    feel("sad")',
           lambda r: r.elifs >= 1 and all((o.n("jump") > 0) == (_roll(o) in (4, 5)) for o in r.others),
           "The second if asks its question even after a 6. Make it  elif  , so it only asks when the first answer was no."),
    "s3": ("Pip's show stops: hop has no number!", 'def hop(n):\n    for i in range(n):\n        jump()\n    say(f"{n} hops!")\nhop(2)\nhop()',
           lambda r: sum(r.own_calls.values()) >= 2 and len({c for c, _ in _hops(r)}) >= 2, "Look at the last line. hop needs a number in its ( ), like  hop(4)"),
}
for _lv in LEVELS:
    _lv["remix"] = REMIXES[_lv["key"]]
    _lv["guess"] = GUESSES.get(_lv["key"])
    _lv["fix"] = FIXES.get(_lv["key"])

# 🎬 Free stage: after My Move, a stage with no stars and no rules, where a student makes any
# show they like with every command they've learned, plus stage toys no mission teaches.
FREE_AFTER = "m1"
SCENE_STARS = {"wedding": 20, "snowy": 30, "candy": 40, "space": 50, "castle": 60}     # places that open with stars


def free_setup(stars):
    """The Free stage knows how many stars a student has, so scene() can open places with them."""
    def setup(show):
        show.stars = stars
    return setup
STAGE_TOYS = ("scene", "sound", "rain", "snow", "friend", "friend_say", "friend_jump", "bye", "hide", "appear")
FREE = {"key": "free", "name": "Free stage", "chapter": None,
        "pip": "The stage is all yours! No stars and no rules: make any show you'd like to watch. "
               "Try the new stage toys, like  scene(\"beach\")  and  friend(\"cat\")  . All words says what each one does.",
        "job": "Make any show you like.", "goals": [], "hints": [], "coach": [], "adds": list(STAGE_TOYS)}

# 💡 Give me an idea: small shows to start from, made only of what a student has at My Move.
FREE_IDEAS = [
    ("A day at the beach", 'scene("beach")\nsay("Time to swim!")\nfor i in range(3):\n    jump()\nsound("yay")\nfeel("happy")'),
    ("A friend comes to play", 'friend("cat")\nfriend_say("Can I play?")\nsay("Yes! Let\'s dance!")\ndance()\nfriend_jump()\nhearts()'),
    ("A magic trick", 'say("Watch this!")\nsound("drum")\nhide()\nwait(1)\nappear()\nsound("tada")\nconfetti()'),
    ("Snow day", 'scene("park")\nsnow()\nsay("Brrr! It\'s cold!")\nfeel("surprised")\nfor i in range(2):\n    spin()\ndance()'),
    ("A starry night", 'scene("night")\nsay("Look at the stars!")\nfor i in range(3):\n    jump()\nstars()\nfeel("happy")'),
    ("Walk with the arrow keys", 'say("Press the arrow keys!")\ndef on_key(key):\n    if key == "left":\n        left(1)\n    if key == "right":\n        right(1)\n    if key == "space":\n        jump()'),
    ("A rainy day", 'scene("park")\nrain()\nfeel("sad")\nsay("Oh no, rain!")\nwait(1)\nfeel("happy")\nsay("I love puddles!")\ndance()'),
]


def free_commands(upto):
    """What works on the Free stage: every command learned up to this mission, and the stage toys."""
    return tuple(dict.fromkeys(commands_for(upto) + STAGE_TOYS))


LEVEL_ORDER = [lv["key"] for lv in LEVELS]
LEVEL_BY_KEY = {lv["key"]: lv for lv in LEVELS}
REMIX_COINS = 15           # once per mission, for doing its Your turn
GUESS_COINS = 5            # for a right first guess on a mission
FIX_COINS = 15             # once per mission, for fixing Pip's bug


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


def _moods(r):
    """Every feeling a run picked, over all the runs."""
    return {args[0] for o in r.others for name, args in o.log if name == "feel" and args}


def _click_moves(r, i):
    """How many things the pal did after click number i (0 is the first)."""
    return sum(1 for name, _ in r.reacts[i] if name in MOVE_ACTIONS) if i < len(r.reacts) else 0


def _click_name_slip(r):
    """A def that's nearly on_click (onclick, On_click, on_clicked) gets named."""
    near = [d for d in r.defs if d.lower().replace("_", "") in ("onclick", "onclicked", "onclicks", "clicked", "click")]
    return f"Nothing happens when I click your pal. Did you mean  def on_click():  instead of  def {near[0]}():  ? It has to be spelled just like that." if near else None


def _countdown(r):
    """The number a countdown to 1 started from, at the end of what the pal said, or 0."""
    nums = [int(s) for s in r.said if s.lstrip("-").isdigit()]
    if not nums or nums[-1] != 1:
        return 0
    i = len(nums) - 1
    while i > 0 and nums[i - 1] == nums[i] + 1:
        i -= 1
    return nums[i]


def _click_said(r, i, words):
    return i < len(r.reacts) and any(name == "say" and args and str(args[0]) == str(words) for name, args in r.reacts[i])


def _the_list(r):
    """The longest list the program kept in a variable, or []."""
    lists = [v for v in r.values.values() if isinstance(v, list)]
    return max(lists, key=len) if lists else []


def _says_each(r):
    """True if the pal said every thing on the list (inside its words)."""
    items = _the_list(r)
    return bool(items) and all(any(str(x) in s for s in r.said) for x in items)


def _feels(r):
    return [args[0] for name, args in r.log if name == "feel" and args]


def _nums(r):
    return [int(s) for s in r.said if s.lstrip("-").isdigit()]


def _counts_up(r):
    """How many numbers the pal said, if they go up by the same step each time, or 0."""
    nums = _nums(r)
    steps = {b - a for a, b in zip(nums, nums[1:])}
    return len(nums) if len(nums) >= 2 and len(steps) == 1 and steps.pop() > 0 else 0


def _roll(o):
    """The dice number a run said first, or 0."""
    return int(o.said[0]) if o.said and o.said[0].isdigit() else 0


def _hops(r):
    """(jumps since the last say, what was said) for every say."""
    out, jumps = [], 0
    for name, args in r.log:
        if name == "jump":
            jumps += 1
        elif name == "say":
            out.append((jumps, args[0] if args else ""))
            jumps = 0
    return out


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
    "propeller": {"name": "Propeller cap", "slot": "hat"}, "bubblespark": {"name": "Bubble sparkles", "slot": "sparkle"},
    "beret": {"name": "Beret", "slot": "hat"}, "pixelshades": {"name": "Pixel shades", "slot": "face"},
    "gradcap": {"name": "Graduation cap", "slot": "hat"}, "viking": {"name": "Viking helmet", "slot": "hat"},
    "sprout": {"name": "Little sprout", "slot": "hat"}, "freckles": {"name": "Freckles", "slot": "face"},
    "codespark": {"name": "Code sparkles", "slot": "sparkle"}, "petalspark": {"name": "Petal sparkles", "slot": "sparkle"},
    # These unlock by themselves when a goal is reached: [what is counted, how many].
    "gemcrown": {"name": "Gem crown", "slot": "hat", "goal": ["gems", 9]},
    "fishhat": {"name": "Fish hat", "slot": "hat", "goal": ["fish", 5]},
    "friendspark": {"name": "Friendship sparkles", "slot": "sparkle", "goal": ["friends", 5]},
    "goldshades": {"name": "Gold shades", "slot": "face", "goal": ["rounds", 10]},
    "dragon": {"name": "Dragon horns", "slot": "hat", "goal": ["stars", 15]},
    "astro": {"name": "Space helmet", "slot": "hat", "goal": ["gems", 21]},
    "superspark": {"name": "Superstar sparkles", "slot": "sparkle", "goal": ["stars", 27]},
    "chestspark": {"name": "Treasure sparkles", "slot": "sparkle", "goal": ["chests", 5]},
    "captain": {"name": "Captain hat", "slot": "hat", "goal": ["chests", 20]},
    # ✨ Fancy: the big things to save up for. 100 coins or more puts them on the shop's Fancy shelf.
    "sunhat": {"name": "Sun hat", "slot": "hat", "price": 100}, "musicspark": {"name": "Music sparkles", "slot": "sparkle", "price": 120},
    "princess": {"name": "Princess hat", "slot": "hat", "price": 120}, "starmask": {"name": "Sparkly mask", "slot": "face", "price": 110},
    "butterflyspark": {"name": "Butterfly sparkles", "slot": "sparkle", "price": 130},
    "diamondtiara": {"name": "Diamond tiara", "slot": "hat", "price": 150}, "royalcrown": {"name": "Royal crown", "slot": "hat", "price": 200},
    # ❄️ Winter: two in the shop, and three goals in the Snow Village.
    "bobble": {"name": "Bobble hat", "slot": "hat", "price": 45}, "earmuffs": {"name": "Fluffy earmuffs", "slot": "hat", "price": 50},
    "santa": {"name": "Santa hat", "slot": "hat", "goal": ["presents", 5]},
    "antlers": {"name": "Reindeer antlers", "slot": "hat", "goal": ["snowballs", 25]},
    "snowspark": {"name": "Snowflake sparkles", "slot": "sparkle", "goal": ["presents", 15]},
}
FANCY_PRICE = 100          # wearables this dear go on the shop's ✨ Fancy shelf

# ✏️ Wear your own drawing: a copy of one of your drawings, worn as a hat or on the face.
# It's a copy, so changing or deleting the drawing later leaves it as it was.
MY_WEAR_PRICE = 40
MY_WEAR_MAX = 6
MY_WEAR_SLOTS = ("hat", "face")


def wear_cut(drawing):
    """The first frame of a drawing, cut down to the squares that are drawn."""
    size, frame = drawing["size"], drawing["frames"][0]
    rows = [frame[i * size:(i + 1) * size] for i in range(size)]
    ys = [y for y, row in enumerate(rows) if set(row) != {"."}]
    if not ys:
        return None
    xs = [x for x in range(size) if any(row[x] != "." for row in rows)]
    return {"size": size, "palette": drawing["palette"], "rows": [row[xs[0]:xs[-1] + 1] for row in rows[ys[0]:ys[-1] + 1]]}
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

# Things for a home. A price of 0 is there from the start, unless it's a "prize" (the
# home level that wins it). A thing with a price can be bought again and again, and each
# copy goes out on its own. "toy" is what happens when someone clicks it (pixel_stage.js
# TOY_FX).
FURNITURE = {
    "rug": {"name": "Round rug", "price": 0}, "plant": {"name": "Pot plant", "price": 0},
    "balloons": {"name": "Balloons", "price": 15, "toy": "pop"}, "cupcakes": {"name": "Cupcakes", "price": 15, "toy": "snack"},
    "duck": {"name": "Rubber duck", "price": 15, "toy": "quack"}, "lamp": {"name": "Lamp", "price": 20, "toy": "glow"},
    "teddy": {"name": "Teddy", "price": 20, "toy": "hug"}, "flowers": {"name": "Flower bed", "price": 20, "toy": "petals"},
    "table": {"name": "Table", "price": 25, "toy": "snack"}, "beanbag": {"name": "Bean bag", "price": 25, "toy": "bounce"},
    "toybox": {"name": "Toy box", "price": 30, "toy": "bounce"}, "tree": {"name": "Little tree", "price": 30, "toy": "apples"},
    "shelf": {"name": "Bookshelf", "price": 35, "toy": "book"}, "fridge": {"name": "Fridge", "price": 35, "toy": "snack"},
    "stove": {"name": "Stove", "price": 35, "toy": "cook"}, "wardrobe": {"name": "Wardrobe", "price": 35, "toy": "dressup"},
    "bed": {"name": "Bed", "price": 40, "toy": "zzz"}, "sofa": {"name": "Sofa", "price": 40, "toy": "bounce"},
    "tv": {"name": "TV", "price": 45, "toy": "tv"}, "swing": {"name": "Swing", "price": 45, "toy": "wheee"},
    "chest": {"name": "Treasure chest", "price": 45, "toy": "treasure"}, "tank": {"name": "Fish tank", "price": 50, "toy": "blub"},
    "drums": {"name": "Drum kit", "price": 50, "toy": "drums"}, "telescope": {"name": "Telescope", "price": 50, "toy": "stars"},
    "trampoline": {"name": "Trampoline", "price": 50, "toy": "bounce"}, "bunkbed": {"name": "Bunk bed", "price": 55, "toy": "zzz"},
    "piano": {"name": "Piano", "price": 55, "toy": "notes"}, "disco": {"name": "Disco ball", "price": 60, "toy": "party"},
    "fountain": {"name": "Fountain", "price": 60, "toy": "splash"}, "slide": {"name": "Slide", "price": 65, "toy": "wheee"},
    "arcade": {"name": "Arcade game", "price": 70, "toy": "arcade"}, "rocketbed": {"name": "Rocket bed", "price": 75, "toy": "zzz"},
    "robot": {"name": "Robot buddy", "price": 80, "toy": "beep"}, "dragonegg": {"name": "Dragon egg", "price": 100, "toy": "magic"},
    "trophy": {"name": "Gold trophy", "price": 0, "prize": 1, "toy": "cheer"},
    "rainbowarch": {"name": "Rainbow", "price": 0, "prize": 3, "toy": "stars"},
    "throne": {"name": "Golden throne", "price": 0, "prize": 4, "toy": "cheer"},
    "unicornpal": {"name": "Unicorn", "price": 0, "prize": 6, "toy": "magic"},
}
# A "room" wall or floor comes with that room and can't be bought on its own.
HOME_WALLS = {"w_cream": {"name": "Cream walls", "price": 0}, "w_pink": {"name": "Pink walls", "price": 30},
              "w_blue": {"name": "Blue walls", "price": 30}, "w_mint": {"name": "Mint walls", "price": 30},
              "w_sky": {"name": "Sky walls", "price": 35}, "w_sea": {"name": "Sea walls", "price": 35},
              "w_candy": {"name": "Candy stripes", "price": 40}, "w_night": {"name": "Starry walls", "price": 40},
              "w_attic": {"name": "Wood walls", "price": 0, "room": "r_attic"},
              "w_castle": {"name": "Castle walls", "price": 0, "room": "r_secret"}}
HOME_FLOORS = {"f_wood": {"name": "Wood floor", "price": 0}, "f_check": {"name": "Checked floor", "price": 30},
               "f_grass": {"name": "Grass floor", "price": 30}, "f_carpet": {"name": "Purple carpet", "price": 30},
               "f_tile": {"name": "Blue tiles", "price": 30}, "f_sand": {"name": "Sand floor", "price": 35},
               "f_cloud": {"name": "Cloud floor", "price": 40}, "f_rainbow": {"name": "Rainbow floor", "price": 0, "prize": 2},
               "f_gold": {"name": "Gold floor", "price": 0, "prize": 5}}
# More rooms, bought in the shop. They join on in a row in the order they're bought, and
# a pal walks from one to the next through an open doorway. Each kind comes with its own
# walls and floor (the owner gets those to use anywhere) and something built in.
HOME_ROOMS = {"r_bed": {"name": "Bedroom", "icon": "🛏️", "price": 50, "wall": "w_blue", "floor": "f_carpet"},
              "r_kitchen": {"name": "Kitchen", "icon": "🍳", "price": 60, "wall": "w_mint", "floor": "f_check"},
              "r_play": {"name": "Playroom", "icon": "🧸", "price": 70, "wall": "w_candy", "floor": "f_carpet"},
              "r_garden": {"name": "Garden", "icon": "🌻", "price": 80, "wall": "w_sky", "floor": "f_grass"},
              "r_attic": {"name": "Attic", "icon": "🕯️", "price": 90, "wall": "w_attic", "floor": "f_wood"},
              "r_games": {"name": "Game room", "icon": "🕹️", "price": 110, "wall": "w_night", "floor": "f_carpet"},
              "r_pool": {"name": "Pool room", "icon": "🏊", "price": 140, "wall": "w_sea", "floor": "f_tile"},
              "r_secret": {"name": "Secret room", "icon": "🗝️", "price": 180, "wall": "w_castle", "floor": "f_sand"}}
HOME_FIRST = "Living room"
# A home grows up as it fills: a point for each thing out (two for a drawing with code),
# ROOM_POINTS for each room built, and one for each heart from a visitor. Each level
# after the first wins a prize that can't be bought.
HOME_LEVELS = (("Tiny hut", 0), ("Cozy cottage", 4), ("Happy house", 9), ("Big house", 15),
               ("Super house", 22), ("Mansion", 30), ("Dream castle", 40))
ROOM_POINTS = 3
HEART_POINTS_MAX = 10      # hearts count up to this many points
COINS_HEART = 2            # the owner's, when a visitor gives their home a heart
# Everything with a price, and which shelf of the shop it's on.
SHOP = dict({key: dict(gift, kind="wear") for key, gift in GIFTS.items() if gift.get("price")},
            **{key: dict(item, kind="furniture") for key, item in FURNITURE.items() if item["price"]},
            **{key: dict(item, kind="wall") for key, item in HOME_WALLS.items() if item["price"]},
            **{key: dict(item, kind="floor") for key, item in HOME_FLOORS.items() if item["price"]},
            **{key: dict(item, kind="room") for key, item in HOME_ROOMS.items()})
HOME_TOYS = frozenset(item["toy"] for item in FURNITURE.values() if "toy" in item)
HOME_ART = 5               # drawings a student can hang up in each room
HOME_ITEMS = 12            # pieces of furniture in each room


def home_free(item):
    """Whether everyone has this thing for a home from the start."""
    return not item["price"] and not item.get("prize") and not item.get("room")


def home_level(points):
    """Which of HOME_LEVELS a home with this many points is."""
    return max(i for i, (_, need) in enumerate(HOME_LEVELS) if points >= need)


def home_prizes(level):
    """The keys of everything a home at this level has won."""
    return [key for key, item in {**FURNITURE, **HOME_WALLS, **HOME_FLOORS}.items() if 0 < item.get("prize", 0) <= level]

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


RACE_WORDS = {"say": "say", "jump": "jump", "wave": "wave", "spin": "spin", "dance": "dance", "cheer": "cheer",
              "hearts": "hearts", "stars": "stars", "confetti": "confetti"}


def race_words(names):
    """Moves in words and pictures, with repeats counted: 🦘 jump 3 times, then 🌀 spin."""
    for size in range(2, len(names) // 2 + 1):      # a pattern done again and again
        times = len(names) // size
        if len(names) % size == 0 and list(names) == list(names[:size]) * times and len(set(names[:size])) > 1:
            return f"{race_words(names[:size])}. Do that {times} times"
    runs = []
    for name in names:
        if runs and runs[-1][0] == name:
            runs[-1][1] += 1
        else:
            runs.append([name, 1])
    shown = [f"{RACE_ICONS.get(n, '❓')} {RACE_WORDS.get(n, n)}" + (f" {k} times" if k > 1 else "") for n, k in runs[:8]]
    return ", then ".join(shown) + (" ..." if len(runs) > 8 else "")


def race_miss(did, want, wants, looped=False):
    """What a student's pal did against what's wanted, and the one thing to change."""
    if did == want[:len(did)]:
        missing = len(want) - len(did)
        nxt = want[len(did)]
        tip = (f"Good start! {missing} more to go. Next is {RACE_ICONS.get(nxt, '')} {nxt}()."
               if missing > 1 else f"So close! Just one more: {RACE_ICONS.get(nxt, '')} {nxt}().")
    elif did[:len(want)] == want:
        extra = len(did) - len(want)
        tip = (f"That's {extra} too many! Make the number in the loop smaller." if looped
               else f"That's {extra} too many! Take away {'a line' if extra == 1 else f'{extra} lines'}.")
    else:
        i = next(i for i, (a, b) in enumerate(zip(did, want)) if a != b) if any(a != b for a, b in zip(did, want)) else min(len(did), len(want))
        tip = f"Move {i + 1} should be {RACE_ICONS.get(want[i], '')} {want[i]}, but your pal did {RACE_ICONS.get(did[i], '')} {did[i]}."
    return f"Your pal did: {race_words(did)}.\n{wants}: {race_words(want)}.\n{tip}"


def race_check(job, code, wants="The job wants"):
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
        message = race_miss(did, want, wants, r.fors + r.whiles > 0)
    elif job.get("said") and [_plain(s) for s in r.said] != [_plain(s) for s in job["said"]]:
        message = ("Your pal said " + ", ".join(f'"{s}"' for s in r.said) + f". {wants} "
                   + ", ".join(f'"{s}"' for s in job["said"]) + ".")
    elif r.fors + r.whiles < job.get("loops", 0):
        message = ("That's the right moves! Now use a loop: tap 🔁 for." if job["loops"] == 1
                   else f"That's the right moves! Now use {job['loops']} loops, one for each move.")
    else:
        return {"ok": True, "message": "⭐ You solved it! Watch your pal.", "steps": compile_move(out["steps"])}
    return {"ok": False, "message": message, "line": None}


# ---- Code chests: one in each place of the Hang out, and code opens it ---------------
# A chest's puzzle is a Code race job. It changes every day, the same for the whole class
# so friends can help each other, and gets harder further along the world. Each student
# opens each chest once a day.
CHEST_SPOTS = {"park": (240, .6), "wedding": (90, .55), "beach": (282, .45), "night": (92, .5),
               "snowy": (240, .75), "candy": (252, .55), "space": (62, .45)}     # x in the place, and how deep
CHEST_TIER = {"park": 0, "wedding": 1, "beach": 1, "night": 2, "snowy": 2, "candy": 3, "space": 3}
CHEST_JOBS = RACE_JOBS + ((
    {"job": "Count 1 to 5 with say(). Use a loop!", "want": ["say"] * 5, "said": ["1", "2", "3", "4", "5"], "loops": 1,
     "chips": ["say(i + 1)"], "answer": "for i in range(5):\n    say(i + 1)"},
    {"job": "Count down 3, 2, 1 with a loop. Then cheer!", "want": ["say"] * 3 + ["cheer"], "said": ["3", "2", "1"], "loops": 1,
     "chips": ["say(3 - i)"], "answer": "for i in range(3):\n    say(3 - i)\ncheer()"},
    {"job": "Jump, spin and wave. Do that 3 times with a loop!", "want": ["jump", "spin", "wave"] * 3, "loops": 1,
     "answer": "for i in range(3):\n    jump()\n    spin()\n    wave()"},
    {"job": "Spin 2 times, then make hearts 3 times. Use 2 loops!", "want": ["spin"] * 2 + ["hearts"] * 3, "loops": 2,
     "answer": "for i in range(2):\n    spin()\nfor i in range(3):\n    hearts()"}),)
CHEST_COINS = 10           # coding coins, so no daily limit


def chest_chips(job):
    """The green buttons at a chest: only the moves its puzzle needs, so nothing else gets in the way."""
    chips = list(job.get("chips", []))
    for name in dict.fromkeys(job["want"]):
        if name == "say":
            chips += [] if any(c.startswith("say(") for c in chips) else [f'say("{w}")' for w in dict.fromkeys(job.get("said", ["Hello!"]))]
        else:
            chips.append(f"{name}()")
    return chips


def chest_job(place, day):
    """Today's puzzle for the chest in this place."""
    return random.Random(f"chest {day} {place}").choice(CHEST_JOBS[CHEST_TIER[place]])


def party_goal(level):
    return min(10 + 5 * level, 30)


# ---- 🎨 Draw & guess: one pal draws a secret word on a little grid, the others tap the picture ----
# The guesses are pictures with words, so nobody has to type or spell.
GUESS_WORDS = (("cat", "🐱", "Cat"), ("dog", "🐶", "Dog"), ("fish", "🐟", "Fish"), ("star", "⭐", "Star"), ("heart", "❤️", "Heart"),
               ("house", "🏠", "House"), ("tree", "🌳", "Tree"), ("flower", "🌸", "Flower"), ("apple", "🍎", "Apple"),
               ("rainbow", "🌈", "Rainbow"), ("sun", "☀️", "Sun"), ("moon", "🌙", "Moon"), ("ghost", "👻", "Ghost"),
               ("snowman", "⛄", "Snowman"), ("cake", "🎂", "Cake"), ("car", "🚗", "Car"), ("boat", "⛵", "Boat"),
               ("bunny", "🐰", "Bunny"), ("icecream", "🍦", "Ice cream"), ("balloon", "🎈", "Balloon"), ("pizza", "🍕", "Pizza"),
               ("crown", "👑", "Crown"), ("butterfly", "🦋", "Butterfly"), ("mushroom", "🍄", "Mushroom"), ("frog", "🐸", "Frog"),
               ("present", "🎁", "Present"), ("snake", "🐍", "Snake"), ("banana", "🍌", "Banana"), ("gem", "💎", "Gem"),
               ("robot", "🤖", "Robot"), ("rocket", "🚀", "Rocket"), ("umbrella", "☂️", "Umbrella"))
GUESS_BY_KEY = {w[0]: w for w in GUESS_WORDS}
DRAW_GRID = 12             # squares across and down
DRAW_COLOURS = ("#1b1530", "#e8294f", "#ff9a3c", "#ffd93b", "#35b55a", "#2f6fe4", "#a05ce8", "#ff8fc7", "#8a5a33", "#ffffff")
DRAW_CHOICES = 6           # pictures to pick from, the right one among them


# ---- ❄️ Winter: the Snow Village ------------------------------------------------------
# From WINTER_FROM to WINTER_TO each year the world gets one more place at its far end. It's
# never in HANG_WORLD, so gems, chests and goals that need every place don't wait on it.
# In it: a class tree to hang a drawing on, a snowman the class rolls together, and every day
# five presents to find, one in each of PRESENT_PLACES, the same spots for everyone.
WINTER_FROM, WINTER_TO = (11, 16), (12, 31)     # (month, day), both days included
VILLAGE = "village"
TREE_X = 92                # where the class tree stands in the village
TREE_MAX = 40              # ornaments: one for each student, the oldest going first
SNOWMAN_X, SNOWMAN_DEEP = 238, .2
SNOWMAN_BALLS = 30         # snowballs the class rolls to finish a snowman
SNOWMAN_REACH = 46         # how close a pal has to be to roll one
SNOWBALL_GAP = 1           # seconds between one student's snowballs
SNOWMAN_POINTS = 2         # a finished snowman fills the party meter this much
SNOWMAN_POINTS_DAY = 3     # for the first few snowmen each day
PRESENT_PLACES = HANG_PLACES + (VILLAGE,)
COINS_PRESENT = 2


def winter_on(month, day):
    return WINTER_FROM <= (month, day) <= WINTER_TO


def presents_on(day):
    """Today's presents: one in each place, somewhere new every day."""
    rng = random.Random(f"presents {day}")
    spots = []
    for place in PRESENT_PLACES:
        x = rng.randint(24, 296)
        while place == VILLAGE and (abs(x - TREE_X) < 40 or abs(x - SNOWMAN_X) < 34):     # not under the tree or the snowman
            x = rng.randint(24, 296)
        spots.append({"place": place, "x": x, "deep": round(rng.uniform(.3, .95), 2)})
    return spots


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


def run_level(lv, code, pal, seed=0, surprise=None):
    """Run a mission. Random missions run on many seeds, so the stars mean the
    program works every time. The first run is the one the student watches:
    with `surprise`, a random mission's watched run gets that seed of its own."""
    commands = lv.get("commands") or commands_for(lv["key"])
    seeds = list(lv.get("seeds", [0]))
    if surprise is not None and "seeds" in lv:
        seeds = [surprise - seed] + seeds
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
    quoted = re.search(r"""==\s*(["'])(\d+)\1""", code)
    if reply and quoted:             # if i == "3": runs, but a word is never the same as a number
        reply = (f"Your code asks if something is the same as {quoted[1]}{quoted[2]}{quoted[1]} with quotes, which is a word, "
                 f"not a number. Take the quotes off:  == {quoted[2]}")
    out = public(main)
    if not main["error"] and good is False:
        bad = next(r for r in runs if r["error"])
        out["error"], out["line"] = bad["error"], bad["line"]
    remix = lv.get("remix")
    out["remix"] = bool(good and remix and remix[1](report))
    fix = lv.get("fix")
    out["fix"] = bool(good and fix and fix[2](report))
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


POKES = ("click",) + tuple(f"key:{k}" for k in KEYS)


def poke(code, pal, events, commands, seed=0, setup=None):
    """A student clicks their pal, or presses an arrow key or space, after a show. The
    program runs again with every click and key so far, so clicks() counts up and
    variables carry on, and only what the newest one makes comes back."""
    events = [e for e in events if e in POKES][-MAX_EVENTS:]
    if not events:
        return {"steps": [], "error": None, "line": None, "listening": False}
    out = perform(code, pal, events, seed, commands, setup)
    if not out["error"] and events[-1].partition(":")[0] not in out["events"]:
        return {"steps": [], "error": None, "line": None, "listening": False}
    return {"steps": [] if out["error"] else [s for s in out["after"] if s["do"] != "event"],
            "error": out["error"], "line": out["line"], "listening": True}


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
