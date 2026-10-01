"""Seasons API against the real compose database (read-only).

Skipped when Postgres is unreachable. Expected values were checked against published IPL
tables (Sportskeeda sample in spikes/live/samples) and docs/FEATURE-CATALOG.md §4.
"""

from __future__ import annotations

import json
import time
from collections.abc import Callable
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from p11.analytics import seasons, seasons_data
from p11.api.app import app
from p11.core import db

pytestmark = pytest.mark.integration

REPO = Path(__file__).resolve().parents[3]
SAMPLE = REPO / "spikes/live/samples/sportskeeda_ipl_points_table.json"


@pytest.fixture(scope="module")
def client() -> TestClient:
    if not db.ping():
        pytest.skip("compose Postgres not reachable")
    seasons_data.core()  # one-off cold load (~1.5 s); requests are then served from memory
    seasons_data.players()
    return TestClient(app)


def _get(client: TestClient, url: str) -> dict | list:
    r = client.get("/api/v1" + url)
    assert r.status_code == 200, r.text
    return r.json()


def test_2026_table_matches_official(client: TestClient) -> None:
    body = _get(client, "/seasons/2026/table")
    rows = body["rows"]
    assert [r["team"]["short_code"] for r in rows[:4]] == ["RCB", "GT", "SRH", "RR"]
    assert all(r["played"] == 14 for r in rows)
    official = json.loads(SAMPLE.read_text())["table"][0]["table"][0]["group"]
    ours = {r["team"]["short_code"]: r for r in rows}
    for o in official:
        r = ours[o["team_short_name"]]
        assert r["position"] == int(o["position"])
        assert (r["won"], r["lost"], r["no_result"]) == (o["won"], o["lost"], o["no_result"])
        assert r["points"] == int(o["points"])
        assert r["nrr"] == pytest.approx(float(o["nrr"]), abs=0.0005)


def test_every_season_top4_are_the_playoff_teams(client: TestClient) -> None:
    for s in _get(client, "/seasons"):
        year = s["year"]
        table = _get(client, f"/seasons/{year}/table")["rows"]
        playoff_stages = {"Semi Final", "Qualifier 1", "Eliminator", "Elimination Final"}
        ms = _get(client, f"/matches?season={year}")
        po = {t["id"] for m in ms if m["stage"] in playoff_stages for t in (m["team1"], m["team2"])}
        assert {r["team"]["id"] for r in table[:4]} == po, year
        assert len({r["played"] for r in table}) == 1, year  # abandoned games filled in


def test_seasons_and_teams(client: TestClient) -> None:
    seasons = _get(client, "/seasons")
    assert [s["year"] for s in seasons] == list(range(2008, 2027))
    by = {s["year"]: s for s in seasons}
    assert by[2026]["champion"]["short_code"] == "RCB"
    assert by[2009]["champion"]["name"] == "Deccan Chargers"
    teams = {t["short_code"]: t for t in _get(client, "/teams")}
    assert {"CSK", "MI", "RCB", "KKR", "DC", "PBKS", "RR", "SRH", "GT", "LSG"} <= set(teams)
    assert {"RPS", "GL", "KTK", "PWI"} <= set(teams)
    assert teams["SRH"]["former_names"][0]["short_code"] == "DCH"
    assert teams["CSK"]["titles"] == [2010, 2011, 2018, 2021, 2023]


def test_story_2026_caps(client: TestClient) -> None:
    story = _get(client, "/seasons/2026/story")
    orange = story["orange_cap"]["leaders"][0]
    assert (orange["player"]["name"], orange["total"]) == ("V Suryavanshi", 776)
    assert orange["cumulative"][-1] == 776
    assert len(story["orange_cap"]["dates"]) == len(orange["cumulative"])
    purple = story["purple_cap"]["leaders"][0]
    assert (purple["player"]["name"], purple["total"]) == ("K Rabada", 29)
    assert story["most_sixes"][0]["player"]["name"] == "V Suryavanshi"


def test_records_all_time(client: TestClient) -> None:
    rec = _get(client, "/records")
    assert rec["most_runs"][0]["player"]["name"] == "V Kohli"
    top = rec["highest_individual_scores"][0]
    assert (top["player"]["name"], top["runs"], top["not_out"]) == ("CH Gayle", 175, True)
    p = rec["highest_partnerships"][0]
    assert {p["batter1"]["name"], p["batter2"]["name"]} == {"V Kohli", "AB de Villiers"}
    assert p["runs"] == 229
    assert rec["lowest_totals"][0]["runs"] == 49
    assert rec["fastest_hundreds"][0]["balls"] == 30
    season = _get(client, "/records?scope=season&season=2026")
    assert season["most_runs"][0]["runs"] == 776


def test_scenarios_replay_2026(client: TestClient) -> None:
    sc = _get(client, "/seasons/2026/scenarios?after_match=56")
    assert sc["method"] == "exhaustive" and sc["remaining_matches"] == 14
    teams = {t["team"]["short_code"]: t for t in sc["teams"]}
    assert teams["MI"]["eliminated"] and teams["LSG"]["eliminated"]
    assert not any(t["eliminated"] for c, t in teams.items() if c not in {"MI", "LSG"})
    assert teams["GT"]["p_top4"] == pytest.approx(0.876, abs=0.001)
    final = _get(client, "/seasons/2026/scenarios")
    assert final["remaining_matches"] == 0
    assert {t["team"]["short_code"] for t in final["teams"] if t["clinched_top4"]} == {
        "RCB", "GT", "SRH", "RR",
    }  # fmt: skip
    early = _get(client, "/seasons/2026/scenarios?after_match=30")
    assert early["method"] == "monte_carlo" and early["outcomes_evaluated"] == 100_000


def test_scenarios_with_picks(client: TestClient) -> None:
    sc = _get(client, "/seasons/2026/scenarios?after_match=56")
    picks = [{"match_id": f["match_id"], "winner_id": f["actual_winner_id"]}
             for f in sc["remaining"] if f["actual_winner_id"]]  # fmt: skip
    r = client.post("/api/v1/seasons/2026/scenarios", json={"after_match": 56, "picks": picks})
    assert r.status_code == 200, r.text
    teams = {t["team"]["short_code"]: t for t in r.json()["teams"]}
    assert all(teams[c]["clinched_top4"] for c in ("RCB", "GT", "SRH", "RR"))
    bad = client.post(
        "/api/v1/seasons/2026/scenarios",
        json={"after_match": 56, "picks": [{"match_id": 1, "winner_id": 1}]},
    )
    assert bad.status_code == 422


def test_head_to_head(client: TestClient) -> None:
    h = _get(client, "/teams/CSK/vs/MI")
    assert h["played"] == h["team_a_won"] + h["team_b_won"] + h["no_result"]
    assert len(h["last5"]) == 5
    assert sum(v["played"] for v in h["by_venue"]) == h["played"]
    old = _get(client, "/teams/RCB/vs/DCH?season=2009")
    assert old["team_b"]["short_code"] == "DCH" and old["played"] >= 1
    assert client.get("/api/v1/teams/CSK/vs/XYZ").status_code == 404


def test_matches_and_etag(client: TestClient) -> None:
    r = client.get("/api/v1/matches?season=2026&team=RCB")
    assert r.status_code == 200
    ms = r.json()
    assert len(ms) == 16 and ms[-1]["stage"] == "Final"
    assert ms[-1]["result_text"].startswith("Royal Challengers Bengaluru won")
    etag = r.headers["etag"]
    again = client.get("/api/v1/matches?season=2026&team=RCB", headers={"If-None-Match": etag})
    assert again.status_code == 304


@pytest.mark.parametrize(
    "url",
    [
        "/seasons",
        "/teams",
        "/seasons/2026/table",
        "/seasons/2026/story",
        "/teams/CSK/vs/MI?venue=1",
        "/records?venue=1",
        "/matches?season=2026",
    ],
)
def test_latency_under_300ms(client: TestClient, url: str) -> None:
    t = time.perf_counter()
    r = client.get("/api/v1" + url)
    assert r.status_code == 200
    assert time.perf_counter() - t < 0.3


def test_worst_case_exhaustive_scenarios_under_300ms(client: TestClient) -> None:
    """20 open matches = 2^20 outcomes, computed fresh (bypassing the memo); best of 3 so a
    busy CI box does not flake."""
    best = min(_timed(lambda: seasons.scenarios(2026, 50)) for _ in range(3))
    assert best < 0.3


def _timed(fn: Callable[[], object]) -> float:
    t = time.perf_counter()
    fn()
    return time.perf_counter() - t
