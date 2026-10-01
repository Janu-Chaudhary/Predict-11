"""Match start-time slot helpers (pure)."""

from __future__ import annotations

import datetime as dt

from p11.ingest.start_times import day_night_of, infer_day_night


def test_day_night_of_ist_slots():
    assert day_night_of(dt.datetime(2026, 4, 4, 10, 0, tzinfo=dt.UTC)) == "day"  # 15:30 IST
    assert day_night_of(dt.datetime(2026, 4, 4, 14, 0, tzinfo=dt.UTC)) == "night"  # 19:30
    assert day_night_of(dt.datetime(2008, 4, 18, 14, 30, tzinfo=dt.UTC)) == "night"  # 20:00


def _m(i, day, num):
    return {"id": i, "start_date": dt.date.fromisoformat(day), "match_number": num}


def test_infer_double_header_and_single_days():
    ms = [
        _m(1, "2026-04-04", 9), _m(2, "2026-04-04", 8),  # double-header: lower number first
        _m(3, "2026-04-05", 11),  # single match -> evening
        _m(4, "2026-05-31", None),  # final, no number, alone -> evening
        _m(5, "2026-04-06", None), _m(6, "2026-04-06", 12),  # can't order -> no inference
    ]
    assert infer_day_night(ms) == {1: "night", 2: "day", 3: "night", 4: "night"}
