"""🎂 The teacher's Birthday! party in the Hang out.

The teacher picks one student who is in the open Hang out. Everyone comes to the
Park and stands in a half circle round the birthday pal by the cake. The class
sings the real Happy Birthday tune, cheers, and then goes back to where they
were. The birthday child keeps a crown for the rest of the day, and the class
gets a small once-a-day gift that a second press cannot pay twice.
"""
import unittest
from unittest.mock import patch

import pixel
import server


class Birthday(unittest.TestCase):
    def setUp(self):
        self.saved = server.pixel_room, server.players, server.pixel_class, server.pixel_feed
        server.pixel_room = dict(server.room_empty(), open=True, words=False)
        server.players = {}
        server.pixel_class = {"open": len(pixel.LEVEL_ORDER) - 1}
        server.pixel_feed = []
        self.clock = 1000.
        self.today = "2026-11-18"
        for p in (patch.object(server.time, "time", side_effect=lambda: self.clock),
                  patch.object(server.time, "strftime", side_effect=lambda fmt, t=None: self.today),
                  patch.object(server, "pixel_save_soon")):
            p.start()
            self.addCleanup(p.stop)
        self.addCleanup(self.restore)

    def restore(self):
        server.pixel_room, server.players, server.pixel_class, server.pixel_feed = self.saved

    # ---- The class in the Hang out ---------------------------------------------------------
    def kid(self, name, home=False):
        p = {"id": "private-" + name, "name": name}
        server.players[p["id"]] = p
        server.pixel_entry(p)["hang_let_in"] = True
        self.assertTrue(server.room_do(p, {"what": "join"})["ok"])
        if home:
            self.assertTrue(server.room_do(p, {"what": "home"})["ok"])
        return p

    def spot(self, p):
        return server.pixel_room["here"][p["id"]]

    def seat(self, p):
        return self.spot(p)["seat"]

    def do(self, p, what, **more):
        return server.room_do(p, dict(what=what, **more))

    def entry(self, p):
        return server.pixel_entry(p)

    def start(self, p):
        return server.pixel_teacher({"action": "birthday", "name": p["name"]})

    def advance(self, seconds=1, stale=()):
        self.clock += seconds
        for spot in server.pixel_room["here"].values():
            if spot["seat"] not in stale:
                spot["seen"] = self.clock
        server.room_keep_up()

    def birthday_events(self):
        return [e for e in server.pixel_room["events"] if e["kind"] == "birthday"]

    # ---- The party -------------------------------------------------------------------------
    def test_the_whole_class_comes_to_the_park_and_the_party_plays_in_order(self):
        ana, ben, cy = self.kid("Ana"), self.kid("Ben"), self.kid("Cy")
        self.assertTrue(self.do(ben, "go", name="beach")["ok"])
        before = {p["name"]: (self.spot(p)["loc"], self.spot(p)["x"], self.spot(p)["y"]) for p in (ana, ben, cy)}

        out = self.start(ana)
        self.assertTrue(out["ok"], out)
        self.assertEqual(out["name"], "Ana")
        self.assertEqual(out["count"], 3)
        self.assertEqual(server.pixel_room["birthday"]["phase"], "party")
        self.assertTrue(self.spot(ana)["crown"])
        self.assertEqual(self.entry(ana)["birthday_crown_day"], self.today)

        # Everyone is outside, at the Park, in a half circle. The birthday pal is by the cake.
        for p in (ana, ben, cy):
            self.assertEqual(self.spot(p)["loc"], 0)
        self.assertEqual((self.spot(ana)["x"], self.spot(ana)["y"]), (196, .55))
        friends = [self.spot(ben), self.spot(cy)]
        self.assertTrue(all(0 < s["x"] < pixel.PLACE_W for s in friends))
        self.assertTrue(all(s["y"] > .55 for s in friends))
        self.assertNotEqual(friends[0]["x"], friends[1]["x"])
        walk_seats = {e["seat"] for e in server.pixel_room["events"] if e["kind"] == "walk"}
        self.assertTrue({self.seat(p) for p in (ana, ben, cy)} <= walk_seats)

        start = self.birthday_events()[0]
        self.assertEqual(start["phase"], "start")
        self.assertEqual(start["name"], "Ana")
        self.assertEqual(start["loc"], None)          # every screen sees the banner
        self.assertIsNotNone(server.room_view(None, -1)["birthday"])

        # Cake candles and then the song, in order.
        self.advance(3.1)
        phases = [e["phase"] for e in self.birthday_events()]
        self.assertIn("candles", phases)
        self.assertIn("song", phases)
        self.assertTrue(any(e["kind"] == "fx" and e["name"] == "cake" for e in server.pixel_room["events"]))

        # Cheer, balloons and a second cheer.
        self.advance(6)
        phases = [e["phase"] for e in self.birthday_events()]
        self.assertIn("cheer", phases)
        self.assertTrue(any(e["kind"] == "move" and e["name"] == "cheer" for e in server.pixel_room["events"]))
        confetti = [e for e in server.pixel_room["events"] if e["kind"] == "fx" and e["name"] == "confetti"]
        self.assertTrue(confetti and confetti[-1]["birthday"])

        self.advance(6)
        self.assertIn("balloons", [e["phase"] for e in self.birthday_events()])
        self.advance(5)
        self.assertIsNone(server.pixel_room["birthday"])
        self.assertEqual(self.birthday_events()[-1]["phase"], "done")
        self.assertEqual(server.pixel_feed[-1]["text"], "🎂 The class sang Happy Birthday to Ana!")
        self.assertEqual({p["name"]: self.entry(p)["coins"] for p in (ana, ben, cy)},
                         {"Ana": server.BIRTHDAY_COINS, "Ben": server.BIRTHDAY_FRIEND_COINS,
                          "Cy": server.BIRTHDAY_FRIEND_COINS})
        self.assertEqual(server.hang_view()["points"], 2)

        # Pals go back to where they were: Ben to the Beach, the others to their Park spots.
        for p in (ana, ben, cy):
            self.assertEqual((self.spot(p)["loc"], self.spot(p)["x"], self.spot(p)["y"]), before[p["name"]])
        self.assertGreaterEqual(self.spot(ben)["x"], pixel.PLACE_W)

    def test_friends_in_a_home_come_out_and_go_back_home(self):
        ana, ben, cy = self.kid("Ana"), self.kid("Ben", home=True), self.kid("Cy")
        home = self.spot(ben)["loc"]
        self.assertTrue(home)
        home_xy = self.spot(ben)["x"], self.spot(ben)["y"]
        self.assertTrue(self.start(ana)["ok"])
        self.assertEqual(self.spot(ben)["loc"], 0)
        self.assertGreater(self.spot(ben)["y"], .55)
        self.advance(server.BIRTHDAY_SECONDS)
        self.assertIsNone(server.pixel_room["birthday"])
        self.assertEqual(self.spot(ben)["loc"], home)
        self.assertEqual((self.spot(ben)["x"], self.spot(ben)["y"]), home_xy)

    def test_pays_at_most_once_per_student_per_day(self):
        ana, ben, cy = self.kid("Ana"), self.kid("Ben"), self.kid("Cy")
        self.assertTrue(self.start(ana)["ok"])
        self.advance(server.BIRTHDAY_SECONDS)
        coins = {p["name"]: self.entry(p)["coins"] for p in (ana, ben, cy)}
        meter = server.hang_view()["points"]
        self.assertEqual(coins, {"Ana": 10, "Ben": 2, "Cy": 2})

        # A second birthday the same day is still fun, but it pays nobody twice.
        self.assertTrue(self.start(ben)["ok"])
        self.advance(server.BIRTHDAY_SECONDS)
        self.assertEqual({p["name"]: self.entry(p)["coins"] for p in (ana, ben, cy)}, coins)
        self.assertEqual(server.hang_view()["points"], meter)
        self.assertEqual(server.pixel_feed[-1]["text"], "🎂 The class sang Happy Birthday to Ben!")

        # A new day pays again.
        self.today = "2026-11-19"
        self.assertTrue(self.start(cy)["ok"])
        self.advance(server.BIRTHDAY_SECONDS)
        self.assertEqual(self.entry(ana)["coins"], coins["Ana"] + 2)
        self.assertEqual(self.entry(ben)["coins"], coins["Ben"] + 2)
        self.assertEqual(self.entry(cy)["coins"], coins["Cy"] + 10)

    def test_leaving_or_closing_mid_song_stops_cleanly(self):
        ana, ben, cy = self.kid("Ana"), self.kid("Ben"), self.kid("Cy")
        self.assertTrue(self.start(ana)["ok"])
        self.advance(3)
        self.assertTrue(self.do(ana, "leave")["ok"])
        server.room_keep_up()
        self.assertIsNone(server.pixel_room["birthday"])
        self.assertEqual(self.birthday_events()[-1]["phase"], "cancelled")
        self.assertIn("birthday", self.birthday_events()[-1]["reason"])
        self.assertEqual(self.entry(ana)["coins"], 0)       # no pay for a stopped party
        self.assertTrue(server.room_view(ben, -1)["open"])

        # A tab that goes away without pressing Leave stops it too.
        self.assertTrue(self.start(ben)["ok"])
        self.advance(server.ROOM_AWAY + 1, stale={self.seat(ben)})
        self.assertIsNone(server.pixel_room["birthday"])
        self.assertEqual(self.birthday_events()[-1]["phase"], "cancelled")

        # Closing the Hang out during the song does not leave anyone waiting.
        self.assertTrue(self.start(cy)["ok"])
        self.advance(2)
        server.pixel_teacher({"action": "room", "on": False})
        self.assertIsNone(server.pixel_room.get("birthday"))
        self.assertFalse(server.room_view(cy, -1)["open"])

    def test_a_game_or_wedding_stops_a_birthday_start_with_a_friendly_message(self):
        ana, ben = self.kid("Ana"), self.kid("Ben")
        dee = {"id": "private-Dee", "name": "Dee"}
        server.players[dee["id"]] = dee
        server.pixel_entry(dee)["hang_let_in"] = True
        self.assertIn("isn't in the Hang out", self.start(dee)["error"])
        server.pixel_teacher({"action": "room", "on": False})
        self.assertIn("Open the Hang out", self.start(ana)["error"])
        server.pixel_teacher({"action": "room", "on": True})
        for p in (ana, ben):
            self.assertTrue(self.do(p, "join")["ok"])

        # A game: the teacher is told to end it first.
        self.assertTrue(self.do(ana, "game", action="create", kind="tag")["ok"])
        self.assertTrue(self.do(ben, "game", action="join")["ok"])
        out = self.start(ben)
        self.assertIn("game", out["error"].lower())
        self.assertIn("End this game", out["error"])
        server.pixel_teacher({"action": "end_game"})

        # A wedding: the teacher is told to wait for it.
        self.assertTrue(self.do(ana, "go", name="wedding")["ok"])
        self.assertTrue(self.do(ben, "go", name="wedding")["ok"])
        self.assertTrue(self.do(ana, "wedding")["ok"])
        out = self.start(ben)
        self.assertIn("wedding", out["error"].lower())
        server.room_do(ana, {"what": "wedding_cancel"})
        server.pixel_room["game"] = None

        # Once the party starts, games and weddings wait for the song.
        self.assertTrue(self.start(ana)["ok"])
        out = self.do(ben, "game", action="create", kind="tag")
        self.assertIn("birthday", out["error"].lower())
        self.do(ben, "go", name="wedding")
        out = self.do(ben, "wedding")
        self.assertIn("birthday", out["error"].lower())

    def test_the_button_only_starts_for_a_student_in_the_open_hang_out(self):
        ana = self.kid("Ana")
        server.pixel_teacher({"action": "room", "on": False})
        self.assertIn("Open the Hang out", self.start(ana)["error"])
        server.pixel_teacher({"action": "room", "on": True})
        self.assertTrue(self.do(ana, "join")["ok"])
        self.assertTrue(self.start(ana)["ok"])
        self.assertIn("already on", self.start(ana)["error"])

    def test_hidden_names_stay_hidden_on_screens_and_in_the_feed(self):
        ana, ben = self.kid("Ana"), self.kid("Ben")
        self.do(ana, "hidename", on=True)
        self.assertTrue(self.start(ana)["ok"])
        start = self.birthday_events()[-1]
        self.assertEqual(start["name"], "Secret pal")
        self.assertEqual(server.room_view(None, -1)["birthday"]["name"], "Secret pal")
        self.advance(server.BIRTHDAY_SECONDS)
        self.assertEqual(server.pixel_feed[-1]["text"], "🎂 The class sang Happy Birthday to Secret pal!")
        self.assertNotIn("Ana", server.pixel_feed[-1]["text"])

    def test_the_crown_is_for_one_day_only(self):
        ana = self.kid("Ana")
        self.assertTrue(self.start(ana)["ok"])
        self.assertTrue(self.spot(ana)["crown"])
        self.advance(server.BIRTHDAY_SECONDS)
        self.assertTrue(self.spot(ana)["crown"])
        self.today = "2026-11-19"
        self.advance(1)
        self.assertFalse(self.spot(ana)["crown"])
        self.assertTrue(any(e["kind"] == "crown" and not e["on"] for e in server.pixel_room["events"]))
        # Joining again after a new day does not bring the old crown back.
        self.do(ana, "leave")
        self.assertTrue(self.do(ana, "join")["ok"])
        self.assertFalse(self.spot(ana)["crown"])

    def test_the_projector_gets_the_moment_even_while_looking_into_a_home(self):
        ana, ben = self.kid("Ana"), self.kid("Ben", home=True)
        home = self.spot(ben)["loc"]
        after = server.pixel_room["seq"]
        self.assertTrue(self.start(ana)["ok"])
        events = server.room_view(None, after, home)["events"]
        self.assertIn("birthday", [e["kind"] for e in events])
        self.assertEqual(server.room_view(None, -1, home)["birthday"]["name"], "Ana")


if __name__ == "__main__":
    unittest.main()
