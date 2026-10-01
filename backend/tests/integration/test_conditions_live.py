"""Conditions endpoints against the live IPL DB (read-only; weather must be backfilled)."""

from __future__ import annotations

import datetime as dt
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Connection, text

from p11.analytics.conditions import batter_vs_types, bowler_vs_hands, pace_spin, toss_trend
from p11.analytics.conditions_weather import dew_report, match_conditions
from p11.analytics.matchups import head_to_head
from p11.analytics.venues import venue_card
from p11.api.app import app

from .players_live import live  # noqa: F401  (fixture)

pytestmark = pytest.mark.integration

KOHLI, BUMRAH = "ba607b88", "462411b3"
WANKHEDE = 154
RCB_MI_2026 = 1527693  # Wankhede, 2026-04-12, 19:30 IST (14:00 UTC)
SAMPLE = Path(__file__).resolve().parents[3] / "spikes/misc/samples/openmeteo_archive.json"


def _has_weather(conn: Connection) -> bool:
    return bool(conn.execute(text("SELECT count(*) FROM match_weather")).scalar_one())


def test_batter_vs_types_consistent_with_h2h(live: Connection) -> None:  # noqa: F811
    r = batter_vs_types(live, KOHLI)
    assert r is not None and r.batting_hand == "R"
    typed = sum(t.balls for t in r.by_type)
    assert typed == sum(g.balls for g in r.by_group) == r.coverage.balls_known
    assert r.coverage.balls - r.coverage.balls_known >= 0
    # the Bumrah pair is a subset of Kohli's right-arm-fast balls
    pair = head_to_head(live, KOHLI, BUMRAH).pair
    assert pair is not None
    rf = next(t for t in r.by_type if t.bowling_type == "right-arm fast")
    assert rf.balls >= pair.balls and rf.confidence == "high"
    recent = batter_vs_types(live, KOHLI, dt.date(2023, 1, 1))
    assert recent is not None and recent.coverage.balls < r.coverage.balls


def test_bowler_vs_hands(live: Connection) -> None:  # noqa: F811
    r = bowler_vs_hands(live, BUMRAH)
    assert r is not None and r.bowling_type == "right-arm fast" and r.group == "pace"
    rhb, lhb = r.by_hand
    assert rhb.balls > lhb.balls > 300
    assert rhb.balls + lhb.balls == r.coverage.balls_known
    assert bowler_vs_hands(live, "nobody00") is None


def test_toss_trend_matches_venue_card(live: Connection) -> None:  # noqa: F811
    t, card = toss_trend(live, WANKHEDE), venue_card(live, WANKHEDE)
    assert t is not None and card is not None
    assert sum(s.matches for s in t.seasons) == card.matches == t.all_time.matches
    assert t.all_time.toss_field_pct == card.toss_all_time.field_pct
    assert t.recent.chase_win_pct == card.recent.chase_win_pct


def test_pace_spin_split(live: Connection) -> None:  # noqa: F811
    p = pace_spin(live, 162)  # Chepauk: spin-friendly
    assert p is not None
    g = {x.group: x for x in p.all_time.groups}
    assert g["spin"].economy < g["pace"].economy  # type: ignore[operator]
    assert (p.all_time.unknown_ball_pct or 0) < 1
    assert sum(x.balls for x in p.all_time.by_type) + g["unknown"].balls == sum(
        x.balls for x in p.all_time.groups
    )


def test_weather_matches_openmeteo_sample(live: Connection) -> None:  # noqa: F811
    if not _has_weather(live):
        pytest.skip("match_weather is empty (run `p11 weather backfill`)")
    mc = match_conditions(live, RCB_MI_2026)
    assert mc is not None and mc.start_approx is False
    assert mc.start_utc == dt.datetime(2026, 4, 12, 14, tzinfo=dt.UTC)
    assert len(mc.hourly) == 9
    # The sample was requested with timezone=Asia/Kolkata: Open-Meteo labels the UTC hour by its
    # IST clock truncated to the hour, so label "19:00" = 14:00 UTC (= 19:30 IST).
    s = json.loads(SAMPLE.read_text())
    h = s["hourly"]
    sample = {
        dt.datetime.fromisoformat(t).replace(tzinfo=dt.UTC) - dt.timedelta(hours=5): i
        for i, t in enumerate(h["time"])
    }
    checked = 0
    for w in mc.hourly:
        i = sample.get(w.time_utc)
        if i is None:
            continue
        checked += 1
        assert w.temperature_2m == pytest.approx(h["temperature_2m"][i], abs=0.25)
        assert w.dew_point_2m == pytest.approx(h["dew_point_2m"][i], abs=0.25)
        assert w.relative_humidity_2m == pytest.approx(h["relative_humidity_2m"][i], abs=1.5)
        assert w.wind_speed_10m == pytest.approx(h["wind_speed_10m"][i], abs=0.5)
        assert w.precipitation == pytest.approx(h["precipitation"][i], abs=0.1)
    assert checked == 9  # the whole window lies inside the sample day
    assert mc.reading is not None and mc.reading.dew_risk in ("high", "moderate")


def test_dew_report(live: Connection) -> None:  # noqa: F811
    if not _has_weather(live):
        pytest.skip("match_weather is empty")
    d = dew_report(live, WANKHEDE)
    assert d is not None
    tot = d.total
    assert tot.evening_matches == sum(s.evening_matches for s in d.seasons)
    assert tot.high_dew.matches + tot.low_dew.matches <= tot.with_weather
    assert dew_report(live, 999999) is None


def test_routes(live: Connection) -> None:  # noqa: F811
    c = TestClient(app)
    assert c.get(f"/api/v1/matchups/batter/{KOHLI}/vs-bowling-types?since=2023").status_code == 200
    assert c.get("/api/v1/matchups/batter/zzzz/vs-bowling-types").status_code == 404
    assert c.get(f"/api/v1/matchups/batter/{KOHLI}/vs-bowling-types?since=x").status_code == 422
    assert c.get(f"/api/v1/matchups/bowler/{BUMRAH}/vs-batting-hand").status_code == 200
    for p in ("toss-trend", "pace-spin", "dew"):
        assert c.get(f"/api/v1/venues/{WANKHEDE}/{p}").status_code == 200
        assert c.get(f"/api/v1/venues/999999/{p}").status_code == 404
    assert c.get(f"/api/v1/matches/{RCB_MI_2026}/conditions").status_code == 200
    assert c.get("/api/v1/matches/1/conditions").status_code == 404
    far = (dt.datetime.now(dt.UTC) + dt.timedelta(days=60)).isoformat()
    assert c.get(f"/api/v1/venues/{WANKHEDE}/forecast", params={"at": far}).status_code == 422
    assert c.get(f"/api/v1/venues/{WANKHEDE}/forecast?at=nope").status_code == 422
