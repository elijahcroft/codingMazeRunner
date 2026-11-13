"""The Rover Farm (planet_farm.py and its routes in server.py)."""
import json
import os
import tempfile
import threading
import unittest
from unittest import mock
from urllib.request import Request, urlopen

import planet_farm as farm_rules
import server

DAY = "2026-11-11"   # a day when the wanted crop (star melon) isn't one a new farm has
ROW = 'for i in range(3):\n    harvest()\n    plant("berry")\n    east()\n'


def fresh(**changes):
    """A farm past its teaching jobs, so a test sees only what it asks about."""
    f = farm_rules.new_farm(1)
    f["job"] = len(farm_rules.JOBS)
    f.update(changes)
    return f


def day(f, code, stars=0):
    return farm_rules.run_day(f, code, stars, DAY)


class Rules(unittest.TestCase):
    def test_a_day_picks_plants_and_grows_overnight(self):
        f = fresh()
        out = day(f, ROW)
        self.assertEqual(out["picked"], {"berry": 3})
        self.assertEqual(f["day"], 1)
        # Planted today, ripe in the morning.
        self.assertTrue(all(cell[0] == "berry" and cell[1] == 1 for cell in f["field"][0]))
        self.assertEqual(sum(day(f, ROW)["picked"].values()), 3)

    def test_nothing_is_lost_by_picking_too_early(self):
        f = fresh(crops=["berry", "carrot"], field=[[["carrot", 1, 0], None, None]])
        out = day(f, "harvest()\n")
        self.assertEqual(out["picked"], {})
        self.assertEqual(f["field"][0][0][:2], ["carrot", 2])   # still there, and it grew
        self.assertIn("if ripe():", " ".join(out["say"]))

    def test_the_battery_ends_the_day_and_keeps_what_was_picked(self):
        f = fresh()
        out = day(f, "while True:\n    harvest()\n    east()\n")
        self.assertEqual(out["end"], "flat")
        self.assertEqual(out["ticks"], farm_rules.BATTERIES[0][0])
        self.assertIsNone(out["error"])
        self.assertEqual(sum(out["picked"].values()), 3)
        self.assertGreaterEqual(f["coins"], 3)

    def test_code_that_cannot_run_does_not_use_up_a_day(self):
        f = fresh()
        for code in ("harvest(", "pick()", 'plant("melon")', "\n".join(["east()"] * 11)):
            out = day(f, code)
            self.assertTrue(out["error"], code)
            self.assertFalse(out["counted"], code)
        self.assertEqual(f["day"], 0)
        self.assertEqual(f["field"][0][0][:2], ["berry", 1])

    def test_an_error_part_way_keeps_the_day_so_far(self):
        f = fresh()
        out = day(f, "harvest()\nfly()\n")
        self.assertEqual(out["line"], 2)
        self.assertTrue(out["counted"])
        self.assertEqual(out["picked"], {"berry": 1})

    def test_memory_is_a_line_limit_that_more_memory_lifts(self):
        f = fresh(coins=1000)
        long = "\n".join(["wait()"] * 11)
        self.assertTrue(day(f, long)["memory_full"])
        self.assertEqual(farm_rules.buy(f, "upgrade", "memory", DAY)["bought"], "More memory")
        self.assertFalse(day(f, long)["memory_full"])

    def test_stars_from_the_levels_make_the_farm_earn_more(self):
        plain, starry = fresh(), fresh()
        a, b = day(plain, ROW), day(starry, ROW, stars=100)
        self.assertEqual(b["bonus"], a["income"])
        self.assertEqual(starry["coins"] - plain["coins"], a["income"])

    def test_the_wanted_crop_pays_double_and_gold_pays_five_times(self):
        hot = farm_rules.hot_crop(DAY)
        f = fresh(crops=["berry", hot], field=[[[hot, 9, 0], [hot, 9, 1], ["berry", 1, 0]]])
        out = day(f, "harvest()\neast()\nharvest()\neast()\nharvest()\n")
        pay = farm_rules.CROPS[hot]["pay"]
        self.assertEqual(out["income"], pay * 2 + pay * 2 * 5 + (1 if hot != "berry" else 2))
        self.assertEqual(out["golden"], 1)

    def test_a_bigger_field_keeps_its_plants(self):
        f = fresh(coins=100)
        farm_rules.buy(f, "upgrade", "field", DAY)
        self.assertEqual([len(f["field"]), len(f["field"][0])], [2, 3])
        self.assertEqual(f["field"][0][0][0], "berry")
        self.assertEqual(f["field"][1], [None, None, None])

    def test_sun_blooms_only_grow_apart(self):
        f = fresh(crops=["berry", "bloom"], field=[[["bloom", 0, 0], ["bloom", 0, 0], None]])
        self.assertEqual(farm_rules.grow(f), 2)
        self.assertEqual([cell[1] for cell in f["field"][0][:2]], [0, 0])
        f["field"][0][1] = None
        self.assertEqual(farm_rules.grow(f), 0)
        self.assertEqual(f["field"][0][0][1], 1)

    def test_buying_needs_the_coins_and_happens_once(self):
        f = fresh(coins=5)
        self.assertIn("costs", farm_rules.buy(f, "crop", "carrot", DAY)["error"])
        f["coins"] = 500
        self.assertEqual(farm_rules.buy(f, "crop", "carrot", DAY)["bought"], "Moon carrot")
        self.assertIn("already", farm_rules.buy(f, "crop", "carrot", DAY)["error"])
        self.assertIn("crate", farm_rules.buy(f, "decor", "dino", DAY)["error"])
        self.assertEqual(f["coins"], 500 - farm_rules.CROPS["carrot"]["cost"])

    def test_part_of_the_year_things_come_and_go(self):
        turkey, snowman = farm_rules.DECOR_BY_KEY["turkey"], farm_rules.DECOR_BY_KEY["snowman"]
        self.assertTrue(farm_rules.in_season(turkey, "2026-11-10"))
        self.assertFalse(farm_rules.in_season(turkey, "2026-12-10"))
        self.assertTrue(farm_rules.in_season(snowman, "2026-12-25"))   # a season that crosses new year
        self.assertTrue(farm_rules.in_season(snowman, "2027-01-10"))
        self.assertFalse(farm_rules.in_season(snowman, "2027-02-01"))
        f = fresh(coins=10 ** 6)
        self.assertIn("today", farm_rules.buy(f, "decor", "snowman", "2026-11-10")["error"])

    def test_mistakes_get_the_farms_own_words(self):
        f = fresh()
        for code, part in (("pick()", "harvest()"), ("plant(berry)", None), ('plant("apple")', "isn't a crop"),
                           ('jump("east")', "On the farm"), ('if look("east") == "rock":\n    east()', '"fence"'),
                           ("harvest", "brackets"), ("water()", "overnight"),
                           ("while True:\n    ripe()", "something inside it that changes")):
            out = day(f, code)
            if part is None:
                self.assertIsNone(out["error"], code)
            else:
                self.assertIn(part, out["error"], code)

    def test_every_sensor_answers(self):
        f = fresh()
        out = day(f, 'print(ripe(), empty(), crop(), x(), y(), width(), height(), battery(), coins(), day(), look("west"))')
        self.assertIsNone(out["error"])
        self.assertEqual(out["prints"][0]["text"], "True False berry 1 1 3 1 14 0 1 fence")


class Jobs(unittest.TestCase):
    def test_every_job_can_be_done_by_typing_what_its_card_shows(self):
        """A student who types each card's code, and buys what a card says to
        buy, finishes every job, and never runs out of coins for the next one."""
        f = farm_rules.new_farm(5)
        code, days = f["code"], 0
        buys = {"field": ("upgrade", "field"), "battery": ("upgrade", "battery"),
                "carrot": ("crop", "carrot"), "memory": ("upgrade", "memory")}
        while f["job"] < len(farm_rules.JOBS):
            job = farm_rules.JOBS[f["job"]]
            if job["key"] in buys:
                out = farm_rules.buy(f, *buys[job["key"]], DAY)
                self.assertNotIn("error", out, job["key"])
                continue
            code = job.get("code", code)
            before = f["job"]
            for _ in range(6):   # a slow crop needs a few days to come ripe
                out = day(f, code)
                days += 1
                self.assertIsNone(out["error"], (job["key"], out["error"]))
                if f["job"] > before:
                    break
            self.assertGreater(f["job"], before, job["key"])
        self.assertLess(days, 40)
        self.assertIsNotNone(f["order"])

    def test_a_day_counts_for_one_job(self):
        f = farm_rules.new_farm(5)
        out = day(f, farm_rules.JOBS[2]["code"])   # picks 3 and plants 3 on day one
        # The first job, and the second because nothing is left to drive to: but
        # planting has to be done on a day of its own.
        self.assertEqual([j["title"] for j in out["jobs"]], ["Pick your first berry", "Drive and pick"])
        self.assertEqual(farm_rules.JOBS[f["job"]]["key"], "plant")
        self.assertEqual(len(day(f, farm_rules.JOBS[2]["code"])["jobs"]), 1)

    def test_picking_ahead_never_leaves_a_job_that_cannot_be_done(self):
        """Whatever a student picks on the first days, the job on the card can
        still be done with what's in the field (or the game moves them on)."""
        for first in ("harvest()\neast()\nharvest()\n", "east(2)\nharvest()\n", "east()\nharvest()\neast()\nharvest()\n"):
            f = farm_rules.new_farm(5)
            day(f, first)
            for _ in range(3):
                if farm_rules.JOBS[f["job"]]["key"] != "drive":
                    break
                day(f, "harvest()\neast()\nharvest()\neast()\nharvest()\n")
            self.assertNotEqual(farm_rules.JOBS[f["job"]]["key"], "drive", first)

    def test_the_code_is_offered_after_two_days_that_miss(self):
        f = farm_rules.new_farm(5)
        day(f, "harvest()\n")
        self.assertFalse(farm_rules.view(f, 0, DAY)["job"]["give"])
        day(f, "wait()\n"); day(f, "wait()\n")
        self.assertTrue(farm_rules.view(f, 0, DAY)["job"]["give"])

    def test_orders_fill_pay_and_bring_a_crate_every_third(self):
        f = fresh()
        f["order"] = farm_rules.next_order(f)
        crates = 0
        for _ in range(200):
            out = day(f, ROW)
            if out["order"]:
                self.assertGreater(out["order"]["pay"], 0)
                crates += bool(out["order"]["crate"])
            if f["orders"] >= 6:
                break
        self.assertEqual(f["orders"], 6)
        self.assertEqual(crates, 2)
        self.assertEqual(len(f["decor"]), 2)
        self.assertTrue(all(farm_rules.DECOR_BY_KEY[k].get("crate") for k in f["decor"]))

    def test_a_different_order_is_free(self):
        f = fresh(crops=list(farm_rules.CROPS))
        f["order"] = farm_rules.next_order(f)
        seen = set()
        for _ in range(12):
            seen.add(f["order"]["crop"])
            farm_rules.skip_order(f)
        self.assertGreater(len(seen), 1)
        self.assertEqual(f["orders"], 0)

    def test_crates_turn_to_coins_once_they_are_all_found(self):
        f = fresh(decor=[d["key"] for d in farm_rules.DECOR if d.get("crate")])
        self.assertGreater(farm_rules.open_crate(f)["coins"], 0)


class Tables(unittest.TestCase):
    """Adding a row to a table should be all it takes: these catch a bad row."""

    def test_prices_rise_and_the_first_of_each_is_free(self):
        for levels in (farm_rules.FIELDS, farm_rules.BATTERIES, farm_rules.MEMORIES):
            costs = [level[-1] for level in levels]
            self.assertEqual(costs[0], 0)
            self.assertEqual(costs, sorted(costs))
            self.assertEqual([level[0] for level in levels], sorted(level[0] for level in levels))

    def test_every_crop_and_yard_thing_is_whole(self):
        for key, crop in farm_rules.CROPS.items():
            self.assertTrue({"icon", "name", "days", "pay", "cost", "about"} <= set(crop), key)
        keys = [d["key"] for d in farm_rules.DECOR]
        self.assertEqual(len(keys), len(set(keys)))
        for d in farm_rules.DECOR:
            self.assertTrue({"icon", "name", "say"} <= set(d), d["key"])
            self.assertTrue(("cost" in d) != bool(d.get("crate")), d["key"])
            self.assertEqual("from" in d, "until" in d, d["key"])

    def test_the_whole_field_fits_the_biggest_battery_and_memory(self):
        """The biggest field can be farmed in one day by a program that fits."""
        f = fresh(field_level=len(farm_rules.FIELDS) - 1, battery_level=len(farm_rules.BATTERIES) - 1,
                  memory_level=2)
        w, h = farm_rules.FIELDS[-1][:2]
        f["field"] = [[["berry", 1, 0] for _ in range(w)] for _ in range(h)]
        code = ('for r in range(height()):\n    for i in range(width() - 1):\n        harvest()\n'
                '        plant("berry")\n        if r % 2 == 0:\n            east()\n        else:\n'
                '            west()\n    harvest()\n    plant("berry")\n    south()\n')
        out = day(f, code)
        self.assertIsNone(out["error"])
        self.assertEqual(out["picked"], {"berry": w * h})

    def test_a_view_is_json_and_names_what_can_be_bought(self):
        f = fresh(coins=50)
        view = farm_rules.view(f, 12, DAY)
        json.dumps(view)
        can = {g["key"] for kind in view["shop"].values() for g in kind if g["can"]}
        self.assertEqual(can, {"field", "battery", "memory", "carrot", "sign", "tree"})


class Routes(unittest.TestCase):
    """The farm over HTTP, on a server of its own with a save in a temp folder."""

    @classmethod
    def setUpClass(cls):
        cls.folder = tempfile.TemporaryDirectory()
        cls.patches = [mock.patch.object(server, "STATE_FILE", os.path.join(cls.folder.name, "s.json")),
                       mock.patch.object(server, "players", {}),
                       mock.patch.object(server, "FARM_GAP", 0),
                       mock.patch.dict(server.planet_class_settings, {"farm": True})]
        for p in cls.patches:
            p.start()
        cls.httpd = server.ThreadingHTTPServer(("127.0.0.1", 0), server.Handler)
        cls.base = f"http://127.0.0.1:{cls.httpd.server_address[1]}"
        threading.Thread(target=cls.httpd.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.httpd.shutdown()
        cls.httpd.server_close()
        for p in cls.patches:
            p.stop()
        cls.folder.cleanup()

    def post(self, path, data):
        req = Request(self.base + path, json.dumps(data).encode(), {"Content-Type": "application/json"})
        return json.load(urlopen(req))

    def get(self, path):
        return json.load(urlopen(self.base + path))

    def test_a_student_farms_buys_and_is_visited(self):
        ada = self.post("/join", {"name": "Ada"})["id"]
        bo = self.post("/join", {"name": "Bo"})["id"]
        view = self.get(f"/planet/farm/state?id={ada}")
        self.assertTrue(view["open"])
        self.assertEqual([view["w"], view["h"], view["coins"]], [3, 1, 0])
        self.assertNotIn("Ada", [f["name"] for f in view["class_farms"]])   # not your own, and Ada has no farm yet
        out = self.post("/planet/farm/run", {"id": ada, "code": ROW})
        self.assertEqual(out["picked"], {"berry": 3})
        self.assertEqual(out["badges"][0]["name"], "Green Wheels")
        self.assertEqual(out["farm"]["day"], 1)
        with server.lock:
            server.farm_of(server.players[ada])["coins"] = 100
        self.assertEqual(self.post("/planet/farm/buy", {"id": ada, "kind": "decor", "key": "sign"})["bought"], "Farm sign")
        # Bo sees Ada's farm by a handle, never by her id (an id is a login).
        friends = self.get(f"/planet/farm/state?id={bo}")["class_farms"]
        self.assertIn("Ada", [f["name"] for f in friends])
        who = next(f["who"] for f in friends if f["name"] == "Ada")
        self.assertNotEqual(who, ada)
        seen = self.get(f"/planet/farm/visit?id={bo}&who={who}")
        self.assertEqual(seen["name"], "Ada")
        self.assertEqual(seen["decor"][0]["key"], "sign")
        self.assertNotIn("code", seen)
        self.assertNotIn("coins", seen)
        self.assertIn("error", self.get(f"/planet/farm/visit?id={bo}&who=nobody"))
        self.assertEqual(self.get("/planet/farm/state?id=nobody"), {"error": "join"})
        # The teacher's list.
        with server.lock:
            rows = server.farm_class()
        self.assertIn(("Ada", 1, ["for"]), [(r["name"], r["days"], r["ideas"]) for r in rows])

    def test_a_closed_farm_runs_nothing_and_keeps_everything(self):
        cy = self.post("/join", {"name": "Cy"})["id"]
        self.post("/planet/farm/run", {"id": cy, "code": "harvest()"})
        with mock.patch.dict(server.planet_class_settings, {"farm": False}):
            self.assertEqual(self.get(f"/planet/farm/state?id={cy}")["open"], False)
            self.assertEqual(self.post("/planet/farm/run", {"id": cy, "code": "harvest()"}), {"open": False})
            self.assertEqual(self.post("/planet/farm/buy", {"id": cy, "kind": "decor", "key": "sign"}), {"open": False})
            self.assertFalse(self.get(f"/planet/ping?id={cy}")["farm"])
        self.assertEqual(self.get(f"/planet/farm/state?id={cy}")["day"], 1)
        self.assertTrue(self.get(f"/planet/state?id={cy}")["farm"])

    def test_days_cannot_be_run_faster_than_the_gap(self):
        di = self.post("/join", {"name": "Di"})["id"]
        with mock.patch.object(server, "FARM_GAP", 60):
            self.assertIn("picked", self.post("/planet/farm/run", {"id": di, "code": "harvest()"}))
            self.assertEqual(self.post("/planet/farm/run", {"id": di, "code": "harvest()"}), {"wait": True})

    def test_the_pages_are_served(self):
        for path in ("/planet/farm", "/planet/farm.js"):
            self.assertEqual(urlopen(self.base + path).status, 200)


if __name__ == "__main__":
    unittest.main()
