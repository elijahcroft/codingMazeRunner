"""The class mural: painting together, its fair limits, and keeping it."""
import os
import tempfile
import unittest
from unittest.mock import patch

import pixel
import server


class Mural(unittest.TestCase):
    def setUp(self):
        self.saved = (server.pixel_room, server.players, server.pixel_class,
                      server.pixel_feed, server.STATE_FILE)
        self.folder = tempfile.TemporaryDirectory()
        server.pixel_room = dict(server.room_empty(), open=True, words=False)
        server.players = {}
        server.pixel_class = {"open": len(pixel.LEVEL_ORDER) - 1}
        server.pixel_feed = []
        server.STATE_FILE = os.path.join(self.folder.name, "state.json")
        server.mural_out.clear()
        if server.mural_batch_timer[0]:
            server.mural_batch_timer[0].cancel()
            server.mural_batch_timer[0] = None
        self.clock = 1000.
        for thing in (patch.object(server.time, "time", side_effect=lambda: self.clock),
                      patch.object(server.time, "strftime", side_effect=lambda fmt, t=None: "2026-11-16"),
                      patch.object(server, "pixel_save_soon"),
                      patch.object(server, "mural_schedule")):     # tests flush by hand
            thing.start()
            self.addCleanup(thing.stop)
        self.addCleanup(self.restore)

    def restore(self):
        if server.mural_batch_timer[0]:
            server.mural_batch_timer[0].cancel()
            server.mural_batch_timer[0] = None
        server.mural_out.clear()
        (server.pixel_room, server.players, server.pixel_class,
         server.pixel_feed, server.STATE_FILE) = self.saved
        self.folder.cleanup()

    def kid(self, name):
        p = {"id": "private-" + name, "name": name}
        server.players[p["id"]] = p
        entry = server.pixel_entry(p)
        entry["solved"].update({key: [True] * 3 for key in pixel.LEVEL_ORDER})
        self.assertTrue(server.room_do(p, {"what": "join"})["ok"])
        return p

    def paint(self, kid, cell, ink=3):
        return server.room_do(kid, {"what": "mural", "action": "paint", "cell": cell, "ink": ink})

    def mural(self, kid=None):
        return server.mural_view(kid)

    def test_paint_undo_and_the_rate_limit(self):
        mia = self.kid("Mia")
        for cell in (0, 1, 2):
            self.assertTrue(self.paint(mia, cell)["ok"])
        self.assertEqual(self.paint(mia, 3), {"error": "wait"})     # 3 a second, then wait
        self.clock += 1.01
        self.assertTrue(self.paint(mia, 3)["ok"])
        self.assertEqual(self.mural(mia)["grid"][:4], "3333")
        self.assertEqual(self.mural(mia)["mine"], 4)
        undo = server.room_do(mia, {"what": "mural", "action": "undo"})
        self.assertTrue(undo["ok"])
        self.assertEqual(self.mural(mia)["grid"][:4], "333.")
        self.assertEqual(self.mural(mia)["mine"], 3)
        self.assertEqual(self.mural(mia)["painted_today"], 4)      # undo doesn't take back the reward count

    def test_undo_takes_only_your_own_last_square(self):
        mia, ben = self.kid("Mia"), self.kid("Ben")
        self.assertTrue(self.paint(mia, 0, 9)["ok"])
        self.assertTrue(self.paint(ben, 1, 2)["ok"])
        self.assertTrue(server.room_do(mia, {"what": "mural", "action": "undo"})["ok"])
        grid = self.mural(mia)["grid"]
        self.assertEqual(grid[0], ".")
        self.assertEqual(grid[1], "2")                             # Ben's square is still there
        self.assertTrue(server.room_do(ben, {"what": "mural", "action": "undo"})["ok"])
        self.assertEqual(self.mural(mia)["grid"][1], ".")
        self.assertEqual(server.room_do(mia, {"what": "mural", "action": "undo"}), {"error": "nothing"})

    def test_teacher_removes_one_student_then_clears_all(self):
        mia, ben = self.kid("Mia"), self.kid("Ben")
        for cell in (0, 1):
            self.assertTrue(self.paint(mia, cell)["ok"])
        self.assertTrue(self.paint(ben, 2, 7)["ok"])
        self.assertEqual(self.mural(None)["total"], 3)
        out = server.pixel_teacher({"action": "mural_remove", "id": mia["id"]})
        self.assertTrue(out["ok"])
        self.assertEqual(out["removed"], 2)
        view = self.mural(mia)
        self.assertEqual(view["grid"][:3], "..7")
        self.assertEqual(view["total"], 1)
        self.assertEqual([p["name"] for p in view["painters"]], ["Ben"])
        self.assertTrue(server.pixel_teacher({"action": "mural_clear"})["ok"])
        self.assertEqual(self.mural(None)["total"], 0)
        self.assertNotIn("3", self.mural(None)["grid"])

    def test_the_mural_is_in_the_saved_class_state(self):
        mia = self.kid("Mia")
        for cell in (4, 5):
            self.assertTrue(self.paint(mia, cell, 11)["ok"])
        grid = self.mural(mia)["grid"]
        server.save_state()
        server.pixel_class.clear()
        server.load_state()
        self.assertEqual(server.mural_state()["grid"], grid)
        self.assertEqual(server.mural_teacher_view()["grid"], grid)
        self.assertTrue(self.paint(mia, 6, 11)["ok"])

    def test_many_squares_leave_as_one_batched_event(self):
        mia, ben = self.kid("Mia"), self.kid("Ben")
        after = server.pixel_room["seq"]
        for cell in (0, 1, 2):
            self.assertTrue(self.paint(mia, cell)["ok"])
        for cell in (10, 11):
            self.assertTrue(self.paint(ben, cell, 8)["ok"])
        self.assertFalse([e for e in server.pixel_room["events"] if e["kind"] == "mural"])
        server.mural_flush()
        events = [e for e in server.room_view(mia, after)["events"] if e["kind"] == "mural"]
        self.assertEqual(len(events), 1)                           # not one event per square
        self.assertEqual(len(events[0]["cells"]), 5)
        self.assertEqual({cell[2] for cell in events[0]["cells"]}, {"Mia", "Ben"})

    def test_ten_squares_pay_once_a_day_and_keep_the_badge(self):
        mia = self.kid("Mia")
        entry = server.pixel_entry(mia)
        coins = entry["coins"]
        for cell in range(10):
            self.clock += .4
            self.assertTrue(self.paint(mia, cell, cell % 16)["ok"])
        self.assertTrue(entry["mural_day"][2])
        self.assertGreaterEqual(entry["coins"], coins + pixel.COINS_MURAL)
        self.assertIn("mural", entry["badges"])
        paid = entry["coins"]
        self.clock += .4
        self.assertTrue(self.paint(mia, 10, 1)["ok"])
        self.assertEqual(entry["coins"], paid)                     # the daily treat doesn't pay twice
        self.assertEqual(entry["badges"].count("mural"), 1)

    def test_a_hidden_name_stays_hidden_but_the_teacher_sees_it(self):
        mia, ben = self.kid("Mia"), self.kid("Ben")
        server.pixel_entry(mia)["hide_name"] = True
        self.assertTrue(self.paint(mia, 0, 4)["ok"])
        view = self.mural(ben)
        self.assertEqual(view["names"], ["Secret pal"])
        self.assertEqual(view["painters"], [{"name": "Secret pal", "count": 1}])
        teacher = server.mural_teacher_view()
        self.assertEqual(teacher["painters"][0]["name"], "Mia")
        self.assertEqual(teacher["painters"][0]["id"], mia["id"])

    def test_bad_squares_and_eraser(self):
        mia = self.kid("Mia")
        self.assertEqual(self.paint(mia, -1), {"error": "bad"})
        self.assertEqual(self.paint(mia, server.MURAL_CELLS), {"error": "bad"})
        self.assertEqual(self.paint(mia, 0, 99), {"error": "bad"})
        self.assertTrue(self.paint(mia, 0, 5)["ok"])
        self.assertTrue(self.paint(mia, 0, -1)["ok"])              # eraser
        self.assertEqual(self.mural(mia)["grid"][0], ".")
        self.assertEqual(self.mural(mia)["total"], 0)


if __name__ == "__main__":
    unittest.main()
