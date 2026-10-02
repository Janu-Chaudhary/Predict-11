# ruff: noqa: E501  (markdown report templates)
"""End-to-end model run: features -> tuning (rolling origin) -> 2025 test -> 2026 walk-forward
-> artifacts (models/<version>/), DB rows (model_run, player_match_prediction) and the
markdown report (docs/MODEL-REPORT.md). ``p11 model train`` / ``p11 model report``.
"""

from __future__ import annotations

import datetime as dt
import json
import time
from typing import Any

import pandas as pd
from sqlalchemy import Connection, text

from ..core.settings import REPO_ROOT
from ..features.build import FEATURES, TARGET, build
from . import train as T

MODELS_DIR = REPO_ROOT / "models"
REPORT = REPO_ROOT / "docs" / "MODEL-REPORT.md"

FEATURE_GROUPS: dict[str, list[str]] = {
    "Fantasy form": [
        "n_prev", "mean_all", "mean_3", "mean_5", "mean_10", "mean_20", "ewm_5", "sd_10",
        "max_10", "p50plus_10", "plow_10", "batting_10", "bowling_10", "fielding_10",
        "season_n", "season_mean", "seasons_played", "days_rest",
    ],
    "Batting craft & opportunity": [
        "bat_pos_last", "bat_pos_5", "batted_rate_10", "sr_10", "avg_10", "bpi_10",
        "bdry_pct_10", "six_rate_10", "sr_car", "avg_car", "bpi_car", "bdry_pct_car",
        "six_rate_car", "bat_pp_share_10", "bat_mid_share_10", "bat_death_share_10",
    ],
    "Bowling craft & opportunity": [
        "bowled_rate_10", "econ_10", "wpm_10", "bsr_10", "dot_pct_10", "overs_pm_10", "econ_car",
        "wpm_car", "bsr_car", "dot_pct_car", "overs_pm_car", "bowl_pp_share_10",
        "bowl_death_share_10",
    ],
    "Fielding": ["field_dis_10"],
    "Matchups vs announced XI": [
        "sr_v_spin", "sr_v_pace", "econ_v_L", "econ_v_R", "opp_spin_share", "opp_left_share",
        "opp_attack", "opp_batting", "exp_sr_matchup", "exp_econ_matchup",
    ],
    "Team context": [
        "team_bat_depth_excl", "rank_in_team", "team_scored_10", "team_conceded_10",
        "opp_scored_10", "opp_conceded_10", "home_share", "team_rest",
    ],
    "Venue / opponent history": [
        "venue_n", "venue_mean_shrunk", "venue_lift", "opp_n", "opp_mean_shrunk", "opp_lift",
    ],
    "Conditions": [
        "venue_par_20", "venue_matches", "venue_par_rel", "league_par_60", "bats_first",
        "won_toss", "temp", "humidity", "dew_point", "dew_spread", "wind", "rain", "night",
    ],
    "Attributes & era": [
        "role_code", "left_hand", "bowl_grp_code", "impact_era", "year", "match_number", "playoff",
    ],
}  # fmt: skip


def _persist(
    conn: Connection, version: str, run: dict, preds: pd.DataFrame, telemetry: dict
) -> int:
    conn.execute(
        text(
            """INSERT INTO model_run
                 (version, params, metrics, features, n_learned_values, telemetry, notes)
               VALUES (:v, cast(:p AS jsonb), cast(:m AS jsonb), cast(:f AS jsonb), :n,
                       cast(:t AS jsonb), :notes)"""
        ),
        {
            "v": version,
            "p": json.dumps({"params": run["params"], "trees": run["trees"]}),
            "m": json.dumps(run["metrics"], default=str),
            "f": json.dumps(FEATURES),
            "n": run["n_learned_values"],
            "t": json.dumps(telemetry, default=str),
            "notes": run.get("notes"),
        },
    )
    rows = [
        {
            "v": version,
            "m": int(r.match_id),
            "p": r.player_id,
            "ph": r.phase,
            "mean": round(float(r.pred_mean), 2),
            "p10": round(float(r.pred_q10), 2),
            "p50": round(float(r.pred_q50), 2),
            "p90": round(float(r.pred_q90), 2),
            "b": round(float(r.pred_base), 2),
        }  # fmt: skip
        for r in preds.itertuples(index=False)
    ]
    conn.execute(
        text(
            """INSERT INTO player_match_prediction
            (model_version, match_id, player_id, phase, mean, p10, p50, p90, baseline)
            VALUES (:v, :m, :p, :ph, :mean, :p10, :p50, :p90, :b)"""
        ),
        rows,
    )
    return len(rows)


EVAL_COLS = ["match_id", "player_id", "team_id", "opp_id", "year", "date", "role", "phase", TARGET]
PRED_COLS = ["pred_mean", "pred_q10", "pred_q50", "pred_q90", "pred_base"]


def _new_version() -> str:
    base = "lgbm-" + dt.datetime.now().strftime("%Y%m%d-%H%M")
    v, k = base, 1
    while (MODELS_DIR / v).exists():  # never overwrite an older run
        k += 1
        v = f"{base}-{k}"
    return v


def train_all(conn: Connection, log=print) -> dict[str, Any]:  # type: ignore[no-untyped-def]
    from .telemetry import build_telemetry, now_iso

    t0 = time.time()
    created_at = now_iso()
    version = _new_version()
    dur: dict[str, float] = {}
    log(f"[{version}] building features…")
    df = build(conn)
    df = df[df[TARGET].notna()].reset_index(drop=True)
    dur["build"] = time.time() - t0
    log(f"  {len(df):,} rows x {len(FEATURES)} features in {dur['build']:.0f}s")

    t = time.time()
    log(f"tuning (rolling origin over {T.CV_SEASONS})…")
    params, grid_results, oof, cv_curves = T.tune(df, log)
    dur["tune"] = time.time() - t
    log(f"  chosen {params}")
    t = time.time()
    cv = T.cv_report(oof)
    dur["cv"] = time.time() - t

    t = time.time()
    log(f"test: fit <= {T.TEST_SEASON - 1}, score {T.TEST_SEASON}…")
    final = T.fit(df[df["year"] < T.TEST_SEASON], params)
    test = T.with_preds(df[df["year"] == T.TEST_SEASON], final)
    test_evals = T.evaluate_matches(test)
    test_metrics = T.summarise(test_evals)
    dur["test"] = time.time() - t

    t = time.time()
    log(f"walk-forward {T.WF_SEASON} (retrain every {T.WF_BLOCK} matches)…")
    wf, timeline = T.walk_forward(df, params, T.WF_SEASON, log)
    wf_evals = T.evaluate_matches(wf)
    wf_metrics = T.summarise(wf_evals)
    dur["walkforward"] = time.time() - t

    log("serving model on every season…")
    serve = T.fit(df, params)
    out_dir = MODELS_DIR / version
    run = {
        "version": version,
        "created_at": created_at,
        "params": params,
        "trees": serve.trees,
        "test_trees": final.trees,
        "n_learned_values": serve.n_learned_values(),
        "rows": len(df),
        "metrics": {
            "cv": cv,
            "test_2025": test_metrics,
            "walkforward_2026": wf_metrics,
            "grid": grid_results,
        },  # fmt: skip
        "importance": T.importance(final),
    }
    T.save(serve, out_dir, {k: v for k, v in run.items() if k != "metrics"})
    # the 2008-2024 test model too: the Lab explains 2025 predictions with it
    for h, b in final.boosters.items():
        b.save_model(str(out_dir / f"test_{h}.txt"))

    preds = pd.concat(
        [oof.assign(phase="cv"), test.assign(phase="test"), wf.assign(phase="walkforward")]
    )
    cols = list(dict.fromkeys(EVAL_COLS + FEATURES + PRED_COLS))  # "year" is both id and feature
    preds[cols].to_parquet(out_dir / "eval_frame.parquet", index=False)

    dur["total"] = time.time() - t0
    run["seconds"] = round(dur["total"])
    ctx = {
        "df": df, "final": final, "serve": serve, "test": test, "wf": wf, "version": version,
        "created_at": created_at, "durations": dur, "cv": cv, "cv_curves": cv_curves,
        "test_metrics": test_metrics, "wf_metrics": wf_metrics, "test_evals": test_evals,
        "wf_evals": wf_evals, "grid": grid_results, "params": params, "timeline": timeline,
    }  # fmt: skip
    log("telemetry…")
    telemetry = build_telemetry(conn, ctx)
    tpath = out_dir / "telemetry.json"
    tpath.write_text(json.dumps(telemetry, default=str))
    (out_dir / "metrics.json").write_text(json.dumps(run["metrics"], indent=2, default=str))
    meta = json.loads((out_dir / "meta.json").read_text())
    (out_dir / "meta.json").write_text(json.dumps({**meta, "seconds": run["seconds"]}, indent=2))

    n = _persist(conn, version, run, preds, telemetry)
    (MODELS_DIR / "latest.json").write_text(
        json.dumps(
            {"version": version, "created_at": created_at, "dir": f"models/{version}"}, indent=2
        )
    )
    log(
        f"  stored {n:,} predictions; artifacts in {out_dir}; telemetry {tpath.stat().st_size / 1e6:.1f} MB"
    )
    REPORT.write_text(render(run))
    log(f"report -> {REPORT} ({run['seconds']}s total)")
    return run


# --------------------------------------------------------------------------- report
def _row(name: str, m: dict) -> str:
    def pair(key: str, fmt: str = "{:.1f}") -> str:
        x = m[key]
        lo, hi = x["ci95"]
        return (
            f"{fmt.format(x['model'])} vs {fmt.format(x['baseline'])} "
            f"(Δ {x['diff']:+.2f}, 95% CI {lo:+.2f}…{hi:+.2f})"
        )

    return (
        f"| {name} | {m['matches']} | {pair('best_xi_points')} | {m['hindsight_best_xi_points']:.0f} "
        f"| {pair('captain_top2_rate', '{:.1%}')} | {pair('mae', '{:.2f}')} "
        f"| {pair('spearman', '{:.3f}')} | {m['p10_p90_coverage']:.1%} |"
    )


def _verdicts(m: dict) -> list[str]:
    """One line per evaluated set: which differences vs the baseline are significant (95% CI
    excludes 0, in the direction that favours the model)."""
    better = {"best_xi_points": 1, "captain_top2_rate": 1, "mae": -1, "spearman": 1}
    label = {"best_xi_points": "best-XI points", "captain_top2_rate": "captain top-2 rate",
             "mae": "MAE", "spearman": "within-match ranking"}  # fmt: skip
    out = []
    sets = [
        (f"Test {T.TEST_SEASON}", m["test_2025"]),
        (f"Walk-forward {T.WF_SEASON}", m["walkforward_2026"]),
    ]
    sets += [(f"CV {y}", v) for y, v in m["cv"].items()]
    for name, v in sets:
        win, lose, tie = [], [], []
        for k, sign in better.items():
            lo, hi = v[k]["ci95"]
            if sign * lo > 0 and sign * hi > 0:
                win.append(label[k])
            elif sign * lo < 0 and sign * hi < 0:
                lose.append(label[k])
            else:
                tie.append(label[k])
        parts = []
        if win:
            parts.append("significantly better on " + ", ".join(win))
        if lose:
            parts.append("significantly worse on " + ", ".join(lose))
        if tie:
            parts.append("no significant difference on " + ", ".join(tie))
        out.append(f"- **{name}**: model vs last-5 — " + "; ".join(parts) + ".")
    return out


def render(run: dict) -> str:
    m = run["metrics"]
    head = (
        "| Set | Matches | Best-XI points: model vs last-5 | Hindsight best XI | Captain top-2 "
        "| MAE / player | Spearman (within match) | p10–p90 coverage |\n"
        "|---|---|---|---|---|---|---|---|"
    )
    lines = [
        f"# Fantasy-points model — `{run['version']}`",
        "",
        "_Generated by `p11 model train`. Dream11 T20 points per player per IPL match, predicted "
        "at the toss (XIs known)._",
        "",
        "## Protocol",
        f"- Training data: IPL 2008–2024, {run['rows']:,} player-match rows overall "
        "(no-results and fielding-only subs excluded); recency weights halve every "
        f"{T.RECENCY_HALFLIFE_SEASONS:g} seasons.",
        f"- Tuning: rolling origin over {', '.join(map(str, T.CV_SEASONS))} (train on seasons < Y, "
        f"score Y); trees chosen by early stopping on the last {T.INNER_MATCHES} *training* "
        "matches (about one season; never the scored fold). Grid: " + json.dumps(T.GRID) + ".",
        f"- Test: one model on 2008–2024, scored once on {T.TEST_SEASON}.",
        f"- Walk-forward: {T.WF_SEASON} predicted in blocks of {T.WF_BLOCK} matches, retraining "
        "on everything before each block.",
        "- Baseline: last-5-form (mean of the player's last 5 IPL games; 0 for debutants).",
        "- Best XI: Dream11 rules (11 players, 1–8 per role, max 10 per team, C ×2 / VC ×1.5, no "
        "credit cap) solved on the predictions, scored on actual points. CIs: paired bootstrap "
        f"over matches ({T.BOOTSTRAP} resamples).",
        "",
        "## Model",
        "- LightGBM gradient-boosted trees, four heads: mean (L2) + quantiles p10 / p50 / p90 "
        "(pinball loss; sorted so they never cross).",
        f"- Chosen parameters: `{json.dumps(run['params'])}` + fixed "
        f"`{json.dumps({k: v for k, v in T.BASE_PARAMS.items() if k not in ('verbose', 'seed')})}`.",
        f"- Trees per head (serving model, trained on ≤{T.WF_SEASON}): `{json.dumps(run['trees'])}`;"
        f" test model: `{json.dumps(run['test_trees'])}`.",
        f"- Learned values (leaf values + split thresholds, all heads): **{run['n_learned_values']:,}**.",
        f"- Features: **{len(FEATURES)}** point-in-time features (see below). Run time "
        f"{run['seconds'] // 60} min.",
        "",
        "## Results",
        head,
        _row(f"Test {T.TEST_SEASON}", m["test_2025"]),
        _row(f"Walk-forward {T.WF_SEASON}", m["walkforward_2026"]),
        "",
        "",
        "### Reading the results",
        *_verdicts(m),
        "",
        "Caveats:",
        "- Fantasy points are very noisy: the mean head explains only a few percent of the variance "
        "of a single player's score; gains show up in rankings and XI totals, not in exact numbers.",
        f"- The {T.TEST_SEASON} test model is frozen for the whole season (trained on ≤{T.TEST_SEASON - 1}); "
        f"the {T.WF_SEASON} walk-forward retrains every {T.WF_BLOCK} matches, as the live product will.",
        "- impact_in substitutes are included as rows although only the named substitutes are known at the toss.",
        "- Player roles / batting hand / bowling type are current values for every season.",
        "- p10–p90 coverage below the nominal 80% means the ranges are somewhat too narrow.",
        "",
        "### Rolling-origin CV (chosen parameters)",
        head,
        *[_row(f"CV {y}", v) for y, v in m["cv"].items()],
        "",
        "### Grid (mean-head MAE by fold)",
        "| Params | Fold MAE | Mean |",
        "|---|---|---|",
        *[
            f"| `{json.dumps(g['params'])}` | "
            + ", ".join(f"{y}: {v:.2f}" for y, v in g["fold_mae"].items())
            + f" | {g['mean_mae']:.3f} |"
            for g in m["grid"]
        ],
        "",
        "## Top features (mean head, share of total gain)",
        "| Feature | Gain share |",
        "|---|---|",
        *[f"| `{k}` | {v:.1%} |" for k, v in run["importance"]],
        "",
        "## Feature list",
        *[f"- **{g}**: " + ", ".join(f"`{f}`" for f in fs) for g, fs in FEATURE_GROUPS.items()],
        "",
        "Leakage guard: `tests/integration/test_features_leakage.py` perturbs every outcome of a "
        "cut-off match and all later matches and requires that match's features to be unchanged.",
        "",
    ]
    return "\n".join(lines)


def report(conn: Connection, version: str | None = None) -> str:
    """Re-render the report for a stored run (latest by default) from models/<version>/."""
    if version is None:
        version = conn.execute(
            text("SELECT version FROM model_run ORDER BY created_at DESC LIMIT 1")
        ).scalar()
        if version is None:
            raise LookupError("no model_run rows")
    d = MODELS_DIR / version
    meta = json.loads((d / "meta.json").read_text())
    run = {**meta, "metrics": json.loads((d / "metrics.json").read_text())}
    out = render(run)
    REPORT.write_text(out)
    return str(REPORT)
