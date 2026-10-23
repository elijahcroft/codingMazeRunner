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

# Each sensor arrives with a zone and stays for every zone after it.
SENSOR_ZONE = {
    "look": 0, "at_beacon": 0,
    "x": 1, "y": 1, "report": 1,
    "tick": 2,
    "samples_left": 3,
    "battery": 4, "in_sun": 4,
    "beacon_x": 6, "beacon_y": 6, "gust_in": 6,
}

# What look() calls each square.
WORDS = {"#": "rock", ".": "ground", "S": "ground", "G": "beacon", "~": "ice",
         "O": "crater", "*": "ground", "+": "sun", "P": "pad"}

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
LOOK_HOW = ('look() needs a direction in quotes: "north", "south", "east" or '
            '"west", like  look("east")')


def literal(node):
    """A number typed straight in, like 6 or -2 (not worked out by code)."""
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.USub, ast.UAdd)):
        node = node.operand
    return isinstance(node, ast.Constant)


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
        if len(code) > MAX_CODE:
            raise BotError(f"Your program is too long: the limit is {MAX_CODE} "
                           f"characters (about 100 lines). Delete some comments "
                           f"or lines you don't need.")
        code = code.replace(" ", " ").replace("​", "").replace("﻿", "")
        try:
            self.tree = ast.parse(code)
        except SyntaxError as e:
            err = BotError(syntax_message(e, "def step():"))
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
        return super().eval(node, frame)

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
        return super().lookup(name, frame)

    def assign(self, name, value, frame):
        if name in ("x", "y") and name in self.sensors:
            raise BotError(f"{name}() is the rover's sensor for where it is, so "
                           f"{name} can't be a variable too. Pick another name, "
                           f"like  n  or  steps")
        super().assign(name, value, frame)

    def run_statement(self, node, frame):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            raise BotError("import isn't allowed on Strange Planet — "
                           "everything you need is already here.")
        if isinstance(node, ast.FunctionDef) and \
                (node.name in COMMANDS or node.name in ("look", "report")):
            raise BotError(f"{node.name}() is already one of the rover's commands — "
                           f"pick another name, like  def hop():")
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

    def direction(self, node, frame):
        """look()'s direction: "east" in quotes, a variable holding it, or
        (forgiven) the bare word east."""
        if isinstance(node, ast.Name) and node.id.lower() in COMPASS and \
                not self.mine(node.id, frame):
            return node.id.lower()
        way = self.eval(node, frame)
        if not isinstance(way, str) or way.strip().lower() not in COMPASS:
            raise BotError(LOOK_HOW)
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
            if n < 0 or n > MAX_MOVE:
                raise BotError(f"{name}() takes a number from 0 to {MAX_MOVE}.")
            for _ in range(n):
                world.act(name)
            return None
        if name == "look" and name in self.sensors:
            if len(node.args) != 1:
                raise BotError(LOOK_HOW)
            return world.look(self.direction(node.args[0], frame))
        if name == "report" and name in self.sensors:
            if len(node.args) != 1:
                raise BotError("report() sends one number, like  report(6)")
            value = self.eval(node.args[0], frame)
            if isinstance(value, bool) or not isinstance(value, int):
                raise BotError(f"report() sends a whole number, like  report(6), "
                               f"not {value!r}.")
            world.report(value, not literal(node.args[0]))
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
                              for c, ch in enumerate(row) if ch == "S")
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
        self.computed = False   # the right report() was worked out by code
        self.samples = {(r, c) for r, row in enumerate(self.grid)
                        for c, ch in enumerate(row) if ch == "*"}
        self.links = {}
        for a, b in variant.get("pairs", []):
            self.links[tuple(a)] = tuple(b)
            self.links[tuple(b)] = tuple(a)
        for a, b in variant.get("oneway", []):
            self.links[tuple(a)] = tuple(b)
        self.log = []
        self.prints = []
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
        raise BotError(f"I don't know the sensor '{name}'.")

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
        ch = self.at(r, c)
        if (r, c) in self.cracked:
            self.frames.append(self.frame())
            self.finish("fell", "💥 cracked ground gave way")
        if ch == "O":
            self.frames.append(self.frame())
            self.finish("fell", "💥 fell into a crater")
        if (r, c) in self.crystals:
            self.crystals.discard((r, c))
            self.say("💎 crystal collected")
        if (r, c) in self.samples:
            self.samples.discard((r, c))
            self.say(f"🧪 sample collected, {len(self.samples)} left")
        self.frames.append(self.frame(how if how != "move" else None))

    def act(self, command):
        if self.end:
            raise _End()
        if self.t >= MAX_TICKS:
            self.finish("ticks", f"⏱ out of time ({MAX_TICKS} ticks)")
        if "battery" in self.rules and command != "wait" and self.battery <= 0:
            self.finish("battery", "🔋 battery empty")
        self.t += 1
        if "battery" in self.rules and command != "wait":
            self.battery -= 1
        if command == "wait":
            self.frames.append(self.frame("wait"))
        else:
            self.d = COMPASS[command]
            self.drive(command)
        if "wind" in self.rules and command != "wait" and self.t % self.v["wind"] == 0:
            self.gust()
        if "battery" in self.rules and self.in_sun():
            self.battery = min(BATTERY_MAX, self.battery + SUN_CHARGE)
            self.frames[-1]["b"] = self.battery
        self.check_goal()

    def drive(self, command):
        r, c = self.ahead()
        if self.at(r, c) == "#":
            self.bumps += 1
            self.say("🧱 bumped into rock")
            self.frames.append(self.frame("bump"))
            return
        self.enter(r, c)
        self.portal()
        # On ice the rover keeps sliding until something stops it.
        slid = False
        while "ice" in self.rules and self.at(self.r, self.c) == "~":
            r, c = self.ahead()
            if self.at(r, c) == "#":
                break
            self.enter(r, c)
            slid = True
        if slid:
            self.say(f"⛸ one {command}() kept sliding")

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
        if self.at(r, c) == "#":
            self.say("💨 gust, but a rock sheltered the rover")
            return
        self.pushes += 1
        self.say("💨 gust pushed the rover east")
        self.enter(r, c, "gust")

    def report(self, value, computed):
        if self.end:
            raise _End()
        if self.mission != "report":
            self.say(f"📡 report sent: {value}")
            return
        self.computed = computed
        if value == self.v["answer"]:
            self.finish("goal", f"📡 you reported {value}. Mission control: "
                                f"that matches what we measured!")
        self.finish("wrong", f"📡 you reported {value}. Mission control "
                             f"measured something different.")

    def check_goal(self):
        if self.mission == "beacon" and (self.r, self.c) == self.goal:
            if self.samples:
                self.say(f"🛰 the beacon needs every sample first "
                         f"({len(self.samples)} left)")
            else:
                self.finish("goal", "🎉 beacon reached")
        elif self.mission == "samples" and not self.samples:
            self.finish("goal", "🎉 every sample collected")


def mission_of(variant):
    """"report" (a field measurement), "beacon" or "samples"."""
    if "answer" in variant:
        return "report"
    return "beacon" if any("G" in row for row in variant["map"]) else "samples"


ENDED_SHORT = {"report": "🏁 program ended without a report()",
               "beacon": "🏁 program ended away from the beacon",
               "samples": "🏁 program ended with samples still out there"}


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
         bonus=None, compact=99):
    """One site. Every variant is a dict with a "map" and the hidden details
    (wind, sun, portal pairs, battery, the answer to report). `per_student`
    sites give each student their own variant; `reference` is a program that
    clears every variant. `bonus` is the site's challenge star and `compact`
    the most lines of code for the compact star; a variant may set its own of
    either."""
    return {"key": key, "name": name, "brief": brief, "variants": variants,
            "per_student": per_student, "reference": reference,
            "bonus": bonus or {"kind": "no_bump"}, "compact": compact}


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
              "Eight samples in a line of steps. One step repeats.",
              [{"map": STEPS_FIELD}],
              reference="for i in range(8):\n    east()\n    south()\n"),
         site("1c", "Boulder Run",
              "A sample waits at every boulder. Your boulders aren't where "
              "anyone else's are.",
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
     "blurb": "Something about this ground is different.",
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
              "📡 Field measurement: how many squares does one east() take "
              "on the ice? report() the number, like  report(4)",
              [{"map": ["#############",
                        "#...........#",
                        "#S~~~~~~#...#",
                        "#...........#",
                        "#############"], "answer": 6}],
              reference="east()\nreport(x() - 1)\n"),
         site("2b", "Glacier",
              "Two squares away. Getting there is another matter.",
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
              "Your lake's rocks are yours alone. Plan your slides.",
              [{"map": m} for m in FROZEN_LAKES], per_student=True),
     ]},
    {"key": "wind", "name": "Wind Canyon", "rules": {"wind"},
     "blurb": "Something keeps nudging the rover.",
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
              "ticks apart are the pushes? report() the number.",
              [{"map": ["########",
                        "#.S....#"] + ["#......#"] * 13 + ["########"],
                "dir": 2, "wind": 5, "answer": 5}],
              reference="while x() == 2:\n    south()\nreport(tick())\n"),
         site("3b", "The Ledge",
              "A long ledge with craters along it. Too far to dodge by hand.",
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
              "This ridge keeps its own time.",
              [{"map": windy_ledge(legs), "dir": 2, "wind": n, "legs": legs}
               for legs in ([(2, 5), (1, 7), (2, 4), (1, 3), (2, 7)],
                            [(2, 4), (1, 5), (2, 6), (1, 4), (2, 5)])
               for n in (4, 6, 7, 9)],
              per_student=True),
     ]},
    {"key": "crumble", "name": "Crumbling Crust", "rules": {"crumble"},
     "blurb": "The ground here is thin. Collect the samples.",
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
              "Three pits, three samples.",
              [{"map": ["####################",
                        "#S................G#",
                        "#####..###..###..###",
                        "#####..###..###..###",
                        "#####*.###*.###*.###",
                        "####################"]}],
              reference="def pit():\n    south(3)\n    east()\n    north(3)\n\n"
                        "for i in range(3):\n    east(4)\n    pit()\neast(2)\n"),
         site("4c", "Sample Field",
              "Sweep the field for samples. Yours are scattered differently.",
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
     "blurb": "Long shadows. Keep an eye on the gauge.",
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
              "📡 Field measurement: how much battery does one tick of "
              "wait() on the bright ground give? report() the number.",
              [{"map": ["############",
                        "#S++++.....#",
                        "############"], "battery": 12, "answer": 2}],
              reference="east()\nbefore = battery()\nwait()\n"
                        "report(battery() - before)\n"),
         site("5b", "Shadow Steps",
              "Sunny corners, long shadows between.",
              [{"map": sunny([(1, 12), (2, 5), (3, 16), (2, 5), (1, 20)],
                             [12, 17, 33, 38]), "dir": 1, "battery": 14}],
              reference="def charge_to(n):\n    while battery() < n:\n"
                        "        wait()\n\neast(12)\ncharge_to(5)\nsouth(5)\n"
                        "charge_to(16)\nwest(16)\ncharge_to(5)\nsouth(5)\n"
                        "charge_to(20)\neast(20)\n"),
         site("5c", "Moving Shadows",
              "Here, the sunlight moves.",
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
     "blurb": "Strange pads, all alike. Where do they go?",
     "hints": [
         "Drive onto one pad at a time and read the log: it says the x and "
         "y where the rover came out. Write it in your field journal.",
         "Pads work in pairs: go in one, come out of its partner. But some "
         "pads only send one way, and some send nowhere.",
         "Make one function per trip, then chain them:\n\n"
         "def to_middle():\n    south(2)\n    east(3)\n\n"
         "to_middle()\n...",
     ],
     "sites": [
         site("6a", "The Pads",
              "The beacon is behind solid rock.",
              [{"map": ["#############",
                        "#S....#.....#",
                        "#.....#..G..#",
                        "#P.P.P#.....#",
                        "#.....#P....#",
                        "#############"],
                "pairs": [[(3, 3), (4, 7)], [(3, 1), (3, 5)]]}],
              reference="east(2)\nsouth(2)\nnorth(2)\neast(2)\n"),
         site("6b", "Relay",
              "Two walls this time.",
              [{"map": ["###################",
                        "#S....#.....#.....#",
                        "#.....#.....#..G..#",
                        "#.P.P.#.P.P.#.....#",
                        "#.....#.....#.P...#",
                        "###################"],
                "pairs": [[(3, 4), (3, 8)], [(3, 10), (4, 14)], [(3, 2), (1, 10)]]}],
              reference="east(3)\nsouth(2)\neast(2)\nnorth(2)\neast()\n"),
         site("6c", "Portal Maze",
              "Seven pads, wired differently on your planet.",
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


# Each site's challenge star and compact-code star. Crystals sit on a fixed
# site's only planet; on the per-student lakes and portal mazes the compact
# target follows that student's own shortest route.
CHALLENGES = {
    "1a": {"bonus": {"kind": "crystals"}, "compact": 7, "crystals": [(1, 10)]},
    "1b": {"bonus": {"kind": "def"}, "compact": 3},
    "1c": {"bonus": {"kind": "no_bump"}, "compact": 5},
    "2a": {"bonus": {"kind": "computed"}, "compact": 3},
    "2b": {"bonus": {"kind": "crystals"}, "compact": 6, "crystals": [(1, 7)]},
    "2c": {"bonus": {"kind": "no_bump"}, "compact": [8, 8, 8, 9, 8, 8, 8, 8]},
    "3a": {"bonus": {"kind": "computed"}, "compact": 3},
    "3b": {"bonus": {"kind": "no_push"}, "compact": 16},
    "3c": {"bonus": {"kind": "no_push"}, "compact": 17},
    "4a": {"bonus": {"kind": "ticks", "max": 14}, "compact": 5},
    "4b": {"bonus": {"kind": "def"}, "compact": 8},
    "4c": {"bonus": {"kind": "no_bump"}, "compact": 8},
    "5a": {"bonus": {"kind": "computed"}, "compact": 4},
    "5b": {"bonus": {"kind": "ticks", "max": 80}, "compact": 12},
    "5c": {"bonus": {"kind": "battery", "min": 30}, "compact": 5},
    "6a": {"bonus": {"kind": "crystals"}, "compact": 4, "crystals": [(4, 1)]},
    "6b": {"bonus": {"kind": "ticks", "max": 8}, "compact": 5},
    "6c": {"bonus": {"kind": "no_bump"}, "compact": [8, 7, 8, 6, 8, 7, 8, 8]},
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
            "ticks": f"⚡ Done in {bonus.get('max')} ticks or fewer",
            "battery": f"🔋 Finish with {bonus.get('min')} battery or more"}[kind]


MISSION_LABELS = {"beacon": "🛰 Reach the beacon",
                  "samples": "🧪 Collect every sample",
                  "report": "📡 Report the right number"}


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
    elif kind == "ticks":
        met = run["ticks"] <= bonus["max"]
    else:
        met = (run["battery"] or 0) >= bonus["min"]
    return [True, met, code_lines(code) <= variant.get("compact", s["compact"])]


# ---- Zone 7: random planets ----------------------------------------------------

# Uncharted is open ground with the beacon somewhere new every run. The
# rover knows where it is, x() and y(), and where the beacon is, beacon_x()
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


# What Uncharted shows before the first run: one planet of the kind every
# run lands on, so students can see it's open ground before writing code.
UNCHARTED_SAMPLE = uncharted_planets(1)[0]

ZONE_NAMES = [z["name"] for z in ZONES] + ["Uncharted"]


# ---- for the classroom side ------------------------------------------------------

UNCHARTED = {"key": "7", "name": "Uncharted",
             "brief": f"{PLANETS_PER_RUN} new planets every run. The beacon is "
                      f"somewhere new each time."}
ZONES.append({"key": "uncharted", "name": "Uncharted", "rules": UNCHARTED_RULES,
              "blurb": "A new planet every run. Two new sensors, beacon_x() "
                       "and beacon_y(), say where the beacon is.",
              "hints": [
                  "Compare where you are with where the beacon is. If x() is "
                  "smaller than beacon_x(), the beacon is to the east:\n\n"
                  "while not at_beacon():\n    if x() < beacon_x():\n"
                  "        east()\n    elif y() < beacon_y():\n        south()",
                  "Rocks and craters get in the way. Only drive a way that's "
                  "safe, and try another way when it isn't:\n\n"
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
