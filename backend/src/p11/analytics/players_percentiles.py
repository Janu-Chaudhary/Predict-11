"""League-wide skill percentiles for the player-compare radar.

For each skill axis every IPL player with a big enough sample in the requested scope (career,
one season, or since a date) forms the population; a player's percentile is the mid-rank share
of that population below them (ties count half), so the median player sits at 50. Lower-is-better
axes (economy) are inverted so 100 is always "best". A requested player below the sample bar still
gets their raw value but no percentile.

Raw stats come from the same bulk per-innings cards as /players/compare (``players_data.bulk``);
fantasy means from persisted Dream11 points (``fantasy_data``), no-result matches excluded.
"""

from __future__ import annotations

import bisect
import datetime as dt
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from typing import Literal

from pydantic import BaseModel
from sqlalchemy import Connection

from . import fantasy_data
from .players import match_filter
from .players_data import bulk, cached, reference
from .players_models import Filters


@dataclass(frozen=True, slots=True)
class Axis:
    key: str
    label: str
    better: Literal["high", "low"]
    sample: str  # human-readable eligibility rule


AXES: tuple[Axis, ...] = (
    Axis("runs_per_inns", "Run volume (runs / innings)", "high", "≥ 8 batting innings"),
    Axis("strike_rate", "Strike rate", "high", "≥ 100 balls faced"),
    Axis("average", "Batting average", "high", "≥ 8 innings and ≥ 3 dismissals"),
    Axis("wickets_per_inns", "Wickets / innings", "high", "≥ 120 balls bowled"),
    Axis("economy", "Economy", "low", "≥ 120 balls bowled"),
    Axis("fielding_per_match", "Fielding dismissals / match", "high", "≥ 8 matches"),
    Axis("fantasy_mean", "Fantasy points / match", "high", "≥ 8 scored matches"),
)

MIN_INNS = 8
MIN_OUTS = 3
MIN_BAT_BALLS = 100
MIN_BOWL_BALLS = 120
MIN_MATCHES = 8


# --------------------------------------------------------------------------- pure core
@dataclass(slots=True)
class Sample:
    """Per-player raw value on each axis plus whether it is eligible to rank."""

    values: dict[str, float | None]
    eligible: dict[str, bool]


def mid_rank_percentile(sorted_pop: Sequence[float], v: float) -> float | None:
    """Share (0-100) of ``sorted_pop`` strictly below ``v`` plus half the ties."""
    n = len(sorted_pop)
    if n == 0:
        return None
    lo = bisect.bisect_left(sorted_pop, v)
    hi = bisect.bisect_right(sorted_pop, v)
    return 100.0 * (lo + 0.5 * (hi - lo)) / n


def sample_of(
    *,
    bat_inns: int,
    bat_outs: int,
    runs: int,
    bat_balls: int,
    bowl_inns: int,
    bowl_balls: int,
    bowl_runs: int,
    wickets: int,
    matches: int,
    fielding: int,
    fantasy: Sequence[int],
) -> Sample:
    def rate(a: float, b: float, k: float = 1.0) -> float | None:
        return a * k / b if b else None

    values: dict[str, float | None] = {
        "runs_per_inns": rate(runs, bat_inns),
        "strike_rate": rate(runs, bat_balls, 100),
        "average": rate(runs, bat_outs),
        "wickets_per_inns": rate(wickets, bowl_inns),
        "economy": rate(bowl_runs, bowl_balls, 6),
        "fielding_per_match": rate(fielding, matches),
        "fantasy_mean": rate(sum(fantasy), len(fantasy)),
    }
    eligible = {
        "runs_per_inns": bat_inns >= MIN_INNS,
        "strike_rate": bat_balls >= MIN_BAT_BALLS,
        "average": bat_inns >= MIN_INNS and bat_outs >= MIN_OUTS,
        "wickets_per_inns": bowl_balls >= MIN_BOWL_BALLS,
        "economy": bowl_balls >= MIN_BOWL_BALLS,
        "fielding_per_match": matches >= MIN_MATCHES,
        "fantasy_mean": len(fantasy) >= MIN_MATCHES,
    }
    return Sample(values, {k: eligible[k] and values[k] is not None for k in values})


@dataclass(slots=True)
class Population:
    samples: dict[str, Sample]
    sorted_by_axis: dict[str, list[float]]  # eligible values, ascending


def population(samples: dict[str, Sample], axes: Iterable[Axis] = AXES) -> Population:
    by_axis: dict[str, list[float]] = {}
    for a in axes:
        by_axis[a.key] = sorted(
            v
            for s in samples.values()
            if s.eligible.get(a.key) and (v := s.values.get(a.key)) is not None
        )
    return Population(samples, by_axis)


def percentile_of(pop: Population, axis: Axis, pid: str) -> float | None:
    s = pop.samples.get(pid)
    if s is None or not s.eligible.get(axis.key):
        return None
    v = s.values[axis.key]
    if v is None:
        return None
    p = mid_rank_percentile(pop.sorted_by_axis[axis.key], v)
    if p is None:
        return None
    return round(100.0 - p if axis.better == "low" else p, 1)


# --------------------------------------------------------------------------- data
def _build(conn: Connection, season: int | None, since: dt.date | None) -> Population:
    ref, bk = reference(conn), bulk(conn)
    keep = match_filter(ref, season, since)
    fdata = fantasy_data.data()
    pids = set(ref.appearances) | set(bk.batting) | set(bk.bowling)
    samples: dict[str, Sample] = {}
    for pid in pids:
        bat = [c for c in bk.batting.get(pid, []) if keep(c.match_id)]
        bowl = [c for c in bk.bowling.get(pid, []) if keep(c.match_id)]
        mids = {m for m, _t in ref.appearances.get(pid, []) if keep(m)}
        mids.update(c.match_id for c in bat)
        mids.update(c.match_id for c in bowl)
        if not mids:
            continue
        fld = [f for m, f in bk.fielding.get(pid, {}).items() if keep(m)]
        pts = [
            r.total
            for r in fdata.by_player.get(pid, [])
            if (season is None or r.year == season) and (since is None or r.date >= since)
        ]
        samples[pid] = sample_of(
            bat_inns=len(bat),
            bat_outs=sum(c.out for c in bat),
            runs=sum(c.runs for c in bat),
            bat_balls=sum(c.balls for c in bat),
            bowl_inns=len(bowl),
            bowl_balls=sum(c.balls for c in bowl),
            bowl_runs=sum(c.runs for c in bowl),
            wickets=sum(c.wickets for c in bowl),
            matches=len(mids),
            fielding=sum(f.catches + f.stumpings + f.run_outs for f in fld),
            fantasy=pts,
        )
    return population(samples)


# --------------------------------------------------------------------------- API models
class AxisInfo(BaseModel):
    key: str
    label: str
    better: Literal["high", "low"]
    sample: str
    population: int


class AxisValue(BaseModel):
    key: str
    value: float | None
    percentile: float | None


class PlayerPercentiles(BaseModel):
    id: str
    axes: list[AxisValue]


class PercentilesResponse(BaseModel):
    filters: Filters
    axes: list[AxisInfo]
    players: list[PlayerPercentiles]


def skill_percentiles(
    conn: Connection, ids: list[str], season: int | None = None, since: dt.date | None = None
) -> PercentilesResponse:
    pop = cached(conn, f"percentiles:{season}:{since}", lambda c: _build(c, season, since))
    out = []
    for pid in ids:
        s = pop.samples.get(pid)
        out.append(
            PlayerPercentiles(
                id=pid,
                axes=[
                    AxisValue(
                        key=a.key,
                        value=round(v, 2) if s and (v := s.values.get(a.key)) is not None else None,
                        percentile=percentile_of(pop, a, pid),
                    )
                    for a in AXES
                ],
            )
        )
    return PercentilesResponse(
        filters=Filters(season=season, since=since),
        axes=[
            AxisInfo(
                key=a.key,
                label=a.label,
                better=a.better,
                sample=a.sample,
                population=len(pop.sorted_by_axis[a.key]),
            )
            for a in AXES
        ],
        players=out,
    )
