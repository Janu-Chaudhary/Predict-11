"""Hero A data: official shot data (wagon wheel) for the last match's top innings.

Official shot coordinates are **not in the DB yet** (no shot table). Until an ingest lands,
``load_shots`` returns ``None`` (API 404, UI falls back to hero C) except for one documented
dev fallback: with the flag ``P11_HOME_DEV_SPIKE_WAGON=1`` (env) or ``?dev_spike_wagon=true``
(query), the cached Ellipse ``/wagon`` payload of the IPL 2026 Final in
``spikes/iplt20/samples/03/final_wagon_epr.json`` is served for that one match only.
"""

from __future__ import annotations

import json
import os
from collections import defaultdict
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

DEV_FLAG_ENV = "P11_HOME_DEV_SPIKE_WAGON"
SPIKE_FINAL_2026_MATCH_ID = 1535465
SPIKE_FILE = Path(__file__).resolve().parents[4] / "spikes/iplt20/samples/03/final_wagon_epr.json"
SPIKE_SOURCE = "Official shot data (IPL site feed, cached sample: dev fallback)"

ZONES = {
    1: "fine leg",
    2: "square leg",
    3: "midwicket",
    4: "long on",
    5: "long off",
    6: "cover",
    7: "point",
    8: "third man",
}


@dataclass(frozen=True, slots=True)
class RawShot:
    batter: str
    left_handed: bool
    innings: int
    over: int  # 0-based
    ball: int
    runs: int
    direction: float
    distance_pct: float
    zone: int
    bowler: str


def dev_flag_on(query_flag: bool = False) -> bool:
    return query_flag or os.environ.get(DEV_FLAG_ENV, "").strip().lower() in {"1", "true", "yes"}


def parse_spider(payload: dict[str, Any]) -> list[RawShot]:
    """Scoring shots from an Ellipse ``/wagon`` payload (``spider_data``, 1-based overs)."""
    out: list[RawShot] = []
    for s in payload.get("spider_data") or []:
        runs = int(s.get("runs_off_bat") or 0)
        if runs <= 0 or s.get("field_direction") is None:
            continue
        out.append(
            RawShot(
                batter=str(s.get("batting_player_name") or "?"),
                left_handed=str(s.get("batting_player_hand") or "").lower() == "left",
                innings=int(s.get("innings_number") or 0),
                over=max(0, int(s.get("over_number") or 1) - 1),
                ball=int(s.get("ball_number") or 0),
                runs=runs,
                direction=float(s["field_direction"]),
                distance_pct=float(s.get("field_distance_percent") or 0),
                zone=int(s.get("field_zone") or 0),
                bowler=str(s.get("bowling_player_name") or "?"),
            )
        )
    out.sort(key=lambda r: (r.innings, r.over, r.ball))
    return out


def top_innings(shots: list[RawShot]) -> tuple[str, int, list[RawShot]] | None:
    """The batter with the most runs off scoring shots, with their shots in ball order."""
    if not shots:
        return None
    by: dict[tuple[str, int], list[RawShot]] = defaultdict(list)
    for s in shots:
        by[(s.batter, s.innings)].append(s)
    (batter, _), best = max(by.items(), key=lambda kv: (sum(s.runs for s in kv[1]), kv[0][0]))
    return batter, sum(s.runs for s in best), best


@lru_cache(maxsize=1)
def _spike_payload() -> dict[str, Any] | None:
    try:
        return json.loads(SPIKE_FILE.read_text())
    except (OSError, ValueError):
        return None


def load_shots(match_id: int, *, query_flag: bool = False) -> list[RawShot] | None:
    """Shot data for a match, or None when none is available (no DB table yet)."""
    if match_id == SPIKE_FINAL_2026_MATCH_ID and dev_flag_on(query_flag):
        payload = _spike_payload()
        if payload is not None:
            return parse_spider(payload) or None
    return None
