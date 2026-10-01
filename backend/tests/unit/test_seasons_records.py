"""Record rankings and the cap-race accumulation on synthetic rows."""

from __future__ import annotations

import datetime as dt
from decimal import Decimal

from p11.analytics.seasons_data import BatRow, BowlRow, InningsRow, MatchRow, PartnershipRow
from p11.analytics.seasons_records import (
    balls_remaining,
    rank_bowling_figures,
    rank_fastest,
    rank_highest_totals,
    rank_individual_scores,
    rank_lowest_totals,
    rank_partnerships,
    rank_run_scorers,
    rank_wicket_takers,
    rank_wins_by_runs,
    rank_wins_by_wickets,
)
from p11.analytics.seasons_story import cumulative_race


def _m(
    mid: int,
    innings: tuple[InningsRow, ...],
    winner: int | None = 1,
    runs: int | None = None,
    wkts: int | None = None,
    result: str = "win",
) -> MatchRow:
    return MatchRow(
        id=mid, year=2026, date=dt.date(2026, 4, 1), match_number=mid, stage=None,
        venue_id=None, city=None, team1_id=1, team2_id=2, toss_winner_id=None,
        toss_decision=None, result=result, winner_id=winner, win_by_runs=runs,
        win_by_wickets=wkts, method=None, overs=20, super_over=False, innings=innings,
    )  # fmt: skip


def _i(mid: int, n: int, team: int, runs: int, balls: int, wk: int, tov: str | None = None):
    return InningsRow(mid, n, team, runs, balls, wk, 0, None, Decimal(tov) if tov else None)


def _bat(mid: int, pid: str, runs: int, balls: int, b50=None, b100=None, out=True) -> BatRow:
    return BatRow(mid, 1, pid, 1, runs, balls, 0, 0, out, b50, b100)


def test_highest_and_lowest_totals() -> None:
    m1 = _m(1, (_i(1, 1, 1, 230, 120, 3), _i(1, 2, 2, 49, 58, 10)), runs=181)
    # successful chase of a small target: 55/0 must not count as a "lowest total"
    m2 = _m(2, (_i(2, 1, 2, 52, 120, 9), _i(2, 2, 1, 55, 40, 0)), winner=1, wkts=10)
    # rain-shortened, not all out, did not bat out its quota -> not a completed innings
    m3 = _m(3, (_i(3, 1, 1, 30, 30, 1),), winner=None, result="no_result")
    pairs = [(m, i) for m in (m1, m2, m3) for i in m.innings]
    assert [i.runs for i in rank_highest_totals((i for _, i in pairs), 2)] == [230, 55]
    assert [i.runs for _, i in rank_lowest_totals(pairs, 5)] == [49, 52, 230]


def test_lowest_total_respects_revised_quota() -> None:
    # chase reduced to 10 overs: 61/5 in 10 overs is a completed innings
    m = _m(4, (_i(4, 1, 1, 100, 120, 5), _i(4, 2, 2, 61, 60, 5, "10")), runs=10)
    assert [i.runs for _, i in rank_lowest_totals([(m, i) for i in m.innings], 5)] == [61, 100]


def test_biggest_wins() -> None:
    a = _m(1, (_i(1, 1, 2, 100, 120, 1), _i(1, 2, 1, 101, 60, 0)), wkts=10)
    b = _m(2, (_i(2, 1, 2, 100, 120, 1), _i(2, 2, 1, 101, 90, 0)), wkts=10)
    c = _m(3, (), runs=146)
    assert [m.id for m in rank_wins_by_wickets([b, a, c], 5)] == [1, 2]
    assert balls_remaining(a) == 60
    assert [m.id for m in rank_wins_by_runs([a, b, c], 5)] == [3]


def test_individual_bowling_partnership_and_fastest() -> None:
    bats = [
        _bat(1, "gayle", 175, 66, 17, 30, out=False),
        _bat(2, "mccullum", 158, 73, 32, 53),
        _bat(3, "jaiswal", 98, 47, 13),
        _bat(4, "slow", 50, 50, 50),
    ]
    assert [b.player_id for b in rank_individual_scores(bats, 2)] == ["gayle", "mccullum"]
    assert [b.player_id for b in rank_fastest(bats, 50, 3)] == ["jaiswal", "gayle", "mccullum"]
    assert [b.player_id for b in rank_fastest(bats, 100, 3)] == ["gayle", "mccullum"]

    bowls = [
        BowlRow(1, 1, "joseph", 1, 22, 12, 6, 15),
        BowlRow(2, 1, "tanvir", 1, 24, 14, 6, 15),
        BowlRow(3, 1, "none", 1, 24, 10, 0, 18),
    ]
    assert [b.player_id for b in rank_bowling_figures(bowls, 5)] == ["joseph", "tanvir"]

    parts = [
        PartnershipRow(1, 1, 1, 2, "abd", "kohli", 229, 97, 129, 100),
        PartnershipRow(2, 1, 1, 1, "a", "b", 229, 110, 100, 129),
        PartnershipRow(3, 1, 1, 3, "c", "d", 50, 30, 25, 25),
    ]
    assert [p.match_id for p in rank_partnerships(parts, 2)] == [1, 2]  # fewer balls first


def test_career_leaderboards() -> None:
    bats = [_bat(1, "kohli", 100, 60), _bat(2, "kohli", 50, 40), _bat(3, "rohit", 120, 70)]
    assert [(p, sum(b.runs for b in rows)) for p, rows in rank_run_scorers(bats, 2)] == [
        ("kohli", 150),
        ("rohit", 120),
    ]
    bowls = [BowlRow(1, 1, "a", 1, 24, 30, 3, 8), BowlRow(2, 1, "b", 1, 24, 20, 3, 10)]
    assert [p for p, _ in rank_wicket_takers(bowls, 2)] == ["b", "a"]  # fewer runs wins ties


def test_cumulative_race() -> None:
    d1, d2, d3 = dt.date(2026, 4, 1), dt.date(2026, 4, 2), dt.date(2026, 4, 3)
    events = [(d1, "a", 10), (d2, "b", 50), (d3, "a", 70), (d3, "a", 5)]
    dates, series = cumulative_race(events, ["a", "b"])
    assert dates == [d1, d2, d3]
    assert series == {"a": [10, 10, 85], "b": [0, 50, 50]}
