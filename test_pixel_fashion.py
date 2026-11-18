"""👗 Fashion show: a theme, a dress-up, one walk each and a kind ribbon for everyone."""
import unittest
from unittest.mock import patch

import server


class FashionShow(unittest.TestCase):
    def setUp(self):
        self.saved = server.pixel_room, server.players, server.pixel_class, server.pixel_feed
        server.pixel_room = dict(server.room_empty(), open=True, words=False)
        server.players = {}
        server.pixel_class = {"open": 3}
        server.pixel_feed = []
        self.clock = 1000.
        self.time = patch.object(server.time, "time", side_effect=lambda: self.clock)
        self.save = patch.object(server, "pixel_save_soon")
        self.job = patch.object(server, "day_job")
        self.job_mock = self.job.start()
        self.time.start()
        self.save.start()
        self.addCleanup(self.time.stop)
        self.addCleanup(self.save.stop)
        self.addCleanup(self.job.stop)
        self.addCleanup(self.restore)
        self.kids = []

    def restore(self):
        server.pixel_room, server.players, server.pixel_class, server.pixel_feed = self.saved

    def kid(self, name):
        p = {"id": "private-" + name, "name": name}
        server.players[p["id"]] = p
        server.pixel_entry(p)["solved"].update({k: [True] * 3 for k in ("a1", "a2", "a3")})
        self.assertTrue(server.room_do(p, {"what": "join"})["ok"])
        self.kids.append(p)
        return p

    def kids_named(self, count, prefix="Kid"):
        return [self.kid(f"{prefix}{i}") for i in range(count)]

    def do(self, p, action, **extra):
        return server.room_do(p, dict(what="game", action=action, **extra))

    def seat(self, p):
        return server.pixel_room["here"][p["id"]]["seat"]

    def begin(self, count=2, prefix="Kid"):
        kids = self.kids_named(count, prefix)
        self.assertTrue(self.do(kids[0], "create", kind="fashion")["ok"])
        for kid in kids[1:]:
            self.assertTrue(self.do(kid, "join")["ok"])
        self.assertTrue(self.do(kids[0], "start")["ok"])
        return kids, server.pixel_room["game"]

    def advance(self, seconds, step=.5):
        """Move the clock in small pieces, because each walk hands on to the next one."""
        left = seconds
        while left > 0:
            bit = min(step, left)
            self.clock += bit
            left -= bit
            for spot in server.pixel_room["here"].values():
                spot["seen"] = self.clock
            server.room_keep_up()

    def run_show(self, limit=130, step=.5):
        for _ in range(int(limit / step)):
            if server.pixel_room["game"]["phase"] == "results":
                return True
            self.advance(step)
        return server.pixel_room["game"]["phase"] == "results"

    def ready_all(self, kids):
        for kid in kids:
            self.assertTrue(self.do(kid, "ready")["ok"])
        return server.pixel_room["game"]

    def test_new_game_has_a_title_a_badge_and_8_to_12_themes(self):
        self.assertIn("fashion", server.GAME_KINDS)
        self.assertEqual(server.GAME_TITLES["fashion"], "Fashion show")
        self.assertEqual(set(server.GAME_KINDS), set(server.GAME_TITLES))
        self.assertEqual(server.GAME_RECAP_ICONS["fashion"], "👗")
        self.assertEqual(server.GAME_RECAP_NAMES["fashion"], "Fashion show")
        self.assertIn("play_fashion", server.PIXEL_BADGES)
        self.assertTrue(8 <= len(server.FASHION_THEMES) <= 12)
        self.assertEqual(len({theme["key"] for theme in server.FASHION_THEMES}), len(server.FASHION_THEMES))
        self.assertIn("Your own drawing!", [theme["words"] for theme in server.FASHION_THEMES])
        self.assertEqual(server.DAY_JOBS["fashion"][0], "👗")

    def test_dress_up_uses_the_wear_route_and_ready_starts_the_runway(self):
        kids, game = self.begin(3)
        self.assertEqual(game["phase"], "dressing")
        self.assertAlmostEqual(game["until"], self.clock + server.FASHION_DRESS_SECONDS)
        self.assertIn(game["theme"], server.FASHION_THEMES)
        self.assertIn("Theme:", [e["message"] for e in server.pixel_room["events"] if e["kind"] == "game"][-1])

        mia = kids[0]
        entry = server.pixel_entry(mia)
        entry["gifts"].append("party")
        self.assertTrue(server.room_do(mia, {"what": "wear", "slot": "hat", "item": "party"})["ok"])
        self.assertEqual(entry["wear"]["hat"], "party")
        self.assertEqual(server.pixel_room["here"][mia["id"]]["wear"]["hat"], "party")

        self.do(kids[0], "ready")
        self.assertIn(self.seat(kids[0]), game["ready"])
        self.assertEqual(game["phase"], "dressing")
        self.do(kids[1], "ready")
        self.assertEqual(game["phase"], "dressing")
        self.do(kids[2], "ready")
        self.assertEqual(game["phase"], "runway")
        self.assertEqual(game["walker"], self.seat(kids[0]))
        self.assertEqual(game["walk_len"], 6)

    def test_reactions_count_and_every_walker_gets_a_kind_ribbon(self):
        kids, game = self.begin(3)
        self.ready_all(kids)
        walker = game["walker"]
        watchers = [kid for kid in kids if self.seat(kid) != walker]
        self.assertIn("error", self.do(kids[0], "react", emoji="👏"))       # the walker cannot cheer for themself
        self.assertIn("error", self.do(watchers[0], "react", emoji="🎉"))
        self.assertTrue(self.do(watchers[0], "react", emoji="👏")["ok"])
        self.advance(.5)
        self.assertTrue(self.do(watchers[1], "react", emoji="😍")["ok"])
        self.advance(.5)
        self.assertTrue(self.do(watchers[1], "react", emoji="✨")["ok"])
        self.assertEqual(game["reactions"][walker], {"👏": 1, "😍": 1, "✨": 1})
        reaction_events = [e for e in server.pixel_room["events"] if e["kind"] == "react"]
        self.assertEqual([e["emoji"] for e in reaction_events], ["👏", "😍", "✨"])

        self.assertTrue(self.run_show(), game["phase"])
        self.assertEqual(game["phase"], "results")
        self.assertEqual(set(game["awards"]), {self.seat(kid) for kid in kids})
        for award in game["awards"].values():
            self.assertIn(award["key"], server.FASHION_AWARDS)
            self.assertEqual((award["icon"], award["name"]), server.FASHION_AWARDS[award["key"]])
        self.assertIn("kind ribbon", game["message"])
        self.assertIn(game["theme"]["words"], game["message"])
        for kid in kids:
            seat = self.seat(kid)
            reward = game["rewards"][seat]
            self.assertFalse(reward["won"])                    # no ranking and no losers
            self.assertEqual(reward["coins"], server.pixel.COINS_ROUND)
            self.assertIn("play_fashion", server.pixel_entry(kid)["badges"])
            self.assertEqual(server.pixel_entry(kid)["play_rounds"]["fashion"], 1)
            self.job_mock.assert_any_call(kid, "fashion")
        self.assertEqual(server.hang_meter()["points"], 6)

    def test_a_walker_who_leaves_is_skipped_and_the_show_finishes_for_the_rest(self):
        kids, game = self.begin(3)
        self.ready_all(kids)
        leaver = next(kid for kid in kids if self.seat(kid) == game["walker"])
        gone = self.seat(leaver)
        self.assertTrue(self.do(leaver, "leave")["ok"])
        self.assertEqual(game["phase"], "runway")
        self.assertNotIn(gone, game["joined"])
        self.assertNotEqual(game["walker"], gone)                # the next walker starts straight away
        self.assertTrue(self.run_show(), game["phase"])
        self.assertEqual(game["phase"], "results")
        self.assertEqual(set(game["rewards"]), {self.seat(kid) for kid in kids if kid is not leaver})
        self.assertNotIn(gone, game["awards"])
        self.assertNotIn(gone, game["rewards"])

    def test_late_joiners_wait_for_the_next_round(self):
        kids, game = self.begin(2)
        self.ready_all(kids)
        late = self.kid("Late")
        self.assertIn("error", self.do(late, "join"))
        self.assertNotIn(self.seat(late), game["joined"])
        self.assertEqual(game["phase"], "runway")

    def test_hidden_names_stay_secret_on_the_runway(self):
        kids, game = self.begin(2)
        self.assertTrue(server.room_do(kids[0], {"what": "hidename", "on": True})["ok"])
        self.ready_all(kids)
        said = [e["message"] for e in server.pixel_room["events"] if e["kind"] == "game" and "runway" in e.get("message", "")]
        self.assertTrue(any("Secret pal" in message for message in said), said)
        self.assertFalse(any(kids[0]["name"] in message for message in said), said)

    def test_wearing_your_own_drawing_gets_the_made_it_myself_ribbon(self):
        kids, game = self.begin(2)
        mia = kids[0]
        entry = server.pixel_entry(mia)
        entry["mywear"].append({"key": "my:1", "slot": "hat", "name": "My drawing",
                                "art": {"size": 8, "palette": ["#1b1530", "#ff8fc7"],
                                        "rows": [".pppp.", "pppppp", "p.pp.p", "pppppp"]}})
        self.assertTrue(server.room_do(mia, {"what": "wear", "slot": "hat", "item": "my:1"})["ok"])
        self.ready_all(kids)
        self.assertTrue(self.run_show(), game["phase"])
        self.assertEqual(game["awards"][self.seat(mia)]["key"], "own")

    def test_a_big_class_walks_in_three_seconds_each_and_finishes_under_two_minutes(self):
        kids, game = self.begin(25, "Big")
        self.assertEqual(game["walk_len"], 3)
        self.assertLessEqual(server.FASHION_DRESS_SECONDS + 25 * game["walk_len"], 120)
        self.ready_all(kids)
        self.assertEqual(game["phase"], "runway")
        self.assertLessEqual(game["until"] - self.clock, 75)
        self.assertTrue(self.run_show(limit=90), game["phase"])
        self.assertEqual(game["phase"], "results")
        self.assertEqual(len(game["awards"]), 25)
        self.assertEqual(len(game["rewards"]), 25)


if __name__ == "__main__":
    unittest.main()
