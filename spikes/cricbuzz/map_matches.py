"""Map Cricsheet IPL 2026 match ids -> Cricbuzz match ids by IST date AND both team names.

Usage: map_matches.py <cricsheet_id> [...]   -> prints "<cricbuzz_mid>\t<cricsheet_id>\t<desc>" lines
Series page cached at samples/raw/series_9241_matches.html (one polite request if missing).
"""
import csv
import datetime as dt
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from scrape_match import fetch, rsc  # noqa: E402

HERE = Path(__file__).parent
TSV = HERE.parent / "misc" / "samples" / "ipl2026_matches.tsv"
IST = dt.timezone(dt.timedelta(hours=5, minutes=30))


def cricbuzz_matches():
    html = fetch("/cricket-series/9241/indian-premier-league-2026/matches",
                 HERE / "samples" / "raw" / "series_9241_matches.html", False, False)
    s, dec, out = rsc(html), json.JSONDecoder(), {}
    for m in re.finditer(r'\{"matchId":(\d+),"seriesId":9241', s):
        o = dec.raw_decode(s[m.start():])[0]
        out[o["matchId"]] = o
    return list(out.values())


def main(ids):
    cs = {r["file"].split(".")[0]: r for r in csv.DictReader(open(TSV), delimiter="\t")}
    cb = cricbuzz_matches()
    for cid in ids:
        r = cs[cid]
        teams = {t.strip().lower() for t in r["teams"].split(" v ")}
        hits = [m for m in cb
                if dt.datetime.fromtimestamp(int(m["startDate"]) / 1000, IST).date().isoformat() == r["date"]
                and {m["team1"]["teamName"].lower(), m["team2"]["teamName"].lower()} == teams]
        if len(hits) != 1:
            print(f"#UNMAPPED\t{cid}\t{r['date']} {r['teams']} hits={[h['matchId'] for h in hits]}", file=sys.stderr)
            continue
        h = hits[0]
        print(f"{h['matchId']}\t{cid}\t{r['date']} {h['matchDesc']} {h['team1']['teamSName']} v "
              f"{h['team2']['teamSName']} | {h['status']}")


if __name__ == "__main__":
    main(sys.argv[1:])
