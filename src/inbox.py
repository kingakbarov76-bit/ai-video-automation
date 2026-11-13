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
def _list(path, br=None):
    r = requests.get(_contents(path), headers=music._gh(), params={"ref": br or music.BRANCH}, timeout=30)
    return r.json() if r.status_code == 200 and isinstance(r.json(), list) else []
def _get_bytes(path, br=None):
    h = dict(music._gh()); h["Accept"] = "application/vnd.github.raw"
    r = requests.get(_contents(path), headers=h, params={"ref": br or music.BRANCH}, timeout=120)
    r.raise_for_status(); return r.content
def _delete(path, sha, br=None):
    requests.delete(_contents(path), headers=music._gh(), timeout=60,
                    json={"message": f"inbox done {path}", "sha": sha, "branch": br or music.BRANCH})
# Videos live on their own branch so it can be wiped from time to time (git history would otherwise keep every video forever).
STORE = "inbox-store"
def _ensure_store():
    g = f"{music.GH}/repos/{music.REPO}/git"
    if requests.get(f"{g}/ref/heads/{STORE}", headers=music._gh(), timeout=30).status_code == 200: return
    main = requests.get(f"{g}/ref/heads/main", headers=music._gh(), timeout=30).json()["object"]["sha"]
    r = requests.post(f"{g}/refs", headers=music._gh(), json={"ref": f"refs/heads/{STORE}", "sha": main}, timeout=30)
    if r.status_code not in (200, 201): raise RuntimeError(f"store branch: {r.status_code} {r.text[:150]}")
def _put_store(path, data, msg):
    _ensure_store()
    old = requests.get(_contents(path), headers=music._gh(), params={"ref": STORE}, timeout=30)
    body = {"message": msg, "branch": STORE, "content": base64.b64encode(data).decode()}
    if old.status_code == 200: body["sha"] = old.json()["sha"]
    r = requests.put(_contents(path), headers=music._gh(), json=body, timeout=180)
    if r.status_code not in (200, 201): raise RuntimeError(f"store put {path}: HTTP {r.status_code} {r.text[:150]}")
def cleanup(log=print):
    """Queue empty and not done for 20 h: delete the store branch (frees old video blobs); it is recreated on the next video."""
    st = _state()
    if time.time() - st.get("last_clean", 0) < 20 * 3600 or pending(): return
    r = requests.delete(f"{music.GH}/repos/{music.REPO}/git/refs/heads/{STORE}", headers=music._gh(), timeout=30)
    st["last_clean"] = time.time(); _save_state(st); log("INBOX: store branch wiped", r.status_code)
def pending():
    """[(base_name, sha_json, None)] oldest first. Only a tiny json (Telegram file_id + caption) is stored: the video stays on Telegram's servers."""
    return [(f["name"][:-5], f["sha"], None) for f in sorted(_list("inbox/pending", STORE), key=lambda f: f["name"]) if f["name"].endswith(".json")]

# ---------- metadata ----------
def clean_cap(cap):
    """Drop zero-width chars and downloader-bot signature lines (e.g. '@utezbot orqali yuklab olindi')."""
    cap = re.sub(r"[\u200b\u200c\u200d\ufeff]", "", cap or "")
    return "\n".join(l for l in cap.splitlines() if "utezbot" not in l.lower() and "yuklab olindi" not in l.lower() and "📥" not in l).strip()
def _words(s): return [w for w in re.findall(r"[A-Za-z][A-Za-z'-]{2,}", s)]
def make_meta(caption):
    """Search-oriented title/description/tags from a short scene phrase (or the owner's caption: 'Title | extra')."""
    cap = (caption or "").strip()
    scene, _, extra = cap.partition("|")
    scene = re.sub(r"\s+", " ", scene).strip(" -:.") or "Beautiful nature scenery"
    scene = scene[:1].upper() + scene[1:]
    title = f"{scene} \U0001F33F Relaxing Nature Sounds to Calm Your Mind"
    if len(title) > 100: title = f"{scene[:60]} \U0001F33F Relaxing Nature Sounds"
    words = [w.lower() for w in _words(scene)]
    desc = (f"{scene}. Relax with calming nature scenery and soothing sounds, perfect for sleep, study, meditation and stress relief.\n"
            + (extra.strip() + "\n" if extra.strip() else "") +
            "\n#nature #relaxing #calmnature\n\n"
            f"\U0001F30D Dreamy Earth shows the most beautiful places on Earth. Subscribe for a new calming nature video every day: {SUB}\n\n"
            "Watch for: relaxing nature sounds, calm nature video, nature ambience, beautiful scenery, nature sounds for sleep, "
            "peaceful nature, scenic views, nature relaxation, travel destinations, places on earth.\n\n"
            "#shorts #naturesounds #scenery #beautifulplaces #travel")
    tags = list(dict.fromkeys([scene.lower()] + words[:5] + ["relaxing nature sounds", "nature sounds", "calm nature", "nature ambience",
            "nature for sleep", "relaxing videos", "beautiful nature", "scenic nature", "nature shorts", "travel", "shorts"]))[:15]
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
    allowed = {x.strip() for x in os.environ.get("TG_CHAT_IDS", "").split(",") if x.strip()}
    if str(chat) in allowed: owner = uid = "chat"      # videos posted in the owner's own channel/group are trusted
    elif owner is None:
        if txt.startswith("/start"):
            st["owner"] = uid; _save_state(st); owner = uid
            _say(chat, "Salom! Men Dreamy Earth boti. Video yuboring, izohga joy nomini yozing (masalan: Bali). "
                       "Men uni sarlavha va heshteglar bilan YouTube'ga navbat bilan yuklayman.")
            return
        _say(chat, "Boshlash uchun /start yozing."); return
    if uid != owner: _say(chat, "Bu bot shaxsiy."); return
    if txt.startswith("/stats"):
        try:
            from src import yt as _y
            import main as _m
            for c in (owner_targets() or [chat]): _say(c, stats_text(_y, _m._yt()))
        except Exception as e: _say(chat, "Statistikani olib bo'lmadi: " + str(e)[:100])
        return
    if txt.startswith("/davom"):
        st["hold"] = False; _save_state(st); _say(chat, "Tasdiqlandi: videolar sizniki yoki ishlatishga ruxsati bor. Yuklash davom etadi."); return
    if txt.startswith("/toxta"):
        st["hold"] = True; _save_state(st); _say(chat, "Yuklash to'xtatildi. Davom ettirish: /davom"); return
    if txt.startswith("/status") or txt.startswith("/start"):
        _say(chat, f"Navbatda: {len(pending())} ta video." + (" (To'xtatilgan: /davom)" if st.get("hold") else "")); return
    v = m.get("video") or (m.get("document") if str((m.get("document") or {}).get("mime_type", "")).startswith("video/") else None)
    if not v:
        _say(chat, "Video yuboring (izohga joy nomi). /status - navbat."); return
    if v.get("file_size", 0) > MAX_BYTES:
        _say(chat, "Video 20 MB dan katta, Telegram bot uni ololmaydi. Kichikroq (siqilgan) yuboring."); return
    dur, w, h, sz = int(v.get("duration", 0) or 0), int(v.get("width", 0) or 0), int(v.get("height", 0) or 0), int(v.get("file_size", 0) or 0)
    if dur and dur < 3: _say(chat, "Video juda qisqa (3 soniyadan kam), qabul qilmadim."); return
    if dur > 900: _say(chat, "Video 15 daqiqadan uzun, qabul qilmadim."); return
    keys = [f"u:{v.get('file_unique_id', '')}", f"f:{dur}-{w}-{h}-{sz}"]      # same file re-sent -> same unique id / same fingerprint
    seen = st.get("seen", [])
    if any(k in seen for k in keys if not k.endswith(":")) and sz:
        _say(chat, "Bu video avval qabul qilingan, qayta qo'shmadim."); return
    st["seen"] = (seen + keys)[-3000:]; _save_state(st)
    notes = []
    if w and h and w > h: notes.append("gorizontal (Shorts bo'lmaydi)")
    if dur > 180: notes.append("180 soniyadan uzun (Shorts bo'lmaydi)")
    base = f"{int(time.time())}_{v.get('file_unique_id', 'x')}"
    cap = clean_cap(m.get("caption"))   # downloader-bot signatures are not titles
    # empty caption -> the scene is described automatically at upload time
    _put_store(f"inbox/pending/{base}.json", json.dumps({"caption": cap, "added": time.time(), "file_id": v["file_id"], "size": v.get("file_size", 0)}).encode(), f"inbox meta {base}")
    log(f"INBOX: queued {base} ({v.get('file_size', 0) // 1024} KB) caption={cap[:40]!r}")
    _say(chat, f"Qabul qilindi. Navbatda: {len(pending())} ta." + ("" if cap else " Sarlavhani o'zim topaman.") + (" Eslatma: " + ", ".join(notes) if notes else ""))

def poll_loop(log=print):
    if not _tok(): return
    try: music.ensure_branch(log)
    except Exception as e: log("inbox branch:", str(e)[:100])
    off = None
    log("INBOX: telegram polling started")
    while True:
        try:
            r = requests.post(f"{TG}/bot{_tok()}/getUpdates", json={"timeout": 50, "offset": off, "allowed_updates": ["message", "channel_post"]}, timeout=70).json()
            for u in r.get("result", []):
                off = u["update_id"] + 1
                try:
                    mm = u.get("message") or u.get("channel_post")
                    if mm: _handle(mm, log)
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
def brand(path, out, text="Dreamy Earth", log=print):
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
        x = int(w * 0.04); y = int(h * 0.125)
        d.text((x + 2, y + 2), text, font=font, fill=(0, 0, 0, 110)); d.text((x, y), text, font=font, fill=(255, 255, 255, 200))
        png = path + ".wm.png"; im.save(png)
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", path, "-i", png, "-filter_complex",
                        f"[0:v]scale={w}:{h}[b];[b][1:v]overlay=0:0,format=yuv420p[v]", "-map", "[v]", "-map", "0:a?", "-c:v", "libx264",
                        "-preset", "veryfast", "-crf", "23", "-threads", "1", "-c:a", "copy", "-movflags", "+faststart", out], check=True, timeout=600)
        return out
    except Exception as e:
        log("INBOX brand failed, uploading without watermark:", str(e)[:150]); return path

# ---------- statistics report ----------
def stats_text(yt_mod, access):
    h = {"Authorization": f"Bearer {access}"}
    ch = requests.get("https://www.googleapis.com/youtube/v3/channels", headers=h, params={"part": "statistics", "mine": "true"}, timeout=30).json()["items"][0]["statistics"]
    vids = yt_mod.my_videos_stats(access, limit=50)
    vids.sort(key=lambda v: v["published"], reverse=True)
    lines = [f"\U0001F30D Dreamy Earth\n\U0001F4CA YouTube statistikasi", f"Obunachilar: {ch.get('subscriberCount', '?')} | Jami ko'rish: {ch.get('viewCount', '?')} | Videolar: {ch.get('videoCount', '?')}",
             f"Navbatda: {len(pending())} ta video", "", "So'nggi videolar:"]
    for v in vids[:6]:
        lines.append(f"- {v['title'][:45]}: {v['views']} ko'rish, {v['likes']} layk ({v['published'][5:10]})")
    top = sorted(vids, key=lambda v: v["views"], reverse=True)[:1]
    if top: lines += ["", f"Eng ko'p ko'rilgan: {top[0]['title'][:45]} ({top[0]['views']})"]
    return "\n".join(lines)
def owner_targets():
    st = _state(); return [st["owner"]] if st.get("owner") else []
def channel_targets():
    return [x.strip() for x in os.environ.get("TG_CHAT_IDS", "").split(",") if x.strip()]
def maybe_report(yt_mod, access, log=print, every_h=20, force=False):
    """Once a day, at 09:00-09:59 Tashkent time."""
    st = _state()
    hour = (time.gmtime(time.time() + 5 * 3600)).tm_hour
    if not force and (hour != 9 or time.time() - st.get("last_report", 0) < every_h * 3600): return
    txt = stats_text(yt_mod, access)
    for c in owner_targets(): _say(c, txt)
    st["last_report"] = time.time(); _save_state(st); log("INBOX: stats report sent")

# ---------- outbox: messages written by other jobs (e.g. Instagram posting/stats) are forwarded to Telegram ----------
def flush_outbox(log=print):
    for f in _list("inbox/outbox"):
        if not f["name"].endswith(".txt"): continue
        try:
            txt = _get_bytes(f"inbox/outbox/{f['name']}").decode()[:3500]
            if not txt.lstrip().startswith("\U0001F30D"): txt = "\U0001F30D Dreamy Earth\n" + txt
            for c in (owner_targets() if f["name"].startswith("igstats") else channel_targets()): _say(c, txt)
            _delete(f"inbox/outbox/{f['name']}", f["sha"]); log("INBOX: outbox message sent:", f["name"])
        except Exception as e: log("INBOX outbox error:", str(e)[:120])

# ---------- upload ----------
def upload_next(yt_mod, access, log=print, work="out"):
    items = pending()
    if not items: log("INBOX: empty, nothing to upload"); return False
    base, sj, sm = items[0]
    meta = json.loads(_get_bytes(f"inbox/pending/{base}.json", STORE).decode())
    os.makedirs(work, exist_ok=True); path = f"{work}/inbox.mp4"
    if meta.get("file_id"):
        fp = _api("getFile", file_id=meta["file_id"]).get("result", {}).get("file_path")
        if not fp: raise RuntimeError("telegram getFile failed for " + base)
        open(path, "wb").write(requests.get(f"{TG}/file/bot{_tok()}/{fp}", timeout=180).content)
    else:      # legacy item queued before the file_id change: the video itself is on the store branch
        open(path, "wb").write(_get_bytes(f"inbox/pending/{base}.mp4", STORE))
    cap = clean_cap(meta.get("caption")) or describe(path, log)
    log("INBOX caption used:", cap[:60])
    title, desc, tags = make_meta(cap)
    path = brand(path, f"{work}/inbox_wm.mp4", log=log)
    vid, privacy = yt_mod.upload(access, path, title, desc, tags, synthetic=False)
    log("uploaded:", vid, "privacy:", privacy, "| title:", title, f"| inbox left: {len(items) - 1}")
    try:      # same video to Instagram Reels (the file is served publicly for a few minutes, then removed)
        from . import igpost
        os.makedirs("out/ig", exist_ok=True); igf = f"out/ig/{vid}.mp4"; import shutil; shutil.copy(path, igf)
        base_url = os.environ.get("RENDER_EXTERNAL_URL", "https://yt-auto-shorts.onrender.com").rstrip("/")
        igpost.publish_reel(f"{base_url}/media/{vid}.mp4", title + "\n\nFollow @dreamyearthh for more beautiful places\n" +
                            "#nature #relaxing #calmnature #naturesounds #scenery #beautifulplaces #travel #reels #asmr #peaceful", log)
    except Exception as e: log("IG failed (YouTube upload is fine):", str(e)[:200])
    finally:
        try: os.remove(f"out/ig/{vid}.mp4")
        except OSError: pass
    _delete(f"inbox/pending/{base}.json", sj, STORE)
    if not meta.get("file_id"):
        for f in _list("inbox/pending", STORE):
            if f["name"] == base + ".mp4": _delete(f"inbox/pending/{base}.mp4", f["sha"], STORE)
    try:
        for c in channel_targets(): _say(c, f"\U0001F30D Dreamy Earth\n\u25B6\uFE0F YouTube'ga joylandi: {title}\nhttps://youtube.com/shorts/{vid}\nNavbatda qoldi: {len(items) - 1}")
    except Exception: pass
    return True
