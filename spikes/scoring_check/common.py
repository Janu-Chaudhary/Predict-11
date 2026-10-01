"""Shared helpers: load a Cricsheet IPL match and score it with p11.scoring."""
from __future__ import annotations

import json
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend" / "tests" / "unit"))
ZIP = ROOT / "spikes" / "misc" / "samples" / "ipl_json.zip"

from test_scoring_golden import cricsheet_to_deliveries  # noqa: E402

from p11.scoring import LineupEntry, LineupStatus, Role, score_match  # noqa: E402

_z = zipfile.ZipFile(ZIP)


def load(mid: str | int) -> dict:
    return json.loads(_z.read(f"{mid}.json"))


def lineup(match: dict, roles: dict[str, Role], default: Role = Role.AR):
    subs_in = set()
    for inn in match["innings"]:
        for o in inn["overs"]:
            for d in o["deliveries"]:
                for r in d.get("replacements", {}).get("match", []):
                    if r.get("reason") == "impact_player":
                        subs_in.add(r["in"])
    return [
        LineupEntry(p, t, roles.get(p, default),
                    LineupStatus.SUBSTITUTE_PLAYED if p in subs_in else LineupStatus.STARTING_XI)
        for t, ps in match["info"]["players"].items() for p in ps
    ]


def score(mid, roles=None, rules=None, default=Role.AR):
    from p11.scoring import T20_2026, ruleset_for_date
    from datetime import date
    m = load(mid)
    rules = rules or ruleset_for_date(date.fromisoformat(m["info"]["dates"][0]))
    return m, score_match(cricsheet_to_deliveries(m), lineup(m, roles or {}, default), rules)
