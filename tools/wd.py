"""A small chromedriver client over plain HTTP (no selenium): wd.new(w, h) starts headless Chromium.
Used by the tools/e2e_planet_*.py bug-hunt scripts."""
import base64, json, os, socket, subprocess, sys, time, urllib.error, urllib.request

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



    def shot(self, path):
        data = self.request("GET", f"/session/{self.sid}/screenshot")
        open(path, "wb").write(base64.b64decode(data))

    def go(self, url):
        self.request("POST", f"/session/{self.sid}/url", {"url": url})


def new(w=1366, h=768):
    return Driver("/usr/bin/chromedriver", "/usr/bin/chromium", w, h)
