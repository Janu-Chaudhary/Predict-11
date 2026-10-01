"""Probe 05: validate Ellipse commentary ball-by-ball vs stats.bcci.tv scorecard; test name->ID mapping from ball_summary_text."""
import json, sys, re, collections, pathlib
D = pathlib.Path(__file__).parent / "samples" / "03"
pre = sys.argv[1] if len(sys.argv) > 1 else "final"
com = json.load(open(D / f"{pre}_commentary_epr_plain.json"))
sc = json.load(open(D / f"{pre}_scorecard_bcci.json"))
known = {}
for t in sc["team"]:
    for p in t["player"]:
        known[p["known_as"]] = p["player_id"]
tot = {i["innings_number"]: (int(i["runs"]), int(i["wickets"]), int(i["total_balls_bowled"])) for i in sc["innings"]}
ok = True
for inn in com["innings"]:
    balls = [b for o in inn["bbb"] for b in o["balls"]]
    runs = sum(b["runs"] for b in balls); wk = sum(1 for b in balls if "W" in b["scoring"])  # e.g. "W", "1,W" (run-out after a run)
    unmapped = collections.Counter()
    for b in balls:
        m = re.match(r"(.+?) to (.+?)(,|$)", b["commentary"]["ball_summary_text"] or "")
        if not m: unmapped["<nomatch>"] += 1; continue
        for n in m.group(1), m.group(2):
            if n not in known: unmapped[n] += 1
    exp = tot[str(inn["innings_number"])]
    print(f"inn {inn['innings_number']}: bbb runs={runs} wkts={wk} balls={len(balls)} | scorecard runs={exp[0]} wkts={exp[1]} balls={exp[2]} -> {'MATCH' if (runs,wk,len(balls))==exp else 'MISMATCH'}; unmapped names={dict(unmapped)}")
    ok &= (runs, wk) == exp[:2]
print("scoring codes:", collections.Counter(b["scoring"] for inn in com["innings"] for o in inn["bbb"] for b in o["balls"]))
