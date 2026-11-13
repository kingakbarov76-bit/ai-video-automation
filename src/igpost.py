"""Instagram Reels publishing through the official Instagram API (Instagram Login). Token is kept on the music-library branch."""
import os, json, time, requests
from . import music
G = "https://graph.instagram.com"
def _redirect(): return os.environ.get("RENDER_EXTERNAL_URL", "https://yt-auto-shorts.onrender.com").rstrip("/") + "/ig-auth"
def auth_link():
    return ("https://www.instagram.com/oauth/authorize?" + "&".join([f"client_id={os.environ.get('IG_APP_ID', '').strip()}",
            f"redirect_uri={_redirect()}", "response_type=code", "scope=instagram_business_basic,instagram_business_content_publish"]))
def exchange(code):
    """code from the redirect -> long-lived token stored on GitHub. Returns username/user id text."""
    cid, sec = os.environ.get("IG_APP_ID", "").strip(), os.environ.get("IG_APP_SECRET", "").strip()
    code = code.split("#")[0]
    r = requests.post("https://api.instagram.com/oauth/access_token", timeout=30, data={"client_id": cid, "client_secret": sec,
                      "grant_type": "authorization_code", "redirect_uri": _redirect(), "code": code}).json()
    if "access_token" not in r: raise RuntimeError("short token: " + json.dumps(r)[:300])
    uid = str(r.get("user_id") or (r.get("data") or [{}])[0].get("user_id"))
    l = requests.get(f"{G}/access_token", timeout=30, params={"grant_type": "ig_exchange_token", "client_secret": sec, "access_token": r["access_token"]}).json()
    if "access_token" not in l: raise RuntimeError("long token: " + json.dumps(l)[:300])
    music.ensure_branch()
    music._put("inbox/ig_token.json", json.dumps({"token": l["access_token"], "user_id": uid, "expires": time.time() + l.get("expires_in", 5184000)}).encode(), "ig token")
    return uid
def _token(log=print):
    t, _ = music._get_text("inbox/ig_token.json")
    if not t: return None, None
    d = json.loads(t)
    if d["expires"] - time.time() < 20 * 86400:      # refresh the 60-day token while it is still valid
        try:
            r = requests.get(f"{G}/refresh_access_token", timeout=30, params={"grant_type": "ig_refresh_token", "access_token": d["token"]}).json()
            if "access_token" in r:
                d["token"] = r["access_token"]; d["expires"] = time.time() + r.get("expires_in", 5184000)
                music._put("inbox/ig_token.json", json.dumps(d).encode(), "ig token refresh"); log("IG: token refreshed")
        except Exception as e: log("IG refresh failed:", str(e)[:100])
    return d["token"], d["user_id"]
def publish_reel(video_url, caption, log=print):
    tok, uid = _token(log)
    if not tok: log("IG: not connected (open /ig-auth), skipping"); return None
    r = requests.post(f"{G}/v21.0/{uid}/media", timeout=60, data={"media_type": "REELS", "video_url": video_url, "caption": caption[:2150],
                      "share_to_feed": "true", "access_token": tok}).json()
    cid = r.get("id")
    if not cid: raise RuntimeError("IG container: " + json.dumps(r)[:300])
    for _ in range(40):
        time.sleep(8)
        s = requests.get(f"{G}/v21.0/{cid}", timeout=30, params={"fields": "status_code,status", "access_token": tok}).json()
        if s.get("status_code") == "FINISHED": break
        if s.get("status_code") in ("ERROR", "EXPIRED"): raise RuntimeError("IG processing: " + json.dumps(s)[:300])
    else: raise RuntimeError("IG processing timeout")
    p = requests.post(f"{G}/v21.0/{uid}/media_publish", timeout=60, data={"creation_id": cid, "access_token": tok}).json()
    if "id" not in p: raise RuntimeError("IG publish: " + json.dumps(p)[:300])
    log("IG: published reel", p["id"]); return p["id"]
