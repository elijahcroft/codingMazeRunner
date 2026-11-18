"""Homes to work towards: rooms with their own look, furniture bought more than once,
levels with prizes, hearts from visitors, and things at home to play with."""
import unittest

import pixel
import server
from test_pixel_fun import Fun


class Homes(Fun):
    def build(self, p, key):
        self.entry(p)["coins"] += pixel.HOME_ROOMS[key]["price"]
        return self.do(p, "buy", key=key)

    def buy(self, p, key):
        self.entry(p)["coins"] += pixel.SHOP[key]["price"]
        return self.do(p, "buy", key=key)

    def items(self, p):
        return self.view(p)["home"]["items"]

    def test_furniture_can_be_bought_again_and_each_copy_goes_out(self):
        self.do(self.mia, "home")
        self.assertTrue(self.buy(self.mia, "balloons")["ok"])
        self.assertTrue(self.buy(self.mia, "balloons")["ok"])
        self.assertEqual(self.entry(self.mia)["stuff"].count("balloons"), 2)
        self.assertTrue(self.do(self.mia, "furnish", key="balloons", x=60, y=.5)["ok"])
        self.assertTrue(self.do(self.mia, "furnish", key="balloons", x=260, y=.5)["ok"])
        self.assertIn("all of yours are out", self.do(self.mia, "furnish", key="balloons", x=160, y=.5)["error"])
        ids = [i["id"] for i in self.items(self.mia)]
        self.assertEqual(len(set(ids)), 2)
        self.do(self.mia, "unfurnish", piece=ids[0])
        self.assertEqual([i["x"] for i in self.items(self.mia)], [260])
        self.assertTrue(self.do(self.mia, "furnish", key="balloons", x=160, y=.5)["ok"])     # put away, so it can go out again

    def test_free_things_come_one_each_and_the_rest_buy_once(self):
        self.do(self.mia, "home")
        self.do(self.mia, "furnish", key="rug", x=60, y=.5)
        self.assertIn("error", self.do(self.mia, "furnish", key="rug", x=200, y=.5))
        self.assertTrue(self.buy(self.mia, "w_pink")["ok"])
        self.assertIn("error", self.buy(self.mia, "w_pink"))
        self.assertTrue(self.build(self.mia, "r_kitchen")["ok"])
        self.assertIn("error", self.build(self.mia, "r_kitchen"))

    def test_a_room_holds_only_so_many_things(self):
        self.do(self.mia, "home")
        self.entry(self.mia)["stuff"] += ["lamp"] * (pixel.HOME_ITEMS + 1)
        for i in range(pixel.HOME_ITEMS):
            self.assertTrue(self.do(self.mia, "furnish", key="lamp", x=20 + i * 20, y=.5)["ok"])
        self.assertIn("full", self.do(self.mia, "furnish", key="lamp", x=100, y=.5)["error"])
        first = self.items(self.mia)[0]["id"]
        self.assertTrue(self.do(self.mia, "furnish", piece=first, x=300, y=.1)["ok"])     # moving one inside a full room is fine

    def test_a_room_comes_with_its_own_walls_and_floor(self):
        self.build(self.mia, "r_secret")
        rooms = server.home_rooms(server.home_of(self.entry(self.mia)))
        self.assertEqual((rooms[1]["wall"], rooms[1]["floor"]), ("w_castle", "f_sand"))
        self.assertTrue(server.pixel_has(self.entry(self.mia), "w_castle"))
        self.assertFalse(server.pixel_has(self.entry(self.ben), "w_castle"))
        self.assertNotIn("w_castle", pixel.SHOP)
        self.do(self.mia, "home")
        self.assertTrue(self.do(self.mia, "look", key="w_castle", room=0)["ok"])          # and can use them anywhere
        self.assertEqual(self.view(self.mia)["home"]["rooms"][0]["kind"], "living")

    def test_rooms_bought_before_get_their_look_unless_already_changed(self):
        entry = self.entry(self.mia)
        entry["stuff"] += ["r_bed", "r_attic"]
        entry["home"] = {"id": 50, "wall": "w_cream", "floor": "f_wood", "items": [{"key": "rug", "x": 10, "y": .5}], "art": [], "rooms": [
            {"key": "r_bed", "id": 51, "wall": "w_cream", "floor": "f_wood", "items": [], "art": []},
            {"key": "r_attic", "id": 52, "wall": "w_pink", "floor": "f_wood", "items": [], "art": []}]}
        home = server.home_of(entry)
        self.assertEqual([(r["wall"], r["floor"]) for r in home["rooms"]], [("w_blue", "f_carpet"), ("w_pink", "f_wood")])
        self.assertEqual(home["items"][0]["id"], 1)
        self.assertTrue(server.pixel_has(entry, "w_attic"))
        home["rooms"][0]["wall"] = "w_cream"
        self.assertEqual(server.home_of(entry)["rooms"][0]["wall"], "w_cream")            # only once

    def test_a_home_grows_and_wins_prizes(self):
        self.do(self.mia, "home")
        self.entry(self.mia)["stuff"] += ["lamp", "teddy"]
        for key, x in (("rug", 100), ("plant", 120), ("lamp", 140)):
            self.assertNotIn("grew", self.do(self.mia, "furnish", key=key, x=x, y=.5))
        self.assertFalse(server.pixel_has(self.entry(self.mia), "trophy"))
        self.assertEqual(self.do(self.mia, "furnish", key="teddy", x=160, y=.5)["grew"], "Cozy cottage")
        self.assertTrue(server.pixel_has(self.entry(self.mia), "trophy"))
        self.assertIn("Cozy cottage", server.pixel_feed[-1]["text"])
        home = self.view(self.mia)["home"]
        self.assertEqual((home["points"], home["level"], home["next"]), (4, 1, 9))
        self.do(self.mia, "unfurnish", piece=home["items"][-1]["id"])                       # a level, once reached, is kept
        self.assertEqual(server.home_of(self.entry(self.mia))["level"], 1)
        self.assertNotIn("grew", self.do(self.mia, "furnish", key="teddy", x=160, y=.5))

    def test_drawings_count_and_code_counts_more(self):
        self.entry(self.mia)["drawings"].append(dict(pixel.PIP, key="d1", title="Cat"))
        self.do(self.mia, "home")
        self.do(self.mia, "place", key="d1", x=100, y=.5)
        self.assertEqual(server.home_points(self.entry(self.mia)), 1)
        self.assertTrue(server.thing_save(self.mia, {"key": "d1", "code": "def on_click():\n    jump()\n"})["ok"])
        self.assertEqual(server.home_points(self.entry(self.mia)), 2)

    def test_an_old_full_home_catches_up_when_its_owner_walks_in(self):
        self.entry(self.mia)["home"] = {"id": 7, "wall": "w_cream", "floor": "f_wood", "art": [],
                                        "items": [{"key": k, "x": 100, "y": .5} for k in ("rug", "plant", "lamp", "teddy")]}
        self.assertEqual(self.do(self.mia, "home")["grew"], "Cozy cottage")

    def test_prizes_cant_be_bought_or_used_before_they_are_won(self):
        for key in pixel.home_prizes(len(pixel.HOME_LEVELS) - 1):
            self.assertNotIn(key, pixel.SHOP)
        self.do(self.mia, "home")
        self.assertIn("error", self.do(self.mia, "furnish", key="unicornpal", x=100, y=.5))
        self.assertIn("error", self.do(self.mia, "look", key="f_gold"))
        self.assertEqual({item["prize"] for item in {**pixel.FURNITURE, **pixel.HOME_FLOORS}.values() if item.get("prize")},
                         set(range(1, len(pixel.HOME_LEVELS))))                              # a prize for every level

    def test_a_visitor_gives_one_heart_and_the_owner_gets_coins(self):
        self.do(self.mia, "home")
        self.do(self.ben, "home", seat=self.spot(self.mia)["seat"])
        coins = self.entry(self.mia)["coins"]
        self.assertIn("error", self.do(self.mia, "heart"))                  # not your own
        self.assertTrue(self.do(self.ben, "heart")["ok"])
        self.assertIn("already", self.do(self.ben, "heart")["error"])
        self.assertEqual(self.entry(self.mia)["coins"], coins + pixel.COINS_HEART)
        home = self.view(self.ben)["home"]
        self.assertEqual((home["hearts"], home["hearted"], home["points"]), (1, True, 1))
        self.assertFalse(self.view(self.mia)["home"]["hearted"])
        self.assertNotIn("private-", repr(self.view(self.ben)) + repr(self.view(self.mia)))
        self.do(self.ben, "home", out=True)
        self.assertIn("error", self.do(self.ben, "heart"))                  # outside

    def test_things_at_home_are_toys(self):
        self.build(self.mia, "r_bed")
        self.do(self.mia, "home")
        self.assertTrue(self.do(self.mia, "toy", name="notes", x=500, y=.5)["ok"])     # in the second room
        self.assertEqual(server.pixel_room["events"][-1]["kind"], "toy")
        self.advance(2)
        self.assertIn("error", self.do(self.mia, "toy", name="coconut", x=100, y=.5))     # a toy from outside
        self.do(self.mia, "home", out=True)
        self.advance(2)
        self.assertIn("error", self.do(self.mia, "toy", name="notes", x=100, y=.5))

    def test_a_piece_can_be_painted_flipped_and_sized(self):
        self.do(self.mia, "home")
        self.do(self.mia, "furnish", key="rug", x=60, y=.5)
        piece = self.items(self.mia)[0]["id"]
        self.assertTrue(self.do(self.mia, "style", piece=piece, paint=3, flip=True)["ok"])
        self.assertTrue(self.do(self.mia, "style", piece=piece, size=2)["ok"])     # the rest stays as it was
        item = self.items(self.mia)[0]
        self.assertEqual((item["paint"], item["flip"], item["size"]), (3, True, 2))
        self.do(self.mia, "furnish", piece=piece, x=200, y=.3)     # moving keeps the look
        self.assertEqual(self.items(self.mia)[0]["paint"], 3)
        self.assertTrue(self.do(self.mia, "style", piece=piece, paint=0, flip=False, size=1)["ok"])
        self.assertNotIn("paint", self.items(self.mia)[0])     # back how it came, with nothing kept
        for bad in ({"paint": pixel.FURN_PAINTS}, {"paint": 1.0}, {"size": True}, {"flip": 1}, {"paint": -1}):
            self.assertIn("error", self.do(self.mia, "style", piece=piece, **bad), bad)
        self.assertIn("error", self.do(self.mia, "style", piece=999, paint=1))
        self.do(self.mia, "home", seat=self.spot(self.ben)["seat"])     # not in someone else's home
        self.assertIn("error", self.do(self.mia, "style", piece=piece, paint=1))

    def test_a_wish_is_kept_until_it_is_bought(self):
        self.assertTrue(self.do(self.mia, "wish", key="piano")["ok"])
        self.assertEqual(server.pixel_state(self.mia)["hang"]["wish"], "piano")
        self.assertIn("error", self.do(self.mia, "wish", key="nothing"))
        self.buy(self.mia, "piano")
        self.assertIsNone(self.entry(self.mia)["wish"])
        self.buy(self.mia, "r_bed")
        self.assertIn("error", self.do(self.mia, "wish", key="r_bed"))     # built already
        self.assertTrue(self.do(self.mia, "wish", key="piano")["ok"])     # furniture can be bought again
        self.assertTrue(self.do(self.mia, "wish", key=None)["ok"])

    def test_every_room_can_be_built_and_the_home_reaches_the_top(self):
        for key in pixel.HOME_ROOMS:
            self.assertTrue(self.build(self.mia, key)["ok"], key)
        self.do(self.mia, "home")
        view = self.view(self.mia)["home"]
        self.assertEqual(len(view["rooms"]), len(pixel.HOME_ROOMS) + 1)
        self.assertFalse(view["more"])
        self.assertEqual([r["wall"] for r in view["rooms"][1:]], [r["wall"] for r in pixel.HOME_ROOMS.values()])
        entry = self.entry(self.mia)
        for i, key in enumerate(k for k in pixel.FURNITURE if pixel.FURNITURE[k]["price"]):
            entry["stuff"].append(key)
            self.assertTrue(self.do(self.mia, "furnish", key=key, x=40 + (i // 12) * pixel.PLACE_W + i % 12 * 20, y=.5)["ok"], key)
        self.assertEqual(self.entry(self.mia)["home"]["level"], len(pixel.HOME_LEVELS) - 1)
        for key in pixel.home_prizes(len(pixel.HOME_LEVELS) - 1):
            self.assertIn(key, entry["stuff"])

    def test_every_thing_and_room_is_drawn_and_every_toy_works(self):
        for room in pixel.HOME_ROOMS.values():
            self.assertIn(room["wall"], pixel.HOME_WALLS)
            self.assertIn(room["floor"], pixel.HOME_FLOORS)
            self.assertTrue(room["icon"])
        with open("pixel_stage.js", encoding="utf-8") as f:
            stage = f.read()
        with open("pixel_hangout.js", encoding="utf-8") as f:
            hang = f.read()
        for toy in pixel.HOME_TOYS:
            self.assertRegex(stage, rf"\b{toy}: {{ink:")
        for key in pixel.FURNITURE:
            self.assertRegex(hang, rf"\n    {key}\(g, x, y\)")
        for key in list(pixel.HOME_WALLS) + list(pixel.HOME_FLOORS):
            self.assertIn(f"{key}:", hang)
        for kind in list(pixel.HOME_ROOMS) + ["living"]:
            self.assertRegex(hang, rf"\n    {kind}\(g")

    def test_a_home_shows_the_level_it_has_earned_and_keeps_it(self):
        self.do(self.mia, "home")
        self.assertEqual(self.view(self.mia)["home"]["level"], 0)
        self.entry(self.mia)["stuff"] += ["lamp", "teddy"]
        for key, x in (("rug", 60), ("plant", 90), ("lamp", 120), ("teddy", 150)):
            self.do(self.mia, "furnish", key=key, x=x, y=.5)
        self.assertEqual(self.view(self.mia)["home"]["level"], 1)
        piece = next(i["id"] for i in self.items(self.mia) if i["key"] == "teddy")
        self.do(self.mia, "unfurnish", piece=piece)
        home = self.view(self.mia)["home"]
        self.assertEqual((home["level"], home["points"], home["next"]), (1, 3, 9))

    def test_a_level_prize_is_on_the_next_look_without_a_reload(self):
        self.do(self.mia, "home")
        self.assertNotIn("trophy", self.view(self.mia)["stuff"])
        for key, x in (("rug", 60), ("plant", 90), ("lamp", 120), ("teddy", 150)):
            self.entry(self.mia)["stuff"] += [key] if key in ("lamp", "teddy") else []
            self.do(self.mia, "furnish", key=key, x=x, y=.5)
        look = self.view(self.mia)
        self.assertEqual(look["home"]["level"], 1)
        self.assertIn("trophy", look["stuff"])
        self.assertIn("trophy", self.entry(self.mia)["stuff"])

    def test_things_and_drawings_keep_clear_of_the_front_door(self):
        self.do(self.mia, "home")
        self.assertTrue(self.do(self.mia, "furnish", key="rug", x=20, y=.5)["ok"])
        self.assertGreaterEqual(self.items(self.mia)[0]["x"], pixel.HOME_FRONT)
        self.build(self.mia, "r_bed")
        self.assertTrue(self.do(self.mia, "furnish", key="plant", x=pixel.PLACE_W + 20, y=.5)["ok"])
        plant = next(i for i in self.items(self.mia) if i["key"] == "plant")
        self.assertEqual(plant["x"], pixel.PLACE_W + 20)          # a back room has no outside door
        self.entry(self.mia)["drawings"].append(dict(pixel.PIP, key="d1", title="Cat"))
        self.do(self.mia, "place", key="d1", x=20, y=.5)
        drawings = self.view(self.mia)["placed"]
        self.assertEqual(len(drawings), 1)
        self.assertGreaterEqual(drawings[0]["x"], pixel.HOME_FRONT)


if __name__ == "__main__":
    unittest.main()
