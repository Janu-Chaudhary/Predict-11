"""Integration tests against the built DuckDB. Skipped if the pipeline hasn't
been run yet (so a fresh clone doesn't fail before `predict11 all`)."""
import duckdb
import pytest

from predict11.config import DUCKDB_PATH

pytestmark = pytest.mark.skipif(not DUCKDB_PATH.exists(), reason="run `predict11 all` first")


@pytest.fixture(scope="module")
def con():
    c = duckdb.connect(str(DUCKDB_PATH), read_only=True)
    yield c
    c.close()


def _tables(con):
    return {r[0] for r in con.execute("SHOW TABLES").fetchall()}


def test_core_tables_populated(con):
    for t in ("matches", "deliveries", "playing_xi", "player_match_points"):
        if t in _tables(con):
            assert con.execute(f"SELECT count(*) FROM {t}").fetchone()[0] > 0


def test_features_have_no_leakage_for_debutants(con):
    if "player_match_features" not in _tables(con):
        pytest.skip("features not built")
    # a player's first match must carry zero prior history
    rows = con.execute(
        "SELECT career_fp_mean, last5_fp_mean FROM player_match_features WHERE career_games = 0"
    ).fetchall()
    assert rows, "expected some debut rows"
    assert all(cfp == 0.0 and l5 == 0.0 for cfp, l5 in rows)


def test_fantasy_points_are_bounded(con):
    if "player_match_points" not in _tables(con):
        pytest.skip("points not built")
    mx, mn = con.execute("SELECT max(fp), min(fp) FROM player_match_points").fetchone()
    assert mx < 400 and mn > -50  # sane fantasy-point range


def test_predict_fixture_returns_valid_xi():
    res = __import__("predict11.api.service", fromlist=["predict_fixture"]).predict_fixture(
        "mumbai-indians", "chennai-super-kings"
    )
    assert res["status"] == "ok"
    assert len(res["xi"]) == 11
    assert res["total_credits"] <= 100.0
    assert sum(p["is_captain"] for p in res["xi"]) == 1
