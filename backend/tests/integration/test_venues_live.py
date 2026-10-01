"""Venue cards against the real IPL data (catalog §4 E2, read-only)."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Connection

from p11.analytics.venues import venue_card, venue_list
from p11.api.app import app

from .players_live import live  # noqa: F401  (fixture)

pytestmark = pytest.mark.integration

CHEPAUK, WANKHEDE = 162, 154


def test_par_scores_match_catalog(live: Connection) -> None:  # noqa: F811
    chepauk, wankhede = venue_card(live, CHEPAUK), venue_card(live, WANKHEDE)
    assert chepauk is not None and wankhede is not None
    # catalog 2023-26: Chepauk avg 173 / median 175 / chase 61%; Wankhede avg 197 / median 205
    assert 168 <= (chepauk.recent.avg_first_innings or 0) <= 178
    assert 190 <= (wankhede.recent.avg_first_innings or 0) <= 204
    assert chepauk.recent.avg_first_innings < wankhede.recent.avg_first_innings  # type: ignore[operator]
    assert chepauk.recent.chase_win_pct == pytest.approx(61, abs=2)
    # scoring inflation: the recent par is above the all-time par
    assert wankhede.recent.avg_first_innings > wankhede.all_time.avg_first_innings  # type: ignore[operator]
    assert any("pace vs spin" in n.lower() for n in chepauk.notes)


def test_venue_card_consistency(live: Connection) -> None:  # noqa: F811
    card = venue_card(live, WANKHEDE)
    assert card is not None
    assert card.toss_all_time.chose_bat + card.toss_all_time.chose_field == card.matches
    assert card.highest_totals[0].runs >= card.highest_totals[-1].runs
    assert card.lowest_totals[0].runs <= card.lowest_totals[-1].runs
    assert len(card.top_run_scorers) == 5 and len(card.top_wicket_takers) == 5
    assert sum(s.matches for s in card.by_season) == card.matches
    pp = {p.phase: p for p in card.phases_recent}
    assert pp["death"].run_rate > pp["middle"].run_rate  # type: ignore[operator]


def test_venue_list_and_endpoints(live: Connection) -> None:  # noqa: F811
    vl = venue_list(live)
    assert len(vl.venues) >= 30
    assert sum(v.matches for v in vl.venues) >= 1200
    c = TestClient(app)
    assert c.get("/api/v1/venues").status_code == 200
    assert c.get(f"/api/v1/venues/{CHEPAUK}").json()["name"] == "MA Chidambaram Stadium"
    assert c.get("/api/v1/venues/999999").status_code == 404
