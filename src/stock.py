import os, random, requests
THEMES = [
 ("Autumn Forest Road", ["autumn forest road", "golden autumn trees", "fall foliage road"]),
 ("Cherry Blossom Paradise", ["cherry blossom", "sakura trees petals", "pink blossoms spring"]),
 ("Frozen Winter Forest", ["snowy forest", "frost trees winter", "winter forest aerial"]),
 ("Hidden Waterfalls", ["waterfall forest", "waterfall aerial", "waterfall canyon"]),
 ("Lavender Fields", ["lavender field", "purple flowers field sunset"]),
 ("Turquoise Lagoons", ["turquoise water aerial", "tropical lagoon", "island aerial"]),
 ("Above The Clouds", ["mountain clouds sunrise", "sea of clouds", "mountain peaks aerial"]),
 ("Misty Bamboo Forest", ["bamboo forest", "misty forest sunrise", "forest light rays"]),
 ("Red Desert Dunes", ["sand dunes", "desert sunset aerial", "canyon desert"]),
 ("Northern Lights", ["aurora borealis", "northern lights sky"]),
 ("Mountain Lakes", ["mountain lake reflection", "alpine lake aerial"]),
 ("Terraced Fields", ["rice terraces", "green fields aerial"]),
]
TITLES = ["Places on Earth That Don't Feel Real", "Places on Earth That Look Unreal", "Most Beautiful Places on Earth", "Unreal Places That Actually Exist", "Places on Earth That Don't Feel Real"]
def _pexels(key, q, rnd):
    r = requests.get("https://api.pexels.com/videos/search", headers={"Authorization": key},
                     params={"query": q, "orientation": "portrait", "size": "large", "per_page": 30}, timeout=40)
    r.raise_for_status(); out = []
    for v in r.json().get("videos", []):
        if v.get("duration", 0) < 5: continue
        files = [f for f in v.get("video_files", []) if f.get("file_type") == "video/mp4" and (f.get("height") or 0) >= 1280 and (f.get("width") or 0) <= 1440]
        if not files: continue
        f = min(files, key=lambda x: (0 if (x["height"] or 0) >= 1920 else 1, (x["width"] or 0) * (x["height"] or 0)))
        out.append({"id": f"px{v['id']}", "url": f["link"], "credit": (v.get("user") or {}).get("name", "Pexels")})
    rnd.shuffle(out); return out
def _pixabay(key, q, rnd):
    r = requests.get("https://pixabay.com/api/videos/", params={"key": key, "q": q, "per_page": 30, "safesearch": "true"}, timeout=40)
    r.raise_for_status(); out = []
    for h in r.json().get("hits", []):
        if h.get("duration", 0) < 5: continue
        v = h["videos"].get("medium") or h["videos"].get("small")
        if v and v.get("url"): out.append({"id": f"pb{h['id']}", "url": v["url"], "credit": h.get("user", "Pixabay")})
    rnd.shuffle(out); return out
def pick_clips(theme_idx, day, n, log=print):
    name, queries = THEMES[theme_idx % len(THEMES)]; rnd = random.Random(day)
    pexels, pixabay = os.environ.get("PEXELS_API_KEY", ""), os.environ.get("PIXABAY_API_KEY", "")
    chosen, seen = [], set()
    for q in queries * 2:
        for src, key in (("pexels", pexels), ("pixabay", pixabay)):
            if not key or len(chosen) >= n: continue
            try:
                res = (_pexels if src == "pexels" else _pixabay)(key, q, rnd)
            except Exception as e:
                log(f"{src} '{q}' failed: {str(e)[:120]}"); continue
            for c in res:
                if c["id"] not in seen and len(chosen) < n:
                    seen.add(c["id"]); chosen.append(dict(c, src=src))
                    break
        if len(chosen) >= n: break
    log(f"stock clips: {len(chosen)} ({', '.join(c['src'] for c in chosen)})")
    return name, chosen
def download(c, path):
    with requests.get(c["url"], stream=True, timeout=90) as r:
        r.raise_for_status()
        with open(path, "wb") as f:
            for chunk in r.iter_content(1 << 20): f.write(chunk)
    return path

HOOK_QUERIES = ["woman arms wide nature", "person standing looking at mountain view", "woman walking autumn forest", "girl in flower field", "person overlooking valley"]
GENERIC = ["colorful landscape aerial", "vibrant nature drone", "scenic road aerial", "unreal landscape"]
def pick_multi(day, n, log=print, max_mb=30, weights=None):
    rnd = random.Random(day * 7 + 3)
    pexels, pixabay = os.environ.get("PEXELS_API_KEY", ""), os.environ.get("PIXABAY_API_KEY", "")
    out, seen, names = [], set(), []
    def grab(q, take):
        got = 0
        for src, key in (("pexels", pexels), ("pixabay", pixabay)):
            if not key or got >= take: continue
            try: res = (_pexels if src == "pexels" else _pixabay)(key, q, rnd)
            except Exception as e: log(f"{src} '{q}' failed: {str(e)[:100]}"); continue
            for c in res:
                if c["id"] not in seen and got < take:
                    seen.add(c["id"]); out.append(dict(c, src=src, q=q)); got += 1
        return got
    grab(rnd.choice(HOOK_QUERIES), 1)
    idx = list(range(len(THEMES))); order = []
    w = {i: (weights or {}).get(THEMES[i][0], 1.0) for i in idx}
    while idx:  # weighted random order: better themes come first more often
        pick = rnd.choices(idx, weights=[w[i] for i in idx])[0]; order.append(pick); idx.remove(pick)
    for ti in order:
        if len(out) >= n: break
        name, qs = THEMES[ti]
        if grab(rnd.choice(qs), 3): names.append(name)
    for q in GENERIC:
        if len(out) >= n: break
        grab(q, 3)
    log(f"stock clips: {len(out)} themes: {', '.join(names)}")
    return names, out[:n]
def download(c, path, max_mb=80):
    with requests.get(c["url"], stream=True, timeout=90) as r:
        r.raise_for_status()
        if int(r.headers.get("Content-Length", 0)) > max_mb * 1048576: raise RuntimeError("clip too large")
        with open(path, "wb") as f:
            for chunk in r.iter_content(1 << 20): f.write(chunk)
    return path

# ---------------- place-matched clips (label must match the footage) ----------------
def _best_pexels_file(v):
    fs = [f for f in v.get("video_files", []) if f.get("file_type") == "video/mp4" and f.get("width") and f.get("height")]
    por = [f for f in fs if f["height"] > f["width"] and f["height"] >= 1280]
    if por: return min(por, key=lambda f: (0 if f["height"] >= 1920 else 1, f["width"] * f["height"]))
    lan = [f for f in fs if f["width"] >= f["height"] and f["height"] >= 1440]   # 9:16 crop of >=1440p keeps detail
    if lan: return min(lan, key=lambda f: f["width"] * f["height"])
    return None
def _best_pexels_wide(v):
    fs = [f for f in v.get("video_files", []) if f.get("file_type") == "video/mp4" and f.get("width") and f.get("height")]
    lan = [f for f in fs if f["width"] > f["height"] and 1920 <= f["width"] <= 2560]
    return min(lan, key=lambda f: f["width"] * f["height"]) if lan else None
def _slug(url):
    return (url or "").rstrip("/").split("/")[-1]
def place_clips(place, need, log=print, seed=0, wide=False):
    from .places import matches
    rnd = random.Random(seed); pexels, pixabay = os.environ.get("PEXELS_API_KEY", ""), os.environ.get("PIXABAY_API_KEY", "")
    out, seen = [], set()
    for q in place["q"]:
        if len(out) >= need: break
        if pexels:
            try:
                r = requests.get("https://api.pexels.com/videos/search", headers={"Authorization": pexels},
                                 params={"query": q, "per_page": 40, "size": "large"}, timeout=40); r.raise_for_status()
                for v in r.json().get("videos", []):
                    if v.get("duration", 0) < 5 or f"px{v['id']}" in seen or not matches(place, _slug(v.get("url"))): continue
                    f = _best_pexels_wide(v) if wide else _best_pexels_file(v)
                    if not f: continue
                    seen.add(f"px{v['id']}")
                    out.append({"id": f"px{v['id']}", "url": f["link"], "credit": (v.get("user") or {}).get("name", "Pexels"), "page": v.get("url"),
                                "src": "pexels", "dur": float(v.get("duration") or 8), "w": f["width"], "h": f["height"]})
            except Exception as e: log(f"pexels '{q}' failed: {str(e)[:100]}")
        if pixabay and len(out) < need:
            try:
                r = requests.get("https://pixabay.com/api/videos/", params={"key": pixabay, "q": q, "per_page": 50, "safesearch": "true"}, timeout=40); r.raise_for_status()
                for h in r.json().get("hits", []):
                    if h.get("duration", 0) < 5 or f"pb{h['id']}" in seen or not matches(place, h.get("tags", "")): continue
                    best = None
                    for k in (("medium", "large") if wide else ("large", "medium")):
                        v = h["videos"].get(k) or {}
                        w, hh = v.get("width") or 0, v.get("height") or 0
                        # long-form: 1080p-1440p only (4K decode on the free 512 MB instance runs out of memory)
                        ok = (w > hh and 1920 <= w <= 2560) if wide else ((hh > w and hh >= 1280) or (w >= hh and hh >= 1440))
                        if v.get("url") and ok: best = v; break
                    if not best: continue
                    seen.add(f"pb{h['id']}")
                    out.append({"id": f"pb{h['id']}", "url": best["url"], "credit": h.get("user", "Pixabay"), "page": h.get("pageURL"),
                                "src": "pixabay", "dur": float(h.get("duration") or 8), "w": best["width"], "h": best["height"]})
            except Exception as e: log(f"pixabay '{q}' failed: {str(e)[:100]}")
    rnd.shuffle(out)
    if wide: out.sort(key=lambda c: -c["dur"])                 # long-form: longest clips first
    else: out.sort(key=lambda c: 0 if c["h"] > c["w"] else 1)  # Shorts: portrait first (no crop needed)
    return out
