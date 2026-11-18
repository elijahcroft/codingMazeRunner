#!/usr/bin/env python3
"""Play Strange Planet's rooms like four kids in the class: the Team Mission,
the Rover Lounge, Predict it and the class race, with /planet/show following
them on the projector. This is a tool, not a unittest: it drives headless
Chromium through tools/wd.py, takes screenshots and fails (exit 1) on console
errors, clipped cards, missing buttons or a room that won't close.

Start a server first:

    MAZE_PORT=8794 MAZE_STATE_FILE=/tmp/rooms-state.json python3 server.py
    python3 tools/e2e_planet_rooms.py --base http://127.0.0.1:8794 \\
        --admin-key 0106 --shots /tmp/rooms-shots

Or let the tool run a fresh test server itself:

    python3 tools/e2e_planet_rooms.py --start-server --fresh

It only ever talks to the server at --base. The server it starts is killed by
the exact process it started, never by name or pattern.
"""
import argparse
import json
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, ROOT)
import wd                       # noqa: E402
import planet                   # noqa: E402
import planet_predict           # noqa: E402
import planet_team              # noqa: E402

ARROWS = {"north": ("ArrowUp", "ArrowUp", 38), "south": ("ArrowDown", "ArrowDown", 40),
          "west": ("ArrowLeft", "ArrowLeft", 37), "east": ("ArrowRight", "ArrowRight", 39)}


class CheckFailed(AssertionError):
    pass


# --------------------------------------------------------------------------
# Small HTTP helpers for setup and for the teacher page's own actions.
# --------------------------------------------------------------------------
def post(url, data, timeout=60):
    req = urllib.request.Request(
        url, data=json.dumps(data).encode(),
        headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as f:
        return json.load(f)


def get(url, timeout=60):
    with urllib.request.urlopen(url, timeout=timeout) as f:
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
    port = base.rsplit(":", 1)[-1] if ":" in base else "8794"
    log = open(log_file, "ab") if log_file else subprocess.DEVNULL
    env = dict(os.environ, MAZE_PORT=port, MAZE_STATE_FILE=state_file)
    proc = subprocess.Popen([sys.executable, "server.py"], cwd=ROOT, env=env,
                            stdout=log, stderr=log)
    for _ in range(240):
        if server_up(base):
            return proc
        if proc.poll() is not None:
            raise SystemExit(f"server exited; see {log_file}")
        time.sleep(.1)
    proc.terminate()
    raise SystemExit("server did not answer")


def state_admin_key(path, fallback):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f).get("admin_key") or fallback
    except Exception:
        return fallback


# --------------------------------------------------------------------------
# A browser page, with the checks this hunt needs.
# --------------------------------------------------------------------------
class Page:
    def __init__(self, base, shots, name, width=1366, height=768):
        self.base, self.shots, self.name = base, shots, name
        self.width, self.height = width, height
        self.d = wd.new(width, height)
        self.failures = []
        self._shot_n = 0

    def js(self, script, *args):
        return self.d.js(script, *args)

    def check(self, ok, what, detail=""):
        if ok:
            print(f"  ok  {self.name}: {what}")
        else:
            msg = f"{self.name}: {what}" + (f" [{detail}]" if detail else "")
            print(f"  FAIL {msg}")
            self.failures.append(msg)
        return ok

    def fail(self, what):
        self.failures.append(f"{self.name}: {what}")
        print(f"  FAIL {self.name}: {what}")

    def wait_for(self, script, timeout, what, *args):
        end = time.time() + timeout
        last = None
        while time.time() < end:
            try:
                value = self.js(script, *args)
                if value:
                    return value
            except Exception as exc:        # the page may be loading
                last = str(exc)[:160]
            time.sleep(.05)
        raise CheckFailed(f"{self.name}: timed out waiting for {what} ({last or 'no value'})")

    def cdp(self, method, params):
        return self.d.request("POST", f"/session/{self.d.sid}/goog/cdp/execute",
                              {"cmd": method, "params": params})

    def click_at(self, x, y):
        for typ in ("mousePressed", "mouseReleased"):
            self.cdp("Input.dispatchMouseEvent",
                     {"type": typ, "x": round(x), "y": round(y),
                      "button": "left", "clickCount": 1})

    def key(self, key, code=None, vk=0):
        for typ in ("keyDown", "keyUp"):
            self.cdp("Input.dispatchKeyEvent",
                     {"type": typ, "key": key, "code": code or key,
                      "windowsVirtualKeyCode": vk, "nativeVirtualKeyCode": vk})

    def shot(self, tag):
        self._shot_n += 1
        name = re.sub(r"[^a-zA-Z0-9_.-]+", "-", tag)[:70]
        path = os.path.join(self.shots, f"{self.name.replace(' ', '_')}-{self._shot_n:02d}-{name}.png")
        self.d.shot(path)
        return path

    def logs(self, where):
        bad = [e for e in self.d.logs() if e["level"] not in ("INFO", "DEBUG")]
        if bad:
            self.check(False, f"console at {where}", json.dumps(bad)[:700])
        return bad

    def close(self):
        try:
            self.logs("final")
        finally:
            self.d.close()

    # -- layout checks ----------------------------------------------------
    def layout(self, card, container=None):
        sel = container or card
        info = self.js("""const c=document.querySelector(arguments[0]), box=document.querySelector(arguments[1]);
          if(!c) return {missing:true};
          const r=c.getBoundingClientRect();
          const bs=[...box.querySelectorAll('button')].filter(b=>b.offsetParent).map(b=>{
            const q=b.getBoundingClientRect();
            return {text:(b.innerText||'').trim(), aria:b.getAttribute('aria-label')||'',
                    rect:[q.left,q.top,q.right,q.bottom]};});
          return {card:[r.left,r.top,r.right,r.bottom], vw:innerWidth, vh:innerHeight,
                  sw:document.documentElement.scrollWidth, buttons:bs};""", card, sel)
        if info.get("missing"):
            self.check(False, f"{card} is on the page")
            return info
        r = info["card"]
        self.check(r[1] >= -1 and r[3] <= info["vh"] + 1,
                   f"{card} fits top to bottom", json.dumps(info["card"]))
        self.check(r[0] >= -1 and r[2] <= info["vw"] + 1,
                   f"{card} fits left to right", json.dumps(info["card"]))
        self.check(info["sw"] <= info["vw"] + 1, "page has no sideways scroll",
                   f'{info["sw"]} > {info["vw"]}')
        for b in info["buttons"]:
            words = re.search(r"[A-Za-z0-9]", b["text"] + " " + b["aria"])
            self.check(bool(words), "visible button has a word label",
                       f'{b["text"]!r} / {b["aria"]!r}')
            self.check(b["rect"][1] >= -1 and b["rect"][3] <= info["vh"] + 1,
                       "visible button fits the screen", json.dumps(b["rect"]))
        return info

    def text(self, css):
        return self.js("const el=document.querySelector(arguments[0]);"
                       "return el ? (el.innerText || '') : ''", css)

    def toast_text(self):
        return self.js("return [...document.querySelectorAll('#toasts .toast')]"
                       ".map(e=>e.innerText).join(' | ')")


# --------------------------------------------------------------------------
# The student page
# --------------------------------------------------------------------------
class Kid(Page):
    def __init__(self, base, shots, name, player_id, calm=False):
        super().__init__(base, shots, name)
        self.player_id = player_id
        self.calm = calm
        self.d.go(base + "/planet")
        self.wait_for("return !!document.querySelector('#name')", 15, "join form")
        self.d.js("localStorage.setItem('mazeId', arguments[0]);"
                  "localStorage.setItem('planetIntroSeen','1');"
                  "localStorage.setItem('planetCalm', arguments[1])",
                  player_id, "1" if calm else "0")
        self.d.go(base + "/planet")
        self.wait_for("return !document.querySelector('#app').hidden", 20, "app after join")
        if self.js("return !document.querySelector('#intro').hidden"):
            self.d.click("#introClose")
        self.check(self.js("return !!me"), "student is signed in")
        if calm:
            self.check(self.js("return CALM && document.body.classList.contains('calm')"),
                       "calm mode is on")

    # -- room buttons and dialogs ----------------------------------------
    def room_button(self, button):
        return self.js("const b=document.querySelector(arguments[0]);"
                       "return b && !b.hidden ? b.innerText.trim() : ''", button)

    def open_room(self, button, dialog, timeout=10):
        self.wait_for("const b=document.querySelector(arguments[0]); return b && !b.hidden",
                      timeout, f"{button} button", button)
        self.d.click(button)
        self.wait_for("return !document.querySelector(arguments[0]).hidden", 8, f"{dialog} open", dialog)

    def close_room(self, button, dialog):
        self.d.click(button)
        self.wait_for("return document.querySelector(arguments[0]).hidden", 5, f"{dialog} closed", dialog)

    # -- Team Mission -----------------------------------------------------
    def team(self):
        return self.js("""const m=team.rovers.get(team.you);
          return {hidden:document.querySelector('#team').hidden, level:team.level,
            view:!!team.view, won:!!(team.view&&team.view.won),
            rovers:[...(team.view?team.view.rovers:[])], path:team.path.length,
            at:m?[m.tr,m.tc]:null, say:document.querySelector('#teamSay').textContent,
            job:document.querySelector('#teamJob').textContent,
            coder:!document.querySelector('#teamCoder').hidden,
            codeSay:document.querySelector('#teamCodeSay').textContent,
            win:document.querySelector('#teamWin').hidden?null:document.querySelector('#teamWin').innerText};""")

    def team_wait(self, script, timeout, what, *args):
        return self.wait_for(script, timeout, what, *args)

    def _team_walk(self, target=None, timeout=45):
        end = time.time() + timeout
        last = None
        while time.time() < end:
            st = self.team()
            last = st
            if st["hidden"]:
                raise CheckFailed(f"{self.name}: the Team Mission closed mid-drive")
            if st["won"]:
                return st
            if st["path"] == 0 and (target is None or st["at"] == target):
                time.sleep(.3)             # let the last POST land
                st = self.team()
                if st["won"]:
                    return st
                if st["path"] == 0 and (target is None or st["at"] == target):
                    return st
            time.sleep(.08)
        raise CheckFailed(f"{self.name}: drive stuck {json.dumps(last)[:500]}")

    def team_drive_to(self, r, c, timeout=45):
        for _ in range(2):
            out = self.js("""const m=team.rovers.get(team.you);
              const ways=teamRoute([m.tr,m.tc],arguments[0]);
              if(!ways) return {error:'no route',from:[m.tr,m.tc]};
              team.path=ways.slice(); return {ways:ways.length};""", [r, c])
            if out.get("error"):
                raise CheckFailed(f"{self.name}: no route {out}")
            st = self._team_walk([r, c], timeout)
            if st["won"] or st["at"] == [r, c]:
                return st
            self.fail(f"drive to {(r, c)} ended at {st['at']}")
        return st

    def team_push(self, way, squares, timeout=45):
        self.js("team.path=Array(arguments[0]).fill(arguments[1])", squares, way)
        return self._team_walk(None, timeout)

    def team_click_square(self, r, c):
        x, y = self.js("""const b=document.querySelector('#teamMap').getBoundingClientRect(), cell=b.width/TEAM_COLS;
          return [b.left+(arguments[1]+.5)*cell, b.top+(arguments[0]+.5)*cell];""", r, c)
        before = self.team()["at"]
        self.click_at(x, y)
        try:
            self.wait_for("const m=team.rovers.get(team.you); return m && (m.tr!==arguments[0][0]||m.tc!==arguments[0][1])",
                          10, "clicked route to start", before)
        except CheckFailed:
            self.fail(f"clicking square {(r, c)} did not move the rover from {before}")
        return self._team_walk(None, 25)

    def team_arrow(self, way):
        key, code, vk = ARROWS[way]
        before = self.team()["at"]
        self.key(key, code, vk)
        try:
            self.wait_for("const m=team.rovers.get(team.you); return m && (m.tr!==arguments[0][0]||m.tc!==arguments[0][1])",
                          8, f"{way} arrow moves", before)
        except CheckFailed:
            self.fail(f"{way} arrow did not move the rover from {before}")
        time.sleep(.3)
        return self.team()

    def team_pad(self, way):
        before = self.team()["at"]
        self.d.click(f'#teamPad [data-way="{way}"]')
        try:
            self.wait_for("const m=team.rovers.get(team.you); return m && (m.tr!==arguments[0][0]||m.tc!==arguments[0][1])",
                          8, f"{way} pad moves", before)
        except CheckFailed:
            self.fail(f"{way} pad did not move the rover from {before}")
        time.sleep(.3)
        return self.team()

    def team_shout(self, key):
        self.d.click(f'#teamShouts [data-shout="{key}"]')
        time.sleep(.35)
        return self.js("return (team.view&&team.view.shouts)||[]")

    def team_code(self, code, timeout=10):
        if not self.team()["coder"]:
            self.d.click("#teamCodeOpen")
            self.wait_for("return !document.querySelector('#teamCoder').hidden", 5, "code box")
        self.js("const t=document.querySelector('#teamCode'); t.value=arguments[0];"
                "t.dispatchEvent(new Event('input',{bubbles:true}));", code)
        self.d.click("#teamRun")
        self.wait_for("return !document.querySelector('#teamRun').disabled", timeout, "Run answered")
        return self.team()

    def team_level(self):
        return self.js("return team.level")

    # -- Rover Lounge -----------------------------------------------------
    def lounge(self):
        return self.js("""return {hidden:document.querySelector('#lounge').hidden, you:lounge.you,
          say:document.querySelector('#loungeSay').textContent,
          rovers:[...lounge.rovers.values()].map(r=>({seat:r.seat, tag:r.row.tag,
            x:Math.round(r.tx*100)/100, y:Math.round(r.ty*100)/100,
            act:r.act&&r.act.word, bubbles:r.bubbles.map(b=>b.text)})),
          stage:lounge.stage&&{seat:lounge.stage.seat,tag:lounge.stage.tag},
          queue:lounge.queue.slice(), card:lounge.card,
          cardText:document.querySelector('#loungeRover').hidden?'':document.querySelector('#loungeRover').innerText,
          wins:document.querySelector('#loungeWins').textContent,
          show:!document.querySelector('#showMaker').hidden};""")

    def lounge_wait_rovers(self, n, timeout=10):
        return self.wait_for("return lounge.rovers.size===arguments[0]", timeout,
                             f"{n} rovers in the lounge", n)

    def lounge_click_floor(self, r, c):
        x, y = self.js("""const b=document.querySelector('#loungeRoom').getBoundingClientRect(), cell=b.width/LOUNGE.cols;
          return [b.left+(arguments[1]+.5)*cell, b.top+(arguments[0]+.5)*cell];""", r, c)
        self.click_at(x, y)

    def lounge_click_rover(self, seat):
        x, y = self.js("""const r=lounge.rovers.get(arguments[0]); if(!r) return [0,0];
          const b=document.querySelector('#loungeRoom').getBoundingClientRect(), cell=b.width/LOUNGE.cols;
          return [b.left+r.at[0]*cell, b.top+r.at[1]*cell];""", seat)
        self.click_at(x, y)

    def lounge_act(self, what):
        self.d.click("#" + what)
        time.sleep(.45)

    def lounge_stage(self):
        self.d.click("#loungeStage")
        time.sleep(.6)

    def lounge_show(self, code="spin()\n"):
        self.d.click("#loungeShow")
        self.wait_for("return !document.querySelector('#showMaker').hidden", 5, "show maker")
        self.js("const t=document.querySelector('#showCode'); t.value=arguments[0];"
                "t.dispatchEvent(new Event('input',{bubbles:true}));", code)
        self.d.click("#showTry")
        self.wait_for("return document.querySelector('#showMsg').textContent.length>0", 8, "show tried")
        ok = "Watch your rover" in self.js("return document.querySelector('#showMsg').textContent")
        self.check(ok, "show plays", self.js("return document.querySelector('#showMsg').textContent"))
        self.d.click("#showKeep")
        self.wait_for("return document.querySelector('#showMsg').textContent.includes('Kept')", 8, "show kept")
        self.check(True, "a show can be kept for the stage")
        self.d.click("#showBack")
        self.wait_for("return document.querySelector('#showMaker').hidden", 5, "show maker closed")

    # -- Predict it -------------------------------------------------------
    def predict(self):
        return self.js("""return {hidden:document.querySelector('#predict').hidden,
          code:document.querySelector('#predictCode').textContent,
          options:[...document.querySelectorAll('#predictOptions button')].map(b=>b.textContent),
          mine:[...document.querySelectorAll('#predictOptions button')].filter(b=>b.classList.contains('mine')).map(b=>b.textContent),
          right:[...document.querySelectorAll('#predictOptions button')].filter(b=>b.classList.contains('right')).map(b=>b.textContent),
          say:document.querySelector('#predictSay').textContent};""")

    def predict_vote(self, choice):
        ok = self.js("""const b=[...document.querySelectorAll('#predictOptions button')]
          .find(e=>e.textContent===String(arguments[0])); if(!b) return false; b.click(); return true;""", choice)
        self.check(ok, f"answer {choice} is on offer")
        time.sleep(.4)
        return self.predict()

    def predict_close(self):
        self.d.click("#predictClose")
        self.wait_for("return document.querySelector('#predict').hidden", 5, "predict card closed")


# --------------------------------------------------------------------------
# The teacher page, using its real switches and buttons.
# --------------------------------------------------------------------------
class Teacher(Page):
    def __init__(self, base, shots, key):
        super().__init__(base, shots, "teacher")
        self.base, self.key = base, key
        self.d.go(base + "/planet/teacher")
        self.wait_for("return !!document.querySelector('#key')", 15, "teacher key box")
        self.d.js("localStorage.setItem('planetKey', arguments[0])", key)
        self.d.go(base + "/planet/teacher")
        self.wait_for("return !!document.querySelector('#settingsButton')", 15, "teacher page")
        self.d.click("#settingsButton")
        self.wait_for("return !document.querySelector('#settings').hidden", 5, "settings open")
        self.check(self.js("return document.querySelector('#team') && document.querySelector('#lounge')"),
                   "teacher has the Team Mission and Lounge switches")

    def overview(self):
        return get(self.base + "/planet/overview")

    def wait_field(self, field, value, timeout=10):
        end = time.time() + timeout
        last = None
        while time.time() < end:
            try:
                last = self.overview()
                if last.get(field) == value:
                    return last
            except Exception:
                pass
            time.sleep(.15)
        raise CheckFailed(f"teacher: {field} never became {value!r} (last {last and last.get(field)!r})")

    def switch(self, what, on):
        current = self.js("return document.querySelector(arguments[0]).checked", "#" + what)
        if current != on:
            self.d.js("document.querySelector(arguments[0]).click()", "#" + what)
        self.wait_field(what, on)
        return self.overview()

    def set_team_level(self, level):
        self.wait_for("return document.querySelector('#teamPick').options.length > 1", 8,
                      "team level list")
        value = str(level)
        self.d.js("const s=document.querySelector('#teamPick'); s.value=arguments[0];"
                  "s.dispatchEvent(new Event('change'));", value)
        self.wait_field("team_level", int(level))

    def team_tool(self, words):
        ok = self.js("""const b=[...document.querySelectorAll('#teamTools button')]
          .find(e=>e.innerText.includes(arguments[0])); if(!b) return false; b.click(); return true;""", words)
        self.check(ok, f"teacher has {words!r}")
        time.sleep(.5)

    def pick_predict(self, number):
        self.d.js("const s=document.querySelector('#predictPick'); s.value=arguments[0];"
                  "s.dispatchEvent(new Event('change'));", "" if number is None else str(number))
        self.wait_field("predict", number)

    def reveal(self):
        self.wait_for("return !document.querySelector('#predictReveal').hidden", 8, "Reveal button")
        self.d.click("#predictReveal")
        self.wait_field("predict_revealed", True)

    def race_board(self, on):
        if self.overview().get("race_on_board") != on:
            self.d.click("#raceBoard")
        self.wait_field("race_on_board", on)


# --------------------------------------------------------------------------
# The projector
# --------------------------------------------------------------------------
class Show(Page):
    def __init__(self, base, shots):
        super().__init__(base, shots, "show", 1920, 1080)
        self.d.go(base + "/planet/show")
        self.wait_for("return !!document.querySelector('#room')", 15, "class screen")

    def room_src(self):
        return self.js("return document.querySelector('#room').getAttribute('src')")

    def wait_room(self, src, timeout=10):
        self.wait_for("const r=document.querySelector('#room');"
                      "return !r.hidden && r.getAttribute('src')===arguments[0]", timeout,
                      f"class screen showing {src}", src)
        self.check(True, f"class screen follows to {src}")
        return self.room_src()

    def wait_no_room(self, timeout=10):
        self.wait_for("return document.querySelector('#room').hidden", timeout, "class screen back to expedition")
        self.check(True, "class screen goes back to the expedition")

    def press_escape(self):
        # Focus inside the room first, as a teacher would after clicking it.
        self.d.js("const w=document.querySelector('#room').contentWindow; if(w) w.focus();")
        self.key("Escape", "Escape", 27)
        time.sleep(.25)
        if self.js("return !document.querySelector('#room').hidden"):
            # A headless window can keep focus on the parent; the room itself
            # listens for the same key once it has loaded.
            self.d.js("const w=document.querySelector('#room').contentWindow;"
                      "if(w) w.dispatchEvent(new w.KeyboardEvent('keydown',{key:'Escape',bubbles:true}));")
            time.sleep(.2)


# --------------------------------------------------------------------------
# Scenarios
# --------------------------------------------------------------------------
def check_show_frame(show):
    info = show.js("""const r=document.querySelector('#room'), b=r.getBoundingClientRect();
      return {sw:document.documentElement.scrollWidth, vw:innerWidth,
              room:[b.left,b.top,b.right,b.bottom], vh:innerHeight};""")
    show.check(info["sw"] <= info["vw"] + 1, "class screen has no sideways scroll", json.dumps(info))
    show.check(info["room"][1] >= -1 and info["room"][3] <= info["vh"] + 1,
               "class screen room fits the screen", json.dumps(info["room"]))


def team_scenario(base, shots, kids, teacher, show, failures):
    print("\n=== 🤝 Team Mission: four kids on one map ===")
    teacher.switch("team", True)
    for kid in kids:
        try:
            kid.wait_for("return !document.querySelector('#teamButton').hidden", 8,
                         "Team Mission button")
            kid.check(True, "Team Mission button came up")
        except CheckFailed as exc:
            kid.fail(str(exc))
    show.wait_room("/planet/team/watch")
    check_show_frame(show)
    for kid in kids:
        try:
            kid.open_room("#teamButton", "#team")
        except CheckFailed as exc:
            kid.fail(str(exc))
    for kid in kids:
        try:
            kid.team_wait("return team.view && team.rovers.size===4", 10, "four rovers on the map")
        except CheckFailed as exc:
            kid.fail(str(exc))
        kid.layout(".team-card", "#team")
        st = kid.team()
        kid.check(st["level"] == planet_team.HUB, "class starts on the Mission Hub", str(st["level"]))
        kid.check(bool(st["say"]), "the page says what to do", st["say"])
        kid.check(bool(st["job"]), "the next job says what to do", st["job"])
        kid.shot("team-hub")
    show.shot("team-hub")

    # Four ways to drive, at the same moment.
    print("-- driving four ways")
    kids[0].team_click_square(9, 24)
    kids[1].team_arrow("north")
    kids[2].team_pad("east")
    kids[3].team_code("north(2)\n")
    kids[3].d.click("#teamCodeClose")
    for kid in kids:
        kid.team_wait("return team.view && team.rovers.size===4", 5, "four rovers after driving")
    moved = kids[0].js("return team.view.rovers.map(r=>r[1]+','+r[2])")
    kids[0].check(len(set(moved)) >= 2, "all four rovers drive and stay on the map", str(moved))

    # Shouts and the helper rover.
    shouts = kids[0].team_shout("help")
    kids[0].check(bool(shouts), "a shout goes to the class", str(shouts))
    kids[1].d.click('#teamShouts [data-shout="hold"]')
    time.sleep(.5)
    heard = kids[2].js("return (team.view&&team.view.shouts)||[]")
    kids[2].check(any("Help" in s[2] for s in heard), "another page hears a shout", str(heard))
    teacher.team_tool("🤖 Helper rover")
    time.sleep(.6)
    helper = kids[0].js("return !!team.people.get(-1) && team.view.rovers.some(r=>r[0]===-1)")
    kids[0].check(helper, "the helper rover appears on every map")
    teacher.team_tool("Send the helper away")

    # Teacher closes the room while everyone is in it.
    print("-- teacher closes the room while four kids are in it")
    codes = [kid.js("return document.querySelector('#code').value") for kid in kids]
    teacher.switch("team", False)
    for kid, code in zip(kids, codes):
        try:
            kid.wait_for("return document.querySelector('#team').hidden && document.querySelector('#teamButton').hidden",
                         4, "Team Mission closed")
            kid.check(True, "closed room returns the kid to their level")
            kid.check("closed for now" in kid.toast_text(), "a toast says the room closed", kid.toast_text()[:200])
            kid.check(kid.js("return document.querySelector('#code').value") == code,
                      "their own code is just as they left it")
        except CheckFailed as exc:
            kid.fail(str(exc))
        kid.logs("team closed")
        kid.shot("team-closed")
    show.wait_no_room()

    # Reopen, late joiner, leave and reload.
    print("-- late joiner, reload and leave")
    teacher.switch("team", True)
    for kid in kids:
        kid.wait_for("return !document.querySelector('#teamButton').hidden", 8, "Team Mission button back")
        kid.open_room("#teamButton", "#team")
    teacher.set_team_level(0)
    for kid in kids:
        kid.team_wait("return team.level===0 && team.view && team.rovers.size===4", 10, "Landing Bay")
    start = kids[1].team()["at"]
    kids[1].d.go(base + "/planet")
    kids[1].wait_for("return !document.querySelector('#app').hidden", 20, "reload")
    kids[1].wait_for("return !document.querySelector('#teamButton').hidden", 8, "Team Mission button after reload")
    kids[1].open_room("#teamButton", "#team")
    kids[1].team_wait("return team.view && team.level===0", 10, "back on the same level")
    kids[1].check(kids[1].team()["at"] == start, "a reload puts the rover back where it was",
                  f'{start} -> {kids[1].team()["at"]}')
    kids[1].logs("team reload")

    late = make_kid(base, shots, "Late Lea", calm=True)
    try:
        late.wait_for("return !document.querySelector('#teamButton').hidden", 8, "late Team Mission button")
        late.open_room("#teamButton", "#team")
        late.team_wait("return team.view && team.rovers.size===5", 10, "five rovers")
        for kid in kids:
            kid.team_wait("return team.rovers.size===5", 8, "the late joiner reaches everyone")
        kids[0].check(True, "a late joiner joins the live map")
        # This student never drives; everyone still moves.
        late.check(late.js("return team.rovers.get(team.you)!==undefined"), "the quiet rover is on the map")
        kids[2].team_arrow("south")
        late.team_wait("const m=team.rovers.get(team.you); return m && team.rovers.size===5", 5,
                       "quiet rover still sees the class")
        late.shot("team-late-quiet")
        late.d.click("#teamClose")
        time.sleep(6)
        for kid in kids:
            kid.team_wait("return team.rovers.size===4", 8, "the late joiner has left")
        kids[0].check(True, "a rover that leaves is gone from everyone's map")
    finally:
        late.close()
        failures.extend(late.failures)

    # Landing Bay, both rovers.
    print("-- playing Landing Bay to the end")
    a, b = kids[0], kids[1]
    a.team_drive_to(3, 4); a.team_push("south", 3)
    a.team_drive_to(7, 13)
    b.team_drive_to(7, 20); b.team_push("west", 6)
    a.team_drive_to(3, 23); a.team_push("west", 2)
    b.team_drive_to(11, 23); b.team_push("west", 2)
    a.team_drive_to(1, 25)
    b.team_drive_to(1, 26)
    for kid in kids:
        try:
            kid.team_wait("return !document.querySelector('#teamWin').hidden", 12, "win card")
            kid.check(True, "every page shows the win card")
            kid.check("Level" in kid.team()["win"] and "done" in kid.team()["win"],
                      "win card has the level and time", kid.team()["win"])
        except CheckFailed as exc:
            kid.fail(str(exc))
        kid.logs("team win")
        kid.shot("team-win")
    kids[3].check(kids[3].js("return CALM && team.confetti.length===0"),
                  "calm mode keeps the win quiet")
    show.shot("team-win")
    for kid in kids:
        kid.team_wait("return team.level===1", 16, "next level after the pause")
        kid.check(True, "the class rolls on to the next level together")
        kid.check(kid.js("return document.querySelector('#teamWin').hidden"), "the win card goes away")
        kid.logs("team next")

    # Four Corners, two more rovers into the vault.
    print("-- playing Four Corners to the end")
    a.team_drive_to(6, 5); a.team_push("north", 2)
    a.team_drive_to(6, 15); a.team_push("north", 2)
    a.team_drive_to(8, 5); a.team_push("south", 2)
    a.team_drive_to(11, 15)
    vault = [(r, c) for r, row in enumerate(planet_team.LEVELS[1]["map"])
             for c, ch in enumerate(row) if ch == "*"]
    b.team_drive_to(*vault[0])
    kids[2].team_drive_to(*vault[1])
    for kid in kids:
        try:
            kid.team_wait("return !document.querySelector('#teamWin').hidden", 12, "second win card")
            kid.check(True, "the second level is won together")
        except CheckFailed as exc:
            kid.fail(str(exc))
        kid.logs("four corners win")
        kid.shot("four-win")
    show.shot("four-win")
    for kid in kids:
        kid.team_wait("return team.level===2", 16, "next level after the second pause")
        kid.check(True, "the class carries on after two levels")
        kid.logs("four next")
    show.shot("team-next")
    teacher.switch("team", False)
    for kid in kids:
        kid.wait_for("return document.querySelector('#team').hidden", 5, "team closed before the lounge")
    show.wait_no_room()
    return True


def lounge_scenario(base, shots, kids, teacher, show, failures):
    print("\n=== 🛋 Rover Lounge: four rovers hanging out ===")
    teacher.switch("lounge", True)
    for kid in kids:
        kid.wait_for("return !document.querySelector('#loungeButton').hidden", 8, "Lounge button")
        kid.open_room("#loungeButton", "#lounge")
    for kid in kids:
        kid.lounge_wait_rovers(4)
        kid.layout(".lounge-card", "#lounge")
        kid.check(bool(kid.lounge()["say"]), "the lounge says what to do", kid.lounge()["say"])
        kid.check(bool(kid.lounge()["wins"]), "the trophy shelf says what it is for")
        kid.shot("lounge-open")
    show.wait_room("/planet/lounge/watch")
    check_show_frame(show)
    show.shot("lounge")
    print("-- moving, tricks and a cheer")
    kids[0].lounge_click_floor(4, 5)
    kids[1].key("ArrowRight", "ArrowRight", 39)
    kids[2].lounge_click_floor(7, 10)
    time.sleep(1.2)
    seen = kids[0].lounge()["rovers"]
    kids[0].check(len(seen) == 4 and len({(r["x"], r["y"]) for r in seen}) >= 2,
                  "everyone sees the rovers move", str(seen))
    kids[0].lounge_act("loungeHonk")
    kids[1].lounge_act("loungeDance")
    kids[2].lounge_act("loungeWave")
    time.sleep(1)
    acts = kids[3].js("return [...lounge.rovers.values()].map(r=>[r.seat,r.act&&r.act.word,r.bubbles.map(b=>b.text)])")
    kids[3].check(any(a[1] == "dance" or a[2] for a in acts), "tricks show on a friend's screen", str(acts))
    kids[0].lounge_click_rover(2)
    time.sleep(.5)
    card = kids[0].lounge()["cardText"]
    kids[0].check("Build" not in card and bool(card), "clicking a rover opens its card", card[:200])
    kids[0].check("Send a cheer" in card, "a friend's card offers a cheer")
    kids[0].d.js("const b=document.querySelector('#loungeRover [data-cheer]'); if(b) b.click()")
    time.sleep(.6)
    kids[1].check("cheered" in kids[1].toast_text(), "a cheer reaches the friend", kids[1].toast_text()[:200])
    kids[0].d.js("document.querySelector('#loungeRover .lc-close').click()")

    print("-- a show and the stage queue")
    kids[0].lounge_show("spin()\n")
    kids[0].lounge_stage()
    kids[0].wait_for("return lounge.stage && lounge.stage.seat===lounge.you", 6,
                     "the first rover takes the stage")
    kids[1].lounge_stage()
    kids[0].check("You're on stage" in kids[0].lounge()["say"], "the first rover takes the stage")
    kids[1].check("next" in kids[1].lounge()["say"].lower(), "the next rover is told they are next",
                  kids[1].lounge()["say"])
    show.shot("lounge-stage")
    end = time.time() + 12
    while time.time() < end:
        if kids[1].lounge()["stage"] and kids[1].lounge()["stage"]["seat"] == kids[1].lounge()["you"]:
            break
        time.sleep(.3)
    kids[1].check(kids[1].lounge()["stage"] and kids[1].lounge()["stage"]["seat"] == kids[1].lounge()["you"],
                  "the stage passes to the next rover")
    kids[1].shot("lounge-stage-next")

    print("-- reload and leave")
    pos = kids[2].lounge()["rovers"]
    kids[2].d.go(base + "/planet")
    kids[2].wait_for("return !document.querySelector('#app').hidden", 20, "lounge reload")
    kids[2].wait_for("return !document.querySelector('#loungeButton').hidden", 8, "Lounge button after reload")
    kids[2].open_room("#loungeButton", "#lounge")
    kids[2].lounge_wait_rovers(4)
    kids[2].check(True, "a reload comes back into the lounge")
    kids[2].logs("lounge reload")
    kids[3].close_room("#loungeClose", "#lounge")
    time.sleep(6)
    kids[0].lounge_wait_rovers(3)
    kids[0].check(True, "a rover that leaves is gone from the room")
    kids[3].open_room("#loungeButton", "#lounge")
    kids[3].lounge_wait_rovers(4)

    teacher.switch("lounge", False)
    for kid in kids:
        try:
            kid.wait_for("return document.querySelector('#lounge').hidden && document.querySelector('#loungeButton').hidden",
                         4, "lounge closed")
            kid.check(True, "closing the lounge sends the kid back to their level")
            kid.check("closed" in kid.toast_text(), "a toast explains the lounge closed", kid.toast_text()[:200])
        except CheckFailed as exc:
            kid.fail(str(exc))
        kid.logs("lounge closed")
        kid.shot("lounge-closed")
    show.wait_no_room()
    return True


def predict_scenario(base, shots, kids, teacher, show, failures):
    print("\n=== 🔮 Predict it: a question, then another one ===")
    code0, options0 = planet_predict.QUESTIONS[0]
    code1, options1 = planet_predict.QUESTIONS[1]
    teacher.pick_predict(0)
    for kid in kids:
        try:
            kid.wait_for("return !document.querySelector('#predict').hidden", 8, "predict card")
            p = kid.predict()
            kid.check(p["code"] == code0.strip(), "the question's code is on the card", p["code"])
            kid.check(p["options"] == [str(x) for x in options0], "four answers are on offer", str(p["options"]))
            kid.layout(".predict-card", "#predict")
            kid.shot("predict")
        except CheckFailed as exc:
            kid.fail(str(exc))
    show.wait_room("/planet/predict")
    check_show_frame(show)
    show.shot("predict")
    print("-- the teacher picks another question while the cards are open")
    teacher.pick_predict(1)
    for kid in kids:
        kid.wait_for("return document.querySelector('#predictCode').textContent===arguments[0]"
                     " && !document.querySelector('#predict').hidden", 8, "new question code", code1.strip())
        kid.check(kid.predict()["options"] == [str(x) for x in options1],
                  "the new answers replace the old ones", str(kid.predict()["options"]))
        kid.check(kid.predict()["code"] == code1.strip(), "the new code replaces the old one")
        kid.shot("predict-new")
    print("-- four different votes")
    for kid, choice in zip(kids, options1):
        kid.predict_vote(choice)
    for kid, choice in zip(kids, options1):
        p = kid.predict()
        kid.check(f"You said {choice}" in p["say"], "the page remembers its answer", p["say"])
    end = time.time() + 5
    class_view = get(base + "/planet/predict/view")
    while class_view["voted"] != 4 and time.time() < end:
        time.sleep(.15)
        class_view = get(base + "/planet/predict/view")
    kids[0].check(class_view["voted"] == 4, "the class screen counts four votes", str(class_view["voted"]))
    kids[0].check("Ada" not in json.dumps(class_view) and "Late" not in json.dumps(class_view),
                  "no names go to the class screen")
    show.shot("predict-votes")
    print("-- reveal")
    teacher.reveal()
    for kid in kids:
        kid.wait_for("return document.querySelector('#predictSay').textContent.includes('It was')", 8,
                     "the answer")
        p = kid.predict()
        kid.check(bool(p["right"]), "the right answer lights up", str(p["right"]))
        kid.logs("predict reveal")
        kid.shot("predict-reveal")
    show.wait_for("""const d=document.querySelector('#room').contentDocument;
      return d && d.querySelector('#ask') && d.querySelector('#ask').textContent.includes('squares')""",
                  10, "the class-screen rover drive")
    time.sleep(.3)
    show.shot("predict-reveal")
    print("-- a reload keeps the answer")
    choice = options1[0]
    kids[0].d.go(base + "/planet")
    kids[0].wait_for("return !document.querySelector('#app').hidden", 20, "predict reload")
    kids[0].wait_for("return !document.querySelector('#predict').hidden", 8, "predict card after reload")
    time.sleep(.5)
    p = kids[0].predict()
    kids[0].check(str(choice) in p["mine"], "the reloaded page marks the answer they gave", str(p["mine"]))
    kids[0].check(f"you said {choice}" in p["say"].lower(), "the reloaded page says what they said", p["say"])
    kids[0].logs("predict reload")
    teacher.pick_predict(None)
    for kid in kids:
        kid.wait_for("return document.querySelector('#predict').hidden", 8, "predict closed")
        kid.check(True, "closing the question clears the card")
        kid.logs("predict closed")
    show.wait_no_room()
    return True


def race_scenario(base, shots, kids, teacher, show, failures):
    print("\n=== 🏁 Class race: four winners at once ===")
    post(base + "/admin", {"key": teacher.key, "action": "planet_challenge", "site": "1a"})
    code = planet.find_site("1a")[2]["reference"]
    for kid in kids:
        kid.js("openSite('1a'); return true")
        kid.wait_for("return site && site.key==='1a'", 15, "the challenge level")
        kid.js("const t=document.querySelector('#code'); t.value=arguments[0];"
               "t.dispatchEvent(new Event('input',{bubbles:true}));", code)
        kid.d.click("#runButton")
    end = time.time() + 30
    lineup = None
    while time.time() < end:
        lineup = get(base + "/planet/race/lineup")
        if len(lineup.get("racers", [])) == len(kids):
            break
        time.sleep(.3)
    kids[0].check(len(lineup.get("racers", [])) == len(kids),
                  "four winners join the race", str([r["name"] for r in lineup.get("racers", [])]))
    for kid in kids:
        kid.logs("race win")
    teacher.race_board(True)
    show.wait_room("/planet/race")
    check_show_frame(show)
    show.shot("race")
    race = Page(base, shots, "race", 1920, 1080)
    try:
        race.d.go(base + "/planet/race")
        race.wait_for("return document.querySelectorAll('.tile').length===4", 10, "four race tiles")
        race.check("4 rovers ready" in race.text("#about"), "the race page sees the class",
                   race.text("#about"))
        race.check(not race.js("return document.querySelector('#go').disabled"),
                   "Start the race is ready")
        race.layout(".race", ".race")
        race.shot("race-ready")
        race.d.click("#go")
        time.sleep(.7)
        race.check(race.text("#count") in ("3", "2", "1", "GO!"),
                   "the countdown is short and visible", race.text("#count"))
        race.shot("race-count")
        race.wait_for("return race.state==='finished'", 25, "the race finishes")
        race.check(race.js("return race.state==='finished'"), "every racer finishes")
        awards = race.text("#awards")
        race.check("Fastest rover" in awards and "Shortest program" in awards,
                   "the race names a fastest and a shortest", awards[:300])
        race.shot("race-finished")
        race.d.click("#program")
        race.wait_for("return !document.querySelector('#codeBox').hidden", 5, "shortest program")
        race.check(race.text("#code").strip() == code.strip(), "the shortest program is the class's code")
        race.shot("race-program")
        race.d.click("#codeClose")
        try:
            race.d.request("POST", f"/session/{race.d.sid}/goog/cdp/execute",
                         {"cmd": "Emulation.setDeviceMetricsOverride",
                          "params": {"width": 1366, "height": 768,
                                     "deviceScaleFactor": 1, "mobile": False}})
            time.sleep(.5)
            race.check(race.js("return document.documentElement.scrollWidth<=innerWidth+1"),
                       "the race still fits a class laptop")
            race.shot("race-small")
        except Exception as exc:
            race.fail(f"could not resize the race page: {exc}")
        race.logs("race")
        # Esc on the class screen goes back to the expedition for now.
        show.press_escape()
        show.wait_for("return document.querySelector('#room').hidden", 5, "Esc goes back early")
        show.check(True, "Esc on the classroom board goes back to the expedition")
        time.sleep(1.5)
        show.check(show.js("return document.querySelector('#room').hidden"),
                   "the board stays on the expedition until the room changes")
    finally:
        race.close()
        failures.extend(race.failures)
    teacher.race_board(False)
    show.wait_no_room()
    return True


# --------------------------------------------------------------------------
def make_kid(base, shots, name, calm=False):
    player = post(base + "/join", {"name": name})
    return Kid(base, shots, name, player["id"], calm=calm)


def play(args):
    base = args.base.rstrip("/")
    shots = os.path.abspath(args.shots)
    os.makedirs(shots, exist_ok=True)
    proc, failures = None, []
    state_file = os.path.abspath(args.state_file)
    server_log = os.path.abspath(args.server_log)
    if args.start_server:
        if server_up(base):
            raise SystemExit(f"{base} is already serving; pick a free port for --start-server")
        if args.fresh and os.path.exists(state_file):
            if os.path.basename(state_file) == "scores.json":
                raise SystemExit("refusing to delete a scores.json")
            os.remove(state_file)
        proc = start_server(base, state_file, server_log)
    try:
        suffix = str(int(time.time() * 1000) % 100000)
        names = [f"Room Ada {suffix}", f"Room Bo {suffix}", f"Room Cy {suffix}", f"Room Dee {suffix}"]
        ids = [post(base + "/join", {"name": n})["id"] for n in names]
        key = state_admin_key(state_file, args.admin_key)
        if args.easy:
            post(base + "/admin", {"key": key, "action": "planet_easy", "on": True})
        # A known clean board, whatever the last run left open.
        for action, data in (("planet_lounge", {"on": False}),
                             ("planet_team", {"on": False}),
                             ("planet_predict", {"n": ""}),
                             ("planet_team_level", {"level": "hub"})):
            try:
                post(base + "/admin", dict(data, key=key, action=action))
            except Exception:
                pass
        # The race is a toggle, so only turn it off if it is really on.
        try:
            if get(base + "/planet/overview").get("race_on_board"):
                post(base + "/admin", {"key": key, "action": "planet_race_board"})
        except Exception:
            pass

        kids = []
        show = teacher = None
        try:
            kids = [Kid(base, shots, name, pid, calm=(i == 3))
                    for i, (name, pid) in enumerate(zip(names, ids))]
            teacher = Teacher(base, shots, key)
            show = Show(base, shots)
            for kid in kids:
                kid.check(not kid.js("return !document.querySelector('#teamButton').hidden"),
                          "Team Mission button starts hidden")
                kid.check(not kid.js("return !document.querySelector('#loungeButton').hidden"),
                          "Lounge button starts hidden")
            show.check(show.js("return document.querySelector('#room').hidden"),
                       "class screen starts on the expedition")
            team_scenario(base, shots, kids, teacher, show, failures)
            lounge_scenario(base, shots, kids, teacher, show, failures)
            predict_scenario(base, shots, kids, teacher, show, failures)
            race_scenario(base, shots, kids, teacher, show, failures)
            for kid in kids:
                kid.logs("end")
            teacher.logs("end")
            show.logs("end")
        finally:
            for page in kids + [teacher, show]:
                if page is not None:
                    try:
                        page.close()
                    except Exception:
                        pass
                    failures.extend(page.failures)
    finally:
        if proc is not None:
            proc.terminate()
            try:
                proc.wait(timeout=8)
            except subprocess.TimeoutExpired:
                proc.kill()
    return failures


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--base", default="http://127.0.0.1:8794")
    ap.add_argument("--start-server", action="store_true", help="run a test server on --base")
    ap.add_argument("--state-file", default="/tmp/planet-rooms-state.json")
    ap.add_argument("--server-log", default="/tmp/planet-rooms-server.log")
    ap.add_argument("--fresh", action="store_true", help="delete --state-file before starting (test state only)")
    ap.add_argument("--admin-key", default=os.environ.get("PLANET_ADMIN_KEY", "0106"))
    ap.add_argument("--shots", default="/tmp/planet-rooms-shots")
    ap.add_argument("--no-easy", dest="easy", action="store_false", default=True)
    args = ap.parse_args(argv)
    failures = play(args)
    if failures:
        print(f"\n{len(failures)} failure(s)")
        for item in failures:
            print(" -", item)
        return 1
    print("\nall room checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
