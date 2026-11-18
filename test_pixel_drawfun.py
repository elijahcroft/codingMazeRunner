"""The Draw tab's little extras: 4-way mirror, Sparkle pen and six new stamps.

The browser checks live in tools/e2e_draw.py, and the Draw tab's core tests
run in node.  These keep the new shapes and the two small pure helpers honest
without needing a page.
"""
import json
import os
import shutil
import subprocess
import unittest


FOLDER = os.path.dirname(os.path.abspath(__file__))
NEW_STAMPS = ["Bunny ears", "Cat ears", "Unicorn horn", "Wings", "Flower crown", "Cupcake"]


def js(code):
    script = (f"const A = require({json.dumps(os.path.join(FOLDER, 'pixel_art.js'))});"
              f"process.stdout.write(JSON.stringify((() => {{ {code} }})()))")
    return json.loads(subprocess.check_output(["node", "-e", script], timeout=60))


@unittest.skipUnless(shutil.which("node"), "needs node")
class NewStamps(unittest.TestCase):
    """The six new stamps use the same tiny rows as the old ones."""

    @classmethod
    def setUpClass(cls):
        cls.stamps = js(r"""
          return Object.fromEntries(Object.keys(A.STAMPS).map(name => {
            const rows = A.STAMPS[name];
            return [name, {rows, width: rows[0].length, height: rows.length,
                           letters: [...new Set(rows.join(""))].sort()}];
          }));
        """)
        cls.ink = js("return A.STAMP_INK")

    def test_the_six_new_stamps_are_there(self):
        for name in NEW_STAMPS:
            with self.subTest(stamp=name):
                self.assertIn(name, self.stamps)

    def test_rows_are_rectangular(self):
        for name in NEW_STAMPS:
            with self.subTest(stamp=name):
                rows = self.stamps[name]["rows"]
                self.assertTrue(rows)
                self.assertEqual(len({len(row) for row in rows}), 1, rows)
                self.assertEqual(self.stamps[name]["width"], len(rows[0]))
                self.assertEqual(self.stamps[name]["height"], len(rows))

    def test_only_known_ink_letters(self):
        known = set(self.ink) | {"x", "."}
        for name in NEW_STAMPS:
            with self.subTest(stamp=name):
                letters = set(self.stamps[name]["letters"])
                self.assertLessEqual(letters, known, letters)
                self.assertGreaterEqual(len(letters - {"."}), 2, letters)

    def test_they_fit_a_small_canvas(self):
        for name in NEW_STAMPS:
            with self.subTest(stamp=name):
                info = self.stamps[name]
                self.assertLessEqual(info["width"], 16)
                self.assertLessEqual(info["height"], 16)
                self.assertGreaterEqual(info["width"], 3)
                self.assertGreaterEqual(info["height"], 3)


@unittest.skipUnless(shutil.which("node"), "needs node")
class MirrorAndSparkle(unittest.TestCase):
    """The two pure helpers the Draw tab uses for mirroring and Sparkle."""

    def mirror(self, x, y, size, sideways, fourways):
        return js(f"return A.mirrorPoints({x}, {y}, {size}, {str(sideways).lower()}, {str(fourways).lower()})")

    def test_mirror_off_is_just_the_square(self):
        self.assertEqual(self.mirror(2, 3, 16, False, False), [[2, 3]])

    def test_left_right_mirror_is_the_old_behaviour(self):
        self.assertEqual(self.mirror(2, 3, 16, True, False), [[2, 3], [13, 3]])

    def test_four_way_mirror_adds_up_and_down(self):
        self.assertEqual(self.mirror(2, 3, 16, True, True),
                         [[2, 3], [13, 3], [2, 12], [13, 12]])

    def test_a_square_in_the_middle_is_not_doubled(self):
        self.assertEqual(self.mirror(8, 8, 17, True, True), [[8, 8]])
        self.assertEqual(self.mirror(8, 3, 17, True, True), [[8, 3], [8, 13]])

    def test_sparkle_is_the_same_for_the_same_square(self):
        first = js("const out=[]; for(let y=0;y<16;y++)for(let x=0;x<16;x++)out.push(A.sparklePart(x,y,16)); return out")
        again = js("const out=[]; for(let y=0;y<16;y++)for(let x=0;x<16;x++)out.push(A.sparklePart(x,y,16)); return out")
        self.assertEqual(first, again)
        self.assertEqual(first, js("const out=[]; for(let y=0;y<16;y++)for(let x=0;x<16;x++)out.push(A.sparklePart(x,y,16)); return out"))

    def test_sparkle_has_about_one_light_in_four_and_one_white_in_twelve(self):
        parts = js("const out=[]; for(let y=0;y<24;y++)for(let x=0;x<24;x++)out.push(A.sparklePart(x,y,24)); return out")
        total = len(parts)
        counts = {name: parts.count(name) for name in ("white", "light", "base")}
        self.assertEqual(sum(counts.values()), total)
        self.assertAlmostEqual(counts["white"] / total, 1 / 12, delta=.05)
        self.assertAlmostEqual(counts["light"] / total, 1 / 4, delta=.08)
        self.assertGreater(counts["base"], total / 2)

    def test_sparkle_works_on_every_canvas_size(self):
        for size in (16, 24, 32, 48):
            with self.subTest(size=size):
                parts = js(f"const out=[]; for(let y=0;y<{size};y++)for(let x=0;x<{size};x++)out.push(A.sparklePart(x,y,{size})); return out")
                self.assertEqual(set(parts), {"white", "light", "base"})


class StudioUsesTheHelpers(unittest.TestCase):
    """A source guard: the studio should not grow a second copy of mirroring."""

    def test_every_mirror_goes_through_one_helper(self):
        with open(os.path.join(FOLDER, "pixel_studio.js"), encoding="utf-8") as f:
            source = f.read()
        self.assertIn("A.mirrorPoints(", source)
        self.assertNotIn("size - 1 - x", source)
        self.assertNotIn("size - 1 - sq.x", source)

    def test_the_three_mirror_buttons_and_sparkle_are_on_the_page(self):
        with open(os.path.join(FOLDER, "pixel.html"), encoding="utf-8") as f:
            page = f.read()
        for button in ('id="mirrorOff"', 'id="mirror"', 'id="mirror4"', 'data-pen="sparkle"'):
            with self.subTest(button=button):
                self.assertIn(button, page)


if __name__ == "__main__":
    unittest.main()
