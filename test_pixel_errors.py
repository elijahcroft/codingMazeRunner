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

    def test_working_code_has_no_error(self):
        for lv in pixel.LEVELS:
            self.assertEqual(error(lv["reference"]), "", lv["key"])


if __name__ == "__main__":
    unittest.main()
