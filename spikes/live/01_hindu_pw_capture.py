"""Probe 01: open Hindu/Sportstar cricket live-score pages headless and log every XHR/fetch
to livescoreapi.thehindu.com (or any JSON) so we can discover the endpoint family.
usage: python 01_hindu_pw_capture.py <url> [<url> ...]"""
import json, pathlib, sys, time
from playwright.sync_api import sync_playwright

OUT = pathlib.Path(__file__).parent / "samples" / "pw"
OUT.mkdir(parents=True, exist_ok=True)
UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0 Safari/537.36"
seen = []

def on_resp(r):
    u = r.url
    ct = r.headers.get("content-type", "")
    if "livescore" in u or ("json" in ct and "thehindu" in u):
        try:
            b = r.body()
        except Exception:
            b = b""
        seen.append((r.status, len(b), u))
        name = u.split("://", 1)[1].replace("/", "_").replace("?", "_")[:150]
        if b:
            (OUT / name).write_bytes(b)

with sync_playwright() as p:
    br = p.chromium.launch(headless=True)
    pg = br.new_page(user_agent=UA)
    pg.on("response", on_resp)
    for url in sys.argv[1:]:
        try:
            pg.goto(url, wait_until="domcontentloaded", timeout=45000)
            pg.wait_for_timeout(8000)
            print("PAGE", url, "->", pg.url, pg.title()[:80])
            links = pg.eval_on_selector_all("a[href]", "els => els.map(e => e.href)")
            for l in sorted({l for l in links if any(k in l for k in ("score", "matchcentre", "match-centre", "live"))})[:40]:
                print("  link", l)
        except Exception as e:
            print("ERR", url, e)
        time.sleep(1)
    br.close()
for s in seen:
    print(*s)
