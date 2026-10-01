"""Milestones watch (I2) and streaks (I3), from the cached per-innings cards."""

from __future__ import annotations

import datetime as dt
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from sqlalchemy import Connection

from .players_data import Bulk, Reference, bulk, player_names, reference
from .players_models import (
    Milestone,
    MilestonesResponse,
    PlayerRef,
    StreakBoard,
    StreakEntry,
    StreaksResponse,
)
from .players_stats import BattingCard, BowlingCard, next_milestone, streak


@dataclass(frozen=True, slots=True)
class MilestoneRule:
    stat: str
    label: str  # "IPL runs"
    small_step: int  # step while below ``big_from``
    big_step: int
    big_from: int
    small_window: int  # "within reach" = needed <= window
    big_window: int

    def step(self, value: int) -> int:
        return self.small_step if value < self.big_from else self.big_step

    def window(self, value: int) -> int:
        return self.small_window if value < self.big_from else self.big_window


MILESTONE_RULES: tuple[MilestoneRule, ...] = (
    MilestoneRule("runs", "IPL runs", 500, 1000, 1000, 100, 200),
    MilestoneRule("wickets", "IPL wickets", 50, 50, 0, 10, 10),
    MilestoneRule("sixes", "IPL sixes", 50, 100, 100, 10, 15),
    MilestoneRule("matches", "IPL matches", 50, 100, 100, 10, 10),
    MilestoneRule("catches", "IPL catches", 50, 50, 0, 10, 10),
)


def milestone_for(rule: MilestoneRule, value: int) -> tuple[int, int] | None:
    """(target, needed) if ``value`` is within the rule's window of its next round number."""
    if value <= 0:
        return None
    target = next_milestone(value, rule.step(value))
    needed = target - value
    return (target, needed) if needed <= rule.window(value) else None


def _scope_season(ref: Reference, season: int | None) -> int:
    latest = ref.latest_season
    if latest is None:
        raise LookupError("no IPL matches loaded")
    return latest if season is None else season


def milestones(conn: Connection, season: int | None = None) -> MilestonesResponse:
    """Players active in ``season`` (default latest) close to a round-number IPL career
    milestone, counting everything up to and including that season."""
    ref, bk = reference(conn), bulk(conn)
    s = _scope_season(ref, season)

    def upto(mid: int) -> bool:
        return ref.matches[mid].season <= s

    active = {
        pid: apps
        for pid, apps in ref.appearances.items()
        if any(ref.matches[m].season == s for m, _ in apps)
    }
    as_of = max((m.date for m in ref.matches.values() if m.season <= s), default=None)
    found: list[tuple[float, Milestone]] = []
    names = player_names(conn, set(active))
    for pid, apps in active.items():
        apps_upto = [(m, t) for m, t in apps if upto(m)]
        totals = {
            "runs": sum(c.runs for c in bk.batting.get(pid, []) if upto(c.match_id)),
            "sixes": sum(c.sixes for c in bk.batting.get(pid, []) if upto(c.match_id)),
            "wickets": sum(c.wickets for c in bk.bowling.get(pid, []) if upto(c.match_id)),
            "catches": sum(f.catches for m, f in bk.fielding.get(pid, {}).items() if upto(m)),
            "matches": len(apps_upto),
        }
        team = ref.teams.get(apps_upto[-1][1]) if apps_upto else None
        name = names.get(pid, pid)
        for rule in MILESTONE_RULES:
            hit = milestone_for(rule, totals[rule.stat])
            if hit is None:
                continue
            target, needed = hit
            found.append(
                (
                    needed / rule.window(totals[rule.stat]),
                    Milestone(
                        player=PlayerRef(id=pid, name=name),
                        team=team,
                        stat=rule.stat,
                        current=totals[rule.stat],
                        target=target,
                        needed=needed,
                        text=f"{name} needs {needed} for {target:,} {rule.label}",
                    ),
                )
            )
    found.sort(key=lambda x: (x[0], -x[1].target))
    return MilestonesResponse(season=s, as_of=as_of, milestones=[m for _, m in found])


# --------------------------------------------------------------------------- streaks
@dataclass(frozen=True, slots=True)
class StreakRule:
    type: str
    label: str
    source: str  # batting | bowling
    ok: Callable[[Any], bool]


def _score30(c: BattingCard) -> bool:
    return c.runs >= 30


def _no_duck(c: BattingCard) -> bool:
    return not c.duck


def _wicket(c: BowlingCard) -> bool:
    return c.wickets >= 1


STREAK_RULES: tuple[StreakRule, ...] = (
    StreakRule("score30", "Consecutive innings with 30+", "batting", _score30),
    StreakRule("wicket", "Consecutive bowling innings with a wicket", "bowling", _wicket),
    StreakRule("no_duck", "Consecutive innings without a duck", "batting", _no_duck),
)
STREAK_TYPES = tuple(r.type for r in STREAK_RULES)


def _entry(
    ref: Reference,
    player: PlayerRef,
    team: str | None,
    cards: Sequence[Any],
    start: int,
    end: int,
    length: int,
    running: bool,
) -> StreakEntry:
    return StreakEntry(
        player=player,
        team=team,
        length=length,
        start_date=ref.matches[cards[start].match_id].date,
        end_date=ref.matches[cards[end].match_id].date,
        active=running,
    )


def _board(
    ref: Reference,
    bk: Bulk,
    rule: StreakRule,
    in_scope: Callable[[int], bool],
    active: set[str],
    names: dict[str, str],
    limit: int,
) -> StreakBoard:
    cards_by_player: Mapping[str, Sequence[Any]] = (
        bk.batting if rule.source == "batting" else bk.bowling
    )
    current: list[StreakEntry] = []
    longest: list[tuple[int, int, StreakEntry]] = []
    for pid, all_cards in cards_by_player.items():
        cards = [c for c in all_cards if in_scope(c.match_id)]
        if not cards:
            continue
        st = streak(cards, rule.ok)
        team = None
        apps = ref.appearances.get(pid)
        if apps:
            team = ref.teams.get(apps[-1][1])

        ref_p = PlayerRef(id=pid, name=names.get(pid, pid))
        n = len(cards)
        if st.current >= 2 and pid in active:
            current.append(_entry(ref, ref_p, team, cards, n - st.current, n - 1, st.current, True))
        if st.longest >= 2 and st.longest_start is not None and st.longest_end is not None:
            running = st.longest_end == n - 1 and pid in active
            e = _entry(
                ref, ref_p, team, cards, st.longest_start, st.longest_end, st.longest, running
            )
            longest.append((st.longest, ref.order[cards[st.longest_end].match_id], e))
    current.sort(key=lambda e: (-e.length, e.player.name))
    longest.sort(key=lambda x: (-x[0], -x[1]))
    return StreakBoard(
        type=rule.type,
        label=rule.label,
        current=current[:limit],
        longest=[e for _, _, e in longest[:limit]],
    )


def streaks(
    conn: Connection, season: int | None = None, type: str | None = None, limit: int = 10
) -> StreaksResponse:
    """Streak leaderboards for one season (``season``) or all-time (``season=None``).

    "Current" streaks run to a player's last innings in the scope and are listed only for
    players who appeared in the scope's final season (the latest season for all-time).
    """
    ref, bk = reference(conn), bulk(conn)
    last_season = _scope_season(ref, season)

    def in_scope(mid: int) -> bool:
        return season is None or ref.matches[mid].season == season

    active = {
        pid
        for pid, apps in ref.appearances.items()
        if any(ref.matches[m].season == last_season for m, _ in apps)
    }
    rules = [r for r in STREAK_RULES if type is None or r.type == type]
    pids = set(bk.batting) | set(bk.bowling)
    names = player_names(conn, pids)
    as_of: dt.date | None = max(
        (m.date for m in ref.matches.values() if m.season <= last_season), default=None
    )
    return StreaksResponse(
        season=season,
        as_of=as_of,
        boards=[_board(ref, bk, r, in_scope, active, names, limit) for r in rules],
    )
