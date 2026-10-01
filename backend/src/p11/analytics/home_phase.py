"""Pure rules for the Home hero rotation (docs/DESIGN-DIRECTION.md §8, owner decision 2026-10-02).

- **pre_match** (a fixture is known, until its result): hero B "XI assembles" when an XI with
  roles + points exists for that fixture; otherwise C.
- **post_match** (after a result, until the next fixture's match-day window opens): hero A
  "wagon wheel" when official shot data exists for the last match; otherwise C.
- **off_season** (no upcoming fixture and the last match is older than ``POST_MATCH_DAYS``):
  C on the season final.

We only know match *dates* (no end times), so "after a result" is approximated in IST:
the post-match window runs until ``POST_MATCH_UNTIL`` (noon) on the day after the match, and a
known fixture takes over once it is less than ``PRE_MATCH_LEAD`` away.
"""

from __future__ import annotations

import datetime as dt
from zoneinfo import ZoneInfo

from .home_schemas import Hero, Phase
from .seasons_teams import era_for

IST = ZoneInfo("Asia/Kolkata")
PRE_MATCH_LEAD = dt.timedelta(hours=8)
POST_MATCH_UNTIL = dt.time(12, 0)
POST_MATCH_DAYS = 2  # with no fixture known, keep the post-match hero this many days


def post_window_end(last_date: dt.date) -> dt.datetime:
    """End of the post-match window: noon IST on the day after the match."""
    return dt.datetime.combine(last_date + dt.timedelta(days=1), POST_MATCH_UNTIL, tzinfo=IST)


def decide_phase(
    now: dt.datetime, next_start: dt.datetime | None, last_date: dt.date | None
) -> Phase:
    if now.tzinfo is None:
        raise ValueError("now must be timezone-aware")
    if next_start is not None:
        if (
            last_date is not None
            and now < post_window_end(last_date)
            and next_start - now > PRE_MATCH_LEAD
        ):
            return "post_match"
        return "pre_match"
    if last_date is not None and (now.astimezone(IST).date() - last_date).days <= POST_MATCH_DAYS:
        return "post_match"
    return "off_season"


def choose_hero(phase: Phase, *, xi_available: bool, wagon_available: bool) -> tuple[Hero, str]:
    """Hero + a short human reason (shown as the hero caption's fallback note)."""
    if phase == "pre_match":
        if xi_available:
            return "B", "Before the match: the XI assembles"
        return "C", "No XI with roles and points for this fixture yet, so the last match's worm"
    if phase == "post_match":
        if wagon_available:
            return "A", "After the match: top innings wagon wheel (official shot data)"
        return "C", "No official shot data for the last match, so its ball-by-ball worm"
    return "C", "Off-season: the season final, one particle per ball"


def overs_text(legal_balls: int) -> str:
    """Cricket notation: 108 -> "18", 107 -> "17.5"."""
    o, b = divmod(max(0, legal_balls), 6)
    return f"{o}.{b}" if b else str(o)


def match_title(stage: str | None, match_number: int | None) -> str:
    if stage:
        return stage
    if match_number:
        return f"Match {match_number}"
    return "League match"


def team_code(canonical_name: str, year: int | None) -> str:
    """Season-correct short code ("DD" in 2015, "DC" in 2020)."""
    return era_for(canonical_name, year).short_code


def team_display(canonical_name: str, year: int | None) -> str:
    return era_for(canonical_name, year).name
