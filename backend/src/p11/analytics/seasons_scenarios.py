"""Playoff qualification scenarios (F2), pure computation.

Every remaining league match is a coin flip (2 points to the winner; no-results are not
simulated). Teams are ranked on (points, wins); NRR is unknown in the future, so a team level
with others on both at the cut line is "tie-dependent": it qualifies in ``*_incl_ties`` but
not in the clear ``p_*`` probability.

With <= ``EXHAUSTIVE_LIMIT`` open matches all 2^k outcomes are enumerated (exact). Beyond that
``MC_SAMPLES`` random outcomes are drawn; clinched/eliminated flags are then derived from
sound bounds only (never from sampling), so they may be conservative.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

import numpy as np
import numpy.typing as npt

EXHAUSTIVE_LIMIT = 20
MC_SAMPLES = 100_000
_WIN_KEY = 2 * 100 + 1  # a win adds 2 points and 1 win; key = points * 100 + wins
_Col = npt.NDArray[np.int16]


@dataclass(frozen=True, slots=True)
class Fixture:
    team1: int
    team2: int
    winner: int | None = None  # fixed (user pick); None = open


@dataclass(frozen=True, slots=True)
class TeamOdds:
    team_id: int
    points: int
    wins: int
    remaining: int
    max_points: int
    p_top4: float
    p_top4_incl_ties: float
    p_top2: float
    p_top2_incl_ties: float
    clinched_top4: bool
    eliminated: bool
    clinched_top2: bool
    out_of_top2: bool


@dataclass(frozen=True, slots=True)
class ScenarioResult:
    method: str  # exhaustive | monte_carlo
    outcomes: int
    exact: bool
    teams: list[TeamOdds]


def _enumerate(base: npt.NDArray[np.int16], open_fx: Sequence[tuple[int, int]]) -> list[_Col]:
    """All 2^k outcomes as per-team key columns. Built as low-half x high-half lookup tables so
    the 2^k rows come from one broadcast add instead of k passes."""

    def table(fx: Sequence[tuple[int, int]]) -> npt.NDArray[np.int16]:
        codes = np.arange(1 << len(fx), dtype=np.uint32)
        out = np.zeros((codes.size, base.size), dtype=np.int16)
        for j, (i1, i2) in enumerate(fx):
            bit = ((codes >> np.uint32(j)) & np.uint32(1)).astype(np.int16)
            out[:, i1] += _WIN_KEY * (1 - bit)
            out[:, i2] += _WIN_KEY * bit
        return out

    half = len(open_fx) // 2
    lo, hi = table(open_fx[:half]), table(open_fx[half:])
    n = lo.shape[0] * hi.shape[0]
    cols: list[_Col] = []
    for i in range(base.size):
        col = np.empty((hi.shape[0], lo.shape[0]), dtype=np.int16)
        np.add((hi[:, i] + base[i])[:, None], lo[None, :, i], out=col)
        cols.append(col.reshape(n))
    return cols


def _sample(
    base: npt.NDArray[np.int16], open_fx: Sequence[tuple[int, int]], samples: int, seed: int
) -> list[_Col]:
    rng = np.random.default_rng(seed)
    cols = [np.full(samples, b, dtype=np.int16) for b in base]
    for i1, i2 in open_fx:
        bit = rng.integers(0, 2, samples, dtype=np.int16)
        cols[i1] += _WIN_KEY * (1 - bit)
        cols[i2] += _WIN_KEY * bit
    return cols


def _top_cuts(cols: Sequence[_Col], depth: int) -> list[_Col]:
    """Per-outcome k-th largest key for k = 1..depth (insertion network, no full sort)."""
    n = cols[0].size
    top = [np.full(n, np.iinfo(np.int16).min, dtype=np.int16) for _ in range(depth)]
    carry = np.empty(n, dtype=np.int16)
    spare = np.empty(n, dtype=np.int16)
    for c in cols:  # allocation-free: max goes to `spare`, min stays in `carry`
        np.copyto(carry, c)
        for r in range(depth):
            np.maximum(top[r], carry, out=spare)
            np.minimum(top[r], carry, out=carry)
            top[r], spare = spare, top[r]
    return top


def _bound_flags(
    idx: int, cur: Sequence[int], best: Sequence[int], slots: int
) -> tuple[bool, bool]:
    """(clinched, eliminated) for a top-``slots`` finish, from bounds that hold in every
    outcome. Clinched: fewer than ``slots`` other teams can even reach our current key.
    Eliminated: at least ``slots`` teams are already strictly above our best possible key."""
    others = [j for j in range(len(cur)) if j != idx]
    can_catch = sum(1 for j in others if best[j] >= cur[idx])
    above_forever = sum(1 for j in others if cur[j] > best[idx])
    return can_catch < slots, above_forever >= slots


def simulate(
    points: Mapping[int, int],
    wins: Mapping[int, int],
    fixtures: Sequence[Fixture],
    *,
    exhaustive_limit: int = EXHAUSTIVE_LIMIT,
    samples: int = MC_SAMPLES,
    seed: int = 2026,
) -> ScenarioResult:
    teams = sorted(set(points) | {t for f in fixtures for t in (f.team1, f.team2)})
    pos = {t: i for i, t in enumerate(teams)}
    n_teams = len(teams)
    pts = [points.get(t, 0) for t in teams]
    wns = [wins.get(t, 0) for t in teams]
    remaining = [0] * n_teams
    for f in fixtures:  # user picks are folded into the base
        if f.winner is not None:
            if f.winner not in (f.team1, f.team2):
                raise ValueError(f"winner {f.winner} is not in fixture {f.team1} v {f.team2}")
            pts[pos[f.winner]] += 2
            wns[pos[f.winner]] += 1
    open_fx = [(pos[f.team1], pos[f.team2]) for f in fixtures if f.winner is None]
    for i1, i2 in open_fx:
        remaining[i1] += 1
        remaining[i2] += 1
    cur = [p * 100 + w for p, w in zip(pts, wns, strict=True)]
    best = [c + _WIN_KEY * r for c, r in zip(cur, remaining, strict=True)]

    exhaustive = len(open_fx) <= exhaustive_limit
    base = np.array(cur, dtype=np.int16)
    cols = _enumerate(base, open_fx) if exhaustive else _sample(base, open_fx, samples, seed)
    n_out = int(cols[0].size)
    # cuts[r] = key of the team in position r+1; the int16 floor stands in when n_teams < 5
    cuts = _top_cuts(cols, 5)
    top4_clear = [float(np.count_nonzero(c > cuts[4])) / n_out for c in cols]
    top4_ties = [float(np.count_nonzero(c >= cuts[3])) / n_out for c in cols]
    top2_clear = [float(np.count_nonzero(c > cuts[2])) / n_out for c in cols]
    top2_ties = [float(np.count_nonzero(c >= cuts[1])) / n_out for c in cols]

    out: list[TeamOdds] = []
    for t in teams:
        i = pos[t]
        if exhaustive:
            c4, e4 = bool(top4_clear[i] == 1.0), bool(top4_ties[i] == 0.0)
            c2, e2 = bool(top2_clear[i] == 1.0), bool(top2_ties[i] == 0.0)
        else:
            c4, e4 = _bound_flags(i, cur, best, 4)
            c2, e2 = _bound_flags(i, cur, best, 2)
        out.append(
            TeamOdds(
                team_id=t,
                points=points.get(t, 0),
                wins=wins.get(t, 0),
                remaining=remaining[i]
                + sum(1 for f in fixtures if f.winner is not None and t in (f.team1, f.team2)),
                max_points=pts[i] + 2 * remaining[i],
                p_top4=top4_clear[i],
                p_top4_incl_ties=top4_ties[i],
                p_top2=top2_clear[i],
                p_top2_incl_ties=top2_ties[i],
                clinched_top4=c4,
                eliminated=e4,
                clinched_top2=c2,
                out_of_top2=e2,
            )
        )
    out.sort(key=lambda o: (-o.p_top4_incl_ties, -o.p_top4, -o.points, o.team_id))
    return ScenarioResult("exhaustive" if exhaustive else "monte_carlo", n_out, exhaustive, out)
