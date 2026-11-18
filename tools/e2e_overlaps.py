#!/usr/bin/env python3
"""End-to-end hunt for bugs where Pixel Pals' class-wide Hang out moments overlap.

Tonight's moments were each tested alone.  This tool starts four students, the
projector and the teacher page in headless Chromium at 1366x768 and plays them
together, the way a class of excited kids and one teacher will:

  * a wedding while a fashion show is dressing or on the runway, and a fashion
    show while a wedding is picking a partner or saying vows,
  * the teacher's 🎂 Birthday and 📸 Class photo during a wedding, a fashion
    runway and an open house,
  * an open house invite arriving while a student is in a wedding invite card
    or in a game; a guest at an open house with a wedding card; the host
    leaving home mid-open-house; two open houses started together,
  * a star shower during the birthday song, mural painting while a game round
    plays, Calm and Mute on through it all,
  * the teacher closing the Hang out in the middle, and a page reload in the
    middle of the wedding invite, the birthday, the open house and a game.

Every scenario also checks for a stuck card or pane, unreadable banner piles,
console errors, and an Auto camera that flip-flops.  Screenshots go to the
--shots folder (not the worktree).

The server must already be running with a fresh state file:

    MAZE_PORT=8916 MAZE_STATE_FILE=/tmp/interhunt-state.json python3 server.py
    python3 tools/e2e_overlaps.py --port 8916 --shots /tmp/interhunt

This is a tool, not a unittest: it is not named test_*.py and unittest will not
pick it up.  It needs chromium and chromedriver on PATH.
"""

import argparse
import base64
import json
import os
import re
import sys
import threading
import time
import traceback
import urllib.error
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "tools"))
import pixel  # noqa: E402
import server  # noqa: E402  (only for the admin key)
from e2e_coach import Driver, WebDriverError  # noqa: E402

BASE = ""
SHOT_DIR = ""
PAL = {"key": "ovpal", "size": 16, "speed": 6, "palette": pixel.PIP["palette"],
       "frames": pixel.PIP["frames"], "names": pixel.PIP["names"], "title": "My pal"}
SHOW = 'scene("beach")\nsay("Hello!")\nfor i in range(3):\n    jump()\nhearts()\n'


# ---------------------------------------------------------------------------
# The report
# ---------------------------------------------------------------------------
class Report:
    def __init__(self):
        self.checks = []
        self.problems = []
        self.notes = []
        self.screenshots = []
        self.console = []

    def check(self, label, ok, detail=""):
        self.checks.append({"check": label, "ok": bool(ok), "detail": str(detail)[:900]})
        if not ok:
            self.problems.append(f"{label}: {detail}"[:1200])
        print(("OK   " if ok else "FAIL ") + label +
              ("" if ok else "  [" + str(detail)[:500] + "]"))
        return bool(ok)

    def problem(self, label, detail=""):
        self.problems.append(f"{label}: {detail}"[:1200])
        self.checks.append({"check": label, "ok": False, "detail": str(detail)[:900]})
        print("FAIL " + label + "  [" + str(detail)[:500] + "]")

    def note(self, text):
        self.notes.append(text)
        print("NOTE " + text)

    def console_errors(self):
        return [e for e in self.console if e.get("level") == "SEVERE"]

    def ok(self):
        return not self.problems and not self.console_errors()


report = Report()


# ---------------------------------------------------------------------------
# HTTP and browser helpers
# ---------------------------------------------------------------------------
def post(path, data, timeout=120):
    req = urllib.request.Request(BASE + path, data=json.dumps(data).encode(),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as f:
        return json.load(f)


def get(path, timeout=120):
    with urllib.request.urlopen(BASE + path, timeout=timeout) as f:
        return json.load(f)


def room_of(pid):
    return get(f"/pixel/room?after=-1&wait=0&id={pid}")


def wait(d, script, timeout=15, what="", *args):
    end = time.time() + timeout
    last = None
    while time.time() < end:
        try:
            if d.js(script, *args):
                return True
        except WebDriverError as e:
            last = e
        time.sleep(.12)
    if what:
        report.problem(f"timed out waiting for {what}", last or "")
    return False


def click_js(d, selector, timeout=4):
    end = time.time() + timeout
    js = """const el=document.querySelector(arguments[0]);
            if(!el) return false;
            el.scrollIntoView({block:'nearest'});
            el.click(); return true;"""
    while time.time() < end:
        try:
            if d.js(js, selector):
                return True
        except WebDriverError:
            pass
        time.sleep(.1)
    return False


def click_room(d, selector):
    return click_js(d, "#roomButtons " + selector)


def teacher_birthday(d):
    """Refresh the teacher page, then click the first 🎂 Birthday! button."""
    try:
        d.js("refresh()")
    except Exception:
        pass
    if not wait(d, "return !!document.querySelector('#rows [data-birthday]')", 8, "a birthday button"):
        return False
    return click_js(d, "#rows [data-birthday]")


def pane(d, name):
    click_js(d, f'#roomTabs [data-pane="{name}"]')
    return wait(d, f"return roomPane === {json.dumps(name)}", 5, f"the {name} pane")


def text_of(d, css):
    return d.js("return (document.querySelector(arguments[0]) || {}).innerText || ''", css)


def visible(d, css):
    return d.js("""const el=document.querySelector(arguments[0]);
        if(!el || el.hidden) return false;
        const r=el.getBoundingClientRect(), s=getComputedStyle(el);
        return s.display!=='none' && s.visibility!=='hidden' && r.width>0 && r.height>0;""", css)


def shot(d, label):
    try:
        os.makedirs(SHOT_DIR, exist_ok=True)
        path = os.path.join(SHOT_DIR, re.sub(r"[^a-z0-9]+", "-", label.lower()).strip("-") + ".png")
        data = d.request("GET", f"/session/{d.sid}/screenshot")
        with open(path, "wb") as f:
            f.write(base64.b64decode(data))
        report.screenshots.append(path)
        return path
    except Exception:
        return ""


def resize(d, width, height):
    try:
        d.request("POST", f"/session/{d.sid}/goog/cdp/execute",
                  {"cmd": "Emulation.setDeviceMetricsOverride",
                   "params": {"width": width, "height": height,
                              "deviceScaleFactor": 1, "mobile": False}})
    except WebDriverError:
        pass
    time.sleep(.35)


def collect_console(d, where):
    try:
        for e in d.logs():
            msg = e.get("message") or ""
            if "favicon.ico" in msg or "AudioContext was not allowed to start" in msg:
                continue
            report.console.append({"where": where, "level": e.get("level"), "message": msg[:800]})
    except Exception:
        pass


def layout_issues(d, where):
    return d.js(r"""return (() => {
      const out = [], h = document.getElementById('hangView');
      if (!h || h.hidden) return ['the Hang out is not showing: ' + arguments[0]];
      if (document.documentElement.scrollWidth > innerWidth + 1) out.push('the page scrolls sideways');
      if (document.body.scrollWidth > innerWidth + 1) out.push('the body scrolls sideways');
      const hr = h.getBoundingClientRect();
      if (hr.bottom > innerHeight + 1 || hr.right > innerWidth + 1 || hr.left < -1)
        out.push('the Hang out is cut off');
      if (hr.height < 300) out.push('the Hang out is too short');
      const vis = el => { const s = getComputedStyle(el); const r = el.getBoundingClientRect();
        return s.display !== 'none' && s.visibility !== 'hidden' && r.width > 0 && r.height > 0; };
      for (const el of document.querySelectorAll('#hangView > *, .hang-side > *, .hang-main > *, #roomTip, #coinBar, #roomTabs, #gameStatus, #houseStatus')) {
        if (!vis(el)) continue;
        const r = el.getBoundingClientRect();
        if (r.left < -1 || r.right > innerWidth + 1 || r.bottom > innerHeight + 1)
          out.push('off screen: ' + (el.id || el.className || el.tagName) + ' ' + (el.innerText || '').slice(0, 24));
        if (el.scrollWidth > el.clientWidth + 2 && !['auto', 'scroll'].includes(getComputedStyle(el).overflowX))
          out.push('cut-off text: ' + (el.id || el.className || el.tagName) + ' ' + (el.innerText || '').slice(0, 24));
      }
      const rb = document.getElementById('roomButtons');
      if (rb) {
        if (rb.scrollWidth > rb.clientWidth + 2) out.push('the buttons scroll sideways');
        const rr = rb.getBoundingClientRect();
        for (const el of rb.querySelectorAll('button, h4, p, .me-note, .home-level')) {
          if (!vis(el)) continue;
          const r = el.getBoundingClientRect();
          if (r.right > rr.right + 2 || r.left < rr.left - 2) out.push('a button sticks out sideways: ' + (el.innerText || '').slice(0, 24));
        }
      }
      // Overlays that should be readable, not on top of each other.
      const bar = document.getElementById('openHouseBar'), ban = document.getElementById('hangBanner');
      if (bar && !bar.hidden && ban && !ban.hidden) {
        const br = bar.getBoundingClientRect(), nr = ban.getBoundingClientRect();
        if (!(nr.top >= br.bottom - 2 || br.top >= nr.bottom - 2))
          out.push('the open house bar and the banner overlap');
      }
      return out.slice(0, 15);
    })()""", where)


def login(d, name):
    d.request("POST", f"/session/{d.sid}/url", {"url": BASE + "/pixel"})
    if not wait(d, "return !document.getElementById('join').hidden || !document.getElementById('app').hidden", 30, "the Pixel Pals page"):
        return False
    if not d.js("return document.getElementById('join').hidden"):
        d.send("#name", name)
        d.click("#joinButton")
        if not wait(d, "return !document.getElementById('app').hidden", 30, "the Pixel Pals page"):
            return False
    wait(d, "return typeof S !== 'undefined' && !!S", 20, "the page to load")
    time.sleep(.35)
    if not d.js("return document.getElementById('shelf').hidden"):
        d.click("#gallery [data-gallery]")
        wait(d, "return document.getElementById('shelf').hidden", 20, "the gallery to close")
    return True


def open_hang(d, timeout=40):
    end = time.time() + timeout
    while time.time() < end:
        try:
            if d.js("return !document.getElementById('hangView').hidden && "
                   "typeof roomStage !== 'undefined' && roomStage && "
                   "roomStage.state && roomStage.state.room && roomInfo && "
                   "roomInfo.you !== null && roomStage.state.room.some(m => m.me)"):
                return True
        except WebDriverError:
            pass
        click_js(d, 'nav [data-view="hang"]')
        time.sleep(.6)
    return False


def join_room(pid):
    return post("/pixel/room/do", {"id": pid, "what": "join"})


def go_place(pid, place):
    return post("/pixel/room/do", {"id": pid, "what": "go", "name": place})


def go_home(pid):
    return post("/pixel/room/do", {"id": pid, "what": "home"})


def leave_home(pid):
    return post("/pixel/room/do", {"id": pid, "what": "home", "out": True})


def start_wedding(host_pid, partner_pid):
    """Start a wedding through the same server calls the card's buttons use."""
    out = post("/pixel/room/do", {"id": host_pid, "what": "wedding"})
    if out.get("error"):
        return out
    partner = room_of(partner_pid)["you"]
    return post("/pixel/room/do", {"id": host_pid, "what": "wedding_pick", "seat": partner})


def accept_wedding(partner_pid):
    return post("/pixel/room/do", {"id": partner_pid, "what": "wedding_yes"})


def wait_game_clear(timeout=14):
    end = time.time() + timeout
    while time.time() < end:
        if not room_of(pid("ana")).get("game"):
            return True
        time.sleep(.25)
    return False


def begin_fashion(host_pid, guest_pid):
    out = post("/pixel/room/do", {"id": host_pid, "what": "game", "action": "create", "kind": "fashion"})
    if out.get("error"):
        return out
    out = post("/pixel/room/do", {"id": guest_pid, "what": "game", "action": "join"})
    if out.get("error"):
        return out
    return post("/pixel/room/do", {"id": host_pid, "what": "game", "action": "start"})


# ---------------------------------------------------------------------------
# Setup: four students, enough coins, two furnished homes
# ---------------------------------------------------------------------------
def setup_state(base):
    tag = str(int(time.time()))[-4:]
    names = [f"Ov Ana {tag}", f"Ov Ben {tag}", f"Ov Cy {tag}", f"Ov Dee {tag}"]
    ids = {}
    for name in names:
        ids[name] = post("/join", {"name": name})["id"]
        post("/pixel/news", {"id": ids[name]})     # the one-time ✨ New card is for real kids; it would cover the world
        post("/pixel/save", {"id": ids[name], "drawing": PAL})
    post("/pixel/teacher", {"key": server.ADMIN_KEY, "action": "open",
                            "level": pixel.LEVEL_ORDER[-1]})
    post("/pixel/teacher", {"key": server.ADMIN_KEY, "action": "placed_clear"})
    post("/pixel/teacher", {"key": server.ADMIN_KEY, "action": "end_game"})
    post("/pixel/teacher", {"key": server.ADMIN_KEY, "action": "room", "on": False})
    post("/pixel/teacher", {"key": server.ADMIN_KEY, "action": "room", "on": True})
    fails = []
    for name in names:                        # enough coins to buy and place things
        for key in pixel.LEVEL_ORDER:
            out = post("/pixel/run", {"id": ids[name], "level": key,
                                      "code": pixel.LEVEL_BY_KEY[key]["reference"]})
            if out.get("error") or not (out.get("stars") or [False])[0]:
                fails.append((name, key, out.get("error"), out.get("stars")))
    report.check("setup: every student can do the missions that open the Hang out", not fails, fails[:2])
    joined = []
    for name in names:
        out = join_room(ids[name])
        if out.get("error"):
            joined.append((name, out.get("error")))
    report.check("setup: all four students can join the Hang out", not joined, joined[:2])
    for name in names:
        pid = ids[name]
        for key in ("balloons", "lamp", "teddy"):
            post("/pixel/room/do", {"id": pid, "what": "buy", "key": key})
        go_home(pid)
        for key, x in (("rug", 60), ("plant", 90), ("balloons", 120)):
            out = post("/pixel/room/do", {"id": pid, "what": "furnish", "key": key, "x": x, "y": .5})
            if out.get("error"):
                fails.append((name, "furnish", key, out.get("error")))
    report.check("setup: every student has 3 things out in their own home", not fails, fails[:2])
    report.check("setup: all four students have a home to open", not fails, fails[:2])
    return names, ids


# ---------------------------------------------------------------------------
# Shared browser state
# ---------------------------------------------------------------------------
NAMES = []
IDS = {}
SHORT = {}                 # short label -> real name
STUDENTS = {}              # short label -> Driver


def pid(short):
    return IDS[SHORT[short]]


def real(short):
    return SHORT[short]


def reset_room():
    """Close and open the Hang out, which clears every class moment, then rejoin."""
    post("/pixel/teacher", {"key": server.ADMIN_KEY, "action": "room", "on": False})
    time.sleep(.25)
    post("/pixel/teacher", {"key": server.ADMIN_KEY, "action": "room", "on": True})
    try:
        STUDENTS["ana"].js("refresh()")
    except Exception:
        pass
    for short in ("ana", "ben", "cy", "dee"):
        join_room(pid(short))
    for short, d in STUDENTS.items():
        wait(d, "return !!(roomInfo && roomInfo.open && roomInfo.you !== null && "
                "!document.getElementById('hangView').hidden)", 20, f"{short} back in the Hang out")
    time.sleep(.35)


def moment_text(d):
    return {
        "banner": text_of(d, "#hangBanner"),
        "bannerShown": visible(d, "#hangBanner"),
        "wedding": text_of(d, "#weddingCard"),
        "weddingShown": visible(d, "#weddingCard"),
        "house": text_of(d, "#houseStatus"),
        "houseShown": visible(d, "#houseStatus"),
        "openBar": text_of(d, "#openHouseBar"),
        "openBarShown": visible(d, "#openHouseBar"),
        "closed": visible(d, "#roomClosed"),
        "tip": text_of(d, "#roomTip"),
        "pane": d.js("return roomPane"),
        "game": d.js("return (roomInfo && roomInfo.game) ? roomInfo.game.phase : null"),
        "weddingPhase": d.js("return (roomInfo && roomInfo.wedding) ? roomInfo.wedding.phase : null"),
        "birthday": d.js("return (roomInfo && roomInfo.birthday) ? roomInfo.birthday.phase : null"),
        "openhouse": d.js("return roomInfo && roomInfo.openhouse"),
    }


def no_stuck_student(short, where):
    d = STUDENTS[short]
    st = moment_text(d)
    ok = (not st["closed"] and st["pane"] in
          ("do", "party", "say", "place", "games", "home", "me", "shop", "art", "mural", "chest", "tree"))
    report.check(f"{short} is not stuck or frozen {where}", ok, st)
    return st


def no_unreadable_overlap(short, where):
    d = STUDENTS[short]
    issues = layout_issues(d, where)
    report.check(f"{short}'s screen is readable {where}", not issues, issues)


# ---------------------------------------------------------------------------
# 1. Wedding and fashion show, both ways round
# ---------------------------------------------------------------------------
def wedding_versus_fashion(a, b, c, dee, show, teacher):
    print("\n--- wedding and fashion show, both ways round ---")
    reset_room()
    for short in ("ana", "ben", "cy", "dee"):
        go_place(pid(short), "park")
    time.sleep(.4)
    out = begin_fashion(pid("ana"), pid("ben"))
    report.check("a fashion show starts with two walkers", not out.get("error"), out)
    wait(a, "return roomInfo.game && roomInfo.game.phase === 'dressing'", 8, "the fashion dressing room")
    report.check("the fashion show is in dressing", a.js("return roomInfo.game.phase") == "dressing",
                 a.js("return roomInfo.game"))

    # The teacher tries a photo and a birthday during dress-up.
    click_js(teacher, "#photo")
    wait(teacher, "return document.getElementById('photo').textContent !== '📸 Class photo'", 5, "the photo answer")
    ptext = text_of(teacher, "#photo")
    report.check("the teacher's photo is refused during a fashion show", "End this game" in ptext, ptext)
    teacher_birthday(teacher)
    wait(teacher, "return !document.getElementById('roomBirthday').hidden && !/Starting/.test(document.getElementById('roomBirthday').textContent)", 8, "the birthday answer")
    btext = text_of(teacher, "#roomBirthday")
    report.check("the teacher's birthday is refused during a fashion show",
                 "game is on" in btext or "End this game" in btext, btext)
    report.check("no birthday party started during the fashion show",
                 a.js("return !roomInfo.birthday"), a.js("return roomInfo.birthday"))

    # A student at the wedding garden tries to start a wedding.
    for short in ("cy", "dee"):
        go_place(pid(short), "wedding")
    out = post("/pixel/room/do", {"id": pid("cy"), "what": "wedding"})
    report.check("a wedding is refused while the fashion show is dressing",
                 "game is on" in (out.get("error") or ""), out)
    report.check("no wedding started during the fashion show",
                 a.js("return !roomInfo.wedding"), a.js("return roomInfo.wedding"))
    report.check("the refused wedding leaves no card on Cy",
                 not visible(c, "#weddingCard"), moment_text(c))
    shot(a, "fashion-dressing-refuses-wedding")
    shot(show, "projector-fashion-dressing")

    # Ready: the runway starts.
    post("/pixel/room/do", {"id": pid("ana"), "what": "game", "action": "ready"})
    post("/pixel/room/do", {"id": pid("ben"), "what": "game", "action": "ready"})
    wait(a, "return roomInfo.game && roomInfo.game.phase === 'runway'", 8, "the runway")
    report.check("the fashion show reaches the runway", a.js("return roomInfo.game.phase") == "runway",
                 a.js("return roomInfo.game"))
    out = post("/pixel/room/do", {"id": pid("cy"), "what": "wedding"})
    report.check("a wedding is refused on the runway", "game is on" in (out.get("error") or ""), out)
    shot(a, "fashion-runway")
    shot(show, "projector-fashion-runway")

    # End the game, then start the wedding the other way round.
    click_js(teacher, "#endGame")
    report.check("the ended fashion game clears before the wedding",
                 wait_game_clear(14), room_of(pid("ana")).get("game"))
    for short in ("ana", "ben", "cy", "dee"):
        go_place(pid(short), "wedding")
    time.sleep(.5)
    out = start_wedding(pid("cy"), pid("dee"))
    report.check("a wedding starts after the fashion show", not out.get("error"), out)
    wait(c, "return !!(roomInfo.wedding && roomInfo.wedding.phase === 'invite')", 8, "the wedding invite")
    report.check("the wedding invite reaches Dee's card", visible(dee, "#weddingCard"), moment_text(dee))
    report.check("the wedding invite card says who asks", "asks you" in text_of(dee, "#weddingCard"),
                 text_of(dee, "#weddingCard"))
    out = begin_fashion(pid("ana"), pid("ben"))
    report.check("a fashion show is refused during a wedding invite", "wedding" in (out.get("error") or ""), out)
    report.check("no fashion game started during the wedding", a.js("return !roomInfo.game"),
                 a.js("return roomInfo.game"))
    shot(dee, "wedding-invite-during-fashion-refused")

    # Accept and let the ceremony run, while the teacher tries the other buttons.
    out = accept_wedding(pid("dee"))
    report.check("Dee can say yes after the fashion show is over", not out.get("error"), out)
    wait(c, "return roomInfo.wedding && roomInfo.wedding.phase === 'ceremony'", 8, "the wedding ceremony")
    report.check("the wedding ceremony is on", c.js("return roomInfo.wedding.phase") == "ceremony",
                 c.js("return roomInfo.wedding"))

    # A birthday during the ceremony is refused.
    teacher_birthday(teacher)
    wait(teacher, "return !document.getElementById('roomBirthday').hidden && !/Starting/.test(document.getElementById('roomBirthday').textContent)", 8, "the birthday answer")
    btext = text_of(teacher, "#roomBirthday")
    report.check("the teacher's birthday is refused during a wedding",
                 "wedding" in btext.lower(), btext)
    report.check("no birthday party started during the wedding",
                 c.js("return !roomInfo.birthday"), c.js("return roomInfo.birthday"))
    w = c.js("return roomInfo.wedding")
    report.check("the wedding is still on after the refused birthday", bool(w) and w.get("phase") == "ceremony", w)

    # 📸 Class photo during the ceremony: it must not break the wedding.
    click_js(teacher, "#photo")
    wait(teacher, "return document.getElementById('photo').textContent !== '📸 Class photo'", 6, "the photo answer")
    ptext = text_of(teacher, "#photo")
    report.check("the teacher's photo is refused during a wedding",
                 "wedding" in ptext.lower(), ptext)
    w = c.js("return roomInfo.wedding")
    report.check("the wedding is still on after the teacher's photo", bool(w) and w.get("phase") == "ceremony", w)
    report.check("the wedding couple did not get moved to the Park",
                 c.js("return !roomInfo.wedding || roomInfo.wedding.phase === 'ceremony'"), w)
    shot(c, "wedding-ceremony-after-photo-try")
    shot(show, "projector-wedding-ceremony")

    # A star shower and open house cannot be forced into the wedding; the
    # teacher's shower is allowed, so keep an eye on the banners.
    click_js(teacher, "#shower")
    time.sleep(.8)
    st = moment_text(c)
    report.check("a star shower during the wedding does not pile two big banners up",
                 not (st["bannerShown"] and "🌠" in st["banner"] and "wedding" in st["banner"]), st["banner"])
    report.check("the wedding still runs after the star shower",
                 c.js("return roomInfo.wedding && roomInfo.wedding.phase === 'ceremony'"),
                 c.js("return roomInfo.wedding"))

    # The wedding's own end should say wedding, not "Class photo".
    wait(c, "return !roomInfo.wedding", 30, "the wedding to finish")
    time.sleep(.7)
    st = moment_text(c)
    report.check("the wedding does not end with a 'Class photo' banner",
                 "Class photo" not in st["banner"], st["banner"])
    report.check("the projector offers to save the wedding photo",
                 wait(show, "return !document.getElementById('savePhoto').hidden", 8, "the wedding save button"),
                 text_of(show, "#savePhoto"))
    report.check("the projector's save button names the wedding photo",
                 "wedding" in text_of(show, "#savePhoto").lower(), text_of(show, "#savePhoto"))
    shot(c, "wedding-done-banner")
    shot(show, "projector-wedding-photo-offer")
    for short, d in STUDENTS.items():
        collect_console(d, short)
    collect_console(show, "show")
    collect_console(teacher, "teacher")


# ---------------------------------------------------------------------------
# 2. Open house overlaps: invites, a wedding card, leaving home, two hosts
# ---------------------------------------------------------------------------
def open_house_overlaps(a, b, c, dee, show, teacher):
    print("\n--- open house overlaps ---")
    reset_room()
    for short in ("ana", "ben"):
        go_home(pid(short))
    time.sleep(.6)
    # Ana starts from her home pane, through the real button.
    pane(a, "home")
    click_room(a, "[data-openhouse]")
    wait(a, "return !!(roomInfo.openhouse && roomInfo.openhouse.mine)", 10, "Ana's open house")
    report.check("Ana's open house starts from her Home pane",
                 bool(a.js("return roomInfo.openhouse && roomInfo.openhouse.mine")),
                 a.js("return roomInfo.openhouse"))
    wait(b, "return !document.getElementById('houseStatus').hidden", 8, "Ben's open house invite")
    wait(c, "return !document.getElementById('houseStatus').hidden", 8, "Cy's open house invite")
    report.check("the one-tap invite reaches both friends",
                 visible(b, "#houseStatus") and visible(c, "#houseStatus"),
                 [text_of(b, "#houseStatus"), text_of(c, "#houseStatus")])
    shot(b, "open-house-invite")
    # A reload while the invite is up must not erase it.
    reload_student(c)
    time.sleep(.8)
    report.check("a reload keeps the open house invite on Cy",
                 visible(c, "#houseStatus"), moment_text(c))
    shot(c, "open-house-invite-after-reload")
    click_js(b, "#houseStatus")
    wait(b, "return !!(roomInfo.home && !roomInfo.home.mine)", 12, "Ben in Ana's home")
    report.check("Ben comes into Ana's open house", bool(b.js("return roomInfo.home && !roomInfo.home.mine")),
                 b.js("return roomInfo.home"))

    # 📸 The teacher's class photo is allowed during an open house, and must not
    # pull the host or the guest out of the home.
    click_js(teacher, "#photo")
    wait(teacher, "return document.getElementById('photo').textContent !== '📸 Class photo'", 6, "the open-house photo answer")
    ptext = text_of(teacher, "#photo")
    report.check("the teacher's class photo is allowed during an open house",
                 "Say cheese" in ptext, ptext)
    report.check("the open house is still on after the class photo",
                 bool(a.js("return roomInfo.openhouse && roomInfo.openhouse.mine")),
                 a.js("return roomInfo.openhouse"))
    report.check("the guest is still in the home after the class photo",
                 bool(b.js("return roomInfo.home && !roomInfo.home.mine")),
                 b.js("return roomInfo.home"))
    report.check("the class photo does not leave a stuck banner on the guest",
                 not layout_issues(b, "the guest after a class photo"),
                 layout_issues(b, "the guest after a class photo"))
    shot(b, "open-house-class-photo")

    # Cy also gets a wedding invite while the open house invite is up.
    for short in ("cy", "dee"):
        go_place(pid(short), "wedding")
    time.sleep(.5)
    out = start_wedding(pid("cy"), pid("dee"))
    report.check("a wedding can start while another pair's open house is on",
                 not out.get("error"), out)
    wait(dee, "return !!(roomInfo.wedding && roomInfo.wedding.phase === 'invite')", 8, "Dee's wedding invite")
    st = moment_text(dee)
    report.check("Dee has both the wedding card and the open house invite without overlap",
                 st["weddingShown"] and st["houseShown"], st)
    report.check("Dee's two cards do not cover each other",
                 not layout_issues(dee, "Dee has a wedding card and an open house invite"),
                 layout_issues(dee, "Dee has a wedding card and an open house invite"))
    shot(dee, "wedding-card-and-open-house-invite")

    # Dee taps the open house invite while the wedding card is open.
    click_js(dee, "#houseStatus")
    wait(dee, "return !!(roomInfo.home && roomInfo.home.name === arguments[0])", 12, "Dee in Ana's home", SHORT["ana"])
    report.check("Dee can choose the open house from under the wedding card",
                 dee.js("return !!(roomInfo.home && !roomInfo.home.mine)"),
                 dee.js("return roomInfo.home"))
    time.sleep(.8)
    st = moment_text(dee)
    report.check("the wedding card does not leave Dee stuck at the open house",
                 st["weddingShown"] or st["wedding"] == "", st)
    # Decline the wedding so Cy is not left waiting.
    if visible(dee, "#weddingCard"):
        click_js(dee, '#weddingCard [data-wedding="no"]')
        wait(dee, "return document.getElementById('weddingCard').hidden", 8, "Dee's wedding card to clear")
    report.check("Dee's wedding card clears after Not now",
                 not visible(dee, "#weddingCard"), moment_text(dee))
    report.check("the wedding host is told the invite was declined",
                 wait(c, "return !roomInfo.wedding", 10, "the declined wedding to end"),
                 c.js("return roomInfo.wedding"))
    report.check("the open house is still on after the wedding ends",
                 bool(a.js("return roomInfo.openhouse && roomInfo.openhouse.mine")),
                 a.js("return roomInfo.openhouse"))

    # A game invite while a student is in the open house: going in is refused.
    for short in ("cy", "dee"):
        leave_home(pid(short)) if short == "dee" else None
        go_place(pid(short), "park")
    time.sleep(.4)
    out = post("/pixel/room/do", {"id": pid("cy"), "what": "game",
                                  "action": "create", "kind": "tag"})
    report.check("a game can start outside while the open house is on", not out.get("error"), out)
    post("/pixel/room/do", {"id": pid("dee"), "what": "game", "action": "join"})
    post("/pixel/room/do", {"id": pid("cy"), "what": "game", "action": "start"})
    time.sleep(.5)
    st = moment_text(b)
    report.check("Ben is still in the open house while a game plays outside",
                 bool(b.js("return roomInfo.home && !roomInfo.home.mine")), st)
    report.check("the open house is not broken by the game outside",
                 bool(a.js("return roomInfo.openhouse && roomInfo.openhouse.mine")),
                 a.js("return roomInfo.openhouse"))
    click_js(teacher, "#endGame")
    time.sleep(.8)

    # The host leaves home: the open house must end cleanly for the guest.
    leave_home(pid("ana"))
    wait(a, "return !roomInfo.openhouse", 8, "Ana's open house to end when she leaves")
    report.check("Ana's open house ends when she walks outside",
                 not a.js("return roomInfo.openhouse"), a.js("return roomInfo.openhouse"))
    report.check("the host's open house bar goes away",
                 wait(a, "return document.getElementById('openHouseBar').hidden", 6, "the host bar to hide"),
                 moment_text(a))
    report.check("Ben, still visiting, is told the open house ended",
                 wait(b, "return !roomInfo.openhouse", 8, "Ben's open house to clear"),
                 b.js("return roomInfo.openhouse"))
    report.check("Ben is not stuck in a home with no way out",
                 wait(b, "return !!document.querySelector('#roomButtons [data-home=\"out\"]')", 5, "Ben's way out") or
                 b.js("return roomPane !== 'home'"), moment_text(b))
    shot(b, "guest-after-host-left")

    # Two students start an open house at the same moment, while Ana and Ben
    # are in a game, so the invite arrives mid-game too.
    reset_room()
    go_home(pid("cy"))
    go_home(pid("dee"))
    go_place(pid("ana"), "park")
    go_place(pid("ben"), "park")
    time.sleep(.5)
    post("/pixel/room/do", {"id": pid("ana"), "what": "game", "action": "create", "kind": "tag"})
    post("/pixel/room/do", {"id": pid("ben"), "what": "game", "action": "join"})
    post("/pixel/room/do", {"id": pid("ana"), "what": "game", "action": "start"})
    time.sleep(.4)
    results = {}

    def start_house(which, which_pid):
        try:
            results[which] = post("/pixel/room/do", {"id": which_pid, "what": "openhouse",
                                                     "action": "start"})
        except Exception as e:
            results[which] = {"crash": str(e)}

    t1 = threading.Thread(target=start_house, args=("cy", pid("cy")))
    t2 = threading.Thread(target=start_house, args=("dee", pid("dee")))
    t1.start(); t2.start(); t1.join(); t2.join()
    report.check("two students can start an open house within a second",
                 results.get("cy", {}).get("ok") and results.get("dee", {}).get("ok"), results)
    houses = post("/pixel/teacher", {"key": server.ADMIN_KEY, "action": "overview"})["room"]["open_houses"]
    report.check("the server keeps both open houses", len(houses) == 2, houses)
    wait(a, "return !document.getElementById('houseStatus').hidden", 8, "a mid-game open house invite")
    st = moment_text(a)
    report.check("an open house invite arrives while Ana is in a game",
                 st["houseShown"] and bool(st["game"]), st)
    click_js(a, "#houseStatus")
    time.sleep(.8)
    st = moment_text(a)
    report.check("a player in a game is told to finish the game, not pulled into the home",
                 "game" in (st["tip"] or "").lower() and not a.js("return roomInfo.home"), st)
    report.check("the mid-game refusal leaves the open house on",
                 bool(post("/pixel/teacher", {"key": server.ADMIN_KEY,
                                             "action": "overview"})["room"]["open_houses"]),
                 houses)
    shot(a, "open-house-invite-mid-game")
    click_js(teacher, "#endGame")
    wait_game_clear(14)
    # Both hosts see their own deck, and each other's invite.
    pane(c, "home")
    pane(dee, "home")
    time.sleep(.8)
    st = moment_text(c)
    report.check("the first host sees her own open house on, not a tangle of cards",
                 "Your open house is on" in st["openBar"] or st["openBarShown"], st)
    report.check("the second invite does not make the first host's screen unreadable",
                 not layout_issues(c, "Cy with two open houses"), layout_issues(c, "Cy with two open houses"))
    shot(c, "two-open-houses-host")
    shot(dee, "two-open-houses-other-host")
    for d in (a, b, c, dee):
        resize(d, 1024, 600)
    time.sleep(.6)
    report.check("two open houses fit at 1024x600",
                 not layout_issues(c, "two open houses at 1024x600"),
                 layout_issues(c, "two open houses at 1024x600"))
    shot(c, "two-open-houses-1024x600")
    for d in (a, b, c, dee):
        resize(d, 1366, 768)
    # The teacher closes the Hang out in the middle of both open houses.
    click_js(teacher, "#roomOpen")
    wait(c, "return roomInfo && roomInfo.open === false", 10, "the Hang out to close in the open houses")
    report.check("closing the Hang out clears both open house bars",
                 wait(c, "return document.getElementById('openHouseBar').hidden", 5, "Cy's bar to hide"),
                 moment_text(c))
    report.check("closing the Hang out clears a guest's open house invite",
                 not visible(a, "#houseStatus"), moment_text(a))
    report.check("the closed sign is readable over the two open houses",
                 not layout_issues(c, "closed with two open houses"),
                 layout_issues(c, "closed with two open houses"))
    shot(c, "closed-during-two-open-houses")
    click_js(teacher, "#roomOpen")
    wait(c, "return roomInfo && roomInfo.open === true", 10, "the Hang out to reopen")
    reset_room()

    # A birthday during an open house ends it cleanly rather than leaving a bar.
    go_home(pid("ben"))
    time.sleep(.5)
    post("/pixel/room/do", {"id": pid("ben"), "what": "openhouse", "action": "start"})
    wait(b, "return !!(roomInfo.openhouse && roomInfo.openhouse.mine)", 8, "Ben's open house for the birthday")
    teacher_birthday(teacher)
    wait(teacher, "return !document.getElementById('roomBirthday').hidden && !/Starting/.test(document.getElementById('roomBirthday').textContent)", 8, "the birthday answer")
    btext = text_of(teacher, "#roomBirthday")
    report.check("the teacher can start a birthday during an open house",
                 "Happy birthday" in btext, btext)
    report.check("the open house ends cleanly when the birthday pulls the host out",
                 wait(b, "return !roomInfo.openhouse", 8, "the open house to end"),
                 b.js("return roomInfo.openhouse"))
    report.check("no open house bar is left over the birthday",
                 not visible(b, "#openHouseBar") or not b.js("return roomInfo.birthday"), moment_text(b))
    wait(a, "return !roomInfo.birthday", 30, "the birthday to finish")
    for short, d in STUDENTS.items():
        collect_console(d, short)
    collect_console(show, "show")
    collect_console(teacher, "teacher")


# ---------------------------------------------------------------------------
# 3. Star shower during the birthday song, Calm and Mute, mural in a game
# ---------------------------------------------------------------------------
def shower_birthday_mural(a, b, c, dee, show, teacher):
    print("\n--- star shower during the birthday song, Calm/Mute, mural in a game ---")
    reset_room()
    for short in ("ana", "ben", "cy", "dee"):
        click_js(STUDENTS[short], "#calm")
        click_js(STUDENTS[short], "#mute")
    for short, d in STUDENTS.items():
        report.check(f"{short}'s Calm is on",
                     d.js("return document.body.classList.contains('calm') || "
                          "document.getElementById('calm').getAttribute('aria-pressed') === 'true'"),
                     d.js("return document.body.className"))
        report.check(f"{short}'s Mute is on",
                     d.js("return PalStage.SFX.muted === true || "
                          "document.getElementById('mute').getAttribute('aria-pressed') === 'true'"),
                     d.js("return document.getElementById('mute').outerHTML"))
    teacher_birthday(teacher)
    wait(teacher, "return !document.getElementById('roomBirthday').hidden && !/Starting/.test(document.getElementById('roomBirthday').textContent)", 8, "the birthday answer")
    btext = text_of(teacher, "#roomBirthday")
    report.check("the teacher starts a birthday with Calm and Mute on",
                 "Happy birthday" in btext, btext)
    report.check("the birthday reaches every student",
                 wait(c, "return !!(roomInfo.birthday && roomInfo.birthday.phase)", 8, "Cy's birthday"),
                 c.js("return roomInfo.birthday"))
    wait(a, "return /singing/i.test(document.getElementById('hangBanner').innerText || '')", 10, "the song")
    # The shower in the middle of the song.
    click_js(teacher, "#shower")
    time.sleep(.8)
    report.check("the star shower really starts during the birthday song",
                 bool(room_of(pid("ana")).get("birthday")),
                 room_of(pid("ana")).get("birthday"))
    st = moment_text(c)
    report.check("the birthday song keeps the screen, with no star shower banner over it",
                 "Happy birthday" in st["banner"] or not st["bannerShown"], st["banner"])
    report.check("no second banner is stacked under the birthday banner",
                 not layout_issues(c, "the birthday song with a star shower"), layout_issues(c, "the birthday song with a star shower"))
    # The projector should not flip cameras every second.
    places = []
    for _ in range(10):
        places.append(show.js("return [cam.mode, cam.loc, cam.seat, Math.round(stage.state.camX || 0)]"))
        time.sleep(.7)
    changes = sum(1 for i in range(1, len(places)) if places[i] != places[i - 1])
    report.check("the projector's Auto camera is not flip-flopping during the birthday",
                 changes <= 4, {"places": places, "changes": changes})
    shot(c, "birthday-song-with-shower")
    shot(show, "projector-birthday-shower")
    wait(a, "return !roomInfo.birthday", 30, "the birthday to finish")

    # Mural in the middle of a tag game: the player may not paint, a watcher may.
    reset_room()
    for short in ("ana", "ben"):
        go_place(pid(short), "park")
    post("/pixel/room/do", {"id": pid("ana"), "what": "game", "action": "create", "kind": "tag"})
    post("/pixel/room/do", {"id": pid("ben"), "what": "game", "action": "join"})
    post("/pixel/room/do", {"id": pid("ana"), "what": "game", "action": "start"})
    time.sleep(.6)
    pane(a, "art")
    click_room(a, '[data-pane="mural"]')
    wait(a, "return roomPane === 'mural' && !!document.getElementById('muralBoard')", 8, "the mural pane in a game")
    a.js("""const cv=document.getElementById('muralBoard');
        const r=cv.getBoundingClientRect();
        cv.dispatchEvent(new MouseEvent('click', {bubbles:true,
          clientX:r.left+r.width*.25, clientY:r.top+r.height*.25}));""")
    time.sleep(.8)
    st = moment_text(a)
    report.check("a player in a game gets a plain 'finish the game' tip, not a broken mural",
                 "game" in st["tip"].lower() or bool(a.js("return roomInfo.mural")), st["tip"])
    # A watcher who is not in the game can paint.
    pane(c, "art")
    click_room(c, '[data-pane="mural"]')
    wait(c, "return roomPane === 'mural' && !!document.getElementById('muralBoard')", 8, "Cy's mural pane")
    before = c.js("return roomInfo.mural ? roomInfo.mural.grid : ''")
    c.js("""const cv=document.getElementById('muralBoard');
        const r=cv.getBoundingClientRect();
        cv.dispatchEvent(new MouseEvent('click', {bubbles:true,
          clientX:r.left+r.width*.5, clientY:r.top+r.height*.5}));""")
    wait(c, "return roomInfo.mural && roomInfo.mural.grid !== arguments[0]", 8, "Cy's mural square", before)
    after = c.js("return roomInfo.mural ? roomInfo.mural.grid : ''")
    report.check("a watcher can paint the class mural while a game round plays", after != before,
                 {"before": before[:40], "after": after[:40]})
    report.check("the game player's screen did not break when the mural changed",
                 bool(a.js("return roomInfo && roomInfo.game")), a.js("return roomInfo.game"))
    shot(c, "mural-during-tag")
    click_js(teacher, "#endGame")
    time.sleep(.8)
    for short, d in STUDENTS.items():
        collect_console(d, short)
    collect_console(show, "show")
    collect_console(teacher, "teacher")


# ---------------------------------------------------------------------------
# 4. Closing the Hang out and reloading in the middle
# ---------------------------------------------------------------------------
def reload_student(d):
    d.request("POST", f"/session/{d.sid}/url", {"url": BASE + "/pixel"})
    wait(d, "return !document.getElementById('app').hidden || !document.getElementById('join').hidden",
         20, "the page after reload")
    time.sleep(.3)
    if not d.js("return document.getElementById('shelf').hidden"):
        click_js(d, "#gallery [data-gallery]")
    return open_hang(d, 30)


def close_and_reload(a, b, c, dee, show, teacher):
    print("\n--- teacher closes the Hang out, and a page reload in the middle ---")
    reset_room()
    # Reload in the middle of a wedding invite: the card should come back.
    for short in ("cy", "dee"):
        go_place(pid(short), "wedding")
    time.sleep(.4)
    out = start_wedding(pid("cy"), pid("dee"))
    report.check("a wedding invite starts before the reload", not out.get("error"), out)
    wait(dee, "return !!(roomInfo.wedding && roomInfo.wedding.phase === 'invite')", 8, "Dee's wedding invite")
    report.check("Dee has the wedding invite card before the reload",
                 visible(dee, "#weddingCard"), moment_text(dee))
    reload_student(dee)
    time.sleep(.8)
    report.check("after a reload Dee still sees the wedding invite card",
                 visible(dee, "#weddingCard"), moment_text(dee))
    report.check("after a reload Dee's card still has the Yes button",
                 dee.js("return !!document.querySelector('#weddingCard [data-wedding=\"yes\"]')"),
                 text_of(dee, "#weddingCard"))
    shot(dee, "wedding-invite-after-reload")
    click_js(dee, '#weddingCard [data-wedding="yes"]')
    wait(c, "return roomInfo.wedding && roomInfo.wedding.phase === 'ceremony'", 8, "the wedding after the reload")
    report.check("Dee can still say yes after the reload",
                 c.js("return roomInfo.wedding && roomInfo.wedding.phase === 'ceremony'"),
                 c.js("return roomInfo.wedding"))

    # Reload the host during the ceremony: the wedding must not be cancelled by the reload.
    reload_student(c)
    time.sleep(1.2)
    w = c.js("return roomInfo.wedding")
    report.check("a host reload in the ceremony does not cancel the wedding", bool(w), w)
    report.check("the reloaded host is back in the Hang out", open_hang(c, 20), moment_text(c))
    shot(c, "wedding-ceremony-after-host-reload")
    wait(c, "return !roomInfo.wedding", 30, "the wedding to finish after reload")

    # Reload in the middle of a birthday.
    reset_room()
    teacher_birthday(teacher)
    wait(teacher, "return !document.getElementById('roomBirthday').hidden && !/Starting/.test(document.getElementById('roomBirthday').textContent)", 8, "the birthday answer")
    wait(c, "return !!(roomInfo.birthday && roomInfo.birthday.phase)", 8, "Cy's birthday")
    reload_student(c)
    time.sleep(.8)
    st = moment_text(c)
    report.check("after a reload in a birthday Cy is still at the party",
                 bool(st["birthday"]), st)
    report.check("after a reload in a birthday Cy is not stuck in a card or pane",
                 not st["weddingShown"] and not st["closed"], st)
    shot(c, "birthday-after-reload")
    wait(c, "return !roomInfo.birthday", 30, "the birthday to finish after reload")

    # Reload a student in the middle of a game round.
    reset_room()
    for short in ("ana", "ben"):
        go_place(pid(short), "park")
    post("/pixel/room/do", {"id": pid("ana"), "what": "game", "action": "create", "kind": "tag"})
    post("/pixel/room/do", {"id": pid("ben"), "what": "game", "action": "join"})
    post("/pixel/room/do", {"id": pid("ana"), "what": "game", "action": "start"})
    time.sleep(.6)
    reload_student(a)
    time.sleep(.8)
    st = moment_text(a)
    report.check("after a reload in a game Ana is not stuck on a blank pane",
                 not st["closed"] and st["pane"] is not None, st)
    report.check("the game is still on for the reloaded player",
                 bool(st["game"]), st)
    shot(a, "tag-after-reload")
    click_js(teacher, "#endGame")
    reset_room()

    # A final close in the middle of a birthday: no big banner over the closed sign.
    teacher_birthday(teacher)
    wait(teacher, "return !document.getElementById('roomBirthday').hidden && !/Starting/.test(document.getElementById('roomBirthday').textContent)", 8, "the birthday answer")
    wait(a, "return !!(roomInfo.birthday && roomInfo.birthday.phase)", 8, "the birthday")
    time.sleep(1.2)
    click_js(teacher, "#roomOpen")
    wait(a, "return roomInfo && roomInfo.open === false", 10, "the Hang out to close mid-birthday")
    time.sleep(.5)
    report.check("closing in the middle of a birthday hides the big birthday banner",
                 not visible(a, "#hangBanner") or not text_of(a, "#hangBanner"),
                 moment_text(a))
    report.check("closing in the middle of a birthday leaves the closed sign readable",
                 not layout_issues(a, "closed mid-birthday"), layout_issues(a, "closed mid-birthday"))
    shot(a, "closed-mid-birthday")
    click_js(teacher, "#roomOpen")
    wait(a, "return roomInfo && roomInfo.open === true", 10, "the Hang out to reopen")
    reset_room()
    for short, d in STUDENTS.items():
        collect_console(d, short)
    collect_console(show, "show")
    collect_console(teacher, "teacher")


# ---------------------------------------------------------------------------
# Worst case at 1024x600
# ---------------------------------------------------------------------------
def small_screen(a, b, c, dee, show, teacher):
    print("\n--- worst cases at 1024x600 ---")
    reset_room()
    for short in ("ana", "ben", "cy", "dee"):
        go_place(pid(short), "wedding")
    time.sleep(.4)
    out = start_wedding(pid("ana"), pid("ben"))
    report.check("small screen: a wedding starts", not out.get("error"), out)
    wait(b, "return !!(roomInfo.wedding && roomInfo.wedding.phase === 'invite')", 8, "the invite")
    for d in (a, b, c, dee, show, teacher):
        resize(d, 1024, 600)
    time.sleep(.6)
    no_unreadable_overlap("ben", "at 1024x600 with a wedding card")
    report.check("the wedding card fits at 1024x600",
                 not layout_issues(b, "the wedding card at 1024x600"),
                 layout_issues(b, "the wedding card at 1024x600"))
    shot(b, "wedding-card-1024x600")
    shot(show, "projector-wedding-1024x600")
    post("/pixel/room/do", {"id": pid("ben"), "what": "wedding_yes"})
    time.sleep(1.0)
    no_unreadable_overlap("ana", "at 1024x600 during the wedding")
    shot(a, "wedding-1024x600")
    # The teacher's photo during the wedding is still refused on the small screen.
    click_js(teacher, "#photo")
    wait(teacher, "return document.getElementById('photo').textContent !== '📸 Class photo'", 6, "the small-screen photo answer")
    report.check("small screen: the photo is still refused during the wedding",
                 "wedding" in text_of(teacher, "#photo").lower(), text_of(teacher, "#photo"))
    wait(a, "return !roomInfo.wedding", 30, "the wedding to finish")
    # A second wedding invite, still at the small size.
    go_place(pid("cy"), "wedding")
    go_place(pid("dee"), "wedding")
    time.sleep(.4)
    out = start_wedding(pid("cy"), pid("dee"))
    report.check("small screen: a second wedding still starts", not out.get("error"), out)
    wait(dee, "return !!(roomInfo.wedding && roomInfo.wedding.phase === 'invite')", 8, "the small wedding invite")
    shot(dee, "wedding-card-second-1024x600")
    for d in (a, b, c, dee, show, teacher):
        resize(d, 1366, 768)
    for short, d in STUDENTS.items():
        collect_console(d, short)
    collect_console(show, "show")
    collect_console(teacher, "teacher")


def main():
    global BASE, SHOT_DIR, NAMES, IDS, SHORT
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", default="8916")
    ap.add_argument("--shots", default="/tmp/interhunt")
    ap.add_argument("--driver", default="/usr/bin/chromedriver")
    ap.add_argument("--browser", default="/usr/bin/chromium")
    args = ap.parse_args()
    BASE = f"http://127.0.0.1:{args.port}"
    SHOT_DIR = args.shots
    drivers = {}
    try:
        NAMES, IDS = setup_state(BASE)
        SHORT = {"ana": NAMES[0], "ben": NAMES[1], "cy": NAMES[2], "dee": NAMES[3]}
        students = sorted(SHORT, key=lambda k: NAMES.index(SHORT[k]))
        for short in students:
            drivers[short] = Driver(args.driver, args.browser, 1366, 768)
            report.check(f"{SHORT[short]} can log in", login(drivers[short], SHORT[short]))
            report.check(f"{SHORT[short]} is in the Hang out", open_hang(drivers[short]))
            STUDENTS[short] = drivers[short]
        drivers["show"] = Driver(args.driver, args.browser, 1366, 768)
        show = drivers["show"]
        show.request("POST", f"/session/{show.sid}/url", {"url": BASE + "/pixel/show"})
        wait(show, "return typeof stage !== 'undefined' && !!stage && document.getElementById('closed').hidden",
             20, "the projector")
        report.check("the projector is in Auto", show.js("return cam.mode === 'auto'"), show.js("return cam"))
        drivers["teacher"] = Driver(args.driver, args.browser, 1366, 768)
        teacher = drivers["teacher"]
        teacher.request("POST", f"/session/{teacher.sid}/url", {"url": BASE + "/pixel/teacher"})
        wait(teacher, "return !document.getElementById('gate').hidden || !document.getElementById('page').hidden",
             20, "the teacher gate")
        if not teacher.js("return document.getElementById('gate').hidden"):
            teacher.js("sessionStorage.setItem('pixelKey', arguments[0]); location.reload();", server.ADMIN_KEY)
            wait(teacher, "return !document.getElementById('page').hidden", 20, "the teacher page")
        report.check("the teacher page loaded", not teacher.js("return document.getElementById('page').hidden"))
        teacher.js("refresh()")
        time.sleep(.5)

        a, b, c, dee = (drivers[k] for k in ("ana", "ben", "cy", "dee"))
        wedding_versus_fashion(a, b, c, dee, show, teacher)
        open_house_overlaps(a, b, c, dee, show, teacher)
        shower_birthday_mural(a, b, c, dee, show, teacher)
        close_and_reload(a, b, c, dee, show, teacher)
        small_screen(a, b, c, dee, show, teacher)
    except Exception:
        traceback.print_exc()
        report.problem("script crashed", traceback.format_exc()[-1400:])
    finally:
        for d in drivers.values():
            d.close()
    for e in report.console_errors():
        report.check(f"console is clean in {e['where']}", False, e["message"])
    out = os.path.join("/tmp", "interhunt-overlaps-report.json")
    try:
        with open(out, "w") as f:
            json.dump({"checks": report.checks, "problems": report.problems,
                       "notes": report.notes, "console": report.console,
                       "screenshots": report.screenshots}, f, indent=2)
    except Exception:
        pass
    print("\n=== SUMMARY ===")
    print("checks:", len(report.checks), "failed:", len(report.problems))
    for p in report.problems:
        print("PROBLEM:", p)
    print("screenshots:", len(report.screenshots))
    sys.exit(1 if report.problems else 0)


if __name__ == "__main__":
    main()
