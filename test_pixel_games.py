"""Multiplayer round rules, privacy, movement, and persistent rewards."""
import copy
import unittest
from unittest.mock import patch

import pixel
import server


class PlaygroundRounds(unittest.TestCase):
    def setUp(self):
        self.saved = server.pixel_room, server.players, server.pixel_class, server.pixel_feed
        server.pixel_room = dict(server.room_empty(), open=True, words=False)
        server.players = {}
        server.pixel_class = {"open": 3}
        server.pixel_feed = []
        self.clock = 1000.
        self.time = patch.object(server.time, "time", side_effect=lambda: self.clock)
        self.save = patch.object(server, "pixel_save_soon")
        self.time.start()
        self.save.start()
        self.addCleanup(self.time.stop)
        self.addCleanup(self.save.stop)
        self.addCleanup(self.restore)
        self.kids = [self.kid(name) for name in ("Mia", "Ben", "Alex")]

    def restore(self):
        server.pixel_room, server.players, server.pixel_class, server.pixel_feed = self.saved

    def kid(self, name):
        p = {"id": "private-" + name, "name": name}
        server.players[p["id"]] = p
        entry = server.pixel_entry(p)
        entry["solved"].update({k: [True] * 3 for k in ("a1", "a2", "a3")})
        self.assertTrue(server.room_do(p, {"what": "join"})["ok"])
        return p

    def do(self, p, action, **extra):
        return server.room_do(p, dict(what="game", action=action, **extra))

    def seat(self, p):
        return server.pixel_room["here"][p["id"]]["seat"]

    def begin(self, kind="hide", count=2):
        self.assertTrue(self.do(self.kids[0], "create", kind=kind)["ok"])
        for kid in self.kids[1:count]:
            self.assertTrue(self.do(kid, "join")["ok"])
        with patch.object(server.random, "choice", side_effect=lambda rows: rows[-1]) as choice:
            self.assertTrue(self.do(self.kids[0], "start")["ok"])
            self.assertEqual(choice.call_count, 1)
        return server.pixel_room["game"]

    def advance(self, seconds):
        self.clock += seconds
        for spot in server.pixel_room["here"].values():
            spot["seen"] = self.clock
        server.room_keep_up()

    def move(self, kid, x, y):
        return server.room_do(kid, dict(what="walk", x=x, y=y))

    def test_opt_in_and_random_seeker_not_always_host(self):
        game = self.begin()
        self.assertEqual(game["joined"], [self.seat(k) for k in self.kids[:2]])
        self.assertEqual(game["it"], self.seat(self.kids[1]))
        self.assertNotEqual(game["it"], game["host"])
        self.assertIn("error", self.do(self.kids[2], "join"))
        self.assertIn("error", self.do(self.kids[2], "create", kind="tag"))

    def test_lobby_needs_two_and_starts_itself(self):
        self.do(self.kids[0], "create", kind="tag")
        self.assertIn("error", self.do(self.kids[0], "start"))
        self.do(self.kids[1], "join")
        self.do(self.kids[1], "join")
        self.advance(server.GAME_JOIN_SECONDS)
        self.assertEqual(server.pixel_room["game"]["phase"], "playing")
        self.assertEqual(len(server.pixel_room["game"]["joined"]), 2)

    def test_empty_lobby_expires_without_rewards(self):
        self.do(self.kids[0], "create", kind="hide")
        self.advance(server.GAME_JOIN_SECONDS)
        self.assertEqual(server.pixel_room["game"]["phase"], "results")
        self.assertEqual(server.pixel_room["game"]["rewards"], {})
        self.advance(10)
        self.assertIsNone(server.pixel_room["game"])

    def test_seeker_cannot_move_while_counting_or_use_teleports(self):
        self.begin()
        self.assertIn("error", self.move(self.kids[1], 500, 0))
        for what in ("go", "toy", "five", "mymove", "rest"):
            self.assertIn("error", server.room_do(self.kids[0], {"what": what, "name": "beach", "x": 500, "y": 0}))

    def test_movement_is_timed_bounded_and_rejects_nonfinite(self):
        game = self.begin("tag")
        seat = self.seat(self.kids[0])
        start = game["motion"][seat]["x"]
        self.move(self.kids[0], 999999, .55)
        self.assertEqual(game["motion"][seat]["x"], start)
        self.advance(.1)
        self.assertAlmostEqual(game["motion"][seat]["x"], start + server.GAME_SPEED * .1)
        self.assertEqual(game["motion"][seat]["tx"], server.GAME_WIDTH - 8)
        for bad in (float('nan'), float('inf'), True, "200", None):
            self.assertIn("error", self.move(self.kids[0], bad, .5))

    def hide_at(self, cover):
        self.move(self.kids[0], cover["x"], cover["y"])
        self.advance(7)
        self.assertTrue(self.do(self.kids[0], "hide", cover=cover["key"])["ok"])

    def test_cover_requires_proximity_and_positions_stay_private(self):
        self.begin()
        cover = server.GAME_COVER[-1]
        self.assertIn("error", self.do(self.kids[0], "hide", cover=cover["key"]))
        self.hide_at(cover)
        for viewer in (self.kids[1], self.kids[2], None):
            for after in (-1, 0):
                data = server.room_view(viewer, after)
                row = next(r for r in data["game_members"] if r["seat"] == self.seat(self.kids[0]))
                self.assertTrue(row["concealed"])
                self.assertEqual((row["x"], row["tx"]), (160, 160))
                self.assertIsNone(data["game"]["hiding"])
                self.assertNotIn("private-", str(data))
        self.assertEqual(server.room_view(self.kids[0], -1)["game"]["hiding"], cover["key"])
        self.advance(13)
        self.assertIn("error", self.move(self.kids[0], 10, .5))

    def test_search_checks_role_range_and_finishes_with_rewards_once(self):
        game = self.begin()
        cover = server.GAME_COVER[0]
        self.hide_at(cover)
        self.assertIn("error", self.do(self.kids[1], "search", cover=cover["key"]))
        self.advance(13)
        self.assertIn("error", self.do(self.kids[0], "search", cover=cover["key"]))
        self.assertIn("error", self.do(self.kids[1], "search", cover=cover["key"]))
        self.move(self.kids[1], cover["x"], cover["y"])
        self.advance(2)
        self.assertTrue(self.do(self.kids[1], "search", cover=cover["key"])["ok"])
        self.assertEqual(game["phase"], "results")
        self.assertEqual(len(game["rewards"]), 2)
        for kid in self.kids[:2]:
            entry = server.pixel_entry(kid)
            self.assertEqual(len(entry["gifts"]), 1)
            self.assertIn("play_hide", entry["badges"])
        before = copy.deepcopy([k["pixel"] for k in self.kids])
        self.do(self.kids[1], "search", cover=cover["key"])
        self.advance(1)
        self.assertEqual(before, [k["pixel"] for k in self.kids])
        self.assertEqual(server.hang_meter()["points"], 4)
        self.assertFalse(server.pixel_entry(self.kids[2])["gifts"])

    def test_tag_passes_it_with_grace_period(self):
        game = self.begin("tag")
        original = game["it"]
        self.move(self.kids[0], 160, .55)
        self.advance(1)
        self.assertEqual(game["it"], original)
        self.advance(2)
        self.assertEqual(game["it"], self.seat(self.kids[0]))
        self.advance(1)
        self.assertEqual(game["it"], self.seat(self.kids[0]))
        self.assertEqual(game["tags"][original], 1)
        self.advance(90)
        self.assertEqual(game["phase"], "results")
        self.assertIn("play_tag", self.kids[0]["pixel"]["badges"])

    def test_disconnection_and_teacher_close_do_not_award(self):
        game = self.begin()
        server.pixel_room["here"][self.kids[1]["id"]]["seen"] = self.clock - 20
        server.room_keep_up()
        self.assertEqual(game["phase"], "results")
        self.assertEqual(game["rewards"], {})
        server.room_set(False)
        self.assertIsNone(server.pixel_room["game"])
        self.assertIn("error", self.do(self.kids[0], "create", kind="hide"))

    def test_leaving_does_not_keep_controlling_the_old_player(self):
        game = self.begin("tag", 3)
        self.do(self.kids[0], "leave")
        self.move(self.kids[0], 900, .7)
        self.advance(.5)
        self.assertEqual(server.pixel_room["here"][self.kids[0]["id"]]["x"], 900)
        self.assertEqual(game["phase"], "playing")

    def test_normal_room_actions_still_work(self):
        self.assertTrue(server.room_do(self.kids[0], {"what": "go", "name": "beach"})["ok"])
        self.assertTrue(server.room_do(self.kids[0], {"what": "say", "text": "Hello!"})["ok"])


if __name__ == "__main__":
    unittest.main()
