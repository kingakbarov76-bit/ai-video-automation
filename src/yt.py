import os, json, requests
TOKEN_URL = "https://oauth2.googleapis.com/token"
def access_token(client_id, client_secret, refresh_token):
    r = requests.post(TOKEN_URL, data={"client_id": client_id, "client_secret": client_secret,
                      "refresh_token": refresh_token, "grant_type": "refresh_token"}, timeout=30)
    if r.status_code != 200: raise RuntimeError(f"token refresh failed HTTP {r.status_code}: {r.text[:300]}")
    return r.json()["access_token"]
def upload(access, path, title, description, tags, privacy="public", synthetic=True, category="19"):
    meta = {"snippet": {"title": title[:100], "description": description[:4900], "tags": tags, "categoryId": category},
            "status": {"privacyStatus": privacy, "selfDeclaredMadeForKids": False, "containsSyntheticMedia": synthetic}}
    size = os.path.getsize(path)
    h = {"Authorization": f"Bearer {access}", "Content-Type": "application/json; charset=UTF-8",
         "X-Upload-Content-Length": str(size), "X-Upload-Content-Type": "video/mp4"}
    r = requests.post("https://www.googleapis.com/upload/youtube/v3/videos?uploadType=resumable&part=snippet,status",
                      headers=h, data=json.dumps(meta), timeout=60)
    if r.status_code != 200: raise RuntimeError(f"init failed HTTP {r.status_code}: {r.text[:400]}")
    loc = r.headers["Location"]
    with open(path, "rb") as f:
        r2 = requests.put(loc, data=f, headers={"Content-Type": "video/mp4", "Content-Length": str(size)}, timeout=600)
    if r2.status_code not in (200, 201): raise RuntimeError(f"upload failed HTTP {r2.status_code}: {r2.text[:400]}")
    j = r2.json()
    return j.get("id"), j.get("status", {}).get("privacyStatus")

def brand(access, description, keywords, banner_png):
    h = {"Authorization": f"Bearer {access}"}
    r = requests.get("https://www.googleapis.com/youtube/v3/channels", headers=h, params={"part": "id,brandingSettings", "mine": "true"}, timeout=30)
    r.raise_for_status(); ch = r.json()["items"][0]; cid = ch["id"]
    bs = ch.get("brandingSettings", {}) or {}; chan = dict(bs.get("channel", {}) or {})
    chan["description"] = description; chan["keywords"] = keywords
    res = []
    img = dict(bs.get("image", {}) or {})
    with open(banner_png, "rb") as f:
        rb = requests.post("https://www.googleapis.com/upload/youtube/v3/channelBanners/insert?uploadType=media",
                           headers=dict(h, **{"Content-Type": "image/png"}), data=f.read(), timeout=120)
    if rb.status_code == 200 and rb.json().get("url"):
        img["bannerExternalUrl"] = rb.json()["url"]; res.append("banner uploaded")
    else:
        res.append(f"banner failed HTTP {rb.status_code}: {rb.text[:200]}")
    body = {"id": cid, "brandingSettings": {"channel": chan, "image": img}}
    ru = requests.put("https://www.googleapis.com/youtube/v3/channels?part=brandingSettings", headers=dict(h, **{"Content-Type": "application/json"}),
                      data=json.dumps(body), timeout=60)
    res.append(f"channel update HTTP {ru.status_code}" + ("" if ru.status_code == 200 else ": " + ru.text[:300]))
    return "; ".join(res)

def my_videos_stats(access, limit=50):
    h = {"Authorization": f"Bearer {access}"}
    r = requests.get("https://www.googleapis.com/youtube/v3/channels", headers=h, params={"part": "contentDetails", "mine": "true"}, timeout=30)
    r.raise_for_status()
    up = r.json()["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]
    r = requests.get("https://www.googleapis.com/youtube/v3/playlistItems", headers=h, params={"part": "contentDetails", "playlistId": up, "maxResults": limit}, timeout=30)
    r.raise_for_status(); ids = [i["contentDetails"]["videoId"] for i in r.json().get("items", [])]
    if not ids: return []
    r = requests.get("https://www.googleapis.com/youtube/v3/videos", headers=h, params={"part": "snippet,statistics", "id": ",".join(ids)}, timeout=30)
    r.raise_for_status(); out = []
    for v in r.json().get("items", []):
        st = v.get("statistics", {}); sn = v["snippet"]
        out.append({"id": v["id"], "title": sn.get("title", ""), "published": sn.get("publishedAt", ""), "description": sn.get("description", ""),
                    "views": int(st.get("viewCount", 0)), "likes": int(st.get("likeCount", 0)), "comments": int(st.get("commentCount", 0))})
    return out

def upload_stats(access):
    """(minutes since newest upload, uploads in last 24h). 2 quota units."""
    import datetime
    h = {"Authorization": f"Bearer {access}"}
    r = requests.get("https://www.googleapis.com/youtube/v3/channels", headers=h, params={"part": "contentDetails", "mine": "true"}, timeout=30)
    r.raise_for_status(); up = r.json()["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]
    r = requests.get("https://www.googleapis.com/youtube/v3/playlistItems", headers=h, params={"part": "contentDetails", "playlistId": up, "maxResults": 12}, timeout=30)
    r.raise_for_status(); items = r.json().get("items", [])
    ts = [datetime.datetime.fromisoformat(i["contentDetails"]["videoPublishedAt"].replace("Z", "+00:00")) for i in items if i["contentDetails"].get("videoPublishedAt")]
    if not ts: return None, 0
    now = datetime.datetime.now(datetime.timezone.utc)
    return (now - max(ts)).total_seconds() / 60, sum(1 for t in ts if (now - t).total_seconds() < 86400)
