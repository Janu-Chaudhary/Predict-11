"""NRR maths (all-out rule, DLS revised overs) and points-table rules on synthetic matches."""

from __future__ import annotations

import datetime as dt
from decimal import Decimal

import pytest

from p11.analytics.seasons_data import InningsRow, MatchRow
from p11.analytics.seasons_nrr import (
    InningsFigures,
    NrrAccumulator,
    balls_to_overs,
    overs_to_balls,
    regulation_figures,
)
from p11.analytics.seasons_table import compute_standings, match_figures
from p11.analytics.seasons_teams import era_for, short_code

A, B, C = 1, 2, 3
_ids = iter(range(1, 10_000))


def inn(
    n: int,
    team: int,
    runs: int,
    balls: int,
    wkts: int = 5,
    target_runs: int | None = None,
    target_overs: str | None = None,
) -> InningsRow:
    return InningsRow(
        0, n, team, runs, balls, wkts, 0, target_runs,
        Decimal(target_overs) if target_overs else None,
    )  # fmt: skip


def match(
    t1: int,
    t2: int,
    winner: int | None,
    innings: tuple[InningsRow, ...] = (),
    result: str = "win",
    day: int = 1,
) -> MatchRow:
    return MatchRow(
        id=next(_ids), year=2026, date=dt.date(2026, 4, day), match_number=day, stage=None,
        venue_id=None, city=None, team1_id=t1, team2_id=t2, toss_winner_id=None,
        toss_decision=None, result=result, winner_id=winner, win_by_runs=None,
        win_by_wickets=None, method=None, overs=20, super_over=result == "tie", innings=innings,
    )  # fmt: skip


# --------------------------------------------------------------------------- overs notation
@pytest.mark.parametrize(
    ("overs", "balls"), [("20", 120), ("19.4", 118), ("9.2", 56), (Decimal("11.0"), 66)]
)
def test_overs_to_balls(overs: str, balls: int) -> None:
    assert overs_to_balls(overs) == balls


def test_overs_to_balls_rejects_bad_notation() -> None:
    with pytest.raises(ValueError):
        overs_to_balls("10.7")


def test_balls_to_overs() -> None:
    assert balls_to_overs(118) == "19.4"
    assert balls_to_overs(120) == "20"


# --------------------------------------------------------------------------- NRR rules
def test_all_out_is_charged_full_quota() -> None:
    bowled_out = InningsFigures(runs=100, legal_balls=90, wickets=10, quota_balls=120)
    assert bowled_out.all_out
    assert bowled_out.nrr_balls == 120
    not_out = InningsFigures(runs=100, legal_balls=90, wickets=9, quota_balls=120)
    assert not_out.nrr_balls == 90


def test_absent_hurt_completes_all_out() -> None:
    f = InningsFigures(runs=80, legal_balls=70, wickets=9, quota_balls=120, absent_hurt=1)
    assert f.all_out and f.nrr_balls == 120


def test_nrr_simple_full_match() -> None:
    # A 180/5 (20) beat B 150/10 (17.0) -> A: 9.0 - 7.5 = +1.5 ; B: -1.5
    f1, f2 = regulation_figures((180, 120, 5, 0), (150, 102, 10, 0), 20, None, None)
    assert f1 is not None and f2 is not None
    a, b = NrrAccumulator(), NrrAccumulator()
    a.add_batting(f1)
    b.add_bowling(f1)
    b.add_batting(f2)
    a.add_bowling(f2)
    assert a.nrr == pytest.approx(1.5)
    assert b.nrr == pytest.approx(-1.5)


def test_dls_first_innings_credited_target_minus_one_off_revised_overs() -> None:
    # Official 2026 match 50 shape: LSG 209/3 (19), RCB 203/6 (19), DLS target 213 in 19.
    f1, f2 = regulation_figures((209, 114, 3, 0), (203, 114, 6, 0), 20, 213, Decimal("19"))
    assert f1 == InningsFigures(212, 114, 0, 114)
    assert f2 is not None and f2.quota_balls == 114


def test_reduced_chase_all_out_uses_revised_quota() -> None:
    # chase reduced to 9.2 overs, bowled out in 8 overs -> charged 9.2 overs (56 balls)
    _, f2 = regulation_figures((150, 120, 4, 0), (60, 48, 10, 0), 20, 90, Decimal("9.2"))
    assert f2 is not None and f2.nrr_balls == 56


def test_full_length_target_overs_is_not_a_reduction() -> None:
    f1, f2 = regulation_figures((150, 120, 4, 0), (151, 100, 2, 0), 20, 151, Decimal("20"))
    assert f1 == InningsFigures(150, 120, 4, 120, 0)
    assert f2 is not None and f2.quota_balls == 120


def test_match_figures_on_reduced_match() -> None:
    m = match(A, B, A, (inn(1, A, 150, 66, 3), inn(2, B, 123, 66, 9, 151, "11")))
    figs = dict(match_figures(m))
    assert figs[A].runs == 150 and figs[A].nrr_balls == 66
    assert figs[B].nrr_balls == 66


# --------------------------------------------------------------------------- table rules
def test_points_nr_tie_and_form() -> None:
    ms = [
        match(A, B, A, (inn(1, A, 180, 120), inn(2, B, 150, 120)), day=1),
        match(B, C, None, (inn(1, B, 40, 30),), result="no_result", day=2),
        # tie settled by super over -> win for C, tied counted for both
        match(A, C, C, (inn(1, A, 160, 120), inn(2, C, 160, 120)), result="tie", day=3),
    ]
    rows = {s.team_id: s for s in compute_standings(ms)}
    assert (rows[A].played, rows[A].won, rows[A].lost, rows[A].points) == (2, 1, 1, 2)
    assert (rows[B].no_result, rows[B].points, rows[B].results) == (1, 1, ["L", "N"])
    assert (rows[C].won, rows[C].tied, rows[C].points) == (1, 1, 3)
    # no-result innings never enter NRR
    assert rows[B].nrr.runs_for == 150
    assert rows[C].nrr.runs_for == 160


def test_ranking_points_then_wins_then_nrr() -> None:
    # A: 1 win + 1 NR = 3 pts ; B: 1 win + 1 NR = 3 pts; C: 0 ; D (4): 1 win 1 loss = 2
    big, small = (inn(1, A, 250, 120), inn(2, C, 100, 120)), (inn(1, B, 151, 120),)
    ms = [
        match(A, C, A, big, day=1),
        match(B, 4, B, small + (inn(2, 4, 150, 120),), day=2),
        match(A, 4, None, (), result="no_result", day=3),
        match(B, C, None, (), result="no_result", day=4),
    ]
    order = [s.team_id for s in compute_standings(ms)]
    assert order[:2] == [A, B]  # level on points and wins; A's NRR is far better
    assert [s.position for s in compute_standings(ms)] == [1, 2, 3, 4]


def test_wins_break_points_ties_before_nrr() -> None:
    x, y, z, w = 1, 2, 3, 4
    ms = [
        match(x, z, x, (inn(1, x, 101, 120), inn(2, z, 100, 120)), day=1),
        match(x, z, x, (inn(1, x, 101, 120), inn(2, z, 100, 120)), day=2),
        match(y, z, y, (inn(1, y, 250, 120), inn(2, z, 80, 120)), day=3),
        match(y, w, None, (), result="no_result", day=4),
        match(y, w, None, (), result="no_result", day=5),
    ]
    rows = compute_standings(ms)
    by = {s.team_id: s for s in rows}
    assert (by[x].points, by[x].won) == (4, 2)
    assert (by[y].points, by[y].won) == (4, 1)
    assert by[y].nrr.nrr > by[x].nrr.nrr
    assert [s.team_id for s in rows][:2] == [x, y]  # more wins beats better NRR


def test_team_eras() -> None:
    assert era_for("Sunrisers Hyderabad", 2009).short_code == "DCH"
    assert era_for("Sunrisers Hyderabad", 2013).name == "Sunrisers Hyderabad"
    assert era_for("Delhi Capitals", 2018).name == "Delhi Daredevils"
    assert era_for("Punjab Kings", 2020).short_code == "KXIP"
    assert era_for("Royal Challengers Bengaluru", 2023).name == "Royal Challengers Bangalore"
    assert short_code("Pune Warriors") == "PWI"
    assert short_code("Some New Franchise") == "SNF"
