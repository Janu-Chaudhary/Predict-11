"""Probe 05: stats.bcci.tv live endpoints. Lists every live BCCI-covered match (any comp), then pulls
the scorecard (+ optional Ellipse ball-by-ball) for each in-progress one and prints live fields.
usage: python 05_bcci_live.py [comp_gid]"""
import json, pathlib, sys, time
from curl_cffi import requests

OUT = pathlib.Path(__file__).parent / "samples" / "bcci"
OUT.mkdir(parents=True, exist_ok=True)
H = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0 Safari/537.36",
     "Origin": "https://www.iplt20.com", "Referer": "https://www.iplt20.com/", "Accept": "application/json"}


def get(url, tag):
    t = time.time()
    r = requests.get(url, headers=H, impersonate="chrome", timeout=30)
    print(f"{r.status_code} {len(r.content):>8}B {time.time()-t:4.2f}s cache={r.headers.get('cache-control')} "
          f"age={r.headers.get('age')} x-cache={r.headers.get('x-cache')} {url}")
    (OUT / f"{tag}.json").write_bytes(r.content)
    time.sleep(1.1)
    return r.json() if r.status_code == 200 else None


q = f"?comp_gid={sys.argv[1]}" if len(sys.argv) > 1 else ""
ls = get(f"https://stats.bcci.tv/match/live_scores/{q}", "live_scores" + ("_" + sys.argv[1] if q else ""))
for m in (ls or {}).get("live_scores", []):
    print(f"  {m['gid']} {m['comp_name']!r} comp_gid?={m.get('comp_gid')} status={m['match_status']}/"
          f"{m['live_status_name']} | {m['name']} | {m['result_string']}")
live = [m for m in (ls or {}).get("live_scores", []) if m["match_status"] == "live"]
for m in live[:2]:
    sc = get(f"https://stats.bcci.tv/match/{m['gid']}/scorecard", f"scorecard_{m['gid']}")
    if not sc:
        continue
    print("  top-level keys:", sorted(sc))
    for k in ("match", "toss", "live", "officials"):
        if k in sc:
            print(f"  {k}:", json.dumps(sc[k])[:700])
    for inn in sc.get("innings", []):
        cur_bat = [(b["player_id"], b["runs"], b["balls_faced"], b["live_status"]) for b in inn["batting"] if b.get("live_status")]
        cur_bowl = [(b["player_id"], b["overs"], b["live_status"]) for b in inn["bowling"] if b.get("live_status")]
        print(f"  inn {inn['innings_number']} live_status={inn['live_status']} {inn.get('runs')}/{inn.get('wickets')} "
              f"({inn['overs']}) reviews={json.dumps(inn.get('reviews'))} bat_live={cur_bat} bowl_live={cur_bowl}")
