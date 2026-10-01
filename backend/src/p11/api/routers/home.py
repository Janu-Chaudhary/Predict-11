"""/api/v1 routes: home (landing hero data). Business logic lives in p11.analytics.home*."""

from __future__ import annotations

from collections.abc import Callable, Iterator
from contextlib import contextmanager

from fastapi import APIRouter, HTTPException, Query, Response
from sqlalchemy import Connection

from ...analytics import home as svc
from ...analytics.home_schemas import XI, HomeState, HomeTiles, Wagon, Worm
from ...core import db

router = APIRouter(prefix="/home", tags=["home"])

CACHE_CONTROL = "public, max-age=60, stale-while-revalidate=600"
DEV_SPIKE_HELP = (
    "Dev only: serve the cached official shot sample for the IPL 2026 Final "
    "(same as env P11_HOME_DEV_SPIKE_WAGON=1)."
)


@contextmanager
def _conn() -> Iterator[Connection]:
    with db.engine().connect() as c:
        try:
            yield c
        finally:
            c.rollback()  # read-only


def _run[T](response: Response, fn: Callable[[Connection], T]) -> T:
    try:
        with _conn() as c:
            out = fn(c)
    except svc.NotFound as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    response.headers["Cache-Control"] = CACHE_CONTROL
    return out


@router.get("/state", response_model=HomeState, operation_id="get_home_state")
def get_state(
    response: Response,
    dev_spike_wagon: bool = Query(False, description=DEV_SPIKE_HELP),
) -> HomeState:
    """Phase (pre_match | post_match | off_season), the hero to show, next fixture, last match."""
    out = _run(response, lambda c: svc.home_state(c, dev_spike_wagon=dev_spike_wagon))
    response.headers["Cache-Control"] = "no-cache"
    return out


@router.get("/worm/{match_id}", response_model=Worm, operation_id="get_home_worm")
def get_worm(match_id: int, response: Response) -> Worm:
    """Hero C: per-ball cumulative runs/wickets per innings, one entry per delivery."""
    return _run(response, lambda c: svc.worm(c, match_id))


@router.get(
    "/wagon/{match_id}",
    response_model=Wagon,
    operation_id="get_home_wagon",
    responses={404: {"description": "No official shot data for this match"}},
)
def get_wagon(
    match_id: int,
    response: Response,
    dev_spike_wagon: bool = Query(False, description=DEV_SPIKE_HELP),
) -> Wagon:
    """Hero A: top innings of the match from official shot data (404 when none exists)."""
    out = _run(response, lambda c: svc.wagon(c, match_id, dev_spike_wagon=dev_spike_wagon))
    if out is None:
        raise HTTPException(status_code=404, detail="no official shot data for this match")
    return out


@router.get(
    "/xi/{match_id}",
    response_model=XI,
    operation_id="get_home_xi",
    responses={204: {"description": "Persisted fantasy points / roles not available"}},
)
def get_xi(match_id: int, response: Response) -> XI | Response:
    """Hero B: lineups + roles + persisted points and the best valid XI (204 when absent)."""
    out = _run(response, lambda c: svc.xi(c, match_id))
    if out is None:
        return Response(status_code=204)
    return out


@router.get("/tiles", response_model=HomeTiles, operation_id="get_home_tiles")
def get_tiles(response: Response) -> HomeTiles:
    """Bento mini-stats: table leader, season top run-scorer / wicket-taker, biggest rivalry,
    highest-par venue, highest team total. A tile is null if its query fails."""
    return _run(response, svc.tiles)
