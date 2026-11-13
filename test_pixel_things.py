"""Furniture students draw and code: clicking a coded thing runs its on_click."""
import unittest

import pixel
import server
from test_pixel_fun import Fun

LAMP = {"key": "lamp1", "title": "Lamp", "size": 16, "speed": 6, "palette": ["#000000", "#ffd93b"],
        "frames": ["0" + "." * 255, "1" + "." * 255], "names": ["", ""]}
SWITCH = 'def on_click():\n    if clicks() % 2 == 1:\n        pose(2)\n    else:\n        pose(1)\n    sound("ding")\n    jump()\n'


class Runner(unittest.TestCase):
    def test_each_click_carries_on_from_the_last(self):
        frames = [pixel.thing_steps(pixel.run_thing(SWITCH, LAMP, n)["steps"], 2, False)[1]["frame"] for n in (1, 2, 3)]
        self.assertEqual(frames, [1, 0, 1])

    def test_only_furniture_commands(self):
        out = pixel.run_thing('def on_click():\n    right(3)\n', LAMP, 1)
        self.assertIn("Furniture can't right()", out["error"])
        self.assertEqual(out["line"], 2)

    def test_it_needs_an_on_click(self):
        self.assertIn("def on_click", pixel.run_thing("jump()", LAMP, 1)["error"])

    def test_words_wait_for_typing_to_be_on(self):
        steps = pixel.run_thing('def on_click():\n    say("Hooray!")\n    say("my own words")\n', LAMP, 1)["steps"]
        self.assertEqual([s["text"] for s in pixel.thing_steps(steps, 2, False)[0]], ["Hooray!"])
        self.assertEqual(len(pixel.thing_steps(steps, 2, True)[0]), 2)

    def test_a_long_loop_is_cut_short(self):
        steps = pixel.run_thing('def on_click():\n    for i in range(100):\n        jump()\n', LAMP, 1)["steps"]
        self.assertEqual(len(pixel.thing_steps(steps, 2, False)[0]), pixel.THING_STEPS)


class Things(Fun):
    def setUp(self):
        super().setUp()
        self.entry(self.mia)["drawings"].append(dict(LAMP))
        self.do(self.mia, "home")
        self.assertTrue(self.do(self.mia, "place", key="lamp1", x=100, y=.5)["ok"])
        self.piece = server.home_of(self.entry(self.mia))["art"][0]["id"]

    def news(self, kind):
        return [e for e in server.pixel_room["events"] if e["kind"] == kind]

    def test_a_coded_thing_plays_for_everyone_in_the_home(self):
        self.assertIn("error", self.do(self.mia, "poke", piece=self.piece))       # no code yet
        self.assertTrue(server.thing_save(self.mia, {"key": "lamp1", "code": SWITCH})["ok"])
        self.assertTrue(self.view(self.mia, -1)["placed"][0]["coded"])
        self.do(self.ben, "home", seat=self.spot(self.mia)["seat"])
        self.assertTrue(self.do(self.ben, "poke", piece=self.piece)["ok"])
        poke = self.news("poke")[-1]
        self.assertEqual([s["do"] for s in poke["steps"]], ["pose", "sound", "jump"])
        self.assertEqual(poke["loc"], self.spot(self.mia)["loc"])
        self.assertEqual(self.view(self.ben)["placed"][0]["look"]["frame"], 1)      # someone arriving later sees it lit
        self.assertIn("error", self.do(self.ben, "poke", piece=self.piece))        # too quick
        self.advance(1)
        self.do(self.ben, "poke", piece=self.piece)
        self.assertEqual(self.news("poke")[-1]["look"]["frame"], 0)

    def test_a_bug_tells_the_owner_and_not_the_visitor(self):
        server.thing_save(self.mia, {"key": "lamp1", "code": "def on_click():\n    jump(\n"})
        self.do(self.ben, "home", seat=self.spot(self.mia)["seat"])
        self.assertIn("Mia's code has a bug", self.do(self.ben, "poke", piece=self.piece)["error"])
        self.advance(1)
        self.assertIn("Line", self.do(self.mia, "poke", piece=self.piece)["error"])

    def test_only_your_own_drawings_get_code(self):
        self.assertIn("error", server.thing_save(self.ben, {"key": "lamp1", "code": SWITCH}))
        self.assertIn("error", server.thing_save(self.mia, {"key": "lamp1", "code": "x" * (pixel.MAX_CODE + 1)}))

    def test_new_code_starts_the_thing_afresh_and_tells_the_room(self):
        server.thing_save(self.mia, {"key": "lamp1", "code": SWITCH})
        self.do(self.mia, "poke", piece=self.piece)
        server.thing_save(self.mia, {"key": "lamp1", "code": ""})
        row = self.news("recode")[-1]["item"]
        self.assertFalse(row["coded"])
        self.assertIsNone(row["look"])
        self.assertNotIn("lamp1", self.entry(self.mia)["things"])

    def test_a_thing_out_in_the_world_works_too(self):
        server.thing_save(self.mia, {"key": "lamp1", "code": SWITCH})
        self.do(self.mia, "home", out=True)
        self.advance(1)
        self.do(self.mia, "place", key="lamp1", x=100, y=.5)
        outside = server.pixel_class["placed"][0]["id"]
        self.assertTrue(self.do(self.ben, "poke", piece=outside)["ok"])
        self.assertEqual(self.news("poke")[-1]["loc"], 0)

    def test_placed_copies_keep_their_frames(self):
        self.assertEqual(len(self.view(self.mia, -1)["placed"][0]["pal"]["frames"]), 2)

    def test_nobody_learns_who_owns_it(self):
        server.thing_save(self.mia, {"key": "lamp1", "code": SWITCH})
        self.do(self.ben, "home", seat=self.spot(self.mia)["seat"])
        self.assertNotIn(self.mia["id"], str(self.view(self.ben)))


if __name__ == "__main__":
    unittest.main()
