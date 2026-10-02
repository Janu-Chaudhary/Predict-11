# ruff: noqa: E501  (plain-English feature descriptions and compact JSON builders)
"""Training telemetry for the Model Lab tab: everything about one model run, as one JSON
document (``models/<version>/telemetry.json`` and ``model_run.telemetry``; ``models/latest.json``
points at the newest run). Schema agreed with the Model Lab UI/API (2026-10-02)."""

from __future__ import annotations

import datetime as dt
import os
import platform
from dataclasses import asdict
from typing import Any

import lightgbm as lgb
import numpy as np
import pandas as pd
from sqlalchemy import Connection, text

from ..analytics import seasons_data
from ..analytics.seasons_refs import team_ref
from ..features.build import FEATURES, TARGET
from . import train as T

GROUP = {
    **dict.fromkeys(
        ["n_prev", "mean_all", "mean_3", "mean_5", "mean_10", "mean_20", "ewm_5", "sd_10",
         "max_10", "p50plus_10", "plow_10", "batting_10", "bowling_10", "fielding_10",
         "season_n", "season_mean", "seasons_played", "days_rest"], "form"),
    **dict.fromkeys(
        ["bat_pos_last", "bat_pos_5", "batted_rate_10", "sr_10", "avg_10", "bpi_10",
         "bdry_pct_10", "six_rate_10", "sr_car", "avg_car", "bpi_car", "bdry_pct_car",
         "six_rate_car", "bat_pp_share_10", "bat_mid_share_10", "bat_death_share_10"], "batting"),
    **dict.fromkeys(
        ["bowled_rate_10", "econ_10", "wpm_10", "bsr_10", "dot_pct_10", "overs_pm_10",
         "econ_car", "wpm_car", "bsr_car", "dot_pct_car", "overs_pm_car", "bowl_pp_share_10",
         "bowl_death_share_10"], "bowling"),
    "field_dis_10": "fielding",
    **dict.fromkeys(
        ["sr_v_spin", "sr_v_pace", "econ_v_L", "econ_v_R", "opp_spin_share", "opp_left_share",
         "opp_attack", "opp_batting", "exp_sr_matchup", "exp_econ_matchup"], "matchup"),
    **dict.fromkeys(
        ["team_bat_depth_excl", "rank_in_team", "team_scored_10", "team_conceded_10",
         "opp_scored_10", "opp_conceded_10", "home_share", "team_rest"], "team"),
    **dict.fromkeys(
        ["venue_n", "venue_mean_shrunk", "venue_lift", "opp_n", "opp_mean_shrunk", "opp_lift"],
        "history"),
    **dict.fromkeys(
        ["venue_par_20", "venue_matches", "venue_par_rel", "league_par_60", "bats_first",
         "won_toss", "temp", "humidity", "dew_point", "dew_spread", "wind", "rain", "night"],
        "conditions"),
    **dict.fromkeys(["role_code", "left_hand", "bowl_grp_code"], "attributes"),
    **dict.fromkeys(["impact_era", "year", "match_number", "playoff"], "era"),
}  # fmt: skip

DESCRIPTIONS = {
    "n_prev": "How many IPL games the player has played before this one; more history means a more reliable form estimate.",
    "mean_all": "Career average Dream11 points per IPL game; the long-run level of the player.",
    "mean_3": "Average points over the last 3 games; captures very recent hot or cold form.",
    "mean_5": "Average points over the last 5 games; the classic 'current form' number (also the baseline).",
    "mean_10": "Average points over the last 10 games; a steadier form estimate.",
    "mean_20": "Average points over the last 20 games; form over roughly a season and a half.",
    "ewm_5": "Recency-weighted average points (half-life 5 games); recent games count more than old ones.",
    "sd_10": "Spread (standard deviation) of points over the last 10 games; how boom-or-bust the player is.",
    "max_10": "Best score in the last 10 games; the player's recent ceiling.",
    "p50plus_10": "Share of the last 10 games with 50+ points; how often the player has a big game.",
    "plow_10": "Share of the last 10 games under 10 points; how often the player fails.",
    "batting_10": "Average batting points over the last 10 games; how much of the value comes from the bat.",
    "bowling_10": "Average bowling points over the last 10 games; how much comes from the ball.",
    "fielding_10": "Average fielding points over the last 10 games (catches, stumpings, run-outs).",
    "season_n": "Games already played this season; early-season form is less settled.",
    "season_mean": "Average points so far this season; current-season form separate from past years.",
    "seasons_played": "Number of IPL seasons the player has appeared in; experience.",
    "days_rest": "Days since the player's previous IPL game; long gaps can mean injury or being dropped.",
    "bat_pos_last": "Batting position in the player's last innings; top-order batters get more balls.",
    "bat_pos_5": "Average batting position over the last 5 games; the player's usual slot.",
    "batted_rate_10": "Share of the last 10 games in which the player got to bat; tail-enders often don't.",
    "sr_10": "Strike rate (runs per 100 balls) over the last 10 games; fast scoring earns bonus points.",
    "avg_10": "Batting average (runs per dismissal) over the last 10 games; how long the player lasts.",
    "bpi_10": "Balls faced per innings over the last 10 games; batting opportunity.",
    "bdry_pct_10": "Share of balls hit for four or six over the last 10 games; boundary bonuses.",
    "six_rate_10": "Sixes per 100 balls over the last 10 games; six bonuses and big-hitting.",
    "sr_car": "Career IPL strike rate; long-run scoring speed.",
    "avg_car": "Career IPL batting average; long-run reliability with the bat.",
    "bpi_car": "Career balls faced per innings; long-run batting opportunity.",
    "bdry_pct_car": "Career share of balls hit for four or six.",
    "six_rate_car": "Career sixes per 100 balls.",
    "bat_pp_share_10": "Share of recent balls faced in the powerplay (overs 1-6); openers' territory.",
    "bat_mid_share_10": "Share of recent balls faced in the middle overs (7-15).",
    "bat_death_share_10": "Share of recent balls faced at the death (overs 16-20); finishers' territory.",
    "bowled_rate_10": "Share of the last 10 games in which the player bowled; bowling opportunity.",
    "econ_10": "Economy rate (runs per over) over the last 10 games; economy bonuses and penalties.",
    "wpm_10": "Wickets per game bowled over the last 10 games; wickets are the biggest bowling points.",
    "bsr_10": "Bowling strike rate (balls per wicket) over the last 10 games.",
    "dot_pct_10": "Share of dot balls bowled over the last 10 games; dots earn points and build pressure.",
    "overs_pm_10": "Overs bowled per game over the last 10 games; how much the captain uses the bowler.",
    "econ_car": "Career IPL economy rate.",
    "wpm_car": "Career wickets per game bowled.",
    "bsr_car": "Career bowling strike rate (balls per wicket).",
    "dot_pct_car": "Career share of dot balls.",
    "overs_pm_car": "Career overs per game bowled.",
    "bowl_pp_share_10": "Share of recent balls bowled in the powerplay; new-ball bowlers take early wickets.",
    "bowl_death_share_10": "Share of recent balls bowled at the death; more wickets but more runs.",
    "field_dis_10": "Catches, stumpings and run-out involvements per game over the last 10 games.",
    "sr_v_spin": "Career strike rate against spin, shrunk towards the overall strike rate when the sample is small.",
    "sr_v_pace": "Career strike rate against pace, shrunk the same way.",
    "econ_v_L": "Career economy against left-handed batters, shrunk towards the overall economy.",
    "econ_v_R": "Career economy against right-handed batters, shrunk the same way.",
    "opp_spin_share": "Expected share of the opposition's overs bowled by spinners, from the announced XI.",
    "opp_left_share": "Expected share of the opposition's balls faced by left-handers, from the announced XI.",
    "opp_attack": "Strength of the opposition attack: sum of its players' recent bowling points.",
    "opp_batting": "Strength of the opposition batting: sum of its players' recent batting points.",
    "exp_sr_matchup": "The player's strike rate re-weighted for the opposition's spin/pace mix today.",
    "exp_econ_matchup": "The player's economy re-weighted for the opposition's left/right-hand mix today.",
    "team_bat_depth_excl": "Recent batting points of the player's teammates; deep line-ups leave fewer balls.",
    "rank_in_team": "Player's rank in his own XI by recent form (1 = in-form star).",
    "team_scored_10": "Fantasy points the player's team scored per game over its last 10 games.",
    "team_conceded_10": "Fantasy points the team's opponents scored per game over its last 10 games.",
    "opp_scored_10": "Fantasy points the opposition scored per game over its last 10 games.",
    "opp_conceded_10": "Fantasy points the opposition gave away per game over its last 10 games; a leaky side helps.",
    "home_share": "Share of the team's past games played at this venue; a proxy for home advantage.",
    "team_rest": "Matches in the league schedule since the team last played; rest between games.",
    "venue_n": "Games the player has previously played at this venue.",
    "venue_mean_shrunk": "Player's average points at this venue, shrunk towards his career average.",
    "venue_lift": "How much better or worse the player does at this venue than his career average.",
    "opp_n": "Games the player has previously played against this opponent.",
    "opp_mean_shrunk": "Player's average points against this opponent, shrunk towards his career average.",
    "opp_lift": "How much better or worse the player does against this opponent than his average.",
    "venue_par_20": "Average first-innings total at this venue over its last 20 games; batting-friendly or not.",
    "venue_matches": "IPL games previously played at this venue; how reliable the par score is.",
    "venue_par_rel": "Venue par minus the league par; positive means a high-scoring ground.",
    "league_par_60": "League-wide average first-innings total over the last 60 games; scoring era.",
    "bats_first": "Whether the player's team bats first (known from the toss).",
    "won_toss": "Whether the player's team won the toss.",
    "temp": "Air temperature at the start hour (°C).",
    "humidity": "Relative humidity at the start hour; affects swing and grip.",
    "dew_point": "Dew point at the start hour; high dew makes the ball wet for bowlers.",
    "dew_spread": "Temperature minus dew point; a small spread means dew is likely later in the game.",
    "wind": "Wind speed at the start hour.",
    "rain": "Rainfall at the start hour; rain can shorten games.",
    "night": "Night (or day-night) game versus afternoon game.",
    "role_code": "Playing role (wicket-keeper, batter, all-rounder, bowler); roles score differently.",
    "left_hand": "Left-handed batter.",
    "bowl_grp_code": "Bowling type group: none, pace or spin.",
    "impact_era": "Season from 2023 on, when the impact-player rule changed scoring.",
    "year": "Season; captures slow drifts in scoring over the years.",
    "match_number": "Match number in the season; early versus late in the tournament.",
    "playoff": "Playoff game (qualifier, eliminator, final).",
}


def _r(x: Any, d: int = 4) -> Any:
    if x is None:
        return None
    try:
        f = float(x)
    except (TypeError, ValueError):
        return x
    return None if not np.isfinite(f) else round(f, d)


def _hist(values: np.ndarray, width: float = 10.0) -> list[dict]:
    v = values[np.isfinite(values)]
    if not len(v):
        return []
    lo = np.floor(v.min() / width) * width
    hi = np.ceil(v.max() / width) * width + width
    counts, edges = np.histogram(v, bins=np.arange(lo, hi + 1e-9, width))
    return [{"lo": _r(edges[i]), "hi": _r(edges[i + 1]), "n": int(c)} for i, c in enumerate(counts)]


def _target(df: pd.DataFrame) -> dict:
    y = df[TARGET].to_numpy(float)
    q = np.percentile(y, [10, 25, 50, 75, 90])
    return {
        "mean": _r(y.mean()), "sd": _r(y.std()), "min": _r(y.min()), "max": _r(y.max()),
        "p10": _r(q[0]), "p25": _r(q[1]), "p50": _r(q[2]), "p75": _r(q[3]), "p90": _r(q[4]),
        "hist": _hist(y),
        "by_role": {
            r: {"mean": _r(g[TARGET].mean()), "sd": _r(g[TARGET].std(ddof=0)), "n": len(g)}
            for r, g in df.groupby("role")
        },
    }  # fmt: skip


def _shap(fitted: T.Fitted, X: pd.DataFrame) -> np.ndarray:
    return fitted.boosters["mean"].predict(X[FEATURES], pred_contrib=True)


def _calibration(p: pd.DataFrame) -> dict:
    y = p[TARGET].to_numpy(float)
    bins = pd.qcut(p["pred_mean"], 10, duplicates="drop")
    rel = [
        {
            "pred_lo": _r(iv.left),
            "pred_hi": _r(iv.right),
            "pred_mean": _r(g["pred_mean"].mean()),
            "actual_mean": _r(g[TARGET].mean()),
            "n": len(g),
        }  # fmt: skip
        for iv, g in p.groupby(bins, observed=True)
    ]

    def pinball(q: float, pred: np.ndarray) -> float:
        d = y - pred
        return float(np.mean(np.maximum(q * d, (q - 1) * d)))

    return {
        "coverage": {
            "below_q10": _r((y < p["pred_q10"]).mean()),
            "below_q50": _r((y < p["pred_q50"]).mean()),
            "below_q90": _r((y < p["pred_q90"]).mean()),
            "inside_80": _r(((y >= p["pred_q10"]) & (y <= p["pred_q90"])).mean()),
        },
        "reliability": rel,
        "pinball": {
            "q10": _r(pinball(0.1, p["pred_q10"].to_numpy())),
            "q50": _r(pinball(0.5, p["pred_q50"].to_numpy())),
            "q90": _r(pinball(0.9, p["pred_q90"].to_numpy())),
        },
    }


def _residuals(p: pd.DataFrame) -> dict:
    """Error = predicted mean - actual (positive = over-prediction)."""
    err = p["pred_mean"] - p[TARGET]

    def agg(mask: pd.Series) -> dict:
        e = err[mask]
        return {"mae": _r(e.abs().mean()), "bias": _r(e.mean()), "n": int(mask.sum())}

    exp = p["n_prev"]
    buckets = [("0", exp == 0), ("1-5", exp.between(1, 5)), ("6-20", exp.between(6, 20)),
               ("21+", exp >= 21)]  # fmt: skip
    bf = p["bats_first"]
    return {
        "definition": "error = predicted mean - actual points",
        "hist": _hist(err.to_numpy(float)),
        "by_role": {r: agg(p["role"] == r) for r in sorted(p["role"].unique())},
        "by_experience": [{"bucket": b, **agg(m)} for b, m in buckets],
        "by_bats_first": {
            "bats_first": agg(bf == 1),
            "chasing": agg(bf == 0),
            "unknown": agg(bf.isna()),
        },
    }


def _names(conn: Connection, ids: list[str]) -> dict[str, str]:
    rows = conn.execute(
        text(
            """SELECT p.id, coalesce(
                 (SELECT a.name FROM player_alias a WHERE a.player_id = p.id AND a.source = 'display'
                  ORDER BY a.name LIMIT 1), p.name)
               FROM player p WHERE p.id = ANY(:ids)"""
        ),
        {"ids": ids},
    )
    return dict(rows.all())  # type: ignore[arg-type]


def _code(core: Any, team_id: int, year: int) -> str:
    return team_ref(core, int(team_id), int(year)).short_code


def _per_match(p: pd.DataFrame, evals: list[T.MatchEval], core: Any) -> list[dict]:
    info = p.drop_duplicates("match_id").set_index("match_id")
    out = []
    for e in evals:
        m = info.loc[e.match_id]
        out.append(
            {
                **{k: (_r(v) if isinstance(v, float) else v) for k, v in asdict(e).items()},
                "date": str(pd.Timestamp(m["date"]).date()),
                "team1": _code(core, m["team1_id"], m["year"]),
                "team2": _code(core, m["team2_id"], m["year"]),
            }
        )
    return out


def _shap_section(
    conn: Connection, fitted: T.Fitted, test: pd.DataFrame, core: Any
) -> tuple[dict, np.ndarray]:
    sv = _shap(fitted, test)
    contrib, base = sv[:, :-1], float(sv[0, -1])
    mean_abs = np.abs(contrib).mean(axis=0)
    top = np.argsort(-mean_abs)[:8]
    rng = np.random.default_rng(T.SEED)
    idx = rng.choice(len(test), size=min(400, len(test)), replace=False)
    X = test[FEATURES].to_numpy(float)
    dependence = {
        FEATURES[j]: [{"x": _r(X[i, j]), "shap": _r(contrib[i, j])} for i in idx] for j in top
    }
    err = (test["pred_mean"] - test[TARGET]).to_numpy()
    order = np.argsort(err)
    picks = list(order[-4:][::-1]) + list(order[:4]) + list(np.argsort(np.abs(err))[:4])
    names = _names(conn, list(test["player_id"].iloc[picks]))
    examples = []
    for i in picks:
        r = test.iloc[i]
        top_j = np.argsort(-np.abs(contrib[i]))[:10]
        examples.append(
            {
                "match_id": int(r["match_id"]),
                "player_id": r["player_id"],
                "player_name": names.get(r["player_id"], r["player_id"]),
                "team": _code(core, r["team_id"], r["year"]),
                "pred": _r(r["pred_mean"]),
                "actual": int(r[TARGET]),
                "base": _r(base),
                "kind": "over" if i in order[-4:] else "under" if i in order[:4] else "accurate",
                "contribs": [
                    {"feature": FEATURES[j], "value": _r(X[i, j]), "shap": _r(contrib[i, j])}
                    for j in top_j
                ],
            }  # fmt: skip
        )
    return {
        "test:2025": {"base_value": _r(base), "dependence": dependence, "examples": examples}
    }, mean_abs


def _match_example(conn: Connection, p: pd.DataFrame, core: Any) -> dict:
    playoff = p[p["stage"].fillna("").str.lower() == "final"]
    mid = (
        int(playoff["match_id"].iloc[0])
        if len(playoff)
        else int(p.loc[p["seq"].idxmax(), "match_id"])
    )
    m = p[p["match_id"] == mid]
    xm, sm = T.best_xi(m, "pred_mean")
    xb, sb = T.best_xi(m, "pred_base")
    xbest, _ = T.best_xi(m, TARGET)
    names = _names(conn, list(m["player_id"]))
    first = m.iloc[0]
    venue = conn.execute(
        text("SELECT name FROM venue WHERE id = :v"), {"v": int(first["venue_id"])}
    ).scalar()
    in_m = set(sm.players) if sm else set()
    in_b = set(sb.players) if sb else set()
    players = []
    for r in m.sort_values("pred_mean", ascending=False).itertuples(index=False):
        cap = None
        if sm and r.player_id == sm.captain:
            cap = "C"
        elif sm and r.player_id == sm.vice_captain:
            cap = "VC"
        players.append(
            {
                "player_id": r.player_id,
                "name": names.get(r.player_id, r.player_id),
                "team": _code(core, r.team_id, r.year),
                "role": r.role,
                "pred_mean": _r(r.pred_mean, 2),
                "q10": _r(r.pred_q10, 2),
                "q50": _r(r.pred_q50, 2),
                "q90": _r(r.pred_q90, 2),
                "baseline": _r(r.pred_base, 2),
                "actual": int(r.total),
                "in_model_xi": r.player_id in in_m,
                "in_base_xi": r.player_id in in_b,
                "captain": cap,
            }  # fmt: skip
        )
    return {
        "match_id": mid, "date": str(pd.Timestamp(first["date"]).date()),
        "team1": _code(core, first["team1_id"], first["year"]),
        "team2": _code(core, first["team2_id"], first["year"]),
        "venue": venue, "stage": first["stage"], "players": players,
        "model_xi_points": _r(xm), "base_xi_points": _r(xb), "best_xi_points": _r(xbest),
    }  # fmt: skip


def build_telemetry(conn: Connection, ctx: dict) -> dict:
    """``ctx`` comes from p11.model.run.train_all (frames, models, evaluations, timings)."""
    df: pd.DataFrame = ctx["df"]
    final: T.Fitted = ctx["final"]
    serve: T.Fitted = ctx["serve"]
    test: pd.DataFrame = ctx["test"]
    wf: pd.DataFrame = ctx["wf"]
    core = seasons_data.core()

    shap_sec, shap_abs = _shap_section(conn, final, test, core)
    gain = final.boosters["mean"].feature_importance("gain").astype(float)
    split = final.boosters["mean"].feature_importance("split").astype(float)
    gain_n = gain / (gain.max() or 1.0)
    split_n = split / (split.max() or 1.0)
    train_rows = df[df["year"] < T.TEST_SEASON]
    feats = []
    for j, f in enumerate(FEATURES):
        col = df[f].astype(float)
        feats.append(
            {
                "name": f,
                "group": GROUP[f],
                "description": DESCRIPTIONS[f],
                "missing_rate": _r(col.isna().mean()),
                "mean": _r(col.mean()),
                "std": _r(col.std()),
                "min": _r(col.min()),
                "max": _r(col.max()),
                "importance_gain": _r(gain_n[j]),
                "importance_split": _r(split_n[j]),
                "shap_mean_abs": _r(shap_abs[j]),
            }  # fmt: skip
        )
    top25 = [FEATURES[j] for j in np.argsort(-gain)[:25]]
    corr = train_rows[top25].astype(float).corr().round(3).fillna(0.0)

    curves = {"final": final.curves, **ctx["cv_curves"]}
    evaluations = {f"cv:{y}": v for y, v in ctx["cv"].items()}
    evaluations["test:2025"] = ctx["test_metrics"]
    evaluations["walkforward:2026"] = ctx["wf_metrics"]
    return {
        "version": ctx["version"],
        "created_at": ctx["created_at"],
        "duration_s": {k: _r(v, 1) for k, v in ctx["durations"].items()},
        "protocol": {
            "cv_seasons": list(T.CV_SEASONS),
            "test_season": T.TEST_SEASON,
            "wf_season": T.WF_SEASON,
            "wf_block": T.WF_BLOCK,
            "quantiles": list(T.QUANTILES),
            "heads": list(T.HEADS),
            "recency_halflife_seasons": T.RECENCY_HALFLIFE_SEASONS,
            "early_stopping_rounds": T.EARLY_STOP,
            "max_trees": T.MAX_TREES,
            "inner_validation": f"last {T.INNER_MATCHES} training matches (about one season)",
        },  # fmt: skip
        "data": {
            "rows": len(df),
            "matches": int(df["match_id"].nunique()),
            "players": int(df["player_id"].nunique()),
            "rows_by_season": {str(k): int(v) for k, v in df.groupby("year").size().items()},
            "target": _target(df),
        },
        "features": feats,
        "correlations": {"features": top25, "matrix": corr.to_numpy().tolist()},
        "tuning": ctx["grid"],
        "chosen_params": ctx["params"],
        "curves": curves,
        "trees": serve.trees,
        "n_learned_values": serve.n_learned_values(),
        "n_learned_by_head": serve.n_learned_by_head(),
        "evaluations": evaluations,
        "per_match": {
            "test:2025": _per_match(test, ctx["test_evals"], core),
            "walkforward:2026": _per_match(wf, ctx["wf_evals"], core),
        },
        "calibration": {"test:2025": _calibration(test), "walkforward:2026": _calibration(wf)},
        "residuals": {"test:2025": _residuals(test), "walkforward:2026": _residuals(wf)},
        "shap": shap_sec,
        "examples": {"match": _match_example(conn, wf if len(wf) else test, core)},
        "walkforward_timeline": ctx["timeline"],
        "baselines": {"last5": "mean of the player's last 5 IPL games, 0 without history"},
        "environment": {
            "lightgbm": lgb.__version__,
            "python": platform.python_version(),
            "cpu_count": os.cpu_count(),
            "num_threads": T.BASE_PARAMS["num_threads"],
        },
    }


def now_iso() -> str:
    return dt.datetime.now(dt.UTC).isoformat(timespec="seconds")
