import json
import os
import shutil
import subprocess
import tempfile
import threading
import time
import unittest
from urllib.request import Request, urlopen
from unittest.mock import patch

import pixel
import server


def drawing(key="abc", size=16, frames=None, **extra):
    return dict({"key": key, "title": "Luna", "size": size, "speed": 6,
                 "palette": ["#000000", "#ffffff"],
                 "frames": frames or ["." * (size * size)]}, **extra)


class CheckingDrawings(unittest.TestCase):
    """What the page sends ends up in the save file, so it's checked first."""

    def test_a_good_drawing_comes_through_whole(self):
        art = drawing(frames=["01" * 128, "." * 256])
        self.assertEqual(pixel.clean_drawing(art), dict(art, names=["", ""], marks="", guide=""))

    def test_bad_drawings_are_turned_away(self):
        bad = [
            None, "drawing", {},
            drawing(key="NOT A KEY"), drawing(key=""), drawing(key=7),
            drawing(size=17), drawing(speed=99),
            drawing(palette=[]), drawing(palette=["red"]), drawing(palette=["#fff"]),
            drawing(palette=["#000000"] * (pixel.MAX_COLOURS + 1)),
            drawing(frames=["." * 255]),            # one square short
            drawing(frames=["2" * 256]),            # a colour past the palette
            drawing(frames=["<" * 256]),
            drawing(frames=[7]),
            drawing(frames=["." * 256] * (pixel.MAX_FRAMES + 1)),
        ]
        for art in bad:
            with self.subTest(art=art):
                self.assertIsNone(pixel.clean_drawing(art))
        self.assertIsNone(pixel.clean_drawing(dict(drawing(), frames=[])))

    def test_extra_fields_are_dropped_and_long_titles_cut(self):
        out = pixel.clean_drawing(drawing(title="x" * 99, sneaky="yes"))
        self.assertEqual(len(out["title"]), pixel.TITLE_MAX)
        self.assertNotIn("sneaky", out)

    def test_a_save_updates_in_place_and_puts_the_newest_first(self):
        drawings = []
        pixel.save_drawing(drawings, drawing("a"))
        pixel.save_drawing(drawings, drawing("b"))
        pixel.save_drawing(drawings, drawing("a", title="Renamed"))
        self.assertEqual([d["key"] for d in drawings], ["a", "b"])
        self.assertEqual(drawings[0]["title"], "Renamed")

    def test_a_full_shelf_stops_new_drawings_but_not_old_ones(self):
        drawings = []
        for n in range(pixel.MAX_DRAWINGS):
            self.assertIsNone(pixel.save_drawing(drawings, drawing(f"k{n}")))
        self.assertEqual(pixel.save_drawing(drawings, drawing("new")), "full")
        self.assertIsNone(pixel.save_drawing(drawings, drawing("k3", title="Fine")))
        self.assertEqual(len(drawings), pixel.MAX_DRAWINGS)


class StudioOverHttp(unittest.TestCase):
    """The whole flow on a real server with its own save file."""

    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.saved = dict(server.players), server.STATE_FILE
        server.pixel_class["check"] = False       # the checking has its own tests
        server.pixel_class.pop("story", None)
        server.players.clear()
        server.STATE_FILE = os.path.join(self.folder.name, "scores.json")
        self.httpd = server.ClassroomServer(("127.0.0.1", 0), server.Handler)
        threading.Thread(target=self.httpd.serve_forever, daemon=True).start()
        self.base = f"http://127.0.0.1:{self.httpd.server_address[1]}"

    def tearDown(self):
        # A write still waiting must not land on the real save file after this.
        if server.pixel_write_timer[0]:
            server.pixel_write_timer[0].cancel()
            server.pixel_write_timer[0] = None
        self.httpd.shutdown()
        self.httpd.server_close()
        server.pixel_class.pop("check", None)
        server.players.clear()
        server.players.update(self.saved[0])
        server.STATE_FILE = self.saved[1]
        self.folder.cleanup()

    def post(self, path, data):
        request = Request(self.base + path, json.dumps(data).encode(),
                          {"Content-Type": "application/json"})
        with urlopen(request) as response:
            return json.load(response)

    def get(self, path):
        with urlopen(self.base + path) as response:
            return json.load(response)

    def test_pages_are_served(self):
        for path in ("/pixel", "/pixel/art.js", "/pixel/stage.js", "/pixel/studio.js", "/pixel/page.js",
                     "/pixel/teacher", "/pixel/show"):
            with self.subTest(path=path), urlopen(self.base + path) as response:
                self.assertEqual(response.status, 200)

    def test_a_drawing_saves_comes_back_and_deletes(self):
        me = self.post("/join", {"name": "Mia"})["id"]
        self.assertEqual(self.get(f"/pixel/state?id={me}")["drawings"], [])
        self.assertTrue(self.post("/pixel/save", {"id": me, "drawing": drawing()})["ok"])
        state = self.get(f"/pixel/state?id={me}")
        self.assertEqual(state["you"], {"name": "Mia"})
        self.assertEqual(state["drawings"], [dict(drawing(), names=[""], marks="", guide="")])
        self.post("/pixel/delete", {"id": me, "key": "abc"})
        self.assertEqual(self.get(f"/pixel/state?id={me}")["drawings"], [])

    def test_a_bad_drawing_or_a_stranger_is_turned_away(self):
        me = self.post("/join", {"name": "Mia"})["id"]
        self.assertEqual(self.post("/pixel/save", {"id": me, "drawing": {}}), {"error": "bad"})
        self.assertEqual(self.post("/pixel/save", {"id": "nobody", "drawing": drawing()}), {"error": "join"})
        self.assertEqual(self.get("/pixel/state?id=nobody"), {"you": None})

    def join(self, name="Mia"):
        return self.post("/join", {"name": name})["id"]

    def run_mission(self, me, key, code=None):
        code = pixel.LEVEL_BY_KEY[key]["reference"] if code is None else code
        return self.post("/pixel/run", {"id": me, "level": key, "code": code})

    def test_stars_are_kept_and_open_the_next_mission(self):
        me = self.join()
        state = self.get(f"/pixel/state?id={me}")
        self.assertEqual(state["current"], "a1")
        self.assertIn("error", self.get(f"/pixel/level?id={me}&level=a2"))
        self.assertIn("🔒", self.run_mission(me, "a2")["error"])
        out = self.run_mission(me, "a1")
        self.assertEqual(out["stars"], [True, True, True])
        self.assertEqual(out["rewards"]["gained"], 3)
        self.assertEqual(out["state"]["current"], "a2")
        self.assertEqual(self.get(f"/pixel/level?id={me}&level=a2")["key"], "a2")
        # A worse run never takes stars back.
        out = self.run_mission(me, "a1", 'say("Hi")')
        self.assertEqual(out["rewards"]["gained"], 0)
        self.assertEqual(out["state"]["stars"], 3)

    def test_a_mission_brings_its_step_by_step_guide(self):
        me = self.join()
        level = self.get(f"/pixel/level?id={me}&level=a1")
        self.assertEqual(level["coach"][0][0], 'say("Hello")')
        self.assertFalse(level["build"])

    def test_badges_come_once_and_reach_the_class_feed(self):
        me = self.join()
        first = self.run_mission(me, "a1")["rewards"]["badges"]
        self.assertEqual([b["name"] for b in first], ["Curtain Up"])
        self.assertEqual(self.run_mission(me, "a1")["rewards"]["badges"], [])
        feed = [f["text"] for f in self.get("/pixel/overview")["feed"]]
        self.assertTrue(any("Curtain Up" in text for text in feed))

    def test_your_own_drawing_is_your_pal(self):
        me = self.join()
        self.assertEqual(self.get(f"/pixel/state?id={me}")["pal"], "pip")
        self.post("/pixel/save", {"id": me, "drawing": drawing("mine", frames=["0" + "." * 255], names=["happy"])})
        self.assertEqual(self.get(f"/pixel/state?id={me}")["pal"], "mine")
        self.post("/pixel/pal", {"id": me, "key": "pip"})
        self.assertEqual(self.get(f"/pixel/state?id={me}")["pal"], "pip")
        self.assertIn("error", self.post("/pixel/pal", {"id": me, "key": "someone-elses"}))

    def test_the_teacher_needs_the_key_and_can_open_missions(self):
        mia = self.join()
        self.get(f"/pixel/state?id={mia}")
        self.assertIn("error", self.post("/pixel/teacher", {"key": "nope", "action": "overview"}))
        key = server.ADMIN_KEY
        over = self.post("/pixel/teacher", {"key": key, "action": "overview"})
        self.assertEqual(over["students"][0]["name"], "Mia")
        self.post("/pixel/teacher", {"key": key, "action": "open", "level": "b1"})
        self.assertEqual(self.get(f"/pixel/level?id={mia}&level=b1")["key"], "b1")
        server.pixel_class["open"] = 0

    def test_the_open_overview_has_no_student_rows(self):
        self.join()
        self.assertEqual(set(self.get("/pixel/overview")), {"feed", "address", "room_open"})

    def test_saves_reach_the_file_and_a_burst_shares_one_write(self):
        me = self.post("/join", {"name": "Mia"})["id"]
        self.post("/pixel/save", {"id": me, "drawing": drawing("a")})
        timer = server.pixel_write_timer[0]
        self.post("/pixel/save", {"id": me, "drawing": drawing("b")})
        self.assertIs(server.pixel_write_timer[0], timer)
        timer.join(5)
        with open(server.STATE_FILE) as f:
            kept = json.load(f)["players"][me]["pixel"]["drawings"]
        self.assertEqual([d["key"] for d in kept], ["b", "a"])


# Every mission up to My Move. More missions come after it.
BEFORE_MOVE = tuple(pixel.LEVEL_ORDER[:pixel.LEVEL_ORDER.index("m1")])


def run(key, code, seed=0):
    return pixel.run_level(pixel.LEVEL_BY_KEY[key], code, pixel.PIP, seed=seed)


class Missions(unittest.TestCase):
    """Every claim a mission makes is a test, as in Strange Planet."""

    def test_every_reference_earns_all_three_stars(self):
        for lv in pixel.LEVELS:
            for seed in (0, 100, 2000):
                with self.subTest(level=lv["key"], seed=seed):
                    out = run(lv["key"], lv["reference"], seed)
                    self.assertIsNone(out["error"])
                    self.assertEqual(out["stars"], [True, True, True], out["reply"])

    def test_the_last_hint_does_the_job(self):
        for lv in pixel.LEVELS:
            with self.subTest(level=lv["key"]):
                out = run(lv["key"], lv["hints"][-1])
                self.assertIsNone(out["error"])
                self.assertTrue(out["stars"][0], out["reply"])

    def test_an_empty_program_earns_nothing(self):
        for lv in pixel.LEVELS:
            with self.subTest(level=lv["key"]):
                self.assertEqual(run(lv["key"], "")["stars"], [False, False, False])

    def test_an_error_earns_nothing(self):
        for lv in pixel.LEVELS:
            with self.subTest(level=lv["key"]):
                out = run(lv["key"], lv["reference"] + "\nnonsense()")
                self.assertIsNotNone(out["error"])
                self.assertEqual(out["stars"], [False, False, False])

    def test_the_step_by_step_guide_is_the_working_answer(self):
        for lv in pixel.LEVELS:
            with self.subTest(lv["key"]):
                self.assertEqual("\n".join(line for line, why in lv["coach"]), lv["reference"])
                self.assertTrue(all(why for line, why in lv["coach"]))

    def test_every_key_in_the_guide_can_be_explained(self):
        with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "pixel_page.js"), encoding="utf-8") as file:
            page = file.read()
        words = page[page.index("const KEY_HELP"):page.index("function coachTarget")]
        for lv in pixel.LEVELS:
            for char in {c for line, why in lv["coach"] for c in line.strip() if not c.isalnum()}:
                with self.subTest(lv["key"], char=char):
                    self.assertTrue(json.dumps(char) in words or f"'{char}'" in words)

    def test_every_mission_has_three_goals_and_at_least_two_hints(self):
        for lv in pixel.LEVELS:
            with self.subTest(level=lv["key"]):
                self.assertEqual(len(lv["goals"]), 3)
                self.assertGreaterEqual(len(lv["hints"]), 2)
                self.assertIsNotNone(lv["goals"][0][2], "the first goal needs words for when it's missed")

    def test_a_mission_only_uses_what_it_has_opened(self):
        # Any command beyond what's open would stop the reference, which the
        # first test would catch, but a stray chapter order is easier read here.
        seen = set()
        for lv in pixel.LEVELS:
            seen |= set(lv["adds"])
            self.assertEqual(set(pixel.commands_for(lv["key"])), seen)

    def test_commands_open_in_order(self):
        out = run("a1", "jump()")
        self.assertIn("isn't open yet", out["error"])

class TheShow(unittest.TestCase):
    """What the interpreter does with a program, and what it says when it can't."""

    def steps(self, code, **kw):
        out = pixel.perform(code, **kw)
        self.assertIsNone(out["error"])
        return out["steps"]

    def error(self, code, **kw):
        out = pixel.perform(code, **kw)
        self.assertIsNotNone(out["error"], code)
        return out["error"]

    def test_commands_become_steps_with_their_lines(self):
        steps = self.steps('say("Hi")\nright(3)\nleft(1)\njump()')
        self.assertEqual([s["do"] for s in steps], ["say", "walk", "walk", "jump"])
        self.assertEqual([s["line"] for s in steps], [1, 2, 3, 4])
        self.assertEqual(steps[1]["to"], 5)
        self.assertEqual(steps[2]["to"], 4)

    def test_walking_stops_at_the_edges(self):
        self.assertEqual(self.steps("right(99)")[0]["to"], 10)
        self.assertEqual(self.steps("left(99)")[0]["to"], 0)

    def test_pose_finds_names_and_numbers(self):
        self.assertEqual(self.steps('pose("sad")')[0]["frame"], 2)
        self.assertEqual(self.steps("pose(4)")[0]["frame"], 3)

    def test_a_missing_pose_says_how_to_make_it(self):
        text = self.error('pose("walk")')
        self.assertIn("+ Copy frame", text)
        self.assertIn('"happy"', text)

    def test_a_click_replays_with_memory(self):
        code = "def on_click():\n    say(clicks())"
        out = pixel.perform(code, events=["click", "click", "click"])
        self.assertEqual([s["text"] for s in out["after"] if s["do"] == "say"], ["3"])
        self.assertEqual(out["events"], ["click"])

    def test_variables_last_between_clicks(self):
        code = "n = 0\ndef on_click():\n    global n\n    n = n + 5\n    say(n)"
        out = pixel.perform(code, events=["click", "click"])
        self.assertEqual([s["text"] for s in out["after"] if s["do"] == "say"], ["10"])

    def test_random_replays_the_same_with_the_same_seed(self):
        code = 'def on_click():\n    say(randint(0, 1000000))'
        one = pixel.perform(code, events=["click", "click"], seed=5)["after"]
        two = pixel.perform(code, events=["click", "click"], seed=5)["after"]
        self.assertEqual(one, two)

    def test_keys_reach_on_key(self):
        code = 'def on_key(key):\n    say(key)'
        out = pixel.perform(code, events=["key:left"])
        self.assertEqual(out["after"][-1]["text"], "left")

    def test_bad_events_are_ignored(self):
        code = 'def on_key(key):\n    say(key)'
        self.assertEqual(pixel.perform(code, events=["key:evil", "hack", 7])["steps"], [])

    def test_a_pet_gets_hungry_and_sleepy(self):
        code = "def on_feed():\n    say(hungry())\n    eat()"
        out = pixel.perform(code, events=["feed", "feed"])
        self.assertEqual([s["text"] for s in out["steps"] if s["do"] == "say"], ["True", "False"])

    def test_an_endless_loop_stops_and_keeps_what_ran(self):
        out = pixel.perform('jump()\nwhile True:\n    n = 1')
        self.assertIn("round and round", out["error"])
        self.assertEqual(out["line"], 2)
        self.assertEqual(len(out["steps"]), 1)

    def test_too_many_moves_stop_politely(self):
        self.assertIn("very long show", self.error("for i in range(9999):\n    jump()"))

    def test_unsafe_python_is_turned_away(self):
        for code in ('import os', 'open("x")', '().__class__', 'exec("1")', '__import__("os")',
                     'class A:\n    pass', 'x = [i for i in range(3)]', 'lambda: 1'):
            with self.subTest(code=code):
                self.assertIsNotNone(pixel.perform(code)["error"])

    def test_errors_a_beginner_makes_are_in_plain_words(self):
        cases = {
            "say(Hello)": 'Words need quotes',
            "Say('hi')": "Did you mean",
            "jump": "add brackets",
            "jump(3)": "use a loop",
            "right three": "Commands have brackets",
            'say "hi"': "Words go inside brackets",
            'say("hi)': 'at both ends',
            "for i in range(3)\n    jump()": "very end of this line",
            "for i in range(3):\njump()": "pushed in",
            "  jump()": "too far to the right",
            "jump(": "closes it",
            "right(1) left(1)": "Only one command",
            'right("3")': "whole number",
            'print("hi")': "say()",
            "walk(3)": "right(3)",
            'feel("hungry")': "The feelings are",
            'look("sideways")': "The ways are",
            "wave(2)": "use a loop" if False else "brackets",
            'pose()': "name of a frame",
            'def on_clik():\n    jump()': "on_click",
            'def jump():\n    spin()': "already a command",
            "def on_key():\n    jump()": "name in its brackets",
            'say("a" + 3)': "f in front",
            'friend_say("Hi")': "no friend",
            'sound("moo")': '"ding"',
        }
        for code, words in cases.items():
            with self.subTest(code=code):
                events = ["key:left"] if "on_key" in code else ()
                self.assertIn(words, self.error(code, events=events))

    def test_no_message_mentions_another_game(self):
        for code in ("move 3", "turn_left()", "repeat 3", "north(2)", "if x() == 1 jump() else spin()",
                     "x = = 2", "1 +", "def", "while", "if"):
            with self.subTest(code=code):
                text = self.error(code).lower()
                for word in ("rover", "cake", "kitchen", "steer", "compass", "light cycles"):
                    self.assertNotIn(word, text)

    def test_syntax_errors_know_their_line(self):
        out = pixel.perform('jump()\njump()\nsay("hi)')
        self.assertEqual(out["line"], 3)
        self.assertTrue(out["error"].startswith("Line 3: "))
        self.assertFalse(out["error"].startswith("Line 3: Line"))


@unittest.skipUnless(shutil.which("node"), "needs node")
class TheRig(unittest.TestCase):
    """pixel_rig.js finds the parts of a drawing and moves them. Node runs it."""

    def js(self, code):
        folder = os.path.dirname(os.path.abspath(__file__))
        need = "".join(f"const {name} = require({json.dumps(os.path.join(folder, file))});"
                       for name, file in (("A", "pixel_art.js"), ("R", "pixel_rig.js"), ("G", "pixel_gallery.js")))
        script = need + f"process.stdout.write(JSON.stringify((() => {{ {code} }})()))"
        return json.loads(subprocess.check_output(["node", "-e", script], timeout=120))

    def parts(self, rows, marks=""):
        """Which parts the rig finds in a drawing made of letters."""
        size = len(rows)
        return self.js(f"""
            const f = Array.from({json.dumps("".join(rows))}, c => c === "." ? -1 : c === "k" ? 0 : c === "g" ? 22 : 4);
            const rig = R.build(f, {size}, A.PALETTE, {json.dumps(marks)});
            const count = kind => rig.limbs.filter(l => l.kind === kind).length;
            return {{eyes: rig.eyes.length, mouth: !!rig.mouth, arm: count("arm"), leg: count("leg"),
                     ear: count("ear"), tail: count("tail"), wing: count("wing")}};""")

    def test_every_gallery_pal_is_square_and_has_eyes(self):
        out = self.js("""return G.names.map(name => {
            const f = G.pictures[name], rig = R.build(f, 16, A.PALETTE);
            return [name, f.length, f.every(n => n !== undefined), rig.eyes.length > 0];
        })""")
        self.assertGreaterEqual(len(out), 18)
        for name, length, known, eyes in out:
            with self.subTest(pal=name):
                self.assertEqual(length, 256)
                self.assertTrue(known)
                self.assertTrue(eyes)

    def test_every_gallery_pal_has_numbers_to_colour(self):
        out = self.js("""return G.names.map(name => {
            const f = G.pictures[name], base = G.outlined(f);
            return [name, new Set(f.filter((n, i) => n !== base[i])).size];
        })""")
        for name, colours in out:
            with self.subTest(pal=name):
                self.assertGreaterEqual(colours, 2)

    def test_the_gallery_pals_are_rigged_as_what_they_are(self):
        found = self.js("""const out = {};
            for (const name of G.names) out[name] = R.build(G.pictures[name], 16, A.PALETTE).limbs.map(l => l.kind);
            return out""")
        self.assertEqual(found["Puppy"].count("ear"), 2)       # floppy ears aren't arms
        self.assertEqual(found["Puppy"].count("arm"), 2)
        self.assertEqual(found["Bunny"].count("ear"), 2)
        self.assertEqual(found["Fairy"].count("wing"), 2)      # wings aren't ears
        self.assertEqual(found["Dino"].count("tail"), 1)       # a tail isn't an arm
        self.assertEqual(found["Robot"].count("arm"), 2)       # joined on at a corner
        self.assertGreaterEqual(found["Butterfly"].count("wing"), 2)
        self.assertNotIn("arm", found["Mushroom"])             # its spots aren't eyes, so its cap isn't arms

    def test_a_shape_with_no_face_has_no_eyes(self):
        rows = ["." * 16] * 4 + ["....gggggggg...."] * 8 + ["." * 16] * 4
        self.assertEqual(self.parts(rows)["eyes"], 0)

    def test_two_dots_on_a_blob_are_eyes(self):
        rows = ["." * 16] * 3 + ["..gggggggggggg.."] * 3 + ["..ggkggggggkgg.."] * 2 + ["..gggggggggggg.."] * 5 + ["." * 16] * 3
        found = self.parts(rows)
        self.assertEqual(found["eyes"], 2)
        self.assertEqual(found["arm"] + found["leg"], 0)

    def test_an_outline_with_nothing_inside_still_has_a_face(self):
        rows = ["." * 16, "...kkkkkkkkkk...", "...k........k...", "...k..k..k..k...", "...k..k..k..k...",
                "...k........k...", "...k........k...", "...kkkkkkkkkk...", "....k......k....", "....k......k....",
                "...kk......kk...", "." * 16, "." * 16, "." * 16, "." * 16, "." * 16]
        self.assertEqual(self.parts(rows)["eyes"], 2)

    def test_what_a_student_paints_beats_the_guess(self):
        rows = ["." * 16] * 3 + ["..gggggggggggg.."] * 3 + ["..ggkggggggkgg.."] * 2 + ["..gggggggggggg.."] * 5 + ["." * 16] * 3
        marks = list("." * 256)
        for at in (8 * 16 + 2, 8 * 16 + 3, 9 * 16 + 2, 9 * 16 + 3):
            marks[at] = "a"
        self.assertEqual(self.parts(rows, "".join(marks))["arm"], 1)
        marks = list("." * 256)
        marks[6 * 16 + 4] = marks[7 * 16 + 4] = "b"
        self.assertEqual(self.parts(rows, "".join(marks))["eyes"], 2)    # Body doesn't rub out a face

    def test_all_the_moods_and_moves_change_the_picture(self):
        out = self.js("""
            const f = G.pictures.Kitty, rig = R.build(f, 16, A.PALETTE), still = String(R.render(rig, f, {}));
            const same = [];
            for (const mood of Object.keys(R.MOODS)) if (String(R.render(rig, f, R.MOODS[mood])) === still) same.push(mood);
            for (const move of R.MOVES) if (move !== "idle" && String(R.render(rig, f, R.pose(move, .3, rig))) === still) same.push(move);
            return same""")
        self.assertEqual(out, [])

    def test_blinking_only_touches_the_eyes(self):
        out = self.js("""
            const f = G.pictures.Kitty, rig = R.build(f, 16, A.PALETTE);
            const open = R.render(rig, f, {}), shut = R.render(rig, f, {eyes: "shut"});
            const rows = new Set();
            open.forEach((n, i) => { if (n !== shut[i]) rows.add(Math.floor(i / rig.wide) - rig.pad); });
            return [[...rows], rig.eyes[0].top, rig.eyes[0].bottom]""")
        self.assertTrue(out[0])
        self.assertTrue(all(out[1] <= row <= out[2] for row in out[0]))

    def test_a_still_pal_is_exactly_the_drawing(self):
        out = self.js("""return G.names.filter(name => {
            const f = G.pictures[name], rig = R.build(f, 16, A.PALETTE), out = R.render(rig, f, {});
            for (let y = 0; y < 16; y++) for (let x = 0; x < 16; x++) {
                if (out[(y + rig.pad) * rig.wide + x + rig.pad] !== f[y * 16 + x]) return true;
            }
            return false;
        })""")
        self.assertEqual(out, [])

    def test_a_face_keeps_its_place_on_big_drawings_too(self):
        out = self.js("""
            const f16 = G.pictures.Kitty, f = new Array(48 * 48);
            for (let y = 0; y < 48; y++) for (let x = 0; x < 48; x++) f[y * 48 + x] = f16[Math.floor(y / 3) * 16 + Math.floor(x / 3)];
            const rig = R.build(f, 48, A.PALETTE);
            return [rig.eyes.length, !!rig.mouth, rig.limbs.filter(l => l.kind === "ear").length, rig.legs.length]""")
        self.assertEqual(out, [2, True, 2, 2])

    def test_nothing_a_child_draws_can_break_it(self):
        out = self.js("""
            let s = 12345;
            const rand = n => (s = (s * 1103515245 + 12345) & 0x7fffffff) % n;
            const faces = [...Object.values(R.MOODS)];
            let bad = [], drawings = 0;
            const tryIt = (f, size, marks = "", what = "") => {
                drawings++;
                try {
                    const rig = R.build(f, size, A.PALETTE, marks);
                    for (const move of R.MOVES) for (const t of [0, .17, .5, .99]) {
                        const out = R.render(rig, f, R.tidy(R.pose(move, t, rig)));
                        if (out.length !== rig.wide * rig.wide || out.some(n => n >= A.PALETTE.length || n !== n)) throw new Error("bad picture");
                    }
                    for (const face of faces) R.render(rig, f, face);
                } catch (e) { bad.push(what + " " + size + ": " + e.message); }
            };
            for (const size of [16, 24, 32, 48]) {
                const n = size * size, all = c => new Array(n).fill(c);
                tryIt(all(-1), size, "", "empty");
                tryIt(all(0), size, "", "solid");
                tryIt(all(0).map((c, i) => (i + Math.floor(i / size)) % 2 ? 4 : c), size, "", "checks");
                tryIt(all(-1).map((c, i) => i === 0 ? 11 : c), size, "", "one corner");
                tryIt(all(-1).map((c, i) => i === n - 1 ? 11 : c), size, "", "other corner");
                tryIt(all(-1).map((c, i) => i < size ? 3 : c), size, "", "top row");
                tryIt(all(-1).map((c, i) => i % size === 0 ? 3 : c), size, "", "left column");
                tryIt(all(5), size, "o".repeat(n), "all eyes");
                tryIt(all(5), size, "m".repeat(n), "all mouth");
                tryIt(all(5), size, "a".repeat(n), "all arm");
                tryIt(all(5), size, "l".repeat(n), "all leg");
                tryIt(all(5), size, "t".repeat(n), "all tail");
                tryIt(all(5), size, "w".repeat(n), "all wing");
                for (let i = 0; i < (size > 24 ? 40 : 120); i++) {
                    const f = all(-1), marks = [], colours = 1 + rand(6), blobs = 1 + rand(8);
                    for (let b = 0; b < blobs; b++) {
                        const x = rand(size), y = rand(size), w = 1 + rand(size), h = 1 + rand(size), c = rand(32);
                        for (let dy = 0; dy < h; dy++) for (let dx = 0; dx < w; dx++) {
                            if (x + dx < size && y + dy < size && rand(10) > i % 4) f[(y + dy) * size + x + dx] = rand(2) ? c : rand(colours);
                        }
                    }
                    for (let m = 0; m < n; m++) marks.push(rand(30) ? "." : ".aletwomb"[rand(9)]);
                    tryIt(f, size, i % 3 ? "" : marks.join(""), "random " + i);
                }
            }
            return {drawings, bad: [...new Set(bad)].slice(0, 12)}""")
        self.assertEqual(out["bad"], [])
        self.assertGreater(out["drawings"], 350)

    def test_finding_the_parts_is_quick_enough_to_do_while_drawing(self):
        ms = self.js("""
            const f = new Array(48 * 48).fill(-1).map((_, i) => i % 7 ? 22 : 0), start = Date.now();
            for (let i = 0; i < 20; i++) R.build(f, 48, A.PALETTE);
            return (Date.now() - start) / 20""")
        self.assertLess(ms, 30)


class TeacherChecksShows(unittest.TestCase):
    """Students can type anything, so by default a show waits for the teacher."""

    setUp, tearDown, post, get = StudioOverHttp.setUp, StudioOverHttp.tearDown, StudioOverHttp.post, StudioOverHttp.get

    def join(self, name):
        return self.post("/join", {"name": name})["id"]

    def teacher(self, **data):
        return self.post("/pixel/teacher", dict(data, key=server.ADMIN_KEY))

    def test_the_new_trophies(self):
        mia = self.join("Mia")
        self.assertEqual(self.post("/pixel/game", {"id": mia, "game": "alive"})["badges"][0]["name"], "It's Alive!")
        self.assertEqual(self.post("/pixel/game", {"id": mia, "game": "alive"})["badges"], [])

    def test_the_teacher_sees_a_picture_of_each_pal_and_the_projector_doesnt(self):
        mia = self.join("Mia")
        art = dict(drawing(), key="ink123", frames=["0" + "." * 255])
        self.post("/pixel/save", {"id": mia, "drawing": art})
        rows = self.teacher(action="overview")["students"]
        self.assertEqual(rows[0]["picture"]["frame"], art["frames"][0])
        self.assertNotIn("0" + "." * 255, json.dumps(self.get("/pixel/overview")))

    def test_a_blank_page_never_goes_on_stage(self):
        mia = self.join("Mia")
        self.post("/pixel/save", {"id": mia, "drawing": drawing()})
        self.assertEqual(self.get(f"/pixel/state?id={mia}")["pal"], "pip")
        art = dict(drawing(), key="ink123", frames=["0" + "." * 255])
        self.post("/pixel/save", {"id": mia, "drawing": art})
        self.assertEqual(self.get(f"/pixel/state?id={mia}")["pal"], "ink123")

class TheStagePlays(unittest.TestCase):
    """The stage's steps, run in node on a pretend canvas. A browser quietly
    forgives a lot, so a step that does nothing is only found by checking."""

    STUB = """
        const folder = process.argv[1];
        const noop = () => {};
        const pen = new Proxy({}, {get: (t, k) => k === "getImageData" ? () => ({data: []}) : k === "measureText" ? () => ({width: 100}) : noop, set: () => true});
        const canvas = () => ({width: 0, height: 0, style: {}, getContext: () => pen});
        global.document = {createElement: canvas};
        global.localStorage = {getItem: () => null, setItem: noop};
        global.matchMedia = () => ({matches: false});
        global.window = {};
        let now = 0;
        Object.defineProperty(global, "performance", {value: {now: () => now}, configurable: true});
        global.requestAnimationFrame = fn => { setImmediate(() => { now += 200; fn(now); }); return 1; };
        global.cancelAnimationFrame = noop;
        global.PixelArt = require(folder + "/pixel_art.js");
        global.PixelRig = require(folder + "/pixel_rig.js");
        const PalStage = require(folder + "/pixel_stage.js");
        const stage = PalStage.create(canvas(), null);
    """

    def js(self, code):
        folder = os.path.dirname(os.path.abspath(__file__))
        script = self.STUB + f"(async () => {{ {code} }})().then(out => process.stdout.write(JSON.stringify(out), () => process.exit(0)), e => {{ console.error(e); process.exit(1); }});"
        return json.loads(subprocess.check_output(["node", "-e", script, folder], timeout=60))

    def test_play_really_shows_every_frame(self):
        out = self.js("""
            const blank = "0" + ".".repeat(255);
            stage.setPal({size: 16, palette: ["#000000"], frames: [blank, blank, blank], names: []});
            stage.fresh();
            const seen = new Set();
            const going = stage.play([{do: "play"}]);
            let finished = false;
            going.then(() => { finished = true; });
            while (!finished) { seen.add(stage.state.frame); await new Promise(r => setImmediate(r)); }
            return [...seen].sort();""")
        self.assertEqual(out, [0, 1, 2])

    def test_every_kind_of_step_runs(self):
        steps = [{"do": "friend", "kind": "cat"}, {"do": "friend", "kind": "bunny"}, {"do": "friend_say", "text": "Hi", "who": "cat"},
                 {"do": "friend_jump", "who": "bunny"}, {"do": "everyone", "move": "dance"}, {"do": "bye", "who": "cat"}, {"do": "bye"},
                 {"do": "walk", "to": 5}, {"do": "jump"}, {"do": "wave"}, {"do": "dance"}, {"do": "cheer"}, {"do": "giggle"},
                 {"do": "look", "way": "left"}, {"do": "feel", "mood": "happy"}, {"do": "spin"}, {"do": "shake"},
                 {"do": "size", "to": 2}, {"do": "hide"}, {"do": "appear"}, {"do": "pose", "frame": 0}, {"do": "play"},
                 {"do": "wait", "beats": 1}, {"do": "say", "text": "Hi"}, {"do": "friend", "kind": "cat"},
                 {"do": "friend_say", "text": "Hi"}, {"do": "friend_jump"}, {"do": "bye"}, {"do": "hearts"}, {"do": "stars"},
                 {"do": "confetti"}, {"do": "rain"}, {"do": "snow"}, {"do": "sound", "name": "ding"}, {"do": "scene", "name": "park"},
                 {"do": "eat"}, {"do": "nap"}, {"do": "snooze"}, {"do": "put", "prop": "star", "at": 3}, {"do": "take", "at": 3},
                 {"do": "point", "score": 1}, {"do": "mark", "at": 2}, {"do": "place", "at": 4}, {"do": "weather", "kind": "sun"},
                 {"do": "event"}]
        out = self.js(f"""
            const blank = "0" + ".".repeat(255);
            stage.setPal({{size: 16, palette: ["#000000"], frames: [blank], names: []}});
            stage.fresh();
            return await stage.play({json.dumps(steps)});""")
        self.assertTrue(out)

class SeveralFriends(unittest.TestCase):
    def run_it(self, code):
        return pixel.perform(code, pixel.PIP)

    def test_three_friends_can_share_the_stage(self):
        out = self.run_it('friend("cat")\nfriend("cat")\nfriend_say("Hi")')
        self.assertEqual([s["do"] for s in out["steps"]], ["friend", "friend_say"])     # no twins
        self.assertEqual(out["steps"][1]["who"], "cat")

    def test_naming_someone_who_isnt_there(self):
        self.assertIn("isn't on stage", self.run_it('friend("cat")\nfriend_say("Ben", "Hi")')["error"])

    def test_everyone(self):
        self.assertEqual(self.run_it('everyone("dance")')["steps"][0]["move"], "dance")
        self.assertIn("The moves are", self.run_it('everyone("sing")')["error"])


class PlayingTogether(unittest.TestCase):
    setUp, tearDown, post, get = StudioOverHttp.setUp, StudioOverHttp.tearDown, StudioOverHttp.post, StudioOverHttp.get

    def open_room(self, words=False):
        server.pixel_room.update(server.room_empty(), open=True, words=words)
        self.addCleanup(lambda: server.pixel_room.update(server.room_empty(), open=True, words=False))

    def join(self, name):
        me = self.post("/join", {"name": name})["id"]
        art = dict(drawing(), key="ink123", frames=["0" + "." * 255])
        self.post("/pixel/save", {"id": me, "drawing": art})
        server.pixel_entry(server.players[me])["solved"].update({k: [True] * 3 for k in ("a1", "a2", "a3")})
        return me

    def do(self, me, what, **more):
        return self.post("/pixel/room/do", dict(more, id=me, what=what))

    def view(self, me="", after=-1):
        return self.get(f"/pixel/room?id={me}&after={after}")

    def teacher(self, **data):
        return self.post("/pixel/teacher", dict(data, key=server.ADMIN_KEY))

    def test_the_teacher_can_close_and_open_the_room(self):
        server.pixel_room.update(server.room_empty(), open=False, words=False)
        mia = self.join("Mia")
        self.assertIn("closed", self.do(mia, "join")["error"])
        self.teacher(action="room", on=True)
        self.addCleanup(lambda: server.pixel_room.update(server.room_empty(), open=True, words=False))
        self.assertTrue(self.do(mia, "join")["ok"])
        self.assertTrue(self.get("/pixel/overview")["room_open"])

    def test_two_students_see_each_other(self):
        self.open_room()
        mia, ben = self.join("Mia"), self.join("Ben")
        self.do(mia, "join")
        self.do(ben, "join")
        seen = self.view(ben)
        self.assertEqual(sorted(m["name"] for m in seen["members"]), ["Ben", "Mia"])
        self.do(mia, "walk", x=200, y=.5)
        news = self.view(ben, seen["seq"])
        self.assertEqual([(e["kind"], e["x"]) for e in news["events"]], [("walk", 200)])

    def test_no_login_ever_leaves_the_server(self):
        self.open_room()
        mia = self.join("Mia")
        self.do(mia, "join")
        self.do(mia, "move", name="dance")
        self.assertNotIn(mia, json.dumps(self.view()))

    def test_words_come_from_the_list_unless_typing_is_on(self):
        self.open_room()
        mia = self.join("Mia")
        self.do(mia, "join")
        self.assertTrue(self.do(mia, "say", text="I do!")["ok"])
        self.assertIn("error", self.do(mia, "say", text="something else"))
        self.teacher(action="room_words", on=True)
        self.assertTrue(self.do(mia, "say", text="something else")["ok"])

    def test_only_real_moves_and_places(self):
        self.open_room()
        mia = self.join("Mia")
        self.do(mia, "join")
        for what, more in (("move", {"name": "fly"}), ("fx", {"name": "bomb"}), ("go", {"name": "castle"}), ("toy", {"name": "bomb", "x": 50, "y": 0}), ("find", {"key": "nope"}), ("scene", {"name": "park"}), ("walk", {"x": "a", "y": 0}), ("nope", {})):
            with self.subTest(what=what):
                self.assertIn("error", self.do(mia, what, **more))
        self.assertTrue(self.do(mia, "go", name="wedding")["ok"])

    def test_someone_who_goes_away_leaves_the_room(self):
        self.open_room()
        mia, ben = self.join("Mia"), self.join("Ben")
        self.do(mia, "join")
        self.do(ben, "join")
        server.pixel_room["here"][mia]["seen"] -= server.ROOM_AWAY + 1
        self.assertEqual([m["name"] for m in self.view(ben)["members"]], ["Ben"])

    def test_a_tap_wakes_a_waiting_browser_at_once(self):
        self.open_room()
        mia = self.join("Mia")
        self.do(mia, "join")
        seq = self.view(mia)["seq"]
        threading.Timer(.15, lambda: self.do(mia, "move", name="wave")).start()
        start = time.time()
        news = self.get(f"/pixel/room?id={mia}&after={seq}&wait=1")
        self.assertLess(time.time() - start, 1.5)
        self.assertEqual(news["events"][0]["kind"], "move")

class TheHangOut(unittest.TestCase):
    setUp, tearDown, post, get = StudioOverHttp.setUp, StudioOverHttp.tearDown, StudioOverHttp.post, StudioOverHttp.get
    do, view, teacher = PlayingTogether.do, PlayingTogether.view, PlayingTogether.teacher
    FIRST = 'say("Hello")\nsay("I am so happy to be here")'
    MOVE = 'say("Hooray!")\nsay("rude words")\nspin()\nfor i in range(3):\n    jump()\n    hearts()\ndance()\ncheer()'

    def setup_room(self):
        server.pixel_room.update(server.room_empty(), open=True, words=False)
        server.pixel_class.pop("hang", None)
        server.pixel_class.pop("placed", None)
        self.addCleanup(lambda: (server.pixel_room.update(server.room_empty(), open=True, words=False), server.pixel_class.pop("hang", None), server.pixel_class.pop("placed", None)))

    def student(self, name, solved=("a1", "a2", "a3")):
        me = self.post("/join", {"name": name})["id"]
        self.post("/pixel/save", {"id": me, "drawing": dict(drawing(), key="ink123", frames=["0" + "." * 255])})
        entry = server.pixel_entry(server.players[me])
        entry["solved"].update({k: [True] * 3 for k in solved})
        return me

    def mission(self, me, key, code):
        return self.post("/pixel/run", {"id": me, "level": key, "code": code})

    def with_move(self, name, code=None):
        me = self.student(name, BEFORE_MOVE)
        out = self.mission(me, "m1", code or self.MOVE)
        self.assertTrue(out["stars"][0], out)
        self.do(me, "join")
        return me

    def news(self, kind):
        return [e for e in server.pixel_room["events"] if e["kind"] == kind]

    def test_it_opens_after_the_third_mission(self):
        self.setup_room()
        me = self.student("Mia", ())
        self.assertEqual(self.get(f"/pixel/state?id={me}")["hang"]["needs"], 3)
        self.assertEqual(self.do(me, "join")["error"], "locked")
        self.mission(me, "a1", self.FIRST)
        self.mission(me, "a2", "jump()\njump()")
        out = self.mission(me, "a3", "right(5)")
        self.assertTrue(out["rewards"]["hang_opened"])
        self.assertEqual(out["state"]["hang"]["needs"], 0)
        self.assertTrue(self.do(me, "join")["ok"])

    def test_a_first_finish_gives_a_gift_once_and_fills_the_meter(self):
        self.setup_room()
        me = self.student("Mia", ())
        out = self.mission(me, "a1", self.FIRST)
        self.assertIn(out["rewards"]["gift"], pixel.BOX_GIFTS)
        self.assertEqual(out["state"]["hang"]["gifts"], [out["rewards"]["gift"]])
        self.assertEqual(server.hang_meter()["points"], pixel.MISSION_POINTS)
        again = self.mission(me, "a1", self.FIRST)
        self.assertFalse(again["rewards"]["first"])
        self.assertNotIn("gift", again["rewards"])
        self.assertEqual(server.hang_meter()["points"], pixel.MISSION_POINTS)

    def test_every_mission_can_give_a_different_gift(self):
        self.assertGreaterEqual(len(pixel.BOX_GIFTS), len(pixel.LEVELS))

    def test_the_finale_makes_a_my_move_with_its_perks(self):
        self.setup_room()
        me = self.student("Mia", BEFORE_MOVE)
        small = self.mission(me, "m1", "jump()\nspin()\ndance()")
        self.assertEqual(small["rewards"]["move"], {"title": "My Move", "loop": False, "big": False, "actions": 3})
        big = self.mission(me, "m1", self.MOVE)
        self.assertEqual((big["rewards"]["move"]["loop"], big["rewards"]["move"]["big"]), (True, True))
        self.assertIn("error", self.post("/pixel/move/name", {"id": me, "name": "anything I type"}))
        named = self.post("/pixel/move/name", {"id": me, "name": "Moon Hop"})
        self.assertEqual(named["state"]["hang"]["move"]["title"], "Moon Hop")
        self.assertEqual(self.mission(me, "m1", self.MOVE)["rewards"]["move"]["title"], "Moon Hop")

    def test_after_my_move_the_new_missions_open_one_at_a_time(self):
        self.setup_room()
        me = self.student("Mia", BEFORE_MOVE)
        self.assertTrue(self.mission(me, "m1", self.MOVE)["stars"][0])
        state = self.get(f"/pixel/state?id={me}")
        self.assertEqual(state["current"], "t1")
        out = self.mission(me, "t2", pixel.LEVEL_BY_KEY["t2"]["reference"])
        self.assertIn("error", out)
        out = self.mission(me, "t1", pixel.LEVEL_BY_KEY["t1"]["reference"])
        self.assertEqual(out["stars"], [True, True, True])
        self.assertGreater(out["rewards"]["coins"], 0)
        self.assertEqual(self.get(f"/pixel/state?id={me}")["current"], "t2")
        self.assertTrue(server.pixel_entry(server.players[me])["move"], "My Move is still kept")

    def test_a_failed_finale_changes_nothing(self):
        self.setup_room()
        me = self.student("Mia", BEFORE_MOVE)
        self.assertNotIn("move", self.mission(me, "m1", "jump()")["rewards"])
        self.assertIsNone(server.pixel_entry(server.players[me])["move"])

    def test_everyone_sees_a_my_move(self):
        self.setup_room()
        mia, ben = self.with_move("Mia"), self.student("Ben")
        self.do(ben, "join")
        seq = self.view(ben)["seq"]
        self.assertTrue(self.do(mia, "mymove")["ok"])
        event = self.view(ben, seq)["events"][0]
        self.assertEqual((event["kind"], event["by"], event["loop"], event["big"]), ("mymove", "Mia", True, True))
        self.assertEqual([s["do"] for s in event["steps"]][:2], ["say", "spin"])
        self.assertNotIn(mia, json.dumps(event))

    def test_a_my_move_only_says_listed_words_unless_typing_is_on(self):
        self.setup_room()
        mia = self.with_move("Mia")
        self.do(mia, "mymove")
        said = [s["text"] for s in self.news("mymove")[-1]["steps"] if s["do"] == "say"]
        self.assertEqual(said, ["Hooray!"])
        server.pixel_room["here"][mia]["move_until"] = 0
        self.teacher(action="room_words", on=True)
        self.do(mia, "mymove")
        said = [s["text"] for s in self.news("mymove")[-1]["steps"] if s["do"] == "say"]
        self.assertEqual(said, ["Hooray!", "rude words"])
        self.assertIn("rude words", self.teacher(action="overview")["room"]["said"])

    def test_a_pal_sits_and_reads_until_it_walks_away(self):
        self.setup_room()
        mia = self.student("Mia")
        self.do(mia, "join")
        self.assertTrue(self.do(mia, "rest", name="sit", x=104, y=.05)["ok"])
        event = self.news("rest")[-1]
        self.assertEqual((event["name"], event["x"], event["y"]), ("sit", 104, .05))
        self.assertTrue(self.do(mia, "rest", name="read")["ok"])
        self.assertEqual(self.news("rest")[-1]["x"], 104)
        self.assertEqual(self.view()["members"][0]["rest"], "read")     # someone arriving later sees it
        self.do(mia, "walk", x=200, y=.5)
        self.assertIsNone(self.view()["members"][0]["rest"])

    def test_other_drawings_come_along_as_buddies(self):
        self.setup_room()
        mia = self.student("Mia")
        ink = "0" + "." * 255
        for key in ("one", "two"):
            self.post("/pixel/save", {"id": mia, "drawing": drawing(key=key, frames=[ink])})
        self.post("/pixel/save", {"id": mia, "drawing": drawing(key="blank")})
        self.do(mia, "join")
        self.assertEqual(self.view()["members"][0]["buddies"], [])     # off to start, so hide and seek works
        self.assertTrue(self.do(mia, "buddies", on=True)["on"])
        self.assertEqual(len(self.view()["members"][0]["buddies"]), 2)     # not the pal, not the blank page

    def test_a_student_can_switch_which_drawing_they_are(self):
        self.setup_room()
        mia = self.student("Mia")
        ink = "1" + "." * 255
        self.post("/pixel/save", {"id": mia, "drawing": drawing(key="two", frames=[ink])})
        self.do(mia, "join")
        self.do(mia, "buddies", on=True)
        self.assertEqual(self.do(mia, "pal", key="two"), {"ok": True, "pal": "two"})
        row = self.view()["members"][0]
        self.assertEqual(row["pal"]["frames"], [ink])
        self.assertEqual([b["frames"] for b in row["buddies"]], [["0" + "." * 255]])     # the old pal comes along
        event = self.news("pal")[-1]
        self.assertEqual((event["seat"], event["pal"]["frames"]), (row["seat"], [ink]))
        self.assertEqual(self.get(f"/pixel/state?id={mia}")["pal"], "two")

    def test_only_your_own_finished_drawings_can_be_your_pal(self):
        self.setup_room()
        mia, ben = self.student("Mia"), self.student("Ben")
        self.post("/pixel/save", {"id": ben, "drawing": drawing(key="bens")})
        self.post("/pixel/save", {"id": mia, "drawing": drawing(key="blank")})
        self.do(mia, "join")
        for key in ("bens", "blank", None):
            self.assertIn("error", self.do(mia, "pal", key=key))
        self.assertEqual(self.get(f"/pixel/state?id={mia}")["pal"], "ink123")

    def test_a_student_can_hide_their_name_from_the_class(self):
        self.setup_room()
        mia = self.student("Mia")
        self.do(mia, "join")
        self.assertTrue(self.do(mia, "hidename", on=True)["on"])
        self.assertEqual(self.news("name")[-1]["name"], "Secret pal")
        self.assertTrue(self.news("name")[-1]["hid"])                                  # the stage drops the tag completely
        self.assertTrue(self.view()["members"][0]["hid"])
        self.assertEqual(self.view()["members"][0]["name"], "Secret pal")
        self.assertEqual(self.view()["people"][0]["name"], "Secret pal")
        self.assertEqual(self.teacher(action="overview")["room"]["here"], ["Mia"])     # the teacher still knows
        self.assertTrue(self.get(f"/pixel/state?id={mia}")["hang"]["hide_name"])
        self.assertFalse(self.do(mia, "hidename", on=False)["on"])
        self.assertEqual(self.news("name")[-1]["name"], "Mia")
        self.assertFalse(self.news("name")[-1]["hid"])
        self.assertEqual(self.view()["members"][0]["name"], "Mia")

    def test_a_pal_can_turn_into_a_prop_for_prop_hunt(self):
        self.setup_room()
        mia = self.student("Mia")
        self.do(mia, "join")
        self.assertFalse(self.view()["members"][0]["prop"])
        self.assertTrue(self.do(mia, "prop", on=True)["on"])
        self.assertTrue(self.view()["members"][0]["prop"])
        self.assertTrue(self.news("prop")[-1]["on"])
        self.assertFalse(self.do(mia, "prop", on=False)["on"])

    def test_only_a_few_buddies_come_along(self):
        self.setup_room()
        mia = self.student("Mia")
        for i in range(6):
            self.post("/pixel/save", {"id": mia, "drawing": drawing(key=f"pic{i}", frames=["0" + "." * 255])})
        self.do(mia, "join")
        self.do(mia, "buddies", on=True)
        self.assertEqual(len(self.view()["members"][0]["buddies"]), pixel.ROOM_BUDDIES)

    def test_the_world_is_as_long_as_the_places_that_are_open(self):
        self.setup_room()
        winter = patch.object(server, "winter", return_value=False)     # the ❄️ Snow Village adds one more place
        winter.start()
        self.addCleanup(winter.stop)
        mia = self.student("Mia")
        self.do(mia, "join")
        self.do(mia, "walk", x=5000, y=.5)
        self.assertEqual(self.news("walk")[-1]["x"], 4 * pixel.PLACE_W - 8)
        with server.lock:
            server.hang_fill(pixel.party_goal(0))
        self.do(mia, "walk", x=5000, y=.5)
        self.assertEqual(self.news("walk")[-1]["x"], 5 * pixel.PLACE_W - 8)

    def test_going_somewhere_takes_only_you(self):
        self.setup_room()
        mia, ben = self.student("Mia"), self.student("Ben")
        self.do(mia, "join")
        self.do(ben, "join")
        spots = lambda: {m["name"]: m["x"] for m in self.view()["members"]}
        ben_was = spots()["Ben"]
        self.do(mia, "go", name="beach")
        self.assertEqual(spots()["Ben"], ben_was)
        self.assertTrue(2 * pixel.PLACE_W <= spots()["Mia"] < 3 * pixel.PLACE_W)     # somewhere free on the Beach

    def place(self, me, key="ink123", x=100):
        with server.lock:
            server.pixel_room["here"][me]["placed"] = 0
        return self.do(me, "place", key=key, x=x, y=.5)

    def test_a_placed_drawing_is_there_for_everyone(self):
        self.setup_room()
        mia, ben = self.student("Mia"), self.student("Ben")
        self.do(mia, "join")
        self.do(ben, "join")
        self.assertTrue(self.place(mia)["ok"])
        self.assertNotIn(mia, json.dumps(self.news("place")[-1]))
        self.assertTrue(self.view(mia)["placed"][0]["mine"])
        self.assertFalse(self.view(ben)["placed"][0]["mine"])
        self.assertNotIn(mia, json.dumps(self.view(ben)["placed"]))

    def test_only_your_own_real_drawings_can_be_placed(self):
        self.setup_room()
        mia = self.student("Mia")
        self.do(mia, "join")
        self.post("/pixel/save", {"id": mia, "drawing": drawing(key="blank")})
        self.assertEqual(self.place(mia, "blank")["error"], "bad")
        self.assertEqual(self.place(mia, "someone-elses")["error"], "bad")

    def test_a_new_drawing_replaces_your_oldest_at_the_limit(self):
        self.setup_room()
        mia = self.student("Mia")
        self.do(mia, "join")
        for x in range(10, 10 + pixel.PLACED_EACH + 1):
            self.place(mia, x=x)
        self.assertEqual([p["x"] for p in self.view(mia)["placed"]], list(range(11, 11 + pixel.PLACED_EACH)))

    def test_only_the_owner_can_take_one_back(self):
        self.setup_room()
        mia, ben = self.student("Mia"), self.student("Ben")
        self.do(mia, "join")
        self.do(ben, "join")
        self.place(mia)
        placed = self.view(mia)["placed"][0]["id"]
        self.do(ben, "unplace", piece=placed)
        self.assertEqual(len(self.view()["placed"]), 1)
        self.do(mia, "unplace", piece=placed)
        self.assertEqual(self.view()["placed"], [])

    def test_deleting_a_drawing_takes_it_out_of_the_world(self):
        self.setup_room()
        mia = self.student("Mia")
        self.do(mia, "join")
        self.place(mia)
        self.post("/pixel/delete", {"id": mia, "key": "ink123"})
        self.assertEqual(self.view()["placed"], [])

    def test_the_teacher_can_remove_placed_drawings(self):
        self.setup_room()
        mia, ben = self.student("Mia"), self.student("Ben")
        self.do(mia, "join")
        self.do(ben, "join")
        self.place(mia)
        self.place(ben)
        self.assertEqual(self.teacher(action="overview")["placed"], {"Mia": 1, "Ben": 1})
        self.teacher(action="placed_clear", name="Mia")
        self.assertEqual(self.teacher(action="overview")["placed"], {"Ben": 1})
        self.teacher(action="placed_clear")
        self.assertEqual(self.view()["placed"], [])

    def test_a_toy_has_to_wait_a_moment(self):
        self.setup_room()
        mia = self.student("Mia")
        self.do(mia, "join")
        self.assertTrue(self.do(mia, "toy", name="splash", x=160, y=.05)["ok"])
        self.assertEqual(self.do(mia, "toy", name="splash", x=160, y=.05)["error"], "wait")

    def test_a_gem_counts_once_and_only_in_an_open_place(self):
        self.setup_room()
        mia = self.student("Mia")
        self.do(mia, "join")
        self.assertEqual(self.do(mia, "find", key="park0")["found"], 1)
        self.assertEqual(self.do(mia, "find", key="park0")["found"], 1)
        self.assertEqual(self.do(mia, "find", key="snowy0")["error"], "bad")
        self.assertEqual(self.get(f"/pixel/state?id={mia}")["hang"]["found"], ["park0"])

    def test_every_gem_earns_the_badge(self):
        self.setup_room()
        mia = self.student("Mia")
        self.do(mia, "join")
        with server.lock:
            server.pixel_entry(server.players[mia])["found"] = list(pixel.HANG_FINDS[1:])
        self.assertEqual(self.do(mia, "find", key="park0")["badges"][0]["name"], "Treasure Hunter")

    def test_a_pal_cannot_rest_in_a_made_up_way(self):
        self.setup_room()
        mia = self.student("Mia")
        self.do(mia, "join")
        self.assertEqual(self.do(mia, "rest", name="fly")["error"], "bad")
        self.assertEqual(self.do(mia, "rest", name="sit", x="far", y=0)["error"], "bad")

    def test_a_my_move_has_to_wait_its_turn(self):
        self.setup_room()
        mia = self.with_move("Mia")
        self.assertTrue(self.do(mia, "mymove")["ok"])
        self.assertEqual(self.do(mia, "mymove")["error"], "wait")

    def test_no_my_move_yet(self):
        self.setup_room()
        ben = self.student("Ben")
        self.do(ben, "join")
        self.assertIn("error", self.do(ben, "mymove"))

    def test_a_my_move_walks_but_stays_in_the_room(self):
        steps = pixel.compile_move([{"do": "walk", "to": 10, "by": 8}, {"do": "walk", "to": 0, "by": 10}])
        played, x, _ = pixel.stage_move(steps, 300, False)
        self.assertEqual(([s["x"] for s in played], x), ([312, 52], 52))

    def test_a_long_program_is_cut_short(self):
        self.assertEqual(len(pixel.compile_move([{"do": "jump"}] * 200)), pixel.MOVE_MAX)

    def test_claps_are_only_for_a_move_that_is_playing(self):
        self.setup_room()
        mia, ben = self.with_move("Mia"), self.student("Ben")
        self.do(ben, "join")
        seat = server.pixel_room["here"][mia]["seat"]
        self.assertIn("error", self.do(ben, "clap", seat=seat))
        self.do(mia, "mymove")
        self.assertIn("error", self.do(mia, "clap", seat=seat))
        self.assertTrue(self.do(ben, "clap", seat=seat)["ok"])
        self.assertTrue(self.do(ben, "clap", seat=seat)["ok"])          # too quick to count
        self.assertEqual([e["claps"] for e in self.news("clap")], [1])

    def test_a_high_five_makes_a_friend_both_ways_only_once(self):
        self.setup_room()
        mia, ben = self.student("Mia"), self.student("Ben")
        self.do(mia, "join")
        self.do(ben, "join")
        here = server.pixel_room["here"]
        self.assertIn("error", self.do(mia, "five", seat=here[mia]["seat"]))
        self.assertEqual(self.do(mia, "five", seat=here[ben]["seat"])["friends"], ["Ben"])
        self.assertEqual(self.get(f"/pixel/state?id={ben}")["hang"]["friends"], ["Mia"])
        self.assertEqual(self.news("five")[-1]["fresh"], [here[mia]["seat"], here[ben]["seat"]])
        here[mia]["fived"] = 0
        self.do(mia, "five", seat=here[ben]["seat"])
        self.assertEqual(self.news("five")[-1]["fresh"], [])
        self.assertEqual(self.get(f"/pixel/state?id={mia}")["hang"]["friends"], ["Ben"])

    def test_the_first_pal_to_a_star_gets_it_and_combos_climb(self):
        self.setup_room()
        mia, ben = self.student("Mia"), self.student("Ben")
        self.do(mia, "join")
        self.do(ben, "join")
        self.teacher(action="shower")
        count = len(server.pixel_room["shower"]["stars"])
        self.assertEqual(count, 10)
        self.assertTrue(self.do(mia, "catch", star=0)["ok"])
        self.assertEqual(self.do(ben, "catch", star=0)["error"], "gone")
        self.do(mia, "catch", star=1)
        self.assertEqual([e["combo"] for e in self.news("catch")], [1, 2])
        for star in (2, 3):
            self.assertEqual(self.do(mia, "catch", star=star)["badges"], [])
        self.assertEqual(self.do(mia, "catch", star=4)["badges"][0]["name"], "Star Catcher")

    def test_a_shower_starts_by_itself_and_ends(self):
        self.setup_room()
        mia = self.student("Mia")
        self.do(mia, "join")
        self.assertIsNone(server.pixel_room["shower"])
        server.pixel_room["next_shower"] = 0
        self.assertTrue(self.view(mia)["members"] is not None)
        self.assertIsNotNone(server.pixel_room["shower"])
        self.assertTrue(self.view(mia)["shower"])                        # someone arriving late sees it too
        server.pixel_room["shower"]["ends"] = 0
        self.view(mia)
        self.assertIsNone(server.pixel_room["shower"])
        self.assertEqual(self.news("shower_end")[-1]["kind"], "shower_end")

    def test_you_can_only_wear_what_you_own(self):
        self.setup_room()
        me = self.post("/join", {"name": "Mia"})["id"]
        server.pixel_entry(server.players[me])["solved"].update({k: [True] * 3 for k in ("a1", "a2", "a3")})
        server.pixel_entry(server.players[me])["gifts"].append("tophat")
        self.do(me, "join")
        self.assertIn("error", self.do(me, "wear", slot="hat", item="party"))
        self.assertIn("error", self.do(me, "wear", slot="face", item="tophat"))
        self.assertIn("error", self.do(me, "wear", slot="nose", item="tophat"))
        self.assertTrue(self.do(me, "wear", slot="hat", item="tophat")["ok"])
        self.assertEqual(self.view(me)["members"][0]["wear"], {"hat": "tophat"})
        self.assertTrue(self.do(me, "wear", slot="hat", item=None)["ok"])
        self.assertEqual(self.view(me)["members"][0]["wear"], {})

    def test_a_full_meter_is_a_party_with_a_new_place_for_everyone(self):
        self.setup_room()
        me = self.student("Mia")
        self.do(me, "join")
        self.assertIn("error", self.do(me, "go", name="snowy"))
        with server.lock:
            server.hang_fill(pixel.party_goal(0) + 1)
        party = self.news("party")[-1]
        self.assertEqual(party["reward"]["key"], "snowy")
        self.assertEqual(server.hang_meter(), {"points": 1, "level": 1})
        self.assertIn("snowy", self.view(me)["places"])
        self.assertTrue(self.do(me, "go", name="snowy")["ok"])

    def test_a_class_gift_comes_to_everyone(self):
        self.setup_room()
        me = self.student("Mia")
        with server.lock:
            server.hang_fill(pixel.party_goal(0))
            server.hang_fill(pixel.party_goal(1))
        self.assertIn("crown", self.get(f"/pixel/state?id={me}")["hang"]["gifts"])

    def test_a_my_move_fills_the_meter_only_once_in_a_while(self):
        self.setup_room()
        mia = self.with_move("Mia")
        before = server.hang_meter()["points"]
        self.do(mia, "mymove")
        server.pixel_room["here"][mia]["move_until"] = 0
        self.do(mia, "mymove")
        self.assertEqual(server.hang_meter()["points"], before + pixel.MOVE_POINTS)

    def test_the_teacher_can_throw_a_party(self):
        self.setup_room()
        self.assertTrue(self.teacher(action="party")["ok"])
        self.assertIsNone(self.news("party")[-1]["reward"])

    def test_old_saves_with_shows_and_cut_missions_still_load(self):
        self.setup_room()
        me = self.student("Mia")
        entry = server.pixel_entry(server.players[me])
        entry["solved"]["g4"] = [True] * 3
        entry["show"] = {"title": "Old"}
        state = self.get(f"/pixel/state?id={me}")
        self.assertEqual(state["stars"], 9)
        self.assertEqual(state["max_stars"], 3 * len(pixel.LEVELS))


class TheMarks(unittest.TestCase):
    def drawing(self, **extra):
        return dict({"key": "abc123", "title": "x", "size": 16, "speed": 6, "palette": ["#000000", "#ffffff"],
                     "frames": ["." * 256], "names": [""]}, **extra)

    def test_marks_and_guides_are_kept_when_they_fit(self):
        marks, guide = "a" * 256, "1" * 256
        out = pixel.clean_drawing(self.drawing(marks=marks, guide=guide))
        self.assertEqual((out["marks"], out["guide"]), (marks, guide))

    def test_bad_marks_and_guides_are_dropped_not_fatal(self):
        for bad in ("a", "z" * 256, 7, None, ["a"] * 256):
            with self.subTest(bad=bad):
                out = pixel.clean_drawing(self.drawing(marks=bad, guide=bad))
                self.assertEqual((out["marks"], out["guide"]), ("", ""))

    def test_a_huge_canvas_is_allowed(self):
        self.assertIsNotNone(pixel.clean_drawing(self.drawing(size=48, frames=["." * 2304])))


class AliveOnStage(unittest.TestCase):
    def out(self, code, pal=pixel.PIP):
        return pixel.perform(code, pal=pal, commands=pixel.EVERYTHING)

    def test_the_new_moves_are_steps(self):
        steps = self.out('wave()\ndance()\ncheer()\nlook("up")\nfeel("silly")')["steps"]
        self.assertEqual([s["do"] for s in steps], ["wave", "dance", "cheer", "look", "feel"])

    def test_every_feeling_and_look_works(self):
        for word in pixel.FEELINGS:
            self.assertIsNone(self.out(f'feel("{word}")')["error"])
        for word in pixel.LOOKS:
            self.assertIsNone(self.out(f'look("{word}")')["error"])

    def test_pose_makes_the_face_when_there_is_no_frame(self):
        pal = dict(pixel.PIP, frames=pixel.PIP["frames"][:1], names=[""])
        steps = self.out('pose("sad")\npose("wave")\npose("hello")', pal)["steps"]
        self.assertEqual([(s["do"], s.get("mood")) for s in steps],
                         [("feel", "sad"), ("wave", None), ("wave", None)])

    def test_a_drawn_frame_beats_the_made_face(self):
        steps = self.out('pose("happy")')["steps"]
        self.assertEqual(steps[0]["do"], "pose")

    def test_every_page_script_is_served(self):
        for path in ("/pixel/rig.js", "/pixel/gallery.js", "/pixel/life.js", "/pixel/hangout.js"):
            self.assertIn(path, server.PAGES)


class TheArtItself(unittest.TestCase):
    """pixel_art.js has no page in it, so node can run it directly."""

    def js(self, code):
        folder = os.path.dirname(os.path.abspath(__file__))
        script = f"const A = require({json.dumps(os.path.join(folder, 'pixel_art.js'))});" \
                 f"process.stdout.write(JSON.stringify((() => {{ {code} }})()))"
        return json.loads(subprocess.check_output(["node", "-e", script]))

    def test_the_palette_and_the_server_agree_on_the_letters(self):
        self.assertEqual(self.js("return A.decode(A.encode([-1, 0, 9, 10, 35, 36, 61]))"),
                         [-1, 0, 9, 10, 35, 36, 61])
        self.assertEqual(self.js("return A.encode([10, 36, 61])"),
                         pixel.LETTERS[10] + pixel.LETTERS[36] + pixel.LETTERS[61])

    def test_the_starters_are_all_square(self):
        self.assertEqual(self.js("return Object.values(A.STARTERS).map(r => [r.length, new Set(r.map(s => s.length)).size])"),
                         [[16, 1]] * 4)

    def test_a_line_joins_its_ends_with_no_gaps(self):
        for ends in ([0, 0, 7, 3], [7, 3, 0, 0], [2, 9, 2, 1], [1, 1, 1, 1]):
            with self.subTest(ends=ends):
                cells = self.js(f"return A.line({', '.join(map(str, ends))})")
                self.assertEqual(cells[0], ends[:2])
                self.assertEqual(cells[-1], ends[2:])
                for a, b in zip(cells, cells[1:]):
                    self.assertLessEqual(max(abs(a[0] - b[0]), abs(a[1] - b[1])), 1)

    def test_a_box_outline_and_a_solid_box(self):
        self.assertEqual(self.js("return [A.box(3, 3, 0, 0).length, A.box(0, 0, 3, 3, true).length]"), [12, 16])

    def test_a_circle_stays_in_its_box_and_touches_all_four_sides(self):
        cells = self.js("return A.circle(2, 3, 12, 9)")
        self.assertEqual({min(c[0] for c in cells), max(c[0] for c in cells)}, {2, 12})
        self.assertEqual({min(c[1] for c in cells), max(c[1] for c in cells)}, {3, 9})

    def test_fill_stops_at_a_wall(self):
        count = self.js("""const f = A.blank(5);
            for (let y = 0; y < 5; y++) f[y * 5 + 2] = 0;
            return A.flood(f, 5, 0, 0).length""")
        self.assertEqual(count, 10)

    def test_flip_twice_and_shift_round_change_nothing(self):
        same = self.js("""const f = A.blank(4); f[1] = 3; f[6] = 2;
            const r = A.shift(A.shift(f, 4, 3, 0), 4, 1, 0);
            return [A.flip(A.flip(f, 4), 4), r, f]""")
        self.assertEqual(same[0], same[2])
        self.assertEqual(same[1], same[2])

    def test_a_gif_opens_with_the_right_frames_colours_and_empty_squares(self):
        try:
            from PIL import Image, ImageSequence
        except ImportError:
            self.skipTest("needs Pillow")
        # Noisy frames fill the compression table, the part of a GIF writer that breaks.
        made = self.js("""let seed = 1, roll = () => (seed = seed * 16807 % 2147483647);
            const frames = [0, 1, 2].map(() => Array.from({length: 1024}, () => roll() % 63 - 1));
            const palette = Array.from({length: 62}, (_, i) => "#" + [i * 4, 255 - i * 4, i * 2]
                .map(n => n.toString(16).padStart(2, "0")).join(""));
            return {frames, palette, bytes: Array.from(A.gif(frames, 32, 8, palette, 6))}""")
        path = os.path.join(tempfile.mkdtemp(), "art.gif")
        with open(path, "wb") as f:
            f.write(bytes(made["bytes"]))
        with Image.open(path) as image:
            self.assertEqual(image.size, (256, 256))
            pictures = [f.convert("RGBA") for f in ImageSequence.Iterator(image)]
        self.assertEqual(len(pictures), 3)
        for picture, frame in zip(pictures, made["frames"]):
            for at, colour in enumerate(frame):
                seen = picture.getpixel(((at % 32) * 8 + 3, (at // 32) * 8 + 3))
                if colour < 0:
                    self.assertEqual(seen[3], 0)
                else:
                    hex_colour = made["palette"][colour]
                    self.assertEqual("#%02x%02x%02x" % seen[:3], hex_colour)


if __name__ == "__main__":
    unittest.main()
