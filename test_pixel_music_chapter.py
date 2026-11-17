"""Make Music: the chapter where note() sings a tune, kept in a list and played with a def."""
import unittest

import pixel
import server
from test_pixel import StudioOverHttp, drawing


def run(key, code=None):
    lv = pixel.LEVEL_BY_KEY[key]
    return pixel.run_level(lv, lv["reference"] if code is None else code, pixel.PIP)


def report(code):
    return pixel.perform(code)["report"]


def notes(code):
    return [n for n, _ in pixel._notes(report(code))]


class TheChapter(unittest.TestCase):
    def test_it_comes_last_and_has_three_missions(self):
        self.assertEqual(pixel.CHAPTERS[-1], {"key": "u", "name": "Make Music", "icon": "🎵"})
        self.assertEqual([lv["key"] for lv in pixel.LEVELS[-3:]], ["u1", "u2", "u3"])
        self.assertEqual({lv["chapter"] for lv in pixel.LEVELS[-3:]}, {len(pixel.CHAPTERS) - 1})

    def test_the_first_mission_opens_note(self):
        self.assertEqual(pixel.LEVEL_BY_KEY["u1"]["adds"], ["note"])
        self.assertIn("note", pixel.commands_for("u1"))
        self.assertNotIn("note", pixel.commands_for("n3"))

    def test_each_reference_earns_all_three_stars(self):
        for key in ("u1", "u2", "u3"):
            with self.subTest(level=key):
                out = run(key)
                self.assertIsNone(out["error"])
                self.assertEqual(out["stars"], [True, True, True], out["reply"])

    def test_the_three_new_box_gifts_are_wearable(self):
        for key in ("notehat", "pianohat", "notespark"):
            with self.subTest(gift=key):
                self.assertIn(key, pixel.BOX_GIFTS)
                self.assertIn(pixel.GIFTS[key]["slot"], pixel.WEAR_SLOTS)


class TheMusic(unittest.TestCase):
    def test_first_notes_sings_c_d_e_then_cheers(self):
        r = report(pixel.LEVEL_BY_KEY["u1"]["reference"])
        self.assertEqual([n for n, _ in pixel._notes(r)], ["C", "D", "E"])
        self.assertEqual(r.log[-1][0], "cheer")

    def test_twinkle_is_a_list_sung_by_a_for_loop(self):
        r = report(pixel.LEVEL_BY_KEY["u2"]["reference"])
        self.assertEqual([n for n, _ in pixel._notes(r)], ["C", "C", "G", "G", "A", "A", "G"])
        self.assertEqual(pixel._notes(r)[-1], ("G", 2))
        self.assertTrue(any(isinstance(r.values.get(name), list) for name in r.loops_over))

    def test_make_a_beat_uses_a_def_three_times(self):
        r = report(pixel.LEVEL_BY_KEY["u3"]["reference"])
        self.assertEqual(r.defs, ["beat"])
        self.assertEqual(sum(r.own_calls.values()), 3)
        self.assertEqual([n for n, _ in pixel._notes(r)], ["C", "rest", "G"] * 3 + ["C"])
        self.assertEqual(pixel._notes(r)[-1], ("C", 2))

    def test_a_note_is_read_with_its_beats(self):
        self.assertEqual(notes('note("E", 2)\nnote("rest")'), ["E", "rest"])
        self.assertEqual(pixel._notes(report('note("E", 2)'))[0], ("E", 2))


class TheNewFixIts(unittest.TestCase):
    def test_each_bug_misses_the_notes_and_the_guide_fixes_it(self):
        for key in ("u1", "u2", "u3"):
            with self.subTest(level=key):
                self.assertFalse(run(key, pixel.FIXES[key][1])["fix"])
                self.assertTrue(run(key)["fix"])

    def test_the_first_two_bugs_run_but_get_the_tune_wrong(self):
        for key in ("u1", "u2"):
            with self.subTest(level=key):
                bad = run(key, pixel.FIXES[key][1])
                self.assertIsNone(bad["error"])
                self.assertFalse(bad["fix"])

    def test_the_beat_bug_stops_with_a_line(self):
        bad = run("u3", pixel.FIXES["u3"][1])
        self.assertTrue(bad["error"].startswith("Line "), bad["error"])


class MusicOverHttp(unittest.TestCase):
    setUp, tearDown, post, get = StudioOverHttp.setUp, StudioOverHttp.tearDown, StudioOverHttp.post, StudioOverHttp.get

    def test_the_new_missions_play_through_the_server(self):
        me = self.post("/join", {"name": "Mia"})["id"]
        self.post("/pixel/save", {"id": me, "drawing": drawing()})
        server.pixel_entry(server.players[me])["solved"].update(
            {key: [True] * 3 for key in pixel.LEVEL_ORDER[:pixel.LEVEL_ORDER.index("u1")]})
        for key in ("u1", "u2", "u3"):
            with self.subTest(level=key):
                out = self.post("/pixel/run", {"id": me, "level": key,
                                               "code": pixel.LEVEL_BY_KEY[key]["reference"]})
                self.assertEqual(out["stars"], [True, True, True], out.get("reply"))
                self.assertEqual(out["rewards"]["gained"], 3)
        state = self.get(f"/pixel/state?id={me}")
        self.assertEqual(state["chapters"][-1]["name"], "Make Music")
        self.assertEqual(len(state["chapters"][-1]["levels"]), 3)


if __name__ == "__main__":
    unittest.main()
