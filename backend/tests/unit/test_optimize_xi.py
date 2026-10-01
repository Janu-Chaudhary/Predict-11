"""Optimizer: exactness vs brute force on tiny pools, Dream11 constraints, infeasible cases."""

from __future__ import annotations

import itertools
import random
from typing import Any

import pytest

from p11.optimize.xi import (
    DREAM11,
    ROLES,
    Candidate,
    Infeasible,
    Options,
    Rules,
    pulp_solver,
    score,
    solve,
)

BACKENDS = ["exact"] + (["pulp"] if pulp_solver() is not None else [])


def _brute(pool: list[Candidate], rules: Rules, budget: bool = True) -> float:
    best = -float("inf")
    for team in itertools.combinations(pool, rules.size):
        roles = {r: sum(c.role == r for c in team) for r in ROLES}
        if any(roles[r] < rules.role_min[r] or roles[r] > rules.role_max[r] for r in ROLES):
            continue
        teams: dict[object, int] = {}
        for c in team:
            teams[c.team] = teams.get(c.team, 0) + 1
        if rules.max_per_team is not None and max(teams.values()) > rules.max_per_team:
            continue
        priced = budget and all(c.credits is not None for c in pool)
        if (
            priced
            and rules.budget is not None
            and sum(c.credits or 0 for c in team) > (rules.budget + 1e-9)
        ):
            continue
        vals = sorted((c.value for c in team), reverse=True)
        tot = sum(vals)
        if rules.captains:
            tot += (rules.captain_mult - 1) * vals[0] + (rules.vice_mult - 1) * vals[1]
        best = max(best, tot)
    if best == -float("inf"):
        raise Infeasible("brute")
    return best


def _pool(n: int, seed: int, credits: bool = False, teams: int = 2) -> list[Candidate]:
    rng = random.Random(seed)
    return [
        Candidate(
            player=f"p{i}",
            team=f"T{i % teams}",
            role=ROLES[rng.randrange(4)] if i >= 4 else ROLES[i],
            value=float(rng.randint(-4, 150)),
            credits=rng.choice([6.0, 7.5, 8.0, 8.5, 9.0, 10.5, 11.0]) if credits else None,
        )
        for i in range(n)
    ]


SMALL = Rules(
    size=5,
    role_min=dict.fromkeys(ROLES, 1),
    role_max=dict.fromkeys(ROLES, 2),
    max_per_team=3,
    budget=40.0,
)


@pytest.mark.parametrize("backend", BACKENDS)
@pytest.mark.parametrize("seed", range(25))
def test_matches_brute_force(seed: int, backend: Any) -> None:
    pool = _pool(10, seed, credits=seed % 2 == 0)
    try:
        want = _brute(pool, SMALL)
    except Infeasible:
        with pytest.raises(Infeasible):
            solve(pool, SMALL, Options(solver=backend))
        return
    sel = solve(pool, SMALL, Options(solver=backend))
    assert sel.total == pytest.approx(want)
    assert score([p.candidate for p in sel.picks], sel.captain, sel.vice_captain, SMALL) == (
        pytest.approx(sel.total)
    )


@pytest.mark.parametrize("backend", BACKENDS)
def test_dream11_constraints_respected(backend: Any) -> None:
    pool = _pool(24, 7, credits=True)
    sel = solve(pool, DREAM11, Options(solver=backend))
    team = [p.candidate for p in sel.picks]
    assert len(team) == 11 and len({c.player for c in team}) == 11
    for r in ROLES:
        assert 1 <= sum(c.role == r for c in team) <= 8
    assert max(sum(c.team == t for c in team) for t in ("T0", "T1")) <= 10
    assert sel.credits_constrained and sel.credits_used is not None
    assert sel.credits_used <= 100
    assert sel.picks[0].multiplier == 2 and sel.picks[1].multiplier == 1.5
    assert sel.picks[0].candidate.value >= sel.picks[1].candidate.value
    assert sel.base_total == pytest.approx(sum(c.value for c in team))


def test_captain_and_vice_are_top_two_and_total_formula() -> None:
    pool = [
        Candidate(f"p{i}", "A" if i < 6 else "B", ROLES[i % 4], float(i * 10)) for i in range(12)
    ]
    sel = solve(pool)
    assert sel.captain == "p11" and sel.vice_captain == "p10"
    assert sel.total == pytest.approx(sum(i * 10 for i in range(1, 12)) + 110 + 50)


def test_role_minimum_forces_low_value_keeper() -> None:
    pool = [Candidate(f"b{i}", "A" if i % 2 else "B", "BAT", 100.0 - i) for i in range(10)]
    pool += [Candidate(f"o{i}", "A", r, 1.0) for i, r in enumerate(["WK", "AR", "BOWL"])]
    sel = solve(pool, options=Options(solver="exact"))
    roles = [p.candidate.role for p in sel.picks]
    assert roles.count("WK") == 1 and roles.count("AR") == 1 and roles.count("BOWL") == 1
    assert roles.count("BAT") == 8  # role max


def test_team_cap_applies() -> None:
    pool = [Candidate(f"a{i}", "A", ROLES[i % 4], 100.0) for i in range(12)]
    pool += [Candidate(f"b{i}", "B", ROLES[i % 4], 1.0) for i in range(4)]
    sel = solve(pool, options=Options(solver="exact"))
    assert sum(p.candidate.team == "A" for p in sel.picks) == 10


def test_unknown_credits_means_unconstrained() -> None:
    pool = [Candidate(f"p{i}", i % 2, ROLES[i % 4], 50.0, 15.0) for i in range(14)]
    with pytest.raises(Infeasible):
        solve(pool, options=Options(solver="exact"))  # 11 x 15 > 100
    pool[0] = Candidate("p0", 0, "WK", 50.0, None)
    sel = solve(pool, options=Options(solver="exact"))
    assert not sel.credits_constrained and sel.credits_used is None
    assert not solve(pool[1:] + [pool[0]], options=Options(use_credits=False)).credits_constrained


@pytest.mark.parametrize("backend", BACKENDS)
def test_locks_excludes_and_forced_captain(backend: Any) -> None:
    pool = _pool(20, 3)
    worst = min(pool, key=lambda c: c.value)
    top = max(pool, key=lambda c: c.value)
    opts = Options(
        locks=frozenset({worst.player}), excludes=frozenset({top.player}), solver=backend
    )
    sel = solve(pool, options=opts)
    assert worst.player in sel.players and top.player not in sel.players
    forced = solve(pool, options=Options(captain=worst.player, solver=backend))
    assert forced.captain == worst.player and forced.picks[0].multiplier == 2
    assert forced.total <= solve(pool).total + 1e-9


@pytest.mark.parametrize(
    "opts",
    [
        Options(locks=frozenset({"nobody"})),
        Options(locks=frozenset({"p1"}), excludes=frozenset({"p1"})),
        Options(captain="p1", vice_captain="p1"),
        Options(excludes=frozenset({f"p{i}" for i in range(10)})),
    ],
)
def test_infeasible_options(opts: Options) -> None:
    with pytest.raises(Infeasible):
        solve(_pool(14, 1), options=opts)


def test_infeasible_missing_role() -> None:
    pool = [Candidate(f"p{i}", i % 2, ["BAT", "AR", "BOWL"][i % 3], 10.0) for i in range(15)]
    with pytest.raises(Infeasible):
        solve(pool)
    with pytest.raises(Infeasible):
        solve(pool, options=Options(solver="exact"))


def test_infeasible_locks_break_team_cap() -> None:
    pool = [Candidate(f"p{i}", "A" if i < 12 else "B", ROLES[i % 4], 10.0) for i in range(16)]
    with pytest.raises(Infeasible):
        solve(pool, options=Options(locks=frozenset(f"p{i}" for i in range(11))))


def test_bad_input() -> None:
    with pytest.raises(ValueError):
        solve([Candidate("x", 1, "KEEPER", 1.0)] * 1)
    with pytest.raises(ValueError):
        solve([Candidate("x", 1, "WK", 1.0), Candidate("x", 1, "WK", 1.0)])


def test_team_of_season_without_captains_is_top_values() -> None:
    pool = _pool(60, 11, teams=8)
    rules = Rules(captains=False, budget=None)
    sel = solve(pool, rules, Options(solver="exact"))
    assert sel.captain is None and all(p.multiplier == 1 for p in sel.picks)
    assert sel.total == pytest.approx(_greedy_role_bound(pool))


def _greedy_role_bound(pool: list[Candidate]) -> float:
    # one best per role, then the 7 best of the rest (role max 8 / team cap 10 never bind here)
    ranked = sorted(pool, key=lambda c: -c.value)
    picked = [next(c for c in ranked if c.role == r) for r in ROLES]
    rest = [c for c in ranked if c not in picked][:7]
    return sum(c.value for c in picked + rest)


def test_large_pool_with_budget_is_fast() -> None:
    import time

    pool = _pool(26, 5, credits=True)
    t = time.perf_counter()
    sel = solve(pool, options=Options(solver="exact"))
    assert time.perf_counter() - t < 2.0
    assert sel.credits_used is not None and sel.credits_used <= 100
