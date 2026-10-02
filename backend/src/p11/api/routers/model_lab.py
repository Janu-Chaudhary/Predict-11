"""/api/v1/model: the Model Lab (trained fantasy-points model runs). Logic in
p11.analytics.model_lab; artifacts are read from ``models/`` (or ``P11_MODELS_DIR``).

Responses for one run are cached in-process by file mtime; the telemetry ETag is the file stamp,
so a browser revalidates for free (304) until a new run lands.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Literal

from fastapi import APIRouter, HTTPException, Path, Query, Request, Response

from ...analytics import model_lab as svc
from ..cache import weak_etag

router = APIRouter(prefix="/model", tags=["model"])
LIST_CACHE = "public, max-age=15, stale-while-revalidate=120"
RUN_CACHE = "public, max-age=120, stale-while-revalidate=600"
VersionP = Path(..., min_length=1, max_length=128, pattern=svc.VERSION_RE.pattern)


def _call[T](fn: Callable[[], T]) -> T:
    try:
        return fn()
    except svc.NotFound as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e


@router.get("/runs", response_model=list[svc.RunSummary], operation_id="list_model_runs")
def list_runs(response: Response) -> list[svc.RunSummary]:
    response.headers["Cache-Control"] = LIST_CACHE
    return svc.list_runs()


@router.get("/runs/{version}/telemetry", operation_id="get_model_telemetry")
def get_telemetry(request: Request, version: str = VersionP) -> Response:
    t = _call(lambda: svc.telemetry(version))
    etag = weak_etag(t.etag, "mt")
    headers = {"ETag": etag, "Cache-Control": RUN_CACHE, "Vary": "Accept-Encoding"}
    if request.headers.get("if-none-match") == etag:
        return Response(status_code=304, headers=headers)
    if "gzip" in request.headers.get("accept-encoding", ""):
        headers["Content-Encoding"] = "gzip"
        return Response(t.gz, media_type="application/json", headers=headers)
    return Response(t.body, media_type="application/json", headers=headers)


@router.get(
    "/runs/{version}/matches",
    response_model=list[svc.MatchRow],
    operation_id="list_model_matches",
)
def list_matches(
    response: Response,
    version: str = VersionP,
    phase: Literal["test", "walkforward"] = Query("test"),
) -> list[svc.MatchRow]:
    response.headers["Cache-Control"] = RUN_CACHE
    return _call(lambda: svc.matches(version, phase))


@router.get(
    "/runs/{version}/matches/{match_id}",
    response_model=svc.MatchDetail,
    operation_id="get_model_match",
)
def get_match(response: Response, match_id: int, version: str = VersionP) -> svc.MatchDetail:
    response.headers["Cache-Control"] = RUN_CACHE
    return _call(lambda: svc.match_detail(version, match_id))


@router.get(
    "/runs/{version}/explain", response_model=svc.Explanation, operation_id="explain_prediction"
)
def explain(
    response: Response,
    version: str = VersionP,
    match_id: int = Query(...),
    player_id: str = Query(..., min_length=1, max_length=32),
) -> svc.Explanation:
    response.headers["Cache-Control"] = RUN_CACHE
    return _call(lambda: svc.explain(version, match_id, player_id))


@router.get("/compare", response_model=svc.Comparison, operation_id="compare_model_runs")
def compare(
    response: Response,
    a: str = Query(..., min_length=1, max_length=128, pattern=svc.VERSION_RE.pattern),
    b: str = Query(..., min_length=1, max_length=128, pattern=svc.VERSION_RE.pattern),
) -> svc.Comparison:
    response.headers["Cache-Control"] = RUN_CACHE
    return _call(lambda: svc.compare(a, b))
