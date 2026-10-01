"""Probe 02: load a page in headless Chromium, log every XHR/fetch (+ any JSON response) to samples/02_<tag>/.
usage: python 02_pw_capture.py <tag> <url> [click-text ...]"""
import sys, json, time, pathlib, hashlib
from playwright.sync_api import sync_playwright
tag, url, clicks = sys.argv[1], sys.argv[2], sys.argv[3:]
out = pathlib.Path(__file__).parent / "samples" / f"02_{tag}"; out.mkdir(parents=True, exist_ok=True)
log = []
def on_resp(r):
    req = r.request
    if req.resource_type not in ("xhr", "fetch", "websocket", "eventsource", "other", "script"): return
    if req.resource_type == "script" and "iplt20" in r.url: return
    ent = {"type": req.resource_type, "method": req.method, "status": r.status, "url": r.url,
           "ct": r.headers.get("content-type", "")}
    try:
        if req.resource_type in ("xhr", "fetch", "other"):
            body = r.body()
            ent["len"] = len(body)
            fn = hashlib.md5(r.url.encode()).hexdigest()[:10] + (".json" if "json" in ent["ct"] else ".txt")
            (out / fn).write_bytes(body); ent["file"] = fn
    except Exception as e:
        ent["err"] = str(e)
    log.append(ent)
with sync_playwright() as p:
    b = p.chromium.launch(headless=True)
    ctx = b.new_context(user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0 Safari/537.36", viewport={"width":1400,"height":900})
    pg = ctx.new_page()
    pg.on("response", on_resp)
    pg.on("websocket", lambda ws: log.append({"type": "ws-open", "url": ws.url}))
    t = time.time()
    pg.goto(url, wait_until="networkidle", timeout=60000)
    print(f"loaded in {time.time()-t:.1f}s final={pg.url}")
    for _ in range(6):
        pg.mouse.wheel(0, 2500); time.sleep(1)
    for c in clicks:
        try:
            pg.get_by_text(c, exact=True).first.click(timeout=8000); print("clicked", c)
            pg.wait_for_load_state("networkidle"); time.sleep(2)
            for _ in range(4): pg.mouse.wheel(0, 2500); time.sleep(1)
        except Exception as e:
            print("click fail", c, str(e)[:100])
    (out / "page.html").write_text(pg.content())
    (out / "page.txt").write_text(pg.inner_text("body"))
    b.close()
(out / "_log.json").write_text(json.dumps(log, indent=1))
for e in log:
    print(e.get("status"), e["type"], e.get("len"), e["url"][:200])
