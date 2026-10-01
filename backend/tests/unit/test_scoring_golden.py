"""End-to-end golden test: IPL 2026 Final (Cricsheet 1535465, GT v RCB, 2026-05-31).

Uses a small *test-only* Cricsheet -> Delivery adapter; production ingest lives elsewhere.
"""

from __future__ import annotations

import json
import zipfile
from collections import Counter
from pathlib import Path

import pytest

from p11.scoring import (
    CATEGORIES,
    T20_2026,
    Delivery,
    LineupEntry,
    LineupStatus,
    Role,
    fantasy_team_points,
    ruleset_for_date,
    score_match,
)

ZIP = Path(__file__).resolve().parents[3] / "spikes" / "misc" / "samples" / "ipl_json.zip"
MATCH_ID = "1535465"

ROLES: dict[str, Role] = {
    # Gujarat Titans
    "M Prasidh Krishna": Role.BOWL, "B Sai Sudharsan": Role.BAT, "Shubman Gill": Role.BAT,
    "N Sindhu": Role.AR, "JC Buttler": Role.WK, "Washington Sundar": Role.AR,
    "Arshad Khan": Role.AR, "R Tewatia": Role.AR, "JO Holder": Role.AR,
    "Rashid Khan": Role.AR, "K Rabada": Role.BOWL, "Mohammed Siraj": Role.BOWL,
    # Royal Challengers Bengaluru
    "JA Duffy": Role.BOWL, "VR Iyer": Role.AR, "V Kohli": Role.BAT, "D Padikkal": Role.BAT,
    "RM Patidar": Role.BAT, "KH Pandya": Role.AR, "TH David": Role.BAT, "JM Sharma": Role.WK,
    "R Shepherd": Role.AR, "B Kumar": Role.BOWL, "JR Hazlewood": Role.BOWL,
    "Rasikh Salam": Role.BOWL,
}


def cricsheet_to_deliveries(match: dict) -> list[Delivery]:
    out: list[Delivery] = []
    for i, inn in enumerate(match["innings"], start=1):
        for over in inn["overs"]:
            for n, d in enumerate(over["deliveries"], start=1):
                ex: dict[str, int] = d.get("extras", {})
                w = (d.get("wickets") or [None])[0]
                out.append(
                    Delivery(
                        innings=i,
                        super_over=bool(inn.get("super_over", False)),
                        over=over["over"],
                        ball=n,
                        batter=d["batter"],
                        bowler=d["bowler"],
                        non_striker=d["non_striker"],
                        batter_runs=d["runs"]["batter"],
                        extras=d["runs"]["extras"],
                        extra_type=next(iter(ex), None),
                        extras_detail=ex if len(ex) > 1 else None,
                        wicket_kind=w["kind"] if w else None,
                        player_out=w["player_out"] if w else None,
                        fielders=tuple(f["name"] for f in (w or {}).get("fielders", [])
                                       if "name" in f),
                        is_boundary=False if d["runs"].get("non_boundary") else None,
                    )
                )
    return out


def cricsheet_lineup(match: dict) -> list[LineupEntry]:
    subs_in: set[str] = set()
    for inn in match["innings"]:
        for over in inn["overs"]:
            for d in over["deliveries"]:
                for r in d.get("replacements", {}).get("match", []):
                    if r.get("reason") == "impact_player":
                        subs_in.add(r["in"])
    return [
        LineupEntry(
            p, team, ROLES[p],
            LineupStatus.SUBSTITUTE_PLAYED if p in subs_in else LineupStatus.STARTING_XI,
        )
        for team, players in match["info"]["players"].items()
        for p in players
    ]


@pytest.fixture(scope="module")
def match() -> dict:
    if not ZIP.exists():
        pytest.skip(f"sample zip not present: {ZIP}")
    with zipfile.ZipFile(ZIP) as z:
        return json.loads(z.read(f"{MATCH_ID}.json"))


@pytest.fixture(scope="module")
def scored(match):
    return score_match(cricsheet_to_deliveries(match), cricsheet_lineup(match), T20_2026)


def test_ruleset_for_match_date_is_2026(match):
    from datetime import date

    assert ruleset_for_date(date.fromisoformat(match["info"]["dates"][0])) is T20_2026


def test_every_lineup_player_scored_with_lineup_points(scored, match):
    expected = {p for ps in match["info"]["players"].values() for p in ps}
    assert set(scored.players) == expected
    assert len(expected) == 24  # 11 + impact sub per side
    for ps in scored.players.values():
        assert ps.lineup == 4, ps.player
    assert scored.players["VR Iyer"].status is LineupStatus.SUBSTITUTE_PLAYED
    assert scored.players["M Prasidh Krishna"].status is LineupStatus.SUBSTITUTE_PLAYED
    # substituted-out players keep their XI points and earlier contributions
    assert scored.players["JA Duffy"].status is LineupStatus.STARTING_XI
    assert scored.players["JA Duffy"].stats.legal_balls_bowled == 24
    assert scored.unscored_participants == frozenset()
    assert scored.warnings == ()


def test_components_sum_to_total(scored):
    for ps in scored.players.values():
        assert sum(getattr(ps, c) for c in CATEGORIES) == ps.total
        assert sum(ps.items.values()) == ps.total


def test_aggregates_match_raw_data(scored, match):
    raw = [d for inn in match["innings"] for o in inn["overs"] for d in o["deliveries"]]
    assert sum(ps.stats.runs for ps in scored.players.values()) == sum(
        d["runs"]["batter"] for d in raw
    )
    bowler_wkts = sum(
        1 for d in raw for w in d.get("wickets", []) if w["kind"] not in ("run out",)
    )
    assert sum(ps.stats.wickets for ps in scored.players.values()) == bowler_wkts
    catches = Counter(
        w["fielders"][0]["name"] for d in raw for w in d.get("wickets", [])
        if w["kind"] == "caught"
    )
    for name, n in catches.items():
        assert scored[name].stats.catches == n


def test_top_scorer_kohli_by_hand(scored):
    k = scored["V Kohli"]
    # 75* off 42 balls, 9 fours, 3 sixes (Cricsheet), role BAT
    assert (k.stats.runs, k.stats.balls_faced, k.stats.fours, k.stats.sixes) == (75, 42, 9, 3)
    assert not k.stats.dismissed
    assert k.batting == 75 * 1 + 9 * 4 + 3 * 6  # 129
    assert k.items["run_milestone"] == 12  # 75-run bonus (highest milestone only)
    assert k.items["strike_rate"] == 6  # 178.57 > 170
    assert k.bowling == 0 and k.fielding == 0
    assert k.total == 129 + 12 + 6 + 4  # 151


def test_known_fielding_and_bowling(scored):
    js = scored["JM Sharma"]  # 1 catch + 1 stumping (Buttler)
    assert (js.stats.catches, js.stats.stumpings) == (1, 1)
    assert js.fielding == 8 + 12
    assert scored["RM Patidar"].stats.catches == 2
    assert scored["RM Patidar"].items["catch_bonus"] == 0
    rabada = scored["K Rabada"]  # 3 overs, 44 runs -> econ 14.67 -> -6
    assert rabada.stats.legal_balls_bowled == 18
    assert rabada.items["economy"] == -6
    pk = scored["M Prasidh Krishna"]  # 1 over: below the 2-over economy minimum
    assert pk.stats.legal_balls_bowled == 6
    assert pk.items["economy"] == 0
    bk = scored["B Kumar"]  # 4-0-29-2 -> econ 7.25 -> no band
    assert bk.stats.wickets == 2 and bk.items["economy"] == 0


def test_captain_vice_captain(scored):
    picks = list(scored.players)[:11]
    c, vc = picks[0], picks[1]
    base = sum(scored[p].total for p in picks)
    got = fantasy_team_points(scored, picks, c, vc, T20_2026)
    assert got == pytest.approx(base + scored[c].total * 1.0 + scored[vc].total * 0.5)
