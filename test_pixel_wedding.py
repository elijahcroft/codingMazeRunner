"""💒 The wedding in the Hang out's Wedding garden.

These are the server-side rules behind the ceremony the class sees: one student
asks a friend in the garden, the friend says yes with one tap, the guests and the
couple walk to their places, the wedding words play in order, and the couple and
guests are paid a little at most once each day. Leaving, or the teacher closing
the room, stops the wedding instead of leaving everyone waiting.
"""
import unittest
from unittest.mock import patch

import pixel
import server


class Wedding(unittest.TestCase):
    def setUp(self):
        self.saved = server.pixel_room, server.players, server.pixel_class, server.pixel_feed
        server.pixel_room = dict(server.room_empty(), open=True, words=False)
        server.players = {}
        server.pixel_class = {"open": len(pixel.LEVEL_ORDER) - 1}
        server.pixel_feed = []
        self.clock = 1000.
        self.today = "2026-11-16"
        for p in (patch.object(server.time, "time", side_effect=lambda: self.clock),
                  patch.object(server.time, "strftime", side_effect=lambda fmt, t=None: self.today),
                  patch.object(server, "pixel_save_soon")):
            p.start()
            self.addCleanup(p.stop)
        self.addCleanup(self.restore)

    def restore(self):
        server.pixel_room, server.players, server.pixel_class, server.pixel_feed = self.saved

    # ---- The class in the garden -----------------------------------------------------------
    def kid(self, name, garden=True):
        p = {"id": "private-" + name, "name": name}
        server.players[p["id"]] = p
        server.pixel_entry(p)["hang_let_in"] = True
        self.assertTrue(server.room_do(p, {"what": "join"})["ok"])
        if garden:
            self.assertTrue(server.room_do(p, {"what": "go", "name": "wedding"})["ok"])
        return p

    def spot(self, p):
        return server.pixel_room["here"][p["id"]]

    def seat(self, p):
        return self.spot(p)["seat"]

    def do(self, p, what, **more):
        return server.room_do(p, dict(what=what, **more))

    def entry(self, p):
        return server.pixel_entry(p)

    def advance(self, seconds=1, stale=()):
        self.clock += seconds
        for spot in server.pixel_room["here"].values():
            if spot["seat"] not in stale:
                spot["seen"] = self.clock
        server.room_keep_up()

    def wedding_events(self):
        return [e for e in server.pixel_room["events"] if e["kind"] == "wedding"]

    def begin(self, host, partner):
        out = self.do(host, "wedding")
        self.assertTrue(out["ok"], out)
        self.assertTrue(self.do(host, "wedding_pick", seat=self.seat(partner))["ok"])
        self.assertTrue(self.do(partner, "wedding_yes")["ok"])
        self.assertEqual(server.pixel_room["wedding"]["phase"], "ceremony")

    # ---- The ceremony ----------------------------------------------------------------------
    def test_a_wedding_plays_for_everyone_in_the_garden(self):
        ana, ben, cy = self.kid("Ana"), self.kid("Ben"), self.kid("Cy")
        out = self.do(ana, "wedding")
        self.assertTrue(out["ok"], out)
        self.assertEqual({c["name"] for c in out["candidates"]}, {"Ben", "Cy"})
        self.assertEqual(self.wedding_events()[-1]["phase"], "pick")

        self.assertTrue(self.do(ana, "wedding_pick", seat=self.seat(ben))["ok"])
        invite = self.wedding_events()[-1]
        self.assertEqual(invite["phase"], "invite")
        self.assertEqual(invite["to"], self.seat(ben))
        self.assertEqual(invite["host_name"], "Ana")

        self.assertTrue(self.do(ben, "wedding_yes")["ok"])
        start = self.wedding_events()[-1]
        self.assertEqual(start["phase"], "start")
        self.assertEqual(start["partner_name"], "Ben")
        view = server.room_view(ana, 0)
        self.assertEqual(view["wedding"]["phase"], "ceremony")
        self.assertEqual(len(view["wedding"]["couple"]), 2)
        self.assertTrue(view["wedding"]["seats"])

        # The guests walk to their rows, then the couple walks up the aisle.
        self.advance(1)
        walks = [e for e in server.pixel_room["events"] if e["kind"] == "walk" and e["n"] > start["n"]]
        self.assertTrue(any(e["seat"] == self.seat(cy) for e in walks), walks)
        self.advance(2)
        couple_walks = [e for e in server.pixel_room["events"] if e["kind"] == "walk" and
                        e["seat"] in (self.seat(ana), self.seat(ben)) and e["n"] > start["n"]]
        self.assertEqual(len(couple_walks), 2, couple_walks)

        # Wedding words come from the existing Wedding tap-word list, in order.
        self.advance(4)
        said = [e["text"] for e in server.pixel_room["events"] if e["kind"] == "say" and e["n"] > start["n"]]
        self.assertEqual(said[:1], ["Do you promise?"])
        self.advance(2)
        said = [e["text"] for e in server.pixel_room["events"] if e["kind"] == "say" and e["n"] > start["n"]]
        self.assertEqual(said[:2], ["Do you promise?", "I do!"])
        self.advance(2)
        said = [e["text"] for e in server.pixel_room["events"] if e["kind"] == "say" and e["n"] > start["n"]]
        self.assertEqual(said[:3], ["Do you promise?", "I do!", "I do too!"])
        self.assertTrue(all(t in pixel.ROOM_WORDS["Wedding"] for t in said))

        # Rings, bells, confetti and a bouquet toss to a real guest.
        self.advance(8)
        fx = {e["name"] for e in server.pixel_room["events"] if e["kind"] == "fx" and e["n"] > start["n"]}
        self.assertTrue({"hearts", "bells", "march", "confetti", "bouquet"} <= fx, fx)
        bouquet = [e for e in self.wedding_events() if e["phase"] == "bouquet"][-1]
        self.assertIn(bouquet["catcher"], (self.seat(ben), self.seat(cy)))
        self.advance(2)
        catch = [e for e in self.wedding_events() if e["phase"] == "catch"][-1]
        self.assertEqual(catch["catcher"], bouquet["catcher"])
        self.assertTrue(any(e.get("text") == "Catch the flowers!" and e.get("seat") == catch["catcher"]
                            for e in server.pixel_room["events"] if e["kind"] == "say"))

        self.advance(4)
        self.assertIsNone(server.pixel_room["wedding"])
        self.assertEqual(self.wedding_events()[-1]["phase"], "done")
        self.assertEqual(server.pixel_feed[-1]["text"], "Ana and Ben had a wedding! 💒")
        self.assertEqual(self.entry(ana)["coins"], server.WEDDING_COUPLE_COINS)
        self.assertEqual(self.entry(ben)["coins"], server.WEDDING_COUPLE_COINS)
        self.assertEqual(self.entry(cy)["coins"], server.WEDDING_GUEST_COINS)
        self.assertEqual(server.hang_view()["points"], 2)

    def test_a_wedding_pays_at_most_once_a_day(self):
        ana, ben, cy = self.kid("Ana"), self.kid("Ben"), self.kid("Cy")
        self.begin(ana, ben)
        self.advance(server.WEDDING_SECONDS)
        coins = {p["name"]: self.entry(p)["coins"] for p in (ana, ben, cy)}
        meter = server.hang_view()["points"]
        self.assertEqual(coins, {"Ana": 5, "Ben": 5, "Cy": 2})

        # A second wedding the same day is allowed, but it pays nobody twice.
        self.begin(ana, ben)
        self.advance(server.WEDDING_SECONDS)
        self.assertEqual({p["name"]: self.entry(p)["coins"] for p in (ana, ben, cy)}, coins)
        self.assertEqual(server.hang_view()["points"], meter)
        self.assertEqual(server.pixel_feed[-1]["text"], "Ana and Ben had a wedding! 💒")

        # A new day pays again.
        self.today = "2026-11-17"
        self.begin(ana, ben)
        self.advance(server.WEDDING_SECONDS)
        self.assertEqual(self.entry(ana)["coins"], coins["Ana"] + 5)
        self.assertEqual(self.entry(ben)["coins"], coins["Ben"] + 5)
        self.assertEqual(self.entry(cy)["coins"], coins["Cy"] + 2)

    def test_leaving_midway_stops_the_wedding_without_a_freeze(self):
        ana, ben, cy = self.kid("Ana"), self.kid("Ben"), self.kid("Cy")
        self.begin(ana, ben)
        self.advance(2)
        self.assertTrue(self.do(ben, "leave")["ok"])
        server.room_keep_up()
        self.assertIsNone(server.pixel_room["wedding"])
        self.assertEqual(self.wedding_events()[-1]["phase"], "cancelled")
        self.assertIn("partner", self.wedding_events()[-1]["reason"])
        # Everyone's screen still answers, and the host can try again.
        self.assertTrue(server.room_view(ana, -1)["open"])
        self.assertEqual(self.entry(ana)["coins"], 0)
        self.assertTrue(self.do(ana, "wedding")["ok"])

        # A tab that goes away without pressing Leave is dropped and stops it too.
        self.assertTrue(self.do(ana, "wedding_pick", seat=self.seat(cy))["ok"])
        self.assertTrue(self.do(cy, "wedding_yes")["ok"])
        self.advance(server.ROOM_AWAY + 1, stale={self.seat(cy)})
        self.assertIsNone(server.pixel_room["wedding"])
        self.assertEqual(self.wedding_events()[-1]["phase"], "cancelled")

    def test_one_wedding_at_a_time_and_two_different_people(self):
        ana = self.kid("Ana")
        out = self.do(ana, "wedding")
        self.assertIn("Ask a friend", out["error"])
        ben = self.kid("Ben")
        self.assertTrue(self.do(ana, "wedding")["ok"])
        # A second wedding cannot start while the first is choosing a partner.
        self.assertIn("already happening", self.do(ben, "wedding")["error"])
        # And a game cannot start in the middle of it either.
        self.assertIn("wedding", self.do(ben, "game", action="create", kind="tag")["error"])
        # A student cannot pick themselves.
        self.assertIn("not in the Wedding garden", self.do(ana, "wedding_pick", seat=self.seat(ana))["error"])
        self.assertTrue(self.do(ana, "wedding_cancel")["ok"])
        self.assertIsNone(server.pixel_room["wedding"])
        self.assertTrue(self.do(ben, "wedding")["ok"])

    def test_hidden_names_stay_hidden_in_the_feed(self):
        ana, ben = self.kid("Ana"), self.kid("Ben")
        self.do(ana, "hidename", on=True)
        self.begin(ana, ben)
        self.advance(server.WEDDING_SECONDS)
        self.assertEqual(server.pixel_feed[-1]["text"], "Secret pal and Ben had a wedding! 💒")
        self.assertNotIn("Ana", server.pixel_feed[-1]["text"])
        self.assertEqual(self.wedding_events()[-1]["host_name"], "Secret pal")


if __name__ == "__main__":
    unittest.main()
