"""Leak-safe pre-match feature engineering.

Golden rule: every feature for (match M, player P) is computed using ONLY data
from matches strictly before M's date. We enforce this with sort-by-date +
groupby().shift() so the current match never leaks into its own features.

Output: one row per (match_id, player) who was in the playing XI, with the
target `fp` (actual fantasy points that match) and the feature columns.
"""
from __future__ import annotations

import duckdb
import numpy as np
import pandas as pd

FEATURE_COLS = [
    "career_games", "career_fp_mean",
    "last3_fp_mean", "last5_fp_mean", "last10_fp_mean",
    "ewm_fp", "fp_std10",
    "venue_fp_mean", "opp_fp_mean",
    "days_since_last", "is_home",
    "career_bat_balls_mean", "career_bowl_balls_mean", "bowl_share", "season",
]


def _base_table(con: duckdb.DuckDBPyConnection) -> pd.DataFrame:
    """player x match with team, opponent, venue, and the target fp."""
    return con.execute(
        """
        WITH pm AS (
            SELECT x.match_id, x.player, x.team,
                   CASE WHEN x.team = m.team1 THEN m.team2 ELSE m.team1 END AS opponent,
                   m.date, m.season, m.venue,
                   m.team1, m.toss_winner
            FROM playing_xi x
            JOIN matches m USING (match_id)
        )
        SELECT pm.match_id, pm.player, pm.team, pm.opponent, pm.date, pm.season,
               pm.venue,
               (pm.team = pm.team1) AS is_home,
               COALESCE(p.fp, 0.0)        AS fp,
               COALESCE(p.bat_balls, 0.0) AS bat_balls,
               COALESCE(p.bowl_balls, 0.0) AS bowl_balls
        FROM pm
        LEFT JOIN player_match_points p
               ON p.match_id = pm.match_id AND p.player = pm.player
        ORDER BY pm.date, pm.match_id
        """
    ).df()


def build_features(con: duckdb.DuckDBPyConnection) -> pd.DataFrame:
    df = _base_table(con)
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values(["player", "date", "match_id"]).reset_index(drop=True)

    g = df.groupby("player", group_keys=False)
    # every history feature uses shift(1) so the current match never leaks into itself
    df["career_games"] = g.cumcount()
    df["career_fp_mean"] = g["fp"].apply(lambda s: s.shift(1).expanding().mean())
    df["last3_fp_mean"] = g["fp"].apply(lambda s: s.shift(1).rolling(3, min_periods=1).mean())
    df["last5_fp_mean"] = g["fp"].apply(lambda s: s.shift(1).rolling(5, min_periods=1).mean())
    df["last10_fp_mean"] = g["fp"].apply(lambda s: s.shift(1).rolling(10, min_periods=1).mean())
    df["ewm_fp"] = g["fp"].apply(lambda s: s.shift(1).ewm(span=5).mean())
    df["fp_std10"] = g["fp"].apply(lambda s: s.shift(1).rolling(10, min_periods=2).std())
    df["career_bat_balls_mean"] = g["bat_balls"].apply(lambda s: s.shift(1).expanding().mean())
    df["career_bowl_balls_mean"] = g["bowl_balls"].apply(lambda s: s.shift(1).expanding().mean())
    df["days_since_last"] = g["date"].apply(lambda s: s.diff().dt.days)

    # venue affinity (prior matches at this venue, this player)
    df = df.sort_values(["player", "venue", "date"]).reset_index(drop=True)
    df["venue_fp_mean"] = df.groupby(["player", "venue"], group_keys=False)["fp"].apply(
        lambda s: s.shift(1).expanding().mean()
    )
    # opponent affinity
    df = df.sort_values(["player", "opponent", "date"]).reset_index(drop=True)
    df["opp_fp_mean"] = df.groupby(["player", "opponent"], group_keys=False)["fp"].apply(
        lambda s: s.shift(1).expanding().mean()
    )

    df["bowl_share"] = df["career_bowl_balls_mean"] / (
        df["career_bat_balls_mean"] + df["career_bowl_balls_mean"] + 1e-6
    )
    df["is_home"] = df["is_home"].astype(float)

    # fill cold-start NaNs (debut players) with neutral values
    fill = {
        "career_fp_mean": 0.0, "last3_fp_mean": 0.0, "last5_fp_mean": 0.0,
        "last10_fp_mean": 0.0, "ewm_fp": 0.0, "fp_std10": 0.0,
        "venue_fp_mean": np.nan, "opp_fp_mean": np.nan,
        "days_since_last": 30.0, "career_bat_balls_mean": 0.0,
        "career_bowl_balls_mean": 0.0, "bowl_share": 0.0,
    }
    df = df.fillna(fill)
    # venue/opp cold-start -> fall back to the player's career mean
    df["venue_fp_mean"] = df["venue_fp_mean"].fillna(df["career_fp_mean"])
    df["opp_fp_mean"] = df["opp_fp_mean"].fillna(df["career_fp_mean"])
    df["days_since_last"] = df["days_since_last"].clip(0, 365).fillna(30.0)

    return df.sort_values(["date", "match_id", "player"]).reset_index(drop=True)


def build_and_store(con: duckdb.DuckDBPyConnection) -> int:
    df = build_features(con)
    con.register("feat_df", df)
    con.execute("CREATE OR REPLACE TABLE player_match_features AS SELECT * FROM feat_df")
    con.unregister("feat_df")
    return len(df)
