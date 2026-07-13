"""
Maze Coder — a classroom game.

Students connect from their browsers to your laptop and drive a little
character through a maze by typing Python:

    move()          move forward one square
    move(3)         move forward 3 squares
    turn_left()     rotate left
    turn_right()    rotate right
    turn_around()   spin 180 degrees

for loops work too, and the leaderboard rewards SHORT solutions, so:

    for i in range(4):
        move()
        turn_right()

while loops and if statements work as well, using these yes/no "sensors":

    wall_ahead()    is there a wall right in front of me?
    can_move()      is the way ahead clear?
    at_goal()       am I standing on the exit?

    while not wall_ahead():
        move()

Variables, whole-number math, and your own functions work too, so clever
short solutions can appear:

    steps = 3
    move(steps * 2)

    def zigzag():
        move()
        turn_right()

    for i in range(4):
        zigzag()

There's also a C++ mode — students flip a toggle in their browser and write
the same maze commands in real C++ syntax instead:

    for (int i = 0; i < 4; i++) {
        move();
        turn_right();
    }

Braces, semicolons, int/bool variables, void functions, && || !, if/else,
while, break/continue all work. Lines holding only braces don't count toward
the score, so Python and C++ solutions golf fairly against each other.

It stays safe by interpreting a whitelist of the parse tree ourselves — no
imports, attribute access, or builtins — so students never run real Python on
your laptop, only these commands.

The leaderboard and everyone's progress are saved to scores.json, so kids
can close the tab and pick up where they left off another day.

Run it:   python3 server.py
Then tell students the URL it prints (e.g. http://192.168.1.42:8000).

Teacher pages:
    /leaderboard    big live scoreboard to project
    /admin          reset scores, jump everyone to a maze (needs the key)

No installing anything — this uses only the Python standard library.
"""

import ast
import json
import os
import random
import re
import socket
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

PORT = 8000

# Where the leaderboard and everyone's progress is saved, so it survives a
# restart and kids can keep playing day to day.
STATE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "scores.json")

# ---------------------------------------------------------------------------
# Mazes.  '#' = wall, '.' = open, 'S' = start, 'G' = goal (the exit).
# Characters start on S facing right (East). Add or edit mazes freely —
# just keep every row the same width and make sure a path S -> G exists.
# ---------------------------------------------------------------------------
MAZES = [
    # 1 — straight shot. Discover move(10) instead of ten move()s.
    [
        "#############",
        "#S.........G#",
        "#############",
    ],
    # 2 — one corner. move(n), turn, move(n).
    [
        "#########",
        "#S......#",
        "#######.#",
        "#######.#",
        "#######.#",
        "#######G#",
        "#########",
    ],
    # 3 — staircase. A repeating step: your first for-loop.
    [
        "########",
        "#S.#####",
        "##..####",
        "###..###",
        "####..##",
        "#####.G#",
        "########",
    ],
    # 4 — snake. Each row-and-turn repeats; loop it.
    [
        "###########",
        "#S........#",
        "#########.#",
        "#.........#",
        "#.#########",
        "#.........#",
        "#########.#",
        "#G........#",
        "###########",
    ],
    # 5 — vertical comb. Same idea, turned sideways.
    [
        "#########",
        "#S#...#G#",
        "#.#.#.#.#",
        "#.#.#.#.#",
        "#.#.#.#.#",
        "#.#.#.#.#",
        "#.#.#.#.#",
        "#...#...#",
        "#########",
    ],
    # 6 — the big snake. Straight-line it and you'll type forever;
    #     a loop solves it in a handful of lines. Optimization finale.
    [
        "#############",
        "#S..........#",
        "###########.#",
        "#...........#",
        "#.###########",
        "#...........#",
        "###########.#",
        "#...........#",
        "#.###########",
        "#...........#",
        "###########.#",
        "#G..........#",
        "#############",
    ],
    # 7 — small spiral. Counting each arm is a pain; instead walk until a
    #     wall, turn, and repeat. Your first while-loop with a sensor:
    #         while not at_goal():
    #             while not wall_ahead():
    #                 move()
    #             turn_right()
    [
        "#########",
        "#S......#",
        "#######.#",
        "#.....#.#",
        "#.###.#.#",
        "#.#G..#.#",
        "#.#####.#",
        "#.......#",
        "#########",
    ],
    # 8 — dead ends! Now there are wrong turns. Counting won't help; you have
    #     to feel your way with the left-hand rule — keep your left hand on the
    #     wall and you'll always find the exit:
    #         while not at_goal():
    #             turn_left()
    #             while wall_ahead():
    #                 turn_right()
    #             move()
    [
        "#########",
        "#S....#.#",
        "#####.#.#",
        "#.....#.#",
        "#.#####.#",
        "#.#.....#",
        "#.###.#.#",
        "#.....#G#",
        "#########",
    ],
    # 9 — the grand labyrinth. Same left-hand rule, far more dead ends. The
    #     handful of lines that solved maze 8 walks the whole thing.
    [
        "#############",
        "#S....#.....#",
        "#####.#####.#",
        "#.....#...#.#",
        "#.#####.#.#.#",
        "#.#.....#...#",
        "#.###.#####.#",
        "#...#.#.#...#",
        "###.#.#.#.###",
        "#.....#....G#",
        "#############",
    ],
    # 10 — battlements. One "tooth" repeats over and over — up, across, down,
    #      across. Teach the character the tooth once, then loop it:
    #          def tooth():
    #              turn_left();  move(2)
    #              turn_right(); move(2)
    #              turn_right(); move(2)
    #              turn_left();  move(2)
    #          for i in range(3):
    #              tooth()
    [
        "###############",
        "#...#...#...###",
        "#.#.#.#.#.#.###",
        "#S#...#...#..G#",
        "###############",
    ],
    # 11 — the mirror spiral. Just like maze 7, but it winds the other way, so
    #      turn_left() where you used to turn_right().
    [
        "###########",
        "#.........#",
        "#.#######.#",
        "#.#.....#.#",
        "#.#.###.#.#",
        "#.#..G#.#.#",
        "#.#####.#.#",
        "#.......#.#",
        "#########.#",
        "#S........#",
        "###########",
    ],
    # 12 — a proper maze. More forks than maze 9 — the left-hand rule still
    #      carries you through every one.
    [
        "###########",
        "#S..#.....#",
        "###.###.#.#",
        "#.#.#...#.#",
        "#.#.#.###.#",
        "#...#.#.#.#",
        "#.###.#.#.#",
        "#...#.#.#.#",
        "###.#.#.#.#",
        "#.....#..G#",
        "###########",
    ],
    # 13 — the grand finale. The biggest labyrinth yet; the same wall-following
    #      lines that beat maze 8 walk this whole thing to the exit.
    [
        "#############",
        "#S....#.#...#",
        "#####.#.#.#.#",
        "#.....#...#.#",
        "#.#####.###.#",
        "#.#.......#.#",
        "#.###.#####.#",
        "#...#.#...#.#",
        "###.###.#.#.#",
        "#.#.#...#...#",
        "#.#.#.#####.#",
        "#.....#....G#",
        "#############",
    ],
]

# Direction vectors, indexed 0=North,1=East,2=South,3=West.
DIRS = [(-1, 0), (0, 1), (1, 0), (0, -1)]
DIR_ARROWS = ["▲", "▶", "▼", "◀"]

COLORS = [
    "#e6194b", "#3cb44b", "#4363d8", "#f58231", "#911eb4",
    "#42d4f4", "#f032e6", "#bfef45", "#fabed4", "#469990",
    "#9a6324", "#800000", "#808000", "#000075", "#e6beff",
]

MAX_STEPS = 500  # cap per Run so a runaway loop can't freeze the game

ADMIN_KEY = str(random.randint(1000, 9999))


class MazeError(Exception):
    """A friendly, student-facing problem with their code."""


class Scope:
    """A set of variables. Function bodies get their own child scope so their
    variables don't leak out; name lookups fall back to the parent (globals)."""

    def __init__(self, parent=None, hint="steps = 3"):
        self.vars = {}
        self.parent = parent
        self.hint = parent.hint if parent is not None else hint

    def get(self, name):
        s = self
        while s is not None:
            if name in s.vars:
                return s.vars[name]
            s = s.parent
        raise MazeError(f"I don't know the variable '{name}'. "
                        f"Did you set it first, like:  {self.hint}")

    def set(self, name, value):
        self.vars[name] = value


def find_start(maze):
    for r, row in enumerate(maze):
        for c, ch in enumerate(row):
            if ch == "S":
                return r, c
    return 1, 1


# ---------------------------------------------------------------------------
# Shared game state (guarded by a lock because requests run on threads).
# ---------------------------------------------------------------------------
lock = threading.Lock()
players = {}          # player_id -> dict
next_player_num = [0]


def save_state():
    """Write everyone's progress to disk. Called while holding `lock`."""
    try:
        tmp = STATE_FILE + ".tmp"
        with open(tmp, "w") as f:
            json.dump({"players": players, "next": next_player_num[0],
                       "admin_key": ADMIN_KEY}, f)
        os.replace(tmp, STATE_FILE)  # atomic: never leaves a half-written file
    except Exception:
        pass


def load_state():
    """Restore progress saved by a previous run, if any."""
    global ADMIN_KEY
    if not os.path.exists(STATE_FILE):
        return
    try:
        with open(STATE_FILE) as f:
            data = json.load(f)
    except Exception:
        return
    for pid, p in data.get("players", {}).items():
        # JSON turns the `best` dict's integer maze-keys into strings; undo that.
        p["best"] = {int(k): v for k, v in p.get("best", {}).items()}
        p.setdefault("unlocked", 0)  # older saves predate teacher unlocks
        players[pid] = p
    next_player_num[0] = data.get("next", len(players))
    # Reuse the same admin key across restarts so an open admin page keeps
    # working; fall back to this run's freshly generated one if none was saved.
    ADMIN_KEY = data.get("admin_key") or ADMIN_KEY


def new_player(name):
    pid = f"p{next_player_num[0]}"
    next_player_num[0] += 1
    color = COLORS[len(players) % len(COLORS)]
    sr, sc = find_start(MAZES[0])
    players[pid] = {
        "id": pid,
        "name": name[:20] or f"Player{pid}",
        "color": color,
        "maze": 0,
        "row": sr,
        "col": sc,
        "dir": 1,          # facing East
        "best": {},        # maze index -> fewest lines that solved it
        "unlocked": 0,     # highest maze index the teacher has unlocked by hand
        "code": "",        # what they're currently typing (for the big screen)
    }
    return players[pid]


def find_player_by_name(name):
    """A returning student who joins with the same name reattaches to their
    existing player instead of spawning a duplicate at maze 1."""
    key = name.strip().lower()
    if not key:
        return None
    for q in players.values():
        if q["name"].lower() == key:
            return q
    return None


def solved_count(p):
    return len(p["best"])


def total_lines(p):
    return sum(p["best"].values())


def cleared(p):
    return p["maze"] in p["best"]


def reset_to_start(p):
    sr, sc = find_start(MAZES[p["maze"]])
    p["row"], p["col"], p["dir"] = sr, sc, 1


# ---------------------------------------------------------------------------
# C++ mode.  We tokenize and parse a small C++ subset ourselves and build the
# same Python ast nodes the interpreter below already understands, so both
# languages run through the one safe interpreter.  A for(init; test; post)
# loop becomes its own CppFor node so `continue` still runs the post step
# (the i++) exactly like real C++.
# ---------------------------------------------------------------------------
class CppSyntax(Exception):
    def __init__(self, line, msg):
        super().__init__(msg)
        self.line = line
        self.msg = msg


class CppFor:
    def __init__(self, init, test, post, body):
        self.init, self.test, self.post, self.body = init, test, post, body


CPP_KEYWORDS = {"int", "bool", "void", "if", "else", "while", "for",
                "return", "break", "continue", "true", "false"}
CPP_TWO_CHAR = ("++", "--", "+=", "-=", "*=", "/=", "%=",
                "==", "!=", "<=", ">=", "&&", "||")
CPP_ONE_CHAR = "+-*/%<>=!(){};,"
CPP_CMP = {"==": ast.Eq, "!=": ast.NotEq, "<": ast.Lt,
           "<=": ast.LtE, ">": ast.Gt, ">=": ast.GtE}
CPP_MATH = {"+": ast.Add, "-": ast.Sub, "*": ast.Mult,
            "/": ast.FloorDiv, "%": ast.Mod}
CPP_BLOCK_COMMENT = re.compile(r"/\*.*?\*/", re.S)


def count_lines(code, lang):
    """Score a program: non-blank, non-comment lines. In C++ mode, lines
    holding only braces/semicolons are free, so both languages golf fairly."""
    if lang == "cpp":
        code = CPP_BLOCK_COMMENT.sub("", code)
        return len([l for l in code.splitlines()
                    if l.strip() and not l.strip().startswith("//")
                    and not set(l.strip()) <= set("{};")])
    return len([l for l in code.splitlines()
                if l.strip() and not l.strip().startswith("#")])


def cpp_tokenize(code):
    toks = []   # (kind, value, line) — kinds: num, name, kw, op
    i, line, n = 0, 1, len(code)
    while i < n:
        c = code[i]
        if c == "\n":
            line += 1
            i += 1
        elif c.isspace():
            i += 1
        elif code.startswith("//", i):
            j = code.find("\n", i)
            i = n if j < 0 else j
        elif code.startswith("/*", i):
            j = code.find("*/", i + 2)
            if j < 0:
                raise CppSyntax(line, "this /* comment never closes with */")
            line += code.count("\n", i, j)
            i = j + 2
        elif c.isdigit():
            j = i
            while j < n and code[j].isdigit():
                j += 1
            toks.append(("num", int(code[i:j]), line))
            i = j
        elif c.isalpha() or c == "_":
            j = i
            while j < n and (code[j].isalnum() or code[j] == "_"):
                j += 1
            w = code[i:j]
            toks.append(("kw" if w in CPP_KEYWORDS else "name", w, line))
            i = j
        elif code[i:i + 2] in CPP_TWO_CHAR:
            toks.append(("op", code[i:i + 2], line))
            i += 2
        elif c in CPP_ONE_CHAR:
            toks.append(("op", c, line))
            i += 1
        else:
            raise CppSyntax(line, f"I don't understand the character '{c}'")
    toks.append(("eof", "", line))
    return toks


def cpp_arguments(params):
    return ast.arguments(posonlyargs=[], args=[ast.arg(arg=p) for p in params],
                         vararg=None, kwonlyargs=[], kw_defaults=[],
                         kwarg=None, defaults=[])


class CppParser:
    def __init__(self, code):
        self.toks = cpp_tokenize(code)
        self.i = 0

    def peek(self, ahead=0):
        return self.toks[min(self.i + ahead, len(self.toks) - 1)]

    def line(self):
        return self.peek()[2]

    def next(self):
        t = self.toks[self.i]
        if t[0] != "eof":
            self.i += 1
        return t

    def check(self, val, ahead=0):
        k, v, _ = self.peek(ahead)
        return v == val and k in ("op", "kw")

    def eat(self, val):
        if self.check(val):
            self.next()
            return True
        return False

    def expect(self, val, msg=None):
        if not self.eat(val):
            k, v, line = self.peek()
            raise CppSyntax(line, msg or (f"I expected '{val}' here" +
                            (f", not '{v}'" if v else "")))

    def parse_program(self):
        out = []
        while self.peek()[0] != "eof":
            out.extend(self.parse_stmt())
        return out

    # ---- statements (each returns a LIST of nodes) ----
    def parse_stmt(self):
        k, v, line = self.peek()
        if self.eat(";"):
            return []
        if k == "kw" and v in ("int", "bool", "void"):
            if self.peek(1)[0] == "name" and self.check("(", 2):
                return [self.parse_funcdef()]
            if v == "void":
                raise CppSyntax(line, "void is only for making functions, "
                                "like:  void zigzag() { ... }")
            return [self.parse_decl()]
        if self.check("if"):
            return [self.parse_if()]
        if self.check("while"):
            self.next()
            self.expect("(", "while needs parentheses:  while (condition) { ... }")
            test = self.parse_expr()
            self.expect(")")
            return [ast.While(test=test, body=self.parse_block(), orelse=[])]
        if self.check("for"):
            return [self.parse_for()]
        if self.check("return"):
            self.next()
            value = None if self.check(";") else self.parse_expr()
            self.expect(";", f"missing ';' after return on line {line}")
            return [ast.Return(value=value)]
        if self.check("break"):
            self.next()
            self.expect(";", f"missing ';' after break on line {line}")
            return [ast.Break()]
        if self.check("continue"):
            self.next()
            self.expect(";", f"missing ';' after continue on line {line}")
            return [ast.Continue()]
        if self.check("{"):
            return self.parse_block()
        if self.check("else"):
            raise CppSyntax(line, "this 'else' has no 'if' in front of it")
        node = self.parse_simple()
        self.expect(";", f"missing ';' at the end of line {line}")
        return [node]

    def parse_simple(self):
        """One command / assignment / i++ — WITHOUT the trailing ';'."""
        k, v, line = self.peek()
        if k == "op" and v in ("++", "--"):
            self.next()
            nk, name, _ = self.next()
            if nk != "name":
                raise CppSyntax(line, f"'{v}' needs a variable, like:  i{v}")
            return ast.AugAssign(target=ast.Name(id=name),
                                 op=ast.Add() if v == "++" else ast.Sub(),
                                 value=ast.Constant(value=1))
        if k == "name":
            nxt = self.peek(1)[1]
            if nxt in ("++", "--"):
                self.next(); self.next()
                return ast.AugAssign(target=ast.Name(id=v),
                                     op=ast.Add() if nxt == "++" else ast.Sub(),
                                     value=ast.Constant(value=1))
            if nxt == "=":
                self.next(); self.next()
                return ast.Assign(targets=[ast.Name(id=v)], value=self.parse_expr())
            if nxt in ("+=", "-=", "*=", "/=", "%="):
                self.next(); self.next()
                return ast.AugAssign(target=ast.Name(id=v), op=CPP_MATH[nxt[0]](),
                                     value=self.parse_expr())
        expr = self.parse_expr()
        if not isinstance(expr, ast.Call):
            raise CppSyntax(line, "this doesn't do anything on its own — "
                            "call a command like  move();  or assign:  x = 3;")
        return ast.Expr(value=expr)

    def parse_decl(self):
        _, typ, line = self.next()
        k, name, _ = self.next()
        if k != "name":
            raise CppSyntax(line, f"{typ} needs a variable name, like:  {typ} x = "
                            + ("3;" if typ == "int" else "true;"))
        if self.eat("="):
            value = self.parse_expr()
        else:
            value = ast.Constant(value=0 if typ == "int" else False)
        if self.check(","):
            raise CppSyntax(line, "declare one variable per line, please")
        self.expect(";", f"missing ';' at the end of line {line}")
        return ast.Assign(targets=[ast.Name(id=name)], value=value)

    def parse_funcdef(self):
        self.next()  # the return type
        _, name, _ = self.next()
        self.expect("(")
        params = []
        if not self.check(")"):
            while True:
                tk, tv, tl = self.next()
                if not (tk == "kw" and tv in ("int", "bool")):
                    raise CppSyntax(tl, "each parameter needs a type, "
                                    "like:  void go(int steps)")
                pk, pname, _ = self.next()
                if pk != "name":
                    raise CppSyntax(tl, "each parameter needs a name, "
                                    "like:  void go(int steps)")
                params.append(pname)
                if not self.eat(","):
                    break
        self.expect(")")
        if not self.check("{"):
            raise CppSyntax(self.line(), "a function body needs { } braces")
        return ast.FunctionDef(name=name, args=cpp_arguments(params),
                               body=self.parse_block(), decorator_list=[])

    def parse_if(self):
        self.next()
        self.expect("(", "if needs parentheses:  if (condition) { ... }")
        test = self.parse_expr()
        self.expect(")")
        body = self.parse_block()
        orelse = []
        if self.eat("else"):
            orelse = [self.parse_if()] if self.check("if") else self.parse_block()
        return ast.If(test=test, body=body, orelse=orelse)

    def parse_for(self):
        self.next()
        self.expect("(", "for loops look like:  for (int i = 0; i < 4; i++) { ... }")
        if self.eat(";"):
            init = []
        elif self.peek()[0] == "kw" and self.peek()[1] in ("int", "bool"):
            init = [self.parse_decl()]        # parse_decl eats its own ';'
        else:
            init = [self.parse_simple()]
            self.expect(";", "for needs two ';' inside the ( ):  "
                        "for (int i = 0; i < 4; i++)")
        test = ast.Constant(value=True) if self.check(";") else self.parse_expr()
        self.expect(";", "for needs two ';' inside the ( ):  "
                    "for (int i = 0; i < 4; i++)")
        post = [] if self.check(")") else [self.parse_simple()]
        self.expect(")")
        return CppFor(init, test, post, self.parse_block())

    def parse_block(self):
        if self.eat("{"):
            out = []
            while not self.check("}"):
                if self.peek()[0] == "eof":
                    raise CppSyntax(self.line(), "a '{' was never closed with '}'")
                out.extend(self.parse_stmt())
            self.next()
            return out
        return self.parse_stmt()      # C++ allows a braceless single statement

    # ---- expressions (precedence: || then && then compare, + -, * / %, !) ----
    def parse_expr(self):
        node = self.parse_and()
        if self.check("||"):
            values = [node]
            while self.eat("||"):
                values.append(self.parse_and())
            return ast.BoolOp(op=ast.Or(), values=values)
        return node

    def parse_and(self):
        node = self.parse_cmp()
        if self.check("&&"):
            values = [node]
            while self.eat("&&"):
                values.append(self.parse_cmp())
            return ast.BoolOp(op=ast.And(), values=values)
        return node

    def parse_cmp(self):
        left = self.parse_add()
        k, v, line = self.peek()
        if k == "op" and v in CPP_CMP:
            self.next()
            right = self.parse_add()
            nk, nv, nline = self.peek()
            if nk == "op" and nv in CPP_CMP:
                raise CppSyntax(nline, "compare two things at a time, "
                                "like:  a < b && b < c")
            return ast.Compare(left=left, ops=[CPP_CMP[v]()], comparators=[right])
        if k == "op" and v == "=":
            raise CppSyntax(line, "use == to compare (a single = assigns)")
        return left

    def parse_add(self):
        node = self.parse_mul()
        while self.peek()[0] == "op" and self.peek()[1] in ("+", "-"):
            _, v, _ = self.next()
            node = ast.BinOp(left=node, op=CPP_MATH[v](), right=self.parse_mul())
        return node

    def parse_mul(self):
        node = self.parse_unary()
        while self.peek()[0] == "op" and self.peek()[1] in ("*", "/", "%"):
            _, v, _ = self.next()
            node = ast.BinOp(left=node, op=CPP_MATH[v](), right=self.parse_unary())
        return node

    def parse_unary(self):
        k, v, line = self.peek()
        if k == "op" and v in ("!", "-", "+"):
            self.next()
            ops = {"!": ast.Not, "-": ast.USub, "+": ast.UAdd}
            return ast.UnaryOp(op=ops[v](), operand=self.parse_unary())
        if k == "op" and v in ("++", "--"):
            raise CppSyntax(line, f"put {v} on its own line, like:  i{v};")
        return self.parse_primary()

    def parse_primary(self):
        k, v, line = self.next()
        if k == "num":
            return ast.Constant(value=v)
        if k == "kw" and v in ("true", "false"):
            return ast.Constant(value=(v == "true"))
        if k == "op" and v == "(":
            node = self.parse_expr()
            self.expect(")")
            return node
        if k == "name":
            if self.eat("("):
                args = []
                if not self.check(")"):
                    args.append(self.parse_expr())
                    while self.eat(","):
                        args.append(self.parse_expr())
                self.expect(")", f"missing ')' for {v}( on line {line}")
                return ast.Call(func=ast.Name(id=v), args=args, keywords=[])
            return ast.Name(id=v)
        raise CppSyntax(line, f"I wasn't expecting '{v}' here" if v
                        else "your code ends in the middle of something")


# ---------------------------------------------------------------------------
# Running a student's code.  We parse it with Python's own parser (or the C++
# parser above) but only allow move/turn commands and simple control flow —
# so it's safe to run on your laptop (no imports, no file access, no
# arbitrary code).
# ---------------------------------------------------------------------------
def run_code(p, code, lang="python"):
    log = []
    n_lines = count_lines(code, lang)

    if lang == "cpp":
        try:
            body = CppParser(code).parse_program()
        except CppSyntax as e:
            return {"log": [f"❌ Syntax error on line {e.line}: {e.msg}.",
                             "   Check your ; { } ( ) — every command ends with ';'"],
                    "trace": []}
    else:
        try:
            body = ast.parse(code).body
        except SyntaxError as e:
            return {"log": [f"❌ Syntax error on line {e.lineno or '?'}: {e.msg}",
                             "   Check your ( ) and add ':' after  for i in range(n)"],
                    "trace": []}

    # Every Run starts the character over at the maze's start, so students
    # must write a full solution instead of nudging forward one move at a time.
    reset_to_start(p)
    if n_lines:
        log.append("🔄 Back to the start — running your whole program…")
    maze = MAZES[p["maze"]]
    steps = [0]

    # Snapshot of position/facing after every move/turn, so the frontend can
    # animate the character walking the path instead of jumping to the end.
    trace = [{"row": p["row"], "col": p["col"], "dir": p["dir"]}]

    def snapshot():
        trace.append({"row": p["row"], "col": p["col"], "dir": p["dir"]})

    class Solved(Exception):
        pass

    class StepLimit(Exception):
        pass

    def tick():
        steps[0] += 1
        if steps[0] > MAX_STEPS:
            raise StepLimit()

    def solve():
        idx = p["maze"]
        prev = p["best"].get(idx)
        p["best"][idx] = n_lines if prev is None else min(prev, n_lines)
        if prev is None:
            log.append(f"🎉 You reached the exit in {n_lines} line(s)!")
            log.append("   Press ▶ Next Maze to move on — or shorten your "
                       "code first to climb the leaderboard.")
        elif n_lines < prev:
            log.append(f"✅ New best: {n_lines} line(s) (was {prev})! Nice optimizing.")
            log.append("   Press ▶ Next Maze when you're happy with it.")
        else:
            log.append(f"🎉 Reached the exit in {n_lines} line(s). "
                       f"Your best here is {p['best'][idx]}.")
            log.append("   Press ▶ Next Maze to continue, or keep shortening.")

    def do_move(n):
        for _ in range(n):
            tick()
            dr, dc = DIRS[p["dir"]]
            nr, nc = p["row"] + dr, p["col"] + dc
            if maze[nr][nc] == "#":
                log.append(f"🧱 Bumped into a wall at row {p['row']}, col {p['col']}.")
                return
            p["row"], p["col"] = nr, nc
            snapshot()
            if maze[nr][nc] == "G":
                solve()
                raise Solved()

    def do_turn(delta, word):
        p["dir"] = (p["dir"] + delta) % 4
        snapshot()
        log.append(f"{word} Now facing {DIR_ARROWS[p['dir']]}.")

    # Sensors — yes/no questions students ask inside if / while conditions.
    def wall_ahead():
        dr, dc = DIRS[p["dir"]]
        return maze[p["row"] + dr][p["col"] + dc] == "#"

    SENSORS = {
        "wall_ahead": wall_ahead,
        "at_goal": lambda: maze[p["row"]][p["col"]] == "G",
        "can_move": lambda: not wall_ahead(),
    }

    class ReturnValue(Exception):
        def __init__(self, value):
            self.value = value

    class BreakLoop(Exception):
        pass

    class ContinueLoop(Exception):
        pass

    global_scope = Scope(hint="int steps = 3;" if lang == "cpp" else "steps = 3")
    funcs = {}               # name -> ast.FunctionDef the student wrote
    depth = [0]              # how deep we are in nested function calls

    def truthy(v):
        return bool(v)

    def require_int(v, what):
        # bools are ints in Python, but for a maze we want real numbers.
        if isinstance(v, bool) or not isinstance(v, int):
            raise MazeError(f"{what} needs a whole number.")
        return v

    def int_binop(op, a, b, what):
        a, b = require_int(a, what), require_int(b, what)
        if isinstance(op, ast.Add):
            return a + b
        if isinstance(op, ast.Sub):
            return a - b
        if isinstance(op, ast.Mult):
            return a * b
        if isinstance(op, ast.FloorDiv):
            if b == 0:
                raise MazeError("You can't divide by zero.")
            return a // b
        if isinstance(op, ast.Mod):
            if b == 0:
                raise MazeError("You can't divide by zero.")
            return a % b
        if isinstance(op, ast.Div):
            raise MazeError("Use // for whole-number division, like 10 // 2.")
        raise MazeError("That kind of math isn't allowed here.")

    def compare(op, a, b):
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
        raise MazeError("That comparison isn't allowed. Use  <  <=  >  >=  ==  !=")

    def eval_expr(node, scope):
        """Work out the value (a number or True/False) of an expression."""
        if isinstance(node, ast.Constant):
            if isinstance(node.value, (int, bool)):
                return node.value
            raise MazeError("Only whole numbers and True/False are allowed.")
        if isinstance(node, ast.Name):
            return scope.get(node.id)
        if isinstance(node, ast.UnaryOp):
            if isinstance(node.op, ast.Not):
                return not truthy(eval_expr(node.operand, scope))
            v = eval_expr(node.operand, scope)
            if isinstance(node.op, ast.USub):
                return -require_int(v, "a minus sign")
            if isinstance(node.op, ast.UAdd):
                return +require_int(v, "a plus sign")
            raise MazeError("That operator isn't allowed.")
        if isinstance(node, ast.BinOp):
            return int_binop(node.op, eval_expr(node.left, scope),
                             eval_expr(node.right, scope), "math")
        if isinstance(node, ast.BoolOp):
            wanted = isinstance(node.op, ast.Or)   # or wants the first truthy one
            result = eval_expr(node.values[0], scope)
            for v in node.values[1:]:
                if truthy(result) == wanted:
                    return result
                result = eval_expr(v, scope)
            return result
        if isinstance(node, ast.Compare):
            left = eval_expr(node.left, scope)
            for op, comp in zip(node.ops, node.comparators):
                right = eval_expr(comp, scope)
                if not compare(op, left, right):
                    return False
                left = right
            return True
        if isinstance(node, ast.Call):
            return call_fn(node, scope)
        raise MazeError("I can't understand that. Use numbers, variables, "
                        "commands, and + - * // % with < > == and / or / not.")

    def eval_range(call, scope):
        args = [require_int(eval_expr(a, scope), "range()") for a in call.args]
        if not 1 <= len(args) <= 3:
            raise MazeError("range() takes 1 to 3 numbers.")
        if len(args) == 3 and args[2] == 0:
            raise MazeError("range() step can't be 0.")
        return range(*args)

    def call_user(fn, args):
        tick()  # each call counts, so runaway recursion hits the step limit
        if len(args) != len(fn.args.args):
            raise MazeError(f"{fn.name}() expected {len(fn.args.args)} thing(s) "
                            f"but got {len(args)}.")
        depth[0] += 1
        if depth[0] > 100:
            depth[0] -= 1
            raise MazeError(f"{fn.name}() called itself too many times.")
        local = Scope(global_scope)
        for param, val in zip(fn.args.args, args):
            local.set(param.arg, val)
        try:
            exec_block(fn.body, local)
        except ReturnValue as r:
            return r.value
        except (BreakLoop, ContinueLoop):
            raise MazeError("break and continue only work inside a loop.")
        finally:
            depth[0] -= 1
        return None

    def call_fn(call, scope):
        if not isinstance(call.func, ast.Name):
            raise MazeError("I can only call plain commands, like  move()")
        if call.keywords:
            raise MazeError("Commands don't take name=value arguments here.")
        name = call.func.id
        args = [eval_expr(a, scope) for a in call.args]
        if name == "move":
            do_move(require_int(args[0], "move()") if args else 1)
            return None
        if name == "turn_left":
            do_turn(-1, "↺ Turned left.")
            return None
        if name == "turn_right":
            do_turn(1, "↻ Turned right.")
            return None
        if name == "turn_around":
            do_turn(2, "↔ Turned around.")
            return None
        if name in SENSORS:
            if args:
                raise MazeError(f"{name}() doesn't take anything in the ( ).")
            return SENSORS[name]()
        if name == "range":
            if lang == "cpp":
                raise MazeError("there's no range() in C++ — count with a for "
                                "loop:  for (int i = 0; i < 4; i++)")
            raise MazeError("range() only goes inside a for loop, "
                            "like:  for i in range(4):")
        if name in funcs:
            return call_user(funcs[name], args)
        raise MazeError(f"I don't know the command '{name}'. Try move(), "
                        "turn_left(), turn_right(), turn_around(), or a "
                        "function you made with "
                        + ("void." if lang == "cpp" else "def."))

    def exec_block(stmts, scope):
        for node in stmts:
            if isinstance(node, ast.For):
                if not (isinstance(node.iter, ast.Call)
                        and getattr(node.iter.func, "id", None) == "range"):
                    raise MazeError("A for loop must use range(), "
                                    "like:  for i in range(4):")
                if not isinstance(node.target, ast.Name):
                    raise MazeError("Use a simple loop variable, "
                                    "like:  for i in range(4):")
                for val in eval_range(node.iter, scope):
                    tick()
                    scope.set(node.target.id, val)
                    try:
                        exec_block(node.body, scope)
                    except BreakLoop:
                        break
                    except ContinueLoop:
                        continue
            elif isinstance(node, ast.While):
                while truthy(eval_expr(node.test, scope)):
                    tick()  # counts toward MAX_STEPS so a loop can't freeze us
                    try:
                        exec_block(node.body, scope)
                    except BreakLoop:
                        break
                    except ContinueLoop:
                        continue
            elif isinstance(node, CppFor):
                exec_block(node.init, scope)
                while truthy(eval_expr(node.test, scope)):
                    tick()
                    try:
                        exec_block(node.body, scope)
                    except BreakLoop:
                        break
                    except ContinueLoop:
                        pass  # continue still runs the i++ below, like real C++
                    exec_block(node.post, scope)
            elif isinstance(node, ast.If):
                branch = node.body if truthy(eval_expr(node.test, scope)) else node.orelse
                exec_block(branch, scope)
            elif isinstance(node, ast.FunctionDef):
                a = node.args
                if (a.vararg or a.kwarg or a.kwonlyargs or a.defaults
                        or getattr(a, "posonlyargs", None) or node.decorator_list):
                    raise MazeError("Keep functions simple:  def go(a, b):  "
                                    "with no defaults or * arguments.")
                funcs[node.name] = node
            elif isinstance(node, ast.Return):
                raise ReturnValue(eval_expr(node.value, scope)
                                  if node.value is not None else None)
            elif isinstance(node, ast.Assign):
                if not node.targets or any(not isinstance(t, ast.Name)
                                           for t in node.targets):
                    raise MazeError("Assign to a simple name, like:  steps = 3")
                val = eval_expr(node.value, scope)
                for t in node.targets:
                    scope.set(t.id, val)
            elif isinstance(node, ast.AugAssign):
                if not isinstance(node.target, ast.Name):
                    raise MazeError("Assign to a simple name, like:  steps += 1")
                cur = scope.get(node.target.id)
                val = eval_expr(node.value, scope)
                scope.set(node.target.id, int_binop(node.op, cur, val, node.target.id))
            elif isinstance(node, ast.Expr) and isinstance(node.value, ast.Call):
                call_fn(node.value, scope)
            elif isinstance(node, ast.Pass):
                pass
            elif isinstance(node, ast.Break):
                raise BreakLoop()
            elif isinstance(node, ast.Continue):
                raise ContinueLoop()
            else:
                raise MazeError("That line isn't something I can run here.")

    try:
        exec_block(body, global_scope)
    except Solved:
        return {"log": log, "trace": trace}
    except StepLimit:
        log.append("⏹ That ran too long — did a loop repeat too many times?")
        return {"log": log, "trace": trace}
    except (BreakLoop, ContinueLoop):
        log.append("⚠️ break and continue only work inside a loop.")
    except ReturnValue:
        log.append("⚠️ return only works inside a function you made with def.")
    except MazeError as e:
        log.append("⚠️ " + str(e))

    if not log:
        log.append("Type a command and press Run!")
    return {"log": log, "trace": trace}


def scoreboard():
    # Fewer lines is better, so we rank by mazes solved (desc) then lines (asc).
    return sorted(
        ({"name": q["name"], "color": q["color"], "solved": solved_count(q),
          "lines": total_lines(q), "maze": q["maze"] + 1} for q in players.values()),
        key=lambda x: (-x["solved"], x["lines"], x["name"].lower()),
    )


def unlocked_frontier(p):
    """Highest maze index this player may enter: the first one they haven't
    solved yet, OR further if the teacher unlocked ahead from the admin page.
    So mazes 0..frontier are open, everything past it is locked until they beat
    the level in front of it (or a teacher unlocks it for them)."""
    i = 0
    while i in p["best"]:
        i += 1
    return max(i, p.get("unlocked", 0))


def level_scores(mi, limit=5):
    """Code-golf ranking for one maze: who solved it in the fewest lines."""
    rows = [{"name": q["name"], "color": q["color"], "lines": q["best"][mi]}
            for q in players.values() if mi in q["best"]]
    rows.sort(key=lambda x: (x["lines"], x["name"].lower()))
    return rows[:limit]


def overview():
    """Everything the teacher's big screen needs: every student, live."""
    people = []
    for q in players.values():
        people.append({
            "id": q["id"], "name": q["name"], "color": q["color"],
            "maze": q["maze"], "maze_num": q["maze"] + 1,
            "row": q["row"], "col": q["col"], "dir": q["dir"],
            "solved": solved_count(q), "lines": total_lines(q),
            "cleared": cleared(q), "code": q["code"],
        })
    people.sort(key=lambda x: x["name"].lower())
    return {"mazes": MAZES, "maze_count": len(MAZES),
            "players": people, "scoreboard": scoreboard()}


def state_for(p):
    """World as seen by player p: their maze + everyone on that same maze."""
    mi = p["maze"]
    here = [
        {"id": q["id"], "name": q["name"], "color": q["color"],
         "row": q["row"], "col": q["col"], "dir": q["dir"]}
        for q in players.values() if q["maze"] == mi
    ]
    return {
        "maze": MAZES[mi],
        "maze_index": mi,
        "maze_count": len(MAZES),
        "players": here,
        "you": p["id"],
        "you_name": p["name"],     # so a reloaded page can restore its header
        "you_color": p["color"],
        "cleared": cleared(p),
        "is_last": mi + 1 >= len(MAZES),
        "best": p["best"],       # this player's fewest lines per maze solved
        "unlocked": unlocked_frontier(p),   # highest maze index they may enter
        "level_board": level_scores(mi),    # top 5 shortest solutions here
        "scoreboard": scoreboard(),
    }


# ---------------------------------------------------------------------------
# Admin actions.
# ---------------------------------------------------------------------------
def admin_action(data):
    action = data.get("action")
    maze_num = int(data.get("maze", 1) or 1)
    if action == "reset_scores":
        for q in players.values():
            q["maze"] = 0
            q["best"] = {}
            q["unlocked"] = 0
            reset_to_start(q)
        return "All scores reset — everyone back to maze 1."
    if action == "clear":
        players.clear()
        return "All players removed."
    if action == "goto":
        idx = max(0, min(len(MAZES) - 1, maze_num - 1))
        for q in players.values():
            q["maze"] = idx
            reset_to_start(q)
        return f"Everyone sent to maze {idx + 1}."
    if action == "unlock_player":
        q = players.get(data.get("pid"))
        if not q:
            return "No such player."
        idx = max(0, min(len(MAZES) - 1, maze_num - 1))
        q["unlocked"] = max(q.get("unlocked", 0), idx)
        return f"Unlocked maze {idx + 1} for {q['name']}."
    if action == "unlock_all":
        idx = max(0, min(len(MAZES) - 1, maze_num - 1))
        for q in players.values():
            q["unlocked"] = max(q.get("unlocked", 0), idx)
        return f"Unlocked everyone up to maze {idx + 1}."
    return "Unknown action."


# ---------------------------------------------------------------------------
# HTTP handling.
# ---------------------------------------------------------------------------
def load(path):
    with open(path, "rb") as f:
        return f.read()


PAGES = {
    "/": ("game.html", "text/html; charset=utf-8"),
    "/leaderboard": ("leaderboard.html", "text/html; charset=utf-8"),
    "/screen": ("screen.html", "text/html; charset=utf-8"),
    "/admin": ("admin.html", "text/html; charset=utf-8"),
}
STATIC = {p: load(f) for p, (f, _) in PAGES.items()}


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass  # keep the console quiet

    def _send(self, code, body, ctype="application/json"):
        if isinstance(body, (dict, list)):
            body = json.dumps(body).encode()
        elif isinstance(body, str):
            body = body.encode()
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _body(self):
        length = int(self.headers.get("Content-Length", 0))
        if not length:
            return {}
        try:
            return json.loads(self.rfile.read(length))
        except Exception:
            return {}

    def do_GET(self):
        path = self.path.split("?")[0]
        if path in PAGES:
            self._send(200, STATIC[path], PAGES[path][1])
            return
        if path == "/state":
            pid = self.path.split("id=")[-1] if "id=" in self.path else ""
            with lock:
                p = players.get(pid)
                self._send(200, state_for(p) if p else {"error": "join"})
            return
        if path == "/scores":
            with lock:
                self._send(200, {"scoreboard": scoreboard(),
                                 "online": len(players),
                                 "maze_count": len(MAZES)})
            return
        if path == "/overview":
            with lock:
                self._send(200, overview())
            return
        self._send(404, {"error": "not found"})

    def do_POST(self):
        data = self._body()
        if self.path == "/join":
            with lock:
                name = str(data.get("name", "")).strip()
                p = find_player_by_name(name) or new_player(name)
                save_state()
                self._send(200, {"id": p["id"], "name": p["name"], "color": p["color"]})
            return
        if self.path == "/run":
            with lock:
                p = players.get(data.get("id"))
                if not p:
                    self._send(200, {"error": "join"})
                    return
                code = str(data.get("code", ""))
                lang = "cpp" if str(data.get("lang", "")) == "cpp" else "python"
                p["code"] = code[:2000]
                p["lang"] = lang
                out = run_code(p, code, lang)
                save_state()  # persist any new best score and final position
                self._send(200, out)
            return
        if self.path == "/typing":
            with lock:
                p = players.get(data.get("id"))
                if p:
                    p["code"] = str(data.get("code", ""))[:2000]
                self._send(200, {"ok": True})
            return
        if self.path == "/next":
            with lock:
                p = players.get(data.get("id"))
                if not p:
                    self._send(200, {"error": "join"})
                    return
                if not cleared(p):
                    self._send(200, {"error": "Solve this maze first!"})
                elif p["maze"] + 1 < len(MAZES):
                    p["maze"] += 1
                    reset_to_start(p)
                    save_state()
                    self._send(200, {"ok": True, "maze_index": p["maze"]})
                else:
                    self._send(200, {"ok": True, "done": True})
            return
        if self.path == "/goto":
            # Go back to any solved maze to golf it shorter, or forward only as
            # far as you've unlocked by beating the level in front of it.
            with lock:
                p = players.get(data.get("id"))
                if not p:
                    self._send(200, {"error": "join"})
                    return
                idx = data.get("maze")
                if not (isinstance(idx, int) and 0 <= idx < len(MAZES)):
                    self._send(200, {"error": "No such maze."})
                elif idx > unlocked_frontier(p):
                    self._send(200, {"error": "🔒 Solve the earlier levels "
                                     "first to unlock this one."})
                else:
                    p["maze"] = idx
                    reset_to_start(p)
                    save_state()
                    self._send(200, {"ok": True, "maze_index": idx})
            return
        if self.path == "/admin":
            if str(data.get("key", "")) != ADMIN_KEY:
                self._send(200, {"error": "Wrong admin key."})
                return
            with lock:
                msg = admin_action(data)
                save_state()
                self._send(200, {"ok": msg})
            return
        self._send(404, {"error": "not found"})


def get_lan_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


def main():
    load_state()  # bring back the leaderboard and everyone's progress
    ip = get_lan_ip()
    server = ThreadingHTTPServer(("0.0.0.0", PORT), Handler)
    banner = "\n".join([
        "=" * 52,
        "  MAZE CODER is running!",
        "=" * 52,
        f"  Students:     http://{ip}:{PORT}",
        f"  On laptop:    http://localhost:{PORT}",
        "",
        f"  Big screen:   http://localhost:{PORT}/screen        (project this)",
        f"  Leaderboard:  http://localhost:{PORT}/leaderboard",
        f"  Admin panel:  http://localhost:{PORT}/admin",
        f"  Admin key:    {ADMIN_KEY}",
        "=" * 52,
        "  Students must be on the same Wi-Fi. Ctrl+C to stop.",
    ])
    print(banner, flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped. Thanks for playing!")


if __name__ == "__main__":
    main()
