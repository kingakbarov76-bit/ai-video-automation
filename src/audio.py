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
