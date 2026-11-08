import wave, numpy as np
def make_pad(path, dur, seed=0):
    sr = 44100; n = int(sr * dur); t = np.arange(n) / sr
    chords = [[220, 261.6, 329.6], [174.6, 220, 261.6], [261.6, 329.6, 392], [196, 246.9, 293.7]]
    rng = np.random.default_rng(seed); out = np.zeros(n); seg = 4.0
    for i in range(int(np.ceil(dur / seg))):
        ch = chords[(i + seed) % 4]; s0 = int(i * seg * sr); s1 = min(n, int((i + 1) * seg * sr) + sr)
        tt = t[s0:s1] - t[s0]
        env = np.clip(np.minimum(tt / 1.5, 1) * np.minimum((tt[-1] - tt) / 1.5, 1), 0, 1)
        for f in ch:
            for hmul, a in ((1, 1), (2, .3), (3, .1)):
                out[s0:s1] += a * np.sin(6.28318 * f * hmul * tt + rng.uniform(0, 6)) * env * 0.12
                out[s0:s1] += a * np.sin(6.28318 * f * hmul * tt + rng.uniform(0, 6)) * env * np.sin(6.28318 * 0.2 * tt + rng.uniform(0, 3)) ** 2 * 0.5
    out = out / np.abs(out).max() * 0.35
    out *= np.minimum(np.minimum(t / 1.0, 1), np.minimum((dur - t) / 1.0, 1))
    st = np.stack([out, np.roll(out, 200)], 1)
    w = wave.open(path, "wb"); w.setnchannels(2); w.setsampwidth(2); w.setframerate(sr)
    w.writeframes((st * 32767).astype(np.int16).tobytes()); w.close()

STYLES = ("pop", "ambient", "uplift", "lofi")
MINOR = ([55.0, 43.65, 65.41, 49.0], [[220, 261.63, 329.63], [174.61, 220, 261.63], [261.63, 329.63, 392.0], [196, 246.94, 293.66]])
MAJOR = ([65.41, 49.0, 55.0, 43.65], [[261.63, 329.63, 392.0], [196, 246.94, 293.66], [220, 261.63, 329.63], [174.61, 220, 261.63]])

def make_beat(path, dur, bpm=116.13, seed=0, style=None):
    """Original royalty-free track generated in code. 4 styles x 5 keys x 4 chord orders, all at the video's BPM so cuts stay on the beat."""
    sr = 44100; n = int(sr * dur); out = np.zeros(n); rng = np.random.default_rng(seed)
    style = STYLES[(seed if style is None else style) % 4]
    shift = 2 ** ([0, 3, 5, 7, -2][(seed // 4) % 5] / 12)             # key change
    order = [[0, 1, 2, 3], [1, 2, 3, 0], [0, 3, 1, 2], [2, 3, 0, 1]][(seed // 20) % 4]
    roots, chords = MAJOR if style == "uplift" else MINOR
    roots = [r * shift for r in roots]; chords = [[f * shift for f in c] for c in chords]
    beat = 60.0 / bpm; step = beat / 4
    def add(sig, t0, gain=1.0):
        i = int(t0 * sr)
        if i >= n: return
        j = min(n, i + len(sig)); out[i:j] += sig[:j - i] * gain
    tk = np.arange(int(0.4 * sr)) / sr
    kick = np.sin(2 * np.pi * np.cumsum(46 + 90 * np.exp(-tk * 28)) / sr) * np.exp(-tk * 7)
    def noise(len_s, decay, hp=True):
        t = np.arange(int(len_s * sr)) / sr; x = rng.standard_normal(len(t))
        if hp: x = np.diff(x, prepend=0)
        return x * np.exp(-t * decay)
    clap = noise(0.18, 22); hat = noise(0.05, 90); ohat = noise(0.14, 30)
    nbeats = int(dur / beat) + 2; kick_times = []
    for b in range(nbeats):
        t0 = b * beat
        if style in ("pop", "uplift"):
            add(kick, t0, 0.95); kick_times.append(t0)
            if b % 2 == 1: add(clap, t0, 0.16)
            add(hat, t0 + beat / 2, 0.05)
            if style == "uplift": add(ohat, t0 + beat / 2, 0.05)
            elif b % 2 == 0: add(hat, t0 + beat * 0.75, 0.025)
        elif style == "lofi":
            if b % 4 in (0, 2): add(kick, t0, 0.8); kick_times.append(t0)
            if b % 4 == 2: add(kick, t0 + beat * 0.75, 0.5)
            if b % 2 == 1: add(clap, t0, 0.10)
            add(hat, t0, 0.03); add(hat, t0 + beat * 0.5 + step * 0.4, 0.035)    # swung hats
        else:                                                                   # ambient: only a whisper of hats
            if b % 2 == 0: add(hat, t0 + beat / 2, 0.015)
    t = np.arange(n) / sr; bass = np.zeros(n); pad = np.zeros(n)
    pad_gain = {"pop": 0.05, "ambient": 0.10, "uplift": 0.06, "lofi": 0.08}[style]
    for bar in range(int(dur / (beat * 4)) + 2):
        c = order[(bar + seed) % 4]; a0 = int(bar * beat * 4 * sr); a1 = min(n, int((bar + 1) * beat * 4 * sr))
        if a0 >= n: break
        tt = t[a0:a1] - t[a0]
        gate = (0.75 + 0.25 * np.sign(np.sin(2 * np.pi * tt / (beat / 2)))) if style in ("pop", "uplift") else 1.0
        bass[a0:a1] += (np.sin(2 * np.pi * roots[c] * tt) + 0.25 * np.sin(4 * np.pi * roots[c] * tt)) * gate
        env = np.minimum(tt / 0.4, 1) * np.minimum((tt[-1] - tt) / 0.4 + 0.01, 1)
        vib = 1 + (0.004 * np.sin(2 * np.pi * 5 * tt) if style == "lofi" else 0)
        for f in chords[c]: pad[a0:a1] += np.sin(2 * np.pi * f * vib * tt + rng.uniform(0, 6)) * env * pad_gain
        for k in range(16):
            if style == "ambient" and k % 4: continue
            if style == "lofi" and k % 3: continue
            pat = [0, 2, 1, 2] if style == "uplift" else [0, 1, 2, 1]
            note = chords[c][pat[k % 4]] * (2 if k % 8 < 4 else 4)
            dec, g = {"pop": (14, 0.05), "ambient": (4, 0.07), "uplift": (11, 0.05), "lofi": (7, 0.06)}[style]
            tp = np.arange(int((0.22 if dec > 8 else 0.6) * sr)) / sr
            pl = (np.sin(2 * np.pi * note * tp) + 0.4 * np.sin(4 * np.pi * note * tp)) * np.exp(-tp * dec)
            add(pl, bar * beat * 4 + k * step, g)
    duck = np.ones(n)
    for kt in kick_times:
        i = int(kt * sr); j = min(n, i + int(0.35 * sr))
        if i < n: duck[i:j] = np.minimum(duck[i:j], 1 - 0.8 * np.exp(-np.arange(j - i) / sr * 14))
    out += bass * duck * (0.2 if style == "ambient" else 0.42) + pad * duck
    out = np.tanh(out * 0.85); out = out / np.abs(out).max() * 0.85
    out *= np.minimum(1, np.maximum(0, (dur - t) / 0.5))
    st = np.stack([out, np.roll(out, 90)], 1)
    w = wave.open(path, "wb"); w.setnchannels(2); w.setsampwidth(2); w.setframerate(sr)
    w.writeframes((st * 32767).astype(np.int16).tobytes()); w.close()

def from_track(src, out_wav, dur, seed=0, bpm=116.0):
    """Cut a bar-aligned segment from a music file, fade, loudness-normalize to about -14 LUFS."""
    import subprocess, random
    p = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", src], capture_output=True, text=True)
    total = float(p.stdout.strip() or 0); bar = 4 * 60.0 / bpm
    max_k = int(max(0, total - dur - 1) // bar)
    k = random.Random(seed).randint(min(2, max_k), max_k) if max_k > 0 else 0
    start = k * bar
    af = f"afade=t=in:st=0:d=0.15,afade=t=out:st={max(0, dur - 0.8):.2f}:d=0.8,loudnorm=I=-14:TP=-1.5:LRA=11"
    r = subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-ss", f"{start:.3f}", "-t", f"{dur:.3f}", "-i", src, "-af", af,
                        "-ar", "44100", "-ac", "2", out_wav], capture_output=True, text=True)
    if r.returncode: raise RuntimeError(r.stderr[-300:])
    return out_wav
