#!/usr/bin/env python3
"""Browser check for Pixel Pals open houses: 3 students, the projector and the teacher.

It starts the server's own page in five headless Chromium sessions, gives two
students 3 things out in their home through the normal server calls, then plays
an open house through: the one-tap invite, arriving, the little banner, hearts,
both small-laptop sizes, the host closing the door, a second host, Auto on the
projector, the teacher card, and the teacher closing the Hang out.

    MAZE_PORT=8912 MAZE_STATE_FILE=/tmp/openhouse-state.json python3 server.py
    python3 tools/e2e_openhouse.py --port 8912 --shots /tmp/openhouse

It needs chromium and chromedriver on PATH, like the other tools/e2e_*.py.
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

BASE = ""
SHOT_DIR = ""
PAL = {"key": "ohpal", "size": 16, "speed": 6, "palette": pixel.PIP["palette"],
       "frames": pixel.PIP["frames"], "names": pixel.PIP["names"], "title": "My pal"}
report = {"checks": [], "problems": [], "screenshots": [], "notes": []}


def check(label, ok, detail=""):
    report["checks"].append({"check": label, "ok": bool(ok), "detail": str(detail)[:900]})
    if not ok:
        report["problems"].append(f"{label}: {detail}"[:1200])
    print(("OK   " if ok else "FAIL ") + label + (f"  [{str(detail)[:300]}]" if not ok else ""))
    return bool(ok)


def post(path, data, timeout=120):
    req = urllib.request.Request(BASE + path, data=json.dumps(data).encode(),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as f:
        return json.load(f)


def wait(d, script, timeout=15, what=""):
    end = time.time() + timeout
    last = None
    while time.time() < end:
        try:
            if d.js(script):
                return True
        except WebDriverError as e:
            last = e
        time.sleep(.12)
    if what:
        check(f"timed out waiting for {what}", False, last or "")
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


def text_of(d, css):
    return d.js("return (document.querySelector(arguments[0]) || {}).innerText || ''", css)


def pane(d, name):
    click_js(d, f'#roomTabs [data-pane="{name}"]')
    return wait(d, f"return roomPane === {json.dumps(name)}", 5, f"the {name} pane")


def resize(d, width, height):
    try:
        d.request("POST", f"/session/{d.sid}/goog/cdp/execute",
                  {"cmd": "Emulation.setDeviceMetricsOverride",
                   "params": {"width": width, "height": height,
                              "deviceScaleFactor": 1, "mobile": False}})
    except WebDriverError:
        pass
    time.sleep(.5)


def shot(d, label):
    try:
        os.makedirs(SHOT_DIR, exist_ok=True)
        path = os.path.join(SHOT_DIR, re.sub(r"[^a-z0-9]+", "-", label.lower()).strip("-") + ".png")
        data = d.request("GET", f"/session/{d.sid}/screenshot")
        with open(path, "wb") as f:
            f.write(base64.b64decode(data))
        report["screenshots"].append(path)
        return path
    except Exception:
        return None


def collect_console(d, where):
    try:
        for e in d.logs():
            msg = e.get("message") or ""
            if "favicon.ico" in msg or "AudioContext was not allowed to start" in msg:
                continue
            if e.get("level") == "SEVERE":
                check(f"console is clean in {where}", False, msg[:700])
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
          const s = getComputedStyle(el);
          if (el.scrollWidth > el.clientWidth + 2 && ['visible', 'clip'].includes(s.overflowX))
            out.push('cut-off inside the buttons: ' + (el.innerText || '').slice(0, 24));
        }
      }
      const bar = document.getElementById('openHouseBar');
      if (bar && !bar.hidden) {
        const br = bar.getBoundingClientRect(), rr = document.getElementById('roomHost').getBoundingClientRect();
        if (br.left < rr.left - 1 || br.right > rr.right + 1 || br.top < rr.top - 1)
          out.push('the open house banner is outside the home picture');
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
        time.sleep(.7)
    return False


def setup():
    names = ["Ana", "Ben", "Cy"]
    ids = {}
    for name in names:
        ids[name] = post("/join", {"name": name})["id"]
        post("/pixel/save", {"id": ids[name], "drawing": PAL})
    post("/pixel/teacher", {"key": server.ADMIN_KEY, "action": "open", "level": pixel.LEVEL_ORDER[-1]})
    post("/pixel/teacher", {"key": server.ADMIN_KEY, "action": "placed_clear"})
    post("/pixel/teacher", {"key": server.ADMIN_KEY, "action": "end_game"})
    post("/pixel/teacher", {"key": server.ADMIN_KEY, "action": "room", "on": False})
    post("/pixel/teacher", {"key": server.ADMIN_KEY, "action": "room", "on": True})
    fails = []
    for name in ("Ana", "Ben"):
        for key in pixel.LEVEL_ORDER:
            out = post("/pixel/run", {"id": ids[name], "level": key,
                                      "code": pixel.LEVEL_BY_KEY[key]["reference"]})
            if out.get("error") or not (out.get("stars") or [False])[0]:
                fails.append((name, key, out.get("error"), out.get("stars")))
    check("setup: Ana and Ben can finish their missions for coins", not fails, fails[:2])
    for name in names:
        out = post("/pixel/room/do", {"id": ids[name], "what": "join"})
        if not out.get("ok"):
            fails.append((name, out))
    check("setup: all three are in the Hang out", not fails, fails[:2])
    for name in ("Ana", "Ben"):
        pid = ids[name]
        for key in ("balloons", "lamp", "teddy"):
            out = post("/pixel/room/do", {"id": pid, "what": "buy", "key": key})
            if out.get("error"):
                fails.append((name, "buy", key, out.get("error")))
        out = post("/pixel/room/do", {"id": pid, "what": "home"})
        if out.get("error"):
            fails.append((name, "home", out.get("error")))
        for key, x in (("rug", 60), ("plant", 90), ("balloons", 120)):
            out = post("/pixel/room/do", {"id": pid, "what": "furnish", "key": key, "x": x, "y": .5})
            if out.get("error"):
                fails.append((name, "furnish", key, out.get("error")))
    check("setup: Ana and Ben each have 3 things out in their own home", not fails, fails[:4])
    return names, ids


def main():
    drivers = {}
    try:
        for label, size in (("ana", (1093, 530)), ("ben", (1093, 530)), ("cy", (1093, 530)),
                            ("show", (1093, 530)), ("teacher", (1093, 530))):
            drivers[label] = Driver("/usr/bin/chromedriver", "/usr/bin/chromium", *size)
        ana, ben, cy, show, teacher = (drivers[k] for k in ("ana", "ben", "cy", "show", "teacher"))
        for label, name in (("ana", "Ana"), ("ben", "Ben"), ("cy", "Cy")):
            check(f"{name} can log in", login(drivers[label], name))
            check(f"{name} is in the Hang out", open_hang(drivers[label]))
        check("Ana starts in her own home", wait(ana, "return !!(roomInfo.home && roomInfo.home.mine)", 12, "Ana's home"),
              ana.js("return roomInfo.home"))
        check("Ben starts in his own home", wait(ben, "return !!(roomInfo.home && roomInfo.home.mine)", 12, "Ben's home"),
              ben.js("return roomInfo.home"))

        show.request("POST", f"/session/{show.sid}/url", {"url": BASE + "/pixel/show"})
        wait(show, "return typeof stage !== 'undefined' && !!stage && document.getElementById('closed').hidden", 20, "the projector")
        check("the projector is in Auto", show.js("return cam.mode === 'auto'"), show.js("return cam"))
        teacher.request("POST", f"/session/{teacher.sid}/url", {"url": BASE + "/pixel/teacher"})
        wait(teacher, "return !document.getElementById('gate').hidden || !document.getElementById('page').hidden", 20, "the teacher gate")
        if not teacher.js("return document.getElementById('gate').hidden"):
            teacher.js("sessionStorage.setItem('pixelKey', arguments[0]); location.reload();", server.ADMIN_KEY)
            wait(teacher, "return !document.getElementById('page').hidden", 20, "the teacher page")
        check("the teacher page loaded", not teacher.js("return document.getElementById('page').hidden"))

        pane(ana, "home")
        check("Ana's Home pane has the Open house button", "Open house" in text_of(ana, "#roomButtons"),
              text_of(ana, "#roomButtons")[:400])
        shot(ana, "ana-home-open-house-button")
        click_room(ana, "[data-openhouse]")
        check("Ana's open house is on", wait(ana, "return !!(roomInfo.openhouse && roomInfo.openhouse.mine)", 10, "Ana's open house"),
              ana.js("return roomInfo.openhouse"))
        check("the host sees the open house banner", wait(ana, "return !document.getElementById('openHouseBar').hidden", 5, "the home banner"),
              text_of(ana, "#openHouseBar"))
        check("the host banner counts the first friends", "0 friends here" in text_of(ana, "#openHouseBar"),
              text_of(ana, "#openHouseBar"))
        shot(ana, "ana-open-house-on")

        check("Ben gets the one-tap invite", wait(ben, "return !document.getElementById('houseStatus').hidden", 8, "Ben's invite"),
              text_of(ben, "#houseStatus"))
        check("Cy gets the one-tap invite", wait(cy, "return !document.getElementById('houseStatus').hidden", 8, "Cy's invite"),
              text_of(cy, "#houseStatus"))
        check("the invite says Ana's open house and Come in",
              "Ana's open house" in text_of(ben, "#houseStatus") and "Come in" in text_of(ben, "#houseStatus"),
              text_of(ben, "#houseStatus"))
        issues = layout_issues(ben, "Ben's invite at 1093x530")
        check("the invite fits at 1093x530", not issues, issues)
        shot(ben, "ben-invite-1093x530")

        check("projector Auto visits Ana's open house",
              wait(show, "return (document.getElementById('placeTag').textContent || '').includes('Ana')", 12, "Auto at Ana's home"),
              text_of(show, "#placeTag"))
        shot(show, "projector-auto-ana-open-house")

        teacher.js("refresh()")
        check("teacher card shows the open house",
              wait(teacher, "return !document.getElementById('roomOpenHouse').hidden", 10, "the teacher open house line"),
              text_of(teacher, "#roomOpenHouse"))
        check("teacher card names Ana's open house", "Open house at Ana" in text_of(teacher, "#roomOpenHouse"),
              text_of(teacher, "#roomOpenHouse"))
        teacher.js("document.getElementById('roomOpenHouse').scrollIntoView({block:'center'})")
        time.sleep(.3)
        shot(teacher, "teacher-open-house-card")

        click_js(ben, "#houseStatus")
        check("Ben lands in Ana's home", wait(ben, "return !!(roomInfo.home && roomInfo.home.name === 'Ana')", 12, "Ben in Ana's home"),
              ben.js("return roomInfo.home"))
        shot(ana, "ana-waves-ben-in")
        shot(ben, "ben-arrives-confetti")
        check("Ben is visiting, not at home", ben.js("return roomInfo.home.mine === false"))
        check("the invite disappears after Ben comes in", wait(ben, "return document.getElementById('houseStatus').hidden", 5, "the invite to hide"))
        check("Ana's banner says 1 friend here", wait(ana, "return document.getElementById('openHouseBar').textContent.includes('1 friend here')", 10, "1 friend in the banner"),
              text_of(ana, "#openHouseBar"))
        shot(ben, "ben-arrives-in-ana-home")
        shot(ana, "ana-open-house-1-friend")

        click_js(cy, "#houseStatus")
        check("Cy lands in Ana's home", wait(cy, "return !!(roomInfo.home && roomInfo.home.name === 'Ana')", 12, "Cy in Ana's home"),
              cy.js("return roomInfo.home"))
        check("Ana's banner counts 2 friends", wait(ana, "return document.getElementById('openHouseBar').textContent.includes('2 friends here')", 10, "2 friends in the banner"),
              text_of(ana, "#openHouseBar"))
        shot(ana, "ana-open-house-2-friends")
        shot(cy, "cy-arrives-in-ana-home")

        pane(ben, "home")
        check("Ben has the usual heart button", wait(ben, "return !!document.querySelector('#roomButtons [data-heart]')", 6, "the heart button"))
        click_room(ben, "[data-heart]")
        check("Ben gives Ana's home a heart", wait(ben, "return !!(roomInfo.home && roomInfo.home.hearted)", 8, "the heart to count"),
              ben.js("return roomInfo.home"))
        check("the heart button says it was given", "You gave this home a heart" in text_of(ben, "#roomButtons"),
              text_of(ben, "#roomButtons")[:500])
        shot(ben, "ben-gave-heart")

        for d in (ana, ben, cy, show):
            resize(d, 1024, 600)
        time.sleep(.6)
        issues = layout_issues(ana, "Ana's open house at 1024x600")
        check("the open house home fits at 1024x600", not issues, issues)
        check("the host banner still shows 2 friends at 1024x600",
              "2 friends here" in text_of(ana, "#openHouseBar"), text_of(ana, "#openHouseBar"))
        shot(ana, "ana-open-house-1024x600")
        shot(ben, "ben-heart-1024x600")
        issues = layout_issues(ben, "Ben's home page at 1024x600")
        check("the visiting home page fits at 1024x600", not issues, issues)

        click_js(ana, "#openHouseBar [data-house-close]")
        check("the host closes the door", wait(ana, "return !roomInfo.openhouse", 10, "the open house to close"),
              ana.js("return roomInfo.openhouse"))
        check("the home banner goes away", wait(ana, "return document.getElementById('openHouseBar').hidden", 5, "the banner to hide"))
        check("a guest's open house banner goes away too", wait(ben, "return document.getElementById('openHouseBar').hidden", 8, "Ben's banner to hide"))
        shot(ben, "ana-open-house-ended")
        teacher.js("refresh()")
        check("the teacher line goes away after the door closes",
              wait(teacher, "return document.getElementById('roomOpenHouse').hidden", 12, "the teacher line to hide"))

        pane(ben, "home")
        click_room(ben, '[data-home="mine"]')
        check("Ben goes to his own home", wait(ben, "return !!(roomInfo.home && roomInfo.home.mine)", 12, "Ben's home"),
              ben.js("return roomInfo.home"))
        click_room(ben, "[data-openhouse]")
        check("Ben's open house is on", wait(ben, "return !!(roomInfo.openhouse && roomInfo.openhouse.mine)", 10, "Ben's open house"),
              ben.js("return roomInfo.openhouse"))
        check("Ana gets Ben's invite", wait(ana, "return !document.getElementById('houseStatus').hidden", 8, "Ana's invite"),
              text_of(ana, "#houseStatus"))
        check("Cy gets Ben's invite", wait(cy, "return !document.getElementById('houseStatus').hidden", 8, "Cy's invite"),
              text_of(cy, "#houseStatus"))
        check("the second invite names Ben", "Ben's open house" in text_of(ana, "#houseStatus"),
              text_of(ana, "#houseStatus"))
        issues = layout_issues(ana, "Ana's invite at 1024x600")
        check("the invite fits at 1024x600", not issues, issues)
        shot(ana, "ana-invite-ben-1024x600")
        check("projector Auto visits Ben's open house",
              wait(show, "return (document.getElementById('placeTag').textContent || '').includes('Ben')", 12, "Auto at Ben's home"),
              text_of(show, "#placeTag"))
        shot(show, "projector-auto-ben-open-house")

        click_js(cy, "#houseStatus")
        check("Cy crosses to Ben's home", wait(cy, "return !!(roomInfo.home && roomInfo.home.name === 'Ben')", 12, "Cy in Ben's home"),
              cy.js("return roomInfo.home"))
        check("Ben's banner says 1 friend here", wait(ben, "return document.getElementById('openHouseBar').textContent.includes('1 friend here')", 10, "Ben's first friend"),
              text_of(ben, "#openHouseBar"))
        shot(ben, "ben-open-house-1024x600")

        teacher.js("refresh()")
        check("teacher card shows Ben's open house", wait(teacher, "return !document.getElementById('roomOpenHouse').hidden && document.getElementById('roomOpenHouse').textContent.includes('Ben')", 12, "Ben's teacher line"),
              text_of(teacher, "#roomOpenHouse"))
        click_js(teacher, "#roomOpen")
        check("the teacher closes the Hang out",
              wait(teacher, "return document.getElementById('roomOpen').textContent.includes('Open the Hang out')", 12, "the Hang out to close"),
              text_of(teacher, "#roomOpen"))
        check("closing the Hang out hides the open house line",
              wait(teacher, "return document.getElementById('roomOpenHouse').hidden", 12, "the line to clear"))
        shot(teacher, "teacher-hangout-closed")

        for label, d in drivers.items():
            collect_console(d, label)
    finally:
        for d in drivers.values():
            d.close()


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", default="8912")
    ap.add_argument("--shots", default="/tmp/openhouse")
    args = ap.parse_args()
    BASE = f"http://127.0.0.1:{args.port}"
    SHOT_DIR = args.shots
    try:
        names, ids = setup()
        main()
    except Exception:
        traceback.print_exc()
        report["problems"].append("script crashed: " + traceback.format_exc()[-1200:])
    with open(os.path.join("/tmp", "openhouse-report.json"), "w") as f:
        json.dump(report, f, indent=2)
    print("\n=== SUMMARY ===")
    print("checks:", len(report["checks"]), "failed:", len(report["problems"]))
    for p in report["problems"]:
        print("PROBLEM:", p)
    print("screenshots:", len(report["screenshots"]))
    sys.exit(1 if report["problems"] else 0)
