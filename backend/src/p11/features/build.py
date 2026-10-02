"""Point-in-time feature frame for the fantasy-points model: one row per player per IPL match.

Prediction moment (owner decision 2026-10-02): **at the toss**. Known then: both playing XIs and
the named impact substitutes, the toss result (who bats first), venue, start time and the
weather forecast (we use the reanalysis weather at the start hour as a stand-in for it).
Everything else is built from *earlier* matches only: every rolling or cumulative statistic is
computed over a chronologically sorted series and shifted by one match, so a row never sees its
own match or anything later.

Feature groups (owner: "use every feature the data supports"):
- fantasy form: last 3/5/10/20 means, EWM, career mean, spread, ceiling, 50+ rate, points by
  category (batting / bowling / fielding), season-to-date, experience, rest days;
- batting craft: strike rate, average, boundary %, dismissal rate, balls per innings, phase usage
  (powerplay / middle / death balls), batting slot (last, mean), batted rate;
- bowling craft: overs per match, economy, wickets per match, strike rate, dot %, phase usage
  (powerplay / death share), bowled rate;
- fielding: catches + stumpings + run-out involvements per match;
- matchups vs the *announced* opposition XI: the opposition's expected spin share of overs and
  left-hander share of balls faced, combined with the player's own (shrunk) strike rate vs
  pace / spin and economy vs left / right hand; opposition attack and batting strength;
- player history at this venue and against this opponent (shrunk to the player's mean);
- team context: team/opponent fantasy points scored & conceded, batting depth around the player,
  the player's rank within his XI by form, home-ground share;
- conditions: venue par (recent first-innings totals, relative to league), bats first, toss
  won, start-hour temperature / humidity / dew point / dew spread / wind / rain, day-night;
- player attributes: role, batting hand, bowling type group;
- era: impact-player era, season, match number, playoff.

Universe: lineup rows of player_match_points with status xi / impact_in / impact_out (the 6
'sub' rows are fielding-only substitutes and are dropped); no-result matches are dropped.
Target: Dream11 ``total`` points (rules T20_2024 for every season, see p11.scoring).

Known approximations: impact_in players are included although at toss time only the five named
substitutes are known, not which one will come in; player attributes (role, hand, bowling
type) are current values, not per season.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from sqlalchemy import Connection, text

TARGET = "total"
ROLES = ("WK", "BAT", "AR", "BOWL")
IMPACT_ERA_FROM = 2023
SPIN = {"off-spin", "leg-spin", "left-arm orthodox", "left-arm wrist"}
PACE = {"right-arm fast", "right-arm medium", "left-arm fast", "left-arm medium"}
SHRINK_BALLS = 60.0  # prior weight (balls) for matchup strike rates / economies
SHRINK_GAMES = 5.0  # prior weight (games) for venue / opponent history

_SQL_ROWS = """
SELECT pmp.match_id, pmp.player_id, pmp.team_id, pmp.role_used AS role, pmp.status,
       pmp.batting, pmp.bowling, pmp.fielding, pmp.total,
       m.start_date AS date, s.year, m.venue_id, m.team1_id, m.team2_id,
       m.toss_winner_id, m.toss_decision, coalesce(m.match_number, 0) AS match_number,
       m.stage, m.result, m.day_night
FROM player_match_points pmp
JOIN match m ON m.id = pmp.match_id
JOIN season s ON s.id = m.season_id
JOIN competition c ON c.id = s.competition_id AND c.code = 'ipl'
WHERE pmp.status <> 'sub'
"""

_SQL_ATTR = """
SELECT player_id, batting_hand, bowling_type FROM player_attribute_resolved
"""

_SQL_BALLS = """
SELECT match_id, innings, ball_seq, over, batter_id, non_striker_id, bowler_id, batter_runs,
       total_runs, wides, noballs, byes, legbyes, wicket_kind, player_out_id, fielder_ids
FROM delivery_resolved WHERE NOT super_over
"""

_SQL_WEATHER = """
SELECT match_id, temperature_2m AS temp, relative_humidity_2m AS humidity,
       dew_point_2m AS dew_point, wind_speed_10m AS wind, precipitation AS rain
FROM match_weather WHERE time_utc = anchor_utc
"""

_BOWLER_WICKETS = {"bowled", "caught", "lbw", "caught and bowled", "stumped", "hit wicket"}


def _q(conn: Connection, sql: str) -> pd.DataFrame:
    return pd.DataFrame(conn.execute(text(sql)).mappings().all())


# --------------------------------------------------------------------------- per-match stats
def _match_stats(balls: pd.DataFrame, attrs: pd.DataFrame) -> pd.DataFrame:
    """One row per (match, player) with raw counting stats from ball-by-ball data."""
    b = balls.copy()
    b["legal"] = (b["wides"] == 0) & (b["noballs"] == 0)
    b["faced"] = b["wides"] == 0
    b["phase"] = np.select([b["over"] < 6, b["over"] >= 15], ["pp", "death"], "mid")
    btype = attrs.set_index("player_id")["bowling_type"]
    hand = attrs.set_index("player_id")["batting_hand"]
    b["bowl_grp"] = (
        b["bowler_id"]
        .map(btype)
        .map(lambda t: "spin" if t in SPIN else "pace" if t in PACE else None)
    )
    b["bat_hand"] = b["batter_id"].map(hand)
    b["conceded"] = b["total_runs"] - b["byes"] - b["legbyes"]
    b["bwk"] = b["wicket_kind"].isin(_BOWLER_WICKETS)
    b["dot"] = b["legal"] & (b["total_runs"] == 0)
    b["four"] = b["batter_runs"] == 4
    b["six"] = b["batter_runs"] == 6

    bat = b.groupby(["match_id", "batter_id"]).agg(
        runs=("batter_runs", "sum"),
        balls=("faced", "sum"),
        fours=("four", "sum"),
        sixes=("six", "sum"),
    )
    for ph in ("pp", "mid", "death"):
        bat[f"balls_{ph}"] = b[b["phase"] == ph].groupby(["match_id", "batter_id"])["faced"].sum()
    for grp in ("spin", "pace"):
        s = b[b["bowl_grp"] == grp].groupby(["match_id", "batter_id"])
        bat[f"runs_v_{grp}"] = s["batter_runs"].sum()
        bat[f"balls_v_{grp}"] = s["faced"].sum()
    bat.index.names = ["match_id", "player_id"]

    outs = b[b["player_out_id"].notna() & ~b["wicket_kind"].isin(["retired hurt"])]
    out = outs.groupby(["match_id", "player_out_id"]).size().rename("outs")
    out.index.names = ["match_id", "player_id"]

    bowl = b.groupby(["match_id", "bowler_id"]).agg(
        b_balls=("legal", "sum"),
        b_runs=("conceded", "sum"),
        b_wkts=("bwk", "sum"),
        b_dots=("dot", "sum"),
    )
    for ph in ("pp", "death"):
        bowl[f"b_balls_{ph}"] = (
            b[b["phase"] == ph].groupby(["match_id", "bowler_id"])["legal"].sum()
        )
    for h in ("L", "R"):
        s = b[b["bat_hand"] == h].groupby(["match_id", "bowler_id"])
        bowl[f"b_runs_v_{h}"] = s["conceded"].sum()
        bowl[f"b_balls_v_{h}"] = s["legal"].sum()
    bowl.index.names = ["match_id", "player_id"]

    fld = b[b["fielder_ids"].notna()][["match_id", "fielder_ids"]].explode("fielder_ids")
    fld = fld.groupby(["match_id", "fielder_ids"]).size().rename("dismissals_f")
    fld.index.names = ["match_id", "player_id"]

    # batting slot = order of first appearance at the crease in the innings
    app = pd.concat(
        [
            b[["match_id", "innings", "ball_seq", "batter_id"]].rename(
                columns={"batter_id": "pid"}
            ),
            b[["match_id", "innings", "ball_seq", "non_striker_id"]].rename(
                columns={"non_striker_id": "pid"}
            ),
        ]
    )
    first = app.groupby(["match_id", "innings", "pid"], as_index=False)["ball_seq"].min()
    first["bat_pos"] = first.groupby(["match_id", "innings"])["ball_seq"].rank(method="first")
    slot = first.groupby(["match_id", "pid"])["bat_pos"].min()
    slot.index.names = ["match_id", "player_id"]

    st = pd.concat([bat, out, bowl, fld, slot], axis=1)
    return st.reset_index()


# --------------------------------------------------------------------------- rolling helpers
# All vectorised: the frame is sorted chronologically, so within a group "earlier rows" are
# earlier matches. Every helper works on the series shifted by one row within the group, so
# a row never sees its own match.
Key = str | list[str]


def _codes(df: pd.DataFrame, key: Key) -> pd.Series:
    cols = [key] if isinstance(key, str) else key
    return pd.Series(df.groupby(cols, sort=False).ngroup().to_numpy(), index=df.index)


def prev(df: pd.DataFrame, key: Key, col: str) -> pd.Series:
    """Value from the group's previous row (NaN for the first)."""
    return df[col].groupby(_codes(df, key), sort=False).shift(1)


def _window(x: pd.Series, codes: pd.Series, k: int | None) -> tuple[pd.Series, pd.Series]:
    """(sum, count of non-null) of ``x`` over the last ``k`` rows of each group (all if None)."""
    s = x.fillna(0.0).groupby(codes, sort=False).cumsum()
    n = x.notna().astype(float).groupby(codes, sort=False).cumsum()
    if k is None:
        return s, n
    s_k = s - s.groupby(codes, sort=False).shift(k).fillna(0.0)
    n_k = n - n.groupby(codes, sort=False).shift(k).fillna(0.0)
    return s_k, n_k


def roll_mean(df: pd.DataFrame, key: Key, col: str, k: int | None) -> pd.Series:
    """Mean of the previous ``k`` values in the group (all previous if None), skipping NaNs;
    same as ``shift(1).rolling(k, min_periods=1).mean()`` per group."""
    codes = _codes(df, key)
    x = df[col].groupby(codes, sort=False).shift(1)
    s, n = _window(x, codes, k)
    return s / n.where(n > 0)


def roll_sum(df: pd.DataFrame, key: Key, col: str, k: int | None) -> pd.Series:
    """Sum of the previous ``k`` values (missing = 0); 0 before the first."""
    codes = _codes(df, key)
    x = df[col].fillna(0.0).groupby(codes, sort=False).shift(1)
    return _window(x, codes, k)[0]


def roll_std(df: pd.DataFrame, key: Key, col: str, k: int, min_n: int = 3) -> pd.Series:
    """Population sd of the previous ``k`` values (NaN with fewer than ``min_n``)."""
    codes = _codes(df, key)
    x = df[col].groupby(codes, sort=False).shift(1)
    s, n = _window(x, codes, k)
    s2, _ = _window(x * x, codes, k)
    mean = s / n.where(n > 0)
    var = (s2 / n.where(n > 0) - mean * mean).clip(lower=0)
    return np.sqrt(var).where(n >= min_n)


def roll_max(df: pd.DataFrame, key: Key, col: str, k: int) -> pd.Series:
    codes = _codes(df, key)
    x = df[col].groupby(codes, sort=False).shift(1)
    r = x.groupby(codes, sort=False).rolling(k, min_periods=1).max()
    return r.reset_index(level=0, drop=True).reindex(df.index)


def roll_ewm(df: pd.DataFrame, key: Key, col: str, halflife: float) -> pd.Series:
    codes = _codes(df, key)
    x = df[col].groupby(codes, sort=False).shift(1)
    r = x.groupby(codes, sort=False).ewm(halflife=halflife).mean()
    return r.reset_index(level=0, drop=True).reindex(df.index)


def last_known(df: pd.DataFrame, key: Key, col: str) -> pd.Series:
    """Most recent non-null value from previous rows."""
    codes = _codes(df, key)
    return df[col].groupby(codes, sort=False).shift(1).groupby(codes, sort=False).ffill()


def _rsum(df: pd.DataFrame, col: str, k: int | None) -> pd.Series:
    return roll_sum(df, "player_id", col, k)


def _rmean(df: pd.DataFrame, col: str, k: int) -> pd.Series:
    return roll_mean(df, "player_id", col, k)


def _ratio(num: pd.Series, den: pd.Series, scale: float = 1.0) -> pd.Series:
    return (num / den.where(den > 0)) * scale


def _shrunk(num: pd.Series, den: pd.Series, prior: pd.Series, k: float, scale: float) -> pd.Series:
    """(num + k * prior/scale) / (den + k) * scale: a rate shrunk toward ``prior``."""
    return (num.fillna(0) + k * prior / scale) / (den.fillna(0) + k) * scale


# --------------------------------------------------------------------------- feature groups
def _form(df: pd.DataFrame) -> pd.DataFrame:
    o = pd.DataFrame(index=df.index)
    g = df.groupby("player_id", sort=False)
    o["n_prev"] = g.cumcount()
    o["mean_all"] = roll_mean(df, "player_id", TARGET, None)
    for k in (3, 5, 10, 20):
        o[f"mean_{k}"] = _rmean(df, TARGET, k)
    o["ewm_5"] = roll_ewm(df, "player_id", TARGET, 5)
    o["sd_10"] = roll_std(df, "player_id", TARGET, 10)
    o["max_10"] = roll_max(df, "player_id", TARGET, 10)
    df["_50"] = (df[TARGET] >= 50).astype(float)
    df["_low"] = (df[TARGET] < 10).astype(float)
    o["p50plus_10"] = _rmean(df, "_50", 10)
    o["plow_10"] = _rmean(df, "_low", 10)
    for cat in ("batting", "bowling", "fielding"):
        o[f"{cat}_10"] = _rmean(df, cat, 10)
    gs = df.groupby(["player_id", "year"], sort=False)
    o["season_n"] = gs.cumcount()
    o["season_mean"] = roll_mean(df, ["player_id", "year"], TARGET, None)
    # distinct seasons among previous matches
    first_of_season = (gs.cumcount() == 0).astype(float)
    o["seasons_played"] = (
        first_of_season.groupby(df["player_id"], sort=False).cumsum() - first_of_season
    )
    o["days_rest"] = (df["date"] - g["date"].shift(1)).dt.days.clip(upper=400)
    return o


def _craft(df: pd.DataFrame) -> pd.DataFrame:
    o = pd.DataFrame(index=df.index)
    df["_batted"] = df["bat_pos"].notna().astype(float)
    df["_bowled"] = (df["b_balls"].fillna(0) > 0).astype(float)
    o["bat_pos_last"] = last_known(df, "player_id", "bat_pos")
    o["bat_pos_5"] = _rmean(df, "bat_pos", 5)
    o["batted_rate_10"] = _rmean(df, "_batted", 10)
    o["bowled_rate_10"] = _rmean(df, "_bowled", 10)
    for k in (10, None):
        sfx = "10" if k else "car"
        runs, balls, outs = _rsum(df, "runs", k), _rsum(df, "balls", k), _rsum(df, "outs", k)
        inns = _rsum(df, "_batted", k)
        o[f"sr_{sfx}"] = _ratio(runs, balls, 100)
        o[f"avg_{sfx}"] = _ratio(runs, outs)
        o[f"bpi_{sfx}"] = _ratio(balls, inns)
        o[f"bdry_pct_{sfx}"] = _ratio(_rsum(df, "fours", k) + _rsum(df, "sixes", k), balls, 100)
        o[f"six_rate_{sfx}"] = _ratio(_rsum(df, "sixes", k), balls, 100)
        bb, bw = _rsum(df, "b_balls", k), _rsum(df, "b_wkts", k)
        nb = _rsum(df, "_bowled", k)
        o[f"econ_{sfx}"] = _ratio(_rsum(df, "b_runs", k), bb, 6)
        o[f"wpm_{sfx}"] = _ratio(bw, nb)
        o[f"bsr_{sfx}"] = _ratio(bb, bw)
        o[f"dot_pct_{sfx}"] = _ratio(_rsum(df, "b_dots", k), bb, 100)
        o[f"overs_pm_{sfx}"] = _ratio(bb, nb) / 6
    b10 = _rsum(df, "balls", 10)
    for ph in ("pp", "mid", "death"):
        o[f"bat_{ph}_share_10"] = _ratio(_rsum(df, f"balls_{ph}", 10), b10)
    bb10 = _rsum(df, "b_balls", 10)
    for ph in ("pp", "death"):
        o[f"bowl_{ph}_share_10"] = _ratio(_rsum(df, f"b_balls_{ph}", 10), bb10)
    o["field_dis_10"] = _rmean(df.assign(_f=df["dismissals_f"].fillna(0)), "_f", 10)
    # career matchup rates (shrunk to the player's own career rate)
    car_sr = o["sr_car"].fillna(125.0)
    for grp in ("spin", "pace"):
        o[f"sr_v_{grp}"] = _shrunk(
            _rsum(df, f"runs_v_{grp}", None), _rsum(df, f"balls_v_{grp}", None),
            car_sr, SHRINK_BALLS, 100,
        )  # fmt: skip
    car_econ = o["econ_car"].fillna(8.0)
    for h in ("L", "R"):
        o[f"econ_v_{h}"] = _shrunk(
            _rsum(df, f"b_runs_v_{h}", None), _rsum(df, f"b_balls_v_{h}", None),
            car_econ, SHRINK_BALLS, 6,
        )  # fmt: skip
    return o


def _league_mean_before(df: pd.DataFrame) -> pd.Series:
    """Mean fantasy points per player over all *earlier* matches (point-in-time league prior)."""
    per = df.groupby("seq")[TARGET].agg(["sum", "count"]).sort_index()
    cum = per.cumsum().shift(1)
    mean = (cum["sum"] / cum["count"]).fillna(30.0)
    return df["seq"].map(mean)


def _history(df: pd.DataFrame, feats: pd.DataFrame) -> pd.DataFrame:
    """Player's record at this venue and against this opponent, shrunk to his career mean."""
    o = pd.DataFrame(index=df.index)
    prior = feats["mean_all"].fillna(_league_mean_before(df))
    for name, key in (("venue", "venue_id"), ("opp", "opp_id")):
        k = ["player_id", key]
        n = df.groupby(k, sort=False).cumcount()
        s = roll_sum(df, k, TARGET, None)
        o[f"{name}_n"] = n
        o[f"{name}_mean_shrunk"] = (s + SHRINK_GAMES * prior) / (n + SHRINK_GAMES)
        o[f"{name}_lift"] = o[f"{name}_mean_shrunk"] - prior
    return o


def _team_match_frame(df: pd.DataFrame) -> pd.DataFrame:
    tm = df.groupby(["match_id", "team_id"], as_index=False).agg(
        seq=("seq", "first"), opp_id=("opp_id", "first"), scored=(TARGET, "sum"),
        venue_id=("venue_id", "first"),
    )  # fmt: skip
    opp = tm[["match_id", "team_id", "scored"]].rename(
        columns={"team_id": "opp_id", "scored": "conceded"}
    )
    tm = tm.merge(opp, on=["match_id", "opp_id"], how="left").sort_values("seq")
    g = tm.groupby("team_id", sort=False)
    for c in ("scored", "conceded"):
        tm[f"team_{c}_10"] = (
            g[c]
            .shift(1)
            .groupby(tm["team_id"], sort=False)
            .transform(lambda s: s.rolling(10, min_periods=1).mean())
        )
    # home-ground share: fraction of the team's previous matches played at this venue
    at = tm.groupby(["team_id", "venue_id"], sort=False).cumcount()
    tm["team_n"] = g.cumcount()
    tm["home_share"] = at / tm["team_n"].clip(lower=1)
    tm["team_rest"] = tm.groupby("team_id", sort=False)["seq"].diff()
    return tm


def _venue(df: pd.DataFrame) -> pd.DataFrame:
    vm = (
        df.drop_duplicates("match_id")[["match_id", "venue_id", "seq", "first_innings"]]
        .sort_values("seq")
        .copy()
    )
    g = vm.groupby("venue_id", sort=False)
    prev = g["first_innings"].shift(1)
    vm["venue_par_20"] = prev.groupby(vm["venue_id"], sort=False).transform(
        lambda s: s.rolling(20, min_periods=1).mean()
    )
    vm["venue_matches"] = g.cumcount()
    league = vm["first_innings"].shift(1).rolling(60, min_periods=1).mean()
    vm["venue_par_rel"] = vm["venue_par_20"] - league
    vm["league_par_60"] = league
    return vm[["match_id", "venue_par_20", "venue_matches", "venue_par_rel", "league_par_60"]]


def _opposition(df: pd.DataFrame, feats: pd.DataFrame) -> pd.DataFrame:
    """Matchup context from the announced XIs: for each (match, team) the expected spin share of
    its bowling and left-hander share of its batting, plus attack / batting strength; joined to
    the *opposing* rows, and the player's own matchup-weighted rates."""
    x = df[["match_id", "team_id", "opp_id", "bowl_grp", "batting_hand"]].copy()
    x["exp_balls_bowled"] = feats["overs_pm_10"].fillna(0) * 6 * feats["bowled_rate_10"].fillna(0)
    x["exp_balls_faced"] = feats["bpi_10"].fillna(0) * feats["batted_rate_10"].fillna(0)
    x["bowl_pts"] = feats["bowling_10"].fillna(0)
    x["bat_pts"] = feats["batting_10"].fillna(0)
    x["spin_balls"] = np.where(x["bowl_grp"] == "spin", x["exp_balls_bowled"], 0.0)
    x["left_balls"] = np.where(x["batting_hand"] == "L", x["exp_balls_faced"], 0.0)
    t = x.groupby(["match_id", "team_id"]).agg(
        spin_balls=("spin_balls", "sum"), exp_bowled=("exp_balls_bowled", "sum"),
        left_balls=("left_balls", "sum"), exp_faced=("exp_balls_faced", "sum"),
        attack=("bowl_pts", "sum"), batting=("bat_pts", "sum"),
    )  # fmt: skip
    t["spin_share"] = _ratio(t["spin_balls"], t["exp_bowled"])
    t["left_share"] = _ratio(t["left_balls"], t["exp_faced"])
    t = t[["spin_share", "left_share", "attack", "batting"]].reset_index()
    opp = t.rename(
        columns={
            "team_id": "opp_id", "spin_share": "opp_spin_share", "left_share": "opp_left_share",
            "attack": "opp_attack", "batting": "opp_batting",
        }
    )  # fmt: skip
    o = df[["match_id", "opp_id"]].merge(opp, on=["match_id", "opp_id"], how="left")
    o.index = df.index
    o = o.drop(columns=["match_id", "opp_id"])
    share = o["opp_spin_share"].fillna(0.35)
    o["exp_sr_matchup"] = share * feats["sr_v_spin"] + (1 - share) * feats["sr_v_pace"]
    left = o["opp_left_share"].fillna(0.3)
    o["exp_econ_matchup"] = left * feats["econ_v_L"] + (1 - left) * feats["econ_v_R"]
    # own team: batting depth around the player, rank within the XI by form
    own = df[["match_id", "team_id"]].assign(bat=feats["batting_10"].fillna(0), ewm=feats["ewm_5"])
    team_bat = own.groupby(["match_id", "team_id"])["bat"].transform("sum")
    o["team_bat_depth_excl"] = team_bat - own["bat"]
    o["rank_in_team"] = own.groupby(["match_id", "team_id"])["ewm"].rank(ascending=False)
    return o


FEATURES: list[str] = [
    # form
    "n_prev", "mean_all", "mean_3", "mean_5", "mean_10", "mean_20", "ewm_5", "sd_10", "max_10",
    "p50plus_10", "plow_10", "batting_10", "bowling_10", "fielding_10", "season_n",
    "season_mean", "seasons_played", "days_rest",
    # batting / bowling / fielding craft
    "bat_pos_last", "bat_pos_5", "batted_rate_10", "bowled_rate_10",
    "sr_10", "avg_10", "bpi_10", "bdry_pct_10", "six_rate_10",
    "sr_car", "avg_car", "bpi_car", "bdry_pct_car", "six_rate_car",
    "econ_10", "wpm_10", "bsr_10", "dot_pct_10", "overs_pm_10",
    "econ_car", "wpm_car", "bsr_car", "dot_pct_car", "overs_pm_car",
    "bat_pp_share_10", "bat_mid_share_10", "bat_death_share_10",
    "bowl_pp_share_10", "bowl_death_share_10", "field_dis_10",
    "sr_v_spin", "sr_v_pace", "econ_v_L", "econ_v_R",
    # matchups vs announced XI, team context
    "opp_spin_share", "opp_left_share", "opp_attack", "opp_batting",
    "exp_sr_matchup", "exp_econ_matchup", "team_bat_depth_excl", "rank_in_team",
    "team_scored_10", "team_conceded_10", "opp_scored_10", "opp_conceded_10",
    "home_share", "team_rest",
    # history at venue / vs opponent
    "venue_n", "venue_mean_shrunk", "venue_lift", "opp_n", "opp_mean_shrunk", "opp_lift",
    # conditions
    "venue_par_20", "venue_matches", "venue_par_rel", "league_par_60",
    "bats_first", "won_toss", "temp", "humidity", "dew_point", "dew_spread", "wind", "rain",
    "night",
    # attributes / era
    "role_code", "left_hand", "bowl_grp_code", "impact_era", "year", "match_number", "playoff",
]  # fmt: skip


def build(conn: Connection) -> pd.DataFrame:
    """Raw rows + point-in-time FEATURES + target, chronological."""
    rows = _q(conn, _SQL_ROWS)
    attrs = _q(conn, _SQL_ATTR)
    balls = _q(conn, _SQL_BALLS)
    weather = _q(conn, _SQL_WEATHER)

    df = rows[rows["result"] != "no_result"].copy()
    df["date"] = pd.to_datetime(df["date"])
    df["opp_id"] = np.where(df["team_id"] == df["team1_id"], df["team2_id"], df["team1_id"])
    df["venue_id"] = df["venue_id"].fillna(-1).astype(int)
    order = (
        df[["match_id", "date", "match_number"]]
        .drop_duplicates("match_id")
        .sort_values(["date", "match_number", "match_id"])
    )
    df["seq"] = df["match_id"].map({m: i for i, m in enumerate(order["match_id"])})

    stats = _match_stats(balls, attrs)
    df = df.merge(stats, on=["match_id", "player_id"], how="left")
    first = (
        balls[balls["innings"] == 1].groupby("match_id")["total_runs"].sum().rename("first_innings")
    )
    df = df.merge(first, on="match_id", how="left")
    df = df.merge(attrs, on="player_id", how="left")
    df["bowl_grp"] = df["bowling_type"].map(
        lambda t: "spin" if t in SPIN else "pace" if t in PACE else None
    )
    num_cols = [c for c in stats.columns if c not in ("match_id", "player_id")]
    df[num_cols] = df[num_cols].astype(float)
    df = df.sort_values(["seq", "team_id", "player_id"]).reset_index(drop=True)

    feats = pd.concat([_form(df), _craft(df)], axis=1)
    feats = pd.concat([feats, _history(df, feats), _opposition(df, feats)], axis=1)
    df = pd.concat([df, feats], axis=1)

    tm = _team_match_frame(df)
    own = tm[
        ["match_id", "team_id", "team_scored_10", "team_conceded_10", "home_share", "team_rest"]
    ]
    df = df.merge(own, on=["match_id", "team_id"], how="left")
    opp = tm[["match_id", "team_id", "team_scored_10", "team_conceded_10"]].rename(
        columns={
            "team_id": "opp_id", "team_scored_10": "opp_scored_10",
            "team_conceded_10": "opp_conceded_10",
        }
    )  # fmt: skip
    df = df.merge(opp, on=["match_id", "opp_id"], how="left")
    df = df.merge(_venue(df), on="match_id", how="left")
    if not weather.empty:
        weather[["temp", "humidity", "dew_point", "wind", "rain"]] = weather[
            ["temp", "humidity", "dew_point", "wind", "rain"]
        ].astype(float)
        df = df.merge(weather, on="match_id", how="left")
    else:
        for c in ("temp", "humidity", "dew_point", "wind", "rain"):
            df[c] = np.nan
    df = df.copy()  # de-fragment before the last column inserts
    df["dew_spread"] = df["temp"] - df["dew_point"]

    won = df["toss_winner_id"] == df["team_id"]
    bat = df["toss_decision"].str.lower() == "bat"
    known = df["toss_winner_id"].notna() & df["toss_decision"].notna()
    df["bats_first"] = np.where(known, (won == bat).astype(float), np.nan)
    df["won_toss"] = np.where(df["toss_winner_id"].notna(), won.astype(float), np.nan)
    df["night"] = (df["day_night"] == "night").astype(float).where(df["day_night"].notna())
    df["impact_era"] = (df["year"] >= IMPACT_ERA_FROM).astype(int)
    df["role_code"] = df["role"].map({r: i for i, r in enumerate(ROLES)}).astype(int)
    df["left_hand"] = (df["batting_hand"] == "L").astype(float).where(df["batting_hand"].notna())
    df["bowl_grp_code"] = df["bowl_grp"].map({"pace": 1.0, "spin": 2.0}).fillna(0.0)
    df["playoff"] = df["stage"].notna().astype(int)
    df = df.drop(columns=[c for c in df.columns if c.startswith("_")])
    return df.sort_values(["seq", "team_id", "player_id"]).reset_index(drop=True)
