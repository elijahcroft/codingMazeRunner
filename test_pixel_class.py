"""The class side of the Hang out: what the teacher sees and can do while games run."""
import unittest
from unittest.mock import patch

import server


class TeacherAndGames(unittest.TestCase):
    def setUp(self):
        self.saved = server.pixel_room, server.players, server.pixel_class, server.pixel_feed
        server.pixel_room = dict(server.room_empty(), open=True, words=False)
        server.players = {}
        server.pixel_class = {"open": 3}
        server.pixel_feed = []
        self.clock = 1000.
        for name, thing in (("time", patch.object(server.time, "time", side_effect=lambda: self.clock)),
                            ("save", patch.object(server, "pixel_save_soon"))):
            thing.start()
            self.addCleanup(thing.stop)
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

    def game(self, kind="tag"):
        self.assertTrue(server.room_do(self.kids[0], {"what": "game", "action": "create", "kind": kind})["ok"])
        self.assertTrue(server.room_do(self.kids[1], {"what": "game", "action": "join"})["ok"])
        self.assertTrue(server.room_do(self.kids[0], {"what": "game", "action": "start"})["ok"])

    def test_the_teacher_sees_the_game_and_can_end_it_with_no_prizes(self):
        self.game("tag")
        room = server.pixel_overview()["room"]
        self.assertEqual(room["game"], {"kind": "tag", "phase": "playing", "count": 2, "left": server.GAME_ROUND_SECONDS})
        coins = [server.pixel_entry(k)["coins"] for k in self.kids]
        self.assertEqual(server.pixel_teacher({"action": "end_game"}), {"ok": True})
        self.assertEqual(server.pixel_room["game"]["phase"], "results")
        self.assertEqual(server.pixel_room["game"]["rewards"], {})
        self.assertEqual([server.pixel_entry(k)["coins"] for k in self.kids], coins)
        self.assertIsNone(server.pixel_overview()["room"]["game"])     # a round that's over isn't "on"

    def test_a_code_race_for_everyone_waits_for_a_game_but_not_for_its_results(self):
        self.game("tag")
        out = server.pixel_teacher({"action": "code_race"})
        self.assertIn("End this game", out["error"])
        server.pixel_teacher({"action": "end_game"})
        out = server.pixel_teacher({"action": "code_race"})
        self.assertEqual(out, {"ok": True, "count": 3})
        self.assertEqual(server.pixel_room["game"]["kind"], "code")
        self.assertEqual(server.pixel_room["game"]["phase"], "lobby")

    def test_the_teacher_sees_where_each_student_is_and_what_they_are_doing(self):
        server.room_do(self.kids[2], {"what": "move", "name": "dance"})
        self.game("tag")
        people = server.pixel_overview()["room"]["people"]
        self.assertEqual(set(people), {"Mia", "Ben", "Alex"})
        self.assertEqual(people["Alex"]["doing"], "💃 Dancing")
        self.assertEqual(people["Mia"]["doing"], "🎮 In a game")
        self.assertEqual(people["Mia"]["where"], "park")

    def test_ending_when_no_game_is_on_does_nothing(self):
        self.assertEqual(server.pixel_teacher({"action": "end_game"}), {"ok": True})
        self.assertIsNone(server.pixel_room["game"])


if __name__ == "__main__":
    unittest.main()
