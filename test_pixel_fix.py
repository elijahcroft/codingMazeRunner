"""Fix it: after a mission, Pip's code for it with one bug for the student to find and fix."""
import unittest

import pixel
import server
from test_pixel import StudioOverHttp, drawing


def run(key, code):
    return pixel.run_level(pixel.LEVEL_BY_KEY[key], code, pixel.PIP)


class EveryBugIsReal(unittest.TestCase):
    def test_every_mission_but_my_move_has_one(self):
        self.assertEqual(set(pixel.FIXES), set(pixel.LEVEL_ORDER) - {"m1"})

    def test_the_bug_breaks_it_and_the_guides_code_fixes_it(self):
        for key, (ask, code, check, hint) in pixel.FIXES.items():
            with self.subTest(level=key):
                self.assertFalse(run(key, code)["fix"])
                self.assertTrue(run(key, pixel.LEVEL_BY_KEY[key]["reference"])["fix"])

    def test_a_bug_is_one_small_change_from_the_guides_code(self):
        for key, (ask, code, check, hint) in pixel.FIXES.items():
            with self.subTest(level=key):
                bad, good = code.split("\n"), pixel.LEVEL_BY_KEY[key]["reference"].split("\n")
                self.assertEqual(len(bad), len(good))
                self.assertLessEqual(sum(a != b for a, b in zip(bad, good)), 2)

    def test_some_stop_the_show_and_some_run_wrong(self):
        stops = [key for key, fix in pixel.FIXES.items() if run(key, fix[1])["error"]]
        self.assertGreaterEqual(len(stops), 5)
        self.assertGreaterEqual(len(pixel.FIXES) - len(stops), 5)

    def test_the_ones_that_stop_say_where(self):
        for key, fix in pixel.FIXES.items():
            out = run(key, fix[1])
            if out["error"]:
                with self.subTest(level=key):
                    self.assertTrue(out["error"].startswith("Line "), out["error"])

    def test_a_fix_that_runs_but_misses_the_bug_does_not_count(self):
        self.assertFalse(run("b2", "for i in range(4):\n    right(1)\n    confetti()\n    left(1)")["fix"])
        self.assertFalse(run("v2", 'jumps = 7\nfor i in range(5):\n    jump()\ngrow()\nsay(f"{jumps} jumps!")')["fix"])
        self.assertTrue(run("v2", 'jumps = 7\nfor i in range(jumps):\n    jump()\ngrow()\nsay(f"{jumps} jumps!")')["fix"])
        self.assertTrue(run("l2", 'for name in ["Ana", "Ben", "Cy"]:\n    say("Hi " + name)\n    jump()')["fix"])


class FixOverHttp(unittest.TestCase):
    setUp, tearDown, post, get = StudioOverHttp.setUp, StudioOverHttp.tearDown, StudioOverHttp.post, StudioOverHttp.get

    def join(self):
        me = self.post("/join", {"name": "Mia"})["id"]
        self.post("/pixel/save", {"id": me, "drawing": drawing()})
        return me

    def fix(self, me, code, fixing=True):
        return self.post("/pixel/run", {"id": me, "level": "a1", "code": code, "fixing": fixing})

    def test_it_pays_once_with_a_badge_and_shows_on_the_mission(self):
        me = self.join()
        good = pixel.LEVEL_BY_KEY["a1"]["reference"]
        self.post("/pixel/run", {"id": me, "level": "a1", "code": good})
        level = self.get(f"/pixel/level?id={me}&level=a1")
        self.assertEqual(level["fix"]["code"], pixel.FIXES["a1"][1])
        self.assertFalse(level["fix"]["done"])
        self.assertNotIn("fixed", self.fix(me, pixel.FIXES["a1"][1])["rewards"])
        coins = server.pixel_entry(server.players[me])["coins"]
        out = self.fix(me, good)
        self.assertTrue(out["rewards"]["fixed"])
        self.assertEqual(out["rewards"]["coins"], pixel.FIX_COINS)
        self.assertIn("Bug Squasher", [b["name"] for b in out["rewards"]["badges"]])
        self.assertEqual(server.pixel_entry(server.players[me])["coins"], coins + pixel.FIX_COINS)
        again = self.fix(me, good)
        self.assertNotIn("fixed", again["rewards"])
        self.assertTrue(self.get(f"/pixel/level?id={me}&level=a1")["fix"]["done"])
        levels = {l["key"]: l for ch in again["state"]["chapters"] for l in ch["levels"]}
        self.assertTrue(levels["a1"]["fixed"])
        self.assertIs(levels["m1"]["fixed"], None)

    def test_it_needs_the_mission_finished_first_and_the_page_to_say_so(self):
        me = self.join()
        good = pixel.LEVEL_BY_KEY["a1"]["reference"]
        self.assertNotIn("fixed", self.fix(me, good)["rewards"])        # not finished before this run
        self.assertNotIn("fixed", self.fix(me, good, fixing=False)["rewards"])
        self.assertNotIn("fixed", self.fix(me, good, fixing="yes")["rewards"])
        self.assertTrue(self.fix(me, good)["rewards"]["fixed"])

    def test_my_move_has_no_fix(self):
        me = self.join()
        server.pixel_entry(server.players[me])["solved"].update({k: [True] * 3 for k in pixel.LEVEL_ORDER[:8]})
        self.assertIsNone(self.get(f"/pixel/level?id={me}&level=m1")["fix"])


if __name__ == "__main__":
    unittest.main()
