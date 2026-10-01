"""/api/v1 routes: conditions. Business logic lives in p11.analytics.conditions*.

D2 bowling-type / batting-hand matchups, E1 venue extras (toss trend, pace vs spin) and E2 dew &
weather (venue dew table, per-match conditions, forecast).
"""

from __future__ import annotations

import datetime as dt
from collections.abc import Iterator
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import Connection

from ...analytics import conditions, conditions_weather
from ...analytics.conditions_models import (
    BatterVsTypes,
    BowlerVsHands,
    DewReport,
    Forecast,
    MatchConditions,
    PaceSpin,
    TossTrend,
)
from ...analytics.players_data import parse_since
from ...core import db

router = APIRouter(tags=["conditions"])


def get_conn() -> Iterator[Connection]:
    with db.engine().connect() as conn:
        yield conn


Conn = Annotated[Connection, Depends(get_conn)]
Since = Annotated[str | None, Query(description="YYYY or YYYY-MM-DD")]


def _since(since: str | None) -> dt.date | None:
    try:
        return parse_since(since)
    except ValueError as e:
        raise HTTPException(422, f"since must be YYYY or YYYY-MM-DD, got {since!r}") from e


def _found[T](x: T | None, what: str) -> T:
    if x is None:
        raise HTTPException(404, f"{what} not found")
    return x


# --------------------------------------------------------------------------- D2
@router.get(
    "/matchups/batter/{player_id}/vs-bowling-types",
    response_model=BatterVsTypes,
    operation_id="get_batter_vs_bowling_types",
)
def batter_vs_bowling_types(conn: Conn, player_id: str, since: Since = None) -> BatterVsTypes:
    return _found(conditions.batter_vs_types(conn, player_id, _since(since)), "player")


@router.get(
    "/matchups/bowler/{player_id}/vs-batting-hand",
    response_model=BowlerVsHands,
    operation_id="get_bowler_vs_batting_hand",
)
def bowler_vs_batting_hand(conn: Conn, player_id: str, since: Since = None) -> BowlerVsHands:
    return _found(conditions.bowler_vs_hands(conn, player_id, _since(since)), "player")


# --------------------------------------------------------------------------- venue extras
@router.get(
    "/venues/{venue_id}/toss-trend", response_model=TossTrend, operation_id="get_venue_toss_trend"
)
def venue_toss_trend(conn: Conn, venue_id: int) -> TossTrend:
    return _found(conditions.toss_trend(conn, venue_id), "venue")


@router.get(
    "/venues/{venue_id}/pace-spin", response_model=PaceSpin, operation_id="get_venue_pace_spin"
)
def venue_pace_spin(conn: Conn, venue_id: int) -> PaceSpin:
    return _found(conditions.pace_spin(conn, venue_id), "venue")


# --------------------------------------------------------------------------- dew & weather
@router.get("/conditions/dew", response_model=DewReport, operation_id="get_league_dew")
def league_dew(conn: Conn) -> DewReport:
    return _found(conditions_weather.dew_report(conn, None), "venue")


@router.get("/venues/{venue_id}/dew", response_model=DewReport, operation_id="get_venue_dew")
def venue_dew(conn: Conn, venue_id: int) -> DewReport:
    return _found(conditions_weather.dew_report(conn, venue_id), "venue")


@router.get(
    "/matches/{match_id}/conditions",
    response_model=MatchConditions,
    operation_id="get_match_conditions",
)
def match_conditions(conn: Conn, match_id: int) -> MatchConditions:
    return _found(conditions_weather.match_conditions(conn, match_id), "match")


@router.get(
    "/venues/{venue_id}/forecast", response_model=Forecast, operation_id="get_venue_forecast"
)
def venue_forecast(
    conn: Conn,
    venue_id: int,
    at: Annotated[str, Query(description="start time, ISO 8601; naive values are read as IST")],
) -> Forecast:
    try:
        when = dt.datetime.fromisoformat(at)
    except ValueError as e:
        raise HTTPException(422, f"at must be ISO 8601, got {at!r}") from e
    if when.tzinfo is None:
        when = when.replace(tzinfo=conditions_weather.IST)
    when = when.astimezone(dt.UTC)
    try:
        fc = conditions_weather.forecast(conn, venue_id, when)
    except ValueError as e:
        raise HTTPException(422, str(e)) from e
    except RuntimeError as e:
        raise HTTPException(502, f"weather provider error: {e}") from e
    return _found(fc, "venue (or its coordinates)")
