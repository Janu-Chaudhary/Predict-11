"""Polite cached GET for stats.bcci.tv / epr.ellipsedata.com / iplt20.com (<=1 req/sec, raw saved to disk)."""
import json
import os
import pathlib
import time

from curl_cffi import requests

ROOT = pathlib.Path(__file__).parent
RAW = ROOT / "samples" / "raw"
UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
      "Chrome/128.0 Safari/537.36")
EDAK = os.environ.get("EDAK", "dREj-f+6etraCroX6")  # public Ellipse widget key (see edak_check.py)
BASE_H = {"User-Agent": UA, "Origin": "https://www.iplt20.com", "Referer": "https://www.iplt20.com/",
          "Accept": "application/json"}

STATS = {"requests": 0, "cached": 0, "seconds": 0.0}
_last = [0.0]


def get_json(url: str, dest: pathlib.Path, edak: bool = False, refresh: bool = False):
    """Return parsed JSON for url; reuse dest if present (unless refresh). Rate-limited to <=1 req/s."""
    if dest.exists() and not refresh:
        STATS["cached"] += 1
        return json.loads(dest.read_text())
    wait = 1.05 - (time.time() - _last[0])
    if wait > 0:
        time.sleep(wait)
    h = dict(BASE_H)
    if edak:
        h["Edak"] = EDAK
    t = time.time()
    r = requests.get(url, headers=h, impersonate="chrome", timeout=40)
    _last[0] = time.time()
    STATS["requests"] += 1
    STATS["seconds"] += time.time() - t
    if r.status_code != 200:
        raise RuntimeError(f"HTTP {r.status_code} {url}: {r.text[:200]}")
    if r.text[:200].lstrip().startswith("{") and '"error"' in r.text[:200]:
        raise RuntimeError(f"API error (Edak rotated? run edak_check.py) {url}: {r.text[:200]}")
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(r.content)
    return r.json()
