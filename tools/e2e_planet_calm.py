#!/usr/bin/env python3
"""An accessibility walk through every Strange Planet page a student sees.

This is a tool, not a unittest: it turns calm mode and bigger text on the way a
kid does (the checkboxes on the ? card), then drives headless Chromium at
1366x768 and 1280x720 through the level, win card, toasts, garage, Paint Shop,
Levels map, hints, typing coach, help card, Team Mission, Lounge, Predict it
and the Rover Farm.  It also hooks AudioContext while the class's sound setting
is off.

It fails (exit 1) on motion that stays on in calm mode (pixel changes between
two screenshots 300 ms apart, or running CSS animations), on clipped/off-screen
pieces with bigger text, on audio starting while sound is off, and on browser
console errors.  Screenshots go to --shots.

Start a server of your own first, then run:

    MAZE_PORT=8798 MAZE_STATE_FILE=/tmp/calm-state.json python3 server.py
    python3 tools/e2e_planet_calm.py --base http://127.0.0.1:8798 \\
        --admin-key 0106 --shots /tmp/calm-shots

It only ever talks to the server at --base, and never starts or kills one.
"""
import argparse
import json
import os
import sys
import time
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import wd                       # noqa: E402

from PIL import Image, ImageChops   # noqa: E402


def http_json(url, data=None, timeout=30):
    req = urllib.request.Request(
        url, None if data is None else json.dumps(data).encode(),
        {"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as f:
        return json.load(f)


class Report:
    def __init__(self):
        self.failures = []
        self.notes = []

    def fail(self, where, what, detail=""):
        row = f"{where}: {what}"
        if detail:
            row += f" ({detail})"
        self.failures.append(row)
        print("  FAIL", row)

    def note(self, text):
        self.notes.append(text)
        print("  note:", text)


REPORT = Report()


class Kid:
    """One student's browser, and the small set of things a kid presses."""

    def __init__(self, base, name, width, height, shots):
        self.base = base.rstrip("/")
        self.name = name
        self.width, self.height = width, height
        self.shots = shots
        os.makedirs(shots, exist_ok=True)
        self.id = http_json(self.base + "/join", {"name": name})["id"]
        self.d = wd.new(width, height)
        self.where = ""
        self.d.go(self.base + "/planet")
        self.d.js("localStorage.clear();localStorage.setItem('mazeId', arguments[0]);"
                  "localStorage.removeItem('planetCalm');"
                  "localStorage.removeItem('planetBig');"
                  "localStorage.removeItem('planetMuted');"
                  "localStorage.setItem('planetIntroSeen', '1');", self.id)
        self.go_planet()

    # -- pages ---------------------------------------------------------------
    def go_planet(self):
        self.where = f"/planet @{self.width}x{self.height}"
        self.d.go(self.base + "/planet")
        self.d.wait("return document.getElementById('app') && !document.getElementById('app').hidden",
                    25, "the planet page")
        self.logs()

    def go_farm(self):
        self.where = f"/planet/farm @{self.width}x{self.height}"
        self.d.go(self.base + "/planet/farm")
        self.d.wait("return document.getElementById('app') && !document.getElementById('app').hidden",
                    25, "the farm page")
        self.logs()

    # -- small checks --------------------------------------------------------
    def logs(self):
        for row in self.d.logs():
            text = row.get("message", "")
            if "favicon" in text:
                continue
            if row.get("level") == "SEVERE":
                REPORT.fail(self.where, "browser console error", text[:300])

    def quiet(self):
        """Nothing should be moving while this is true."""
        self.d.js("document.activeElement && document.activeElement.blur();"
                  "document.querySelectorAll('.toast').forEach(t => t.remove());")

    def animations(self):
        return self.d.js(r"""
            return document.getAnimations()
              .filter(a => a.playState === 'running')
              .map(a => ({name: a.animationName,
                          target: (a.effect && a.effect.target &&
                            (a.effect.target.id || a.effect.target.className || a.effect.target.tagName)) || ''}));
        """) or []

    def shot(self, name):
        path = os.path.join(self.shots, f"{name}.png")
        self.d.shot(path)
        return path

    def still(self, label, settle=.45):
        """The motion check: two screenshots 300 ms apart with calm on."""
        self.quiet()
        time.sleep(settle)
        # A toast arriving between the two shots is new content, not motion
        # (calm mode already stops its slide), so the toast corner is hidden.
        hide = "document.querySelectorAll('.toasts').forEach(t => t.style.visibility = arguments[0])"
        self.d.js(hide, "hidden")
        a_path = self.shot(label + "-a")
        time.sleep(.30)
        b_path = self.shot(label + "-b")
        self.d.js(hide, "")
        a = Image.open(a_path).convert("RGB")
        b = Image.open(b_path).convert("RGB")
        diff = ImageChops.difference(a, b)
        bbox = diff.getbbox()
        raw = diff.tobytes()
        changed = sum(1 for i in range(0, len(raw), 3)
                      if raw[i] or raw[i + 1] or raw[i + 2])
        anims = self.animations()
        if bbox and changed > 8:
            diff.crop(bbox).save(os.path.join(self.shots, label + "-diff.png"))
            REPORT.fail(self.where, f"{label} still moves in calm mode",
                        f"{changed} pixels changed, box {bbox}")
        if anims:
            REPORT.fail(self.where, f"{label} still has a running animation",
                        ", ".join(f"{x['name']} on {x['target']}" for x in anims[:6]))

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
              if (el.closest('#route, #announce, #toasts, .ac, .feed, .garage-card, .shop-card, .levels-card, .team-map, .lounge-room')) continue;
              const r = el.getBoundingClientRect();
              if (r.width < 1 || r.height < 1) continue;
              if ((r.right > innerWidth + 1 || r.left < -1 || r.bottom > innerHeight + 1 || r.top < -1)
                  && !scrollable(el)) {
                bad.push({el: name(el), text: (el.innerText || '').slice(0, 50),
                          left: Math.round(r.left), right: Math.round(r.right),
                          top: Math.round(r.top), bottom: Math.round(r.bottom)});
              }
              if (el.scrollWidth > el.clientWidth + 2 && cs.overflowX === 'hidden'
                  && cs.textOverflow !== 'ellipsis' && el.clientWidth > 4
                  && !['TEXTAREA', 'INPUT', 'SELECT'].includes(el.tagName)
                  && (el.innerText || '').trim()) {
                bad.push({el: name(el), cut: 'x', scroll: el.scrollWidth,
                          client: el.clientWidth, text: (el.innerText || '').slice(0, 50)});
              }
            }
            // Header pieces must not sit on top of one another.
            const bar = document.querySelector('#app .bar');
            const tops = bar ? [...bar.children].filter(e => e.offsetParent).map(e => {
              const r = e.getBoundingClientRect();
              return {el: name(e), left: Math.round(r.left), right: Math.round(r.right)};
            }) : [];
            for (let i = 1; i < tops.length; i++)
              if (tops[i].left < tops[i - 1].right - 1)
                bad.push({overlap: `${tops[i - 1].el} / ${tops[i].el}`});
            return {bad: bad.slice(0, 15), scrollWidth: document.documentElement.scrollWidth,
                    vw: innerWidth, scrollHeight: document.documentElement.scrollHeight, vh: innerHeight};
        """) or {}
        if info.get("bad"):
            REPORT.fail(self.where, f"{label} is clipped or overlaps with bigger text",
                        json.dumps(info["bad"])[:700])
        if info.get("scrollWidth", 0) > info.get("vw", 0) + 1:
            REPORT.fail(self.where, f"{label} scrolls sideways", json.dumps(info)[:300])

    def buttons(self, label):
        bad = self.d.js(r"""
            const out = [];
            for (const b of document.querySelectorAll('button')) {
              if (!b.offsetParent) continue;
              const r = b.getBoundingClientRect();
              if (r.width < 1 || r.height < 1) continue;
              const text = (b.innerText || '').trim();
              const label = b.getAttribute('aria-label') || b.title || '';
              if (!text && !label) out.push(b.id || b.className || b.tagName);
            }
            return out;
        """) or []
        if bad:
            REPORT.fail(self.where, f"{label} has a button with no text label", ", ".join(bad[:8]))

    def sound_hook(self):
        return self.d.js(r"""
            window.__calmAc = 0; window.__calmOsc = 0;
            const AC = window.AudioContext || window.webkitAudioContext;
            if (AC) {
              const Orig = AC;
              const Wrapped = function(...args) { window.__calmAc++; return new Orig(...args); };
              Wrapped.prototype = Orig.prototype;
              window.AudioContext = Wrapped;
              const osc = Orig.prototype.createOscillator;
              Orig.prototype.createOscillator = function(...args) {
                window.__calmOsc++; return osc.apply(this, args);
              };
            }
            return {muted: (typeof SFX !== 'undefined' ? SFX.muted : null)};
        """)

    def sound_check(self, label):
        counts = self.d.js("return {muted: (typeof SFX !== 'undefined' ? SFX.muted : null),"
                           "ac: window.__calmAc || 0, osc: window.__calmOsc || 0}") or {}
        if counts.get("muted") is False:
            REPORT.fail(self.where, f"{label}: sound is on although the class setting is off")
        if counts.get("ac") or counts.get("osc"):
            REPORT.fail(self.where, f"{label}: audio started with sound off",
                        json.dumps(counts))

    def set_settings(self, calm_id, big_id, close_id, wait_id):
        """Turn calm and bigger text on from the ? card, as a kid would."""
        self.d.click("#helpButton")
        self.d.wait(f"return !document.getElementById('{wait_id}').hidden", 6, "the help card")
        for sel in (calm_id, big_id):
            if not self.d.js("return document.getElementById(arguments[0]).checked", sel):
                self.d.js("document.getElementById(arguments[0]).click()", sel)
                time.sleep(.15)
        self.d.click(close_id)
        self.d.wait(f"return document.getElementById('{wait_id}').hidden", 6, "the help card closed")
        time.sleep(.25)

    def close(self):
        try:
            self.d.close()
        except Exception:
            pass


# --------------------------------------------------------------------------
# The pieces of the student page
# --------------------------------------------------------------------------
def check_calm_and_big_shared(kid):
    kid.set_settings("calmPick", "bigPick", "#introClose", "intro")
    values = kid.d.js("return {calm: localStorage.getItem('planetCalm'),"
                      "big: localStorage.getItem('planetBig')}") or {}
    if values.get("calm") != "1" or values.get("big") != "1":
        REPORT.fail(kid.where, "the ? card did not save calm and bigger text", json.dumps(values))
    if not kid.d.js("return document.body.classList.contains('calm') &&"
                    " document.body.classList.contains('big')"):
        REPORT.fail(kid.where, "the page did not apply calm and bigger text at once")


def check_planet_views(kid):
    kid.go_planet()
    check_calm_and_big_shared(kid)
    kid.sound_hook()
    kid.d.js("SFX.wake(); SFX.play('beep');")
    kid.sound_check("level")
    kid.still("level")
    kid.layout("level")
    kid.buttons("level")

    # A real toast, with calm on: it may appear and go, but it must not slide.
    kid.d.js("toast('🧪', 'A calm toast', 'It should not slide or bounce.');")
    time.sleep(.15)
    if kid.animations():
        REPORT.fail(kid.where, "a toast still animates in calm mode",
                    json.dumps(kid.animations()[:4]))
    kid.d.js("clearToasts()")
    time.sleep(.4)

    # Hints: the Hints button opens mission control; asking for one adds a card.
    kid.d.click("#radioButton")
    kid.d.wait("return !document.getElementById('radioPop').hidden", 6, "the hints card")
    kid.still("hints")
    kid.layout("hints")
    if not kid.d.js("return document.getElementById('hintButton').disabled"):
        kid.d.click("#hintButton")
        time.sleep(.5)
        kid.still("hint-given")
    kid.d.js("closePops()")
    time.sleep(.25)

    # The ? card itself, with the two settings on it.
    kid.d.click("#helpButton")
    kid.d.wait("return !document.getElementById('intro').hidden", 6, "the help card")
    kid.still("help-card")
    kid.layout("help-card")
    kid.d.click("#introClose")
    time.sleep(.25)

    # The typing coach: scout the practice route, turn the drive into code.
    if not kid.d.js("return !!scout"):
        kid.d.click("#scoutButton")
    kid.d.wait("return !!scout", 6, "Scout")
    for _ in range(3):
        kid.d.js("const b=[...document.querySelectorAll('#pad [data-move]')]"
                 ".find(e => e.dataset.move === 'east' && e.offsetParent); if (b) b.click();")
        time.sleep(.25)
    kid.d.wait("return !document.getElementById('scoutCode').disabled", 6, "Use as code")
    kid.d.click("#scoutCode")
    kid.d.wait("return !!site.typing", 3)   # no error here: the check below says what went wrong
    if not kid.d.js("return !!site.typing"):
        REPORT.fail(kid.where, "Use as code did not open the typing coach")
    else:
        kid.still("typing-coach")
        kid.layout("typing-coach")
        # Finish the blanks, then transmit: the win card must be still too.
        for _ in range(40):
            info = kid.d.js("return {t: site.typing && site.typing.target, gap: gapAt()}")
            if not info or info.get("gap", -1) < 0:
                break
            kid.d.send("#code", info["t"][info["gap"]])
            time.sleep(.14)
        kid.d.click("#runButton")
        try:
            kid.d.wait("return !document.getElementById('celebrate').hidden", 45, "the win card")
            time.sleep(1.6)
        except wd.WebDriverError:
            REPORT.fail(kid.where, "the win card never appeared")
        else:
            kid.still("win-card")
            kid.layout("win-card")
            kid.buttons("win-card")
            card = kid.d.js("""const c=document.querySelector('.cele-card').getBoundingClientRect();
              return {top:c.top,bottom:c.bottom,left:c.left,right:c.right,vw:innerWidth,vh:innerHeight};""")
            if card and (card["top"] < -1 or card["bottom"] > card["vh"] + 1
                         or card["left"] < -1 or card["right"] > card["vw"] + 1):
                REPORT.fail(kid.where, "the win card is off screen with bigger text", json.dumps(card))
            kid.d.js("hideCelebrate()")
            time.sleep(.3)

    # Levels map.
    kid.d.click("#levelsButton")
    kid.d.wait("return !document.getElementById('levels').hidden", 8, "the Levels map")
    kid.still("levels-map")
    kid.layout("levels-map")
    kid.d.click("#levelsClose")
    time.sleep(.3)

    # Garage, then the Paint Shop's code editor.
    kid.d.click("#starsButton")
    kid.d.wait("return !document.getElementById('garage').hidden", 8, "the garage")
    kid.still("garage")
    kid.layout("garage")
    kid.d.js("[...document.querySelectorAll('#garageTabs button')]"
             ".find(b => /paint/i.test(b.textContent)).click();")
    time.sleep(.4)
    kid.still("garage-paint-tab")
    if kid.d.exists("#shopDoor"):
        kid.d.click("#shopDoor")
        kid.d.wait("return !document.getElementById('paintShop').hidden", 8, "Paint Shop")
        kid.still("paint-shop")
        kid.layout("paint-shop")
        size = kid.d.js("return getComputedStyle(document.getElementById('shopCode')).fontSize")
        if size not in ("18px", "19px"):
            REPORT.fail(kid.where, "Paint Shop code is still small with bigger text", size)
        kid.d.click("#shopBack")
        time.sleep(.3)
    kid.d.click("#garageClose")
    time.sleep(.25)

    # Calm must also stop the Halloween candy bump, the warm-up/typing coach
    # glow, and a candy-button bump already queued in the page.
    probe = kid.d.js(r"""
      const box = document.createElement('div');
      box.innerHTML = '<div class="warm-code"><span class="next">e</span></div>' +
                      '<div class="type-coach"><kbd class="next">e</kbd></div>' +
                      '<div class="candy-button bump">candy</div>';
      document.body.appendChild(box);
      const names = [...box.querySelectorAll('*')].map(e => ({e, a: e.getAnimations().map(x => x.animationName)}));
      const running = names.filter(x => x.a.length);
      box.remove();
      return running.map(x => x.e.className + ':' + x.a.join(','));
    """) or []
    if probe:
        REPORT.fail(kid.where, "calm mode leaves a warm-up/typing/candy animation on", ", ".join(probe))

    # Team Mission.
    kid.d.click("#teamButton")
    kid.d.wait("return !document.getElementById('team').hidden", 10, "the Team Mission")
    time.sleep(.8)
    kid.still("team")
    kid.layout("team")
    kid.buttons("team")
    kid.d.click("#teamClose")
    time.sleep(.3)

    # Rover Lounge.
    kid.d.click("#loungeButton")
    kid.d.wait("return !document.getElementById('lounge').hidden", 10, "the Lounge")
    time.sleep(1.0)
    kid.still("lounge")
    kid.layout("lounge")
    kid.buttons("lounge")
    # Dance and honk: bubbles may appear, but must not float up in calm mode.
    kid.d.js("[...document.querySelectorAll('#lounge button')]"
             ".find(b => /Dance/.test(b.textContent))?.click();")
    kid.d.js("[...document.querySelectorAll('#lounge button')]"
             ".find(b => /Honk/.test(b.textContent))?.click();")
    time.sleep(.12)
    kid.still("lounge-emote", settle=.1)
    kid.sound_check("lounge")
    kid.d.click("#loungeClose")
    time.sleep(.3)

    # Predict it: open a question, look at the card, then the class screen.
    try:
        http_json(kid.base + "/admin", {"key": ADMIN_KEY, "action": "planet_predict", "n": 6})
    except Exception as exc:
        REPORT.fail(kid.where, "could not open Predict it", str(exc)[:200])
    kid.d.js("if (typeof predictLook === 'function') { predict.closed = null; predict.n = null; predictLook(); }")
    try:
        kid.d.wait("return !document.getElementById('predict').hidden", 10, "the Predict it card")
        time.sleep(.4)
        kid.still("predict-card")
        kid.layout("predict-card")
        size = kid.d.js("return getComputedStyle(document.getElementById('predictCode')).fontSize")
        if size not in ("18px", "19px"):
            REPORT.fail(kid.where, "Predict code is still small with bigger text", size)
        kid.d.click("#predictClose")
        time.sleep(.3)
    except wd.WebDriverError:
        REPORT.fail(kid.where, "the Predict it card never appeared")

    # The class screen is not a student page, but it reads the same calm key.
    kid.where = f"/planet/predict @{kid.width}x{kid.height}"
    kid.d.go(kid.base + "/planet/predict")
    time.sleep(.8)
    if not kid.d.js("return typeof CALM !== 'undefined' && CALM"):
        REPORT.fail(kid.where, "the Predict it screen ignores the calm setting")
    kid.still("predict-screen")
    kid.sound_check("planet")


def check_farm(kid):
    kid.go_farm()
    # The farm's own ? card must already know the shared settings.
    if not kid.d.js("return document.body.classList.contains('calm') &&"
                    " document.body.classList.contains('big')"):
        REPORT.fail(kid.where, "the farm did not get the calm and bigger text chosen on /planet")
    kid.sound_hook()
    kid.d.js("if (typeof SFX !== 'undefined') SFX.play('coins');")
    kid.sound_check("farm before a day")
    kid.still("farm")
    kid.layout("farm")
    kid.buttons("farm")

    # Run one day.  In calm mode there must be no night fade and no meteor
    # falling; the rover may drive (that is the program).
    kid.d.click("#runButton")
    seen_night = seen_falls = False
    end = time.time() + 45
    while time.time() < end:
        state = kid.d.js("return {busy: !!busy, night: typeof night !== 'undefined' && !!night,"
                         "falls: typeof falls !== 'undefined' ? falls.length : 0,"
                         "play: typeof play !== 'undefined' && !!play};") or {}
        seen_night = seen_night or bool(state.get("night"))
        seen_falls = seen_falls or bool(state.get("falls"))
        if not state.get("busy") and not state.get("play") and not state.get("night"):
            break
        time.sleep(.12)
    else:
        REPORT.fail(kid.where, "the farm day did not finish")
    if seen_night:
        REPORT.fail(kid.where, "the night still fades in calm mode")
    if seen_falls:
        REPORT.fail(kid.where, "a meteor still falls in calm mode")
    time.sleep(.8)
    kid.still("farm-after-day")
    kid.layout("farm-after-day")
    kid.sound_check("farm after a day")

    # Toast, shop and a classmate's farm.
    kid.d.js("toast('🧪', 'A calm farm toast', 'It should not slide.');")
    time.sleep(.15)
    if kid.animations():
        REPORT.fail(kid.where, "a farm toast still animates in calm mode")
    kid.d.js("document.getElementById('toasts').replaceChildren()")
    for button, label, close in (("#helpButton", "farm-help", "closeDialogs()"),
                                 ("#shopButton", "farm-shop", "closeDialogs()"),
                                 ("#visitButton", "farm-visit", "closeDialogs()")):
        kid.d.click(button)
        time.sleep(.45)
        kid.still(label)
        kid.layout(label)
        kid.d.js(close)
        time.sleep(.25)

    # A bigger-text code box really is bigger.
    size = kid.d.js("return getComputedStyle(document.getElementById('code')).fontSize")
    if size not in ("18px", "19px"):
        REPORT.fail(kid.where, "the farm code box is still small with bigger text", size)


def run_size(base, admin_key, width, height, shots, tag):
    global ADMIN_KEY
    ADMIN_KEY = admin_key
    kid = Kid(base, f"Calm E2E {tag} {int(time.time())}", width, height, shots)
    try:
        print(f"\n--- {width}x{height} ---")
        check_planet_views(kid)
        check_farm(kid)
        kid.logs()
    finally:
        kid.close()


def main():
    global ADMIN_KEY
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="http://127.0.0.1:8798")
    ap.add_argument("--admin-key", default="0106")
    ap.add_argument("--shots", default="calm-e2e-shots")
    args = ap.parse_args()
    base = args.base.rstrip("/")
    ADMIN_KEY = args.admin_key

    # The teacher's switches this class runs with.
    for action, extra in (("planet_easy", {"on": True}), ("planet_farm", {"on": True}),
                          ("planet_lounge", {"on": True}), ("planet_team", {"on": True}),
                          ("planet_sound", {"on": False})):
        try:
            http_json(base + "/admin", {"key": ADMIN_KEY, "action": action, **extra})
        except Exception as exc:
            raise SystemExit(f"could not set {action}: {exc}")

    for width, height, tag in ((1366, 768, "1366"), (1280, 720, "1280")):
        # A question left open from the last run must not sit over the page
        # while the other parts are checked.  The Predict it test opens it.
        http_json(base + "/admin", {"key": ADMIN_KEY, "action": "planet_predict", "n": ""})
        run_size(base, ADMIN_KEY, width, height, args.shots, tag)
    http_json(base + "/admin", {"key": ADMIN_KEY, "action": "planet_predict", "n": ""})

    print("\n=== result ===")
    if REPORT.failures:
        print(f"{len(REPORT.failures)} failure(s):")
        for row in REPORT.failures:
            print(" -", row)
        return 1
    print("all calm, bigger-text and sound checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
