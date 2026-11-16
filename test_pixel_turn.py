"""Your turn: after each mission, one change a student makes with the guide off."""
import json
import unittest

import pixel
import server
from test_pixel import StudioOverHttp, drawing

# One way to do each Your turn, written the way a student might change the guide's code.
CHANGED = {
    "a1": 'say("Hello")\nsay("I am so happy to be here")\nsay("Bye")',
    "a2": 'jump()\nsay("Wheee!")\njump()\njump()',
    "a3": 'right(5)\nsay("Here I am!")\nright(3)\nleft(8)',
    "h1": 'say("Hello!")\nwave()\nwave()\nwave()\njump()',
    "h3": 'feel("sad")\nwait(1)\nfeel("silly")\nwait(1)\nfeel("happy")',
    "h4": "dance()\ndance()\ncheer()\nhearts()",
    "b1": "for i in range(10):\n    jump()",
    "b2": "for i in range(4):\n    right(1)\n    left(1)\n    jump()\nconfetti()",
    "m1": 'spin()\nfor i in range(3):\n    jump()\n    hearts()\nsay("Ta-da")\ndance()\ncheer()',
    "t1": 'grow()\ngrow()\nshake()\nshrink()\nshrink()\nsay("Ta-da!")',
    "t2": 'look("left")\nwait(1)\nlook("right")\nwait(1)\nlook("up")\nlook("down")\nlook("front")\nsay("Oh, hello!")',
    "l1": "for i in range(10):\n    say(i + 1)\n    jump()",
    "l2": 'for name in ["Ana", "Ben", "Cy", "Mia"]:\n    say("Hi " + name)\n    jump()',
    "v1": 'name = "Sparkle"\nsay("I am " + name)\nsay(name.upper() + " IS HERE")',
    "v2": 'jumps = 7\nfor i in range(jumps):\n    jump()\ngrow()\nsay(f"{jumps} jumps!")',
    "w1": "def boogie():\n    jump()\n    spin()\n    jump()\nboogie()\nboogie()\nboogie()",
    "w2": "for i in range(1, 6):\n    say(i)\n    if i == 5:\n        jump()",
    "r1": 'mood = choice(["happy", "silly", "cool", "sleepy"])\nfeel(mood)\nsay("I feel " + mood)',
    "r2": "roll = randint(1, 6)\nsay(roll)\nif roll == 6:\n    cheer()\nif roll == 1:\n    jump()",
    "r3": 'jumps = randint(5, 10)\nfor i in range(jumps):\n    jump()\nsay(f"{jumps} lucky jumps!")',
}


# What really happens when the guide's code runs, in the words of each guess's choices.
def _n(steps, do):
    return sum(1 for s in steps if s["do"] == do)


def _said(steps):
    return [str(s["text"]) for s in steps if s["do"] == "say"]


TRUTH = {
    "a1": lambda st: str(_n(st, "say")),
    "a2": lambda st: "Your pal talks" if [s["do"] for s in st] == ["jump", "say", "jump"] else "?",
    "a3": lambda st: "Back on spot 2" if [s for s in st if s["do"] == "walk"][-1]["to"] == 2 else "?",
    "h1": lambda st: str(_n(st, "wave")),
    "h3": lambda st: [s["mood"] for s in st if s["do"] == "feel"][-1].capitalize(),
    "h4": lambda st: {"dance": "Dancing", "cheer": "Cheering", "hearts": "Hearts"}[st[-1]["do"]],
    "b1": lambda st: str(_n(st, "jump")),
    "b2": lambda st: "Once" if _n(st, "confetti") == 1 else "?",
    "t1": lambda st: "Small, like at the start" if [s for s in st if s["do"] == "size"][-1]["to"] == 1 else "Big",
    "t2": lambda st: {"left": "Left", "right": "Right", "front": "At us"}[[s for s in st if s["do"] == "look"][-1]["way"]],
    "l1": lambda st: _said(st)[0],
    "l2": lambda st: _said(st)[0],
    "v1": lambda st: _said(st)[0],
    "v2": lambda st: _said(st)[-1],
    "w1": lambda st: str(_n(st, "jump")),
    "w2": lambda st: "Once" if _n(st, "jump") == 1 else "?",
    "r1": lambda st: "Sad" if [s["mood"] for s in st if s["do"] == "feel"][0] in ("happy", "silly", "cool") else "?",
    "r2": lambda st: "6" if 1 <= int(_said(st)[0]) <= 6 else "?",
    "r3": lambda st: "2" if _n(st, "jump") >= 2 else "?",
}


def run(key, code):
    return pixel.run_level(pixel.LEVEL_BY_KEY[key], code, pixel.PIP)


class EveryMissionHasATurn(unittest.TestCase):
    def test_every_mission_has_one(self):
        self.assertEqual(set(pixel.REMIXES), set(pixel.LEVEL_ORDER))
        self.assertEqual(set(CHANGED), set(pixel.LEVEL_ORDER))

    def test_the_guides_own_code_is_not_enough(self):
        for lv in pixel.LEVELS:
            with self.subTest(level=lv["key"]):
                self.assertFalse(run(lv["key"], lv["reference"])["remix"])

    def test_a_changed_program_does_the_mission_and_the_turn(self):
        for key, code in CHANGED.items():
            with self.subTest(level=key):
                out = run(key, code)
                self.assertIsNone(out["error"])
                self.assertTrue(out["stars"][0], out["reply"])
                self.assertTrue(out["remix"])

    def test_jumping_on_the_wrong_number_is_not_the_turn(self):
        self.assertFalse(run("w2", "for i in range(1, 6):\n    say(i)\n    if i == 4:\n        jump()")["remix"])


class GuessFirst(unittest.TestCase):
    def test_every_answer_is_what_really_happens(self):
        self.assertEqual(set(pixel.GUESSES), set(TRUTH))
        self.assertEqual(set(pixel.GUESSES), set(pixel.LEVEL_ORDER) - {"m1"})
        for key, (ask, choices, answer) in pixel.GUESSES.items():
            with self.subTest(level=key):
                steps = run(key, pixel.LEVEL_BY_KEY[key]["reference"])["steps"]
                self.assertEqual(TRUTH[key](steps), choices[answer])
                self.assertEqual(len(set(choices)), len(choices))


class TurnOverHttp(unittest.TestCase):
    setUp, tearDown, post, get = StudioOverHttp.setUp, StudioOverHttp.tearDown, StudioOverHttp.post, StudioOverHttp.get

    def test_it_pays_once_with_a_badge_and_shows_on_the_mission(self):
        me = self.post("/join", {"name": "Mia"})["id"]
        self.post("/pixel/save", {"id": me, "drawing": drawing()})
        first = self.post("/pixel/run", {"id": me, "level": "a1", "code": pixel.LEVEL_BY_KEY["a1"]["reference"]})
        self.assertNotIn("remixed", first["rewards"])
        level = self.get(f"/pixel/level?id={me}&level=a1")
        self.assertEqual(level["remix"]["done"], False)
        self.assertEqual(level["remix"]["ask"], pixel.REMIXES["a1"][0])
        coins = server.pixel_entry(server.players[me])["coins"]
        out = self.post("/pixel/run", {"id": me, "level": "a1", "code": CHANGED["a1"]})
        self.assertTrue(out["rewards"]["remixed"])
        self.assertEqual(out["rewards"]["coins"], pixel.REMIX_COINS)
        self.assertIn("Remixer", [b["name"] for b in out["rewards"]["badges"]])
        self.assertEqual(server.pixel_entry(server.players[me])["coins"], coins + pixel.REMIX_COINS)
        again = self.post("/pixel/run", {"id": me, "level": "a1", "code": CHANGED["a1"]})
        self.assertNotIn("remixed", again["rewards"])
        self.assertEqual(again["rewards"]["coins"], 0)
        self.assertTrue(self.get(f"/pixel/level?id={me}&level=a1")["remix"]["done"])
        a1 = next(l for ch in again["state"]["chapters"] for l in ch["levels"] if l["key"] == "a1")
        self.assertTrue(a1["remixed"])

    def test_the_teacher_sees_how_many_turns(self):
        me = self.post("/join", {"name": "Mia"})["id"]
        self.post("/pixel/run", {"id": me, "level": "a1", "code": pixel.LEVEL_BY_KEY["a1"]["reference"]})
        self.post("/pixel/run", {"id": me, "level": "a1", "code": CHANGED["a1"]})
        row = next(r for r in server.pixel_overview()["students"] if r["name"] == "Mia")
        self.assertEqual(row["turns"], 1)

    def test_a_right_first_guess_pays_and_only_the_first_guess_counts(self):
        me = self.post("/join", {"name": "Mia"})["id"]
        ref = pixel.LEVEL_BY_KEY["a1"]["reference"]
        self.assertEqual(self.get(f"/pixel/level?id={me}&level=a1")["guess"]["choices"], ["1", "2", "3"])
        self.assertNotIn("answer", json.dumps(self.get(f"/pixel/level?id={me}&level=a1")["guess"]))
        out = self.post("/pixel/run", {"id": me, "level": "a1", "code": ref, "guess": 1})
        self.assertEqual(out["rewards"]["guess"], {"right": True, "answer": "2"})
        self.assertEqual(out["rewards"]["coins"], pixel.COINS_FIRST + 3 * pixel.COINS_STAR + pixel.GUESS_COINS)
        again = self.post("/pixel/run", {"id": me, "level": "a1", "code": ref, "guess": 1})
        self.assertNotIn("guess", again["rewards"])
        self.assertIsNone(self.get(f"/pixel/level?id={me}&level=a1")["guess"])

    def test_a_wrong_guess_says_the_answer_and_pays_nothing_extra(self):
        me = self.post("/join", {"name": "Mia"})["id"]
        out = self.post("/pixel/run", {"id": me, "level": "a1", "code": pixel.LEVEL_BY_KEY["a1"]["reference"], "guess": 2})
        self.assertEqual(out["rewards"]["guess"], {"right": False, "answer": "2"})
        self.assertEqual(out["rewards"]["coins"], pixel.COINS_FIRST + 3 * pixel.COINS_STAR)

    def test_a_first_finish_is_the_mission_win_not_a_turn(self):
        # My Move is the student's own code, and most moves already say something.
        me = self.post("/join", {"name": "Mia"})["id"]
        move = 'say("Hi")\njump()\nspin()\ncheer()'
        for key in pixel.LEVEL_ORDER[:pixel.LEVEL_ORDER.index("m1")]:
            self.post("/pixel/run", {"id": me, "level": key, "code": pixel.LEVEL_BY_KEY[key]["reference"]})
        first = self.post("/pixel/run", {"id": me, "level": "m1", "code": move})
        self.assertTrue(first["rewards"]["first"])
        self.assertNotIn("remixed", first["rewards"])
        self.assertFalse(self.get(f"/pixel/level?id={me}&level=m1")["remix"]["done"])
        again = self.post("/pixel/run", {"id": me, "level": "m1", "code": move})
        self.assertTrue(again["rewards"]["remixed"])

    def test_a_turn_that_breaks_the_mission_does_not_count(self):
        me = self.post("/join", {"name": "Mia"})["id"]
        out = self.post("/pixel/run", {"id": me, "level": "a1", "code": 'say("a b c")\nsay("x")\nsay(1/0)'})
        self.assertNotIn("remixed", out["rewards"])


if __name__ == "__main__":
    unittest.main()
