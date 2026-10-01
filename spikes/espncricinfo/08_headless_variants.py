"""Probe 08: which HEADLESS configurations get past Akamai on the commentary page?
Variants: bundled chromium (new headless) / real Chrome headless, with/without UA override
(default headless UA contains 'HeadlessChrome'), with/without the hs-consumer-api XHRs succeeding."""
import json, sys, time, pathlib
from playwright.sync_api import sync_playwright

S = pathlib.Path(__file__).parent / "samples"
URL = "https://www.espncricinfo.com/series/ipl-2026-1510719/royal-challengers-bengaluru-vs-gujarat-titans-final-1535465/ball-by-ball-commentary"
CHROME_VER = "153"
UA = f"Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{CHROME_VER}.0.0.0 Safari/537.36"

VARIANTS = {
    "chromium_default": dict(channel=None, ua=None),
    "chromium_ua": dict(channel=None, ua=UA),
    "chrome_default": dict(channel="chrome", ua=None),
    "chrome_ua": dict(channel="chrome", ua=UA),
    "chromiumchannel_ua": dict(channel="chromium", ua=UA),
}
sel = sys.argv[1:] or list(VARIANTS)
res = {}
with sync_playwright() as p:
    for name in sel:
        v = VARIANTS[name]
        kw = dict(headless=True, args=["--disable-blink-features=AutomationControlled"])
        if v["channel"]: kw["channel"] = v["channel"]
        b = p.chromium.launch(**kw)
        ckw = dict(viewport={"width": 1366, "height": 900}, locale="en-US")
        if v["ua"]: ckw["user_agent"] = v["ua"]
        ctx = b.new_context(**ckw)
        page = ctx.new_page()
        api = []
        page.on("response", lambda r: api.append((r.status, r.url.split("?")[0][-40:])) if "hs-consumer-api" in r.url else None)
        t = time.time()
        r = page.goto(URL, wait_until="domcontentloaded", timeout=60000)
        st = r.status
        page.wait_for_timeout(3000)
        for _ in range(4):
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)"); page.wait_for_timeout(1300)
        real_ua = page.evaluate("navigator.userAgent")
        res[name] = {"page": st, "api": api, "secs": round(time.time() - t, 1), "ua": real_ua[-60:]}
        print(name, json.dumps(res[name]))
        b.close()
        time.sleep(2)
(S / "08_headless_variants.json").write_text(json.dumps(res, indent=1))
