"""Pydantic response models for /api/v1/fantasy/*."""

from __future__ import annotations

import datetime as dt
from typing import Literal

from pydantic import BaseModel, Field

from .seasons_schemas import MatchSummary, TeamRef

Role = Literal["WK", "BAT", "AR", "BOWL"]


class FantasyPlayerRef(BaseModel):
    id: str
    name: str
    image_url: str | None = None


class Distribution(BaseModel):
    n: int = Field(description="Scored matches (no-results and non-appearances excluded)")
    total: int
    mean: float
    median: float
    sd: float = Field(description="Population standard deviation")
    cv: float | None = Field(description="sd / mean (lower = more consistent)")
    p10: float
    p25: float
    p75: float
    p90: float
    floor: float = Field(description="p10")
    ceiling: float = Field(description="p90")
    min: int
    max: int
    pct_50_plus: float
    pct_100_plus: float


class CategoryMix(BaseModel):
    """Points by category and each category's share of the total."""

    batting: int
    bowling: int
    fielding: int
    lineup: int
    bonuses: int
    share_batting: float | None
    share_bowling: float | None
    share_fielding: float | None
    share_lineup: float | None
    share_bonuses: float | None


class SparkPoint(BaseModel):
    match_id: int
    date: dt.date
    season: int
    team: TeamRef
    opponent: TeamRef
    points: int


class FantasySeasonLine(BaseModel):
    season: int
    team: TeamRef
    role: Role
    n: int
    total: int
    mean: float
    median: float
    sd: float
    p10: float
    p90: float
    max: int
    credits: float | None
    credits_season: int | None = Field(description="Season whose credits apply (fallback)")
    points_per_credit: float | None = Field(description="Mean points per match / credits")


class FantasyPlayer(BaseModel):
    player: FantasyPlayerRef
    role: Role
    season: int | None
    since: dt.date | None
    distribution: Distribution | None
    category_mix: CategoryMix | None
    last10: list[SparkPoint]
    seasons: list[FantasySeasonLine]
    credits: float | None = Field(description="Credits for the filtered season, if any")
    credits_season: int | None
    points_per_credit: float | None


class LeaderboardRow(BaseModel):
    rank: int
    player: FantasyPlayerRef
    team: TeamRef
    role: Role
    n: int
    total: int
    mean: float
    median: float
    sd: float
    cv: float | None
    p10: float
    p90: float
    max: int
    pct_50_plus: float
    credits: float | None
    points_per_credit: float | None = Field(description="Mean points per match / credits")


class Leaderboard(BaseModel):
    season: int
    role: Role | None
    min_matches: int
    sort: Literal["total", "mean", "consistency", "ppc"]
    credits_season: int | None
    players_with_credits: int
    total_players: int
    rows: list[LeaderboardRow]


class RulesInfo(BaseModel):
    size: int
    role_min: dict[str, int]
    role_max: dict[str, int]
    max_per_team: int | None
    budget: float | None
    captain_mult: float
    vice_mult: float


class XIPlayer(BaseModel):
    player: FantasyPlayerRef
    team: TeamRef
    role: Role
    multiplier: float
    points: int | None = Field(description="Actual base points in the match / season")
    scored: float | None = Field(description="points x multiplier")
    value: float = Field(description="The value the optimizer maximised")
    credits: float | None


class XI(BaseModel):
    players: list[XIPlayer]
    captain: str | None
    vice_captain: str | None
    total: float = Field(description="Actual points incl. C x2 / VC x1.5")
    base_total: float
    objective: float = Field(description="Optimised value incl. multipliers")
    credits_used: float | None
    credits_constrained: bool
    team_counts: dict[str, int]
    solver: str


class MatchBestXI(BaseModel):
    match: MatchSummary
    no_result: bool
    rules: RulesInfo
    credits_season: int | None
    best: XI | None = Field(description="Hindsight Dream Team, no credit limit")
    best_with_credits: XI | None = Field(
        description="Hindsight Dream Team under the 100-credit budget (players without "
        "credits are left out of the pool); null when the season has no credits"
    )
    without_credits: list[FantasyPlayerRef] = Field(default_factory=list)
    naive_form: XI | None = Field(
        description="Best XI by mean of each player's last 5 IPL games before the match "
        "(0 when no history); total = its realised actual points"
    )
    gap: float | None = Field(description="best.total - naive_form.total")


class SeasonXIPlayer(BaseModel):
    player: FantasyPlayerRef
    team: TeamRef
    role: Role
    matches: int
    total: int
    mean: float


class SeasonXI(BaseModel):
    metric: Literal["total", "mean"]
    min_matches: int
    players: list[SeasonXIPlayer]
    sum_total: int
    sum_mean: float
    solver: str


class TeamOfSeason(BaseModel):
    season: int
    rules: RulesInfo
    by_total: SeasonXI
    by_mean: SeasonXI


class SeasonMatchXI(BaseModel):
    match_id: int
    date: dt.date
    match_number: int | None
    stage: str | None
    team1: TeamRef
    team2: TeamRef
    best_total: float
    naive_total: float
    gap: float
    best_with_credits_total: float | None
    captain: FantasyPlayerRef
    top_scorer: FantasyPlayerRef
    top_points: int


class SeasonBestXIs(BaseModel):
    season: int
    credits_season: int | None
    matches: list[SeasonMatchXI]
    no_result_matches: list[int]
    mean_best: float | None
    median_best: float | None
    max_best: float | None
    mean_naive: float | None
    mean_gap: float | None
