"""E2 dew maths: spread, dew / rain classification, interpolation, buckets (no DB)."""

from __future__ import annotations

import datetime as dt

import pytest

from p11.analytics.conditions_weather import (
    HIGH_DEW_SPREAD,
    EveningResult,
    bucket,
    dew_risk,
    dew_season,
    interpolate,
    is_high_dew,
    rain_risk,
    reading,
    spread,
)

UTC = dt.UTC


def test_spread_and_dew_classification() -> None:
    assert spread(28.8, 24.3) == 4.5
    assert spread(None, 20) is None
    assert HIGH_DEW_SPREAD == 3.0
    assert dew_risk(3.0) == "high" and dew_risk(2.1) == "high"
    assert dew_risk(3.01) == "moderate" and dew_risk(6.0) == "moderate"
    assert dew_risk(6.5) == "low" and dew_risk(None) == "unknown"
    assert is_high_dew(3.0) is True and is_high_dew(3.1) is False and is_high_dew(None) is None


def test_rain_risk() -> None:
    assert rain_risk(0.0) == "none"
    assert rain_risk(1.9) == "low"
    assert rain_risk(2.0) == "high"
    assert rain_risk(None) == "unknown"


def _series(start: dt.datetime, temps: list[float], dews: list[float], rain: list[float]):
    return {
        start + dt.timedelta(hours=i): {
            "temperature_2m": t,
            "dew_point_2m": d,
            "relative_humidity_2m": 70.0,
            "precipitation": r,
        }
        for i, (t, d, r) in enumerate(zip(temps, dews, rain, strict=True))
    }


def test_interpolate() -> None:
    t0 = dt.datetime(2026, 4, 12, 14, tzinfo=UTC)
    s = _series(t0, [30.0, 28.0], [20.0, 22.0], [0, 0])
    assert interpolate(s, t0, "temperature_2m") == 30.0
    assert interpolate(s, t0 + dt.timedelta(minutes=30), "temperature_2m") == 29.0
    assert interpolate(s, t0 + dt.timedelta(minutes=90), "temperature_2m") is None


def test_reading_at_second_innings_time() -> None:
    start = dt.datetime(2026, 4, 12, 14, tzinfo=UTC)  # 19:30 IST
    s = _series(
        start - dt.timedelta(hours=4),
        [33, 32, 31, 30, 29, 28.4, 28.2, 27.8, 27.5],
        [21, 22, 22, 23, 24, 24.6, 24.2, 24.4, 24.8],
        [0, 0, 0, 0, 0.5, 0, 1.0, 0.2, 5.0],  # last hour (start+4h) is outside the match
    )
    rd = reading(s, start)
    assert rd.at_utc == start + dt.timedelta(hours=2, minutes=30)
    assert rd.temperature_2m == pytest.approx(28.0)  # midway 28.2 -> 27.8
    assert rd.dew_point_2m == pytest.approx(24.3)
    assert rd.spread == pytest.approx(3.7) and rd.dew_risk == "moderate"
    assert rd.rain_mm == pytest.approx(1.7) and rd.rain_risk == "low"


def test_buckets_and_season() -> None:
    rs = [
        EveningResult(2024, 2.0, 85.0, True),
        EveningResult(2024, 3.0, 80.0, False),
        EveningResult(2024, 2.5, 82.0, True),
        EveningResult(2024, 5.0, 70.0, False),
        EveningResult(2024, 8.0, 60.0, True),
        EveningResult(2024, 1.0, 90.0, None),  # DLS / no result: spread counted, not chase
        EveningResult(2024, None, None, True),  # no weather
    ]
    hi, lo = bucket(rs, True), bucket(rs, False)
    assert (hi.matches, hi.chase_wins, hi.chase_win_pct) == (3, 2, pytest.approx(66.7))
    assert (lo.matches, lo.chase_wins, lo.chase_win_pct) == (2, 1, 50.0)
    s = dew_season(2024, 8, rs)
    assert s.evening_matches == 8 and s.with_weather == 6 and s.high_dew_matches == 4
    assert s.avg_spread == pytest.approx(3.58, abs=0.01)
