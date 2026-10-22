"""
Strange Planet: drive a rover across an alien planet with Python.

Every zone has ONE hidden physics rule that nobody explains. Students find it
by running code, watching the replay and reading the log, then write a
program that works with it. Each zone has three sites:

    A  Notice      the rule appears, and the obvious program breaks in plain sight
    B  Use         the site can only be solved by using the rule on purpose
    C  Generalise  the rule's details differ per student, so only a program
                   built on sensors and variables works (and copying doesn't)

The program runs top to bottom like Python Quest, with commands

    move()  move(3)  turn_left()  turn_right()  wait()

and every command takes one tick of planet time. Sensors arrive zone by zone.
Student code runs in the Light Cycles interpreter (cycles.Brain): a whitelist
of the parse tree, so no imports, attribute access or real builtins ever run
on the teacher's laptop.

Map squares:
    #  rock          .  ground        S  start (ground)   G  beacon (the goal)
    ~  ice           O  crater        *  sample           +  sunny ground
    P  portal pad
"""

import ast
import random
import zlib

from cycles import (DIRS, BotError, Brain, _Break, _Continue, _Frame, _TooLong,
                    syntax_message)

MAX_TICKS = 1000          # planet time before the rover gives up
PROGRAM_BUDGET = 200_000  # interpreter operations for one whole run
MAX_CODE = 4000           # characters in one program
MAX_PRINTS = 80           # print() lines kept: the LAST ones
MAX_MOVE = 50             # move(n) takes at most this many squares
BATTERY_MAX = 100
SUN_CHARGE = 2            # battery gained each tick the rover ends in sunlight

COMMANDS = ("move", "turn_left", "turn_right", "wait")

# Each sensor arrives with a zone and stays for every zone after it.
SENSOR_ZONE = {
    "wall_ahead": 0, "wall_left": 0, "wall_right": 0, "at_goal": 0,
    "tick": 2, "crater_ahead": 2,
    "cracked_ahead": 3, "samples_left": 3,
    "battery": 4, "in_sun": 4,
    "gust_in": 6,
}


class _End(Exception):
    """The run is over (goal, fall, flat battery, out of time): stop the program."""


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
        code = code.replace(" ", " ").replace("​", "").replace("﻿", "")
        try:
            self.tree = ast.parse(code)
        except SyntaxError as e:
            raise BotError(syntax_message(e))

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

    def run_statement(self, node, frame):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            raise BotError("import isn't allowed on Strange Planet — "
                           "everything you need is already here.")
        super().run_statement(node, frame)

    def call(self, node, frame):
        if isinstance(node.func, ast.Attribute):
            raise BotError(f"{ast.unparse(node.func)}() isn't part of Strange "
                           f"Planet — use the commands and sensors, or make your "
                           f"own with def.")
        if not isinstance(node.func, ast.Name):
            raise BotError("I can only call plain commands, like  move()")
        if node.keywords:
            raise BotError("Commands don't take name=value arguments here.")
        name = node.func.id
        world = self.world
        if name in COMMANDS:
            args = [self.eval(a, frame) for a in node.args]
            if name == "move":
                if len(args) > 1:
                    raise BotError("move() takes one number at most, like  move(3)")
                n = self.number(args[0], "move()") if args else 1
                if n < 0 or n > MAX_MOVE:
                    raise BotError(f"move() takes a number from 0 to {MAX_MOVE}.")
                for _ in range(n):
                    world.act("move")
            elif args:
                raise BotError(f"{name}() doesn't take anything in the ( ).")
            else:
                world.act(name)
            return None
        if name in self.sensors:
            if node.args:
                raise BotError(f"{name}() doesn't take anything in the ( ).")
            return world.sense(name)
        if name in SENSOR_ZONE:
            raise BotError(f"{name}() hasn't been unlocked yet: it arrives in "
                           f"{ZONE_NAMES[SENSOR_ZONE[name]]}.")
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
        if name in ("steer", "left", "right", "forward", "turn", "go", "stop") \
                and name not in self.funcs:
            raise BotError(f"I don't know the command '{name}'. The rover's "
                           f"commands are  move()  turn_left()  turn_right()  "
                           f"and  wait()")
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
        self.d = variant.get("dir", 1)
        self.t = 0
        self.battery = variant.get("battery", BATTERY_MAX)
        self.cracked = set()
        self.crack = None    # the square that just cracked, for the next frame
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
        self.end = None      # "goal", "fell", "battery", "ticks" once it's over

    # ---- what the rover sees ----------------------------------------------

    def at(self, r, c):
        if 0 <= r < self.rows and 0 <= c < self.cols:
            return self.grid[r][c]
        return "#"

    def ahead(self, turn=0):
        dr, dc = DIRS[(self.d + turn) % 4]
        return self.r + dr, self.c + dc

    def in_sun(self):
        if self.at(self.r, self.c) == "+":
            return True
        band = self.v.get("sun")
        if not band:
            return False
        return (self.c - self.sun_at(self.t)) % self.cols < band["width"]

    def sun_at(self, t):
        band = self.v["sun"]
        return (band["start"] + t // band["every"]) % self.cols

    def gust_in(self):
        every = self.v.get("wind")
        if not every:
            return 0
        return every - self.t % every

    def sense(self, name):
        if name == "wall_ahead":
            return self.at(*self.ahead()) == "#"
        if name == "wall_left":
            return self.at(*self.ahead(-1)) == "#"
        if name == "wall_right":
            return self.at(*self.ahead(1)) == "#"
        if name == "at_goal":
            return self.at(self.r, self.c) == "G"
        if name == "tick":
            return self.t
        if name == "crater_ahead":
            return self.at(*self.ahead()) == "O"
        if name == "cracked_ahead":
            return self.ahead() in self.cracked
        if name == "samples_left":
            return len(self.samples)
        if name == "battery":
            return self.battery
        if name == "in_sun":
            return self.in_sun()
        if name == "gust_in":
            return self.gust_in()
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
        if command == "turn_left":
            self.d = (self.d - 1) % 4
            self.frames.append(self.frame())
        elif command == "turn_right":
            self.d = (self.d + 1) % 4
            self.frames.append(self.frame())
        elif command == "wait":
            self.frames.append(self.frame("wait"))
        else:
            self.drive()
        if "wind" in self.rules and command == "move" and self.t % self.v["wind"] == 0:
            self.gust()
        if "battery" in self.rules and self.in_sun():
            self.battery = min(BATTERY_MAX, self.battery + SUN_CHARGE)
            self.frames[-1]["b"] = self.battery
        self.check_goal()

    def drive(self):
        r, c = self.ahead()
        if self.at(r, c) == "#":
            self.say("🧱 bumped into rock")
            self.frames.append(self.frame("bump"))
            return
        start = (self.r, self.c)
        self.enter(r, c)
        self.portal()
        # On ice the rover keeps sliding until something stops it.
        slid = 1
        while "ice" in self.rules and self.at(self.r, self.c) == "~":
            r, c = self.ahead()
            if self.at(r, c) == "#":
                break
            self.enter(r, c)
            slid += 1
        if slid > 1:
            self.say(f"⛸ one move() slid {slid} squares")

    def portal(self):
        if self.at(self.r, self.c) != "P":
            return
        to = self.links.get((self.r, self.c))
        if to is None:
            return
        frm = (self.r, self.c)
        self.r, self.c = to
        self.frames.append(self.frame("portal"))
        self.say(f"✨ pad at row {frm[0]} col {frm[1]} → row {to[0]} col {to[1]}")

    def gust(self):
        r, c = self.r, self.c + 1
        if self.at(r, c) == "#":
            self.say("💨 gust, but a rock sheltered the rover")
            return
        self.say("💨 gust pushed the rover east")
        self.enter(r, c, "gust")

    def check_goal(self):
        if self.at(self.r, self.c) == "G":
            if self.samples:
                self.say(f"🛰 the beacon needs every sample first "
                         f"({len(self.samples)} left)")
            else:
                self.finish("goal", "🎉 beacon reached")


def drive(code, variant, rules, zone):
    """Run one program on one planet. Returns the replay the browser animates."""
    world = World(variant, rules)
    sensors = {name: None for name, z in SENSOR_ZONE.items() if z <= zone}
    sensors.update({name: None for name in COMMANDS})
    error = line = None
    try:
        rover = Rover(str(code)[:MAX_CODE + 1], world, sensors)
        rover.run()
    except _End:
        pass
    except BotError as e:
        error, line = str(e), e.line
    except RecursionError:
        error = "Your functions call each other too deeply."
    if error is None and world.end is None:
        world.end = "stopped"
        world.say("🏁 program ended away from the beacon")
    return {"reached": world.end == "goal", "end": "error" if error else world.end,
            "ticks": world.t, "error": error, "line": line,
            "frames": world.frames, "log": world.log, "prints": world.prints,
            "cracked": sorted(world.cracked),
            "sun_width": (variant.get("sun") or {}).get("width", 0)}


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


def spiral_room(rows, cols, samples):
    """An empty crumbling room. A rover that turns right whenever it's blocked
    by rock or cracks spirals in and visits every square once; the beacon
    sits where that spiral ends, and the samples are on the way."""
    grid = [["#"] * (cols + 2)] + [["#"] + ["."] * cols + ["#"]
                                   for _ in range(rows)] + [["#"] * (cols + 2)]
    r, c, d = 1, 1, 1
    seen = {(r, c)}
    while True:
        for turn in range(4):
            dr, dc = DIRS[(d + turn) % 4]
            if grid[r + dr][c + dc] != "#" and (r + dr, c + dc) not in seen:
                d = (d + turn) % 4
                break
        else:
            break
        r, c = r + DIRS[d][0], c + DIRS[d][1]
        seen.add((r, c))
    grid[1][1] = "S"
    grid[r][c] = "G"
    for sr, sc in samples:
        grid[sr][sc] = "*"
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
]


def site(key, name, brief, variants, per_student=False, reference=""):
    """One site. Every variant is a dict with a "map" and the hidden details
    (wind, sun, portal pairs, battery). `per_student` sites give each student
    their own variant; `reference` is a program that clears every variant."""
    return {"key": key, "name": name, "brief": brief, "variants": variants,
            "per_student": per_student, "reference": reference}


ZONES = [
    {"key": "landing", "name": "Landing Site", "rules": set(),
     "blurb": "Ordinary ground. Learn to drive.",
     "hints": [
         "Commands run in order, top to bottom. Count the squares on the map "
         "before each turn.",
         "for i in range(7):  repeats the lines pushed in under it 7 times. "
         "Find the piece of the route that repeats.",
         "When the lengths change, don't count them: drive until you meet "
         "rock.\n\nwhile not wall_ahead():\n    move()",
     ],
     "sites": [
         site("1a", "Touchdown",
              "Drive to the beacon. Count the squares before each turn.",
              [{"map": ["###########",
                        "#S...######",
                        "####.######",
                        "####.....G#",
                        "###########"]}],
              reference="move(3)\nturn_right()\nmove(2)\nturn_left()\nmove(5)\n"),
         site("1b", "Ridge Steps",
              "A long staircase. One step repeats.",
              [{"map": ["###########",
                        "#S.########",
                        "##..#######",
                        "###..######",
                        "####..#####",
                        "#####..####",
                        "######..###",
                        "#######..##",
                        "########.G#",
                        "###########"]}],
              reference="for i in range(7):\n    move()\n    turn_right()\n"
                        "    move()\n    turn_left()\nmove()\n"),
         site("1c", "Long Corridors",
              "Your corridors are a different length from everyone else's.",
              [{"map": strings(path_map(legs)[0])} for legs in (
                  [(1, 4), (2, 3), (1, 6), (2, 4), (1, 5)],
                  [(1, 7), (2, 2), (1, 3), (2, 5), (1, 4)],
                  [(1, 3), (2, 5), (1, 5), (2, 2), (1, 7)],
                  [(1, 6), (2, 4), (1, 2), (2, 3), (1, 6)])],
              per_student=True,
              reference="for i in range(2):\n    while not wall_ahead():\n"
                        "        move()\n    turn_right()\n"
                        "    while not wall_ahead():\n        move()\n"
                        "    turn_left()\nwhile not wall_ahead():\n    move()\n"),
     ]},
    {"key": "ice", "name": "Ice Field", "rules": {"ice"},
     "blurb": "Something about this ground is different.",
     "hints": [
         "Watch the replay closely. How many squares does ONE move() take "
         "on the shiny ground?",
         "On ice, one move() slides until something stops it: rock, or "
         "ordinary ground. You can't stop in the middle of the ice.",
         "Rocks are your brakes. Work backwards from the beacon: which rock "
         "could stop you right next to it? A function per direction helps:\n\n"
         "def slide_up():\n    turn_left()\n    move()\n    turn_right()",
     ],
     "sites": [
         site("2a", "First Frost",
              "The beacon is just below the ice.",
              [{"map": ["###########",
                        "#S~~~~~~..#",
                        "#.###.###.#",
                        "#.###G###.#",
                        "#.........#",
                        "###########"]}],
              reference="turn_right()\nmove(3)\nturn_left()\nmove(4)\n"
                        "turn_left()\nmove()\n"),
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
              reference="turn_left()\nmove()\nturn_right()\nmove()\n"
                        "turn_right()\nmove()\nturn_left()\nmove()\n"
                        "turn_right()\nmove()\nturn_right()\nmove()\n"),
         site("2c", "Frozen Lake",
              "Your lake's rocks are yours alone. Plan your route.",
              [{"map": m} for m in FROZEN_LAKES], per_student=True),
     ]},
    {"key": "wind", "name": "Wind Canyon", "rules": {"wind"},
     "blurb": "Craters line the canyon. Something keeps nudging the rover.",
     "hints": [
         "Watch WHEN the rover gets pushed. print(tick()) before each move "
         "and compare the numbers.",
         "A gust comes every few ticks, and it only catches a rover that is "
         "driving. A rover that wait()s holds on. tick() % 5 is 4 just "
         "before a gust that comes every 5 ticks.",
         "Make your own safe move:\n\ndef step():\n    if tick() % 5 == 4:\n"
         "        wait()\n    move()",
     ],
     "sites": [
         site("3a", "Canyon Floor",
              "A straight run south. What could go wrong?",
              [{"map": ["######",
                        "##S.O#"] + ["##..O#"] * 11 + [
                        "##G.O#",
                        "######"], "dir": 2, "wind": 5}],
              reference="move(4)\nwait()\nmove(4)\nwait()\nmove(4)\n"),
         site("3b", "The Ledge",
              "A long ledge. Too much to dodge by hand.",
              [{"map": windy_ledge([(2, 6), (1, 5), (2, 6), (1, 4), (2, 5)]),
                "dir": 2, "wind": 5}],
              reference="def step():\n    if tick() % 5 == 4:\n        wait()\n"
                        "    move()\n\ndef go(n):\n    for i in range(n):\n"
                        "        step()\n\ngo(6)\nturn_left()\ngo(5)\n"
                        "turn_right()\ngo(6)\nturn_left()\ngo(4)\nturn_right()\n"
                        "go(5)\n"),
         site("3c", "Gale Ridge",
              "This ridge keeps its own time.",
              [{"map": windy_ledge([(2, 5), (1, 7), (2, 4), (1, 3), (2, 7)]),
                "dir": 2, "wind": n} for n in (4, 6, 7, 9)],
              per_student=True),
     ]},
    {"key": "crumble", "name": "Crumbling Crust", "rules": {"crumble"},
     "blurb": "The ground here is thin. Collect the samples.",
     "hints": [
         "Look at the squares the rover has already driven over. What "
         "happens if it drives over one again?",
         "Ground cracks as soon as the rover leaves it, and cracked ground "
         "gives way. Never go back the way you came: find a loop.",
         "Treat cracks like rock. Turn when either is ahead:\n\n"
         "if wall_ahead() or cracked_ahead():\n    turn_right()",
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
              reference="move(4)\nturn_right()\nmove(3)\nturn_left()\nmove()\n"
                        "turn_left()\nmove(3)\nturn_right()\nmove(3)\n"),
         site("4b", "Three Pits",
              "Three pits, three samples.",
              [{"map": ["####################",
                        "#S................G#",
                        "#####..###..###..###",
                        "#####..###..###..###",
                        "#####*.###*.###*.###",
                        "####################"]}],
              reference="def pit():\n    turn_right()\n    move(3)\n    turn_left()\n"
                        "    move()\n    turn_left()\n    move(3)\n    turn_right()\n\n"
                        "for i in range(3):\n    move(4)\n    pit()\nmove(2)\n"),
         site("4c", "Sample Field",
              "Sweep the field. Your samples are scattered differently.",
              [{"map": spiral_room(5, 7, [(2, 4), (4, 2), (5, 6)])},
               {"map": spiral_room(6, 6, [(1, 5), (5, 3), (3, 2)])},
               {"map": spiral_room(7, 5, [(6, 1), (2, 3), (4, 5)])},
               {"map": spiral_room(6, 8, [(2, 6), (6, 2), (5, 7)])}],
              per_student=True,
              reference="while not at_goal():\n"
                        "    if wall_ahead() or cracked_ahead():\n"
                        "        turn_right()\n    else:\n        move()\n"),
     ]},
    {"key": "solar", "name": "Solar Valley", "rules": {"battery"},
     "blurb": "Long shadows. Keep an eye on the gauge.",
     "hints": [
         "print(battery()) as you go. What makes it go down? Does anything "
         "make it go up?",
         "Driving and turning cost 1 battery. Waiting is free, and every "
         "tick the rover spends in sunlight adds 2.",
         "Charge until you have enough for the next stretch:\n\n"
         "def charge_to(n):\n    while battery() < n:\n        wait()",
     ],
     "sites": [
         site("5a", "First Light",
              "A straight run east.",
              [{"map": ["################################",
                        "#S++..........................G#",
                        "################################"], "battery": 12}],
              reference="move(2)\nfor i in range(10):\n    wait()\nmove(27)\n"),
         site("5b", "Shadow Steps",
              "Sunny corners, long shadows between.",
              [{"map": sunny([(1, 12), (2, 5), (3, 16), (2, 5), (1, 20)],
                             [12, 17, 33, 38]), "dir": 1, "battery": 14}],
              reference="def charge_to(n):\n    while battery() < n:\n"
                        "        wait()\n\nmove(12)\ncharge_to(8)\nturn_right()\n"
                        "move(5)\ncharge_to(18)\nturn_right()\nmove(16)\n"
                        "charge_to(8)\nturn_left()\nmove(5)\ncharge_to(22)\n"
                        "turn_left()\nmove(20)\n"),
         site("5c", "Moving Shadows",
              "Here, the sunlight moves.",
              [{"map": ["#" * 44, "#S" + "." * 40 + "G#", "#" * 44],
                "battery": 10, "sun": sun}
               # The rover can catch each band before its 10 battery runs out.
               for sun in ({"start": 6, "width": 4, "every": 3},
                           {"start": 5, "width": 3, "every": 2},
                           {"start": 4, "width": 3, "every": 4},
                           {"start": 7, "width": 3, "every": 3})],
              per_student=True,
              reference="while not at_goal():\n"
                        "    if in_sun() and battery() < 90:\n        wait()\n"
                        "    else:\n        move()\n"),
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
         "Drive onto one pad at a time and read the log: it says the row and "
         "col where the rover came out. Write it in your field journal.",
         "Pads work in pairs: go in one, come out of its partner. But some "
         "pads only send one way, and some send nowhere.",
         "Make one function per trip, then chain them:\n\n"
         "def to_middle():\n    move(3)\n    turn_right()\n    move(2)\n\n"
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
              reference="move(2)\nturn_right()\nmove(2)\nturn_left()\nmove(2)\n"
                        "turn_left()\nmove(2)\n"),
         site("6b", "Relay",
              "Two walls this time.",
              [{"map": ["###################",
                        "#S....#.....#.....#",
                        "#.....#.....#..G..#",
                        "#.P.P.#.P.P.#.....#",
                        "#.....#.....#.P...#",
                        "###################"],
                "pairs": [[(3, 4), (3, 8)], [(3, 10), (4, 14)], [(3, 2), (1, 10)]]}],
              reference="move(3)\nturn_right()\nmove(2)\nturn_left()\nmove(2)\n"
                        "move()\nturn_left()\nmove(2)\n"),
         site("6c", "Portal Maze",
              "Seven pads, wired differently on your planet.",
              [{"map": PORTAL_MAP, "pairs": pairs, "oneway": oneway}
               for pairs, oneway in (
                   ([(A1, B2), (B1, C2)], [(C1, D1), (A2, B1)]),
                   ([(A2, C1), (C2, B1)], [(B2, D1), (A1, C2)]),
                   ([(A1, C2), (C1, B2)], [(B1, D1), (A2, A1)]),
                   ([(A2, B1), (B2, C1)], [(C2, D1), (A1, C1)]))],
              per_student=True),
     ]})


# ---- Zone 7: random planets ----------------------------------------------------

UNCHARTED_REFERENCE = """def blocked():
    return wall_ahead() or crater_ahead()

def step():
    if gust_in() == 1:
        wait()
    move()

while not at_goal():
    if in_sun() and battery() < 60:
        while battery() < 95:
            wait()
    if not wall_right():
        turn_right()
        if blocked():
            turn_left()
    if blocked():
        turn_left()
    else:
        step()
"""
PLANETS_PER_RUN = 5


def random_planet(rng):
    """A random maze with ice, craters, wind and sunlight. The rover starts in
    the top-left corner facing east; the beacon is on the far cell."""
    h, w = rng.randint(4, 6), rng.randint(6, 8)
    rows, cols = 2 * h + 1, 2 * w + 1
    grid = [["#"] * cols for _ in range(rows)]
    stack, seen = [(0, 0)], {(0, 0)}
    grid[1][1] = "."
    while stack:
        y, x = stack[-1]
        options = [(y + dy, x + dx) for dy, dx in DIRS
                   if 0 <= y + dy < h and 0 <= x + dx < w and (y + dy, x + dx) not in seen]
        if not options:
            stack.pop()
            continue
        ny, nx = rng.choice(options)
        grid[y + ny + 1][x + nx + 1] = "."
        grid[2 * ny + 1][2 * nx + 1] = "."
        seen.add((ny, nx))
        stack.append((ny, nx))
    # The beacon goes on the cell furthest from the start.
    far, dist = (1, 1), {(1, 1): 0}
    queue = [(1, 1)]
    for r, c in queue:
        for dr, dc in DIRS:
            n = (r + dr, c + dc)
            if grid[n[0]][n[1]] != "#" and n not in dist:
                dist[n] = dist[(r, c)] + 1
                queue.append(n)
                if dist[n] > dist[far] and n[0] % 2 and n[1] % 2:
                    far = n
    on_route = set()
    p = far
    while p != (1, 1):
        on_route.add(p)
        p = next((p[0] + dr, p[1] + dc) for dr, dc in DIRS
                 if dist.get((p[0] + dr, p[1] + dc)) == dist[p] - 1)

    def openings(r, c):
        return [(dr, dc) for dr, dc in DIRS if grid[r + dr][c + dc] != "#"]

    squares = [(r, c) for r in range(rows) for c in range(cols)
               if grid[r][c] == "." and (r, c) != (1, 1)]
    for r, c in squares:
        ways = openings(r, c)
        if len(ways) == 1 and (r, c) not in on_route and rng.random() < 0.5:
            grid[r][c] = "O"          # a crater at the end of a dead end
        elif len(ways) == 2 and ways[0][0] == -ways[1][0] and \
                ways[0][1] == -ways[1][1] and rng.random() < 0.25:
            grid[r][c] = "~"          # ice only on straight stretches
        elif rng.random() < 0.12:
            grid[r][c] = "+"
    grid[1][1] = "S"
    grid[far[0]][far[1]] = "G"
    return {"map": strings(grid), "wind": rng.randint(4, 7),
            "battery": rng.randint(40, 70)}


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


ZONE_NAMES = [z["name"] for z in ZONES] + ["Uncharted"]


# ---- for the classroom side ------------------------------------------------------

UNCHARTED = {"key": "7", "name": "Uncharted",
             "brief": f"{PLANETS_PER_RUN} new random planets every run."}
ZONES.append({"key": "uncharted", "name": "Uncharted", "rules": UNCHARTED_RULES,
              "blurb": "Random planets. Everything you've learnt, at once.",
              "hints": [
                  "Start from a wall follower: keep your right hand on the "
                  "rock and you'll find the beacon in any maze.",
                  "Treat craters like rock: write  def blocked():  that "
                  "returns  wall_ahead() or crater_ahead().  gust_in() says "
                  "how many ticks until the next gust.",
                  "Before each move:  if gust_in() == 1: wait().  When the "
                  "battery is low and you're in the sun, charge up first.",
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
