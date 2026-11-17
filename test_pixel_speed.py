"""Pixel Pals on slow school wifi: small Hang out updates, squeezed pages, and reloads that download nothing."""
import gzip
import threading
import unittest
import urllib.request
from unittest.mock import patch

import server


class SmallUpdates(unittest.TestCase):
    def setUp(self):
        self.saved = server.pixel_room, server.players, server.pixel_class
        server.pixel_room = dict(server.room_empty(), open=True, words=False)
        server.players = {}
        server.pixel_class = {"open": 3}
        self.addCleanup(self.restore)
        for patcher in (patch.object(server, "pixel_save_soon"), patch.object(server, "day_job")):
            patcher.start()
            self.addCleanup(patcher.stop)
        self.kids = []
        for name in ("Mia", "Ben", "Alex"):
            p = {"id": "private-" + name, "name": name}
            server.players[p["id"]] = p
            server.pixel_entry(p)
            self.assertTrue(server.room_do(p, {"what": "join"})["ok"])
            self.kids.append(p)

    def restore(self):
        server.pixel_room, server.players, server.pixel_class = self.saved

    def test_updates_leave_out_the_drawings_the_screen_already_has(self):
        mia = self.kids[0]
        whole = server.room_view(mia, -1)
        self.assertTrue(all("pal" in m for m in whole["members"]))      # the first answer has everything
        self.assertTrue(server.room_do(self.kids[1], {"what": "walk", "x": 50, "y": .5})["ok"])
        news = server.room_view(mia, whole["seq"])
        self.assertNotIn("members", news)
        self.assertTrue(news["events"])
        for row in news["game_members"]:
            self.assertEqual(set(row) - set(server.SYNC_KEYS), set())
            self.assertNotIn("pal", row)


class Pages(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.httpd = server.ClassroomServer(("127.0.0.1", 0), server.Handler)
        threading.Thread(target=cls.httpd.serve_forever, daemon=True).start()
        cls.base = f"http://127.0.0.1:{cls.httpd.server_address[1]}"

    @classmethod
    def tearDownClass(cls):
        cls.httpd.shutdown()
        cls.httpd.server_close()

    def get(self, path, **headers):
        try:
            with urllib.request.urlopen(urllib.request.Request(self.base + path, headers=headers)) as r:
                return r.status, r.headers, r.read()
        except urllib.error.HTTPError as e:
            return e.code, e.headers, e.read()

    def test_pages_come_squeezed_to_browsers_that_ask(self):
        status, headers, body = self.get("/pixel/page.js", **{"Accept-Encoding": "gzip, deflate"})
        self.assertEqual((status, headers["Content-Encoding"]), (200, "gzip"))
        self.assertEqual(gzip.decompress(body), server.STATIC["/pixel/page.js"])
        self.assertLess(len(body), len(server.STATIC["/pixel/page.js"]) / 2)
        status, headers, body = self.get("/pixel/page.js")
        self.assertIsNone(headers["Content-Encoding"])
        self.assertEqual(body, server.STATIC["/pixel/page.js"])

    def test_a_reload_with_nothing_new_downloads_nothing(self):
        status, headers, _ = self.get("/pixel")
        tag = headers["ETag"]
        self.assertEqual(headers["Cache-Control"], "no-cache")
        status, _, body = self.get("/pixel", **{"If-None-Match": tag})
        self.assertEqual((status, body), (304, b""))
        status, _, body = self.get("/pixel", **{"If-None-Match": '"old"'})
        self.assertEqual(status, 200)
        self.assertTrue(body)

    def test_big_answers_are_squeezed_too(self):
        status, headers, body = self.get("/pixel/room?after=-1", **{"Accept-Encoding": "gzip"})
        self.assertEqual(status, 200)
        if len(body) >= server.SQUEEZE_FROM or headers["Content-Encoding"]:
            self.assertEqual(headers["Content-Encoding"], "gzip")
            gzip.decompress(body)


if __name__ == "__main__":
    unittest.main()
