"""
Strange Planet: drive a rover across an alien planet with Python.

Every zone has ONE hidden physics rule that nobody explains. Students find it
by running code, watching the replay and reading the log, then write a
program that works with it. Each zone has three sites:

    A  Notice      a field measurement: the rule shows up, and the mission is
                   to find its number and report() it (Crumbling Crust and
                   the Portal Fields notice it on a normal mission instead)
    B  Use         the site can only be solved by using the rule on purpose
    C  Generalise  the rule's details differ per student, so only a program
                   built on sensors and variables works (and copying doesn't)

This is not the maze game. The rover never turns: it drives by compass on
open ground,

    north()  south(3)  east()  west(2)  wait()

and every square of driving (or wait) takes one tick of planet time. It
senses with look("east"), which says what's on the next square in words
("rock", "ice", "crater"...), and x() and y(), the square it's on. Each site
has a mission: reach the beacon, collect every sample, or report() a number
to mission control. Sensors arrive zone by zone. Student code runs in the
Light Cycles interpreter (cycles.Brain): a whitelist of the parse tree, so no
imports, attribute access or real builtins ever run on the teacher's laptop.

Map squares:
    #  rock          .  ground        S  start (ground)   G  beacon
    ~  ice           O  crater        *  sample           +  sunny ground
    P  portal pad

A site with a beacon is reached by stopping on it (with every sample
collected first, if there are any). Without a beacon, collecting the last
sample completes it. A variant with an "answer" is a field measurement:
report() the right number. Crystals are bonus pick-ups listed beside the map
(a variant's "crystals"), lying on top of whatever square they're on.

Every site has three stars: complete the mission, the site's bonus
challenge, and compact code (that many lines or fewer). Re-running to earn
them is the practice.
"""

import ast
import difflib
import random
import zlib

from cycles import (DIRS, BotError, Brain, _Break, _Continue, _Frame, _TooLong,
                    syntax_message)

MAX_TICKS = 1000          # planet time before the rover gives up
PROGRAM_BUDGET = 200_000  # interpreter operations for one whole run
MAX_CODE = 4000           # characters in one program
MAX_PRINTS = 80           # print() lines kept: the LAST ones
MAX_MOVE = 50             # east(n) drives at most this many squares
BATTERY_MAX = 100
SUN_CHARGE = 2            # battery gained each tick the rover ends in sunlight

COMMANDS = ("north", "south", "east", "west", "wait")
COMPASS = {"north": 0, "east": 1, "south": 2, "west": 3}   # index into DIRS

# The zones in order, by key (a test checks ZONES matches). Each sensor
# arrives with a zone and stays for every zone after it.
ZONE_ORDER = ["landing", "ice", "wind", "crumble", "solar", "portals", "signal",
              "hops", "belts", "drill", "gates", "relay", "push", "laser", "cargo",
              "uncharted"]
SENSOR_ARRIVES = {
    "look": "landing", "at_beacon": "landing",
    "x": "ice", "y": "ice", "report": "ice",
    "tick": "wind",
    "samples_left": "crumble",
    "battery": "solar", "in_sun": "solar",
    "beacon_x": "signal", "beacon_y": "signal",
    "jump": "hops",
    "drill": "drill", "drills_left": "drill",
    "has_key": "gates", "key_x": "gates", "key_y": "gates",
    "next_x": "relay", "next_y": "relay", "flags_left": "relay",
    "distance": "laser",
    "cargo": "cargo", "home_x": "cargo", "home_y": "cargo",
    "sample_x": "cargo", "sample_y": "cargo",
    "gust_in": "uncharted",
}
SENSOR_ZONE = {name: ZONE_ORDER.index(key) for name, key in SENSOR_ARRIVES.items()}
RELAY_ZONE = ZONE_ORDER.index("relay")

# What look() calls each square.
WORDS = {"#": "rock", ".": "ground", "S": "ground", "G": "beacon", "~": "ice",
         "O": "crater", "*": "ground", "+": "sun", "P": "pad",
         ">": "belt", "<": "belt", "^": "belt", "v": "belt",
         "k": "ground", "D": "gate", **{str(n): "ground" for n in range(1, 10)},
         "B": "boulder", "H": "home"}
# Every word look() can give back, for spotting one written without quotes.
LOOK_WORDS = set(WORDS.values()) | {"crack", "sample", "key", "flag", "sun"}
OPEN_WORDS = {"empty", "open", "space", "free", "clear", "nothing", "floor", ""}


def check_look_words(node):
    """look() compared with a word it never gives back, like "wall" from the
    maze game or "Rock": the check is never true, so say so before it runs."""
    sides = [node.left] + node.comparators
    if not any(isinstance(s, ast.Call) and getattr(s.func, "id", "") == "look"
               for s in sides):
        return
    for s in sides:
        if isinstance(s, ast.Constant) and isinstance(s.value, str) and \
                s.value not in LOOK_WORDS:
            word = s.value.strip().lower()
            near = difflib.get_close_matches(word, LOOK_WORDS, 1, 0.6)
            raise BotError(f'look() never gives back "{s.value}". '
                           + ('An open square is "ground".' if word in OPEN_WORDS else
                              f'Did you mean "{near[0]}"?' if near else
                              'It gives back words like "rock", "ground" and '
                              '"crater", in small letters.'))


def check_drive_math(node):
    """A drive command in a sum, like  east(2) + south(2):  it gives back
    nothing to add, so say what to write instead of "not None"."""
    parts = node.values if isinstance(node, ast.BoolOp) else [node.left, node.right]
    for part in parts:
        name = getattr(getattr(part, "func", None), "id", "")
        if isinstance(part, ast.Call) and name in COMMANDS:
            raise BotError(f"{name}() drives the rover: it doesn't give back a "
                           f"number to add up. Put each command on its own line, "
                           f"and to go 3 squares write  {name}(3)")
BELTS = {"^": 0, ">": 1, "v": 2, "<": 3}   # which way each belt carries, into DIRS

# The maze game's words, each with what to write on this planet instead.
COMPASS_ONLY = ("This rover doesn't turn: it drives by compass. Write  "
                "north()  south()  east()  or  west(),  like  east(3)")
LOOK_INSTEAD = ('There\'s no "ahead" on this planet. To check the square to '
                'the east, write  look("east") == "rock"')
MAZE_HABITS = {
    "move": COMPASS_ONLY, "turn_left": COMPASS_ONLY, "turn_right": COMPASS_ONLY,
    "turn": COMPASS_ONLY, "forward": COMPASS_ONLY, "go": COMPASS_ONLY,
    "drive": COMPASS_ONLY, "steer": COMPASS_ONLY, "left": COMPASS_ONLY,
    "right": COMPASS_ONLY,
    "wall_ahead": LOOK_INSTEAD, "wall_left": LOOK_INSTEAD,
    "wall_right": LOOK_INSTEAD, "crater_ahead": LOOK_INSTEAD,
    "cracked_ahead": LOOK_INSTEAD,
    "at_goal": "Here it's  at_beacon()",
}
# Commands students guess for this planet's own things, which happen by
# driving (or are theirs to make with def).
PICK_UP = "Samples are picked up by driving over them: no command needed."
UNLOAD = ("Samples unload by themselves when the rover drives onto home 📦. "
          "home_x() and home_y() say where it is.")
GUESSES = {
    "pickup": PICK_UP, "pick_up": PICK_UP, "collect": PICK_UP, "grab": PICK_UP,
    "deliver": UNLOAD, "unload": UNLOAD, "drop": UNLOAD, "home": UNLOAD,
    "go_home": UNLOAD,
    "push": "Drive into a boulder to push it: east() pushes a boulder that's "
            "just east of the rover.",
    "unlock": "A gate opens when you drive into it holding a key: no command needed.",
    "open": "A gate opens when you drive into it holding a key: no command needed.",
    "laser": 'distance("east") measures how many squares the rover can drive east.',
    "measure": 'distance("east") measures how many squares the rover can drive east.',
    "go_to": "go_to() isn't built in: make it with  def go_to(tx, ty):  above "
             "where you use it (📻 Hints shows how). If you saved one, 🧰 "
             "Functions adds it to your code.",
}
LOOK_HOW = ('look() needs a direction in quotes: "north", "south", "east" or '
            '"west", like  look("east")')
JUMP_HOW = ('jump() needs a direction in quotes: "north", "south", "east" or '
            '"west", like  jump("east")')
DRILL_HOW = ('drill() needs a direction in quotes: "north", "south", "east" or '
             '"west", like  drill("east")')
DISTANCE_HOW = ('distance() needs a direction in quotes: "north", "south", "east" '
                'or "west", like  distance("east")')
CARGO_MAX = 3             # samples the rover can carry home at once
# Squares that stop a slide, a belt ride or a gust, as rock does.
SOLID = "#DB"
# Commands that aren't plain driving, so a def can't take their name.
OWN_COMMANDS = ("look", "report", "jump", "drill", "distance")


def literal(node):
    """A number typed straight in, like 6 or -2 (not worked out by code)."""
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.USub, ast.UAdd)):
        node = node.operand
    return isinstance(node, ast.Constant)


READINGS = ("x", "y", "battery", "beacon_x", "beacon_y")   # where things are, not changes


def fixed(node):
    """Typed numbers only, maybe summed like 1+5: no sensor or variable in it."""
    return not any(isinstance(n, (ast.Name, ast.Call)) for n in ast.walk(node))


class _End(Exception):
    """The run is over (mission done, fall, flat battery, out of time): stop
    the program."""


class Rover(Brain):
    """One student's program driving one rover. Unlike a Light Cycles bot,
    the program runs once from top to bottom, and its commands move the rover."""

    def __init__(self, code, world, sensors):
        self.world = world
        self.sensors = sensors            # every name the program may call
        self.prints = []
        self.globals = _Frame(module=True)
        self.funcs = {}
        self.ops = 0
        self.budget = PROGRAM_BUDGET
        self.steering = False
        self.depth = 0
        # When planet time last moved on, and the last drive of 0 squares, to
        # say why a while loop that stopped the rover never ends.
        self.seen_t = self.still_since = 0
        self.zero = None
        if len(code) > MAX_CODE:
            raise BotError(f"Your program is too long: the limit is {MAX_CODE} "
                           f"characters (about 100 lines). Delete some comments "
                           f"or lines you don't need.")
        code = code.replace(" ", " ").replace("​", "").replace("﻿", "")
        self.source = code   # to quote a student's own line back to them
        try:
            self.tree = ast.parse(code)
        except SyntaxError as e:
            # The maze game's sensor isn't on this planet: give one that is.
            err = BotError(syntax_message(e, "def step():").replace(
                "if not wall_ahead():", "while not at_beacon():"))
            err.syntax_line = e.lineno   # for the editor; the text already says it
            raise err
        # Every def in the program, so a call above its def can say where it is,
        # and the ones that ran, so a def nobody calls can be pointed out.
        self.defs = {n.name: n.lineno for n in ast.walk(self.tree)
                     if isinstance(n, ast.FunctionDef)}
        self.called = set()

    def run(self):
        try:
            self.run_block(self.tree.body, self.globals)
        except (_Break, _Continue):
            raise BotError("break and continue only work inside a loop.")

    def tick(self):
        self.ops += 1
        if self.world.t != self.seen_t:
            self.seen_t, self.still_since = self.world.t, self.ops
        if self.ops > self.budget:
            raise _TooLong("Your program ran too long")

    # Strange Planet's own wording for things the interpreter doesn't allow.
    def eval(self, node, frame):
        if isinstance(node, (ast.List, ast.Tuple, ast.Dict, ast.Set, ast.ListComp,
                             ast.Subscript)):
            raise BotError("Lists and [ ] aren't part of Strange Planet — use a "
                           "few separate variables instead.")
        if isinstance(node, ast.JoinedStr):
            raise BotError("f-strings aren't part of Strange Planet. To print words "
                           'and a number use a comma:  print("tick", tick())')
        if isinstance(node, ast.Attribute):
            raise BotError("Dots like  random.choice  aren't part of Strange "
                           "Planet — use the commands and sensors, or make your "
                           "own with def.")
        if isinstance(node, ast.Compare):
            check_look_words(node)
        if isinstance(node, (ast.BinOp, ast.BoolOp)):
            check_drive_math(node)
        return super().eval(node, frame)

    def math(self, op, a, b):
        # Light Cycles' example uses its wall_ahead(): use this planet's sensor.
        if isinstance(op, (ast.BitAnd, ast.BitOr)):
            word = "and" if isinstance(op, ast.BitAnd) else "or"
            raise BotError(f'Use the word  {word}  to join two checks, like:  '
                           f'if look("east") == "rock" {word} look("south") == "rock":')
        return super().math(op, a, b)

    def mine(self, name, frame):
        return name in frame.vars or name in self.globals.vars

    def lookup(self, name, frame):
        if not self.mine(name, frame):
            if name.lower() in ("left", "right", "straight", "forward"):
                raise BotError(COMPASS_ONLY)
            if name.lower() in COMPASS:
                raise BotError(f'To drive, write  {name.lower()}()  with brackets. '
                               f'To name the direction, put it in quotes: '
                               f'"{name.lower()}"')
            if name.lower() in LOOK_WORDS and name not in self.defs:
                raise BotError(f'Put quotes round words:  "{name.lower()}". look() '
                               f'gives back a word, like  look("east") == '
                               f'"{name.lower()}"')
        return super().lookup(name, frame)

    def assign(self, name, value, frame):
        if name in ("x", "y") and name in self.sensors:
            raise BotError(f"{name}() is the rover's sensor for where it is, so "
                           f"{name} can't be a variable too. Pick another name, "
                           f"like  n  or  steps")
        super().assign(name, value, frame)

    def run_statement(self, node, frame):
        self.world.line = node.lineno
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            raise BotError("import isn't allowed on Strange Planet — "
                           "everything you need is already here.")
        if isinstance(node, ast.FunctionDef) and \
                (node.name in COMMANDS or node.name in OWN_COMMANDS):
            raise BotError(f"{node.name}() is already one of the rover's commands — "
                           f"pick another name, like  def hop():")
        if isinstance(node, ast.Expr) and not isinstance(node.value, (ast.Call, ast.Name, ast.Tuple)) \
                and not (isinstance(node.value, ast.Constant) and isinstance(node.value.value, str)):
            if isinstance(node.value, ast.Constant) and node.value.value is Ellipsis:
                raise BotError("The hints' ... only marks where your own lines go. "
                               "Replace it with the commands you need.")
            if isinstance(node.value, (ast.BinOp, ast.BoolOp)):
                check_drive_math(node.value)
            # Worked out and then dropped: show where it could go.
            src = ast.get_source_segment(self.source, node.value) or ast.unparse(node.value)
            text = (f"That line checks something but doesn't use the answer. Put it "
                    f"after if or while, like:  if {src}:"
                    if isinstance(node.value, ast.Compare) else
                    f"That line works something out but doesn't use it. Keep it in a "
                    f"variable, like  n = {src}  or put it inside print() or report().")
            raise BotError(text if frame.module else
                           text + " Inside a def, return hands it back.")
        if isinstance(node, ast.Expr) and isinstance(node.value, ast.Tuple) and \
                all(isinstance(e, ast.Call) for e in node.value.elts):
            raise BotError("Put each command on its own line, with no comma "
                           "between them.")
        if isinstance(node, ast.Expr) and isinstance(node.value, ast.Name):
            name = node.value.id
            if name in self.sensors or name in self.defs:
                raise BotError(f"{name} needs brackets to run: write  {name}()")
            self.lookup(name, frame)   # left, north, or a name it doesn't know
            if frame.module:
                raise BotError("That line doesn't do anything on its own. "
                               "Commands need brackets, like  east()")
        super().run_statement(node, frame)

    def call_user(self, fn, args):
        self.called.add(fn.name)
        want = len(fn.args.args)
        if len(args) != want:
            raise BotError(f"{fn.name}() doesn't take anything in the ( ), because "
                           f"it was made with  def {fn.name}():" if not want else
                           f"{fn.name}() needs {want} value{'s' if want > 1 else ''} "
                           f"in the ( ), like  {fn.name}({', '.join(['3'] * want)})")
        return super().call_user(fn, args)

    def direction(self, node, frame, how=LOOK_HOW):
        """look()'s or jump()'s direction: "east" in quotes, a variable
        holding it, or (forgiven) the bare word east."""
        if isinstance(node, ast.Name) and node.id.lower() in COMPASS and \
                not self.mine(node.id, frame):
            return node.id.lower()
        way = self.eval(node, frame)
        if not isinstance(way, str) or way.strip().lower() not in COMPASS:
            raise BotError(how)
        return way.strip().lower()

    def call(self, node, frame):
        if isinstance(node.func, ast.Attribute):
            raise BotError(f"{ast.unparse(node.func)}() isn't part of Strange "
                           f"Planet — use the commands and sensors, or make your "
                           f"own with def.")
        if not isinstance(node.func, ast.Name):
            raise BotError("I can only call plain commands, like  east()")
        if node.keywords:
            raise BotError("Commands don't take name=value arguments here.")
        name = node.func.id
        world = self.world
        if name in COMMANDS:
            args = [self.eval(a, frame) for a in node.args]
            if len(args) > 1:
                raise BotError(f"{name}() takes one number at most, like  {name}(3)")
            n = self.number(args[0], f"{name}()") if args else 1
            if args and literal(node.args[0]):
                world.typed = True   # a number typed in, not measured
            back = {"north": "south", "south": "north", "east": "west", "west": "east"}.get(name)
            if n < 0 and back:
                raise BotError(f"{name}() only drives {name}. To go the other way, "
                               f"use  {back}({-n})")
            if n < 0 or n > MAX_MOVE:
                raise BotError(f"{name}() takes a number from 0 to {MAX_MOVE}.")
            if n == 0:
                said = ast.unparse(node.args[0]).replace("'", '"')
                self.zero = (f"{name}({said})", self.ops)
            for _ in range(n):
                world.act(name)
            return None
        if name == "look" and name in self.sensors:
            if len(node.args) != 1:
                raise BotError(LOOK_HOW)
            return world.look(self.direction(node.args[0], frame))
        if name == "jump" and name in self.sensors:
            if len(node.args) != 1:
                raise BotError(JUMP_HOW)
            world.act("jump", self.direction(node.args[0], frame, JUMP_HOW))
            return None
        if name == "distance" and name in self.sensors:
            if len(node.args) != 1:
                raise BotError(DISTANCE_HOW)
            return world.distance(self.direction(node.args[0], frame, DISTANCE_HOW))
        if name == "drill" and name in self.sensors:
            if len(node.args) != 1:
                raise BotError(DRILL_HOW)
            world.act("drill", self.direction(node.args[0], frame, DRILL_HOW))
            return None
        if name == "report" and name in self.sensors:
            if len(node.args) != 1:
                raise BotError("report() sends one number, like  report(6)")
            value = self.eval(node.args[0], frame)
            if isinstance(value, bool) or not isinstance(value, int):
                raise BotError(f"report() sends a whole number, like  report(6), "
                               f"not {value!r}.")
            arg = node.args[0]
            # report(battery()) sends a reading, not a change: worth naming.
            reading = arg.func.id if isinstance(arg, ast.Call) and isinstance(arg.func, ast.Name) \
                and not arg.args and arg.func.id in READINGS else None
            world.report(value, not literal(arg), fixed(arg), reading)
            return None
        if name in self.sensors:
            if node.args:
                raise BotError(f"{name}() doesn't take anything in the ( ).")
            return world.sense(name)
        if name in SENSOR_ZONE:
            raise BotError(f"{name}() hasn't been unlocked yet: it arrives in "
                           f"{ZONE_NAMES[SENSOR_ZONE[name]]}.")
        if name in MAZE_HABITS and name not in self.funcs and name not in self.defs:
            raise BotError(MAZE_HABITS[name])
        if name in GUESSES and name not in self.funcs and name not in self.defs:
            raise BotError(GUESSES[name])
        if name == "print":
            args = [self.eval(a, frame) for a in node.args]
            line = " ".join(str(a) for a in args)
            world.note(line if len(line) <= 200 else line[:199] + "…")
            return None
        if name in ("str", "int"):
            raise BotError(f"{name}() isn't needed here. To print words and a "
                           f'number use a comma:  print("tick", tick())')
        if name in ("max", "min") and len(node.args) < 2:
            raise BotError(f"{name}() needs at least two numbers, like "
                           f"{name}(3, battery())")
        if name not in self.funcs and name in self.defs:
            raise BotError(f"{name}() is made with def further down, on line "
                           f"{self.defs[name]}. The program runs from the top, so "
                           f"move the def above the first line that uses {name}().")
        known = list(self.sensors) + list(self.funcs) + ["print", "max", "min", "abs", "range"]
        if name not in known and not difflib.get_close_matches(name.lower(), known, 1, 0.75):
            raise BotError(f"I don't know the command '{name}'. The rover's commands "
                           f"and sensors are the buttons under your code — or make "
                           f"{name}() yourself with def.")
        return super().call(node, frame)


class World:
    """The planet during one run: the rover, the hidden rules, and the replay."""

    def __init__(self, variant, rules):
        self.grid = [list(row) for row in variant["map"]]
        self.rows, self.cols = len(self.grid), len(self.grid[0])
        self.rules = rules
        self.v = variant
        self.r, self.c = next((r, c) for r, row in enumerate(self.grid)
                              for c, ch in enumerate(row) if ch in "SH")
        self.goal = next(((r, c) for r, row in enumerate(self.grid)
                          for c, ch in enumerate(row) if ch == "G"), None)
        self.mission = mission_of(variant)
        self.d = variant.get("dir", 1)   # the way the rover last drove: for drawing it
        self.t = 0
        self.battery = variant.get("battery", BATTERY_MAX)
        self.cracked = set()
        self.crack = None    # the square that just cracked, for the next frame
        self.crystals = {tuple(p) for p in variant.get("crystals", [])}
        self.bumps = self.pushes = 0
        self.gusted = []        # the ticks a gust pushed the rover
        self.computed = False   # the right report() was worked out by code
        self.reading = None     # (sensor, value) when report() sent a reading as it was
        self.copied = False     # report()ed the answer on a classmate's planet,
                                # or "old": the answer from before each had their own
        self.samples = {(r, c) for r, row in enumerate(self.grid)
                        for c, ch in enumerate(row) if ch == "*"}
        self.keys = {(r, c) for r, row in enumerate(self.grid)
                     for c, ch in enumerate(row) if ch == "k"}
        self.held = 0          # keys picked up and not used on a gate yet
        self.last_key = None   # where the last key was picked up
        self.locked = None     # the last gate the rover found locked
        # Flags by number: they count only in order, 1 first.
        self.flags = {int(ch): (r, c) for r, row in enumerate(self.grid)
                      for c, ch in enumerate(row) if ch.isdigit()}
        self.flag = 1          # the next flag to reach
        self.drills = variant.get("drills", 0)
        self.drill_out = False  # a drill() found none left
        self.sunlit = None      # (tick, square, battery) the last time it stood in sun
        self.how = None        # how the rover got onto its last square
        self.opened = None     # the square that just turned to ground, for the next frame
        self.moved = []        # squares a pushed boulder just changed, for the next frame
        self.stuck = None      # the last boulder that wouldn't move
        self.typed = False     # a drive was given a typed-in number
        self.laser = None      # the last distance() measured, for the next frame
        self.home = next(((r, c) for r, row in enumerate(self.grid)
                          for c, ch in enumerate(row) if ch == "H"), None)
        self.cargo = 0         # samples on board, not yet brought home
        self.picked = None     # the sample just picked up, for the next frame
        self.links = {}
        for a, b in variant.get("pairs", []):
            self.links[tuple(a)] = tuple(b)
            self.links[tuple(b)] = tuple(a)
        for a, b in variant.get("oneway", []):
            self.links[tuple(a)] = tuple(b)
        self.log = []
        self.prints = []
        self.line = 0        # the line of code running now, for the editor to follow
        self.frames = [self.frame()]
        self.end = None      # "goal", "wrong", "fell", "battery", "ticks" once it's over

    # ---- what the rover sees ----------------------------------------------

    def at(self, r, c):
        if 0 <= r < self.rows and 0 <= c < self.cols:
            return self.grid[r][c]
        return "#"

    def ahead(self):
        dr, dc = DIRS[self.d]
        return self.r + dr, self.c + dc

    def sunny(self, r, c):
        if self.at(r, c) == "+":
            return True
        band = self.v.get("sun")
        if not band or self.at(r, c) == "#":
            return False
        return (c - self.sun_at(self.t)) % self.cols < band["width"]

    def in_sun(self):
        return self.sunny(self.r, self.c)

    def sun_at(self, t):
        band = self.v["sun"]
        return (band["start"] + t // band["every"]) % self.cols

    def gust_in(self):
        every = self.v.get("wind")
        if not every:
            return 0
        return every - self.t % every

    def look(self, way):
        dr, dc = DIRS[COMPASS[way]]
        r, c = self.r + dr, self.c + dc
        if (r, c) in self.cracked:
            return "crack"
        if (r, c) in self.samples:
            return "sample"
        if (r, c) in self.keys:
            return "key"
        if (r, c) in self.flags.values() and self.flag_at(r, c) >= self.flag:
            return "flag"
        word = WORDS[self.at(r, c)]
        return "sun" if word == "ground" and self.sunny(r, c) else word

    def sense(self, name):
        if name == "at_beacon":
            return (self.r, self.c) == self.goal
        if name == "x":
            return self.c
        if name == "y":
            return self.r
        if name == "tick":
            return self.t
        if name == "samples_left":
            return len(self.samples)
        if name == "battery":
            return self.battery
        if name == "in_sun":
            return self.in_sun()
        if name == "gust_in":
            return self.gust_in()
        if name in ("beacon_x", "beacon_y"):
            if self.goal is None:
                return -1
            return self.goal[1] if name == "beacon_x" else self.goal[0]
        if name == "drills_left":
            return self.drills
        if name == "has_key":
            return self.held > 0
        if name in ("key_x", "key_y"):
            # The nearest key still lying there, else where the last one was.
            spot = min(self.keys, key=lambda p: (abs(p[0] - self.r) + abs(p[1] - self.c), p),
                       default=self.last_key)
            if spot is None:
                return -1
            return spot[1] if name == "key_x" else spot[0]
        if name == "cargo":
            return self.cargo
        if name in ("home_x", "home_y"):
            if self.home is None:
                return -1
            return self.home[1] if name == "home_x" else self.home[0]
        if name in ("sample_x", "sample_y"):
            # The nearest sample still out there.
            spot = min(self.samples, key=lambda p: (abs(p[0] - self.r) + abs(p[1] - self.c), p),
                       default=None)
            if spot is None:
                return -1
            return spot[1] if name == "sample_x" else spot[0]
        if name == "flags_left":
            return len(self.flags) - self.flag + 1
        if name in ("next_x", "next_y"):
            # The next flag, then the beacon once every flag is done.
            spot = self.flags.get(self.flag, self.goal)
            if spot is None:
                return -1
            return spot[1] if name == "next_x" else spot[0]
        raise BotError(f"I don't know the sensor '{name}'.")

    def distance(self, way):
        """How many squares the rover could drive `way` before something is
        in the way: rock, a crater, a boulder or a gate."""
        dr, dc = DIRS[COMPASS[way]]
        n = 0
        while self.at(self.r + dr * (n + 1), self.c + dc * (n + 1)) not in SOLID + "O":
            n += 1
        self.laser = [COMPASS[way], n]
        return n

    def flag_at(self, r, c):
        return next(n for n, p in self.flags.items() if p == (r, c))

    # ---- the replay ----------------------------------------------------------

    def frame(self, event=None):
        f = {"r": self.r, "c": self.c, "d": self.d, "t": self.t}
        if "battery" in self.rules:
            f["b"] = self.battery
        if self.v.get("sun"):
            f["sun"] = self.sun_at(self.t)
        if self.crack:
            f["x"] = self.crack
            self.crack = None
        if self.v.get("drills") is not None:
            f["dl"] = self.drills
        if self.held or self.last_key:
            f["k"] = self.held
        if self.flags:
            f["fl"] = self.flag
        if self.opened:
            f["g"] = self.opened   # a gate opened or a rock drilled: ground now
            self.opened = None
        if self.moved:
            f["m"] = self.moved    # [r, c, what's there now] for each square
            self.moved = []
        if self.laser:
            f["ls"] = self.laser
            self.laser = None
        if self.picked:
            f["p"] = self.picked
            self.picked = None
        if self.home:
            f["cg"] = self.cargo
        if self.line:
            f["ln"] = self.line
        if event:
            f["e"] = event
        return f

    def note(self, text):
        self.prints.append({"t": self.t, "text": text})
        del self.prints[:-MAX_PRINTS]

    def say(self, text):
        self.log.append(f"tick {self.t}: {text}")

    def finish(self, why, text):
        self.end = why
        self.say(text)
        self.frames.append(self.frame(why))
        raise _End()

    # ---- what the rover does -------------------------------------------------

    def leave(self):
        """The rover is about to leave its square: on crumbling ground it cracks."""
        if "crumble" in self.rules and self.at(self.r, self.c) in ".S*+":
            self.cracked.add((self.r, self.c))
            self.crack = [self.r, self.c]

    def enter(self, r, c, how="move"):
        """Put the rover on (r, c) and deal with whatever is there."""
        self.leave()
        self.r, self.c = r, c
        self.how = how
        ch = self.at(r, c)
        if (r, c) in self.cracked:
            self.frames.append(self.frame("jump" if how == "jump" else None))
            self.finish("fell", "💥 cracked ground gave way")
        if ch == "O":
            self.frames.append(self.frame("jump" if how == "jump" else None))
            self.finish("fell", "💥 fell into a crater")
        if (r, c) in self.crystals:
            self.crystals.discard((r, c))
            self.say("💎 crystal collected")
        if (r, c) in self.samples:
            if self.home and self.cargo >= CARGO_MAX:
                self.say(f"🧪 the cargo bay is full ({CARGO_MAX}): unload at home first")
            else:
                self.samples.discard((r, c))
                self.picked = [r, c]
                if self.home:
                    self.cargo += 1
                    self.say(f"🧪 sample on board, {self.cargo} of {CARGO_MAX}")
                else:
                    self.say(f"🧪 sample collected, {len(self.samples)} left")
        if (r, c) == self.home and self.cargo:
            self.say(f"📦 brought {self.cargo} sample{'s' if self.cargo != 1 else ''} home, "
                     f"{len(self.samples)} still out")
            self.cargo = 0
        if (r, c) in self.keys:
            self.keys.discard((r, c))
            self.held += 1
            self.last_key = (r, c)
            self.say("🔑 picked up a key")
        if ch.isdigit() and int(ch) >= self.flag:
            if int(ch) == self.flag:
                self.flag += 1
                left = len(self.flags) - self.flag + 1
                self.say(f"🚩 flag {ch} reached, " +
                         (f"{left} to go" if left else "every flag done"))
            else:
                self.say(f"🚩 that's flag {ch}: flag {self.flag} comes first")
        self.frames.append(self.frame(how if how in ("jump", "gust") else None))

    def act(self, command, way=None):
        """One tick: drive, wait, or jump `way`."""
        if self.end:
            raise _End()
        if "battery" in self.rules and self.in_sun():
            self.sunlit = (self.t, (self.r, self.c), self.battery)
        if self.t >= MAX_TICKS:
            self.finish("ticks", f"⏱ out of time ({MAX_TICKS} ticks)")
        if "battery" in self.rules and command != "wait" and self.battery <= 0:
            self.finish("battery", "🔋 battery empty")
        self.t += 1
        if "battery" in self.rules and command != "wait":
            self.battery -= 1
        if command == "wait":
            self.frames.append(self.frame("wait"))
        elif command == "drill":
            self.d = COMPASS[way]
            self.drill()
        else:
            self.d = COMPASS[way or command]
            self.drive(way or command, 2 if command == "jump" else 1)
        if "wind" in self.rules and command not in ("wait", "drill") and \
                self.t % self.v["wind"] == 0:
            self.gust()
        if "battery" in self.rules and self.in_sun():
            self.battery = min(BATTERY_MAX, self.battery + SUN_CHARGE)
            self.frames[-1]["b"] = self.battery
        self.check_goal()

    def drive(self, command, squares=1):
        """Drive one square, or jump two: over whatever is in between, onto
        the square beyond."""
        dr, dc = DIRS[self.d]
        r, c = self.r + dr * squares, self.c + dc * squares
        if self.at(r, c) == "#":
            self.bumps += 1
            self.say("🧱 bumped into rock" if squares == 1 else
                     "🧱 a jump can't land on rock")
            self.frames.append(self.frame("bump"))
            return
        if self.at(r, c) == "B":
            if squares == 2:
                self.say("🧱 a jump can't land on a boulder")
                self.frames.append(self.frame("bump"))
                return
            br, bc = r + dr, c + dc
            if self.at(br, bc) not in ".+O" or (br, bc) in self.cracked:
                self.stuck = (r, c)
                self.say("🪨 the boulder won't move: something is behind it")
                self.frames.append(self.frame("bump"))
                return
            filled = self.at(br, bc) == "O"
            self.grid[r][c] = "."
            self.grid[br][bc] = "." if filled else "B"
            self.moved = [[r, c, "."], [br, bc, "." if filled else "B"]]
            self.say("🪨 pushed the boulder into the crater: it's filled in" if filled
                     else f"🪨 pushed the boulder {command}")
        if squares == 2 and self.at(self.r + dr, self.c + dc) == "D":
            self.say("🚪 a gate is too tall to jump over")
            self.frames.append(self.frame("bump"))
            return
        if self.at(r, c) == "D":
            if squares == 2 or not self.held:
                if squares == 1:
                    self.locked = (r, c)
                self.say(f"🔒 the gate at x {c}, y {r} is locked: it needs a key"
                         if squares == 1 else "🧱 a jump can't land on a gate")
                self.frames.append(self.frame("bump"))
                return
            self.held -= 1
            self.grid[r][c] = "."
            self.opened = [r, c]
            self.say("🚪 the key opened the gate")
        if squares == 2:
            self.say(f"🦘 jumped {command}")
        self.enter(r, c, "jump" if squares == 2 else "move")
        self.portal()
        # On ice the rover keeps sliding until something stops it.
        slid = False
        while "ice" in self.rules and self.at(self.r, self.c) == "~":
            r, c = self.ahead()
            if self.at(r, c) in SOLID:
                break
            self.enter(r, c, "slide")
            slid = True
        if slid:
            self.say(f"⛸ one {'jump' if squares == 2 else command}() kept sliding")
        self.ride()

    def ride(self):
        """A belt carries the rover the way its arrow points, belt after belt,
        onto the square after the last one (unless that's rock: then it stays
        on the last belt). All in the same tick, like a slide on ice."""
        seen = set()
        while self.at(self.r, self.c) in BELTS and (self.r, self.c) not in seen:
            seen.add((self.r, self.c))
            dr, dc = DIRS[BELTS[self.at(self.r, self.c)]]
            r, c = self.r + dr, self.c + dc
            if self.at(r, c) in SOLID:
                break
            self.enter(r, c, "belt")
        if seen:
            self.say(f"🛤 a belt carried the rover to x {self.c}, y {self.r}")

    def drill(self):
        """drill(way): the rock on the next square that way becomes ground."""
        dr, dc = DIRS[self.d]
        r, c = self.r + dr, self.c + dc
        if self.at(r, c) != "#" or not (0 < r < self.rows - 1 and 0 < c < self.cols - 1):
            self.say("⛏ nothing to drill there" if self.at(r, c) != "#" else
                     "⛏ the edge of the map is too hard to drill")
        elif not self.drills:
            self.drill_out = True
            self.say("⛏ no drills left")
        else:
            self.drills -= 1
            self.grid[r][c] = "."
            self.opened = [r, c]
            self.say(f"⛏ drilled through the rock, {self.drills} "
                     f"drill{'s' if self.drills != 1 else ''} left")
        self.frames.append(self.frame("drill"))

    def portal(self):
        if self.at(self.r, self.c) != "P":
            return
        to = self.links.get((self.r, self.c))
        if to is None:
            return
        frm = (self.r, self.c)
        self.r, self.c = to
        self.frames.append(self.frame("portal"))
        self.say(f"✨ pad at x {frm[1]} y {frm[0]} → x {to[1]} y {to[0]}")

    def gust(self):
        r, c = self.r, self.c + 1
        if self.at(r, c) in SOLID:
            self.say("💨 gust, but a rock sheltered the rover")
            return
        self.pushes += 1
        self.gusted.append(self.t)
        self.say("💨 gust pushed the rover east")
        self.enter(r, c, "gust")

    def report(self, value, computed, fixed=True, reading=None):
        if self.end:
            raise _End()
        if self.mission != "report":
            self.say(f"📡 report sent: {value}")
            return
        self.computed = computed
        if value == self.v["answer"]:
            self.finish("goal", f"📡 you reported {value}. Mission control: "
                                f"that matches what we measured!")
        # A number the code found itself (report(y())) isn't a copy, even
        # when it happens to be someone else's.
        if fixed and value == self.v.get("old"):
            self.copied = "old"
            self.finish("wrong", f"📡 you reported {value}. That was the number "
                                 f"before every planet got its own: measure yours.")
        if reading:
            self.reading = (reading, value)
            self.finish("wrong", f"📡 you reported {value}: what {reading}() says "
                                 f"right now, not " + ("how far away it is." if reading.startswith("beacon_")
                                                       else "how much it changed."))
        if fixed and value in self.v.get("others", ()):
            self.copied = True
            self.finish("wrong", f"📡 you reported {value}. That's the number on "
                                 f"someone else's planet: measure your own.")
        self.finish("wrong", f"📡 you reported {value}. Mission control "
                             f"measured something different.")

    def check_goal(self):
        if self.mission == "beacon" and (self.r, self.c) == self.goal:
            if self.samples:
                self.say(f"🛰 the beacon needs every sample first "
                         f"({len(self.samples)} left)")
            elif self.flag in self.flags:
                self.say(f"🛰 the beacon needs every flag first "
                         f"(flag {self.flag} is next)")
            else:
                self.finish("goal", "🎉 beacon reached")
        elif self.mission == "samples" and not self.samples:
            self.finish("goal", "🎉 every sample collected")
        elif self.mission == "deliver" and not self.samples and not self.cargo:
            self.finish("goal", "🎉 every sample brought home")


def n_squares(n, way):
    return f"{n} square{'s' if n != 1 else ''} {way}"


def far(frm, to):
    """How far `to` is from `frm` by compass, like '5 squares east and 2 south'."""
    (r, c), (tr, tc) = frm, to
    parts = []
    if tc != c:
        parts.append(n_squares(abs(tc - c), "east" if tc > c else "west"))
    if tr != r:
        parts.append(n_squares(abs(tr - r), "south" if tr > r else "north"))
    return " and ".join(parts)


def where(p):
    return f"x {p[1]}, y {p[0]}"


# Why the rover fell, by how it got onto the square.
FELL = {"gust": "A 💨 gust pushed the rover into a crater",
        "slide": "The rover slid across the ice into a crater",
        "belt": "A belt carried the rover into a crater",
        "jump": "The rover jumped into a crater",
        "move": "The rover drove into a crater"}
FELL_NEXT = {"slide": "On ice, one move keeps sliding until rock stops it. Pick a "
                      "rock to stop against.",
             "belt": "Belts carry the rover the way their arrows point. Jump over a "
                     "belt you don't want to ride.",
             "jump": "A jump lands two squares away. Check that square is ground "
                     "before you jump.",
             "move": 'Check the square before you drive, like  '
                     'if look("east") == "crater":'}


def locked_gate(world, at):
    """The next step when a locked gate stopped the rover and a key is still out."""
    if not (world.locked and world.at(*world.locked) == "D" and world.keys):
        return ""
    key = min(world.keys)
    return (f"The gate at {where(world.locked)} is locked. Pick up the key at "
            f"{where(key)} first: {far(at, key)}.")


def drill_next(world):
    """The next step when rock stopped the rover and it still has drills."""
    dr, dc = DIRS[world.d]
    r, c = world.r + dr, world.c + dc
    if not (world.bumps and world.drills and world.at(r, c) == "#"
            and 0 < r < world.rows - 1 and 0 < c < world.cols - 1):
        return ""
    way = next(w for w, d in COMPASS.items() if d == world.d)
    return (f'Rock stopped it going {way}. drill("{way}") turns that rock into '
            f"ground, then drive on. You have {world.drills} "
            f"drill{'s' if world.drills != 1 else ''} left.")


def gust_numbers(code):
    """The numbers a program divides tick() by, like 9 in  tick() % 9 == 8,
    or in  GUST = 9  then  tick() % GUST."""
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return []
    named = {t.id: n.value.value for n in ast.walk(tree) if isinstance(n, ast.Assign)
             and isinstance(n.value, ast.Constant) and type(n.value.value) is int
             for t in n.targets if isinstance(t, ast.Name)}
    numbers = []
    for n in ast.walk(tree):
        if isinstance(n, ast.BinOp) and isinstance(n.op, ast.Mod) and \
                isinstance(n.left, ast.Call) and getattr(n.left.func, "id", "") == "tick":
            if isinstance(n.right, ast.Constant) and type(n.right.value) is int:
                numbers.append(n.right.value)
            elif isinstance(n.right, ast.Name) and n.right.id in named:
                numbers.append(named[n.right.id])
    return numbers


def gust_next(world, code):
    """The next step after a gust blew the rover into a crater. A number
    copied from a classmate's planet is the usual reason, so say so."""
    every, numbers = world.v["wind"], gust_numbers(code)
    # What the telemetry's 💨 lines show, said plainly.
    when = f"{every}, {2 * every}, {3 * every} and so on"
    wrong = [n for n in numbers if n != every]
    if wrong:
        return (f"Your code waits with tick() % {wrong[0]}, but the gusts here "
                f"don't come every {wrong[0]} ticks: they come on ticks {when}.")
    if numbers:
        return (f"tick() % {every} is the right number here, but the gust caught "
                f"the rover driving on tick {world.gusted[-1]}. Check before every single "
                f"square, and wait() when tick() % {every} == {every - 1}.")
    return (f"The gusts here come on ticks {when}, and only catch a rover that "
            f"is driving. wait() just before each one: tick() tells your code "
            f"which tick it is.")


def pacing(world, unlocked):
    """A rover that ran out of time going to and fro over the same two or three
    squares: say which, and a crater it could jump from one of them."""
    spots = []
    for f in world.frames[-40:]:
        if (f["r"], f["c"]) not in spots:
            spots.append((f["r"], f["c"]))
    if len(world.frames) < 40 or not 2 <= len(spots) <= 3:
        return None
    names = [where(p) for p in spots]
    what = (f": the rover kept going back and forth between {names[0]} and {names[1]}"
            if len(spots) == 2 else
            f": the rover kept going round {names[0]}, {names[1]} and {names[2]}")
    nxt = ("Your loop keeps making the same moves there, because what it checks "
           "there never changes. Give it another way to go.")
    if "jump" in unlocked:
        jumps = []
        for r, c in spots:
            for way, d in COMPASS.items():
                dr, dc = DIRS[d]
                land = (r + 2 * dr, c + 2 * dc)
                if world.at(r + dr, c + dc) == "O" and world.at(*land) not in SOLID + "O":
                    near = abs(land[0] - world.goal[0]) + abs(land[1] - world.goal[1]) \
                        if world.goal else 0
                    jumps.append((near, way, (r, c)))
        if jumps:
            _, way, frm = min(jumps)
            nxt = f'A crater is in the way. jump("{way}") from {where(frm)} goes over it.'
    return what, nxt


def called_once(code):
    """A def of drives called just once, outside any loop: the likeliest
    reason a program that found the repeat stopped short. Its name, or None."""
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return None
    calls = [n.func.id for n in ast.walk(tree)
             if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)]
    top = [n.value.func.id for n in tree.body if isinstance(n, ast.Expr)
           and isinstance(n.value, ast.Call) and isinstance(n.value.func, ast.Name)]
    for d in tree.body:
        drives = any(isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
                     and n.func.id in COMMANDS for n in ast.walk(d))
        if isinstance(d, ast.FunctionDef) and drives and calls.count(d.name) == 1 \
                and d.name in top:
            return d.name
    return None


def out_of_time(code):
    """What to change when time ran out and nothing else explains it: a while
    loop that never stops, or (with no while in the code) numbers too big."""
    try:
        nodes = list(ast.walk(ast.parse(code)))
    except SyntaxError:
        nodes = []
    if not nodes or any(isinstance(n, ast.While) for n in nodes):
        return ("A while loop is probably going round forever. Check that "
                "what it waits for can happen.")
    if any(isinstance(n, ast.For) for n in nodes):
        return (f"Your for loop repeats more often than the rover has time for: "
                f"{MAX_TICKS} ticks in all. Use a smaller number in range().")
    return (f"Your code asks for more driving than the rover has time for: "
            f"{MAX_TICKS} ticks in all. Use smaller numbers.")


def explain(world, unlocked=(), code=""):
    """What went wrong in plain words, for the banner after a run that didn't
    finish its mission: {"what": what happened, "next": one thing to try}.
    Statements, not questions, and always where it happened."""
    at = (world.r, world.c)
    end = world.end
    what = nxt = ""
    bumps_said = False
    if end == "fell":
        if at in world.cracked:
            what = (f"The ground at {where(at)} had cracked from driving over it "
                    f"before, and gave way")
            nxt = "Ground cracks when the rover leaves it. Never drive back over your own tracks."
        else:
            what = f"{FELL.get(world.how, FELL['move'])} at {where(at)}"
            nxt = FELL_NEXT.get(world.how, FELL_NEXT["move"])
            if world.how == "gust" and "gust_in" in unlocked:
                nxt = ("gust_in() says how many ticks until the next gust. Before "
                       "each square:  if gust_in() == 1: wait()")
            elif world.how == "gust":
                what += f" on tick {world.t}"
                nxt = gust_next(world, code)
            elif world.how == "move" and world.gusted and "gust_in" not in unlocked:
                # Blown off its path earlier, then drove on into the crater.
                what += (f", after a 💨 gust pushed it off its path on tick "
                         f"{world.gusted[-1]}")
                nxt = gust_next(world, code)
            elif world.how == "move":
                # Name the way it was driving, and a crater it could have jumped.
                way = next(w for w, d in COMPASS.items() if d == world.d)
                dr, dc = DIRS[world.d]
                beyond = world.at(at[0] + dr, at[1] + dc)
                if "jump" in unlocked and beyond not in SOLID and beyond != "O":
                    nxt = (f'That crater is one square wide: jump("{way}") from '
                           f"{where((at[0] - dr, at[1] - dc))} goes over it.")
                else:
                    nxt = f'Check the square before you drive, like  if look("{way}") == "crater":'
    elif end == "battery":
        what = f"The battery ran out at {where(at)}, on tick {world.t}"
        if world.sunlit:
            t, spot, charge = world.sunlit
            nxt = (f"It was in the sun at {where(spot)} on tick {t} with {charge} "
                   f"battery, and drove on. Charge up there before you go:  "
                   f"while in_sun() and battery() < 40: wait()")
        else:
            nxt = ("Driving uses 1 battery a square, and the rover never stood in "
                   "the sun. Waiting in sunlight charges it: in_sun() says when "
                   "you're there.")
    elif end == "ticks":
        what = f"Your program ran for {world.t} ticks without finishing"
        nxt = locked_gate(world, at) or drill_next(world)
        if not nxt and world.bumps * 3 > world.t:
            # Stuck driving into rock (a third of the time is plenty, as
            # waits can fill the rest): say where, and which way.
            way = next(w for w, d in COMPASS.items() if d == world.d)
            what += f": the rover was stuck at {where(at)}, bumping into rock"
            nxt = (f'It kept driving {way} into rock. Check look("{way}") first, '
                   f'and drive another way when it says "rock".')
            bumps_said = True
        paced = None if nxt else pacing(world, unlocked)
        if paced:
            what += paced[0]
            nxt = paced[1]
        nxt = nxt or out_of_time(code)
    elif end == "wrong" and world.copied == "old":
        what = "That was the number before every planet got its own"
        nxt = ("Everyone's planet is different now, so everyone's number is too. "
               "Measure your own.")
    elif end == "wrong" and world.reading:
        name, value = world.reading
        what = f"You reported {name}() as it was at the end: {value}"
        if name.startswith("beacon_"):
            own = name[-1]
            nxt = (f"Mission control wants how far the beacon is from the rover, not "
                   f"where it is: take the rover's {own}() away from {name}().")
        else:
            nxt = (f"Mission control wants how much it changed. Remember it first, "
                   f"before = {name}(), then report({name}() - before).")
    elif end == "wrong" and world.copied:
        what = "That's the number on someone else's planet"
        nxt = ("Everyone's planet is different, so everyone's number is too. "
               "Measure your own.")
    elif end == "wrong":
        what = "Mission control measured a different number"
        nxt = "Play the replay and count again."
    elif end == "stopped":
        what = f"Your code finished with the rover at {where(at)}"
        if world.mission == "report":
            nxt = "Nothing was sent. Add a last line with your number inside report( ), and transmit again."
        elif world.mission == "deliver" and world.cargo >= CARGO_MAX and world.samples:
            what += f", carrying {CARGO_MAX} samples: the cargo bay is full"
            nxt = f"Drive home to {where(world.home)} to unload them: {far(at, world.home)}."
        elif world.mission == "deliver" and world.cargo and not world.samples:
            what += (f", carrying the last {world.cargo} "
                     f"sample{'s' if world.cargo != 1 else ''}")
            nxt = f"Bring them home to {where(world.home)}: {far(at, world.home)}."
        elif world.samples:
            near = min(world.samples, key=lambda p: (abs(p[0] - at[0]) + abs(p[1] - at[1]), p))
            n = len(world.samples)
            what += f", and {n} sample{'s' if n != 1 else ''} still out"
            nxt = f"The closest is at {where(near)}: {far(at, near)}."
        elif world.flag in world.flags:
            spot = world.flags[world.flag]
            nxt = f"Flag {world.flag} is next, at {where(spot)}: {far(at, spot)}."
        elif world.goal and locked_gate(world, at):
            nxt = locked_gate(world, at)
        elif world.goal and drill_next(world):
            what += f", away from the beacon at {where(world.goal)}"
            nxt = drill_next(world)
        elif world.goal:
            what += f", away from the beacon at {where(world.goal)}"
            nxt = f"The beacon is {far(at, world.goal)} of there."
            if "ice" in world.rules and "gust_in" not in unlocked:
                # Squares to go mean little when one move slides to a rock.
                nxt += (" On ice one move slides until rock stops it, so work "
                        "back from the beacon: find a rock that would stop a "
                        "slide right next to it.")
    once = end == "stopped" and world.mission != "report" and nxt and called_once(code)
    if once:
        nxt = (f"{once}() ran once. To do its moves again, call it again, or put "
               f"{once}() inside a for loop. {nxt}")
    if not what:
        return None
    extra = []
    if world.drill_out:
        extra.append("The rover ran out of drills.")
    if world.stuck and end in ("stopped", "ticks"):
        extra.append(f"The boulder at {where(world.stuck)} couldn't move: something "
                     f"was behind it.")
    if world.bumps and end in ("stopped", "ticks") and not bumps_said:
        extra.append(f"The rover bumped into rock {world.bumps} "
                     f"time{'s' if world.bumps != 1 else ''}: when it bumps, it doesn't move.")
    out = {"what": " ".join([what + "."] + extra), "next": nxt}
    if world.copied:
        out["copied"] = True   # the coach leads with it
    if world.reading:
        out["lead"] = True     # so does a reading sent as it was
    return out


def progress(variant, run):
    """How far a missed run got, to compare with the student's best:
    ("more", n, words) when more is better (samples), ("less", n, words) when
    less is (squares from the beacon by open ground), or None when distance
    says little (a map with portal pads) or the mission isn't one of those."""
    grid = variant["map"]
    mission = mission_of(variant)
    if mission == "samples":
        total = sum(row.count("*") for row in grid)
        got = total - run["samples"]
        return ("more", got, f"{got} of {total} samples") if total else None
    if mission != "beacon" or any("P" in row for row in grid) or not run["frames"]:
        return None
    start = (run["frames"][-1]["r"], run["frames"][-1]["c"])
    seen, edge, d = {start}, [start], 0
    while edge:
        if any(grid[r][c] == "G" for r, c in edge):
            return ("less", d, f"{d} square{'s' if d != 1 else ''} from the beacon")
        nxt = []
        for r, c in edge:
            for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                rr, cc = r + dr, c + dc
                if 0 <= rr < len(grid) and 0 <= cc < len(grid[rr]) \
                        and grid[rr][cc] not in "#O" and (rr, cc) not in seen:
                    seen.add((rr, cc))
                    nxt.append((rr, cc))
        edge, d = nxt, d + 1
    return None


def mission_of(variant):
    """"report" (a field measurement), "beacon" or "samples"."""
    if "answer" in variant:
        return "report"
    if any("H" in row for row in variant["map"]):
        return "deliver"
    return "beacon" if any("G" in row for row in variant["map"]) else "samples"


ENDED_SHORT = {"report": "🏁 program ended without a report()",
               "beacon": "🏁 program ended away from the beacon",
               "samples": "🏁 program ended with samples still out there",
               "deliver": "🏁 program ended before every sample was home"}


def stalled(line, world, rover):
    """Why a while loop went round forever after the rover stopped moving."""
    text = (f"Line {line}: This while loop kept going round, but the rover had "
            f"stopped at {where((world.r, world.c))}.")
    if rover.zero and rover.zero[1] >= rover.still_since:
        drove = rover.zero[0]
        if "distance(" in drove:
            return (f"{text} {drove} drove 0 squares there, because something "
                    f"is right next to the rover. Jump it or go round it, so the "
                    f"loop can get further.")
        return f"{text} {drove} drove 0 squares there, so nothing changed."
    if world.mission == "deliver" and world.cargo >= CARGO_MAX:
        return (f"{text} The cargo bay was full, so the sample there stayed put. "
                f"When cargo() is {CARGO_MAX}, drive home to {where(world.home)} "
                f"to unload.")
    # Steering that can't reach where it's going: say which way it never drives.
    at, spot, what = (world.r, world.c), None, ""
    if world.samples:
        spot = min(world.samples, key=lambda p: (abs(p[0] - at[0]) + abs(p[1] - at[1]), p))
        what = "The closest sample"
    elif world.flag in world.flags:
        spot, what = world.flags[world.flag], f"Flag {world.flag}"
    elif world.goal:
        spot, what = world.goal, "The beacon"
    if spot and spot != at:
        drives = {n.func.id for n in ast.walk(rover.tree) if isinstance(n, ast.Call)
                  and isinstance(n.func, ast.Name) and n.func.id in COMPASS}
        need = [w for w, go in (("north", spot[0] < at[0]), ("south", spot[0] > at[0]),
                                ("east", spot[1] > at[1]), ("west", spot[1] < at[1]))
                if go and w not in drives]
        if need:
            return (f"{text} {what} is {far(at, spot)} of there, but nothing in "
                    f"your code drives {' or '.join(need)}: add a part that does.")
    # What its look() checks were seeing there, which no branch drove on.
    ways = sorted({n.args[0].value for n in ast.walk(rover.tree) if isinstance(n, ast.Call)
                   and isinstance(n.func, ast.Name) and n.func.id == "look" and n.args
                   and isinstance(n.args[0], ast.Constant) and n.args[0].value in COMPASS})
    saw = " ".join(f'look("{w}") says "{world.look(w)}".' for w in ways)
    return (f"{text} {'There, ' + saw + ' ' if saw else ''}Nothing in the loop moved it "
            f"then, so the loop could never end. Make sure the loop moves the rover "
            f"every time round, whatever it sees.")


def drive(code, variant, rules, zone):
    """Run one program on one planet. Returns the replay the browser animates."""
    world = World(variant, rules)
    sensors = {name: None for name, z in SENSOR_ZONE.items() if z <= zone}
    sensors.update({name: None for name in COMMANDS})
    error = line = rover = None
    try:
        rover = Rover(str(code)[:MAX_CODE + 1], world, sensors)
        rover.run()
    except _End:
        pass
    except _TooLong as e:
        error, line = str(e), e.line
        if e.in_loop == "while" and rover.ops - rover.still_since > 1000:
            error = stalled(e.line, world, rover)
    except BotError as e:
        error, line = str(e), e.line or getattr(e, "syntax_line", None)
    except RecursionError:
        error = "Your functions call each other too deeply."
    if error is None and world.end is None:
        world.end = "stopped"
        for name in [n for n in rover.defs if n not in rover.called][:1]:
            world.say(f"🧩 {name}() was made with def but never used. Add a "
                      f"line  {name}()  to run it.")
        world.say(ENDED_SHORT[world.mission])
    return {"reached": world.end == "goal", "end": "error" if error else world.end,
            "mission": world.mission,
            "ticks": world.t, "error": error, "line": line,
            "frames": world.frames, "log": world.log, "prints": world.prints,
            "cracked": sorted(world.cracked),
            "sun_width": (variant.get("sun") or {}).get("width", 0),
            "crystals": [len(variant.get("crystals", [])) - len(world.crystals),
                         len(variant.get("crystals", []))],
            "samples": len(world.samples),
            "bumps": world.bumps, "pushes": world.pushes,
            "computed": world.computed,
            "explain": None if error else explain(world, sensors, code),
            "drills": world.drills if "drills" in variant else None,
            "typed": world.typed,
            # A def the program actually ran, for the def star and badge.
            "own_function": bool(rover and rover.called),
            "battery": world.battery if "battery" in rules else None}


# ---- building planets --------------------------------------------------------

def path_map(legs, pad=1):
    """A one-square-wide track from S that follows `legs` [(direction, squares)]
    and ends at the beacon. Everything off the track is rock. Directions are
    0 N, 1 E, 2 S, 3 W. Returns (grid as lists, the track squares in order)."""
    r = c = 0
    track = [(0, 0)]
    for d, n in legs:
        dr, dc = DIRS[d]
        for _ in range(n):
            r, c = r + dr, c + dc
            track.append((r, c))
    top = min(p[0] for p in track) - pad
    left = min(p[1] for p in track) - pad
    rows = max(p[0] for p in track) - top + pad + 1
    cols = max(p[1] for p in track) - left + pad + 1
    track = [(r - top, c - left) for r, c in track]
    grid = [["#"] * cols for _ in range(rows)]
    for r, c in track:
        grid[r][c] = "."
    grid[track[0][0]][track[0][1]] = "S"
    grid[track[-1][0]][track[-1][1]] = "G"
    return grid, track


def strings(grid):
    return ["".join(row) for row in grid]


def open_ground(rows, cols):
    """An empty field: ground with a rock border."""
    return [["#"] * cols] + [["#"] + ["."] * (cols - 2) + ["#"]
                             for _ in range(rows - 2)] + [["#"] * cols]


def boulder_run(pairs, seed):
    """Open ground with a sample at every stop of a rover that drives east
    until the next square is rock, then south until it's rock, `len(pairs)`
    times over. `pairs` are the (east, south) squares of each stretch. A few
    loose boulders lie well away from the way through."""
    r = c = 1
    path, rocks, stops = [(r, c)], [], []
    for east, south in pairs:
        for _ in range(east):
            c += 1
            path.append((r, c))
        rocks.append((r, c + 1))
        stops.append((r, c))
        for _ in range(south):
            r += 1
            path.append((r, c))
        rocks.append((r + 1, c))
        stops.append((r, c))
    rows = r + 4
    cols = max(p[1] for p in path) + 4
    grid = open_ground(rows, cols)
    for rr, cc in rocks:
        grid[rr][cc] = "#"
    rng = random.Random(seed)
    for _ in range(14):
        rr, cc = rng.randrange(1, rows - 1), rng.randrange(1, cols - 1)
        if all(max(abs(rr - a), abs(cc - b)) > 1 for a, b in path + rocks):
            grid[rr][cc] = "#"
    for rr, cc in stops:
        grid[rr][cc] = "*"
    grid[1][1] = "S"
    return strings(grid)


def windy_ledge(legs):
    """A track with craters just east of every square, wherever there's room:
    a gust that catches the rover driving pushes it over the edge."""
    grid, track = path_map(legs)
    for r, c in track:
        if grid[r][c + 1] == "#":
            grid[r][c + 1] = "O"
    return strings(grid)


def sunny(legs, pads):
    """A track with sunny ground at the given track squares (by index)."""
    grid, track = path_map(legs)
    for i in pads:
        r, c = track[i]
        if grid[r][c] == ".":
            grid[r][c] = "+"
    return strings(grid)


def crust_room(rows, cols, seed):
    """An empty crumbling room with a sample somewhere on every row but the
    first, so sweeping it like mowing a lawn collects them all."""
    rng = random.Random(seed)
    grid = open_ground(rows + 2, cols + 2)
    c = 1
    for r in range(2, rows + 1):   # never straight below the last one
        c = rng.choice([x for x in range(1, cols + 1) if x != c])
        grid[r][c] = "*"
    grid[1][1] = "S"
    return strings(grid)


# The 2C ice fields, one per student. Each takes 7 or 8 slides, found by a
# search over random rock layouts and checked in test_planet.py.
FROZEN_LAKES = [
    ["##########",
     "#~G~~#~~~#",
     "#~~~~~~~##",
     "#~#~##~~~#",
     "##~~~~#~~#",
     "#~~~~~~~~#",
     "#~#~~~~~~#",
     "#S~~~#~#~#",
     "##########"],
    ["##########",
     "#~###~~~~#",
     "#~~~~~##~#",
     "#~#~~~~~~#",
     "##~~#~~~~#",
     "#~~~#~~~G#",
     "#~~#~~~~~#",
     "#S~~##~~~#",
     "##########"],
    ["##########",
     "#~~~~~~~~#",
     "#~~~~~~~~#",
     "##~~~~#~##",
     "#~#~#~~~~#",
     "#~G~~~~###",
     "#~~#~#~~##",
     "#S~~~~~~##",
     "##########"],
    ["##########",
     "#~#~~#~~##",
     "#~#G~~~#~#",
     "#~~#~~~~~#",
     "#~#~~~~~##",
     "#~~~~~~~##",
     "#~~~~~~#~#",
     "#S~~##~~~#",
     "##########"],
    ["##########",
     "#~~~G~~~~#",
     "#~~~~#~#~#",
     "#~~~#~~#~#",
     "##~~~~~~~#",
     "#~##~#~~~#",
     "#~~~~~~~##",
     "#S~~#~~~~#",
     "##########"],
    ["##########",
     "#~~####~~#",
     "#~~~~~#~~#",
     "##~~~~~~~#",
     "#~~~~#~G~#",
     "#~~~~~~~~#",
     "#~~~~~~~~#",
     "#S~~#~~###",
     "##########"],
    ["##########",
     "#~##~#~~~#",
     "#~~~~~#~~#",
     "#~~~~~~~~#",
     "#~~~~~G~~#",
     "#~~~####~#",
     "#~#~~~~~~#",
     "#S~~~~~#~#",
     "##########"],
    ["##########",
     "#~~#~~~~~#",
     "#~##~~#~~#",
     "#~~~~~#~~#",
     "#~~##~~~~#",
     "#~G#~~~~~#",
     "###~~~~~~#",
     "#S~~~~~~~#",
     "##########"],
]



def site(key, name, brief, variants, per_student=False, reference="",
         bonus=None, compact=99, coach=None):
    """One site. Every variant is a dict with a "map" and the hidden details
    (wind, sun, portal pairs, battery, the answer to report). `per_student`
    sites give each student their own variant; `reference` is a program that
    clears every variant. `bonus` is the site's challenge star and `compact`
    the most lines of code for the compact star; a variant may set its own of
    either. `coach` walks a field measurement through step by step: an
    `intro` when the site opens, a tip for a run with no report() (`short`),
    and `steps` that go further after each miss."""
    if per_student and "answer" in variants[0]:
        # Each planet knows its classmates' numbers, to spot a copied one.
        for v in variants:
            v["others"] = sorted({w["answer"] for w in variants} - {v["answer"]})
    return {"key": key, "name": name, "brief": brief, "variants": variants,
            "per_student": per_student, "reference": reference,
            "bonus": bonus or {"kind": "no_bump"}, "compact": compact,
            "coach": coach}


# The 1B field: eight samples on a diagonal, loose boulders off it.
STEPS_FIELD = open_ground(11, 11)
for _k in range(2, 10):
    STEPS_FIELD[_k][_k] = "*"
for _r, _c in ((1, 6), (2, 9), (4, 1), (6, 3), (7, 9), (9, 5)):
    STEPS_FIELD[_r][_c] = "#"
STEPS_FIELD[1][1] = "S"
STEPS_FIELD = strings(STEPS_FIELD)

ZONES = [
    {"key": "landing", "name": "Landing Site", "rules": set(),
     "blurb": "Ordinary ground. Learn to drive by compass.",
     "hints": [
         "The rover doesn't turn: it drives by compass. east(3) drives three "
         "squares east (to the right), south() one square down. Count the "
         "squares on the map.",
         "for i in range(8):  repeats the lines pushed in under it 8 times. "
         "Find the piece of the route that repeats.",
         "look(\"east\") says what's on the next square to the east, like "
         "\"rock\". Drive until it's rock:\n\nwhile look(\"east\") != \"rock\":\n"
         "    east()",
     ],
     "sites": [
         site("1a", "Touchdown",
              "Collect the three samples. Drive with north() south() east() west().",
              [{"map": ["############",
                        "#S...#.....#",
                        "#....#..*..#",
                        "#.*..#.....#",
                        "#..........#",
                        "#....##..*.#",
                        "############"]}],
              reference="south(2)\neast()\nsouth()\neast(7)\nsouth()\n"
                        "north(3)\nwest()\n"),
         site("1b", "Crystal Steps",
              "Collect the eight samples. They sit on steps: one square east,"
              " one square south, and again.\n"
              "A for loop repeats the lines pushed in under it. This one "
              "drives east 3 times:\n\n"
              "for i in range(3):\n    east()",
              [{"map": STEPS_FIELD}],
              reference="for i in range(8):\n    east()\n    south()\n"),
         site("1c", "Rock Run",
              "Collect the sample in front of every rock. Your rocks aren't where "
              "anyone else's are, so let look() find them.\n"
              "look(\"east\") says what's on the next square east. This while "
              "loop drives east until that's \"rock\":\n\n"
              "while look(\"east\") != \"rock\":\n    east()",
              [{"map": boulder_run(pairs, i)} for i, pairs in enumerate((
                  [(4, 2), (3, 4), (5, 2), (2, 3)],
                  [(6, 3), (2, 2), (3, 4), (4, 2)],
                  [(3, 4), (5, 3), (2, 2), (3, 3)],
                  [(5, 2), (4, 3), (3, 3), (2, 2)],
                  [(2, 3), (3, 2), (6, 3), (3, 4)],
                  [(4, 4), (2, 3), (4, 2), (5, 3)],
                  [(3, 2), (6, 2), (2, 4), (4, 2)],
                  [(5, 3), (3, 4), (2, 2), (2, 3)]))],
              per_student=True,
              # A route counted off the map is 8 lines; this is 5, so only
              # it is compact.
              reference="for i in range(4):\n"
                        "    while look(\"east\") != \"rock\":\n        east()\n"
                        "    while look(\"south\") != \"rock\":\n        south()\n"),
     ]},
    {"key": "ice", "name": "Ice Field", "rules": {"ice"},
     "blurb": "Shiny ground. Watch closely how the rover moves on it.",
     "hints": [
         "Watch the replay closely. How many squares does ONE east() take "
         "on the shiny ground? x() says which column the rover is on.",
         "On ice, one east() slides until something stops it: rock, or "
         "ordinary ground. You can't stop in the middle of the ice.",
         "Rocks are your brakes. Work backwards from the beacon: which rock "
         "could stop you right next to it? To measure a slide in code:\n\n"
         "before = x()\neast()\nreport(x() - before)",
     ],
     "sites": [
         site("2a", "First Frost",
              "📡 Field measurement: how many squares does ONE east() slide "
              "on your ice? It's not the same length as anyone else's.\n"
              "1. Write east() and press Transmit.\n"
              "2. Watch the replay. Which x does the rover stop on? The x "
              "numbers run along the top of the map.\n"
              "3. It started on x 1, so take 1 away from that x.\n"
              "4. Add a last line with your number, like report(4), and Transmit "
              "again.",
              # Each student's ice is a different length, so a classmate's
              # number is wrong here. 4 and 6 (the old answer) are left out.
              [{"map": ["#" * 14,
                        "#" + "." * 12 + "#",
                        "#S" + "~" * n + "#" + "." * (10 - n) + "#",
                        "#" + "." * 12 + "#",
                        "#" * 14], "answer": n, "old": 6}
               for n in (5, 7, 8, 9)],
              per_student=True,
              reference="east()\nreport(x() - 1)\n",
              coach={
                  "intro": "📡 To measure, use the numbers along the top of "
                           "the map: that's x, the column the rover is on. "
                           "x() tells your code the same number.",
                  "short": "Your rover slid, but no number reached mission "
                           "control. Add a last line: report() with how many "
                           "squares ONE east() slid, like report(4).",
                  "steps": [
                      "Not quite. Play the replay and watch ONE east(): "
                      "where does the rover start, and where does it stop? "
                      "Use the numbers along the top of the map.",
                      "Drag the timeline to the very start: the rover is on "
                      "x 1. Drag it to the end: which x is it on now? The "
                      "slide is the end x take away the start x.",
                      "Let the rover measure it: remember x() before the "
                      "slide, and take it away after.\n\n"
                      "before = x()\neast()\nreport(x() - before)",
                  ]}),
         site("2b", "Glacier",
              "Reach the beacon. It's only two squares away, but the ice "
              "won't let you stop where you want.",
              [{"map": ["#########",
                        "#~~~#~~~#",
                        "#~~~#~~~#",
                        "#~~~~~~~#",
                        "#~###~~~#",
                        "#~~#~~#~#",
                        "#S#G~~~~#",
                        "#########"]}],
              reference="north()\neast()\nsouth()\neast()\nsouth()\nwest()\n"),
         site("2c", "Frozen Lake",
              "Reach the beacon across your own frozen lake. Rocks are the "
              "only way to stop on ice.",
              [{"map": m} for m in FROZEN_LAKES], per_student=True),
     ]},
    {"key": "wind", "name": "Wind Canyon", "rules": {"wind"},
     "blurb": "Something keeps pushing the rover. Watch the replay to see "
              "when.",
     "hints": [
         "Watch WHEN the rover gets pushed. print(tick()) before each "
         "south() and compare the numbers.",
         "A gust comes every few ticks, and it only catches a rover that is "
         "driving. A rover that wait()s holds on. tick() % 5 is 4 just "
         "before a gust that comes every 5 ticks.",
         "Make your own guard, and call it before every square:\n\n"
         "def guard():\n    if tick() % 5 == 4:\n        wait()\n\n"
         "for i in range(6):\n    guard()\n    south()",
     ],
     "sites": [
         site("3a", "Canyon Floor",
              "📡 Field measurement: something pushes the rover. How many "
              "ticks apart are your pushes? Everyone's keep their own time.\n"
              "1. Write south(16) and press Transmit.\n"
              "2. Find the 💨 lines in the telemetry. Each one starts with "
              "its tick.\n"
              "3. Take the first 💨 tick away from the second one.\n"
              "4. Add a last line with your number, like report(3), and Transmit "
              "again.",
              # Each student's gusts keep their own time. 3B's 5 is left out,
              # and south(16) shows two pushes even at 8.
              [{"map": ["########",
                        "#.S....#"] + ["#......#"] * 16 + ["########"],
                "dir": 2, "wind": n, "answer": n, "old": 5}
               for n in (4, 6, 7, 8)],
              per_student=True,
              reference="while x() == 2:\n    south()\nreport(tick())\n",
              coach={
                  "intro": "⏱ Planet time is counted in ticks. Every command "
                           "takes one tick: south() is 1 tick, south(4) is 4 "
                           "ticks, wait() is 1 tick. The tick counter at the "
                           "top left of the map counts them, and tick() tells "
                           "your code which tick it is.",
                  "short": "Your rover drove, but no number reached mission "
                           "control. Watch for the 💨 pushes, then add a last "
                           "line: report() with how many ticks apart they are.",
                  "steps": [
                      "Not quite. In the telemetry, the number at the start "
                      "of each line is the tick it happened on. Find the 💨 "
                      "pushes: which ticks did they come on? Drive far "
                      "enough to see two of them, like south(16).",
                      "The pushes come at the same gap every time. If they "
                      "came on ticks 3 and 6, the gap would be 6 − 3 = 3. "
                      "Find your two 💨 tick numbers and take one away from "
                      "the other.",
                      "Let the rover measure it: keep driving south until "
                      "the first push moves it off its column, then report "
                      "the tick.\n\nwhile x() == 2:\n    south()\nreport(tick())",
                  ]}),
         site("3b", "The Ledge",
              "Drive down the ledge to the beacon without being pushed into a"
              " crater. Here the gusts come every 5 ticks: on ticks 5, 10, 15 "
              "and so on.\n"
              "1. A gust only catches a rover that is driving, so wait() on the "
              "tick just before one: when tick() % 5 is 4.\n"
              "2. Put that check in your own def, and call it before every "
              "single square.\n"
              "3. Drive each part of the ledge one square at a time, with a for "
              "loop.",
              [{"map": windy_ledge([(2, 6), (1, 5), (2, 6), (1, 4), (2, 5)]),
                "dir": 2, "wind": 5}],
              reference="def guard():\n    if tick() % 5 == 4:\n        wait()\n\n"
                        "def go_south(n):\n    for i in range(n):\n"
                        "        guard()\n        south()\n\n"
                        "def go_east(n):\n    for i in range(n):\n"
                        "        guard()\n        east()\n\n"
                        "go_south(6)\ngo_east(5)\ngo_south(6)\ngo_east(4)\n"
                        "go_south(5)\n"),
         site("3c", "Gale Ridge",
              "Reach the beacon without being blown into a crater. Your gusts "
              "and your ridge aren't your classmates': measure your gusts as "
              "on Canyon Floor, then use your number in The Ledge's check.",
              [{"map": windy_ledge(legs), "dir": 2, "wind": n, "legs": legs}
               for legs in ([(2, 5), (1, 7), (2, 4), (1, 3), (2, 7)],
                            [(2, 4), (1, 5), (2, 6), (1, 4), (2, 5)])
               for n in (4, 6, 7, 9)],
              per_student=True),
     ]},
    {"key": "crumble", "name": "Crumbling Crust", "rules": {"crumble"},
     "blurb": "The ground here is thin. Watch what happens to the squares you"
              " drive over.",
     "hints": [
         "Look at the squares the rover has already driven over. What "
         "happens if it drives over one again?",
         "Ground cracks as soon as the rover leaves it, and cracked ground "
         "gives way. Never go back the way you came: find a loop. "
         "look(\"south\") says \"crack\" for a cracked square.",
         "Sweep like mowing a lawn: east to the rock, down one, west to "
         "the rock, down one, and again. You never cross your own tracks:\n\n"
         "while look(\"east\") != \"rock\":\n    east()\nsouth()",
     ],
     "sites": [
         site("4a", "Thin Crust",
              "Grab the sample, then reach the beacon.",
              [{"map": ["###########",
                        "#S.......G#",
                        "#####..####",
                        "#####..####",
                        "#####*.####",
                        "###########"]}],
              reference="east(4)\nsouth(3)\neast()\nnorth(3)\neast(3)\n"),
         site("4b", "Three Pits",
              "Collect the sample at the bottom of each pit, then reach the "
              "beacon. Never drive back over your own tracks.",
              [{"map": ["####################",
                        "#S................G#",
                        "#####..###..###..###",
                        "#####..###..###..###",
                        "#####*.###*.###*.###",
                        "####################"]}],
              reference="def pit():\n    south(3)\n    east()\n    north(3)\n\n"
                        "for i in range(3):\n    east(4)\n    pit()\neast(2)\n"),
         site("4c", "Sample Field",
              "Collect every sample in the field without crossing your own "
              "tracks. Yours are scattered differently from everyone else's.",
              [{"map": crust_room(rows, cols, i)} for i, (rows, cols) in enumerate(
                  [(6, 7), (7, 6), (6, 8), (7, 8), (6, 9), (7, 7), (6, 6), (7, 9)])],
              per_student=True,
              reference="while samples_left() > 0:\n"
                        "    while look(\"east\") != \"rock\":\n        east()\n"
                        "    south()\n"
                        "    while look(\"west\") != \"rock\":\n        west()\n"
                        "    south()\n"),
     ]},
    {"key": "solar", "name": "Solar Valley", "rules": {"battery"},
     "blurb": "Long shadows. Keep an eye on the battery gauge at the top "
              "left.",
     "hints": [
         "print(battery()) as you go. What makes it go down? Does anything "
         "make it go up?",
         "Driving costs 1 battery a square. Waiting is free, and every "
         "tick the rover spends in sunlight adds 2.",
         "Charge until you have enough for the next stretch:\n\n"
         "def charge_to(n):\n    while battery() < n:\n        wait()",
     ],
     "sites": [
         site("5a", "First Light",
              "📡 Field measurement: how much battery does ONE wait() on the "
              "bright ground give?\n"
              "1. Write east() and then wait(), and press Transmit.\n"
              "2. Play the replay and watch the 🔋 gauge at the top left on "
              "the wait(). How much does it go up?\n"
              "3. Add a last line with that number, like report(5), and Transmit "
              "again.",
              [{"map": ["############",
                        "#S++++.....#",
                        "############"], "battery": 12, "answer": 2}],
              reference="east()\nbefore = battery()\nwait()\n"
                        "report(battery() - before)\n",
              coach={
                  "intro": "🔋 The gauge at the top left is the battery, and "
                           "battery() tells your code the same number. Watch "
                           "it as the rover drives and waits.",
                  "short": "No number reached mission control. Drive onto "
                           "the bright ground, wait() for one tick, and "
                           "report() how much the battery went up.",
                  "steps": [
                      "Not quite. Play the replay and watch the 🔋 gauge on "
                      "a wait() in the bright squares. How much does it "
                      "change in that ONE tick?",
                      "Only measure the wait(). Driving uses battery too, so "
                      "print(battery()) just before and just after one "
                      "wait(): the telemetry shows both numbers, and the "
                      "answer is the difference.",
                      "Let the rover measure it: step into the sun, remember "
                      "the battery, wait, then take it away.\n\neast()\n"
                      "before = battery()\nwait()\nreport(battery() - before)",
                  ]}),
         site("5b", "Shadow Steps",
              "Reach the beacon. Driving uses battery, so charge up in each "
              "sunny corner before the long shadow.",
              [{"map": sunny([(1, 12), (2, 5), (3, 16), (2, 5), (1, 20)],
                             [12, 17, 33, 38]), "dir": 1, "battery": 14}],
              reference="def charge_to(n):\n    while battery() < n:\n"
                        "        wait()\n\neast(12)\ncharge_to(5)\nsouth(5)\n"
                        "charge_to(16)\nwest(16)\ncharge_to(5)\nsouth(5)\n"
                        "charge_to(20)\neast(20)\n"),
         site("5c", "Moving Shadows",
              "Drive to the beacon. The sunny patch moves along the valley: "
              "charge while you're in it.",
              [{"map": ["#" * 44, "#S" + "." * 40 + "G#", "#" * 44],
                "battery": 10, "sun": sun}
               # The rover can catch each band before its 10 battery runs out.
               for sun in ({"start": 8, "width": 4, "every": 3},
                           {"start": 5, "width": 3, "every": 2},
                           {"start": 4, "width": 3, "every": 5},
                           {"start": 5, "width": 4, "every": 2},
                           {"start": 3, "width": 4, "every": 5},
                           {"start": 8, "width": 3, "every": 3},
                           {"start": 6, "width": 3, "every": 4},
                           {"start": 8, "width": 3, "every": 5})],
              per_student=True,
              reference="while not at_beacon():\n"
                        "    if in_sun() and battery() < 90:\n        wait()\n"
                        "    else:\n        east()\n"),
     ]},
]

PORTAL_MAP = ["#######################",
              "#S....#..P..#.....#...#",
              "#.....#.....#...P.#.G.#",
              "#.P.P.#.....#.....#.P.#",
              "#.....#.P...#.P...#...#",
              "#######################"]
# The pads on PORTAL_MAP, by field: A is the lander's, D has the beacon. Each
# field has its pads in different places, so the moves for one wiring never
# happen to fit another.
A1, A2, B1, B2, C1, C2, D1 = (3, 2), (3, 4), (1, 9), (4, 8), (4, 14), (2, 16), (3, 20)

ZONES.append(
    {"key": "portals", "name": "Portal Fields", "rules": set(),
     "blurb": "Strange pads, all alike. Drive onto one and see where you come"
              " out.",
     "hints": [
         "Drive onto one pad at a time and read the log: it says the x and "
         "y where the rover came out. Write it down.",
         "Pads work in pairs: go in one, come out of its partner. But some "
         "pads only send one way, and some send nowhere.",
         "Make one function per trip, then chain them:\n\n"
         "def to_middle():\n    south(2)\n    east(3)\n\n"
         "to_middle()\n...",
     ],
     "sites": [
         site("6a", "The Pads",
              "Reach the beacon behind the rock. Drive onto a pad and see "
              "where you come out.",
              [{"map": ["#############",
                        "#S....#.....#",
                        "#.....#..G..#",
                        "#P.P.P#.....#",
                        "#.....#P....#",
                        "#############"],
                "pairs": [[(3, 3), (4, 7)], [(3, 1), (3, 5)]]}],
              reference="east(2)\nsouth(2)\nnorth(2)\neast(2)\n"),
         site("6b", "Relay",
              "Reach the beacon behind two rock walls. Use the pads to get "
              "through.",
              [{"map": ["###################",
                        "#S....#.....#.....#",
                        "#.....#.....#..G..#",
                        "#.P.P.#.P.P.#.....#",
                        "#.....#.....#.P...#",
                        "###################"],
                "pairs": [[(3, 4), (3, 8)], [(3, 10), (4, 14)], [(3, 2), (1, 10)]]}],
              reference="east(3)\nsouth(2)\neast(2)\nnorth(2)\neast()\n"),
         site("6c", "Portal Maze",
              "Reach the beacon. Your seven pads are wired differently from "
              "everyone else's: test each one.",
              [{"map": PORTAL_MAP, "pairs": pairs, "oneway": oneway}
               for pairs, oneway in (
                   ([(A1, B2), (B1, C2)], [(C1, D1), (A2, B1)]),
                   ([(A2, C1), (C2, B1)], [(B2, D1), (A1, C2)]),
                   ([(A1, C2), (C1, B2)], [(B1, D1), (A2, A1)]),
                   ([(A2, B1), (B2, C1)], [(C2, D1), (A1, C1)]),
                   ([(B1, A2), (C1, C2)], [(B2, D1), (A1, C2)]),
                   ([(C2, B2), (B1, A2)], [(C1, D1), (A1, B2)]),
                   ([(A1, B1), (B2, C2)], [(C1, D1), (A2, B2)]),
                   ([(B2, A2), (C1, A1)], [(B1, D1), (C2, C1)]))],
              per_student=True),
     ]})


def open_plain(rows, cols, start, goal, seed):
    """Open ground with loose boulders, none of them on either straight way
    from the lander to the beacon: east or west first, or north or south first."""
    grid = open_ground(rows, cols)
    (sr, sc), (gr, gc) = start, goal
    lanes = {(sr, c) for c in range(min(sc, gc), max(sc, gc) + 1)} | \
            {(gr, c) for c in range(min(sc, gc), max(sc, gc) + 1)} | \
            {(r, sc) for r in range(min(sr, gr), max(sr, gr) + 1)} | \
            {(r, gc) for r in range(min(sr, gr), max(sr, gr) + 1)}
    rng = random.Random(seed)
    for _ in range(14):
        r, c = rng.randrange(1, rows - 1), rng.randrange(1, cols - 1)
        if all(abs(r - a) + abs(c - b) > 1 for a, b in lanes):
            grid[r][c] = "#"
    grid[sr][sc] = "S"
    grid[gr][gc] = "G"
    return strings(grid)


def boulder_plain(seed):
    """A wide field with rock ridges and crater lines between the lander and
    the beacon, in opposite corners. Like Uncharted's planets, without the
    ice, wind and sunshine."""
    rng = random.Random(seed)
    rows, cols = rng.randint(10, 12), rng.randint(20, 24)
    grid = open_ground(rows, cols)
    start = (rng.randint(1, 3), rng.randint(1, 3))
    goal = (rng.randint(rows - 4, rows - 2), rng.randint(cols - 5, cols - 2))
    clear = {(p[0] + dr, p[1] + dc) for p in (start, goal)
             for dr in (-1, 0, 1) for dc in (-1, 0, 1)}

    def put(r, c, ch):
        if 0 < r < rows - 1 and 0 < c < cols - 1 and (r, c) not in clear \
                and grid[r][c] == ".":
            grid[r][c] = ch

    for _ in range(rng.randint(7, 10)):         # rock ridges, 2 to 5 long
        r, c = rng.randrange(1, rows - 1), rng.randrange(1, cols - 1)
        dr, dc = rng.choice(DIRS)
        for i in range(rng.randint(2, 5)):
            put(r + dr * i, c + dc * i, "#")
    for _ in range(rng.randint(2, 4)):          # crater lines, north to south
        r, c = rng.randrange(1, rows - 1), rng.randrange(1, cols - 1)
        for i in range(rng.randint(2, 3)):
            put(r + i, c, "O")
    grid[start[0]][start[1]] = "S"
    grid[goal[0]][goal[1]] = "G"
    if rng.random() < .5:
        grid.reverse()
    if rng.random() < .5:
        grid = [row[::-1] for row in grid]
    return strings(grid)


# Signal Plains comes before Uncharted and takes its ideas one at a time, on
# calm ground: what beacon_x() says, steering by it, then steering round
# rock and craters. Uncharted then only adds the rules from earlier zones.
SIGNAL_STEER = ("while x() < beacon_x():\n    east()\n"
                "while x() > beacon_x():\n    west()\n"
                "while y() < beacon_y():\n    south()\n"
                "while y() > beacon_y():\n    north()\n")
SIGNAL_ROUND = """def safe(way):
    return look(way) != "rock" and look(way) != "crater"

while not at_beacon():
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
"""

ZONES.append(
    {"key": "signal", "name": "Signal Plains", "rules": set(),
     "blurb": "Calm, open ground. A new signal says where the beacon is.",
     "hints": [
         "beacon_x() is the beacon's column, the same numbers along the top "
         "as x(). If x() is smaller, the beacon is to the east:\n\n"
         "while x() < beacon_x():\n    east()",
         "Each plain has its beacon somewhere else. Write one loop for each "
         "way: east while x() is smaller, west while it's bigger, then the "
         "same for y() with south and north.",
         "To go round rock, only drive a way that's safe, and when no good "
         "way is safe, step south (or north) and try again:\n\n"
         "def safe(way):\n    return look(way) != \"rock\" and "
         "look(way) != \"crater\"",
     ],
     "sites": [
         site("7a", "Homing Signal",
              "📡 Field measurement: how many squares east of the lander is "
              "your beacon? It's not where anyone else's is.\n"
              "1. Find the lander's x and the beacon's x. The x numbers run "
              "along the top of the map.\n"
              "2. Take the lander's x away from the beacon's x.\n"
              "3. Write report() with that number, like report(5), and press "
              "Transmit.",
              # Each student's beacon is a different distance away, so a
              # classmate's number is wrong here. 12 (the old answer) is left out.
              [{"map": ["#" * 20,
                        "#" + "." * 18 + "#",
                        "#S" + "." * (n - 1) + "G" + "." * (17 - n) + "#",
                        "#" + "." * 18 + "#",
                        "#" * 20], "answer": n, "old": 12}
               for n in (9, 11, 14, 16)],
              per_student=True,
              reference="report(beacon_x() - x())\n",
              coach={
                  "intro": "🛰 Two new sensors: beacon_x() is the beacon's "
                           "column, numbered like x() along the top of the "
                           "map, and beacon_y() is its row.",
                  "short": "No number reached mission control. Add a line: "
                           "report() with how many squares east the beacon "
                           "is, like report(5).",
                  "steps": [
                      "Not quite. Use the numbers along the top of the map: "
                      "which x is the lander on, and which x is the beacon on?",
                      "The lander is on x 1. Find the beacon's x. The gap is "
                      "the beacon's x take away the lander's x.",
                      "Let the rover work it out: beacon_x() is the beacon's "
                      "column and x() is yours.\n\nreport(beacon_x() - x())",
                  ]}),
         site("7b", "Open Plain",
              "Reach the beacon. Yours isn't where anyone else's is: steer "
              "with x(), y(), beacon_x() and beacon_y().",
              [{"map": open_plain(rows, cols, start, goal, i)}
               for i, (rows, cols, start, goal) in enumerate((
                   (9, 16, (1, 1), (6, 12)), (9, 16, (7, 2), (2, 13)),
                   (9, 16, (1, 14), (6, 3)), (9, 16, (7, 13), (1, 4)),
                   (10, 15, (4, 1), (8, 10)), (10, 15, (1, 7), (8, 9)),
                   (10, 17, (8, 1), (3, 9)), (10, 17, (2, 15), (7, 9))))],
              per_student=True, reference=SIGNAL_STEER),
         site("7c", "Rocky Plain",
              "Reach the beacon across the plain, going round rock and "
              "craters. Yours aren't where anyone else's are.",
              [{"map": boulder_plain(seed)}
               # Fields where only going round gets there, picked by a search.
               for seed in (31, 63, 90, 143, 180, 183, 224, 252)],
              per_student=True, reference=SIGNAL_ROUND),
     ]})


def hop_field(seed):
    """A long field crossed by walls of rock or craters, one square thick and
    wall to wall, with the beacon on the lander's row. Ground beyond the
    beacon, so jumping at anything that isn't ground overshoots it."""
    rng = random.Random(seed)
    rows, cols = 7, rng.randint(22, 26)
    grid = open_ground(rows, cols)
    c = rng.randint(3, 4)
    while c < cols - 5:
        wall = rng.choice("OO#")
        for r in range(1, rows - 1):
            grid[r][c] = wall
        c += rng.randint(2, 4)
    row = rng.randint(1, rows - 2)
    grid[row][1] = "S"
    grid[row][cols - 3] = "G"
    return strings(grid)


# Crater Hops gives the rover a new trick instead of a new rule: jump("east")
# leaps two squares in one tick, over whatever is in between.
ZONES.append(
    {"key": "hops", "name": "Crater Hops", "rules": set(),
     "blurb": "Trenches everywhere. Good thing the rover has a new trick: "
              "jump(\"east\").",
     "hints": [
         "jump(\"east\") leaps two squares east in one tick, right over "
         "whatever is in between: a crater, a rock, anything.",
         "A jump needs somewhere to land: ground two squares away. It can't "
         "land on rock, and landing in a crater is still a fall.",
         "Let a sensor decide when to jump:\n\n"
         "while not at_beacon():\n    if look(\"east\") == \"crater\":\n"
         "        jump(\"east\")\n    else:\n        east()",
     ],
     "sites": [
         site("8a", "The Trench",
              "Jump over the crater trench to the beacon. New command: "
              "jump(\"east\") leaps two squares.",
              [{"map": ["###########",
                        "#.....O...#",
                        "#S....O..G#",
                        "#.....O...#",
                        "###########"]}],
              reference="east(4)\njump(\"east\")\neast(2)\n"),
         site("8b", "Stepping Stones",
              "Jump wall after wall to the beacon. Every hop is the same, so "
              "use a loop.",
              [{"map": ["###################",
                        "#..O..#..O..#..O..#",
                        "#S.O..#..O..#..O.G#",
                        "#..O..#..O..#..O..#",
                        "###################"]}],
              reference="for i in range(5):\n    east()\n    jump(\"east\")\n"
                        "east()\n"),
         site("8c", "Crater Field",
              "Reach the beacon across walls and trenches. Yours aren't where"
              " anyone else's are, so let look() decide when to jump.",
              # Seed 6 left out: its route also fits another field.
              [{"map": hop_field(seed)} for seed in (0, 1, 2, 3, 4, 5, 7, 8)],
              per_student=True,
              reference="while not at_beacon():\n"
                        "    if look(\"east\") == \"crater\" or look(\"east\") == \"rock\":\n"
                        "        jump(\"east\")\n    else:\n        east()\n"),
     ]})


def belt_steps(n):
    """1B's steps again, but on belts: east() lands on a belt that carries the
    rover two more squares to a sample, and south() on one that carries it
    down another. `n` steps."""
    grid = open_ground(2 * n + 3, 3 * n + 3)
    r = c = 1
    for _ in range(n):
        grid[r][c + 1] = grid[r][c + 2] = ">"
        grid[r][c + 3] = "*"
        grid[r + 1][c + 3] = "v"
        r, c = r + 2, c + 3
    grid[1][1] = "S"
    return strings(grid)


def belt_field(seed):
    """Crater Hops' long field, but most walls are belts running to a crater
    at their end: step onto one and it carries the rover in."""
    rng = random.Random(seed)
    rows, cols = 7, rng.randint(22, 26)
    grid = open_ground(rows, cols)
    walls, c = [], rng.randint(3, 4)
    while c < cols - 5:
        walls.append([c, rng.choice("v^vO")])
        c += rng.randint(2, 4)
    if not any(w in "v^" for _, w in walls):
        walls[0][1] = "v"
    for c, w in walls:
        for r in range(1, rows - 1):
            grid[r][c] = w
        if w == "v":
            grid[rows - 2][c] = "O"
        if w == "^":
            grid[1][c] = "O"
    row = rng.randint(2, rows - 3)   # where every belt wall is still a belt
    grid[row][1] = "S"
    grid[row][cols - 3] = "G"
    return strings(grid)


def quarry_field(seed):
    """A long field crossed by rock walls two squares thick (too thick to
    jump: drill through) and crater trenches (can't be drilled: jump). Returns
    the map and the drills it needs, plus one to spare."""
    rng = random.Random(seed)
    rows, cols = 7, rng.randint(22, 26)
    grid = open_ground(rows, cols)
    kinds, c = [], rng.randint(3, 4)
    while c < cols - 6:
        kind = rng.choice("##O") if len(kinds) > 1 else "#O"[len(kinds) % 2]
        kinds.append(kind)
        width = 2 if kind == "#" else 1
        for r in range(1, rows - 1):
            for w in range(width):
                grid[r][c + w] = kind
        c += width + rng.randint(1, 3)
    row = rng.randint(1, rows - 2)
    grid[row][1] = "S"
    grid[row][cols - 3] = "G"
    return {"map": strings(grid), "drills": 2 * kinds.count("#") + 1}


def gate_yard(seed):
    """Open ground with the beacon in a rock box. Its gate faces the rest of
    the yard, and the key lies somewhere out there, as does the lander."""
    rng = random.Random(seed)
    rows, cols = rng.randint(9, 10), rng.randint(14, 17)
    grid = open_ground(rows, cols)
    gr, gc = rows - 3, rng.randint(3, cols - 4)
    for dr in (-1, 0, 1):
        for dc in (-1, 0, 1):
            grid[gr + dr][gc + dc] = "#"
    grid[gr][gc] = "G"
    grid[gr - 1][gc] = "D"
    spots = [(r, c) for r in range(1, gr - 2) for c in range(1, cols - 1)]
    (sr, sc), (kr, kc) = rng.sample(spots, 2)
    while abs(sr - kr) + abs(sc - kc) < 6:   # the key is a trip away
        (sr, sc), (kr, kc) = rng.sample(spots, 2)
    grid[sr][sc] = "S"
    grid[kr][kc] = "k"
    if rng.random() < .5:
        grid.reverse()
    if rng.random() < .5:
        grid = [row[::-1] for row in grid]
    return strings(grid)


def flag_map(rows, cols, start, goal, flags):
    """Open ground with numbered flags, in order, at `flags`."""
    grid = open_ground(rows, cols)
    for n, (r, c) in enumerate(flags, 1):
        grid[r][c] = str(n)
    grid[start[0]][start[1]] = "S"
    grid[goal[0]][goal[1]] = "G"
    return strings(grid)


def relay_field(seed):
    """Open ground with rock ridges, four flags and the beacon."""
    rng = random.Random(seed)
    rows, cols = rng.randint(9, 10), rng.randint(14, 17)
    grid = open_ground(rows, cols)
    inside = [(r, c) for r in range(1, rows - 1) for c in range(1, cols - 1)]
    start, goal, *flags = rng.sample(inside, 6)
    keep = {start, goal, *flags}
    for _ in range(rng.randint(4, 6)):           # rock ridges, 2 or 3 long
        r, c = rng.choice(inside)
        dr, dc = rng.choice(DIRS)
        for i in range(rng.randint(2, 3)):
            if (r + dr * i, c + dc * i) in inside and (r + dr * i, c + dc * i) not in keep:
                grid[r + dr * i][c + dc * i] = "#"
    for n, (r, c) in enumerate(flags, 1):
        grid[r][c] = str(n)
    grid[start[0]][start[1]] = "S"
    grid[goal[0]][goal[1]] = "G"
    return strings(grid)


# Steering to a square, made into a function: Signal Plains' four loops with
# the square passed in. Gate Station uses it twice, the Flag Relay in a loop.
GO_TO = """def go_to(tx, ty):
    while x() < tx:
        east()
    while x() > tx:
        west()
    while y() < ty:
        south()
    while y() > ty:
        north()

"""
RELAY_ROUND = SIGNAL_ROUND.replace("beacon_x", "next_x").replace("beacon_y", "next_y")


def relay_fields():
    """Eight relay fields where steering round the rock reaches every flag
    and the beacon, but steering straight at them doesn't."""
    fields, seed = [], 0
    while len(fields) < 8:
        m = relay_field(seed)
        seed += 1
        if drive(RELAY_ROUND, {"map": m}, set(), RELAY_ZONE)["reached"] and \
                not drive(GO_TO + "while not at_beacon():\n    go_to(next_x(), next_y())\n",
                          {"map": m}, set(), RELAY_ZONE)["reached"]:
            fields.append(m)
    return fields


# Four zones that each give the rover one new thing to work with, told and
# drawn on the map rather than hidden: belts, a drill, keys and gates, flags.
# Each has four sites: A tries the new thing once, B uses it with a choice to
# make, C repeats it (so a loop or def earns the ✂️ star), and D gives every
# student their own planet.
ZONES.append(
    {"key": "belts", "name": "Conveyor Works", "rules": set(),
     "blurb": "Belts! Drive onto one and it carries the rover the way its "
              "arrows point.",
     "new": {"icon": "🛤", "what": "Belts carry the rover the way their arrows "
                                    "point, right to the end, in one tick. "
                                    "look() says \"belt\".",
             "example": "east(2)"},
     "hints": [
         "Follow the arrows with your finger: where does the belt end? The "
         "rover lands on the square just after the last arrow.",
         "You don't have to ride every belt. jump(\"east\") hops right over "
         "one, the same as over a crater.",
         "Let a sensor decide when to jump:\n\n"
         "while not at_beacon():\n    if look(\"east\") == \"belt\":\n"
         "        jump(\"east\")\n    else:\n        east()",
     ],
     "sites": [
         site("9a", "First Ride",
              "Drive onto the belt and let it carry you to the beacon. Try  east(2)",
              [{"map": ["##########",
                        "#S.>>>>v.#",
                        "#......v.#",
                        "#####..v.#",
                        "#G<<<<<<.#",
                        "##########"]}],
              reference="east(2)\n"),
         site("9b", "Two Belts",
              "Pick the belt that goes the right way, then grab the sample "
              "and reach the beacon.",
              [{"map": ["##############",
                        "#v<<<<S>>>>>v#",
                        "#v##########v#",
                        "#v#.....*..#v#",
                        "#>>>>......#v#",
                        "#.........G#O#",
                        "##############"]}],
              reference="west()\nnorth()\neast(3)\nsouth(2)\neast(2)\n"),
         site("9c", "Belt Steps",
              "Collect the five samples. Each step is the same: east() onto a "
              "belt, then south() onto another.",
              [{"map": belt_steps(5)}],
              reference="for i in range(5):\n    east()\n    south()\n"),
         site("9d", "Cross Belts",
              "Reach the beacon. Belts cross your way and run into craters: "
              "jump over them. Yours aren't where anyone else's are.",
              [{"map": belt_field(seed)} for seed in (0, 1, 2, 3, 4, 5, 6, 7)],
              per_student=True,
              reference="while not at_beacon():\n"
                        "    if look(\"east\") == \"belt\" or look(\"east\") == \"crater\":\n"
                        "        jump(\"east\")\n    else:\n        east()\n"),
     ]})

ZONES.append(
    {"key": "drill", "name": "The Quarry", "rules": set(),
     "blurb": "Rock everywhere. The rover has a drill now, but only a few "
              "drill bits.",
     "new": {"icon": "⛏", "what": "drill(\"east\") turns the rock next to the "
                                   "rover into ground. Each site gives you a "
                                   "few drills: drills_left() counts them.",
             "example": "drill(\"east\")"},
     "hints": [
         "drill(\"east\") drills the square right next to the rover, then "
         "you still have to drive onto it with east().",
         "Count your drills before you start (the gauge at the top). If "
         "there's a way round a wall, save your drill for one you can't "
         "go round.",
         "Three choices, one for each kind of square:\n\n"
         "if look(\"east\") == \"rock\":\n    drill(\"east\")\n"
         "elif look(\"east\") == \"crater\":\n    jump(\"east\")\nelse:\n    east()",
     ],
     "sites": [
         site("10a", "First Drill",
              "A rock wall stands between you and the beacon. Drive up to it, "
              "drill(\"east\"), and drive on.",
              [{"map": ["###########",
                        "#....#....#",
                        "#S...#...G#",
                        "#....#....#",
                        "###########"], "drills": 1}],
              reference="east(3)\ndrill(\"east\")\neast(5)\n"),
         site("10b", "Drill or Go Round",
              "Three walls and only 2 drills. One wall has a gap: go round "
              "that one.",
              [{"map": ["################",
                        "#...#...#...#..#",
                        "#S..#...#...#.G#",
                        "#...#.......#..#",
                        "################"], "drills": 2}],
              reference="east(2)\ndrill(\"east\")\neast(4)\nsouth()\neast(4)\n"
                        "north()\ndrill(\"east\")\neast(3)\n"),
         site("10c", "Tunnel",
              "Drill a tunnel to the beacon. Every other square is rock: drill, "
              "drive two, and again.",
              [{"map": ["###############",
                        "###############",
                        "#S#.#.#.#.#.#G#",
                        "###############",
                        "###############"], "drills": 8}],
              reference="for i in range(6):\n    drill(\"east\")\n    east(2)\n"),
         site("10d", "Your Quarry",
              "Reach the beacon through thick rock walls and crater trenches. "
              "Yours aren't where anyone else's are.",
              [quarry_field(seed) for seed in (0, 1, 2, 3, 4, 5, 6, 7)],
              per_student=True,
              reference="while not at_beacon():\n"
                        "    if look(\"east\") == \"rock\":\n        drill(\"east\")\n"
                        "    elif look(\"east\") == \"crater\":\n        jump(\"east\")\n"
                        "    else:\n        east()\n"),
     ]})

ZONES.append(
    {"key": "gates", "name": "Gate Station", "rules": set(),
     "blurb": "Locked gates. Drive over a key to pick it up, and a gate "
              "opens when you drive into it with a key.",
     "new": {"icon": "🔑", "what": "Drive over a 🔑 to pick it up. Drive into a "
                                   "🚪 gate with a key and it opens (the key is "
                                   "used up). has_key() is True when you hold one.",
             "example": "print(has_key())"},
     "hints": [
         "A gate without a key is like rock: the rover stops. Get the key "
         "first, then drive into the gate.",
         "Each key opens one gate. key_x() and key_y() say where the nearest "
         "key is, numbered like x() and y().",
         "Steer to the key, then to the beacon, with one function for both:\n\n"
         "def go_to(tx, ty):\n    while x() < tx:\n        east()\n    ...\n\n"
         "go_to(key_x(), key_y())\ngo_to(beacon_x(), beacon_y())",
     ],
     "sites": [
         site("11a", "The Gate",
              "The key is on your way. Drive east over it, through the gate, "
              "to the beacon.",
              [{"map": ["#############",
                        "#.....#.....#",
                        "#S.k..D...G.#",
                        "#.....#.....#",
                        "#############"]}],
              reference="east(9)\n"),
         site("11b", "Key First",
              "The gate is locked. Fetch the key from the corner first, then "
              "go through to the beacon.",
              [{"map": ["#############",
                        "#..k..#.....#",
                        "#.....#.....#",
                        "#S....D...G.#",
                        "#############"]}],
              reference="north(2)\neast(2)\nsouth(2)\neast(7)\n"),
         site("11c", "Three Rooms",
              "Three rooms, three gates, a key in each room. Every room is the "
              "same, so make one function for a room and repeat it.",
              [{"map": ["#####################",
                        "#.k..#.k..#.k..#....#",
                        "#....#....#....#....#",
                        "#S...D....D....D..G.#",
                        "#####################"]}],
              reference="def room():\n    east()\n    north(2)\n    south(2)\n"
                        "    east(4)\n\nfor i in range(3):\n    room()\neast(2)\n"),
         site("11d", "Your Key",
              "Get the key, then reach the beacon behind its gate. Your key "
              "and beacon aren't where anyone else's are: key_x() and key_y() "
              "say where the key is.",
              [{"map": gate_yard(seed)} for seed in (0, 1, 2, 3, 4, 5, 6, 7)],
              per_student=True,
              reference=GO_TO + "go_to(key_x(), key_y())\n"
                                "go_to(beacon_x(), beacon_y())\n"),
     ]})

ZONES.append(
    {"key": "relay", "name": "Flag Relay", "rules": set(),
     "blurb": "Numbered flags. Drive over them in order, 1 first, then reach "
              "the beacon.",
     "new": {"icon": "🚩", "what": "Drive over the flags in order: 1, then 2, "
                                   "then 3. next_x() and next_y() say where the "
                                   "next one is (the beacon, once they're all done).",
             "example": "print(next_x(), next_y())"},
     "hints": [
         "A flag only counts when it's the next one. Driving over flag 3 "
         "before flag 2 doesn't count, and that's fine: come back later.",
         "next_x() is the next flag's column, like beacon_x() was the "
         "beacon's. Steer to it with the same while loops.",
         "Make steering a function, and let the flags tell it where to go:\n\n"
         "def go_to(tx, ty):\n    while x() < tx:\n        east()\n    ...\n\n"
         "while not at_beacon():\n    go_to(next_x(), next_y())",
     ],
     "sites": [
         site("12a", "First Flags",
              "Drive over flags 1, 2 and 3, then reach the beacon.",
              [{"map": ["############",
                        "#S..1..2..3#",
                        "#..........#",
                        "#.........G#",
                        "############"]}],
              reference="east(9)\nsouth(2)\n"),
         site("12b", "Zig-Zag",
              "Four flags, all over the field. Visit them in order, 1 to 4, "
              "then the beacon.",
              [{"map": ["#############",
                        "#S....3.....#",
                        "#...........#",
                        "#.1.....4...#",
                        "#...........#",
                        "#.....2....G#",
                        "#############"]}],
              reference="south(2)\neast()\nsouth(2)\neast(4)\nnorth(4)\n"
                        "south(2)\neast(2)\nsouth(2)\neast(3)\n"),
         site("12c", "Long Relay",
              "Seven flags. Steering to each one by hand is long: make a "
              "go_to(tx, ty) function and let next_x() and next_y() fill it in.",
              [{"map": flag_map(9, 15, (1, 1), (1, 12),
                                [(2, 3), (6, 2), (7, 8), (2, 9), (4, 12), (7, 13), (5, 6)])}],
              reference=GO_TO + "while not at_beacon():\n"
                                "    go_to(next_x(), next_y())\n"),
         site("12d", "Your Relay",
              "Four flags and the beacon, with rock in the way. Yours aren't "
              "where anyone else's are. Steer round the rock.",
              [{"map": m} for m in relay_fields()],
              per_student=True, reference=RELAY_ROUND),
     ]})


def boulder_lane(seed):
    """A long field crossed by crater trenches. A one-wide trench can be
    jumped; a two-wide one has a boulder in front of it on the lander's row,
    to push into the near half before jumping the rest."""
    rng = random.Random(seed)
    rows, cols = 7, rng.randint(22, 26)
    grid = open_ground(rows, cols)
    row = rng.randint(1, rows - 2)
    kinds, c = [], rng.randint(3, 4)
    while c < cols - 6:
        kind = rng.choice("BBO") if len(kinds) > 1 else "BO"[len(kinds) % 2]
        kinds.append(kind)
        if kind == "B":
            for r in range(1, rows - 1):
                grid[r][c + 1] = grid[r][c + 2] = "O"
            grid[row][c] = "B"
            c += 3 + rng.randint(1, 2)
        else:
            for r in range(1, rows - 1):
                grid[r][c] = "O"
            c += 1 + rng.randint(1, 3)
    grid[row][1] = "S"
    grid[row][cols - 3] = "G"
    return strings(grid)


def laser_steps(pairs):
    """Steps east and south with a sample at every corner, each corner one
    square short of the rock that ends its stretch: east(distance("east") - 1)."""
    r = c = 1
    rocks, stops = [], []
    for east, south in pairs:
        c += east
        rocks.append((r, c + 2))
        stops.append((r, c))
        r += south
        rocks.append((r + 2, c))
        stops.append((r, c))
    grid = open_ground(r + 4, max(p[1] for p in rocks) + 2)
    for rr, cc in rocks:
        grid[rr][cc] = "#"
    for rr, cc in stops:
        grid[rr][cc] = "*"
    grid[1][1] = "S"
    return strings(grid)


def laser_lane(seed):
    """A long field crossed by walls of rock and crater trenches, one square
    thick, with the beacon on the last square before the far edge: drive up
    to each one with distance() and jump it."""
    rng = random.Random(seed)
    rows, cols = 7, rng.randint(22, 26)
    grid = open_ground(rows, cols)
    kinds, c = [], rng.randint(3, 5)
    while c < cols - 4:
        kind = rng.choice("#O") if len(kinds) > 1 else "#O"[len(kinds) % 2]
        kinds.append(kind)
        for r in range(1, rows - 1):
            grid[r][c] = kind
        c += 1 + rng.randint(2, 4)
    row = rng.randint(1, rows - 2)
    grid[row][1] = "S"
    grid[row][cols - 2] = "G"
    return strings(grid)


def cargo_field(seed):
    """Open ground with home somewhere on it and six samples around."""
    rng = random.Random(seed)
    rows, cols = rng.randint(9, 10), rng.randint(13, 16)
    grid = open_ground(rows, cols)
    inside = [(r, c) for r in range(1, rows - 1) for c in range(1, cols - 1)]
    home, *samples = rng.sample(inside, 7)
    for r, c in samples:
        grid[r][c] = "*"
    grid[home[0]][home[1]] = "H"
    return strings(grid)


# Three more zones that build on the four before: pushing (with Crater Hops'
# loop), measuring (numbers from a sensor, worked on with - 1), and carrying
# (a counter, and go_to() from Gate Station and the Flag Relay).
ZONES.append(
    {"key": "push", "name": "Boulder Yard", "rules": set(),
     "blurb": "Boulders! Drive into one and the rover pushes it. Push it into "
              "a crater and the crater is filled in.",
     "new": {"icon": "🪨", "what": "Drive into a boulder to push it one square. "
                                   "Push it into a crater and you can drive over. "
                                   "It won't move if something is behind it. "
                                   "look() says \"boulder\".",
             "example": "east(8)"},
     "hints": [
         "Push from the side you want it to go away from: to push a boulder "
         "south, drive into it from the north.",
         "A trench two squares wide is too wide to jump. Push a boulder into "
         "the near half, drive onto it, then jump the other half.",
         "Driving into a boulder pushes it, so only craters need a jump:\n\n"
         "while not at_beacon():\n    if look(\"east\") == \"crater\":\n"
         "        jump(\"east\")\n    else:\n        east()",
     ],
     "sites": [
         site("13a", "First Push",
              "Push the boulder into the crater, then drive over to the beacon. "
              "Try  east(8)",
              [{"map": ["###########",
                        "#....O....#",
                        "#S.B.O...G#",
                        "#....O....#",
                        "###########"]}],
              reference="east(8)\n"),
         site("13b", "Push South",
              "The trench is two squares wide: too far to jump. Push the boulder "
              "into it from above, then jump the rest.",
              [{"map": ["#########",
                        "#S......#",
                        "#...B...#",
                        "#.......#",
                        "#OOOOOOO#",
                        "#OOOOOOO#",
                        "#...G...#",
                        "#########"]}],
              reference="east(3)\nsouth(3)\njump(\"south\")\n"),
         site("13c", "Boulder Steps",
              "Four wide trenches, a boulder before each. Every one is the same: "
              "push, step, jump.",
              [{"map": ["####################",
                        "#.OO..OO..OO..OO...#",
                        "#SBOO.BOO.BOO.BOO.G#",
                        "#.OO..OO..OO..OO...#",
                        "####################"]}],
              reference="for i in range(4):\n    east(2)\n    jump(\"east\")\neast()\n"),
         site("13d", "Your Boulders",
              "Reach the beacon across wide and narrow trenches. Yours aren't "
              "where anyone else's are.",
              [{"map": boulder_lane(seed)} for seed in (0, 1, 2, 3, 4, 5, 6, 7)],
              per_student=True,
              reference="while not at_beacon():\n"
                        "    if look(\"east\") == \"crater\":\n        jump(\"east\")\n"
                        "    else:\n        east()\n"),
     ]})

ZONES.append(
    {"key": "laser", "name": "Laser Range", "rules": set(),
     "blurb": "A laser on the rover measures how far it can drive. No more "
              "counting squares.",
     "new": {"icon": "🔦", "what": "distance(\"east\") is how many squares the "
                                   "rover can drive east before rock, a crater, "
                                   "a boulder or a gate. Put it inside a drive.",
             "example": "east(distance(\"east\"))"},
     "hints": [
         "distance(\"east\") is a number, so it can go inside the ( ) of a "
         "drive: east(distance(\"east\")) drives right up to the next thing.",
         "You can do sums with it. To stop one square short of the rock:\n\n"
         "east(distance(\"east\") - 1)",
         "Drive up to it, jump it, and again:\n\n"
         "while not at_beacon():\n    east(distance(\"east\"))\n    jump(\"east\")",
     ],
     "sites": [
         site("14a", "First Laser",
              "Drive to the beacon at the far end without counting. Try  "
              "east(distance(\"east\"))",
              [{"map": ["################",
                        "#..............#",
                        "#S............G#",
                        "#..............#",
                        "################"]}],
              reference="east(distance(\"east\"))\n"),
         site("14b", "Crater Edge",
              "Two trenches on the way. Drive up to each edge with distance(), "
              "then jump.",
              [{"map": ["################",
                        "#......O...O...#",
                        "#S.....O...O..G#",
                        "#......O...O...#",
                        "################"]}],
              reference="while not at_beacon():\n    east(distance(\"east\"))\n"
                        "    jump(\"east\")\n"),
         site("14c", "Laser Steps",
              "Collect the samples on the steps. Each one is one square before "
              "the rock, so drive distance() - 1.",
              [{"map": laser_steps([(4, 2), (3, 3), (5, 2)])}],
              reference="for i in range(3):\n    east(distance(\"east\") - 1)\n"
                        "    south(distance(\"south\") - 1)\n"),
         site("14d", "Your Range",
              "Reach the beacon at the far end, past walls and trenches. Yours "
              "aren't where anyone else's are.",
              [{"map": laser_lane(seed)} for seed in (0, 1, 2, 3, 4, 5, 6, 7)],
              per_student=True,
              reference="while not at_beacon():\n    east(distance(\"east\"))\n"
                        "    jump(\"east\")\n"),
     ]})

ZONES.append(
    {"key": "cargo", "name": "Cargo Run", "rules": set(),
     "blurb": "Bring the samples home to 📦. The rover only has room for 3 at "
              "a time.",
     "new": {"icon": "📦", "what": "Samples go in the cargo bay, 3 at most, and "
                                   "count when you bring them home to 📦. cargo() "
                                   "says how many you carry; home_x() and home_y() "
                                   "say where home is.",
             "example": "print(cargo())"},
     "hints": [
         "With 3 on board the bay is full: the rover drives over a sample "
         "and leaves it. Go home, then come back for the rest.",
         "for i in range(4):  counts i = 0, 1, 2, 3. Use i inside the loop "
         "to go one row further each time, like  south(i).",
         "Decide each trip with an if, and steer with go_to():\n\n"
         "while True:\n    if cargo() == 3 or samples_left() == 0:\n"
         "        go_to(home_x(), home_y())\n    else:\n"
         "        go_to(sample_x(), sample_y())",
     ],
     "sites": [
         site("15a", "First Load",
              "Pick up the three samples and bring them home to 📦. Try  "
              "east(7)  then  west(7)",
              [{"map": ["############",
                        "#..........#",
                        "#H..*.*.*..#",
                        "#..........#",
                        "############"]}],
              reference="east(7)\nwest(7)\n"),
         site("15b", "Two Trips",
              "Six samples, but room for only 3 at a time. Bring one row home, "
              "then go back for the other.",
              [{"map": ["############",
                        "#H..*.*.*..#",
                        "#..........#",
                        "#...*.*.*..#",
                        "############"]}],
              reference="east(7)\nwest(7)\nsouth(2)\neast(7)\nwest(7)\nnorth(2)\n"),
         site("15c", "Shuttle",
              "Four rows of samples, one trip each. Every trip goes one row "
              "further down: use the loop's i.",
              [{"map": ["#########",
                        "#H.*.*.*#",
                        "#..*.*.*#",
                        "#..*.*.*#",
                        "#..*.*.*#",
                        "#########"]}],
              reference="for i in range(4):\n    south(i)\n    east(6)\n"
                        "    west(6)\n    north(i)\n"),
         site("15d", "Your Cargo",
              "Bring all six samples home, 3 at a time. Your home and samples "
              "aren't where anyone else's are.",
              [{"map": cargo_field(seed)} for seed in (0, 1, 2, 3, 4, 5, 6, 7)],
              per_student=True,
              reference=GO_TO + "while True:\n"
                                "    if cargo() == 3 or samples_left() == 0:\n"
                                "        go_to(home_x(), home_y())\n"
                                "    else:\n"
                                "        go_to(sample_x(), sample_y())\n"),
     ]})


# Each site's challenge star and compact-code star. Crystals sit on a fixed
# site's only planet; on the per-student lakes and portal mazes the compact
# target follows that student's own shortest route. Where the star needs a
# loop, def or sensor, the target leaves up to 2 spare lines over the
# shortest program, but stays under a route counted out by hand.
CHALLENGES = {
    "1a": {"bonus": {"kind": "crystals"}, "compact": 7, "crystals": [(1, 10)]},
    "1b": {"bonus": {"kind": "def"}, "compact": 3},
    # Counting squares off your own map works, so the star wants look().
    "1c": {"bonus": {"kind": "everywhere", "of": "rock run"}, "compact": 7},
    "2a": {"bonus": {"kind": "computed"}, "compact": 3},
    "2b": {"bonus": {"kind": "crystals"}, "compact": 6, "crystals": [(1, 7)]},
    "2c": {"bonus": {"kind": "no_bump"}, "compact": [8, 8, 8, 9, 8, 8, 8, 8]},
    "3a": {"bonus": {"kind": "computed"}, "compact": 3},
    "3b": {"bonus": {"kind": "no_push"}, "compact": 16},
    "3c": {"bonus": {"kind": "no_push"}, "compact": 17},
    "4a": {"bonus": {"kind": "ticks", "max": 14}, "compact": 5},
    "4b": {"bonus": {"kind": "def"}, "compact": 10},
    "4c": {"bonus": {"kind": "no_bump"}, "compact": 9},
    "5a": {"bonus": {"kind": "computed"}, "compact": 4},
    "5b": {"bonus": {"kind": "ticks", "max": 80}, "compact": 14},
    "5c": {"bonus": {"kind": "battery", "min": 30}, "compact": 7},
    "6a": {"bonus": {"kind": "crystals"}, "compact": 4, "crystals": [(4, 1)]},
    "6b": {"bonus": {"kind": "ticks", "max": 8}, "compact": 5},
    "6c": {"bonus": {"kind": "no_bump"}, "compact": [8, 7, 8, 6, 8, 7, 8, 8]},
    "7a": {"bonus": {"kind": "computed"}, "compact": 2},
    "7b": {"bonus": {"kind": "everywhere"}, "compact": 10},
    "7c": {"bonus": {"kind": "everywhere"}, "compact": 17},
    "8a": {"bonus": {"kind": "ticks", "max": 4}, "compact": 3},
    "8b": {"bonus": {"kind": "def"}, "compact": 4},
    "8c": {"bonus": {"kind": "everywhere", "of": "field"}, "compact": 7},
    "9a": {"bonus": {"kind": "ticks", "max": 2}, "compact": 2},
    "9b": {"bonus": {"kind": "ticks", "max": 9}, "compact": 6},
    "9c": {"bonus": {"kind": "def"}, "compact": 3},
    "9d": {"bonus": {"kind": "everywhere", "of": "field"}, "compact": 7},
    "10a": {"bonus": {"kind": "no_bump"}, "compact": 3},
    "10b": {"bonus": {"kind": "no_bump"}, "compact": 8},
    "10c": {"bonus": {"kind": "drills", "min": 2}, "compact": 3},
    "10d": {"bonus": {"kind": "drills", "min": 1}, "compact": 9},
    "11a": {"bonus": {"kind": "no_bump"}, "compact": 2},
    "11b": {"bonus": {"kind": "no_bump"}, "compact": 4},
    "11c": {"bonus": {"kind": "def"}, "compact": 9},
    "11d": {"bonus": {"kind": "everywhere", "of": "yard"}, "compact": 13},
    "12a": {"bonus": {"kind": "no_bump"}, "compact": 2},
    "12b": {"bonus": {"kind": "no_bump"}, "compact": 9},
    "12c": {"bonus": {"kind": "def"}, "compact": 13},
    "12d": {"bonus": {"kind": "everywhere", "of": "field"}, "compact": 17},
    "13a": {"bonus": {"kind": "ticks", "max": 8}, "compact": 2},
    "13b": {"bonus": {"kind": "no_bump"}, "compact": 3},
    "13c": {"bonus": {"kind": "def"}, "compact": 6},
    "13d": {"bonus": {"kind": "everywhere", "of": "field"}, "compact": 7},
    "14a": {"bonus": {"kind": "measured"}, "compact": 2},
    "14b": {"bonus": {"kind": "measured"}, "compact": 5},
    "14c": {"bonus": {"kind": "measured"}, "compact": 5},
    "14d": {"bonus": {"kind": "everywhere", "of": "field"}, "compact": 5},
    "15a": {"bonus": {"kind": "ticks", "max": 14}, "compact": 2},
    "15b": {"bonus": {"kind": "no_bump"}, "compact": 6},
    "15c": {"bonus": {"kind": "def"}, "compact": 7},
    "15d": {"bonus": {"kind": "everywhere", "of": "field"}, "compact": 16},
}
for _zone in ZONES:
    for _s in _zone["sites"]:
        _c = CHALLENGES[_s["key"]]
        _s["bonus"] = _c["bonus"]
        if isinstance(_c["compact"], list):
            for _v, _n in zip(_s["variants"], _c["compact"]):
                _v["compact"] = _n
        else:
            _s["compact"] = _c["compact"]
        if "crystals" in _c:
            _s["variants"][0]["crystals"] = _c["crystals"]


# A hint for a star still to earn: shown when a student comes back to a site
# they've completed, and after a run. It says which idea gets the star, not
# the code. Bonus stars have one hint per kind unless a site needs its own.
BONUS_TIPS = {
    "crystals": "💎 The crystal isn't on the way. Find it on the map and add a "
                "detour that drives over it.",
    "def": "🧩 Find lines that repeat. Put them under  def name():  and call "
           "name() where they were. The def has to run to count.",
    "no_bump": "🧱 Watch the replay for the 🧱 in the telemetry. Make that drive "
               "stop one square sooner, or check look() before you move.",
    "no_push": "💨 Note the ticks the gusts came on. wait() on the tick just "
               "before each one, and the rover holds on.",
    "computed": "🔢 Put sensors inside report() instead of a typed number, so "
                "the rover works it out.",
    "everywhere": "🌍 Your code is also tried on everyone else's {of}. Steer with "
                  "sensors instead of counted squares. The telemetry says how "
                  "many it reached.",
    "ticks": "⚡ Every square and every wait() is a tick. Find a quicker way.",
    "drills": "⛏ Only drill a wall you can't go round. Every drill() you skip is "
              "one to spare.",
    "measured": "🔢 Put distance() inside the ( ) instead of a number you "
                "counted, like  east(distance(\"east\")).",
    "battery": "🔋 Charge for longer in the sun before you leave it.",
}
STAR_TIPS = {
    "1a": {"bonus": "💎 The crystal is in the top right corner. Add a detour "
                    "that drives over it.",
           "compact": "One line can drive a whole straight stretch: east(7) "
                      "instead of seven east() lines. 7 lines means 7 straight "
                      "drives, so pick the order of samples with the fewest turns."},
    "1b": {"compact": "The steps repeat: east(), then south(), 8 times. A for "
                      "loop writes them only once."},
    "1c": {"compact": "Counting squares takes a line for every drive. A while "
                      "loop with look() drives up to the next rock however "
                      "far it is. One loop east and one loop south, repeated "
                      "4 times, reaches every sample."},
    "2a": {"compact": "Drive once, then report(). Delete any other lines."},
    "2b": {"bonus": "💎 The crystal is in the top right corner. A slide stops "
                    "against rock: find one that stops on the crystal.",
           "compact": "Every line is one slide. Find a route with fewer slides, "
                      "stopping against different rocks."},
    "2c": {"compact": "Every line is one slide. Find a route with fewer slides, "
                      "stopping against different rocks."},
    "3a": {"compact": "Let a while loop drive south until the push moves the "
                      "rover off its column, then report the tick."},
    "3b": {"compact": "Skip counting the legs. One while not at_beacon(): loop "
                      "can choose every tick: wait() just before a gust, "
                      "otherwise south() if south isn't rock, otherwise east()."},
    "3c": {"compact": "Skip counting the legs. One while not at_beacon(): loop "
                      "can choose every tick: wait() just before a gust, "
                      "otherwise south() if south isn't rock, otherwise east()."},
    "4a": {"bonus": "⚡ Drive no square you don't need: down one side of the "
                    "pit, across, and up the other side.",
           "compact": "One line can drive a whole straight stretch: east(4) "
                      "instead of four east() lines. 5 lines means 5 straight "
                      "drives."},
    "4b": {"compact": "The three pits are the same. Write one pit's drive once, "
                      "and repeat it 3 times with a for loop."},
    "4c": {"compact": "Sweep the field like mowing a lawn. While loops with "
                      "look() drive to the rock and back, and one more while "
                      "loop repeats the sweep until samples_left() is 0."},
    "5a": {"compact": "Four lines are enough: drive into the light, keep the "
                      "battery in a variable, wait() once, report the difference."},
    "5b": {"bonus": "⚡ Waiting is slow. Charge only as much as the next stretch "
                    "needs.",
           "compact": "Charging is the same job every time: wait() until the "
                      "battery is high enough. Make a def with a while loop, "
                      "and each charge is one line."},
    "5c": {"compact": "One while not at_beacon(): loop can decide every tick: "
                      "wait() when you're in the sun, otherwise drive east()."},
    "6a": {"bonus": "💎 The crystal is in the bottom left corner, next to a pad. "
                    "Get it before you step on a pad.",
           "compact": "Each line is one straight drive. 4 lines means 4 drives: "
                      "find the pad that takes you nearest the beacon."},
    "6b": {"bonus": "⚡ Another pad gets you there sooner. Test the pads you "
                    "haven't used yet.",
           "compact": "Each line is one straight drive, like east(3). 5 lines "
                      "means 5 drives: find the two pads that take you through "
                      "both walls."},
    "6c": {"compact": "Each line is one straight drive. Once you know where the "
                      "pads go, use as few as you can and drive each stretch in "
                      "one line."},
    "7a": {"compact": "You don't need to drive. The sensors can work the "
                      "number out right inside report( )."},
    "7b": {"compact": "Four while loops, one for each way: keep driving east "
                      "while x() is less than beacon_x(), and the same for the "
                      "other three. Nothing else is needed."},
    "7c": {"compact": "Make a def safe(way) that says whether look(way) is "
                      "clear. Then one while not at_beacon(): loop with if and "
                      "elif picks a safe way toward the beacon each step."},
    "8a": {"bonus": "⚡ A jump covers 2 squares in 1 tick, and works on plain "
                    "ground too.",
           "compact": "Drive to the trench in one line, jump, and drive the rest "
                      "in one line."},
    "8b": {"compact": "Every hop is the same: east(), then jump(\"east\"). A for "
                      "loop repeats them, and one more line finishes."},
    "8c": {"compact": "One while not at_beacon(): loop with an if: jump when "
                      "look(\"east\") is crater or rock, otherwise drive east()."},
    "9a": {"compact": "east(2) is all you need. Delete the other lines."},
    "9b": {"bonus": "⚡ Try the other belt and compare the ticks.",
           "compact": "Each line is one straight drive, like east(3). The belts "
                      "do some of the driving for you."},
    "9c": {"compact": "Each step is the same: east(), then south(). A for loop "
                      "repeats them 5 times."},
    "9d": {"compact": "One while not at_beacon(): loop with an if: jump when "
                      "there's a belt or crater east, otherwise drive east()."},
    "10a": {"compact": "Drive up to the wall in one line, drill, and drive the "
                       "rest in one line."},
    "10b": {"compact": "Each line is one straight drive, like east(4). Drill "
                       "two walls and go round the one with the gap."},
    "10c": {"compact": "The tunnel repeats: drill, then drive two. A for loop "
                       "writes it only once."},
    "10d": {"compact": "One while not at_beacon(): loop with if, elif and else: "
                       "drill rock, jump craters, otherwise drive east()."},
    "11a": {"compact": "One line can do it: drive east all the way, over the key "
                       "and through the gate."},
    "11b": {"compact": "Each line is one straight drive. 4 drives are enough: "
                       "up, across to the key, down, and through the gate."},
    "11c": {"compact": "The rooms are the same. Make one def room(), call it 3 "
                       "times in a for loop, then drive to the beacon."},
    "11d": {"compact": "Make one def go_to(tx, ty) that drives with four while "
                       "loops. Then call it twice: once for the key, once for "
                       "the beacon."},
    "12a": {"compact": "The flags are in a row: 2 straight drives are enough."},
    "12b": {"compact": "Each line is one straight drive. Go straight on from one "
                       "flag to the next wherever you can."},
    "12c": {"compact": "Make def go_to(tx, ty) with four while loops. Then one "
                       "while not at_beacon(): loop calls go_to(next_x(), next_y())."},
    "12d": {"compact": "Use your safe(way) idea from 7C Rocky Plain, and steer "
                       "toward next_x() and next_y() instead of the beacon."},
    "13a": {"compact": "One line: east(8) pushes the boulder in and drives on."},
    "13b": {"compact": "3 lines: drive above the boulder, push it south into "
                       "the trench, then jump."},
    "13c": {"compact": "Every trench is the same: east(2), then jump(\"east\"). "
                       "A for loop repeats them, and one more line finishes."},
    "13d": {"compact": "One while not at_beacon(): loop with an if: jump a "
                       "crater, otherwise drive east() (that pushes boulders too)."},
    "14a": {"compact": "One line: east(distance(\"east\"))."},
    "14b": {"compact": "Drive and jump repeat. Put them in a while not "
                       "at_beacon(): loop."},
    "14c": {"compact": "The steps repeat: east to one before the rock, south to "
                       "one before the rock. A for loop does it 3 times."},
    "14d": {"compact": "One while not at_beacon(): loop: east(distance(\"east\")), "
                       "then jump(\"east\")."},
    "15a": {"compact": "Two straight drives: out east over the samples, and back."},
    "15b": {"compact": "Each line is one straight drive. Out and back along one "
                       "row, then down to the other row, out and back, and up home."},
    "15c": {"compact": "Each trip is the same but one row further down. In "
                       "for i in range(4):  use south(i) and north(i)."},
    "15d": {"compact": "Make def go_to(tx, ty). Then a while True: loop with an "
                       "if: go home when the bay is full or nothing is left, "
                       "otherwise go to the nearest sample."},
}


def star_tips(s, variant):
    """A hint for each of the site's three stars (none for the mission: the
    zone's 📻 hints cover that)."""
    bonus = variant.get("bonus", s["bonus"])
    tips = STAR_TIPS.get(s["key"], {})
    return [None,
            tips.get("bonus") or BONUS_TIPS[bonus["kind"]].format(of=bonus.get("of", "plain")),
            "✂️ " + tips["compact"]]


# A mystery gift waits on one site in each zone. Driving over it in a
# transmitted run (the mission needn't be done) finds a garage item. Most sit
# on a square picked by hand; where every student has their own planet (None)
# it goes a short detour off the reference route on that planet.
GIFT_SQUARES = {"1a": (1, 4), "2b": (4, 5), "3b": (13, 9), "4c": None,
                "5b": (11, 9), "6a": (4, 11), "7b": None, "8b": (3, 10),
                "9b": (5, 4), "10b": (1, 10), "11b": (1, 9), "12b": (2, 10),
                "13b": (3, 7), "14b": (1, 13), "15b": (2, 10)}
_gifts = {}


def gift_square(key, vi):
    """(row, col) of the gift on variant `vi` of site `key`, or None."""
    if key not in GIFT_SQUARES:
        return None
    if GIFT_SQUARES[key]:
        return GIFT_SQUARES[key]
    if (key, vi) not in _gifts:
        zi, zone, s = find_site(key)
        v = s["variants"][vi]
        run = drive(s["reference"], v, zone["rules"], zi)
        route = {(f["r"], f["c"]) for f in run["frames"]}
        taken = route | {tuple(p) for p in v.get("crystals", [])}
        far = {p: 0 for p in route}
        queue = list(route)
        for r, c in queue:   # breadth first over plain ground
            for dr, dc in DIRS:
                n = (r + dr, c + dc)
                if n not in far and n not in taken and v["map"][n[0]][n[1]] == ".":
                    far[n] = far[(r, c)] + 1
                    queue.append(n)
        # Two squares off the route, or as far off as the planet leaves room for.
        want = min(2, max(far.values()))
        spots = sorted(p for p, d in far.items() if d == want)
        _gifts[(key, vi)] = spots[zlib.crc32(f"{key}:{vi}".encode()) % len(spots)]
    return _gifts[(key, vi)]


def code_lines(code):
    """Lines that do something: not blank, not only a comment."""
    return sum(1 for line in str(code).split("\n")
               if line.strip() and not line.strip().startswith("#"))


def bonus_label(bonus):
    kind = bonus["kind"]
    return {"crystals": "💎 Grab every crystal",
            "def": "🧩 Use a function you made with def",
            "no_bump": "🧱 Never bump into rock",
            "no_push": "💨 Never get blown off course",
            "computed": "🔢 Work the number out in code, not typed in",
            "everywhere": f"🌍 The same code works on every {bonus.get('of', 'plain')}",
            "ticks": f"⚡ Done in {bonus.get('max')} ticks or fewer",
            "drills": f"⛏ Finish with {bonus.get('min')} drill"
                      f"{'s' if bonus.get('min') != 1 else ''} to spare",
            "battery": f"🔋 Finish with {bonus.get('min')} battery or more",
            "measured": "🔢 No typed-in numbers: let distance() measure"}[kind]


MISSION_LABELS = {"beacon": "🛰 Reach the beacon",
                  "samples": "🧪 Collect every sample",
                  "report": "📡 Report the right number",
                  "deliver": "📦 Bring every sample home"}


def goals(s, variant):
    """The three stars a site offers, as the student sees them."""
    compact = variant.get("compact", s["compact"])
    return [MISSION_LABELS[mission_of(variant)],
            bonus_label(variant.get("bonus", s["bonus"])),
            f"✂️ {compact} lines of code or fewer"]


def stars(s, variant, run, code):
    """Which of the site's three stars this run earned."""
    if not run["reached"]:
        return [False, False, False]
    bonus = variant.get("bonus", s["bonus"])
    kind = bonus["kind"]
    if kind == "crystals":
        met = run["crystals"][0] == run["crystals"][1]
    elif kind == "def":
        met = run.get("own_function", False)
    elif kind == "no_bump":
        met = run["bumps"] == 0
    elif kind == "no_push":
        met = run["pushes"] == 0
    elif kind == "computed":
        met = run.get("computed", False)
    elif kind == "everywhere":
        met = everywhere(s, code, run)
    elif kind == "ticks":
        met = run["ticks"] <= bonus["max"]
    elif kind == "drills":
        met = (run["drills"] or 0) >= bonus["min"]
    elif kind == "measured":
        met = not run["typed"]
    else:
        met = (run["battery"] or 0) >= bonus["min"]
    return [True, met, code_lines(code) <= variant.get("compact", s["compact"])]


MISSION_DONE = {"beacon": "reached the beacon", "samples": "collected every sample",
                "deliver": "brought every sample home", "report": "reported the right number"}
ENDED_WHY = {"fell": "fell in a crater", "battery": "ran flat",
             "ticks": "ran out of time", "stopped": "stopped short",
             "error": "hit a code error"}


def everywhere(s, code, run):
    """Does this run's code reach the beacon on every variant of the site,
    the classmates' ones too? The run's telemetry gets a line saying how
    many it reached and what stopped the rest. Worked out once per run."""
    if "everywhere" not in run:
        zi, zone, _ = find_site(s["key"])
        ends = [drive(code, v, zone["rules"], zi)["end"] for v in s["variants"]]
        reached = ends.count("goal")
        missed = {}
        for end in ends:
            if end != "goal":
                missed[end] = missed.get(end, 0) + 1
        why = ", ".join(f"{n} {ENDED_WHY.get(end, end)}" for end, n in missed.items())
        of = s["bonus"].get("of", "plain")
        did = MISSION_DONE[mission_of(s["variants"][0])]
        run["log"].append(f"tick {run['ticks']}: 🌍 the same code {did} "
                          f"on {reached} of the {len(ends)} {of}s"
                          + (f" ({why})" if why else ""))
        run["everywhere"] = reached == len(ends)
    return run["everywhere"]


def elsewhere(s, code, run, own):
    """A run that missed on the student's own planet: if the same code works
    on classmates' planets, a copied route is the likely reason, so the next
    step says their planet is different."""
    zi, zone, _ = find_site(s["key"])
    n = sum(drive(code, v, zone["rules"], zi)["reached"]
            for i, v in enumerate(s["variants"]) if i != own)
    if n:
        run["explain"]["next"] = (
            f"This code works on {n} other planet{'s' if n != 1 else ''} in the "
            f"class, but yours is different. {run['explain']['next'] or ''}").strip()
    return n


# ---- Zone 9: five planets -------------------------------------------------------

# Uncharted is five planets of open ground, each with its beacon somewhere
# else, and the same five every run. The rover knows where it is, x() and y(), and where the beacon is, beacon_x()
# and beacon_y(): the program compares them to pick a way, and goes round
# whatever is in the way.
UNCHARTED_REFERENCE = """def safe(way):
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
"""
PLANETS_PER_RUN = 5


def random_planet(rng):
    """Open ground with rock ridges, crater lines, ice and sunny patches. The
    lander and the beacon are in opposite corners (which corners changes).
    The lander sits in a patch of sun with too little battery to cross the
    planet, and a few craters lie round the beacon, where a gust that catches
    the rover can push it in. Craters keep away from ice, so a slide never
    ends in one."""
    rows, cols = rng.randint(9, 11), rng.randint(14, 18)
    grid = open_ground(rows, cols)
    start = (rng.randint(1, 3), rng.randint(1, 3))
    goal = (rng.randint(rows - 4, rows - 3), rng.randint(cols - 5, cols - 3))
    clear = {(p[0] + dr, p[1] + dc) for p in (start, goal)
             for dr in (-1, 0, 1) for dc in (-1, 0, 1)}

    def put(r, c, ch):
        if 0 < r < rows - 1 and 0 < c < cols - 1 and (r, c) not in clear \
                and grid[r][c] == ".":
            grid[r][c] = ch

    for _ in range(rng.randint(5, 8)):          # rock ridges, 2 to 4 long
        r, c = rng.randrange(1, rows - 1), rng.randrange(1, cols - 1)
        dr, dc = rng.choice(DIRS)
        for i in range(rng.randint(2, 4)):
            put(r + dr * i, c + dc * i, "#")
    for _ in range(rng.randint(1, 3)):          # ice patches
        r, c = rng.randrange(1, rows - 2), rng.randrange(1, cols - 3)
        for dr in range(2):
            for dc in range(rng.randint(2, 3)):
                put(r + dr, c + dc, "~")
    ice = [(r, c) for r in range(rows) for c in range(cols) if grid[r][c] == "~"]
    for _ in range(rng.randint(2, 4)):          # crater lines, north to south
        r, c = rng.randrange(1, rows - 1), rng.randrange(1, cols - 1)
        for i in range(rng.randint(2, 4)):
            if all(abs(r + i - a) + abs(c - b) > 2 for a, b in ice):
                put(r + i, c, "O")
    for _ in range(rng.randint(2, 4)):          # sunny ground
        put(rng.randrange(1, rows - 1), rng.randrange(1, cols - 1), "+")
    for dr in (-1, 0, 1):                       # sun round the lander
        for dc in (-1, 0, 1):
            if grid[start[0] + dr][start[1] + dc] == ".":
                grid[start[0] + dr][start[1] + dc] = "+"
    ring = [(goal[0] + dr, goal[1] + dc) for dr in range(-2, 3) for dc in range(-2, 3)
            if max(abs(dr), abs(dc)) == 2 or (dr == 0 and abs(dc) == 1)]
    for r, c in rng.sample(ring, 4):            # craters round the beacon
        if 0 < r < rows - 1 and 0 < c < cols - 1 and grid[r][c] == ".":
            grid[r][c] = "O"
    grid[start[0]][start[1]] = "S"
    grid[goal[0]][goal[1]] = "G"
    if rng.random() < .5:
        grid.reverse()
    if rng.random() < .5:
        grid = [row[::-1] for row in grid]
    return {"map": strings(grid), "wind": rng.randint(3, 6),
            "battery": rng.randint(8, 12)}


UNCHARTED_RULES = {"ice", "wind", "battery"}
UNCHARTED_ZONE = len(ZONES)


def uncharted_planets(seed):
    """PLANETS_PER_RUN random planets, each one checked: the reference rover
    can reach its beacon, so every planet in a run is fair."""
    rng = random.Random(seed)
    planets = []
    while len(planets) < PLANETS_PER_RUN:
        planet = random_planet(rng)
        if drive(UNCHARTED_REFERENCE, planet, UNCHARTED_RULES,
                 UNCHARTED_ZONE)["reached"]:
            planets.append(planet)
    return planets


# The planets every run lands on. They were random, new each run, but that
# was too hard for the class: the same five let students fix one thing at
# a time. Seed 2 is a set where 7C's program already reaches 2, and where
# leaving out any idea (sun, wind, craters, going round) loses one.
UNCHARTED_PLANETS = uncharted_planets(2)
# What Uncharted shows before the first run: the first of them.
UNCHARTED_SAMPLE = UNCHARTED_PLANETS[0]

ZONE_NAMES = [z["name"] for z in ZONES] + ["Uncharted"]


# ---- for the classroom side ------------------------------------------------------

UNCHARTED = {"key": "7", "name": "Uncharted",
             "brief": f"{PLANETS_PER_RUN} planets, the same {PLANETS_PER_RUN} "
                      f"every run. One program has to reach the beacon on all of them."}
ZONES.append({"key": "uncharted", "name": "Uncharted", "rules": UNCHARTED_RULES,
              "blurb": "Five planets, with ice, wind and sunshine too."
                       " A new sensor, gust_in(), says how many ticks "
                       "until the next gust.",
              "hints": [
                  "Compare where you are with where the beacon is. If x() is "
                  "smaller than beacon_x(), the beacon is to the east:\n\n"
                  "while not at_beacon():\n    if x() < beacon_x():\n"
                  "        east()\n    elif y() < beacon_y():\n        south()",
                  "Rocks and craters get in the way. Only drive a way that's "
                  "safe, and try another way (or jump) when it isn't:\n\n"
                  "def safe(way):\n    return look(way) != \"rock\" and "
                  "look(way) != \"crater\"",
                  "Everything from before still counts. Before each square:  "
                  "if gust_in() == 1: wait().  And when you're in the sun "
                  "with a low battery, charge up first.",
              ],
              "sites": [UNCHARTED]})
SITE_ORDER = [s["key"] for z in ZONES for s in z["sites"]]


def find_site(key):
    """(zone index, zone, site) for a site key, or None."""
    for zi, zone in enumerate(ZONES):
        for s in zone["sites"]:
            if s["key"] == key:
                return zi, zone, s
    return None


def variant_index(student, s):
    """Which variant a student gets: their own, the same every time."""
    if not s.get("per_student"):
        return 0
    return zlib.crc32(f"{student}:{s['key']}".encode()) % len(s["variants"])


def sensors_for(zi):
    return [name for name, z in SENSOR_ZONE.items() if z <= zi]
