#!/usr/bin/env python3
"""End-to-end check of Pixel Pals' guided typing ("coach"), in a real browser.

It starts headless Chromium through chromedriver and talks to chromedriver's
WebDriver wire protocol with the standard library, so there is nothing to pip
install.  It makes one student, finishes mission m1 (My Move, a build mission)
through POST /pixel/run with its reference code so the later missions open, and
then for every other mission in pixel.LEVEL_ORDER it:

  * opens the mission from the Missions sheet,
  * types the coach lines with real key events, one character at a time, and
    checks the editor after every key (leading spaces are never typed: the
    guide pushes them in, and lines that move back out must lose them),
  * answers Guess first (one mission on purpose with a wrong guess),
  * presses Show time! and waits for the show, and
  * checks the result is three stars.

It also tries the guide's mistakes and the boxes around it: a wrong key,
Backspace (including an auto-indented line), a capital letter, pressing Show
time! early, "I can type it myself" then a mistake, "Go back to where it was
right", "Keep my code", Guess first, the win popup, Your turn and Fix it.

Usage (the server must already be running on the port given, with a fresh
state file; see the report):

    python3 tools/e2e_coach.py --port 8126 --json-out /tmp/coach.json

This is a tool, not a unittest: it is not named test_*.py and unittest will not
pick it up.  It needs chromium and chromedriver on PATH.
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
import pixel  # noqa: E402  (the mission data the page is served from)

ENTER = "\ue007"
BACKSPACE = "\ue003"

DEFAULT_BASE = "http://127.0.0.1:8126"
DEFAULT_DRIVER = "chromedriver"


# ---------------------------------------------------------------------------
# A very small WebDriver client: enough for clicks, keys, script and logs.
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
        # Headless Chromium leaves room for a window frame in window.rect, so
        # ask for the exact 1366x768 page the class's laptops have.
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

    def state(self):
        return self.js(r"""
        return (() => {
          const q = s => document.querySelector(s);
          const hidden = s => { const el = q(s); return !el || el.hidden; };
          return {
            url: location.href,
            inner: [innerWidth, innerHeight],
            code: q('#code') ? q('#code').value : '',
            coach: q('#coach') ? (q('#coach').innerText || '') : '',
            coachHidden: q('#coach') ? q('#coach').hidden : null,
            coaching: document.body.classList.contains('coaching'),
            coachBack: q('#coachBack') ? !q('#coachBack').hidden : null,
            coachOops: q('.coach-oops') ? q('.coach-oops').innerText : '',
            job: q('#job') ? (q('#job').innerText || '') : '',
            verdict: q('#verdict') ? (q('#verdict').innerText || '') : '',
            caption: q('#caption') ? (q('#caption').innerText || '') : '',
            levelName: q('#levelName') ? (q('#levelName').innerText || '') : '',
            best: (typeof view !== 'undefined' && view) ? view.best : null,
            remixDone: (typeof view !== 'undefined' && view && view.remix) ? view.remix.done : null,
            fixDone: (typeof view !== 'undefined' && view && view.fix) ? view.fix.done : null,
            goals: [...document.querySelectorAll('#goals li')].map(li => li.classList.contains('got')),
            win: !hidden('#win'),
            winTitle: q('#winTitle') ? (q('#winTitle').innerText || '') : '',
            winStars: document.querySelectorAll('#winStars .on').length,
            winDo: q('#winDo') ? (q('#winDo').innerText || '') : '',
            gift: !!q('#giftOpen'),
            giftLater: !!q('#giftLater'),
            giftOpen: !!q('.gift-open'),
            giftName: q('.gift-open b') ? q('.gift-open b').innerText : '',
            yourTurn: hidden('#yourTurn') ? '' : (q('#yourTurn').innerText || ''),
            running: typeof running !== 'undefined' ? running : null,
            guessButtons: [...document.querySelectorAll('[data-guess]')].map(
              b => ({text: b.innerText, idx: b.dataset.guess})),
            stars: (typeof S !== 'undefined' && S) ? S.stars : null,
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
# Page helpers
# ---------------------------------------------------------------------------

def wait_join(driver, name="Coach E2E"):
    driver.wait("return !document.getElementById('join').hidden", 30, "the join screen")
    driver.send("#name", name)
    driver.click("#joinButton")
    driver.wait("return !document.getElementById('app').hidden", 30, "the app")
    # A brand new student gets the gallery, because there is nothing on their
    # shelf yet.  Pick a ready pal, as a student would.  A returning student
    # (same name) already has one, so there is no gallery to close.
    time.sleep(.3)
    if not driver.js("return document.getElementById('shelf').hidden"):
        driver.click("#gallery [data-gallery]")
        driver.wait("return document.getElementById('shelf').hidden", 20, "the gallery to close")


def open_code(driver):
    driver.click("nav [data-view=stage]")
    driver.wait("return !document.getElementById('stageView').hidden && !!document.getElementById('levelName').innerText",
                30, "the Code tab and a mission")


def wait_mission_ready(driver, key):
    driver.wait("return typeof mode !== 'undefined' && mode === %s && "
                "typeof view !== 'undefined' && !!view && "
                "!document.getElementById('coach').hidden" % json.dumps(key),
                30, f"mission {key} to open")
    driver.wait("return ((document.getElementById('coach') || {}).innerText || '').trim().length > 0",
                20, f"mission {key}'s guide")


def open_mission(driver, key):
    driver.click("#openMissions")
    driver.wait("return !document.getElementById('missions').hidden", 20, "the Missions sheet")
    selector = f"#missionList [data-mission='{key}']"
    if not driver.exists(selector):
        raise WebDriverError(f"no mission button for {key}")
    if driver.js("return document.querySelector(arguments[0]).disabled", selector):
        raise WebDriverError(f"mission {key} is still locked")
    driver.click(selector)
    wait_mission_ready(driver, key)


def focus_code(driver):
    driver.js("const t=document.getElementById('code'); if (t) { t.focus();"
              "t.setSelectionRange(t.value.length, t.value.length); }")


def code_value(driver):
    return driver.js("return document.getElementById('code').value")


def key_name(ch):
    return "Enter" if ch == "\n" else "space bar" if ch == " " else ch


def expected_after(target, at):
    """What the editor must hold after the key at target[at-1].

    After Enter the guide already pushes in the next line's leading spaces, so
    a kid never types those.  That is also how a line moves back out: the next
    line's indent is smaller, or zero.
    """
    want = target[:at]
    if at > 0 and target[at - 1] == "\n":
        end = at
        while end < len(target) and target[end] == " ":
            end += 1
        want += target[at:end]
    return want


def type_coach(driver, target, stop_at=None):
    """Type target from the current (prefix) editor value, one real key at a time.

    Returns a dict.  The editor value is compared with the target after every
    key, so a key the guide refused, or an indent it got wrong, is caught at
    that exact key.
    """
    got = code_value(driver)
    if not target.startswith(got):
        return {"ok": False, "where": "before typing",
                "detail": "the editor did not hold a prefix of the steps",
                "expected": target, "got": got, "state": driver.state()}
    focus_code(driver)
    i = len(got)
    started = time.time()
    while i < len(target):
        if stop_at is not None and i >= stop_at:
            break
        # Leading spaces are the guide's job, including a line that moves out.
        if target[i] == " " and (i == 0 or target[i - 1] == "\n"):
            end = i
            while end < len(target) and target[end] == " ":
                end += 1
            want = target[:end]
            have = code_value(driver)
            if have != want:
                return {"ok": False, "where": f"auto-indent before column {i}",
                        "detail": "the guide did not push the line in as the steps show",
                        "expected": want, "got": have, "state": driver.state()}
            i = end
            continue
        ch = target[i]
        driver.send("#code", ENTER if ch == "\n" else ch)
        i += 1
        want = expected_after(target, i)
        have = code_value(driver)
        if have != want:
            line = target[:i].count("\n") + 1
            return {"ok": False, "where": f"line {line}, key {key_name(ch)!r}",
                    "detail": "the editor did not match the steps after this key",
                    "expected": want, "got": have,
                    "key": key_name(ch), "state": driver.state()}
    return {"ok": True, "chars": len(target) - len(got),
            "seconds": round(time.time() - started, 2),
            "code": code_value(driver)}


def run_show(driver, guess_choice="right", timeout=90):
    """Press Show time!, answer Guess first if it appears, wait for the show."""
    before = driver.state()
    driver.click("#runButton")
    guess = None
    end = time.time() + 6
    while time.time() < end:
        s = driver.state()
        if s["guessButtons"]:
            view_guess = driver.js("return view && view.guess ? "
                                   "{ask: view.guess.ask, choices: view.guess.choices} : null")
            if not view_guess:
                raise WebDriverError("a guess appeared but view.guess is empty")
            mode = driver.js("return mode")
            known = pixel.GUESSES.get(mode)
            right = known[2] if known and known[0] == view_guess["ask"] else 0
            picked = (right + 1) % len(view_guess["choices"]) if guess_choice == "wrong" else right
            guess = {"ask": view_guess["ask"], "choices": view_guess["choices"],
                     "picked": view_guess["choices"][picked], "right": view_guess["choices"][right],
                     "wanted": guess_choice}
            driver.click(f"[data-guess='{picked}']")
            break
        if s["running"]:
            break
        time.sleep(.05)
    started = time.time()
    ok = driver.wait("return !running", timeout, "")
    time.sleep(.35)
    s = driver.state()
    s["show_seconds"] = round(time.time() - started, 2)
    s["show_timed_out"] = not ok
    s["guess"] = guess
    s["before"] = before
    return s


def close_win(driver):
    if driver.exists("#winClose"):
        driver.click("#winClose")
        driver.wait("return document.getElementById('win').hidden", 10, "the win popup to close")


def handle_win(driver, result, open_gift=False, allow_next=True):
    """Record the win popup, open the gift (once) or choose Open it later.

    allow_next clicks the popup's Next mission button when it has one; the
    caller then skips its own open_mission for that key.
    """
    s = result
    info = {"shown": bool(s["win"]), "title": s["winTitle"], "stars": s["winStars"],
            "buttons": s["winDo"], "gift": None, "opened": None}
    if not s["win"]:
        return info
    if s["gift"] and open_gift:
        driver.click("#giftOpen")
        driver.wait("return !!document.querySelector('.gift-open')", 10, "the gift to open")
        info["gift"] = driver.state()["giftName"]
        driver.wait("return !!document.querySelector('#winDo button')", 10, "the win buttons")
    elif s["giftLater"]:
        driver.click("#giftLater")
        driver.wait("return !!document.querySelector('#winDo button')", 10, "the win buttons")
    info["buttons"] = driver.state()["winDo"]
    next_selector = "#winDo [data-mission]"
    if allow_next and driver.exists(next_selector):
        info["opened"] = driver.js("return document.querySelector('#winDo [data-mission]').dataset.mission")
        driver.click(next_selector)
    else:
        close_win(driver)
    return info


def mode_target(driver):
    return driver.js("return view.coach.map(c => c[0]).join('\\n')")


# ---------------------------------------------------------------------------
# Mistakes and the boxes around the guide
# ---------------------------------------------------------------------------

def record(report, name, mission, ok, screen, detail=""):
    report["mistakes"].append({"name": name, "mission": mission,
                               "result": "OK" if ok else "FAIL",
                               "screen": screen, "detail": detail})
    return ok


def probe_a1(driver, report):
    """Show time! early, a wrong key, a capital letter, Backspace."""
    s = driver.state()
    # Show time! early: the editor is empty, and nothing may run.
    driver.click("#runButton")
    time.sleep(.3)
    s = driver.state()
    ok = ("Not yet! Finish typing first" in s["coach"] and s["running"] is False
          and s["code"] == "")
    record(report, "Show time! pressed early", "a1", ok, s["coach"].strip(),
           "nothing ran; editor still empty")

    # Leaving the guide and coming back must not keep the old "Not yet!".
    driver.click("#coach [data-coach='own']")
    driver.click("#coachBack")
    driver.wait("return document.body.classList.contains('coaching')", 10, "the guide back")
    s = driver.state()
    ok = "Not yet! Finish typing first" not in s["coach"]
    record(report, "the early warning is not left behind", "a1", ok,
           s["coach"].strip()[:400], "after Show me step by step the old warning is gone")

    # A wrong key: the guide refuses it and says which key to find.
    focus_code(driver)
    driver.send("#code", "z")
    s = driver.state()
    ok = (s["code"] == "" and "Not that key" in s["coach"] and "s key" in s["coach"])
    record(report, "a wrong key", "a1", ok, s["coach"].strip(),
           "typed z where the steps want s; the editor was not changed")

    # A capital letter is accepted and typed as the guide's small letter.
    driver.send("#code", "S")
    s = driver.state()
    ok = s["code"] == "s"
    record(report, "a capital letter", "a1", ok, s["coach"].strip(),
           f"typed Shift+S where the steps want s; editor is {s['code']!r}")

    # Backspace clears that key again.
    driver.send("#code", BACKSPACE)
    s = driver.state()
    ok = s["code"] == ""
    record(report, "Backspace", "a1", ok, s["coach"].strip(),
           f"after Backspace the editor is {s['code']!r}")


def probe_b1(driver, report):
    """Enter pushes the loop body in; Backspace takes the push and the newline away."""
    target = mode_target(driver)
    first = "for i in range(5):"
    step = type_coach(driver, target, stop_at=len(first))
    if not step["ok"]:
        record(report, "typing the for line", "b1", False, step.get("state", {}).get("coach", ""),
               json.dumps(step)[:1000])
        return step
    driver.send("#code", ENTER)
    s = driver.state()
    pushed = s["code"] == first + "\n    "
    record(report, "Enter pushes the loop body in", "b1", pushed, s["coach"].strip(),
           f"editor after Enter is {s['code']!r}")
    # A wrong key inside the pushed-in line is refused too.
    driver.send("#code", "x")
    s = driver.state()
    ok = s["code"] == first + "\n    " and "j key" in s["coach"]
    record(report, "a wrong key inside the loop body", "b1", ok, s["coach"].strip(),
           f"editor is still {s['code']!r}")
    driver.send("#code", BACKSPACE)
    s = driver.state()
    back = s["code"] == first
    record(report, "Backspace on a pushed-in line", "b1", back, s["coach"].strip(),
           f"after Backspace the editor is {s['code']!r} (newline and 4 spaces gone)")
    # Put the Enter back so the main typing continues from the right place.
    driver.send("#code", ENTER)
    s = driver.state()
    if s["code"] != first + "\n    ":
        return {"ok": False, "where": "restoring the auto-indent",
                "detail": "Enter did not push the loop body in again",
                "expected": first + "\n    ", "got": s["code"], "state": s}

    # "I can type it myself" with the indentation taken out, then Show me step
    # by step and Go back.  Going back must push the loop body in again, just
    # like Enter does, so the next key is j and not the space bar.
    driver.click("#coach [data-coach='own']")
    driver.send("#code", BACKSPACE)      # the editor takes the 4 pushed-in spaces at once
    s = driver.state()
    if s["code"] != first + "\n":
        return {"ok": False, "where": "taking the auto-indent out by hand",
                "detail": "Backspace did not leave the loop body at the left edge",
                "expected": first + "\n", "got": s["code"], "state": s}
    driver.send("#code", "jump()")
    driver.click("#coachBack")
    driver.wait("return document.body.classList.contains('coaching')", 10, "the guide back")
    s = driver.state()
    mismatch = "Your code is different from the steps." in s["coach"]
    record(report, "Show me step by step after removing the indent", "b1", mismatch,
           s["coach"].strip()[:400], "the mismatch card appears")
    driver.click("#coach [data-coach='back']")
    s = driver.state()
    pushed_back = s["code"] == first + "\n    "
    record(report, "↩ Go back pushes the loop body in again", "b1", pushed_back,
           s["coach"].strip()[:400],
           f"after Go back the editor is {s['code']!r}; the next key should be j")
    if not pushed_back:
        return {"ok": False, "where": "↩ Go back after removing the auto-indent",
                "detail": "Go back left the line at the left edge instead of pushing it in",
                "expected": first + "\n    ", "got": s["code"], "state": s}
    return step


def probe_c2(driver, report):
    """I can type it myself, a real mistake, Show me step by step, Keep my code, Go back."""
    target = mode_target(driver)
    first = "n = 5"
    step = type_coach(driver, target, stop_at=len(first))
    if not step["ok"]:
        return step
    driver.send("#code", ENTER)
    if code_value(driver) != first + "\n":
        return {"ok": False, "where": "Enter after the first line", "state": driver.state()}

    driver.click("#coach [data-coach='own']")
    s = driver.state()
    ok = (not s["coaching"] and s["coachHidden"] is True and driver.js(
        "return getComputedStyle(document.getElementById('pipSays')).display !== 'none'"))
    record(report, "✋ I can type it myself", "c2", ok, s["verdict"].strip(),
           "guide hidden, story and Help me back")

    focus_code(driver)
    driver.send("#code", "if n = 5:")
    driver.send("#code", ENTER)          # the editor pushes the body in
    driver.send("#code", "n = 4")
    s = run_show(driver)
    ok = bool(s["verdict"].strip()) and s["best"] == [False, False, False]
    record(report, "typing a mistake after I can type it myself", "c2", ok,
           s["verdict"].strip()[:500], "Show time! gave a real message, not a crash")

    driver.click("#coachBack")
    driver.wait("return document.body.classList.contains('coaching')", 10, "the guide back")
    s = driver.state()
    mismatch = "Your code is different from the steps." in s["coach"]
    record(report, "Show me step by step notices the code differs", "c2", mismatch,
           s["coach"].strip()[:500], "the card offers Go back and Keep my code")

    before_keep = s["code"]
    driver.click("#coach [data-coach='own']")
    s = driver.state()
    ok = (not s["coaching"] and s["code"] == before_keep)
    record(report, "✋ Keep my code", "c2", ok, s["verdict"].strip(),
           f"guide hidden; the editor still holds {s['code']!r}")

    driver.click("#coachBack")
    driver.wait("return document.body.classList.contains('coaching')", 10, "the guide back again")
    driver.click("#coach [data-coach='back']")
    s = driver.state()
    ok = s["code"] == first + "\n" and "Next key" in s["coach"]
    record(report, "↩ Go back to where it was right", "c2", ok, s["coach"].strip()[:500],
           f"editor went back to {s['code']!r}; the guide asks for the next key")
    return {"ok": True}


def do_your_turn_and_fix(driver, report):
    """Your turn and Fix it on a2, after its first win."""
    s = driver.state()
    ok = "Your turn" in s["yourTurn"] and "Try it!" in s["yourTurn"]
    record(report, "🎨 Your turn card", "a2", ok, s["yourTurn"][:500])

    driver.click("#yourTurn [data-remix='1']")
    driver.wait("return typeof remixOn !== 'undefined' && remixOn", 10, "Your turn mode")
    s = driver.state()
    ok = (not s["coaching"] and "No guide this time" in s["yourTurn"])
    record(report, "Your turn turns the guide off", "a2", ok, s["yourTurn"][:500],
           "the editor keeps the code")

    # Show it before the change: the show works, but Your turn still wants something.
    s = run_show(driver)
    ok = "Your turn wants" in s["verdict"] and "The show works" in s["verdict"]
    record(report, "Show time! before the Your turn change", "a2", ok,
           s["verdict"].strip()[:500], "it says what Your turn still wants")

    # Add the extra jump the card asks for.
    focus_code(driver)
    driver.send("#code", ENTER)
    driver.send("#code", "jump()")
    s = run_show(driver)
    ok = "Your turn: done!" in s["verdict"] and s["remixDone"] is True
    record(report, "doing Your turn", "a2", ok, s["verdict"].strip()[:500],
           "the show works and the change is there")
    s = driver.state()
    ok = "Fix it" in s["yourTurn"]
    record(report, "🐞 Fix it card after Your turn", "a2", ok, s["yourTurn"][:500])

    driver.click("#yourTurn [data-fix='1']")
    driver.wait("return typeof fixOn !== 'undefined' && fixOn", 10, "Fix it mode")
    s = driver.state()
    buggy = s["code"]
    ok = (not s["coaching"] and "Fix it" in s["yourTurn"])
    record(report, "Fix Pip's code loads Pip's code", "a2", ok, s["yourTurn"][:500],
           f"the editor holds {buggy!r}")
    driver.click("#yourTurn [data-fix-hint='1']")
    s = driver.state()
    ok = "💡" in s["yourTurn"] and bool(s["yourTurn"].strip())
    record(report, "💡 Where's the bug?", "a2", ok, s["yourTurn"][:500])

    # Edit, then use Pip's code again to put the bug back.
    focus_code(driver)
    driver.send("#code", " ")
    changed = code_value(driver)
    driver.click("#yourTurn [data-fix-reset='1']")
    s = driver.state()
    ok = s["code"] == buggy and changed != buggy
    record(report, "↩ Pip's code again", "a2", ok, s["yourTurn"][:500],
           "the editor goes back to Pip's buggy code")

    s = run_show(driver)
    ok = bool(s["verdict"].strip()) and "Bug fixed" not in s["verdict"]
    record(report, "Show time! with Pip's bug", "a2", ok, s["verdict"].strip()[:500],
           "the show either stops with a message or says the bug is still there")

    # The fixed code is the mission's guide code.
    driver.js("setCode(view.coach.map(c => c[0]).join('\\n'))")
    s = run_show(driver)
    ok = "Bug fixed" in s["verdict"] and s["fixDone"] is True
    record(report, "fixing Pip's bug", "a2", ok, s["verdict"].strip()[:500])


# ---------------------------------------------------------------------------
# The run
# ---------------------------------------------------------------------------

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
    ap.add_argument("--only", default="", help="comma-separated mission keys, to re-check a few that are already open")
    ap.add_argument("--limit", type=int, default=0, help="stop after this many missions (development)")
    ap.add_argument("--name", default="Coach E2E", help="the one student this run makes")
    ap.add_argument("--skip-extras", action="store_true", help="no mistake/Your turn/Fix it probes")
    args = ap.parse_args()
    base = args.base if args.port is None else re.sub(r":\d+$", f":{args.port}", args.base)

    report = {"base": base, "missions": [], "mistakes": [], "console": [],
              "student": None, "viewport": None, "finished_all": False,
              "started": time.strftime("%Y-%m-%d %H:%M:%S")}
    driver = Driver(args.driver, args.browser, args.width, args.height,
                    verbose=bool(args.only))
    try:
        driver.request("POST", f"/session/{driver.sid}/url", {"url": base + "/pixel"})
        wait_join(driver, args.name)
        report["student"] = driver.js("return me")
        report["viewport"] = driver.js("return [innerWidth, innerHeight]")
        open_code(driver)
        report["console"].extend(driver.logs())

        me = report["student"]
        only = [k for k in args.only.split(",") if k]
        keys = only or pixel.LEVEL_ORDER
        if args.limit:
            keys = keys[:args.limit]
        preopened = None
        # In a full run, finish m1 through the API when we reach it.
        for pos, key in enumerate(keys):
            lv = pixel.LEVEL_BY_KEY[key]
            at = pixel.LEVEL_ORDER.index(key)
            next_key = pixel.LEVEL_ORDER[at + 1] if at + 1 < len(pixel.LEVEL_ORDER) else None
            entry = {"key": key, "name": lv["name"], "result": "STUCK", "stars": None,
                     "console": [], "notes": []}
            started = time.time()

            if key == "m1":
                # My Move is a build mission: finish it through POST so the next
                # missions open, as the brief says, and check its own stars.
                try:
                    out = post_json(base + "/pixel/run",
                                    {"id": me, "level": "m1",
                                     "code": pixel.LEVEL_BY_KEY["m1"]["reference"]})
                except Exception as e:
                    entry["notes"].append(f"POST /pixel/run failed: {e}")
                    entry["console"] = driver.logs()
                    report["missions"].append(entry)
                    print(f"{key:3} {lv['name']:22} STUCK (POST)")
                    break
                entry["result"] = "OK" if out.get("stars") == [True, True, True] else "STUCK"
                entry["stars"] = out.get("stars")
                entry["notes"].append("skipped in the page; finished through POST /pixel/run "
                                      "with the reference, as the brief asks")
                entry["seconds"] = round(time.time() - started, 2)
                entry["console"] = driver.logs()
                report["missions"].append(entry)
                preopened = None
                print(f"{key:3} {lv['name']:22} {entry['result']} (POST)")
                continue

            try:
                if preopened == key:
                    wait_mission_ready(driver, key)
                else:
                    open_mission(driver, key)
                preopened = None
                target = mode_target(driver)
                expected_target = "\n".join(line for line, why in lv["coach"])
                if target != expected_target:
                    entry["notes"].append("the page's coach target differs from pixel.py")
                entry["target_chars"] = len(target)
                entry["console"].extend(driver.logs())

                step = None
                if not args.skip_extras and key == "a1":
                    probe_a1(driver, report)
                if not args.skip_extras and key == "b1":
                    step = probe_b1(driver, report)
                if not args.skip_extras and key == "c2":
                    step = probe_c2(driver, report)
                if step is not None and not step["ok"]:
                    entry["result"] = "STUCK"
                    entry["stuck"] = step
                    entry["notes"].append(f"guide refused: {step.get('where')}")
                    entry["console"].extend(driver.logs())
                    report["missions"].append(entry)
                    print(f"{key:3} {lv['name']:22} STUCK {step.get('where')}")
                    break

                step = type_coach(driver, target)
                if not step["ok"]:
                    entry["result"] = "STUCK"
                    entry["stuck"] = step
                    entry["notes"].append(f"guide refused: {step.get('where')}")
                    entry["console"].extend(driver.logs())
                    report["missions"].append(entry)
                    print(f"{key:3} {lv['name']:22} STUCK {step.get('where')}")
                    break

                entry["typed_chars"] = step.get("chars")
                entry["typing_seconds"] = step.get("seconds")
                entry["code_ok"] = code_value(driver) == target
                # Guess first: answer right, except a2 where a wrong guess is tried.
                guess = "wrong" if key == "a2" else "right"
                result = run_show(driver, guess_choice=guess)
                entry["show_seconds"] = result["show_seconds"]
                entry["seen"] = {"verdict": result["verdict"].strip(),
                                 "caption": result["caption"].strip()}
                if result.get("guess"):
                    entry["guess"] = result["guess"]
                    if key == "a2":
                        ok = "Good guess! It was really" in result["verdict"]
                        record(report, "a wrong Guess first answer", "a2", ok,
                               result["verdict"].strip()[:500],
                               "it says what the answer really was and still runs the show")
                stars = result["best"] or []
                entry["stars"] = stars
                entry["win"] = {"shown": result["win"], "title": result["winTitle"],
                                "stars": result["winStars"], "do": result["winDo"]}
                if result["show_timed_out"]:
                    entry["notes"].append("the show timed out")
                if stars == [True, True, True]:
                    entry["result"] = "OK"
                else:
                    entry["notes"].append("not three stars")

                if key == "a2" and not args.skip_extras:
                    # Stay here for Your turn and Fix it, then open the next one.
                    entry["win"]["handled"] = handle_win(
                        driver, result, open_gift=False, allow_next=False)
                    do_your_turn_and_fix(driver, report)
                    if next_key and next_key != "m1":
                        open_mission(driver, next_key)
                        preopened = next_key
                else:
                    allow = bool(next_key) and next_key != "m1"
                    win = handle_win(driver, result,
                                     open_gift=(key == pixel.LEVEL_ORDER[0]),
                                     allow_next=allow)
                    entry["win"]["handled"] = win
                    preopened = win.get("opened")
                entry["console"].extend(driver.logs())
            except WebDriverError as e:
                entry["result"] = "STUCK"
                entry["notes"].append(str(e)[:2000])
                try:
                    entry["state"] = driver.state()
                except Exception:
                    pass
                entry["console"].extend(driver.logs())
                report["missions"].append(entry)
                print(f"{key:3} {lv['name']:22} STUCK {str(e)[:160]}")
                break
            entry["seconds"] = round(time.time() - started, 2)
            report["missions"].append(entry)
            print(f"{key:3} {lv['name']:22} {entry['result']} "
                  f"{stars if 'stars' in entry else ''} ({entry['seconds']}s)")

        final = driver.js("return typeof S !== 'undefined' && S ? "
                          "{stars: S.stars, max: S.max_stars, open: S.free_open} : null")
        report["finished_all"] = bool(final and final["stars"] == final["max"])
        report["final"] = final
        report["console"].extend(driver.logs())
    finally:
        report["ended"] = time.strftime("%Y-%m-%d %H:%M:%S")
        driver.close()

    # Seeded console errors are often a missing favicon: keep the message, but
    # say which page they came from in the report.
    out = args.json_out or os.path.join(ROOT, "tools", "e2e_coach_results.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    bad = [e for e in report["console"] if e.get("level") in ("SEVERE", "ERROR")]
    print(f"\nwrote {out}")
    print(f"missions OK: {sum(1 for m in report['missions'] if m['result'] == 'OK')}"
          f"/{len(report['missions'])}   console errors: {len(bad)}")
    return 0 if all(m["result"] == "OK" for m in report["missions"]) and report["finished_all"] else 1


def post_json(url, data):
    req = urllib.request.Request(url, data=json.dumps(data).encode(), method="POST",
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=120) as f:
        return json.load(f)


if __name__ == "__main__":
    sys.exit(main())
