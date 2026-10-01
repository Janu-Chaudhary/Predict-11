"""Scenario enumeration on tiny synthetic leagues, checked against hand enumeration."""

from __future__ import annotations

import itertools

import pytest

from p11.analytics.seasons_scenarios import Fixture, simulate


def _brute(points: dict[int, int], fixtures: list[tuple[int, int]], slots: int) -> dict[int, float]:
    """P(clear top-`slots` on points) by explicit enumeration (no wins tiebreak needed when
    every team has the same NR count, i.e. wins = points / 2)."""
    hits = dict.fromkeys(points, 0)
    outcomes = list(itertools.product((0, 1), repeat=len(fixtures)))
    for o in outcomes:
        pts = dict(points)
        for (a, b), bit in zip(fixtures, o, strict=True):
            pts[b if bit else a] += 2
        for t in pts:
            if sum(1 for u in pts if u != t and pts[u] >= pts[t]) < slots:
                hits[t] += 1
    return {t: h / len(outcomes) for t, h in hits.items()}


def test_exhaustive_matches_brute_force_six_team_league() -> None:
    points = {1: 8, 2: 6, 3: 6, 4: 4, 5: 2, 6: 0}
    fx = [(1, 2), (3, 4), (5, 6), (1, 3), (2, 4), (5, 1), (6, 3), (4, 5)]
    res = simulate(points, {t: p // 2 for t, p in points.items()}, [Fixture(a, b) for a, b in fx])
    assert res.method == "exhaustive" and res.outcomes == 2 ** len(fx) and res.exact
    want4, want2 = _brute(points, fx, 4), _brute(points, fx, 2)
    got = {o.team_id: o for o in res.teams}
    for t in points:
        assert got[t].p_top4 == pytest.approx(want4[t])
        assert got[t].p_top2 == pytest.approx(want2[t])
        assert got[t].p_top4_incl_ties >= got[t].p_top4


def test_clinched_and_eliminated_four_teams_one_slot_each_side() -> None:
    # 5 teams, top 4 qualify. Team 5 can reach at most 2 points, team 4 already has 6.
    points = {1: 10, 2: 8, 3: 8, 4: 6, 5: 0}
    fx = [Fixture(5, 1)]
    res = {o.team_id: o for o in simulate(points, {t: p // 2 for t, p in points.items()}, fx).teams}
    assert res[5].eliminated and res[5].p_top4_incl_ties == 0
    assert res[1].clinched_top4 and res[1].p_top4 == 1
    assert res[1].max_points == 12 and res[5].max_points == 2


def test_tie_dependent_probability() -> None:
    # 5 teams; 4 and 5 meet; 3 already safe. If 5 wins, 4 and 5 finish level on 4 pts each.
    points = {1: 10, 2: 10, 3: 10, 4: 4, 5: 2}
    wins = {1: 5, 2: 5, 3: 5, 4: 2, 5: 1}
    res = {o.team_id: o for o in simulate(points, wins, [Fixture(4, 5)]).teams}
    assert res[4].p_top4 == pytest.approx(0.5)  # wins outright
    # when 5 wins: both on 4 pts and 2 wins -> NRR decides -> tie-dependent for both
    assert res[4].p_top4_incl_ties == pytest.approx(1.0)
    assert res[5].p_top4 == 0 and res[5].p_top4_incl_ties == pytest.approx(0.5)


def test_wins_tiebreak_is_applied_before_nrr() -> None:
    # 4 and 5 level on 10 points for the last spot; 4 has 5 wins, 5 has 4 wins + 2 NR.
    points = {1: 20, 2: 20, 3: 20, 4: 10, 5: 10}
    wins = {1: 10, 2: 10, 3: 10, 4: 5, 5: 4}
    res = {o.team_id: o for o in simulate(points, wins, [Fixture(1, 2)]).teams}
    assert res[4].p_top4 == 1 and res[4].clinched_top4
    assert res[5].p_top4_incl_ties == 0 and res[5].eliminated


def test_user_picks_fix_outcomes() -> None:
    points = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
    fx = [Fixture(1, 2, winner=1), Fixture(3, 4), Fixture(1, 5, winner=1)]
    res = simulate(points, dict.fromkeys(points, 0), fx)
    got = {o.team_id: o for o in res.teams}
    assert res.outcomes == 2  # only the open fixture is enumerated
    assert got[1].clinched_top2 and got[1].p_top2 == 1
    assert got[2].remaining == 1 and got[1].remaining == 2


def test_bad_pick_rejected() -> None:
    with pytest.raises(ValueError):
        simulate({1: 0, 2: 0, 3: 0}, {}, [Fixture(1, 2, winner=3)])


def test_monte_carlo_close_to_exact_and_flags_sound() -> None:
    teams = list(range(1, 9))
    points = {t: 2 * (9 - t) for t in teams}
    fx = [Fixture(a, b) for a, b in itertools.combinations(teams, 2)][:22]  # > 20 -> MC
    wins = {t: p // 2 for t, p in points.items()}
    mc = simulate(points, wins, fx, samples=40_000)
    ex = simulate(points, wins, fx, exhaustive_limit=22)
    assert mc.method == "monte_carlo" and not mc.exact
    e = {o.team_id: o for o in ex.teams}
    for o in mc.teams:
        assert o.p_top4 == pytest.approx(e[o.team_id].p_top4, abs=0.02)
        # bound-based flags never claim more than the exact answer
        assert not o.clinched_top4 or e[o.team_id].clinched_top4
        assert not o.eliminated or e[o.team_id].eliminated
