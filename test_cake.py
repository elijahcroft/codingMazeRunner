import json
import os
import tempfile
import threading
import unittest
from urllib.request import Request, urlopen

import cake
import server


def level(key):
    return cake.LEVEL_BY_KEY[key]


def run(key, code, seed=0):
    lv = level(key)
    results = cake.run_level(lv, code, seed=seed)
    return results, cake.stars(lv, results, code)


def happy(results):
    return [r["happy"] for r in results]


class LevelClaims(unittest.TestCase):
    """Every claim a level makes is a test, as in Strange Planet."""

    def test_every_reference_earns_all_three_stars(self):
        for lv in cake.LEVELS:
            seeds = range(40) if lv.get("bake_off") else [0]
            for seed in seeds:
                with self.subTest(level=lv["key"], seed=seed):
                    results, stars = run(lv["key"], lv["reference"], seed)
                    self.assertEqual(stars, [True, True, True],
                                     [(r["name"], r["reply"], r["error"]) for r in results])

    def test_the_last_hint_makes_every_customer_happy(self):
        for lv in cake.LEVELS:
            with self.subTest(level=lv["key"]):
                results, stars = run(lv["key"], lv["hints"][-1], 3)
                self.assertTrue(all(happy(results)),
                                [(r["name"], r["reply"]) for r in results])

    def test_starter_code_runs_without_an_error(self):
        for lv in cake.LEVELS + [{"key": "studio"}]:
            code = lv.get("starter", cake.STUDIO_STARTER)
            with self.subTest(level=lv["key"]):
                out = cake.bake(code, (lv.get("customers") or [{}])[0].get("ticket")
                                if lv["key"] != "7" else cake.bake_off_customers(1)[0]["ticket"],
                                cake.COMMANDS)
                self.assertIsNone(out["error"])

    def test_starters_dont_already_solve_the_level(self):
        for lv in cake.LEVELS:
            with self.subTest(level=lv["key"]):
                results, stars = run(lv["key"], lv["starter"])
                self.assertFalse(stars[0])

    def test_hard_coding_the_first_ticket_fails_the_rest_of_the_queue(self):
        for lv in cake.LEVELS:
            if not lv["customers"] or len(lv["customers"]) < 2:
                continue
            first = lv["customers"][0]
            with self.subTest(level=lv["key"]):
                # The reference with the first ticket pasted in as fixed values.
                code = f"order = {first['ticket']!r}\n" + lv["reference"]
                results, stars = run(lv["key"], code)
                self.assertTrue(results[0]["happy"])
                self.assertFalse(all(happy(results)))

    def test_compact_stars_need_a_loop(self):
        # Typing every candle out is too many lines for the compact star.
        code = 'layer("strawberry")\nlayer("strawberry")\nfrosting("pink")\n' + \
               'candle()\n' * 8 + 'write("Happy Birthday Ava")\n'
        results, stars = run("2a", code)
        self.assertEqual(stars, [True, False, False])

    def test_sprinkles_for_everyone_upsets_the_no_sprinkles_customers(self):
        code = 'layer(order["flavour"])\nlayer(order["flavour"])\nfrosting("white")\nsprinkles()\n'
        results, _ = run("4a", code)
        self.assertEqual(happy(results), [True, False, True, False])
        self.assertIn("NO sprinkles", results[1]["reply"])

    def test_age_rules_check_the_edges(self):
        wrong = level("4c")["reference"].replace("age < 10", "age <= 10")
        results, _ = run("4c", wrong)
        self.assertEqual([r["name"] for r in results if not r["happy"]], ["Max"])

    def test_a_birthday_rule_for_everyone_gives_the_wedding_candles(self):
        code = 'layer(order["flavour"])\nlayer(order["flavour"])\nfrosting("pink")\n' \
               'for i in range(order["age"]):\n    candle()\n'
        results, _ = run("4b", code)
        self.assertEqual(happy(results), [True, False, False, True])

    def test_counting_loops_reach_an_empty_list(self):
        # Bramble wants no toppings at all: a for over [] does nothing.
        results, _ = run("5c", level("5c")["hints"][-1])
        self.assertEqual(results[3]["cake"][0]["toppings"], [])
        self.assertTrue(results[3]["happy"])

    def test_wedding_names_go_on_the_bottom_tier(self):
        code = level("6c")["hints"][-1].replace('write(order["names"])\n', '') + \
            '\nwrite(order["names"])'
        results, _ = run("6c", code)
        self.assertFalse(any(happy(results)))
        self.assertIn("bottom tier", results[0]["reply"])

    def test_bake_off_tickets_cover_every_choice(self):
        for seed in range(60):
            tickets = [c["ticket"] for c in cake.bake_off_customers(seed)]
            with self.subTest(seed=seed):
                self.assertEqual({t["sprinkles"] for t in tickets}, {True, False})
                self.assertEqual({t["drip"] == "" for t in tickets}, {True, False})
                self.assertEqual({t["candles"] == 0 for t in tickets}, {True, False})
                self.assertEqual({t["toppings"] == [] for t in tickets}, {True, False})
                self.assertEqual({t["message"] == "" for t in tickets}, {True, False})

    def test_a_bake_off_program_that_skips_a_part_never_gets_five(self):
        reference = level("7")["reference"]
        for part in ("drip", "sprinkles", "candle", "topping", "write"):
            lines = reference.split("\n")
            i = next(i for i, l in enumerate(lines) if part + "(" in l)
            broken = "\n".join(lines[:i - 1] + lines[i + 1:])
            for seed in range(20):
                with self.subTest(part=part, seed=seed):
                    self.assertFalse(run("7", broken, seed)[1][2])

    def test_stars_for_creativity_and_python(self):
        _, stars = run("1a", 'layer("chocolate")\nlayer("chocolate")\nfrosting("white")\n')
        self.assertEqual(stars, [True, False, False])
        _, stars = run("3c", 'for i in range(order["layers"]):\n    layer(order["flavour"])\n'
                             'frosting(order["frosting"])\n'
                             'write(order["name"] + " is " + str(order["age"]))\n')
        self.assertEqual(stars, [True, False, True])
        _, stars = run("6a", level("6a")["hints"][-1])
        self.assertEqual(stars, [True, False, True])

    def test_a_def_that_never_runs_does_not_count(self):
        code = level("3a")["reference"] + "def unused():\n    candle()\n"
        results = cake.run_level(level("3a"), code)
        self.assertFalse(cake._met({"kind": "uses", "what": "def"}, results, code))


class Judge(unittest.TestCase):
    def cake_of(self, code):
        out = cake.bake(code)
        self.assertIsNone(out["error"])
        return out["cake"]

    def test_writing_ignores_capitals_and_punctuation(self):
        c = self.cake_of('layer("vanilla")\nwrite("happy birthday, AVA!!")')
        checks, _ = cake.judge({"layers": ["vanilla"], "text": "Happy Birthday Ava"}, c)
        self.assertTrue(all(ch["ok"] for ch in checks))

    def test_extras_are_your_own_touch(self):
        c = self.cake_of('layer("vanilla")\nfrosting("white")\ntopping("cherry")\n'
                         'topping("star")\nsprinkles()')
        checks, extras = cake.judge({"layers": ["vanilla"], "frosting": "white",
                                     "toppings": {"cherry": 1}}, c)
        self.assertTrue(all(ch["ok"] for ch in checks))
        self.assertEqual(sorted(extras), sorted(["sprinkles", "⭐"]))

    def test_complaints_say_what_is_wrong(self):
        c = self.cake_of('layer("vanilla")\nlayer("lemon")\nfrosting("pink")')
        checks, _ = cake.judge({"layers": ["vanilla", "strawberry"], "frosting": "white",
                                "candles": 3}, c)
        says = [ch["say"] for ch in checks if not ch["ok"]]
        self.assertEqual(says, ["Layer 2 from the bottom should be strawberry, not lemon.",
                                "The frosting should be white, not pink.",
                                "I need 3 candles, but I count 0."])

    def test_checklist_describes_the_order(self):
        self.assertEqual(cake.checklist(level("1c")["customers"][0]["want"]),
                         ["2 lemon layers", "white frosting", "chocolate drip",
                          "3 × 🐟 fish", 'writing: "MEOW"'])


class Interpreter(unittest.TestCase):
    def bake(self, code, order=None, unlocked=cake.LOCKED):
        return cake.bake(code, order, cake.COMMANDS, unlocked)

    def ok(self, code, order=None):
        out = self.bake(code, order)
        self.assertIsNone(out["error"], out["error"])
        return out

    def error(self, code, order=None, unlocked=cake.LOCKED):
        out = self.bake(code, order, unlocked)
        self.assertIsNotNone(out["error"])
        return out["error"]

    def prints(self, code, order=None):
        return [p["text"] for p in self.ok(code, order)["prints"]]

    def test_lists_dicts_and_loops_over_them(self):
        self.assertEqual(self.prints(
            'flavours = ["lemon", "lime"]\nflavours.append("grape")\n'
            'for f in flavours:\n    print(f)\nprint(len(flavours), flavours[-1], flavours[1:])\n'
            'd = {"a": 1}\nprint(d["a"], "a" in d, "lime" in flavours)'),
            ["lemon", "lime", "grape", "3 grape ['lime', 'grape']", "1 True True"])

    def test_text_tricks(self):
        self.assertEqual(self.prints(
            'name = "nana bea"\nprint(name.upper(), name.title())\n'
            'print(f"{name} is {80}!")\nprint("ha" * 3, str(7) + "!")\n'
            'for ch in "ab":\n    print(ch)'),
            ["NANA BEA Nana Bea", "nana bea is 80!", "hahaha 7!", "a", "b"])

    def test_the_order_ticket(self):
        order = {"name": "Mia", "flavour": "lemon", "layers": ["lime"]}
        self.assertEqual(self.prints('print(order["flavor"], order["name"])', order),
                         ["lemon Mia"])
        self.assertIn('Did you mean  ["name"]', self.error('print(order["nme"])', order))
        # Changing the ticket in one run doesn't change it for the next customer.
        self.ok('order["layers"].append("grape")', order)
        self.assertEqual(order["layers"], ["lime"])

    def test_no_ticket_before_chapter_3(self):
        self.assertIn("Chapter 3", self.error('layer(order["flavour"])'))

    def test_friendly_mistakes(self):
        self.assertIn('Put quotes round words', self.error("layer(chocolate)"))
        self.assertIn('Did you mean "chocolate"', self.error('layer("choclate")'))
        self.assertIn("is a colour", self.error('layer("pink")'))
        self.assertIn("is a flavour", self.error('layer("lime")\nfrosting("vanilla")'))
        self.assertIn('ONE topping', self.error('layer("lime")\ntopping("cherries")'))
        self.assertIn("Bake a layer first", self.error('frosting("pink")'))
        self.assertIn("str()", self.error('layer("lime")\nwrite("Age " + 8)'))
        self.assertIn("candle() adds one", self.error('layer("lime")\ncandles(8)'))
        self.assertIn("for i in range(8)", self.error('layer("lime")\ncandle(8)'))
        order = {"flavour": "lime"}
        self.assertIn('order["flavour"]', self.error("layer(order[flavour])", order))
        self.assertIn('order["flavour"]', self.error("layer(order.flavour)", order))
        self.assertIn("for i in range(4)", self.error('for i in 4:\n    candle()'))
        self.assertIn("positions", self.error('x = ["a"]\nprint(x[3])'))
        self.assertIn("Syntax error on line 1", self.error('layer("lime"'))

    def test_beginner_slips_say_what_to_type(self):
        self.assertIn("add brackets:  sprinkles()", self.error('layer("lime")\nsprinkles'))
        self.assertIn('layer("lime")', self.error('layer "lime"'))
        self.assertIn("own line", self.error('layer("lime") layer("lime")'))
        self.assertIn("colon", self.error('layer("lime")\nfor i in range(3) candle()'))
        self.assertIn("an  if  line", self.error('layer("lime")\nif 1 > 0\n    sprinkles()'))
        self.assertIn("space after  if", self.error('age = 3\nifage < 10:\n    sprinkles()'))
        self.assertIn("Take the  :  off", self.error('layer("lime")\nfrosting("pink"):'))
        # A name the program never sets is probably a word without its quotes...
        self.assertIn('"Enjoy"', self.error("print(Enjoy)"))
        # ...but one it sets later just needs setting first.
        self.assertIn("set it first", self.error("print(n)\nn = 2"))
        self.assertIn("doesn't do anything", self.error('layer("lime")\nn = 2\nn'))

    def test_a_whole_ticket_or_list_where_one_word_belongs(self):
        order = {"flavour": "lime", "toppings": ["star", "fish"]}
        self.assertIn('layer(order["flavour"])', self.error("layer(order)", order))
        self.assertIn("loop over the list",
                      self.error('layer("lime")\ntopping(order["toppings"])', order))

    def test_recipes_that_are_never_called(self):
        self.assertIn("choco_bomb()", self.error('def choco_bomb():\n    layer("lime")'))
        # A def that isn't used is fine if the cake gets baked anyway.
        self.ok('def spare():\n    layer("lime")\nlayer("lemon")')

    def test_locked_toppings_say_how_to_unlock_them(self):
        message = self.error('layer("lime")\ntopping("unicorn")', unlocked=set())
        self.assertIn("unlocks at 15 stars", message)
        self.ok('layer("lime")\ntopping("unicorn")\nfrosting("galaxy")')

    def test_commands_arrive_chapter_by_chapter(self):
        out = cake.bake('layer("lime")\ncandle()', None, level("1a")["commands"])
        self.assertIn("Chapter 2", out["error"])

    def test_hex_colours(self):
        out = self.ok('layer("#ABC")\nfrosting("#ff88cc")')
        self.assertEqual(out["cake"][0]["layers"], ["#aabbcc"])

    def test_cake_limits(self):
        self.assertIn("tall as the oven", self.error('for i in range(11):\n    layer("lime")'))
        self.assertIn("too long to fit", self.error('layer("lime")\nwrite("x" * 41)'))
        self.assertIn("120 candles", self.error('layer("lime")\nfor i in range(121):\n    candle()'))

    def test_it_stays_safe(self):
        self.assertIn("import", self.error("import os"))
        self.assertIn("methods", self.error('print("".__class__)'))
        self.assertIn("isn't something text can do", self.error('"x".format()'))
        self.assertIn("ran too long", self.error("while True:\n    pass"))
        self.assertIn("called itself", self.error("def f():\n    f()\nf()"))
        self.assertIn("isn't part of Cake Shop", self.error("x = [i for i in range(3)]"))
        self.assertIn("isn't part of Cake Shop", self.error("try:\n    pass\nexcept:\n    pass"))

    def test_lists_as_dictionary_keys_are_a_friendly_error(self):
        self.assertIn('order["name"]', self.error('print(order[["name"]])', {"name": "x"}))
        self.assertIn("in order", self.error('print([1] in order)', {"name": "x"}))

    def test_lists_inside_lists_print_short_and_compare_cheaply(self):
        out = self.ok("a = [1]\nfor i in range(60):\n    a = [a, a]\nprint(a)")
        self.assertLessEqual(len(out["prints"][0]["text"]), cake.MAX_TEXT)
        self.assertIn("too big", self.error("a = [1]\nb = [1]\nfor i in range(40):\n"
                                            "    a = [a, a]\n    b = [b, b]\nprint(a == b)"))

    def test_random_is_the_same_for_the_same_seed(self):
        code = 'layer(choice(["lime", "lemon", "grape"]))\nfor i in range(randint(1, 9)):\n    candle()'
        a = cake.bake(code, seed=5)
        self.assertEqual(a["cake"], cake.bake(code, seed=5)["cake"])

    def test_writing_in_colour(self):
        out = self.ok('layer("lime")\nwrite("Boo!", "orange")')
        self.assertEqual((out["cake"][0]["text"], out["cake"][0]["text_colour"]), ("Boo!", "orange"))
        self.assertEqual(out["steps"][-1], {"do": "write", "arg": "Boo!", "colour": "orange"})
        self.assertIn("colour", self.error('layer("lime")\nwrite("Boo!", "vanilla")'))

    def test_tiers(self):
        out = self.ok('layer("lime")\ntier()\nlayer("lemon")\nwrite("Top")')
        self.assertEqual([t["layers"] for t in out["cake"]], [["lime"], ["lemon"]])
        self.assertEqual(out["cake"][1]["text"], "Top")


class Classroom(unittest.TestCase):
    """The whole flow over HTTP, on a real server with its own save file."""

    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.saved = dict(server.players), server.STATE_FILE, dict(server.cake_class)
        server.players.clear()
        server.STATE_FILE = os.path.join(self.folder.name, "scores.json")
        self.httpd = server.ClassroomServer(("127.0.0.1", 0), server.Handler)
        threading.Thread(target=self.httpd.serve_forever, daemon=True).start()
        self.base = f"http://127.0.0.1:{self.httpd.server_address[1]}"

    def tearDown(self):
        self.httpd.shutdown()
        self.httpd.server_close()
        server.players.clear()
        server.players.update(self.saved[0])
        server.STATE_FILE = self.saved[1]
        server.cake_class.update(self.saved[2])
        self.folder.cleanup()

    def get(self, path):
        with urlopen(self.base + path) as response:
            return json.loads(response.read())

    def post(self, path, data):
        request = Request(self.base + path, json.dumps(data).encode(),
                          {"Content-Type": "application/json"})
        with urlopen(request) as response:
            return json.loads(response.read())

    def join(self, name="Ada"):
        return self.post("/join", {"name": name})["id"]

    def bake(self, pid, key, code=None):
        return self.post("/cake/run", {"id": pid, "level": key,
                                       "code": code or level(key)["reference"]})

    def test_pages_are_served(self):
        for path in ("/cake", "/cake/teacher", "/cake/show"):
            with urlopen(self.base + path) as response:
                self.assertIn(b"Cake Shop", response.read())

    def test_levels_open_one_at_a_time(self):
        pid = self.join()
        state = self.get(f"/cake/state?id={pid}")
        self.assertEqual(state["current"], "1a")
        self.assertEqual(state["total_stars"], 0)
        self.assertIn("vanilla", state["palette"]["flavours"])
        self.assertIn("error", self.get(f"/cake/level?id={pid}&level=1b"))
        self.assertIn("error", self.bake(pid, "1b"))
        view = self.get(f"/cake/level?id={pid}&level=1a")
        self.assertEqual(view["customers"][0]["checklist"],
                         ["2 chocolate layers", "white frosting"])
        self.assertEqual(view["hints"], [])
        out = self.bake(pid, "1a")
        self.assertEqual(out["rewards"]["stars"], [True, True, True])
        self.assertEqual(out["rewards"]["new_stars"], 3)
        self.assertTrue(out["rewards"]["first"])
        self.assertEqual(out["state"]["current"], "1b")
        self.assertIn("First Customer", [b["name"] for b in out["rewards"]["badges"]])
        self.assertIn("board", [u["key"] for u in out["rewards"]["unlocked"]])
        # Stars add up across bakes and never go away.
        again = self.bake(pid, "1a", 'layer("chocolate")')
        self.assertEqual(again["rewards"]["best"], [True, True, True])
        self.assertEqual(again["rewards"]["stars"], [False, False, False])

    def test_rush_levels_show_the_tickets(self):
        pid = self.join()
        self.post("/cake/teacher", {"key": server.ADMIN_KEY, "action": "unlock",
                                    "id": pid, "level": "3a"})
        view = self.get(f"/cake/level?id={pid}&level=3a")
        self.assertEqual(len(view["customers"]), 3)
        self.assertEqual(view["customers"][0]["ticket"], {"name": "Sam", "flavour": "lemon"})
        out = self.bake(pid, "3a", 'layer("lemon")\nlayer("lemon")\nfrosting("white")')
        self.assertEqual([r["happy"] for r in out["runs"]], [True, False, False])
        self.assertIn("blueberry", out["runs"][1]["reply"])

    def test_bake_off_has_new_customers_every_bake(self):
        pid = self.join()
        self.post("/cake/teacher", {"key": server.ADMIN_KEY, "action": "unlock",
                                    "id": pid, "level": "7"})
        a = self.bake(pid, "7")
        b = self.bake(pid, "7")
        self.assertEqual(a["rewards"]["stars"], [True, True, True])
        self.assertNotEqual([r["ticket"] for r in a["runs"]], [r["ticket"] for r in b["runs"]])

    def test_hints_open_one_at_a_time(self):
        pid = self.join()
        self.assertEqual(len(self.post("/cake/hint", {"id": pid, "level": "1a"})["hints"]), 1)
        self.assertEqual(len(self.post("/cake/hint", {"id": pid, "level": "1a"})["hints"]), 2)
        self.assertEqual(len(self.get(f"/cake/level?id={pid}&level=1a")["hints"]), 2)

    def test_locked_toppings_unlock_with_stars(self):
        pid = self.join()
        code = 'layer("lime")\ntopping("butterfly")'
        self.assertIn("unlocks at 2 stars", self.post("/cake/studio", {"id": pid, "code": code})["error"])
        self.bake(pid, "1a")
        self.assertIsNone(self.post("/cake/studio", {"id": pid, "code": code})["error"])

    def test_shop_window_hearts_and_teacher(self):
        ada, bo = self.join("Ada"), self.join("Bo")
        self.post("/cake/shop", {"id": ada, "name": "  Ada's   Cakes  "})
        studio = self.post("/cake/studio", {"id": ada, "new_seed": True,
                                            "code": cake.STUDIO_STARTER})
        self.assertIsNone(studio["error"])
        self.assertIn("error", self.post("/cake/window", {"id": ada, "code": cake.STUDIO_STARTER,
                                                         "seed": studio["seed"], "title": ""}))
        put = self.post("/cake/window", {"id": ada, "code": cake.STUDIO_STARTER,
                                         "seed": studio["seed"], "title": "Pink Dream"})
        self.assertTrue(put["ok"])
        window = self.get(f"/cake/window?id={bo}")
        mine = window["cakes"][0]
        self.assertEqual((mine["title"], mine["shop"], mine["mine"]),
                         ("Pink Dream", "Ada's Cakes", False))
        # The same seed bakes the same cake the student saw.
        self.assertEqual(mine["cake"], studio["cake"])
        self.assertNotIn(ada, json.dumps(window))
        heart = self.post("/cake/heart", {"id": bo, "owner": mine["owner"]})
        self.assertEqual((heart["hearts"], heart["hearted"]), (1, True))
        self.assertIn("error", self.post("/cake/heart", {"id": ada, "owner": mine["owner"]}))
        self.assertEqual(self.post("/cake/heart", {"id": bo, "owner": mine["owner"]})["hearts"], 0)
        # The teacher can hide a cake from the window, and set a theme.
        self.assertIn("error", self.post("/cake/teacher", {"key": "nope", "action": "hide",
                                                           "owner": mine["owner"]}))
        self.post("/cake/teacher", {"key": server.ADMIN_KEY, "action": "hide",
                                    "owner": mine["owner"]})
        self.post("/cake/teacher", {"key": server.ADMIN_KEY, "action": "theme",
                                    "theme": "Spooky 🎃"})
        window = self.get(f"/cake/window?id={bo}")
        self.assertEqual((window["cakes"], window["theme"]), ([], "Spooky 🎃"))
        self.assertEqual(json.load(open(server.STATE_FILE))["cake_class"]["theme"], "Spooky 🎃")
        self.assertEqual(len(self.get(f"/cake/window?key={server.ADMIN_KEY}")["cakes"]), 1)

    def test_opening_levels_for_everyone_includes_newcomers(self):
        self.post("/cake/teacher", {"key": server.ADMIN_KEY, "action": "unlock",
                                    "everyone": True, "level": "4a"})
        pid = self.join("Late")
        self.assertEqual(self.get(f"/cake/state?id={pid}")["current"], "4a")
        self.assertNotIn("error", self.get(f"/cake/level?id={pid}&level=4a"))
        self.assertIn("error", self.get(f"/cake/level?id={pid}&level=4b"))

    def test_teacher_overview(self):
        pid = self.join()
        self.bake(pid, "1a", "layer(chocolate)")
        overview = self.get("/cake/overview")
        row = overview["students"][0]
        self.assertEqual((row["level"], row["misses"]), ("1a", 1))
        self.assertIn("Put quotes", row["last_error"])
        self.assertTrue(overview["address"].endswith("/cake"))

    def test_teacher_can_peek_at_code(self):
        pid = self.join()
        self.bake(pid, "1a", 'layer("chocolate")')
        self.assertIn("error", self.get(f"/cake/peek?id={pid}&key=nope"))
        peek = self.get(f"/cake/peek?id={pid}&key={server.ADMIN_KEY}")
        self.assertEqual((peek["level"], peek["code"]), ("1a", 'layer("chocolate")'))

    def test_look_only_takes_unlocked_things(self):
        pid = self.join()
        self.assertEqual(self.post("/cake/look", {"id": pid, "stand": "gold"})["look"]["stand"], "plate")
        self.bake(pid, "1a")
        self.assertEqual(self.post("/cake/look", {"id": pid, "stand": "board"})["look"]["stand"], "board")


if __name__ == "__main__":
    unittest.main()
