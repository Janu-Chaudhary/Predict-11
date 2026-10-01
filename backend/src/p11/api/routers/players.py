"""/api/v1 routes: players, matchups, venues, milestones, streaks.

Business logic lives in p11.analytics (players*, matchups, venues).
"""

from __future__ import annotations

import datetime as dt
import threading
from collections.abc import Iterator
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import Connection

from ...analytics import matchups, players, players_records, venues
from ...analytics.players_data import bulk, parse_since, reference
from ...analytics.players_models import (
    CompareResponse,
    H2HResponse,
    MilestonesResponse,
    PlayerProfile,
    SearchResponse,
    StreaksResponse,
)
from ...core import db


def _warm() -> None:
    """Build the analytics caches in the background so the first request is fast."""

    def run() -> None:
        try:
            with db.engine().connect() as conn:
                reference(conn)
                bulk(conn)
        except Exception:  # pragma: no cover - DB may be down at startup
            pass

    threading.Thread(target=run, name="p11-analytics-warm", daemon=True).start()


router = APIRouter(tags=["players"], on_startup=[_warm])


def get_conn() -> Iterator[Connection]:
    with db.engine().connect() as conn:
        yield conn


Conn = Annotated[Connection, Depends(get_conn)]


def _since(since: str | None) -> dt.date | None:
    try:
        return parse_since(since)
    except ValueError as e:
        raise HTTPException(422, f"since must be YYYY or YYYY-MM-DD, got {since!r}") from e


# --------------------------------------------------------------------------- players
@router.get("/players/search", response_model=SearchResponse)
def player_search(
    conn: Conn,
    q: Annotated[str, Query(min_length=1, max_length=64)],
    limit: Annotated[int, Query(ge=1, le=50)] = 10,
) -> SearchResponse:
    return players.search(conn, q, limit)


@router.get("/players/compare", response_model=CompareResponse)
def player_compare(
    conn: Conn,
    ids: Annotated[str, Query(description="comma-separated player ids (2-4)")],
    season: int | None = None,
    since: Annotated[str | None, Query(description="YYYY or YYYY-MM-DD")] = None,
) -> CompareResponse:
    id_list = list(dict.fromkeys(i.strip() for i in ids.split(",") if i.strip()))
    if not 1 <= len(id_list) <= 4:
        raise HTTPException(422, "ids must list 1-4 player ids")
    res = players.compare(conn, id_list, season, _since(since))
    missing = set(id_list) - {p.id for p in res.players}
    if missing:
        raise HTTPException(404, f"unknown player id(s): {sorted(missing)}")
    return res


@router.get("/players/{player_id}", response_model=PlayerProfile)
def player_profile(
    conn: Conn,
    player_id: str,
    season: int | None = None,
    since: Annotated[str | None, Query(description="YYYY or YYYY-MM-DD")] = None,
) -> PlayerProfile:
    prof = players.profile(conn, player_id, season, _since(since))
    if prof is None:
        raise HTTPException(404, f"unknown player id {player_id!r}")
    return prof


# --------------------------------------------------------------------------- matchups
@router.get("/h2h", response_model=H2HResponse)
def head_to_head(
    conn: Conn,
    batter: str | None = None,
    bowler: str | None = None,
    since: Annotated[str | None, Query(description="YYYY or YYYY-MM-DD")] = None,
    min_balls: Annotated[int, Query(ge=1, le=500)] = 12,
    limit: Annotated[int, Query(ge=1, le=50)] = 10,
    sort: Annotated[
        str | None, Query(pattern="^(dismissals|runs|strike_rate|balls|dot_pct)$")
    ] = None,
) -> H2HResponse:
    if not batter and not bowler:
        raise HTTPException(422, "pass batter and/or bowler")
    return matchups.head_to_head(conn, batter, bowler, _since(since), min_balls, limit, sort)


# --------------------------------------------------------------------------- venues
@router.get("/venues", response_model=venues.VenueList)
def venue_list(conn: Conn) -> venues.VenueList:
    return venues.venue_list(conn)


@router.get("/venues/{venue_id}", response_model=venues.VenueCard)
def venue_card(conn: Conn, venue_id: int) -> venues.VenueCard:
    card = venues.venue_card(conn, venue_id)
    if card is None:
        raise HTTPException(404, f"unknown venue id {venue_id}")
    return card


# --------------------------------------------------------------------------- records
@router.get("/milestones", response_model=MilestonesResponse)
def milestones(conn: Conn, season: int | None = None) -> MilestonesResponse:
    try:
        return players_records.milestones(conn, season)
    except LookupError as e:
        raise HTTPException(404, str(e)) from e


@router.get("/streaks", response_model=StreaksResponse)
def streaks(
    conn: Conn,
    season: int | None = None,
    type: Annotated[str | None, Query(pattern="^(score30|wicket|no_duck)$")] = None,
    limit: Annotated[int, Query(ge=1, le=50)] = 10,
) -> StreaksResponse:
    try:
        return players_records.streaks(conn, season, type, limit)
    except LookupError as e:
        raise HTTPException(404, str(e)) from e
