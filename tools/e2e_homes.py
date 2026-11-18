#!/usr/bin/env python3
"""Play the Hang out HOMES like a class of children, in headless Chromium.

It starts the server's own web page in three separate browser sessions (three
students with separate cookies and local storage), gives them coins the way the
tests do (by finishing missions through the server), and then:

  * opens a home, buys cheap and dear furniture, buys one piece twice,
  * puts things out, moves them, paints, resizes, flips and puts them away,
  * puts a thing near the front door and checks it cannot cover it,
  * buys rooms, looks at the previews, walks between rooms,
  * changes walls and floors in one room only,
  * uses the wish and the coin bar, earns the coins and buys the wished thing,
  * wins a home level and makes sure its prize appears without a reload,
  * visits a friend's home, sees their decor, gives a heart and takes the door out,
  * plays every new toy (bubbles, paint, woof, meow, spin),
  * reloads the page and checks the home is still there, and
  * checks the layout and console at 1366x768 and 1024x600.

It is a tool, not a unittest: it is not named test_*.py. Screenshots go to
/tmp/homehunt-<width>/, never into the worktree.

    MAZE_PORT=8901 MAZE_STATE_FILE=/tmp/homehunt-state.json python3 server.py
    python3 tools/e2e_homes.py --port 8901
    python3 tools/e2e_homes.py --port 8901 --width 1024 --height 600
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
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "tools"))
import pixel  # noqa: E402
import server  # noqa: E402
from e2e_coach import Driver, WebDriverError  # noqa: E402

PAL = {"key": "homespal", "size": 16, "speed": 6, "palette": pixel.PIP["palette"],
       "frames": pixel.PIP["frames"], "names": pixel.PIP["names"], "title": "My pal"}
THING = 'def on_click():\n    say("Hello!")\n    jump()\n    hearts()\n'
KEYS = {"Left": "\ue012", "Up": "\ue013", "Right": "\ue014", "Down": "\ue015"}


class Report:
    def __init__(self):
        self.checks, self.problems, self.console, self.notes, self.screenshots = [], [], [], [], []

    def check(self, label, ok, detail=""):
        self.checks.append({"check": label, "ok": bool(ok), "detail": str(detail)[:800]})
        if not ok:
            self.problems.append(f"{label}: {detail}"[:1000])
        return bool(ok)

    def problem(self, label, detail=""):
        self.checks.append({"check": label, "ok": False, "detail": str(detail)[:800]})
        self.problems.append(f"{label}: {detail}"[:1000])

    def note(self, text):
        self.notes.append(text)

    def console_errors(self):
        return [e for e in self.console if e.get("level") == "SEVERE"]

    def ok(self):
        return not self.problems and not self.console_errors()


def post(base, path, data, timeout=120):
    req = urllib.request.Request(base + path, data=json.dumps(data).encode(),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as f:
        return json.load(f)


def get(base, path, timeout=120):
    with urllib.request.urlopen(base + path, timeout=timeout) as f:
        return json.load(f)


def setup_state(base, tag, report):
    """Three students: two rich from finishing everything, one with just
    My Move (55 coins) and a coded drawing for the level/prize check."""
    names = [f"Home Ana {tag}", f"Home Ben {tag}", f"Home Cy {tag}"]
    ids = {}
    for name in names:
        ids[name] = post(base, "/join", {"name": name})["id"]
        post(base, "/pixel/save", {"id": ids[name], "drawing": PAL})
    post(base, "/pixel/teacher", {"key": server.ADMIN_KEY, "action": "open",
                                  "level": pixel.LEVEL_ORDER[-1]})
    post(base, "/pixel/teacher", {"key": server.ADMIN_KEY, "action": "placed_clear"})
    post(base, "/pixel/teacher", {"key": server.ADMIN_KEY, "action": "end_game"})
    post(base, "/pixel/teacher", {"key": server.ADMIN_KEY, "action": "room", "on": False})
    post(base, "/pixel/teacher", {"key": server.ADMIN_KEY, "action": "room", "on": True})
    fails = []
    for name in names[:2]:
        for key in pixel.LEVEL_ORDER:
            out = post(base, "/pixel/run", {"id": ids[name], "level": key,
                                            "code": pixel.LEVEL_BY_KEY[key]["reference"]})
            if out.get("error") or not (out.get("stars") or [False])[0]:
                fails.append((name, key, out.get("error"), out.get("stars")))
    report.check("setup: the two rich students finish every mission", not fails, fails[:2])
    cy = ids[names[2]]
    out = post(base, "/pixel/run", {"id": cy, "level": "m1", "code": pixel.LEVEL_BY_KEY["m1"]["reference"]})
    report.check("setup: Cy can finish My Move for coins", not out.get("error"), out.get("error"))
    saved = post(base, "/pixel/thing/save", {"id": cy, "key": "homespal", "code": THING})
    report.check("setup: Cy has a coded drawing to hang up", not saved.get("error"), saved.get("error"))
    return names, ids


# ---------------------------------------------------------------------------
# browser helpers
# ---------------------------------------------------------------------------
base_url = ""
report = None
shot_dir = ""


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
        report.problem(f"timed out waiting for {what}", d.js("return location.href") if False else what)
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
    ok = wait(d, "return !document.getElementById('join').hidden || !document.getElementById('app').hidden", 30, "the Pixel Pals page")
    if not ok:
        return False
    if not d.js("return document.getElementById('join').hidden"):
        d.send("#name", name)
        d.click("#joinButton")
        wait(d, "return !document.getElementById('app').hidden", 30, "the Pixel Pals page")
    wait(d, "return typeof S !== 'undefined' && !!S", 20, "the page to load")
    time.sleep(.4)
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
          x: Math.round(m.x), y: +m.y.toFixed(2)}))""") or []
    except WebDriverError:
        return []


def seat_of(d, name):
    return next((m["seat"] for m in members(d) if m["name"] == name), None)


def mine(d):
    return next((m for m in members(d) if m["me"]), None)


def tap_screen(d, cx, cy):
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


def tap_world(d, x, depth):
    p = canvas_point(d, x, depth)
    ok = tap_screen(d, p["px"], p["py"])
    if not ok or p["px"] < p["left"] or p["px"] > p["right"]:
        try:
            d.js("""(() => { const cv = document.getElementById('roomCanvas');
                cv.dispatchEvent(new MouseEvent('click', {bubbles: true,
                  clientX: arguments[0], clientY: arguments[1]})); })()""", p["px"], p["py"])
            ok = True
        except WebDriverError:
            ok = False
    return ok


def tap_at(d, x, y):
    """Click at a stage coordinate (x across the room, y down the picture, 0..180)."""
    p = d.js("""return (() => { const cv = document.getElementById('roomCanvas');
        const r = cv.getBoundingClientRect();
        return {px: r.left + (arguments[0] - roomStage.state.camX) / PalStage.W * r.width,
                py: r.top + arguments[1] / PalStage.H * r.height,
                left: r.left, right: r.right}; })()""", x, y)
    ok = tap_screen(d, p["px"], p["py"])
    if not ok or p["px"] < p["left"] or p["px"] > p["right"]:
        try:
            d.js("""(() => { const cv = document.getElementById('roomCanvas');
                cv.dispatchEvent(new MouseEvent('click', {bubbles: true,
                  clientX: arguments[0], clientY: arguments[1]})); })()""", p["px"], p["py"])
            ok = True
        except WebDriverError:
            ok = False
    return ok


def people_seat(d, name):
    return d.js("const p=(roomInfo.people||[]).find(p => p.name === arguments[0]); return p ? p.seat : null", name)


def press_key(d, key):
    d.request("POST", f"/session/{d.sid}/actions", {"actions": [{
        "type": "key", "id": "e2e-keys",
        "actions": [{"type": "keyDown", "value": key}, {"type": "keyUp", "value": key}]}]})


def text_of(d, css):
    return d.js("return (document.querySelector(arguments[0]) || {}).innerText || ''", css)


def shot(d, label):
    try:
        os.makedirs(shot_dir, exist_ok=True)
        path = os.path.join(shot_dir, re.sub(r"[^a-z0-9]+", "-", label.lower()).strip("-") + ".png")
        data = d.request("GET", f"/session/{d.sid}/screenshot")
        with open(path, "wb") as f:
            f.write(base64.b64decode(data))
        report.screenshots.append(path)
    except Exception:
        pass


def collect_console(d, label):
    try:
        entries = d.logs()
    except Exception:
        return
    for e in entries:
        msg = e.get("message") or ""
        if "favicon.ico" in msg or "AudioContext was not allowed to start" in msg:
            continue
        report.console.append({"where": label, "level": e.get("level"), "message": msg[:800]})


def layout_issues(d, where):
    return d.js(r"""return (() => {
      const out = [], h = document.getElementById('hangView');
      if (!h || h.hidden) return ['the Hang out is not showing: ' + arguments[0]];
      const hr = h.getBoundingClientRect();
      if (hr.bottom > innerHeight + 1 || hr.right > innerWidth + 1) out.push('the Hang out is cut off');
      if (hr.height < 300) out.push('the Hang out is too short');
      const vis = el => { const s = getComputedStyle(el); const r = el.getBoundingClientRect();
        return s.display !== 'none' && s.visibility !== 'hidden' && r.width > 0 && r.height > 0; };
      for (const el of document.querySelectorAll('#hangView > *, .hang-side > *, .hang-main > *, #roomTip, #coinBar, #roomTabs, #gameStatus')) {
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
          const s = getComputedStyle(el);
          if (el.scrollWidth > el.clientWidth + 2 && ['visible', 'clip'].includes(s.overflowX))
            out.push('cut-off inside the buttons: ' + (el.innerText || '').slice(0, 24));
        }
      }
      return out.slice(0, 15);
    })()""", where)


def buy_tile(d, key, report=None, double=True):
    """Click a shop tile twice (the page asks for a second click)."""
    if not click_room(d, f'[data-buy="{key}"]'):
        if report:
            report.problem("shop tile missing", key)
        return False
    time.sleep(.25)
    if double and not click_room(d, f'[data-buy="{key}"]'):
        if report:
            report.problem("shop tile missing on the second click", key)
        return False
    return True


def stuff(d):
    try:
        return d.js("return S.hang.stuff.slice()")
    except WebDriverError:
        return []


def coins(d):
    try:
        return d.js("return S.hang.coins")
    except WebDriverError:
        return None


def home(d):
    try:
        return d.js("return roomInfo && roomInfo.home")
    except WebDriverError:
        return None


def go_home(d, where="mine"):
    pane(d, "home")
    click_room(d, f'[data-home="{where}"]')
    if where == "out":
        return wait(d, "return !roomInfo.home", 8, "the way outside")
    return wait(d, "return roomInfo.home && roomInfo.home.mine", 10, "your own home")


def go_room(d, n):
    pane(d, "home")
    click_room(d, f'[data-goroom="{n}"]')
    return wait(d, f"return Math.min(roomInView, roomInfo.home.rooms.length - 1) === {n}", 8, f"room {n}")


def items(d):
    h = home(d)
    return (h or {}).get("items", [])


def place(d, key, x, depth, expect_add=1):
    before = len(items(d))
    if not click_room(d, f'[data-furn="{key}"]'):
        report.problem("could not find your thing to put out", key)
        return False
    wait(d, "return !!furnArmed", 4, "the thing to be picked")
    tap_world(d, x, depth)
    return wait(d, f"return (roomInfo.home && roomInfo.home.items.length) >= {before + expect_add}", 8, f"placing {key}")


def piece_point(d, piece):
    """A spot on the floor where furnitureAt gives this piece, not a neighbour."""
    return d.js(r"""return (() => {
      const id = arguments[0], h = roomInfo && roomInfo.home;
      const it = h && h.items.find(i => i.id === id);
      if (!it) return null;
      for (let dx = 0; dx <= 80; dx += 4) for (const sx of (dx ? [dx, -dx] : [0]))
        for (let dy = 0; dy <= .12; dy += .02) for (const sy of (dy ? [dy, -dy] : [0])) {
          const x = it.x + sx, y = Math.max(0, Math.min(1, it.y + sy));
          const hit = PalHang.furnitureAt(h, x, y);
          if (hit && hit.id === id) return {x, y};
        }
      return {x: it.x, y: it.y};
    })()""", piece)


def select_item(d, piece):
    """Turn on ✋ moving and click a piece, using a spot that resolves to it."""
    pane(d, "home")
    on = d.js("return moving === true")
    if not on:
        click_room(d, "[data-moving]")
        wait(d, "return moving === true", 3, "moving mode")
    p = piece_point(d, piece)
    if not p:
        return False
    tap_world(d, p["x"], p["y"])
    return wait(d, f"return furnArmed && furnArmed.piece === {piece}", 5, "picking up the thing")


def run_mission(base, pid, key, report):
    out = post(base, "/pixel/run", {"id": pid, "level": key,
                                    "code": pixel.LEVEL_BY_KEY[key]["reference"]})
    report.check(f"server: {key} pays the wish fund", not out.get("error") and (out.get("stars") or [False])[0],
                 out.get("error") or out.get("stars"))
    return out


# ---------------------------------------------------------------------------
# The play-through
# ---------------------------------------------------------------------------

def section_layout(d, label):
    issues = layout_issues(d, label)
    report.check(f"{label} fits the window", not issues, issues)


def art_checks(a, report):
    """Every piece of furniture, every room and every wall or floor is drawn by the browser."""
    bad = a.js(r"""return (() => {
      const bad = [];
      const blank = cv => { const d = cv.getContext('2d').getImageData(0, 0, cv.width, cv.height).data;
        for (let i = 3; i < d.length; i += 4) if (d[i] > 20) return false; return true; };
      for (const key of Object.keys(S.hang.furniture)) {
        try { const cv = PalHang.furniturePicture(key, 0);
          if (!cv.width || !cv.height || blank(cv)) bad.push([key, 'blank']); }
        catch (e) { bad.push([key, String(e)]); }
      }
      for (const key of Object.keys(S.hang.rooms)) {
        const r = S.hang.rooms[key];
        try { const cv = PalHang.roomPicture(key, r.wall, r.floor);
          if (!cv.width || !cv.height || blank(cv)) bad.push([key, 'blank']); }
        catch (e) { bad.push([key, String(e)]); }
      }
      for (const key of Object.keys(S.hang.walls)) {
        try { const cv = PalHang.roomPicture('', key, 'f_wood'); if (blank(cv)) bad.push([key, 'blank']); }
        catch (e) { bad.push([key, String(e)]); }
      }
      for (const key of Object.keys(S.hang.floors)) {
        try { const cv = PalHang.roomPicture('', 'w_cream', key); if (blank(cv)) bad.push([key, 'blank']); }
        catch (e) { bad.push([key, String(e)]); }
      }
      return bad;
    })()""")
    report.check("every thing, room, wall and floor can be drawn", not bad, bad[:20])


def home_shop_and_place(a, b, cy, report):
    pane(a, "home")
    section_layout(a, "the empty home page")
    if not go_home(a, "mine"):
        report.problem("Ana could not go into her own home", room(a))
        return
    h = home(a)
    report.check("a new student has one room", h and len(h.get("rooms", [])) == 1, h and h.get("rooms"))
    report.check("the home says how it grows", "Tiny hut" in text_of(a, "#roomButtons") and "points" in text_of(a, "#roomButtons"),
                 text_of(a, "#roomButtons")[:300])
    shot(a, "home-empty")

    # Buy cheap furniture twice, and watch the coins.
    # The "Build a room" button should land on the Rooms shelf, not Furniture.
    click_room(a, '[data-roomshop]')
    opened = wait(a, "return roomPane === 'shop'", 4, "the shop from Build a room")
    report.check("Build a room opens the Rooms shelf", opened and a.js("return shopTab === 'room'"),
                 [opened, a.js("return shopTab")])
    # Buying while inside your home goes straight to putting it out.
    click_room(a, '[data-shoptab="furniture"]')
    wait(a, "return shopTab === 'furniture'", 3, "the furniture tab")
    buy_tile(a, "duck")
    report.check("buying at home takes you straight to putting it out",
                 wait(a, "return roomPane === 'home' && furnArmed && furnArmed.key === 'duck'", 6, "the duck to be ready"),
                 [a.js("return roomPane"), a.js("return furnArmed")])
    tap_world(a, 120, .3)
    wait(a, "return roomInfo.home.items.some(i => i.key === 'duck')", 6, "the duck on the floor")
    # Shop from outside, so each purchase stays in the shop for the next one.
    go_home(a, "out")
    pane(a, "shop")
    click_room(a, '[data-shoptab="furniture"]')
    wait(a, "return shopTab === 'furniture'", 3, "the furniture tab")
    before_coins, before_balloons = coins(a), stuff(a).count("balloons")
    report.check("the shop groups things by what a child can afford",
                 "You can buy these now" in text_of(a, "#roomButtons"),
                 text_of(a, "#roomButtons")[:400])
    buy_tile(a, "balloons")
    ok = wait(a, f"return S.hang.stuff.filter(k => k === 'balloons').length === {before_balloons + 1}", 6, "the first balloons")
    report.check("buying a thing takes its price once", ok and coins(a) == before_coins - pixel.SHOP["balloons"]["price"],
                 [before_coins, coins(a), stuff(a).count("balloons")])
    buy_tile(a, "balloons")
    ok = wait(a, f"return S.hang.stuff.filter(k => k === 'balloons').length === {before_balloons + 2}", 6, "the second balloons")
    report.check("the same thing can be bought a second time", ok, stuff(a).count("balloons"))
    report.check("a bought thing says how many you have", "you have 2" in text_of(a, "#roomButtons"), text_of(a, "#roomButtons")[:500])

    # The other pieces for the toy check, and two rooms.
    for key in ("globe", "easel", "bathtub", "puppy", "kitty"):
        buy_tile(a, key)
    click_room(a, '[data-shoptab="room"]')
    wait(a, "return shopTab === 'room'", 3, "the rooms tab")
    for key in ("r_bed", "r_bath"):
        buy_tile(a, key)
    wait(a, "return S.hang.stuff.includes('r_bed') && S.hang.stuff.includes('r_bath')", 10, "the two rooms")
    report.check("a room is yours once built", "Built" in text_of(a, "#roomButtons"), text_of(a, "#roomButtons")[:500])
    pics = a.js("""return [...document.querySelectorAll('#roomButtons canvas.roompic')].map(cv => {
        const d = cv.getContext('2d').getImageData(0, 0, cv.width, cv.height).data;
        let n = 0; for (let i = 3; i < d.length; i += 4) if (d[i] > 20) n++;
        return [cv.dataset.roompic, n]; })""")
    report.check("room previews are actually drawn", bool(pics) and all(n > 100 for _, n in pics), pics)
    section_layout(a, "the shop at the bottom of a home")

    # A room's own wall and floor are in the walls and floors tab.
    click_room(a, '[data-shoptab="look"]')
    wait(a, "return shopTab === 'look'", 3, "the walls tab")
    report.check("walls and floors from a bought room are yours", "Blue walls" in text_of(a, "#roomButtons") and
                 "Purple carpet" in text_of(a, "#roomButtons"), text_of(a, "#roomButtons")[:400])
    buy_tile(a, "w_pink")
    buy_tile(a, "f_check")
    wait(a, "return S.hang.stuff.includes('w_pink') && S.hang.stuff.includes('f_check')", 8, "Ana's new wall and floor")

    # Put things out, including both copies of the balloons.
    if not go_home(a, "mine"):
        report.problem("Ana could not get back into her home after shopping", room(a))
        return
    wait(a, "return roomInfo.home.rooms.length === 3", 8, "the bought rooms to join the home")
    report.check("bought rooms join the home", len((home(a) or {}).get("rooms", [])) == 3, (home(a) or {}).get("rooms"))
    placed_ok = True
    for key, x, y in (("balloons", 150, .55), ("balloons", 210, .55), ("globe", 270, .4),
                      ("easel", 110, .75), ("bathtub", 40, .85), ("puppy", 190, .85), ("kitty", 300, .85)):
        placed_ok = place(a, key, x, y) and placed_ok
    report.check("things can be put out one at a time", placed_ok and len(items(a)) >= 7, items(a))
    report.check("a child can see how many copies are out", "2 of 2 out" in text_of(a, "#roomButtons"),
                 text_of(a, "#roomButtons")[:500])
    # All copies are out: a third balloons must not appear.
    before = len(items(a))
    click_room(a, '[data-furn="balloons"]')
    tap_world(a, 100, .5)
    time.sleep(.8)
    report.check("the page says when every copy is already out",
                 len(items(a)) == before and ("all of yours are out" in text_of(a, "#roomTip")),
                 [len(items(a)), text_of(a, "#roomTip")])
    shot(a, "home-with-things")

    # Move, paint, resize, flip and put away.
    balloons = next((i for i in items(a) if i["key"] == "balloons"), None)
    if balloons:
        report.check("a thing can be picked up to change it", select_item(a, balloons["id"]), a.js("return furnArmed"))
        if a.js("return furnArmed && furnArmed.piece"):
            click_room(a, '[data-paint="3"]')
            wait(a, f"return (roomInfo.home.items.find(i => i.id === {balloons['id']}) || {{}}).paint === 3", 5, "the paint")
            click_room(a, '[data-size="2"]')
            wait(a, f"return (roomInfo.home.items.find(i => i.id === {balloons['id']}) || {{}}).size === 2", 5, "the new size")
            click_room(a, '[data-flip="1"]')
            changed = wait(a, f"return !!(roomInfo.home.items.find(i => i.id === {balloons['id']}) || {{}}).flip", 5, "the flip")
            item = next((i for i in items(a) if i["id"] == balloons["id"]), {})
            report.check("paint, size and flip all stick", changed and item.get("paint") == 3 and item.get("size") == 2,
                         item)
            shot(a, "home-painted")
            section_layout(a, "the paint and resize panel")
            click_room(a, f'[data-away="{balloons["id"]}"]')
            wait(a, f"return !roomInfo.home.items.some(i => i.id === {balloons['id']})", 6, "the thing to go away")
            report.check("a thing can be put away", not any(i["id"] == balloons["id"] for i in items(a)), items(a))
    globe = next((i for i in items(a) if i["key"] == "globe"), None)
    if globe and select_item(a, globe["id"]):
        click_room(a, '[data-paint="5"]')
        wait(a, f"return (roomInfo.home.items.find(i => i.id === {globe['id']}) || {{}}).paint === 5", 5, "the globe paint")
        click_room(a, '[data-size="0"]')
        wait(a, f"return (roomInfo.home.items.find(i => i.id === {globe['id']}) || {{}}).size === 0", 5, "the small globe")
        click_room(a, '[data-flip="1"]')
        wait(a, f"return !!(roomInfo.home.items.find(i => i.id === {globe['id']}) || {{}}).flip", 5, "the flipped globe")
        report.check("a second thing can keep its own paint and size",
                     next((i for i in items(a) if i["id"] == globe["id"]), {}).get("paint") == 5,
                     next((i for i in items(a) if i["id"] == globe["id"]), {}))

    # A free thing in the second room can sit close to the left wall, where there is no outside door.
    go_room(a, 1)
    if place(a, "plant", pixel.PLACE_W + 20, .5):
        got = items(a)[-1]
        report.check("a thing in a back room can sit near the left wall", 320 + 8 <= got["x"] <= 320 + 80, got)
    go_room(a, 0)


def front_door(a, report):
    """The first room's outside door must stay clear of furniture."""
    if not go_home(a, "mine"):
        report.problem("could not go home for the door check")
        return
    go_room(a, 0)
    before = len(items(a))
    if not place(a, "rug", 20, .5):
        report.problem("could not put the rug near the door")
        return
    rug = items(a)[-1]
    report.check("a thing put by the door keeps clear of it", rug["x"] >= 80, rug)
    # With nothing in hand, a click on the door itself still goes outside.
    a.js("moving = false; furnArmed = null; buildRoomButtons();")
    tap_at(a, 28, 80)
    if wait(a, "return !roomInfo.home", 6, "the door to go outside"):
        report.check("the front door still goes outside", True)
    else:
        report.check("the front door still goes outside", False, [home(a), text_of(a, "#roomTip")])
    go_home(a, "mine")


def wall_floor(a, report):
    if not go_home(a, "mine"):
        report.problem("could not go home to change the walls")
        return
    go_room(a, 1)
    pane(a, "home")
    before_scroll = a.js("const b=document.getElementById('roomButtons'); b.scrollTop=b.scrollHeight; return b.scrollTop")
    a.js("document.querySelector('#roomButtons [data-look=\"w_pink\"]').click()")
    ok_wall = wait(a, "return roomInfo.home.rooms[1].wall === 'w_pink'", 8, "the pink walls")
    after_scroll = a.js("return document.getElementById('roomButtons').scrollTop")
    report.check("changing a wall does not jump the buttons back to the top",
                 before_scroll > 0 and abs(after_scroll - before_scroll) <= 2, [before_scroll, after_scroll])
    click_room(a, '[data-look="f_check"]')
    ok_floor = wait(a, "return roomInfo.home.rooms[1].floor === 'f_check'", 8, "the checked floor")
    report.check("a room can have its own wall and floor", ok_wall and ok_floor,
                 (home(a) or {}).get("rooms"))
    report.check("changing one room leaves the first room alone",
                 (home(a) or {}).get("rooms", [{}, {}])[0].get("wall") != "w_pink",
                 (home(a) or {}).get("rooms"))
    shot(a, "home-new-room")
    go_room(a, 0)


def toys(a, report):
    """Click the new home toys: bathtub bubbles, easel paint, puppy woof, kitty meow and globe spin."""
    if not go_home(a, "mine"):
        report.problem("could not go home to play with the toys")
        return
    go_room(a, 0)
    found = {i["key"]: i for i in items(a) if i["key"] in ("bathtub", "easel", "puppy", "kitty", "globe")}
    for key in ("bathtub", "easel", "puppy", "kitty", "globe"):
        report.check(f"the {key} is ready to play with", key in found, list(found))
    for key in ("bathtub", "easel", "puppy", "kitty", "globe"):
        item = found.get(key)
        if not item:
            continue
        a.js("moving = false; furnArmed = null; buildRoomButtons();")
        p = piece_point(a, item["id"])
        tap_world(a, p["x"], p["y"])
        got = wait(a, "return (roomInfo.people || []).some(m => m.seat === roomInfo.you && (m.doing || '').includes('Playing'))",
                   5, f"the {key} to play")
        report.check(f"the {key} plays when you click it", got,
                     [text_of(a, "#roomTip"), a.js("return (roomInfo.people || []).find(m => m.seat === roomInfo.you)")])
        time.sleep(1.2)     # TOY_GAP


def level_and_prize(cy, report, base, ids):
    if not go_home(cy, "mine"):
        report.problem("Cy could not go into her own home", room(cy))
        return
    # Hang a coded drawing (2 points), then a free rug and plant (2 more).
    pane(cy, "art")
    click_room(cy, '[data-art="homespal"]')
    tap_world(cy, 210, .55)
    wait(cy, "return (roomStage.state.placed || []).some(p => p.mine && p.coded)", 8, "the coded drawing")
    pane(cy, "home")
    place(cy, "rug", 160, .55)
    place(cy, "plant", 260, .55)
    grew = wait(cy, "return roomInfo.home.level >= 1", 8, "the home to grow")
    h = home(cy) or {}
    prize_stuff = stuff(cy)
    report.check("a home grows when it has enough points", grew and h.get("level") == 1 and h.get("points") >= 4, h)
    report.check("a new level's prize is yours without a reload", "trophy" in prize_stuff, prize_stuff)
    report.check("the prize is in your things, not still locked",
                 "Gold trophy" in text_of(cy, "#roomButtons") and not cy.js("return !!document.querySelector('#roomButtons [data-prize=\"trophy\"]')"),
                 text_of(cy, "#roomButtons")[:800])
    shot(cy, "home-level-prize")
    # Take one thing away: the level is kept.
    plant = next((i for i in items(cy) if i["key"] == "plant"), None)
    if plant and select_item(cy, plant["id"]):
        click_room(cy, f'[data-away="{plant["id"]}"]')
        wait(cy, f"return !roomInfo.home.items.some(i => i.id === {plant['id']})", 6, "putting the plant away")
        time.sleep(.8)
        h = home(cy) or {}
        report.check("a level is kept when a thing is put away", h.get("level") == 1 and h.get("points") == 3, h)
        report.check("the next level still says 9 points", h.get("next") == 9, h)
    else:
        report.problem("could not pick Cy's plant to put it away")


def wish_and_buy(cy, report, base, ids):
    pane(cy, "shop")
    click_room(cy, '[data-shoptab="furniture"]')
    wait(cy, "return shopTab === 'furniture'", 3, "the furniture tab")
    report.check("a student who cannot afford everything gets a Save up group",
                 "Save up" in text_of(cy, "#roomButtons"), text_of(cy, "#roomButtons")[:500])
    before = coins(cy)
    click_room(cy, '[data-buy="robot"]')
    got = wait(cy, "return S.hang.wish === 'robot'", 5, "the wish")
    report.check("clicking a dear thing saves up for it", got, cy.js("return S.hang.wish"))
    report.check("the coin bar shows the wish and how close it is",
                 cy.js("return !document.getElementById('coinWish').hidden") and
                 "Robot buddy" in text_of(cy, "#coinWish") and "/" in text_of(cy, "#coinWish"),
                 text_of(cy, "#coinWish"))
    shot(cy, "home-wish")
    # Earn the coins the way the server does: finish a mission.
    key = pixel.LEVEL_ORDER[1]
    run_mission(base, ids[report.names[2]], key, report)
    want = pixel.SHOP["robot"]["price"]
    got_coins = wait(cy, f"return S.hang.coins >= {want}", 10, "mission coins to reach the wish")
    after_mission = coins(cy)
    report.check("mission coins fill up the wish", got_coins and after_mission > before, [before, after_mission])
    report.check("the saved-up banner says what to do", "SAVED UP" in text_of(cy, "#hangBanner").upper(),
                 text_of(cy, "#hangBanner"))
    # Buy it now: two clicks, as the shop asks.
    buy_tile(cy, "robot")
    bought = wait(cy, "return S.hang.stuff.includes('robot')", 8, "buying the wished thing")
    report.check("the wished thing can be bought", bought and coins(cy) == after_mission - want,
                 [bought, before, coins(cy)])
    report.check("buying the wish clears it", cy.js("return S.hang.wish === null") and
                 cy.js("return document.getElementById('coinWish').hidden"),
                 [cy.js("return S.hang.wish"), cy.js("return document.getElementById('coinWish').hidden")])
    shot(cy, "home-wish-bought")


def visit_and_heart(a, b, report):
    # Ben decorates his home first so Ana can see it.
    if not go_home(b, "mine"):
        report.problem("Ben could not go into his own home", room(b))
        return
    go_home(b, "out")
    pane(b, "shop")
    click_room(b, '[data-shoptab="furniture"]')
    buy_tile(b, "balloons")
    wait(b, "return S.hang.stuff.includes('balloons')", 6, "Ben's balloons")
    click_room(b, '[data-shoptab="look"]')
    wait(b, "return shopTab === 'look'", 3, "Ben's walls tab")
    buy_tile(b, "w_pink")
    wait(b, "return S.hang.stuff.includes('w_pink')", 6, "Ben's pink wall")
    go_home(b, "mine")
    pane(b, "home")
    click_room(b, '[data-look="w_pink"]')
    wait(b, "return roomInfo.home && roomInfo.home.rooms[0].wall === 'w_pink'", 6, "Ben's pink wall at home")
    place(b, "balloons", 220, .5)
    b_seat = people_seat(a, report.names[1])
    # Ana visits from her own home.
    go_home(a, "mine")
    pane(a, "home")
    found = wait(a, f"return [...document.querySelectorAll('#roomButtons [data-home]')].some(x => x.dataset.home === '{b_seat}')",
                 6, "the friend to visit")
    click_room(a, f'[data-home="{b_seat}"]')
    visited = wait(a, "return roomInfo.home && !roomInfo.home.mine", 10, "visiting Ben's home")
    h = home(a) or {}
    report.check("a friend's home can be visited", visited and h.get("name") == report.names[1], h)
    report.check("a visitor sees the owner's wall and thing",
                 (h.get("rooms") or [{}])[0].get("wall") == "w_pink" and len(h.get("items") or []) >= 1, h)
    shot(a, "home-visiting")
    ben_coins = coins(b)
    click_room(a, "[data-heart]")
    hearted = wait(a, "return roomInfo.home && roomInfo.home.hearted", 8, "the heart")
    report.check("a visitor can give a heart", hearted, home(a))
    report.check("a heart pays the owner", wait(b, "return roomInfo.home && roomInfo.home.hearts >= 1", 8, "the owner's heart") and
                 coins(b) == ben_coins + pixel.COINS_HEART, [ben_coins, coins(b)])
    again = post(base_url, "/pixel/room/do", {"id": a.js("return me"), "what": "heart"})
    report.check("the same visitor cannot give a second heart", again.get("error") == "You gave this home a heart already.", again)
    # Back out, then use the drawn door in the owner's own home.
    click_room(a, '[data-home="out"]')
    wait(a, "return !roomInfo.home", 8, "out of Ben's home")
    go_home(a, "mine")
    a.js("moving = false; furnArmed = null; buildRoomButtons();")
    tap_at(a, 28, 80)
    report.check("the drawn door goes outside", wait(a, "return !roomInfo.home", 8, "the door outside"),
                 [home(a), text_of(a, "#roomTip")])


def reload_and_check(a, report, before):
    a.request("POST", f"/session/{a.sid}/url", {"url": base_url + "/pixel"})
    ok = wait(a, "return !document.getElementById('app').hidden", 35, "the page after a reload")
    if not ok:
        report.problem("Ana's page did not come back after a reload")
        return
    time.sleep(1.0)
    report.check("coins are still there after a reload", coins(a) == before["coins"], [before["coins"], coins(a)])
    open_hang(a)
    if not go_home(a, "mine"):
        report.problem("Ana could not get home after a reload", room(a))
        return
    h = home(a) or {}
    got = {i["id"]: i for i in h.get("items", [])}
    report.check("the rooms are still there after a reload", len(h.get("rooms", [])) == before["rooms"],
                 [before["rooms"], len(h.get("rooms", []))])
    report.check("the things are still there after a reload", len(h.get("items", [])) == before["items"],
                 [before["items"], len(h.get("items", []))])
    report.check("the paint, size and flip are still there after a reload",
                 all(got.get(i["id"], {}).get("paint") == i.get("paint") and
                     got.get(i["id"], {}).get("size") == i.get("size") and
                     got.get(i["id"], {}).get("flip") == i.get("flip") for i in before["styled"]),
                 [before["styled"], list(got.values())])
    report.check("the room's wall and floor are still there after a reload",
                 [r.get("wall") for r in h.get("rooms", [])] == before["walls"] and
                 [r.get("floor") for r in h.get("rooms", [])] == before["floors"],
                 [(r.get("wall"), r.get("floor")) for r in h.get("rooms", [])])
    shot(a, "home-after-reload")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    global base_url, report, shot_dir
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--base", default="http://127.0.0.1:8901")
    ap.add_argument("--port", type=int, default=None)
    ap.add_argument("--driver", default="chromedriver")
    ap.add_argument("--browser", default="/usr/bin/chromium")
    ap.add_argument("--width", type=int, default=1366)
    ap.add_argument("--height", type=int, default=768)
    ap.add_argument("--tag", default="")
    ap.add_argument("--json-out", default="")
    ap.add_argument("--shot-dir", default="")
    ap.add_argument("--only", default="", help="comma-separated sections to run (for development)")
    args = ap.parse_args()
    base_url = re.sub(r":\d+$", f":{args.port}", args.base) if args.port else args.base
    shot_dir = args.shot_dir or f"/tmp/homehunt-{args.width}"
    report = Report()
    tag = args.tag or str(int(time.time()))[-6:]
    names, ids = setup_state(base_url, tag, report)
    report.names = names
    drivers = []
    try:
        a = b = cy = None
        for idx, name in enumerate(names):
            d = Driver(args.driver, args.browser, args.width, args.height)
            drivers.append(d)
            login(d, name, report)
            if idx == 0:
                a = d
            elif idx == 1:
                b = d
            else:
                cy = d
        openers = []
        for d, who in ((a, "Ana"), (b, "Ben"), (cy, "Cy")):
            ok = open_hang(d)
            report.check(f"{who} can open the Hang out", ok, room(d).get("you"))
        shot(a, "hang-outside")
        collect_console(a, "start Ana")
        collect_console(b, "start Ben")
        collect_console(cy, "start Cy")

        sections = [
            ("drawing everything", lambda: art_checks(a, report)),
            ("home/shop/place", lambda: home_shop_and_place(a, b, cy, report)),
            ("front door", lambda: front_door(a, report)),
            ("walls/floors", lambda: wall_floor(a, report)),
            ("toys", lambda: toys(a, report)),
            ("level/prize", lambda: level_and_prize(cy, report, base_url, ids)),
            ("wish", lambda: wish_and_buy(cy, report, base_url, ids)),
            ("visit/heart", lambda: visit_and_heart(a, b, report)),
        ]
        only = set(filter(None, args.only.split(",")))
        for label, fn in sections:
            if only and label not in only:
                continue
            try:
                fn()
            except Exception:
                report.problem(f"section crashed: {label}", traceback.format_exc()[-900:])
                traceback.print_exc()
            collect_console(a, f"after {label} (Ana)")
            collect_console(b, f"after {label} (Ben)")
            collect_console(cy, f"after {label} (Cy)")

        # What Ana has now, then reload and check it all came back.
        if not go_home(a, "mine"):
            report.problem("Ana could not get home for the reload check", room(a))
        before = {
            "coins": coins(a),
            "rooms": len((home(a) or {}).get("rooms", [])),
            "items": len(items(a)),
            "styled": [dict(i) for i in items(a) if i.get("paint") is not None or i.get("size") is not None or i.get("flip")],
            "walls": [r.get("wall") for r in (home(a) or {}).get("rooms", [])],
            "floors": [r.get("floor") for r in (home(a) or {}).get("rooms", [])],
        }
        if not only or "reload" in only:
            try:
                reload_and_check(a, report, before)
            except Exception:
                report.problem("section crashed: reload", traceback.format_exc()[-900:])
                traceback.print_exc()
            collect_console(a, "after reload")
        for d, label in ((a, "Ana"), (b, "Ben"), (cy, "Cy")):
            issues = layout_issues(d, label)
            report.check(f"{label}'s screen fits {args.width}x{args.height}", not issues, issues)
        for d in (a, b, cy):
            try:
                d.close()
            except Exception:
                pass
    finally:
        for d in drivers:
            try:
                d.close()
            except Exception:
                pass

    result = {"ok": report.ok(), "checks": report.checks, "problems": report.problems,
              "console": report.console, "console_errors": report.console_errors(),
              "notes": report.notes, "screenshots": report.screenshots,
              "width": args.width, "height": args.height, "names": names}
    if args.json_out:
        with open(args.json_out, "w") as f:
            json.dump(result, f, indent=1)
    print(json.dumps({k: result[k] for k in ("ok", "width", "height", "problems", "console_errors")}, indent=1))
    if report.screenshots:
        print("screenshots:", ", ".join(report.screenshots))
    if not report.ok():
        for p in report.problems:
            print("PROBLEM:", p)
        for e in report.console_errors():
            print("CONSOLE:", e)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
