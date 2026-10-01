"""Probe 06: poll the three live sources side by side and log what changed + how stale each is.
Re-run during a real live match to measure cadence (each source <= 1 req per poll; requests spaced 1.1 s).

usage: python 06_poll_freshness.py --bcci <match_uuid> --cb <cricbuzz_mid> --hindu <game_id> [--n 5] [--every 60]
Writes samples/poll/<ts>_<src>.json and one CSV line per poll to samples/poll/log.tsv."""
import argparse, hashlib, json, pathlib, time
from datetime import datetime, timezone
import requests

OUT = pathlib.Path(__file__).parent / "samples" / "poll"
OUT.mkdir(parents=True, exist_ok=True)
UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0 Safari/537.36"
S = requests.Session(); S.headers.update({"User-Agent": UA, "Accept": "application/json"})


def fetch(url, ref):
    t = time.time()
    r = S.get(url, headers={"Referer": ref}, timeout=20)
    time.sleep(1.1)
    return r, time.time() - t


def bcci(uuid):
    r, dt = fetch(f"https://stats.bcci.tv/match/{uuid}/bbb?size=12", "https://www.iplt20.com/")
    b = r.json()["ball"]
    last = b[0] if b else {}
    return r, dt, f"inn{last.get('innings_number')} {last.get('over_number')}.{last.get('ball_number')}", last.get("ball_timestamp")


def cb(mid):
    r, dt = fetch(f"https://www.cricbuzz.com/api/mcenter/{mid}/miniscore", "https://www.cricbuzz.com/")
    j = r.json()
    ms = j.get("miniscore", j)
    return r, dt, f"{ms.get('overs')} {ms.get('recentOvsStats')}", ms.get("responseLastUpdated")


def hindu(gid):
    r, dt = fetch(f"https://livescoreapi.thehindu.com/api/cricket/current/x/{gid}/x", "https://sportstar.thehindu.com/")
    j = r.json()
    t = j.get("totalscore", {}).get("totals", {})
    return r, dt, f"{t.get('runs_scored')}/{t.get('wickets')} ({t.get('overs')})", j.get("last_update")


ap = argparse.ArgumentParser()
ap.add_argument("--bcci"); ap.add_argument("--cb"); ap.add_argument("--hindu")
ap.add_argument("--n", type=int, default=3); ap.add_argument("--every", type=int, default=60)
a = ap.parse_args()
prev = {}
log = open(OUT / "log.tsv", "a")
for i in range(a.n):
    now = datetime.now(timezone.utc).strftime("%H:%M:%S")
    for name, fn, arg in (("bcci", bcci, a.bcci), ("cricbuzz", cb, a.cb), ("hindu", hindu, a.hindu)):
        if not arg:
            continue
        try:
            r, dt, where, upd = fn(arg)
            h = hashlib.md5(r.content).hexdigest()[:8]
            changed = prev.get(name) not in (None, h)
            prev[name] = h
            (OUT / f"{now.replace(':', '')}_{name}.json").write_bytes(r.content)
            line = (f"{now}\t{name}\t{r.status_code}\t{len(r.content)}B\t{dt:.2f}s\tcc={r.headers.get('cache-control')}"
                    f"\tetag={r.headers.get('etag')}\tchanged={changed}\t{where}\tsrc_updated={upd}")
        except Exception as e:
            line = f"{now}\t{name}\tERR {e}"
        print(line); log.write(line + "\n"); log.flush()
    if i < a.n - 1:
        time.sleep(a.every)
