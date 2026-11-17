"""🎤 Show my friends: a student's Free stage show plays on their pal in the Hang out."""
import unittest
from unittest.mock import patch

import pixel
import server

SHOW = ('scene("beach")\nfriend("cat")\nrain()\nsnow()\nsay("Hello!")\njump()\n'
        'note("C")\nfeel("happy")\nhearts()\nspin()')


class Perform(unittest.TestCase):
    def setUp(self):
        self.saved = server.pixel_room, server.players, server.pixel_class, server.pixel_feed
        server.pixel_room = dict(server.room_empty(), open=True, words=False)
        server.players = {}
        server.pixel_class = {"open": 3}
        server.pixel_feed = []
        self.clock = 1000.
        for p in (patch.object(server.time, "time", side_effect=lambda: self.clock),
                  patch.object(server.time, "strftime", side_effect=lambda fmt, t=None: "2026-11-16"),
                  patch.object(server, "pixel_save_soon")):
            p.start()
            self.addCleanup(p.stop)
        self.addCleanup(self.restore)

    def restore(self):
        server.pixel_room, server.players, server.pixel_class, server.pixel_feed = self.saved

    def kid(self, name="Mia", free=True):
        p = {"id": "private-" + name, "name": name}
        server.players[p["id"]] = p
        entry = server.pixel_entry(p)
        entry["solved"].update({k: [True] * 3 for k in ("a1", "a2", "a3")})
        if free:
            entry["solved"].update({k: [True] * 3
                                    for k in pixel.LEVEL_ORDER[:pixel.LEVEL_ORDER.index(pixel.FREE_AFTER) + 1]})
        self.assertTrue(server.room_do(p, {"what": "join"})["ok"])
        return p

    def enter(self, p, code):
        server.pixel_entry(p)["free_code"] = code

    def perform(self, p, **more):
        return server.room_do(p, dict(what="perform", **more))

    def event(self):
        return [e for e in server.pixel_room["events"] if e["kind"] == "mymove"][-1]

    def advance(self, seconds):
        self.clock += seconds
        for spot in server.pixel_room["here"].values():
            spot["seen"] = self.clock

    def test_a_show_keeps_only_what_the_hang_out_can_show(self):
        mia = self.kid()
        self.enter(mia, SHOW)
        out = self.perform(mia)
        self.assertTrue(out["ok"])
        show = self.event()
        self.assertTrue(show["perform"])
        self.assertEqual(show["by"], "Mia")
        self.assertEqual([s["do"] for s in show["steps"]],
                         ["say", "jump", "note", "feel", "hearts", "spin"])
        self.assertEqual(show["steps"][0]["text"], "Hello!")
        for stage_only in ("scene", "friend", "rain", "snow"):
            self.assertFalse(any(s["do"] == stage_only for s in show["steps"]), stage_only)

    def test_a_long_show_is_capped(self):
        mia = self.kid()
        self.enter(mia, "for i in range(60):\n    dance()")
        out = self.perform(mia)
        self.assertTrue(out["ok"])
        show = self.event()
        self.assertLessEqual(len(show["steps"]), pixel.MOVE_MAX)
        self.assertLessEqual(sum(s["ms"] for s in show["steps"]), pixel.PERFORM_MS)
        self.assertEqual(show["ms"], sum(s["ms"] for s in show["steps"]))
        self.assertLess(len(show["steps"]), 60)       # the show really is cut short

    def test_one_at_a_time_and_a_cooldown(self):
        mia = self.kid()
        self.enter(mia, "jump()")
        self.assertTrue(self.perform(mia)["ok"])
        self.assertIn("One show at a time", self.perform(mia)["error"])
        self.advance(5)
        waiting = self.perform(mia)["error"]
        self.assertIn("One show at a time", waiting)
        self.assertIn("seconds", waiting)
        self.advance(30)
        self.assertTrue(self.perform(mia)["ok"])

    def test_a_broken_show_says_to_fix_it_on_the_free_stage(self):
        mia = self.kid()
        self.enter(mia, "jmp()")
        out = self.perform(mia)
        self.assertIn("jmp", out["error"])
        self.assertIn("Fix it on the 🎬 Free stage first", out["error"])
        self.assertEqual(out["line"], 1)
        self.assertFalse(any(e["kind"] == "mymove" for e in server.pixel_room["events"]))
        self.assertNotIn("showtime", server.pixel_entry(mia)["badges"])

    def test_words_follow_the_my_move_rule(self):
        mia = self.kid()
        self.enter(mia, 'say("Not on the list")\njump()')
        self.assertTrue(self.perform(mia)["ok"])
        self.assertEqual([s["do"] for s in self.event()["steps"]], ["jump"])
        server.pixel_room["words"] = True              # the teacher let them type their own words
        self.advance(31)
        self.assertTrue(self.perform(mia)["ok"])
        self.assertEqual([s["do"] for s in self.event()["steps"]], ["say", "jump"])
        self.assertEqual(self.event()["steps"][0]["text"], "Not on the list")

    def test_a_saved_show_can_be_performed(self):
        mia = self.kid()
        self.enter(mia, "")
        server.pixel_entry(mia)["free_shows"] = ['say("Hello!")', "spin()"]
        self.assertTrue(self.perform(mia)["ok"])
        self.assertEqual([s["do"] for s in self.event()["steps"]], ["say"])
        self.advance(31)
        self.assertTrue(self.perform(mia, show=1)["ok"])
        self.assertEqual([s["do"] for s in self.event()["steps"]], ["spin"])
        self.assertEqual(self.perform(mia, show=9)["error"], "That show isn't there. Open the 🎬 Free stage and pick one.")

    def test_the_showtime_badge_comes_once(self):
        mia = self.kid()
        self.enter(mia, "jump()")
        first = self.perform(mia)
        self.assertEqual([b["name"] for b in first["badges"]], ["Showtime"])
        self.advance(31)
        self.assertEqual(self.perform(mia)["badges"], [])
        self.assertEqual(server.pixel_entry(mia)["badges"].count("showtime"), 1)

    def test_a_student_without_the_free_stage_gets_a_plain_message(self):
        mia = self.kid(free=False)
        self.enter(mia, "jump()")
        out = self.perform(mia)
        self.assertIn("Free stage", out["error"])
        self.assertNotIn("Traceback", out["error"])
        self.assertFalse(any(e["kind"] == "mymove" for e in server.pixel_room["events"]))

    def test_no_show_yet_gets_a_plain_message(self):
        mia = self.kid()
        self.enter(mia, "")
        out = self.perform(mia)
        self.assertIn("no show", out["error"])
        self.assertIn("Free stage", out["error"])


if __name__ == "__main__":
    unittest.main()
