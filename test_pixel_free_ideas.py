"""💡 Free stage ideas: small shows that work as soon as the Free stage opens."""
import unittest

import pixel
import test_pixel

EARLIEST = pixel.LEVEL_ORDER[pixel.LEVEL_ORDER.index(pixel.FREE_AFTER) + 1]
LATEST = pixel.LEVEL_ORDER[-1]
NEW = ("Robot dance party", "Spell my name", "Ode to Joy", "Drum beat",
       "Count the stars", "Picnic with a friend")


class FreeIdeas(unittest.TestCase):
    def run_idea(self, code, upto, stars=0):
        return pixel.public(pixel.perform(code, commands=pixel.free_commands(upto),
                                          setup=pixel.free_setup(stars)))

    def test_the_six_new_ideas_are_there(self):
        titles = [title for title, _code in pixel.FREE_IDEAS]
        for title in NEW:
            self.assertIn(title, titles)
        self.assertEqual(len(titles), len(set(titles)), "two ideas have the same name")

    def test_every_idea_runs_early_and_at_the_end(self):
        for upto in (EARLIEST, LATEST):
            for title, code in pixel.FREE_IDEAS:
                with self.subTest(idea=title, upto=upto):
                    self.assertLessEqual(len(code.splitlines()), 10)
                    out = self.run_idea(code, upto)
                    self.assertIsNone(out["error"])
                    if "def on_key" not in code:        # a pal to steer does its moves when keys are pressed
                        self.assertGreaterEqual(len(out["steps"]), 4)

    def test_every_idea_works_before_any_stars_are_earned(self):
        for title, code in pixel.FREE_IDEAS:
            with self.subTest(idea=title):
                self.assertIsNone(self.run_idea(code, EARLIEST, stars=0)["error"])

    def test_the_new_ideas_have_enough_to_show_friends(self):
        ideas = dict(pixel.FREE_IDEAS)
        for title in NEW:
            with self.subTest(idea=title):
                out = self.run_idea(ideas[title], EARLIEST)
                self.assertGreaterEqual(len(pixel.compile_move(out["steps"])), 4)

    def test_ode_to_joy_has_the_real_tune(self):
        code = dict(pixel.FREE_IDEAS)["Ode to Joy"]
        out = self.run_idea(code, EARLIEST)
        notes = [s["name"] for s in out["steps"] if s["do"] == "note"]
        self.assertEqual(notes, ["E", "E", "F", "G", "G", "F", "E", "D", "C",
                                 "C", "D", "E", "E", "D", "D"])
        self.assertEqual(out["steps"][-1]["do"], "cheer")

    def test_the_new_ideas_show_six_different_things(self):
        code = dict(pixel.FREE_IDEAS)
        self.assertIn("\n    for step in range(3):\n        jump()", code["Robot dance party"])
        self.assertIn("for letter in name:", code["Spell my name"])
        self.assertIn("for n in tune:", code["Ode to Joy"])
        self.assertIn("def beat():", code["Drum beat"])
        self.assertIn('note("rest")', code["Drum beat"])
        self.assertIn("def count_stars():", code["Count the stars"])
        self.assertIn("return 4", code["Count the stars"])
        self.assertIn('scene("park")', code["Picnic with a friend"])
        self.assertIn('friend("bunny")', code["Picnic with a friend"])
        self.assertIn("friend_say(", code["Picnic with a friend"])

    def test_spell_my_name_says_each_letter_then_cheers(self):
        out = self.run_idea(dict(pixel.FREE_IDEAS)["Spell my name"], EARLIEST)
        said = [s["text"] for s in out["steps"] if s["do"] == "say"]
        self.assertEqual(said[1:], list("Luna"))
        self.assertEqual([s["do"] for s in out["steps"]].count("jump"), 4)
        self.assertEqual(out["steps"][-1]["do"], "cheer")

    def test_count_the_stars_uses_the_returned_number(self):
        out = self.run_idea(dict(pixel.FREE_IDEAS)["Count the stars"], EARLIEST)
        said = [s["text"] for s in out["steps"] if s["do"] == "say"]
        self.assertEqual(said, ["Let's count the stars!", "4"])
        self.assertEqual([s["do"] for s in out["steps"]].count("stars"), 4)


class FreeIdeasOverHttp(unittest.TestCase):
    setUp = test_pixel.StudioOverHttp.setUp
    tearDown = test_pixel.StudioOverHttp.tearDown
    post = test_pixel.StudioOverHttp.post
    get = test_pixel.StudioOverHttp.get

    def test_the_new_ideas_are_offered_as_soon_as_my_move_is_done(self):
        me = self.post("/join", {"name": "Mia"})["id"]
        self.post("/pixel/save", {"id": me, "drawing": test_pixel.drawing()})
        for key in pixel.LEVEL_ORDER[:pixel.LEVEL_ORDER.index(pixel.FREE_AFTER) + 1]:
            self.post("/pixel/run", {"id": me, "level": key, "code": pixel.LEVEL_BY_KEY[key]["reference"]})
        titles = [title for title, _code in self.get(f"/pixel/level?id={me}&level=free")["ideas"]]
        for title in NEW:
            self.assertIn(title, titles)


if __name__ == "__main__":
    unittest.main()
