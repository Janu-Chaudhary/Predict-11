"""/players/percentiles against the real IPL data (read-only)."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Connection

from p11.api.app import app

from .players_live import live  # noqa: F401  (fixture)

pytestmark = pytest.mark.integration

KOHLI, BUMRAH = "ba607b88", "462411b3"


def test_percentiles_shape_and_sanity(live: Connection) -> None:  # noqa: F811
    client = TestClient(app)
    body = client.get(f"/api/v1/players/percentiles?ids={KOHLI},{BUMRAH}").json()
    assert [p["id"] for p in body["players"]] == [KOHLI, BUMRAH]
    assert all(a["population"] > 100 for a in body["axes"])
    kohli = {a["key"]: a for a in body["players"][0]["axes"]}
    bumrah = {a["key"]: a for a in body["players"][1]["axes"]}
    assert kohli["runs_per_inns"]["percentile"] > 90
    assert kohli["economy"]["percentile"] is None  # too few balls bowled to rank
    assert bumrah["economy"]["percentile"] > 80
    assert bumrah["wickets_per_inns"]["percentile"] > 70
    for p in body["players"]:
        for a in p["axes"]:
            assert a["percentile"] is None or 0 <= a["percentile"] <= 100


def test_percentiles_rejects_unknown_and_bad_input(live: Connection) -> None:  # noqa: F811
    client = TestClient(app)
    assert client.get("/api/v1/players/percentiles?ids=zzzzzzzz").status_code == 404
    assert client.get("/api/v1/players/percentiles?ids=").status_code == 422
    assert client.get(f"/api/v1/players/percentiles?ids={KOHLI}&since=nope").status_code == 422
