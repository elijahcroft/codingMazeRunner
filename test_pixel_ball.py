"""⚽ Pal ball: two teams kick a server-held ball into the goal at their end."""
import copy
import unittest
from unittest.mock import patch

import server


class Ball(unittest.TestCase):
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

    def roll(self, seconds, step=.1):
        for _ in range(round(seconds / step)):
            self.advance(step)

    def begin(self, count=2):
        self.assertTrue(self.do(self.kids[0], "create", kind="ball")["ok"])
        for kid in self.kids[1:count]:
            self.assertTrue(self.do(kid, "join")["ok"])
        self.assertTrue(self.do(self.kids[0], "start")["ok"])
        return server.pixel_room["game"]

    def view(self, kid):
        return server.room_view(kid, server.pixel_room["seq"])["game"]

    def test_every_game_kind_has_a_title_and_a_badge(self):
        self.assertIn("ball", server.GAME_KINDS)
        self.assertEqual(server.GAME_TITLES["ball"], "Pal ball")
        self.assertEqual(set(server.GAME_KINDS), set(server.GAME_TITLES))
        for kind in server.GAME_KINDS:
            self.assertIn("play_" + kind, server.PIXEL_BADGES)

    def test_players_are_split_into_blue_and_orange_in_join_order(self):
        game = self.begin(3)
        seats = [self.seat(k) for k in self.kids]
        self.assertEqual([game["teams"][s] for s in seats], ["blue", "orange", "blue"])
        # Each team starts on its own half, behind the ball for the way it kicks.
        self.assertLess(server.pixel_room["here"][self.kids[0]["id"]]["x"], server.GAME_WIDTH / 2)
        self.assertGreater(server.pixel_room["here"][self.kids[1]["id"]]["x"], server.GAME_WIDTH / 2)
        # Every screen sees the same ball and teams, including the projector.
        for viewer in (self.kids[0], self.kids[2], None):
            view = server.room_view(viewer, server.pixel_room["seq"])["game"]
            self.assertEqual(view["ball"], {"x": server.GAME_WIDTH / 2, "y": .55})
            self.assertEqual(view["teams"], game["teams"])
            self.assertEqual(view["team_scores"], {"blue": 0, "orange": 0})
        rows = server.room_view(self.kids[0], server.pixel_room["seq"])["game_members"]
        self.assertEqual({r["seat"]: r["team"] for r in rows}, game["teams"])

    def test_a_pal_walking_into_the_ball_pushes_it_away(self):
        game = self.begin(2)
        kid, seat = self.kids[0], self.seat(self.kids[0])
        motion = game["motion"][seat]
        motion.update(x=300, y=.55, tx=340, ty=.55, at=self.clock)
        server.pixel_room["here"][kid["id"]].update(x=300, y=.55)
        before = [e["message"] for e in server.pixel_room["events"] if e["kind"] == "game"]
        self.advance(.2)
        self.assertGreater(game["ball"]["x"], server.GAME_WIDTH / 2)
        self.assertGreater(game["ball"]["vx"], 0)
        self.assertEqual([e["message"] for e in server.pixel_room["events"] if e["kind"] == "game"], before)     # a kick is silent

    def test_friction_slows_the_ball_to_a_stop(self):
        game = self.begin(2)
        game["ball"].update(x=server.GAME_WIDTH / 2, y=.55, vx=200, vy=0)
        game["ball_at"] = self.clock
        self.roll(2)
        self.assertEqual(game["ball"]["vx"], 0)
        stopped = game["ball"]["x"]
        self.assertLess(stopped, 500)
        self.roll(1)
        self.assertEqual(game["ball"]["x"], stopped)

    def test_a_goal_scores_for_the_right_team_and_resets_the_ball(self):
        game = self.begin(2)
        ball = game["ball"]
        ball.update(x=server.GAME_WIDTH - server.BALL_GOAL_AT - 2, y=.55, vx=200, vy=0)
        game["ball_at"] = self.clock
        self.advance(.1)
        self.assertEqual(game["team_score"], {"blue": 1, "orange": 0})
        self.assertEqual(ball["vx"], 0)
        self.assertGreater(game["goal_until"], self.clock)
        self.assertIn("GOAL for 🔵 Blue", [e["message"] for e in server.pixel_room["events"] if e["kind"] == "game"][-1])
        self.advance(.5)                     # the ball rests in the goal: no second goal
        self.assertEqual(game["team_score"], {"blue": 1, "orange": 0})
        self.advance(server.BALL_GOAL_PAUSE)
        self.assertEqual(game["ball"]["x"], server.GAME_WIDTH / 2)
        self.assertEqual(game["ball"]["y"], .55)
        self.assertEqual(len([e for e in server.pixel_room["events"] if "GOAL" in e.get("message", "")]), 1)

    def test_orange_scores_in_the_left_goal(self):
        game = self.begin(2)
        ball = game["ball"]
        ball.update(x=server.BALL_GOAL_AT + 2, y=.55, vx=-200, vy=0)
        game["ball_at"] = self.clock
        self.advance(.1)
        self.assertEqual(game["team_score"], {"blue": 0, "orange": 1})
        self.assertIn("GOAL for 🟠 Orange", [e["message"] for e in server.pixel_room["events"] if e["kind"] == "game"][-1])

    def test_the_team_with_more_goals_wins_and_every_player_is_paid(self):
        game = self.begin(3)
        seats = [self.seat(k) for k in self.kids]
        game["team_score"] = {"blue": 2, "orange": 1}
        self.advance(server.BALL_SECONDS)
        self.assertEqual(game["phase"], "results")
        self.assertIn("Mia and Alex", game["message"])
        self.assertEqual(set(game["rewards"]), set(seats))
        for seat in seats:
            won = game["teams"][seat] == "blue"
            self.assertEqual(game["rewards"][seat]["won"], won)
        for kid, seat in zip(self.kids, seats):
            entry = server.pixel_entry(kid)
            self.assertEqual(entry["coins"], server.pixel.COINS_ROUND + (server.pixel.COINS_WIN if game["teams"][seat] == "blue" else 0))
            self.assertEqual(len(entry["gifts"]), 1)
            self.assertIn("play_ball", entry["badges"])
        self.assertEqual(server.hang_meter()["points"], 6)

    def test_a_draw_shares_the_win(self):
        game = self.begin(2)
        seats = [self.seat(k) for k in self.kids[:2]]
        game["team_score"] = {"blue": 2, "orange": 2}
        self.advance(server.BALL_SECONDS)
        self.assertEqual(game["phase"], "results")
        self.assertIn("Draw", game["message"])
        self.assertTrue(all(game["rewards"][s]["won"] for s in seats))

    def test_a_player_leaving_mid_round_is_dropped_and_the_round_goes_on(self):
        game = self.begin(3)
        gone = self.seat(self.kids[2])
        self.advance(3)
        self.do(self.kids[2], "leave")
        self.assertEqual(game["phase"], "playing")
        self.assertNotIn(gone, game["joined"])
        self.advance(server.BALL_SECONDS)
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
