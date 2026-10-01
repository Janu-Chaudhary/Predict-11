"""Match start time: ``match.start_time_utc`` / ``day_night`` / ``start_time_source``.

Known times (cached payloads, no requests):
- ``bcci``: stats.bcci.tv per-match scorecards (IPL 2026) and the 2025 results list
  (``start_datetime_utc``, ``start_time_local``).
- ``espn``: ESPNcricinfo ``__NEXT_DATA__`` ``startTime`` (IPL 2026; fills gaps, cross-checks).

``day_night``: ``day`` = afternoon start (local start before 17:00, i.e. the 15:30/16:00 IST
slot), ``night`` = evening start.

Inference (``source='inferred'``, day_night only, start_time_utc left NULL): IPL plays at most
two matches a day; on a double-header day the lower match number is the afternoon game, and a
single-match day is an evening game. The rule is checked against every 2025-26 known time
before it is applied (``validate_inference``). Exact clock times are *not* inferred because the
evening slot moved over the years (20:00 IST in early seasons, 19:30 IST from 2020), so the
clock time for older seasons needs a real source: ESPN's open core API
``core.espnuk.org/v2/sports/cricket/events/<match_id>`` returns ``date`` (UTC) and ``dayNight``
for 2008 matches too (1 request per match, ~1,100 requests for 2008-2024; not run).
"""

from __future__ import annotations

import datetime as dt
import json
from collections import defaultdict
from pathlib import Path
from typing import Any

from sqlalchemy import Connection, text

from p11.ingest.player_attributes import BCCI_RAW, ESPN_SCORECARDS, SPIKES
from p11.registry.canonical import canonical_team_name

BCCI_RESULTS = (SPIKES / "iplt20" / "samples" / "03" / "results_2025.json",)
IST = dt.timezone(dt.timedelta(hours=5, minutes=30))
DAY_CUTOFF_LOCAL = dt.time(17, 0)


def day_night_of(start_utc: dt.datetime, tz: dt.tzinfo = IST) -> str:
    return "day" if start_utc.astimezone(tz).time() < DAY_CUTOFF_LOCAL else "night"


def _bcci_records(raw_dir: Path = BCCI_RAW, results: tuple[Path, ...] = BCCI_RESULTS):
    """(local date, {team1, team2}, start utc, offset minutes) from cached BCCI payloads."""
    docs: list[dict[str, Any]] = []
    for f in sorted(raw_dir.glob("*/scorecard.json")):
        try:
            docs.append(json.loads(f.read_text())["match"])
        except (json.JSONDecodeError, KeyError):
            continue
    for f in results:
        if f.exists():
            docs.extend(json.loads(f.read_text()).get("match", []))
    for m in docs:
        if not m.get("start_datetime_utc"):
            continue
        utc = dt.datetime.fromisoformat(m["start_datetime_utc"]).replace(tzinfo=dt.UTC)
        off = int(m.get("start_time_offset") or 330)
        yield (
            dt.date.fromisoformat(m["start_date"]),
            frozenset(canonical_team_name(m[k]) for k in ("team1_name", "team2_name")),
            utc,
            dt.timezone(dt.timedelta(minutes=off)),
        )


def _espn_records(root: Path = ESPN_SCORECARDS):
    """(cricinfo match id, start utc, floodlit) from cached ESPN scorecards."""
    for f in sorted(root.glob("*/full-scorecard.next.json")):
        m = json.loads(f.read_text())["props"]["appPageProps"]["data"]["match"]
        if not m.get("startTime") or not m.get("timePublished", True):
            continue
        utc = dt.datetime.fromisoformat(m["startTime"].replace("Z", "+00:00"))
        yield int(m["objectId"]), utc, m.get("floodlit")


def _matches(conn: Connection) -> list[dict[str, Any]]:
    rows = conn.execute(
        text(
            """
            SELECT m.id, m.cricinfo_id, m.start_date, m.match_number, s.year,
                   t1.name AS team1, t2.name AS team2
            FROM match m JOIN season s ON s.id = m.season_id
            JOIN team t1 ON t1.id = m.team1_id JOIN team t2 ON t2.id = m.team2_id
            """
        )
    ).mappings()
    return [dict(r) for r in rows]


def infer_day_night(matches: list[dict[str, Any]]) -> dict[int, str]:
    """match id -> inferred slot, from how many matches share the date and match numbers."""
    by_day: dict[dt.date, list[dict[str, Any]]] = defaultdict(list)
    for m in matches:
        by_day[m["start_date"]].append(m)
    out: dict[int, str] = {}
    for ms in by_day.values():
        if len(ms) == 1:
            out[ms[0]["id"]] = "night"
        elif len(ms) == 2 and all(m["match_number"] is not None for m in ms):
            a, b = sorted(ms, key=lambda m: m["match_number"])
            out[a["id"]], out[b["id"]] = "day", "night"
    return out


def known_times(conn: Connection) -> tuple[dict[int, dict[str, Any]], dict[str, Any]]:
    matches = _matches(conn)
    by_key = {(m["start_date"], frozenset((m["team1"], m["team2"]))): m for m in matches}
    by_cricinfo = {m["cricinfo_id"] or m["id"]: m for m in matches}
    out: dict[int, dict[str, Any]] = {}
    stats = {"bcci_records": 0, "bcci_matched": 0, "espn_records": 0, "espn_filled": 0,
             "espn_agrees_with_bcci": 0, "espn_disagrees": []}
    for day, teams, utc, tz in _bcci_records():
        stats["bcci_records"] += 1
        m = by_key.get((day, teams))
        if m is None:
            continue  # abandoned without a ball (not in the DB)
        stats["bcci_matched"] += 1
        out[m["id"]] = {"start_time_utc": utc, "day_night": day_night_of(utc, tz),
                        "start_time_source": "bcci"}
    for mid, utc, _floodlit in _espn_records():
        stats["espn_records"] += 1
        m = by_cricinfo.get(mid)
        if m is None:
            continue
        if m["id"] in out:
            if out[m["id"]]["start_time_utc"] == utc:
                stats["espn_agrees_with_bcci"] += 1
            else:
                stats["espn_disagrees"].append(mid)
            continue
        stats["espn_filled"] += 1
        out[m["id"]] = {"start_time_utc": utc, "day_night": day_night_of(utc),
                        "start_time_source": "espn"}
    return out, stats


def validate_inference(conn: Connection, known: dict[int, dict[str, Any]]) -> dict[str, Any]:
    inferred = infer_day_night(_matches(conn))
    checked = [(mid, k["day_night"], inferred.get(mid)) for mid, k in known.items()]
    ok = sum(1 for _, a, b in checked if a == b)
    return {"checked": len(checked), "agree": ok,
            "mismatches": [mid for mid, a, b in checked if a != b][:20]}


def load_start_times(conn: Connection, *, infer: bool = True) -> dict[str, Any]:
    known, stats = known_times(conn)
    validation = validate_inference(conn, known)
    rows = [{"id": mid, **v} for mid, v in known.items()]
    inferred_n = 0
    if infer and validation["checked"] and validation["agree"] == validation["checked"]:
        for mid, slot in infer_day_night(_matches(conn)).items():
            if mid not in known:
                rows.append({"id": mid, "start_time_utc": None, "day_night": slot,
                             "start_time_source": "inferred"})
                inferred_n += 1
    # only these three columns are touched, and only where they change
    ch = _update_matches(conn, rows)
    by_src = conn.execute(
        text("SELECT coalesce(start_time_source, 'none'), count(*) FROM match GROUP BY 1")
    ).all()
    return {**stats, "inference_validation": validation, "inferred": inferred_n,
            "updated_rows": ch, "by_source": {r[0]: r[1] for r in by_src}}


def _update_matches(conn: Connection, rows: list[dict[str, Any]]) -> int:
    if not rows:
        return 0
    n = 0
    for r in rows:
        n += conn.execute(
            text(
                """
                UPDATE match SET start_time_utc = :start_time_utc, day_night = :day_night,
                       start_time_source = :start_time_source
                WHERE id = :id AND ROW(start_time_utc, day_night, start_time_source)
                      IS DISTINCT FROM ROW(CAST(:start_time_utc AS timestamptz),
                                           CAST(:day_night AS text),
                                           CAST(:start_time_source AS text))
                """
            ),
            r,
        ).rowcount
    return n

