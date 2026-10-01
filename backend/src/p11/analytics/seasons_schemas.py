"""Pydantic response/request models for the seasons API (snake_case, typed for TS codegen)."""

from __future__ import annotations

import datetime as dt
from typing import Literal

from pydantic import BaseModel, Field

FormResult = Literal["W", "L", "N"]


class TeamRef(BaseModel):
    id: int
    name: str = Field(description="Name the franchise used in that season")
    short_code: str


class VenueRef(BaseModel):
    id: int
    name: str
    city: str | None = None


class PlayerRef(BaseModel):
    id: str
    name: str


# --------------------------------------------------------------------------- seasons / teams
class SeasonSummary(BaseModel):
    year: int
    label: str
    source_label: str
    match_count: int
    league_match_count: int
    team_count: int
    start_date: dt.date
    end_date: dt.date
    champion: TeamRef | None = None
    runner_up: TeamRef | None = None


class TeamEra(BaseModel):
    name: str
    short_code: str
    from_season: int
    to_season: int


class TeamSummary(BaseModel):
    id: int
    name: str
    short_code: str
    active: bool = Field(description="Played in the latest season in the data")
    seasons: list[int]
    titles: list[int]
    former_names: list[TeamEra]


# --------------------------------------------------------------------------- matches
class InningsScore(BaseModel):
    innings: int
    team_id: int
    runs: int
    wickets: int
    overs: str
    target_overs: str | None = None


class MatchSummary(BaseModel):
    id: int
    season: int
    date: dt.date
    match_number: int | None
    stage: str | None
    venue: VenueRef | None
    team1: TeamRef
    team2: TeamRef
    toss_winner_id: int | None
    toss_decision: str | None
    result: Literal["win", "tie", "no_result"]
    winner_id: int | None
    margin_runs: int | None
    margin_wickets: int | None
    method: str | None
    super_over: bool
    result_text: str
    scores: list[InningsScore]


# --------------------------------------------------------------------------- points table
class PointsRow(BaseModel):
    position: int
    team: TeamRef
    played: int
    won: int
    lost: int
    no_result: int
    tied: int = Field(description="Ties decided by super over; already counted in won/lost")
    points: int
    nrr: float
    runs_for: int
    overs_for: str
    runs_against: int
    overs_against: str
    form: list[FormResult] = Field(description="Last 5 league results, oldest first")
    qualified: bool = Field(description="Finished in the playoff places (top 4; 2008-10 top 4)")


class PointsTable(BaseModel):
    season: int
    league_matches: int
    after_match: int | None
    rows: list[PointsRow]
    tiebreak: str = "points, then wins, then net run rate"


# --------------------------------------------------------------------------- scenarios
class ScenarioFixture(BaseModel):
    match_id: int
    match_number: int | None
    date: dt.date
    team1_id: int
    team2_id: int
    actual_winner_id: int | None = Field(description="Real result (historical replay), if any")
    picked_winner_id: int | None = None


class ScenarioTeam(BaseModel):
    team: TeamRef
    played: int
    points: int
    wins: int
    remaining: int
    max_points: int
    p_top4: float = Field(description="Top 4 on points (and wins) alone, no NRR needed")
    p_top4_incl_ties: float = Field(description="Top 4 possible once NRR breaks level teams")
    p_top4_tie_dependent: float
    p_top2: float
    p_top2_incl_ties: float
    p_top2_tie_dependent: float
    clinched_top4: bool
    eliminated: bool
    clinched_top2: bool
    out_of_top2: bool


class ScenarioPick(BaseModel):
    match_id: int
    winner_id: int


class ScenarioRequest(BaseModel):
    after_match: int | None = None
    picks: list[ScenarioPick] = Field(default_factory=list)


class Scenarios(BaseModel):
    season: int
    after_match: int
    league_matches: int
    remaining_matches: int
    method: Literal["exhaustive", "monte_carlo"]
    outcomes_evaluated: int
    flags_exact: bool = Field(
        description="True when clinched/eliminated come from full enumeration; otherwise they "
        "are proven by bounds and may be conservative"
    )
    assumption: str = "each remaining match is a 50/50; no-results not simulated"
    teams: list[ScenarioTeam]
    remaining: list[ScenarioFixture]


# --------------------------------------------------------------------------- story
class RaceSeries(BaseModel):
    player: PlayerRef
    team: TeamRef | None
    total: int
    cumulative: list[int] = Field(description="Running total at each date in `dates`")


class CapRace(BaseModel):
    dates: list[dt.date]
    leaders: list[RaceSeries]


class BattingLeader(BaseModel):
    player: PlayerRef
    team: TeamRef | None
    innings: int
    runs: int
    balls: int
    strike_rate: float
    fours: int
    sixes: int


class BowlingLeader(BaseModel):
    player: PlayerRef
    team: TeamRef | None
    innings: int
    overs: str
    runs: int
    wickets: int
    economy: float


class SeasonStory(BaseModel):
    season: int
    orange_cap: CapRace
    purple_cap: CapRace
    most_sixes: list[BattingLeader]
    best_strike_rate: list[BattingLeader]
    best_economy: list[BowlingLeader]
    min_balls_for_strike_rate: int
    min_overs_for_economy: int


# --------------------------------------------------------------------------- head to head
class ResultLine(BaseModel):
    match_id: int
    season: int
    date: dt.date
    venue: VenueRef | None
    winner_id: int | None
    result_text: str


class TeamTotalRecord(BaseModel):
    match_id: int
    season: int
    date: dt.date
    team: TeamRef
    opponent: TeamRef
    venue: VenueRef | None
    runs: int
    wickets: int
    overs: str


class VenueSplit(BaseModel):
    venue: VenueRef
    played: int
    team_a_won: int
    team_b_won: int
    no_result: int


class HeadToHead(BaseModel):
    team_a: TeamRef
    team_b: TeamRef
    season: int | None
    venue_id: int | None
    played: int
    team_a_won: int
    team_b_won: int
    no_result: int
    tied: int = Field(description="Ties settled by super over (included in the won counts)")
    last5: list[ResultLine]
    team_a_highest: TeamTotalRecord | None
    team_b_highest: TeamTotalRecord | None
    team_a_lowest: TeamTotalRecord | None
    team_b_lowest: TeamTotalRecord | None
    by_venue: list[VenueSplit]


# --------------------------------------------------------------------------- records
class MarginRecord(BaseModel):
    match_id: int
    season: int
    date: dt.date
    winner: TeamRef
    loser: TeamRef
    venue: VenueRef | None
    margin: int
    balls_remaining: int | None = None


class BattingInningsRecord(BaseModel):
    match_id: int
    season: int
    date: dt.date
    player: PlayerRef
    team: TeamRef
    opponent: TeamRef
    venue: VenueRef | None
    runs: int
    balls: int
    not_out: bool
    fours: int
    sixes: int
    strike_rate: float


class BowlingFiguresRecord(BaseModel):
    match_id: int
    season: int
    date: dt.date
    player: PlayerRef
    team: TeamRef
    opponent: TeamRef
    venue: VenueRef | None
    wickets: int
    runs: int
    overs: str


class PartnershipRecord(BaseModel):
    match_id: int
    season: int
    date: dt.date
    team: TeamRef
    opponent: TeamRef
    venue: VenueRef | None
    wicket: int
    batter1: PlayerRef
    batter2: PlayerRef
    runs: int
    balls: int
    batter1_runs: int
    batter2_runs: int


class FastestMilestone(BaseModel):
    match_id: int
    season: int
    date: dt.date
    player: PlayerRef
    team: TeamRef
    opponent: TeamRef
    venue: VenueRef | None
    balls: int
    final_runs: int


class Records(BaseModel):
    scope: Literal["all", "season"]
    season: int | None
    venue_id: int | None
    most_runs: list[BattingLeader]
    most_wickets: list[BowlingLeader]
    highest_totals: list[TeamTotalRecord]
    lowest_totals: list[TeamTotalRecord]
    biggest_wins_by_runs: list[MarginRecord]
    biggest_wins_by_wickets: list[MarginRecord]
    highest_individual_scores: list[BattingInningsRecord]
    best_bowling_figures: list[BowlingFiguresRecord]
    highest_partnerships: list[PartnershipRecord]
    fastest_fifties: list[FastestMilestone]
    fastest_hundreds: list[FastestMilestone]
