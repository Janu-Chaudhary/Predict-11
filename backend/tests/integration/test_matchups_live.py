"""Batter-v-bowler H2H against the real IPL data (catalog §4 E1, read-only)."""

from __future__ import annotations

import datetime as dt

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Connection

from p11.analytics.matchups import head_to_head
from p11.api.app import app

from .players_live import live  # noqa: F401  (fixture)

pytestmark = pytest.mark.integration

KOHLI, BUMRAH = "ba607b88", "462411b3"


@pytest.mark.parametrize(
    ("batter", "bowler", "balls", "runs", "outs", "matches"),
    [
        (KOHLI, BUMRAH, 108, 159, 5, 18),
        ("740742ef", "9d430b40", 137, 145, 8, 22),  # RG Sharma v SP Narine
        ("4a8a2e3b", BUMRAH, 65, 62, 4, 16),  # MS Dhoni v JJ Bumrah
        (KOHLI, "57ee1fde", 54, 72, 2, 7),  # V Kohli v YS Chahal
        ("99b75528", "5f547c8b", 50, 30, 4, 9),  # JC Buttler v Rashid Khan
    ],
)
def test_catalog_pairs(
    live: Connection,  # noqa: F811
    batter: str,
    bowler: str,
    balls: int,
    runs: int,
    outs: int,
    matches: int,
) -> None:
    p = head_to_head(live, batter, bowler).pair
    assert p is not None
    assert (p.balls, p.runs, p.dismissals, p.matches) == (balls, runs, outs, matches)
    assert sum(s.balls for s in p.by_season) == balls
    assert sum(p.how_out.values()) == outs


def test_kohli_bumrah_detail(live: Connection) -> None:  # noqa: F811
    r = head_to_head(live, KOHLI, BUMRAH)
    p = r.pair
    assert p is not None
    assert p.fours + p.sixes == 22
    assert p.confidence == "high"
    assert len(p.last_encounters) == 5
    dates = [e.date for e in p.last_encounters]
    assert dates == sorted(dates, reverse=True)
    assert any(row.player.id == BUMRAH for row in r.top_bowlers_vs_batter + r.top_batters_vs_bowler)
    assert all(row.balls >= 12 for row in r.top_bowlers_vs_batter)


def test_since_filter_shrinks_sample(live: Connection) -> None:  # noqa: F811
    p = head_to_head(live, KOHLI, BUMRAH, since=dt.date(2023, 1, 1)).pair
    assert p is not None
    assert p.balls == 16 and all(s.season >= 2023 for s in p.by_season)


def test_h2h_endpoint(live: Connection) -> None:  # noqa: F811
    c = TestClient(app)
    r = c.get(f"/api/v1/h2h?batter={KOHLI}&bowler={BUMRAH}")
    assert r.status_code == 200
    assert r.json()["pair"]["balls"] == 108
    r = c.get(f"/api/v1/h2h?bowler={BUMRAH}&min_balls=30&sort=strike_rate&limit=3")
    rows = r.json()["top_batters_vs_bowler"]
    assert len(rows) == 3 and all(x["balls"] >= 30 for x in rows)
    assert c.get("/api/v1/h2h").status_code == 422
