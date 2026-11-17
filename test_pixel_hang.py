"""The Hang out's small in-between rules, the parts a browser can get wrong.

These are the server-side halves of the Hang out fixes found with
`tools/e2e_hang.py`: a show and a My Move take turns on the same pal, and a
hide round's first message tells the class to hide (the seeker's own screen
says "You're counting..." on top of it).
"""
import unittest
from unittest.mock import patch

import pixel
import server


class Hang(unittest.TestCase):
    def setUp(self):
        self.saved = server.pixel_room, server.players, server.pixel_class, server.pixel_feed
        server.pixel_room = dict(server.room_empty(), open=True, words=False)
        server.players = {}
        server.pixel_class = {"open": len(pixel.LEVEL_ORDER) - 1}
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

    def kid(self, name):
        p = {"id": "private-" + name, "name": name}
        server.players[p["id"]] = p
        entry = server.pixel_entry(p)
        entry["solved"].update({key: [True] * 3 for key in pixel.LEVEL_ORDER[:pixel.LEVEL_ORDER.index(pixel.FREE_AFTER) + 1]})
        entry["hang_let_in"] = True
        self.assertTrue(server.room_do(p, {"what": "join"})["ok"])
        return p

    def spot(self, p):
        return server.pixel_room["here"][p["id"]]

    def test_a_show_says_to_wait_for_the_move_on_the_same_pal(self):
        mia = self.kid("Mia")
        server.pixel_entry(mia)["free_code"] = "jump()"
        self.spot(mia)["move_until"] = self.clock + 5
        out = server.room_do(mia, {"what": "perform"})
        self.assertIn("One thing at a time", out["error"])
        self.assertIn("pal to finish", out["error"])
        self.assertNotIn("your show", out["error"])      # it may be a My Move that is playing

        self.clock += 6
        self.spot(mia)["seen"] = self.clock
        self.assertTrue(server.room_do(mia, {"what": "perform"})["ok"])

    def test_a_move_says_wait_while_a_show_plays(self):
        mia = self.kid("Mia")
        server.pixel_entry(mia)["move"] = {"steps": [], "title": "My Move", "loop": False, "big": False, "actions": 0}
        self.spot(mia)["move_until"] = self.clock + 5
        self.assertEqual(server.room_do(mia, {"what": "mymove"}), {"error": "wait"})

    def test_the_hide_message_says_to_hide(self):
        mia, ben = self.kid("Mia"), self.kid("Ben")
        self.assertTrue(server.room_do(mia, {"what": "game", "action": "create", "kind": "hide"})["ok"])
        self.assertTrue(server.room_do(ben, {"what": "game", "action": "join"})["ok"])
        self.assertTrue(server.room_do(mia, {"what": "game", "action": "start"})["ok"])
        message = [e for e in server.pixel_room["events"] if e["kind"] == "game"][-1]["message"]
        self.assertEqual(message, "🙈 Hide! The seeker is counting...")
        self.assertNotEqual(message, "The seeker is counting!")     # the old, confusing message


if __name__ == "__main__":
    unittest.main()
