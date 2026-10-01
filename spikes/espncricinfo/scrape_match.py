"""ESPNcricinfo match scraper (open routes only) -> normalized JSON for spikes/compare/compare.py.

Sources (no hs-consumer-api, no tokens):
  1. www.espncricinfo.com match page (curl_cffi, impersonate="chrome") -> __NEXT_DATA__:
     meta, toss, matchPlayers (XI + impact sub), replacementPlayers, full scorecard
     (dismissalFielders), superOverInnings.  /matches/engine/match/<id>.html redirects to the
     slugged full-scorecard URL, so only the id is needed.
  2. ESPN open site API playbyplay (25 deliveries/page): batter, bowler, otherBatsman
     (= non-striker), runs, extras flags, dismissal.

usage: scrape_match.py <cricinfo_match_id> [--refetch]
writes normalized/<id>.json, raw responses under samples/raw/<id>/
"""
from __future__ import annotations

import json
import re
import sys
import time
from pathlib import Path

from curl_cffi import requests as cr

HERE = Path(__file__).parent
RAW = HERE / "samples" / "raw"
OUT = HERE / "normalized"
ESPN_PBP = "https://site.web.api.espn.com/apis/site/v2/sports/cricket/8676/playbyplay"
CI_MATCH = "https://www.espncricinfo.com/matches/engine/match/{id}.html"
MIN_GAP = 1.05  # seconds between requests (<= 1 req/s)

STATS = {"requests": 0, "retries_5xx": 0, "cache_hits": 0}
_session = None
_last = [0.0]

KIND = {  # ESPN pbp / cricinfo scorecard short text -> Cricsheet vocabulary
    "caught": "caught", "bowled": "bowled", "lbw": "lbw", "leg before wicket": "lbw",
    "run out": "run out", "stumped": "stumped", "hit wicket": "hit wicket",
    "caught and bowled": "caught and bowled", "obstructing the field": "obstructing the field",
    "obstruct field": "obstructing the field", "handled the ball": "handled the ball",
    "retired hurt": "retired hurt", "retired not out": "retired hurt", "retired out": "retired out",
    "timed out": "timed out", "hit the ball twice": "hit the ball twice",
}


def _get(url, params=None):
    global _session
    if _session is None:
        _session = cr.Session(impersonate="chrome")
    delay = 2.0
    for attempt in range(7):
        wait = MIN_GAP - (time.time() - _last[0])
        if wait > 0:
            time.sleep(wait)
        _last[0] = time.time()
        STATS["requests"] += 1
        try:
            r = _session.get(url, params=params, timeout=30, allow_redirects=True)
        except Exception as e:  # network hiccup -> treat like 5xx
            print(f"   ! {e!r}", file=sys.stderr)
            r = None
        if r is not None and r.status_code < 500:
            return r
        STATS["retries_5xx"] += 1
        print(f"   {r.status_code if r is not None else 'ERR'} {(r.text[:60] if r is not None else '')!r} "
              f"retry {attempt + 1} in {delay:.0f}s", file=sys.stderr)
        time.sleep(delay)
        delay *= 2
    raise RuntimeError(f"giving up on {url} {params}")


def _cached(path: Path, fetch, refetch: bool):
    if path.exists() and not refetch:
        STATS["cache_hits"] += 1
        return json.loads(path.read_text())
    data = fetch()
    path.write_text(json.dumps(data))
    return data


def fetch_scorecard(mid: str, rawdir: Path, refetch: bool) -> dict:
    def f():
        r = _get(CI_MATCH.format(id=mid))
        r.raise_for_status()
        m = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', r.text, re.S)
        if not m:
            raise RuntimeError(f"no __NEXT_DATA__ at {r.url}")
        nd = json.loads(m.group(1))
        nd["_fetched_url"] = str(r.url)
        return nd
    return _cached(rawdir / "full-scorecard.next.json", f, refetch)


def fetch_pbp(mid: str, rawdir: Path, refetch: bool) -> list[dict]:
    items, page, count = [], 1, 1
    while page <= count:
        def f(page=page):
            r = _get(ESPN_PBP, {"event": mid, "page": page})
            r.raise_for_status()
            return r.json()
        d = _cached(rawdir / f"pbp_p{page:02d}.json", f, refetch)
        c = d.get("commentary", {})
        count = c.get("pageCount", 1)
        items += c.get("items", [])
        if not c.get("items"):
            break
        page += 1
    return items


# --------------------------------------------------------------------------- normalize
class People:
    """cricinfo objectId <-> canonical name (longName), plus internal id -> objectId."""

    def __init__(self):
        self.name, self.by_internal, self.fielding = {}, {}, {}

    def add(self, p: dict | None):
        if not p or not p.get("objectId"):
            return None
        oid = str(p["objectId"])
        self.name.setdefault(oid, p.get("longName") or p.get("name"))
        if p.get("id"):
            self.by_internal[p["id"]] = oid
        if p.get("fieldingName"):
            self.fielding[oid] = p["fieldingName"]
        return oid


def nonstriker_reconstruct(rows: list[dict], order: list[str]) -> list[str | None]:
    """Crease-pair tracking (spikes/cricbuzz/08 method). rows need batter / player_out (objectIds)."""
    crease, nxt, out = list(order[:2]), 2, []
    for d in rows:
        s = d["_b"]
        if s not in crease:  # unexpected: drop the most recent arrival, keep the striker
            crease = [c for c in crease if c != crease[-1]] + [s] if len(crease) == 2 else crease + [s]
        out.append(next((c for c in crease if c != s), None))
        gone = d.get("_out")
        if gone:
            crease = [c for c in crease if c != gone]
            while nxt < len(order) and order[nxt] in crease:
                nxt += 1
            if nxt < len(order):
                crease.append(order[nxt])
                nxt += 1
    return out


def synth_super_over(inn: dict, P: People, fielding_team_oids: set[str], inn_no: int) -> tuple[list, str]:
    """Rebuild a 1-over super-over innings from scorecard aggregates by exhaustive search.
    Emits only if all consistent ball sequences agree (unique). Returns (rows, note)."""
    bowlers = inn.get("inningBowlers") or []
    if len(bowlers) != 1 or (inn.get("extras") or 0) != 0:
        return [], "skip: >1 bowler or extras present (order not determinable)"
    bowler = P.add(bowlers[0]["player"])
    bats = [b for b in inn["inningBatsmen"] if b.get("battedType") == "yes"]
    order = [P.add(b["player"]) for b in bats]
    need = {P.add(b["player"]): [b["runs"] or 0, b["balls"] or 0] for b in bats}
    fow = {round(f["fowOvers"] * 10) % 10 or 6: str(f["dismissalBatsman"]["objectId"])
           for f in inn.get("inningFallOfWickets") or []}  # legal ball no -> out batter
    dis = {P.add(b["player"]): b for b in bats if b.get("isOut")}
    nballs = inn["balls"]
    sols = []

    def dfs(i, striker, non, nxt, need, seq):
        if len(sols) > 1:
            return
        if i > nballs:
            if all(v == [0, 0] for v in need.values()):
                sols.append(list(seq))
            return
        if striker is None or need[striker][1] <= 0:
            return
        out = fow.get(i)
        for r in (0, 1, 2, 3, 4, 5, 6):
            if r > need[striker][0]:
                break
            n2 = {k: list(v) for k, v in need.items()}
            n2[striker][0] -= r
            n2[striker][1] -= 1
            s, ns = (non, striker) if r % 2 else (striker, non)
            nx = nxt
            if out:
                runout = dis[out]["dismissalText"]["short"] == "run out"
                if out not in (striker, non) or (not runout and (out != striker or r)):
                    continue
                newb = order[nx] if nx < len(order) else None
                nx += 1
                s, ns = (newb if s == out else s), (newb if ns == out else ns)
            seq.append((striker, non, r, out))
            dfs(i + 1, s, ns, nx, n2, seq)
            seq.pop()

    dfs(1, order[0], order[1] if len(order) > 1 else None, 2, need, [])
    if len(sols) != 1:
        return [], f"skip: {len(sols)} consistent sequences"
    rows = []
    for k, (b, ns, r, out) in enumerate(sols[0], start=1):
        row = {"innings": inn_no, "super_over": True, "over": 0, "ball": k, "batter": P.name[b],
               "bowler": P.name[bowler], "non_striker": P.name.get(ns) if ns else None,
               "batter_runs": r, "extras": 0, "extra_type": None, "wicket_kind": None,
               "player_out": None, "fielders": [], "cricinfo": {"batter": b, "bowler": bowler, "non_striker": ns}}
        if out:
            b_ = dis[out]
            kind = KIND.get(b_["dismissalText"]["short"], b_["dismissalText"]["short"])
            fl = []
            ft = (b_["dismissalText"].get("fielderText") or "").replace("†", "")
            ft = re.sub(r"^(c|st|run out)\s*\(?", "", ft).strip(" )")
            if ft and kind not in ("bowled", "lbw"):
                for part in ft.split("/"):
                    hit = [o for o in fielding_team_oids if P.fielding.get(o, "").replace("†", "") == part.strip()]
                    if len(hit) == 1:
                        fl.append(P.name[hit[0]])
            if kind == "caught" and b_["dismissalText"]["long"].strip().startswith("c & b"):
                kind, fl = "caught and bowled", []
            row.update(wicket_kind=kind, player_out=P.name[out], fielders=fl)
        rows.append(row)
    return rows, "synthesized (unique)"


def normalize(mid: str, nd: dict, items: list[dict]) -> dict:
    data = nd["props"]["appPageProps"]["data"]
    match, content = data["match"], data["content"]
    P = People()
    teams = {t["team"]["id"]: t["team"]["longName"] for t in match["teams"]}
    team_oid = {t["team"]["objectId"]: t["team"]["longName"] for t in match["teams"]}

    # ---- players
    players, status, team_of = [], {}, {}
    for tp in content["matchPlayers"]["teamPlayers"]:
        tname = tp["team"]["longName"]
        for p in tp["players"]:
            oid = P.add(p["player"])
            team_of[oid] = tname
            status[oid] = "xi" if tp["type"] == "PLAYING" else "sub"
    for rp in match.get("replacementPlayers") or []:
        if rp.get("playerReplacementType") == 8:  # impact player
            i, o = P.add(rp["player"]), P.add(rp["replacingPlayer"])
            status[i], status[o] = "impact_in", "impact_out"
            team_of.setdefault(i, rp["team"]["longName"])
            team_of.setdefault(o, rp["team"]["longName"])
    # scorecard people (fielders incl. substitutes)
    dismissals = {}  # (inningNumber, out objectId) -> batsman row
    batting_order = {}
    for inn in content["innings"] + (content.get("superOverInnings") or []):
        bt = inn["team"]["longName"]
        order = []
        for b in inn["inningBatsmen"]:
            oid = P.add(b["player"])
            team_of.setdefault(oid, bt)
            if b.get("battedType") == "yes":
                order.append(oid)
            if b.get("isOut"):
                dismissals[(inn["inningNumber"], oid)] = b
            for f in b.get("dismissalFielders") or []:
                fo = P.add(f.get("player"))
                if fo and fo not in status:
                    status[fo] = "sub"
                    team_of[fo] = next(t for t in teams.values() if t != bt)
        batting_order[inn["inningNumber"]] = order
        for b in inn.get("inningBowlers") or []:
            P.add(b["player"])
    for oid, st in status.items():
        players.append({"team": team_of.get(oid), "name": P.name[oid], "source_id": oid,
                        "cricinfo_id": oid, "status": st})

    # ---- toss
    toss = {"winner": teams.get(match.get("tossWinnerTeamId")),
            "decision": {1: "bat", 2: "field"}.get(match.get("tossWinnerChoice"))}

    # ---- deliveries from ESPN pbp
    seen, its = set(), []
    for it in sorted(items, key=lambda i: (i["period"], i["sequence"])):
        if it["id"] in seen or not it["batsman"]["athlete"].get("id"):
            continue  # duplicate, or empty placeholder row (e.g. id 999999999999999 in no-result games)
        seen.add(it["id"])
        its.append(it)
    skipped = len(items) - len(its)
    dels, ns_feed_vs_recon = [], {"agree": 0, "disagree": 0, "feed_missing": 0}
    unknown_kinds = set()
    for inn_no in sorted({i["period"] for i in its}):
        rows = []
        for it in (i for i in its if i["period"] == inn_no):
            ov, dm = it["over"], it["dismissal"]
            b = str(it["batsman"]["athlete"]["id"])
            bw = str(it["bowler"]["athlete"]["id"])
            ns = (it.get("otherBatsman") or {}).get("athlete", {}).get("id")
            for a in (it["batsman"]["athlete"], it["bowler"]["athlete"], (it.get("otherBatsman") or {}).get("athlete") or {}):
                if a.get("id"):
                    P.name.setdefault(str(a["id"]), a.get("displayName") or a.get("name"))
            br = it["batsman"].get("runs", 0) or 0
            ex = (it.get("scoreValue") or 0) - br
            et = ("wides" if ov.get("wide") else "noballs" if ov.get("noBall") else
                  "legbyes" if ov.get("legByes") else "byes" if ov.get("byes") else
                  "penalty" if ex else None)
            row = {"innings": inn_no, "super_over": False, "over": ov["number"] - 1, "ball": ov.get("ball"),
                   "_b": b, "_bw": bw, "_ns": str(ns) if ns else None, "_out": None,
                   "batter_runs": br, "extras": ex, "extra_type": et,
                   "wicket_kind": None, "player_out": None, "fielders": []}
            if dm.get("dismissal"):
                out = str(((dm.get("batsman") or {}).get("athlete") or {}).get("id") or b)
                sc = dismissals.get((inn_no, out))
                t = (dm.get("type") or "").lower()
                kind = KIND.get(t)
                if kind is None and sc and sc.get("dismissalText"):
                    kind = KIND.get(sc["dismissalText"]["short"])
                if kind is None:
                    unknown_kinds.add(t)
                    kind = t
                fl = []
                if sc:
                    fl = [P.add(f["player"]) for f in sc.get("dismissalFielders") or [] if f.get("player")]
                    if sc.get("dismissalText") and sc["dismissalText"]["long"].strip().startswith("c & b"):
                        kind = "caught and bowled"
                else:
                    fid = ((dm.get("fielder") or {}).get("athlete") or {}).get("id")
                    fl = [str(fid)] if fid else []
                if kind == "caught" and fl == [bw]:
                    kind = "caught and bowled"
                if kind in ("bowled", "lbw", "caught and bowled", "obstructing the field", "retired hurt",
                            "retired out", "hit wicket", "timed out", "handled the ball"):
                    fl = []
                row.update(_out=out, wicket_kind=kind, _fl=fl)
            rows.append(row)
        recon = nonstriker_reconstruct(rows, batting_order.get(inn_no, []))
        for row, rc in zip(rows, recon):
            if row["_ns"] is None:
                ns_feed_vs_recon["feed_missing"] += 1
                row["_ns"] = rc
            else:
                ns_feed_vs_recon["agree" if rc == row["_ns"] else "disagree"] += 1
            nm = lambda o: P.name.get(o) if o else None  # noqa: E731
            dels.append({"innings": row["innings"], "super_over": False, "over": row["over"], "ball": row["ball"],
                         "batter": nm(row["_b"]), "bowler": nm(row["_bw"]), "non_striker": nm(row["_ns"]),
                         "batter_runs": row["batter_runs"], "extras": row["extras"], "extra_type": row["extra_type"],
                         "wicket_kind": row["wicket_kind"], "player_out": nm(row["_out"]),
                         "fielders": [nm(f) for f in row.get("_fl", []) if f],
                         "cricinfo": {"batter": row["_b"], "bowler": row["_bw"], "non_striker": row["_ns"]}})

    # ---- super overs (not in ESPN pbp): synthesize from scorecard if unambiguous
    so_notes = {}
    have = {d["innings"] for d in dels}
    for inn in content.get("superOverInnings") or []:
        n = inn["inningNumber"]
        if n in have:
            continue
        fteam = next(t for t in teams.values() if t != inn["team"]["longName"])
        foids = {o for o, t in team_of.items() if t == fteam}
        rows, note = synth_super_over(inn, P, foids, n)
        so_notes[n] = note
        dels += rows

    return {
        "source": "espn", "source_match_id": mid, "cricsheet_id": mid,
        "meta": {"title": match.get("title"), "status": match.get("statusText"),
                 "url": nd.get("_fetched_url"), "pbp_items": len(its), "pbp_skipped": skipped,
                 "nonstriker_feed_vs_reconstruction": ns_feed_vs_recon,
                 "super_over": so_notes, "unknown_wicket_kinds": sorted(unknown_kinds)},
        "toss": toss, "players": players, "deliveries": dels,
    }


def main(argv):
    mid = argv[0]
    refetch = "--refetch" in argv
    rawdir = RAW / mid
    rawdir.mkdir(parents=True, exist_ok=True)
    OUT.mkdir(exist_ok=True)
    t0 = time.time()
    nd = fetch_scorecard(mid, rawdir, refetch)
    items = fetch_pbp(mid, rawdir, refetch)
    doc = normalize(mid, nd, items)
    doc["meta"]["scrape"] = {**STATS, "seconds": round(time.time() - t0, 1)}
    (OUT / f"{mid}.json").write_text(json.dumps(doc, indent=1))
    m = doc["meta"]
    print(f"{mid} {m['title']}: players={len(doc['players'])} deliveries={len(doc['deliveries'])} "
          f"ns={m['nonstriker_feed_vs_reconstruction']} so={m['super_over']} {m['scrape']}")


if __name__ == "__main__":
    main(sys.argv[1:])
