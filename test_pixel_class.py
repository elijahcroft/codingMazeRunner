"""The class side of the Hang out: what the teacher sees and can do while games run."""
import unittest
from unittest.mock import patch

import pixel
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

    def spots(self):
        return [s for s in server.pixel_room["here"].values() if not s["loc"]]

    def test_a_whole_class_arriving_together_is_spread_out_not_one_heap(self):
        for i in range(22):
            self.kid(f"Kid{i}")
        here = self.spots()
        self.assertEqual(len(here), 25)
        self.assertTrue(all(0 < s["x"] < server.hang_width() and 0 <= s["y"] <= 1 for s in here))
        gaps = [min(server.game_distance(a, b) for b in here if b is not a) for a in here]
        self.assertGreaterEqual(min(gaps), 30)
        self.assertEqual(len({(s["x"], s["y"]) for s in here}), 25)
        # The first few still start together in the Park, where the class begins.
        self.assertTrue(all(s["x"] < pixel.PLACE_W for s in here[:5]))

    def test_a_small_group_gets_more_room_because_their_pals_are_drawn_bigger(self):
        here = self.spots()
        gaps = [min(server.game_distance(a, b) for b in here if b is not a) for a in here]
        self.assertGreaterEqual(min(gaps), 48)

    def test_jumping_to_a_place_finds_a_free_spot_there(self):
        for kid in self.kids[:2]:
            self.assertEqual(server.room_do(kid, {"what": "go", "name": "beach"}), {"ok": True})
        a, b = (server.pixel_room["here"][k["id"]] for k in self.kids[:2])
        left = server.hang_places().index("beach") * pixel.PLACE_W
        for s in (a, b):
            self.assertTrue(left <= s["x"] < left + pixel.PLACE_W)
        self.assertGreaterEqual(server.game_distance(a, b), 30)

    def jobs(self, kid, keys=None):
        jobs = server.day_jobs(server.pixel_entry(kid))
        if keys:
            jobs["keys"] = keys
        return jobs

    def seat_of(self, kid):
        return server.pixel_room["here"][kid["id"]]["seat"]

    def test_todays_jobs_are_the_same_for_the_class_and_new_each_day(self):
        mia, ben = self.kids[:2]
        today = self.jobs(mia)["keys"]
        self.assertEqual(len(set(today)), 3)
        self.assertEqual(self.jobs(ben)["keys"], today)
        self.assertTrue(set(today) <= set(server.DAY_JOBS))
        days = {tuple(today)}
        for day in range(1, 6):
            self.clock = 1000. + day * 86400
            days.add(tuple(self.jobs(mia)["keys"]))
        self.assertGreater(len(days), 1)
        self.assertEqual(self.jobs(mia)["have"], {})        # a new day starts from nothing

    def test_a_job_pays_when_done_and_all_three_open_a_gift_box(self):
        mia = self.kids[0]
        entry = server.pixel_entry(mia)
        self.jobs(mia, ["catch", "clap", "visit"])
        coins, gifts, meter = entry["coins"], len(entry["gifts"]), server.hang_meter()["points"]
        server.day_job(mia, "catch")
        server.day_job(mia, "catch")
        self.assertEqual(entry["coins"], coins)                          # 2 of 3 stars: not yet
        server.day_job(mia, "catch")
        self.assertEqual(entry["coins"], coins + server.DAY_JOB_COINS)
        server.day_job(mia, "catch")                                      # a 4th star changes nothing
        self.assertEqual(self.jobs(mia)["have"]["catch"], 3)
        server.day_job(mia, "gem")                                        # not one of today's jobs
        self.assertNotIn("gem", self.jobs(mia)["have"])
        server.day_job(mia, "clap")
        self.assertFalse(self.jobs(mia)["paid"])
        server.day_job(mia, "visit")
        jobs = self.jobs(mia)
        self.assertTrue(jobs["paid"])
        self.assertEqual(len(entry["gifts"]), gifts + 1)
        self.assertEqual(entry["gifts"][-1], jobs["gift"])
        self.assertIn(jobs["gift"], pixel.BOX_GIFTS)
        self.assertEqual(server.hang_meter()["points"], meter + 2)
        view = server.room_view(mia, -1)["jobs"]
        self.assertEqual([j["have"] == j["need"] for j in view["list"]], [True] * 3)
        self.assertTrue(view["done"])

    def test_with_every_box_gift_owned_all_three_pay_coins_instead(self):
        mia = self.kids[0]
        entry = server.pixel_entry(mia)
        entry["gifts"] = list(pixel.BOX_GIFTS)
        self.jobs(mia, ["clap", "visit", "code"])
        coins = entry["coins"]
        for key in ("clap", "visit", "code"):
            server.day_job(mia, key)
        self.assertEqual(entry["coins"], coins + 3 * server.DAY_JOB_COINS + server.DAY_JOBS_ALL_COINS)

    def test_high_fives_count_different_friends(self):
        mia, ben, alex = self.kids
        self.jobs(mia, ["five", "clap", "visit"])
        self.assertTrue(server.room_do(mia, {"what": "five", "seat": self.seat_of(ben)})["ok"])
        self.clock += 2     # past the high-five gap, well before anyone counts as away
        server.room_do(mia, {"what": "five", "seat": self.seat_of(ben)})
        self.assertEqual(self.jobs(mia)["have"]["five"], 1)               # Ben again doesn't count
        self.clock += 2     # past the high-five gap, well before anyone counts as away
        server.room_do(mia, {"what": "five", "seat": self.seat_of(alex)})
        self.assertEqual(self.jobs(mia)["have"]["five"], 2)

    def test_visiting_counts_a_friends_home_not_your_own(self):
        mia, ben = self.kids[:2]
        self.jobs(mia, ["visit", "clap", "code"])
        server.room_do(mia, {"what": "home"})
        self.assertNotIn("visit", self.jobs(mia)["have"])
        server.room_do(mia, {"what": "home", "out": True})
        server.room_do(mia, {"what": "home", "seat": self.seat_of(ben)})
        self.assertEqual(self.jobs(mia)["have"]["visit"], 1)

    def test_the_projector_shows_the_class_jobs_and_the_feed_cheers_all_three(self):
        mia = self.kids[0]
        keys = self.jobs(mia)["keys"]
        self.assertEqual(server.room_view(None, -1)["class_jobs"], [server.DAY_JOBS[k][:2] for k in keys])
        for key in keys:
            for _ in range(server.DAY_JOBS[key][2]):
                server.day_job(mia, key, who=f"friend{_}" if key == "five" else None)
        self.assertEqual(server.pixel_feed[-1]["text"], "🎯 Mia did all of today's jobs!")

    def test_the_teacher_sees_how_many_jobs_each_student_has_done(self):
        mia = self.kids[0]
        key = self.jobs(mia)["keys"][0]
        for i in range(server.DAY_JOBS[key][2]):
            server.day_job(mia, key, who=f"friend{i}")
        rows = {r["name"]: r["jobs"] for r in server.pixel_overview()["students"]}
        self.assertEqual(rows, {"Mia": 1, "Ben": 0, "Alex": 0})

    def test_every_day_has_a_coding_job(self):
        mia = self.kids[0]
        for day in range(60):
            self.clock = 1000. + day * 86400
            keys = self.jobs(mia)["keys"]
            self.assertEqual(len(set(keys)), 3)
            self.assertTrue(set(keys) & set(server.CODING_JOBS), keys)
            self.assertEqual([j[1] for j in server.room_view(None, -1)["class_jobs"]], [server.DAY_JOBS[k][1] for k in keys])

    def test_with_every_star_the_coding_job_is_the_code_race(self):
        mia = self.kids[0]
        server.pixel_entry(mia)["solved"].update({k: [True] * 3 for k in pixel.LEVEL_ORDER})
        for day in range(30):
            self.clock = 1000. + day * 86400
            keys = self.jobs(mia)["keys"]
            self.assertNotIn("star", keys)
            self.assertIn("code", keys)

    def test_earning_a_mission_star_counts(self):
        mia = self.kids[0]
        self.jobs(mia, ["star", "clap", "visit"])
        level = pixel.LEVEL_BY_KEY["h1"]
        out = pixel.run_level(level, level["reference"], server.pixel_pal(server.pixel_entry(mia)))
        self.assertTrue(server.pixel_record(mia, "h1", level["reference"], out)["gained"])
        self.assertEqual(self.jobs(mia)["have"]["star"], 1)

    def test_the_teacher_page_lists_todays_jobs(self):
        keys = self.jobs(self.kids[0])["keys"]
        self.assertEqual(server.pixel_overview()["room"]["jobs"], [" ".join(server.DAY_JOBS[k][:2]) for k in keys])

    def test_no_gem_job_once_every_gem_is_found(self):
        mia = self.kids[0]
        server.pixel_entry(mia)["found"] = list(pixel.HANG_FINDS)
        for day in range(10):
            self.clock = 1000. + day * 86400
            self.assertNotIn("gem", self.jobs(mia)["keys"])
            self.assertEqual(len(self.jobs(mia)["keys"]), 3)

    def test_starting_a_game_tells_everyone_which_game_and_how_to_join(self):
        server.room_do(self.kids[0], {"what": "game", "action": "create", "kind": "dance"})
        said = [e["message"] for e in server.pixel_room["events"] if e["kind"] == "game"][-1]
        self.assertEqual(said, "🎮 Mia started Copy the dance! Tap the yellow bar above to join.")

    def test_go_to_a_friend_lands_next_to_them_and_not_on_them(self):
        mia, ben, alex = self.kids
        friend = server.pixel_room["here"][alex["id"]]
        friend["x"] = 700
        self.assertEqual(server.room_do(mia, {"what": "go", "seat": friend["seat"]}), {"ok": True})
        me = server.pixel_room["here"][mia["id"]]
        self.assertLessEqual(abs(me["x"] - 700), 90)
        self.assertGreaterEqual(server.game_distance(me, friend), 30)
        server.room_do(ben, {"what": "home"})                                      # from a home, out next to them
        self.assertEqual(server.room_do(ben, {"what": "go", "seat": friend["seat"]}), {"ok": True})
        self.assertEqual(server.pixel_room["here"][ben["id"]]["loc"], 0)
        server.room_do(alex, {"what": "home"})
        self.assertIn("isn't outside", server.room_do(mia, {"what": "go", "seat": friend["seat"]})["error"])

    def test_ending_when_no_game_is_on_does_nothing(self):
        self.assertEqual(server.pixel_teacher({"action": "end_game"}), {"ok": True})
        self.assertIsNone(server.pixel_room["game"])


if __name__ == "__main__":
    unittest.main()
