"""🌊 Under the sea: the last class party reward, its bubble helmet and place lists."""
import os
import unittest
from unittest.mock import patch

import pixel
import server

HERE = os.path.dirname(os.path.abspath(__file__))


def source(name):
    with open(os.path.join(HERE, name), encoding="utf-8") as f:
        return f.read()


class Rewards(unittest.TestCase):
    def test_the_last_two_rewards_are_a_class_gift_then_the_sea(self):
        gift, place = pixel.HANG_REWARDS[-2:]
        self.assertEqual(gift["kind"], "gift")
        self.assertEqual(gift["key"], "bubblehelmet")
        self.assertTrue(pixel.GIFTS[gift["key"]].get("class"))
        self.assertEqual(pixel.GIFTS[gift["key"]]["slot"], "hat")
        self.assertEqual(place, {"kind": "place", "key": "sea", "name": "Under the sea"})
        self.assertEqual(pixel.HANG_WORLD[-1], "sea")
        self.assertEqual(pixel.HANG_REWARDS[-1]["name"], "Under the sea")

    def test_the_bubble_helmet_has_hat_art_and_the_sea_has_a_bubbles_toy(self):
        self.assertIn("bubblehelmet:", source("pixel_stage.js"))
        self.assertIn("bubbles:", source("pixel_stage.js"))
        self.assertIn("bubbles", pixel.HANG_TOYS)
        self.assertIn("bubbleVent", source("pixel_hangout.js"))


class SeaLists(unittest.TestCase):
    def test_every_per_place_list_includes_the_sea(self):
        self.assertIn("sea", pixel.HANG_WORLD)
        self.assertIn("sea", pixel.CHEST_SPOTS)
        self.assertIn("sea", pixel.CHEST_TIER)
        self.assertEqual(pixel.CHEST_TIER["sea"], max(pixel.CHEST_TIER.values()))
        self.assertIn("sea", server.PLACE_WORDS)
        self.assertEqual([key for key in pixel.HANG_FINDS if key.startswith("sea")], ["sea0", "sea1", "sea2"])
        self.assertEqual(sum(1 for key in pixel.HANG_FINDS if key.startswith("sea")), 3)

    def test_every_place_label_and_scene_in_the_pages_has_the_sea(self):
        hangout = source("pixel_hangout.js")
        self.assertIn('sea: "Under the sea"', hangout)                 # PLACE_LABEL
        self.assertIn("    sea(g) {", hangout)                          # the scene art
        self.assertIn("sea: [[112, .55], [232, .75]]", hangout)         # SEATS
        self.assertIn("sea: [[160, .12, 34, \"bubbles\"]", hangout)     # TOYS
        self.assertIn("sea: [[70, .78], [196, .55], [304, .92]]", hangout)     # GEMS
        self.assertIn('sea: ["🌊", "Under the sea"]', source("pixel_room.js"))
        self.assertIn('sea: "🌊 Under the sea"', source("pixel_show.html"))
        self.assertIn('sea: "🌊 Under the sea"', source("pixel_teacher.html"))
        self.assertIn('[data-place="sea"]', source("pixel.html"))


class Sea(unittest.TestCase):
    def setUp(self):
        self.saved = server.pixel_room, server.players, server.pixel_class, server.pixel_feed
        server.pixel_room = dict(server.room_empty(), open=True, words=False)
        server.players = {}
        server.pixel_class = {"open": 3}
        server.pixel_feed = []
        self.clock = 1000.
        self.day = "2026-11-16"
        for p in (patch.object(server.time, "time", side_effect=lambda: self.clock),
                  patch.object(server.time, "strftime", side_effect=lambda fmt, t=None: self.day),
                  patch.object(server, "pixel_save_soon")):
            p.start()
            self.addCleanup(p.stop)
        self.addCleanup(self.restore)
        self.mia = self.kid("Mia")

    def restore(self):
        server.pixel_room, server.players, server.pixel_class, server.pixel_feed = self.saved

    def kid(self, name):
        p = {"id": "private-" + name, "name": name}
        server.players[p["id"]] = p
        server.pixel_entry(p)["solved"].update({k: [True] * 3 for k in ("a1", "a2", "a3")})
        self.assertTrue(server.room_do(p, {"what": "join"})["ok"])
        return p

    def fill_to(self, level):
        with server.lock:
            while server.hang_meter()["level"] < level:
                server.hang_fill(pixel.party_goal(server.hang_meter()["level"]))

    def test_the_sea_unlocks_after_the_bubble_helmet_gift(self):
        self.fill_to(6)
        self.assertEqual(server.hang_meter()["level"], 6)
        self.assertIn("bubblehelmet", server.pixel_owned(server.pixel_entry(self.mia)))
        self.assertNotIn("sea", server.hang_places())
        self.assertEqual(server.room_do(self.mia, {"what": "go", "name": "sea"})["error"], "bad")
        self.fill_to(7)
        self.assertIn("sea", server.hang_places())
        self.assertTrue(server.room_do(self.mia, {"what": "go", "name": "sea"})["ok"])

    def test_gems_can_be_found_in_the_sea(self):
        self.fill_to(7)
        self.assertTrue(server.room_do(self.mia, {"what": "go", "name": "sea"})["ok"])
        out = server.room_do(self.mia, {"what": "find", "key": "sea0"})
        self.assertEqual(out["found"], 1)
        self.assertIn("sea0", server.pixel_entry(self.mia)["found"])

    def test_the_sea_chest_opens_with_its_code(self):
        self.fill_to(7)
        self.assertTrue(server.room_do(self.mia, {"what": "go", "name": "sea"})["ok"])
        self.clock += server.CODE_RUN_GAP + .01
        job = pixel.chest_job("sea", self.day)
        out = server.room_do(self.mia, {"what": "chest", "place": "sea", "code": job["answer"]})
        self.assertTrue(out["open"], out)
        self.assertEqual(out["coins"], pixel.CHEST_COINS)

    def test_the_bubbles_toy_is_a_sea_toy(self):
        self.fill_to(7)
        self.assertTrue(server.room_do(self.mia, {"what": "go", "name": "sea"})["ok"])
        self.assertTrue(server.room_do(self.mia, {"what": "toy", "name": "bubbles", "x": 160, "y": .12})["ok"])


if __name__ == "__main__":
    unittest.main()
