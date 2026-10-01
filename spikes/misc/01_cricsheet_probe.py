"""Probe 01: Cricsheet IPL JSON zips — coverage, lag, schema."""
import json, zipfile, collections, datetime as dt
from pathlib import Path

S = Path(__file__).parent / "samples"


def load(zipname):
    out = {}
    with zipfile.ZipFile(S / zipname) as z:
        for n in z.namelist():
            if n.endswith(".json"):
                out[n] = json.loads(z.read(n))
    return out


ipl = load("ipl_json.zip")
print("ipl_json.zip matches:", len(ipl))
by_season = collections.Counter(str(m["info"].get("season")) for m in ipl.values())
print("by season (last 5):", sorted(by_season.items())[-5:])

rows = []
for n, m in ipl.items():
    i = m["info"]
    rows.append(dict(file=n, season=str(i["season"]), date=i["dates"][0],
                     created=m["meta"].get("created"), revision=m["meta"].get("revision"),
                     num=i.get("event", {}).get("match_number"), stage=i.get("event", {}).get("stage"),
                     teams=" v ".join(i["teams"]), venue=i.get("venue"),
                     result=i.get("outcome", {}).get("result") or ("win" if "winner" in i.get("outcome", {}) else "?"),
                     method=i.get("outcome", {}).get("method"),
                     eliminator=i.get("outcome", {}).get("eliminator")))
rows.sort(key=lambda r: r["date"])
print("newest:", rows[-1])
s26 = [r for r in rows if r["season"] == "2026"]
print("2026 matches:", len(s26), "date range", s26[0]["date"] if s26 else None, s26[-1]["date"] if s26 else None)
nums = sorted(r["num"] for r in s26 if r["num"])
print("match_numbers present:", len(nums), "max", max(nums) if nums else None)
print("missing league match numbers 1..70:", [k for k in range(1, 71) if k not in nums])
print("stages:", [(r["date"], r["stage"], r["teams"]) for r in s26 if r["stage"]])
print("no-result/tie/DLS:", [(r["date"], r["num"], r["result"], r["method"], r["eliminator"]) for r in s26 if r["result"] != "win" or r["method"] or r["eliminator"]])
lags = []
for r in s26:
    d = dt.date.fromisoformat(r["date"]); c = dt.date.fromisoformat(r["created"])
    lags.append((c - d).days)
if lags:
    lags.sort()
    print("lag days (created - match) min/median/p90/max:", lags[0], lags[len(lags)//2], lags[int(len(lags)*.9)], lags[-1])
    print("lag distribution:", collections.Counter(lags).most_common(10))
with open(S / "ipl2026_matches.tsv", "w") as f:
    f.write("\t".join(rows[0].keys()) + "\n")
    for r in s26:
        f.write("\t".join(str(v) for v in r.values()) + "\n")

for zn in ["recently_added_7_json.zip", "recently_added_30_json.zip"]:
    ra = load(zn)
    comps = collections.Counter(m["info"].get("event", {}).get("name", "?") for m in ra.values())
    created = sorted(m["meta"]["created"] for m in ra.values())
    print(f"{zn}: {len(ra)} matches, created {created[0]}..{created[-1]}, top events {comps.most_common(6)}")
    ipl_in = [m for m in ra.values() if "Indian Premier League" in m["info"].get("event", {}).get("name", "")]
    print("  IPL in it:", len(ipl_in))

# save one 2026 sample, prefer one with impact sub / DLS
pick = None
for n, m in ipl.items():
    if str(m["info"]["season"]) == "2026":
        has_rep = any("replacements" in o for inn in m["innings"] for ov in inn["overs"] for o in ov["deliveries"])
        if has_rep:
            pick = (n, m); break
n, m = pick
(S / f"sample_ipl2026_{n}").write_text(json.dumps(m, indent=1))
print("sample:", n, "top keys:", list(m), "meta:", m["meta"])
print("info keys:", list(m["info"]))
print("toss:", m["info"]["toss"])
print("players:", {k: len(v) for k, v in m["info"]["players"].items()})
print("registry people count:", len(m["info"]["registry"]["people"]))
inn = m["innings"][0]
print("innings keys:", list(inn))
d = inn["overs"][0]["deliveries"][0]
print("first delivery:", d)
for inn in m["innings"]:
    for ov in inn["overs"]:
        for dl in ov["deliveries"]:
            if "replacements" in dl:
                print("replacements example (over", ov["over"], "):", dl["replacements"])
            if "wickets" in dl and dl["wickets"][0].get("fielders"):
                wk = dl["wickets"]
    if "powerplays" in inn: print("powerplays:", inn["powerplays"])
print("wicket example:", wk)
ex = next(dl for inn in m["innings"] for ov in inn["overs"] for dl in ov["deliveries"] if "extras" in dl)
print("extras example:", ex)

# DLS / super over representations across whole IPL zip
so = [(n, x["info"]["dates"][0]) for n, x in ipl.items() if any(i.get("super_over") for i in x["innings"])]
print("super over matches:", len(so), so[-3:])
if so:
    x = ipl[so[-1][0]]
    print("super over innings keys:", [ (i["team"], i.get("super_over")) for i in x["innings"]], x["info"]["outcome"])
dls = [(n, x["info"]["dates"][0], x["info"]["outcome"]) for n, x in ipl.items() if x["info"].get("outcome", {}).get("method")]
print("DLS matches:", len(dls), dls[-2:])
if dls:
    x = ipl[dls[-1][0]]
    print("DLS target repr:", [i.get("target") for i in x["innings"]])
all_rep_kinds = collections.Counter()
for x in ipl.values():
    for i in x["innings"]:
        for ov in i["overs"]:
            for dl in ov["deliveries"]:
                for k, v in dl.get("replacements", {}).items():
                    for e in v: all_rep_kinds[(k, e.get("reason"))] += 1
print("replacement kinds (all IPL):", all_rep_kinds)
print("info key frequency 2026:", collections.Counter(k for x in ipl.values() if str(x['info']['season'])=='2026' for k in x['info']))
