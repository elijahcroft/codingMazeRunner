"""The six starter pals added to the Draw gallery: Fox, Octopus, Alien, Ghost,
Dragon and Ladybug. Each one must look right in the gallery and come alive."""
import json
import os
import shutil
import subprocess
import unittest

NEW = ["Fox", "Octopus", "Alien", "Ghost", "Dragon", "Ladybug"]


@unittest.skipUnless(shutil.which("node"), "needs node")
class TheNewGalleryPals(unittest.TestCase):
    """pixel_gallery.js is plain JavaScript, so node can read it directly."""

    def js(self, code):
        folder = os.path.dirname(os.path.abspath(__file__))
        need = "".join(f"const {name} = require({json.dumps(os.path.join(folder, file))});"
                       for name, file in (("A", "pixel_art.js"), ("R", "pixel_rig.js"), ("G", "pixel_gallery.js")))
        script = need + f"process.stdout.write(JSON.stringify((() => {{ {code} }})()))"
        return json.loads(subprocess.check_output(["node", "-e", script], timeout=120))

    def pals(self):
        return self.js(f"""
            return {json.dumps(NEW)}.map(name => {{
                const f = G.pictures[name], rig = R.build(f, 16, A.PALETTE);
                const base = G.outlined(f), count = kind => rig.limbs.filter(l => l.kind === kind).length;
                return {{name, length: f.length,
                         known: f.every(n => Number.isInteger(n) && n >= -1 && n < A.PALETTE.length),
                         colours: new Set(f.filter((n, i) => n !== base[i])).size,
                         eyes: rig.eyes.length, mouth: !!rig.mouth,
                         arm: count("arm"), leg: count("leg")}};
            }})""")

    def test_the_six_new_pals_join_the_gallery(self):
        gallery = self.js("return {names: G.names, furniture: G.furniture}")
        names = gallery["names"]
        self.assertEqual(len(names), 26)
        for name in NEW:
            with self.subTest(pal=name):
                self.assertIn(name, names)
                self.assertNotIn(name, gallery["furniture"])

    def test_every_new_pal_is_a_whole_sixteen_square_picture(self):
        for pal in self.pals():
            with self.subTest(pal=pal["name"]):
                self.assertEqual(pal["length"], 256)
                self.assertTrue(pal["known"])
                self.assertGreaterEqual(pal["colours"], 2)   # enough to colour by numbers

    def test_every_new_pal_has_a_face_legs_and_arms(self):
        for pal in self.pals():
            with self.subTest(pal=pal["name"]):
                self.assertGreaterEqual(pal["eyes"], 2, "needs a pair of clear eyes")
                self.assertTrue(pal["mouth"], "needs a mouth under the eyes")
                self.assertGreaterEqual(pal["leg"], 2, "needs legs or feet, so it can walk")
                self.assertGreaterEqual(pal["arm"], 2, "needs arms, so it can wave")

    def test_the_guide_counts_the_six_new_pals(self):
        folder = os.path.dirname(os.path.abspath(__file__))
        with open(os.path.join(folder, "PIXEL_PALS_GUIDE.md"), encoding="utf-8") as fh:
            guide = fh.read()
        self.assertIn("one of 26 pals from the gallery", guide)


if __name__ == "__main__":
    unittest.main()
