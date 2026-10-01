"""Integration fixtures: a throwaway `p11_test` database on the compose Postgres.

The database is (re)created per test session and migrated with Alembic, so the real
migration is exercised. Tests are skipped if Postgres is not reachable.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from sqlalchemy import Engine, create_engine, text
from sqlalchemy.engine import make_url

from p11.core.settings import get_settings

BACKEND = Path(__file__).resolve().parents[2]
TEST_DB = "p11_test"


def _test_url() -> str:
    base = make_url(os.environ.get("P11_TEST_DATABASE_URL") or get_settings().database_url)
    return base.set(database=TEST_DB).render_as_string(hide_password=False)


@pytest.fixture(scope="session")
def pg_engine() -> Engine:
    admin_url = make_url(_test_url()).set(database="postgres")
    admin = create_engine(admin_url, isolation_level="AUTOCOMMIT")
    try:
        with admin.connect() as c:
            c.execute(text(f"DROP DATABASE IF EXISTS {TEST_DB} WITH (FORCE)"))
            c.execute(text(f"CREATE DATABASE {TEST_DB}"))
    except Exception as e:  # pragma: no cover - environment dependent
        pytest.skip(f"Postgres not reachable for integration tests: {e}")
    finally:
        admin.dispose()

    from alembic import command
    from alembic.config import Config

    cfg = Config(str(BACKEND / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND / "migrations"))
    cfg.set_main_option("sqlalchemy.url", _test_url())
    command.upgrade(cfg, "head")

    eng = create_engine(_test_url())
    yield eng
    eng.dispose()


TABLES = (
    "field_conflict, delivery, innings, match_player, match_source, match, raw_payload, "
    "season_credits, season, competition, team_alias, team, venue_alias, venue, "
    "player_alias, player_source_id, player"
)


@pytest.fixture
def db(pg_engine: Engine) -> Engine:
    with pg_engine.begin() as c:
        c.execute(text(f"TRUNCATE {TABLES} RESTART IDENTITY CASCADE"))
    return pg_engine
