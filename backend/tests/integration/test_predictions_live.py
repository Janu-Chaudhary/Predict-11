"""Predicted XIs against the real latest model run + IPL data (read-only).

Skipped when the repo has no trained run (models/ is not in git).
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from p11.analytics import model_lab as ml
from p11.api.app import app

pytestmark = pytest.mark.integration

FINAL_2026 = 1535465


@pytest.fixture(scope="module")
def season():
    v = ml.latest_version()
    if v is None or not (ml.models_dir() / v / "eval_frame.parquet").is_file():
        pytest.skip("no trained model run")
    r = TestClient(app).get("/api/v1/predictions/seasons/2026")
    if r.status_code == 404:
        pytest.skip("latest run has no 2026 walk-forward phase")
    assert r.status_code == 200
    return r.json()


def test_season_matches_telemetry(season):
    t = ml.telemetry(season["version"]).data
    k = ml.phase_key(t["evaluations"], "walkforward")
    ev = t["evaluations"][k]
    s = season["summary"]
    assert season["phase"] == "walkforward" and not season["frozen"]
    assert s["matches"] == ev["matches"] == len(season["matches"])
    assert s["model_mean"] == pytest.approx(ev["best_xi_points"]["model"], abs=0.01)
    assert s["baseline_mean"] == pytest.approx(ev["best_xi_points"]["baseline"], abs=0.01)
    assert s["captain_top2_model"] == pytest.approx(ev["captain_top2_rate"]["model"], abs=1e-3)
    dates = [m["match"]["date"] for m in season["matches"]]
    assert dates == sorted(dates) and all(d.startswith("2026") for d in dates)


def test_final_has_header_and_three_xis(season):
    ids = [m["match"]["match_id"] for m in season["matches"]]
    assert FINAL_2026 in ids
    d = TestClient(app).get(f"/api/v1/predictions/matches/{FINAL_2026}").json()
    assert d["match"]["stage"] == "Final" and d["match"]["venue"]["name"]
    assert {d["match"]["team1"]["short_code"], d["match"]["team2"]["short_code"]} == {"GT", "RCB"}
    row = next(m for m in season["matches"] if m["match"]["match_id"] == FINAL_2026)
    assert d["totals"]["model"] == row["model_xi_points"]
    assert all(len(d["xis"][k]["picks"]) == 11 for k in ("model", "baseline", "best"))
    assert all(p["image_url"] for p in d["xis"]["model"]["picks"][:3])
