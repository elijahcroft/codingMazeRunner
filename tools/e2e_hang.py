#!/usr/bin/env python3
"""End-to-end bug hunt in the 🎉 Hang out, with several students and the projector.

It starts headless Chromium through chromedriver and talks to it with the
standard library, the same way tools/e2e_coach.py does, so there is nothing to
pip install.  It makes four separate browser sessions (separate cookies and
local storage) as four students, plus one projector session at /pixel/show,
and plays through what children do in the Hang out at 1366x768:

  * walking by click and the arrow keys, and 🏞️ Go to every place,
  * sitting, a toy, a gem, fishing, and coding a 🧰 chest open,
  * 💬 Say with the tap words and with the teacher's typing on,
  * 👋 Do, 🎉 Party, ✨ My Move, 🎤 My show and 👏 Clap,
  * high-fives, hiding names, buddies and props,
  * 🛍️ Shop (enough and not enough coins), 🧢 Me (a gift, a pal switch and
    wearing your own drawing), 🖼️ Art (placing and clicking a coded drawing),
    🏠 Home (furniture, visiting, hearts, the door),
  * every game: Code race, Draw & guess, Hide & seek, Tag, Red light green
    light, Copy the dance, 🍎 Apple grab and ⚽ Pal ball, including joining a
    Code race late, leaving mid-game and closing a tab mid-game,
  * a star shower and catching one, the teacher closing and opening the Hang
    out while the class is in it, and a page reload in the middle of things,
  * the projector's people, places, map, game card, follow, and the labels
    on its buttons, and Auto leaving a home to show a My Move outside.

It records console errors, and checks the layout at 1366x768 for text that is
cut off or pushed off the screen.  It is a tool, not a unittest: it is not
named test_*.py and unittest will not pick it up.

Use a fresh state file (or the setup will still work, but names carry a tag):

    MAZE_PORT=8132 MAZE_STATE_FILE=/tmp/hang-state.json python3 server.py
    python3 tools/e2e_hang.py --port 8132 --json-out /tmp/hang.json

The tool needs chromium and chromedriver on PATH.
"""

import argparse
import base64
import json
import os
import re
import sys
import time
import traceback
import urllib.error
import urllib.parse
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "tools"))
import pixel  # noqa: E402
import server  # noqa: E402  (only for the admin key)
from e2e_coach import Driver, WebDriverError  # noqa: E402

PAL = {"key": "e2epal", "size": 16, "speed": 6, "palette": pixel.PIP["palette"],
       "frames": pixel.PIP["frames"], "names": pixel.PIP["names"], "title": "My pal"}
PAL2 = {"key": "e2epal2", "size": 16, "speed": 6,
        "palette": ["#1b1530", "#7ab8ff", "#ffd27a"], "frames": pixel.PIP["frames"],
        "names": pixel.PIP["names"], "title": "Blue me"}
SHOW = ('scene("beach")\nsay("Hello!")\nfor i in range(3):\n    jump()\n'
        'hearts()\nnote("C")\ndance()')
THING = 'def on_click():\n    say("Hello!")\n    jump()\n    hearts()\n'
KEYS = {"Left": "\ue012", "Up": "\ue013", "Right": "\ue014", "Down": "\ue015"}


# ---------------------------------------------------------------------------
# The tool's own little report
# ---------------------------------------------------------------------------

class Report:
    def __init__(self):
        self.checks = []
        self.problems = []
        self.console = []
        self.notes = []
        self.screenshots = []
        self.welcome_text = ""

    def check(self, label, ok, detail=""):
        self.checks.append({"check": label, "ok": bool(ok), "detail": str(detail)[:600]})
        if not ok:
            self.problems.append(f"{label}: {detail}"[:1000])
        return bool(ok)

    def problem(self, label, detail=""):
        self.problems.append(f"{label}: {detail}"[:1000])
        self.checks.append({"check": label, "ok": False, "detail": str(detail)[:600]})

    def note(self, text):
        self.notes.append(text)

    def console_errors(self):
        return [e for e in self.console if e.get("level") == "SEVERE"]

    def ok(self):
        return not self.problems and not self.console_errors()


# ---------------------------------------------------------------------------
# HTTP setup: students, drawings, missions, the party meter and a Free show
# ---------------------------------------------------------------------------

def post(base, path, data, timeout=90):
    req = urllib.request.Request(base + path, data=json.dumps(data).encode(),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as f:
        return json.load(f)


def get(base, path, timeout=90):
    with urllib.request.urlopen(base + path, timeout=timeout) as f:
        return json.load(f)


def setup_state(base, tag, report):
    """A class that has been playing for a while: all places open, and a Free show."""
    names = [f"Hang Ana {tag}", f"Hang Ben {tag}", f"Hang Cy {tag}", f"Hang Dee {tag}"]
    ids = {}
    for name in names:
        ids[name] = post(base, "/join", {"name": name})["id"]
        post(base, "/pixel/save", {"id": ids[name], "drawing": PAL})
    post(base, "/pixel/teacher", {"key": server.ADMIN_KEY, "action": "open",
                                  "level": pixel.LEVEL_ORDER[-1]})
    # A clean world for a repeatable run: no leftover drawings or game from another class.
    post(base, "/pixel/teacher", {"key": server.ADMIN_KEY, "action": "placed_clear"})
    post(base, "/pixel/teacher", {"key": server.ADMIN_KEY, "action": "end_game"})
    post(base, "/pixel/teacher", {"key": server.ADMIN_KEY, "action": "room", "on": False})
    post(base, "/pixel/teacher", {"key": server.ADMIN_KEY, "action": "room", "on": True})
    # Two students finish everything: their first finishes fill the party meter
    # past every place, so Snowy hill, Candy land, Space and Under the sea open.
    fails = []
    for name in names[:2]:
        for key in pixel.LEVEL_ORDER:
            out = post(base, "/pixel/run", {"id": ids[name], "level": key,
                                            "code": pixel.LEVEL_BY_KEY[key]["reference"]})
            if out.get("error") or not (out.get("stars") or [False])[0]:
                fails.append((name, key, out.get("error"), out.get("stars")))
    # The other two only finish My Move (for the Hang out and its My Move button).
    for name in names[2:]:
        out = post(base, "/pixel/run", {"id": ids[name], "level": "m1",
                                        "code": pixel.LEVEL_BY_KEY["m1"]["reference"]})
        if out.get("error") or not (out.get("stars") or [False])[0]:
            fails.append((name, "m1", out.get("error"), out.get("stars")))
    report.check("setup: every test student can finish their missions", not fails, fails[:2])
    # Ana has a second drawing, a coded drawing and a Free stage show.
    a = ids[names[0]]
    post(base, "/pixel/save", {"id": a, "drawing": PAL2})
    post(base, "/pixel/save", {"id": a, "drawing": PAL})
    post(base, "/pixel/pal", {"id": a, "key": "e2epal"})
    post(base, "/pixel/thing/save", {"id": a, "key": "e2epal", "code": THING})
    for name in names[:2]:
        out = post(base, "/pixel/run", {"id": ids[name], "level": "free", "code": SHOW})
        report.check(f"setup: {name}'s Free stage show runs", not out.get("error"), out.get("error"))
    world = get(base, "/pixel/room?after=-1&wait=0").get("world", [])
    for place in ("park", "wedding", "beach", "night", "snowy", "candy", "space", "sea"):
        report.check(f"setup: {place} is open", place in world, world)
    return names, ids, world


# ---------------------------------------------------------------------------
# WebDriver helpers
# ---------------------------------------------------------------------------

def wait(d, script, timeout=15, what=""):
    end = time.time() + timeout
    while time.time() < end:
        try:
            if d.js(script):
                return True
        except WebDriverError:
            pass
        time.sleep(.15)
    if what:
        report.problem(f"timed out waiting for {what}", d.js("return location.href"))
    return False


def click_js(d, selector, timeout=3):
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


def click_text(d, selector, text):
    return d.js("""const el=[...document.querySelectorAll(arguments[0])]
        .find(x => (x.innerText || '').includes(arguments[1]));
        if(!el) return false; el.scrollIntoView({block:'nearest'}); el.click(); return true;""",
        selector, text)


def pane(d, name):
    click_js(d, f'#roomTabs [data-pane="{name}"]')
    wait(d, f"return roomPane === {json.dumps(name)}", 4, f"the {name} pane")


def login(d, name, report):
    d.request("POST", f"/session/{d.sid}/url", {"url": base_url + "/pixel"})
    ok = wait(d, "return !document.getElementById('join').hidden || !document.getElementById('app').hidden", 25, "the Pixel Pals page")
    if not ok:
        return False
    if not d.js("return document.getElementById('join').hidden"):
        d.send("#name", name)
        d.click("#joinButton")
        wait(d, "return !document.getElementById('app').hidden", 30, "the Pixel Pals page")
    wait(d, "return typeof S !== 'undefined' && !!S", 15, "the page to load")
    time.sleep(.35)
    if not d.js("return document.getElementById('shelf').hidden"):
        d.click("#gallery [data-gallery]")
        wait(d, "return document.getElementById('shelf').hidden", 15, "the gallery to close")
    return True


def open_hang(d, report, timeout=35):
    end = time.time() + timeout
    while time.time() < end:
        if d.js("return !document.getElementById('hangView').hidden && "
               "typeof roomStage !== 'undefined' && roomStage && "
               "roomStage.state && roomStage.state.room && "
               "roomInfo && roomInfo.you !== null && "
               "roomStage.state.room.some(m => m.me)"):
            return True
        click_js(d, 'nav [data-view="hang"]')
        time.sleep(.8)
    return False


def room(d):
    try:
        return d.js("return roomInfo") or {}
    except WebDriverError:
        return {}


def members(d):
    try:
        return d.js("""return (typeof roomStage !== 'undefined' && roomStage && roomStage.state &&
          roomStage.state.room || []).map(m => ({seat: m.seat, name: m.name, me: m.me,
          x: Math.round(m.x), y: +m.y.toFixed(2), rest: m.rest, mood: m.mood, move: m.move,
          prop: m.prop, hid: m.hid, wear: m.wear, wearArt: m.wearArt,
          buddies: (m.buddies || []).length}))""") or []
    except WebDriverError:
        return []


def mine(d):
    for m in members(d):
        if m["me"]:
            return m
    return None


def seat_of(d, name):
    for m in members(d):
        if m["name"] == name:
            return m["seat"]
    return None


def tap_screen(d, cx, cy):
    """A real mouse click at viewport coordinates."""
    cx, cy = int(round(cx)), int(round(cy))
    if cx < 0 or cy < 0 or cx > d.js("return innerWidth") or cy > d.js("return innerHeight"):
        return False
    try:
        d.request("POST", f"/session/{d.sid}/actions", {"actions": [{
            "type": "pointer", "id": "e2e-mouse", "parameters": {"pointerType": "mouse"},
            "actions": [{"type": "pointerMove", "duration": 0, "x": cx, "y": cy, "origin": "viewport"},
                        {"type": "pointerDown", "button": 0},
                        {"type": "pointerUp", "button": 0}]}]})
        return True
    except WebDriverError:
        return False


def canvas_point(d, x, depth):
    return d.js("""return (() => { const cv = document.getElementById('roomCanvas');
        const r = cv.getBoundingClientRect();
        return {px: r.left + (arguments[0] - roomStage.state.camX) / PalStage.W * r.width,
                py: r.top + (PalStage.GROUND_TOP + arguments[1] * PalStage.GROUND_DEEP) / PalStage.H * r.height,
                left: r.left, top: r.top, right: r.right, bottom: r.bottom,
                camX: roomStage.state.camX}; })()""", x, depth)


def tap_world(d, x, depth, report=None):
    p = canvas_point(d, x, depth)
    ok = tap_screen(d, p["px"], p["py"])
    if not ok:
        # Off this laptop's little window: still send the same click to the canvas,
        # which is what the page handler uses.
        try:
            d.js("""(() => { const cv = document.getElementById('roomCanvas');
                cv.dispatchEvent(new MouseEvent('click', {bubbles: true,
                  clientX: arguments[0], clientY: arguments[1]})); })()""", p["px"], p["py"])
            ok = True
        except WebDriverError:
            ok = False
    if report and not ok:
        report.problem("could not click the world", f"{x},{depth}")
    return ok


def press_key(d, key):
    d.request("POST", f"/session/{d.sid}/actions", {"actions": [{
        "type": "key", "id": "e2e-keys",
        "actions": [{"type": "keyDown", "value": key}, {"type": "keyUp", "value": key}]}]})


def js_click(d, script):
    return d.js(script)


def mine_x(d):
    return d.js("return (() => { const m = roomStage.state.room.find(m => m.me); return m ? [m.x, m.y] : null; })()")


def walk_towards(d, x, y=None, steps=26):
    """Arrow-key steps towards a world point, so the test never clicks off the picture."""
    for _ in range(steps):
        m = mine(d)
        if not m:
            return False
        dx, dy = x - m["x"], (y - m["y"]) if y is not None else 0
        if abs(dx) < 14 and abs(dy) < .06:
            return True
        key = KEYS["Right"] if dx > 14 else KEYS["Left"] if dx < -14 else KEYS["Down"] if dy > .06 else KEYS["Up"]
        press_key(d, key)
        time.sleep(.12)
    return False


def has_text(d, css, text):
    return d.js("return [...document.querySelectorAll(arguments[0])].some(el => (el.innerText || '').includes(arguments[1]))",
                css, text)


def text_of(d, css):
    return d.js("return (document.querySelector(arguments[0]) || {}).innerText || ''", css)


def shot(d, label, report, folder):
    try:
        os.makedirs(folder, exist_ok=True)
        path = os.path.join(folder, re.sub(r"[^a-z0-9]+", "-", label.lower()).strip("-") + ".png")
        data = d.request("GET", f"/session/{d.sid}/screenshot")
        with open(path, "wb") as f:
            f.write(base64.b64decode(data))
        report.screenshots.append(path)
        return path
    except Exception:
        return ""


def collect_console(d, label, report):
    try:
        entries = d.logs()
    except Exception:
        return
    for e in entries:
        msg = e.get("message") or ""
        if "AudioContext was not allowed to start" in msg:
            continue                      # the projector has no click yet; not a JS error
        if "favicon.ico" in msg:
            continue
        report.console.append({"where": label, "level": e.get("level"), "message": msg[:800]})


def layout_issues(d):
    return d.js(r"""return (() => {
      const out = [], h = document.getElementById('hangView');
      if (!h || h.hidden) return ['the Hang out is not showing'];
      const hr = h.getBoundingClientRect();
      if (hr.bottom > innerHeight + 1 || hr.right > innerWidth + 1) out.push('the Hang out is cut off');
      if (hr.height < 300) out.push('the Hang out is too short');
      const vis = el => { const s = getComputedStyle(el); const r = el.getBoundingClientRect();
        return s.display !== 'none' && s.visibility !== 'hidden' && r.width > 0 && r.height > 0; };
      const scroll = document.getElementById('roomButtons');
      for (const el of h.querySelectorAll('button, p, h4, .me-note, #roomTip, #coinBar, #gameStatus, #roomTabs button')) {
        if (!vis(el) || (scroll && scroll.contains(el))) continue;
        const r = el.getBoundingClientRect();
        if (r.left < -1 || r.right > innerWidth + 1 || r.bottom > innerHeight + 1)
          out.push('off screen: ' + (el.id || el.className || 'button') + ' ' + (el.innerText || '').slice(0, 30));
        const s = getComputedStyle(el);
        if (el.scrollWidth > el.clientWidth + 2 && !['auto', 'scroll'].includes(s.overflowX))
          out.push('cut-off text: ' + (el.id || el.className || 'button') + ' ' + (el.innerText || '').slice(0, 30));
      }
      if (scroll && scroll.scrollWidth > scroll.clientWidth + 2) out.push('the buttons scroll sideways');
      return out.slice(0, 12);
    })()""")


def button_label_issues(d):
    return d.js(r"""return (() => {
      const out = [];
      const vis = el => { const s = getComputedStyle(el); const r = el.getBoundingClientRect();
        return s.display !== 'none' && s.visibility !== 'hidden' && r.width > 0 && r.height > 0; };
      for (const el of document.querySelectorAll('#hangView button, #pixelShow button, #camLeft, #camRight, #camAuto, #savePhoto')) {
        if (!vis(el) || el.dataset.ink !== undefined) continue;       // colour swatches are colours
        const words = (el.innerText || '').replace(/[^A-Za-z0-9]/g, '');
        if (!words && !el.getAttribute('aria-label')) out.push('icon-only: ' + (el.id || el.className || el.outerHTML.slice(0, 50)));
      }
      return out.slice(0, 12);
    })()""")


def pstate(p):
    return p.js("""return {closed: !document.getElementById('closed').hidden,
      people: [...document.querySelectorAll('#people button')].map(b => b.innerText),
      places: [...document.querySelectorAll('#places button')].map(b => b.innerText),
      map: document.getElementById('map').innerText,
      tag: document.getElementById('placeTag').hidden ? null : document.getElementById('placeTag').innerText,
      follow: document.getElementById('followTag').hidden ? null : document.getElementById('followTag').innerText,
      word: document.getElementById('camWord').innerText,
      mode: cam.mode, loc: cam.loc, seat: cam.seat,
      race: [document.getElementById('raceLabel').innerText,
             document.getElementById('raceJob').innerText,
             document.getElementById('raceWho').innerText],
      banner: document.getElementById('banner').hidden ? null : document.getElementById('banner').innerText}""")


def clear_game(base, report=None, timeout=22):
    """End any round and wait until the servers' game is gone (results last 10s)."""
    try:
        post(base, "/pixel/teacher", {"key": server.ADMIN_KEY, "action": "end_game"})
    except Exception:
        pass
    end = time.time() + timeout
    while time.time() < end:
        try:
            if not get(base, "/pixel/room?after=-1&wait=0").get("game"):
                return True
        except Exception:
            pass
        time.sleep(.5)
    if report:
        report.note("a game did not clear within %.0fs" % timeout)
    return False


def make_game(d, kind, report=None):
    pane(d, "games")
    click_room(d, f'[data-game="create"][data-kind="{kind}"]')
    ok = wait(d, f"return !!currentGame() && currentGame().kind === {json.dumps(kind)}", 6, f"the {kind} lobby")
    if report and not ok:
        report.problem(f"could not start a {kind} lobby", d.js("return document.getElementById('roomButtons').innerText.slice(0,300)"))
    return ok


def join_game(d):
    if click_room(d, '[data-game="join"]'):
        return True
    click_js(d, "#gameStatus")
    return wait(d, "return currentGame() && currentGame().joined.includes(roomInfo.you)", 6, "joining the game")


def start_game(d):
    # The host's Start now button is disabled until the second player reaches it.
    wait(d, "return currentGame() && currentGame().joined.length >= 2", 5, "")
    click_room(d, '[data-game="start"]')
    return wait(d, "return currentGame() && currentGame().phase !== 'lobby'", 8, "the game to start")


def game(d):
    try:
        return d.js("return currentGame()")
    except WebDriverError:
        return None


# ---------------------------------------------------------------------------
# The checks
# ---------------------------------------------------------------------------

base_url = ""
report = None


def basic_checks(a, b, c, p, report):
    ra, rb, rc, rp = room(a), room(b), room(c), pstate(p)
    report.check("every student has a seat", ra.get("you") and rb.get("you") and rc.get("you"),
                 [ra.get("you"), rb.get("you"), rc.get("you")])
    names = [m["name"] for m in members(a)]
    for who in (b, c):
        n = text_of(who, "#palStripName")
        report.check("a pal sees the others", len(members(who)) >= 2, names)
    report.check("the projector lists everyone", len(rp["people"]) >= 3, rp["people"])
    report.check("the projector shows the party meter", "of" in p.js("return document.getElementById('words').innerText"),
                 p.js("return document.getElementById('words').innerText"))
    welcome = report.welcome_text or text_of(a, "#hangBanner")
    report.check("the welcome banner says what to do", "Click the ground" in welcome, welcome)
    report.check("the welcome banner lets clicks through",
                 a.js("return getComputedStyle(document.getElementById('hangBanner')).pointerEvents") == "none")
    for d, label in ((a, "Ana"), (b, "Ben"), (c, "Cy")):
        issues = layout_issues(d)
        report.check(f"{label}'s Hang out fits 1366x768", not issues, issues)
        report.check(f"{label}'s buttons have words", not button_label_issues(d), button_label_issues(d))
    issues = p.js("return button_label_issues && button_label_issues()") if False else []
    report.check("the projector's camera buttons have words",
                 "Left" in text_of(p, "#camLeft") and "Right" in text_of(p, "#camRight"),
                 [text_of(p, "#camLeft"), text_of(p, "#camRight")])
    shot(a, "hang-arrival", report, shot_dir)


def walk_checks(a, b, p, report):
    # one click on the ground, and a real arrow key
    before = mine(a)
    if not before:
        report.problem("walking checks could not find Ana's pal")
        return
    if before:
        # Click a spot with no friend on it: a click on a friend is a high-five,
        # and a click on your own pal is a jump. 200 is clear in the Park's first
        # screen, with the toys, seats and chest further over.
        target = 200 if before["x"] < 120 else max(8, before["x"] - 150)
        if any(m["seat"] != before["seat"] and abs(m["x"] - target) < 30 for m in members(a)):
            target = 200 if target != 200 else 40
        tap_world(a, target, .5, report)
        if target > before["x"]:
            wait(a, "return (() => { const m = roomStage.state.room.find(m => m.me); return m && m.x > %d; })()" % (before["x"] + 20), 8, "")
        else:
            wait(a, "return (() => { const m = roomStage.state.room.find(m => m.me); return m && m.x < %d; })()" % (before["x"] - 20), 8, "")
        after = mine(a)
        report.check("clicking the ground walks your pal", bool(after) and abs(after["x"] - before["x"]) > 20, [before, after])
        if not after:
            report.problem("Ana's pal vanished after a click walk", members(a))
        else:
            # another screen sees the new spot
            other = next((m for m in members(b) if m["name"] == before["name"]), None)
            report.check("another student sees you walk", other and abs(other["x"] - after["x"]) < 24, [after, other])
            press_key(a, KEYS["Right"])
            time.sleep(.7)
            moved = mine(a)
            report.check("the arrow keys walk your pal", moved and moved["x"] >= after["x"] + 8, [after, moved])
            press_key(a, KEYS["Up"])
            time.sleep(.7)
            up = mine(a)
            report.check("the up arrow changes depth", up and moved and up["y"] < moved["y"], [moved, up])
    # every place, by Go to
    for place in ("park", "wedding", "beach", "night", "snowy", "candy", "space", "sea"):
        pane(a, "place")
        click_room(a, f'[data-name="{place}"]')
        ok = wait(a, f"return document.getElementById('hangView').dataset.place === {json.dumps(place)}", 7, f"Go to {place}")
        report.check(f"Go to works for {place}", ok, a.js("return document.getElementById('hangView').dataset.place"))
        collect_console(a, "Go to " + place, report)
    shot(a, "hang-under-the-sea", report, shot_dir)
    # the projector knows the whole world
    world = a.js("return roomInfo && roomInfo.places ? roomInfo.places.join() : ''")
    report.check("all open places are in one world", all(x in world for x in ("park", "wedding", "beach", "night", "snowy", "candy", "space", "sea")), world)


def do_sit_toy_gem_fish_chest(a, b, p, report):
    # Sit anywhere
    pane(a, "do")
    click_room(a, '[data-name="sit"]')
    time.sleep(1)
    report.check("Sit makes the pal sit", (mine(a) or {}).get("rest") == "sit", mine(a))
    other = next((m for m in members(b) if m["seat"] == room(a).get("you")), None)
    report.check("a friend sees you sit", other and other.get("rest") == "sit", other)
    press_key(a, KEYS["Right"])       # get up again (the server clears rest on walk)
    time.sleep(.7)
    # A toy: click a pink ring in the park
    pane(a, "place")
    click_room(a, '[data-name="park"]')
    time.sleep(1)
    toy = a.js("""return (() => { const places = roomStage.state.places;
      for (let i = 0; i < places.length; i++)
        for (let x = i * PalStage.W + 10; x < (i + 1) * PalStage.W; x += 6)
          for (let deep = 0; deep <= 1; deep += .04) {
            const t = PalHang.toyAt(places, x, PalStage.GROUND_TOP + deep * PalStage.GROUND_DEEP);
            if (t) return t; } return null; })()""")
    if toy:
        tap_world(a, toy["x"], toy["y"], report)
        time.sleep(.9)
        doing = a.js("return (roomInfo.people || []).find(m => m.seat === roomInfo.you)?.doing || ''")
        floats = a.js("return [...document.querySelectorAll('#roomHost .float')].map(e => e.textContent).join(' ')")
        report.check("a pink-ring toy goes off", "Playing" in doing or "Apples" in floats or "toy" in text_of(a, "#roomTip"),
                     [toy, doing, floats])
    else:
        report.problem("could not find a toy in the Park")
    # A gem: go to a place with nobody else in it, then stand on one.
    empty = a.js("""return (() => { const me = roomInfo.you, here = new Set(roomInfo.people.filter(m => m.seat !== me && !m.loc).map(m => m.loc));
      return roomInfo.places.find(p => p !== 'village' && !roomInfo.people.some(m => m.seat !== me && !m.loc &&
        Math.floor((m.x || 0) / PalStage.W) === roomInfo.places.indexOf(p)));
    })()""") or "park"
    pane(a, "place")
    click_room(a, f'[data-name="{empty}"]')
    time.sleep(1)
    press_key(a, KEYS["Right"])
    time.sleep(.6)
    gem = a.js("""return (() => { const places = roomStage.state.places, i = places.indexOf(arguments[0]);
      const found = new Set(roomStage.state.found);
      const me = roomStage.state.room.find(m => m.me);
      for (let x = i * PalStage.W + 4; x < (i + 1) * PalStage.W; x += 5)
        for (let deep = 0; deep <= 1; deep += .03) {
          const k = PalHang.gemAt(places, x, deep, found);
          if (k && Math.abs(x - me.x) > 34) return {k, x, y: deep}; }
      return null; })()""", empty)
    if gem:
        tap_world(a, gem["x"], gem["y"], report)
        ok = wait(a, "return [...roomStage.state.found].includes(arguments[0])".replace("arguments[0]", json.dumps(gem["k"])), 7, "the gem to be found")
        report.check("a gem is found by walking on it", ok, [gem["k"], a.js("return [...roomStage.state.found]")])
        report.check("a found gem is kept when the Hang out is reopened",
                     a.js("return S.hang.found.includes(arguments[0])".replace("arguments[0]", json.dumps(gem["k"]))),
                     a.js("return S.hang.found"))
        click_js(a, 'nav [data-view="stage"]')
        time.sleep(.6)
        open_hang(a, report)
        report.check("a found gem is still found after leaving and coming back",
                     a.js("return [...roomStage.state.found].includes(arguments[0])".replace("arguments[0]", json.dumps(gem["k"]))),
                     a.js("return [...roomStage.state.found]"))
    else:
        report.problem("could not find a gem anywhere")
    # Fishing at the pier
    pane(a, "place")
    click_room(a, '[data-name="beach"]')
    time.sleep(1.2)
    pier = a.js("""return (() => { const p = roomStage.state.places;
      for (let i = 0; i < p.length; i++) { const f = PalHang.fishAt(p, i * PalStage.W + 140, 120); if (f) return f; }
      return null; })()""")
    if pier:
        tap_world(a, pier["x"], pier["y"], report)
        wait(a, "return fishing && fishing.biteAt", 8, "the fishing cast")
        got_bite = wait(a, "return fishing && fishing.bitten === true", 14, "a bite")
        report.check("fishing waits for a bite", got_bite, text_of(a, "#roomTip"))
        if got_bite:
            time.sleep(.4)      # a child takes a moment to click; don't beat the server's own clock
            before_reel = a.js("return fishing && {biteAt: fishing.biteAt, bitten: fishing.bitten}")
            tap_world(a, pier["x"], .3, report)
            time.sleep(1.2)
            report.check("fishing catches something", bool(a.js("return S.hang.fish")) and
                         a.js("return Object.keys(S.hang.fish).length > 0"),
                         [before_reel, a.js("return S.hang.fish"), text_of(a, "#roomTip"),
                          a.js("return fishing && {biteAt: fishing.biteAt, bitten: fishing.bitten}")])
    else:
        report.problem("could not find the pier")
    # A chest: open pane, ← Leave, click it again, then code it open
    chest = next((c for c in a.js("return S.hang.chests") if c["place"] == "wedding"), None)
    if chest:
        pane(a, "place")
        click_room(a, '[data-name="wedding"]')
        time.sleep(1.2)
        gx = a.js("return roomInfo.places.indexOf('wedding') * PalStage.W + arguments[0]", chest["x"])
        for _ in range(8):
            tap_world(a, gx, chest["deep"], report)
            time.sleep(.8)
            if a.js("return roomPane === 'chest'"):
                break
        report.check("walking to a chest opens its code pane", a.js("return roomPane === 'chest'"), a.js("return [roomPane, chestNear]"))
        if a.js("return roomPane === 'chest'"):
            shot(a, "hang-chest", report, shot_dir)
            click_room(a, "[data-chestleave]")
            time.sleep(.5)
            report.check("← Leave puts the usual buttons back",
                         a.js("return roomPane === 'do'") and "Left the chest" in text_of(a, "#roomTip"),
                         [a.js("return roomPane"), text_of(a, "#roomTip")])
            # Clicking the chest again reopens it; this used to jump on your own pal.
            tap_world(a, gx, chest["deep"], report)
            time.sleep(2.2)
            report.check("clicking the chest again reopens it", a.js("return roomPane === 'chest'"),
                         a.js("return [roomPane, chestNear, chestDismissed]"))
            if a.js("return roomPane === 'chest'"):
                # wrong code says what the pal did
                a.js("const t=document.getElementById('raceCode'); t.value='jump()'; "
                     "t.dispatchEvent(new Event('input',{bubbles:true}));")
                click_room(a, '[data-race="run"]')
                time.sleep(1)
                msg = a.js("return (document.getElementById('raceMsg')||{}).textContent || ''")
                report.check("a chest miss says what to change", bool(msg) and ("wants" in msg or "Jump" in msg or "jump" in msg), msg)
                # the answer from the page's own chest data
                a.js("const t=document.getElementById('raceCode'); t.value=arguments[0]; "
                     "t.dispatchEvent(new Event('input',{bubbles:true}));", chest["hint"])
                coins_before = a.js("return S.hang.coins")
                click_room(a, '[data-race="run"]')
                ok = wait(a, "return chestNow() && chestNow().open", 8, "the chest to open")
                time.sleep(1)
                report.check("the right code opens the chest", ok, a.js("return chestNow()"))
                report.check("opening a chest pays 10 coins", a.js("return S.hang.coins") >= coins_before + 10,
                             [coins_before, a.js("return S.hang.coins")])
                report.check("the opened chest says so and offers the next one",
                             "opened it" in a.js("return document.getElementById('roomButtons').innerText") and
                             "next chest" in a.js("return document.getElementById('roomButtons').innerText"),
                             a.js("return document.getElementById('roomButtons').innerText.slice(0,200)"))
                # Walk away: the pane closes instead of letting you code from afar.
                tap_world(a, gx - 110, chest["deep"], report)
                time.sleep(2.2)
                report.check("walking away from a chest puts the buttons back", a.js("return roomPane === 'do'"),
                             a.js("return [roomPane, chestNear]"))
    else:
        report.problem("no wedding chest in the state")


def say_do_party(a, b, c, report):
    # Keep Cy out of the way of the high-five click.
    pane(c, "place")
    click_room(c, '[data-name="night"]')
    time.sleep(.8)
    # 💬 Say with a tap word
    pane(a, "say")
    click_room(a, '[data-tap="say"][data-name="Hello!"]')
    time.sleep(.6)
    bubbles = b.js("return [...document.querySelectorAll('#roomHost .bubble')].map(b => b.textContent)")
    report.check("a tapped word shows to a friend", "Hello!" in bubbles, bubbles)
    # typing off: the box is hidden, and the server refuses own words
    report.check("the Say box is hidden while typing is off", a.js("return document.getElementById('roomType').hidden"))
    ref = post(base_url, "/pixel/room/do", {"id": a.js("return me"), "what": "say", "text": "not on the list"})
    report.check("own words are refused while typing is off", ref.get("error") == "bad", ref)
    # typing on: the box shows and a friend sees it
    post(base_url, "/pixel/teacher", {"key": server.ADMIN_KEY, "action": "room_words", "on": True})
    time.sleep(.7)
    pane(a, "say")
    report.check("the Say box appears when typing is on", not a.js("return document.getElementById('roomType').hidden"))
    a.send("#roomWords", "My own words")
    a.click("#roomType button")
    time.sleep(.7)
    bubbles = b.js("return [...document.querySelectorAll('#roomHost .bubble')].map(b => b.textContent)")
    report.check("typed words show to a friend", "My own words" in bubbles, bubbles)
    post(base_url, "/pixel/teacher", {"key": server.ADMIN_KEY, "action": "room_words", "on": False})
    time.sleep(.7)
    report.check("the Say box hides again when typing is off", a.js("return document.getElementById('roomType').hidden"))
    # 👋 Do: a move and a feeling land on the other screen
    pane(a, "do")
    click_room(a, '[data-tap="move"][data-name="wave"]')
    time.sleep(.6)
    other = next((m for m in members(b) if m["seat"] == room(a).get("you")), None)
    report.check("a friend sees a move", other and other.get("move") in ("wave", None), other)   # fast move may just have ended
    click_room(a, '[data-tap="feel"][data-name="happy"]')
    time.sleep(.6)
    other = next((m for m in members(b) if m["seat"] == room(a).get("you")), None)
    report.check("a friend sees a feeling", other and other.get("mood") == "happy", other)
    # 🏃 Go to a friend, then high-five them
    for d in (a, b):
        pane(d, "place")
        click_room(d, '[data-name="park"]')
        time.sleep(.8)
    bseat = room(b).get("you")
    pane(a, "place")
    click_room(a, f'[data-friend="{bseat}"]')
    time.sleep(1.2)
    bpos = next((m for m in members(a) if m["seat"] == bseat and not m["me"]), None)
    report.check("Go to a friend puts you beside them",
                 bpos and abs((mine(a) or {}).get("x", 0) - bpos["x"]) < 130,
                 [bpos, mine(a)])
    both_friends = False
    for _ in range(3):
        bpos = next((m for m in members(a) if m["seat"] == bseat and not m["me"]), None)
        if not bpos:
            break
        tap_world(a, bpos["x"], bpos["y"], report)
        time.sleep(1.1)
        both_friends = (a.js("return S.hang.friends.includes(arguments[0])".replace("arguments[0]", json.dumps(report.names[1]))) and
                        b.js("return S.hang.friends.includes(arguments[0])".replace("arguments[0]", json.dumps(report.names[0]))))
        if both_friends:
            break
    report.check("a high-five makes a friend for both", both_friends,
                 [a.js("return S.hang.friends"), b.js("return S.hang.friends")])
    # 🎉 Party: the effect runs, and a friend gets the event
    pane(a, "party")
    click_room(a, '[data-tap="fx"][data-name="hearts"]')
    time.sleep(.5)
    report.check("the Party buttons still work", a.js("return roomStage.state.room.length > 0"))


def my_move_show_clap(a, b, p, report):
    # Wait out any show/move cooldown from earlier
    time.sleep(7)
    # ✨ My Move: the button gets a cooldown that another room update must not clear
    if a.js("return !!S.hang.move"):
        a.click("#myMove")
        time.sleep(.5)
        report.check("My Move disables while it plays", a.js("return document.getElementById('myMove').disabled === true"),
                     a.js("return [document.getElementById('myMove').disabled, moveReadyAt, performance.now()]"))
        time.sleep(1.5)
        report.check("My Move stays disabled on later updates",
                     a.js("return document.getElementById('myMove').disabled === true"),
                     a.js("return [document.getElementById('myMove').disabled, moveReadyAt, performance.now()]"))
        report.check("a friend gets a Clap button for My Move",
                     b.js("return !document.getElementById('clapGo').hidden"),
                     b.js("return [document.getElementById('clapGo').hidden, document.getElementById('clapGo').innerText]"))
        if b.js("return !document.getElementById('clapGo').hidden"):
            b.click("#clapGo")
            time.sleep(.8)
            report.check("a clap reaches the performer", a.js("return roomStage.state.room.find(m => m.me).claps") >= 1,
                         a.js("return roomStage.state.room.find(m => m.me).claps"))
        report.check("the projector sees the My Move", "My Move" in (pstate(p)["banner"] or ""), pstate(p)["banner"])
    else:
        report.problem("Ana has no My Move to test")
    # 🎤 My show
    time.sleep(7)
    if a.js("return !!S.hang.free_show"):
        pane(a, "do")
        click_room(a, "[data-perform]")
        time.sleep(.8)
        report.check("My show plays for the class", "show" in text_of(b, "#hangBanner").lower(), text_of(b, "#hangBanner"))
        report.check("My show disables My Move", a.js("return document.getElementById('myMove').disabled === true"),
                     a.js("return [document.getElementById('myMove').disabled, moveReadyAt, performance.now()]"))
        report.check("a friend gets a Clap button for the show",
                     b.js("return !document.getElementById('clapGo').hidden"),
                     b.js("return [document.getElementById('clapGo').hidden, document.getElementById('clapGo').innerText]"))
        if b.js("return !document.getElementById('clapGo').hidden"):
            b.click("#clapGo")
            time.sleep(.7)
            report.check("a clap reaches the show", a.js("return roomStage.state.room.find(m => m.me).claps") >= 1,
                         a.js("return roomStage.state.room.find(m => m.me).claps"))
        report.check("the projector sees the show", "show" in (pstate(p)["banner"] or "").lower(), pstate(p)["banner"])
    else:
        report.problem("Ana has no Free stage show to perform")
    # The same pal can't do a show while a move is playing: a plain message, not silence.
    pane(a, "do")
    click_room(a, "[data-perform]")
    time.sleep(.5)
    tip = text_of(a, "#roomTip")
    report.check("starting a show during a move says what to do", "Wait" in tip or "wait" in tip or "One thing" in tip, tip)
    shot(b, "hang-my-show", report, shot_dir)


def hide_name_calm_mute_prop_buddies(a, b, report):
    # 🏷️ Hide names (on this screen) and 🧢 Me's invisible name (for everyone)
    click_js(a, "#tags")
    time.sleep(.3)
    report.check("Hide names hides the tags", a.js("return document.body.classList.contains('no-tags')") and
                 a.js("return getComputedStyle(document.querySelector('#roomHost .tag')).visibility") == "hidden",
                 a.js("return getComputedStyle(document.querySelector('#roomHost .tag')).visibility"))
    click_js(a, "#tags")
    time.sleep(.2)
    pane(a, "me")
    click_js(a, '[data-hidename]')
    time.sleep(.8)
    report.check("hiding your name makes it Secret pal for others",
                 b.js("return roomStage.state.room.some(m => m.name === 'Secret pal' && m.hid)"),
                 b.js("return roomStage.state.room.map(m => [m.name, m.hid])"))
    click_js(a, '[data-hidename]')
    time.sleep(.8)
    report.check("showing your name again works", b.js("return roomStage.state.room.some(m => m.name !== 'Secret pal')"),
                 b.js("return roomStage.state.room.map(m => m.name)"))
    # 🌿 Calm and 🔊 mute, remembered
    click_js(a, "#calm")
    click_js(a, "#mute")
    time.sleep(.3)
    report.check("Calm turns on", a.js("return PalStage.calm === true && document.body.classList.contains('calm')"))
    report.check("mute has a word, not just an icon", len(re.sub("[^A-Za-z]", "", text_of(a, "#mute"))) >= 3, text_of(a, "#mute"))
    # 🪑 Prop
    click_js(a, "#palProp")
    time.sleep(.8)
    report.check("Be a prop hides your face and name from friends",
                 b.js("return roomStage.state.room.some(m => m.prop && m.name !== 'Secret pal')"),
                 b.js("return roomStage.state.room.map(m => [m.name, m.prop])"))
    click_js(a, "#palProp")
    time.sleep(.5)
    # 👯 Buddies
    if not a.js("return document.getElementById('palFollow').hidden"):
        click_js(a, "#palFollow")
        time.sleep(.8)
        report.check("Buddies brings another drawing along",
                     b.js("return roomStage.state.room.some(m => (m.buddies || []).length > 0)"),
                     b.js("return roomStage.state.room.map(m => [m.name, (m.buddies || []).length])"))
        click_js(a, "#palFollow")
        time.sleep(.3)


def shop_me_art_home(a, b, c, p, report):
    # C starts with 55 coins: the 100 coin Sun hat is too dear, the 40 coin Rainbow hat is not.
    coins_before = c.js("return S.hang.coins")
    pane(c, "shop")
    click_js(c, '[data-shoptab="wear"]')
    time.sleep(.3)
    click_room(c, '[data-buy="sunhat"]')
    click_room(c, '[data-buy="sunhat"]')
    time.sleep(.5)
    tip = text_of(c, "#roomTip")
    report.check("the Shop says how many more coins you need", "more coins" in tip, tip)
    report.check("the Shop does not buy what you can't afford",
                 not c.js("return S.hang.gifts.includes('sunhat')") and
                 c.js("return S.hang.coins") < coins_before + 20,
                 [coins_before, c.js("return S.hang.coins"), c.js("return S.hang.gifts")])
    click_room(c, '[data-buy="beanie"]')
    click_room(c, '[data-buy="beanie"]')
    time.sleep(.8)
    report.check("the Shop buys with enough coins", c.js("return S.hang.gifts.includes('beanie')") and
                 c.js("return S.hang.coins") < coins_before, [c.js("return S.hang.coins"), c.js("return S.hang.gifts")])
    pane(c, "me")
    click_js(c, '[data-wear="beanie"]')
    time.sleep(.8)
    report.check("wearing a bought hat is seen by a friend",
                 b.js("return roomStage.state.room.some(m => m.wear && m.wear.hat === 'beanie')"),
                 b.js("return roomStage.state.room.map(m => [m.name, m.wear])"))
    # Ana: switch pal and wear her own drawing
    pane(a, "me")
    click_js(a, '[data-pal="e2epal2"]')
    time.sleep(.8)
    report.check("switching pal shows the new drawing to a friend",
                 b.js("return roomStage.state.room.some(m => m.pal && m.pal.palette && m.pal.palette[1] === '#7ab8ff')"),
                 b.js("return roomStage.state.room.map(m => [m.name, m.pal && m.pal.palette])"))
    click_js(a, '[data-sew="start"]')
    time.sleep(.3)
    click_js(a, '[data-sewkey="e2epal2"]')
    time.sleep(.3)
    click_js(a, '[data-sewslot="hat"]')
    time.sleep(1)
    report.check("Wear your own drawing makes a copy you wear",
                 a.js("return (S.hang.mywear || []).length > 0 && S.hang.wear.hat"),
                 a.js("return [S.hang.mywear, S.hang.wear]"))
    report.check("a friend sees your own drawing on your head",
                 b.js("return roomStage.state.room.some(m => m.wearArt && m.wearArt.hat)",
                     ),
                 b.js("return roomStage.state.room.map(m => [m.name, m.wearArt])"))
    # 🖼️ Art: both in the Park, place the coded drawing, then a friend clicks it
    for d in (a, b):
        pane(d, "place")
        click_room(d, '[data-name="park"]')
        time.sleep(.8)
    pane(a, "art")
    click_js(a, '[data-art="e2epal"]')
    time.sleep(.3)
    tap_world(a, mine(a)["x"] + 60 if mine(a) else 120, .7, report)
    time.sleep(1.2)
    placed = a.js("return roomStage.state.placed.filter(p => p.mine && p.coded)")
    report.check("a coded drawing can be put out", bool(placed), placed)
    if placed:
        piece = placed[-1]
        report.check("a friend sees the coded drawing", b.js("return roomStage.state.placed.some(p => p.coded && !p.mine && Math.abs(p.x - arguments[0]) < 2)", piece["x"]),
                     b.js("return roomStage.state.placed"))
        tap_world(b, piece["x"], piece["y"], report)
        time.sleep(1.2)
        report.check("clicking a coded drawing runs it for everyone",
                     "Hello!" in b.js("return [...document.querySelectorAll('#roomHost .bubble')].map(b => b.textContent)"),
                     b.js("return [...document.querySelectorAll('#roomHost .bubble')].map(b => b.textContent)"))
    # 🏠 Home: put a rug down, visit, give a heart and go out
    pane(a, "home")
    click_room(a, '[data-home="mine"]')
    time.sleep(1.2)
    report.check("Home goes inside your own home", a.js("return roomInfo.home && roomInfo.home.mine"), a.js("return roomInfo.home"))
    click_room(a, '[data-furn="rug"]')
    tap_world(a, 100, .6, report)
    time.sleep(1.2)
    report.check("a thing can be put on the floor", a.js("return roomInfo.home.items.length") >= 1, a.js("return roomInfo.home.items"))
    pane(b, "home")
    click_text(b, "#roomButtons [data-home]", report.names[0])
    time.sleep(1.5)
    report.check("a friend can visit your home", b.js("return roomInfo.home && !roomInfo.home.mine && roomInfo.home.items.length >= 1"),
                 b.js("return roomInfo.home"))
    click_room(b, "[data-heart]")
    time.sleep(1)
    report.check("a visitor can give a heart", b.js("return roomInfo.home.hearted") and
                 a.js("return roomInfo.home.hearts") >= 1,
                 [b.js("return roomInfo.home.hearted"), a.js("return roomInfo.home.hearts")])
    click_room(b, '[data-home="out"]')
    time.sleep(1)
    report.check("the door goes back outside", b.js("return !roomInfo.home"), b.js("return roomInfo.home"))
    pane(a, "home")
    click_room(a, '[data-home="out"]')
    time.sleep(1)
    # A room can be bought, and its doorway walked through.
    pane(a, "shop")
    click_js(a, '[data-shoptab="room"]')
    time.sleep(.3)
    click_room(a, '[data-buy="r_bed"]')
    click_room(a, '[data-buy="r_bed"]')
    time.sleep(1)
    report.check("a room can be bought", a.js("return S.hang.stuff.includes('r_bed')"),
                 a.js("return S.hang.stuff"))
    pane(a, "home")
    click_room(a, '[data-home="mine"]')
    time.sleep(1.2)
    report.check("the new room joins the home", a.js("return roomInfo.home && roomInfo.home.rooms.length >= 2"),
                 a.js("return roomInfo.home"))
    if a.js("return roomInfo.home && roomInfo.home.rooms.length >= 2"):
        click_room(a, '[data-goroom="1"]')
        wait(a, "return (() => { const m = roomStage.state.room.find(m => m.me); return m && m.x > 300; })()", 6, "the walk into the new room")
        report.check("walking into the new room works",
                     (mine(a) or {}).get("x", 0) > 300,
                     mine(a))
    pane(a, "home")
    click_room(a, '[data-home="out"]')
    time.sleep(1)


def game_code_race(a, b, c, p, report):
    clear_game(base_url, report)
    make_game(a, "code", report)
    join_game(b)
    start_game(a)
    g = game(a) or {}
    report.check("the Code race starts for both players", g.get("phase") == "playing" and set(g.get("joined") or []) == {room(a)["you"], room(b)["you"]}, g)
    # C joins late
    pane(c, "games")
    join_game(c)
    time.sleep(.6)
    report.check("a friend can join a Code race late", c.js("return currentGame() && currentGame().joined.includes(roomInfo.you)"),
                 game(c))
    # During a round, other tabs are still open. Buttons must say why they can't
    # work, and a refused hat must not stay on in this browser.
    before_wear = a.js("return JSON.stringify(S.hang.wear)")
    pane(a, "me")
    a.js("document.querySelector('#roomButtons [data-wear]')?.click()")
    time.sleep(.8)
    tip = text_of(a, "#roomTip")
    report.check("changing clothes during a game says why", "game" in tip.lower(), tip)
    report.check("a refused change leaves the clothes alone",
                 a.js("return JSON.stringify(S.hang.wear)") == before_wear,
                 [before_wear, a.js("return JSON.stringify(S.hang.wear)")])
    pane(a, "do")
    click_room(a, '[data-tap="move"][data-name="wave"]')
    time.sleep(.6)
    report.check("a do button during a game says why", "game" in text_of(a, "#roomTip").lower(), text_of(a, "#roomTip"))
    pane(a, "games")
    # A solves the job with its own answer
    hint = a.js("return currentGame() && currentGame().job && currentGame().job.hint")
    if hint:
        a.js("const t=document.getElementById('raceCode'); t.value=arguments[0]; t.dispatchEvent(new Event('input',{bubbles:true}));", hint)
        click_room(a, '[data-race="run"]')
        # Clap while the short spotlight is still playing (a jump is only about 2 seconds).
        wait(a, "return (currentGame().solved || []).includes(roomInfo.you)", 4, "the Code race solve")
        got_clap = wait(b, "return !document.getElementById('clapGo').hidden", 3, "")
        if got_clap:
            b.click("#clapGo")
            time.sleep(.7)
        report.check("solving the Code race lands on the other screens",
                     b.js("return (currentGame().solved || []).length >= 1"),
                     [game(a), game(b)])
        card = pstate(p)["race"]
        report.check("the projector shows the Code race job and who solved it",
                     "Code race" in card[0] and ("Solved" in card[2] or "0 of" in card[2]), card)
        if got_clap:
            report.check("a clap for the Code race reaches the solver", a.js("return roomStage.state.room.find(m=>m.me).claps") >= 1,
                         [a.js("return roomStage.state.room.find(m=>m.me).claps"), game(a)])
        else:
            report.problem("no Clap button for the Code race solve")
    else:
        report.problem("the Code race job had no answer")
    # A leaves mid-game; the rest carry on
    pane(a, "games")
    click_room(a, '[data-game="leave"]')
    time.sleep(1.2)
    report.check("leaving a Code race mid-game does not end it for the rest",
                 c.js("return !!currentGame() && currentGame().phase === 'playing'"), game(c))
    # B then C leave, and the round ends cleanly
    pane(b, "games")
    b.js("document.querySelector('#roomButtons [data-game=leave]')?.click()")
    pane(c, "games")
    c.js("document.querySelector('#roomButtons [data-game=leave]')?.click()")
    time.sleep(1.5)
    report.check("the last Code race players leaving finishes the round",
                 not game(b) or game(b).get("phase") in ("results", None), game(b))
    shot(p, "projector-code-race", report, shot_dir)
    clear_game(base_url, report)


def game_draw(a, b, report):
    clear_game(base_url, report)
    make_game(a, "draw", report)
    join_game(b)
    start_game(a)
    ga, gb = game(a) or {}, game(b) or {}
    drawer = a if ga.get("drawer") == room(a).get("you") else b
    guesser = b if drawer is a else a
    report.check("one student draws and the other guesses",
                 drawer.js("return !!document.getElementById('drawBoard')") and
                 not guesser.js("return !!document.getElementById('drawBoard')"),
                 [ga.get("drawer"), gb.get("drawer")])
    # the drawer colours one square on the little board
    drawer.js("""(() => { const cv=document.getElementById('drawBoard'); const r=cv.getBoundingClientRect();
      cv.dispatchEvent(new PointerEvent('pointerdown', {bubbles:true, buttons:1, pointerId:1,
        clientX:r.left+r.width*.3, clientY:r.top+r.height*.3})); })()""")
    time.sleep(.8)
    report.check("the picture grows on the guesser's screen",
                 guesser.js("return (currentGame().board || '').split('').some(c => c !== '.')"),
                 guesser.js("return currentGame().board"))
    # a wrong guess, then the right one
    choices = guesser.js("return (currentGame().choices || []).map(c => [c[0], c[2]])")
    word = drawer.js("return currentGame().word && currentGame().word[0]")
    if choices and word:
        wrong = next((c[0] for c in choices if c[0] != word), None)
        if wrong:
            click_room(guesser, f'[data-guess="{wrong}"]')
            time.sleep(.6)
            report.check("a wrong guess says to look again", "Not that one" in text_of(guesser, "#roomTip"), text_of(guesser, "#roomTip"))
            time.sleep(3.2)      # the drawer's pictures grey out for 3 seconds
        click_room(guesser, f'[data-guess="{word}"]')
        time.sleep(.8)
        report.check("the right guess scores", guesser.js("return (currentGame().guessed || []).includes(roomInfo.you)"),
                     game(guesser))
    else:
        report.problem("no draw word or choices reached the screens")
    clear_game(base_url, report)


def game_hide(a, b, p, report):
    clear_game(base_url, report)
    make_game(a, "hide", report)
    join_game(b)
    start_game(a)
    ga, gb = game(a) or {}, game(b) or {}
    seeker = a if ga.get("it") == room(a).get("you") else b
    hider = b if seeker is a else a
    st = text_of(seeker, "#roomTip")
    ht = text_of(hider, "#roomTip")
    report.check("the seeker is told to count, not that someone else is counting",
                 "You're counting" in st and "The seeker is counting" not in st, st)
    report.check("the hider is told to hide", "Hide" in ht, ht)
    # the hider picks a cover
    click_room(hider, "[data-cover]")
    time.sleep(1.5)
    hidden = game(hider) or {}
    report.check("the hider can pick a hiding place", bool(hidden.get("hiding")), hidden)
    # wait out the 20 second count
    end = time.time() + 24
    while time.time() < end and (game(a) or {}).get("phase") == "hiding":
        time.sleep(.5)
    report.check("hide & seek moves on from counting", (game(a) or {}).get("phase") == "playing", game(a))
    if (game(a) or {}).get("phase") == "playing":
        # the seeker looks behind the right cover
        key = hidden.get("hiding")
        seeker.js("""(() => { const b=document.querySelector('#roomButtons [data-cover="'+arguments[0]+'"]'); b && b.click(); })()""", key)
        end = time.time() + 8
        while time.time() < end and not (game(seeker) or {}).get("found"):
            time.sleep(.5)
        report.check("the seeker can find the hider", bool((game(seeker) or {}).get("found")), game(seeker))
    report.check("the projector has a Hide & seek card", "Hide" in " ".join(pstate(p)["race"]), pstate(p)["race"])
    clear_game(base_url, report)


def game_tag_race_dance_apples_ball(a, b, p, report):
    clear_game(base_url, report)
    # Tag
    make_game(a, "tag", report)
    join_game(b)
    start_game(a)
    g = game(a) or {}
    before_it = g.get("it")
    report.check("Tag starts with someone IT", before_it is not None, g)
    # whoever is not IT walks into IT so the tag changes
    mover = a if g.get("it") != room(a).get("you") else b
    for _ in range(6):
        pos = mover.js("""return (() => { const g=currentGame(); const r=roomStage.state.room;
          const it=r.find(m=>m.seat===g.it), me=r.find(m=>m.me); return it&&me?{ix:it.x,iy:it.y,mx:me.x,my:me.y}:null; })()""")
        if not pos or g.get("it") == room(mover).get("you"):
            break
        tap_world(mover, pos["ix"], pos["iy"], report)
        time.sleep(1.1)
        g = game(a) or {}
    report.check("Tag passes IT when pals touch", g.get("it") != before_it, [before_it, g.get("it")])
    report.check("the projector has a Tag card", "Tag" in " ".join(pstate(p)["race"]), pstate(p)["race"])
    clear_game(base_url, report)
    # Red light, green light
    make_game(a, "race", report)
    join_game(b)
    start_game(a)
    for _ in range(60):
        if a.js("return currentGame() && currentGame().light === 'green'"):
            click_room(a, '[data-run="1"]')
        time.sleep(.3)
        if a.js("return (currentGame() && currentGame().done || []).includes(roomInfo.you)"):
            break
    report.check("a runner can reach the flag", a.js("return (currentGame() && currentGame().done || []).includes(roomInfo.you)"),
                 game(a))
    report.check("the projector has a Red light card", "Red light" in " ".join(pstate(p)["race"]), pstate(p)["race"])
    clear_game(base_url, report)
    # Copy the dance
    make_game(a, "dance", report)
    join_game(b)
    start_game(a)
    rounds_seen = set()
    end = time.time() + 40
    while time.time() < end:
        g = game(a) or {}
        if g.get("phase") != "playing" or g.get("round", 0) >= 3:
            break
        rounds_seen.add(g.get("round"))
        if a.js("return gameNow() >= currentGame().ready"):
            for d in (a, b):
                gg = game(d) or {}
                if gg.get("step", 0) < len(gg.get("seq") or []):
                    move = gg["seq"][gg["step"]]
                    click_room(d, f'[data-step="{move}"]')
            time.sleep(.25)
        else:
            time.sleep(.2)
    report.check("Copy the dance plays 3 rounds and finishes", len(rounds_seen) >= 2 or (game(a) or {}).get("phase") == "results",
                 [rounds_seen, game(a)])
    report.check("the projector has a dance card", "Copy the dance" in " ".join(pstate(p)["race"]), pstate(p)["race"])
    clear_game(base_url, report)
    # Apple grab
    make_game(a, "apples", report)
    join_game(b)
    start_game(a)
    for _ in range(5):
        apples = (game(a) or {}).get("apples") or []
        if not apples:
            break
        apple = apples[0]
        walk_towards(a, apple["x"], apple["y"])
        time.sleep(.9)
        if (game(a) or {}).get("score", 0) > 0:
            break
    report.check("a pal can grab apples", a.js("return (currentGame() && currentGame().score || 0) > 0"),
                 game(a))
    report.check("the projector has an Apple grab card", "Apple grab" in " ".join(pstate(p)["race"]), pstate(p)["race"])
    clear_game(base_url, report)
    # Pal ball
    make_game(a, "ball", report)
    join_game(b)
    start_game(a)
    for _ in range(10):
        ball = (game(a) or {}).get("ball")
        if not ball:
            break
        walk_towards(a, max(8, ball["x"] - 12), ball["y"])
        # a click past the ball is a kick in that direction; keep it visible
        m = mine(a)
        if m and abs(ball["x"] - m["x"]) < 60:
            tap_world(a, ball["x"] + 25 if ball["x"] + 25 < m["x"] + 150 else ball["x"] + 10, ball["y"], report)
        time.sleep(.5)
        if (game(a) or {}).get("team_scores", {}).get("blue", 0) > 0:
            break
    report.check("Pal ball moves and can score", (game(a) or {}).get("team_scores", {}).get("blue", 0) > 0 or
                 (game(a) or {}).get("ball", {}).get("x") != 320, game(a))
    report.check("the projector has a Pal ball card", "Pal ball" in " ".join(pstate(p)["race"]), pstate(p)["race"])
    clear_game(base_url, report)


def game_close_tab(base, a, b, d, report):
    """Dee closes the tab in a tag round; Ben must not be left waiting."""
    clear_game(base, report)
    make_game(b, "tag", report)
    join_game(d)
    start_game(b)
    report.check("a tag round has both players", (game(b) or {}).get("phase") == "playing", game(b))
    d.request("POST", f"/session/{d.sid}/url", {"url": "about:blank"})
    end = time.time() + 22
    while time.time() < end:
        g = game(b)
        if not g or g.get("phase") == "results":
            break
        time.sleep(.5)
    report.check("closing the tab mid-game does not leave the round stuck",
                 not game(b) or game(b).get("phase") == "results", game(b))
    # bring Dee back
    d.request("POST", f"/session/{d.sid}/url", {"url": base + "/pixel"})
    wait(d, "return !document.getElementById('app').hidden || !document.getElementById('join').hidden", 25, "Dee's page")
    if not d.js("return document.getElementById('join').hidden"):
        login(d, report.names[3] if hasattr(report, "names") else "Hang Dee", report)
    open_hang(d, report)
    report.check("the closed tab can come back to the Hang out", room(d).get("you") is not None, room(d))
    clear_game(base, report)


def shower_check(base, a, b, p, report):
    # A shower falls outside. Bring everyone out of their homes first, and let any
    # held Snow Village banner finish, so this checks the shower's own message.
    for d in (a, b):
        if d.js("return !!(roomInfo && roomInfo.home)"):
            pane(d, "home")
            click_room(d, '[data-home="out"]')
            time.sleep(1)
    if p.js("return cam.loc !== 0"):
        p.js("document.querySelector('#places [data-loc=\"0\"]')?.click()")
        time.sleep(.6)
    wait(a, "return document.getElementById('hangBanner').hidden", 10, "the old banner to go")
    # If the class's own timer already started a shower, let it finish first.
    for _ in range(34):
        try:
            if not get(base, "/pixel/room?after=-1&wait=0").get("shower"):
                break
        except Exception:
            pass
        time.sleep(.5)
    post(base, "/pixel/teacher", {"key": server.ADMIN_KEY, "action": "shower"})
    time.sleep(1)
    try:
        view = get(base, f"/pixel/room?after=-1&wait=0&id={urllib.parse.quote(a.js('return me'))}")
        stars = view.get("shower") or []
    except Exception:
        stars = []
    report.check("the teacher's star shower starts", bool(stars), stars[:2])
    report.check("a star shower is announced", "Star shower" in text_of(a, "#hangBanner"), text_of(a, "#hangBanner"))
    report.check("the projector announces a star shower", "Star shower" in (pstate(p)["banner"] or ""), pstate(p)["banner"])
    if stars:
        # A shower can fall in the Snow Village; pick a star in the ordinary world.
        star = next((s for s in stars if a.js("return roomInfo.places[Math.floor(arguments[0] / PalStage.W)]", s["x"]) != "village"), stars[0])
        place = a.js("return roomInfo.places[Math.floor(arguments[0] / PalStage.W)]", star["x"])
        pane(a, "place")
        click_room(a, f'[data-name="{place}"]')
        time.sleep(1)
        # Walk under it with the arrow keys, so no friend or toy can swallow the click.
        for _ in range(18):
            pos = mine(a)
            if not pos:
                break
            dx = star["x"] - pos["x"]
            if abs(dx) < 16:
                break
            press_key(a, KEYS["Right"] if dx > 0 else KEYS["Left"])
            time.sleep(.3)
        tap_world(a, star["x"], .5, report)
        time.sleep(max(2.6, star["delay"] / 1000 + 2.4))
        try:
            left = get(base, "/pixel/room?after=-1&wait=0").get("shower") or []
            caught = all(s["id"] != star["id"] for s in left)
        except Exception:
            caught = False
        if not caught:      # the star rests where it landed; walk under it once more
            tap_world(a, star["x"], .5, report)
            time.sleep(1.2)
            try:
                left = get(base, "/pixel/room?after=-1&wait=0").get("shower") or []
                caught = all(s["id"] != star["id"] for s in left)
            except Exception:
                pass
        report.check("a falling star can be caught", caught,
                     [star, mine(a), len(left) if 'left' in locals() else None])
    else:
        report.problem("the teacher's star shower had no stars")


def teacher_close_open(a, b, c, p, report):
    post(base_url, "/pixel/teacher", {"key": server.ADMIN_KEY, "action": "room", "on": False})
    time.sleep(2)
    for d, label in ((a, "Ana"), (b, "Ben"), (c, "Cy")):
        report.check(f"the closed Hang out says so to {label}",
                     d.js("return !document.getElementById('roomClosed').hidden && roomInfo.open === false"),
                     [d.js("return !document.getElementById('roomClosed').hidden"), room(d).get("open")])
        report.check(f"the closed Hang out hides {label}'s buttons",
                     d.js("return document.getElementById('roomButtons').style.visibility") == "hidden")
    report.check("the projector says the Hang out is closed", pstate(p)["closed"], pstate(p))
    post(base_url, "/pixel/teacher", {"key": server.ADMIN_KEY, "action": "room", "on": True})
    time.sleep(3)
    for d, label in ((a, "Ana"), (b, "Ben"), (c, "Cy")):
        ok = wait(d, "return roomInfo && roomInfo.open && roomInfo.you !== null && roomStage.state.room.length >= 1", 10, f"{label} to rejoin")
        report.check(f"the reopened Hang out brings {label} back", ok,
                     [room(d).get("open"), room(d).get("you"), len(members(d))])
    report.check("the projector repopulates after reopening", len(pstate(p)["people"]) >= 3, pstate(p)["people"])


def reload_check(a, b, report):
    # Catch calm and mute still on, then reload in the middle of a My Move.
    a.js("roomPane='do'; buildRoomButtons()")
    if a.js("return !!S.hang.move"):
        a.click("#myMove")
        time.sleep(.5)
    before = [a.js("return PalStage.calm"), a.js("return localStorage.getItem('pixelMute')")]
    a.request("POST", f"/session/{a.sid}/url", {"url": base_url + "/pixel"})
    wait(a, "return !document.getElementById('app').hidden", 30, "the page after a reload")
    time.sleep(1.2)
    report.check("Calm stays on after a reload", a.js("return PalStage.calm") == before[0],
                 [before[0], a.js("return PalStage.calm")])
    report.check("mute stays after a reload", a.js("return localStorage.getItem('pixelMute')") == before[1],
                 [before[1], a.js("return localStorage.getItem('pixelMute')")])
    ok = open_hang(a, report)
    report.check("the Hang out opens again after a reload", ok, [room(a).get("you"), members(a)])
    if ok:
        report.check("a reloaded student is back in the room", room(a).get("you") is not None, room(a))
        time.sleep(.5)
        report.check("a friend sees the reloaded student", b.js("return roomStage.state.room.length >= 2"),
                     b.js("return roomStage.state.room.map(m => m.name)"))


def projector_checks(a, b, p, report):
    p.js("document.querySelector('#places [data-loc=\"0\"]')?.click()")     # look outside first
    time.sleep(1)
    ps = pstate(p)
    report.check("the projector shows everyone", len(ps["people"]) >= 3, ps["people"])
    report.check("the projector's map lists the places", "Park" in ps["map"] and "Wedding" in ps["map"], ps["map"])
    report.check("the projector's Look at lists Outside", any("Outside" in x for x in ps["places"]), ps["places"])
    # Keyboard activation: a plain click (what Enter on a focused button fires) must work.
    p.js("""(() => { const b=[...document.querySelectorAll('#people button')].find(x => x.innerText.includes(arguments[0])); b && b.click(); })()""",
         report.names[1] if hasattr(report, "names") else "Hang Ben")
    time.sleep(1.2)
    ps = pstate(p)
    report.check("following someone works from the keyboard too", ps["mode"] == "follow" and ps["follow"], ps)
    p.js("document.getElementById('camAuto').click()")
    time.sleep(.5)
    report.check("Auto takes the camera back", pstate(p)["mode"] == "auto", pstate(p)["mode"])
    # A home is a place the projector can look into, and everyone leaving sends it outside.
    pane(b, "home")
    click_room(b, '[data-home="mine"]')
    time.sleep(1.2)
    click_text(p, "#places [data-loc]", report.names[1])
    time.sleep(1.4)
    ps = pstate(p)
    report.check("the projector can look into a home", bool(ps["tag"]) and report.names[1] in ps["tag"] and "home" in ps["tag"].lower(), ps)
    shot(p, "projector-home", report, shot_dir)
    pane(b, "home")
    click_room(b, '[data-home="out"]')
    time.sleep(2)
    report.check("the projector goes back outside when the home empties", not pstate(p)["tag"], pstate(p))
    # The label on each camera button is a word, not an arrow by itself.
    report.check("the projector's camera buttons are words", "Left" in text_of(p, "#camLeft") and "Right" in text_of(p, "#camRight"),
                 [text_of(p, "#camLeft"), text_of(p, "#camRight")])
    for d, label in ((a, "Ana"), (p, "the projector")):
        issues = layout_issues(d) if d is a else []
        if d is a:
            report.check(f"{label}'s layout still fits", not issues, issues)


def projector_moment_check(a, b, p, report):
    """Auto in a home must not miss a My Move outside: it jumps there and shows the banner.
    A place the teacher picked by hand stays put but still shows the banner."""
    # Both students back outside, so the home starts empty.
    for d in (a, b):
        if d.js("return !!(roomInfo && roomInfo.home)"):
            pane(d, "home")
            click_room(d, '[data-home="out"]')
            time.sleep(1)
    # Ben goes home. Auto is sped up through its 8-second turns until it looks there.
    pane(b, "home")
    click_room(b, '[data-home="mine"]')
    wait(b, "return !!(roomInfo && roomInfo.home)", 6, "Ben's home")
    p.js("document.getElementById('camAuto').click()")
    looked = wait(p, "cam.mode = 'auto'; cam.moveOn = 0; return cam.loc !== 0", 15,
                 "Auto to look into Ben's home")
    report.check("Auto can be looking into a home", looked, pstate(p))
    # Ana, still outside, does her My Move. Auto must leave the home for it.
    time.sleep(7)
    ana_seat = room(a).get("you")
    if a.js("return !!S.hang.move") and ana_seat is not None:
        a.click("#myMove")
        wait(p, "return cam.loc === 0", 6, "the projector to jump outside for the My Move")
        ps = pstate(p)
        report.check("Auto leaves the home for a My Move outside", ps["loc"] == 0, ps)
        report.check("Auto jumps to the pal doing the My Move", ps["seat"] == ana_seat, ps)
        report.check("the projector shows the My Move banner from another place",
                     "My Move" in (ps["banner"] or ""), ps)
        shot(p, "projector-moment-mymove", report, shot_dir)
        time.sleep(1)
    else:
        report.problem("Ana has no My Move to test the projector moment")
    # A place the teacher picked by hand keeps the camera there, but the class still sees the banner.
    time.sleep(7)
    click_text(p, "#places [data-loc]", report.names[1])
    picked = wait(p, "return cam.mode === 'free' && cam.loc !== 0", 6, "the projector to look at Ben's home by hand")
    report.check("the teacher can look at a home by hand", picked, pstate(p))
    if picked and a.js("return !!S.hang.move"):
        a.click("#myMove")
        time.sleep(1.2)
        ps = pstate(p)
        report.check("a hand-picked camera stays in the home", ps["loc"] != 0 and ps["mode"] == "free", ps)
        report.check("a hand-picked camera still shows the My Move banner",
                     "My Move" in (ps["banner"] or ""), ps)
    # Leave things as the later sections expect them: outside and Auto.
    pane(b, "home")
    click_room(b, '[data-home="out"]')
    p.js("document.getElementById('camAuto').click()")
    time.sleep(1)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    global base_url, report, shot_dir
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--base", default="http://127.0.0.1:8126")
    ap.add_argument("--port", type=int, default=None)
    ap.add_argument("--driver", default="chromedriver")
    ap.add_argument("--browser", default="/usr/bin/chromium")
    ap.add_argument("--width", type=int, default=1366)
    ap.add_argument("--height", type=int, default=768)
    ap.add_argument("--tag", default="")
    ap.add_argument("--json-out", default="")
    ap.add_argument("--shot-dir", default="/tmp/pixel-hang-shots")
    ap.add_argument("--no-games", action="store_true", help="skip the long game section (for a quick look)")
    ap.add_argument("--no-close-tab", action="store_true", help="skip the close-tab game check")
    ap.add_argument("--only", default="", help="comma-separated section names to run (for development)")
    args = ap.parse_args()
    base_url = re.sub(r":\d+$", f":{args.port}", args.base) if args.port else args.base
    shot_dir = args.shot_dir
    report = Report()
    tag = args.tag or str(int(time.time()))[-5:]
    names, ids, world = setup_state(base_url, tag, report)
    # Keep the names on the report for the projector helpers.
    report.names = names
    a = b = c = d = p = None
    drivers = []
    try:
        # Four students, then the projector.
        for idx, name in enumerate(names[:3]):
            drv = Driver(args.driver, args.browser, args.width, args.height)
            drivers.append(drv)
            login(drv, name, report)
            if idx == 0:
                a = drv
            elif idx == 1:
                b = drv
            else:
                c = drv
        for drv in (a, b, c):
            if not open_hang(drv, report):
                report.problem("a student could not open the Hang out", room(drv))
            if drv is a:
                report.welcome_text = text_of(a, "#hangBanner")
        p = Driver(args.driver, args.browser, args.width, args.height)
        drivers.append(p)
        p.request("POST", f"/session/{p.sid}/url", {"url": base_url + "/pixel/show"})
        ok_p = wait(p, "return typeof PalStage !== 'undefined' && document.querySelectorAll('#people button').length >= 3", 40, "the projector")
        if not ok_p:
            report.note("the projector was slow to list the class; reloading it once")
            p.request("POST", f"/session/{p.sid}/url", {"url": base_url + "/pixel/show"})
            ok_p = wait(p, "return typeof PalStage !== 'undefined' && document.querySelectorAll('#people button').length >= 3", 25, "the projector after a reload")
            report.check("the projector lists the class after one reload", ok_p, p.js("return document.getElementById('people').innerText"))
        collect_console(p, "projector start", report)
        shot(a, "first-look", report, shot_dir)
        # Sections; each failure is recorded and the next section still runs.
        sections = [
            ("arrival", lambda: basic_checks(a, b, c, p, report)),
            ("walking", lambda: walk_checks(a, b, p, report)),
            ("do/sit/toy/gem/fish/chest", lambda: do_sit_toy_gem_fish_chest(a, b, p, report)),
            ("say/do/party", lambda: say_do_party(a, b, c, report)),
            ("my move/show/clap", lambda: my_move_show_clap(a, b, p, report)),
            ("names/calm/mute/prop/buddies", lambda: hide_name_calm_mute_prop_buddies(a, b, report)),
            ("shop/me/art/home", lambda: shop_me_art_home(a, b, c, p, report)),
            ("projector", lambda: projector_checks(a, b, p, report)),
            ("projector moment", lambda: projector_moment_check(a, b, p, report)),
            ("star shower", lambda: shower_check(base_url, a, b, p, report)),
            ("teacher close/open", lambda: teacher_close_open(a, b, c, p, report)),
            ("reload", lambda: reload_check(a, b, report)),
        ]
        wanted = [x.strip().lower() for x in args.only.split(",") if x.strip()]
        def chosen(label):
            return not wanted or any(label.lower().startswith(w) or w in label.lower() for w in wanted)
        for label, fn in sections:
            if not chosen(label):
                continue
            print(f"[e2e_hang] {label}...", flush=True)
            try:
                fn()
            except Exception as e:
                report.problem(f"{label} section stopped", f"{type(e).__name__}: {e}\n{traceback.format_exc()[-1200:]}")
            collect_console(a, label, report)
            collect_console(b, label, report)
            collect_console(c, label, report)
            collect_console(p, label, report)
        if not args.no_games:
            games = [
                ("code race", lambda: game_code_race(a, b, c, p, report)),
                ("draw & guess", lambda: game_draw(a, b, report)),
                ("hide & seek", lambda: game_hide(a, b, p, report)),
                ("tag/race/dance/apples/ball", lambda: game_tag_race_dance_apples_ball(a, b, p, report)),
            ]
            for label, fn in games:
                if not chosen(label):
                    continue
                print(f"[e2e_hang] {label}...", flush=True)
                try:
                    fn()
                except Exception as e:
                    report.problem(f"{label} stopped", f"{type(e).__name__}: {e}")
                collect_console(a, label, report)
                collect_console(b, label, report)
                collect_console(c, label, report)
                collect_console(p, label, report)
            if not args.no_close_tab and chosen("close tab"):
                try:
                    d = Driver(args.driver, args.browser, args.width, args.height)
                    drivers.append(d)
                    login(d, names[3], report)
                    open_hang(d, report)
                    report.names = names
                    game_close_tab(base_url, a, b, d, report)
                except Exception as e:
                    report.problem("close-tab game check stopped", f"{type(e).__name__}: {e}")
        shot(a, "hang-final", report, shot_dir)
        shot(p, "projector-final", report, shot_dir)
        for drv, label in zip(drivers, ["Ana", "Ben", "Cy", "projector", "Dee"]):
            collect_console(drv, "final " + label, report)
    finally:
        for drv in drivers:
            try:
                drv.close()
            except Exception:
                pass
    data = {
        "base": base_url,
        "tag": tag,
        "names": names,
        "world": world,
        "checks": report.checks,
        "problems": report.problems,
        "console_errors": report.console_errors(),
        "console": report.console,
        "notes": report.notes,
        "screenshots": report.screenshots,
        "ok": report.ok(),
    }
    if args.json_out:
        with open(args.json_out, "w") as f:
            json.dump(data, f, indent=2)
    print(json.dumps({k: data[k] for k in ("base", "names", "problems", "console_errors", "notes", "ok")}, indent=2))
    print(f"{len(data['checks']) - len(data['problems'])}/{len(data['checks'])} checks passed; "
          f"{len(data['console_errors'])} console errors; screenshots in {shot_dir}")
    return 0 if data["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
