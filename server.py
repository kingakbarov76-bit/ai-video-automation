import os, json, threading, time, urllib.parse, requests
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import main as job
STATE = {"running": False, "last_start": 0, "last_mode": None}
LOCK = threading.Lock()
def keepalive():
    url = os.environ.get("RENDER_EXTERNAL_URL", "")
    while STATE["running"]:
        time.sleep(240)
        try: requests.get(url + "/", timeout=30)
        except Exception: pass
def runner(mode):
    threading.Thread(target=keepalive, daemon=True).start()
    r = None
    try: r = job.execute(mode)
    finally:
        if r != "busy": STATE["running"] = False   # a refused duplicate must not mark the real job as finished
def start(mode):
    with LOCK:
        if STATE["running"]:
            # a second wake-up ping (or the boot timer) while a run is already
            # going is just a duplicate: answer fast, queue nothing
            long_job = time.time() - STATE.get("last_start", 0) > 20 * 60   # e.g. the weekly long video
            if mode == "run" and (STATE.get("last_mode") != "run" or long_job) and not STATE.get("queued"):
                STATE["queued"] = True
                def later():
                    while STATE["running"]: time.sleep(5)
                    STATE["queued"] = False; start("run")
                threading.Thread(target=later, daemon=True).start()
                return "busy, run queued"
            return "already running"
        STATE.update(running=True, last_mode=mode, last_start=time.time())
    threading.Thread(target=runner, args=(mode,), daemon=True).start()
    return "started " + mode
class H(BaseHTTPRequestHandler):
    def send(self, body, code=200, ctype="text/plain; charset=utf-8"):
        b = body.encode(); self.send_response(code); self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(b))); self.end_headers()
        if not getattr(self, "_head", False): self.wfile.write(b)
    def do_HEAD(self):   # UptimeRobot probes with HEAD; treat it like GET (no body)
        self._head = True; self.do_GET()
    def do_GET(self):
        u = urllib.parse.urlparse(self.path); q = urllib.parse.parse_qs(u.query)
        if u.path == "/": return self.send("ok")
        if u.path == "/run": return self.send(start("run"))
        if u.path == "/check": return self.send(start("check"))
        if u.path == "/choose": return self.send(start("choose"))
        if u.path == "/analyze": return self.send(start("analyze"))
        if u.path == "/brand": return self.send(start("brand"))
        if u.path == "/ai": return self.send(start("ai"))
        if u.path == "/musictest": return self.send(start("musictest"))
        if u.path == "/ttstest": return self.send(start("ttstest"))
        if u.path.strip("/") in ("placescan", "dry_list", "dry_single", "dry_dream", "dry_choose", "dry_ambient", "ambient", "dry_long", "long"): return self.send(start(u.path.strip("/")))
        if u.path == "/music.mp3":
            p = "out/music_test.mp3"
            if not os.path.exists(p): return self.send("hali yo'q", 404)
            b = open(p, "rb").read(); self.send_response(200); self.send_header("Content-Type", "audio/mpeg")
            self.send_header("Content-Length", str(len(b))); self.end_headers(); self.wfile.write(b); return
        if u.path == "/status":
            txt = open("logs/last_run.txt").read() if os.path.exists("logs/last_run.txt") else "no run yet"
            return self.send(f"running={STATE['running']}\n{txt}")
        if u.path == "/auth":
            cid = os.environ.get("GOOGLE_CLIENT_ID", "")
            scope = "https://www.googleapis.com/auth/youtube.upload https://www.googleapis.com/auth/youtube https://www.googleapis.com/auth/yt-analytics.readonly"
            link = ("https://accounts.google.com/o/oauth2/v2/auth?" + urllib.parse.urlencode({
                "client_id": cid, "redirect_uri": "http://localhost", "response_type": "code",
                "scope": scope, "access_type": "offline", "prompt": "consent"}))
            code = (q.get("code") or [""])[0]
            if not code:
                return self.send(f'<a href="{link}">1) Ruxsat berish uchun shu havolani bosing</a><br>2) Oxirida localhost xatosi chiqadi: manzildan code= dan keyingi qismni nusxalang<br>3) Shu sahifaga ?code=NUSXA qo\'shib oching', ctype="text/html; charset=utf-8")
            r = requests.post("https://oauth2.googleapis.com/token", data={"code": code, "client_id": cid,
                "client_secret": os.environ.get("GOOGLE_CLIENT_SECRET", ""), "redirect_uri": "http://localhost",
                "grant_type": "authorization_code"}, timeout=30)
            j = r.json()
            if "refresh_token" in j: return self.send("REFRESH TOKEN (nusxalang va Claude'ga yuboring):\n" + j["refresh_token"])
            return self.send("xato: " + json.dumps({k: j.get(k) for k in ("error", "error_description")}))
        self.send("not found", 404)
    def log_message(self, *a): pass
if __name__ == "__main__":
    # any wake-up (cron ping, deploy, visit) starts a run; the run itself skips if the slot is already done
    threading.Timer(40, lambda: start("run")).start()
    ThreadingHTTPServer(("0.0.0.0", int(os.environ.get("PORT", "10000"))), H).serve_forever()
