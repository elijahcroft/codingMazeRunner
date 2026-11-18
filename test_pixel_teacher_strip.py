"""The teacher's "Where the class is" strip: one count per chapter, plus
Not started and All done, from the same overview the page reads."""
import unittest

import pixel
import server


def through(chapter):
    """Every mission before one chapter, so the student's open mission is the
    first mission of that chapter."""
    return [lv["key"] for lv in pixel.LEVELS if lv["chapter"] < chapter]


class WhereTheClassIs(unittest.TestCase):
    def setUp(self):
        self.saved = server.players, server.pixel_room, server.pixel_class, server.pixel_feed
        server.players = {}
        server.pixel_room = dict(server.room_empty(), open=False, words=False)
        server.pixel_class = {"open": 0}
        server.pixel_feed = []
        self.addCleanup(self.restore)

    def restore(self):
        server.players, server.pixel_room, server.pixel_class, server.pixel_feed = self.saved

    def kid(self, name, solved=(), runs=()):
        p = {"id": "kid-" + name, "name": name}
        server.players[p["id"]] = p
        entry = server.pixel_entry(p)
        for key in solved:
            entry["solved"][key] = [True, True, True]
        for key in runs:
            entry["runs"][key] = entry["runs"].get(key, 0) + 1
        return p

    def strip(self):
        return server.pixel_overview()["strip"]

    def test_a_made_up_class_is_counted_per_chapter_and_at_both_ends(self):
        self.kid("Noa")                                  # opened the page, ran nothing
        self.kid("Mia", ["a1"])                          # on Say hello's next mission
        self.kid("Ben", ["a1"], runs=["a1", "a2"])       # tried the next one too
        self.kid("Fay", runs=["a1"])                     # trying Say hello
        self.kid("Cy", through(1))                       # finished Opening Night
        self.kid("Dee", through(15))                     # far along: Make Music
        self.kid("Eli", pixel.LEVEL_ORDER)               # every mission done

        strip = self.strip()
        counts = {tile["key"]: tile["count"] for tile in strip["chapters"]}
        self.assertEqual(counts["a"], 3)                 # Mia, Ben and Fay
        self.assertEqual(counts["h"], 1)                 # Cy
        self.assertEqual(counts["u"], 1)                 # Dee
        self.assertEqual(counts["b"], 0)
        self.assertEqual(strip["not_started"], 1)        # Noa
        self.assertEqual(strip["all_done"], 1)           # Eli
        self.assertEqual(sum(counts.values()) + strip["not_started"] + strip["all_done"], 7)

        places = {row["name"]: row["place"] for row in server.pixel_overview()["students"]}
        self.assertEqual(places, {"Noa": "not", "Mia": "a", "Ben": "a", "Fay": "a",
                                  "Cy": "h", "Dee": "u", "Eli": "done"})

    def test_the_chapter_tile_names_are_short_and_keep_the_icons(self):
        strip = self.strip()
        self.assertEqual([tile["key"] for tile in strip["chapters"]],
                         [chapter["key"] for chapter in pixel.CHAPTERS])
        for tile, chapter in zip(strip["chapters"], pixel.CHAPTERS):
            with self.subTest(chapter=chapter["key"]):
                self.assertEqual(tile["icon"], chapter["icon"])
                self.assertEqual(tile["name"], chapter["name"])
                self.assertTrue(tile["short"])
                self.assertLessEqual(len(tile["short"]), len(chapter["name"]))

    def test_all_done_means_every_mission_is_finished_not_every_star(self):
        self.kid("Eli")
        entry = server.pixel_entry(server.players["kid-Eli"])
        for key in pixel.LEVEL_ORDER:
            entry["solved"][key] = [True, False, False]
        strip = self.strip()
        self.assertEqual(strip["all_done"], 1)
        self.assertEqual(strip["not_started"], 0)
        self.assertEqual(sum(tile["count"] for tile in strip["chapters"]), 0)

    def test_a_student_who_has_not_run_stays_not_started_when_missions_open_ahead(self):
        self.kid("Noa")
        server.pixel_class["open"] = pixel.LEVEL_ORDER.index("b1")
        strip = self.strip()
        self.assertEqual(strip["not_started"], 1)
        self.assertEqual({tile["key"]: tile["count"] for tile in strip["chapters"]}["b"], 0)
        self.assertEqual(server.pixel_overview()["students"][0]["place"], "not")


if __name__ == "__main__":
    unittest.main()
