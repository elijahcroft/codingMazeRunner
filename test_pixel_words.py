"""Word Play: the chapter of words, where words repeat with *, len() counts letters, and a loop visits them."""
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
    def test_it_has_three_missions(self):
        chapter = next(i for i, ch in enumerate(pixel.CHAPTERS) if ch["key"] == "p")
        self.assertEqual(pixel.CHAPTERS[chapter], {"key": "p", "name": "Word Play", "icon": "🔤"})
        self.assertEqual([lv["key"] for lv in pixel.LEVELS if lv["chapter"] == chapter], ["p1", "p2", "p3"])

    def test_make_music_comes_just_before_it(self):
        chapter = next(i for i, ch in enumerate(pixel.CHAPTERS) if ch["key"] == "u")
        self.assertEqual(pixel.CHAPTERS[chapter], {"key": "u", "name": "Make Music", "icon": "🎵"})
        self.assertEqual(pixel.LEVEL_BY_KEY["u3"]["chapter"] + 1, pixel.LEVEL_BY_KEY["p1"]["chapter"])

    def test_each_reference_earns_all_three_stars(self):
        for key in ("p1", "p2", "p3"):
            with self.subTest(level=key):
                out = run(key)
                self.assertIsNone(out["error"])
                self.assertEqual(out["stars"], [True, True, True], out["reply"])

    def test_the_three_new_box_gifts_are_wearable(self):
        for key in ("wordhat", "bookhat", "letterspark"):
            with self.subTest(gift=key):
                self.assertIn(key, pixel.BOX_GIFTS)
                self.assertIn(pixel.GIFTS[key]["slot"], pixel.WEAR_SLOTS)

    def test_the_new_python_chips_are_there(self):
        page_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "pixel_page.js")
        with open(page_path, encoding="utf-8") as file:
            page = file.read()
        self.assertIn("word: [", page)
        self.assertIn("letters: [", page)


class TheWords(unittest.TestCase):
    def test_big_name_repeats_the_word_in_one_bubble(self):
        r = report(pixel.LEVEL_BY_KEY["p1"]["reference"])
        self.assertEqual(r.said, ["LunaLunaLuna"])
        self.assertEqual(r.n("say"), 1)
        self.assertEqual(r.log[-1][0], "cheer")

    def test_how_long_counts_letters_and_jumps_that_many(self):
        r = report(pixel.LEVEL_BY_KEY["p2"]["reference"])
        self.assertEqual(r.said, ["4"])
        self.assertEqual(r.n("jump"), 4)
        self.assertTrue(r.range_len)
        hard = report('word = "Luna"\nsay(len(word))\nfor i in range(4):\n    jump()')
        self.assertFalse(hard.range_len)

    def test_first_letter_then_each_letter(self):
        r = report(pixel.LEVEL_BY_KEY["p3"]["reference"])
        self.assertEqual(r.said, ["L", "L", "u", "n", "a"])
        self.assertIn("word", r.loops_over)
        self.assertEqual(r.log[-1][0], "cheer")

    def test_a_loop_can_visit_the_letters_of_a_word(self):
        r = report('for letter in "Pip":\n    say(letter)')
        self.assertEqual(r.said, ["P", "i", "p"])

    def test_a_word_can_be_repeated_and_measured(self):
        self.assertEqual(report('word = "Pixel"\nsay(word * 2)').said, ["PixelPixel"])
        self.assertEqual(report('word = "Pixel"\nsay(len(word))').said, ["5"])


class TheNewFixIts(unittest.TestCase):
    def test_each_bug_misses_and_the_guide_fixes_it(self):
        for key in ("p1", "p2", "p3"):
            with self.subTest(level=key):
                self.assertFalse(run(key, pixel.FIXES[key][1])["fix"])
                self.assertTrue(run(key)["fix"])

    def test_big_name_bug_says_the_name_twice(self):
        bad = run("p1", pixel.FIXES["p1"][1])
        self.assertIsNone(bad["error"])
        self.assertFalse(bad["fix"])

    def test_how_long_bug_says_one_too_many(self):
        bad = run("p2", pixel.FIXES["p2"][1])
        self.assertIsNone(bad["error"])
        self.assertFalse(bad["fix"])

    def test_first_letter_bug_stops_past_the_end(self):
        bad = run("p3", pixel.FIXES["p3"][1])
        self.assertTrue(bad["error"].startswith("Line "), bad["error"])


class WordsOverHttp(unittest.TestCase):
    setUp, tearDown, post, get = StudioOverHttp.setUp, StudioOverHttp.tearDown, StudioOverHttp.post, StudioOverHttp.get

    def test_the_new_missions_play_through_the_server(self):
        me = self.post("/join", {"name": "Mia"})["id"]
        self.post("/pixel/save", {"id": me, "drawing": drawing()})
        server.pixel_entry(server.players[me])["solved"].update(
            {key: [True] * 3 for key in pixel.LEVEL_ORDER[:pixel.LEVEL_ORDER.index("p1")]})
        for key in ("p1", "p2", "p3"):
            with self.subTest(level=key):
                out = self.post("/pixel/run", {"id": me, "level": key,
                                               "code": pixel.LEVEL_BY_KEY[key]["reference"]})
                self.assertEqual(out["stars"], [True, True, True], out.get("reply"))
                self.assertEqual(out["rewards"]["gained"], 3)
        state = self.get(f"/pixel/state?id={me}")
        chapter = next(ch for ch in state["chapters"] if ch["name"] == "Word Play")
        self.assertEqual(len(chapter["levels"]), 3)
        self.assertEqual(state["max_stars"], 135)


if __name__ == "__main__":
    unittest.main()
