"""
Light Cycles — a Tron-style battle royale for Python Quest.

Every student writes ONE function. The game calls it every turn and asks
"which way?", and the function answers with a return value:

    def steer():
        if wall_ahead():
            return "left"
        return "straight"

All cycles move at the same time and leave a solid trail of light behind them.
Hit a wall, any trail (yours too) or another cycle head-on and you're out.
Last cycle riding wins.

Sensors the function can ask (they look from the cycle's point of view):

    wall_ahead()  wall_left()  wall_right()     is the next square solid?
    space_ahead() space_left() space_right()    free squares in a straight line

Trails count as walls. The student's program runs once at the start (so it can
set up variables), then steer() runs once per turn with a budget of
operations, in the same whitelist interpreter style as the maze game: no
imports, attribute access, or real builtins ever run on the teacher's laptop.
"""

import ast
import difflib
import keyword
import math
import random
import re

DIRS = [(-1, 0), (0, 1), (1, 0), (0, -1)]   # N E S W, same order as the mazes
TURNS = {"straight": 0, "right": 1, "left": -1}
SETUP_BUDGET = 2000    # operations for the top of the program
STEER_BUDGET = 500     # operations for each steer() call (real bots use ~5-150),
ARENA_BUDGET = 10      # plus this many per square of the arena's longer side, so
                       # a loop over space_ahead() that works in a test drive
                       # still fits in the big class battle arena
# Safety net for the whole class: all steer() calls in one match together may
# use this many operations (about 1 s on a laptop), then the match ends with
# everyone still riding sharing the finish. Normal battles use a small part.
MATCH_BUDGET = 1_000_000
MAX_INT = 10 ** 9
MAX_CODE = 4000        # characters in one program
MAX_PRINTS = 80        # print() lines kept per cycle per match: the LAST ones,
                       # because the lines just before a crash matter most


class BotError(Exception):
    """A friendly, student-facing problem with their code. It crashes the cycle."""
    line = None   # the line it happened on, once known

    def __str__(self):
        text = super().__str__()
        return f"Line {self.line}: {text}" if self.line else text


class _TooLong(BotError):
    """Out of operations. The loop it's stuck in is the line to look at."""
    in_loop = None   # "while" or "for", once we know which loop it was stuck in

    def __str__(self):
        hint = {"while": "is a while loop stuck going round forever?",
                "for": "does a for loop go round too many times?",
                None: "it does too much work in one go. Make it simpler."}
        return f"{super().__str__()} — {hint[self.in_loop]}"


# Python's own wording for the commonest beginner slips, in plain words.
SYNTAX_HINTS = [
    ("expected ':'", "a line that starts with def, if, elif, else, while or "
                     "for has to end with a  :"),
    ("expected an indented block", "the lines inside it need pushing in "
                                   "(indenting) with spaces"),
    ("unexpected indent", "this line is pushed in further than the line above it"),
    ("unindent does not match", "this line doesn't line up with the lines "
                                "above it — check its spaces"),
    ("inconsistent use of tabs", "it mixes tabs and spaces — use spaces only"),
    ("Missing parentheses in call to 'print'", 'print needs brackets, like  '
                                               'print("hi")'),
    ("instead of '='", "to compare two things use  ==  (two equals signs). "
                       "One  =  stores a value"),
    ("cannot assign to", "to compare two things use  ==  (two equals signs). "
                         "One  =  stores a value"),
    ("unterminated string", 'some text is missing its closing quote  "'),
    ("unterminated triple-quoted", 'some text is missing its closing quotes  """'),
    ("U+201C", 'it has curly quotes “ ” — type plain quotes " instead'),
    ("U+201D", 'it has curly quotes “ ” — type plain quotes " instead'),
    ("U+2018", "it has curly quotes ‘ ’ — type plain quotes ' instead"),
    ("U+2019", "it has curly quotes ‘ ’ — type plain quotes ' instead"),
    ("was never closed", "a bracket  (  is never closed with  )"),
    ("non-printable character", "it has an invisible character (often from "
                                "copying). Type the line again with the keyboard"),
    ("unmatched ')'", "there's a  )  with no  (  before it"),
]


# Habits from other languages, spotted in the line itself (outside any text).
LINE_HINTS = [
    (r"&&", "write  and  (not  &&)"),
    (r"\|\|", "write  or  (not  ||)"),
    (r"=!", "write  !=  (not  =!)"),
    (r"!(?!=)", "write the word  not  instead of  !  — like:  if not wall_ahead():"),
    (r"=<", "write  <=  (not  =<)"),
    (r"=>", "write  >=  (not  =>)"),
    (r"\b(wall|space) (ahead|left|right)\b", "sensor names have an underscore "
                                            "in the middle, like  wall_ahead()"),
    # The rover's commands (Strange Planet).
    (r"^(north|south|east|west|wait|report)\s+\w", "commands need brackets, like  east(3)"),
    (r"^(move|turn_left|turn_right|turn)\b", "this rover drives by compass: "
                                            "north()  south()  east(3)  west()"),
    (r"\)\s*(?!(?:and|or|not|if|else|in|is)\b)[A-Za-z_]\w*\s*\(",
     "put each command on its own line"),
    (r"\brange\s+\d", "range needs brackets round the number, like  range(8)"),
    (r"^(repeat|loop)\b", "to repeat lines, write  for i in range(7):  and push "
                          "the lines to repeat in under it"),
]
KEYWORDS = ["return", "if", "elif", "else", "while", "for", "def", "print", "global"]


def syntax_message(e, def_example="def steer():"):
    """A friendly sentence for a SyntaxError, pointing at its line."""
    msg, text = e.msg or "", (e.text or "").strip()
    code = re.sub(r"\"[^\"]*\"|'[^']*'", '""', text)   # ignore what's inside text
    words = code.replace("(", " ").replace(":", " ").split()
    first = words[0] if words else ""
    # A misspelt Python word starting the line, like  retrun "left"  or  esle:
    typo = re.match(r"(\w+)(\s+[\w\"'(]|\s*:)", code)
    near = difflib.get_close_matches(first.lower(), KEYWORDS, 1, 0.75) \
        if typo and first.lower() not in keyword.kwlist else []
    if words[:2] == ["else", "if"] or first in ("elseif", "elsif"):
        hint = "write  elif  for 'else if'"
    elif first == "def" and "(" not in code:
        hint = f"a def needs brackets, like  {def_example}"
    else:
        hint = next((h for key, h in LINE_HINTS if re.search(key, code)), None)
    if hint is None:
        hint = next((h for key, h in SYNTAX_HINTS if key in msg), None)
    odd = re.match(r"invalid character '(.)'", msg)   # like a long dash – from copying
    if hint is None and odd:
        hint = f"Python doesn't know the character  {odd[1]}  — type it again " \
               f"with the keyboard"
    if hint is None and near:
        hint = f"did you mean  {near[0]} ?  Check the spelling of  {first}"
    elif hint is None and first in ("elif", "else"):
        hint = f"{first} needs an  if  just above it, lined up with it"
    elif hint is None and first.lower() in keyword.kwlist and first != first.lower():
        hint = f"Python words use small letters: write  {first.lower()}  not  {first}"
    elif hint is None and text.count("(") != text.count(")"):
        hint = "a bracket  (  isn't closed with  )  on this line"
    elif hint is None:
        hint = "Python couldn't read it. Check for a missing  :  or  ( )  " \
               "and the indentation"
    return f"Syntax error on line {e.lineno or '?'}: {hint}" + \
        ("" if hint[-1] in ':)"' else ".")


class _Return(Exception):
    def __init__(self, value):
        self.value = value


class _Break(Exception):
    pass


class _Continue(Exception):
    pass


class _Frame:
    """Variables for the top of the program (module) or one function call."""

    def __init__(self, module, local_names=(), global_names=()):
        self.module = module
        self.vars = {}
        self.local_names = set(local_names)    # assigned somewhere in the def
        self.global_names = set(global_names)  # listed in a  global  line


def _function_names(fn):
    """Names a def assigns (its locals, as in real Python) and names it
    declares global. Nested defs aren't allowed, so a flat walk is right."""
    assigned, declared = set(), set()
    for node in ast.walk(fn):
        if isinstance(node, ast.Global):
            declared.update(node.names)
        elif isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store):
            assigned.add(node.id)
    assigned.update(a.arg for a in fn.args.args)
    return assigned - declared, declared


class Brain:
    """One student's program, parsed and set up once, then asked each turn."""

    def __init__(self, code, sensors, prints):
        self.sensors = sensors          # name -> zero-argument function
        self.prints = prints            # print() output lands in this list
        self.globals = _Frame(module=True)
        self.funcs = {}
        self.ops = 0
        self.budget = SETUP_BUDGET
        self.steering = False   # running the top of the program, not steer()
        self.depth = 0
        if len(code) > MAX_CODE:
            raise BotError(f"Your program is too long: the limit is {MAX_CODE} "
                           f"characters (about 100 lines). Delete some comments "
                           f"or lines you don't need.")
        # Invisible characters that come with copied code read as spaces.
        code = code.replace("\u00a0", " ").replace("\u200b", "").replace("\ufeff", "")
        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            raise BotError(syntax_message(e))
        try:
            self.run_block(tree.body, self.globals)
        except (_Break, _Continue):
            raise BotError("break and continue only work inside a loop.")
        steer = self.funcs.get("steer")
        if steer is None:
            near = difflib.get_close_matches("steer", [n.lower() for n in self.funcs],
                                             1, 0.6)
            name = next((n for n in self.funcs if near and n.lower() == near[0]), None)
            raise BotError(f"Your def is called {name}(), but the game asks  "
                           f"steer()  — spell it exactly like that."
                           if name else
                           'Your program needs a  def steer():  that returns '
                           '"left", "right" or "straight".')
        if steer.args.args:
            raise BotError("steer() shouldn't take anything in the ( ) — "
                           "write  def steer():")

    def steer(self, budget=STEER_BUDGET):
        self.ops = 0
        self.budget = budget
        self.steering = True
        return self.call_user(self.funcs["steer"], [])

    # ---- the interpreter ---------------------------------------------------

    def tick(self):
        self.ops += 1
        if self.ops > self.budget:
            raise _TooLong("steer() took too long to decide" if self.steering
                           else "The top of your program ran too long")

    def lookup(self, name, frame):
        if not frame.module and name not in frame.global_names:
            if name in frame.vars:
                return frame.vars[name]
            if name in frame.local_names:
                if name in self.globals.vars:
                    raise BotError(f"'{name}' is a variable from the top of your "
                                   f"program. To change it inside a function, "
                                   f"put  global {name}  as the function's "
                                   f"first line.")
                raise BotError(f"You used '{name}' before giving it a value.")
        if name in self.globals.vars:
            return self.globals.vars[name]
        if name in self.sensors or name in self.funcs:
            raise BotError(f"{name} is a command — put  ( )  after it to use it, "
                           f"like  {name}()")
        if name.lower() in TURNS:
            raise BotError(f'Put quotes round words, in small letters:  '
                           f'return "{name.lower()}"')
        if name in ("true", "false", "none"):
            raise BotError(f"Write {name.capitalize()} with a capital letter.")
        known = list(self.globals.vars) + list(frame.vars) + list(self.sensors)
        near = difflib.get_close_matches(name, known, 1, 0.75)
        raise BotError(f"I don't know '{name}'. Did you mean  {near[0]}"
                       f"{'()' if near[0] in self.sensors else ''} ?" if near else
                       f"I don't know the variable '{name}'. Did you set it "
                       f"first, like:  {name} = 0")

    def assign(self, name, value, frame):
        if name in self.sensors or name in self.funcs:
            raise BotError(f"'{name}' is already a command — pick another "
                           f"variable name.")
        if frame.module or name in frame.global_names:
            self.globals.vars[name] = value
        else:
            frame.vars[name] = value

    def number(self, value, what):
        if isinstance(value, bool) or not isinstance(value, int):
            raise BotError(f"{what} needs a whole number, not {value!r}.")
        return value

    def math(self, op, a, b):
        if isinstance(op, (ast.BitAnd, ast.BitOr)):
            word = "and" if isinstance(op, ast.BitAnd) else "or"
            raise BotError(f"Use the word  {word}  to join two checks, like:  "
                           f"if wall_ahead() {word} wall_left():")
        if isinstance(op, ast.Add) and isinstance(a, str) and isinstance(b, str):
            if len(a) + len(b) > 200:
                raise BotError("That text got too long.")
            return a + b
        if isinstance(a, str) or isinstance(b, str):
            raise BotError("You can't do math with text. To print words and a "
                           'number together use a comma:  print("room", 5)')
        a, b = self.number(a, "Math"), self.number(b, "Math")
        if isinstance(op, ast.Add):
            result = a + b
        elif isinstance(op, ast.Sub):
            result = a - b
        elif isinstance(op, ast.Mult):
            result = a * b
        elif isinstance(op, (ast.FloorDiv, ast.Mod)):
            if b == 0:
                raise BotError("You can't divide by zero.")
            result = a // b if isinstance(op, ast.FloorDiv) else a % b
        elif isinstance(op, ast.Div):
            raise BotError("Use // for whole-number division, like 10 // 2.")
        elif isinstance(op, (ast.Pow, ast.BitXor)):
            raise BotError(f"{'**' if isinstance(op, ast.Pow) else '^'} isn't part of the "
                           f"math here. For a power, multiply: 2 * 2 * 2 is 2 to "
                           f"the power 3.")
        else:
            raise BotError("That kind of math isn't allowed here.")
        if abs(result) > MAX_INT:
            raise BotError("That number got too big. Keep math under a billion.")
        return result

    def compare(self, op, a, b):
        try:
            if isinstance(op, ast.Eq):
                return a == b
            if isinstance(op, ast.NotEq):
                return a != b
            if isinstance(op, ast.Lt):
                return a < b
            if isinstance(op, ast.LtE):
                return a <= b
            if isinstance(op, ast.Gt):
                return a > b
            if isinstance(op, ast.GtE):
                return a >= b
        except TypeError:
            raise BotError("Compare like with like: numbers with numbers, "
                           "text with text.")
        if isinstance(op, (ast.Is, ast.IsNot)):
            raise BotError("To compare, use  ==  or  !=  instead of  is.")
        raise BotError("That comparison isn't allowed. Use  < <= > >= == !=")

    def eval(self, node, frame):
        self.tick()   # every piece of an expression is work, not just each line
        if isinstance(node, ast.Constant):
            v = node.value
            if v is None or isinstance(v, (int, bool)):
                return v
            if isinstance(v, str) and len(v) <= 200:
                return v
            raise BotError("Use whole numbers, short text, True/False or None.")
        if isinstance(node, ast.Name):
            return self.lookup(node.id, frame)
        if isinstance(node, ast.UnaryOp):
            v = self.eval(node.operand, frame)
            if isinstance(node.op, ast.Not):
                return not v
            if isinstance(node.op, ast.USub):
                return -self.number(v, "A minus sign")
            if isinstance(node.op, ast.UAdd):
                return self.number(v, "A plus sign")
            raise BotError("That operator isn't allowed.")
        if isinstance(node, ast.BinOp):
            return self.math(node.op, self.eval(node.left, frame),
                             self.eval(node.right, frame))
        if isinstance(node, ast.BoolOp):
            wanted = isinstance(node.op, ast.Or)   # or stops at the first truthy
            result = self.eval(node.values[0], frame)
            for v in node.values[1:]:
                if bool(result) == wanted:
                    return result
                result = self.eval(v, frame)
            return result
        if isinstance(node, ast.Compare):
            left = self.eval(node.left, frame)
            for op, comp in zip(node.ops, node.comparators):
                right = self.eval(comp, frame)
                if not self.compare(op, left, right):
                    return False
                left = right
            return True
        if isinstance(node, ast.Call):
            return self.call(node, frame)
        if isinstance(node, ast.IfExp):   # "left" if wall_right() else "right"
            branch = node.body if self.eval(node.test, frame) else node.orelse
            return self.eval(branch, frame)
        if isinstance(node, (ast.List, ast.Tuple, ast.Dict, ast.Set, ast.ListComp,
                             ast.Subscript)):
            raise BotError("Lists and [ ] aren't part of Light Cycles — use a "
                           "few separate variables instead.")
        if isinstance(node, ast.JoinedStr):
            raise BotError("f-strings aren't part of Light Cycles. To print words "
                           'and a number use a comma:  print("room", space_ahead())')
        if isinstance(node, ast.Attribute):
            raise BotError("Dots like  random.choice  aren't part of Light Cycles "
                           "— use the sensors, or make a command with def.")
        raise BotError("I can't understand that. Use numbers, text, variables, "
                       "sensors, + - * // % and comparisons.")

    def call(self, node, frame):
        if isinstance(node.func, ast.Attribute):
            raise BotError(f"{ast.unparse(node.func)}() isn't part of Light Cycles "
                           f"— use the sensors, or make a command with def.")
        if not isinstance(node.func, ast.Name):
            raise BotError("I can only call plain commands, like  space_ahead()")
        if node.keywords:
            raise BotError("Commands don't take name=value arguments here.")
        name = node.func.id
        args = [self.eval(a, frame) for a in node.args]
        if name in self.sensors:
            if args:
                raise BotError(f"{name}() doesn't take anything in the ( ).")
            return self.sensors[name]()
        if name in self.funcs:
            return self.call_user(self.funcs[name], args)
        if name == "print":
            line = " ".join(str(a) for a in args)
            self.prints.append(line if len(line) <= 200 else line[:199] + "…")
            return None
        if name in ("max", "min"):
            if len(args) < 2:
                raise BotError(f"{name}() needs at least two numbers, like "
                               f"{name}(space_left(), space_right())")
            nums = [self.number(a, f"{name}()") for a in args]
            return max(nums) if name == "max" else min(nums)
        if name == "abs":
            if len(args) != 1:
                raise BotError("abs() takes one number.")
            return abs(self.number(args[0], "abs()"))
        if name == "range":
            raise BotError("range() only goes inside a for loop, like:  "
                           "for i in range(4):")
        if name in ("turn_left", "turn_right", "move"):
            raise BotError(f"There's no {name}() in Light Cycles. Your cycle "
                           f'always moves — steer() picks a way by returning '
                           f'"left", "right" or "straight".')
        if name in ("str", "int"):
            raise BotError(f"{name}() isn't needed here. To print words and a "
                           f'number use a comma:  print("room", space_ahead())')
        known = list(self.sensors) + list(self.funcs) + ["print", "max", "min", "abs"]
        near = difflib.get_close_matches(name.lower(), known, 1, 0.75)
        raise BotError(f"I don't know the command '{name}'. Did you mean  "
                       f"{near[0]}() ?" if near else
                       f"I don't know the command '{name}'. Check the sensor "
                       f"list, or make it with def.")

    def call_user(self, fn, args):
        self.tick()
        if len(args) != len(fn.args.args):
            raise BotError(f"{fn.name}() expected {len(fn.args.args)} thing(s) "
                           f"but got {len(args)}.")
        if self.depth >= 50:
            raise BotError(f"{fn.name}() called itself too many times.")
        local_names, global_names = fn._names
        frame = _Frame(False, local_names, global_names)
        for param, value in zip(fn.args.args, args):
            frame.vars[param.arg] = value
        self.depth += 1
        try:
            self.run_block(fn.body, frame)
        except _Return as r:
            return r.value
        except (_Break, _Continue):
            raise BotError("break and continue only work inside a loop.")
        finally:
            self.depth -= 1
        return None

    def run_loop_body(self, body, frame):
        """Run one pass of a loop body. False means a break happened."""
        try:
            self.run_block(body, frame)
        except _Break:
            return False
        except _Continue:
            pass
        return True

    def run_block(self, stmts, frame):
        for node in stmts:
            try:
                self.run_statement(node, frame)
            except BotError as e:
                # Point at the innermost line, or for a stuck loop, the loop.
                if isinstance(e, _TooLong) and not e.in_loop and \
                        isinstance(node, (ast.While, ast.For)):
                    e.line = node.lineno
                    e.in_loop = "while" if isinstance(node, ast.While) else "for"
                elif e.line is None:
                    e.line = node.lineno
                raise

    def run_statement(self, node, frame):
        self.tick()
        if isinstance(node, ast.FunctionDef):
            if not frame.module:
                raise BotError("Make each def at the top level, not inside "
                               "another function.")
            a = node.args
            if (a.vararg or a.kwarg or a.kwonlyargs or a.defaults
                    or a.posonlyargs or node.decorator_list):
                raise BotError("Keep functions simple:  def name(a, b):  "
                               "with no defaults or * arguments.")
            if node.name in self.sensors:
                raise BotError(f"{node.name}() is already a sensor — "
                               f"pick another name.")
            if node.name in self.funcs and self.funcs[node.name] is not node:
                raise BotError(f"There are two  def {node.name}():  — keep "
                               f"just one.")
            node._names = _function_names(node)
            self.funcs[node.name] = node
        elif isinstance(node, ast.Return) and frame.module:
            raise BotError("return only works inside a function you made "
                           "with def.")
        elif isinstance(node, ast.Return):
            raise _Return(None if node.value is None
                          else self.eval(node.value, frame))
        elif isinstance(node, ast.If):
            branch = node.body if self.eval(node.test, frame) else node.orelse
            self.run_block(branch, frame)
        elif isinstance(node, ast.While):
            while self.eval(node.test, frame):
                self.tick()
                if not self.run_loop_body(node.body, frame):
                    break
        elif isinstance(node, ast.For):
            it = node.iter
            if not (isinstance(it, ast.Call) and isinstance(it.func, ast.Name)
                    and it.func.id == "range" and not it.keywords
                    and isinstance(node.target, ast.Name)):
                raise BotError("A for loop must look like:  "
                               "for i in range(4):")
            nums = [self.number(self.eval(a, frame), "range()")
                    for a in it.args]
            if not 1 <= len(nums) <= 3 or (len(nums) == 3 and nums[2] == 0):
                raise BotError("range() takes 1 to 3 numbers, and the "
                               "step can't be 0.")
            for value in range(*nums):
                self.tick()
                self.assign(node.target.id, value, frame)
                if not self.run_loop_body(node.body, frame):
                    break
        elif isinstance(node, ast.Assign):
            if any(not isinstance(t, ast.Name) for t in node.targets):
                raise BotError("Assign to a simple name, like:  turns = 0")
            value = self.eval(node.value, frame)
            for t in node.targets:
                self.assign(t.id, value, frame)
        elif isinstance(node, ast.AugAssign):
            if not isinstance(node.target, ast.Name):
                raise BotError("Assign to a simple name, like:  turns += 1")
            name = node.target.id
            value = self.math(node.op, self.lookup(name, frame),
                              self.eval(node.value, frame))
            self.assign(name, value, frame)
        elif isinstance(node, ast.Global):
            if frame.module:
                raise BotError("global only goes inside a function.")
        elif isinstance(node, ast.Expr):
            if isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
                return   # a docstring
            if not isinstance(node.value, ast.Call):
                raise BotError("That line doesn't do anything. Did you mean "
                               "to return it?")
            self.call(node.value, frame)
        elif isinstance(node, ast.Pass):
            pass
        elif isinstance(node, ast.Break):
            raise _Break()
        elif isinstance(node, ast.Continue):
            raise _Continue()
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            raise BotError("import isn't allowed in Light Cycles — "
                           "everything you need is already here.")
        else:
            raise BotError("That line isn't something I can run here.")


# ---- arenas ----------------------------------------------------------------

def box(rows, cols):
    """An empty arena: a wall all the way round."""
    return [["#"] * cols] + [["#"] + ["."] * (cols - 2) + ["#"]
                             for _ in range(rows - 2)] + [["#"] * cols]


def fill(grid, r, c, h, w):
    for rr in range(r, r + h):
        for cc in range(c, c + w):
            grid[rr][cc] = "#"


def _practice_arenas():
    open_grid = box(20, 30)

    pillars = box(20, 30)
    for r, c in ((6, 8), (6, 20), (12, 8), (12, 20)):
        fill(pillars, r, c, 2, 2)

    split = box(20, 30)
    fill(split, 9, 3, 2, 10)
    fill(split, 9, 17, 2, 10)

    # Starts: (row, col, direction). Each heat puts the student somewhere
    # different, so no one corner decides the result.
    corners = [(4, 4, 1), (4, 25, 2), (15, 25, 3), (15, 4, 0)]
    return [
        {"name": "Open Grid", "grid": open_grid, "starts": corners},
        {"name": "Pillar Hall", "grid": pillars,
         "starts": corners[1:] + corners[:1]},
        {"name": "The Divide", "grid": split,
         "starts": [(16, 5, 1), (3, 24, 3), (6, 5, 1), (13, 24, 3)]},
    ]


PRACTICE = _practice_arenas()

HOUSE_BOTS = [
    {"name": "Rex", "color": "#ff6577", "code": '''
# Rex goes straight and turns right at the last second.
def steer():
    if wall_ahead():
        return "right"
    return "straight"
'''},
    {"name": "Cora", "color": "#f4c95d", "code": '''
# Cora always heads for whichever way has the most room.
def steer():
    ahead = space_ahead()
    left = space_left()
    right = space_right()
    if ahead >= left and ahead >= right:
        return "straight"
    if left > right:
        return "left"
    return "right"
'''},
    {"name": "Hugo", "color": "#69a8ff", "code": '''
# Hugo keeps going straight while there's room, and when he must turn he
# turns the way with more space.
def steer():
    if space_ahead() > 2:
        return "straight"
    if space_left() > space_right():
        return "left"
    return "right"
'''},
]


def royale_arena(n, seed):
    """A box sized for n cycles, with starts spread out and a few pillars."""
    rng = random.Random(seed)
    cols = max(36, min(100, round(math.sqrt(n * 200 * 1.5))))
    rows = max(24, round(cols * 2 / 3))
    grid = box(rows, cols)
    # A grid of start slots, inset from the walls, shuffled each round.
    across = max(2, math.ceil(math.sqrt(n * 1.5)))
    down = max(2, math.ceil(n / across))
    slots = []
    for i in range(down):
        for j in range(across):
            r = round((i + 0.5) * (rows - 2) / down) + 1
            c = round((j + 0.5) * (cols - 2) / across) + 1
            slots.append((r, c))
    rng.shuffle(slots)
    starts = []
    for r, c in slots[:n]:
        # Face the middle along whichever axis is further from it, so every
        # cycle starts with room ahead.
        dr, dc = rows / 2 - r, cols / 2 - c
        d = (2 if dr > 0 else 0) if abs(dr) > abs(dc) else (1 if dc > 0 else 3)
        starts.append((r, c, d))
    # Pillars, but none near a start or in the first squares ahead of one,
    # so nobody's round is decided by where they happened to start.
    clear = set()
    for r, c, d in starts:
        dr, dc = DIRS[d]
        clear.update((r + i, c + j) for i in range(-3, 4) for j in range(-3, 4))
        clear.update((r + dr * k, c + dc * k) for k in range(1, 7))
    for _ in range(n // 3 + 3):
        r, c = rng.randrange(2, rows - 3), rng.randrange(2, cols - 3)
        if not {(r, c), (r + 1, c), (r, c + 1), (r + 1, c + 1)} & clear:
            fill(grid, r, c, 2, 2)
    return grid, starts


# ---- a match ---------------------------------------------------------------

def bad_return(choice):
    """The one-time warning when steer() answers something that isn't a way."""
    if choice is None:
        return ("steer() didn't return anything. End it with  return \"left\", "
                "\"right\" or \"straight\"  — going straight for now.")
    if isinstance(choice, str) and choice.strip().lower() in TURNS:
        return (f"steer() returned {choice!r}. Use small letters and no spaces: "
                f"\"{choice.strip().lower()}\"  — going straight for now.")
    return (f"steer() returned {choice!r}. Return \"left\", \"right\" or "
            f"\"straight\"  — going straight for now.")


def run_match(entries, grid, starts):
    """Race every entry until at most one is left (or none, if alone).

    entries: [{"key", "name", "color", "code"}]; starts: one (row, col, dir)
    per entry. Returns the replay the browsers animate: each cycle's path,
    when and why it crashed, its place, and its print() output.
    """
    rows, cols = len(grid), len(grid[0])
    owner = {}   # (r, c) -> index of the cycle whose trail is there

    def solid(r, c):
        return not (0 <= r < rows and 0 <= c < cols) or grid[r][c] == "#" \
            or (r, c) in owner

    bikes = []
    for i, (entry, (r, c, d)) in enumerate(zip(entries, starts)):
        bike = {"entry": entry, "r": r, "c": c, "d": d, "path": [[r, c]],
                "dirs": [d], "died": None, "cause": "", "crash": None,
                "error": False, "prints": [], "dropped": 0, "warned": False,
                "looks": {}}
        owner[(r, c)] = i
        bikes.append(bike)

    def sensors_for(bike):
        def look(turn):
            return DIRS[(bike["d"] + turn) % 4]

        def wall(turn):
            dr, dc = look(turn)
            return solid(bike["r"] + dr, bike["c"] + dc)

        def space(turn):
            # The board can't change while bots decide, so count each way
            # once per turn: asking again is cheap, however often a bot asks.
            if turn not in bike["looks"]:
                dr, dc = look(turn)
                r, c, n = bike["r"] + dr, bike["c"] + dc, 0
                while not solid(r, c):
                    n += 1
                    r, c = r + dr, c + dc
                bike["looks"][turn] = n
            return bike["looks"][turn]

        return {
            "wall_ahead": lambda: wall(0), "wall_left": lambda: wall(-1),
            "wall_right": lambda: wall(1), "space_ahead": lambda: space(0),
            "space_left": lambda: space(-1), "space_right": lambda: space(1),
        }

    for bike in bikes:
        try:
            bike["brain"] = Brain(bike["entry"]["code"], sensors_for(bike),
                                  bike["prints"])
        except BotError as e:
            bike["died"], bike["cause"] = 0, f"💥 code error: {e}"
        except RecursionError:
            bike["died"], bike["cause"] = 0, "💥 code error: that line is too deeply nested."
        bike["error"] = bike["died"] == 0

    def tag(prints, turn, start):
        # Mark which turn each new print() line came from.
        for k in range(start, len(prints)):
            prints[k] = f"turn {turn} › {prints[k]}"

    def keep_last(b):
        extra = len(b["prints"]) - MAX_PRINTS
        if extra > 0:
            b["dropped"] += extra
            del b["prints"][:extra]

    for b in bikes:
        keep_last(b)   # the top of the program may print too

    turn = spent = 0
    budget = STEER_BUDGET + ARENA_BUDGET * max(rows, cols)
    stop_at = 0 if len(bikes) == 1 else 1
    free = sum(row.count(".") for row in grid)
    while sum(b["died"] is None for b in bikes) > stop_at and turn < free \
            and spent < MATCH_BUDGET:
        turn += 1
        alive = [b for b in bikes if b["died"] is None]
        # Everyone decides from the same picture of the board, then all move.
        for b in alive:
            before = len(b["prints"])
            b["looks"] = {}
            try:
                choice = b["brain"].steer(budget)
            except BotError as e:
                b["died"], b["cause"] = turn, f"💥 error in steer(): {e}"
                b["error"] = True
                continue
            except RecursionError:
                b["died"], b["cause"] = turn, "💥 error in steer(): too deeply nested."
                b["error"] = True
                continue
            finally:
                tag(b["prints"], turn, before)
                keep_last(b)
                spent += b["brain"].ops
            if choice not in TURNS:
                if not b["warned"]:
                    b["prints"].append(f"turn {turn} ⚠️ {bad_return(choice)}")
                    keep_last(b)
                b["warned"] = True
                choice = "straight"
            b["d"] = (b["d"] + TURNS[choice]) % 4
        moving = [b for b in alive if b["died"] is None]
        targets = {}
        for b in moving:
            dr, dc = DIRS[b["d"]]
            b["next"] = (b["r"] + dr, b["c"] + dc)
            targets.setdefault(b["next"], []).append(b)
        for b in moving:
            r, c = b["next"]
            others = [o for o in targets[b["next"]] if o is not b]
            hit = owner.get((r, c))
            swap = hit is not None and bikes[hit] in moving and \
                bikes[hit]["next"] == (b["r"], b["c"])
            if swap:
                # Two cycles trying to trade squares meet in the middle.
                b["cause"] = f"crashed head-on into {bikes[hit]['entry']['name']}"
            elif solid(r, c):
                b["cause"] = ("hit the arena wall" if hit is None
                              else "hit their own trail" if bikes[hit] is b
                              else f"hit {bikes[hit]['entry']['name']}'s trail")
            elif others:
                b["cause"] = f"crashed head-on into {others[0]['entry']['name']}"
            else:
                continue
            b["died"], b["crash"] = turn, [r, c]
            b["dirs"][-1] = b["d"]   # it turned to face what it hit
        for b in moving:
            if b["died"] is None:
                b["r"], b["c"] = b["next"]
                owner[b["next"]] = bikes.index(b)
                b["path"].append([b["r"], b["c"]])
                b["dirs"].append(b["d"])

    def lasted(b):
        return math.inf if b["died"] is None else b["died"]

    out = []
    for b in bikes:
        entry = b["entry"]
        out.append({
            "key": entry["key"], "name": entry["name"], "color": entry["color"],
            "dir": starts[bikes.index(b)][2], "path": b["path"],
            "dirs": b["dirs"],   # which way it faces at each square of path
            "died": b["died"], "cause": b["cause"], "crash": b["crash"],
            "error": b["error"],   # crashed because of a code error
            "place": 1 + sum(lasted(o) > lasted(b) for o in bikes),
            "outlasted": sum(lasted(o) < lasted(b) for o in bikes),
            "prints": ([f"… {b['dropped']} earlier lines not shown"]
                       if b["dropped"] else []) + b["prints"],
        })
    return {"grid": ["".join(row) for row in grid], "turns": turn, "bikes": out}


def practice(code, name, color):
    """The student's cycle against the three house bots on every practice
    arena. The student's start rotates, so every heat is a fresh test."""
    you = {"key": "you", "name": name, "color": color, "code": code}
    heats = []
    for arena in PRACTICE:
        result = run_match([you] + HOUSE_BOTS_ENTRIES, arena["grid"],
                           arena["starts"])
        result["name"] = arena["name"]
        heats.append(result)
    return heats


HOUSE_BOTS_ENTRIES = [dict(bot, key=f"house{i}") for i, bot in enumerate(HOUSE_BOTS)]
