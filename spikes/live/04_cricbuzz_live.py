"""Probe 04: Cricbuzz live endpoints for one or more match ids (plain requests, <=1 req/s).
Saves payloads to samples/cricbuzz/ and prints the live-relevant fields of the miniscore.
usage: python 04_cricbuzz_live.py <mid> [<mid> ...]"""
import json, pathlib, sys, time
import requests

OUT = pathlib.Path(__file__).parent / "samples" / "cricbuzz"
OUT.mkdir(parents=True, exist_ok=True)
H = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0 Safari/537.36",
     "Accept": "application/json, text/plain, */*", "Referer": "https://www.cricbuzz.com/"}
S = requests.Session(); S.headers.update(H)


def get(mid, path):
    t = time.time()
    r = S.get("https://www.cricbuzz.com" + path, timeout=30)
    print(f"{r.status_code} {len(r.content):>8}B {time.time()-t:4.2f}s cache={r.headers.get('cache-control')} {path}")
    time.sleep(1.1)
    if r.status_code == 200 and "json" in r.headers.get("content-type", ""):
        (OUT / f"{mid}_{path.split('/')[-1] if path.endswith(mid) else path.split('/')[-1]}_{path.split('/')[3]}.json").write_text(r.text)
        return r.json()


for mid in sys.argv[1:]:
    comm = get(mid, f"/api/mcenter/comm/{mid}")
    get(mid, f"/api/mcenter/{mid}/miniscore")
    get(mid, f"/api/mcenter/scorecard/{mid}")
    if comm:
        ms = comm.get("miniscore") or {}
        hdr = comm.get("matchHeader") or {}
        print(" header keys:", sorted(hdr)[:40])
        print(" miniscore keys:", sorted(ms))
        print(" state/status:", hdr.get("state"), "|", hdr.get("status"), "| toss:", hdr.get("tossResults"))
        for k in ("batsmanStriker", "batsmanNonStriker", "bowlerStriker"):
            print(" ", k, json.dumps(ms.get(k))[:200])
        print("  recentOvsStats:", ms.get("recentOvsStats"), "crr:", ms.get("currentRunRate"), "rrr:", ms.get("requiredRunRate"))
        print("  udrs:", json.dumps(ms.get("udrs"))[:300])
        print("  comm lines:", len(comm.get("commentaryList") or []))
