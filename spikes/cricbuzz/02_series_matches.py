"""Probe 02: IPL 2026 (series 9241) match list from HTML page; also try JSON-ish endpoints."""
import re, time, json, requests
UA = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36'
S = requests.Session(); S.headers.update({'User-Agent': UA, 'Accept-Language': 'en-US,en;q=0.9'})
urls = {
 '02_series_matches.html': 'https://www.cricbuzz.com/cricket-series/9241/indian-premier-league-2026/matches',
 '02_series_squads.html': 'https://www.cricbuzz.com/cricket-series/9241/indian-premier-league-2026/squads',
 '02_api_series.json': 'https://www.cricbuzz.com/api/cricket-series/9241/matches',
 '02_api_series2.json': 'https://www.cricbuzz.com/api/series/9241',
}
for fn, url in urls.items():
    r = S.get(url, timeout=30); time.sleep(1.2)
    print(url, r.status_code, len(r.content), r.headers.get('content-type'))
    open('samples/' + fn, 'w').write(r.text)
