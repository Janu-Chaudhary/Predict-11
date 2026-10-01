"""Probe 03: hit /api/mcenter/* JSON route handlers for the IPL 2026 final (155409)
with plain `requests` first, then curl_cffi (chrome impersonation) for comparison."""
import time, json, sys, requests
from curl_cffi import requests as creq
MID = sys.argv[1] if len(sys.argv) > 1 else '155409'
UA = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36'
H = {'User-Agent': UA, 'Accept': 'application/json, text/plain, */*', 'Accept-Language': 'en-US,en;q=0.9',
     'Referer': 'https://www.cricbuzz.com/'}
paths = [f'/api/mcenter/scorecard/{MID}', f'/api/mcenter/{MID}/miniscore', f'/api/mcenter/comm/{MID}',
         f'/api/mcenter/{MID}/full-commentary/1', f'/api/mcenter/{MID}/full-commentary/2',
         f'/api/mcenter/{MID}/full-commentary/3', f'/api/mcenter/{MID}/full-commentary/4',
         f'/api/mcenter/over-by-over/{MID}/1', f'/api/mcenter/balls-map/{MID}/1']
s = requests.Session(); s.headers.update(H)
for p in paths:
    t = time.time(); r = s.get('https://www.cricbuzz.com' + p, timeout=40)
    ct = r.headers.get('content-type', '')
    print(f'[requests] {r.status_code} {len(r.content):>8}B {time.time()-t:4.1f}s {ct[:30]:30} {p}')
    if r.status_code == 200 and 'json' in ct:
        fn = 'samples/03_%s_%s.json' % (MID, p.replace(f'/api/mcenter/', '').replace(MID, '').strip('/').replace('/', '_'))
        open(fn, 'w').write(r.text)
    time.sleep(1.1)
c = creq.Session(impersonate='chrome')
for p in paths[:2]:
    r = c.get('https://www.cricbuzz.com' + p, headers={'accept': 'application/json'}, timeout=40)
    print(f'[curl_cffi] {r.status_code} {len(r.content):>8}B {p}'); time.sleep(1.1)
