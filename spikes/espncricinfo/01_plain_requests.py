"""Probe 01: plain `requests` against ESPNcricinfo HTML + hs-consumer-api."""
import time, requests, pathlib

S = pathlib.Path(__file__).parent / "samples"
UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
      "Chrome/128.0.0.0 Safari/537.36")
H = {"User-Agent": UA, "Accept": "text/html,application/json;q=0.9,*/*;q=0.8",
     "Accept-Language": "en-US,en;q=0.9"}

URLS = [
    ("html_home", "https://www.espncricinfo.com/"),
    ("html_ipl_series_search", "https://www.espncricinfo.com/series/ipl-2026"),
    ("api_series_search", "https://hs-consumer-api.espncricinfo.com/v1/pages/series/home?lang=en&seriesId=1449924"),
    ("api_match_ipl25final", "https://hs-consumer-api.espncricinfo.com/v1/pages/match/home?lang=en&seriesId=1449924&matchId=1473511"),
]
for name, u in URLS:
    t = time.time()
    try:
        r = requests.get(u, headers=H, timeout=20, allow_redirects=True)
        dt = time.time() - t
        print(f"{name}: {r.status_code} {len(r.content)}B {dt:.2f}s final={r.url} server={r.headers.get('server')}")
        (S / f"01_{name}.txt").write_bytes(r.content[:200000])
    except Exception as e:
        print(name, "ERR", e)
    time.sleep(1.5)
