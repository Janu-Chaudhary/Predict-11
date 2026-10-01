"""Probe 01: robots.txt, sitemaps, key HTML pages with plain HTTP (curl_cffi chrome impersonation)."""
import time, sys, pathlib
from curl_cffi import requests
S = pathlib.Path(__file__).parent / "samples"
UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0 Safari/537.36"
urls = sys.argv[1:] or [
    "https://www.iplt20.com/robots.txt",
    "https://www.iplt20.com/sitemap.xml",
    "https://www.iplt20.com/",
    "https://www.iplt20.com/matches/results",
    "https://www.iplt20.com/matches/fixtures",
    "https://www.iplt20.com/teams/mumbai-indians/squad",
    "https://www.bcci.tv/robots.txt",
]
for u in urls:
    t = time.time()
    try:
        r = requests.get(u, impersonate="chrome", headers={"User-Agent": UA}, timeout=30, allow_redirects=True)
        name = u.split("://")[1].replace("/", "_").replace("?", "_")[:120]
        (S / f"01_{name}").write_bytes(r.content)
        print(f"{r.status_code} {len(r.content):>8}B {time.time()-t:.2f}s {u} -> {r.url} ct={r.headers.get('content-type')}")
    except Exception as e:
        print("ERR", u, e)
    time.sleep(1.1)
