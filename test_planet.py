import unittest
from collections import deque

import planet


def sites():
    for zi, zone in enumerate(planet.ZONES):
        for s in zone["sites"]:
            yield zi, zone, s


def site(key):
    return next((zi, zone, s) for zi, zone, s in sites() if s["key"] == key)


def run(key, code, variant=0):
    zi, zone, s = site(key)
    return planet.drive(code, s["variants"][variant], zone["rules"], zi)


def solve(key, variant):
    """The shortest list of commands that reaches the beacon, found by
    driving every sequence breadth first (fine for these small sites)."""
    zi, zone, s = site(key)
    v = s["variants"][variant]
    commands = ("move()", "turn_left()", "turn_right()")
    queue, seen = deque([[]]), set()
    while queue:
        actions = queue.popleft()
        for command in commands:
            out = planet.drive("\n".join(actions + [command]), v, zone["rules"], zi)
            if out["reached"]:
                return actions + [command]
            last = out["frames"][-1]
            state = (last["r"], last["c"], last["d"], out["ticks"] % 60
                     if "wind" in zone["rules"] else 0)
            if out["end"] == "stopped" and state not in seen:
                seen.add(state)
                queue.append(actions + [command])
    return None


def replay_as_code(out):
    """The commands a run did, one per line (for sites without ice, wind or
    portals, where every frame is one command)."""
    lines = []
    for a, b in zip(out["frames"], out["frames"][1:]):
        if b.get("e") == "wait":
            lines.append("wait()")
        elif b["d"] != a["d"]:
            lines.append("turn_right()" if b["d"] == (a["d"] + 1) % 4 else "turn_left()")
        elif b.get("e") != "goal":
            lines.append("move()")
    return "\n".join(lines) + "\n"


def wind_program(gust):
    return (f"GUST = {gust}\n\ndef step():\n    if tick() % GUST == GUST - 1:\n"
            f"        wait()\n    move()\n\ndef go(n):\n    for i in range(n):\n"
            f"        step()\n\ngo(5)\nturn_left()\ngo(7)\nturn_right()\ngo(4)\n"
            f"turn_left()\ngo(3)\nturn_right()\ngo(7)\n")


class SiteClaims(unittest.TestCase):
    def test_maps_are_rectangles_with_one_start_and_beacon(self):
        for _, _, s in sites():
            for v in s["variants"]:
                width = len(v["map"][0])
                self.assertTrue(all(len(row) == width for row in v["map"]), s["key"])
                text = "".join(v["map"])
                self.assertEqual(text.count("S"), 1, s["key"])
                self.assertEqual(text.count("G"), 1, s["key"])

    def test_every_reference_clears_every_variant(self):
        for zi, zone, s in sites():
            if not s["reference"]:
                continue
            for i in range(len(s["variants"])):
                out = run(s["key"], s["reference"], i)
                self.assertTrue(out["reached"], (s["key"], i, out["log"][-3:],
                                                 out["error"]))

    def test_every_site_without_a_reference_can_be_solved(self):
        for key in ("2c", "6c"):
            for i in range(len(site(key)[2]["variants"])):
                self.assertIsNotNone(solve(key, i), (key, i))
        for i, v in enumerate(site("3c")[2]["variants"]):
            self.assertTrue(run("3c", wind_program(v["wind"]), i)["reached"], i)

    # ---- Zone 1 ----
    def test_1c_counting_only_works_on_your_own_planet(self):
        route = solve("1c", 0)
        self.assertTrue(run("1c", "\n".join(route), 0)["reached"])
        for i in (1, 2, 3):
            self.assertFalse(run("1c", "\n".join(route), i)["reached"], i)

    # ---- Zone 2 ----
    def test_2a_counting_slides_past_the_turn(self):
        out = run("2a", "move(4)\nturn_right()\nmove(2)\n")
        self.assertFalse(out["reached"])
        self.assertTrue(any("⛸" in line for line in out["log"]))

    def test_2b_the_beacon_is_close_but_needs_six_slides(self):
        route = solve("2b", 0)
        self.assertEqual(sum(a == "move()" for a in route), 6)
        self.assertFalse(run("2b", "turn_right()\nmove(2)\n")["reached"])

    def test_2c_each_lake_needs_its_own_plan(self):
        routes = [solve("2c", i) for i in range(4)]
        for i, route in enumerate(routes):
            self.assertGreaterEqual(sum(a == "move()" for a in route), 7)
            for j in range(4):
                if j != i:
                    self.assertFalse(run("2c", "\n".join(route), j)["reached"], (i, j))

    # ---- Zone 3 ----
    def test_3a_driving_straight_falls_on_the_second_gust(self):
        out = run("3a", "move(12)\n")
        self.assertEqual((out["end"], out["ticks"]), ("fell", 10))
        self.assertEqual(run("3a", "while not at_goal():\n    move()\n")["end"], "fell")

    def test_3b_hand_counted_moves_fall(self):
        out = run("3b", "move(6)\nturn_left()\nmove(5)\nturn_right()\nmove(6)\n"
                        "turn_left()\nmove(4)\nturn_right()\nmove(5)\n")
        self.assertEqual(out["end"], "fell")

    def test_3c_a_neighbours_gust_number_falls(self):
        variants = site("3c")[2]["variants"]
        for i, v in enumerate(variants):
            for j, other in enumerate(variants):
                if v["wind"] != other["wind"]:
                    out = run("3c", wind_program(other["wind"]), i)
                    self.assertEqual(out["end"], "fell", (i, j))
        # 3B's answer, every 5 ticks, works on nobody's ridge.
        three_b = site("3b")[2]["reference"].replace("go(6)\nturn_left()\ngo(5)",
                                                     "go(5)\nturn_left()\ngo(7)")
        for i in range(len(variants)):
            self.assertFalse(run("3c", three_b, i)["reached"], i)

    # ---- Zone 4 ----
    def test_4a_in_and_out_the_same_way_falls(self):
        out = run("4a", "move(4)\nturn_right()\nmove(3)\nturn_right()\n"
                        "turn_right()\nmove(3)\n")
        self.assertEqual(out["end"], "fell")

    def test_4a_the_beacon_wants_the_sample(self):
        out = run("4a", "move(8)\n")
        self.assertFalse(out["reached"])
        self.assertTrue(any("needs every sample" in line for line in out["log"]))

    def test_4c_following_the_edge_comes_back_round_and_falls(self):
        edge = ("while not at_goal():\n    if wall_ahead():\n        turn_right()\n"
                "    else:\n        move()\n")
        for i in range(4):
            self.assertEqual(run("4c", edge, i)["end"], "fell", i)

    # ---- Zone 5 ----
    def test_5a_driving_straight_runs_flat(self):
        self.assertEqual(run("5a", "move(29)\n")["end"], "battery")

    def test_5b_one_long_charge_isnt_enough_but_charging_each_time_is(self):
        self.assertEqual(run("5b", "move(12)\nturn_right()\nmove(5)\nturn_right()\n"
                                   "move(16)\nturn_left()\nmove(5)\nturn_left()\n"
                                   "move(20)\n")["end"], "battery")

    def test_5c_one_charge_stop_is_never_enough(self):
        for i in range(4):
            for steps in range(1, 12):
                code = f"move({steps})\nwhile battery() < 100 and in_sun():\n" \
                       f"    wait()\nmove({40 - steps})\n"
                self.assertFalse(run("5c", code, i)["reached"], (i, steps))

    def test_5c_no_hard_coded_plan_works_on_every_planet(self):
        for i in range(4):
            mine = replay_as_code(run("5c", site("5c")[2]["reference"], i))
            self.assertTrue(run("5c", mine, i)["reached"])
            self.assertFalse(all(run("5c", mine, j)["reached"] for j in range(4)), i)

    # ---- Zone 6 ----
    def test_6a_6b_the_beacon_is_walled_off(self):
        for key in ("6a", "6b"):
            self.assertFalse(run(key, "while not wall_ahead():\n    move()\n"
                                      "turn_right()\nmove(2)\n")["reached"], key)

    def test_6c_every_wiring_needs_two_trips_and_its_own_route(self):
        routes = [solve("6c", i) for i in range(4)]
        for i, route in enumerate(routes):
            out = run("6c", "\n".join(route), i)
            self.assertGreaterEqual(sum("✨" in line for line in out["log"]), 2, i)
            for j in range(4):
                if j != i:
                    self.assertFalse(run("6c", "\n".join(route), j)["reached"], (i, j))


class UnchartedTests(unittest.TestCase):
    def test_reference_clears_every_planet_it_was_checked_on(self):
        for seed in range(20):
            for p in planet.uncharted_planets(seed):
                out = planet.drive(planet.UNCHARTED_REFERENCE, p,
                                   planet.UNCHARTED_RULES, planet.UNCHARTED_ZONE)
                self.assertTrue(out["reached"])

    def test_shortcuts_fail_somewhere(self):
        planets = [p for seed in range(10) for p in planet.uncharted_planets(seed)]

        def score(code):
            return sum(planet.drive(code, p, planet.UNCHARTED_RULES,
                                    planet.UNCHARTED_ZONE)["reached"] for p in planets)
        best = score(planet.UNCHARTED_REFERENCE)
        no_sun = planet.UNCHARTED_REFERENCE.replace("battery() < 60", "False")
        no_craters = planet.UNCHARTED_REFERENCE.replace(" or crater_ahead()", "")
        no_wind = planet.UNCHARTED_REFERENCE.replace("gust_in() == 1", "False")
        self.assertEqual(best, len(planets))
        for name, code in (("sun", no_sun), ("craters", no_craters),
                           ("wind", no_wind)):
            self.assertLess(score(code), best * 0.8, name)


class RoverTests(unittest.TestCase):
    def test_sensors_arrive_zone_by_zone(self):
        out = run("1a", "print(tick())\n")
        self.assertIn("Wind Canyon", out["error"])
        self.assertIsNone(run("3a", "print(tick())\n")["error"])

    def test_friendly_errors(self):
        self.assertIn("Strange Planet", run("1a", "x = [1, 2]\n")["error"])
        self.assertIn("import", run("1a", "import os\n")["error"])
        self.assertIn("Syntax error", run("1a", "move(\n")["error"])
        out = run("1a", "while True:\n    pass\n")
        self.assertIn("ran too long", out["error"])
        self.assertEqual(out["line"], 1)

    def test_an_endless_drive_runs_out_of_time(self):
        out = run("1a", "while True:\n    turn_left()\n")
        self.assertEqual((out["end"], out["ticks"]), ("ticks", planet.MAX_TICKS))

    def test_prints_keep_the_tick(self):
        out = run("3a", "move()\nprint('here', tick())\n")
        self.assertEqual(out["prints"], [{"t": 1, "text": "here 1"}])


if __name__ == "__main__":
    unittest.main()
