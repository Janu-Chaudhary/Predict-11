"""Probe 06: pull all 10 IPL squads without a browser.
 - iplt20 BFF:  https://www.iplt20.com/api/bff/cms/teams/<slug>?tab=squad   (role, country, isInternational=overseas, captain/WK, image, externalId)
 - Ellipse:     https://epr.ellipsedata.com/redirect/1/comp/8903/squads?team_id=<externalTeamId>  (Cricsheet-style short names, needs Edak header)
Joins on player externalId == stats.bcci.tv player_id. Writes samples/06/squads_2026.csv and compares to data/raw/Teams/*.csv."""
import json, time, csv, pathlib, sys
from curl_cffi import requests
ROOT = pathlib.Path(__file__).parent; OUT = ROOT / "samples" / "06"; OUT.mkdir(parents=True, exist_ok=True)
UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0 Safari/537.36"
EDAK = "dREj-f+6etraCroX6"   # public widget key observed in browser request headers (probe 04)
SLUGS = ["chennai-super-kings","delhi-capitals","gujarat-titans","kolkata-knight-riders","lucknow-super-giants",
         "mumbai-indians","punjab-kings","rajasthan-royals","royal-challengers-bengaluru","sunrisers-hyderabad"]
season = sys.argv[1] if len(sys.argv) > 1 else None
def get(u, **h):
    t = time.time(); r = requests.get(u, impersonate="chrome", headers={"User-Agent": UA, **h}, timeout=30); time.sleep(1.1)
    print(f"  {r.status_code} {len(r.content)}B {time.time()-t:.2f}s {u}"); return r
rows = []
for slug in SLUGS:
    u = f"https://www.iplt20.com/api/bff/cms/teams/{slug}?tab=squad" + (f"&season={season}" if season else "")
    d = get(u).json(); (OUT / f"bff_{slug}{'_'+season if season else ''}.json").write_text(json.dumps(d))
    team_ext = d["data"]["externalId"]; players = d["data"]["squad"]["players"]
    short = {}
    if not season:
        e = get(f"https://epr.ellipsedata.com/redirect/1/comp/8903/squads?team_id={team_ext}", Edak=EDAK, Origin="https://www.iplt20.com", Referer="https://www.iplt20.com/")
        ej = e.json(); (OUT / f"epr_{slug}.json").write_text(json.dumps(ej))
        for t in ej.get("teams", []):
            for p in t["players"]: short[p["player_id"]] = p
    for p in players:
        s = short.get(p["externalId"], {})
        rows.append({"team": slug, "team_ext_id": team_ext, "player_id": p["externalId"], "name": p["name"], "short_name": s.get("player_name", ""),
                     "role": p["role"], "epr_role": s.get("player_role", ""), "overseas": p["isInternational"], "country": p["country"],
                     "captain": p["isCaptain"], "wk": p["isWicketKeeper"], "image": p["imageUrl"]})
    print(slug, team_ext, len(players), "players;", sum(r["overseas"] for r in rows if r["team"] == slug), "overseas;", len(short), "in epr squad")
fn = OUT / f"squads_{season or '2026'}.csv"
with open(fn, "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
print("wrote", fn, len(rows))
