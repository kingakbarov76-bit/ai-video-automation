import os, json, re, requests
FALLBACK = ["Nature is full of surprises", "Colors you have to see to believe", "Every season paints a new world", "Save this for your next trip"]
def make(theme, n=4, log=print):
    keys = [os.environ.get("GROQ_API_KEY", "")]
    prompt = (f"Write {n} short on-screen captions (max 8 words each) for a calm nature Short about: {theme}. "
              "Each caption is a vivid description or a well-known true fact. No emojis, no invented place names, no statistics. "
              f"Return only a JSON array of {n} strings.")
    for k in keys:
        if not k: continue
        try:
            r = requests.post("https://api.groq.com/openai/v1/chat/completions", headers={"Authorization": f"Bearer {k}"},
                json={"model": "llama-3.1-8b-instant", "messages": [{"role": "user", "content": prompt}], "temperature": 0.8}, timeout=40)
            r.raise_for_status()
            txt = r.json()["choices"][0]["message"]["content"]
            arr = json.loads(re.search(r"\[.*\]", txt, re.S).group(0))
            arr = [str(x).strip()[:70] for x in arr if str(x).strip()][:n]
            if len(arr) == n: return arr
        except Exception as e:
            log("groq failed:", str(e)[:150])
    return FALLBACK[:n]
