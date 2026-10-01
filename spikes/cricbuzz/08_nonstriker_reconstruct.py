"""Spike: can we reconstruct the non-striker for every Cricbuzz delivery?

Method: track the pair of batters at the crease. Striker is given per ball; the non-striker is
the other one. On a wicket, remove the dismissed batter (from scorecard wicketsData, in order)
and bring in the next batter by scorecard batting order.

Validate ball-by-ball against Cricsheet's non_striker for the same match.
Usage: 08_nonstriker_reconstruct.py <cricbuzz_mid> <cricsheet_id>
"""
import json
import sys
import zipfile
from pathlib import Path

S = Path(__file__).parent / "samples"
MISC = Path(__file__).parents[1] / "misc" / "samples" / "ipl_json.zip"


def surname(name: str) -> str:
    return name.split()[-1].lower()


def reconstruct(mid: str, inn: int) -> list[dict]:
    sc = json.loads((S / f"03_{mid}_scorecard.json").read_text())["scoreCard"][inn - 1]
    order = [b["batName"] for b in sc["batTeamDetails"]["batsmenData"].values()]
    wkts = sorted(sc["wicketsData"].values(), key=lambda w: w["wktNbr"])
    dels = json.loads((S / f"04_{mid}_deliveries_inn{inn}.json").read_text())

    crease = order[:2]
    next_in = 2
    wk_i = 0
    out = []
    for d in dels:
        striker = d["batter"]
        if striker not in crease:  # unexpected: a batter we didn't bring in yet
            crease = [c for c in crease if c != crease[-1]] + [striker]
        non = next((c for c in crease if c != striker), None)
        out.append({**d, "non_striker": non})
        if d["wicket"] and wk_i < len(wkts):
            gone = wkts[wk_i]["batName"]
            wk_i += 1
            crease = [c for c in crease if c != gone]
            if next_in < len(order):
                crease.append(order[next_in])
                next_in += 1
    return out


def cricsheet_innings(cs_id: str, inn: int) -> list[dict]:
    with zipfile.ZipFile(MISC) as z:
        doc = json.loads(z.read(f"{cs_id}.json"))
    rows = []
    for ov in doc["innings"][inn - 1]["overs"]:
        for d in ov["deliveries"]:
            rows.append(d)
    return rows


def main(mid: str, cs_id: str):
    for inn in (1, 2):
        cb = reconstruct(mid, inn)
        cs = cricsheet_innings(cs_id, inn)
        n = min(len(cb), len(cs))
        bad_striker = bad_non = 0
        for i in range(n):
            if surname(cb[i]["batter"]) != surname(cs[i]["batter"]):
                bad_striker += 1
            if cb[i]["non_striker"] is None or surname(cb[i]["non_striker"]) != surname(cs[i]["non_striker"]):
                bad_non += 1
                if bad_non <= 5:
                    print(f"  inn{inn} #{i} {cb[i]['over']}: cb non={cb[i]['non_striker']} "
                          f"cs non={cs[i]['non_striker']} (striker cb={cb[i]['batter']} cs={cs[i]['batter']})")
        print(f"innings {inn}: cricbuzz={len(cb)} cricsheet={len(cs)} balls | "
              f"striker mismatches={bad_striker} non-striker mismatches={bad_non}")


if __name__ == "__main__":
    main(*(sys.argv[1:3] or ["155409", "1535465"]))
