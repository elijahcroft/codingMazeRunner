"""🛍️ The gentle "you can buy something!" nudge for a student sitting on coins.

The line is drawn by the browser, but who sees it is decided from the student's
entry: enough coins for the cheapest Shop thing, and nothing bought yet. A buy
stops it for good. These tests check the server half and what each kind of
student is sent; the small-screen look is checked by tools/e2e_coinnudge.py.
"""
import unittest

import pixel
import server
from test_pixel_fun import Fun


class CoinNudge(Fun):
    def nudge(self, p):
        return self.view(p)["shop_nudge"]

    def test_the_cheapest_thing_in_the_shop_is_the_first_they_can_afford(self):
        self.assertEqual(pixel.SHOP_CHEAPEST, min(item["price"] for item in pixel.SHOP.values()))
        self.assertEqual(pixel.SHOP_CHEAPEST, 15)     # the little rubber duck / balloons

    def test_a_student_with_enough_coins_and_nothing_bought_is_nudged(self):
        self.entry(self.mia)["coins"] = pixel.SHOP_CHEAPEST
        self.assertTrue(self.nudge(self.mia))
        self.assertTrue(server.pixel_state(self.mia)["hang"]["shop_nudge"])
        self.entry(self.mia)["coins"] = 150
        self.assertTrue(self.nudge(self.mia))

    def test_a_student_with_too_few_coins_is_not_nudged(self):
        self.entry(self.mia)["coins"] = pixel.SHOP_CHEAPEST - 1
        self.assertFalse(self.nudge(self.mia))
        self.assertFalse(server.pixel_state(self.mia)["hang"]["shop_nudge"])

    def test_buying_wear_ends_the_nudge_for_good(self):
        self.entry(self.mia)["coins"] = 200
        self.assertTrue(self.do(self.mia, "buy", key="beanie")["ok"])
        self.assertIn("beanie", self.entry(self.mia)["gifts"])
        self.assertFalse(self.nudge(self.mia))
        self.entry(self.mia)["coins"] = 500          # more coins later don't bring it back
        self.assertFalse(self.nudge(self.mia))

    def test_buying_furniture_ends_the_nudge_for_good(self):
        self.entry(self.mia)["coins"] = 200
        self.assertTrue(self.do(self.mia, "buy", key="balloons")["ok"])
        self.assertIn("balloons", self.entry(self.mia)["stuff"])
        self.assertFalse(self.nudge(self.mia))

    def test_buying_a_wall_or_a_room_also_ends_the_nudge(self):
        self.entry(self.mia)["coins"] = 300
        self.assertTrue(self.do(self.mia, "buy", key="w_pink")["ok"])
        self.assertFalse(self.nudge(self.mia))
        self.entry(self.ben)["coins"] = 300
        self.assertTrue(self.do(self.ben, "buy", key="r_kitchen")["ok"])
        self.assertFalse(self.nudge(self.ben))

    def test_box_gifts_and_home_prizes_are_not_buying(self):
        self.entry(self.mia)["coins"] = 100
        self.entry(self.mia)["gifts"].append("party")       # a mission's gift box
        self.entry(self.mia)["stuff"].append("trophy")      # a home level prize
        self.assertTrue(self.nudge(self.mia))

    def test_wearing_your_own_drawing_is_buying(self):
        self.entry(self.mia)["coins"] = 100
        self.entry(self.mia)["mywear"].append({"key": "my:1", "slot": "hat", "name": "My hat", "art": {}})
        self.assertFalse(self.nudge(self.mia))

    def test_the_projector_has_no_nudge(self):
        self.entry(self.mia)["coins"] = 150
        self.assertNotIn("shop_nudge", self.view(None))     # the class screen has no student rows


if __name__ == "__main__":
    unittest.main()
