"""Fantasy-points model: LightGBM mean + p10/p50/p90 quantile heads on point-in-time features.

Protocol (owner decision 2026-10-02):
- **Tuning**: rolling-origin folds over 2020-2024 (train on seasons < Y, validate on Y). The
  number of trees is chosen by early stopping on the *last training season* (inner, time-based),
  never on the fold being scored. Hyper-parameters are picked by mean fold MAE of the mean head.
- **Test**: one model trained on 2008-2024 with the chosen settings, scored once on 2025.
- **Walk-forward 2026**: retrain on everything before each block of ``WF_BLOCK`` matches, then
  predict the block (features are point-in-time anyway), i.e. how the live product behaves.

Metrics per evaluated set (each with a paired bootstrap CI against the last-5-form baseline):
best-XI actual points (optimiser on predictions, Dream11 rules, no credits), captain top-2
hit-rate, MAE per player, within-match Spearman, p10-p90 coverage.
"""

from __future__ import annotations

import itertools
import json
import math
import time
from collections.abc import Iterable
from dataclasses import asdict, dataclass, field
from pathlib import Path

import lightgbm as lgb
import numpy as np
import pandas as pd

from ..features.build import FEATURES, TARGET
from ..optimize.xi import Candidate, Infeasible, Options, Selection, solve

QUANTILES = (0.1, 0.5, 0.9)
HEADS = ("mean", "q10", "q50", "q90")
RECENCY_HALFLIFE_SEASONS = 3.0
CV_SEASONS = (2020, 2021, 2022, 2023, 2024)
TEST_SEASON = 2025
WF_SEASON = 2026
WF_BLOCK = 10  # matches per walk-forward retrain
MAX_TREES = 3000
EARLY_STOP = 100
INNER_MATCHES = 74  # inner validation: the last ~one season of matches in the training set
CURVE_POINTS = 600
BOOTSTRAP = 2000
SEED = 11

GRID = {
    "num_leaves": (15, 31),
    "min_child_samples": (40, 100),
    "learning_rate": (0.03,),
}
BASE_PARAMS = {
    "feature_fraction": 0.8,
    "bagging_fraction": 0.8,
    "bagging_freq": 1,
    "lambda_l2": 1.0,
    "verbose": -1,
    "seed": SEED,
    "num_threads": 4,
}


@dataclass
class Fitted:
    params: dict
    trees: dict[str, int]
    boosters: dict[str, lgb.Booster] = field(repr=False)
    # per head: inner train / valid loss per iteration (downsampled), metric, best iteration
    curves: dict[str, dict] = field(default_factory=dict, repr=False)

    def predict(self, X: pd.DataFrame) -> pd.DataFrame:
        out = pd.DataFrame({h: self.boosters[h].predict(X[FEATURES]) for h in HEADS}, index=X.index)
        q = np.sort(out[["q10", "q50", "q90"]].to_numpy(), axis=1)  # no crossing
        out[["q10", "q50", "q90"]] = q
        return out

    def n_learned_by_head(self) -> dict[str, int]:
        """Leaf values + split thresholds per head (the model's 'parameters')."""
        out = {}
        for h, b in self.boosters.items():
            n = 0
            for t in b.dump_model()["tree_info"]:
                leaves = t["num_leaves"]
                n += leaves + (leaves - 1)
            out[h] = n
        return out

    def n_learned_values(self) -> int:
        return sum(self.n_learned_by_head().values())


def _objective(head: str) -> dict:
    if head == "mean":
        return {"objective": "regression"}
    return {"objective": "quantile", "alpha": int(head[1:]) / 100}


def _weights(years: pd.Series, ref_year: int) -> np.ndarray:
    return np.power(0.5, (ref_year - years.to_numpy()) / RECENCY_HALFLIFE_SEASONS)


def _downsample(xs: list[float], n: int = CURVE_POINTS) -> list[float]:
    if len(xs) <= n:
        return [round(float(x), 4) for x in xs]
    idx = np.linspace(0, len(xs) - 1, n).round().astype(int)
    return [round(float(xs[i]), 4) for i in idx]


def fit(train: pd.DataFrame, params: dict) -> Fitted:
    """Fit all heads. Trees per head: early stopping on the last INNER_MATCHES matches of
    ``train`` (inner, time-based validation), then a refit on all of ``train`` with that many
    trees. Recency weights are relative to the newest training season."""
    seqs = np.sort(train["seq"].unique())
    cut = seqs[-INNER_MATCHES] if len(seqs) > INNER_MATCHES else seqs[0]
    inner_tr, inner_va = train[train["seq"] < cut], train[train["seq"] >= cut]
    last = int(train["year"].max())
    boosters: dict[str, lgb.Booster] = {}
    trees: dict[str, int] = {}
    curves: dict[str, dict] = {}
    for head in HEADS:
        obj = _objective(head)
        p = {**BASE_PARAMS, **params, **obj}
        dtr = lgb.Dataset(
            inner_tr[FEATURES], inner_tr[TARGET], weight=_weights(inner_tr["year"], last)
        )
        dva = lgb.Dataset(inner_va[FEATURES], inner_va[TARGET], reference=dtr)
        rec: dict = {}
        b = lgb.train(
            p,
            dtr,
            MAX_TREES,
            valid_sets=[dtr, dva],
            valid_names=["train", "valid"],
            callbacks=[
                lgb.early_stopping(EARLY_STOP, verbose=False),
                lgb.record_evaluation(rec),
            ],
        )
        n = max(50, b.best_iteration or MAX_TREES)
        metric = next(iter(rec["valid"]))
        curves[head] = {
            "train": _downsample(rec["train"][metric]),
            "valid": _downsample(rec["valid"][metric]),
            "metric": metric,
            "best_iter": int(b.best_iteration or 0),
            "iters": len(rec["valid"][metric]),
        }
        full = lgb.Dataset(train[FEATURES], train[TARGET], weight=_weights(train["year"], last))
        boosters[head] = lgb.train(p, full, n)
        trees[head] = n
    return Fitted(params=params, trees=trees, boosters=boosters, curves=curves)


# --------------------------------------------------------------------------- evaluation
def baseline(df: pd.DataFrame) -> pd.Series:
    """Last-5-form rule (mean of the last 5 IPL games, 0 without history)."""
    return df["mean_5"].fillna(0.0)


def best_xi(m: pd.DataFrame, value: str) -> tuple[float, Selection | None]:
    """Optimiser XI on column ``value`` (Dream11 rules, no credits) and its *actual* points."""
    pool = [
        Candidate(r.player_id, r.team_id, r.role, float(getattr(r, value)))
        for r in m.itertuples(index=False)
    ]
    try:
        sel = solve(pool, options=Options(use_credits=False))
    except Infeasible:
        return math.nan, None
    actual = dict(zip(m["player_id"], m[TARGET], strict=True))
    tot = sum(actual[p.candidate.player] * p.multiplier for p in sel.picks)
    return float(tot), sel


def _best_xi(m: pd.DataFrame, value: str) -> tuple[float, str | None, list[str]]:
    tot, sel = best_xi(m, value)
    return tot, (sel.captain if sel else None), (sel.players if sel else [])


@dataclass
class MatchEval:
    match_id: int
    xi_model: float
    xi_base: float
    xi_best: float
    cap_hit_model: bool
    cap_hit_base: bool
    mae_model: float
    mae_base: float
    rho_model: float
    rho_base: float
    covered: float


def evaluate_matches(df: pd.DataFrame) -> list[MatchEval]:
    """``df`` has TARGET, pred_mean/q10/q90 and pred_base per player row."""
    out = []
    for mid, m in df.groupby("match_id", sort=False):
        top2 = set(m.nlargest(2, TARGET)["player_id"])
        xm, cm, _ = _best_xi(m, "pred_mean")
        xb, cb, _ = _best_xi(m, "pred_base")
        xbest, _, _ = _best_xi(m, TARGET)
        y = m[TARGET].to_numpy(float)
        out.append(
            MatchEval(
                match_id=int(mid),  # type: ignore[call-overload]
                xi_model=xm,
                xi_base=xb,
                xi_best=xbest,
                cap_hit_model=cm in top2,
                cap_hit_base=cb in top2,
                mae_model=float(np.abs(m["pred_mean"] - y).mean()),
                mae_base=float(np.abs(m["pred_base"] - y).mean()),
                rho_model=float(m["pred_mean"].rank().corr(m[TARGET].rank())),
                rho_base=float(m["pred_base"].rank().corr(m[TARGET].rank())),
                covered=float(((y >= m["pred_q10"]) & (y <= m["pred_q90"])).mean()),
            )
        )
    return out


def _ci(diff: np.ndarray, rng: np.random.Generator) -> tuple[float, float]:
    diff = diff[~np.isnan(diff)]
    if len(diff) == 0:
        return math.nan, math.nan
    idx = rng.integers(0, len(diff), size=(BOOTSTRAP, len(diff)))
    means = diff[idx].mean(axis=1)
    return float(np.percentile(means, 2.5)), float(np.percentile(means, 97.5))


def summarise(evals: list[MatchEval]) -> dict:
    e = pd.DataFrame([asdict(x) for x in evals])
    rng = np.random.default_rng(SEED)

    def pair(a: str, b: str) -> dict:
        d = e[a].to_numpy(float) - e[b].to_numpy(float)
        lo, hi = _ci(d, rng)
        return {
            "model": round(float(e[a].mean()), 3),
            "baseline": round(float(e[b].mean()), 3),
            "diff": round(float(np.nanmean(d)), 3),
            "ci95": [round(lo, 3), round(hi, 3)],
        }

    return {
        "matches": len(e),
        "best_xi_points": pair("xi_model", "xi_base"),
        "hindsight_best_xi_points": round(e["xi_best"].mean(), 1),
        "captain_top2_rate": pair("cap_hit_model", "cap_hit_base"),
        "mae": pair("mae_model", "mae_base"),
        "spearman": pair("rho_model", "rho_base"),
        "p10_p90_coverage": round(e["covered"].mean(), 3),
    }


def with_preds(rows: pd.DataFrame, fitted: Fitted) -> pd.DataFrame:
    p = fitted.predict(rows)
    out = rows.copy()
    for h in HEADS:
        out[f"pred_{h}"] = p[h]
    out["pred_base"] = baseline(rows)
    return out


# --------------------------------------------------------------------------- protocol
def grid() -> Iterable[dict]:
    keys = list(GRID)
    for vals in itertools.product(*(GRID[k] for k in keys)):
        yield dict(zip(keys, vals, strict=True))


def tune(
    df: pd.DataFrame,
    log=print,  # type: ignore[no-untyped-def]
) -> tuple[dict, list[dict], pd.DataFrame, dict[str, dict]]:
    """Rolling-origin search over GRID. Returns (best params, all results, the best params'
    out-of-fold predictions for CV_SEASONS, the best params' training curves per fold)."""
    results = []
    best: tuple[float, dict, pd.DataFrame, dict[str, dict]] | None = None
    for params in grid():
        t = time.time()
        maes: dict[str, float] = {}
        parts, curves = [], {}
        for y in CV_SEASONS:
            f = fit(df[df["year"] < y], params)
            va = with_preds(df[df["year"] == y], f)
            maes[str(y)] = round(float(np.abs(va["pred_mean"] - va[TARGET]).mean()), 3)
            parts.append(va)
            curves[f"cv:{y}"] = f.curves
        r = {
            "params": params,
            "fold_mae": maes,
            "mean_mae": round(float(np.mean(list(maes.values()))), 4),
            "seconds": round(time.time() - t, 1),
        }
        log(f"  {params} -> MAE {r['mean_mae']:.3f} {maes} ({r['seconds']}s)")
        results.append(r)
        if best is None or r["mean_mae"] < best[0]:
            best = (r["mean_mae"], params, pd.concat(parts), curves)
    assert best is not None
    return best[1], results, best[2], best[3]


def cv_report(oof: pd.DataFrame) -> dict:
    """Full metric set per CV season from out-of-fold predictions."""
    return {
        str(y): summarise(evaluate_matches(oof[oof["year"] == y]))
        for y in sorted(oof["year"].unique())
    }


def walk_forward(
    df: pd.DataFrame,
    params: dict,
    season: int = WF_SEASON,
    log=print,  # type: ignore[no-untyped-def]
) -> tuple[pd.DataFrame, list[dict]]:
    """Predict ``season`` in blocks of WF_BLOCK matches, retraining on everything before each
    block. Returns (predictions, per-block timeline)."""
    season_rows = df[df["year"] == season]
    seqs = sorted(season_rows["seq"].unique())
    parts, timeline = [], []
    for i in range(0, len(seqs), WF_BLOCK):
        block = seqs[i : i + WF_BLOCK]
        train = df[df["seq"] < block[0]]
        f = fit(train, params)
        pr = with_preds(season_rows[season_rows["seq"].isin(block)], f)
        ev = evaluate_matches(pr)
        timeline.append(
            {
                "block": i // WF_BLOCK + 1,
                "first_match_seq": int(block[0]),
                "n_matches": len(block),
                "train_rows": len(train),
                "mae": round(float(np.abs(pr["pred_mean"] - pr[TARGET]).mean()), 3),
                "xi_model": round(float(np.nanmean([e.xi_model for e in ev])), 1),
                "xi_base": round(float(np.nanmean([e.xi_base for e in ev])), 1),
                "trees": f.trees,
            }
        )
        log(f"  walk-forward block {timeline[-1]['block']}: {timeline[-1]}")
        parts.append(pr)
    return pd.concat(parts), timeline


def importance(fitted: Fitted, top: int = 15) -> list[tuple[str, float]]:
    b = fitted.boosters["mean"]
    gain = b.feature_importance("gain")
    tot = gain.sum() or 1.0
    pairs = sorted(zip(FEATURES, gain / tot, strict=True), key=lambda x: -x[1])
    return [(k, round(float(v), 3)) for k, v in pairs[:top]]


def save(fitted: Fitted, out_dir: Path, meta: dict) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    for h, b in fitted.boosters.items():
        b.save_model(str(out_dir / f"{h}.txt"))
    (out_dir / "meta.json").write_text(
        json.dumps(
            {**meta, "features": FEATURES, "trees": fitted.trees, "params": fitted.params},
            indent=2,
            default=str,
        )  # fmt: skip
    )
