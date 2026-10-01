"""Shared validator: score a source's normalized match JSON against Cricsheet (ground truth).

Normalized match JSON (one file per match, written by each source's scraper):
{
  "source": "cricbuzz|espn|bcci", "source_match_id": "...", "cricsheet_id": "1535465",
  "toss": {"winner": "Gujarat Titans", "decision": "bat|field"},
  "players": [{"team": "...", "name": "...", "source_id": "...", "cricinfo_id": "..."|null,
               "status": "xi|impact_in|impact_out|sub"}],
  "deliveries": [{"innings": 1, "super_over": false, "over": 0, "ball": 1,
                  "batter": "...", "bowler": "...", "non_striker": "..."|null,
                  "batter_runs": 0, "extras": 0,
                  "extra_type": "wides|noballs|legbyes|byes|penalty"|null,
                  "wicket_kind": "caught|bowled|lbw|run out|stumped|..."|null,
                  "player_out": "..."|null, "fielders": ["..."]}]
}
Deliveries must be in bowling order and include wides/no-balls as separate rows.

Usage: compare.py <normalized.json> [...]   -> prints a per-match report + a summary line
"""
from __future__ import annotations

import csv
import json
import re
import sys
import zipfile
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).parent
MISC = HERE.parent / "misc" / "samples"
ZIP = MISC / "ipl_json.zip"
PEOPLE = MISC / "people.csv"
NAMES = MISC / "names.csv"
OVERRIDES = {k: v for k, v in json.loads((HERE / "overrides.json").read_text()).items()
             if not k.startswith("_")} if (HERE / "overrides.json").exists() else {}

_people = None


def people():
    """identifier -> row, plus cricinfo key -> identifier, plus identifier -> alias names."""
    global _people
    if _people is None:
        by_id, by_ci, aliases = {}, {}, defaultdict(set)
        with open(PEOPLE) as fh:
            for r in csv.DictReader(fh):
                by_id[r["identifier"]] = r
                for k in ("key_cricinfo", "key_cricinfo_2", "key_cricinfo_3"):
                    if r.get(k):
                        by_ci[r[k].split(".")[0]] = r["identifier"]
                aliases[r["identifier"]].update({r["name"], r["unique_name"]})
        if NAMES.exists():
            with open(NAMES) as fh:
                for r in csv.DictReader(fh):
                    aliases[r["identifier"]].add(r["name"])
        _people = (by_id, by_ci, aliases)
    return _people


def cricsheet(cs_id: str) -> dict:
    with zipfile.ZipFile(ZIP) as z:
        return json.loads(z.read(f"{cs_id}.json"))


def _tokens(name: str) -> list[str]:
    return [t for t in re.split(r"[\s.\-']+", name.lower().replace("(sub)", "")) if t]


def name_compatible(full: str, cs: str) -> bool:
    """'Rohit Gurunath Sharma' ~ 'RG Sharma'; 'Virat Kohli' ~ 'V Kohli'; 'Sai Sudharsan' ~ 'B Sai Sudharsan'.

    Rule: same surname, and the source's given names are consistent with Cricsheet's
    initials/given tokens (first letter of the first given name appears among them).
    """
    a, b = _tokens(full), _tokens(cs)
    if not a or not b or a[-1] != b[-1]:
        return False
    if len(a) == 1 or len(b) == 1:
        return True
    cs_letters = "".join(t if (len(t) <= 3 and t.isalpha() and t == t.lower() and len(t) < 4
                              and not any(t == g for g in a[:-1])) else t[0] for t in b[:-1])
    src_letters = "".join(t[0] for t in a[:-1])
    given_overlap = set(a[:-1]) & set(b[:-1])
    return bool(given_overlap) or src_letters[0] in cs_letters or cs_letters[0] in src_letters


class Resolver:
    """Map a source name -> Cricsheet name, constrained to the 22-24 people in this match."""

    def __init__(self, cs_doc: dict, src_players: list[dict]):
        self.reg = cs_doc["info"]["registry"]["people"]  # cs name -> identifier
        self.id2cs = {v: k for k, v in self.reg.items()}
        by_id, by_ci, aliases = people()
        self.map: dict[str, str | None] = {}
        self.method = Counter()
        for p in src_players:
            n = p["name"]
            if n in self.map:
                continue
            ci = str(p.get("cricinfo_id") or "").split(".")[0]
            if ci and by_ci.get(ci) in self.id2cs:
                self.map[n] = self.id2cs[by_ci[ci]]
                self.method["cricinfo_id"] += 1
                continue
            if OVERRIDES.get(n) in self.reg:
                self.map[n] = OVERRIDES[n]
                self.method["override"] += 1
                continue
            if n in self.reg:
                self.map[n] = n
                self.method["exact"] += 1
                continue
            alias_hits = [cs for cs, pid in self.reg.items() if n in aliases.get(pid, ())]
            if len(alias_hits) == 1:
                self.map[n] = alias_hits[0]
                self.method["alias"] += 1
                continue
            cands = [cs for cs in self.reg if name_compatible(n, cs)]
            if len(cands) == 1:
                self.map[n] = cands[0]
                self.method["fuzzy"] += 1
            else:
                self.map[n] = None
                self.method["unresolved" if not cands else "ambiguous"] += 1

    def __call__(self, name):
        if name is None:
            return None
        if name not in self.map and OVERRIDES.get(name) in self.reg:
            self.map[name] = OVERRIDES[name]
        if name not in self.map:  # name seen only in deliveries
            cands = [cs for cs in self.reg if name_compatible(name, cs)]
            self.map[name] = cands[0] if len(cands) == 1 else None
            self.method["fuzzy_late" if len(cands) == 1 else "unresolved_late"] += 1
        return self.map[name]


def cs_deliveries(doc):
    out = []
    for i, inn in enumerate(doc["innings"], start=1):
        so = bool(inn.get("super_over"))
        for ov in inn["overs"]:
            for d in ov["deliveries"]:
                ex = d.get("extras") or {}
                w = (d.get("wickets") or [None])[0]
                out.append({
                    "innings": i, "super_over": so, "batter": d["batter"], "bowler": d["bowler"],
                    "non_striker": d["non_striker"], "batter_runs": d["runs"]["batter"],
                    "extras": d["runs"]["extras"], "extra_type": next(iter(ex), None),
                    "wicket_kind": w["kind"] if w else None, "player_out": w["player_out"] if w else None,
                    "fielders": [f.get("name") for f in (w or {}).get("fielders", []) if f.get("name")],
                })
    return out


BOWLER_WICKETS = {"caught", "bowled", "lbw", "stumped", "caught and bowled", "hit wicket"}


def _team_key(name: str) -> str:
    return " ".join(_tokens(name or ""))


def player_stats(dels, R=lambda x: x):
    s = defaultdict(Counter)
    for d in dels:
        if d.get("super_over"):
            continue
        b, bw = R(d["batter"]), R(d["bowler"])
        s[b]["runs"] += d["batter_runs"]
        if d.get("extra_type") != "wides":
            s[b]["balls"] += 1
        if d.get("wicket_kind") in BOWLER_WICKETS:
            s[bw]["wkts"] += 1
        if d.get("wicket_kind") in ("caught",):
            for f in d.get("fielders") or []:
                s[R(f)]["catches"] += 1
    return s


def innings_totals(dels):
    t = defaultdict(Counter)
    for d in dels:
        k = (d["innings"], bool(d.get("super_over")))
        t[k]["runs"] += d["batter_runs"] + d["extras"]
        t[k]["wkts"] += 1 if d.get("wicket_kind") else 0
        t[k]["legal"] += 0 if d.get("extra_type") in ("wides", "noballs") else 1
        t[k]["rows"] += 1
    return t


def compare(path: Path) -> dict:
    src = json.loads(path.read_text())
    doc = cricsheet(src["cricsheet_id"])
    R = Resolver(doc, src.get("players", []))
    rep = {"file": path.name, "source": src["source"], "cs": src["cricsheet_id"], "issues": []}

    # toss
    ct = doc["info"].get("toss", {})
    st = src.get("toss") or {}
    rep["toss_ok"] = (st.get("decision") == ct.get("decision")
                      and _team_key(st.get("winner")) == _team_key(ct.get("winner")))
    if not rep["toss_ok"]:
        rep["issues"].append(f"toss src={st} cs={ct}")

    # XI (12 per team incl. impact player in Cricsheet)
    cs_xi = {n for team in doc["info"]["players"].values() for n in team}
    src_xi = {R(p["name"]) for p in src.get("players", [])
              if p.get("status") in ("xi", "impact_in", "impact_out")}
    rep["xi_missing"] = sorted(cs_xi - src_xi)
    rep["xi_extra"] = sorted(x for x in src_xi - cs_xi if x)
    rep["xi_ok"] = not rep["xi_missing"] and not rep["xi_extra"]

    # identity resolution
    rep["resolve"] = dict(R.method)

    # innings totals
    cd, sd = cs_deliveries(doc), src.get("deliveries", [])
    ct_, st_ = innings_totals(cd), innings_totals(sd)
    rep["innings"] = []
    for k in sorted(set(ct_) | set(st_)):
        a, b = ct_.get(k, Counter()), st_.get(k, Counter())
        ok = all(a[m] == b[m] for m in ("runs", "wkts", "legal", "rows"))
        rep["innings"].append({"inn": k[0], "super_over": k[1], "ok": ok,
                               "cs": dict(a), "src": dict(b)})
    rep["innings_ok"] = all(i["ok"] for i in rep["innings"] if not i["super_over"])

    # per-player stats
    cps, sps = player_stats(cd), player_stats(sd, R)
    mism = []
    for p in set(cps) | {k for k in sps if k}:
        for m in ("runs", "balls", "wkts", "catches"):
            if cps[p][m] != sps[p][m]:
                mism.append(f"{p}.{m} cs={cps[p][m]} src={sps[p][m]}")
    rep["player_mismatches"] = sorted(mism)

    # ball-level (only if same row count per innings)
    ball_bad = Counter()
    for inn in {d["innings"] for d in cd}:
        a = [d for d in cd if d["innings"] == inn]
        b = [d for d in sd if d["innings"] == inn]
        if len(a) != len(b):
            ball_bad["row_count_diff"] += 1
            continue
        for x, y in zip(a, b):
            for f in ("batter", "bowler", "non_striker", "player_out"):
                yv = R(y.get(f)) if y.get(f) is not None else None
                if f == "non_striker" and y.get(f) is None:
                    ball_bad["non_striker_absent"] += 1
                elif yv != x[f]:
                    ball_bad[f] += 1
            if (x["extra_type"] or None) != (y.get("extra_type") or None):
                ball_bad["extra_type"] += 1
            if (x["wicket_kind"] or None) != (y.get("wicket_kind") or None):
                ball_bad["wicket_kind"] += 1
            if x["batter_runs"] != y.get("batter_runs"):
                ball_bad["batter_runs"] += 1
            if x["extras"] != y.get("extras"):
                ball_bad["extras"] += 1
            if set(x["fielders"]) != {R(f) for f in (y.get("fielders") or [])}:
                ball_bad["fielders"] += 1
    rep["ball_mismatches"] = dict(ball_bad)
    return rep


def main(paths):
    reps = [compare(Path(p)) for p in paths]
    for r in reps:
        print(json.dumps(r, indent=1, default=str))
    n = len(reps)
    print(f"\nSUMMARY {n} matches | toss_ok={sum(r['toss_ok'] for r in reps)} "
          f"xi_ok={sum(r['xi_ok'] for r in reps)} innings_ok={sum(r['innings_ok'] for r in reps)} "
          f"player_mismatch_matches={sum(bool(r['player_mismatches']) for r in reps)}")


if __name__ == "__main__":
    main(sys.argv[1:])
