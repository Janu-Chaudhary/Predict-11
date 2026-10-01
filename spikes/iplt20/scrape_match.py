"""Scrape one IPL match from the official BCCI/IPL stack and write normalized JSON (compare.py schema).

usage: scrape_match.py <matchUUID> <cricsheet_id> [--refresh]

Sources (raw saved under samples/raw/<uuid>/):
  stats.bcci.tv/match/<uuid>/scorecard        meta, toss, 16-man team lists (full_sub.type), batting order, FoW
  stats.bcci.tv/match/<uuid>/bbb?size=500     ball-by-ball WITH player ids: batter, non-striker, bowler,
                                               runs_off_bat/wides/noballs/byes/legbyes/penalties, dismissals, fielding
  epr.ellipsedata.com/redirect/1/comp/<comp>/squads?team_id=<id>   (Edak header) Cricsheet-style short names
                                               (cached per team in samples/raw/_epr_squads/)
No browser needed. Non-striker comes straight from the bbb feed; if a row lacks it, it is reconstructed
by crease-pair tracking (scorecard batting order + dismissals), same method as cricbuzz/08.
"""
import csv
import json
import pathlib
import re
import sys
import time

from http_util import RAW, STATS, get_json

HERE = pathlib.Path(__file__).parent
OUT = HERE / "normalized"

# BCCI dismissal_name -> Cricsheet wicket kind
KIND = {
    "caught": "caught", "bowled": "bowled", "leg before wicket": "lbw", "lbw": "lbw",
    "run out": "run out", "stumped": "stumped", "hit wicket": "hit wicket",
    "caught and bowled": "caught and bowled", "handled the ball": "handled the ball",
    "obstructing the field": "obstructing the field", "obstructed the field": "obstructing the field",
    "hit the ball twice": "hit the ball twice", "timed out": "timed out",
    "retired hurt": "retired hurt", "retired not out": "retired hurt", "retired not out (hurt)": "retired hurt",
    "retired out": "retired out", "retired": "retired out",
}
MISC = HERE.parent / "misc" / "samples"
CROSSWALK = HERE / "bcci_cricsheet_crosswalk.json"  # manual BCCI player_id -> Cricsheet name (spelling diffs)
_REG = None


def registry_names():
    """All names/aliases in the public Cricsheet register (people.csv + names.csv) - NOT match-specific."""
    global _REG
    if _REG is None:
        _REG = set()
        for fn, cols in ((MISC / "people.csv", ("name", "unique_name")), (MISC / "names.csv", ("name",))):
            if fn.exists():
                for r in csv.DictReader(open(fn)):
                    _REG.update(r[c] for c in cols if r.get(c))
    return _REG


def _toks(n):
    return [t for t in re.split(r"[\s.\-']+", (n or "").lower()) if t]


def pick_name(pid, short, sc_name, known):
    """Choose the display name most likely to resolve to Cricsheet.

    1. manual crosswalk by BCCI id;  2. drop short names whose surname is absent from known_as
    (feed has corrupt short names, e.g. id 65476 'Riyan Parag' -> 'RP Das');  3. first of
    [known_as, short names] found in the public Cricsheet register;  4. else known_as, else short name."""
    cw = crosswalk().get(str(pid))
    if cw:
        return cw, "crosswalk"
    kt = set(_toks(known))
    cands = [c for c in dict.fromkeys((short, sc_name)) if c and (not kt or _toks(c)[-1:] and _toks(c)[-1] in kt)]
    reg = registry_names()
    # full known_as first: initials collide far more often in the global register
    # (e.g. 'K Sharma' = Karn Sharma, but Kartik Sharma is 'Kartik Sharma' in Cricsheet)
    for c in ([known] if known else []) + cands:
        if c in reg:
            return c, "register"
    # nothing registered: full name fuzzy-matches Cricsheet initials better than BCCI's
    # (e.g. 'LMD Madushanka' vs Cricsheet 'D Madushanka'; 'Dilshan Madushanka' matches)
    return (known, "known_as") if known else ((cands[0], "short") if cands else (None, "none"))


def crosswalk():
    return json.loads(CROSSWALK.read_text()) if CROSSWALK.exists() else {}
FIELD_ACTIONS = {"caught", "stumped", "run out", "caught and bowled",
                 "run out with throw", "run out with direct hit", "run out assist"}
STATUS = {None: "xi", "substitute": "impact_in", "replaced": "impact_out", "unused": "sub"}


def fetch(uuid, refresh=False):
    d = RAW / uuid
    sc = get_json(f"https://stats.bcci.tv/match/{uuid}/scorecard", d / "scorecard.json", refresh=refresh)
    balls, page = [], 1
    while True:
        b = get_json(f"https://stats.bcci.tv/match/{uuid}/bbb?page={page}&size=500",
                     d / f"bbb_p{page}.json", refresh=refresh)
        balls += b.get("ball") or []
        if not (b.get("page") or {}).get("next_page"):
            break
        page += 1
    squads = {}
    comp = sc["match"]["comp_id"]
    for t in sc["team"]:
        try:
            e = get_json(f"https://epr.ellipsedata.com/redirect/1/comp/{comp}/squads?team_id={t['team_id']}",
                         RAW / "_epr_squads" / f"{comp}_{t['team_id']}.json", edak=True)
            for tt in e.get("teams", []):
                for p in tt["players"]:
                    squads[str(p["player_id"])] = dict(p, team_id=tt.get("team_id"))
        except Exception as ex:  # squads are only a naming nicety; never fatal
            print("WARN epr squads:", ex, file=sys.stderr)
    return sc, balls, squads


def build(uuid, cs_id, sc, balls, squads):
    m = sc["match"]
    team_name = {t["team_id"]: t["name"] for t in sc["team"]}
    names, players = {}, []
    for t in sc["team"]:
        for p in t["player"]:
            pid = str(p["player_id"])
            short = (squads.get(pid) or {}).get("player_name")
            name, how = pick_name(pid, short, p.get("name"), p.get("known_as"))
            names[pid] = name
            st = (p.get("full_sub") or {}).get("type")
            players.append({"team": t["name"], "name": name, "name_source": how, "long_name": p.get("known_as"),
                            "epr_short_name": short, "scorecard_name": p.get("name"),
                            "source_id": pid, "cricinfo_id": None,
                            "status": STATUS.get(st, st or "xi"),
                            "sub_over": (p.get("full_sub") or {}).get("overs")})
    # names for anyone not in the 16 (e.g. substitute fielders): scorecard fielding blocks, then squads
    for inn in sc.get("innings", []):
        for b in inn.get("batting", []):
            for f in b.get("fielding") or []:
                names.setdefault(str(f["player_id"]), f.get("player_known_as"))

    def sub_lookup(short, team_id):
        """Resolve a scorecard short name (e.g. 'Rizvi') to a fielding-team player name."""
        hits = [names[str(p["player_id"])] for t in sc["team"] if str(t["team_id"]) == str(team_id)
                for p in t["player"] if short.lower() in (p.get("short_name", "").lower(),
                                                          (p.get("known_as") or "").lower())
                or _toks(p.get("known_as"))[-1:] == _toks(short)]
        if len(hits) == 1:
            return hits[0]
        # substitute fielder outside the 16-man list (e.g. 'c Manish Pandey b Narine'): full season squad
        sq = [p for p in squads.values() if str(p.get("team_id")) == str(team_id)
              and (short.lower() == (p.get("player_known_as") or "").lower()
                   or _toks(p.get("player_known_as"))[-1:] == _toks(short))]
        if len(sq) == 1:
            pid = str(sq[0]["player_id"])
            nm_, _ = pick_name(pid, sq[0].get("player_name"), None, sq[0].get("player_known_as"))
            return names.setdefault(pid, nm_)
        return None

    def nm(pid):
        pid = str(pid or "")
        if pid in ("", "0", "None"):
            return None
        if pid not in names:
            names[pid] = (squads.get(pid) or {}).get("player_name") or f"bcci:{pid}"
        return names[pid]

    balls = sorted(balls, key=lambda x: (int(x["innings_number"]), int(x["innings_ball_number"]),
                                        float(x["overs_unique"])))
    # BCCI numbers super-over innings 5,6(,7,8..); Cricsheet numbers them 3,4 -> renumber sequentially
    inn_seq = {n: i for i, n in enumerate(sorted({int(x["innings_number"]) for x in balls}), start=1)}
    # retirements where the batter came back are not dismissals in Cricsheet
    returned = {(int(i["innings_number"]), str(r["player_id"])) for i in sc.get("innings", [])
                for r in i.get("retirement") or [] if r.get("returned_overs")}
    dels = []
    for x in balls:
        bcci_inn = int(x["innings_number"])
        inn = inn_seq[bcci_inn]
        wd, nb = int(x["wides"] or 0), int(x["noballs"] or 0)
        b_, lb, pen = int(x["byes"] or 0), int(x["legbyes"] or 0), int(x["penalties"] or 0)
        etype = ("noballs" if nb else "wides" if wd else "legbyes" if lb else "byes" if b_
                 else "penalty" if pen else None)
        dis = (x.get("dismissals") or [None])[0]
        kind = out = None
        fielders = []
        if dis and KIND.get((dis.get("dismissal_name") or "").lower()) == "retired hurt" and \
                (bcci_inn, str(dis.get("out_player_id"))) in returned:
            dis = None  # retired hurt and later resumed innings
        if dis:
            raw_kind = (dis.get("dismissal_name") or x.get("dismissal_name") or "").lower()
            kind = KIND.get(raw_kind, raw_kind)
            out = nm(dis.get("out_player_id") or x.get("out_player_id"))
            dstr = dis.get("dismissal_str") or ""
            fl = [f for f in sorted(x.get("fielding") or [], key=lambda f: f.get("fielding_order", 0))
                  if f.get("fielding_action") in FIELD_ACTIONS]
            # null fielding id at position 'bowler' -> the ball's bowler (e.g. run-out assist by bowler)
            fielders = list(dict.fromkeys(
                nm(f["fielding_player_id"] or (x["bowling_player_id"] if f.get("fielding_position") == "bowler"
                                               else None))
                for f in fl if f.get("fielding_player_id") or f.get("fielding_position") == "bowler"))
            if re.match(r"c\s*&\s*b\b", dstr) or (kind == "caught" and str(x["bowling_player_id"]) in [
                    str(f["fielding_player_id"]) for f in x.get("fielding") or []
                    if f.get("fielding_action") == "caught"]):
                kind, fielders = "caught and bowled", []
            elif kind in ("caught", "stumped", "run out") and len(fielders) < len(fl) or \
                    (kind in ("caught", "stumped") and not fielders):
                # feed has a catch/run-out row with null id, or no catch row at all (only 'fielded'):
                # fall back to the official dismissal text, e.g. "c Manish Pandey b Narine",
                # "c †Buttler b Rabada", "run out (sub [Rizvi])", "run out (A/B)"
                mt = re.match(r"(?:c|st)\s+(.+?)\s+b\s", dstr) or re.match(r"run out\s*\((.+)\)", dstr)
                txt = [t for t in re.split(r"/", mt.group(1))] if mt else []
                for t in txt:
                    t = re.sub(r"[†\[\]]|\bsub\b", "", t).strip()
                    n = sub_lookup(t, x["bowling_team_id"]) if t else None
                    if n and n not in fielders:
                        fielders.append(n)
            if kind in ("bowled", "lbw", "hit wicket"):
                fielders = []
        dels.append({
            "innings": inn, "super_over": bcci_inn > 4 or (inn > 2 and int(m.get("tiebreaker_id") or 0) != 0),
            "over": int(x["over_number"]) - 1, "ball": int(x["ball_number"]),
            "batter": nm(x["batting_player_id"]), "bowler": nm(x["bowling_player_id"]),
            # feed occasionally repeats the striker as non-striker -> treat as missing, reconstruct below
            "non_striker": None if str(x.get("nonstriker_player_id")) == str(x["batting_player_id"])
            else nm(x.get("nonstriker_player_id")),
            "batter_runs": int(x["runs_off_bat"] or 0), "extras": wd + nb + b_ + lb + pen,
            "extra_type": etype, "wicket_kind": kind, "player_out": out, "fielders": fielders,
            "source_ball_id": x["ball_id"],
        })
    n_recon = reconstruct_non_striker(dels, sc, nm, inn_seq)
    n_ret = shift_retirements(dels)
    toss_w = team_name.get(m.get("toss_winner_team_id"))
    dec = (m.get("toss_decision") or "").lower()
    dec = {"bowl": "field", "field": "field", "bat": "bat"}.get(dec, dec or None)
    return {
        "source": "bcci", "source_match_id": uuid, "bcci_match_id": m.get("match_id"),
        "cricsheet_id": str(cs_id),
        "meta": {"date": m.get("start_date"), "venue": m.get("ground_name"), "title": m.get("title"),
                 "result": m.get("result_name"), "result_string": m.get("result_string"),
                 "winner": team_name.get(m.get("winner_team_id")),
                 "tiebreaker": m.get("tiebreaker_name"),
                 "dls": int(m.get("is_adjusted_target") or 0) == 1 or "DLS" in (m.get("result_string") or ""),
                 "reduced_overs": m.get("is_reduced_overs"), "non_striker_reconstructed": n_recon,
                 "retirements_shifted": n_ret},
        "toss": {"winner": toss_w, "decision": dec},
        "players": players,
        "deliveries": dels,
    }


RETIRE = {"retired hurt", "retired out", "retired not out"}


def shift_retirements(dels):
    """BCCI hangs a retirement on the NEXT ball bowled (to the incoming batter); Cricsheet records it on
    the last ball the retiring batter was involved in. Move it back one row (same innings) when that
    row has no wicket of its own. Returns #moved."""
    moved = 0
    for i, d in enumerate(dels):
        if d["wicket_kind"] in RETIRE and i and dels[i - 1]["innings"] == d["innings"] \
                and not dels[i - 1]["wicket_kind"] and d["player_out"] in (dels[i - 1]["batter"],
                                                                         dels[i - 1]["non_striker"]):
            p = dels[i - 1]
            p["wicket_kind"], p["player_out"], p["fielders"] = d["wicket_kind"], d["player_out"], []
            d["wicket_kind"], d["player_out"], d["fielders"] = None, None, []
            moved += 1
    return moved


def reconstruct_non_striker(dels, sc, nm, inn_seq):
    """Fill missing non_striker by crease-pair tracking (batting order + dismissals). Returns #filled."""
    if all(d["non_striker"] for d in dels):
        return 0
    order = {}
    for inn in sc.get("innings", []):
        bats = sorted(inn.get("batting", []), key=lambda b: int(b.get("batting_position") or 99))
        order[inn_seq.get(int(inn["innings_number"]), -1)] = [nm(b["player_id"]) for b in bats]
    filled = 0
    for inn in sorted({d["innings"] for d in dels}):
        o = order.get(inn, [])
        crease, nxt = o[:2], 2
        for d in (x for x in dels if x["innings"] == inn):
            if d["batter"] not in crease:
                crease = [c for c in crease if c != crease[-1]][:1] + [d["batter"]]
            if not d["non_striker"]:
                d["non_striker"] = next((c for c in crease if c != d["batter"]), None)
                filled += 1
            if d["player_out"]:
                crease = [c for c in crease if c != d["player_out"]]
                if nxt < len(o):
                    crease.append(o[nxt])
                    nxt += 1
    return filled


def main(uuid, cs_id, refresh=False):
    t = time.time()
    sc, balls, squads = fetch(uuid, refresh)
    doc = build(uuid, cs_id, sc, balls, squads)
    OUT.mkdir(exist_ok=True)
    p = OUT / f"{cs_id}.json"
    p.write_text(json.dumps(doc, indent=1))
    print(f"{cs_id} {uuid}: {len(doc['players'])} players, {len(doc['deliveries'])} deliveries, "
          f"result={doc['meta']['result']!r} -> {p}  [{time.time()-t:.1f}s, http={STATS}]")


if __name__ == "__main__":
    a = [x for x in sys.argv[1:] if not x.startswith("--")]
    main(a[0], a[1], refresh="--refresh" in sys.argv)
