#!/usr/bin/env python3
"""Real-browser bug hunt for the Strange Planet garage and Paint Shop.

This is a tool, not a test. It starts a throwaway server (unless --base is
given), makes one student who has every garage item and one brand-new student,
then drives headless Chromium at 1366x768 and 1280x720 through:

  * every garage tab, putting every unlocked item on the rover at least once,
    checking the stage preview and the map both draw it with no console errors;
  * every locked item's "how to get it" line, on the brand-new student;
  * Surprise me, the four saved looks, the rover name box and Done/reopen;
  * the Paint Shop: clicking squares, all six examples, simple/weird/broken
    code, the error line, wearing a painting and the class screen /planet/show;
  * calm mode, where nothing may animate;
  * layout: no off-screen buttons, no text overflowing its card, no late toast
    landing on top of the garage.

It also checks the four things this branch fixed in planet.html:
  * the garage reopens at the top, and a tab switch starts at the top;
  * paint cards and the Paint Shop's rover preview are not hidden by a hat;
  * the Paint Shop's red error line is visible behind the code;
  * the delayed "new levels" toast does not appear over an open sheet.

Usage (the default starts its own throwaway server on a free port):

    python3 tools/e2e_planet_garage.py
    python3 tools/e2e_planet_garage.py --base http://127.0.0.1:8796 \
        --student p0 --new-student p11
    python3 tools/e2e_planet_garage.py --shots /tmp/garage-shots

With --base the tool uses a server you already started. That server should
already have a fully unlocked student and a brand-new one (see the report's
setup notes); without --base it builds that state itself in a temp folder.

Exit code 0 means every check passed; 1 lists the checks that did not.
"""
import argparse
import json
import os
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "tools"))
import wd  # noqa: E402

PROBLEMS = []
SHOTS = None
ERRORS = []


def check(ok, text):
    print(("  ok  " if ok else "  !!  ") + text)
    if not ok:
        PROBLEMS.append(text)
    return ok


def shot(driver, name):
    path = os.path.join(SHOTS, name + ".png")
    driver.shot(path)
    return path


def collect(driver, tag):
    """Console errors since the last call, without repeats."""
    for entry in driver.logs():
        level, message = entry.get("level"), entry.get("message") or ""
        if level in ("SEVERE", "ERROR") or "Uncaught" in message:
            ERRORS.append((tag, message))
            print(f"  !!  console {tag}: {message[:220]}")
    return ERRORS


def http(base, path, data=None, timeout=20):
    body = None if data is None else json.dumps(data).encode("utf-8")
    headers = {"Content-Type": "application/json"} if body is not None else {}
    req = urllib.request.Request(base + path, data=body, headers=headers)
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def free_port():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def wait_server(base, proc=None, timeout=40):
    end = time.time() + timeout
    while time.time() < end:
        if proc is not None and proc.poll() is not None:
            return False
        try:
            http(base, "/planet/overview", timeout=1)
            return True
        except Exception:
            time.sleep(0.1)
    return False


def launch_server(folder, port):
    base = f"http://127.0.0.1:{port}"
    log_path = os.path.join(folder, "server.log")
    log = open(log_path, "w", encoding="utf-8")
    env = dict(os.environ, MAZE_PORT=str(port),
               MAZE_STATE_FILE=os.path.join(folder, "garage-state.json"))
    proc = subprocess.Popen([sys.executable, "server.py"], cwd=HERE, env=env,
                            stdout=log, stderr=subprocess.STDOUT)
    if not wait_server(base, proc):
        log.close()
        text = open(log_path, encoding="utf-8", errors="replace").read()[-3000:]
        proc.kill()
        raise SystemExit("the test server did not start:\n" + text)
    return base, proc, log, log_path


def stop_server(proc, log):
    try:
        if log:
            log.close()
    except Exception:
        pass
    if proc and proc.poll() is None:
        proc.terminate()
        try:
            proc.wait(timeout=6)
        except subprocess.TimeoutExpired:
            proc.kill()


def prepare_state(folder):
    """Start a fresh server, join a class, stop it, fill the saves, restart."""
    port = free_port()
    base, proc, log, log_path = launch_server(folder, port)
    names = ["Zoe", "Ace", "Nova", "Milo", "Ivy", "Rex", "Luna", "Finn",
             "Ada", "Kai", "Pip", "Bea"]
    ids = {}
    try:
        for name in names:
            ids[name] = http(base, "/join", {"name": name})["id"]
        for name in names:          # make a planet entry for every student
            http(base, f"/planet/state?id={ids[name]}")
        for name in names:          # /join saves the entries to disk
            http(base, "/join", {"name": name})
    finally:
        stop_server(proc, log)

    import planet
    import server

    state_path = os.path.join(folder, "garage-state.json")
    state = json.load(open(state_path, encoding="utf-8"))
    sites = list(dict.fromkeys(planet.SITE_ORDER + planet.BUILD_ORDER))
    stars = {key: [True, True, True] for key in sites}
    gifts = [item["key"] for item in server.GARAGE if "find" in item]
    badges = list(server.PLANET_BADGES)
    rich = [ids[name] for name in names if name != "Bea"]
    for pid in rich:
        entry = state["players"][pid]["planet"]
        entry["stars"] = dict(stars)
        entry["trophies"] = 99
    zoe = state["players"][ids["Zoe"]]["planet"]
    zoe["badges"] = list(badges)
    zoe["found"] = list(gifts)
    zoe["look"].update({"paint": "galaxy", "topper": "party", "wheels": "std",
                        "trail": "hearts", "world": "planet", "dance": "spin",
                        "glow": "noglow", "pet": "nopet", "horn": "beep"})
    state.setdefault("planet_class", {})["easy"] = True
    json.dump(state, open(state_path, "w", encoding="utf-8"))

    base, proc, log, log_path = launch_server(folder, port)
    return base, proc, log, ids["Zoe"], ids["Bea"]


def open_student(driver, base, pid, calm=False):
    driver.go(base + "/planet")
    driver.js(
        "localStorage.setItem('mazeId', arguments[0]);"
        "localStorage.setItem('planetIntroSeen', '1');"
        "localStorage.setItem('planetCalm', arguments[1]);",
        pid, "1" if calm else "0")
    driver.go(base + "/planet")
    driver.wait("return !!document.getElementById('app') && "
                "!document.getElementById('app').hidden", 30, "the planet page")
    return driver.js("return {me, stars: state.total_stars, calm: CALM}")


def open_garage(driver):
    if driver.js("return !document.getElementById('garage').hidden"):
        return
    driver.click("#starsButton")
    driver.wait("return !document.getElementById('garage').hidden", 10, "the garage")


def wait_js(driver, script, timeout=8, interval=0.03, *args):
    end = time.time() + timeout
    while time.time() < end:
        try:
            if driver.js(script, *args):
                return True
        except wd.WebDriverError:
            pass
        time.sleep(interval)
    return False


def box(driver, css):
    return driver.js(
        "const el=document.querySelector(arguments[0]); if(!el) return null;"
        "const r=el.getBoundingClientRect();"
        "return {left:r.left, top:r.top, right:r.right, bottom:r.bottom,"
        " width:r.width, height:r.height, scrollW:el.scrollWidth,"
        " clientW:el.clientWidth, scrollH:el.scrollHeight, clientH:el.clientHeight};", css)


def fits(driver, css, label, width, height):
    r = box(driver, css)
    if not r:
        return check(False, f"{label}: element is missing")
    ok = (r["width"] > 0 and r["left"] >= -1 and r["top"] >= -1
          and r["right"] <= width + 1 and r["bottom"] <= height + 1)
    return check(ok, f"{label}: inside the {width}x{height} page ({r['left']:.0f},"
                      f"{r['top']:.0f})-({r['right']:.0f},{r['bottom']:.0f})")


def patch_rover(driver):
    driver.js("""
      window.__draws = [];
      if (!window.__origDrawRover) {
        window.__origDrawRover = window.drawRover;
        window.drawRover = function (ctx, x, y, s, angle, alpha, gear, now) {
          const g = gear || {};
          window.__draws.push({paint: g.paint, topper: g.topper, wheels: g.wheels,
                               trail: g.trail, pet: g.pet, glow: g.glow,
                               world: g.world, dance: g.dance, horn: g.horn,
                               art: (g.art || '').length, nomast: !!g.nomast});
          return window.__origDrawRover.apply(this, arguments);
        };
      }
      return typeof window.__origDrawRover;
    """)


def tab_items(driver):
    return driver.js("""
      return [...document.querySelectorAll('#garageShelf .card')].map(c => ({
        slot: c.dataset.slot, key: c.dataset.key,
        open: !c.classList.contains('locked'),
        name: (c.querySelector('.cname') || {}).textContent || '',
        tier: (c.querySelector('.tier') || {}).textContent || '',
        title: c.title || ''}));
    """)


def choose(driver, slot, key, timeout=6):
    done = driver.js("""
      window.__chosen = false;
      const slot = arguments[0], key = arguments[1];
      const c = [...document.querySelectorAll('#garageShelf .card')]
        .find(x => x.dataset.slot === slot && x.dataset.key === key);
      if (!c) return 'missing';
      c.click();
      return 'clicked';
    """, slot, key)
    if done != "clicked":
        return False, done
    ok = wait_js(driver, "return look[arguments[0]] === arguments[1]",
                 timeout, 0.03, slot, key)
    return ok, done


def every_item(driver, width, height):
    print("\n-- every unlocked item, preview and map --")
    open_garage(driver)
    collect(driver, "garage-open")
    fits(driver, "#garage .garage-card", "garage card", width, height)
    fits(driver, "#garage .garage-head", "garage header", width, height)
    fits(driver, "#garage .stage", "garage stage", width, height)
    check(box(driver, "#garage .garage-card")["scrollW"]
          <= box(driver, "#garage .garage-card")["clientW"] + 1,
          "garage has no sideways scroll")
    tabs = driver.js("return [...document.querySelectorAll('#garageTabs .tab')].map(b => b.dataset.tab)")
    check(len(tabs) >= 10, f"{len(tabs)} garage tabs")
    seen, drawn, missed = set(), 0, []
    errors_before = len(ERRORS)
    for tab in tabs:
        driver.js("document.querySelector('#garageTabs .tab[data-tab=' + JSON.stringify(arguments[0]) + ']').click()", tab)
        time.sleep(0.15)
        check(driver.js("return document.querySelector('.garage-card').scrollTop") == 0,
              f"{tab} tab opens at the top")
        shot(driver, f"garage-{tab}-{width}")
        items = tab_items(driver)
        if tab == "badges":
            check(all(i["title"] for i in items[:3]) or bool(items), "badge cabinet draws")
            continue
        check(len(items) > 0, f"{tab} tab has cards")
        for item in items:
            if not item["open"] or (item["slot"], item["key"]) in seen:
                continue
            seen.add((item["slot"], item["key"]))
            ok, why = choose(driver, item["slot"], item["key"])
            if not ok:
                missed.append((item["slot"], item["key"], why))
                continue
            driver.js("window.__draws = []; window.garagePreview(1000); render(0);")
            drawn += 1
            calls = driver.js("return window.__draws")
            if not any(call.get(item["slot"]) == item["key"] for call in calls):
                missed.append((item["slot"], item["key"], "not drawn"))
            if drawn % 25 == 0:
                collect(driver, f"{tab}-items")
    check(not missed, f"{drawn} unlocked items tried on and drawn"
          + (f" (missed: {missed[:4]})" if missed else ""))
    check(len(seen) >= 200, f"{len(seen)} unique items visited")
    check(len(ERRORS) == errors_before, "no console errors while trying items")
    shot(driver, f"garage-after-all-items-{width}")
    driver.js("document.getElementById('garageClose').click()")
    time.sleep(0.1)


def locked_items(driver, base, pid, width):
    print("\n-- locked items on a brand-new student --")
    open_student(driver, base, pid)
    open_garage(driver)
    before = driver.js("return JSON.stringify(look)")
    tabs = driver.js("return [...document.querySelectorAll('#garageTabs .tab')].map(b => b.dataset.tab)")
    missing, clicked = [], 0
    for tab in tabs:
        driver.js("document.querySelector('#garageTabs .tab[data-tab=' + JSON.stringify(arguments[0]) + ']').click()", tab)
        time.sleep(0.1)
        items = tab_items(driver)
        for item in items:
            if item["open"]:
                continue
            if not item["title"] or not item["tier"] or "undefined" in item["title"] + item["tier"]:
                missing.append((tab, item["slot"], item["key"]))
            driver.js("""
              const c=[...document.querySelectorAll('#garageShelf .card')]
                .find(x=>x.dataset.slot===arguments[0]&&x.dataset.key===arguments[1]);
              if (c && c.dataset.key !== 'mine') c.click();
            """, item["slot"], item["key"])
            clicked += 1
        collect(driver, f"locked-{tab}")
    after = driver.js("return JSON.stringify(look)")
    check(not missing, f"every locked card says how to get it ({clicked} checked)"
          + (f" (missing: {missing[:4]})" if missing else ""))
    check(before == after, "clicking locked items changes nothing")
    driver.js("document.querySelector('#garageTabs .tab[data-tab=paint]').click()")
    time.sleep(0.1)
    check(driver.exists("#garageShelf .card.locked[data-key=mine]"),
          "the brand-new student's Paint Shop card is locked")
    driver.js("const c=document.querySelector('#garageShelf .card.locked[data-key=mine]'); if(c)c.click();")
    check(wait_js(driver, "return !document.getElementById('paintShop').hidden", 5),
          "the locked Paint Shop card opens the Paint Shop")
    driver.js("document.getElementById('shopBack').click()")
    shot(driver, f"garage-locked-{width}")


def surprise_and_presets(driver, width):
    print("\n-- Surprise me and saved looks --")
    open_garage(driver)
    opens = driver.js("""
      const by = {};
      for (const i of state.garage) if (i.open) (by[i.slot] = by[i.slot] || []).push(i.key);
      return by;
    """)
    missing = []
    for n in range(12):
        driver.click("#surpriseButton")
        time.sleep(0.18)
        got = driver.js("return look")
        for slot, keys in opens.items():
            if got.get(slot) not in keys:
                missing.append((n, slot, got.get(slot)))
        if n % 4 == 0:
            collect(driver, "surprise")
    check(not missing, "Surprise me always picks an unlocked item"
          + (f" (bad: {missing[:4]})" if missing else ""))
    shot(driver, f"garage-surprise-{width}")

    # Four clearly different looks.
    looks = [
        {"paint": "galaxy", "topper": "party", "wheels": "std", "trail": "hearts",
         "world": "moon", "dance": "spin", "glow": "noglow", "pet": "nopet", "horn": "beep"},
        {"paint": "lava", "topper": "crown", "wheels": "treads", "trail": "fire",
         "world": "volcano", "dance": "flip", "glow": "rainbowglow", "pet": "dragon", "horn": "roar"},
        {"paint": "rgb", "topper": "shades", "wheels": "portalwheels", "trail": "clones",
         "world": "space", "dance": "disco", "glow": "blackhole", "pet": "lovity", "horn": "boom"},
        {"paint": "mine", "topper": "none", "wheels": "sneakers", "trail": "notes",
         "world": "candy", "dance": "floss", "glow": "jacko", "pet": "bunny", "horn": "quack"},
    ]
    for n, look in enumerate(looks):
        for slot, key in look.items():
            driver.js("return chooseLook(arguments[0], arguments[1])", slot, key)
            time.sleep(0.05)
        time.sleep(0.1)
        if driver.js("return !!document.querySelector('#presets .preset.empty[data-save=\"' + arguments[0] + '\"]')", n):
            driver.js("document.querySelector('#presets .preset.empty[data-save=\"' + arguments[0] + '\"]').click()", n)
            time.sleep(0.18)
    presets = driver.js("return state.presets.map(p => p && p.paint)")
    check(sum(1 for p in presets if p) == 4, f"four looks saved ({presets})")
    shot(driver, f"garage-presets-{width}")
    # Put one back on, then empty them all.
    driver.js("document.querySelector('#presets .preset.full[data-wear=\"1\"]').click()")
    time.sleep(0.25)
    check(driver.js("return look.paint") == "lava", "a saved look puts its paint back on")
    cleared = 0
    while cleared < 4 and driver.js("return !!document.querySelector('#presets .preset.full')"):
        driver.js("const c=document.querySelector('#presets .preset.full .clear'); if(c)c.click();")
        time.sleep(0.15)
        cleared += 1
    check(driver.js("return state.presets.every(p => p == null)"), "all four saved looks can be emptied")


def rover_name(driver):
    print("\n-- the rover name box --")
    original = driver.js("return state.rover_name || ''")
    def set_name(value):
        driver.js("""
          const el = document.getElementById('roverName');
          el.value = arguments[0];
          el.dispatchEvent(new Event('change', {bubbles: true}));
        """, value)
        time.sleep(0.25)
        return driver.js("return {input: document.getElementById('roverName').value,"
                         " saved: state.rover_name || ''}")
    long = set_name("Super Duper Rover 9000")
    check(len(long["saved"]) <= 14 and long["input"] == long["saved"],
          f"a long name is cut to 14 characters ({long['saved']!r})")
    emoji = set_name("🚀Rex🐍")
    check(emoji["saved"] == "Rex", f"emoji are left out of the tag ({emoji['saved']!r})")
    empty = set_name("")
    check(empty["saved"] == "" and empty["input"] == "",
          "an empty name is allowed and does not break the garage")
    set_name(original)
    collect(driver, "rover-name")


def paint_cards_not_covered(driver):
    """The paint cards and shop preview must show the paint, not the hat."""
    print("\n-- a hat must not hide the paint --")
    driver.js("return chooseLook('topper', 'beret')")
    time.sleep(0.12)
    driver.js("return chooseLook('paint', 'galaxy')")
    time.sleep(0.12)
    driver.js("document.querySelector('#garageTabs .tab[data-tab=paint]').click()")
    time.sleep(0.15)
    result = driver.js("""
      const orig = window.drawRover;
      let seen = null;
      window.drawRover = function (ctx, x, y, s, angle, alpha, gear, now) {
        if (!seen && gear && gear.paint === 'galaxy') seen = gear;
        return orig.apply(this, arguments);
      };
      const cv = document.createElement('canvas');
      thumb(cv, 'paint', 'galaxy');
      window.drawRover = orig;
      return seen && {topper: seen.topper, wheels: seen.wheels};
    """)
    check(result and result["topper"] == "none",
          "a paint card leaves the hat off, so the paint shows")
    # The same for the Paint Shop's rover preview.
    driver.click("#shopDoor")
    driver.wait("return !document.getElementById('paintShop').hidden", 10, "the Paint Shop")
    time.sleep(0.4)
    shop_gear = driver.js("""
      const orig = window.drawRover;
      let seen = null;
      window.drawRover = function (ctx, x, y, s, angle, alpha, gear, now) {
        if (!seen && gear && gear.paint === 'mine') seen = gear;
        return orig.apply(this, arguments);
      };
      drawShop(performance.now());
      window.drawRover = orig;
      return seen && {topper: seen.topper, art: (seen.art || '').length};
    """)
    check(shop_gear and shop_gear["topper"] == "none",
          "the Paint Shop rover preview leaves the hat off, so the paint shows")
    driver.click("#shopBack")
    driver.wait("return !document.getElementById('garage').hidden", 10, "the garage")


def paint_shop(driver, width, height):
    print("\n-- the Paint Shop --")
    open_garage(driver)
    driver.js("document.querySelector('#garageTabs .tab[data-tab=paint]').click()")
    driver.click("#shopDoor")
    driver.wait("return !document.getElementById('paintShop').hidden", 10, "the Paint Shop")
    time.sleep(0.4)
    check(not driver.js("return document.getElementById('paintShop').hidden"), "the Paint Shop opens")
    fits(driver, ".shop-card", "Paint Shop card", width, height)
    fits(driver, "#shopWear", "Wear it button", width, height)
    shot(driver, "paint-shop-open")

    def shop_state():
        return driver.js("return {error: document.getElementById('shopMsg').innerText,"
                         " cls: document.getElementById('shopMsg').className,"
                         " painted: painted(shop.art), wear: document.getElementById('shopWear').disabled,"
                         " line: shop.errorLine, anim: !!shop.anim,"
                         " code: document.getElementById('shopCode').value}")

    def set_code(code, want=None, timeout=6):
        driver.js("""
          const t = document.getElementById('shopCode');
          t.value = arguments[0];
          t.dispatchEvent(new Event('input', {bubbles: true}));
        """, code)
        end = time.time() + timeout
        out = shop_state()
        while time.time() < end:
            out = shop_state()
            if out["code"] == code and not out["anim"] and (want is None or want in out["error"]):
                break
            time.sleep(0.08)
        time.sleep(0.1)
        return shop_state()

    # Click a square: the page writes the matching paint() line.
    driver.js("""
      const box = easelBox(), r = box.cv.getBoundingClientRect();
      box.cv.dispatchEvent(new MouseEvent('click', {bubbles: true,
        clientX: r.left + box.left + 9.5 * box.cell,
        clientY: r.top + box.top + 6.5 * box.cell}));
    """)
    time.sleep(0.6)
    check("paint(10, 7, \"red\")" in driver.js("return document.getElementById('shopCode').value"),
          "clicking square 10,7 writes paint(10, 7, \"red\")")

    for index, expected in enumerate((1, 10, 70, 70, 70, 70)):
        name = driver.js("return document.querySelectorAll('#shopExamples button')[arguments[0]].textContent", index)
        driver.js("document.querySelectorAll('#shopExamples button')[arguments[0]].click()", index)
        end = time.time() + 6
        out = {"painted": 0, "line": 1}
        while time.time() < end:
            out = shop_state()
            if out["painted"] == expected and not out["line"]:
                break
            time.sleep(0.08)
        check(out["painted"] == expected and not out["line"], f"example {name!r} paints")
    shot(driver, "paint-shop-checkers")

    cases = [
        ('paint(0, 1, "red")\n', "off the rover"),
        ('paint(1, 1, red)\n', "Put quotes round colours"),
        ('paint(1, 1, "glitter")\n', "isn't one of the paints"),
        ('fill("navy"\n', "opens a bracket"),
        ('while True:\n    paint(1, 1, "red")\n', "ran too long"),
    ]
    for code, want in cases:
        out = set_code(code, want)
        check(want in out["error"] and out["wear"],
              f"broken code says {want!r}")
    line = driver.js("""
      const bar = document.querySelector('#shopPaint .err-line');
      return {exists: !!bar, parentZ: bar && getComputedStyle(bar.parentElement).zIndex,
              bg: bar && getComputedStyle(bar).backgroundColor};
    """)
    check(line["exists"] and line["parentZ"] == "0" and "rgba(0, 0, 0, 0)" not in str(line["bg"]),
          "the paint error line has a visible stacking context")
    shot(driver, "paint-shop-error")

    checker = ('fill("navy")\nfor y in range(1, 8):\n'
               '    for x in range(1, 11):\n'
               '        if (x + y) % 2 == 0:\n            paint(x, y, "gold")\n')
    out = set_code(checker, "70 of 70")
    check(not out["cls"].endswith("err") and out["painted"] == 70,
          "a checker loop paints all 70 squares")
    driver.click("#shopRun")
    wait_js(driver, "return !shop.anim && painted(shop.shown) === 70", 6)
    check(driver.js("return painted(shop.shown)") == 70, "Paint animates to the finished painting")
    shot(driver, "paint-shop-worn-before")
    driver.click("#shopWear")
    time.sleep(0.8)
    worn = driver.js("return {paint: look.paint, art: (look.art || '').length,"
                     " mine: (state.garage.find(i => i.key === 'mine') || {}).open}")
    check(worn["paint"] == "mine" and worn["art"] == 70 and worn["mine"] is True,
          "Wear it puts the painting on the rover and opens My paint")
    shot(driver, "paint-shop-worn")
    collect(driver, "paint-shop")
    driver.js("document.getElementById('shopBack').click()")
    driver.wait("return !document.getElementById('garage').hidden", 10, "the garage")
    mine = driver.js("""
      const c = [...document.querySelectorAll('#garageShelf .card')].find(x => x.dataset.key === 'mine');
      return c && {open: !c.classList.contains('locked'), on: c.classList.contains('on')};
    """)
    check(bool(mine and mine["open"] and mine["on"]), "My paint is open and ON after wearing it")


def map_and_show(driver, base, pid):
    print("\n-- the map and the class screen --")
    driver.js("render(0)")
    map_ok = driver.js("""
      const cv = document.getElementById('map');
      const g = cv.getContext('2d'), d = g.getImageData(0, 0, cv.width, cv.height).data;
      let n = 0; for (let i = 3; i < d.length; i += 4) if (d[i]) n++;
      return n > cv.width * cv.height * 0.05;
    """)
    check(map_ok, "the map canvas draws the rover and ground")
    shot(driver, "map-with-paint")
    http(base, f"/planet/ping?id={pid}&busy=1")
    show = wd.new(1366, 768)
    try:
        show.go(base + "/planet/show")
        selector = "#ships .ship[data-id=" + json.dumps(pid) + "]"
        wait_js(show, "return !!document.querySelector(arguments[0])", 20, 0.05, selector)
        check(show.exists(selector), "the class screen has the student's card")
        shot(show, "class-show")
        collect(show, "class-show")
    finally:
        show.close()


def calm(driver, base, pid):
    print("\n-- calm mode --")
    open_student(driver, base, pid, calm=True)
    check(driver.js("return CALM") is True, "calm mode is on")
    open_garage(driver)
    driver.js("document.querySelector('#garageTabs .tab[data-tab=topper]').click()")
    time.sleep(0.1)
    driver.js("const c=[...document.querySelectorAll('#garageShelf .card')].find(x=>x.dataset.slot==='topper'&&x.dataset.key==='propeller'); if(c)c.click();")
    time.sleep(0.25)
    first = driver.js("return document.getElementById('garageScene').toDataURL()")
    time.sleep(0.45)
    second = driver.js("return document.getElementById('garageScene').toDataURL()")
    check(first == second, "the garage preview does not move in calm mode")
    driver.js("document.querySelector('#garageTabs .tab[data-tab=paint]').click()")
    driver.click("#shopDoor")
    driver.wait("return !document.getElementById('paintShop').hidden", 10, "the Paint Shop")
    time.sleep(0.4)
    check(driver.js("return !shop.anim") is True, "Paint does not animate in calm mode")
    shot(driver, "calm-paint-shop")
    collect(driver, "calm")


def late_toast(base, pid):
    print("\n-- the late new-levels toast --")
    opened = wd.new(1366, 768)
    try:
        opened.go(base + "/planet")
        opened.js("localStorage.setItem('mazeId', arguments[0]);"
                  "localStorage.setItem('planetIntroSeen', '1');"
                  "localStorage.removeItem('planetVoyage:' + arguments[0]);", pid)
        opened.go(base + "/planet")
        opened.wait("return !!document.getElementById('app') && !document.getElementById('app').hidden", 30, "the planet page")
        if not opened.js("return !!voyageNext()"):
            print("  ok  (no voyage level left; the new-levels toast check is skipped)")
            return
        opened.click("#starsButton")
        time.sleep(2.3)
        texts = opened.js("return [...document.querySelectorAll('#toasts .toast')].map(t => t.innerText)")
        check(not any("New levels have landed" in text for text in texts),
              "the new-levels toast stays off an open garage")
        shot(opened, "garage-early-no-toast")
    finally:
        opened.close()

    normal = wd.new(1366, 768)
    try:
        normal.go(base + "/planet")
        normal.js("localStorage.setItem('mazeId', arguments[0]);"
                  "localStorage.setItem('planetIntroSeen', '1');"
                  "localStorage.removeItem('planetVoyage:' + arguments[0]);", pid)
        normal.go(base + "/planet")
        normal.wait("return !!document.getElementById('app') && !document.getElementById('app').hidden", 30, "the planet page")
        time.sleep(2.1)
        texts = normal.js("return [...document.querySelectorAll('#toasts .toast')].map(t => t.innerText)")
        check(any("New levels have landed" in text for text in texts),
              "the new-levels toast still appears on the map")
    finally:
        normal.close()


def scroll_reset(driver):
    print("\n-- Done and reopen, and tab switches --")
    open_garage(driver)
    driver.js("const c=document.querySelector('.garage-card'); c.scrollTop=c.scrollHeight;")
    time.sleep(0.1)
    check(driver.js("return document.querySelector('.garage-card').scrollTop") > 0,
          "the Paint shelf can scroll down")
    driver.js("document.querySelector('#garageTabs .tab[data-tab=topper]').click()")
    time.sleep(0.15)
    check(driver.js("return document.querySelector('.garage-card').scrollTop") == 0,
          "switching tabs starts the new shelf at the top")
    driver.js("const c=document.querySelector('.garage-card'); c.scrollTop=c.scrollHeight;")
    time.sleep(0.1)
    driver.click("#garageClose")
    time.sleep(0.1)
    open_garage(driver)
    check(driver.js("return document.querySelector('.garage-card').scrollTop") == 0,
          "Done and reopen starts at the top")


def layout_at(base, pid, width, height):
    print(f"\n-- layout at {width}x{height} --")
    driver = wd.new(width, height)
    try:
        open_student(driver, base, pid)
        open_garage(driver)
        fits(driver, "#garage .garage-card", "garage card", width, height)
        fits(driver, "#garage .garage-head", "garage header", width, height)
        fits(driver, "#garage .stage", "garage stage", width, height)
        fits(driver, "#garageClose", "Done button", width, height)
        fits(driver, "#surpriseButton", "Surprise me button", width, height)
        check(driver.js("return document.documentElement.scrollWidth") <= width + 1,
              "the page does not scroll sideways")
        driver.js("document.querySelector('#garageTabs .tab[data-tab=paint]').click()")
        driver.click("#shopDoor")
        driver.wait("return !document.getElementById('paintShop').hidden", 10, "the Paint Shop")
        time.sleep(0.3)
        fits(driver, ".shop-card", "Paint Shop card", width, height)
        fits(driver, "#shopWear", "Wear it button", width, height)
        fits(driver, "#shopRun", "Paint button", width, height)
        check(driver.js("return document.documentElement.scrollWidth") <= width + 1,
              "the Paint Shop does not scroll sideways")
        shot(driver, f"layout-{width}")
        collect(driver, "layout")
    finally:
        driver.close()


def main():
    global SHOTS
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--base", help="use this running server instead of starting one")
    parser.add_argument("--student", default="p0", help="the student with every item (default p0)")
    parser.add_argument("--new-student", default="p11", help="a brand-new student (default p11)")
    parser.add_argument("--shots", help="where to save screenshots")
    args = parser.parse_args()

    SHOTS = args.shots or tempfile.mkdtemp(prefix="planet-garage-shots-")
    os.makedirs(SHOTS, exist_ok=True)
    print("screenshots: " + SHOTS)

    folder = None
    proc = log = None
    try:
        if args.base:
            base, student, new_student = args.base.rstrip("/"), args.student, args.new_student
            if not wait_server(base):
                raise SystemExit("no server at " + base)
        else:
            folder = tempfile.mkdtemp(prefix="planet-garage-e2e-")
            base, proc, log, student, new_student = prepare_state(folder)
        print(f"server: {base}  student: {student}  new: {new_student}")
        state = http(base, f"/planet/state?id={student}")
        check(len(state["garage"]) > 0, f"the student has {len(state['garage'])} garage items")
        check(sum(1 for i in state["garage"] if i["open"]) >= 200,
              f"{sum(1 for i in state['garage'] if i['open'])} of them are unlocked")

        for width, height in ((1366, 768), (1280, 720)):
            driver = wd.new(width, height)
            try:
                open_student(driver, base, student)
                patch_rover(driver)
                every_item(driver, width, height)
                scroll_reset(driver)
                surprise_and_presets(driver, width)
                rover_name(driver)
                paint_cards_not_covered(driver)
                paint_shop(driver, width, height)
                map_and_show(driver, base, student)
                calm(driver, base, student)
                collect(driver, f"page-{width}")
            finally:
                driver.close()
            layout_at(base, student, width, height)

        new = wd.new(1366, 768)
        try:
            locked_items(new, base, new_student, 1366)
        finally:
            new.close()
        late_toast(base, student)
        check(not ERRORS, "no console errors through the whole run"
              + (f" (first: {ERRORS[0]})" if ERRORS else ""))
    finally:
        if not args.base and folder:
            stop_server(proc, log)
            shutil.rmtree(folder, ignore_errors=True)

    print("\n" + ("ALL CHECKS PASSED" if not PROBLEMS else f"{len(PROBLEMS)} CHECK(S) FAILED:"))
    for problem in PROBLEMS:
        print("  - " + problem)
    return 0 if not PROBLEMS else 1


if __name__ == "__main__":
    sys.exit(main())
