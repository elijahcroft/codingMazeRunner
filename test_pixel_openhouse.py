"""🎉 Open house: invite the whole Hang out into your home for a couple of minutes.

The tests use the same little class and clock as the other Hang out tests. They
check the one-tap invite, landing in the host's home, hearts, the class limits,
the host cool-down, the two ways a host can end it, and the teacher's Hang out
card. Nothing here touches the browser: the client is checked with tools/e2e.
"""
import unittest

import pixel
import server
from test_pixel_fun import Fun


class OpenHouse(Fun):
    def seat(self, p):
        return self.spot(p)["seat"]

    def ready_home(self, p, things=3):
        """Walk into your own home and put out 3 things (or as many as asked)."""
        self.do(p, "home")
        self.entry(p)["stuff"] += ["lamp", "teddy", "balloons"]
        for key, x in (("rug", 60), ("plant", 90), ("lamp", 120))[:things]:
            out = self.do(p, "furnish", key=key, x=x, y=.5)
            self.assertTrue(out.get("ok"), out)
        self.assertEqual(len(self.entry(p)["home"]["items"]), things)

    def start(self, p):
        return self.do(p, "openhouse", action="start")

    def join(self, p, host):
        return self.do(p, "openhouse", action="join", host=self.seat(host))

    def close(self, p):
        return self.do(p, "openhouse", action="close")

    def recent(self, kind, phase=None):
        return [e for e in server.pixel_room["events"]
                if e["kind"] == kind and (phase is None or e.get("phase") == phase)]

    def test_a_home_needs_three_things_out_before_it_can_open(self):
        self.do(self.mia, "home")
        self.entry(self.mia)["stuff"] += ["lamp"]
        for key, x in (("rug", 60), ("plant", 90)):
            self.assertTrue(self.do(self.mia, "furnish", key=key, x=x, y=.5)["ok"])
        out = self.start(self.mia)
        self.assertIn("3 things", out["error"])
        self.assertFalse(server.pixel_room["openhouses"])
        self.assertTrue(self.do(self.mia, "furnish", key="lamp", x=120, y=.5)["ok"])
        self.assertTrue(self.start(self.mia)["ok"])

    def test_the_invite_reaches_everyone_in_the_hang_out_and_fades(self):
        self.ready_home(self.mia)
        before = server.pixel_room["seq"]
        out = self.start(self.mia)
        self.assertTrue(out["ok"])
        seat = self.seat(self.mia)
        for other in (self.ben, self.alex):
            invite = self.view(other)["house_invite"]
            self.assertEqual((invite["seat"], invite["name"]), (seat, "Mia"))
            self.assertLessEqual(invite["left"], server.OPENHOUSE_INVITE_SECONDS)
            self.assertGreater(invite["left"], 0)
        self.assertIsNone(self.view(self.mia)["house_invite"])          # the host doesn't invite themself
        event = next(e for e in server.pixel_room["events"] if e["n"] > before and e["kind"] == "openhouse")
        self.assertEqual(event["phase"], "invite")
        self.assertEqual(event["moment"], "openhouse")                 # Auto on the projector can visit
        self.assertEqual(event["host_name"], "Mia")
        self.assertNotIn("private-", repr(self.view(self.ben)))
        self.advance(server.OPENHOUSE_INVITE_SECONDS + 1)
        self.assertIsNone(self.view(self.ben)["house_invite"])
        self.assertTrue(server.pixel_room["openhouses"])               # the house is still open
        self.assertIn("invite_end", [e.get("phase") for e in self.recent("openhouse")])

    def test_a_host_does_not_get_another_hosts_invite(self):
        # Walking out to a friend's open house would quietly close your own.
        self.ready_home(self.mia)
        self.assertTrue(self.start(self.mia)["ok"])
        self.ready_home(self.ben)
        self.assertTrue(self.start(self.ben)["ok"])
        self.assertIsNone(self.view(self.mia)["house_invite"])
        self.assertIsNone(self.view(self.ben)["house_invite"])
        self.assertIsNotNone(self.view(self.alex)["house_invite"])

    def test_tapping_the_invite_lands_in_the_host_home_and_hearts_still_work(self):
        self.ready_home(self.mia)
        home_id = server.home_of(self.entry(self.mia))["id"]
        self.assertTrue(self.start(self.mia)["ok"])
        coins = self.entry(self.mia)["coins"]
        before = server.pixel_room["seq"]
        self.assertTrue(self.join(self.ben, self.mia)["ok"])
        self.assertEqual(self.spot(self.ben)["loc"], home_id)
        home = self.view(self.ben)["home"]
        self.assertEqual((home["name"], home["mine"]), ("Mia", False))
        house = self.view(self.ben)["openhouse"]
        self.assertEqual((house["name"], house["count"], house["mine"]), ("Mia", 1, False))
        self.assertEqual(self.view(self.mia)["openhouse"]["count"], 1)
        self.assertTrue(self.view(self.mia)["openhouse"]["mine"])
        self.assertIsNone(self.view(self.ben)["house_invite"])          # the invite is used up
        self.assertIsNotNone(self.view(self.alex)["house_invite"])      # Alex can still come
        # The host's pal waves and the first arrival gets light confetti.
        events = [e for e in server.pixel_room["events"] if e["n"] > before]
        arrival = next(e for e in events if e["kind"] == "openhouse" and e.get("phase") == "arrive")
        self.assertEqual((arrival["guest_name"], arrival["count"], arrival["confetti"]), ("Ben", 1, True))
        self.assertTrue(any(e["kind"] == "fx" and e["name"] == "confetti" for e in events))
        self.assertTrue(any(e["kind"] == "move" and e["seat"] == self.seat(self.mia) and e["name"] == "wave"
                            for e in events))
        # A guest still gives the home their usual one heart, and the owner is paid.
        self.assertTrue(self.do(self.ben, "heart")["ok"])
        self.assertEqual(self.entry(self.mia)["coins"], coins + pixel.COINS_HEART)
        self.assertIn("already", self.do(self.ben, "heart")["error"])

    def test_at_most_two_open_houses_and_only_one_for_each_host(self):
        for kid in (self.mia, self.ben, self.alex):
            self.ready_home(kid)
        self.assertTrue(self.start(self.mia)["ok"])
        self.assertIn("already", self.start(self.mia)["error"])
        self.assertTrue(self.start(self.ben)["ok"])
        self.assertIn("Two open houses", self.start(self.alex)["error"])
        self.assertEqual(len(server.pixel_room["openhouses"]), 2)
        self.assertNotIn("Two open houses", repr(self.view(self.alex)))

    def test_a_host_waits_five_minutes_after_closing(self):
        self.ready_home(self.mia)
        self.assertTrue(self.start(self.mia)["ok"])
        self.assertTrue(self.close(self.mia)["ok"])
        self.assertFalse(server.pixel_room["openhouses"])
        self.assertIn("just ended", self.start(self.mia)["error"])
        self.assertGreater(self.view(self.mia)["home"]["house_cool"], 0)
        self.advance(server.OPENHOUSE_COOLDOWN - 2)
        self.assertIn("just ended", self.start(self.mia)["error"])
        self.advance(3)
        self.assertEqual(self.view(self.mia)["home"]["house_cool"], 0)
        self.assertTrue(self.start(self.mia)["ok"])

    def test_host_leaving_home_ends_the_open_house(self):
        self.ready_home(self.mia)
        home_id = server.home_of(self.entry(self.mia))["id"]
        self.assertTrue(self.start(self.mia)["ok"])
        self.assertTrue(self.join(self.ben, self.mia)["ok"])
        self.assertTrue(self.do(self.mia, "home", out=True)["ok"])
        self.assertFalse(server.pixel_room["openhouses"])
        self.assertIsNone(self.view(self.ben)["openhouse"])
        self.assertEqual(self.spot(self.ben)["loc"], home_id)           # Ben is still in the room
        self.assertIn("end", [e.get("phase") for e in self.recent("openhouse")])
        self.assertFalse(self.start(self.mia).get("ok"))               # she is outside now

    def test_host_leaving_the_hang_out_ends_it_too(self):
        self.ready_home(self.mia)
        self.assertTrue(self.start(self.mia)["ok"])
        self.assertTrue(self.do(self.mia, "leave")["ok"])
        self.assertFalse(server.pixel_room["openhouses"])
        self.assertFalse(self.start(self.mia).get("ok"))               # she isn't in the Hang out now

    def test_closing_the_hang_out_clears_every_open_house(self):
        self.ready_home(self.mia)
        self.ready_home(self.ben)
        self.assertTrue(self.start(self.mia)["ok"])
        self.assertTrue(self.start(self.ben)["ok"])
        self.assertEqual(len(server.pixel_overview()["room"]["open_houses"]), 2)
        server.room_set(False)
        self.assertFalse(server.pixel_room["openhouses"])
        self.assertFalse(server.pixel_overview()["room"]["open_houses"])
        server.room_set(True)
        self.assertFalse(server.pixel_room["openhouses"])
        self.assertFalse(server.pixel_overview()["room"]["open_houses"])

    def test_it_ends_by_itself_after_about_two_minutes(self):
        self.ready_home(self.mia)
        self.assertTrue(self.start(self.mia)["ok"])
        self.advance(server.OPENHOUSE_SECONDS - 2)
        self.assertTrue(server.pixel_room["openhouses"])
        self.advance(3)
        self.assertFalse(server.pixel_room["openhouses"])
        self.assertIn("time", [e.get("reason") for e in self.recent("openhouse", "end")])
        self.assertIn("just ended", self.start(self.mia)["error"])

    def test_confetti_is_light_when_a_group_arrives(self):
        self.ready_home(self.mia)
        self.assertTrue(self.start(self.mia)["ok"])
        self.assertTrue(self.join(self.ben, self.mia)["ok"])
        self.assertTrue(self.join(self.alex, self.mia)["ok"])
        arrivals = self.recent("openhouse", "arrive")
        self.assertEqual([e["confetti"] for e in arrivals], [True, False])
        self.assertEqual([e["count"] for e in arrivals], [1, 2])
        self.assertEqual(len([e for e in self.recent("fx") if e.get("name") == "confetti"]), 1)
        self.assertEqual(len([e for e in self.recent("move") if e.get("name") == "wave"]), 2)

    def test_secret_pal_hides_the_host_name_everywhere_public(self):
        self.entry(self.mia)["hide_name"] = True
        self.ready_home(self.mia)
        self.assertTrue(self.start(self.mia)["ok"])
        invite = self.view(self.ben)["house_invite"]
        self.assertEqual(invite["name"], "Secret pal")
        self.assertNotIn("Mia", repr(invite))
        self.assertEqual(server.pixel_overview()["room"]["open_houses"][0]["name"], "Secret pal")
        self.assertTrue(self.join(self.ben, self.mia)["ok"])
        arrival = self.recent("openhouse", "arrive")[-1]
        self.assertEqual(arrival["host_name"], "Secret pal")
        self.assertEqual(self.view(self.ben)["openhouse"]["name"], "Secret pal")

    def test_the_host_gets_a_small_once_a_day_treat_only_when_friends_came(self):
        self.ready_home(self.mia)
        self.assertTrue(self.start(self.mia)["ok"])
        self.assertTrue(self.close(self.mia)["ok"])
        self.assertEqual(self.entry(self.mia)["coins"], 0)              # no visitors, no treat
        self.advance(server.OPENHOUSE_COOLDOWN + 1)
        self.assertTrue(self.start(self.mia)["ok"])
        self.assertTrue(self.join(self.ben, self.mia)["ok"])
        self.assertTrue(self.close(self.mia)["ok"])
        self.assertEqual(self.entry(self.mia)["coins"], pixel.COINS_OPENHOUSE)
        self.advance(server.OPENHOUSE_COOLDOWN + 1)
        self.assertTrue(self.do(self.ben, "home", out=True)["ok"])      # Ben goes back outside for a new invite
        self.assertTrue(self.start(self.mia)["ok"])
        self.assertTrue(self.join(self.ben, self.mia)["ok"])
        self.assertTrue(self.close(self.mia)["ok"])
        self.assertEqual(self.entry(self.mia)["coins"], pixel.COINS_OPENHOUSE)      # once a day

    def test_the_class_projector_can_visit_the_open_house_moment(self):
        self.ready_home(self.mia)
        home_id = server.home_of(self.entry(self.mia))["id"]
        after = server.pixel_room["seq"]
        self.assertTrue(self.start(self.mia)["ok"])
        # The projector is watching a different home, but the start is a class moment.
        events = server.room_view(None, after, home_id)["events"]
        start = next(e for e in events if e["kind"] == "openhouse")
        self.assertEqual((start["moment"], start["home"], start["host_name"]), ("openhouse", home_id, "Mia"))
        self.assertEqual(server.room_view(None, -1, home_id)["openhouse"]["count"], 0)


if __name__ == "__main__":
    unittest.main()
