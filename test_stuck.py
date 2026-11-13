"""Nobody stays stuck on Strange Planet. 🙌 Build it together is the last rung
of the help: after many misses in a row the rover builds a level's answer
with the student, so no level can hold anyone for good. And what the rover
says after a miss has to be the real reason, or it sends them the wrong way."""
import json
import os
import tempfile
import threading
import time
import unittest
from urllib.request import Request, urlopen

import planet
import server


def every_site():
    """(zone index, zone, site) for every level with a map of its own."""
    zones = planet.PRACTICE_ZONES + planet.ZONES + planet.BUILD_ZONES \
        + planet.VOYAGE_ZONES + planet.HALLOWEEN_ZONES
    for zone in zones:
        for s in zone["sites"]:
            if "variants" in s:
                yield planet.find_site(s["key"])[0], zone, s


class AnswerTests(unittest.TestCase):
    def test_every_level_has_an_answer_that_wins_on_every_planet(self):
        count = 0
        for zi, zone, s in every_site():
            for vi, v in enumerate(s["variants"]):
                built = planet.together(s["key"], vi)
                self.assertIsNotNone(built, (s["key"], vi))
                out = planet.drive(built["code"], v, zone["rules"], zi)
                self.assertTrue(out["reached"], (s["key"], vi, out["end"], out["error"]))
                count += 1
        self.assertGreater(count, 400)

    def test_every_line_of_every_answer_says_what_it_does(self):
        for zi, zone, s in every_site():
            for vi in range(len(s["variants"])):
                built = planet.together(s["key"], vi)
                lines = built["code"].split("\n")
                self.assertEqual(len(built["notes"]), len(lines), s["key"])
                for line, note in zip(lines, built["notes"]):
                    self.assertEqual(bool(note), bool(line.strip()), (s["key"], line))
                    self.assertNotIn("  ", note, (s["key"], line))   # (two spaces would turn into a code chip)

    def test_the_typed_characters_line_up_with_the_answer(self):
        for zi, zone, s in every_site():
            built = planet.together(s["key"], 0)
            code, mask = built["code"], built["mask"]
            self.assertEqual(len(code), len(mask), s["key"])
            typed = 0
            for a, b in zip(code, mask):
                if a != b:
                    self.assertEqual(b, "_", s["key"])
                    self.assertFalse(a.isspace() or a == "_", (s["key"], a))
                    typed += 1
            # Something to type on every level, and never a wall of it.
            self.assertGreater(typed, 0, s["key"])
            longest = max(sum(not ch.isspace() for ch in line) for line in code.split("\n"))
            self.assertLessEqual(typed, planet.TOGETHER_KEYS + longest, s["key"])

    def test_a_short_answer_is_typed_whole_and_a_long_one_starts_with_its_ideas(self):
        short = planet.together("1b", 0)
        self.assertEqual(short["mask"], "___ _ __ _________\n    ______\n    _______\n")
        long_ = planet.together("7c", 0)
        code, mask = long_["code"].split("\n"), long_["mask"].split("\n")
        self.assertEqual(mask[0], "___ __________")            # def safe(way):
        self.assertIn("        east()", mask)                  # a plain drive is given
        self.assertIn("    _____", mask)                       # else:
        self.assertTrue(any(a == b and a.strip() for a, b in zip(code, mask)))

    def test_a_real_underscore_in_a_name_is_never_a_gap(self):
        built = planet.together("7a", 0)   # report(beacon_x() - x())
        self.assertIn("beacon_x", built["code"])
        at = built["code"].index("beacon_x") + len("beacon")
        self.assertEqual(built["mask"][at], "_")
        self.assertEqual(built["code"][at], "_")

    def test_notes_are_plain_sentences(self):
        notes = planet.line_notes(
            'for i in range(4):\n    east(3)\n    jump("north")\n'
            'while not at_beacon():\n    if look("east") == "rock":\n        south()\n'
            '    else:\n        east()\n'
            'def hop():\n    wait()\nhop()\nn = 2\nn = n + 1\nreport(x() - 1)\n')
        self.assertEqual(notes[:8], [
            "A loop: do the pushed-in lines under it 4 times.",
            "Drive east 3 squares.",
            "Jump 2 squares to the north, over whatever is in between.",
            "A loop: keep doing the pushed-in lines until the rover is on the beacon.",
            "A check: only if the square to the east is rock, do the pushed-in lines under it.",
            "Drive south 1 square.",
            "If none of the checks above were true, do these pushed-in lines.",
            "Drive east 1 square."])
        self.assertIn("new word, hop", notes[8])
        self.assertEqual(notes[9], "Wait 1 tick, without moving.")
        self.assertIn("Use your new word hop", notes[10])
        self.assertEqual(notes[11:14], ["Remember 2, and call it n.", "Make n bigger by 1.",
                                        "Report a number: the rover's x minus 1."])
        # Code that can't be read gets no notes, not a crash.
        self.assertEqual(planet.line_notes("for i in"), [""])

    def test_the_levels_with_no_reference_get_a_worked_out_answer(self):
        for key in ("p59", "2c", "3c", "6c"):
            zi, zone, s = planet.find_site(key)
            self.assertFalse(s["reference"], key)
            for vi, v in enumerate(s["variants"]):
                code = planet.answer_for(key, vi)
                self.assertTrue(planet.drive(code, v, zone["rules"], zi)["reached"], (key, vi))
        self.assertIsNone(planet.answer_for("7", 0))       # the finale is theirs to crack
        self.assertIsNone(planet.answer_for("nope", 0))


class RealReasonTests(unittest.TestCase):
    """A student sent this to Uncharted 79 times. Each time the rover said to
    charge up first, when it was really stuck against a rock."""

    STUCK = ("east()\nwait(50)\nwhile not at_beacon():\n    if x() < beacon_x():\n        east()\n"
             "    elif y() < beacon_y():\n        south()\n    else:\n        west()\n")

    def uncharted(self, code, i=0):
        return planet.drive(code, planet.UNCHARTED_PLANETS[i], planet.UNCHARTED_RULES, planet.UNCHARTED_ZONE)

    def test_a_battery_that_ran_flat_against_a_rock_says_so(self):
        out = self.uncharted(self.STUCK)
        self.assertEqual(out["end"], "battery")
        self.assertIn("stuck there for", out["explain"]["what"])
        self.assertIn("bumping into rock", out["explain"]["what"])
        self.assertIn('look("east")', out["explain"]["next"])
        self.assertNotIn("Charge up", out["explain"]["next"])

    def test_a_battery_that_ran_flat_going_to_and_fro_says_so(self):
        out = self.uncharted(self.STUCK, 3)
        self.assertEqual(out["end"], "battery")
        self.assertIn("back and forth", out["explain"]["what"])

    def test_a_battery_that_ran_flat_driving_still_says_to_charge(self):
        zi, zone, s = planet.find_site("5b")
        out = planet.drive("while True:\n    east()\n    west()\n", s["variants"][0], zone["rules"], zi)
        self.assertEqual(out["end"], "battery")
        self.assertIn("sun", out["explain"]["next"])
        self.assertNotIn("stuck", out["explain"]["what"])


class TogetherClassroomTests(unittest.TestCase):
    """Over HTTP, on a real server with its own save file."""

    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.saved = dict(server.players), server.STATE_FILE, dict(server.planet_class_settings)
        server.players.clear()
        server.planet_runs.clear()
        server.planet_class_settings.update(easy=False, together=True)
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
        server.planet_class_settings.clear()
        server.planet_class_settings.update(self.saved[2])
        server.planet_runs.clear()
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

    def run_code(self, pid, key, code):
        return self.post("/planet/run", {"id": pid, "site": key, "code": code})

    def miss(self, pid, key, times, code="north()\n"):
        for i in range(times):
            out = self.run_code(pid, key, code + "wait()\n" * i)
        return out["rewards"]

    def waited(self, pid, key):
        """As if the first miss was a while ago."""
        server.players[pid]["planet"]["stuck"][key] = time.time() - server.TOGETHER_WAIT - 1

    def test_it_is_offered_after_many_misses_and_a_while(self):
        pid = self.join()
        rewards = self.miss(pid, "1a", server.TOGETHER_AFTER - 1)
        self.assertFalse(rewards["can_together"])
        self.waited(pid, "1a")
        self.assertFalse(self.get(f"/planet/site?id={pid}&site=1a")["can_together"])
        self.assertIn("error", self.post("/planet/together", {"id": pid, "site": "1a"}))
        rewards = self.miss(pid, "1a", 1)
        self.assertTrue(rewards["can_together"])
        self.assertTrue(self.get(f"/planet/site?id={pid}&site=1a")["can_together"])

    def test_mashing_transmit_is_not_a_way_to_get_it(self):
        pid = self.join()
        rewards = self.miss(pid, "1a", server.TOGETHER_AFTER + 3)
        self.assertFalse(rewards["can_together"])    # ten misses in ten seconds
        for i in range(3):
            out = self.post("/planet/again", {"id": pid, "site": "1a"})
        self.assertFalse(out["can_together"])
        self.waited(pid, "1a")
        self.assertTrue(self.post("/planet/again", {"id": pid, "site": "1a"})["can_together"])

    def test_easy_mode_offers_it_sooner(self):
        server.planet_class_settings["easy"] = True
        pid = self.join()
        rewards = self.miss(pid, "p1", server.EASY_TOGETHER_AFTER)
        self.waited(pid, "p1")
        self.assertTrue(self.get(f"/planet/site?id={pid}&site=p1")["can_together"])
        self.assertLess(server.EASY_TOGETHER_AFTER, server.EASY_SKIP_AFTER)
        self.assertLess(server.TOGETHER_AFTER, server.SKIP_AFTER)

    def build(self, pid, key):
        if key in planet.SITE_ORDER:   # (as if they'd got this far)
            entry = server.planet_entry(server.players[pid])
            entry["unlocked"] = max(entry["unlocked"], planet.SITE_ORDER.index(key))
        self.miss(pid, key, server.TOGETHER_AFTER)
        self.waited(pid, key)
        return self.post("/planet/together", {"id": pid, "site": key})

    def test_building_it_wins_the_level_with_one_star(self):
        pid = self.join()
        built = self.build(pid, "1b")
        self.assertEqual(built["code"], planet.find_site("1b")[2]["reference"].strip("\n") + "\n")
        self.assertEqual(len(built["mask"]), len(built["code"]))
        self.assertEqual(server.players[pid]["planet"]["together"], ["1b"])
        out = self.run_code(pid, "1b", built["code"])
        rewards = out["rewards"]
        self.assertTrue(out["runs"][0]["reached"])
        self.assertTrue(rewards["together"])
        self.assertEqual(rewards["stars"], [True, False, False])
        self.assertIsNone(rewards["record"])
        entry = server.players[pid]["planet"]
        self.assertIn("1b", entry["solved"])
        self.assertNotIn("1b", entry["routes"])
        # The coding badges wait for their own code.
        self.assertNotIn("loop", entry["badges"])
        self.assertIn("first", entry["badges"])
        # The next level is open, and the offer is over here.
        self.assertEqual(self.get(f"/planet/state?id={pid}")["current"], "1b1")
        self.assertEqual(server.planet_frontier(server.players[pid]), planet.SITE_ORDER.index("1b1"))
        self.assertFalse(self.get(f"/planet/site?id={pid}&site=1b")["can_together"])
        # Sending the same program again earns nothing more.
        again = self.run_code(pid, "1b", built["code"] + "\n\n")["rewards"]
        self.assertEqual(again["best"], [True, False, False])
        self.assertEqual(self.get(f"/planet/site?id={pid}&site=1b")["stars"], [True, False, False])

    def test_their_own_way_afterwards_earns_the_rest(self):
        ada, bo = self.join("Ada"), self.join("Bo")
        built = self.build(ada, "1b")
        self.run_code(ada, "1b", built["code"])
        # Not a time for the class to beat.
        self.assertIsNone(server.class_record("1b"))
        server.planet_entry(server.players[bo])["unlocked"] = planet.SITE_ORDER.index("1b")
        self.assertIsNone(self.get(f"/planet/site?id={bo}&site=1b")["record"])
        own = "def step():\n    east()\n    south()\n\nfor i in range(8):\n    step()\n"
        rewards = self.run_code(ada, "1b", own)["rewards"]
        self.assertFalse(rewards["together"])
        self.assertTrue(rewards["own_way"])       # said once, on the win that does it
        self.assertEqual(rewards["stars"], [True, True, False])   # (a def: too long for ✂️)
        self.assertFalse(self.run_code(ada, "1b", own)["rewards"]["own_way"])
        self.assertEqual(server.players[ada]["planet"]["together"], [])
        self.assertEqual(server.class_record("1b")["name"], "Ada")
        self.assertIn("loop", server.players[ada]["planet"]["badges"])

    def test_the_teacher_sees_it_and_can_turn_it_off(self):
        pid = self.join()
        self.build(pid, "1a")
        row = self.get("/planet/overview")["students"][0]
        self.assertEqual(row["together"], ["1a"])
        self.assertTrue(self.get("/planet/overview")["together"])
        self.assertIn("error", self.post("/admin", {"key": "nope", "action": "planet_together", "on": False}))
        ok = self.post("/admin", {"key": server.ADMIN_KEY, "action": "planet_together", "on": False})
        self.assertIn("off", ok["ok"])
        self.assertFalse(self.get("/planet/overview")["together"])
        self.assertFalse(self.get(f"/planet/site?id={pid}&site=1a")["can_together"])
        self.assertIn("error", self.post("/planet/together", {"id": pid, "site": "1a"}))
        ok = self.post("/admin", {"key": server.ADMIN_KEY, "action": "planet_together", "on": True})
        self.assertIn(str(server.TOGETHER_AFTER), ok["ok"])
        # A build already begun stays open.
        self.assertTrue(self.get(f"/planet/site?id={pid}&site=1a")["can_together"])

    def test_the_after_class_report_names_who_built_a_level(self):
        ada, bo = self.join("Ada"), self.join("Bo")
        built = self.build(ada, "1a")
        self.run_code(bo, "1a", "north()\n")
        row = next(r for r in self.get("/planet/report")["sites"] if r["key"] == "1a")
        self.assertEqual(row["built"], ["Ada"])
        # It stays in the report after she does the level her own way.
        self.run_code(ada, "1a", built["code"])
        self.run_code(ada, "1a", "south(2)\neast()\nsouth()\neast(7)\nsouth()\nnorth(3)\nwest()\nwait()\n")
        self.assertEqual(server.players[ada]["planet"]["together"], [])
        row = next(r for r in self.get("/planet/report")["sites"] if r["key"] == "1a")
        self.assertEqual(row["built"], ["Ada"])

    def test_a_younger_class_sees_its_practice_levels_in_the_report(self):
        pid = self.join()
        self.assertEqual(self.get("/planet/report")["zones"][0]["name"], "Landing Site")
        server.planet_class_settings["easy"] = True
        self.run_code(pid, "p1", "north()\n")
        report = self.get("/planet/report")
        self.assertEqual(report["zones"][0]["name"], "Practice Park")
        self.assertEqual([r["key"] for r in report["sites"]], ["p1"])

    def test_never_on_the_finale_or_a_level_already_done(self):
        pid = self.join()
        entry = server.planet_entry(server.players[pid])
        entry["unlocked"] = len(planet.SITE_ORDER) - 1
        entry["misses"]["7"] = 50
        entry.setdefault("stuck", {})["7"] = 0
        self.assertFalse(server.can_together(server.players[pid], "7"))
        self.run_code(pid, "1a", planet.find_site("1a")[2]["reference"])
        entry["misses"]["1a"] = 50
        entry["stuck"]["1a"] = 0
        self.assertFalse(server.can_together(server.players[pid], "1a"))

    def test_a_per_student_level_builds_that_students_own_answer(self):
        s = planet.find_site("2c")[2]
        for name in ("Ada", "Bo", "Cy", "Di"):
            pid = self.join(name)
            built = self.build(pid, "2c")
            self.assertNotIn("error", built)
            out = self.run_code(pid, "2c", built["code"])
            self.assertTrue(out["runs"][0]["reached"], name)
            self.assertEqual(out["rewards"]["stars"], [True, False, False])


class PageTests(unittest.TestCase):
    """The page has the pieces the build needs (the browser play-test drives them)."""

    def test_the_student_page_offers_and_runs_the_build(self):
        here = os.path.dirname(os.path.abspath(__file__))
        with open(os.path.join(here, "planet.html")) as f:
            page = f.read()
        for piece in ("function buildTogether()", "function endTogether(", "/planet/together",
                      "site.can_together", "function idleHelp()", "Build it together"):
            self.assertIn(piece, page)
        with open(os.path.join(here, "planet_teacher.html")) as f:
            teacher = f.read()
        self.assertIn("planet_together", teacher)
        self.assertIn("built with the rover", teacher)


if __name__ == "__main__":
    unittest.main()
