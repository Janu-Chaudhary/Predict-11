"""Open-Meteo ingest helpers: anchors, windows, parsing (no network, no DB)."""

from __future__ import annotations

import datetime as dt

import pytest

from p11.ingest.weather import VENUE_GEO, anchor_of, parse_hourly, window_hours

UTC = dt.UTC


def test_anchor_real_and_inferred() -> None:
    real = dt.datetime(2026, 4, 12, 14, tzinfo=UTC)
    assert anchor_of(real, "night", dt.date(2026, 4, 12)) == (real, False)
    a, approx = anchor_of(None, "night", dt.date(2019, 4, 1))
    assert approx and a == dt.datetime(2019, 4, 1, 14, 0, tzinfo=UTC)  # 19:30 IST
    a, _ = anchor_of(None, "day", dt.date(2019, 4, 1))
    assert a == dt.datetime(2019, 4, 1, 10, 0, tzinfo=UTC)  # 15:30 IST
    a, _ = anchor_of(None, None, dt.date(2019, 4, 1))
    assert a.hour == 14


def test_window_hours() -> None:
    w = window_hours(dt.datetime(2026, 4, 12, 14, tzinfo=UTC))
    assert len(w) == 9 and w[0].hour == 10 and w[-1].hour == 18
    w = window_hours(dt.datetime(2026, 4, 12, 14, 30, tzinfo=UTC))
    assert len(w) == 10 and w[0].hour == 10 and w[-1].hour == 19


def test_parse_hourly_requires_gmt() -> None:
    p = {
        "utc_offset_seconds": 0,
        "hourly": {
            "time": ["2026-04-12T14:00", "2026-04-12T15:00"],
            "temperature_2m": [28.8, 28.4],
            "dew_point_2m": [24.3, None],
        },
    }
    s = parse_hourly(p)
    t = dt.datetime(2026, 4, 12, 14, tzinfo=UTC)
    assert s[t]["temperature_2m"] == 28.8 and s[t + dt.timedelta(hours=1)]["dew_point_2m"] is None
    with pytest.raises(ValueError):
        parse_hourly({**p, "utc_offset_seconds": 19800})


def test_venue_geo_sane() -> None:
    assert len(VENUE_GEO) == 36
    for name, (lat, lon, src) in VENUE_GEO.items():
        assert src.startswith(("wikipedia:", "wikidata:")), name
        assert -35 < lat < 33 and 18 < lon < 92, name
    assert VENUE_GEO["Wankhede Stadium"][:2] == (18.93889, 72.82583)
