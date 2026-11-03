import re, datetime
def run(videos, theme_names):
    """Learn which themes earn views fastest. Returns (weights, summary lines). Uses only data from YouTube itself."""
    now = datetime.datetime.now(datetime.timezone.utc); per = {}; lines = []
    vids = []
    for v in videos:
        try: age = max(1.0, (now - datetime.datetime.fromisoformat(v["published"].replace("Z", "+00:00"))).total_seconds() / 3600)
        except Exception: continue
        vids.append((v, age))
        m = re.search(r"Featuring: (.+?)\.\n", v["description"] + "\n")
        for t in (m.group(1).split(", ") if m else []):
            per.setdefault(t.strip(), []).append((v["views"], min(age, 72)))
    for v, age in sorted(vids, key=lambda x: -x[0]["views"])[:5]:
        lines.append(f"{v['id']} views={v['views']} likes={v['likes']} age_h={age:.0f}")
    weights = {}
    for t in theme_names:
        pts = [(vw, ag) for vw, ag in per.get(t, []) if ag >= 6]
        if len(pts) >= 2: weights[t] = 1 + sum(vw for vw, _ in pts) / max(1.0, sum(ag for _, ag in pts))
        else: weights[t] = 2.0   # explore themes with little data
    total_views = sum(v["views"] for v, _ in vids); n = len(vids)
    summ = f"videos={n} total_views={total_views} avg={total_views / max(1, n):.0f}"
    best = sorted(weights.items(), key=lambda x: -x[1])[:3]
    return weights, summ + " | top themes: " + ", ".join(f"{k}({w:.1f})" for k, w in best), lines
