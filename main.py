import os, sys, datetime, traceback
from src import scenes, cf_images, render, yt
LOG = "logs/last_run.txt"
lines = []
def log(*a):
    s = " ".join(str(x) for x in a); lines.append(s); print(s, flush=True)
def save():
    os.makedirs("logs", exist_ok=True)
    open(LOG, "w").write(f"{datetime.datetime.utcnow().isoformat()}Z\n" + "\n".join(lines) + "\n")
import json
_CFG = json.loads(os.environ.get("CONFIG_JSON") or "{}")
def env(k):
    v = (os.environ.get(k) or _CFG.get(k) or "").strip()
    if not v: raise SystemExit(f"missing secret: {k}")
    return v
def main(mode):
    acc, tok = env("CF_ACCOUNT_ID"), env("CF_API_TOKEN")
    log("cloudflare verify:", *cf_images.verify(acc, tok))
    day = (datetime.date.today() - datetime.date(2026, 1, 1)).days
    name, desc = scenes.SCENES[day % len(scenes.SCENES)]
    light = scenes.LIGHTS[(day // len(scenes.SCENES)) % len(scenes.LIGHTS)]
    n = 1 if mode == "check" else 5
    imgs = []
    for i in range(n):
        ang = scenes.ANGLES[i % len(scenes.ANGLES)]
        prompt = f"Ultra realistic cinematic photo, {desc}, {light}, {ang}, highly detailed, vivid colors, no people, no text"
        imgs.append(cf_images.generate(acc, tok, prompt)); log(f"image {i+1}/{n} ok ({len(imgs[-1])} bytes)")
    if mode == "check":
        from PIL import Image; import io
        log("image size:", Image.open(io.BytesIO(imgs[0])).size)
        return
    hook = scenes.HOOKS[day % len(scenes.HOOKS)]
    os.makedirs("out", exist_ok=True); out = "out/video.mp4"
    render.build_video(imgs, hook, out, "out/work", per=4.0, seed=day)
    log("video built", os.path.getsize(out), "bytes")
    access = yt.access_token(env("GOOGLE_CLIENT_ID"), env("GOOGLE_CLIENT_SECRET"), env("YT_REFRESH_TOKEN"))
    title = f"{name} #shorts"
    description = (f"{hook}. AI-generated dreamlike landscapes with original calm music.\n"
                   "All visuals are AI-generated and not real photographs.\n#AIart #relaxing #shorts #dreamy")
    vid, privacy = yt.upload(access, out, title, description, ["AI art", "relaxing", "shorts", "landscape"])
    log("uploaded:", vid, "privacy:", privacy)
if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "run"
    try:
        main(mode); log("RESULT: OK")
    except BaseException as e:
        log("RESULT: FAIL", type(e).__name__, str(e)[:500]); log(traceback.format_exc()[-600:])
    finally:
        save()
