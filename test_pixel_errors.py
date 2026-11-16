"""Beginner mistakes get a message that says what to type, in that line's own words."""
import unittest

import pixel


def error(code):
    return pixel.public(pixel.perform(code)).get("error") or ""


class MistakesSayWhatToType(unittest.TestCase):
    def test_a_word_without_quotes_in_a_command_names_that_command(self):
        self.assertIn('feel("happy")', error("feel(happy)"))
        self.assertIn('look("left")', error("look(left)"))

    def test_a_word_in_a_walking_command_asks_for_a_number(self):
        self.assertIn("needs a number", error("right(five)"))
        self.assertIn("right(3)", error("right(five)"))

    def test_say_still_offers_both_quotes_and_a_variable(self):
        e = error("say(hello)")
        self.assertIn('say("hello")', e)
        self.assertIn("hello = 3", e)

    def test_a_word_without_quotes_in_a_variable_keeps_the_variable(self):
        self.assertIn('name = "Luna"', error("name = Luna\nsay(name)"))

    def test_capitals_in_a_name(self):
        e = error('name = "Luna"\nsay("I am " + Name)')
        self.assertIn("Capital letters matter", e)
        self.assertIn("name", e)

    def test_words_and_a_name_with_no_plus(self):
        self.assertIn("+", error('name = "Luna"\nsay("I am " name)'))

    def test_using_a_def_before_it_is_made(self):
        e = error("boogie()\ndef boogie():\n    jump()")
        self.assertIn("further down", e)
        self.assertIn("def boogie():", e)

    def test_a_command_nobody_made_still_offers_def(self):
        self.assertIn("def zoom():", error("zoom()"))

    def test_two_equals_on_a_line_of_its_own_means_one(self):
        e = error('name == "Luna"\nsay(name)')
        self.assertIn('name = "Luna"', e)
        self.assertIn("one  =", e)

    def test_the_name_on_the_wrong_side(self):
        e = error('"Luna" = name')
        self.assertIn('name = "Luna"', e)
        self.assertNotIn("==", e)

    def test_a_for_loop_with_no_counter(self):
        self.assertIn("for i in range(5):", error("for in range(5):\n    jump()"))

    def test_a_colon_line_with_nothing_under_it(self):
        e = error("for i in range(5):")
        self.assertIn("needs a line under it", e)

    def test_a_spelling_slip_in_a_name_they_made(self):
        e = error('name = "Luna"\nsay(f"Hi {nam}")')
        self.assertIn("Did you mean  name", e)
        e = error('jumps = 3\nfor i in range(jumsp):\n    jump()')
        self.assertIn("Did you mean  jumps", e)

    def test_long_words_say_what_to_do(self):
        self.assertIn("split them into two", error('say("' + "la " * 80 + '")'))
        self.assertIn('name = "Luna"', error("name = input()"))

    def test_a_long_bubble_shows_it_was_cut(self):
        steps = pixel.public(pixel.perform('say("' + "la " * 30 + '")'))["steps"]
        said = next(s["text"] for s in steps if s["do"] == "say")
        self.assertTrue(said.endswith("…"))
        self.assertLessEqual(len(said), pixel.MAX_SAY)

    def test_list_mistakes(self):
        self.assertIn('["Ana", "Ben"]', error('for name in [Ana, Ben]:\n    say(name)'))
        self.assertIn("Add a  ]", error('for name in ["Ana", "Ben":\n    say(name)'))

    def test_a_command_used_for_a_variable_with_a_close_name(self):
        self.assertIn("Did you mean  jumps", error('jumps = 4\nsay(f"{jump} jumps!")'))

    def test_random_points_to_randint(self):
        self.assertIn("randint(1, 6)", error("roll = random(1, 6)"))

    def test_working_code_has_no_error(self):
        for lv in pixel.LEVELS:
            self.assertEqual(error(lv["reference"]), "", lv["key"])


if __name__ == "__main__":
    unittest.main()
