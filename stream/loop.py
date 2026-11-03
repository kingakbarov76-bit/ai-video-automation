import os, subprocess
from PIL import Image, ImageDraw, ImageFont
from src.audio import make_pad
W, H, FPS = 1280, 720, 30
def run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode: raise RuntimeError(r.stderr[-600:])
def mark(path, text="Dreamy Earth"):
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    fp = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
    f = ImageFont.truetype(fp, 30) if os.path.exists(fp) else ImageFont.load_default()
    d.text((41, H - 61), text, font=f, fill=(0, 0, 0, 160)); d.text((40, H - 62), text, font=f, fill=(255, 255, 255, 220)); im.save(path)
def build(files, out, work, per=7, seed=0, log=print):
    os.makedirs(work, exist_ok=True); clips = []; ov = f"{work}/mark.png"; mark(ov)
    for i, src in enumerate(files):
        c = f"{work}/c{i}.mp4"
        vf = (f"[0:v]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},fps={FPS},eq=saturation=1.2:contrast=1.04,setsar=1,format=yuv420p[a];"
              f"[a][1:v]overlay=0:0,fade=t=in:st=0:d=0.5,fade=t=out:st={per-0.5}:d=0.5[v]")
        run(["ffmpeg", "-y", "-loglevel", "error", "-ss", "0.5", "-t", str(per), "-i", src, "-i", ov, "-filter_complex", vf, "-map", "[v]", "-an",
             "-c:v", "libx264", "-preset", "veryfast", "-b:v", "2500k", "-maxrate", "2800k", "-bufsize", "5000k", "-g", "60", "-keyint_min", "60", "-sc_threshold", "0", c])
        clips.append(c)
        if (i + 1) % 10 == 0: log(f"loop clips {i+1}/{len(files)}")
    lst = f"{work}/list.txt"; open(lst, "w").write("".join(f"file '{os.path.abspath(c)}'\n" for c in clips))
    dur = per * len(clips); wav = f"{work}/a.wav"; make_pad(wav, dur, seed)
    run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", lst, "-i", wav, "-map", "0:v", "-map", "1:a",
         "-c:v", "copy", "-c:a", "aac", "-b:a", "128k", "-ar", "44100", out])
    for c in clips: os.remove(c)
    return out
