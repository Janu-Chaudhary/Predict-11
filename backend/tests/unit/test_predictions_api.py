"""Predicted-XI router on a temp models dir (the Model Lab's synthetic run + a cv row)."""

from __future__ import annotations

import json

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from p11.analytics import model_lab as ml
from p11.analytics import predictions as svc
from p11.api.app import app

from .test_model_lab_api import V, _make_run

WF_MATCH, TEST_MATCH, CV_MATCH = 9_900_001, 9_900_000, 9_800_000


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("P11_MODELS_DIR", str(tmp_path))
    monkeypatch.setattr(ml, "_db_runs", lambda: [])
    monkeypatch.setattr(ml, "_match_meta", lambda ids: {})
    monkeypatch.setattr(ml, "_player_refs", lambda ids: {})
    monkeypatch.setattr(svc, "_headers", lambda ids: {})
    monkeypatch.setattr(svc, "_credits", lambda year: (2025, {"p1100": 9.0, "p1201": 8.5}))
    return TestClient(app), tmp_path


def _run(root, with_cv: bool = True) -> None:
    _make_run(root)
    (root / "latest.json").write_text(json.dumps({"version": V}))
    if with_cv:  # cross-validation rows exist in real frames; they are never served
        p = root / V / "eval_frame.parquet"
        df = pd.read_parquet(p)
        cv = df[df["match_id"] == TEST_MATCH].copy()
        cv["match_id"], cv["phase"], cv["year"] = CV_MATCH, "cv", 2024
        cv["player_id"] = "c" + cv["player_id"]
        pd.concat([df, cv]).to_parquet(p)


def test_404_without_a_run(client):
    c, _ = client
    assert c.get("/api/v1/predictions/seasons/2026").status_code == 404
    assert c.get(f"/api/v1/predictions/matches/{WF_MATCH}").status_code == 404


def test_walkforward_season(client):
    c, root = client
    _run(root)
    r = c.get("/api/v1/predictions/seasons/2026")
    assert r.status_code == 200
    d = r.json()
    assert d["phase"] == "walkforward" and d["frozen"] is False
    assert "walk-forward" in d["method_note"] and "credit" in d["credits_note"]
    assert [s["year"] for s in d["seasons"]] == [2026, 2025]
    assert [m["match"]["match_id"] for m in d["matches"]] == [WF_MATCH]
    m = d["matches"][0]
    # no per-match telemetry for 2026 in the synthetic run: XI totals are solved here
    detail = c.get(f"/api/v1/predictions/matches/{WF_MATCH}").json()
    assert m["model_xi_points"] == detail["totals"]["model"]
    assert m["baseline_xi_points"] == detail["totals"]["baseline"]
    assert m["best_xi_points"] == detail["totals"]["best"]
    assert m["best_xi_points"] >= m["model_xi_points"]
    assert m["model_minus_baseline"] == pytest.approx(
        m["model_xi_points"] - m["baseline_xi_points"]
    )
    cap = m["captain"]
    assert cap["player"]["id"] == detail["xis"]["model"]["captain"]
    assert cap["points"] == pytest.approx(2 * cap["actual"])
    assert cap["top2"] == (cap["actual_rank"] <= 2)
    s = d["summary"]
    assert s["matches"] == 1 and s["model_mean"] == m["model_xi_points"]
    assert s["best_call"]["match_id"] == WF_MATCH == s["worst_call"]["match_id"]
    assert s["beat_baseline"] == int(m["model_minus_baseline"] > 0)


def test_test_season_is_flagged_frozen_and_uses_telemetry_totals(client):
    c, root = client
    _run(root)
    d = c.get("/api/v1/predictions/seasons/2025").json()
    assert d["phase"] == "test" and d["frozen"] is True and "frozen" in d["method_note"]
    assert d["matches"][0]["model_xi_points"] == 700.0  # telemetry per_match
    assert c.get("/api/v1/predictions/seasons/2024").status_code == 404


def test_match_detail(client):
    c, root = client
    _run(root)
    d = c.get(f"/api/v1/predictions/matches/{WF_MATCH}").json()
    assert d["phase"] == "walkforward" and d["year"] == 2026 and d["credits_season"] == 2025
    assert len(d["players"]) == 22
    means = [p["pred_mean"] for p in d["players"]]
    assert means == sorted(means, reverse=True)
    ranks = sorted(p["actual_rank"] for p in d["players"])
    assert ranks[0] == 1
    for key in ("model", "baseline", "best"):
        xi = d["xis"][key]
        assert len(xi["picks"]) == 11 and xi["captain"] != xi["vice_captain"]
        assert sorted(p["multiplier"] for p in xi["picks"])[-2:] == [1.5, 2.0]
        assert xi["actual_points"] == pytest.approx(sum(p["points"] for p in xi["picks"]), abs=0.05)
    assert d["xis"]["best"]["actual_points"] >= d["xis"]["model"]["actual_points"]
    assert d["xis"]["best"]["overlap_with_best"] == 11
    model = d["xis"]["model"]
    for p in model["picks"]:
        assert p["selected_on"] == p["pred_mean"]
    # credits: only two synthetic players have them, so the total is partial
    assert model["credits_complete"] is False
    assert d["totals"]["model_share_of_best"] == pytest.approx(
        d["totals"]["model"] / d["totals"]["best"], abs=1e-3
    )


def test_cv_and_unknown_matches_404(client):
    c, root = client
    _run(root)
    assert c.get(f"/api/v1/predictions/matches/{CV_MATCH}").status_code == 404
    assert c.get("/api/v1/predictions/matches/123").status_code == 404
    assert c.get("/api/v1/predictions/matches/0").status_code == 422


def test_optimise_honours_locks_and_excludes(client):
    c, root = client
    _run(root)
    url = f"/api/v1/predictions/matches/{WF_MATCH}/optimise"
    base = c.post(url, json={}).json()
    model = c.get(f"/api/v1/predictions/matches/{WF_MATCH}").json()["xis"]["model"]
    # nothing locked: the same XI as the predicted model XI (uncapped: credits are partial)
    assert {p["player_id"] for p in base["xi"]["picks"]} == {p["player_id"] for p in model["picks"]}
    assert base["credits_constrained"] is False and base["budget"] is None
    cap = base["xi"]["captain"]
    out = next(
        p["player_id"]
        for p in c.get(f"/api/v1/predictions/matches/{WF_MATCH}").json()["players"]
        if not p["in_model_xi"]
    )
    r = c.post(url, json={"locks": [out], "excludes": [cap]}).json()
    ids = {p["player_id"] for p in r["xi"]["picks"]}
    assert out in ids and cap not in ids and len(ids) == 11
    assert r["projected"] <= base["projected"]
    assert c.post(url, json={"locks": ["nope"]}).status_code == 422
    assert c.post(url, json={"locks": [cap], "excludes": [cap]}).status_code == 422
    assert c.post(f"/api/v1/predictions/matches/{CV_MATCH}/optimise", json={}).status_code == 404
