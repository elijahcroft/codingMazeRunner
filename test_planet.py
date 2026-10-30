import json
import os
import re
import tempfile
import threading
import unittest
from unittest import mock
from collections import deque
from functools import lru_cache
from urllib.request import Request, urlopen

import planet
import server

HERE = os.path.dirname(os.path.abspath(__file__))

COMPASS = ("north()", "south()", "east()", "west()")


def sites():
    for zi, zone in enumerate(planet.ZONES):
        for s in zone["sites"] if zone["key"] != "uncharted" else ():
            yield zi, zone, s


def site(key):
    # A practice site (easy mode) is found the planet's own way.
    return next(((zi, zone, s) for zi, zone, s in sites() if s["key"] == key), None) \
        or planet.find_site(key)


def run(key, code, variant=0):
    zi, zone, s = site(key)
    return planet.drive(code, s["variants"][variant], zone["rules"], zi)


@lru_cache(maxsize=None)   # several tests need the same site's route
def solve(key, variant):
    """The shortest list of compass commands that completes the mission,
    found by driving every sequence breadth first (fine for these small
    sites, which don't crumble). A tuple, since it's shared."""
    zi, zone, s = site(key)
    v = s["variants"][variant]
    samples = {(r, c) for r, row in enumerate(v["map"])
               for c, ch in enumerate(row) if ch == "*"}
    queue, seen = deque([[]]), set()
    while queue:
        actions = queue.popleft()
        for command in COMPASS:
            out = planet.drive("\n".join(actions + [command]), v, zone["rules"], zi)
            if out["reached"]:
                return tuple(actions + [command])
            last = out["frames"][-1]
            got = frozenset(samples & {(f["r"], f["c"]) for f in out["frames"]})
            state = (last["r"], last["c"], got, out["ticks"] % 60
                     if "wind" in zone["rules"] else 0)
            if out["end"] == "stopped" and state not in seen:
                seen.add(state)
                queue.append(actions + [command])
    return None


def reach(key, variant, square):
    """The shortest list of moves (compass commands, and jumps once they've
    arrived) that drives over `square`, breadth first. A shortest route never
    crosses its own tracks, so crumbling ground needs nothing extra."""
    zi, zone, s = site(key)
    v = s["variants"][variant]
    moves = list(COMPASS)
    if zi >= planet.SENSOR_ZONE["jump"]:
        moves += [f'jump("{w}")' for w in planet.COMPASS]
    if v.get("drills"):
        moves += [f'drill("{w}")' for w in planet.COMPASS]
    queue, seen = deque([[]]), set()
    while queue:
        actions = queue.popleft()
        for move in moves:
            out = planet.drive("\n".join(actions + [move]), v, zone["rules"], zi)
            if any((f["r"], f["c"]) == tuple(square) for f in out["frames"]):
                return actions + [move]
            last = out["frames"][-1]
            state = (last["r"], last["c"], out["ticks"] % v["wind"] if v.get("wind") else 0,
                     last.get("k"), sum("g" in f for f in out["frames"]))
            if out["end"] == "stopped" and state not in seen:
                seen.add(state)
                queue.append(actions + [move])
    return None


def as_code(route):
    """A list of commands as code, runs of the same one joined: east(3)."""
    lines = []
    for a in route:
        if lines and lines[-1][0] == a and a.endswith("()"):
            lines[-1][1] += 1
        else:
            lines.append([a, 1])
    return "".join((a if n == 1 else f"{a[:-1]}{n})") + "\n" for a, n in lines)


def replay_as_code(out):
    """The commands a run did (for sites without ice, wind or portals, where
    every frame is one command)."""
    route = []
    for a, b in zip(out["frames"], out["frames"][1:]):
        way = COMPASS[[0, 2, 1, 3].index(b["d"])]
        if b.get("e") == "wait":
            route.append("wait()")
        elif b.get("e") == "jump":
            route.append(f'jump("{way[:-2]}")')
        elif b.get("e") == "drill":
            route.append(f'drill("{way[:-2]}")')
        elif b.get("e") not in ("goal", "fell"):
            route.append(COMPASS[[0, 2, 1, 3].index(b["d"])])
    return as_code(route)


def wind_program(gust, legs=((2, 5), (1, 7), (2, 4), (1, 3), (2, 7))):
    """The 3C answer for one gust number, along one ridge's legs."""
    calls = [("go_south" if d == 2 else "go_east") + f"({n})" for d, n in legs]
    return (f"GUST = {gust}\n\ndef guard():\n    if tick() % GUST == GUST - 1:\n"
            f"        wait()\n\ndef go_south(n):\n    for i in range(n):\n"
            f"        guard()\n        south()\n\ndef go_east(n):\n"
            f"    for i in range(n):\n        guard()\n        east()\n\n"
            + "\n".join(calls) + "\n")


# Programs that earn a bonus star the reference program doesn't.
BONUS_PROGRAMS = {
    "1a": "south(2)\neast()\nsouth()\neast(4)\nnorth(2)\neast(2)\nnorth()\n"
          "east(2)\nsouth(4)\nwest()\n",
    "1b": "def step():\n    east()\n    south()\n\nfor i in range(8):\n    step()\n",
    "2b": "north()\neast()\nsouth()\neast()\nnorth()\nsouth()\nwest()\n",
    "6a": "south(2)\nnorth()\nsouth(2)\nnorth()\nwest(2)\nnorth(2)\neast(2)\n",
    "6b": "south(2)\neast()\nsouth(2)\nnorth(2)\neast()\n",
    "8a": 'for i in range(4):\n    jump("east")\n',
    "8b": 'def hop():\n    east()\n    jump("east")\n\nfor i in range(5):\n    hop()\neast()\n',
    "9c": "def step():\n    east()\n    south()\n\nfor i in range(5):\n    step()\n",
    "13c": 'def hop():\n    east(2)\n    jump("east")\n\nfor i in range(4):\n    hop()\neast()\n',
    "15c": "def trip(n):\n    south(n)\n    east(6)\n    west(6)\n    north(n)\n\n"
           "for i in range(4):\n    trip(i)\n",
    "16a": 'east(3)\ndrill("east")\neast(10)\nsouth(2)\nwest(8)\n',
}


def answer_program(key, i):
    """The program a C site with no reference is solved by."""
    s = site(key)[2]
    if key == "3c":
        v = s["variants"][i]
        return wind_program(v["wind"], v["legs"])
    return as_code(solve(key, i))


class StarTests(unittest.TestCase):
    def earn(self, key, code, i):
        zi, zone, s = site(key)
        v = s["variants"][i]
        return planet.stars(s, v, planet.drive(code, v, zone["rules"], zi), code)

    def test_every_star_on_every_planet_can_be_earned(self):
        for zi, zone, s in sites():
            for i, v in enumerate(s["variants"]):
                programs = [s["reference"] or answer_program(s["key"], i)]
                if s["key"] in BONUS_PROGRAMS:
                    programs.append(BONUS_PROGRAMS[s["key"]])
                earned = [any(star) for star in zip(*(self.earn(s["key"], p, i)
                                                      for p in programs))]
                self.assertEqual(earned, [True, True, True], (s["key"], i))

    def test_every_star_past_the_mission_has_a_hint(self):
        for zi, zone, s in sites():
            for v in s["variants"]:
                tips = planet.star_tips(s, v)
                self.assertIsNone(tips[0])
                self.assertTrue(all(isinstance(t, str) and "{" not in t for t in tips[1:]),
                                s["key"])

    def test_the_bonus_takes_something_extra(self):
        # The plain answer misses these bonuses: they need a detour, a def,
        # or a quicker way through the pads.
        for key in BONUS_PROGRAMS:
            self.assertFalse(self.earn(key, site(key)[2]["reference"], 0)[1], key)

    def test_a_typed_in_number_misses_the_computed_star(self):
        for key, typed in (("2a", "east()\nreport(5)\n"),
                           ("3a", "south(4)\nreport(4)\n"),
                           ("5a", "report(2)\n"),
                           ("7a", "report(9)\n")):
            self.assertEqual(self.earn(key, typed, 0)[:2], [True, False], key)
            self.assertEqual(self.earn(key, site(key)[2]["reference"], 0)[:2],
                             [True, True], key)

    def test_1c_counting_your_own_rocks_misses_the_look_star(self):
        # Every student who solved 1C counted squares off their own map.
        zi, zone, s = site("1c")
        counted = as_code(solve("1c", 0))
        self.assertEqual(self.earn("1c", counted, 0)[:2], [True, False])
        out = planet.drive(s["reference"], s["variants"][0], zone["rules"], zi)
        self.assertTrue(planet.stars(s, s["variants"][0], out, s["reference"])[1])
        self.assertIn("🌍 the same code collected every sample on 8 of the 8 rock runs",
                      out["log"][-1])

    def test_the_def_star_wants_a_def_that_runs(self):
        route = "for i in range(8):\n    east()\n    south()\n"
        self.assertFalse(self.earn("1b", "def spare():\n    wait()\n" + route, 0)[1])
        self.assertEqual(self.earn("1b", BONUS_PROGRAMS["1b"], 0)[:2], [True, True])

    def test_no_stars_without_the_mission(self):
        self.assertEqual(self.earn("1a", "south(2)\neast()\n", 0), [False, False, False])

    def test_compact_counts_lines_that_do_something(self):
        self.assertEqual(planet.code_lines("# plan\neast(3)\n\n   \nsouth()  # go\n"), 2)

    def test_every_site_shows_three_goals(self):
        for _, _, s in sites():
            for v in s["variants"]:
                self.assertEqual(len(planet.goals(s, v)), 3)

    def test_the_first_goal_names_the_mission(self):
        for key, first in (("1a", "🧪 Collect every sample"),
                           ("2a", "📡 Report the right number"),
                           ("2b", "🛰 Reach the beacon")):
            s = site(key)[2]
            self.assertEqual(planet.goals(s, s["variants"][0])[0], first)


class SiteClaims(unittest.TestCase):
    def test_maps_are_rectangles_with_one_start(self):
        for _, _, s in sites():
            for v in s["variants"]:
                width = len(v["map"][0])
                self.assertTrue(all(len(row) == width for row in v["map"]), s["key"])
                text = "".join(v["map"])
                # The lander, or home when the rover starts there.
                self.assertEqual(text.count("S") + text.count("H"), 1, s["key"])
                self.assertLessEqual(text.count("G"), 1, s["key"])
                # Every site has something to do.
                self.assertTrue("G" in text or "*" in text or "answer" in v, s["key"])

    def test_no_site_is_a_maze_of_corridors(self):
        # This isn't the maze game: the opening sites are open ground,
        # where most squares have three or four open neighbours.
        for key in ("1a", "1b", "1c", "2a", "3a", "4c", "7b", "7c"):
            for v in site(key)[2]["variants"]:
                grid = v["map"]
                open_ = [(r, c) for r, row in enumerate(grid)
                         for c, ch in enumerate(row) if ch != "#"]
                roomy = sum(sum(grid[r + dr][c + dc] != "#" for dr, dc in planet.DIRS) >= 3
                            for r, c in open_)
                self.assertGreater(roomy / len(open_), .5, key)

    def test_every_reference_clears_every_variant(self):
        for zi, zone, s in sites():
            if not s["reference"]:
                continue
            for i in range(len(s["variants"])):
                out = run(s["key"], s["reference"], i)
                self.assertTrue(out["reached"], (s["key"], i, out["log"][-3:],
                                                 out["error"]))

    def test_every_site_without_a_reference_can_be_solved(self):
        for key in ("2c", "3c", "6c"):
            for i in range(len(site(key)[2]["variants"])):
                self.assertTrue(run(key, answer_program(key, i), i)["reached"], (key, i))

    def test_the_maze_games_commands_say_what_to_use_instead(self):
        for code, says in (("move(3)\n", "drives by compass"),
                           ("turn_right()\n", "drives by compass"),
                           ("if wall_ahead():\n    east()\n", 'look("east") == "rock"'),
                           ("while not at_goal():\n    east()\n", "at_beacon()")):
            self.assertIn(says, run("1a", code)["error"], code)
        out = run("1a", "def move():\n    east()\nmove()\n")
        self.assertIsNone(out["error"])   # their own move() is fine

    # ---- Zone 1 ----
    def test_1a_a_route_collects_the_samples(self):
        out = run("1a", site("1a")[2]["reference"])
        self.assertEqual(out["log"][-1], "tick 16: 🎉 every sample collected")
        self.assertIn("🧪 sample collected, 2 left", out["log"][0])

    def test_1b_typing_the_steps_out_isnt_compact(self):
        typed = "east()\nsouth()\n" * 8
        zi, zone, s = site("1b")
        self.assertEqual(planet.stars(s, s["variants"][0], run("1b", typed), typed),
                         [True, False, False])

    def test_1c_a_counted_route_misses_the_compact_star(self):
        zi, zone, s = site("1c")
        route = as_code(solve("1c", 0))
        out = run("1c", route)
        self.assertEqual(planet.stars(s, s["variants"][0], out, route)[::2], [True, False])

    def test_1c_counting_only_works_on_your_own_planet(self):
        variants = site("1c")[2]["variants"]
        for i in range(len(variants)):
            # The reference's moves typed out: a route counted off map i.
            route = replay_as_code(run("1c", site("1c")[2]["reference"], i))
            self.assertTrue(run("1c", route, i)["reached"])
            for j in range(len(variants)):
                if j != i:
                    self.assertFalse(run("1c", route, j)["reached"], (i, j))

    # ---- Zone 2 ----
    def test_2a_one_east_slides_and_the_log_doesnt_say_how_far(self):
        for i, v in enumerate(site("2a")[2]["variants"]):
            out = run("2a", "east()\n", i)
            self.assertEqual(out["frames"][-1]["c"] - out["frames"][0]["c"], v["answer"])
            self.assertTrue(any("⛸" in line for line in out["log"]))
            self.assertFalse(any(str(v["answer"]) in line.split(":", 1)[1]
                                 for line in out["log"]))

    def test_the_first_lessons_number_is_named_as_the_old_one(self):
        # Everyone typed report(6) on 2A in the first lesson; no planet has it now.
        for key, drive, old in (("2a", "east()\n", 6), ("3a", "south(16)\n", 5), ("7a", "", 12)):
            for i, v in enumerate(site(key)[2]["variants"]):
                self.assertNotEqual(v["answer"], old, key)
                out = run(key, drive + f"report({old})\n", i)
                self.assertEqual(out["end"], "wrong", key)
                self.assertIn("before every planet got its own", out["log"][-1])
                self.assertIn("before every planet got its own", out["explain"]["what"])
                self.assertTrue(out["explain"]["copied"])   # the coach leads with it
        # Found by the code, it's only wrong: Gl1tchXD's report(y()) landed on 5.
        out = run("3a", "while y() != 5:\n    south()\nreport(y())\n", 1)
        self.assertNotIn("copied", out["explain"])

    def test_a_reading_sent_as_it_is_says_to_send_the_change(self):
        out = run("5a", "east()\nwait()\nreport(battery())\n")
        self.assertIn("You reported battery() as it was", out["explain"]["what"])
        self.assertIn("before = battery()", out["explain"]["next"])
        self.assertTrue(out["explain"]["lead"])     # the coach leads with it
        self.assertIn("not how much it changed", out["log"][-1])
        self.assertIn("take the rover's x() away", run("7a", "report(beacon_x())\n")["explain"]["next"])
        # A reading that is the answer still completes it: 3A's report(tick()).
        self.assertTrue(run("3a", "while x() == 2:\n    south()\nreport(tick())\n")["reached"])

    def test_a_classmates_measurement_is_wrong_on_your_planet(self):
        # Every student measures their own number, so copying one fails.
        for key, drive in (("2a", "east()\n"), ("3a", "south(16)\n"), ("7a", "")):
            variants = site(key)[2]["variants"]
            self.assertTrue(site(key)[2]["per_student"])
            self.assertEqual(len({v["answer"] for v in variants}), len(variants), key)
            for i, v in enumerate(variants):
                for j in range(len(variants)):
                    if j != i:
                        out = run(key, drive + f"report({v['answer']})\n", j)
                        self.assertEqual(out["end"], "wrong", (key, i, j))
                        # ...and the rover says whose number it is.
                        self.assertIn("someone else's planet", out["log"][-1])
                        self.assertTrue(out["explain"]["copied"])
            # A number nobody has is just wrong.
            out = run(key, drive + "report(1000)\n")
            self.assertNotIn("copied", out["explain"])

    def test_2a_a_wrong_report_ends_the_run(self):
        out = run("2a", "east()\nreport(3)\nreport(5)\n")
        self.assertEqual(out["end"], "wrong")
        self.assertIn("measured something different", out["log"][-1])

    def test_2a_no_report_is_no_mission(self):
        out = run("2a", "east()\n")
        self.assertEqual((out["end"], out["log"][-1]),
                         ("stopped", "tick 1: 🏁 program ended without a report()"))

    def test_2b_the_beacon_is_close_but_needs_six_slides(self):
        self.assertEqual(len(solve("2b", 0)), 6)
        self.assertFalse(run("2b", "east(2)\n")["reached"])

    def test_2c_each_lake_needs_its_own_plan(self):
        routes = [solve("2c", i) for i in range(len(site("2c")[2]["variants"]))]
        for i, route in enumerate(routes):
            self.assertGreaterEqual(len(route), 7)
            for j in range(len(routes)):
                if j != i:
                    self.assertFalse(run("2c", "\n".join(route), j)["reached"], (i, j))

    # ---- Zone 3 ----
    def test_3a_driving_south_shows_the_gusts(self):
        # The brief's south(16) shows at least two pushes on every planet.
        for i, v in enumerate(site("3a")[2]["variants"]):
            n = v["answer"]
            out = run("3a", "south(16)\n", i)
            pushes = [line for line in out["log"] if "💨" in line]
            self.assertEqual(pushes[:2], [f"tick {n}: 💨 gust pushed the rover east",
                                          f"tick {2 * n}: 💨 gust pushed the rover east"])
            self.assertTrue(run("3a", f"south(16)\nreport({n})\n", i)["reached"])

    def test_3b_hand_counted_squares_fall(self):
        out = run("3b", "south(6)\neast(5)\nsouth(6)\neast(4)\nsouth(5)\n")
        self.assertEqual(out["end"], "fell")

    def test_3c_a_neighbours_gust_number_falls(self):
        variants = site("3c")[2]["variants"]
        for i, v in enumerate(variants):
            for j, other in enumerate(variants):
                if v["wind"] != other["wind"]:
                    out = run("3c", wind_program(other["wind"], v["legs"]), i)
                    self.assertEqual(out["end"], "fell", (i, j))
        # 3B's answer, every 5 ticks, works on nobody's ridge.
        for i, v in enumerate(variants):
            self.assertFalse(run("3c", wind_program(5, v["legs"]), i)["reached"], i)

    def test_the_wind_hints_loop_earns_every_star(self):
        # The ✂️ hint on 3B and 3C: one loop that picks a move every tick.
        loop = ("while not at_beacon():\n    if tick() % {0} == {1}:\n        wait()\n"
                '    elif look("south") != "rock":\n        south()\n    else:\n'
                "        east()\n")
        for key in ("3b", "3c"):
            zi, zone, s = site(key)
            for i, v in enumerate(s["variants"]):
                code = loop.format(v["wind"], v["wind"] - 1)
                self.assertEqual(planet.stars(s, v, run(key, code, i), code),
                                 [True, True, True], (key, i))

    # ---- Zone 4 ----
    def test_4a_in_and_out_the_same_way_falls(self):
        out = run("4a", "east(4)\nsouth(3)\nnorth(3)\n")
        self.assertEqual(out["end"], "fell")

    def test_4a_the_beacon_wants_the_sample(self):
        out = run("4a", "east(8)\n")
        self.assertFalse(out["reached"])
        self.assertTrue(any("needs every sample" in line for line in out["log"]))

    def test_4c_driving_round_the_edge_comes_back_round_and_falls(self):
        edge = "while samples_left() > 0:\n" + "".join(
            f'    while look("{w}") != "rock":\n        {w}()\n'
            for w in ("east", "south", "west", "north"))
        for i in range(len(site("4c")[2]["variants"])):
            self.assertEqual(run("4c", edge, i)["end"], "fell", i)

    def test_4c_a_hand_route_is_long_and_only_fits_your_field(self):
        # Row by row: down to the next sample's row, then across to it.
        zi, zone, s = site("4c")
        routes = []
        for v in s["variants"]:
            r = c = 1
            route = []
            for sr, sc in sorted((r_, c_) for r_, row in enumerate(v["map"])
                                 for c_, ch in enumerate(row) if ch == "*"):
                route += ["south()"] * (sr - r) + \
                         ["east()" if sc > c else "west()"] * abs(sc - c)
                r, c = sr, sc
            routes.append(as_code(route))
        for i, route in enumerate(routes):
            self.assertTrue(run("4c", route, i)["reached"], i)
            self.assertGreater(planet.code_lines(route), s["compact"], i)
            for j in range(len(routes)):
                if j != i:
                    self.assertFalse(run("4c", route, j)["reached"], (i, j))

    def test_4c_cracks_look_like_cracks(self):
        out = run("4c", 'east()\nwest()\n')
        self.assertEqual(out["end"], "fell")
        out = run("4c", 'east()\nprint(look("west"))\n')
        self.assertEqual(out["prints"][0]["text"], "crack")

    # ---- Zone 5 ----
    def test_5a_waiting_in_the_sun_charges(self):
        out = run("5a", "east()\nprint(battery())\nwait()\nprint(battery())\n")
        self.assertEqual([p["text"] for p in out["prints"]], ["13", "15"])

    def test_5b_driving_straight_through_runs_flat(self):
        self.assertEqual(run("5b", "east(12)\nsouth(5)\nwest(16)\nsouth(5)\n"
                                   "east(20)\n")["end"], "battery")

    def test_5c_one_charge_stop_is_never_enough(self):
        for i in range(len(site("5c")[2]["variants"])):
            for steps in range(1, 12):
                code = f"east({steps})\nwhile battery() < 100 and in_sun():\n" \
                       f"    wait()\neast({40 - steps})\n"
                self.assertFalse(run("5c", code, i)["reached"], (i, steps))

    def test_5c_no_hard_coded_plan_works_on_every_planet(self):
        n = len(site("5c")[2]["variants"])
        for i in range(n):
            mine = replay_as_code(run("5c", site("5c")[2]["reference"], i))
            self.assertTrue(run("5c", mine, i)["reached"])
            self.assertFalse(all(run("5c", mine, j)["reached"] for j in range(n)), i)

    # ---- Zone 6 ----
    def test_6a_6b_the_beacon_is_walled_off(self):
        for key in ("6a", "6b"):
            self.assertFalse(run(key, 'while look("east") != "rock":\n    east()\n'
                                      "south(2)\neast(2)\n")["reached"], key)

    def test_6c_every_wiring_needs_two_trips_and_its_own_route(self):
        routes = [solve("6c", i) for i in range(len(site("6c")[2]["variants"]))]
        for i, route in enumerate(routes):
            out = run("6c", "\n".join(route), i)
            self.assertGreaterEqual(sum("✨" in line for line in out["log"]), 2, i)
            for j in range(len(routes)):
                if j != i:
                    self.assertFalse(run("6c", "\n".join(route), j)["reached"], (i, j))

    # ---- Zone 7 ----
    def test_7a_the_beacon_sensors_say_where_it_is(self):
        out = run("7a", "print(x(), y(), beacon_x(), beacon_y())\n")
        self.assertEqual(out["prints"][0]["text"], "1 2 10 2")

    def test_7b_7c_a_route_only_fits_your_own_plain(self):
        for key in ("7b", "7c"):
            zi, zone, s = site(key)
            for i, v in enumerate(s["variants"]):
                route = replay_as_code(run(key, s["reference"], i))
                out = run(key, route, i)
                # A route earns the mission, but not the 🌍 star.
                self.assertEqual(planet.stars(s, v, out, route)[:2], [True, False], (key, i))
                self.assertIn("🌍 the same code reached the beacon on 1 of the 8",
                              out["log"][-1], (key, i))

    def test_7c_needs_safe_ground_and_going_round(self):
        ref = site("7c")[2]["reference"]
        side = '    elif safe("south"):\n        south()\n    else:\n        north()\n'
        self.assertIn(side, ref)
        for name, code in (("7b's steering", site("7b")[2]["reference"]),
                           ("craters", ref.replace(' and look(way) != "crater"', "")),
                           ("going round", ref.replace(side, ""))):
            for i in range(len(site("7c")[2]["variants"])):
                self.assertFalse(run("7c", code, i)["reached"], (name, i))

    def test_uncharted_is_7cs_program_with_the_old_rules_added(self):
        ready = "    ready()\n"
        self.assertIn(ready, planet.UNCHARTED_REFERENCE)
        self.assertTrue(planet.UNCHARTED_REFERENCE.replace(ready, "").endswith(
            site("7c")[2]["reference"].split("\n\n", 1)[1]))


    # ---- Zone 8 ----
    def test_jump_leaps_two_squares_over_anything(self):
        out = run("8b", 'east()\njump("east")\neast()\njump("east")\n')
        self.assertEqual((out["frames"][-1]["c"], out["ticks"]), (7, 4))
        self.assertIn("tick 2: 🦘 jumped east", out["log"])
        self.assertEqual(out["frames"][2]["e"], "jump")

    def test_a_jump_needs_ground_to_land_on(self):
        out = run("8b", 'east()\njump("east")\njump("east")\n')   # x 6 is rock
        self.assertEqual(out["frames"][-1]["c"], 4)
        self.assertIn("a jump can't land on rock", out["log"][-2])
        self.assertEqual(run("8b", 'jump("east")\n')["end"], "fell")   # into the trench at x 3
        self.assertEqual(run("8a", "east(8)\n")["end"], "fell")       # and walking falls in too

    def test_jump_arrives_in_crater_hops(self):
        self.assertIn("Crater Hops", run("7c", 'jump("east")\n')["error"])
        self.assertIn('jump("east")', run("8a", "jump()\n")["error"])
        self.assertIn('jump("east")', run("8a", 'jump("up")\n')["error"])

    def test_8c_a_route_only_fits_your_own_field(self):
        zi, zone, s = site("8c")
        for i, v in enumerate(s["variants"]):
            route = replay_as_code(run("8c", s["reference"], i))
            out = run("8c", route, i)
            self.assertEqual(planet.stars(s, v, out, route)[:2], [True, False], i)
            self.assertIn("🌍 the same code reached the beacon on 1 of the 8 fields",
                          out["log"][-1], i)

    def test_8c_jumping_at_anything_but_ground_overshoots_the_beacon(self):
        code = ('while not at_beacon():\n    if look("east") != "ground":\n'
                '        jump("east")\n    else:\n        east()\n')
        for i in range(len(site("8c")[2]["variants"])):
            out = run("8c", code, i)
            self.assertFalse(out["reached"], i)


    # ---- Zones 9 to 12: one new thing each, told and drawn ----
    def test_every_new_zone_says_what_is_new(self):
        for key in ("belts", "drill", "gates", "relay"):
            zone = next(z for z in planet.ZONES if z["key"] == key)
            self.assertEqual(len(zone["sites"]), 5, key)   # A to D, and a mix
            self.assertEqual(set(zone["new"]), {"icon", "what", "example"}, key)
            self.assertEqual(len(zone["hints"]), 3, key)
            # The A site is a try-it: its reference is a line or three.
            self.assertLessEqual(planet.code_lines(zone["sites"][0]["reference"]), 3, key)

    def test_each_zone_needs_its_new_thing(self):
        # The last zone's final program fails on this zone's last site.
        for key, before in (("9d", "8c"), ("10d", "9d"), ("11d", "10d"), ("12d", "11d")):
            code = site(before)[2]["reference"]
            for i in range(8):
                self.assertFalse(run(key, code, i)["reached"], (key, i))

    def test_new_d_sites_a_route_only_fits_your_own(self):
        for key in ("9d", "10d", "11d", "12d"):
            zi, zone, s = site(key)
            fits = 0
            for i in range(8):
                route = replay_as_code(run(key, s["reference"], i))
                self.assertTrue(run(key, route, i)["reached"], (key, i))
                fits += sum(run(key, route, j)["reached"] for j in range(8) if j != i)
            self.assertLessEqual(fits / 56, .15, key)

    def test_a_belt_carries_the_rover_to_its_end(self):
        out = run("9a", "east(2)\n")
        self.assertTrue(out["reached"])
        self.assertEqual(out["ticks"], 2)       # the ride is part of one move
        self.assertIn("tick 2: 🛤 a belt carried the rover to x 1, y 4", out["log"])
        self.assertEqual(run("9a", 'east()\nprint(look("east"))\n')["prints"][0]["text"], "belt")

    def test_the_wrong_belt_runs_into_a_crater(self):
        out = run("9b", "east()\n")
        self.assertEqual(out["end"], "fell")
        self.assertIn("belt carried the rover into a crater", out["explain"]["what"])

    def test_9c_is_1bs_loop_on_belts(self):
        self.assertEqual(site("9c")[2]["reference"], site("1b")[2]["reference"].replace("8", "5"))

    def test_drill_turns_rock_into_ground(self):
        out = run("10a", 'east(3)\ndrill("east")\nprint(drills_left())\n')
        self.assertIn("tick 4: ⛏ drilled through the rock, 0 drills left", out["log"])
        self.assertEqual(out["frames"][-1]["g"], [2, 5])
        self.assertEqual(out["prints"][0]["text"], "0")
        out = run("10a", 'east(3)\ndrill("east")\ndrill("east")\n')
        self.assertIn("⛏ nothing to drill there", out["log"][-2])
        out = run("10b", 'east(2)\ndrill("east")\neast(4)\ndrill("east")\neast(4)\n'
                         'drill("east")\neast(3)\n')
        self.assertIn("tick 13: ⛏ no drills left", out["log"])
        self.assertIn("ran out of drills", out["explain"]["what"])
        self.assertIn('drill("east")', run("10a", 'drill("up")\n')["error"])

    def test_10b_drilling_the_wall_with_a_gap_leaves_too_few(self):
        out = run("10b", 'east(2)\ndrill("east")\neast(4)\ndrill("east")\neast(4)\n'
                         'drill("east")\neast(3)\n')
        self.assertFalse(out["reached"])

    def test_10d_thick_rock_cant_be_jumped(self):
        jump = ('while not at_beacon():\n    if look("east") != "ground" and look("east") != "beacon":\n'
                '        jump("east")\n    else:\n        east()\n')
        for i in range(8):
            self.assertFalse(run("10d", jump, i)["reached"], i)

    def test_a_gate_needs_a_key(self):
        out = run("11b", "east(9)\n")
        self.assertFalse(out["reached"])
        self.assertIn("🔒 the gate at x 6, y 3 is locked", out["log"][0])
        self.assertIn("Pick up the key at x 3, y 1 first", out["explain"]["next"])
        out = run("11b", 'north(2)\neast(2)\nprint(has_key(), look("south"))\nsouth(2)\n'
                         'east(3)\nprint(has_key())\n')
        self.assertEqual([p["text"] for p in out["prints"]], ["True ground", "False"])
        self.assertIn("tick 9: 🚪 the key opened the gate", out["log"])
        self.assertEqual(run("11a", 'east()\nprint(look("east"))\n')["prints"][0]["text"], "key")
        # A gate is too tall to jump over.
        self.assertIn("too tall", run("11a", 'east(4)\njump("east")\n')["log"][-2])

    def test_flags_count_only_in_order(self):
        out = run("12b", "north()\n" * 0 + "east(5)\nprint(flags_left(), next_x(), next_y())\n")
        self.assertIn("🚩 that's flag 3: flag 1 comes first", out["log"][0])
        self.assertEqual(out["prints"][0]["text"], "4 2 3")
        self.assertIn("Flag 1 is next, at x 2, y 3", out["explain"]["next"])
        out = run("12a", "east(11)\nprint(next_x(), next_y())\n")
        self.assertEqual(out["prints"][0]["text"], "10 3")   # every flag done: the beacon

    def test_12c_go_to_in_a_loop_is_compact(self):
        zi, zone, s = site("12c")
        v = s["variants"][0]
        route = replay_as_code(run("12c", s["reference"]))
        self.assertGreater(planet.code_lines(route), s["compact"])
        self.assertTrue(planet.stars(s, v, run("12c", s["reference"]), s["reference"])[2])

    # ---- Zones 13 to 15: push, measure, carry ----
    def test_13_to_15_each_zone_needs_its_new_thing(self):
        for key, before in (("13d", "12d"), ("14d", "13d"), ("15d", "14d")):
            code = site(before)[2]["reference"]
            for i in range(8):
                self.assertFalse(run(key, code, i)["reached"], (key, i))
        for key in ("push", "laser", "cargo"):
            zone = next(z for z in planet.ZONES if z["key"] == key)
            self.assertEqual(len(zone["sites"]), 5, key)   # A to D, and a mix
            self.assertEqual(set(zone["new"]), {"icon", "what", "example"}, key)
            self.assertLessEqual(planet.code_lines(zone["sites"][0]["reference"]), 3, key)

    def test_13_to_15_a_route_only_fits_your_own(self):
        for key in ("13d", "14d", "15d"):
            zi, zone, s = site(key)
            fits = 0
            for i in range(8):
                route = replay_as_code(run(key, s["reference"], i))
                self.assertTrue(run(key, route, i)["reached"], (key, i))
                fits += sum(run(key, route, j)["reached"] for j in range(8) if j != i)
            self.assertLessEqual(fits / 56, .15, key)

    # ---- Zone 16: everything at once ----
    def test_16d_needs_every_zone_before_it(self):
        # Each earlier zone's final program misses: 16D takes them together.
        for before in ("9d", "10d", "13d", "14d", "15d"):
            code = site(before)[2]["reference"]
            for i in range(8):
                self.assertFalse(run("16d", code, i)["reached"], (before, i))

    def test_16d_a_route_only_fits_your_own(self):
        s = site("16d")[2]
        fits = 0
        for i in range(8):
            route = replay_as_code(run("16d", s["reference"], i))
            self.assertTrue(run("16d", route, i)["reached"], i)
            fits += sum(run("16d", route, j)["reached"] for j in range(8) if j != i)
        self.assertLessEqual(fits / 56, .15)

    def test_16a_the_key_comes_before_the_one_way_belt(self):
        out = run("16a", 'east(3)\ndrill("east")\neast(3)\nsouth(2)\nwest(8)\n')
        self.assertIn("locked", out["explain"]["what"] + out["explain"]["next"])
        # Drilling straight down from the lander needs more drills than there are.
        self.assertFalse(run("16a", 'south(4)\ndrill("south")\nsouth(2)\neast(5)\n')["reached"])

    def test_16b_only_one_boulder_reaches_the_trench(self):
        out = run("16b", "south()\neast(5)\n")
        self.assertIn("🪨 the boulder won't move: something is behind it", "\n".join(out["log"]))

    def test_16c_counted_squares_fall_in(self):
        out = run("16c", "for i in range(4):\n    south(i)\n    east(14)\n    west(14)\n    north(i)\n")
        self.assertEqual(out["end"], "fell")

    # ---- The mixes that end Zones 8 to 15 ----
    def test_every_mix_has_more_than_one_way_through(self):
        # Each way uses something different; every one completes the mission.
        ways = {
            "8d": ['for i in range(3):\n    east()\n    jump("east")\nsouth(2)\neast()\n',
                   "south(3)\nnorth()\nwest()\n"],
            "9e": ['east()\njump("east")\nsouth(3)\neast()\n', "south(4)\neast(11)\nnorth()\n"],
            "10e": ['east(4)\ndrill("east")\neast(6)\n', "south(3)\nnorth(2)\n"],
            "11e": ['south()\neast(5)\ndrill("south")\nsouth(2)\n',
                    "east(10)\nsouth(4)\nwest(4)\nnorth()\nwest()\n"],
            "12e": ["east(5)\nwest(5)\nsouth(4)\neast(11)\n",
                    "east(5)\nwest(5)\nsouth(4)\nnorth(2)\neast(2)\n"],
            "13e": ['east(4)\njump("east")\neast(4)\n',
                    'south(3)\neast(3)\ndrill("east")\neast()\ndrill("east")\neast(2)\n'
                    "north(3)\neast(4)\n"],
            "14e": ['east(distance("east"))\neast()\neast(distance("east"))\njump("east")\n'
                    'east(distance("east"))\n', 'east(11)\njump("east")\neast(2)\n'],
            "15e": ['east(4)\njump("east")\neast(4)\nsouth(3)\nnorth(3)\n',
                    'east(4)\njump("east")\neast(4)\nsouth(2)\nwest(4)\njump("west")\n'
                    "west(4)\nnorth(2)\n"],
        }
        self.assertEqual(set(ways), {s["key"] for s in planet.MIX_SITES.values()})
        for key, codes in ways.items():
            for code in codes:
                self.assertTrue(run(key, code)["reached"], (key, code))
            zone = next(z for z in planet.ZONES if key in [s["key"] for s in z["sites"]])
            self.assertEqual(zone["sites"][-1]["key"], key)   # last in its zone

    def test_a_boulder_is_pushed_and_fills_a_crater(self):
        out = run("13a", "east(4)\n")
        self.assertIn("tick 2: 🪨 pushed the boulder east", out["log"])
        self.assertIn("tick 3: 🪨 pushed the boulder into the crater: it's filled in", out["log"])
        self.assertEqual(out["frames"][3]["m"], [[2, 4, "."], [2, 5, "."]])
        self.assertEqual(run("13a", 'east()\nprint(look("east"))\n')["prints"][0]["text"], "boulder")
        # Pushed against rock, it won't move.
        out = run("13b", "east(4)\nsouth()\nwest(4)\n")
        self.assertIn("won't move", out["log"][-2])
        self.assertIn("couldn't move", out["explain"]["what"])
        # And a two-wide trench can't be jumped.
        self.assertEqual(run("13b", 'east(3)\nsouth()\njump("south")\n')["end"], "fell")

    def test_13d_jumping_at_a_boulder_falls(self):
        jump = ('while not at_beacon():\n    if look("east") != "ground":\n'
                '        jump("east")\n    else:\n        east()\n')
        for i in range(8):
            self.assertFalse(run("13d", jump, i)["reached"], i)

    def test_distance_measures_up_to_the_next_thing(self):
        out = run("14b", 'print(distance("east"), distance("north"), distance("west"))\n')
        self.assertEqual(out["prints"][0]["text"], "5 1 0")
        out = run("14a", 'east(distance("east"))\n')
        self.assertTrue(out["reached"])
        self.assertEqual(out["frames"][1]["ls"], [1, 13])   # the beam, for the replay
        self.assertIn('distance("east")', run("14a", "distance()\n")["error"])

    def test_the_measured_star_wants_no_typed_numbers(self):
        zi, zone, s = site("14a")
        v = s["variants"][0]
        for code, met in (("east(13)\n", False), ('east(distance("east"))\n', True)):
            self.assertEqual(planet.stars(s, v, run("14a", code), code)[1], met, code)

    def test_14c_needs_one_less_than_the_laser(self):
        # 1C's loops drive right up to the rock, a square past each sample.
        code = ('for i in range(3):\n    while look("east") != "rock":\n        east()\n'
                '    while look("south") != "rock":\n        south()\n')
        self.assertFalse(run("14c", code)["reached"])

    def test_cargo_holds_three_and_counts_at_home(self):
        out = run("15b", "east(7)\nsouth(2)\nwest(7)\nprint(cargo(), samples_left())\n")
        self.assertIn("🧪 the cargo bay is full (3): unload at home first", "\n".join(out["log"]))
        self.assertEqual(out["prints"][0]["text"], "3 3")
        self.assertIn("cargo bay is full", out["explain"]["what"])
        self.assertIn("Drive home to x 1, y 1", out["explain"]["next"])
        out = run("15a", "east(7)\nwest(7)\n")
        self.assertIn("tick 14: 📦 brought 3 samples home, 0 still out", out["log"])
        self.assertTrue(out["reached"])
        self.assertEqual(planet.goals(site("15a")[2], site("15a")[2]["variants"][0])[0],
                         "📦 Bring every sample home")

class GiftTests(unittest.TestCase):
    def test_every_gift_sits_on_ground_the_rover_can_drive_over(self):
        for key in planet.GIFT_SQUARES:
            zi, zone, s = site(key)
            for vi, v in enumerate(s["variants"]):
                r, c = planet.gift_square(key, vi)
                self.assertIn(v["map"][r][c], ".~", (key, vi))
                self.assertNotIn((r, c), [tuple(p) for p in v.get("crystals", [])])
                ref = planet.drive(s["reference"], v, zone["rules"], zi)
                if (r, c) not in {(f["r"], f["c"]) for f in ref["frames"]}:
                    self.assertIsNotNone(reach(key, vi, (r, c)), (key, vi))

    def test_one_gift_per_zone_each_with_its_own_garage_item(self):
        # One for every zone but Uncharted: site keys start with the zone's number.
        self.assertEqual([k[:-1] for k in server.MAIN_GIFTS],
                         [str(n) for n in range(1, len(planet.ZONES))])
        # And one in each practice zone (Halloween night has its own, see HalloweenTests).
        practice = [k for k in planet.GIFT_SQUARES if k not in server.MAIN_GIFTS
                    and k not in planet.HALLOWEEN_ORDER]
        self.assertEqual([next(z["key"] for z in planet.PRACTICE_ZONES if k in [x["key"] for x in z["sites"]])
                          for k in practice], [z["key"] for z in planet.PRACTICE_ZONES])
        self.assertEqual(set(server.GIFTS), set(planet.GIFT_SQUARES))
        keys = [i["key"] for i in server.GARAGE]
        self.assertEqual(len(keys), len(set(keys)))
        self.assertTrue(all(i["slot"] in server.GARAGE_SLOTS for i in server.GARAGE))
        # Everything a star count unlocks can be reached.
        top = 3 * len(planet.SITE_ORDER)
        self.assertTrue(all(i["stars"] <= top for i in server.GARAGE if "stars" in i))

    def test_every_garage_item_is_drawn(self):
        render = open(os.path.join(HERE, "planet_render.js"), encoding="utf-8").read()
        page = open(os.path.join(HERE, "planet.html"), encoding="utf-8").read()
        drawn = {"paint": lambda k: re.search(rf"\b{k}: ", render),
                 "topper": lambda k: k == "none" or f'topper === "{k}"' in render,
                 "trail": lambda k: k == "tracks" or f'look.trail === "{k}"' in page,
                 "world": lambda k: k == "planet" or re.search(rf"\n  {k}: {{", page),
                 "dance": lambda k: k == "spin" or f'kind === "{k}"' in page,
                 "glow": lambda k: k == "noglow" or re.search(rf"\n  {k}[:(]", render),
                 "wheels": lambda k: re.search(rf"\n  {k}\(ctx, s", render),
                 "pet": lambda k: k == "nopet" or re.search(rf"\n  {k}\(ctx", render),
                 "horn": lambda k: re.search(rf"\n    {k}: \(\) =>", page) and k in page.split("HORN_ICONS")[1]}
        for item in server.GARAGE:
            self.assertTrue(drawn[item["slot"]](item["key"]), item["key"])

    def test_every_set_piece_is_in_the_garage(self):
        render = open(os.path.join(HERE, "planet_render.js"), encoding="utf-8").read()
        sets = re.findall(r'name: "([^"]+)", icon: "[^"]+", items: \{([^}]*)\}', render)
        self.assertGreaterEqual(len(sets), 9)
        garage = {(i["slot"], i["key"]) for i in server.GARAGE}
        for name, items in sets:
            pieces = re.findall(r'(\w+): "(\w+)"', items)
            self.assertGreaterEqual(len(pieces), 3, name)
            for piece in pieces:
                self.assertIn(piece, garage, name)

    def test_dances_have_icons(self):
        page = open(os.path.join(HERE, "planet.html"), encoding="utf-8").read()
        icons = page.split("const DANCE_ICONS")[1].split("};")[0]
        for item in server.GARAGE:
            if item["slot"] == "dance":
                self.assertIn(f"{item['key']}:", icons)


class PaintShopTests(unittest.TestCase):
    """The Paint Shop: code that paints the rover, 10 squares by 7."""

    def rows(self, code):
        art = planet.paint_shop(code)["art"]
        return [art[i:i + 10] for i in range(0, 70, 10)]

    def test_loops_paint_a_pattern(self):
        rows = self.rows('fill("navy")\nfor y in range(1, 8):\n    for x in range(1, 11):\n'
                         '        if (x + y) % 2 == 0:\n            paint(x, y, "white")\n')
        self.assertEqual(rows[0], "wvwvwvwvwv")
        self.assertEqual(rows[1], "vwvwvwvwvw")
        self.assertEqual(self.rows('paint(10, 7, "Gold ")')[6], ".........a")

    def test_the_squares_go_on_in_the_order_they_were_painted(self):
        out = planet.paint_shop('paint(2, 1, "red")\npaint(1, 1, "red")\npaint(2, 1, "red")\n')
        self.assertEqual(out["steps"], [[1, "r"], [0, "r"]])   # repainting the same is no step
        self.assertFalse(out["loops"])

    def test_mistakes_say_how_to_fix_them(self):
        said = lambda code: planet.paint_shop(code)["error"]
        self.assertIn("range(1, 11) counts 1 to 10", said('for x in range(10):\n    paint(x, 1, "red")\n'))
        self.assertIn('Put quotes round colours:  "red"', said("paint(1, 1, red)"))
        self.assertIn('"purple"', said('paint(1, 1, "rainbow")'))
        self.assertIn("y goes from 1 to 7", said('paint(1, 8, "red")'))
        self.assertIn("is for missions on the planet", said("east()"))
        self.assertIn("three things", said("paint(1, 1)"))
        self.assertIn("ran too long", said('while True:\n    paint(1, 1, "red")\n'))
        # What got painted before the mistake stays.
        out = planet.paint_shop('paint(1, 1, "red")\npaint(0, 1, "red")\n')
        self.assertEqual((out["art"][0], out["line"]), ("r", 2))


class ChallengeTests(unittest.TestCase):
    """The code challenges: badges for one coding trick, that unlock garage items."""

    def met(self, code, jumps=0, ran=True):
        frames = [{"r": 0, "c": 0, "e": "jump"}] * jumps + [{"r": 0, "c": 1}]
        return server.challenge_badges(code, [{"frames": frames, "own_function": ran}])

    def test_each_challenge_badge_unlocks_something(self):
        for key in server.CHALLENGE_BADGES:
            self.assertTrue(any(i.get("badge") == key for i in server.GARAGE), key)

    def test_a_hiss_is_a_printed_sss(self):
        self.assertEqual(self.met('print("Sssss!")\neast()\n'), {"hiss"})
        self.assertEqual(self.met('print("hi", "ssss")\n'), {"hiss"})
        self.assertEqual(self.met('print("ss")\nsss = 1\n'), set())

    def test_a_moo_is_a_printed_moo(self):
        self.assertEqual(self.met('print("Moooo!")\neast()\n'), {"moo"})
        self.assertEqual(self.met('print("moo", "sss")\n'), {"moo", "hiss"})
        self.assertEqual(self.met('print("mo", "o")\nmoo = 1\n'), set())

    def test_a_loop_inside_a_loop(self):
        self.assertEqual(self.met("for i in range(2):\n    for j in range(3):\n        east()\n"), {"nested"})
        self.assertEqual(self.met("while not at_beacon():\n    for i in range(2):\n        east()\n"), {"nested"})
        self.assertEqual(self.met("for i in range(2):\n    east()\nfor i in range(2):\n    north()\n"), set())

    def test_function_fan_counts_calls_and_calls_in_loops(self):
        go = "def go():\n    east()\n"
        self.assertEqual(self.met(go + "go()\ngo()\ngo()\n"), {"fan"})
        self.assertEqual(self.met(go + "for i in range(4):\n    go()\n"), {"fan"})
        self.assertEqual(self.met(go + "go()\ngo()\n"), set())
        # A def that never ran doesn't count.
        self.assertEqual(self.met(go + "go()\ngo()\ngo()\n", ran=False), set())

    def test_kangaroo_wants_ten_jumps_in_one_run(self):
        self.assertEqual(self.met("east()\n", jumps=10), {"kangaroo"})
        self.assertEqual(self.met("east()\n", jumps=9), set())

    def test_broken_code_meets_nothing(self):
        self.assertEqual(self.met('print("sss"\n'), set())


class UnchartedTests(unittest.TestCase):
    def planets(self, seeds=10):
        return [p for seed in range(seeds) for p in planet.uncharted_planets(seed)]

    def score(self, code, planets):
        return sum(planet.drive(code, p, planet.UNCHARTED_RULES,
                                planet.UNCHARTED_ZONE)["reached"] for p in planets)

    def test_reference_clears_every_planet_it_was_checked_on(self):
        planets = self.planets(20)
        self.assertEqual(self.score(planet.UNCHARTED_REFERENCE, planets), len(planets))

    def test_leaving_out_any_idea_loses_planets(self):
        planets = self.planets()
        ref = planet.UNCHARTED_REFERENCE
        side = '    elif safe("south"):\n        south()\n    else:\n        north()\n'
        self.assertIn(side, ref)
        for name, code in (("sun", ref.replace("battery() < 30", "False")),
                           ("craters", ref.replace(' and look(way) != "crater"', "")),
                           ("wind", ref.replace("gust_in() == 1", "False")),
                           ("going round", ref.replace(side, ""))):
            self.assertLess(self.score(code, planets), len(planets) * 0.9, name)

    def test_every_run_lands_on_the_same_five_planets(self):
        planets = planet.UNCHARTED_PLANETS
        self.assertEqual(planets, planet.uncharted_planets(2))
        self.assertEqual(len(planets), planet.PLANETS_PER_RUN)
        self.assertEqual(planet.UNCHARTED_SAMPLE, planets[0])
        # 7C's program is a start (the first star), and every idea from the
        # earlier zones it leaves out wins another planet.
        self.assertEqual(self.score(planet.SIGNAL_ROUND, planets), 2)
        ref = planet.UNCHARTED_REFERENCE
        side = '    elif safe("south"):\n        south()\n    else:\n        north()\n'
        self.assertEqual(self.score(ref, planets), 5)
        for name, code in (("sun", ref.replace("battery() < 30", "False")),
                           ("craters", ref.replace(' and look(way) != "crater"', "")),
                           ("wind", ref.replace("gust_in() == 1", "False")),
                           ("going round", ref.replace(side, ""))):
            self.assertLess(self.score(code, planets), 5, name)

    def test_a_route_from_one_planet_fails_on_the_others(self):
        planets = self.planets(4)
        first = planet.drive(planet.UNCHARTED_REFERENCE, planets[0],
                             planet.UNCHARTED_RULES, planet.UNCHARTED_ZONE)
        self.assertLess(self.score(replay_as_code(first), planets), 4)

    def test_the_beacon_sensors_say_where_it_is(self):
        world = {"map": ["#####", "#S..#", "#..G#", "#####"], "wind": 9, "battery": 50}
        out = planet.drive("print(x(), y(), beacon_x(), beacon_y())\neast()\n"
                           "print(x(), y())\n", world,
                           planet.UNCHARTED_RULES, planet.UNCHARTED_ZONE)
        self.assertEqual([p["text"] for p in out["prints"]], ["1 1 3 2", "2 1"])


class RoverTests(unittest.TestCase):
    def test_out_of_time_names_the_loop_it_has(self):
        # Harvey's 1A: a for loop of 4000 moves was told a while loop was stuck.
        out = run("1a", "for i in range(1000):\n    south()\n    east()\n    north()\n    west()\n")
        self.assertEqual(out["end"], "ticks")
        self.assertIn("for loop", out["explain"]["next"])
        self.assertNotIn("while", out["explain"]["next"])
        self.assertIn("smaller numbers", planet.out_of_time("south(50)\n" * 30))
        self.assertIn("while loop", planet.out_of_time("while True:\n    wait()\n"))

    def test_bumping_between_waits_still_says_where_it_was_stuck(self):
        # 5B: waiting in the sun fills half the ticks, bumping the other half.
        out = run("5b", "while not at_beacon():\n    if in_sun():\n        wait()\n    east()\n")
        self.assertEqual(out["end"], "ticks")
        self.assertIn("bumping into rock", out["explain"]["what"])
        self.assertIn('look("east")', out["explain"]["next"])

    def test_a_def_called_once_says_to_repeat_it(self):
        # ej's 1B try: the repeat was found, but staircase() ran once.
        once = "def staircase():\n    east()\n    south()\nstaircase()\n"
        self.assertIn("staircase() ran once", run("1b", once)["explain"]["next"])
        looped = "def staircase():\n    east()\n    south()\nfor i in range(3):\n    staircase()\n"
        self.assertNotIn("ran once", run("1b", looped)["explain"]["next"])

    def test_numbers_a_drive_cant_take_say_what_to_write(self):
        self.assertIn("use  west(1)", run("1b", "east(-1)\n")["error"])
        self.assertIn("whole numbers here, like 1 (not 1.5)", run("1b", "east(1.5)\n")["error"])

    def test_an_if_on_one_line_says_where_its_commands_go(self):
        for code in ("def i():\n    if tick() % 1 == 0 east() else south()\ni()\n",
                     "while x() < 5 east()\n", "for i in range(3) east()\n"):
            self.assertIn("end this line with  :", run("1b", code)["error"], code)
        self.assertIn("else  goes on its own line",
                      run("1b", "if x() == 1: east() else: south()\n")["error"])
        # A missing colon with the body already below keeps Python's own hint.
        self.assertIn("has to end with a  :", run("1b", "for i in range(3)\n    east()\n")["error"])

    def test_sensors_arrive_zone_by_zone(self):
        out = run("1a", "print(tick())\n")
        self.assertIn("Wind Canyon", out["error"])
        self.assertIsNone(run("3a", "print(tick())\n")["error"])
        self.assertIn("Uncharted", run("7c", "print(gust_in())\n")["error"])
        self.assertIn("Uncharted", run("12d", "print(gust_in())\n")["error"])
        self.assertIn("The Quarry", run("9a", 'drill("east")\n')["error"])
        self.assertIn("Gate Station", run("10a", "print(has_key())\n")["error"])
        self.assertIn("Flag Relay", run("11a", "print(next_x())\n")["error"])
        self.assertIn("Laser Range", run("13a", 'print(distance("east"))\n')["error"])
        self.assertIn("Cargo Run", run("14a", "print(cargo())\n")["error"])

    def test_zone_order_matches_the_zones(self):
        self.assertEqual([z["key"] for z in planet.ZONES], planet.ZONE_ORDER)
        self.assertEqual(planet.UNCHARTED_ZONE, planet.ZONE_ORDER.index("uncharted"))

    def test_each_frame_knows_the_line_that_made_it(self):
        # The editor lights up the running line during the replay: a drive in
        # a def is its line in the def, and a gust's push stays with the drive.
        out = run("1a", "def hop():\n    east()\n\nsouth()\nhop()\n")
        self.assertNotIn("ln", out["frames"][0])
        self.assertEqual([f["ln"] for f in out["frames"][1:]], [4, 2])
        out = run("3b", "south(20)\n")
        self.assertIn("💨", out["log"][0])
        self.assertEqual({f.get("ln") for f in out["frames"][1:]}, {1})

    def test_look_names_the_next_square(self):
        out = run("2a", 'print(look("north"))\nprint(look("east"))\n'
                        'print(look(south))\nway = "west"\nprint(look(way))\n')
        self.assertEqual([p["text"] for p in out["prints"]],
                         ["ground", "ice", "ground", "rock"])

    def test_report_is_quiet_where_nothing_is_measured(self):
        out = run("2b", "report(3)\n")
        self.assertEqual((out["end"], out["log"][0]), ("stopped", "tick 0: 📡 report sent: 3"))

    def test_a_run_that_misses_says_what_happened_in_plain_words(self):
        for key, code, what, nxt in [
            ("1a", "east(2)\n", "finished with the rover at x 3, y 1, and 3 samples still out",
             "The closest is at x 2, y 3: 1 square west and 2 squares south."),
            ("7b", "east()\n", "away from the beacon at", "of there."),
            ("8a", "east(8)\n", "The rover drove into a crater at x 6, y 2", 'jump("east") from x 5, y 2'),
            ("3b", "south(20)\n", "gust pushed the rover into a crater", "wait()"),
            ("2b", "east(2)\n", "away from the beacon", "work back from the beacon"),
            ("4a", "east()\nwest()\n", "had cracked", "own tracks"),
            ("5c", "east(40)\n", "The battery ran out", "sun"),
            ("1a", "while True:\n    wait()\n", "ran for 1000 ticks", "while loop"),
            ("1a", "east(20)\n", "bumped into rock", "doesn't move"),
        ]:
            out = run(key, code)
            self.assertIn(what, out["explain"]["what"], code)
            self.assertIn(nxt, out["explain"]["next"] + out["explain"]["what"], code)
            # Statements, never questions.
            self.assertNotIn("?", out["explain"]["what"] + out["explain"]["next"], code)
        self.assertIsNone(run("1a", "east(\n")["explain"])
        self.assertIsNone(run("9a", "east(2)\n")["explain"])

    def test_running_out_of_time_on_two_squares_says_which(self):
        # 7C's steering on 8A paces in front of the crater wall for 995 ticks.
        out = run("8a", site("7c")[2]["reference"])
        self.assertIn("back and forth between x 5, y 2 and x 5, y 3", out["explain"]["what"])
        self.assertIn('jump("east") from x 5, y 2', out["explain"]["next"])
        # Before jump() arrives, it says the loop needs another way to go.
        out = run("7c", "while not at_beacon():\n    east()\n    west()\n")
        self.assertIn("back and forth", out["explain"]["what"])
        self.assertIn("another way to go", out["explain"]["next"])

    def test_a_gust_fall_says_whose_number_the_code_used(self):
        guard = ("def guard():\n    if tick() % {} == {}:\n        wait()\n\n"
                 "for i in range(20):\n    guard()\n    south()\n")
        # A classmate's number: say it's wrong here, and when the first gust came.
        variants = site("3c")[2]["variants"]
        for i, v in enumerate(variants):
            other = next(o["wind"] for o in variants if o["wind"] != v["wind"])
            out = run("3c", wind_program(other, v["legs"]), i)
            self.assertEqual(out["end"], "fell", i)
            self.assertIn(f"don't come every {other} ticks", out["explain"]["next"], i)
            n = v["wind"]
            self.assertIn(f"they come on ticks {n}, {2 * n}, {3 * n} and so on",
                          out["explain"]["next"], i)
        # The right number but the wrong tick: say which tick to wait on.
        out = run("3b", guard.format(5, 0))
        self.assertIn("tick() % 5 is the right number", out["explain"]["next"])
        self.assertIn("tick() % 5 == 4", out["explain"]["next"])
        # No tick() at all: when the gusts come, as the telemetry shows them,
        # even when a wait() happened to dodge the first one.
        for code in ("south(20)\n", "south(4)\nwait()\nsouth(2)\neast(5)\nsouth(6)\n"):
            self.assertIn("come on ticks 5, 10, 15 and so on", run("3b", code)["explain"]["next"])

    def test_every_code_snippet_students_are_shown_runs(self):
        # Hints, coach steps and briefs end with code that students copy in.
        for zi, zone, s in sites():
            texts = [h for h in zone["hints"]] if s is zone["sites"][0] else []
            texts += (s["coach"] or {}).get("steps", []) + [s["brief"]]
            for text in texts:
                if "\n\n" not in text:
                    continue
                error = run(s["key"], text.split("\n\n", 1)[1])["error"] or ""
                # ...  marks the student's own lines; go_to() is made on 11A.
                self.assertTrue(not error or "only marks where your own lines go" in error
                                or "go_to() isn't built in" in error, (s["key"], error))

    def test_the_place_it_names_is_where_the_rover_ended(self):
        out = run("7b", "east(3)\nsouth()\n")
        last = out["frames"][-1]
        self.assertIn(f"x {last['c']}, y {last['r']}", out["explain"]["what"])

    def test_friendly_errors(self):
        self.assertIn("Strange Planet", run("1a", "x = [1, 2]\n")["error"])
        self.assertIn("import", run("1a", "import os\n")["error"])
        self.assertIn("Syntax error", run("1a", "east(\n")["error"])
        # Beginners' slips get the fix, not a misleading guess.
        self.assertIn('Put quotes round words:  "rock"',
                      run("1c", 'while look("east") != rock:\n    east()\n')["error"])
        self.assertTrue(run("1c", 'rock = "rock"\nprint(look("east") != rock)\n')["prints"])
        self.assertIn("each command on its own line",
                      run("1b", "for i in range(8):\n    east(), south()\n")["error"])
        self.assertIn("range(8)", run("1b", "for i in range 8:\n    east()\n")["error"])
        self.assertIn("like:  while not at_beacon():", run("7b", "while !at_beacon():\n    east()\n")["error"])
        self.assertIn('like:  if look("east") == "rock":',
                      run("1c", 'look("east") == "rock"\n')["error"])
        self.assertIn("n = beacon_x() - x()", run("7b", "beacon_x() - x()\n")["error"])
        self.assertIn("return hands it back", run("7b", "def f():\n    x() + 1\nf()\n")["error"])
        # A drive command in a sum gives back nothing: say so, not "n = ...".
        for code in ("east(2) + south(2)\n", "n = east() + 1\n", "east() * 3\n"):
            self.assertIn("east() drives the rover: it doesn't give back a number",
                          run("1a", code)["error"])
        self.assertIn("multiply: 2 * 2 * 2", run("1a", "print(2 ** 3)\n")["error"])
        self.assertIn("multiply: 2 * 2 * 2", run("1a", "print(2 ^ 3)\n")["error"])
        self.assertIn('Use the word  and  to join two checks, like:  if look("east")',
                      run("7b", "print(x() > 0 & y() > 0)\n")["error"])
        self.assertIn("write  !=  (not  =!)",
                      run("1c", 'while look("east") =! "rock":\n    east()\n')["error"])
        # A word look() never gives back, like "wall" from the maze game.
        for word, says in (("wall", 'It gives back words like "rock"'), ("Rock", 'Did you mean "rock"'),
                           ("empty", 'An open square is "ground"')):
            out = run("1c", f'while look("east") != "{word}":\n    east()\n')
            self.assertIn(f'look() never gives back "{word}". {says}', out["error"])
        out = run("1a", "while True:\n    pass\n")
        self.assertIn("rover had stopped at x 1, y 1", out["error"])
        self.assertEqual(out["line"], 1)
        out = run("1a", "for i in range(99999):\n    for j in range(99):\n        n = i\n")
        self.assertIn("ran too long", out["error"])

    def test_a_loop_that_stopped_the_rover_says_why(self):
        out = run("14b", 'while not at_beacon():\n    east(distance("east"))\n')
        self.assertIn('east(distance("east")) drove 0 squares', out["error"])
        self.assertIn("Jump it or go round it", out["error"])
        out = run("15d", planet.GO_TO + "while True:\n    go_to(sample_x(), sample_y())\n")
        self.assertIn("cargo bay was full", out["error"])
        steer = ("while not at_beacon():\n    if x() < next_x():\n        east()\n"
                 "    elif y() < next_y():\n        south()\n")
        self.assertIn("nothing in your code drives west", run("12c", steer)["error"])
        out = run("13d", 'while not at_beacon():\n    if look("east") == "ground":\n'
                         '        east()\n')
        self.assertIn('look("east") says "boulder"', out["error"])

    def test_stuck_runs_point_at_the_drill_and_the_key(self):
        self.assertIn('drill("east")', run("10a", "east(10)\n")["explain"]["next"])
        self.assertIn('drill("east")', run("10d", "while not at_beacon():\n"
                                                  "    east()\n")["explain"]["next"])
        out = run("11b", "while not at_beacon():\n    east()\n")
        self.assertEqual(out["end"], "ticks")
        self.assertIn("Pick up the key", out["explain"]["next"])

    def test_a_loop_stuck_on_rock_says_where_and_which_way(self):
        out = run("6c", "while not at_beacon():\n    east()\n")
        self.assertEqual(out["end"], "ticks")
        self.assertIn("stuck at x 5, y 1, bumping into rock", out["explain"]["what"])
        self.assertNotIn("times", out["explain"]["what"])
        self.assertIn('look("east")', out["explain"]["next"])

    def test_a_flat_battery_says_where_the_sun_was(self):
        out = run("5c", "east(40)\n")
        self.assertIn("in the sun at x 16, y 1 on tick 15", out["explain"]["next"])
        self.assertIn("while in_sun() and battery() < 40: wait()", out["explain"]["next"])
        out = planet.drive("east(20)\n", planet.UNCHARTED_PLANETS[0],
                           planet.UNCHARTED_RULES, planet.UNCHARTED_ZONE)
        self.assertEqual(out["end"], "battery")
        self.assertIn("in the sun at", out["explain"]["next"])

    def test_a_fall_names_the_way_it_drove_and_a_jump(self):
        self.assertIn('look("south")', run("13b", "south(5)\n")["explain"]["next"])
        self.assertIn('jump("south") from x 4, y 4',
                      run("13b", "east(3)\nsouth(4)\n")["explain"]["next"])
        # Before jump() arrives, a fall only says to look first.
        self.assertIn('look("east")', run("3b", "east(9)\n")["explain"]["next"])

    def test_beginner_slips_say_what_to_do(self):
        step = "def step():\n    east()\n"
        for key, code, says, line in [
            ("1a", "east(3) south()\n", "put each command on its own line", 1),
            ("1a", "east 3\n", "commands need brackets, like  east(3)", 1),
            ("1a", "east()\nturn right()\n", "drives by compass", 2),
            ("1a", "repeat 7:\n    east()\n", "for i in range(7):", 1),
            ("1a", "def step:\n    east()\n", "def step():", 1),
            ("1a", "east()\nsouth\n", "write  south()", 2),
            ("1a", step + "step\n", "write  step()", 3),
            ("1a", "east()\nleft\n", "drives by compass", 2),
            ("1a", "d = east\n", '"east"', 1),
            ("1a", 'look("up")\n', 'look("east")', 1),
            ("1a", "step()\n" + step, "further down, on line 2", 1),
            ("1a", "def east():\n    wait()\n", "already one of the rover's commands", 1),
            ("1a", "def go(n):\n    east(n)\ngo()\n", "go() needs 1 value in the ( ), like  go(3)", 3),
            ("15d", "go_to(home_x(), home_y())\n", "def go_to(tx, ty):", 1),
            ("15a", "east(7)\nhome()\n", "unload by themselves", 2),
            ("15a", "pickup()\n", "driving over them", 1),
            ("13a", 'push("east")\n', "Drive into a boulder", 1),
            ("1a", step + "step(2)\n", "made with  def step():", 3),
            ("2a", "x = 3\n", "Pick another name", 1),
            ("2a", 'report("6")\n', "report() sends a whole number", 1),
        ]:
            out = run(key, code)
            self.assertIn(says, out["error"], code)
            self.assertEqual(out["line"], line, code)

    def test_a_def_that_never_runs_is_pointed_out(self):
        out = run("1a", "def go():\n    east(3)\n")
        self.assertEqual(out["end"], "stopped")
        self.assertTrue(any("go() was made with def but never used" in l for l in out["log"]))
        self.assertFalse(any("🧩" in l for l in run("1a", "def go():\n    east(3)\ngo()\n")["log"]))

    def test_an_endless_drive_runs_out_of_time(self):
        out = run("1a", "while True:\n    wait()\n")
        self.assertEqual((out["end"], out["ticks"]), ("ticks", planet.MAX_TICKS))

    def test_prints_keep_the_tick(self):
        out = run("3a", "south()\nprint('here', tick())\n")
        self.assertEqual(out["prints"], [{"t": 1, "text": "here 1"}])


class ClassroomTests(unittest.TestCase):
    """The whole flow over HTTP, on a real server with its own save file."""

    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.saved = dict(server.players), server.STATE_FILE
        server.players.clear()
        server.planet_runs.clear()
        server.STATE_FILE = os.path.join(self.folder.name, "scores.json")
        self.httpd = server.ClassroomServer(("127.0.0.1", 0), server.Handler)
        threading.Thread(target=self.httpd.serve_forever, daemon=True).start()
        self.base = f"http://127.0.0.1:{self.httpd.server_address[1]}"

    def tearDown(self):
        self.httpd.shutdown()
        self.httpd.server_close()
        server.players.clear()
        server.players.update(self.saved[0])
        server.STATE_FILE = self.saved[1]
        server.planet_spotlight[0] = None
        server.planet_runs.clear()
        server.planet_class_settings["blanks"] = True
        server.planet_class_settings["easy"] = False
        server.planet_class_settings["coach"] = False
        self.folder.cleanup()

    def get(self, path):
        with urlopen(self.base + path) as response:
            return json.loads(response.read())

    def post(self, path, data):
        request = Request(self.base + path, json.dumps(data).encode(),
                          {"Content-Type": "application/json"})
        with urlopen(request) as response:
            return json.loads(response.read())

    def join(self, name="Ada"):
        return self.post("/join", {"name": name})["id"]

    def test_pages_are_served(self):
        for path in ("/planet", "/planet/teacher", "/planet/show"):
            with urlopen(self.base + path) as response:
                self.assertIn(b"Strange Planet", response.read())
        with urlopen(self.base + "/planet/replay.js") as response:
            self.assertIn(b"function replayStage", response.read())
        with urlopen(self.base + "/planet/render.js") as response:
            self.assertIn(b"function drawRover", response.read())

    def test_sites_open_one_at_a_time(self):
        pid = self.join()
        state = self.get(f"/planet/state?id={pid}")
        self.assertEqual(state["current"], "1a")
        self.assertIn("error", self.get(f"/planet/site?id={pid}&site=1b"))
        self.assertIn("error", self.post("/planet/run", {"id": pid, "site": "1b",
                                                         "code": "east()"}))
        out = self.post("/planet/run", {"id": pid, "site": "1a",
                                        "code": site("1a")[2]["reference"]})
        self.assertTrue(out["runs"][0]["reached"])
        self.assertEqual(out["state"]["current"], "1b")
        view = self.get(f"/planet/site?id={pid}&site=1b")
        self.assertEqual(view["name"], "Crystal Steps")

    def test_a_site_never_shows_its_hidden_rule(self):
        pid = self.join()
        server.planet_entry(server.players[pid])["unlocked"] = len(planet.SITE_ORDER)
        for key in ("2a", "3c", "5c", "6c"):
            view = self.get(f"/planet/site?id={pid}&site={key}")
            text = json.dumps(view)
            for secret in ("wind", "sun", "pairs", "oneway", "start", "every", "answer", "others"):
                self.assertNotIn(f'"{secret}"', text, (key, secret))

    def test_each_student_keeps_their_own_variant(self):
        ids = [self.join(f"Student{i}") for i in range(12)]
        s = site("2c")[2]
        picks = {planet.variant_index(pid, s) for pid in ids}
        self.assertGreater(len(picks), 1)
        for pid in ids[:3]:
            server.planet_entry(server.players[pid])["unlocked"] = 5
            first = self.get(f"/planet/site?id={pid}&site=2c")["map"]
            self.assertEqual(first, self.get(f"/planet/site?id={pid}&site=2c")["map"])

    def test_a_run_saves_the_code_and_a_better_best(self):
        pid = self.join()
        slow = "wait()\n" + site("1a")[2]["reference"]
        self.post("/planet/run", {"id": pid, "site": "1a", "code": slow})
        self.post("/planet/run", {"id": pid, "site": "1a",
                                  "code": site("1a")[2]["reference"]})
        self.post("/planet/run", {"id": pid, "site": "1a", "code": slow})
        view = self.get(f"/planet/site?id={pid}&site=1a")
        self.assertEqual(view["solved"], 16)
        self.assertEqual(view["code"], slow)

    def test_uncharted_runs_five_planets_and_keeps_the_best(self):
        pid = self.join()
        server.planet_entry(server.players[pid])["unlocked"] = len(planet.SITE_ORDER)
        out = self.post("/planet/run", {"id": pid, "site": "7",
                                        "code": planet.UNCHARTED_REFERENCE})
        self.assertEqual(len(out["runs"]), planet.PLANETS_PER_RUN)
        self.assertTrue(all(r["reached"] for r in out["runs"]))
        self.assertTrue(all("map" in r for r in out["runs"]))
        again = self.post("/planet/run", {"id": pid, "site": "7", "code": "east()"})
        self.assertEqual([r["map"] for r in again["runs"]],
                         [r["map"] for r in out["runs"]])
        self.post("/planet/run", {"id": pid, "site": "7", "code": "east()"})
        self.assertEqual(self.get(f"/planet/state?id={pid}")["uncharted"]["reached"], 5)

    def test_the_globe_star_checks_every_plain(self):
        pid = self.join()
        server.planet_entry(server.players[pid])["unlocked"] = len(planet.SITE_ORDER)
        s = site("7b")[2]
        out = self.transmit(pid, "7b", s["reference"])
        self.assertEqual(out["rewards"]["stars"], [True, True, True])
        self.assertIn("8 of the 8 plains", out["runs"][0]["log"][-1])
        mine = planet.variant_index(pid, s)
        route = replay_as_code(run("7b", s["reference"], mine))
        out = self.transmit(pid, "7b", route)
        self.assertEqual(out["rewards"]["stars"], [True, False, True])

    def test_hints_and_the_teacher_overview(self):
        pid = self.join()
        for _ in range(5):
            state = self.post("/planet/hint", {"id": pid, "zone": "ice"})
        ice = next(z for z in state["zones"] if z["key"] == "ice")
        self.assertEqual(len(ice["hints"]), 3)
        # Opened the planet, never pressed Run: the teacher's page marks them.
        self.assertEqual(self.get("/planet/overview")["students"][0]["runs_total"], 0)
        for _ in range(3):
            self.post("/planet/run", {"id": pid, "site": "1a", "code": "east()"})
        row = self.get("/planet/overview")["students"][0]
        self.assertEqual((row["name"], row["site"], row["runs_here"], row["hints"]),
                         ("Ada", "1a", 3, 3))
        self.assertEqual(row["runs_total"], 3)
        # What the last run's banner said, so the teacher knows before walking over.
        self.assertIn("3 samples still out", row["now"]["said"])
        self.post("/planet/run", {"id": pid, "site": "1a", "code": "east(\n"})
        row = self.get("/planet/overview")["students"][0]
        self.assertIn("Syntax error", row["now"]["said"])
        # Each site keeps the last few tries, to see where a student got stuck.
        for i in range(server.TRIES_KEPT):
            self.post("/planet/run", {"id": pid, "site": "1a", "code": f"east({i})"})
        tries = server.players[pid]["planet"]["tries"]["1a"]
        self.assertEqual(len(tries), server.TRIES_KEPT)
        self.assertEqual((tries[-1]["code"], tries[-1]["end"]), (f"east({server.TRIES_KEPT - 1})", "stopped"))
        self.assertIn("samples still out", tries[-1]["said"])
        # The teacher's page gets them for the site the student is on.
        row = self.get("/planet/overview")["students"][0]
        self.assertEqual([x["code"] for x in row["tries"]], [x["code"] for x in tries])

    def test_first_try_ranks_and_class_goals(self):
        pid = self.join()
        ref = lambda key: site(key)[2]["reference"]
        # A miss first, then a clear: not a first try.
        self.post("/planet/run", {"id": pid, "site": "1a", "code": "east()\n"})
        out = self.post("/planet/run", {"id": pid, "site": "1a", "code": ref("1a")})
        self.assertFalse(out["rewards"]["first_try"])
        out = self.post("/planet/run", {"id": pid, "site": "1b", "code": ref("1b")})
        self.assertTrue(out["rewards"]["first_try"])
        self.assertEqual(out["state"]["rank"]["name"], "Cadet")
        self.assertGreater(out["state"]["rank"]["need"], 0)
        # Enough stars for the next rank: the run that gets there says so once.
        ups = []
        for key in planet.SITE_ORDER[2:8]:
            i = planet.variant_index(pid, site(key)[2])
            code = ref(key) or answer_program(key, i)
            ups.append(self.post("/planet/run", {"id": pid, "site": key, "code": code})["rewards"]["rank_up"])
        self.assertEqual([u["name"] for u in ups if u], ["Rookie Pilot"])
        badges = [b["key"] for b in out["state"]["badges"] if b["earned"]]
        state = self.post("/planet/run", {"id": pid, "site": "1b", "code": ref("1b")})["state"]
        self.assertIn("sharp", [b["key"] for b in state["badges"] if b["earned"]])
        self.assertNotIn("sharp", badges)
        # Crossing a class goal tells the whole class on the projector.
        for key in planet.SITE_ORDER[8:]:
            if state["total_stars"] >= 30:
                break
            i = planet.variant_index(pid, site(key)[2])
            state = self.post("/planet/run", {"id": pid, "site": key,
                                              "code": ref(key) or answer_program(key, i)})["state"]
        feed = self.get("/planet/overview")
        self.assertTrue(any("The class reached 30" in m["text"] for m in feed["feed"]))
        self.assertEqual(feed["class"]["unlocks"]["30"], "Aurora paint")

    def test_todays_missions(self):
        day, keys = server.todays_missions("2026-10-24")
        self.assertEqual((day, keys), server.todays_missions("2026-10-24"))
        self.assertEqual(len(set(keys)), 3)
        self.assertIn(keys[0], server.PROGRESS_MISSIONS)
        self.assertFalse(set(keys[1:]) & set(server.PROGRESS_MISSIONS))
        pid = self.join()
        ref = lambda key: site(key)[2]["reference"]
        with mock.patch.object(server, "todays_missions",
                               lambda day=None: ("2026-10-24", ["sites", "loop", "print"])):
            state = self.post("/planet/run", {"id": pid, "site": "1a", "code": "east()\n"})["state"]
            self.assertEqual([m["have"] for m in state["missions"]["list"]], [0, 0, 0])
            out = self.post("/planet/run", {"id": pid, "site": "1a", "code": ref("1a")})
            self.assertEqual([m["text"] for m in out["rewards"]["missions_done"]], [])
            self.assertEqual(out["state"]["missions"]["list"][0]["have"], 1)
            # The same site again doesn't count twice; a loop on another does both.
            out = self.post("/planet/run", {"id": pid, "site": "1a", "code": ref("1a")})
            self.assertEqual(out["state"]["missions"]["list"][0]["have"], 1)
            out = self.post("/planet/run", {"id": pid, "site": "1b", "code": ref("1b")})
            self.assertEqual(len(out["rewards"]["missions_done"]), 2)
            self.assertFalse(out["rewards"]["trophy"])
            out = self.post("/planet/run", {"id": pid, "site": "1b",
                                            "code": 'print("go")\n' + ref("1b")})
            self.assertTrue(out["rewards"]["trophy"])
            self.assertEqual(out["state"]["missions"]["trophies"], 1)
            self.assertIn("daily", [b["key"] for b in out["state"]["badges"] if b["earned"]])
            # Nothing more to finish today.
            out = self.post("/planet/run", {"id": pid, "site": "1b",
                                            "code": 'print("go")\n' + ref("1b")})
            self.assertFalse(out["rewards"]["trophy"])
        # A new day starts afresh; three mission days unlock the medal.
        with mock.patch.object(server, "todays_missions",
                               lambda day=None: ("2026-10-25", ["sites", "loop", "print"])):
            state = self.post("/planet/run", {"id": pid, "site": "1a", "code": "east()\n"})["state"]
            self.assertEqual([m["have"] for m in state["missions"]["list"]], [0, 0, 0])
        medal = next(i for i in state["garage"] if i["key"] == "medal")
        self.assertFalse(medal["open"])
        server.players[pid]["planet"]["trophies"] = 3
        state = self.post("/planet/run", {"id": pid, "site": "1a", "code": "east()\n"})["state"]
        self.assertTrue(next(i for i in state["garage"] if i["key"] == "medal")["open"])

    def test_badges_unlock_dances_and_one_can_be_worn(self):
        pid = self.join()
        state = self.post("/planet/run", {"id": pid, "site": "1a", "code": "east()\n"})["state"]
        flip = next(i for i in state["garage"] if i["key"] == "flip")
        self.assertEqual((flip["open"], flip["badge_name"]), (False, "Triple Star"))
        # Not earned yet: neither the dance nor wearing the badge takes.
        look = self.post("/planet/look", {"id": pid, "dance": "flip", "showoff": "triple"})["look"]
        self.assertEqual(look["dance"], "spin")
        self.assertIsNone(self.get("/planet/overview")["students"][0]["showoff"])
        server.players[pid]["planet"]["badges"].append("triple")
        look = self.post("/planet/look", {"id": pid, "dance": "flip", "showoff": "triple"})["look"]
        self.assertEqual(look["dance"], "flip")
        self.assertEqual(self.get("/planet/overview")["students"][0]["showoff"], "🌟")
        self.post("/planet/look", {"id": pid, "showoff": None})
        self.assertIsNone(self.get("/planet/overview")["students"][0]["showoff"])

    def test_the_everyday_coding_badges_unlock_paints(self):
        pid = self.join()
        garage = lambda: {i["key"]: i for i in self.get(f"/planet/state?id={pid}")["garage"]}
        self.assertFalse(garage()["ladybug"]["open"])
        self.assertEqual(garage()["ladybug"]["badge_name"], "Bug Squasher")
        server.players[pid]["planet"]["badges"] += ["fixer", "loop"]
        self.assertTrue(garage()["ladybug"]["open"] and garage()["cheetah"]["open"])
        self.assertFalse(garage()["zebra"]["open"])   # that one wants an if

    def test_every_rank_up_picks_one_of_three_rewards(self):
        pid = self.join()
        self.assertEqual(self.get(f"/planet/state?id={pid}")["picks"], 0)   # a Cadet
        entry = server.planet_entry(server.players[pid])
        entry["stars"] = {k: [True] * 3 for k in planet.SITE_ORDER[:4]}   # 12 ★: Rookie Pilot
        state = self.get(f"/planet/state?id={pid}")
        self.assertEqual(state["picks"], 1)
        offer = state["pick_choices"]
        self.assertEqual(len({i["slot"] for i in offer}), 3)
        self.assertTrue(all(i["stars"] > 12 for i in offer))
        self.assertEqual(self.get(f"/planet/state?id={pid}")["pick_choices"], offer)   # no reroll
        # Only one of the three, and only once.
        self.post("/planet/pick", {"id": pid, "key": "rocket"})
        self.assertEqual(self.get(f"/planet/state?id={pid}")["picks"], 1)
        state = self.post("/planet/pick", {"id": pid, "key": offer[1]["key"]})
        self.assertEqual((state["picks"], state["pick_choices"]), (0, []))
        self.assertTrue(next(i for i in state["garage"] if i["key"] == offer[1]["key"])["open"])
        self.assertEqual(self.post("/planet/pick", {"id": pid, "key": offer[0]["key"]})["picks"], 0)
        self.assertFalse(next(i for i in self.get(f"/planet/state?id={pid}")["garage"]
                              if i["key"] == offer[0]["key"])["open"])

    def test_the_paint_shop_paints_your_rover(self):
        pid = self.join()
        mine = lambda: next(i for i in self.get(f"/planet/state?id={pid}")["garage"] if i["key"] == "mine")
        self.assertFalse(mine()["open"])
        # Painting shows it; only wearing it puts it on.
        out = self.post("/planet/paint", {"id": pid, "code": 'paint(1, 1, "red")'})
        self.assertEqual(out["art"][:2], "r.")
        self.assertNotIn("art", out["look"])
        self.assertEqual(self.get(f"/planet/state?id={pid}")["paint_code"], 'paint(1, 1, "red")')
        self.assertIn("Paint a square", self.post("/planet/paint", {"id": pid, "code": "", "wear": True})["error"])
        out = self.post("/planet/paint", {"id": pid, "code": 'paint(1, 1, "red")', "wear": True})
        self.assertEqual((out["look"]["paint"], out["look"]["art"][0]), ("mine", "r"))
        self.assertNotIn("badge", out)   # no loop, no Pixel Artist
        self.assertTrue(mine()["open"])
        self.assertEqual(self.get("/planet/overview")["students"][0]["look"]["art"][0], "r")
        out = self.post("/planet/paint", {"id": pid, "wear": True,
                                          "code": 'for x in range(1, 11):\n    paint(x, 1, "blue")\n'})
        self.assertEqual(out["badge"]["name"], "Pixel Artist")
        # Broken code never goes on the rover.
        out = self.post("/planet/paint", {"id": pid, "code": 'paint(1, 1, red)', "wear": True})
        self.assertEqual(out["look"]["art"][:2], "bb")
        # The teacher can take it off.
        self.post("/admin", {"key": server.ADMIN_KEY, "action": "planet_wipe_paint", "pid": pid})
        look = self.get(f"/planet/state?id={pid}")["look"]
        self.assertEqual(look["paint"], "bone")
        self.assertNotIn("art", look)
        self.assertFalse(mine()["open"])

    def test_a_hiss_in_a_finished_run_unlocks_the_creeper(self):
        pid = self.join()
        ref = site("1a")[2]["reference"]
        # A run that doesn't get there earns nothing.
        out = self.post("/planet/run", {"id": pid, "site": "1a", "code": 'print("sssss")\neast()\n'})
        self.assertFalse(next(i for i in out["state"]["garage"] if i["key"] == "creeper")["open"])
        out = self.post("/planet/run", {"id": pid, "site": "1a", "code": 'print("sssss")\n' + ref})
        self.assertIn("Sssneaky", [b["name"] for b in out["rewards"]["badges"]])
        garage = {i["key"]: i for i in out["state"]["garage"]}
        self.assertTrue(garage["creeper"]["open"] and garage["hiss"]["open"])
        self.assertIn("creeper", [i["key"] for i in out["rewards"]["unlocked"]])
        self.assertIn('print("sssss")', garage["creeper"]["badge_how"])
        look = self.post("/planet/look", {"id": pid, "paint": "creeper", "horn": "hiss"})["look"]
        self.assertEqual((look["paint"], look["horn"]), ("creeper", "hiss"))

    def test_the_record_ghost_appears_once_a_site_is_done(self):
        ada, bo = self.join("Ada"), self.join("Bo")
        slow = "south(2)\neast()\nsouth()\neast(4)\nnorth(2)\neast(2)\nnorth()\neast(2)\nsouth(4)\nwest()\n"
        out = self.post("/planet/run", {"id": ada, "site": "1a", "code": slow})
        ghost = out["ghost"]
        self.assertEqual((ghost["name"], ghost["ticks"]), ("Ada", out["runs"][0]["ticks"]))
        self.assertEqual(len(ghost["route"]), len(out["runs"][0]["frames"]))
        # Bo hasn't done it: no ghost yet, so it gives nothing away.
        self.assertIsNone(self.get(f"/planet/site?id={bo}&site=1a")["ghost"])
        out = self.post("/planet/run", {"id": bo, "site": "1a", "code": site("1a")[2]["reference"]})
        self.assertEqual(out["ghost"]["name"], "Bo" if out["runs"][0]["ticks"] < ghost["ticks"] else "Ada")
        # A slower run later doesn't replace a student's best route.
        route = server.players[ada]["planet"]["routes"]["1a"]
        self.post("/planet/run", {"id": ada, "site": "1a", "code": slow + "north()\nsouth()\n"})
        self.assertEqual(server.players[ada]["planet"]["routes"]["1a"], route)
        # Each student's own planet: no ghost to race.
        self.assertFalse(server.ghostly("1c", site("1c")[2]))

    def test_clearing_a_zone_says_whats_next(self):
        pid = self.join()
        for key in ("1a", "1b"):
            out = self.post("/planet/run", {"id": pid, "site": key, "code": site(key)[2]["reference"]})
            self.assertIsNone(out["rewards"]["zone_cleared"])
        loop = site("1c")[2]["reference"]   # clears every student's rock run
        out = self.post("/planet/run", {"id": pid, "site": "1c", "code": loop})
        cleared = out["rewards"]["zone_cleared"]
        self.assertEqual((cleared["name"], cleared["next"]["name"]), ("Landing Site", "Ice Field"))
        again = self.post("/planet/run", {"id": pid, "site": "1c", "code": loop})
        self.assertIsNone(again["rewards"]["zone_cleared"])

    def test_teacher_can_unlock_the_next_site(self):
        pid = self.join()
        bad = self.post("/admin", {"key": "nope", "action": "planet_unlock", "pid": pid})
        self.assertIn("error", bad)
        ok = self.post("/admin", {"key": server.ADMIN_KEY, "action": "planet_unlock",
                                  "pid": pid})
        self.assertIn("1B", ok["ok"])
        self.assertEqual(self.get(f"/planet/state?id={pid}")["current"], "1b")
        # Clearing the unlocked site goes on past it, with 1A still to do.
        self.post("/planet/run", {"id": pid, "site": "1b", "code": site("1b")[2]["reference"]})
        self.assertEqual(self.get(f"/planet/state?id={pid}")["current"], "1c")

    def transmit(self, pid, key, code):
        return self.post("/planet/run", {"id": pid, "site": key, "code": code})

    def test_code_that_isnt_text_runs_as_nothing(self):
        pid = self.join()
        self.post("/planet/run", {"id": pid, "site": "1a", "code": None})
        self.assertEqual(server.players[pid]["planet"]["code"]["1a"], "")

    def test_a_body_that_isnt_an_object_gets_an_answer(self):
        request = Request(self.base + "/planet/run", b"[1, 2]", {"Content-Type": "application/json"})
        with urlopen(request) as response:
            self.assertIn("error", json.loads(response.read()))

    def test_a_neighbours_route_says_your_planet_is_different(self):
        s = site("2c")[2]
        ids = [self.join(f"Lake{i}") for i in range(12)]
        a = ids[0]
        b = next(q for q in ids if planet.variant_index(q, s) != planet.variant_index(a, s))
        route = as_code(solve("2c", planet.variant_index(a, s)))
        server.planet_entry(server.players[b])["unlocked"] = planet.SITE_ORDER.index("2c")
        out = self.transmit(b, "2c", route)["runs"][0]
        self.assertFalse(out["reached"])
        self.assertIn("works on 1 other planet in the class, but yours is different",
                      out["explain"]["next"])
        # A route that fits nobody's lake says nothing about classmates.
        out = self.transmit(b, "2c", "north()\n")["runs"][0]
        self.assertNotIn("other planet", out["explain"]["next"])

    def test_a_run_earns_stars_and_coding_badges(self):
        pid = self.join()
        out = self.transmit(pid, "1a", site("1a")[2]["reference"])
        self.assertEqual(out["rewards"]["stars"], [True, False, True])
        self.assertEqual(out["rewards"]["new_stars"], 2)
        self.assertEqual([b["name"] for b in out["rewards"]["badges"]], ["First Contact"])
        # Stars add up across runs: the crystal run brings the third.
        out = self.transmit(pid, "1a", BONUS_PROGRAMS["1a"])
        self.assertEqual(out["rewards"]["best"], [True, True, True])
        self.assertEqual(out["rewards"]["new_stars"], 1)
        out = self.transmit(pid, "1b", BONUS_PROGRAMS["1b"])
        names = {b["name"] for b in out["rewards"]["badges"]}
        self.assertEqual(names, {"Loop Pilot", "Architect", "Function Fan"})
        self.assertEqual(out["state"]["total_stars"], 5)

    def test_fixing_a_bug_and_grit_earn_badges(self):
        pid = self.join()
        self.transmit(pid, "1a", "east(\n")
        out = self.transmit(pid, "1a", site("1a")[2]["reference"])
        self.assertIn("Bug Squasher", [b["name"] for b in out["rewards"]["badges"]])
        server.planet_entry(server.players[pid])["unlocked"] = 1
        for _ in range(5):
            missed = self.transmit(pid, "1b", "east()\n")
        self.assertEqual(missed["rewards"]["misses"], 5)   # the page offers help from 3
        out = self.transmit(pid, "1b", site("1b")[2]["reference"])
        self.assertIn("Never Give Up", [b["name"] for b in out["rewards"]["badges"]])

    def test_long_miss_runs_name_classmates_then_open_the_next_site(self):
        ada, bo = self.join("Ada"), self.join("Bo")
        self.transmit(ada, "1a", site("1a")[2]["reference"])
        for n in range(1, server.SKIP_AFTER + 1):
            out = self.transmit(bo, "1a", "east()\n")["rewards"]
            self.assertEqual(out["helpers"], ["Ada"] if n >= server.HELP_AFTER else [], n)
            self.assertEqual(out["can_skip"], n >= server.SKIP_AFTER, n)
        self.assertTrue(self.get(f"/planet/site?id={bo}&site=1a")["can_skip"])
        state = self.post("/planet/skip", {"id": bo, "site": "1a"})
        self.assertEqual(state["current"], "1b")
        self.assertIn("error", self.post("/planet/skip", {"id": bo, "site": "1b"}))
        row = next(r for r in server.planet_class()["students"] if r["name"] == "Bo")
        self.assertEqual(row["skipped"], ["1a"])   # the teacher sees it
        self.post("/planet/typing", {"id": bo, "site": "1b", "code": "east()"})
        row = next(r for r in server.planet_class()["students"] if r["name"] == "Bo")
        self.assertIsNotNone(row["typed"])
        # The finale can't be skipped.
        server.planet_entry(server.players[bo])["unlocked"] = len(planet.SITE_ORDER)
        server.planet_entry(server.players[bo])["misses"]["7"] = 99
        self.assertFalse(server.can_skip(server.players[bo], "7"))

    def test_starting_the_server_keeps_the_last_saves(self):
        with open(server.STATE_FILE, "w") as f:
            f.write("{}")
        hand_made = server.STATE_FILE + ".bak-mine"
        open(hand_made, "w").close()
        for n in range(server.BACKUPS_KEPT + 2):
            with mock.patch("time.strftime", return_value=f"2026102{n}-0900"):
                server.back_up_state()
        kept = sorted(f for f in os.listdir(self.folder.name) if ".start-" in f)
        self.assertEqual(len(kept), server.BACKUPS_KEPT)
        self.assertTrue(kept[-1].endswith("20261026-0900"))
        self.assertTrue(os.path.exists(hand_made))

    def test_the_after_class_report_groups_what_students_were_told(self):
        ada, bo = self.join("Ada"), self.join("Bo")
        for pid in (ada, bo):
            self.transmit(pid, "1a", "east(2)\n")
            self.transmit(pid, "1a", "south(1)\n")
        self.transmit(ada, "1a", site("1a")[2]["reference"])
        report = self.get("/planet/report")
        row = next(r for r in report["sites"] if r["key"] == "1a")
        self.assertEqual((row["tried"], row["cleared"]), (2, 1))
        self.assertEqual(row["not_cleared"], [["Bo", 2, True]])
        # Messages that differ only in their squares count as one.
        self.assertEqual(row["said"][0]["students"], 2)
        self.assertEqual(row["said"][0]["tries"], 4)
        self.assertEqual([r["key"] for r in report["sites"]], ["1a"])   # only sites tried
        self.assertEqual(report["zones"][0]["name"], "Landing Site")

    def test_a_miss_that_gets_further_is_the_closest_yet(self):
        pid = self.join()
        server.planet_entry(server.players[pid])["unlocked"] = 1
        first = self.transmit(pid, "1b", "east()\nsouth()\n")["rewards"]
        self.assertIsNone(first["closer"])        # the first miss only sets the mark
        better = self.transmit(pid, "1b", "for i in range(3):\n    east()\n    south()\n")["rewards"]
        self.assertEqual(better["closer"], "3 of 8 samples (before: 1 of 8 samples)")
        same = self.transmit(pid, "1b", "for i in range(2):\n    east()\n    south()\n")["rewards"]
        self.assertIsNone(same["closer"])         # not better than 3
        self.assertIsNone(self.transmit(pid, "1b", site("1b")[2]["reference"])["rewards"]["closer"])

    def test_beacon_progress_counts_squares_round_rock(self):
        zi, zone, s = site("3b")
        v = s["variants"][0]
        near, far = (planet.progress(v, planet.drive(c, v, zone["rules"], zi))
                     for c in ("south(3)\n", "south()\n"))
        self.assertEqual(near[0], "less")
        self.assertLess(near[1], far[1])
        portal = site("6a")
        self.assertIsNone(planet.progress(portal[2]["variants"][0], run("6a", "east()\n")))

    def test_the_teacher_can_put_one_program_on_the_class_screen(self):
        pid = self.join("Ada")
        nothing = self.post("/admin", {"key": server.ADMIN_KEY, "action": "planet_spotlight", "pid": pid})
        self.assertIn("hasn't transmitted", nothing["ok"])
        self.transmit(pid, "1a", site("1a")[2]["reference"])
        self.post("/admin", {"key": server.ADMIN_KEY, "action": "planet_spotlight", "pid": pid})
        spot = self.get("/planet/overview")["spotlight"]
        self.assertEqual((spot["site"], spot["done"]), ("1a", True))
        self.assertEqual(spot["code"], site("1a")[2]["reference"].strip())
        self.assertNotIn("Ada", json.dumps(spot))   # no name on the projector
        self.post("/admin", {"key": server.ADMIN_KEY, "action": "planet_spotlight_off"})
        self.assertIsNone(self.get("/planet/overview")["spotlight"])

    def test_the_page_knows_whether_you_ever_ran(self):
        pid = self.join()
        self.assertFalse(self.get(f"/planet/state?id={pid}")["you"]["ran"])
        self.transmit(pid, "1a", "east()\n")
        self.assertTrue(self.get(f"/planet/state?id={pid}")["you"]["ran"])

    def test_class_records_and_the_feed(self):
        ada, bo = self.join("Ada"), self.join("Bo")
        slow = "wait()\n" + site("1a")[2]["reference"]
        first = self.transmit(ada, "1a", slow)["rewards"]["record"]
        self.assertEqual((first["name"], first["first"]), ("Ada", True))
        beat = self.transmit(bo, "1a", site("1a")[2]["reference"])["rewards"]
        self.assertEqual((beat["record"]["ticks"], beat["record"]["first"]), (16, False))
        self.assertIn("Record Breaker", [b["name"] for b in beat["badges"]])
        self.assertEqual(self.get(f"/planet/site?id={ada}&site=1a")["record"],
                         {"ticks": 16, "name": "Bo"})
        overview = self.get("/planet/overview")
        self.assertTrue(any("class record" in m["text"] for m in overview["feed"]))
        self.assertEqual(overview["class"]["stars"], 3)   # Ada's slow run isn't compact
        self.assertTrue(overview["address"].endswith("/planet"))

    def test_a_measurement_has_no_class_record(self):
        pid = self.join()
        server.planet_entry(server.players[pid])["unlocked"] = 3
        out = self.transmit(pid, "2a", site("2a")[2]["reference"])
        self.assertTrue(out["runs"][0]["reached"])
        self.assertIsNone(out["rewards"]["record"])
        self.assertIsNone(self.get(f"/planet/site?id={pid}&site=2a")["record"])
        self.assertEqual(self.get(f"/planet/site?id={pid}&site=2a")["mission"], "report")

    def test_the_garage_only_fits_what_you_have_unlocked(self):
        pid = self.join()
        self.assertEqual(self.post("/planet/look", {"id": pid, "paint": "gold"})["look"]["paint"],
                         "bone")
        self.assertEqual(self.transmit(pid, "1a", site("1a")[2]["reference"])
                         ["rewards"]["unlocked"],   # 2 stars: the bunny, not the paint yet
                         [{"slot": "pet", "key": "bunny", "name": "Bunny", "rarity": "common"}])
        out = self.transmit(pid, "1a", BONUS_PROGRAMS["1a"])   # the third star
        self.assertEqual(out["rewards"]["unlocked"], [{"slot": "paint", "key": "coral", "name": "Coral", "rarity": "common"}])
        self.assertEqual(self.post("/planet/look", {"id": pid, "paint": "coral"})["look"]["paint"],
                         "coral")

    def test_the_practice_zones_hide_gifts_in_easy_mode(self):
        pid = self.join()
        garage = lambda: {i["key"]: i for i in self.get(f"/planet/state?id={pid}")["garage"]}
        self.assertNotIn("chick", garage())   # no practice zones, so no practice gifts
        server.planet_class_settings["easy"] = True
        try:
            self.assertEqual(garage()["chick"]["where"], "Downhill (P2)")
            self.assertTrue(self.get(f"/planet/state?id={pid}")["zones"][0]["sites"][1]["gift"])
            out = self.post("/planet/run", {"id": pid, "site": "p2", "code": "east()\nsouth()\n"})
            self.assertEqual(out["rewards"]["found"][0]["key"], "chick")
            self.assertTrue(garage()["chick"]["open"])
        finally:
            server.planet_class_settings["easy"] = False
        self.assertTrue(garage()["chick"]["open"])   # found stays found

    def test_driving_over_a_gift_finds_a_garage_item(self):
        pid = self.join()
        self.assertEqual(self.get(f"/planet/site?id={pid}&site=1a")["gift"], [1, 4])
        gifts = lambda: {x["key"]: x["gift"] for z in self.get(f"/planet/state?id={pid}")["zones"]
                         for x in z["sites"]}
        self.assertEqual((gifts()["1a"], gifts()["1b"]), (True, False))
        self.assertEqual(self.post("/planet/look", {"id": pid, "paint": "grass"})["look"]["paint"],
                         "bone")
        # Scouting past it doesn't open it.
        self.post("/planet/scout", {"id": pid, "site": "1a", "moves": ["east"] * 3})
        self.assertEqual(self.get(f"/planet/site?id={pid}&site=1a")["gift"], [1, 4])
        # A run that drives over it does, mission or not.
        out = self.transmit(pid, "1a", "east(3)\n")
        self.assertFalse(out["runs"][0]["reached"])
        self.assertEqual(out["rewards"]["found"],
                         [{"slot": "paint", "key": "grass", "name": "Grass Block", "rarity": "epic"}])
        self.assertEqual(out["rewards"]["unlocked"], [])
        self.assertIn("tick 3: 🎁 found a mystery gift: Grass Block!", out["runs"][0]["log"])
        self.assertIsNone(self.get(f"/planet/site?id={pid}&site=1a")["gift"])
        self.assertFalse(gifts()["1a"])
        self.assertEqual(self.transmit(pid, "1a", "east(3)\n")["rewards"]["found"], [])
        self.assertEqual(self.post("/planet/look", {"id": pid, "paint": "grass"})["look"]["paint"],
                         "grass")
        self.assertTrue(any("mystery gift" in m["text"] for m in self.get("/planet/overview")["feed"]))
        # A classmate's gift is still waiting for them.
        bo = self.join("Bo")
        self.assertEqual(self.get(f"/planet/site?id={bo}&site=1a")["gift"], [1, 4])

    def test_finding_every_gift_earns_treasure_hunter(self):
        pid = self.join()
        entry = server.planet_entry(server.players[pid])
        entry["found"] = [i["key"] for k, i in server.GIFTS.items() if k != "1a"]
        out = self.transmit(pid, "1a", "east(3)\n")
        self.assertIn("Treasure Hunter", [b["name"] for b in out["rewards"]["badges"]])

    def test_the_map_look_is_a_garage_slot(self):
        pid = self.join()
        self.assertEqual(self.get(f"/planet/state?id={pid}")["look"]["world"], "planet")
        self.assertEqual(self.post("/planet/look", {"id": pid, "world": "moon"})["look"]["world"],
                         "planet")
        server.planet_entry(server.players[pid])["stars"]["1a"] = [True] * 3
        server.planet_entry(server.players[pid])["stars"]["1b"] = [True] * 3
        self.assertEqual(self.post("/planet/look", {"id": pid, "world": "moon"})["look"]["world"],
                         "moon")

    def test_a_site_added_later_never_sends_anyone_back(self):
        pid = self.join()
        entry = server.planet_entry(server.players[pid])
        before = planet.SITE_ORDER[:planet.SITE_ORDER.index("9e")]
        entry["solved"] = {k: 10 for k in before}   # best ticks
        self.assertEqual(self.get(f"/planet/state?id={pid}")["current"], "9e")
        # Someone who got further before 9E was there carries on where they were.
        entry["solved"]["10a"] = 10
        self.assertEqual(self.get(f"/planet/state?id={pid}")["current"], "10b")

    def test_scouting_drives_by_hand_but_saves_nothing(self):
        pid = self.join()
        out = self.post("/planet/scout", {"id": pid, "site": "1a",
                                          "moves": ["east", "east", "east", "south"]})
        self.assertEqual(out["run"]["frames"][-1]["c"], 4)
        self.assertEqual(out["left"], server.SCOUT_MAX - 4)
        self.assertIn("error", self.post("/planet/scout", {"id": pid, "site": "1a",
                                                           "moves": ["import os"]}))
        self.assertIn("error", self.post("/planet/scout", {"id": pid, "site": "1b",
                                                           "moves": ["east"]}))
        state = self.get(f"/planet/state?id={pid}")
        self.assertEqual((state["total_stars"], state["current"]), (0, "1a"))

    def test_scouting_jumps_and_drills_once_code_can(self):
        pid = self.join()
        server.planet_entry(server.players[pid])["unlocked"] = len(planet.SITE_ORDER)
        scout = lambda key, moves: self.post("/planet/scout", {"id": pid, "site": key, "moves": moves})
        self.assertIn("error", scout("7a", ["jump:east"]))      # before Crater Hops
        self.assertIn("error", scout("8a", ["drill:east"]))     # before The Quarry
        self.assertIn("error", scout("8a", ["jump:up"]))
        self.assertIn("error", scout("8a", [["jump", "east"]]))
        out = scout("10a", ["east"] * 3 + ["drill:east"] + ["east"] * 5)
        self.assertEqual(out["run"]["end"], "goal")
        self.assertIn("tick 4: ⛏ drilled through the rock, 0 drills left", out["run"]["log"])
        self.assertEqual(scout("16b", ["south"] * 2 + ["east"] * 6 + ["jump:east"])["run"]["frames"][-1]["c"], 9)

    def test_teacher_can_remove_a_student(self):
        ada, bo = self.join("Ada"), self.join("Bo")
        self.post("/planet/run", {"id": bo, "site": "1a", "code": "east()\n"})
        bad = self.post("/admin", {"key": "nope", "action": "planet_remove", "pid": bo})
        self.assertIn("error", bad)
        ok = self.post("/admin", {"key": server.ADMIN_KEY, "action": "planet_remove", "pid": bo})
        self.assertIn("Bo", ok["ok"])
        names = [r["name"] for r in self.get("/planet/overview")["students"]]
        self.assertNotIn("Bo", names)
        self.assertIn(bo, server.players)   # the other games keep them

    def test_teacher_switches_scouted_code_blanks(self):
        pid = self.join()
        scout = lambda: self.post("/planet/scout", {"id": pid, "site": "1a", "moves": ["east"]})
        self.assertTrue(scout()["blanks"])
        self.assertTrue(self.get("/planet/overview")["blanks"])
        self.post("/admin", {"key": "nope", "action": "planet_blanks", "on": False})
        self.assertTrue(scout()["blanks"])
        self.post("/admin", {"key": server.ADMIN_KEY, "action": "planet_blanks", "on": False})
        self.assertFalse(scout()["blanks"])
        self.assertFalse(self.get("/planet/overview")["blanks"])
        self.assertFalse(json.load(open(server.STATE_FILE))["planet_class"]["blanks"])

    def test_teacher_switches_letter_by_letter_typing(self):
        pid = self.join()
        scout = lambda: self.post("/planet/scout", {"id": pid, "site": "1a", "moves": ["east"]})
        self.assertFalse(scout()["coach"])
        self.post("/admin", {"key": server.ADMIN_KEY, "action": "planet_blanks", "on": False})
        self.post("/admin", {"key": server.ADMIN_KEY, "action": "planet_coach", "on": True})
        self.assertTrue(scout()["coach"])
        self.assertTrue(scout()["blanks"])   # letter by letter needs words to finish
        self.assertTrue(self.get("/planet/overview")["coach"])
        self.post("/admin", {"key": server.ADMIN_KEY, "action": "planet_coach", "on": False})
        self.assertFalse(scout()["coach"])
        self.post("/admin", {"key": server.ADMIN_KEY, "action": "planet_easy", "on": True})
        self.assertTrue(scout()["coach"])

    def test_easy_mode_helps_sooner(self):
        ada, bo = self.join("Ada"), self.join("Bo")
        self.transmit(ada, "1a", site("1a")[2]["reference"])
        self.post("/admin", {"key": server.ADMIN_KEY, "action": "planet_easy", "on": True})
        self.assertTrue(self.get("/planet/overview")["easy"])
        self.assertTrue(self.get("/planet/overview")["blanks"])   # kids finish the words
        for n in range(1, server.EASY_SKIP_AFTER + 1):
            out = self.transmit(bo, "1a", "east()\n")["rewards"]
            self.assertEqual(out["helpers"], ["Ada"] if n >= server.EASY_HELP_AFTER else [], n)
            self.assertEqual(out["can_skip"], n >= server.EASY_SKIP_AFTER, n)
        self.assertTrue(json.load(open(server.STATE_FILE))["planet_class"]["easy"])
        self.post("/admin", {"key": server.ADMIN_KEY, "action": "planet_easy", "on": False})
        self.assertTrue(self.get("/planet/overview")["blanks"])
        self.assertFalse(self.get(f"/planet/site?id={bo}&site=1a")["can_skip"])

    def test_practice_park_only_in_easy_mode(self):
        pid = self.join()
        state = self.get(f"/planet/state?id={pid}")
        self.assertNotIn("practice", [z["key"] for z in state["zones"]])
        self.assertIn("error", self.post("/planet/run", {"id": pid, "site": "p1", "code": "east()\n"}))
        self.post("/admin", {"key": server.ADMIN_KEY, "action": "planet_easy", "on": True})
        state = self.get(f"/planet/state?id={pid}")
        self.assertEqual(state["zones"][0]["key"], "practice")
        self.assertEqual(state["current"], "p1")
        self.assertEqual([z["key"] for z in state["zones"][:8]],
                         ["practice", "garden", "rink", "pads", "bounce", "lookout", "forks", "landing"])
        self.assertEqual(state["zones"][7]["zi"], 0)   # the Landing Site keeps its sensors
        for key in planet.PRACTICE_ORDER:
            s = planet.find_site(key)[2]
            out = self.transmit(pid, key, s["reference"])
            self.assertEqual(out["rewards"]["stars"], [True], key)   # one star: they're easy
            if key == "p8":
                self.assertEqual(out["rewards"]["zone_cleared"]["next"]["key"], "garden")
            if key == "p16":
                self.assertEqual(out["rewards"]["zone_cleared"]["next"]["key"], "rink")
            if key == "p24":
                self.assertEqual(out["rewards"]["zone_cleared"]["next"]["key"], "pads")
            if key == "p30":
                self.assertEqual(out["rewards"]["zone_cleared"]["next"]["key"], "bounce")
            if key == "p38":
                self.assertEqual(out["rewards"]["zone_cleared"]["next"]["key"], "lookout")
            if key == "p46":
                self.assertEqual(out["rewards"]["zone_cleared"]["next"]["key"], "forks")
        self.assertEqual(out["rewards"]["zone_cleared"]["next"]["key"], "landing")
        self.assertEqual(out["state"]["current"], "1a")
        self.assertFalse(self.get(f"/planet/site?id={pid}&site=p1")["can_skip"])
        self.post("/admin", {"key": server.ADMIN_KEY, "action": "planet_easy", "on": False})
        state = self.get(f"/planet/state?id={pid}")
        self.assertNotIn("practice", [z["key"] for z in state["zones"]])
        self.assertEqual(state["current"], "1a")   # nobody's way is blocked

    def test_new_practice_zones_never_send_anyone_back(self):
        self.post("/admin", {"key": server.ADMIN_KEY, "action": "planet_easy", "on": True})
        try:
            pid = self.join()
            entry = server.planet_entry(server.players[pid])
            entry["solved"] = {k: 5 for k in planet.PRACTICE_ORDER if k not in planet.LATE_PRACTICE}
            self.assertEqual(self.get(f"/planet/state?id={pid}")["current"], "p39")
            entry["solved"]["1a"] = 10   # already on the main route: carries on there
            self.assertEqual(self.get(f"/planet/state?id={pid}")["current"], "1b")
        finally:
            self.post("/admin", {"key": server.ADMIN_KEY, "action": "planet_easy", "on": False})

    def test_jump_park_scouts_with_jumps_and_shows_a_short_kit(self):
        pid = self.join()
        jump = lambda key: self.post("/planet/scout", {"id": pid, "site": key, "moves": ["east", "jump:east", "east"]})
        self.assertIn("error", jump("p31"))   # practice sites are closed outside easy mode
        self.post("/admin", {"key": server.ADMIN_KEY, "action": "planet_easy", "on": True})
        self.assertEqual(jump("p31")["run"]["end"], "goal")
        self.assertIn("error", jump("p25"))   # Pad Park drives without jumping
        self.assertEqual(self.get(f"/planet/site?id={pid}&site=p31")["sensors"], ["look", "at_beacon", "jump"])
        server.planet_entry(server.players[pid])["unlocked"] = len(planet.SITE_ORDER)
        self.assertIn("tick 2: 🦘 jumped east", jump("8a")["run"]["log"])   # Crater Hops on
        for key in [k for z in (planet.PAD_PARK, planet.JUMP_PARK) for k in (s["key"] for s in z["sites"])]:
            s = planet.find_site(key)[2]
            self.assertEqual(self.transmit(pid, key, s["reference"])["rewards"]["stars"], [True], key)

    def test_practice_sites_give_one_star_and_keep_old_ones(self):
        pid = self.join()
        self.post("/admin", {"key": server.ADMIN_KEY, "action": "planet_easy", "on": True})
        entry = server.planet_entry(server.players[pid])
        entry["stars"]["p2"] = [True, True, True]   # earned before practice gave one
        before = self.get(f"/planet/state?id={pid}")["total_stars"]
        out = self.transmit(pid, "p1", planet.find_site("p1")[2]["reference"])
        self.assertEqual(out["rewards"]["new_stars"], 1)
        self.assertEqual(out["state"]["total_stars"], before + 1)
        view = self.get(f"/planet/site?id={pid}&site=p1")
        self.assertEqual((len(view["goals"]), len(view["tips"]), view["stars"]), (1, 1, [True]))
        state = self.get(f"/planet/state?id={pid}")
        self.assertEqual(state["zones"][0]["sites"][1]["stars"], [True])
        self.assertEqual(entry["stars"]["p2"], [True, True, True])   # nothing taken away
        self.assertEqual(len(self.get(f"/planet/site?id={pid}&site=1a")["goals"]), 3)

    def test_the_teacher_sees_each_run_with_its_route(self):
        ada = self.join("Ada")
        self.assertEqual(self.get("/planet/overview")["runs"], [])
        self.transmit(ada, "1a", site("1a")[2]["reference"])
        self.transmit(ada, "1b", "east()\n")
        runs = self.get("/planet/overview")["runs"]
        self.assertEqual([(r["name"], r["site"], r["reached"]) for r in runs],
                         [("Ada", "1a", True), ("Ada", "1b", False)])
        self.assertEqual(runs[1]["n"], runs[0]["n"] + 1)
        self.assertEqual(runs[0]["path"][0][:2], [1, 1])
        self.assertEqual(runs[0]["map"], site("1a")[2]["variants"][0]["map"])
        self.assertTrue(runs[1]["said"])
        student = self.get("/planet/overview")["students"][0]
        self.assertEqual((student["misses"], student["runs_now"], student["practice"]), (1, 1, False))

    def test_field_measurements_coach_step_by_step(self):
        pid = self.join()
        server.planet_entry(server.players[pid])["unlocked"] = len(planet.SITE_ORDER)
        for key in ("2a", "3a", "5a", "7a"):
            coach = self.get(f"/planet/site?id={pid}&site={key}")["coach"]
            self.assertTrue(coach["intro"] and coach["short"])
            self.assertEqual(len(coach["steps"]), 3)
            # The last step's code is a program that gets the number.
            code = coach["steps"][-1].split("\n\n", 1)[1]
            self.assertTrue(self.transmit(pid, key, code)["runs"][0]["reached"], key)
        self.assertIn("tick", self.get(f"/planet/site?id={pid}&site=3a")["coach"]["intro"])
        self.assertIsNone(self.get(f"/planet/site?id={pid}&site=2b")["coach"])

    def test_saved_functions_are_kept_for_later_sites(self):
        pid = self.join()
        hop = "def hop(n):\n    east(n)\n    south(n)"
        self.assertEqual(self.post("/planet/functions", {"id": pid, "code": hop})["functions"],
                         [{"name": "hop", "code": hop}])
        better = "def hop(n):\n    east(n)"
        self.post("/planet/functions", {"id": pid, "code": "def other():\n    wait()"})
        out = self.post("/planet/functions", {"id": pid, "code": better})
        self.assertEqual([f["code"] for f in out["functions"]], [better, "def other():\n    wait()"])
        for broken in ("def hop(:\n    east()", "east()", hop + "\nhop(2)"):
            self.assertIn("error", self.post("/planet/functions", {"id": pid, "code": broken}))
        self.post("/planet/functions", {"id": pid, "remove": "other"})
        server.players.clear()
        server.load_state()
        self.assertEqual(self.get(f"/planet/state?id={pid}")["functions"],
                         [{"name": "hop", "code": better}])

    def test_the_class_screen_shows_each_rover_and_its_code(self):
        pid = self.join()
        now = self.get("/planet/overview")["students"]
        self.assertEqual(now, [])
        self.post("/planet/typing", {"id": pid, "site": "1a", "code": "east(3)"})
        now = self.get("/planet/overview")["students"][0]["now"]
        start = site("1a")[2]["variants"][0]["map"]
        self.assertEqual((now["site"], now["code"], now["map"]), ("1a", "east(3)", start))
        self.assertEqual(start[now["pos"][0]][now["pos"][1]], "S")
        self.post("/planet/run", {"id": pid, "site": "1a", "code": "east(3)\nsouth()"})
        self.post("/planet/typing", {"id": pid, "site": "1a", "code": "east(3)\nsouth()\n"})
        now = self.get("/planet/overview")["students"][0]["now"]
        self.assertEqual((now["pos"], now["end"]), ([2, 4], "stopped"))
        # A locked site isn't shown, and nothing in the map gives a rule away.
        self.post("/planet/typing", {"id": pid, "site": "3c", "code": "x"})
        self.assertEqual(self.get("/planet/overview")["students"][0]["now"]["site"], "1a")
        self.assertEqual(set(now), {"site", "site_name", "zone", "zone_name", "map", "pos", "end", "code", "said"})

    def test_progress_survives_a_restart(self):
        pid = self.join()
        self.post("/planet/run", {"id": pid, "site": "1a",
                                  "code": site("1a")[2]["reference"]})
        server.players.clear()
        server.load_state()
        self.assertEqual(self.get(f"/planet/state?id={pid}")["current"], "1b")


def spooky(code, variant):
    """Run code on a Halloween night map: knock() and candy() included."""
    return planet.drive(code, variant, {"spooky"}, 0)


def halloween_sites():
    for zone in planet.HALLOWEEN_ZONES:
        for s in zone["sites"]:
            yield zone, s


class HalloweenTests(unittest.TestCase):
    """Halloween night: knock() at houses for candy, haunted houses and ghosts
    say BOO, and each site's claim holds on every street."""

    STREET = {"map": ["#########",
                      "###h#z###",
                      "#S......#",
                      "#########"]}

    def test_every_site_has_a_reference_that_clears_every_street(self):
        for zone, s in halloween_sites():
            seeds = range(30) if s["key"] in planet.NIGHTLY else [None]
            for vi, v in enumerate(s["variants"]):
                for seed in seeds:
                    vv = v if seed is None else dict(v, seed=seed)
                    out = planet.drive(s["reference"], vv, zone["rules"], zone.get("zi", 0))
                    self.assertTrue(out["reached"], (s["key"], vi, seed, out["log"][-2:], out["error"]))
            self.assertLessEqual(planet.code_lines(s["reference"]), s["compact"], s["key"])
            self.assertEqual(len(zone["hints"]), 3, zone["key"])

    def test_a_knock_on_a_lit_door_fills_the_bag_once(self):
        out = spooky('east(2)\nknock("north")\nprint(candy())\nknock("north")\nprint(candy())\n'
                     'east(2)\nknock("south")', dict(self.STREET, map=self.STREET["map"][:1] +
                                                      ["###h#h###"] + self.STREET["map"][2:]))
        given = planet.treats(1, 3)
        self.assertIn(2, range(2, 6))
        self.assertEqual([p["text"] for p in out["prints"]], [str(given), str(given)])
        self.assertTrue(any("already got candy here" in line for line in out["log"]))
        self.assertTrue(any("no door there" in line for line in out["log"]))
        self.assertEqual(out["houses"], [1, 2])
        self.assertEqual(out["end"], "stopped")
        self.assertIn("1 lit house still to visit", out["explain"]["what"])
        self.assertIn("knock() found no door 1 time", out["explain"]["what"])

    def test_knocking_on_every_lit_house_is_the_mission(self):
        out = spooky('east(2)\nknock("north")', self.STREET)
        self.assertTrue(out["reached"])
        self.assertEqual(out["mission"], "treats")
        self.assertEqual(out["candy"], planet.treats(1, 3))
        self.assertEqual(out["frames"][-2]["kn"], [1, 3, planet.treats(1, 3)])

    def test_a_haunted_house_says_boo(self):
        out = spooky('east(4)\nknock("north")', self.STREET)
        self.assertEqual(out["end"], "spooked")
        self.assertEqual(out["spooked"], "haunted")
        self.assertIn('look("north") says "haunted"', out["explain"]["next"])
        self.assertEqual(spooky('east(4)\nprint(look("north"))\nwest(2)\nprint(look("north"))',
                                self.STREET)["prints"][-2:], [{"t": 4, "text": "haunted"}, {"t": 6, "text": "house"}])

    def test_houses_are_solid_and_knock_needs_a_way(self):
        out = spooky('east(2)\nnorth()', self.STREET)
        self.assertEqual(out["bumps"], 1)
        self.assertTrue(any("bumped into a house" in line for line in out["log"]))
        self.assertIn('knock("north")', spooky("knock()", self.STREET)["error"])
        self.assertIn('knock("north")', spooky("knock(north)\nknock(1)", self.STREET)["error"])

    def test_knock_and_candy_are_only_for_halloween_night(self):
        for code in ('knock("north")', "print(candy())"):
            out = planet.drive(code, self.STREET, set(), 0)
            self.assertIn("Halloween night", out["error"])

    def test_ghosts_float_through_a_waiting_rover_but_boo_one_that_drives_in(self):
        v = {"map": ["#######", "#S...G#", "#######"], "ghosts": [{"path": [[0, 3], [1, 3], [2, 3]]}]}
        rush = spooky("east(4)", v)
        self.assertEqual(rush["end"], "spooked")
        self.assertEqual(rush["spooked"], "ghost")
        self.assertIn('while look("east") == "ghost"', rush["explain"]["next"])
        careful = spooky('east()\nwhile look("east") == "ghost":\n    wait()\neast(3)', v)
        self.assertTrue(careful["reached"])
        # A ghost floating onto a rover that waits there does nothing.
        sit = {"map": ["#####", "#S.G#", "#####"], "ghosts": [{"path": [[1, 1], [0, 1]], "start": 1}]}
        self.assertTrue(spooky("wait()\nwait()\nwait()\neast(2)", sit)["reached"])
        self.assertEqual([f["gh"] for f in careful["frames"][:3]], [[[0, 3]], [[1, 3]], [[2, 3]]])

    def test_ground_candy_counts_and_can_be_the_mission(self):
        field = {"map": ["######", "#Sccc#", "######"]}
        out = spooky("east(3)", field)
        self.assertTrue(out["reached"])
        self.assertEqual((out["mission"], out["candy"], out["candy_left"]), ("candy", 3, 0))
        self.assertEqual(spooky('print(look("east"))', field)["prints"][0]["text"], "candy")

    def test_shortcuts_that_dont_check_get_spooked(self):
        cases = {"h4": 'for i in range(6):\n    east(2)\n    knock("north")\n',
                 "h5": 'east(12)\nknock("north")\n',
                 "h9": planet.PARADE_RUSH,
                 "h13": planet.GHOST_WALK_RUSH}
        for key, code in cases.items():
            zone, s = next((z, x) for z, x in halloween_sites() if x["key"] == key)
            for vi, v in enumerate(s["variants"]):
                self.assertEqual(spooky(code, v)["end"], "spooked", (key, vi))

    def test_a_route_timed_for_one_street_fails_on_the_others(self):
        for key in ("h4", "h5", "h7", "h9", "h12", "h13"):
            zone, s = next((z, x) for z, x in halloween_sites() if x["key"] == key)
            own = spooky(s["reference"], s["variants"][0])
            moves = []
            for a, b in zip(own["frames"], own["frames"][1:]):
                if b.get("kn"):
                    way = {(-1, 0): "north", (1, 0): "south", (0, 1): "east", (0, -1): "west"}[
                        (b["kn"][0] - b["r"], b["kn"][1] - b["c"])]
                    moves.append(f'knock("{way}")')
                elif b.get("e") == "wait":
                    moves.append("wait()")
                elif (b["r"], b["c"]) != (a["r"], a["c"]):
                    moves.append({(0, 1): "east()", (0, -1): "west()", (1, 0): "south()",
                                  (-1, 0): "north()"}[(b["r"] - a["r"], b["c"] - a["c"])])
            plan = "\n".join(moves)
            self.assertTrue(spooky(plan, s["variants"][0])["reached"], key)
            others = [spooky(plan, v)["reached"] for v in s["variants"][1:]]
            self.assertIn(False, others, key)
            run_ = spooky(plan, s["variants"][0])
            self.assertFalse(planet.everywhere(s, plan, run_), key)

    def test_the_mansion_picks_its_haunted_houses_every_night(self):
        zone, s = next((z, x) for z, x in halloween_sites() if x["key"] == "h10")
        v = s["variants"][0]
        maps = {tuple(spooky("wait()", dict(v, seed=seed))["map"]) for seed in range(12)}
        self.assertGreater(len(maps), 6)
        for m in maps:
            self.assertEqual("".join(m).count("z"), 4)
            self.assertNotIn("m", "".join(m))
        self.assertEqual(spooky("wait()", dict(v, seed=3))["map"], spooky("wait()", dict(v, seed=3))["map"])
        # A program that knocks on every house it passes, without looking, is
        # spooked on almost every night.
        blind = s["reference"].replace('    if look(way) == "house":\n        knock(way)\n',
                                       "    knock(way)\n")
        self.assertNotEqual(blind, s["reference"])
        ends = [spooky(blind, dict(v, seed=seed))["end"] for seed in range(20)]
        self.assertEqual(ends.count("spooked"), 20)
        goals = planet.goals(s, v)
        self.assertEqual(goals[0], "🏠 Every lit house, then 🛰 the beacon")

    def test_halloween_stars_and_bonuses(self):
        zone, s = next((z, x) for z, x in halloween_sites() if x["key"] == "h1")
        v = s["variants"][0]
        plain = spooky(s["reference"], v)
        self.assertEqual(planet.stars(s, v, plain, s["reference"]), [True, False, True])
        self.assertEqual(plain["candy"], 5)   # a full-size bar from the first door
        pumpkin = 'east(6)\nwest(2)\nknock("north")'
        self.assertEqual(planet.stars(s, v, spooky(pumpkin, v), pumpkin), [True, True, False])
        zone, s = next((z, x) for z, x in halloween_sites() if x["key"] == "h2")
        nooks = 'for i in range(5):\n    east(2)\n    south()\n    north()\n    knock("north")\n'
        out = spooky(nooks, s["variants"][0])
        self.assertEqual(planet.stars(s, s["variants"][0], out, nooks), [True, True, False])
        self.assertEqual(planet.bonus_label({"kind": "candy"}), "🍬 Pick up every candy on the ground")

    def test_every_mission_done_reaches_the_end_of_the_candy_road(self):
        # The unluckiest streets, and the mansion's meanest night, with no
        # candy picked up off the ground unless that's the mission.
        total = 0
        for zone, s in halloween_sites():
            nights = [dict(v, seed=seed) for v in s["variants"] for seed in range(60)] \
                if s["key"] in planet.NIGHTLY else s["variants"]
            total += min(spooky(s["reference"], v)["candy"] for v in nights)
        self.assertGreaterEqual(total, max(i["candy"] for i in server.CANDY_ROAD))

    def test_the_witch_wants_her_count_worked_out_in_code(self):
        zone, s = next((z, x) for z, x in halloween_sites() if x["key"] == "h11")
        answers = [v["answer"] for v in s["variants"]]
        self.assertEqual(len(set(answers)), len(answers))   # every street its own total
        v = s["variants"][0]
        knocks = 'for i in range(5):\n    east(2)\n    knock("north")\n'
        own = spooky(knocks + f"report({v['answer']})", v)
        self.assertTrue(own["reached"])
        self.assertEqual(planet.stars(s, v, own, knocks + "report(1)"), [True, False, True])
        copied = spooky(knocks + f"report({answers[1]})", v)
        self.assertEqual(copied["end"], "wrong")
        self.assertIn("someone else's street", copied["explain"]["what"])
        early = spooky("report(candy())", v)
        self.assertIn("5 lit houses still had candy", early["explain"]["what"])
        self.assertEqual(planet.goals(s, v)[0], "🧙 Tell the witch your candy count")
        # The party: a different count every night, so only candy() gets it.
        zone, s = next((z, x) for z, x in halloween_sites() if x["key"] == "h14")
        night = spooky(s["reference"], dict(s["variants"][0], seed=5))
        typed = s["reference"].replace("report(candy())", f"report({night['candy']})")
        ends = [spooky(typed, dict(s["variants"][0], seed=seed))["end"] for seed in range(20)]
        self.assertIn("wrong", ends)

    def test_the_witchs_path_never_hides_a_house_east_of_the_path(self):
        zone, s = next((z, x) for z, x in halloween_sites() if x["key"] == "h12")
        for v in s["variants"]:
            m = v["map"]
            for r, row in enumerate(m):
                for c, ch in enumerate(row):
                    if ch in "hz":
                        self.assertIn(m[r + 1][c], ".G", (r, c))   # right above the path
                        self.assertNotIn(m[r][c - 1], ".SG", (r, c))   # nothing to walk into
            self.assertEqual("".join(m).count("z"), 1)

    def test_every_halloween_gift_is_on_open_ground_next_to_the_road(self):
        for key in ("h3", "h8"):
            zone, s = next((z, x) for z, x in halloween_sites() if x["key"] == key)
            for vi, v in enumerate(s["variants"]):
                r, c = planet.gift_square(key, vi)
                self.assertEqual(v["map"][r][c], ".", (key, vi))
                self.assertEqual(v["map"][r + 1][c], ".", (key, vi))


class PageScriptTests(unittest.TestCase):
    """Every script the planet pages run parses, so one slip can't leave a
    student with a blank page."""

    def test_every_page_script_parses(self):
        import shutil
        import subprocess
        node = shutil.which("node")
        if not node:
            self.skipTest("node isn't installed")
        with tempfile.TemporaryDirectory() as folder:
            for name in ("planet.html", "planet_teacher.html", "planet_show.html", "planet_render.js",
                         "planet_replay.js", "planet_halloween.js"):
                text = open(os.path.join(HERE, name), encoding="utf-8").read()
                parts = re.findall(r"<script>(.*?)</script>", text, re.S) if name.endswith(".html") else [text]
                for i, part in enumerate(parts):
                    path = os.path.join(folder, f"{name}.{i}.js")
                    with open(path, "w", encoding="utf-8") as f:
                        f.write(part)
                    out = subprocess.run([node, "--check", path], capture_output=True, text=True)
                    self.assertEqual(out.returncode, 0, f"{name}: {out.stderr[:400]}")


class HalloweenClassroomTests(unittest.TestCase):
    """Halloween night in the classroom: the teacher invites students, candy
    fills the candy road, and limited-time things stay with whoever won them."""

    setUp, get, post, join = ClassroomTests.setUp, ClassroomTests.get, ClassroomTests.post, ClassroomTests.join

    def tearDown(self):
        ClassroomTests.tearDown(self)
        server.planet_class_settings["halloween"] = True

    def admin(self, action, **data):
        return self.post("/admin", dict(data, key=server.ADMIN_KEY, action=action))

    def transmit(self, pid, key, code=None):
        code = code if code is not None else planet.find_site(key)[2]["reference"]
        return self.post("/planet/run", {"id": pid, "site": key, "code": code})

    def test_halloween_night_opens_only_for_students_the_teacher_invites(self):
        ada, bo = self.join("Ada"), self.join("Bo")
        self.get(f"/planet/state?id={ada}"); self.get(f"/planet/state?id={bo}")
        self.assertIsNone(self.get(f"/planet/state?id={ada}")["halloween"])
        self.assertIn("error", self.transmit(ada, "h1"))
        self.assertFalse(self.get(f"/planet/ping?id={ada}")["halloween"])
        self.assertIn("Invited Ada", self.admin("planet_invite", pid=ada, on=True)["ok"])
        self.assertTrue(self.get(f"/planet/ping?id={ada}")["halloween"])
        state = self.get(f"/planet/state?id={ada}")
        spooky_zones = [z for z in state["zones"] if z.get("halloween")]
        self.assertEqual([z["key"] for z in spooky_zones], ["street", "hollow", "woods"])
        self.assertEqual([x["open"] for x in spooky_zones[0]["sites"]], [True, False, False, False, False])
        self.assertEqual(state["halloween"]["next"], "h1")
        self.assertIsNone(self.get(f"/planet/state?id={bo}")["halloween"])
        self.assertIn("error", self.get(f"/planet/site?id={ada}&site=h2"))
        out = self.transmit(ada, "h1")
        self.assertTrue(out["runs"][0]["reached"])
        self.assertEqual(out["rewards"]["candy"]["total"], 5)
        self.assertEqual(out["state"]["halloween"]["next"], "h2")
        self.assertIn("ghosts", self.get(f"/planet/site?id={ada}&site=h2"))
        # Inviting everyone, and putting it away.
        self.assertIn("all 2", self.admin("planet_invite_all", on=True)["ok"])
        self.assertTrue(self.get(f"/planet/ping?id={bo}")["halloween"])
        self.admin("planet_halloween", on=False)
        self.assertFalse(self.get(f"/planet/ping?id={ada}")["halloween"])
        self.assertIn("closed", self.transmit(ada, "h2")["error"])
        overview = self.get("/planet/overview")
        self.assertFalse(overview["halloween"])
        ada_row = next(s for s in overview["students"] if s["id"] == ada)
        self.assertEqual(ada_row["halloween"]["candy"], 5)

    def test_candy_is_the_best_haul_on_each_site_and_a_boo_drops_it(self):
        pid = self.join()
        self.get(f"/planet/state?id={pid}")
        self.admin("planet_invite", pid=pid, on=True)
        for key in ("h1", "h2", "h3"):
            self.transmit(pid, key)
        entry = server.planet_entry(server.players[pid])
        before = server.candy_total(entry)
        self.assertEqual(before, sum(entry["candy"].values()))
        # A run that knocks on the haunted house drops what it collected.
        h4 = planet.find_site("h4")[2]
        v = h4["variants"][planet.variant_index(pid, h4)]
        out = self.transmit(pid, "h4", 'for i in range(6):\n    east(2)\n    knock("north")\n')
        self.assertEqual(out["runs"][0]["end"], "spooked")
        self.assertTrue(out["rewards"]["candy"]["dropped"] or out["runs"][0]["candy"] == 0)
        self.assertEqual(server.candy_total(entry), before)
        self.assertIn("😱", [b["icon"] for b in out["rewards"]["badges"]])
        out = self.transmit(pid, "h4")
        self.assertEqual(server.candy_total(entry), before + out["runs"][0]["candy"])
        again = self.transmit(pid, "h4")
        self.assertEqual(server.candy_total(entry), before + out["runs"][0]["candy"])   # the best, not a sum
        self.assertEqual(again["rewards"]["candy"]["total"] - again["rewards"]["candy"]["before"], 0)
        self.assertIn("🔦", [b["icon"] for b in out["rewards"]["badges"]])
        self.assertTrue(v)

    def test_halloween_stars_stay_out_of_the_planet_stars(self):
        pid = self.join()
        self.get(f"/planet/state?id={pid}")
        self.admin("planet_invite", pid=pid, on=True)
        out = self.transmit(pid, "h1", 'east(6)\nwest(2)\nknock("north")')
        self.assertEqual(out["rewards"]["stars"], [True, True, False])
        self.assertEqual(out["rewards"]["new_stars"], 0)
        state = out["state"]
        self.assertEqual(state["total_stars"], 0)
        self.assertEqual(state["halloween"]["stars"], 2)
        self.assertEqual(state["rank"]["name"], "Cadet")
        self.assertEqual(self.get("/planet/overview")["class"]["stars"], 0)

    def test_limited_things_are_out_only_while_halloween_is_and_stay_once_won(self):
        pid = self.join()
        self.get(f"/planet/state?id={pid}")
        limited = lambda: {i["key"]: i for i in self.get(f"/planet/state?id={pid}")["garage"] if i.get("limited")}
        self.assertEqual(limited(), {})
        self.admin("planet_invite", pid=pid, on=True)
        items = limited()
        self.assertEqual(len(items), len(server.HALLOWEEN_GARAGE))
        self.assertFalse(items["witchhat"]["open"])
        self.assertEqual(items["candybucket"]["where"], "Both Sides (H3)")
        for key in ("h1", "h2"):
            self.transmit(pid, key)
        self.assertTrue(limited()["witchhat"]["open"])   # 10 candy
        self.assertEqual(self.post("/planet/look", {"id": pid, "topper": "witchhat"})["look"]["topper"], "witchhat")
        self.admin("planet_halloween", on=False)
        kept = limited()
        self.assertIn("witchhat", kept)
        self.assertTrue(all(i["open"] for i in kept.values()))
        self.assertNotIn("vampire", kept)
        badges = {b["key"] for b in self.get(f"/planet/state?id={pid}")["badges"]}
        self.assertIn("h_knock", badges)
        self.assertNotIn("h_king", badges)

    def test_the_mansion_gets_new_houses_every_run_and_the_replay_shows_them(self):
        pid = self.join()
        self.get(f"/planet/state?id={pid}")
        self.admin("planet_invite", pid=pid, on=True)
        entry = server.planet_entry(server.players[pid])
        entry["skipped"] = planet.HALLOWEEN_ORDER[:-1]
        maps = set()
        for _ in range(6):
            out = self.transmit(pid, "h10")
            self.assertTrue(out["runs"][0]["reached"])
            maps.add(tuple(out["runs"][0]["map"]))
        self.assertGreater(len(maps), 1)
        self.assertIn("🏚", [b["icon"] for b in self.get(f"/planet/state?id={pid}")["badges"] if b["earned"]])
        self.assertEqual(server.planet_runs[-1]["map"], list(out["runs"][0]["map"]))

    def test_scouting_can_knock(self):
        pid = self.join()
        self.get(f"/planet/state?id={pid}")
        self.admin("planet_invite", pid=pid, on=True)
        out = self.post("/planet/scout", {"id": pid, "site": "h1",
                                          "moves": ["east", "east", "east", "east", "knock:north"]})
        self.assertTrue(out["run"]["reached"])
        self.assertIn("error", self.post("/planet/scout", {"id": pid, "site": "h1", "moves": ["knock:up"]}))


if __name__ == "__main__":
    unittest.main()
