"""Wording review: facts, short sentences and next steps in the four new chapters."""
import os
import re
import unittest

import pixel

NEW_KEYS = [lv["key"] for lv in pixel.LEVELS if lv["key"][0] in "nupgd"]
# A missing message has to name something a child can do next.
ACTIONS = ("type", "add", "put", "push", "try", "use", "change", "check",
           "say", "sing", "play", "start", "give", "make", "move", "keep",
           "write", "count")


def sentences(text):
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if s.strip()]


class EveryMissingMessage(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.empty = pixel.perform("")["report"]

    def messages(self):
        for key in NEW_KEYS:
            for goal, check, miss in pixel.LEVEL_BY_KEY[key]["goals"]:
                if miss is not None:
                    yield key, goal, miss(self.empty) if callable(miss) else miss

    def test_it_says_what_to_do_next(self):
        for key, goal, text in self.messages():
            with self.subTest(level=key, goal=goal):
                self.assertTrue(any(word in text.lower() for word in ACTIONS),
                                f"{key} {goal}: {text}")

    def test_it_is_three_short_sentences_or_less(self):
        for key, goal, text in self.messages():
            with self.subTest(level=key, goal=goal):
                lines = sentences(text)
                self.assertLessEqual(len(lines), 3, text)
                self.assertLessEqual(max(len(line.split()) for line in lines), 20, text)


class TheNewTextIsShort(unittest.TestCase):
    def test_pip_and_job_use_short_sentences(self):
        for key in NEW_KEYS:
            lv = pixel.LEVEL_BY_KEY[key]
            for label in ("pip", "job"):
                for line in sentences(lv[label]):
                    with self.subTest(level=key, label=label, line=line):
                        self.assertLessEqual(len(line.split()), 16, line)


class FixHintsPointAtTheLine(unittest.TestCase):
    def test_no_fix_hint_contains_the_corrected_line(self):
        for key in NEW_KEYS:
            lv = pixel.LEVEL_BY_KEY[key]
            bug_lines = lv["fix"][1].splitlines()
            fixed = [line for line in lv["reference"].splitlines() if line not in bug_lines]
            for line in fixed:
                with self.subTest(level=key, line=line):
                    self.assertNotIn(line, lv["fix"][3])


class TurnHintsLeaveTheNumberToFind(unittest.TestCase):
    def test_a_count_change_does_not_give_the_new_number(self):
        for key, number in (("n2", "5"), ("n3", "4"), ("u3", "5")):
            with self.subTest(level=key):
                self.assertNotIn(number, pixel.REMIXES[key][2])


class TheFactsInTheNewText(unittest.TestCase):
    def test_the_times_table_fix_names_the_fact_it_really_stops_at(self):
        lv = pixel.LEVEL_BY_KEY["n2"]
        said = pixel.perform(lv["fix"][1])["report"].said
        self.assertEqual(said[-1], "3 x 2 = 6")
        self.assertIn("3 x 2", lv["fix"][0])
        self.assertNotIn("2 x 3", lv["fix"][0])

    def test_the_double_fix_story_matches_what_say_does(self):
        lv = pixel.LEVEL_BY_KEY["g1"]
        said = pixel.perform(lv["fix"][1])["report"].said
        self.assertIn("nothing", said)
        self.assertIn("nothing", lv["fix"][0])

    def test_the_first_letter_is_said_twice_and_both_places_say_so(self):
        r = pixel.perform(pixel.LEVEL_BY_KEY["p3"]["reference"])["report"]
        self.assertEqual(r.said, ["L", "L", "u", "n", "a"])
        coach = pixel.LEVEL_BY_KEY["p3"]["coach"][3][1]
        self.assertIn("twice", coach)
        path = os.path.join(os.path.dirname(__file__), "PIXEL_PALS_GUIDE.md")
        with open(path) as guide:
            self.assertIn("first letter L is said twice", guide.read())


if __name__ == "__main__":
    unittest.main()
