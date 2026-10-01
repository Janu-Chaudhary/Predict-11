"""Curated league-stage corrections the ball-by-ball data cannot express.

Cricsheet (our only match source so far) has no record of matches **abandoned without a
ball bowled**, yet those count as no-results (1 point each) in the official table. It also
keeps the abandoned-and-replayed 2025 PBKS v DC game at Dharamsala, which was declared void.
Without these, e.g. 2008 would put Mumbai 4th instead of Delhi, and 2025 RCB/KKR would show
13 games played.

Each entry was located from a gap in the season's league match numbering (or, for 2025, the
renumbered schedule) plus the teams left one game short, and checked against the published
final tables. Drop this module once a fixtures scraper records washed-out games.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Abandoned:
    year: int
    match_number: int | None  # league match number in the published schedule
    date: dt.date
    team1: str  # canonical (current) franchise name
    team2: str


ABANDONED_NO_BALL: tuple[Abandoned, ...] = (
    Abandoned(2008, 47, dt.date(2008, 5, 22), "Delhi Capitals", "Kolkata Knight Riders"),
    Abandoned(2009, 7, dt.date(2009, 4, 21), "Mumbai Indians", "Rajasthan Royals"),
    Abandoned(2009, 13, dt.date(2009, 4, 25), "Chennai Super Kings", "Kolkata Knight Riders"),
    Abandoned(2011, 20, dt.date(2011, 4, 19), "Royal Challengers Bengaluru", "Rajasthan Royals"),
    Abandoned(2012, 32, dt.date(2012, 4, 24), "Kolkata Knight Riders", "Sunrisers Hyderabad"),
    Abandoned(2012, 34, dt.date(2012, 4, 25), "Royal Challengers Bengaluru", "Chennai Super Kings"),
    Abandoned(2015, 25, dt.date(2015, 4, 26), "Kolkata Knight Riders", "Rajasthan Royals"),
    Abandoned(2017, 29, dt.date(2017, 4, 25), "Royal Challengers Bengaluru", "Sunrisers Hyderabad"),
    Abandoned(2024, 63, dt.date(2024, 5, 13), "Gujarat Titans", "Kolkata Knight Riders"),
    Abandoned(2024, 66, dt.date(2024, 5, 16), "Sunrisers Hyderabad", "Gujarat Titans"),
    Abandoned(2024, 70, dt.date(2024, 5, 19), "Rajasthan Royals", "Kolkata Knight Riders"),
    Abandoned(
        2025, None, dt.date(2025, 5, 17), "Royal Challengers Bengaluru", "Kolkata Knight Riders"
    ),
)

# Played-but-void league games (match.id): excluded from the table and from NRR.
VOID_MATCH_IDS: frozenset[int] = frozenset(
    {1473495}  # 2025 PBKS v DC, Dharamsala, stopped for security after 10.1 overs; replayed
)
