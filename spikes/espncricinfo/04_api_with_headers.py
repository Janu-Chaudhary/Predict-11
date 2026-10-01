"""Probe 04: hs-consumer-api via curl_cffi with browser-like Origin/Referer, after warming cookies on www."""
import time, pathlib
from curl_cffi import requests as cr

S = pathlib.Path(__file__).parent / "samples"
REF = "https://www.espncricinfo.com/series/ipl-2026-1510719/royal-challengers-bengaluru-vs-gujarat-titans-final-1535465/ball-by-ball-commentary"
APIS = [
    "https://hs-consumer-api.espncricinfo.com/v1/pages/match/comments?lang=en&seriesId=1510719&matchId=1535465&inningNumber=1&commentType=ALL&sortDirection=DESC&fromInningOver=10",
    "https://hs-consumer-api.espncricinfo.com/v1/pages/match/scorecard?lang=en&seriesId=1510719&matchId=1535465",
]
for imp in ["chrome", "chrome131", "safari"]:
    s = cr.Session(impersonate=imp)
    r = s.get(REF, timeout=30); print(imp, "warm", r.status_code, "cookies", list(s.cookies.keys()))
    time.sleep(1.5)
    for origin in ["https://www.espncricinfo.com", "https://www.cricinfo.com"]:
        for u in APIS:
            r = s.get(u, headers={"Origin": origin, "Referer": origin + "/", "Accept": "application/json, text/plain, */*",
                                  "Sec-Fetch-Site": "same-site", "Sec-Fetch-Mode": "cors", "Sec-Fetch-Dest": "empty"}, timeout=30)
            print(f"  [{imp} origin={origin}] {r.status_code} {len(r.content)}B {u.split('/v1/')[1][:40]}")
            if r.status_code == 200:
                (S / f"04_{imp}_{u.split('/')[-1].split('?')[0]}.json").write_bytes(r.content)
            time.sleep(1.2)
