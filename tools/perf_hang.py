#!/usr/bin/env python3
"""Measure how smooth the Hang out is on a slow school laptop.

The tool starts headless Chromium through chromedriver (stdlib only), joins one
real student browser plus 24 more students over HTTP, and records what the page
does while the class is busy:

  * frame times from requestAnimationFrame (median, 95th percentile, longest),
  * long tasks from PerformanceObserver('longtask'),
  * how long buildRoomButtons() and roomState() take on each poll,
  * screenshots of every scene, so a change can be looked at.

It measures the Park with the class mural painted full, a fashion runway, a
wedding ceremony, a home with 20 things, and the projector at /pixel/show, at
1366x768 and 1024x600, with the page CPU-throttled 4x (like a cheap laptop).

Use a fresh state file and the port you were given:

    MAZE_PORT=8920 MAZE_STATE_FILE=/tmp/perf-state.json python3 server.py
    python3 tools/perf_hang.py --port 8920 --phase before
    # ... change code, restart the server ...
    python3 tools/perf_hang.py --port 8920 --phase after

Screenshots go to --shot-dir (default /tmp/pq-perf/<phase>), never in the repo.
The tool is not a unittest: unittest will not pick it up as test_*.py.
"""

import argparse
import base64
import json
import math
import os
import sys
import threading
import time
import traceback
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "tools"))
import pixel  # noqa: E402
import server  # noqa: E402  (only for the admin key)
from e2e_coach import Driver, WebDriverError  # noqa: E402


# ---------------------------------------------------------------------------
# HTTP helpers
# ---------------------------------------------------------------------------
def post(base, path, data, timeout=120):
    req = urllib.request.Request(base + path, data=json.dumps(data).encode(),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as f:
        return json.load(f)


def get(base, path, timeout=120):
    with urllib.request.urlopen(base + path, timeout=timeout) as f:
        return json.load(f)


def teacher(base, action, **more):
    return post(base, "/pixel/teacher", dict(key=server.ADMIN_KEY, action=action, **more))


def room_do(base, pid, what, **more):
    return post(base, "/pixel/room/do", dict(id=pid, what=what, **more))


def room_view(base):
    return get(base, "/pixel/room?after=-1&wait=0")


# ---------------------------------------------------------------------------
# A crowd of students: 24 over HTTP, walking and talking while we measure
# ---------------------------------------------------------------------------
class Crowd:
    def __init__(self, base, ids):
        self.base = base
        self.ids = ids
        self.stop = threading.Event()
        self.thread = None
        self.words = sorted(pixel.ROOM_SAYS)
        self.tick = 0

    def start(self):
        self.thread = threading.Thread(target=self._walk, daemon=True)
        self.thread.start()

    def _walk(self):
        i = 0
        while not self.stop.is_set():
            self.tick += 1
            for _ in range(2):
                pid = self.ids[(i + self.tick * 7) % len(self.ids)]
                i += 1
                x = 28 + ((self.tick * 37 + i * 53) % 264)
                y = .18 + ((self.tick * 13 + i * 7) % 70) / 100
                try:
                    out = room_do(self.base, pid, "walk", x=round(x), y=round(y, 2))
                    if out.get("error") == "join":
                        room_do(self.base, pid, "join")
                        room_do(self.base, pid, "go", name="park")
                    if self.tick % 7 == 0:
                        room_do(self.base, pid, "say", text=self.words[(self.tick + i) % len(self.words)])
                except Exception:
                    pass
            self.stop.wait(.18)

    def close(self):
        self.stop.set()
        if self.thread:
            self.thread.join(timeout=2)


# ---------------------------------------------------------------------------
# Setting the class up through the server's own API
# ---------------------------------------------------------------------------
def setup_class(base, tag):
    names = [f"Perf Kid {n:02d} {tag}" for n in range(25)]
    ids = []
    for name in names:
        pid = post(base, "/join", {"name": name})["id"]
        ids.append(pid)
        post(base, "/pixel/news", {"id": pid})       # hide the one-time ✨ New card

    teacher(base, "open", level=pixel.LEVEL_ORDER[-1])
    teacher(base, "placed_clear")
    teacher(base, "end_game")
    teacher(base, "mural_clear")
    teacher(base, "room", on=False)
    teacher(base, "room", on=True)

    # Everyone earns their way into the Hang out (the first three missions);
    # the first student finishes all of them, so there are coins for a home.
    fails = []
    for n, pid in enumerate(ids):
        keys = pixel.LEVEL_ORDER if n == 0 else pixel.LEVEL_ORDER[:3]
        for key in keys:
            out = post(base, "/pixel/run", {"id": pid, "level": key,
                                            "code": pixel.LEVEL_BY_KEY[key]["reference"]})
            if out.get("error") or not (out.get("stars") or [False])[0]:
                fails.append((n, key, out.get("error")))
    if fails:
        raise RuntimeError(f"setup missions failed: {fails[:3]}")

    # Everyone comes into the Hang out and stands in the Park.
    for pid in ids:
        out = room_do(base, pid, "join")
        if out.get("error"):
            raise RuntimeError(f"join failed: {out}")
        room_do(base, pid, "go", name="park")
    return names, ids


def paint_mural_full(base, ids):
    """Paint all 960 squares with the 25 students, 3 squares each per second."""
    cells = 40 * 24
    rounds = math.ceil(cells / (len(ids) * 3))
    sent = 0
    for r in range(rounds):
        for n, pid in enumerate(ids):
            for k in range(3):
                cell = r * len(ids) * 3 + n * 3 + k
                if cell >= cells:
                    continue
                try:
                    room_do(base, pid, "mural", action="paint", cell=cell, ink=(cell + n) % 16)
                    sent += 1
                except Exception:
                    pass
        time.sleep(1.02)
    view = room_view(base)
    grid = (view.get("mural") or {}).get("grid") or ""
    return sent, grid.count(".")


def setup_home(base, pid):
    """A home with a second room and 20 pieces of furniture out."""
    keys = ["rug", "plant", "balloons", "cupcakes", "duck", "lamp", "teddy", "flowers",
            "table", "beanbag", "toybox", "tree", "shelf", "fridge", "stove", "globe",
            "snowglobe", "partycake", "gumball", "mirror"]
    out = room_do(base, pid, "buy", key="r_bed")
    if out.get("error"):
        raise RuntimeError(f"could not buy a room: {out}")
    for key in keys[2:]:
        out = room_do(base, pid, "buy", key=key)
        if out.get("error"):
            raise RuntimeError(f"could not buy {key}: {out}")
    out = room_do(base, pid, "home")
    if out.get("error"):
        raise RuntimeError(f"could not go home: {out}")
    for i, key in enumerate(keys):
        n = 0 if i < 12 else 1
        x = n * pixel.PLACE_W + 95 + (i % 4) * 52
        y = .28 + ((i // 4) % 4) * .16
        out = room_do(base, pid, "furnish", key=key, x=round(x), y=round(y, 2))
        if out.get("error"):
            raise RuntimeError(f"could not put {key} out: {out}")
    room_do(base, pid, "home", out=True)       # the browser must start outside, with the class
    return len(keys)


def ensure_outside(base, ids):
    for pid in ids:
        out = room_do(base, pid, "join")
        if out.get("error") and out.get("error") != "locked":
            raise RuntimeError(f"could not join {pid}: {out}")
        room_do(base, pid, "go", name="park")


def start_fashion(base, ids):
    teacher(base, "end_game")
    ensure_outside(base, ids[1:7])
    out = room_do(base, ids[1], "game", action="create", kind="fashion")
    if out.get("error"):
        raise RuntimeError(f"fashion create: {out}")
    joined = [ids[1]]
    for pid in ids[2:7]:
        room_do(base, pid, "game", action="join")
        joined.append(pid)
    out = room_do(base, ids[1], "game", action="start")
    if out.get("error"):
        raise RuntimeError(f"fashion start: {out}")
    for pid in joined:
        room_do(base, pid, "game", action="ready")
    time.sleep(.4)
    view = room_view(base)
    return (view.get("game") or {}).get("phase")


def start_wedding(base, ids, names):
    teacher(base, "end_game")
    for pid in ids[1:3]:
        room_do(base, pid, "join")
        room_do(base, pid, "go", name="wedding")
    view = room_view(base)
    partner_seat = next((m["seat"] for m in view.get("people", []) if m["name"] == names[2]), None)
    host, partner = ids[1], ids[2]
    out = room_do(base, host, "wedding")
    if out.get("error"):
        raise RuntimeError(f"wedding start: {out}")
    cands = [c for c in (out.get("candidates") or []) if c["seat"] == partner_seat]
    if not cands:
        raise RuntimeError(f"wedding partner {names[2]} was not in the garden")
    out = room_do(base, host, "wedding_pick", seat=cands[0]["seat"])
    if out.get("error"):
        raise RuntimeError(f"wedding pick: {out}")
    out = room_do(base, partner, "wedding_yes")
    if out.get("error"):
        raise RuntimeError(f"wedding yes: {out}")
    time.sleep(.5)
    return (room_view(base).get("wedding") or {}).get("phase")

# ---------------------------------------------------------------------------
# Browser instrumentation (one classic script global, checked for clashes)
# ---------------------------------------------------------------------------
INJECT = r"""
return (() => {
  if (window.__pqPerf) return true;
  const p = window.__pqPerf = {frames: [], long: [], bb: [], rs: [], on: false, last: 0, t0: 0};
  function tick(t) {
    if (p.on) {
      const dt = p.last ? t - p.last : 0;
      if (dt > 0) p.frames.push(dt);
    }
    p.last = t;
    requestAnimationFrame(tick);
  }
  requestAnimationFrame(tick);
  try {
    new PerformanceObserver(list => {
      if (!p.on) return;
      for (const e of list.getEntries()) p.long.push(e.duration);
    }).observe({entryTypes: ["longtask"]});
  } catch (e) {}
  function wrap(name, key) {
    const orig = window[name];
    if (typeof orig !== "function" || orig.__pqWrapped) return;
    const f = function () {
      const t = performance.now();
      const out = orig.apply(this, arguments);
      if (p.on) p[key].push(performance.now() - t);
      return out;
    };
    f.__pqWrapped = true;
    window[name] = f;
  }
  wrap("buildRoomButtons", "bb");
  wrap("roomState", "rs");
  window.__pqPerfReset = () => {
    p.frames.length = 0; p.long.length = 0; p.bb.length = 0; p.rs.length = 0;
    p.last = 0; p.t0 = performance.now(); p.on = true; return true;
  };
  window.__pqPerfStop = () => {
    p.on = false;
    return {wall: performance.now() - p.t0, frames: p.frames.slice(), long: p.long.slice(),
            bb: p.bb.slice(), rs: p.rs.slice()};
  };
  return true;
})()
"""


def inject(d, room_page=True):
    if not d.js(INJECT):
        raise RuntimeError("could not inject the perf probe")
    if not d.js('return !!window.__pqPerf && typeof window.__pqPerfReset === "function"'):
        raise RuntimeError("the perf probe did not take")
    if room_page:
        ok = d.js('return typeof window.buildRoomButtons === "function" && typeof window.roomState === "function" && '
                  'window.buildRoomButtons.__pqWrapped === true')
        if not ok:
            raise RuntimeError("buildRoomButtons/roomState are not global functions to wrap")


def set_throttle(d, rate):
    d.request("POST", f"/session/{d.sid}/goog/cdp/execute",
              {"cmd": "Emulation.setCPUThrottlingRate", "params": {"rate": rate}})


def set_viewport(d, w, h):
    d.request("POST", f"/session/{d.sid}/goog/cdp/execute",
              {"cmd": "Emulation.setDeviceMetricsOverride",
               "params": {"width": w, "height": h, "deviceScaleFactor": 1, "mobile": False}})
    time.sleep(.35)


# ---------------------------------------------------------------------------
# The page helpers: login, open the Hang out, choose a place/pane
# ---------------------------------------------------------------------------
def wait(d, script, timeout=20, what=""):
    end = time.time() + timeout
    while time.time() < end:
        try:
            if d.js(script):
                return True
        except WebDriverError:
            pass
        time.sleep(.15)
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


def login(d, base, name):
    d.request("POST", f"/session/{d.sid}/url", {"url": base + "/pixel"})
    if not wait(d, "return !document.getElementById('join').hidden || !document.getElementById('app').hidden", 30):
        return False
    if not d.js("return document.getElementById('join').hidden"):
        d.send("#name", name)
        d.click("#joinButton")
        wait(d, "return !document.getElementById('app').hidden", 30)
    wait(d, "return typeof S !== 'undefined' && !!S", 20)
    time.sleep(.4)
    if not d.js("return document.getElementById('shelf').hidden"):
        d.click("#gallery [data-gallery]")
        wait(d, "return document.getElementById('shelf').hidden", 20)
    return True


def open_hang(d, want=25, timeout=45):
    end = time.time() + timeout
    while time.time() < end:
        if d.js("return !document.getElementById('hangView').hidden && typeof roomStage !== 'undefined' && roomStage && "
               "roomStage.state && roomStage.state.room && roomInfo && roomInfo.you !== null && "
               "roomStage.state.room.some(m => m.me) && roomStage.state.room.length >= %d" % want):
            return True
        click_js(d, 'nav [data-view="hang"]')
        time.sleep(.8)
    return False


def pane(d, name, timeout=6):
    click_js(d, f'#roomTabs [data-pane="{name}"]')
    return wait(d, f"return roomPane === {json.dumps(name)}", timeout)


def go_place(d, name, timeout=8):
    pane(d, "place")
    click_js(d, f'#roomButtons [data-name="{name}"]')
    return wait(d, f"return document.getElementById('hangView').dataset.place === {json.dumps(name)}", timeout)


def screenshot(d, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    data = d.request("GET", f"/session/{d.sid}/screenshot")
    with open(path, "wb") as f:
        f.write(base64.b64decode(data))
    return path


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


def measure(d, label, seconds=6.0):
    set_throttle(d, 4)
    time.sleep(.5)
    d.js("return window.__pqPerfReset()")
    time.sleep(seconds)
    raw = d.js("return window.__pqPerfStop()")
    set_throttle(d, 1)
    time.sleep(.2)
    frames, long, bb, rs = raw["frames"], raw["long"], raw["bb"], raw["rs"]
    out = {"label": label, "seconds": round(raw["wall"] / 1000, 2),
           "frames": stats(frames), "long": {"n": len(long), "total": round(sum(long), 1),
                                             "max": round(max(long), 1) if long else 0},
           "buildRoomButtons": stats(bb), "roomState": stats(rs),
           "polls": len(rs), "polls_per_sec": round(len(rs) / max(.001, raw["wall"] / 1000), 2)}
    print("[perf] %-34s frames median %6.1f p95 %7.1f max %7.1f | long %2d max %6.1f | "
          "buttons %5.1f p95 %6.1f | roomState %5.1f p95 %6.1f (%d polls)" %
          (label, out["frames"]["median"], out["frames"]["p95"], out["frames"]["max"],
           out["long"]["n"], out["long"]["max"], out["buildRoomButtons"]["median"],
           out["buildRoomButtons"]["p95"], out["roomState"]["median"],
           out["roomState"]["p95"], out["polls"]), flush=True)
    return out


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--base", default="http://127.0.0.1:8920")
    ap.add_argument("--port", type=int, default=None)
    ap.add_argument("--driver", default="chromedriver")
    ap.add_argument("--browser", default="/usr/bin/chromium")
    ap.add_argument("--phase", default="run", help="name for the screenshots, e.g. before/after")
    ap.add_argument("--shot-dir", default="")
    ap.add_argument("--json-out", default="")
    ap.add_argument("--seconds", type=float, default=6.0)
    ap.add_argument("--only", default="", help="comma-separated: park,fashion,wedding,home,projector")
    args = ap.parse_args()
    base = args.base if not args.port else args.base.rsplit(":", 1)[0] + f":{args.port}"
    shots = args.shot_dir or f"/tmp/pq-perf/{args.phase}"
    only = {x.strip().lower() for x in args.only.split(",") if x.strip()}
    tag = str(int(time.time()))[-5:]
    result = {"base": base, "phase": args.phase, "tag": tag, "widths": {}, "notes": [], "problems": []}
    crowd = None
    drivers = []
    try:
        print("[perf] setting the class up...", flush=True)
        t0 = time.time()
        names, ids = setup_class(base, tag)
        print("[perf] %d students joined (%.1fs)" % (len(ids), time.time() - t0), flush=True)
        sent, left = paint_mural_full(base, ids)
        print("[perf] mural: %d squares sent, %d blank left" % (sent, left), flush=True)
        home_things = setup_home(base, ids[0])
        print("[perf] home: %d things out" % home_things, flush=True)
        crowd = Crowd(base, ids[1:])
        crowd.start()

        # One real student browser, logged in as the first student.
        d = Driver(args.driver, args.browser, 1366, 768)
        drivers.append(d)
        if not login(d, base, names[0]):
            raise RuntimeError("the student browser could not log in")
        inject(d)
        if not open_hang(d, 25):
            raise RuntimeError("the student browser could not open the Hang out")
        if not go_place(d, "park"):
            raise RuntimeError("the student browser could not go to the Park")
        print("[perf] student browser is in the Park", flush=True)

        p = None
        if not only or "projector" in only:
            p = Driver(args.driver, args.browser, 1366, 768)
            drivers.append(p)
            p.request("POST", f"/session/{p.sid}/url", {"url": base + "/pixel/show"})
            ok = wait(p, "return typeof PalStage !== 'undefined' && document.querySelectorAll('#people button').length >= 20", 45)
            if not ok:
                ok = wait(p, "return typeof PalStage !== 'undefined' && document.querySelectorAll('#people button').length >= 20", 20)
            if not ok:
                result["problems"].append("the projector did not list the class")
            inject(p, room_page=False)
            # Look at the Park, where the class is.
            p.js("cam.mode='free'; cam.seat=null; cam.loc=0; cam.x=0; paintWorld && paintWorld()")

        for width, height in ((1366, 768), (1024, 600)):
            set_viewport(d, width, height)
            ensure_outside(base, ids)
            if not go_place(d, "park"):
                raise RuntimeError("lost the Park after resizing")
            block = {"width": width, "height": height, "runs": {}}
            result["widths"][f"{width}x{height}"] = block
            if not only or "park" in only:
                block["runs"]["park"] = measure(d, f"{width}x{height} park + full mural", args.seconds)
                screenshot(d, os.path.join(shots, f"{width}x{height}-park.png"))
            if p is not None and width == 1366 and (not only or "projector" in only):
                set_viewport(p, width, height)
                p.js("cam.mode='free'; cam.seat=null; cam.loc=0; cam.x=0; paintWorld && paintWorld()")
                result["projector"] = measure(p, f"{width}x{height} projector + full mural", args.seconds)
                screenshot(p, os.path.join(shots, f"{width}x{height}-projector.png"))

            if not only or "fashion" in only:
                phase = start_fashion(base, ids)
                result["notes"].append(f"fashion phase {phase}")
                if not go_place(d, "park"):
                    raise RuntimeError("lost the Park for the fashion show")
                time.sleep(.3)
                block["runs"]["fashion"] = measure(d, f"{width}x{height} fashion runway", args.seconds)
                screenshot(d, os.path.join(shots, f"{width}x{height}-fashion.png"))
                teacher(base, "end_game")

            if not only or "wedding" in only:
                phase = start_wedding(base, ids, names)
                result["notes"].append(f"wedding phase {phase}")
                room_do(base, ids[0], "go", name="wedding")
                if not wait(d, 'return document.getElementById("hangView").dataset.place === "wedding"', 10):
                    raise RuntimeError("the student browser could not go to the Wedding")
                time.sleep(.5)
                block["runs"]["wedding"] = measure(d, f"{width}x{height} wedding ceremony", args.seconds)
                screenshot(d, os.path.join(shots, f"{width}x{height}-wedding.png"))
                room_do(base, ids[1], "go", name="park")      # stops the ceremony
                room_do(base, ids[2], "go", name="park")

            if not only or "home" in only:
                room_do(base, ids[0], "home")
                if not wait(d, "return !!(roomInfo && roomInfo.home && roomInfo.home.mine)", 12):
                    raise RuntimeError("the student browser could not go home")
                pane(d, "home")
                time.sleep(.5)
                block["runs"]["home"] = measure(d, f"{width}x{height} home with 20 things", args.seconds)
                screenshot(d, os.path.join(shots, f"{width}x{height}-home.png"))
                room_do(base, ids[0], "home", out=True)

        if p is not None:
            try:
                p.close()
            except Exception:
                pass
        for drv in drivers:
            try:
                drv.close()
            except Exception:
                pass
        drivers = []
    except Exception as e:
        result["problems"].append(f"{type(e).__name__}: {e}")
        result["traceback"] = traceback.format_exc()[-2000:]
        print(result["traceback"], file=sys.stderr)
    finally:
        if crowd:
            crowd.close()
        for drv in drivers:
            try:
                drv.close()
            except Exception:
                pass
        try:
            teacher(base, "end_game")
        except Exception:
            pass

    result["ok"] = not result["problems"]
    if args.json_out:
        with open(args.json_out, "w") as f:
            json.dump(result, f, indent=2)
    print(json.dumps({k: result[k] for k in ("phase", "problems", "ok")}, indent=2))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
