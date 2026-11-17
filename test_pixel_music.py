"""🎵 note(): a pal sings a small tune on the Free stage or as coded furniture."""
import unittest

import pixel

LAMP = {"key": "lamp1", "title": "Lamp", "size": 16, "speed": 6, "palette": ["#000000", "#ffd93b"],
        "frames": ["0" + "." * 255, "1" + "." * 255], "names": ["", ""]}


def notes(out):
    return [(s["name"], s["beats"]) for s in out["steps"] if s["do"] == "note"]


class Notes(unittest.TestCase):
    def run_free(self, code):
        return pixel.perform(code, commands=pixel.free_commands("m1"))

    def test_notes_come_out_with_their_lengths(self):
        out = self.run_free('note("C")\nnote("E", 2)\nnote("rest")\nnote("C2")')
        self.assertIsNone(out["error"])
        self.assertEqual(notes(out), [("C", 1), ("E", 2), ("rest", 1), ("C2", 1)])

    def test_a_small_letter_is_still_the_same_note(self):
        self.assertEqual(notes(self.run_free('note("c", 3)')), [("C", 3)])

    def test_bad_notes_say_which_ones_to_pick(self):
        for code in ('note("H")', "note()", 'note("do")', 'note(3)'):
            with self.subTest(code=code):
                error = self.run_free(code)["error"]
                self.assertIn('Pick a note, like  note("C")', error)
                for name in pixel.NOTES:
                    self.assertIn(f'"{name}"', error)

    def test_a_note_without_quotes_gets_the_words_need_quotes_error(self):
        error = self.run_free("note(C)")["error"]
        self.assertIn('Words need quotes round them', error)
        self.assertIn('note("C")', error)

    def test_the_length_is_a_whole_number_of_beats(self):
        for length in (0, 9, "2", True):
            with self.subTest(length=length):
                self.assertIn("1 to 8 beats", self.run_free(f'note("C", {length!r})')["error"])
        self.assertIn("whole numbers", self.run_free('note("C", 2.5)')["error"])

    def test_a_for_loop_over_a_list_sings_in_order(self):
        out = self.run_free('tune = ["C", "D", "E", "C2"]\nfor n in tune:\n    note(n, 2)')
        self.assertIsNone(out["error"])
        self.assertEqual(notes(out), [("C", 2), ("D", 2), ("E", 2), ("C2", 2)])

    def test_it_is_a_free_stage_toy(self):
        self.assertIn("note", pixel.STAGE_TOYS)
        self.assertIn("note", pixel.FREE["adds"])
        self.assertIn("note", pixel.free_commands("m1"))
        self.assertIsNone(self.run_free('note("C")')["error"])

    def test_the_free_stage_has_a_twinkle_idea(self):
        _title, code = [idea for idea in pixel.FREE_IDEAS if idea[0] == "Sing Twinkle Twinkle"][0]
        self.assertIn("for n in tune:", code)
        out = pixel.perform(code, commands=pixel.free_commands("t1"), setup=pixel.free_setup(27))
        self.assertIsNone(out["error"])
        self.assertEqual([n for n, _ in notes(out)],
                         ["C", "C", "G", "G", "A", "A", "G", "F", "F", "E", "E", "D", "D", "C"])


class CodedThings(unittest.TestCase):
    def test_a_coded_thing_can_play_a_jingle(self):
        self.assertIn("note", pixel.THING_COMMANDS)
        out = pixel.run_thing('def on_click():\n    note("C")\n    note("E", 2)\n', LAMP, 1)
        self.assertIsNone(out["error"])
        steps, _ = pixel.thing_steps(out["steps"], 2, False)
        self.assertEqual([(s["do"], s["name"], s["beats"], s["ms"]) for s in steps if s["do"] == "note"],
                         [("note", "C", 1, pixel.NOTE_MS), ("note", "E", 2, 2 * pixel.NOTE_MS)])

    def test_a_bad_note_in_a_thing_says_which_ones_to_pick(self):
        out = pixel.run_thing('def on_click():\n    note("H")\n', LAMP, 1)
        self.assertIn('Pick a note, like  note("C")', out["error"])
        self.assertEqual(out["line"], 2)


if __name__ == "__main__":
    unittest.main()
