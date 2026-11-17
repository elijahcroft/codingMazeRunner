"""The class projector never misses a big moment, even while Auto is in a home.

The server sends the class screen a short list of class-wide moments (My Move,
a show, a star shower, a party, a photo, a game start, a Pal ball goal) whatever
place it is watching. Students' screens stay filtered to their own place.
"""
import unittest
from unittest.mock import patch

import server
from test_pixel_fun import Fun

MOVE = {"steps": [{"do": "jump", "ms": 650}, {"do": "cheer", "ms": 500}],
        "title": "Moon Hop", "loop": False, "big": False, "actions": 2}


class ProjectorMoments(Fun):
    def home(self, kid):
        """Send a student home and return the place the projector would watch."""
        self.assertTrue(self.do(kid, "home")["ok"])
        return self.spot(kid)["loc"]

    def moments(self, after, home):
        return server.room_view(None, after, home)["events"]

    def kinds(self, after, home):
        return [e["kind"] for e in self.moments(after, home)]

    def test_a_my_move_outside_reaches_the_projector_in_a_home(self):
        home = self.home(self.mia)
        self.entry(self.ben)["move"] = MOVE
        after = server.pixel_room["seq"]
        self.assertTrue(self.do(self.ben, "mymove")["ok"])
        events = self.moments(after, home)
        self.assertEqual([e["kind"] for e in events], ["mymove"])
        self.assertEqual((events[0]["by"], events[0]["seat"]), ("Ben", self.spot(self.ben)["seat"]))
        self.assertEqual(events[0]["loc"], 0)          # it happened outside, not in the watched home

    def test_a_student_in_the_home_does_not_get_the_outside_move(self):
        home = self.home(self.mia)
        self.entry(self.ben)["move"] = MOVE
        after = server.pixel_room["seq"]
        self.assertTrue(self.do(self.ben, "mymove")["ok"])
        self.assertEqual(self.view(self.mia, after, home)["events"], [])
        self.assertIn("mymove", self.kinds(after, home))       # only the class screen gets it

    def test_a_star_shower_and_a_class_photo_reach_the_projector(self):
        home = self.home(self.mia)
        after = server.pixel_room["seq"]
        server.room_start_shower()
        server.class_photo()
        kinds = self.kinds(after, home)
        self.assertIn("shower", kinds)
        self.assertIn("photo", kinds)
        # The pals walking into rows and the photo's own message do not leak into the home.
        self.assertNotIn("move", kinds)
        self.assertEqual(self.view(self.mia, after, home)["events"], [])

    def test_ordinary_events_stay_in_their_own_place(self):
        home = self.home(self.mia)
        after = server.pixel_room["seq"]
        self.do(self.ben, "move", name="wave")
        self.do(self.ben, "say", text="Hello!")
        kinds = self.kinds(after, home)
        self.assertNotIn("move", kinds)
        self.assertNotIn("say", kinds)
        self.assertEqual(kinds, [])

    def test_a_class_party_is_a_moment(self):
        home = self.home(self.mia)
        after = server.pixel_room["seq"]
        server.hang_fill(server.pixel.party_goal(0))
        self.assertIn("party", self.kinds(after, home))

    def test_a_game_start_is_tagged_for_the_projector_camera(self):
        home = self.home(self.mia)
        after = server.pixel_room["seq"]
        self.assertTrue(self.do(self.ben, "game", action="create", kind="tag")["ok"])
        events = self.moments(after, home)
        start = next(e for e in events if e["kind"] == "game")
        self.assertEqual(start["moment"], "game")
        self.assertEqual(start["focus"], self.spot(self.ben)["seat"])

    def test_the_projector_is_not_sent_another_place_s_ordinary_walk(self):
        home = self.home(self.mia)
        after = server.pixel_room["seq"]
        self.do(self.ben, "walk", x=250, y=.5)
        self.assertEqual(self.kinds(after, home), [])


class BallGoalMoments(unittest.TestCase):
    def setUp(self):
        self.saved = server.pixel_room, server.players, server.pixel_class, server.pixel_feed
        server.pixel_room = dict(server.room_empty(), open=True, words=False)
        server.players = {}
        server.pixel_class = {"open": 3}
        server.pixel_feed = []
        self.clock = 1000.
        for p in (patch.object(server.time, "time", side_effect=lambda: self.clock),
                  patch.object(server, "pixel_save_soon"),
                  patch.object(server, "day_job")):
            p.start()
            self.addCleanup(p.stop)
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

    def do(self, p, action, **more):
        return server.room_do(p, dict(what="game", action=action, **more))

    def advance(self, seconds):
        self.clock += seconds
        for spot in server.pixel_room["here"].values():
            spot["seen"] = self.clock
        server.room_keep_up()

    def begin(self, count=2):
        self.assertTrue(self.do(self.kids[0], "create", kind="ball")["ok"])
        for kid in self.kids[1:count]:
            self.assertTrue(self.do(kid, "join")["ok"])
        self.assertTrue(self.do(self.kids[0], "start")["ok"])
        return server.pixel_room["game"]

    def home(self, kid):
        self.assertTrue(server.room_do(kid, {"what": "home"})["ok"])
        return server.pixel_room["here"][kid["id"]]["loc"]

    def test_a_goal_is_a_moment_the_projector_gets_from_a_home(self):
        game = self.begin(2)
        home = self.home(self.kids[2])
        after = server.pixel_room["seq"]
        ball = game["ball"]
        ball.update(x=server.GAME_WIDTH - server.BALL_GOAL_AT - 2, y=.55, vx=200, vy=0)
        game["ball_at"] = self.clock
        self.advance(.1)
        goal = [e for e in server.pixel_room["events"] if "GOAL" in e.get("message", "")][-1]
        self.assertEqual(goal["moment"], "goal")
        self.assertIn("x", goal)
        self.assertIn("game", [e["kind"] for e in server.room_view(None, after, home)["events"]])


if __name__ == "__main__":
    unittest.main()
