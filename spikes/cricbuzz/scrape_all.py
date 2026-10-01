"""Scrape every mapped match (samples/raw/_map_74.tsv from map_matches.py) and log aggregate cost.

Usage: scrape_all.py [--refresh]   -> normalized/<cricsheet_id>.json for each, samples/raw/_scrape_all_log.json
"""
import json
import sys
import time
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import scrape_match as sm  # noqa: E402

HERE = Path(__file__).parent
refresh = "--refresh" in sys.argv
rows = [l.split("\t")[:2] for l in (HERE / "samples/raw/_map_74.tsv").read_text().splitlines() if l.strip()]
agg = {"matches": len(rows), "requests": 0, "retries": 0, "cached": 0, "errors": [], "failed": [], "notes": {}}
t0 = time.time()
for mid, cs in rows:
    sm.LOG.clear(); sm.LOG.update(requests=0, retries=0, errors=[], cached=0)
    try:
        sm.scrape(mid, cs, refresh=refresh)
        if sm.LOG.get("notes"):
            agg["notes"][cs] = sm.LOG["notes"]
    except Exception as e:
        agg["failed"].append(f"{mid}/{cs}: {type(e).__name__}: {e}")
        traceback.print_exc()
    for k in ("requests", "retries", "cached"):
        agg[k] += sm.LOG.get(k, 0)
    agg["errors"] += sm.LOG.get("errors", [])
    print(f"{mid} {cs} req={sm.LOG.get('requests')} err={len(sm.LOG.get('errors', []))}", flush=True)
agg["wall_s"] = round(time.time() - t0, 1)
(HERE / "samples/raw/_scrape_all_log.json").write_text(json.dumps(agg, indent=1))
print({k: v for k, v in agg.items() if k != "notes"})
