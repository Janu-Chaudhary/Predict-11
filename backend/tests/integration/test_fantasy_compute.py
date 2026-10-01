"""player_attribute resolution + player_match_points compute against a real Postgres."""

from __future__ import annotations

import datetime as dt
import zipfile
from pathlib import Path

import pytest
from sqlalchemy import Engine, text

from p11.core.upsert import upsert
from p11.fantasy.compute import compute_points
from p11.ingest.backfill import backfill_zip
from p11.ingest.player_attributes import load_derived
from p11.registry.people import load_registry
from tests.fixtures import ALL_MATCHES, CRICSHEET, FINAL, NO_RESULT, SUPER_OVER, cricsheet_json
from tests.unit.test_scoring_golden import ROLES

pytestmark = pytest.mark.integration


@pytest.fixture
def loaded(db: Engine, tmp_path: Path) -> Engine:
    with db.begin() as c:
        load_registry(c, CRICSHEET / "people.csv", CRICSHEET / "names.csv")
    z = tmp_path / "ipl_json.zip"
    with zipfile.ZipFile(z, "w") as zf:
        for m in ALL_MATCHES:
            zf.writestr(f"{m}.json", cricsheet_json(m))
    backfill_zip(db, z, tmp_path / "archive")
    with db.begin() as c:
        ids = {
            r[0]: r[1]
            for r in c.execute(
                text(
                    "SELECT p.name, p.id FROM player p JOIN match_player mp "
                    "ON mp.player_id = p.id WHERE mp.match_id = :m"
                ),
                {"m": FINAL},
            )
        }
        rows = [
            {"player_id": ids[n], "source": "bcci", "playing_role": r.value,
             "source_role": None, "batting_hand": None, "bowling_style": None,
             "bowling_type": None, "as_of": dt.date(2026, 3, 28), "detail": None}
            for n, r in ROLES.items()
        ]
        upsert(c, "player_attribute", rows, ["player_id", "source"])
        load_derived(c)
    return db


def q(db: Engine, sql: str, **kw):
    with db.connect() as c:
        return c.execute(text(sql), kw).all()


def test_resolved_role_prefers_scraped_over_derived(loaded):
    (row,) = q(
        loaded,
        "SELECT r.playing_role, r.role_source FROM player_attribute_resolved r "
        "JOIN player p ON p.id = r.player_id WHERE p.name = 'K Rabada'",
    )
    assert row == ("BOWL", "bcci")
    # every lineup member of every match has some role (derived covers the rest)
    assert q(loaded, """
        SELECT count(*) FROM match_player mp LEFT JOIN player_attribute_resolved r
        USING (player_id) WHERE mp.role_in_match <> 'sub_fielder' AND r.playing_role IS NULL
    """)[0][0] == 0


def test_compute_is_idempotent_and_matches_known_values(loaded):
    with loaded.begin() as c:
        r1 = compute_points(c)
    assert r1.matches_scored == 4 and r1.changes.inserted == r1.rows > 0
    assert r1.default_roles == 0

    with loaded.begin() as c:
        assert compute_points(c).matches_scored == 0  # nothing stale
        r3 = compute_points(c, force=True)
    assert r3.matches_scored == 4 and r3.changes.total == 0, vars(r3.changes)

    (kohli,) = q(loaded, """
        SELECT x.total, x.role_used, x.rules_version, x.status, x.items->>'runs'
        FROM player_match_points x JOIN player p ON p.id = x.player_id
        WHERE x.match_id = :m AND p.name = 'V Kohli'
    """, m=FINAL)
    assert kohli == (151, "BAT", "T20_2026", "xi", "75")

    # impact sub in, impact sub out both scored with +4 lineup points
    statuses = dict(q(loaded, """
        SELECT p.name, x.status FROM player_match_points x JOIN player p ON p.id = x.player_id
        WHERE x.match_id = :m AND p.name IN ('VR Iyer', 'JA Duffy')
    """, m=FINAL))
    assert statuses == {"VR Iyer": "impact_in", "JA Duffy": "impact_out"}
    assert q(loaded, "SELECT count(*), min(lineup) FROM player_match_points WHERE match_id = :m",
             m=FINAL)[0] == (24, 4)

    # no-result match: rows exist, all zero
    n, worst = q(loaded, "SELECT count(*), max(abs(total)) FROM player_match_points "
                         "WHERE match_id = :m", m=NO_RESULT)[0]
    assert n >= 22 and worst == 0
    # super-over match scored without the super-over balls (only lineup members scored)
    assert q(loaded, "SELECT count(*) FROM player_match_points WHERE match_id = :m",
             m=SUPER_OVER)[0][0] >= 22

    # components always add up
    assert q(loaded, "SELECT count(*) FROM player_match_points "
                     "WHERE batting + bowling + fielding + lineup + bonuses <> total")[0][0] == 0


def test_role_change_makes_match_stale(loaded):
    with loaded.begin() as c:
        compute_points(c)
        c.execute(text("""
            UPDATE player_attribute SET playing_role = 'BOWL'
            WHERE source = 'bcci' AND player_id = (SELECT id FROM player WHERE name = 'V Kohli')
        """))
        rep = compute_points(c)
    assert rep.matches_scored >= 1  # Kohli's matches rescored
    (role,) = q(loaded, """
        SELECT x.role_used FROM player_match_points x JOIN player p ON p.id = x.player_id
        WHERE x.match_id = :m AND p.name = 'V Kohli'
    """, m=FINAL)
    assert role == ("BOWL",)
