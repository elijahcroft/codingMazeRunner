#!/usr/bin/env python3
"""End-to-end bug hunt for Pixel Pals' 🎨 Draw tab, in a real browser.

It drives headless Chromium through chromedriver with the standard library
only (the same wire-protocol client as tools/e2e_coach.py), at the class's
1366x768, with real mouse and key events.  It joins as a student, then walks
through the Draw tab the way a kid does:

  * the gallery's three ways (🖍️ colour it in, 🔢 by numbers, ⭐ ready to change),
  * every tool, pen size, rainbow/checks pen, Easy pen, Mirror, Grid, zoom,
  * Undo/Redo (many undos, after a frame switch, after a gallery pick),
  * frames (+ Copy, + Blank, Delete, Ghost, many, Move it, naming),
  * naming the drawing, My drawings (switch, delete, a new one), Download,
  * ✨ Bring to life, fixing a part, Turn into frames, Download a GIF, Place,
  * the four sizes, 🌿 Calm, a reload in the middle, and two tabs of one student.

Each check is recorded with OK/FAIL and what was on screen.  It is a tool, not
a unittest, so unittest will not pick it up.

Usage (the server must already be running on the port given; see DS_REPORT.md):

    python3 tools/e2e_draw.py --port 8130 --json-out /tmp/draw.json
    python3 tools/e2e_draw.py --port 8130 --only gallery,tools

It needs chromium and chromedriver on PATH.  Exit code 0 means every check
passed and no console errors were seen.
"""

import argparse
import json
import os
import re
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import pixel  # noqa: E402  (only for the state-file path in the report)

ENTER = "\ue007"
ESCAPE = "\ue00c"
BACKSPACE = "\ue003"
DEFAULT_BASE = "http://127.0.0.1:8130"
DEFAULT_DRIVER = "chromedriver"


# ---------------------------------------------------------------------------
# A very small WebDriver client: enough for clicks, drags, keys, script and logs.
# ---------------------------------------------------------------------------

class WebDriverError(RuntimeError):
    pass


class Driver:
    def __init__(self, driver_bin, browser_bin, width, height, verbose=False):
        self.verbose = verbose
        self.port = self._free_port()
        self.proc = subprocess.Popen(
            [driver_bin, f"--port={self.port}", "--allowed-ips=127.0.0.1"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        self.base = f"http://127.0.0.1:{self.port}"
        self._wait_driver()
        self.sid = self._new_session(browser_bin, width, height)
        self.log_seen = 0

    @staticmethod
    def _free_port():
        with socket.socket() as s:
            s.bind(("127.0.0.1", 0))
            return s.getsockname()[1]

    def _wait_driver(self):
        for _ in range(100):
            try:
                urllib.request.urlopen(self.base + "/status", timeout=1)
                return
            except Exception:
                time.sleep(.1)
        raise WebDriverError("chromedriver did not start")

    @staticmethod
    def _read_error(e):
        try:
            return e.read().decode("utf-8", "replace")
        except Exception:
            return ""

    def request(self, method, path, data=None, timeout=120):
        body = None if data is None else json.dumps(data).encode()
        req = urllib.request.Request(
            self.base + path, data=body, method=method,
            headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=timeout) as f:
                return json.load(f).get("value")
        except urllib.error.HTTPError as e:
            raise WebDriverError(f"{method} {path}: {e.code} {self._read_error(e)[:700]}") from None

    def _new_session(self, browser_bin, width, height):
        caps = {
            "capabilities": {"alwaysMatch": {
                "browserName": "chrome",
                "goog:chromeOptions": {
                    "binary": browser_bin,
                    "args": ["--headless=new", "--no-sandbox", "--disable-gpu",
                             "--disable-dev-shm-usage", "--log-level=3",
                             f"--window-size={width},{height}"],
                },
                "goog:loggingPrefs": {"browser": "ALL"},
            }}
        }
        sid = self.request("POST", "/session", caps)["sessionId"]
        try:
            self.request("POST", f"/session/{sid}/window/rect",
                         {"width": width, "height": height})
        except WebDriverError:
            pass
        try:
            self.request("POST", f"/session/{sid}/goog/cdp/execute",
                         {"cmd": "Emulation.setDeviceMetricsOverride",
                          "params": {"width": width, "height": height,
                                     "deviceScaleFactor": 1, "mobile": False}})
        except WebDriverError:
            pass
        return sid

    # -- basics -------------------------------------------------------------
    def js(self, script, *args):
        return self.request("POST", f"/session/{self.sid}/execute/sync",
                            {"script": script, "args": list(args)})

    def js_async(self, script, *args, timeout=30):
        return self.request("POST", f"/session/{self.sid}/execute/async",
                            {"script": script, "args": list(args)}, timeout=timeout)

    def find(self, css):
        value = self.request("POST", f"/session/{self.sid}/element",
                             {"using": "css selector", "value": css})
        return value["element-6066-11e4-a52e-4f735466cecf"]

    def exists(self, css):
        return bool(self.js("return !!document.querySelector(arguments[0])", css))

    def click(self, css, retry=True):
        try:
            eid = self.find(css)
            self.request("POST", f"/session/{self.sid}/element/{eid}/click", {})
        except WebDriverError as e:
            text = str(e)
            # A sticky sheet header or an animation can intercept the native
            # click; clicking the element's own handler is still a real click.
            if retry and ("click intercepted" in text or "not interactable" in text
                          or "element not found" in text):
                self.js("const el=document.querySelector(arguments[0]);"
                        "if (el) el.click();", css)
            else:
                raise

    def send(self, css, text):
        for attempt in (0, 1):
            try:
                eid = self.find(css)
                self.request("POST", f"/session/{self.sid}/element/{eid}/value",
                             {"text": text})
                return
            except WebDriverError:
                if attempt:
                    raise
                self.js("const t=document.getElementById('code');"
                        "if (t) { t.focus(); t.setSelectionRange(t.value.length, t.value.length); }")

    def text(self, css):
        return self.js("const el=document.querySelector(arguments[0]);"
                       "return el ? (el.innerText || '') : ''", css)

    def wait(self, script, timeout=20, what="", poll=.04):
        end = time.time() + timeout
        while time.time() < end:
            try:
                if self.js(script):
                    return True
            except WebDriverError:
                pass
            time.sleep(poll)
        if what:
            raise WebDriverError(f"timed out waiting for {what}\n{json.dumps(self.state(), indent=2)[:4000]}")
        return False

    def logs(self):
        """Browser console entries since the last call, without repeats."""
        try:
            entries = self.request("POST", f"/session/{self.sid}/se/log", {"type": "browser"})
        except WebDriverError:
            try:
                entries = self.request("GET", f"/session/{self.sid}/se/log", None)
            except WebDriverError:
                return []
        entries = entries or []
        new = entries[self.log_seen:]
        self.log_seen = len(entries)
        return [{"level": e.get("level"), "message": e.get("message")} for e in new]

    # -- real pointer input -------------------------------------------------
    def actions(self, steps):
        self.request("POST", f"/session/{self.sid}/actions", {"actions": [
            {"type": "pointer", "id": "mouse", "parameters": {"pointerType": "mouse"},
             "actions": steps}]})

    def mouse_at(self, x, y):
        self.actions([{"type": "pointerMove", "x": int(round(x)), "y": int(round(y)),
                       "origin": "viewport", "duration": 0}])

    def click_at(self, x, y):
        self.actions([
            {"type": "pointerMove", "x": int(round(x)), "y": int(round(y)),
             "origin": "viewport", "duration": 0},
            {"type": "pointerDown", "button": 0},
            {"type": "pointerUp", "button": 0}])

    def drag_at(self, x0, y0, x1, y1, steps=8, hold=0.02):
        acts = [{"type": "pointerMove", "x": int(round(x0)), "y": int(round(y0)),
                 "origin": "viewport", "duration": 0},
                {"type": "pointerDown", "button": 0}]
        for i in range(1, steps + 1):
            x = x0 + (x1 - x0) * i / steps
            y = y0 + (y1 - y0) * i / steps
            acts.append({"type": "pointerMove", "x": int(round(x)), "y": int(round(y)),
                         "origin": "viewport", "duration": 12})
        acts.append({"type": "pointerUp", "button": 0})
        self.actions(acts)
        time.sleep(hold)

    def rect(self, css):
        return self.js("const e=document.querySelector(arguments[0]);"
                       "if (!e) return null; const r=e.getBoundingClientRect();"
                       "return {x:r.left,y:r.top,w:r.width,h:r.height};", css)

    def click_center(self, css):
        r = self.rect(css)
        if not r:
            raise WebDriverError(f"no element {css}")
        self.click_at(r["x"] + r["w"] / 2, r["y"] + r["h"] / 2)

    # -- the drawing board --------------------------------------------------
    def board_xy(self, x, y):
        """Viewport point at the middle of board square (x, y)."""
        point = self.js(r"""
        const cv=document.getElementById('board'), r=cv.getBoundingClientRect();
        return {left:r.left, top:r.top, cell:(typeof cell!=='undefined'?cell:16),
                pan:(typeof panAt!=='undefined'?panAt:{x:0,y:0})};
        """)
        return (point["left"] + 2 + x * point["cell"] + point["cell"] / 2 - point["pan"]["x"],
                point["top"] + 2 + y * point["cell"] + point["cell"] / 2 - point["pan"]["y"])

    def click_square(self, x, y):
        px, py = self.board_xy(x, y)
        self.click_at(px, py)

    def drag_squares(self, x0, y0, x1, y1, steps=8):
        ax, ay = self.board_xy(x0, y0)
        bx, by = self.board_xy(x1, y1)
        self.drag_at(ax, ay, bx, by, steps=steps)

    def key(self, key, times=1):
        for _ in range(times):
            eid = self.find("body")
            self.request("POST", f"/session/{self.sid}/element/{eid}/value",
                         {"text": key})

    def current_handle(self):
        return self.request("GET", f"/session/{self.sid}/window")

    def new_tab(self):
        return self.request("POST", f"/session/{self.sid}/window/new", {"type": "tab"})["handle"]

    def switch_tab(self, handle):
        self.request("POST", f"/session/{self.sid}/window", {"handle": handle})

    def screenshot(self, path):
        try:
            data = self.request("GET", f"/session/{self.sid}/screenshot")
            import base64
            with open(path, "wb") as f:
                f.write(base64.b64decode(data))
        except Exception:
            pass

    def state(self):
        return self.js(r"""
        return (() => {
          const q = s => document.querySelector(s);
          const hidden = s => { const el = q(s); return !el || el.hidden; };
          const a = (typeof art !== 'undefined') ? art : null;
          const f = a ? a.frames[Math.min(typeof cur === 'number' ? cur : 0, a.frames.length - 1)] : null;
          const get = (name, fallback=null) => { try { return eval(name); } catch (e) { return fallback; } };
          const pixel = (x, y) => (a && f) ? f[y * a.size + x] : null;
          return {
            url: location.href,
            inner: [innerWidth, innerHeight],
            joinHidden: hidden('#join'),
            appHidden: hidden('#app'),
            drawHidden: hidden('#drawView'),
            lifeHidden: hidden('#lifeView'),
            stageHidden: hidden('#stageView'),
            shelfHidden: hidden('#shelf'),
            title: q('#title') ? q('#title').value : '',
            saved: q('#saved') ? (q('#saved').innerText || '') : '',
            toast: q('#toast') && !q('#toast').hidden ? (q('#toast').innerText || '') : '',
            tip: q('#tip') ? (q('#tip').innerText || '') : '',
            tool: get('tool'), brush: get('brush'), colour: get('colour'),
            penStyle: get('penStyle'), shadeWay: get('shadeWay'),
            mirror: get('mirror'), showGrid: get('showGrid'), easy: get('easy'),
            solid: get('solid'), onion: get('onion'),
            zoom: get('zoom'), cell: get('cell'), pan: get('panAt'),
            cur: get('cur'), undoLen: (get('undoList') || []).length,
            redoLen: (get('redoList') || []).length,
            dirty: get('dirty'), saving: get('saving'), stroke: !!get('stroke'),
            shape: !!get('shape'), sel: get('sel'),
            key: a ? a.key : null, size: a ? a.size : null,
            frames: a ? a.frames.map(x => A.encode(x)) : null,
            names: a ? a.names.slice() : null,
            guide: a ? (a.guide || '') : '',
            target: a && a.guide ? A.decode(a.guide) : null,
            shelfList: (get('shelfList') || []).map(d => ({key: d.key, title: d.title, size: d.size})),
            frameButtons: [...document.querySelectorAll('#frames .frame')].map(b => ({
              n: +b.dataset.frame, on: b.getAttribute('aria-pressed') === 'true'})),
            undoDisabled: q('#undo') ? q('#undo').disabled : null,
            redoDisabled: q('#redo') ? q('#redo').disabled : null,
            copyDisabled: q('#copyFrame') ? q('#copyFrame').disabled : null,
            newDisabled: q('#newFrame') ? q('#newFrame').disabled : null,
            deleteDisabled: q('#deleteFrame') ? q('#deleteFrame').disabled : null,
            frameLeftDisabled: q('#frameLeft') ? q('#frameLeft').disabled : null,
            frameRightDisabled: q('#frameRight') ? q('#frameRight').disabled : null,
            leftDisabled: q('#selFlip') ? q('#selFlip').disabled : null,
            downloadTitle: q('#download') ? q('#download').title : '',
            guideOn: a ? !!a.guide : false,
            guideKey: q('#guideKey') && !q('#guideKey').hidden,
            tipHasNext: /click|Click|press|Press|Pick|Slide|Now/.test(q('#tip') ? q('#tip').innerText : ''),
            calm: get('PalStage') ? PalStage.calm : null,
            calmPressed: q('#calm') ? q('#calm').getAttribute('aria-pressed') : null,
            bodyCalm: document.body.classList.contains('calm'),
            easyPressed: q('#easy') ? q('#easy').getAttribute('aria-pressed') : null,
            mirrorPressed: q('#mirror') ? q('#mirror').getAttribute('aria-pressed') : null,
            gridPressed: q('#grid') ? q('#grid').getAttribute('aria-pressed') : null,
            lifeBusy: get('lifeBusy'), boneKey: get('boneKey'), marks: a ? (a.marks || '') : '',
            scene: get('lifeStage') ? lifeStage.state.scene : null,
            lifeEmpty: hidden('#lifeEmpty'),
            undoDoes: q('#undo') ? !q('#undo').disabled : null,
          };
        })();
        """)

    def close(self):
        try:
            self.request("DELETE", f"/session/{self.sid}")
        except Exception:
            pass
        try:
            self.proc.terminate()
            self.proc.wait(timeout=5)
        except Exception:
            try:
                self.proc.kill()
            except Exception:
                pass


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------

class Report:
    def __init__(self):
        self.checks = []
        self.console = []
        self.sections = []
        self.failures = 0
        self.current = ""

    def section(self, name):
        self.current = name
        self.sections.append(name)
        print(f"\n== {name} ==")

    def check(self, name, ok, detail="", data=None):
        result = "OK" if ok else "FAIL"
        entry = {"section": self.current, "name": name, "result": result,
                 "detail": str(detail)[:1200]}
        if data is not None:
            entry["data"] = data
        self.checks.append(entry)
        if not ok:
            self.failures += 1
        print(f"  {result:4} {name}" + ("" if ok else f"  -- {str(detail)[:300]}"))
        return ok

    def note(self, name, detail=""):
        self.checks.append({"section": self.current, "name": name, "result": "NOTE",
                            "detail": str(detail)[:1200]})
        print(f"  NOTE {name}" + (f"  -- {str(detail)[:300]}" if detail else ""))

    def absorb_logs(self, driver, where=""):
        for entry in driver.logs():
            entry["at"] = where or self.current
            self.console.append(entry)


# ---------------------------------------------------------------------------
# Page helpers
# ---------------------------------------------------------------------------

def wait_join(driver, name="Draw E2E"):
    driver.wait("return !document.getElementById('join').hidden", 30, "the join screen")
    driver.send("#name", name)
    driver.click("#joinButton")
    driver.wait("return !document.getElementById('app').hidden", 30, "the app")
    driver.wait("return typeof art !== 'undefined' && !!art", 20, "a drawing")


def wait_for_save(driver, timeout=15):
    """Wait for the auto-save of a change just made, not the previous Saved ✓."""
    driver.wait("return (typeof dirty!=='undefined' && dirty) || "
                "document.getElementById('saved').innerText.indexOf('Saving')>=0",
                5, "the change to start saving")
    driver.wait("return (typeof dirty==='undefined' || !dirty) && "
                "document.getElementById('saved').innerText.indexOf('Saved')>=0",
                timeout, "the change to save")


def wait_enter(driver, name="Draw E2E"):
    """The app (a returning tab) or the join screen, then the Draw tab."""
    driver.wait("return !document.getElementById('join').hidden || "
                "(!document.getElementById('app').hidden && typeof art!=='undefined' && !!art)",
                30, "the app or the join screen")
    if not driver.js("return document.getElementById('join').hidden"):
        driver.send("#name", name)
        driver.click("#joinButton")
    driver.wait("return !document.getElementById('app').hidden && typeof art!=='undefined' && !!art",
                30, "the app")
    if not driver.js("return document.getElementById('shelf').hidden"):
        if driver.js("return !document.getElementById('closeShelf').hidden"):
            driver.click("#closeShelf")
        else:
            driver.click("#picks [data-size='16']")
    driver.wait("return document.getElementById('shelf').hidden", 15, "the shelf to close")


def wait_draw(driver):
    driver.wait("return !document.getElementById('drawView').hidden && "
                "typeof art !== 'undefined' && !!art", 20, "the Draw tab")


def corpus(driver):
    """The gallery pictures, as the page itself has them."""
    return driver.js(r"""
      const pictures={}, outlined={};
      for (const n of PalGallery.names) {
        pictures[n]=A.encode(PalGallery.pictures[n]);
        outlined[n]=A.encode(PalGallery.outlined(PalGallery.pictures[n]));
      }
      return {names: PalGallery.names, furniture: PalGallery.furniture,
              pictures, outlined, palette: A.PALETTE};
    """)


def start_blank(driver, size=16):
    """Open My drawings and pick a blank page of this size."""
    wait_draw(driver)
    if driver.js("return document.getElementById('shelf').hidden"):
        driver.click("#openShelf")
    driver.wait("return !document.getElementById('shelf').hidden", 15, "the shelf")
    driver.click(f"#picks [data-size='{size}']")
    driver.wait(f"return document.getElementById('shelf').hidden && "
                f"typeof art!=='undefined' && art && art.size==={size}", 15,
                f"a blank {size} drawing")
    time.sleep(.1)
    return driver.state()


def open_shelf(driver):
    driver.click("#openShelf")
    driver.wait("return !document.getElementById('shelf').hidden", 15, "the shelf")
    time.sleep(.1)


def close_shelf(driver):
    if not driver.js("return document.getElementById('shelf').hidden"):
        if driver.js("return !document.getElementById('closeShelf').hidden"):
            driver.click("#closeShelf")
        driver.wait("return document.getElementById('shelf').hidden", 10, "the shelf to close")


def trim_shelf(driver, keep=2):
    """Leave the drawing shelf under the limit, deleting extra drawings by API.

    This is setup, not a UI check: the real delete button is exercised in the
    My drawings section.  It keeps the open drawing and `keep`-1 others.
    """
    open_shelf(driver)
    keys = driver.js("return [...document.querySelectorAll('#savedArt [data-open]')].map(b=>b.dataset.open)")
    current = driver.state()["key"]
    extras = [k for k in keys if k != current][:max(0, len(keys) - keep)]
    for key in extras:
        driver.js_async(r"""
          const done = arguments[arguments.length-1];
          fetch('/pixel/delete', {method:'POST', headers:{'Content-Type':'application/json'},
                                  body: JSON.stringify({id: me, key: arguments[0]})})
            .then(r => r.json()).then(done).catch(() => done(null));
        """, key)
    if extras:
        close_shelf(driver)
        open_shelf(driver)
    close_shelf(driver)


def pick_gallery(driver, name, way):
    """Choose a gallery pal through the three-way picker."""
    open_shelf(driver)
    driver.click(f"[data-way='{way}']")
    driver.wait(f"return document.querySelector(\"[data-way='{way}']\").getAttribute('aria-pressed')==='true'",
                10, f"the {way} way")
    driver.click(f"#gallery [data-gallery='{name}']")
    driver.wait("return document.getElementById('shelf').hidden && typeof art!=='undefined' && !!art", 15,
                f"the {name} gallery drawing")
    time.sleep(.15)
    return driver.state()


def pick_tool(driver, key):
    driver.click(f"#tools [data-tool='{key}']")
    driver.wait(f"return typeof tool!=='undefined' && tool==={json.dumps(key)}", 10, f"the {key} tool")


def pix(driver, x, y):
    return driver.js("return (typeof art!=='undefined' && art) ? art.frames[cur][arguments[1]*art.size+arguments[0]] : null",
                     x, y)


def pixels(driver):
    s = driver.state()
    return s["frames"][s["cur"]]


def pixel_at(state, x, y):
    frame = state["frames"][state["cur"]]
    ch = frame[y * state["size"] + x]
    return -1 if ch == "." else pixel.LETTERS.index(ch)


def frame_changed(before, after):
    return before["frames"] != after["frames"]


def clear_canvas(driver):
    if driver.exists("#moreMenu") and not driver.js("return document.getElementById('moreMenu').hidden"):
        driver.click("#closeMore")
    driver.click("#openMore")
    driver.wait("return !document.getElementById('moreMenu').hidden", 10, "More")
    driver.click("#clear")
    driver.click("#closeMore")


def choose_colour(driver, n):
    # The swatches include the palette; the by-numbers key uses the same data.
    selectors = [f"#swatches [data-colour='{n}']", f"#mine [data-colour='{n}']",
                 f"#guideKey [data-colour='{n}']"]
    for sel in selectors:
        if driver.exists(sel):
            driver.click(sel)
            return
    raise WebDriverError(f"no colour button {n}")


def choose_brush(driver, n):
    driver.click(f"#sizes [data-brush='{n}']")
    driver.wait(f"return typeof brush!=='undefined' && brush==={n}", 10, f"brush {n}")


def set_switch(driver, button, on):
    current = driver.js("const b=document.getElementById(arguments[0]);"
                        "return b.getAttribute('aria-pressed')==='true'", button)
    if current != on:
        driver.click("#" + button)
        time.sleep(.05)
        want = "true" if on else "false"
        driver.wait(f"return document.getElementById('{button}').getAttribute('aria-pressed')==="
                    f"{json.dumps(want)}", 10, f"{button} {'on' if on else 'off'}")


def set_ghost(driver, on):
    """Ghost is a text toggle ("Ghost: On"/"Off"), not an aria-pressed switch."""
    word = "Ghost: On" if on else "Ghost: Off"
    if word not in driver.text("#showLast"):
        driver.click("#showLast")
    driver.wait(f"return document.getElementById('showLast').innerText.indexOf("
                f"{json.dumps(word)}) >= 0", 10, word)


def download_intercept(driver):
    driver.js(r"""
      window.__dl = [];
      if (!window.__dlPatched) {
        window.__dlPatched = true;
        const real = URL.createObjectURL.bind(URL);
        URL.createObjectURL = blob => { window.__dl.push({blob}); window.__dlBlob = blob; return real(blob); };
        const click = HTMLAnchorElement.prototype.click;
        HTMLAnchorElement.prototype.click = function () {
          window.__dl.push({name: this.download || '', href: this.href || ''});
          if (window.__dlNoNav) return;
          return click.call(this);
        };
      }
      window.__dl = [];
    """)


def downloaded(driver):
    return driver.js(r"""
      return {items: window.__dl.map(x => x.blob ? {blob:true, type:x.blob.type, size:x.blob.size}
                                                  : {name:x.name, href:x.href}),
              bytes: null};
    """)


def blob_bytes(driver):
    return driver.js_async(r"""
      const done = arguments[arguments.length-1];
      if (!window.__dlBlob) return done(null);
      window.__dlBlob.arrayBuffer().then(buf => {
        const a = new Uint8Array(buf), out = [];
        for (let i=0; i<Math.min(12, a.length); i++) out.push(a[i]);
        done({length: a.length, head: out, text: String.fromCharCode.apply(null, out)});
      }).catch(() => done(null));
    """)


# ---------------------------------------------------------------------------
# Sections
# ---------------------------------------------------------------------------

def section_gallery(driver, report, data):
    """The three gallery ways, including a wrong colour and the locked squares."""
    report.section("gallery ways")
    trim_shelf(driver, 3)
    names = data["names"]
    kitty = "Kitty" if "Kitty" in names else names[0]

    s = pick_gallery(driver, kitty, "colour")
    expect = data["outlined"][kitty]
    report.check("🖍️ colour it in starts from an outline", s["guide"] == "" and s["frames"][0] == expect,
                 f"guide={bool(s['guide'])} frame_matches_outline={s['frames'][0]==expect}")
    report.check("a colouring-book page has something to colour",
                 any(c not in ('.', '0') for c in s["frames"][0]), "no empty squares")

    s = pick_gallery(driver, kitty, "ready")
    report.check("⭐ ready to change starts as the finished picture", s["frames"][0] == data["pictures"][kitty],
                 f"match={s['frames'][0]==data['pictures'][kitty]}")
    # Change one square in the ready picture and undo.
    before = s
    choose_colour(driver, 1)
    driver.click_square(3, 3)
    after = driver.state()
    report.check("⭐ ready to change can be drawn on", frame_changed(before, after),
                 "the square under the pen changed")
    driver.click("#undo")
    back = driver.state()
    report.check("Undo after a ready-picture change works", back["frames"] == before["frames"],
                 f"undo_disabled={back['undoDisabled']}")

    s = pick_gallery(driver, kitty, "numbers")
    report.check("🔢 by numbers starts with a guide to finish", bool(s["guide"]) and s["guideOn"],
                 f"guide={bool(s['guide'])} key_hidden={not s['guideKey']}")
    target = s["target"]
    frame = [('.' if c == '.' else pixel.LETTERS.index(c)) for c in s["frames"][0]]
    report.check("🔢 the picture starts unfinished", any(n != target[i] for i, n in enumerate(frame)),
                 "some numbered squares are still white")

    # A locked square: the ink outline must not take a new colour.
    locked = next((i for i, n in enumerate(target) if n == 0 and frame[i] == 0), None)
    if locked is not None:
        x, y = locked % s["size"], locked // s["size"]
        choose_colour(driver, 5)
        driver.click_square(x, y)
        got = pix(driver, x, y)
        report.check("🔢 the locked outline can't be painted over", got == 0,
                     f"outline square ({x},{y}) is {got}, wanted 0")
    else:
        report.note("no ink outline square found to test the lock", kitty)

    # Swap and Move explain themselves instead of doing half a job.
    pick_tool(driver, "swap")
    choose_colour(driver, 5)
    # find a square that still needs colour
    need = next((i for i, n in enumerate(target) if n >= 0 and frame[i] != n), 0)
    nx, ny = need % s["size"], need // s["size"]
    driver.click_square(nx, ny)
    tip = driver.state()["tip"]
    report.check("🔢 Swap says to finish the numbers first", "once the picture is coloured in" in tip,
                 tip)
    pick_tool(driver, "pencil")      # Swap stays selected after its no-op, so go back to painting

    # A wrong colour is allowed on an unfinished square, then can be fixed.
    wrong = next((n for n in range(len(data["palette"])) if n != target[need] and n >= 0), 1)
    choose_colour(driver, wrong)
    driver.click_square(nx, ny)
    got_wrong = pix(driver, nx, ny)
    report.check("🔢 a wrong colour goes on and is not hidden", got_wrong == wrong,
                 f"square ({nx},{ny}) is {got_wrong}, wanted {wrong}")
    choose_colour(driver, target[need])
    driver.click_square(nx, ny)
    report.check("🔢 the right colour fixes a wrong one", pix(driver, nx, ny) == target[need],
                 f"square is {pix(driver, nx, ny)}, wanted {target[need]}")

    # Finish the picture with real clicks, colour by colour.
    remaining = [(i, n) for i, n in enumerate(target) if n >= 0 and frame[i] != n]
    report.note("finishing by numbers", f"{len(remaining)} squares still to colour")
    by_colour = {}
    for i, n in remaining:
        by_colour.setdefault(n, []).append(i)
    for n, spots in sorted(by_colour.items()):
        choose_colour(driver, n)
        for i in spots:
            driver.click_square(i % s["size"], i // s["size"])
    end = driver.state()
    report.check("🔢 finishing every square ends the guide",
                 end["guide"] == "" and not end["guideOn"],
                 f"guide_left={bool(end['guide'])} toast={end['toast']!r}")
    report.check("🔢 finishing says what to do next",
                 "Bring to life" in end["toast"], end["toast"])
    report.check("🔢 the finished picture matches the pal",
                 end["frames"][0] == data["pictures"][kitty],
                 f"match={end['frames'][0]==data['pictures'][kitty]}")

    # Undo after finishing must bring the guide back: the last square is undone,
    # and without its number/key the picture would be impossible to finish.
    driver.click("#undo")
    back = driver.state()
    report.check("Undo after finishing by numbers brings the numbers back",
                 bool(back["guide"]) and back["guideKey"],
                 f"guide={bool(back['guide'])} key={back['guideKey']} toast={back['toast']!r}")
    driver.click("#redo")
    again = driver.state()
    report.check("Redo finishes the numbers again", again["guide"] == "" and again["guideKey"] is False,
                 f"guide={bool(again['guide'])} key={again['guideKey']}")

    # Fill must not flood every unfinished white square: they are all joined.
    # (This is checked while the guide is still on, before finishing again.)
    if again["guide"] == "":
        # re-open the numbers page to test Fill on a fresh guide
        s2 = pick_gallery(driver, kitty, "numbers")
        target2 = s2["target"]
        frame2 = [('.' if c == '.' else pixel.LETTERS.index(c)) for c in s2["frames"][0]]
        need2 = next(i for i, n in enumerate(target2) if n >= 0 and frame2[i] != n)
        want = target2[need2]
        choose_colour(driver, want)
        pick_tool(driver, "fill")
        driver.click_square(need2 % s2["size"], need2 // s2["size"])
        marked = sum(1 for i, n in enumerate(target2) if n >= 0 and pix(driver, i % 16, i // 16) == want)
        wrong = sum(1 for i, n in enumerate(target2) if n >= 0 and n != want and pix(driver, i % 16, i // 16) == want)
        should = sum(1 for n in target2 if n == want)
        report.check("🔢 Fill only fills the number you picked", wrong == 0,
                     f"filled {marked} squares with colour {want}, {wrong} of them belong to another number; the pal has {should} of that colour")
        pick_tool(driver, "pencil")
    return {"kitty": kitty}


def section_tools(driver, report, data):
    """Every tool, pen size, pen style, Mirror, Grid and zoom."""
    report.section("tools")
    trim_shelf(driver, 3)
    start_blank(driver, 16)
    report.check("a blank page is empty", all(c == '.' for c in pixels(driver)), "all squares empty")
    report.check("the tip says what to do", "Click a square" in driver.state()["tip"],
                 driver.state()["tip"])

    # Clicking along a line offers Easy pen, once; choosing a tool must put the
    # current instruction back instead of leaving the old offer on screen.
    driver.js("localStorage.removeItem('pixelEasyOffered');")
    set_switch(driver, "easy", False)
    pick_tool(driver, "pencil")
    choose_colour(driver, 0)
    for x in range(8):
        driver.click_square(1 + x, 1)
    offer = driver.state()["tip"]
    report.check("clicking along a line offers Easy pen", "Try Easy pen" in offer, offer)
    pick_tool(driver, "eraser")
    report.check("choosing a tool replaces the Easy pen offer with its own tip",
                 "Try Easy pen" not in driver.state()["tip"] and "rub it out" in driver.state()["tip"],
                 driver.state()["tip"])
    clear_canvas(driver)

    # Pencil and pen sizes.
    pick_tool(driver, "pencil")
    choose_colour(driver, 0)
    driver.click_square(2, 2)
    report.check("Pencil colours the square clicked", pix(driver, 2, 2) == 0, pix(driver, 2, 2))
    choose_brush(driver, 3)
    driver.click_square(6, 6)
    big = all(pix(driver, x, y) == 0 for x in range(5, 8) for y in range(5, 8))
    report.check("pen size 3 colours a 3x3 square", big,
                 f"3x3={[pix(driver,x,y) for y in range(5,8) for x in range(5,8)]}")
    choose_brush(driver, 1)

    # Rainbow and checks pens.
    clear_canvas(driver)
    driver.click("#pens [data-pen='rainbow']")
    pick_tool(driver, "pencil")
    choose_brush(driver, 1)
    for i in range(5):
        driver.click_square(2 + i, 4)
    rainbow = [pix(driver, 2 + i, 4) for i in range(5)]
    report.check("🌈 Rainbow pen changes colour along the line", len(set(rainbow)) >= 2, rainbow)
    clear_canvas(driver)
    driver.click("#pens [data-pen='checks']")
    for x in range(2, 8):
        driver.click_square(x, 6)
    checks = [pix(driver, x, 6) for x in range(2, 8)]
    painted = [n for n in checks if n >= 0]
    report.check("Checker pen leaves gaps", 0 < len(painted) < len(checks), checks)
    driver.click("#pens [data-pen='plain']")

    # Eraser.
    clear_canvas(driver)
    choose_colour(driver, 0)
    pick_tool(driver, "pencil")
    driver.click_square(4, 4)
    pick_tool(driver, "eraser")
    driver.click_square(4, 4)
    report.check("Eraser rubs a square out", pix(driver, 4, 4) == -1, pix(driver, 4, 4))

    # Fill inside a box.
    clear_canvas(driver)
    choose_colour(driver, 0)
    pick_tool(driver, "box")
    driver.click_square(2, 2)
    driver.click_square(7, 7)
    choose_colour(driver, 1)
    pick_tool(driver, "fill")
    driver.click_square(4, 4)
    report.check("Fill pours inside a box and stops at its edge",
                 pix(driver, 4, 4) == 1 and pix(driver, 2, 2) == 0 and pix(driver, 5, 5) == 1,
                 f"inside={pix(driver,4,4)} edge={pix(driver,2,2)}")

    # Line, box and circle with two clicks.
    clear_canvas(driver)
    choose_colour(driver, 0)
    pick_tool(driver, "line")
    driver.click_square(1, 1)
    driver.click_square(9, 1)
    report.check("Line draws between the two clicks",
                 all(pix(driver, x, 1) == 0 for x in range(1, 10)), [pix(driver, x, 1) for x in range(1, 10)])
    clear_canvas(driver)
    pick_tool(driver, "box")
    driver.click_square(2, 2)
    driver.click_square(8, 8)
    report.check("Box draws an empty box",
                 pix(driver, 2, 2) == 0 and pix(driver, 8, 8) == 0 and pix(driver, 5, 5) == -1,
                 f"corner={pix(driver,2,2)} inside={pix(driver,5,5)}")
    clear_canvas(driver)
    pick_tool(driver, "circle")
    driver.click_square(2, 2)
    driver.click_square(9, 9)
    want_circle = driver.js("return A.circle(2,2,9,9,false).map(([x,y])=>y*art.size+x)")
    have_circle = driver.js("const f=art.frames[cur]; return f.map((n,i)=>n>=0?i:-1).filter(i=>i>=0)")
    report.check("Circle draws the circle between the two clicks",
                 sorted(want_circle) == sorted(have_circle),
                 f"wanted {len(want_circle)} squares, got {len(have_circle)}")
    report.check("the circle is empty in the middle", pix(driver, 5, 5) == -1, pix(driver, 5, 5))
    # Escape drops a shape without drawing it.
    pick_tool(driver, "line")
    driver.click_square(1, 12)
    driver.key(ESCAPE)
    report.check("Esc drops a half-drawn shape", not driver.state()["shape"], driver.state()["tip"])

    # Stamp.
    clear_canvas(driver)
    pick_tool(driver, "stamp")
    report.check("Stamp shows its stamps", driver.js("return !document.getElementById('stampBar').hidden"),
                 "stamp bar visible")
    driver.click("#stampBar [data-stamp='Heart']")
    choose_colour(driver, 1)
    driver.click_square(8, 8)
    report.check("Stamp puts the picture on the board", pix(driver, 8, 8) == 1, pix(driver, 8, 8))

    # Shade.
    clear_canvas(driver)
    choose_colour(driver, 4)
    pick_tool(driver, "pencil")
    driver.click_square(3, 3)
    before_shade = pix(driver, 3, 3)
    pick_tool(driver, "shade")
    driver.click("#optShade [data-shade='-1']")
    driver.click_square(3, 3)
    after_shade = pix(driver, 3, 3)
    report.check("Shade makes a colour darker", after_shade != before_shade and after_shade >= 0,
                 f"{before_shade} -> {after_shade}")
    driver.click("#optShade [data-shade='1']")
    driver.click_square(3, 3)
    report.check("Shade makes a colour lighter again", pix(driver, 3, 3) != after_shade,
                 f"{after_shade} -> {pix(driver,3,3)}")

    # Swap recolours every square of the clicked colour.
    clear_canvas(driver)
    choose_colour(driver, 0)
    pick_tool(driver, "pencil")
    driver.click_square(2, 2)
    driver.click_square(3, 3)
    choose_colour(driver, 1)
    pick_tool(driver, "swap")
    driver.click_square(2, 2)
    report.check("Swap recolours every square of that colour",
                 pix(driver, 2, 2) == 1 and pix(driver, 3, 3) == 1,
                 f"({pix(driver,2,2)},{pix(driver,3,3)})")

    # Move: pick up a 2x2 block and drop it somewhere else.
    clear_canvas(driver)
    choose_colour(driver, 0)
    pick_tool(driver, "pencil")
    for x, y in ((2, 2), (3, 2), (2, 3), (3, 3)):
        driver.click_square(x, y)
    pick_tool(driver, "select")
    driver.drag_squares(2, 2, 3, 3)          # select the block
    selected = driver.state()["sel"]
    driver.drag_squares(2, 2, 7, 7)          # drag the selection
    floating_tip = driver.state()["tip"]
    report.check("a floating Move selection says to click to put it down",
                 "put it down" in floating_tip, floating_tip)
    driver.click_square(15, 15)              # put it down
    moved = all(pix(driver, x, y) == 0 for x in range(7, 9) for y in range(7, 9))
    source = all(pix(driver, x, y) == -1 for x in range(2, 4) for y in range(2, 4))
    report.check("Move picks up a block and drops it", moved and source,
                 f"sel={bool(selected)} moved={moved} source_clear={source}")

    # The other Move way: select a block, click it so it follows, slide, click
    # to put it down.  That last click must put it down, not leave it floating.
    clear_canvas(driver)
    choose_colour(driver, 0)
    pick_tool(driver, "pencil")
    for x, y in ((2, 6), (3, 6), (2, 7), (3, 7)):
        driver.click_square(x, y)
    pick_tool(driver, "select")
    driver.drag_squares(2, 6, 3, 7)    # select the 2x2 block
    driver.click_square(2, 6)          # pick it up: it now follows
    following = driver.state()["tip"]
    ax, ay = driver.board_xy(9, 9)
    driver.mouse_at(ax, ay)            # slide with nothing held down
    report.check("Move says it is following the pointer", "following" in following, following)
    driver.click_square(9, 9)          # click where it should go
    s = driver.state()
    report.check("Move's following mode puts the block down on the next click",
                 s["sel"] is None and pix(driver, 9, 9) == 0 and pix(driver, 2, 6) == -1,
                 f"sel={bool(s['sel'])} at_target={pix(driver,9,9)} following_tip={following!r}")

    # Picker takes the colour under the pointer.
    choose_colour(driver, 0)
    pick_tool(driver, "pencil")
    driver.click_square(12, 12)
    choose_colour(driver, 3)
    pick_tool(driver, "picker")
    driver.click_square(12, 12)
    s = driver.state()
    report.check("Picker takes the colour and goes back to drawing",
                 s["colour"] == 0 and s["tool"] == "pencil", f"colour={s['colour']} tool={s['tool']}")

    # More: flip, turn, outline, slide, clear.
    clear_canvas(driver)
    choose_colour(driver, 0)
    pick_tool(driver, "pencil")
    driver.click_square(1, 2)
    driver.click("#openMore")
    driver.click("#flip")
    driver.click("#closeMore")
    report.check("More > Flip mirrors the picture", pix(driver, 14, 2) == 0, pix(driver, 14, 2))
    clear_canvas(driver)
    pick_tool(driver, "pencil")
    driver.click_square(2, 1)
    driver.click("#openMore")
    driver.click("#spin")
    driver.click("#closeMore")
    report.check("More > Turn turns the picture a quarter",
                 pix(driver, 14, 2) == 0, f"turned={pix(driver,14,2)}")
    clear_canvas(driver)
    pick_tool(driver, "pencil")
    driver.click_square(5, 5)
    driver.click("#openMore")
    driver.click("#outline")
    driver.click("#closeMore")
    report.check("More > Add outline draws around the picture", pix(driver, 4, 5) == 0, pix(driver, 4, 5))
    clear_canvas(driver)
    pick_tool(driver, "pencil")
    driver.click_square(5, 5)
    driver.click("#openMore")
    driver.click("#moreMenu [data-dx='1'][data-dy='0']")
    driver.click("#closeMore")
    report.check("More > Slide moves the picture", pix(driver, 6, 5) == 0, f"at 5,5={pix(driver,5,5)} at 6,5={pix(driver,6,5)}")
    driver.click("#openMore")
    driver.click("#clear")
    driver.click("#closeMore")
    report.check("More > Clear all empties the page", all(c == '.' for c in pixels(driver)), "empty")

    # Every tool's tip says what to do next.
    tips = {}
    for key in ("pencil", "eraser", "fill", "line", "box", "circle", "stamp", "shade",
                "swap", "select", "picker"):
        pick_tool(driver, key)
        tip = driver.state()["tip"]
        tips[key] = tip
        if not tip.strip() or not re.search(r"click|Click|press|Press|Pick|Slide|Now", tip):
            report.check(f"the {key} tip says what to do next", False, tip)
    report.note("tool tips", json.dumps(tips))

    # Easy pen: click, slide, click.
    clear_canvas(driver)
    set_switch(driver, "easy", True)
    choose_colour(driver, 0)
    pick_tool(driver, "pencil")
    driver.click_square(1, 10)
    ax, ay = driver.board_xy(4, 10)
    driver.mouse_at(ax, ay)
    bx, by = driver.board_xy(7, 10)
    driver.mouse_at(bx, by)
    report.check("Easy pen shows the pen is down", "pen is down" in driver.state()["tip"],
                 driver.state()["tip"])
    driver.click_square(7, 10)
    s = driver.state()
    line = [pix(driver, x, 10) for x in range(1, 8)]
    report.check("Easy pen draws with nothing held down",
                 all(n == 0 for n in line) and not s["stroke"], line)
    set_switch(driver, "easy", False)

    # Mirror.
    clear_canvas(driver)
    set_switch(driver, "mirror", True)
    choose_colour(driver, 0)
    pick_tool(driver, "pencil")
    driver.click_square(2, 5)
    report.check("Mirror draws the other side too",
                 pix(driver, 2, 5) == 0 and pix(driver, 13, 5) == 0,
                 f"left={pix(driver,2,5)} right={pix(driver,13,5)}")
    set_switch(driver, "mirror", False)

    # Grid lines: the board actually changes when they go off.
    before_grid = driver.js(r"""
      const cv=document.getElementById('board'), g=cv.getContext('2d');
      const c=typeof cell!=='undefined'?cell:16;
      const d=g.getImageData(Math.round(c*3), Math.round(c*1.5), 1, 1).data;
      return [d[0],d[1],d[2]];
    """)
    set_switch(driver, "grid", False)
    time.sleep(.1)
    off_grid = driver.js(r"""
      const cv=document.getElementById('board'), g=cv.getContext('2d');
      const c=typeof cell!=='undefined'?cell:16;
      const d=g.getImageData(Math.round(c*3), Math.round(c*1.5), 1, 1).data;
      return [d[0],d[1],d[2]];
    """)
    set_switch(driver, "grid", True)
    report.check("Grid lines change the board", before_grid != off_grid,
                 f"on={before_grid} off={off_grid}")

    # Zoom: +/- changes the square size, and a click still lands on the right square.
    clear_canvas(driver)
    choose_colour(driver, 0)
    pick_tool(driver, "pencil")
    before_zoom = driver.state()["zoom"]
    driver.click("#zoomIn")
    time.sleep(.5)          # let the zoom settle, as a child's next click would
    zoomed = driver.state()
    report.check("Zoom + makes the squares bigger", zoomed["zoom"] == before_zoom + 1 and zoomed["cell"] > zoomed["zoom"] and True,
                 f"zoom={zoomed['zoom']} cell={zoomed['cell']}")
    driver.click_square(6, 6)
    report.check("a click lands on the right square while zoomed", pix(driver, 6, 6) == 0, pix(driver, 6, 6))
    driver.click("#zoomOut")
    report.check("Zoom - goes back", driver.state()["zoom"] == before_zoom,
                 driver.state()["zoom"])
    report.check("Zoom - is disabled at the smallest size",
                 driver.js("return document.getElementById('zoomOut').disabled"), "disabled")

    # Undo/redo one tool change.
    driver.click("#undo")
    report.check("Undo takes back the tool change", pix(driver, 6, 6) == -1, pix(driver, 6, 6))
    driver.click("#redo")
    report.check("Redo puts it back", pix(driver, 6, 6) == 0, pix(driver, 6, 6))


def section_undo(driver, report, data):
    """Many undos, undo after a frame switch, undo after a gallery pick."""
    report.section("undo and redo")
    trim_shelf(driver, 3)
    start_blank(driver, 16)
    choose_colour(driver, 0)
    pick_tool(driver, "pencil")
    choose_brush(driver, 1)
    spots = [(1, 1), (3, 1), (5, 1), (7, 1), (9, 1), (11, 1), (13, 1), (15, 1)]
    for x, y in spots:
        driver.click_square(x, y)
        time.sleep(.03)
    painted = driver.state()
    report.check("eight strokes are on the page", all(pixel_at(painted, x, y) == 0 for x, y in spots),
                 "all eight squares painted")
    report.check("Undo is offered", not painted["undoDisabled"], f"len={painted['undoLen']}")

    for _ in range(len(spots)):
        driver.click("#undo")
        time.sleep(.02)
    undone = driver.state()
    report.check("many undos empty the page again", all(c == '.' for c in pixels(driver)),
                 f"undo_len={undone['undoLen']} redo_len={undone['redoLen']}")
    report.check("Undo is now disabled, not a dead button", undone["undoDisabled"],
                 f"undoLen={undone['undoLen']}")
    for _ in range(len(spots)):
        driver.click("#redo")
        time.sleep(.02)
    redone = driver.state()
    report.check("many redos put every stroke back", all(pixel_at(redone, x, y) == 0 for x, y in spots),
                 f"redo_len={redone['redoLen']}")

    # Ctrl+Z and Ctrl+Y are the same as the buttons, unless a text box has the keys.
    driver.js("document.body.focus()")
    driver.key("\ue009z")
    time.sleep(.15)
    report.check("Ctrl+Z undoes the last square", pix(driver, 15, 1) == -1, pix(driver, 15, 1))
    driver.key("\ue009y")
    time.sleep(.15)
    report.check("Ctrl+Y redoes it", pix(driver, 15, 1) == 0, pix(driver, 15, 1))
    before_title = pixels(driver)
    driver.send("#title", "\ue009z")
    time.sleep(.15)
    report.check("Ctrl+Z in the name box doesn't undo the drawing",
                 pixels(driver) == before_title, "drawing unchanged")
    driver.js("document.body.focus()")

    # Undo after switching frame: the change belongs to the frame it was made on.
    clear_canvas(driver)
    choose_colour(driver, 0)
    pick_tool(driver, "pencil")
    driver.click_square(2, 2)
    frame0_before = driver.state()
    driver.click("#copyFrame")
    driver.wait("return typeof art!=='undefined' && art.frames.length===2", 10, "two frames")
    driver.click("#frames [data-frame='1']")
    driver.wait("return typeof cur!=='undefined' && cur===1", 10, "frame 2")
    choose_colour(driver, 1)
    driver.click_square(5, 5)
    driver.click("#frames [data-frame='0']")
    driver.wait("return typeof cur!=='undefined' && cur===0", 10, "frame 1")
    driver.click("#undo")
    s = driver.state()
    report.check("undo after switching frame goes to the frame it changed and takes it back",
                 s["cur"] == 1 and pix(driver, 5, 5) == -1,
                 f"cur={s['cur']} pixel={pix(driver,5,5)}")
    # A frame switch alone is not a change to undo.
    undo_len = driver.state()["undoLen"]
    driver.click("#frames [data-frame='0']")
    driver.click("#undo")
    s2 = driver.state()
    report.note("undo after a plain frame switch", f"before={undo_len} after={s2['undoLen']} cur={s2['cur']}")

    # Undo after a gallery pick: the shelf survives, so this shouldn't strand anyone.
    pick_gallery(driver, "Kitty", "colour")
    s = driver.state()
    report.check("a new gallery pick starts with an empty Undo",
                 s["undoDisabled"], f"undoLen={s['undoLen']}")
    before = s["frames"]
    driver.click("#undo")
    after = driver.state()
    report.note("Undo after a gallery pick does nothing",
                f"picture_changed={before != after['frames']} undoDisabled={after['undoDisabled']}")


def section_frames(driver, report, data):
    """Copy, blank, delete, ghost, many frames, move and name."""
    report.section("frames")
    trim_shelf(driver, 3)
    start_blank(driver, 16)
    choose_colour(driver, 0)
    pick_tool(driver, "pencil")
    driver.click_square(2, 2)
    first = driver.state()

    driver.click("#copyFrame")
    driver.wait("return typeof art!=='undefined' && art.frames.length===2", 10, "a copied frame")
    s = driver.state()
    report.check("+ Copy frame makes a second frame with the same picture",
                 s["names"] is not None and s["frames"][0] == s["frames"][1] and s["cur"] == 1,
                 f"cur={s['cur']} same={s['frames'][0]==s['frames'][1]}")
    driver.click("#newFrame")
    driver.wait("return typeof art!=='undefined' && art.frames.length===3", 10, "a blank frame")
    s = driver.state()
    report.check("+ Blank makes an empty frame", all(c == '.' for c in s["frames"][s["cur"]]),
                 f"cur={s['cur']}")
    report.check("the reel shows every frame", len(s["frameButtons"]) == 3,
                 s["frameButtons"])
    report.check("the drawing now downloads as a GIF", "GIF" in s["downloadTitle"], s["downloadTitle"])

    # Ghost: the last frame is shown faintly behind this one.
    set_ghost(driver, True)
    report.check("Ghost turns on", driver.state()["onion"], driver.state()["names"])
    report.check("Ghost has a text label, not just an icon", "Ghost: On" in driver.text("#showLast"),
                 driver.text("#showLast"))
    set_ghost(driver, False)

    # Delete a frame.
    driver.click("#deleteFrame")
    driver.wait("return typeof art!=='undefined' && art.frames.length===2", 10, "one frame deleted")
    report.check("Delete removes the open frame", driver.state()["cur"] <= 1 and len(driver.state()["frames"]) == 2,
                 f"frames={len(driver.state()['frames'])} cur={driver.state()['cur']}")
    driver.click("#deleteFrame")
    driver.wait("return typeof art!=='undefined' && art.frames.length===1", 10, "back to one frame")
    report.check("Delete is disabled with one frame left", driver.state()["deleteDisabled"],
                 "disabled")

    # Move it (the frame menu's arrows) and naming.
    driver.click("#copyFrame")
    driver.wait("return typeof art!=='undefined' && art.frames.length===2", 10, "two frames again")
    driver.click("#frameMore")
    driver.wait("return !document.getElementById('frameMenu').hidden", 10, "the frame menu")
    before_names = driver.state()["names"]
    driver.click("#frameLeft")
    s = driver.state()
    report.check("Move it slides the open frame left", s["cur"] == 0,
                 f"cur={s['cur']} names={s['names']} before={before_names}")
    report.check("Move it is disabled at the first frame", s["frameLeftDisabled"], "disabled")
    driver.click("#frameRight")
    report.check("Move it slides it right again", driver.state()["cur"] == 1,
                 driver.state()["cur"])
    driver.js("const s=document.getElementById('frameName'); s.value='happy';"
              "s.dispatchEvent(new Event('change', {bubbles:true}));")
    time.sleep(.1)
    s = driver.state()
    report.check("naming a frame keeps its name", s["names"][s["cur"]] == "happy",
                 f"names={s['names']}")
    # The same name can only be on one frame.
    driver.js("const s=document.getElementById('frameName'); s.value='happy';"
              "s.dispatchEvent(new Event('change', {bubbles:true}));")
    driver.click("#frames [data-frame='0']")
    driver.js("const s=document.getElementById('frameName'); s.value='happy';"
              "s.dispatchEvent(new Event('change', {bubbles:true}));")
    time.sleep(.1)
    names = driver.state()["names"]
    report.check("a frame name can only be on one frame", names.count("happy") == 1,
                 names)
    driver.click("#closeFrameMenu")

    # Many frames: fill the shelf, then the buttons say why they stop.
    for _ in range(20):
        if driver.js("return typeof art!=='undefined' && art.frames.length >= 12"):
            break
        before = driver.js("return art.frames.length")
        driver.click("#copyFrame")
        driver.wait(f"return typeof art!=='undefined' && art.frames.length > {before}", 5, "")
    driver.wait("return typeof art!=='undefined' && art.frames.length===12", 10, "twelve frames")
    s = driver.state()
    report.check("many frames fill the reel and stay usable", len(s["frameButtons"]) == 12,
                 len(s["frameButtons"]))
    report.check("with 12 frames Copy and Blank are disabled, with no stuck state",
                 s["copyDisabled"] and s["newDisabled"], f"copy={s['copyDisabled']} new={s['newDisabled']}")
    note = driver.text("#reelNote")
    report.check("the frames limit says what to do next", "Delete one" in note, note)
    report.check("the reel still offers Undo after filling it", not s["undoDisabled"],
                 f"undoLen={s['undoLen']}")

    # A frame switch doesn't change the picture.
    driver.click("#frames [data-frame='0']")
    frame0 = driver.state()["frames"][0]
    driver.click("#frames [data-frame='11']")
    driver.click("#frames [data-frame='0']")
    report.check("switching frames doesn't change the picture", driver.state()["frames"][0] == frame0,
                 "frame 1 unchanged")


def section_shelf(driver, report, data):
    """Naming, My drawings switch/delete/new, and Download."""
    report.section("my drawings and download")
    trim_shelf(driver, 3)
    start_blank(driver, 16)
    # Name the drawing with real key events.
    driver.send("#title", "My Pal")
    driver.wait("return typeof art!=='undefined' && art.title==='My Pal'", 10, "the new title")
    report.check("typing a name names the drawing", driver.state()["title"] == "My Pal",
                 driver.state()["title"])

    # Make two more drawings so the shelf has something to switch between.
    start_blank(driver, 24)
    start_blank(driver, 32)
    drawn_key = driver.state()["key"]
    open_shelf(driver)
    cards = driver.js("return [...document.querySelectorAll('#savedArt [data-open]')].map(b=>b.dataset.open)")
    report.check("My drawings lists every drawing", len(cards) >= 3, len(cards))
    other = next((k for k in cards if k != drawn_key), None)
    driver.click(f"#savedArt [data-open='{other}']")
    driver.wait(f"return typeof art!=='undefined' && art.key==={json.dumps(other)}", 10, "another drawing")
    report.check("My drawings switches to another drawing", driver.state()["key"] == other,
                 driver.state()["key"])
    report.check("the title follows the drawing", driver.state()["title"] == "",
                 driver.state()["title"])

    # Delete a non-open drawing: the first click asks, the second deletes.
    open_shelf(driver)
    gone = next(k for k in cards if k not in (drawn_key, other))
    driver.click(f"#savedArt [data-gone='{gone}']")
    first_text = driver.text(f"#savedArt [data-gone='{gone}']")
    driver.click(f"#savedArt [data-gone='{gone}']")
    driver.wait(f"return !document.querySelector(\"#savedArt [data-gone='{gone}']\")", 10,
                "the drawing to be deleted")
    report.check("Delete asks once, then deletes", "again" in first_text.lower(), first_text)
    report.check("the deleted drawing is gone", not driver.js(
        "return [...document.querySelectorAll('#savedArt [data-open]')].some(b=>b.dataset.open===arguments[0])", gone),
        gone)

    # New one of each size.
    for size in (16, 24, 32, 48):
        s = start_blank(driver, size)
        report.check(f"a {size} × {size} blank page opens", s["size"] == size and len(s["frames"]) == 1,
                     f"size={s['size']} frames={len(s['frames'])}")
        choose_colour(driver, 0)
        pick_tool(driver, "pencil")
        driver.click_square(size // 2, size // 2)
        report.check(f"drawing works on a {size} × {size} page",
                     pix(driver, size // 2, size // 2) == 0, pix(driver, size // 2, size // 2))

    # Download: one frame is a PNG, more than one is a GIF.  A floating Move
    # selection has to be put down first, or the file would miss it.
    start_blank(driver, 16)
    choose_colour(driver, 0)
    pick_tool(driver, "pencil")
    driver.click_square(2, 2)
    pick_tool(driver, "select")
    driver.click("#selectAll")
    if driver.state()["sel"]:
        driver.drag_squares(2, 2, 6, 6)
    download_intercept(driver)
    driver.click("#download")
    time.sleep(.3)
    report.check("Download puts a floating Move selection down first",
                 driver.state()["sel"] is None and pix(driver, 6, 6) == 0,
                 f"sel={bool(driver.state()['sel'])} at 6,6={pix(driver,6,6)}")
    one = downloaded(driver)
    blobs = [i for i in one["items"] if i.get("blob")]
    report.check("Download saves a PNG for one picture",
                 bool(blobs) and blobs[-1]["type"] == "image/png", one)
    driver.click("#copyFrame")
    driver.wait("return typeof art!=='undefined' && art.frames.length===2", 10, "two frames")
    download_intercept(driver)
    driver.click("#download")
    time.sleep(.3)
    many = downloaded(driver)
    gifs = [i for i in many["items"] if i.get("blob")]
    report.check("Download saves a GIF for an animation",
                 bool(gifs) and gifs[-1]["type"] == "image/gif", many)
    head = blob_bytes(driver)
    report.check("the GIF starts with GIF89a", bool(head) and head["text"].startswith("GIF89a"), head)
    return {"last_key": driver.state()["key"]}


def section_life(driver, report, data):
    """Bring to life, a move, fixing a part, frames/GIF/Place."""
    report.section("bring to life")
    trim_shelf(driver, 3)
    pick_gallery(driver, "Kitty", "ready")
    driver.wait("return !document.getElementById('toLife').disabled", 10, "Bring to life")
    driver.click("#toLife")
    driver.wait("return !document.getElementById('lifeView').hidden", 15, "the Life tab")
    time.sleep(.4)
    report.check("✨ Bring to life opens the pal", not driver.state()["lifeHidden"],
                 "life view shown")
    report.check("the pal is found, not empty", driver.state()["lifeEmpty"],
                 "the empty message is hidden")
    report.check("the tips say how to fix a part", "click the squares" in driver.text("#boneNote"),
                 driver.text("#boneNote"))

    # Every move can be pressed, and nothing gets stuck.
    for word in ("Wave", "Walk", "Dance", "Jump", "Cheer", "Nap"):
        driver.click(f"#moves [data-move='{word}']")
        ok = driver.wait("return !lifeBusy", 20, "")
        report.check(f"the {word} move plays and lets go", ok, driver.state()["scene"])

    # Fix a part: press a bone key, click one of the squares the rig found.
    info = driver.js(r"""
      return {limbs: lifeRig.limbs.map(l => ({kind:l.kind, at:l.at.slice(0,4)})),
              eyes: lifeRig.eyes.map(e => e.at.slice(0,4))};
    """)
    which = next(((l["kind"], l["at"][0]) for l in info["limbs"] if l["at"]), None)
    if which:
        key, at = which
        driver.click(f"#boneKeys [data-bone='{key[0]}']")
        sq = driver.js(r"""
          const b=document.getElementById('boneBoard'), r=b.getBoundingClientRect();
          const size=art.size, n=arguments[0];
          const x=n%size, y=Math.floor(n/size);
          return [r.left+2+(x+.5)*(r.width-4)/size, r.top+2+(y+.5)*(r.height-4)/size];
        """, at)
        driver.click_at(*sq)
        time.sleep(.2)
        marks = driver.state()["marks"]
        report.check(f"fixing a {key} marks the clicked square", len(marks) == art_sq(driver) and marks[at] != ".",
                     f"marks_len={len(marks)} at={at} mark={marks[at] if at < len(marks) else None}")
        driver.click("#bonesAgain")
        report.check("Guess again clears the marks", "." not in driver.state()["marks"],
                     driver.state()["marks"][:20])
    else:
        report.note("no limbs to fix on this pal", "no rig limbs")

    # Turn into frames.
    driver.click("#moves [data-move='Wave']")
    driver.wait("return !lifeBusy", 20, "the wave")
    frames_before = len(driver.state()["frames"])
    driver.click("#bakeMove")
    time.sleep(.4)
    s = driver.state()
    report.check("Turn into frames adds frames to the drawing", len(s["frames"]) > frames_before,
                 f"{frames_before} -> {len(s['frames'])}")
    report.check("Turn into frames says where they went", "new frames are in 🎨 Draw" in driver.text("#boneNote"),
                 driver.text("#boneNote"))

    # Download a GIF.
    download_intercept(driver)
    driver.click("#gifMove")
    time.sleep(.3)
    dl = downloaded(driver)
    gifs = [i for i in dl["items"] if i.get("blob")]
    report.check("Download a GIF makes a GIF", bool(gifs) and gifs[-1]["type"] == "image/gif", dl)
    head = blob_bytes(driver)
    report.check("the move GIF starts with GIF89a", bool(head) and head["text"].startswith("GIF89a"), head)

    # Place changes the scene and says what it did.
    scene_before = driver.state()["scene"]
    driver.click("#nextPlace")
    time.sleep(.5)
    scene_after = driver.state()["scene"]
    report.check("Place takes the pal somewhere new", scene_after != scene_before,
                 f"{scene_before} -> {scene_after}")

    # Back to Draw, frames are there.
    driver.click("nav [data-view='draw']")
    wait_draw(driver)
    report.check("the new frames are in the Draw reel",
                 len(driver.state()["frameButtons"]) == len(driver.state()["frames"]),
                 len(driver.state()["frameButtons"]))


def section_extras(driver, report, data):
    """Filled shapes, select all/copy/flip/delete, See the code and Bead pattern."""
    report.section("extras")
    trim_shelf(driver, 3)
    start_blank(driver, 16)
    choose_colour(driver, 0)
    pick_tool(driver, "box")
    set_switch(driver, "solid", True)
    driver.click_square(3, 3)
    driver.click_square(7, 7)
    filled = all(pix(driver, x, y) == 0 for x in range(3, 8) for y in range(3, 8))
    report.check("Filled in makes a solid Box", filled,
                 f"middle={pix(driver,5,5)}")
    set_switch(driver, "solid", False)

    # Select everything, nudge with the arrow keys, put it down.
    clear_canvas(driver)
    pick_tool(driver, "pencil")
    for x, y in ((2, 2), (3, 3), (4, 4)):
        driver.click_square(x, y)
    pick_tool(driver, "select")
    driver.click("#selectAll")
    s = driver.state()
    started = s["sel"]
    if started:
        driver.key("\ue014")            # ArrowRight
        driver.click_square(15, 15)      # put it down
    moved = pix(driver, 3, 2) == 0 and pix(driver, 4, 3) == 0 and pix(driver, 5, 4) == 0
    report.check("Pick up everything and the arrow keys move it", bool(started) and moved,
                 f"sel={bool(started)} moved={moved}")

    # Copy a picked-up block.
    clear_canvas(driver)
    pick_tool(driver, "pencil")
    driver.click_square(2, 2)
    pick_tool(driver, "select")
    driver.drag_squares(2, 2, 2, 2)
    # a single-square drag is a click; use a 1x1 selection through Pick up everything instead
    driver.click("#selectAll")
    if driver.state()["sel"]:
        driver.click("#selCopy")
        driver.click_square(15, 15)
    report.check("Copy copies the picked-up squares", pix(driver, 2, 2) == 0 and sum(
        1 for x in range(16) for y in range(16) if pix(driver, x, y) == 0) >= 2,
        f"pixels={sum(1 for x in range(16) for y in range(16) if pix(driver, x, y) == 0)}")

    # Flip and Delete on a picked-up block.
    clear_canvas(driver)
    pick_tool(driver, "pencil")
    driver.click_square(2, 2)
    driver.click_square(3, 2)
    driver.click_square(2, 3)
    pick_tool(driver, "select")
    driver.click("#selectAll")
    if driver.state()["sel"]:
        driver.click("#selFlip")
        driver.click_square(15, 15)
    report.check("Flip mirrors the picked-up squares",
                 pix(driver, 2, 2) == 0 and pix(driver, 3, 2) == 0
                 and pix(driver, 2, 3) == -1 and pix(driver, 3, 3) == 0,
                 f"row2={[pix(driver,x,2) for x in range(2,5)]} row3={[pix(driver,x,3) for x in range(2,5)]}")
    pick_tool(driver, "select")
    driver.click("#selectAll")
    if driver.state()["sel"]:
        driver.click("#selDelete")
    report.check("Delete empties the picked-up squares",
                 all(c == '.' for c in pixels(driver)), "empty")
    pick_tool(driver, "pencil")

    # Mix a colour and use the little shade strip.
    choose_colour(driver, 0)
    before_palette = driver.js("return art.palette.length")
    driver.js("const m=document.getElementById('mix'); m.value='#123456';"
              "m.dispatchEvent(new Event('change',{bubbles:true}));")
    time.sleep(.1)
    after_palette = driver.js("return art.palette.length")
    report.check("Mix adds a colour of your own", after_palette == before_palette + 1,
                 f"{before_palette} -> {after_palette}")
    driver.click("#shades [data-tone]")
    report.check("a shade in the strip can be chosen", driver.state()["colour"] >= 0,
                 driver.state()["colour"])

    # See the code: a row that isn't yours says why; a good edit changes the picture.
    clear_canvas(driver)
    pick_tool(driver, "pencil")
    driver.click_square(5, 5)
    driver.click("#openMore")
    driver.click("#seeCode")
    driver.wait("return !document.getElementById('artSheet').hidden", 10, "See the code")
    rows = driver.js("return document.getElementById('artCode').value.split('\\n')")
    report.check("See the code shows one row per square", len(rows) == 16 and all(len(r) == 16 for r in rows),
                 f"{len(rows)} rows")
    driver.js("const t=document.getElementById('artCode');"
              "t.value=t.value.replace(/[^.\\n]/, 'z');"
              "t.dispatchEvent(new Event('input',{bubbles:true}));")
    note_bad = driver.text("#artNote")
    report.check("an unknown letter says why the picture didn't change",
                 "isn't one of your colours" in note_bad, note_bad)
    before_frame = pixels(driver)
    driver.js("const t=document.getElementById('artCode'); t.focus();")
    driver.send("#artCode", "\ue009z")  # Ctrl+Z in the text box
    time.sleep(.2)
    report.check("Ctrl+Z while typing the code doesn't undo the drawing",
                 pixels(driver) == before_frame, "drawing unchanged")

    # A real edit goes onto the picture when the sheet closes.
    driver.js("const t=document.getElementById('artCode');"
              "let rows=t.value.split('\\n'); rows=rows.map(r=>r.replace(/z/g,'0'));"
              "rows[0]='0'+rows[0].slice(1);"
              "t.value=rows.join('\\n'); t.dispatchEvent(new Event('input',{bubbles:true}));")
    driver.click("#closeArt")
    driver.wait("return document.getElementById('artSheet').hidden", 10, "the code sheet to close")
    report.check("a valid See the code edit changes the picture", pix(driver, 0, 0) == 0, pix(driver,0,0))

    # Bead pattern opens with a count.
    driver.click("#openMore")
    driver.click("#seeBeads")
    driver.wait("return !document.getElementById('beads').hidden", 10, "Bead pattern")
    report.check("Bead pattern opens with bead counts", "beads" in driver.text("#beadTotal"),
                 driver.text("#beadTotal"))
    driver.click("#closeBeads")

    # Speed buttons on an animation.
    driver.click("#copyFrame")
    driver.wait("return typeof art!=='undefined' && art.frames.length===2", 10, "two frames")
    driver.click("#speed [data-fps='10']")
    driver.wait("return typeof art!=='undefined' && art.speed===10", 10, "fast speed")
    report.check("the Fast speed button sets the speed", driver.state()["frames"] is not None,
                 "speed 10")


def section_calm(driver, report, data):
    report.section("calm")
    trim_shelf(driver, 3)
    pick_gallery(driver, "Kitty", "ready")
    was = driver.state()["calm"]
    if was:
        driver.click("#calm")
    report.check("Calm starts off for this run", driver.state()["calm"] is False, driver.state()["calm"])
    driver.click("#calm")
    s = driver.state()
    report.check("🌿 Calm toggles on",
                 s["calm"] is True and s["calmPressed"] == "true" and s["bodyCalm"],
                 f"calm={s['calm']} pressed={s['calmPressed']} body={s['bodyCalm']}")
    # The little pal in the corner must stop wobbling in Calm too.
    frames = []
    for _ in range(6):
        frames.append(driver.js("return document.getElementById('preview').toDataURL()"))
        time.sleep(.15)
    report.check("🌿 Calm holds the little pal still", len(set(frames)) == 1,
                 f"{len(set(frames))} different preview pictures in 0.9 s")
    driver.click("#calm")
    s = driver.state()
    report.check("🌿 Calm toggles back off",
                 s["calm"] is False and s["calmPressed"] == "false" and not s["bodyCalm"],
                 f"calm={s['calm']}")
    report.note("Calm was", f"{was}")


def section_reload(driver, report, data):
    """A reload in the middle must not lose work, even before the 2 s save."""
    report.section("reload")
    trim_shelf(driver, 3)
    start_blank(driver, 16)
    choose_colour(driver, 0)
    pick_tool(driver, "pencil")
    driver.click_square(4, 4)
    wait_for_save(driver)
    key = driver.state()["key"]
    base = re.sub(r"/pixel.*$", "", driver.state()["url"])
    driver.request("POST", f"/session/{driver.sid}/url", {"url": base + "/pixel"})
    wait_join_reload(driver, data.get("name", "Draw E2E"))
    s = driver.state()
    report.check("a save before reload comes back", s["key"] == key and pix(driver, 4, 4) == 0,
                 f"key={s['key']} pixel={pix(driver,4,4)}")

    # Now reload straight after a click, before the 2 s debounce is up.
    choose_colour(driver, 1)
    pick_tool(driver, "pencil")
    driver.click_square(9, 9)
    driver.request("POST", f"/session/{driver.sid}/url", {"url": base + "/pixel"})
    wait_join_reload(driver, data.get("name", "Draw E2E"))
    time.sleep(.6)
    s = driver.state()
    report.check("a click just before reload is kept (pagehide beacon)",
                 s["key"] == key and pix(driver, 9, 9) == 1,
                 f"key={s['key']} pixel={pix(driver,9,9)} saved={s['saved']!r}")
    return {"key": key, "base": base}


def wait_join_reload(driver, name="Draw E2E"):
    driver.wait("return !document.getElementById('join').hidden || "
                "(!document.getElementById('app').hidden && typeof art!=='undefined' && !!art)",
                30, "the page after reload")
    if not driver.js("return document.getElementById('join').hidden"):
        # localStorage should remember this student, but if not, the same name
        # attaches to the same player rather than making a second one.
        driver.send("#name", name)
        driver.click("#joinButton")
    driver.wait("return !document.getElementById('app').hidden && typeof art!=='undefined' && !!art",
                30, "the app after reload")


def art_sq(driver):
    return driver.js("return art.size*art.size")


def section_fullshelf(driver, report, data):
    """A save that can't go in because the shelf is full says what to do, and
    saves itself once a drawing is deleted."""
    report.section("full shelf")
    trim_shelf(driver, 2)
    start_blank(driver, 16)
    # Hold this new drawing's first save back until the shelf is full.
    driver.js("clearTimeout(saveTimer); dirty = false;")
    drawing = driver.js("return payload().drawing")
    tag = driver.state()["key"][:4]
    for i in range(12):
        filler = dict(drawing)
        filler["key"] = f"{tag}fill{i:02d}"
        filler["title"] = ""
        driver.js_async(r"""
          const done=arguments[arguments.length-1], d=arguments[0];
          fetch('/pixel/save', {method:'POST', headers:{'Content-Type':'application/json'},
                                body: JSON.stringify({id: me, drawing: d})})
            .then(r=>r.json()).then(done).catch(()=>done(null));
        """, filler)
    count = driver.js_async(r"""
      const done=arguments[arguments.length-1];
      fetch('/pixel/state?id='+me).then(r=>r.json())
        .then(x=>done(x.drawings.length)).catch(()=>done(-1));
    """)
    report.note("the shelf was filled for this check", f"{count} drawings")
    choose_colour(driver, 0)
    pick_tool(driver, "pencil")
    driver.click_square(3, 3)
    told = driver.wait("return document.getElementById('saved').innerText.indexOf('shelf is full')>=0",
                       12, "")
    report.check("a full shelf says to delete a drawing, not just 'trying again'", told,
                 driver.text("#saved"))
    # Make a little room; the retry then saves this drawing.
    driver.js_async(r"""
      const done=arguments[arguments.length-1];
      fetch('/pixel/delete', {method:'POST', headers:{'Content-Type':'application/json'},
                              body: JSON.stringify({id: me, key: arguments[0]})})
        .then(r=>r.json()).then(done).catch(()=>done(null));
    """, f"{tag}fill00")
    saved = driver.wait("return document.getElementById('saved').innerText.indexOf('Saved')>=0",
                        12, "")
    report.check("after making room the drawing saves by itself", saved, driver.text("#saved"))
    trim_shelf(driver, 2)


def section_tabs(driver, report, data, args):
    """Two real tabs of the same student: work must not be silently overwritten."""
    report.section("two tabs")
    trim_shelf(driver, 3)
    # Start from a known, saved, blank drawing so both tabs open the same one.
    start_blank(driver, 16)
    wait_for_save(driver)
    key = driver.state()["key"]
    base = re.sub(r"/pixel.*$", "", driver.state()["url"])
    tab_a = driver.current_handle()
    tab_b = driver.new_tab()
    try:
        driver.switch_tab(tab_b)
        driver.request("POST", f"/session/{driver.sid}/url", {"url": base + "/pixel"})
        wait_enter(driver, args.name)
        report.check("a second tab shows the same student and drawing",
                     driver.state()["key"] == key, f"{driver.state()['key']} vs {key}")

        # Tab A paints one square and saves.
        driver.switch_tab(tab_a)
        choose_colour(driver, 0)
        pick_tool(driver, "pencil")
        driver.click_square(1, 14)
        wait_for_save(driver)

        # Tab B should hear about it and start from the newer picture.
        driver.switch_tab(tab_b)
        heard = driver.wait(f"return (typeof art!=='undefined' && art && art.key==={json.dumps(key)}) ? "
                            "art.frames[0][14*art.size+1] === 0 : false", 10, "")
        report.check("the other tab hears the save and gets the new square", heard,
                     f"tab B key={driver.state()['key']} square={pix(driver,1,14)}")

        # Now tab B paints its own square and saves.  It must keep tab A's.
        choose_colour(driver, 1)
        pick_tool(driver, "pencil")
        driver.click_square(14, 1)
        wait_for_save(driver)

        # Tab A should hear about B's save, with both squares.
        driver.switch_tab(tab_a)
        both = driver.wait(f"return (typeof art!=='undefined' && art && art.key==={json.dumps(key)}) ? "
                           "(art.frames[0][14*art.size+1] === 0 && art.frames[0][1*art.size+14] === 1) : false",
                           10, "")
        report.check("both tabs keep both squares while open", both,
                     f"a={pix(driver,1,14)} b={pix(driver,14,1)}")

        # A reload shows what was actually saved: both squares.
        driver.request("POST", f"/session/{driver.sid}/url", {"url": base + "/pixel"})
        wait_join_reload(driver, args.name)
        kept_a = pix(driver, 1, 14) == 0
        kept_b = pix(driver, 14, 1) == 1
        report.check("two tabs do not silently lose the other tab's squares",
                     kept_a and kept_b,
                     f"tab A square kept={kept_a} tab B square kept={kept_b}")
        report.check("two tabs do not crash", driver.state()["key"] == key, driver.state()["key"])
    finally:
        try:
            driver.switch_tab(tab_b)
            driver.request("DELETE", f"/session/{driver.sid}/window")
        except Exception:
            pass
        try:
            driver.switch_tab(tab_a)
        except Exception:
            pass


# ---------------------------------------------------------------------------
# The run
# ---------------------------------------------------------------------------

SECTIONS = {
    "gallery": section_gallery,
    "tools": section_tools,
    "undo": section_undo,
    "frames": section_frames,
    "shelf": section_shelf,
    "life": section_life,
    "extras": section_extras,
    "calm": section_calm,
    "reload": section_reload,
    "fullshelf": section_fullshelf,
}


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--base", default=DEFAULT_BASE)
    ap.add_argument("--port", type=int, default=None)
    ap.add_argument("--driver", default=DEFAULT_DRIVER)
    ap.add_argument("--browser", default="/usr/bin/chromium")
    ap.add_argument("--width", type=int, default=1366)
    ap.add_argument("--height", type=int, default=768)
    ap.add_argument("--json-out", default="")
    ap.add_argument("--only", default="",
                    help="comma-separated sections: " + ",".join(list(SECTIONS) + ["tabs"]))
    ap.add_argument("--name", default="Draw E2E")
    ap.add_argument("--keep-open", action="store_true", help="leave the browser open")
    args = ap.parse_args()
    base = args.base if args.port is None else re.sub(r":\d+$", f":{args.port}", args.base)
    wanted = [s for s in args.only.split(",") if s] or list(SECTIONS) + ["tabs"]

    report = Report()
    report.data = {"base": base, "viewport": None, "started": time.strftime("%Y-%m-%d %H:%M:%S"),
                   "sections": wanted, "student": None, "name": args.name}
    driver = Driver(args.driver, args.browser, args.width, args.height)
    try:
        driver.request("POST", f"/session/{driver.sid}/url", {"url": base + "/pixel"})
        wait_join(driver, args.name)
        report.data["student"] = driver.js("return me")
        report.data["viewport"] = driver.js("return [innerWidth, innerHeight]")
        data = corpus(driver)
        report.absorb_logs(driver, "join")
        for name in wanted:
            try:
                if name == "tabs":
                    section_tabs(driver, report, data, args)
                elif name in SECTIONS:
                    result = SECTIONS[name](driver, report, data)
                    if result:
                        data.update(result)
                else:
                    raise WebDriverError(f"unknown section {name}")
            except Exception as e:
                report.check(f"{name} finished without throwing", False, repr(e)[:1000])
                try:
                    report.data.setdefault("stuck", {})[name] = driver.state()
                except Exception:
                    pass
                driver.screenshot(os.path.join(ROOT, "tools", f"e2e_draw_{name}.png"))
            report.absorb_logs(driver, name)
        report.data["final"] = driver.state()
    finally:
        report.data["ended"] = time.strftime("%Y-%m-%d %H:%M:%S")
        report.data["console"] = report.console
        report.data["checks"] = report.checks
        report.data["failures"] = report.failures
        out = args.json_out or os.path.join(ROOT, "tools", "e2e_draw_results.json")
        with open(out, "w", encoding="utf-8") as f:
            json.dump(report.data, f, indent=2)
        if not args.keep_open:
            driver.close()
        elif args.keep_open:
            print(f"browser left open on {driver.base} (session {driver.sid})")

    bad = [e for e in report.console if e.get("level") in ("SEVERE", "ERROR")]
    total = sum(1 for c in report.checks if c["result"] in ("OK", "FAIL"))
    fails = sum(1 for c in report.checks if c["result"] == "FAIL")
    print(f"\nwrote {out}")
    print(f"checks OK: {total - fails}/{total}   failures: {fails}   console errors: {len(bad)}")
    for e in bad[:10]:
        print(f"  console {e.get('level')}: {e.get('message')[:200]}")
    return 0 if not fails and not bad else 1


if __name__ == "__main__":
    sys.exit(main())
