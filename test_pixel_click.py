"""🖱️ Click Me!: def on_click(): missions, and clicking your pal after the show."""
import unittest

import pixel
import server
from test_pixel import StudioOverHttp, drawing

K2 = pixel.LEVEL_BY_KEY["k2"]["reference"]


class Pokes(unittest.TestCase):
    def test_each_click_gives_only_what_that_click_does(self):
        said = [pixel.poke(K2, pixel.PIP, ["click"] * n, pixel.commands_for("k2"))["steps"] for n in (1, 2, 3, 4)]
        self.assertEqual([[s["do"] for s in steps] for steps in said],
                         [["say", "jump"], ["say", "jump"], ["say", "cheer"], ["say", "jump"]])
        self.assertEqual([steps[0]["text"] for steps in said], ["1", "2", "3", "4"])

    def test_code_with_no_on_click_is_not_listening(self):
        out = pixel.poke("jump()", pixel.PIP, ["click"], pixel.commands_for("k2"))
        self.assertFalse(out["listening"])
        self.assertEqual(out["steps"], [])

    def test_a_mistake_in_the_click_says_where(self):
        out = pixel.poke("def on_click():\n    jump(5)", pixel.PIP, ["click"], pixel.commands_for("k1"))
        self.assertTrue(out["error"].startswith("Line 2"))

    def test_top_lines_are_not_played_again_on_a_click(self):
        out = pixel.poke('say("Hi")\ndef on_click():\n    jump()', pixel.PIP, ["click", "click"], pixel.commands_for("k1"))
        self.assertEqual([s["do"] for s in out["steps"]], ["jump"])


class Keys(unittest.TestCase):
    WALK = pixel.FREE_IDEAS[[t for t, c in pixel.FREE_IDEAS].index("Walk with the arrow keys")][1]

    def test_arrow_keys_and_space_run_on_key(self):
        free = pixel.free_commands("t1")
        self.assertEqual([s["do"] for s in pixel.poke(self.WALK, pixel.PIP, ["key:right"], free)["steps"]], ["walk"])
        out = pixel.poke(self.WALK, pixel.PIP, ["key:right", "key:right", "key:space"], free)
        self.assertEqual([s["do"] for s in out["steps"]], ["jump"])
        walks = pixel.poke(self.WALK, pixel.PIP, ["key:right", "key:right"], free)["steps"]
        self.assertEqual(walks[0]["to"], pixel.START + 2)       # the earlier keys still count

    def test_only_real_keys_and_clicks_count(self):
        free = pixel.free_commands("t1")
        self.assertFalse(pixel.poke(self.WALK, pixel.PIP, ["key:q", "feed", 3], free)["listening"])
        self.assertFalse(pixel.poke(self.WALK, pixel.PIP, ["click"], free)["listening"])


class ClickMistakes(unittest.TestCase):
    def run_k1(self, code):
        return pixel.run_level(pixel.LEVEL_BY_KEY["k1"], code, pixel.PIP)

    def test_a_nearly_right_name_is_named(self):
        for name in ("onclick", "On_click", "clicked"):   # on_clicked already stops with "Did you mean"
            with self.subTest(name=name):
                self.assertIn("def on_click():", self.run_k1(f"def {name}():\n    jump()")["reply"])
                self.assertIn(name, self.run_k1(f"def {name}():\n    jump()")["reply"])

    def test_a_missing_def_says_to_add_it(self):
        self.assertIn("def on_click():", self.run_k1("on_click():\n    jump()")["error"])
        self.assertIn("start the line with  def", self.run_k1("on_click():\n    jump()")["error"])


class PokesOverHttp(unittest.TestCase):
    setUp, tearDown, post, get = StudioOverHttp.setUp, StudioOverHttp.tearDown, StudioOverHttp.post, StudioOverHttp.get

    def test_only_open_missions_and_nothing_is_kept(self):
        me = self.post("/join", {"name": "Mia"})["id"]
        self.post("/pixel/save", {"id": me, "drawing": drawing()})
        self.assertIn("error", self.post("/pixel/poke", {"id": me, "level": "k2", "code": K2, "clicks": 1}))
        for key in pixel.LEVEL_ORDER[:pixel.LEVEL_ORDER.index("k2")]:
            self.post("/pixel/run", {"id": me, "level": key, "code": pixel.LEVEL_BY_KEY[key]["reference"]})
        entry = server.pixel_entry(server.players[me])
        runs, coins = dict(entry["runs"]), entry["coins"]
        out = self.post("/pixel/poke", {"id": me, "level": "k2", "code": K2, "clicks": 3})
        self.assertEqual([s["do"] for s in out["steps"]], ["say", "cheer"])
        self.assertEqual(entry["runs"], runs)
        self.assertEqual(entry["coins"], coins)
        self.assertEqual(self.post("/pixel/poke", {"id": me, "level": "k2", "code": K2, "clicks": "3"}), {"error": "bad"})

    def test_a_click_keeps_the_shows_own_surprises(self):
        me = self.post("/join", {"name": "Mia"})["id"]
        for key in pixel.LEVEL_ORDER[:pixel.LEVEL_ORDER.index("r1") + 1]:      # randint comes with Surprise!
            self.post("/pixel/run", {"id": me, "level": key, "code": pixel.LEVEL_BY_KEY[key]["reference"]})
        code = "n = randint(1, 1000)\nsay(n)\ndef on_click():\n    say(n)"
        for _ in range(3):
            show = self.post("/pixel/run", {"id": me, "level": "free", "code": code})
            said = next(s["text"] for s in show["steps"] if s["do"] == "say")
            out = self.post("/pixel/poke", {"id": me, "level": "free", "code": code, "events": ["click"], "seed": show["seed"]})
            self.assertEqual(out["steps"][0]["text"], said)

    def test_the_free_stage_listens_too(self):
        me = self.post("/join", {"name": "Mia"})["id"]
        for key in pixel.LEVEL_ORDER[:pixel.LEVEL_ORDER.index(pixel.FREE_AFTER) + 1]:
            self.post("/pixel/run", {"id": me, "level": key, "code": pixel.LEVEL_BY_KEY[key]["reference"]})
        out = self.post("/pixel/poke", {"id": me, "level": "free", "code": 'def on_click():\n    scene("space")\n    jump()', "clicks": 1})
        self.assertEqual([s["do"] for s in out["steps"]], ["scene", "jump"])


if __name__ == "__main__":
    unittest.main()
