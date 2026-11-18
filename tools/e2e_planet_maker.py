#!/usr/bin/env python3
"""Real-browser bug hunt for the two student parts nobody tested tonight:

  * the Class Workshop: build, beat and publish a level, then a classmate
    finds it, plays it, wins and loses, and the maker hears who beat it;
  * Star Voyage: v1, then the first level of each of the other three zones.

It drives Chromium through tools/wd.py, talks to the same server the class
uses and starts its own on port 8797 (with a fresh state file) unless
PLANET_E2E_BASE says a server is already running.

    python3 tools/e2e_planet_maker.py

It is a tool, not a unit test: it prints each check and exits 1 on the first
miss. Screenshots land in tools/shots/e2e_*.png. Only its own server process
is stopped, never one it did not start.
"""
import json
import os
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import wd  # noqa: E402  (the local headless-Chromium helper)

PORT = int(os.environ.get("PLANET_E2E_PORT", "8797"))
BASE = os.environ.get("PLANET_E2E_BASE") or f"http://127.0.0.1:{PORT}"
ADMIN = os.environ.get("PLANET_E2E_ADMIN", "0106")
SHOTS = os.path.join(ROOT, "tools", "shots")
os.makedirs(SHOTS, exist_ok=True)

drivers = []
severe = []


# ---- small helpers -------------------------------------------------------------------------
def check(ok, what):
    print(("  ok  " if ok else "  FAIL ") + what)
    if not ok:
        raise AssertionError(what)


def post(path, data):
    request = urllib.request.Request(
        BASE + path, json.dumps(data).encode(), {"Content-Type": "application/json"})
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read())


def get(path):
    with urllib.request.urlopen(BASE + path, timeout=30) as response:
        return json.loads(response.read())


def admin(action, **data):
    return post("/admin", dict(key=ADMIN, action=action, **data))


def join(name):
    return post("/join", {"name": name})["id"]


def workshop_sites(pid):
    state = get(f"/planet/state?id={pid}")
    return [s for z in state["zones"] if z.get("workshop") for s in z["sites"]]


def shot(d, name):
    path = os.path.join(SHOTS, f"e2e_{name}.png")
    d.shot(path)
    print(f"  shot {os.path.relpath(path, ROOT)}")


def logs(d, where):
    for entry in d.logs():
        if entry.get("level") in ("SEVERE", "ERROR"):
            severe.append(f"{where}: {entry.get('message')}")


def set_value(d, css, text):
    """Type into a field. Used for emoji too: ChromeDriver's sendKeys only
    takes BMP characters, while a child's keyboard can type a rocket."""
    d.js("const el=document.querySelector(arguments[0]);"
         "el.value=arguments[1]; el.dispatchEvent(new Event('input',{bubbles:true}));",
         css, text)


def resize(d, width, height):
    try:
        d.request("POST", f"/session/{d.sid}/window/rect",
                  {"width": width, "height": height})
    except wd.WebDriverError:
        pass
    try:
        d.request("POST", f"/session/{d.sid}/goog/cdp/execute",
                  {"cmd": "Emulation.setDeviceMetricsOverride",
                   "params": {"width": width, "height": height,
                              "deviceScaleFactor": 1, "mobile": False}})
    except wd.WebDriverError:
        pass


def page_fits(d):
    return d.js("return document.documentElement.scrollWidth <= innerWidth + 1")


def student(name, width=1366, height=768, intro_seen=True):
    pid = join(name)
    d = wd.new(width, height)
    drivers.append(d)
    d.go(BASE + "/planet")
    keys = [f"localStorage.setItem('mazeId',{json.dumps(pid)})",
            "localStorage.setItem('planetCalm','1')"]
    if intro_seen:
        keys.append("localStorage.setItem('planetIntroSeen','1')")
    d.js("localStorage.clear();" + ";".join(keys) + ";")
    d.go(BASE + "/planet")
    d.wait("return !document.getElementById('app').hidden", 20, f"{name}'s page")
    d.wait("return !!state && !!site", 20, f"{name}'s first level")
    time.sleep(.4)
    logs(d, f"{name} open")
    return pid, d


def open_levels(d):
    if not d.js("return document.getElementById('maker').hidden"):
        d.click("#makerClose")
        time.sleep(.2)
    d.click("#levelsButton")
    d.wait("return !document.getElementById('levels').hidden", 5, "Levels")
    time.sleep(.25)


def close_levels(d):
    if not d.js("return document.getElementById('levels').hidden"):
        d.click("#levelsClose")
        time.sleep(.15)


def open_level(d, key):
    d.js("openSite(arguments[0])", key)
    d.wait(f"return site && site.key === '{key}'", 15, f"level {key}")
    time.sleep(.35)
    logs(d, f"open {key}")


def open_tile(d, zone, key):
    open_levels(d)
    card = f'.zone-card[data-zone="{zone}"]'
    if d.js("const c=document.querySelector(arguments[0]);"
            "return !!c && !c.classList.contains('open')", card):
        d.click(card + " .zone-top")
        time.sleep(.25)
    d.click(f'{card} .tile[data-key="{key}"]')
    d.wait(f"return site && site.key === '{key}'", 15, f"tile {key}")
    time.sleep(.35)
    logs(d, f"tile {key}")


def open_maker(d):
    open_levels(d)
    d.click("#levelsMake")
    d.wait("return !document.getElementById('maker').hidden", 5, "maker")
    time.sleep(.25)


def pick_tile(d, ch):
    d.click(f'#makerTools button[data-tile="{ch}"]')


def tap(d, row, col):
    # A native click on a square: the click handler added for keyboard users
    # paints it, while a mouse still paints on pointerdown.
    d.js("document.querySelector(`.mk[data-r='${arguments[0]}'][data-c='${arguments[1]}']`).click()",
         row, col)


def fill(d, ch):
    pick_tile(d, ch)
    d.js("for (let i=0;i<96;i++) document.querySelectorAll('.mk')[i].click();")


def save_maker(d, name, expect_error=None):
    set_value(d, "#makerName", name)
    d.click("#makerTest")
    d.wait("return document.getElementById('maker').hidden ||"
           "document.getElementById('makerWhy').classList.contains('bad')", 10, "maker answer")
    time.sleep(.25)
    hidden = d.js("return document.getElementById('maker').hidden")
    why = d.text("#makerWhy")
    if expect_error:
        check(not hidden and expect_error in why, f"maker says: {why!r}")
        logs(d, f"maker error {name!r}")
        return None
    check(hidden, f"level {name!r} saved (reason was {why!r})")
    d.wait("return !!site && !!site.key", 15, "new level page")
    time.sleep(.35)
    logs(d, f"save {name!r}")
    return d.js("return site.key")


def run_code(d, code, win=None, timeout=45):
    """Transmit code. win=True waits for the card, win=False waits for the
    replay to end and the rover to say what happened. Returns the banner."""
    set_value(d, "#code", code)
    d.click("#runButton")
    if win is True:
        d.wait("return !document.getElementById('celebrate').hidden", timeout, "win card")
        time.sleep(.25)
        logs(d, "win")
        return True
    end_states = ("['Stopped','Line to fix','Fell','Out of time','Flat battery',"
                  "'Wrong number','Wrong count','Spooked!','Beacon reached',"
                  "'Picture painted','Report confirmed','Crashed']")
    d.wait("return !document.getElementById('runButton').disabled &&"
           f" {end_states}.includes(document.getElementById('status').innerText)",
           timeout, "run end")
    time.sleep(.2)
    logs(d, "run end")
    return d.text("#banner")


def win_info(d):
    return {
        "sub": d.text("#celeSub"),
        "note": d.text("#celeNote"),
        "actions": d.text("#celeActions"),
        "stars": d.js("return site.stars"),
        "total": d.js("return state.total_stars"),
    }


def as_maker(d, key, code):
    run_code(d, code, win=True)
    info = win_info(d)
    check("It's live!" in info["note"], f"{key} published: {info['note']!r}")
    check(info["total"] == 0, f"{key} earns no class stars")


# ---- server ---------------------------------------------------------------------------------
def start_server():
    if os.environ.get("PLANET_E2E_BASE"):
        print(f"using the server at {BASE}")
        return None
    with socket.socket() as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            sock.bind(("127.0.0.1", PORT))
        except OSError:
            raise SystemExit(f"port {PORT} is already in use; stop that server or set PLANET_E2E_BASE")
    state = os.environ.get("PLANET_E2E_STATE", f"/tmp/planet-e2e-{os.getpid()}.json")
    if os.path.exists(state):
        os.remove(state)
    log_path = os.path.join(SHOTS, "e2e_server.log")
    log = open(log_path, "w")
    env = dict(os.environ, MAZE_PORT=str(PORT), MAZE_STATE_FILE=state)
    proc = subprocess.Popen([sys.executable, "server.py"], cwd=ROOT, env=env,
                            stdout=log, stderr=subprocess.STDOUT)
    for _ in range(150):
        if proc.poll() is not None:
            log.close()
            raise SystemExit(f"server did not start; see {log_path}")
        try:
            urllib.request.urlopen(BASE + "/planet", timeout=1).read()
            print(f"started server on {BASE} (pid {proc.pid})")
            return proc, log, state
        except Exception:
            time.sleep(.1)
    proc.terminate()
    log.close()
    raise SystemExit(f"server did not answer; see {log_path}")


# ---- the hunt -------------------------------------------------------------------------------
def main():
    started = start_server()
    proc, log, state = started if started else (None, None, None)
    try:
        print("classroom: easy mode + students can make levels")
        admin("planet_easy", on=True)
        admin("planet_maker", on=True)
        for name in ("Ada", "Bo", "Cleo"):
            print(f"  joined {name}: {join(name)}")
        ada, a = student("Ada")
        bo, b = student("Bo")
        cleo, c = student("Cleo", 1280, 720, intro_seen=False)

        # A brand-new laptop gets the intro; Cleo keeps it open until there are
        # levels to announce, then closes it. Those announcements used to be
        # skipped for ever on a first visit.
        check(a.js("return document.getElementById('intro').hidden"),
              "returning student Ada does not get the intro again")
        check(c.js("return !document.getElementById('intro').hidden"), "new student Cleo gets the intro")

        print("\nAda builds levels the way a child would")
        check(workshop_sites(ada) == [], "Class Workshop is empty before anything is made")
        open_levels(a)
        shot(a, "02_ada_empty_levels")
        close_levels(a)

        # all walls: the start is covered up, so this must not save
        open_maker(a)
        fill(a, "#")
        shot(a, "03_maker_all_walls")
        save_maker(a, "all walls", expect_error="needs one 🚙 start")
        a.click("#makerClose")
        check(workshop_sites(ada) == [], "an all-wall drawing did not make a level")

        # tiny level, named moo
        open_maker(a)
        pick_tile(a, "G")
        tap(a, 0, 1)
        key_moo = save_maker(a, "moo")
        check(a.js("return site.name") == "moo", "moo opens on its own page")
        check("Now beat your own level" in a.text("#banner"),
              "the maker is told to beat it before the class can play")
        check(not any(s["key"] == key_moo for s in workshop_sites(bo)),
              "a classmate cannot see moo before its maker beats it")
        shot(a, "04_moo_unpublished")
        as_maker(a, key_moo, "east()\n")
        check(any(s["key"] == key_moo for s in workshop_sites(bo)),
              "moo is live for the class after the maker's win")
        check(get(f"/planet/site?id={ada}&site={key_moo}")["code"] == "east()\n",
              "the class level kept the maker's code on the server")
        shot(a, "05_moo_live")

        # no way to the beacon, with a name full of markup
        open_maker(a)
        pick_tile(a, "#")
        tap(a, 0, 1)
        tap(a, 1, 0)
        pick_tile(a, "G")
        tap(a, 0, 4)
        # A level nobody could beat isn't saved: the maker is told what's cut off.
        save_maker(a, 'My <b> & "cool"', expect_error="can't reach the 🛰 beacon")
        # Open a path past the rock, and it saves (still to be beaten by its maker).
        pick_tile(a, ".")
        tap(a, 0, 1)
        key_noway = save_maker(a, 'My <b> & "cool"')
        check(a.js("return site.name") == "My b cool", "markup is stripped from a level name")
        check(a.js("return !document.body.innerHTML.includes('&lt;b&gt;')"),
              "a level name is shown as text, never as markup")
        miss = run_code(a, "east()\nsouth()\n", win=False)
        check("beacon" in miss.lower(), f"an impossible level says what is missing: {miss[:80]!r}")
        check(not any(s["key"] == key_noway for s in workshop_sites(bo)),
              "a level nobody can beat never reaches the class")
        shot(a, "06_noway_miss")

        # delete it from the drawing board, with the two-step confirmation
        open_levels(a)
        a.click("#levelsMake")
        a.wait("return !document.getElementById('maker').hidden", 5, "maker")
        a.js("document.querySelector('#makerMine [data-drop=\"%s\"]').scrollIntoView({block:'center'})" % key_noway)
        time.sleep(.2)
        a.click(f'#makerMine [data-drop="{key_noway}"]')
        time.sleep(.2)
        check("Sure? Delete" in a.js("return document.querySelector('#makerMine [data-drop=\"%s\"]').innerText" % key_noway),
              "deleting asks first")
        a.click(f'#makerMine [data-drop="{key_noway}"]')
        a.wait("return !document.querySelector('#makerMine [data-drop=\"%s\"]')" % key_noway, 8, "level deleted")
        check(not any(s["key"] == key_noway for s in workshop_sites(ada)), "the level is gone")
        a.click("#makerClose")
        shot(a, "07_maker_deleted")

        # huge map, longest allowed name
        open_maker(a)
        pick_tile(a, "G")
        tap(a, 7, 11)
        key_long = save_maker(a, "W" * 24)
        check(a.js("return site.name") == "W" * 24, "a 24-letter name is kept")
        as_maker(a, key_long, "east(11)\nsouth(7)\n")
        open_levels(a)
        wrap = a.js("const t=document.querySelector('.tile[data-key=\"%s\"]');"
                    "const n=t.querySelector('.tname');"
                    "return [n.scrollWidth,n.clientWidth,t.scrollWidth,t.clientWidth]" % key_long)
        check(wrap[0] <= wrap[1] + 1 and wrap[2] <= wrap[3] + 1,
              f"a very long level name wraps inside its tile ({wrap})")
        shot(a, "08_long_name_tile")
        close_levels(a)

        # a rocket is a name to a 9-year-old
        open_maker(a)
        pick_tile(a, "G")
        tap(a, 0, 1)
        key_rocket = save_maker(a, "🚀")
        check(a.js("return site.name") == "🚀", "an emoji-only level name is allowed")
        as_maker(a, key_rocket, "east()\n")
        shot(a, "09_emoji_level")

        # a fourth level: the funniest name in last term's class
        open_maker(a)
        pick_tile(a, "G")
        tap(a, 0, 1)
        key_question = save_maker(a, "are you? yes")
        check(a.js("return site.name") == "are you? yes", "punctuation in a level name is kept")
        as_maker(a, key_question, "east()\n")
        shot(a, "09b_question_level")

        # the dialog still fits with four levels, and its delete buttons have words
        open_maker(a)
        box = a.js("const c=document.querySelector('.maker-card').getBoundingClientRect();"
                   "return [c.top,c.bottom,innerHeight]")
        check(box[1] <= box[2] + 1, f"the maker dialog fits the 1366x768 screen ({box})")
        labels = a.js("return [...document.querySelectorAll('#makerMine button')].map(b=>b.innerText)")
        check(any("Delete" in x for x in labels), "the delete buttons say Delete, not just 🗑")
        shot(a, "10_maker_full_1366")
        a.click("#makerClose")

        # now that levels are live, close the intro on Cleo's new laptop: the
        # Star Voyage and class-level announcements must not be lost for ever
        c.click("#introClose")
        c.wait("return [...document.querySelectorAll('#toasts .toast')]"
               ".some(t=>t.innerText.includes('New levels have landed'))", 8, "Star Voyage announcement")
        c.wait("return [...document.querySelectorAll('#toasts .toast')]"
               ".some(t=>t.innerText.includes('class made') || t.innerText.includes('made a level'))",
               8, "class-level announcement")
        c_toasts = c.js("return [...document.querySelectorAll('#toasts .toast')].map(t=>t.innerText)")
        check(any("New levels have landed" in t for t in c_toasts),
              "Star Voyage is announced after the intro")
        check(any("class made" in t or "made a level" in t for t in c_toasts),
              "class levels are announced after the intro")
        shot(c, "01_intro_announcements")
        logs(c, "intro")

        print("\nBo finds and plays the class levels")
        b.wait("return [...document.querySelectorAll('#toasts .toast')]"
              ".some(t=>t.innerText.includes('class made') || t.innerText.includes('made a level'))",
              15, "Bo's new-level toast")
        b_toasts = b.js("return [...document.querySelectorAll('#toasts .toast')].map(t=>t.innerText)")
        check(any("class made" in t or "made a level" in t for t in b_toasts),
              f"Bo hears about the new levels ({b_toasts})")
        shot(b, "11_bo_new_level_toast")
        open_levels(b)
        group = b.js("return document.querySelector('#zoneList .zone-group') ? "
                     "document.querySelector('#zoneList .zone-group').innerText : ''")
        check("MADE BY YOUR CLASS" in group, "the Class Workshop is the first group on Levels")
        check(b.js("return !!document.querySelector('.zone-card[data-zone=\"workshop\"]')"),
              "the Class Workshop card is there")
        check(b.js("return document.getElementById('levelsPip').hidden") is False,
              "the pink Levels count shows unseen class levels")
        check(b.js("return document.getElementById('levelsPip').textContent") == "4",
              "the count is the four levels Bo has not beaten (pip says %r)" % b.js("return document.getElementById('levelsPip').textContent"))
        shot(b, "12_bo_workshop")
        open_tile(b, "workshop", key_moo)
        shot(b, "13_bo_moo")
        miss = run_code(b, "north()\n", win=False)
        check("beacon" in miss.lower(), f"Bo's first try on moo misses: {miss[:70]!r}")
        shot(b, "14_bo_moo_miss")
        run_code(b, "east()\n", win=True)
        info = win_info(b)
        check("It's live!" not in info["note"], "only the maker is told a level went live")
        check(info["total"] == 0, "a class level does not add a class star")
        check("Another class level" in info["actions"], "Bo is offered another class level")
        shot(b, "15_bo_moo_won")
        b.click("#celeActions .go")
        b.wait(f"return site && site.key && site.key !== '{key_moo}'",
               15, "another class level")
        next_key = b.js("return site.key")
        check(next_key in (key_long, key_rocket, key_question),
              f"Another class level opens the next one ({next_key})")
        b.js("hideCelebrate()")

        # the maker is told who beat it, within a ping
        a.wait("return [...document.querySelectorAll('#toasts .toast')]"
               ".some(t=>t.innerText.includes('beat your level'))", 14, "maker's who-beat-it note")
        beat_note = a.js("return [...document.querySelectorAll('#toasts .toast')]"
                         ".map(t=>t.innerText).find(x=>x.includes('beat your level'))")
        check("Bo beat your level moo!" in beat_note, f"Ada is told who beat moo ({beat_note})")
        shot(a, "16_ada_beat_note")

        # NEW goes away and the count drops after a win
        open_levels(b)
        check(b.js("return document.getElementById('levelsPip').textContent") == "3",
              "the Levels count drops after Bo beats moo")
        moo_tile = b.js("return document.querySelector('.tile[data-key=\"%s\"]').innerText" % key_moo)
        check("NEW" not in moo_tile, "a beaten class level is no longer NEW")
        shot(b, "17_bo_levels_after")
        close_levels(b)

        # 1280x720: the maker's own-levels row is still on screen
        resize(a, 1280, 720)
        time.sleep(.5)
        open_maker(a)
        box = a.js("const c=document.querySelector('.maker-card').getBoundingClientRect();"
                   "return [c.top,c.bottom,innerHeight]")
        check(box[1] <= box[2] + 1, f"the maker dialog fits the 1280x720 screen ({box})")
        buttons = a.js("return [...document.querySelectorAll('#makerMine button')].map("
                       "b=>b.getBoundingClientRect().bottom)")
        check(all(y <= 720 for y in buttons), "every one of Ada's levels is reachable at 1280x720")
        shot(a, "18_maker_1280")
        a.click("#makerClose")
        resize(a, 1366, 768)

        print("\nCleo paints Star Voyage")
        check(c.js("return !document.getElementById('voyageButton').hidden"),
              "the New levels button is showing")
        check("New levels" in c.js("return document.getElementById('voyageButton').innerText"),
              "the New levels button has words, not just a rocket")
        check(page_fits(c), "the 1280x720 page does not scroll sideways")
        c.click("#voyageButton")
        c.wait("return site && site.key === 'v1'", 15, "v1")
        time.sleep(.4)
        check(c.js("return site.name") == "Rainbow Road", "New levels opens v1 Rainbow Road")
        shot(c, "19_cleo_v1")
        miss = run_code(c, "north()\n", win=False)
        check("dots still to paint" in miss and "sample" not in miss.lower(),
              f"a paint miss says dots, not samples ({miss[:90]!r})")
        end = c.js("return document.getElementById('status').innerText")
        check(end in ("Stopped", "Line to fix"), f"the run ended cleanly ({end})")
        shot(c, "20_cleo_v1_miss")
        run_code(c, "east(6)\n", win=True)
        info = win_info(c)
        check("+1 ★" in info["note"], f"v1 earns its star ({info['note']})")
        c.js("hideCelebrate()")
        shot(c, "21_cleo_v1_won")

        # first of Pattern Studio
        open_tile(c, "studio", "v7")
        check(c.js("return site.name") == "Stripes", "the first Pattern Studio level opens")
        miss = run_code(c, "east(3)\n", win=False)
        check("dots still to paint" in miss, f"v7's miss also says dots ({miss[:80]!r})")
        shot(c, "22_cleo_v7_miss")
        run_code(c, "south()\nfor i in range(2):\n    east(8)\n    south(2)\n    west(8)\n    south(2)\n", win=True)
        check(c.js("return JSON.stringify(site.stars)") == "[true,true,true]",
              "v7 earns all three stars from the loop")
        c.js("hideCelebrate()")
        shot(c, "23_cleo_v7_won")

        # first of Picture Zoo
        open_tile(c, "zoo", "v19")
        check(c.js("return site.name") == "Goldfish", "the first Picture Zoo level opens")
        run_code(c, "east(2)\n", win=False)
        shot(c, "24_cleo_v19_miss")
        run_code(c, "south()\nfor i in range(2):\n    east(7)\n    south()\n    west(7)\n    south()\neast(7)\n", win=True)
        check(c.js("return JSON.stringify(site.stars)") == "[true]", "v19 paints the goldfish")
        c.js("hideCelebrate()")
        shot(c, "25_cleo_v19_won")

        # first of Mystery Murals
        open_tile(c, "murals", "v13")
        check(c.js("return site.name") == "Paint Trail", "the first Mystery Murals level opens")
        run_code(c, "east(1)\n", win=False)
        shot(c, "26_cleo_v13_miss")
        run_code(c, 'while look("east") == "paint":\n    east()\n', win=True)
        check(c.js("return JSON.stringify(site.stars)") == "[true,true,true]",
              "v13 earns all three stars by looking for paint")
        c.js("hideCelebrate()")
        check(page_fits(c), "the mural page does not scroll sideways")
        shot(c, "27_cleo_v13_won")

        print("\nthe teacher removes a level and closes the workshop")
        before = [x["key"] for x in get("/planet/overview")["levels"]]
        check(key_long in before, "the teacher can see the long level")
        admin("planet_maker_remove", level=key_long)
        after = [x["key"] for x in get("/planet/overview")["levels"]]
        check(key_long not in after, "the teacher removed it")
        check(not any(s["key"] == key_long for s in workshop_sites(bo)),
              "the removed level is gone from Bo's Levels screen")
        admin("planet_maker", on=False)
        check(not any(z.get("workshop") for z in get(f"/planet/state?id={bo}")["zones"]),
              "closing the workshop hides it from students")
        admin("planet_maker", on=True)
        check(any(z.get("workshop") for z in get(f"/planet/state?id={bo}")["zones"]),
              "opening it again brings the kept levels back")

        print("\nconsole")
        # Every session is asked one last time; a closed session is fine.
        for d, name in ((a, "Ada"), (b, "Bo"), (c, "Cleo")):
            logs(d, f"{name} final")
        check(not severe, f"no console errors ({severe[:3]})")
        print("\nall browser checks passed")
        return 0
    finally:
        for d in drivers:
            try:
                d.close()
            except Exception:
                pass
        if proc:
            proc.terminate()
            try:
                proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                proc.kill()
            if log:
                log.close()
            if state and os.path.exists(state):
                try:
                    os.remove(state)
                except OSError:
                    pass
            print("stopped the server this tool started")


if __name__ == "__main__":
    try:
        sys.exit(main())
    except AssertionError as exc:
        print(f"\nFAILED: {exc}")
        sys.exit(1)
