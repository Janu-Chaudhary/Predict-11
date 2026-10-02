"""Team squad (latest roster) against the real IPL data (read-only)."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Connection

from p11.analytics import teams_squad
from p11.api.app import app

from .players_live import live  # noqa: F401  (fixture)

pytestmark = pytest.mark.integration

CSK = 53
NOOR, CONWAY, SAMSON = "Noor Ahmad", "Devon Conway", "Sanju Samson"


def test_csk_squad_latest_roster(live: Connection) -> None:  # noqa: F811
    sq = teams_squad.squad(live, CSK)
    assert sq.season == 2026 and sq.team.short_code == "CSK"
    by_name = {p.player.display_name: p for p in sq.players}
    # played every 2026 game; on the 2025 list as an overseas player
    assert by_name[NOOR].matches == 14 and by_name[NOOR].overseas is True
    # on the 2025 list, did not feature in 2026
    assert by_name[CONWAY].matches == 0 and by_name[CONWAY].in_squad_list
    # traded in: played for CSK in 2026 but listed by another team in 2025
    assert by_name[SAMSON].matches > 0 and not by_name[SAMSON].in_squad_list
    assert len({p.player.id for p in sq.players}) == len(sq.players)
    order = [teams_squad.ROLE_ORDER[p.role] for p in sq.players]
    assert order == sorted(order)


def test_players_who_moved_on_are_left_out(live: Connection) -> None:  # noqa: F811
    for team_id in (CSK, 54, 46):  # CSK, RR, RCB
        sq = teams_squad.squad(live, team_id)
        others = {
            p.player.id
            for t in (CSK, 54, 46)
            if t != team_id
            for p in teams_squad.squad(live, t).players
            if p.matches > 0
        }
        assert not others & {p.player.id for p in sq.players if p.matches == 0}


def test_squad_endpoint() -> None:
    client = TestClient(app)
    assert client.get(f"/api/v1/teams/{CSK}/squad").status_code == 200
    assert client.get("/api/v1/teams/999999/squad").status_code == 404
