"""Give It Back: the last chapter, where a def hands a value back with return."""
import os
import unittest

import pixel
import server
from test_pixel import StudioOverHttp, drawing


def run(key, code=None):
    lv = pixel.LEVEL_BY_KEY[key]
    return pixel.run_level(lv, lv["reference"] if code is None else code, pixel.PIP)


def report(code):
    return pixel.perform(code)["report"]


class TheChapter(unittest.TestCase):
    def test_it_comes_last_and_has_a_new_icon(self):
        self.assertEqual(pixel.CHAPTERS[-1], {"key": "g", "name": "Give It Back", "icon": "📦"})
        self.assertEqual([ch["icon"] for ch in pixel.CHAPTERS].count("📦"), 1)
        self.assertEqual([lv["key"] for lv in pixel.LEVELS[-3:]], ["g1", "g2", "g3"])
        self.assertEqual({lv["chapter"] for lv in pixel.LEVELS[-3:]}, {len(pixel.CHAPTERS) - 1})

    def test_there_are_now_42_missions_and_126_stars(self):
        self.assertEqual(len(pixel.LEVELS), 42)
        self.assertEqual(pixel.LEVEL_ORDER[-3:], ["g1", "g2", "g3"])

    def test_each_reference_earns_all_three_stars(self):
        for key in ("g1", "g2", "g3"):
            with self.subTest(level=key):
                out = run(key)
                self.assertIsNone(out["error"])
                self.assertEqual(out["stars"], [True, True, True], out["reply"])

    def test_the_three_new_box_gifts_are_wearable(self):
        for key in ("boxhat", "returnhat", "givespark"):
            with self.subTest(gift=key):
                self.assertIn(key, pixel.BOX_GIFTS)
                self.assertIn(pixel.GIFTS[key]["slot"], pixel.WEAR_SLOTS)

    def test_the_new_python_chip_is_there(self):
        page_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "pixel_page.js")
        with open(page_path, encoding="utf-8") as file:
            page = file.read()
        self.assertIn("return: [", page)


class TheReturn(unittest.TestCase):
    def test_a_def_hands_a_number_back_to_say(self):
        r = report(pixel.LEVEL_BY_KEY["g1"]["reference"])
        self.assertEqual(r.said, ["6", "10"])
        self.assertEqual(r.returns, 1)
        self.assertEqual(r.return_values, 1)
        self.assertEqual(r.call_in_call["double"], 2)
        self.assertEqual(r.defs, ["double"])

    def test_a_def_can_be_called_inside_say_and_range(self):
        self.assertEqual(report('def double(n):\n    return n * 2\nsay(double(4))').said, ["8"])
        r = report('def double(n):\n    return n * 2\nfor i in range(double(2)):\n    jump()')
        self.assertEqual(r.n("jump"), 4)

    def test_a_hardcoded_say_does_not_earn_the_return_goal(self):
        out = run("g1", "say(6)\nsay(10)")
        self.assertEqual(out["stars"], [False, False, False])

    def test_a_def_that_ignores_its_number_does_not_earn_it(self):
        out = run("g1", "def double(n):\n    return 7\nsay(double(3))\nsay(double(5))")
        self.assertFalse(out["stars"][2])

    def test_a_def_hands_a_number_back_to_range(self):
        r = report(pixel.LEVEL_BY_KEY["g2"]["reference"])
        self.assertEqual(r.n("jump"), 3)
        self.assertEqual(r.return_calls["len"], 1)
        self.assertEqual(r.range_funcs, ("jumps_for",))
        self.assertEqual(r.call_in_call["jumps_for"], 1)

    def test_a_hardcoded_range_does_not_earn_the_return_goal(self):
        out = run("g2", "for i in range(3):\n    jump()")
        self.assertEqual(out["stars"], [False, False, False])

    def test_a_def_hands_back_different_moods(self):
        r = report(pixel.LEVEL_BY_KEY["g3"]["reference"])
        self.assertEqual([a[0] for n, a in r.log if n == "feel"], ["happy", "sad"])
        self.assertEqual(r.returns, 2)
        self.assertEqual(r.return_values, 2)
        self.assertEqual(r.call_in_call["mood_for"], 2)

    def test_hardcoded_feelings_do_not_earn_the_return_goal(self):
        out = run("g3", 'feel("happy")\nfeel("sad")')
        self.assertEqual(out["stars"], [False, False, False])

    def test_return_outside_a_def_says_where_it_works(self):
        out = pixel.perform("return 3")
        self.assertTrue(out["error"].startswith("Line 1:"), out["error"])
        self.assertIn("return only works inside a def", out["error"])

    def test_return_stops_the_def_there(self):
        r = report('def double(n):\n    return n * 2\n    say("never")\nsay(double(3))')
        self.assertEqual(r.said, ["6"])

    def test_a_missing_return_makes_the_pal_say_nothing(self):
        r = report('def double(n):\n    say(n * 2)\nsay(double(3))')
        self.assertIn("nothing", r.said)
        self.assertNotIn("None", r.said)

    def test_a_missing_return_for_a_range_says_nothing_came_back(self):
        out = pixel.perform('def jumps_for(word):\n    len(word)\nfor i in range(jumps_for("Pip")):\n    jump()')
        self.assertTrue(out["error"].startswith("Line 3:"), out["error"])
        self.assertIn("nothing back", out["error"])
        self.assertNotIn("None", out["error"])

    def test_a_missing_return_for_a_feeling_says_nothing_came_back(self):
        out = pixel.perform('def mood_for(points):\n    if points > 5:\n        return "happy"\nfeel(mood_for(2))')
        self.assertTrue(out["error"].startswith("Line 4:"), out["error"])
        self.assertIn("nothing back", out["error"])
        self.assertNotIn("None", out["error"])


class TheNewFixIts(unittest.TestCase):
    def test_each_bug_misses_and_the_guide_fixes_it(self):
        for key in ("g1", "g2", "g3"):
            with self.subTest(level=key):
                self.assertFalse(run(key, pixel.FIXES[key][1])["fix"])
                self.assertTrue(run(key)["fix"])

    def test_double_that_says_instead_of_returns(self):
        bad = run("g1", pixel.FIXES["g1"][1])
        self.assertIsNone(bad["error"])
        self.assertIn("nothing", pixel.perform(pixel.FIXES["g1"][1])["report"].said)
        self.assertFalse(bad["fix"])

    def test_a_missing_return_in_range_stops_with_a_line(self):
        bad = run("g2", pixel.FIXES["g2"][1])
        self.assertTrue(bad["error"].startswith("Line 3:"), bad["error"])
        self.assertIn("nothing back", bad["error"])
        self.assertFalse(bad["fix"])

    def test_a_return_pushed_inside_the_if_stops_with_a_line(self):
        bad = run("g3", pixel.FIXES["g3"][1])
        self.assertTrue(bad["error"].startswith("Line 6:"), bad["error"])
        self.assertIn("nothing back", bad["error"])
        self.assertFalse(bad["fix"])


class ReturnOverHttp(unittest.TestCase):
    setUp, tearDown, post, get = StudioOverHttp.setUp, StudioOverHttp.tearDown, StudioOverHttp.post, StudioOverHttp.get

    def test_the_new_missions_play_through_the_server(self):
        me = self.post("/join", {"name": "Mia"})["id"]
        self.post("/pixel/save", {"id": me, "drawing": drawing()})
        server.pixel_entry(server.players[me])["solved"].update(
            {key: [True] * 3 for key in pixel.LEVEL_ORDER[:pixel.LEVEL_ORDER.index("g1")]})
        for key in ("g1", "g2", "g3"):
            with self.subTest(level=key):
                out = self.post("/pixel/run", {"id": me, "level": key,
                                               "code": pixel.LEVEL_BY_KEY[key]["reference"]})
                self.assertEqual(out["stars"], [True, True, True], out.get("reply"))
                self.assertEqual(out["rewards"]["gained"], 3)
        state = self.get(f"/pixel/state?id={me}")
        self.assertEqual(state["chapters"][-1]["name"], "Give It Back")
        self.assertEqual(state["chapters"][-1]["icon"], "📦")
        self.assertEqual(len(state["chapters"][-1]["levels"]), 3)
        self.assertEqual(state["max_stars"], 126)


if __name__ == "__main__":
    unittest.main()
