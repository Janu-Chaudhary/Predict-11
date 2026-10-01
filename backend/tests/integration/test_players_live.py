"""Player analytics against the real IPL data (read-only)."""

from __future__ import annotations

import statistics
import time

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Connection

from p11.analytics import players, players_records
from p11.analytics.players_data import bulk, player_balls, reference
from p11.analytics.players_stats import batting_cards, bowling_cards, fielding
from p11.api.app import app

from .players_live import live  # noqa: F401  (fixture)

pytestmark = pytest.mark.integration

KOHLI, BUMRAH, DHONI, PANDYA, RABADA = "ba607b88", "462411b3", "4a8a2e3b", "dbe50b21", "e62dd25d"


def test_kohli_career_matches_public_figures(live: Connection) -> None:  # noqa: F811
    # Public IPL record after the 2025 season: 8,661 runs in 259 innings, 8 hundreds, HS 113.
    upto_2025 = players.profile(live, KOHLI, since=None)
    assert upto_2025 is not None
    seasons = {s.season: s for s in upto_2025.by_season}
    runs_2025 = sum(s.batting.runs for y, s in seasons.items() if y <= 2025)
    inns_2025 = sum(s.batting.innings for y, s in seasons.items() if y <= 2025)
    hundreds_2025 = sum(s.batting.hundreds for y, s in seasons.items() if y <= 2025)
    assert (runs_2025, inns_2025, hundreds_2025) == (8661, 259, 8)
    assert upto_2025.batting.highest == "113*"
    assert upto_2025.bowling.wickets == 4
    assert upto_2025.last_team == "Royal Challengers Bengaluru"


def test_public_figures_bumrah_dhoni(live: Connection) -> None:  # noqa: F811
    ref, bk = reference(live), bulk(live)

    def upto(cards, season):  # type: ignore[no-untyped-def]
        return [c for c in cards if ref.matches[c.match_id].season <= season]

    assert sum(c.wickets for c in upto(bk.bowling[BUMRAH], 2025)) == 183
    assert sum(c.runs for c in upto(bk.batting[DHONI], 2025)) == 5439


@pytest.mark.parametrize("pid", [KOHLI, BUMRAH, DHONI])
def test_bulk_sql_cards_equal_python_definitions(live: Connection, pid: str) -> None:  # noqa: F811
    """The cached SQL cards and the pure-Python ball aggregation must agree exactly."""
    balls = player_balls(live, pid)
    bk = bulk(live)
    assert batting_cards(balls, pid) == bk.batting.get(pid, [])
    assert bowling_cards(balls, pid) == bk.bowling.get(pid, [])
    f = fielding(balls, pid)
    fsum = players.sum_fielding(bk.fielding.get(pid, {}).values())
    assert (f.catches, f.stumpings, f.run_outs) == (fsum.catches, fsum.stumpings, fsum.run_outs)


def test_dhoni_phase_split_is_death_heavy(live: Connection) -> None:  # noqa: F811
    p = players.profile(live, DHONI, since=None)
    assert p is not None
    ph = {x.phase: x for x in p.batting_phases}
    assert ph["death"].balls > ph["middle"].balls > ph["powerplay"].balls
    assert sum(x.balls for x in p.batting_phases) == p.batting.balls
    assert sum(x.runs for x in p.batting_phases) == p.batting.runs


def test_season_filter_and_compare(live: Connection) -> None:  # noqa: F811
    res = players.compare(live, [KOHLI, BUMRAH], season=2026)
    k = next(x for x in res.players if x.id == KOHLI)
    assert k.batting.runs == sum(
        s.batting.runs
        for s in players.profile(live, KOHLI).by_season
        if s.season == 2026  # type: ignore[union-attr]
    )
    assert k.matches <= 17


def test_search_prioritises_ipl_players(live: Connection) -> None:  # noqa: F811
    hits = players.search(live, "kohli").results
    assert hits[0].id == KOHLI and hits[0].matches > 250
    assert players.search(live, "Virat").results[0].id == KOHLI  # via alias
    assert all(h.matches == 0 for h in hits[hits.index(next(h for h in hits if h.matches == 0)) :])


def test_milestones_catalog_examples(live: Connection) -> None:  # noqa: F811
    ms = players_records.milestones(live, 2026).milestones
    texts = {(m.player.id, m.stat): m for m in ms}
    assert texts[(RABADA, "wickets")].current == 148
    assert texts[(RABADA, "wickets")].needed == 2
    assert texts[(PANDYA, "runs")].current == 2955
    assert texts[(PANDYA, "runs")].text == "HH Pandya needs 45 for 3,000 IPL runs"


def test_streaks_shape(live: Connection) -> None:  # noqa: F811
    res = players_records.streaks(live, season=None)
    boards = {b.type: b for b in res.boards}
    assert set(boards) == {"score30", "wicket", "no_duck"}
    for b in boards.values():
        assert all(e.length >= 2 for e in b.current + b.longest)
        assert [e.length for e in b.longest] == sorted((e.length for e in b.longest), reverse=True)
        assert all(e.active for e in b.current)


URLS = [
    "/api/v1/players/search?q=sharma",
    f"/api/v1/players/{KOHLI}",
    f"/api/v1/players/{BUMRAH}?since=2023",
    f"/api/v1/players/compare?ids={KOHLI},{BUMRAH},{DHONI}",
    "/api/v1/milestones",
    "/api/v1/streaks",
    "/api/v1/streaks?season=2026&type=wicket",
]


@pytest.mark.parametrize("url", URLS)
def test_endpoints_respond_fast_when_warm(live: Connection, url: str) -> None:  # noqa: F811
    client = TestClient(app)
    assert client.get(url).status_code == 200  # warm caches
    times = []
    for _ in range(3):
        t = time.perf_counter()
        r = client.get(url)
        times.append((time.perf_counter() - t) * 1000)
        assert r.status_code == 200
    assert statistics.median(times) < 300, f"{url}: {times}"


def test_endpoint_errors(live: Connection) -> None:  # noqa: F811
    client = TestClient(app)
    assert client.get("/api/v1/players/nope1234").status_code == 404
    assert client.get("/api/v1/players/compare?ids=").status_code == 422
    assert client.get(f"/api/v1/players/compare?ids={KOHLI},nope1234").status_code == 404
    assert client.get(f"/api/v1/players/{KOHLI}?since=last-year").status_code == 422
    assert client.get("/api/v1/streaks?type=bogus").status_code == 422
