import os, sys, json, random, datetime, traceback
from src import scenes, cf_images, render, yt, stock, captions, analyze, aiplaces, places, dreamworld
LOG = "logs/last_run.txt"
lines = []
def log(*a):
    s = " ".join(str(x) for x in a); lines.append(s); print(s, flush=True)
def save():
    os.makedirs("logs", exist_ok=True)
    open(LOG, "w").write(f"{datetime.datetime.utcnow().isoformat()}Z\n" + "\n".join(lines) + "\n")
_CFG = json.loads(os.environ.get("CONFIG_JSON") or "{}")
def env(k):
    v = (os.environ.get(k) or _CFG.get(k) or "").strip()
    if not v: raise SystemExit(f"missing secret: {k}")
    return v
def _yt():
    return yt.access_token(env("GOOGLE_CLIENT_ID"), env("GOOGLE_CLIENT_SECRET"), env("YT_REFRESH_TOKEN"))

# ---- schedule: 3 uploads a day at 04:00, 12:00, 20:00 Tashkent (UTC+5) ----
SLOT_HOURS = (4, 12, 20)
EPOCH = datetime.date(2026, 11, 4)
LONG_DAY, LONG_HOUR = 5, 16   # Saturday 16:00 Tashkent
def is_long_slot(now=None):
    loc = (now or datetime.datetime.utcnow()) + datetime.timedelta(hours=5)
    return loc.weekday() == LONG_DAY and loc.hour == LONG_HOUR
def slot_info(now=None):
    loc = (now or datetime.datetime.utcnow()) + datetime.timedelta(hours=5)
    h = loc.hour; d = loc.date()
    if h < 4: d -= datetime.timedelta(days=1)
    k = 0 if 4 <= h < 12 else (1 if 12 <= h < 20 else 2)
    return max(0, (d - EPOCH).days * 3 + k), k, h in SLOT_HOURS
PLAYLISTS = {
    "list": ("Real Places That Don't Feel Real", "Real places on Earth that look unreal. Every place is named in the video, with a quick fact in the description."),
    "single": ("Real Places That Don't Feel Real", "Real places on Earth that look unreal. Every place is named in the video, with a quick fact in the description."),
    "dream": ("Dreamworld: AI Art Series", "Dreamworld is our AI art series of imaginary places. Every episode is an invented place with its own short story. All visuals are AI-generated."),
    "long": ("Real Places That Don't Feel Real", "Real places on Earth that look unreal. Every place is named in the video, with a quick fact in the description."),
    "choose": ("Which Place Would You Stay In?", "Pick your favourite dream stay and comment the number. All visuals are AI-generated."),
}
FOOTER = "#shorts #placesthatdontfeelreal #beautifulplaces #travel #nature"
def music_line():
    return ("Music: original AI-generated track (ACE-Step 1.5)." if render.MUSIC_SRC else "Music: original track made for this channel.")

class Cursor:
    """Walks through each source clip so repeated uses show new footage instead of the same second."""
    def __init__(self): self.pos = {}
    def take(self, c, frames, fps=30):
        need = frames / fps + 0.2; p = self.pos.get(c["id"], 0.4)
        if p + need > c["dur"]: p = 0.4 if 0.4 + need <= c["dur"] else max(0.0, c["dur"] - need)
        self.pos[c["id"]] = p + need + 0.3; return p
def _download(c, path):
    return stock.download(c, path, max_mb=150)

def fmt_list(ep, work):
    """6 real, named places (label on screen), loop back to the first one."""
    D = ep // 3; order = places.order(101); n = len(order); got = []
    for j in range(18):
        if len(got) >= 6: break
        pl = places.PLACES[order[(D * 6 + j) % n]]
        cl = stock.place_clips(pl, 2, log, seed=ep + j)
        files = []
        for i, c in enumerate(cl[:3]):
            if len(files) >= 2: break
            try: files.append((_download(c, f"{work}/p{len(got)}_{i}.mp4"), c))
            except Exception as ex: log(f"  download failed: {str(ex)[:80]}")
        log(f"place {pl['label']}: {len(cl)} matching clips, {len(files)} downloaded")
        if files: got.append((pl, files))
    if len(got) < 5: return None
    m = len(got); cuts = list(range(2, 12)); per = [len(cuts) // (m - 1) + (1 if i < len(cuts) % (m - 1) else 0) for i in range(m - 1)]
    owner = [0, 0]
    for pi, k in enumerate(per): owner += [pi + 1] * k
    owner.append(0)  # last segment loops back to place 1
    used = {}; segs = []; ovs = []; cur = Cursor(); fr = render.FRAMES13
    hooks = [("Places on Earth that don't feel real", f"All {m} are real"), ("Real places that look fake", "Every one of them is real"),
             ("These places are real", "Which one is your favorite?")]
    h1, h2 = hooks[(ep // 3) % len(hooks)]; log("hook:", h1)
    for i, pi in enumerate(owner):
        pl, files = got[pi]
        if i == len(owner) - 1: path, c = got[0][1][0]; off = 0.4   # same frame as the start -> seamless loop
        else:
            u = used.get(pi, 0); used[pi] = u + 1; path, c = files[u % len(files)]; off = cur.take(c, fr[i])
        segs.append((path, off)); ov = f"{work}/card{i}.png"
        if i == 0: render.card(ov, hook=h1, hook2=h2, label=pl["label"], num=1)
        elif i == len(owner) - 1: render.card(ov, cta="Which one would you visit?")
        else: render.card(ov, label=pl["label"], num=pi + 1)
        ovs.append(ov)
    out = f"{work}/../video.mp4"; render.build_seq_video(segs, ovs, out, work, seed=ep, log=log, hd=True)
    names = [p["label"] for p, _ in got]; credits = sorted({c["credit"] for _, fs in got for _, c in fs})
    emo = ["🤯", "😱", "😍"][ep % 3]
    title = [f"Places on Earth that don't feel real {emo} #travel #nature #earth",
             f"Real places that look fake {emo} #travel #nature #earth",
             f"{m} real places that look unreal {emo} #travel #nature #earth"][(ep // 3) % 3]
    body = "\n".join(f"{i + 1}. {p['label']}: {p['f1']}. {p['f2']}." for i, (p, _) in enumerate(got))
    desc = (f"Places on Earth that don't feel real, but every one of them is real. Which one would you visit? Comment the number 👇\n\n{body}\n\n"
            f"Footage: {', '.join(credits[:10])} via Pexels and Pixabay (licensed stock footage, edited by Dreamy Earth).\n{music_line()}\n"
            f"Follow for real places that look unreal.\n{FOOTER} " + " ".join("#" + t for t in dict.fromkeys(p['tag'] for p, _ in got)))
    tags = ["places on earth that don't feel real", "real places that look fake", "unreal places", "beautiful places", "travel", "nature"] + [p["label"].split(",")[0] for p, _ in got]
    rec = [{"place": p["label"], "clips": [{"src": c["src"], "id": c["id"], "page": c["page"], "author": c["credit"]} for _, c in fs]} for p, fs in got]
    return dict(out=out, title=title, desc=desc, tags=tags, synthetic=False, rec=rec, theme=", ".join(names))

def fmt_single(ep, work):
    """One real place: name + two facts on screen."""
    D = ep // 3; order = places.order(202); n = len(order)
    for j in range(12):
        pl = places.PLACES[order[(D + j * 7) % n]]
        cl = stock.place_clips(pl, 6, log, seed=ep + j); files = []
        for i, c in enumerate(cl[:8]):
            if len(files) >= 5: break
            try: files.append((_download(c, f"{work}/s{i}.mp4"), c))
            except Exception as ex: log(f"  download failed: {str(ex)[:80]}")
        log(f"single {pl['label']}: {len(cl)} matching clips, {len(files)} downloaded")
        if len(files) >= 3: break
    else: return None
    if len(files) < 3: return None
    k = len(files); segs = []; ovs = []; cur = Cursor(); fr = render.FRAMES13
    for i in range(13):
        if i == 12: path, c = files[0]; off = 0.4
        else: path, c = files[i % k]; off = cur.take(c, fr[i])
        segs.append((path, off)); ov = f"{work}/card{i}.png"
        if i == 0: render.card(ov, hook="This place doesn't look real", hook2="But it is.", label=pl["label"])
        elif i == 1: render.card(ov, label=pl["label"])
        elif i <= 6: render.card(ov, fact=pl["f1"])
        elif i <= 11: render.card(ov, fact=pl["f2"])
        else: render.card(ov, cta="Would you go here?")
        ovs.append(ov)
    log("hook: This place doesn't look real |", pl["label"])
    out = f"{work}/../video.mp4"; render.build_seq_video(segs, ovs, out, work, seed=ep, log=log, hd=True)
    short = pl["label"].split(",")[0]; emo = ["😱", "🤯", "😍"][ep % 3]
    title = f"{short} doesn't look real {emo} #{pl['tag']} #travel #nature #earth"
    credits = sorted({c["credit"] for _, c in files})
    desc = (f"{pl['label']}: {pl['f1']}. {pl['f2']}.\nWould you go here? Tell me in the comments 👇\n\n"
            f"Footage: {', '.join(credits)} via Pexels and Pixabay (licensed stock footage, edited by Dreamy Earth).\n{music_line()}\n"
            f"Follow for real places that look unreal.\n{FOOTER} #{pl['tag']}")
    tags = [short, pl["label"], "places on earth that don't feel real", "unreal places", "travel", "nature", "beautiful places"]
    rec = [{"place": pl["label"], "clips": [{"src": c["src"], "id": c["id"], "page": c["page"], "author": c["credit"]} for _, c in files]}]
    return dict(out=out, title=title, desc=desc, tags=tags, synthetic=False, rec=rec, theme=pl["label"])

def fmt_dream(ep, work):
    """Dreamworld: one invented, named place per episode, with lore. Always labeled AI-generated."""
    acc, tok = env("CF_ACCOUNT_ID"), env("CF_API_TOKEN")
    epn = (ep // 3) // 2 + 1; name, prompts, lore = dreamworld.episode(epn - 1); segs = []; ovs = []
    for i, pr in enumerate(prompts):
        img = cf_images.generate(acc, tok, pr); segs.append((render.image_to_clip(img, f"{work}/dw{i}.mp4", work, i), 0.0)); log(f"image {i+1}/13 ok")
    for i in range(13):
        ov = f"{work}/card{i}.png"; b = "AI-generated"; sz = (render.W, render.H)
        if i == 0: render.card(ov, badge=b, hook=f"Dreamworld #{epn}", hook2=name, out_size=sz)
        elif i <= 4: render.card(ov, badge=b, fact=lore[0], out_size=sz)
        elif i <= 8: render.card(ov, badge=b, fact=lore[1], out_size=sz)
        elif i <= 11: render.card(ov, badge=b, fact=lore[2], out_size=sz)
        else: render.card(ov, badge=b, cta="Would you visit?", out_size=sz)
        ovs.append(ov)
    out = f"{work}/../video.mp4"; render.build_seq_video(segs, ovs, out, work, seed=ep, log=log, hd=False)
    title = f"Dreamworld #{epn}: {name} ✨ (AI art) #AIart #fantasy #dreamy #shorts"
    desc = (f"Dreamworld #{epn}: {name}. An imaginary place from Dreamworld, an AI art series by Dreamy Earth.\n"
            f"{lore[0]}. {lore[1]}. {lore[2]}.\nWould you visit? Tell me in the comments 👇\n\n"
            f"This place does not exist: all visuals are AI-generated (Flux) from our own descriptions.\n{music_line()}\n"
            "#AIart #fantasy #dreamworld #aiartwork #shorts")
    tags = ["dreamworld", "ai art", "fantasy world", "dream places", "imaginary places", name]
    return dict(out=out, title=title, desc=desc, tags=tags, synthetic=True, rec=[{"dreamworld": epn, "name": name}], theme="AI dream places")

def fmt_choice(ep, work):
    acc, tok = env("CF_ACCOUNT_ID"), env("CF_API_TOKEN")
    ch = aiplaces.pick_choices(ep, 4); imgs = []
    for i, (nm, pr) in enumerate(ch):
        imgs.append(cf_images.generate(acc, tok, pr)); log(f"choice image {i+1}/4 ok")
    out = f"{work}/../video.mp4"; render.build_choice_video(imgs, [n for n, _ in ch], out, work, seed=ep, log=log)
    title = "Which place would you stay in? 🤔 #AIart #travel #dreamplaces #nature"
    desc = ("Which place would you stay in? Comment your number 👇\n\n" + "\n".join(f"{i + 1}. {n}" for i, (n, _) in enumerate(ch)) +
            f"\n\nAll visuals are AI-generated and are not real places.\n{music_line()}\n#AIart #dreamplaces #shorts")
    return dict(out=out, title=title, desc=desc, tags=["which place would you stay in", "ai art", "dream places", "would you rather"],
                synthetic=True, rec=[{"choice": [n for n, _ in ch]}], theme=", ".join(n for n, _ in ch))

def fmt_long(ep, work, n_target=20, dry=False):
    """Weekly 16:9 long video: N named real places, ~25 s each, name + two facts on screen, chapters in the description."""
    W = ep // 3; order = places.order(303); n = len(order); fps = 25; seg_f = 208   # W = days since start; 3 x 8.3 s per place
    intro_f = 250; got = []; segs = []; cur = Cursor(); os.makedirs(work, exist_ok=True)
    for j in range(n):
        if len(got) >= n_target: break
        pl = places.PLACES[order[(W * 7 + j) % n]]
        cl = [c for c in stock.place_clips(pl, 4, log, seed=ep + j, wide=True) if c["dur"] >= 7][:4]
        files = []
        for i, c in enumerate(cl):
            if len(files) >= 2: break
            try: files.append((_download(c, f"{work}/L{len(got)}_{i}.mp4"), c))
            except Exception as ex: log(f"  download failed: {str(ex)[:80]}")
        if not files: continue
        k = len(got) + 1; got.append((pl, files))
        if k == 1:   # intro on the first place's footage
            ov = f"{work}/Lintro.png"; render.card_wide(ov, title="Real Places That Don't Feel Real", title2="Every one of them is real. Here is where they are.")
            p0, c0 = files[0]; first_raw = (p0, c0); segs.append(render.wide_segment(p0, cur.take(c0, intro_f, fps), intro_f, ov, f"{work}/W000.mp4"))
        for si in range(3):
            path, c = files[si % len(files)]; ov = f"{work}/Lc{k}_{si}.png"
            if si == 0: render.card_wide(ov, label=pl["label"], num=k)
            else: render.card_wide(ov, fact=pl["f1"] if si == 1 else pl["f2"])
            segs.append(render.wide_segment(path, cur.take(c, seg_f, fps), seg_f, ov, f"{work}/W{k:02d}{si}.mp4"))
        for pth, _ in files[(1 if k == 1 else 0):]:   # keep place 1's main clip for the outro and thumbnail
            try: os.remove(pth)
            except OSError: pass
        log(f"long: place {k}/{n_target} {pl['label']} done")
    m = len(got)
    if m < (3 if dry else 12): return None
    # outro: back to place 1 with a question
    pl1, _ = got[0]; ov = f"{work}/Lout.png"; render.card_wide(ov, title="Which one would you visit first?", title2="Tell me in the comments. New places every day.")
    segs.append(render.wide_segment(first_raw[0], 0.4, 200, ov, f"{work}/W999.mp4"))
    dur = (intro_f + 3 * seg_f * m + 200) / fps
    lst = f"{work}/Wlist.txt"; open(lst, "w").write("".join(f"file '{os.path.abspath(x)}'\n" for x in segs))
    tracks = []
    try:
        from src import music
        for f in music.lib_list()[:10]:
            dst = f"{work}/LT_{f['name']}"; open(dst, "wb").write(__import__("requests").get(f["download_url"], timeout=60).content); tracks.append(dst)
    except Exception as ex: log("long music library skipped:", str(ex)[:100])
    wav = f"{work}/Lmusic.wav"; render.long_music(wav, dur, tracks, work, seed=ep, log=log)
    out = f"{work}/../long.mp4"
    render.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", lst, "-i", wav, "-map", "0:v", "-map", "1:a",
                "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", out])
    def ts(sec): sec = int(sec); return f"{sec // 60}:{sec % 60:02d}"
    chap = ["0:00 Intro"] + [f"{ts((intro_f + 3 * seg_f * i) / fps)} {i + 1}. {p['label']}" for i, (p, _) in enumerate(got)] + [f"{ts((intro_f + 3 * seg_f * m) / fps)} Which one would you visit?"]
    facts = "\n".join(f"{i + 1}. {p['label']}: {p['f1']}. {p['f2']}." for i, (p, _) in enumerate(got))
    credits = sorted({c["credit"] for _, fs in got for _, c in fs})
    title = f"{m} Real Places That Don't Feel Real 🌍 Nature & Travel"
    desc = (f"{m} places on Earth that don't feel real, but every one of them is real. Each place is named on screen with two quick facts.\n\n"
            "Chapters:\n" + "\n".join(chap) + f"\n\nThe places:\n{facts}\n\n"
            f"Footage: {', '.join(credits[:25])} via Pexels and Pixabay (licensed stock footage, edited by Dreamy Earth).\n{music_line()}\n"
            "Which one would you visit first? Tell me in the comments.\n#travel #nature #placesthatdontfeelreal #beautifulplaces #earth")
    thumb = None
    try:
        thumb = render.thumbnail(first_raw[0], 2.0, f"{m} REAL PLACES", "that don't feel real", f"{work}/thumb.jpg", work)
    except Exception as ex: log("thumbnail failed:", str(ex)[:100])
    tags = ["places on earth that don't feel real", "real places that look fake", "most beautiful places on earth", "travel", "nature", "relaxing"] + [p["label"].split(",")[0] for p, _ in got[:8]]
    rec = [{"place": p["label"], "clips": [{"src": c["src"], "id": c["id"], "page": c["page"], "author": c["credit"]} for _, c in fs]} for p, fs in got]
    log(f"long video: {m} places, {dur:.0f} s")
    return dict(out=out, title=title, desc=desc, tags=tags, synthetic=False, rec=rec, theme="long", thumb=thumb)

def fmt_generic(ep, work):
    """Old mixed-stock format, used only if named-place footage can't be found."""
    names, clips = stock.pick_multi(ep, 18, log); files = []
    for i, c in enumerate(clips):
        if len(files) >= 13: break
        try: files.append(stock.download(c, f"{work}/g{i}.mp4"))
        except Exception as ex: log(f"download {i} failed: {str(ex)[:80]}")
    if len(files) < 9: return None
    seq = files[:12] + [files[0]]; rr = random.Random(ep)
    caps = {3: rr.choice(aiplaces.FEEL_MID), len(seq) - 1: rr.choice(aiplaces.FEEL_END)}
    out = f"{work}/../video.mp4"
    render.build_beat_video2(seq, ("Places on Earth that don't feel real", "Wait for the last one"), caps, None, out, work, seed=ep, log=log, hd=True)
    credits = sorted({c["credit"] for c in clips})
    desc = (f"Beautiful places on Earth. Which one is your favorite? 👇\nFeaturing: {', '.join(names[:4])}.\n"
            f"Footage: {', '.join(credits[:8])} via Pexels and Pixabay (licensed stock footage, edited by Dreamy Earth).\n{music_line()}\n{FOOTER}")
    return dict(out=out, title="Beautiful places on Earth 😍 #travel #nature #earth #places", desc=desc,
                tags=["beautiful places", "travel", "nature", "scenery"], synthetic=False,
                rec=[{"clips": [{"src": c["src"], "id": c["id"], "author": c["credit"]} for c in clips[:13]]}], theme=", ".join(names[:4]))

def place_scan():
    tot = 0
    for pl in places.PLACES:
        cl = stock.place_clips(dict(pl, q=pl["q"][:1]), 99, log)
        p = sum(1 for c in cl if c["h"] > c["w"]); tot += 1 if len(cl) >= 3 else 0
        log(f"SCAN {pl['label']}: {len(cl)} clips ({p} portrait, {sum(1 for c in cl if c['src']=='pixabay')} pixabay)")
    log(f"SCAN summary: {tot}/{len(places.PLACES)} places have >=3 clips")

def save_record(vid, data):
    try:
        from src import music
        music._put(f"licenses/{datetime.datetime.utcnow():%Y%m%d_%H%M}_{vid}.json",
                   json.dumps({"video": vid, "title": data["title"], "music": os.path.basename(str(render.MUSIC_SRC or "built-in synth")),
                               "items": data["rec"]}, ensure_ascii=False, indent=1).encode(), f"license record {vid}")
    except Exception as ex: log("license record failed:", str(ex)[:120])

def main(mode):
    ep, k, in_slot = slot_info()
    acc, tok = env("CF_ACCOUNT_ID"), env("CF_API_TOKEN")
    log("cloudflare verify:", *cf_images.verify(acc, tok))
    if mode == "analyze":
        vids = yt.my_videos_stats(_yt()); w, summ, top = analyze.run(vids, [t[0] for t in stock.THEMES]); log("ANALYSIS:", summ)
        for v in vids[:20]: log(f"  {v['id']} views={v['views']} likes={v['likes']} | {v['title'][:50]}")
        return
    if mode == "placescan": return place_scan()
    if mode == "check": mode = "dry_list"
    dry = mode.startswith("dry_"); fmode = mode[4:] if dry else mode
    if mode == "run":
        try:
            mins, n24 = yt.upload_stats(_yt())
            if mins is not None and mins < 150: log(f"SKIP: last upload {mins:.0f} min ago (slot already done)"); return
            if is_long_slot(): mode = "long"
            elif not in_slot and mins is not None and mins < 450: log(f"SKIP: not an upload slot (last upload {mins:.0f} min ago)"); return
            if n24 >= 10: log(f"SKIP: already {n24} uploads in last 24h (safety cap)"); return
        except Exception as ex: log("upload-guard check failed, continuing:", str(ex)[:120])
    try:
        vids = yt.my_videos_stats(_yt()); _, summ, top = analyze.run(vids, [t[0] for t in stock.THEMES])
        log("ANALYSIS:", summ); [log("  top:", t) for t in top]
    except Exception as ex: log("analysis skipped:", str(ex)[:120])
    try:
        from src import music
        if not dry: music.maybe_generate_daily(log)
        render.MUSIC_SRC = music.pick_track(ep, "out/work", log)
    except Exception as ex: log("music step skipped:", str(ex)[:120]); render.MUSIC_SRC = None
    if mode == "long": fmode = "long"
    if fmode == "run": fmode = ["list", "single", "dream" if (ep // 3) % 2 == 0 else "choose"][k]
    fmode = {"ai": "dream"}.get(fmode, fmode)
    log(f"slot ep={ep} k={k} format={fmode}" + (" (dry run)" if dry else ""))
    work = "out/work"; os.makedirs(work, exist_ok=True)
    fn = {"list": fmt_list, "single": fmt_single, "dream": fmt_dream, "choose": fmt_choice, "long": fmt_long}[fmode]
    data = fmt_long(ep, work, n_target=3, dry=True) if (fmode == "long" and dry) else fn(ep, work)
    if data is None and fmode in ("list", "single"):
        log(f"{fmode}: not enough named-place footage, trying the other real format")
        data = (fmt_single if fmode == "list" else fmt_list)(ep, work) or fmt_generic(ep, work)
    if data is None and fmode == "long": log("long: not enough wide footage, skipping this week"); return
    if data is None: raise RuntimeError("no footage for any format")
    log("video built", os.path.getsize(data["out"]), "bytes |", data["title"])
    if dry:
        from src import music
        if os.path.getsize(data["out"]) < 45 * 1048576: music._put(f"previews/{fmode}.mp4", open(data["out"], "rb").read(), f"preview {fmode}")
        else: log("preview too big for GitHub, video file not saved")
        music._put(f"previews/{fmode}.txt", (data["title"] + "\n\n" + data["desc"]).encode(), f"preview {fmode} text")
        log("preview saved to music-library/previews/"); return
    vid, privacy = yt.upload(_yt(), data["out"], data["title"], data["desc"], data["tags"][:15], synthetic=data["synthetic"])
    log("uploaded:", vid, "privacy:", privacy, "| title:", data["title"])
    if privacy != "public": log("WARNING: upload is not public:", privacy)
    if data.get("thumb"):
        try: log("thumbnail:", yt.set_thumbnail(_yt(), vid, data["thumb"]))
        except Exception as ex: log("thumbnail set failed:", str(ex)[:120])
    pl = PLAYLISTS.get(fmode)
    if pl:
        try: yt.add_to_playlist(_yt(), vid, *pl); log("playlist:", pl[0])
        except Exception as ex: log("playlist add failed:", str(ex)[:120])
    save_record(vid, data)

def do_brand():
    from src import art
    access = _yt(); os.makedirs("out", exist_ok=True); art.banner("out/banner.png")
    desc = ("Dreamy Earth: real places on Earth that look unreal, in short videos.\n"
            "Every real-place video names the place and shares a quick fact. Footage is licensed stock video (Pexels, Pixabay), "
            "credited in each description and edited by us. Music is original.\n"
            "Dreamworld is our AI art series of imaginary places: every episode is clearly labeled AI-generated.\n"
            "New videos every day. Subscribe and tell us which place you'd visit!")
    kw = 'travel nature "places on earth" "real places" scenery "beautiful places" dreamworld shorts'
    res = yt.brand(access, desc, kw, "out/banner.png"); log("brand:", res); return res
import threading
RUN_LOCK = threading.Lock()
def execute(mode="run"):
    if not RUN_LOCK.acquire(blocking=False):   # never two jobs at once (memory: free instance has 512 MB)
        print(f"busy: '{mode}' ignored, another job is running", flush=True); return "busy"
    try: return _execute(mode)
    finally: RUN_LOCK.release()
def _execute(mode="run"):
    lines.clear()
    try:
        if mode == "musictest":
            from src import music; music.test(log)
        elif mode == "brand": do_brand()
        else: main(mode)
        log("RESULT: OK")
    except BaseException as e:
        log("RESULT: FAIL", type(e).__name__, str(e)[:500]); log(traceback.format_exc()[-600:])
    finally:
        save()
    return "\n".join(lines)
if __name__ == "__main__":
    execute(sys.argv[1] if len(sys.argv) > 1 else "run")
