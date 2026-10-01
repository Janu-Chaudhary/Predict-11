"""Probe 09: validate captured ball-by-ball (07) against the SSR scorecard (03) and, if present, Cricsheet.

usage: 09_validate.py <matchId> <balls_prefix>
"""
import io, json, sys, zipfile, pathlib, collections
import requests

S = pathlib.Path(__file__).parent / "samples"
MID, PFX = sys.argv[1], sys.argv[2]
balls = json.loads((S / f"07_{PFX}_balls.json").read_text())
sc = json.loads((S / f"03_{MID}_full-scorecard.next.json").read_text())["props"]["appPageProps"]["data"]

# internal player id -> (objectId, longName) from every player object in the scorecard payload
pid = {}
def harvest(o):
    if isinstance(o, dict):
        if "objectId" in o and "longName" in o and "battingName" in o:
            pid[o["id"]] = (o["objectId"], o["longName"])
        for v in o.values(): harvest(v)
    elif isinstance(o, list):
        for v in o: harvest(v)
harvest(sc)

ok = True
for inn in sc["content"]["innings"]:
    n = inn["inningNumber"]
    bb = [b for b in balls if b["inningNumber"] == n]
    runs = sum(b["totalRuns"] for b in bb)
    wk = sum(1 for b in bb if b["isWicket"])
    legal = sum(1 for b in bb if not b["wides"] and not b["noballs"])
    ext = {k: sum(b[k] for b in bb) for k in ("wides", "noballs", "byes", "legbyes", "penalties")}
    print(f"inn {n}: balls={len(bb)} legal={legal} runs={runs} vs scorecard {inn['runs']} | wkts={wk} vs {inn['wickets']} | "
          f"extras {ext} vs w={inn['wides']} nb={inn['noballs']} b={inn['byes']} lb={inn['legbyes']}")
    ok &= runs == inn["runs"] and wk == inn["wickets"]
    # per-batter / per-bowler vs scorecard
    bat = collections.Counter(); bowlw = collections.Counter()
    for b in bb:
        bat[b["batsmanPlayerId"]] += b["batsmanRuns"]
        if b["isWicket"] and b["dismissalType"] not in (4, 6, 7):   # exclude run out etc. (checked below)
            bowlw[b["bowlerPlayerId"]] += 1
    for x in inn["inningBatsmen"]:
        if x["runs"] is not None and bat[x["player"]["id"]] != x["runs"]:
            ok = False; print("   BAT MISMATCH", x["player"]["longName"], bat[x["player"]["id"]], x["runs"])
    for x in inn["inningBowlers"]:
        if bowlw[x["player"]["id"]] != x["wickets"]:
            print("   bowler wkts differ (maybe runout kind code)", x["player"]["longName"], bowlw[x["player"]["id"]], x["wickets"])
    unk = {b["batsmanPlayerId"] for b in bb} | {b["bowlerPlayerId"] for b in bb}
    print("   unmapped player ids:", [u for u in unk if u not in pid])
print("dismissalType codes seen:", collections.Counter((b["dismissalType"], (b.get("dismissalText") or {}).get("short")) for b in balls if b["isWicket"]))
print("SCORECARD RECONCILES:", ok)

# ---- Cricsheet comparison ----
zp = S / "ipl_json.zip"
if not zp.exists():
    r = requests.get("https://cricsheet.org/downloads/ipl_json.zip", timeout=120,
                     headers={"User-Agent": "predict11-spike/0.1 (personal research)"})
    print("cricsheet zip", r.status_code, len(r.content)); zp.write_bytes(r.content)
z = zipfile.ZipFile(zp)
name = f"{MID}.json"
if name not in z.namelist():
    print(f"Cricsheet: {name} NOT in ipl_json.zip ({len(z.namelist())} files; newest:",
          sorted(n for n in z.namelist() if n.endswith('.json'))[-3:], ")")
    sys.exit()
cs = json.loads(z.read(name))
reg = cs["info"]["registry"]["people"]
cs_bat = collections.Counter(); cs_bowl = collections.Counter()
for ii, inn in enumerate(cs["innings"]):
    for ov in inn["overs"]:
        for d in ov["deliveries"]:
            cs_bat[(ii + 1, d["batter"])] += d["runs"]["batter"]
            for w in d.get("wickets", []):
                if w["kind"] not in ("run out", "retired hurt", "retired out", "obstructing the field"):
                    cs_bowl[(ii + 1, d["bowler"])] += 1
my_bat = collections.Counter(); my_bowl = collections.Counter()
for b in balls:
    my_bat[(b["inningNumber"], pid[b["batsmanPlayerId"]][1])] += b["batsmanRuns"]
    if b["isWicket"] and b["dismissalType"] not in (4, 6, 7):
        my_bowl[(b["inningNumber"], pid[b["bowlerPlayerId"]][1])] += 1
print("Cricsheet names (sample):", list(cs_bat)[:4], "| cricinfo longName (sample):", list(my_bat)[:4])
print("cricsheet per-batter total", sum(cs_bat.values()), "vs mine", sum(my_bat.values()))
print("cricsheet bowler wkts", sum(cs_bowl.values()), "vs mine", sum(my_bowl.values()))

# per-player comparison keyed on cricinfo objectId via Cricsheet people.csv (key_cricinfo)
import csv
pp = S / "people.csv"
if not pp.exists():
    pp.write_bytes(requests.get("https://cricsheet.org/register/people.csv", timeout=60,
                                headers={"User-Agent": "predict11-spike/0.1 (personal research)"}).content)
key = {row["identifier"]: row["key_cricinfo"] for row in csv.DictReader(pp.open())}
name2ci = {n: key.get(i) for n, i in reg.items()}
cs_by = collections.Counter({(i, name2ci[n]): v for (i, n), v in cs_bat.items()})
my_by = collections.Counter()
for b in balls:
    my_by[(b["inningNumber"], str(pid[b["batsmanPlayerId"]][0]))] += b["batsmanRuns"]
missing = [n for n, c in name2ci.items() if not c]
print("cricsheet registry names without key_cricinfo:", missing)
diff = {k: (cs_by.get(k), my_by.get(k)) for k in set(cs_by) | set(my_by) if cs_by.get(k) != my_by.get(k)}
print(f"per-batter runs keyed by cricinfo id: {len(cs_by)} batters, mismatches: {diff}")
