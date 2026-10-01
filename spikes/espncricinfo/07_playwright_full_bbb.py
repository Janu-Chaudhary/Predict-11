"""Probe 07: headed real Chrome (window offscreen) — drive the commentary page UI to page through the
comments API for BOTH innings, capturing every hs-consumer-api JSON response. No token forging: the page's
own JS signs each request; we just scroll and switch the innings tab.

usage: 07_playwright_full_bbb.py <match-commentary-url> <out_prefix>
"""
import json, sys, time, pathlib
from playwright.sync_api import sync_playwright

S = pathlib.Path(__file__).parent / "samples"
URL = sys.argv[1]
OUT = sys.argv[2]
balls, other, stats = {}, [], {"api_calls": 0, "api_bytes": 0, "statuses": {}}

def on_resp(r):
    if "hs-consumer-api" not in r.url: return
    stats["api_calls"] += 1
    stats["statuses"][r.status] = stats["statuses"].get(r.status, 0) + 1
    try: body = r.body()
    except Exception: return
    stats["api_bytes"] += len(body)
    if r.status != 200: return
    try: d = json.loads(body)
    except Exception: return
    if "/match/comments" in r.url:
        for c in d.get("comments", []):
            balls[c["id"]] = c
        print(f"  comments {r.url.split('inningNumber=')[1][:60]} -> {len(d.get('comments', []))} balls, next={d.get('nextInningOver')}")
    else:
        other.append({"url": r.url, "keys": list(d.keys())[:10], "size": len(body)})

def scroll_until_done(page, inning, max_iter=60):
    last, stale = -1, 0
    for _ in range(max_iter):
        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        page.wait_for_timeout(1300)
        page.evaluate("window.scrollBy(0, -600)")
        page.wait_for_timeout(500)
        n = sum(1 for b in balls.values() if b["inningNumber"] == inning)
        mn = min([b["oversUnique"] for b in balls.values() if b["inningNumber"] == inning] or [99])
        if n == last:
            stale += 1
            if stale >= 4: break
        else:
            stale = 0
        last = n
    print(f"  inning {inning}: {last} balls captured, min over {mn}")

t0 = time.time()
with sync_playwright() as p:
    # HEADLESS works only with the full browser in new-headless mode (channel="chromium"/"chrome", NOT the
    # default headless-shell) AND a UA override that drops "HeadlessChrome" (see probe 08).
    headed = "--headed" in sys.argv
    b = p.chromium.launch(channel="chromium", headless=not headed,
                          args=["--disable-blink-features=AutomationControlled"] + (["--window-position=-2400,0"] if headed else []))
    ctx = b.new_context(viewport={"width": 1366, "height": 900}, locale="en-US",
                        user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/153.0.0.0 Safari/537.36")
    page = ctx.new_page()
    page.on("response", on_resp)
    page.on("response", lambda r: (S / "raw").mkdir(exist_ok=True) or ((S / "raw" / f"{OUT}_{stats['api_calls']:03d}.json").write_bytes(r.body()) if "hs-consumer-api" in r.url and r.status == 200 and "/match/" in r.url else None))
    resp = page.goto(URL, wait_until="domcontentloaded", timeout=60000)
    print("page", resp.status)
    page.wait_for_timeout(3000)
    # SSR also embeds the latest ~12 balls
    nd = page.evaluate("JSON.parse(document.getElementById('__NEXT_DATA__').textContent).props.appPageProps.data")
    for c in nd["content"]["comments"]:
        balls[c["id"]] = c
    cur = nd["content"]["currentInningNumber"]
    scroll_until_done(page, cur)
    # switch to the other innings via the team dropdown (e.g. "RCB v") above the commentary
    page.evaluate("window.scrollTo(0, 0)"); page.wait_for_timeout(800)
    for txt in ["Accept All", "I Accept", "Got it"]:
        try: page.get_by_text(txt, exact=True).first.click(timeout=1500); page.wait_for_timeout(500)
        except Exception: pass
    page.keyboard.press("Escape"); page.wait_for_timeout(500)
    abbr = {t["team"]["id"]: t["team"]["abbreviation"] for t in nd["match"]["teams"]}
    inn_team = {i["inningNumber"]: abbr[i["team"]["id"]] for i in nd["content"]["innings"]}
    print("innings teams", inn_team)
    for inn, team in sorted(inn_team.items()):
        if inn == cur: continue
        try:
            dd = page.locator(".ds-popper-wrapper button[aria-expanded]").filter(has=page.locator("i.icon-caret_down"))
            print("  dropdown candidates", dd.count())
            dd.first.scroll_into_view_if_needed(); dd.first.click(timeout=5000); page.wait_for_timeout(1000)
            page.screenshot(path=str(S / f"07_{OUT}_dropdown.png"))
            bb = dd.first.bounding_box()
            pt = page.evaluate("""([team, y0]) => { const els = Array.from(document.querySelectorAll('li,div,span,a'))
                .filter(e => e.children.length === 0 && e.innerText && e.innerText.trim() === team);
                for (const e of els) { const r = e.getBoundingClientRect();
                  if (r.top > y0 && r.top < y0 + 250 && r.width > 0) return [r.left + r.width/2, r.top + r.height/2]; }
                return null; }""", [team, bb["y"] + bb["height"] - 2])
            print("  option at", pt)
            page.mouse.click(*pt); page.wait_for_timeout(2500)
            cur_team = team
        except Exception as e:
            print("  switch failed:", e); page.screenshot(path=str(S / f"07_{OUT}_fail.png")); continue
        scroll_until_done(page, inn)
    b.close()

out = sorted(balls.values(), key=lambda c: (c["inningNumber"], c["oversUnique"], c["id"]))
(S / f"07_{OUT}_balls.json").write_text(json.dumps(out))
print(json.dumps(stats), "other api:", [o["url"][:90] for o in other])
print(f"total balls {len(out)} by inning", {i: sum(1 for c in out if c['inningNumber'] == i) for i in (1, 2, 3, 4)}, f"elapsed {time.time()-t0:.1f}s")
