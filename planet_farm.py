"""
The Rover Farm: a part of Strange Planet with no levels to run out of.

Every student has a field of their own. Their program is one farm day: the
rover drives by compass, as on the planet, and picks and plants as it goes,

    harvest()   plant("berry")   dig()   east(2)   wait()

and asks ripe(), empty(), crop() and look("east"). Each command takes one
tick of battery, and the day ends when the program does or the battery runs
out. Crops sell as they're picked. Coins buy a bigger field, a bigger
battery, more memory (lines of code), new crops and things for the yard.

Nothing is ever lost and no run fails: a weak program earns a little and a
better one earns more, so the reason to learn a loop, an if or a def is the
student's own farm. The same program can run day after day, which is the
point of writing one.

Everything a student can grow, buy or be asked for is in the tables below.
Adding to the farm is adding a row: see "Adding to the farm" in the guide.
"""

import ast
import copy
import zlib

import planet
from cycles import DIRS, BotError, _TooLong
from planet import COMMANDS, COMPASS, MAX_CODE, MAX_PRINTS, Rover, _End, code_lines

# ---- What grows ----------------------------------------------------------------
# days: nights in the ground before it's ripe. pay: coins for picking one.
# cost: coins to unlock it in the shop. alone: only grows with no plant of its
# own kind on the four squares beside it.
CROPS = {
    "berry": {"icon": "🍓", "name": "Glowberry", "days": 1, "pay": 1, "cost": 0,
              "about": "Ripe the very next day."},
    "carrot": {"icon": "🥕", "name": "Moon carrot", "days": 2, "pay": 3, "cost": 30,
               "about": "Ask  ripe()  first, so no battery is wasted."},
    "melon": {"icon": "🍉", "name": "Star melon", "days": 3, "pay": 6, "cost": 300,
              "about": "Slow, but it earns a lot for each tick of battery."},
    "bloom": {"icon": "🌻", "name": "Sun bloom", "days": 1, "pay": 5, "cost": 1200, "alone": True,
              "about": "Only grows with no sun bloom beside it. Plant them like a chess board."},
    "pizza": {"icon": "🍕", "name": "Pizza plant", "days": 4, "pay": 16, "cost": 8000,
              "about": "Yes, it grows pizza."},
    "gem": {"icon": "💎", "name": "Crystal bloom", "days": 6, "pay": 40, "cost": 40000,
            "about": "The best there is."},
}
GOLD_ODDS = 12     # one plant in this many grows golden
GOLD_PAYS = 5      # and pays this many times over
HOT_PAYS = 2       # today's wanted crop pays double

# ---- Meteors and perfect days: what better code earns -------------------------------
# After the meteor job, space rocks sometimes land in the field at night. A
# rock stops the rover (a loop that drives into one is stuck behind it),
# look() says "rock", and drill("east") cracks it for more than any crop pays.
ROCK = "rock"
METEOR_ODDS = 3      # a meteor lands on about one night in this many
SHOWER_ODDS = 8      # and one meteor night in this many brings three
GEM_ODDS = 5         # one rock in this many has a space gem inside
ROCK_PAYS = 3        # a rock pays this many times the best crop the farm has
GEM_PAYS = 5         # and a gem in it, this many times more
# A day with no tick wasted (no bump, nothing picked too early, nothing
# planted twice, no drill at nothing) earns this many percent more.
PERFECT_PAYS = 50
PERFECT_PICKS = 3    # once it picks at least this many

# ---- What coins buy ------------------------------------------------------------
# Each list is the levels in order: the first is what a new farm starts with.
FIELDS = [   # (squares wide, squares tall, coins)
    (3, 1, 0), (3, 2, 15), (4, 3, 60), (5, 4, 240), (6, 5, 900), (7, 6, 5000), (8, 7, 25000)]
BATTERIES = [   # (ticks in a day, coins)
    (14, 0), (20, 20), (32, 70), (48, 260), (72, 900), (110, 3000), (170, 15000), (260, 60000)]
MEMORIES = [   # (lines of code the rover remembers, coins)
    (10, 0), (12, 30), (16, 160), (24, 700), (40, 3000)]
UPGRADES = {
    "field": {"icon": "🌾", "name": "Bigger field", "levels": FIELDS},
    "battery": {"icon": "🔋", "name": "Bigger battery", "levels": BATTERIES},
    "memory": {"icon": "🧠", "name": "More memory", "levels": MEMORIES},
}

# Things for the yard. They do nothing but look good, and say something when
# clicked ("big" ones are drawn larger). "cost" ones are in the shop. "crate" ones only come out of a 🎁
# crate, which every third order brings. "from" and "until" (month-day) keep
# one in the shop for part of the year only: once bought it stays.
DECOR = [
    {"key": "sign", "icon": "🪧", "name": "Farm sign", "cost": 10, "say": "Welcome to my farm!"},
    {"key": "tree", "icon": "🌳", "name": "Shady tree", "cost": 35, "say": "Rustle rustle."},
    {"key": "scarecrow", "icon": "🧑‍🌾", "name": "Scarecrow", "cost": 80, "say": "No crows today."},
    {"key": "chicken", "icon": "🐔", "name": "Chicken", "cost": 150, "say": "Bok bok!"},
    {"key": "barn", "big": True, "icon": "🏡", "name": "Barn", "cost": 400, "say": "Smells like hay."},
    {"key": "cow", "icon": "🐄", "name": "Space cow", "cost": 900, "say": "Mooooo."},
    {"key": "fountain", "icon": "⛲", "name": "Fountain", "cost": 2000, "say": "Splash!"},
    {"key": "tractor", "icon": "🚜", "name": "Old tractor", "cost": 4500, "say": "Vroom. Putt putt."},
    {"key": "statue", "icon": "🗿", "name": "Stone head", "cost": 10000, "say": "..."},
    {"key": "wheel", "big": True, "icon": "🎡", "name": "Big wheel", "cost": 25000, "say": "Wheee!"},
    {"key": "castle", "big": True, "icon": "🏰", "name": "Castle", "cost": 60000, "say": "Fit for a farm king."},
    {"key": "rocket", "big": True, "icon": "🚀", "name": "Your own rocket", "cost": 150000, "say": "3... 2... 1..."},
    {"key": "planet", "big": True, "icon": "🪐", "name": "Your own planet", "cost": 500000, "say": "It's all yours."},
    {"key": "turkey", "icon": "🦃", "name": "Turkey", "cost": 120, "say": "Gobble gobble!", "from": "11-01", "until": "11-30"},
    {"key": "snowman", "icon": "⛄", "name": "Snowman", "cost": 200, "say": "Brrr!", "from": "12-01", "until": "01-15"},
    {"key": "xmastree", "icon": "🎄", "name": "Twinkle tree", "cost": 350, "say": "Twinkle twinkle.", "from": "12-01", "until": "01-05"},
    {"key": "heartbush", "icon": "💝", "name": "Heart bush", "cost": 200, "say": "Aww.", "from": "02-01", "until": "02-20"},
    {"key": "clover", "icon": "🍀", "name": "Lucky clover", "cost": 200, "say": "Feeling lucky.", "from": "03-01", "until": "03-20"},
    {"key": "bunny", "icon": "🐇", "name": "Bunny", "cost": 250, "say": "Hop hop.", "from": "03-15", "until": "04-30"},
    {"key": "frog", "icon": "🐸", "name": "Frog", "crate": True, "say": "Ribbit."},
    {"key": "mushroom", "icon": "🍄", "name": "Giant mushroom", "crate": True, "say": "Boing."},
    {"key": "cat", "icon": "🐈", "name": "Farm cat", "crate": True, "say": "Meow."},
    {"key": "dog", "icon": "🐕", "name": "Farm dog", "crate": True, "say": "Woof!"},
    {"key": "rainbow", "big": True, "icon": "🌈", "name": "Rainbow", "crate": True, "say": "Ooooh."},
    {"key": "alien", "icon": "👽", "name": "Friendly alien", "crate": True, "say": "Greetings, farmer."},
    {"key": "dino", "big": True, "icon": "🦖", "name": "Dinosaur", "crate": True, "say": "RAWR!"},
    {"key": "ufo", "big": True, "icon": "🛸", "name": "Parked UFO", "crate": True, "say": "Bzzzzt."},
    {"key": "unicorn", "icon": "🦄", "name": "Unicorn", "crate": True, "say": "Neigh! ✨"},
    {"key": "dragon", "big": True, "icon": "🐉", "name": "Dragon", "crate": True, "say": "It's friendly. Probably."},
]
DECOR_BY_KEY = {d["key"]: d for d in DECOR}

# A title that grows with every coin the farm has ever earned.
TITLES = [(0, "🌱 Sprout"), (60, "🧑‍🌾 Farm Hand"), (400, "🚜 Farmer"), (2500, "🌾 Rancher"),
          (15000, "🏆 Tycoon"), (100000, "👑 Farm Legend")]

IDLE_DAYS = 25       # days 🔁 Auto runs with nobody touching the page
CRATE_EVERY = 3      # every third order brings a crate

# ---- Jobs: the first ones teach, one idea each ------------------------------------
# "code" is shown on the card, to type. "done" is checked after every day and
# every buy, against the farm and that day (None after a buy).

def _picked(day):
    return sum((day or {}).get("picked", {}).values())


def _planted(farm):
    return sum(1 for row in farm["field"] for cell in row if cell)


def _nothing_ripe(farm):
    return not any(cell and cell[0] in CROPS and cell[1] >= CROPS[cell[0]]["days"]
                   for row in farm["field"] for cell in row)


def _day(day, key):
    return (day or {}).get(key, 0)


JOBS = [
    {"key": "run", "title": "Pick your first berry",
     "say": "Your rover is on the first square, and the berry there is ripe. "
            "The code box already says  harvest() . Press ▶ Run a day.",
     "pay": 3, "done": lambda farm, day: _picked(day) >= 1},
    {"key": "drive", "title": "Drive and pick",
     "say": "More berries are ripe. Drive east to each one and pick it. Type this:",
     "code": "east()\nharvest()\neast()\nharvest()\n",
     # Or there's nothing left to pick: a student who picked them all on the
     # first day goes straight on to planting.
     "pay": 4, "done": lambda farm, day: _picked(day) >= 2 or _nothing_ripe(farm)
     or (_picked(day) >= 1 and (day or {}).get("moved", 0) >= 1)},
    {"key": "plant", "title": "Plant for tomorrow",
     "say": "The field is empty now. A whole farm day is: pick, plant, drive. "
            "Type this, and the berries will be ripe tomorrow:",
     "code": 'harvest()\nplant("berry")\neast()\nharvest()\nplant("berry")\neast()\nharvest()\nplant("berry")\n',
     "pay": 5, "done": lambda farm, day: day is not None and _planted(farm) >= 3},
    {"key": "again", "title": "They grew!",
     "say": "Run the same code again. That's the trick of a program: write it once, "
            "use it every day. Pick 3 berries in one day.",
     "pay": 5, "done": lambda farm, day: _picked(day) >= 3},
    {"key": "field", "title": "A bigger field",
     "say": "You have coins! Open the 🛒 Shop and buy 🌾 Bigger field. "
            "(🔁 Auto runs your code day after day while you watch.)",
     "pay": 5, "done": lambda farm, day: farm["field_level"] >= 1},
    {"key": "loop", "title": "Teach your rover a loop",
     "say": "Your rover only remembers 10 lines, and the field keeps growing. "
            "A loop says it once and repeats it. Change your code to this:",
     "code": 'for i in range(3):\n    harvest()\n    plant("berry")\n    east()\n',
     "pay": 10, "done": lambda farm, day: _picked(day) >= 3 and "for" in (day or {}).get("ideas", ())},
    {"key": "battery", "title": "More battery",
     "say": "Two rows need more battery than you have. Open the 🛒 Shop and buy 🔋 Bigger battery.",
     "pay": 5, "done": lambda farm, day: farm["battery_level"] >= 1},
    {"key": "rows", "title": "Farm both rows",
     "say": "Go along the top row, drive south, and come back along the bottom row. "
            "The new squares are empty, so plant today and pick tomorrow. Pick 6 in one day:",
     "code": 'for i in range(3):\n    harvest()\n    plant("berry")\n    east()\nsouth()\n'
             'for i in range(3):\n    harvest()\n    plant("berry")\n    west()\n',
     "pay": 15, "done": lambda farm, day: _picked(day) >= 6},
    {"key": "carrot", "title": "A new crop",
     "say": "Open the 🛒 Shop and buy 🥕 Moon carrots. Each one pays 3 coins.",
     "pay": 10, "done": lambda farm, day: "carrot" in farm["crops"]},
    {"key": "if", "title": "Only pick what's ripe",
     "say": "Carrots take 2 days. Picking one too early gets nothing and wastes battery. "
            "So ask first:  if ripe():  picks only when it's ready, and  if empty():  "
            "plants only where there's room. Pick a carrot with code like this:",
     "code": 'for i in range(3):\n    if ripe():\n        harvest()\n    if empty():\n        plant("carrot")\n    east()\n',
     "pay": 20, "done": lambda farm, day: (day or {}).get("picked", {}).get("carrot", 0) >= 1
     and "if" in (day or {}).get("ideas", ())},
    {"key": "memory", "title": "More memory",
     "say": "The next trick takes 12 lines, and your rover remembers 10. "
            "Open the 🛒 Shop and buy 🧠 More memory.",
     "pay": 5, "done": lambda farm, day: farm["memory_level"] >= 1},
    {"key": "def", "title": "Teach your rover a trick",
     "say": "def gives a name to some lines, so you can use them again and again. "
            "This makes a trick called care, and uses it on every square:",
     "code": 'def care():\n    if ripe():\n        harvest()\n    if empty():\n        plant("carrot")\n'
             'for i in range(3):\n    care()\n    east()\nsouth()\nfor i in range(3):\n    care()\n    west()\n',
     "pay": 30, "done": lambda farm, day: _picked(day) >= 3 and "def" in (day or {}).get("ideas", ())},
    {"key": "while", "title": "A loop that looks",
     "say": "Your field will get wider. A while loop looks instead of counting, so it works "
            "however wide the field is. This one drives until the fence, then does the last "
            "square. Pick 2 or more on a day that uses while:",
     "code": 'while look("east") != "fence":\n    harvest()\n    plant("berry")\n    east()\n'
             'harvest()\nplant("berry")\n',
     "pay": 40, "done": lambda farm, day: _picked(day) >= 2 and "while" in (day or {}).get("ideas", ())},
    {"key": "meteor", "title": "A meteor!",
     "say": "A meteor crashed into your field! 🪨 Your rover can't drive through rock, so a loop "
            "that drives east gets stuck. Look first, then drill it. A rock pays more than any crop, "
            "and some have a 💎 inside. Drill the rock:",
     "code": 'while look("east") != "fence":\n    if look("east") == "rock":\n        drill("east")\n'
             '    harvest()\n    plant("berry")\n    east()\nharvest()\nplant("berry")\n',
     "pay": 40, "done": lambda farm, day: _day(day, "drilled") >= 1},
    {"key": "perfect", "title": "A perfect day",
     "say": "A tick that does nothing is wasted: a bump, picking too early, planting where "
            "something grows. A day with no wasted ticks is ✨ Perfect, and pays 50% more! "
            "Ask before you act. Pick 3 or more with no wasted ticks:",
     "code": 'def care():\n    if ripe():\n        harvest()\n    if empty():\n        plant("berry")\n'
             'while look("east") != "fence":\n    care()\n    if look("east") == "rock":\n'
             '        drill("east")\n    east()\ncare()\n',
     "pay": 60, "done": lambda farm, day: bool(_day(day, "perfect"))},
]
METEOR_JOB = next(i for i, job in enumerate(JOBS) if job["key"] == "meteor")

# ---- Words -----------------------------------------------------------------------

LOOK_WORDS = {"fence", "empty", "growing", "ripe", ROCK}
FARM_COMMANDS = ("harvest", "plant", "dig", "drill")
FARM_SENSORS = ("ripe", "empty", "crop", "x", "y", "width", "height", "battery", "coins", "day")
FARM_WORDS = ('north(), south(), east(), west(), harvest(), plant("berry"), drill("east"), '
              'dig() and wait()')
PLANT_HOW = 'plant() needs a crop in quotes, like  plant("berry")'
PICK = "To pick the plant under the rover, write  harvest()"
SOW = 'To put a plant in the ground, write  plant("berry")'
BREAK = 'To break a rock, write  drill("east")  with the way the rock is'
GUESSES = {
    "pick": PICK, "pickup": PICK, "pick_up": PICK, "collect": PICK, "grab": PICK, "get": PICK,
    "take": PICK, "harvests": PICK, "havest": PICK,
    "seed": SOW, "sow": SOW, "grow": SOW, "plants": SOW, "put": SOW,
    "sell": "Crops sell by themselves as the rover picks them: no command needed.",
    "water": "These plants don't need water. They grow overnight.",
    "remove": "To clear a square, write  dig()", "clear": "To clear a square, write  dig()",
    "is_ripe": "Here it's  ripe()", "is_empty": "Here it's  empty()",
    "smash": BREAK, "crack": BREAK, "mine": BREAK, "blast": BREAK, "hit": BREAK, "drills": BREAK,
}


class Field:
    """One farm day: the field, the rover on it, and the replay."""

    def __init__(self, farm, hot):
        self.w, self.h = FIELDS[farm["field_level"]][:2]
        self.cells = copy.deepcopy(farm["field"])
        self.x = self.y = 1
        self.t = 0
        self.battery = BATTERIES[farm["battery_level"]][0]
        self.coins, self.days, self.seed, self.hot = farm["coins"], farm["day"], farm["seed"], hot
        self.owned = farm["crops"]
        self.line = None
        self.typed = False     # the planet's rover sets this: nothing here reads it
        self.prints = []
        self.frames = []
        self.end = None
        self.income = 0
        self.picked = {}       # crop -> how many
        self.golden = 0
        self.early = self.nothing = self.full = self.bumps = self.planted = 0
        self.rocked = self.missed = self.drilled = self.gems = 0

    # What the Rover calls on its world.
    def note(self, line):
        self.prints.append({"t": self.t, "text": line})
        del self.prints[:-MAX_PRINTS]

    def cell(self, x, y):
        return self.cells[y - 1][x - 1]

    def is_ripe(self, cell):
        return bool(cell) and cell[0] in CROPS and cell[1] >= CROPS[cell[0]]["days"]

    def wasted(self):
        """Ticks that did nothing."""
        return self.early + self.nothing + self.full + self.bumps + self.missed

    def frame(self, do, **more):
        self.frames.append(dict(more, x=self.x, y=self.y, line=self.line, do=do))
        self.t += 1
        self.battery -= 1
        if self.battery <= 0:
            self.end = "flat"
            raise _End()

    def act(self, name, way=None):
        if name == "wait":
            self.frame("wait")
            return
        if name == "drill":
            self.drill(way)
            return
        dr, dc = DIRS[COMPASS[name]]
        x, y = self.x + dc, self.y + dr
        if not (1 <= x <= self.w and 1 <= y <= self.h):
            self.bumps += 1
            self.frame("bump", way=name)
            return
        if self.is_rock(x, y):
            self.bumps += 1
            self.rocked += 1
            self.frame("bump", way=name, rock=True)
            return
        self.x, self.y = x, y
        self.frame("move")

    def is_rock(self, x, y):
        return 1 <= x <= self.w and 1 <= y <= self.h and bool(self.cell(x, y)) \
            and self.cell(x, y)[0] == ROCK

    def drill(self, way):
        """drill(way): the rock on the next square that way cracks, and sells."""
        dr, dc = DIRS[COMPASS[way]]
        x, y = self.x + dc, self.y + dr
        if not self.is_rock(x, y):
            self.missed += 1
            self.frame("nodrill", way=way)
            return
        gem = bool(self.cell(x, y)[2])
        pay = rock_pay(self.owned) * (GEM_PAYS if gem else 1)
        self.cells[y - 1][x - 1] = None
        self.drilled += 1
        self.gems += gem
        self.income += pay
        self.coins += pay
        self.frame("drill", way=way, at=[x, y], pay=pay, gem=gem)

    def look(self, way):
        dr, dc = DIRS[COMPASS[way]]
        x, y = self.x + dc, self.y + dr
        if not (1 <= x <= self.w and 1 <= y <= self.h):
            return "fence"
        cell = self.cell(x, y)
        return "empty" if not cell else ROCK if cell[0] == ROCK else "ripe" if self.is_ripe(cell) else "growing"

    def sense(self, name):
        cell = self.cell(self.x, self.y)
        if name == "ripe":
            return self.is_ripe(cell)
        if name == "empty":
            return not cell
        if name == "crop":
            return cell[0] if cell else "none"
        if name in ("x", "y", "battery", "coins"):
            return getattr(self, name)
        if name == "width":
            return self.w
        if name == "height":
            return self.h
        if name == "day":
            return self.days + 1
        if name == "harvest":
            return self.harvest()
        if name == "dig":
            self.cells[self.y - 1][self.x - 1] = None
            self.frame("dig")
        return None

    def harvest(self):
        cell = self.cell(self.x, self.y)
        if not cell:
            self.nothing += 1
            self.frame("nothing")
        elif not self.is_ripe(cell):
            self.early += 1
            self.frame("early")
        else:
            crop, gold = cell[0], bool(cell[2])
            pay = CROPS[crop]["pay"] * (GOLD_PAYS if gold else 1) * (HOT_PAYS if crop == self.hot else 1)
            self.cells[self.y - 1][self.x - 1] = None
            self.picked[crop] = self.picked.get(crop, 0) + 1
            self.golden += gold
            self.income += pay
            self.coins += pay
            self.frame("pick", crop=crop, pay=pay, gold=gold)

    def plant(self, crop):
        if self.cell(self.x, self.y):
            self.full += 1
            self.frame("full")
            return
        gold = zlib.crc32(f"{self.seed}:{self.days}:{self.x}:{self.y}".encode()) % GOLD_ODDS == 0
        self.cells[self.y - 1][self.x - 1] = [crop, 0, int(gold)]
        self.planted += 1
        self.frame("plant", crop=crop, gold=gold)


class Farmer(Rover):
    """A student's program for one farm day."""
    look_words = LOOK_WORDS

    def __init__(self, code, field):
        names = COMMANDS + FARM_COMMANDS + FARM_SENSORS + ("look",)
        super().__init__(code, field, dict.fromkeys(names))

    def eval(self, node, frame):
        # look() compared with a word it never says here: the planet's own
        # check would offer "rock" and "crater".
        if isinstance(node, ast.Compare):
            sides = [node.left] + node.comparators
            if any(isinstance(s, ast.Call) and getattr(s.func, "id", "") == "look" for s in sides):
                for s in sides:
                    if isinstance(s, ast.Constant) and isinstance(s.value, str) and s.value not in LOOK_WORDS:
                        raise BotError(f'look() never gives back "{s.value}" on the farm. It says '
                                       f'"fence", "empty", "growing", "ripe" or "rock".')
        return super().eval(node, frame)

    def lookup(self, name, frame):
        if not self.mine(name, frame) and name.lower() in CROPS:
            raise BotError(f'Put quotes round the crop:  plant("{name.lower()}")')
        return super().lookup(name, frame)

    def run_statement(self, node, frame):
        if isinstance(node, ast.FunctionDef) and node.name in FARM_COMMANDS + FARM_SENSORS:
            raise BotError(f"{node.name}() is already one of the rover's farm words. Pick "
                           f"another name, like  def my_{node.name}():")
        super().run_statement(node, frame)

    def call(self, node, frame):
        name = node.func.id if isinstance(node.func, ast.Name) else None
        if name == "plant":
            if len(node.args) != 1:
                raise BotError(PLANT_HOW)
            arg = node.args[0]
            # plant(berry) without quotes is forgiven, as look(east) is.
            crop = arg.id.lower() if isinstance(arg, ast.Name) and arg.id.lower() in CROPS \
                and not self.mine(arg.id, frame) else self.eval(arg, frame)
            if not isinstance(crop, str) or crop.strip().lower() not in CROPS:
                said = f'"{crop}"' if isinstance(crop, str) else repr(crop)
                have = ", ".join(f'"{c}"' for c in self.world.owned)
                raise BotError(f"{said} isn't a crop. You can plant: {have}.")
            crop = crop.strip().lower()
            if crop not in self.world.owned:
                raise BotError(f"You don't have {CROPS[crop]['name'].lower()} seeds yet. "
                               f"Buy them in the 🛒 Shop for {CROPS[crop]['cost']} coins.")
            self.world.plant(crop)
            return None
        if name in GUESSES and name not in self.funcs and name not in self.defs:
            raise BotError(GUESSES[name])
        if name and name not in self.sensors and name not in self.funcs and name not in self.defs \
                and (name in planet.SENSOR_ZONE or name in planet.OWN_COMMANDS):
            raise BotError(f"{name}() is for missions on the planet. On the farm your rover "
                           f"knows {FARM_WORDS}.")
        return super().call(node, frame)


def ideas(tree):
    """The big ideas a program uses, for the jobs and for the teacher."""
    found = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.For):
            found.add("for")
            if any(isinstance(n, (ast.For, ast.While)) for body in node.body for n in ast.walk(body)):
                found.add("nested")
        elif isinstance(node, ast.While):
            found.add("while")
        elif isinstance(node, ast.If):
            found.add("if")
        elif isinstance(node, ast.FunctionDef):
            found.add("def")
        elif isinstance(node, ast.Assign):
            found.add("variable")
    return found


# ---- The farm itself, kept in the student's save ------------------------------------

def new_farm(seed):
    """A farm on its first morning: three ripe berries and the first job."""
    return {"coins": 0, "earned": 0, "day": 0, "seed": seed,
            "field_level": 0, "battery_level": 0, "memory_level": 0,
            "field": [[["berry", 1, 0] for _ in range(FIELDS[0][0])]],
            "crops": ["berry"], "decor": [], "code": "harvest()\n",
            "best": 0, "job": 0, "job_tries": 0, "order": None, "orders": 0,
            "picked": {}, "golden": 0, "ideas": [], "last": None}


def hot_crop(today):
    """The crop the space station wants today: the same for the whole class."""
    keys = list(CROPS)
    return keys[zlib.crc32(f"market:{today}".encode()) % len(keys)]


def in_season(item, today):
    """Is a part-of-the-year thing in the shop today? today is YYYY-MM-DD."""
    if "from" not in item:
        return True
    now, start, end = today[5:], item["from"], item["until"]
    return start <= now <= end if start <= end else now >= start or now <= end


def title(farm):
    return [name for coins, name in TITLES if farm["earned"] >= coins][-1]


def grow(farm):
    """A night passes: everything in the ground is a day older. A plant that
    has to stand alone waits while one of its own kind is beside it."""
    field = farm["field"]
    shaded = 0
    blocked = set()
    for y, row in enumerate(field):
        for x, cell in enumerate(row):
            if cell and cell[0] in CROPS and CROPS[cell[0]].get("alone"):
                for dy, dx in DIRS:
                    yy, xx = y + dy, x + dx
                    if 0 <= yy < len(field) and 0 <= xx < len(row) and field[yy][xx] \
                            and field[yy][xx][0] == cell[0]:
                        blocked.add((x, y))
    for y, row in enumerate(field):
        for x, cell in enumerate(row):
            if not cell or cell[0] not in CROPS:
                continue
            if (x, y) in blocked and cell[1] < CROPS[cell[0]]["days"]:
                shaded += 1
            else:
                cell[1] = min(cell[1] + 1, CROPS[cell[0]]["days"])
    return shaded


def rock_pay(crops):
    return ROCK_PAYS * max(CROPS[c]["pay"] for c in crops)


def meteors(farm):
    """Space rocks landing in the night, once the farm has learnt to drill
    them. Never on the rover's square or a golden plant, and never so many
    that a field ignoring them fills up. Returns where they landed."""
    if farm["job"] <= METEOR_JOB or farm["field_level"] < 1:
        return []
    roll = zlib.crc32(f"{farm['seed']}:meteor:{farm['day']}".encode())
    if roll % METEOR_ODDS:
        return []
    field = farm["field"]
    w, h = len(field[0]), len(field)
    room = max(1, w * h // 5) - sum(1 for row in field for cell in row if cell and cell[0] == ROCK)
    spots = [(x, y) for y in range(h) for x in range(w)
             if (x, y) != (0, 0) and not (field[y][x] and (field[y][x][0] == ROCK or field[y][x][2]))]
    many = 3 if roll // METEOR_ODDS % SHOWER_ODDS == 0 else 1
    landed = []
    for k in range(min(many, room, len(spots))):
        pick = zlib.crc32(f"{farm['seed']}:rock:{farm['day']}:{k}".encode())
        x, y = spots.pop(pick % len(spots))
        field[y][x] = [ROCK, 0, int(pick // 7 % GEM_ODDS == 0)]
        landed.append([x + 1, y + 1])
    return landed


def lesson_rock(farm):
    """The meteor job's own rock, east of where the rover starts, with a gem in it."""
    if farm["job"] == METEOR_JOB and not any(cell and cell[0] == ROCK for row in farm["field"] for cell in row):
        farm["field"][0][1] = [ROCK, 0, 1]


def next_order(farm):
    """An order from the space station: so many of one crop, for a bonus."""
    n = farm["orders"]
    pick = zlib.crc32(f"{farm['seed']}:order:{n}:{farm.get('skips', 0)}".encode())
    crop = farm["crops"][pick % len(farm["crops"])]
    w, h = FIELDS[farm["field_level"]][:2]
    need = max(3, w * h * (1 + pick // 7 % 3) // CROPS[crop]["days"])
    return {"crop": crop, "need": need, "have": 0, "pay": need * CROPS[crop]["pay"] * 2,
            "crate": n % CRATE_EVERY == CRATE_EVERY - 1}


def skip_order(farm):
    """A different order, for free: a stuck order shouldn't sit there for ever."""
    if farm["order"]:
        farm["skips"] = farm.get("skips", 0) + 1
        farm["order"] = next_order(farm)


def open_crate(farm):
    """Something for the yard that can't be bought, or coins once they have them all."""
    left = [d for d in DECOR if d.get("crate") and d["key"] not in farm["decor"]]
    if not left:
        coins = 50 * (farm["field_level"] + 1) ** 2
        farm["coins"] += coins
        farm["earned"] += coins
        return {"coins": coins}
    item = left[zlib.crc32(f"{farm['seed']}:crate:{farm['orders']}".encode()) % len(left)]
    farm["decor"].append(item["key"])
    return {"key": item["key"], "icon": item["icon"], "name": item["name"]}


def check_jobs(farm, day=None):
    """Pay for every job the farm has just finished, in order. A day counts
    for one job only, so each new idea gets a run of its own."""
    done = []
    while farm["job"] < len(JOBS):
        job = JOBS[farm["job"]]
        if not job["done"](farm, day):
            break
        farm["job"] += 1
        farm["job_tries"] = 0
        farm["coins"] += job["pay"]
        farm["earned"] += job["pay"]
        done.append({"title": job["title"], "pay": job["pay"]})
        if day is not None:
            day = None
    if farm["job"] >= len(JOBS) and not farm["order"]:
        farm["order"] = next_order(farm)
    return done


def check_order(farm, picked):
    """Count a day's crops towards the order. Returns it once it's filled."""
    order = farm["order"]
    if not order:
        return None
    order["have"] = min(order["need"], order["have"] + picked.get(order["crop"], 0))
    if order["have"] < order["need"]:
        return None
    farm["coins"] += order["pay"]
    farm["earned"] += order["pay"]
    filled = dict(order, crate=open_crate(farm) if order["crate"] else None)
    farm["orders"] += 1
    farm["order"] = next_order(farm)
    return filled


def tips(field, error, memory_full, learning=False):
    """One or two plain lines on what would make tomorrow better."""
    out = []
    if error or memory_full:
        return out
    if field.rocked:
        n = field.rocked
        out.append(f"🪨 A rock blocked your rover {n} time{'s' if n > 1 else ''}. Look first, then "
                   f'drill it:  if look("east") == "rock":  then  drill("east")')
    if field.missed and len(out) < 2:
        n = field.missed
        out.append(f"⛏ drill() found no rock {n} time{'s' if n > 1 else ''}. Ask first:  "
                   f'if look("east") == "rock":')
    if field.end == "flat" and len(out) < 2:
        out.append(f"🔋 The battery ran out on line {field.line}. Everything picked today still counts. "
                   f"A bigger battery is in the 🛒 Shop.")
    if field.early and len(out) < 2:
        n = field.early
        out.append(f"🌱 {n} plant{'s weren' if n > 1 else ' wasn'}'t ripe yet, and trying to pick "
                   f"{'them' if n > 1 else 'it'} used {n} tick{'s' if n > 1 else ''} of battery. "
                   f"Ask first:  if ripe():")
    if field.full and len(out) < 2:
        n = field.full
        out.append(f"🌱 {n} square{'s' if n > 1 else ''} already had a plant, so plant() did nothing "
                   f"there. Ask first:  if empty():")
    if field.nothing and not field.early and not field.planted and len(out) < 2:
        n = field.nothing
        # Before planting has been taught, point at the berries that are left.
        out.append("There was nothing left to pick on that square. The other berries are "
                   "further east: drive there first with  east()" if learning else
                   f"There was nothing to pick on {n} square{'s' if n > 1 else ''}. "
                   f'Plant there for tomorrow:  plant("berry")')
    if field.bumps - field.rocked >= 4 and len(out) < 2:
        out.append(f"The rover bumped the fence {field.bumps - field.rocked} times. The field is {field.w} wide "
                   f"and {field.h} tall.")
    if not field.frames and not out:
        out.append("The rover didn't do anything today. Give it a command, like  harvest()")
    return out[:2]


def run_day(farm, code, stars=0, today="2000-01-01"):
    """Run a program as one farm day, and bank what it earns. Changes farm."""
    code = str(code)[:MAX_CODE + 1]
    lesson_rock(farm)
    hot = hot_crop(today)
    field = Field(farm, hot)
    memory = MEMORIES[farm["memory_level"]][0]
    lines = code_lines(code)
    error = line = farmer = None
    full = lines > memory
    try:
        if full:
            raise BotError(f"🧠 Your rover remembers {memory} lines, and your program is {lines}. "
                           f"Put the part that repeats in a loop, or buy 🧠 More memory in the 🛒 Shop.")
        farmer = Farmer(code, field)
        farmer.run()
    except _End:
        pass
    except _TooLong as e:
        error, line = str(e), e.line
        if e.in_loop == "while":
            error = ("Your program ran too long. A while loop needs something inside it that "
                     "changes what it asks, like  east()  or  harvest()")
    except BotError as e:
        error, line = str(e), e.line or getattr(e, "syntax_line", None)
    except RecursionError:
        error = "Your functions call each other too deeply."
    start = farm["field"]
    used = sorted(ideas(farmer.tree)) if farmer else []
    out = {"error": error, "line": line, "memory_full": full, "frames": field.frames,
           "start": start, "prints": field.prints, "end": "error" if error else field.end or "done",
           "ticks": field.t, "battery": BATTERIES[farm["battery_level"]][0],
           "income": 0, "bonus": 0, "picked": {}, "golden": 0, "hot": hot,
           "say": tips(field, error, full, farm["job"] < 2 and not _nothing_ripe(farm)),
           "jobs": [], "order": None, "counted": False,
           "ideas": used, "best": False, "shaded": 0, "meteors": [],
           "drilled": 0, "gems": 0, "perfect": 0, "wasted": field.wasted()}
    farm["code"] = code[:MAX_CODE]
    if farmer:
        farm["ideas"] = sorted(set(farm["ideas"]) | set(used))
    # A day the rover never moved in (the code couldn't be read, or stopped on
    # its first line) isn't used up: nothing happened, so nothing grows.
    if error and not field.frames:
        if farm["job"] < len(JOBS):
            farm["job_tries"] += 1
        return out
    bonus = field.income * stars // 100
    perfect = not error and not field.wasted() and _picked({"picked": field.picked}) >= PERFECT_PICKS
    extra = field.income * PERFECT_PAYS // 100 if perfect else 0
    farm["field"] = field.cells
    farm["coins"] += field.income + bonus + extra
    farm["earned"] += field.income + bonus + extra
    farm["day"] += 1
    farm["golden"] += field.golden
    for crop, n in field.picked.items():
        farm["picked"][crop] = farm["picked"].get(crop, 0) + n
    total = field.income + bonus + extra
    out.update(counted=True, income=field.income, bonus=bonus, picked=field.picked,
               golden=field.golden, best=total > farm["best"] and farm["day"] > 1,
               drilled=field.drilled, gems=field.gems, perfect=extra)
    farm["best"] = max(farm["best"], total)
    day = {"picked": field.picked, "ideas": used, "drilled": field.drilled, "perfect": perfect,
           "moved": sum(1 for f in field.frames if f["do"] == "move")}
    before = farm["job"]
    out["jobs"] = check_jobs(farm, day)
    if farm["job"] == before and farm["job"] < len(JOBS):
        farm["job_tries"] += 1
    if before >= len(JOBS):
        out["order"] = check_order(farm, field.picked)
    out["shaded"] = grow(farm)
    out["meteors"] = meteors(farm)
    if out["shaded"] and len(out["say"]) < 2:
        n = out["shaded"]
        out["say"].append(f"🌻 {n} sun bloom{'s' if n > 1 else ''} didn't grow: one of its own kind is "
                          f"on the square beside it. Leave a gap, like a chess board.")
    return out


def price(kind, key, farm, today):
    """What something costs this farm now, or why it can't be bought."""
    if kind == "upgrade" and key in UPGRADES:
        levels, at = UPGRADES[key]["levels"], farm[f"{key}_level"]
        return (levels[at + 1][-1], None) if at + 1 < len(levels) else (None, "That's as big as it gets!")
    if kind == "crop" and key in CROPS:
        return (None, "You already have those seeds.") if key in farm["crops"] else (CROPS[key]["cost"], None)
    if kind == "decor" and key in DECOR_BY_KEY:
        item = DECOR_BY_KEY[key]
        if key in farm["decor"]:
            return None, "You already have that."
        if "cost" not in item:
            return None, "That only comes out of a 🎁 crate."
        if not in_season(item, today):
            return None, "That isn't in the shop today."
        return item["cost"], None
    return None, "The shop doesn't have that."


def buy(farm, kind, key, today="2000-01-01"):
    """Spend coins. Returns {"error"} or what was bought and the jobs it finished."""
    cost, why = price(kind, key, farm, today)
    if cost is None:
        return {"error": why}
    if farm["coins"] < cost:
        return {"error": f"That costs {cost} coins, and you have {farm['coins']}. "
                         f"Run a few more days!"}
    farm["coins"] -= cost
    if kind == "upgrade":
        farm[f"{key}_level"] += 1
        if key == "field":
            # The same plants, in a bigger field: the new squares are empty.
            w, h = FIELDS[farm["field_level"]][:2]
            old = farm["field"]
            farm["field"] = [[old[y][x] if y < len(old) and x < len(old[y]) else None
                              for x in range(w)] for y in range(h)]
        name = UPGRADES[key]["name"]
    elif kind == "crop":
        farm["crops"].append(key)
        name = CROPS[key]["name"]
    else:
        farm["decor"].append(key)
        name = DECOR_BY_KEY[key]["name"]
    return {"bought": name, "jobs": check_jobs(farm)}


def shop(farm, today):
    """Everything in the shop, with what this farm has and can afford."""
    coins = farm["coins"]
    upgrades = []
    for key, up in UPGRADES.items():
        levels, at = up["levels"], farm[f"{key}_level"]
        nxt = levels[at + 1] if at + 1 < len(levels) else None
        size = (lambda lv: f"{lv[0]} by {lv[1]}") if key == "field" else \
            (lambda lv: f"{lv[0]} ticks") if key == "battery" else (lambda lv: f"{lv[0]} lines")
        upgrades.append({"key": key, "icon": up["icon"], "name": up["name"], "now": size(levels[at]),
                         "next": nxt and size(nxt), "cost": nxt and nxt[-1],
                         "can": bool(nxt) and coins >= nxt[-1]})
    crops = [{"key": key, "icon": c["icon"], "name": c["name"], "days": c["days"], "pay": c["pay"],
              "about": c["about"], "cost": c["cost"], "have": key in farm["crops"],
              "can": key not in farm["crops"] and coins >= c["cost"]} for key, c in CROPS.items()]
    decor = [{"key": d["key"], "icon": d["icon"], "name": d["name"], "cost": d.get("cost"),
              "have": d["key"] in farm["decor"], "crate": bool(d.get("crate")),
              "until": d.get("until") if "cost" in d else None,
              "can": d["key"] not in farm["decor"] and "cost" in d and coins >= d["cost"]}
             for d in DECOR if d["key"] in farm["decor"] or d.get("crate") or in_season(d, today)]
    return {"upgrades": upgrades, "crops": crops, "decor": decor}


def yard(farm):
    """What anyone may see of a farm: the field and the things round it."""
    w, h = FIELDS[farm["field_level"]][:2]
    return {"w": w, "h": h, "field": farm["field"], "title": title(farm), "day": farm["day"],
            "decor": [{"key": k, "icon": DECOR_BY_KEY[k]["icon"], "name": DECOR_BY_KEY[k]["name"],
                       "say": DECOR_BY_KEY[k]["say"], "big": bool(DECOR_BY_KEY[k].get("big"))}
                      for k in farm["decor"] if k in DECOR_BY_KEY]}


def view(farm, stars=0, today="2000-01-01"):
    """Everything the student's page shows."""
    lesson_rock(farm)
    job = JOBS[farm["job"]] if farm["job"] < len(JOBS) else None
    order = farm["order"]
    hot = hot_crop(today)
    nxt = FIELDS[farm["field_level"] + 1] if farm["field_level"] + 1 < len(FIELDS) else None
    out = dict(yard(farm), coins=farm["coins"], earned=farm["earned"], best=farm["best"],
               code=farm["code"], battery=BATTERIES[farm["battery_level"]][0],
               memory=MEMORIES[farm["memory_level"]][0], crops=farm["crops"],
               stars=stars, golden=farm["golden"], orders=farm["orders"],
               hot={"key": hot, "icon": CROPS[hot]["icon"], "name": CROPS[hot]["name"],
                    "have": hot in farm["crops"]},
               next_field=nxt and {"w": nxt[0], "h": nxt[1], "cost": nxt[2]},
               shop=shop(farm, today), idle_days=IDLE_DAYS,
               icons={key: c["icon"] for key, c in CROPS.items()},
               days={key: c["days"] for key, c in CROPS.items()})
    out["job"] = job and {"n": farm["job"] + 1, "of": len(JOBS), "title": job["title"], "say": job["say"],
                          "code": job.get("code"), "pay": job["pay"],
                          "give": bool(job.get("code")) and farm["job_tries"] >= 2}
    out["order"] = order and dict(order, icon=CROPS[order["crop"]]["icon"],
                                  name=CROPS[order["crop"]]["name"])
    return out
