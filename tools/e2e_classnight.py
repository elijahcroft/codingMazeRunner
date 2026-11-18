#!/usr/bin/env python3
"""Small-screen sweep of tonight's Pixel Pals things, in a real browser.

Three students, the projector and the teacher page go through:
  * the 👗 Fashion show (dressing, runway with reactions, kind ribbons),
  * the 💒 wedding (pick card, invite, ceremony),
  * the 🖼️ class mural,
  * a 🏠 home with a piece picked up (paint / size / flip),
  * the four 🛍️ Shop tabs,
and the teacher page, logged in by typing the admin key.

Every check records a screenshot (in --shot-dir), the page's sideways scroll,
any control pushed off the right edge, any visible buttons that overlap, and
text that is too wide for its box.  Run it at 1024x600 and 1093x530 (a laptop
at 125% zoom):

    python3 tools/e2e_classnight.py --port 8907 --width 1024 --height 600 \\
        --shot-dir .classtest-artifacts/shots-1024 --json-out /tmp/night.json

It uses tools/e2e_coach.Driver (stdlib WebDriver), so the server must already
be running.  It is a tool, not a unittest: it is not named test_*.py.
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
import server  # noqa: E402  (ADMIN_KEY)
from e2e_coach import Driver, WebDriverError  # noqa: E402

ENTER = "\ue007"
PAL = {"key": "classnight", "size": 16, "speed": 6, "palette": pixel.PIP["palette"],
       "frames": pixel.PIP["frames"], "names": pixel.PIP["names"], "title": "Night pal"}
W, H = 1024, 600


class Report:
    def __init__(self, shot_dir):
        self.checks, self.problems, self.notes, self.console = [], [], [], []
        self.screenshots = []
        self.shot_dir = shot_dir

    def check(self, label, ok, detail=""):
        self.checks.append({"check": label, "ok": bool(ok), "detail": str(detail)[:1200]})
        if not ok:
            self.problems.append(f"{label}: {detail}"[:1000])
        return bool(ok)

    def problem(self, label, detail=""):
        self.checks.append({"check": label, "ok": False, "detail": str(detail)[:1200]})
        self.problems.append(f"{label}: {detail}"[:1000])

    def note(self, text):
        self.notes.append(str(text)[:1200])

    def console_errors(self):
        return [e for e in self.console if e.get("level") == "SEVERE"]

    def ok(self):
        return not self.problems and not self.console_errors()


def post(base, path, data, timeout=60):
    req = urllib.request.Request(base + path, data=json.dumps(data).encode(),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as f:
        return json.load(f)


def get(base, path, timeout=60):
    with urllib.request.urlopen(base + path, timeout=timeout) as f:
        return json.load(f)


def setup_state(base, tag, report):
    """Three students with every mission, a drawing, coins and one of each shop kind."""
    names = [f"Night Ana {tag}", f"Night Ben {tag}", f"Night Cy {tag}"]
    ids = {}
    for name in names:
        ids[name] = post(base, "/join", {"name": name})["id"]
        post(base, "/pixel/news", {"id": ids[name]})     # the one-time ✨ New card is for real kids; it would cover the world
    post(base, "/pixel/teacher", {"key": server.ADMIN_KEY, "action": "room", "on": False})
    post(base, "/pixel/teacher", {"key": server.ADMIN_KEY, "action": "open", "level": pixel.LEVEL_ORDER[-1]})
    post(base, "/pixel/teacher", {"key": server.ADMIN_KEY, "action": "end_game"})
    post(base, "/pixel/teacher", {"key": server.ADMIN_KEY, "action": "placed_clear"})
    post(base, "/pixel/teacher", {"key": server.ADMIN_KEY, "action": "room", "on": True})
    for pid in ids.values():
        post(base, "/pixel/room/do", {"id": pid, "what": "join"})
    fails = []
    for i, name in enumerate(names):
        pid = ids[name]
        for key in pixel.LEVEL_ORDER:
            out = post(base, "/pixel/run", {"id": pid, "level": key,
                                            "code": pixel.LEVEL_BY_KEY[key]["reference"]})
            if out.get("error"):
                fails.append((name, key, out["error"]))
        pal = dict(PAL)
        pal["key"] = "night" + str(i)
        pal["title"] = "Night pal"
        post(base, "/pixel/save", {"id": pid, "drawing": pal})
        state = get(base, "/pixel/state?id=" + pid)
        hang = state.get("hang") or {}
        shop, coins = hang.get("shop") or {}, hang.get("coins") or 0
        for key in ("beanie", "bunny", "balloons", "duck", "lamp", "w_pink", "f_check"):
            item = shop.get(key)
            if item and coins >= item["price"]:
                out = post(base, "/pixel/room/do", {"id": pid, "what": "buy", "key": key})
                if out.get("ok"):
                    coins = out.get("coins", coins)
        # Put everyone back in the Park: a browser that was closed mid-home can
        # leave a saved spot behind, and a returning name would start there.
        post(base, "/pixel/room/do", {"id": pid, "what": "go", "name": "park"})
    report.check("setup: the three students finish every mission", not fails, fails[:3])
    # A previous run (or a closed tab) can leave a results card behind. Clear it
    # before the first section, or the host sees "Another game can start in a moment".
    for _ in range(16):
        try:
            view = get(base, "/pixel/room?after=-1")
        except Exception:
            view = {}
        if not view.get("game") and not view.get("wedding"):
            break
        post(base, "/pixel/teacher", {"key": server.ADMIN_KEY, "action": "end_game"})
        time.sleep(1.0)
    return names, ids


# ---------------------------------------------------------------------------
# browser helpers
# ---------------------------------------------------------------------------
def login(d, base, name, report):
    d.request("POST", f"/session/{d.sid}/url", {"url": base + "/pixel"})
    ok = d.wait("return !document.getElementById('join').hidden || !document.getElementById('app').hidden",
                25, "the Pixel Pals page")
    if not ok:
        return False
    if not d.js("return document.getElementById('join').hidden"):
        d.send("#name", name)
        d.click("#joinButton")
        d.wait("return !document.getElementById('app').hidden", 30, "the Pixel Pals page")
    d.wait("return typeof S !== 'undefined' && !!S", 15, "the page to load")
    time.sleep(.3)
    if not d.js("return document.getElementById('shelf').hidden"):
        d.click("#gallery [data-gallery]")
        d.wait("return document.getElementById('shelf').hidden", 15, "the gallery to close")
    return True


def open_hang(d, report, timeout=35):
    end = time.time() + timeout
    while time.time() < end:
        if d.js("return !document.getElementById('hangView').hidden && typeof roomInfo !== 'undefined' && "
               "roomInfo && typeof roomStage !== 'undefined' && roomStage && roomStage.state && "
               "roomStage.state.room && roomStage.state.room.some(m => m.me)"):
            return True
        d.js("const b=document.querySelector('nav [data-view=\"hang\"]'); if(b) b.click();")
        time.sleep(.8)
    report.problem("a student could not open the Hang out", d.js("return document.getElementById('hangView') && document.getElementById('hangView').hidden"))
    return False


def pane(d, name):
    d.js("const b=document.querySelector('#roomTabs [data-pane=\"%s\"]'); if(b) b.click();" % name)
    d.wait(f"return roomPane === {json.dumps(name)}", 5, "the " + name + " pane")
    time.sleep(.15)


def click_css(d, css):
    return d.js("const el=document.querySelector(arguments[0]); if(!el) return false;"
                "el.scrollIntoView({block:'nearest'}); el.click(); return true;", css)


def click_text(d, css, text):
    return d.js("const el=[...document.querySelectorAll(arguments[0])].find(x =>"
                "(x.innerText||'').includes(arguments[1])); if(!el) return false;"
                "el.scrollIntoView({block:'nearest'}); el.click(); return true;", css, text)


def click_at(d, x, y):
    """A real mouse click at viewport coordinates."""
    try:
        d.request("POST", f"/session/{d.sid}/actions", {"actions": [{
            "type": "pointer", "id": "night-mouse", "parameters": {"pointerType": "mouse"},
            "actions": [{"type": "pointerMove", "duration": 0, "x": int(x), "y": int(y), "origin": "viewport"},
                        {"type": "pointerDown", "button": 0},
                        {"type": "pointerUp", "button": 0}]}]})
        return True
    except WebDriverError:
        return False


def click_canvas(d, x, y):
    """Click the room canvas at a world point (x, depth 0..1)."""
    p = d.js("""return (() => { const cv = document.getElementById('roomCanvas');
      if (!cv) return null; const r = cv.getBoundingClientRect();
      return {px: r.left + arguments[0] / PalStage.W * r.width,
              py: r.top + (PalStage.GROUND_TOP + arguments[1] * PalStage.GROUND_DEEP) / PalStage.H * r.height,
              left: r.left, right: r.right, top: r.top, bottom: r.bottom}; })()""", x, y)
    if not p:
        return False
    ok = click_at(d, p["px"], p["py"])
    if not ok:
        d.js("""const cv=document.getElementById('roomCanvas'); const r=cv.getBoundingClientRect();
          cv.dispatchEvent(new MouseEvent('click',{bubbles:true,clientX:arguments[0],clientY:arguments[1]}));""",
            p["px"], p["py"])
    return True


def shot(d, label, report):
    try:
        os.makedirs(report.shot_dir, exist_ok=True)
        path = os.path.join(report.shot_dir, re.sub(r"[^a-z0-9]+", "-", label.lower()).strip("-") + ".png")
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
        if "AudioContext was not allowed to start" in msg or "favicon.ico" in msg:
            continue
        report.console.append({"where": label, "level": e.get("level"), "message": msg[:700]})


AUDIT_JS = r"""
return (() => {
  const out = {viewport: [innerWidth, innerHeight],
               page_x: Math.max(0, document.documentElement.scrollWidth - innerWidth),
               page_y: Math.max(0, document.documentElement.scrollHeight - innerHeight),
               off_right: [], off_left: [], off_bottom: [], overlaps: [], cut_text: [], notes: []};
  const visible = el => { const s = getComputedStyle(el); const r = el.getBoundingClientRect();
    return s.display !== 'none' && s.visibility !== 'hidden' && r.width > 1 && r.height > 1; };
  const rect = el => { const r = el.getBoundingClientRect();
    return {l: Math.round(r.left), t: Math.round(r.top), r: Math.round(r.right), b: Math.round(r.bottom),
            w: Math.round(r.width), h: Math.round(r.height)}; };
  const describe = el => ((el.id ? '#' + el.id : '') + (el.dataset && el.dataset.pane ? ' pane=' + el.dataset.pane : '') +
                          (el.dataset && el.dataset.shoptab ? ' tab=' + el.dataset.shoptab : '') +
                          (el.innerText || el.getAttribute('aria-label') || el.tagName || '').trim().slice(0, 48));
  const els = [...document.querySelectorAll(
    '#roomTabs button, #roomButtons button, #roomButtons canvas, #weddingCard button, ' +
    '.shop-tabs button, #shopTabs button, #roomButtons [data-mural-ink], #roomButtons [data-wish]')].filter(visible);
  for (const el of els) {
    const r = rect(el);
    if (r.r > innerWidth + 1) out.off_right.push({el: describe(el), rect: r});
    if (r.l < -1) out.off_left.push({el: describe(el), rect: r});
    if (r.b > innerHeight + 1) out.off_bottom.push({el: describe(el), rect: r});
  }
  for (let i = 0; i < els.length; i++) {
    for (let j = i + 1; j < els.length; j++) {
      const a = els[i], b = els[j];
      if (a.parentElement !== b.parentElement && !(a.closest('.shop-tabs') && b.closest('.shop-tabs'))) continue;
      const ra = rect(a), rb = rect(b);
      const ox = Math.min(ra.r, rb.r) - Math.max(ra.l, rb.l);
      const oy = Math.min(ra.b, rb.b) - Math.max(ra.t, rb.t);
      if (ox > 3 && oy > 3) out.overlaps.push({a: describe(a), b: describe(b), ox, oy});
    }
  }
  const texts = [...document.querySelectorAll('#roomTip, #gameDetail, .me-note, #weddingCard h3, #weddingCard p, ' +
    '.fashion-theme, .shop-tabs button, #coinBar, #meterWords')].filter(visible);
  for (const el of texts) {
    if (el.scrollWidth > el.clientWidth + 3 && getComputedStyle(el).overflowX !== 'visible') {
      out.cut_text.push({el: describe(el), scroll: el.scrollWidth, client: el.clientWidth});
    }
  }
  const tabs = document.getElementById('roomTabs');
  if (tabs && visible(tabs)) {
    out.tabs = rect(tabs);
    if (out.tabs.r > innerWidth + 1) out.notes.push('the room tab bar is wider than the screen');
    if (out.tabs.b > innerHeight + 1) out.notes.push('the room tab bar is below the screen');
  }
  const card = document.getElementById('weddingCard');
  if (card && visible(card)) {
    out.wedding_card = rect(card);
    if (out.wedding_card.l < 0 || out.wedding_card.r > innerWidth ||
        out.wedding_card.t < 0 || out.wedding_card.b > innerHeight) out.notes.push('the wedding card is cut off');
  }
  const rb = document.getElementById('roomButtons');
  if (rb && visible(rb)) {
    out.buttons = rect(rb);
    out.buttons_scroll = {y: Math.max(0, rb.scrollHeight - rb.clientHeight), x: Math.max(0, rb.scrollWidth - rb.clientWidth)};
    if (out.buttons.r > innerWidth + 1) out.notes.push('the right-hand button box is wider than the screen');
    if (out.buttons.l < -1) out.notes.push('the right-hand button box starts off the left of the screen');
  }
  return out;
})()
"""


def audit(d, label, report):
    try:
        out = d.js(AUDIT_JS)
    except WebDriverError as e:
        report.problem("layout audit: " + label, e)
        return {}
    ok = (out.get("page_x", 0) <= 1 and not out.get("off_right") and not out.get("off_left") and
          not out.get("overlaps") and not out.get("notes"))
    report.check("layout: " + label, ok, out)
    return out


def wait_game(d, phase, timeout=40):
    return d.wait(f"return roomInfo && roomInfo.game && roomInfo.game.phase === {json.dumps(phase)}",
                  timeout, "the game to reach " + phase)


def wait_wedding(d, phase, timeout=30):
    return d.wait(f"return roomInfo && roomInfo.wedding && roomInfo.wedding.phase === {json.dumps(phase)}",
                  timeout, "the wedding to reach " + phase)


def students_to_wedding(drivers, report):
    for d in drivers:
        ok = False
        for attempt in range(4):
            pane(d, "place")
            click_css(d, '#roomButtons [data-tap="go"][data-name="wedding"]')
            ok = d.wait("return roomInfo && roomInfo.people && roomInfo.people.some(p => p.seat === roomInfo.you && p.where === 'wedding')",
                        4, "")
            if ok:
                break
            time.sleep(.3)
        if not ok:
            report.problem("wedding: a student did not reach the garden",
                           d.js("return roomInfo && {you:roomInfo.you,people:roomInfo.people}"))
    # The server says where everyone is; the drawn screen catches up a moment later.
    ok = True
    detail = []
    for d in drivers:
        seen = d.wait("return inWedding && inWedding()", 6, "")
        detail.append(d.js("""const st=roomStage&&roomStage.state; const m=st&&st.room&&st.room.find(x=>x.me);
            return {inW:typeof inWedding==='function'?inWedding():null, you:roomInfo.you,
                    stageYou:st&&st.you, m:m&&{x:m.x,y:m.y}, places:st&&st.places,
                    where:(roomInfo.people.find(p=>p.seat===roomInfo.you)||{}).where,
                    button:!!document.querySelector('#roomButtons [data-wedding-start="1"]')}"""))
        ok = ok and seen
    report.check("wedding: all three students walk to the garden", ok, detail)
    return ok


def run_fashion(a, b, c, p, report):
    report.note("fashion show")
    pane(a, "games")
    ok = click_css(a, '#roomButtons [data-game="create"][data-kind="fashion"]')
    ok = ok and wait_game(a, "lobby", 8)
    report.check("fashion: the host opens the fashion lobby", ok, a.js("return roomInfo && roomInfo.game"))
    for d in (b, c):
        pane(d, "games")
        d.wait("return roomInfo && roomInfo.game && roomInfo.game.phase === 'lobby'", 6, "the fashion lobby")
        click_css(d, '#roomButtons [data-game="join"]')
    time.sleep(.6)
    joined = a.js("return (roomInfo.game.joined || []).length")
    report.check("fashion: two friends join the lobby", joined >= 3, joined)
    click_css(a, '#roomButtons [data-game="start"]')
    wait_game(a, "dressing", 10)
    # Dress-up: click a real tile, then take the dressing screenshot.
    a.js("const t=document.querySelector('#roomButtons .fashion-tile'); if(t) t.click();")
    time.sleep(.3)
    shot(a, "fashion-dressing", report)
    audit(a, "fashion dressing", report)
    for d in (a, b, c):
        click_css(d, '#roomButtons [data-game="ready"]')
    wait_game(a, "runway", 20)
    time.sleep(.6)
    # Let one walker go, then react from a watcher.
    a.wait("return roomInfo.game.walker !== null", 15, "a runway walker")
    walker = a.js("return roomInfo.game.walker")
    watcher = b if b.js("return roomInfo.you") != walker else c
    click_css(watcher, '#roomButtons [data-react="👏"]')
    time.sleep(.25)
    shot(watcher, "fashion-runway", report)
    audit(watcher, "fashion runway", report)
    wait_game(a, "results", 90)
    time.sleep(.4)
    awards = a.js("return (roomInfo.game.awards || {})")
    joined = a.js("return (roomInfo.game.joined || []).length")
    report.check("fashion: every walker gets a kind ribbon", len(awards) == joined and joined >= 3,
                 {"joined": joined, "awards": len(awards)})
    shot(a, "fashion-results", report)
    audit(a, "fashion results", report)
    shot(p, "projector-fashion", report)


def run_wedding(a, b, c, p, report):
    report.note("wedding")
    if not students_to_wedding([a, b, c], report):
        return
    pane(a, "party")
    started = click_css(a, '#roomButtons [data-wedding-start="1"]')
    if not started:
        report.problem("wedding: the Hold a wedding button is missing in the garden",
                       a.js("return {pane:roomPane, where:(roomInfo.people.find(p=>p.seat===roomInfo.you)||{}).where}"))
        a.js("if (typeof startWedding === 'function') startWedding();")
    ok = a.wait("return !document.getElementById('weddingCard').hidden && weddingAsk && weddingAsk.mode === 'pick'", 8, "the wedding pick card")
    report.check("wedding: the pick card opens", ok, a.js("return weddingAsk"))
    shot(a, "wedding-pick", report)
    audit(a, "wedding pick card", report)
    # Pick Ben if he is in the list, else the first friend.
    pick = a.js("""const bs=[...document.querySelectorAll('#weddingCard [data-wedding=\"pick\"]')];
      const el=bs.find(x => (x.innerText||'').includes(arguments[0])) || bs[0];
      return el ? el.dataset.name : null;""", "Night Ben")
    if not pick:
        report.problem("wedding: there is a friend to pick", a.js("return document.getElementById('weddingCard').innerText"))
        return
    click_text(a, '#weddingCard [data-wedding="pick"]', pick)
    ok = b.wait("return !document.getElementById('weddingCard').hidden && weddingAsk && weddingAsk.mode === 'invite'", 10, "the invite card")
    report.check("wedding: the friend sees the invite card", ok, b.js("return weddingAsk"))
    shot(b, "wedding-invite", report)
    audit(b, "wedding invite card", report)
    click_css(b, '#weddingCard [data-wedding="yes"]')
    ok = wait_wedding(a, "ceremony", 8)
    report.check("wedding: yes starts the ceremony", ok, a.js("return roomInfo && roomInfo.wedding"))
    time.sleep(5.5)
    shot(a, "wedding-ceremony", report)
    audit(a, "wedding ceremony", report)
    shot(p, "projector-wedding", report)
    ok = a.wait("return !roomInfo.wedding", 30, "the wedding to finish")
    report.check("wedding: the ceremony finishes", ok, a.js("return roomInfo && roomInfo.wedding"))


def run_mural(a, p, report):
    report.note("class mural")
    pane(a, "art")
    ok = click_text(a, '#roomButtons button', "Class mural")
    ok = ok and a.wait("return !!document.getElementById('muralBoard')", 8, "the mural board")
    report.check("mural: the Art pane opens the class mural", ok, a.js("return roomPane"))
    if not ok:
        return
    a.js("const b=document.querySelector('#roomButtons [data-mural-ink=\"2\"]'); if(b) b.click();")
    time.sleep(.2)
    # Paint a few squares at real canvas points, slowly enough for the 3/s limit.
    for fx, fy in ((.2, .3), (.3, .35), (.4, .4)):
        cv = a.js("const c=document.getElementById('muralBoard'); const r=c.getBoundingClientRect();"
                  "return {x:r.left+r.width*arguments[0], y:r.top+r.height*arguments[1],"
                  "l:r.left,r:r.right,t:r.top,b:r.bottom};", fx, fy)
        click_at(a, cv["x"], cv["y"])
        time.sleep(.45)
    time.sleep(.8)
    mine = a.js("return (document.getElementById('muralMine')||{}).innerText || ''")
    report.check("mural: a tap paints a square and the count updates", "painted" in mine.lower(), mine)
    shot(a, "mural-pane", report)
    audit(a, "mural pane", report)
    shot(p, "projector-mural", report)


def run_home(a, p, report):
    report.note("home pane with a piece picked up")
    pane(a, "home")
    if not a.js("return !!(roomInfo && roomInfo.home && roomInfo.home.mine)"):
        click_css(a, '#roomButtons [data-home="mine"]')
    ok = a.wait("return roomInfo && roomInfo.home && roomInfo.home.mine", 10, "the student's own home")
    report.check("home: the Home pane opens my home", ok, a.js("return roomPane"))
    if not ok:
        return
    # Put out a balloons piece if it is not out yet. Free pieces are always there.
    has = a.js("return (roomInfo.home.items || []).some(i => i.key === 'balloons')")
    if not has:
        click_css(a, '#roomButtons [data-furn="balloons"]')
        time.sleep(.2)
        click_canvas(a, 170, .55)
        a.wait("return (roomInfo.home.items || []).some(i => i.key === 'balloons')", 8, "the balloons to go out")
    # Pick it up with the real click handler, then check the style controls.
    click_css(a, '#roomButtons [data-moving="1"]')
    item = a.js("return (roomInfo.home.items || []).find(i => i.key === 'balloons')")
    if not item:
        report.problem("home: the balloons piece is out", a.js("return roomInfo.home.items"))
        return
    click_canvas(a, item["x"], item["y"])
    ok = a.wait("return typeof furnArmed !== 'undefined' && furnArmed && furnArmed.piece", 8, "a picked-up piece")
    report.check("home: clicking a thing picks it up", ok, a.js("return furnArmed"))
    if not ok:
        return
    paints = a.js("return document.querySelectorAll('#roomButtons button[data-paint]').length")
    sizes = a.js("return document.querySelectorAll('#roomButtons [data-size]').length")
    flips = a.js("return document.querySelectorAll('#roomButtons [data-flip]').length")
    report.check("home: a picked-up piece has paint, size and flip controls",
                 paints == pixel.FURN_PAINTS and sizes == pixel.FURN_SIZES and flips == 1,
                 {"paints": paints, "sizes": sizes, "flips": flips})
    shot(a, "home-picked-up", report)
    audit(a, "home picked-up piece", report)
    # Use the controls and check the server kept the change.
    click_css(a, '#roomButtons [data-paint="3"]')
    click_css(a, '#roomButtons [data-size="2"]')
    click_css(a, '#roomButtons [data-flip="1"]')
    got = a.wait("""return (roomInfo.home.items || []).some(i => i.id === furnArmed.piece &&
        i.paint === 3 && i.size === 2 && i.flip === true)""", 8, "the styled piece")
    report.check("home: paint, size and flip reach the home", got, a.js("return roomInfo.home.items"))
    shot(a, "home-styled", report)


def run_shop(a, report):
    report.note("shop tabs")
    pane(a, "shop")
    for tab in ("furniture", "room", "look", "wear"):
        ok = click_css(a, f'#roomButtons [data-shoptab="{tab}"]')
        ok = ok and a.wait(f"return shopTab === {json.dumps(tab)}", 4, "the " + tab + " tab")
        tiles = a.js("return document.querySelectorAll('#roomButtons [data-buy]').length")
        report.check("shop: the " + tab + " tab opens with things in it", ok and tiles > 0, {"tiles": tiles})
        shot(a, "shop-" + tab, report)
        audit(a, "shop " + tab, report)


def run_teacher(t, report):
    report.note("teacher page")
    t.request("POST", f"/session/{t.sid}/url", {"url": base + "/pixel/teacher"})
    t.wait("return !document.getElementById('gate').hidden", 20, "the teacher gate")
    t.send("#key", server.ADMIN_KEY)          # log in by typing the admin key
    t.click("#gate button")
    ok = t.wait("return !document.getElementById('page').hidden && document.querySelectorAll('#rows tr').length >= 3", 20, "the teacher page")
    report.check("teacher: typing the admin key opens the teacher page", ok,
                 t.js("return document.getElementById('rows') && document.getElementById('rows').innerText"))
    shot(t, "teacher-top", report)
    # The mural card lives further down a long page: scroll it into view before judging it.
    t.js("const el=document.getElementById('muralPic'); if(el) el.scrollIntoView({block:'center'});")
    time.sleep(.4)
    audit(t, "teacher page", report)
    m = t.js("""const c=document.getElementById('muralPic'); const r=c.getBoundingClientRect();
      return {w:c.width,h:c.height,left:r.left,right:r.right,top:r.top,bottom:r.bottom,
              painters:(document.getElementById('muralWho')||{}).length||0,
              total:(document.getElementById('muralTotal')||{}).innerText||''}""")
    report.check("teacher: the class mural card is on screen and inside the width",
                 m and m["left"] >= 0 and m["right"] <= t.js("return innerWidth") + 1 and m["w"] > 100, m)
    shot(t, "teacher-mural", report)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--port", type=int, default=8907)
    ap.add_argument("--base", default="")
    ap.add_argument("--width", type=int, default=1024)
    ap.add_argument("--height", type=int, default=600)
    ap.add_argument("--tag", default="")
    ap.add_argument("--shot-dir", required=True)
    ap.add_argument("--json-out", required=True)
    ap.add_argument("--driver", default="chromedriver")
    ap.add_argument("--browser", default="/usr/bin/chromium")
    args = ap.parse_args()
    global base, W, H
    base = args.base or f"http://127.0.0.1:{args.port}"
    W, H = args.width, args.height
    os.makedirs(args.shot_dir, exist_ok=True)
    report = Report(args.shot_dir)
    tag = args.tag or str(int(time.time()))[-5:]
    names, ids = setup_state(base, tag, report)
    drivers = []
    a = b = c = p = t = None
    try:
        for i, name in enumerate(names):
            d = Driver(args.driver, args.browser, W, H)
            drivers.append(d)
            if not login(d, base, name, report):
                report.problem("could not log in " + name, "")
                continue
            if i == 0:
                a = d
            elif i == 1:
                b = d
            else:
                c = d
        for d in (a, b, c):
            if d and not open_hang(d, report):
                report.problem("could not open the Hang out", d.js("return roomInfo"))
        p = Driver(args.driver, args.browser, W, H)
        drivers.append(p)
        p.request("POST", f"/session/{p.sid}/url", {"url": base + "/pixel/show"})
        p.wait("return typeof PalStage !== 'undefined' && document.querySelectorAll('#people button').length >= 3",
               35, "the projector")
        t = Driver(args.driver, args.browser, W, H)
        drivers.append(t)
        shot(a, "hang-first-look", report)
        audit(a, "hang first look", report)
        run_fashion(a, b, c, p, report)
        run_wedding(a, b, c, p, report)
        run_mural(a, p, report)
        run_home(a, p, report)
        run_shop(a, report)
        run_teacher(t, report)
        # Projector layout: the world and the side column must both be in view.
        p_out = p.js("""const s=document.getElementById('stage').getBoundingClientRect();
          const b=document.getElementById('bar').getBoundingClientRect();
          return {viewport:[innerWidth,innerHeight], stage:{l:s.left,r:s.right,t:s.top,b:s.bottom},
                  bar:{l:b.left,r:b.right,t:b.top,b:b.bottom},
                  pageX:document.documentElement.scrollWidth-innerWidth,
                  pageY:document.documentElement.scrollHeight-innerHeight,
                  fashionVisible:!!(document.getElementById('fashionSpot') && document.getElementById('fashionSpot').offsetParent)}""")
        ok = (p_out["pageX"] <= 1 and p_out["stage"]["r"] <= args.width + 1 and
              p_out["bar"]["r"] <= args.width + 1)
        report.check("projector: stage and side column fit the screen", ok, p_out)
    except Exception as e:
        report.problem("the sweep stopped", f"{type(e).__name__}: {e}\n{traceback.format_exc()[-1200:]}")
    finally:
        for d, label in zip(drivers, ["Ana", "Ben", "Cy", "projector", "teacher"]):
            if d:
                collect_console(d, "final " + label, report)
        seen = set()
        for d in drivers:
            if not d or id(d) in seen:
                continue
            seen.add(id(d))
            try:
                d.close()
            except Exception:
                pass
    result = {"viewport": [W, H], "checks": report.checks, "problems": report.problems,
              "notes": report.notes, "console": report.console, "screenshots": report.screenshots}
    with open(args.json_out, "w") as f:
        json.dump(result, f, indent=2, default=str)
    print(json.dumps({"viewport": [W, H], "checks": len(report.checks),
                      "failed": [c for c in report.checks if not c["ok"]],
                      "console_errors": report.console_errors(),
                      "screenshots": report.screenshots, "notes": report.notes}, indent=2)[:12000])
    return 0 if report.ok() else 1


if __name__ == "__main__":
    sys.exit(main())
