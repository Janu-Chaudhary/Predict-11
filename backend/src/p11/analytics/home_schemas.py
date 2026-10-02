"""Response models for the Home page (/api/v1/home/*).

The landing hero rotates by match state (docs/DESIGN-DIRECTION.md §8):
B "XI assembles" before a match, A "wagon wheel" after a match when official shot data
exists, otherwise C "particle worm"; off-season shows C on the season final.
"""

from __future__ import annotations

import datetime as dt
from typing import Literal

from pydantic import BaseModel, Field

Phase = Literal["pre_match", "post_match", "off_season"]
Hero = Literal["A", "B", "C"]
BallKind = Literal["dot", "run", "four", "six", "wicket"]


# --------------------------------------------------------------------------- shared refs
class HomeTeam(BaseModel):
    id: int
    name: str = Field(description="Name the franchise used that season")
    short_code: str


class HomeVenue(BaseModel):
    id: int
    name: str
    city: str | None = None


class HomeScore(BaseModel):
    innings: int
    team_id: int
    runs: int
    wickets: int
    overs: str = Field(description='Cricket notation, e.g. "20" or "17.5"')


class HomeMatch(BaseModel):
    id: int
    date: dt.date
    season: int
    title: str = Field(description='"Final", "Qualifier 1", "Match 41"')
    stage: str | None
    match_number: int | None
    venue: HomeVenue | None
    team1: HomeTeam
    team2: HomeTeam
    winner_id: int | None
    result: str = Field(description='e.g. "RCB won by 5 wickets"')
    scores: list[HomeScore]


# --------------------------------------------------------------------------- state
class NextFixture(BaseModel):
    id: int | None
    start: dt.datetime
    title: str
    venue: HomeVenue | None
    team1: HomeTeam
    team2: HomeTeam
    status: Literal["provisional", "xi_confirmed"]


class SeasonCard(BaseModel):
    year: int
    champion: HomeTeam | None
    runner_up: HomeTeam | None
    final_match_id: int | None
    next_season: str = Field(description='Off-season hint, e.g. "IPL 2027 starts ~March"')


class HomeState(BaseModel):
    phase: Phase
    now: dt.datetime
    hero: Hero
    hero_match_id: int | None = Field(description="Match the hero visualises")
    hero_reason: str = Field(description="Why this hero was picked (shown as a caption)")
    next_fixture: NextFixture | None = Field(description="Null in the off-season")
    last_match: HomeMatch | None
    season: SeasonCard | None


# --------------------------------------------------------------------------- C: worm
class WormBall(BaseModel):
    x: float = Field(description="Overs as a real number: over + legal balls in over / 6")
    runs: int = Field(description="Cumulative innings runs after this delivery")
    wickets: int = Field(description="Cumulative innings wickets after this delivery")
    kind: BallKind
    label: str = Field(description='Ball code, e.g. "14.3"')


class WormInnings(BaseModel):
    innings: int
    team: HomeTeam
    runs: int
    wickets: int
    overs: str
    balls: list[WormBall]


class Worm(BaseModel):
    match: HomeMatch
    innings: list[WormInnings]
    ball_count: int
    y_max: int = Field(description="Suggested y-axis maximum (runs), rounded up to 10")


# --------------------------------------------------------------------------- A: wagon
class Shot(BaseModel):
    over: int = Field(description="0-based over")
    ball: int
    label: str
    runs: int
    direction: float = Field(description="Degrees: 270 straight, 0 square leg (RHB), 180 point")
    distance_pct: float
    zone: int
    zone_name: str
    bowler: str


class Wagon(BaseModel):
    match_id: int
    batter: str
    team: HomeTeam | None
    runs: int
    balls: int | None
    not_out: bool | None
    left_handed: bool
    shots: list[Shot]
    source: str = Field(description="Where the shot data came from (labelled in the UI)")


# --------------------------------------------------------------------------- B: XI
class XIPlayer(BaseModel):
    id: str
    name: str
    short_name: str
    team: str = Field(description="Team short code")
    role: Literal["WK", "BAT", "AR", "BOWL"]
    points: float
    picked: bool
    captain: Literal["C", "VC"] | None = None


class XI(BaseModel):
    match_id: int
    kind: Literal["actual"] = Field(
        description="actual = hindsight-best valid XI from persisted actual fantasy points"
    )
    teams: list[str]
    players: list[XIPlayer]
    total: float = Field(description="Points of the picked XI with C x2 and VC x1.5")


# --------------------------------------------------------------------------- bento tiles
class TableTile(BaseModel):
    season: int
    leader: HomeTeam
    leader_points: int
    played: int
    champion: HomeTeam | None


class PlayerStatLine(BaseModel):
    id: str
    name: str
    team: str | None
    value: int


class PlayersTile(BaseModel):
    season: int
    top_runs: PlayerStatLine | None
    top_wickets: PlayerStatLine | None


class H2HTile(BaseModel):
    team_a: HomeTeam
    team_b: HomeTeam
    matches: int
    a_wins: int
    b_wins: int


class VenuesTile(BaseModel):
    season: int
    venues_used: int
    top_par_venue: HomeVenue | None
    top_par: int | None = Field(description="Average first-innings total at that venue")


class RecordsTile(BaseModel):
    team: HomeTeam
    opponent: HomeTeam
    runs: int
    wickets: int
    year: int
    match_id: int


class FantasyTile(BaseModel):
    season: int
    top: PlayerStatLine = Field(description="Most Dream11 points in the season (value = total)")
    matches: int
    mean: float


class HomeTiles(BaseModel):
    table: TableTile | None
    players: PlayersTile | None
    h2h: H2HTile | None
    venues: VenuesTile | None
    records: RecordsTile | None
    fantasy: FantasyTile | None = None
