"""Probe 02: curl_cffi with browser TLS impersonation."""
import sys, time, pathlib
from curl_cffi import requests as cr

S = pathlib.Path(__file__).parent / "samples"
URLS = [
    ("html_home", "https://www.espncricinfo.com/"),
    ("html_ipl2026", "https://www.espncricinfo.com/series/ipl-2026"),
    ("api_series_home", "https://hs-consumer-api.espncricinfo.com/v1/pages/series/home?lang=en&seriesId=1449924"),
]
for imp in sys.argv[1:] or ["chrome"]:
    s = cr.Session(impersonate=imp)
    for name, u in URLS:
        t = time.time()
        try:
            r = s.get(u, timeout=25)
            print(f"[{imp}] {name}: {r.status_code} {len(r.content)}B {time.time()-t:.2f}s final={r.url} server={r.headers.get('server')}")
            (S / f"02_{imp}_{name}.txt").write_bytes(r.content)
        except Exception as e:
            print(imp, name, "ERR", e)
        time.sleep(1.5)
