"""Venue cards (E1).

Par / chase stats use completed, non-DLS matches with a winner (``result = 'win'`` and no
``method``), matching the catalog's §4 E2 query. Scoring has inflated sharply (powerplay RPO
7.8 in 2022 -> 10.1 in 2026), so every headline number is given for the impact-player era
(``RECENT_FROM`` = 2023+) next to all-time, plus a recency-weighted par.

Not available: pace vs spin wicket split (bowling style is not stored yet).
"""

from __future__ import annotations

import datetime as dt
import statistics
from collections import defaultdict

from pydantic import BaseModel, Field
from sqlalchemy import Connection

from .players_data import InningsTotal, Reference, bulk, player_names, reference
from .players_models import PlayerRef
from .players_stats import PHASES, overs_str

RECENT_FROM = 2023
HALF_LIFE_SEASONS = 2.0
TOP_N = 5
NOTES = [
    "Pace vs spin wicket split is not available: bowling style is not stored in the DB yet.",
    "Par / chase figures use completed non-DLS matches with a result. Run rates are runs "
    "(incl. extras) per 6 legal balls.",
]


class ParStats(BaseModel):
    matches: int
    avg_first_innings: float | None
    median_first_innings: float | None
    avg_second_innings: float | None
    chase_win_pct: float | None
    bat_first_win_pct: float | None


class TossStats(BaseModel):
    matches: int
    chose_field: int
    chose_bat: int
    field_pct: float | None
    toss_winner_win_pct: float | None
    toss_winner_win_pct_when_field: float | None
    toss_winner_win_pct_when_bat: float | None


class PhaseRate(BaseModel):
    phase: str
    run_rate: float | None
    wickets_per_innings: float | None


class TeamTotal(BaseModel):
    match_id: int
    date: dt.date
    season: int
    team: str | None
    opponent: str | None
    innings: int
    runs: int
    wickets: int
    overs: str
    score: str = Field(description='e.g. "287/3 (20)"')


class VenueLeader(BaseModel):
    player: PlayerRef
    innings: int
    value: int
    rate: float | None = Field(description="batting SR or bowling economy")


class SeasonTrend(BaseModel):
    season: int
    matches: int
    avg_first_innings: float | None


class VenueCard(BaseModel):
    id: int
    name: str
    city: str | None
    matches: int
    first_match: dt.date | None
    last_match: dt.date | None
    par_weighted: float | None = Field(
        description=f"recency-weighted avg 1st-innings total (half-life {HALF_LIFE_SEASONS:g} "
        "seasons)"
    )
    recent: ParStats = Field(description=f"{RECENT_FROM}+ (impact-player era)")
    all_time: ParStats
    toss_recent: TossStats
    toss_all_time: TossStats
    phases_recent: list[PhaseRate]
    phases_all_time: list[PhaseRate]
    by_season: list[SeasonTrend]
    highest_totals: list[TeamTotal]
    lowest_totals: list[TeamTotal]
    top_run_scorers: list[VenueLeader]
    top_wicket_takers: list[VenueLeader]
    notes: list[str]


class VenueSummary(BaseModel):
    id: int
    name: str
    city: str | None
    matches: int
    matches_recent: int
    first_season: int | None
    last_season: int | None
    par_recent: float | None
    par_all_time: float | None
    chase_win_pct_recent: float | None


class VenueList(BaseModel):
    recent_from: int
    venues: list[VenueSummary]


def _pct(a: int, b: int) -> float | None:
    return round(a / b * 100, 1) if b else None


def _mean(xs: list[int]) -> float | None:
    return round(statistics.fmean(xs), 1) if xs else None


def _innings_by_match(ref: Reference) -> dict[int, dict[int, InningsTotal]]:
    out: dict[int, dict[int, InningsTotal]] = defaultdict(dict)
    for t in ref.innings:
        out[t.match_id][t.innings] = t
    return out


def _decided(ref: Reference, mid: int) -> bool:
    m = ref.matches[mid]
    return m.result == "win" and not m.method and m.winner_id is not None


def par_stats(
    ref: Reference, mids: list[int], inns: dict[int, dict[int, InningsTotal]]
) -> ParStats:
    firsts, seconds = [], []
    chase_wins = decided = 0
    for mid in mids:
        i = inns.get(mid, {})
        if not _decided(ref, mid) or 1 not in i or 2 not in i:
            continue
        decided += 1
        firsts.append(i[1].runs)
        seconds.append(i[2].runs)
        chase_wins += ref.matches[mid].winner_id == i[2].team_id
    return ParStats(
        matches=decided,
        avg_first_innings=_mean(firsts),
        median_first_innings=float(statistics.median(firsts)) if firsts else None,
        avg_second_innings=_mean(seconds),
        chase_win_pct=_pct(chase_wins, decided),
        bat_first_win_pct=_pct(decided - chase_wins, decided),
    )


def weighted_par(
    ref: Reference, mids: list[int], inns: dict[int, dict[int, InningsTotal]]
) -> float | None:
    latest = ref.latest_season or 0
    num = den = 0.0
    for mid in mids:
        i = inns.get(mid, {})
        if not _decided(ref, mid) or 1 not in i:
            continue
        w = 0.5 ** ((latest - ref.matches[mid].season) / HALF_LIFE_SEASONS)
        num += w * i[1].runs
        den += w
    return round(num / den, 1) if den else None


def toss_stats(ref: Reference, mids: list[int]) -> TossStats:
    field = bat = 0
    won = played = 0
    won_by = {"field": 0, "bat": 0}
    played_by = {"field": 0, "bat": 0}
    for mid in mids:
        m = ref.matches[mid]
        if m.toss_decision == "field":
            field += 1
        elif m.toss_decision == "bat":
            bat += 1
        if m.result == "no_result" or m.winner_id is None or m.toss_winner_id is None:
            continue
        played += 1
        w = m.winner_id == m.toss_winner_id
        won += w
        if m.toss_decision in played_by:
            played_by[m.toss_decision] += 1
            won_by[m.toss_decision] += w
    return TossStats(
        matches=len(mids),
        chose_field=field,
        chose_bat=bat,
        field_pct=_pct(field, field + bat),
        toss_winner_win_pct=_pct(won, played),
        toss_winner_win_pct_when_field=_pct(won_by["field"], played_by["field"]),
        toss_winner_win_pct_when_bat=_pct(won_by["bat"], played_by["bat"]),
    )


def phase_rates(mids: list[int], inns: dict[int, dict[int, InningsTotal]]) -> list[PhaseRate]:
    runs = dict.fromkeys(PHASES, 0)
    balls = dict.fromkeys(PHASES, 0)
    wkts = dict.fromkeys(PHASES, 0)
    n = 0
    for mid in mids:
        for t in inns.get(mid, {}).values():
            n += 1
            for p in PHASES:
                runs[p] += t.phase_runs.get(p, 0)
                balls[p] += t.phase_balls.get(p, 0)
                wkts[p] += t.phase_wickets.get(p, 0)
    return [
        PhaseRate(
            phase=p,
            run_rate=round(runs[p] / balls[p] * 6, 2) if balls[p] else None,
            wickets_per_innings=round(wkts[p] / n, 2) if n else None,
        )
        for p in PHASES
    ]


def _total(ref: Reference, t: InningsTotal) -> TeamTotal:
    m = ref.matches[t.match_id]
    ov = overs_str(t.legal_balls)
    return TeamTotal(
        match_id=t.match_id,
        date=m.date,
        season=m.season,
        team=ref.teams.get(t.team_id),
        opponent=ref.teams.get(m.opponent(t.team_id)),
        innings=t.innings,
        runs=t.runs,
        wickets=t.wickets,
        overs=ov,
        score=f"{t.runs}{'' if t.wickets >= 10 else f'/{t.wickets}'} ({ov})",
    )


def _venue_mids(ref: Reference) -> dict[int, list[int]]:
    out: dict[int, list[int]] = defaultdict(list)
    for mid, m in ref.matches.items():  # chronological
        if m.venue_id is not None:
            out[m.venue_id].append(mid)
    return out


def venue_list(conn: Connection) -> VenueList:
    ref = reference(conn)
    inns = _innings_by_match(ref)
    out = []
    for vid, mids in _venue_mids(ref).items():
        name, city = ref.venues.get(vid, (str(vid), None))
        recent = [m for m in mids if ref.matches[m].season >= RECENT_FROM]
        pr = par_stats(ref, recent, inns)
        pa = par_stats(ref, mids, inns)
        seasons = [ref.matches[m].season for m in mids]
        out.append(
            VenueSummary(
                id=vid,
                name=name,
                city=city,
                matches=len(mids),
                matches_recent=len(recent),
                first_season=min(seasons),
                last_season=max(seasons),
                par_recent=pr.avg_first_innings,
                par_all_time=pa.avg_first_innings,
                chase_win_pct_recent=pr.chase_win_pct,
            )
        )
    out.sort(key=lambda v: (-v.matches_recent, -v.matches))
    return VenueList(recent_from=RECENT_FROM, venues=out)


def venue_card(conn: Connection, vid: int) -> VenueCard | None:
    ref = reference(conn)
    if vid not in ref.venues:
        return None
    name, city = ref.venues[vid]
    mids = _venue_mids(ref).get(vid, [])
    recent = [m for m in mids if ref.matches[m].season >= RECENT_FROM]
    inns = _innings_by_match(ref)

    by_season: dict[int, list[int]] = defaultdict(list)
    for m in mids:
        by_season[ref.matches[m].season].append(m)
    trend = [
        SeasonTrend(
            season=s, matches=len(ms), avg_first_innings=par_stats(ref, ms, inns).avg_first_innings
        )
        for s, ms in sorted(by_season.items())
    ]

    all_inns = [t for m in mids for t in inns.get(m, {}).values()]
    highest = sorted(all_inns, key=lambda t: (-t.runs, t.wickets))[:TOP_N]
    complete = [
        t
        for t in all_inns
        if not ref.matches[t.match_id].method
        and t.target_overs is None
        and (t.wickets >= 10 or t.legal_balls >= 120)
    ]
    lowest = sorted(complete, key=lambda t: (t.runs, -t.wickets))[:TOP_N]

    # leaders from the cached per-innings cards
    bk = bulk(conn)
    at_venue = set(mids)
    bat_lead: list[tuple[int, int, int, str]] = []  # runs, balls, inns, pid
    for pid, cards in bk.batting.items():
        cs = [c for c in cards if c.match_id in at_venue]
        if cs:
            bat_lead.append((sum(c.runs for c in cs), sum(c.balls for c in cs), len(cs), pid))
    bat_lead.sort(key=lambda x: (-x[0], x[1]))
    bowl_lead: list[tuple[int, int, int, int, str]] = []  # wkts, runs, balls, inns, pid
    for pid, bcards in bk.bowling.items():
        bs = [c for c in bcards if c.match_id in at_venue]
        if bs:
            bowl_lead.append(
                (
                    sum(c.wickets for c in bs),
                    sum(c.runs for c in bs),
                    sum(c.balls for c in bs),
                    len(bs),
                    pid,
                )
            )
    bowl_lead.sort(key=lambda x: (-x[0], x[1]))
    bat_top, bowl_top = bat_lead[:TOP_N], bowl_lead[:TOP_N]
    names = player_names(conn, {x[-1] for x in bat_top} | {x[-1] for x in bowl_top})

    return VenueCard(
        id=vid,
        name=name,
        city=city,
        matches=len(mids),
        first_match=ref.matches[mids[0]].date if mids else None,
        last_match=ref.matches[mids[-1]].date if mids else None,
        par_weighted=weighted_par(ref, mids, inns),
        recent=par_stats(ref, recent, inns),
        all_time=par_stats(ref, mids, inns),
        toss_recent=toss_stats(ref, recent),
        toss_all_time=toss_stats(ref, mids),
        phases_recent=phase_rates(recent, inns),
        phases_all_time=phase_rates(mids, inns),
        by_season=trend,
        highest_totals=[_total(ref, t) for t in highest],
        lowest_totals=[_total(ref, t) for t in lowest],
        top_run_scorers=[
            VenueLeader(
                player=PlayerRef(id=pid, name=names.get(pid, pid)),
                innings=n,
                value=runs,
                rate=round(runs / balls * 100, 2) if balls else None,
            )
            for runs, balls, n, pid in bat_top
        ],
        top_wicket_takers=[
            VenueLeader(
                player=PlayerRef(id=pid, name=names.get(pid, pid)),
                innings=n,
                value=w,
                rate=round(r / b * 6, 2) if b else None,
            )
            for w, r, b, n, pid in bowl_top
        ],
        notes=NOTES,
    )
