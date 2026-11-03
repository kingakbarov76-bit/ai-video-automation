import base64, time, requests
MODEL = "@cf/black-forest-labs/flux-1-schnell"
def generate(account_id, token, prompt, steps=8):
    url = f"https://api.cloudflare.com/client/v4/accounts/{account_id}/ai/run/{MODEL}"
    h = {"Authorization": f"Bearer {token}"}
    last = None
    for attempt in range(3):
        r = requests.post(url, headers=h, json={"prompt": prompt, "steps": steps}, timeout=120)
        if r.status_code == 200:
            j = r.json()
            img = (j.get("result") or {}).get("image")
            if img:
                return base64.b64decode(img)
            last = f"no image in response: {str(j)[:200]}"
        else:
            last = f"HTTP {r.status_code}: {r.text[:300]}"
        time.sleep(4 * (attempt + 1))
    raise RuntimeError(last)
def verify(account_id, token):
    r = requests.get(f"https://api.cloudflare.com/client/v4/accounts/{account_id}/tokens/verify",
                     headers={"Authorization": f"Bearer {token}"}, timeout=30)
    return r.status_code, r.text[:300]
