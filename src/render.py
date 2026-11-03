import os, subprocess, shutil
from PIL import Image, ImageDraw, ImageFont
from .audio import make_pad
W, H, FPS = 720, 1280, 30
MUSIC_SRC = None  # set by main: path to a library track; None = built-in synth
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
    dur = (93 + 31 * (len(clips) - 2) + 46) / FPS; wav = f"{workdir}/a.wav"; _music(wav, dur, bpm, seed, log)
    run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", lst, "-i", wav, "-map", "0:v", "-map", "1:a",
         "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest", out_path])
    return out_path


def soft_overlay(path, hook=None, caption=None, badge=None):
    """Small soft caption near the bottom + optional corner badge + optional big hook (first clip)."""
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    if hook:
        f1 = _font(64); y = 230
        words = hook[0].split(); lines, c = [], ""
        for w in words:
            x = (c + " " + w).strip()
            if d.textlength(x, font=f1) <= W - 80: c = x
            else: lines.append(c); c = w
        lines.append(c)
        for l in lines:
            x = (W - d.textlength(l, font=f1)) / 2
            for dx, dy in ((-4, 0), (4, 0), (0, -4), (0, 4), (-3, -3), (3, 3), (-3, 3), (3, -3)): d.text((x + dx, y + dy), l, font=f1, fill=(0, 0, 0, 255))
            d.text((x, y), l, font=f1, fill=(255, 226, 40, 255)); y += 80
        f2 = _font(44); l = hook[1]; x = (W - d.textlength(l, font=f2)) / 2
        for dx, dy in ((-3, 0), (3, 0), (0, -3), (0, 3)): d.text((x + dx, y + 10 + dy), l, font=f2, fill=(0, 0, 0, 255))
        d.text((x, y + 10), l, font=f2, fill=(255, 255, 255, 255))
    if caption:
        f = _font(40); tw = d.textlength(caption, font=f); x = (W - tw) / 2; y = int(H * 0.80)
        d.rounded_rectangle([x - 26, y - 12, x + tw + 26, y + 58], radius=30, fill=(0, 0, 0, 105))
        d.text((x + 2, y + 2), caption, font=f, fill=(0, 0, 0, 140)); d.text((x, y), caption, font=f, fill=(255, 255, 255, 255))
    if badge:
        f = _font(26); tw = d.textlength(badge, font=f)
        d.rounded_rectangle([W - tw - 56, 36, W - 24, 82], radius=22, fill=(0, 0, 0, 110)); d.text((W - tw - 40, 44), badge, font=f, fill=(255, 255, 255, 235))
    im.save(path)

def image_to_clip(img_bytes, out_mp4, workdir, idx, secs=3.4):
    """Photo -> short vertical clip with a gentle pan/zoom (alternating direction)."""
    import io
    p = f"{workdir}/ai{idx}.jpg"; Image.open(io.BytesIO(img_bytes)).convert("RGB").save(p, quality=95)
    t = f"(t/{secs})" if idx % 2 == 0 else f"(1-t/{secs})"
    vf = (f"scale=-2:{int(H*1.18)}:flags=bilinear,crop={W}:{H}:x='(iw-{W})*{t}':y='(ih-{H})/2',fps={FPS},setsar=1,format=yuv420p")
    run(["ffmpeg", "-y", "-loglevel", "error", "-loop", "1", "-t", str(secs), "-framerate", str(FPS), "-i", p, "-vf", vf,
         "-c:v", "libx264", "-preset", "ultrafast", "-crf", "20", "-threads", "1", out_mp4])
    return out_mp4

def build_beat_video2(clip_files, hook, captions, badge, out_path, workdir, bpm=116.13, seed=0, log=print, hd=False):
    """Same beat structure as build_beat_video (hook 93f, cuts of 31f, last 46f) with small soft captions by clip index."""
    from .audio import make_beat
    os.makedirs(workdir, exist_ok=True); clips = []; last = len(clip_files) - 1
    for i, src in enumerate(clip_files):
        frames = 93 if i == 0 else (46 if i == last else 31)
        cap = captions.get(i); ov = None
        if i == 0 or cap or badge:
            ov = f"{workdir}/ov{i}.png"; soft_overlay(ov, hook=hook if i == 0 else None, caption=cap, badge=badge)
            if hd: Image.open(ov).resize((1080, 1920), Image.LANCZOS).save(ov)
        c = f"{workdir}/clip{i}.mp4"
        ow, oh = (1080, 1920) if hd else (W, H)
        base = (f"scale={ow}:{oh}:force_original_aspect_ratio=increase:flags=lanczos,crop={ow}:{oh},fps={FPS},eq=saturation=1.3:contrast=1.06:brightness=0.02,setsar=1,format=yuv420p")
        if ov: cmd = ["ffmpeg", "-y", "-loglevel", "error", "-ss", "0.3", "-i", src, "-i", ov, "-filter_complex", f"[0:v]{base}[a];[a][1:v]overlay=0:0[v]", "-map", "[v]"]
        else: cmd = ["ffmpeg", "-y", "-loglevel", "error", "-ss", "0.3", "-i", src, "-vf", base, "-map", "0:v"]
        enc = (["-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-maxrate", "10M", "-bufsize", "20M", "-threads", "1"] if hd
               else ["-c:v", "libx264", "-preset", "ultrafast", "-crf", "24", "-threads", "1"])
        run(cmd + ["-frames:v", str(frames), "-an", "-r", str(FPS)] + enc + [c])
        clips.append(c); log(f"clip {i+1}/{len(clip_files)} done")
    lst = f"{workdir}/list.txt"; open(lst, "w").write("".join(f"file '{os.path.abspath(c)}'\n" for c in clips))
    dur = (93 + 31 * (len(clips) - 2) + 46) / FPS; wav = f"{workdir}/a.wav"; _music(wav, dur, bpm, seed, log)
    run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", lst, "-i", wav, "-map", "0:v", "-map", "1:a",
         "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest", out_path])
    return out_path


def _music(wav, dur, bpm, seed, log=print):
    from .audio import make_beat, from_track
    if MUSIC_SRC:
        try: from_track(MUSIC_SRC, wav, dur, seed); return
        except Exception as e: log("track cut failed, built-in used:", str(e)[:120])
    make_beat(wav, dur, bpm, seed)

def _pill(d, text, f, cx, y, fill=(0, 0, 0, 120)):
    tw = d.textlength(text, font=f); x = cx - tw / 2
    d.rounded_rectangle([x - 28, y - 12, x + tw + 28, y + int(f.size * 1.35)], radius=32, fill=fill)
    d.text((x + 2, y + 2), text, font=f, fill=(0, 0, 0, 150)); d.text((x, y), text, font=f, fill=(255, 255, 255, 255))

def choice_overlay(path, question, number, name):
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    fq = _font(38); tw = d.textlength(question, font=fq)
    for dx, dy in ((-3, 0), (3, 0), (0, -3), (0, 3), (-2, -2), (2, 2)): d.text(((W - tw) / 2 + dx, 150 + dy), question, font=fq, fill=(0, 0, 0, 255))
    d.text(((W - tw) / 2, 150), question, font=fq, fill=(255, 226, 40, 255))
    d.ellipse([40, 240, 170, 370], fill=(255, 255, 255, 235)); fn = _font(96); nw = d.textlength(str(number), font=fn)
    d.text((105 - nw / 2, 252), str(number), font=fn, fill=(30, 30, 30, 255))
    _pill(d, name, _font(44), W // 2, int(H * 0.80))
    fb = _font(24); bw = d.textlength("AI-generated", font=fb); bx = (W - bw) / 2   # top centre, below the Shorts top bar
    d.rounded_rectangle([bx - 16, 98, bx + bw + 16, 134], radius=18, fill=(0, 0, 0, 120)); d.text((bx, 102), "AI-generated", font=fb, fill=(255, 255, 255, 235))
    im.save(path)

def build_choice_video(imgs, names, out_path, workdir, question="Which place would you stay in?", seed=0, log=print):
    """4 options x 105 frames + 60-frame grid outro with 'Comment your number' = 480 frames (16s)."""
    import io
    from .audio import make_beat
    os.makedirs(workdir, exist_ok=True); clips = []; frames_each = 105
    for i, (data, name) in enumerate(zip(imgs, names)):
        base = image_to_clip(data, f"{workdir}/ch{i}_raw.mp4", workdir, 20 + i, secs=frames_each / FPS + 0.1)
        ov = f"{workdir}/chov{i}.png"; choice_overlay(ov, question, i + 1, name); c = f"{workdir}/chc{i}.mp4"
        fc = "[0:v]eq=saturation=1.25:contrast=1.05[a];[a][1:v]overlay=0:0[v]"
        run(["ffmpeg", "-y", "-loglevel", "error", "-i", base, "-i", ov, "-filter_complex", fc, "-map", "[v]", "-frames:v", str(frames_each), "-an",
             "-r", str(FPS), "-c:v", "libx264", "-preset", "ultrafast", "-crf", "22", "-threads", "1", c]); clips.append(c); log(f"option {i+1} done")
    g = Image.new("RGB", (W, H)); hw, hh = W // 2, H // 2; gd = ImageDraw.Draw(g)
    for i, data in enumerate(imgs):
        im = Image.open(io.BytesIO(data)).convert("RGB"); s = max(hw / im.width, hh / im.height); im = im.resize((int(im.width * s) + 1, int(im.height * s) + 1))
        l, t = (im.width - hw) // 2, (im.height - hh) // 2; g.paste(im.crop((l, t, l + hw, t + hh)), ((i % 2) * hw, (i // 2) * hh))
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(ov); fn = _font(70)
    for i in range(4):
        cx, cy = (i % 2) * hw + 60, (i // 2) * hh + 60; d.ellipse([cx - 44, cy - 44, cx + 44, cy + 44], fill=(255, 255, 255, 235))
        nw = d.textlength(str(i + 1), font=fn); d.text((cx - nw / 2, cy - 44), str(i + 1), font=fn, fill=(30, 30, 30, 255))
    _pill(d, "Comment your number", _font(48), W // 2, H // 2 - 30, fill=(0, 0, 0, 170))
    g = Image.alpha_composite(g.convert("RGBA"), ov).convert("RGB"); gp = f"{workdir}/grid.jpg"; g.save(gp, quality=95)
    c = f"{workdir}/chgrid.mp4"
    run(["ffmpeg", "-y", "-loglevel", "error", "-loop", "1", "-t", "2", "-framerate", str(FPS), "-i", gp, "-frames:v", "60", "-vf", f"fps={FPS},format=yuv420p",
         "-an", "-c:v", "libx264", "-preset", "ultrafast", "-crf", "22", "-threads", "1", c]); clips.append(c)
    lst = f"{workdir}/list.txt"; open(lst, "w").write("".join(f"file '{os.path.abspath(x)}'\n" for x in clips))
    wav = f"{workdir}/a.wav"; _music(wav, 16.0, 116.13, seed, log)
    run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", lst, "-i", wav, "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest", out_path])
    return out_path


# ---------------- v3: native 1080x1920 cards for named places / Dreamworld ----------------
HW, HH = 1080, 1920
def _wrap(d, text, f, maxw):
    lines, c = [], ""
    for w in text.split():
        x = (c + " " + w).strip()
        if d.textlength(x, font=f) <= maxw: c = x
        else:
            if c: lines.append(c)
            c = w
    if c: lines.append(c)
    return lines
def _outline_text(d, xy, text, f, fill, stroke=4):
    d.text(xy, text, font=f, fill=fill, stroke_width=stroke, stroke_fill=(0, 0, 0, 255))
def _box_lines(d, lines, f, y, fill=(255, 255, 255, 255), box=(0, 0, 0, 125), pad=26, gap=1.28):
    lh = int(f.size * gap); tw = max(d.textlength(l, font=f) for l in lines); x0 = (HW - tw) / 2
    d.rounded_rectangle([x0 - pad, y - pad * 0.6, x0 + tw + pad, y + lh * len(lines) - (lh - f.size) + pad * 0.9], radius=34, fill=box)
    for i, l in enumerate(lines):
        x = (HW - d.textlength(l, font=f)) / 2
        d.text((x, y + i * lh), l, font=f, fill=fill, stroke_width=2, stroke_fill=(0, 0, 0, 160))
    return y + lh * len(lines)
def card(path, hook=None, hook2=None, label=None, num=None, fact=None, cta=None, badge=None, out_size=None):
    """Transparent overlay: small, readable text inside the Shorts safe zone (centre band, away from the UI)."""
    im = Image.new("RGBA", (HW, HH), (0, 0, 0, 0)); d = ImageDraw.Draw(im); maxw = 820
    if badge:
        f = _font(34); tw = d.textlength(badge, font=f); x = (HW - tw) / 2
        d.rounded_rectangle([x - 22, 158, x + tw + 22, 210], radius=24, fill=(0, 0, 0, 120)); d.text((x, 164), badge, font=f, fill=(255, 255, 255, 235))
    if hook:
        f1 = _font(84); y = 290
        for l in _wrap(d, hook, f1, 940):
            _outline_text(d, ((HW - d.textlength(l, font=f1)) / 2, y), l, f1, (255, 226, 40, 255), 5); y += 104
        if hook2:
            f2 = _font(56)
            for l in _wrap(d, hook2, f2, 940):
                _outline_text(d, ((HW - d.textlength(l, font=f2)) / 2, y + 8), l, f2, (255, 255, 255, 255), 4); y += 70
    y0 = 1230
    if label:
        size = 54
        while size > 40 and d.textlength(label, font=_font(size)) > maxw: size -= 4
        f = _font(size); lines = _wrap(d, label, f, maxw)
        if num:
            fn = _font(50); cx = HW // 2; cy = y0 - 70
            d.ellipse([cx - 40, cy - 40, cx + 40, cy + 40], fill=(255, 226, 40, 240))
            nw = d.textlength(str(num), font=fn); d.text((cx - nw / 2, cy - 31), str(num), font=fn, fill=(20, 20, 20, 255))
        y0 = _box_lines(d, lines, f, y0) + 40
    if fact:
        f = _font(48); _box_lines(d, _wrap(d, fact, f, maxw), f, y0, box=(0, 0, 0, 115))
    if cta:
        f = _font(54); _box_lines(d, _wrap(d, cta, f, maxw), f, 1230, fill=(255, 236, 120, 255), box=(0, 0, 0, 135))
    if out_size and out_size != (HW, HH): im = im.resize(out_size, Image.LANCZOS)
    im.save(path)

FRAMES13 = [93] + [31] * 11 + [46]   # 480 frames = 16.0 s at 116.13 BPM (cuts on the beat)
def build_seq_video(segments, overlays, out_path, workdir, seed=0, log=print, hd=True, bpm=116.13):
    """segments: list of (src, start_seconds); overlays: list of png paths (or None); 13 segments -> 16 s."""
    os.makedirs(workdir, exist_ok=True); clips = []; ow, oh = (HW, HH) if hd else (W, H)
    frames = FRAMES13 if len(segments) == 13 else [93] + [31] * (len(segments) - 2) + [46]
    for i, ((src, ss), ov) in enumerate(zip(segments, overlays)):
        c = f"{workdir}/seq{i}.mp4"
        base = (f"scale={ow}:{oh}:force_original_aspect_ratio=increase:flags=lanczos,crop={ow}:{oh},fps={FPS},"
                f"eq=saturation=1.22:contrast=1.05:brightness=0.01,setsar=1,format=yuv420p")
        cmd = ["ffmpeg", "-y", "-loglevel", "error", "-ss", f"{ss:.2f}", "-i", src]
        if ov: cmd += ["-i", ov, "-filter_complex", f"[0:v]{base}[a];[a][1:v]overlay=0:0[v]", "-map", "[v]"]
        else: cmd += ["-vf", base, "-map", "0:v"]
        enc = (["-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-maxrate", "10M", "-bufsize", "20M", "-threads", "1"] if hd
               else ["-c:v", "libx264", "-preset", "ultrafast", "-crf", "22", "-threads", "1"])
        run(cmd + ["-frames:v", str(frames[i]), "-an", "-r", str(FPS)] + enc + [c])
        clips.append(c); log(f"segment {i+1}/{len(segments)} done")
    lst = f"{workdir}/seqlist.txt"; open(lst, "w").write("".join(f"file '{os.path.abspath(c)}'\n" for c in clips))
    dur = sum(frames) / FPS; wav = f"{workdir}/a.wav"; _music(wav, dur, bpm, seed, log)
    run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", lst, "-i", wav, "-map", "0:v", "-map", "1:a",
         "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", out_path])
    return out_path
