"""✨ The one-time "New in the Hang out!" card.

The card itself is browser-only, but the flag that makes it one-time per
student lives on their server entry so it doesn't return on another laptop.
"""
import os
import tempfile
import unittest
from unittest.mock import patch

import pixel
import server


class News(unittest.TestCase):
    def setUp(self):
        self.saved = (server.pixel_room, server.players, server.pixel_class,
                      server.pixel_feed, server.STATE_FILE)
        self.folder = tempfile.TemporaryDirectory()
        server.pixel_room = dict(server.room_empty(), open=True, words=False)
        server.players = {}
        server.pixel_class = {"open": len(pixel.LEVEL_ORDER) - 1}
        server.pixel_feed = []
        server.STATE_FILE = os.path.join(self.folder.name, "state.json")
        self.clock = 1000.
        for thing in (patch.object(server.time, "time", side_effect=lambda: self.clock),
                      patch.object(server.time, "strftime", side_effect=lambda fmt, t=None: "2026-11-16"),
                      patch.object(server, "pixel_save_soon")):
            thing.start()
            self.addCleanup(thing.stop)
        self.addCleanup(self.restore)

    def restore(self):
        (server.pixel_room, server.players, server.pixel_class,
         server.pixel_feed, server.STATE_FILE) = self.saved
        self.folder.cleanup()

    def kid(self, name):
        p = {"id": "private-" + name, "name": name}
        server.players[p["id"]] = p
        entry = server.pixel_entry(p)
        entry["hang_let_in"] = True
        self.assertTrue(server.room_do(p, {"what": "join"})["ok"])
        return p

    def test_the_card_is_pending_until_the_student_marks_it_seen(self):
        mia = self.kid("Mia")
        self.assertEqual(server.pixel_entry(mia)["news"], 0)
        self.assertEqual(server.pixel_state(mia)["news"], 0)
        self.assertEqual(server.room_view(mia, -1)["news"], 0)
        self.assertNotIn("news", server.room_view(None, -1))       # never on the projector

        self.assertTrue(server.pixel_post("/pixel/news", {"id": mia["id"]})["ok"])
        self.assertEqual(server.pixel_entry(mia)["news"], 1)
        self.assertEqual(server.pixel_state(mia)["news"], 1)
        self.assertEqual(server.room_view(mia, -1)["news"], 1)
        self.assertTrue(server.pixel_post("/pixel/news", {"id": mia["id"]})["ok"])   # once only, no error

    def test_marking_it_seen_survives_a_restart(self):
        mia = self.kid("Mia")
        self.assertTrue(server.pixel_post("/pixel/news", {"id": mia["id"]})["ok"])
        server.players = {}                    # a server restart reads the save file
        server.load_state()
        self.assertEqual(server.players[mia["id"]]["pixel"]["news"], 1)
        self.assertEqual(server.pixel_state(server.players[mia["id"]])["news"], 1)

    def test_a_student_who_never_opened_it_stays_pending(self):
        ben = self.kid("Ben")
        self.assertEqual(server.room_view(ben, -1)["news"], 0)
        self.assertTrue(server.pixel_post("/pixel/news", {"id": "nobody"})["error"] == "join")


if __name__ == "__main__":
    unittest.main()
