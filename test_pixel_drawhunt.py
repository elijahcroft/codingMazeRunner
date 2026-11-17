"""Draw-tab bug hunt: the number-aware Fill used by 🔢 By numbers.

While a picture is being coloured by numbers, every unfinished square starts
white, so the ordinary flood fill would run across the whole drawing and paint
all the other numbers' squares too.  PixelArt.floodTarget follows the numbers
under the picture instead, and these tests keep it honest.

The browser checks for the rest of the Draw tab live in tools/e2e_draw.py.
"""
import json
import os
import shutil
import subprocess
import unittest

import pixel


FOLDER = os.path.dirname(os.path.abspath(__file__))


@unittest.skipUnless(shutil.which("node"), "needs node")
class NumberAwareFill(unittest.TestCase):
    """pixel_art.js is plain JavaScript, so node can run it directly."""

    def js(self, code):
        script = (f"const A = require({json.dumps(os.path.join(FOLDER, 'pixel_art.js'))});"
                  f"process.stdout.write(JSON.stringify((() => {{ {code} }})()))")
        return json.loads(subprocess.check_output(["node", "-e", script], timeout=60))

    def test_fill_follows_only_squares_with_the_same_number(self):
        # 4x4: a 1 patch, a 2 patch, a 3 patch.
        target = [1, 1, 2, 2,
                  1, 1, 2, 2,
                  3, 3, 2, 2,
                  3, 3, 2, 2]
        got = self.js(f"return A.floodTarget({json.dumps(target)}, 4, 0, 0, 1).map(([x,y]) => y*4+x).sort((a,b)=>a-b)")
        self.assertEqual(got, [0, 1, 4, 5])

    def test_fill_stops_at_empty_squares(self):
        target = [-1, 1, 1,
                  1, 1, -1,
                  1, -1, 1]
        got = self.js(f"return A.floodTarget({json.dumps(target)}, 3, 1, 0, 1).map(([x,y]) => y*3+x).sort((a,b)=>a-b)")
        self.assertEqual(got, [1, 2, 3, 4, 6])

    def test_fill_does_not_wrap_round_the_edges(self):
        target = [1, 1, 1, 1,
                  1, 2, 2, 1,
                  1, 2, 1, 1,
                  1, 1, 1, 1]
        got = self.js(f"return A.floodTarget({json.dumps(target)}, 4, 0, 3, 1).map(([x,y]) => y*4+x).sort((a,b)=>a-b)")
        self.assertNotIn(5, got)       # (1,1) is the 2 patch
        self.assertIn(0, got)          # the left edge, joined round row 3
        self.assertIn(15, got)         # the right edge, joined round row 0

    def test_an_ordinary_flood_would_have_painted_the_whole_page(self):
        # The page starts white (4) everywhere; the numbers underneath differ.
        target = [1, 1, 2, 2,
                  1, 1, 2, 2,
                  3, 3, 2, 2,
                  3, 3, 2, 2]
        frame = [4] * 16
        everything = self.js(f"return A.flood({json.dumps(frame)}, 4, 0, 0).length")
        only_one = self.js(f"return A.floodTarget({json.dumps(target)}, 4, 0, 0, 1).length")
        self.assertEqual(everything, 16)
        self.assertEqual(only_one, 4)

    def test_every_gallery_pal_has_numbers_to_fill(self):
        script = (f"const A = require({json.dumps(os.path.join(FOLDER, 'pixel_art.js'))});"
                  f"const G = require({json.dumps(os.path.join(FOLDER, 'pixel_gallery.js'))});"
                  "const out = G.names.map(name => {"
                  "  const target = A.decode(A.encode(G.pictures[name]));"
                  "  const base = G.outlined(target);"
                  "  return {name, known: target.every(n => n >= -1 && n < A.PALETTE.length),"
                  "          numbered: new Set(target.filter((n, i) => n >= 0 && n !== base[i])).size};"
                  "});"
                  "process.stdout.write(JSON.stringify(out))")
        pals = json.loads(subprocess.check_output(["node", "-e", script], timeout=60))
        self.assertEqual(len(pals), 26)
        for pal in pals:
            with self.subTest(pal=pal["name"]):
                self.assertTrue(pal["known"])
                self.assertGreaterEqual(pal["numbered"], 1)


class ByNumbersSave(unittest.TestCase):
    """The guide is part of a drawing, so a save and reload keeps it (and a
    finished picture saves with no guide left)."""

    def drawing(self, **extra):
        return dict({"key": "nums01", "title": "Kitty", "size": 16, "speed": 6,
                     "palette": ["#1b1530", "#ffffff", "#ff0000", "#00ff00", "#0000ff"],
                     "frames": ["4" * 256],
                     "names": [""], "guide": "0" * 256}, **extra)

    def test_a_guide_is_kept_and_a_finished_picture_clears_it(self):
        drawings = []
        self.assertIsNone(pixel.save_drawing(drawings, self.drawing()))
        self.assertEqual(drawings[0]["guide"], "0" * 256)
        self.assertIsNone(pixel.save_drawing(drawings, self.drawing(
            frames=["0" * 256], guide="")))
        self.assertEqual(len(drawings), 1)
        self.assertEqual(drawings[0]["frames"], ["0" * 256])
        self.assertEqual(drawings[0]["guide"], "")


if __name__ == "__main__":
    unittest.main()
