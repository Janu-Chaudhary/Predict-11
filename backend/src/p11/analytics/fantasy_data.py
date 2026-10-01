"""Read side for the fantasy analytics: persisted Dream11 points + credits + roles, cached.

Source of truth is ``player_match_points`` (one row per lineup member per match, computed by
p11.fantasy.compute). Only IPL matches are loaded. No-result matches are stored with 0 for
everyone; they are kept here (flagged through the match) and every consumer drops them from
distributions, leaderboards and hindsight XIs.

All of it (≈28k small rows) is loaded once into memory and re-used until a cheap fingerprint of
the write counters of the source tables changes (checked at most every ``_RECHECK_S`` s).
Derived results are memoised under the same fingerprint (``memo``).
"""

from __future__ import annotations

import bisect
import datetime as dt
import hashlib
import threading
import time
from collections import Counter
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import text

from ..core import db
from ..registry.credits import credits_for_season
from . import seasons_data
from .seasons_data import Core, MatchRow

_RECHECK_S = 10.0
_MAX_MEMO = 2048
FORM_WINDOW = 5  # "naive form" = mean of the last N scored appearances


@dataclass(frozen=True, slots=True)
class PointsRow:
    match_id: int
    player_id: str
    team_id: int
    role: str  # role_used by the scorer for this match
    status: str
    batting: int
    bowling: int
    fielding: int
    lineup: int
    bonuses: int
    total: int
    year: int
    date: dt.date
    seq: int  # chronological rank of the match


@dataclass(frozen=True, slots=True)
class SeasonCredits:
    season: int
    effective: int | None  # season whose credits apply (fallback, e.g. 2026 -> 2025)
    credits: dict[str, float]


@dataclass(slots=True)
class FantasyData:
    core: Core
    seq: dict[int, int]  # match id -> chronological rank
    rows: list[PointsRow]  # chronological; no-result matches included
    by_match: dict[int, list[PointsRow]]
    by_player: dict[str, list[PointsRow]]  # chronological, scored (no-result excluded)
    by_season: dict[int, list[PointsRow]]  # scored rows only
    names: dict[str, str]
    roles: dict[str, str]  # player_attribute_resolved.playing_role
    images: dict[str, str]
    credits: dict[int, SeasonCredits] = field(default_factory=dict)
    _form_seq: dict[str, list[int]] = field(default_factory=dict)
    _form_cum: dict[str, list[int]] = field(default_factory=dict)

    def match(self, match_id: int) -> MatchRow | None:
        return self.core.by_id.get(match_id)

    def no_result(self, match_id: int) -> bool:
        m = self.core.by_id.get(match_id)
        return m is None or m.result == "no_result"

    def role_of(self, player_id: str, rows: list[PointsRow] | None = None) -> str:
        """Profile role, else the role the scorer used most often."""
        r = self.roles.get(player_id)
        if r:
            return r
        rs = rows if rows is not None else self.by_player.get(player_id, [])
        if not rs:
            return "BAT"
        return Counter(x.role for x in rs).most_common(1)[0][0]

    def credits_for(self, season: int) -> SeasonCredits:
        return self.credits.get(season) or SeasonCredits(season, None, {})

    def form(self, player_id: str, before_seq: int, window: int = FORM_WINDOW) -> float | None:
        """Mean points of the player's last ``window`` scored IPL games before ``before_seq``."""
        seqs = self._form_seq.get(player_id)
        if not seqs:
            return None
        k = bisect.bisect_left(seqs, before_seq)
        if k == 0:
            return None
        lo = max(0, k - window)
        cum = self._form_cum[player_id]
        return (cum[k] - cum[lo]) / (k - lo)


_SQL_POINTS = """
select pmp.match_id, pmp.player_id, pmp.team_id, pmp.role_used, pmp.status, pmp.batting,
       pmp.bowling, pmp.fielding, pmp.lineup, pmp.bonuses, pmp.total
from player_match_points pmp
join match m on m.id = pmp.match_id
join season s on s.id = m.season_id
join competition c on c.id = s.competition_id and c.code = 'ipl'
"""

_SQL_FINGERPRINT = """
select coalesce(string_agg(relname || ':' || (n_tup_ins + n_tup_upd + n_tup_del)::text, ','
                           order by relname), '')
from pg_stat_user_tables
where relname in ('player_match_points', 'match', 'season_credits', 'player_attribute',
                  'player_media', 'player', 'team', 'season')
"""


def load() -> FantasyData:
    core = seasons_data.core()
    seq = {m.id: i for i, m in enumerate(core.matches)}
    with db.engine().connect() as conn:
        raw = conn.execute(text(_SQL_POINTS)).all()
        names: dict[str, str] = {
            r[0]: r[1] for r in conn.execute(text("select id, name from player"))
        }
        roles = {
            r[0]: r[1]
            for r in conn.execute(
                text("select player_id, playing_role from player_attribute_resolved")
            )
            if r[1]
        }
        images: dict[str, str] = dict(
            conn.execute(text("select player_id, image_url from player_media_resolved")).all()
        )
        credits: dict[int, SeasonCredits] = {}
        for year in sorted(core.seasons):
            eff, cmap = credits_for_season(conn, year)
            if eff is not None:
                credits[year] = SeasonCredits(year, eff, {k: float(v) for k, v in cmap.items()})
    rows: list[PointsRow] = []
    for r in raw:
        m = core.by_id.get(r[0])
        if m is None:
            continue
        rows.append(
            PointsRow(
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
                year=m.year,
                date=m.date,
                seq=seq[r[0]],
            )
        )
    rows.sort(key=lambda x: (x.seq, x.player_id))
    data = FantasyData(core, seq, rows, {}, {}, {}, names, roles, images, credits)
    for x in rows:
        data.by_match.setdefault(x.match_id, []).append(x)
        if core.by_id[x.match_id].result == "no_result":
            continue
        data.by_player.setdefault(x.player_id, []).append(x)
        data.by_season.setdefault(x.year, []).append(x)
    for pid, prs in data.by_player.items():
        data._form_seq[pid] = [x.seq for x in prs]
        cum = [0]
        for x in prs:
            cum.append(cum[-1] + x.total)
        data._form_cum[pid] = cum
    return data


# --------------------------------------------------------------------------- cache
_lock = threading.RLock()
_state: dict[str, Any] = {"fp": None, "checked": 0.0, "data": None, "data_fp": None}
_memo: dict[str, tuple[str, Any]] = {}


def fingerprint() -> str:
    with _lock:
        now = time.monotonic()
        if _state["fp"] is None or now - _state["checked"] > _RECHECK_S:
            with db.engine().connect() as conn:
                raw = conn.execute(text(_SQL_FINGERPRINT)).scalar() or ""
            _state["fp"] = hashlib.sha1(raw.encode()).hexdigest()[:16]
            _state["checked"] = now
        return str(_state["fp"])


def data() -> FantasyData:
    fp = fingerprint()
    with _lock:
        if _state["data"] is None or _state["data_fp"] != fp:
            _state["data"] = load()
            _state["data_fp"] = fp
        return _state["data"]  # type: ignore[no-any-return]


def memo[T](key: str, compute: Callable[[], T]) -> T:
    fp = fingerprint()
    hit = _memo.get(key)
    if hit is not None and hit[0] == fp:
        return hit[1]  # type: ignore[no-any-return]
    value = compute()
    with _lock:
        if len(_memo) >= _MAX_MEMO:
            _memo.clear()
        _memo[key] = (fp, value)
    return value


def clear_cache() -> None:
    with _lock:
        _state.update(fp=None, checked=0.0, data=None, data_fp=None)
        _memo.clear()
