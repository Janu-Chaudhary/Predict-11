"""Bowling-type matchups (D2) and venue extras (E1: toss trend, pace vs spin).

Bowling type / batting hand come from ``player_attribute_resolved`` (normalized types of
``p11.registry.attributes``). Groups: *pace* = right/left-arm fast and medium; *spin* =
off-spin, leg-spin, left-arm orthodox, left-arm wrist. A ball whose bowler (batter) has no
type (hand) is counted under ``unknown`` and reported as a coverage share, never guessed.

Ball definitions are those of ``players_stats`` (see ``matchups``): batter splits use balls
faced / runs off the bat / bowler-credited dismissals of the striker; bowler splits use legal
balls, runs charged to the bowler and bowler wickets.
"""

from __future__ import annotations

import datetime as dt
from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass, field

from sqlalchemy import Connection, text

from .conditions_models import (
    BatterVsTypes,
    BowlerVsHands,
    BowlGroupLine,
    Coverage,
    HandSplit,
    PaceSpin,
    PaceSpinWindow,
    TossSeason,
    TossTrend,
    TypeSplit,
)
from .players_data import InningsTotal, Reference, bulk, cached, fetch_balls, reference
from .players_models import PlayerRef
from .players_stats import H2H, Ball, BowlingCard, confidence, overs_str
from .venues import RECENT_FROM, par_stats, toss_stats

PACE_TYPES: tuple[str, ...] = (
    "right-arm fast",
    "right-arm medium",
    "left-arm fast",
    "left-arm medium",
)
SPIN_TYPES: tuple[str, ...] = ("off-spin", "leg-spin", "left-arm orthodox", "left-arm wrist")
BOWLING_TYPES = PACE_TYPES + SPIN_TYPES
GROUPS = ("pace", "spin")
HAND_LABEL = {"R": "RHB", "L": "LHB"}


def group_of(bowling_type: str | None) -> str | None:
    """Normalized bowling type -> 'pace' | 'spin' (None when unknown / unrecognized)."""
    if bowling_type in PACE_TYPES:
        return "pace"
    if bowling_type in SPIN_TYPES:
        return "spin"
    return None


def _pct(a: float, b: float) -> float | None:
    return round(a / b * 100, 1) if b else None


def _rate(a: float, b: float, scale: float = 1.0) -> float | None:
    return round(a / b * scale, 2) if b else None


# --------------------------------------------------------------------------- attributes
@dataclass(frozen=True, slots=True)
class Attributes:
    bowling_type: dict[str, str]
    batting_hand: dict[str, str]


def _build_attributes(conn: Connection) -> Attributes:
    bt: dict[str, str] = {}
    bh: dict[str, str] = {}
    for pid, btype, hand in conn.execute(
        text("SELECT player_id, bowling_type, batting_hand FROM player_attribute_resolved")
    ):
        if btype:
            bt[pid] = btype
        if hand:
            bh[pid] = hand
    return Attributes(bt, bh)


def attributes(conn: Connection) -> Attributes:
    return cached(conn, "conditions_attributes", _build_attributes)


def _player(conn: Connection, pid: str) -> PlayerRef | None:
    row = conn.execute(text("SELECT id, name FROM player WHERE id = :p"), {"p": pid}).first()
    return PlayerRef(id=row[0], name=row[1]) if row else None


def _coverage(balls: int, known: int, opponents: set[str], known_opp: set[str]) -> Coverage:
    return Coverage(
        balls=balls,
        balls_known=known,
        unknown_pct=_pct(balls - known, balls),
        opponents=len(opponents),
        opponents_known=len(opponents & known_opp),
    )


# --------------------------------------------------------------------------- D2 batter
def _type_split(name: str, group: str, agg: H2H, bowlers: int) -> TypeSplit:
    return TypeSplit(
        bowling_type=name,
        group=group,
        balls=agg.balls,
        runs=agg.runs,
        dismissals=agg.dismissals,
        strike_rate=agg.strike_rate,
        average=agg.average,
        dot_pct=agg.dot_pct,
        boundary_pct=agg.boundary_pct,
        fours=agg.fours,
        sixes=agg.sixes,
        bowlers=bowlers,
        confidence=confidence(agg.balls),
    )


def split_by_type(
    balls: Iterable[Ball], types: dict[str, str]
) -> tuple[list[TypeSplit], list[TypeSplit], H2H, set[str]]:
    """Batter balls -> (per type rows, pace/spin rows, unknown aggregate, unknown bowlers)."""
    by_type: dict[str, H2H] = defaultdict(H2H)
    bowlers: dict[str, set[str]] = defaultdict(set)
    unknown, unknown_bowlers = H2H(), set()
    for b in balls:
        t = types.get(b.bowler)
        g = group_of(t)
        if t is None or g is None:
            unknown.add(b)
            unknown_bowlers.add(b.bowler)
            continue
        for key in (t, g):
            by_type[key].add(b)
            bowlers[key].add(b.bowler)
    rows = [
        _type_split(t, group_of(t) or "", by_type.get(t, H2H()), len(bowlers.get(t, ())))
        for t in BOWLING_TYPES
    ]
    groups = [_type_split(g, g, by_type.get(g, H2H()), len(bowlers.get(g, ()))) for g in GROUPS]
    return rows, groups, unknown, unknown_bowlers


def batter_vs_types(
    conn: Connection, batter: str, since: dt.date | None = None
) -> BatterVsTypes | None:
    who = _player(conn, batter)
    if who is None:
        return None
    ref = reference(conn)
    attrs = attributes(conn)
    balls = [
        b
        for b in fetch_balls(conn, "d.batter_id = :p", {"p": batter})
        if since is None or ref.matches[b.match_id].date >= since
    ]
    rows, groups, unknown, unknown_bowlers = split_by_type(balls, attrs.bowling_type)
    total = sum(1 for b in balls if b.faced)
    bowlers = {b.bowler for b in balls}
    notes = [
        "Bowling type from player_attribute_resolved; balls by bowlers with no known type are "
        "excluded from the splits and counted in coverage.unknown_pct.",
        "Confidence badge as /h2h: low <12 balls, medium 12-29, high >=30.",
    ]
    if unknown.balls:
        notes.append(
            f"{unknown.balls} balls ({_pct(unknown.balls, total)}%) came from "
            f"{len(unknown_bowlers)} bowler(s) with unknown bowling type."
        )
    return BatterVsTypes(
        batter=who,
        batting_hand=attrs.batting_hand.get(batter),
        since=since,
        by_type=rows,
        by_group=groups,
        coverage=_coverage(total, total - unknown.balls, bowlers, bowlers - unknown_bowlers),
        notes=notes,
    )


# --------------------------------------------------------------------------- D2 bowler
@dataclass(slots=True)
class BowlAgg:
    balls: int = 0  # legal
    runs: int = 0
    wickets: int = 0
    dots: int = 0
    boundaries: int = 0
    batters: set[str] = field(default_factory=set)

    def add(self, b: Ball) -> None:
        self.balls += b.legal
        self.runs += b.bowler_runs
        self.wickets += b.bowler_wicket
        self.dots += b.dot
        self.boundaries += b.four or b.six
        self.batters.add(b.batter)


def split_by_hand(balls: Iterable[Ball], hands: dict[str, str]) -> tuple[list[HandSplit], BowlAgg]:
    by: dict[str, BowlAgg] = defaultdict(BowlAgg)
    unknown = BowlAgg()
    for b in balls:
        h = hands.get(b.batter)
        (by[h] if h in HAND_LABEL else unknown).add(b)
    out = []
    for h, label in HAND_LABEL.items():
        a = by.get(h, BowlAgg())
        out.append(
            HandSplit(
                hand=h,
                label=label,
                balls=a.balls,
                runs_conceded=a.runs,
                wickets=a.wickets,
                economy=_rate(a.runs, a.balls, 6),
                strike_rate=_rate(a.balls, a.wickets),
                average=_rate(a.runs, a.wickets),
                dot_pct=_rate(a.dots, a.balls, 100),
                boundary_pct=_rate(a.boundaries, a.balls, 100),
                batters=len(a.batters),
                confidence=confidence(a.balls),
            )
        )
    return out, unknown


def bowler_vs_hands(
    conn: Connection, bowler: str, since: dt.date | None = None
) -> BowlerVsHands | None:
    who = _player(conn, bowler)
    if who is None:
        return None
    ref = reference(conn)
    attrs = attributes(conn)
    balls = [
        b
        for b in fetch_balls(conn, "d.bowler_id = :p", {"p": bowler})
        if since is None or ref.matches[b.match_id].date >= since
    ]
    rows, unknown = split_by_hand(balls, attrs.batting_hand)
    total = sum(1 for b in balls if b.legal)
    batters = {b.batter for b in balls}
    btype = attrs.bowling_type.get(bowler)
    notes = [
        "Legal balls; runs conceded = off the bat + wides + no-balls; wickets exclude run outs.",
        "Confidence badge as /h2h: low <12 balls, medium 12-29, high >=30.",
    ]
    if unknown.balls:
        notes.append(f"{unknown.balls} legal balls to batters with unknown batting hand.")
    return BowlerVsHands(
        bowler=who,
        bowling_type=btype,
        group=group_of(btype),
        since=since,
        by_hand=rows,
        coverage=_coverage(total, total - unknown.balls, batters, batters - unknown.batters),
        notes=notes,
    )


# --------------------------------------------------------------------------- toss trend
def _venue_mids(ref: Reference, vid: int) -> list[int]:
    return [mid for mid, m in ref.matches.items() if m.venue_id == vid]  # chronological


def _innings_index(ref: Reference, mids: set[int]) -> dict[int, dict[int, InningsTotal]]:
    out: dict[int, dict[int, InningsTotal]] = defaultdict(dict)
    for t in ref.innings:
        if t.match_id in mids:
            out[t.match_id][t.innings] = t
    return out


def toss_season(
    ref: Reference, season: int, mids: list[int], inns: dict[int, dict[int, InningsTotal]]
) -> TossSeason:
    ts = toss_stats(ref, mids)
    ps = par_stats(ref, mids, inns)
    return TossSeason(
        season=season,
        matches=len(mids),
        toss_field_pct=ts.field_pct,
        toss_winner_win_pct=ts.toss_winner_win_pct,
        chase_win_pct=ps.chase_win_pct,
        decided=ps.matches,
    )


def toss_trend(conn: Connection, vid: int) -> TossTrend | None:
    ref = reference(conn)
    if vid not in ref.venues:
        return None
    mids = _venue_mids(ref, vid)
    inns = _innings_index(ref, set(mids))
    by_season: dict[int, list[int]] = defaultdict(list)
    for m in mids:
        by_season[ref.matches[m].season].append(m)
    recent = [m for m in mids if ref.matches[m].season >= RECENT_FROM]
    first = min(by_season, default=0)
    return TossTrend(
        venue_id=vid,
        venue=ref.venues[vid][0],
        seasons=[toss_season(ref, s, ms, inns) for s, ms in sorted(by_season.items())],
        recent=toss_season(ref, RECENT_FROM, recent, inns),
        all_time=toss_season(ref, first, mids, inns),
        notes=[
            "toss_field_pct = toss winners choosing to field / toss decisions.",
            "toss_winner_win_pct excludes no results; super-over winners count as winners.",
            "chase_win_pct uses completed non-DLS matches with a winner (column 'decided').",
        ],
    )


# --------------------------------------------------------------------------- pace vs spin
@dataclass(slots=True)
class _Bowl:
    balls: int = 0
    runs: int = 0
    wickets: int = 0

    def add(self, c: BowlingCard) -> None:
        self.balls += c.balls
        self.runs += c.runs
        self.wickets += c.wickets


def _line(name: str, a: _Bowl, tot: _Bowl) -> BowlGroupLine:
    return BowlGroupLine(
        group=name,
        balls=a.balls,
        overs=overs_str(a.balls),
        runs=a.runs,
        wickets=a.wickets,
        economy=_rate(a.runs, a.balls, 6),
        strike_rate=_rate(a.balls, a.wickets),
        average=_rate(a.runs, a.wickets),
        overs_share_pct=_pct(a.balls, tot.balls),
        wickets_share_pct=_pct(a.wickets, tot.wickets),
    )


def pace_spin_window(
    window: str, cards: Iterable[tuple[str, BowlingCard]], types: dict[str, str], matches: int
) -> PaceSpinWindow:
    """(bowler, card) pairs -> pace / spin / unknown and per-type lines."""
    grp: dict[str, _Bowl] = defaultdict(_Bowl)
    typ: dict[str, _Bowl] = defaultdict(_Bowl)
    tot = _Bowl()
    for pid, c in cards:
        t = types.get(pid)
        g = group_of(t) or "unknown"
        grp[g].add(c)
        if t in BOWLING_TYPES:
            typ[t].add(c)
        tot.add(c)
    return PaceSpinWindow(
        window=window,
        matches=matches,
        groups=[_line(g, grp.get(g, _Bowl()), tot) for g in (*GROUPS, "unknown")],
        by_type=[_line(t, typ.get(t, _Bowl()), tot) for t in BOWLING_TYPES],
        unknown_ball_pct=_pct(grp.get("unknown", _Bowl()).balls, tot.balls),
    )


def pace_spin(conn: Connection, vid: int) -> PaceSpin | None:
    ref = reference(conn)
    if vid not in ref.venues:
        return None
    mids = set(_venue_mids(ref, vid))
    recent = {m for m in mids if ref.matches[m].season >= RECENT_FROM}
    types = attributes(conn).bowling_type
    cards = [(pid, c) for pid, cs in bulk(conn).bowling.items() for c in cs if c.match_id in mids]
    return PaceSpin(
        venue_id=vid,
        venue=ref.venues[vid][0],
        recent=pace_spin_window(
            "recent", [x for x in cards if x[1].match_id in recent], types, len(recent)
        ),
        all_time=pace_spin_window("all_time", cards, types, len(mids)),
        notes=[
            f"recent = {RECENT_FROM}+ (impact-player era).",
            "Pace = right/left-arm fast and medium; spin = off-spin, leg-spin, left-arm "
            "orthodox, left-arm wrist (player_attribute_resolved).",
            "Economy = runs charged to the bowler per 6 legal balls; wickets exclude run outs; "
            "strike rate = balls per wicket. Super overs excluded.",
        ],
    )
