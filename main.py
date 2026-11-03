import os, sys, datetime, traceback
from src import scenes, cf_images, render, yt, stock, captions
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
    day = (datetime.date.today() - datetime.date(2026, 1, 1)).days
    acc, tok = env("CF_ACCOUNT_ID"), env("CF_API_TOKEN")
    log("cloudflare verify:", *cf_images.verify(acc, tok))
    if mode == "check":
        stock_name, clips = stock.pick_clips(day, day, 4, log)
        log("captions:", captions.make(stock_name, 4, log)); return
    os.makedirs("out", exist_ok=True); out = "out/video.mp4"; work = "out/work"
    use_ai = (day % 3 == 2) or mode == "ai"
    synthetic = True; credits = ""
    hook = scenes.HOOKS[day % len(scenes.HOOKS)]
    if not use_ai:
        name, clips = stock.pick_clips(day, day, 4, log)
        if len(clips) >= 3:
            os.makedirs(work, exist_ok=True); files = []
            for i, c in enumerate(clips):
                files.append(stock.download(c, f"{work}/src{i}.mp4"))
            caps = captions.make(name, 3, log)
            render.build_stock_video(files, hook, caps, out, work, per=4.0, seed=day, log=log)
            synthetic = False
            credits = "Footage: " + ", ".join(sorted({c["credit"] for c in clips})) + " via Pexels/Pixabay."
            title_base = stock.TITLES[day % len(stock.TITLES)]; theme = name
        else:
            log("not enough stock clips, falling back to AI images"); use_ai = True
    if use_ai:
        name, desc = scenes.SCENES[day % len(scenes.SCENES)]
        light = scenes.LIGHTS[(day // len(scenes.SCENES)) % len(scenes.LIGHTS)]
        imgs = []
        for i in range(4):
            ang = scenes.ANGLES[i % len(scenes.ANGLES)]
            prompt = f"Ultra realistic cinematic photo, {desc}, {light}, {ang}, highly detailed, vivid colors, no people, no text"
            imgs.append(cf_images.generate(acc, tok, prompt)); log(f"image {i+1}/4 ok")
        render.build_video(imgs, hook, out, work, per=4.0, seed=day, log=log)
        title_base = "AI Dream Places"; theme = name
        credits = "All visuals are AI-generated and not real photographs."
    log("video built", os.path.getsize(out), "bytes")
    access = yt.access_token(env("GOOGLE_CLIENT_ID"), env("GOOGLE_CLIENT_SECRET"), env("YT_REFRESH_TOKEN"))
    title = f"{title_base}: {theme} #shorts"[:100]
    description = (f"{hook}. {theme} in a calm 16 second escape.\n{credits}\n"
                   "#travel #nature #adventure #shorts #places #earth")
    vid, privacy = yt.upload(access, out, title, description, ["travel", "nature", "places on earth", "shorts", "scenery"], synthetic=synthetic)
    log("uploaded:", vid, "privacy:", privacy, "| title:", title)
def do_brand():
    from src import art
    access = yt.access_token(env("GOOGLE_CLIENT_ID"), env("GOOGLE_CLIENT_SECRET"), env("YT_REFRESH_TOKEN"))
    os.makedirs("out", exist_ok=True); art.banner("out/banner.png")
    desc = ("Dreamy Earth: calm, breathtaking places on our planet in short videos. New video every day.\n"
            "Visuals are real stock footage or clearly labeled AI art.\nSubscribe for daily escapes.")
    kw = 'travel nature "places on earth" scenery relaxing "beautiful places" shorts'
    res = yt.brand(access, desc, kw, "out/banner.png"); log("brand:", res); return res
def execute(mode="run"):
    lines.clear()
    try:
        (do_brand if mode == "brand" else main)(*([] if mode == "brand" else [mode])); log("RESULT: OK")
    except BaseException as e:
        log("RESULT: FAIL", type(e).__name__, str(e)[:500]); log(traceback.format_exc()[-600:])
    finally:
        save()
    return "\n".join(lines)
if __name__ == "__main__":
    execute(sys.argv[1] if len(sys.argv) > 1 else "run")
