#!/usr/bin/env python3
"""Real-browser run of the two teacher Strange Planet screens.

Opens /planet/show and /planet/teacher in headless Chromium at 1366x768 and
1920x1080 while a class of six students joins over HTTP and runs a realistic
mix: one run, four at once, six at once, misses, code errors, a long program
full of print() lines, a farm day, an invisible name and a teacher message.
It checks for console errors, projector scrollbars, clipped/over-large boxes
and a replay queue that never drains, and saves screenshots you can look at.

This is a tool, not a test (no test_ prefix). It starts its own server on a
free port with a throwaway state file, so it never touches the class's scores.

    python3 tools/e2e_planet_show.py
    python3 tools/e2e_planet_show.py --base http://127.0.0.1:8792  # use a running server
    python3 tools/e2e_planet_show.py --shots /tmp/planet-shots

Exit code 0 means every check passed; 1 lists what did not.
"""
import argparse
import json
import os
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(HERE, "tools"))
import wd  # noqa: E402

ROW = 'for i in range(3):\n    harvest()\n    plant("berry")\n    east()\n'
P1 = "east()\neast()\neast()\n"
P2 = "south()\nsouth()\nsouth()\n"
P3 = "east()\neast()\neast()\nsouth()\nsouth()\nsouth()\n"
LONG = "".join(f'print("counting {i}")\n' for i in range(40)) + P1

PROBLEMS = []


def expect(ok, text):
    if ok:
        print("  ok  " + text)
    else:
        print("  !!  " + text)
        PROBLEMS.append(text)


def http(base, path, data=None, timeout=20):
    body = None if data is None else json.dumps(data).encode("utf-8")
    headers = {"Content-Type": "application/json"} if body is not None else {}
    req = urllib.request.Request(base + path, data=body, headers=headers)
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def free_port():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def admin_key():
    text = open(os.path.join(HERE, "server.py"), encoding="utf-8").read()
    found = re.search(r'^ADMIN_KEY\s*=\s*"([^"]+)"', text, re.M)
    return found.group(1) if found else "0106"


def start_server():
    folder = tempfile.mkdtemp(prefix="planet-show-e2e-")
    port = free_port()
    base = f"http://127.0.0.1:{port}"
    state = os.path.join(folder, "scores.json")
    log_path = os.path.join(folder, "server.log")
    log = open(log_path, "w", encoding="utf-8")
    env = dict(os.environ, MAZE_PORT=str(port), MAZE_STATE_FILE=state)
    proc = subprocess.Popen([sys.executable, "server.py"], cwd=HERE, env=env,
                            stdout=log, stderr=subprocess.STDOUT)
    for _ in range(120):
        if proc.poll() is not None:
            break
        try:
            http(base, "/planet/overview", timeout=1)
            return base, proc, folder, log
        except Exception:
            time.sleep(0.1)
    log.close()
    tail = open(log_path, encoding="utf-8", errors="replace").read()[-2000:]
    print(tail)
    proc.kill()
    shutil.rmtree(folder, ignore_errors=True)
    raise SystemExit("server did not start")


def stop_server(proc, log, folder):
    try:
        if log:
            log.close()
    except Exception:
        pass
    if proc and proc.poll() is None:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
    if folder:
        shutil.rmtree(folder, ignore_errors=True)


def poll(driver, script, timeout=20, interval=0.25):
    end = time.time() + timeout
    while time.time() < end:
        try:
            if driver.js(script):
                return True
        except Exception:
            pass
        time.sleep(interval)
    return False


def drain_errors(driver):
    bad = []
    try:
        entries = driver.logs()
    except Exception:
        return bad
    for entry in entries:
        message = entry.get("message", "")
        level = entry.get("level", "")
        # Chrome's harmless warning about the admin-key password box.
        if "Password field is not contained in a form" in message:
            continue
        if level in ("SEVERE", "ERROR") or "Uncaught" in message \
                or "TypeError" in message or "ReferenceError" in message:
            bad.append(f"{level}: {message[:300]}")
    return bad


def describe_show(driver):
    return driver.js("""return {
      iw: innerWidth, ih: innerHeight,
      sw: document.documentElement.scrollWidth,
      sh: document.documentElement.scrollHeight,
      stage: (() => { const r = document.getElementById("stage").getBoundingClientRect();
                     return [r.left, r.top, r.right, r.bottom]; })(),
      ships: (() => { const r = document.getElementById("ships").getBoundingClientRect();
                     return [r.left, r.top, r.right, r.bottom]; })(),
      splash: !document.getElementById("splash").hidden,
      name: document.getElementById("name").textContent,
      label: document.getElementById("labelText").textContent,
      file: document.getElementById("file").textContent,
      lines: document.getElementById("lines").textContent,
      queue: stage.queue.length,
      done: stage.done,
      farming: farmShow.on,
    }""") or {}


def check_show_layout(driver, label):
    info = describe_show(driver)
    expect(info["sw"] <= info["iw"] + 1,
           f"{label}: projector has no sideways scrollbar "
           f"({info['sw']} <= {info['iw']})")
    expect(info["sh"] <= info["ih"] + 1,
           f"{label}: projector has no page scrollbar "
           f"({info['sh']} <= {info['ih']})")
    for key in ("stage", "ships"):
        left, top, right, bottom = info.get(key) or (0, 0, 0, 0)
        expect(left >= -1 and top >= -1 and right <= info["iw"] + 1 and bottom <= info["ih"] + 1,
               f"{label}: {key} fits on the projector")
    return info


def check_teacher_layout(driver, label):
    info = driver.js("""return {
      iw: innerWidth, ih: innerHeight,
      sw: document.documentElement.scrollWidth,
      cards: document.querySelectorAll("#crew .card").length,
      names: [...document.querySelectorAll("#crew .card .card-top b")].map(b => b.textContent),
    }""") or {}
    expect(info.get("sw", 0) <= info.get("iw", 0) + 1,
           f"{label}: teacher page has no sideways scrollbar")
    return info


def click_text(driver, css, text):
    return driver.js("""const want = arguments[0], text = arguments[1];
      const b = [...document.querySelectorAll(want)].find(x => x.textContent.includes(text));
      if (b) { b.click(); return true; } return false;""", css, text)


def sleep(seconds):
    time.sleep(seconds)


def wait_batch(driver, before, timeout=45):
    """Wait until new runs have taken the stage and drained, not merely for a
    stage that was already quiet when the runs were posted."""
    end = time.time() + timeout
    started, seen = False, set()
    while time.time() < end:
        state = driver.js("""return {name: document.getElementById("name").textContent,
          queue: stage.queue.length, done: stage.done}""") or {}
        seen.add(state.get("name"))
        if state.get("queue", 0) > 0 or state.get("name") != before:
            started = True
        if started and state.get("queue") == 0 and state.get("done"):
            return True, seen
        sleep(0.3)
    return False, seen


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", help="use this already-running server, e.g. http://127.0.0.1:8792")
    parser.add_argument("--shots", help="folder for screenshots (default: a new temp folder)")
    parser.add_argument("--keep", action="store_true", help="keep the server after the run")
    args = parser.parse_args()

    shots = args.shots or tempfile.mkdtemp(prefix="planet-show-e2e-shots-")
    os.makedirs(shots, exist_ok=True)
    print("screenshots:", shots)

    base, proc, folder, log = (None, None, None, None)
    if args.base:
        base = args.base.rstrip("/")
    else:
        base, proc, folder, log = start_server()
    print("server:", base)
    key = admin_key()

    drivers = []
    show = teach = None

    def add(name, width, height, path):
        driver = wd.new(width, height)
        drivers.append((name, driver))
        driver.go(base + path)
        return driver

    def drain(label):
        for name, driver in drivers:
            for message in drain_errors(driver):
                PROBLEMS.append(f"{label} [{name}] console: {message}")

    def shot(driver, name):
        path = os.path.join(shots, name)
        driver.shot(path)
        print("  shot", path)

    def admin(action, **extra):
        return http(base, "/admin", dict(extra, key=key, action=action))

    def run(pid, site, code):
        return http(base, "/planet/run", {"id": pid, "site": site, "code": code})

    try:
        # -- the class ----------------------------------------------------------
        specs = [
            ("Ada", "Ada"),
            ("Bo", "Bo"),
            ("Chloe", "Chloe"),
            ("Max", "Maximilian Alexander Fitzgerald-Longbottom"),
            ("Rocket", "🌮 Rocket"),
            ("Invisible", "\u200b\u200c\u200d\ufeff\ufe0f"),
        ]
        students = {}
        for label, name in specs:
            students[label] = http(base, "/join", {"name": name})
        expect(students["Invisible"]["name"].strip() != "",
               "a name made of invisible marks becomes a name the class can see")
        expect(students["Max"]["name"] == "Maximilian Alexander",
               "a very long name is shortened to fit the cards")
        expect(students["Rocket"]["name"] == "🌮 Rocket", "an emoji name is kept")
        expect(admin("planet_easy", on=True).get("ok"), "easy mode on")
        expect(admin("planet_farm", on=True).get("ok"), "Rover Farm on")

        def ping():
            for student in students.values():
                http(base, f"/planet/ping?id={student['id']}&busy=0")

        ping()
        ids = {name: row["id"] for name, row in students.items()}
        expect(len({row["id"] for row in students.values()}) == 6,
               "six students joined with different ids")

        # -- 1366x768: the projector and Mission Control ------------------------
        show = add("show-1366", 1366, 768, "/planet/show")
        teach = add("teacher-1366", 1366, 768, "/planet/teacher")
        # The page's buttons need the admin key, as the teacher would type it.
        teach.js('document.getElementById("key").value = arguments[0];'
                 'localStorage.setItem("planetKey", arguments[0]); return 1', key)
        expect(poll(show, 'return document.querySelectorAll("#ships .ship").length === 6', 15),
               "projector crew shows all six")
        expect(poll(teach, 'return document.querySelectorAll("#crew .card").length === 6', 15),
               "teacher page has all six cards")
        show_info = check_show_layout(show, "show 1366 initial")
        expect(show_info.get("splash"), "projector starts with the Ready for launch card")
        teach_info = check_teacher_layout(teach, "teacher 1366 initial")
        expect(all(n.strip() for n in teach_info.get("names", [])),
               "no blank student name on the teacher cards")
        shot(show, "show-initial-1366.png")
        shot(teach, "teacher-initial-1366.png")
        drain("initial 1366")

        # One run: a win.
        run(ids["Ada"], "p1", P1)
        expect(poll(show, 'return document.getElementById("name").textContent === "Ada"', 15),
               "one run replays with the student's name")
        expect(poll(show, 'return /Ada/.test(document.getElementById("labelText").textContent)', 10),
               "the finished run says Ada's run")
        shot(show, "show-one-run-1366.png")
        drain("one run")

        # Four students at once: a win, a miss, a code error and another win.
        before = show.js('return document.getElementById("name").textContent')
        for label, site, code in (
                ("Bo", "p1", "east()\n"),
                ("Chloe", "p1", "fly()\n"),
                ("Max", "p2", P2),
                ("Rocket", "p1", P1)):
            run(ids[label], site, code)
        took_shot = False
        end = time.time() + 45
        seen = set()
        while time.time() < end:
            state = show.js("""return {name: document.getElementById("name").textContent,
              queue: stage.queue.length, done: stage.done}""") or {}
            seen.add(state.get("name"))
            if len(seen) >= 3 and not took_shot:
                shot(show, "show-four-1366.png")
                took_shot = True
            started = state.get("queue", 0) > 0 or state.get("name") != before
            if started and state.get("queue") == 0 and state.get("done"):
                break
            sleep(0.3)
        expect({"Bo", "Chloe", "Maximilian Alexander", "🌮 Rocket"} <= seen,
               f"four runs at once each reach the stage (saw {sorted(seen)})")
        expect(show.js("return stage.queue.length") == 0, "the four-run queue drains")
        if not took_shot:
            shot(show, "show-four-1366.png")
        drain("four at once")

        # Six at once, including the emoji and invisible names.
        before = show.js('return document.getElementById("name").textContent')
        for label, site, code in (
                ("Ada", "p1", P1),
                ("Bo", "p1", "east()\neast()\n"),
                ("Chloe", "p1", P1),
                ("Max", "p2", P2),
                ("Rocket", "p3", P3),
                ("Invisible", "p1", P1)):
            run(ids[label], site, code)
        drained, _ = wait_batch(show, before)
        expect(drained, "the six-at-once replay queue drains")
        shot(show, "show-six-1366.png")
        drain("six at once")

        # Long code with lots of prints: the teacher's stage must not grow huge.
        expect(poll(show, "return stage.queue.length === 0", 10), "stage is quiet before long code")
        run(ids["Rocket"], "p1", LONG)
        expect(poll(show, 'return document.getElementById("lines").textContent === "43 lines"', 20),
               "the projector counts all 43 lines")
        check_show_layout(show, "show 1366 long code")
        shot(show, "show-long-1366.png")
        expect(poll(teach, 'return document.getElementById("stageCode").textContent'
                          '.includes("counting 39")', 20),
               "the teacher stage picks up the long program")
        measured = teach.js("""return {
          stage: document.querySelector(".stage").getBoundingClientRect().height,
          screen: document.getElementById("screen").getBoundingClientRect().height,
          code: document.getElementById("stageCode").clientHeight,
          codeScroll: document.getElementById("stageCode").scrollHeight,
        }""")
        expect(measured["stage"] < 760,
               f"long code does not stretch the teacher stage (height {measured['stage']:.0f}px)")
        expect(measured["code"] <= 340,
               f"long code scrolls inside its own box ({measured['code']:.0f}px)")
        expect(measured["codeScroll"] > measured["code"], "the long code really is scrollable")
        shot(teach, "teacher-long-1366.png")
        drain("long code")

        # A farm day while nothing else is running.
        expect(poll(show, "return stage.queue.length === 0", 10), "stage is quiet before the farm")
        http(base, "/planet/farm/run", {"id": ids["Ada"], "code": ROW})
        expect(poll(show, 'return /Farming now/.test(document.getElementById("labelText").textContent)', 12),
               "a farm day plays when no level run is happening")
        expect(show.js('return !document.getElementById("farmYard").hidden'), "the farm yard is on screen")
        shot(show, "show-farm-1366.png")
        expect(poll(show, 'return /farm day/.test(document.getElementById("labelText").textContent)', 15),
               "the farm day finishes with its coins")
        shot(show, "show-farm-done-1366.png")
        drain("farm day")

        # Turning the farm off drops a queued farm day and stops one playing.
        http(base, "/planet/farm/run", {"id": ids["Ada"], "code": ROW})
        run(ids["Bo"], "p1", P1)
        sleep(0.4)
        admin("planet_farm", on=False)
        stopped = poll(show, "return !farmShow.on && !farmShow.pending", 12)
        expect(stopped, "switching the farm off stops the farm day and drops any queued one")
        shot(show, "show-farm-off-1366.png")
        admin("planet_farm", on=True)
        drain("farm off")

        # -- the teacher page's own controls ------------------------------------
        teach.click("#settingsButton")
        expect(poll(teach, 'return !document.getElementById("settings").hidden', 5),
               "the Settings panel opens")
        expect(teach.js('return document.getElementById("settings").scrollWidth'
                        ' <= document.getElementById("settings").clientWidth + 1'),
               "the Settings panel does not overflow sideways")
        shot(teach, "teacher-settings-1366.png")
        # Let the page catch up with the farm-on we set through the admin
        # endpoint before flipping the switch through the page.
        expect(poll(teach, 'return document.getElementById("farm").checked === true', 8),
               "the Settings switch shows the farm on before we flip it")
        # The farm switch through the page, not only the admin endpoint.
        teach.js('document.getElementById("farm").click(); return 1')
        expect(poll(teach, 'return document.getElementById("farm").checked === false', 8),
               "the farm switch turns off in Settings")
        teach.js('document.getElementById("farm").click(); return 1')
        expect(poll(teach, 'return document.getElementById("farm").checked === true', 8),
               "the farm switch turns back on in Settings")
        teach.click("#settingsButton")

        # Eyes up, then the 5-minute countdown.
        expect(click_text(teach, ".top-actions .btn", "Eyes up"), "the Eyes up button is there")
        expect(poll(show, 'return !document.getElementById("notice").hidden &&'
                          ' /Eyes/.test(document.getElementById("noticeTitle").textContent)', 10),
               "Eyes up fills the projector")
        shot(show, "show-eyes-1366.png")
        show.js('clearTimeout(window.noticeTimer); document.getElementById("notice").hidden = true; return 1')
        expect(click_text(teach, ".top-actions .btn", "5 minutes"), "the 5 minutes button is there")
        expect(poll(show, 'return !document.getElementById("clock").hidden', 10),
               "5 minutes leaves a countdown on the projector")
        shot(show, "show-five-1366.png")
        drain("messages")

        # Spin: lands on a visible name, then gets out of the way by itself.
        expect(click_text(teach, ".top-actions .btn", "Spin"), "the Spin button is there")
        expect(poll(show, 'return !document.getElementById("spin").hidden', 8), "Spin takes the board")
        expect(poll(show, 'return document.getElementById("spinName").textContent.trim() !== ""', 10),
               "Spin lands on a student whose name shows")
        shot(show, "show-spin-1366.png")
        expect(poll(show, 'return document.getElementById("spin").hidden', 18),
               "the spinner leaves the board by itself")
        drain("spin")

        # Show code and Replay on a student card.
        expect(click_text(teach, ".card .btn", "Show code"), "a card has a Show code button")
        expect(poll(show, 'return !document.getElementById("spot").hidden', 10),
               "Show code puts the class code on the projector")
        shot(show, "show-spotlight-1366.png")
        expect(click_text(teach, ".top-actions .btn", "Stop showing code"),
               "the Stop showing code button is there")
        expect(poll(show, 'return document.getElementById("spot").hidden', 10),
               "Stop showing code brings the fleet back")
        expect(click_text(teach, ".card .btn", "Replay"), "a card has a Replay button")
        expect(poll(teach, 'return document.getElementById("stageName").textContent.trim() !== ""', 10),
               "Replay brings a run back to the teacher stage")
        shot(teach, "teacher-replay-1366.png")
        drain("show code and replay")

        # Find a name, sort, and open both after-class tables.
        teach.js("""const q = document.getElementById("search"); q.value = "rocket";
                    q.dispatchEvent(new Event("input")); return 1""")
        sleep(0.4)
        expect(teach.js('return document.querySelectorAll("#crew .card").length === 1'),
               "Find a name narrows the crew")
        teach.js("""const q = document.getElementById("search"); q.value = "";
                    q.dispatchEvent(new Event("input"));
                    document.querySelector("#sort button[data-sort=name]").click();
                    return 1""")
        sleep(0.4)
        teach.js('document.getElementById("todayBox").open = true; return 1')
        expect(poll(teach, 'return document.querySelectorAll("#today tr").length >= 6', 10),
               "Today's class table lists everyone")
        teach.js('document.getElementById("todayBox").scrollIntoView({block: "start"}); return 1')
        sleep(0.3)
        shot(teach, "teacher-today-1366.png")
        teach.js('document.getElementById("reportBox").open = true; return 1')
        expect(poll(teach, 'return document.querySelectorAll("#report tr").length > 0', 10),
               "Level by level table opens")
        teach.js('document.getElementById("reportBox").scrollIntoView({block: "start"}); return 1')
        sleep(0.3)
        shot(teach, "teacher-report-1366.png")
        drain("tables")

        # -- 1920x1080: both screens again, with four runs while they're open ---
        ping()
        show2 = add("show-1920", 1920, 1080, "/planet/show")
        teach2 = add("teacher-1920", 1920, 1080, "/planet/teacher")
        expect(poll(show2, 'return document.querySelectorAll("#ships .ship").length === 6', 15),
               "the 1920 projector shows the crew")
        check_show_layout(show2, "show 1920 initial")
        shot(show2, "show-initial-1920.png")
        check_teacher_layout(teach2, "teacher 1920 initial")
        expect(poll(teach2, 'return document.querySelectorAll("#crew .card").length === 6', 15),
               "the 1920 teacher page has all six cards")
        shot(teach2, "teacher-initial-1920.png")
        before = show2.js('return document.getElementById("name").textContent')
        for label, site, code in (
                ("Ada", "p6", "north(3)\nwest(4)\n"),
                ("Bo", "p1", "east()\n"),
                ("Chloe", "p2", P2),
                ("Max", "p3", P3)):
            run(ids[label], site, code)
        drained, _ = wait_batch(show2, before, 50)
        expect(drained, "the 1920 projector gets through four runs at once")
        check_show_layout(show2, "show 1920 after runs")
        shot(show2, "show-four-1920.png")
        measured2 = teach2.js('return document.querySelector(".stage").getBoundingClientRect().height')
        expect(measured2 < 900, f"the 1920 teacher stage stays a sensible height ({measured2:.0f}px)")
        shot(teach2, "teacher-four-1920.png")
        drain("1920")

        # A long program at 1920 too, to prove the code box scrolls there.
        run(ids["Rocket"], "p1", LONG)
        expect(poll(teach2, 'return document.getElementById("stageCode").textContent'
                           '.includes("counting 39")', 20),
               "the 1920 teacher stage shows the long program")
        measured2 = teach2.js("""return {stage: document.querySelector(".stage").getBoundingClientRect().height,
          code: document.getElementById("stageCode").clientHeight}""")
        expect(measured2["stage"] < 900,
               f"long code does not stretch the 1920 teacher stage (height {measured2['stage']:.0f}px)")
        expect(measured2["code"] <= 340,
               f"long code scrolls at 1920 too ({measured2['code']:.0f}px)")
        shot(teach2, "teacher-long-1920.png")
        drain("1920 long code")

        # -- stop notices last: they are meant to stay up for the class ---------
        expect(click_text(teach, ".top-actions .btn", "👋 Stop"), "the Stop button is there")
        expect(poll(show, 'return !document.getElementById("notice").hidden &&'
                          ' /stop/i.test(document.getElementById("noticeTitle").textContent)', 10),
               "Stop shows the day's numbers on the projector")
        shot(show, "show-stop-1366.png")
        drain("stop message")
    finally:
        for _, driver in drivers:
            try:
                driver.close()
            except Exception:
                pass
        if not args.keep:
            stop_server(proc, log, folder)
        else:
            print("server kept at", base)

    print("\n=== RESULT ===")
    if PROBLEMS:
        print(f"{len(PROBLEMS)} problem(s):")
        for problem in PROBLEMS:
            print(" -", problem)
        raise SystemExit(1)
    print("Every check passed.")
    print("Screenshots:", shots)


if __name__ == "__main__":
    main()
