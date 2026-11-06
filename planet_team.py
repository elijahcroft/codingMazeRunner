"""The Team Mission: one big map the whole class plays at the same moment.

Everyone's rover is on the same map, driven live. Doors stand between the
lander and the vault, and getting enough rovers into the vault finishes the
level and moves the whole class on to the next map. A door opens while something heavy is on its plate (or
on all its plates): a rover holds it open only while it stays there, and a
boulder pushed onto the plate sinks in and opens it for good. So the first
rover through needs a friend standing on the plate, and the boulders set that
friend free.

Nothing can get stuck for good. Progress only goes forward (a filled crater
stays filled and a sunk plate stays sunk), ♻ sends lost boulders home, and any
rover can go back to the lander. Rovers never block each other or a boulder,
so nobody can stand in the way.

The rules are here and the classroom side is in server.py. The game is in
memory only and earns no stars: the reward is getting there together, and the
class's trophies and best times are all it keeps.

Map squares:
    #  rock          .  ground        S  lander (where rovers start)
    @  boulder       o  crater        *  vault floor
    %  ♻ sends lost boulders home
    A  a door        a  its plate (the same letter, small)
"""

import ast
import copy
import math
from collections import deque

import planet

LEVELS = (
    {"name": "Landing Bay", "map": (
        "##############################",
        "#.......#.......#.......#****#",
        "#.......#.......#.......#****#",
        "#.......#.......#...c.@.#****#",
        "#...@...#.......#.......#****#",
        "#.......#.......#.......#****#",
        "#.......#.......#.......#****#",
        "#...a...A....b..B..@....C****#",
        "#.......#.......#.......#****#",
        "#.SS....#.......#.......#****#",
        "#.SS....#.......#.......#****#",
        "#.......#.......#...c.@.#****#",
        "#.......#.......#.......#****#",
        "#%......#.......#.......#****#",
        "##############################",
    )},
    {"name": "Four Corners", "map": (
        "##############################",
        "#.....................#******#",
        "#.....................#******#",
        "#....v.........v......#******#",
        "#.....................#******#",
        "#....@.........@......#******#",
        "#.....................V******#",
        "#.........SS..........V******#",
        "#.........SS..........V******#",
        "#....@................#******#",
        "#.....................#******#",
        "#....v.........v......#******#",
        "#.....................#******#",
        "#%....................#******#",
        "##############################",
    )},
    {"name": "Crater Crossing", "map": (
        "##############################",
        "#........#..........#...#****#",
        "#........#..........#.@.#****#",
        "#........A...b......C...V****#",
        "#........#..........#...#****#",
        "#........#......@...#.v.#****#",
        "#........#..........#...#****#",
        "#....####################****#",
        "#.SS.....o.....#........#****#",
        "#.SS.....o.....#......@.#****#",
        "#......@.o.a...B..c.....V****#",
        "#........o.....#......v.#****#",
        "#........o.@...#..@.....#****#",
        "#%.......o.....#........#****#",
        "##############################",
    )},
    {"name": "The Long Road", "map": (
        "##############################",
        "#.SS.........................#",
        "#.SS.....@...............a...#",
        "#............................#",
        "###########################A##",
        "#.............o..............#",
        "#.....b..@....o.......@......#",
        "#.............o..............#",
        "##B###########################",
        "#......................#*****#",
        "#.............@.....c..#*****#",
        "#......................C*****#",
        "#.............@.....c..#*****#",
        "#%.....................#*****#",
        "##############################",
    )},
    {"name": "Three-Step Bridge", "map": (
        "##############################",
        "#.............ooo......#*****#",
        "#.............ooo......#*****#",
        "#.............ooo.@.v..#*****#",
        "#.......@.....ooo......#*****#",
        "#.............ooo......#*****#",
        "#.............ooo......#*****#",
        "#.........@...ooo......V*****#",
        "#.SS..........ooo......#*****#",
        "#.SS..........ooo......#*****#",
        "#.....@.......ooo......#*****#",
        "#.............ooo...v..#*****#",
        "#.............ooo......#*****#",
        "#%............ooo......#*****#",
        "##############################",
    )},
    {"name": "The Ring", "map": (
        "##############################",
        "#.SS.........................#",
        "#.SS.........................#",
        "#...######################...#",
        "#.a.A..@.................#...#",
        "#...#.@................@.#.@.#",
        "#...#...##############...#...#",
        "#...#ooo#************#ooo#.v.#",
        "#...#...######V#######...#...#",
        "#...#.....v..@..@..v.....#...#",
        "#...#....................#...#",
        "#...######################...#",
        "#%...........................#",
        "#............................#",
        "##############################",
    )},
    {"name": "Pass It Back", "map": (
        "##############################",
        "#......#......#......#.......#",
        "#......#......#......#.......#",
        "#......#......#......#.......#",
        "#......#..@...#......#..@....#",
        "#......#......#......#.......#",
        "#......#......#......#.......#",
        "#...a..A...b..B...c..C.......#",
        "#......#......#......#.......#",
        "#.SS...#......#......####.####",
        "#.SS...#......#......#*******#",
        "#......#......#..@...#*******#",
        "#......#......#......#*******#",
        "#%.....#......#......#*******#",
        "##############################",
    )},
    {"name": "The Big Vault", "map": (
        "##############################",
        "#.........#********#.........#",
        "#.v.@...@.#********#...@...v.#",
        "#.........#********#.........#",
        "########C#####VV######G#######",
        "#.........#v.......#....o....#",
        "#.c..@..c.#.@..@...#..@.o.@..#",
        "#.........#........#g...o....#",
        "##.###########D############.##",
        "#....oo...#........#...#.....#",
        "#....oo.@.#.@.d..@.#.@.E.e...#",
        "#....oo...A........B...#.....#",
        "#....oo.@.#.a.SS.b.#.f.F..@..#",
        "#....oo...#%..SS...#...#.....#",
        "##############################",
    )},
)
DOORS = "ABCDEFGV"
WAYS = {"north": (-1, 0), "south": (1, 0), "east": (0, 1), "west": (0, -1)}
BOULDER_REST = 20    # seconds since a push before ♻ counts a boulder as lost
NEWS_KEPT = 4
SHOUT_LASTS = 6      # seconds a shout stays on the map
# Everything a rover can say to the class. It's a fixed list, so there's no chat to watch.
SHOUTS = {"help": "🆘 Help me here!", "hold": "✋ I'm holding the door!", "look": "👀 Look here!",
          "boulder": "🪨 Bring a boulder!", "thanks": "🙌 Thank you!"}


HELPER = -1          # the helper rover's seat: students' seats start at 1


class Mission:
    """One game of the map. Rovers are known by seat number, and a square is
    a (row, column) pair."""

    def __init__(self, level=0):
        self.level, self.map = level, LEVELS[level]["map"]
        self.doors, self.plates = {}, {}
        self.boulders = []                # at None once it has gone into the ground
        self.starts, self.vault = [], set()
        self.filled, self.sunk = set(), set()
        self.forced = set()               # doors the teacher opened
        self.rovers = {}
        self.news = []
        self.shouts = []                  # [number, seat, words, when]
        self.shouted = 0
        self.steps = self.pushes = 0      # for the recap when the level is won
        self.trail = {}                   # square: how many times a rover drove onto it
        self.began = self.won = None
        self.record = None                # "first", or seconds off the class best
        self.helped = False               # the helper rover was here: no trophy or class best
        for r, row in enumerate(self.map):
            for c, ch in enumerate(row):
                if ch == "@":
                    self.boulders.append({"at": (r, c), "home": (r, c), "pushed": 0, "plate": False})
                elif ch == "S":
                    self.starts.append((r, c))
                elif ch == "*":
                    self.vault.add((r, c))
                elif ch == "%":
                    self.recycler = (r, c)
                elif ch in DOORS:
                    self.doors.setdefault(ch, []).append((r, c))
                elif ch.upper() in DOORS:     # a door's plate: the same letter, small
                    self.plates.setdefault(ch.upper(), []).append((r, c))

    def boulder_on(self, spot):
        return next((b for b in self.boulders if b["at"] == spot), None)

    def pressed(self, letter):
        """Plates of this door with something heavy on them right now."""
        stood_on = set(self.rovers.values())
        return [p for p in self.plates[letter] if p in self.sunk or p in stood_on]

    def door_open(self, letter):
        """A door stays open while something is in the doorway, so it can't
        shut on a rover or a boulder."""
        if letter in self.forced or len(self.pressed(letter)) == len(self.plates[letter]):
            return True
        return any(s in self.rovers.values() or self.boulder_on(s) for s in self.doors[letter])

    def done_for_good(self, letter):
        return letter in self.forced or all(p in self.sunk for p in self.plates[letter])

    def shut_door(self, spot):
        """The letter of the closed door on this square, if there is one."""
        ch = self.map[spot[0]][spot[1]]
        return ch if ch in DOORS and not self.door_open(ch) else None

    def crater(self, spot):
        return self.map[spot[0]][spot[1]] == "o" and spot not in self.filled

    def landing_spot(self, seat):
        """The nearest open ground to the lander with nobody on it, so a whole
        class spreads out and every name can be read. Never a plate or ♻,
        and never past a door."""
        taken = {spot for other, spot in self.rovers.items() if other != seat}
        seen, queue = set(self.starts), deque(self.starts)
        while queue:
            at = queue.popleft()
            if at not in taken and not self.boulder_on(at):
                return at
            for dr, dc in WAYS.values():
                step = (at[0] + dr, at[1] + dc)
                if step not in seen and self.map[step[0]][step[1]] in ".S@":
                    seen.add(step)
                    queue.append(step)
        return self.starts[seat % len(self.starts)]

    def enter(self, seat, now, spot=None):
        """A rover comes in, back where it was or on the lander."""
        self.began = self.began or now
        self.rovers[seat] = spot or self.landing_spot(seat)

    def leave(self, seat):
        """A rover goes. Returns where it was, for if it comes back."""
        return self.rovers.pop(seat, None)

    def say(self, text):
        self.news = (self.news + [text])[-NEWS_KEPT:]

    def roll(self, boulder, spot, name, now):
        """A pushed boulder arrives. Craters and plates swallow it."""
        boulder["at"], boulder["pushed"] = spot, now
        ch = self.map[spot[0]][spot[1]]
        if self.crater(spot):
            self.filled.add(spot)
            boulder["at"] = None
            self.say(f"🕳 {name} filled in a crater")
        elif ch.islower() and ch.upper() in self.plates and spot not in self.sunk:
            self.sunk.add(spot)
            boulder.update(at=None, plate=True)
            letter = ch.upper()
            self.say(f"🚪 {name} opened door {letter} for good!" if self.done_for_good(letter)
                     else f"🪨 {name} sank plate {letter}")

    def move(self, seat, way, name, now):
        """One square of driving. Returns a tip when the rover couldn't go."""
        r, c = self.rovers[seat]
        dr, dc = WAYS[way]
        to = (r + dr, c + dc)
        door = self.shut_door(to)
        if door:
            return f"Door {door} is shut. Something heavy on plate {door} opens it."
        if self.crater(to):
            return "That's a crater. Push a boulder into it to fill it in."
        if self.map[to[0]][to[1]] == "#":
            return ""
        boulder = self.boulder_on(to)
        if boulder:
            past = (to[0] + dr, to[1] + dc)
            if self.map[past[0]][past[1]] == "#" or self.shut_door(past) or self.boulder_on(past):
                return "That boulder can't go that way. Stuck? Drive onto ♻ in the landing room."
            self.roll(boulder, past, name, now)
            self.pushes += 1
        self.rovers[seat] = to
        self.steps += 1
        self.trail[to] = self.trail.get(to, 0) + 1
        if to == self.recycler:
            self.send_boulders_home(name, now)
        return None

    def send_boulders_home(self, name, now):
        """♻ Lost boulders go back where they started, even ones that went into
        a crater. One that was pushed lately is left alone, so someone using it
        doesn't lose it."""
        count = 0
        for b in self.boulders:
            if b["plate"] or b["at"] == b["home"] or now - b["pushed"] < BOULDER_REST:
                continue
            if not self.boulder_on(b["home"]):
                b["at"] = b["home"]
                count += 1
        if count:
            self.say(f"♻ {name} sent {count} lost boulder{'s' if count > 1 else ''} home")
        return count

    def shout(self, seat, key, now):
        self.shouted += 1
        self.shouts = [s for s in self.shouts if now - s[3] < SHOUT_LASTS]
        self.shouts.append([self.shouted, seat, SHOUTS[key], now])

    def go_home(self, seat):
        self.rovers[seat] = self.landing_spot(seat)

    def open_all(self):
        """The teacher opens every door and fills every crater: the way to end
        on a win if time runs out."""
        self.forced.update(self.doors)
        self.filled.update((r, c) for r, row in enumerate(self.map)
                           for c, ch in enumerate(row) if ch == "o")
        self.say("🔓 Mission control cleared the way")

    def reachable(self):
        """Squares the class can drive to for good from the lander. A door a
        rover is only holding doesn't count, and neither does a boulder, since
        a rover can always push or go round one."""
        seen, queue = set(self.starts), list(self.starts)
        while queue:
            r, c = queue.pop()
            for dr, dc in WAYS.values():
                spot = (r + dr, c + dc)
                ch = self.map[spot[0]][spot[1]]
                if spot in seen or ch == "#" or self.crater(spot) or (ch in DOORS and not self.done_for_good(ch)):
                    continue
                seen.add(spot)
                queue.append(spot)
        return seen

    def door_job(self, letter):
        plates, doors = self.plates[letter], self.doors[letter]
        count, pressed = len(plates), len(self.pressed(letter))
        friends = "a friend holds it" if count == 1 else "friends hold it"
        if pressed == count:
            to_vault = any((r + dr, c + dc) in self.vault for r, c in doors for dr, dc in WAYS.values())
            text = (f"Door {letter} is open while {friends}. Everyone drive through to the vault!" if to_vault else
                    f"Door {letter} is open while {friends}. Go through now! Then bring a boulder back "
                    f"onto the plate, so your friend can leave it.")
        elif count == 1:
            text = (f"Door {letter} is shut. Drive onto plate {letter} to hold it open for a friend, "
                    f"or push a boulder onto it to open it for good.")
        else:
            text = (f"Door {letter} needs all {count} of its plates pressed at once, and {pressed} "
                    f"{'is' if pressed == 1 else 'are'} pressed. Stand on one, or push a boulder onto it.")
        return {"text": text, "marks": [list(s) for s in doors + [p for p in plates if p not in self.sunk]]}

    def next_job(self):
        """What the class needs to do next, in plain words, and the squares to
        mark on the map. It goes by what's open for good, so it never sends
        anyone off to something that's already done."""
        if self.won:
            return None
        reach = self.reachable()
        if reach & self.vault:
            return {"text": "The way is clear! Everyone drive to the gold vault.", "marks": []}
        beside = []                       # squares just past the edge, and the way in
        for r, row in enumerate(self.map):
            for c, ch in enumerate(row):
                for dr, dc in WAYS.values():
                    if ch != "#" and (r, c) not in reach and (r - dr, c - dc) in reach:
                        beside.append(((r, c), (dr, dc)))
        doors = sorted({self.map[r][c] for (r, c), _ in beside if self.map[r][c] in DOORS})
        ready = [d for d in doors if all(p in reach or p in self.sunk for p in self.plates[d])]
        craters = [(s, way) for s, way in beside if self.crater(s)]
        if ready:
            return self.door_job(ready[0])
        if craters:
            wide = any(self.crater((r + dr, c + dc)) for (r, c), (dr, dc) in craters)
            text = ("Wide craters! Push boulders along one row, one after another, to make a bridge." if wide else
                    "A crater is in the way. Push a boulder into it to fill it in, then you can drive over it.")
            return {"text": text, "marks": [list(s) for s, _ in craters]}
        if doors:
            return self.door_job(doors[0])
        return {"text": "Look for a plate you haven't pressed yet.", "marks": []}

    def on_plate(self, spot):
        """The door this square holds, if a rover standing here is holding one."""
        ch = self.map[spot[0]][spot[1]]
        return ch.upper() if ch.islower() and ch.upper() in self.plates and spot not in self.sunk else None

    def your_job(self, seat):
        """The next job for one rover, so a whole class doesn't all do the same
        thing: whoever's on a plate stays there, and the closest rover that's
        free goes for the next one. None means the class's job is theirs too."""
        spot, job = self.rovers.get(seat), self.next_job()
        if not spot or not job:
            return None
        if spot in self.vault:
            return "🎉 You're in the vault! Stay here and cheer for your friends."
        holding = self.on_plate(spot)
        if holding:
            return f"✋ You're holding door {holding}. Stay here until your friends are through."
        reach = self.reachable()
        if spot not in reach:             # past a door: the plate on the lander's side is no use to them
            held = any(len(self.pressed(d)) == len(self.plates[d]) for d in self.doors if not self.done_for_good(d))
            return None if held else ("🚪 A door shut behind you. Press 🆘 Help so a friend comes to stand on "
                                       "its plate, or press 🏠 Back to the lander.")
        plates = [tuple(m) for m in job["marks"] if self.on_plate(tuple(m)) and tuple(m) not in self.rovers.values()]
        free = [s for s, at in self.rovers.items() if s != HELPER and at in reach and not self.on_plate(at)]
        if not plates:
            return None
        far = lambda at: min(abs(at[0] - p[0]) + abs(at[1] - p[1]) for p in plates)
        closest = min(free, key=lambda s: (far(self.rovers[s]), s))
        return f"👉 You're the closest rover, so go! {job['text']}" if closest == seat else None

    def helper_step(self):
        """The helper rover stands on the next plate that needs someone, and
        stays while it's holding one that's still needed."""
        job = self.next_job()
        plates = [tuple(m) for m in (job or {"marks": []})["marks"] if self.on_plate(tuple(m))]
        here = self.rovers.get(HELPER)
        if here in plates or not plates:
            return False
        free = [p for p in plates if p not in self.rovers.values()]
        if not free:
            return False
        self.rovers[HELPER] = free[0]
        return True

    def in_vault(self):
        return sum(spot in self.vault for seat, spot in self.rovers.items() if seat != HELPER)

    def needed(self):
        """Half the rovers here, so one kid off doing something else can't
        keep the class from finishing."""
        return max(1, math.ceil(len(set(self.rovers) - {HELPER}) / 2))

    def check_win(self, now):
        if not self.won and self.rovers and self.in_vault() >= self.needed():
            self.won = now
            self.say("🎉 The class did it together!")

    def view(self, now):
        """The moving parts of the map. Boulders stay in the same order, so a
        page can follow each one as it rolls."""
        recap = self.won and {"steps": self.steps, "pushes": self.pushes,
                              "trail": [[*spot, n] for spot, n in self.trail.items()]}
        return {"rovers": [[seat, *spot] for seat, spot in self.rovers.items()],
                "boulders": [b["at"] and list(b["at"]) for b in self.boulders],
                "filled": [list(s) for s in self.filled],
                "sunk": [list(s) for s in self.sunk],
                "doors": {letter: {"open": self.door_open(letter),
                                   "good": self.done_for_good(letter),
                                   "pressed": len(self.pressed(letter)),
                                   "plates": len(self.plates[letter])} for letter in self.doors},
                "pressed": [list(p) for letter in self.doors for p in self.pressed(letter)],
                "news": self.news, "in_vault": self.in_vault(), "needed": self.needed(),
                "job": self.next_job(), "recap": recap, "record": self.record,
                "shouts": [s[:3] for s in self.shouts if now - s[3] < SHOUT_LASTS],
                "secs": round((self.won or now) - self.began) if self.began else 0, "won": bool(self.won),
                "level": self.level, "levels": len(LEVELS), "name": LEVELS[self.level]["name"]}


# ---- 🤖 Code my rover ------------------------------------------------------------
# An extra for anyone who wants it: a short program that drives your rover on
# the map. It runs at once on a copy of the map, so look() is true to what's
# there now, and the page then drives the moves it made.

PILOT_STEPS = 60     # one program's moves, so nobody parks a rover on an endless loop
# It runs while the server holds its lock, so a stuck loop must end quickly or
# it stops the map for the whole class. This is about 20 ms, and plenty for 60 moves.
PILOT_BUDGET = 15_000
PILOT_PRINTS = 4     # print() lines shown beside the code
PILOT_WORDS = 'north(), south(), east(), west(), wait() and look("east")'


class _PilotStop(Exception):
    """The program has gone as far as it can."""


class PilotFloor(planet.Easel):
    """What a Pilot drives on: a copy of the map, where only this rover moves."""

    def __init__(self, game, seat):
        super().__init__()
        self.game, self.seat = copy.deepcopy(game), seat
        self.stopped = None

    def act(self, word, way=None):
        if len(self.steps) >= PILOT_STEPS:
            self.stopped = f"Your program stopped here, because one program can do {PILOT_STEPS} moves."
            raise _PilotStop()
        if word != "wait":
            tip = self.game.move(self.seat, word, "", 0)
            if tip is not None:
                self.stopped = f"Line {self.line} drives {word}, but your rover can't go that way. {tip}".rstrip()
                raise _PilotStop()
        self.steps.append(word)

    def look(self, way):
        game = self.game
        r, c = game.rovers[self.seat]
        spot = (r + WAYS[way][0], c + WAYS[way][1])
        ch = game.map[spot[0]][spot[1]]
        if ch == "#":
            return "rock"
        if game.shut_door(spot):
            return "door"
        if game.crater(spot):
            return "crater"
        if game.boulder_on(spot):
            return "boulder"
        if spot in game.vault:
            return "vault"
        return "plate" if ch.islower() and ch.upper() in game.plates else "ground"


class Pilot(planet.Rover):
    look_words = {"rock", "door", "crater", "boulder", "plate", "vault", "ground"}

    def __init__(self, code, world):
        super().__init__(code, world, {"look": None})
        self.budget = PILOT_BUDGET

    def call(self, node, frame):
        name = node.func.id if isinstance(node.func, ast.Name) else None
        if name != "look" and (name in planet.SENSOR_ZONE or name in planet.OWN_COMMANDS):
            raise planet.BotError(f"{name}() is for missions on the planet. On the team map "
                                  f"your rover knows {PILOT_WORDS}.")
        return super().call(node, frame)


def fly(game, seat, code):
    """Run a program for this rover. Returns the moves it makes, and why it
    stopped if it stopped early or couldn't run."""
    world = PilotFloor(game, seat)
    error = line = None
    try:
        Pilot(str(code), world).run()
    except _PilotStop:
        pass
    except planet._TooLong as e:
        error, line = str(e), e.line
    except planet.BotError as e:
        error, line = str(e), e.line or getattr(e, "syntax_line", None)
    except RecursionError:
        error = "Your functions call each other too deeply."
    return {"ways": world.steps, "stopped": world.stopped, "error": error, "line": line,
            "prints": world.prints[-PILOT_PRINTS:]}
