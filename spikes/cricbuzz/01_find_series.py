"""Probe 01: find IPL 2026 series id via Cricbuzz archive pages (plain requests)."""
import re, time, requests
UA = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36'
S = requests.Session(); S.headers.update({'User-Agent': UA, 'Accept-Language': 'en-US,en;q=0.9'})
for url, fn in [('https://www.cricbuzz.com/cricket-scorecard-archives/2026', '01_archive_2026.html'),
                ('https://www.cricbuzz.com/cricket-series/archive', '01_series_archive.html')]:
    r = S.get(url, timeout=30); time.sleep(1.2)
    print(url, r.status_code, len(r.content), r.headers.get('content-type'))
    open('samples/' + fn, 'w').write(r.text)
    print(sorted(set(re.findall(r'cricket-series/(\d+)/([a-z0-9-]*premier-league[a-z0-9-]*)', r.text))))
