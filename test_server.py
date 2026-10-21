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

    def test_every_royale_start_has_room_ahead(self):
        for n in range(1, 41):
            for seed in range(25):
                grid, starts = cycles.royale_arena(n, seed)
                taken = {(r, c) for r, c, _ in starts}
                for r, c, d in starts:
                    dr, dc = cycles.DIRS[d]
                    ahead = [(r + dr * k, c + dc * k) for k in range(1, 6)]
                    self.assertTrue(all(grid[y][x] == "." and (y, x) not in taken
                                        for y, x in ahead), (n, seed, r, c))

    def test_no_practice_heat_is_decided_in_the_first_ten_turns(self):
        for code in (cycles.HOUSE_BOTS[1]["code"], SWEEP,
                     'def steer():\n    if wall_ahead():\n        return "left"\n'
                     '    return "straight"\n'):
            for heat in cycles.practice(code, "T", "#fff"):
                for bike in heat["bikes"]:
                    self.assertTrue(bike["died"] is None or bike["died"] > 10,
                                    (heat["name"], bike["name"]))

    def test_missing_return_warns_once_and_goes_straight(self):
        died, cause, prints = cycle_cause("def steer():\n    pass\n")
        self.assertEqual(cycle_places("def steer():\n    pass\n"), [4, 4, 4])
        warnings = [line for line in prints if "didn't return anything" in line]
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

    def test_beginner_mistakes_get_friendly_accurate_messages(self):
        s = "def steer():\n"
        cases = [   # (program, what the student must see in the cause/warning)
            ('def steer()\n    return "left"\n', "line 1: a line that starts with def"),
            (s + '    if wall_ahead()\n        return "left"\n', "line 2: a line that starts"),
            (s + 'return "left"\n', "line 2: the lines inside it need pushing in"),
            (s + '    x = 1\n        return "left"\n', "line 3: this line is pushed in further"),
            (s + '    if wall_ahead():\n        return "left"\n      return "x"\n',
             "line 4: this line doesn't line up"),
            (s + '\tif wall_ahead():\n        return "left"\n', "mixes tabs and spaces"),
            ('return "left"\n', "Line 1: return only works inside a function"),
            (s + '    return left\n', 'Line 2: Put quotes round words, in small letters:  return "left"'),
            (s + '    return Left\n', 'return "left"'),
            (s + '    return "Left"\n', 'Use small letters and no spaces: "left"'),
            (s + "    return 'left '\n", 'Use small letters and no spaces: "left"'),
            (s + '    return "forward"\n', "returned 'forward'. Return \"left\", \"right\" or"),
            (s + '    return True\n', "returned True."),
            (s + '    return 1\n', "returned 1."),
            (s + '    return\n', "steer() didn't return anything"),
            (s + '    if wall_ahead():\n        "left"\n    "straight"\n', "didn't return anything"),
            (s + '    print "hi"\n    return "left"\n', 'line 2: print needs brackets'),
            (s + '    if space_left() = 3:\n        return "left"\n', "use  ==  (two equals signs)"),
            (s + '    if wall_ahead:\n        return "left"\n    return "straight"\n',
             "Line 2: wall_ahead is a command — put  ( )  after it"),
            (s + '    x = space_ahead\n    return "left"\n', "space_ahead is a command"),
            (s + '    elif wall_ahead():\n        return "left"\n', "elif needs an  if  just above it"),
            (s + '    else:\n        return "left"\n', "else needs an  if  just above it"),
            ('def steer(direction):\n    return "left"\n', "steer() shouldn't take anything"),
            (s + '    return "left"\n' + s + '    return "right"\n', "Line 3: There are two  def steer():"),
            ('def Steer():\n    return "left"\n', "Your def is called Steer(), but the game asks  steer()"),
            ('', "Your program needs a  def steer():"),
            ('# my bot\n', "Your program needs a  def steer():"),
            (s + '    while True:\n        x = 1\n', "Line 2: steer() took too long to "
             "decide — is a while loop stuck going round forever?"),
            (s + '    for i in range(100000):\n        x = i\n    return "left"\n',
             "Line 2: steer() took too long to decide — does a for loop go round"),
            ('x = 0\nwhile True:\n    x += 1\n' + s + '    return "left"\n',
             "Line 2: The top of your program ran too long — is a while loop stuck"),
            ("# " + "x" * 4000 + "\n" + s + '    return "left"\n',
             "Your program is too long: the limit is 4000 characters"),
            (s + '    n = 0\n    while n < 5:\n        x = 1\n', "Line 3: steer() took too long"),
            (s + '    return steer()\n', "called itself too many times"),
            (s + '    x = "left" * 2\n    return "left"\n', "You can't do math with text"),
            (s + '    print("room " + space_ahead())\n    return "left"\n', 'use a comma:  print("room", 5)'),
            (s + '    move()\n', "There's no move() in Light Cycles"),
            (s + '    turn_left()\n', "There's no turn_left() in Light Cycles"),
            (s + '    if space_left() > "3":\n        return "left"\n', "Compare like with like"),
            ('turns = 0\n' + s + '    turns = turns + 1\n    return "left"\n', "put  global turns"),
            ('global turns\n' + s + '    return "left"\n', "Line 1: global only goes inside a function"),
            (s + '    if space_ahaed() > 2:\n        return "left"\n', "Did you mean  space_ahead() ?"),
            (s + '    if wall_infront():\n        return "left"\n', "I don't know the command 'wall_infront'"),
            (s + '    if space_ahead(1) > 2:\n        return "left"\n', "space_ahead() doesn't take anything"),
            ('turns = 0\n' + s + '    if trns > 2:\n        return "left"\n', "Did you mean  turns ?"),
            (s + '    return "left\n', "missing its closing quote"),
            (s + '    if (space_ahead() > 2:\n        return "left"\n', "a bracket  (  isn't closed"),
            (s + '    return “left”\n', "curly quotes"),
            (s + '    Return "left"\n', "write  return  not  Return"),
            (s + '    If wall_ahead():\n        return "left"\n', "write  if  not  If"),
            (s + '    if wall_ahead() == true:\n        return "left"\n', "Write True with a capital letter"),
            (s + '    ways = ["left", "right"]\n    return "left"\n', "Lists and [ ] aren't part"),
            ('import random\n' + s + '    return "left"\n', "Line 1: import isn't allowed"),
            (s + '    return random.choice("lr")\n', "random.choice() isn't part of Light Cycles"),
            (s + '    if wall_ahead():\n        way = "left"\n    return way\n',
             "Line 4: You used 'way' before giving it a value"),
            (s + '    x = space_ahead() / 2\n    return "left"\n', "Use // for whole-number division"),
            (s + '    print("room", str(space_ahead()))\n    return "left"\n', "str() isn't needed"),
            (s + '    print(f"room {space_ahead()}")\n    return "left"\n', "f-strings aren't part"),
            (s + '    def helper():\n        return "left"\n    return helper()\n',
             "Make each def at the top level"),
            (s + '    space_ahead = 3\n    return "left"\n', "'space_ahead' is already a command"),
            (s + '    for i in space_ahead():\n        x = i\n', "A for loop must look like"),
            (s + '    retrun "left"\n', "line 2: did you mean  return ?"),
            (s + '    if wall_ahead():\n        return "left"\n    esle:\n        return "right"\n',
             "line 4: did you mean  else ?"),
            (s + '    whlie wall_ahead():\n        return "left"\n', "did you mean  while ?"),
            ('deff steer():\n    return "left"\n', "did you mean  def ?"),
            ('def steer:\n    return "left"\n', "a def needs brackets, like  def steer():"),
            (s + '    if wall_ahead():\n        return "left"\n    else if wall_left():\n'
                 '        return "right"\n', "line 4: write  elif  for 'else if'"),
            (s + '    if wall_ahead() && wall_left():\n        return "left"\n', "write  and  (not  &&)"),
            (s + '    if !wall_ahead():\n        return "left"\n', "write the word  not  instead of  !"),
            (s + '    if space_ahead() => 2:\n        return "left"\n', "write  >=  (not  =>)"),
            (s + '    if wall ahead():\n        return "left"\n', "sensor names have an underscore"),
            (s + '    if wall_ahead() & wall_left():\n        return "left"\n    return "straight"\n',
             "Line 2: Use the word  and  to join two checks"),
            (s + '    if wall_ahead() is True:\n        return "left"\n    return "straight"\n',
             "use  ==  or  !=  instead of  is"),
        ]
        self.assertGreaterEqual(len(cases), 40)
        for code, expected in cases:
            heat = cycles.practice(code, "T", "#fff")[0]["bikes"][0]
            seen = heat["cause"] + " ".join(heat["prints"])
            self.assertIn(expected, seen, code)
            self.assertNotIn("Traceback", seen)
        # These are fine Python and must just work: no crash, no warning.
        for code in ('x = space_ahead()\n' + s + '    return "straight"\n',
                     s + '    n = 0\n    for i in range(space_ahead()):\n        n += 1\n'
                         '    return "straight"\n',
                     s + '    """My bot."""\n    return "straight"\n',
                     s + '    return "straight" if space_ahead() > 0 else "left"\n',
                     # Text that only looks like a slip from another language.
                     s + '    note = "a && b => !"\n    return "straight"\n',
                     'turns = 0\n' + s + '    global turns\n    turns += 1\n'
                     '    return "straight"\n'):
            heat = cycles.practice(code, "T", "#fff")[0]["bikes"][0]
            self.assertFalse(heat["error"], heat["cause"])
            self.assertEqual(heat["prints"], [])

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

    def test_bikes_say_which_way_they_face_and_if_code_broke(self):
        grid = cycles.box(6, 8)
        bots = [{"key": "a", "name": "a", "color": "#fff",
                 "code": 'def steer():\n    if wall_ahead():\n'
                         '        return "right"\n    return "straight"\n'},
                {"key": "b", "name": "b", "color": "#fff",
                 "code": "def steer():\n    return 1 // 0\n"},
                {"key": "c", "name": "c", "color": "#fff", "code": "steer"}]
        a, b, c = cycles.run_match(bots, grid, [(1, 1, 1), (4, 1, 1), (4, 4, 0)])["bikes"]
        self.assertEqual(len(a["dirs"]), len(a["path"]))
        self.assertEqual(a["dirs"][:2], [1, 1])
        # Each square's heading matches the step taken to reach it.
        for (r0, c0), (r1, c1), d in zip(a["path"], a["path"][1:], a["dirs"][1:]):
            self.assertEqual(cycles.DIRS[d], (r1 - r0, c1 - c0))
        self.assertEqual((a["error"], b["error"], c["error"]), (False, True, True))
        self.assertEqual((b["dirs"], c["dirs"]), ([1], [0]))
        # A cycle that turns into a wall faces the wall on its last frame.
        turner = [{"key": "t", "name": "t", "color": "#fff",
                   "code": 'def steer():\n    return "left"\n'}]
        t = cycles.run_match(turner, grid, [(1, 3, 1)])["bikes"][0]
        self.assertEqual((t["path"], t["dirs"], t["crash"]), ([[1, 3]], [0], [0, 3]))

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
        # A helper keeps it under the program size limit, as a student's must be.
        burn = "def burn():\n    return max(" + ",".join(
            ["space_ahead()", "space_left()", "space_right()"] * 40) + ")\n"
        code = burn + SWEEP.replace("    a = space_ahead()\n",
                                    "    a = space_ahead()\n" + "    burn()\n" * 3)
        self.assertLessEqual(len(code), cycles.MAX_CODE)
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
        self.assertIn("too much work in one go", cause)   # there's no loop to blame

    def test_server_accepts_a_whole_class_connecting_at_once(self):
        self.assertGreaterEqual(server.ClassroomServer.request_queue_size, 64)

    def test_admin_overview_shows_each_light_cycles_entry(self):
        original = dict(server.players)
        try:
            server.players.clear()
            ada, bo = fake_player("Ada"), dict(fake_player("Bo"), id="bo")
            server.players.update({ada["id"]: ada, bo["id"]: bo})
            server.cycles_test(ada, SWEEP)
            server.cycles_test(ada, 'def steer()\n    return "left"\n')
            rows = {r["name"]: r["cycles"] for r in server.overview()["players"]}
            self.assertIsNone(rows["Bo"])
            self.assertEqual((rows["Ada"]["ok"], rows["Ada"]["kept_previous"],
                              rows["Ada"]["best"]["wins"]), (True, True, 3))
        finally:
            server.players.clear()
            server.players.update(original)

    def test_only_one_battle_runs_at_a_time(self):
        self.assertTrue(server.cycles_battle_lock.acquire(blocking=False))
        try:
            self.assertIn("already running", server.cycles_battle()["error"])
        finally:
            server.cycles_battle_lock.release()

    def test_broken_code_never_replaces_a_working_entry(self):
        original = dict(server.players)
        broken = 'def steer()\n    return "left"\n'
        try:
            server.players.clear()
            p = fake_player("Ada")
            server.players[p["id"]] = p
            entry = server.cycles_test(p, broken)["entry"]   # first try: broken
            self.assertEqual((entry["code"], entry["ok"], entry["kept_previous"]),
                             (broken, False, False))
            self.assertIn("Syntax error on line 1", entry["error"])
            entry = server.cycles_test(p, STRAIGHT)["entry"]   # now it works
            self.assertEqual((entry["code"], entry["ok"], entry["error"]),
                             (STRAIGHT, True, None))
            self.assertIsInstance(entry["entered_at"], int)
            entry = server.cycles_test(p, SWEEP)["entry"]      # working again
            self.assertEqual(entry["code"], SWEEP)
            entered_at = entry["entered_at"]
            entry = server.cycles_test(p, broken)["entry"]     # broken again
            self.assertEqual((entry["code"], entry["ok"], entry["kept_previous"],
                              entry["entered_at"]), (SWEEP, True, True, entered_at))
            self.assertIn("Syntax error", entry["error"])
            state = server.cycles_state(p)
            self.assertEqual(state["code"], broken)   # the editor keeps the draft
            self.assertTrue(state["entry"]["kept_previous"])
            for code in ("x = 1\n", "def steer():\n    return 1 // 0\n" + "x = 1 // 0\n",
                         "# " + "x" * 5000 + "\n" + SWEEP):
                self.assertTrue(server.cycles_test(p, code)["entry"]["kept_previous"])
            bike = server.cycles_battle()["replay"]["bikes"][0]
            self.assertNotIn("code error", bike["cause"])   # raced the kept bot
            # A steer() that only crashes once it's running is still entered.
            crashy = 'def steer():\n    return 1 // 0\n'
            self.assertEqual(server.cycles_test(p, crashy)["entry"]["code"], crashy)
        finally:
            server.players.clear()
            server.players.update(original)
            server.cycles_round.update(number=0, last=None)

    def test_cycle_colors_are_bright_and_never_shared_in_a_battle(self):
        def luminance(color):
            rgb = [int(color[i:i + 2], 16) / 255 for i in (1, 3, 5)]
            r, g, b = [c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
                       for c in rgb]
            return 0.2126 * r + 0.7152 * g + 0.0722 * b
        arena = luminance("#0b111e")
        self.assertGreaterEqual(len(set(server.CYCLE_COLORS)), 24)
        for color in server.CYCLE_COLORS:   # WCAG contrast ratio on the arena
            self.assertGreaterEqual((luminance(color) + 0.05) / (arena + 0.05), 4.5)
        original = dict(server.players)
        try:
            server.players.clear()
            for i in range(30):
                p = fake_player(f"Kid{i}")
                p["id"] = f"k{i}"
                server.players[p["id"]] = p
            kids = list(server.players.values())
            colors = [server.cycles_color(p) for p in kids]
            self.assertEqual(len(set(colors[:24])), 24)
            self.assertEqual(server.cycles_state(kids[3])["you"]["color"], colors[3])
            # Kid 24 repeats kid 0's colour; a battle of 24 with both of them
            # still gives every rider a different colour.
            self.assertEqual(colors[24], colors[0])
            for p in kids[:23] + [kids[24]]:
                server.cycles_entry(p)["code"] = STRAIGHT
            bikes = server.cycles_battle()["replay"]["bikes"]
            self.assertEqual(len(bikes), 24)
            self.assertEqual(len({b["color"] for b in bikes}), 24)
            self.assertEqual(bikes[0]["color"], colors[0])   # own colour kept
        finally:
            server.players.clear()
            server.players.update(original)
            server.cycles_round.update(number=0, last=None)

    def test_round_and_last_replay_survive_a_restart(self):
        import json, os, tempfile
        original, original_file = dict(server.players), server.STATE_FILE
        original_next = server.next_player_num[0]
        with tempfile.TemporaryDirectory() as folder:
            server.STATE_FILE = os.path.join(folder, "scores.json")
            try:
                server.players.clear()
                p = fake_player("Ada")
                server.players[p["id"]] = p
                server.cycles_test(p, SWEEP)
                server.cycles_battle()
                server.cycles_battle()
                server.save_state()
                server.cycles_round.update(number=0, last=None)   # a restart
                server.players.clear()
                server.load_state()
                self.assertEqual(server.cycles_state(server.players["test"])["round"], 2)
                self.assertEqual(server.cycles_replay(None)["replay"]["round"], 2)
                # Saves from before Light Cycles rounds were kept still load.
                with open(server.STATE_FILE, "w") as f:
                    json.dump({"players": {}, "next": 0}, f)
                server.load_state()
                self.assertEqual(server.cycles_round, {"number": 0, "last": None})
            finally:
                server.STATE_FILE = original_file
                server.next_player_num[0] = original_next
                server.players.clear()
                server.players.update(original)
                server.cycles_round.update(number=0, last=None)

    def test_old_cycles_entries_still_load(self):
        p = fake_player()
        p["cycles"] = {"code": STRAIGHT, "best": None, "points": 3,
                       "rounds": 1, "wins": 0}
        state = server.cycles_state(p)
        self.assertEqual(state["code"], STRAIGHT)
        self.assertEqual(state["entry"], {"code": STRAIGHT, "entered_at": None,
                                          "ok": True, "error": None,
                                          "kept_previous": False})

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
