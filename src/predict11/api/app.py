"""FastAPI app: typed contracts, a thin API over the prediction service, and it
serves the single-page frontend. No business logic lives here.
"""
from __future__ import annotations

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from ..config import ROOT
from . import service

FRONTEND_DIR = ROOT / "frontend"

app = FastAPI(title="Predict-11", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8000", "http://127.0.0.1:8000"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


class PredictRequest(BaseModel):
    team1: str
    team2: str


@app.get("/api/teams")
def teams():
    return service.list_teams()


@app.post("/api/predict")
def predict(req: PredictRequest):
    if req.team1 == req.team2:
        raise HTTPException(400, "team1 and team2 must differ")
    try:
        result = service.predict_fixture(req.team1, req.team2)
    except FileNotFoundError as e:
        raise HTTPException(404, str(e)) from e
    if result.get("status") != "ok":
        raise HTTPException(422, result.get("error", "prediction failed"))
    return result


@app.get("/")
def index():
    return FileResponse(FRONTEND_DIR / "index.html")


if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")
