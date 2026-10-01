"""Home endpoints against the real IPL data (read-only)."""

from __future__ import annotations

import datetime as dt

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Connection

from p11.analytics import home
from p11.analytics.home_phase import IST
from p11.api.app import app

from .players_live import live  # noqa: F401  (fixture)

pytestmark = pytest.mark.integration

FINAL_2026 = 1535465


def test_off_season_state_points_at_the_2026_final(live: Connection) -> None:  # noqa: F811
    st = home.home_state(live, dt.datetime(2026, 10, 2, 12, tzinfo=IST))
    assert st.phase == "off_season" and st.hero == "C"
    assert st.next_fixture is None
    assert st.hero_match_id == FINAL_2026
    assert st.last_match is not None and st.last_match.result == "RCB won by 5 wickets"
    assert st.season is not None and st.season.champion is not None
    assert st.season.champion.short_code == "RCB" and st.season.next_season.startswith("IPL 2027")


def test_post_match_falls_back_to_c_without_shot_data(live: Connection) -> None:  # noqa: F811
    st = home.home_state(live, dt.datetime(2026, 6, 1, 9, tzinfo=IST))
    assert st.phase == "post_match" and st.hero == "C" and st.hero_match_id == FINAL_2026
    st = home.home_state(live, dt.datetime(2026, 6, 1, 9, tzinfo=IST), dev_spike_wagon=True)
    assert st.hero == "A"


def test_worm_matches_scorecard(live: Connection) -> None:  # noqa: F811
    w = home.worm(live, FINAL_2026)
    gt, rcb = w.innings
    assert (gt.team.short_code, gt.runs, gt.wickets, gt.overs) == ("GT", 155, 8, "20")
    assert (rcb.team.short_code, rcb.runs, rcb.wickets, rcb.overs) == ("RCB", 161, 5, "18")
    assert w.ball_count == 233 == len(gt.balls) + len(rcb.balls)
    assert gt.balls[-1].runs == 155 and gt.balls[-1].x == pytest.approx(20)
    assert sum(b.kind == "wicket" for b in gt.balls) == 8
    assert all(a.runs <= b.runs for a, b in zip(gt.balls, gt.balls[1:], strict=False))
    assert w.y_max >= 161


def test_api_contract(live: Connection) -> None:  # noqa: F811
    c = TestClient(app)
    r = c.get("/api/v1/home/state")
    assert r.status_code == 200 and r.json()["hero"] in {"A", "B", "C"}
    assert c.get(f"/api/v1/home/worm/{FINAL_2026}").status_code == 200
    assert c.get("/api/v1/home/worm/1").status_code == 404
    assert c.get(f"/api/v1/home/wagon/{FINAL_2026}").status_code == 404
    r = c.get(f"/api/v1/home/wagon/{FINAL_2026}?dev_spike_wagon=true")
    assert r.status_code == 200
    body = r.json()
    assert (body["batter"], body["runs"], body["balls"], body["not_out"]) == (
        "V Kohli",
        75,
        42,
        True,
    )
    assert sum(s["runs"] for s in body["shots"]) == 75
    assert c.get(f"/api/v1/home/xi/{FINAL_2026}").status_code in {200, 204}
    t = c.get("/api/v1/home/tiles").json()
    assert t["table"]["season"] == 2026 and t["records"]["runs"] >= 250
