"""Fantasy distribution helpers (pure)."""

from __future__ import annotations

import statistics

import pytest

from p11.analytics.fantasy_stats import distribution, percentile, shares


def test_percentile_matches_numpy_linear() -> None:
    vals = [2, 10, 20, 35, 50, 80, 120, 151]
    q = statistics.quantiles(vals, n=10, method="inclusive")
    assert percentile(vals, 10) == pytest.approx(q[0])
    assert percentile(vals, 90) == pytest.approx(q[-1])
    assert percentile(vals, 50) == pytest.approx(statistics.median(vals))
    assert percentile([7], 90) == 7
    with pytest.raises(ValueError):
        percentile([], 50)


def test_distribution_fields() -> None:
    vals = [100, 4, 50, 0, 46, 120]
    d = distribution(vals)
    assert d is not None
    assert (d.n, d.total, d.min, d.max) == (6, 320, 0, 120)
    assert d.mean == pytest.approx(320 / 6)
    assert d.sd == pytest.approx(statistics.pstdev(vals))
    assert d.cv == pytest.approx(d.sd / d.mean)
    assert d.pct_50_plus == pytest.approx(100 * 3 / 6)
    assert d.pct_100_plus == pytest.approx(100 * 2 / 6)
    assert d.p10 <= d.p25 <= d.median <= d.p75 <= d.p90
    assert distribution([]) is None


def test_cv_undefined_for_non_positive_mean() -> None:
    d = distribution([0, 0, -2])
    assert d is not None and d.cv is None


def test_shares() -> None:
    s = shares({"batting": 60, "bowling": 30, "fielding": 10})
    assert s == {"batting": 0.6, "bowling": 0.3, "fielding": 0.1}
    assert shares({"batting": 0})["batting"] is None
