"""Code race: a Hang out game where everyone codes the same little job."""
import unittest
from unittest.mock import patch

import pixel
import server


class Jobs(unittest.TestCase):
    def test_every_answer_solves_its_job(self):
        for tier in pixel.RACE_JOBS:
            for job in tier:
                self.assertTrue(pixel.race_check(job, job["answer"])["ok"], job["job"])

    def test_loop_jobs_need_a_loop(self):
        for tier in pixel.RACE_JOBS[1:]:
            for job in tier:
                self.assertGreaterEqual(job.get("loops", 0), 1, job["job"])
        job = pixel.RACE_JOBS[1][0]
        out = pixel.race_check(job, "jump()\n" * 5)
        self.assertFalse(out["ok"])
        self.assertIn("loop", out["message"])

    def test_misses_say_what_happened(self):
        job = pixel.RACE_JOBS[0][0]
        self.assertIn("🦘 🦘 🦘", pixel.race_check(job, "jump()\n" * 3)["message"])
        self.assertIn("anything", pixel.race_check(job, "")["message"])
        bug = pixel.race_check(job, "jmp()")
        self.assertEqual(bug["line"], 1)
        self.assertIn("jump()", bug["message"])
        self.assertIn("Code race uses", pixel.race_check(job, "right(3)")["message"])

    def test_said_words_are_checked_without_fuss_over_case(self):
        job = pixel.RACE_JOBS[0][2]
        self.assertTrue(pixel.race_check(job, 'say("hello")\njump()')["ok"])
        self.assertFalse(pixel.race_check(job, 'say("Bye")\njump()')["ok"])


class Race(unittest.TestCase):
    def setUp(self):
        self.saved = server.pixel_room, server.players, server.pixel_class, server.pixel_feed
        server.pixel_room = dict(server.room_empty(), open=True, words=False)
        server.players = {}
        server.pixel_class = {"open": 3}
        server.pixel_feed = []
        self.clock = 1000.
        for p in (patch.object(server.time, "time", side_effect=lambda: self.clock),
                  patch.object(server, "pixel_save_soon"),
                  patch.object(server.random, "choice", side_effect=lambda rows: rows[0])):
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

    def do(self, p, action, **extra):
        return server.room_do(p, dict(what="game", action=action, **extra))

    def seat(self, p):
        return server.pixel_room["here"][p["id"]]["seat"]

    def advance(self, seconds):
        self.clock += seconds
        for spot in server.pixel_room["here"].values():
            spot["seen"] = self.clock
        server.room_keep_up()

    def run_code(self, p, code):
        self.clock += server.CODE_RUN_GAP + .01      # just past the gap, whatever the float rounding
        return self.do(p, "run", code=code)

    def begin(self, count=2):
        self.assertTrue(self.do(self.kids[0], "create", kind="code")["ok"])
        for kid in self.kids[1:count]:
            self.assertTrue(self.do(kid, "join")["ok"])
        self.assertTrue(self.do(self.kids[0], "start")["ok"])
        return server.pixel_room["game"]

    def events(self, kind):
        return [e for e in server.pixel_room["events"] if e["kind"] == kind]

    def test_solving_plays_the_code_for_everyone_and_scores(self):
        game = self.begin()
        self.assertEqual(game["job"], pixel.RACE_JOBS[0][0])
        miss = self.run_code(self.kids[1], "jump()")
        self.assertFalse(miss["solved"])
        self.assertIn("🦘", miss["message"])
        coins = server.pixel_entry(self.kids[0])["coins"]
        out = self.run_code(self.kids[0], "jump()\njump()")
        self.assertTrue(out["solved"] and out["fastest"])
        self.assertEqual(server.pixel_entry(self.kids[0])["coins"], coins + server.CODE_SOLVE_COINS)
        move = self.events("mymove")[-1]
        self.assertEqual(move["seat"], self.seat(self.kids[0]))
        self.assertEqual([s["do"] for s in move["steps"]], ["jump", "jump"])
        again = self.run_code(self.kids[0], "jump()")                          # already solved: a run now is for the bonus
        self.assertTrue(again["solved"])
        self.assertFalse(again["bonus"])
        self.assertEqual(game["score"], {self.seat(self.kids[0]): 2})
        self.run_code(self.kids[1], "jump()\njump()")
        self.assertEqual(game["score"][self.seat(self.kids[1])], 1)
        self.assertTrue(game["pause_until"])                                   # everyone solved: the round ends
        self.assertEqual(game["reveal"], {"by": "Mia", "code": "jump()\njump()"})
        self.assertIn("error", self.run_code(self.kids[1], "jump()"))

    def test_after_solving_the_bonus_is_the_whole_job_two_times(self):
        game = self.begin()
        mia, ben = self.kids[:2]
        self.assertTrue(self.run_code(mia, "jump()\njump()")["solved"])
        coins, score = server.pixel_entry(mia)["coins"], dict(game["score"])
        miss = self.run_code(mia, "jump()\njump()\njump()")
        self.assertEqual((miss["solved"], miss["bonus"]), (True, False))
        self.assertIn("The bonus is 🦘 🦘 🦘 🦘", miss["message"])
        out = self.run_code(mia, "jump()\njump()\njump()\njump()")      # copying the lines again works
        self.assertEqual((out["solved"], out["bonus"]), (True, True))
        self.assertEqual(server.pixel_entry(mia)["coins"], coins + server.CODE_BONUS_COINS)
        self.assertEqual(game["score"], score)                                # no race points: the winner doesn't change
        self.assertEqual(self.events("mymove")[-1]["title"], "🌟 Bonus!")
        self.assertIn("Bonus done", self.run_code(mia, "jump()")["message"])  # once a job
        self.assertEqual(server.pixel_entry(mia)["coins"], coins + server.CODE_BONUS_COINS)
        self.assertFalse(self.run_code(ben, "jump()\njump()\njump()\njump()")["solved"])     # not solved yet: no bonus
        view = server.game_view(self.seat(mia))
        self.assertEqual(view["bonus"], [self.seat(mia)])
        self.assertEqual(view["bonus_icons"], "🦘 🦘 🦘 🦘")

    def test_a_loop_round_the_job_does_the_bonus_and_a_loop_job_still_needs_its_loop(self):
        game = self.begin()
        mia = self.kids[0]
        self.run_code(mia, "jump()\njump()")
        self.assertTrue(self.run_code(mia, "for i in range(2):\n    jump()\n    jump()")["bonus"])
        game["job"] = pixel.RACE_JOBS[1][0]                                   # Jump 5 times. Use a loop!
        game["solved"], game["bonus"] = [self.seat(mia)], []
        self.assertIn("loop", self.run_code(mia, "\n".join(["jump()"] * 10))["message"])
        self.assertTrue(self.run_code(mia, "for i in range(10):\n    jump()")["bonus"])

    def test_every_screen_sees_the_solve_and_the_claps(self):
        self.begin()
        after = server.pixel_room["seq"]
        self.run_code(self.kids[0], "jump()\njump()")
        server.room_do(self.kids[1], {"what": "clap", "seat": self.seat(self.kids[0])})
        for viewer in (self.kids[1], None):            # a classmate and the projector
            kinds = [e["kind"] for e in server.room_view(viewer, after)["events"]]
            self.assertIn("mymove", kinds)
            self.assertIn("clap", kinds)
        self.assertIn("error", server.room_do(self.kids[1], {"what": "move", "name": "dance"}))

    def test_three_rounds_then_the_top_coder_wins(self):
        game = self.begin()
        for tier in range(pixel.RACE_ROUNDS):
            self.assertEqual(game["round"], tier)
            self.assertIs(game["job"], pixel.RACE_JOBS[tier][0])
            self.run_code(self.kids[1], game["job"]["answer"])
            self.run_code(self.kids[0], game["job"]["answer"])
            self.advance(server.CODE_PAUSE)
        self.assertEqual(game["phase"], "results")
        self.assertIn("Ben", game["message"])
        reward = game["rewards"][self.seat(self.kids[1])]
        self.assertTrue(reward["won"])
        self.assertIn("play_code", server.pixel_entry(self.kids[1])["badges"])

    def test_time_runs_out_and_shows_one_way(self):
        game = self.begin()
        self.advance(server.CODE_SECONDS[0])
        self.assertEqual(game["reveal"], {"by": "", "code": game["job"]["answer"]})
        self.advance(server.CODE_PAUSE)
        self.assertEqual(game["round"], 1)
        self.assertFalse(game["pause_until"])

    def test_words_not_on_the_list_stay_private(self):
        game = self.begin()
        game["job"] = pixel.RACE_JOBS[0][2]
        rude = 'say("Hello!")\njump()\n# you smell'
        self.run_code(self.kids[0], rude)
        self.advance(server.CODE_SECONDS[0])
        self.assertEqual(game["reveal"]["code"], game["job"]["answer"])
        self.assertTrue(server.code_clean('say("Hello!")\njump()', game["job"]))
        self.assertFalse(server.code_clean('say("poo")\njump()', game["job"]))
        server.pixel_room["words"] = True
        self.assertTrue(server.code_clean('say("poo")\njump()', game["job"]))

    def test_say_lines_only_show_words_from_the_list_or_the_job(self):
        game = self.begin()
        game["job"] = {"job": "Say then jump", "want": ["say", "jump"], "answer": ""}
        self.run_code(self.kids[0], 'say("poo")\njump()')
        self.assertEqual([s["do"] for s in self.events("mymove")[-1]["steps"]], ["jump"])

    def test_the_teacher_can_start_one_for_everyone(self):
        self.assertTrue(server.pixel_teacher({"action": "code_race"})["ok"])
        game = server.pixel_room["game"]
        self.assertEqual((game["kind"], game["phase"]), ("code", "lobby"))
        self.assertEqual(game["joined"], [self.seat(k) for k in self.kids])
        self.assertIn("error", server.pixel_teacher({"action": "code_race"}))
        self.advance(server.GAME_JOIN_SECONDS)
        self.assertEqual(game["phase"], "playing")

    def test_late_friends_can_join_mid_race(self):
        game = self.begin()
        self.assertTrue(self.do(self.kids[2], "join")["ok"])
        self.assertIn(self.seat(self.kids[2]), game["joined"])
        self.advance(1)
        self.assertTrue(self.run_code(self.kids[2], game["job"]["answer"])["solved"])
        self.assertEqual(game["phase"], "playing")

    def test_pals_stay_put_and_the_view_has_the_job(self):
        game = self.begin()
        self.assertIn("error", server.room_do(self.kids[0], dict(what="walk", x=200, y=.5)))
        view = server.game_view(self.seat(self.kids[0]))
        self.assertEqual(view["job"]["job"], game["job"]["job"])
        self.assertEqual(view["job"]["icons"], "🦘 🦘")
        self.assertEqual(view["rounds"], pixel.RACE_ROUNDS)


if __name__ == "__main__":
    unittest.main()
