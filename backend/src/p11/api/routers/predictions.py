"""/api/v1/predictions: the XI our model would have picked before each played match, vs what
happened. Logic in p11.analytics.predictions; only honest out-of-sample (walk-forward / frozen
test) predictions of the latest model run are served, never the final serving model.
"""

from __future__ import annotations

import sys
import threading
from collections.abc import Callable

from fastapi import APIRouter, HTTPException, Path, Response

from ...analytics import model_lab as ml
from ...analytics import predictions as svc

router = APIRouter(prefix="/predictions", tags=["predictions"])
CACHE = "public, max-age=120, stale-while-revalidate=600"


def _call[T](fn: Callable[[], T]) -> T:
    try:
        return fn()
    except ml.NotFound as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@router.get(
    "/seasons", response_model=list[svc.SeasonOption], operation_id="list_prediction_seasons"
)
def list_seasons(response: Response) -> list[svc.SeasonOption]:
    response.headers["Cache-Control"] = CACHE
    return _call(svc.seasons)


@router.get(
    "/seasons/{year}", response_model=svc.SeasonPredictions, operation_id="get_season_predictions"
)
def get_season(
    response: Response, year: int = Path(..., ge=2008, le=2100)
) -> svc.SeasonPredictions:
    response.headers["Cache-Control"] = CACHE
    return _call(lambda: svc.season(year))


@router.get(
    "/matches/{match_id}", response_model=svc.MatchPrediction, operation_id="get_match_prediction"
)
def get_match(response: Response, match_id: int = Path(..., ge=1)) -> svc.MatchPrediction:
    response.headers["Cache-Control"] = CACHE
    return _call(lambda: svc.match(match_id))


@router.post(
    "/matches/{match_id}/optimise",
    response_model=svc.OptimiseResult,
    operation_id="optimise_match_prediction",
)
def optimise(body: svc.OptimiseRequest, match_id: int = Path(..., ge=1)) -> svc.OptimiseResult:
    try:
        return _call(lambda: svc.optimise(match_id, body.locks, body.excludes))
    except ValueError as e:  # unknown ids, infeasible locks/excludes
        raise HTTPException(status_code=422, detail=str(e)) from e


# Building a season solves ~70 XIs (several seconds); do it once in the background at startup so
# the first visitor doesn't wait. Skipped under pytest (tests point P11_MODELS_DIR elsewhere).
if "pytest" not in sys.modules:
    threading.Thread(target=svc.warm, name="predictions-warm", daemon=True).start()
