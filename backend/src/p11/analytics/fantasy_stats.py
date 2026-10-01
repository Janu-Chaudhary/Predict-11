"""Pure distribution helpers for fantasy points (no DB).

Conventions (match docs/FEATURE-CATALOG.md §4 E6):
- percentiles use linear interpolation between order statistics (numpy's default,
  ``statistics.quantiles(method="inclusive")``); floor = p10, ceiling = p90;
- ``sd`` is the population standard deviation of the per-match points;
- ``cv`` (consistency) = sd / mean; lower is more consistent. Undefined when mean <= 0.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Dist:
    n: int
    total: int
    mean: float
    median: float
    sd: float
    cv: float | None
    min: int
    max: int
    p10: float
    p25: float
    p75: float
    p90: float
    pct_50_plus: float
    pct_100_plus: float


def percentile(sorted_vals: Sequence[float], q: float) -> float:
    """Linear-interpolated percentile (0 <= q <= 100) of an ascending sequence."""
    if not sorted_vals:
        raise ValueError("percentile of an empty sequence")
    if len(sorted_vals) == 1:
        return float(sorted_vals[0])
    pos = (len(sorted_vals) - 1) * q / 100.0
    lo = math.floor(pos)
    hi = min(lo + 1, len(sorted_vals) - 1)
    frac = pos - lo
    return float(sorted_vals[lo] + (sorted_vals[hi] - sorted_vals[lo]) * frac)


def distribution(values: Sequence[int]) -> Dist | None:
    if not values:
        return None
    s = sorted(values)
    n = len(s)
    total = sum(s)
    mean = total / n
    sd = math.sqrt(sum((v - mean) ** 2 for v in s) / n)
    return Dist(
        n=n,
        total=total,
        mean=mean,
        median=percentile(s, 50),
        sd=sd,
        cv=sd / mean if mean > 0 else None,
        min=s[0],
        max=s[-1],
        p10=percentile(s, 10),
        p25=percentile(s, 25),
        p75=percentile(s, 75),
        p90=percentile(s, 90),
        pct_50_plus=100.0 * sum(v >= 50 for v in s) / n,
        pct_100_plus=100.0 * sum(v >= 100 for v in s) / n,
    )


def shares(parts: dict[str, int]) -> dict[str, float | None]:
    """Each category's share of the summed total (can be negative / >1 when a category is
    negative overall, e.g. bowling economy penalties). None when the total is 0."""
    tot = sum(parts.values())
    return {k: (v / tot if tot else None) for k, v in parts.items()}


def r1(x: float | None) -> float | None:
    return None if x is None else round(x, 1)


def r2(x: float | None) -> float | None:
    return None if x is None else round(x, 2)
