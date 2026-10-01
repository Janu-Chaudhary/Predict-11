"""Probe 04: parse /api/mcenter/{mid}/full-commentary/{inn} into structured deliveries and
validate vs /api/mcenter/scorecard/{mid}. Usage: 04_parse_deliveries.py MID [fetch]"""
import json, re, sys, os, time, collections, requests
MID = sys.argv[1] if len(sys.argv) > 1 else '155409'
UA = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36'
S = requests.Session(); S.headers.update({'User-Agent': UA, 'Accept': 'application/json', 'Referer': 'https://www.cricbuzz.com/'})

def get(path, fn):
    fp = f'samples/{fn}'
    if not os.path.exists(fp):
        r = S.get('https://www.cricbuzz.com' + path, timeout=40); time.sleep(1.1)
        print('GET', path, r.status_code, len(r.content), r.headers.get('content-type'))
        open(fp, 'w').write(r.text if r.status_code == 200 else '{}')
    t = open(fp).read()
    return json.loads(t) if t.strip() else {}

sc = get(f'/api/mcenter/scorecard/{MID}', f'03_{MID}_scorecard.json')
EXTRA_RE = re.compile(r'^[^,]+ to [^,]+, (wide|wides|\d+ wides|no ball|byes?|leg byes?|\d+ (?:leg )?byes?)', re.I)
DISMISS_RE = re.compile(r'^(?P<bat>.+?) (?P<how>c and b |c & b |c (?P<c>.+?) b |st (?P<st>.+?) b |lbw b |b |run out \((?P<ro>[^)]*)\)|hit wicket b |retired|obstructing the field|obs )')

def kind_of(t):
    t = t.lower()
    if 'no ball' in t: return 'noballs'
    if 'leg bye' in t: return 'legbyes'
    if 'bye' in t: return 'byes'
    if 'wide' in t: return 'wides'
    return None

def parse(inn):
    d = get(f'/api/mcenter/{MID}/full-commentary/{inn}', f'03_{MID}_full-commentary_{inn}.json')
    items = [c for blk in d.get('commentary', []) for c in blk.get('commentaryList', []) if c.get('inningsId') == inn]
    balls = sorted([c for c in items if c.get('overNumber') is not None], key=lambda c: c['timestamp'])
    out, prev = [], 0
    for c in balls:
        txt = c['commText']
        for fmt in (c.get('commentaryFormats') or {}).values():   # placeholders like B0$ / I0$
            for fid, fv in zip(fmt.get('formatId', []), fmt.get('formatValue', [])):
                txt = txt.replace(fid, fv)
        head = txt.split(',', 2)[1].strip() if txt.count(',') >= 1 else ''
        ek = kind_of(head) if EXTRA_RE.match(txt) else None
        runs = c['batTeamScore'] - prev; prev = c['batTeamScore']
        wk = fielder = None
        if 'WICKET' in c['event']:
            fv = c.get('commentaryFormats', {}).get('bold', {}).get('formatValue', [])
            desc = next((v for v in fv if re.search(r' (c|b|lbw|st|run out|hit wicket|obstructing|obs)( |\()', v) and v != 'out'), '')
            m = DISMISS_RE.match(desc)
            if m:
                how = m.group('how').lower()
                wk = ('caught and bowled' if how.startswith(('c &','c and')) else 'caught' if how.startswith('c ') else
                      'stumped' if how.startswith('st') else 'lbw' if how.startswith('lbw') else
                      'run out' if how.startswith('run out') else 'obstructing the field' if how.startswith('obs') else 'hit wicket' if how.startswith('hit') else 'bowled')
                fielder = m.group('c') or m.group('st') or m.group('ro')
            else:
                wk = 'UNPARSED:' + desc
        out.append(dict(over=c['overNumber'], ballNbr=c['ballNbr'], batter=c['batsmanStriker']['batName'],
                        batter_id=c['batsmanStriker']['batId'], bowler=c['bowlerStriker']['bowlName'],
                        bowler_id=c['bowlerStriker']['bowlId'], runs_total=runs, extra=ek, wicket=wk, fielder=fielder,
                        score=c['batTeamScore'], text=txt[:90]))
    return items, out

for card in sc['scoreCard']:
    inn = card['inningsId']
    items, dels = parse(inn)
    tot = sum(x['runs_total'] for x in dels); wk = sum(1 for x in dels if x['wicket'])
    legal = sum(1 for x in dels if x['extra'] not in ('wides', 'noballs'))
    ex = collections.Counter(x['extra'] for x in dels if x['extra'])
    sd = card['scoreDetails']
    print(f"INN {inn} {card['batTeamDetails']['batTeamShortName']}: items={len(items)} deliveries={len(dels)} legal={legal} "
          f"parsed runs={tot} wkts={wk} | scorecard runs={sd['runs']} wkts={sd['wickets']} balls={sd['ballNbr']} extras={card['extrasData']}")
    print('   extra deliveries:', dict(ex), '| wickets:', [(x['over'], x['wicket'], x['fielder']) for x in dels if x['wicket']])
    # per-over check of sequence gaps
    nums = sorted({x['ballNbr'] for x in dels}); miss = sorted(set(range(1, sd['ballNbr'] + 1)) - set(nums))
    print('   missing ballNbr:', miss[:20])
    json.dump(dels, open(f'samples/04_{MID}_deliveries_inn{inn}.json', 'w'), indent=1)

# extras-by-type runs check vs scorecard extrasData
for card in sc['scoreCard']:
    _, dels = parse(card['inningsId'])
    by = collections.Counter()
    for x in dels:
        if x['extra']: by[x['extra']] += x['runs_total']
    e = card['extrasData']
    print(f"   extras runs inn{card['inningsId']}: parsed wides={by['wides']} nb-deliveries-runs={by['noballs']} lb={by['legbyes']} b={by['byes']} | card wides={e['wides']} nb={e['noBalls']} lb={e['legByes']} b={e['byes']}")
