#!/usr/bin/env python3
"""Measure how smooth Draw and Code are on a slow school laptop.

It uses the same headless-Chromium (chromedriver, stdlib only) client as
tools/e2e_draw.py and the real typing from tools/e2e_coach.py, joins one
student, and then, at 1024x600 and 1366x768 with the page CPU throttled 4x:

  Draw
    * 40 click-by-click squares,
    * an Easy pen stroke (click, glide, click),
    * Fill on a 48 x 48 (Huge) page,
    * a 4-way Mirror + sparkle pen stroke,
    * switching frames in an 8-frame reel,
    * 20 Undos.
    Measured: click -> the square showing in the next painted frame, long
    tasks, frame times, and how long the page's own paint/snap/reel work takes.

  Code
    * a 12-line guided program typed one real key at a time (the typing guide
      is on, using e2e_coach's type_coach), then
    * Show time! for its 30-step show.
    Measured: key -> next painted frame (median/p95), long tasks, frame times
    on the stage.

The tool is not a unittest, so unittest will not pick it up as test_*.py.
Screenshots go under /tmp/<job>/ by default, never in the repo.

Usage (start the server first, on the port you were given):

    MAZE_PORT=8921 MAZE_STATE_FILE=/tmp/perf2-state.json python3 server.py
    python3 tools/perf_draw_code.py --port 8921 --phase before
    # ... change code, restart the server ...
    python3 tools/perf_draw_code.py --port 8921 --phase after
"""

import argparse
import base64
import json
import math
import os
import sys
import time
import traceback
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "tools"))
import pixel  # noqa: E402
from e2e_draw import (Driver, WebDriverError, start_blank, close_shelf, trim_shelf,  # noqa: E402
                      pick_tool, choose_colour, set_switch)
from e2e_coach import type_coach, focus_code  # noqa: E402


# ---------------------------------------------------------------------------
# HTTP helpers (the test student posts /pixel/news after /join)
# ---------------------------------------------------------------------------
def post(base, path, data, timeout=120):
    req = urllib.request.Request(base + path, data=json.dumps(data).encode(),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# Browser instrumentation: one classic-script global, checked for clashes
# ---------------------------------------------------------------------------
INJECT = r"""
return (() => {
  if (window.__pqPerf) return true;
  const p = window.__pqPerf = {
    frames: [], long: [], clicks: [], keys: [], work: {},
    on: false, last: 0, t0: 0,
    armed: false, pendingClick: null, keysOn: false, pendingKeys: []
  };
  let painting = 0;
  function tick(now) {
    if (p.on) {
      const dt = p.last ? now - p.last : 0;
      if (dt > 0) p.frames.push(dt);
      if (p.pendingKeys.length) {
        const t = performance.now();
        for (const k of p.pendingKeys) p.keys.push({ms: t - k.t, key: k.key});
        p.pendingKeys.length = 0;
      }
    }
    p.last = now;
    requestAnimationFrame(tick);
  }
  requestAnimationFrame(tick);
  try {
    new PerformanceObserver(list => {
      if (!p.on) return;
      for (const e of list.getEntries()) p.long.push(e.duration);
    }).observe({entryTypes: ["longtask"]});
  } catch (e) {}
  document.addEventListener("pointerdown", e => {
    if (!p.armed) return;
    p.pendingClick = {t: performance.now(), target: (e.target && (e.target.id || e.target.tagName)) || ""};
  }, true);
  document.addEventListener("keydown", e => {
    if (!p.keysOn || !e.target || e.target.id !== "code") return;
    p.pendingKeys.push({t: performance.now(), key: e.key});
  }, true);
  function timed(name, fn) {
    return function () {
      const t = performance.now();
      const out = fn.apply(this, arguments);
      if (p.on) {
        const ms = performance.now() - t;
        (p.work[name] || (p.work[name] = [])).push(ms);
      }
      return out;
    };
  }
  function wrap(name) {
    const orig = window[name];
    if (typeof orig !== "function" || orig.__pqTimed) return;
    const f = timed(name, orig);
    f.__pqTimed = true;
    window[name] = f;
  }
  for (const name of ["paintBoard", "paintThumb", "buildReel", "snap", "done", "restore",
                      "openFrame", "updateEditor", "paintCoach", "paintCode", "saveCode",
                      "setRunLine", "setBand", "placeBand", "syncScroll", "checkGuide",
                      "refreshButtons"]) wrap(name);
  // paintBoard is measured both as work and as "the square is showing".
  const origBoard = window.paintBoard;
  if (origBoard) {
    const board = function () {
      const t0 = performance.now();
      const out = origBoard.apply(this, arguments);
      const t1 = performance.now();
      if (p.on && p.pendingClick) {
        p.clicks.push({ms: t1 - p.pendingClick.t, work: t1 - t0,
                       target: p.pendingClick.target});
        p.pendingClick = null;
      }
      return out;
    };
    board.__pqTimed = true;
    window.paintBoard = board;
  }
  const PA = (typeof PixelArt !== "undefined") ? PixelArt : window.PixelArt;
  if (PA) {
    for (const name of ["flood", "decode", "encode"]) {
      if (typeof PA[name] === "function") PA[name] = timed("PixelArt." + name, PA[name]);
    }
  }
  window.__pqPerfReset = () => {
    p.frames.length = 0; p.long.length = 0; p.clicks.length = 0; p.keys.length = 0;
    p.work = {}; p.last = 0; p.t0 = performance.now(); p.on = true;
    p.armed = false; p.pendingClick = null; p.keysOn = false; p.pendingKeys.length = 0;
    window.__pqPerfSteps = 0;
    return true;
  };
  window.__pqPerfStop = () => {
    p.on = false;
    const work = {};
    for (const k of Object.keys(p.work)) work[k] = p.work[k].slice();
    return {wall: performance.now() - p.t0, frames: p.frames.slice(), long: p.long.slice(),
            clicks: p.clicks.slice(), keys: p.keys.slice(), work};
  };
  window.__pqPerfArmClick = () => {
    p.armed = true; p.pendingClick = null; p.clicks.length = 0; return true;
  };
  window.__pqPerfTakeClick = () => {
    if (!p.clicks.length) return null;
    const out = p.clicks[p.clicks.length - 1];
    p.clicks.length = 0; p.armed = false;
    return out;
  };
  window.__pqPerfArmKeys = on => { p.keysOn = !!on; p.pendingKeys.length = 0; return true; };
  window.__pqPerfWrapStage = () => {
    if (typeof stage === "undefined" || !stage || stage.__pqWrapped) return false;
    const orig = stage.play;
    stage.play = function (steps, options) {
      window.__pqPerfSteps = (steps || []).length;
      return orig.call(this, steps, options);
    };
    stage.__pqWrapped = true;
    return true;
  };
  return true;
})()
"""


def inject(d):
    if not d.js(INJECT):
        raise RuntimeError("could not inject the perf probe")
    ok = d.js('return !!window.__pqPerf && typeof window.__pqPerfReset === "function" && '
              'window.paintBoard.__pqTimed === true')
    if not ok:
        raise RuntimeError("the perf probe did not take: paintBoard is not wrapped")
    return True


def set_throttle(d, rate):
    d.request("POST", f"/session/{d.sid}/goog/cdp/execute",
              {"cmd": "Emulation.setCPUThrottlingRate", "params": {"rate": rate}})


def set_viewport(d, w, h):
    d.request("POST", f"/session/{d.sid}/goog/cdp/execute",
              {"cmd": "Emulation.setDeviceMetricsOverride",
               "params": {"width": w, "height": h, "deviceScaleFactor": 1, "mobile": False}})
    time.sleep(.35)


def screenshot(d, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    data = d.request("GET", f"/session/{d.sid}/screenshot")
    with open(path, "wb") as f:
        f.write(base64.b64decode(data))
    return path


# ---------------------------------------------------------------------------
# The page: join, open Draw / Code
# ---------------------------------------------------------------------------
def wait(d, script, timeout=20):
    end = time.time() + timeout
    while time.time() < end:
        try:
            if d.js(script):
                return True
        except WebDriverError:
            pass
        time.sleep(.1)
    return False


def click_js(d, selector, timeout=3):
    end = time.time() + timeout
    js = ("const el=document.querySelector(arguments[0]); if(!el) return false;"
          "el.scrollIntoView({block:'nearest'}); el.click(); return true;")
    while time.time() < end:
        try:
            if d.js(js, selector):
                return True
        except WebDriverError:
            pass
        time.sleep(.1)
    return False


def join(d, base, name):
    d.request("POST", f"/session/{d.sid}/url", {"url": base + "/pixel"})
    if not wait(d, "return !document.getElementById('join').hidden || "
                    "!document.getElementById('app').hidden", 30):
        raise RuntimeError("the page did not load")
    if not d.js("return document.getElementById('join').hidden"):
        d.send("#name", name)
        d.click("#joinButton")
    if not wait(d, "return !document.getElementById('app').hidden && typeof me !== 'undefined' && !!me", 30):
        raise RuntimeError("the student did not join")
    me = d.js("return me")
    post(base, "/pixel/news", {"id": me})          # hide the one-time New card
    time.sleep(.3)
    if not d.js("return document.getElementById('shelf').hidden"):
        if d.js("return !!document.querySelector('#picks [data-size=\"16\"]')"):
            d.click('#picks [data-size="16"]')
        else:
            d.click("#gallery [data-gallery]")
        wait(d, "return document.getElementById('shelf').hidden", 20)
    open_draw(d)
    wait(d, "return typeof art !== 'undefined' && !!art", 20)
    return me


def open_draw(d):
    click_js(d, 'nav [data-view="draw"]')
    return wait(d, "return !document.getElementById('drawView').hidden && "
                   "typeof art !== 'undefined' && !!art", 20)


def open_code(d, key):
    click_js(d, 'nav [data-view="stage"]')
    if not wait(d, "return !document.getElementById('stageView').hidden && "
                   "typeof mode !== 'undefined' && !!mode", 30):
        raise RuntimeError("the Code tab did not open a mission")
    # Make sure the mission we want is the open one.
    if d.js("return mode") != key:
        click_js(d, "#openMissions")
        wait(d, "return !document.getElementById('missions').hidden", 20)
        sel = f"#missionList [data-mission='{key}']"
        if not d.js("return !!document.querySelector(arguments[0])", sel):
            raise RuntimeError(f"no mission button for {key}: is it unlocked?")
        if d.js("return document.querySelector(arguments[0]).disabled", sel):
            raise RuntimeError(f"mission {key} is still locked")
        d.click(sel)
    if not wait(d, "return typeof mode !== 'undefined' && mode === %s && "
                   "typeof view !== 'undefined' && !!view && !document.getElementById('coach').hidden"
              % json.dumps(key), 30):
        raise RuntimeError(f"mission {key} did not open")
    wait(d, "return ((document.getElementById('coach') || {}).innerText || '').trim().length > 0", 20)
    return True


def unlock_to(base, me, key):
    """Finish every mission before `key` through the server, so it is open."""
    for k in pixel.LEVEL_ORDER:
        if k == key:
            break
        lv = pixel.LEVEL_BY_KEY[k]
        try:
            out = post(base, "/pixel/run", {"id": me, "level": k, "code": lv["reference"]})
        except Exception as e:
            raise RuntimeError(f"could not finish {k} to unlock {key}: {e}")
        if out.get("error") or not (out.get("stars") or [False])[0]:
            raise RuntimeError(f"finishing {k} to unlock {key} failed: {out.get('error') or out.get('reply')}")


# ---------------------------------------------------------------------------
# Measuring and adding it up
# ---------------------------------------------------------------------------
def pct(values, q):
    if not values:
        return 0.0
    s = sorted(values)
    i = max(0, min(len(s) - 1, math.ceil(q * len(s)) - 1))
    return s[i]


def stats(values):
    if not values:
        return {"n": 0, "median": 0, "p95": 0, "max": 0, "mean": 0}
    return {"n": len(values), "median": round(pct(values, .5), 2), "p95": round(pct(values, .95), 2),
            "max": round(max(values), 2), "mean": round(sum(values) / len(values), 2)}


def summary(raw):
    frames = raw["frames"]
    long = raw["long"]
    clicks = [c["ms"] for c in raw["clicks"]]
    keys = [k["ms"] for k in raw["keys"]]
    work = {name: stats(v) for name, v in raw["work"].items() if v}
    return {
        "seconds": round(raw["wall"] / 1000, 2),
        "frames": stats(frames),
        "long": {"n": len(long), "total": round(sum(long), 1),
                 "max": round(max(long), 1) if long else 0},
        "clicks": stats(clicks),
        "keys": stats(keys),
        "work": work,
        "steps": raw.get("steps"),
    }


def take_click(d, timeout=4):
    end = time.time() + timeout
    while time.time() < end:
        try:
            got = d.js("return window.__pqPerfTakeClick()")
        except WebDriverError:
            got = None
        if got:
            return got
        time.sleep(.01)
    return None


def measured(d, action, timeout=4):
    d.js("return window.__pqPerfArmClick()")
    action()
    got = take_click(d, timeout)
    if not got:
        raise RuntimeError("a click never showed in a painted frame")
    return got


def click_square_measured(d, x, y, timeout=4):
    return measured(d, lambda: d.click_square(x, y), timeout)


def layout(d):
    return d.js("return {inner: [innerWidth, innerHeight], scroll: "
               "[document.documentElement.scrollWidth, document.documentElement.scrollHeight], "
               "body: document.body.scrollWidth}")


def report_work(work, names):
    bits = []
    for name in names:
        s = work.get(name)
        if s and s["n"]:
            bits.append(f"{name} {s['median']:.1f}/{s['p95']:.1f}/{s['max']:.1f}")
    return " | ".join(bits)


# ---------------------------------------------------------------------------
# Draw: the six scenarios
# ---------------------------------------------------------------------------
def clear(d):
    """More > Clear all, with real clicks and no measuring."""
    if d.exists("#moreMenu") and not d.js("return document.getElementById('moreMenu').hidden"):
        d.click("#closeMore")
    d.click("#openMore")
    wait(d, "return !document.getElementById('moreMenu').hidden", 10)
    d.click("#clear")
    d.click("#closeMore")
    time.sleep(.15)


def blank(d, size):
    if not d.js("return document.getElementById('shelf').hidden"):
        close_shelf(d)
    trim_shelf(d, 2)
    start_blank(d, size)
    wait(d, f"return typeof art !== 'undefined' && art.size === {size}", 15)
    time.sleep(.15)


def draw_click_by_click(d):
    blank(d, 16)
    pick_tool(d, "pencil")
    choose_colour(d, 0)
    d.js("return window.__pqPerfReset()")
    spots = [(x, y) for y in range(2, 10) for x in range(2, 7)][:40]
    clicks = []
    for x, y in spots:
        clicks.append(click_square_measured(d, x, y))
    raw = d.js("return window.__pqPerfStop()")
    raw["clicks"] = clicks               # the real per-click timings, not the consumed list
    return summary(raw)


def draw_easy_pen(d):
    blank(d, 16)
    set_switch(d, "easy", True)
    pick_tool(d, "pencil")
    choose_colour(d, 0)
    d.js("return window.__pqPerfReset()")
    clicks = []
    clicks.append(click_square_measured(d, 1, 10))
    ax, ay = d.board_xy(4, 10)
    bx, by = d.board_xy(11, 10)
    d.mouse_at(ax, ay)
    d.mouse_at(bx, by)
    clicks.append(measured(d, lambda: d.click_square(11, 10)))
    raw = d.js("return window.__pqPerfStop()")
    raw["clicks"] = clicks
    set_switch(d, "easy", False)
    return summary(raw)


def draw_fill_huge(d):
    blank(d, 48)
    pick_tool(d, "fill")
    choose_colour(d, 0)
    d.js("return window.__pqPerfReset()")
    clicks = [click_square_measured(d, 24, 24, timeout=8)]
    raw = d.js("return window.__pqPerfStop()")
    raw["clicks"] = clicks
    filled = d.js("return art.frames[cur].filter(n => n >= 0).length")
    out = summary(raw)
    out["filled_squares"] = filled
    return out


def draw_mirror_sparkle(d):
    blank(d, 16)
    # ✚ 4-way mirror, then the sparkle pen.
    if d.js("return document.getElementById('mirror4').getAttribute('aria-pressed') !== 'true'"):
        d.click("#mirror4")
        wait(d, "return document.getElementById('mirror4').getAttribute('aria-pressed') === 'true'", 10)
    if d.js("return document.querySelector('#pens [data-pen=\"sparkle\"]').getAttribute('aria-pressed') !== 'true'"):
        d.click('#pens [data-pen="sparkle"]')
        wait(d, "return document.querySelector('#pens [data-pen=\"sparkle\"]').getAttribute('aria-pressed') === 'true'", 10)
    pick_tool(d, "pencil")
    choose_colour(d, 11)
    d.js("return window.__pqPerfReset()")
    clicks = []
    for x, y in [(3, 4), (4, 4), (5, 5), (6, 5), (7, 6)]:
        clicks.append(click_square_measured(d, x, y))
    raw = d.js("return window.__pqPerfStop()")
    raw["clicks"] = clicks
    out = summary(raw)
    out["lit_squares"] = d.js("return art.frames[cur].filter(n => n >= 0).length")
    return out


def eight_frames(d):
    """Make eight frames by copying, then paint on four of them so Undo has work."""
    blank(d, 16)
    while d.js("return art.frames.length") < 8:
        before = d.js("return art.frames.length")
        d.click("#copyFrame")
        if not wait(d, f"return typeof art!=='undefined' && art.frames.length > {before}", 10):
            raise RuntimeError("Copy frame did not add a frame")
    # A few different pictures, so the thumbnails are not all empty.
    pick_tool(d, "pencil")
    choose_colour(d, 0)
    for i in range(8):
        d.click(f"#frames [data-frame='{i}']")
        wait(d, f"return typeof cur !== 'undefined' && cur === {i}", 5)
        d.click_square(1 + i, 3)
        d.click_square(2 + i, 4)
    d.click("#frames [data-frame='0']")
    wait(d, "return typeof cur !== 'undefined' && cur === 0", 5)
    return d.js("return art.frames.length")


def draw_frames_switch(d):
    eight_frames(d)
    d.js("return window.__pqPerfReset()")
    clicks = []
    for i in range(8):
        clicks.append(measured(d, lambda i=i: d.click(f"#frames [data-frame='{i}']")))
        if not wait(d, f"return typeof cur !== 'undefined' && cur === {i}", 5):
            raise RuntimeError(f"frame {i} did not open")
    raw = d.js("return window.__pqPerfStop()")
    raw["clicks"] = clicks
    out = summary(raw)
    out["frames_in_reel"] = d.js("return art.frames.length")
    return out


def draw_undo20(d):
    eight_frames(d)
    pick_tool(d, "pencil")
    choose_colour(d, 0)
    for i in range(24):
        d.click_square(2 + (i % 12), 2 + (i // 12))
    # A frame switch in the middle of the history, like a child looking back.
    d.click("#frames [data-frame='2']")
    wait(d, "return typeof cur !== 'undefined' && cur === 2", 5)
    d.click_square(7, 7)
    d.click("#frames [data-frame='0']")
    wait(d, "return typeof cur !== 'undefined' && cur === 0", 5)
    have = d.js("return undoList.length")
    if have < 20:
        raise RuntimeError(f"only {have} undo steps before Undo x20")
    d.js("return window.__pqPerfReset()")
    clicks = []
    for _ in range(20):
        clicks.append(measured(d, lambda: d.click("#undo")))
    raw = d.js("return window.__pqPerfStop()")
    raw["clicks"] = clicks
    out = summary(raw)
    out["undo_left"] = d.js("return undoList.length")
    out["redo_len"] = d.js("return redoList.length")
    return out


# ---------------------------------------------------------------------------
# Code: a 12-line guided program and its 30-step show
# ---------------------------------------------------------------------------
COACH = [
    ["# my big show", "This line is a note for you. It does nothing."],
    ["for i in range(5):", "Do the lines pushed in, 5 times."],
    ["    jump()", "Jump!"],
    ["    spin()", "Spin round."],
    ["    wave()", "Wave hello."],
    ["    cheer()", "Cheer!"],
    ['    say("hi")', "Say hi."],
    ["# now some hearts", "Another note for you. It does nothing."],
    ["for i in range(5):", "Do the next line, 5 times."],
    ["    hearts()", "Hearts float up."],
    ["# that's all", "The end. It does nothing."],
    ["# 30 moves!", "Yes, thirty things happen."],
]
COACH_TARGET = "\n".join(line for line, _ in COACH)


def set_guide(d):
    """Use the same guide a mission uses, with a 12-line program for this test.

    This only changes the page's `view.coach` for this measurement; the saved
    mission content and every app file stay exactly as they are.
    """
    d.js("""
      window.__pqCoach = arguments[0];
      view.coach = window.__pqCoach;
      coachWay = "type";
      coachOops = "";
      coachEarly = false;
      setCode("");
      paintYourTurn();
      paintCoach();
      coachFocus();
      return view.coach.map(c => c[0]).join("\\n");
    """, COACH)
    got = d.js("return coachTarget()")
    if got != COACH_TARGET:
        raise RuntimeError("the 12-line guide did not take")
    if not d.js("return document.getElementById('code').value === ''"):
        raise RuntimeError("the editor was not empty before typing")
    return True


def code_type_and_show(d):
    open_code(d, "s2")
    set_guide(d)
    d.js("return window.__pqPerfWrapStage()")
    focus_code(d)
    d.js("return window.__pqPerfReset()")
    d.js("return window.__pqPerfArmKeys(true)")
    typed = type_coach(d, COACH_TARGET)
    if not typed.get("ok"):
        raise RuntimeError("typing the 12-line program failed: " + json.dumps(typed)[:1500])
    raw = d.js("return window.__pqPerfStop()")
    typing = summary(raw)
    typing["len"] = len(COACH_TARGET)
    typing["lines"] = COACH_TARGET.count("\n") + 1
    if d.js("return document.getElementById('code').value") != COACH_TARGET:
        raise RuntimeError("the editor does not hold the 12-line program after typing")

    # Show time! for the 30-step show.
    d.js("return window.__pqPerfArmKeys(false)")
    d.js("return window.__pqPerfReset()")
    d.request("POST", f"/session/{d.sid}/element/{d.find('#runButton')}/click", {})
    # The first watch asks a "Guess first" question before the show starts.
    if wait(d, "return !!document.querySelector('[data-guess]')", 5):
        d.click("[data-guess='skip']")
    if not wait(d, "return (typeof running !== 'undefined' && running === true) || "
                    "(window.__pqPerfSteps || 0) > 0", 10):
        raise RuntimeError("Show time! did not start")
    ok = wait(d, "return (typeof running !== 'undefined' && running === false) && "
                 "(window.__pqPerfSteps || 0) > 0", 120)
    if not ok:
        raise RuntimeError("the 30-step show did not finish")
    raw = d.js("return window.__pqPerfStop()")
    show = summary(raw)
    show["steps"] = d.js("return window.__pqPerfSteps || 0")
    show["caption"] = d.js("return document.getElementById('caption').innerText")
    return typing, show


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--base", default="http://127.0.0.1:8921")
    ap.add_argument("--port", type=int, default=None)
    ap.add_argument("--driver", default="chromedriver")
    ap.add_argument("--browser", default="/usr/bin/chromium")
    ap.add_argument("--phase", default="run", help="name for the screenshots, e.g. before/after")
    ap.add_argument("--shot-dir", default="")
    ap.add_argument("--json-out", default="")
    ap.add_argument("--only", default="", help="comma-separated: draw,code")
    ap.add_argument("--name", default="Perf Draw Code")
    args = ap.parse_args()
    base = args.base if not args.port else args.base.rsplit(":", 1)[0] + f":{args.port}"
    shots = args.shot_dir or f"/tmp/perf2/{args.phase}/screens"
    only = {x.strip().lower() for x in args.only.split(",") if x.strip()}
    tag = str(int(time.time()))[-5:]
    result = {"base": base, "phase": args.phase, "tag": tag, "viewports": {},
              "notes": [], "problems": []}
    d = None
    try:
        print("[perf] starting a student...", flush=True)
        d = Driver(args.driver, args.browser, 1366, 768)
        me = join(d, base, f"{args.name} {tag}")
        inject(d)
        result["student"] = me
        print("[perf] student %s is on Draw" % me, flush=True)

        if not only or "code" in only:
            print("[perf] unlocking the Code missions...", flush=True)
            t0 = time.time()
            unlock_to(base, me, "s2")
            print("[perf] missions unlocked (%.1fs)" % (time.time() - t0), flush=True)
            # Go back to Draw so each viewport starts in the same place.
            open_draw(d)
            inject(d)
            wait(d, "return !document.getElementById('drawView').hidden", 10)

        for width, height in ((1024, 600), (1366, 768)):
            set_viewport(d, width, height)
            block = {"width": width, "height": height, "draw": {}, "code": {}}
            result["viewports"][f"{width}x{height}"] = block
            set_throttle(d, 4)
            time.sleep(.5)

            if not only or "draw" in only:
                open_draw(d)
                inject(d)
                wait(d, "return typeof art !== 'undefined' && !!art", 20)
                print("[perf] %dx%d Draw..." % (width, height), flush=True)
                for name, fn in (("click40", draw_click_by_click),
                                 ("easyPen", draw_easy_pen),
                                 ("fillHuge48", draw_fill_huge),
                                 ("mirror4Sparkle", draw_mirror_sparkle),
                                 ("frames8", draw_frames_switch),
                                 ("undo20", draw_undo20)):
                    try:
                        block["draw"][name] = fn(d)
                        b = block["draw"][name]
                        print("[perf]   %-16s clicks %5.1f/%6.1f ms | frames %5.1f/%6.1f | "
                              "long %2d max %6.1f | %s" %
                              (name, b["clicks"]["median"], b["clicks"]["p95"],
                               b["frames"]["median"], b["frames"]["p95"],
                               b["long"]["n"], b["long"]["max"],
                               report_work(b["work"], ("paintBoard", "buildReel", "snap",
                                                       "restore", "openFrame", "paintThumb",
                                                       "checkGuide", "PixelArt.flood",
                                                       "PixelArt.decode"))), flush=True)
                    except Exception as e:
                        result["problems"].append(f"{width}x{height} draw {name}: {type(e).__name__}: {e}")
                        print("[perf]   %-16s FAILED: %s" % (name, e), flush=True)
                        try:
                            open_draw(d)
                        except Exception:
                            pass
                block["draw"]["layout"] = layout(d)
                if block["draw"]["layout"]["scroll"][0] > block["draw"]["layout"]["inner"][0] + 1:
                    result["problems"].append(f"{width}x{height} Draw scrolls sideways: "
                                              f"{block['draw']['layout']['scroll'][0]} > "
                                              f"{block['draw']['layout']['inner'][0]}")
                screenshot(d, os.path.join(shots, f"{width}x{height}-draw.png"))

            if not only or "code" in only:
                print("[perf] %dx%d Code..." % (width, height), flush=True)
                try:
                    typing, show = code_type_and_show(d)
                    block["code"]["typing12"] = typing
                    block["code"]["show30"] = show
                    print("[perf]   typing12       keys %5.1f/%6.1f ms | frames %5.1f/%6.1f | "
                          "long %2d max %6.1f | %s" %
                          (typing["keys"]["median"], typing["keys"]["p95"],
                           typing["frames"]["median"], typing["frames"]["p95"],
                           typing["long"]["n"], typing["long"]["max"],
                           report_work(typing["work"], ("updateEditor", "paintCoach", "paintCode",
                                                        "saveCode", "syncScroll", "placeBand",
                                                        "paintBoard"))), flush=True)
                    print("[perf]   show30         steps %2d | frames %5.1f/%6.1f | long %2d max %6.1f" %
                          (show["steps"], show["frames"]["median"], show["frames"]["p95"],
                           show["long"]["n"], show["long"]["max"]), flush=True)
                except Exception as e:
                    result["problems"].append(f"{width}x{height} code: {type(e).__name__}: {e}")
                    print("[perf]   code FAILED: %s" % e, flush=True)
                    result["traceback"] = traceback.format_exc()[-2000:]
                block["code"]["layout"] = layout(d)
                if block["code"]["layout"]["scroll"][0] > block["code"]["layout"]["inner"][0] + 1:
                    result["problems"].append(f"{width}x{height} Code scrolls sideways: "
                                              f"{block['code']['layout']['scroll'][0]} > "
                                              f"{block['code']['layout']['inner'][0]}")
                screenshot(d, os.path.join(shots, f"{width}x{height}-code.png"))

        set_throttle(d, 1)
    except Exception as e:
        result["problems"].append(f"{type(e).__name__}: {e}")
        result["traceback"] = traceback.format_exc()[-4000:]
        print(result["traceback"], file=sys.stderr)
    finally:
        if d is not None:
            try:
                set_throttle(d, 1)
            except Exception:
                pass
            try:
                d.close()
            except Exception:
                pass

    result["ok"] = not result["problems"]
    if args.json_out:
        os.makedirs(os.path.dirname(args.json_out) or ".", exist_ok=True)
        with open(args.json_out, "w") as f:
            json.dump(result, f, indent=2)
    print(json.dumps({k: result[k] for k in ("phase", "problems", "ok")}, indent=2))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
