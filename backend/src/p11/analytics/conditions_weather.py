"""Dew & weather watch (E2) over ``match_weather`` (see p11.ingest.weather).

Definitions:
- *Spread* = temperature_2m - dew_point_2m (degC) at 2 m. The smaller the spread, the closer the
  air is to saturation and the more dew forms on the outfield as the evening cools.
- *2nd-innings reference time* = (anchor) start + 2.5 h, i.e. roughly the first half of the
  chase (1st innings ~1 h 40 min + 20 min break). Values are linearly interpolated between the
  two surrounding UTC hours.
- *Dew risk*: high = spread <= 3 degC (``HIGH_DEW_SPREAD``), moderate = spread <= 6 degC,
  low otherwise. *High-dew evening* (the venue dew table) = night match whose spread at the
  reference time is <= 3 degC; every other night match with weather is a low-dew evening.
- *Rain risk*: precipitation summed over start .. start + 4 h: none = 0, low < 2 mm, high >= 2.
- Chase win % uses completed non-DLS matches with a winner (as the venue card).

Weather is ERA5 reanalysis on a ~0.1-0.25 degree grid (not a ground station), so absolute dew
points are smoothed; it ranks evenings well but is not the outfield reading.
"""

from __future__ import annotations

import datetime as dt
import threading
import time
from collections import defaultdict
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass
from typing import Any

from sqlalchemy import Connection, text

from ..ingest import weather as om
from .conditions_models import (
    DewBucket,
    DewReading,
    DewReport,
    DewSeason,
    Forecast,
    MatchConditions,
    WeatherHour,
)
from .players_data import Reference, reference
from .venues import RECENT_FROM

HIGH_DEW_SPREAD = 3.0
MODERATE_DEW_SPREAD = 6.0
SECOND_INNINGS_OFFSET = dt.timedelta(hours=2, minutes=30)
MATCH_SPAN = dt.timedelta(hours=4)
IST = om.IST
FORECAST_TTL_S = 1800.0
FORECAST_HORIZON = dt.timedelta(days=15)
ARCHIVE_LAG = dt.timedelta(days=5)  # ERA5 archive is ~5 days behind real time

Series = Mapping[dt.datetime, Mapping[str, float | None]]


# --------------------------------------------------------------------------- pure maths
def spread(temp: float | None, dew: float | None) -> float | None:
    return round(temp - dew, 2) if temp is not None and dew is not None else None


def dew_risk(s: float | None) -> str:
    if s is None:
        return "unknown"
    if s <= HIGH_DEW_SPREAD:
        return "high"
    if s <= MODERATE_DEW_SPREAD:
        return "moderate"
    return "low"


def is_high_dew(s: float | None) -> bool | None:
    return None if s is None else s <= HIGH_DEW_SPREAD


def rain_risk(mm: float | None) -> str:
    if mm is None:
        return "unknown"
    if mm <= 0:
        return "none"
    return "low" if mm < 2 else "high"


def interpolate(series: Series, at: dt.datetime, var: str) -> float | None:
    """Linear interpolation of hourly ``var`` at ``at`` (UTC); None if a neighbour is missing."""
    lo = at.replace(minute=0, second=0, microsecond=0)
    frac = (at - lo).total_seconds() / 3600
    a = series.get(lo, {}).get(var)
    if frac == 0:
        return a
    b = series.get(lo + dt.timedelta(hours=1), {}).get(var)
    if a is None or b is None:
        return None
    return round(a + (b - a) * frac, 2)


def reading(series: Series, start: dt.datetime) -> DewReading:
    at = start + SECOND_INNINGS_OFFSET
    temp = interpolate(series, at, "temperature_2m")
    dew = interpolate(series, at, "dew_point_2m")
    s = spread(temp, dew)
    rain_hours = [
        v.get("precipitation")
        for t, v in series.items()
        if start.replace(minute=0, second=0, microsecond=0) <= t < start + MATCH_SPAN
    ]
    rain = (
        round(sum(x for x in rain_hours if x is not None), 2)
        if rain_hours and all(x is not None for x in rain_hours)
        else None
    )
    return DewReading(
        at_utc=at,
        temperature_2m=temp,
        dew_point_2m=dew,
        relative_humidity_2m=interpolate(series, at, "relative_humidity_2m"),
        spread=s,
        dew_risk=dew_risk(s),
        rain_mm=rain,
        rain_risk=rain_risk(rain),
    )


def hours_out(series: Series, start: dt.datetime) -> list[WeatherHour]:
    out = []
    for t, v in sorted(series.items()):
        out.append(
            WeatherHour(
                time_utc=t,
                time_local=t.astimezone(IST).strftime("%H:%M"),
                offset_h=round((t - start).total_seconds() / 3600, 2),
                temperature_2m=v.get("temperature_2m"),
                relative_humidity_2m=v.get("relative_humidity_2m"),
                dew_point_2m=v.get("dew_point_2m"),
                spread=spread(v.get("temperature_2m"), v.get("dew_point_2m")),
                precipitation=v.get("precipitation"),
                wind_speed_10m=v.get("wind_speed_10m"),
            )
        )
    return out


@dataclass(slots=True)
class EveningResult:
    season: int
    spread: float | None
    humidity: float | None
    chase_won: bool | None  # None = not a decided non-DLS match


def bucket(results: Iterable[EveningResult], high: bool) -> DewBucket:
    rs = [
        r
        for r in results
        if r.spread is not None and r.chase_won is not None and is_high_dew(r.spread) is high
    ]
    wins = sum(1 for r in rs if r.chase_won)
    return DewBucket(
        matches=len(rs),
        chase_wins=wins,
        chase_win_pct=round(wins / len(rs) * 100, 1) if rs else None,
    )


def dew_season(season: int, evening: int, results: list[EveningResult]) -> DewSeason:
    sp = [r.spread for r in results if r.spread is not None]
    hu = [r.humidity for r in results if r.humidity is not None]
    return DewSeason(
        season=season,
        evening_matches=evening,
        with_weather=len(sp),
        avg_spread=round(sum(sp) / len(sp), 2) if sp else None,
        avg_humidity=round(sum(hu) / len(hu), 1) if hu else None,
        high_dew_matches=sum(1 for s in sp if s <= HIGH_DEW_SPREAD),
        high_dew=bucket(results, True),
        low_dew=bucket(results, False),
    )


# --------------------------------------------------------------------------- DB
def _weather(
    conn: Connection, where: str, params: dict[str, Any]
) -> dict[int, tuple[dict[dt.datetime, dict[str, float | None]], dt.datetime, bool]]:
    """match_id -> (series, anchor_utc, start_approx)."""
    out: dict[int, tuple[dict[dt.datetime, dict[str, float | None]], dt.datetime, bool]] = {}
    for r in conn.execute(
        text(
            "SELECT w.match_id, w.time_utc, w.temperature_2m, w.relative_humidity_2m, "
            "w.dew_point_2m, w.precipitation, w.wind_speed_10m, w.anchor_utc, w.start_approx "
            f"FROM match_weather w JOIN match m ON m.id = w.match_id WHERE {where} "
            "ORDER BY w.match_id, w.time_utc"
        ),
        params,
    ):
        ser, _, _ = out.setdefault(r[0], ({}, r[7], r[8]))
        ser[r[1]] = {
            v: (float(x) if x is not None else None) for v, x in zip(om.HOURLY, r[2:7], strict=True)
        }
    return out


def chase_won(ref: Reference, mid: int) -> bool | None:
    m = ref.matches.get(mid)
    if m is None or m.result != "win" or m.method or m.winner_id is None:
        return None
    chaser = ref.batting_team.get((mid, 2))
    return None if chaser is None else m.winner_id == chaser


def match_conditions(conn: Connection, mid: int) -> MatchConditions | None:
    row = conn.execute(
        text(
            "SELECT m.id, m.start_date, m.venue_id, v.name, m.day_night, m.start_time_utc "
            "FROM match m LEFT JOIN venue v ON v.id = m.venue_id WHERE m.id = :m"
        ),
        {"m": mid},
    ).first()
    if row is None:
        return None
    w = _weather(conn, "w.match_id = :m", {"m": mid}).get(mid)
    notes = []
    series: dict[dt.datetime, dict[str, float | None]] = {}
    approx: bool | None = None
    if w is None:
        notes.append("No weather stored for this match (run `p11 weather backfill`).")
        anchor = row[5]
    else:
        series, anchor, approx = w
        if approx:
            notes.append(
                "Start time approximate: inferred day/night slot anchored at 15:30 / 19:30 IST."
            )
    ref = reference(conn)
    return MatchConditions(
        match_id=row[0],
        date=row[1],
        venue_id=row[2],
        venue=row[3],
        day_night=row[4],
        start_utc=anchor,
        start_approx=approx,
        hourly=hours_out(series, anchor) if anchor else [],
        reading=reading(series, anchor) if series and anchor else None,
        chased_successfully=chase_won(ref, mid),
        notes=[
            *notes,
            f"Dew risk from temperature - dew point at start + 2.5 h: high <= "
            f"{HIGH_DEW_SPREAD:g} degC, moderate <= {MODERATE_DEW_SPREAD:g} degC.",
            "Open-Meteo archive (ERA5 reanalysis grid cell), not a ground station.",
        ],
    )


def dew_report(conn: Connection, vid: int | None) -> DewReport | None:
    ref = reference(conn)
    if vid is not None and vid not in ref.venues:
        return None
    nights = [
        r[0]
        for r in conn.execute(
            text(
                "SELECT id FROM match WHERE day_night = 'night'"
                + (" AND venue_id = :v" if vid is not None else "")
            ),
            {"v": vid},
        )
        if r[0] in ref.matches
    ]
    wx = _weather(
        conn,
        "m.day_night = 'night'" + (" AND m.venue_id = :v" if vid is not None else ""),
        {"v": vid},
    )
    by_season: dict[int, list[EveningResult]] = defaultdict(list)
    evening: dict[int, int] = defaultdict(int)
    for mid in nights:
        season = ref.matches[mid].season
        evening[season] += 1
        if mid not in wx:
            continue
        series, anchor, _ = wx[mid]
        rd = reading(series, anchor)
        by_season[season].append(
            EveningResult(season, rd.spread, rd.relative_humidity_2m, chase_won(ref, mid))
        )
    all_results = [r for rs in by_season.values() for r in rs]
    recent = [r for r in all_results if r.season >= RECENT_FROM]
    return DewReport(
        venue_id=vid,
        venue=ref.venues[vid][0] if vid is not None else None,
        high_dew_spread_c=HIGH_DEW_SPREAD,
        seasons=[dew_season(s, evening[s], by_season.get(s, [])) for s in sorted(evening)],
        total=dew_season(0, sum(evening.values()), all_results),
        recent=dew_season(
            RECENT_FROM, sum(n for s, n in evening.items() if s >= RECENT_FROM), recent
        ),
        notes=[
            "Evening = day_night 'night' (start 17:00 IST or later). Spread = temperature - "
            "dew point at start + 2.5 h (2nd innings), linear between hourly values.",
            f"High-dew evening: spread <= {HIGH_DEW_SPREAD:g} degC; all other evenings with "
            "weather are low-dew. Chase win % over completed non-DLS matches.",
            "Pre-2025 start times are approximate (19:30 IST assumed; early seasons began at "
            "20:00 IST). Weather is ERA5 reanalysis, not an outfield measurement.",
        ],
    )


# --------------------------------------------------------------------------- forecast
_fc_lock = threading.Lock()
_fc_cache: dict[tuple[Any, ...], tuple[float, Any]] = {}


def _fetch_cached(key: tuple[Any, ...], fetch: Callable[[], Any]) -> Any:
    now = time.monotonic()
    with _fc_lock:
        hit = _fc_cache.get(key)
        if hit and now - hit[0] < FORECAST_TTL_S:
            return hit[1]
    value = fetch()
    with _fc_lock:
        _fc_cache[key] = (now, value)
    return value


def venue_geo(conn: Connection, vid: int) -> tuple[str, float, float] | None:
    row = conn.execute(
        text(
            "SELECT v.name, g.lat, g.lon FROM venue v JOIN venue_geo g ON g.venue_id = v.id "
            "WHERE v.id = :v"
        ),
        {"v": vid},
    ).first()
    return (row[0], float(row[1]), float(row[2])) if row else None


def forecast(
    conn: Connection, vid: int, at: dt.datetime, now: dt.datetime | None = None
) -> Forecast | None:
    """Hourly weather at venue ``vid`` around ``at`` (start time, UTC-aware). Uses the Open-Meteo
    forecast API up to ~15 days ahead and the archive API for dates older than ~5 days.
    Raises ValueError beyond the forecast horizon."""
    geo = venue_geo(conn, vid)
    if geo is None:
        return None
    name, lat, lon = geo
    now = now or dt.datetime.now(dt.UTC)
    if at > now + FORECAST_HORIZON:
        raise ValueError(f"'at' is beyond the {FORECAST_HORIZON.days}-day forecast horizon")
    use_archive = at < now - ARCHIVE_LAG
    url = om.ARCHIVE_URL if use_archive else om.FORECAST_URL
    payload, series = _fetch_cached(
        (url, lat, lon, at.isoformat()), lambda: om.fetch_window(lat, lon, at, url=url)
    )
    notes = [
        f"Dew risk from temperature - dew point at start + 2.5 h: high <= "
        f"{HIGH_DEW_SPREAD:g} degC, moderate <= {MODERATE_DEW_SPREAD:g} degC.",
    ]
    if not use_archive:
        notes.append("Forecast values; cached for 30 min. Accuracy drops beyond ~3 days.")
    return Forecast(
        venue_id=vid,
        venue=name,
        at_utc=at,
        source="open-meteo-archive" if use_archive else "open-meteo-forecast",
        grid_lat=payload.get("latitude"),
        grid_lon=payload.get("longitude"),
        hourly=hours_out(series, at),
        reading=reading(series, at) if series else None,
        notes=notes,
    )
