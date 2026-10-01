"""Probe 03: curl_cffi fetch of match HTML pages, extract embedded __NEXT_DATA__ JSON."""
import json, re, sys, time, pathlib
from curl_cffi import requests as cr

S = pathlib.Path(__file__).parent / "samples"
BASE = "https://www.espncricinfo.com/series/ipl-2026-1510719"
MATCH = sys.argv[1] if len(sys.argv) > 1 else "royal-challengers-bengaluru-vs-gujarat-titans-final-1535465"
PAGES = sys.argv[2].split(",") if len(sys.argv) > 2 else [
    "full-scorecard", "ball-by-ball-commentary", "match-playing-xi", "match-squads", "live-cricket-score"]

s = cr.Session(impersonate="chrome")
mid = MATCH.rsplit("-", 1)[1]
for p in PAGES:
    u = f"{BASE}/{MATCH}/{p}" if p != "_series" else f"{BASE}/match-schedule-fixtures-and-results"
    t = time.time()
    r = s.get(u, timeout=30)
    dt = time.time() - t
    m = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', r.text, re.S)
    nd = json.loads(m.group(1)) if m else None
    tag = f"{mid}_{p}"
    print(f"{p}: {r.status_code} html={len(r.content)}B {dt:.2f}s final={r.url} next_data={'yes %dB' % len(m.group(1)) if m else 'NO'}")
    if nd:
        (S / f"03_{tag}.next.json").write_text(json.dumps(nd))
        pp = nd.get("props", {}).get("appPageProps", {}) or nd.get("props", {}).get("pageProps", {})
        def walk(o, path="", depth=0):
            if depth > 3 or not isinstance(o, dict): return
            for k, v in o.items():
                sz = len(json.dumps(v))
                print(f"   {path}.{k}: {type(v).__name__} {sz}B")
                if sz > 2000: walk(v, f"{path}.{k}", depth + 1)
        walk(nd.get("props", {}), "props")
    else:
        (S / f"03_{tag}.html").write_bytes(r.content)
    time.sleep(1.5)
