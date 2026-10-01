"""Probe 10: ESPN's *open* site API (site.web.api.espn.com) — found via the `cricdata` library.
Not behind cricinfo's Akamai token. Test plain requests: playbyplay pagination + summary, for a match id.

usage: 10_espn_site_api.py <matchId> [leagueId=8676]
"""
import json, sys, time, pathlib, requests

S = pathlib.Path(__file__).parent / "samples"
MID = sys.argv[1] if len(sys.argv) > 1 else "1535465"
LG = sys.argv[2] if len(sys.argv) > 2 else "8676"
H = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/153.0.0.0 Safari/537.36"}
RETRIES = {"n": 0}
def get(url, **kw):
    for attempt in range(5):
        r = requests.get(url, headers=H, timeout=30, **kw)
        if r.status_code < 500: return r
        RETRIES["n"] += 1; print(f"   {r.status_code} {r.text[:40]} retry {attempt+1}"); time.sleep(2 * (attempt + 1))
    return r
t0 = time.time()
items, page, sizes = [], 1, []
while True:
    r = get(f"https://site.web.api.espn.com/apis/site/v2/sports/cricket/{LG}/playbyplay",
            params={"event": MID, "page": page})
    sizes.append(len(r.content))
    if r.status_code != 200:
        print("playbyplay", page, r.status_code, r.text[:200]); break
    d = r.json(); c = d.get("commentary", {})
    if page == 1:
        (S / f"10_{MID}_pbp_p1.json").write_text(json.dumps(d))
        print("page1 keys", list(d.keys()), "commentary keys", list(c.keys()), "pageCount", c.get("pageCount"), "count", c.get("count"))
    items += c.get("items", [])
    if not c.get("items") or page >= c.get("pageCount", 1): break
    page += 1; time.sleep(1.0)
(S / f"10_{MID}_pbp_all.json").write_text(json.dumps(items))
print(f"retries={RETRIES['n']} playbyplay: {page} pages, {len(items)} items, {sum(sizes)}B, {time.time()-t0:.1f}s")
time.sleep(1)
r = get(f"https://site.web.api.espn.com/apis/site/v2/sports/cricket/{LG}/summary", params={"event": MID})
print("summary", r.status_code, len(r.content))
if r.ok:
    (S / f"10_{MID}_summary.json").write_text(r.text)
    print("summary keys", list(r.json().keys()))
