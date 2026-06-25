"""Prediction service for a live fixture: squads -> features -> model -> XI.

Bridges current-squad metadata (role, credits, foreign — from the Teams CSVs)
with each player's latest historical feature snapshot, predicts fantasy points,
and runs the Dream11 optimizer.
"""
from __future__ import annotations

import functools

import duckdb
import pandas as pd

from ..config import DUCKDB_PATH, SQUADS_DIR
from ..features.build import FEATURE_COLS
from ..model.train import load_model
from ..optimize.select_xi import DREAM11, select_xi

ROLE_MAP = {"WK-Batter": "WK", "Batter": "BAT", "Bowler": "BOWL", "All-Rounder": "AR"}

# Neutral cold-start features for players with no history in our data.
COLD_START = {
    "career_games": 0, "career_fp_mean": 0.0, "last3_fp_mean": 0.0,
    "last5_fp_mean": 0.0, "last10_fp_mean": 0.0, "ewm_fp": 0.0, "fp_std10": 0.0,
    "venue_fp_mean": 0.0, "opp_fp_mean": 0.0, "days_since_last": 30.0,
    "is_home": 0.0, "career_bat_balls_mean": 0.0, "career_bowl_balls_mean": 0.0,
    "bowl_share": 0.0, "season": 2025,
}


def list_teams() -> list[dict]:
    teams = []
    for f in sorted(SQUADS_DIR.glob("*_squad.csv")):
        slug = f.stem.replace("_squad", "")
        teams.append({"slug": slug, "name": slug.replace("-", " ").title()})
    return teams


# Squad CSVs were scraped inconsistently: the credits column appears as any of
# these spellings, and one file carries a UTF-8 BOM. Resolve columns by a
# normalised (lowercased, stripped, BOM-free) lookup instead of exact names.
_CREDIT_KEYS = {"credits", "credit", "credit points"}


def _resolve(cols: list[str], wanted: set[str] | str) -> str | None:
    wanted = {wanted} if isinstance(wanted, str) else wanted
    for c in cols:
        if c.replace("﻿", "").strip().lower() in wanted:
            return c
    return None


def load_squad(slug: str) -> pd.DataFrame:
    f = SQUADS_DIR / f"{slug}_squad.csv"
    if not f.exists():
        raise FileNotFoundError(f"unknown team '{slug}'")
    df = pd.read_csv(f)
    cols = list(df.columns)
    full = _resolve(cols, "full name")
    role = _resolve(cols, "role")
    credit = _resolve(cols, _CREDIT_KEYS)
    foreign = _resolve(cols, "foreign player")

    out = pd.DataFrame()
    out["player"] = df[full].astype(str).str.strip()
    out["role"] = df[role].map(ROLE_MAP).fillna("BAT")
    out["credits"] = (
        pd.to_numeric(df[credit], errors="coerce").fillna(8.0) if credit else 8.0
    )
    out["foreign"] = (
        df[foreign].astype(str).str.strip().str.lower().eq("true") if foreign else False
    )
    out["team"] = slug.replace("-", " ").title()
    return out[out["player"].str.len() > 0].reset_index(drop=True)


@functools.lru_cache(maxsize=1)
def _latest_features() -> pd.DataFrame:
    con = duckdb.connect(str(DUCKDB_PATH), read_only=True)
    df = con.execute(
        """
        SELECT * EXCLUDE (rn) FROM (
            SELECT *, row_number() OVER (PARTITION BY player ORDER BY date DESC) rn
            FROM player_match_features
        ) WHERE rn = 1
        """
    ).df()
    con.close()
    return df


@functools.lru_cache(maxsize=1)
def _model():
    return load_model()


def predict_fixture(slug1: str, slug2: str) -> dict:
    squad = pd.concat([load_squad(slug1), load_squad(slug2)], ignore_index=True)
    squad = squad.drop_duplicates(subset=["player"])

    snap = _latest_features()[["player", *FEATURE_COLS]]
    cand = squad.merge(snap, on="player", how="left")
    for col, default in COLD_START.items():
        cand[col] = cand[col].fillna(default)
    cand["has_history"] = cand["player"].isin(set(snap["player"]))

    cand["pred"] = _model().predict(cand[FEATURE_COLS])
    cand["pred"] = cand["pred"].clip(lower=0)  # negative expected points are meaningless for selection

    res = select_xi(cand[["player", "pred", "role", "team", "credits", "foreign"]], DREAM11)
    if res["xi"].empty:
        return {"status": res["status"], "error": "no feasible XI under Dream11 constraints"}

    xi = res["xi"].merge(cand[["player", "has_history", "last5_fp_mean"]], on="player", how="left")
    return {
        "status": "ok",
        "fixture": {"team1": load_squad(slug1)["team"].iloc[0],
                    "team2": load_squad(slug2)["team"].iloc[0]},
        "captain": res["captain"],
        "vice_captain": res["vice_captain"],
        "expected_points": round(res["expected_points"], 1),
        "total_credits": round(float(xi["credits"].sum()), 1),
        "foreign_count": int(xi["foreign"].sum()),
        "xi": [
            {
                "player": r["player"],
                "team": r["team"],
                "role": r["role"],
                "credits": float(r["credits"]),
                "foreign": bool(r["foreign"]),
                "pred_points": round(float(r["pred"]), 1),
                "recent_form": round(float(r["last5_fp_mean"]), 1),
                "is_captain": bool(r["is_captain"]),
                "is_vice_captain": bool(r["is_vice_captain"]),
                "debut_or_unknown": not bool(r["has_history"]),
            }
            for _, r in xi.iterrows()
        ],
    }
