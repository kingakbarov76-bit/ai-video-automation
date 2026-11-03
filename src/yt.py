import os, json, requests
TOKEN_URL = "https://oauth2.googleapis.com/token"
def access_token(client_id, client_secret, refresh_token):
    r = requests.post(TOKEN_URL, data={"client_id": client_id, "client_secret": client_secret,
                      "refresh_token": refresh_token, "grant_type": "refresh_token"}, timeout=30)
    if r.status_code != 200: raise RuntimeError(f"token refresh failed HTTP {r.status_code}: {r.text[:300]}")
    return r.json()["access_token"]
def upload(access, path, title, description, tags, privacy="public"):
    meta = {"snippet": {"title": title[:100], "description": description, "tags": tags, "categoryId": "22"},
            "status": {"privacyStatus": privacy, "selfDeclaredMadeForKids": False, "containsSyntheticMedia": True}}
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
