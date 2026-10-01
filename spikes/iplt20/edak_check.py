"""Check the Ellipse `Edak` widget key; if it has rotated, re-capture it with headless Playwright.

usage: edak_check.py [matchUUID] [--force-capture]
  1. GET epr.ellipsedata.com/.../commentary with the current key (env EDAK or http_util default) -> 200?
  2. control: same request with NO key and a bogus key (shows the key is actually enforced)
  3. if the key fails (or --force-capture): open the iplt20 commentary page headless, sniff the `edak`
     request header the Ellipse widget sends, re-test it, and write it to samples/raw/_edak.txt
     (export EDAK=$(cat samples/raw/_edak.txt) to use it).
Note: the core scraper does NOT need Edak - stats.bcci.tv /scorecard and /bbb are unauthenticated.
Edak is only needed for epr.ellipsedata.com (squads short names, commentary text).
"""
import sys
import time

from curl_cffi import requests

from http_util import BASE_H, EDAK, RAW

UUID = next((a for a in sys.argv[1:] if not a.startswith("--")), "8c6b3b7b-d2c6-482e-936e-9454d7ee0eb2")
API = f"https://epr.ellipsedata.com/redirect/1/match/{UUID}/commentary"
PAGE = f"https://www.iplt20.com/matches/{UUID}/tbc-vs-tbc/commentary"


def probe(key):
    h = dict(BASE_H)
    if key is not None:
        h["Edak"] = key
    r = requests.get(API, headers=h, impersonate="chrome", timeout=30)
    time.sleep(1.1)
    ok = r.status_code == 200 and '"error"' not in r.text[:200]  # rejection is HTTP 200 + {"error": ...}
    return ok, r.status_code, r.text[:90].replace("\n", " ")


def capture():
    from playwright.sync_api import sync_playwright
    found = []
    with sync_playwright() as p:
        b = p.chromium.launch(headless=True)
        pg = b.new_page()
        pg.on("request", lambda r: found.append(r.headers.get("edak"))
              if "ellipsedata.com" in r.url and r.headers.get("edak") else None)
        pg.goto(PAGE, wait_until="domcontentloaded", timeout=60000)
        for _ in range(30):  # widget loads lazily; wait up to ~30s for the first epr request
            if found:
                break
            pg.mouse.wheel(0, 1500)
            pg.wait_for_timeout(1000)
        b.close()
    return found[0] if found else None


if __name__ == "__main__":
    st = probe(EDAK)
    print(f"current key {EDAK!r}: {st}")
    print(f"no key: {probe(None)}")
    print(f"bogus key: {probe('xxxx-invalid')}")
    if not st[0] or "--force-capture" in sys.argv:
        t = time.time()
        k = capture()
        print(f"captured via Playwright in {time.time()-t:.1f}s: {k!r}")
        if k:
            print(f"captured key re-test: {probe(k)}")
            (RAW / "_edak.txt").write_text(k)
