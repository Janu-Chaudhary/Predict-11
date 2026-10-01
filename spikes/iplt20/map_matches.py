"""Map Cricsheet match ids -> BCCI (stats.bcci.tv) match UUIDs using date AND both team names.

usage: map_matches.py <cricsheet_id> [...] | --all   -> writes samples/raw/match_map.json, prints mapping
"""
import csv
import json
import pathlib
import sys

from http_util import RAW, get_json

HERE = pathlib.Path(__file__).parent
TSV = HERE.parent / "misc" / "samples" / "ipl2026_matches.tsv"


def season_gid(season="2026"):
    d = get_json(f"https://www.iplt20.com/api/bff/cms/matches?status=results&season={season}",
                 RAW / f"_bff_matches_{season}.json")
    comps = d["data"]["competitions"]
    for c in (comps["data"] if isinstance(comps, dict) else comps):
        if c.get("externalGid"):
            return c["externalGid"]
    raise RuntimeError("no externalGid in BFF matches response")


def results(gid):
    out, page = [], 1
    while True:
        d = get_json(f"https://stats.bcci.tv/match/results/?comp_gid={gid}&min_start_date=2026-01-01"
                     f"&page={page}&size=100", RAW / f"_results_p{page}.json")
        out += d["match"]
        if not d["page"].get("next_page"):
            return out
        page += 1


def main(ids):
    idx = {r["file"].split(".")[0]: r for r in csv.DictReader(open(TSV), delimiter="\t")}
    if ids == ["--all"]:
        ids = list(idx)
    gid = season_gid()
    ms = results(gid)
    mapping = {}
    for cs in ids:
        row = idx[cs]
        teams = set(t.strip() for t in row["teams"].split(" v "))
        hits = [m for m in ms if m["start_date"] == row["date"]
                and {m["team1_name"], m["team2_name"]} == teams]
        if len(hits) != 1:
            print(f"{cs}: {len(hits)} candidates for {row['date']} {teams}")
            mapping[cs] = None
            continue
        m = hits[0]
        mapping[cs] = m["gid"]
        print(f"{cs}\t{m['gid']}\t{m['start_date']}\t{m['match_short_name']}\t{m['match_status']}\t"
              f"{m['result_name']}\t{m['result_string']}")
    used = [g for g in mapping.values() if g]
    dup = {g for g in used if used.count(g) > 1}
    unused = [m["gid"] for m in ms if m["gid"] not in used]
    print(f"mapped {len(used)}/{len(ids)}; duplicate UUIDs: {sorted(dup)}; BCCI matches unmapped: {len(unused)}")
    for m in ms:
        if m["gid"] in unused:
            print("  unmapped BCCI:", m["gid"], m["start_date"], m["team1_name"], "v", m["team2_name"])
    (RAW / "match_map.json").write_text(json.dumps(mapping, indent=1))
    print(f"results list: {len(ms)} matches, comp_gid={gid}")


if __name__ == "__main__":
    main(sys.argv[1:])
