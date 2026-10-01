"""Scrape one Cricbuzz match and write the normalized JSON used by spikes/compare/compare.py.

Usage: scrape_match.py <cricbuzz_mid> <cricsheet_id> [--refresh]

Fetches (cached under samples/raw/<mid>/, re-used unless --refresh):
  /api/mcenter/scorecard/<mid>                 toss, batting order, wicketsData, wicketCode, fielder IDs
  /api/mcenter/<mid>/full-commentary/<inn>     ball-by-ball (+ super-over prose in the last innings)
  /cricket-match-squads/<mid>/match            playing XI / substitutes / bench + impact MIN/MOUT (RSC flight)
Writes normalized/<cricsheet_id>.json and samples/raw/<mid>/_fetch_log.json (requests/retries/errors/time).
Politeness: >=1.1 s between requests, Chrome UA, Referer https://www.cricbuzz.com/.
"""
from __future__ import annotations

import json
import re
import sys
import time
from pathlib import Path

import requests

HERE = Path(__file__).parent
BASE = "https://www.cricbuzz.com"
UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
      "Chrome/128.0.0.0 Safari/537.36")
S = requests.Session()
S.headers.update({"User-Agent": UA, "Accept-Language": "en-US,en;q=0.9",
                  "Referer": "https://www.cricbuzz.com/"})
GAP = 1.1
LAST_REQ = HERE / "samples" / "raw" / ".last_request"   # shared across processes -> global <=1 req/s
LOG = {"requests": 0, "retries": 0, "errors": [], "cached": 0}


def _throttle():
    try:
        last = float(LAST_REQ.read_text())
    except (OSError, ValueError):
        last = 0.0
    wait = GAP - (time.time() - last)
    if wait > 0:
        time.sleep(wait)
    LAST_REQ.parent.mkdir(parents=True, exist_ok=True)
    LAST_REQ.write_text(str(time.time()))


def fetch(path: str, dest: Path, refresh: bool, accept_json: bool) -> str:
    if dest.exists() and not refresh:
        LOG["cached"] += 1
        return dest.read_text()
    hdr = {"Accept": "application/json, text/plain, */*" if accept_json else "text/html,*/*"}
    for attempt in range(4):
        _throttle()
        LOG["requests"] += 1
        try:
            r = S.get(BASE + path, headers=hdr, timeout=45)
            if r.status_code == 200 and r.text.strip():
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_text(r.text)
                return r.text
            LOG["errors"].append(f"{path} HTTP {r.status_code} len={len(r.content)}")
        except requests.RequestException as e:
            LOG["errors"].append(f"{path} {type(e).__name__}: {e}")
        LOG["retries"] += 1
        time.sleep(2 ** attempt * 2)
    raise RuntimeError(f"giving up on {path}")


# ---------------------------------------------------------------- helpers
def subst(item: dict) -> str:
    """Replace B0$/I0$ placeholders with commentaryFormats values; strip HTML."""
    txt = item.get("commText") or ""
    for fmt in (item.get("commentaryFormats") or {}).values():
        for fid, fv in zip(fmt.get("formatId", []), fmt.get("formatValue", [])):
            txt = txt.replace(fid, fv)
    return re.sub(r"<[^>]+>", "", txt)


def rsc(html: str) -> str:
    return "".join(json.loads('"' + c + '"')
                   for c in re.findall(r'self\.__next_f\.push\(\[1,"(.*?)"\]\)</script>', html, re.S))


WK_CODE = {"CAUGHT": "caught", "BOWLED": "bowled", "LBW": "lbw", "STUMPED": "stumped",
           "CAUGHTBOWLED": "caught and bowled", "RUNOUT": "run out", "RUN OUT": "run out",
           "HITWICKET": "hit wicket", "HITWKT": "hit wicket", "HIT WICKET": "hit wicket", "OBSTRUCTION": "obstructing the field",
           "RETIREDHURT": "retired hurt", "RETIRED HURT": "retired hurt", "RETIREDOUT": "retired out",
           "RETIRED OUT": "retired out", "HANDLEDBALL": "handled the ball", "TIMEDOUT": "timed out"}


def wk_kind(b: dict) -> str | None:
    code = (b.get("wicketCode") or "").upper()
    code = code.replace("RETD_", "RETIRED").replace("_", "")   # RETD_OUT / RETD_HURT seen in 2026
    return WK_CODE.get(code) or kind_from_desc(b.get("outDesc", ""))


def text_runs(txt: str) -> int | None:
    """Runs off a ball from commentary text 'Bowler to Batter, <outcome>, ...' (used when legalRuns is null)."""
    # comma is sometimes missing: 'Natarajan to Shreyas Iyer  1 run, very full'
    m = re.match(r"^.+? to [^,]+?(?:,|\s{2,})\s*(no run|four|six|\d+ runs?)\b", txt, re.I)
    if not m:
        return None
    o = m.group(1).lower()
    return 0 if o == "no run" else 4 if o == "four" else 6 if o == "six" else int(o.split()[0])


def kind_from_desc(desc: str) -> str | None:
    d = desc.lower().strip()
    for pat, k in [(r"^c (and|&) b ", "caught and bowled"), (r"^c ", "caught"), (r"^st ", "stumped"),
                   (r"^lbw ", "lbw"), (r"^run out", "run out"), (r"^hit (wicket|wkt)", "hit wicket"),
                   (r"^b ", "bowled"), (r"retired hurt|retd hurt|retired not out", "retired hurt"),
                   (r"retired out|retired", "retired out"), (r"^obs", "obstructing the field"),
                   (r"handled", "handled the ball"), (r"timed out", "timed out")]:
        if re.search(pat, d):
            return k
    return None


def extra_type(head: str) -> str | None:
    h = head.lower().strip()
    if re.fullmatch(r"(\d+ )?wides?", h):
        return "wides"
    if h.startswith("no ball"):
        return "noballs"
    h = re.sub(r"^(\d+|one|two|three|four|five|six) ", "", h)  # "1 leg bye", "4 byes", "FOUR byes"
    if h.startswith(("leg bye", "legbye")):
        return "legbyes"
    if h.startswith("bye"):
        return "byes"
    if h.startswith("penalty"):
        return "penalty"
    return None


# ---------------------------------------------------------------- main parse
def scrape(mid: str, cs_id: str, refresh: bool = False) -> dict:
    t0 = time.time()
    raw = HERE / "samples" / "raw" / mid
    sc = json.loads(fetch(f"/api/mcenter/scorecard/{mid}", raw / "scorecard.json", refresh, True))
    squads_html = fetch(f"/cricket-match-squads/{mid}/match", raw / "match_squads.html", refresh, False)
    hdr = sc["matchHeader"]

    # ---- players (squads page)
    flight = rsc(squads_html)
    i = flight.find('{"team1":{"team":')
    if i < 0:
        raise RuntimeError("squads flight payload not found")
    sq = json.JSONDecoder().raw_decode(flight[i:])[0]
    id2name, id2team, players = {}, {}, []
    for tk in ("team1", "team2"):
        team = sq[tk]["team"]["teamName"]
        for grp, pl in sq[tk]["players"].items():
            if grp == "support staff":
                continue
            for p in pl:
                id2name[p["id"]] = p["name"]
                id2team[p["id"]] = team
                chg = p.get("inMatchChange") or ""
                status = ("impact_in" if chg == "MIN" else "impact_out" if chg == "MOUT"
                          else "xi" if grp == "playing XI" else None)
                if status:
                    players.append({"team": team, "name": p["name"], "source_id": str(p["id"]),
                                    "cricinfo_id": None, "status": status})
    listed = {p["source_id"] for p in players}

    def pname(pid, fallback=None):
        return id2name.get(pid, fallback)

    # ---- toss
    tr = hdr.get("tossResults") or {}
    dec = (tr.get("decision") or "").lower()
    toss = {"winner": tr.get("tossWinnerName"),
            "decision": "bat" if dec.startswith("bat") else "field" if dec.startswith("bowl") else dec or None}

    deliveries, notes, extra_players = [], [], {}
    cards = sorted(sc.get("scoreCard", []), key=lambda c: c["inningsId"])
    last_comm = None
    for card in cards:
        inn = card["inningsId"]
        cm = json.loads(fetch(f"/api/mcenter/{mid}/full-commentary/{inn}",
                              raw / f"full-commentary_{inn}.json", refresh, True))
        items = [c for blk in cm.get("commentary", []) for c in blk.get("commentaryList", [])
                 if c.get("inningsId", inn) == inn]
        last_comm = items
        balls = sorted([c for c in items if c.get("overNumber") is not None],
                       key=lambda c: (c.get("ballNbr", 0), c["timestamp"]))
        # stale/duplicate ball stubs: no striker id / score (seen once, superseded by a full record of the
        # same ballNbr+overNumber). Drop them; anything without a full twin is kept and will error loudly.
        full = {(c.get("ballNbr"), c["overNumber"]) for c in balls
                if "batTeamScore" in c and c.get("batsmanStriker", {}).get("batId")}
        stubs = [c for c in balls if "batTeamScore" not in c or not c.get("batsmanStriker", {}).get("batId")]
        for c in stubs:
            if (c.get("ballNbr"), c["overNumber"]) in full:
                notes.append(f"inn{inn} {c['overNumber']}: dropped stub ball record '{c.get('commText', '')[:50]}'")
        balls = [c for c in balls if c not in stubs or (c.get("ballNbr"), c["overNumber"]) not in full]
        bats = [card["batTeamDetails"]["batsmenData"][k] for k in
                sorted(card["batTeamDetails"]["batsmenData"], key=lambda k: int(k.split("_")[1]))]
        bat_by_id = {b["batId"]: b for b in bats}
        order = [b["batId"] for b in bats]
        wkts = sorted(card.get("wicketsData", {}).values(), key=lambda w: w["wktNbr"])

        # ---- assign each scorecard wicket to one commentary ball
        wk_at: dict[int, list] = {}
        used = set()
        def bold_vals(c):
            return [v for f in (c.get("commentaryFormats") or {}).values() for v in f.get("formatValue", [])]

        for w in wkts:
            # 1) WICKET ball whose bold dismissal text names this batter (robust to wickets on wides,
            #    which wicketsData files under the previous legal ball)
            cands = [k for k, c in enumerate(balls) if k not in used and "WICKET" in (c.get("event") or "")
                     and any(v.startswith(w["batName"] + " ") for v in bold_vals(c))]
            if not cands:
                cands = [k for k, c in enumerate(balls) if k not in used
                         and abs(c["overNumber"] - w["wktOver"]) < 1e-6 and c["batTeamScore"] == w["wktRuns"]]
            if not cands:
                cands = [k for k, c in enumerate(balls) if k not in used and c.get("ballNbr") == w["ballNbr"]]
            if not cands:
                notes.append(f"inn{inn}: wicket {w['wktNbr']} ({w['batName']}) not matched to a ball")
                continue
            pref = [k for k in cands if "WICKET" in (balls[k].get("event") or "")] or cands
            k = pref[0]
            used.add(k)
            wk_at.setdefault(k, []).append(w)
        # retired hurt: in batsmenData (wicketCode RETD_HURT) but absent from wicketsData. Cricsheet files it
        # as a wicket on the last ball the batter faced; do the same (heuristic: assumes he retired as striker)
        wk_ids = {w["batId"] for w in wkts}
        for b in bats:
            if wk_kind(b) == "retired hurt" and b["batId"] not in wk_ids:
                faced = [k for k, c in enumerate(balls) if c["batsmanStriker"]["batId"] == b["batId"]]
                if not faced or faced[-1] in wk_at:
                    notes.append(f"inn{inn}: retired hurt {b['batName']} not placed")
                    continue
                wk_at[faced[-1]] = [{"batId": b["batId"], "batName": b["batName"]}]
                notes.append(f"inn{inn} {balls[faced[-1]]['overNumber']}: retired hurt {b['batName']} "
                             f"placed on last ball faced")
        # WICKET events with no scorecard wicket
        for k, c in enumerate(balls):
            if "WICKET" in (c.get("event") or "") and k not in wk_at:
                notes.append(f"inn{inn} {c['overNumber']}: WICKET event without wicketsData entry")

        # ---- walk balls: runs, extras, wickets, non-striker reconstruction
        crease = [order[0], order[1]] if len(order) >= 2 else list(order)
        pending = list(order[2:])   # yet to come in, scorecard order
        retired = []                # left without a wicket (retired hurt), may return

        def next_face(pid, start):
            return next((j for j in range(start, len(balls)) if balls[j]["batsmanStriker"]["batId"] == pid),
                        10 ** 9)
        prev_score = 0
        cur_over, ball_in_over = None, 0
        for k, c in enumerate(balls):
            txt = subst(c)
            parts = [p.strip() for p in txt.split(",")]
            ext = extra_type(parts[1]) if len(parts) > 1 else None
            bat_runs = int(c.get("legalRuns") or 0)
            total = int(c.get("totalRuns") or 0)
            if c.get("legalRuns") is None and ext is None:
                # degraded record (legalRuns null, totalRuns 0, sometimes batTeamScore 0): runs from text
                tr = text_runs(txt)
                notes.append(f"inn{inn} {c['overNumber']}: legalRuns null; runs from text = {tr}")
                bat_runs = total if tr is None else tr
                total = max(total, bat_runs)
            if ext in ("byes", "legbyes") and bat_runs:
                # '1 leg bye' sometimes carried in legalRuns
                notes.append(f"inn{inn} {c['overNumber']}: {ext} carried in legalRuns={bat_runs}; moved to extras")
                total, bat_runs = max(total, bat_runs), 0
            delta = c["batTeamScore"] - prev_score
            prev_score = c["batTeamScore"] or prev_score   # degraded records carry batTeamScore 0
            if delta != total:
                notes.append(f"inn{inn} {c['overNumber']}: totalRuns={total} but score delta={delta}")
                if delta > total and ext is None:
                    ext = "penalty" if delta - total == 5 else ext
            extras = total - bat_runs
            if ext is None and extras:
                notes.append(f"inn{inn} {c['overNumber']}: extras={extras} but no extra type in text "
                             f"'{txt[:60]}'")
            striker = c["batsmanStriker"]["batId"]
            bowler = c["bowlerStriker"]["bowlId"]
            if striker not in crease:
                # someone left without a recorded wicket (retired hurt/out): drop the crease member whose
                # next appearance as striker is furthest away (or never)
                gone = max(crease, key=lambda x: next_face(x, k)) if crease else None
                crease = [x for x in crease if x != gone] + [striker]
                if gone is not None and next_face(gone, k) < 10 ** 9:
                    retired.append(gone)
                pending = [x for x in pending if x != striker]
                retired = [x for x in retired if x != striker]
                notes.append(f"inn{inn} {c['overNumber']}: {pname(striker)} on strike without a wicket; "
                             f"assumed {pname(gone)} retired")
            non = next((x for x in crease if x != striker), None)
            # wides/no-balls carry the number of the NEXT legal ball; ballNbr counts legal balls
            ov = (c["ballNbr"] - 1) // 6 if c.get("ballNbr") else int(c["overNumber"])
            if ov != cur_over:
                cur_over, ball_in_over = ov, 0
            ball_in_over += 1
            row = {"innings": inn, "super_over": False, "over": ov, "ball": ball_in_over,
                   "batter": pname(striker, c["batsmanStriker"]["batName"]),
                   "bowler": pname(bowler, c["bowlerStriker"]["bowlName"]),
                   "non_striker": pname(non) if non else None,
                   "batter_runs": bat_runs, "extras": extras, "extra_type": ext,
                   "wicket_kind": None, "player_out": None, "fielders": []}
            for w in wk_at.get(k, [])[:1]:
                b = bat_by_id.get(w["batId"], {})
                kind = wk_kind(b)
                if not kind:
                    notes.append(f"inn{inn}: unknown wicketCode {b.get('wicketCode')!r} / {b.get('outDesc')!r}")
                    kind = (b.get("wicketCode") or "unknown").lower()
                fids = [b.get(f"fielderId{j}") for j in (1, 2, 3)]
                fl = [pname(f) for f in fids if f]
                if kind in ("caught and bowled", "bowled", "lbw", "hit wicket", "retired hurt", "retired out"):
                    fl = []
                for f in fids:
                    if f and kind not in ("caught and bowled",) and str(f) not in listed and f in id2name:
                        extra_players[f] = {"team": id2team.get(f), "name": id2name[f], "source_id": str(f),
                                            "cricinfo_id": None, "status": "sub"}
                row.update(wicket_kind=kind, player_out=pname(w["batId"], w["batName"]), fielders=fl)
                if kind in ("caught", "caught and bowled") and row["batter_runs"]:
                    # 'WICKET,SIX' events with legalRuns=6 but unchanged score: no runs off a catch
                    notes.append(f"inn{inn} {c['overNumber']}: caught but legalRuns={row['batter_runs']} "
                                 f"(score delta {delta}); set batter_runs=0")
                    row["batter_runs"] = 0
            if len(wk_at.get(k, [])) > 1:
                notes.append(f"inn{inn} {c['overNumber']}: >1 wicket on one ball, kept first")
            deliveries.append(row)
            for w in wk_at.get(k, []):
                crease = [x for x in crease if x != w["batId"]]
                # a retired batter returning takes precedence if he is the next new face on strike
                nxt = next((b["batsmanStriker"]["batId"] for b in balls[k + 1:]
                            if b["batsmanStriker"]["batId"] not in crease), None)
                if nxt in retired:
                    retired.remove(nxt)
                    crease.append(nxt)
                elif pending:
                    crease.append(pending.pop(0))
        sd = card["scoreDetails"]
        mine = [d for d in deliveries if d["innings"] == inn]
        runs = sum(d["batter_runs"] + d["extras"] for d in mine)
        if runs != sd["runs"] or sum(1 for d in mine if d["wicket_kind"]) != sd["wickets"]:
            notes.append(f"inn{inn}: parsed {runs}/{sum(1 for d in mine if d['wicket_kind'])} "
                         f"vs scorecard {sd['runs']}/{sd['wickets']}")

    # ---- super over: prose only ("Ball N: Bowler to Batter, outcome") in last innings' commentary
    so_rows = parse_super_over(last_comm or [], players, id2name)
    if so_rows:
        notes.append(f"super over parsed from prose: {len(so_rows)} balls (non_striker unknown)")
    deliveries += so_rows

    players += list(extra_players.values())
    out = {"source": "cricbuzz", "source_match_id": mid, "cricsheet_id": cs_id, "toss": toss,
           "players": players, "deliveries": deliveries}
    meta = {"status": hdr.get("status"), "revisedTarget": hdr.get("revisedTarget"), "notes": notes}
    out_path = HERE / "normalized" / f"{cs_id}.json"
    out_path.parent.mkdir(exist_ok=True)
    out_path.write_text(json.dumps(out, indent=1))
    LOG.update(elapsed_s=round(time.time() - t0, 1), **meta)
    (raw / "_fetch_log.json").write_text(json.dumps(LOG, indent=1))
    return out


SO_RE = re.compile(r"^Ball (\d+):\s*(.+?) to (.+?), (.*)$", re.S)


def parse_super_over(items: list[dict], players: list[dict], id2name: dict) -> list[dict]:
    last_ball_ts = max((c["timestamp"] for c in items if c.get("overNumber") is not None), default=None)
    if last_ball_ts is None:
        return []
    prose = sorted([c for c in items if c.get("overNumber") is None and c["timestamp"] > last_ball_ts],
                   key=lambda c: c["timestamp"])
    team_of = {p["name"]: p["team"] for p in players}

    def resolve(short, team=None):
        cands = [n for n, t in team_of.items() if (team is None or t == team)
                 and (n == short or n.split()[-1] == short.split()[-1] or short in n.split())]
        return cands[0] if len(cands) == 1 else short

    rows, inn, bowl_team = [], 2, None
    for c in prose:
        m = SO_RE.match(subst(c).strip())
        if not m:
            continue
        _, bowler_s, batter_s, rest = m.groups()
        bowler = resolve(bowler_s)
        bt = team_of.get(bowler)
        if bt != bowl_team:
            inn, bowl_team, ball = inn + 1, bt, 0
        bat_team = next((t for t in set(team_of.values()) if t != bt), None)
        batter = resolve(batter_s, bat_team)
        ball += 1
        r = rest.lower()
        ext = extra_type(rest.split(",")[0])
        n = re.match(r"(\d+) runs?", r)
        bat_runs = 6 if r.startswith("six") else 4 if r.startswith("four") else int(n.group(1)) if n and not ext else 0
        extras = (int(n.group(1)) if n else 1) if ext else 0
        kind = player_out = None
        fl = []
        mo = re.match(r"out!?\s*([a-z ]+)!", r)
        if mo:
            kind = {"caught": "caught", "bowled": "bowled", "lbw": "lbw", "stumped": "stumped",
                    "run out": "run out"}.get(mo.group(1).strip(), mo.group(1).strip())
            player_out = batter
            mc = re.search(r"\b\S+ c (.+?) b ", rest)
            if kind == "caught" and mc:
                fl = [resolve(mc.group(1), bt)]
        rows.append({"innings": inn, "super_over": True, "over": 0, "ball": ball, "batter": batter,
                     "bowler": bowler, "non_striker": None, "batter_runs": bat_runs, "extras": extras,
                     "extra_type": ext, "wicket_kind": kind, "player_out": player_out, "fielders": fl})
    return rows


if __name__ == "__main__":
    a = [x for x in sys.argv[1:] if not x.startswith("--")]
    o = scrape(a[0], a[1], refresh="--refresh" in sys.argv)
    print(f"{a[0]} -> normalized/{a[1]}.json: {len(o['players'])} players, {len(o['deliveries'])} deliveries, "
          f"requests={LOG['requests']} cached={LOG['cached']} retries={LOG['retries']} "
          f"errors={len(LOG['errors'])} {LOG['elapsed_s']}s")
    for n in LOG["notes"]:
        print("  note:", n)
