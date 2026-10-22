import json
import os
import tempfile
import threading
import unittest
from collections import deque
from urllib.request import Request, urlopen

import planet
import server


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


# Programs that earn a bonus star the reference program doesn't.
BONUS_PROGRAMS = {
    "1a": "turn_right()\nmove()\nturn_right()\nturn_right()\nmove()\nturn_right()\n"
          "move(3)\nturn_right()\nmove(2)\nturn_left()\nmove(5)\n",
    "1b": "def step():\n    move()\n    turn_right()\n    move()\n    turn_left()\n\n"
          "for i in range(7):\n    step()\nmove()\n",
    "2a": "move()\nmove()\nturn_right()\nmove(3)\nturn_right()\nmove(4)\n"
          "turn_right()\nmove()\n",
    "2b": "turn_left()\nmove()\nturn_right()\nmove()\nturn_right()\nmove()\n"
          "turn_left()\nmove()\nturn_left()\nmove()\nturn_right()\nturn_right()\n"
          "move()\nturn_right()\nmove()\n",
    "5a": "move(2)\nfor i in range(30):\n    wait()\nmove(27)\n",
    "6a": "move()\nturn_right()\nmove(3)\nturn_right()\nmove()\nturn_right()\n"
          "turn_right()\nmove(2)\nturn_left()\nmove()\nturn_right()\nmove(2)\n"
          "turn_left()\nmove(2)\n",
}


def as_code(route):
    """A solver route as code, runs of move() joined into move(n)."""
    lines = []
    for a in route:
        if a == "move()" and lines and lines[-1].startswith("move("):
            n = int(lines[-1][5:-1] or 1)
            lines[-1] = f"move({n + 1})"
        else:
            lines.append(a)
    return "\n".join(lines) + "\n"


class StarTests(unittest.TestCase):
    def earn(self, key, code, i):
        zi, zone, s = site(key)
        v = s["variants"][i]
        return planet.stars(s, v, planet.drive(code, v, zone["rules"], zi), code)

    def test_every_star_on_every_planet_can_be_earned(self):
        for zi, zone, s in sites():
            for i, v in enumerate(s["variants"]):
                if s["reference"]:
                    programs = [s["reference"]]
                elif s["key"] == "3c":
                    programs = [wind_program(v["wind"])]
                else:
                    programs = [as_code(solve(s["key"], i))]
                if s["key"] in BONUS_PROGRAMS:
                    programs.append(BONUS_PROGRAMS[s["key"]])
                earned = [any(star) for star in zip(*(self.earn(s["key"], p, i)
                                                      for p in programs))]
                self.assertEqual(earned, [True, True, True], (s["key"], i))

    def test_the_bonus_takes_something_extra(self):
        # The plain answer misses these bonuses: they need a detour, a def,
        # or banking battery.
        for key in BONUS_PROGRAMS:
            self.assertFalse(self.earn(key, site(key)[2]["reference"], 0)[1], key)

    def test_no_stars_without_the_beacon(self):
        self.assertEqual(self.earn("1a", "move()\n", 0), [False, False, False])

    def test_compact_counts_lines_that_do_something(self):
        self.assertEqual(planet.code_lines("# plan\nmove(3)\n\n   \nturn_left()  # go\n"), 2)

    def test_every_site_shows_three_goals(self):
        for _, _, s in sites():
            for v in s["variants"]:
                self.assertEqual(len(planet.goals(s, v)), 3)


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

    def test_sites_open_one_at_a_time(self):
        pid = self.join()
        state = self.get(f"/planet/state?id={pid}")
        self.assertEqual(state["current"], "1a")
        self.assertIn("error", self.get(f"/planet/site?id={pid}&site=1b"))
        self.assertIn("error", self.post("/planet/run", {"id": pid, "site": "1b",
                                                         "code": "move()"}))
        out = self.post("/planet/run", {"id": pid, "site": "1a",
                                        "code": site("1a")[2]["reference"]})
        self.assertTrue(out["runs"][0]["reached"])
        self.assertEqual(out["state"]["current"], "1b")
        view = self.get(f"/planet/site?id={pid}&site=1b")
        self.assertEqual(view["name"], "Ridge Steps")

    def test_a_site_never_shows_its_hidden_rule(self):
        pid = self.join()
        server.planet_entry(server.players[pid])["unlocked"] = len(planet.SITE_ORDER)
        for key in ("3c", "5c", "6c"):
            view = self.get(f"/planet/site?id={pid}&site={key}")
            text = json.dumps(view)
            for secret in ("wind", "sun", "pairs", "oneway", "start", "every"):
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
        slow = "move(3)\nturn_left()\nturn_right()\nturn_right()\nmove(2)\n" \
               "turn_left()\nmove(5)\n"
        self.post("/planet/run", {"id": pid, "site": "1a", "code": slow})
        self.post("/planet/run", {"id": pid, "site": "1a",
                                  "code": site("1a")[2]["reference"]})
        self.post("/planet/run", {"id": pid, "site": "1a", "code": slow})
        view = self.get(f"/planet/site?id={pid}&site=1a")
        self.assertEqual(view["solved"], 12)
        self.assertEqual(view["code"], slow)

    def test_uncharted_runs_five_planets_and_keeps_the_best(self):
        pid = self.join()
        server.planet_entry(server.players[pid])["unlocked"] = len(planet.SITE_ORDER)
        out = self.post("/planet/run", {"id": pid, "site": "7",
                                        "code": planet.UNCHARTED_REFERENCE})
        self.assertEqual(len(out["runs"]), planet.PLANETS_PER_RUN)
        self.assertTrue(all(r["reached"] for r in out["runs"]))
        self.assertTrue(all("map" in r for r in out["runs"]))
        self.post("/planet/run", {"id": pid, "site": "7", "code": "move()"})
        self.assertEqual(self.get(f"/planet/state?id={pid}")["uncharted"]["reached"], 5)

    def test_hints_journal_and_the_teacher_overview(self):
        pid = self.join()
        for _ in range(5):
            state = self.post("/planet/hint", {"id": pid, "zone": "ice"})
        ice = next(z for z in state["zones"] if z["key"] == "ice")
        self.assertEqual(len(ice["hints"]), 3)
        self.post("/planet/journal", {"id": pid, "zone": "ice",
                                      "text": "one move slides " + "x" * 300})
        for _ in range(3):
            self.post("/planet/run", {"id": pid, "site": "1a", "code": "move()"})
        row = self.get("/planet/overview")["students"][0]
        self.assertEqual((row["name"], row["site"], row["runs_here"], row["hints"]),
                         ("Ada", "1a", 3, 3))
        self.assertEqual(len(row["journal"]["Ice Field"]), server.JOURNAL_MAX)

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
        self.transmit(pid, "1a", "move(\n")
        out = self.transmit(pid, "1a", site("1a")[2]["reference"])
        self.assertIn("Bug Squasher", [b["name"] for b in out["rewards"]["badges"]])
        server.planet_entry(server.players[pid])["unlocked"] = 1
        for _ in range(5):
            self.transmit(pid, "1b", "move()\n")
        out = self.transmit(pid, "1b", site("1b")[2]["reference"])
        self.assertIn("Never Give Up", [b["name"] for b in out["rewards"]["badges"]])

    def test_the_first_sighting_of_a_hidden_rule_is_an_anomaly(self):
        pid = self.join()
        server.planet_entry(server.players[pid])["unlocked"] = 3
        out = self.transmit(pid, "2a", "move(4)\n")
        self.assertEqual(out["rewards"]["anomaly"], {"zone": "Ice Field", "tick": 1})
        self.assertIsNone(self.transmit(pid, "2a", "move(4)\n")["rewards"]["anomaly"])

    def test_class_records_and_the_feed(self):
        ada, bo = self.join("Ada"), self.join("Bo")
        slow = "move(3)\nturn_left()\nturn_right()\nturn_right()\nmove(2)\nturn_left()\nmove(5)\n"
        first = self.transmit(ada, "1a", slow)["rewards"]["record"]
        self.assertEqual((first["name"], first["first"]), ("Ada", True))
        beat = self.transmit(bo, "1a", site("1a")[2]["reference"])["rewards"]
        self.assertEqual((beat["record"]["ticks"], beat["record"]["first"]), (12, False))
        self.assertIn("Record Breaker", [b["name"] for b in beat["badges"]])
        self.assertEqual(self.get(f"/planet/site?id={ada}&site=1a")["record"],
                         {"ticks": 12, "name": "Bo"})
        overview = self.get("/planet/overview")
        self.assertTrue(any("class record" in m["text"] for m in overview["feed"]))
        self.assertEqual(overview["class"]["stars"], 3)   # Ada's slow run isn't compact
        self.assertTrue(overview["address"].endswith("/planet"))

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

    def test_scouting_drives_by_hand_but_saves_nothing(self):
        pid = self.join()
        out = self.post("/planet/scout", {"id": pid, "site": "1a",
                                          "moves": ["move", "move", "move", "turn_right"]})
        self.assertEqual(out["run"]["frames"][-1]["c"], 4)
        self.assertEqual(out["left"], server.SCOUT_MAX - 4)
        self.assertIn("error", self.post("/planet/scout", {"id": pid, "site": "1a",
                                                           "moves": ["import os"]}))
        self.assertIn("error", self.post("/planet/scout", {"id": pid, "site": "1b",
                                                           "moves": ["move"]}))
        state = self.get(f"/planet/state?id={pid}")
        self.assertEqual((state["total_stars"], state["current"]), (0, "1a"))

    def test_progress_survives_a_restart(self):
        pid = self.join()
        self.post("/planet/run", {"id": pid, "site": "1a",
                                  "code": site("1a")[2]["reference"]})
        server.players.clear()
        server.load_state()
        self.assertEqual(self.get(f"/planet/state?id={pid}")["current"], "1b")


if __name__ == "__main__":
    unittest.main()
