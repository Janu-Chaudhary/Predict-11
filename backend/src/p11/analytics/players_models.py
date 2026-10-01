"""Pydantic response models for player / matchup / milestone / streak endpoints."""

from __future__ import annotations

import datetime as dt

from pydantic import BaseModel, Field

from .players_stats import BattingLine, BowlingLine, Fielding, PhaseBat, PhaseBowl


class PlayerRef(BaseModel):
    id: str
    name: str


class BattingStats(BaseModel):
    innings: int
    not_outs: int
    runs: int
    balls: int
    average: float | None
    strike_rate: float | None
    fifties: int
    hundreds: int
    thirties: int
    ducks: int
    fours: int
    sixes: int
    dot_pct: float | None
    highest: str | None

    @classmethod
    def of(cls, ln: BattingLine) -> BattingStats:
        return cls(
            innings=ln.innings,
            not_outs=ln.not_outs,
            runs=ln.runs,
            balls=ln.balls,
            average=ln.average,
            strike_rate=ln.strike_rate,
            fifties=ln.fifties,
            hundreds=ln.hundreds,
            thirties=ln.thirties,
            ducks=ln.ducks,
            fours=ln.fours,
            sixes=ln.sixes,
            dot_pct=round(ln.dots / ln.balls * 100, 2) if ln.balls else None,
            highest=ln.highest_str,
        )


class BowlingStats(BaseModel):
    innings: int
    overs: str
    balls: int
    runs: int
    wickets: int
    economy: float | None
    average: float | None
    strike_rate: float | None
    best: str | None
    three_plus: int = Field(description="innings with 3+ wickets")
    four_plus: int = Field(description="innings with 4+ wickets")
    five_plus: int
    maidens: int
    dot_pct: float | None

    @classmethod
    def of(cls, ln: BowlingLine) -> BowlingStats:
        return cls(
            innings=ln.innings,
            overs=ln.overs,
            balls=ln.balls,
            runs=ln.runs,
            wickets=ln.wickets,
            economy=ln.economy,
            average=ln.average,
            strike_rate=ln.strike_rate,
            best=ln.best,
            three_plus=ln.three_plus,
            four_plus=ln.four_plus,
            five_plus=ln.five_plus,
            maidens=ln.maidens,
            dot_pct=ln.dot_pct,
        )


class FieldingStats(BaseModel):
    catches: int
    stumpings: int
    run_outs: int

    @classmethod
    def of(cls, f: Fielding) -> FieldingStats:
        return cls(catches=f.catches, stumpings=f.stumpings, run_outs=f.run_outs)


class PhaseBatting(BaseModel):
    phase: str
    balls: int
    runs: int
    outs: int
    strike_rate: float | None
    boundary_pct: float | None

    @classmethod
    def of(cls, phase: str, p: PhaseBat) -> PhaseBatting:
        return cls(
            phase=phase,
            balls=p.balls,
            runs=p.runs,
            outs=p.outs,
            strike_rate=p.strike_rate,
            boundary_pct=round((p.fours + p.sixes) / p.balls * 100, 2) if p.balls else None,
        )


class PhaseBowling(BaseModel):
    phase: str
    balls: int
    runs: int
    wickets: int
    economy: float | None
    dot_pct: float | None

    @classmethod
    def of(cls, phase: str, p: PhaseBowl) -> PhaseBowling:
        return cls(
            phase=phase,
            balls=p.balls,
            runs=p.runs,
            wickets=p.wickets,
            economy=p.economy,
            dot_pct=round(p.dots / p.balls * 100, 2) if p.balls else None,
        )


class SeasonLine(BaseModel):
    season: int
    team: str | None
    matches: int
    batting: BattingStats
    bowling: BowlingStats
    fielding: FieldingStats


class Split(BaseModel):
    """Venue or opposition split."""

    id: int
    name: str
    matches: int
    batting: BattingStats
    bowling: BowlingStats


class FormBat(BaseModel):
    match_id: int
    date: dt.date
    season: int
    opponent: str | None
    venue: str | None
    runs: int
    balls: int
    not_out: bool
    how_out: str | None
    score: str = Field(description='e.g. "73*(45)"')


class FormBowl(BaseModel):
    match_id: int
    date: dt.date
    season: int
    opponent: str | None
    venue: str | None
    overs: str
    runs: int
    wickets: int
    figures: str


class TeamSpan(BaseModel):
    id: int
    name: str
    first_season: int
    last_season: int
    matches: int


class Filters(BaseModel):
    season: int | None = None
    since: dt.date | None = None


class PlayerProfile(BaseModel):
    id: str
    name: str
    unique_name: str
    aliases: list[str]
    filters: Filters
    matches: int
    seasons: list[int]
    last_team: str | None
    teams: list[TeamSpan]
    debut: dt.date | None
    last_match: dt.date | None
    batting: BattingStats
    bowling: BowlingStats
    fielding: FieldingStats
    batting_phases: list[PhaseBatting]
    bowling_phases: list[PhaseBowling]
    by_season: list[SeasonLine]
    venues: list[Split]
    vs_teams: list[Split]
    form_batting: list[FormBat] = Field(description="last 10 innings, newest first")
    form_bowling: list[FormBowl] = Field(description="last 10 bowling innings, newest first")


class CompareEntry(BaseModel):
    id: str
    name: str
    matches: int
    last_team: str | None
    batting: BattingStats
    bowling: BowlingStats
    fielding: FieldingStats
    batting_phases: list[PhaseBatting]
    bowling_phases: list[PhaseBowling]


class CompareResponse(BaseModel):
    filters: Filters
    players: list[CompareEntry]


class SearchHit(BaseModel):
    id: str
    name: str
    matched: str = Field(description="name or alias that matched the query")
    team: str | None = Field(description="last IPL team")
    first_season: int | None
    last_season: int | None
    seasons: int
    matches: int


class SearchResponse(BaseModel):
    query: str
    results: list[SearchHit]


# --------------------------------------------------------------------------- matchups
class EncounterSeason(BaseModel):
    season: int
    balls: int
    runs: int
    dismissals: int
    strike_rate: float | None


class Encounter(BaseModel):
    match_id: int
    date: dt.date
    season: int
    venue: str | None
    balls: int
    runs: int
    out: bool
    how_out: str | None
    summary: str = Field(description='"balls-runs-out", e.g. "9-14-1"')


class PairStats(BaseModel):
    balls: int
    runs: int
    dismissals: int
    how_out: dict[str, int]
    strike_rate: float | None
    average: float | None
    dot_pct: float | None
    boundary_pct: float | None
    fours: int
    sixes: int
    matches: int
    innings: int
    confidence: str = Field(description="low <12 balls, medium 12-29, high >=30")
    by_season: list[EncounterSeason]
    last_encounters: list[Encounter]


class MatchupRow(BaseModel):
    player: PlayerRef
    balls: int
    runs: int
    dismissals: int
    strike_rate: float | None
    dot_pct: float | None
    boundary_pct: float | None
    matches: int
    confidence: str


class H2HResponse(BaseModel):
    batter: PlayerRef | None
    bowler: PlayerRef | None
    since: dt.date | None
    min_balls: int
    pair: PairStats | None
    top_bowlers_vs_batter: list[MatchupRow]
    top_batters_vs_bowler: list[MatchupRow]
    notes: list[str]


# --------------------------------------------------------------------------- records
class Milestone(BaseModel):
    player: PlayerRef
    team: str | None
    stat: str
    current: int
    target: int
    needed: int
    text: str


class MilestonesResponse(BaseModel):
    season: int
    as_of: dt.date | None
    milestones: list[Milestone]


class StreakEntry(BaseModel):
    player: PlayerRef
    team: str | None
    length: int
    start_date: dt.date
    end_date: dt.date
    active: bool = Field(description="streak still running at the end of the scope")


class StreakBoard(BaseModel):
    type: str
    label: str
    current: list[StreakEntry]
    longest: list[StreakEntry]


class StreaksResponse(BaseModel):
    season: int | None
    as_of: dt.date | None
    boards: list[StreakBoard]
