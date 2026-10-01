"""Probe 03: hit The Hindu livescore API family directly with plain requests (no browser) and save
payloads. Endpoint family (from sportstar cricket-matchhub.min.js / manhattanChart.min.js):
  grouped/fixtures/<comp_id|widget>   scorecard/<comp-slug>/<game_id>/<teams-slug>
  current/<...same>   commentary/<...same>   current-scorecard/<...same>
  matchstats/<game_id>/<inn>   runrate/<game_id>/<inn>   wagonwheel/<game_id>/<inn>
usage: python 03_hindu_endpoints.py <comp-slug>/<game_id>/<teams-slug> [...]"""
import json, pathlib, sys, time
import requests

API = "https://livescoreapi.thehindu.com/api/cricket/"
OUT = pathlib.Path(__file__).parent / "samples" / "hindu"
OUT.mkdir(parents=True, exist_ok=True)
H = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) Chrome/128.0 Safari/537.36",
     "Referer": "https://sportstar.thehindu.com/", "Origin": "https://sportstar.thehindu.com"}


def get(path):
    t = time.time()
    r = requests.get(API + path, headers=H, timeout=20)
    dt = time.time() - t
    tag = path.replace("/", "_")
    (OUT / f"{tag}.json").write_bytes(r.content)
    print(f"{r.status_code} {len(r.content):>8}B {dt:4.2f}s cache={r.headers.get('cache-control')} "
          f"age={r.headers.get('age')} lm={r.headers.get('last-modified')} {path}")
    time.sleep(1.1)
    return r


for slug in sys.argv[1:]:
    gid = slug.split("/")[1]
    for ep in ("scorecard", "current", "commentary", "current-scorecard"):
        get(f"{ep}/{slug}")
    for ep in ("matchstats", "runrate", "wagonwheel"):
        get(f"{ep}/{gid}/1")
