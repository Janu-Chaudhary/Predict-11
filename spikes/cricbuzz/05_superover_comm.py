"""Probe 05: where does super-over data live? /api/mcenter/comm/{mid} (latest page) + commentary-pagination."""
import json, time, requests, collections
MID = '151924'
S = requests.Session(); S.headers.update({'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36', 'Referer': 'https://www.cricbuzz.com/'})
def g(p):
    r = S.get('https://www.cricbuzz.com' + p, timeout=40); time.sleep(1.1)
    print(p, r.status_code, len(r.content), r.headers.get('content-type')); return r
r = g(f'/api/mcenter/comm/{MID}'); open(f'samples/05_{MID}_comm.json', 'w').write(r.text); j = r.json()
print(j.keys())
mc = j.get('matchCommentary') or {}
print(type(mc), len(mc))
vals = list(mc.values()) if isinstance(mc, dict) else mc
print(collections.Counter(v.get('inningsId') for v in vals))
for v in sorted(vals, key=lambda v: v.get('timestamp', 0))[-12:]:
    print(v.get('inningsId'), v.get('overNumber'), v.get('ballNbr'), (v.get('commText') or '')[:110])
ms = j.get('miniscore', {}); print('miniscore keys', list(ms.keys())[:40])
print(json.dumps(ms.get('matchScoreDetails', {}))[:1500])
r = g(f'/api/mcenter/hscorecard/{MID}'); open(f'samples/05_{MID}_hscorecard.json', 'w').write(r.text)
print([ (i['inningsId'], i['batTeamDetails']['batTeamShortName'], i['scoreDetails']['runs']) for i in r.json()['scoreCard']])
