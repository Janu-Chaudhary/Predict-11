"""Fetch only ESPNcricinfo full-scorecard __NEXT_DATA__ pages (no ball-by-ball API) for all
IPL 2026 matches. Used for player/match ID linking (cricinfo ID == Cricsheet key_cricinfo)."""
import csv
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from scrape_match import fetch_scorecard  # noqa: E402

HERE = Path(__file__).parent
TSV = HERE.parents[0] / "misc" / "samples" / "ipl2026_matches.tsv"

ids = [r["file"].removesuffix(".json") for r in csv.DictReader(open(TSV), delimiter="\t")]
ok, failed, t0 = 0, [], time.time()
for mid in ids:
    try:
        rawdir = HERE / "samples" / "raw" / mid
        rawdir.mkdir(parents=True, exist_ok=True)
        nd = fetch_scorecard(mid, rawdir, False)
        players = sum(len(t.get("players", [])) for t in nd["props"]["appPageProps"]["data"]["content"]["matchPlayers"]["teamPlayers"])
        ok += 1
        print(f"{mid} ok players={players}", flush=True)
    except Exception as e:  # noqa: BLE001
        failed.append((mid, repr(e)[:120]))
        print(f"{mid} FAILED {e!r}"[:160], flush=True)
print(f"\n{ok}/{len(ids)} scorecards, {len(failed)} failed, {time.time()-t0:.0f}s")
for f in failed:
    print("  ", *f)
