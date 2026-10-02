"""FastAPI app. Routers are thin; logic lives in the domain packages."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .. import __version__
from ..core import db
from ..core.logging import configure
from ..core.settings import get_settings
from .routers import conditions, fantasy, home, model_lab, players, seasons

configure()

app = FastAPI(title="Predict-11", version=__version__)
_settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=_settings.cors_origins,
    allow_origin_regex=_settings.effective_cors_origin_regex,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


@app.get("/api/v1/health")
def health() -> dict:
    return {"status": "ok", "version": __version__, "db": "ok" if db.ping() else "down"}


app.include_router(seasons.router, prefix="/api/v1")
app.include_router(players.router, prefix="/api/v1")
app.include_router(home.router, prefix="/api/v1")
app.include_router(fantasy.router, prefix="/api/v1")
app.include_router(conditions.router, prefix="/api/v1")
app.include_router(model_lab.router, prefix="/api/v1")
