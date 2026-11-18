#!/usr/bin/env python3
"""A real-browser walk through the Rover Farm, the way the class plays it.

This is a tool, not a test: start a server of your own, then run it, e.g.

    MAZE_PORT=8793 MAZE_STATE_FILE=/tmp/farm-state.json python3 server.py &
    python3 tools/e2e_planet_farm.py --base http://127.0.0.1:8793 \
        --admin-key KEY --scenario all

It joins its own students ("E2E Ada ...", one per scenario), drives Chromium at 1366x768 and
1280x720, takes screenshots, and prints every browser console error and any
layout problem it can see.  Screenshots go to --shots (default: farm-e2e-shots).
"""
import argparse
import json
import os
import sys
import time
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import wd  # the worktree's small chromedriver helper


def http_json(url, data=None):
    req = urllib.request.Request(url, None if data is None else json.dumps(data).encode(),
                                 {"Content-Type": "application/json"})
    return json.load(urllib.request.urlopen(req, timeout=20))


class Report:
    def __init__(self):
        self.console = []
        self.layout = []
        self.notes = []
        self.fail = []

    def logs(self, driver, where):
        for row in driver.logs():
            text = row.get("message", "")
            # Chrome's own noise, and failed favicon-ish requests, is not the game.
            if "favicon" in text:
                continue
            self.console.append((where, row.get("level"), text[:400]))
            if row.get("level") == "SEVERE":
                self.fail.append(f"console error at {where}: {text[:300]}")

    def check_layout(self, driver, where):
        found = driver.js(r"""
            const out = [];
            const name = el => (el.id ? '#' + el.id : el.className ? '.' + String(el.className).split(' ')[0] : el.tagName);
            for (const el of document.querySelectorAll('body *')) {
              const cs = getComputedStyle(el);
              if (cs.display === 'none' || cs.visibility === 'hidden' || cs.opacity === '0') continue;
              const r = el.getBoundingClientRect();
              if (r.width < 1 || r.height < 1) continue;
              if (r.right > innerWidth + 1 || r.left < -1 || r.bottom > innerHeight + 1 || r.top < -1) {
                if (el.closest('.result') || el.closest('.dialog') || el.closest('.card-body') || el.closest('.toast') || el.closest('.gutter')) continue;
                out.push({el: name(el), right: Math.round(r.right), left: Math.round(r.left),
                          bottom: Math.round(r.bottom), top: Math.round(r.top), text: (el.innerText || '').slice(0, 60)});
              }
              if (el.scrollWidth > el.clientWidth + 2 && cs.overflowX === 'hidden' &&
                  cs.textOverflow !== 'ellipsis' && (el.innerText || '').trim()) {
                out.push({el: name(el), cut: 'x', scroll: el.scrollWidth, client: el.clientWidth,
                          text: (el.innerText || '').slice(0, 60)});
              }
            }
            return out.slice(0, 12);
        """)
        if found:
            self.layout.append((where, found))


REPORT = Report()


class Kid:
    """One student's browser, and the small set of things a kid presses."""

    def __init__(self, base, name, width=1366, height=768, report=None):
        self.base = base.rstrip("/")
        self.name = name
        self.report = report or REPORT
        self.width, self.height = width, height
        self.id = http_json(self.base + "/join", {"name": name})["id"]
        self.d = wd.new(width, height)
        self.d.go(self.base + "/planet")
        self.d.js("localStorage.setItem('mazeId', arguments[0]);"
                  "for (const k of Object.keys(localStorage)) if (k.startsWith('farmCode:')) localStorage.removeItem(k);"
                  "for (const k of ['farmSpeed', 'planetCalm', 'planetBig', 'planetMuted']) localStorage.removeItem(k);",
                  self.id)
        self.go_farm()

    def go_farm(self):
        self.d.go(self.base + "/planet/farm")
        self.d.wait("return document.getElementById('app') && !document.getElementById('app').hidden", 20,
                    "the farm page")
        self.check("load")

    def close(self):
        self.d.close()

    def check(self, where):
        if self.report:
            self.report.logs(self.d, f"{self.name}:{where}")
            self.report.check_layout(self.d, f"{self.name}:{where}")

    def shot(self, path):
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        self.d.shot(path)

    # ---- reading the page -------------------------------------------------
    def state(self):
        return self.d.js("""return {
            day: farm && farm.day, job: farm && farm.job, order: farm && farm.order,
            coins: farm && farm.coins, orders: farm && farm.orders, decor: farm && farm.decor,
            w: farm && farm.w, h: farm && farm.h,
            autoHidden: document.getElementById('autoLabel').hidden,
            autoOn: document.getElementById('auto').checked,
            give: !document.getElementById('sample').hidden && !document.getElementById('sampleFoot').hidden,
            sampleHidden: document.getElementById('sample').hidden,
            result: document.getElementById('result').innerText,
            jobCard: document.getElementById('job').innerText,
            code: document.getElementById('code').value,
            closed: !document.getElementById('closed').hidden,
            busy: !!busy, playing: !!play, night: !!night
        }""")

    def idle(self, timeout=40):
        self.d.wait("return !!farm && !busy && !play && !night", timeout, "the day to finish")

    def wait_true(self, script, timeout=10):
        end = time.time() + timeout
        while time.time() < end:
            if self.d.js(script):
                return True
            time.sleep(.08)
        return False

    # ---- pressing things ---------------------------------------------------
    def run(self, wait=True):
        self.d.click("#runButton")
        if wait:
            self.d.wait("return !!play || !busy", 10, "the day to start")
            self.idle()

    def buy(self, kind, key):
        self.d.click("#shopButton")
        self.d.wait("return !document.getElementById('shop').hidden", 5, "the shop")
        css = f'.buy[data-kind="{kind}"][data-key="{key}"]'
        if not self.d.exists(css):
            raise AssertionError(f"shop has no {kind}/{key}")
        disabled = self.d.js("return document.querySelector(arguments[0]).disabled", css)
        if disabled:
            raise AssertionError(f"cannot afford {kind}/{key}")
        self.d.click(css)
        self.d.wait("return !!farm", 10, "the buy")
        self.d.wait("return !!farm && !!farm.shop", 5)
        self.d.click("#shopClose")
        self.d.wait("return document.getElementById('shop').hidden", 5, "the shop to close")

    def type_code(self, text):
        """Type into the editor with real key presses, including indentation.

        Enter adds the Python indent the page itself adds, and one Backspace
        removes four spaces (the page's own rule), so a card's code can be
        typed exactly as it is on the card.
        """
        d = self.d
        d.js("const t=document.getElementById('code'); t.focus();"
             "t.setSelectionRange(0, t.value.length); t.scrollTop = 0;")
        lines = text.rstrip("\n").split("\n")
        indent = 0
        previous = ""
        for n, raw in enumerate(lines):
            target = len(raw) - len(raw.lstrip(" "))
            body = raw.strip()
            if n:
                d.send("#code", "\n")
                auto = indent + (4 if previous.rstrip().endswith(":") else 0)
                if auto > target:
                    for _ in range((auto - target) // 4):
                        d.send("#code", "\b")
                elif target > auto:
                    d.send("#code", " " * (target - auto))
                indent = target
            d.send("#code", body)
            previous = raw
        self.d.wait("return !document.getElementById('ac') || document.getElementById('ac').hidden", 2)
        left = self.d.js("return document.getElementById('code').scrollLeft")
        self.expect(left == 0, f"the code box stayed scrolled sideways after typing: {left}px")
        self.check("typed")

    # ---- checks a kid can see ---------------------------------------------
    def expect(self, condition, message, where="expect"):
        if not condition:
            raise AssertionError(message)
        if self.report:
            self.report.logs(self.d, where)

    def open_and_shot(self, css, path, wait=None):
        self.d.click(css)
        if wait:
            self.d.wait(wait, 8, css)
        time.sleep(.35)
        self.shot(path)
        self.check(os.path.basename(path))


# ---- Scenario A: type every card, buy what it says, then orders and a crate ----
RUN_TAG = str(int(time.time()))

BUYS = {   # job number -> what its card says to buy
    5: [("upgrade", "field")],
    7: [("upgrade", "battery")],
    9: [("crop", "carrot")],
    11: [("upgrade", "memory")],
}


def scenario_a(base, shots):
    kid = Kid(base, f"E2E Ada {RUN_TAG}")
    r = kid.report
    print("A: joined as", kid.id)
    try:
        for job_no in range(1, 16):
            st = kid.state()
            job = st["job"]
            print(f"  job {job['n']} {job['title']!r} day {st['day']} coins {st['coins']}")
            assert job["n"] == job_no, (job_no, job)
            kid.shot(os.path.join(shots, f"a-job{job_no:02d}-1366.png"))
            if job_no in (13, 14, 15):
                ov = kid.d.js("const p=document.querySelector('#sampleCode');"
                              "return p && !document.getElementById('sample').hidden ?"
                              " {sw:p.scrollWidth, cw:p.clientWidth} : null")
                kid.expect(ov and ov["sw"] <= ov["cw"] + 2,
                           f"Type this cuts off a long line at job {job_no}: {ov}")
            # A kid whose code is already right (the first job) just presses Run.
            if job["code"] and job_no > 1:
                kid.type_code(job["code"])
            if job_no in (5, 7, 9, 11):
                for kind, key in BUYS[job_no]:
                    old = kid.state()["job"]["n"]
                    kid.buy(kind, key)
                    kid.expect(kid.state()["job"]["n"] > old,
                               f"buying {key} did not finish job {old}")
                kid.check(f"buy-{job_no}")
                continue
            before = st["job"]["n"] if st["job"] else 99
            for attempt in range(8):
                kid.run()
                st = kid.state()
                if not st["job"] or st["job"]["n"] > before:
                    break
            kid.expect(not st["job"] or st["job"]["n"] > before,
                       f"job {job_no} never finished; result: {st['result']!r}")
        kid.shot(os.path.join(shots, "a-jobs-done-1366.png"))
        print("A: all 15 jobs done, coins", kid.state()["coins"])
        # Some real shop buys for the yard.
        for kind, key in (("decor", "sign"), ("decor", "tree")):
            try:
                kid.buy(kind, key)
            except AssertionError as e:
                print("A: shop buy skipped:", e)
        # Orders: the last card's berry program fills berry orders. Stop Auto
        # only to press the card's own 🔄 Different order, then carry on; the
        # third order brings a crate.
        def open_crate_if_shown():
            if not kid.d.exists("#crate:not([hidden])"):
                return False
            kid.shot(os.path.join(shots, "a-crate.png"))
            kid.d.click("#crateOpen")
            time.sleep(.3)
            kid.d.click("#crateOpen")
            kid.wait_true("return document.getElementById('crate').hidden", 6)
            kid.check("crate")
            return True

        def auto_off():
            open_crate_if_shown()
            if kid.state()["autoOn"]:
                kid.d.click("#auto")
                kid.wait_true("return !document.getElementById('auto').checked", 5)
            # A crate can open just as Auto is turned off: the day waits there.
            end = time.time() + 20
            while time.time() < end:
                if open_crate_if_shown():
                    continue
                if kid.d.js("return !!farm && !busy && !play && !night"):
                    return
                time.sleep(.1)
            raise AssertionError("Auto did not stop; the page stayed busy")

        def auto_on():
            if not kid.state()["autoOn"]:
                kid.d.click("#auto")
                kid.wait_true("return document.getElementById('auto').checked", 5)

        def berry_order():
            auto_off()
            for _ in range(20):
                st = kid.state()
                if not st["order"] or st["order"]["crop"] == "berry":
                    return
                old_crop, old_need = st["order"]["crop"], st["order"]["need"]
                kid.d.click("#orderSkip")
                kid.expect(kid.wait_true(
                    f"const o=farm.order; return o && (o.crop !== {old_crop!r} || o.need !== {old_need});", 6),
                    "the Different order button did not change the order")
                kid.idle()

        berry_order()
        auto_on()
        for _ in range(400):
            st = kid.state()
            if st["orders"] >= 3:
                break
            if open_crate_if_shown():
                continue
            if st["order"] and st["order"]["crop"] != "berry":
                berry_order()
                auto_on()
                continue
            time.sleep(.2)
        open_crate_if_shown()
        auto_off()
        st = kid.state()
        kid.shot(os.path.join(shots, "a-orders-1366.png"))
        kid.expect(st["orders"] >= 3, f"only {st['orders']} orders filled")
        kid.expect(any(d["key"] not in ("sign", "tree") for d in st["decor"]),
                   "no crate thing in the yard")
        print("A: orders", st["orders"], "decor", [d["key"] for d in st["decor"]])
        # A shop buy pressed while a day is playing must survive the day's reply.
        kid.d.click("#runButton")
        kid.wait_true("return !!play", 5)
        kid.d.click("#shopButton")
        kid.wait_true("return !document.getElementById('shop').hidden", 5)
        css = '.buy[data-kind="upgrade"][data-key="field"]'
        if kid.d.exists(css) and not kid.d.js("return document.querySelector(arguments[0]).disabled", css):
            kid.d.click(css)
            kid.wait_true("return farm.w > 3", 5)
            bought_w = kid.state()["w"]
            kid.idle(60)
            kid.expect(kid.state()["w"] == bought_w,
                       f"a buy during a day was undone: {bought_w} -> {kid.state()['w']}")
            kid.shot(os.path.join(shots, "a-buy-during-day.png"))
            kid.d.click("#shopClose")
            kid.wait_true("return document.getElementById('shop').hidden", 5)
        else:
            print("A: no affordable field upgrade to race with")
        kid.check("end-a")
    finally:
        kid.close()


# ---- Scenario B: only Run and Auto, with the starting code ----
def scenario_b(base, shots):
    kid = Kid(base, f"E2E Bo {RUN_TAG}", width=1280, height=720)
    print("B: run-only kid", kid.id)
    try:
        st = kid.state()
        kid.expect(st["autoHidden"], "Auto is visible on job 1")
        kid.shot(os.path.join(shots, "b-job1-1280.png"))
        same = []
        for n in range(6):
            kid.run()
            st = kid.state()
            same.append({"day": st["day"], "job": st["job"]["n"], "autoHidden": st["autoHidden"],
                         "give": st["give"], "result": st["result"]})
        kid.shot(os.path.join(shots, "b-stuck-1280.png"))
        print("B:", [(x["day"], x["job"], x["autoHidden"], x["give"]) for x in same])
        kid.expect(same[-1]["job"] <= 3, "Run-only unexpectedly left the first three jobs")
        kid.expect(same[-1]["autoHidden"], "Auto showed before job 4")
        kid.expect(same[-1]["give"], "no Put this in my code after repeated misses")
        kid.expect("Same code" in st["result"], "the result does not say the code needs changing")
        kid.expect("📋 Job: 0 of 2 berries picked today" in st["result"],
                   "the result does not say how close the job came")
        kid.expect(not st["sampleHidden"], "the Type this panel did not open")
        kid.check("end-b")
    finally:
        kid.close()


# ---- Scenario C: press Put this in my code for each job ----
def scenario_c(base, shots):
    kid = Kid(base, f"E2E Cy {RUN_TAG}")
    print("C: put-this kid", kid.id)
    try:
        for job_no in range(1, 16):
            st = kid.state()
            job = st["job"]
            assert job["n"] == job_no, (job_no, job)
            if job_no in (5, 7, 9, 11):
                for kind, key in BUYS[job_no]:
                    kid.buy(kind, key)
                continue
            if job_no == 1 or not job["code"]:
                before = (job["n"] if job else 99)
                for _ in range(4):
                    kid.run()
                    if (kid.state()["job"] or {}).get("n", 99) > before:
                        break
                continue
            # Miss once or twice until the page offers the code.
            guard = 0
            while not kid.state()["give"] and guard < 4:
                guard += 1
                before = (kid.state()["job"] or {}).get("n", 99)
                kid.run()
                if not kid.state()["job"] or kid.state()["job"]["n"] > before:
                    break
            st = kid.state()
            if not st["job"] or st["job"]["n"] > job_no:
                continue
            if not st["give"]:
                raise AssertionError(f"job {job_no} never offered Put this: {st['result']!r}")
            if job_no == 2:
                kid.shot(os.path.join(shots, "c-put-this-1366.png"))
            want = kid.d.js("return farm.job.code")
            kid.d.click("#sampleGive")
            time.sleep(.2)
            got = kid.d.js("return document.getElementById('code').value")
            kid.expect(got == want, f"Put this wrote {got!r}, wanted {want!r}")
            scrolled = kid.d.js("const t=document.getElementById('code');"
                                " return {left:t.scrollLeft, top:t.scrollTop}")
            kid.expect(scrolled == {"left": 0, "top": 0},
                       f"Put this left the code box scrolled: {scrolled}")
            kid.check(f"put-{job_no}")
            before = kid.state()["job"]["n"]
            for _ in range(8):
                kid.run()
                now = kid.state()["job"]
                if not now or now["n"] > before:
                    break
            now = kid.state()["job"]
            kid.expect(not now or now["n"] > before, f"job {job_no} not done after Put this")
        kid.shot(os.path.join(shots, "c-jobs-done-1280.png"))
        kid.check("end-c")
    finally:
        kid.close()


# ---- Scenario D: the mistakes kids make ----
def scenario_d(base, shots):
    kid = Kid(base, f"E2E Di {RUN_TAG}")
    print("D: mistakes kid", kid.id)
    try:
        cases = [
            ("missing bracket", "harvest", "fix"),
            ("unknown cash", 'cash("67")', None),
            ("plant no quotes", "plant(berry)", None),
            ("endless while", "while True:\n    east()", None),
            ("forty lines", "\n".join(["wait()"] * 40), None),
            ("print spam", 'for i in range(12):\n    print("hi hi hi")', None),
        ]
        for name, code, _ in cases:
            before = kid.state()
            kid.type_code(code)
            if name == "missing bracket":
                kid.shot(os.path.join(shots, "d-ac-typing-1366.png"))
            kid.run()
            after = kid.state()
            kid.shot(os.path.join(shots, f"d-{name.replace(' ', '-')}-1366.png"))
            print(f"  {name}: day {before['day']}->{after['day']} result={after['result'][:180]!r}")
            kid.expect(after["day"] <= before["day"] + 1, f"{name}: more than one day used")
            kid.expect(after["result"], f"{name}: empty result")
        # A real key-press type that opens autocomplete, to see the list.
        kid.type_code("harv")
        kid.d.js("const t=document.getElementById('code'); t.focus(); t.setSelectionRange(4,4)")
        kid.d.send("#code", "")
        kid.shot(os.path.join(shots, "d-autocomplete-1366.png"))
        kid.check("end-d")
    finally:
        kid.close()


# ---- UI: visit, help, sound, calm, speed, reload, teacher off/on ----
def scenario_ui(base, shots, admin_key):
    friend = f"E2E Friend {RUN_TAG}"[:20]
    other = Kid(base, friend)
    try:
        # A farm with a day and something in its yard, so it can be visited and clicked.
        other.type_code('east()\nharvest()\neast()\nharvest()')
        other.run()
        other.type_code('harvest()\nplant("berry")\neast()\nharvest()\nplant("berry")\neast()\n'
                        'harvest()\nplant("berry")')
        other.run()
        if other.state()["coins"] >= 10:
            other.buy("decor", "sign")
        other.check("friend")
    finally:
        other.close()
    kid = Kid(base, f"E2E Ui {RUN_TAG}")
    print("UI: kid", kid.id)
    try:
        kid.d.click("#visitButton")
        kid.d.wait("return !document.getElementById('visit').hidden", 5, "the visit card")
        time.sleep(.3)
        kid.shot(os.path.join(shots, "ui-visit-empty-1366.png"))
        buttons = kid.d.js("return [...document.querySelectorAll('#friends button')].map(b=>b.textContent)")
        kid.expect(any(friend in b for b in buttons), f"classmate not listed: {buttons}")
        kid.d.js("const b=[...document.querySelectorAll('#friends button')]"
                 ".find(x => x.textContent === arguments[0]); if (b) b.click();", friend)
        kid.d.wait("return !document.getElementById('visitYardBox').hidden", 8, "the visit yard")
        time.sleep(.4)
        kid.shot(os.path.join(shots, "ui-visit-farm-1366.png"))
        # The guide says clicking a thing in a yard makes it say something.
        hit = kid.d.js("""const cv=document.getElementById('visitYard');
            if (!visitView || !visitView.hits.length) return null;
            const h=visitView.hits[0], b=cv.getBoundingClientRect(), key=h.d.key;
            cv.dispatchEvent(new MouseEvent('click', {clientX:b.left+h.cx, clientY:b.top+h.cy, bubbles:true}));
            return {key, wiggle: wiggles[key] || 0};""")
        kid.expect(hit and hit["wiggle"], f"clicking a yard thing did nothing: {hit}")
        time.sleep(.2)
        kid.shot(os.path.join(shots, "ui-visit-hello-1366.png"))
        kid.check("visit")
        kid.d.click("#visitClose")

        kid.d.click("#helpButton")
        kid.d.wait("return !document.getElementById('help').hidden", 5, "help")
        time.sleep(.3)
        kid.shot(os.path.join(shots, "ui-help-1366.png"))
        kid.d.click("#calmBox")
        calm = kid.d.js("return {on: document.body.classList.contains('calm'), stored: localStorage.getItem('planetCalm')}")
        kid.expect(calm == {"on": True, "stored": "1"}, f"calm mode did not stick: {calm}")
        kid.d.click("#bigBox")
        kid.shot(os.path.join(shots, "ui-help-big-1366.png"))
        kid.d.click("#helpClose")

        before = kid.d.text("#muteButton")
        kid.d.click("#muteButton")
        after = kid.d.text("#muteButton")
        kid.expect(before != after, "sound button did not change")
        speeds = []
        for _ in range(3):
            kid.d.click("#speedButton")
            speeds.append(kid.d.text("#speedButton"))
        print("UI: sound", before, "->", after, "speeds", speeds)
        kid.expect(speeds == ["2×", "4×", "1×"], f"speed button cycles {speeds}")

        # Reload in the middle of a day. The typed code is kept and a half day
        # does not leave the page broken.
        kid.type_code("for i in range(3):\n    harvest()\n    east()")
        kid.d.click("#runButton")
        kid.d.wait("return !!play", 5, "playback")
        time.sleep(.15)
        kid.d.go(base + "/planet/farm")
        kid.d.wait("return document.getElementById('app') && !document.getElementById('app').hidden", 20)
        kid.d.wait("return !!farm && !busy", 20)
        kept = kid.d.js("return {calm: document.body.classList.contains('calm'),"
                        " big: document.body.classList.contains('big'),"
                        " speed: localStorage.getItem('farmSpeed')}")
        kid.expect(kept["calm"] and kept["big"], f"calm/big settings were lost on reload: {kept}")
        kid.shot(os.path.join(shots, "ui-reload-1366.png"))
        kid.check("reload")

        if admin_key:
            kid.d.click("#shopButton")
            kid.d.wait("return !document.getElementById('shop').hidden", 5, "the shop")
            http_json(base + "/admin", {"key": admin_key, "action": "planet_farm", "on": False})
            kid.d.wait("return !document.getElementById('closed').hidden", 15, "the farm to close")
            kid.shot(os.path.join(shots, "ui-closed-1366.png"))
            kid.expect(kid.d.js("return document.getElementById('app').hidden"), "app still shown when closed")
            kid.expect(kid.d.js("return document.getElementById('shop').hidden"), "shop stayed open over the closed page")
            http_json(base + "/admin", {"key": admin_key, "action": "planet_farm", "on": True})
            reopened = kid.d.wait("return !document.getElementById('app').hidden", 10)
            kid.shot(os.path.join(shots, "ui-reopened-1366.png"))
            kid.expect(reopened, "the farm did not come back when the teacher turned it on again")
            kid.check("reopen")
    finally:
        kid.close()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="http://127.0.0.1:8793")
    ap.add_argument("--admin-key", default=os.environ.get("FARM_ADMIN_KEY", ""))
    ap.add_argument("--scenario", default="all", help="all or a comma list of a,b,c,d,ui")
    ap.add_argument("--shots", default="farm-e2e-shots")
    ap.add_argument("--tag", default=str(int(time.time())))
    args = ap.parse_args()
    global RUN_TAG
    RUN_TAG = args.tag
    run = set(args.scenario.split(",") if args.scenario != "all" else ["a", "b", "c", "d", "ui"])
    if args.admin_key:
        http_json(args.base.rstrip("/") + "/admin",
                  {"key": args.admin_key, "action": "planet_farm", "on": True})
    try:
        if "a" in run:
            scenario_a(args.base, args.shots)
        if "b" in run:
            scenario_b(args.base, args.shots)
        if "c" in run:
            scenario_c(args.base, args.shots)
        if "d" in run:
            scenario_d(args.base, args.shots)
        if "ui" in run:
            scenario_ui(args.base, args.shots, args.admin_key)
    finally:
        print("\n== console errors ==")
        for row in REPORT.console:
            print(*row)
        print("== layout problems ==")
        for where, rows in REPORT.layout:
            for row in rows:
                print(where, json.dumps(row))
        print("== failures ==")
        for row in REPORT.fail:
            print(row)
    if REPORT.fail:
        sys.exit(1)


if __name__ == "__main__":
    main()
