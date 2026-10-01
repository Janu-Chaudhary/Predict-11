"""Probe 06: curl_cffi against the NEW API host hs-consumer-api.cricinfo.com (found via Playwright), with/without x-hsci-auth-token."""
import sys, time, pathlib
from curl_cffi import requests as cr

S = pathlib.Path(__file__).parent / "samples"
U = "https://hs-consumer-api.cricinfo.com/v1/pages/match/comments?lang=en&seriesId=1510719&matchId=1535465&inningNumber=1&commentType=ALL&sortDirection=DESC&fromInningOver=10"
tok = sys.argv[1] if len(sys.argv) > 1 else None
s = cr.Session(impersonate="chrome")
for label, h in [("no-token", {}), ("referer-only", {"Referer": "https://www.cricinfo.com/"}),
                 ("token", {"Referer": "https://www.cricinfo.com/", "x-hsci-auth-token": tok} if tok else None)]:
    if h is None: continue
    t = time.time(); r = s.get(U, headers=h, timeout=30)
    print(label, r.status_code, len(r.content), f"{time.time()-t:.2f}s", r.text[:150].replace("\n", " "))
    (S / f"06_{label}.txt").write_bytes(r.content)
    time.sleep(1.2)
