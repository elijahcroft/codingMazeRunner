"""🔮 Predict it: the class reads a short program and says how far the rover
will drive, then watches it go. The skill the whole game is built on, in a
form everyone can join whatever level they're on.

Answers are never typed in here. Each program is really run on an open field,
so a question can't have the wrong answer. It earns nothing and shows no names.
The classroom side is in server.py.
"""

import planet

FIELD_ROWS, FIELD_COLS = 8, 16        # with a rock edge round them
START = (1, 1)
WAYS = {"north": (-1, 0), "south": (1, 0), "east": (0, 1), "west": (0, -1)}

# (program, the four answers on offer)
QUESTIONS = (
    ("east(3)\nsouth(2)\n", (3, 4, 5, 6)),
    ("east(4)\nwest(4)\n", (0, 4, 8, 10)),
    ("for i in range(4):\n    east()\n", (1, 4, 5, 8)),
    ("for i in range(3):\n    east(2)\n", (3, 5, 6, 8)),
    ("for i in range(3):\n    east()\nsouth()\n", (3, 4, 6, 9)),
    ("for i in range(3):\n    east()\n    south()\n", (3, 4, 6, 9)),
    ("def hop():\n    east(2)\n    south()\n\nhop()\nhop()\n", (3, 4, 6, 12)),
    ("n = 0\nwhile n < 3:\n    east()\n    n = n + 1\n", (2, 3, 4, 6)),
    ("for i in range(4):\n    if i == 2:\n        south()\n    east()\n", (4, 5, 6, 8)),
    ("for i in range(2):\n    for j in range(3):\n        east()\n", (2, 3, 5, 6)),
    ('while look("east") != "rock":\n    east()\n', (5, 13, 14, 15)),
    ("size = 2\nfor i in range(3):\n    east(size)\n    size = size + 1\n", (6, 8, 9, 12)),
)


class Field(planet.Easel):
    """Open ground with a rock edge. Driving into the edge just stops the rover."""

    def __init__(self):
        super().__init__()
        self.path = [list(START)]

    def next_to(self, way):
        r, c = self.path[-1]
        return r + WAYS[way][0], c + WAYS[way][1]

    def rock(self, spot):
        return not (0 < spot[0] < FIELD_ROWS - 1 and 0 < spot[1] < FIELD_COLS - 1)

    def act(self, word, way=None):
        if word != "wait" and not self.rock(self.next_to(word)):
            self.path.append(list(self.next_to(word)))

    def look(self, way):
        return "rock" if self.rock(self.next_to(way)) else "ground"


def play(code):
    """The squares the rover drives over, start included."""
    field = Field()
    planet.Rover(code, field, {"look": None}).run()
    return field.path
