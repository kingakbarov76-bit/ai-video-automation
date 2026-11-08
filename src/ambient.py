"""Calm nature Shorts (~20-35 s): ONE named place, 1-3 slow licensed stock clips (Pexels/Pixabay), nature ambience that we synthesize
ourselves (water, wind, waves, light birdsong) under a very soft pad with sparse bell notes. Only the place name is shown, briefly.
The sound is synthetic and the description says so."""
import os, random, subprocess, wave
import numpy as np

SEG_S, MAX_S = 12.0, 34.0
CALM = ["lake", "lago", "falls", "bay", "island", "beach", "bora", "maldives", "fjord", "forest", "bamboo", "lauterbrunnen", "hallstatt", "dolomites", "banff",
        "yosemite", "plitvice", "milford", "guilin", "terraces", "cinque", "torres", "baikal", "lofoten", "faroe", "iceland", "zhangjiajie", "bali", "palawan", "reef", "blue hole"]
def calm_places(places_mod):
    return [p for p in places_mod.PLACES if any(k in p["label"].lower() for k in CALM)]
def kind_for(label):
    l = label.lower()
    if any(w in l for w in ("falls", "waterfall", "river", "zhangjiajie", "lauterbrunnen")): return "stream"
    if any(w in l for w in ("bora", "maldives", "beach", "bay", "island", "palawan", "reef", "blue hole", "cinque", "faroe", "lofoten", "fjord", "bali")): return "ocean"
    if any(w in l for w in ("lake", "lago", "plitvice", "baikal", "hallstatt", "milford")): return "lake"
    return "wind"
BIRDS = {"stream": 0.7, "wind": 0.8, "lake": 0.9, "ocean": 0.0}

# ---------------- sound ----------------
SR = 22050   # half rate keeps RAM low on the free 512 MB instance; ffmpeg resamples to 44.1 kHz
def _shaped(n, rng, lo, hi, tilt=0.0):
    x = rng.standard_normal(n); X = np.fft.rfft(x); f = np.fft.rfftfreq(n, 1 / SR)
    g = np.clip((f - lo) / max(lo * 0.3, 1), 0, 1) * np.clip((hi - f) / max(hi * 0.3, 1), 0, 1) / np.maximum(f, 20) ** tilt
    y = np.fft.irfft(X * g, n); return y / (np.abs(y).max() + 1e-9)
def _env(n, rng, rate, depth):
    k = max(2, int(n / SR * rate) + 2); pts = rng.uniform(1 - depth, 1, k)
    return np.interp(np.linspace(0, k - 1, n), np.arange(k), pts)
def _reverb(x, rng, rt=1.6, wet=0.25):
    """Cheap convolution reverb: decaying noise tail. Gives depth, so nothing sounds 'dry' or synthetic."""
    L = int(rt * SR); t = np.arange(L) / SR; ir = rng.standard_normal(L) * np.exp(-t * 6.9 / rt); ir[:int(0.012 * SR)] *= np.linspace(0, 1, int(0.012 * SR))
    N = len(x) + L; y = np.fft.irfft(np.fft.rfft(x, N) * np.fft.rfft(ir, N), N)[:len(x)]
    y *= np.abs(x).max() / (np.abs(y).max() + 1e-9); return x * (1 - wet) + y * wet
def _add(buf, sig, i, g=1.0):
    if i >= len(buf) or i < 0: return
    j = min(len(buf), i + len(sig)); buf[i:j] += sig[:j - i] * g

def _bubbles(n, rng, per_s):
    """Babbling-water detail: many tiny rising 'bloops'."""
    out = np.zeros(n)
    for t0 in rng.uniform(0, n / SR - 0.1, int(n / SR * per_s)):
        d = rng.uniform(0.02, 0.06); tt = np.arange(int(d * SR)) / SR; f0 = rng.uniform(500, 1900); f = f0 * (1 + 0.7 * tt / d)
        _add(out, np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-tt / (d * 0.35)), int(t0 * SR), rng.uniform(0.05, 0.4))
    return out
def _channel(kind, n, rng):
    t = np.arange(n) / SR
    if kind == "stream":      # flowing water: broadband rush made of several bands, each with its own fast random movement (no drips)
        a = sum(_shaped(n, rng, lo, hi, 0.2) * (0.45 + 0.55 * _env(n, rng, rate, 0.85)) * g
                for lo, hi, rate, g in ((120, 400, 4, 0.5), (350, 900, 9, 0.7), (800, 2000, 14, 0.9), (1800, 4200, 20, 0.8), (3800, 8000, 28, 0.45)))
    elif kind == "ocean":
        ph = rng.uniform(0, 6); swell = (0.5 + 0.5 * np.sin(2 * np.pi * t / 10.5 + ph)) ** 2.2 * 0.85 + 0.15
        foam = (0.5 + 0.5 * np.sin(2 * np.pi * t / 10.5 + ph - 0.9)) ** 3
        a = _shaped(n, rng, 100, 2200, 0.8) * swell + _shaped(n, rng, 1500, 8000, 0.3) * 0.35 * foam
    elif kind == "lake":      # shore lapping: soft low wash that swells and fades, plus a faint far-off ripple hiss. No drips.
        per = rng.uniform(5.5, 8.0); sw = (0.5 + 0.5 * np.sin(2 * np.pi * t / per + rng.uniform(0, 6))) ** 1.6 * (0.6 + 0.4 * _env(n, rng, 0.3, 0.8)) + 0.12
        a = _shaped(n, rng, 90, 1300, 0.9) * sw + _shaped(n, rng, 900, 3800, 0.5) * 0.14 * sw ** 1.5 * (0.6 + 0.4 * _env(n, rng, 3, 0.8)) + _shaped(n, rng, 60, 600, 0.9) * 0.2 * _env(n, rng, 0.1, 0.9)
    else:
        a = _shaped(n, rng, 70, 1000, 0.8) * (0.3 + 0.7 * _env(n, rng, 0.12, 0.9)) + _shaped(n, rng, 2500, 7000, 0.6) * 0.07 * _env(n, rng, 0.4, 0.95)   # gusts + a little leaf rustle
    return a / (np.abs(a).max() + 1e-9)
def _birds(n, rng, density):
    """Light synthetic birdsong: short chirp phrases at random times, soft, spread in the stereo field."""
    L, R = np.zeros(n), np.zeros(n); dur = n / SR; t = rng.uniform(1.5, 5); last = -1
    def note(f0, f1, d, vib=0):
        tt = np.arange(int(d * SR)) / SR; f = f0 + (f1 - f0) * tt / d + vib * np.sin(2 * np.pi * 30 * tt)
        ph = 2 * np.pi * np.cumsum(f) / SR; env = np.sin(np.pi * tt / d) ** 1.5
        return (np.sin(ph) + 0.25 * np.sin(2 * ph)) * env
    while t < dur - 1:
        sp = int(rng.integers(3))
        if sp == last: sp = (sp + 1 + int(rng.integers(2))) % 3
        last = sp; f0 = rng.uniform(2600, 4800); notes = []; pos = 0.0; g = rng.uniform(0.04, 0.11) * density
        if sp == 0:   # tweets
            for _ in range(rng.integers(3, 7)): d = rng.uniform(0.05, 0.1); notes.append((pos, note(f0, f0 * rng.uniform(0.7, 1.3), d))); pos += d + rng.uniform(0.07, 0.14)
        elif sp == 1:  # trill
            for k in range(rng.integers(8, 15)): d = 0.03; notes.append((pos, note(f0 * (1.05 if k % 2 else 0.95), f0 * (0.95 if k % 2 else 1.05), d))); pos += 0.055
        else:          # whistle
            for _ in range(2): d = rng.uniform(0.2, 0.32); notes.append((pos, note(f0 * 0.6, f0 * 0.75, d, vib=60))); pos += d + 0.12
        pan = rng.uniform(0.15, 0.85)
        for p, s in notes: _add(L, s, int((t + p) * SR), g * (1 - pan)); _add(R, s, int((t + p) * SR), g * pan)
        t += 3 + rng.gamma(2.0, 2.2)
    return L, R
def _music(n, rng, seed):
    """Warm pad + sparse pentatonic bell notes: slow, no beat, nothing to follow."""
    t = np.arange(n) / SR; pad = np.zeros(n); seg = int(SR * 9); chords = [[110, 164.81, 220, 277.18], [87.31, 130.81, 174.61, 220], [130.81, 196, 261.63, 329.63], [98, 146.83, 196, 246.94]]
    for i, a0 in enumerate(range(0, n, seg)):
        a1 = min(n, a0 + seg + SR * 2); tt = t[a0:a1] - t[a0]; env = np.minimum(tt / 4, 1) * np.clip((tt[-1] - tt) / 4, 0, 1)
        for f in chords[(i + seed) % 4]:
            for dt in (-0.6, 0.6): pad[a0:a1] += np.sin(2 * np.pi * (f + dt) * tt + rng.uniform(0, 6)) * env * 0.5
    pad = pad / (np.abs(pad).max() + 1e-9) * (0.8 + 0.2 * np.sin(2 * np.pi * t / 14))
    bells = np.zeros(n); scale = [220, 261.63, 293.66, 329.63, 392, 440, 523.25, 587.33]; tb = rng.uniform(1.5, 3)
    while tb < n / SR - 3:
        f = rng.choice(scale); tt = np.arange(int(3.2 * SR)) / SR
        _add(bells, (np.sin(2 * np.pi * f * tt) + 0.22 * np.sin(2 * np.pi * 2.0 * f * tt) + 0.08 * np.sin(2 * np.pi * 3.01 * f * tt)) * np.exp(-tt * 1.6) * np.minimum(tt / 0.01, 1), int(tb * SR), rng.uniform(0.18, 0.32))
        tb += rng.uniform(3.2, 7.5)
    m = _reverb(pad * 0.55 + bells, rng, rt=3.0, wet=0.5); return m / (np.abs(m).max() + 1e-9)
def _plan_env(n, plan, dur):
    """Per-sample 'mood' curves from what each clip looks like: sunny/bright -> birds, dull/grey -> more wind, bluish -> more water."""
    sun, blue = np.zeros(n), np.zeros(n); pos = 0.0
    for d, (r, g, b) in plan:
        i0, i1 = int(pos / dur * n), int(min(dur, pos + d) / dur * n); pos += d
        br = (r + g + b) / 765; sat = (max(r, g, b) - min(r, g, b)) / max(max(r, g, b), 1)
        sun[i0:i1] = np.clip((br - 0.32) / 0.3, 0, 1) * np.clip(sat / 0.28, 0, 1); blue[i0:i1] = np.clip((b - (r + g) / 2) / 35, 0, 1)
    sun[int(pos / dur * n):] = sun[max(0, int(pos / dur * n) - 1)]; blue[int(pos / dur * n):] = blue[max(0, int(pos / dur * n) - 1)]
    k = int(2.0 * SR)                                              # 2 s glide between moods so cuts do not jump
    def sm(x):
        c = np.cumsum(np.pad(x, (k // 2 + 1, k // 2), mode="edge")); return (c[k:k + n] - c[:n]) / k
    return sm(sun), sm(blue)
def make_sound(path, dur, kind, seed=0, plan=None):
    n = int(SR * dur); rng = np.random.default_rng(seed + 1000)
    sun, blue = _plan_env(n, plan, dur) if plan else (np.full(n, 0.6), np.full(n, 0.6))
    wind = np.stack([_channel("wind", n, rng) for _ in range(2)], 1) * (1.05 - 0.45 * sun)[:, None]
    if kind != "wind":
        water = np.stack([_channel(kind, n, rng) for _ in range(2)], 1) * (0.45 + 0.55 * blue)[:, None]
        nat = wind * 0.55 + water
    else: nat = wind
    nat = np.stack([_reverb(nat[:, 0], rng, 1.4, 0.18), _reverb(nat[:, 1], rng, 1.4, 0.18)], 1) * 0.85
    d = BIRDS.get(kind, 0)
    if d:
        bl, br = _birds(n, rng, d); bl, br = _reverb(bl, rng, 1.8, 0.35), _reverb(br, rng, 1.8, 0.35)
        nat += np.stack([bl, br], 1) * 1.6 * (0.1 + 0.9 * sun)[:, None]
    mus = _music(n, rng, seed); mus2 = np.stack([mus, np.roll(mus, 400)], 1) * 0.32
    st = nat + mus2
    t = np.arange(n) / SR; st *= np.minimum(1, np.minimum(t / 1.5, (dur - t) / 2.0))[:, None]
    st = np.tanh(st * 0.9) * 0.6
    w = wave.open(path, "wb"); w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes((st * 32767).astype(np.int16).tobytes()); w.close()

# ---------------- video ----------------
def _avg_rgb(path):
    r = subprocess.run(["ffmpeg", "-loglevel", "error", "-ss", "2", "-i", path, "-frames:v", "1", "-vf", "scale=1:1", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], capture_output=True)
    return tuple(r.stdout[:3]) if len(r.stdout) >= 3 else (128, 128, 128)
def pick_coherent(files, k=3):
    """Same place can be filmed in different weather/seasons: keep the clips whose overall colour and brightness are closest."""
    if len(files) <= k: return files
    import itertools
    cols = [_avg_rgb(p) for p, _ in files]
    def spread(ix): return max(sum((cols[a][c] - cols[b][c]) ** 2 for c in range(3)) for a, b in itertools.combinations(ix, 2))
    best = min(itertools.combinations(range(len(files)), k), key=spread)
    return [files[i] for i in best]

def _run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode: raise RuntimeError(r.stderr[-600:])
def build(files, out, work, kind, label_png=None, seed=0, log=print):
    """files: [(path, clip)] of ONE place. Each segment fades softly in/out; 720x1280 keeps the free CPU fast. The place name shows for ~4 s."""
    segs, total, i, plan = [], 0.0, 0, []
    for path, c in files:
        if total >= MAX_S - 0.5: break
        d = round(min(SEG_S, c["dur"] - 0.6, MAX_S - total), 2)
        if d < 6: continue
        ss = round(random.Random(seed + i).uniform(0, max(0, c["dur"] - d - 0.3)), 2); seg = f"{work}/amb{i}.mp4"
        base = (f"scale=720:1280:force_original_aspect_ratio=increase:flags=lanczos,crop=720:1280,fps=30,eq=saturation=1.06:contrast=1.03,"
                f"fade=t=in:st=0:d=1.0,fade=t=out:st={d - 1.0:.2f}:d=1.0,setsar=1")
        cmd = ["ffmpeg", "-y", "-loglevel", "error", "-ss", f"{ss}", "-t", f"{d}", "-i", path]
        if i == 0 and label_png:
            cmd += ["-loop", "1", "-framerate", "30", "-t", f"{d}", "-i", label_png, "-filter_complex",
                    f"[0:v]{base}[a];[1:v]format=rgba,fade=t=in:st=1.0:d=0.8:alpha=1,fade=t=out:st=4.4:d=0.8:alpha=1[o];[a][o]overlay=0:0:shortest=1,format=yuv420p[v]", "-map", "[v]"]
        else: cmd += ["-vf", base + ",format=yuv420p"]
        _run(cmd + ["-an", "-c:v", "libx264", "-preset", "veryfast", "-crf", "23", "-threads", "1", seg])
        segs.append(seg); plan.append((d, _avg_rgb(path))); total += d; i += 1; log(f"ambient segment {i} done ({total:.0f} s)")
    if total < 14: return None
    lst = f"{work}/amblist.txt"; open(lst, "w").write("".join(f"file '{os.path.abspath(s)}'\n" for s in segs))
    wav = f"{work}/amb.wav"; make_sound(wav, total, kind, seed, plan)
    _run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", lst, "-i", wav, "-map", "0:v", "-map", "1:a", "-c:v", "copy",
          "-af", "loudnorm=I=-17:TP=-1.5:LRA=9", "-c:a", "aac", "-b:a", "192k", "-ar", "44100", "-shortest", "-movflags", "+faststart", out])
    return out
