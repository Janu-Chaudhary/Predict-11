"""Pydantic response models for the conditions endpoints (D2 matchup types, E1 venue extras,
E2 dew & weather)."""

from __future__ import annotations

import datetime as dt

from pydantic import BaseModel, Field

from .players_models import PlayerRef


# --------------------------------------------------------------------------- D2
class Coverage(BaseModel):
    balls: int = Field(description="balls in scope")
    balls_known: int = Field(description="balls whose opponent attribute is known")
    unknown_pct: float | None = Field(description="% of balls with unknown type / hand")
    opponents: int
    opponents_known: int


class TypeSplit(BaseModel):
    bowling_type: str = Field(description="normalized bowling type, or 'pace' / 'spin' group")
    group: str = Field(description="pace | spin")
    balls: int
    runs: int
    dismissals: int
    strike_rate: float | None
    average: float | None
    dot_pct: float | None
    boundary_pct: float | None
    fours: int
    sixes: int
    bowlers: int
    confidence: str = Field(description="low <12 balls, medium 12-29, high >=30 (as /h2h)")


class BatterVsTypes(BaseModel):
    batter: PlayerRef
    batting_hand: str | None
    since: dt.date | None
    by_type: list[TypeSplit]
    by_group: list[TypeSplit]
    coverage: Coverage
    notes: list[str]


class HandSplit(BaseModel):
    hand: str = Field(description="R | L")
    label: str = Field(description="RHB | LHB")
    balls: int = Field(description="legal balls")
    runs_conceded: int
    wickets: int
    economy: float | None
    strike_rate: float | None = Field(description="balls per wicket")
    average: float | None
    dot_pct: float | None
    boundary_pct: float | None
    batters: int
    confidence: str


class BowlerVsHands(BaseModel):
    bowler: PlayerRef
    bowling_type: str | None
    group: str | None
    since: dt.date | None
    by_hand: list[HandSplit]
    coverage: Coverage
    notes: list[str]


# --------------------------------------------------------------------------- venue extras
class TossSeason(BaseModel):
    season: int
    matches: int
    toss_field_pct: float | None = Field(description="% of toss winners choosing to field")
    toss_winner_win_pct: float | None = Field(description="excl. no results")
    chase_win_pct: float | None = Field(description="completed non-DLS matches")
    decided: int = Field(description="matches behind chase_win_pct")


class TossTrend(BaseModel):
    venue_id: int
    venue: str
    seasons: list[TossSeason]
    recent: TossSeason = Field(description="2023+ aggregate (season = 2023)")
    all_time: TossSeason = Field(description="all seasons (season = first season)")
    notes: list[str]


class BowlGroupLine(BaseModel):
    group: str = Field(description="pace | spin | unknown, or a bowling type")
    balls: int
    overs: str
    runs: int
    wickets: int
    economy: float | None
    strike_rate: float | None
    average: float | None
    overs_share_pct: float | None
    wickets_share_pct: float | None


class PaceSpinWindow(BaseModel):
    window: str = Field(description="recent (2023+) | all_time")
    matches: int
    groups: list[BowlGroupLine]
    by_type: list[BowlGroupLine]
    unknown_ball_pct: float | None


class PaceSpin(BaseModel):
    venue_id: int
    venue: str
    recent: PaceSpinWindow
    all_time: PaceSpinWindow
    notes: list[str]


# --------------------------------------------------------------------------- weather
class WeatherHour(BaseModel):
    time_utc: dt.datetime
    time_local: str = Field(description="IST clock, HH:MM")
    offset_h: float = Field(description="hours from the (anchor) start")
    temperature_2m: float | None
    relative_humidity_2m: float | None
    dew_point_2m: float | None
    spread: float | None = Field(description="temperature - dew point, degC")
    precipitation: float | None
    wind_speed_10m: float | None


class DewReading(BaseModel):
    at_utc: dt.datetime = Field(description="2nd-innings reference time (start + 2.5 h)")
    temperature_2m: float | None
    dew_point_2m: float | None
    relative_humidity_2m: float | None
    spread: float | None
    dew_risk: str = Field(description="high (spread <=3) | moderate (<=6) | low | unknown")
    rain_mm: float | None = Field(description="precipitation summed over start .. start+4 h")
    rain_risk: str = Field(description="none | low (<2 mm) | high (>=2 mm) | unknown")


class MatchConditions(BaseModel):
    match_id: int
    date: dt.date
    venue_id: int | None
    venue: str | None
    day_night: str | None
    start_utc: dt.datetime | None
    start_approx: bool | None
    hourly: list[WeatherHour]
    reading: DewReading | None
    chased_successfully: bool | None
    notes: list[str]


class DewBucket(BaseModel):
    matches: int
    chase_wins: int
    chase_win_pct: float | None


class DewSeason(BaseModel):
    season: int
    evening_matches: int
    with_weather: int
    avg_spread: float | None
    avg_humidity: float | None
    high_dew_matches: int
    high_dew: DewBucket
    low_dew: DewBucket


class DewReport(BaseModel):
    venue_id: int | None = Field(description="None = league-wide")
    venue: str | None
    high_dew_spread_c: float
    seasons: list[DewSeason]
    total: DewSeason = Field(description="all seasons (season = 0)")
    recent: DewSeason = Field(description="2023+ (season = 2023)")
    notes: list[str]


class Forecast(BaseModel):
    venue_id: int
    venue: str
    at_utc: dt.datetime
    source: str = Field(description="open-meteo-forecast | open-meteo-archive")
    grid_lat: float | None
    grid_lon: float | None
    hourly: list[WeatherHour]
    reading: DewReading | None
    notes: list[str]
