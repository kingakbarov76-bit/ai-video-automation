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
    if kind == "stream":
        a = _shaped(n, rng, 250, 6500, 0.3) * (0.5 + 0.5 * _env(n, rng, 2.5, 0.8)) * 0.8 + _shaped(n, rng, 900, 3800, 0.2) * 0.3 * _env(n, rng, 6, 0.9) + _bubbles(n, rng, 60) * 0.5
    elif kind == "ocean":
        ph = rng.uniform(0, 6); swell = (0.5 + 0.5 * np.sin(2 * np.pi * t / 10.5 + ph)) ** 2.2 * 0.85 + 0.15
        foam = (0.5 + 0.5 * np.sin(2 * np.pi * t / 10.5 + ph - 0.9)) ** 3
        a = _shaped(n, rng, 100, 2200, 0.8) * swell + _shaped(n, rng, 1500, 8000, 0.3) * 0.35 * foam
    elif kind == "lake":
        a = _shaped(n, rng, 70, 800, 0.8) * (0.3 + 0.5 * _env(n, rng, 0.1, 0.9)) + _shaped(n, rng, 180, 2000, 0.8) * 0.16 * (0.5 + 0.5 * np.sin(2 * np.pi * t / 6.5 + rng.uniform(0, 6))) ** 2 \
            + _bubbles(n, rng, 3) * 0.3
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
def make_sound(path, dur, kind, seed=0):
    n = int(SR * dur); rng = np.random.default_rng(seed + 1000)
    ch = [_reverb(_channel(kind, n, rng), rng, rt=1.4, wet=0.18) for _ in range(2)]
    nat = np.stack(ch, 1) * 0.85
    d = BIRDS.get(kind, 0)
    if d: bl, br = _birds(n, rng, d); bl, br = _reverb(bl, rng, 1.8, 0.35), _reverb(br, rng, 1.8, 0.35); nat += np.stack([bl, br], 1) * 1.6
    mus = _music(n, rng, seed); mus2 = np.stack([mus, np.roll(mus, 400)], 1) * 0.32
    st = nat + mus2
    t = np.arange(n) / SR; st *= np.minimum(1, np.minimum(t / 1.5, (dur - t) / 2.0))[:, None]
    st = np.tanh(st * 0.9) * 0.6
    w = wave.open(path, "wb"); w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes((st * 32767).astype(np.int16).tobytes()); w.close()

# ---------------- video ----------------
def _run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode: raise RuntimeError(r.stderr[-600:])
def build(files, out, work, kind, label_png=None, seed=0, log=print):
    """files: [(path, clip)] of ONE place. Each segment fades softly in/out; 720x1280 keeps the free CPU fast. The place name shows for ~4 s."""
    segs, total, i = [], 0.0, 0
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
        segs.append(seg); total += d; i += 1; log(f"ambient segment {i} done ({total:.0f} s)")
    if total < 14: return None
    lst = f"{work}/amblist.txt"; open(lst, "w").write("".join(f"file '{os.path.abspath(s)}'\n" for s in segs))
    wav = f"{work}/amb.wav"; make_sound(wav, total, kind, seed)
    _run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", lst, "-i", wav, "-map", "0:v", "-map", "1:a", "-c:v", "copy",
          "-af", "loudnorm=I=-17:TP=-1.5:LRA=9", "-c:a", "aac", "-b:a", "192k", "-ar", "44100", "-shortest", "-movflags", "+faststart", out])
    return out
