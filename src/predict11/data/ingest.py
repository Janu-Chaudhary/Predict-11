"""Cricsheet YAML -> normalized DuckDB tables.

Why YAML, not the bundled Dataset.csv: the CSV is unquoted and several venue
names contain commas ("... Stadium, Mohali, Chandigarh"), which silently shifts
columns. The YAML is structured, so parsing is unambiguous and also gives us the
per-match playing XI (which the CSV lacks).

Tables produced:
  matches(match_id, date, season, venue, city, team1, team2, toss_winner,
          toss_decision, winner, player_of_match)
  playing_xi(match_id, team, player)        -- who actually played
  deliveries(match_id, date, season, innings, batting_team, bowling_team,
             over, ball, batter, bowler, non_striker, batsman_runs, extras,
             total_runs, extra_kind, wicket_kind, player_out, fielders)
"""
from __future__ import annotations

import glob
from pathlib import Path

import duckdb
import pandas as pd
import yaml

from ..config import CRICSHEET_DIR, DUCKDB_PATH

# libyaml C loader is ~10-20x faster than the pure-Python parser; fall back if absent.
_Loader = getattr(yaml, "CSafeLoader", yaml.SafeLoader)


def _season(date: str) -> int:
    return int(str(date)[:4])


def _wicket_records(d: dict) -> list[dict]:
    """A delivery may carry 0..n wickets (old format: single 'wicket' dict)."""
    w = d.get("wicket")
    if not w:
        return []
    if isinstance(w, list):
        return w
    return [w]


def _parse_one(path: str) -> tuple[dict, list[dict], list[dict]]:
    with open(path) as fh:
        doc = yaml.load(fh, Loader=_Loader)
    info = doc["info"]
    match_id = Path(path).stem
    date = str(info["dates"][0])
    teams = info.get("teams", [])
    match = {
        "match_id": match_id,
        "date": date,
        "season": _season(date),
        "venue": info.get("venue"),
        "city": info.get("city"),
        "team1": teams[0] if len(teams) > 0 else None,
        "team2": teams[1] if len(teams) > 1 else None,
        "toss_winner": (info.get("toss") or {}).get("winner"),
        "toss_decision": (info.get("toss") or {}).get("decision"),
        "winner": (info.get("outcome") or {}).get("winner"),
        "player_of_match": (info.get("player_of_match") or [None])[0],
    }

    xi: list[dict] = []
    for team, players in (info.get("players") or {}).items():
        for p in players:
            xi.append({"match_id": match_id, "team": team, "player": p})

    deliveries: list[dict] = []
    for inning_idx, inning_block in enumerate(doc.get("innings", []), start=1):
        # each block is {"Nth innings": {team, deliveries: [...]}}
        (_, inn), = inning_block.items()
        batting_team = inn.get("team")
        bowling_team = next((t for t in teams if t != batting_team), None)
        for ball_block in inn.get("deliveries", []):
            (ob, d), = ball_block.items()
            over, ball = str(ob).split(".")
            runs = d.get("runs", {})
            extras = d.get("extras", {})
            extra_kind = next(iter(extras), None) if extras else None
            wrecs = _wicket_records(d)
            base = {
                "match_id": match_id,
                "date": date,
                "season": match["season"],
                "innings": inning_idx,
                "batting_team": batting_team,
                "bowling_team": bowling_team,
                "over": int(over),
                "ball": int(ball),
                "batter": d.get("batsman") or d.get("batter"),
                "bowler": d.get("bowler"),
                "non_striker": d.get("non_striker"),
                "batsman_runs": int(runs.get("batsman", 0)),
                "extras": int(runs.get("extras", 0)),
                "total_runs": int(runs.get("total", 0)),
                "extra_kind": extra_kind,
            }
            if not wrecs:
                deliveries.append(
                    {**base, "wicket_kind": None, "player_out": None, "fielders": None}
                )
            else:
                for w in wrecs:
                    fielders = w.get("fielders") or []
                    deliveries.append(
                        {
                            **base,
                            "wicket_kind": w.get("kind"),
                            "player_out": w.get("player_out"),
                            "fielders": "|".join(fielders) if fielders else None,
                        }
                    )
    return match, xi, deliveries


def ingest(cricsheet_dir: Path = CRICSHEET_DIR, db_path: Path = DUCKDB_PATH) -> dict:
    files = sorted(glob.glob(str(cricsheet_dir / "*.yaml")))
    if not files:
        raise FileNotFoundError(f"No YAML files under {cricsheet_dir}")

    matches, xis, dels = [], [], []
    bad = 0
    for f in files:
        try:
            m, x, d = _parse_one(f)
            matches.append(m)
            xis.extend(x)
            dels.extend(d)
        except Exception as e:  # noqa: BLE001 -- record & skip a malformed file
            bad += 1
            print(f"  ! skipped {Path(f).name}: {e}")

    m_df = pd.DataFrame(matches)
    x_df = pd.DataFrame(xis)
    d_df = pd.DataFrame(dels)

    db_path.parent.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(db_path))
    con.register("m_df", m_df)
    con.register("x_df", x_df)
    con.register("d_df", d_df)
    con.execute("CREATE OR REPLACE TABLE matches AS SELECT * FROM m_df")
    con.execute("CREATE OR REPLACE TABLE playing_xi AS SELECT * FROM x_df")
    con.execute("CREATE OR REPLACE TABLE deliveries AS SELECT * FROM d_df")
    con.close()

    return {
        "files": len(files),
        "skipped": bad,
        "matches": len(m_df),
        "deliveries": len(d_df),
        "xi_rows": len(x_df),
        "db": str(db_path),
    }


if __name__ == "__main__":
    print(ingest())
