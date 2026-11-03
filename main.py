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
def _mk(work, i):
    os.makedirs(work, exist_ok=True); return f"{work}/s{i}.mp4"
def main(mode):
    _now = datetime.datetime.utcnow()
    day = (_now.date() - datetime.date(2026, 1, 1)).days * 2 + (1 if _now.hour >= 10 else 0)  # two slots per day
    acc, tok = env("CF_ACCOUNT_ID"), env("CF_API_TOKEN")
    log("cloudflare verify:", *cf_images.verify(acc, tok))
    if mode == "check":
        names, clips = stock.pick_multi(day, 13, log)
        log("themes:", names, "| first clip:", clips[0]["src"] if clips else None); return
    os.makedirs("out", exist_ok=True); out = "out/video.mp4"; work = "out/work"
    use_ai = (day % 6 == 5) or mode == "ai"
    synthetic = True; credits = ""
    hook = scenes.HOOKS[day % len(scenes.HOOKS)]
    if not use_ai:
        names, clips = stock.pick_multi(day, 13, log)
        files = []
        for i, c in enumerate(clips):
            try: files.append(stock.download(c, f"{work}/s{i}.mp4" if os.path.isdir(work) else _mk(work, i)))
            except Exception as ex: log(f"download {i} failed: {str(ex)[:80]}")
        if len(files) >= 9:
            line1 = "Places on Earth that don't feel real"
            render.build_beat_video(files, line1, "Wait for the last one", "Follow for more", out, work, seed=day, log=log)
            synthetic = False; theme = ", ".join(names[:4]) or "Nature"
            credits = "Footage from " + ", ".join(sorted({c["credit"] for c in clips})[:8]) + " via Pexels and Pixabay."
            title_base = stock.TITLES[day % len(stock.TITLES)]
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
    title = (f"Places on earth that don't feel real {['😱','🤯','😍'][day % 3]} #travel #nature #world #adventure" if not use_ai
             else f"{title_base}: {theme} #shorts #nature")[:100]
    description = (("#travel #nature #places\n" if not use_ai else "#AIart #nature #places\n") +
                   f"Places on Earth that don't feel real. Which one is your favorite? Tell me in the comments!\n"
                   f"Featuring: {theme}.\n{credits}\nFollow for a new unreal place every day.\n"
                   "#shorts #beautifulplaces #scenery #earth #adventure #aesthetic")
    vid, privacy = yt.upload(access, out, title, description, ["places on earth that don't feel real", "unreal places", "most beautiful places", "travel", "nature", "scenery", "satisfying", "aesthetic", "shorts"], synthetic=synthetic)
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
