"""Odd student code gets a friendly answer, never a dropped connection."""
import unittest

import pixel
import test_pixel


def error(code):
    out = pixel.perform(code)
    return out["error"] or ""


class TheRunnerKeepsItsFeet(unittest.TestCase):
    def test_break_and_continue_outside_a_loop_say_where_they_go(self):
        for code, line in (("break\n", 1), ("if True:\n    continue\n", 2),
                           ("def a():\n    break\na()\n", 2)):
            with self.subTest(code=code):
                out = pixel.perform(code)
                self.assertIn("only work inside a loop", out["error"])
                self.assertIn("under a  for  or  while  loop", out["error"])
                self.assertEqual(out["line"], line)

    def test_break_and_continue_still_work_inside_a_loop(self):
        out = pixel.perform("for i in range(5):\n    if i == 2:\n        break\n    jump()")
        self.assertIsNone(out["error"])
        self.assertEqual(sum(s["do"] == "jump" for s in out["steps"]), 2)
        out = pixel.perform("for i in range(4):\n    if i == 2:\n        continue\n    jump()")
        self.assertIsNone(out["error"])
        self.assertEqual(sum(s["do"] == "jump" for s in out["steps"]), 3)

    def test_max_min_and_abs_work(self):
        out = pixel.perform('say(abs(-3))\nsay(max(2, 5, 1))\nsay(min(2, 5, 1))')
        self.assertIsNone(out["error"])
        self.assertEqual([s["text"] for s in out["steps"] if s["do"] == "say"], ["3", "5", "1"])

    def test_max_min_and_abs_say_what_they_need(self):
        self.assertIn("abs() takes one number", error("abs()"))
        self.assertIn("at least two numbers", error("max(1)"))
        self.assertIn("at least two numbers", error("min()"))

    def test_a_deep_expression_gets_a_message_not_a_traceback(self):
        out = pixel.perform("say(" + "not " * 500 + "True)")
        self.assertIsNotNone(out["error"])
        self.assertIn("stacked on one line", out["error"])
        self.assertIn("smaller lines", out["error"])

    def test_an_unreadable_character_gets_a_message(self):
        out = pixel.perform("say('" + chr(0xD800) + "')\n")
        self.assertIsNotNone(out["error"])
        self.assertIn("can't be read here", out["error"])
        self.assertIn("Delete the odd character", out["error"])

    def test_a_list_of_numbers_does_not_crash_a_word_list_mission(self):
        out = pixel.run_level(pixel.LEVEL_BY_KEY["j3"],
                              "names = [1, 2, 3]\nfor name in names:\n    say(name)\n", pixel.PIP)
        self.assertIsNone(out["error"])
        self.assertEqual(len(out["stars"]), 3)


class MessagesSayWhatToDo(unittest.TestCase):
    def test_an_f_string_with_a_missing_brace(self):
        e = error('name = "Luna"\nsay(f"Hi {name")')
        self.assertIn("f-string needs a  }", e)
        self.assertIn('f"Hi {name}"', e)

    def test_an_f_string_with_an_extra_brace(self):
        e = error('name = "Luna"\nsay(f"Hi {name}}")')
        self.assertIn("extra  }", e)

    def test_an_f_string_with_nothing_in_the_braces(self):
        e = error('say(f"{}")')
        self.assertIn("curly brackets", e)

    def test_a_line_that_stops_after_an_equals_sign(self):
        e = error("name =")
        self.assertIn("After the  =  put what to keep", e)
        self.assertIn('name = "Luna"', e)

    def test_a_line_that_stops_after_a_plus_sign(self):
        e = error('say("a" + )')
        self.assertIn("Something is missing after the sign", e)
        self.assertIn('say("Hi " + name)', e)

    def test_print_without_brackets_points_at_say(self):
        e = error('print "hi"')
        self.assertIn('say("Hello")', e)
        self.assertNotIn('print("hi")', e)

    def test_open_says_files_are_not_part_of_the_stage(self):
        e = error('open("x")')
        self.assertIn("don't need open()", e)
        self.assertIn('say("Hello")', e)


class HuntOverHttp(unittest.TestCase):
    setUp, tearDown, post, get = (test_pixel.StudioOverHttp.setUp, test_pixel.StudioOverHttp.tearDown,
                                  test_pixel.StudioOverHttp.post, test_pixel.StudioOverHttp.get)

    def test_odd_code_gets_an_answer_instead_of_a_dropped_connection(self):
        me = self.post("/join", {"name": "Mia"})["id"]
        codes = ("break\n", "say(" + "not " * 500 + "True)\n", "say('" + chr(0xD800) + "')\n")
        for code in codes:
            with self.subTest(code=code):
                out = self.post("/pixel/run", {"id": me, "level": "a1", "code": code})
                self.assertTrue(out["error"])
        out = self.post("/pixel/poke", {"id": me, "level": "a1", "code": "break\n", "events": ["click"]})
        self.assertTrue(out["error"])


if __name__ == "__main__":
    unittest.main()
