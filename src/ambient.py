"""Relaxing nature Shorts (~1 min): a few slow licensed stock clips (Pexels/Pixabay) + nature ambience that we synthesize ourselves
(rain, stream, waves, wind) + a very soft pad. No on-screen text. The sound is synthetic and the description says so."""
import os, random, subprocess, wave
import numpy as np, requests

SCENES = [
    dict(key="rain", title="Rain in a quiet forest", emo="🌧️", q=["rain forest", "rainy forest", "rain in forest", "rain on leaves"], must=["rain"], sound="rain", tag="rain"),
    dict(key="lake", title="Misty mountain lake at dawn", emo="🌫️", q=["misty lake", "foggy lake mountains", "lake fog morning", "mist mountains lake"], must=["mist", "fog", "lake"], sound="lake", tag="mistylake"),
    dict(key="river", title="Mountain river in a green valley", emo="🏞️", q=["mountain river", "river valley green", "stream rocks forest", "creek forest"], must=["river", "stream", "creek"], sound="stream", tag="river"),
    dict(key="waterfall", title="Waterfall deep in the forest", emo="💧", q=["waterfall forest", "waterfall", "waterfall jungle"], must=["waterfall", "cascade"], sound="stream", tag="waterfall"),
    dict(key="ocean", title="Ocean waves at golden hour", emo="🌊", q=["ocean waves sunset", "sea waves", "waves beach", "waves rocks"], must=["wave", "ocean", "sea", "surf"], sound="ocean", tag="ocean"),
    dict(key="snow", title="Snowfall in a silent forest", emo="❄️", q=["snowfall forest", "snow falling trees", "winter forest snow", "snowy forest"], must=["snow", "winter"], sound="wind", tag="snowfall"),
]
SEG_S, TOTAL_S = 14.0, 58.0

def scene_for(ep): return SCENES[(ep // 2) % len(SCENES)]

def _ok(scene, text): t = (text or "").lower(); return any(k in t for k in scene["must"])

def clips(scene, need, log=print, seed=0):
    """Slow nature clips for the scene: >= 9 s, portrait 1280-2560 px or landscape >= 1440 p (9:16 crop keeps detail)."""
    from .stock import _best_pexels_file, _slug
    rnd = random.Random(seed); px, pb = os.environ.get("PEXELS_API_KEY", ""), os.environ.get("PIXABAY_API_KEY", ""); out, seen = [], set()
    for q in scene["q"]:
        if len(out) >= need * 3: break
        if px:
            try:
                r = requests.get("https://api.pexels.com/videos/search", headers={"Authorization": px}, params={"query": q, "per_page": 40, "size": "large"}, timeout=40); r.raise_for_status()
                for v in r.json().get("videos", []):
                    if v.get("duration", 0) < 9 or f"px{v['id']}" in seen or not _ok(scene, _slug(v.get("url"))): continue
                    f = _best_pexels_file(v)
                    if not f: continue
                    seen.add(f"px{v['id']}")
                    out.append({"id": f"px{v['id']}", "url": f["link"], "credit": (v.get("user") or {}).get("name", "Pexels"), "page": v.get("url"), "src": "pexels",
                                "dur": float(v["duration"]), "w": f["width"], "h": f["height"]})
            except Exception as e: log(f"pexels '{q}' failed: {str(e)[:100]}")
        if pb:
            try:
                r = requests.get("https://pixabay.com/api/videos/", params={"key": pb, "q": q, "per_page": 50, "safesearch": "true"}, timeout=40); r.raise_for_status()
                for h in r.json().get("hits", []):
                    if h.get("duration", 0) < 9 or f"pb{h['id']}" in seen or not _ok(scene, h.get("tags", "")): continue
                    best = None
                    for k in ("large", "medium"):
                        v = h["videos"].get(k) or {}; w, hh = v.get("width") or 0, v.get("height") or 0
                        if v.get("url") and ((hh > w and 1280 <= hh <= 2560) or (w >= hh and hh >= 1440 and w <= 2560)): best = v; break
                    if not best: continue
                    seen.add(f"pb{h['id']}")
                    out.append({"id": f"pb{h['id']}", "url": best["url"], "credit": h.get("user", "Pixabay"), "page": h.get("pageURL"), "src": "pixabay",
                                "dur": float(h["duration"]), "w": best["width"], "h": best["height"]})
            except Exception as e: log(f"pixabay '{q}' failed: {str(e)[:100]}")
    rnd.shuffle(out); out.sort(key=lambda c: 0 if c["h"] > c["w"] else 1)
    return out

# ---------------- sound ----------------
SR = 22050   # half rate keeps RAM low on the free 512 MB instance; ffmpeg resamples to 44.1 kHz
def _shaped(n, rng, lo, hi, tilt=0.0):
    """Noise band-limited to [lo, hi] Hz with a 1/f^tilt slope (0 = white, 1 = pink)."""
    x = rng.standard_normal(n); X = np.fft.rfft(x); f = np.fft.rfftfreq(n, 1 / SR)
    g = np.where((f >= lo) & (f <= hi), 1.0, 0.0) / np.maximum(f, 20) ** tilt
    g *= np.clip((f - lo) / max(lo * 0.3, 1), 0, 1) * np.clip((hi - f) / max(hi * 0.3, 1), 0, 1) if hi > lo else 1
    y = np.fft.irfft(X * g, n); return y / (np.abs(y).max() + 1e-9)
def _env(n, rng, rate, depth, smooth=1.0):
    """Slow random loudness movement around 1.0."""
    k = max(2, int(n / SR * rate) + 2); pts = rng.uniform(1 - depth, 1, k)
    return np.interp(np.linspace(0, k - 1, n), np.arange(k), pts)
def _drops(n, rng, per_s, lo, hi):
    """Sparse droplet ticks: short band-passed bursts at random times."""
    imp = np.zeros(n); t = rng.uniform(0, n - 1, int(n / SR * per_s)).astype(int); imp[t] = rng.uniform(0.2, 1.0, len(t))
    k = int(0.012 * SR); kern = _shaped(k, rng, lo, hi) * np.exp(-np.arange(k) / (0.003 * SR))
    return np.fft.irfft(np.fft.rfft(imp) * np.fft.rfft(kern, n), n)
def _channel(kind, n, rng):
    if kind == "rain":
        a = _shaped(n, rng, 600, 9000, 0.4) * 0.55 * _env(n, rng, 0.15, 0.25) + _drops(n, rng, 90, 2500, 9000) * 0.9 + _shaped(n, rng, 40, 250, 1) * 0.25
    elif kind == "stream":
        a = _shaped(n, rng, 250, 6500, 0.3) * (0.55 + 0.45 * _env(n, rng, 2.5, 0.8)) + _shaped(n, rng, 900, 3500, 0.2) * 0.35 * _env(n, rng, 6, 0.9)
    elif kind == "ocean":
        t = np.arange(n) / SR; ph = rng.uniform(0, 6)
        swell = (0.5 + 0.5 * np.sin(2 * np.pi * t / 10.5 + ph)) ** 2.2 * 0.8 + 0.2
        a = _shaped(n, rng, 120, 2600, 0.7) * swell + _shaped(n, rng, 3000, 9000, 0.2) * 0.12 * swell ** 3
    elif kind == "wind":
        a = _shaped(n, rng, 80, 1100, 0.8) * (0.35 + 0.65 * _env(n, rng, 0.12, 0.9)) + _shaped(n, rng, 40, 200, 1) * 0.2
    else:                                           # lake: faint wind + soft lapping
        t = np.arange(n) / SR
        a = _shaped(n, rng, 80, 900, 0.8) * (0.3 + 0.5 * _env(n, rng, 0.1, 0.9)) + _shaped(n, rng, 200, 2200, 0.8) * 0.18 * (0.5 + 0.5 * np.sin(2 * np.pi * t / 6.5 + rng.uniform(0, 6))) ** 2
    return a
def _pad(n, rng, seed):
    t = np.arange(n) / SR; chords = [[110, 164.81, 220], [87.31, 130.81, 174.61], [130.81, 196, 261.63], [98, 146.83, 196]]; pad = np.zeros(n); seg = int(SR * 8)
    for i, a0 in enumerate(range(0, n, seg)):
        a1 = min(n, a0 + seg + SR); tt = t[a0:a1] - t[a0]; env = np.minimum(tt / 3, 1) * np.minimum((tt[-1] - tt) / 3, 1).clip(0)
        for f in chords[(i + seed) % 4]: pad[a0:a1] += np.sin(2 * np.pi * f * tt + rng.uniform(0, 6)) * env
    return pad / (np.abs(pad).max() + 1e-9)
def make_sound(path, dur, kind, seed=0):
    n = int(SR * dur); rng = np.random.default_rng(seed + 1000)
    ch = []
    for _ in range(2): ch.append(_channel(kind, n, rng))
    pad = _pad(n, rng, seed); st = np.stack([ch[0] / (np.abs(ch[0]).max() + 1e-9) + pad * 0.10, ch[1] / (np.abs(ch[1]).max() + 1e-9) + np.roll(pad, 700) * 0.10], 1)
    t = np.arange(n) / SR; st *= np.minimum(1, np.minimum(t / 1.2, (dur - t) / 1.8))[:, None]
    st = np.tanh(st * 0.9) * 0.6
    w = wave.open(path, "wb"); w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes((st * 32767).astype(np.int16).tobytes()); w.close()

# ---------------- video ----------------
def _run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode: raise RuntimeError(r.stderr[-600:])
def build(files, out, work, scene, seed=0, log=print):
    """files: [(path, clip)]. Each segment is up to SEG_S long with soft fade in/out; 720x1280 keeps the free CPU fast."""
    segs, total, i = [], 0.0, 0
    for path, c in files:
        if total >= TOTAL_S - 0.5: break
        d = min(SEG_S, c["dur"] - 0.6, TOTAL_S - total); d = round(d, 2)
        if d < 7: continue
        ss = round(random.Random(seed + i).uniform(0, max(0, c["dur"] - d - 0.3)), 2); seg = f"{work}/amb{i}.mp4"
        vf = (f"scale=720:1280:force_original_aspect_ratio=increase:flags=lanczos,crop=720:1280,fps=30,eq=saturation=1.08:contrast=1.03,"
              f"fade=t=in:st=0:d=0.8,fade=t=out:st={d - 0.8:.2f}:d=0.8,setsar=1,format=yuv420p")
        _run(["ffmpeg", "-y", "-loglevel", "error", "-ss", f"{ss}", "-t", f"{d}", "-i", path, "-vf", vf, "-an", "-c:v", "libx264", "-preset", "veryfast", "-crf", "23", "-threads", "1", seg])
        segs.append(seg); total += d; i += 1; log(f"ambient segment {i} done ({total:.0f} s)")
    if total < 30: return None
    lst = f"{work}/amblist.txt"; open(lst, "w").write("".join(f"file '{os.path.abspath(s)}'\n" for s in segs))
    wav = f"{work}/amb.wav"; make_sound(wav, total, scene["sound"], seed)
    _run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", lst, "-i", wav, "-map", "0:v", "-map", "1:a", "-c:v", "copy",
          "-af", "loudnorm=I=-17:TP=-1.5:LRA=9", "-c:a", "aac", "-b:a", "192k", "-ar", "44100", "-shortest", "-movflags", "+faststart", out])
    return out
