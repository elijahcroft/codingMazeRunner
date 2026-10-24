import json
import os
import re
import tempfile
import threading
import unittest
from unittest import mock
from collections import deque
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
    return next((zi, zone, s) for zi, zone, s in sites() if s["key"] == key)


def run(key, code, variant=0):
    zi, zone, s = site(key)
    return planet.drive(code, s["variants"][variant], zone["rules"], zi)


def solve(key, variant):
    """The shortest list of compass commands that completes the mission,
    found by driving every sequence breadth first (fine for these small
    sites, which don't crumble)."""
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
                return actions + [command]
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
        for key, typed in (("2a", "east()\nreport(6)\n"),
                           ("3a", "south(5)\nreport(5)\n"),
                           ("5a", "report(2)\n"),
                           ("7a", "report(12)\n")):
            self.assertEqual(self.earn(key, typed, 0)[:2], [True, False], key)
            self.assertEqual(self.earn(key, site(key)[2]["reference"], 0)[:2],
                             [True, True], key)

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
            route = as_code(solve("1c", i))
            self.assertTrue(run("1c", route, i)["reached"])
            for j in range(len(variants)):
                if j != i:
                    self.assertFalse(run("1c", route, j)["reached"], (i, j))

    # ---- Zone 2 ----
    def test_2a_one_east_slides_and_the_log_doesnt_say_how_far(self):
        out = run("2a", "east()\n")
        self.assertEqual(out["frames"][-1]["c"] - out["frames"][0]["c"], 6)
        self.assertTrue(any("⛸" in line for line in out["log"]))
        self.assertFalse(any("6" in line.split(":", 1)[1] for line in out["log"]))

    def test_2a_a_wrong_report_ends_the_run(self):
        out = run("2a", "east()\nreport(5)\nreport(6)\n")
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
        out = run("3a", "south(12)\n")
        pushes = [line for line in out["log"] if "💨" in line]
        self.assertEqual(pushes, ["tick 5: 💨 gust pushed the rover east",
                                  "tick 10: 💨 gust pushed the rover east"])
        self.assertTrue(run("3a", "south(12)\nreport(5)\n")["reached"])

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
        self.assertEqual(out["prints"][0]["text"], "1 2 13 2")

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
            self.assertEqual(len(zone["sites"]), 4, key)
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
            self.assertEqual(len(zone["sites"]), 4, key)
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
        self.assertEqual([k[:-1] for k in planet.GIFT_SQUARES],
                         [str(n) for n in range(1, len(planet.ZONES))])
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
                 "dance": lambda k: k == "spin" or f'kind === "{k}"' in page}
        for item in server.GARAGE:
            self.assertTrue(drawn[item["slot"]](item["key"]), item["key"])


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

    def test_the_place_it_names_is_where_the_rover_ended(self):
        out = run("7b", "east(3)\nsouth()\n")
        last = out["frames"][-1]
        self.assertIn(f"x {last['c']}, y {last['r']}", out["explain"]["what"])

    def test_friendly_errors(self):
        self.assertIn("Strange Planet", run("1a", "x = [1, 2]\n")["error"])
        self.assertIn("import", run("1a", "import os\n")["error"])
        self.assertIn("Syntax error", run("1a", "east(\n")["error"])
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
            for secret in ("wind", "sun", "pairs", "oneway", "start", "every", "answer"):
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
        for _ in range(3):
            self.post("/planet/run", {"id": pid, "site": "1a", "code": "east()"})
        row = self.get("/planet/overview")["students"][0]
        self.assertEqual((row["name"], row["site"], row["runs_here"], row["hints"]),
                         ("Ada", "1a", 3, 3))
        # What the last run's banner said, so the teacher knows before walking over.
        self.assertIn("3 samples still out", row["now"]["said"])
        self.post("/planet/run", {"id": pid, "site": "1a", "code": "east(\n"})
        row = self.get("/planet/overview")["students"][0]
        self.assertIn("Syntax error", row["now"]["said"])

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

    def test_clearing_a_zone_says_whats_next(self):
        pid = self.join()
        for key in ("1a", "1b"):
            out = self.post("/planet/run", {"id": pid, "site": key, "code": site(key)[2]["reference"]})
            self.assertIsNone(out["rewards"]["zone_cleared"])
        i = planet.variant_index(pid, site("1c")[2])
        out = self.post("/planet/run", {"id": pid, "site": "1c", "code": answer_program("1c", i)})
        cleared = out["rewards"]["zone_cleared"]
        self.assertEqual((cleared["name"], cleared["next"]["name"]), ("Landing Site", "Ice Field"))
        again = self.post("/planet/run", {"id": pid, "site": "1c", "code": answer_program("1c", i)})
        self.assertIsNone(again["rewards"]["zone_cleared"])

    def test_teacher_can_unlock_the_next_site(self):
        pid = self.join()
        bad = self.post("/admin", {"key": "nope", "action": "planet_unlock", "pid": pid})
        self.assertIn("error", bad)
        ok = self.post("/admin", {"key": server.ADMIN_KEY, "action": "planet_unlock",
                                  "pid": pid})
        self.assertIn("1B", ok["ok"])
        self.assertEqual(self.get(f"/planet/state?id={pid}")["current"], "1b")

    def transmit(self, pid, key, code):
        return self.post("/planet/run", {"id": pid, "site": key, "code": code})

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
        self.assertEqual(names, {"Loop Pilot", "Architect"})
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
                         ["rewards"]["unlocked"], [])   # 2 stars: not yet
        out = self.transmit(pid, "1a", BONUS_PROGRAMS["1a"])   # the third star
        self.assertEqual(out["rewards"]["unlocked"], [{"slot": "paint", "key": "coral", "name": "Coral"}])
        self.assertEqual(self.post("/planet/look", {"id": pid, "paint": "coral"})["look"]["paint"],
                         "coral")

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
                         [{"slot": "paint", "key": "grass", "name": "Grass Block"}])
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
        self.assertEqual(set(now), {"site", "site_name", "zone", "map", "pos", "end", "code", "said"})

    def test_progress_survives_a_restart(self):
        pid = self.join()
        self.post("/planet/run", {"id": pid, "site": "1a",
                                  "code": site("1a")[2]["reference"]})
        server.players.clear()
        server.load_state()
        self.assertEqual(self.get(f"/planet/state?id={pid}")["current"], "1b")


if __name__ == "__main__":
    unittest.main()
