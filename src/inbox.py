"""Telegram inbox: the owner sends his OWN videos (caption = place / title) to a bot; they are stored on the
GitHub branch `music-library` (survives Render restarts) and uploaded one by one by main.do_inbox()."""
import os, re, json, time, base64, requests
from . import music

TG = "https://api.telegram.org"
MAX_BYTES = 20 * 1048576          # Telegram Bot API download limit
SUB = "https://www.youtube.com/@dreamyearthh?sub_confirmation=1"
BASE_TAGS = ["shorts", "nature", "travel", "beautiful places", "places on earth", "relaxing", "calm nature", "scenery"]


def _tok(): return os.environ.get("TG_BOT_TOKEN", "").strip()
def _api(method, **kw):
    r = requests.post(f"{TG}/bot{_tok()}/{method}", json=kw, timeout=70)
    return r.json()
def _say(chat, text):
    try: _api("sendMessage", chat_id=chat, text=text)
    except Exception: pass

# ---------- GitHub storage (branch music-library, folder inbox/) ----------
def _contents(path): return f"{music.GH}/repos/{music.REPO}/contents/{path}"
def _list(path):
    r = requests.get(_contents(path), headers=music._gh(), params={"ref": music.BRANCH}, timeout=30)
    return r.json() if r.status_code == 200 and isinstance(r.json(), list) else []
def _get_bytes(path):
    h = dict(music._gh()); h["Accept"] = "application/vnd.github.raw"
    r = requests.get(_contents(path), headers=h, params={"ref": music.BRANCH}, timeout=120)
    r.raise_for_status(); return r.content
def _delete(path, sha):
    requests.delete(_contents(path), headers=music._gh(), timeout=60,
                    json={"message": f"inbox done {path}", "sha": sha, "branch": music.BRANCH})
def pending():
    """[(base_name, sha_json, sha_mp4)] oldest first."""
    fs = {f["name"]: f for f in _list("inbox/pending")}
    out = []
    for n, f in sorted(fs.items()):
        if n.endswith(".json") and n[:-5] + ".mp4" in fs:
            out.append((n[:-5], f["sha"], fs[n[:-5] + ".mp4"]["sha"]))
    return out

# ---------- metadata ----------
def _words(s): return [w for w in re.findall(r"[A-Za-z][A-Za-z'-]{2,}", s)]
def make_meta(caption):
    """caption: 'Title | extra description'. Title = place name -> search-style title."""
    cap = (caption or "").strip()
    title_src, _, extra = cap.partition("|")
    title_src = re.sub(r"\s+", " ", title_src).strip(" -:.")
    if not title_src: title_src = "Beautiful place on Earth"
    if len(title_src) > 60 or title_src.count(" ") > 6: title = title_src[:100]
    else: title = f"{title_src} \U0001F33F calm nature sounds to relax"
    words = _words(title_src)
    ht = ["#shorts", "#nature", "#travel"] + [("#" + "".join(words[:2]).lower())] if words else ["#shorts", "#nature", "#travel"]
    desc = (f"{title_src}.\n" + (extra.strip() + "\n" if extra.strip() else "") +
            f"\nSubscribe for more beautiful places: {SUB}\n\n" +
            f"{' '.join(dict.fromkeys(ht))} #beautifulplaces #relaxing")
    tags = list(dict.fromkeys([title_src] + words[:4] + BASE_TAGS))[:15]
    return title, desc, tags

# ---------- Telegram polling ----------
def _state():
    t, _ = music._get_text("inbox/state.json")
    return json.loads(t) if t else {}
def _save_state(st): music._put("inbox/state.json", json.dumps(st).encode(), "inbox state")

def _handle(m, log):
    chat = m["chat"]["id"]; uid = m.get("from", {}).get("id")
    st = _state(); owner = st.get("owner")
    txt = (m.get("text") or "").strip()
    if owner is None:
        if txt.startswith("/start"):
            st["owner"] = uid; _save_state(st); owner = uid
            _say(chat, "Salom! Men Dreamy Earth boti. Video yuboring, izohga joy nomini yozing (masalan: Bali). "
                       "Men uni sarlavha va heshteglar bilan YouTube'ga navbat bilan yuklayman.")
            return
        _say(chat, "Boshlash uchun /start yozing."); return
    if uid != owner: _say(chat, "Bu bot shaxsiy."); return
    if txt.startswith("/status") or txt.startswith("/start"):
        _say(chat, f"Navbatda: {len(pending())} ta video."); return
    v = m.get("video") or (m.get("document") if str((m.get("document") or {}).get("mime_type", "")).startswith("video/") else None)
    if not v:
        _say(chat, "Video yuboring (izohga joy nomi). /status - navbat."); return
    if v.get("file_size", 0) > MAX_BYTES:
        _say(chat, "Video 20 MB dan katta, Telegram bot uni ololmaydi. Kichikroq (siqilgan) yuboring."); return
    fp = _api("getFile", file_id=v["file_id"]).get("result", {}).get("file_path")
    if not fp: _say(chat, "Videoni ololmadim, qayta yuboring."); return
    data = requests.get(f"{TG}/file/bot{_tok()}/{fp}", timeout=120).content
    base = f"{int(time.time())}_{v.get('file_unique_id', 'x')}"
    cap = (m.get("caption") or "").strip()      # empty caption -> the scene is described automatically at upload time
    music._put(f"inbox/pending/{base}.mp4", data, f"inbox video {base}")
    music._put(f"inbox/pending/{base}.json", json.dumps({"caption": cap, "added": time.time()}).encode(), f"inbox meta {base}")
    log(f"INBOX: queued {base} ({len(data) // 1024} KB) caption={cap[:40]!r}")
    _say(chat, f"Qabul qilindi. Navbatda: {len(pending())} ta." + ("" if cap else " Sarlavhani o'zim topaman."))

def poll_loop(log=print):
    if not _tok(): return
    try: music.ensure_branch(log)
    except Exception as e: log("inbox branch:", str(e)[:100])
    off = None
    log("INBOX: telegram polling started")
    while True:
        try:
            r = requests.post(f"{TG}/bot{_tok()}/getUpdates", json={"timeout": 50, "offset": off, "allowed_updates": ["message"]}, timeout=70).json()
            for u in r.get("result", []):
                off = u["update_id"] + 1
                try:
                    if "message" in u: _handle(u["message"], log)
                except Exception as e: log("INBOX handle error:", type(e).__name__, str(e)[:150])
            if not r.get("ok", True): time.sleep(20)
        except Exception as e:
            log("INBOX poll error:", str(e)[:100]); time.sleep(10)

# ---------- automatic title from the picture (Cloudflare Workers AI vision, free tier) ----------
def describe(path, log=print):
    """3-5 word scene description of the video (e.g. 'turquoise waterfall in green forest') or '' on any failure."""
    import subprocess
    acc, tok = os.environ.get("CF_ACCOUNT_ID", "").strip(), os.environ.get("CF_API_TOKEN", "").strip()
    if not (acc and tok): return ""
    try:
        d = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path],
                                 capture_output=True, text=True).stdout.strip() or 6)
        jpg = path + ".jpg"
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-ss", f"{d / 3:.2f}", "-i", path, "-frames:v", "1",
                        "-vf", "scale=448:-2", "-q:v", "4", jpg], check=True)
        img = list(open(jpg, "rb").read())
        r = requests.post(f"https://api.cloudflare.com/client/v4/accounts/{acc}/ai/run/@cf/llava-hf/llava-1.5-7b-hf",
                          headers={"Authorization": f"Bearer {tok}"}, timeout=120,
                          json={"image": img, "max_tokens": 24,
                                "prompt": "Describe the main scenery of this photo in 3 to 5 words, like 'turquoise waterfall in green forest'. "
                                          "Answer with only those words, no punctuation, no sentence."})
        txt = (r.json().get("result") or {}).get("description") or (r.json().get("result") or {}).get("response") or ""
        txt = re.sub(r"[^A-Za-z' -]", " ", txt).strip()
        txt = re.sub(r"^(a|an|the)\s+", "", re.sub(r"\s+", " ", txt), flags=re.I)
        if 2 <= len(txt.split()) <= 8: return txt[:1].upper() + txt[1:]
        log("INBOX describe: unusable answer:", txt[:60])
    except Exception as e: log("INBOX describe failed:", str(e)[:120])
    return ""

# ---------- channel-name watermark ----------
def brand(path, out, text="@dreamyearthh", log=print):
    """Burns a small semi-transparent channel name into the upper third (clear of the Shorts UI). Returns out, or path on failure."""
    import subprocess
    from PIL import Image, ImageDraw, ImageFont
    try:
        w, h = [int(x) for x in subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height",
                "-of", "csv=p=0:s=x", path], capture_output=True, text=True).stdout.strip().split("x")]
        if w > 1080: h = round(h * 1080 / w / 2) * 2; w = 1080
        fs = max(24, int(w * 0.05)); font = None
        for fp in ("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"):
            if os.path.exists(fp): font = ImageFont.truetype(fp, fs); break
        font = font or ImageFont.load_default()
        im = Image.new("RGBA", (w, h), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
        tw = d.textlength(text, font=font); x = (w - tw) / 2; y = int(h * 0.13)
        d.text((x + 2, y + 2), text, font=font, fill=(0, 0, 0, 110)); d.text((x, y), text, font=font, fill=(255, 255, 255, 175))
        png = path + ".wm.png"; im.save(png)
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", path, "-i", png, "-filter_complex",
                        f"[0:v]scale={w}:{h}[b];[b][1:v]overlay=0:0,format=yuv420p[v]", "-map", "[v]", "-map", "0:a?", "-c:v", "libx264",
                        "-preset", "veryfast", "-crf", "23", "-threads", "1", "-c:a", "copy", "-movflags", "+faststart", out], check=True, timeout=600)
        return out
    except Exception as e:
        log("INBOX brand failed, uploading without watermark:", str(e)[:150]); return path

# ---------- upload ----------
def upload_next(yt_mod, access, log=print, work="out"):
    items = pending()
    if not items: log("INBOX: empty, nothing to upload"); return False
    base, sj, sm = items[0]
    meta = json.loads(_get_bytes(f"inbox/pending/{base}.json").decode())
    os.makedirs(work, exist_ok=True); path = f"{work}/inbox.mp4"
    open(path, "wb").write(_get_bytes(f"inbox/pending/{base}.mp4"))
    cap = (meta.get("caption") or "").strip() or describe(path, log)
    log("INBOX caption used:", cap[:60])
    title, desc, tags = make_meta(cap)
    path = brand(path, f"{work}/inbox_wm.mp4", log=log)
    vid, privacy = yt_mod.upload(access, path, title, desc, tags, synthetic=False)
    log("uploaded:", vid, "privacy:", privacy, "| title:", title, f"| inbox left: {len(items) - 1}")
    _delete(f"inbox/pending/{base}.mp4", sm); _delete(f"inbox/pending/{base}.json", sj)
    try:
        st = _state()
        if st.get("owner"): _say(st["owner"], f"Yuklandi: https://youtube.com/shorts/{vid}\nNavbatda qoldi: {len(items) - 1}")
    except Exception: pass
    return True
