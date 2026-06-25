"""Walk-forward backtest: does picking an XI by model predictions beat baselines?

For every held-out match we know the 22 players who actually played and their
realised fantasy points. We build each strategy's XI from pre-match information
only, then score it with the realised points (captain 2x, vice 1.5x). Strategies:

  model   - LightGBM predicted points  (this project)
  form    - last-5-match average points (what the old heuristic effectively did)
  random  - a random *legal* XI         (floor)
  oracle  - picked with hindsight        (ceiling / upper bound)

The headline number is mean realised XI points across matches.
"""
from __future__ import annotations

import duckdb
import numpy as np
import pandas as pd

from ..config import DUCKDB_PATH, TEST_FROM_DATE
from ..features.build import FEATURE_COLS
from ..optimize.select_xi import BACKTEST, score_xi_actual, select_xi
from .train import load_model


def derive_role(bowl_share: float) -> str:
    if bowl_share > 0.55:
        return "BOWL"
    if bowl_share >= 0.25:
        return "AR"
    return "BAT"


def _strategy_points(cand: pd.DataFrame, pred_col: str, actual: dict) -> tuple[float, str, bool]:
    df = cand[["player", "role", "team"]].copy()
    df["pred"] = cand[pred_col].to_numpy()
    res = select_xi(df, BACKTEST)
    if res["xi"].empty:  # infeasible -> fall back to top-11 by pred, captain=top
        top = df.sort_values("pred", ascending=False).head(11).copy()
        top["multiplier"] = 1.0
        top.iloc[0, top.columns.get_loc("multiplier")] = 2.0
        top.iloc[1, top.columns.get_loc("multiplier")] = 1.5
        cap = top.iloc[0]["player"]
        return score_xi_actual(top, actual), cap, False
    pts = score_xi_actual(res["xi"], actual)
    cap = res["captain"]
    # did the captain pick land in the actual top-3 scorers of the match?
    top3 = set(sorted(actual, key=lambda p: -actual[p])[:3])
    return pts, cap, cap in top3


def backtest(con: duckdb.DuckDBPyConnection, test_from: str = TEST_FROM_DATE) -> dict:
    model = load_model()
    feats = con.execute(
        "SELECT * FROM player_match_features WHERE date >= ? ORDER BY date", [test_from]
    ).df()
    feats["pred"] = model.predict(feats[FEATURE_COLS])
    feats["role"] = feats["bowl_share"].apply(derive_role)

    rng = np.random.default_rng(42)
    rows = []
    for match_id, g in feats.groupby("match_id"):
        if g["team"].nunique() < 2 or len(g) < 13:
            continue
        actual = dict(zip(g["player"], g["fp"]))
        g = g.copy()
        g["rand"] = rng.random(len(g))
        g["oracle"] = g["fp"]

        m_pts, m_cap, m_hit = _strategy_points(g, "pred", actual)
        f_pts, _, _ = _strategy_points(g, "last5_fp_mean", actual)
        r_pts, _, _ = _strategy_points(g, "rand", actual)
        o_pts, _, _ = _strategy_points(g, "oracle", actual)
        rows.append(dict(match_id=match_id, model=m_pts, form=f_pts, random=r_pts,
                         oracle=o_pts, cap_hit=m_hit))

    res = pd.DataFrame(rows)
    summary = {
        "matches": len(res),
        "test_from": test_from,
        "mean_model": round(res["model"].mean(), 1),
        "mean_form": round(res["form"].mean(), 1),
        "mean_random": round(res["random"].mean(), 1),
        "mean_oracle": round(res["oracle"].mean(), 1),
        "model_beats_form_pct": round((res["model"] > res["form"]).mean() * 100, 1),
        "model_beats_random_pct": round((res["model"] > res["random"]).mean() * 100, 1),
        "captain_top3_hit_pct": round(res["cap_hit"].mean() * 100, 1),
    }
    # how far model closes the random->oracle gap (0% = random, 100% = perfect)
    denom = summary["mean_oracle"] - summary["mean_random"]
    summary["skill_vs_oracle_pct"] = round(
        (summary["mean_model"] - summary["mean_random"]) / denom * 100, 1
    ) if denom else 0.0
    return summary


if __name__ == "__main__":
    con = duckdb.connect(str(DUCKDB_PATH))
    s = backtest(con)
    con.close()
    for k, v in s.items():
        print(f"{k}: {v}")
