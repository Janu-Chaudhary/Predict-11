"""Probe 05: Playwright headless Chromium; load commentary page, scroll, capture all XHR/fetch JSON + request headers."""
import json, sys, time, pathlib
from playwright.sync_api import sync_playwright

S = pathlib.Path(__file__).parent / "samples"
URL = sys.argv[1] if len(sys.argv) > 1 else "https://www.espncricinfo.com/series/ipl-2026-1510719/royal-challengers-bengaluru-vs-gujarat-titans-final-1535465/ball-by-ball-commentary"
MODE = sys.argv[2] if len(sys.argv) > 2 else "shell"  # shell | chromium-new | chrome-headless | chrome-headed
SCROLLS = int(sys.argv[3]) if len(sys.argv) > 3 else 25
log = []

with sync_playwright() as p:
    args = ["--disable-blink-features=AutomationControlled"]
    kw = dict(headless=MODE != "chrome-headed", args=args)
    if MODE == "chromium-new": kw["channel"] = "chromium"
    if MODE.startswith("chrome-"): kw["channel"] = "chrome"
    if MODE == "chrome-headed": args.append("--window-position=-2400,0")
    print("mode", MODE, kw)
    b = p.chromium.launch(**kw)
    ctx = b.new_context(
                        viewport={"width": 1366, "height": 900}, locale="en-US")
    page = ctx.new_page()

    def on_resp(r):
        rt = r.request.resource_type
        if rt in ("xhr", "fetch") and ("consumer" in r.url or "api" in r.url):
            entry = {"url": r.url, "status": r.status, "req_headers": r.request.headers}
            try:
                body = r.body(); entry["size"] = len(body)
                if r.status == 200 and "comments" in r.url:
                    fn = S / f"05_xhr_{len(log)}.json"; fn.write_bytes(body); entry["saved"] = fn.name
            except Exception as e:
                entry["err"] = str(e)
            log.append(entry)
            print(r.status, entry.get("size"), r.url[:160])
    page.on("response", on_resp)
    t = time.time()
    resp = page.goto(URL, wait_until="domcontentloaded", timeout=60000)
    print("page", resp.status, f"{time.time()-t:.1f}s")
    page.wait_for_timeout(4000)
    for i in range(SCROLLS):
        page.mouse.wheel(0, 4000)
        page.wait_for_timeout(1200)
    (S / "05_xhr_log.json").write_text(json.dumps(log, indent=1))
    print("total xhr", len(log), f"{time.time()-t:.1f}s")
    b.close()
