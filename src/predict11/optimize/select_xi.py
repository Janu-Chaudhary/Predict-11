"""Pick the optimal fantasy XI from candidate players via integer programming.

Maximises expected fantasy points INCLUDING the captain (2x) and vice-captain
(1.5x) multipliers, modelled exactly as binary selection/captain/vice variables
(no greedy approximation):

    maximise  sum_i pred_i * (x_i + c_i + 0.5 * v_i)

subject to Dream11-style constraints. Constraints that don't apply (e.g. credits
during a historical backtest, where player prices are unknown) are simply omitted
by passing the relevant limit as None.
"""
from __future__ import annotations

from dataclasses import dataclass

import pandas as pd
import pulp


@dataclass
class XIConstraints:
    size: int = 11
    role_min: dict | None = None      # {"WK":1,"BAT":3,"AR":1,"BOWL":3}
    role_max: dict | None = None      # {"WK":4,"BAT":6,"AR":4,"BOWL":6}
    max_per_team: int | None = 7
    max_credits: float | None = 100.0
    max_foreign: int | None = None    # Dream11 has no foreign cap; IPL XI rule is 4


DREAM11 = XIConstraints(
    role_min={"WK": 1, "BAT": 3, "AR": 1, "BOWL": 3},
    role_max={"WK": 4, "BAT": 6, "AR": 4, "BOWL": 6},
    max_per_team=7,
    max_credits=100.0,
)

# Relaxed set for historical backtests: roles are derived, prices unknown.
BACKTEST = XIConstraints(
    role_min={"BAT": 3, "AR": 0, "BOWL": 3, "WK": 0},
    role_max={"BAT": 8, "AR": 8, "BOWL": 8, "WK": 8},
    max_per_team=7,
    max_credits=None,
    max_foreign=None,
)


def select_xi(players: pd.DataFrame, con: XIConstraints = DREAM11) -> dict:
    """players: columns [player, pred, role, team] + optional [credits, foreign].

    Returns dict with selected XI, captain, vice_captain, and expected points.
    """
    df = players.reset_index(drop=True)
    idx = list(df.index)
    pred = df["pred"].to_dict()

    prob = pulp.LpProblem("fantasy_xi", pulp.LpMaximize)
    x = pulp.LpVariable.dicts("x", idx, cat="Binary")   # selected
    c = pulp.LpVariable.dicts("c", idx, cat="Binary")   # captain
    v = pulp.LpVariable.dicts("v", idx, cat="Binary")   # vice-captain

    prob += pulp.lpSum(pred[i] * (x[i] + c[i] + 0.5 * v[i]) for i in idx)

    prob += pulp.lpSum(x[i] for i in idx) == con.size
    prob += pulp.lpSum(c[i] for i in idx) == 1
    prob += pulp.lpSum(v[i] for i in idx) == 1
    for i in idx:
        prob += c[i] <= x[i]
        prob += v[i] <= x[i]
        prob += c[i] + v[i] <= 1   # captain != vice-captain

    if con.role_min or con.role_max:
        for role in set((con.role_min or {})) | set((con.role_max or {})):
            members = [i for i in idx if df.at[i, "role"] == role]
            if con.role_min and role in con.role_min:
                prob += pulp.lpSum(x[i] for i in members) >= con.role_min[role]
            if con.role_max and role in con.role_max:
                prob += pulp.lpSum(x[i] for i in members) <= con.role_max[role]

    if con.max_per_team is not None and "team" in df.columns:
        for team in df["team"].dropna().unique():
            members = [i for i in idx if df.at[i, "team"] == team]
            prob += pulp.lpSum(x[i] for i in members) <= con.max_per_team

    if con.max_credits is not None and "credits" in df.columns:
        prob += pulp.lpSum(float(df.at[i, "credits"]) * x[i] for i in idx) <= con.max_credits

    if con.max_foreign is not None and "foreign" in df.columns:
        foreign_idx = [i for i in idx if bool(df.at[i, "foreign"])]
        prob += pulp.lpSum(x[i] for i in foreign_idx) <= con.max_foreign

    prob.solve(pulp.PULP_CBC_CMD(msg=False))
    status = pulp.LpStatus[prob.status]
    if status != "Optimal":
        return {"status": status, "xi": pd.DataFrame(), "expected_points": 0.0}

    chosen = [i for i in idx if x[i].value() > 0.5]
    cap = next(i for i in idx if c[i].value() > 0.5)
    vice = next(i for i in idx if v[i].value() > 0.5)
    xi = df.loc[chosen].copy()
    xi["is_captain"] = xi.index == cap
    xi["is_vice_captain"] = xi.index == vice
    xi["multiplier"] = 1.0
    xi.loc[cap, "multiplier"] = 2.0
    xi.loc[vice, "multiplier"] = 1.5
    return {
        "status": status,
        "xi": xi.sort_values("pred", ascending=False).reset_index(drop=True),
        "captain": df.at[cap, "player"],
        "vice_captain": df.at[vice, "player"],
        "expected_points": float(pulp.value(prob.objective)),
    }


def score_xi_actual(xi: pd.DataFrame, actual: dict[str, float]) -> float:
    """Realised fantasy points of a chosen XI given actual per-player points."""
    total = 0.0
    for _, r in xi.iterrows():
        total += actual.get(r["player"], 0.0) * r["multiplier"]
    return total
