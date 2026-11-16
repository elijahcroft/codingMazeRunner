"""More fun in the Hang out: ✏️ wear your own drawing, ✨ fancy things, 🎨 Draw & guess, and the ❄️ Snow Village."""
import unittest
from unittest.mock import patch

import pixel
import server


def drawing(key="hat", size=16, title="My hat"):
    frame = "." * size * 3 + ("...." + "a" * 8 + "." * (size - 12)) * 2 + "." * size * (size - 5)
    return {"key": key, "title": title, "size": size, "speed": 6, "palette": ["#e8294f"], "frames": [frame], "names": [""],
            "marks": "", "guide": ""}


class Room(unittest.TestCase):
    winter = False

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
                  patch.object(server, "winter", side_effect=lambda: self.winter),
                  patch.object(server, "pixel_save_soon")):
            p.start()
            self.addCleanup(p.stop)
        self.addCleanup(self.restore)
        self.mia, self.ben, self.zoe = self.kid("Mia"), self.kid("Ben"), self.kid("Zoe")

    def restore(self):
        server.pixel_room, server.players, server.pixel_class, server.pixel_feed = self.saved

    def kid(self, name):
        p = {"id": "private-" + name, "name": name}
        server.players[p["id"]] = p
        entry = server.pixel_entry(p)
        entry["solved"].update({k: [True] * 3 for k in ("a1", "a2", "a3")})
        entry["drawings"].append(drawing())
        self.assertTrue(server.room_do(p, {"what": "join"})["ok"])
        return p

    def spot(self, p):
        return server.pixel_room["here"][p["id"]]

    def events(self, kind):
        return [e for e in server.pixel_room["events"] if e["kind"] == kind]


class OwnWear(Room):
    def test_a_drawing_cut_down_to_what_is_drawn(self):
        art = pixel.wear_cut(drawing())
        self.assertEqual(art["rows"], ["a" * 8] * 2)
        self.assertEqual(art["size"], 16)
        self.assertIsNone(pixel.wear_cut(dict(drawing(), frames=["." * 256])))

    def test_making_one_costs_coins_and_puts_it_on_for_everyone_to_see(self):
        entry = server.pixel_entry(self.mia)
        entry["coins"] = 50
        out = server.room_do(self.mia, {"what": "sew", "key": "hat", "slot": "hat"})
        self.assertTrue(out["ok"], out)
        self.assertEqual(out["coins"], 50 - pixel.MY_WEAR_PRICE)
        key = out["item"]["key"]
        self.assertEqual(entry["wear"]["hat"], key)
        self.assertEqual(self.events("wear")[-1]["wear_art"]["hat"]["rows"], ["a" * 8] * 2)
        row = server.room_row(self.spot(self.mia))
        self.assertEqual(row["wear_art"]["hat"]["palette"], ["#e8294f"])
        self.assertEqual(server.pixel_state(self.mia)["hang"]["mywear"][0]["name"], "My hat")

    def test_it_is_a_copy(self):
        server.pixel_entry(self.mia)["coins"] = 50
        server.room_do(self.mia, {"what": "sew", "key": "hat", "slot": "face"})
        pixel.delete_drawing(server.pixel_entry(self.mia)["drawings"], "hat")
        self.assertEqual(server.wear_art(server.pixel_entry(self.mia))["face"]["rows"], ["a" * 8] * 2)

    def test_not_enough_coins(self):
        server.pixel_entry(self.mia)["coins"] = 10
        out = server.room_do(self.mia, {"what": "sew", "key": "hat", "slot": "hat"})
        self.assertIn("30 more coins", out["error"])
        self.assertEqual(server.pixel_entry(self.mia)["mywear"], [])

    def test_only_hats_and_faces_and_only_your_own_drawings(self):
        server.pixel_entry(self.mia)["coins"] = 500
        self.assertIn("error", server.room_do(self.mia, {"what": "sew", "key": "hat", "slot": "sparkle"}))
        self.assertIn("error", server.room_do(self.mia, {"what": "sew", "key": "nope", "slot": "hat"}))

    def test_wearing_taking_off_and_throwing_away(self):
        server.pixel_entry(self.mia)["coins"] = 500
        key = server.room_do(self.mia, {"what": "sew", "key": "hat", "slot": "hat"})["item"]["key"]
        self.assertTrue(server.room_do(self.mia, {"what": "wear", "slot": "hat", "item": None})["ok"])
        self.assertEqual(server.room_row(self.spot(self.mia))["wear_art"], {})
        self.assertTrue(server.room_do(self.mia, {"what": "wear", "slot": "hat", "item": key})["ok"])
        self.assertEqual(server.room_do(self.mia, {"what": "wear", "slot": "face", "item": key})["error"], "bad")
        self.assertEqual(server.room_do(self.ben, {"what": "wear", "slot": "hat", "item": key})["error"], "bad")     # not Ben's
        out = server.room_do(self.mia, {"what": "unsew", "item": key})
        self.assertEqual((out["mywear"], out["wear"]), ([], {}))

    def test_there_is_a_most(self):
        server.pixel_entry(self.mia)["coins"] = 1000
        for _ in range(pixel.MY_WEAR_MAX):
            self.assertTrue(server.room_do(self.mia, {"what": "sew", "key": "hat", "slot": "hat"})["ok"])
        self.assertIn("error", server.room_do(self.mia, {"what": "sew", "key": "hat", "slot": "hat"}))
        self.assertEqual(len({w["key"] for w in server.pixel_entry(self.mia)["mywear"]}), pixel.MY_WEAR_MAX)


class Fancy(Room):
    def test_the_fancy_shelf_is_dear_and_never_in_a_box(self):
        fancy = [k for k, g in pixel.GIFTS.items() if g.get("price", 0) >= pixel.FANCY_PRICE]
        self.assertGreaterEqual(len(fancy), 6)
        self.assertFalse(set(fancy) & set(pixel.BOX_GIFTS))
        self.assertTrue(all(k in pixel.SHOP for k in fancy))

    def test_buying_the_crown(self):
        server.pixel_entry(self.mia)["coins"] = 200
        out = server.room_do(self.mia, {"what": "buy", "key": "royalcrown"})
        self.assertEqual(out["coins"], 0)
        self.assertTrue(server.room_do(self.mia, {"what": "wear", "slot": "hat", "item": "royalcrown"})["ok"])

    def test_every_thing_to_wear_has_a_picture(self):
        with open("pixel_stage.js") as f:
            stage = f.read()
        for key, gift in pixel.GIFTS.items():
            self.assertRegex(stage, rf"\b{key}: [\[{{]", key)


class DrawAndGuess(Room):
    def start(self, *kids):
        kids = kids or (self.mia, self.ben, self.zoe)
        self.assertTrue(server.room_do(kids[0], {"what": "game", "action": "create", "kind": "draw"})["ok"])
        for p in kids[1:]:
            self.assertTrue(server.room_do(p, {"what": "game", "action": "join"})["ok"])
        self.assertTrue(server.room_do(kids[0], {"what": "game", "action": "start"})["ok"])
        return server.pixel_room["game"]

    def who(self, seat):
        return next(p for p in (self.mia, self.ben, self.zoe) if self.spot(p)["seat"] == seat)

    def test_the_word_is_a_secret_from_the_guessers(self):
        game = self.start()
        drawer = self.who(game["drawer"])
        guesser = next(p for p in (self.mia, self.ben) if p is not drawer)
        self.assertEqual(server.game_view(game["drawer"])["word"][0], game["word"])
        self.assertIsNone(server.game_view(self.spot(guesser)["seat"])["word"])
        self.assertIsNone(server.game_view(None)["word"])          # nor on the projector
        self.assertIn(game["word"], [c[0] for c in server.game_view(None)["choices"]])
        self.assertEqual(len(game["choices"]), pixel.DRAW_CHOICES)

    def test_painting_is_only_for_the_drawer(self):
        game = self.start()
        drawer = self.who(game["drawer"])
        guesser = next(p for p in (self.mia, self.ben) if p is not drawer)
        self.assertTrue(server.room_do(drawer, {"what": "game", "action": "paint", "cell": 13, "colour": 2})["ok"])
        self.assertEqual(game["board"][13], pixel.LETTERS[2])
        self.assertTrue(server.room_do(drawer, {"what": "game", "action": "paint", "cell": 13, "colour": None})["ok"])
        self.assertEqual(game["board"][13], ".")
        self.assertIn("error", server.room_do(guesser, {"what": "game", "action": "paint", "cell": 1, "colour": 0}))
        self.assertIn("error", server.room_do(drawer, {"what": "game", "action": "paint", "cell": 144, "colour": 0}))
        self.assertIn("error", server.room_do(drawer, {"what": "game", "action": "paint", "cell": 1, "colour": 99}))
        server.room_do(drawer, {"what": "game", "action": "paint", "cell": 5, "colour": 0})
        server.room_do(drawer, {"what": "game", "action": "paint", "wipe": True})
        self.assertEqual(set(game["board"]), {"."})

    def test_guessing_right_wrong_and_the_points(self):
        game = self.start()
        drawer = self.who(game["drawer"])
        a, b = [p for p in (self.mia, self.ben, self.zoe) if p is not drawer]
        wrong = next(k for k in game["choices"] if k != game["word"])
        out = server.room_do(a, {"what": "game", "action": "guess", "word": wrong})
        self.assertFalse(out["right"])
        self.assertIn("error", server.room_do(a, {"what": "game", "action": "guess", "word": game["word"]}))     # wait a moment
        self.assertEqual(server.room_do(b, {"what": "game", "action": "guess", "word": game["word"]})["points"], 3)
        self.clock += server.DRAW_WRONG_WAIT
        self.assertEqual(server.room_do(a, {"what": "game", "action": "guess", "word": game["word"]})["points"], 2)
        self.assertEqual(game["score"][game["drawer"]], 2)
        self.assertTrue(game["pause_until"])                       # everyone got it: show the answer
        self.assertIsNotNone(server.game_view(self.spot(a)["seat"])["word"])

    def test_a_whole_game_takes_turns_and_pays(self):
        game = self.start()
        drawers = []
        for _ in range(3):
            drawers.append(game["drawer"])
            for p in (self.mia, self.ben, self.zoe):
                if self.spot(p)["seat"] != game["drawer"]:
                    server.room_do(p, {"what": "game", "action": "guess", "word": game["word"]})
            self.clock += server.DRAW_PAUSE + .1
            server.game_tick(self.clock)
        self.assertEqual(len(set(drawers)), 3)                     # everyone drew once
        self.assertEqual(game["phase"], "results")
        self.assertEqual(set(game["rewards"]), set(drawers))
        self.assertEqual(server.pixel_entry(self.mia)["play_rounds"]["draw"], 1)

    def test_time_runs_out(self):
        game = self.start()
        self.clock += server.DRAW_SECONDS + 1
        server.game_tick(self.clock)
        self.assertTrue(game["pause_until"])
        self.assertIn("Nobody guessed it", server.pixel_room["events"][-1]["message"])

    def test_the_next_game_starts_with_someone_who_has_not_drawn(self):
        game = self.start(self.mia, self.ben)
        first = game["drawer"]
        server.pixel_room["game"] = None
        game = self.start(self.mia, self.ben)
        self.assertNotEqual(game["drawer"], first)

    def test_players_stay_put_and_can_cheer(self):
        game = self.start()
        guesser = next(p for p in (self.mia, self.ben) if self.spot(p)["seat"] != game["drawer"])
        self.assertIn("error", server.room_do(guesser, {"what": "walk", "x": 100, "y": .5}))
        self.assertTrue(server.room_do(guesser, {"what": "say", "text": "Hello!"})["ok"])

    def test_a_late_friend_can_join_and_guess(self):
        game = self.start(self.mia, self.ben)
        self.assertTrue(server.room_do(self.zoe, {"what": "game", "action": "join"})["ok"])
        out = server.room_do(self.zoe, {"what": "game", "action": "guess", "word": game["word"]})
        self.assertTrue(out["right"])


class Village(Room):
    winter = True

    def go_village(self, p, x=None):
        left = server.village_left()
        self.spot(p)["x"] = left + (pixel.SNOWMAN_X if x is None else x)

    def test_the_village_is_only_there_in_winter_and_last(self):
        self.assertEqual(server.hang_places()[-1], "village")
        self.assertNotIn("village", pixel.HANG_WORLD)
        self.assertTrue(pixel.winter_on(11, 16) and pixel.winter_on(12, 31))
        self.assertFalse(pixel.winter_on(1, 5) or pixel.winter_on(11, 15))
        self.winter = False
        self.assertNotIn("village", server.hang_places())
        self.assertEqual(server.pixel_state(self.mia)["hang"]["winter"], {"on": False})

    def test_a_present_in_each_place_found_once_a_day(self):
        view = server.winter_view(server.pixel_entry(self.mia))
        self.assertEqual([p["place"] for p in view["presents"]], list(pixel.PRESENT_PLACES))
        present = view["presents"][0]
        self.spot(self.mia)["x"] = server.hang_places().index(present["place"]) * pixel.PLACE_W + present["x"]
        out = server.room_do(self.mia, {"what": "present", "i": 0})
        self.assertEqual((out["found"], out["count"], out["coins"]), (1, 1, pixel.COINS_PRESENT))
        self.assertNotIn("coins", server.room_do(self.mia, {"what": "present", "i": 0}))
        self.assertEqual(server.pixel_entry(self.mia)["present_count"], 1)
        self.assertIn("error", server.room_do(self.ben, {"what": "present", "i": 1}))     # too far away
        self.day = "2026-11-17"
        self.assertFalse(any(p["found"] for p in server.winter_view(server.pixel_entry(self.mia))["presents"]))

    def test_presents_are_new_every_day_and_not_under_the_tree(self):
        self.assertNotEqual(pixel.presents_on("2026-11-16"), pixel.presents_on("2026-11-17"))
        for d in range(1, 31):
            village = pixel.presents_on(f"2026-12-{d:02}")[-1]
            self.assertGreaterEqual(abs(village["x"] - pixel.TREE_X), 40)

    def test_the_class_rolls_a_snowman_together(self):
        self.assertIn("error", server.room_do(self.mia, {"what": "snowball"}))          # in the Park
        for p in (self.mia, self.ben):
            self.go_village(p)
        points = server.hang_meter()["points"]
        for i in range(pixel.SNOWMAN_BALLS):
            self.clock += pixel.SNOWBALL_GAP / 2 + .01
            out = server.room_do(self.mia if i % 2 else self.ben, {"what": "snowball"})
            self.assertTrue(out["ok"], (i, out))
        self.assertTrue(out["done"])
        self.assertEqual(server.snowman_view(), {"balls": 0, "need": pixel.SNOWMAN_BALLS, "built": 1})
        self.assertEqual(server.hang_meter()["points"], points + pixel.SNOWMAN_POINTS)
        self.assertTrue(self.events("snowman")[-1]["done"])
        self.assertEqual(server.pixel_entry(self.ben)["snowballs"], pixel.SNOWMAN_BALLS // 2)
        self.assertIn("snowman", server.pixel_feed[-1]["text"] if isinstance(server.pixel_feed[-1], dict) else server.pixel_feed[-1])

    def test_snowballs_wait_a_moment(self):
        self.go_village(self.mia)
        self.assertTrue(server.room_do(self.mia, {"what": "snowball"})["ok"])
        self.assertEqual(server.room_do(self.mia, {"what": "snowball"})["error"], "wait")

    def test_snowballs_unlock_the_antlers_and_presents_the_santa_hat(self):
        entry = server.pixel_entry(self.mia)
        self.assertNotIn("antlers", server.pixel_owned(entry))
        entry["snowballs"], entry["present_count"] = 25, 5
        self.assertIn("antlers", server.pixel_owned(entry))
        self.assertIn("santa", server.pixel_owned(entry))
        self.assertNotIn("snowspark", server.pixel_owned(entry))

    def test_one_ornament_each_on_the_class_tree(self):
        self.assertTrue(server.room_do(self.mia, {"what": "ornament", "key": "hat"})["ok"])
        server.pixel_entry(self.mia)["drawings"].append(drawing("star", title="Star"))
        self.assertEqual(server.room_do(self.mia, {"what": "ornament", "key": "star"})["count"], 1)
        self.assertTrue(server.room_do(self.ben, {"what": "ornament", "key": "hat"})["ok"])
        self.assertEqual([r["by"] for r in server.tree_rows()], ["Mia", "Ben"])
        self.assertNotIn("owner", server.tree_rows()[0])
        self.assertEqual(self.events("tree")[-1]["tree"], server.tree_rows())
        view = server.room_view(self.mia, -1)
        self.assertEqual((len(view["tree"]), view["ornament"]), (2, "star"))
        self.assertEqual(server.room_do(self.mia, {"what": "ornament", "key": "nope"})["error"], "bad")

    def test_the_teacher_can_take_ornaments_down(self):
        server.room_do(self.mia, {"what": "ornament", "key": "hat"})
        server.room_do(self.ben, {"what": "ornament", "key": "hat"})
        self.assertEqual(server.room_placed_counts(), {"Mia": 1, "Ben": 1})       # so the teacher page has a button for each
        server.pixel_teacher({"action": "placed_clear", "name": "Mia"})
        self.assertEqual([r["by"] for r in server.tree_rows()], ["Ben"])
        server.pixel_teacher({"action": "placed_clear"})
        self.assertEqual(server.tree_rows(), [])

    def test_the_tree_has_room_for_everyone_and_drops_the_oldest(self):
        server.pixel_class["tree"] = [{"owner": f"x{i}", "by": f"K{i}", "key": "a", "pal": {}} for i in range(pixel.TREE_MAX)]
        server.room_do(self.mia, {"what": "ornament", "key": "hat"})
        self.assertEqual(len(server.pixel_class["tree"]), pixel.TREE_MAX)
        self.assertEqual(server.pixel_class["tree"][-1]["by"], "Mia")
        self.assertEqual(server.pixel_class["tree"][0]["by"], "K1")

    def test_no_chest_in_the_village_and_every_chest_still_counts(self):
        self.assertNotIn("village", pixel.CHEST_SPOTS)
        self.assertEqual(server.room_do(self.mia, {"what": "chest", "place": "village", "code": "jump()"})["error"], "bad")

    def test_going_to_the_village(self):
        self.assertTrue(server.room_do(self.mia, {"what": "go", "name": "village"})["ok"])
        self.assertGreaterEqual(self.spot(self.mia)["x"], server.village_left())

    def test_the_projector_gets_the_snowman_and_tree(self):
        view = server.room_view(None, -1)
        self.assertEqual(view["snowman"]["need"], pixel.SNOWMAN_BALLS)
        self.assertEqual(view["tree"], [])


if __name__ == "__main__":
    unittest.main()
