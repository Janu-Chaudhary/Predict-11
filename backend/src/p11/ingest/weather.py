"""Venue coordinates + Open-Meteo hourly weather (E2 dew & weather watch).

Coordinates (``venue_geo``): one row per canonical venue, WGS84 decimal degrees. Each value is
the English Wikipedia article's coordinates (``{{coord}}``, read via the MediaWiki
``prop=coordinates`` API) where the article carries them, otherwise the article's Wikidata item
P625 (coordinate location). ``source`` names the article / item so every number can be checked.

Weather (``match_weather``): Open-Meteo historical archive (``archive-api.open-meteo.com``,
ERA5-based reanalysis, no key). Requests always use ``timezone=GMT`` and rows are stored as UTC
hours. (With ``timezone=Asia/Kolkata`` Open-Meteo labels each UTC hour with the IST clock
truncated to the hour: the value labelled ``19:00`` IST is really the 14:00 UTC = 19:30 IST
hour. Storing UTC avoids that half-hour ambiguity.)

Per match the window is ``anchor - 4 h .. anchor + 4 h`` (whole UTC hours), where the anchor is
``match.start_time_utc`` (real BCCI/ESPN time, 2025-26) or, when only the inferred
``day_night`` slot is known, 15:30 IST (day) / 19:30 IST (night) with ``start_approx = true``.
Early seasons actually started evening games at 20:00 IST and 2009 was in South Africa on IST
clocks, so approximate anchors can be ~30 min off.

Politeness: one archive request per (venue, season) covering every match date of that venue in
that season (not one per match), at most ``REQUEST_GAP_S`` apart, with retry/backoff on 429/5xx.
Raw responses are archived gzipped under ``data/archive/open-meteo/``.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import time
from collections import defaultdict
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any

import httpx
from sqlalchemy import Connection, text

from p11.core.upsert import Changes, upsert
from p11.ingest.archive import archive_payload

ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
HOURLY = (
    "temperature_2m",
    "relative_humidity_2m",
    "dew_point_2m",
    "precipitation",
    "wind_speed_10m",
)
WINDOW_H = 4
IST = dt.timezone(dt.timedelta(hours=5, minutes=30))
DAY_START_IST = dt.time(15, 30)
NIGHT_START_IST = dt.time(19, 30)
REQUEST_GAP_S = 1.0
USER_AGENT = "predict11/2.0 (IPL analytics; personal research)"
SOURCE = "open-meteo-archive"

# canonical venue name -> (lat, lon, source). Wikipedia = enwiki {{coord}}; wikidata = P625.
VENUE_GEO: dict[str, tuple[float, float, str]] = {
    "Rajiv Gandhi International Stadium": (
        17.40650,
        78.55044,
        "wikidata:Q7286209 (Rajiv Gandhi International Cricket Stadium)",
    ),
    "Maharashtra Cricket Association Stadium": (
        18.67444,
        73.70639,
        "wikidata:Q7631918 (Maharashtra Cricket Association Stadium)",
    ),
    "Saurashtra Cricket Association Stadium": (
        22.36300,
        70.71000,
        "wikidata:Q7427525 (Niranjan Shah Stadium)",
    ),
    "Holkar Cricket Stadium": (22.72430, 75.87997, "wikidata:Q5880726 (Holkar Stadium)"),
    "M Chinnaswamy Stadium": (12.97889, 77.59944, "wikipedia:M. Chinnaswamy Stadium"),
    "Wankhede Stadium": (18.93889, 72.82583, "wikipedia:Wankhede Stadium"),
    "Eden Gardens": (22.56444, 88.34333, "wikidata:Q2035004 (Eden Gardens)"),
    "Arun Jaitley Stadium": (28.63778, 77.24306, "wikipedia:Arun Jaitley Cricket Stadium"),
    "Punjab Cricket Association IS Bindra Stadium": (
        30.69086,
        76.73726,
        "wikipedia:I. S. Bindra Stadium",
    ),
    "Green Park": (26.48194, 80.34778, "wikipedia:Green Park Stadium"),
    "MA Chidambaram Stadium": (13.06278, 80.27944, "wikipedia:M. A. Chidambaram Stadium"),
    "Sawai Mansingh Stadium": (26.89403, 75.80322, "wikidata:Q7428548 (Sawai Mansingh Stadium)"),
    "Dr. Y.S. Rajasekhara Reddy ACA-VDCA Cricket Stadium": (
        17.79736,
        83.35194,
        "wikidata:Q23975544 (ACA-VDCA Cricket Stadium)",
    ),
    "Zayed Cricket Stadium": (
        24.39639,
        54.54056,
        "wikidata:Q7492977 (Sheikh Zayed Cricket Stadium)",
    ),
    "Dubai International Cricket Stadium": (
        25.04667,
        55.21889,
        "wikidata:Q5206119 (Dubai International Cricket Stadium)",
    ),
    "Sharjah Cricket Stadium": (25.33082, 55.42096, "wikidata:Q3056365 (Sharjah Cricket Stadium)"),
    "Narendra Modi Stadium": (23.09167, 72.59750, "wikidata:Q3531421 (Narendra Modi Stadium)"),
    "Brabourne Stadium": (18.93222, 72.82472, "wikipedia:Brabourne Stadium"),
    "Dr DY Patil Sports Academy": (19.04194, 73.02667, "wikidata:Q1156264 (DY Patil Stadium)"),
    "Bharat Ratna Shri Atal Bihari Vajpayee Ekana Cricket Stadium": (
        26.81120,
        81.01680,
        "wikidata:Q109373985 (Ekana Cricket Stadium)",
    ),
    "Barsapara Cricket Stadium": (
        26.14509,
        91.73651,
        "wikidata:Q4864977 (Assam Cricket Association Stadium)",
    ),
    "Himachal Pradesh Cricket Association Stadium": (
        32.19767,
        76.32600,
        "wikidata:Q5635576 (Himachal Pradesh Cricket Association Stadium)",
    ),
    "Maharaja Yadavindra Singh International Cricket Stadium": (
        30.77889,
        76.72417,
        "wikidata:Q24747936 (Maharaja Yadavindra Singh Intl Cricket Stadium)",
    ),
    "Shaheed Veer Narayan Singh International Stadium": (
        21.20417,
        81.82333,
        "wikidata:Q7285044 (Shaheed Veer Narayan Singh Intl Cricket Stadium)",
    ),
    "Newlands": (-33.97370, 18.46893, "wikidata:Q3045283 (Newlands Cricket Ground)"),
    "St George's Park": (-33.96650, 25.61000, "wikidata:Q3495321 (St George's Park)"),
    "Kingsmead": (-29.85000, 31.02778, "wikipedia:Kingsmead Cricket Ground"),
    "SuperSport Park": (-25.85990, 28.19540, "wikidata:Q142670 (Centurion Park)"),
    "Buffalo Park": (-33.00671, 27.91937, "wikidata:Q4985806 (Buffalo Park)"),
    "New Wanderers Stadium": (-26.13111, 28.05750, "wikipedia:Wanderers Stadium"),
    "De Beers Diamond Oval": (-28.74243, 24.79772, "wikidata:Q5244241 (De Beers Diamond Oval)"),
    "OUTsurance Oval": (-29.11668, 26.20527, "wikidata:Q5094407 (Mangaung Oval)"),
    "Barabati Stadium": (20.48111, 85.86861, "wikipedia:Barabati Stadium"),
    "Vidarbha Cricket Association Stadium": (
        21.01360,
        79.03960,
        "wikidata:Q7927721 (VCA Stadium, Jamtha)",
    ),
    "Nehru Stadium": (9.99722, 76.30111, "wikidata:Q1684271 (Jawaharlal Nehru Stadium, Kochi)"),
    "JSCA International Stadium Complex": (
        23.31005,
        85.27488,
        "wikidata:Q15229080 (JSCA International Stadium Complex)",
    ),
}


# --------------------------------------------------------------------------- pure helpers
def anchor_of(
    start_time_utc: dt.datetime | None, day_night: str | None, start_date: dt.date
) -> tuple[dt.datetime, bool]:
    """(anchor start in UTC, approximate?) for a match."""
    if start_time_utc is not None:
        return start_time_utc.astimezone(dt.UTC), False
    t = DAY_START_IST if day_night == "day" else NIGHT_START_IST
    return dt.datetime.combine(start_date, t, IST).astimezone(dt.UTC), True


def window_hours(anchor: dt.datetime, hours: int = WINDOW_H) -> list[dt.datetime]:
    """Whole UTC hours from floor(anchor - h) to ceil(anchor + h)."""
    lo = (anchor - dt.timedelta(hours=hours)).replace(minute=0, second=0, microsecond=0)
    hi = anchor + dt.timedelta(hours=hours)
    if hi.minute or hi.second or hi.microsecond:
        hi = hi.replace(minute=0, second=0, microsecond=0) + dt.timedelta(hours=1)
    out = []
    t = lo
    while t <= hi:
        out.append(t)
        t += dt.timedelta(hours=1)
    return out


def parse_hourly(payload: dict[str, Any]) -> dict[dt.datetime, dict[str, float | None]]:
    """Open-Meteo ``hourly`` block (requested with timezone=GMT) -> {utc hour: {var: value}}."""
    if payload.get("utc_offset_seconds", 0) != 0:
        raise ValueError("expected a timezone=GMT response")
    h = payload["hourly"]
    out: dict[dt.datetime, dict[str, float | None]] = {}
    for i, ts in enumerate(h["time"]):
        t = dt.datetime.fromisoformat(ts).replace(tzinfo=dt.UTC)
        out[t] = {v: h[v][i] for v in HOURLY if v in h}
    return out


def _dec(x: float | None) -> Decimal | None:
    """float -> Decimal for NUMERIC COPY (psycopg cannot COPY a float into numeric)."""
    return None if x is None else Decimal(str(x))


# --------------------------------------------------------------------------- HTTP client
@dataclass
class OpenMeteo:
    """Tiny polite client: spacing between requests, retry with backoff on 429 / 5xx."""

    gap_s: float = REQUEST_GAP_S
    retries: int = 4
    timeout_s: float = 60.0
    requests: int = 0
    _last: float = 0.0
    _client: httpx.Client | None = field(default=None, repr=False)

    def _http(self) -> httpx.Client:
        if self._client is None:
            self._client = httpx.Client(timeout=self.timeout_s, headers={"User-Agent": USER_AGENT})
        return self._client

    def get(self, url: str, params: dict[str, Any]) -> tuple[dict[str, Any], bytes]:
        last_err: Exception | None = None
        for attempt in range(self.retries):
            wait = self._last + self.gap_s - time.monotonic()
            if wait > 0:
                time.sleep(wait)
            self._last = time.monotonic()
            self.requests += 1
            try:
                r = self._http().get(url, params=params)
            except httpx.TransportError as e:
                last_err = e
            else:
                if r.status_code == 200:
                    return r.json(), r.content
                if r.status_code not in (429, 500, 502, 503, 504):
                    raise RuntimeError(f"Open-Meteo HTTP {r.status_code}: {r.text[:300]}")
                last_err = RuntimeError(f"Open-Meteo HTTP {r.status_code}")
            time.sleep(min(60.0, 5.0 * 2**attempt))
        raise RuntimeError(f"Open-Meteo request failed after {self.retries} tries: {last_err}")

    def hourly(
        self, url: str, lat: float, lon: float, start: dt.date, end: dt.date
    ) -> tuple[dict[str, Any], bytes]:
        return self.get(
            url,
            {
                "latitude": lat,
                "longitude": lon,
                "start_date": start.isoformat(),
                "end_date": end.isoformat(),
                "hourly": ",".join(HOURLY),
                "timezone": "GMT",
            },
        )

    def close(self) -> None:
        if self._client is not None:
            self._client.close()
            self._client = None


# --------------------------------------------------------------------------- venue_geo
def load_venue_geo(conn: Connection) -> dict[str, Any]:
    venues: dict[str, int] = dict(conn.execute(text("SELECT name, id FROM venue")).all())
    rows, missing = [], []
    for name, vid in sorted(venues.items()):
        geo = VENUE_GEO.get(name)
        if geo is None:
            missing.append(name)
            continue
        rows.append({"venue_id": vid, "lat": _dec(geo[0]), "lon": _dec(geo[1]), "source": geo[2]})
    ch = upsert(conn, "venue_geo", rows, ["venue_id"])
    unknown = sorted(set(VENUE_GEO) - set(venues))
    return {
        "venues": len(venues),
        "with_coordinates": len(rows),
        "missing": missing,
        "unused_entries": unknown,
        "changes": vars(ch),
    }


# --------------------------------------------------------------------------- backfill
@dataclass(frozen=True, slots=True)
class MatchSlot:
    match_id: int
    venue_id: int
    season: int
    anchor: dt.datetime
    approx: bool


@dataclass
class BackfillReport:
    matches: int = 0
    skipped_existing: int = 0
    no_coordinates: int = 0
    requests: int = 0
    groups: int = 0
    rows: Changes = field(default_factory=Changes)
    matches_written: int = 0
    approx_matches: int = 0
    missing_hours: int = 0
    seconds: float = 0.0
    errors: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        d = {k: v for k, v in vars(self).items() if k != "rows"}
        d["rows"] = vars(self.rows)
        return d


def match_slots(conn: Connection, seasons: Sequence[int] | None = None) -> list[MatchSlot]:
    sql = """
        SELECT m.id, m.venue_id, s.year, m.start_date, m.start_time_utc, m.day_night
        FROM match m
        JOIN season s ON s.id = m.season_id
        JOIN competition c ON c.id = s.competition_id AND c.code = 'ipl'
        WHERE m.venue_id IS NOT NULL
    """
    params: dict[str, Any] = {}
    if seasons:
        sql += " AND s.year = ANY(:seasons)"
        params["seasons"] = list(seasons)
    out = []
    for mid, vid, season, date, start_utc, dn in conn.execute(text(sql + " ORDER BY m.id"), params):
        anchor, approx = anchor_of(start_utc, dn, date)
        out.append(MatchSlot(mid, vid, season, anchor, approx))
    return out


def backfill_weather(
    conn: Connection,
    seasons: Sequence[int] | None = None,
    *,
    force: bool = False,
    client: OpenMeteo | None = None,
    archive_root: Any = None,
    commit: Callable[[], None] | None = None,
) -> BackfillReport:
    """Fetch + upsert ``match_weather`` for IPL matches (one request per venue-season)."""
    t0 = time.monotonic()
    rep = BackfillReport()
    own_client = client is None
    om = client or OpenMeteo()
    geo = {
        r[0]: (float(r[1]), float(r[2]))
        for r in conn.execute(text("SELECT venue_id, lat, lon FROM venue_geo"))
    }
    have = {r[0] for r in conn.execute(text("SELECT DISTINCT match_id FROM match_weather"))}
    groups: dict[tuple[int, int], list[MatchSlot]] = defaultdict(list)
    for s in match_slots(conn, seasons):
        rep.matches += 1
        if s.venue_id not in geo:
            rep.no_coordinates += 1
            continue
        if s.match_id in have and not force:
            rep.skipped_existing += 1
            continue
        groups[(s.venue_id, s.season)].append(s)
    rep.groups = len(groups)
    try:
        for (vid, season), slots in sorted(groups.items()):
            lat, lon = geo[vid]
            hours = {s.match_id: window_hours(s.anchor) for s in slots}
            first = min(h[0] for h in hours.values()).date()
            last = max(h[-1] for h in hours.values()).date()
            try:
                payload, raw = om.hourly(ARCHIVE_URL, lat, lon, first, last)
            except RuntimeError as e:
                rep.errors.append(f"venue {vid} season {season}: {e}")
                continue
            if archive_root is not None:
                sha = hashlib.sha256(raw).hexdigest()
                archive_payload(
                    archive_root, "open-meteo", f"archive_v{vid}_{season}.json", sha, raw
                )
            series = parse_hourly(payload)
            rows = []
            for s in slots:
                for t in hours[s.match_id]:
                    vals = series.get(t)
                    if vals is None:
                        rep.missing_hours += 1
                        continue
                    rows.append(
                        {
                            "match_id": s.match_id,
                            "time_utc": t,
                            **{k: _dec(v) for k, v in vals.items()},
                            "anchor_utc": s.anchor,
                            "start_approx": s.approx,
                            "source": SOURCE,
                            "grid_lat": _dec(payload.get("latitude")),
                            "grid_lon": _dec(payload.get("longitude")),
                        }
                    )
                rep.matches_written += 1
                rep.approx_matches += s.approx
            rep.rows += upsert(
                conn,
                "match_weather",
                rows,
                ["match_id", "time_utc"],
                delete_missing=(["match_id"], [(s.match_id,) for s in slots]),
            )
            if commit is not None:
                commit()
    finally:
        rep.requests = om.requests
        if own_client:
            om.close()
    rep.seconds = round(time.monotonic() - t0, 1)
    return rep


def fetch_window(
    lat: float,
    lon: float,
    center_utc: dt.datetime,
    *,
    hours: int = WINDOW_H,
    url: str = FORECAST_URL,
    client: OpenMeteo | None = None,
) -> tuple[dict[str, Any], dict[dt.datetime, dict[str, float | None]]]:
    """Hourly values for ``center ± hours`` from one Open-Meteo endpoint (forecast or archive)."""
    want = window_hours(center_utc, hours)
    om = client or OpenMeteo(gap_s=0.0, retries=2, timeout_s=20.0)
    try:
        payload, _ = om.hourly(url, lat, lon, want[0].date(), want[-1].date())
    finally:
        if client is None:
            om.close()
    series = parse_hourly(payload)
    return payload, {t: series[t] for t in want if t in series}
