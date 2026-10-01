"""Venue card maths on a synthetic Reference (no DB)."""

from __future__ import annotations

import datetime as dt

import pytest

from p11.analytics.players_data import InningsTotal, MatchInfo, Reference
from p11.analytics.venues import (
    _innings_by_match,
    par_stats,
    phase_rates,
    toss_stats,
    weighted_par,
)

A, B = 1, 2


def _match(mid: int, season: int, winner: int | None, toss: int, decision: str, **kw: object):
    base: dict[str, object] = {
        "id": mid,
        "date": dt.date(season, 4, mid),
        "season": season,
        "venue_id": 9,
        "team1_id": A,
        "team2_id": B,
        "toss_winner_id": toss,
        "toss_decision": decision,
        "result": "win" if winner else "no_result",
        "winner_id": winner,
        "method": None,
        "stage": None,
    }
    base.update(kw)
    return MatchInfo(**base)  # type: ignore[arg-type]


def _inn(mid: int, inn: int, team: int, runs: int, pp: tuple[int, int] = (0, 0)) -> InningsTotal:
    t = InningsTotal(mid, inn, team, runs=runs, wickets=5, legal_balls=120)
    t.phase_runs["powerplay"], t.phase_balls["powerplay"] = pp
    t.phase_wickets["powerplay"] = 1
    return t


def _ref() -> Reference:
    matches = [
        _match(1, 2022, A, A, "bat"),  # A bats first and wins
        _match(2, 2024, B, B, "field"),  # B chases and wins
        _match(3, 2026, B, A, "field"),  # A fields first, B (batting first) wins
        _match(4, 2026, B, B, "field", method="D/L"),  # DLS: excluded from par/chase
        _match(5, 2026, None, A, "field"),  # no result: excluded from toss win %
    ]
    inns = [
        _inn(1, 1, A, 160, (50, 36)),
        _inn(1, 2, B, 150, (40, 36)),
        _inn(2, 1, A, 200, (60, 36)),
        _inn(2, 2, B, 201, (70, 36)),
        _inn(3, 1, B, 220, (66, 36)),
        _inn(3, 2, A, 180, (48, 36)),
        _inn(4, 1, A, 120),
        _inn(4, 2, B, 100),
    ]
    return Reference(
        matches={m.id: m for m in matches},
        order={m.id: i for i, m in enumerate(matches)},
        batting_team={(t.match_id, t.innings): t.team_id for t in inns},
        innings=inns,
        teams={A: "A", B: "B"},
        venues={9: ("Ground", "City")},
        appearances={},
    )


def test_par_and_chase_use_completed_non_dls_wins() -> None:
    ref = _ref()
    inns = _innings_by_match(ref)
    p = par_stats(ref, list(ref.matches), inns)
    assert p.matches == 3
    assert p.avg_first_innings == pytest.approx((160 + 200 + 220) / 3, abs=0.1)
    assert p.median_first_innings == 200
    assert p.avg_second_innings == pytest.approx((150 + 201 + 180) / 3, abs=0.1)
    assert p.chase_win_pct == pytest.approx(33.3)
    assert p.bat_first_win_pct == pytest.approx(66.7)


def test_weighted_par_favours_recent_seasons() -> None:
    ref = _ref()
    inns = _innings_by_match(ref)
    w = weighted_par(ref, list(ref.matches), inns)
    # weights 0.25 (2022), 0.5 (2024), 1 (2026)
    assert w == pytest.approx((0.25 * 160 + 0.5 * 200 + 220) / 1.75, abs=0.1)


def test_toss_stats() -> None:
    ref = _ref()
    t = toss_stats(ref, list(ref.matches))
    assert (t.matches, t.chose_field, t.chose_bat) == (5, 4, 1)
    # decided: m1 (toss A won), m2 (B won), m3 (A lost), m4 (B won); m5 no result
    assert t.toss_winner_win_pct == 75.0
    assert t.toss_winner_win_pct_when_bat == 100.0
    assert t.toss_winner_win_pct_when_field == pytest.approx(66.7)


def test_phase_rates_are_runs_per_six_legal_balls() -> None:
    ref = _ref()
    inns = _innings_by_match(ref)
    pr = {p.phase: p for p in phase_rates([1, 2], inns)}
    assert pr["powerplay"].run_rate == pytest.approx((50 + 40 + 60 + 70) / 144 * 6, abs=0.01)
    assert pr["powerplay"].wickets_per_innings == 1.0
    assert pr["middle"].run_rate is None
