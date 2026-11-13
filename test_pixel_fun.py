"""Coins and the shop, homes, fishing, and the race and dance rounds."""
import unittest
from unittest.mock import patch

import pixel
import server


class Fun(unittest.TestCase):
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
        self.mia, self.ben, self.alex = [self.kid(name) for name in ("Mia", "Ben", "Alex")]

    def restore(self):
        server.pixel_room, server.players, server.pixel_class, server.pixel_feed = self.saved

    def kid(self, name):
        p = {"id": "private-" + name, "name": name}
        server.players[p["id"]] = p
        server.pixel_entry(p)
        self.assertTrue(server.room_do(p, {"what": "join"})["ok"])
        return p

    def do(self, p, what, **more):
        return server.room_do(p, dict(what=what, **more))

    def entry(self, p):
        return server.pixel_entry(p)

    def spot(self, p):
        return server.pixel_room["here"][p["id"]]

    def view(self, p, after=-1, watch=0):
        return server.room_view(p, after, watch)

    def advance(self, seconds):
        self.clock += seconds
        for spot in server.pixel_room["here"].values():
            spot["seen"] = self.clock
        server.room_keep_up()


class Coins(Fun):
    def test_a_mission_pays_for_the_first_finish_and_each_star(self):
        out = server.pixel_record(self.mia, "a1", "x", {"stars": [True, True, False], "error": None, "steps": []})
        self.assertEqual(out["coins"], pixel.COINS_FIRST + 2 * pixel.COINS_STAR)
        again = server.pixel_record(self.mia, "a1", "x", {"stars": [True, True, True], "error": None, "steps": []})
        self.assertEqual(again["coins"], pixel.COINS_STAR)
        self.assertEqual(server.pixel_record(self.mia, "a1", "x", {"stars": [True] * 3, "error": None, "steps": []})["coins"], 0)
        self.assertEqual(self.entry(self.mia)["coins"], pixel.COINS_FIRST + 3 * pixel.COINS_STAR)

    def test_stars_from_before_coins_are_paid_for(self):
        p = {"id": "old", "name": "Old", "pixel": {"solved": {"a1": [True, True, False], "a2": [False] * 3}, "found": ["park0"]}}
        self.assertEqual(server.pixel_entry(p)["coins"], pixel.COINS_FIRST + 2 * pixel.COINS_STAR + pixel.COINS_GEM)

    def test_playing_pays_only_so_much_a_day_but_missions_always_pay(self):
        self.assertEqual(server.pixel_pay(self.mia, pixel.PLAY_COINS_DAY - 1), pixel.PLAY_COINS_DAY - 1)
        self.assertEqual(server.pixel_pay(self.mia, 5), 1)
        self.assertEqual(server.pixel_pay(self.mia, 5), 0)
        self.assertEqual(self.view(self.mia)["play_left"], 0)
        self.assertEqual(server.pixel_pay(self.mia, 30, play=False), 30)
        self.clock += 2 * 24 * 3600
        self.assertEqual(server.pixel_pay(self.mia, 5), 5)

    def test_a_gem_and_a_new_friend_pay(self):
        self.assertTrue(self.do(self.mia, "find", key="park0")["ok"])
        self.do(self.mia, "find", key="park0")
        self.assertEqual(self.entry(self.mia)["coins"], pixel.COINS_GEM)
        self.do(self.mia, "five", seat=self.spot(self.ben)["seat"])
        self.assertEqual(self.entry(self.mia)["coins"], pixel.COINS_GEM + pixel.COINS_FRIEND)
        self.assertEqual(self.entry(self.ben)["coins"], pixel.COINS_FRIEND)
        self.assertEqual(self.view(self.mia)["coins"], pixel.COINS_GEM + pixel.COINS_FRIEND)

    def test_buying_takes_coins_once_and_refuses_without_enough(self):
        self.assertIn("more coins", self.do(self.mia, "buy", key="beanie")["error"])
        self.entry(self.mia)["coins"] = 100
        out = self.do(self.mia, "buy", key="beanie")
        self.assertEqual(out["coins"], 100 - pixel.SHOP["beanie"]["price"])
        self.assertIn("beanie", out["gifts"])
        self.assertIn("error", self.do(self.mia, "buy", key="beanie"))
        self.assertTrue(self.do(self.mia, "wear", slot="hat", item="beanie")["ok"])
        self.assertTrue(self.do(self.mia, "buy", key="lamp")["ok"])
        self.assertIn("lamp", self.entry(self.mia)["stuff"])
        self.assertIn("error", self.do(self.mia, "buy", key="party"))      # box gifts aren't for sale

    def test_shop_things_never_come_out_of_a_gift_box(self):
        self.assertFalse(set(pixel.BOX_GIFTS) & set(pixel.SHOP))
        self.assertIn("error", self.do(self.mia, "wear", slot="hat", item="pirate"))

    def test_a_goal_gift_unlocks_by_itself_and_shows_on_the_next_look(self):
        self.assertFalse(set(pixel.GOAL_GIFTS) & (set(pixel.BOX_GIFTS) | set(pixel.SHOP)))
        self.assertIn("error", self.do(self.mia, "wear", slot="hat", item="gemcrown"))
        self.assertEqual(self.view(self.mia)["progress"]["gems"], 0)
        self.entry(self.mia)["found"] = [f"park{i % 3}{i}" for i in range(8)]
        self.assertNotIn("gemcrown", self.view(self.mia)["owned"])
        self.entry(self.mia)["found"].append("beach0")
        look = self.view(self.mia)
        self.assertEqual(look["progress"]["gems"], 9)
        self.assertIn("gemcrown", look["owned"])
        self.assertTrue(self.do(self.mia, "wear", slot="hat", item="gemcrown")["ok"])
        self.assertNotIn("gemcrown", self.view(self.ben)["owned"])

    def test_every_goal_can_be_reached(self):
        most = {"gems": len(pixel.HANG_FINDS), "fish": len(pixel.FISH), "stars": 3 * len(pixel.LEVELS), "friends": 30, "rounds": 999}
        for key in pixel.GOAL_GIFTS:
            what, n = pixel.GIFTS[key]["goal"]
            self.assertLessEqual(n, most[what], key)


class Homes(Fun):
    def test_going_home_shows_only_who_is_there(self):
        self.assertTrue(self.do(self.mia, "home")["ok"])
        mine = self.view(self.mia, 0)
        self.assertIn("members", mine)          # the screen starts again in the new place
        self.assertEqual([m["name"] for m in mine["members"]], ["Mia"])
        self.assertEqual(mine["places"], ["home"])
        self.assertTrue(mine["home"]["mine"])
        self.assertEqual({m["name"] for m in self.view(self.ben)["members"]}, {"Ben", "Alex"})
        self.assertIsNone(self.view(self.ben)["home"])

    def test_a_friend_can_visit_and_what_happens_inside_stays_inside(self):
        self.do(self.mia, "home")
        self.view(self.mia, 0)                  # her screen has started again at home
        seq = server.pixel_room["seq"]
        self.assertTrue(self.do(self.ben, "home", seat=self.spot(self.mia)["seat"])["ok"])
        self.assertEqual({m["name"] for m in self.view(self.ben)["members"]}, {"Mia", "Ben"})
        self.assertFalse(self.view(self.ben)["home"]["mine"])
        self.assertEqual([e["kind"] for e in self.view(self.mia, seq)["events"]], ["join"])
        self.assertEqual([e["kind"] for e in self.view(self.alex, seq)["events"]], ["leave"])
        seq = server.pixel_room["seq"]
        self.do(self.ben, "say", text=next(iter(pixel.ROOM_SAYS)))
        self.assertEqual(len(self.view(self.mia, seq)["events"]), 1)
        self.assertEqual(self.view(self.alex, seq)["events"], [])
        self.assertEqual(self.view(None, seq)["events"], [])              # nor the projector

    def test_the_class_screen_can_look_into_a_home_and_sees_what_everyone_is_doing(self):
        self.do(self.mia, "home")
        self.do(self.ben, "home", seat=self.spot(self.mia)["seat"])
        self.do(self.ben, "move", name="dance")
        outside = self.view(None)
        self.assertEqual({m["name"] for m in outside["members"]}, {"Alex"})
        people = {m["name"]: m for m in outside["people"]}
        self.assertEqual(people["Mia"]["where"], "🏠 Their home")
        self.assertEqual(people["Ben"]["where"], "🏠 Mia's home")
        self.assertEqual(people["Ben"]["home"], "Mia")
        self.assertEqual(people["Ben"]["doing"], "💃 Dancing")
        self.assertEqual(people["Alex"]["where"], "park")
        inside = self.view(None, -1, people["Mia"]["loc"])
        self.assertEqual({m["name"] for m in inside["members"]}, {"Mia", "Ben"})
        self.assertEqual(inside["home"]["name"], "Mia")
        self.assertFalse(inside["home"]["mine"])
        self.advance(server.DOING_FOR + 1)
        self.assertEqual({m["name"]: m["doing"] for m in self.view(None)["people"]}["Ben"], "")
        self.assertEqual({m["name"] for m in self.view(None, -1, 9999)["members"]}, {"Alex"})     # no such home: outside

    def test_nothing_sent_to_a_screen_holds_a_player_id(self):
        self.do(self.mia, "home")
        self.do(self.ben, "home", seat=self.spot(self.mia)["seat"])
        self.assertNotIn("private-", repr(self.view(self.ben)) + repr(self.view(self.mia)))

    def test_going_out_puts_you_back_where_you_were(self):
        self.do(self.mia, "walk", x=500, y=.5)
        self.do(self.mia, "home")
        self.assertLess(self.spot(self.mia)["x"], 150)                   # just inside the door
        self.do(self.mia, "walk", x=900, y=.5)
        self.assertLessEqual(self.spot(self.mia)["x"], pixel.PLACE_W)     # a home is one screen wide
        self.do(self.mia, "home", out=True)
        self.assertEqual((self.spot(self.mia)["loc"], self.spot(self.mia)["x"]), (0, 500))

    def test_only_the_owner_furnishes_and_only_with_what_they_have(self):
        self.do(self.mia, "home")
        self.do(self.ben, "home", seat=self.spot(self.mia)["seat"])
        self.assertTrue(self.do(self.mia, "furnish", key="rug", x=100, y=.5)["ok"])       # a rug is free
        self.assertIn("error", self.do(self.mia, "furnish", key="sofa", x=100, y=.5))
        self.assertIn("error", self.do(self.ben, "furnish", key="rug", x=100, y=.5))
        self.entry(self.mia)["stuff"] += ["sofa", "w_pink"]
        self.do(self.mia, "furnish", key="sofa", x=200, y=.2)
        self.do(self.mia, "furnish", key="rug", x=150, y=.7)                             # putting it down again moves it
        self.assertTrue(self.do(self.mia, "look", key="w_pink")["ok"])
        self.assertIn("error", self.do(self.mia, "look", key="w_blue"))
        home = self.view(self.ben)["home"]
        self.assertEqual(home["wall"], "w_pink")
        self.assertEqual(home["items"], [{"key": "sofa", "x": 200, "y": .2}, {"key": "rug", "x": 150, "y": .7}])
        self.do(self.mia, "unfurnish", key="sofa")
        self.assertEqual([i["key"] for i in self.view(self.ben)["home"]["items"]], ["rug"])

    def test_drawings_hang_at_home_apart_from_the_world(self):
        drawing = dict(pixel.PIP, key="d1", title="Cat")
        self.entry(self.mia)["drawings"].append(drawing)
        self.entry(self.ben)["drawings"].append(dict(drawing, key="d2"))
        self.do(self.mia, "home")
        self.do(self.ben, "home", seat=self.spot(self.mia)["seat"])
        self.assertTrue(self.do(self.mia, "place", key="d1", x=100, y=.5)["ok"])
        self.assertIn("error", self.do(self.ben, "place", key="d2", x=100, y=.5))
        self.assertEqual(len(self.view(self.ben)["placed"]), 1)
        self.assertEqual(self.view(self.alex)["placed"], [])
        self.assertEqual(server.pixel_class.get("placed", []), [])
        self.do(self.mia, "unplace", piece=self.view(self.mia)["placed"][0]["id"])
        self.assertEqual(self.view(self.mia)["placed"], [])

    def test_games_and_stars_are_for_outside(self):
        self.do(self.mia, "home")
        self.assertIn("outside", self.do(self.mia, "game", action="create", kind="tag")["error"])
        self.do(self.ben, "game", action="create", kind="tag")
        self.do(self.alex, "game", action="join")
        self.do(self.alex, "home")                    # walking off into a home leaves the lobby
        self.assertEqual(server.pixel_room["game"]["joined"], [self.spot(self.ben)["seat"]])
        self.assertIn("error", self.do(self.mia, "find", key="park0"))


class Rooms(Fun):
    def buy_room(self, p, key="r_bed"):
        self.entry(p)["coins"] = 500
        return self.do(p, "buy", key=key)

    def test_a_room_costs_coins_and_joins_on_in_the_order_bought(self):
        self.entry(self.mia)["coins"] = pixel.HOME_ROOMS["r_attic"]["price"] - 1
        self.assertIn("error", self.do(self.mia, "buy", key="r_attic"))
        self.buy_room(self.mia, "r_attic")
        self.buy_room(self.mia, "r_bed")
        self.assertIn("error", self.do(self.mia, "buy", key="r_bed"))           # once only
        self.do(self.mia, "home")
        home = self.view(self.mia)["home"]
        self.assertEqual([r["name"] for r in home["rooms"]], [pixel.HOME_FIRST, "Attic", "Bedroom"])
        self.assertEqual(home["at"], 0)

    def test_doors_go_along_the_row_and_only_to_rooms_in_that_home(self):
        self.buy_room(self.mia)
        self.do(self.mia, "home")
        first, bed = [r["loc"] for r in self.view(self.mia)["home"]["rooms"]]
        self.assertTrue(self.do(self.mia, "home", to=bed)["ok"])
        self.assertEqual(self.view(self.mia)["home"]["at"], 1)
        self.do(self.ben, "home")
        self.assertIn("error", self.do(self.ben, "home", to=bed))                # not his home
        self.do(self.ben, "home", seat=self.spot(self.mia)["seat"])
        self.assertTrue(self.do(self.ben, "home", to=bed)["ok"])                 # a visitor can look round
        self.assertEqual({m["name"] for m in self.view(self.ben, -1)["members"]}, {"Mia", "Ben"})
        self.do(self.mia, "home", to=first)
        self.assertGreater(self.spot(self.mia)["x"], pixel.PLACE_W / 2)          # came back in by the right-hand door
        self.assertEqual({m["name"] for m in self.view(self.mia, -1)["members"]}, {"Mia"})

    def test_each_room_has_its_own_look_things_and_drawings(self):
        self.buy_room(self.mia)
        self.entry(self.mia)["stuff"] += ["sofa", "w_pink"]
        self.entry(self.mia)["drawings"].append(dict(pixel.PIP, key="d1", title="Cat"))
        self.do(self.mia, "home")
        first, bed = [r["loc"] for r in self.view(self.mia)["home"]["rooms"]]
        self.do(self.mia, "furnish", key="sofa", x=100, y=.5)
        self.do(self.mia, "home", to=bed)
        self.do(self.mia, "look", key="w_pink")
        self.do(self.mia, "furnish", key="sofa", x=200, y=.5)                    # owned once: it moves rooms
        self.assertTrue(self.do(self.mia, "place", key="d1", x=100, y=.5)["ok"])
        here = self.view(self.mia, -1)
        self.assertEqual((here["home"]["wall"], [i["key"] for i in here["home"]["items"]], len(here["placed"])), ("w_pink", ["sofa"], 1))
        self.do(self.mia, "home", to=first)
        there = self.view(self.mia, -1)
        self.assertEqual((there["home"]["wall"], there["home"]["items"], there["placed"]), ("w_cream", [], []))
        self.do(self.mia, "home", to=bed)
        self.do(self.mia, "unplace", piece=self.view(self.mia, -1)["placed"][0]["id"])
        self.assertEqual(self.view(self.mia, -1)["placed"], [])

    def test_the_class_screen_knows_whose_room_it_is(self):
        self.buy_room(self.mia)
        self.do(self.mia, "home")
        bed = self.view(self.mia)["home"]["rooms"][1]["loc"]
        self.do(self.mia, "home", to=bed)
        people = {m["name"]: m for m in self.view(None)["people"]}
        self.assertEqual(people["Mia"]["where"], "🏠 Their home")
        self.assertEqual(self.view(None, -1, bed)["home"]["at"], 1)


class Fishing(Fun):
    def pier(self):
        return server.hang_places().index("beach") * pixel.PLACE_W + pixel.FISH_X

    def cast(self, p):
        self.do(p, "walk", x=self.pier(), y=0)
        with patch.object(server.random, "uniform", return_value=3):
            return self.do(p, "fish", action="cast")

    def test_reeling_in_at_the_bite_catches_something(self):
        self.assertIn("error", self.do(self.mia, "fish", action="cast"))        # not at the pier
        self.assertEqual(self.cast(self.mia)["wait"], 3)
        self.clock += 3.5
        with patch.object(server.random, "choices", return_value=["crab"]):
            out = self.do(self.mia, "fish", action="reel")
        self.assertEqual((out["fish"], out["new"], out["coins"]), ("crab", True, pixel.COINS_FISH + pixel.COINS_NEW_FISH))
        self.assertEqual(self.entry(self.mia)["fish"], {"crab": 1})
        self.cast(self.mia)
        self.clock += 3.5
        with patch.object(server.random, "choices", return_value=["crab"]):
            self.assertEqual(self.do(self.mia, "fish", action="reel")["coins"], pixel.COINS_FISH)

    def test_too_soon_too_late_and_walking_away_all_lose_it(self):
        self.cast(self.mia)
        self.clock += 1
        self.assertIn("soon", self.do(self.mia, "fish", action="reel")["missed"])
        self.cast(self.mia)
        self.clock += 3 + pixel.FISH_BITE + .1
        self.assertIn("slow", self.do(self.mia, "fish", action="reel")["missed"])
        self.cast(self.mia)
        self.do(self.mia, "walk", x=20, y=.5)
        self.assertIn("error", self.do(self.mia, "fish", action="reel"))
        self.assertEqual(self.entry(self.mia)["fish"], {})

    def test_catching_every_kind_is_a_badge(self):
        self.entry(self.mia)["fish"] = {k: 1 for k in list(pixel.FISH)[1:]}
        self.cast(self.mia)
        self.clock += 3.5
        with patch.object(server.random, "choices", return_value=[list(pixel.FISH)[0]]):
            out = self.do(self.mia, "fish", action="reel")
        self.assertEqual([b["name"] for b in out["badges"]], ["Gone Fishing"])


class Rounds(Fun):
    def begin(self, kind):
        self.assertTrue(self.do(self.mia, "game", action="create", kind=kind)["ok"])
        self.assertTrue(self.do(self.ben, "game", action="join")["ok"])
        self.assertTrue(self.do(self.mia, "game", action="start")["ok"])
        return server.pixel_room["game"]

    def run_to(self, p, x):
        """Keeps pressing run until this pal is at `x`, with the light held green."""
        game = server.pixel_room["game"]
        for _ in range(200):
            if not server.pixel_room["game"] or game["phase"] != "playing" or game["motion"][self.spot(p)["seat"]]["x"] >= x:
                return
            game["light_until"] = self.clock + 99
            self.do(p, "walk", x=640, y=.5)
            self.advance(.4)
        self.fail("never got there")

    def test_a_race_is_won_by_the_first_to_the_flag(self):
        game = self.begin("race")
        self.assertEqual(game["light"], "green")
        self.assertEqual({self.spot(p)["x"] for p in (self.mia, self.ben)}, {server.RACE_START})
        self.do(self.mia, "walk", x=640, y=.5)
        self.assertLessEqual(game["motion"][self.spot(self.mia)["seat"]]["tx"], server.RACE_START + server.RACE_STEP)
        self.run_to(self.mia, server.RACE_END)
        self.assertEqual(game["done"], [self.spot(self.mia)["seat"]])
        self.assertIn("made it", self.do(self.mia, "walk", x=640, y=.5)["error"])
        self.run_to(self.ben, server.RACE_END)
        self.assertEqual(game["phase"], "results")
        self.assertIn("Mia won", game["message"])
        self.assertEqual(self.entry(self.mia)["coins"], pixel.COINS_ROUND + pixel.COINS_WIN)
        self.assertEqual(self.entry(self.ben)["coins"], pixel.COINS_ROUND)
        self.assertIn("play_race", self.entry(self.ben)["badges"])

    def test_moving_on_red_sends_a_pal_back_a_bit(self):
        game = self.begin("race")
        self.run_to(self.mia, 200)
        seat = self.spot(self.mia)["seat"]
        game["light_until"] = self.clock
        self.advance(.1)
        self.assertEqual(game["light"], "red")
        still = game["motion"][seat]["x"]
        self.advance(server.RACE_GRACE + .1)                 # standing still on red is fine
        self.assertEqual(game["motion"][seat]["x"], still)
        game["light_until"] = self.clock + 99
        self.do(self.mia, "walk", x=640, y=.5)
        self.advance(.1)
        self.assertLess(game["motion"][seat]["x"], still)
        self.assertGreaterEqual(game["motion"][seat]["x"], server.RACE_START)
        self.assertEqual(self.view(self.mia)["game"]["light"], "red")

    def dance(self, p, game):
        for name in game["seq"][game["progress"].get(self.spot(p)["seat"], 0):]:
            out = self.do(p, "game", action="step", name=name)
            self.assertTrue(out.get("ok"), out)

    def test_copying_the_dance_scores_a_round_and_the_best_dancer_wins(self):
        game = self.begin("dance")
        self.assertEqual(len(game["seq"]), 3)
        self.assertIn("ready", self.do(self.mia, "game", action="step", name=game["seq"][0])["error"])
        self.assertIn("dance floor", self.do(self.mia, "walk", x=300, y=.5)["error"])
        self.advance(server.DANCE_READY)
        wrong = next(m for m in pixel.DANCE_MOVES if m != game["seq"][0])
        self.assertIn("Not that one", self.do(self.mia, "game", action="step", name=wrong)["message"])
        self.assertIn("error", self.do(self.mia, "game", action="step", name=game["seq"][0]))      # frozen for a moment
        self.advance(server.DANCE_FREEZE)
        seq = server.pixel_room["seq"]
        self.dance(self.mia, game)
        self.assertEqual(self.view(self.mia)["game"]["step"], 3)
        self.assertIn("move", [e["kind"] for e in self.view(self.ben, seq)["events"]])              # everyone sees the dancing
        for _ in range(server.DANCE_ROUNDS):
            if game["phase"] != "playing":
                break
            self.advance(30)
            self.advance(server.DANCE_READY)
            if game["phase"] == "playing":
                self.dance(self.mia, game)
        self.assertEqual(game["phase"], "results")
        self.assertIn("Mia", game["message"])
        self.assertEqual(game["score"], {self.spot(self.mia)["seat"]: server.DANCE_ROUNDS})
        self.assertEqual(self.entry(self.mia)["coins"], pixel.COINS_ROUND + pixel.COINS_WIN)
        self.assertEqual(self.entry(self.ben)["coins"], pixel.COINS_ROUND)

    def test_a_round_ends_early_when_everyone_has_the_dance(self):
        game = self.begin("dance")
        self.advance(server.DANCE_READY)
        self.dance(self.mia, game)
        self.assertEqual(game["round"], 0)
        self.dance(self.ben, game)
        self.assertEqual((game["round"], len(game["seq"])), (1, 4))


if __name__ == "__main__":
    unittest.main()
