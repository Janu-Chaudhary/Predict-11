"""Pure-unit tests for the XI optimizer's constraint handling."""
import pandas as pd

from predict11.optimize.select_xi import DREAM11, XIConstraints, select_xi


def _candidates():
    rows = []
    roles = ["WK", "WK", "BAT", "BAT", "BAT", "BAT", "BAT", "AR", "AR", "AR",
             "BOWL", "BOWL", "BOWL", "BOWL", "BOWL", "BAT", "AR", "BOWL", "WK", "BAT", "BOWL", "AR"]
    for i, role in enumerate(roles):
        rows.append({
            "player": f"P{i}", "pred": 100 - i, "role": role,
            "team": "A" if i % 2 == 0 else "B",
            "credits": 8.0, "foreign": i < 6,
        })
    return pd.DataFrame(rows)


def test_selects_exactly_eleven_with_one_captain_and_vice():
    res = select_xi(_candidates(), DREAM11)
    xi = res["xi"]
    assert len(xi) == 11
    assert xi["is_captain"].sum() == 1
    assert xi["is_vice_captain"].sum() == 1
    assert res["captain"] != res["vice_captain"]


def test_respects_role_and_credit_limits():
    res = select_xi(_candidates(), DREAM11)
    xi = res["xi"]
    counts = xi["role"].value_counts().to_dict()
    assert counts.get("WK", 0) >= 1
    assert counts.get("BOWL", 0) >= 3
    assert counts.get("BAT", 0) >= 3
    assert xi["credits"].sum() <= 100.0


def test_captain_is_a_high_prediction_player():
    res = select_xi(_candidates(), DREAM11)
    # captain should be the max-pred player among the chosen XI
    xi = res["xi"]
    cap_pred = xi.loc[xi["is_captain"], "pred"].iloc[0]
    assert cap_pred == xi["pred"].max()


def test_max_per_team_constraint():
    con = XIConstraints(role_min={"BAT": 0, "BOWL": 0, "AR": 0, "WK": 0},
                        role_max=None, max_per_team=7, max_credits=None)
    res = select_xi(_candidates(), con)
    xi = res["xi"]
    assert xi["team"].value_counts().max() <= 7
