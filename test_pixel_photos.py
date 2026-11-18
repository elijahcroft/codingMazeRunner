"""📸 Photo keepsakes for the class projector.

After the class photo, the projector can keep two more moments: the garden at a
wedding's "are married!" moment, and the runway when a fashion show shows its
results. The server marks each moment with a photo event that carries the caption
to draw into the PNG (with hidden names already hidden), so the projector has one
small, testable job.
"""
import unittest
from unittest.mock import patch

import pixel
import server


class PhotoBase(unittest.TestCase):
    def setUp(self):
        self.saved = server.pixel_room, server.players, server.pixel_class, server.pixel_feed
        server.pixel_room = dict(server.room_empty(), open=True, words=False)
        server.players = {}
        server.pixel_class = {"open": len(pixel.LEVEL_ORDER) - 1}
        server.pixel_feed = []
        self.clock = 1000.
        self.photo_day = patch.object(server, "photo_day", return_value="18 Nov 2026")
        self.time = patch.object(server.time, "time", side_effect=lambda: self.clock)
        self.save = patch.object(server, "pixel_save_soon")
        self.photo_day.start()
        self.time.start()
        self.save.start()
        self.addCleanup(self.photo_day.stop)
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

    def advance(self, seconds=1, step=.5):
        left = seconds
        while left > 0:
            bit = min(step, left)
            self.clock += bit
            left -= bit
            for spot in server.pixel_room["here"].values():
                spot["seen"] = self.clock
            server.room_keep_up()

    def photos(self):
        return [e for e in server.pixel_room["events"] if e["kind"] == "photo"]


class WeddingPhoto(PhotoBase):
    def begin(self, host, partner):
        self.assertTrue(self.do(host, "go", name="wedding")["ok"])
        self.assertTrue(self.do(partner, "go", name="wedding")["ok"])
        out = self.do(host, "wedding")
        self.assertTrue(out["ok"], out)
        self.assertTrue(self.do(host, "wedding_pick", seat=self.seat(partner))["ok"])
        self.assertTrue(self.do(partner, "wedding_yes")["ok"])
        self.assertEqual(server.pixel_room["wedding"]["phase"], "ceremony")

    def test_a_married_moment_offers_a_captioned_garden_photo(self):
        ana, ben, cy = self.kid("Ana"), self.kid("Ben"), self.kid("Cy")
        self.begin(ana, ben)
        self.assertEqual(self.photos(), [])                  # not during the ceremony
        self.advance(server.WEDDING_SECONDS)
        self.assertEqual(server.pixel_room["wedding"], None)
        photos = self.photos()
        self.assertEqual(len(photos), 1, photos)
        photo = photos[0]
        self.assertEqual(photo["style"], "wedding")
        self.assertEqual(photo["caption"], "💒 Ana & Ben · 18 Nov 2026")
        self.assertEqual(photo["seconds"], server.PHOTO_SHOW_SECONDS)
        self.assertEqual(photo["loc"], 0)
        span = server.wedding_span()
        self.assertEqual(photo["x"], span[0] + pixel.PLACE_W // 2)
        self.assertEqual((photo["host_name"], photo["partner_name"]), ("Ana", "Ben"))
        # The couple's own event still says the happy news, as it did before.
        done = [e for e in server.pixel_room["events"] if e["kind"] == "wedding"][-1]
        self.assertEqual(done["phase"], "done")
        self.assertEqual(done["host_name"], "Ana")

    def test_a_hidden_name_stays_hidden_in_the_wedding_photo(self):
        ana, ben = self.kid("Ana"), self.kid("Ben")
        self.assertTrue(self.do(ana, "hidename", on=True)["ok"])
        self.begin(ana, ben)
        self.advance(server.WEDDING_SECONDS)
        photo = self.photos()[-1]
        self.assertEqual(photo["caption"], "💒 Secret pal & Ben · 18 Nov 2026")
        self.assertNotIn("Ana", photo["caption"])

    def test_a_cancelled_wedding_offers_no_photo(self):
        ana, ben = self.kid("Ana"), self.kid("Ben")
        self.begin(ana, ben)
        self.advance(2)
        self.assertTrue(self.do(ben, "leave")["ok"])
        server.room_keep_up()
        self.assertEqual(self.photos(), [])


class FashionPhoto(PhotoBase):
    def begin(self):
        ana, ben = self.kid("Ana"), self.kid("Ben")
        self.assertTrue(self.do(ana, "game", action="create", kind="fashion")["ok"])
        self.assertTrue(self.do(ben, "game", action="join")["ok"])
        self.assertTrue(self.do(ana, "game", action="start")["ok"])
        game = server.pixel_room["game"]
        game["theme"] = next(t for t in server.FASHION_THEMES if t["words"] == "Royal")
        return ana, ben, game

    def test_the_results_offer_a_captioned_runway_photo_once(self):
        ana, ben, game = self.begin()
        self.assertEqual(self.photos(), [])                  # not while they dress or walk
        self.assertTrue(self.do(ana, "game", action="ready")["ok"])
        self.assertTrue(self.do(ben, "game", action="ready")["ok"])
        self.assertEqual(game["phase"], "runway")
        self.assertEqual(self.photos(), [])
        self.advance(server.fashion_walk_seconds(len(game["joined"])) * len(game["joined"]) + 1)
        self.assertEqual(game["phase"], "results")
        photos = self.photos()
        self.assertEqual(len(photos), 1, photos)
        photo = photos[0]
        self.assertEqual(photo["style"], "fashion")
        self.assertEqual(photo["caption"], "👗 Fashion show · Theme: Royal · 18 Nov 2026")
        self.assertEqual(photo["seconds"], server.PHOTO_SHOW_SECONDS)
        self.assertEqual(photo["x"], server.FASHION_X)
        self.assertEqual(photo["theme"]["words"], "Royal")
        # A second call at the results must not add another save button.
        server.fashion_awards(game, server.game_seats(), self.clock)
        self.assertEqual(len(self.photos()), 1)

    def test_the_caption_uses_the_theme_the_class_got(self):
        ana, ben, game = self.begin()
        game["theme"] = next(t for t in server.FASHION_THEMES if t["words"] == "Spooky")
        self.assertTrue(self.do(ana, "game", action="ready")["ok"])
        self.assertTrue(self.do(ben, "game", action="ready")["ok"])
        self.advance(server.fashion_walk_seconds(len(game["joined"])) * len(game["joined"]) + 1)
        self.assertEqual(self.photos()[-1]["caption"],
                         "👗 Fashion show · Theme: Spooky · 18 Nov 2026")


class ClassPhotoStillTheSame(PhotoBase):
    def test_the_class_photo_event_is_unchanged(self):
        self.kid("Ana")
        self.kid("Ben")
        server.class_photo()
        photo = self.photos()[-1]
        self.assertEqual(photo["count"], 2)
        self.assertEqual(photo["loc"], 0)
        self.assertNotIn("style", photo)
        self.assertNotIn("caption", photo)


if __name__ == "__main__":
    unittest.main()
