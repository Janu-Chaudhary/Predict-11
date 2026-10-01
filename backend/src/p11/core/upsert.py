"""Bulk natural-key upserts that report exactly how many rows changed.

Rows are COPY'd into a temp staging table, then merged with one
``INSERT ... SELECT ... ON CONFLICT (key) DO UPDATE ... WHERE (cols) IS DISTINCT FROM (new)``.
Unchanged rows are not touched, so a re-run with identical input reports 0 inserted / 0 updated.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from typing import Any

from psycopg.types.json import Jsonb
from sqlalchemy import Connection, text

JSONB_OID = 3802


@dataclass
class Changes:
    inserted: int = 0
    updated: int = 0
    deleted: int = 0

    @property
    def total(self) -> int:
        return self.inserted + self.updated + self.deleted

    def __iadd__(self, other: Changes) -> Changes:
        self.inserted += other.inserted
        self.updated += other.updated
        self.deleted += other.deleted
        return self


@dataclass
class ChangeLog:
    by_table: dict[str, Changes] = field(default_factory=dict)

    def add(self, table: str, ch: Changes) -> None:
        self.by_table.setdefault(table, Changes())
        self.by_table[table] += ch

    @property
    def total(self) -> int:
        return sum(c.total for c in self.by_table.values())

    def as_dict(self) -> dict[str, dict[str, int]]:
        return {
            t: {"inserted": c.inserted, "updated": c.updated, "deleted": c.deleted}
            for t, c in sorted(self.by_table.items())
        }


def _q(ident: str) -> str:
    return '"' + ident.replace('"', '""') + '"'


def _stage(conn: Connection, table: str, cols: Sequence[str], rows: Iterable[Sequence[Any]]) -> str:
    tmp = f"_stg_{table}"
    collist = ", ".join(_q(c) for c in cols)
    conn.execute(text(f"DROP TABLE IF EXISTS {_q(tmp)}"))
    conn.execute(
        text(f"CREATE TEMP TABLE {_q(tmp)} AS SELECT {collist} FROM {_q(table)} WITH NO DATA")
    )
    types = [
        r[0]
        for r in conn.execute(
            text(
                "SELECT CAST(atttypid AS integer) FROM pg_attribute "
                "WHERE attrelid = CAST(:t AS regclass) AND attnum > 0 AND NOT attisdropped "
                "ORDER BY attnum"
            ),
            {"t": tmp},
        )
    ]
    raw = conn.connection.driver_connection
    assert raw is not None
    with raw.cursor() as cur, cur.copy(f"COPY {_q(tmp)} ({collist}) FROM STDIN") as cp:
        cp.set_types(types)
        for r in rows:
            cp.write_row(
                [
                    Jsonb(v) if isinstance(v, dict | list) and t == JSONB_OID else v
                    for v, t in zip(r, types, strict=True)
                ]
            )
    conn.execute(text(f"ANALYZE {_q(tmp)}"))  # real stats -> hash anti-join for deletes
    return tmp


def upsert(
    conn: Connection,
    table: str,
    rows: Sequence[dict[str, Any]],
    key: Sequence[str],
    *,
    update: Sequence[str] | None = None,
    update_where: str | None = None,
    delete_missing: tuple[Sequence[str], Sequence[tuple[Any, ...]]] | None = None,
) -> Changes:
    """Merge ``rows`` into ``table`` on ``key``.

    update: columns refreshed on conflict (default: every non-key column); [] = DO NOTHING.
    update_where: extra SQL guard on the existing row (alias ``t``), e.g. "t.resolved_from = 'x'".
    delete_missing: (scope cols, scope values), e.g. (["match_id", "source"], [(1, "cricsheet")]);
      existing rows inside those scopes that are absent from ``rows`` are deleted, so a revised
      payload that drops a ball also drops it here.
    """
    if not rows:
        if delete_missing is not None and delete_missing[1]:
            return Changes(deleted=_delete_missing(conn, table, None, key, *delete_missing))
        return Changes()
    cols = list(rows[0].keys())
    tmp = _stage(conn, table, cols, ([r[c] for c in cols] for r in rows))
    collist = ", ".join(_q(c) for c in cols)
    keylist = ", ".join(_q(c) for c in key)
    upd = [c for c in cols if c not in key] if update is None else list(update)
    if upd:
        sets = ", ".join(f"{_q(c)} = EXCLUDED.{_q(c)}" for c in upd)
        old = ", ".join(f"t.{_q(c)}" for c in upd)
        new = ", ".join(f"EXCLUDED.{_q(c)}" for c in upd)
        guard = f"(ROW({old}) IS DISTINCT FROM ROW({new}))"
        if update_where:
            guard += f" AND ({update_where})"
        action = f"DO UPDATE SET {sets} WHERE {guard}"
    else:
        action = "DO NOTHING"
    res = conn.execute(
        text(
            f"INSERT INTO {_q(table)} AS t ({collist}) "
            f"SELECT DISTINCT ON ({keylist}) {collist} FROM {_q(tmp)} "
            f"ON CONFLICT ({keylist}) {action} RETURNING (xmax = 0) AS inserted"
        )
    ).all()
    ch = Changes(inserted=sum(1 for r in res if r[0]), updated=sum(1 for r in res if not r[0]))
    if delete_missing is not None:
        scope_cols, scope_vals = delete_missing
        ch.deleted = _delete_missing(conn, table, tmp, key, scope_cols, scope_vals)
    conn.execute(text(f"DROP TABLE {_q(tmp)}"))
    return ch


def _delete_missing(
    conn: Connection,
    table: str,
    tmp: str | None,
    key: Sequence[str],
    scope_cols: Sequence[str],
    scope_vals: Sequence[tuple[Any, ...]],
) -> int:
    if not scope_vals:
        return 0
    params: dict[str, Any] = {}
    tuples = []
    for i, vals in enumerate(scope_vals):
        names = []
        for j, v in enumerate(vals):
            params[f"s{i}_{j}"] = v
            names.append(f":s{i}_{j}")
        tuples.append("(" + ", ".join(names) + ")")
    tcols = "(" + ", ".join("t." + _q(c) for c in scope_cols) + ")"
    sql = f"DELETE FROM {_q(table)} t WHERE {tcols} IN ({', '.join(tuples)})"
    if tmp is not None:
        match = " AND ".join(f"t.{_q(c)} = s.{_q(c)}" for c in key)
        sql += f" AND NOT EXISTS (SELECT 1 FROM {_q(tmp)} s WHERE {match})"
    return conn.execute(text(sql), params).rowcount
