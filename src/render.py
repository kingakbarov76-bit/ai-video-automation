import os, subprocess, shutil
from PIL import Image, ImageDraw, ImageFont
from .audio import make_pad
W, H, FPS = 720, 1280, 30
def _font(size):
    for p in ("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"):
        if os.path.exists(p): return ImageFont.truetype(p, size)
    return ImageFont.load_default()
def hook_overlay(path, text):
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(im); f = _font(78)
    lines, c = [], ""
    for w in text.split():
        x = (c + " " + w).strip()
        if d.textlength(x, font=f) <= 940: c = x
        else: lines.append(c); c = w
    lines.append(c); y = 300
    for l in lines:
        x = (W - d.textlength(l, font=f)) / 2
        for dx, dy in ((-4, 0), (4, 0), (0, -4), (0, 4), (-3, -3), (3, 3), (-3, 3), (3, -3)):
            d.text((x + dx, y + dy), l, font=f, fill=(0, 0, 0, 255))
        d.text((x, y), l, font=f, fill=(255, 230, 80, 255)); y += 100
    im.save(path)
def run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode: raise RuntimeError(r.stderr[-800:])
def build_video(images, hook, out_path, workdir, per=4.0, seed=0, log=print):
    os.makedirs(workdir, exist_ok=True); clips = []
    for i, data in enumerate(images):
        p = f"{workdir}/img{i}.jpg"
        im = Image.open(__import__("io").BytesIO(data)).convert("RGB")
        im.save(p, quality=95)
        side = i % 2  # alternate pan direction
        x = "(iw-1080)*t/%s" % per if side == 0 else "(iw-1080)*(1-t/%s)" % per
        vf = (f"scale=-2:{H*1.12:.0f}:flags=bilinear,crop={W}:{H}:x='({'iw-'+str(W)})*{'t/'+str(per) if side==0 else '(1-t/'+str(per)+')'}':y='(ih-{H})/2',"
              f"eq=saturation=1.2:contrast=1.04,fade=t=in:st=0:d=0.3,fade=t=out:st={per-0.3}:d=0.3,setsar=1,format=yuv420p")
        c = f"{workdir}/clip{i}.mp4"
        run(["ffmpeg", "-y", "-loglevel", "error", "-loop", "1", "-t", str(per), "-framerate", str(FPS), "-i", p, "-vf", vf,
             "-r", str(FPS), "-c:v", "libx264", "-preset", "ultrafast", "-crf", "24", "-threads", "1", c])
        clips.append(c); log(f"clip {i+1}/{len(images)} done")
    lst = f"{workdir}/list.txt"
    open(lst, "w").write("".join(f"file '{os.path.abspath(c)}'\n" for c in clips))
    dur = per * len(images); wav = f"{workdir}/a.wav"; ov = f"{workdir}/ov.png"
    make_pad(wav, dur, seed); hook_overlay(ov, hook)
    run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", lst, "-i", wav, "-i", ov,
         "-filter_complex", "[0:v][2:v]overlay=0:0:enable='between(t,0,5)'[v]", "-map", "[v]", "-map", "1:a",
         "-c:v", "libx264", "-preset", "ultrafast", "-crf", "24", "-threads", "1", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "160k", "-shortest", out_path])
    return out_path


def cap_overlay(path, text, y_top=None, big=False):
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(im); f = _font(54 if not big else 70)
    lines, c = [], ""
    for w in text.split():
        x = (c + " " + w).strip()
        if d.textlength(x, font=f) <= W - 100: c = x
        else: lines.append(c); c = w
    lines.append(c); y = y_top if y_top is not None else int(H * 0.72)
    for l in lines:
        x = (W - d.textlength(l, font=f)) / 2
        for dx, dy in ((-3, 0), (3, 0), (0, -3), (0, 3), (-2, -2), (2, 2), (-2, 2), (2, -2)):
            d.text((x + dx, y + dy), l, font=f, fill=(0, 0, 0, 255))
        d.text((x, y), l, font=f, fill=(255, 255, 255, 255)); y += 70
    im.save(path)

def build_stock_video(clip_files, hook, captions, out_path, workdir, per=4.0, seed=0, log=print):
    os.makedirs(workdir, exist_ok=True); clips = []
    for i, src in enumerate(clip_files):
        ov = f"{workdir}/cap{i}.png"
        if i == 0:
            hook_overlay(ov, hook)
        else:
            cap_overlay(ov, captions[(i - 1) % len(captions)])
        c = f"{workdir}/clip{i}.mp4"
        vf = (f"[0:v]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},fps={FPS},eq=saturation=1.25:contrast=1.05,"
              f"setsar=1,format=yuv420p[a];[a][1:v]overlay=0:0,fade=t=in:st=0:d=0.25,fade=t=out:st={per-0.25}:d=0.25[v]")
        run(["ffmpeg", "-y", "-loglevel", "error", "-ss", "0.5", "-t", str(per), "-i", src, "-i", ov, "-filter_complex", vf, "-map", "[v]", "-an",
             "-r", str(FPS), "-c:v", "libx264", "-preset", "ultrafast", "-crf", "24", "-threads", "1", c])
        clips.append(c); log(f"clip {i+1}/{len(clip_files)} done")
    lst = f"{workdir}/list.txt"
    open(lst, "w").write("".join(f"file '{os.path.abspath(c)}'\n" for c in clips))
    dur = per * len(clips); wav = f"{workdir}/a.wav"; make_pad(wav, dur, seed)
    run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", lst, "-i", wav, "-map", "0:v", "-map", "1:a",
         "-c:v", "copy", "-c:a", "aac", "-b:a", "160k", "-shortest", out_path])
    return out_path


def hook_overlay2(path, line1, line2):
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    def block(text, size, y, col):
        f = _font(size); lines, c = [], ""
        for w in text.split():
            x = (c + " " + w).strip()
            if d.textlength(x, font=f) <= W - 80: c = x
            else: lines.append(c); c = w
        lines.append(c)
        for l in lines:
            x = (W - d.textlength(l, font=f)) / 2
            for dx, dy in ((-4, 0), (4, 0), (0, -4), (0, 4), (-3, -3), (3, 3), (-3, 3), (3, -3)):
                d.text((x + dx, y + dy), l, font=f, fill=(0, 0, 0, 255))
            d.text((x, y), l, font=f, fill=col); y += int(size * 1.25)
        return y
    y = block(line1, 64, 230, (255, 226, 40, 255))
    block(line2, 44, y + 10, (255, 255, 255, 255))
    im.save(path)

def build_beat_video(clip_files, line1, line2, outro, out_path, workdir, bpm=116.13, seed=0, log=print):
    """Hook clip (6 beats = 93 frames) then fast cuts of 2 beats (31 frames) on the beat."""
    from .audio import make_beat
    os.makedirs(workdir, exist_ok=True); clips = []
    ov1 = f"{workdir}/hook.png"; hook_overlay2(ov1, line1, line2)
    ov2 = f"{workdir}/outro.png"; cap_overlay(ov2, outro, y_top=int(H * 0.78), big=False)
    last = len(clip_files) - 1
    for i, src in enumerate(clip_files):
        frames = 93 if i == 0 else (46 if i == last else 31)
        ov = ov1 if i == 0 else (ov2 if i == last else None)
        c = f"{workdir}/clip{i}.mp4"
        base = (f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},fps={FPS},eq=saturation=1.35:contrast=1.08:brightness=0.02,setsar=1,format=yuv420p")
        if ov:
            fc = f"[0:v]{base}[a];[a][1:v]overlay=0:0[v]"
            cmd = ["ffmpeg", "-y", "-loglevel", "error", "-ss", "0.6", "-i", src, "-i", ov, "-filter_complex", fc, "-map", "[v]"]
        else:
            cmd = ["ffmpeg", "-y", "-loglevel", "error", "-ss", "0.6", "-i", src, "-vf", base, "-map", "0:v"]
        run(cmd + ["-frames:v", str(frames), "-an", "-r", str(FPS), "-c:v", "libx264", "-preset", "ultrafast", "-crf", "24", "-threads", "1", c])
        clips.append(c); log(f"clip {i+1}/{len(clip_files)} done")
    lst = f"{workdir}/list.txt"
    open(lst, "w").write("".join(f"file '{os.path.abspath(c)}'\n" for c in clips))
    dur = (93 + 31 * (len(clips) - 2) + 46) / FPS; wav = f"{workdir}/a.wav"; make_beat(wav, dur, bpm, seed)
    run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", lst, "-i", wav, "-map", "0:v", "-map", "1:a",
         "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest", out_path])
    return out_path
