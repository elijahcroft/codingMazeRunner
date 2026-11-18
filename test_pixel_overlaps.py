"""Moments in the Hang out that must not break each other.

Tonight's class-wide moments were each tested on their own. These are the few
server rules where two of them meet: the teacher's 📸 Class photo while a
wedding is playing. The photo lines everyone up in the Park, which would walk
the couple out of the Wedding garden and silently cancel their wedding, so the
teacher is told to take the photo afterwards instead.
"""
import unittest
from unittest.mock import patch

import pixel
import server


class OverlapBase(unittest.TestCase):
    def setUp(self):
        self.saved = server.pixel_room, server.players, server.pixel_class, server.pixel_feed
        server.pixel_room = dict(server.room_empty(), open=True, words=False)
        server.players = {}
        server.pixel_class = {"open": len(pixel.LEVEL_ORDER) - 1}
        server.pixel_feed = []
        self.clock = 1000.
        self.time = patch.object(server.time, "time", side_effect=lambda: self.clock)
        self.save = patch.object(server, "pixel_save_soon")
        self.time.start()
        self.save.start()
        self.addCleanup(self.time.stop)
        self.addCleanup(self.save.stop)
        self.addCleanup(self.restore)

    def restore(self):
        server.pixel_room, server.players, server.pixel_class, server.pixel_feed = self.saved

    def kid(self, name):
        p = {"id": "private-" + name, "name": name}
        server.players[p["id"]] = p
        server.pixel_entry(p)["hang_let_in"] = True
        self.assertTrue(server.room_do(p, {"what": "join"})["ok"])
        return p

    def do(self, p, what, **more):
        return server.room_do(p, dict(what=what, **more))

    def seat(self, p):
        return server.pixel_room["here"][p["id"]]["seat"]

    def wedding(self, host, partner):
        self.assertTrue(self.do(host, "go", name="wedding")["ok"])
        self.assertTrue(self.do(partner, "go", name="wedding")["ok"])
        self.assertTrue(self.do(host, "wedding")["ok"])
        self.assertTrue(self.do(host, "wedding_pick", seat=self.seat(partner))["ok"])
        self.assertTrue(self.do(partner, "wedding_yes")["ok"])
        self.assertEqual(server.pixel_room["wedding"]["phase"], "ceremony")

    def photos(self):
        return [e for e in server.pixel_room["events"] if e["kind"] == "photo"]


class ClassPhotoDuringWedding(OverlapBase):
    def test_the_teacher_photo_waits_for_the_wedding(self):
        ana, ben = self.kid("Ana"), self.kid("Ben")
        self.wedding(ana, ben)
        spots = [server.pixel_room["here"][p["id"]] for p in (ana, ben)]
        before = [(s["x"], s["y"]) for s in spots]
        out = server.pixel_teacher({"action": "photo"})
        self.assertIn("wedding", out.get("error", "").lower())
        self.assertEqual(server.pixel_room["wedding"]["phase"], "ceremony")
        self.assertEqual([(s["x"], s["y"]) for s in spots], before)   # nobody walked to the Park
        self.assertEqual(self.photos(), [])

    def test_a_photo_still_works_without_a_wedding(self):
        self.kid("Ana")
        self.kid("Ben")
        self.assertEqual(server.pixel_teacher({"action": "photo"}), {"ok": True})
        photo = self.photos()[-1]
        self.assertEqual(photo["count"], 2)
        self.assertNotIn("style", photo)


if __name__ == "__main__":
    unittest.main()
