#!/usr/bin/env python3
"""End-to-end check of 🎬 On the big screen, in a real browser.

It makes a student with a Free stage show through the same HTTP calls the
student page uses, opens the projector at /pixel/show, signs in to
/pixel/teacher in a second tab, presses the student's 🎬 Big screen button, and
checks the projector's overlay: the title, the stage, the code beside it with
the running line lit, the sound button, Close, and the auto close after the
show ends. It saves a screenshot mid-show to look at.

The server must already be running; use a fresh --state file if you can:

    MAZE_PORT=8129 MAZE_STATE_FILE=/tmp/bigshow-state.json python3 server.py
    python3 tools/e2e_bigshow.py --port 8129 --screenshot /tmp/bigshow.png

It starts headless Chromium through chromedriver and speaks the WebDriver wire
protocol with the standard library, so there is nothing to pip install. It
reuses the small client in tools/e2e_coach.py. This is a tool, not a unittest:
it is not named test_*.py and unittest will not pick it up.
"""

import argparse
import base64
import json
import os
import re
import sys
import time
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "tools"))
import pixel  # noqa: E402
import server  # noqa: E402  (only for the admin key)
from e2e_coach import Driver  # noqa: E402

SHOW = ('scene("beach")\nfriend("cat")\nsay("Hello!")\nfor i in range(3):\n    jump()\n'
        'note("C")\nrain()\nfeel("happy")\nhearts()\ndance()')
PAL = {"key": "e2epal", "size": 16, "speed": 6, "palette": pixel.PIP["palette"],
       "frames": pixel.PIP["frames"], "names": pixel.PIP["names"]}


def post(base, path, data):
    req = urllib.request.Request(base + path, data=json.dumps(data).encode(),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as f:
        return json.load(f)


def make_show(base, name):
    """A student with a saved drawing and a Free stage show, ready for the teacher."""
    pid = post(base, "/join", {"name": name})["id"]
    post(base, "/pixel/teacher", {"key": server.ADMIN_KEY, "action": "open", "level": "m1"})
    post(base, "/pixel/run", {"id": pid, "level": "m1",
                              "code": pixel.LEVEL_BY_KEY["m1"]["reference"]})
    post(base, "/pixel/save", {"id": pid, "drawing": PAL})
    out = post(base, "/pixel/run", {"id": pid, "level": "free", "code": SHOW})
    if out.get("error"):
        raise RuntimeError(f"the test show did not run: {out['error']}")
    return pid


def switch(driver, handle):
    driver.request("POST", f"/session/{driver.sid}/window", {"handle": handle})


def run(args, report):
    d = Driver(args.driver, args.browser, args.width, args.height)
    try:
        d.request("POST", f"/session/{d.sid}/url", {"url": args.base + "/pixel/show"})
        d.wait("return !!document.getElementById('stage') && typeof PalStage !== 'undefined'",
               30, "the projector")
        report["viewport"] = d.js("return [innerWidth, innerHeight]")
        main = d.request("GET", f"/session/{d.sid}/window")

        new = d.request("POST", f"/session/{d.sid}/window/new", {"type": "tab"})
        switch(d, new["handle"] if isinstance(new, dict) else new)
        d.request("POST", f"/session/{d.sid}/url", {"url": args.base + "/pixel/teacher"})
        d.wait("return !document.getElementById('gate').hidden", 30, "the teacher gate")
        d.send("#key", server.ADMIN_KEY)
        d.click("#gate button")
        d.wait("return !document.getElementById('page').hidden && "
               "document.querySelectorAll('#rows tr').length > 0", 30, "the teacher page")
        report["big_screen_buttons"] = d.js("return document.querySelectorAll('[data-big-show]').length")
        if not report["big_screen_buttons"]:
            raise RuntimeError("the student has no 🎬 Big screen button")
        d.js("const b = [...document.querySelectorAll('[data-big-show]')]"
             ".find(x => x.dataset.bigShow === arguments[0]); if (b) b.click();", args.name)
        d.wait("return !document.getElementById('bigShowNote').hidden", 15, "the teacher's note")
        report["teacher_note"] = d.text("#bigShowNote")

        switch(d, main)
        d.wait("return !document.getElementById('bigShow').hidden", 20, "the big screen overlay")
        d.wait("return document.querySelectorAll('#bigShowCode .show-line').length > 0", 10, "the show's code")
        time.sleep(args.mid_show)
        report.update(d.js("""
          return {
            title: document.getElementById('bigShowTitle').innerText,
            overlay: !document.getElementById('bigShow').hidden,
            code_lines: document.querySelectorAll('#bigShowCode .show-line').length,
            running: [...document.querySelectorAll('#bigShowCode .show-line.run')].map(r => r.innerText),
            running_is_lit: (() => { const r = document.querySelector('#bigShowCode .show-line.run');
                                     return !!r && getComputedStyle(r).backgroundColor !== 'rgba(0, 0, 0, 0)'; })(),
            close: document.getElementById('bigShowClose').innerText,
            sound: !document.getElementById('bigShowSound').hidden,
            sound_text: document.getElementById('bigShowSound').innerText,
            code_font: getComputedStyle(document.getElementById('bigShowCode')).fontSize,
            stage_size: (() => { const r = document.getElementById('bigShowStage').getBoundingClientRect();
                                 return [Math.round(r.width), Math.round(r.height)]; })(),
          };
        """))
        shot = d.request("GET", f"/session/{d.sid}/screenshot")
        with open(args.screenshot, "wb") as f:
            f.write(base64.b64decode(shot))
        report["screenshot"] = args.screenshot
        report["console_errors"] = [e for e in d.logs() if e.get("level") == "SEVERE"]

        if report["sound"]:
            d.click("#bigShowSound")
            time.sleep(.5)
            report["sound_unlocked"] = d.js("return !PalStage.SFX.locked")
        d.click("#bigShowClose")
        d.wait("return document.getElementById('bigShow').hidden", 10, "Close to hide the overlay")

        switch(d, new["handle"] if isinstance(new, dict) else new)
        d.js("const b = [...document.querySelectorAll('[data-big-show]')]"
             ".find(x => x.dataset.bigShow === arguments[0]); if (b) b.click();", args.name)
        switch(d, main)
        d.wait("return !document.getElementById('bigShow').hidden", 20, "the overlay again")
        started = time.time()
        d.wait("return document.getElementById('bigShow').hidden", 60, "auto close")
        report["auto_closed_after"] = round(time.time() - started, 1)
    finally:
        d.close()


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--base", default="http://127.0.0.1:8129")
    ap.add_argument("--port", type=int, default=None)
    ap.add_argument("--driver", default="chromedriver")
    ap.add_argument("--browser", default="/usr/bin/chromium")
    ap.add_argument("--width", type=int, default=1366)
    ap.add_argument("--height", type=int, default=768)
    ap.add_argument("--name", default="Big Screen E2E")
    ap.add_argument("--mid-show", type=float, default=1.2)
    ap.add_argument("--screenshot", default="/tmp/pixel-bigshow.png")
    ap.add_argument("--json-out", default="")
    args = ap.parse_args()
    args.base = args.base if args.port is None else re.sub(r":\d+$", f":{args.port}", args.base)
    report = {"base": args.base, "problems": []}
    make_show(args.base, args.name)
    run(args, report)
    if report.get("title", "").find(args.name) < 0: report["problems"].append("title doesn't name the student")
    if not report.get("code_lines"): report["problems"].append("the code is missing")
    if not report.get("running"): report["problems"].append("no line was lit mid-show")
    if not report.get("running_is_lit"): report["problems"].append("the running line has no highlight")
    if not report.get("sound"): report["problems"].append("the sound button was not offered while audio was locked")
    if not report.get("sound_unlocked"): report["problems"].append("clicking the sound button did not unlock audio")
    if not report.get("overlay"): report["problems"].append("the overlay did not open")
    report["ok"] = not report["problems"] and not report.get("console_errors")
    if args.json_out:
        with open(args.json_out, "w") as f:
            json.dump(report, f, indent=2)
    print(json.dumps(report, indent=2))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
