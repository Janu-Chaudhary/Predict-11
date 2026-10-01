"""/api/v1 routes: fantasy. Business logic lives in p11.analytics.fantasy*.

Results are memoised in-process per data fingerprint (p11.analytics.fantasy_data), which is
also the weak ETag (``If-None-Match`` -> 304).
"""

from __future__ import annotations

import contextlib
import datetime as dt
import threading
from collections.abc import Callable
from typing import Literal

from fastapi import APIRouter, HTTPException, Path, Query, Request, Response

from ...analytics import fantasy as svc
from ...analytics import fantasy_data as data
from ...analytics.fantasy_schemas import (
    FantasyPlayer,
    Leaderboard,
    MatchBestXI,
    SeasonBestXIs,
    TeamOfSeason,
)
from ...analytics.players_data import parse_since


def _warm() -> None:
    def run() -> None:
        with contextlib.suppress(Exception):  # DB may be down at startup
            data.data()

    threading.Thread(target=run, name="p11-fantasy-warm", daemon=True).start()


router = APIRouter(tags=["fantasy"], on_startup=[_warm])
CACHE_CONTROL = "public, max-age=60, stale-while-revalidate=600"
RoleQ = Literal["WK", "BAT", "AR", "BOWL"]


def _serve[T](
    request: Request, response: Response, key: str, compute: Callable[[], T]
) -> T | Response:
    try:
        etag = f'W/"f{data.fingerprint()}"'
        if request.headers.get("if-none-match") == etag:
            return Response(status_code=304, headers={"ETag": etag, "Cache-Control": CACHE_CONTROL})
        result = data.memo(key, compute)
    except svc.NotFound as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
    response.headers["ETag"] = etag
    response.headers["Cache-Control"] = CACHE_CONTROL
    return result


def _since(since: str | None) -> dt.date | None:
    try:
        return parse_since(since)
    except ValueError as e:
        raise HTTPException(422, f"since must be YYYY or YYYY-MM-DD, got {since!r}") from e


@router.get(
    "/fantasy/players/{player_id}",
    response_model=FantasyPlayer,
    operation_id="get_fantasy_player",
)
def get_player(
    request: Request,
    response: Response,
    player_id: str = Path(..., min_length=1, max_length=32),
    season: int | None = Query(None, ge=2008, le=2100),
    since: str | None = Query(None, description="YYYY or YYYY-MM-DD"),
) -> FantasyPlayer | Response:
    d = _since(since)
    return _serve(
        request,
        response,
        f"player:{player_id}:{season}:{d}",
        lambda: svc.player(player_id, season, d),
    )


@router.get(
    "/fantasy/leaderboard", response_model=Leaderboard, operation_id="get_fantasy_leaderboard"
)
def get_leaderboard(
    request: Request,
    response: Response,
    season: int | None = Query(None, ge=2008, le=2100, description="Default: latest season"),
    role: RoleQ | None = None,
    min_matches: int = Query(3, ge=1, le=30),
    sort: svc.SortKey = "total",
    limit: int = Query(50, ge=1, le=500),
) -> Leaderboard | Response:
    return _serve(
        request,
        response,
        f"lb:{season}:{role}:{min_matches}:{sort}:{limit}",
        lambda: svc.leaderboard(season, role, min_matches, sort, limit),
    )


@router.get(
    "/fantasy/matches/{match_id}/best-xi",
    response_model=MatchBestXI,
    operation_id="get_match_best_xi",
)
def get_match_best_xi(
    match_id: int, request: Request, response: Response
) -> MatchBestXI | Response:
    return _serve(request, response, f"mxi:{match_id}", lambda: svc.match_best_xi(match_id))


@router.get(
    "/fantasy/seasons/{year}/team-of-season",
    response_model=TeamOfSeason,
    operation_id="get_team_of_season",
)
def get_team_of_season(
    year: int,
    request: Request,
    response: Response,
    min_matches: int = Query(
        svc.DEFAULT_MIN_MATCHES_MEAN, ge=1, le=20, description="Minimum matches for the by-mean XI"
    ),
) -> TeamOfSeason | Response:
    return _serve(
        request,
        response,
        f"tos-r:{year}:{min_matches}",
        lambda: svc.team_of_season(year, min_matches),
    )


@router.get(
    "/fantasy/seasons/{year}/best-xis",
    response_model=SeasonBestXIs,
    operation_id="get_season_best_xis",
)
def get_season_best_xis(
    year: int, request: Request, response: Response
) -> SeasonBestXIs | Response:
    return _serve(request, response, f"sxi-r:{year}", lambda: svc.season_best_xis(year))
