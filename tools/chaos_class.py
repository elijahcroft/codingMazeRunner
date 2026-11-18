#!/usr/bin/env python3
"""A whole-class stress test for Pixel Pals, with no browser.

It starts its own server (or uses one already running), joins 25 students through
the same HTTP routes the page uses, and for about ten minutes mixes realistic
kid traffic: walking, saying, doing, every game (including the 👗 Fashion show),
weddings (including someone leaving mid-ceremony), the class mural (including
the 3-a-second rate limit), homes (buy, place, paint, size, flip, wish, visit),
chests, gems and Code race runs.  One projector and one teacher poll at the same
time, just like the big screen and the teacher's laptop.

While it runs it watches for server tracebacks, 5xx replies, requests slower
than a second, CPU and RSS (from /proc, sampled every 10 s), and state-file
growth.  Near the end it restarts the server on the same state file and checks
that the class is still there.

    python3 tools/chaos_class.py --port 8907 --state /tmp/classtest-state.json \\
        --server-log /tmp/classtest/server.log --duration 600 \\
        --json-out /tmp/classtest/chaos.json

It is stdlib only and needs no Chromium.  It is a tool, not a unittest: it is
not named test_*.py and unittest will not pick it up.
"""

import argparse
import json
import os
import random
import signal
import subprocess
import sys
import threading
import time
import traceback
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import pixel  # noqa: E402
import server as server_module  # noqa: E402  (only for ADMIN_KEY and a couple of constants)

ADMIN_KEY = server_module.ADMIN_KEY
GAME_KINDS = list(server_module.GAME_KINDS)
MURAL_CELLS = server_module.MURAL_CELLS
HANG_FINDS = list(pixel.HANG_FINDS)
PLACES = list(pixel.HANG_PLACES)
THING_CODE = 'def on_click():\n    say("Hello!")\n    jump()\n    hearts()\n'
PAL = {"key": "chaospal", "size": 16, "speed": 6, "palette": pixel.PIP["palette"],
       "frames": pixel.PIP["frames"], "names": pixel.PIP["names"], "title": "Class pal"}


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------
class Report:
    def __init__(self):
        self.lock = threading.Lock()
        self.checks = []
        self.notes = []
        self.action_errors = Counter()
        self.action_error_examples = {}
        self.counts = Counter()
        self.request_count = 0
        self.status_counts = Counter()
        self.server_errors = []
        self.net_errors = []
        self.slow = []
        self.poll_times = []
        self.worker_errors = []
        self.tracebacks = []
        self.samples = []
        self.restarts = []
        self.started = time.time()
        self.peak_threads = 0

    def check(self, label, ok, detail=""):
        with self.lock:
            self.checks.append({"check": label, "ok": bool(ok), "detail": str(detail)[:1200]})
        return bool(ok)

    def note(self, text):
        with self.lock:
            self.notes.append(str(text)[:1200])

    def count(self, key, n=1):
        with self.lock:
            self.counts[key] += n

    def action_error(self, action, out):
        if not isinstance(out, dict) or not out.get("error"):
            return
        err = str(out["error"])
        key = f"{action}: {err}"
        with self.lock:
            self.action_errors[key] += 1
            self.action_error_examples.setdefault(key, str(action)[:300])

    def problem(self, where, detail):
        with self.lock:
            self.worker_errors.append({"where": where, "detail": str(detail)[:900]})

    def summary(self):
        with self.lock:
            return {
                "seconds": round(time.time() - self.started, 1),
                "requests": self.request_count,
                "status_counts": dict(self.status_counts),
                "server_errors": self.server_errors[-20:],
                "server_error_count": len(self.server_errors),
                "net_error_count": len(self.net_errors),
                "net_errors": self.net_errors[-10:],
                "slow_over_1s": self.slow[-30:],
                "slow_count": len(self.slow),
                "worker_errors": self.worker_errors[-10:],
                "worker_error_count": len(self.worker_errors),
                "tracebacks": self.tracebacks[-10:],
                "traceback_count": len(self.tracebacks),
                "action_errors": dict(self.action_errors.most_common(20)),
                "action_error_examples": self.action_error_examples,
                "counts": dict(self.counts),
                "checks": self.checks,
                "notes": self.notes,
                "samples": self.samples,
                "restarts": self.restarts,
            }


REPORT = Report()


# ---------------------------------------------------------------------------
# HTTP client, with timing and the incident counters
# ---------------------------------------------------------------------------
class Ctx:
    def __init__(self, base, port, state_file, server_log, serve, keep_server):
        self.base = base
        self.port = port
        self.state_file = state_file
        self.server_log = server_log
        self.serve = serve
        self.keep_server = keep_server
        self.proc = None
        self.log_file = None
        self.log_lock = threading.Lock()
        self.restarting = threading.Event()
        self.busy = set()
        self.busy_lock = threading.Lock()
        self.stop = threading.Event()
        self.kids = []
        self.latencies = []

    # -- server --------------------------------------------------------------
    def start_server(self):
        env = os.environ.copy()
        env["MAZE_PORT"] = str(self.port)
        env["MAZE_STATE_FILE"] = self.state_file
        self.log_file = open(self.server_log, "ab", buffering=0)
        self.log_file.write(f"\n=== chaos_class starts server at {time.strftime('%H:%M:%S')} ===\n".encode())
        self.proc = subprocess.Popen([sys.executable, "server.py"], cwd=ROOT, env=env,
                                     stdout=self.log_file, stderr=subprocess.STDOUT,
                                     start_new_session=True)
        end = time.time() + 30
        while time.time() < end:
            if self.proc.poll() is not None:
                return False
            try:
                with urllib.request.urlopen(self.base + "/pixel/overview", timeout=2) as f:
                    json.loads(f.read().decode("utf-8", "replace"))
                return True
            except Exception:
                pass
            time.sleep(.2)
        return False

    def stop_server(self):
        proc = self.proc
        self.proc = None
        if not proc:
            return
        try:
            os.killpg(proc.pid, signal.SIGTERM)
        except OSError:
            pass
        try:
            proc.wait(timeout=8)
        except subprocess.TimeoutExpired:
            try:
                os.killpg(proc.pid, signal.SIGKILL)
            except OSError:
                pass
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                pass
        with self.log_lock:
            if self.log_file:
                try:
                    self.log_file.close()
                except OSError:
                    pass
                self.log_file = None

    def restart_server(self):
        """Restart on the same state file and check the class comes back."""
        REPORT.note("restarting the server on the same state file")
        self.restarting.set()
        time.sleep(1.2)                      # let a request that is already running finish
        # A teacher action writes the state file, so the check compares what was
        # actually saved rather than a few seconds of live-but-unsaved coins.
        self.teacher(action="open", level=pixel.LEVEL_ORDER[-1])
        before = self.snapshot_for_reload_check()
        size_before = os.path.getsize(self.state_file) if os.path.exists(self.state_file) else 0
        self.stop_server()
        time.sleep(1.0)
        ok = self.start_server()
        after = self.snapshot_for_reload_check() if ok else None
        same = bool(ok and before and after and
                    before["name"] == after["name"] and before["stars"] == after["stars"] and
                    before["drawings"] == after["drawings"] and
                    abs((before["coins"] or 0) - (after["coins"] or 0)) <= 200)
        size_after = os.path.getsize(self.state_file) if os.path.exists(self.state_file) else 0
        REPORT.restarts.append({"at": round(time.time() - REPORT.started, 1), "started": ok,
                              "state_bytes_before": size_before, "state_bytes_after": size_after,
                              "before": before, "after": after, "same": same})
        REPORT.check("the state file reloads after a restart", same,
                     {"started": ok, "before": before, "after": after})
        REPORT.note(f"restart: server_started={ok} state_same={same} bytes {size_before}->{size_after}")
        self.restarting.clear()
        return ok

    def snapshot_for_reload_check(self):
        if not self.kids:
            return None
        kid = self.kids[0]
        try:
            state = self.call("/pixel/state?" + urllib.parse.urlencode({"id": kid.pid}), None, timeout=8)
        except Exception:
            return None
        if not isinstance(state, dict) or state.get("__error__") or not state.get("you"):
            return None
        hang = state.get("hang") or {}
        return {"name": state["you"].get("name"), "stars": state.get("stars"),
                "coins": hang.get("coins"), "drawings": len(state.get("drawings") or [])}

    # -- requests ------------------------------------------------------------
    def call(self, path, payload=None, timeout=25, poll=False):
        url = self.base + path
        data = None
        headers = {}
        if payload is not None:
            data = json.dumps(payload).encode()
            headers["Content-Type"] = "application/json"
        req = urllib.request.Request(url, data=data, headers=headers)
        started = time.time()
        status = None
        body = None
        try:
            with urllib.request.urlopen(req, timeout=timeout) as f:
                status = f.status
                raw = f.read()
            try:
                body = json.loads(raw.decode("utf-8", "replace"))
            except Exception:
                body = {"__raw__": raw[:200].decode("utf-8", "replace")}
        except urllib.error.HTTPError as e:
            status = e.code
            raw = e.read()
            try:
                body = json.loads(raw.decode("utf-8", "replace"))
            except Exception:
                body = {"__raw__": raw[:300].decode("utf-8", "replace")}
        except Exception as e:
            elapsed = time.time() - started
            with REPORT.lock:
                REPORT.request_count += 1
                if not self.restarting.is_set():
                    REPORT.net_errors.append({"path": path, "error": f"{type(e).__name__}: {e}",
                                              "seconds": round(elapsed, 3)})
            return {"__error__": f"{type(e).__name__}: {e}"}
        elapsed = time.time() - started
        with REPORT.lock:
            REPORT.request_count += 1
            REPORT.status_counts[str(status)] += 1
            if status and status >= 500:
                REPORT.server_errors.append({"path": path, "status": status,
                                             "body": str(body)[:500], "seconds": round(elapsed, 3)})
            if poll:
                REPORT.poll_times.append(round(elapsed, 3))
                if len(REPORT.poll_times) > 500:
                    del REPORT.poll_times[:-500]
            elif elapsed > 1.0:
                REPORT.slow.append({"path": path, "seconds": round(elapsed, 3), "status": status})
                if len(REPORT.slow) > 300:
                    del REPORT.slow[:-300]
        return body

    # -- little helpers ------------------------------------------------------
    def room_do(self, pid, _action, **more):
        body = dict(id=pid, what=_action)
        body.update(more)
        out = self.call("/pixel/room/do", body)
        REPORT.action_error(_action, out)
        return out

    def student_state(self, pid, timeout=25):
        path = "/pixel/state?" + urllib.parse.urlencode({"id": pid})
        out = self.call(path, None, timeout=timeout)
        if isinstance(out, dict) and not out.get("__error__"):
            return out
        return {}

    def room_snapshot(self, pid=None, wait=False):
        q = {"after": "-1"}
        if pid:
            q["id"] = pid
        # A snapshot is cheap and does not hold; wait=True is the projector's held poll.
        return self.call("/pixel/room?" + urllib.parse.urlencode(q), None, timeout=30 if wait else 15)

    def teacher(self, **data):
        body = {"key": ADMIN_KEY}
        body.update(data)
        out = self.call("/pixel/teacher", body)
        REPORT.action_error("teacher:" + str(data.get("action")), out)
        return out

    def mark_busy(self, kids, on):
        with self.busy_lock:
            for kid in kids:
                if on:
                    self.busy.add(kid.pid)
                else:
                    self.busy.discard(kid.pid)


# ---------------------------------------------------------------------------
# A student and its background traffic
# ---------------------------------------------------------------------------
class Kid:
    def __init__(self, ctx, pid, name, index):
        self.ctx = ctx
        self.pid = pid
        self.name = name
        self.index = index
        self.view = None
        self.seq = -1
        self.state = {}
        self.last_state = 0
        self.rng = random.Random(f"{index}:{name}")
        self.thread = threading.Thread(target=self.run, name=f"kid-{index}", daemon=True)

    def log(self, msg):
        REPORT.problem("kid", f"{self.name}: {msg}")

    def refresh(self):
        path = "/pixel/room?" + urllib.parse.urlencode({"after": self.seq, "wait": "1", "id": self.pid})
        out = self.ctx.call(path, None, timeout=20, poll=True)
        if isinstance(out, dict) and not out.get("__error__") and ("you" in out or "open" in out):
            self.view = out
            self.seq = max(0, int(out.get("seq", self.seq) or 0))
        if time.time() - self.last_state > 9 or not self.state:
            st = self.ctx.student_state(self.pid, timeout=20)
            if st:
                self.state = st
                self.last_state = time.time()

    def run(self):
        while not self.ctx.stop.is_set():
            try:
                if self.ctx.restarting.is_set():
                    time.sleep(.3)
                    continue
                with self.ctx.busy_lock:
                    if self.pid in self.ctx.busy:
                        busy = True
                    else:
                        busy = False
                if busy:
                    time.sleep(.25)
                    continue
                self.refresh()
                with self.ctx.busy_lock:
                    busy = self.pid in self.ctx.busy
                if not busy:
                    self.act()
            except Exception as e:
                REPORT.problem("kid loop", f"{self.name}: {type(e).__name__}: {e}")
                time.sleep(.5)
            time.sleep(self.rng.uniform(.25, 1.2))

    # -- what a kid does -----------------------------------------------------
    def act(self):
        view = self.view or {}
        if not view or view.get("__error__"):
            return
        if view.get("you") is None:
            self.ctx.room_do(self.pid, "join")
            return
        seat = view.get("you")
        wedding = view.get("wedding")
        if wedding:
            if wedding.get("phase") == "invite" and wedding.get("partner") == seat:
                yes = self.rng.random() < .82
                self.ctx.room_do(self.pid, "wedding_yes" if yes else "wedding_no")
                REPORT.count("wedding_yes" if yes else "wedding_no")
                return
            if wedding.get("phase") in ("pick", "invite") and wedding.get("host") == seat and self.rng.random() < .08:
                self.ctx.room_do(self.pid, "wedding_cancel")
                return
        game = view.get("game")
        if game:
            joined = seat in (game.get("joined") or [])
            phase = game.get("phase")
            if phase == "lobby":
                if not joined and self.rng.random() < .45:
                    self.ctx.room_do(self.pid, "game", action="join")
                    REPORT.count("game_join")
                    return
                if joined and self.rng.random() < .05:
                    self.ctx.room_do(self.pid, "game", action="leave")
                    return
            if joined and phase in ("dressing", "runway"):
                self.act_fashion(game, seat)
                return
            if joined and phase in ("hiding", "playing"):
                if self.rng.random() < .015:
                    self.ctx.room_do(self.pid, "game", action="leave")
                    REPORT.count("game_leave")
                    return
                self.act_game(game, seat)
                return
            if not joined and game.get("kind") in ("code", "draw") and phase == "playing" and self.rng.random() < .25:
                self.ctx.room_do(self.pid, "game", action="join")
                return
        # A wedding, game or home scene is not blocking normal play, but if the
        # kid is at home, do home things.
        if view.get("loc") and view.get("home"):
            if self.rng.random() < .55:
                self.act_home(view)
            else:
                self.ctx.room_do(self.pid, "walk", x=self.rng.randint(16, 290), y=round(self.rng.uniform(.2, .9), 2))
            return
        self.act_outside(view)

    def act_fashion(self, game, seat):
        if game.get("phase") == "dressing":
            if self.rng.random() < .35:
                self.wear_something()
            if self.rng.random() < .4 and seat not in (game.get("dress_ready") or []):
                out = self.ctx.room_do(self.pid, "game", action="ready")
                REPORT.count("fashion_ready", 1 if isinstance(out, dict) and out.get("ok") else 0)
        else:
            if game.get("walker") != seat and self.rng.random() < .7:
                emoji = self.rng.choice(server_module.FASHION_REACTIONS)
                out = self.ctx.room_do(self.pid, "game", action="react", emoji=emoji)
                REPORT.count("fashion_react", 1 if isinstance(out, dict) and out.get("ok") else 0)

    def wear_something(self):
        hang = self.state.get("hang") or {}
        catalog = hang.get("catalog") or {}
        choices = []
        for key in hang.get("gifts") or []:
            item = catalog.get(key)
            if item and item.get("slot"):
                choices.append((item["slot"], key))
        for item in hang.get("mywear") or []:
            if isinstance(item, dict) and item.get("slot") and item.get("key"):
                choices.append((item["slot"], item["key"]))
        if not choices:
            return
        slot, item = self.rng.choice(choices)
        if self.rng.random() < .12:
            item = None
        out = self.ctx.room_do(self.pid, "wear", slot=slot, item=item)
        REPORT.count("wear", 1 if isinstance(out, dict) and out.get("ok") else 0)

    def act_game(self, game, seat):
        kind, phase = game.get("kind"), game.get("phase")
        if kind == "code":
            hint = (game.get("job") or {}).get("hint")
            if hint:
                out = self.ctx.room_do(self.pid, "game", action="run", code=hint)
                REPORT.count("code_race_run", 1 if isinstance(out, dict) and out.get("ok") else 0)
            return
        if kind == "draw":
            if game.get("drawer") == seat:
                word = game.get("word")
                for _ in range(self.rng.randint(1, 4)):
                    self.ctx.room_do(self.pid, "game", action="paint", cell=self.rng.randrange(pixel.DRAW_GRID ** 2),
                                     colour=self.rng.randrange(len(pixel.DRAW_COLOURS)))
                REPORT.count("draw_paint")
            else:
                choices = game.get("choices") or []
                if choices and self.rng.random() < .6:
                    pick = self.rng.choice(choices)
                    key = pick[0] if isinstance(pick, (list, tuple)) else pick
                    self.ctx.room_do(self.pid, "game", action="guess", word=key)
                    REPORT.count("draw_guess")
            return
        if kind == "dance":
            seq, step, ready = game.get("seq") or [], game.get("step") or 0, game.get("ready") or 0
            if time.time() >= ready and step < len(seq) and self.rng.random() < .7:
                out = self.ctx.room_do(self.pid, "game", action="step", name=seq[step])
                REPORT.count("dance_step", 1 if isinstance(out, dict) and out.get("ok") else 0)
            return
        if kind == "hide":
            if phase == "hiding":
                if seat != game.get("it"):
                    cover = self.rng.choice(self.view.get("cover") or [{"x": 100, "y": .5, "key": "oak"}])
                    self.ctx.room_do(self.pid, "walk", x=cover["x"], y=cover["y"])
                    out = self.ctx.room_do(self.pid, "game", action="hide", cover=cover["key"])
                    REPORT.count("hide", 1 if isinstance(out, dict) and out.get("ok") else 0)
            elif seat == game.get("it") and self.rng.random() < .25:
                cover = self.rng.choice(self.view.get("cover") or [{"key": "oak"}])
                self.ctx.room_do(self.pid, "game", action="search", cover=cover["key"])
                REPORT.count("search")
            return
        # tag, race, apples, ball: move about, but respect a red light in the race
        if kind == "race" and game.get("light") == "red":
            return
        if self.rng.random() < .7:
            x = self.rng.randint(30, 600)
            out = self.ctx.room_do(self.pid, "walk", x=x, y=round(self.rng.uniform(.15, .9), 2))
            REPORT.count("game_walk:" + str(kind))
        if kind in ("tag", "ball") and self.rng.random() < .1:
            self.ctx.room_do(self.pid, "move", name="cheer")

    def act_home(self, view):
        home = view.get("home") or {}
        mine = bool(home.get("mine"))
        if not mine:
            if self.rng.random() < .5:
                self.ctx.room_do(self.pid, "heart")
                REPORT.count("home_heart")
            else:
                self.ctx.room_do(self.pid, "home", out=True)
            return
        if self.rng.random() < .45:
            self.ctx.room_do(self.pid, "home", out=True)
            return
        items = home.get("items") or []
        if items and self.rng.random() < .5:
            piece = self.rng.choice(items).get("id")
            if piece:
                self.ctx.room_do(self.pid, "furnish", what="style", piece=piece,
                                 paint=self.rng.randrange(pixel.FURN_PAINTS),
                                 size=self.rng.randrange(pixel.FURN_SIZES),
                                 flip=self.rng.random() < .5)
                REPORT.count("home_style")
        else:
            hang = self.state.get("hang") or {}
            stuff = set(hang.get("stuff") or [])
            keys = [k for k, item in (hang.get("furniture") or {}).items()
                    if k in stuff or pixel.home_free(item)]
            if keys:
                key = self.rng.choice(keys)
                out = self.ctx.room_do(self.pid, "furnish", key=key, x=self.rng.randint(20, 280),
                                       y=round(self.rng.uniform(.3, .85), 2))
                REPORT.count("home_place", 1 if isinstance(out, dict) and out.get("ok") else 0)

    def act_outside(self, view):
        r = self.rng.random()
        place = self.rng.choice(PLACES)
        if r < .28:
            self.ctx.room_do(self.pid, "walk", x=self.rng.randint(16, 620), y=round(self.rng.uniform(.05, .95), 2))
            REPORT.count("walk")
        elif r < .43:
            what = self.rng.choice(["move", "feel", "fx", "rest", "say"])
            if what == "move":
                self.ctx.room_do(self.pid, "move", name=self.rng.choice(list(pixel.ROOM_MOVES)))
            elif what == "feel":
                self.ctx.room_do(self.pid, "feel", name=self.rng.choice(list(pixel.FEELINGS)))
            elif what == "fx":
                self.ctx.room_do(self.pid, "fx", name=self.rng.choice(list(pixel.ROOM_FX)))
            elif what == "rest":
                self.ctx.room_do(self.pid, "rest", name=self.rng.choice(list(pixel.ROOM_RESTS)))
            else:
                groups = list(pixel.ROOM_WORDS.values())
                word = self.rng.choice(self.rng.choice(groups)) if groups else ""
                if word:
                    self.ctx.room_do(self.pid, "say", text=word)
            REPORT.count("do")
        elif r < .53:
            self.ctx.room_do(self.pid, "go", name=place)
            REPORT.count("go")
        elif r < .62:
            cell = self.rng.randrange(MURAL_CELLS)
            out = self.ctx.room_do(self.pid, "mural", action="paint", cell=cell,
                                   ink=self.rng.randrange(len(server_module.MURAL_COLOURS)))
            if isinstance(out, dict) and out.get("error") == "wait":
                REPORT.count("mural_rate_limited")
            else:
                REPORT.count("mural_paint", 1 if isinstance(out, dict) and out.get("ok") else 0)
            if self.rng.random() < .25:
                self.ctx.room_do(self.pid, "mural", action="undo")
        elif r < .69:
            state = self.state or self.ctx.student_state(self.pid)
            self.state = state
            chests = ((state.get("hang") or {}).get("chests") or [])
            chest = self.rng.choice(chests) if chests else None
            if chest and not chest.get("open"):
                out = self.ctx.room_do(self.pid, "go", name=chest["place"])
                out = self.ctx.room_do(self.pid, "chest", place=chest["place"], code=chest.get("hint") or "")
                opened = isinstance(out, dict) and out.get("open")
                REPORT.count("chest_open", 1 if opened else 0)
        elif r < .75:
            gem = self.rng.choice(HANG_FINDS)
            self.ctx.room_do(self.pid, "go", name=gem[:-1])
            out = self.ctx.room_do(self.pid, "find", key=gem)
            REPORT.count("gem_find", 1 if isinstance(out, dict) and out.get("ok") else 0)
        elif r < .83:
            self.ctx.room_do(self.pid, "home")
            REPORT.count("home_enter")
        elif r < .89:
            state = self.state or self.ctx.student_state(self.pid)
            self.state = state
            hang = state.get("hang") or {}
            shop, coins = hang.get("shop") or {}, hang.get("coins") or 0
            gifts, stuff = set(hang.get("gifts") or []), set(hang.get("stuff") or [])
            affordable = [k for k, v in shop.items() if v.get("price", 99999) <= coins and
                          (v.get("kind") == "furniture" or k not in gifts | stuff)]
            if affordable:
                key = self.rng.choice(affordable)
                out = self.ctx.room_do(self.pid, "buy", key=key)
                REPORT.count("buy", 1 if isinstance(out, dict) and out.get("ok") else 0)
            if self.rng.random() < .4:
                wishes = [k for k, v in shop.items() if v.get("kind") == "furniture"] + [None]
                self.ctx.room_do(self.pid, "wish", key=self.rng.choice(wishes))
        elif r < .94:
            # a My Move or a Free show, if this student has one
            out = self.ctx.room_do(self.pid, "mymove")
            REPORT.count("mymove", 1 if isinstance(out, dict) and out.get("ok") else 0)
            if isinstance(out, dict) and "My Move first" in str(out.get("error", "")):
                self.ctx.room_do(self.pid, "perform")
        elif r < .97:
            # place a drawing, or take one back
            drawings = [d for d in (self.state.get("drawings") or []) if d.get("key")]
            if drawings:
                key = self.rng.choice(drawings)["key"]
                self.ctx.room_do(self.pid, "place", key=key, x=self.rng.randint(8, 620),
                                 y=round(self.rng.uniform(.1, .9), 2))
                REPORT.count("place")
        else:
            if view.get("loc"):
                self.ctx.room_do(self.pid, "toy", name=self.rng.choice(list(pixel.HOME_TOYS)),
                                 x=self.rng.randint(16, 290), y=round(self.rng.uniform(.2, .8), 2))
            else:
                self.ctx.room_do(self.pid, "move", name=self.rng.choice(list(pixel.ROOM_MOVES)))


# ---------------------------------------------------------------------------
# Scene helpers (the deliberate coverage part of the chaos)
# ---------------------------------------------------------------------------
def wait_until(fn, timeout=8, step=.2):
    end = time.time() + timeout
    while time.time() < end:
        try:
            if fn():
                return True
        except Exception:
            pass
        time.sleep(step)
    return False


def ensure_outside(ctx, kids, place="park"):
    for kid in kids:
        snap = ctx.room_snapshot(kid.pid)
        if isinstance(snap, dict) and snap.get("you") is None:
            ctx.room_do(kid.pid, "join")
        ctx.room_do(kid.pid, "go", name=place)


def fresh_state(ctx, kid):
    st = ctx.student_state(kid.pid)
    if st:
        kid.state = st
    return kid.state


def pick_wear(kid):
    hang = (kid.state.get("hang") or {}) if kid else {}
    catalog = hang.get("catalog") or {}
    for key in hang.get("gifts") or []:
        item = catalog.get(key)
        if item and item.get("slot"):
            return item["slot"], key
    for item in hang.get("mywear") or []:
        if isinstance(item, dict) and item.get("slot") and item.get("key"):
            return item["slot"], item["key"]
    return None


def quiet_room(ctx, kids):
    """Clear any leftover round or wedding so the next scene can start cleanly."""
    view = ctx.room_snapshot()
    if not isinstance(view, dict) or view.get("__error__"):
        return
    game = view.get("game")
    wedding = view.get("wedding")
    if game:
        ctx.teacher(action="end_game")
        wait_until(lambda: not ((ctx.room_snapshot() or {}).get("game")), 14, .5)
    if wedding:
        # Leaving cancels a wedding if it is one of the couple; try everyone,
        # then come back.
        everyone = ctx.kids or kids
        for kid in everyone:
            ctx.room_do(kid.pid, "leave")
        time.sleep(.4)
        for kid in everyone:
            ctx.room_do(kid.pid, "join")
        time.sleep(.3)


def kid_by_name(ctx, name):
    return next((k for k in ctx.kids if k.name == name), None)


def scene_fashion(ctx, kids):
    REPORT.note("scene: fashion show")
    quiet_room(ctx, kids)
    ensure_outside(ctx, kids)
    host = kids[0]
    out = ctx.room_do(host.pid, "game", action="create", kind="fashion")
    if not out.get("ok"):
        ctx.teacher(action="end_game")
        time.sleep(11)
        out = ctx.room_do(host.pid, "game", action="create", kind="fashion")
    REPORT.check("fashion: the host can start a show", bool(out.get("ok")), out)
    if not out.get("ok"):
        return False
    REPORT.count("scene_fashion")
    for kid in kids[1:]:
        fresh_state(ctx, kid)
        j = ctx.room_do(kid.pid, "game", action="join")
        REPORT.count("game_join", 1 if isinstance(j, dict) and j.get("ok") else 0)
        time.sleep(.15)
    start = ctx.room_do(host.pid, "game", action="start")
    REPORT.check("fashion: the show starts", bool(start.get("ok")), start)
    # Dress: put something on each kid, then all ready.
    for kid in kids:
        fresh_state(ctx, kid)
        choice = pick_wear(kid)
        if choice:
            slot, item = choice
            ctx.room_do(kid.pid, "wear", slot=slot, item=item)
            REPORT.count("scene_fashion_wear")
    time.sleep(.8)
    # Other children may have joined the lobby too. Ready every player in the
    # round, not only this scene's group, so a crowded show really starts.
    for attempt in range(30):
        view = ctx.room_snapshot(host.pid)
        game = (view or {}).get("game") or {}
        if game.get("phase") != "dressing":
            break
        seats = {p.get("name"): p for p in ((ctx.room_snapshot() or {}).get("people") or [])}
        for kid in kids:
            ctx.room_do(kid.pid, "game", action="ready")
        for seat in game.get("joined") or []:
            for name, person in seats.items():
                if person.get("seat") == seat:
                    other = kid_by_name(ctx, name)
                    if other and other.pid not in [k.pid for k in kids]:
                        ctx.room_do(other.pid, "game", action="ready")
        time.sleep(1.0)
    view = ctx.room_snapshot(host.pid)
    game = (view or {}).get("game") or {}
    REPORT.check("fashion: all ready starts the runway", game.get("phase") in ("runway", "results"), game)
    # Cheer every walker until the results.
    end = time.time() + 100
    seen_walk = False
    while time.time() < end:
        view = ctx.room_snapshot(host.pid)
        game = (view or {}).get("game") or {}
        if game.get("phase") == "results":
            break
        if game.get("phase") == "runway" and game.get("walker"):
            seen_walk = True
            for kid in kids:
                if kid.pid == host.pid:
                    own = ctx.room_snapshot(kid.pid)
                    if ((own or {}).get("game") or {}).get("walker") == (own or {}).get("you"):
                        continue
                r = ctx.room_do(kid.pid, "game", action="react",
                                emoji=random.choice(server_module.FASHION_REACTIONS))
                REPORT.count("fashion_react", 1 if isinstance(r, dict) and r.get("ok") else 0)
                time.sleep(.15)
        time.sleep(.6)
    if game.get("phase") != "results" and game.get("phase") != "runway":
        wait_until(lambda: (((ctx.room_snapshot(host.pid) or {}).get("game") or {}).get("phase") == "runway"), 20, .5)
    view = ctx.room_snapshot(host.pid)
    game = (view or {}).get("game") or {}
    awards = game.get("awards") or {}
    REPORT.check("fashion: the runway ran and gave kind ribbons",
                 seen_walk and game.get("phase") == "results" and bool(awards),
                 {"phase": game.get("phase"), "walked": len(game.get("walked") or []), "awards": len(awards)})
    if game.get("phase") != "results":
        ctx.teacher(action="end_game")
        time.sleep(11)
    return True


def scene_game(ctx, kind, kids, seconds=14):
    REPORT.note(f"scene: game {kind}")
    quiet_room(ctx, kids)
    ensure_outside(ctx, kids)
    host = kids[0]
    out = ctx.room_do(host.pid, "game", action="create", kind=kind)
    if not out.get("ok"):
        ctx.teacher(action="end_game")
        time.sleep(11)
        out = ctx.room_do(host.pid, "game", action="create", kind=kind)
    REPORT.check(f"{kind}: a game can start", bool(out.get("ok")), out)
    if not out.get("ok"):
        return False
    REPORT.count("scene_game:" + kind)
    for kid in kids[1:]:
        ctx.room_do(kid.pid, "game", action="join")
        REPORT.count("game_join")
        time.sleep(.1)
    start = ctx.room_do(host.pid, "game", action="start")
    REPORT.check(f"{kind}: the host starts the round", bool(start.get("ok")), start)
    end = time.time() + seconds
    did_actions = False
    while time.time() < end:
        for kid in kids:
            view = ctx.room_snapshot(kid.pid)
            game = (view or {}).get("game") or {}
            if not game or game.get("phase") not in ("hiding", "playing", "dressing", "runway"):
                continue
            did_actions = True
            # A tiny copy of the kid's game handler, driven here so the scene
            # always touches this game kind even if the random thread is busy.
            seat = (view or {}).get("you")
            if seat not in (game.get("joined") or []):
                continue
            if kind == "code":
                hint = (game.get("job") or {}).get("hint")
                if hint:
                    r = ctx.room_do(kid.pid, "game", action="run", code=hint)
                    REPORT.count("code_race_run", 1 if isinstance(r, dict) and r.get("ok") else 0)
            elif kind == "draw":
                if game.get("drawer") == seat:
                    for _ in range(3):
                        ctx.room_do(kid.pid, "game", action="paint", cell=random.randrange(pixel.DRAW_GRID ** 2),
                                    colour=random.randrange(len(pixel.DRAW_COLOURS)))
                    REPORT.count("draw_paint")
                    # Use the drawer's own word when it is shown.
                    word = (view.get("game") or {}).get("word")
                    if word:
                        pass
                else:
                    choices = game.get("choices") or []
                    if choices:
                        pick = random.choice(choices)
                        key = pick[0] if isinstance(pick, (list, tuple)) else pick
                        ctx.room_do(kid.pid, "game", action="guess", word=key)
                        REPORT.count("draw_guess")
            elif kind == "dance":
                seq, step = game.get("seq") or [], game.get("step") or 0
                if time.time() >= (game.get("ready") or 0) and step < len(seq):
                    r = ctx.room_do(kid.pid, "game", action="step", name=seq[step])
                    REPORT.count("dance_step", 1 if isinstance(r, dict) and r.get("ok") else 0)
            elif kind == "hide":
                if game.get("phase") == "hiding" and seat != game.get("it"):
                    cover = random.choice(view.get("cover") or [{"key": "oak", "x": 66, "y": .15}])
                    ctx.room_do(kid.pid, "walk", x=cover["x"], y=cover["y"])
                    r = ctx.room_do(kid.pid, "game", action="hide", cover=cover["key"])
                    REPORT.count("hide", 1 if isinstance(r, dict) and r.get("ok") else 0)
                elif game.get("phase") == "playing" and seat == game.get("it"):
                    cover = random.choice(view.get("cover") or [{"key": "oak"}])
                    ctx.room_do(kid.pid, "game", action="search", cover=cover["key"])
                    REPORT.count("search")
            elif kind == "race":
                if game.get("light") != "red":
                    r = ctx.room_do(kid.pid, "walk", x=random.randint(30, 620), y=round(random.uniform(.2, .9), 2))
                    REPORT.count("game_walk:race", 1 if isinstance(r, dict) and r.get("ok") else 0)
            else:
                r = ctx.room_do(kid.pid, "walk", x=random.randint(20, 620), y=round(random.uniform(.1, .95), 2))
                REPORT.count("game_walk:" + kind, 1 if isinstance(r, dict) and r.get("ok") else 0)
            time.sleep(.12)
        time.sleep(.5)
    view = ctx.room_snapshot(host.pid)
    game = (view or {}).get("game") or {}
    ctx.teacher(action="end_game")
    REPORT.check(f"{kind}: the round took actions", did_actions,
                 {"game": game.get("kind"), "phase": game.get("phase"), "actions": did_actions})
    # Let results clear before the next scene.
    wait_until(lambda: not ((ctx.room_snapshot(host.pid) or {}).get("game")), 14, .5)
    return True


def scene_wedding(ctx, kids, cancel=False):
    REPORT.note("scene: wedding" + (" (leave mid-ceremony)" if cancel else ""))
    quiet_room(ctx, kids)
    ensure_outside(ctx, kids, "wedding")
    host, partner = kids[0], kids[1]
    out = ctx.room_do(host.pid, "wedding")
    if not out.get("ok"):
        ctx.teacher(action="end_game")
        time.sleep(11)
        out = ctx.room_do(host.pid, "wedding")
    REPORT.check("wedding: the host can ask", bool(out.get("ok")), out)
    if not out.get("ok"):
        return False
    REPORT.count("scene_wedding")
    candidates = out.get("candidates") or []
    names = {k.name for k in kids}
    pick = next((c for c in candidates if c.get("name") in names and c.get("seat") != (ctx.room_snapshot(host.pid) or {}).get("you")), None)
    pick = pick or next((c for c in candidates if c.get("seat") != (ctx.room_snapshot(host.pid) or {}).get("you")), None)
    if not pick:
        REPORT.check("wedding: there is a friend to ask", False, candidates)
        ctx.room_do(host.pid, "wedding_cancel")
        return False
    partner = kid_by_name(ctx, pick.get("name")) or partner
    REPORT.check("wedding: the pick card has a friend", True, pick)
    r = ctx.room_do(host.pid, "wedding_pick", seat=pick["seat"])
    REPORT.check("wedding: the host picks a partner", bool(r.get("ok")), r)
    time.sleep(.7)
    view = ctx.room_snapshot(partner.pid)
    w = (view or {}).get("wedding") or {}
    REPORT.check("wedding: the friend sees the invite", w.get("phase") == "invite", w)
    r = ctx.room_do(partner.pid, "wedding_yes")
    REPORT.count("wedding_yes", 1 if isinstance(r, dict) and r.get("ok") else 0)
    REPORT.check("wedding: yes starts the ceremony", bool(r.get("ok")), r)
    wait_until(lambda: (((ctx.room_snapshot(host.pid) or {}).get("wedding") or {}).get("phase") == "ceremony"), 5, .2)
    if cancel:
        time.sleep(2.5)
        r = ctx.room_do(partner.pid, "leave")
        REPORT.count("wedding_leave_mid", 1 if isinstance(r, dict) and r.get("ok") else 0)
        time.sleep(1.0)
        w = (ctx.room_snapshot(host.pid) or {}).get("wedding")
        REPORT.check("wedding: a partner leaving stops the ceremony", not w, w)
    else:
        seen = {"seen_ceremony": False, "done": False}
        end = time.time() + 30
        while time.time() < end:
            w = (ctx.room_snapshot(host.pid) or {}).get("wedding")
            if w:
                seen["seen_ceremony"] = seen["seen_ceremony"] or w.get("phase") == "ceremony"
            else:
                seen["done"] = bool(seen["seen_ceremony"])
                break
            time.sleep(.8)
        REPORT.check("wedding: the ceremony finishes", seen["done"], seen)
    # clear any half-started wedding for the next scene
    w = (ctx.room_snapshot(host.pid) or {}).get("wedding")
    if w:
        ctx.room_do(host.pid, "wedding_cancel")
    return True


def scene_mural(ctx, kids):
    REPORT.note("scene: class mural, including the rate limit")
    ensure_outside(ctx, kids)
    kid = kids[0]
    # A quick burst: the fourth paint inside a second must be told to wait.
    rate_limited = 0
    for i in range(5):
        out = ctx.room_do(kid.pid, "mural", action="paint", cell=(kid.index * 37 + i) % MURAL_CELLS,
                          ink=i % len(server_module.MURAL_COLOURS))
        if isinstance(out, dict) and out.get("error") == "wait":
            rate_limited += 1
        elif isinstance(out, dict) and out.get("ok"):
            REPORT.count("mural_paint")
        time.sleep(.02)
    REPORT.count("mural_rate_limited", rate_limited)
    REPORT.check("mural: the 3-a-second limit answers wait", rate_limited >= 1, rate_limited)
    # Everyone paints a few, spaced enough to be accepted.
    for n in range(3):
        for k in kids:
            out = ctx.room_do(k.pid, "mural", action="paint",
                              cell=(k.index * 53 + n * 11 + int(time.time())) % MURAL_CELLS,
                              ink=(k.index + n) % len(server_module.MURAL_COLOURS))
            REPORT.count("mural_paint", 1 if isinstance(out, dict) and out.get("ok") else 0)
            time.sleep(.02)
        time.sleep(1.05)
    out = ctx.room_do(kid.pid, "mural", action="undo")
    REPORT.count("mural_undo", 1 if isinstance(out, dict) and out.get("ok") else 0)
    # One painter reaches the ten-square daily treat.
    for n in range(10):
        ctx.room_do(kid.pid, "mural", action="paint", cell=(kid.index * 31 + n) % MURAL_CELLS,
                    ink=n % len(server_module.MURAL_COLOURS))
        time.sleep(.36)
    view = ctx.room_snapshot(kid.pid)
    m = (view or {}).get("mural") or {}
    REPORT.check("mural: the shared picture keeps everyone's squares", (m.get("total") or 0) >= 8,
                 {"total": m.get("total"), "painters": len(m.get("painters") or [])})
    return True


def scene_homes(ctx, kids):
    REPORT.note("scene: homes round 2 (buy, place, paint/size/flip, wish, visit)")
    for kid in kids:
        fresh_state(ctx, kid)
        hang = kid.state.get("hang") or {}
        coins = hang.get("coins") or 0
        shop = hang.get("shop") or {}
        # Buy a couple of the cheap furniture pieces and a wall/floor to change.
        for key in ("balloons", "duck", "lamp", "w_pink", "f_check"):
            item = shop.get(key)
            if item and coins >= item["price"]:
                out = ctx.room_do(kid.pid, "buy", key=key)
                if isinstance(out, dict) and out.get("ok"):
                    REPORT.count("home_buy")
                    coins = out.get("coins", coins)
        out = ctx.room_do(kid.pid, "wish", key="lamp")
        REPORT.count("home_wish", 1 if isinstance(out, dict) and out.get("ok") else 0)
        fresh_state(ctx, kid)
        out = ctx.room_do(kid.pid, "home")
        REPORT.count("home_enter", 1 if isinstance(out, dict) and out.get("ok") else 0)
        view = ctx.room_snapshot(kid.pid)
        home = (view or {}).get("home") or {}
        # Put a piece out, then pick it up in the view and style it.
        out = ctx.room_do(kid.pid, "furnish", key="balloons", x=random.randint(40, 280), y=.55)
        REPORT.count("home_place", 1 if isinstance(out, dict) and out.get("ok") else 0)
        view = ctx.room_snapshot(kid.pid)
        home = (view or {}).get("home") or {}
        items = [i for i in (home.get("items") or []) if i.get("key") == "balloons"]
        if items:
            piece = items[-1]["id"]
            out = ctx.room_do(kid.pid, "furnish", what="style", piece=piece,
                              paint=random.randrange(pixel.FURN_PAINTS), size=2, flip=True)
            REPORT.check("home: a picked-up piece can be painted, resized and flipped",
                         isinstance(out, dict) and out.get("ok"), out)
            REPORT.count("home_style", 1 if isinstance(out, dict) and out.get("ok") else 0)
        else:
            REPORT.check("home: a piece can be put out", False, home)
        # Change this room's look.
        fresh_state(ctx, kid)
        for key in ("w_pink", "f_check"):
            if key in ((kid.state.get("hang") or {}).get("stuff") or []):
                ctx.room_do(kid.pid, "furnish", what="look", key=key, room=0)
        # Put a drawing in the home.
        drawings = kid.state.get("drawings") or []
        if drawings:
            out = ctx.room_do(kid.pid, "place", key=drawings[0]["key"], x=random.randint(30, 280), y=.35)
            REPORT.count("home_art", 1 if isinstance(out, dict) and out.get("ok") else 0)
        ctx.room_do(kid.pid, "home", out=True)
    # Visit a friend, give a heart, and leave.
    host, guest = kids[0], kids[1]
    ctx.room_do(guest.pid, "home", seat=(ctx.room_snapshot(host.pid) or {}).get("you"))
    out = ctx.room_do(guest.pid, "heart")
    REPORT.count("home_heart", 1 if isinstance(out, dict) and out.get("ok") else 0)
    REPORT.check("home: a visitor can give a heart", isinstance(out, dict) and out.get("ok"), out)
    ctx.room_do(guest.pid, "home", out=True)
    return True


def scene_chests_and_gems(ctx, kids):
    REPORT.note("scene: chests and gems")
    opened = 0
    for kid in kids:
        fresh_state(ctx, kid)
        chests = ((kid.state.get("hang") or {}).get("chests") or [])
        chest = next((c for c in chests if not c.get("open")), None)
        if chest:
            ctx.room_do(kid.pid, "go", name=chest["place"])
            out = ctx.room_do(kid.pid, "chest", place=chest["place"], code=chest.get("hint") or "")
            if isinstance(out, dict) and out.get("open"):
                opened += 1
            REPORT.count("chest_open", 1 if isinstance(out, dict) and out.get("open") else 0)
            time.sleep(.9)
        gem = next((g for g in HANG_FINDS if g[:-1] == chest["place"]), HANG_FINDS[0]) if chest else HANG_FINDS[kid.index % len(HANG_FINDS)]
        ctx.room_do(kid.pid, "go", name=gem[:-1])
        out = ctx.room_do(kid.pid, "find", key=gem)
        REPORT.count("gem_find", 1 if isinstance(out, dict) and out.get("ok") else 0)
        time.sleep(.2)
    REPORT.check("chests: a correct code opens a chest", opened >= 1, opened)
    return True


# ---------------------------------------------------------------------------
# Background pollers: one projector and one teacher page
# ---------------------------------------------------------------------------
def projector_loop(ctx):
    after = -1
    while not ctx.stop.is_set():
        if ctx.restarting.is_set():
            time.sleep(.4)
            continue
        try:
            out = ctx.call(f"/pixel/room?after={after}&wait=1", None, timeout=15, poll=True)
            if isinstance(out, dict) and not out.get("__error__"):
                after = max(after, int(out.get("seq", after) or after))
                REPORT.count("poll_projector")
            if random.random() < .2:
                ctx.call("/pixel/overview", None, timeout=10, poll=True)
        except Exception:
            time.sleep(.5)
        time.sleep(.1)


def teacher_loop(ctx):
    while not ctx.stop.is_set():
        if ctx.restarting.is_set():
            time.sleep(.4)
            continue
        try:
            out = ctx.teacher(action="overview")
            if isinstance(out, dict) and not out.get("__error__"):
                REPORT.count("poll_teacher")
        except Exception:
            pass
        time.sleep(4.0)


# ---------------------------------------------------------------------------
# Monitoring: tracebacks, /proc CPU+RSS, state-file size
# ---------------------------------------------------------------------------
def monitor_loop(ctx):
    log_pos = 0
    last = {}
    while not ctx.stop.is_set():
        # tracebacks in the server log
        try:
            if os.path.exists(ctx.server_log):
                with open(ctx.server_log, "rb") as f:
                    f.seek(log_pos)
                    chunk = f.read()
                    log_pos = f.tell()
                text = chunk.decode("utf-8", "replace")
                if "Traceback (most recent call last)" in text or "Exception occurred during processing" in text:
                    with REPORT.lock:
                        REPORT.tracebacks.append({"at": round(time.time() - REPORT.started, 1),
                                                  "text": text[-1200:]})
        except OSError:
            pass
        # proc sample every 10 s
        proc = ctx.proc
        if proc and proc.poll() is None:
            try:
                pid = proc.pid
                now = time.time()
                with open(f"/proc/{pid}/stat") as f:
                    parts = f.read().split()
                ticks = int(parts[13]) + int(parts[14])
                rss = 0
                try:
                    with open(f"/proc/{pid}/status") as f:
                        for line in f:
                            if line.startswith("VmRSS:"):
                                rss = int(line.split()[1])
                                break
                except OSError:
                    pass
                state_bytes = os.path.getsize(ctx.state_file) if os.path.exists(ctx.state_file) else 0
                if last.get("pid") == pid:
                    dt = max(.1, now - last["at"])
                    cpu = (ticks - last["ticks"]) / os.sysconf("SC_CLK_TCK") / dt * 100
                else:
                    cpu = 0.0
                last = {"pid": pid, "ticks": ticks, "at": now}
                with REPORT.lock:
                    REPORT.samples.append({"at": round(now - REPORT.started, 1), "pid": pid,
                                           "cpu": round(cpu, 1), "rss_kb": rss, "state_bytes": state_bytes})
                    if len(REPORT.samples) > 1000:
                        del REPORT.samples[:-1000]
                try:
                    REPORT.peak_threads = max(REPORT.peak_threads, len(os.listdir(f"/proc/{pid}/task")))
                except OSError:
                    pass
            except Exception:
                pass
        time.sleep(1.0)


# ---------------------------------------------------------------------------
# Setup: 25 students, all missions, a drawing, some shop things
# ---------------------------------------------------------------------------
def setup_class(ctx, count):
    REPORT.note(f"joining {count} students")
    names = [f"Chaos {i + 1:02d}" for i in range(count)]
    kids = []
    for i, name in enumerate(names):
        out = ctx.call("/join", {"name": name})
        if not out.get("id"):
            raise SystemExit(f"could not join {name}: {out}")
        kids.append(Kid(ctx, out["id"], name, i))
    ctx.kids = kids
    ctx.teacher(action="room", on=False)
    ctx.teacher(action="open", level=pixel.LEVEL_ORDER[-1])
    ctx.teacher(action="end_game")
    ctx.teacher(action="placed_clear")
    ctx.teacher(action="room", on=True)
    # All missions, so every child has coins, every gift box, and the Free
    # stage. Run them in a few threads so this setup also loads the server.
    errors = []
    error_lock = threading.Lock()

    def run_all(kid):
        for key in pixel.LEVEL_ORDER:
            out = ctx.call("/pixel/run", {"id": kid.pid, "level": key,
                                          "code": pixel.LEVEL_BY_KEY[key]["reference"]})
            if isinstance(out, dict) and out.get("error"):
                with error_lock:
                    errors.append((kid.name, key, out["error"]))
        palette = dict(PAL)
        palette["key"] = "cp" + kid.pid
        palette["title"] = kid.name + " pal"
        ctx.call("/pixel/save", {"id": kid.pid, "drawing": palette})
        ctx.call("/pixel/thing/save", {"id": kid.pid, "key": palette["key"], "code": THING_CODE})
        ctx.call("/pixel/room/do", {"id": kid.pid, "what": "join"})
        st = ctx.student_state(kid.pid)
        hang = (st or {}).get("hang") or {}
        shop, coins = hang.get("shop") or {}, hang.get("coins") or 0
        want = ["beanie", "bunny", "balloons", "duck", "lamp", "w_pink", "f_check"]
        for key in want:
            item = shop.get(key)
            if item and coins >= item["price"]:
                out = ctx.call("/pixel/room/do", {"id": kid.pid, "what": "buy", "key": key})
                if isinstance(out, dict) and out.get("ok"):
                    coins = out.get("coins", coins)
        # One kid buys a room, so the grown home is exercised.
        if kid.index == 0:
            ctx.call("/pixel/room/do", {"id": kid.pid, "what": "buy", "key": "r_bed"})
        kid.state = ctx.student_state(kid.pid)

    workers = []
    for kid in kids:
        t = threading.Thread(target=run_all, args=(kid,), daemon=True)
        t.start()
        workers.append(t)
    for t in workers:
        t.join(timeout=60)
    REPORT.check("setup: every student finishes every mission", not errors, errors[:4])
    REPORT.note(f"setup: {len(kids)} students, each with "
                f"{len((kids[0].state.get('drawings') or []))} drawings and "
                f"{(kids[0].state.get('hang') or {}).get('coins')} coins")
    return kids


# ---------------------------------------------------------------------------
# Summary of the samples
# ---------------------------------------------------------------------------
def sample_summary():
    samples = REPORT.samples
    if not samples:
        return {}
    by_pid = {}
    for s in samples:
        by_pid.setdefault(s["pid"], []).append(s)
    runs = []
    for pid, rows in by_pid.items():
        runs.append({"pid": pid,
                     "samples": len(rows),
                     "cpu_avg": round(sum(r["cpu"] for r in rows) / len(rows), 1),
                     "cpu_max": max(r["cpu"] for r in rows),
                     "rss_first_kb": rows[0]["rss_kb"], "rss_last_kb": rows[-1]["rss_kb"],
                     "rss_max_kb": max(r["rss_kb"] for r in rows),
                     "state_first": rows[0]["state_bytes"], "state_last": rows[-1]["state_bytes"],
                     "state_max": max(r["state_bytes"] for r in rows)})
    states = [s["state_bytes"] for s in samples if s["state_bytes"]]
    return {"runs": runs, "state_min": min(states) if states else 0,
            "state_max": max(states) if states else 0,
            "state_first": states[0] if states else 0,
            "state_last": states[-1] if states else 0,
            "peak_threads": REPORT.peak_threads}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--port", type=int, default=int(os.environ.get("MAZE_PORT", "8907")))
    ap.add_argument("--base", default="")
    ap.add_argument("--state", default="/tmp/classtest-state.json")
    ap.add_argument("--server-log", default="/tmp/classtest/server.log")
    ap.add_argument("--duration", type=float, default=600)
    ap.add_argument("--students", type=int, default=25)
    ap.add_argument("--seed", type=int, default=4)
    ap.add_argument("--json-out", default="/tmp/classtest/chaos.json")
    ap.add_argument("--no-serve", action="store_true", help="use a server already on --port")
    ap.add_argument("--keep-server", action="store_true")
    ap.add_argument("--fresh", action="store_true", help="delete the state file first (when serving)")
    args = ap.parse_args()
    random.seed(args.seed)
    os.makedirs(os.path.dirname(args.server_log) or ".", exist_ok=True)
    os.makedirs(os.path.dirname(args.json_out) or ".", exist_ok=True)
    if args.fresh and not args.no_serve and os.path.exists(args.state):
        os.remove(args.state)
    base = args.base or f"http://127.0.0.1:{args.port}"
    ctx = Ctx(base, args.port, args.state, args.server_log, not args.no_serve, args.keep_server)
    monitor = threading.Thread(target=monitor_loop, args=(ctx,), daemon=True)
    monitor.start()
    projector = threading.Thread(target=projector_loop, args=(ctx,), daemon=True)
    teacher = threading.Thread(target=teacher_loop, args=(ctx,), daemon=True)
    ok_start = True
    if ctx.serve:
        # A stale server from a previous run would make the port fail: check first.
        try:
            urllib.request.urlopen(base + "/pixel/overview", timeout=1)
            raise SystemExit(f"something is already listening on {args.port}; stop it first")
        except SystemExit:
            raise
        except Exception:
            pass
        ok_start = ctx.start_server()
        REPORT.check("server starts for the stress test", ok_start, ctx.server_log)
        if not ok_start:
            print("server did not start; see", ctx.server_log)
            return 2
    projector.start()
    teacher.start()
    try:
        kids = setup_class(ctx, args.students)
        for kid in kids:
            kid.thread.start()
        REPORT.note("the random class traffic is running")
        scenes = ["fashion", "hide", "tag", "race", "dance", "draw", "apples", "ball", "code",
                  "wedding", "mural", "homes", "chests", "shop", "wedding-cancel"]
        started = time.time()
        restart_at = started + args.duration * .55
        did_restart = False
        scene_no = 0
        while time.time() - started < args.duration:
            elapsed = time.time() - started
            if not did_restart and time.time() >= restart_at and ctx.serve:
                REPORT.note("pausing the class for the mid-run restart")
                ctx.stop_backup = None
                ctx.restart_server()
                did_restart = True
                time.sleep(1.0)
                continue
            if did_restart is False and time.time() >= restart_at and not ctx.serve:
                REPORT.note("not restarting: --no-serve")
                did_restart = True
            name = scenes[scene_no % len(scenes)]
            scene_no += 1
            # Rotate the participant group so all 25 students are used.
            start_index = (scene_no * 3) % max(1, len(kids))
            if name in ("fashion", "wedding", "wedding-cancel", "mural"):
                group = [kids[(start_index + i) % len(kids)] for i in range(4 if name == "fashion" else 6 if name.startswith("wedding") else 8)]
            elif name in ("homes", "chests"):
                group = [kids[(start_index + i) % len(kids)] for i in range(4)]
            elif name == "shop":
                group = [kids[(start_index + i) % len(kids)] for i in range(6)]
            else:
                group = [kids[(start_index + i) % len(kids)] for i in range(4)]
            ctx.mark_busy(group, True)
            time.sleep(.5)
            try:
                if name == "fashion":
                    scene_fashion(ctx, group)
                elif name == "wedding":
                    scene_wedding(ctx, group, cancel=False)
                elif name == "wedding-cancel":
                    scene_wedding(ctx, group, cancel=True)
                elif name == "mural":
                    scene_mural(ctx, group)
                elif name == "homes":
                    scene_homes(ctx, group)
                elif name == "chests":
                    scene_chests_and_gems(ctx, group)
                elif name == "shop":
                    for kid in group:
                        fresh_state(ctx, kid)
                        shop = ((kid.state.get("hang") or {}).get("shop") or {})
                        for key in list(shop):
                            if shop[key].get("price", 0) <= 40:
                                ctx.room_do(kid.pid, "wish", key=key)
                                break
                else:
                    scene_game(ctx, name, group, seconds=24 if name == "hide" else 12)
            except Exception as e:
                REPORT.problem("scene " + name, f"{type(e).__name__}: {e}\n{traceback.format_exc()[-700:]}")
                try:
                    ctx.teacher(action="end_game")
                except Exception:
                    pass
            finally:
                ctx.mark_busy(group, False)
            # Random gap: the class keeps playing on its own between scenes.
            time.sleep(random.uniform(2.0, 5.0))
        REPORT.check("the stress run lasted the planned time", time.time() - started >= args.duration * .95,
                     round(time.time() - started, 1))
    finally:
        ctx.stop.set()
        for kid in ctx.kids:
            try:
                kid.thread.join(timeout=3)
            except Exception:
                pass
        time.sleep(.5)
        projector.join(timeout=3)
        teacher.join(timeout=3)
        if ctx.serve and not ctx.keep_server:
            ctx.stop_server()
        summary = REPORT.summary()
        summary["samples_summary"] = sample_summary()
        summary["port"] = args.port
        summary["state_file"] = args.state
        summary["server_log"] = args.server_log
        summary["duration_target"] = args.duration
        with open(args.json_out, "w") as f:
            json.dump(summary, f, indent=2, default=str)
        print(json.dumps({k: summary[k] for k in
                          ("seconds", "requests", "status_counts", "server_error_count",
                           "net_error_count", "slow_count", "traceback_count", "restarts",
                           "counts", "samples_summary")}, indent=2, default=str)[:8000])
        print("\nwrote", args.json_out)
    failed = (REPORT.net_errors or REPORT.server_errors or REPORT.tracebacks or
              any(not c["ok"] for c in REPORT.checks))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
