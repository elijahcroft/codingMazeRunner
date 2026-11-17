"""Odd requests get a friendly answer, never a dropped connection, and a player who
leaves in the middle of a race doesn't leave the round broken."""
import unittest
from unittest.mock import patch

import pixel
import server
import test_pixel
from test_pixel_fun import Fun


class OddRequests(Fun):
    """A list or a dictionary where a word belongs is answered, not raised."""

    def test_a_what_that_is_not_a_word_is_turned_away(self):
        for what in ([], {}, ["walk"], {"walk": 1}):
            with self.subTest(what=what):
                self.assertIn("error", server.room_do(self.mia, {"what": what}))

    def test_a_move_name_that_is_not_a_word_is_turned_away(self):
        for name in ([], {}, ["dance"], {"dance": 1}):
            with self.subTest(name=name):
                self.assertIn("error", self.do(self.mia, "move", name=name))

    def test_buying_with_a_key_that_is_not_a_word_is_turned_away(self):
        for key in ([], {}, ["beanie"], {"beanie": 1}):
            with self.subTest(key=key):
                self.assertIn("error", self.do(self.mia, "buy", key=key))

    def test_wearing_an_item_that_is_not_a_word_is_turned_away(self):
        for item in ([], {}, ["beanie"], {"beanie": 1}):
            with self.subTest(item=item):
                self.assertIn("error", self.do(self.mia, "wear", slot="hat", item=item))

    def test_a_chest_place_that_is_not_a_word_is_turned_away(self):
        for place in ([], {}, ["park"], {"park": 1}):
            with self.subTest(place=place):
                self.assertIn("error", self.do(self.mia, "chest", place=place, code="jump()"))

    def test_saying_something_that_is_not_words_is_turned_away(self):
        server.pixel_room["words"] = True          # even with typing on
        for text in (None, [], {}, ["Hello!"], 5, True):
            with self.subTest(text=text):
                self.assertIn("error", self.do(self.mia, "say", text=text))
        self.assertTrue(self.do(self.mia, "say", text="Hello!")["ok"])

    def test_looking_and_furnishing_with_a_key_that_is_not_a_word_is_turned_away(self):
        self.assertTrue(self.do(self.mia, "home")["ok"])
        for key in ([], {}, ["lamp"], {"lamp": 1}):
            with self.subTest(key=key):
                self.assertIn("error", self.do(self.mia, "look", key=key))
                self.assertIn("error", self.do(self.mia, "furnish", key=key, x=100, y=.5))

    def test_a_player_id_that_is_not_a_word_is_turned_away(self):
        for path, more in (("/pixel/save", {"drawing": {}}), ("/pixel/delete", {"key": "abc"}),
                           ("/pixel/pal", {"key": "pip"})):
            for pid in ([], {}, ["private-Mia"]):
                with self.subTest(path=path, pid=pid):
                    self.assertEqual(server.pixel_post(path, dict(more, id=pid)), {"error": "join"})


class DeletingADrawing(Fun):
    def test_deleting_a_drawing_takes_its_ornament_off_the_class_tree(self):
        self.entry(self.mia)["drawings"].append(dict(pixel.PIP, key="d1", title="Cat"))
        with patch.object(server, "winter", return_value=True):
            self.assertTrue(self.do(self.mia, "ornament", key="d1")["ok"])
            self.assertEqual(len(server.pixel_class["tree"]), 1)
            self.assertTrue(server.pixel_post("/pixel/delete", {"id": self.mia["id"], "key": "d1"})["ok"])
        self.assertEqual(server.pixel_class["tree"], [])


class LeavingARace(Fun):
    def start(self):
        self.assertTrue(self.do(self.mia, "game", action="create", kind="race")["ok"])
        self.assertTrue(self.do(self.ben, "game", action="join")["ok"])
        self.assertTrue(self.do(self.alex, "game", action="join")["ok"])
        self.assertTrue(self.do(self.mia, "game", action="start")["ok"])
        return server.pixel_room["game"], {p["name"]: self.spot(p)["seat"]
                                            for p in (self.mia, self.ben, self.alex)}

    def finished_then_left(self):
        game, seats = self.start()
        game["done"].append(seats["Mia"])
        self.assertTrue(self.do(self.mia, "leave")["ok"])
        return game, seats

    def test_a_finished_player_who_leaves_does_not_break_the_timeout(self):
        game, _ = self.finished_then_left()
        server.game_tick(self.clock + server.RACE_SECONDS + 1)
        self.assertEqual(game["phase"], "results")
        self.assertIn("Nobody reached", game["message"])

    def test_the_next_finisher_wins_if_the_first_one_left(self):
        game, seats = self.finished_then_left()
        game["done"].extend([seats["Ben"], seats["Alex"]])
        server.game_tick(self.clock)
        self.assertEqual(game["phase"], "results")
        self.assertIn("Ben won", game["message"])
        self.assertEqual(self.entry(self.ben)["coins"], pixel.COINS_ROUND + pixel.COINS_WIN)
        self.assertEqual(self.entry(self.alex)["coins"], pixel.COINS_ROUND)


class OddRequestsOverHttp(unittest.TestCase):
    tearDown, post, get = (test_pixel.StudioOverHttp.tearDown,
                           test_pixel.StudioOverHttp.post, test_pixel.StudioOverHttp.get)

    def setUp(self):
        test_pixel.StudioOverHttp.setUp(self)
        self.saved_room = server.pixel_room
        self.addCleanup(lambda: setattr(server, "pixel_room", self.saved_room))
        server.pixel_room = dict(server.room_empty(), open=True, words=False)

    def join(self, name="Mia"):
        me = self.post("/join", {"name": name})["id"]
        server.pixel_entry(server.players[me])["hang_let_in"] = True
        return me

    def test_odd_requests_get_an_answer_instead_of_a_dropped_connection(self):
        me = self.join()
        self.assertTrue(self.post("/pixel/room/do", {"id": me, "what": "join"})["ok"])
        self.assertEqual(self.post("/pixel/room/do", {"id": me, "what": []}), {"error": "bad"})
        for more in ({"what": "move", "name": []}, {"what": "buy", "key": []},
                     {"what": "wear", "slot": "hat", "item": []},
                     {"what": "chest", "place": [], "code": "jump()"}):
            with self.subTest(more=more):
                self.assertIn("error", self.post("/pixel/room/do", dict(more, id=me)))
        self.assertTrue(self.post("/pixel/room/do", {"id": me, "what": "home"})["ok"])
        for more in ({"what": "look", "key": []}, {"what": "furnish", "key": [], "x": 100, "y": .5}):
            with self.subTest(more=more):
                self.assertIn("error", self.post("/pixel/room/do", dict(more, id=me)))
        for path, more in (("/pixel/save", {"drawing": {}}), ("/pixel/delete", {"key": "abc"}),
                           ("/pixel/pal", {"key": "pip"})):
            for pid in ([], {}):
                with self.subTest(path=path, pid=pid):
                    self.assertEqual(self.post(path, dict(more, id=pid)), {"error": "join"})


if __name__ == "__main__":
    unittest.main()
