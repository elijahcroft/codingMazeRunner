"""🧰 Code chests: one in each place of the Hang out, opened by coding today's puzzle."""
import unittest
from unittest.mock import patch

import pixel
import server


class Puzzles(unittest.TestCase):
    def test_every_answer_opens_its_chest(self):
        for tier in pixel.CHEST_JOBS:
            for job in tier:
                self.assertTrue(pixel.race_check(job, job["answer"])["ok"], job["job"])

    def test_every_place_has_a_chest_and_a_puzzle(self):
        self.assertEqual(set(pixel.CHEST_SPOTS), set(pixel.HANG_WORLD))
        self.assertEqual(set(pixel.CHEST_TIER), set(pixel.HANG_WORLD))
        for place in pixel.HANG_WORLD:
            self.assertIn(pixel.chest_job(place, "2026-11-16"), pixel.CHEST_JOBS[pixel.CHEST_TIER[place]])

    def test_the_puzzle_is_the_same_all_day_and_changes_over_the_days(self):
        self.assertEqual(pixel.chest_job("night", "2026-11-16"), pixel.chest_job("night", "2026-11-16"))
        self.assertGreater(len({pixel.chest_job("night", f"2026-11-{d:02}")["job"] for d in range(1, 29)}), 1)

    def test_the_park_is_easiest(self):
        self.assertEqual(pixel.CHEST_TIER["park"], 0)
        self.assertEqual(min(pixel.CHEST_TIER.values()), 0)


class Chests(unittest.TestCase):
    def setUp(self):
        self.saved = server.pixel_room, server.players, server.pixel_class, server.pixel_feed
        server.pixel_room = dict(server.room_empty(), open=True, words=False)
        server.players = {}
        server.pixel_class = {"open": 3}
        server.pixel_feed = []
        self.clock = 1000.
        self.day = "2026-11-16"
        for p in (patch.object(server.time, "time", side_effect=lambda: self.clock),
                  patch.object(server.time, "strftime", side_effect=lambda fmt, t=None: self.day),
                  patch.object(server, "pixel_save_soon")):
            p.start()
            self.addCleanup(p.stop)
        self.addCleanup(self.restore)
        self.mia, self.ben = self.kid("Mia"), self.kid("Ben")

    def restore(self):
        server.pixel_room, server.players, server.pixel_class, server.pixel_feed = self.saved

    def kid(self, name):
        p = {"id": "private-" + name, "name": name}
        server.players[p["id"]] = p
        server.pixel_entry(p)["solved"].update({k: [True] * 3 for k in ("a1", "a2", "a3")})
        self.assertTrue(server.room_do(p, {"what": "join"})["ok"])
        return p

    def open_it(self, p, place, code=None):
        self.clock += server.CODE_RUN_GAP + .01
        code = pixel.chest_job(place, self.day)["answer"] if code is None else code
        return server.room_do(p, {"what": "chest", "place": place, "code": code})

    def test_a_wrong_answer_says_what_the_pal_did(self):
        out = self.open_it(self.mia, "park", "wave()\nwave()\nwave()\nwave()\nwave()\nwave()")
        self.assertTrue(out["ok"])
        self.assertFalse(out["open"])
        self.assertIn("The chest wants", out["message"])
        self.assertEqual(server.pixel_entry(self.mia)["chest_count"], 0)

    def test_the_answer_opens_it_pays_and_plays_for_everyone(self):
        coins = server.pixel_entry(self.mia)["coins"]
        out = self.open_it(self.mia, "park")
        self.assertTrue(out["open"])
        self.assertEqual(out["coins"], pixel.CHEST_COINS)
        self.assertGreaterEqual(server.pixel_entry(self.mia)["coins"], coins + pixel.CHEST_COINS)     # and maybe a 🎯 job
        self.assertEqual((out["today"], out["count"]), (1, 1))
        move = [e for e in server.pixel_room["events"] if e["kind"] == "mymove"]
        self.assertEqual(move[-1]["title"], "🧰 Opened a chest!")
        view = {c["place"]: c for c in server.pixel_state(self.mia)["hang"]["chests"]}
        self.assertTrue(view["park"]["open"])
        self.assertFalse(view["wedding"]["open"])
        self.assertFalse({c["place"]: c for c in server.pixel_state(self.ben)["hang"]["chests"]}["park"]["open"])

    def test_each_chest_opens_once_a_day_and_locks_again_tomorrow(self):
        self.assertTrue(self.open_it(self.mia, "park")["coins"])
        again = self.open_it(self.mia, "park")
        self.assertTrue(again["open"])
        self.assertNotIn("coins", again)
        self.assertEqual(server.pixel_entry(self.mia)["chest_count"], 1)
        self.day = "2026-11-17"
        self.assertFalse({c["place"]: c for c in server.pixel_state(self.mia)["hang"]["chests"]}["park"]["open"])
        self.assertTrue(self.open_it(self.mia, "park")["coins"])
        self.assertEqual(server.pixel_entry(self.mia)["chest_count"], 2)

    def test_a_place_the_class_has_not_opened_yet_has_no_chest(self):
        self.assertNotIn("space", server.hang_places())
        self.assertEqual(self.open_it(self.mia, "space")["error"], "bad")
        self.assertEqual(server.room_do(self.mia, {"what": "chest", "place": "nowhere", "code": "jump()"})["error"], "bad")

    def test_not_from_inside_a_home(self):
        self.assertTrue(server.room_do(self.mia, {"what": "home"})["ok"])
        self.assertEqual(self.open_it(self.mia, "park")["error"], "bad")

    def test_runs_wait_a_moment_between_them(self):
        self.open_it(self.mia, "wedding", "jump()")
        out = server.room_do(self.mia, {"what": "chest", "place": "wedding", "code": "jump()"})
        self.assertEqual(out["error"], "One moment...")

    def test_chests_count_towards_the_treasure_goals(self):
        self.assertNotIn("chestspark", server.pixel_owned(server.pixel_entry(self.mia)))
        server.pixel_entry(self.mia)["chest_count"] = 4
        self.open_it(self.mia, "park")
        self.assertIn("chestspark", server.pixel_owned(server.pixel_entry(self.mia)))
        self.assertNotIn("captain", server.pixel_owned(server.pixel_entry(self.mia)))

    def test_it_is_one_of_the_coding_jobs(self):
        self.assertIn("chest", server.CODING_JOBS)
        jobs = server.day_jobs(server.pixel_entry(self.mia))
        jobs["keys"][0] = "chest"
        self.open_it(self.mia, "park")
        self.assertEqual(jobs["have"].get("chest"), 1)

    def test_opening_every_chest_today_goes_on_the_projector(self):
        for place in server.hang_places():
            if place in pixel.CHEST_SPOTS:          # the ❄️ Snow Village has no chest
                self.assertTrue(self.open_it(self.mia, place)["open"], place)
        self.assertIn("Mia opened every chest today!", server.pixel_feed[-1]["text"])

    def test_the_first_to_open_a_chest_goes_on_the_projector(self):
        self.open_it(self.mia, "wedding")
        self.assertIn("Mia was first to code open the Wedding chest today!", server.pixel_feed[-1]["text"])
        self.open_it(self.ben, "wedding")
        self.assertEqual(len(server.pixel_feed), 1)

    def test_the_projector_sees_every_chest_and_how_many_opened_it(self):
        self.open_it(self.mia, "park")
        self.open_it(self.ben, "park")
        self.open_it(self.ben, "beach")
        chests = {c["place"]: c for c in server.room_view(None, -1)["chests"]}
        self.assertEqual((chests["park"]["count"], chests["beach"]["count"], chests["night"]["count"]), (2, 1, 0))
        self.assertEqual(chests["park"]["job"], pixel.chest_job("park", self.day)["job"])
        self.assertFalse(chests["park"]["open"])
        self.assertNotIn("chests", server.room_view(self.mia, -1))        # a student's chests come with their own state

    def test_the_teacher_sees_chests_per_student_and_today_s_puzzles(self):
        self.open_it(self.mia, "park")
        over = server.pixel_overview()
        self.assertEqual({s["name"]: s["chests"] for s in over["students"]}, {"Mia": 1, "Ben": 0})
        self.assertEqual([c[0] for c in over["room"]["chests"]], ["Park", "Wedding", "Beach", "Night"])
        self.assertEqual(over["room"]["chests"][0][2], 1)


if __name__ == "__main__":
    unittest.main()
