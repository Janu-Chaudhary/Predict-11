"""Records (I1) and team-vs-team (D4) leaderboards over the pre-aggregated resolved rows.

Ranking functions are pure (``rank_*``) so they can be unit-tested on synthetic rows; the
``build_*`` functions attach display references.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable, Iterable, Sequence

from .seasons_data import BatRow, BowlRow, Core, InningsRow, MatchRow, PartnershipRow, PlayerData
from .seasons_nrr import balls_to_overs
from .seasons_refs import (
    chase_quota_balls,
    is_completed_innings,
    player_ref,
    team_ref,
    venue_ref,
)
from .seasons_schemas import (
    BattingInningsRecord,
    BattingLeader,
    BowlingFiguresRecord,
    BowlingLeader,
    FastestMilestone,
    MarginRecord,
    PartnershipRecord,
    Records,
    TeamTotalRecord,
)


def _top[T](rows: Iterable[T], key: Callable[[T], tuple[float, ...]], n: int) -> list[T]:
    return sorted(rows, key=key)[:n]


# --------------------------------------------------------------------------- pure rankings
def rank_highest_totals(inns: Iterable[InningsRow], n: int) -> list[InningsRow]:
    return _top(inns, lambda i: (-i.runs, i.legal_balls, i.match_id), n)


def rank_lowest_totals(
    pairs: Iterable[tuple[MatchRow, InningsRow]], n: int
) -> list[tuple[MatchRow, InningsRow]]:
    """Lowest completed totals (all out / full quota), no-result matches and successful
    chases (the chasing side stopped because it had won) excluded."""
    ok = [
        (m, i)
        for m, i in pairs
        if m.result != "no_result"
        and is_completed_innings(m, i)
        and not (i.innings == 2 and m.result == "win" and m.winner_id == i.team_id)
    ]
    return _top(ok, lambda p: (p[1].runs, -p[1].legal_balls, p[0].id), n)


def rank_wins_by_runs(matches: Iterable[MatchRow], n: int) -> list[MatchRow]:
    ms = [m for m in matches if m.result == "win" and m.win_by_runs]
    return _top(ms, lambda m: (-(m.win_by_runs or 0), m.id), n)


def balls_remaining(m: MatchRow) -> int | None:
    inn2 = next((i for i in m.innings if i.innings == 2), None)
    return chase_quota_balls(m) - inn2.legal_balls if inn2 else None


def rank_wins_by_wickets(matches: Iterable[MatchRow], n: int) -> list[MatchRow]:
    ms = [m for m in matches if m.result == "win" and m.win_by_wickets]
    return _top(ms, lambda m: (-(m.win_by_wickets or 0), -(balls_remaining(m) or 0), m.id), n)


def rank_individual_scores(rows: Iterable[BatRow], n: int) -> list[BatRow]:
    return _top(rows, lambda b: (-b.runs, b.balls, b.match_id), n)


def rank_bowling_figures(rows: Iterable[BowlRow], n: int) -> list[BowlRow]:
    ok = [b for b in rows if b.wickets > 0]
    return _top(ok, lambda b: (-b.wickets, b.runs, b.balls, b.match_id), n)


def rank_partnerships(rows: Iterable[PartnershipRow], n: int) -> list[PartnershipRow]:
    return _top(rows, lambda p: (-p.runs, p.balls, p.match_id), n)


def rank_fastest(rows: Iterable[BatRow], milestone: int, n: int) -> list[BatRow]:
    def balls(b: BatRow) -> int | None:
        return b.balls_to_50 if milestone == 50 else b.balls_to_100

    ok = [b for b in rows if balls(b) is not None]
    return _top(ok, lambda b: (balls(b) or 0, -b.runs, b.match_id), n)


# --------------------------------------------------------------------------- builders
def rank_run_scorers(rows: Iterable[BatRow], n: int) -> list[tuple[str, list[BatRow]]]:
    per: dict[str, list[BatRow]] = defaultdict(list)
    for b in rows:
        per[b.player_id].append(b)
    ranked = sorted(per.items(), key=lambda kv: (-sum(b.runs for b in kv[1]), kv[0]))
    return ranked[:n]


def rank_wicket_takers(rows: Iterable[BowlRow], n: int) -> list[tuple[str, list[BowlRow]]]:
    per: dict[str, list[BowlRow]] = defaultdict(list)
    for b in rows:
        per[b.player_id].append(b)
    ranked = sorted(
        per.items(),
        key=lambda kv: (-sum(b.wickets for b in kv[1]), sum(b.runs for b in kv[1]), kv[0]),
    )
    return ranked[:n]


def total_record(core: Core, m: MatchRow, i: InningsRow) -> TeamTotalRecord:
    return TeamTotalRecord(
        match_id=m.id,
        season=m.year,
        date=m.date,
        team=team_ref(core, i.team_id, m.year),
        opponent=team_ref(core, m.opponent(i.team_id), m.year),
        venue=venue_ref(core, m.venue_id),
        runs=i.runs,
        wickets=i.wickets,
        overs=balls_to_overs(i.legal_balls),
    )


def _margin(core: Core, m: MatchRow, by: str) -> MarginRecord:
    assert m.winner_id is not None
    return MarginRecord(
        match_id=m.id,
        season=m.year,
        date=m.date,
        winner=team_ref(core, m.winner_id, m.year),
        loser=team_ref(core, m.opponent(m.winner_id), m.year),
        venue=venue_ref(core, m.venue_id),
        margin=(m.win_by_runs if by == "runs" else m.win_by_wickets) or 0,
        balls_remaining=balls_remaining(m) if by == "wickets" else None,
    )


def build_records(
    core: Core,
    pdata: PlayerData,
    matches: Sequence[MatchRow],
    *,
    scope: str,
    season: int | None,
    venue_id: int | None,
    limit: int,
) -> Records:
    ids = {m.id for m in matches}
    by_id = core.by_id
    names = pdata.names
    pairs = [(m, i) for m in matches for i in m.innings]
    inn_by = {(m.id, i.innings): (m, i) for m, i in pairs}

    def ctx(match_id: int, team_id: int) -> dict[str, object]:
        m = by_id[match_id]
        return {
            "match_id": m.id,
            "season": m.year,
            "date": m.date,
            "team": team_ref(core, team_id, m.year),
            "opponent": team_ref(core, m.opponent(team_id), m.year),
            "venue": venue_ref(core, m.venue_id),
        }

    bat = [b for b in pdata.batting if b.match_id in ids]
    bowl = [b for b in pdata.bowling if b.match_id in ids]
    parts = [p for p in pdata.partnerships if p.match_id in ids]

    def sr(runs: int, balls: int) -> float:
        return round(100 * runs / balls, 2) if balls else 0.0

    def milestone(b: BatRow, balls: int | None) -> FastestMilestone:
        return FastestMilestone(
            **ctx(b.match_id, b.team_id),  # type: ignore[arg-type]
            player=player_ref(names, b.player_id),
            balls=balls or 0,
            final_runs=b.runs,
        )

    def latest_team(rows: Iterable[tuple[int, int]]) -> int:
        """Team of the most recent (match_id, team_id) appearance."""
        return max(rows, key=lambda r: (by_id[r[0]].date, r[0]))[1]

    def runs_leader(pid: str, rows: list[BatRow]) -> BattingLeader:
        runs, balls = sum(b.runs for b in rows), sum(b.balls for b in rows)
        return BattingLeader(
            player=player_ref(names, pid),
            team=team_ref(core, latest_team((r.match_id, r.team_id) for r in rows), season),
            innings=len(rows),
            runs=runs,
            balls=balls,
            strike_rate=sr(runs, balls),
            fours=sum(b.fours for b in rows),
            sixes=sum(b.sixes for b in rows),
        )

    def wkts_leader(pid: str, rows: list[BowlRow]) -> BowlingLeader:
        balls, runs = sum(b.balls for b in rows), sum(b.runs for b in rows)
        return BowlingLeader(
            player=player_ref(names, pid),
            team=team_ref(core, latest_team((r.match_id, r.team_id) for r in rows), season),
            innings=len(rows),
            overs=balls_to_overs(balls),
            runs=runs,
            wickets=sum(b.wickets for b in rows),
            economy=round(6 * runs / balls, 2) if balls else 0.0,
        )

    highest = rank_highest_totals((i for _, i in pairs), limit)
    return Records(
        scope=scope,  # type: ignore[arg-type]
        season=season,
        venue_id=venue_id,
        most_runs=[runs_leader(p, rows) for p, rows in rank_run_scorers(bat, limit)],
        most_wickets=[wkts_leader(p, rows) for p, rows in rank_wicket_takers(bowl, limit)],
        highest_totals=[total_record(core, *inn_by[(i.match_id, i.innings)]) for i in highest],
        lowest_totals=[total_record(core, m, i) for m, i in rank_lowest_totals(pairs, limit)],
        biggest_wins_by_runs=[_margin(core, m, "runs") for m in rank_wins_by_runs(matches, limit)],
        biggest_wins_by_wickets=[
            _margin(core, m, "wickets") for m in rank_wins_by_wickets(matches, limit)
        ],
        highest_individual_scores=[
            BattingInningsRecord(
                **ctx(b.match_id, b.team_id),  # type: ignore[arg-type]
                player=player_ref(names, b.player_id),
                runs=b.runs,
                balls=b.balls,
                not_out=not b.out,
                fours=b.fours,
                sixes=b.sixes,
                strike_rate=sr(b.runs, b.balls),
            )
            for b in rank_individual_scores(bat, limit)
        ],
        best_bowling_figures=[
            BowlingFiguresRecord(
                **ctx(b.match_id, b.team_id),  # type: ignore[arg-type]
                player=player_ref(names, b.player_id),
                wickets=b.wickets,
                runs=b.runs,
                overs=balls_to_overs(b.balls),
            )
            for b in rank_bowling_figures(bowl, limit)
        ],
        highest_partnerships=[
            PartnershipRecord(
                **ctx(p.match_id, p.team_id),  # type: ignore[arg-type]
                wicket=p.wicket,
                batter1=player_ref(names, p.player1_id),
                batter2=player_ref(names, p.player2_id),
                runs=p.runs,
                balls=p.balls,
                batter1_runs=p.player1_runs,
                batter2_runs=p.player2_runs,
            )
            for p in rank_partnerships(parts, limit)
        ],
        fastest_fifties=[milestone(b, b.balls_to_50) for b in rank_fastest(bat, 50, limit)],
        fastest_hundreds=[milestone(b, b.balls_to_100) for b in rank_fastest(bat, 100, limit)],
    )
