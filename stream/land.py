"""Landscape stock footage (Pexels/Pixabay) for the live stream loop."""
import os, random, requests
QUERIES = ["autumn forest", "cherry blossom", "snowy forest", "waterfall", "lavender field", "turquoise water aerial", "sea of clouds mountain",
           "bamboo forest", "sand dunes", "northern lights", "mountain lake", "rice terraces", "ocean waves sunset", "green meadow drone", "foggy forest"]
def _pexels(key, q, rnd):
    r = requests.get("https://api.pexels.com/videos/search", headers={"Authorization": key},
                     params={"query": q, "orientation": "landscape", "size": "large", "per_page": 30}, timeout=40)
    r.raise_for_status(); out = []
    for v in r.json().get("videos", []):
        if v.get("duration", 0) < 8: continue
        fs = [f for f in v.get("video_files", []) if f.get("file_type") == "video/mp4" and 1280 <= (f.get("width") or 0) <= 1920 and (f.get("height") or 0) >= 720]
        if fs:
            f = min(fs, key=lambda x: x["width"] * x["height"]); out.append({"id": f"px{v['id']}", "url": f["link"], "credit": (v.get("user") or {}).get("name", "Pexels")})
    rnd.shuffle(out); return out
def _pixabay(key, q, rnd):
    r = requests.get("https://pixabay.com/api/videos/", params={"key": key, "q": q, "per_page": 30, "safesearch": "true"}, timeout=40)
    r.raise_for_status(); out = []
    for h in r.json().get("hits", []):
        if h.get("duration", 0) < 8: continue
        v = h["videos"].get("medium") or h["videos"].get("large")
        if v and v.get("url") and (v.get("width") or 0) >= 1280: out.append({"id": f"pb{h['id']}", "url": v["url"], "credit": h.get("user", "Pixabay")})
    rnd.shuffle(out); return out
def pick(n, seed, log=print):
    rnd = random.Random(seed); px, pb = os.environ.get("PEXELS_API_KEY", ""), os.environ.get("PIXABAY_API_KEY", "")
    out, seen = [], set(); qs = QUERIES[:]; rnd.shuffle(qs)
    for q in qs * 3:
        if len(out) >= n: break
        for fn, key in ((_pexels, px), (_pixabay, pb)):
            if not key or len(out) >= n: continue
            try: res = fn(key, q, rnd)
            except Exception as e: log(f"stock '{q}' failed: {str(e)[:90]}"); continue
            for c in res[:2]:
                if c["id"] not in seen and len(out) < n: seen.add(c["id"]); out.append(c)
    return out
def download(c, path, max_mb=60):
    with requests.get(c["url"], stream=True, timeout=120) as r:
        r.raise_for_status()
        if int(r.headers.get("Content-Length", 0)) > max_mb * 1048576: raise RuntimeError("too large")
        with open(path, "wb") as f:
            for ch in r.iter_content(1 << 20): f.write(ch)
    return path
