import os, sys, datetime, traceback
from src import scenes, cf_images, render, yt, stock, captions, analyze, aiplaces
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
    day = (_now.date() - datetime.date(2026, 1, 1)).days * 6 + _now.hour // 4  # six slots per day
    acc, tok = env("CF_ACCOUNT_ID"), env("CF_API_TOKEN")
    log("cloudflare verify:", *cf_images.verify(acc, tok))
    if mode == "analyze":
        a = yt.access_token(env("GOOGLE_CLIENT_ID"), env("GOOGLE_CLIENT_SECRET"), env("YT_REFRESH_TOKEN"))
        vids = yt.my_videos_stats(a); w, summ, top = analyze.run(vids, [t[0] for t in stock.THEMES])
        log("ANALYSIS:", summ)
        for v in vids[:20]: log(f"  {v['id']} views={v['views']} likes={v['likes']} | {v['title'][:50]}")
        return
    if mode == "check":
        names, clips = stock.pick_multi(day, 13, log)
        log("themes:", names, "| first clip:", clips[0]["src"] if clips else None); return
    os.makedirs("out", exist_ok=True); out = "out/video.mp4"; work = "out/work"
    use_choose = (day % 6 == 3) or mode == "choose"
    use_ai = ((day % 3 == 2) or mode == "ai") and not use_choose
    synthetic = True; credits = ""
    hook = scenes.HOOKS[day % len(scenes.HOOKS)]
    if use_choose:
        ch = aiplaces.pick_choices(day, 4); imgs = []
        for i, (nm, pr) in enumerate(ch):
            imgs.append(cf_images.generate(acc, tok, pr)); log(f"choice image {i+1}/4 ok")
        render.build_choice_video(imgs, [n for n, _ in ch], out, work, seed=day, log=log)
        title_base = "Which place would you stay in?"; theme = ", ".join(n for n, _ in ch)
        credits = "All visuals are AI-generated and not real places."
    if not use_ai and not use_choose:
        weights = None
        try:
            acc_tok = yt.access_token(env("GOOGLE_CLIENT_ID"), env("GOOGLE_CLIENT_SECRET"), env("YT_REFRESH_TOKEN"))
            weights, summ, top = analyze.run(yt.my_videos_stats(acc_tok), [t[0] for t in stock.THEMES])
            log("ANALYSIS:", summ); [log("  top:", t) for t in top]
        except Exception as ex: log("analysis skipped:", str(ex)[:120])
        names, clips = stock.pick_multi(day, 18, log, weights=weights)
        files = []
        for i, c in enumerate(clips):
            if len(files) >= 13: break
            try: files.append(stock.download(c, f"{work}/s{i}.mp4" if os.path.isdir(work) else _mk(work, i)))
            except Exception as ex: log(f"download {i} failed: {str(ex)[:80]}")
        if len(files) >= 9:
            line1 = "Places on Earth that don't feel real"
            rr = __import__("random").Random(day)
            caps = {3: rr.choice(aiplaces.FEEL_MID), len(files[:13]) - 1: rr.choice(aiplaces.FEEL_END)}
            try:
                render.build_beat_video2(files[:13], (line1, "Wait for the last one"), caps, None, out, work, seed=day, log=log, hd=True)
            except Exception as ex:
                log("HD build failed, falling back to 720p:", str(ex)[:150])
                render.build_beat_video2(files[:13], (line1, "Wait for the last one"), caps, None, out, work, seed=day, log=log)
            synthetic = False; theme = ", ".join(names[:4]) or "Nature"
            credits = "Footage from " + ", ".join(sorted({c["credit"] for c in clips})[:8]) + " via Pexels and Pixabay."
            title_base = stock.TITLES[day % len(stock.TITLES)]
        else:
            log("not enough stock clips, falling back to AI images"); use_ai = True
    if use_ai and not use_choose:
        prompts = aiplaces.pick(day, 13); os.makedirs(work, exist_ok=True); clipf = []
        for i, pr in enumerate(prompts):
            img = cf_images.generate(acc, tok, pr); clipf.append(render.image_to_clip(img, f"{work}/aic{i}.mp4", work, i)); log(f"image {i+1}/13 ok")
        rr = __import__("random").Random(day)
        caps = {3: rr.choice(aiplaces.FEEL_MID), 8: rr.choice(aiplaces.FEEL_MID), 12: rr.choice(aiplaces.FEEL_END)}
        render.build_beat_video2(clipf, ("Places that don't exist but should", "Wait for the last one"), caps, "AI-generated", out, work, seed=day, log=log)
        title_base = "AI Places I Wish Were Real"; theme = "AI dream places"
        credits = "All visuals are AI-generated and not real places."
    log("video built", os.path.getsize(out), "bytes")
    access = yt.access_token(env("GOOGLE_CLIENT_ID"), env("GOOGLE_CLIENT_SECRET"), env("YT_REFRESH_TOKEN"))
    title = (f"Which place would you stay in? 🤔 #AIart #travel #dreamplaces #nature" if use_choose else
             f"Places on earth that don't feel real {['😱','🤯','😍'][day % 3]} #travel #nature #world #adventure" if not use_ai
             else f"{title_base} 😍 #AIart #nature #travel #dreamy")[:100]
    description = (("#travel #nature #places\n" if not (use_ai or use_choose) else "#AIart #dreamplaces #travel\n") + ("Comment your number: which place would you choose? 👇\n" if use_choose else "") +
                   f"Places on Earth that don't feel real. Which one is your favorite? Tell me in the comments!\n"
                   f"Featuring: {theme}.\n{credits}\nFollow for a new unreal place every day.\n"
                   "#shorts #beautifulplaces #scenery #earth #adventure #aesthetic")
    synthetic = synthetic or use_choose or use_ai
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
