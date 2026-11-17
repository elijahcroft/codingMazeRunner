"""New small coding jobs in the Hang out, and the two new 🎯 Today's jobs."""
import unittest
from unittest.mock import patch

import pixel
import server


class NewCodingJobs(unittest.TestCase):
    def job(self, start):
        for tier in pixel.RACE_JOBS + pixel.CHEST_JOBS[-1:]:
            for job in tier:
                if job["job"].startswith(start):
                    return job
        self.fail(f"no job starting {start!r}")

    def test_every_answer_still_solves_its_job(self):
        for tier in pixel.RACE_JOBS + pixel.CHEST_JOBS[-1:]:
            for job in tier:
                with self.subTest(job["job"]):
                    self.assertTrue(pixel.race_check(job, job["answer"])["ok"], job["job"])

    def test_note_jobs_show_their_note_names_in_pictures_words_and_chips(self):
        job = self.job("Sing C, then E, then G.")
        self.assertEqual(pixel.race_icons(job["want"], job["notes"]), "🎵 C 🎵 E 🎵 G")
        self.assertEqual(pixel.race_words(job["want"], job["notes"]), "🎵 C, then 🎵 E, then 🎵 G")
        self.assertEqual(pixel.chest_chips(job), ['note("C")', 'note("E")', 'note("G")'])
        loop = self.job("Sing C 3 times.")
        self.assertEqual(pixel.race_icons(loop["want"], loop["notes"]), "🎵 C 🎵 C 🎵 C")
        self.assertEqual(pixel.chest_chips(loop), ['note("C")'])

    def test_a_wrong_note_says_which_note_to_change(self):
        out = pixel.race_check(self.job("Sing C, then E, then G."), 'note("C")\nnote("D")\nnote("G")')
        self.assertFalse(out["ok"])
        self.assertIn("Move 2 should be 🎵 E, but your pal sang 🎵 D.", out["message"])
        self.assertIn("Your pal did: 🎵 C, then 🎵 D, then 🎵 G.", out["message"])

    def test_too_few_notes_and_too_many_notes_say_the_count(self):
        job = self.job("Sing C, then E, then G.")
        self.assertIn("So close! Just one more: 🎵 G.", pixel.race_check(job, 'note("C")\nnote("E")')["message"])
        self.assertIn("1 too many", pixel.race_check(job, 'note("C")\nnote("E")\nnote("G")\nnote("C")')["message"])
        loop = self.job("Sing C 3 times.")
        self.assertIn("So close! Just one more: 🎵 C.", pixel.race_check(loop, 'note("C")\nnote("C")')["message"])
        too_many = pixel.race_check(loop, 'for i in range(4):\n    note("C")')["message"]
        self.assertIn("🎵 C 4 times", too_many)
        self.assertIn("Make the number in the loop smaller.", too_many)

    def test_a_note_job_with_a_loop_needs_its_loop(self):
        loop = self.job("Sing C 3 times.")
        self.assertIn("Now use a loop", pixel.race_check(loop, 'note("C")\nnote("C")\nnote("C")')["message"])

    def test_a_loop_in_a_loop_is_required_and_explained(self):
        job = self.job("Do 2 rounds of: jump 3 times, then cheer.")
        flat = "\n".join((["jump()"] * 3 + ["cheer()"]) * 2)
        out = pixel.race_check(job, flat)
        self.assertFalse(out["ok"])
        self.assertIn("loop in a loop", out["message"])
        one_loop = "for i in range(2):\n    jump()\n    jump()\n    jump()\n    cheer()"
        self.assertIn("loop in a loop", pixel.race_check(job, one_loop)["message"])
        self.assertTrue(pixel.race_check(job, job["answer"])["ok"])

    def test_the_bonus_repeats_the_notes_too(self):
        job = self.job("Sing C 3 times.")
        bonus = server.race_bonus(job)
        self.assertEqual(bonus["notes"], ["C"] * 6)
        twice = 'for i in range(3):\n    note("C")\nfor i in range(3):\n    note("C")'
        self.assertTrue(pixel.race_check(bonus, twice)["ok"])
        self.assertEqual(pixel.race_icons(bonus["want"], bonus["notes"]), "🎵 C 🎵 C 🎵 C 🎵 C 🎵 C 🎵 C")

    def test_the_word_job_says_it_in_one_bubble(self):
        job = self.job('Say "Hi" 3 times')
        self.assertTrue(pixel.race_check(job, job["answer"])["ok"])
        self.assertTrue(server.code_clean('say("Hi" * 3)', job))       # the class can see this solver's code
        out = pixel.race_check(job, 'say("Hi" * 2)')
        self.assertFalse(out["ok"])
        self.assertIn('Your pal said "HiHi".', out["message"])
        self.assertIn('"HiHiHi"', out["message"])
        chest = self.job('Say "Hi" 3 times in one bubble, then jump!')
        self.assertIn("HiHiHi", pixel.race_check(chest, 'say("Hi" * 2)\njump()')["message"])
        self.assertIn('say("Hi" * 3)', pixel.chest_chips(chest))

    def test_the_chest_view_sends_note_names_to_the_page(self):
        job = self.job("Sing C, then E, then G.")
        day = server.time.strftime("%Y-%m-%d", server.time.localtime(server.time.time()))
        entry = {"chests": {"day": day, "open": []}}
        with patch.object(server.pixel, "chest_job", return_value=job):
            view = {c["place"]: c for c in server.chests_view(entry)}
        self.assertEqual(view["park"]["icons"], "🎵 C 🎵 E 🎵 G")
        self.assertEqual(view["park"]["words"], "🎵 C, then 🎵 E, then 🎵 G")
        self.assertEqual(view["park"]["moves"], ['note("C")', 'note("E")', 'note("G")'])

    def test_the_hard_chest_note_tune_counts_the_notes_it_wants(self):
        job = self.job("Sing C, then E, then G. Do that 2 times")
        self.assertEqual(pixel.race_icons(job["want"], job["notes"]), "🎵 C 🎵 E 🎵 G 🎵 C 🎵 E 🎵 G")
        self.assertEqual(pixel.race_words(job["want"], job["notes"]), "🎵 C, then 🎵 E, then 🎵 G. Do that 2 times")
        out = pixel.race_check(job, 'note("C")\nnote("E")\nnote("G")')
        self.assertFalse(out["ok"])
        self.assertIn("3 more to go", out["message"])
        self.assertIn("🎵 C", out["message"])


class RaceView(unittest.TestCase):
    """The Code race page gets its pictures and note names from game_view."""

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
        self.mia, self.ben = (self.kid(name) for name in ("Mia", "Ben"))

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

    def test_the_bar_and_the_bonus_show_note_names(self):
        self.assertTrue(self.do(self.mia, "create", kind="code")["ok"])
        self.assertTrue(self.do(self.ben, "join")["ok"])
        self.assertTrue(self.do(self.mia, "start")["ok"])
        game = server.pixel_room["game"]
        game["job"] = NewCodingJobs.job(self, "Sing C, then E, then G.")
        view = server.game_view(self.seat(self.mia))
        self.assertEqual(view["job"]["icons"], "🎵 C 🎵 E 🎵 G")
        self.assertEqual(view["job"]["chips"], ['note("C")', 'note("E")', 'note("G")'])
        self.assertEqual(view["bonus_icons"], "🎵 C 🎵 E 🎵 G 🎵 C 🎵 E 🎵 G")
        out = self.do(self.mia, "run", code=game["job"]["answer"])
        self.assertTrue(out["solved"])
        move = [e for e in server.pixel_room["events"] if e["kind"] == "mymove"][-1]
        self.assertEqual([(s["do"], s.get("name")) for s in move["steps"]],
                         [("note", "C"), ("note", "E"), ("note", "G")])


class TodayJobs(unittest.TestCase):
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
        server.pixel_entry(p)["solved"].update({k: [True] * 3 for k in ("a1", "a2", "a3")})
        self.assertTrue(server.room_do(p, {"what": "join"})["ok"])
        return p

    def do(self, p, action, **extra):
        return server.room_do(p, dict(what="game", action=action, **extra))

    def seat(self, p):
        return server.pixel_room["here"][p["id"]]["seat"]

    def jobs(self, kid, keys):
        jobs = server.day_jobs(server.pixel_entry(kid))
        jobs["keys"] = keys
        return jobs

    def begin(self, kind, count=2):
        self.assertTrue(self.do(self.kids[0], "create", kind=kind)["ok"])
        for kid in self.kids[1:count]:
            self.assertTrue(self.do(kid, "join")["ok"])
        self.assertTrue(self.do(self.kids[0], "start")["ok"])
        return server.pixel_room["game"]

    def move(self, p, x, y):
        return server.room_do(p, dict(what="walk", x=x, y=y))

    def advance(self, seconds):
        self.clock += seconds
        for spot in server.pixel_room["here"].values():
            spot["seen"] = self.clock
        server.room_keep_up()

    def near(self, kid):
        game, seat = server.pixel_room["game"], self.seat(kid)
        motion = game["motion"][seat]
        apple = {"id": 900 + seat, "x": round(motion["x"] + 40, 1), "y": motion["y"], "gold": False}
        game["apples"][0] = apple
        return apple

    def goal(self):
        game = server.pixel_room["game"]
        game["ball"].update(x=server.GAME_WIDTH - server.BALL_GOAL_AT - 2, y=.55, vx=200, vy=0)
        game["ball_at"] = self.clock
        self.advance(.1)

    def test_the_new_jobs_are_offered_with_plain_words(self):
        for key, icon, words, need in (("apples", "🍎", "Grab 5 apples in Apple grab", 5),
                                       ("ball", "⚽", "Score a goal in Pal ball", 1)):
            with self.subTest(key):
                self.assertEqual(server.DAY_JOBS[key][:3], (icon, words, need))
                self.assertIn("friend", server.DAY_JOBS[key][3])
                self.assertIn("join", server.DAY_JOBS[key][3])

    def test_grab_five_apples_counts_each_one_and_pays_once(self):
        mia, ben = self.kids[:2]
        jobs = self.jobs(mia, ["apples", "clap", "visit"])
        coins = server.pixel_entry(mia)["coins"]
        game = self.begin("apples")
        far = game["motion"][self.seat(ben)]        # keep Ben away, so only Mia grabs the test apples
        far.update(x=600, y=.9, tx=600, ty=.9)
        server.pixel_room["here"][ben["id"]].update(x=600, y=.9)
        for i in range(5):
            apple = self.near(mia)
            self.move(mia, apple["x"], apple["y"])
            self.advance(.6)
            self.assertEqual(jobs["have"].get("apples"), i + 1)
        self.assertEqual(server.pixel_entry(mia)["coins"], coins + server.DAY_JOB_COINS)
        apple = self.near(mia)
        self.move(mia, apple["x"], apple["y"])
        self.advance(.6)
        self.assertEqual(jobs["have"]["apples"], 5)              # the sixth apple changes nothing
        self.assertEqual(server.pixel_entry(mia)["coins"], coins + server.DAY_JOB_COINS)

    def test_a_goal_counts_for_the_whole_scoring_team_and_pays_once(self):
        mia, ben, alex = self.kids
        jobs = {kid["id"]: self.jobs(kid, ["ball", "clap", "visit"]) for kid in self.kids}
        coins = {kid["id"]: server.pixel_entry(kid)["coins"] for kid in self.kids}
        game = self.begin("ball", 3)
        blue = [kid for kid in self.kids if game["teams"][self.seat(kid)] == "blue"]
        orange = [kid for kid in self.kids if game["teams"][self.seat(kid)] == "orange"]
        self.assertEqual((len(blue), len(orange)), (2, 1))
        self.goal()
        for kid in blue:
            self.assertEqual(jobs[kid["id"]]["have"].get("ball"), 1)
            self.assertEqual(server.pixel_entry(kid)["coins"], coins[kid["id"]] + server.DAY_JOB_COINS)
        for kid in orange:
            self.assertNotIn("ball", jobs[kid["id"]]["have"])
            self.assertEqual(server.pixel_entry(kid)["coins"], coins[kid["id"]])
        self.advance(server.BALL_GOAL_PAUSE)
        self.goal()
        for kid in blue:                                          # paid once: the second goal changes nothing
            self.assertEqual(jobs[kid["id"]]["have"]["ball"], 1)
            self.assertEqual(server.pixel_entry(kid)["coins"], coins[kid["id"]] + server.DAY_JOB_COINS)


if __name__ == "__main__":
    unittest.main()
