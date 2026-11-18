#!/usr/bin/env python3
"""A real-browser bug hunt of the Strange Planet MAIN ROUTE, without easy mode.

This is a tool, not a unittest.  It drives headless Chromium through the page
the top students use: a wrong run and the same code again, the win card's Next,
the record ghost, coming back to a finished level, scouting + Use as code with
its blanks, wrong and right report() levels, hints, a jump level, a laser level,
Cargo Run, Grand Tour and Uncharted (including a partial-planet summary card).
It also runs a second student at 1280x720, joins, checks the main-route page
rules and plays the scouting/blank flow there.

Start a test server of your own first, with a student whose route is unlocked
(see DS_REPORT.md), then run:

    python3 tools/e2e_planet_route.py --base http://127.0.0.1:8799 \\
        --shots .kidshunt-shots/route-e2e

It never starts or kills a server, and it only talks to --base.  Screenshots
go to --shots.  It exits 1 on console errors, a card that does not fit, a
missing button label, a step that does not finish, or a wrong answer.

--stuck also waits for the normal 10-miss / 90-second Build it together offer
and the 20-miss Skip for now, and drives both.  That is slow; use a test server
whose stuck thresholds you shortened (server.TOGETHER_AFTER, TOGETHER_WAIT and
SKIP_AFTER) when iterating.
"""
import argparse
import json
import os
import re
import sys
import time
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, ROOT)
import wd                       # noqa: E402
import planet                   # noqa: E402

# Crystal/bonus detours, from test_planet's BONUS_PROGRAMS.
BONUS = {
    "8a": 'for i in range(4):\n    jump("east")\n',
    "6a": ("south(2)\nnorth()\nsouth(2)\nnorth()\nwest(2)\n"
           "north(2)\neast(2)\n"),
    "16a": 'east(3)\ndrill("east")\neast(10)\nsouth(2)\nwest(8)\n',
    "2b": "north()\neast()\nsouth()\neast()\nnorth()\nsouth()\nwest()\n",
}
UNCHARTED_PARTIAL = planet.UNCHARTED_REFERENCE.replace("    ready()\n", "")


def post(url, data):
    req = urllib.request.Request(
        url, data=json.dumps(data).encode(),
        headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as f:
        return json.load(f)


def get(url):
    with urllib.request.urlopen(url, timeout=60) as f:
        return json.load(f)


def expand(reference):
    """A reference route as hand moves; a for loop is the same moves again."""
    lines = reference.split("\n")
    out = []

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
                while j < len(lines) and (not lines[j].strip() or
                                          len(lines[j]) - len(lines[j].lstrip()) >= indent + 4):
                    j += 1
                body = lines[i + 1:j]
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

    parse(0, 0)
    return out


class Report:
    def __init__(self):
        self.failures = []
        self.notes = []

    def ok(self, text):
        print(f"  ok   {text}")

    def fail(self, text, detail=""):
        row = text + (f" [{detail}]" if detail else "")
        self.failures.append(row)
        print(f"  FAIL {row}")

    def note(self, text):
        self.notes.append(text)
        print(f"  note {text}")

    def check(self, ok, text, detail=""):
        self.ok(text) if ok else self.fail(text, detail)
        return ok


REPORT = Report()


class Kid:
    def __init__(self, base, name, width, height, shots, label):
        self.base = base.rstrip("/")
        self.name = name
        self.width, self.height = width, height
        self.shots = shots
        self.label = label
        os.makedirs(shots, exist_ok=True)
        self.d = wd.new(width, height)
        self.shot_n = 0
        self.d.go(self.base + "/planet")
        self.wait("return !!document.querySelector('#joinButton')", 20, "the join form")
        # Start this browser clean: a draft saved by an earlier run must not
        # hide the code-carry check.
        self.d.js("localStorage.clear();")
        self.d.js("document.querySelector('#name').value=arguments[0]", self.name)
        self.d.click("#joinButton")
        self.wait("return !document.querySelector('#app').hidden", 20, "the app after join")
        self.pid = self.d.js("return me")
        self.d.js("window.__e2eErrors=[];"
                 "window.addEventListener('error',e=>window.__e2eErrors.push(String(e.message)));"
                 "window.addEventListener('unhandledrejection',e=>window.__e2eErrors.push(String(e.reason)));")
        if self.d.js("return !document.querySelector('#intro').hidden"):
            self.shot("intro")
            self.check_intro()
            self.d.click("#introClose")
            time.sleep(.2)
        self.logs("join")

    # -- checks --------------------------------------------------------------
    def check(self, ok, text, detail=""):
        return REPORT.check(ok, f"{self.label}: {text}", detail)

    def fail(self, text, detail=""):
        REPORT.fail(f"{self.label}: {text}", detail)

    def note(self, text):
        REPORT.note(f"{self.label}: {text}")

    def check_intro(self):
        box = self.d.js("""const i=document.querySelector('#intro'), c=i.querySelector('.intro-card'),
          b=document.querySelector('#introClose');
          const R=e=>{const r=e.getBoundingClientRect();return [Math.round(r.left),Math.round(r.top),Math.round(r.right),Math.round(r.bottom)]};
          return {card:R(c), button:R(b), vw:innerWidth, vh:innerHeight};""")
        self.check(box["card"][1] >= 0 and box["card"][3] <= box["vh"] + 1,
                   "the intro card fits the screen", json.dumps(box))
        self.check(box["button"][1] >= 0 and box["button"][3] <= box["vh"] + 1,
                   "the intro button is visible", json.dumps(box))

    def shot(self, tag):
        self.shot_n += 1
        name = re.sub(r"[^a-zA-Z0-9_.-]+", "-", tag)[:60]
        path = os.path.join(self.shots, f"{self.label}-{self.shot_n:02d}-{name}.png")
        self.d.shot(path)
        return path

    def wait(self, script, timeout, what, *args):
        end = time.time() + timeout
        last = None
        while time.time() < end:
            try:
                value = self.d.js(script, *args)
                if value:
                    return value
            except Exception as exc:        # the page may still be loading
                last = str(exc)[:200]
            time.sleep(.05)
        state = ""
        try:
            state = json.dumps({
                "site": self.d.js("return typeof site !== 'undefined' && site ? site.key : null"),
                "banner": (self.d.js("return (document.querySelector('#banner')||{}).innerText || ''") or "")[:240],
                "busy": self.d.js("return typeof busy !== 'undefined' ? busy : null"),
                "errors": self.d.js("return window.__e2eErrors || []"),
            })
        except Exception:
            pass
        raise RuntimeError(f"timed out waiting for {what} ({last or 'no value'}) {state}")

    def logs(self, where):
        bad = []
        for entry in self.d.logs():
            if entry["level"] not in ("INFO",):
                bad.append(entry)
        try:
            page_errors = self.d.js("return window.__e2eErrors.splice(0)") or []
        except Exception:
            page_errors = []
        if bad or page_errors:
            self.fail(f"console at {where}", json.dumps(bad + page_errors)[:600])

    def layout(self, label):
        info = self.d.js(r"""
            const bad = [];
            const name = el => el.id ? '#' + el.id
              : (el.className ? '.' + String(el.className).split(' ')[0] : el.tagName);
            const scrollable = el => {
              for (let p = el.parentElement; p; p = p.parentElement) {
                const cs = getComputedStyle(p);
                if (/(auto|scroll)/.test(cs.overflowX + cs.overflowY)) return true;
              }
              return false;
            };
            for (const el of document.querySelectorAll('body *')) {
              const cs = getComputedStyle(el);
              if (cs.display === 'none' || cs.visibility === 'hidden' || cs.opacity === '0') continue;
              if (el.closest('#route, #announce, #toasts, .ac, .feed, .levels-card, .garage-card, .shop-card, .team-map, .lounge-room, #paint, #scope') || el.id === 'newPip') continue;
              if (['TEXTAREA', 'INPUT', 'SELECT'].includes(el.tagName)) continue;
              const r = el.getBoundingClientRect();
              if (r.width < 1 || r.height < 1) continue;
              if ((r.right > innerWidth + 1 || r.left < -1 || r.bottom > innerHeight + 1 || r.top < -1)
                  && !scrollable(el)) {
                bad.push({el: name(el), text: (el.innerText || '').slice(0, 40),
                          l: Math.round(r.left), r: Math.round(r.right),
                          t: Math.round(r.top), b: Math.round(r.bottom)});
              }
              if (el.scrollWidth > el.clientWidth + 2 && cs.overflowX === 'hidden'
                  && cs.textOverflow !== 'ellipsis' && el.clientWidth > 4
                  && (el.innerText || '').trim()) {
                bad.push({el: name(el), cut: 'x', scroll: el.scrollWidth,
                          client: el.clientWidth, text: (el.innerText || '').slice(0, 40)});
              }
            }
            return {bad: bad.slice(0, 10), sw: document.documentElement.scrollWidth,
                    vw: innerWidth, sh: document.documentElement.scrollHeight, vh: innerHeight};
        """) or {}
        if info.get("bad"):
            self.fail(f"{label} is clipped or overlaps", json.dumps(info["bad"])[:800])
        if info.get("sw", 0) > info.get("vw", 0) + 1:
            self.fail(f"{label} scrolls sideways", json.dumps(info)[:300])

    def buttons(self, label):
        bad = self.d.js(r"""
            return [...document.querySelectorAll('button')].filter(b => b.offsetParent)
              .filter(b => !(b.innerText || '').trim()
                      && !(b.getAttribute('aria-label') || b.title))
              .map(b => b.id || b.className || b.tagName);
        """) or []
        if bad:
            self.fail(f"{label} has a button with no label", ", ".join(bad[:8]))

    def check_page(self, label):
        self.layout(label)
        self.buttons(label)
        self.logs(label)

    # -- opening and running -------------------------------------------------
    def close_win(self):
        if self.d.js("return !document.querySelector('#celebrate').hidden"):
            self.d.js("hideCelebrate()")
            time.sleep(.15)

    def open(self, key):
        self.close_win()
        if not self.d.js("return document.querySelector('#levels').hidden"):
            self.d.js("closeLevels()")
        self.d.click("#levelsButton")
        self.wait("return !document.querySelector('#levels').hidden", 8, "the Levels map")
        selector = "document.querySelector('#zoneList .tile[data-key=\"' + arguments[0] + '\"]')"
        if not self.d.js(f"return !!{selector}", key):
            self.fail(f"no Levels tile for {key}")
            self.d.js("closeLevels()")
            return False
        self.d.js(f"{selector}.click()", key)
        try:
            self.wait("return typeof site !== 'undefined' && site && site.key === arguments[0]",
                      15, f"site {key}", key)
        except RuntimeError as exc:
            self.fail(str(exc))
            self.d.js("closeLevels()")
            return False
        time.sleep(.3)
        self.check_page(f"{key} open")
        return True

    def set_code(self, code):
        self.d.js("const t=document.querySelector('#code'); t.value=arguments[0];"
                  "t.dispatchEvent(new Event('input',{bubbles:true}));", code)
        time.sleep(.1)
        got = self.d.js("return document.querySelector('#code').value")
        if got != code:
            self.fail("the editor did not keep the code", repr(got)[:200])

    def run_miss(self, key, code, label):
        self.set_code(code)
        before = self.d.js("return (site && site.misses) || 0")
        self.d.click("#runButton")
        try:
            # A miss adds one to the site's count in a row.  (site.lastSent is
            # not reliable here: a code error can be replayed without a run.)
            self.wait("return !busy && !playing && site && site.misses !== arguments[0]",
                      40, f"miss on {key}", before)
            self.wait("return !document.querySelector('#banner').hidden", 8,
                      f"the miss banner on {key}")
        except RuntimeError as exc:
            self.fail(str(exc))
            return ""
        time.sleep(.2)
        self.check_page(label)
        self.shot(label)
        return self.d.js("return document.querySelector('#bannerText').innerText")

    def win_card(self, label, key):
        info = self.d.js("""const c=document.querySelector('.cele-card'),
          a=document.querySelector('#celeActions button');
          const R=e=>{const r=e.getBoundingClientRect();return [Math.round(r.left),Math.round(r.top),Math.round(r.right),Math.round(r.bottom)]};
          return {card:R(c), action:a?R(a):null, vw:innerWidth, vh:innerHeight,
            title:document.querySelector('#celeTitle').textContent,
            sub:document.querySelector('#celeSub').textContent,
            note:document.querySelector('#celeNote').innerText,
            actions:[...document.querySelectorAll('#celeActions button')].map(b=>b.innerText),
            stars:site.stars, ghost:site.ghost,
            frames:scene && scene.run ? scene.run.frames.length : 0,
            jumps:scene && scene.run ? scene.run.frames.filter(f=>f.e==='jump').length : 0,
            beams:scene && scene.run ? scene.run.frames.filter(f=>f.ls).length : 0,
            delivered:scene && scene.run ? scene.run.frames.some(f=>f.cg != null) : false};""")
        self.check(info["title"].strip() != "", f"{key} win card has a title", json.dumps(info)[:400])
        self.check(bool(info["actions"]), f"{key} win card has a button", json.dumps(info["actions"]))
        self.check(info["card"][1] >= 0 and info["card"][3] <= info["vh"] + 1
                   and info["card"][0] >= -1 and info["card"][2] <= info["vw"] + 1,
                   f"{key} win card fits the screen", json.dumps(info["card"]))
        self.check_page(f"{key} win card")
        self.shot(f"{key}-win")
        return info

    def run_win(self, key, code, timeout=75, close=True):
        self.set_code(code)
        self.d.click("#runButton")
        try:
            self.wait("return !document.querySelector('#celebrate').hidden", timeout,
                      f"the win card on {key}")
        except RuntimeError as exc:
            self.fail(str(exc), (self.d.js("return document.querySelector('#bannerText').innerText") or "")[:300])
            self.shot(f"{key}-nowin")
            return None
        time.sleep(1.4)
        info = self.win_card(key, key)
        if close:
            self.close_win()
        return info

    def click_win_action(self, word):
        actions = self.d.js("return [...document.querySelectorAll('#celeActions button')].map(b=>b.innerText)")
        label = next((a for a in actions if word.lower() in a.lower()), None)
        if not label:
            self.fail(f"win card has no {word!r} button", json.dumps(actions))
            return None
        before = self.d.js("return site && site.key")
        self.d.js("const b=[...document.querySelectorAll('#celeActions button')]"
                  ".find(e=>e.innerText===arguments[0]); if (b) b.click();", label)
        try:
            self.wait("return site && site.key !== arguments[0]", 15, f"{word} to open a site", before)
        except RuntimeError as exc:
            self.fail(str(exc))
            return None
        time.sleep(.4)
        self.check_page(f"{word} opened {self.d.js('return site.key')}")
        return self.d.js("return site.key")

    # -- scouting ------------------------------------------------------------
    def scout(self, moves):
        if not self.d.js("return !!scout"):
            self.d.click("#scoutButton")
            self.wait("return !!scout", 8, "Scout")
        for n, move in enumerate(moves):
            if self.d.js("return !scout || scout.over"):
                break
            before = self.d.js("return scout.moves.length")
            if isinstance(move, tuple):
                kind, way = move
                self.d.js("const b=[...document.querySelectorAll('#pad [data-move]')]"
                          ".find(e=>e.dataset.move===arguments[0]&&e.offsetParent); if(b)b.click();", kind)
                time.sleep(.06)
                self.d.js("const b=[...document.querySelectorAll('#pad [data-move]')]"
                          ".find(e=>e.dataset.move===arguments[0]&&e.offsetParent); if(b)b.click();", way)
            else:
                self.d.js("const b=[...document.querySelectorAll('#pad [data-move]')]"
                          ".find(e=>e.dataset.move===arguments[0]&&e.offsetParent); if(b)b.click();", move)
            # The pad queues three clicks; wait for this move to be driven so
            # a long hand route is not silently dropped.
            self.wait("return !scout || scout.moves.length > arguments[0]", 5,
                      f"scout move {n + 1}", before)
            time.sleep(.03)
        self.wait("return scout && scout.over", 15, f"the end of the scout route")
        # The replay still has to play out before the scout says whether it won.
        self.wait("return scout && typeof scout.reached === 'boolean'", 30, "the scout replay to finish")
        self.check(self.d.js("return !!scout && scout.reached"), "the scout reached the goal")
        self.check(not self.d.js("return document.querySelector('#scoutCode').hidden"),
                   "Use as code is on screen before Solar Valley")

    def fill_blanks(self):
        # Two kinds of blanks: a Build it together answer is a guided target
        # with gapAt(), while Use as code on the main route leaves loose words
        # like r____ with no letter-by-letter coach.
        words = ["range", "for", "north", "south", "east", "west", "wait"]
        for _ in range(400):
            info = self.d.js("return {t:site && site.typing && site.typing.target,"
                             "gap:typeof gapAt==='function'?gapAt():-2}")
            if info["t"]:
                if info["gap"] < 0:
                    return True
                self.d.send("#code", info["t"][info["gap"]])
                time.sleep(.04)
                continue
            code = self.d.js("return document.querySelector('#code').value")
            m = re.search(r"\b([a-z])(_+)\b", code)
            if not m:
                return not bool(re.search(r"\b[a-z]+_+\b", code))
            target = next((w for w in words if w.startswith(m.group(1))
                           and len(w) == len(m.group(0))), None)
            if not target:
                return False
            start = m.start()
            self.d.js("const t=document.querySelector('#code'); t.focus();"
                      "t.setSelectionRange(arguments[0],arguments[0]);", start + len(m.group(1)))
            for ch in target[len(m.group(1)):]:
                self.d.send("#code", ch)
                time.sleep(.05)
        return False

    def close_pops(self):
        self.d.js("document.body.dispatchEvent(new PointerEvent('pointerdown',{bubbles:true}));")
        time.sleep(.2)


def answer_for(kid, key):
    if key == "7":
        return planet.UNCHARTED_REFERENCE, None
    found = planet.find_site(key)
    variant = planet.variant_index(kid.pid, found[2])
    return planet.answer_for(key, variant), variant


def play_route(kid, keys):
    for key in keys:
        code, variant = answer_for(kid, key)
        if not code:
            kid.fail(f"no answer for {key}")
            continue
        print(f"\n-- {key} {planet.find_site(key)[2]['name']} (variant {variant}) --")
        if not kid.open(key):
            continue
        info = kid.run_win(key, code)
        if not info:
            continue
        if key == "8a":
            kid.check(info["jumps"] > 0, "8A replays the jump")
        if key == "14a":
            kid.check(info["beams"] > 0, "14A replays the laser beam")
        if key == "15a":
            kid.check(info["delivered"], "15A brings samples home")
        if key == "7":
            kid.check("planets!" in info["title"], "Uncharted's card counts the planets",
                      info["title"])
            kid.check("reached" in info["sub"], "Uncharted's card summarises the run",
                      info["sub"])


def main_route(kid):
    print("\n=== main route, 1366x768 ===")
    kid.check(not kid.d.js("return easyClass()"),
              "a class without easy mode is not easyClass()")
    kid.check("Scout" not in (kid.d.js("return document.querySelector('#code').placeholder") or ""),
              "the empty editor on the main route does not say to Scout first")

    # A miss, the same code again, the win, the ghost, and Next.
    kid.open("1a")
    first = kid.run_miss("1a", "south(2)\neast()\n", "1a-wrong")
    kid.check("samples still out" in first, "a miss says what happened", first[:160])
    same = kid.run_miss("1a", "south(2)\neast()\n", "1a-same-code")
    kid.check("Same code" in same, "the same code says 'Same code'", same[:160])
    info = kid.run_win("1a", planet.find_site("1a")[2]["reference"], close=False)
    if info:
        kid.check(info["ghost"] is not None, "the finished site has a record ghost")
        kid.check(any("Next level" in a for a in info["actions"]),
                  "the win card has Next level", json.dumps(info["actions"]))
        kid.check(bool(kid.d.js("return document.querySelector('#record').textContent")),
                  "the class record is named on the map")
        # Watch again: the record ghost drives its route with this replay.
        kid.d.js("const b=[...document.querySelectorAll('#celeActions button')]"
                 ".find(e=>/Watch again/.test(e.innerText)); if (b) b.click();")
        time.sleep(1.0)
        kid.shot("1a-ghost")
        kid.check_page("1a ghost")
        kid.close_win()

    # Back for more stars: pick a finished level that still has a star to earn.
    state = get(kid.base + f"/planet/state?id={kid.pid}")
    back_key = next((s["key"] for z in state["zones"] for s in z["sites"]
                     if s["solved"] is not None and not all(s["stars"]) and s["key"] in BONUS),
                    None)
    if back_key:
        kid.open(back_key)
        back = kid.d.js("return document.querySelector('#bannerText').innerText")
        kid.check("Back for more stars" in back, "a finished level offers the missing-star hint",
                  back[:220])
        info = kid.run_win(back_key, BONUS[back_key], close=False)
        if info:
            kid.check(info["stars"][1], "the detour earns the missing star", json.dumps(info["stars"]))
            next_key = kid.click_win_action("Next level")
            kid.check(next_key is not None, "Next level opens the next site", next_key)
    else:
        kid.note("every finished site already has all its stars; no back-for-more check")

    # Report levels: a wrong number, then the measured one.
    kid.open("2a")
    wrong = kid.run_miss("2a", "east()\nreport(3)\n", "2a-wrong-number")
    kid.check("Not quite" in wrong or "different" in wrong,
              "a wrong number gets the measurement tip", wrong[:200])
    code, _ = answer_for(kid, "2a")
    kid.run_win("2a", code)

    # Every level of one zone: Ice Field (2A above, then 2B and 2C).
    play_route(kid, ["2b", "2c"])

    # First level of every remaining zone (6A was handled above).
    play_route(kid, ["3a", "4a", "5a", "7a", "8a", "9a", "10a",
                     "11a", "12a", "13a", "14a", "15a", "16a"])

    # Uncharted: the full answer, then a partial run whose card has to say
    # what stopped the other planets.
    kid.open("7")
    kid.run_win("7", planet.UNCHARTED_REFERENCE)
    kid.open("7")
    info = kid.run_win("7", UNCHARTED_PARTIAL)
    if info:
        kid.check(info["title"].strip() == "2 of 5 planets!", "the partial Uncharted card counts 2 planets",
                  info["title"])
        kid.check("ran flat" in info["sub"] or "fell in a crater" in info["sub"],
                  "the partial Uncharted card names what stopped them", info["sub"])
        kid.check(any("Watch again" in a for a in info["actions"]),
                  "the Uncharted card has Watch again", json.dumps(info["actions"]))
        kid.check(not kid.d.js("return document.querySelector('#prevSite').disabled"),
                  "the Uncharted site has a previous level")
        kid.check(kid.d.js("return document.querySelector('#nextSiteButton').disabled"),
                  "the Uncharted site has no next level")


def second_student(kid):
    print("\n=== second student, 1280x720 ===")
    kid.check(not kid.d.js("return easyClass()"),
              "easy mode is still off for the second student")
    state = get(kid.base + f"/planet/state?id={kid.pid}")
    sites = [s for z in state["zones"] for s in z["sites"]]
    before_solar = [s["key"] for s in sites if s["open"] and s["solved"] is None
                    and s["key"] in planet.SITE_ORDER
                    and planet.SITE_ORDER.index(s["key"]) < planet.SITE_ORDER.index("5a")]
    key = next((k for k in ("1b2", "1b1", "1b") if k in before_solar), None)
    if not key:
        kid.note("no open unsolved level before Solar Valley to scout")
        return
    print(f"\n-- scouting {key} at 1280x720 --")
    if not kid.open(key):
        return
    kid.check(not kid.d.js("return easyClass()"),
              "the main route still does not call itself easy mode")
    found = planet.find_site(key)
    moves = expand(found[2]["reference"])
    kid.scout(moves)
    kid.shot(f"{key}-scout")
    kid.d.click("#scoutCode")
    time.sleep(.5)
    kid.check(kid.d.js("return !document.querySelector('#scoutCode').hidden"),
              "Use as code stays available before Solar Valley")
    code = kid.d.js("return document.querySelector('#code').value")
    kid.check(bool(re.search(r"\b[a-z]+_+\b", code)), "Use as code leaves words to finish", code[:120])
    kid.check(kid.fill_blanks(), "the blanks can be typed in", code[:120])
    kid.check(kid.d.js("return gapAt() < 0"), "no unfinished word is left")
    info = kid.run_win(key, kid.d.js("return document.querySelector('#code').value"))
    if info:
        kid.check(info["card"][1] >= 0 and info["card"][3] <= 720,
                  "the win card fits 1280x720", json.dumps(info["card"]))

    # Hints: two misses make the button glow and "Get a hint" opens a card.
    state = get(kid.base + f"/planet/state?id={kid.pid}")
    unsolved = [s["key"] for z in state["zones"] for s in z["sites"]
                if s["open"] and s["solved"] is None and s["key"] in planet.SITE_ORDER
                and s["key"] != "7"]
    hint_key = next((k for k in ("1c", "2a", "3a", "3a1") if k in unsolved), None)
    if hint_key and kid.open(hint_key):
        kid.run_miss(hint_key, "wait()\n", f"{hint_key}-miss-1")
        kid.run_miss(hint_key, "wait(2)\n", f"{hint_key}-miss-2")
        kid.check("Get a hint" in kid.d.js("return document.querySelector('#radioButton small').textContent"),
                  "two misses make the Hints button say Get a hint")
        kid.d.click("#radioButton")
        kid.wait("return !document.querySelector('#radioPop').hidden", 8, "the hints card")
        time.sleep(.2)
        kid.check_page("hints card")
        pop = kid.d.js("""const p=document.querySelector('#radioPop'),r=p.getBoundingClientRect();
          return {rect:[r.left,r.top,r.right,r.bottom],vw:innerWidth,vh:innerHeight,
                  buttons:[...p.querySelectorAll('button')].map(b=>b.innerText)}""")
        kid.check(pop["rect"][1] >= 0 and pop["rect"][3] <= pop["vh"] + 1,
                  "the hints card fits the screen", json.dumps(pop["rect"]))
        kid.check(all(a.strip() for a in pop["buttons"]), "the hints card buttons have words",
                  json.dumps(pop["buttons"]))
        kid.shot(f"{hint_key}-hints")
        if not kid.d.js("return document.querySelector('#hintButton').hidden"):
            kid.d.click("#hintButton")
            time.sleep(.5)
            kid.check(bool(kid.d.js("return document.querySelector('#hints').innerText").strip()),
                      "asking for a hint adds it to the card")
            kid.shot(f"{hint_key}-hint-open")
        kid.close_pops()

    if args_stuck:
        stuck_flows(kid)


args_stuck = False


def stuck_flows(kid):
    """Only with --stuck: wait for and drive Build it together and Skip."""
    print("\n-- stuck help (slow) --")
    state = get(kid.base + f"/planet/state?id={kid.pid}")
    current = state["current"]
    if not kid.open(current):
        return
    # Enough different misses for the server's own thresholds.
    for n in range(24):
        actions = kid.d.js("return [...document.querySelectorAll('#bannerActions button')].map(b=>b.innerText)")
        if any("Build it together" in b or "Skip for now" in b for b in actions):
            break
        kid.run_miss(current, f"wait({n + 1})\n", f"stuck-miss-{n + 1}")
    # A short wait only: the normal wait has usually passed by now.
    end = time.time() + 100
    while time.time() < end:
        actions = kid.d.js("return [...document.querySelectorAll('#bannerActions button')].map(b=>b.innerText)")
        if any("Build it together" in b for b in actions):
            break
        time.sleep(1)
    buttons = kid.d.js("return [...document.querySelectorAll('#bannerActions button')].map(b=>b.innerText)")
    if any("Build it together" in b for b in buttons):
        kid.d.js("[...document.querySelectorAll('#bannerActions button')]"
                 ".find(b=>/Build it together/.test(b.innerText)).click()")
        try:
            kid.wait("return !!(site && site.together)", 10, "Build it together")
        except RuntimeError:
            # A shortened test server can offer the button a moment before the
            # server's own wait has passed; the page correctly says to try a
            # little more.  Don't call that an app failure in this optional path.
            said = kid.d.js("return document.querySelector('#bannerText').innerText")
            if "Try it your own way" in said:
                kid.note("Build it together was offered just before the server's wait passed")
            else:
                kid.fail("Build it together did not start", said[:200])
        else:
            kid.check(kid.fill_blanks(), "the built answer can be typed in")
            info = kid.run_win(current, kid.d.js("return document.querySelector('#code').value"))
            if info:
                kid.check(info["stars"] == [True, False, False],
                          "building together earns the first star only", json.dumps(info["stars"]))
    else:
        kid.note("Build it together was not open at this threshold")
    kid.close_win()
    # Skip: skip is offered on the site the student is up to, so use the
    # server's current site (the build just opened the next one).
    state = get(kid.base + f"/planet/state?id={kid.pid}")
    skip_key = state["current"]
    if skip_key == "7" or skip_key not in planet.SITE_ORDER:
        skip_key = next((s["key"] for z in state["zones"] for s in z["sites"]
                         if s["open"] and s["solved"] is None and s["key"] in planet.SITE_ORDER
                         and s["key"] != "7"), None)
    if skip_key and kid.open(skip_key):
        for n in range(24):
            if kid.d.js("return !!site.can_skip"):
                break
            kid.run_miss(skip_key, f"wait({n + 1})\n", f"skip-miss-{n + 1}")
        buttons = kid.d.js("return [...document.querySelectorAll('#bannerActions button')].map(b=>b.innerText)")
        if any("Skip for now" in b for b in buttons):
            before = skip_key
            kid.d.js("[...document.querySelectorAll('#bannerActions button')]"
                     ".find(b=>/Skip for now/.test(b.innerText)).click()")
            kid.wait("return site && site.key !== arguments[0]", 20, "Skip to open the next site", before)
            time.sleep(.4)
            kid.check(kid.d.js("return site.key !== arguments[0]", before),
                      "Skip for now opens the next site")
            kid.check(bool(kid.d.js("return [...document.querySelectorAll('.toast')]"
                                    ".some(t=>/can wait/.test(t.innerText))")),
                      "Skip says the level can wait")
            kid.shot("after-skip")
        else:
            kid.note("Skip for now was not open at this threshold")


def main():
    global args_stuck
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--base", default="http://127.0.0.1:8799")
    parser.add_argument("--shots", default=os.path.join(ROOT, ".kidshunt-shots", "route-e2e"))
    parser.add_argument("--student-a", default="Route Test A",
                        help="the student whose main route is unlocked")
    parser.add_argument("--student-b", default="Route Test B")
    parser.add_argument("--stuck", action="store_true", help="also test Build it together and Skip")
    args = parser.parse_args()
    args_stuck = args.stuck
    base = args.base.rstrip("/")
    try:
        with urllib.request.urlopen(base + "/planet", timeout=10):
            pass
    except Exception as exc:
        raise SystemExit(f"{base} is not answering: {exc}")
    print(f"Strange Planet main-route hunt on {base}")
    print(f"Screenshots: {args.shots}")

    a = None
    b = None
    try:
        a = Kid(base, args.student_a, 1366, 768, args.shots, "a")
        main_route(a)
        b = Kid(base, args.student_b, 1280, 720, args.shots, "b")
        second_student(b)
    finally:
        if a:
            a.d.close()
        if b:
            b.d.close()

    print("\n" + "=" * 60)
    if REPORT.failures:
        print(f"{len(REPORT.failures)} FAILURE(S):")
        for row in REPORT.failures:
            print(" -", row)
        return 1
    print(f"All checks passed ({len(REPORT.notes)} notes).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
