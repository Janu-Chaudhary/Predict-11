"""Probe 04: capture request headers the browser sends to epr.ellipsedata.com / stats.bcci.tv (to find auth like the `Edak` header)."""
import sys, json, pathlib
from playwright.sync_api import sync_playwright
url = sys.argv[1]
out = []
with sync_playwright() as p:
    b = p.chromium.launch(headless=True); pg = b.new_page()
    def onreq(r):
        if "ellipsedata" in r.url or "stats.bcci.tv" in r.url or "emc.cricviz" in r.url:
            out.append({"url": r.url, "headers": r.all_headers()})
    pg.on("request", onreq)
    pg.goto(url, wait_until="networkidle", timeout=60000)
    b.close()
pathlib.Path(__file__).parent.joinpath("samples/04_headers.json").write_text(json.dumps(out, indent=1))
for o in out: print(o["url"][:120]); print("   ", {k: v for k, v in o["headers"].items() if k.lower() not in ("user-agent","accept-language","sec-ch-ua","sec-ch-ua-mobile","sec-ch-ua-platform","accept-encoding")})
