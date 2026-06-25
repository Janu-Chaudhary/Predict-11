"""Dream11 IPL T20 fantasy-point computation from ball-by-ball deliveries.

Produces the GROUND-TRUTH label table `player_match_points`:
one row per (match_id, player) who appears in the data, with the actual fantasy
points that player earned, plus a component breakdown for debugging.

Scoring follows the widely published Dream11 IPL T20 system. Constants are kept
in one place so the ruleset is auditable and tweakable.
"""
from __future__ import annotations

import duckdb
import numpy as np
import pandas as pd

# --- batting ---
PTS_PER_RUN = 1
BONUS_FOUR = 1
BONUS_SIX = 2
MILESTONES = [(100, 16), (50, 8), (30, 4)]  # highest reached wins
DUCK_PENALTY = -2
SR_MIN_BALLS = 10
# (lower_exclusive, upper_inclusive, points) on strike rate
SR_BANDS = [(170, 1e9, 6), (150, 170, 4), (130, 150, 2),
            (60, 70, -2), (50, 60, -4), (0, 50, -6)]

# --- bowling ---
PTS_PER_WICKET = 25
BONUS_BOWLED_LBW = 8
HAULS = [(5, 16), (4, 8), (3, 4)]  # highest reached wins
MAIDEN_PTS = 12
ECON_MIN_BALLS = 12  # 2 overs
ECON_BANDS = [(0, 5, 6), (5, 6, 4), (6, 7, 2),
              (10, 11, -2), (11, 12, -4), (12, 1e9, -6)]

# --- fielding ---
CATCH_PTS = 8
CATCH3_BONUS = 4
STUMP_PTS = 12
RUNOUT_DIRECT = 12
RUNOUT_INDIRECT = 6

# --- being in the XI ---
LINEUP_PTS = 4

BOWLER_WICKETS = {"caught", "bowled", "lbw", "stumped", "caught and bowled", "hit wicket"}
BOWLER_NOT_CREDITED = {"run out", "retired hurt", "obstructing the field", "retired out"}


def _band(value: float, bands) -> int:
    for lo, hi, pts in bands:
        if lo < value <= hi:
            return pts
    return 0


def _milestone(runs: int) -> int:
    for thr, pts in MILESTONES:
        if runs >= thr:
            return pts
    return 0


def _haul(wkts: int) -> int:
    for thr, pts in HAULS:
        if wkts >= thr:
            return pts
    return 0


def compute_fantasy_points(con: duckdb.DuckDBPyConnection) -> pd.DataFrame:
    d = con.execute("SELECT * FROM deliveries").df()
    xi = con.execute("SELECT * FROM playing_xi").df()
    meta = con.execute("SELECT match_id, date, season FROM matches").df()

    is_wide = d["extra_kind"].eq("wides")
    is_noball = d["extra_kind"].eq("noballs")
    bowler_conceded_extra = (is_wide | is_noball).astype(int) * d["extras"].fillna(0)

    # ---------------- batting ----------------
    d_bat = d.assign(
        faced=(~is_wide).astype(int),
        is_four=d["batsman_runs"].eq(4).astype(int),
        is_six=d["batsman_runs"].eq(6).astype(int),
    )
    bat = d_bat.groupby(["match_id", "batter"]).agg(
        runs=("batsman_runs", "sum"),
        balls=("faced", "sum"),
        fours=("is_four", "sum"),
        sixes=("is_six", "sum"),
    ).reset_index().rename(columns={"batter": "player"})

    dismissed = d.loc[d["player_out"].notna(), ["match_id", "player_out"]].drop_duplicates()
    dismissed["dismissed"] = 1
    bat = bat.merge(
        dismissed.rename(columns={"player_out": "player"}), on=["match_id", "player"], how="left"
    )
    bat["dismissed"] = bat["dismissed"].fillna(0)

    sr = np.where(bat["balls"] > 0, bat["runs"] / bat["balls"] * 100, 0.0)
    bat["bat_pts"] = (
        bat["runs"] * PTS_PER_RUN
        + bat["fours"] * BONUS_FOUR
        + bat["sixes"] * BONUS_SIX
        + bat["runs"].apply(_milestone)
        + np.where((bat["runs"] == 0) & (bat["dismissed"] == 1) & (bat["balls"] >= 1),
                   DUCK_PENALTY, 0)
        + np.where(bat["balls"] >= SR_MIN_BALLS, [_band(x, SR_BANDS) for x in sr], 0)
    )

    # ---------------- bowling ----------------
    d_bowl = d.assign(
        legal=(~(is_wide | is_noball)).astype(int),
        conceded=d["batsman_runs"] + bowler_conceded_extra,
        is_wkt=d["wicket_kind"].isin(BOWLER_WICKETS).astype(int),
        is_bowled_lbw=d["wicket_kind"].isin({"bowled", "lbw"}).astype(int),
    )
    bowl = d_bowl.groupby(["match_id", "bowler"]).agg(
        balls=("legal", "sum"),
        conceded=("conceded", "sum"),
        wickets=("is_wkt", "sum"),
        bowled_lbw=("is_bowled_lbw", "sum"),
    ).reset_index().rename(columns={"bowler": "player"})

    # maidens: legal over with zero runs conceded to the bowler
    overs = d_bowl.groupby(["match_id", "bowler", "over"]).agg(
        conceded=("conceded", "sum"), legal=("legal", "sum")
    ).reset_index()
    maidens = overs[(overs["conceded"] == 0) & (overs["legal"] >= 1)]
    maidens = maidens.groupby(["match_id", "bowler"]).size().reset_index(name="maidens")
    bowl = bowl.merge(maidens.rename(columns={"bowler": "player"}),
                      on=["match_id", "player"], how="left")
    bowl["maidens"] = bowl["maidens"].fillna(0)

    econ = np.where(bowl["balls"] > 0, bowl["conceded"] / (bowl["balls"] / 6), 0.0)
    bowl["bowl_pts"] = (
        bowl["wickets"] * PTS_PER_WICKET
        + bowl["bowled_lbw"] * BONUS_BOWLED_LBW
        + bowl["wickets"].apply(_haul)
        + bowl["maidens"] * MAIDEN_PTS
        + np.where(bowl["balls"] >= ECON_MIN_BALLS, [_band(x, ECON_BANDS) for x in econ], 0)
    )

    # ---------------- fielding ----------------
    w = d.loc[d["wicket_kind"].notna() & d["fielders"].notna(),
              ["match_id", "wicket_kind", "fielders"]].copy()
    w["fielders"] = w["fielders"].str.split("|")
    w = w.explode("fielders").rename(columns={"fielders": "player"})
    w["player"] = w["player"].str.strip()
    w["catch"] = w["wicket_kind"].isin({"caught", "caught and bowled"}).astype(int)
    w["stump"] = w["wicket_kind"].eq("stumped").astype(int)
    w["runout"] = w["wicket_kind"].eq("run out").astype(int)
    field = w.groupby(["match_id", "player"]).agg(
        catches=("catch", "sum"),
        stumpings=("stump", "sum"),
        runouts=("runout", "sum"),
    ).reset_index()
    field["field_pts"] = (
        field["catches"] * CATCH_PTS
        + np.where(field["catches"] >= 3, CATCH3_BONUS, 0)
        + field["stumpings"] * STUMP_PTS
        + field["runouts"] * RUNOUT_INDIRECT
    )

    # ---------------- combine ----------------
    bat = bat.rename(columns={"balls": "bat_balls"})
    bowl = bowl.rename(columns={"balls": "bowl_balls"})
    parts = bat[["match_id", "player", "bat_pts", "bat_balls"]] \
        .merge(bowl[["match_id", "player", "bowl_pts", "bowl_balls", "wickets"]],
               on=["match_id", "player"], how="outer") \
        .merge(field[["match_id", "player", "field_pts"]], on=["match_id", "player"], how="outer")
    for c in ("bat_pts", "bowl_pts", "field_pts", "bat_balls", "bowl_balls", "wickets"):
        parts[c] = parts[c].fillna(0.0)

    # lineup point: anyone who appears in playing_xi gets +4; also union XI players
    xi_pts = xi[["match_id", "player"]].drop_duplicates().assign(lineup_pts=LINEUP_PTS)
    parts = parts.merge(xi_pts, on=["match_id", "player"], how="outer")
    parts["lineup_pts"] = parts["lineup_pts"].fillna(0.0)
    for c in ("bat_pts", "bowl_pts", "field_pts", "bat_balls", "bowl_balls", "wickets"):
        parts[c] = parts[c].fillna(0.0)

    parts["fp"] = parts["bat_pts"] + parts["bowl_pts"] + parts["field_pts"] + parts["lineup_pts"]
    parts = parts.merge(meta, on="match_id", how="left")
    parts = parts.dropna(subset=["player"])
    return parts.sort_values(["date", "match_id", "fp"], ascending=[True, True, False]) \
                .reset_index(drop=True)


def build_points_table(con: duckdb.DuckDBPyConnection) -> int:
    df = compute_fantasy_points(con)
    con.register("pmp_df", df)
    con.execute("CREATE OR REPLACE TABLE player_match_points AS SELECT * FROM pmp_df")
    con.unregister("pmp_df")
    return len(df)
