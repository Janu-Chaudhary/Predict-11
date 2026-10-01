"""Curated league-stage corrections the ball-by-ball data cannot express.

Cricsheet (our only match source so far) has no record of matches **abandoned without a
ball bowled**, yet those count as no-results (1 point each) in the official table. It also
keeps the abandoned-and-replayed 2025 PBKS v DC game at Dharamsala, which was declared void.
Without these, e.g. 2008 would put Mumbai 4th instead of Delhi, and 2025 RCB/KKR would show
13 games played.

Each entry was located from a gap in the season's league match numbering (or, for 2025, the
renumbered schedule) plus the teams left one game short, and checked against the published
final tables. Drop this module once a fixtures scraper records washed-out games.

Verified 2026-10-02 against ESPNcricinfo season "match-schedule-fixtures-and-results" pages
(__NEXT_DATA__, every season 2008-2026): all entries below match a "Match abandoned without a
ball bowled" / "No result (abandoned with a toss)" fixture, and no other such fixture exists.
Every other "No result" game had balls bowled and is present in Cricsheet. Per-entry source:
https://www.espncricinfo.com/series/<series>/<slug>-<cricinfo id>/full-scorecard
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
    # ESPNcricinfo series/match 313494 / 336030
    Abandoned(2008, 47, dt.date(2008, 5, 22), "Delhi Capitals", "Kolkata Knight Riders"),
    # ESPNcricinfo series/match 374163 / 392187
    Abandoned(2009, 7, dt.date(2009, 4, 21), "Mumbai Indians", "Rajasthan Royals"),
    # ESPNcricinfo series/match 374163 / 392193
    Abandoned(2009, 13, dt.date(2009, 4, 25), "Chennai Super Kings", "Kolkata Knight Riders"),
    # ESPNcricinfo series/match 466304 / 501217
    Abandoned(2011, 20, dt.date(2011, 4, 19), "Royal Challengers Bengaluru", "Rajasthan Royals"),
    # ESPNcricinfo series/match 520932 / 548338 (vs Deccan Chargers)
    Abandoned(2012, 32, dt.date(2012, 4, 24), "Kolkata Knight Riders", "Sunrisers Hyderabad"),
    # ESPNcricinfo series/match 520932 / 548340 (toss made)
    Abandoned(2012, 34, dt.date(2012, 4, 25), "Royal Challengers Bengaluru", "Chennai Super Kings"),
    # ESPNcricinfo series/match 791129 / 829755
    Abandoned(2015, 25, dt.date(2015, 4, 26), "Kolkata Knight Riders", "Rajasthan Royals"),
    # ESPNcricinfo series/match 1078425 / 1082619
    Abandoned(2017, 29, dt.date(2017, 4, 25), "Royal Challengers Bengaluru", "Sunrisers Hyderabad"),
    # ESPNcricinfo series/match 1410320 / 1426301
    Abandoned(2024, 63, dt.date(2024, 5, 13), "Gujarat Titans", "Kolkata Knight Riders"),
    # ESPNcricinfo series/match 1410320 / 1426304
    Abandoned(2024, 66, dt.date(2024, 5, 16), "Sunrisers Hyderabad", "Gujarat Titans"),
    # ESPNcricinfo series/match 1410320 / 1426308 (toss made)
    Abandoned(2024, 70, dt.date(2024, 5, 19), "Rajasthan Royals", "Kolkata Knight Riders"),
    # ESPNcricinfo series/match 1449924 / 1473496 (58th match in the renumbered schedule)
    Abandoned(
        2025, None, dt.date(2025, 5, 17), "Royal Challengers Bengaluru", "Kolkata Knight Riders"
    ),
)

# Played-but-void league games (match.id): excluded from the table and from NRR.
VOID_MATCH_IDS: frozenset[int] = frozenset(
    {1473495}  # 2025 PBKS v DC, Dharamsala, stopped for security after 10.1 overs; replayed
)
