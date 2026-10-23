"""
Python Quest — a classroom coding game.

The main experience is a four-mission, Python-only workspace at `/`.  It uses
an IDE-style editor, a real output console, and a progression from functions to
general algorithms to debugging and exploration.  Bot Rally at `/arena` tests
one program on five tracks.  Light Cycles at `/cycles` is a battle royale where
every student's steer() function rides against the class (cycles.py).  Strange
Planet at `/planet` is a rover in zones that each hide a physics rule
(planet.py).  The original maze ladders remain at `/classic` as optional drills.

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
while, break/continue all work. Scoring counts characters rather than lines
(whitespace and comments are free), so Python and C++ solutions golf fairly
against each other — a C++ one-liner wins nothing on line count alone.

World 5 turns the lights off. Its mazes arrive blank and a student only ever
sees the squares their character has walked past — the server never sends the
rest, so there's no map on the page to read, screenshot, or paste into a chatbot
for an answer. The only way through is to write code that explores in the dark,
look at what it uncovered (it stays uncovered), and plan the route from that.

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
import math
import os
import random
import re
import socket
import threading
import time
import zlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlsplit

import cake
import cycles
import planet

PORT = int(os.environ.get("MAZE_PORT", "8000"))

# Where the leaderboard and everyone's progress is saved, so it survives a
# restart and kids can keep playing day to day.
STATE_FILE = os.environ.get(
    "MAZE_STATE_FILE",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "scores.json"),
)
# Placeholder character score for levels solved before scoring counted
# characters — higher than any real solution, so re-running always beats it.
LEGACY_CHARS = 400

# ---------------------------------------------------------------------------
# Mazes.  '#' = wall, '.' = open, 'S' = start, 'G' = goal (the exit).
# Characters start on S facing right (East). Add or edit mazes freely —
# just keep every row the same width and make sure a path S -> G exists.
#
# Mazes are grouped into WORLDS (see below). Each world is its own ladder of
# levels with its own progress, so a class can start fresh in a new world
# without losing what they did in an old one.
# ---------------------------------------------------------------------------
WORLD1_MAZES = [
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

# ---------------------------------------------------------------------------
# World 2 — The Deep Labyrinth.  Same commands, bigger and twistier: the early
# levels are longer versions of the World 1 patterns (corridor, staircase,
# comb, spiral) so a beginner can still start here, then it turns into real
# dead-end labyrinths that only wall-following solves.
# ---------------------------------------------------------------------------
WORLD2_MAZES = [
    # 1 — long U corridor. move(n), turn, move(n) — a gentle warm-up.
    [
        "#############",
        "#S..........#",
        "###########.#",
        "#G..........#",
        "#############",
    ],
    # 2 — long staircase. One step repeats six times: a for-loop.
    [
        "############",
        "#S.#########",
        "##..########",
        "###..#######",
        "####..######",
        "#####..#####",
        "######..####",
        "#######...G#",
        "############",
    ],
    # 3 — the comb. Up-across-down repeats; loop it, or write a def.
    [
        "#############",
        "#S#...#...#G#",
        "#.#.#.#.#.#.#",
        "#.#.#.#.#.#.#",
        "#.#.#.#.#.#.#",
        "#.#.#.#.#.#.#",
        "#...#...#...#",
        "#############",
    ],
    # 4 — the great spiral. Counting each arm is misery; walk until a wall,
    #     turn, repeat:
    #         while not at_goal():
    #             while not wall_ahead():
    #                 move()
    #             turn_right()
    [
        "#############",
        "#S..........#",
        "###########.#",
        "#.........#.#",
        "#.#######.#.#",
        "#.#.....#.#.#",
        "#.#.###.#.#.#",
        "#.#.#G..#.#.#",
        "#.#.#####.#.#",
        "#.#.......#.#",
        "#.#########.#",
        "#...........#",
        "#############",
    ],
    # 5 — the wide comb. Uneven teeth, so counting breaks down — the
    #     wall-following loop from maze 4 walks it without changes.
    [
        "#################",
        "#S..#...#...#...#",
        "###.#.#.#.#.#.#.#",
        "#...#.#.#.#.#.#.#",
        "#.###.#.#.#.#.#.#",
        "#.....#...#...#G#",
        "#################",
    ],
    # 6 — the big staircase. Two across, two down, five times over. Teach the
    #     character one step with def, then loop it.
    [
        "#############",
        "#S..#########",
        "###.#########",
        "###...#######",
        "#####.#######",
        "#####...#####",
        "#######.#####",
        "#######...###",
        "#########.###",
        "#########...#",
        "###########.#",
        "###########G#",
        "#############",
    ],
    # 7 — the long snake. Straight-lining this takes forever; a loop does it
    #     in a handful of lines.
    [
        "###############",
        "#S............#",
        "#############.#",
        "#.............#",
        "#.#############",
        "#.............#",
        "#############.#",
        "#.............#",
        "#.#############",
        "#.............#",
        "#############.#",
        "#G............#",
        "###############",
    ],
    # 8 — the mirror spiral. Winds the other way, so turn_left() where maze 4
    #     used turn_right(). You start facing a wall — turn first.
    [
        "###############",
        "#S#...........#",
        "#.#.#########.#",
        "#.#.#.......#.#",
        "#.#.#.#####.#.#",
        "#.#.#.#...#.#.#",
        "#.#.#.#.#.#.#.#",
        "#.#.#.#G#.#.#.#",
        "#.#.#.###.#.#.#",
        "#.#.#.....#.#.#",
        "#.#.#######.#.#",
        "#.#.........#.#",
        "#.###########.#",
        "#.............#",
        "###############",
    ],
    # 9 — first true labyrinth. Dead ends everywhere, so counting is hopeless.
    #     Keep your left hand on the wall and you always find the exit:
    #         while not at_goal():
    #             turn_left()
    #             while wall_ahead():
    #                 turn_right()
    #             move()
    [
        "###########",
        "#S#.......#",
        "#.#.###.###",
        "#.#...#...#",
        "#.###.###.#",
        "#...#...#.#",
        "###.#.###.#",
        "#...#.#...#",
        "#.#####.#.#",
        "#.......#G#",
        "###########",
    ],
    # 10 — wider labyrinth. The same left-hand lines from maze 9 walk it.
    [
        "#############",
        "#S#...#.....#",
        "#.#.#.#.#.###",
        "#.#.#.#.#...#",
        "#.#.###.###.#",
        "#.#.......#.#",
        "#.#.#######.#",
        "#.#.#...#...#",
        "#.###.#.#.#.#",
        "#.....#...#G#",
        "#############",
    ],
    # 11 — taller labyrinth. Try to shorten yesterday's solution instead of
    #      rewriting it.
    [
        "#############",
        "#S..#.......#",
        "###.###.###.#",
        "#.#.#...#.#.#",
        "#.#.#.###.#.#",
        "#...#.#.....#",
        "#.###.#######",
        "#.#...#.....#",
        "#.#.###.###.#",
        "#.#.....#...#",
        "#.#######.#.#",
        "#.........#G#",
        "#############",
    ],
    # 12 — long corridors, more forks.
    [
        "###############",
        "#S#...........#",
        "#.#.###.#######",
        "#.#.#.#.......#",
        "#.#.#.#######.#",
        "#.#.#.....#...#",
        "#.#.###.#.#.###",
        "#.#.....#.#...#",
        "#.#######.###.#",
        "#.#...#...#...#",
        "#.#.#.#####.#.#",
        "#...#.......#G#",
        "###############",
    ],
    # 13 — the deep labyrinth.
    [
        "###############",
        "#S#.......#...#",
        "#.#.###.###.#.#",
        "#.#...#.#...#.#",
        "#.#.#.###.###.#",
        "#.#.#...#.#...#",
        "#.#.###.#.#.#.#",
        "#.#...#...#.#.#",
        "#.###.#####.###",
        "#.#...#...#...#",
        "#.###.#.#.###.#",
        "#...#...#.#...#",
        "###.#######.#.#",
        "#...........#G#",
        "###############",
    ],
    # 14 — the grand finale. The biggest labyrinth in the game; the same few
    #      wall-following lines walk the whole thing to the exit.
    [
        "#################",
        "#S#.............#",
        "#.#.#######.###.#",
        "#.#...#...#...#.#",
        "#.###.#.#.#####.#",
        "#...#.#.#.....#.#",
        "###.#.#.#####.#.#",
        "#...#.#...#.....#",
        "#.#####.#.#######",
        "#.....#.#.......#",
        "#####.#.#######.#",
        "#.....#.....#...#",
        "#.###########.#.#",
        "#.............#G#",
        "#################",
    ],
]

# ---------------------------------------------------------------------------
# World 3 — Lost in the Dark.  The hard world: no friendly patterns left to
# count, just real labyrinths that grow level by level.  Every one of these is
# loop-free, so the left-hand rule from World 2 walks all of them — the work is
# writing it once, shortening it, and trusting it on a maze you can't eyeball:
#         while not at_goal():
#             turn_left()
#             while wall_ahead():
#                 turn_right()
#             move()
# ---------------------------------------------------------------------------
WORLD3_MAZES = [
    # 1 — the way in. Dead ends from the first step; nothing to count.
    [
        "#############",
        "#S..#...#...#",
        "###.#.#.#.#.#",
        "#...#.#...#.#",
        "#.###.#####.#",
        "#.#...#...#.#",
        "#.#.###.#.#.#",
        "#.#.#...#G#.#",
        "#.#.#.#####.#",
        "#...#.......#",
        "#############",
    ],
    # 2 — the goal is buried in the middle now, not out on an edge.
    [
        "###############",
        "#S#...#...#...#",
        "#.#.#.#.#.#.#.#",
        "#...#.#.#G#.#.#",
        "#####.#.###.#.#",
        "#.....#.#...#.#",
        "#.#####.#.###.#",
        "#.#...#.....#.#",
        "#.#.#.#######.#",
        "#...#.........#",
        "###############",
    ],
    # 3 — taller. Same few lines; try to shorten them instead of adding more.
    [
        "###############",
        "#S#.......#...#",
        "#.#.#####.#.#.#",
        "#...#.....#.#.#",
        "#####.#####.#.#",
        "#...#.#.....#.#",
        "#.#.#.#.#####.#",
        "#G#.#.#...#...#",
        "###.#.###.#.###",
        "#...#.....#...#",
        "#.###########.#",
        "#.............#",
        "###############",
    ],
    # 4 — wider, and the exit sits behind a long detour.
    [
        "#################",
        "#S#.....#.......#",
        "#.#.###.#.#####.#",
        "#.#.#G..#...#...#",
        "#.#.#######.#.#.#",
        "#.#.......#.#.#.#",
        "#.#######.#.#.#.#",
        "#...#...#...#.#.#",
        "###.#.#.#####.###",
        "#...#.#.#...#...#",
        "#.###.#.#.#.###.#",
        "#.....#...#.....#",
        "#################",
    ],
    # 5 — halfway. Roughly a hundred steps of maze between you and the flag.
    [
        "#################",
        "#S#...#.....#...#",
        "#.#.#.#.###.#.#.#",
        "#.#.#...#...#.#.#",
        "#.#.#####.###.#.#",
        "#.#.#.....#...#.#",
        "#.#.#.###.#.###.#",
        "#.#G#...#.#...#.#",
        "#.###.#.#####.#.#",
        "#...#.#.....#.#.#",
        "###.#####.###.#.#",
        "#...#...#.....#.#",
        "#.###.#.#######.#",
        "#.....#.........#",
        "#################",
    ],
    # 6 — the wide one. Twenty-one columns; you may have to scroll to see it.
    [
        "#####################",
        "#S#....G#...#.......#",
        "#.#.#####.#.#.#####.#",
        "#.#.#.....#.....#...#",
        "#.#.#.###########.###",
        "#.#.#...#.......#...#",
        "#.#.###.#.#####.###.#",
        "#.#.....#.#...#...#.#",
        "#.#.#####.#.#.###.#.#",
        "#.#.#...#.#.#.....#.#",
        "#.###.#.#.#.#######.#",
        "#.....#...#.........#",
        "#####################",
    ],
    # 7 — the exit is three cells from the start, and nowhere near it.
    [
        "###################",
        "#S#...#.....#.....#",
        "#.#.#.#.###.#.###.#",
        "#.#G#.#.#...#.#.#.#",
        "#.###.#.#.###.#.#.#",
        "#...#...#.......#.#",
        "###.#############.#",
        "#...#...........#.#",
        "#.###.#########.#.#",
        "#.....#...#.....#.#",
        "#######.#.#.#####.#",
        "#.#.....#...#...#.#",
        "#.#.#########.#.#.#",
        "#.............#...#",
        "###################",
    ],
    # 8 — a hundred and thirty steps. Watch your run: it's a long walk.
    [
        "###################",
        "#S....#.......#G..#",
        "#####.#.#####.###.#",
        "#...#...#...#.#...#",
        "#.#.#####.#.#.#.###",
        "#.#.......#.#.#...#",
        "#.#######.###.###.#",
        "#.#.#.....#...#...#",
        "#.#.#.#####.###.###",
        "#...#.....#...#...#",
        "###.#####.###.#.#.#",
        "#.#.#...#.#...#.#.#",
        "#.#.#.#.#.#.#####.#",
        "#...#.#.#...#...#.#",
        "#.###.#.#####.#.#.#",
        "#.....#.......#...#",
        "###################",
    ],
    # 9 — the long straight at the top is the only easy part.
    [
        "#####################",
        "#S..................#",
        "###################.#",
        "#.#.........#.......#",
        "#.#.#######.#.#######",
        "#...#.#...#.#.#.....#",
        "#.###.#.#.#.#.###.#.#",
        "#.....#.#...#...#.#G#",
        "#####.#.#######.#.###",
        "#.....#.#.......#...#",
        "#.#####.#.#########.#",
        "#.#...#...#...#...#.#",
        "#.#.#.#####.#.#.#.#.#",
        "#...#.......#...#...#",
        "#####################",
    ],
    # 10 — Lost in the Dark. The biggest labyrinth in the game, and the same
    #      four lines that beat level 1 walk every step of it.
    [
        "#####################",
        "#S..#.......#.......#",
        "###.#.#####.#.#####.#",
        "#...#.#...#...#.....#",
        "#.###.#.#.#####.#####",
        "#...#...#.....#...#.#",
        "###.#####.###.###.#.#",
        "#.#.#...#.#...#.....#",
        "#.#.#.#.###.#######.#",
        "#.#.#.#...#.......#.#",
        "#.#.#.###.#######.#.#",
        "#.#.#.#.........#.#G#",
        "#.#.#.#########.#.###",
        "#...#.......#...#...#",
        "#.#########.#.#####.#",
        "#...........#.......#",
        "#####################",
    ],
]

# World 4 breaks the one-size-fits-all solution. In every maze above, the exit
# touches a wall that connects — however indirectly — to the wall beside your
# start, which is exactly why the left-hand rule walks the whole thing. Here the
# exit is locked in a little wall box standing free in an open courtyard, with
# nothing joining it to the rest of the maze. A hand-on-the-wall bot can circle
# forever and never once touch that box. There is no shortcut left: read the
# map, work out the route to the doorway, and drive yourself there.
WORLD4_MAZES = [
    # 1 — the vault. Your old wall-following lines still run; watch them loop
    #     past the box without ever going in. Now steer there on purpose.
    [
        "#############",
        "#S#...#.....#",
        "#.#.#.#.###.#",
        "#...#.#.#...#",
        "#####.#.#.###",
        "#...#...#.#.#",
        "#.#.#####.#.#",
        "#.#.........#",
        "#.###..###..#",
        "#.#.....G#..#",
        "#.#.##.###.##",
        "#.#.........#",
        "#############",
    ],
    # 2 — find the doorway first, then plan backwards from it.
    [
        "###############",
        "#S....#.......#",
        "#####.#.#####.#",
        "#.#...#...#.#.#",
        "#.#.#####.#.#.#",
        "#.#.#...#...#.#",
        "#.#.#.#.#.....#",
        "#.#...#.#.###.#",
        "#.#####.#..G#.#",
        "#.#...#.#.###.#",
        "#.#.#.#.#.....#",
        "#...#.....#...#",
        "###############",
    ],
    # 3 — the box is tucked low. Count your way down before you count across.
    [
        "###############",
        "#S....#.#.....#",
        "#####.#.#.###.#",
        "#.....#...#...#",
        "#.#######.#.#.#",
        "#.#.....#.#.#.#",
        "#.###.#.#.#.#.#",
        "#.....#.#.#.#.#",
        "#######.#.#.#.#",
        "#...#.......#.#",
        "###.#.#.###.#.#",
        "#...#...#G#.#.#",
        "#.#####.#.#.#.#",
        "#.............#",
        "###############",
    ],
    # 4 — sixty-five steps of maze, and the doorway faces away from you.
    [
        "#################",
        "#S....#.#.....#.#",
        "#####.#.#.#.....#",
        "#.#...#...#.###.#",
        "#.#.###.###.#G..#",
        "#.#...#...#.###.#",
        "#.###.###.#.....#",
        "#...#.#...#.....#",
        "#.#.#.#.###.#####",
        "#.#...#.#.#.....#",
        "#.#####.#.#####.#",
        "#...#.....#...#.#",
        "###.#######.#.#.#",
        "#...........#...#",
        "#################",
    ],
    # 5 — a wide courtyard. Open floor is where wall-following gives up
    #     completely: with no wall to hold, it just spins on the spot.
    [
        "###################",
        "#S#.#...........#.#",
        "#.#.#.#.......#.#.#",
        "#.#.#.#.......#.#.#",
        "#.#.#.#..###..#.#.#",
        "#.#...#..#G.....#.#",
        "#.###.#..###..###.#",
        "#...#.#...........#",
        "###.#.#.......###.#",
        "#.#.#...#.......#.#",
        "#.#.#####.#####.#.#",
        "#.#.....#.....#.#.#",
        "#.#####.#######.#.#",
        "#...............#.#",
        "###################",
    ],
    # 6 — the courtyard is down in the corner this time.
    [
        "###################",
        "#S..#.....#.......#",
        "###.###.###.#####.#",
        "#.#...#.....#.....#",
        "#.###.#####.#.#####",
        "#...#.....#.#.....#",
        "#.#######.#####.#.#",
        "#.......#.....#.#.#",
        "#.......#####.#.#.#",
        "#...........#.#.#.#",
        "#..###..#####.#.#.#",
        "#..#G...#.....#.#.#",
        "#..###..#.#####.#.#",
        "#.......#.#.....#.#",
        "#.......#.#######.#",
        "#...#.............#",
        "###################",
    ],
    # 7 — twenty-one columns. The box is early, but the way in is not.
    [
        "#####################",
        "#S..#...............#",
        "###.#.###.......###.#",
        "#...#.#....###......#",
        "#.###.#.#..#G...###.#",
        "#.#.....#..###....#.#",
        "#.#######.......#.#.#",
        "#.....#...........#.#",
        "#####.#.###.#######.#",
        "#.....#.#...#.......#",
        "#.#####.#.#.#.#######",
        "#.#.....#.#.#.......#",
        "#.#.#####.#.#######.#",
        "#.#.#...#.#.#.......#",
        "#.#.#.#.#.#.#.#######",
        "#...#.#...#.........#",
        "#####################",
    ],
    # 8 — dead centre, and the only door is on the far side of the box.
    [
        "#####################",
        "#S....#.....#.......#",
        "#####.#.###.#.#####.#",
        "#.#...#...........#.#",
        "#.#.#####.......###.#",
        "#...#...#..###..#...#",
        "#.###.#.#..#G#..#.###",
        "#.#...#....#.#..#...#",
        "#.#.#####.......#.#.#",
        "#.#.#...........#.#.#",
        "#.#.###.#######.#.#.#",
        "#.#...#.........#.#.#",
        "#.###.#.###########.#",
        "#.#...#.....#.......#",
        "#.#.#######.#.#####.#",
        "#...#.........#.....#",
        "#####################",
    ],
    # 9 — sixty-one steps. Break it up: get to the courtyard, then to the door.
    [
        "#####################",
        "#S#...#.....#.......#",
        "#.#.#.#.#.#.#.###.###",
        "#...#.#.#.#.#...#...#",
        "#####.###.#.#######.#",
        "#...#.....#.........#",
        "#.#.###############.#",
        "#.#.....#.........#.#",
        "#.#######.###.###.#.#",
        "#.#...........#...#.#",
        "#.#.##.......##.###.#",
        "#...#...#.#...#.#.#.#",
        "#.###...#G#...#.#.#.#",
        "#.#.....###...#...#.#",
        "#.###.........#####.#",
        "#...................#",
        "#####################",
    ],
    # 10 — the Sealed Vault. Longest route in the game to a door two cells wide
    #      of nothing. Nobody pastes their way through this one.
    [
        "#####################",
        "#S#.........#...#...#",
        "#.###.#####.#.#.#.#.#",
        "#...#.....#...#...#.#",
        "###.###############.#",
        "#.#.............#...#",
        "#.#############.#.###",
        "#.............#.#...#",
        "#.#.......###.#.###.#",
        "#.#..#.#......#.#...#",
        "#.#..#G#..###.#.#.#.#",
        "#....###....#.#...#.#",
        "#.#.......#.#.#####.#",
        "#...........#.#...#.#",
        "#####.#.#######.#.#.#",
        "#.....#.........#...#",
        "#####################",
    ],
]

# World 5 turns the lights off. The map arrives blank: you only ever see the
# squares your character has actually stood next to, and what you uncover stays
# uncovered between runs. Nobody can hand this maze to someone else — or to a
# chatbot — because nobody can see it until they walk it. The loop the world
# teaches is EXPLORE, LOOK, then SOLVE: run something that gropes around in the
# dark, study the strip of map it lit up, and write the real route from that.
#
# The three stages of the world:
#   1-3  ordinary labyrinths. Your wall-following lines never needed eyes, so
#        they still walk these blind — a satisfying first win in the dark.
#   4-6  the corridors join back on themselves now. A hand on the wall goes
#        round and round forever, so it maps the maze but never finishes it.
#        Send it in to draw you a map, then drive the route yourself.
#   7-10 the vault returns, unlit. Wall-following can't reach it and you can't
#        see it — the only way through is to explore, read what you uncovered,
#        and plan the way in.
WORLD5_MAZES = [
    # 1 — first steps in the dark. A plain labyrinth: the wall-following lines
    #     from World 2 walk it without seeing a thing.
    [
        "#############",
        "#S#...#.....#",
        "#.#.#.#.#.###",
        "#.#G#...#...#",
        "#.#####.###.#",
        "#.....#...#.#",
        "#####.#####.#",
        "#...........#",
        "#############",
    ],
    # 2 — bigger, still fair. Notice how much of the map one run lights up.
    [
        "#############",
        "#S....#.....#",
        "#####.#####.#",
        "#...#.......#",
        "###.#######.#",
        "#.......#...#",
        "#.#####.#.###",
        "#.#...#G#...#",
        "#.#.#.#####.#",
        "#...#.......#",
        "#############",
    ],
    # 3 — sixty-two steps of pitch black. Last one your old lines beat on their
    #     own; from here they only draw the map.
    [
        "###############",
        "#S#...#...#G..#",
        "#.#.#.#.#.###.#",
        "#...#.#.#...#.#",
        "#####.#.###.#.#",
        "#.....#.#...#.#",
        "#.#####.#.###.#",
        "#...#...#.#...#",
        "###.#.###.#.#.#",
        "#.....#.....#.#",
        "###############",
    ],
    # 4 — the corridors loop. Run your wall-follower and watch it circle until
    #     it runs out of steps — but look what it uncovered on the way.
    [
        "###############",
        "#S..#.........#",
        "###.#.###.##..#",
        "#.#.#.#...#...#",
        "#.#.#.#.#.#.###",
        "#...#.#.#.....#",
        "#.###.#.#####.#",
        "#...#.#.#G..#.#",
        "###.#.#.#.#.#.#",
        "#...#.#.#.....#",
        "#.###.#.#.#####",
        "#.....#.......#",
        "###############",
    ],
    # 5 — more loops. Two runs light up most of it: one to explore, one to win.
    [
        "#################",
        "#S..#.....#.....#",
        "###.#.#.#.#.#...#",
        "#.#.#.#.#.#.#.#.#",
        "#.#.#.#.#.#.#.###",
        "#.#.#..G#...#...#",
        "#...#.###.###.#.#",
        "#.#.#.......#...#",
        "#.#.###.#####.#.#",
        "#.#...#.#...#.#.#",
        "#.##..###.#.#.#.#",
        "#.........#...#.#",
        "#################",
    ],
    # 6 — wide open in places, which is worse: a hand on the wall wanders the
    #     rooms and comes back where it started.
    [
        "#################",
        "#S....#.........#",
        "#####.###.#.#.#.#",
        "#.....#...#..G#.#",
        "#.#####.#.#####.#",
        "#.....#.#.......#",
        "#.#.#.#.#.#######",
        "#.....#.........#",
        "#.###########.#.#",
        "#...#...........#",
        "###.###.###.#.#.#",
        "#.#...#...#...#.#",
        "#.###.##..#####.#",
        "#.........#.....#",
        "#################",
    ],
    # 7 — the vault, unlit. It's boxed off in a courtyard you haven't found yet.
    #     Explore first; there is nothing to solve until you've seen it.
    [
        "###################",
        "#S......#.......#.#",
        "#######.###.###.#.#",
        "#.....#...#...#.#.#",
        "#.#.#####.#.#...#.#",
        "#.#.#.....#.#.#.#.#",
        "#.#...#######.#.#.#",
        "#.#...#...........#",
        "#.#####.###.......#",
        "#.#...#.#....###..#",
        "#.#.#.#.###..#G...#",
        "#...#.#.#....###..#",
        "#####.#.#.#.......#",
        "#.......#.........#",
        "###################",
    ],
    # 8 — find the courtyard, then find the one doorway in the box.
    [
        "###################",
        "#S....#...#.......#",
        "#####.###.#.#.###.#",
        "#.....#...#.#.#...#",
        "#.#.#.#.###...###.#",
        "#.#...#.....#...#.#",
        "#.###.#########.#.#",
        "#...#...#.......#.#",
        "#.#.###.#.#######.#",
        "#.#.#...#.#.......#",
        "#.###.###.#.......#",
        "#.#...#...#..###..#",
        "#....##.###..#G...#",
        "#.#...#.#.#..###..#",
        "#.###.#.#.#.......#",
        "#.......#.........#",
        "###################",
    ],
    # 9 — eighty-eight steps, none of them visible when you start.
    [
        "#####################",
        "#S#.......#.........#",
        "#.#.#####.#######.#.#",
        "#.#...#...#.....#.#.#",
        "#.###.#.###.###.#.#.#",
        "#.#...#.....#.#...#.#",
        "#.#.#########.###.#.#",
        "#.#.......#.....#...#",
        "#.###.#.#.#.#..##.#.#",
        "#...#...#.#.#.......#",
        "###.#####.#.#.......#",
        "#...#...#.#.#..###..#",
        "#.###.#.#.#.#...G#..#",
        "#.....#.#.#.#..###..#",
        "#####.#.#.#.#.......#",
        "#.........#.........#",
        "#####################",
    ],
    # 10 — the Black Vault. Ninety-six steps in the dark to a door you have to
    #      discover before you can aim at it. The last maze in the game.
    [
        "#####################",
        "#S#...#.........#...#",
        "#.#.#.###.#####.#.#.#",
        "#.#.#.....#...#.....#",
        "#.#.#######..######.#",
        "#...#.....#...#...#.#",
        "#####.#.#.#.#.#.#.#.#",
        "#...#.#.....#...#...#",
        "#.###.###############",
        "#.....#...#.........#",
        "#.#####.#.#.#.......#",
        "#.....#.#...#..#.#..#",
        "#####.###.#.#..#G#..#",
        "#...#...#......###..#",
        "#.###.#.####........#",
        "#...................#",
        "#####################",
    ],
]

# The worlds a student can play. Each is an independent ladder of levels with
# its own progress, unlocks and per-level leaderboards.
QUEST_LEVELS = [
    {
        "title": "Pattern Foundry",
        "chapter": "Mission 01",
        "brief": "The assembly line repeats one metal tooth three times. Teach the bot that shape once, then call it in a loop.",
        "objective": "Reach the uplink using a helper function and a for loop.",
        "concepts": ["def", "for", "decomposition"],
        "starter": "def tooth():\n    # Program one repeating section.\n    pass\n\nfor repeat in range(3):\n    tooth()",
    },
    {
        "title": "Search Protocol",
        "chapter": "Mission 02",
        "brief": "A long rescue grid has forks and dead ends. Move counts will not survive it; the bot needs a rule it can repeat at every junction.",
        "objective": "Write a sensor-driven algorithm that navigates the whole labyrinth.",
        "concepts": ["while", "if", "sensors"],
        "starter": "while not at_goal():\n    # Sense the walls, decide, then move.\n    pass",
    },
    {
        "title": "The Sealed Archive",
        "chapter": "Mission 03",
        "brief": "The uplink sits inside a freestanding vault. A simple wall follower circles forever, so split the job into phases and plan the doorway approach.",
        "objective": "Combine a reusable exploration function with a precise vault entry plan.",
        "concepts": ["functions", "state", "debugging"],
        "starter": "def reach_courtyard():\n    # Write a reusable exploration phase.\n    pass\n\ndef enter_vault():\n    # Add the precise final approach.\n    pass\n\nreach_courtyard()\nenter_vault()",
    },
    {
        "title": "Blackout Protocol",
        "chapter": "Mission 04",
        "brief": "No map. One lamp. The vault is somewhere in the dark, and every run keeps the squares you discover. Explore, inspect the evidence, then revise.",
        "objective": "Use code to explore an unknown system, then refine it into a complete solution.",
        "concepts": ["experimentation", "algorithms", "refinement"],
        "starter": "# Start with an exploration algorithm.\n# Use print() to leave yourself debugging notes.\nwhile not at_goal():\n    pass",
    },
]

QUEST_MAZES = [
    WORLD1_MAZES[9],   # a repeating battlement pattern
    WORLD2_MAZES[13],  # the deep labyrinth finale
    WORLD4_MAZES[0],   # a goal inside a freestanding vault
    WORLD5_MAZES[9],   # the same idea, large and dark
]

WORLDS = [
    {"name": "World 1 — Maze Basics",
     "blurb": "Loops, functions and your first sensors.",
     "mazes": WORLD1_MAZES},
    {"name": "World 2 — The Deep Labyrinth",
     "blurb": "Bigger mazes, real dead ends, wall-following.",
     "mazes": WORLD2_MAZES},
    {"name": "World 3 — Lost in the Dark",
     "blurb": "Hard: no patterns to count, only true labyrinths.",
     "mazes": WORLD3_MAZES},
    {"name": "World 4 — The Sealed Vault",
     "blurb": "Hardest: the exit is walled off. Wall-following never gets in.",
     "mazes": WORLD4_MAZES},
    {"name": "World 5 — Blackout",
     "blurb": "The map starts blank. Explore it with code before you can solve it.",
     "mazes": WORLD5_MAZES,
     "fog": True},
    {"name": "Python Quest — Mission Control",
     "blurb": "Four substantial missions: build, generalize, debug, and explore.",
     "mazes": QUEST_MAZES,
     "levels": QUEST_LEVELS,
     "fog_levels": {3}},
]

QUEST_WORLD = len(WORLDS) - 1

# ---------------------------------------------------------------------------
# Bot Rally — one program, five different tracks, three leagues.
#
# This is deliberately separate from the normal world ladder. A route made of
# hard-coded move counts may win one trial, but only a real navigation
# algorithm can clear a whole league. Each league is built to defeat the
# previous league's easy answer (checked by test_server.py):
#   Rookie  — any sensor loop clears it; the plain wall follower does.
#   Pro     — the plain wall follower still clears it but earns no par stars;
#             mirrored tracks punish always using the same hand.
#   Expert  — the goal sits inside a vault: every wall follower circles
#             forever, and simply walking toward the goal gets stuck.
# Clearing every track in a league (Gold) unlocks the next one.
# ---------------------------------------------------------------------------
def mirror(maze):
    return [row[::-1] for row in maze]


def rally_track(name, maze, mirrored=False):
    # A mirrored track also starts facing West, so it's an exact mirror image:
    # whatever the right hand does on the original, the left does here.
    return {"name": name, "maze": mirror(maze) if mirrored else maze,
            "dir": 3 if mirrored else 1}


RALLY_LEAGUES = [
    {"key": "rookie", "name": "Rookie League",
     "blurb": "Five short tracks. Any loop that uses sensors can clear them.",
     "tracks": [
         rally_track("Corner Dash", WORLD1_MAZES[1]),
         rally_track("Switchback", WORLD1_MAZES[2]),
         rally_track("Spiral Run", WORLD1_MAZES[6]),
         rally_track("Branch Lab", WORLD1_MAZES[7]),
         rally_track("Final Circuit", WORLD1_MAZES[11]),
     ],
     "hints": [
         "Numbers only work on one route you already know. Sensors let your "
         "bot decide for itself. Try an if with wall_ahead().",
         "Your bot should repeat its decision until it arrives. A useful "
         "outer shape is:  while not at_goal():",
         "Pretend the bot keeps its right hand on the wall: check right first, "
         "turn away from walls, then move.\n\nwhile not at_goal():\n"
         "    if not wall_right():\n        turn_right()\n    ...",
     ]},
    {"key": "pro", "name": "Pro League",
     "blurb": "Bigger labyrinths, two of them mirrored. Clearing them is "
              "the easy part — beat par for the stars.",
     "tracks": [
         rally_track("Twin Forks", WORLD2_MAZES[9]),
         rally_track("Looking Glass", WORLD2_MAZES[11], mirrored=True),
         rally_track("Long Hall", WORLD2_MAZES[13]),
         rally_track("Long Hall, Mirrored", WORLD2_MAZES[13], mirrored=True),
         rally_track("Back Alley", WORLD3_MAZES[1], mirrored=True),
     ],
     "hints": [
         "Turning just to look at a wall costs an action. wall_right() and "
         "wall_left() check without turning.",
         "The right hand is perfect on some tracks and terrible on their "
         "mirror image. Could the bot choose which hand to use before it "
         "starts, using a goal sensor?",
         "Decide once, then follow that hand:\n\nuse_right = goal_right()\n"
         "while not at_goal():\n    if use_right:\n        ...\n    else:\n"
         "        ...",
     ]},
    {"key": "expert", "name": "Expert League",
     "blurb": "Each goal is locked in a vault in the middle. Wall followers "
              "circle it forever. You'll need a new idea.",
     "tracks": [
         rally_track("Vault Door", WORLD4_MAZES[5]),
         rally_track("Mirror Vault", WORLD4_MAZES[6], mirrored=True),
         rally_track("Courtyard", WORLD4_MAZES[8]),
         rally_track("Night Garden", WORLD5_MAZES[6]),
         rally_track("Deep Mirror", WORLD5_MAZES[7], mirrored=True),
     ],
     "hints": [
         "A wall follower never leaves the outer wall, so it never reaches a "
         "vault in the middle. What else could the bot pay attention to?",
         "Robots use the Bug algorithm: head toward the goal "
         "(goal_ahead/left/right). When blocked, follow the wall until "
         "distance_to_goal() is smaller than when you got stuck, then head "
         "for the goal again.",
         "while not at_goal():\n    if goal_ahead() and not wall_ahead():\n"
         "        move()\n    # ...turn toward the goal if you can...\n"
         "    else:\n        stuck_at = distance_to_goal()\n"
         "        # follow the wall while distance_to_goal() >= stuck_at",
     ]},
]
# Par is the fewest moves + turns that reach the goal, plus this much slack.
PAR_SLACK = 1.25

# Everyone joining today starts here (0 = World 1, 1 = World 2, …).
DEFAULT_WORLD = QUEST_WORLD


def mazes_of(p):
    """The maze list of the world this player is currently in."""
    # Rally runners use a tiny throw-away player with one injected maze. That
    # lets the battle-tested safe interpreter run tournament code without
    # changing the student's campaign position or scores.
    if "_arena_maze" in p:
        return [p["_arena_maze"]]
    return WORLDS[p["world"]]["mazes"]


def bkey(wi, mi):
    """Key used in a player's `best` dict — progress is tracked per world."""
    return f"{wi}:{mi}"


# Direction vectors, indexed 0=North,1=East,2=South,3=West.
DIRS = [(-1, 0), (0, 1), (1, 0), (0, -1)]
DIR_ARROWS = ["▲", "▶", "▼", "◀"]

COLORS = [
    "#e6194b", "#3cb44b", "#4363d8", "#f58231", "#911eb4",
    "#42d4f4", "#f032e6", "#bfef45", "#fabed4", "#469990",
    "#9a6324", "#800000", "#808000", "#000075", "#e6beff",
]

# Cap per Run so a runaway loop can't freeze the game. Every move AND every
# loop iteration counts, so wall-following the biggest World 2 labyrinth burns
# roughly 700 — keep plenty of headroom above that.
MAX_STEPS = 2000
MAX_INT = 10 ** 9      # biggest number math may produce

# Fog of war (World 5). The character carries a lamp: standing anywhere lights
# the eight squares touching it, and shines down the corridor it faces until
# something blocks the beam. What's been lit stays lit — a run that crashes into
# a wall or spins until the step limit still leaves its map behind, so groping
# around in the dark is never wasted.
FOG_BEAM = 6           # how far the lamp reaches along the way you're facing
FOG_HIDDEN = "?"       # what an unlit square looks like to the browser

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


def min_actions(maze, start_dir):
    """Fewest moves + turns from the start to the goal (a turn_around() is one
    action, like in the replay)."""
    start = (find_start(maze), start_dir)
    dist = {start: 0}
    queue = [start]
    for (r, c), d in queue:
        if maze[r][c] == "G":
            return dist[((r, c), d)]
        dr, dc = DIRS[d]
        steps = [((r, c), (d + t) % 4) for t in (1, 2, 3)]
        if maze[r + dr][c + dc] != "#":
            steps.append(((r + dr, c + dc), d))
        for nxt in steps:
            if nxt not in dist:
                dist[nxt] = dist[((r, c), d)] + 1
                queue.append(nxt)
    return None


for _league in RALLY_LEAGUES:
    for _track in _league["tracks"]:
        _track["par"] = math.ceil(min_actions(_track["maze"], _track["dir"])
                                  * PAR_SLACK)


def is_fogged(wi, mi=None):
    world = WORLDS[wi]
    return bool(world.get("fog") or
                (mi is not None and mi in world.get("fog_levels", set())))


def seen_set(p, wi, mi):
    """The squares this player has lit in one maze, as {(row, col)}. On disk
    they're "r,c" strings, because the player dict is saved to scores.json."""
    cells = p.setdefault("seen", {}).get(bkey(wi, mi), [])
    out = set()
    for cell in cells:
        r, _, c = str(cell).partition(",")
        if r.isdigit() and c.isdigit():
            out.add((int(r), int(c)))
    return out


def light_up(p, maze, seen):
    """Shine the lamp from where p is standing. Adds to `seen` and returns the
    squares newly lit, as (row, col, character) for the browser to paint in."""
    fresh = []

    def light(r, c):
        if 0 <= r < len(maze) and 0 <= c < len(maze[0]) and (r, c) not in seen:
            seen.add((r, c))
            fresh.append([r, c, maze[r][c]])

    for dr in (-1, 0, 1):           # everything you can touch
        for dc in (-1, 0, 1):
            light(p["row"] + dr, p["col"] + dc)
    dr, dc = DIRS[p["dir"]]         # plus the beam, until a wall stops it
    r, c = p["row"], p["col"]
    for _ in range(FOG_BEAM):
        r, c = r + dr, c + dc
        if not (0 <= r < len(maze) and 0 <= c < len(maze[0])):
            break
        light(r, c)
        if maze[r][c] == "#":
            break
    return fresh


def save_seen(p, wi, mi, seen):
    p.setdefault("seen", {})[bkey(wi, mi)] = [f"{r},{c}" for r, c in seen]


def fog_maze(maze, seen):
    """The maze as this player has actually seen it — everything else blank.
    The goal always shows through the dark, so groping around has a direction
    to grope in; only the way there is hidden."""
    return ["".join(ch if ch == "G" or (r, c) in seen else FOG_HIDDEN
                    for c, ch in enumerate(row))
            for r, row in enumerate(maze)]


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
                       "admin_key": ADMIN_KEY, "cycles_round": cycles_round}, f)
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
        # Saves from before worlds existed keyed `best` by maze number alone
        # and had a single `unlocked` number; fold those into World 1.
        best = p.get("best", {})
        p["best"] = {(k if ":" in str(k) else bkey(0, int(k))): v
                     for k, v in best.items()}
        p.setdefault("world", 0)
        unlocked = p.get("unlocked", 0)
        p["unlocked"] = unlocked if isinstance(unlocked, dict) else {"0": unlocked}
        p.setdefault("seen", {})   # fogged worlds arrived after some saves did
        # Bot Rally had a single track set before leagues; that set is now the
        # Rookie League, so carry its best run and code over.
        if "arena_best" in p or "arena_code" in p:
            p.setdefault("rally", {}).setdefault("rookie", {
                "best": p.pop("arena_best", None),
                "code": p.pop("arena_code", ""), "hints": 0})
        # Character scores arrived after some saves did. Levels solved before
        # then get a flat placeholder bigger than any real solution, so those
        # solves still count — and the first re-run of the level always
        # replaces it with the student's real character count.
        chars = p.get("chars", {})
        p["chars"] = {k: chars.get(k, LEGACY_CHARS) for k in p["best"]}
        players[pid] = p
    next_player_num[0] = data.get("next", len(players))
    # The Light Cycles round number and last replay arrived after some saves.
    saved_round = data.get("cycles_round") or {}
    cycles_round["number"] = int(saved_round.get("number", 0) or 0)
    cycles_round["last"] = saved_round.get("last") or None
    # Reuse the same admin key across restarts so an open admin page keeps
    # working; fall back to this run's freshly generated one if none was saved.
    ADMIN_KEY = data.get("admin_key") or ADMIN_KEY


def new_player(name):
    pid = f"p{next_player_num[0]}"
    next_player_num[0] += 1
    color = COLORS[len(players) % len(COLORS)]
    sr, sc = find_start(WORLDS[DEFAULT_WORLD]["mazes"][0])
    players[pid] = {
        "id": pid,
        "name": name[:20] or f"Player{pid}",
        "color": color,
        "world": DEFAULT_WORLD,
        "maze": 0,
        "row": sr,
        "col": sc,
        "dir": 1,          # facing East
        "best": {},        # "world:maze" -> lines of their shortest solution
        "chars": {},       # "world:maze" -> fewest characters that solved it
        "unlocked": {},    # "world" -> highest maze the teacher unlocked by hand
        "seen": {},        # "world:maze" -> squares lit so far in a fogged maze
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


def total_chars(p):
    return sum(p["chars"].values())


def cleared(p):
    return bkey(p["world"], p["maze"]) in p["best"]


def solved_in_world(p, wi):
    prefix = f"{wi}:"
    return sum(1 for k in p["best"] if str(k).startswith(prefix))


def reset_to_start(p):
    sr, sc = find_start(mazes_of(p)[p["maze"]])
    # Mirrored rally tracks start facing West so they're a true mirror image.
    p["row"], p["col"], p["dir"] = sr, sc, p.get("_arena_dir", 1)


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


def count_chars(code, lang):
    """Score a program by size: non-whitespace characters, comments free.
    Lines mean little in C++ (a whole solution fits on one), so this is what
    the leaderboard actually ranks on. Whitespace is free in both languages so
    Python indentation and readable spacing never cost anything."""
    if lang == "cpp":
        code = CPP_BLOCK_COMMENT.sub("", code)
        code = "\n".join(l.split("//")[0] for l in code.splitlines())
    else:
        code = "\n".join(l for l in code.splitlines()
                         if not l.strip().startswith("#"))
    return len(re.sub(r"\s", "", code))


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
    n_chars = count_chars(code, lang)

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
    maze = mazes_of(p)[p["maze"]]
    steps = [0]

    # In a fogged world the lamp lights squares as the character walks, and each
    # frame carries the ones it just lit so the browser can uncover them live.
    fog = is_fogged(p["world"], p["maze"])
    seen = seen_set(p, p["world"], p["maze"]) if fog else set()
    lit_before = len(seen)

    def lamp():
        return light_up(p, maze, seen) if fog else []

    # Snapshot of position/facing after every move/turn, so the frontend can
    # animate the character walking the path instead of jumping to the end.
    trace = [{"row": p["row"], "col": p["col"], "dir": p["dir"], "lit": lamp()}]
    visited = {(p["row"], p["col"])}   # squares stood on this run

    def snapshot():
        trace.append({"row": p["row"], "col": p["col"], "dir": p["dir"],
                      "lit": lamp()})
        visited.add((p["row"], p["col"]))

    class Solved(Exception):
        pass

    class StepLimit(Exception):
        pass

    def tick():
        steps[0] += 1
        if steps[0] > MAX_STEPS:
            raise StepLimit()

    def solve():
        idx = bkey(p["world"], p["maze"])
        prev = p["chars"].get(idx)
        if prev is None or n_chars < prev:
            p["chars"][idx] = n_chars
            p["best"][idx] = n_lines   # the lines that came with the record run
        if "_arena_maze" in p:
            # The rally page shows actions and par itself.
            log.append("🎉 Reached the goal!")
            return
        quest = p["world"] == QUEST_WORLD
        if prev is None:
            log.append(f"🎉 {'Mission complete' if quest else 'You reached the exit'} "
                       f"in {n_chars} characters ({n_lines} line(s))!")
            log.append("   Review what worked, then open the next mission."
                       if quest else
                       "   Press ▶ Next Maze to move on — or shorten your "
                       "code first to climb the leaderboard.")
        elif n_chars < prev:
            log.append(f"✅ New best: {n_chars} characters (was {prev})! "
                       "Nice optimizing.")
            log.append("   Your mission is still complete; keep refining or move on."
                       if quest else
                       "   Press ▶ Next Maze when you're happy with it.")
        else:
            log.append(f"🎉 {'Mission complete' if quest else 'Reached the exit'} "
                       f"in {n_chars} characters. "
                       f"Your best here is {p['chars'][idx]}.")
            log.append("   Open the next mission, or keep experimenting here."
                       if quest else
                       "   Press ▶ Next Maze to continue, or keep shortening.")

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
        # The missions and the rally replay every turn on the map, so only the
        # classic maze library spells them out in the log.
        if p["world"] != QUEST_WORLD and "_arena_maze" not in p:
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

    if "_arena_maze" in p:
        # Bot Rally gets extra sensors so students can invent their own
        # algorithms. The missions keep the three above.
        goal = next((r, c) for r, row in enumerate(maze)
                    for c, ch in enumerate(row) if ch == "G")

        def wall_on(turn):
            dr, dc = DIRS[(p["dir"] + turn) % 4]
            return maze[p["row"] + dr][p["col"] + dc] == "#"

        def goal_side(turn):
            # Positive when the goal lies some distance that way (0 = ahead,
            # 1 = right, -1 = left) from where the bot stands and faces.
            dr, dc = DIRS[(p["dir"] + turn) % 4]
            return (goal[0] - p["row"]) * dr + (goal[1] - p["col"]) * dc > 0

        def visited_ahead():
            dr, dc = DIRS[p["dir"]]
            return (p["row"] + dr, p["col"] + dc) in visited

        SENSORS.update({
            "wall_left": lambda: wall_on(-1),
            "wall_right": lambda: wall_on(1),
            "goal_ahead": lambda: goal_side(0),
            "goal_left": lambda: goal_side(-1),
            "goal_right": lambda: goal_side(1),
            "distance_to_goal": lambda: (abs(goal[0] - p["row"])
                                         + abs(goal[1] - p["col"])),
            "visited_ahead": visited_ahead,
        })

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
        result = raw_binop(op, require_int(a, what), require_int(b, what))
        # Huge numbers get slow to multiply, and this runs while holding the
        # lock — so  x *= x  in a loop would freeze the whole class.
        if abs(result) > MAX_INT:
            raise MazeError("That number got too big. Keep math under a billion.")
        return result

    def raw_binop(op, a, b):
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
            raise MazeError("Compare like with like: numbers with numbers or text with text.")
        raise MazeError("That comparison isn't allowed. Use  <  <=  >  >=  ==  !=")

    def eval_expr(node, scope):
        """Work out the value (a number or True/False) of an expression."""
        if isinstance(node, ast.Constant):
            if isinstance(node.value, (int, bool)):
                return node.value
            if isinstance(node.value, str) and len(node.value) <= 200:
                return node.value
            raise MazeError("Use whole numbers, short text, or True/False here.")
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
        if name == "print":
            if len(args) > 4:
                raise MazeError("print() can show up to four things at once.")
            log.append("› " + " ".join(str(value) for value in args))
            return None
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
        raise MazeError(f"I don't know the command '{name}'. Try move(), print(), "
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

    def done(solved=False):
        """Hand back the run — and in a fogged world keep whatever the lamp lit,
        even if the program crashed or looped forever. Exploring always pays."""
        if fog:
            save_seen(p, p["world"], p["maze"], seen)
            fresh = len(seen) - lit_before
            if not solved:
                log.append(f"🔦 Lit {fresh} new square(s) — {len(seen)} of the "
                           f"map uncovered so far. What you found stays found."
                           if fresh else
                           "🔦 Nothing new in the dark that time — try steering "
                           "somewhere you haven't been.")
        return {"log": log, "trace": trace}

    try:
        exec_block(body, global_scope)
    except Solved:
        return done(solved=True)
    except StepLimit:
        log.append("⏹ That ran too long — did a loop repeat too many times?")
        return done()
    except (BreakLoop, ContinueLoop):
        log.append("⚠️ break and continue only work inside a loop.")
    except ReturnValue:
        log.append("⚠️ return only works inside a function you made with def.")
    except MazeError as e:
        log.append("⚠️ " + str(e))
    except RecursionError:
        log.append("⚠️ That line is too deeply nested for me to follow — "
                   "try splitting it up.")

    if not log:
        log.append("Type a command and press Run!")
    return done()


def scoreboard():
    # Shorter code is better, so we rank by mazes solved (desc) then total
    # characters (asc). Lines come along for display only — in C++ everything
    # fits on one line, so they can't decide anything.
    return sorted(
        ({"name": q["name"], "color": q["color"], "solved": solved_count(q),
          "chars": total_chars(q), "lines": total_lines(q), "maze": q["maze"] + 1,
          "world": q["world"] + 1} for q in players.values()),
        key=lambda x: (-x["solved"], x["chars"], x["name"].lower()),
    )


def _arena_rank(score):
    """Lower tuple wins: clear more tracks, then earn more par stars, then use
    fewer actions and chars."""
    return (-score["solved"], -score.get("stars", 0), score["actions"],
            score["chars"], score.get("lines", 0))


def rally_league(key):
    return next((lg for lg in RALLY_LEAGUES if lg["key"] == key), None)


def rally_entry(p, key):
    """This player's saved code, best run and opened hints for one league."""
    return p.setdefault("rally", {}).setdefault(
        key, {"best": None, "code": "", "hints": 0})


def rally_gold(p, key):
    best = rally_entry(p, key)["best"]
    return bool(best) and best["solved"] == len(rally_league(key)["tracks"])


def rally_unlocked(p, index):
    """Rookie is always open. Each later league opens with Gold in the one
    before it, or when the teacher unlocks it from the admin page."""
    return (index == 0 or index <= p.get("rally_unlocked", 0)
            or rally_gold(p, RALLY_LEAGUES[index - 1]["key"]))


def rally_hints_used(p):
    return sum(entry.get("hints", 0) for entry in p.get("rally", {}).values())


def arena_scoreboard(key="rookie", limit=12):
    total = len(rally_league(key)["tracks"])
    rows = []
    for p in players.values():
        best = p.get("rally", {}).get(key, {}).get("best")
        if best:
            rows.append({
                "name": p["name"], "color": p["color"],
                "solved": best["solved"], "total": total,
                "stars": best.get("stars", 0),
                "actions": best["actions"], "chars": best["chars"],
                "lines": best.get("lines", 0),
                # Gold reached without opening a single hint in this league.
                "no_hints": best["solved"] == total and best.get("hints", 0) == 0,
            })
    rows.sort(key=lambda x: (_arena_rank(x), x["name"].lower()))
    return rows[:limit]


def run_arena(p, code, key="rookie"):
    """Test one Python program on every track of a league without touching
    the campaign.

    A student's best result per league is persistent. Ranking is
    lexicographic: cleared tracks first, then par stars, then actions taken
    on the cleared tracks, then program size. That gives beginners credit for
    partial progress and gives experts a real efficiency contest at 5/5.
    """
    league = rally_league(key)
    code = str(code)[:4000]
    entry = rally_entry(p, key)
    results = []
    solved_actions = 0

    for track in league["tracks"]:
        maze = track["maze"]
        sr, sc = find_start(maze)
        runner = {
            "id": "arena", "name": p["name"], "color": p["color"],
            "world": 0, "maze": 0, "row": sr, "col": sc, "dir": track["dir"],
            "best": {}, "chars": {}, "unlocked": {}, "seen": {},
            "code": code, "_arena_maze": maze, "_arena_dir": track["dir"],
        }
        out = run_code(runner, code, "python")
        solved = bkey(0, 0) in runner["best"]
        actions = max(0, len(out["trace"]) - 1)
        # The rally UI replays every track. Send each frame as a bare
        # [row, col, dir] so a 2,000-step trace stays small on classroom Wi-Fi.
        trace = [[f["row"], f["col"], f["dir"]] for f in out["trace"]]
        last = (out["trace"][-1] if out["trace"] else
                {"row": runner["row"], "col": runner["col"]})
        if solved:
            solved_actions += actions
        results.append({
            "name": track["name"], "maze": maze, "solved": solved,
            "actions": actions, "par": track["par"],
            "star": solved and actions <= track["par"], "trace": trace,
            "final": {"row": last["row"], "col": last["col"]},
            # Keep the student's print() lines (up to 40) so debugging notes
            # aren't pushed out by moves, plus the last lines of the run.
            "log": ([line for line in out["log"][:-12] if line.startswith("› ")][-40:]
                    + out["log"][-12:]),
        })

    candidate = {
        "solved": sum(1 for r in results if r["solved"]),
        "stars": sum(1 for r in results if r["star"]),
        "actions": solved_actions,
        "chars": count_chars(code, "python"),
        "lines": count_lines(code, "python"),
        "hints": entry["hints"],
        "code": code,
    }
    previous = entry["best"]
    is_best = previous is None or _arena_rank(candidate) < _arena_rank(previous)
    if is_best:
        entry["best"] = candidate
    entry["code"] = code

    return {
        "results": results, "score": candidate,
        "best": entry["best"], "new_best": is_best,
        "leaderboard": arena_scoreboard(key),
        "leagues": rally_summary(p),
    }


def rally_summary(p):
    """Every league as this player sees it: open or locked, and their best."""
    return [{"key": lg["key"], "name": lg["name"], "blurb": lg["blurb"],
             "tracks": len(lg["tracks"]), "unlocked": rally_unlocked(p, i),
             "best": rally_entry(p, lg["key"])["best"]}
            for i, lg in enumerate(RALLY_LEAGUES)]


def rally_state(p, key):
    """What the rally page needs for one league. Track names stay sealed until
    the player's first run there; hints are only sent once opened."""
    league = rally_league(key)
    entry = rally_entry(p, key)
    return {
        "you": {"name": p["name"], "color": p["color"]},
        "league": key,
        "leagues": rally_summary(p),
        "code": entry["code"],
        "best": entry["best"],
        "hints": league["hints"][:entry["hints"]],
        "hint_count": len(league["hints"]),
        "leaderboard": arena_scoreboard(key),
        "trial_count": len(league["tracks"]),
    }


def open_rally_hint(p, key):
    league = rally_league(key)
    entry = rally_entry(p, key)
    entry["hints"] = min(len(league["hints"]), entry["hints"] + 1)
    return league["hints"][:entry["hints"]]


# ---------------------------------------------------------------------------
# Light Cycles (/cycles): every student's steer() in one Tron-style battle
# royale. The game itself lives in cycles.py; this is the classroom side —
# saved bots, practice heats against the house bots, and season points.
# ---------------------------------------------------------------------------
cycles_round = {"number": 0, "last": None}   # the last battle, for replays
cycles_battle_lock = threading.Lock()

# Light Cycles has its own colours: bright on the dark arena (#0b111e, every
# one at least 5:1 contrast) and as different from each other and from the
# house bots as 24 colours can be (closest pair ~14 CIEDE2000). The first
# ones differ most, so small classes get the clearest set.
CYCLE_COLORS = [
    "#34b26f", "#cb3dff", "#d46c11", "#2be1ee", "#f9b8f9", "#94ff1a",
    "#ffc2b2", "#c4eec4", "#99b234", "#3499b2", "#d369a9", "#9988dd",
    "#c4ccee", "#ff291a", "#b29034", "#1affa3", "#ffad66", "#f4e2be",
    "#b8e4f9", "#e5e600", "#34b2a9", "#eea0b5", "#1ac2ff", "#ff8566",
]


def cycles_entry(p):
    entry = p.setdefault("cycles", {"code": "", "best": None, "points": 0,
                                    "rounds": 0, "wins": 0})
    # "code" is the bot entered for the next battle; "tested" is whatever
    # the student test-drove last (it goes back in their editor). Saves from
    # before this kept only "code", which was always entered.
    for key, value in (("tested", entry["code"]), ("entered_at", None),
                       ("ok", True), ("error", None), ("kept_previous", False)):
        entry.setdefault(key, value)
    return entry


def cycles_color(p):
    """The student's own Light Cycles colour: the first one nobody has yet."""
    entry = cycles_entry(p)
    if "color" not in entry:
        used = [q["cycles"]["color"] for q in players.values()
                if "color" in q.get("cycles", {})]
        entry["color"] = next((c for c in CYCLE_COLORS if c not in used),
                              CYCLE_COLORS[len(used) % len(CYCLE_COLORS)])
    return entry["color"]


def cycles_entry_status(entry):
    return {k: entry[k] for k in ("code", "entered_at", "ok", "error",
                                  "kept_previous")}


def cycles_board():
    rows = [{**cycles_entry(p), "name": p["name"], "color": cycles_color(p)}
            for p in players.values() if cycles_entry(p)["code"].strip()]
    rows.sort(key=lambda x: (-x["points"], -x["wins"], x["name"].lower()))
    return [{k: row[k] for k in ("name", "color", "points", "rounds", "wins")}
            for row in rows]


def cycles_test(p, code, heats=None):
    """Race the student's bot against the house bots in every practice heat.
    The code they test is the bot they'll enter in the next battle. The
    server races the heats before taking the lock and passes them in."""
    code = str(code)[:cycles.MAX_CODE + 1]   # one more, so it can say "too long"
    entry = cycles_entry(p)
    heats = heats or cycles.practice(code, p["name"], cycles_color(p))
    # Code that can't even start (a syntax error, a crash at the top, no
    # steer()) never replaces a bot that works: breaking your code just
    # before a round shouldn't enter a cycle that crashes on the start line.
    error = next((h["bikes"][0]["cause"].replace("💥 code error: ", "")
                  for h in heats if h["bikes"][0]["died"] == 0), None)
    entry["tested"] = code
    if error and entry["ok"] and entry["code"].strip():
        entry.update(error=error, kept_previous=True)
    else:
        entry.update(code=code, entered_at=int(time.time()), ok=error is None,
                     error=error, kept_previous=False)
    places = [h["bikes"][0]["place"] for h in heats]
    lasted = [h["turns"] if h["bikes"][0]["died"] is None
              else h["bikes"][0]["died"] for h in heats]
    score = {"wins": places.count(1), "places": places, "lasted": lasted,
             "turns": sum(lasted)}
    best = entry["best"]
    new_best = best is None or (score["wins"], -sum(places), score["turns"]) > \
        (best["wins"], -sum(best["places"]), best["turns"])
    if new_best:
        entry["best"] = score
    for h in heats:
        for bike in h["bikes"][1:]:
            bike["prints"] = []   # the house bots' notes are just noise
    return {"heats": heats, "score": score, "best": entry["best"],
            "new_best": new_best, "board": cycles_board(),
            "entry": cycles_entry_status(entry)}


def cycles_battle():
    """Every student with a saved bot, one arena, last cycle riding wins.
    Each student scores a point for every cycle they outlast. The race runs
    outside `lock` so the rest of the class isn't frozen while it does, and
    only one battle runs at a time."""
    if not cycles_battle_lock.acquire(blocking=False):
        return {"error": "A round is already running — wait for it to finish."}
    try:
        with lock:
            racers = [p for p in players.values()
                      if cycles_entry(p)["code"].strip()]
            entries = []
            for p in racers:
                # Keep everyone's own colour, unless someone in this race
                # already has it: then the first colour still free.
                taken = [e["color"] for e in entries]
                color = cycles_color(p)
                if color in taken:
                    color = next((c for c in CYCLE_COLORS if c not in taken), color)
                entries.append({"key": p["id"], "name": p["name"], "color": color,
                                "code": cycles_entry(p)["code"]})
        if not racers:
            return {"error": "No bots entered yet. Students enter by pressing "
                             "Test drive on /cycles."}
        grid, starts = cycles.royale_arena(len(racers), random.randrange(10 ** 6))
        result = cycles.run_match(entries, grid, starts)
        with lock:
            for p, bike in zip(racers, result["bikes"]):
                entry = cycles_entry(p)
                entry["points"] += bike["outlasted"]
                entry["rounds"] += 1
                if bike["place"] == 1 and len(racers) > 1:
                    entry["wins"] += 1
            cycles_round["number"] += 1
            result["round"] = cycles_round["number"]
            cycles_round["last"] = result
            return cycles_replay(None)
    finally:
        cycles_battle_lock.release()


def cycles_replay(p):
    """The last battle, with only this student's own print() output."""
    last = cycles_round["last"]
    if not last:
        return {"replay": None, "board": cycles_board()}
    bikes = [dict(b, prints=b["prints"] if p and b["key"] == p["id"] else [])
             for b in last["bikes"]]
    return {"replay": dict(last, bikes=bikes), "board": cycles_board()}


def cycles_summary(p):
    """For the admin page: the student's best test drive and whether the bot
    entered for the next battle works. None until their first test drive."""
    entry = p.get("cycles")   # read only: don't start an entry for them
    if not entry or not entry["code"].strip():
        return None
    return {"best": entry["best"], "points": entry["points"],
            "color": entry.get("color"), "ok": entry.get("ok", True),
            "kept_previous": entry.get("kept_previous", False)}


def cycles_state(p):
    entry = cycles_entry(p)
    return {"you": {"name": p["name"], "color": cycles_color(p)},
            "code": entry["tested"], "best": entry["best"],
            "points": entry["points"], "board": cycles_board(),
            "round": cycles_round["number"],
            "entry": cycles_entry_status(entry)}


# ---------------------------------------------------------------------------
# Strange Planet (/planet): every zone hides one physics rule. The planets live
# in planet.py; this is the classroom side — progress, stars, badges, the rover
# garage, class records and the class star meter, hints and field journals,
# and the teacher's overview at /planet/teacher.
#
# Every reward is for coding: stars for reaching, for a site's challenge and
# for compact code; badges for first loops, functions, fixed bugs and grit.
# Nothing is random and nothing is taken away.
# ---------------------------------------------------------------------------
JOURNAL_MAX = 140   # characters in one field journal note
SCOUT_MAX = 60      # hand-driven moves in one scouting trip
planet_feed = []    # the class's recent moments, newest last, for the projector

# Badges: (icon, name, how to earn it). Zone masters are added below.
PLANET_BADGES = {
    "first": ("🛰", "First Contact", "Reach your first beacon"),
    "loop": ("🔁", "Loop Pilot", "Reach a beacon using a for loop"),
    "while": ("👀", "Sensor Driver", "Reach a beacon using a while loop"),
    "if": ("🔀", "Decision Maker", "Reach a beacon using an if"),
    "def": ("🧩", "Architect", "Reach a beacon using a function you made"),
    "print": ("🔬", "Scientist", "Reach a beacon with print() in your code"),
    "fixer": ("🐛", "Bug Squasher", "Fix a code error, then reach the beacon"),
    "grit": ("💪", "Never Give Up", "Reach a beacon after 5 runs that didn't"),
    "triple": ("🌟", "Triple Star", "Earn all three stars in one run"),
    "compact": ("✂️", "Minimalist", "Earn the compact star on 5 sites"),
    "crystals": ("💎", "Crystal Hunter", "Collect every crystal on 4 sites"),
    "discover": ("📡", "Discoverer", "Spot 3 anomalies"),
    "record": ("🏆", "Record Breaker", "Beat a class record"),
    "hopper": ("🪐", "Planet Hopper", "Reach all 5 Uncharted planets in one run"),
}
for _zone in planet.ZONES[:-1]:
    PLANET_BADGES["master_" + _zone["key"]] = (
        "🏅", f"{_zone['name']} Master", f"Earn all 9 stars in {_zone['name']}")

# The first time a zone's hidden rule shows up in a student's run, it's an
# anomaly: the page celebrates spotting it without saying what it is.
ANOMALIES = {"ice": "⛸", "wind": "💨 gust pushed", "crumble": "💥 cracked",
             "solar": "🔋", "portals": "✨"}

# The rover garage. Paint, toppers and trails unlock with your stars; the
# class unlocks the last paints together on the class star meter.
GARAGE = [
    {"slot": "paint", "key": "bone", "name": "Moonstone", "stars": 0},
    {"slot": "paint", "key": "coral", "name": "Coral", "stars": 3},
    {"slot": "paint", "key": "mint", "name": "Mint", "stars": 8},
    {"slot": "paint", "key": "sky", "name": "Sky", "stars": 15},
    {"slot": "paint", "key": "gold", "name": "Gold", "stars": 30},
    {"slot": "paint", "key": "aurora", "name": "Aurora", "class": 30},
    {"slot": "paint", "key": "nebula", "name": "Nebula", "class": 90},
    {"slot": "paint", "key": "supernova", "name": "Supernova", "class": 180},
    {"slot": "topper", "key": "none", "name": "Antenna", "stars": 0},
    {"slot": "topper", "key": "flag", "name": "Flag", "stars": 5},
    {"slot": "topper", "key": "dish", "name": "Radar dish", "stars": 12},
    {"slot": "topper", "key": "light", "name": "Beacon light", "stars": 20},
    {"slot": "topper", "key": "crown", "name": "Crown", "stars": 40},
    {"slot": "trail", "key": "tracks", "name": "Tracks", "stars": 0},
    {"slot": "trail", "key": "dust", "name": "Dust", "stars": 10},
    {"slot": "trail", "key": "sparkle", "name": "Sparkle", "stars": 25},
    {"slot": "trail", "key": "rainbow", "name": "Rainbow", "stars": 45},
]
CLASS_GOALS = sorted({item["class"] for item in GARAGE if "class" in item})


def planet_entry(p):
    entry = p.setdefault("planet", {"solved": {}, "code": {}, "runs": {},
                                    "hints": {}, "journal": {}, "unlocked": 0,
                                    "uncharted": None, "active": None})
    # Stars, badges and the garage arrived after some saves did.
    for key, value in (("stars", {}), ("badges", []), ("anomalies", []),
                       ("misses", {}), ("errored", {}),
                       ("look", {"paint": "bone", "topper": "none", "trail": "tracks"})):
        entry.setdefault(key, value)
    return entry


def planet_frontier(p):
    """Index in planet.SITE_ORDER of the furthest site this student may open:
    the first one they haven't solved, or further if the teacher unlocked it."""
    entry = planet_entry(p)
    first = next((i for i, key in enumerate(planet.SITE_ORDER)
                  if key not in entry["solved"]), len(planet.SITE_ORDER) - 1)
    return max(first, min(entry["unlocked"], len(planet.SITE_ORDER) - 1))


def planet_open(p, key):
    return key in planet.SITE_ORDER and \
        planet.SITE_ORDER.index(key) <= planet_frontier(p)


def planet_variant(p, key):
    zi, zone, s = planet.find_site(key)
    return s["variants"][planet.variant_index(p["id"], s)]


def star_count(entry):
    return sum(sum(v) for v in entry["stars"].values())


def class_stars():
    return sum(star_count(planet_entry(q)) for q in players.values() if q.get("planet"))


def garage_for(entry):
    mine, ours = star_count(entry), class_stars()
    return [dict(item, open=(mine >= item["stars"]) if "stars" in item
                 else ours >= item["class"]) for item in GARAGE]


def class_record(key):
    """The fewest ticks anyone has reached this site's beacon in, and who."""
    best = None
    for q in players.values():
        ticks = (q.get("planet") or {}).get("solved", {}).get(key)
        if ticks is not None and (best is None or ticks < best["ticks"]):
            best = {"ticks": ticks, "name": q["name"]}
    return best


def feed(text):
    planet_feed.append({"at": int(time.time()), "text": text})
    del planet_feed[:-40]


def planet_state(p):
    """The student's map of the planet: every zone and site, with stars,
    what's open, hints, journal notes, badges and the garage."""
    entry = planet_entry(p)
    frontier = planet_frontier(p)
    zones = []
    for zone in planet.ZONES:
        zones.append({
            "key": zone["key"], "name": zone["name"], "blurb": zone["blurb"],
            "hints": zone["hints"][:entry["hints"].get(zone["key"], 0)],
            "hint_count": len(zone["hints"]),
            "journal": entry["journal"].get(zone["key"], ""),
            "sites": [{"key": s["key"], "name": s["name"],
                       "solved": entry["solved"].get(s["key"]),
                       "stars": entry["stars"].get(s["key"], [False] * 3),
                       "open": planet.SITE_ORDER.index(s["key"]) <= frontier}
                      for s in zone["sites"]]})
    return {"you": {"name": p["name"]}, "zones": zones,
            "current": planet.SITE_ORDER[frontier],
            "uncharted": entry["uncharted"],
            "total_stars": star_count(entry),
            "max_stars": 3 * len(planet.SITE_ORDER),
            "badges": [{"key": k, "icon": b[0], "name": b[1], "how": b[2],
                        "earned": k in entry["badges"]}
                       for k, b in PLANET_BADGES.items()],
            "look": entry["look"], "garage": garage_for(entry),
            "class": {"stars": class_stars(), "goals": CLASS_GOALS}}


def planet_site(p, key):
    """One site as the student sees it before running: the map, its three
    goals and crystals, but none of the hidden rules (wind, sunlight timing,
    portal wiring)."""
    zi, zone, s = planet.find_site(key)
    entry = planet_entry(p)
    view = {"key": key, "name": s["name"], "brief": s["brief"],
            "zone": zone["name"], "sensors": planet.sensors_for(zi),
            "code": entry["code"].get(key, ""),
            "solved": entry["solved"].get(key),
            "stars": entry["stars"].get(key, [False] * 3),
            "record": None if key == planet.UNCHARTED["key"] else class_record(key)}
    if key == planet.UNCHARTED["key"]:
        view["goals"] = ["🪐 Reach 1 planet", "🪐 Reach 3 planets in one run",
                         "🪐 Reach all 5 in one run"]
    else:
        v = planet_variant(p, key)
        view.update(map=v["map"], dir=v.get("dir", 1),
                    battery="battery" in zone["rules"],
                    crystals=v.get("crystals", []), goals=planet.goals(s, v))
    return view


def code_features(code):
    """Which Python a program uses, for the coding badges."""
    try:
        nodes = list(ast.walk(ast.parse(code)))
    except SyntaxError:
        return set()
    found = set()
    for n in nodes:
        if isinstance(n, ast.For):
            found.add("loop")
        elif isinstance(n, ast.While):
            found.add("while")
        elif isinstance(n, ast.If):
            found.add("if")
        elif isinstance(n, ast.FunctionDef):
            found.add("def")
        elif isinstance(n, ast.Call) and getattr(n.func, "id", None) == "print":
            found.add("print")
    return found


def planet_record(p, key, code, results):
    """Save a run and work out everything it earned: stars, badges, a class
    record, the first sighting of the zone's hidden rule, garage unlocks."""
    entry = planet_entry(p)
    zi, zone, s = planet.find_site(key)
    entry["code"][key] = code
    entry["runs"][key] = entry["runs"].get(key, 0) + 1
    entry["active"] = int(time.time())
    before_open = {i["key"] for i in garage_for(entry) if i["open"]}
    before_stars = star_count(entry)
    earned = []
    record = None

    def badge(key_):
        if key_ not in entry["badges"]:
            entry["badges"].append(key_)
            icon, name, how = PLANET_BADGES[key_]
            earned.append({"icon": icon, "name": name, "how": how})
            feed(f"{icon} {p['name']} earned {name}")

    if key == planet.UNCHARTED["key"]:
        reached = sum(r["reached"] for r in results)
        score = {"reached": reached,
                 "ticks": sum(r["ticks"] for r in results if r["reached"])}
        best = entry["uncharted"]
        if best is None or (score["reached"], -score["ticks"]) > \
                (best["reached"], -best["ticks"]):
            entry["uncharted"] = score
        if reached:
            entry["solved"].setdefault(key, score["ticks"])
        run_stars = [reached >= 1, reached >= 3, reached == len(results)]
        if reached == len(results):
            badge("hopper")
        reached_any = reached > 0
    else:
        run = results[0]
        v = planet_variant(p, key)
        run_stars = planet.stars(s, v, run, code)
        reached_any = run["reached"]
        if run["reached"]:
            previous = class_record(key)
            best = entry["solved"].get(key)
            entry["solved"][key] = run["ticks"] if best is None else min(best, run["ticks"])
            if previous is None:
                record = {"ticks": run["ticks"], "name": p["name"], "first": True}
                feed(f"🚩 {p['name']} was first to reach {s['name']}")
            elif run["ticks"] < previous["ticks"]:
                record = {"ticks": run["ticks"], "name": p["name"], "first": False}
                feed(f"🏆 {p['name']} set a class record on {s['name']}: "
                     f"{run['ticks']} ticks")
                badge("record")
    stars = [a or b for a, b in zip(entry["stars"].get(key, [False] * 3), run_stars)]
    entry["stars"][key] = stars
    new_stars = star_count(entry) - before_stars

    # Coding badges, for runs that got there.
    if reached_any:
        badge("first")
        for feature in sorted(code_features(code)):
            badge(feature)
        if entry["errored"].get(key):
            badge("fixer")
        if entry["misses"].get(key, 0) >= 5:
            badge("grit")
        entry["misses"][key] = 0
    else:
        entry["misses"][key] = entry["misses"].get(key, 0) + 1
    entry["errored"][key] = any(r.get("error") for r in results)
    if all(run_stars):
        badge("triple")
        if key != planet.UNCHARTED["key"]:
            feed(f"🌟 {p['name']} earned all three stars on {s['name']}")
    if sum(v[2] for k, v in entry["stars"].items() if k != planet.UNCHARTED["key"]) >= 5:
        badge("compact")
    crystal_sites = [k for k, c in planet.CHALLENGES.items() if c["bonus"]["kind"] == "crystals"]
    if all(entry["stars"].get(k, [0, 0, 0])[1] for k in crystal_sites):
        badge("crystals")
    for z in planet.ZONES[:-1]:
        if all(all(entry["stars"].get(x["key"], [False])) for x in z["sites"]):
            badge("master_" + z["key"])

    # The zone's hidden rule, the first time it shows up.
    anomaly = None
    mark = ANOMALIES.get(zone["key"])
    if mark and zone["key"] not in entry["anomalies"] and key != planet.UNCHARTED["key"]:
        line = next((l for l in results[0]["log"] if mark in l), None)
        if line:
            entry["anomalies"].append(zone["key"])
            anomaly = {"zone": zone["name"], "tick": int(line.split(":")[0][5:])}
            if len(entry["anomalies"]) >= 3:
                badge("discover")

    unlocked = [i for i in garage_for(entry) if i["open"] and i["key"] not in before_open]
    return {"stars": run_stars, "best": stars, "new_stars": new_stars,
            "badges": earned, "record": record, "anomaly": anomaly,
            "unlocked": [{"slot": i["slot"], "key": i["key"], "name": i["name"]}
                         for i in unlocked],
            "total_stars": star_count(entry)}


def planet_set_look(p, data):
    """Fit the rover with garage items the student has unlocked."""
    entry = planet_entry(p)
    open_items = {(i["slot"], i["key"]) for i in garage_for(entry) if i["open"]}
    for slot in ("paint", "topper", "trail"):
        choice = str(data.get(slot, entry["look"].get(slot, "")))
        if (slot, choice) in open_items:
            entry["look"][slot] = choice
    return entry["look"]


def planet_class():
    """The teacher's overview and the projector's class view: where everyone
    is, how stuck they are, their stars, what they think each zone's hidden
    rule is, and the class's recent moments."""
    rows = []
    for q in players.values():
        entry = q.get("planet")   # read only: don't start an entry for them
        if not entry:
            continue
        entry = planet_entry(q)
        frontier = planet_frontier(q)
        key = planet.SITE_ORDER[frontier]
        zi, zone, s = planet.find_site(key)
        rows.append({"id": q["id"], "name": q["name"], "site": key,
                     "site_name": s["name"], "zone": zone["name"],
                     "solved": len(entry["solved"]),
                     "stars": star_count(entry),
                     "badges": len(entry["badges"]),
                     "look": entry["look"],
                     "runs_here": entry["runs"].get(key, 0),
                     "hints": sum(entry["hints"].values()),
                     "journal": {z["name"]: entry["journal"][z["key"]]
                                 for z in planet.ZONES if entry["journal"].get(z["key"])},
                     "uncharted": entry["uncharted"],
                     "active": entry["active"]})
    rows.sort(key=lambda x: (x["solved"], -x["runs_here"], x["name"].lower()))
    return {"students": rows, "sites": len(planet.SITE_ORDER),
            "zones": [z["name"] for z in planet.ZONES],
            "class": {"stars": class_stars(), "goals": CLASS_GOALS,
                      "max": 3 * len(planet.SITE_ORDER) * max(1, len(rows))},
            "feed": planet_feed[-12:]}


def unlocked_frontier(p, wi=None):
    """Highest maze index this player may enter in world `wi`: the first one
    they haven't solved yet, OR further if the teacher unlocked ahead from the
    admin page. So mazes 0..frontier are open, everything past it is locked
    until they beat the level in front of it (or a teacher unlocks it)."""
    if wi is None:
        wi = p["world"]
    i = 0
    while bkey(wi, i) in p["best"]:
        i += 1
    return max(i, p.get("unlocked", {}).get(str(wi), 0))


def level_scores(wi, mi, limit=5):
    """Code-golf ranking for one maze: who solved it in the fewest characters."""
    k = bkey(wi, mi)
    rows = [{"name": q["name"], "color": q["color"], "chars": q["chars"][k],
             "lines": q["best"][k]}
            for q in players.values() if k in q["best"]]
    rows.sort(key=lambda x: (x["chars"], x["name"].lower()))
    return rows[:limit]


def overview():
    """Everything the teacher's big screen needs: every student, live."""
    people = []
    for q in players.values():
        # In a fogged world the big screen shows each student only the squares
        # their own lamp has found. Otherwise the projector hands the whole
        # blackout map to everyone in the room.
        view = None
        if is_fogged(q["world"], q["maze"]):
            seen = seen_set(q, q["world"], q["maze"])
            seen.add((q["row"], q["col"]))
            view = fog_maze(mazes_of(q)[q["maze"]], seen)
        people.append({
            "maze_view": view,
            "id": q["id"], "name": q["name"], "color": q["color"],
            "world": q["world"], "world_name": WORLDS[q["world"]]["name"],
            "maze": q["maze"], "maze_num": q["maze"] + 1,
            "maze_count": len(mazes_of(q)),
            "row": q["row"], "col": q["col"], "dir": q["dir"],
            "solved": solved_count(q), "chars": total_chars(q),
            "lines": total_lines(q),
            "cleared": cleared(q), "code": q["code"],
            "rally": [{"name": lg["name"], "unlocked": lg["unlocked"],
                       "solved": (lg["best"] or {}).get("solved", 0),
                       "stars": (lg["best"] or {}).get("stars", 0),
                       "tracks": lg["tracks"]}
                      for lg in rally_summary(q)],
            "rally_hints": rally_hints_used(q),
            "cycles": cycles_summary(q),
        })
    people.sort(key=lambda x: (x["world"], x["name"].lower()))
    # A fogged world's mazes are sent blanked out — the screen draws those from
    # each student's own `maze_view` instead, and nobody can read the map out of
    # this response.
    return {"worlds": [{"name": w["name"],
                        "mazes": [fog_maze(m, set()) for m in w["mazes"]]
                                 if w.get("fog") else w["mazes"]}
                       for w in WORLDS],
            "maze_count": len(WORLDS[DEFAULT_WORLD]["mazes"]),
            "players": people, "scoreboard": scoreboard()}


def world_summaries(p):
    """One line per world for the player's world switcher."""
    return [{"index": i, "name": w["name"], "blurb": w["blurb"],
             "count": len(w["mazes"]), "solved": solved_in_world(p, i),
             "frontier": unlocked_frontier(p, i)}
            for i, w in enumerate(WORLDS)]


def state_for(p):
    """The game as seen by player p: their maze + everyone on that same maze."""
    wi, mi = p["world"], p["maze"]
    mazes = mazes_of(p)
    here = [
        {"id": q["id"], "name": q["name"], "color": q["color"],
         "row": q["row"], "col": q["col"], "dir": q["dir"]}
        for q in players.values() if q["world"] == wi and q["maze"] == mi
    ]
    # In a fogged world the browser is only ever told the part of the map this
    # player has lit — the rest genuinely isn't in the page, so there's nothing
    # to peek at, and no map to paste anywhere. Classmates standing in the dark
    # are hidden too, or you could read the maze off where they're walking.
    fog = is_fogged(wi, mi)
    view = mazes[mi]
    if fog:
        seen = seen_set(p, wi, mi)
        seen.add((p["row"], p["col"]))
        view = fog_maze(view, seen)
        here = [q for q in here if (q["row"], q["col"]) in seen]
    # `best` is handed over already narrowed to this world, keyed by maze index,
    # so the level bar can look levels up directly.
    best_here = {i: p["best"][bkey(wi, i)]
                 for i in range(len(mazes)) if bkey(wi, i) in p["best"]}
    chars_here = {i: p["chars"][bkey(wi, i)]
                  for i in range(len(mazes)) if bkey(wi, i) in p["chars"]}
    level_infos = WORLDS[wi].get("levels") or [
        {"title": f"Maze {i + 1}", "chapter": f"Level {i + 1}",
         "brief": WORLDS[wi]["blurb"], "objective": "Reach the exit.",
         "concepts": [], "starter": ""}
        for i in range(len(mazes))
    ]
    return {
        "maze": view,
        "fog": fog,
        "maze_index": mi,
        "maze_count": len(mazes),
        "world_index": wi,
        "world_name": WORLDS[wi]["name"],
        "quest_world_index": QUEST_WORLD,
        "is_quest": wi == QUEST_WORLD,
        "level_info": level_infos[mi],
        "level_infos": level_infos,
        "worlds": world_summaries(p),
        "players": here,
        "you": p["id"],
        "you_name": p["name"],     # so a reloaded page can restore its header
        "you_color": p["color"],
        "cleared": cleared(p),
        "is_last": mi + 1 >= len(mazes),
        "best": best_here,       # lines of this player's record run per maze
        "chars": chars_here,     # this player's fewest characters per maze
        "unlocked": unlocked_frontier(p),   # highest maze index they may enter
        "level_board": level_scores(wi, mi),  # top 5 shortest solutions here
        "scoreboard": scoreboard(),
    }


# ---------------------------------------------------------------------------
# Admin actions.
# ---------------------------------------------------------------------------
def admin_action(data):
    action = data.get("action")
    maze_num = int(data.get("maze", 1) or 1)
    wi = max(0, min(len(WORLDS) - 1, int(data.get("world", 1) or 1) - 1))
    name = WORLDS[wi]["name"]
    clamp = lambda n: max(0, min(len(WORLDS[wi]["mazes"]) - 1, n - 1))

    def unlock(q, idx):
        q.setdefault("unlocked", {})[str(wi)] = max(
            q["unlocked"].get(str(wi), 0), idx)

    if action == "reset_scores":
        for q in players.values():
            q["world"] = wi
            q["maze"] = 0
            q["best"] = {}
            q["unlocked"] = {}
            q["seen"] = {}      # fogged worlds go dark again too
            reset_to_start(q)
        return f"All scores reset — everyone starts at {name}, maze 1."
    if action == "clear":
        players.clear()
        return "All players removed."
    if action == "goto":
        idx = clamp(maze_num)
        for q in players.values():
            q["world"] = wi
            q["maze"] = idx
            reset_to_start(q)
        return f"Everyone sent to {name}, maze {idx + 1}."
    if action == "unlock_player":
        q = players.get(data.get("pid"))
        if not q:
            return "No such player."
        # A single student is unlocked inside whichever world they're in.
        wi, name = q["world"], WORLDS[q["world"]]["name"]
        idx = clamp(maze_num)
        unlock(q, idx)
        return f"Unlocked {name} maze {idx + 1} for {q['name']}."
    if action == "rally_unlock":
        q = players.get(data.get("pid"))
        if not q:
            return "No such player."
        locked = [i for i in range(len(RALLY_LEAGUES)) if not rally_unlocked(q, i)]
        if not locked:
            return f"{q['name']} already has every Bot Rally league."
        q["rally_unlocked"] = locked[0]
        return (f"Unlocked Bot Rally {RALLY_LEAGUES[locked[0]]['name']} "
                f"for {q['name']}.")
    if action == "unlock_all":
        idx = clamp(maze_num)
        for q in players.values():
            unlock(q, idx)
        return f"Unlocked everyone up to {name} maze {idx + 1}."
    if action == "planet_unlock":
        q = players.get(data.get("pid"))
        if not q:
            return "No such player."
        frontier = planet_frontier(q)
        if frontier + 1 >= len(planet.SITE_ORDER):
            return f"{q['name']} already has every Strange Planet site."
        planet_entry(q)["unlocked"] = frontier + 1
        key = planet.SITE_ORDER[frontier + 1]
        return (f"Unlocked Strange Planet site {key.upper()} "
                f"({planet.find_site(key)[2]['name']}) for {q['name']}.")
    if action == "cycles_reset":
        # A new season (or a new class) starts with nobody entered, so last
        # class's bots and ej's own test bot don't ride in its battles. Each
        # student keeps their code and best test drive, and enters again
        # with their next Test drive.
        for q in players.values():
            entry = cycles_entry(q)
            entry["points"] = entry["rounds"] = entry["wins"] = 0
            entry.update(code="", entered_at=None, ok=True, error=None,
                         kept_previous=False)
        cycles_round["number"], cycles_round["last"] = 0, None
        return ("Light Cycles season reset — everyone is back to 0 points and "
                "enters again with their next Test drive.")
    return "Unknown action."


# ---------------------------------------------------------------------------
# HTTP handling.
# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------
# Cake Shop (cake.py): customers order cakes and students bake them with
# Python at /cake. The projector shows the class shop window at /cake/show,
# and the teacher's overview is /cake/teacher.
#
# Stars unlock toppings, special frostings and the look of the shop; the class
# star meter unlocks the last few for everyone. Studio cakes go in the class
# shop window, where classmates can heart them and remix their recipes.
# ---------------------------------------------------------------------------
SHOP_NAME_MAX = 30
CAKE_TITLE_MAX = 30
THEME_MAX = 60
cake_feed = []                       # the class's recent moments, for the projector
cake_class = {"theme": ""}           # the shop window theme the teacher set

CAKE_BADGES = {
    "first": ("🎂", "First Customer", "Make a customer happy"),
    "loop": ("🔁", "Loop Baker", "Make a customer happy using a for loop"),
    "if": ("🔀", "Decision Maker", "Make a customer happy using an if"),
    "list": ("📋", "List Maker", "Make a customer happy using a list you made"),
    "fstring": ("✍️", "Word Wizard", "Make a customer happy using an f-string"),
    "def": ("📖", "Recipe Writer", "Make a customer happy with a recipe you made with def"),
    "print": ("🔬", "Taste Tester", "Make a customer happy with print() in your code"),
    "fixer": ("🐛", "Bug Squasher", "Fix a code error, then make the customer happy"),
    "grit": ("💪", "Never Give Up", "Make a customer happy after 5 bakes that didn't"),
    "triple": ("🌟", "Triple Star", "Earn all three stars in one bake"),
    "artist": ("🎨", "Artist", "Earn the own-touch star on 5 levels"),
    "dragon": ("🐉", "Dragon Tamer", "Light all 100 of Ember's candles"),
    "window": ("🪟", "Window Display", "Put a cake in the shop window"),
    "loved": ("💖", "Crowd Pleaser", "Get 5 hearts on your shop window cake"),
    "kind": ("💌", "Kind Critic", "Heart 5 cakes in the shop window"),
    "starbaker": ("🏆", "Star Baker", "Make all 5 Bake-Off customers happy at once"),
}
for _ci, _ch in enumerate(cake.CHAPTERS[:-1]):
    CAKE_BADGES["master_" + _ch["key"]] = (
        "🏅", f"{_ch['name']} Master", f"Earn all 9 stars in {_ch['name']}")
CAKE_CLASS_GOALS = sorted({u["class"] for u in cake.UNLOCKS if "class" in u})


def cake_entry(p):
    entry = p.setdefault("cake", {})
    for key, value in (("shop", ""), ("solved", {}), ("stars", {}), ("code", {}),
                       ("runs", {}), ("hints", {}), ("badges", []), ("misses", {}),
                       ("errored", {}), ("unlocked", 0), ("active", None),
                       ("look", {"stand": "plate", "wallpaper": "strawberry"}),
                       ("studio", ""), ("window", None), ("last_error", ""),
                       ("bake_off", 0)):
        entry.setdefault(key, value)
    return entry


def cake_public(p):
    """A name for a student's shop window cake that isn't their login id."""
    return "w%08x" % zlib.crc32(("cake:" + p["id"]).encode())


def cake_frontier(p):
    """Index in cake.LEVEL_ORDER of the furthest level this student may open."""
    entry = cake_entry(p)
    first = next((i for i, key in enumerate(cake.LEVEL_ORDER)
                  if key not in entry["solved"]), len(cake.LEVEL_ORDER) - 1)
    return max(first, min(entry["unlocked"], len(cake.LEVEL_ORDER) - 1))


def cake_open(p, key):
    return key in cake.LEVEL_ORDER and cake.LEVEL_ORDER.index(key) <= cake_frontier(p)


def cake_star_count(entry):
    return sum(sum(v) for v in entry["stars"].values())


def cake_class_stars():
    return sum(cake_star_count(cake_entry(q)) for q in players.values() if q.get("cake"))


def cake_unlocked(entry):
    return cake.open_unlocks(cake_star_count(entry), cake_class_stars())


def cake_pantry(entry):
    opened = cake_unlocked(entry)
    return [dict(u, name=cake.unlock_name(u), open=(u["kind"], u["key"]) in opened)
            for u in cake.UNLOCKS]


def cake_feed_add(text):
    cake_feed.append({"at": int(time.time()), "text": text})
    del cake_feed[:-40]


def cake_state(p):
    """Everything the student page needs: chapters and levels with stars,
    badges, the pantry of unlocks and the look of their shop."""
    entry = cake_entry(p)
    frontier = cake_frontier(p)
    chapters = []
    for ci, ch in enumerate(cake.CHAPTERS):
        chapters.append(dict(ch, levels=[
            {"key": lv["key"], "name": lv["name"],
             "face": lv["customers"][0]["face"] if lv["customers"] else "🏆",
             "solved": lv["key"] in entry["solved"],
             "stars": entry["stars"].get(lv["key"], [False] * 3),
             "open": cake.LEVEL_ORDER.index(lv["key"]) <= frontier}
            for lv in cake.LEVELS if lv["chapter"] == ci]))
    window = entry["window"]
    return {"you": {"name": p["name"], "shop": entry["shop"]},
            "chapters": chapters, "current": cake.LEVEL_ORDER[frontier],
            "total_stars": cake_star_count(entry),
            "max_stars": 3 * len(cake.LEVEL_ORDER),
            "badges": [{"key": k, "icon": b[0], "name": b[1], "how": b[2],
                        "earned": k in entry["badges"]}
                       for k, b in CAKE_BADGES.items()],
            "look": entry["look"], "pantry": cake_pantry(entry),
            "studio": entry["studio"] or cake.STUDIO_STARTER,
            "window": {"title": window["title"], "hearts": len(window["hearts"]),
                       "hidden": window.get("hidden", False)} if window else None,
            "theme": cake_class["theme"],
            "class": {"stars": cake_class_stars(), "goals": CAKE_CLASS_GOALS}}


def cake_palette():
    return {"flavours": cake.FLAVOURS, "colours": cake.COLOURS,
            "specials": cake.SPECIALS, "toppings": cake.TOPPINGS,
            "stands": cake.STANDS, "wallpapers": cake.WALLPAPERS}


def cake_level(p, key):
    """One level as the student sees it before baking: the customers, their
    tickets, the house rules, the Chef's tip and the goals."""
    lv = cake.LEVEL_BY_KEY[key]
    entry = cake_entry(p)
    bake_off = lv.get("bake_off", False)
    customers = cake.customers_for(lv, 0)
    return {"key": key, "name": lv["name"], "chapter": cake.CHAPTERS[lv["chapter"]],
            "tip": lv["tip"], "rules": lv.get("rules", []),
            "starter": lv["starter"], "code": entry["code"].get(key, ""),
            "hints": lv["hints"][:entry["hints"].get(key, 0)],
            "hint_count": len(lv["hints"]), "goals": cake.goals(lv),
            "stars": entry["stars"].get(key, [False] * 3),
            "solved": key in entry["solved"], "bake_off": bake_off,
            "commands": lv["commands"],
            "new": [c for c in lv["commands"] if cake.COMMAND_CHAPTER[c] == lv["chapter"]],
            "customers": [{"name": c["name"], "face": c["face"], "says": c["says"],
                           "ticket": c.get("ticket"),
                           "checklist": None if c.get("ticket") else cake.checklist(c["want"])}
                          for c in customers]}


def cake_code_features(code):
    """Which Python a program uses, for the coding badges."""
    found = code_features(code) - {"while", "def"}
    try:
        nodes = list(ast.walk(ast.parse(code)))
    except SyntaxError:
        return found
    if any(isinstance(n, ast.List) for n in nodes):
        found.add("list")
    if any(isinstance(n, ast.JoinedStr) and any(isinstance(v, ast.FormattedValue)
                                                for v in n.values) for n in nodes):
        found.add("fstring")
    return found


def cake_record(p, key, code, results):
    """Save a bake and work out everything it earned."""
    entry = cake_entry(p)
    lv = cake.LEVEL_BY_KEY[key]
    entry["code"][key] = code
    entry["runs"][key] = entry["runs"].get(key, 0) + 1
    entry["active"] = int(time.time())
    before_open = cake_unlocked(entry)
    before_stars = cake_star_count(entry)
    earned = []

    def badge(k):
        if k not in entry["badges"]:
            entry["badges"].append(k)
            icon, name, how = CAKE_BADGES[k]
            earned.append({"icon": icon, "name": name, "how": how})
            cake_feed_add(f"{icon} {p['name']} earned {name}")

    run_stars = cake.stars(lv, results, code)
    happy = sum(r["happy"] for r in results)
    stars = [a or b for a, b in zip(entry["stars"].get(key, [False] * 3), run_stars)]
    entry["stars"][key] = stars
    new_stars = cake_star_count(entry) - before_stars
    first_time = run_stars[0] and key not in entry["solved"]
    if run_stars[0]:
        entry["solved"].setdefault(key, int(time.time()))
    if lv.get("bake_off"):
        entry["bake_off"] = max(entry["bake_off"], happy)
    if first_time:
        face = results[0]["face"] if len(results) == 1 else "🎉"
        who = results[0]["name"] if len(results) == 1 else f"every customer at {lv['name']}"
        cake_feed_add(f"{face} {p['name']} made {who} happy")

    if run_stars[0]:
        badge("first")
        for feature in sorted(cake_code_features(code)):
            badge(feature)
        if any(r["own_function"] for r in results):
            badge("def")
        if entry["errored"].get(key):
            badge("fixer")
        if entry["misses"].get(key, 0) >= 5:
            badge("grit")
        if key == "2b":
            badge("dragon")
        entry["misses"][key] = 0
    else:
        entry["misses"][key] = entry["misses"].get(key, 0) + 1
    errors = [r["error"] for r in results if r.get("error")]
    entry["errored"][key] = bool(errors)
    entry["last_error"] = errors[0] if errors else ""
    if all(run_stars):
        badge("triple")
        if lv.get("bake_off"):
            badge("starbaker")
        cake_feed_add(f"🌟 {p['name']} earned all three stars on {lv['name']}")
    touch = [k for k, v in entry["stars"].items()
             if v[1] and cake.LEVEL_BY_KEY[k]["star2"]["kind"] == "touch"]
    if len(touch) >= 5:
        badge("artist")
    for ci, ch in enumerate(cake.CHAPTERS[:-1]):
        if all(all(entry["stars"].get(x["key"], [False])) for x in cake.LEVELS
               if x["chapter"] == ci):
            badge("master_" + ch["key"])
    unlocked = cake_unlocked(entry) - before_open
    return {"stars": run_stars, "best": stars, "new_stars": new_stars,
            "happy": happy, "badges": earned, "first": first_time,
            "unlocked": [dict(u, name=cake.unlock_name(u)) for u in cake.UNLOCKS
                         if (u["kind"], u["key"]) in unlocked],
            "total_stars": cake_star_count(entry),
            "misses": entry["misses"].get(key, 0)}


def cake_window(viewer=None, teacher=False):
    """Every cake in the class shop window, newest first. Hidden ones only
    show on the teacher's page."""
    cakes = []
    for q in players.values():
        w = (q.get("cake") or {}).get("window")
        if not w or (w.get("hidden") and not teacher):
            continue
        entry = cake_entry(q)
        cakes.append({"owner": cake_public(q), "baker": q["name"],
                      "shop": entry["shop"] or f"{q['name']}'s Bakery",
                      "title": w["title"], "cake": w["cake"], "code": w["code"],
                      "look": entry["look"], "at": w["at"],
                      "hearts": len(w["hearts"]), "hidden": w.get("hidden", False),
                      "hearted": bool(viewer) and viewer["id"] in w["hearts"],
                      "mine": bool(viewer) and viewer["id"] == q["id"]})
    cakes.sort(key=lambda c: -c["at"])
    return {"theme": cake_class["theme"], "cakes": cakes}


def cake_owner(public):
    return next((q for q in players.values()
                 if q.get("cake") and cake_public(q) == public), None)


def cake_overview():
    """The teacher's page and the projector: where everyone is, who's stuck,
    their last error, the class star meter and the recent moments."""
    rows = []
    for q in players.values():
        if not q.get("cake"):
            continue
        entry = cake_entry(q)
        frontier = cake_frontier(q)
        key = cake.LEVEL_ORDER[frontier]
        lv = cake.LEVEL_BY_KEY[key]
        rows.append({"id": q["id"], "name": q["name"],
                     "shop": entry["shop"] or f"{q['name']}'s Bakery",
                     "level": key, "level_name": lv["name"], "at": frontier,
                     "chapter": cake.CHAPTERS[lv["chapter"]]["name"],
                     "solved": len(entry["solved"]), "stars": cake_star_count(entry),
                     "badges": len(entry["badges"]),
                     "runs_here": entry["runs"].get(key, 0),
                     "misses": entry["misses"].get(key, 0),
                     "hints": sum(entry["hints"].values()),
                     "last_error": entry["last_error"],
                     "window": bool(entry["window"]),
                     "active": entry["active"]})
    rows.sort(key=lambda x: (x["at"], -x["misses"], x["name"].lower()))
    return {"students": rows, "levels": len(cake.LEVEL_ORDER),
            "level_names": {lv["key"]: lv["name"] for lv in cake.LEVELS},
            "class": {"stars": cake_class_stars(), "goals": CAKE_CLASS_GOALS,
                      "unlocks": [dict(u, name=cake.unlock_name(u))
                                  for u in cake.UNLOCKS if "class" in u]},
            "theme": cake_class["theme"], "feed": cake_feed[-12:]}


def cake_teacher(data):
    """Teacher actions on /cake/teacher (they need the admin key)."""
    action = data.get("action")
    if action == "theme":
        cake_class["theme"] = str(data.get("theme", "")).strip()[:THEME_MAX]
        if cake_class["theme"]:
            cake_feed_add(f"🪟 New shop window theme: {cake_class['theme']}")
        return {"ok": True}
    if action in ("hide", "show"):
        q = cake_owner(str(data.get("owner", "")))
        if not q or not cake_entry(q)["window"]:
            return {"error": "No such cake."}
        cake_entry(q)["window"]["hidden"] = action == "hide"
        return {"ok": True}
    if action == "unlock":
        targets = list(players.values()) if data.get("everyone") else \
            [players.get(str(data.get("id", "")))]
        if not all(targets):
            return {"error": "No such student."}
        to = cake.LEVEL_ORDER.index(data.get("level")) if data.get("level") in \
            cake.LEVEL_ORDER else len(cake.LEVEL_ORDER) - 1
        for q in targets:
            if q.get("cake") or not data.get("everyone"):
                entry = cake_entry(q)
                entry["unlocked"] = max(entry["unlocked"], to)
        return {"ok": True}
    return {"error": "Unknown action."}


def load(path):
    with open(path, "rb") as f:
        return f.read()


PAGES = {
    "/": ("studio.html", "text/html; charset=utf-8"),
    "/classic": ("game.html", "text/html; charset=utf-8"),
    "/arena": ("arena.html", "text/html; charset=utf-8"),
    "/cycles": ("cycles.html", "text/html; charset=utf-8"),
    "/cycles/show": ("cycles_show.html", "text/html; charset=utf-8"),
    "/planet": ("planet.html", "text/html; charset=utf-8"),
    "/planet/teacher": ("planet_teacher.html", "text/html; charset=utf-8"),
    "/planet/show": ("planet_show.html", "text/html; charset=utf-8"),
    "/cake": ("cake.html", "text/html; charset=utf-8"),
    "/cake/teacher": ("cake_teacher.html", "text/html; charset=utf-8"),
    "/cake/show": ("cake_show.html", "text/html; charset=utf-8"),
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
                                 "worlds": [{"name": w["name"],
                                             "count": len(w["mazes"])}
                                            for w in WORLDS]})
            return
        if path == "/overview":
            with lock:
                self._send(200, overview())
            return
        if path == "/arena/state":
            query = parse_qs(urlsplit(self.path).query)
            pid = query.get("id", [""])[0]
            key = query.get("league", ["rookie"])[0]
            with lock:
                p = players.get(pid)
                if not p:
                    self._send(200, {"you": None})
                elif not rally_league(key):
                    self._send(200, {"error": "No such league."})
                else:
                    self._send(200, rally_state(p, key))
            return
        # Light Cycles replies are built under the lock but sent after it, so
        # a slow Wi-Fi connection never holds up the rest of the class.
        if path in ("/cycles/state", "/cycles/last"):
            pid = parse_qs(urlsplit(self.path).query).get("id", [""])[0]
            with lock:
                p = players.get(pid)
                if path == "/cycles/last":
                    body = json.dumps(cycles_replay(p)).encode()
                else:
                    body = json.dumps(cycles_state(p) if p else {"you": None}).encode()
            self._send(200, body)
            return
        if path in ("/planet/state", "/planet/site", "/planet/overview"):
            address = f"http://{get_lan_ip()}:{PORT}/planet" if path == "/planet/overview" else ""
            query = parse_qs(urlsplit(self.path).query)
            pid = query.get("id", [""])[0]
            key = query.get("site", [""])[0]
            with lock:
                p = players.get(pid)
                if path == "/planet/overview":
                    body = dict(planet_class(), address=address)
                elif not p:
                    body = {"you": None}
                elif path == "/planet/state":
                    body = planet_state(p)
                elif not planet_open(p, key):
                    body = {"error": "🔒 Reach the beacon on the site before "
                                     "this one to open it."}
                else:
                    body = planet_site(p, key)
                body = json.dumps(body).encode()
            self._send(200, body)
            return
        if path.startswith("/cake/"):
            self.cake_get(path, parse_qs(urlsplit(self.path).query))
            return
        if path == "/cycles/board":
            address = f"http://{get_lan_ip()}:{PORT}/cycles"
            with lock:
                body = json.dumps({"board": cycles_board(),
                                   "round": cycles_round["number"],
                                   "address": address}).encode()
            self._send(200, body)
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
        if self.path == "/arena/run":
            with lock:
                p = players.get(data.get("id"))
                if not p:
                    self._send(200, {"error": "join"})
                    return
                key = str(data.get("league", "rookie"))
                index = next((i for i, lg in enumerate(RALLY_LEAGUES)
                              if lg["key"] == key), None)
                if index is None or not rally_unlocked(p, index):
                    self._send(200, {"error": "🔒 Get Gold in the league "
                                     "before this one to unlock it."})
                    return
                out = run_arena(p, data.get("code", ""), key)
                save_state()
                self._send(200, out)
            return
        if self.path == "/arena/hint":
            with lock:
                p = players.get(data.get("id"))
                key = str(data.get("league", ""))
                if not p:
                    self._send(200, {"error": "join"})
                    return
                if not rally_league(key):
                    self._send(200, {"error": "No such league."})
                    return
                hints = open_rally_hint(p, key)
                save_state()
                self._send(200, {"hints": hints})
            return
        if self.path == "/cycles/test":
            with lock:
                p = players.get(data.get("id"))
                if p:
                    name, color = p["name"], cycles_color(p)
            if not p:
                self._send(200, {"error": "join"})
                return
            # Race the heats without the lock: other students keep working.
            code = str(data.get("code", ""))[:cycles.MAX_CODE + 1]
            heats = cycles.practice(code, name, color)
            with lock:
                body = json.dumps(cycles_test(p, code, heats)).encode()
                save_state()
            self._send(200, body)
            return
        if self.path == "/planet/run":
            key = str(data.get("site", ""))
            with lock:
                p = players.get(data.get("id"))
                if p and planet_open(p, key):
                    zi, zone, s = planet.find_site(key)
                    uncharted = key == planet.UNCHARTED["key"]
                    variant = None if uncharted else planet_variant(p, key)
            if not p:
                self._send(200, {"error": "join"})
                return
            if not planet_open(p, key):
                self._send(200, {"error": "🔒 Reach the beacon on the site "
                                          "before this one to open it."})
                return
            # Drive without the lock: other students keep working.
            code = str(data.get("code", ""))[:planet.MAX_CODE + 1]
            if uncharted:
                worlds = planet.uncharted_planets(random.randrange(10 ** 9))
                runs = [dict(planet.drive(code, w, zone["rules"], zi),
                             map=w["map"], dir=w.get("dir", 1)) for w in worlds]
            else:
                runs = [planet.drive(code, variant, zone["rules"], zi)]
            with lock:
                rewards = planet_record(p, key, code[:planet.MAX_CODE], runs)
                save_state()
                body = json.dumps({"runs": runs, "rewards": rewards,
                                   "state": planet_state(p)}).encode()
            self._send(200, body)
            return
        if self.path == "/planet/scout":
            # Driving by hand, to feel the planet: nothing is saved, and the
            # beacon only counts when code gets there.
            key = str(data.get("site", ""))
            moves = data.get("moves")
            with lock:
                p = players.get(data.get("id"))
                ok = p and planet_open(p, key) and key != planet.UNCHARTED["key"]
                if ok:
                    zi, zone, s = planet.find_site(key)
                    variant = planet_variant(p, key)
            if not ok or not isinstance(moves, list) or \
                    any(m not in planet.COMMANDS for m in moves):
                self._send(200, {"error": "Scouting isn't available here."})
                return
            code = "".join(f"{m}()\n" for m in moves[:SCOUT_MAX])
            self._send(200, {"run": planet.drive(code, variant, zone["rules"], zi),
                             "left": SCOUT_MAX - min(len(moves), SCOUT_MAX)})
            return
        if self.path == "/planet/look":
            with lock:
                p = players.get(data.get("id"))
                if not p:
                    self._send(200, {"error": "join"})
                    return
                look = planet_set_look(p, data)
                save_state()
                self._send(200, {"look": look})
            return
        if self.path in ("/planet/hint", "/planet/journal"):
            with lock:
                p = players.get(data.get("id"))
                zone = next((z for z in planet.ZONES
                             if z["key"] == data.get("zone")), None)
                if not p:
                    self._send(200, {"error": "join"})
                    return
                if not zone:
                    self._send(200, {"error": "No such zone."})
                    return
                entry = planet_entry(p)
                if self.path == "/planet/hint":
                    opened = entry["hints"].get(zone["key"], 0)
                    entry["hints"][zone["key"]] = min(opened + 1, len(zone["hints"]))
                else:
                    entry["journal"][zone["key"]] = \
                        str(data.get("text", "")).strip()[:JOURNAL_MAX]
                save_state()
                self._send(200, planet_state(p))
            return
        if self.path == "/cycles/battle":
            if str(data.get("key", "")) != ADMIN_KEY:
                self._send(200, {"error": "Wrong admin key."})
                return
            out = cycles_battle()   # takes the lock itself, only when it must
            with lock:
                body = json.dumps(out).encode()
                save_state()
            self._send(200, body)
            return
        if self.path.startswith("/cake/"):
            self.cake_post(self.path, data)
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
                elif p["maze"] + 1 < len(mazes_of(p)):
                    p["maze"] += 1
                    reset_to_start(p)
                    save_state()
                    self._send(200, {"ok": True, "maze_index": p["maze"]})
                elif p["world"] + 1 < len(WORLDS):
                    # Finished a world — roll straight into the next one.
                    p["world"] += 1
                    p["maze"] = 0
                    reset_to_start(p)
                    save_state()
                    self._send(200, {"ok": True, "maze_index": 0,
                                     "world_index": p["world"]})
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
                wi = data.get("world", p["world"])
                if not (isinstance(wi, int) and 0 <= wi < len(WORLDS)):
                    self._send(200, {"error": "No such world."})
                elif not (isinstance(idx, int)
                          and 0 <= idx < len(WORLDS[wi]["mazes"])):
                    self._send(200, {"error": "No such maze."})
                elif idx > unlocked_frontier(p, wi):
                    self._send(200, {"error": "🔒 Solve the earlier levels "
                                     "first to unlock this one."})
                else:
                    p["world"], p["maze"] = wi, idx
                    reset_to_start(p)
                    save_state()
                    self._send(200, {"ok": True, "maze_index": idx,
                                     "world_index": wi})
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


    # ---- Cake Shop -------------------------------------------------------------
    # Replies are built under the lock but sent after it, and code is baked
    # without the lock, so a slow program never holds up the rest of the class.

    def cake_get(self, path, query):
        pid = query.get("id", [""])[0]
        with lock:
            p = players.get(pid)
            if path == "/cake/overview":
                body = dict(cake_overview(), address=f"http://{get_lan_ip()}:{PORT}/cake")
            elif path == "/cake/window":
                body = cake_window(p, teacher=query.get("key", [""])[0] == ADMIN_KEY)
            elif not p:
                body = {"you": None}
            elif path == "/cake/state":
                body = dict(cake_state(p), palette=cake_palette())
            elif path == "/cake/level":
                key = query.get("level", [""])[0]
                body = cake_level(p, key) if cake_open(p, key) else \
                    {"error": "🔒 Make the customers before this one happy to open it."}
            else:
                body = {"error": "not found"}
            body = json.dumps(body).encode()
        self._send(200, body)

    def cake_post(self, path, data):
        if path == "/cake/teacher":
            with lock:
                body = cake_teacher(data) if str(data.get("key", "")) == ADMIN_KEY \
                    else {"error": "Wrong admin key."}
                save_state()
                self._send(200, body)
            return
        with lock:
            p = players.get(data.get("id"))
            if not p:
                self._send(200, {"error": "join"})
                return
            entry = cake_entry(p)
            unlocked = cake_unlocked(entry)
            if path == "/cake/run":
                key = str(data.get("level", ""))
                if not cake_open(p, key):
                    self._send(200, {"error": "🔒 That level isn't open yet."})
                    return
        code = str(data.get("code", ""))[:cake.MAX_CODE + 1]
        if path == "/cake/run":
            # Bake without the lock: other students keep working.
            lv = cake.LEVEL_BY_KEY[key]
            results = cake.run_level(lv, code, unlocked, seed=random.randrange(10 ** 9)
                                     if lv.get("bake_off") else 0)
            with lock:
                rewards = cake_record(p, key, code[:cake.MAX_CODE], results)
                save_state()
                body = json.dumps({"runs": results, "rewards": rewards,
                                   "state": cake_state(p)}).encode()
            self._send(200, body)
            return
        if path in ("/cake/studio", "/cake/window"):
            try:
                seed = int(data.get("seed", 0)) % 10 ** 9
            except (TypeError, ValueError):
                seed = 0
            if path == "/cake/studio" and data.get("new_seed"):
                seed = random.randrange(10 ** 9)
            out = cake.studio_bake(code, unlocked, seed=seed)
            with lock:
                entry["studio"] = code[:cake.MAX_CODE]
                if path == "/cake/window":
                    title = str(data.get("title", "")).strip()[:CAKE_TITLE_MAX]
                    if out["error"] or not out["cake"][0]["layers"]:
                        body = {"error": "Bake a cake without errors first, then put it "
                                         "in the window."}
                    elif not title:
                        body = {"error": "Give your cake a name first."}
                    else:
                        old = entry["window"] or {}
                        entry["window"] = {"title": title, "code": code[:cake.MAX_CODE],
                                           "seed": seed, "cake": out["cake"],
                                           "at": int(time.time()),
                                           "hearts": old.get("hearts", []) if
                                           old.get("title") == title else [],
                                           "hidden": False}
                        cake_feed_add(f"🪟 {p['name']} put {title} in the shop window")
                        earned = []
                        if "window" not in entry["badges"]:
                            entry["badges"].append("window")
                            icon, name, how = CAKE_BADGES["window"]
                            earned.append({"icon": icon, "name": name, "how": how})
                        body = {"ok": True, "badges": earned, "state": cake_state(p)}
                else:
                    body = dict(out, seed=seed)
                save_state()
                body = json.dumps(body).encode()
            self._send(200, body)
            return
        with lock:
            if path == "/cake/heart":
                owner = cake_owner(str(data.get("owner", "")))
                w = owner and cake_entry(owner)["window"]
                if not w or owner is p:
                    body = {"error": "You can't heart that cake."}
                else:
                    earned = []
                    if p["id"] in w["hearts"]:
                        w["hearts"].remove(p["id"])
                    else:
                        w["hearts"].append(p["id"])
                        if len(w["hearts"]) == 5:
                            o = cake_entry(owner)
                            if "loved" not in o["badges"]:
                                o["badges"].append("loved")
                                cake_feed_add(f"💖 {owner['name']}'s {w['title']} got 5 hearts")
                        given = sum(p["id"] in (cake_entry(q)["window"] or {}).get("hearts", [])
                                    for q in players.values() if q.get("cake"))
                        if given >= 5 and "kind" not in entry["badges"]:
                            entry["badges"].append("kind")
                            icon, name, how = CAKE_BADGES["kind"]
                            earned.append({"icon": icon, "name": name, "how": how})
                    body = {"hearts": len(w["hearts"]), "hearted": p["id"] in w["hearts"],
                            "badges": earned}
            elif path == "/cake/hint":
                key = str(data.get("level", ""))
                if not cake_open(p, key):
                    body = {"error": "No such level."}
                else:
                    opened = entry["hints"].get(key, 0)
                    entry["hints"][key] = min(opened + 1, len(cake.LEVEL_BY_KEY[key]["hints"]))
                    body = {"hints": cake.LEVEL_BY_KEY[key]["hints"][:entry["hints"][key]]}
            elif path == "/cake/shop":
                name = " ".join(str(data.get("name", "")).split())[:SHOP_NAME_MAX]
                entry["shop"] = name
                body = cake_state(p)
            elif path == "/cake/look":
                opened = unlocked | {("stand", "plate"), ("wallpaper", "strawberry")}
                for slot, kind in (("stand", "stand"), ("wallpaper", "wallpaper")):
                    choice = str(data.get(slot, entry["look"][slot]))
                    if (kind, choice) in opened:
                        entry["look"][slot] = choice
                body = {"look": entry["look"]}
            elif path == "/cake/code":
                key = str(data.get("level", ""))
                if key == "studio":
                    entry["studio"] = code[:cake.MAX_CODE]
                elif cake_open(p, key):
                    entry["code"][key] = code[:cake.MAX_CODE]
                body = {"ok": True}
            else:
                body = {"error": "not found"}
            save_state()
            body = json.dumps(body).encode()
        self._send(200, body)


class ClassroomServer(ThreadingHTTPServer):
    # Python waits for only 5 connections by default; a whole class pressing
    # Run at once overflowed that, so some got "connection reset".
    request_queue_size = 128


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
    server = ClassroomServer(("0.0.0.0", PORT), Handler)
    banner = "\n".join([
        "=" * 52,
        "  PYTHON QUEST is running!",
        "=" * 52,
        f"  Python Quest: http://{ip}:{PORT}                 (students start here)",
        f"  On laptop:    http://localhost:{PORT}",
        "",
        f"  Bot Rally:    http://{ip}:{PORT}/arena          (one program, 5 trials)",
        f"  Light Cycles: http://{ip}:{PORT}/cycles         (battle royale bots)",
        f"  Cycles show:  http://localhost:{PORT}/cycles/show   (project the battles)",
        f"  Strange Planet: http://{ip}:{PORT}/planet       (hidden-rule rover zones)",
        f"  Planet class: http://localhost:{PORT}/planet/teacher (who's stuck, journals)",
        f"  Planet show:  http://localhost:{PORT}/planet/show    (project the class star meter)",
        f"  Cake Shop:    http://{ip}:{PORT}/cake           (bake cakes for customers)",
        f"  Cake class:   http://localhost:{PORT}/cake/teacher  (who's stuck, the shop window)",
        f"  Cake show:    http://localhost:{PORT}/cake/show     (project the shop window)",
        f"  Maze library: http://{ip}:{PORT}/classic        (optional practice)",
        f"  Big screen:   http://localhost:{PORT}/screen        (project this)",
        f"  Leaderboard:  http://localhost:{PORT}/leaderboard",
        f"  Admin panel:  http://localhost:{PORT}/admin",
        f"  Admin key:    {ADMIN_KEY}",
        "=" * 52,
        f"  New students start in: {WORLDS[DEFAULT_WORLD]['name']} "
        f"({len(WORLDS[DEFAULT_WORLD]['mazes'])} levels)",
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
