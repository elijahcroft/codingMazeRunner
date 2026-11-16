"""🎬 Free stage: after My Move, any show at all, with stage toys and no stars."""
import unittest

import pixel
import server
from test_pixel import StudioOverHttp, drawing

SHOW = 'scene("beach")\nfriend("cat")\nfriend_say("Hi!")\nsound("tada")\nrain()\nfor i in range(2):\n    jump()\nsay("The end")'


class FreeStage(unittest.TestCase):
    def test_every_stage_toy_runs(self):
        out = pixel.public(pixel.perform(SHOW + "\nsnow()\nfriend_jump()\nhide()\nappear()\nbye()",
                                         commands=pixel.free_commands("m1")))
        self.assertEqual(out.get("error"), None)
        done = {s["do"] for s in out["steps"]}
        for toy in ("scene", "friend", "rain", "snow", "hide", "appear"):
            self.assertTrue(any(toy in d for d in done), toy)

    def test_every_idea_runs_right_after_my_move(self):
        for title, code in pixel.FREE_IDEAS:
            with self.subTest(idea=title):
                out = pixel.public(pixel.perform(code, commands=pixel.free_commands("t1")))
                self.assertIsNone(out.get("error"))

    def test_it_has_what_they_learned_and_the_toys_only(self):
        early = pixel.free_commands("m1")
        self.assertIn("jump", early)
        self.assertIn("scene", early)
        self.assertNotIn("grow", early)            # Grow big comes after My Move
        self.assertIn("grow", pixel.free_commands("t1"))


    def test_every_command_a_student_can_get_has_words_on_the_page(self):
        import os, re
        with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "pixel_page.js"), encoding="utf-8") as file:
            page = file.read()
        words = page[page.index("const WORDS"):page.index("const SAMPLE")]
        python = page[page.index("const PYTHON"):page.index("const ALL_PYTHON")]
        for name in pixel.free_commands(pixel.LEVEL_ORDER[-1]):
            with self.subTest(command=name):
                self.assertRegex(words, rf"\b{name}:")
        for lv in pixel.LEVELS:
            for key in lv["python"]:
                with self.subTest(python=key):
                    self.assertRegex(python, rf"\b{key}:")


class FreeStageOverHttp(unittest.TestCase):
    setUp, tearDown, post, get = StudioOverHttp.setUp, StudioOverHttp.tearDown, StudioOverHttp.post, StudioOverHttp.get

    def finish_up_to_my_move(self, me):
        out = None
        for key in pixel.LEVEL_ORDER[:pixel.LEVEL_ORDER.index(pixel.FREE_AFTER) + 1]:
            out = self.post("/pixel/run", {"id": me, "level": key, "code": pixel.LEVEL_BY_KEY[key]["reference"]})
        return out

    def test_it_opens_with_my_move(self):
        me = self.post("/join", {"name": "Mia"})["id"]
        self.post("/pixel/save", {"id": me, "drawing": drawing()})
        self.assertIn("error", self.get(f"/pixel/level?id={me}&level=free"))
        self.assertIn("error", self.post("/pixel/run", {"id": me, "level": "free", "code": "jump()"}))
        self.assertFalse(self.get(f"/pixel/state?id={me}")["free_open"])
        last = self.finish_up_to_my_move(me)
        self.assertTrue(last["rewards"]["free_opened"])
        self.assertTrue(last["state"]["free_open"])
        level = self.get(f"/pixel/level?id={me}&level=free")
        self.assertTrue(level["free"])
        self.assertEqual(level["goals"], [])
        self.assertIn("scene", level["commands"])

    def test_a_show_runs_keeps_its_code_and_pays_nothing(self):
        me = self.post("/join", {"name": "Mia"})["id"]
        self.finish_up_to_my_move(me)
        coins = server.pixel_entry(server.players[me])["coins"]
        stars = server.pixel_stars(server.pixel_entry(server.players[me]))
        out = self.post("/pixel/run", {"id": me, "level": "free", "code": SHOW})
        self.assertIsNone(out.get("error"))
        self.assertEqual(out["stars"], [])
        self.assertEqual(out["rewards"], {})
        self.assertTrue(any(s["do"] == "say" for s in out["steps"]))
        self.assertEqual(self.get(f"/pixel/level?id={me}&level=free")["code"], SHOW)
        entry = server.pixel_entry(server.players[me])
        self.assertEqual(entry["coins"], coins)
        self.assertEqual(server.pixel_stars(entry), stars)
        self.assertNotIn("free", entry["solved"])

    def test_a_real_show_tells_the_class_now_and_then(self):
        me = self.post("/join", {"name": "Zed"})["id"]
        self.finish_up_to_my_move(me)
        feed = lambda: [f for f in server.pixel_feed if f["text"] == "🎬 Zed made a show on the Free stage"]
        self.post("/pixel/run", {"id": me, "level": "free", "code": "jump()"})
        self.assertEqual(feed(), [])
        self.post("/pixel/run", {"id": me, "level": "free", "code": SHOW})
        self.post("/pixel/run", {"id": me, "level": "free", "code": SHOW})
        self.assertEqual(len(feed()), 1)

    def test_a_command_not_learned_yet_says_so(self):
        me = self.post("/join", {"name": "Mia"})["id"]
        self.finish_up_to_my_move(me)
        out = self.post("/pixel/run", {"id": me, "level": "free", "code": 'look("left")'})   # Who's there? isn't open yet
        self.assertTrue(out.get("error"))

    def test_the_teacher_page_still_works(self):
        me = self.post("/join", {"name": "Mia"})["id"]
        self.finish_up_to_my_move(me)
        self.post("/pixel/run", {"id": me, "level": "free", "code": SHOW})
        self.assertTrue(any(r["name"] == "Mia" for r in server.pixel_overview()["students"]))


if __name__ == "__main__":
    unittest.main()
