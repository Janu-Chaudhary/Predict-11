"""/api/v1 routes: seasons. Business logic lives in p11.analytics.

Responses are deterministic for a given state of the DB, so every GET carries a weak ETag
derived from the data fingerprint (``If-None-Match`` -> 304) plus a short public max-age.
Computed results are memoised in-process per data fingerprint.
"""

from __future__ import annotations

import logging
import threading
from collections.abc import Callable
from typing import Literal

from fastapi import APIRouter, HTTPException, Query, Request, Response

from ...analytics import seasons as svc
from ...analytics import seasons_data as data
from ...analytics.seasons_schemas import (
    HeadToHead,
    MatchSummary,
    PointsTable,
    Records,
    ScenarioRequest,
    Scenarios,
    SeasonStory,
    SeasonSummary,
    TeamSummary,
)

router = APIRouter(tags=["seasons"])
log = logging.getLogger(__name__)

CACHE_CONTROL = "public, max-age=60, stale-while-revalidate=600"


def _serve[T](
    request: Request, response: Response, key: str, compute: Callable[[], T]
) -> T | Response:
    try:
        etag = f'W/"{data.fingerprint()}"'
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


@router.get("/seasons", response_model=list[SeasonSummary], operation_id="list_seasons")
def get_seasons(request: Request, response: Response) -> list[SeasonSummary] | Response:
    return _serve(request, response, "seasons", svc.list_seasons)


@router.get("/teams", response_model=list[TeamSummary], operation_id="list_teams")
def get_teams(request: Request, response: Response) -> list[TeamSummary] | Response:
    return _serve(request, response, "teams", svc.list_teams)


@router.get("/seasons/{year}/table", response_model=PointsTable, operation_id="get_points_table")
def get_table(
    year: int,
    request: Request,
    response: Response,
    after_match: int | None = Query(None, ge=0, description="Only league matches 1..N"),
) -> PointsTable | Response:
    return _serve(
        request,
        response,
        f"table:{year}:{after_match}",
        lambda: svc.points_table(year, after_match),
    )


@router.get("/seasons/{year}/scenarios", response_model=Scenarios, operation_id="get_scenarios")
def get_scenarios(
    year: int,
    request: Request,
    response: Response,
    after_match: int | None = Query(
        None, ge=0, description="Replay from after league match N (default: all played)"
    ),
) -> Scenarios | Response:
    return _serve(
        request,
        response,
        f"scenarios:{year}:{after_match}",
        lambda: svc.scenarios(year, after_match),
    )


@router.post("/seasons/{year}/scenarios", response_model=Scenarios, operation_id="pick_scenarios")
def post_scenarios(year: int, body: ScenarioRequest) -> Scenarios:
    try:
        return svc.scenarios(year, body.after_match, body.picks)
    except svc.NotFound as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e


@router.get("/seasons/{year}/story", response_model=SeasonStory, operation_id="get_season_story")
def get_story(
    year: int,
    request: Request,
    response: Response,
    min_balls: int = Query(100, ge=1, le=1000, description="Strike-rate qualification"),
    min_overs: int = Query(20, ge=1, le=200, description="Economy qualification"),
) -> SeasonStory | Response:
    return _serve(
        request,
        response,
        f"story:{year}:{min_balls}:{min_overs}",
        lambda: svc.season_story(year, min_balls, min_overs),
    )


@router.get("/teams/{a}/vs/{b}", response_model=HeadToHead, operation_id="get_team_vs_team")
def get_h2h(
    a: str,
    b: str,
    request: Request,
    response: Response,
    season: int | None = None,
    venue: int | None = Query(None, description="Venue id"),
) -> HeadToHead | Response:
    return _serve(
        request,
        response,
        f"h2h:{a}:{b}:{season}:{venue}",
        lambda: svc.head_to_head(a, b, season, venue),
    )


@router.get("/records", response_model=Records, operation_id="get_records")
def get_records(
    request: Request,
    response: Response,
    scope: Literal["all", "season"] = "all",
    season: int | None = None,
    venue: int | None = Query(None, description="Venue id"),
    limit: int = Query(10, ge=1, le=50),
) -> Records | Response:
    return _serve(
        request,
        response,
        f"records:{scope}:{season}:{venue}:{limit}",
        lambda: svc.records(scope, season, venue, limit),
    )


@router.get("/matches", response_model=list[MatchSummary], operation_id="list_matches")
def get_matches(
    request: Request,
    response: Response,
    season: int | None = None,
    team: str | None = Query(None, description="Team id or short code (e.g. RCB, DCH)"),
) -> list[MatchSummary] | Response:
    return _serve(
        request,
        response,
        f"matches:{season}:{team}",
        lambda: svc.list_matches(season, team),
    )


def _warm() -> None:
    try:
        data.core()
        data.players()
    except Exception as e:  # DB down at startup is fine; first request will retry
        log.info("seasons cache warm-up skipped: %s", e)


threading.Thread(target=_warm, name="seasons-warmup", daemon=True).start()
