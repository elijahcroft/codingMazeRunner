"""🎬 On the big screen: a teacher plays one student's Free stage show on the projector."""
import unittest
from unittest.mock import patch

import pixel
import server

SHOW = ('scene("beach")\nfriend("cat")\nrain()\nsnow()\nsay("Hello!")\njump()\n'
        'note("C")\nfeel("happy")\nhearts()\nspin()')


class BigShow(unittest.TestCase):
    def setUp(self):
        self.saved = (server.pixel_room, server.players, server.pixel_class, server.pixel_feed,
                      server.pixel_bigshow)
        server.pixel_room = dict(server.room_empty(), open=True, words=False)
        server.players = {}
        server.pixel_class = {"open": 3}
        server.pixel_feed = []
        server.pixel_bigshow = {"n": 0, "show": None}
        self.clock = 1000.
        for p in (patch.object(server.time, "time", side_effect=lambda: self.clock),
                  patch.object(server.time, "strftime", side_effect=lambda fmt, t=None: "2026-11-16"),
                  patch.object(server, "pixel_save_soon"),
                  patch.object(server, "save_state")):
            p.start()
            self.addCleanup(p.stop)
        self.addCleanup(self.restore)

    def restore(self):
        (server.pixel_room, server.players, server.pixel_class, server.pixel_feed,
         server.pixel_bigshow) = self.saved

    def kid(self, name="Mia", free=True, code=""):
        p = {"id": "private-" + name, "name": name}
        server.players[p["id"]] = p
        entry = server.pixel_entry(p)
        if free:
            entry["solved"].update({k: [True] * 3
                                    for k in pixel.LEVEL_ORDER[:pixel.LEVEL_ORDER.index(pixel.FREE_AFTER) + 1]})
        entry["free_code"] = code
        return p

    def big_show(self, name="Mia", key=None):
        data = {"action": "big_show", "name": name}
        if key is not None:
            data["key"] = key
            return server.pixel_post("/pixel/teacher", data)
        return server.pixel_teacher(data)

    def event(self):
        return [e for e in server.pixel_room["events"] if e["kind"] == "bigshow"][-1]

    def test_a_show_is_posted_with_the_full_stage_steps_and_the_name(self):
        mia = self.kid(code=SHOW)
        out = self.big_show()
        self.assertTrue(out["ok"])
        self.assertEqual(out["name"], "Mia")
        show = self.event()
        self.assertEqual(show["name"], "Mia")
        self.assertEqual(show["by"], "Mia")
        self.assertEqual(show["code"], SHOW)
        self.assertEqual(show["show_id"], 1)
        self.assertEqual([s["do"] for s in show["steps"]],
                         ["scene", "friend", "rain", "snow", "say", "jump", "note", "feel", "hearts", "spin"])
        self.assertEqual(show["steps"][0]["name"], "beach")       # the projector has the full stage
        self.assertEqual(show["steps"][1]["kind"], "cat")
        self.assertEqual(show["steps"][4]["text"], "Hello!")
        self.assertTrue(all(s.get("line") for s in show["steps"]))     # for lighting up the code
        self.assertEqual(show["pal"]["frames"], [server.pixel_pal(server.pixel_entry(mia))["frames"][0]])

    def test_the_projector_can_fetch_the_show_it_missed(self):
        self.kid(code="jump()")
        self.assertTrue(self.big_show()["ok"])
        got = server.pixel_get("/pixel/bigshow", {"after": ["0"]})
        self.assertEqual(got["name"], "Mia")
        self.assertEqual(got["show_id"], 1)
        self.assertEqual(got["steps"][0]["do"], "jump")
        self.assertEqual(server.pixel_get("/pixel/bigshow", {"after": ["1"]}), {"n": 1})
        self.assertEqual(server.pixel_get("/pixel/bigshow", {"now": ["1"]}), {"n": 1})

    def test_a_kept_show_plays_when_the_one_being_made_is_empty(self):
        mia = self.kid()
        server.pixel_entry(mia)["free_shows"] = ["spin()", "jump()"]
        self.assertTrue(self.big_show()["ok"])
        self.assertEqual([s["do"] for s in self.event()["steps"]], ["spin"])

    def test_a_student_without_a_show_gets_a_plain_message(self):
        self.kid(code="")
        out = self.big_show()
        self.assertIn("no Free stage show", out["error"])
        self.assertIn("🎬 Free stage", out["error"])
        self.assertFalse(any(e["kind"] == "bigshow" for e in server.pixel_room["events"]))
        self.assertIsNone(server.pixel_bigshow["show"])

    def test_a_student_without_the_free_stage_gets_a_plain_message(self):
        self.kid(free=False, code="jump()")
        out = self.big_show()
        self.assertIn("isn't open", out["error"])
        self.assertFalse(any(e["kind"] == "bigshow" for e in server.pixel_room["events"]))

    def test_a_broken_show_says_where_to_fix_it(self):
        self.kid(code="jmp()")
        out = self.big_show()
        self.assertIn("jmp", out["error"])
        self.assertIn("fix it on the 🎬 Free stage first", out["error"])
        self.assertFalse(any(e["kind"] == "bigshow" for e in server.pixel_room["events"]))

    def test_words_follow_the_public_screen_rule(self):
        code = 'friend("cat")\nfriend_say("Not on the list")\nsay("Not on the list")\nsay("Hello!")\njump()'
        self.kid(code=code)
        self.assertTrue(self.big_show()["ok"])
        self.assertEqual([s["do"] for s in self.event()["steps"]], ["friend", "say", "jump"])
        self.assertEqual(self.event()["steps"][1]["text"], "Hello!")
        self.assertEqual(self.event()["code"], code)
        server.pixel_room["words"] = True                 # the teacher let them type their own words
        self.assertTrue(self.big_show()["ok"])
        self.assertEqual([s["do"] for s in self.event()["steps"]],
                         ["friend", "friend_say", "say", "say", "jump"])

    def test_a_new_press_replaces_the_show(self):
        self.kid(name="Mia", code="jump()")
        self.kid(name="Ben", code="spin()")
        self.assertTrue(self.big_show("Mia")["ok"])
        self.assertTrue(self.big_show("Ben")["ok"])
        self.assertEqual(self.event()["name"], "Ben")
        self.assertEqual(self.event()["show_id"], 2)
        self.assertEqual(server.pixel_bigshow["show"]["name"], "Ben")

    def test_the_teacher_needs_the_admin_key(self):
        self.kid(code="jump()")
        out = self.big_show(key="nope")
        self.assertEqual(out, {"error": "Wrong admin key."})
        self.assertFalse(any(e["kind"] == "bigshow" for e in server.pixel_room["events"]))
        out = self.big_show(key=server.ADMIN_KEY)
        self.assertTrue(out["ok"])
        self.assertEqual(self.event()["name"], "Mia")

    def test_the_teacher_page_marks_who_has_a_show(self):
        self.kid(name="Mia", code="jump()")
        self.kid(name="Ben", code="")
        self.kid(name="Alex", free=False, code="")
        rows = {r["name"]: r["free_show"] for r in server.pixel_overview()["students"]}
        self.assertEqual(rows, {"Mia": True, "Ben": False, "Alex": False})


if __name__ == "__main__":
    unittest.main()
