"""Cricsheet zip -> raw archive -> parse -> DQ -> Postgres, idempotently.

Unchanged payloads (same sha256 already loaded for that match) are skipped outright; with
``force=True`` they are re-parsed and re-upserted, which must still report zero row changes.
"""

from __future__ import annotations

import datetime as dt
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from sqlalchemy import Connection, Engine, text

from p11.core.upsert import ChangeLog, upsert
from p11.registry.canonical import Resolver

from .archive import archive_payload
from .quality import check_match
from .sources import cricsheet
from .store import SourceCopy, write_copies


@dataclass
class BackfillReport:
    files: int = 0
    skipped_unchanged: int = 0
    loaded: int = 0
    quarantined: dict[int, list[dict[str, Any]]] = field(default_factory=dict)
    errors: dict[str, str] = field(default_factory=dict)
    changes: ChangeLog = field(default_factory=ChangeLog)
    seconds: float = 0.0

    def summary(self) -> dict[str, Any]:
        return {
            "files": self.files,
            "skipped_unchanged": self.skipped_unchanged,
            "loaded_ok": self.loaded,
            "quarantined": len(self.quarantined),
            "errors": len(self.errors),
            "row_changes": self.changes.total,
            "changes_by_table": self.changes.as_dict(),
            "seconds": round(self.seconds, 1),
        }


def _loaded_payloads(conn: Connection) -> dict[int, str]:
    """match_id -> sha256 of the cricsheet payload loaded cleanly for it. Quarantined copies are
    always re-checked (a registry refresh may fix them); that re-check is itself idempotent."""
    rows = conn.execute(
        text(
            "SELECT ms.match_id, rp.sha256 FROM match_source ms "
            "JOIN raw_payload rp ON rp.id = ms.raw_payload_id "
            "WHERE ms.source = :s AND ms.status = 'loaded'"
        ),
        {"s": cricsheet.SOURCE},
    )
    return {r[0]: r[1] for r in rows}


def backfill_zip(
    engine: Engine,
    zip_path: Path,
    archive_root: Path,
    *,
    force: bool = False,
    chunk: int = 100,
    only: set[int] | None = None,
) -> BackfillReport:
    t0 = time.perf_counter()
    rep = BackfillReport()
    fetched_at = dt.datetime.fromtimestamp(zip_path.stat().st_mtime, tz=dt.UTC)
    with engine.connect() as conn:
        known_ids = {r[0] for r in conn.execute(text("SELECT id FROM player"))}
        loaded = _loaded_payloads(conn)
    if not known_ids:
        raise RuntimeError("player table is empty: run `p11 registry load` first")

    batch: list[cricsheet.RawFile] = []

    def flush() -> None:
        if not batch:
            return
        with engine.begin() as conn:
            _load_batch(conn, batch, zip_path.name, fetched_at, archive_root, known_ids, rep)
        batch.clear()

    for rf in cricsheet.iter_zip(zip_path):
        if only is not None and rf.match_id not in only:
            continue
        rep.files += 1
        if not force and loaded.get(rf.match_id) == rf.sha256:
            rep.skipped_unchanged += 1
            continue
        batch.append(rf)
        if len(batch) >= chunk:
            flush()
    flush()
    rep.seconds = time.perf_counter() - t0
    return rep


def _load_batch(
    conn: Connection,
    files: list[cricsheet.RawFile],
    zip_name: str,
    fetched_at: dt.datetime,
    archive_root: Path,
    known_ids: set[str],
    rep: BackfillReport,
) -> None:
    resolver = Resolver(conn)
    payload_rows = []
    parsed: list[tuple[cricsheet.RawFile, cricsheet.ParsedMatch, list[dict[str, Any]]]] = []
    for rf in files:
        path = archive_payload(archive_root, cricsheet.SOURCE, rf.member, rf.sha256, rf.data)
        try:
            pm = cricsheet.parse_bytes(rf.data, rf.match_id)
        except Exception as e:  # malformed payload: keep the raw row, report, move on
            rep.errors[rf.member] = f"{type(e).__name__}: {e}"
            status, detail = "error", rep.errors[rf.member]
        else:
            issues = check_match(pm, known_ids)
            parsed.append((rf, pm, issues))
            status = "quarantined" if issues else "loaded"
            detail = f"{len(issues)} DQ issue(s)" if issues else None
        payload_rows.append(
            {
                "source": cricsheet.SOURCE,
                "url_or_file": f"{zip_name}!{rf.member}",
                "fetched_at": fetched_at,
                "sha256": rf.sha256,
                "archive_path": str(path.relative_to(archive_root)),
                "parse_status": status,
                "detail": detail,
            }
        )
    rep.changes.add(
        "raw_payload",
        upsert(
            conn,
            "raw_payload",
            payload_rows,
            ["source", "sha256"],
            update=["url_or_file", "archive_path", "parse_status", "detail"],
        ),
    )
    ids = dict(
        conn.execute(
            text("SELECT sha256, id FROM raw_payload WHERE source = :s AND sha256 = ANY(:h)"),
            {"s": cricsheet.SOURCE, "h": [rf.sha256 for rf in files]},
        ).all()
    )
    copies = []
    for rf, pm, issues in parsed:
        copies.append(SourceCopy(pm, cricsheet.SOURCE, str(rf.match_id), ids[rf.sha256], issues))
        if issues:
            rep.quarantined[rf.match_id] = issues
        else:
            rep.loaded += 1
    log = write_copies(conn, copies, resolver)
    for t, ch in log.by_table.items():
        rep.changes.add(t, ch)
