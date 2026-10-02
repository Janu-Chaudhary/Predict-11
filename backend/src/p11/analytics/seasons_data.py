"""Read-side data access for the seasons analytics, with an in-process cache.

Everything here reads the *resolved* views (``innings_resolved``, ``delivery_resolved``) so
results follow the per-source merge. Super-over innings/balls are excluded from every
aggregate here; whether a match had a super over is carried as a flag on the match.

The whole IPL history is small (≈1.2k matches, ≈2.5k innings, ≈17k batting innings), so the
pre-aggregated rows are loaded once and every endpoint filters them in Python. The cache is
invalidated by a cheap fingerprint of the write counters on the source tables, checked at
most every ``_RECHECK_S`` seconds; the same fingerprint is the HTTP ETag.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any

from sqlalchemy import text

from ..core import db

_RECHECK_S = 10.0
_MAX_SLOTS = 1024

# Kinds that do not count as a dismissal of the batting side's wicket for "all out".
NOT_A_WICKET = ("retired hurt", "retired not out")
# Kinds not credited to the bowler.
NOT_BOWLER_WICKET = (
    "run out",
    "retired hurt",
    "retired out",
    "retired not out",
    "obstructing the field",
)


# --------------------------------------------------------------------------- rows
@dataclass(frozen=True, slots=True)
class InningsRow:
    match_id: int
    innings: int
    team_id: int
    runs: int
    legal_balls: int
    wickets: int
    absent_hurt: int
    target_runs: int | None
    target_overs: Decimal | None


@dataclass(frozen=True, slots=True)
class MatchRow:
    id: int
    year: int
    date: dt.date
    match_number: int | None
    stage: str | None
    venue_id: int | None
    city: str | None
    team1_id: int
    team2_id: int
    toss_winner_id: int | None
    toss_decision: str | None
    result: str  # win | tie | no_result
    winner_id: int | None
    win_by_runs: int | None
    win_by_wickets: int | None
    method: str | None
    overs: int
    super_over: bool
    innings: tuple[InningsRow, ...]  # regulation innings only, ordered

    @property
    def league(self) -> bool:
        return self.stage is None

    def opponent(self, team_id: int) -> int:
        return self.team2_id if team_id == self.team1_id else self.team1_id

    def has_team(self, team_id: int) -> bool:
        return team_id in (self.team1_id, self.team2_id)


@dataclass(frozen=True, slots=True)
class TeamRow:
    id: int
    name: str


@dataclass(frozen=True, slots=True)
class VenueRow:
    id: int
    name: str
    city: str | None


@dataclass(frozen=True, slots=True)
class SeasonRow:
    id: int
    year: int
    source_label: str


@dataclass(frozen=True, slots=True)
class Core:
    matches: tuple[MatchRow, ...]  # chronological
    by_id: dict[int, MatchRow]
    teams: dict[int, TeamRow]
    venues: dict[int, VenueRow]
    seasons: dict[int, SeasonRow]  # by year

    def season_matches(self, year: int) -> list[MatchRow]:
        return [m for m in self.matches if m.year == year]


@dataclass(frozen=True, slots=True)
class BatRow:
    match_id: int
    innings: int
    player_id: str
    team_id: int
    runs: int
    balls: int
    fours: int
    sixes: int
    out: bool
    balls_to_50: int | None
    balls_to_100: int | None


@dataclass(frozen=True, slots=True)
class BowlRow:
    match_id: int
    innings: int
    player_id: str
    team_id: int  # bowling side
    balls: int
    runs: int
    wickets: int
    dots: int


@dataclass(frozen=True, slots=True)
class PartnershipRow:
    match_id: int
    innings: int
    team_id: int
    wicket: int  # 1 = opening stand
    player1_id: str
    player2_id: str
    runs: int
    balls: int
    player1_runs: int
    player2_runs: int


@dataclass(frozen=True, slots=True)
class PlayerData:
    batting: tuple[BatRow, ...]
    bowling: tuple[BowlRow, ...]
    partnerships: tuple[PartnershipRow, ...]
    names: dict[str, str]
    display_names: dict[str, str] = field(default_factory=dict)
    images: dict[str, str] = field(default_factory=dict)


# --------------------------------------------------------------------------- SQL
_SQL_MATCHES = """
select m.id, s.year, m.start_date, m.match_number, m.stage, m.venue_id, m.city,
       m.team1_id, m.team2_id, m.toss_winner_id, m.toss_decision, m.result, m.winner_id,
       m.win_by_runs, m.win_by_wickets, m.method, m.overs,
       exists (select 1 from innings_resolved i where i.match_id = m.id and i.super_over)
from match m join season s on s.id = m.season_id
order by m.start_date, m.match_number nulls last, m.id
"""

_SQL_INNINGS = f"""
select i.match_id, i.innings, i.team_id, coalesce(sum(d.total_runs), 0)::int,
       (count(d.ball_seq) filter (where d.wides = 0 and d.noballs = 0))::int,
       (count(d.player_out_id) filter (where d.wicket_kind not in {NOT_A_WICKET!r}))::int,
       coalesce(cardinality(i.absent_hurt), 0), i.target_runs, i.target_overs
from innings_resolved i
left join delivery_resolved d on d.match_id = i.match_id and d.innings = i.innings
where not i.super_over
group by i.match_id, i.innings, i.team_id, i.absent_hurt, i.target_runs, i.target_overs
"""

_SQL_BATTING = """
with agg as (
  select match_id, innings, batter_id, sum(batter_runs)::int runs,
         (count(*) filter (where wides = 0))::int balls,
         (count(*) filter (where batter_runs = 4 and not non_boundary))::int fours,
         (count(*) filter (where batter_runs = 6 and not non_boundary))::int sixes
  from delivery_resolved where not super_over group by 1, 2, 3
), cum as (
  select d.match_id, d.innings, d.batter_id,
         sum(d.batter_runs) over w cr, sum((d.wides = 0)::int) over w cb
  from delivery_resolved d join agg a using (match_id, innings, batter_id)
  where not d.super_over and a.runs >= 50
  window w as (partition by d.match_id, d.innings, d.batter_id order by d.ball_seq)
), ms as (
  select match_id, innings, batter_id,
         min(cb) filter (where cr >= 50) b50, min(cb) filter (where cr >= 100) b100
  from cum group by 1, 2, 3
), outs as (
  select distinct match_id, innings, player_out_id batter_id from delivery_resolved
  where not super_over and player_out_id is not null
    and wicket_kind not in ('retired hurt', 'retired not out')
)
select a.match_id, a.innings, a.batter_id, a.runs, a.balls, a.fours, a.sixes,
       (o.batter_id is not null), ms.b50::int, ms.b100::int
from agg a
left join ms using (match_id, innings, batter_id)
left join outs o using (match_id, innings, batter_id)
"""

_SQL_BOWLING = f"""
select match_id, innings, bowler_id,
       (count(*) filter (where wides = 0 and noballs = 0))::int,
       sum(total_runs - byes - legbyes - penalty)::int,
       (count(player_out_id) filter (where wicket_kind not in {NOT_BOWLER_WICKET!r}))::int,
       (count(*) filter (where total_runs = 0))::int
from delivery_resolved where not super_over group by 1, 2, 3
"""

_SQL_PARTNERSHIPS = """
with b as (
  select match_id, innings, ball_seq, batter_id, batter_runs, total_runs, wides, noballs,
         least(batter_id, non_striker_id) p1, greatest(batter_id, non_striker_id) p2
  from delivery_resolved where not super_over
)
select match_id, innings, p1, p2, min(ball_seq) first_ball, sum(total_runs)::int runs,
       (count(*) filter (where wides = 0 and noballs = 0))::int balls,
       coalesce(sum(batter_runs) filter (where batter_id = p1), 0)::int,
       coalesce(sum(batter_runs) filter (where batter_id = p2), 0)::int
from b group by 1, 2, 3, 4
"""

_SQL_FINGERPRINT = """
select coalesce(string_agg(relname || ':' || (n_tup_ins + n_tup_upd + n_tup_del)::text, ','
                           order by relname), '')
from pg_stat_user_tables
where relname in ('match', 'match_source', 'innings', 'delivery', 'team', 'team_alias',
                  'venue', 'season', 'player', 'player_alias', 'player_media')
"""


def _rows(sql: str, **params: Any) -> list[Any]:
    with db.engine().connect() as c:
        return list(c.execute(text(sql), params))


def load_core() -> Core:
    inns: dict[int, list[InningsRow]] = {}
    for r in _rows(_SQL_INNINGS):
        inns.setdefault(r[0], []).append(
            InningsRow(r[0], r[1], r[2], r[3], r[4], r[5], r[6], r[7], r[8])
        )
    matches: list[MatchRow] = []
    for r in _rows(_SQL_MATCHES):
        own = tuple(sorted(inns.get(r[0], []), key=lambda i: i.innings))
        matches.append(
            MatchRow(
                id=r[0],
                year=r[1],
                date=r[2],
                match_number=r[3],
                stage=r[4],
                venue_id=r[5],
                city=r[6],
                team1_id=r[7],
                team2_id=r[8],
                toss_winner_id=r[9],
                toss_decision=r[10],
                result=r[11],
                winner_id=r[12],
                win_by_runs=r[13],
                win_by_wickets=r[14],
                method=r[15],
                overs=r[16],
                super_over=bool(r[17]),
                innings=own,
            )
        )
    teams = {r[0]: TeamRow(r[0], r[1]) for r in _rows("select id, name from team")}
    venues = {r[0]: VenueRow(r[0], r[1], r[2]) for r in _rows("select id, name, city from venue")}
    comp = (
        "select s.id, s.year, s.label from season s join competition c on c.id = s.competition_id"
        " where c.code = 'ipl'"
    )
    seasons = {r[1]: SeasonRow(r[0], r[1], r[2]) for r in _rows(comp)}
    return Core(tuple(matches), {m.id: m for m in matches}, teams, venues, seasons)


def load_players(core: Core) -> PlayerData:
    def batting_team(match_id: int, innings: int) -> int | None:
        m = core.by_id.get(match_id)
        if m is None:
            return None
        for i in m.innings:
            if i.innings == innings:
                return i.team_id
        return None

    bat: list[BatRow] = []
    for r in _rows(_SQL_BATTING):
        t = batting_team(r[0], r[1])
        if t is not None:
            bat.append(BatRow(r[0], r[1], r[2], t, r[3], r[4], r[5], r[6], bool(r[7]), r[8], r[9]))
    bowl: list[BowlRow] = []
    for r in _rows(_SQL_BOWLING):
        t = batting_team(r[0], r[1])
        if t is not None:
            bowl.append(BowlRow(r[0], r[1], r[2], core.by_id[r[0]].opponent(t), *r[3:7]))
    raw_parts = sorted(_rows(_SQL_PARTNERSHIPS), key=lambda r: (r[0], r[1], r[4]))
    parts: list[PartnershipRow] = []
    wicket_no: dict[tuple[int, int], int] = {}
    for r in raw_parts:
        t = batting_team(r[0], r[1])
        if t is None:
            continue
        key = (r[0], r[1])
        wicket_no[key] = wicket_no.get(key, 0) + 1
        parts.append(PartnershipRow(r[0], r[1], t, wicket_no[key], r[2], r[3], *r[5:9]))
    ids = {b.player_id for b in bat} | {b.player_id for b in bowl}
    names = {r[0]: r[1] for r in _rows("select id, name from player") if r[0] in ids}
    displays = {
        r[0]: r[1]
        for r in _rows(
            "select distinct on (player_id) player_id, name from player_alias "
            "where source = 'display' order by player_id, name"
        )
        if r[0] in ids
    }
    images = {
        r[0]: r[1]
        for r in _rows(
            "select player_id, coalesce(local_path, image_url) from player_media_resolved"
        )
        if r[0] in ids and r[1]
    }
    return PlayerData(tuple(bat), tuple(bowl), tuple(parts), names, displays, images)


# --------------------------------------------------------------------------- cache
@dataclass
class _Slot:
    value: Any = None
    fingerprint: str | None = None


@dataclass
class _Cache:
    lock: threading.RLock = field(default_factory=threading.RLock)
    fingerprint: str | None = None
    checked_at: float = 0.0
    slots: dict[str, _Slot] = field(default_factory=dict)


_cache = _Cache()


def fingerprint() -> str:
    """Short hash of the source tables' write counters (re-read at most every 10 s)."""
    with _cache.lock:
        now = time.monotonic()
        if _cache.fingerprint is None or now - _cache.checked_at > _RECHECK_S:
            raw = _rows(_SQL_FINGERPRINT)[0][0] or ""
            _cache.fingerprint = hashlib.sha1(raw.encode()).hexdigest()[:16]
            _cache.checked_at = now
        return _cache.fingerprint


def _cached[T](name: str, loader: Callable[[], T]) -> T:
    fp = fingerprint()
    with _cache.lock:
        if name not in _cache.slots and len(_cache.slots) >= _MAX_SLOTS:
            for k in [k for k in _cache.slots if k.startswith("memo:")]:
                del _cache.slots[k]
        slot = _cache.slots.setdefault(name, _Slot())
        if slot.fingerprint != fp:
            slot.value = loader()
            slot.fingerprint = fp
        return slot.value  # type: ignore[no-any-return]


def core() -> Core:
    return _cached("core", load_core)


def players() -> PlayerData:
    c = core()
    return _cached("players", lambda: load_players(c))


def memo[T](name: str, compute: Callable[[], T]) -> T:
    """Cache a derived result under ``name`` for the current data fingerprint."""
    return _cached("memo:" + name, compute)


def clear_cache() -> None:
    with _cache.lock:
        _cache.slots.clear()
        _cache.fingerprint = None
