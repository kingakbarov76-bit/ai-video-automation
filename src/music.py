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
def test(log=print):
    os.makedirs("out", exist_ok=True)
    try: ccmixter(10, log)
    except Exception as e: log("ccmixter failed:", str(e)[:200])
    try: inspect(log)
    except Exception as e: log("ACE inspect failed:", type(e).__name__, str(e)[:300])
