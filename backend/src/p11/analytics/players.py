"""Player analytics: search (autocomplete), profile (C1) and comparison (C3).

Career / season / venue / opposition lines come from the cached per-innings cards
(``players_data.bulk``); phase splits are computed from the player's balls with the pure
definitions in ``players_stats``.
"""

from __future__ import annotations

import datetime as dt
from collections import Counter, defaultdict
from collections.abc import Callable, Iterable

from sqlalchemy import Connection, text

from .players_data import Bulk, Reference, bulk, fetch_balls, reference
from .players_identity import identity, match_quality, name_index, normalize
from .players_models import (
    BattingStats,
    BowlingStats,
    CompareEntry,
    CompareResponse,
    FieldingStats,
    Filters,
    FormBat,
    FormBowl,
    PhaseBatting,
    PhaseBowling,
    PlayerProfile,
    SearchHit,
    SearchResponse,
    SeasonLine,
    Split,
    TeamSpan,
)
from .players_stats import (
    PHASES,
    Ball,
    Fielding,
    batting_line,
    batting_phases,
    bowling_line,
    bowling_phases,
    group_by,
    overs_str,
)

FORM_N = 10
SPLIT_LIMIT = 10

MatchFilter = Callable[[int], bool]


def match_filter(ref: Reference, season: int | None, since: dt.date | None) -> MatchFilter:
    def keep(mid: int) -> bool:
        m = ref.matches.get(mid)
        if m is None:
            return False
        if season is not None and m.season != season:
            return False
        return not (since is not None and m.date < since)

    return keep


def sum_fielding(items: Iterable[Fielding]) -> Fielding:
    out = Fielding()
    for f in items:
        out.catches += f.catches
        out.stumpings += f.stumpings
        out.run_outs += f.run_outs
    return out


# --------------------------------------------------------------------------- search
RECENT_SEASONS = 2  # a player seen in the last N IPL seasons counts as current


def search(conn: Connection, q: str, limit: int = 10) -> SearchResponse:
    """Token/substring search over Cricsheet names, register aliases and full display names
    ("suryakumar" -> SA Yadav). Players with IPL appearances only, unless none match; ranked by
    match quality, then IPL matches with a boost for current players."""
    q_norm = normalize(q)
    if len(q_norm.replace(" ", "")) < 2:
        return SearchResponse(query=q, results=[])
    tokens = q_norm.split()
    ref = reference(conn)
    best: dict[str, tuple[int, str]] = {}
    for e in name_index(conn):
        qual = match_quality(e, q_norm, tokens)
        if qual is not None and (e.player_id not in best or qual < best[e.player_id][0]):
            best[e.player_id] = (qual, e.name)

    ipl = {pid: v for pid, v in best.items() if ref.appearances.get(pid)}
    pool = ipl or best
    latest = ref.latest_season or 0
    ranked: list[tuple[tuple[int, int, int], str]] = []
    for pid, (qual, _m) in pool.items():
        apps = ref.appearances.get(pid, [])
        last_season = ref.matches[apps[-1][0]].season if apps else 0
        recent = last_season > latest - RECENT_SEASONS
        last_order = ref.order[apps[-1][0]] if apps else -1
        # quality first; then IPL matches, current players weighted up (x2 + 25)
        relevance = len(apps) * 2 + 25 if recent else len(apps)
        ranked.append(((qual, -relevance, -last_order), pid))
    ranked.sort()
    top = [pid for _k, pid in ranked[:limit]]
    names = dict(
        conn.execute(text("SELECT id, name FROM player WHERE id = ANY(:ids)"), {"ids": top}).all()
    )
    hits = []
    for pid in top:
        apps = ref.appearances.get(pid, [])
        seasons = sorted({ref.matches[mid].season for mid, _ in apps})
        ident = identity(conn, pid, names.get(pid, pid))
        hits.append(
            SearchHit(
                id=pid,
                name=ident.name,
                display_name=ident.display_name,
                image_url=ident.image_url,
                matched=pool[pid][1],
                team=ref.teams.get(apps[-1][1]) if apps else None,
                first_season=seasons[0] if seasons else None,
                last_season=seasons[-1] if seasons else None,
                seasons=len(seasons),
                matches=len(apps),
            )
        )
    return SearchResponse(query=q, results=hits)


# --------------------------------------------------------------------------- profile
def _phase_balls(conn: Connection, ids: list[str], keep: MatchFilter) -> list[Ball]:
    balls = fetch_balls(
        conn,
        "d.batter_id = ANY(:ids) OR d.bowler_id = ANY(:ids) OR d.player_out_id = ANY(:ids)",
        {"ids": ids},
    )
    return [b for b in balls if keep(b.match_id)]


class _PlayerData:
    """A player's cards and appearances restricted to a match filter."""

    def __init__(self, ref: Reference, bk: Bulk, pid: str, keep: MatchFilter) -> None:
        self.ref = ref
        self.bat = [c for c in bk.batting.get(pid, []) if keep(c.match_id)]
        self.bowl = [c for c in bk.bowling.get(pid, []) if keep(c.match_id)]
        self.fld = {m: f for m, f in bk.fielding.get(pid, {}).items() if keep(m)}
        self.apps = [(m, t) for m, t in ref.appearances.get(pid, []) if keep(m)]
        self.team_of: dict[int, int] = dict(self.apps)
        # fallback for matches missing from the lineup table
        for c in self.bat:
            self.team_of.setdefault(c.match_id, ref.batting_team.get((c.match_id, c.innings), 0))
        for b in self.bowl:
            t = ref.bowling_team(b.match_id, b.innings)
            if t is not None:
                self.team_of.setdefault(b.match_id, t)
        self.match_ids = sorted(self.team_of, key=lambda m: ref.order[m])

    @property
    def last_team(self) -> str | None:
        return self.ref.teams.get(self.team_of[self.match_ids[-1]]) if self.match_ids else None

    def opponent(self, mid: int) -> int | None:
        team = self.team_of.get(mid)
        return self.ref.matches[mid].opponent(team) if team else None

    def stats(
        self, key: Callable[[int], object] | None = None
    ) -> dict[object, tuple[int, BattingStats, BowlingStats, Fielding]]:
        """(matches, batting, bowling, fielding) grouped by ``key(match_id)``."""
        k: Callable[[int], object] = key or (lambda _m: None)
        bat = group_by(self.bat, lambda c: k(c.match_id))
        bowl = group_by(self.bowl, lambda c: k(c.match_id))
        mids = group_by(self.match_ids, k)
        out: dict[object, tuple[int, BattingStats, BowlingStats, Fielding]] = {}
        for g in mids:
            out[g] = (
                len(mids[g]),
                BattingStats.of(batting_line(bat.get(g, []))),
                BowlingStats.of(bowling_line(bowl.get(g, []))),
                sum_fielding(self.fld[m] for m in mids[g] if m in self.fld),
            )
        return out


def _splits(
    pd: _PlayerData, key: Callable[[int], int | None], names: dict[int, str]
) -> list[Split]:
    rows = []
    for g, (n, bat, bowl, _f) in pd.stats(key).items():
        if not isinstance(g, int):
            continue
        rows.append(Split(id=g, name=names.get(g, str(g)), matches=n, batting=bat, bowling=bowl))
    rows.sort(key=lambda s: (-s.matches, -s.batting.runs, -s.bowling.wickets))
    return rows


def _form(pd: _PlayerData) -> tuple[list[FormBat], list[FormBowl]]:
    ref = pd.ref

    def ctx(mid: int) -> tuple[dt.date, int, str | None, str | None]:
        m = ref.matches[mid]
        opp = pd.opponent(mid)
        venue = ref.venues[m.venue_id][0] if m.venue_id in ref.venues else None
        return m.date, m.season, ref.teams.get(opp) if opp else None, venue

    bat: list[FormBat] = []
    for c in reversed(pd.bat[-FORM_N:]):
        date, season, opp, venue = ctx(c.match_id)
        bat.append(
            FormBat(
                match_id=c.match_id,
                date=date,
                season=season,
                opponent=opp,
                venue=venue,
                runs=c.runs,
                balls=c.balls,
                not_out=not c.out,
                how_out=c.how_out,
                score=f"{c.runs}{'' if c.out else '*'}({c.balls})",
            )
        )
    bowl: list[FormBowl] = []
    for b in reversed(pd.bowl[-FORM_N:]):
        date, season, opp, venue = ctx(b.match_id)
        bowl.append(
            FormBowl(
                match_id=b.match_id,
                date=date,
                season=season,
                opponent=opp,
                venue=venue,
                overs=overs_str(b.balls),
                runs=b.runs,
                wickets=b.wickets,
                figures=b.figures,
            )
        )
    return bat, bowl


def _phases(balls: list[Ball], pid: str) -> tuple[list[PhaseBatting], list[PhaseBowling]]:
    bp = batting_phases(balls, pid)
    wp = bowling_phases(balls, pid)
    return (
        [PhaseBatting.of(p, bp[p]) for p in PHASES],
        [PhaseBowling.of(p, wp[p]) for p in PHASES],
    )


def _player_row(conn: Connection, pid: str) -> tuple[str, str] | None:
    row = conn.execute(
        text("SELECT name, unique_name FROM player WHERE id = :p"), {"p": pid}
    ).first()
    return (row[0], row[1]) if row else None


def profile(
    conn: Connection, pid: str, season: int | None = None, since: dt.date | None = None
) -> PlayerProfile | None:
    row = _player_row(conn, pid)
    if row is None:
        return None
    ref, bk = reference(conn), bulk(conn)
    keep = match_filter(ref, season, since)
    pd = _PlayerData(ref, bk, pid, keep)
    aliases: list[str] = list(
        conn.execute(
            text("SELECT name FROM player_alias WHERE player_id = :p AND name <> :n ORDER BY 1"),
            {"p": pid, "n": row[0]},
        ).scalars()
    )

    career = pd.stats()
    n, bat, bowl, fld = career.get(
        None, (0, BattingStats.of(batting_line([])), BowlingStats.of(bowling_line([])), Fielding())
    )

    by_season = []
    for s, (sn, sbat, sbowl, sfld) in sorted(
        pd.stats(lambda m: ref.matches[m].season).items(), key=lambda x: int(str(x[0]))
    ):
        season_teams = Counter(pd.team_of[m] for m in pd.match_ids if ref.matches[m].season == s)
        by_season.append(
            SeasonLine(
                season=int(str(s)),
                team=ref.teams.get(season_teams.most_common(1)[0][0]) if season_teams else None,
                matches=sn,
                batting=sbat,
                bowling=sbowl,
                fielding=FieldingStats.of(sfld),
            )
        )

    spans: dict[int, list[int]] = defaultdict(list)
    for m in pd.match_ids:
        spans[pd.team_of[m]].append(ref.matches[m].season)
    teams = sorted(
        (
            TeamSpan(
                id=t,
                name=ref.teams.get(t, str(t)),
                first_season=min(v),
                last_season=max(v),
                matches=len(v),
            )
            for t, v in spans.items()
            if t
        ),
        key=lambda s: (-s.last_season, -s.matches),
    )

    venue_names = {vid: name for vid, (name, _c) in ref.venues.items()}
    venues = _splits(pd, lambda m: ref.matches[m].venue_id, venue_names)[:SPLIT_LIMIT]
    vs_teams = _splits(pd, pd.opponent, ref.teams)
    form_bat, form_bowl = _form(pd)
    bat_ph, bowl_ph = _phases(_phase_balls(conn, [pid], keep), pid)
    ident = identity(conn, pid, row[0])

    return PlayerProfile(
        id=pid,
        name=row[0],
        display_name=ident.display_name,
        image_url=ident.image_url,
        unique_name=row[1],
        aliases=aliases,
        filters=Filters(season=season, since=since),
        matches=n,
        seasons=sorted({ref.matches[m].season for m in pd.match_ids}),
        last_team=pd.last_team,
        teams=teams,
        debut=ref.matches[pd.match_ids[0]].date if pd.match_ids else None,
        last_match=ref.matches[pd.match_ids[-1]].date if pd.match_ids else None,
        batting=bat,
        bowling=bowl,
        fielding=FieldingStats.of(fld),
        batting_phases=bat_ph,
        bowling_phases=bowl_ph,
        by_season=by_season,
        venues=venues,
        vs_teams=vs_teams,
        form_batting=form_bat,
        form_bowling=form_bowl,
    )


def compare(
    conn: Connection, ids: list[str], season: int | None = None, since: dt.date | None = None
) -> CompareResponse:
    ref, bk = reference(conn), bulk(conn)
    keep = match_filter(ref, season, since)
    names: dict[str, str] = dict(
        conn.execute(text("SELECT id, name FROM player WHERE id = ANY(:ids)"), {"ids": ids}).all()
    )
    found = [i for i in ids if i in names]
    balls = _phase_balls(conn, found, keep) if found else []
    out = []
    for pid in found:
        pd = _PlayerData(ref, bk, pid, keep)
        n, bat, bowl, fld = pd.stats().get(
            None,
            (0, BattingStats.of(batting_line([])), BowlingStats.of(bowling_line([])), Fielding()),
        )
        bat_ph, bowl_ph = _phases(balls, pid)
        ident = identity(conn, pid, names[pid])
        out.append(
            CompareEntry(
                id=pid,
                name=names[pid],
                display_name=ident.display_name,
                image_url=ident.image_url,
                matches=n,
                last_team=pd.last_team,
                batting=bat,
                bowling=bowl,
                fielding=FieldingStats.of(fld),
                batting_phases=bat_ph,
                bowling_phases=bowl_ph,
            )
        )
    return CompareResponse(filters=Filters(season=season, since=since), players=out)
