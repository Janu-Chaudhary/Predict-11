"""Scrape all mapped matches (samples/raw/match_map.json) with timing. usage: run_validation.py [--refresh]"""
import json
import sys
import time
import traceback

import scrape_match
from http_util import RAW, STATS

mp = json.loads((RAW / "match_map.json").read_text())
t0 = time.time()
for cs, uuid in mp.items():
    t = time.time()
    try:
        scrape_match.main(uuid, cs, refresh="--refresh" in sys.argv)
    except Exception:
        print(f"ERROR {cs} {uuid}")
        traceback.print_exc()
    print(f"  time {cs}: {time.time()-t:.1f}s")
print(f"TOTAL {time.time()-t0:.1f}s  http={STATS}")
