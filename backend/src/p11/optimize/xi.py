"""Exact fantasy-XI selection: pick ``size`` players from a candidate pool maximising

    sum_i value_i * (x_i + (C-1) * c_i + (VC-1) * v_i)        (C = 2, VC = 1.5)

subject to Dream11 team rules. Reusable by any caller that can express its pool as
``Candidate(player, team, role, value, credits?)`` -- hindsight XIs (value = actual points),
"naive form" XIs (value = recent average) and, later, the projection optimizer.

Two exact back-ends give the same optimum:

* **PuLP ILP** (binary x/c/v variables) when a MILP solver is installed. PuLP 4 bundles no
  solver (``PULP_CBC_CMD`` is gone); we try ``HiGHS`` (``highspy``), ``HiGHS_CMD``,
  ``COIN_CMD`` (``cbcbox`` or ``cbc`` on PATH), then ``GLPK_CMD``.
* **Branch and bound** in pure Python otherwise (or with ``solver="exact"``). Candidates are
  scanned in value order and a subtree is cut when ``chosen + best possible remainder`` (the
  top values still available, captain bonuses included) cannot beat the incumbent, or when the
  role minima / budget can no longer be met. Fast for match pools (≈22-26 players) and season
  pools (≈200, budget-free); it is exact, not a heuristic.

Team rules (``DREAM11``): 11 players; 1-8 from each of WK / BAT / AR / BOWL; at most 10 from one
real team; a 100-credit budget. These are Dream11's current cricket rules (the 2023 change that
replaced the old 1-4 WK / 3-6 BAT / 1-4 AR / 3-6 BOWL / max-7-per-team limits used by the v1
system). The official pages were unreachable (HTTP 502) when this was written on 2026-10-02,
so the values are from Dream11's in-app team-creation rules as last known, and were confirmed by
the owner on 2026-10-02. Every limit is a field of ``Rules`` so it can be changed in one place.
"""

from __future__ import annotations

import math
from collections.abc import Hashable, Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Any, Literal

ROLES: tuple[str, ...] = ("WK", "BAT", "AR", "BOWL")
EPS = 1e-6


@dataclass(frozen=True, slots=True)
class Candidate:
    player: str
    team: Hashable
    role: str  # WK | BAT | AR | BOWL
    value: float
    credits: float | None = None


@dataclass(frozen=True, slots=True)
class Rules:
    size: int = 11
    role_min: Mapping[str, int] = field(default_factory=lambda: dict.fromkeys(ROLES, 1))
    role_max: Mapping[str, int] = field(default_factory=lambda: dict.fromkeys(ROLES, 8))
    max_per_team: int | None = 10
    budget: float | None = 100.0
    captain_mult: float = 2.0
    vice_mult: float = 1.5
    captains: bool = True  # False: no C/VC (e.g. a "team of the season")


DREAM11 = Rules()


@dataclass(frozen=True, slots=True)
class Options:
    locks: frozenset[str] = frozenset()
    excludes: frozenset[str] = frozenset()
    captain: str | None = None  # forced captain (implicitly locked)
    vice_captain: str | None = None
    # Apply ``Rules.budget`` when every remaining candidate has credits; otherwise the
    # selection is credit-unconstrained (reported via ``Selection.credits_constrained``).
    use_credits: bool = True
    solver: Literal["auto", "pulp", "exact"] = "auto"


@dataclass(frozen=True, slots=True)
class Pick:
    candidate: Candidate
    multiplier: float

    @property
    def points(self) -> float:
        return self.candidate.value * self.multiplier


@dataclass(frozen=True, slots=True)
class Selection:
    picks: tuple[Pick, ...]  # captain, vice-captain, then by value (desc)
    captain: str | None
    vice_captain: str | None
    total: float  # with multipliers
    base_total: float  # without multipliers
    credits_used: float | None
    credits_constrained: bool
    solver: str

    @property
    def players(self) -> list[str]:
        return [p.candidate.player for p in self.picks]


class Infeasible(ValueError):
    """No team satisfies the rules with this pool and these options."""


# --------------------------------------------------------------------------- public API
def solve(
    candidates: Iterable[Candidate], rules: Rules = DREAM11, options: Options | None = None
) -> Selection:
    opts = options or Options()
    pool = _prepare(list(candidates), rules, opts)
    budget = _budget(pool, rules, opts)
    backend = opts.solver
    if backend == "auto":
        backend = "pulp" if pulp_solver() is not None else "exact"
    if backend == "pulp":
        chosen, cap, vc, name = _solve_pulp(pool, rules, opts, budget)
    else:
        chosen, cap, vc = _solve_exact(pool, rules, opts, budget)
        name = "exact-bnb"
    return _selection(chosen, cap, vc, rules, budget is not None, name)


def score(
    picks: Sequence[Candidate],
    captain: str | None,
    vice_captain: str | None,
    rules: Rules = DREAM11,
) -> float:
    """Total of a given team with its C/VC (used to re-score an XI with other values)."""
    tot = 0.0
    for c in picks:
        m = _mult(c.player, captain, vice_captain, rules)
        tot += c.value * m
    return tot


@lru_cache(maxsize=1)
def pulp_solver() -> Any | None:
    """The first installed PuLP MILP solver, or None (then the exact B&B is used)."""
    try:
        import pulp
    except ImportError:  # pragma: no cover
        return None
    for name in ("HiGHS", "HiGHS_CMD", "COIN_CMD", "GLPK_CMD"):
        try:
            s = pulp.getSolver(name, msg=False)
            if s.available():
                return s
        except Exception:  # noqa: S112 - probing optional solvers
            continue
    return None


# --------------------------------------------------------------------------- validation
def _prepare(cands: list[Candidate], rules: Rules, opts: Options) -> list[Candidate]:
    seen: set[str] = set()
    for c in cands:
        if c.player in seen:
            raise ValueError(f"duplicate candidate {c.player!r}")
        seen.add(c.player)
        if c.role not in ROLES:
            raise ValueError(f"unknown role {c.role!r} for {c.player!r}")
        if not math.isfinite(c.value):
            raise ValueError(f"non-finite value for {c.player!r}")
    forced = set(opts.locks)
    for p in (opts.captain, opts.vice_captain):
        if p is not None:
            forced.add(p)
    if opts.captain is not None and opts.captain == opts.vice_captain:
        raise Infeasible("captain and vice-captain must differ")
    if not rules.captains and (opts.captain or opts.vice_captain):
        raise ValueError("captain options given but rules.captains is False")
    if missing := forced - seen:
        raise Infeasible(f"locked players not in the pool: {sorted(missing)}")
    if clash := forced & set(opts.excludes):
        raise Infeasible(f"players both locked and excluded: {sorted(clash)}")
    pool = [c for c in cands if c.player not in opts.excludes]
    if len(pool) < rules.size:
        raise Infeasible(f"only {len(pool)} candidates for a team of {rules.size}")
    if len(forced) > rules.size:
        raise Infeasible(f"{len(forced)} locked players for a team of {rules.size}")
    if rules.captains and rules.size < 2:
        raise ValueError("a captain and a vice-captain need a team of at least 2")
    if sum(rules.role_min.values()) > rules.size:
        raise Infeasible("role minimums exceed the team size")
    return pool


def _budget(pool: list[Candidate], rules: Rules, opts: Options) -> int | None:
    """Budget in tenths of a credit, or None when unconstrained."""
    if not opts.use_credits or rules.budget is None:
        return None
    if any(c.credits is None for c in pool):
        return None
    return _tenths(rules.budget)


def _tenths(x: float | None) -> int:
    return round((x or 0.0) * 10)


def _mult(player: str, cap: str | None, vc: str | None, rules: Rules) -> float:
    if player == cap:
        return rules.captain_mult
    if player == vc:
        return rules.vice_mult
    return 1.0


def _selection(
    chosen: list[Candidate],
    cap: str | None,
    vc: str | None,
    rules: Rules,
    constrained: bool,
    solver: str,
) -> Selection:
    def order(c: Candidate) -> tuple[int, float, str]:
        rank = 0 if c.player == cap else 1 if c.player == vc else 2
        return (rank, -c.value, c.player)

    chosen = sorted(chosen, key=order)
    picks = tuple(Pick(c, _mult(c.player, cap, vc, rules)) for c in chosen)
    credits = [c.credits for c in chosen]
    used = (
        _tenths(sum(x for x in credits if x is not None)) / 10
        if all(x is not None for x in credits)
        else None
    )
    return Selection(
        picks=picks,
        captain=cap,
        vice_captain=vc,
        total=round(sum(p.points for p in picks), 6),
        base_total=round(sum(c.value for c in chosen), 6),
        credits_used=used,
        credits_constrained=constrained,
        solver=solver,
    )


# --------------------------------------------------------------------------- PuLP ILP
def _solve_pulp(
    pool: list[Candidate], rules: Rules, opts: Options, budget: int | None
) -> tuple[list[Candidate], str | None, str | None, str]:
    import pulp

    solver = pulp_solver()
    if solver is None:
        raise RuntimeError("no PuLP MILP solver installed (install pulp[highs] or cbc)")
    idx = list(range(len(pool)))
    prob = pulp.LpProblem("fantasy_xi", pulp.LpMaximize)
    x = prob.add_variable_dicts("x", idx, cat="Binary")
    c = prob.add_variable_dicts("c", idx, cat="Binary") if rules.captains else {}
    v = prob.add_variable_dicts("v", idx, cat="Binary") if rules.captains else {}
    cm, vm = rules.captain_mult - 1, rules.vice_mult - 1
    obj = pulp.lpSum(pool[i].value * x[i] for i in idx)
    if rules.captains:
        obj += pulp.lpSum(pool[i].value * (cm * c[i] + vm * v[i]) for i in idx)
    prob += obj
    prob += pulp.lpSum(x[i] for i in idx) == rules.size
    if rules.captains:
        prob += pulp.lpSum(c[i] for i in idx) == 1
        prob += pulp.lpSum(v[i] for i in idx) == 1
        for i in idx:
            prob += c[i] <= x[i]
            prob += v[i] <= x[i]
            prob += c[i] + v[i] <= 1
    for role in ROLES:
        members = [i for i in idx if pool[i].role == role]
        prob += pulp.lpSum(x[i] for i in members) >= rules.role_min.get(role, 0)
        prob += pulp.lpSum(x[i] for i in members) <= rules.role_max.get(role, rules.size)
    if rules.max_per_team is not None:
        for team in {p.team for p in pool}:
            members = [i for i in idx if pool[i].team == team]
            prob += pulp.lpSum(x[i] for i in members) <= rules.max_per_team
    if budget is not None:
        prob += pulp.lpSum(_tenths(pool[i].credits) * x[i] for i in idx) <= budget
    pos = {p.player: i for i, p in enumerate(pool)}
    for p in opts.locks:
        prob += x[pos[p]] == 1
    if opts.captain is not None:
        prob += c[pos[opts.captain]] == 1
    if opts.vice_captain is not None:
        prob += v[pos[opts.vice_captain]] == 1
    stats = prob.solve(solver)
    if stats.status != pulp.LpSolveStatus.Optimal or not stats.has_solution:
        raise Infeasible(f"no feasible team ({stats.status.name})")
    chosen = [pool[i] for i in idx if (x[i].value() or 0) > 0.5]
    cap = next((pool[i].player for i in idx if rules.captains and (c[i].value() or 0) > 0.5), None)
    vc = next((pool[i].player for i in idx if rules.captains and (v[i].value() or 0) > 0.5), None)
    # tie-break like the exact solver so both back-ends report the same C/VC
    cap, vc = _assign_captains(chosen, rules, opts) if rules.captains else (cap, vc)
    return chosen, cap, vc, f"pulp-{stats.solver}"


# --------------------------------------------------------------------------- exact B&B
def _assign_captains(
    team: Sequence[Candidate], rules: Rules, opts: Options
) -> tuple[str | None, str | None]:
    """Optimal C/VC for a fixed team: the two highest values (respecting forced ones)."""
    if not rules.captains:
        return None, None
    ranked = sorted(team, key=lambda c: (-c.value, c.player))
    cap = opts.captain
    vc = opts.vice_captain
    if cap is None:
        cap = next(c.player for c in ranked if c.player != vc)
    if vc is None:
        vc = next(c.player for c in ranked if c.player != cap)
    return cap, vc


def _team_value(team: Sequence[Candidate], rules: Rules, opts: Options) -> float:
    cap, vc = _assign_captains(team, rules, opts)
    return score(team, cap, vc, rules)


def _solve_exact(
    pool: list[Candidate], rules: Rules, opts: Options, budget: int | None
) -> tuple[list[Candidate], str | None, str | None]:
    size = rules.size
    forced_ids = set(opts.locks) | {p for p in (opts.captain, opts.vice_captain) if p}
    forced = [c for c in pool if c.player in forced_ids]
    free = sorted(
        (c for c in pool if c.player not in forced_ids), key=lambda c: (-c.value, c.player)
    )
    n = len(free)
    vals = [c.value for c in free]
    roles = [c.role for c in free]
    teams = [c.team for c in free]
    cred = [_tenths(c.credits) for c in free]
    rmin = {r: rules.role_min.get(r, 0) for r in ROLES}
    rmax = {r: rules.role_max.get(r, size) for r in ROLES}
    tmax = rules.max_per_team if rules.max_per_team is not None else size

    # suffix data for feasibility pruning
    role_left = [dict.fromkeys(ROLES, 0) for _ in range(n + 1)]
    min_cred = [math.inf] * (n + 1)
    for i in range(n - 1, -1, -1):
        role_left[i] = dict(role_left[i + 1])
        role_left[i][roles[i]] += 1
        min_cred[i] = min(min_cred[i + 1], cred[i])

    role_cnt = dict.fromkeys(ROLES, 0)
    team_cnt: dict[Hashable, int] = {}
    used = 0
    for c in forced:
        role_cnt[c.role] += 1
        team_cnt[c.team] = team_cnt.get(c.team, 0) + 1
        used += _tenths(c.credits)
    if any(role_cnt[r] > rmax[r] for r in ROLES) or any(v > tmax for v in team_cnt.values()):
        raise Infeasible("locked players break the role or team limits")
    if budget is not None and used > budget:
        raise Infeasible("locked players exceed the budget")

    cm, vm = rules.captain_mult - 1, rules.vice_mult - 1
    fixed_cap = next((c.value for c in forced if c.player == opts.captain), None)
    fixed_vc = next((c.value for c in forced if c.player == opts.vice_captain), None)

    def bonus_bound(values: list[float]) -> float:
        if not rules.captains:
            return 0.0
        rest = sorted(values, reverse=True)
        if fixed_cap is not None and fixed_vc is not None:
            return cm * fixed_cap + vm * fixed_vc
        if fixed_cap is not None:
            return cm * fixed_cap + vm * (rest[0] if rest else 0.0)
        if fixed_vc is not None:
            return cm * (rest[0] if rest else 0.0) + vm * fixed_vc
        return cm * rest[0] + vm * rest[1]

    chosen_idx: list[int] = []
    fixed_ids = {opts.captain, opts.vice_captain}
    forced_free = [c.value for c in forced if c.player not in fixed_ids]

    def free_vals(chosen_vals: list[float]) -> list[float]:
        """Values eligible for a free C/VC slot (everyone but a forced C/VC)."""
        return forced_free + chosen_vals

    best_val = -math.inf
    best: list[int] | None = None
    base = sum(c.value for c in forced)

    def feasible_tail(i: int, need: int) -> bool:
        if n - i < need:
            return False
        short = 0
        for r in ROLES:
            lack = rmin[r] - role_cnt[r]
            if lack > 0:
                if role_left[i][r] < lack:
                    return False
                short += lack
        if short > need:
            return False
        return not (budget is not None and need and used + need * min_cred[i] > budget)

    def dfs(i: int, cur: float) -> None:
        nonlocal best_val, best, used
        k = len(forced) + len(chosen_idx)
        need = size - k
        if need == 0:
            if all(role_cnt[r] >= rmin[r] for r in ROLES):
                total = cur + bonus_bound(free_vals([vals[j] for j in chosen_idx]))
                if total > best_val + EPS:
                    best_val, best = total, list(chosen_idx)
            return
        if not feasible_tail(i, need):
            return
        tail = vals[i : i + need]
        bound = bonus_bound(free_vals([vals[j] for j in chosen_idx]) + tail)
        if cur + sum(tail) + bound <= best_val + EPS:
            return
        # include i
        r, t = roles[i], teams[i]
        if (
            role_cnt[r] < rmax[r]
            and team_cnt.get(t, 0) < tmax
            and (budget is None or used + cred[i] <= budget)
        ):
            role_cnt[r] += 1
            team_cnt[t] = team_cnt.get(t, 0) + 1
            used += cred[i]
            chosen_idx.append(i)
            dfs(i + 1, cur + vals[i])
            chosen_idx.pop()
            used -= cred[i]
            team_cnt[t] -= 1
            role_cnt[r] -= 1
        # exclude i
        dfs(i + 1, cur)

    dfs(0, base)
    if best is None:
        raise Infeasible("no team satisfies the role / team / budget rules")
    team = forced + [free[j] for j in best]
    cap, vc = _assign_captains(team, rules, opts)
    return team, cap, vc
