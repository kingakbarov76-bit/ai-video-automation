import os
from PIL import Image, ImageDraw, ImageFont
def _f(sz):
    for p in ("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",):
        if os.path.exists(p): return ImageFont.truetype(p, sz)
    return ImageFont.load_default()
def gradient(w, h, c1, c2):
    im = Image.new("RGB", (w, h)); px = im.load()
    for x in range(w):
        t = x / (w - 1)
        col = tuple(int(c1[i] + (c2[i] - c1[i]) * t) for i in range(3))
        for y in range(h): px[x, y] = col
    return im
def banner(path, title="Dreamy Earth", sub="Places on Earth that don't feel real"):
    im = gradient(2560, 1440, (255, 150, 60), (120, 70, 200)); d = ImageDraw.Draw(im)
    f1, f2 = _f(190), _f(80)
    for text, f, y, col in ((title, f1, 560, (255, 255, 255)), (sub, f2, 800, (255, 240, 200))):
        w = d.textlength(text, font=f); d.text(((2560 - w) / 2, y), text, font=f, fill=col)
    im.save(path)
def avatar(path, letter="D"):
    im = gradient(800, 800, (255, 150, 60), (120, 70, 200)); d = ImageDraw.Draw(im); f = _f(420)
    w = d.textlength(letter, font=f); d.text(((800 - w) / 2, 150), letter, font=f, fill=(255, 255, 255)); im.save(path)
