#!/usr/bin/env python3
"""Play the Strange Planet student page like a kid in this class.

This is a tool, not a unittest: it drives headless Chromium through joining,
the practice parks (scout -> Use as code -> the typing coach -> Transmit),
the win card, the Levels map, the garage, a Star Voyage level, hints/help,
odd names, double presses and a reload mid-run. It takes screenshots and
fails (exit 1) on console errors, clipped dialogs or missing buttons.

Start a server first, for example:

    MAZE_PORT=8791 MAZE_STATE_FILE=/tmp/kidshunt-state.json python3 server.py
    python3 tools/e2e_planet_kids.py --base http://127.0.0.1:8791 \\
        --admin-key 0106 --easy --setup-workshop

Or let the tool start a fresh test server itself:

    python3 tools/e2e_planet_kids.py --start-server --easy --setup-workshop

Use --quick for a shorter run while changing the page.
"""
import argparse
import json
import os
import re
import subprocess
import sys
import time
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, ROOT)
import wd                       # noqa: E402
import planet                   # noqa: E402

PRACTICE = [("p1", "drive"), ("p2", "drive"), ("p3", "drive"), ("p8", "drive"),
            ("p9", "drive"), ("p13", "drive"), ("p17", "drive"),
            ("p25", "drive"), ("p31", "drive"),
            ("p39", "typed"), ("p47", "typed"), ("p52", "typed"),
            ("p58", "typed")]
QUICK = [("p1", "drive"), ("p8", "drive"), ("p17", "drive"),
         ("p31", "drive"), ("p39", "typed"), ("p52", "typed")]


def button_label(text):
    """The words on a button, without its leading icon."""
    return re.sub(r"^[^\w]+", "", text).strip()


# --------------------------------------------------------------------------
# Small HTTP helpers for setup only (the browser does the student playing).
# --------------------------------------------------------------------------
def base_url(s):
    return s.rstrip("/")


def post(url, data):
    req = urllib.request.Request(
        url, data=json.dumps(data).encode(),
        headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as f:
        return json.load(f)


def server_up(base):
    try:
        with urllib.request.urlopen(base + "/planet", timeout=2):
            return True
    except Exception:
        return False


def start_server(base, state_file, log_file):
    if server_up(base):
        raise SystemExit(f"{base} is already serving; pick a free port for --start-server")
    port = base.rsplit(":", 1)[-1] if ":" in base else "8791"
    env = dict(os.environ, MAZE_PORT=port, MAZE_STATE_FILE=state_file)
    log = open(log_file, "ab")
    proc = subprocess.Popen([sys.executable, "server.py"], cwd=ROOT, env=env,
                            stdout=log, stderr=log)
    for _ in range(240):
        if server_up(base):
            return proc
        if proc.poll() is not None:
            raise SystemExit(f"server exited; see {log_file}")
        time.sleep(.1)
    proc.terminate()
    raise SystemExit(f"server did not answer; see {log_file}")


# --------------------------------------------------------------------------
# A browser that plays like a kid.
# --------------------------------------------------------------------------
class CheckFailed(AssertionError):
    pass


class Kid:
    def __init__(self, base, width, height, shots, name=None, label=""):
        self.base = base
        self.width = width
        self.height = height
        self.shots = shots
        self.label = label
        self.name = name or f"Kid {int(time.time() * 1000) % 1000000} {label}"[:20]
        self.d = wd.new(width, height)
        self.failures = []
        self._shot_n = 0

    # -- checks -----------------------------------------------------------
    def check(self, ok, what, detail=""):
        if ok:
            print(f"  ok  {what}")
        else:
            msg = what + (f" [{detail}]" if detail else "")
            print(f"  FAIL {msg}")
            self.failures.append(msg)
        return ok

    def fail(self, what):
        self.failures.append(what)
        print(f"  FAIL {what}")

    def _install_error_collector(self):
        try:
            self.d.js("window.__e2eErrors=[];"
                      "window.addEventListener('error',e=>window.__e2eErrors.push(String(e.message)));"
                      "window.addEventListener('unhandledrejection',e=>window.__e2eErrors.push(String(e.reason)));")
        except Exception:
            pass

    def js(self, script, *args):
        return self.d.js(script, *args)

    def wait_for(self, script, timeout, what, *args):
        end = time.time() + timeout
        last = None
        while time.time() < end:
            try:
                value = self.js(script, *args)
                if value:
                    return value
            except Exception as exc:        # the page may be loading
                last = str(exc)[:200]
            time.sleep(.05)
        state = ""
        try:
            state = json.dumps({
                "url": self.js("return location.href"),
                "site": self.js("return typeof site !== 'undefined' && site ? site.key : null"),
                "banner": self.js("return (document.querySelector('#banner')||{}).innerText || ''")[:300],
                "busy": self.js("return typeof busy !== 'undefined' ? busy : null"),
            })
        except Exception:
            pass
        raise CheckFailed(f"timed out waiting for {what} ({last or 'no value'}) {state}")

    def shot(self, tag):
        self._shot_n += 1
        name = re.sub(r"[^a-zA-Z0-9_.-]+", "-", tag)[:60]
        path = os.path.join(self.shots, f"{self.label}-{self._shot_n:02d}-{name}.png")
        self.d.shot(path)
        return path

    def logs(self, where):
        bad = []
        for entry in self.d.logs():
            if entry["level"] in ("INFO",):
                continue
            bad.append(entry)
        if bad:
            self.check(False, f"console at {where}", json.dumps(bad)[:500])
        return bad

    # -- joining ----------------------------------------------------------
    def join(self):
        self.d.go(self.base + "/planet")
        self.wait_for("return !!document.querySelector('#joinButton')", 15, "join form")
        self.d.js("document.querySelector('#name').value=arguments[0]", self.name)
        self.d.click("#joinButton")
        self.wait_for("return !document.querySelector('#app').hidden", 20, "app after join")
        self._install_error_collector()
        # First join shows the how-it-works card. On a class laptop its title
        # and its button must both be on screen without scrolling.
        if self.js("return !document.querySelector('#intro').hidden"):
            self.check_intro()
            self.d.click("#introClose")
            time.sleep(.15)
        self.check(self.js("return document.querySelector('#intro').hidden"), "intro closed")
        self.logs("join/intro")
        self.check_header()

    def check_intro(self):
        box = self.js("""const i=document.querySelector('#intro'), c=i.querySelector('.intro-card'),
          b=document.querySelector('#introClose'), cv=document.querySelector('#introScene');
          const R=e=>{const r=e.getBoundingClientRect();return [Math.round(r.left),Math.round(r.top),Math.round(r.right),Math.round(r.bottom)]};
          return {card:R(c), button:R(b), canvas:R(cv), scrollTop:i.scrollTop, vw:innerWidth, vh:innerHeight};""")
        card, button, canvas = box["card"], box["button"], box["canvas"]
        self.check(card[1] >= 0 and card[3] <= box["vh"] + 1,
                   "intro card fits the screen", json.dumps(box))
        self.check(button[1] >= 0 and button[3] <= box["vh"] + 1,
                   "intro button is visible", json.dumps(button))
        self.check(canvas[1] >= 0 and canvas[3] <= box["vh"] + 1,
                   "intro picture is visible", json.dumps(canvas))

    def check_header(self):
        # The stars button deliberately scales up while a new star flies to it;
        # that short animation makes neighbouring buttons' rects overlap, so
        # wait for it to settle before measuring the real layout.
        for _ in range(30):
            if not self.js("return !!document.querySelector('#starsButton.bump')"):
                break
            time.sleep(.05)
        info = self.js("""return {vw:innerWidth, sw:document.documentElement.scrollWidth,
          hiddenIntro:document.querySelector('#intro').hidden,
          who:[...document.querySelectorAll('.who > *')].filter(e=>e.offsetParent).map(e=>{
            const r=e.getBoundingClientRect();return [e.id||e.className,Math.round(r.left),Math.round(r.right)]})}""")
        self.check(info["sw"] <= info["vw"] + 1, "page has no sideways scroll", json.dumps(info))
        # Buttons in the header must not sit under each other.
        rects = [(a[0], a[1], a[2]) for a in info["who"]]
        for (n1, l1, r1), (n2, l2, r2) in zip(rects, rects[1:]):
            if n1 and n2 and r1 > l2 + 1:
                self.check(False, "header buttons overlap", f"{n1} {r1} > {n2} {l2}")

    # -- opening a site ---------------------------------------------------
    def open_from_map(self, key):
        if self.js("return !document.querySelector('#celebrate').hidden"):
            self.js("hideCelebrate()")
        if not self.js("return document.querySelector('#levels').hidden"):
            self.d.js("closeLevels()")
        self.d.click("#levelsButton")
        self.wait_for("return !document.querySelector('#levels').hidden", 8, "Levels map")
        tile = f'#zoneList .tile[data-key="{key}"]'
        if not self.js("return !!document.querySelector(arguments[0])", tile):
            # Star Voyage and class levels are there; a locked one is a failure.
            self.fail(f"no Levels tile for {key}")
            self.d.js("closeLevels()")
            return False
        self.d.js("document.querySelector(arguments[0]).click()", tile)
        try:
            self.wait_for("return typeof site !== 'undefined' && site && site.key === arguments[0]", 15,
                          f"site {key}", key)
        except CheckFailed as exc:
            self.fail(str(exc))
            return False
        self.wait_for("return document.querySelector('#siteName').textContent.length > 1", 3,
                      "site name")
        self.check_header()
        self.logs(f"open {key}")
        return True

    def open_voyage(self):
        if not self.js("return !document.querySelector('#celebrate').hidden"):
            self.js("hideCelebrate()")
        self.d.click("#voyageButton")
        self.wait_for("return /^v\\d+$/.test(site.key)", 15, "a Star Voyage level")
        return self.js("return site.key")

    # -- scouting and the typing coach -----------------------------------
    def _pad_click(self, move):
        self.d.js("""const b=[...document.querySelectorAll('#pad [data-move]')]
          .find(e=>e.dataset.move===arguments[0] && e.offsetParent); if(b) b.click();""", move)

    def drive_reference(self, key, double_use=False):
        ref = planet.find_site(key)[2]["reference"]
        moves = expand(reference=ref)
        # The site opens in Scout mode on the drive-first practice parks.
        if self.js("return !scout"):
            self.d.click("#scoutButton")
        self.wait_for("return !!scout && !document.querySelector('#pad').hidden", 8, "Scout pad")
        for n, move in enumerate(moves):
            if isinstance(move, tuple):
                kind, way = move
                self._pad_click(kind)
                time.sleep(.08)
                self._pad_click(way)
            else:
                self._pad_click(move)
            self.wait_for("return scout && scout.moves.length >= arguments[0]", 10,
                          f"scout move {n + 1}", n + 1)
            time.sleep(.03)
        self.wait_for("return !document.querySelector('#scoutCode').disabled", 10,
                      "Use as code enabled")
        if double_use:
            # A kid may tap it twice; the second tap must not break the code.
            self.d.js("document.querySelector('#scoutCode').click();"
                      "document.querySelector('#scoutCode').click();")
        else:
            self.d.click("#scoutCode")
        self.wait_for("return typeof site !== 'undefined' && !!site.typing", 8, "typing target")
        self.logs(f"use as code {key}")
        self.type_blanks(wrong_once=(key in ("p1", "p8")))
        self.check(self.js("return gapAt() < 0"), f"{key} coach finished")
        self.check(self.js("return document.querySelector('#code').value === site.typing.target"),
                   f"{key} code is finished", self.js("return document.querySelector('#code').value"))

    def type_blanks(self, wrong_once=False):
        wrong_done = False
        for _ in range(400):
            info = self.js("""return {v:document.querySelector('#code').value,
              t:site.typing&&site.typing.target, m:site.typing&&site.typing.mask,
              coach:(document.querySelector('#typeCoach')||{}).innerText||'',
              gap:typeof gapAt==='function'?gapAt():-2};""")
            if not info["t"]:
                break
            v, target, mask = info["v"], info["t"], info["m"]
            idx = next((i for i, ch in enumerate(v)
                        if ch == "_" and i < len(target) and target[i] != "_"), None)
            if idx is None:
                break
            want = target[idx]
            if wrong_once and not wrong_done:
                wrong = "q" if want.lower() != "q" else "z"
                self.d.send("#code", wrong)
                time.sleep(.08)
                coach = self.js("return document.querySelector('#typeCoach').innerText")
                self.check("Not that one" in coach, "typing coach says which key is right",
                           coach[:200])
                wrong_done = True
            if want in '():,"' and "Shift" not in info["coach"]:
                self.fail(f"typing coach does not say how to shift {want!r}")
            self.d.send("#code", want)
            try:
                self.wait_for(
                    "return document.querySelector('#code').value[arguments[0]] === arguments[1]",
                    3, f"coach key {want!r}", idx, want)
            except CheckFailed:
                got = self.js("return document.querySelector('#code').value")
                self.fail(f"typing coach lost key {want!r} at {idx}: {got!r}")
                break
        coach = self.js("return (document.querySelector('#typeCoach')||{}).innerText||''")
        return coach

    def set_typed_code(self, key, code=None):
        if code is None:
            found = planet.find_site(key)
            if not found:
                self.fail(f"no reference route for {key}")
                return
            code = found[2]["reference"]
        self.d.js("""const t=document.querySelector('#code'); t.value=arguments[0];
          t.dispatchEvent(new Event('input',{bubbles:true}));""", code)
        time.sleep(.1)
        self.check(self.js("return document.querySelector('#code').value === arguments[0]", code),
                   f"{key} typed level code set")

    # -- running and the win card ----------------------------------------
    def transmit(self, timeout=50):
        self.d.click("#runButton")
        try:
            self.wait_for("return !document.querySelector('#celebrate').hidden", timeout, "win card")
        except CheckFailed as exc:
            self.fail(str(exc))
            return False
        self.logs("transmit")
        box = self.js("""const c=document.querySelector('.cele-card'),
          a=document.querySelector('#celeActions button');
          const R=e=>{const r=e.getBoundingClientRect();return [Math.round(r.left),Math.round(r.top),Math.round(r.right),Math.round(r.bottom)]};
          return {card:R(c), action:a?R(a):null, vw:innerWidth, vh:innerHeight,
            title:document.querySelector('#celeTitle').textContent,
            sub:document.querySelector('#celeSub').textContent,
            actions:[...document.querySelectorAll('#celeActions button')].map(b=>b.innerText)};""")
        self.check(box["title"].strip() != "", "win card has a title")
        self.check(box["card"][1] >= 0 and box["card"][3] <= box["vh"] + 1,
                   "win card fits the screen", json.dumps(box["card"]))
        self.check(bool(box["actions"]), "win card has a button", json.dumps(box["actions"]))
        if box["action"]:
            self.check(box["action"][1] >= 0 and box["action"][3] <= box["vh"] + 1,
                       "win card button is visible", json.dumps(box["action"]))
        return box

    def next_level(self, expected=None):
        actions = self.js("return [...document.querySelectorAll('#celeActions button')].map(b=>b.innerText)")
        button = next((a for a in actions
                       if button_label(a).startswith(("Next level", "Another class level", "Back to my levels"))), None)
        if not button:
            self.fail(f"no Next button on win card: {actions}")
            return False
        before = self.js("return site ? site.key : null")
        self.d.js("""const b=[...document.querySelectorAll('#celeActions button')]
          .find(e=>e.innerText===arguments[0]); if(b) b.click();""", button)
        try:
            self.wait_for("return site && site.key !== arguments[0]", 15, "next site", before)
        except CheckFailed as exc:
            self.fail(str(exc))
            return False
        got = self.js("return site.key")
        if expected:
            self.check(got == expected, f"Next opens {expected} (got {got})")
        self.logs(f"next {got}")
        return True

    def close_win(self):
        if self.js("return !document.querySelector('#celebrate').hidden"):
            self.js("hideCelebrate()")

    # -- other screens ----------------------------------------------------
    def levels_map(self):
        self.close_win()
        self.d.click("#levelsButton")
        self.wait_for("return !document.querySelector('#levels').hidden", 8, "Levels map")
        info = self.js("""const c=document.querySelector('.levels-card').getBoundingClientRect();
          const zs=[...document.querySelectorAll('#zoneList .zone-card')].map(e=>e.dataset.zone);
          return {rect:[Math.round(c.left),Math.round(c.top),Math.round(c.right),Math.round(c.bottom)],
            vw:innerWidth,vh:innerHeight,zones:zs,
            groups:[...document.querySelectorAll('#zoneList .zone-group')].map(e=>e.innerText)};""")
        self.check(info["rect"][1] >= 0 and info["rect"][3] <= info["vh"] + 1,
                   "Levels map fits the screen", json.dumps(info["rect"]))
        self.check("practice" in info["zones"], "Levels map lists the practice parks", info["zones"][:5])
        self.check(any("voyage" in g.lower() for g in info["groups"]), "Levels map lists Star Voyage")
        # Fold and unfold the practice zone.
        self.d.js("""document.querySelector('#zoneList .zone-card[data-zone="practice"] .zone-top').click()""")
        time.sleep(.1)
        self.d.js("""document.querySelector('#zoneList .zone-card[data-zone="practice"] .zone-top').click()""")
        # A zone icon should scroll, not error.
        if self.js("return !!document.querySelector('#zoneJump .jump-zone[data-zone=\"practice\"]')"):
            self.d.js("document.querySelector('#zoneJump .jump-zone[data-zone=\"practice\"]').click()")
            time.sleep(.1)
        self.logs("levels map")
        self.shot("levels")
        self.d.click("#levelsClose")
        self.check(self.js("return document.querySelector('#levels').hidden"), "Levels map closes")
        self.d.js("document.querySelector('#levelsClose').click()")

    def garage(self):
        self.close_win()
        self.d.click("#starsButton")
        self.wait_for("return !document.querySelector('#garage').hidden", 8, "garage")
        info = self.js("""const c=document.querySelector('.garage-card').getBoundingClientRect();
          return {rect:[Math.round(c.left),Math.round(c.top),Math.round(c.right),Math.round(c.bottom)],
            vw:innerWidth,vh:innerHeight,tabs:[...document.querySelectorAll('#garageTabs .tab')].map(b=>b.innerText)};""")
        self.check(info["rect"][1] >= 0 and info["rect"][3] <= info["vh"] + 1,
                   "garage fits the screen", json.dumps(info["rect"]))
        self.check(len(info["tabs"]) >= 8, "garage has its shelves", json.dumps(info["tabs"]))
        # Pick something on Paint, then Surprise me, then look at Badges.
        self.d.js("""const b=[...document.querySelectorAll('#garageShelf .card')]
          .find(e=>!e.classList.contains('locked')); if(b) b.click();""")
        time.sleep(.2)
        self.d.click("#surpriseButton")
        time.sleep(.3)
        self.d.click('#garageTabs [data-tab="badges"]')
        time.sleep(.2)
        self.shot("garage")
        self.d.click("#garageClose")
        time.sleep(.1)
        self.d.js("document.querySelector('#garageClose').click()")
        self.check(self.js("return document.querySelector('#garage').hidden"), "garage closes")
        self.logs("garage")

    def hints_and_help(self):
        self.close_win()
        self.d.click("#radioButton")
        self.wait_for("return !document.querySelector('#radioPop').hidden", 5, "hints pop")
        info = self.js("""const p=document.querySelector('#radioPop'),r=p.getBoundingClientRect();
          return [Math.round(r.left),Math.round(r.top),Math.round(r.right),Math.round(r.bottom),
            innerWidth,innerHeight];""")
        self.check(info[1] >= 0 and info[3] <= info[5] + 1,
                   "hints pop fits the screen", json.dumps(info))
        before = self.js("return document.querySelector('#hints').innerText")
        if self.js("return !document.querySelector('#hintButton').hidden"):
            self.d.click("#hintButton")
            time.sleep(.35)
            after = self.js("return document.querySelector('#hints').innerText")
            self.check(after != before, "Ask for a hint gives a hint",
                       f"{before[:80]!r} -> {after[:80]!r}")
        self.logs("hints")
        self.d.click("#radioButton")       # toggle the pop shut
        self.d.click("#helpButton")
        self.wait_for("return !document.querySelector('#intro').hidden", 5, "help card")
        self.check_intro()
        self.logs("help")
        self.d.click("#introClose")
        time.sleep(.1)

    # -- resize ------------------------------------------------------------
    def resize(self, width, height):
        self.d.request("POST", f"/session/{self.d.sid}/goog/cdp/execute",
                       {"cmd": "Emulation.setDeviceMetricsOverride",
                        "params": {"width": width, "height": height,
                                   "deviceScaleFactor": 1, "mobile": False}})
        time.sleep(.25)
        self.check_header()

    def close(self):
        try:
            self.logs("final")
        finally:
            self.d.close()


# --------------------------------------------------------------------------
# Reference routes: a for loop in a level's own answer is the same moves.
# --------------------------------------------------------------------------
def expand(reference):
    lines = reference.split("\n")
    out = []

    # A for loop body is parsed once into out, then repeated by re-parsing.
    def parse(i, indent):
        while i < len(lines):
            line = lines[i]
            if not line.strip():
                i += 1
                continue
            cur = len(line) - len(line.lstrip())
            if cur < indent:
                return i
            s = line.strip()
            m = re.match(r"for \w+ in range\((\d+)\):$", s)
            if m:
                j = i + 1
                body_start = j
                while j < len(lines) and (not lines[j].strip() or
                                          len(lines[j]) - len(lines[j].lstrip()) >= indent + 4):
                    j += 1
                body = lines[body_start:j]
                for _ in range(int(m.group(1))):
                    out.extend(expand("\n".join(body)))
                i = j
                continue
            if s.startswith(("if ", "while ", "else:", "elif ")):
                i += 1
                continue
            m = re.match(r"(north|south|east|west|wait)\((?:(\d+))?\)$", s)
            if m:
                out.extend([m.group(1)] * int(m.group(2) or 1))
                i += 1
                continue
            m = re.match(r'(jump|drill|knock)\("(\w+)"\)$', s)
            if m:
                out.append((m.group(1), m.group(2)))
                i += 1
                continue
            raise ValueError(f"cannot scout reference line: {line!r}")
        return i

    out = []
    parse(0, 0)
    return out


# --------------------------------------------------------------------------
# One full play-through at one window size.
# --------------------------------------------------------------------------
def play_through(args, base, width, height, label, workshop_key, quick):
    print(f"\n=== {label} at {width}x{height} ===")
    kid = Kid(base, width, height, args.shots, name=f"{args.name} {label}"[:20] if args.name else None,
              label=label)
    try:
        kid.join()
        plan = QUICK if quick else PRACTICE
        won_any = False
        for key, mode in plan:
            print(f"-- {key} ({mode})")
            nxt = kid.js("return typeof nextSite === 'function' ? nextSite() : null")
            if won_any and nxt == key:
                if not kid.next_level(expected=key):
                    return kid.failures
            else:
                if won_any:
                    kid.close_win()
                if not kid.open_from_map(key):
                    continue
            if mode == "drive":
                kid.drive_reference(key, double_use=(key == "p1"))
            else:
                kid.set_typed_code(key)
            if not kid.transmit():
                continue
            kid.shot(f"win-{key}")
            won_any = True
        kid.close_win()

        kid.levels_map()
        kid.garage()
        kid.hints_and_help()

        # Star Voyage: drive the first paint picture and use its Next button.
        vkey = kid.js("return typeof voyageNext === 'function' ? voyageNext() : null")
        if vkey:
            if not kid.open_from_map(vkey):
                kid.fail("could not open the Star Voyage level")
            else:
                kid.drive_reference(vkey)
                if kid.transmit():
                    kid.shot("win-voyage")
                    if kid.next_level():
                        kid.shot("voyage-next")
                        kid.close_win()
        else:
            kid.d.js("openSite('v1')")
            kid.wait_for("return site && site.key === 'v1'", 10, "v1")
            kid.drive_reference("v1")
            kid.transmit()
            kid.close_win()

        # A classmate's Class Workshop level, when the setup made one.
        if workshop_key:
            print(f"-- workshop {workshop_key}")
            kid.close_win()
            if kid.open_from_map(workshop_key):
                kid.set_typed_code(workshop_key, "east(10)\n")
                if kid.transmit():
                    kid.shot("win-workshop")
                    actions = kid.js("return [...document.querySelectorAll('#celeActions button')].map(b=>b.innerText)")
                    kid.check(any(button_label(a).startswith(("Back to my levels", "Another class level", "Next level"))
                                  for a in actions), "workshop win offers a way on", json.dumps(actions))
        else:
            print("  (no class workshop level to play; pass --setup-workshop)")

        # The header has to survive a resize to a class laptop size.
        kid.close_win()
        kid.resize(1280 if width != 1280 else 1366, 720 if height != 720 else 768)
        kid.resize(width, height)
        kid.shot("final")
    except CheckFailed as exc:
        kid.fail(str(exc))
    finally:
        kid.close()
    return kid.failures


# --------------------------------------------------------------------------
# Odd names, double presses and reload mid-run, each in its own browser.
# --------------------------------------------------------------------------
def odd_names(args, base):
    print("\n=== odd names ===")
    failures = []
    cases = [("\u200b", False, "invisible name is refused"),
             ("\u0301", False, "combining-mark name is refused"),
             ("   ", False, "spaces are refused"),
             ("O'Brien", True, "a single quote is fine"),
             ("\U0001F600", True, "an emoji is fine"),
             ("\U0001F9D1\u200d\U0001F680", True, "a joined emoji is fine")]
    for name, should_join, what in cases:
        kid = Kid(base, 1280, 720, args.shots,
                  name=(name if should_join else "Odd Name"), label="odd")
        try:
            kid.d.go(base + "/planet")
            kid.wait_for("return !!document.querySelector('#joinButton')", 15, "join form")
            kid.d.js("document.querySelector('#name').value=arguments[0]", name)
            kid.d.click("#joinButton")
            time.sleep(.8)
            joined = kid.js("return !document.querySelector('#app').hidden")
            if should_join:
                ok = joined and kid.js("return document.querySelector('#driver').textContent") == name
                kid.check(ok, what)
                if joined:
                    if kid.js("return !document.querySelector('#intro').hidden"):
                        kid.d.click("#introClose")
                    kid.check_header()
            else:
                placeholder = kid.js("return document.querySelector('#name').placeholder")
                kid.check(not joined and "Type your name" in placeholder, what, placeholder)
            kid.logs(f"name {name!r}")
        except CheckFailed as exc:
            kid.fail(str(exc))
        finally:
            kid.close()
        failures.extend(kid.failures)
    return failures


def double_presses(args, base):
    print("\n=== double presses and reload mid-run ===")
    failures = []
    kid = Kid(base, 1280, 720, args.shots, name="Double Kid", label="double")
    try:
        kid.join()
        # Double-tap Land the rover is harmless too, but it needs a fresh page;
        # the join is already covered by the main play-through.
        if not kid.open_from_map("p4"):
            raise CheckFailed("could not open p4")
        moves = ["east"] * 5
        for n, move in enumerate(moves):
            kid._pad_click(move)
            kid.wait_for("return scout && scout.moves.length >= arguments[0]", 10,
                         f"p4 move {n + 1}", n + 1)
        kid.wait_for("return !document.querySelector('#scoutCode').disabled", 10,
                     "p4 Use as code")
        kid.d.js("document.querySelector('#scoutCode').click();"
                 "document.querySelector('#scoutCode').click();")
        kid.wait_for("return !!site.typing", 8, "p4 typing")
        kid.type_blanks()
        # Send twice as fast as a kid can: the second press must be ignored.
        kid.d.js("const b=document.querySelector('#runButton'); b.click(); b.click();")
        # Wait for the server to take the run, then reload while its replay is
        # still playing (and before a kid would have read the win card).
        kid.wait_for("return (typeof busy !== 'undefined' && busy === false)"
                     " && (typeof site !== 'undefined' && !!site.lastSent)", 15, "run sent")
        time.sleep(.1)
        kid.d.go(base + "/planet")
        kid.wait_for("return !document.querySelector('#app').hidden", 20, "app after reload")
        time.sleep(1)
        kid.check(int(kid.js("return document.querySelector('#totalStars').textContent") or 0) >= 1,
                  "a reload mid-run keeps the win", kid.js("return document.querySelector('#totalStars').textContent"))
        kid.check(kid.js("return document.querySelector('#code').value").strip() == "east(5)",
                  "a reload mid-run keeps the code")
        kid.logs("reload")
        kid.check_header()
        # Double-tap the garage and Levels close buttons.
        kid.d.click("#starsButton")
        kid.wait_for("return !document.querySelector('#garage').hidden", 8, "garage")
        kid.d.js("document.querySelector('#garageClose').click();"
                 "document.querySelector('#garageClose').click();")
        kid.check(kid.js("return document.querySelector('#garage').hidden"), "garage closes twice cleanly")
        kid.d.click("#levelsButton")
        kid.wait_for("return !document.querySelector('#levels').hidden", 8, "Levels map")
        kid.d.js("document.querySelector('#levelsClose').click();"
                 "document.querySelector('#levelsClose').click();")
        kid.check(kid.js("return document.querySelector('#levels').hidden"), "Levels closes twice cleanly")
        kid.logs("double")
    except CheckFailed as exc:
        kid.fail(str(exc))
    finally:
        kid.close()
    failures.extend(kid.failures)
    return failures


def setup_workshop(args, base):
    """Make one known class level and publish it, for play_through to open."""
    if not args.setup_workshop:
        return None
    print("\n=== setting up a Class Workshop level ===")
    try:
        out = post(base + "/admin", {"key": args.admin_key, "action": "planet_maker", "on": True})
        if out.get("error"):
            print("  could not open the Class Workshop:", out.get("error"))
            return None
        suffix = int(time.time()) % 10000
        maker = post(base + "/join", {"name": f"E2E Maker {suffix}"})
        rows = ["S.........G."] + ["............"] * 7
        saved = post(base + "/planet/maker/save",
                     {"id": maker["id"], "rows": rows, "name": f"e2e moo {suffix}"})
        if saved.get("error"):
            print("  could not save the level:", saved["error"])
            return None
        key = saved["key"]
        ran = post(base + "/planet/run", {"id": maker["id"], "site": key, "code": "east(10)\n"})
        live = bool(ran.get("rewards", {}).get("published"))
        print(f"  class level {key} live={live}")
        return key if live else None
    except Exception as exc:
        print("  workshop setup failed:", exc)
        return None


# --------------------------------------------------------------------------
def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--base", default="http://127.0.0.1:8791")
    ap.add_argument("--start-server", action="store_true",
                    help="start a fresh test server on --base and kill it at the end")
    ap.add_argument("--state-file", default="/tmp/kidshunt-e2e-state.json")
    ap.add_argument("--fresh", action="store_true",
                    help="delete --state-file before starting (use only for a test state)")
    ap.add_argument("--server-log", default="/tmp/kidshunt-e2e-server.log")
    ap.add_argument("--admin-key", default=os.environ.get("PLANET_ADMIN_KEY", "0106"))
    ap.add_argument("--easy", action="store_true", help="turn Easy mode on with the admin key")
    ap.add_argument("--setup-workshop", action="store_true",
                    help="make and publish one known class level to play")
    ap.add_argument("--quick", action="store_true", help="fewer levels; useful while editing")
    ap.add_argument("--name", default="", help="join with this name instead of a unique one")
    ap.add_argument("--shots", default=os.path.join(ROOT, ".kidshunt-shots"))
    ap.add_argument("--skip-odd", action="store_true")
    ap.add_argument("--skip-double", action="store_true")
    args = ap.parse_args(argv)
    os.makedirs(args.shots, exist_ok=True)
    base = base_url(args.base)
    server = None
    if args.start_server:
        if args.fresh and os.path.exists(args.state_file):
            os.unlink(args.state_file)
        server = start_server(base, args.state_file, args.server_log)
        print(f"started test server pid {server.pid}, state {args.state_file}")
    elif not server_up(base):
        raise SystemExit(f"no server at {base}; start server.py first or use --start-server")

    failures = []
    try:
        if args.easy:
            out = post(base + "/admin", {"key": args.admin_key,
                                         "action": "planet_easy", "on": True})
            msg = out.get("ok") or out.get("error")
            print("easy mode:", msg)
            if not out.get("ok") or "Easy mode on" not in out.get("ok", ""):
                failures.append(f"could not turn on Easy mode: {msg}")
        workshop = setup_workshop(args, base)
        # The class part of the check is at the younger class's two sizes.
        for width, height, label in ((1366, 768, "1366"), (1280, 720, "1280")):
            failures.extend(play_through(args, base, width, height, label, workshop, args.quick))
        if not args.skip_odd:
            failures.extend(odd_names(args, base))
        if not args.skip_double:
            failures.extend(double_presses(args, base))
    finally:
        if server is not None:
            print(f"stopping test server pid {server.pid}")
            server.terminate()
            try:
                server.wait(timeout=10)
            except subprocess.TimeoutExpired:
                server.kill()

    print("\n=== result ===")
    if failures:
        print(f"{len(failures)} failure(s):")
        for f in failures:
            print(" -", f)
        return 1
    print("all checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
