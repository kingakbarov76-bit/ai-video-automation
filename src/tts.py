"""Free English voiceover with Kokoro-82M (Apache-2.0, commercial use OK). Runs in a subprocess so its RAM is freed
before video rendering. Any failure returns None and the video simply goes out without narration."""
import json, os, subprocess, sys

MODEL = os.environ.get("KOKORO_DIR", "/app/models")
VOICE = "af_heart"

def _worker(job, out_dir):
    import soundfile as sf
    from kokoro_onnx import Kokoro
    k = Kokoro(f"{MODEL}/kokoro-v1.0.int8.onnx", f"{MODEL}/voices-v1.0.bin")
    res = []
    for i, text in enumerate(job):
        s, sr = k.create(text, voice=VOICE, speed=0.95, lang="en-us")
        p = f"{out_dir}/n{i:02d}.wav"; sf.write(p, s, sr); res.append(p)
    json.dump(res, open(f"{out_dir}/done.json", "w"))

def synth(lines, out_dir, log=print, timeout=600):
    """lines: list of strings -> list of wav paths (same order) or None."""
    os.makedirs(out_dir, exist_ok=True)
    jf = f"{out_dir}/job.json"; json.dump(lines, open(jf, "w"))
    try:
        r = subprocess.run([sys.executable, "-m", "src.tts", jf, out_dir], capture_output=True, text=True, timeout=timeout)
        if r.returncode != 0: log("tts failed:", (r.stderr or "")[-300:]); return None
        return json.load(open(f"{out_dir}/done.json"))
    except Exception as ex:
        log("tts error:", str(ex)[:150]); return None

def schedule(wavs, starts, dur, gap=0.25):
    """Place narration lines at their wanted starts without overlapping; drop lines that would run past the video."""
    import soundfile as sf
    out = []; t = 0.0
    for p, s in zip(wavs, starts):
        d = sf.info(p).duration; s = max(s, t)
        if s + d > dur - 0.2: continue
        out.append((p, s)); t = s + d + gap
    return out

def mix(music_wav, narr, starts, dur, out_wav, run):
    """Narration wavs placed at `starts` (seconds) over the music (music lowered to 40%)."""
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-i", music_wav]
    for p in narr: cmd += ["-i", p]
    fc = "[0:a]volume=0.40[m];"
    labels = ""
    for i, st in enumerate(starts):
        fc += f"[{i+1}:a]aresample=44100,pan=stereo|c0=c0|c1=c0,volume=1.6,adelay={int(st*1000)}|{int(st*1000)}[n{i}];"; labels += f"[n{i}]"
    fc += f"[m]{labels}amix=inputs={len(narr)+1}:normalize=0:duration=first,alimiter=limit=0.95,atrim=0:{dur:.2f}[out]"
    run(cmd + ["-filter_complex", fc, "-map", "[out]", "-ar", "44100", "-ac", "2", out_wav]); return out_wav

if __name__ == "__main__":
    _worker(json.load(open(sys.argv[1])), sys.argv[2])
