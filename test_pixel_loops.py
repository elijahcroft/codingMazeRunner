"""Loop in a Loop: the chapter of for loops inside for loops."""
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
    def test_it_comes_last_and_has_three_missions(self):
        self.assertEqual(pixel.CHAPTERS[-1], {"key": "n", "name": "Loop in a Loop", "icon": "🪆"})
        self.assertEqual([lv["key"] for lv in pixel.LEVELS[-3:]], ["n1", "n2", "n3"])
        self.assertEqual({lv["chapter"] for lv in pixel.LEVELS[-3:]}, {len(pixel.CHAPTERS) - 1})

    def test_each_reference_earns_all_three_stars(self):
        for key in ("n1", "n2", "n3"):
            with self.subTest(level=key):
                out = run(key)
                self.assertIsNone(out["error"])
                self.assertEqual(out["stars"], [True, True, True], out["reply"])

    def test_the_three_new_box_gifts_are_wearable(self):
        for key in ("loophat", "spiralhat", "loopspark"):
            with self.subTest(gift=key):
                self.assertIn(key, pixel.BOX_GIFTS)
                self.assertIn(pixel.GIFTS[key]["slot"], pixel.WEAR_SLOTS)


class NestedLoops(unittest.TestCase):
    def test_a_loop_in_a_loop_is_deeper(self):
        self.assertEqual(report("for i in range(2):\n    jump()").loop_depth, 1)
        out = report("for i in range(2):\n    for j in range(2):\n        jump()")
        self.assertEqual(out.loop_depth, 2)
        self.assertEqual(out.n("jump"), 4)
        three = report("for i in range(2):\n    for j in range(2):\n        for k in range(2):\n            jump()")
        self.assertEqual(three.loop_depth, 3)
        self.assertEqual(three.n("jump"), 8)

    def test_clap_clap_jump_waves_twice_then_jumps(self):
        r = report(pixel.LEVEL_BY_KEY["n1"]["reference"])
        self.assertEqual(r.n("wave"), 6)
        self.assertEqual(r.n("jump"), 3)
        self.assertTrue(r.first("wave", "wave", "jump"))

    def test_the_times_table_says_each_fact(self):
        r = report(pixel.LEVEL_BY_KEY["n2"]["reference"])
        self.assertEqual(r.said, [f"{i} x {j} = {i * j}" for i in range(1, 4) for j in range(1, 4)])
        self.assertEqual(pixel._table(r), 9)

    def test_the_stairs_get_bigger(self):
        r = report(pixel.LEVEL_BY_KEY["n3"]["reference"])
        self.assertEqual(pixel._stair_runs(r), [1, 2, 3])
        self.assertEqual(r.n("right"), 6)
        self.assertEqual(r.log[-1][0], "jump")

    def test_a_wrong_fact_is_not_counted(self):
        r = report('say("2 x 2 = 5")')
        self.assertEqual(pixel._table(r), 0)


class TheNewFixIts(unittest.TestCase):
    def test_each_bug_runs_but_gets_it_wrong_and_the_guide_fixes_it(self):
        for key in ("n1", "n2", "n3"):
            with self.subTest(level=key):
                bad = run(key, pixel.FIXES[key][1])
                self.assertIsNone(bad["error"])
                self.assertFalse(bad["fix"])
                self.assertTrue(run(key)["fix"])


class LoopsOverHttp(unittest.TestCase):
    setUp, tearDown, post, get = StudioOverHttp.setUp, StudioOverHttp.tearDown, StudioOverHttp.post, StudioOverHttp.get

    def test_the_new_missions_play_through_the_server(self):
        me = self.post("/join", {"name": "Mia"})["id"]
        self.post("/pixel/save", {"id": me, "drawing": drawing()})
        server.pixel_entry(server.players[me])["solved"].update(
            {key: [True] * 3 for key in pixel.LEVEL_ORDER[:pixel.LEVEL_ORDER.index("n1")]})
        for key in ("n1", "n2", "n3"):
            with self.subTest(level=key):
                out = self.post("/pixel/run", {"id": me, "level": key,
                                               "code": pixel.LEVEL_BY_KEY[key]["reference"]})
                self.assertEqual(out["stars"], [True, True, True], out.get("reply"))
                self.assertEqual(out["rewards"]["gained"], 3)
        state = self.get(f"/pixel/state?id={me}")
        self.assertEqual(state["chapters"][-1]["name"], "Loop in a Loop")
        self.assertEqual(len(state["chapters"][-1]["levels"]), 3)


if __name__ == "__main__":
    unittest.main()
