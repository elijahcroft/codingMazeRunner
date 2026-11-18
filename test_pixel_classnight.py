"""Small-screen / whole-class checks that grew out of the night-4 stress run.

The first test is a real bug found with tools/e2e_classnight.py: after a game
had finished, a student's "Go to" event was filtered out for everyone who had
been in that round, so their pal stayed at the old game spot on every screen
until a reload.  A finished round hides nothing, so rooms must pass those
events on.
"""
import unittest
from unittest.mock import patch

import pixel
import server


class RoomEventsAfterAGame(unittest.TestCase):
    def setUp(self):
        self.saved = server.pixel_room, server.players, server.pixel_class, server.pixel_feed
        server.pixel_room = dict(server.room_empty(), open=True, words=False)
        server.players = {}
        server.pixel_class = {"open": len(pixel.LEVEL_ORDER) - 1}
        server.pixel_feed = []
        self.clock = 1000.
        things = [patch.object(server.time, "time", side_effect=lambda: self.clock),
                  patch.object(server, "pixel_save_soon"),
                  patch.object(server.time, "strftime", side_effect=lambda fmt, t=None: "2026-11-18")]
        for thing in things:
            thing.start()
            self.addCleanup(thing.stop)
        self.addCleanup(self.restore)

    def restore(self):
        server.pixel_room, server.players, server.pixel_class, server.pixel_feed = self.saved

    def kid(self, name):
        p = {"id": "private-" + name, "name": name}
        server.players[p["id"]] = p
        server.pixel_entry(p)["hang_let_in"] = True
        self.assertTrue(server.room_do(p, {"what": "join"})["ok"])
        return p

    def test_a_go_event_is_not_hidden_after_the_round_has_finished(self):
        ana, ben = self.kid("Ana"), self.kid("Ben")
        self.assertTrue(server.room_do(ana, {"what": "game", "action": "create", "kind": "fashion"})["ok"])
        self.assertTrue(server.room_do(ben, {"what": "game", "action": "join"})["ok"])
        self.assertTrue(server.room_do(ana, {"what": "game", "action": "start"})["ok"])
        server.room_do(ana, {"what": "game", "action": "ready"})
        server.room_do(ben, {"what": "game", "action": "ready"})
        # The round is over, but its results card stays up for a moment.
        server.pixel_room["game"]["phase"] = "results"
        server.pixel_room["game"]["until"] = self.clock + 10
        server.pixel_room["game"]["rewards"] = {}
        before = server.pixel_room["seq"]
        self.assertTrue(server.room_do(ana, {"what": "go", "name": "wedding"})["ok"])
        view = server.room_view(ana, before)
        events = [e for e in view["events"] if e["kind"] == "go" and e["seat"] == view["you"]]
        self.assertTrue(events, "a finished game must not hide the go event")
        self.assertIsInstance(events[-1]["x"], int)

    def test_a_hiding_game_still_hides_other_players_moves(self):
        ana, ben = self.kid("Ana"), self.kid("Ben")
        self.assertTrue(server.room_do(ana, {"what": "game", "action": "create", "kind": "hide"})["ok"])
        self.assertTrue(server.room_do(ben, {"what": "game", "action": "join"})["ok"])
        self.assertTrue(server.room_do(ana, {"what": "game", "action": "start"})["ok"])
        server.pixel_room["game"]["it"] = server.pixel_room["here"][ben["id"]]["seat"]   # Ben seeks
        before = server.pixel_room["seq"]
        self.assertTrue(server.room_do(ana, {"what": "walk", "x": 300, "y": .5})["ok"])
        ana_seat = server.pixel_room["here"][ana["id"]]["seat"]
        view = server.room_view(ben, before)
        own = [e for e in view["events"] if e["kind"] == "walk" and e["seat"] == ana_seat]
        # A hiding player's move stays hidden while the round is on.
        self.assertEqual(own, [])


if __name__ == "__main__":
    unittest.main()
