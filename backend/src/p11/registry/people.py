"""Cricsheet register -> player / player_source_id / player_alias.

people.csv: identifier (our canonical player key), name, unique_name and key_<source>[_N]
columns (cricinfo, cricbuzz, bcci, pulse, ...). names.csv: alternative names per identifier.
"""

from __future__ import annotations

import csv
import re
from pathlib import Path

from sqlalchemy import Connection, text

from p11.core.upsert import ChangeLog, upsert

_KEY_COL = re.compile(r"^key_(?P<source>[a-z0-9]+?)(?:_(?P<n>\d+))?$")


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def parse_people(path: Path) -> tuple[list[dict], list[dict]]:
    rows = _read_csv(path)
    players: list[dict] = []
    source_ids: list[dict] = []
    for r in rows:
        pid = r["identifier"].strip()
        players.append(
            {"id": pid, "name": r["name"].strip(), "unique_name": r["unique_name"].strip()}
        )
        for col, val in r.items():
            m = _KEY_COL.match(col or "")
            if m and val and val.strip():
                source_ids.append(
                    {"player_id": pid, "source": m["source"], "source_key": val.strip()}
                )
    return players, source_ids


def parse_names(path: Path, known_ids: set[str] | None = None) -> list[dict]:
    out = []
    for r in _read_csv(path):
        pid, name = r["identifier"].strip(), r["name"].strip()
        if name and (known_ids is None or pid in known_ids):
            out.append({"player_id": pid, "name": name, "source": "cricsheet_names"})
    return out


def load_registry(conn: Connection, people_csv: Path, names_csv: Path | None) -> ChangeLog:
    log = ChangeLog()
    players, source_ids = parse_people(people_csv)
    log.add("player", upsert(conn, "player", players, ["id"]))
    log.add(
        "player_source_id",
        upsert(conn, "player_source_id", source_ids, ["source", "source_key"]),
    )
    if names_csv is not None and names_csv.exists():
        known = {r[0] for r in conn.execute(text("SELECT id FROM player"))}
        aliases = parse_names(names_csv, known)
        log.add("player_alias", upsert(conn, "player_alias", aliases, ["player_id", "name"]))
    return log
