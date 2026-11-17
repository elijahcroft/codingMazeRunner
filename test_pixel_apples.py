"""🍎 Apple grab: a Hang out round where walking onto apples scores them."""
import copy
import unittest
from unittest.mock import patch

import server


class Apples(unittest.TestCase):
    def setUp(self):
        self.saved = server.pixel_room, server.players, server.pixel_class, server.pixel_feed
        server.pixel_room = dict(server.room_empty(), open=True, words=False)
        server.players = {}
        server.pixel_class = {"open": 3}
        server.pixel_feed = []
        self.clock = 1000.
        self.time = patch.object(server.time, "time", side_effect=lambda: self.clock)
        self.save = patch.object(server, "pixel_save_soon")
        self.job = patch.object(server, "day_job")      # today's jobs pay too; they have their own tests
        self.time.start()
        self.save.start()
        self.job.start()
        self.addCleanup(self.time.stop)
        self.addCleanup(self.save.stop)
        self.addCleanup(self.job.stop)
        self.addCleanup(self.restore)
        self.kids = [self.kid(name) for name in ("Mia", "Ben", "Alex")]

    def restore(self):
        server.pixel_room, server.players, server.pixel_class, server.pixel_feed = self.saved

    def kid(self, name):
        p = {"id": "private-" + name, "name": name}
        server.players[p["id"]] = p
        server.pixel_entry(p)["solved"].update({k: [True] * 3 for k in ("a1", "a2", "a3")})
        self.assertTrue(server.room_do(p, {"what": "join"})["ok"])
        return p

    def do(self, p, action, **extra):
        return server.room_do(p, dict(what="game", action=action, **extra))

    def seat(self, p):
        return server.pixel_room["here"][p["id"]]["seat"]

    def move(self, p, x, y):
        return server.room_do(p, dict(what="walk", x=x, y=y))

    def advance(self, seconds):
        self.clock += seconds
        for spot in server.pixel_room["here"].values():
            spot["seen"] = self.clock
        server.room_keep_up()

    def begin(self, count=2):
        self.assertTrue(self.do(self.kids[0], "create", kind="apples")["ok"])
        for kid in self.kids[1:count]:
            self.assertTrue(self.do(kid, "join")["ok"])
        self.assertTrue(self.do(self.kids[0], "start")["ok"])
        return server.pixel_room["game"]

    def near(self, kid, gold=False, dx=40):
        """Put an apple right where this pal is standing, for a walk to pick up."""
        game, seat = server.pixel_room["game"], self.seat(kid)
        motion = game["motion"][seat]
        apple = {"id": 900 + seat, "x": round(motion["x"] + dx, 1), "y": motion["y"], "gold": gold}
        game["apples"][0] = apple
        return apple

    def test_every_game_kind_has_a_title_and_a_badge(self):
        self.assertIn("apples", server.GAME_KINDS)
        self.assertEqual(server.GAME_TITLES["apples"], "Apple grab")
        self.assertEqual(set(server.GAME_KINDS), set(server.GAME_TITLES))
        for kind in server.GAME_KINDS:
            self.assertIn("play_" + kind, server.PIXEL_BADGES)

    def test_walking_onto_an_apple_scores_it_and_a_new_one_appears(self):
        game = self.begin()
        self.assertEqual(len(game["apples"]), server.APPLE_COUNT)
        apple = dict(game["apples"][0], gold=False)
        game["apples"][0] = apple
        self.move(self.kids[0], apple["x"], apple["y"])
        self.advance(server.GAME_WIDTH / server.GAME_SPEED + 1)      # long enough to walk right across the game area
        seat = self.seat(self.kids[0])
        self.assertEqual(game["score"], {seat: server.APPLE_WORTH})
        self.assertEqual(len(game["apples"]), server.APPLE_COUNT)
        self.assertNotIn(apple["id"], [a["id"] for a in game["apples"]])
        # A plain apple isn't news: only golden ones pop up on everyone's screen.
        self.assertFalse(any("grabbed" in e.get("message", "") for e in server.pixel_room["events"] if e["kind"] == "game"))

    def test_a_golden_apple_is_worth_three(self):
        game = self.begin()
        apple = self.near(self.kids[0], gold=True)
        self.move(self.kids[0], apple["x"], apple["y"])
        self.advance(.5)
        self.assertEqual(game["score"], {self.seat(self.kids[0]): server.APPLE_GOLD_WORTH})
        self.assertIn("golden apple", [e["message"] for e in server.pixel_room["events"] if e["kind"] == "game"][-1])

    def test_every_screen_sees_the_apples_and_the_live_scores(self):
        game = self.begin()
        for viewer in (self.kids[0], self.kids[1], None):
            view = server.room_view(viewer, server.pixel_room["seq"])["game"]
            self.assertEqual(len(view["apples"]), server.APPLE_COUNT)
            self.assertEqual(view["scores"], game["score"])
            self.assertEqual({a["id"] for a in view["apples"]}, {a["id"] for a in game["apples"]})

    def test_the_most_apples_wins_and_every_player_is_paid(self):
        game = self.begin()
        mia, ben = (self.seat(k) for k in self.kids[:2])
        game["score"] = {mia: 4, ben: 2}
        self.advance(server.APPLE_SECONDS)
        self.assertEqual(game["phase"], "results")
        self.assertIn("Mia", game["message"])
        self.assertEqual(set(game["rewards"]), {mia, ben})
        self.assertTrue(game["rewards"][mia]["won"])
        self.assertFalse(game["rewards"][ben]["won"])
        for kid, won in ((self.kids[0], True), (self.kids[1], False)):
            entry = server.pixel_entry(kid)
            self.assertEqual(entry["coins"], server.pixel.COINS_ROUND + (server.pixel.COINS_WIN if won else 0))
            self.assertEqual(len(entry["gifts"]), 1)
            self.assertIn("play_apples", entry["badges"])
        self.assertEqual(server.hang_meter()["points"], 4)

    def test_a_tie_shares_the_win(self):
        game = self.begin()
        seats = [self.seat(k) for k in self.kids[:2]]
        game["score"] = {seats[0]: 3, seats[1]: 3}
        self.advance(server.APPLE_SECONDS)
        self.assertEqual(game["phase"], "results")
        self.assertIn("Most apples: Mia and Ben", game["message"])
        self.assertTrue(all(game["rewards"][s]["won"] for s in seats))

    def test_a_player_leaving_mid_round_is_dropped_and_the_round_goes_on(self):
        game = self.begin(3)
        gone = self.seat(self.kids[2])
        self.advance(3)
        self.do(self.kids[2], "leave")
        self.assertEqual(game["phase"], "playing")
        self.assertNotIn(gone, game["joined"])
        apple = self.near(self.kids[0])
        self.move(self.kids[0], apple["x"], apple["y"])
        self.advance(.5)
        self.assertEqual(game["score"].get(self.seat(self.kids[0])), server.APPLE_WORTH)
        self.advance(server.APPLE_SECONDS)
        self.assertEqual(game["phase"], "results")
        self.assertNotIn(gone, game["rewards"])
        self.assertEqual(set(game["rewards"]), {self.seat(self.kids[0]), self.seat(self.kids[1])})

    def test_two_players_and_one_leaves_the_round_ends_without_prizes(self):
        game = self.begin()
        before = copy.deepcopy([server.pixel_entry(k)["coins"] for k in self.kids])
        self.advance(5)
        self.do(self.kids[1], "leave")
        self.assertEqual(game["phase"], "results")
        self.assertEqual(game["rewards"], {})
        self.assertIn("A player left", game["message"])
        self.assertEqual([server.pixel_entry(k)["coins"] for k in self.kids], before)


if __name__ == "__main__":
    unittest.main()
