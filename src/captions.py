import os, json, re, requests
BANK = {
 "Autumn Forest Road": ["Leaves turn gold when chlorophyll fades", "Every autumn repaints the road", "Slow down. Breathe. Look around."],
 "Cherry Blossom Paradise": ["Cherry blossoms last only a short time", "Spring arrives in a cloud of pink", "Some moments are meant to be brief"],
 "Frozen Winter Forest": ["Frost turns every branch into art", "Winter makes the whole world quiet", "Silence has a color too"],
 "Hidden Waterfalls": ["Waterfalls carve rock over thousands of years", "The sound of water calms the mind", "Nature hides its best shows"],
 "Lavender Fields": ["Lavender fields glow purple in summer", "Its scent is known for helping people relax", "Rows of color to the horizon"],
 "Turquoise Lagoons": ["Shallow sand makes the water glow turquoise", "Clear water and endless sky", "Paradise has a color"],
 "Above The Clouds": ["Above the clouds the sun always shines", "Mountains rise from a sea of white", "Higher is quieter"],
 "Misty Bamboo Forest": ["Some bamboo grows nearly a meter in a day", "Mist turns a forest into a dream", "Light finds its way through everything"],
 "Red Desert Dunes": ["Wind sculpts dunes into smooth waves", "Sand changes shape with every storm", "Golden hour makes the desert glow"],
 "Northern Lights": ["Auroras happen when solar particles hit our atmosphere", "The sky can dance in green and purple", "Best seen on long dark winter nights"],
 "Mountain Lakes": ["Still water turns mountains into mirrors", "Glacial lakes get color from fine rock dust", "Calm looks like this"],
 "Terraced Fields": ["Farmers shaped these hills by hand over centuries", "Terraces turn steep slopes into green steps", "Patience can shape a mountain"],
}
FALLBACK = ["Nature is full of surprises", "Colors you have to see to believe", "Save this for your next trip"]
MODELS = ["llama-3.3-70b-versatile", "llama-3.1-8b-instant", "openai/gpt-oss-20b", "gemma2-9b-it"]
def make(theme, n=4, log=print):
    keys = [os.environ.get("GROQ_API_KEY", "")]
    prompt = (f"Write {n} short on-screen captions (max 8 words each) for a calm nature Short about: {theme}. "
              "Each caption is a vivid description or a well-known true fact. No emojis, no invented place names, no statistics. "
              f"Return only a JSON array of {n} strings.")
    for k in keys:
        if not k: continue
        for model in MODELS:
            try:
                r = requests.post("https://api.groq.com/openai/v1/chat/completions", headers={"Authorization": f"Bearer {k}"},
                    json={"model": model, "messages": [{"role": "user", "content": prompt}], "temperature": 0.8}, timeout=40)
                if r.status_code in (404, 400): log(f"groq {model}: HTTP {r.status_code} {r.text[:120]}"); continue
                r.raise_for_status()
                txt = r.json()["choices"][0]["message"]["content"]
                arr = json.loads(re.search(r"\[.*\]", txt, re.S).group(0))
                arr = [str(x).strip()[:70] for x in arr if str(x).strip()][:n]
                if len(arr) == n: return arr
            except Exception as e:
                log("groq failed:", str(e)[:150]); break
    return (BANK.get(theme) or FALLBACK)[:n]
