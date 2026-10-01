"""Fantasy API against the real compose database (read-only; skipped when unreachable).

Totals are cross-checked by recomputing from ``player_match_points`` directly in SQL.
"""

from __future__ import annotations

import time
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from p11.analytics import fantasy_data
from p11.api.app import app
from p11.core import db
from p11.optimize.xi import ROLES, Candidate, Options, pulp_solver, solve

pytestmark = pytest.mark.integration

FINAL_2026 = 1535465
KOHLI = "ba607b88"


@pytest.fixture(scope="module")
def client() -> TestClient:
    if not db.ping():
        pytest.skip("compose Postgres not reachable")
    fantasy_data.data()  # one-off cold load
    return TestClient(app)


def _get(client: TestClient, url: str) -> Any:
    r = client.get("/api/v1" + url)
    assert r.status_code == 200, r.text
    return r.json()


def _sql(sql: str, **kw: Any) -> list[Any]:
    with db.engine().connect() as c:
        return list(c.execute(text(sql), kw))


def _check_xi(xi: dict, match_id: int) -> None:
    actual = dict(
        _sql("select player_id, total from player_match_points where match_id = :m", m=match_id)
    )
    ids = [p["player"]["id"] for p in xi["players"]]
    assert len(ids) == 11 == len(set(ids))
    recomputed = sum(actual[p["player"]["id"]] * p["multiplier"] for p in xi["players"])
    assert xi["total"] == pytest.approx(recomputed)
    mults = sorted(p["multiplier"] for p in xi["players"])
    assert mults[-2:] == [1.5, 2.0]
    roles = [p["role"] for p in xi["players"]]
    assert all(1 <= roles.count(r) <= 8 for r in ROLES)
    assert max(xi["team_counts"].values()) <= 10


def test_2026_final_best_xi(client: TestClient) -> None:
    body = _get(client, f"/fantasy/matches/{FINAL_2026}/best-xi")
    best = body["best"]
    assert best["captain"] == KOHLI
    kohli = best["players"][0]
    assert kohli["player"]["id"] == KOHLI and kohli["points"] == 151 and kohli["multiplier"] == 2
    _check_xi(best, FINAL_2026)
    _check_xi(body["naive_form"], FINAL_2026)
    assert best["total"] >= body["naive_form"]["total"]
    assert body["gap"] == pytest.approx(best["total"] - body["naive_form"]["total"])
    # unconstrained optimum is an upper bound of the credit-limited one
    bwc = body["best_with_credits"]
    assert body["credits_season"] == 2025 and bwc is not None
    assert bwc["credits_used"] <= 100 and bwc["total"] <= best["total"]
    _check_xi(bwc, FINAL_2026)


def test_best_xi_is_optimal_vs_unconstrained_top11(client: TestClient) -> None:
    # any XI <= top-11 sum + top1 + 0.5*top2; equality when the top 11 already satisfy roles
    for (mid,) in _sql(
        "select m.id from match m join season s on s.id = m.season_id "
        "where s.year = 2026 and m.result <> 'no_result' order by m.start_date limit 8"
    ):
        body = _get(client, f"/fantasy/matches/{mid}/best-xi")
        vals = sorted(
            (r[0] for r in _sql("select total from player_match_points where match_id=:m", m=mid)),
            reverse=True,
        )
        bound = sum(vals[:11]) + vals[0] + 0.5 * vals[1]
        assert body["best"]["total"] <= bound + 1e-9
        _check_xi(body["best"], mid)


def test_no_result_match(client: TestClient) -> None:
    (mid,) = _sql(
        "select m.id from match m join season s on s.id=m.season_id "
        "where s.year=2026 and m.result='no_result' limit 1"
    )[0]
    body = _get(client, f"/fantasy/matches/{mid}/best-xi")
    assert body["no_result"] and body["best"] is None and body["naive_form"] is None
    assert client.get("/api/v1/fantasy/matches/1/best-xi").status_code == 404


def test_leaderboard_2026_matches_sql(client: TestClient) -> None:
    body = _get(client, "/fantasy/leaderboard?season=2026&min_matches=1&limit=500")
    top = _sql(
        """select pmp.player_id, sum(pmp.total), count(*) from player_match_points pmp
           join match m on m.id = pmp.match_id join season s on s.id = m.season_id
           where s.year = 2026 and m.result <> 'no_result'
           group by 1 order by 2 desc limit 5"""
    )
    got = [(r["player"]["id"], r["total"], r["n"]) for r in body["rows"][:5]]
    assert got == [tuple(t) for t in top]
    assert body["rows"][0]["player"]["name"] == "V Suryavanshi"
    assert body["credits_season"] == 2025 and body["players_with_credits"] > 100
    cons = _get(client, "/fantasy/leaderboard?season=2026&sort=consistency&min_matches=10")
    cvs = [r["cv"] for r in cons["rows"]]
    assert cvs == sorted(cvs)
    wk = _get(client, "/fantasy/leaderboard?season=2026&role=WK")
    assert wk["rows"] and all(r["role"] == "WK" for r in wk["rows"])
    ppc = _get(client, "/fantasy/leaderboard?season=2026&sort=ppc")["rows"]
    assert ppc[0]["points_per_credit"] == max(r["points_per_credit"] or 0 for r in ppc)


def test_player_distribution(client: TestClient) -> None:
    body = _get(client, f"/fantasy/players/{KOHLI}?season=2026")
    d = body["distribution"]
    n, tot = _sql(
        """select count(*), sum(total) from player_match_points pmp join match m on m.id=match_id
           join season s on s.id=m.season_id
           where player_id=:p and s.year=2026 and m.result<>'no_result'""",
        p=KOHLI,
    )[0]
    assert (d["n"], d["total"]) == (n, tot)
    assert d["floor"] == d["p10"] and d["ceiling"] == d["p90"]
    mix = body["category_mix"]
    assert sum(mix[k] for k in ("batting", "bowling", "fielding", "lineup", "bonuses")) == tot
    assert len(body["last10"]) == 10 and body["last10"][-1]["match_id"] == FINAL_2026
    assert body["credits"] is not None and body["points_per_credit"] is not None
    career = _get(client, f"/fantasy/players/{KOHLI}")
    assert {s["season"] for s in career["seasons"]} >= {2008, 2026}
    assert client.get("/api/v1/fantasy/players/nobody").status_code == 404


def test_team_of_season_and_season_xis(client: TestClient) -> None:
    tos = _get(client, "/fantasy/seasons/2026/team-of-season")
    for xi in (tos["by_total"], tos["by_mean"]):
        roles = [p["role"] for p in xi["players"]]
        assert len(roles) == 11 and all(1 <= roles.count(r) <= 8 for r in ROLES)
    assert tos["by_total"]["players"][0]["player"]["name"] == "V Suryavanshi"
    assert all(p["matches"] >= 7 for p in tos["by_mean"]["players"])

    s = _get(client, "/fantasy/seasons/2026/best-xis")
    n_scored = _sql(
        "select count(*) from match m join season s on s.id=m.season_id "
        "where s.year=2026 and m.result<>'no_result'"
    )[0][0]
    assert len(s["matches"]) == n_scored
    final = next(m for m in s["matches"] if m["match_id"] == FINAL_2026)
    single = _get(client, f"/fantasy/matches/{FINAL_2026}/best-xi")
    assert final["best_total"] == single["best"]["total"]
    assert final["naive_total"] == single["naive_form"]["total"]
    assert all(m["best_total"] >= m["naive_total"] for m in s["matches"])
    assert all(
        m["best_with_credits_total"] is None or m["best_with_credits_total"] <= m["best_total"]
        for m in s["matches"]
    )


@pytest.mark.skipif(pulp_solver() is None, reason="no PuLP MILP solver installed")
def test_pulp_and_exact_agree_on_real_matches(client: TestClient) -> None:
    d = fantasy_data.data()
    for m in d.core.season_matches(2025)[:15]:
        if m.result == "no_result":
            continue
        sc = d.credits_for(2025)
        pool = [
            Candidate(r.player_id, r.team_id, r.role, float(r.total), sc.credits.get(r.player_id))
            for r in d.by_match[m.id]
            if r.player_id in sc.credits
        ]
        a = solve(pool, options=Options(solver="pulp"))
        b = solve(pool, options=Options(solver="exact"))
        assert a.total == pytest.approx(b.total)


def test_warm_timings(client: TestClient) -> None:
    urls = [
        f"/fantasy/players/{KOHLI}",
        f"/fantasy/players/{KOHLI}?season=2026",
        "/fantasy/leaderboard?season=2026",
        "/fantasy/leaderboard?season=2025&sort=ppc&role=BOWL",
        f"/fantasy/matches/{FINAL_2026}/best-xi",
        "/fantasy/seasons/2026/team-of-season",
        "/fantasy/seasons/2026/best-xis",
    ]
    for u in urls:
        _get(client, u)  # warm
    for u in urls:
        t = time.perf_counter()
        _get(client, u)
        assert time.perf_counter() - t < 0.3, u
