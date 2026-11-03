import os, subprocess, shutil
from PIL import Image, ImageDraw, ImageFont
from .audio import make_pad
W, H, FPS = 1080, 1920, 30
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
def build_video(images, hook, out_path, workdir, per=4.0, seed=0):
    os.makedirs(workdir, exist_ok=True); clips = []
    for i, data in enumerate(images):
        p = f"{workdir}/img{i}.jpg"
        im = Image.open(__import__("io").BytesIO(data)).convert("RGB")
        im.save(p, quality=95)
        side = i % 2  # alternate pan direction
        x = "(iw-1080)*t/%s" % per if side == 0 else "(iw-1080)*(1-t/%s)" % per
        vf = (f"scale=-2:{H*1.12:.0f}:flags=lanczos,crop={W}:{H}:x='({'iw-'+str(W)})*{'t/'+str(per) if side==0 else '(1-t/'+str(per)+')'}':y='(ih-{H})/2',"
              f"unsharp=5:5:0.6,eq=saturation=1.2:contrast=1.04,fade=t=in:st=0:d=0.3,fade=t=out:st={per-0.3}:d=0.3,setsar=1,format=yuv420p")
        c = f"{workdir}/clip{i}.mp4"
        run(["ffmpeg", "-y", "-loglevel", "error", "-loop", "1", "-t", str(per), "-framerate", str(FPS), "-i", p, "-vf", vf,
             "-r", str(FPS), "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", c])
        clips.append(c)
    lst = f"{workdir}/list.txt"
    open(lst, "w").write("".join(f"file '{os.path.abspath(c)}'\n" for c in clips))
    dur = per * len(images); wav = f"{workdir}/a.wav"; ov = f"{workdir}/ov.png"
    make_pad(wav, dur, seed); hook_overlay(ov, hook)
    run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", lst, "-i", wav, "-i", ov,
         "-filter_complex", "[0:v][2:v]overlay=0:0:enable='between(t,0,5)'[v]", "-map", "[v]", "-map", "1:a",
         "-c:v", "libx264", "-preset", "veryfast", "-crf", "21", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "160k", "-shortest", out_path])
    return out_path
