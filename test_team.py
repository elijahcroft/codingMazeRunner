"""The Team Mission: the map can be finished, and the classroom side keeps it live."""

import json
import os
import re
import time
import unittest
from collections import deque
from urllib.request import urlopen

import planet
import planet_predict
import planet_team
import server
from planet_team import LEVELS, Mission
import test_planet

HERE = os.path.dirname(os.path.abspath(__file__))
FAR_LATER = 10_000
BIG = len(LEVELS) - 1                  # most tests use the last map, which has everything
NUMBER = {level["name"]: i for i, level in enumerate(LEVELS)}


class Crew:
    """Drives rovers the way a page's click does: a route round everything in
    the way, then pushes in a straight line."""

    def __init__(self, count=2, level=BIG):
        self.game, self.now = Mission(level), 1000
        for seat in range(count):
            self.game.enter(seat, self.now)

    def free(self, spot):
        g = self.game
        return (g.map[spot[0]][spot[1]] != "#" and not g.shut_door(spot)
                and not g.crater(spot) and not g.boulder_on(spot))

    def drive(self, seat, to):
        start, seen = self.game.rovers[seat], {}
        seen[start] = None
        queue = deque([start])
        while queue:
            at = queue.popleft()
            if at == to:
                break
            for way, (dr, dc) in planet_team.WAYS.items():
                step = (at[0] + dr, at[1] + dc)
                if step not in seen and self.free(step):
                    seen[step] = (at, way)
                    queue.append(step)
        assert to in seen, f"rover {seat} can't reach {to} from {start}"
        ways = []
        while seen[to]:
            to, way = seen[to]
            ways.append(way)
        for way in reversed(ways):
            self.push(seat, way, 1)

    def push(self, seat, way, squares):
        for _ in range(squares):
            self.now += 1
            tip = self.game.move(seat, way, "Ada", self.now)
            assert tip is None, f"rover {seat} going {way}: {tip!r}"
            assert self.game.next_job()["text"], "every step of a level has a next job"


class MapTests(unittest.TestCase):
    def test_every_map_is_the_same_size_with_a_rock_edge(self):
        for level in LEVELS:
            rows = level["map"]
            self.assertEqual({len(row) for row in rows}, {30}, level["name"])
            self.assertEqual(len(rows), 15, level["name"])
            self.assertEqual({row[0] + row[-1] for row in rows}, {"##"}, level["name"])
            self.assertEqual(set(rows[0] + rows[-1]), {"#"}, level["name"])

    def test_every_map_has_a_way_in_a_way_out_and_a_plate_for_each_door(self):
        for number, level in enumerate(LEVELS):
            g = Mission(number)
            self.assertEqual(set(g.doors), set(g.plates), level["name"])
            self.assertTrue(g.starts and g.vault and g.recycler, level["name"])

    def finish(self, crew, one, two):
        crew.drive(one, sorted(crew.game.vault)[0])
        crew.drive(two, sorted(crew.game.vault)[1])
        crew.game.check_win(crew.now)
        self.assertTrue(crew.game.won)

    def test_the_teachers_button_clears_a_way_to_the_vault_on_every_level(self):
        for number in range(len(LEVELS)):
            crew = Crew(1, number)
            crew.game.open_all()
            crew.drive(0, sorted(crew.game.vault)[0])

    def test_two_rovers_can_finish_landing_bay(self):
        crew = Crew(2, NUMBER["Landing Bay"])
        g, one, two = crew.game, 0, 1
        crew.drive(one, (3, 4)); crew.push(one, "south", 3)       # a boulder onto plate A
        self.assertTrue(g.done_for_good("A"))
        crew.drive(one, (7, 13))                                  # hold door B for a friend
        crew.drive(two, (7, 20)); crew.push(two, "west", 6)       # who rolls a boulder back
        self.assertTrue(g.done_for_good("B"))
        crew.drive(one, (3, 23)); crew.push(one, "west", 2)
        crew.drive(two, (11, 23)); crew.push(two, "west", 2)
        self.assertTrue(g.done_for_good("C"))
        self.finish(crew, one, two)

    def test_two_rovers_can_finish_crater_crossing(self):
        crew = Crew(2, NUMBER["Crater Crossing"])
        g, one, two = crew.game, 0, 1
        crew.drive(one, (10, 6)); crew.push(one, "east", 2)       # bridge the crater
        crew.drive(one, (13, 11)); crew.push(one, "north", 2)     # plate A opens the top lane
        self.assertTrue(g.done_for_good("A"))
        crew.drive(two, (6, 16)); crew.push(two, "north", 2)
        crew.drive(two, (3, 17)); crew.push(two, "west", 3)       # plate B opens the bottom lane
        self.assertTrue(g.done_for_good("B"))
        crew.drive(one, (13, 18)); crew.push(one, "north", 2)     # plate C opens the top again
        self.assertTrue(g.done_for_good("C"))
        crew.drive(one, (8, 22)); crew.push(one, "south", 2)
        crew.drive(two, (1, 22)); crew.push(two, "south", 3)
        self.assertTrue(g.done_for_good("V"))
        self.finish(crew, one, two)

    def test_two_rovers_can_finish_the_ring(self):
        crew = Crew(2, NUMBER["The Ring"])
        g, one, two = crew.game, 0, 1
        crew.drive(one, (4, 2))                                   # hold door A
        crew.drive(two, (4, 8)); crew.push(two, "west", 5)        # roll the boulder out to it
        self.assertTrue(g.done_for_good("A"))
        crew.drive(two, (4, 6)); crew.push(two, "south", 2)       # fill in a crater
        crew.drive(two, (9, 14)); crew.push(two, "west", 3)
        crew.drive(two, (9, 15)); crew.push(two, "east", 3)
        crew.drive(one, (4, 27)); crew.push(one, "south", 2)
        self.assertTrue(g.done_for_good("V"))
        self.finish(crew, one, two)

    def test_two_rovers_can_finish_four_corners(self):
        crew = Crew(2, NUMBER["Four Corners"])
        g, one, two = crew.game, 0, 1
        crew.drive(one, (6, 5)); crew.push(one, "north", 2)
        crew.drive(one, (6, 15)); crew.push(one, "north", 2)
        crew.drive(one, (8, 5)); crew.push(one, "south", 2)
        crew.drive(one, (11, 15))                                 # no boulder for this one
        self.assertTrue(g.door_open("V"))
        crew.drive(two, sorted(g.vault)[0])
        g.check_win(crew.now)
        self.assertTrue(g.won)

    def test_two_rovers_can_finish_the_long_road(self):
        crew = Crew(2, NUMBER["The Long Road"])
        g, one, two = crew.game, 0, 1
        crew.drive(one, (2, 8)); crew.push(one, "east", 16)
        self.assertTrue(g.done_for_good("A"))
        crew.drive(two, (6, 23)); crew.push(two, "west", 8)       # fill the crater
        crew.drive(two, (6, 10)); crew.push(two, "west", 3)
        self.assertTrue(g.done_for_good("B"))
        crew.drive(two, (10, 13)); crew.push(two, "east", 6)
        crew.drive(two, (12, 13)); crew.push(two, "east", 6)
        self.assertTrue(g.done_for_good("C"))
        self.finish(crew, one, two)

    def test_two_rovers_can_finish_three_step_bridge(self):
        crew = Crew(2, NUMBER["Three-Step Bridge"])
        g, one, two = crew.game, 0, 1
        crew.drive(one, (7, 9)); crew.push(one, "east", 4)        # the first boulder fills the first crater
        crew.drive(one, (3, 8)); crew.push(one, "south", 3)       # down into the same row
        crew.drive(one, (7, 7)); crew.push(one, "east", 7)
        crew.drive(one, (11, 6)); crew.push(one, "north", 3)
        crew.drive(one, (7, 5)); crew.push(one, "east", 10)
        crew.drive(one, (3, 17)); crew.push(one, "east", 2)       # one plate down for good
        crew.drive(one, (11, 20))                                 # and stand on the other
        self.assertTrue(g.door_open("V"))
        crew.drive(two, sorted(g.vault)[0])
        g.check_win(crew.now)
        self.assertTrue(g.won)

    def test_two_rovers_can_finish_pass_it_back(self):
        crew = Crew(2, NUMBER["Pass It Back"])
        g, one, two = crew.game, 0, 1
        crew.drive(one, (7, 4))                                   # hold door A
        crew.drive(two, (3, 10)); crew.push(two, "south", 3)
        crew.drive(two, (7, 11)); crew.push(two, "west", 6)       # roll a boulder back to the plate
        self.assertTrue(g.done_for_good("A"))
        crew.drive(one, (7, 11))
        crew.drive(two, (12, 17)); crew.push(two, "north", 4)
        crew.drive(two, (7, 18)); crew.push(two, "west", 6)
        self.assertTrue(g.done_for_good("B"))
        crew.drive(one, (7, 18))
        crew.drive(two, (3, 24)); crew.push(two, "south", 3)
        crew.drive(two, (7, 25)); crew.push(two, "west", 6)
        self.assertTrue(g.done_for_good("C"))
        self.finish(crew, one, two)

    def test_two_rovers_can_finish_the_big_vault(self):
        """The answer keys in STRANGE_PLANET_GUIDE.md, played square by square."""
        crew = Crew(2)
        g = crew.game
        one, two = 0, 1
        # The landing room: a boulder onto plate A and one onto plate B.
        crew.drive(one, (9, 12)); crew.push(one, "south", 2)
        self.assertTrue(g.door_open("A"))
        crew.drive(one, (9, 17)); crew.push(one, "south", 2)
        self.assertTrue(g.door_open("B"))
        # Door D: one stands on the plate while the other rolls a boulder down.
        crew.drive(one, (10, 14))
        self.assertTrue(g.door_open("D"))
        crew.drive(two, (6, 16)); crew.push(two, "west", 1)
        crew.drive(two, (5, 14)); crew.push(two, "south", 4)
        self.assertTrue(g.done_for_good("D"))
        # The hall: the second boulder goes up, then along onto a vault plate.
        crew.drive(two, (7, 12)); crew.push(two, "north", 1)
        crew.drive(two, (5, 13)); crew.push(two, "west", 1)
        # West: two boulders in one row bridge the double crater.
        crew.drive(one, (10, 9)); crew.push(one, "west", 2)
        crew.drive(one, (13, 8)); crew.push(one, "north", 2)
        crew.drive(one, (10, 9)); crew.push(one, "west", 3)
        crew.drive(one, (6, 6)); crew.push(one, "west", 3)      # one of door C's two plates
        crew.drive(one, (6, 8))                                 # stand on the other
        crew.drive(two, (1, 8)); crew.push(two, "south", 4)     # bring a boulder out to it
        self.assertTrue(g.done_for_good("C"))
        crew.drive(two, (2, 5)); crew.push(two, "west", 2)      # a vault plate
        # East: the swap doors, a boulder through each one.
        crew.drive(one, (12, 21))
        crew.drive(two, (10, 25))
        crew.drive(one, (10, 20)); crew.push(one, "east", 4)
        self.assertTrue(g.done_for_good("E"))
        crew.drive(one, (12, 21))
        crew.drive(two, (12, 27)); crew.push(two, "west", 5)
        self.assertTrue(g.done_for_good("F"))
        # Up, over the crater and through door G to the last vault plate.
        crew.drive(two, (6, 27)); crew.push(two, "west", 2)
        crew.drive(two, (5, 22)); crew.push(two, "south", 1)
        crew.drive(two, (7, 23)); crew.push(two, "west", 2)
        self.assertTrue(g.done_for_good("G"))
        crew.drive(two, (2, 22)); crew.push(two, "east", 4)
        self.assertTrue(g.done_for_good("V"))
        self.finish(crew, one, two)


class RuleTests(unittest.TestCase):
    def setUp(self):
        self.crew = Crew(2)
        self.game = self.crew.game

    def test_a_rover_holds_a_door_only_while_it_stays_on_the_plate(self):
        self.assertFalse(self.game.door_open("A"))
        self.crew.drive(0, (12, 12))
        self.assertTrue(self.game.door_open("A"))
        self.crew.drive(0, (12, 13))
        self.assertFalse(self.game.door_open("A"))

    def test_a_boulder_opens_a_door_for_good(self):
        self.crew.drive(0, (9, 12))
        self.crew.push(0, "south", 2)
        self.assertTrue(self.game.done_for_good("A"))
        self.crew.drive(0, (12, 15))
        self.assertTrue(self.game.door_open("A"))

    def test_a_door_needing_two_plates_waits_for_both(self):
        g = self.game
        g.rovers[0] = (6, 2)
        self.assertFalse(g.door_open("C"))
        g.rovers[1] = (6, 8)
        self.assertTrue(g.door_open("C"))

    def test_a_door_will_not_shut_on_a_rover(self):
        g = self.game
        g.rovers[0], g.rovers[1] = (12, 12), (11, 10)
        self.assertTrue(g.door_open("A"))
        g.rovers[0] = (12, 13)
        self.assertTrue(g.door_open("A"))

    def test_a_shut_door_stops_a_rover_and_says_why(self):
        self.game.rovers[0] = (11, 11)
        tip = self.game.move(0, "west", "Ada", 1)
        self.assertEqual(self.game.rovers[0], (11, 11))
        self.assertIn("Door A", tip)

    def test_rovers_share_squares(self):
        self.game.rovers[0] = (11, 12)
        self.game.rovers[1] = (11, 13)
        self.assertIsNone(self.game.move(1, "west", "Bo", 1))

    def test_a_boulder_rolls_over_a_rover(self):
        g = self.game
        g.rovers[0], g.rovers[1] = (9, 12), (11, 12)
        self.assertIsNone(g.move(0, "south", "Ada", 1))
        self.assertEqual(g.boulder_on((11, 12))["home"], (10, 12))

    def test_a_boulder_will_not_go_into_rock_a_boulder_or_a_shut_door(self):
        g = self.game
        g.boulder_on((10, 12))["at"] = (11, 11)
        g.rovers[0] = (11, 12)
        self.assertIn("boulder", g.move(0, "west", "Ada", 1))    # door A's shut
        g.boulder_on((11, 11))["at"] = (9, 11)
        g.rovers[0] = (10, 11)
        self.assertIn("boulder", g.move(0, "north", "Ada", 3))   # rock

    def test_a_crater_stops_a_rover_and_a_boulder_fills_it(self):
        g = self.game
        g.rovers[0] = (11, 7)
        self.assertIn("crater", g.move(0, "west", "Ada", 1))
        g.forced.add("A")
        self.crew.drive(1, (10, 9))
        self.crew.push(1, "west", 2)
        self.assertFalse(g.crater((10, 6)))
        self.crew.drive(1, (10, 6))

    def test_recycling_brings_back_lost_boulders_but_not_one_in_use_or_sunk(self):
        g = self.game
        self.crew.drive(0, (9, 12))
        self.crew.push(0, "south", 2)                       # sunk on plate A
        lost, busy, used = [g.boulder_on(s) for s in ((10, 17), (6, 5), (10, 8))]
        lost.update(at=(9, 18), pushed=100)
        busy.update(at=(6, 6), pushed=self.crew.now)
        used.update(at=None, pushed=100)
        g.rovers[1] = (13, 12)
        self.assertIsNone(g.move(1, "west", "Bo", self.crew.now + 1))
        self.assertEqual(lost["at"], (10, 17))
        self.assertEqual(busy["at"], (6, 6))
        self.assertEqual(used["at"], (10, 8))
        self.assertEqual(sum(b["plate"] for b in g.boulders), 1)
        self.assertTrue(g.done_for_good("A"))
        self.assertIn("2 lost boulders", g.news[-1])

    def test_recycling_leaves_a_boulder_whose_home_is_taken(self):
        g = self.game
        first, second = g.boulder_on((10, 12)), g.boulder_on((10, 17))
        first["at"], second["at"] = (9, 11), (10, 12)
        g.send_boulders_home("Ada", FAR_LATER)
        self.assertEqual(second["at"], (10, 17))

    def test_half_the_rovers_in_the_vault_wins(self):
        g = Crew(5).game
        g.forced.update(g.doors)
        g.rovers[0] = g.rovers[1] = (2, 12)
        g.check_win(1)
        self.assertFalse(g.won)
        g.rovers[2] = (2, 13)
        g.check_win(2)
        self.assertTrue(g.won)

    def test_a_whole_class_starts_on_squares_of_its_own(self):
        for number in range(len(LEVELS)):
            game = Mission(number)
            for seat in range(30):
                game.enter(seat, 1000)
            spots = list(game.rovers.values())
            self.assertEqual(len(set(spots)), 30, LEVELS[number]["name"])
            for r, c in spots:
                self.assertIn(game.map[r][c], ".S", LEVELS[number]["name"])
            self.assertEqual(game.in_vault(), 0)
            self.assertEqual(game.pressed("A") if "A" in game.plates else [], [])

    def test_a_rover_sent_home_gets_a_free_square_and_keeps_its_own(self):
        game = Mission(0)
        for seat in range(6):
            game.enter(seat, 1000)
        start = game.rovers[5]
        game.go_home(5)
        self.assertEqual(game.rovers[5], start)
        self.assertEqual(len(set(game.rovers.values())), 6)

    def test_going_home_works_from_anywhere(self):
        self.game.rovers[0] = (2, 27)
        self.game.go_home(0)
        self.assertIn(self.game.rovers[0], self.game.starts)


class NextJobTests(unittest.TestCase):
    def game(self, name):
        game = Mission(NUMBER[name])
        game.enter(0, 1000)
        return game

    def test_every_level_starts_with_a_job_that_marks_real_squares(self):
        for number in range(len(LEVELS)):
            game = Mission(number)
            job = game.next_job()
            self.assertTrue(job["marks"], LEVELS[number]["name"])
            for r, c in job["marks"]:
                self.assertIn(game.map[r][c].upper(), "OABCDEFGV")

    def test_it_never_asks_for_a_plate_nobody_can_reach(self):
        game = self.game("Crater Crossing")
        self.assertIn("crater", game.next_job()["text"].lower())

    def test_the_job_moves_on_when_a_door_opens_for_good(self):
        game = self.game("Landing Bay")
        self.assertIn("Door A", game.next_job()["text"])
        game.sunk.update(game.plates["A"])
        self.assertIn("Door B", game.next_job()["text"])

    def test_a_held_door_says_go_through_and_bring_a_boulder_back(self):
        game = self.game("Landing Bay")
        game.rovers[0] = game.plates["A"][0]
        text = game.next_job()["text"]
        self.assertIn("Go through now", text)
        self.assertIn("boulder back", text)

    def test_a_door_with_many_plates_counts_them(self):
        game = self.game("Four Corners")
        game.rovers[0] = game.plates["V"][0]
        self.assertIn("all 4 of its plates pressed at once, and 1 is pressed", game.next_job()["text"])

    def test_wide_craters_say_to_use_one_row(self):
        self.assertIn("one row", self.game("Three-Step Bridge").next_job()["text"])

    def test_a_clear_way_says_go_to_the_vault(self):
        game = self.game("The Ring")
        game.open_all()
        job = game.next_job()
        self.assertIn("gold vault", job["text"])
        self.assertEqual(job["marks"], [])

    def test_a_won_level_has_no_job(self):
        game = self.game("Landing Bay")
        game.won = 1
        self.assertIsNone(game.next_job())


class YourJobTests(unittest.TestCase):
    def game(self, *spots, name="Landing Bay"):
        game = Mission(NUMBER[name])
        for seat, spot in enumerate(spots):
            game.enter(seat, 1000, spot)
        return game

    def test_the_rover_on_a_plate_is_told_to_stay(self):
        game = self.game((7, 4), (9, 2))
        self.assertIn("holding door A", game.your_job(0))

    def test_the_rover_on_a_plate_is_not_told_to_go_through(self):
        game = self.game((7, 4), (9, 2))
        self.assertIn("Go through now", game.next_job()["text"])
        self.assertNotIn("Go through", game.your_job(0))

    def test_only_the_closest_free_rover_is_sent_to_a_plate(self):
        game = self.game((8, 4), (12, 2), (13, 3))
        self.assertIn("closest", game.your_job(0))
        self.assertIsNone(game.your_job(1))
        self.assertIsNone(game.your_job(2))

    def test_a_tie_goes_to_one_rover_not_both(self):
        game = self.game((7, 3), (7, 5))
        self.assertEqual([bool(game.your_job(s)) for s in (0, 1)], [True, False])

    def test_a_rover_in_the_vault_is_told_to_wait(self):
        game = self.game((3, 27), (9, 2))
        self.assertIn("in the vault", game.your_job(0))

    def test_a_rover_shut_in_past_a_door_is_told_how_to_get_out(self):
        game = self.game((7, 10), (9, 2))
        self.assertIn("door shut behind you", game.your_job(0))
        self.assertIn("🏠", game.your_job(0))

    def test_a_rover_past_a_held_door_gets_the_class_job(self):
        game = self.game((7, 10), (7, 4))
        self.assertIsNone(game.your_job(0))
        self.assertIn("boulder back", game.next_job()["text"])

    def test_the_closest_rover_can_really_get_there(self):
        game = self.game((7, 9), (12, 2))           # 5 squares away, but through a shut door
        self.assertIn("closest", game.your_job(1))

    def test_a_crater_job_has_nobody_singled_out(self):
        game = self.game((9, 2), name="Crater Crossing")
        self.assertIsNone(game.your_job(0))

    def test_a_won_level_or_a_rover_that_left_has_no_job(self):
        game = self.game((8, 4))
        self.assertIsNone(game.your_job(7))
        game.won = 1
        self.assertIsNone(game.your_job(0))


class HelperTests(unittest.TestCase):
    H = planet_team.HELPER

    def game(self):
        game = Mission(0)
        game.enter(1, 1000)
        game.enter(self.H, 1000)
        return game

    def test_it_goes_to_the_plate_that_is_needed(self):
        game = self.game()
        self.assertTrue(game.helper_step())
        self.assertEqual(game.rovers[self.H], game.plates["A"][0])
        self.assertTrue(game.door_open("A"))

    def test_it_stays_while_it_holds_a_door(self):
        game = self.game()
        game.helper_step()
        self.assertFalse(game.helper_step())

    def test_it_moves_on_when_a_boulder_takes_over(self):
        game = self.game()
        game.helper_step()
        game.sunk.update(game.plates["A"])
        game.helper_step()
        self.assertEqual(game.rovers[self.H], game.plates["B"][0])

    def test_it_never_counts_towards_the_vault(self):
        game = self.game()
        game.rovers[self.H] = next(iter(game.vault))
        self.assertEqual((game.in_vault(), game.needed()), (0, 1))
        game.check_win(1001)
        self.assertFalse(game.won)

    def test_a_student_is_still_told_they_are_closest(self):
        self.assertIn("closest", self.game().your_job(1))

    def test_one_student_and_the_helper_can_finish_landing_bay(self):
        crew = Crew(1, 0)
        game = crew.game
        game.enter(self.H, crew.now)
        game.helper_step()
        crew.drive(0, (3, 4))              # A is held: use the boulder for good
        crew.push(0, "south", 3)
        game.helper_step()
        self.assertEqual(game.rovers[self.H], game.plates["B"][0])


class RecapTests(unittest.TestCase):
    def test_steps_pushes_and_the_trail_are_counted(self):
        crew = Crew(1, 0)
        start = crew.game.rovers[0]
        crew.push(0, "east", 1)
        crew.push(0, "west", 1)
        self.assertEqual(crew.game.steps, 2)
        self.assertEqual(crew.game.trail[start], 1)
        crew.drive(0, (3, 4))              # just above the first room's boulder
        crew.push(0, "south", 1)
        self.assertEqual(crew.game.pushes, 1)

    def test_the_recap_only_comes_with_a_win(self):
        crew = Crew(1, 0)
        self.assertFalse(crew.game.view(1000)["recap"])
        crew.game.won = 1001
        self.assertEqual(crew.game.view(1001)["recap"], {"steps": 0, "pushes": 0, "trail": []})


class PilotTests(unittest.TestCase):
    def fly(self, code, level=0):
        self.game = Mission(level)
        self.game.enter(0, 1000)
        return planet_team.fly(self.game, 0, code)

    def test_a_program_gives_the_moves_it_makes(self):
        self.assertEqual(self.fly("east(2)\nsouth()\nwait()")["ways"], ["east", "east", "south", "wait"])

    def test_loops_functions_and_variables_all_work(self):
        out = self.fly("def step(n):\n    east(n)\n    north()\nsize = 2\nfor i in range(2):\n    step(size)\n")
        self.assertIsNone(out["error"])
        self.assertEqual(out["ways"], ["east", "east", "north"] * 2)

    def test_look_sees_what_is_there_and_keeps_up_with_the_moves(self):
        out = self.fly('while look("west") != "rock":\n    west()\n')
        self.assertIsNone(out["error"])
        self.assertTrue(out["ways"])
        self.assertEqual(set(out["ways"]), {"west"})

    def test_every_word_look_gives_back_can_go_in_a_program(self):
        for word in ("rock", "door", "crater", "boulder", "plate", "vault", "ground"):
            out = self.fly(f'if look("east") == "{word}":\n    wait()\n')
            self.assertIsNone(out["error"], word)

    def test_a_word_look_never_gives_back_is_pointed_out(self):
        self.assertIn('Did you mean "door"', self.fly('if look("east") == "dor":\n    wait()\n')["error"])
        self.assertIn('look() never gives back "wall"', self.fly('if look("east") == "wall":\n    wait()\n')["error"])

    def test_look_knows_every_kind_of_square(self):
        game = Mission(0)
        game.enter(0, 1000)
        floor = planet_team.PilotFloor(game, 0)
        for spot, way, word in (((1, 1), "west", "rock"), ((7, 7), "east", "door"), ((7, 3), "east", "plate"),
                                ((3, 4), "south", "boulder"), ((1, 23), "east", "rock"), ((1, 2), "east", "ground")):
            floor.game.rovers[0] = spot
            self.assertEqual(floor.look(way), word, spot)
        floor.game.forced.add("C")
        floor.game.rovers[0] = (7, 23)
        self.assertEqual(floor.look("east"), "ground")
        floor.game.rovers[0] = (7, 24)
        self.assertEqual(floor.look("east"), "vault")
        crater = Mission(NUMBER["Crater Crossing"])
        crater.enter(0, 1000)
        floor = planet_team.PilotFloor(crater, 0)
        floor.game.rovers[0] = (9, 8)
        self.assertEqual(floor.look("east"), "crater")

    def test_a_boulder_a_program_pushes_moves_on_the_copy_and_not_on_the_map(self):
        game = Mission(0)
        game.enter(0, 1000)
        game.rovers[0] = (3, 4)
        out = planet_team.fly(game, 0, "south(3)")
        self.assertEqual(len(out["ways"]), 3)
        self.assertEqual(game.rovers[0], (3, 4))
        self.assertEqual(game.boulders[0]["at"], (3, 22))
        self.assertEqual(game.boulders[1]["at"], (4, 4))
        self.assertFalse(game.sunk)

    def test_driving_into_rock_stops_there_and_says_which_line(self):
        out = self.fly("east()\nwest(5)\n")
        self.assertEqual(out["ways"], ["east", "west", "west"])
        self.assertIn("Line 2 drives west", out["stopped"])

    def test_a_shut_door_is_named(self):
        game = Mission(0)
        game.enter(0, 1000)
        game.rovers[0] = (7, 6)
        self.assertIn("Door A is shut", planet_team.fly(game, 0, "east(2)")["stopped"])

    def test_a_program_stops_after_its_moves_run_out(self):
        out = self.fly("while True:\n    wait()\n")
        self.assertEqual(len(out["ways"]), planet_team.PILOT_STEPS)
        self.assertIn("60 moves", out["stopped"])

    def test_a_loop_that_never_moves_runs_out_of_time_rather_than_hanging(self):
        self.assertIn("too long", self.fly('while True:\n    look("east")\n')["error"])

    def test_a_stuck_loop_ends_fast_enough_not_to_stop_the_class(self):
        start = time.perf_counter()
        for code in ('while True:\n    look("east")\n', "n = 0\nwhile True:\n    n = n + 1\n"):
            self.assertIn("too long", self.fly(code)["error"])
        self.assertLess((time.perf_counter() - start) / 2, .1)

    def test_the_longest_program_still_fits_its_budget(self):
        code = 'for i in range(30):\n    if look("east") == "ground":\n        east()\n    else:\n        wait()\n    wait()\n'
        out = self.fly(code)
        self.assertIsNone(out["error"])
        self.assertEqual(len(out["ways"]), 60)

    def test_print_comes_back_to_the_page_for_finding_bugs(self):
        out = self.fly('print(look("west"))\nprint("hi")\n')
        self.assertEqual(out["prints"], ["ground", "hi"])

    def test_mistakes_say_what_is_wrong_and_where(self):
        out = self.fly("east()\nfor i in range(3)\n    west()\n")
        self.assertTrue(out["error"])
        self.assertEqual(out["ways"], [])
        self.assertEqual(out["line"], 2)

    def test_words_from_other_places_are_turned_away_kindly(self):
        self.assertIn("On the team map", self.fly("report(3)")["error"])
        self.assertIn("On the team map", self.fly("jump(\"east\")")["error"])
        self.assertIsNotNone(self.fly("import os")["error"])
        self.assertIsNotNone(self.fly("open('x')")["error"])


class ClassroomSide(unittest.TestCase):
    Base = test_planet.ClassroomTests
    setUp, get, post, join = Base.setUp, Base.get, Base.post, Base.join

    def tearDown(self):
        self.Base.tearDown(self)
        server.team_set(False)
        server.team_room["here"].clear()
        server.team_restart()
        server.planet_class_settings["team_wins"] = []
        server.planet_class_settings["team_best"] = {}

    def admin(self, action, **data):
        return self.post("/admin", dict(data, key=server.ADMIN_KEY, action=action))

    def look(self, pid=None, **query):
        args = "&".join(f"{k}={v}" for k, v in ({"id": pid, **query} if pid else query).items())
        return self.get("/planet/team?" + args)

    def go(self, pid, way):
        server.team_room["here"][pid]["stepped"] = 0
        return self.post("/planet/team", {"id": pid, "do": "move", "way": way})

    def enter(self, *names, level=BIG):
        self.admin("planet_team", on=True)
        server.team_restart(level)
        pids = [self.join(n) for n in names]
        for pid in pids:
            self.look(pid)
        return pids

    def shout(self, pid, key):
        return self.post("/planet/team", {"id": pid, "do": "shout", "key": key})

    def test_the_teacher_is_warned_when_the_server_is_behind_its_files(self):
        started = server.STARTED
        self.addCleanup(lambda: setattr(server, "STARTED", started))
        server.STARTED = server.time.time() + 60
        self.assertEqual(self.get("/planet/overview")["out_of_date"], [])
        server.STARTED = 0
        self.assertIn("server.py", self.get("/planet/overview")["out_of_date"])

    def test_each_student_gets_their_own_job_and_the_class_screen_gets_none(self):
        ada, bob = self.enter("Ada", "Bob", level=0)
        game = server.team_room["mission"]
        game.rovers[server.team_room["here"][ada]["seat"]] = game.plates["A"][0]
        self.assertIn("holding door A", self.look(ada)["mine"])
        self.assertNotIn("holding", self.look(bob)["mine"] or "")
        self.assertIsNone(self.look()["mine"])

    def test_todays_class_lists_the_team_bests_in_level_order(self):
        server.planet_class_settings["team_best"].update({"2": 412, "0": 95})
        self.assertEqual(self.get("/planet/today")["team_best"],
                         [{"name": "Landing Bay", "secs": 95}, {"name": "Crater Crossing", "secs": 412}])

    def test_the_helper_comes_when_asked_and_shows_on_the_map(self):
        self.addCleanup(lambda: server.team_helper(False))
        ada, = self.enter("Ada", level=0)
        self.admin("planet_team_helper")
        out = self.look(ada)
        self.assertIn(planet_team.HELPER, [row[0] for row in out["rovers"]])
        self.assertIn("🤖 Helper", [p["tag"] for p in out["people"]])
        self.assertEqual(self.get("/planet/overview")["team_rovers"], 1)
        self.admin("planet_team_helper")
        self.assertNotIn(planet_team.HELPER, [row[0] for row in self.look(ada)["rovers"]])

    def test_the_helper_comes_along_to_the_next_level(self):
        self.addCleanup(lambda: server.team_helper(False))
        ada, = self.enter("Ada", level=0)
        self.admin("planet_team_helper")
        self.admin("planet_team_level", level=1)
        self.assertIn(planet_team.HELPER, [row[0] for row in self.look(ada)["rovers"]])

    def test_a_level_the_helper_helped_on_earns_nothing(self):
        self.addCleanup(lambda: server.team_helper(False))
        ada, = self.enter("Ada", level=0)
        self.admin("planet_team_helper")
        out = self.into_vault(ada, server.time.time() - 50)
        self.assertTrue(out["won"])
        self.assertIsNone(out["best"])
        self.assertEqual(server.planet_class_settings["team_wins"], [])

    def test_the_teacher_sees_how_many_are_on_the_map(self):
        self.enter("Ada", "Bob", level=0)
        overview = self.get("/planet/overview")
        self.assertEqual((overview["team_rovers"], overview["team_vault"]), (2, 0))

    def test_the_lounge_shelf_carries_the_class_best(self):
        server.planet_class_settings["team_best"]["0"] = 95
        server.lounge_set(True) if hasattr(server, "lounge_set") else server.planet_lounge.update(open=True)
        self.addCleanup(lambda: server.planet_lounge.update(open=False))
        ada = self.join("Ada")
        shelf = self.get(f"/planet/lounge?id={ada}")["trophies"]
        self.assertEqual(shelf[0]["best"], 95)
        self.assertIsNone(shelf[1]["best"])

    def test_the_teacher_can_move_the_class_to_any_level(self):
        ada, = self.enter("Ada", level=0)
        self.admin("planet_team_level", level=4)
        self.assertEqual(self.look(ada)["name"], "Three-Step Bridge")
        self.assertEqual(self.get("/planet/overview")["team_level"], 4)
        self.admin("planet_team_level", level=99)
        self.assertEqual(self.look(ada)["level"], 4)

    def test_a_shout_goes_to_everyone_on_the_map(self):
        ada, bob = self.enter("Ada", "Bob")
        self.shout(ada, "help")
        seat = server.team_room["here"][ada]["seat"]
        self.assertEqual(self.look(bob)["shouts"], [[1, seat, "🆘 Help me here!"]])

    def test_only_the_fixed_shouts_get_through(self):
        ada, _ = self.enter("Ada", "Bob")
        self.assertEqual(self.shout(ada, "you smell")["shouts"], [])

    def test_a_rover_cant_shout_over_and_over(self):
        ada, _ = self.enter("Ada", "Bob")
        self.shout(ada, "help")
        self.assertEqual(len(self.shout(ada, "look")["shouts"]), 1)

    def test_a_shout_fades_away(self):
        ada, bob = self.enter("Ada", "Bob")
        self.shout(ada, "help")
        server.team_room["mission"].shouts[0][3] -= planet_team.SHOUT_LASTS
        self.assertEqual(self.look(bob)["shouts"], [])

    def test_every_shout_button_on_the_page_is_a_real_shout(self):
        with open(os.path.join(HERE, "planet.html"), encoding="utf-8") as f:
            found = set(re.findall(r'data-shout="(\w+)"', f.read()))
        self.assertEqual(found, set(planet_team.SHOUTS))

    def test_a_program_comes_back_for_the_page_to_drive_and_moves_nothing_yet(self):
        ada, = self.enter("Ada", level=0)
        before = list(server.team_room["mission"].rovers.values())
        out = self.post("/planet/team", {"id": ada, "do": "code", "code": "east(2)"})
        self.assertEqual(out["program"]["ways"], ["east", "east"])
        self.assertEqual(list(server.team_room["mission"].rovers.values()), before)

    def test_programs_cant_be_sent_over_and_over(self):
        ada, = self.enter("Ada", level=0)
        self.post("/planet/team", {"id": ada, "do": "code", "code": "east(2)"})
        self.assertNotIn("program", self.post("/planet/team", {"id": ada, "do": "code", "code": "east(2)"}))

    def test_a_program_that_is_not_text_does_nothing_bad(self):
        ada, = self.enter("Ada", level=0)
        self.assertEqual(self.post("/planet/team", {"id": ada, "do": "code", "code": 5})["program"]["ways"], [])

    def into_vault(self, pid, began):
        game = server.team_room["mission"]
        game.began, game.rovers[server.team_room["here"][pid]["seat"]] = began, next(iter(game.vault))
        return self.look(pid)

    def test_a_first_win_sets_the_time_to_beat_and_a_faster_one_beats_it(self):
        ada, = self.enter("Ada", level=0)
        now = server.time.time()
        out = self.into_vault(ada, now - 200)
        self.assertEqual(out["record"], "first")
        self.assertEqual(out["best"], 200)
        server.team_restart(0)
        out = self.look(ada)
        self.assertEqual(out["best"], 200)
        self.assertIsNone(out["record"])
        out = self.into_vault(ada, now - 150)
        self.assertAlmostEqual(out["record"], 50, delta=2)
        self.assertLess(out["best"], 200)

    def test_a_slower_win_leaves_the_class_best_alone(self):
        ada, = self.enter("Ada", level=0)
        server.planet_class_settings["team_best"]["0"] = 100
        out = self.into_vault(ada, server.time.time() - 300)
        self.assertIsNone(out["record"])
        self.assertEqual(out["best"], 100)

    def test_opening_the_doors_earns_no_class_best(self):
        ada, = self.enter("Ada", level=0)
        self.admin("planet_team_doors")
        out = self.into_vault(ada, server.time.time() - 5)
        self.assertIsNone(out["record"])
        self.assertIsNone(out["best"])

    def test_the_teacher_opens_it_and_a_button_comes_up(self):
        pid = self.join("Ada")
        self.assertEqual(self.look(pid), {"open": False})
        self.assertFalse(self.get(f"/planet/ping?id={pid}")["team"])
        self.assertIn("open", self.admin("planet_team", on=True)["ok"])
        self.assertTrue(self.get(f"/planet/ping?id={pid}")["team"])
        self.assertTrue(self.get(f"/planet/state?id={pid}")["team"])
        self.assertTrue(self.get("/planet/overview")["team"])

    def test_everyone_sees_each_others_rovers_move(self):
        ada, bo = self.enter("Ada", "Bo")
        seen = self.look(bo)
        self.assertEqual(len(seen["rovers"]), 2)
        self.assertEqual({row["tag"] for row in seen["people"]}, {"Ada", "Bo"})
        you = self.look(ada)["you"]
        before = next(row for row in seen["rovers"] if row[0] == you)
        self.go(ada, "north")
        after = next(row for row in self.look(bo)["rovers"] if row[0] == you)
        self.assertEqual(after[1], before[1] - 1)

    def test_the_map_and_the_people_come_only_when_a_page_needs_them(self):
        pid = self.enter("Ada")[0]
        first = self.look(pid)
        self.assertEqual(first["map"], list(LEVELS[BIG]["map"]))
        self.assertIn("people", first)
        later = self.look(pid, after=first["seq"], roster=first["roster"], level=first["level"])
        self.assertNotIn("map", later)
        self.assertNotIn("people", later)

    def test_a_step_doesnt_send_the_whole_map_again(self):
        pid = self.enter("Ada")[0]
        first = self.look(pid)
        server.team_room["here"][pid]["stepped"] = 0
        out = self.post("/planet/team", {"id": pid, "do": "move", "way": "north",
                                         "level": first["level"], "roster": first["roster"]})
        self.assertNotIn("map", out)
        self.assertNotIn("people", out)

    def test_a_shut_door_tip_comes_back_to_the_driver(self):
        pid = self.enter("Ada")[0]
        room = server.team_room
        room["mission"].rovers[room["here"][pid]["seat"]] = (11, 11)
        self.assertIn("Door A", self.go(pid, "west")["tip"])

    def test_steps_are_limited_to_what_a_key_can_do(self):
        pid = self.enter("Ada")[0]
        self.go(pid, "north")
        spot = server.team_room["mission"].rovers[server.team_room["here"][pid]["seat"]]
        self.post("/planet/team", {"id": pid, "do": "move", "way": "north"})
        self.assertEqual(server.team_room["mission"].rovers[server.team_room["here"][pid]["seat"]], spot)

    def test_a_bad_way_is_ignored(self):
        pid = self.enter("Ada")[0]
        self.assertTrue(self.go(pid, "up")["open"])

    def test_someone_who_leaves_stops_holding_a_door_and_comes_back_to_the_same_place(self):
        ada, bo = self.enter("Ada", "Bo")
        room = server.team_room
        seat = room["here"][ada]["seat"]
        room["mission"].rovers[seat] = (12, 12)
        self.assertTrue(self.look(bo)["doors"]["A"]["open"])
        room["here"][ada]["seen"] = 0
        seen = self.look(bo)
        self.assertFalse(seen["doors"]["A"]["open"])
        self.assertEqual(len(seen["rovers"]), 1)
        self.assertEqual(self.look(ada)["you"], seat)
        self.assertEqual(room["mission"].rovers[seat], (12, 12))

    def test_a_watcher_is_not_a_rover(self):
        self.enter("Ada")
        seen = self.look()
        self.assertTrue(seen["open"])
        self.assertIsNone(seen["you"])
        self.assertEqual(len(seen["rovers"]), 1)

    def test_seats_not_ids_go_to_the_class(self):
        pid = self.enter("Ada")[0]
        self.assertNotIn(pid, json.dumps(self.look(pid)))

    def test_turning_the_switch_off_keeps_the_mission(self):
        pid = self.enter("Ada")[0]
        self.go(pid, "north")
        mission = server.team_room["mission"]
        self.admin("planet_team", on=False)
        self.assertEqual(self.post("/planet/team", {"id": pid, "do": "move", "way": "north"}), {"open": False})
        self.admin("planet_team", on=True)
        self.assertIs(server.team_room["mission"], mission)

    def test_the_teacher_can_start_again_and_open_every_door(self):
        pid = self.enter("Ada")[0]
        mission = server.team_room["mission"]
        self.assertIn("door", self.admin("planet_team_doors")["ok"])
        self.assertTrue(self.look(pid)["doors"]["V"]["open"])
        self.assertIn("again", self.admin("planet_team_restart")["ok"])
        self.assertIsNot(server.team_room["mission"], mission)
        self.assertFalse(self.look(pid)["doors"]["A"]["open"])

    def test_the_class_starts_on_the_first_level(self):
        self.admin("planet_team_restart")
        self.admin("planet_team", on=True)
        pid = self.join("Ada")
        seen = self.look(pid)
        self.assertEqual((seen["level"], seen["name"]), (0, LEVELS[0]["name"]))
        self.assertEqual(seen["map"], list(LEVELS[0]["map"]))

    def win(self, pids):
        room = server.team_room
        for pid in pids:
            room["mission"].rovers[room["here"][pid]["seat"]] = sorted(room["mission"].vault)[0]
        return self.look(pids[0])

    def test_finishing_a_level_moves_everyone_on_after_a_pause(self):
        ada, bo = self.enter("Ada", "Bo", level=0)
        seen = self.win([ada, bo])
        self.assertTrue(seen["won"])
        self.assertEqual(seen["level"], 0)
        self.assertGreater(seen["next_in"], 0)
        server.team_room["mission"].won -= server.TEAM_PAUSE
        seen = self.look(ada, level=0)
        self.assertEqual(seen["level"], 1)
        self.assertFalse(seen["won"])
        self.assertEqual(seen["map"], list(LEVELS[1]["map"]))
        self.assertEqual(len(seen["rovers"]), 2)
        mission = server.team_room["mission"]
        self.assertTrue(all(spot in mission.starts for spot in mission.rovers.values()))

    def test_a_rover_away_when_the_level_changes_comes_back_on_the_new_lander(self):
        ada, bo = self.enter("Ada", "Bo", level=0)
        self.win([ada, bo])
        room = server.team_room
        room["here"][bo]["seen"] = 0
        room["mission"].won -= server.TEAM_PAUSE
        self.look(ada)
        self.look(bo)
        self.assertIn(room["mission"].rovers[room["here"][bo]["seat"]], room["mission"].starts)

    def test_the_last_level_stays_won(self):
        ada, bo = self.enter("Ada", "Bo")
        self.win([ada, bo])
        server.team_room["mission"].won -= 1000
        seen = self.look(ada)
        self.assertEqual(seen["level"], BIG)
        self.assertTrue(seen["won"])
        self.assertEqual(seen["next_in"], 0)

    def test_the_teacher_can_skip_a_level(self):
        pid = self.enter("Ada", level=0)[0]
        self.assertIn(LEVELS[1]["name"], self.admin("planet_team_next")["ok"])
        self.assertEqual(self.look(pid)["level"], 1)
        server.team_restart(BIG)
        self.assertIn("last", self.admin("planet_team_next")["ok"])

    def test_a_student_the_teacher_removed_does_not_break_the_next_level(self):
        ada, bo = self.enter("Ada", "Bo", level=0)
        del server.players[bo]
        self.admin("planet_team_next")
        self.assertEqual(len(self.look(ada)["rovers"]), 1)

    def test_a_student_not_signed_in_is_told_to_join(self):
        self.admin("planet_team", on=True)
        self.assertEqual(self.look("nobody"), {"error": "join"})
        self.assertEqual(self.post("/planet/team", {"id": "nobody", "do": "home"}), {"error": "join"})

    def test_only_the_classes_trophies_are_saved(self):
        pid = self.enter("Ada", level=0)[0]
        self.win([pid])
        server.save_state()
        with open(server.STATE_FILE, encoding="utf-8") as f:
            saved = json.load(f)
        self.assertEqual(saved["planet_class"]["team_wins"], [0])
        self.assertNotIn("team", {k for k in saved if k != "planet_class"})

    def test_the_page_has_everything_the_script_asks_for(self):
        script = open(os.path.join(HERE, "planet_team.js"), encoding="utf-8").read()
        page = open(os.path.join(HERE, "planet.html"), encoding="utf-8").read()
        watch = open(os.path.join(HERE, "planet_team_watch.html"), encoding="utf-8").read()
        self.assertIn('src="/planet/team.js"', page)
        self.assertIn('src="/planet/team.js"', watch)
        for name in set(re.findall(r'\$\("(\w+)"\)', script)):
            self.assertIn(f'id="{name}"', page)
        for name in ("teamMap", "teamWin", "teamLevel", "teamGoal", "teamDoors", "teamNews", "teamSay"):
            self.assertIn(f'id="{name}"', watch)


class LoungeUpdates(unittest.TestCase):
    """What the Team Mission and the fresh room added to the Rover Lounge."""

    Base = test_planet.ClassroomTests
    setUp, get, post, join = Base.setUp, Base.get, Base.post, Base.join

    def tearDown(self):
        self.Base.tearDown(self)
        server.lounge_set(False)
        server.team_set(False)
        server.team_room["here"].clear()
        server.team_restart()
        server.planet_class_settings["team_wins"] = []
        server.planet_class_settings["team_best"] = {}

    def admin(self, action, **data):
        return self.post("/admin", dict(data, key=server.ADMIN_KEY, action=action))

    def enter(self, *names):
        self.admin("planet_lounge", on=True)
        pids = [self.join(n) for n in names]
        for pid in pids:
            self.get(f"/planet/lounge?id={pid}")
        return pids

    def act(self, pid, what, **more):
        return self.post("/planet/lounge", dict(more, id=pid, do=what, after=0))

    def test_the_class_screen_watches_without_a_rover(self):
        self.enter("Ada")
        seen = self.get("/planet/lounge")
        self.assertTrue(seen["open"])
        self.assertIsNone(seen["you"])
        self.assertEqual(len(seen["rovers"]), 1)
        self.assertEqual(len(server.planet_lounge["here"]), 1)

    def test_a_watcher_sees_nothing_when_it_is_closed_and_a_bad_id_still_joins(self):
        self.assertEqual(self.get("/planet/lounge"), {"open": False})
        self.admin("planet_lounge", on=True)
        self.assertEqual(self.get("/planet/lounge?id=nobody"), {"error": "join"})

    def test_new_tricks_and_emotes_reach_everyone(self):
        ada, bo = self.enter("Ada", "Bo")
        self.act(ada, "spin")
        server.planet_lounge["here"][ada]["acted"] = 0
        out = self.act(ada, "emote", emote="🥳")
        self.assertEqual([e["kind"] for e in out["events"]], ["spin", "emote"])
        self.assertEqual(out["events"][1]["emote"], "🥳")

    def test_an_emote_must_come_from_the_list(self):
        ada = self.enter("Ada")[0]
        self.assertEqual(self.act(ada, "emote", emote="rude word")["events"], [])

    def test_a_kick_reaches_everyone_and_stays_in_the_room(self):
        ada, bo = self.enter("Ada", "Bo")
        self.act(ada, "kick", x=99, y=-5, vx=500, vy=1)
        ball = self.get(f"/planet/lounge?id={bo}")["ball"]
        self.assertEqual(ball["n"], 1)
        self.assertEqual((ball["x"], ball["y"]), (server.LOUNGE_COLS - .3, server.LOUNGE_FLOOR + .3))
        self.assertEqual(ball["vx"], server.LOUNGE_KICK)

    def test_kicks_are_limited_and_nonsense_is_ignored(self):
        ada = self.enter("Ada")[0]
        self.act(ada, "kick", x=1, y=5, vx=1, vy=1)
        self.act(ada, "kick", x=2, y=5, vx=1, vy=1)
        self.assertEqual(server.planet_lounge["ball"]["n"], 1)
        server.planet_lounge["here"][ada]["kicked"] = 0
        self.act(ada, "kick", x="left", y=5, vx=1, vy=1)
        self.assertEqual(server.planet_lounge["ball"]["n"], 1)

    def win(self, *names):
        self.admin("planet_team", on=True)
        pids = [self.join(n) for n in names]
        for pid in pids:
            self.get(f"/planet/team?id={pid}")
        room = server.team_room
        for pid in pids:
            room["mission"].rovers[room["here"][pid]["seat"]] = sorted(room["mission"].vault)[0]
        self.get(f"/planet/team?id={pids[0]}")

    def test_a_finished_level_puts_a_trophy_on_the_shelf_for_good(self):
        self.win("Ada")
        pid = self.enter("Bo")[0]
        shelf = self.get(f"/planet/lounge?id={pid}")["trophies"]
        self.assertEqual(len(shelf), len(LEVELS))
        self.assertEqual([t["won"] for t in shelf[:2]], [True, False])
        self.admin("planet_team_restart")
        self.assertTrue(self.get(f"/planet/lounge?id={pid}")["trophies"][0]["won"])

    def test_the_teachers_button_does_not_earn_a_trophy(self):
        self.admin("planet_team", on=True)
        self.admin("planet_team_doors")
        self.win("Ada")
        self.assertEqual(server.planet_class_settings["team_wins"], [])

    def test_a_trophy_says_who_won_it_as_nobody(self):
        self.win("Ada")
        pid = self.enter("Bo")[0]
        self.assertNotIn("Ada", json.dumps(self.get(f"/planet/lounge?id={pid}")["trophies"]))

    def test_the_watch_page_has_everything_the_script_asks_for(self):
        script = open(os.path.join(HERE, "planet_lounge.js"), encoding="utf-8").read()
        page = open(os.path.join(HERE, "planet_lounge_watch.html"), encoding="utf-8").read()
        for name in ("loungeRoom", "loungeSay", "loungeStage", "loungeWins", "loungeEmotes", "loungeRover", "lounge"):
            self.assertIn(f'id="{name}"', page)
            self.assertIn(f'$("{name}")', script)


class PredictIt(unittest.TestCase):
    Base = test_planet.ClassroomTests
    setUp, get, post, join = Base.setUp, Base.get, Base.post, Base.join

    def tearDown(self):
        self.Base.tearDown(self)
        server.predict_open("")

    def admin(self, action, **data):
        return self.post("/admin", dict(data, key=server.ADMIN_KEY, action=action))

    def vote(self, pid, choice):
        return self.post("/planet/predict", {"id": pid, "choice": choice})

    def test_every_question_has_its_real_answer_among_four_different_ones(self):
        for code, options in planet_predict.QUESTIONS:
            self.assertEqual(len(set(options)), 4, code)
            self.assertIn(len(planet_predict.play(code)) - 1, options, code)

    def test_no_question_drives_into_the_edge_and_stops_early(self):
        class Strict(planet_predict.Field):
            def act(self, word, way=None):
                assert word == "wait" or not self.rock(self.next_to(word)), "drove into the edge"
                super().act(word, way)
        for code, _ in planet_predict.QUESTIONS:
            planet.Rover(code, Strict(), {"look": None}).run()

    def test_a_question_reaches_a_student_without_its_answer(self):
        ada = self.join("Ada")
        self.assertIsNone(self.get(f"/planet/ping?id={ada}")["predict"])
        self.admin("planet_predict", n=3)
        question = self.get(f"/planet/ping?id={ada}")["predict"]
        self.assertEqual(question["options"], list(planet_predict.QUESTIONS[3][1]))
        self.assertNotIn("answer", question)

    def test_the_class_screen_hides_the_vote_and_the_route_until_the_reveal(self):
        ada = self.join("Ada")
        self.admin("planet_predict", n=3)
        self.vote(ada, 6)
        view = self.get("/planet/predict/view")
        self.assertEqual(view["voted"], 1)
        for secret in ("tally", "path", "answer"):
            self.assertNotIn(secret, view)
        self.admin("planet_predict_reveal")
        view = self.get("/planet/predict/view")
        self.assertEqual((view["answer"], view["tally"]["6"], len(view["path"])), (6, 1, 7))

    def test_a_student_can_change_their_mind_but_not_after_the_reveal(self):
        ada = self.join("Ada")
        self.admin("planet_predict", n=3)
        self.vote(ada, 3)
        self.assertEqual(self.vote(ada, 6)["voted"], 6)
        self.admin("planet_predict_reveal")
        self.assertEqual(self.vote(ada, 3)["voted"], 6)

    def test_only_the_answers_on_offer_count(self):
        ada = self.join("Ada")
        self.admin("planet_predict", n=3)
        self.assertIsNone(self.vote(ada, 99)["voted"])
        self.assertIsNone(self.vote(ada, "you smell")["voted"])

    def test_no_names_or_ids_reach_the_class_screen(self):
        ada = self.join("Ada")
        self.admin("planet_predict", n=3)
        self.vote(ada, 6)
        self.admin("planet_predict_reveal")
        text = json.dumps(self.get("/planet/predict/view"))
        self.assertNotIn("Ada", text)
        self.assertNotIn(ada, text)

    def test_a_new_question_starts_with_no_votes_and_none_closes_it(self):
        ada = self.join("Ada")
        self.admin("planet_predict", n=3)
        self.vote(ada, 6)
        self.admin("planet_predict", n=4)
        self.assertEqual(self.get("/planet/predict/view")["voted"], 0)
        self.admin("planet_predict", n="")
        self.assertIsNone(self.get(f"/planet/ping?id={ada}")["predict"])

    def test_reveal_needs_a_question_and_the_teachers_key(self):
        self.assertIn("error", self.post("/admin", {"key": "nope", "action": "planet_predict_reveal"}))
        self.admin("planet_predict", n=3)
        self.post("/admin", {"key": "nope", "action": "planet_predict_reveal"})
        self.assertFalse(server.predict_room["revealed"])

    def test_the_pages_are_served(self):
        self.assertIn("Predict It", urlopen(self.base + "/planet/predict").read().decode())
        self.assertIn("predictHear", urlopen(self.base + "/planet/predict.js").read().decode())


class BugHunts(unittest.TestCase):
    Base = test_planet.ClassroomTests
    setUp, get, post, join = Base.setUp, Base.get, Base.post, Base.join
    transmit = Base.transmit

    def tearDown(self):
        self.Base.tearDown(self)
        server.planet_class_settings["challenge"] = None
        server.planet_race.update(key=None, runs={})

    def admin(self, action, **data):
        return self.post("/admin", dict(data, key=server.ADMIN_KEY, action=action))

    def test_every_broken_program_loses_and_its_one_fix_wins(self):
        for n, (key, what, code, (wrong, right)) in enumerate(planet.BUG_HUNTS):
            self.admin("planet_bug", n=n)
            self.assertEqual(code.count(wrong), 1, what)
            ada = self.join(f"Kid{n}")
            broken = self.transmit(ada, key, code)
            self.assertFalse(all(r["reached"] for r in broken["runs"]), what)
            fixed = self.transmit(ada, key, code.replace(wrong, right))
            self.assertTrue(all(r["reached"] for r in fixed["runs"]), what)

    def test_a_bug_hunt_reaches_the_students_page_with_the_code(self):
        ada = self.join("Ada")
        self.admin("planet_bug", n=3)
        challenge = self.get(f"/planet/state?id={ada}")["challenge"]
        self.assertEqual(challenge["bug"], planet.BUG_HUNTS[3][2])
        self.assertEqual(self.get(f"/planet/ping?id={ada}")["challenge"], challenge["tag"])

    def test_two_hunts_on_one_level_look_different_to_a_page(self):
        ada = self.join("Ada")
        self.admin("planet_bug", n=3)
        first = self.get(f"/planet/ping?id={ada}")["challenge"]
        self.admin("planet_bug", n=4)
        self.assertNotEqual(self.get(f"/planet/ping?id={ada}")["challenge"], first)

    def test_none_ends_the_hunt(self):
        self.admin("planet_bug", n=3)
        self.admin("planet_bug", n="")
        self.assertIsNone(self.get("/planet/overview")["challenge"])

    def test_two_misses_bring_a_clue_and_one_does_not(self):
        self.admin("planet_bug", n=3)
        ada = self.join("Ada")
        code = planet.BUG_HUNTS[3][2]
        self.assertIsNone(self.transmit(ada, "1b", code)["rewards"]["bug_clue"])
        self.assertEqual(self.transmit(ada, "1b", code + "\n")["rewards"]["bug_clue"], planet.BUG_HUNTS[3][1])

    def test_an_ordinary_challenge_has_no_clue(self):
        self.admin("planet_challenge", site="1a")
        ada = self.join("Ada")
        for _ in range(3):
            self.assertIsNone(self.transmit(ada, "1a", "wait()")["rewards"]["bug_clue"])

    def test_todays_class_lists_who_played_and_how_far(self):
        ada, bob = self.join("Ada"), self.join("Bob")
        self.transmit(ada, "1a", "wait()")
        self.transmit(ada, "1a", planet.find_site("1a")[2]["reference"])
        today = self.get("/planet/today")["students"]
        self.assertEqual([s["name"] for s in today], ["Ada"])
        self.assertEqual({k: today[0][k] for k in ("runs", "wins", "new_levels", "on")},
                         {"runs": 2, "wins": 1, "new_levels": 1, "on": "1b"})

    def test_winning_a_level_again_is_not_a_new_level(self):
        ada = self.join("Ada")
        code = planet.find_site("1a")[2]["reference"]
        self.transmit(ada, "1a", code)
        self.transmit(ada, "1a", code + "\n")
        self.assertEqual(self.get("/planet/today")["students"][0]["new_levels"], 1)

    def test_a_win_joins_the_race(self):
        self.admin("planet_bug", n=3)
        ada = self.join("Ada")
        self.transmit(ada, "1b", planet.find_site("1b")[2]["reference"])
        self.assertEqual(len(self.get("/planet/race/lineup")["racers"]), 1)

    def test_a_teachers_message_comes_once_to_each_page_and_only_the_fixed_ones(self):
        ada = self.join("Ada")
        n = self.get(f"/planet/ping?id={ada}")["notice"]["n"]
        self.admin("planet_notice", what="eyes")
        notice = self.get(f"/planet/ping?id={ada}")["notice"]
        self.assertEqual((notice["n"], notice["title"]), (n + 1, "Eyes on your teacher, please!"))
        self.admin("planet_notice", what="rude words")
        self.assertEqual(self.get(f"/planet/ping?id={ada}")["notice"]["n"], n + 1)


class ClassRace(unittest.TestCase):
    Base = test_planet.ClassroomTests
    setUp, get, post, join = Base.setUp, Base.get, Base.post, Base.join
    transmit = Base.transmit

    def tearDown(self):
        self.Base.tearDown(self)
        server.planet_class_settings["challenge"] = None
        server.planet_race.update(key=None, runs={})

    def challenge(self, key="1a"):
        self.post("/admin", {"key": server.ADMIN_KEY, "action": "planet_challenge", "site": key})

    def lineup(self):
        return self.get("/planet/race/lineup")

    def test_a_win_on_the_challenge_joins_the_race_with_its_route(self):
        self.challenge()
        ada = self.join("Ada")
        code = test_planet.site("1a")[2]["reference"]
        self.assertTrue(self.transmit(ada, "1a", code)["rewards"]["in_race"])
        racers = self.lineup()["racers"]
        self.assertEqual([r["name"] for r in racers], ["Ada"])
        self.assertGreater(len(racers[0]["path"]), 1)
        self.assertEqual(racers[0]["chars"], server.count_chars(code, "python"))
        self.assertNotIn(ada, json.dumps(racers))

    def test_a_miss_or_another_level_stays_out(self):
        self.challenge()
        ada = self.join("Ada")
        self.assertFalse(self.transmit(ada, "1a", "wait()")["rewards"]["in_race"])
        self.assertEqual(self.lineup()["racers"], [])

    def test_only_a_quicker_win_replaces_the_one_in_the_race(self):
        self.challenge()
        ada = self.join("Ada")
        code = test_planet.site("1a")[2]["reference"]
        self.transmit(ada, "1a", code)
        kept = self.lineup()["racers"][0]
        self.transmit(ada, "1a", "wait()\n" + code)
        self.assertEqual(self.lineup()["racers"][0]["path"], kept["path"])

    def test_a_win_after_the_challenge_ends_stays_out(self):
        self.challenge()
        self.post("/admin", {"key": server.ADMIN_KEY, "action": "planet_challenge", "site": ""})
        ada = self.join("Ada")
        out = self.transmit(ada, "1a", test_planet.site("1a")[2]["reference"])
        self.assertFalse(out["rewards"]["in_race"])

    def test_a_challenge_that_outlived_a_restart_still_fills_the_race(self):
        self.challenge()
        server.planet_race.update(key=None, runs={})       # what a restart leaves
        ada = self.join("Ada")
        self.transmit(ada, "1a", test_planet.site("1a")[2]["reference"])
        self.assertEqual(len(self.lineup()["racers"]), 1)

    def test_the_race_keeps_a_winners_code_without_comments(self):
        self.challenge()
        ada = self.join("Ada")
        code = test_planet.site("1a")[2]["reference"]
        self.transmit(ada, "1a", "# rude words here\n" + code)
        self.assertEqual(self.lineup()["racers"][0]["code"], code.strip())

    def test_a_new_challenge_starts_a_new_race_but_ending_one_keeps_it(self):
        self.challenge()
        ada = self.join("Ada")
        self.transmit(ada, "1a", test_planet.site("1a")[2]["reference"])
        self.post("/admin", {"key": server.ADMIN_KEY, "action": "planet_challenge", "site": ""})
        self.assertEqual(len(self.lineup()["racers"]), 1)
        self.challenge("1b")
        self.assertEqual(self.lineup()["racers"], [])

    def test_no_challenge_means_an_empty_lineup(self):
        self.assertEqual(self.lineup(), {"key": None, "name": None, "racers": []})

    def test_the_race_page_is_served(self):
        self.assertIn("Class Race", urlopen(self.base + "/planet/race").read().decode())

    def test_the_teacher_page_links_to_it(self):
        self.assertIn('href="/planet/race"', urlopen(self.base + "/planet/teacher").read().decode())


if __name__ == "__main__":
    unittest.main()
