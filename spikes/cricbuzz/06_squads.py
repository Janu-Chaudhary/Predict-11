"""Probe 06: playing XIs (match squads page RSC) and series squads (JSON route)."""
import json, re, time, sys, requests
MID = sys.argv[1] if len(sys.argv) > 1 else '155409'
S = requests.Session(); S.headers.update({'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36', 'Accept-Language': 'en-US,en;q=0.9', 'Referer': 'https://www.cricbuzz.com/'})
def g(p):
    r = S.get('https://www.cricbuzz.com' + p, timeout=45); time.sleep(1.1)
    print(p, r.status_code, len(r.content), r.headers.get('content-type')); return r
def rsc(html):
    return ''.join(json.loads('"' + c + '"') for c in re.findall(r'self\.__next_f\.push\(\[1,"(.*?)"\]\)</script>', html, re.S))
def find_obj(s, key):
    i = s.find('"%s":' % key)
    if i < 0: return None
    j = s.index('{', i) if s[i+len(key)+3] == '{' else s.index('[', i)
    dec = json.JSONDecoder(); return dec.raw_decode(s[j:])[0]
r = g(f'/cricket-match-squads/{MID}/match'); open(f'samples/06_{MID}_match_squads.html', 'w').write(r.text)
s = rsc(r.text); open(f'samples/06_{MID}_match_squads_rsc.txt', 'w').write(s)
for k in ('team1', 'team2'):
    t = find_obj(s, k)
    if not t: print('no', k); continue
    print(k, t.get('team', {}).get('teamName') if isinstance(t.get('team'), dict) else list(t.keys()))
    for grp in t.get('players', {}) if isinstance(t.get('players'), dict) else []:
        pl = t['players'][grp]
        print('  ', grp, len(pl), [(p.get('id'), p.get('name'), p.get('fullName'), p.get('role'), p.get('captain'), p.get('keeper')) for p in pl][:13])
# series squads
r = g('/cricket-series/9241/indian-premier-league-2026/squads'); s2 = rsc(r.text)
open('samples/06_series_squads_rsc.txt', 'w').write(s2)
sq = sorted(set(re.findall(r'"squadId":(\d+),"squadType":"([^"]*)"(?:,"teamId":(\d+))?', s2)))
print('squads', sq[:12])
if sq:
    r = g(f'/api/cricket-series/series-squads/9241/{sq[0][0]}'); open(f'samples/06_series_squad_{sq[0][0]}.json', 'w').write(r.text)
    j = r.json(); print(list(j.keys())); print(json.dumps(j)[:800])
