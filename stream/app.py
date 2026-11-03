import os, sys, time, threading, datetime, subprocess, collections
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from stream import land, loop
LOGS = collections.deque(maxlen=80); STATE = {"running": False, "slot": None}
KEY = os.environ.get("STREAM_KEY", "").strip()
HOURS = [int(x) for x in os.environ.get("STREAM_HOURS_UTC", "18,0").split(",") if x.strip()]
DUR_H = float(os.environ.get("STREAM_HOURS", "3"))
URL = os.environ.get("STREAM_URL", "rtmps://a.rtmps.youtube.com:443/live2")
LOOP = "work/loop.mp4"
def log(*a):
    s = datetime.datetime.utcnow().strftime("%H:%M:%S ") + " ".join(str(x) for x in a)
    LOGS.append(s.replace(KEY, "***") if KEY else s); print(LOGS[-1], flush=True)
def ensure_loop():
    if os.path.exists(LOOP): return
    os.makedirs("work/src", exist_ok=True)
    clips = land.pick(50, datetime.date.today().toordinal(), log); files = []
    for i, c in enumerate(clips):
        try: files.append(land.download(c, f"work/src/s{i}.mp4"))
        except Exception as e: log("download failed:", str(e)[:80])
    if len(files) < 15: raise RuntimeError(f"only {len(files)} clips")
    loop.build(files, LOOP, "work/b", per=7, seed=datetime.date.today().toordinal() % 7, log=log)
    for f in files: os.remove(f)
    log("loop ready")
def stream(seconds, slot):
    STATE.update(running=True, slot=slot)
    try:
        if not KEY: log("STREAM_KEY yo'q"); return
        ensure_loop(); end = time.time() + seconds; tries = 0
        while time.time() < end - 20:
            left = int(end - time.time()); log(f"streaming, {left}s left")
            p = subprocess.run(["ffmpeg", "-re", "-stream_loop", "-1", "-i", LOOP, "-c", "copy", "-t", str(left), "-f", "flv", f"{URL}/{KEY}"],
                               capture_output=True, text=True)
            if p.returncode == 0: break
            tries += 1; log("ffmpeg exit", p.returncode, p.stderr[-200:].replace(KEY, "***")); time.sleep(min(60, 5 * tries))
        log("stream block finished")
    except Exception as e: log("stream error:", str(e)[:200])
    finally: STATE["running"] = False
def scheduler():
    while True:
        try:
            now = datetime.datetime.utcnow()
            for h in HOURS:
                start = now.replace(hour=h, minute=0, second=0, microsecond=0); endt = start + datetime.timedelta(hours=DUR_H)
                slot = start.isoformat()
                if start <= now < endt - datetime.timedelta(minutes=2) and not STATE["running"] and STATE["slot"] != slot:
                    secs = int((endt - now).total_seconds()); threading.Thread(target=stream, args=(secs, slot), daemon=True).start()
        except Exception as e: log("scheduler error:", str(e)[:100])
        time.sleep(30)
class H(BaseHTTPRequestHandler):
    def do_GET(self):
        path = self.path.split("?")[0]; body = "ok"
        if path == "/status": body = f"running={STATE['running']} hours_utc={HOURS} dur_h={DUR_H} key_set={bool(KEY)}\n" + "\n".join(LOGS)
        if path == "/test" and not STATE["running"] and KEY:
            threading.Thread(target=stream, args=(300, "test"), daemon=True).start(); body = "test stream 5 min started"
        b = body.encode(); self.send_response(200); self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(b))); self.end_headers(); self.wfile.write(b)
    def log_message(self, *a): pass
if __name__ == "__main__":
    threading.Thread(target=scheduler, daemon=True).start(); log("live app started; hours_utc", HOURS, "dur_h", DUR_H)
    ThreadingHTTPServer(("0.0.0.0", int(os.environ.get("PORT", "7860"))), H).serve_forever()
