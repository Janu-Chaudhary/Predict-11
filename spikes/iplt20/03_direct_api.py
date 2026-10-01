"""Probe 03: call discovered data endpoints directly (no browser) to check auth/blocking/speed.
usage: python 03_direct_api.py <tag> <url> [<tag> <url> ...]"""
import sys, time, json, pathlib, os
from curl_cffi import requests
S = pathlib.Path(__file__).parent / "samples" / "03"; S.mkdir(parents=True, exist_ok=True)
H = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0 Safari/537.36",
     "Origin": "https://www.iplt20.com", "Referer": "https://www.iplt20.com/"}
if os.environ.get("EDAK"): H["Edak"] = os.environ["EDAK"]  # public CricViz widget key seen in browser
a = sys.argv[1:]
for tag, u in zip(a[::2], a[1::2]):
    t = time.time()
    try:
        r = requests.get(u, headers=H, impersonate="chrome", timeout=30, allow_redirects=True)
        ext = "json" if "json" in r.headers.get("content-type", "") else "txt"
        (S / f"{tag}.{ext}").write_bytes(r.content)
        hist = " via " + " -> ".join(h for h in [getattr(x, 'url', '') for x in (r.history or [])]) if getattr(r, "history", None) else ""
        print(f"{r.status_code} {len(r.content):>8}B {time.time()-t:.2f}s {tag} {u} -> {r.url}{hist} ct={r.headers.get('content-type')}")
    except Exception as e:
        print("ERR", tag, u, e)
    time.sleep(1.1)
