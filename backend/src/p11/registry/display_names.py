"""Full display names ("Suryakumar Yadav") for Cricsheet players ("SA Yadav").

Cricsheet's register only carries scorecard names, so search for "suryakumar" found nothing.
This loader collects full names from sources already on disk / in the DB and stores them as
``player_alias`` rows:

- ``source='display'``     exactly one per player: the name the UI should print.
- ``source='display_alt'`` other full spellings, searchable but never displayed.

Sources, best first (the first one that knows a player supplies the display name):
1. ``cricinfo``    ESPNcricinfo ``longName`` from the cached 2026 full scorecards.
2. ``espn_api``    ESPN core API ``displayName`` / ``fullName`` (cached athlete JSON, covers
                   retired players).
3. ``bcci``        iplt20 squads_2026.csv ``name`` (bcci id bridged via player_attribute).
4. ``iplt20_2025`` owner-supplied 2025 squad CSV name (player_attribute.detail.name).

Idempotent: re-running with the same inputs changes 0 rows; display rows that are no longer
produced are deleted. Run ``p11 registry display-names``.
"""

from __future__ import annotations

import csv
import json
from collections import defaultdict
from pathlib import Path
from typing import Any

from sqlalchemy import Connection, text

from p11.core.upsert import upsert
from p11.ingest.player_attributes import (
    BCCI_SQUADS_CSV,
    ESPN_SCORECARDS,
    espn_cache_dir,
    iter_espn_scorecard_players,
)

SOURCES = ("cricinfo", "espn_api", "bcci", "iplt20_2025")


def _clean(name: Any) -> str | None:
    if not isinstance(name, str):
        return None
    s = " ".join(name.split())
    return s if len(s) >= 3 else None


def _cricinfo_ids(conn: Connection) -> dict[str, str]:
    rows = conn.execute(
        text("SELECT source_key, player_id FROM player_source_id WHERE source = 'cricinfo'")
    )
    return {r[0]: r[1] for r in rows}


def collect(
    conn: Connection,
    *,
    scorecards: Path = ESPN_SCORECARDS,
    espn_cache: Path | None = None,
    bcci_csv: Path = BCCI_SQUADS_CSV,
) -> dict[str, dict[str, list[str]]]:
    """player id -> source -> [full names] (in source order)."""
    out: dict[str, dict[str, list[str]]] = defaultdict(lambda: defaultdict(list))

    def add(pid: str | None, source: str, name: Any) -> None:
        n = _clean(name)
        if pid and n and n not in out[pid][source]:
            out[pid][source].append(n)

    ids = _cricinfo_ids(conn)
    if scorecards.exists():
        for _day, p in iter_espn_scorecard_players(scorecards):
            add(ids.get(str(p.get("objectId"))), "cricinfo", p.get("longName"))

    cache = espn_cache if espn_cache is not None else espn_cache_dir()
    if cache.exists():
        for f in sorted(cache.glob("*.json")):
            pid = ids.get(f.stem)
            if pid is None:
                continue
            try:
                doc = json.loads(f.read_text())
            except json.JSONDecodeError:
                continue
            add(pid, "espn_api", doc.get("displayName"))
            add(pid, "espn_api", doc.get("fullName"))

    if bcci_csv.exists():
        bridge = {
            r[0]: r[1]
            for r in conn.execute(
                text(
                    "SELECT detail->>'bcci_id', player_id FROM player_attribute "
                    "WHERE source = 'bcci' AND detail ? 'bcci_id'"
                )
            )
        }
        with bcci_csv.open(encoding="utf-8") as f:
            for r in csv.DictReader(f):
                add(bridge.get(r["player_id"]), "bcci", r.get("name"))

    for pid, name in conn.execute(
        text(
            "SELECT player_id, detail->>'name' FROM player_attribute "
            "WHERE source = 'iplt20_2025' AND detail ? 'name'"
        )
    ):
        add(pid, "iplt20_2025", name)
    return out


def build_rows(names: dict[str, dict[str, list[str]]]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for pid, by_src in sorted(names.items()):
        ordered = [n for s in SOURCES for n in by_src.get(s, [])]
        if not ordered:
            continue
        seen: set[str] = set()
        for i, n in enumerate(ordered):
            if n in seen:
                continue
            seen.add(n)
            rows.append(
                {"player_id": pid, "name": n, "source": "display" if i == 0 else "display_alt"}
            )
    return rows


def load_display_names(conn: Connection, **kw: Any) -> dict[str, Any]:
    names = collect(conn, **kw)
    rows = build_rows(names)
    # A display spelling can equal an existing Cricsheet alias ("Virat Kohli"): it is
    # re-labelled 'display'; registry.people never relabels it back.
    ch = upsert(
        conn,
        "player_alias",
        rows,
        ["player_id", "name"],
        delete_missing=(["source"], [("display",), ("display_alt",)]),
    )
    per_source: dict[str, int] = defaultdict(int)
    for by_src in names.values():
        for s in SOURCES:
            if by_src.get(s):
                per_source[s] += 1
                break
    return {
        "players": sum(1 for r in rows if r["source"] == "display"),
        "display_from": dict(per_source),
        "alt_rows": sum(1 for r in rows if r["source"] == "display_alt"),
        "changes": vars(ch),
    }
