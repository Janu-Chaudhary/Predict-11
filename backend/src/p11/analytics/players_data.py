"""DB access for player / matchup / venue analytics.

Reads only the ``*_resolved`` views (never the raw multi-source tables) and drops super-over
balls. Small, slowly-changing reference data (IPL matches, innings teams, appearances) and the
bulk per-innings cards used by league-wide endpoints (milestones, streaks, venue leaders,
search ranking) are cached in-process, keyed by DB URL and a cheap fingerprint of the ``match``
table that is re-checked at most every ``FINGERPRINT_TTL_S`` seconds.

The bulk cards are computed in SQL with exactly the definitions of ``players_stats`` (an
integration test cross-checks them against the Python path ball-for-ball).
"""

from __future__ import annotations

import datetime as dt
import threading
import time
from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import Connection, text

from .players_stats import Ball, BattingCard, BowlingCard, Fielding

FINGERPRINT_TTL_S = 60.0
PLAYING_ROLES = ("xi", "impact_in", "impact_out")

_NOT_DISMISSALS_SQL = "('retired hurt', 'retired not out')"
_NOT_BOWLER_WKTS_SQL = (
    "('run out', 'retired hurt', 'retired out', 'retired not out', 'obstructing the field')"
)


@dataclass(frozen=True, slots=True)
class MatchInfo:
    id: int
    date: dt.date
    season: int
    venue_id: int | None
    team1_id: int
    team2_id: int
    toss_winner_id: int | None
    toss_decision: str | None
    result: str
    winner_id: int | None
    method: str | None
    stage: str | None

    def opponent(self, team_id: int) -> int:
        return self.team2_id if team_id == self.team1_id else self.team1_id


@dataclass(slots=True)
class InningsTotal:
    match_id: int
    innings: int
    team_id: int
    runs: int = 0
    wickets: int = 0
    legal_balls: int = 0
    target_overs: float | None = None
    phase_runs: dict[str, int] = field(default_factory=dict)
    phase_balls: dict[str, int] = field(default_factory=dict)
    phase_wickets: dict[str, int] = field(default_factory=dict)


@dataclass(slots=True)
class Reference:
    """IPL matches + innings + names, sorted chronologically."""

    matches: dict[int, MatchInfo]
    order: dict[int, int]  # match_id -> chronological rank
    batting_team: dict[tuple[int, int], int]  # (match, innings) -> team_id
    innings: list[InningsTotal]
    teams: dict[int, str]
    venues: dict[int, tuple[str, str | None]]  # id -> (name, city)
    appearances: dict[str, list[tuple[int, int]]]  # player -> [(match_id, team_id)] chrono

    @property
    def latest_season(self) -> int | None:
        return max((m.season for m in self.matches.values()), default=None)

    def bowling_team(self, match_id: int, innings: int) -> int | None:
        bat = self.batting_team.get((match_id, innings))
        m = self.matches.get(match_id)
        return m.opponent(bat) if m and bat is not None else None


@dataclass(slots=True)
class Bulk:
    """League-wide per-innings cards keyed by player (chronological)."""

    batting: dict[str, list[BattingCard]]
    bowling: dict[str, list[BowlingCard]]
    fielding: dict[str, dict[int, Fielding]]  # player -> match -> fielding


# --------------------------------------------------------------------------- cache
_lock = threading.Lock()
_cache: dict[tuple[str, str], tuple[Any, Any]] = {}  # (url, name) -> (fingerprint, value)
_fp_checked: dict[str, tuple[float, Any]] = {}


def _fingerprint(conn: Connection) -> Any:
    url = str(conn.engine.url)
    now = time.monotonic()
    hit = _fp_checked.get(url)
    if hit and now - hit[0] < FINGERPRINT_TTL_S:
        return hit[1]
    row = conn.execute(
        text(
            "SELECT count(*), coalesce(sum(id), 0), max(start_date), "
            "string_agg(DISTINCT ball_source, ',') FROM match"
        )
    ).one()
    fp = tuple(row)
    _fp_checked[url] = (now, fp)
    return fp


def cached[T](conn: Connection, name: str, build: Callable[[Connection], T]) -> T:
    url = str(conn.engine.url)
    fp = _fingerprint(conn)
    hit = _cache.get((url, name))
    if hit and hit[0] == fp:
        return hit[1]  # type: ignore[no-any-return]
    with _lock:
        hit = _cache.get((url, name))
        if hit and hit[0] == fp:
            return hit[1]  # type: ignore[no-any-return]
        value = build(conn)
        _cache[(url, name)] = (fp, value)
        return value


def clear_cache() -> None:
    with _lock:
        _cache.clear()
        _fp_checked.clear()


# --------------------------------------------------------------------------- reference data
def _build_reference(conn: Connection) -> Reference:
    rows = conn.execute(
        text(
            """
            SELECT m.id, m.start_date, s.year, m.venue_id, m.team1_id, m.team2_id,
                   m.toss_winner_id, m.toss_decision, m.result, m.winner_id, m.method, m.stage
            FROM match m
            JOIN season s ON s.id = m.season_id
            JOIN competition c ON c.id = s.competition_id AND c.code = 'ipl'
            ORDER BY m.start_date, m.id
            """
        )
    ).all()
    matches = {r[0]: MatchInfo(*r) for r in rows}
    order = {mid: i for i, mid in enumerate(matches)}

    batting_team: dict[tuple[int, int], int] = {}
    tot: dict[tuple[int, int], InningsTotal] = {}
    for mid, inn, team, target_overs in conn.execute(
        text(
            "SELECT match_id, innings, team_id, target_overs FROM innings_resolved "
            "WHERE NOT super_over"
        )
    ):
        if mid in matches:
            batting_team[(mid, inn)] = team
            tot[(mid, inn)] = InningsTotal(
                mid, inn, team, target_overs=float(target_overs) if target_overs else None
            )
    for mid, inn, phase, runs, wkts, legal in conn.execute(
        text(
            f"""
            SELECT match_id, innings,
                   CASE WHEN over <= 5 THEN 'powerplay' WHEN over <= 14 THEN 'middle'
                        ELSE 'death' END AS phase,
                   sum(total_runs),
                   count(*) FILTER (WHERE player_out_id IS NOT NULL
                                    AND wicket_kind NOT IN {_NOT_DISMISSALS_SQL}),
                   count(*) FILTER (WHERE wides = 0 AND noballs = 0)
            FROM delivery_resolved WHERE NOT super_over
            GROUP BY 1, 2, 3
            """
        )
    ):
        t = tot.get((mid, inn))
        if t is None:
            continue
        t.runs += runs
        t.wickets += wkts
        t.legal_balls += legal
        t.phase_runs[phase] = runs
        t.phase_balls[phase] = legal
        t.phase_wickets[phase] = wkts
    innings = sorted(tot.values(), key=lambda t: (order[t.match_id], t.innings))

    teams: dict[int, str] = dict(conn.execute(text("SELECT id, name FROM team")).all())
    venues = {r[0]: (r[1], r[2]) for r in conn.execute(text("SELECT id, name, city FROM venue"))}

    apps: dict[str, list[tuple[int, int]]] = defaultdict(list)
    for mid, pid, team in conn.execute(
        text(
            "SELECT match_id, player_id, team_id FROM match_player_resolved "
            "WHERE role_in_match = ANY(:roles)"
        ),
        {"roles": list(PLAYING_ROLES)},
    ):
        if mid in matches:
            apps[pid].append((mid, team))
    for lst in apps.values():
        lst.sort(key=lambda x: order[x[0]])
    return Reference(matches, order, batting_team, innings, teams, venues, dict(apps))


def reference(conn: Connection) -> Reference:
    return cached(conn, "reference", _build_reference)


# --------------------------------------------------------------------------- balls
_BALL_COLS = (
    "d.match_id, d.innings, d.over, d.batter_id, d.bowler_id, d.non_striker_id, d.batter_runs, "
    "d.wides, d.noballs, d.byes, d.legbyes, d.penalty, d.non_boundary, d.wicket_kind, "
    "d.player_out_id, d.fielder_ids"
)


def fetch_balls(conn: Connection, where: str, params: dict[str, Any]) -> list[Ball]:
    """Non-super-over IPL balls matching ``where`` (SQL over alias ``d``), chronological."""
    ref = reference(conn)
    rows = conn.execute(
        text(
            f"SELECT {_BALL_COLS} FROM delivery_resolved d "
            f"WHERE NOT d.super_over AND ({where}) ORDER BY d.match_id, d.innings, d.ball_seq"
        ),
        params,
    ).all()
    balls = [
        Ball(
            r[0],
            r[1],
            r[2],
            r[3],
            r[4],
            r[5],
            r[6],
            r[7],
            r[8],
            r[9],
            r[10],
            r[11],
            r[12],
            r[13],
            r[14],
            tuple(r[15]) if r[15] else (),
        )
        for r in rows
        if r[0] in ref.matches
    ]
    balls.sort(key=lambda b: ref.order[b.match_id])  # stable: keeps innings/ball order
    return balls


def player_balls(conn: Connection, pid: str) -> list[Ball]:
    """Every ball in which ``pid`` batted, bowled, was out, or fielded in a dismissal."""
    return fetch_balls(
        conn,
        "d.batter_id = :p OR d.non_striker_id = :p OR d.bowler_id = :p OR d.player_out_id = :p "
        "OR (d.wicket_kind IS NOT NULL AND :p = ANY(d.fielder_ids))",
        {"p": pid},
    )


# --------------------------------------------------------------------------- bulk cards
_BULK_BAT_SQL = f"""
SELECT pid, match_id, innings, sum(runs)::int, sum(balls)::int, sum(fours)::int, sum(sixes)::int,
       sum(dots)::int, max(how)
FROM (
    SELECT batter_id AS pid, match_id, innings, sum(batter_runs) AS runs,
           count(*) FILTER (WHERE wides = 0) AS balls,
           count(*) FILTER (WHERE batter_runs = 4 AND NOT non_boundary) AS fours,
           count(*) FILTER (WHERE batter_runs = 6 AND NOT non_boundary) AS sixes,
           count(*) FILTER (WHERE wides = 0 AND noballs = 0 AND batter_runs = 0) AS dots,
           NULL::text AS how
    FROM delivery_resolved WHERE NOT super_over GROUP BY 1, 2, 3
    UNION ALL
    SELECT DISTINCT non_striker_id, match_id, innings, 0, 0, 0, 0, 0, NULL
    FROM delivery_resolved WHERE NOT super_over
    UNION ALL
    SELECT player_out_id, match_id, innings, 0, 0, 0, 0, 0,
           CASE WHEN wicket_kind NOT IN {_NOT_DISMISSALS_SQL} THEN wicket_kind END
    FROM delivery_resolved WHERE NOT super_over AND player_out_id IS NOT NULL
) x
GROUP BY 1, 2, 3
"""

_BULK_BOWL_SQL = f"""
SELECT bowler_id, match_id, innings, sum(legal)::int, sum(r)::int, sum(w)::int, sum(dots)::int,
       (count(*) FILTER (WHERE legal >= 6 AND r = 0))::int, sum(wd)::int, sum(nb)::int,
       sum(f4)::int, sum(s6)::int
FROM (
    SELECT bowler_id, match_id, innings, over,
           count(*) FILTER (WHERE wides = 0 AND noballs = 0) AS legal,
           sum(batter_runs + wides + noballs) AS r,
           count(*) FILTER (WHERE player_out_id IS NOT NULL
                            AND wicket_kind NOT IN {_NOT_BOWLER_WKTS_SQL}) AS w,
           count(*) FILTER (WHERE wides = 0 AND noballs = 0 AND batter_runs = 0) AS dots,
           count(*) FILTER (WHERE wides > 0) AS wd,
           count(*) FILTER (WHERE noballs > 0) AS nb,
           count(*) FILTER (WHERE batter_runs = 4 AND NOT non_boundary) AS f4,
           count(*) FILTER (WHERE batter_runs = 6 AND NOT non_boundary) AS s6
    FROM delivery_resolved WHERE NOT super_over
    GROUP BY 1, 2, 3, 4
) o
GROUP BY 1, 2, 3
"""

_BULK_FIELD_SQL = """
WITH d AS (SELECT * FROM delivery_resolved
           WHERE NOT super_over AND player_out_id IS NOT NULL)
SELECT f.pid, d.match_id, d.wicket_kind, count(*)
FROM d CROSS JOIN LATERAL unnest(d.fielder_ids) AS f(pid)
WHERE d.wicket_kind IN ('caught', 'stumped', 'run out')
GROUP BY 1, 2, 3
UNION ALL
SELECT bowler_id, match_id, 'caught', count(*) FROM d
WHERE wicket_kind = 'caught and bowled' GROUP BY 1, 2
"""


def _build_bulk(conn: Connection) -> Bulk:
    ref = reference(conn)
    bat: dict[str, list[BattingCard]] = defaultdict(list)
    for pid, mid, inn, runs, balls, fours, sixes, dots, how in conn.execute(text(_BULK_BAT_SQL)):
        if mid in ref.matches:
            bat[pid].append(
                BattingCard(mid, inn, runs, balls, fours, sixes, dots, how is not None, how)
            )
    bowl: dict[str, list[BowlingCard]] = defaultdict(list)
    for r in conn.execute(text(_BULK_BOWL_SQL)):
        if r[1] in ref.matches:
            bowl[r[0]].append(BowlingCard(r[1], r[2], *r[3:]))
    fld: dict[str, dict[int, Fielding]] = defaultdict(dict)
    for pid, mid, kind, n in conn.execute(text(_BULK_FIELD_SQL)):
        if mid not in ref.matches:
            continue
        f = fld[pid].setdefault(mid, Fielding())
        if kind == "caught":
            f.catches += n
        elif kind == "stumped":
            f.stumpings += n
        else:
            f.run_outs += n

    def chrono(c: BattingCard | BowlingCard) -> tuple[int, int]:
        return ref.order[c.match_id], c.innings

    for lst in bat.values():
        lst.sort(key=chrono)
    for blst in bowl.values():
        blst.sort(key=chrono)
    return Bulk(dict(bat), dict(bowl), dict(fld))


def bulk(conn: Connection) -> Bulk:
    return cached(conn, "bulk", _build_bulk)


# --------------------------------------------------------------------------- names
def player_names(conn: Connection, ids: set[str] | list[str]) -> dict[str, str]:
    if not ids:
        return {}
    return dict(
        conn.execute(
            text("SELECT id, name FROM player WHERE id = ANY(:ids)"), {"ids": list(ids)}
        ).all()
    )


def parse_since(since: str | None) -> dt.date | None:
    """``2023`` -> 2023-01-01; ``2024-04-01`` -> that date; None/'' -> None."""
    if not since:
        return None
    s = since.strip()
    if len(s) == 4 and s.isdigit():
        return dt.date(int(s), 1, 1)
    return dt.date.fromisoformat(s)
