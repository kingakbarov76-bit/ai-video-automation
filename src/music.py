"""Music sources: ACE-Step 1.5 (HF Space, via user's HF token) -> ccMixter (CC BY, commercial OK) -> built-in synth."""
import os, json, shutil, requests
SPACE = os.environ.get("ACE_SPACE", "ACE-Step/Ace-Step-v1.5")
def _client(log=print):
    from gradio_client import Client
    tok = os.environ.get("HF_TOKEN", "").strip()
    try: return Client(SPACE, token=tok or None, verbose=False)
    except TypeError: return Client(SPACE, hf_token=tok or None, verbose=False)
def inspect(log=print):
    c = _client(log)
    info = c.view_api(return_format="dict", print_info=False) or {}
    eps = info.get("named_endpoints", {})
    log(f"ACE space endpoints: {len(eps)}")
    for name, ep in eps.items():
        params = [f"{p.get('parameter_name')}={str(p.get('parameter_default'))[:30]}" for p in ep.get("parameters", [])]
        rets = [r.get("label") or r.get("component") for r in ep.get("returns", [])]
        log(f"  EP {name} | params({len(params)}): {', '.join(params)[:900]} | returns: {rets}")
    return info
def ccmixter(limit=10, log=print):
    r = requests.get("http://ccmixter.org/api/query", params={"f": "json", "lic": "open", "tags": "instrumental",
                     "limit": limit, "sort": "rank"}, timeout=40)
    r.raise_for_status(); items = r.json(); out = []
    for it in items:
        files = it.get("files") or []
        mp3 = next((f.get("download_url") for f in files if str(f.get("download_url", "")).lower().endswith(".mp3")), None)
        out.append({"title": it.get("upload_name"), "artist": it.get("user_name"), "license": it.get("license_name"),
                    "license_url": it.get("license_url"), "page": it.get("file_page_url"), "mp3": mp3})
    log(f"ccmixter: {len(out)} results")
    for o in out[:6]: log("  ccm:", json.dumps(o)[:300])
    return out
def runtime(log=print):
    try:
        h = {"Authorization": "Bearer " + os.environ.get("HF_TOKEN", "")}
        r = requests.get(f"https://huggingface.co/api/spaces/{SPACE}/runtime", headers=h, timeout=30)
        log("ACE runtime:", r.status_code, r.text[:300])
        r = requests.get("https://huggingface.co/api/whoami-v2", headers=h, timeout=30)
        j = r.json() if r.ok else {}
        log("HF whoami:", r.status_code, j.get("name"), "type", j.get("type"), "pro", j.get("isPro"), "auth", json.dumps(j.get("auth", {}))[:300])
    except Exception as e: log("runtime err", str(e)[:150])
def gh_runs(log=print):
    r = requests.get(f"{GH}/repos/{REPO}/actions/runs", headers=_gh(), params={"per_page": 15}, timeout=30)
    if r.status_code != 200: log("gh runs:", r.status_code, r.text[:150]); return
    for w in r.json().get("workflow_runs", []):
        log(f"  RUN {w.get('name')} event={w.get('event')} status={w.get('status')}/{w.get('conclusion')} created={w.get('created_at')}")
    r = requests.get(f"{GH}/repos/{REPO}/actions/workflows", headers=_gh(), timeout=30)
    for w in (r.json().get("workflows", []) if r.ok else []): log(f"  WF {w.get('name')} state={w.get('state')} path={w.get('path')}")
def test(log=print):
    os.makedirs("out", exist_ok=True)
    try: gh_runs(log)
    except Exception as e: log("gh runs err", str(e)[:120])
    runtime(log)
    try: selftest(log)
    except Exception as e: log("library selftest failed:", str(e)[:200])
    try: ccmixter(10, log)
    except Exception as e: log("ccmixter failed:", str(e)[:200])
    if os.environ.get("ACE_TEST") == "1":
        try:
            p = generate("out/music_test.mp3", 0, 20, 116, log); describe(p, log); log("ACE OK: listen at /music.mp3")
        except Exception as e: log("ACE generate failed:", type(e).__name__, str(e)[:400])

STYLES = [
 "uplifting cinematic electronic, atmospheric pads, deep sub bass, punchy drums, dreamy travel montage",
 "mysterious ambient phonk, deep 808 bass, crisp hi-hats, dark atmospheric synth, hypnotic",
 "euphoric melodic house, bright plucks, warm chords, four on the floor kick, summer travel vibe",
 "epic cinematic orchestral hybrid, soaring strings, big drums, wonder and awe",
 "chill future bass, lush supersaw chords, soft vocal chops, relaxing yet energetic",
 "space ambient synthwave, shimmering arpeggios, warm analog bass, cosmic and dreamy",
]
def _path(x):
    if isinstance(x, dict): return x.get("path") or x.get("name") or x.get("url")
    return x
def generate(out_path, style_idx=0, seconds=20, bpm=116, log=print, timeout=600):
    c = _client(log)
    info = c.view_api(return_format="dict", print_info=False)
    params = info["named_endpoints"]["/generation_wrapper"]["parameters"]
    over = {"generation_mode": "custom", "param_4": STYLES[style_idx % len(STYLES)] + ", instrumental, no vocals",
            "param_5": "[Instrumental]", "param_6": bpm, "param_15": seconds, "param_16": 1, "param_30": "mp3"}
    args = [over.get(p.get("parameter_name"), p.get("parameter_default")) for p in params]
    log(f"ACE submit with {len(args)} args")
    job = c.submit(*args, api_name="/generation_wrapper")
    import time as _t
    t0 = _t.time(); last = None
    while not job.done():
        if _t.time() - t0 > timeout: job.cancel(); raise TimeoutError(f"ACE timeout, last status {last}")
        try:
            st = job.status(); cur = f"{getattr(st, 'code', '')} rank={getattr(st, 'rank', '')} queue={getattr(st, 'queue_size', '')} eta={getattr(st, 'eta', '')} msg={str(getattr(st, 'log', '') or getattr(st, 'message', ''))[:120]}"
            if cur != last: log("ACE status:", cur); last = cur
        except Exception as e: log("status err", str(e)[:100])
        _t.sleep(10)
    res = job.result()
    first = _path(res[0] if isinstance(res, (list, tuple)) else res)
    status = res[10] if isinstance(res, (list, tuple)) and len(res) > 10 else ""
    log("ACE status:", str(status)[:200])
    if not first or not os.path.exists(str(first)): raise RuntimeError(f"no audio in result: {str(res)[:300]}")
    shutil.copy(first, out_path); return out_path
def describe(path, log=print):
    import subprocess, numpy as np
    d = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path], capture_output=True, text=True).stdout.strip()
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-ac", "1", "-ar", "22050", "-f", "s16le", "-"], capture_output=True).stdout
    x = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768
    rms = float(np.sqrt((x ** 2).mean())) if len(x) else 0
    log(f"music file: {os.path.getsize(path)} bytes, duration {d}s, rms {rms:.3f}, peak {float(np.abs(x).max()) if len(x) else 0:.2f}")

# ---------------- library on a separate GitHub branch (does not trigger deploys) ----------------
import base64, random, time, re
REPO = os.environ.get("MUSIC_REPO", "kingakbarov76-bit/ai-video-automation")
BRANCH = "music-library"
GH = "https://api.github.com"
def _gh():
    return {"Authorization": f"Bearer {os.environ.get('GH_PAT', '').strip()}", "Accept": "application/vnd.github+json"}
def ensure_branch(log=print):
    r = requests.get(f"{GH}/repos/{REPO}/git/ref/heads/{BRANCH}", headers=_gh(), timeout=30)
    if r.status_code == 200: return True
    m = requests.get(f"{GH}/repos/{REPO}/git/ref/heads/main", headers=_gh(), timeout=30); m.raise_for_status()
    c = requests.post(f"{GH}/repos/{REPO}/git/refs", headers=_gh(), json={"ref": f"refs/heads/{BRANCH}", "sha": m.json()["object"]["sha"]}, timeout=30)
    log("create music branch:", c.status_code); return c.status_code in (200, 201)
def lib_list():
    r = requests.get(f"{GH}/repos/{REPO}/contents/music", headers=_gh(), params={"ref": BRANCH}, timeout=30)
    if r.status_code != 200: return []
    return [f for f in r.json() if f.get("name", "").endswith(".mp3") and not f["name"].startswith("_")]
def _get_text(path):
    r = requests.get(f"{GH}/repos/{REPO}/contents/{path}", headers=_gh(), params={"ref": BRANCH}, timeout=30)
    if r.status_code != 200: return None, None
    j = r.json(); return base64.b64decode(j["content"]).decode(), j["sha"]
def _put(path, data_bytes, msg):
    old = requests.get(f"{GH}/repos/{REPO}/contents/{path}", headers=_gh(), params={"ref": BRANCH}, timeout=30)
    body = {"message": msg, "branch": BRANCH, "content": base64.b64encode(data_bytes).decode()}
    if old.status_code == 200: body["sha"] = old.json()["sha"]
    r = requests.put(f"{GH}/repos/{REPO}/contents/{path}", headers=_gh(), json=body, timeout=120)
    if r.status_code not in (200, 201): raise RuntimeError(f"github put {path}: HTTP {r.status_code} {r.text[:200]}")
def maybe_generate_daily(log=print, batch=4, seconds=60):
    """At most one ACE-Step call per ~24h (free ZeroGPU quota). Adds `batch` tracks to the library."""
    if not os.environ.get("HF_TOKEN") or not os.environ.get("GH_PAT"): return
    try:
        ensure_branch(log)
        txt, _ = _get_text("music/_state.json"); st = json.loads(txt) if txt else {}
        if time.time() < st.get("next_try", 0):
            log(f"ACE: next try in {int((st['next_try'] - time.time()) / 60)} min, library={len(lib_list())}"); return
        style = st.get("style", 0)
        c = _client(log); info = c.view_api(return_format="dict", print_info=False)
        params = info["named_endpoints"]["/generation_wrapper"]["parameters"]
        over = {"generation_mode": "custom", "param_4": STYLES[style % len(STYLES)] + ", instrumental, no vocals, emotional, cinematic build-up",
                "param_5": "[Instrumental]", "param_6": 116, "param_15": seconds, "param_16": batch, "param_30": "mp3"}
        args = [over.get(p.get("parameter_name"), p.get("parameter_default")) for p in params]
        log(f"ACE: generating {batch} x {seconds}s, style {style}")
        job = c.submit(*args, api_name="/generation_wrapper"); t0 = time.time()
        while not job.done():
            if time.time() - t0 > 600: job.cancel(); raise TimeoutError("ACE timeout")
            time.sleep(10)
        res = job.result(); n = 0
        for i in range(min(batch, 8)):
            p = _path(res[i]) if isinstance(res, (list, tuple)) and len(res) > i else None
            if p and os.path.exists(str(p)):
                name = f"music/ace_{time.strftime('%Y%m%d_%H%M')}_{style}_{i}.mp3"
                _put(name, open(p, "rb").read(), f"add {name}"); n += 1
        st.update(next_try=time.time() + 24.5 * 3600, style=style + 1, last_added=n)
        log(f"ACE: added {n} tracks, library={len(lib_list())}")
    except Exception as e:
        msg = str(e); wait = 6 * 3600
        m = re.search(r"Try again in (\d+):(\d+):(\d+)", msg)
        if m: wait = int(m.group(1)) * 3600 + int(m.group(2)) * 60 + int(m.group(3)) + 300
        st = locals().get("st") or {}; st["next_try"] = time.time() + wait
        log("ACE daily failed:", type(e).__name__, msg[:200], f"| retry in {wait // 60} min")
    try: _put("music/_state.json", json.dumps(st).encode(), "state")
    except Exception as e: log("state save failed:", str(e)[:150])
def pick_track(day, workdir, log=print):
    try:
        files = lib_list()
        if not files: log("music: library empty, using built-in track"); return None
        f = random.Random(day * 31 + 7).choice(files); os.makedirs(workdir, exist_ok=True)
        dst = f"{workdir}/track.mp3"
        with requests.get(f["download_url"], timeout=60) as r:
            r.raise_for_status(); open(dst, "wb").write(r.content)
        log("music:", f["name"], f"({len(files)} in library)"); return dst
    except Exception as e:
        log("music pick failed:", str(e)[:150]); return None
def selftest(log=print):
    """No GPU use: checks GitHub write access to the library branch."""
    ok = ensure_branch(log)
    _put("music/_selftest.txt", f"ok {time.time()}".encode(), "selftest")
    log("library selftest:", ok, "files:", len(lib_list()))
