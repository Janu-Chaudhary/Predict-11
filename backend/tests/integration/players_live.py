"""Shared fixture for read-only analytics tests against the live compose DB (``p11``).

Unlike ``conftest.py`` (throwaway ``p11_test`` database), these tests need the real loaded IPL
data, so they connect to the configured database and only ever SELECT. Skipped when the DB is
unreachable or empty.
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from sqlalchemy import Connection, text

from p11.core import db


@pytest.fixture(scope="module")
def live() -> Iterator[Connection]:
    try:
        conn = db.engine().connect()
        n = conn.execute(text("SELECT count(*) FROM match")).scalar_one()
    except Exception as e:  # pragma: no cover - environment dependent
        pytest.skip(f"live Postgres not reachable: {e}")
    if n < 1000:
        conn.close()
        pytest.skip("live DB does not hold the IPL history")
    conn.execute(text("SET TRANSACTION READ ONLY"))
    try:
        yield conn
    finally:
        conn.rollback()
        conn.close()
