"""👗 Dress Up: wear() on the Code stage, and the chapter right after My Move."""
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
    def test_it_comes_right_after_my_move(self):
        chapter = next(i for i, ch in enumerate(pixel.CHAPTERS) if ch["key"] == "d")
        self.assertEqual(pixel.CHAPTERS[chapter], {"key": "d", "name": "Dress Up", "icon": "👗"})
        self.assertEqual(pixel.CHAPTERS[chapter - 1]["key"], "m")
        self.assertEqual([lv["key"] for lv in pixel.LEVELS if lv["chapter"] == chapter], ["d1", "d2", "d3"])
        self.assertEqual([ch["icon"] for ch in pixel.CHAPTERS].count("👗"), 1)

    def test_each_reference_earns_all_three_stars(self):
        for key in ("d1", "d2", "d3"):
            with self.subTest(level=key):
                out = run(key)
                self.assertIsNone(out["error"])
                self.assertEqual(out["stars"], [True, True, True], out["reply"])

    def test_they_only_use_commands_and_python_from_before_them(self):
        self.assertEqual(pixel.LEVEL_BY_KEY["d1"]["adds"], ["wear"])
        self.assertIn("wear", pixel.commands_for("d1"))
        self.assertNotIn("wear", pixel.commands_for("m1"))
        for key in ("d1", "d2", "d3"):
            with self.subTest(level=key):
                self.assertFalse({"list", "if", "while", "def", "return"} & set(pixel.LEVEL_BY_KEY[key]["python"]))

    def test_the_three_new_box_gifts_are_wearable(self):
        for key in ("showhat", "diva", "glamspark"):
            with self.subTest(gift=key):
                self.assertIn(key, pixel.BOX_GIFTS)
                self.assertIn(pixel.GIFTS[key]["slot"], pixel.WEAR_SLOTS)


class TheWearCommand(unittest.TestCase):
    def test_a_crown_goes_on_the_hat_place(self):
        r = report('wear("crown")')
        self.assertEqual(r.wears, ["crown"])
        self.assertEqual(r.worn, {"hat": "crown"})
        step = pixel.perform('wear("crown")')["steps"][0]
        self.assertEqual((step["do"], step["key"], step["slot"]), ("wear", "crown", "hat"))

    def test_none_or_no_brackets_takes_it_off(self):
        self.assertEqual(report('wear("crown")\nwear("shades")\nwear("none", "hat")').worn, {"face": "shades"})
        self.assertEqual(report('wear("crown")\nwear("none")').worn, {})
        self.assertEqual(report('wear("crown")\nwear()').worn, {})

    def test_friendly_words_point_at_real_things(self):
        self.assertEqual(report('wear("hat")').worn, {"hat": "party"})
        self.assertEqual(report('wear("glasses")').worn, {"face": "shades"})

    def test_a_made_up_name_gets_a_kind_error_with_real_ones(self):
        out = pixel.perform('wear("crwn")')
        self.assertEqual(out["error"], 'Line 1: I don\'t have a "crwn". Try "crown", "tiara" or "sunhat".')

    def test_it_is_free_and_does_not_change_the_hang_out_look(self):
        p = {"id": "wear-kid", "name": "Mia"}
        entry = server.pixel_entry(p)
        entry["wear"] = {"hat": "party"}
        out = run("d1")
        self.assertEqual(out["stars"], [True, True, True])
        self.assertEqual(entry["wear"], {"hat": "party"})       # a show is pretend only

    def test_the_free_stage_has_it_after_my_move(self):
        self.assertIn("wear", pixel.free_commands("d1"))
        self.assertIn("wear", pixel.free_commands("t1"))

    def test_each_change_is_held_for_a_short_beat(self):
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "pixel_stage.js")
        with open(path, encoding="utf-8") as file:
            stage = file.read()
        self.assertIn("async wear(s, t)", stage)
        self.assertIn("await sleep(450, t)", stage)

    def test_coded_things_can_put_something_on_too(self):
        out = pixel.run_thing('def on_click():\n    wear("crown")\n    spin()', drawing(), 1)
        self.assertIsNone(out["error"])
        steps, look = pixel.thing_steps(out["steps"], 1, True)
        self.assertTrue(any(s["do"] == "wear" and s["key"] == "crown" for s in steps))
        self.assertEqual(look["wear"], {"hat": "crown"})
        out = pixel.run_thing('def on_click():\n    wear("crown")\n    wear("none")', drawing(), 1)
        _steps, look = pixel.thing_steps(out["steps"], 1, True)
        self.assertEqual(look["wear"], {})


class OldSavesStayOpen(unittest.TestCase):
    def setUp(self):
        self.saved = server.players, server.pixel_class, server.pixel_feed
        server.players, server.pixel_class, server.pixel_feed = {}, {"open": 0}, []
        self.addCleanup(self.restore)

    def restore(self):
        server.players, server.pixel_class, server.pixel_feed = self.saved

    def old_kid(self, through):
        p = {"id": "old-kid", "name": "Mia"}
        server.players[p["id"]] = p
        entry = server.pixel_entry(p)
        old = server.pixel_old_level_order()
        for key in old[:old.index(through) + 1]:
            entry["solved"][key] = [True, True, True]
        entry.pop("reached", None)
        server.pixel_class.pop("dressup", None)
        return p

    def levels(self, p):
        return {level["key"]: level for chapter in server.pixel_state(p)["chapters"]
                for level in chapter["levels"]}

    def test_a_student_midway_in_encore_keeps_their_t_mission_and_gets_the_new_chapter(self):
        p = self.old_kid("t1")                    # t1 finished, t2 is where they were
        levels = self.levels(p)
        for key in ("t1", "t2", "d1", "d2", "d3"):
            with self.subTest(level=key):
                self.assertTrue(levels[key]["open"])
        self.assertFalse(levels["l1"]["open"])    # still not the next chapter
        self.assertEqual(server.pixel_state(p)["current"], "t2")
        self.assertEqual(server.pixel_where_class(server.pixel_entry(p), server.pixel_frontier(server.pixel_entry(p))), "t")

    def test_a_student_who_just_finished_my_move_can_open_encore_and_dress_up(self):
        p = self.old_kid("m1")
        levels = self.levels(p)
        for key in ("d1", "d2", "d3", "t1"):
            with self.subTest(level=key):
                self.assertTrue(levels[key]["open"])
        self.assertFalse(levels["t2"]["open"])
        self.assertEqual(server.pixel_state(p)["current"], "t1")

    def test_a_brand_new_student_goes_my_move_then_dress_up_then_encore(self):
        order = [chapter["key"] for chapter in pixel.CHAPTERS]
        self.assertEqual(order[:6], ["a", "h", "b", "m", "d", "t"])
        self.assertEqual([lv["key"] for lv in pixel.LEVELS[:13]],
                         ["a1", "a2", "a3", "h1", "h3", "h4", "b1", "b2", "m1", "d1", "d2", "d3", "t1"])
        p = {"id": "new-kid", "name": "New"}
        server.players[p["id"]] = p
        entry = server.pixel_entry(p)
        self.assertEqual(pixel.LEVEL_ORDER[server.pixel_frontier(entry)], "a1")
        for key in pixel.LEVEL_ORDER[:pixel.LEVEL_ORDER.index("m1") + 1]:
            entry["solved"][key] = [True, True, True]
        self.assertEqual(pixel.LEVEL_ORDER[server.pixel_frontier(entry)], "d1")
        self.assertTrue(server.pixel_is_open(entry, "d1"))
        self.assertFalse(server.pixel_is_open(entry, "t1"))
        for key in ("d1", "d2", "d3"):
            entry["solved"][key] = [True, True, True]
        self.assertEqual(pixel.LEVEL_ORDER[server.pixel_frontier(entry)], "t1")

    def test_the_teachers_open_index_moves_with_the_new_missions(self):
        old = server.pixel_old_level_order()
        for key in ("h3", "m1", "t1"):
            with self.subTest(open=key):
                server.players = {}
                server.players["teacher-kid"] = {"id": "teacher-kid", "name": "Mia"}
                server.pixel_class = {"open": old.index(key)}
                entry = server.pixel_entry(server.players["teacher-kid"])
                self.assertEqual(pixel.LEVEL_ORDER[server.pixel_frontier(entry)], key)


class DressOverHttp(unittest.TestCase):
    setUp, tearDown, post, get = StudioOverHttp.setUp, StudioOverHttp.tearDown, StudioOverHttp.post, StudioOverHttp.get

    def test_the_new_missions_play_through_the_server(self):
        me = self.post("/join", {"name": "Mia"})["id"]
        self.post("/pixel/save", {"id": me, "drawing": drawing()})
        server.pixel_entry(server.players[me])["solved"].update(
            {key: [True] * 3 for key in pixel.LEVEL_ORDER[:pixel.LEVEL_ORDER.index("d1")]})
        for key in ("d1", "d2", "d3"):
            with self.subTest(level=key):
                out = self.post("/pixel/run", {"id": me, "level": key,
                                               "code": pixel.LEVEL_BY_KEY[key]["reference"]})
                self.assertEqual(out["stars"], [True, True, True], out.get("reply"))
                self.assertEqual(out["rewards"]["gained"], 3)
        state = self.get(f"/pixel/state?id={me}")
        chapter = next(ch for ch in state["chapters"] if ch["name"] == "Dress Up")
        self.assertEqual(len(chapter["levels"]), 3)
        self.assertEqual(state["max_stars"], 135)


if __name__ == "__main__":
    unittest.main()
