"""Scrape every IPL 2026 match (ids from spikes/misc/samples/ipl2026_matches.tsv) sequentially, <=1 req/s.
usage: run_all.py [--refetch]   -> normalized/<id>.json for all, prints aggregate request stats."""
import csv, sys, time, traceback
from pathlib import Path
import scrape_match as sm

TSV = Path(__file__).parent.parent / "misc" / "samples" / "ipl2026_matches.tsv"
ids = [r["file"].split(".")[0] for r in csv.DictReader(open(TSV), delimiter="\t")]
t0, fails = time.time(), []
for mid in ids:
    try:
        sm.main([mid] + sys.argv[1:])
    except Exception as e:
        traceback.print_exc()
        fails.append((mid, repr(e)))
print(f"\nTOTAL matches={len(ids)} failed={fails} stats={sm.STATS} wall={time.time()-t0:.0f}s")
