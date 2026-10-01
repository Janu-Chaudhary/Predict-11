"""Probe 11: validate ESPN open-API playbyplay (probe 10) vs cricinfo SSR scorecard (probe 03) and Cricsheet,
keyed on cricinfo player id (ESPN athlete.id == cricinfo objectId == people.csv key_cricinfo).

usage: 11_validate_espn_api.py <matchId> [...]
"""
import csv, json, sys, zipfile, pathlib, collections

S = pathlib.Path(__file__).parent / "samples"
key = {r["identifier"]: r["key_cricinfo"] for r in csv.DictReader((S / "people.csv").open())}
z = zipfile.ZipFile(S / "ipl_json.zip")
NON_BOWLER = ("run out", "retired hurt", "retired out", "obstructing the field")

for MID in sys.argv[1:]:
    print(f"===== {MID}")
    it = json.loads((S / f"10_{MID}_pbp_all.json").read_text())
    ids = [i["id"] for i in it]
    print(f"items={len(it)} unique={len(set(ids))} periods={collections.Counter(i['period'] for i in it)}")
    sc = json.loads((S / f"03_{MID}_full-scorecard.next.json").read_text())["props"]["appPageProps"]["data"]["content"]
    for inn in sc["innings"] + sc["superOverInnings"]:
        n = inn["inningNumber"]
        bb = [i for i in it if i["period"] == n]
        runs = sum(i["scoreValue"] for i in bb)
        wk = sum(1 for i in bb if i["dismissal"].get("dismissal"))
        legal = sum(1 for i in bb if not i["over"]["wide"] and not i["over"]["noBall"])
        flag = "OK" if (runs, wk) == (inn["runs"], inn["wickets"]) else "MISMATCH"
        print(f" inn {n} {inn['team']['abbreviation']}: deliveries={len(bb)} legal={legal} runs={runs}/{inn['runs']} wkts={wk}/{inn['wickets']} {flag}")
    fld = [i for i in it if i["dismissal"].get("dismissal") and i["dismissal"]["type"] in ("caught", "stumped", "run out")]
    print(" dismissals w/ fielder:", sum(1 for i in fld if (i["dismissal"].get("fielder") or {}).get("athlete", {}).get("id")), "/", len(fld),
          "kinds:", dict(collections.Counter(i["dismissal"]["type"] for i in it if i["dismissal"].get("dismissal"))))
    name = f"{MID}.json"
    if name not in z.namelist():
        print(" not in Cricsheet zip"); continue
    cs = json.loads(z.read(name))
    reg = {n: key.get(i) for n, i in cs["info"]["registry"]["people"].items()}
    cb, cw, cf = collections.Counter(), collections.Counter(), collections.Counter()
    for ii, inn in enumerate(cs["innings"]):
        for ov in inn["overs"]:
            for d in ov["deliveries"]:
                cb[(ii + 1, reg[d["batter"]])] += d["runs"]["batter"]
                for w in d.get("wickets", []):
                    if w["kind"] not in NON_BOWLER: cw[(ii + 1, reg[d["bowler"]])] += 1
                    for f in w.get("fielders", []):
                        if f.get("name"): cf[(ii + 1, reg[f["name"]])] += 1
    eb, ew, ef = collections.Counter(), collections.Counter(), collections.Counter()
    for i in it:
        n = i["period"]
        eb[(n, i["batsman"]["athlete"]["id"])] += i["batsman"]["runs"]
        dm = i["dismissal"]
        if dm.get("dismissal"):
            if dm["type"] not in NON_BOWLER: ew[(n, i["bowler"]["athlete"]["id"])] += 1
            fid = (dm.get("fielder") or {}).get("athlete", {}).get("id")
            if fid: ef[(n, fid)] += 1
    for lbl, a, b in (("batter runs", cb, eb), ("bowler wkts", cw, ew), ("fielder dismissals", cf, ef)):
        a = +a; b = +b
        diff = {k: (a.get(k), b.get(k)) for k in set(a) | set(b) if a.get(k) != b.get(k)}
        print(f" vs Cricsheet {lbl}: {len(a)} keys, mismatches={diff or 0}")
    print(" cricsheet innings:", [(inn["team"], len(inn["overs"])) for inn in cs["innings"]], "outcome:", cs["info"].get("outcome"))
