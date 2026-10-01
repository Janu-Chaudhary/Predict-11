"""Seasons analytics service: seasons, teams, points table (F1), playoff scenarios (F2),
season story (F3), team vs team (D4), records (I1) and match lists.

Routers call these functions; they return the Pydantic models in ``seasons_schemas``.
``NotFound`` maps to HTTP 404 and ``ValueError`` to 422.
"""

from __future__ import annotations

from collections.abc import Sequence

from . import seasons_data as data
from .seasons_adjustments import ABANDONED_NO_BALL, VOID_MATCH_IDS, Abandoned
from .seasons_data import Core, MatchRow
from .seasons_records import build_records, rank_highest_totals, rank_lowest_totals, total_record
from .seasons_refs import match_summary, result_text, team_ref, venue_ref
from .seasons_scenarios import Fixture, simulate
from .seasons_schemas import (
    HeadToHead,
    MatchSummary,
    PointsRow,
    PointsTable,
    Records,
    ResultLine,
    ScenarioFixture,
    ScenarioPick,
    Scenarios,
    ScenarioTeam,
    SeasonStory,
    SeasonSummary,
    TeamEra,
    TeamSummary,
    TeamTotalRecord,
    VenueSplit,
)
from .seasons_story import build_story
from .seasons_table import compute_standings
from .seasons_teams import all_codes, eras, short_code

PLAYOFF_SPOTS = 4


class NotFound(LookupError):
    pass


# --------------------------------------------------------------------------- helpers
def _season_matches(core: Core, year: int) -> list[MatchRow]:
    ms = core.season_matches(year)
    if not ms:
        raise NotFound(f"no matches for season {year}")
    return ms


def _league(core: Core, ms: Sequence[MatchRow]) -> list[MatchRow]:
    """League-stage matches in schedule order, with void games dropped and games abandoned
    without a ball (absent from the ball-by-ball data) added as no-results."""
    out = [m for m in ms if m.league and m.id not in VOID_MATCH_IDS]
    if ms:
        year = ms[0].year
        by_name = {t.name: t.id for t in core.teams.values()}
        for k, a in enumerate(x for x in ABANDONED_NO_BALL if x.year == year):
            if a.team1 in by_name and a.team2 in by_name:
                out.append(_abandoned_row(-(year * 100 + k + 1), a, by_name))
    return sorted(out, key=lambda m: (m.date, m.match_number or 10_000, m.id))


def _abandoned_row(match_id: int, a: Abandoned, by_name: dict[str, int]) -> MatchRow:
    return MatchRow(
        id=match_id,
        year=a.year,
        date=a.date,
        match_number=a.match_number,
        stage=None,
        venue_id=None,
        city=None,
        team1_id=by_name[a.team1],
        team2_id=by_name[a.team2],
        toss_winner_id=None,
        toss_decision=None,
        result="no_result",
        winner_id=None,
        win_by_runs=None,
        win_by_wickets=None,
        method=None,
        overs=20,
        super_over=False,
        innings=(),
    )


def _split(league: Sequence[MatchRow], n: int | None) -> tuple[list[MatchRow], list[MatchRow]]:
    """(played, remaining) after league match number ``n`` (None = everything played).
    Unnumbered games fall on their date relative to match ``n``."""
    if n is None:
        return list(league), []
    numbered = [m for m in league if m.match_number is not None and m.match_number <= n]
    cutoff = max((m.date for m in numbered), default=None)

    def done(m: MatchRow) -> bool:
        if m.match_number is not None:
            return m.match_number <= n
        return cutoff is not None and m.date <= cutoff

    return [m for m in league if done(m)], [m for m in league if not done(m)]


def resolve_team(core: Core, key: str | int) -> int:
    """Team by id, current or historical short code (e.g. "DCH" -> SRH), or exact name."""
    s = str(key).strip()
    if s.isdigit() and int(s) in core.teams:
        return int(s)
    up = s.upper()
    for t in core.teams.values():
        if up in all_codes(t.name) or s.lower() == t.name.lower():
            return t.id
        if any(s.lower() == e.name.lower() for e in eras(t.name)):
            return t.id
    raise NotFound(f"unknown team {key!r}")


def _champion(core: Core, ms: Sequence[MatchRow]) -> tuple[int | None, int | None]:
    final = next((m for m in ms if m.stage == "Final"), None)
    if final is None or final.winner_id is None:
        return None, None
    return final.winner_id, final.opponent(final.winner_id)


# --------------------------------------------------------------------------- seasons / teams
def list_seasons() -> list[SeasonSummary]:
    core = data.core()
    out: list[SeasonSummary] = []
    for year in sorted({m.year for m in core.matches}):
        ms = core.season_matches(year)
        champ, runner = _champion(core, ms)
        src = core.seasons.get(year)
        out.append(
            SeasonSummary(
                year=year,
                label=f"IPL {year}",
                source_label=src.source_label if src else str(year),
                match_count=len(ms),
                league_match_count=sum(1 for m in ms if m.league),
                team_count=len({t for m in ms for t in (m.team1_id, m.team2_id)}),
                start_date=min(m.date for m in ms),
                end_date=max(m.date for m in ms),
                champion=team_ref(core, champ, year) if champ else None,
                runner_up=team_ref(core, runner, year) if runner else None,
            )
        )
    return out


def list_teams() -> list[TeamSummary]:
    core = data.core()
    latest = max(m.year for m in core.matches)
    seasons: dict[int, set[int]] = {}
    titles: dict[int, list[int]] = {}
    for m in core.matches:
        for tid in (m.team1_id, m.team2_id):
            seasons.setdefault(tid, set()).add(m.year)
        if m.stage == "Final" and m.winner_id:
            titles.setdefault(m.winner_id, []).append(m.year)
    out: list[TeamSummary] = []
    for t in core.teams.values():
        yrs = sorted(seasons.get(t.id, set()))
        if not yrs:
            continue
        former: list[TeamEra] = []
        for e in eras(t.name):
            played = [
                y
                for y in yrs
                if (e.from_year is None or y >= e.from_year)
                and (e.to_year is None or y <= e.to_year)
            ]
            if played and e.name != t.name:
                former.append(
                    TeamEra(
                        name=e.name,
                        short_code=e.short_code,
                        from_season=played[0],
                        to_season=played[-1],
                    )
                )
        out.append(
            TeamSummary(
                id=t.id,
                name=t.name,
                short_code=short_code(t.name),
                active=latest in yrs,
                seasons=yrs,
                titles=sorted(titles.get(t.id, [])),
                former_names=former,
            )
        )
    out.sort(key=lambda s: (not s.active, s.name))
    return out


# --------------------------------------------------------------------------- F1 table
def points_table(year: int, after_match: int | None = None) -> PointsTable:
    core = data.core()
    league = _league(core, _season_matches(core, year))
    played, _ = _split(league, after_match)
    rows: list[PointsRow] = []
    for s in compute_standings(played):
        rows.append(
            PointsRow(
                position=s.position,
                team=team_ref(core, s.team_id, year),
                played=s.played,
                won=s.won,
                lost=s.lost,
                no_result=s.no_result,
                tied=s.tied,
                points=s.points,
                nrr=round(s.nrr.nrr, 3),
                runs_for=s.nrr.runs_for,
                overs_for=s.nrr.overs_for,
                runs_against=s.nrr.runs_against,
                overs_against=s.nrr.overs_against,
                form=s.results[-5:],  # type: ignore[arg-type]
                qualified=after_match is None and s.position <= PLAYOFF_SPOTS,
            )
        )
    return PointsTable(season=year, league_matches=len(league), after_match=after_match, rows=rows)


# --------------------------------------------------------------------------- F2 scenarios
def scenarios(
    year: int, after_match: int | None = None, picks: Sequence[ScenarioPick] = ()
) -> Scenarios:
    core = data.core()
    league = _league(core, _season_matches(core, year))
    last = max((m.match_number or 0) for m in league)
    n = last if after_match is None else after_match
    if n < 0:
        raise ValueError("after_match must be >= 0")
    done, rest = _split(league, n)
    pick = {p.match_id: p.winner_id for p in picks}
    rest_ids = {m.id for m in rest}
    unknown = set(pick) - rest_ids
    if unknown:
        raise ValueError(f"picks for matches that are not remaining: {sorted(unknown)}")
    for m in rest:
        if m.id in pick and not m.has_team(pick[m.id]):
            raise ValueError(f"team {pick[m.id]} does not play match {m.id}")

    standings = compute_standings(done)
    teams_in = {t for m in league for t in (m.team1_id, m.team2_id)}
    pts = {t: 0 for t in teams_in} | {s.team_id: s.points for s in standings}
    wins = {t: 0 for t in teams_in} | {s.team_id: s.won for s in standings}
    played = {t: 0 for t in teams_in} | {s.team_id: s.played for s in standings}
    fixtures = [Fixture(m.team1_id, m.team2_id, pick.get(m.id)) for m in rest]
    res = simulate(pts, wins, fixtures)

    def r4(x: float) -> float:
        return round(x, 4)

    teams = [
        ScenarioTeam(
            team=team_ref(core, o.team_id, year),
            played=played[o.team_id],
            points=o.points,
            wins=o.wins,
            remaining=o.remaining,
            max_points=o.max_points,
            p_top4=r4(o.p_top4),
            p_top4_incl_ties=r4(o.p_top4_incl_ties),
            p_top4_tie_dependent=r4(o.p_top4_incl_ties - o.p_top4),
            p_top2=r4(o.p_top2),
            p_top2_incl_ties=r4(o.p_top2_incl_ties),
            p_top2_tie_dependent=r4(o.p_top2_incl_ties - o.p_top2),
            clinched_top4=o.clinched_top4,
            eliminated=o.eliminated,
            clinched_top2=o.clinched_top2,
            out_of_top2=o.out_of_top2,
        )
        for o in res.teams
    ]
    return Scenarios(
        season=year,
        after_match=n,
        league_matches=len(league),
        remaining_matches=len(rest),
        method=res.method,  # type: ignore[arg-type]
        outcomes_evaluated=res.outcomes,
        flags_exact=res.exact,
        teams=teams,
        remaining=[
            ScenarioFixture(
                match_id=m.id,
                match_number=m.match_number,
                date=m.date,
                team1_id=m.team1_id,
                team2_id=m.team2_id,
                actual_winner_id=m.winner_id if m.result != "no_result" else None,
                picked_winner_id=pick.get(m.id),
            )
            for m in rest
        ],
    )


# --------------------------------------------------------------------------- F3 story
def season_story(year: int, min_balls: int = 100, min_overs: int = 20) -> SeasonStory:
    core = data.core()
    ms = _season_matches(core, year)
    return build_story(core, data.players(), year, ms, min_balls=min_balls, min_overs=min_overs)


# --------------------------------------------------------------------------- D4 h2h
def head_to_head(
    a: str | int, b: str | int, season: int | None = None, venue_id: int | None = None
) -> HeadToHead:
    core = data.core()
    ta, tb = resolve_team(core, a), resolve_team(core, b)
    if ta == tb:
        raise ValueError("pick two different teams")
    ms = [
        m
        for m in core.matches
        if m.has_team(ta)
        and m.has_team(tb)
        and (season is None or m.year == season)
        and (venue_id is None or m.venue_id == venue_id)
    ]

    def score(team: int, lowest: bool) -> TeamTotalRecord | None:
        pairs = [(m, i) for m in ms for i in m.innings if i.team_id == team]
        if lowest:
            best = rank_lowest_totals(pairs, 1)
            return total_record(core, *best[0]) if best else None
        top = rank_highest_totals((i for _, i in pairs), 1)
        if not top:
            return None
        return total_record(core, core.by_id[top[0].match_id], top[0])

    venues: dict[int, list[MatchRow]] = {}
    for m in ms:
        if m.venue_id is not None:
            venues.setdefault(m.venue_id, []).append(m)
    by_venue = []
    for vid, vms in venues.items():
        v = venue_ref(core, vid)
        if v is None:
            continue
        by_venue.append(
            VenueSplit(
                venue=v,
                played=len(vms),
                team_a_won=sum(1 for m in vms if m.winner_id == ta),
                team_b_won=sum(1 for m in vms if m.winner_id == tb),
                no_result=sum(1 for m in vms if m.result == "no_result"),
            )
        )
    by_venue.sort(key=lambda s: (-s.played, s.venue.name))
    latest_year = ms[-1].year if ms else None
    return HeadToHead(
        team_a=team_ref(core, ta, latest_year),
        team_b=team_ref(core, tb, latest_year),
        season=season,
        venue_id=venue_id,
        played=len(ms),
        team_a_won=sum(1 for m in ms if m.winner_id == ta),
        team_b_won=sum(1 for m in ms if m.winner_id == tb),
        no_result=sum(1 for m in ms if m.result == "no_result"),
        tied=sum(1 for m in ms if m.result == "tie"),
        last5=[
            ResultLine(
                match_id=m.id,
                season=m.year,
                date=m.date,
                venue=venue_ref(core, m.venue_id),
                winner_id=m.winner_id,
                result_text=result_text(core, m),
            )
            for m in reversed(ms[-5:])
        ],
        team_a_highest=score(ta, False),
        team_b_highest=score(tb, False),
        team_a_lowest=score(ta, True),
        team_b_lowest=score(tb, True),
        by_venue=by_venue,
    )


# --------------------------------------------------------------------------- I1 records
def records(
    scope: str = "all", season: int | None = None, venue_id: int | None = None, limit: int = 10
) -> Records:
    if scope not in ("all", "season"):
        raise ValueError("scope must be 'all' or 'season'")
    if scope == "season" and season is None:
        raise ValueError("scope=season needs season")
    core = data.core()
    if season is not None:
        _season_matches(core, season)
    ms = [
        m
        for m in core.matches
        if (scope == "all" or m.year == season) and (venue_id is None or m.venue_id == venue_id)
    ]
    return build_records(
        core,
        data.players(),
        ms,
        scope=scope,
        season=season if scope == "season" else None,
        venue_id=venue_id,
        limit=limit,
    )


# --------------------------------------------------------------------------- matches
def list_matches(season: int | None = None, team: str | int | None = None) -> list[MatchSummary]:
    core = data.core()
    tid = resolve_team(core, team) if team is not None else None
    return [
        match_summary(core, m)
        for m in core.matches
        if (season is None or m.year == season) and (tid is None or m.has_team(tid))
    ]
