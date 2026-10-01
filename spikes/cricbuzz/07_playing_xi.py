"""Probe 07: parse playing XI / substitutes / bench from /cricket-match-squads/{mid}/match RSC payload."""
import json, re, sys
MID = sys.argv[1] if len(sys.argv) > 1 else '155409'
s = open(f'samples/06_{MID}_match_squads_rsc.txt').read()
dec = json.JSONDecoder()
for m in re.finditer(r'"players":\{"playing XI"', s):
    obj = dec.raw_decode(s[m.start() + len('"players":'):])[0]
    for grp, pl in obj.items():
        print(grp, len(pl))
        for p in pl:
            print('   ', p['id'], p['name'], '| full:', p['fullName'], '|', p['role'], 'C' if p['captain'] else '', 'WK' if p['keeper'] else '',
                  '| XIchg:', p.get('playingXIChange'), '| inMatch:', p.get('inMatchChange'), '| overseas' if p.get('isOverseas') else '')
