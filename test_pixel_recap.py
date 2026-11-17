"""📋 Today's recap: the end-of-lesson celebration on the projector."""
import json
import os
import tempfile
import unittest
from unittest.mock import patch

import pixel
import server


def drawing(key):
    return {"key": key, "title": "Luna", "size": 16, "speed": 6,
            "palette": ["#000000", "#ffffff"], "frames": ["." * 256]}


class Recap(unittest.TestCase):
    def setUp(self):
        self.saved = (server.players, server.pixel_class, server.pixel_feed,
                      server.pixel_room, server.pixel_recap)
        server.players = {}
        server.pixel_class = {"open": len(pixel.LEVEL_ORDER) - 1}
        server.pixel_feed = []
        server.pixel_room = dict(server.room_empty(), open=True, words=False)
        server.pixel_recap = {"n": 0, "recap": None}
        self.clock = 1000.
        self.today = "2026-11-17"
        for p in (patch.object(server.time, "time", side_effect=lambda: self.clock),
                  patch.object(server.time, "strftime", side_effect=lambda fmt, t=None: self.today),
                  patch.object(server, "pixel_save_soon"),
                  patch.object(server, "save_state")):
            p.start()
            self.addCleanup(p.stop)
        self.addCleanup(self.restore)

    def restore(self):
        (server.players, server.pixel_class, server.pixel_feed,
         server.pixel_room, server.pixel_recap) = self.saved

    def kid(self, name, solved=(), **fields):
        p = {"id": "private-" + name, "name": name}
        server.players[p["id"]] = p
        entry = server.pixel_entry(p)
        for key in solved:
            entry["solved"][key] = [True, False, False]
        for key, value in fields.items():
            entry[key] = value
        return p

    def record(self, p, key="a1", stars=(True, False, False), code="", fixing=False, **out):
        data = {"stars": list(stars), "error": None}
        data.update(out)
        return server.pixel_record(p, key, code, data, fixing=fixing)

    def show_spot(self, p, seat=1):
        return {"seat": seat, "name": server.hang_name(p), "real": p["name"],
                "x": 100, "y": .5, "loc": 0, "rest": None}

    def room(self, kids):
        spots, joined = {}, []
        for i, p in enumerate(kids):
            seat = i + 1
            joined.append(seat)
            spots[p["id"]] = self.show_spot(p, seat)
        server.pixel_room["here"] = spots
        return joined

    def play_game(self, kind, kids, winners=()):
        joined = self.room(kids)
        server.pixel_room["game"] = {"kind": kind, "phase": "playing", "joined": joined,
                                     "host": joined[0], "until": self.clock + 60, "rewards": {}}
        server.game_finish("Game over!", reward=True, winners=winners)

    def test_counts_from_a_made_up_day(self):
        mia, ben, cy = self.kid("Mia"), self.kid("Ben"), self.kid("Cy")
        self.record(mia, "a1", stars=(True, True, False))          # 2 stars
        self.record(mia, "a1", stars=(True, True, False), code="say('hi')", remix=True)   # Your turn
        self.record(mia, "a1", stars=(True, True, False), code="say('hi'", fixing=True, fix=True)   # Fix it
        self.record(ben, "u1", stars=(True, True, True))           # a new chapter, 3 stars
        self.play_game("apples", [mia, ben, cy], winners=[1])
        self.record(cy, "a1", stars=(False, False, False))         # a try, so Cy has played too
        self.room([ben])
        entry = server.pixel_entry(ben)
        entry["solved"].setdefault("a1", [True, False, False])
        entry["solved"][pixel.FREE_AFTER] = [True, False, False]
        entry["free_code"] = "jump()"
        self.assertTrue(server.room_perform(ben, self.show_spot(ben), {})["ok"])
        spot = {"seat": 9, "name": "Cy", "x": 780, "y": .5, "loc": 0}
        self.assertTrue(server.room_fish(cy, spot, {"action": "cast"})["ok"])
        spot["bite"] = self.clock - 1
        self.assertTrue(server.room_fish(cy, spot, {})["ok"])
        self.assertTrue(server.room_find(cy, {"seat": 9, "loc": 0}, "park0")["ok"])
        self.assertTrue(server.pixel_post("/pixel/save", {"id": cy["id"], "drawing": drawing("new")})["ok"])

        out = server.pixel_recap_view()
        self.assertEqual(out["day"], "2026-11-17")
        self.assertEqual(out["missions"], 2)
        self.assertEqual(out["stars"], 5)
        self.assertEqual(out["students"], 3)
        self.assertEqual([c["key"] for c in out["chapters"]], ["a", "u"])
        self.assertEqual([c["icon"] for c in out["chapters"]], ["🎭", "🎵"])
        self.assertEqual((out["turns"], out["fixes"]), (1, 1))
        self.assertEqual(out["games"], [{"key": "apples", "icon": "🍎", "name": "Apple grab", "count": 1}])
        self.assertEqual((out["shows"], out["fish"], out["gems"], out["drawings"]), (1, 1, 1, 1))
        self.assertEqual(out["party"], {"points": 0, "goal": 15, "next": "Golden crown"})
        self.assertEqual(out["unlocks"], ["Snowy hill"])

    def test_yesterdays_events_do_not_count(self):
        mia = self.kid("Mia")
        self.record(mia, "a1", stars=(True, False, False))
        self.today = "2026-11-18"
        ben = self.kid("Ben")
        self.record(ben, "a1", stars=(True, True, False))

        out = server.pixel_recap_view()
        self.assertEqual(out["missions"], 1)
        self.assertEqual(out["stars"], 2)
        self.assertEqual(out["students"], 1)
        self.assertEqual([c["key"] for c in out["chapters"]], ["a"])
        said = " ".join(s["text"] for s in out["shoutouts"])
        self.assertIn("Ben", said)
        self.assertNotIn("Mia", said)

    def test_shout_outs_are_kind_and_spread_around(self):
        kids = [self.kid(f"Kid{i}") for i in range(6)]
        day = server.pixel_day()
        for i, p in enumerate(kids):
            server.pixel_day_kid(p).update(stars=2 + i, claps=i)
        day["chapters"] = ["u"]
        day["first_chapter"] = {"u": kids[0]["id"]}
        day["first_mission"] = {"pid": kids[1]["id"], "name": "Say hello"}
        day["first_drawing"] = {"pid": kids[2]["id"]}
        day["first_show"] = {"pid": kids[3]["id"]}
        day["first_game"] = {"pid": kids[4]["id"], "kind": "apples"}

        out = server.pixel_recap_view()
        shouts = out["shoutouts"]
        self.assertGreaterEqual(len(shouts), 3)
        self.assertLessEqual(len(shouts), 5)
        self.assertEqual(len({s["who"] for s in shouts}), len(shouts))     # never the same student twice
        for shout in shouts:
            text = shout["text"].lower()
            for bad in ("worst", "last place", "least", "bottom"):
                self.assertNotIn(bad, text)
            self.assertTrue(shout["text"].strip())

    def test_hide_names_is_respected(self):
        mia = self.kid("Mia", hide_name=True)
        server.pixel_day()["first_mission"] = {"pid": mia["id"], "name": "Say hello"}
        server.pixel_day()["first_chapter"] = {"a": mia["id"]}
        server.pixel_day()["chapters"] = ["a"]

        out = server.pixel_recap_view()
        self.assertNotIn("Mia", json.dumps(out))
        self.assertTrue(any("Secret pal" in s["text"] for s in out["shoutouts"]))
        self.assertTrue(server.pixel_recap_show()["ok"])
        self.assertNotIn("Mia", json.dumps(server.pixel_room["events"]))

    def test_the_teacher_needs_the_admin_key(self):
        self.kid("Mia")
        self.assertEqual(server.pixel_post("/pixel/teacher", {"action": "recap"}),
                         {"error": "Wrong admin key."})
        self.assertEqual(server.pixel_recap["n"], 0)
        self.assertFalse(any(e["kind"] == "recap" for e in server.pixel_room["events"]))
        out = server.pixel_post("/pixel/teacher", {"action": "recap", "key": server.ADMIN_KEY})
        self.assertTrue(out["ok"])
        self.assertEqual(server.pixel_recap["n"], 1)
        event = [e for e in server.pixel_room["events"] if e["kind"] == "recap"][-1]
        self.assertEqual(event["recap_id"], 1)
        self.assertEqual(event["shoutouts"], [])
        got = server.pixel_get("/pixel/recap", {"after": ["0"]})
        self.assertEqual(got["recap_id"], 1)
        self.assertEqual(server.pixel_get("/pixel/recap", {"after": ["1"]}), {"n": 1})
        self.assertEqual(server.pixel_get("/pixel/recap", {"now": ["1"]}), {"n": 1})

    def test_an_old_save_without_days_still_works(self):
        server.pixel_class = {"open": 0}
        self.kid("Mia")
        out = server.pixel_recap_view()
        self.assertEqual((out["missions"], out["stars"], out["students"], out["shoutouts"]),
                         (0, 0, 0, []))
        self.assertEqual(out["party"], {"points": 0, "goal": 10, "next": "Snowy hill"})
        self.assertEqual(server.pixel_recap_show()["students"], 0)

    def test_an_old_state_file_loads_and_makes_a_recap(self):
        old_file = server.STATE_FILE
        name = ""
        try:
            with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
                name = f.name
                json.dump({"players": {"p0": {"id": "p0", "name": "Old Pal",
                                              "pixel": {"solved": {"a1": [True, False, False]}}}},
                           "next": 1, "pixel_class": {"open": 0}}, f)
            server.players.clear()
            server.STATE_FILE = name
            server.load_state()
            self.assertIn("p0", server.players)
            self.assertEqual(server.pixel_recap_view()["missions"], 0)
            self.assertTrue(server.pixel_recap_show()["ok"])
        finally:
            server.STATE_FILE = old_file
            if name:
                os.unlink(name)


if __name__ == "__main__":
    unittest.main()
