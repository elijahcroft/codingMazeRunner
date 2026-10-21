import time
import unittest
from collections import deque

import cycles
import server


ROOKIE = """for step in range(100):
    if wall_ahead():
        turn_right()
    move()
"""

RIGHT_HAND = """while not at_goal():
    turn_right()
    while wall_ahead():
        turn_left()
    move()
"""


def fake_player(name="Tester"):
    return {
        "id": "test", "name": name, "color": "#1647d8",
        "world": 0, "maze": 0, "row": 1, "col": 1, "dir": 1,
        "best": {}, "chars": {}, "unlocked": {}, "seen": {}, "code": "",
    }


class ArenaTests(unittest.TestCase):
    def test_every_track_has_a_reachable_goal(self):
        for trial in (t for lg in server.RALLY_LEAGUES for t in lg["tracks"]):
            maze = trial["maze"]
            width = len(maze[0])
            self.assertTrue(all(len(row) == width for row in maze), trial["name"])
            start = server.find_start(maze)
            goal = next((r, c) for r, row in enumerate(maze)
                        for c, char in enumerate(row) if char == "G")
            queue, seen = deque([start]), {start}
            while queue:
                row, col = queue.popleft()
                for dr, dc in server.DIRS:
                    nxt = row + dr, col + dc
                    if nxt not in seen and maze[nxt[0]][nxt[1]] != "#":
                        seen.add(nxt)
                        queue.append(nxt)
            self.assertIn(goal, seen, trial["name"])

    def test_rookie_bot_gets_a_real_partial_win(self):
        result = server.run_arena(fake_player(), ROOKIE)
        self.assertEqual(result["score"]["solved"], 2)
        self.assertEqual([r["solved"] for r in result["results"]],
                         [True, False, True, False, False])

    def test_general_algorithm_clears_all_tracks(self):
        result = server.run_arena(fake_player(), RIGHT_HAND)
        self.assertEqual(result["score"]["solved"], 5)
        self.assertEqual(result["score"]["actions"], 342)
        self.assertTrue(all(r["solved"] for r in result["results"]))

    def test_syntax_error_is_friendly_and_safe(self):
        result = server.run_arena(fake_player(), "while True\n    move()")
        self.assertEqual(result["score"]["solved"], 0)
        for trial in result["results"]:
            self.assertIn("Syntax error", " ".join(trial["log"]))
            self.assertLessEqual(len(trial["trace"]), 1)

    def test_early_print_output_survives_a_long_run(self):
        result = server.run_arena(fake_player(), 'print("starting")\n' + RIGHT_HAND)
        for trial in result["results"]:
            self.assertIn("› starting", trial["log"])

    def test_a_weaker_later_run_does_not_erase_personal_best(self):
        player = fake_player()
        gold = server.run_arena(player, RIGHT_HAND)
        later = server.run_arena(player, ROOKIE)
        self.assertTrue(gold["new_best"])
        self.assertFalse(later["new_best"])
        self.assertEqual(later["best"]["solved"], 5)
        self.assertEqual(later["best"]["actions"], 342)

    def test_leaderboard_prioritizes_reliability(self):
        original = server.players
        try:
            gold, bronze = fake_player("Gold"), fake_player("Bronze")
            gold["id"], bronze["id"] = "g", "b"
            server.rally_entry(gold, "rookie")["best"] = {
                "solved": 5, "actions": 900, "chars": 100, "lines": 7}
            server.rally_entry(bronze, "rookie")["best"] = {
                "solved": 2, "actions": 1, "chars": 1, "lines": 1}
            server.players = {"b": bronze, "g": gold}
            self.assertEqual(server.arena_scoreboard()[0]["name"], "Gold")
        finally:
            server.players = original


def swap_hands(code):
    for a, b in (("turn_right", "turn_left"), ("wall_right", "wall_left")):
        code = code.replace(a, "@").replace(b, a).replace("@", b)
    return code


LEFT_HAND = swap_hands(RIGHT_HAND)

# A right-hand follower that looks sideways instead of turning to check.
SMART_RIGHT = """while not at_goal():
    if not wall_right():
        turn_right()
        move()
    elif not wall_ahead():
        move()
    else:
        turn_left()
"""

# Picks a hand once, from where the goal is, then follows it.
HAND_BY_GOAL = """use_right = goal_right()
while not at_goal():
    if use_right:
        if not wall_right():
            turn_right()
            move()
        elif not wall_ahead():
            move()
        else:
            turn_left()
    else:
        if not wall_left():
            turn_left()
            move()
        elif not wall_ahead():
            move()
        else:
            turn_right()
"""

GREEDY = """while not at_goal():
    if goal_ahead() and not wall_ahead():
        move()
    elif goal_right() and not wall_right():
        turn_right()
        move()
    elif goal_left() and not wall_left():
        turn_left()
        move()
    elif not wall_ahead():
        move()
    else:
        turn_right()
"""

NAIVE_EXPLORER = """while not at_goal():
    tries = 0
    while tries < 4 and (wall_ahead() or visited_ahead()):
        turn_right()
        tries += 1
    if tries == 4:
        while wall_ahead():
            turn_left()
    move()
"""

BUG = """def toward_goal():
    if goal_ahead() and not wall_ahead():
        return True
    if goal_right() and not wall_right():
        turn_right()
        return True
    if goal_left() and not wall_left():
        turn_left()
        return True
    return False

while not at_goal():
    if toward_goal():
        move()
    else:
        stuck_at = distance_to_goal()
        turn_left()
        while not at_goal() and distance_to_goal() >= stuck_at:
            if not wall_right():
                turn_right()
                move()
            elif not wall_ahead():
                move()
            else:
                turn_left()
"""


class LeagueTests(unittest.TestCase):
    """Each league must defeat the previous league's easy answer."""

    def score(self, code, league):
        return server.run_arena(fake_player(), code, league)["score"]

    def test_pro_is_cleared_by_the_wall_follower_but_without_stars(self):
        plain = self.score(RIGHT_HAND, "pro")
        self.assertEqual((plain["solved"], plain["stars"]), (5, 0))
        smart = self.score(SMART_RIGHT, "pro")
        self.assertEqual((smart["solved"], smart["stars"]), (5, 3))
        chooser = self.score(HAND_BY_GOAL, "pro")
        self.assertEqual((chooser["solved"], chooser["stars"]), (5, 5))

    def test_a_memorized_route_fails_its_mirror_twin(self):
        tracks = {t["name"]: t for t in server.rally_league("pro")["tracks"]}
        maze = tracks["Long Hall"]["maze"]
        # Turn the shortest Long Hall route into a list of commands.
        start = server.find_start(maze)
        prev, queue = {start: None}, deque([start])
        while queue:
            cur = queue.popleft()
            for dr, dc in server.DIRS:
                nxt = cur[0] + dr, cur[1] + dc
                if nxt not in prev and maze[nxt[0]][nxt[1]] != "#":
                    prev[nxt] = cur
                    queue.append(nxt)
        goal = next((r, c) for r, row in enumerate(maze)
                    for c, ch in enumerate(row) if ch == "G")
        path = [goal]
        while prev[path[-1]]:
            path.append(prev[path[-1]])
        path.reverse()
        facing, lines = 1, []
        for a, b in zip(path, path[1:]):
            want = server.DIRS.index((b[0] - a[0], b[1] - a[1]))
            lines += ["turn_right()"] * ((want - facing) % 4)
            lines.append("move()")
            facing = want
        result = server.run_arena(fake_player(), "\n".join(lines), "pro")
        solved = {r["name"]: r["solved"] for r in result["results"]}
        self.assertTrue(solved["Long Hall"])
        self.assertFalse(solved["Long Hall, Mirrored"])

    def test_expert_defeats_every_simple_strategy(self):
        for name, code in [("right hand", RIGHT_HAND), ("left hand", LEFT_HAND),
                           ("smart right", SMART_RIGHT),
                           ("smart left", swap_hands(SMART_RIGHT)),
                           ("hand by goal", HAND_BY_GOAL), ("greedy", GREEDY),
                           ("naive explorer", NAIVE_EXPLORER)]:
            self.assertEqual(self.score(code, "expert")["solved"], 0, name)

    def test_the_bug_algorithm_clears_expert(self):
        best = self.score(BUG, "expert")
        self.assertEqual(best["solved"], 5)
        self.assertEqual(best["stars"], 3)   # room left to optimize

    def test_new_sensors_are_rally_only(self):
        player = fake_player()
        player["world"] = server.QUEST_WORLD
        log = server.run_code(player, "if wall_left():\n    move()")["log"]
        self.assertTrue(any("don't know the command 'wall_left'" in l for l in log))

    def test_goal_sensors_are_relative_to_facing(self):
        # Corner Dash: the goal is south-east of a bot that starts facing east.
        code = ('print(goal_ahead(), goal_right(), goal_left())\n'
                'turn_right()\nprint(goal_ahead(), goal_right(), goal_left())')
        log = server.run_arena(fake_player(), code)["results"][0]["log"]
        self.assertIn("› True True False", log)
        self.assertIn("› True False True", log)

    def test_leagues_unlock_with_gold_or_the_teacher(self):
        player = fake_player()
        self.assertFalse(server.rally_unlocked(player, 1))
        server.run_arena(player, RIGHT_HAND, "rookie")
        self.assertTrue(server.rally_unlocked(player, 1))
        self.assertFalse(server.rally_unlocked(player, 2))
        original = server.players
        try:
            server.players = {"test": player}
            server.admin_action({"action": "rally_unlock", "pid": "test"})
        finally:
            server.players = original
        self.assertTrue(server.rally_unlocked(player, 2))

    def test_opening_hints_is_recorded_and_ends_the_no_hint_mark(self):
        original = server.players
        try:
            clean, helped = fake_player("Clean"), fake_player("Helped")
            server.players = {"c": clean, "h": helped}
            self.assertEqual(len(server.open_rally_hint(helped, "rookie")), 1)
            for _ in range(5):
                server.open_rally_hint(helped, "rookie")
            self.assertEqual(server.rally_entry(helped, "rookie")["hints"], 3)
            server.run_arena(clean, RIGHT_HAND)
            server.run_arena(helped, RIGHT_HAND)
            marks = {row["name"]: row["no_hints"]
                     for row in server.arena_scoreboard("rookie")}
            self.assertEqual(marks, {"Clean": True, "Helped": False})
        finally:
            server.players = original

    def test_old_rally_scores_move_to_rookie(self):
        import json, os, tempfile
        saved = {"players": {"p0": {**fake_player("Old"), "id": "p0",
                                    "arena_best": {"solved": 5, "actions": 342,
                                                   "chars": 65, "lines": 5},
                                    "arena_code": "move()"}}, "next": 1}
        original, original_file = dict(server.players), server.STATE_FILE
        original_next = server.next_player_num[0]
        with tempfile.TemporaryDirectory() as folder:
            server.STATE_FILE = os.path.join(folder, "scores.json")
            with open(server.STATE_FILE, "w") as f:
                json.dump(saved, f)
            try:
                server.players.clear()
                server.load_state()
                old = server.players["p0"]
                self.assertNotIn("arena_best", old)
                self.assertEqual(old["rally"]["rookie"]["best"]["solved"], 5)
                self.assertEqual(old["rally"]["rookie"]["code"], "move()")
                self.assertTrue(server.rally_unlocked(old, 1))
            finally:
                server.STATE_FILE = original_file
                server.next_player_num[0] = original_next
                server.players.clear()
                server.players.update(original)


class QuestTests(unittest.TestCase):
    def quest_player(self, mission=0):
        player = fake_player("Quest Tester")
        player["world"] = server.QUEST_WORLD
        player["maze"] = mission
        return player

    def test_quest_is_the_short_four_mission_default(self):
        self.assertEqual(server.DEFAULT_WORLD, server.QUEST_WORLD)
        self.assertEqual(len(server.WORLDS[server.QUEST_WORLD]["mazes"]), 4)
        self.assertEqual(len(server.WORLDS[server.QUEST_WORLD]["levels"]), 4)

    def test_only_the_final_quest_mission_uses_fog(self):
        self.assertEqual([server.is_fogged(server.QUEST_WORLD, i)
                          for i in range(4)], [False, False, False, True])

    def test_print_accepts_safe_debug_text(self):
        result = server.run_code(self.quest_player(), 'print("checking left wall")')
        self.assertIn("› checking left wall", result["log"])

    def test_mixed_text_number_comparison_is_a_friendly_error(self):
        result = server.run_code(self.quest_player(), 'print("left" < 3)')
        self.assertTrue(any("Compare like with like" in line for line in result["log"]))

    def test_runaway_number_growth_stops_quickly(self):
        start = time.time()
        result = server.run_code(self.quest_player(),
                                 "x = 2\nfor i in range(40):\n    x *= x\nprint(x)")
        self.assertLess(time.time() - start, 1)
        self.assertTrue(any("too big" in line for line in result["log"]))

    def test_deeply_nested_expression_is_a_friendly_error(self):
        result = server.run_code(self.quest_player(), "x = " + "-" * 3000 + "1")
        self.assertTrue(any("too deeply nested" in line for line in result["log"]))

    def test_mission_one_pattern_solution_completes(self):
        code = """def tooth():
    turn_left()
    move(2)
    turn_right()
    move(2)
    turn_right()
    move(2)
    turn_left()
    move(2)

for repeat in range(3):
    tooth()
"""
        player = self.quest_player()
        server.run_code(player, code)
        self.assertIn(server.bkey(server.QUEST_WORLD, 0), player["best"])


STRAIGHT = 'def steer():\n    return "straight"\n'

SWEEP = """def steer():
    a = space_ahead()
    l = space_left()
    r = space_right()
    if a > 8 or (a > 0 and a >= max(l, r)):
        return "straight"
    if l >= r:
        return "left"
    return "right"
"""


def cycle_places(code):
    return [h["bikes"][0]["place"] for h in cycles.practice(code, "T", "#fff")]


def cycle_cause(code):
    heat = cycles.practice(code, "T", "#fff")[0]["bikes"][0]
    return heat["died"], heat["cause"], heat["prints"]


class CyclesTests(unittest.TestCase):
    def test_starter_loses_every_heat(self):
        self.assertEqual(cycle_places(STRAIGHT), [4, 4, 4])

    def test_challenge_ladder_is_reachable(self):
        podium = ('def steer():\n    if wall_ahead():\n        if wall_left():\n'
                  '            return "right"\n        return "left"\n'
                  '    return "straight"\n')
        self.assertEqual(min(cycle_places(podium)), 2)
        self.assertIn(1, cycle_places(cycles.HOUSE_BOTS[1]["code"]))
        self.assertEqual(cycle_places(SWEEP), [1, 1, 1])

    def test_practice_starts_are_open_and_distinct(self):
        for arena in cycles.PRACTICE:
            starts = [(r, c) for r, c, _ in arena["starts"]]
            self.assertEqual(len(set(starts)), 4, arena["name"])
            self.assertTrue(all(arena["grid"][r][c] == "." for r, c in starts))

    def test_missing_return_warns_once_and_goes_straight(self):
        died, cause, prints = cycle_cause("def steer():\n    pass\n")
        self.assertEqual(cycle_places("def steer():\n    pass\n"), [4, 4, 4])
        warnings = [line for line in prints if "returned None" in line]
        self.assertEqual(len(warnings), 1)

    def test_code_errors_crash_with_friendly_messages(self):
        died, cause, _ = cycle_cause('def steer()\n    return "left"\n')
        self.assertEqual(died, 0)
        self.assertIn("Syntax error on line 1", cause)
        died, cause, _ = cycle_cause("x = 1\n")
        self.assertIn("def steer():", cause)
        died, cause, _ = cycle_cause("def steer():\n    while True:\n        pass\n")
        self.assertEqual(died, 1)
        self.assertIn("took too long", cause)
        died, cause, _ = cycle_cause("def steer():\n    turn_left()\n")
        self.assertIn("no turn_left()", cause)
        died, cause, _ = cycle_cause("def steer():\n    return left\n")
        self.assertIn('return "left"', cause)

    def test_print_keeps_the_last_lines_before_a_crash(self):
        code = ("n = 0\ndef steer():\n    global n\n    n += 1\n"
                "    for i in range(5):\n        print(i, n)\n"
                "    return \"straight\"\n")
        died, _, prints = cycle_cause(code)
        self.assertEqual(len(prints), cycles.MAX_PRINTS + 1)
        self.assertEqual(prints[0], f"… {5 * died - cycles.MAX_PRINTS} "
                                    "earlier lines not shown")
        self.assertEqual(prints[-1], f"turn {died} › 4 {died}")
        _, _, prints = cycle_cause("def steer():\n    print(1)\n"
                                   "    return \"straight\"\n")
        self.assertEqual(prints[0], "turn 1 › 1")   # short logs are untouched
        _, _, prints = cycle_cause("for i in range(200):\n    print(i)\n"
                                   "def steer():\n    return 1\n")
        self.assertEqual(len(prints), cycles.MAX_PRINTS + 1)
        self.assertIn("returned 1", prints[-1])

    def test_globals_need_the_global_keyword_like_real_python(self):
        _, cause, _ = cycle_cause("n = 0\ndef steer():\n    n += 1\n"
                                  "    return \"straight\"\n")
        self.assertIn("global n", cause)
        _, _, prints = cycle_cause("n = 0\ndef steer():\n    global n\n    n += 1\n"
                                   "    print(n)\n    return \"straight\"\n")
        self.assertEqual(prints[:3], ["turn 1 › 1", "turn 2 › 2", "turn 3 › 3"])

    def test_unsafe_python_is_rejected(self):
        for code in ('import os\ndef steer():\n    return "left"\n',
                     'def steer():\n    return "".join("a")\n',
                     'def steer():\n    return open("x")\n'):
            died, cause, _ = cycle_cause(code)
            self.assertIn("💥", cause, code)

    def test_head_on_crash_is_a_tie(self):
        grid = cycles.box(5, 12)
        bots = [{"key": k, "name": k, "color": "#fff", "code": STRAIGHT}
                for k in ("a", "b")]
        result = cycles.run_match(bots, grid, [(2, 2, 1), (2, 9, 3)])
        a, b = result["bikes"]
        self.assertEqual(a["died"], b["died"])
        self.assertEqual((a["place"], b["place"]), (1, 1))
        self.assertIn("head-on", a["cause"])

    def test_royale_fits_a_whole_class_quickly(self):
        for n in (1, 2, 12, 40):
            grid, starts = cycles.royale_arena(n, seed=n)
            self.assertEqual(len({(r, c) for r, c, _ in starts}), n)
            self.assertTrue(all(grid[r][c] == "." for r, c, _ in starts))
        entries = [{"key": str(i), "name": str(i), "color": "#fff",
                    "code": SWEEP if i % 2 else cycles.HOUSE_BOTS[i % 3]["code"]}
                   for i in range(40)]
        start = time.time()
        result = cycles.run_match(entries, grid, starts)
        self.assertLess(time.time() - start, 2)
        self.assertEqual(sum(b["place"] == 1 for b in result["bikes"]) >= 1, True)

    def test_worst_case_battle_and_test_drive_stay_quick(self):
        # Every bot fills its whole budget every turn with the slowest kind
        # of work (sensor calls) and still rides well, so the match lasts.
        burn = "    x = max(" + ",".join(["space_ahead()", "space_left()",
                                          "space_right()"] * 60) + ")\n"
        code = SWEEP.replace("    a = space_ahead()\n",
                             "    a = space_ahead()\n" + burn * 2)
        grid, starts = cycles.royale_arena(35, seed=1)
        entries = [{"key": str(i), "name": str(i), "color": "#fff",
                    "code": code} for i in range(35)]
        start = time.time()
        result = cycles.run_match(entries, grid, starts)
        self.assertLess(time.time() - start, 3)   # ~1 s on ej's laptop
        self.assertFalse(any("too long" in b["cause"] for b in result["bikes"]))
        start = time.time()
        cycles.practice(code, "T", "#fff")
        self.assertLess(time.time() - start, 0.5)

    def test_one_long_line_counts_as_lots_of_work(self):
        line = " and ".join(["1"] * 600)
        _, cause, _ = cycle_cause(f"def steer():\n    x = {line}\n"
                                  "    return \"left\"\n")
        self.assertIn("took too long", cause)

    def test_only_one_battle_runs_at_a_time(self):
        self.assertTrue(server.cycles_battle_lock.acquire(blocking=False))
        try:
            self.assertIn("already running", server.cycles_battle()["error"])
        finally:
            server.cycles_battle_lock.release()

    def test_battle_scores_points_and_hides_other_prints(self):
        original = dict(server.players)
        try:
            server.players.clear()
            for i, name in enumerate(("Ada", "Ben", "Cy")):
                p = fake_player(name)
                p["id"] = f"t{i}"
                server.players[p["id"]] = p
                server.cycles_test(p, SWEEP.replace("    a = ", "    print(\"hi\")\n    a = ")
                                   if name == "Ada" else STRAIGHT)
            out = server.cycles_battle()
            bikes = out["replay"]["bikes"]
            self.assertEqual(len(bikes), 3)
            self.assertTrue(all(b["prints"] == [] for b in bikes))
            mine = server.cycles_replay(server.players["t0"])["replay"]["bikes"]
            self.assertTrue(next(b for b in mine if b["key"] == "t0")["prints"])
            points = {row["name"]: row["points"] for row in out["board"]}
            self.assertEqual(sum(points.values()),
                             sum(b["outlasted"] for b in bikes))
            server.admin_action({"action": "cycles_reset"})
            self.assertTrue(all(row["points"] == 0 for row in server.cycles_board()))
        finally:
            server.players.clear()
            server.players.update(original)
            server.cycles_round.update(number=0, last=None)


if __name__ == "__main__":
    unittest.main()
