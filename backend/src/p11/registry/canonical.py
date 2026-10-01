"""Canonical teams, venues, competitions and seasons (+ alias tables).

Every raw spelling seen in any source is stored in ``team_alias`` / ``venue_alias`` pointing at
one canonical row. The rename tables below are the curated knowledge; anything unknown becomes
its own canonical row (never silently merged) so it shows up in review.
"""

from __future__ import annotations

import re

from sqlalchemy import Connection, text

# Team merges: old name -> current name. True renames of the same franchise, plus owner-approved
# history merges (Deccan Chargers -> Sunrisers Hyderabad: one Hyderabad team history, 2026-10-02).
TEAM_RENAMES: dict[str, str] = {
    "Royal Challengers Bangalore": "Royal Challengers Bengaluru",
    "Delhi Daredevils": "Delhi Capitals",
    "Kings XI Punjab": "Punjab Kings",
    "Rising Pune Supergiants": "Rising Pune Supergiant",
    "Deccan Chargers": "Sunrisers Hyderabad",
}

# Venue spellings whose first comma-separated part is still not the canonical ground name.
# Includes physical-ground renames (same stadium, new name).
VENUE_RENAMES: dict[str, str] = {
    "M.Chinnaswamy Stadium": "M Chinnaswamy Stadium",
    "Feroz Shah Kotla": "Arun Jaitley Stadium",  # renamed 2019
    "Sardar Patel Stadium": "Narendra Modi Stadium",  # Motera, rebuilt + renamed 2021
    "Punjab Cricket Association Stadium": "Punjab Cricket Association IS Bindra Stadium",
    "Sheikh Zayed Stadium": "Zayed Cricket Stadium",
    "Subrata Roy Sahara Stadium": "Maharashtra Cricket Association Stadium",  # Pune, Gahunje
}

CITY_RENAMES = {"Bangalore": "Bengaluru"}

COMPETITIONS = {"Indian Premier League": "ipl"}


def canonical_team_name(raw: str) -> str:
    raw = " ".join(raw.split())
    return TEAM_RENAMES.get(raw, raw)


def canonical_venue_name(raw: str) -> str:
    """'Wankhede Stadium, Mumbai' -> 'Wankhede Stadium'; then apply curated renames."""
    raw = " ".join(raw.split())
    base = raw.split(",")[0].strip()
    return VENUE_RENAMES.get(base, base)


def canonical_city(raw: str | None) -> str | None:
    if not raw:
        return None
    return CITY_RENAMES.get(raw, raw)


def competition_code(event_name: str) -> str:
    return COMPETITIONS.get(event_name) or re.sub(r"[^a-z0-9]+", "_", event_name.lower()).strip("_")


class Resolver:
    """Get-or-create canonical ids with an in-process cache (one per load run)."""

    def __init__(self, conn: Connection) -> None:
        self.conn = conn
        self._team: dict[str, int] = {}
        self._venue: dict[str, int] = {}
        self._season: dict[tuple[str, int], int] = {}

    def team(self, raw: str) -> int:
        if raw in self._team:
            return self._team[raw]
        c = self.conn
        tid = c.execute(
            text("SELECT team_id FROM team_alias WHERE alias = :a"), {"a": raw}
        ).scalar()
        if tid is None:
            name = canonical_team_name(raw)
            c.execute(
                text("INSERT INTO team (name) VALUES (:n) ON CONFLICT (name) DO NOTHING"),
                {"n": name},
            )
            tid = c.execute(text("SELECT id FROM team WHERE name = :n"), {"n": name}).scalar_one()
            for alias in {raw, name}:
                c.execute(
                    text(
                        "INSERT INTO team_alias (alias, team_id) VALUES (:a, :t) "
                        "ON CONFLICT (alias) DO NOTHING"
                    ),
                    {"a": alias, "t": tid},
                )
        self._team[raw] = tid
        return tid

    def venue(self, raw: str, city: str | None) -> int:
        if raw in self._venue:
            return self._venue[raw]
        c = self.conn
        vid = c.execute(
            text("SELECT venue_id FROM venue_alias WHERE alias = :a"), {"a": raw}
        ).scalar()
        if vid is None:
            name = canonical_venue_name(raw)
            c.execute(
                text(
                    "INSERT INTO venue (name, city) VALUES (:n, :c) ON CONFLICT (name) DO NOTHING"
                ),
                {"n": name, "c": canonical_city(city)},
            )
            vid = c.execute(text("SELECT id FROM venue WHERE name = :n"), {"n": name}).scalar_one()
            c.execute(
                text("UPDATE venue SET city = CAST(:c AS text) WHERE id = :v AND city IS NULL"),
                {"c": canonical_city(city), "v": vid},
            )
            c.execute(
                text(
                    "INSERT INTO venue_alias (alias, venue_id) VALUES (:a, :v) "
                    "ON CONFLICT (alias) DO NOTHING"
                ),
                {"a": raw, "v": vid},
            )
        self._venue[raw] = vid
        return vid

    def season(self, event_name: str, year: int, label: str) -> int:
        code = competition_code(event_name)
        k = (code, year)
        if k in self._season:
            return self._season[k]
        c = self.conn
        c.execute(
            text(
                "INSERT INTO competition (code, name) VALUES (:c, :n) ON CONFLICT (code) DO NOTHING"
            ),
            {"c": code, "n": event_name},
        )
        comp = c.execute(
            text("SELECT id FROM competition WHERE code = :c"), {"c": code}
        ).scalar_one()
        c.execute(
            text(
                "INSERT INTO season (competition_id, year, label) VALUES (:c, :y, :l) "
                "ON CONFLICT (competition_id, year) DO NOTHING"
            ),
            {"c": comp, "y": year, "l": label},
        )
        sid = c.execute(
            text("SELECT id FROM season WHERE competition_id = :c AND year = :y"),
            {"c": comp, "y": year},
        ).scalar_one()
        self._season[k] = sid
        return sid
