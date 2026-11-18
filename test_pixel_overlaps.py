"""Moments in the Hang out that must not break each other.

Tonight's class-wide moments were each tested on their own. These are the few
server rules where two of them meet: the teacher's 📸 Class photo while a
wedding is playing, the 🌠 Star shower during a 🎂 birthday song, a 🎂 birthday
during a 🏠 open house, and friends inside a home when the class photo is taken.
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

    def advance(self, seconds=1):
        self.clock += seconds
        for spot in server.pixel_room["here"].values():
            spot["seen"] = self.clock
        server.room_keep_up()

    def ready_home(self, p):
        """Walk into your own home and put out 3 things, so it can open."""
        self.assertTrue(self.do(p, "home")["ok"])
        entry = server.pixel_entry(p)
        entry["stuff"] += ["lamp", "teddy", "balloons"]
        for key, x in (("rug", 60), ("plant", 90), ("lamp", 120)):
            out = self.do(p, "furnish", key=key, x=x, y=.5)
            self.assertTrue(out.get("ok"), out)
        self.assertEqual(len(entry["home"]["items"]), 3)

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


class ClassPhotoWithFriendsInside(OverlapBase):
    def test_the_answer_says_how_many_were_inside_a_home(self):
        ana, ben, cy = self.kid("Ana"), self.kid("Ben"), self.kid("Cy")
        self.assertTrue(self.do(ben, "home")["ok"])
        self.assertTrue(self.do(cy, "home")["ok"])
        out = server.pixel_teacher({"action": "photo"})
        self.assertTrue(out["ok"], out)
        self.assertEqual(out["inside"], 2)
        self.assertEqual(out["message"],
                         "📸 Done! 2 friends were inside a home, so they're not in this one.")
        for name in ("Ana", "Ben", "Cy"):
            self.assertNotIn(name, out["message"])       # just the count, no names
        self.assertEqual(self.photos()[-1]["count"], 1)  # only Ana was outside

    def test_one_friend_inside_uses_the_singular_words(self):
        ana, ben = self.kid("Ana"), self.kid("Ben")
        self.assertTrue(self.do(ben, "home")["ok"])
        out = server.pixel_teacher({"action": "photo"})
        self.assertEqual(out["inside"], 1)
        self.assertIn("1 friend was inside a home", out["message"])

    def test_a_photo_with_everybody_outside_keeps_the_plain_answer(self):
        self.kid("Ana")
        self.kid("Ben")
        self.assertEqual(server.pixel_teacher({"action": "photo"}), {"ok": True})


class BirthdayDuringOpenHouse(OverlapBase):
    def test_the_answer_says_the_open_house_ended(self):
        ana, ben = self.kid("Ana"), self.kid("Ben")
        self.ready_home(ana)
        self.assertTrue(self.do(ana, "openhouse", action="start")["ok"])
        self.assertTrue(server.pixel_room["openhouses"])

        out = server.pixel_teacher({"action": "birthday", "name": "Ana"})
        self.assertTrue(out["ok"], out)                  # the birthday is not blocked
        self.assertEqual(out["openhouse_ended"], 1)
        self.assertEqual(out["message"],
                         "🎂 Started. (Ana's open house ended so everyone could come.)")
        self.assertFalse(server.pixel_room["openhouses"])
        self.assertIsNotNone(server.pixel_room["birthday"])

    def test_two_open_houses_are_named_in_the_answer(self):
        ana, ben = self.kid("Ana"), self.kid("Ben")
        self.ready_home(ana)
        self.ready_home(ben)
        self.assertTrue(self.do(ana, "openhouse", action="start")["ok"])
        self.assertTrue(self.do(ben, "openhouse", action="start")["ok"])

        out = server.pixel_teacher({"action": "birthday", "name": "Ana"})
        self.assertTrue(out["ok"], out)
        self.assertEqual(out["openhouse_ended"], 2)
        self.assertIn("Ana's and Ben's open houses ended", out["message"])
        self.assertFalse(server.pixel_room["openhouses"])


class StarShowerDuringBirthday(OverlapBase):
    def test_the_shower_waits_for_the_birthday_to_finish(self):
        ana = self.kid("Ana")
        self.kid("Ben")
        self.assertTrue(server.pixel_teacher({"action": "birthday", "name": "Ana"})["ok"])

        out = server.pixel_teacher({"action": "shower"})
        self.assertTrue(out["ok"], out)
        self.assertEqual(out["message"], "The star shower starts right after the song.")
        self.assertIsNone(server.pixel_room["shower"])    # no unexplained stars during the song
        self.advance(3)
        self.assertIsNone(server.pixel_room["shower"])

        self.advance(server.BIRTHDAY_SECONDS)
        self.assertIsNone(server.pixel_room["birthday"])
        self.assertIsNotNone(server.pixel_room["shower"])
        self.assertTrue(any(e["kind"] == "shower" for e in server.pixel_room["events"]))


if __name__ == "__main__":
    unittest.main()
