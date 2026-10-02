"""Model Lab router on a temp models dir: tiny synthetic telemetry + 5-tree booster + parquet."""

from __future__ import annotations

import gzip
import json
from pathlib import Path

import lightgbm as lgb
import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from p11.analytics import model_lab as svc
from p11.api.app import app

FEATS = ["f0", "f1", "f2", "f3", "f4"]
ROLES = ["WK", "BAT", "BAT", "BAT", "BAT", "AR", "AR", "BOWL", "BOWL", "BOWL", "BOWL"]
V = "lgbm-test-1"


def _summary(model: float, base: float) -> dict:
    pair = {
        "model": model,
        "baseline": base,
        "diff": model - base,
        "ci95": [model - base - 1, model - base + 1],
    }
    return {
        "matches": 2,
        "best_xi_points": pair,
        "hindsight_best_xi_points": 900.0,
        "captain_top2_rate": {"model": 0.5, "baseline": 0.25, "diff": 0.25, "ci95": [0.0, 0.5]},
        "mae": {"model": 18.0, "baseline": 21.0, "diff": -3.0, "ci95": [-4.0, -2.0]},
        "spearman": {"model": 0.3, "baseline": 0.2, "diff": 0.1, "ci95": [0.0, 0.2]},
        "p10_p90_coverage": 0.79,
    }


def _make_run(root: Path, version: str = V, gain_scale: float = 1.0, nl: int = 7) -> None:
    rng = np.random.default_rng(0)
    d = root / version
    d.mkdir(parents=True)
    X = pd.DataFrame(rng.normal(size=(300, 5)), columns=FEATS)
    y = 30 + 10 * X["f0"] + rng.normal(size=300) * 5
    for head in ("mean", "q10", "q50", "q90"):
        params = {"objective": "regression", "num_leaves": nl, "verbose": -1, "num_threads": 1}
        lgb.train(params, lgb.Dataset(X, y), 5).save_model(str(d / f"{head}.txt"))
    rows = []
    for m, (phase, year) in enumerate([("test", 2025), ("walkforward", 2026)]):
        for t in (1, 2):
            for i, role in enumerate(ROLES):
                f = rng.normal(size=5)
                pred = 30 + 10 * f[0]
                rows.append(
                    {
                        "match_id": 9_900_000 + m,
                        "player_id": f"p{m}{t}{i:02d}",
                        "team_id": t,
                        "role": role,
                        "year": year,
                        "phase": phase,
                        **dict(zip(FEATS, f, strict=True)),
                        "total": float(pred + rng.normal() * 10),
                        "pred_mean": pred,
                        "pred_q10": pred - 15,
                        "pred_q50": pred,
                        "pred_q90": pred + 20,
                        "pred_base": 28.0 + i,
                    }
                )
    rows[0]["f1"] = np.nan  # missing values are allowed
    pd.DataFrame(rows).to_parquet(d / "eval_frame.parquet")
    tel = {
        "version": version,
        "created_at": "2026-10-02T12:00:00+00:00" if version == V else "2026-10-03T12:00:00+00:00",
        "duration_s": {"total": 12.5},
        "protocol": {"test_season": 2025, "wf_season": 2026},
        "features": [
            {
                "name": f,
                "group": "G",
                "description": f"feature {f}",
                "importance_gain": (i + 1) * gain_scale,
            }
            for i, f in enumerate(FEATS)
        ],
        "chosen_params": {"num_leaves": nl, "learning_rate": 0.03},
        "trees": {"mean": 5, "q10": 5, "q50": 5, "q90": 5},
        "n_learned_values": 4 * 5 * (2 * nl - 1),
        "evaluations": {
            "test:2025": _summary(700.0, 650.0),
            "walkforward:2026": _summary(710.0, 690.0),
        },
        "per_match": {
            "test:2025": [
                {
                    "match_id": 9_900_000,
                    "team1": "AAA",
                    "team2": "BBB",
                    "date": "2025-04-01",
                    "xi_model": 700.0,
                    "xi_base": 650.0,
                    "xi_best": 900.0,
                }
            ]
        },
        "weird": float("nan"),
    }
    # json.dumps writes NaN literally; the reader must turn it into null
    (d / "telemetry.json").write_text(json.dumps(tel))


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("P11_MODELS_DIR", str(tmp_path))
    monkeypatch.setattr(svc, "_db_runs", lambda: [])
    monkeypatch.setattr(svc, "_match_meta", lambda ids: {})
    monkeypatch.setattr(svc, "_player_refs", lambda ids: {})
    return TestClient(app), tmp_path


def test_runs_empty_when_no_models(client):
    c, _ = client
    r = c.get("/api/v1/model/runs")
    assert r.status_code == 200
    assert r.json() == []


def test_runs_lists_newest_first_with_latest_flag(client):
    c, root = client
    _make_run(root)
    _make_run(root, "lgbm-test-2", gain_scale=2.0, nl=15)
    (root / "latest.json").write_text(json.dumps({"version": V}))
    runs = c.get("/api/v1/model/runs").json()
    assert [r["version"] for r in runs] == ["lgbm-test-2", V]
    assert [r["is_latest"] for r in runs] == [False, True]
    r = runs[1]
    assert r["has_telemetry"] and r["has_eval_frame"] and r["has_booster"]
    assert r["n_features"] == 5 and r["trees"]["mean"] == 5
    assert r["test"]["best_xi_points"]["diff"] == 50.0
    assert r["walkforward"]["key"] == "walkforward:2026"


def test_telemetry_gzip_nan_and_etag(client):
    c, root = client
    _make_run(root)
    r = c.get(f"/api/v1/model/runs/{V}/telemetry", headers={"accept-encoding": "gzip"})
    assert r.status_code == 200
    assert r.headers["content-encoding"] == "gzip"
    body = r.json()  # httpx decodes gzip
    assert body["weird"] is None
    assert body["evaluations"]["test:2025"]["matches"] == 2
    again = c.get(f"/api/v1/model/runs/{V}/telemetry", headers={"if-none-match": r.headers["etag"]})
    assert again.status_code == 304
    raw = c.get(f"/api/v1/model/runs/{V}/telemetry", headers={"accept-encoding": "identity"})
    assert "content-encoding" not in raw.headers
    assert json.loads(raw.content)["version"] == V
    assert gzip.decompress(svc.telemetry(V).gz) == svc.telemetry(V).body


def test_unknown_run_and_bad_version_404(client):
    c, root = client
    _make_run(root)
    assert c.get("/api/v1/model/runs/nope/telemetry").status_code == 404
    assert c.get("/api/v1/model/runs/..%2Fetc/telemetry").status_code in (404, 422)
    assert c.get("/api/v1/model/runs/nope/matches").status_code == 404
    assert c.get(f"/api/v1/model/runs/{V}/matches/1").status_code == 404
    assert c.get("/api/v1/model/compare", params={"a": V, "b": "nope"}).status_code == 404


def test_matches_by_phase(client):
    c, root = client
    _make_run(root)
    test = c.get(f"/api/v1/model/runs/{V}/matches", params={"phase": "test"}).json()
    wf = c.get(f"/api/v1/model/runs/{V}/matches", params={"phase": "walkforward"}).json()
    assert [m["info"]["match_id"] for m in test] == [9_900_000]
    assert [m["info"]["match_id"] for m in wf] == [9_900_001]
    m = test[0]
    assert m["n_players"] == 22
    assert m["xi_model"] == 700.0  # from telemetry per_match
    assert m["info"]["team1"]["code"] == "AAA"  # fallback when the DB has no such match
    assert m["mae_model"] is not None
    assert c.get(f"/api/v1/model/runs/{V}/matches", params={"phase": "cv"}).status_code == 422


def test_match_detail_has_three_xis(client):
    c, root = client
    _make_run(root)
    d = c.get(f"/api/v1/model/runs/{V}/matches/9900000").json()
    assert len(d["players"]) == 22
    for key in ("model", "baseline", "hindsight"):
        xi = d["xi"][key]
        assert len(xi["picks"]) == 11
        assert xi["captain"] and xi["vice_captain"] and xi["captain"] != xi["vice_captain"]
        mults = sorted(p["multiplier"] for p in xi["picks"])
        assert mults[-2:] == [1.5, 2.0]
        assert xi["actual_points"] == pytest.approx(sum(p["points"] for p in xi["picks"]), abs=0.05)
    # hindsight XI is the best achievable with actual points
    assert d["xi"]["hindsight"]["actual_points"] >= d["xi"]["model"]["actual_points"]
    assert d["xi"]["hindsight"]["actual_points"] >= d["xi"]["baseline"]["actual_points"]
    assert sum(p["in_model_xi"] for p in d["players"]) == 11
    assert d["mae_model"] is not None and 0 <= d["coverage"] <= 1


def test_explain_shap_sums_to_prediction(client):
    c, root = client
    _make_run(root)
    for pid in ("p0100", "p0101"):  # p0100 has a missing f1
        e = c.get(
            f"/api/v1/model/runs/{V}/explain", params={"match_id": 9_900_000, "player_id": pid}
        ).json()
        assert len(e["contributions"]) == 5
        total = e["base_value"] + sum(x["shap"] for x in e["contributions"])
        assert total == pytest.approx(e["prediction"], abs=1e-2)
        shaps = [abs(x["shap"]) for x in e["contributions"]]
        assert shaps == sorted(shaps, reverse=True)
        assert e["contributions"][0]["description"].startswith("feature ")
    assert (
        c.get(
            f"/api/v1/model/runs/{V}/explain", params={"match_id": 9_900_000, "player_id": "zz"}
        ).status_code
        == 404
    )


def test_compare_runs(client):
    c, root = client
    _make_run(root)
    _make_run(root, "lgbm-test-2", gain_scale=2.0, nl=15)
    r = c.get("/api/v1/model/compare", params={"a": V, "b": "lgbm-test-2"}).json()
    assert r["a"]["version"] == V and r["b"]["version"] == "lgbm-test-2"
    nl = next(p for p in r["params"] if p["name"] == "num_leaves")
    assert nl == {"name": "num_leaves", "a": 7, "b": 15, "changed": True}
    assert not next(p for p in r["params"] if p["name"] == "learning_rate")["changed"]
    mae = next(m for m in r["metrics"] if m["phase"] == "test" and m["metric"] == "mae")
    assert mae["delta"] == 0 and mae["higher_is_better"] is False
    # gain shares are normalised, so a uniform scale change gives no deltas
    assert all(abs(d["delta"]) < 1e-9 for d in r["importance"])
