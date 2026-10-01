"""Shared helpers turning resolved rows into API reference objects and display strings."""

from __future__ import annotations

from .seasons_data import Core, InningsRow, MatchRow
from .seasons_nrr import balls_to_overs, revised_balls
from .seasons_schemas import InningsScore, MatchSummary, PlayerRef, TeamRef, VenueRef
from .seasons_teams import era_for


def team_ref(core: Core, team_id: int, year: int | None = None) -> TeamRef:
    t = core.teams.get(team_id)
    canonical = t.name if t else f"Team {team_id}"
    e = era_for(canonical, year)
    return TeamRef(id=team_id, name=e.name, short_code=e.short_code)


def venue_ref(core: Core, venue_id: int | None) -> VenueRef | None:
    if venue_id is None or venue_id not in core.venues:
        return None
    v = core.venues[venue_id]
    return VenueRef(id=v.id, name=v.name, city=v.city)


def player_ref(names: dict[str, str], player_id: str) -> PlayerRef:
    return PlayerRef(id=player_id, name=names.get(player_id, player_id))


def chase_quota_balls(m: MatchRow) -> int:
    inn2 = next((i for i in m.innings if i.innings == 2), None)
    rev = revised_balls(m.overs, inn2.target_overs) if inn2 else None
    return rev if rev is not None else m.overs * 6


def is_completed_innings(m: MatchRow, inn: InningsRow) -> bool:
    """Bowled out or batted its full quota (for "lowest total" style records)."""
    if inn.wickets + inn.absent_hurt >= 10:
        return True
    # the revised length (when shortened) is the entitlement of both sides
    return inn.legal_balls >= chase_quota_balls(m)


def result_text(core: Core, m: MatchRow) -> str:
    if m.result == "no_result":
        return "No result"
    winner = team_ref(core, m.winner_id, m.year).name if m.winner_id else None
    if m.result == "tie":
        return f"Match tied ({winner} won the super over)" if winner else "Match tied"
    if winner is None:
        return "Result unknown"
    suffix = " (DLS)" if m.method else ""
    if m.win_by_runs:
        unit = "run" if m.win_by_runs == 1 else "runs"
        return f"{winner} won by {m.win_by_runs} {unit}{suffix}"
    if m.win_by_wickets:
        unit = "wicket" if m.win_by_wickets == 1 else "wickets"
        return f"{winner} won by {m.win_by_wickets} {unit}{suffix}"
    return f"{winner} won{suffix}"


def match_summary(core: Core, m: MatchRow) -> MatchSummary:
    scores = [
        InningsScore(
            innings=i.innings,
            team_id=i.team_id,
            runs=i.runs,
            wickets=i.wickets,
            overs=balls_to_overs(i.legal_balls),
            target_overs=str(i.target_overs) if i.target_overs is not None else None,
        )
        for i in m.innings
    ]
    return MatchSummary(
        id=m.id,
        season=m.year,
        date=m.date,
        match_number=m.match_number,
        stage=m.stage,
        venue=venue_ref(core, m.venue_id),
        team1=team_ref(core, m.team1_id, m.year),
        team2=team_ref(core, m.team2_id, m.year),
        toss_winner_id=m.toss_winner_id,
        toss_decision=m.toss_decision,
        result=m.result,  # type: ignore[arg-type]
        winner_id=m.winner_id,
        margin_runs=m.win_by_runs,
        margin_wickets=m.win_by_wickets,
        method=m.method,
        super_over=m.super_over,
        result_text=result_text(core, m),
        scores=scores,
    )
