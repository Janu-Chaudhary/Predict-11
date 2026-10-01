"""Probe 02: load a Sportstar match-centre page, collect every JS bundle it loads, and grep them for
livescoreapi path templates (endpoint family discovery without guessing)."""
import pathlib, re, sys
from playwright.sync_api import sync_playwright

URL = sys.argv[1] if len(sys.argv) > 1 else \
    "https://sportstar.thehindu.com/cricket/matchcentre/ipl-2025/63975/rcb-vs-pnk/#scorecard"
UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0 Safari/537.36"
OUT = pathlib.Path(__file__).parent / "samples" / "hindu_js_endpoints.txt"
bodies = {}

with sync_playwright() as p:
    br = p.chromium.launch(headless=True)
    pg = br.new_page(user_agent=UA)

    def on_resp(r):
        if ("javascript" in r.headers.get("content-type", "") or r.url.endswith(".js")) and "thehindu" in r.url:
            try:
                bodies[r.url] = r.text()
            except Exception:
                pass
    pg.on("response", on_resp)
    pg.goto(URL, wait_until="domcontentloaded", timeout=45000)
    pg.wait_for_timeout(6000)
    html = pg.content()
    for tab in ("#commentary", "#playingxi", "#manhattan", "#summary"):
        try:
            pg.evaluate(f"location.hash = '{tab}'"); pg.wait_for_timeout(1500)
        except Exception:
            pass
    br.close()

bodies["<page>"] = html
hits = set()
for u, t in bodies.items():
    for m in re.finditer(r"""["'`]([^"'`\s]*(?:livescoreapi|/api/cricket/)[^"'`\s]*)["'`]""", t):
        hits.add((m.group(1)[:200], u[-80:]))
    for m in re.finditer(r"api/cricket/[a-zA-Z0-9_/-]+", t):
        hits.add((m.group(0), u[-80:]))
lines = sorted(hits)
OUT.write_text("\n".join(f"{a}\t{b}" for a, b in lines))
print(len(bodies), "bundles;", len(lines), "hits")
print("\n".join(f"{a}\t{b}" for a, b in lines))
