"""
Cake Shop: bake and decorate cakes for customers with Python.

Customers walk in with orders. Students write a program that bakes the cake
one step at a time, and the customer reacts: delighted, or politely puzzled
("I asked for 3 layers, but this has 2!"), which is the debugging feedback.

    layer("vanilla")        add a sponge layer (bottom first)
    frosting("pink")        frost the cake (top and between the layers)
    drip("chocolate")       a drip running down the sides
    sprinkles()             rainbow sprinkles, or sprinkles("pink")
    swirl("white")          one piped swirl on the rim
    topping("cherry")       one topping on top
    candle()                one candle, or candle("blue")
    write("Hi Gran")        writing on the front, or write("Hi Gran", "pink")
    tier()                  start a smaller cake on top

From Chapter 3 on, the same program bakes for every customer in the queue,
and each one's ticket is in a dictionary called  order , so the program has to
read it: layer(order["flavour"]).

Student code runs in the Light Cycles interpreter (cycles.Brain), extended
with what a bakery needs: lists, dictionaries, for loops over lists, f-strings,
`in`, slices and a few text and list methods (.upper() .append() ...). It is
still a whitelist of the parse tree: no imports, no other attribute access and
no real builtins ever run on the teacher's laptop.
"""

import ast
import collections
import difflib
import random
import re
import zlib

from cycles import BotError, Brain, _Break, _Continue, _Frame, _TooLong, syntax_message

PROGRAM_BUDGET = 100_000   # interpreter operations for one cake
MAX_CODE = 4000            # characters in one program
MAX_PRINTS = 60            # print() lines kept per cake: the LAST ones
MAX_TEXT = 200             # characters in one piece of text
MAX_LIST = 200             # items in one list
MAX_STEPS = 600            # kitchen steps in one cake
MAX_TIERS = 4
MAX_LAYERS = 10            # per tier
MAX_CANDLES = 120          # per tier: enough for a dragon
MAX_TOPPINGS = 40          # per tier
MAX_SWIRLS = 40            # per tier
MAX_MESSAGE = 40           # characters written on a cake

# ---- the pantry ------------------------------------------------------------

FLAVOURS = {
    "vanilla": "#f7e1ae", "chocolate": "#7b4a2d", "strawberry": "#f6a3b6",
    "lemon": "#fbe07a", "orange": "#f8ae5c", "lime": "#bde27c",
    "blueberry": "#8ba5e6", "grape": "#ad87d6", "cherry": "#e15a66",
    "red velvet": "#ad2a3e", "caramel": "#d89c62", "mint": "#a6e3c9",
    "coconut": "#fbf7ee", "cookies": "#e6d8c0", "matcha": "#9cc386",
    "banana": "#f6e6a0",
}
COLOURS = {
    "white": "#fffcf6", "cream": "#fbeccd", "pink": "#f9a6c8", "red": "#e5474f",
    "orange": "#f99a3d", "yellow": "#fbd648", "green": "#79cc66", "mint": "#97e1c4",
    "blue": "#68a4ee", "purple": "#a479df", "lavender": "#cdb5f3",
    "chocolate": "#5b3220", "caramel": "#c98945", "black": "#2c2730",
}
SPECIALS = ["glitter", "galaxy", "rainbow", "gold"]   # frosting, drip, swirl, candle
TOPPINGS = {
    "cherry": "🍒", "strawberry": "🍓", "blueberry": "🫐", "lemon": "🍋",
    "heart": "❤️", "star": "⭐", "flower": "🌸", "fish": "🐟", "coin": "🪙",
    "cookie": "🍪", "candy": "🍬", "chocolate": "🍫", "bow": "🎀",
    "lollipop": "🍭", "leaf": "🍃",
    # These unlock with stars (UNLOCKS below).
    "butterfly": "🦋", "ghost": "👻", "pumpkin": "🎃", "rainbow": "🌈",
    "crown": "👑", "unicorn": "🦄", "gem": "💎", "moon": "🌙", "rocket": "🚀",
    "dragon": "🐉", "teddy": "🧸", "planet": "🪐", "fireworks": "🎆", "disco": "🪩",
}

# Unlocked by the student's own stars, or by the whole class's star meter.
# Stands and wallpapers are the look of the shop, picked on the page.
UNLOCKS = [
    {"kind": "stand", "key": "board", "stars": 1},
    {"kind": "topping", "key": "butterfly", "stars": 2},
    {"kind": "topping", "key": "ghost", "stars": 4},
    {"kind": "special", "key": "glitter", "stars": 5},
    {"kind": "topping", "key": "pumpkin", "stars": 6},
    {"kind": "stand", "key": "glass", "stars": 8},
    {"kind": "topping", "key": "rainbow", "stars": 9},
    {"kind": "wallpaper", "key": "mint", "stars": 10},
    {"kind": "topping", "key": "crown", "stars": 12},
    {"kind": "special", "key": "galaxy", "stars": 14},
    {"kind": "topping", "key": "unicorn", "stars": 15},
    {"kind": "stand", "key": "pink", "stars": 17},
    {"kind": "topping", "key": "gem", "stars": 18},
    {"kind": "wallpaper", "key": "lavender", "stars": 20},
    {"kind": "topping", "key": "moon", "stars": 21},
    {"kind": "special", "key": "rainbow", "stars": 23},
    {"kind": "topping", "key": "rocket", "stars": 24},
    {"kind": "stand", "key": "gold", "stars": 26},
    {"kind": "topping", "key": "dragon", "stars": 27},
    {"kind": "wallpaper", "key": "lemon", "stars": 30},
    {"kind": "topping", "key": "teddy", "stars": 32},
    {"kind": "special", "key": "gold", "stars": 35},
    {"kind": "topping", "key": "planet", "stars": 38},
    {"kind": "wallpaper", "key": "night", "stars": 44},
    {"kind": "topping", "key": "fireworks", "class": 40},
    {"kind": "wallpaper", "key": "candy", "class": 120},
    {"kind": "topping", "key": "disco", "class": 240},
]
STANDS = ["plate", "board", "glass", "pink", "gold"]
WALLPAPERS = ["strawberry", "mint", "lavender", "lemon", "night", "candy"]
LOCKED = {(u["kind"], u["key"]) for u in UNLOCKS}


def unlock_name(u):
    if u["kind"] == "topping":
        return f"{TOPPINGS[u['key']]} {u['key'].capitalize()} topping"
    if u["kind"] == "special":
        return f"{u['key'].capitalize()} frosting"
    if u["kind"] == "stand":
        return f"{u['key'].capitalize()} cake stand"
    return f"{u['key'].capitalize()} wallpaper"


def open_unlocks(stars, class_stars):
    """Every unlock this many stars has opened, as (kind, key) pairs."""
    return {(u["kind"], u["key"]) for u in UNLOCKS
            if ("stars" in u and stars >= u["stars"])
            or ("class" in u and class_stars >= u["class"])}

COMMANDS = ("layer", "frosting", "drip", "sprinkles", "swirl", "topping",
            "candle", "write", "tier")
# Python helpers that aren't kitchen commands.
HELPERS = ("print", "len", "str", "int", "max", "min", "abs", "choice", "randint")
TEXT_METHODS = ("upper", "lower", "title", "capitalize", "strip", "replace")
LIST_METHODS = ("append", "count")


class _Done(Exception):
    """The kitchen is full: stop the program."""


def _clean(word):
    return re.sub(r"\s+", " ", str(word).strip().lower().replace("_", " ").replace("-", " "))


HEX = re.compile(r"#(?:[0-9a-fA-F]{6}|[0-9a-fA-F]{3})")


def _hex(value):
    if HEX.fullmatch(value):
        v = value.lower()
        return v if len(v) == 7 else "#" + "".join(ch * 2 for ch in v[1:])
    return None


# ---- the kitchen: what the commands build ----------------------------------

def new_tier():
    return {"layers": [], "frosting": None, "drip": None, "sprinkles": None,
            "swirls": [], "toppings": [], "candles": [], "text": None, "text_colour": None}


class Kitchen:
    """One cake being made. Every command is a step the browser replays."""

    def __init__(self, unlocked, unlock_hint):
        self.tiers = [new_tier()]
        self.steps = []
        self.prints = []
        self.unlocked = unlocked
        self.unlock_hint = unlock_hint   # (kind, key) -> "unlocks at 5 stars"

    @property
    def top(self):
        return self.tiers[-1]

    def note(self, text):
        self.prints.append({"step": len(self.steps), "text": text})
        del self.prints[:-MAX_PRINTS]

    def step(self, do, arg=None):
        if len(self.steps) >= MAX_STEPS:
            raise BotError(f"That's a LOT of baking! The kitchen stops at "
                           f"{MAX_STEPS} steps for one cake. Is a loop going "
                           f"round too many times?")
        self.steps.append({"do": do, "arg": arg} if arg is not None else {"do": do})

    def locked(self, kind, key, what):
        if (kind, key) in LOCKED and (kind, key) not in self.unlocked:
            raise BotError(f"🔒 {what} {self.unlock_hint(kind, key)}. Keep baking "
                           f"to unlock it!")

    @staticmethod
    def one_thing(value, command):
        """A whole ticket or a whole list where one word belongs."""
        if isinstance(value, dict):
            key = {"layer": "flavour", "frosting": "frosting", "drip": "drip"}.get(command, "...")
            raise BotError(f"That's the whole ticket. {command}() needs one part of it, "
                           f"with square brackets, like  {command}(order[\"{key}\"])")
        if isinstance(value, list):
            raise BotError(f"That's a list of {len(value)}. {command}() takes one at a time, "
                           f"so loop over the list:  for x in ...:  and then  {command}(x)")

    def colour(self, value, command, specials=True, extra=()):
        example = {"frosting": "frosting(\"pink\")", "drip": "drip(\"chocolate\")",
                   "sprinkles": "sprinkles(\"pink\")", "swirl": "swirl(\"white\")",
                   "candle": "candle(\"blue\")", "write": "write(\"Hi\", \"pink\")"}[command]
        if not isinstance(value, str):
            self.one_thing(value, command)
            raise BotError(f"{command}() needs a colour in quotes, like  {example}")
        word = _clean(value)
        if word in COLOURS or word in extra:
            return word
        code = _hex(value.strip())
        if code:
            return code
        if specials and word in SPECIALS:
            self.locked("special", word, f"{word.capitalize()} frosting")
            return word
        if word in FLAVOURS:
            raise BotError(f'"{value}" is a flavour for layer(). {command}() takes a '
                           f'colour, like  {example}')
        known = list(COLOURS) + list(extra) + (SPECIALS if specials else [])
        near = difflib.get_close_matches(word, known, 1, 0.6)
        if near:
            raise BotError(f'I don\'t have the colour "{value}". Did you mean "{near[0]}"?')
        raise BotError(f'I don\'t have the colour "{value}". Colours: '
                       f'{", ".join(COLOURS)}. (A code like "#ff88cc" works too.)')

    def need_cake(self, command):
        if not self.top["layers"]:
            raise BotError(f"Bake a layer first: {command}() needs a cake to go on. "
                           f'Start with something like  layer("vanilla")')

    def do(self, command, args):
        t = self.top
        if command == "tier":
            if args:
                raise BotError("tier() doesn't take anything in the ( ).")
            self.need_cake("tier")
            if len(self.tiers) >= MAX_TIERS:
                raise BotError(f"{MAX_TIERS} tiers is as tall as a wedding cake gets!")
            self.step("tier")
            self.tiers.append(new_tier())
            return
        if command in ("sprinkles", "swirl", "candle") and not args:
            args = [{"sprinkles": "rainbow", "swirl": "white", "candle": "classic"}[command]]
        if command == "write" and len(args) not in (1, 2):
            raise BotError('write() needs a message in quotes, like  write("Hi Gran")  '
                           '(and a colour if you like:  write("Hi Gran", "pink") )')
        if len(args) != 1 and command != "write":
            example = {"layer": 'layer("vanilla")', "frosting": 'frosting("pink")',
                       "drip": 'drip("chocolate")', "topping": 'topping("cherry")',
                       "sprinkles": 'sprinkles("pink")', "swirl": 'swirl("white")',
                       "candle": 'candle("blue")'}[command]
            raise BotError(f"{command}() takes one thing in the ( ), like  {example}")
        value = args[0]
        if isinstance(value, int) and not isinstance(value, bool) and command != "write":
            noun = {"layer": 'layer("vanilla")', "topping": 'topping("cherry")',
                    "candle": "candle()", "swirl": 'swirl("white")'}.get(command)
            if noun:
                raise BotError(f"{command}() adds ONE at a time. For {value} use a loop:  "
                               f"for i in range({value}):  then  {noun}  pushed in under it.")
        if command == "layer":
            if len(t["layers"]) >= MAX_LAYERS:
                raise BotError(f"That cake is as tall as the oven! {MAX_LAYERS} layers "
                               f"is the most for one tier.")
            t["layers"].append(self.flavour(value))
            self.step("layer", t["layers"][-1])
            return
        self.need_cake(command)
        if command == "frosting":
            t["frosting"] = self.colour(value, "frosting")
            self.step("frosting", t["frosting"])
        elif command == "drip":
            t["drip"] = self.colour(value, "drip")
            self.step("drip", t["drip"])
        elif command == "sprinkles":
            t["sprinkles"] = self.colour(value, "sprinkles", specials=False,
                                         extra=("rainbow",))
            self.step("sprinkles", t["sprinkles"])
        elif command == "swirl":
            if len(t["swirls"]) >= MAX_SWIRLS:
                raise BotError(f"There's no room on the rim for more than {MAX_SWIRLS} swirls.")
            t["swirls"].append(self.colour(value, "swirl"))
            self.step("swirl", t["swirls"][-1])
        elif command == "candle":
            if len(t["candles"]) >= MAX_CANDLES:
                raise BotError(f"{MAX_CANDLES} candles is the most that fit, even for a dragon!")
            t["candles"].append(self.colour(value, "candle", extra=("classic",)))
            self.step("candle", t["candles"][-1])
        elif command == "topping":
            if len(t["toppings"]) >= MAX_TOPPINGS:
                raise BotError(f"The top is full! {MAX_TOPPINGS} toppings is the most.")
            t["toppings"].append(self.topping(value))
            self.step("topping", t["toppings"][-1])
        elif command == "write":
            if isinstance(value, bool) or not isinstance(value, (str, int)):
                raise BotError('write() needs a message in quotes, like  write("Hi Gran")')
            text = str(value).strip()
            if len(text) > MAX_MESSAGE:
                raise BotError(f"That message is too long to fit on the cake: keep it "
                               f"to {MAX_MESSAGE} letters (it has {len(text)}).")
            t["text"] = text
            t["text_colour"] = self.colour(args[1], "write") if len(args) > 1 else None
            self.step("write", text)
            if t["text_colour"]:
                self.steps[-1]["colour"] = t["text_colour"]

    def flavour(self, value):
        if not isinstance(value, str):
            self.one_thing(value, "layer")
            raise BotError('layer() needs a flavour in quotes, like  layer("vanilla")')
        word = _clean(value)
        word = {"redvelvet": "red velvet", "cookies and cream": "cookies",
                "cookies & cream": "cookies"}.get(word, word)
        if word in FLAVOURS:
            return word
        code = _hex(value.strip())
        if code:
            return code
        if word.endswith("s") and (word[:-1] in FLAVOURS or word[:-3] + "y" in FLAVOURS):
            single = word[:-1] if word[:-1] in FLAVOURS else word[:-3] + "y"
            raise BotError(f'layer() adds ONE layer: write  layer("{single}")  and '
                           f'use it again (or a loop) for more.')
        if word in COLOURS:
            raise BotError(f'"{value}" is a colour. Layers are flavours, like '
                           f'"strawberry" or "lemon". Flavours: {", ".join(FLAVOURS)}')
        near = difflib.get_close_matches(word, list(FLAVOURS), 1, 0.6)
        if near:
            raise BotError(f'I don\'t have a "{value}" flavour. Did you mean "{near[0]}"?')
        raise BotError(f'I don\'t have a "{value}" flavour. Flavours: '
                       f'{", ".join(FLAVOURS)}')

    def topping(self, value):
        if not isinstance(value, str):
            self.one_thing(value, "topping")
            raise BotError('topping() needs a topping in quotes, like  topping("cherry")')
        word = _clean(value)
        if word in TOPPINGS:
            self.locked("topping", word, f"The {TOPPINGS[word]} {word} topping")
            return word
        for single in (word[:-1], word[:-2], word[:-3] + "y", word[:-3] + "f"):
            if word.endswith("s") and single in TOPPINGS:
                raise BotError(f'topping() adds ONE topping: write  topping("{single}")  '
                               f'and use a loop for more.')
        if word == "candle" or word == "candles":
            raise BotError("Candles have their own command: candle() adds one.")
        if word == "sprinkles":
            raise BotError("Sprinkles have their own command: sprinkles()")
        near = difflib.get_close_matches(word, list(TOPPINGS), 1, 0.6)
        if near:
            raise BotError(f'I don\'t have a "{value}" topping. Did you mean "{near[0]}"?')
        free = [k for k in TOPPINGS if ("topping", k) not in LOCKED]
        raise BotError(f'I don\'t have a "{value}" topping. Toppings: {", ".join(free)} '
                       f'(and more to unlock)')

    def cake(self):
        return [dict(t, layers=list(t["layers"]), swirls=list(t["swirls"]),
                     toppings=list(t["toppings"]), candles=list(t["candles"]))
                for t in self.tiers]


# ---- the interpreter: Light Cycles' Brain, with what a bakery needs ----------

KNOWN_WORDS = set(FLAVOURS) | set(COLOURS) | set(TOPPINGS) | set(SPECIALS) | {"rainbow"}
TICKET_ALIASES = {"flavor": "flavour", "color": "colour", "colors": "colours",
                  "flavors": "flavours"}


class _Cut(Exception):
    pass


def show(value):
    """A value as print() and str() write it, cut short at MAX_TEXT characters.
    It never writes more than that, however deeply lists hold other lists."""
    out = []
    size = [0]

    def emit(text):
        out.append(text)
        size[0] += len(text)
        if size[0] > MAX_TEXT:
            raise _Cut()

    def walk(v, depth, top):
        if isinstance(v, list):
            if depth > 8:
                return emit("[...]")
            emit("[")
            for i, x in enumerate(v):
                if i:
                    emit(", ")
                walk(x, depth + 1, False)
            emit("]")
        elif isinstance(v, dict):
            if depth > 8:
                return emit("{...}")
            emit("{")
            for i, (k, x) in enumerate(v.items()):
                if i:
                    emit(", ")
                emit(repr(k) + ": ")
                walk(x, depth + 1, False)
            emit("}")
        else:
            emit(v if top and isinstance(v, str) else repr(v) if isinstance(v, str) else str(v))

    try:
        walk(value, 0, True)
    except _Cut:
        return "".join(out)[:MAX_TEXT - 1] + "…"
    return "".join(out)


def bulk(value, cap=5000):
    """How many values a list or dictionary holds, counting inside the lists it
    holds; stops counting at cap (a list can hold itself many times over)."""
    count, todo = 0, [value]
    while todo and count <= cap:
        v = todo.pop()
        count += 1
        if isinstance(v, list):
            todo.extend(v)
        elif isinstance(v, dict):
            todo.extend(v.values())
    return count


class Baker(Brain):
    """One student's program baking one cake. Like a Strange Planet rover, the
    program runs once from top to bottom, and its commands build the cake."""

    def __init__(self, code, kitchen, commands, order=None, rng=None, arrives=None):
        self.kitchen = kitchen
        self.commands = set(commands)       # kitchen commands open in this chapter
        self.arrives = arrives or {}        # command -> where it's unlocked
        self.order = order
        self.rng = rng or random.Random(0)
        # Brain's lookup and assign treat these names as commands.
        self.sensors = {name: None for name in COMMANDS + HELPERS}
        self.prints = []
        self.globals = _Frame(module=True)
        self.funcs = {}
        self.ops = 0
        self.budget = PROGRAM_BUDGET
        self.steering = False
        self.depth = 0
        self.own_function = False     # one of the student's own defs ran
        self.own_params = False       # ...and it took parameters
        if len(code) > MAX_CODE:
            raise BotError(f"Your program is too long: the limit is {MAX_CODE} "
                           f"characters (about 100 lines). Delete some comments "
                           f"or lines you don't need.")
        code = code.replace(" ", " ").replace("​", "").replace("﻿", "")
        try:
            self.tree = ast.parse(code)
        except SyntaxError as e:
            raise BotError(cake_syntax(code, e) or
                           syntax_message(e).replace("def steer():", "def my_cake():"))
        # Every name the program sets somewhere, so a name it never sets can
        # be taken for a word that's missing its quotes.
        self.named = {n.id for n in ast.walk(self.tree)
                      if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Store)}
        self.named |= {n.name for n in ast.walk(self.tree) if isinstance(n, ast.FunctionDef)}
        self.named |= {a.arg for n in ast.walk(self.tree) if isinstance(n, ast.FunctionDef)
                       for a in n.args.args}
        if order is not None:
            self.globals.vars["order"] = order

    def run(self):
        try:
            self.run_block(self.tree.body, self.globals)
        except (_Break, _Continue):
            raise BotError("break and continue only work inside a loop.")

    def tick(self):
        self.ops += 1
        if self.ops > self.budget:
            raise _TooLong("Your program ran too long")

    def lookup(self, name, frame):
        try:
            return super().lookup(name, frame)
        except BotError as err:
            if name == "order" and self.order is None:
                raise BotError("There's no order ticket here. Tickets come with the "
                               "customers from Chapter 3 on.")
            if isinstance(self.order, dict) and name in self.order:
                raise BotError(f'Put quotes round the ticket\'s word:  order["{name}"]')
            word = name.lower().replace("_", " ")
            if word in KNOWN_WORDS and name not in frame.vars:
                raise BotError(f'Put quotes round words:  "{word}"  — like  '
                               f'layer("vanilla")  or  frosting("pink")')
            if name not in self.named and "Did you mean" not in str(err):
                raise BotError(f'Words need quotes round them, like  "{name}"  '
                               f'(or if {name} is a variable, set it first, like  {name} = 3)')
            raise

    def assign(self, name, value, frame):
        if name in COMMANDS or name in HELPERS:
            raise BotError(f"'{name}' is already a command — pick another "
                           f"variable name.")
        super().assign(name, value, frame)

    # ---- values: text, lists and dictionaries --------------------------------

    def math(self, op, a, b):
        if isinstance(op, ast.Add) and isinstance(a, list) and isinstance(b, list):
            return self.fits(a + b)
        if isinstance(op, ast.Mult) and isinstance(a, (str, list)) != isinstance(b, (str, list)):
            seq, n = (a, b) if isinstance(a, (str, list)) else (b, a)
            n = self.number(n, "Repeating with *")
            if len(seq) * max(n, 0) > (MAX_TEXT if isinstance(seq, str) else MAX_LIST):
                raise BotError("That got too long.")
            return seq * n
        if isinstance(op, ast.Add) and (isinstance(a, str) or isinstance(b, str)) \
                and not (isinstance(a, str) and isinstance(b, str)):
            num = b if isinstance(a, str) else a
            raise BotError(f"Text and {type(num).__name__ if not isinstance(num, int) else 'a number'} "
                           f"can't be joined with + directly. Turn the number into "
                           f'text with str():  "Age " + str(8)  — or use an '
                           f'f-string:  f"Age {{8}}"')
        if isinstance(a, (list, dict)) or isinstance(b, (list, dict)):
            raise BotError("You can't do math with a list.")
        return super().math(op, a, b)

    def fits(self, items):
        if len(items) > MAX_LIST:
            raise BotError(f"That list got too long: {MAX_LIST} items is the most.")
        return items

    def heavy(self, *values):
        """Comparing big nested lists takes a lot of work: count it, and stop
        anything that would take far too long."""
        for v in values:
            if isinstance(v, (list, dict)):
                n = bulk(v)
                if n > 5000:
                    raise BotError("Those lists are too big to compare.")
                self.ops += n

    def compare(self, op, a, b):
        self.heavy(a, b)
        if isinstance(op, (ast.In, ast.NotIn)):
            if isinstance(b, str):
                if not isinstance(a, str):
                    raise BotError("in with text checks for text inside it, like  "
                                   "\"a\" in name")
                found = a in b
            elif isinstance(b, dict) and not isinstance(a, (str, int, bool)) and a is not None:
                raise BotError("in with a dictionary checks for a word, like  \"name\" in order")
            elif isinstance(b, (list, dict)):
                found = a in b
            else:
                raise BotError("in needs a list or some text on its right, like  "
                               'if "star" in order["toppings"]:')
            return found if isinstance(op, ast.In) else not found
        return super().compare(op, a, b)

    def eval(self, node, frame):
        if isinstance(node, ast.List):
            self.tick()
            return self.fits([self.eval(e, frame) for e in node.elts])
        if isinstance(node, ast.Dict):
            self.tick()
            if any(k is None for k in node.keys):
                raise BotError("Write each part of a dictionary as  \"key\": value")
            out = {}
            for k, v in zip(node.keys, node.values):
                key = self.eval(k, frame)
                if not isinstance(key, (str, int)) or isinstance(key, bool):
                    raise BotError("Dictionary keys should be text, like  {\"flavour\": \"lime\"}")
                out[key] = self.eval(v, frame)
            return self.fits(out)
        if isinstance(node, ast.Subscript):
            self.tick()
            return self.item(self.eval(node.value, frame), node.slice, frame)
        if isinstance(node, ast.JoinedStr):
            self.tick()
            parts = []
            for v in node.values:
                if isinstance(v, ast.Constant):
                    parts.append(str(v.value))
                elif isinstance(v, ast.FormattedValue):
                    if v.format_spec is not None:
                        raise BotError('Keep f-strings simple, like  f"Hi {name}"  '
                                       '— no : formatting inside the { }.')
                    parts.append(show(self.eval(v.value, frame)))
                    self.ops += len(parts[-1])
                else:
                    raise BotError("I can't read that f-string.")
            text = "".join(parts)
            if len(text) > MAX_TEXT:
                raise BotError("That text got too long.")
            return text
        if isinstance(node, (ast.Tuple, ast.Set)):
            raise BotError("Use a list in square brackets, like  [\"lemon\", \"lime\"]")
        if isinstance(node, (ast.ListComp, ast.DictComp, ast.SetComp, ast.GeneratorExp)):
            raise BotError("That shortcut isn't part of Cake Shop. Use a for loop "
                           "and .append() instead.")
        if isinstance(node, ast.Attribute):
            if isinstance(node.value, ast.Name) and node.value.id == "order":
                raise BotError(f'Read the ticket with square brackets:  order["{node.attr}"]')
            raise BotError(f"Dots like  .{node.attr}  only work as methods with ( ), "
                           f"like  name.upper()")
        if isinstance(node, ast.Constant) and isinstance(node.value, float):
            raise BotError("Use whole numbers here, like 3 (not 3.5).")
        if isinstance(node, ast.Lambda) or type(node).__name__ in ("TemplateStr", "NamedExpr", "Await"):
            raise BotError("That isn't part of Cake Shop.")
        return super().eval(node, frame)

    def item(self, target, index, frame):
        if isinstance(index, ast.Slice):
            if not isinstance(target, (list, str)):
                raise BotError("Slices like [1:] work on lists and text.")
            parts = [None if p is None else self.number(self.eval(p, frame), "A slice")
                     for p in (index.lower, index.upper, index.step)]
            if parts[2] == 0:
                raise BotError("A slice's step can't be 0.")
            return target[slice(*parts)]
        key = self.eval(index, frame)
        if isinstance(target, dict):
            if not isinstance(key, (str, int)):
                raise BotError('Read a dictionary with a word in quotes, like  order["name"]')
            if key in target:
                return target[key]
            if TICKET_ALIASES.get(key) in target:
                return target[TICKET_ALIASES[key]]
            what = "The ticket" if target is self.order else "That dictionary"
            near = difflib.get_close_matches(str(key), [str(k) for k in target], 1, 0.6)
            if near:
                raise BotError(f'{what} has no "{key}". Did you mean  ["{near[0]}"] ?')
            keys = ", ".join(f'"{k}"' for k in target)
            raise BotError(f'{what} has no "{key}". It has: {keys}')
        if isinstance(target, (list, str)):
            if isinstance(key, bool) or not isinstance(key, int):
                raise BotError("Use a whole number for the position in [ ], like  "
                               "flavours[0]  (the first one is 0)")
            if -len(target) <= key < len(target):
                return target[key]
            if not target:
                raise BotError(f"[{key}] can't work: it's empty.")
            raise BotError(f"There's nothing at position {key}: it has {len(target)} "
                           f"thing{'s' if len(target) != 1 else ''}, so the positions "
                           f"go from 0 to {len(target) - 1}.")
        raise BotError(f"[ ] works on lists, text and dictionaries, not on {show(target)}.")

    # ---- calls: kitchen commands, helpers, methods and your own defs ---------

    def call(self, node, frame):
        if node.keywords:
            raise BotError("Commands don't take name=value arguments here.")
        if any(isinstance(a, ast.Starred) for a in node.args):
            raise BotError("* in a call isn't part of Cake Shop.")
        if isinstance(node.func, ast.Attribute):
            return self.method(node, frame)
        if not isinstance(node.func, ast.Name):
            raise BotError('I can only call plain commands, like  layer("vanilla")')
        name = node.func.id
        if name in self.funcs:
            return self.call_user(self.funcs[name], [self.eval(a, frame) for a in node.args])
        args = [self.eval(a, frame) for a in node.args]
        if name in COMMANDS:
            if name not in self.commands:
                raise BotError(f"{name}() isn't open yet: it arrives in "
                               f"{self.arrives.get(name, 'a later chapter')}.")
            self.kitchen.do(name, args)
            return None
        if name == "print":
            text = show(" ".join(show(a) for a in args))
            self.ops += len(text)   # writing text out is work too
            self.kitchen.note(text)
            return None
        if name == "len":
            if len(args) != 1 or not isinstance(args[0], (list, str, dict)):
                raise BotError('len() takes one list or text, like  len(order["layers"])')
            return len(args[0])
        if name == "str":
            if len(args) != 1:
                raise BotError("str() takes one thing, like  str(8)")
            text = show(args[0])
            self.ops += len(text)
            return text
        if name == "int":
            if len(args) != 1:
                raise BotError('int() takes one thing, like  int("8")')
            v = args[0]
            if isinstance(v, str) and re.fullmatch(r"\s*-?\d{1,9}\s*", v):
                return int(v)
            return self.number(v, "int()")
        if name == "choice":
            if len(args) != 1 or not isinstance(args[0], (list, str)) or not args[0]:
                raise BotError('choice() picks from a list, like  choice(["pink", "blue"])')
            return self.rng.choice(args[0])
        if name == "randint":
            if len(args) != 2:
                raise BotError("randint() takes two numbers, like  randint(1, 6)")
            lo, hi = (self.number(a, "randint()") for a in args)
            if lo > hi:
                raise BotError("randint(a, b) needs a to be no bigger than b.")
            return self.rng.randint(lo, hi)
        if name in ("max", "min", "abs"):
            return super().call(node, frame)
        if name == "range":
            raise BotError("range() only goes inside a for loop, like:  for i in range(4):")
        guesses = {"candles": "candle() adds one candle. Use a for loop for lots",
                   "layers": 'layer() adds one layer, like  layer("vanilla")',
                   "frost": 'frosting("pink")', "icing": 'frosting("pink")',
                   "sprinkle": "sprinkles()", "toppings": 'topping("cherry") adds one',
                   "swirls": 'swirl("white") adds one swirl',
                   "text": 'write("Hello")', "message": 'write("Hello")',
                   "decorate": 'topping("cherry") or swirl("pink")'}
        if name in guesses and name not in self.funcs:
            raise BotError(f"There's no {name}(). Try  {guesses[name]}.")
        known = [c for c in COMMANDS if c in self.commands] + list(self.funcs) + list(HELPERS)
        near = difflib.get_close_matches(name.lower(), known, 1, 0.7)
        raise BotError(f"I don't know the command '{name}'. Did you mean  {near[0]}() ?"
                       if near else
                       f"I don't know the command '{name}'. Check the recipe book, "
                       f"or make it yourself with def.")

    def method(self, node, frame):
        name = node.func.attr
        target = self.eval(node.func.value, frame)
        args = [self.eval(a, frame) for a in node.args]
        self.tick()
        if isinstance(target, str) and name in TEXT_METHODS:
            if name == "replace":
                if len(args) != 2 or not all(isinstance(a, str) for a in args):
                    raise BotError('.replace() takes two pieces of text, like  '
                                   'name.replace("a", "o")')
                out = target.replace(*args)
                if len(out) > MAX_TEXT:
                    raise BotError("That text got too long.")
                return out
            if args:
                raise BotError(f".{name}() doesn't take anything in the ( ).")
            return getattr(target, name)()
        if isinstance(target, list) and name in LIST_METHODS:
            if len(args) != 1:
                raise BotError(f".{name}() takes one thing, like  toppings.{name}(\"star\")")
            if name == "count":
                self.heavy(target, args[0])
                return target.count(args[0])
            target.append(args[0])
            self.fits(target)
            return None
        if isinstance(target, str):
            raise BotError(f".{name}() isn't something text can do here. Try .upper(), "
                           f".lower() or .title()")
        if isinstance(target, list):
            raise BotError(f".{name}() isn't something a list can do here. Try .append()")
        raise BotError(f".{name}() doesn't work on {show(target)}.")

    def call_user(self, fn, args):
        self.own_function = True
        if fn.args.args:
            self.own_params = True
        return super().call_user(fn, args)

    # ---- statements: for loops over lists --------------------------------------

    def run_statement(self, node, frame):
        if isinstance(node, ast.For):
            self.tick()
            if not isinstance(node.target, ast.Name):
                raise BotError("A for loop needs one simple name, like:  "
                               "for flavour in flavours:")
            if node.orelse:
                raise BotError("for ... else isn't part of Cake Shop.")
            it = node.iter
            if isinstance(it, ast.Call) and isinstance(it.func, ast.Name) \
                    and it.func.id == "range" and it.func.id not in self.funcs:
                nums = [self.number(self.eval(a, frame), "range()") for a in it.args]
                if it.keywords or not 1 <= len(nums) <= 3 or (len(nums) == 3 and nums[2] == 0):
                    raise BotError("range() takes 1 to 3 numbers, and the step can't be 0.")
                values = range(*nums)
            else:
                seq = self.eval(it, frame)
                if isinstance(seq, (list, str)):
                    values = list(seq)
                elif isinstance(seq, dict):
                    values = list(seq.keys())
                elif isinstance(seq, int):
                    raise BotError(f"To repeat {seq} times write  for i in range({seq}):")
                else:
                    raise BotError("A for loop goes through a list, some text or "
                                   "range(), like:  for i in range(4):")
            for value in values:
                self.tick()
                self.assign(node.target.id, value, frame)
                if not self.run_loop_body(node.body, frame):
                    break
            return
        if isinstance(node, ast.While) and node.orelse:
            raise BotError("while ... else isn't part of Cake Shop.")
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            raise BotError("import isn't needed in Cake Shop — choice() and "
                           "randint() are already here.")
        if isinstance(node, ast.Assign) and any(
                isinstance(t, ast.Subscript) for t in node.targets):
            raise BotError("Changing one item with [ ] = isn't part of Cake Shop. "
                           "Make a new variable instead.")
        if isinstance(node, ast.Assign) and any(
                isinstance(t, (ast.Tuple, ast.List)) for t in node.targets):
            raise BotError("Give each variable its own line, like:  a = 1")
        if isinstance(node, ast.FunctionDef) and (node.name in COMMANDS or node.name in HELPERS):
            raise BotError(f"{node.name}() is already a command — give your "
                           f"recipe another name, like  def my_{node.name}():")
        if isinstance(node, ast.Expr) and not isinstance(node.value, ast.Call) and not (
                isinstance(node.value, ast.Constant) and isinstance(node.value.value, str)):
            v = node.value
            if isinstance(v, ast.Name) and (v.id in COMMANDS or v.id in HELPERS or v.id in self.funcs):
                raise BotError(f"To use {v.id}, add brackets:  {v.id}()")
            raise BotError('That line doesn\'t do anything on its own. Commands need '
                           'brackets, like  sprinkles()  or  layer("vanilla")')
        if isinstance(node, (ast.Try, ast.With, ast.ClassDef, ast.Delete, ast.Raise,
                             ast.Assert, ast.Nonlocal, ast.AsyncFunctionDef)) or \
                type(node).__name__ in ("Match", "TypeAlias", "TryStar"):
            raise BotError("That kind of line isn't part of Cake Shop.")
        super().run_statement(node, frame)


def cake_syntax(code, e):
    """Beginner slips Python's own message doesn't explain: a command without
    its brackets, a colon in the wrong place or missing, no space after if,
    and two commands on one line."""
    lines = code.split("\n")
    if not e.lineno or e.lineno > len(lines):
        return None
    line = lines[e.lineno - 1]
    bare = re.match(r"\s*([a-z_]+)\s+([\"'].*?[\"']|\d+)\s*$", line)
    if bare and bare[1] in COMMANDS + HELPERS:
        return (f"Syntax error on line {e.lineno}: put brackets round what goes in:  "
                f"{bare[1]}({bare[2]})")
    glued = re.match(r"\s*(if|elif|for|while)([a-z_]\w*)", line)
    if glued and not re.match(r"\s*(if|elif|for|while|def|else)\b", line):
        return f"Syntax error on line {e.lineno}: put a space after  {glued[1]} ."
    if re.match(r"\s*[a-z_]+\s*\(.*\)\s*:\s*$", line) and \
            not re.match(r"\s*(if|elif|for|while|def|else)\b", line):
        return (f"Syntax error on line {e.lineno}: only lines starting with for, if, elif, "
                f"else or def end with a colon. Take the  :  off the end of this one.")
    head = re.match(r"\s*(for|if|elif|else|while|def)\b", line)
    if head and not line.rstrip().endswith(":"):
        a = "an" if head[1][0] in "aeiou" else "a"
        return (f"Syntax error on line {e.lineno}: {a}  {head[1]}  line ends with a colon  :  "
                f"and the steps go on the lines below it, pushed in.")
    if re.search(r"[a-z_]\s*\(.*\)\s*[a-z_]+\s*\(", line) and not head:
        return f"Syntax error on line {e.lineno}: put each command on its own line."
    return None


# ---- baking one cake -----------------------------------------------------------

ARRIVES = {"candle": "Chapter 2: Birthday Week", "swirl": "Chapter 2: Birthday Week",
           "tier": "Chapter 6: Secret Recipes"}


def default_hint(kind, key):
    u = next(u for u in UNLOCKS if (u["kind"], u["key"]) == (kind, key))
    if "stars" in u:
        return f"unlocks at {u['stars']} stars"
    return f"unlocks when the class star meter reaches {u['class']}"


def _copy(value):
    if isinstance(value, list):
        return [_copy(v) for v in value]
    if isinstance(value, dict):
        return {k: _copy(v) for k, v in value.items()}
    return value


def bake(code, order=None, commands=COMMANDS, unlocked=LOCKED, unlock_hint=None,
         seed=0):
    """Run one program to bake one cake. Returns the steps the browser replays
    and the finished cake (a list of tiers, bottom first)."""
    kitchen = Kitchen(unlocked, unlock_hint or default_hint)
    error = line = None
    baker = None
    try:
        baker = Baker(str(code)[:MAX_CODE + 1], kitchen, commands,
                      _copy(order) if order is not None else None,
                      random.Random(seed), ARRIVES)
        baker.run()
        if baker.funcs and not baker.own_function and not kitchen.steps:
            name = next(iter(baker.funcs))
            raise BotError(f"Your recipes are written down, but nothing uses them yet. "
                           f"Call one by its name with brackets, like  {name}()")
    except BotError as e:
        error, line = str(e), e.line
    except RecursionError:
        error = "Your recipes call each other too deeply."
    except Exception as e:   # a bug in the kitchen, not the student's code
        print(f"Cake Shop: unexpected {type(e).__name__}: {e}", flush=True)
        error = "Something unexpected went wrong in the kitchen. Try changing that line a little."
    return {"cake": kitchen.cake(), "steps": kitchen.steps, "prints": kitchen.prints,
            "error": error, "line": line,
            "own_function": bool(baker and baker.own_function),
            "own_params": bool(baker and baker.own_params)}


# ---- judging: does the cake match the order? ----------------------------------

def plain(text):
    """Text as the judge reads it: capitals, spaces and punctuation don't count."""
    return re.sub(r"[^0-9a-z]", "", str(text).lower())


def _s(n, word):
    return f"{n} {word}{'' if n == 1 else 's'}"


def describe_layers(layers):
    if layers and len(set(layers)) == 1:
        return _s(len(layers), f"{layers[0]} layer")
    return "layers from the bottom: " + ", ".join(layers)


def describe_swirls(swirls):
    if isinstance(swirls, int):
        return _s(swirls, "swirl")
    if swirls and len(set(swirls)) == 1:
        return _s(len(swirls), f"{swirls[0]} swirl")
    shown = ", ".join(swirls[:4]) + (", …" if len(swirls) > 4 else "")
    return f"{len(swirls)} swirls: {shown}"


def judge_tier(want, t):
    checks, extras = [], []

    def check(text, ok, say):
        checks.append({"text": text, "ok": bool(ok), "say": None if ok else say})

    if "layers" in want:
        w, g = want["layers"], t["layers"]
        if not g:
            say = f"There's no cake yet! I'd like {_s(len(w), 'layer')}: start with  layer(...)"
        elif len(g) != len(w):
            say = f"I asked for {_s(len(w), 'layer')}, but this cake has {len(g)}."
        else:
            i = next((i for i, (a, b) in enumerate(zip(w, g)) if a != b), 0)
            say = f"Layer {i + 1} from the bottom should be {w[i]}, not {g[i]}."
        check(describe_layers(w), g == w, say)
    for part, noun in (("frosting", "frosting"), ("drip", "drip")):
        if part not in want:
            if t[part]:
                extras.append(noun)
            continue
        w, g = want[part], t[part]
        if w is None:
            check(f"no {noun}", g is None, f"I didn't want any {noun}!")
        elif g is None:
            check(f"{w} {noun}", False, f"Where's the {w} {noun}?" if part == "frosting"
                  else f"I wanted a {w} drip.")
        else:
            check(f"{w} {noun}", g == w, f"The {noun} should be {w}, not {g}.")
    if "sprinkles" in want:
        w, g = want["sprinkles"], t["sprinkles"]
        if w is True:
            check("sprinkles", g, "Where are the sprinkles?")
        elif w is False:
            check("no sprinkles", not g, "Oh no, I said NO sprinkles!")
        else:
            check(f"{w} sprinkles", g == w, "Where are the sprinkles?" if not g
                  else f"The sprinkles should be {w}, not {g}.")
    elif t["sprinkles"]:
        extras.append("sprinkles")
    if "candles" in want:
        n, m = want["candles"], len(t["candles"])
        if n == 0:
            check("no candles", m == 0, "Candles? It isn't my birthday!")
        else:
            check(_s(n, "candle"), m == n, f"I need {_s(n, 'candle')}, but I count {m}.")
    elif t["candles"]:
        extras.append("candles")
    wanted = want.get("toppings", {})
    for name, n in wanted.items():
        m, icon = t["toppings"].count(name), TOPPINGS[name]
        if n == 0:
            check(f"no {name}", m == 0, f"I didn't want any {icon}!")
        elif m == 0:
            check(f"{n} × {icon} {name}", False, f"Where's my {icon} {name}?" if n == 1
                  else f"I wanted {n} × {icon}, but there aren't any.")
        else:
            check(f"{n} × {icon} {name}", m == n, f"I wanted {n} × {icon}, but I count {m}.")
    extras += sorted({TOPPINGS[x] for x in t["toppings"] if x not in wanted})
    if "swirls" in want:
        w, g = want["swirls"], t["swirls"]
        n = w if isinstance(w, int) else len(w)
        if len(g) != n:
            say = f"I wanted {_s(n, 'swirl')}, but there are {len(g)}."
        else:
            i = next((i for i, (a, b) in enumerate(zip(w, g)) if a != b), 0) \
                if isinstance(w, list) else 0
            say = f"Swirl {i + 1} should be {w[i]}, not {g[i]}." if isinstance(w, list) else ""
        check(describe_swirls(w), len(g) == n and (isinstance(w, int) or g == w), say)
    elif t["swirls"]:
        extras.append("swirls")
    if "text" in want:
        w, g = want["text"], t["text"]
        check(f'writing: "{w}"', g is not None and plain(g) == plain(w),
              f'Could you write "{w}" on it?' if g is None
              else f'It should say "{w}", but it says "{g}".')
    elif t["text"]:
        extras.append("writing")
    return checks, extras


TIER_WORDS = ["bottom tier", "second tier", "third tier", "fourth tier"]


def tier_word(i, n):
    return "top tier" if i == n - 1 and n > 1 else TIER_WORDS[i]


def judge(want, cake):
    """What the customer thinks: a checklist (each item ok or not, with what
    they'd say), and the extras on the cake that they didn't ask for, which is
    your own touch."""
    checks, extras = [], []
    if "tiers" in want:
        tiers = want["tiers"]
        n, m = len(tiers), len(cake)
        checks.append({"text": _s(n, "tier"), "ok": n == m,
                       "say": None if n == m else f"I wanted {_s(n, 'tier')}, but this cake has {m}."})
        for i, (tw, t) in enumerate(zip(tiers, cake)):
            sub, ex = judge_tier(tw, t)
            where = tier_word(i, n)
            for c in sub:
                c["text"] = f"{where}: {c['text']}"
                if c["say"]:
                    c["say"] = f"On the {where}: {c['say']}"
            checks += sub
            extras += ex
    else:
        if len(cake) > 1:
            checks.append({"text": "one tier", "ok": False,
                           "say": "I asked for one cake, not a tiered one!"})
        sub, ex = judge_tier(want, cake[0])
        checks += sub
        extras += ex
    return checks, extras


def checklist(want):
    """The order as a list of things to bake, before anything is baked."""
    tiers = len(want["tiers"]) if "tiers" in want else 1
    return [c["text"] for c in judge(want, [new_tier() for _ in range(tiers)])[0]]


def cake_text(cake):
    return " ".join(t["text"] for t in cake if t["text"])


# ---- the levels ----------------------------------------------------------------

CHAPTERS = [
    {"key": "1", "name": "Opening Day", "icon": "🎀",
     "blurb": "Your first customers! Each line of code is one step of the recipe."},
    {"key": "2", "name": "Birthday Week", "icon": "🎂",
     "blurb": "Candles, candles, candles. A for loop repeats lines so you don't have to."},
    {"key": "3", "name": "Lunch Rush", "icon": "🎫",
     "blurb": "A queue! Now ONE program bakes for every customer. Read their order ticket."},
    {"key": "4", "name": "Picky Customers", "icon": "🤔",
     "blurb": "Different customers, different rules: if, elif and else."},
    {"key": "5", "name": "Patterns & Rainbows", "icon": "🌈",
     "blurb": "Stripes, spots and rainbows with %, lists and loops over lists."},
    {"key": "6", "name": "Secret Recipes", "icon": "📖",
     "blurb": "Name your own recipes with def, and build towering wedding cakes."},
    {"key": "7", "name": "The Great Bake-Off", "icon": "🏆",
     "blurb": "Five surprise customers. One program that can bake anything."},
]
COMMAND_CHAPTER = {"layer": 0, "frosting": 0, "drip": 0, "sprinkles": 0, "topping": 0,
                   "write": 0, "candle": 1, "swirl": 1, "tier": 5}
HAPPY = ["Yum! It's perfect, thank you!", "Exactly what I wanted!",
         "Wow, look at it! I'm taking a photo.", "Best bakery in town!",
         "It's beautiful! I almost don't want to eat it.", "Mmm! You're a star baker!"]


def one(name, face, says, want, happy):
    return {"name": name, "face": face, "says": says, "want": want, "happy": happy}


def queue(people, rule, ask):
    """Customers for a rush level: each one's ticket, what they want (the
    level's house rules applied to the ticket) and what they say."""
    out = []
    for face, ticket in people:
        out.append({"name": ticket.get("name", ticket.get("names")), "face": face,
                    "ticket": ticket, "want": rule(ticket), "says": ask(ticket)})
    return out


def _party(t):
    want = {"layers": [t["flavour"]] * 2}
    if t["party"] == "birthday":
        want.update(frosting="pink", candles=t["age"])
    elif t["party"] == "wedding":
        want.update(frosting="white", toppings={"heart": 2}, candles=0)
    else:
        want.update(frosting="yellow", toppings={"flower": 1}, candles=0)
    return want


def _ages(t):
    want = {"layers": [t["flavour"]] * 2, "frosting": "white"}
    if t["age"] < 10:
        want.update(sprinkles=True, drip=None)
    elif t["age"] < 18:
        want.update(sprinkles=True, drip="chocolate")
    else:
        want.update(sprinkles=False, drip="chocolate", toppings={"cherry": 1})
    return want


MENU = {"Choco Bomb": {"layers": ["chocolate"] * 3, "frosting": "chocolate",
                       "toppings": {"cherry": 6}},
        "Lemon Cloud": {"layers": ["lemon"] * 2, "frosting": "white",
                        "sprinkles": "yellow"}}
SIZES = {"small": (2, 6), "medium": (3, 8), "large": (4, 10)}


def _sized(t):
    layers, swirls = SIZES[t["size"]]
    return {"layers": [t["flavour"]] * layers, "frosting": "white",
            "swirls": ["pink"] * swirls}


def _wedding(t):
    tiers = []
    for i, f in enumerate(t["flavours"]):
        tw = {"layers": [f, f], "frosting": "white", "swirls": ["white"] * 8}
        if i == 0:
            tw["text"] = t["names"]
        if i == len(t["flavours"]) - 1:
            tw["toppings"] = {"heart": 2}
        tiers.append(tw)
    return {"tiers": tiers}


LEVELS = [
    # ---- Chapter 1: Opening Day ----------------------------------------------
    {"key": "1a", "chapter": 0, "name": "Granny Rose",
     "customers": [one("Granny Rose", "👵",
                       "Hello, dear! Could I have a cake with two chocolate layers "
                       "and white frosting, please?",
                       {"layers": ["chocolate"] * 2, "frosting": "white"},
                       "Oh, how lovely! Just like the ones I used to bake.")],
     "tip": {"title": "A recipe is a program",
             "text": "Each line is one step, and they run from top to bottom. "
                     "Words go inside quotes.",
             "code": 'layer("vanilla")\nfrosting("pink")'},
     "starter": '# Granny Rose wants two chocolate\n'
                '# layers and white frosting.\n'
                '# Each line is one step. Press Bake!\n'
                'layer("chocolate")\n',
     "hints": ['Two layers means two lines of `layer("chocolate")`',
               'Frosting goes on after the layers: `frosting("white")`',
               'layer("chocolate")\nlayer("chocolate")\nfrosting("white")'],
     "star2": {"kind": "touch"}, "star3": {"kind": "print"},
     "reference": 'layer("chocolate")\nlayer("chocolate")\nfrosting("white")\n'
                  'sprinkles()\nprint("Enjoy your cake, Granny!")\n'},
    {"key": "1b", "chapter": 0, "name": "Leo's Sandwich Cake",
     "customers": [one("Leo", "🧒",
                       "Hi! Can I have vanilla, then strawberry, then vanilla on top? "
                       "With pink frosting and one cherry on top!",
                       {"layers": ["vanilla", "strawberry", "vanilla"], "frosting": "pink",
                        "toppings": {"cherry": 1}},
                       "Whoa, it looks like a giant sandwich! Thank you!")],
     "tip": {"title": "Order matters",
             "text": "The first `layer()` goes at the bottom, and each new one goes on "
                     "top. `topping()` puts something on top of the cake.",
             "code": 'layer("chocolate")   # bottom\nlayer("lemon")       # on top of it\n'
                     'topping("star")'},
     "starter": "# Leo's order, from the bottom up:\n"
                "# vanilla, strawberry, vanilla,\n"
                "# then pink frosting and one cherry\n",
     "hints": ["The first `layer()` you write ends up at the bottom.",
               'The cherry is `topping("cherry")`',
               'layer("vanilla")\nlayer("strawberry")\nlayer("vanilla")\n'
               'frosting("pink")\ntopping("cherry")'],
     "star2": {"kind": "touch"}, "star3": {"kind": "text", "text": "LEO"},
     "reference": 'layer("vanilla")\nlayer("strawberry")\nlayer("vanilla")\n'
                  'frosting("pink")\ntopping("cherry")\nwrite("LEO")\n'},
    {"key": "1c", "chapter": 0, "name": "Captain Whiskers",
     "customers": [one("Captain Whiskers", "🐱",
                       "Meow. Two lemon layers, white frosting and a chocolate drip. "
                       "Three fish on top. And it must say MEOW.",
                       {"layers": ["lemon"] * 2, "frosting": "white", "drip": "chocolate",
                        "toppings": {"fish": 3}, "text": "MEOW"},
                       "Purrrrfect. I shall eat the fish first.")],
     "tip": {"title": "Drips and writing",
             "text": "`drip()` runs down the sides of the cake, and `write()` writes a "
                     "message on the front.",
             "code": 'drip("caramel")\nwrite("Hello!")'},
     "starter": "# Captain Whiskers wants 2 lemon\n"
                "# layers, white frosting, a chocolate\n"
                "# drip, 3 fish on top, and MEOW\n"
                "# written on it.\n",
     "hints": ["Three fish means three lines of `topping(\"fish\")`",
               'The message is `write("MEOW")`',
               'layer("lemon")\nlayer("lemon")\nfrosting("white")\ndrip("chocolate")\n'
               'topping("fish")\ntopping("fish")\ntopping("fish")\nwrite("MEOW")'],
     "star2": {"kind": "touch"}, "star3": {"kind": "lines", "max": 9},
     "reference": 'layer("lemon")\nlayer("lemon")\nfrosting("white")\ndrip("chocolate")\n'
                  'topping("fish")\ntopping("fish")\ntopping("fish")\nwrite("MEOW")\n'
                  'sprinkles("blue")\n'},

    # ---- Chapter 2: Birthday Week ----------------------------------------------
    {"key": "2a", "chapter": 1, "name": "Ava Turns 8",
     "customers": [one("Ava", "👧",
                       "It's my 8th birthday! Two strawberry layers, pink frosting, "
                       "8 candles, and write Happy Birthday Ava!",
                       {"layers": ["strawberry"] * 2, "frosting": "pink", "candles": 8,
                        "text": "Happy Birthday Ava"},
                       "8 candles! I'm going to make a really big wish!")],
     "tip": {"title": "for loops",
             "text": "A `for` loop repeats the lines pushed in (indented) under it. "
                     "The number in `range()` is how many times.",
             "code": "for i in range(3):\n    candle()"},
     "starter": 'layer("strawberry")\nlayer("strawberry")\nfrosting("pink")\n'
                "# This loop adds 3 candles. Ava needs 8!\n"
                "for i in range(3):\n    candle()\n",
     "hints": ["Change the 3 in `range(3)` to the number of candles Ava needs.",
               "`write()` goes after the loop and NOT pushed in, or it would run 8 times.",
               'layer("strawberry")\nlayer("strawberry")\nfrosting("pink")\n'
               'for i in range(8):\n    candle()\nwrite("Happy Birthday Ava")'],
     "star2": {"kind": "touch"}, "star3": {"kind": "lines", "max": 7},
     "reference": 'layer("strawberry")\nlayer("strawberry")\nfrosting("pink")\n'
                  'for i in range(8):\n    candle()\nwrite("Happy Birthday Ava")\n'
                  'swirl("white")\n'},
    {"key": "2b", "chapter": 1, "name": "Ember the Dragon",
     "customers": [one("Ember", "🐉",
                       "ROAR! I'm 100 years old today! Three chocolate layers, orange "
                       "frosting, 100 candles... and 10 gold coins on top. Dragons "
                       "love treasure.",
                       {"layers": ["chocolate"] * 3, "frosting": "orange", "candles": 100,
                        "toppings": {"coin": 10}},
                       "*whoosh* ALL 100 CANDLES, LIT AT ONCE! Best. Birthday. Ever.")],
     "tip": {"title": "Loops can repeat anything",
             "text": "Any command can go in a loop, as many times as you like. "
                     "You can have more than one loop, too.",
             "code": "for i in range(5):\n    topping(\"star\")"},
     "starter": "# 100 candles. You are NOT typing\n# candle() 100 times!\n",
     "hints": ["One loop for the candles and another loop for the coins.",
               "for i in range(100):\n    candle()",
               'for i in range(3):\n    layer("chocolate")\nfrosting("orange")\n'
               'for i in range(100):\n    candle()\nfor i in range(10):\n    topping("coin")'],
     "star2": {"kind": "touch"}, "star3": {"kind": "lines", "max": 8},
     "reference": 'for i in range(3):\n    layer("chocolate")\nfrosting("orange")\n'
                  'for i in range(100):\n    candle()\nfor i in range(10):\n'
                  '    topping("coin")\ndrip("red")\n'},
    {"key": "2c", "chapter": 1, "name": "Zoe Loves Stripes",
     "customers": [one("Zoe", "🦓",
                       "STRIPES! Eight layers: chocolate, vanilla, chocolate, vanilla... "
                       "with chocolate at the bottom. White frosting, and 12 black "
                       "swirls around the top.",
                       {"layers": ["chocolate", "vanilla"] * 4, "frosting": "white",
                        "swirls": ["black"] * 12},
                       "Stripes inside AND out? You totally get me.")],
     "tip": {"title": "Two lines in one loop",
             "text": "Everything pushed in under the for repeats, so each time round "
                     "this loop adds TWO layers. `swirl()` pipes one swirl on the rim.",
             "code": 'for i in range(2):\n    layer("lime")\n    layer("lemon")\n'
                     'swirl("pink")'},
     "starter": "# 8 stripy layers (chocolate first),\n"
                "# white frosting and 12 black swirls.\n",
     "hints": ["Each time round the loop, add a chocolate layer AND a vanilla layer. "
               "How many times round makes 8 layers?",
               'for i in range(4):\n    layer("chocolate")\n    layer("vanilla")',
               'for i in range(4):\n    layer("chocolate")\n    layer("vanilla")\n'
               'frosting("white")\nfor i in range(12):\n    swirl("black")'],
     "star2": {"kind": "touch"}, "star3": {"kind": "lines", "max": 7},
     "reference": 'for i in range(4):\n    layer("chocolate")\n    layer("vanilla")\n'
                  'frosting("white")\nfor i in range(12):\n    swirl("black")\n'
                  'topping("star")\n'},

    # ---- Chapter 3: Lunch Rush -----------------------------------------------------
    {"key": "3a", "chapter": 2, "name": "Flavour of the Day",
     "rules": ["Every cake: 2 layers of the customer's flavour, and white frosting."],
     "customers": queue([("🧑", {"name": "Sam", "flavour": "lemon"}),
                         ("👩🏽", {"name": "Priya", "flavour": "blueberry"}),
                         ("🐶", {"name": "Biscuit", "flavour": "caramel"})],
                        lambda t: {"layers": [t["flavour"]] * 2, "frosting": "white"},
                        lambda t: f"Hi! A {t['flavour']} cake for me, please."),
     "tip": {"title": "The order ticket",
             "text": "Each customer's ticket is a dictionary called `order`. Square "
                     "brackets read one part of it, and a variable can keep it.",
             "code": 'flavour = order["flavour"]\nlayer(flavour)\nprint(order["name"])'},
     "starter": "# ONE program bakes for EVERY customer.\n"
                "# Their ticket is in  order . See it:\n"
                "print(order)\n"
                'layer("lemon")\n',
     "hints": ['`print(order)` shows the ticket in the Kitchen notes. The flavour is '
               '`order["flavour"]`',
               'Swap `"lemon"` for `order["flavour"]` so each customer gets their own.',
               'flavour = order["flavour"]\nlayer(flavour)\nlayer(flavour)\n'
               'frosting("white")'],
     "star2": {"kind": "touch"}, "star3": {"kind": "uses", "what": "variable"},
     "reference": 'flavour = order["flavour"]\nlayer(flavour)\nlayer(flavour)\n'
                  'frosting("white")\ntopping("heart")\n'},
    {"key": "3b", "chapter": 2, "name": "Birthday Rush",
     "rules": ["2 layers of their flavour and pink frosting.",
               "One candle for each year of their age.",
               'Write "Happy Birthday" and their name.'],
     "customers": queue([("👧🏻", {"name": "Mia", "age": 6, "flavour": "strawberry"}),
                         ("🧒🏽", {"name": "Kai", "age": 9, "flavour": "chocolate"}),
                         ("🦊", {"name": "Hazel", "age": 11, "flavour": "orange"})],
                        lambda t: {"layers": [t["flavour"]] * 2, "frosting": "pink",
                                   "candles": t["age"],
                                   "text": f"Happy Birthday {t['name']}"},
                        lambda t: f"I'm {t['age']} today! Can I have a birthday cake?"),
     "tip": {"title": "Joining text, and numbers from the ticket",
             "text": "`+` joins two pieces of text. A number from the ticket can go "
                     "straight into `range()`.",
             "code": 'write("Hello " + order["name"])\n'
                     'for i in range(order["age"]):\n    candle()'},
     "starter": 'layer(order["flavour"])\nlayer(order["flavour"])\nfrosting("pink")\n',
     "hints": ['The number of candles is `order["age"]`, so loop '
               '`for i in range(order["age"]):`',
               'Join the words and the name: `write("Happy Birthday " + order["name"])` '
               '(mind the space after Birthday).',
               'layer(order["flavour"])\nlayer(order["flavour"])\nfrosting("pink")\n'
               'for i in range(order["age"]):\n    candle()\n'
               'write("Happy Birthday " + order["name"])'],
     "star2": {"kind": "touch"}, "star3": {"kind": "lines", "max": 8},
     "reference": 'layer(order["flavour"])\nlayer(order["flavour"])\nfrosting("pink")\n'
                  'for i in range(order["age"]):\n    candle()\n'
                  'write("Happy Birthday " + order["name"])\nsprinkles()\n'},
    {"key": "3c", "chapter": 2, "name": "Party Planner",
     "rules": ["As many layers as the ticket says, in their flavour.",
               "Frosting in the colour on the ticket.",
               'Write their name and age, like "Sam is 9"'],
     "customers": queue([("🧒🏼", {"name": "Theo", "age": 7, "flavour": "lime",
                                   "layers": 3, "frosting": "green"}),
                         ("👵🏾", {"name": "Nana Bea", "age": 80, "flavour": "vanilla",
                                   "layers": 2, "frosting": "lavender"}),
                         ("🤖", {"name": "Robo-7", "age": 3, "flavour": "blueberry",
                                 "layers": 4, "frosting": "blue"})],
                        lambda t: {"layers": [t["flavour"]] * t["layers"],
                                   "frosting": t["frosting"],
                                   "text": f"{t['name']} is {t['age']}"},
                        lambda t: f"It's my party! The details are on my ticket."),
     "tip": {"title": "f-strings",
             "text": "Put `f` before the quotes, and anything in `{ }` is filled in. "
                     "Or turn a number into text with `str()` and join with `+`.",
             "code": 'name = order["name"]\nwrite(f"Go {name}!")\n'
                     'write(name + " is " + str(order["age"]))'},
     "starter": 'for i in range(order["layers"]):\n    layer(order["flavour"])\n',
     "hints": ['The frosting colour is `order["frosting"]`',
               'name = order["name"]\nage = order["age"]\nwrite(f"{name} is {age}")',
               'for i in range(order["layers"]):\n    layer(order["flavour"])\n'
               'frosting(order["frosting"])\nname = order["name"]\nage = order["age"]\n'
               'write(f"{name} is {age}")'],
     "star2": {"kind": "caps"}, "star3": {"kind": "lines", "max": 6},
     "reference": 'for i in range(order["layers"]):\n    layer(order["flavour"])\n'
                  'frosting(order["frosting"])\nname = order["name"].upper()\n'
                  'age = order["age"]\nwrite(f"{name} is {age}")\n'},

    # ---- Chapter 4: Picky Customers ----------------------------------------------
    {"key": "4a", "chapter": 3, "name": "Sprinkles or Not?",
     "rules": ["2 layers of their flavour, and white frosting.",
               'Sprinkles ONLY if the ticket says `"sprinkles": True`'],
     "customers": queue([("👧🏼", {"name": "Lily", "flavour": "cherry", "sprinkles": True}),
                         ("🦉", {"name": "Sir Hoot", "flavour": "coconut", "sprinkles": False}),
                         ("🐭", {"name": "Pip", "flavour": "banana", "sprinkles": True}),
                         ("👴", {"name": "Grandpa Joe", "flavour": "red velvet",
                                 "sprinkles": False})],
                        lambda t: {"layers": [t["flavour"]] * 2, "frosting": "white",
                                   "sprinkles": t["sprinkles"]},
                        lambda t: "Sprinkles please, LOTS of sprinkles!" if t["sprinkles"]
                        else ("No sprinkles, please. They get stuck in my feathers."
                              if t["name"] == "Sir Hoot" else "No sprinkles for me, thank you.")),
     "tip": {"title": "if",
             "text": "`if` runs the lines pushed in under it ONLY when its check is "
                     "`True`. The ticket's `True` or `False` is a check already.",
             "code": 'if order["sprinkles"]:\n    sprinkles()'},
     "starter": 'layer(order["flavour"])\nlayer(order["flavour"])\nfrosting("white")\n'
                "sprinkles()\n",
     "hints": ['Some tickets say `"sprinkles": False`. Those customers mustn\'t get any.',
               'Push `sprinkles()` in under `if order["sprinkles"]:`',
               'layer(order["flavour"])\nlayer(order["flavour"])\nfrosting("white")\n'
               'if order["sprinkles"]:\n    sprinkles()'],
     "star2": {"kind": "touch"}, "star3": {"kind": "lines", "max": 7},
     "reference": 'for i in range(2):\n    layer(order["flavour"])\nfrosting("white")\n'
                  'if order["sprinkles"]:\n    sprinkles()\ntopping("strawberry")\n'},
    {"key": "4b", "chapter": 3, "name": "Party Time",
     "rules": ["Every cake: 2 layers of their flavour.",
               "🎂 birthday: pink frosting, and a candle for every year.",
               "💍 wedding: white frosting and 2 hearts on top.",
               "Any other party: yellow frosting and a flower on top."],
     "customers": queue([("🧒🏿", {"name": "Leo", "party": "birthday", "age": 10,
                                   "flavour": "chocolate"}),
                         ("👰🏽", {"name": "Amara", "party": "wedding", "age": 31,
                                   "flavour": "lemon"}),
                         ("🐸", {"name": "Dr Frog", "party": "get well soon", "age": 40,
                                 "flavour": "lime"}),
                         ("👻", {"name": "Luna", "party": "birthday", "age": 13,
                                 "flavour": "grape"})],
                        _party,
                        lambda t: {"birthday": "It's my birthday!",
                                   "wedding": "I'm getting married!"}.get(
                                       t["party"], "Cheer me up, I've got a cold. *ribbit*")),
     "tip": {"title": "elif and else",
             "text": "`==` checks whether two things are the same. `elif` means "
                     "'otherwise, if...' and `else` catches everything left over.",
             "code": 'if order["party"] == "birthday":\n    frosting("pink")\n'
                     'elif order["party"] == "wedding":\n    frosting("white")\n'
                     'else:\n    frosting("yellow")'},
     "starter": 'layer(order["flavour"])\nlayer(order["flavour"])\n'
                'if order["party"] == "birthday":\n    frosting("pink")\n',
     "hints": ["Three kinds of party means `if`, `elif` and `else`.",
               'Under the wedding branch:\n    frosting("white")\n    topping("heart")\n'
               '    topping("heart")',
               'layer(order["flavour"])\nlayer(order["flavour"])\n'
               'if order["party"] == "birthday":\n    frosting("pink")\n'
               '    for i in range(order["age"]):\n        candle()\n'
               'elif order["party"] == "wedding":\n    frosting("white")\n'
               '    topping("heart")\n    topping("heart")\nelse:\n'
               '    frosting("yellow")\n    topping("flower")'],
     "star2": {"kind": "names"}, "star3": {"kind": "uses", "what": "elif"},
     "reference": 'layer(order["flavour"])\nlayer(order["flavour"])\n'
                  'if order["party"] == "birthday":\n    frosting("pink")\n'
                  '    for i in range(order["age"]):\n        candle()\n'
                  'elif order["party"] == "wedding":\n    frosting("white")\n'
                  '    topping("heart")\n    topping("heart")\nelse:\n'
                  '    frosting("yellow")\n    topping("flower")\nwrite(order["name"])\n'},
    {"key": "4c", "chapter": 3, "name": "The Age Rules",
     "rules": ["Every cake: 2 layers of their flavour, and white frosting.",
               "Under 10: sprinkles.",
               "10 to 17: sprinkles AND a chocolate drip.",
               "18 and over: a chocolate drip and a cherry (no sprinkles)."],
     "customers": queue([("👧🏽", {"name": "Ruby", "age": 9, "flavour": "strawberry"}),
                         ("🧒🏼", {"name": "Max", "age": 10, "flavour": "cookies"}),
                         ("🧑🏻", {"name": "Jade", "age": 17, "flavour": "mint"}),
                         ("🧑🏾", {"name": "Omar", "age": 18, "flavour": "caramel"}),
                         ("👵", {"name": "Granny Rose", "age": 72, "flavour": "chocolate"})],
                        _ages,
                        lambda t: f"I'm {t['age']}. What do I get?"),
     "tip": {"title": "Comparing numbers",
             "text": "`<` means less than, and `<=` less than or equal. Python checks "
                     "an `if`/`elif` chain from the top and runs the FIRST branch that's "
                     "True, so the order of the checks matters.",
             "code": 'if order["age"] < 10:\n    print("a kid")\n'
                     'elif order["age"] < 18:\n    print("a teenager")\n'
                     'else:\n    print("a grown-up")'},
     "starter": 'layer(order["flavour"])\nlayer(order["flavour"])\nfrosting("white")\n'
                'age = order["age"]\n',
     "hints": ["Watch the edges: Max is exactly 10 and Omar is exactly 18. Which "
               "group is each of them in?",
               'if age < 10:\n    sprinkles()\nelif age < 18:\n    sprinkles()\n'
               '    drip("chocolate")\nelse:\n    ...',
               'layer(order["flavour"])\nlayer(order["flavour"])\nfrosting("white")\n'
               'age = order["age"]\nif age < 10:\n    sprinkles()\nelif age < 18:\n'
               '    sprinkles()\n    drip("chocolate")\nelse:\n    drip("chocolate")\n'
               '    topping("cherry")'],
     "star2": {"kind": "touch"}, "star3": {"kind": "lines", "max": 13},
     "reference": 'layer(order["flavour"])\nlayer(order["flavour"])\nfrosting("white")\n'
                  'age = order["age"]\nif age < 10:\n    sprinkles()\nelif age < 18:\n'
                  '    sprinkles()\n    drip("chocolate")\nelse:\n    drip("chocolate")\n'
                  '    topping("cherry")\nswirl("pink")\n'},

    # ---- Chapter 5: Patterns & Rainbows --------------------------------------------
    {"key": "5a", "chapter": 4, "name": "Penguin Pete",
     "customers": [one("Penguin Pete", "🐧",
                       "Candy-cane cake, please! Two vanilla layers, white frosting, "
                       "and 12 swirls going red, white, red, white... all the way "
                       "round. Red first!",
                       {"layers": ["vanilla"] * 2, "frosting": "white",
                        "swirls": ["red", "white"] * 6},
                       "Red, white, red, white... *happy flapping*")],
     "tip": {"title": "Counting with i and %",
             "text": "In `for i in range(6)`, `i` counts 0, 1, 2, 3, 4, 5. `i % 2` is "
                     "the remainder after dividing by 2: 0, 1, 0, 1... so it's 0 "
                     "every other time round.",
             "code": 'for i in range(6):\n    if i % 2 == 0:\n        topping("star")\n'
                     '    else:\n        topping("heart")'},
     "starter": "# Run this, then look at the\n# Kitchen notes:\n"
                "for i in range(12):\n    print(i, i % 2)\n",
     "hints": ["`i % 2` is 0 on the 1st, 3rd, 5th... swirl. Those ones are red.",
               'for i in range(12):\n    if i % 2 == 0:\n        swirl("red")\n'
               '    else:\n        swirl("white")',
               'for i in range(2):\n    layer("vanilla")\nfrosting("white")\n'
               'for i in range(12):\n    if i % 2 == 0:\n        swirl("red")\n'
               '    else:\n        swirl("white")'],
     "star2": {"kind": "touch"}, "star3": {"kind": "lines", "max": 9},
     "reference": 'for i in range(2):\n    layer("vanilla")\nfrosting("white")\n'
                  'for i in range(12):\n    if i % 2 == 0:\n        swirl("red")\n'
                  '    else:\n        swirl("white")\ntopping("star")\n'},
    {"key": "5b", "chapter": 4, "name": "Rainbow the Unicorn",
     "customers": [one("Rainbow", "🦄",
                       "Make me a RAINBOW! Six layers from the bottom: cherry, orange, "
                       "lemon, lime, blueberry, grape. White frosting. Then six swirls: "
                       "red, orange, yellow, green, blue, purple.",
                       {"layers": ["cherry", "orange", "lemon", "lime", "blueberry", "grape"],
                        "frosting": "white",
                        "swirls": ["red", "orange", "yellow", "green", "blue", "purple"]},
                       "It's... it's MAGNIFICENT. *sparkles everywhere*")],
     "tip": {"title": "Lists",
             "text": "A list keeps lots of values in order, inside `[ ]`. A `for` loop "
                     "can visit each one in turn.",
             "code": 'fruits = ["cherry", "lemon", "lime"]\nfor fruit in fruits:\n'
                     '    layer(fruit)'},
     "starter": 'layers = ["cherry", "orange", "lemon", "lime", "blueberry", "grape"]\n',
     "hints": ["for flavour in layers:\n    layer(flavour)",
               "Make a second list for the swirl colours, and loop over it the same way.",
               'layers = ["cherry", "orange", "lemon", "lime", "blueberry", "grape"]\n'
               'colours = ["red", "orange", "yellow", "green", "blue", "purple"]\n'
               'for flavour in layers:\n    layer(flavour)\nfrosting("white")\n'
               'for colour in colours:\n    swirl(colour)'],
     "star2": {"kind": "touch"}, "star3": {"kind": "lines", "max": 8},
     "reference": 'layers = ["cherry", "orange", "lemon", "lime", "blueberry", "grape"]\n'
                  'colours = ["red", "orange", "yellow", "green", "blue", "purple"]\n'
                  'for flavour in layers:\n    layer(flavour)\nfrosting("white")\n'
                  'for colour in colours:\n    swirl(colour)\nsprinkles()\n'},
    {"key": "5c", "chapter": 4, "name": "Build Your Own",
     "rules": ['The ticket lists the layers (bottom first) and the toppings.',
               "Bake exactly those, with the frosting on the ticket."],
     "customers": queue([("🧜🏽‍♀️", {"name": "Marina", "layers": ["blueberry", "coconut", "blueberry"],
                                      "frosting": "blue", "toppings": ["fish", "star"]}),
                         ("👽", {"name": "Cosmo", "layers": ["grape", "grape", "lime", "grape", "grape"],
                                 "frosting": "purple", "toppings": ["star", "star", "star"]}),
                         ("🧚", {"name": "Fern", "layers": ["matcha", "strawberry"],
                                 "frosting": "pink", "toppings": ["flower", "flower", "leaf"]}),
                         ("🦔", {"name": "Bramble", "layers": ["caramel"],
                                 "frosting": "chocolate", "toppings": []})],
                        lambda t: {"layers": t["layers"], "frosting": t["frosting"],
                                   "toppings": dict(collections.Counter(t["toppings"]))},
                        lambda t: "I've written my dream cake on the ticket!"),
     "tip": {"title": "Lists on the ticket",
             "text": '`order["layers"]` is a list, so a `for` loop can go through it. '
                     "`len()` says how many things a list has.",
             "code": 'for flavour in order["layers"]:\n    layer(flavour)\n'
                     'print(len(order["layers"]))'},
     "starter": "print(order)\n",
     "hints": ['for flavour in order["layers"]:\n    layer(flavour)',
               'Toppings work the same way: `for t in order["toppings"]:`',
               'for flavour in order["layers"]:\n    layer(flavour)\n'
               'frosting(order["frosting"])\nfor t in order["toppings"]:\n    topping(t)'],
     "star2": {"kind": "count"}, "star3": {"kind": "lines", "max": 6},
     "reference": 'for flavour in order["layers"]:\n    layer(flavour)\n'
                  'frosting(order["frosting"])\nfor t in order["toppings"]:\n    topping(t)\n'
                  'write(len(order["layers"]))\n'},

    # ---- Chapter 6: Secret Recipes ------------------------------------------------
    {"key": "6a", "chapter": 5, "name": "The Menu",
     "rules": ["🍫 Choco Bomb: 3 chocolate layers, chocolate frosting, 6 cherries.",
               "🍋 Lemon Cloud: 2 lemon layers, white frosting, yellow sprinkles."],
     "customers": queue([("🐼", {"name": "Professor Paws", "cake": "Choco Bomb"}),
                         ("👸🏻", {"name": "Princess Pea", "cake": "Lemon Cloud"}),
                         ("🧔🏽", {"name": "Tom", "cake": "Lemon Cloud"}),
                         ("🦖", {"name": "Rex", "cake": "Choco Bomb"})],
                        lambda t: MENU[t["cake"]],
                        lambda t: f"One {t['cake']}, please!"),
     "tip": {"title": "def: your own recipe",
             "text": "`def` gives a recipe a name. The lines pushed in under it don't "
                     "run straight away: they run each time you call it.",
             "code": 'def cherry_top():\n    for i in range(3):\n        topping("cherry")\n\n'
                     'cherry_top()'},
     "starter": 'def choco_bomb():\n    for i in range(3):\n        layer("chocolate")\n'
                "    # finish the recipe...\n\n"
                'def lemon_cloud():\n    layer("lemon")\n    # ...\n\n'
                'if order["cake"] == "Choco Bomb":\n    choco_bomb()\n',
     "hints": ["Finish each recipe from the menu, then call the right one with `if` and `else`.",
               'else:\n    lemon_cloud()',
               'def choco_bomb():\n    for i in range(3):\n        layer("chocolate")\n'
               '    frosting("chocolate")\n    for i in range(6):\n        topping("cherry")\n\n'
               'def lemon_cloud():\n    layer("lemon")\n    layer("lemon")\n'
               '    frosting("white")\n    sprinkles("yellow")\n\n'
               'if order["cake"] == "Choco Bomb":\n    choco_bomb()\nelse:\n    lemon_cloud()'],
     "star2": {"kind": "touch"}, "star3": {"kind": "uses", "what": "def"},
     "reference": 'def choco_bomb():\n    for i in range(3):\n        layer("chocolate")\n'
                  '    frosting("chocolate")\n    for i in range(6):\n        topping("cherry")\n\n'
                  'def lemon_cloud():\n    layer("lemon")\n    layer("lemon")\n'
                  '    frosting("white")\n    sprinkles("yellow")\n\n'
                  'if order["cake"] == "Choco Bomb":\n    choco_bomb()\nelse:\n'
                  '    lemon_cloud()\nwrite("Enjoy!")\n'},
    {"key": "6b", "chapter": 5, "name": "Any Size",
     "rules": ["Every cake: their flavour, white frosting and pink swirls.",
               "small: 2 layers and 6 swirls.", "medium: 3 layers and 8 swirls.",
               "large: 4 layers and 10 swirls."],
     "customers": queue([("🐶", {"name": "Biscuit", "flavour": "caramel", "size": "small"}),
                         ("🐼", {"name": "Professor Paws", "flavour": "cookies",
                                 "size": "large"}),
                         ("👸🏻", {"name": "Princess Pea", "flavour": "strawberry",
                                   "size": "medium"}),
                         ("🧔🏽", {"name": "Tom", "flavour": "lemon", "size": "small"})],
                        _sized,
                        lambda t: f"A {t['size']} {t['flavour']} cake, please."),
     "tip": {"title": "Parameters",
             "text": "Names in the `( )` of a `def` are parameters. You fill them in "
                     "each time you call it, so one recipe makes many cakes.",
             "code": 'def stack(flavour, n):\n    for i in range(n):\n        layer(flavour)\n\n'
                     'stack("lime", 3)'},
     "starter": "def cake(layers, swirls):\n"
                "    # use the numbers here...\n"
                "    print(layers, swirls)\n\n"
                'if order["size"] == "small":\n    cake(2, 6)\n',
     "hints": ['Inside the def: `for i in range(layers):` then `layer(order["flavour"])`',
               'Call it with the right numbers for each size: `cake(3, 8)` for medium.',
               'def cake(layers, swirls):\n    for i in range(layers):\n'
               '        layer(order["flavour"])\n    frosting("white")\n'
               '    for i in range(swirls):\n        swirl("pink")\n\n'
               'if order["size"] == "small":\n    cake(2, 6)\n'
               'elif order["size"] == "medium":\n    cake(3, 8)\nelse:\n    cake(4, 10)'],
     "star2": {"kind": "touch"}, "star3": {"kind": "uses", "what": "params"},
     "reference": 'def cake(layers, swirls):\n    for i in range(layers):\n'
                  '        layer(order["flavour"])\n    frosting("white")\n'
                  '    for i in range(swirls):\n        swirl("pink")\n\n'
                  'if order["size"] == "small":\n    cake(2, 6)\n'
                  'elif order["size"] == "medium":\n    cake(3, 8)\nelse:\n    cake(4, 10)\n'
                  'topping("bow")\n'},
    {"key": "6c", "chapter": 5, "name": "Wedding Bells",
     "rules": ["One tier for each flavour on the ticket, bottom tier first.",
               "Every tier: 2 layers of its flavour, white frosting, 8 white swirls.",
               "Write the couple's names on the bottom tier.",
               "2 hearts on the very top tier."],
     "customers": queue([("👰🏿", {"names": "Amara & Jo", "flavours": ["vanilla", "lemon"]}),
                         ("🦉", {"names": "Sir Hoot & Lady Owl",
                                 "flavours": ["chocolate", "caramel", "vanilla"]}),
                         ("👵", {"names": "Rose & Joe",
                                 "flavours": ["strawberry", "vanilla", "strawberry", "vanilla"]})],
                        _wedding,
                        lambda t: f"We're getting married! {len(t['flavours'])} tiers, please!"
                        if t["names"] != "Rose & Joe" else
                        "50 years married! Make it the tallest cake you've ever baked."),
     "tip": {"title": "Tiers",
             "text": "`tier()` starts a new, smaller cake on top. Everything after it "
                     "goes on the new tier. `[1:]` is the list without its first item.",
             "code": 'layer("lemon")\ntier()\nlayer("lime")\n\n'
                     'rest = order["flavours"][1:]'},
     "starter": "def one_tier(flavour):\n"
                "    layer(flavour)\n    layer(flavour)\n    # frosting and 8 swirls...\n\n"
                'flavours = order["flavours"]\none_tier(flavours[0])\n',
     "hints": ["Bake the bottom tier and write the names, THEN loop over the rest of "
               "the flavours: each one needs `tier()` first.",
               'for flavour in flavours[1:]:\n    tier()\n    one_tier(flavour)',
               "def one_tier(flavour):\n    layer(flavour)\n    layer(flavour)\n"
               '    frosting("white")\n    for i in range(8):\n        swirl("white")\n\n'
               'flavours = order["flavours"]\none_tier(flavours[0])\nwrite(order["names"])\n'
               'for flavour in flavours[1:]:\n    tier()\n    one_tier(flavour)\n'
               'topping("heart")\ntopping("heart")'],
     "star2": {"kind": "touch"}, "star3": {"kind": "lines", "max": 15},
     "reference": "def one_tier(flavour):\n    layer(flavour)\n    layer(flavour)\n"
                  '    frosting("white")\n    for i in range(8):\n        swirl("white")\n\n'
                  'flavours = order["flavours"]\none_tier(flavours[0])\nwrite(order["names"])\n'
                  'for flavour in flavours[1:]:\n    tier()\n    one_tier(flavour)\n'
                  'for i in range(2):\n    topping("heart")\nsprinkles("white")\n'},
]

# ---- Chapter 7: The Great Bake-Off (random customers every run) ---------------

BAKE_OFF_PEOPLE = [
    ("Mia", "👧🏻"), ("Kai", "🧒🏽"), ("Hazel", "🦊"), ("Biscuit", "🐶"), ("Ruby", "👧🏽"),
    ("Cosmo", "👽"), ("Fern", "🧚"), ("Marina", "🧜🏽‍♀️"), ("Pip", "🐭"), ("Rex", "🦖"),
    ("Luna", "👻"), ("Theo", "🧒🏼"), ("Omar", "🧑🏾"), ("Lily", "👧🏼"), ("Ember", "🐉"),
    ("Pete", "🐧"), ("Zoe", "🦓"), ("Bramble", "🦔"), ("Robo-7", "🤖"), ("Nana Bea", "👵🏾"),
]
FREE_TOPPINGS = [k for k in TOPPINGS if ("topping", k) not in LOCKED]
BAKE_OFF_REFERENCE = '''for flavour in order["layers"]:
    layer(flavour)
frosting(order["frosting"])
if order["drip"] != "":
    drip(order["drip"])
if order["sprinkles"]:
    sprinkles()
for i in range(order["candles"]):
    candle()
for t in order["toppings"]:
    topping(t)
if order["message"] != "":
    write(order["message"])
'''


def bake_off_customers(seed):
    """Five random customers. Every ticket has every key, and an empty ""
    means none. Between them they always cover each kind of choice, so a
    program that ignores one part of the ticket can't get all five."""
    rng = random.Random(seed)
    people = rng.sample(BAKE_OFF_PEOPLE, 5)
    # For each choice (sprinkles, a drip, candles, toppings, a message) at least
    # one customer says yes and at least one says no.
    columns = []
    for _ in range(5):
        column = [True, False] + [rng.random() < .5 for _ in range(3)]
        rng.shuffle(column)
        columns.append(column)
    flags = list(zip(*columns))
    tickets = []
    for (name, face), (sprinkles, dripped, candles, toppings, message) in zip(people, flags):
        n = rng.randint(1, 4)
        ticket = {"name": name,
                  "layers": [rng.choice(list(FLAVOURS)) for _ in range(n)],
                  "frosting": rng.choice(list(COLOURS)),
                  "sprinkles": sprinkles,
                  "drip": rng.choice(["chocolate", "caramel", "white", "pink"]) if dripped else "",
                  "candles": rng.randint(1, 12) if candles else 0,
                  "toppings": [rng.choice(FREE_TOPPINGS) for _ in range(rng.randint(1, 3))]
                  if toppings else [],
                  "message": rng.choice([f"Happy Birthday {name}", f"Go {name}!", "Yum!",
                                         "Thank you", f"Well done {name}", "Best day ever"])
                  if message else ""}
        tickets.append((face, ticket))
    return queue(tickets, _bake_off_want, lambda t: rng.choice([
        "Here's my ticket. Surprise me... exactly!", "Everything's on the ticket!",
        "I hope you can read my writing!", "I've been looking forward to this all week."]))


def _bake_off_want(t):
    want = {"layers": t["layers"], "frosting": t["frosting"], "sprinkles": t["sprinkles"],
            "candles": t["candles"],
            "toppings": dict(collections.Counter(t["toppings"]))}
    if t["drip"]:
        want["drip"] = t["drip"]
    if t["message"]:
        want["text"] = t["message"]
    return want


BAKE_OFF = {"key": "7", "chapter": 6, "name": "The Great Bake-Off", "bake_off": True,
            "rules": ["Bake exactly what each ticket says.",
                      'An empty `""` means none, and so does `0` or an empty list `[ ]`.',
                      "Every run brings five NEW customers."],
            "customers": None,
            "tip": {"title": "One program for anything",
                    "text": "You don't know what's coming, so check every part of the "
                            "ticket. `!=` means 'is not the same as'.",
                    "code": 'if order["drip"] != "":\n    drip(order["drip"])'},
            "starter": "# Five surprise customers!\n# print(order) shows their tickets.\n"
                       "print(order)\n",
            "hints": ["Go through the ticket one key at a time: layers, frosting, drip, "
                      "sprinkles, candles, toppings, message.",
                      'Lists need a `for` loop. Things that might be `""` need an `if`.',
                      BAKE_OFF_REFERENCE.strip()],
            "star2": {"kind": "happy", "n": 3}, "star3": {"kind": "happy", "n": 5},
            "reference": BAKE_OFF_REFERENCE}
LEVELS.append(BAKE_OFF)
LEVEL_ORDER = [lv["key"] for lv in LEVELS]
LEVEL_BY_KEY = {lv["key"]: lv for lv in LEVELS}
for _lv in LEVELS:
    _lv["commands"] = [c for c in COMMANDS if COMMAND_CHAPTER[c] <= _lv["chapter"]]

STUDIO_STARTER = '''# 🎨 Studio: bake ANYTHING you like.
# Then put your best cake in the
# Shop Window for the class to see.
colours = ["pink", "white", "lavender"]
for i in range(3):
    layer("strawberry")
frosting("cream")
for i in range(12):
    swirl(colours[i % 3])
topping(choice(["star", "heart", "flower"]))
write("Made by me")
'''


STUDIO_IDEAS = [
    {"name": "🌈 Rainbow tower", "code": '''flavours = ["cherry", "orange", "lemon", "lime", "blueberry", "grape"]
colours = ["red", "orange", "yellow", "green", "blue", "purple"]
for f in flavours:
    layer(f)
frosting("white")
for i in range(12):
    swirl(colours[i % 6])
topping("star")
'''},
    {"name": "🌙 Spooky night", "code": '''for i in range(3):
    layer("chocolate")
frosting("black")
drip("orange")
for i in range(14):
    if i % 2 == 0:
        swirl("orange")
    else:
        swirl("purple")
for i in range(5):
    candle("purple")
write("BOO!", "orange")
'''},
    {"name": "🎲 Surprise me", "code": '''# Press 🎲 Again to get a different cake every time!
flavours = ["vanilla", "chocolate", "strawberry", "lemon", "mint", "grape"]
for i in range(randint(2, 5)):
    layer(choice(flavours))
frosting(choice(["pink", "white", "lavender", "mint", "yellow"]))
sprinkles()
for i in range(randint(3, 8)):
    topping(choice(["cherry", "star", "heart", "flower", "candy"]))
'''},
    {"name": "🎂 Birthday for…", "code": '''name = "Sam"
age = 9
layer("chocolate")
layer("vanilla")
layer("chocolate")
frosting("blue")
for i in range(age):
    candle("classic")
write(f"Happy {age}th {name}!")
for i in range(10):
    swirl("white")
'''},
    {"name": "🍓 Strawberry dream", "code": '''def strawberry_ring(n):
    for i in range(n):
        topping("strawberry")

layer("vanilla")
layer("strawberry")
layer("vanilla")
frosting("cream")
drip("pink")
strawberry_ring(8)
'''},
    {"name": "👑 Royal wedding", "code": '''def one_tier(flavour, swirls):
    layer(flavour)
    layer(flavour)
    frosting("white")
    for i in range(swirls):
        swirl("white")

one_tier("vanilla", 16)
write("Forever")
tier()
one_tier("lemon", 12)
tier()
one_tier("strawberry", 8)
topping("heart")
'''},
]

# ---- running a level, and its stars ---------------------------------------------

def customers_for(level, seed=0):
    return bake_off_customers(seed) if level.get("bake_off") else level["customers"]


def run_level(level, code, unlocked=LOCKED, unlock_hint=None, seed=0):
    """Bake for every customer in the level's queue, and judge every cake."""
    results = []
    for i, c in enumerate(customers_for(level, seed)):
        out = bake(code, c.get("ticket"), level["commands"], unlocked, unlock_hint,
                   seed=seed * 7 + i)
        checks, extras = judge(c["want"], out["cake"])
        happy = out["error"] is None and all(ch["ok"] for ch in checks)
        if out["error"]:
            reply = "Oh dear... something went wrong in the kitchen!"
        elif happy:
            reply = c.get("happy") or HAPPY[zlib.crc32(c["name"].encode()) % len(HAPPY)]
            if extras:
                reply += " " + touch_line(extras, c["name"])
        else:
            reply = next(ch["say"] for ch in checks if not ch["ok"])
        results.append(dict(out, name=c["name"], face=c["face"], says=c["says"],
                            ticket=c.get("ticket"), happy=happy, reply=reply,
                            checks=checks, extras=extras))
    return results


def touch_line(extras, name):
    """What a happy customer says about the decoration they didn't ask for."""
    first = extras[0]
    named = {icon: key for key, icon in TOPPINGS.items()}
    thing = {"sprinkles": "sprinkles", "drip": "a drip", "swirls": "swirls",
             "candles": "candles", "writing": "writing on it",
             "frosting": "frosting"}.get(first) or f"the {first} {named.get(first, 'topping')}"
    lines = [f"Ooh, {thing} too! What a lovely touch.", f"And {thing}? I love it!",
             f"{thing[0].upper() + thing[1:]}! You thought of everything."]
    return lines[zlib.crc32(f"{name}:{first}".encode()) % len(lines)]


def code_lines(code):
    """Lines that do something: not blank, not only a comment."""
    return sum(1 for line in str(code).split("\n")
               if line.strip() and not line.strip().startswith("#"))


def code_uses(code, what):
    try:
        nodes = list(ast.walk(ast.parse(code)))
    except SyntaxError:
        return False
    if what == "variable":
        return any(isinstance(n, (ast.Assign, ast.AugAssign)) for n in nodes)
    if what == "elif":
        return any(isinstance(n, ast.If) and len(n.orelse) == 1
                   and isinstance(n.orelse[0], ast.If) for n in nodes)
    return False


def star_label(level, star):
    kind = star["kind"]
    many = level.get("customers") is None or len(level["customers"]) > 1
    return {
        "touch": "✨ Your own touch: add something extra"
                 + (" to every cake" if many else ""),
        "print": '🖨 `print()` a note, like `print("Enjoy!")`',
        "text": f"🖊 Write {star.get('text')} on the cake",
        "caps": "📣 Write the name in CAPITALS with `.upper()`",
        "names": "🖊 Write each customer's name on their cake",
        "count": "🔢 Write how many layers it has, using `len()`",
        "lines": f"✂️ {star.get('max')} lines of code or fewer",
        "uses": {"variable": "🏷 Keep the flavour in a variable",
                 "elif": "🔀 Use `if`, `elif` and `else`",
                 "def": "🧩 Use a recipe you made with `def`",
                 "params": "🧩 Use a `def` with parameters"}.get(star.get("what"), ""),
        "happy": f"🏆 {star.get('n')} happy customers in one run"
                 if star.get("n", 5) < 5 else "🏆 All 5 happy in one run",
    }[kind]


def goals(level):
    first = "🏆 1 happy customer" if level.get("bake_off") else \
        ("😊 Make every customer happy" if level["customers"] and len(level["customers"]) > 1
         else "😊 Make the customer happy")
    return [first, star_label(level, level["star2"]), star_label(level, level["star3"])]


def _met(star, results, code):
    kind = star["kind"]
    if kind == "touch":
        return all(r["extras"] for r in results)
    if kind == "print":
        return all(r["prints"] for r in results)
    if kind == "text":
        return all(plain(cake_text(r["cake"])) == plain(star["text"]) for r in results)
    if kind == "caps":
        return all(r["ticket"]["name"].upper() in cake_text(r["cake"]) for r in results)
    if kind == "names":
        return all(plain(r["ticket"]["name"]) in plain(cake_text(r["cake"])) for r in results)
    if kind == "count":
        return all(plain(cake_text(r["cake"])) == str(len(r["ticket"]["layers"]))
                   for r in results)
    if kind == "lines":
        return code_lines(code) <= star["max"]
    if kind == "uses" and star["what"] == "def":
        return all(r["own_function"] for r in results)
    if kind == "uses" and star["what"] == "params":
        return all(r["own_params"] for r in results)
    if kind == "uses":
        return code_uses(code, star["what"])
    if kind == "happy":
        return sum(r["happy"] for r in results) >= star["n"]
    return False


def stars(level, results, code):
    """Which of the level's three stars this run earned."""
    happy = sum(r["happy"] for r in results)
    if level.get("bake_off"):
        return [happy >= 1, happy >= 3, happy >= 5]
    if happy < len(results):
        return [False, False, False]
    return [True, _met(level["star2"], results, code), _met(level["star3"], results, code)]


def studio_bake(code, unlocked=LOCKED, unlock_hint=None, seed=0):
    """A free bake: every command, no customer."""
    return bake(code, None, COMMANDS, unlocked, unlock_hint, seed)
