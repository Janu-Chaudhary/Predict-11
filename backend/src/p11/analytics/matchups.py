"""Batter-vs-bowler head-to-head (D1) plus discovery lists.

Pair definitions (see ``players_stats``): balls = balls faced (wides excluded), runs = runs off
the bat, dismissals = bowler-credited dismissals of the striker (run outs etc. excluded), dot =
legal ball with no runs off the bat, boundary % = (4s + 6s) / balls.
"""

from __future__ import annotations

import datetime as dt
from collections import defaultdict

from sqlalchemy import Connection

from .players_data import Reference, fetch_balls, reference
from .players_identity import player_refs, ref_or_id
from .players_models import (
    Encounter,
    EncounterSeason,
    H2HResponse,
    MatchupRow,
    PairStats,
)
from .players_stats import H2H, Ball, confidence, h2h

LAST_N = 5
SORTS = ("dismissals", "runs", "strike_rate", "balls", "dot_pct")


def _pair_stats(ref: Reference, balls: list[Ball]) -> PairStats:
    agg = h2h(balls)
    by_season: dict[int, H2H] = defaultdict(H2H)
    by_match: dict[int, H2H] = defaultdict(H2H)
    for b in balls:
        by_season[ref.matches[b.match_id].season].add(b)
        by_match[b.match_id].add(b)
    last = sorted(by_match, key=lambda m: ref.order[m], reverse=True)[:LAST_N]
    encounters = []
    for mid in last:
        e = by_match[mid]
        m = ref.matches[mid]
        how = next(iter(e.how_out), None) if e.how_out else None
        encounters.append(
            Encounter(
                match_id=mid,
                date=m.date,
                season=m.season,
                venue=ref.venues[m.venue_id][0] if m.venue_id in ref.venues else None,
                balls=e.balls,
                runs=e.runs,
                out=e.dismissals > 0,
                how_out=how,
                summary=f"{e.balls}-{e.runs}-{e.dismissals}",
            )
        )
    return PairStats(
        balls=agg.balls,
        runs=agg.runs,
        dismissals=agg.dismissals,
        how_out=dict(sorted(agg.how_out.items(), key=lambda kv: -kv[1])),
        strike_rate=agg.strike_rate,
        average=agg.average,
        dot_pct=agg.dot_pct,
        boundary_pct=agg.boundary_pct,
        fours=agg.fours,
        sixes=agg.sixes,
        matches=len(agg.matches),
        innings=len(agg.innings),
        confidence=confidence(agg.balls),
        by_season=[
            EncounterSeason(
                season=s,
                balls=v.balls,
                runs=v.runs,
                dismissals=v.dismissals,
                strike_rate=v.strike_rate,
            )
            for s, v in sorted(by_season.items())
        ],
        last_encounters=encounters,
    )


def _rows(
    conn: Connection, groups: dict[str, H2H], min_balls: int, sort: str, limit: int
) -> list[MatchupRow]:
    eligible = {k: v for k, v in groups.items() if v.balls >= min_balls}
    refs = player_refs(conn, set(eligible))

    def key(item: tuple[str, H2H]) -> tuple[float, ...]:
        v = item[1]
        sr = v.strike_rate or 0.0
        if sort == "dismissals":
            return (-v.dismissals, sr)
        if sort == "strike_rate":
            return (-sr, -v.balls)
        if sort == "dot_pct":
            return (-(v.dot_pct or 0.0), -v.balls)
        if sort == "balls":
            return (-v.balls, -v.runs)
        return (-v.runs, -sr)

    out = []
    for pid, v in sorted(eligible.items(), key=key)[:limit]:
        out.append(
            MatchupRow(
                player=ref_or_id(refs, pid),
                balls=v.balls,
                runs=v.runs,
                dismissals=v.dismissals,
                strike_rate=v.strike_rate,
                dot_pct=v.dot_pct,
                boundary_pct=v.boundary_pct,
                matches=len(v.matches),
                confidence=confidence(v.balls),
            )
        )
    return out


def head_to_head(
    conn: Connection,
    batter: str | None,
    bowler: str | None,
    since: dt.date | None = None,
    min_balls: int = 12,
    limit: int = 10,
    sort: str | None = None,
) -> H2HResponse:
    ref = reference(conn)
    names = player_refs(conn, {p for p in (batter, bowler) if p})

    def keep(b: Ball) -> bool:
        return since is None or ref.matches[b.match_id].date >= since

    bat_balls = (
        [b for b in fetch_balls(conn, "d.batter_id = :p", {"p": batter}) if keep(b)]
        if batter in names
        else []
    )
    bowl_balls = (
        [b for b in fetch_balls(conn, "d.bowler_id = :p", {"p": bowler}) if keep(b)]
        if bowler in names
        else []
    )

    pair = None
    if batter in names and bowler in names:
        pair = _pair_stats(ref, [b for b in bat_balls if b.bowler == bowler])

    vs_bowlers: dict[str, H2H] = defaultdict(H2H)
    for b in bat_balls:
        vs_bowlers[b.bowler].add(b)
    vs_batters: dict[str, H2H] = defaultdict(H2H)
    for b in bowl_balls:
        vs_batters[b.batter].add(b)

    notes = []
    if pair is not None and pair.confidence == "low":
        notes.append(
            "Small sample: the median IPL batter-bowler pair has only ~5 balls; treat as anecdote."
        )
    for role, pid in (("batter", batter), ("bowler", bowler)):
        if pid and pid not in names:
            notes.append(f"Unknown {role} id {pid!r}.")

    return H2HResponse(
        batter=names[batter] if batter in names and batter else None,
        bowler=names[bowler] if bowler in names and bowler else None,
        since=since,
        min_balls=min_balls,
        pair=pair,
        top_bowlers_vs_batter=_rows(conn, vs_bowlers, min_balls, sort or "dismissals", limit),
        top_batters_vs_bowler=_rows(conn, vs_batters, min_balls, sort or "runs", limit),
        notes=notes,
    )
